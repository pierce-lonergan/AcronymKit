"""Parenthetical abbreviation extraction (Schwartz & Hearst, 2003).

This module implements the high-precision algorithm described in

    A. S. Schwartz and M. A. Hearst, *A simple algorithm for identifying
    abbreviation definitions in biomedical text*, Pacific Symposium on
    Biocomputing, 2003, pp. 451-462.

The algorithm looks for a bracketed candidate ``short form`` and then walks the
preceding text right-to-left, matching the short form's characters against the
long form. The first short-form character is additionally required to align with
a word boundary, which is what gives the method its high precision.

Both the canonical ``Long Form (Short Form)`` arrangement and the inverted
``Short Form (Long Form)`` arrangement are supported.

The module is Tier 0 pure: it imports only the standard library, ``pydantic``
(transitively, via :mod:`acronymkit.models`) and other ``acronymkit`` modules.
:class:`~acronymkit.tokenizer.Tokenizer` is imported lazily, and only when
``Config.extraction_capture_sentences`` is enabled, so importing this module
never pulls in the tokenizer or its resource files.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from .config import Config
from .models import AcronymPair

if TYPE_CHECKING:  # pragma: no cover - typing-only import
    from .tokenizer import Tokenizer

__all__ = [
    "AbbreviationExtractor",
    "find_best_long_form",
    "is_valid_long_form",
    "is_valid_short_form",
]

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

#: Closing bracket -> the opening bracket it must be matched against.
_BRACKETS: dict[str, str] = {")": "(", "]": "[", "}": "{"}
_OPENING_BRACKETS = frozenset(_BRACKETS.values())
_CLOSING_BRACKETS = frozenset(_BRACKETS)

#: Characters that terminate the backwards scan for the long-form window.
#: A bracket or a ``;``/``:`` delimiter means the preceding material belongs to
#: a different syntactic unit and may not be absorbed into the long form.
_WINDOW_STOP_CHARS = frozenset("()[]{};:")

#: Sentence-terminating punctuation, including the CJK/fullwidth forms.
_SENTENCE_END_CHARS = frozenset(".!?\u3002\uff01\uff1f")

#: Closing quotes/brackets that may trail a sentence terminator.
_CLOSING_QUOTES = "\"')]}\u2019\u201d"

#: Lowercase words whose trailing full stop does not end a sentence.
_ABBREVIATIONS = frozenset(
    {
        "al",
        "approx",
        "cf",
        "dr",
        "eq",
        "eqs",
        "est",
        "etc",
        "fig",
        "figs",
        "inc",
        "jr",
        "ltd",
        "mr",
        "mrs",
        "ms",
        "no",
        "nos",
        "prof",
        "ref",
        "refs",
        "sr",
        "st",
        "vol",
        "vs",
    }
)

#: Word separators for long-form word counting (whitespace, dashes, slashes).
_WORD_SPLIT_RE = re.compile(r"[\s/\u2010-\u2015-]+")

#: Confidence floor for a pair whose characters never align with word initials.
_MIN_CONFIDENCE = 0.6
_CONFIDENCE_RANGE = 1.0 - _MIN_CONFIDENCE

#: Longest punctuation run trimmed from either end of a candidate. Bounding the
#: trim keeps deeply nested bracket runs from degrading to quadratic time.
_MAX_TRIM = 8

#: Longest whitespace run tolerated between a token and a following bracket.
_MAX_GAP = 64

#: Character budget for the backwards long-form window scan, per retained word.
_WINDOW_CHAR_BUDGET_PER_WORD = 40

#: The line terminators a blank line is built from. ``\r\n`` counts once.
_LINE_BREAK_CHARS = frozenset("\n\r")


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------


def _window_char_budget(word_limit: int) -> int:
    """Character ceiling for a long-form window retaining ``word_limit`` words.

    Every per-region cost -- the backwards window scan, the trailing-word
    trimmer, the matcher and the post-filters -- is clamped to this many
    characters, which is what keeps extraction linear in document length rather
    than quadratic in the size of a deeply nested bracket region.

    Args:
        word_limit: Number of words the window may retain.

    Returns:
        The maximum number of characters the window may span.
    """
    return _WINDOW_CHAR_BUDGET_PER_WORD * word_limit + _MAX_GAP


def _casefold_char(char: str) -> str:
    """Return a single-character, case-insensitive comparison key for ``char``.

    ``str.lower`` is not length preserving: ``"İ"`` (LATIN CAPITAL LETTER I
    WITH DOT ABOVE) lowercases to ``"i"`` plus a combining dot above, a
    two-code-point string whose :meth:`str.isalnum` is ``False``. Folding to the
    first code point keeps the key one character wide for every input, so a real
    letter can never be mistaken for punctuation and ``"I"`` still compares
    equal to ``"İ"``.

    Args:
        char: A single character.

    Returns:
        The folded key -- one character, or ``char`` itself if the fold is empty.
    """
    folded = char.casefold()
    return folded[:1] or char


def _line_break_count(text: str, index: int, ceiling: int = 2) -> int:
    """Count line terminators in the newline run ending at ``text[index]``.

    ``\\r\\n`` is one terminator, so an ordinary Windows newline scores ``1``
    while a blank line -- ``\\n\\n``, ``\\r\\n\\r\\n``, ``\\r\\r`` or any mixture --
    scores ``2``. Counting stops at ``ceiling``, so the walk inspects at most a
    handful of characters however long the run of blank lines is.

    Args:
        text: The text being scanned.
        index: Offset of a line terminator; the run is walked leftwards from it.
        ceiling: Stop once this many terminators have been counted.

    Returns:
        The number of terminators found, capped at ``ceiling``.
    """
    count = 0
    cursor = index
    while cursor >= 0 and text[cursor] in _LINE_BREAK_CHARS and count < ceiling:
        if text[cursor] == "\n" and cursor > 0 and text[cursor - 1] == "\r":
            cursor -= 2  # a CRLF pair is a single terminator
        else:
            cursor -= 1
        count += 1
    return count


def _is_plain_word(word: str) -> bool:
    """Report whether ``word`` is an ordinary word rather than an abbreviation.

    A plain word is all letters with nothing but lowercase after the first, so
    ``"World"``, ``"Table"`` and ``"magnetic"`` are plain while ``"CNS"``,
    ``"mRNA"``, ``"IL-6"`` and ``"H2O"`` are not.

    Args:
        word: A single whitespace-free token.

    Returns:
        ``True`` when the token reads as a word, not as an abbreviation.
    """
    return len(word) > 1 and word.isalpha() and word[1:].islower()


def _alnum_count(text: str) -> int:
    """Return the number of alphanumeric characters in ``text``."""
    return sum(1 for char in text if char.isalnum())


def _split_words(text: str) -> list[str]:
    """Split ``text`` into words on whitespace, dashes and slashes.

    Mirrors the ``StringTokenizer(longForm, " \\t\\n\\r\\f-")`` behaviour of the
    reference implementation, so ``"non-Hodgkin lymphoma"`` counts as three
    words rather than two.

    Args:
        text: Arbitrary text.

    Returns:
        The non-empty word components, in order.
    """
    return [word for word in _WORD_SPLIT_RE.split(text.strip()) if word]


def _contains_standalone(haystack: str, needle: str) -> bool:
    """Report whether ``needle`` occurs in ``haystack`` as a standalone word.

    The comparison is case-sensitive (as in the reference implementation) and a
    match counts only when neither neighbouring character is alphanumeric.

    Args:
        haystack: Text to search.
        needle: Literal substring to look for.

    Returns:
        ``True`` when a standalone occurrence exists.
    """
    if not needle:
        return False
    start = 0
    while True:
        index = haystack.find(needle, start)
        if index < 0:
            return False
        before_ok = index == 0 or not haystack[index - 1].isalnum()
        after = index + len(needle)
        after_ok = after >= len(haystack) or not haystack[after].isalnum()
        if before_ok and after_ok:
            return True
        start = index + 1


def _trim_span(text: str, start: int, end: int, *, limit: int = _MAX_TRIM) -> tuple[int, int]:
    """Shrink ``[start, end)`` until both ends sit on alphanumeric characters.

    At most ``limit`` characters are removed from each end: real candidates
    carry a character or two of punctuation, and the bound keeps pathological
    input such as ``"((((((...))))))"`` linear rather than quadratic.

    Args:
        text: The text the offsets index into.
        start: Inclusive start offset.
        end: Exclusive end offset.
        limit: Maximum characters trimmed from each end.

    Returns:
        The trimmed ``(start, end)`` pair; ``start == end`` when nothing
        alphanumeric survives.
    """
    budget = limit
    while start < end and budget > 0 and not text[start].isalnum():
        start += 1
        budget -= 1
    budget = limit
    while end > start and budget > 0 and not text[end - 1].isalnum():
        end -= 1
        budget -= 1
    return start, end


def _bracket_regions(text: str) -> list[tuple[int, int]]:
    """Find every balanced bracketed region in ``text``.

    A single left-to-right pass with an explicit stack handles ``()``, ``[]``
    and ``{}``. Unbalanced openers are dropped when the scan ends, unbalanced or
    mismatched closers are ignored, and nested regions are all reported. The
    pass is linear and therefore cannot loop forever on malformed input.

    Args:
        text: Text to scan.

    Returns:
        ``(open_index, close_index)`` offsets sorted by opening position.
    """
    stack: list[tuple[str, int]] = []
    regions: list[tuple[int, int]] = []
    for index, char in enumerate(text):
        if char in _OPENING_BRACKETS:
            stack.append((char, index))
        elif char in _CLOSING_BRACKETS and stack and stack[-1][0] == _BRACKETS[char]:
            _, open_index = stack.pop()
            regions.append((open_index, index))
    regions.sort()
    return regions


def _is_sentence_boundary(text: str, index: int) -> bool:
    """Report whether ``text[index]`` terminates a sentence.

    Guards against the common abbreviations that would otherwise split a
    sentence in two (``e.g.``, ``i.e.``, ``Dr.``, ``Fig.``, ``vs.``, ``et al.``,
    ``cf.``, ``approx.``, ``No.`` and single initials such as ``J. R.``).

    Args:
        text: The text being scanned.
        index: Offset of the candidate terminator.

    Returns:
        ``True`` when the character ends a sentence.
    """
    char = text[index]
    if char not in _SENTENCE_END_CHARS:
        return False
    following = text[index + 1] if index + 1 < len(text) else " "
    if not (following.isspace() or following in _CLOSING_QUOTES):
        return False
    if char != ".":
        return True
    cursor = index - 1
    while cursor >= 0 and (text[cursor].isalnum() or text[cursor] == "."):
        cursor -= 1
    raw_word = text[cursor + 1 : index]
    if "." in raw_word:  # "e.g." / "i.e." / "U.S."
        return False
    word = raw_word.lower()
    if len(word) <= 1:  # a single initial such as "J."
        return False
    return word not in _ABBREVIATIONS


def _fallback_sentence_spans(text: str) -> list[tuple[int, int]]:
    """Split ``text`` into sentence spans without the tokenizer.

    Used only when :class:`~acronymkit.tokenizer.Tokenizer` is unavailable, so
    that sentence capture degrades instead of failing.

    Args:
        text: Text to split.

    Returns:
        ``(start, end)`` offsets covering every sentence, in order.
    """
    spans: list[tuple[int, int]] = []
    start = 0
    index = 0
    length = len(text)
    while index < length:
        if text[index] in _SENTENCE_END_CHARS and _is_sentence_boundary(text, index):
            end = index + 1
            while end < length and text[end] in _CLOSING_QUOTES:
                end += 1
            if end > start:
                spans.append((start, end))
            start = end
            while start < length and text[start].isspace():
                start += 1
            index = start
            continue
        index += 1
    if start < length:
        spans.append((start, length))
    return spans


def _limit_to_last_words(
    text: str, start: int, end: int, limit: int, *, char_budget: int
) -> Optional[tuple[int, int]]:
    """Restrict ``text[start:end]`` to its trailing ``limit`` words.

    At most ``char_budget`` characters are examined: a longer segment is clipped
    to its final ``char_budget`` characters and the clip point is then advanced
    to the next whitespace so no partial word leaks in. The clip matters because
    ``limit`` bounds the number of retained *words*, not their size -- a single
    unbounded "word" such as the closing run of a deep bracket nest would
    otherwise make this scan proportional to the whole region, and the extraction
    quadratic in document length.

    Args:
        text: The text the offsets index into.
        start: Inclusive start offset of the segment.
        end: Exclusive end offset of the segment.
        limit: Maximum number of trailing words to retain.
        char_budget: Maximum number of characters examined.

    Returns:
        ``(start, end)`` offsets of the retained words with surrounding
        whitespace removed, or ``None`` when no whole word survives the budget.
    """
    if end - start > char_budget:
        start = end - char_budget
        while start < end and not text[start].isspace():
            start += 1
    retained = max(1, limit)
    cursor = end
    word_start = end
    last_end = -1
    count = 0
    while cursor > start and count < retained:
        while cursor > start and text[cursor - 1].isspace():
            cursor -= 1
        if cursor <= start:
            break
        if last_end < 0:
            last_end = cursor
        while cursor > start and not text[cursor - 1].isspace():
            cursor -= 1
        word_start = cursor
        count += 1
    if last_end < 0:
        return None
    return word_start, last_end


def _initial_match_fraction(short_form: str, long_form: str) -> float:
    """Fraction of short-form characters that align with long-form initials.

    Greedy left-to-right alignment that is allowed to skip long-form words (so
    that function words such as ``and`` in ``"National Aeronautics and Space
    Administration"`` do not penalise ``NASA``) but never rewinds. A character
    that cannot be placed on any remaining initial is simply not counted.

    Args:
        short_form: Candidate short form.
        long_form: Candidate long form.

    Returns:
        A value in ``[0.0, 1.0]``; ``1.0`` means every short-form character sits
        on a word initial.
    """
    characters = [_casefold_char(char) for char in short_form if char.isalnum()]
    if not characters:
        return 0.0
    initials = [
        _casefold_char(word[0]) for word in _split_words(long_form) if word and word[0].isalnum()
    ]
    matched = 0
    cursor = 0
    for character in characters:
        probe = cursor
        while probe < len(initials) and initials[probe] != character:
            probe += 1
        if probe < len(initials):
            matched += 1
            cursor = probe + 1
    return matched / len(characters)


def _confidence(short_form: str, long_form: str) -> float:
    """Map the initial-alignment fraction onto the reported confidence.

    A fully initial alignment scores ``1.0``; confidence decays linearly toward
    ``0.6`` as characters fall inside words instead of starting them.

    Args:
        short_form: Candidate short form.
        long_form: Candidate long form.

    Returns:
        A confidence in ``[0.6, 1.0]``, rounded to four decimal places so the
        output is byte-stable.
    """
    fraction = _initial_match_fraction(short_form, long_form)
    value = _MIN_CONFIDENCE + _CONFIDENCE_RANGE * fraction
    return round(min(1.0, max(_MIN_CONFIDENCE, value)), 4)


# ---------------------------------------------------------------------------
# Public predicate / matching functions
# ---------------------------------------------------------------------------


def is_valid_short_form(text: str, *, min_length: int = 2, max_length: int = 10) -> bool:
    """Report whether ``text`` may act as a short form (abbreviation).

    Applies the Schwartz & Hearst admissibility rules: the candidate must be
    between ``min_length`` and ``max_length`` characters long, begin with an
    alphanumeric character, contain at least one letter, consist of at most two
    words, and carry at least one uppercase letter (or be caseless/all-caps).

    Args:
        text: Candidate short form; surrounding whitespace is ignored.
        min_length: Minimum admissible length in characters.
        max_length: Maximum admissible length in characters.

    Returns:
        ``True`` when the candidate is an admissible short form.
    """
    candidate = text.strip()
    if not candidate:
        return False
    if not min_length <= len(candidate) <= max_length:
        return False
    if not candidate[0].isalnum():
        return False
    if not any(char.isalpha() for char in candidate):
        return False
    if len(candidate.split()) > 2:
        return False
    return any(char.isupper() for char in candidate) or candidate == candidate.upper()


def is_valid_long_form(short_form: str, long_form: str) -> bool:
    """Post-filter a recovered long form against its short form.

    Rejects a long form that is not longer than the short form, that holds fewer
    alphanumeric characters than the short form, that spans more than
    ``len(short_form) + 5`` words, or that already contains the short form as a
    standalone word (which would make the parenthetical a restatement rather
    than a definition).

    Args:
        short_form: The abbreviation.
        long_form: The expansion recovered by :func:`find_best_long_form`.

    Returns:
        ``True`` when the pair should be reported.
    """
    short = short_form.strip()
    expansion = long_form.strip()
    if not short or not expansion:
        return False
    if len(expansion) <= len(short):
        return False
    if _alnum_count(expansion) < _alnum_count(short):
        return False
    if len(_split_words(expansion)) > len(short) + 5:
        return False
    return not _contains_standalone(expansion, short)


def find_best_long_form(short_form: str, long_form_window: str) -> Optional[str]:
    """Recover the long form of ``short_form`` from the preceding text.

    This is the reference ``findBestLongForm`` control flow, transcribed
    verbatim. Both cursors start at the right-hand end. For every alphanumeric
    short-form character (non-alphanumeric characters are skipped; the test is
    applied to the original character, never to its case fold, so a letter whose
    lowercase expands to several code points is still a letter) the window
    cursor walks leftward -- restarting the comparison from ``lIndex - 1`` on
    every mismatch -- until the character matches case-insensitively. The
    *first* short-form character carries the extra constraint that it must land
    at offset ``0`` or be immediately preceded by a non-alphanumeric character
    (a space or hyphen in practice), which is what makes the method
    high-precision. Running the window cursor off the left edge means failure.

    On success the cursor is snapped back to the start of the word it landed in
    and everything from there to the end of the window is returned.

    Args:
        short_form: The abbreviation being defined.
        long_form_window: Text preceding the opening bracket (for the inverted
            arrangement, the bracketed text itself).

    Returns:
        The matched long form -- always a suffix of ``long_form_window`` -- or
        ``None`` when no alignment exists.
    """
    if not short_form or not long_form_window:
        return None

    s_index = len(short_form) - 1
    l_index = len(long_form_window) - 1

    while s_index >= 0:
        character = short_form[s_index]
        if not character.isalnum():
            s_index -= 1
            continue
        current = _casefold_char(character)
        while (l_index >= 0 and _casefold_char(long_form_window[l_index]) != current) or (
            s_index == 0 and l_index > 0 and long_form_window[l_index - 1].isalnum()
        ):
            l_index -= 1
        if l_index < 0:
            return None
        l_index -= 1
        s_index -= 1

    start = long_form_window.rfind(" ", 0, l_index + 1) + 1
    return long_form_window[start:]


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


class AbbreviationExtractor:
    """Extract ``(short form, long form)`` definitions from running text.

    The extractor is stateless apart from a lazily constructed tokenizer used
    for sentence capture, so a single instance can be shared across threads.

    Example:
        >>> from acronymkit.config import Config
        >>> from acronymkit.extractor import AbbreviationExtractor
        >>> pairs = AbbreviationExtractor(Config()).extract(
        ...     "The World Health Organization (WHO) responded."
        ... )
        >>> [(p.short_form, p.long_form) for p in pairs]
        [('WHO', 'World Health Organization')]
    """

    __slots__ = ("_config", "_tokenizer")

    def __init__(self, config: Config, tokenizer: Optional[Tokenizer] = None) -> None:
        """Build an extractor.

        Args:
            config: Engine configuration. ``extraction_min_short_form_length``,
                ``extraction_max_short_form_length`` and
                ``extraction_capture_sentences`` are honoured.
            tokenizer: Optional pre-built tokenizer reused for sentence
                splitting. One is constructed on demand when sentence capture is
                enabled and none was supplied.
        """
        self._config = config
        self._tokenizer = tokenizer

    @property
    def config(self) -> Config:
        """The configuration governing this extractor."""
        return self._config

    # -- public API --------------------------------------------------------
    def extract(self, text: str) -> list[AcronymPair]:
        """Extract every abbreviation definition in ``text``.

        Scans balanced ``()``/``[]``/``{}`` regions in document order, applies
        the Schwartz & Hearst matcher to each, and returns the surviving pairs.
        Identical ``(short form, long form, spans)`` tuples are reported once.

        Args:
            text: Source document. Empty or whitespace-only input yields ``[]``.

        Returns:
            The recovered pairs in document order. Every pair satisfies
            ``text[p.short_form_span[0]:p.short_form_span[1]] == p.short_form``
            and the equivalent identity for the long form.
        """
        if not text or not text.strip():
            return []

        pairs: list[AcronymPair] = []
        seen: set[tuple[str, str, tuple[int, int], tuple[int, int]]] = set()
        for open_index, close_index in _bracket_regions(text):
            pair = self._pair_for_region(text, open_index, close_index)
            if pair is None:
                continue
            key = (pair.short_form, pair.long_form, pair.short_form_span, pair.long_form_span)
            if key in seen:
                continue
            seen.add(key)
            pairs.append(pair)

        if pairs and self._config.extraction_capture_sentences:
            pairs = self._attach_sentences(text, pairs)
        return pairs

    # -- region handling ---------------------------------------------------
    def _pair_for_region(
        self, text: str, open_index: int, close_index: int
    ) -> Optional[AcronymPair]:
        """Build the pair defined by one bracketed region, if any.

        The canonical ``Long Form (Short Form)`` arrangement is tried first, and
        the inverted ``Short Form (Long Form)`` arrangement is tried whenever it
        yields nothing. The fallback is what makes a capitalised expansion work:
        ``"(World Health Organization)"`` may still be read as a bracketed short
        form by some route, and committing to the forward branch on that reading
        would lose the definition entirely.

        Args:
            text: The source document.
            open_index: Offset of the opening bracket.
            close_index: Offset of the closing bracket.

        Returns:
            The recovered :class:`~acronymkit.models.AcronymPair`, or ``None``.
        """
        content_start, content_end = open_index + 1, close_index
        if content_start >= content_end:
            return None

        short = self._short_form_in(text, content_start, content_end)
        if short is not None:
            pair = self._match_forward(text, open_index, short)
            if pair is not None:
                return pair
        return self._match_inverted(text, open_index, content_start, content_end)

    def _match_forward(
        self, text: str, open_index: int, short: tuple[str, int, int]
    ) -> Optional[AcronymPair]:
        """Match the canonical ``Long Form (Short Form)`` arrangement.

        Args:
            text: The source document.
            open_index: Offset of the opening bracket.
            short: ``(short_form, start, end)`` of the bracketed short form.

        Returns:
            The recovered pair, or ``None`` when no long form aligns.
        """
        short_form, short_start, short_end = short
        window = self._long_form_window(text, open_index, len(short_form))
        if window is None:
            return None
        return self._build_pair(text, short_form, (short_start, short_end), window, "long(short)")

    def _match_inverted(
        self, text: str, open_index: int, content_start: int, content_end: int
    ) -> Optional[AcronymPair]:
        """Match the inverted ``Short Form (Long Form)`` arrangement.

        Attempted when the canonical arrangement yielded nothing and the token
        immediately preceding the bracket is a valid short form. The bracketed
        text is clamped to the same word *and* character budget as a forward
        window, so an enormous parenthetical costs no more than a small one.

        Args:
            text: The source document.
            open_index: Offset of the opening bracket.
            content_start: Offset of the first bracketed character.
            content_end: Offset one past the last bracketed character.

        Returns:
            The recovered pair, or ``None``.
        """
        preceding = self._preceding_token(text, open_index)
        if preceding is None:
            return None
        short_form, short_start, short_end = preceding
        word_limit = _window_word_limit(len(short_form))
        window = _limit_to_last_words(
            text,
            content_start,
            content_end,
            word_limit,
            char_budget=_window_char_budget(word_limit),
        )
        if window is None:
            return None
        return self._build_pair(text, short_form, (short_start, short_end), window, "short(long)")

    def _build_pair(
        self,
        text: str,
        short_form: str,
        short_span: tuple[int, int],
        window: tuple[int, int],
        pattern: str,
    ) -> Optional[AcronymPair]:
        """Run the matcher over ``window`` and assemble the resulting pair.

        Args:
            text: The source document.
            short_form: The abbreviation.
            short_span: Exact offsets of ``short_form`` in ``text``.
            window: ``(start, end)`` offsets of the long-form search window.
            pattern: ``"long(short)"`` or ``"short(long)"``.

        Returns:
            The recovered pair, or ``None`` when nothing valid aligned.
        """
        window_start, window_end = window
        window_text = text[window_start:window_end]
        long_form = find_best_long_form(short_form, window_text)
        if long_form is None or not is_valid_long_form(short_form, long_form):
            return None
        long_start = window_start + len(window_text) - len(long_form)
        return AcronymPair(
            short_form=short_form,
            long_form=long_form,
            short_form_span=short_span,
            long_form_span=(long_start, window_end),
            confidence=_confidence(short_form, long_form),
            pattern=pattern,
        )

    # -- candidate location ------------------------------------------------
    def _short_form_in(self, text: str, start: int, end: int) -> Optional[tuple[str, int, int]]:
        """Locate an admissible short form inside a bracketed region.

        Implements the Schwartz & Hearst "take the first word" rule: when the
        bracketed text contains whitespace and its first word alone is a valid
        short form, that word wins (``"(RCT; n=42)"`` -> ``"RCT"``); otherwise
        the whole bracketed text is tried.

        The first-word rule is refused for a *plain* leading word (see
        :func:`_is_plain_word`), because a multi-word Title Case parenthetical is
        an expansion rather than an abbreviation plus a gloss: without that
        guard ``"(World Health Organization)"`` reads as the short form
        ``"World"`` and the definition is lost.

        Both branches are size-capped -- the first word is scanned only as far as
        an admissible short form could reach, and the whole-text branch is gated
        on the region already being short enough -- so an enormous parenthetical
        costs O(1) here.

        Args:
            text: The source document.
            start: Offset of the first bracketed character.
            end: Offset one past the last bracketed character.

        Returns:
            ``(short_form, start, end)`` with exact offsets, or ``None``.
        """
        content_start, content_end = _trim_span(text, start, end)
        if content_start >= content_end:
            return None

        max_length = self._config.extraction_max_short_form_length
        # Locate the end of the first word without materialising the (possibly
        # enormous) bracketed text: anything longer than a short form can be.
        scan_limit = min(content_end, content_start + max_length + 2 * _MAX_TRIM + 1)
        cursor = content_start
        while cursor < scan_limit and not text[cursor].isspace():
            cursor += 1
        if cursor >= scan_limit and cursor < content_end:
            return None  # first word alone exceeds any admissible short form

        if cursor < content_end:  # the bracketed text holds whitespace
            word_start, word_end = _trim_span(text, content_start, cursor)
            if word_start < word_end:
                first_word = text[word_start:word_end]
                if not _is_plain_word(first_word) and self._is_short_form(first_word):
                    return first_word, word_start, word_end

        if content_end - content_start <= max_length:
            candidate = text[content_start:content_end]
            if self._is_short_form(candidate):
                return candidate, content_start, content_end
        return None

    def _preceding_token(self, text: str, open_index: int) -> Optional[tuple[str, int, int]]:
        """Return the admissible short-form token immediately before a bracket.

        Args:
            text: The source document.
            open_index: Offset of the opening bracket.

        Returns:
            ``(short_form, start, end)`` with exact offsets, or ``None`` when
            the preceding token is missing, too long to be a short form, or is
            not a valid short form.
        """
        cursor = open_index - 1
        gap = _MAX_GAP
        while cursor >= 0 and text[cursor].isspace():
            if gap <= 0:
                return None
            cursor -= 1
            gap -= 1
        end = cursor + 1
        budget = self._config.extraction_max_short_form_length + 2 * _MAX_TRIM
        while cursor >= 0 and not text[cursor].isspace():
            if budget <= 0:
                return None
            cursor -= 1
            budget -= 1
        start = cursor + 1
        if start >= end:
            return None
        start, end = _trim_span(text, start, end)
        if start >= end:
            return None
        token = text[start:end]
        if not self._is_short_form(token):
            return None
        return token, start, end

    def _long_form_window(
        self, text: str, open_index: int, short_length: int
    ) -> Optional[tuple[int, int]]:
        """Compute the long-form search window preceding a bracket.

        The window never crosses a sentence boundary, a paragraph break, or a
        preceding bracket/``;``/``:`` delimiter, and retains at most
        ``min(short_length + 5, short_length * 2)`` trailing words.

        A paragraph break means a *blank line*: two line terminators in a row
        under any convention (``\\n\\n``, ``\\r\\n\\r\\n``, ``\\r\\r``, or a
        mixture). A single newline is only a line wrap and never a boundary --
        testing ``text[cursor - 1] in "\\n\\r"`` instead would read the ``\\r`` of
        an ordinary CRLF as a paragraph break and lose every definition whose
        long form wraps a line in a Windows document.

        Args:
            text: The source document.
            open_index: Offset of the opening bracket.
            short_length: Length of the short form in characters.

        Returns:
            ``(start, end)`` offsets of the window, or ``None`` when no words
            precede the bracket.
        """
        word_limit = _window_word_limit(short_length)
        char_budget = _window_char_budget(word_limit)
        budget = char_budget
        boundary = 0
        cursor = open_index - 1
        while cursor >= 0:
            char = text[cursor]
            if char in _WINDOW_STOP_CHARS:
                boundary = cursor + 1
                break
            if char in _LINE_BREAK_CHARS and _line_break_count(text, cursor) >= 2:
                boundary = cursor + 1
                break
            if char in _SENTENCE_END_CHARS and _is_sentence_boundary(text, cursor):
                boundary = cursor + 1
                break
            if budget <= 0:
                # Far more text than the window can retain: stop here, then step
                # forward to the next whitespace so no partial word leaks in.
                # Both walks are capped by ``char_budget``, so this is O(1) in
                # the length of the document.
                boundary = cursor
                while boundary < open_index and not text[boundary].isspace():
                    boundary += 1
                break
            cursor -= 1
            budget -= 1
        # The scan above already bounds ``open_index - boundary`` by the budget
        # (inclusive of the stopping character), so the clamp never bites here.
        return _limit_to_last_words(
            text, boundary, open_index, word_limit, char_budget=char_budget + 1
        )

    def _is_short_form(self, candidate: str) -> bool:
        """Apply :func:`is_valid_short_form` using the configured bounds."""
        return is_valid_short_form(
            candidate,
            min_length=self._config.extraction_min_short_form_length,
            max_length=self._config.extraction_max_short_form_length,
        )

    # -- sentence capture --------------------------------------------------
    def _attach_sentences(self, text: str, pairs: list[AcronymPair]) -> list[AcronymPair]:
        """Return copies of ``pairs`` carrying their enclosing sentence.

        Args:
            text: The source document.
            pairs: Pairs already extracted from ``text``.

        Returns:
            New pairs with :attr:`~acronymkit.models.AcronymPair.sentence` set
            where an enclosing sentence could be identified.
        """
        spans = self._sentence_spans(text)
        if not spans:
            return pairs
        updated: list[AcronymPair] = []
        for pair in pairs:
            anchor = min(pair.short_form_span[0], pair.long_form_span[0])
            sentence: Optional[str] = None
            for span_start, span_end in spans:
                if span_start <= anchor < span_end:
                    sentence = text[span_start:span_end].strip()
                    break
            updated.append(pair.model_copy(update={"sentence": sentence}) if sentence else pair)
        return updated

    def _sentence_spans(self, text: str) -> list[tuple[int, int]]:
        """Return sentence offsets, preferring the tokenizer's splitter.

        The tokenizer is imported lazily so that this module carries no
        import-time dependency on it; any failure to build or run it degrades to
        a local splitter rather than propagating.

        Args:
            text: The source document.

        Returns:
            ``(start, end)`` offsets of each sentence.
        """
        tokenizer = self._tokenizer
        if tokenizer is None:
            try:
                from .tokenizer import Tokenizer as _Tokenizer

                tokenizer = _Tokenizer(self._config)
            except Exception:  # pragma: no cover - defensive degradation
                return _fallback_sentence_spans(text)
            self._tokenizer = tokenizer
        try:
            return [(int(start), int(end)) for start, end in tokenizer.split_sentences(text)]
        except Exception:  # pragma: no cover - defensive degradation
            return _fallback_sentence_spans(text)


def _window_word_limit(short_length: int) -> int:
    """Return the S&H long-form window size for a short form of this length.

    Args:
        short_length: Length of the short form in characters.

    Returns:
        ``min(short_length + 5, short_length * 2)``, at least ``1``.
    """
    return max(1, min(short_length + 5, short_length * 2))
