"""Deterministic, Unicode-aware tokenisation for ``acronymkit``.

Tokenization contract
---------------------
:class:`Tokenizer` turns raw text into a flat, ordered list of
:class:`~acronymkit.models.Token` records. Every downstream subsystem (scoring,
forward generation, backronym alignment, extraction) consumes that list and
nothing else, so the guarantees below are load-bearing:

1. **Exact offsets.** ``text[token.start:token.end] == token.text`` holds for
   every emitted token. Offsets index the *original* string, never a normalised
   copy, so callers can highlight or slice the source safely.
2. **Ordered and gapless in sequence.** ``token.index`` is the zero-based
   position in the returned list. Tokens never overlap and are yielded in
   left-to-right document order.
3. **Punctuation is dropped.** Runs consisting only of punctuation or symbols
   are never emitted. Whitespace-only or empty input yields ``[]``; raising
   :class:`~acronymkit.exceptions.EmptyPhraseError` is the caller's job.
4. **Unicode by construction.** Accented Latin, Greek, Cyrillic and other
   cased scripts tokenise like ASCII. A run of CJK / kana / Hangul characters
   forms a single token whose ``letters`` is its first character, because those
   scripts have no initial-letter convention to exploit.
5. **Compounds keep their parts.** Hyphenated (``-``, ``\\u2013``, ``\\u2014``),
   slashed and camelCase/PascalCase words stay one token but populate
   :attr:`~acronymkit.models.Token.subtokens`; which characters they may donate
   is decided by :class:`~acronymkit.enums.HyphenPolicy`.
6. **Apostrophes are contractions by default.** ``"don't"`` is one token.
   Romance-language elision (``"l'International"``) splits into the clitic and
   the head word so the clitic can be caught by the stop-word registry.
7. **``letters`` is the only donation channel.** A token contributes characters
   to a candidate acronym exclusively through
   :attr:`~acronymkit.models.Token.letters`; index ``0`` is the token initial
   and any further characters are what make ``INTERNAL`` / ``CONTIGUOUS``
   mappings possible.
8. **``is_critical`` defines T_critical.** It is exactly
   ``role in (CONTENT, ACRONYM) and is_eligible`` -- the set counted by the
   information-loss term ``Psi(T, A)``.

The module is pure standard library plus ``pydantic`` and therefore usable on
the Tier 0 (zero-dependency) path.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

from .config import Config
from .enums import HyphenPolicy, NumeralPolicy, StopWordCategory, TokenRole
from .exceptions import ResourceNotFoundError, TokenizationError
from .models import Token
from .stopwords import StopWordRegistry

__all__ = [
    "Tokenizer",
    "is_roman_numeral",
    "normalize",
    "spell_number",
    "split_camel_case",
    "strip_accents",
]


# ---------------------------------------------------------------------------
# Character inventories
# ---------------------------------------------------------------------------

#: Scripts whose characters carry no initial-letter convention. A maximal run of
#: these is emitted as one token contributing only its first character.
_CJK_RANGES = (
    "\u2e80-\u2eff"  # CJK radicals supplement
    "\u3005-\u3007"  # iteration marks / ideographic zero
    "\u3040-\u30ff"  # hiragana + katakana
    "\u3100-\u312f"  # bopomofo
    "\u3130-\u318f"  # hangul compatibility jamo
    "\u31f0-\u31ff"  # katakana phonetic extensions
    "\u3400-\u4dbf"  # CJK unified ideographs extension A
    "\u4e00-\u9fff"  # CJK unified ideographs
    "\ua960-\ua97f"  # hangul jamo extended-A
    "\uac00-\ud7af"  # hangul syllables
    "\uf900-\ufaff"  # CJK compatibility ideographs
    "\U00020000-\U0002a6df"  # CJK unified ideographs extension B
)
_CJK_CLASS = "[" + _CJK_RANGES + "]"

#: Apostrophe-like code points treated as word-internal.
_APOSTROPHES = frozenset("'\u2019\u02bc\u055a")

#: Hyphen-like code points and the solidus, treated as compound separators.
_COMPOUND_SEPARATORS = "\\-\u2010\u2011\u2012\u2013\u2014\u2015/"

#: A word character: any Unicode letter that is *not* CJK, or any decimal digit.
_WORD_CHAR = "(?:(?!" + _CJK_CLASS + r")[^\W\d_]|\d)"

#: Word-internal connectors: apostrophes, hyphen family, solidus, and the
#: decimal point when (and only when) it sits between two digits.
_CONNECTOR = (
    "(?:['\u2019\u02bc\u055a\u2010\u2011\u2012\u2013\u2014\u2015/-]"
    r"|(?<=\d)\.(?=\d))"
)

_TOKEN_RE = re.compile(
    "(?P<cjk>" + _CJK_CLASS + "+)"
    "|(?P<word>" + _WORD_CHAR + "+(?:" + _CONNECTOR + _WORD_CHAR + "+)*)",
    re.UNICODE,
)

_CJK_RUN_RE = re.compile(_CJK_CLASS + "+", re.UNICODE)
_COMPOUND_SPLIT_RE = re.compile("[" + _COMPOUND_SEPARATORS + "]", re.UNICODE)
_DIGITS_RE = re.compile(r"\d+", re.UNICODE)
_NUMERAL_RE = re.compile(r"\d+(?:\.\d+)*(?:st|nd|rd|th)?", re.IGNORECASE | re.UNICODE)
_ORDINAL_RE = re.compile(r"(\d+)(?:st|nd|rd|th)", re.IGNORECASE | re.UNICODE)
_ROMAN_RE = re.compile(
    r"M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})",
    re.IGNORECASE,
)

#: Clitics that elide before a vowel in French (and, for the Italian/Catalan
#: forms, before any head word). When one of these precedes an apostrophe the
#: token is split so the clitic can be matched against the stop-word registry.
_ELISION_PREFIXES = frozenset(
    {
        "c",
        "d",
        "dall",
        "dell",
        "j",
        "jusqu",
        "l",
        "lorsqu",
        "m",
        "n",
        "nell",
        "presqu",
        "puisqu",
        "qu",
        "quelqu",
        "quoiqu",
        "s",
        "sull",
        "t",
        "un",
    }
)


# ---------------------------------------------------------------------------
# Sentence-splitting inventories
# ---------------------------------------------------------------------------

_TERMINALS = frozenset(".!?\u2026\u3002\uff01\uff1f")
_CLOSERS = frozenset("\"')]}\u2019\u201d\u300d\u300f\u00bb")

#: Lower-cased word forms (trailing period removed) after which a period does
#: *not* end a sentence.
_ABBREVIATIONS = frozenset(
    {
        "a.m",
        "al",
        "apr",
        "approx",
        "art",
        "assn",
        "aug",
        "ave",
        "blvd",
        "bros",
        "ca",
        "cf",
        "ch",
        "chap",
        "co",
        "corp",
        "dec",
        "dept",
        "dr",
        "e.g",
        "ed",
        "eds",
        "eq",
        "eqs",
        "esp",
        "est",
        "feb",
        "fig",
        "figs",
        "i.e",
        "inc",
        "jan",
        "jr",
        "jul",
        "jun",
        "ltd",
        "mar",
        "max",
        "md",
        "min",
        "mr",
        "mrs",
        "ms",
        "mt",
        "no",
        "nos",
        "nov",
        "oct",
        "p",
        "p.m",
        "ph.d",
        "phd",
        "pp",
        "prof",
        "rd",
        "ref",
        "refs",
        "resp",
        "sec",
        "sect",
        "sep",
        "sept",
        "sr",
        "st",
        "trans",
        "u.k",
        "u.s",
        "univ",
        "viz",
        "vol",
        "vols",
        "vs",
    }
)

_ABBREV_TAIL_RE = re.compile(r"(?:[^\W\d_]|\.)+\Z", re.UNICODE)


# ---------------------------------------------------------------------------
# Number spelling tables (0-999 plus ordinals)
# ---------------------------------------------------------------------------

_CARDINAL_ONES = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
)
_CARDINAL_TENS = (
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
)
_ORDINAL_ONES = (
    "zeroth",
    "first",
    "second",
    "third",
    "fourth",
    "fifth",
    "sixth",
    "seventh",
    "eighth",
    "ninth",
    "tenth",
    "eleventh",
    "twelfth",
    "thirteenth",
    "fourteenth",
    "fifteenth",
    "sixteenth",
    "seventeenth",
    "eighteenth",
    "nineteenth",
)
_ORDINAL_TENS = (
    "",
    "",
    "twentieth",
    "thirtieth",
    "fortieth",
    "fiftieth",
    "sixtieth",
    "seventieth",
    "eightieth",
    "ninetieth",
)

_UPPER_CLASS = 0
_LOWER_CLASS = 1
_DIGIT_CLASS = 2
_OTHER_CLASS = 3


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def normalize(text: str) -> str:
    """Return the canonical matching form of ``text``.

    Applies NFKC compatibility composition followed by ``str.casefold``.
    Accents are deliberately *preserved*: they are meaningful for the French,
    Spanish and German lexicons. Use :func:`strip_accents` when a folded,
    accent-free key is required.

    Args:
        text: Arbitrary input string.

    Returns:
        The NFKC-composed, case-folded form.

    Example:
        >>> normalize("Caf\\u00e9 NA\\u00cfVE") == "caf\\u00e9 na\\u00efve"
        True
        >>> normalize("\\uff21\\uff22\\uff23")
        'abc'
    """
    return unicodedata.normalize("NFKC", text).casefold()


def strip_accents(text: str) -> str:
    """Return ``text`` with combining diacritical marks removed.

    Decomposes to NFD, drops every combining mark, then recomposes to NFC so
    the result is a well-formed string.

    Args:
        text: Arbitrary input string.

    Returns:
        The accent-free form; case is untouched.

    Example:
        >>> strip_accents("r\\u00e9sum\\u00e9")
        'resume'
        >>> strip_accents("\\u00dcber")
        'Uber'
    """
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return unicodedata.normalize("NFC", stripped)


def _char_class(char: str) -> int:
    """Classify ``char`` as upper / lower / digit / other (Unicode-aware)."""
    if char.isupper():
        return _UPPER_CLASS
    if char.islower():
        return _LOWER_CLASS
    if char.isdigit():
        return _DIGIT_CLASS
    return _OTHER_CLASS


def split_camel_case(word: str) -> list[str]:
    """Split a camelCase / PascalCase word into its components.

    Boundaries are inserted:

    * before an uppercase letter that follows a lowercase letter or a digit;
    * before the last uppercase letter of an uppercase run that is followed by
      a lowercase letter (so an acronym run stays intact);
    * on either side of a digit run.

    Characters that are neither cased nor digits (apostrophes, CJK ideographs,
    combining marks) never introduce a boundary, which keeps ``"don't"`` and
    ``"O'Brien"`` in one piece.

    Args:
        word: A single word with no separators (callers split on hyphens and
            solidi first).

    Returns:
        The ordered components; ``[]`` for an empty string, ``[word]`` when no
        boundary is found.

    Example:
        >>> split_camel_case("XMLHttpRequest")
        ['XML', 'Http', 'Request']
        >>> split_camel_case("iOS")
        ['i', 'OS']
        >>> split_camel_case("parseJSON")
        ['parse', 'JSON']
        >>> split_camel_case("multi")
        ['multi']
    """
    if not word:
        return []
    segments: list[str] = []
    current: list[str] = []
    previous: Optional[int] = None
    total = len(word)
    for position, char in enumerate(word):
        kind = _char_class(char)
        boundary = False
        if current and previous is not None:
            if kind == _UPPER_CLASS and previous in (_LOWER_CLASS, _DIGIT_CLASS):
                boundary = True
            elif kind == _UPPER_CLASS and previous == _UPPER_CLASS:
                following = _char_class(word[position + 1]) if position + 1 < total else None
                boundary = following == _LOWER_CLASS
            elif (kind == _DIGIT_CLASS and previous in (_UPPER_CLASS, _LOWER_CLASS)) or (
                kind in (_UPPER_CLASS, _LOWER_CLASS) and previous == _DIGIT_CLASS
            ):
                boundary = True
        if boundary:
            segments.append("".join(current))
            current = []
        current.append(char)
        previous = kind
    if current:
        segments.append("".join(current))
    return segments


def is_roman_numeral(word: str) -> bool:
    """Return whether ``word`` is a well-formed Roman numeral (1-3999).

    The test is case-insensitive and strict: ``"IIII"`` and ``"IC"`` are
    rejected, ``"XIV"`` and ``"mcmxc"`` are accepted. The empty string is
    always ``False``.

    Args:
        word: Candidate string.

    Returns:
        ``True`` when the whole string is a canonical Roman numeral.

    Example:
        >>> is_roman_numeral("XIV")
        True
        >>> is_roman_numeral("IIII")
        False
        >>> is_roman_numeral("")
        False
    """
    if not word:
        return False
    return _ROMAN_RE.fullmatch(word) is not None


def _cardinal(number: int) -> str:
    """Spell ``number`` (0-999) as an English cardinal."""
    if number < 20:
        return _CARDINAL_ONES[number]
    if number < 100:
        tens = _CARDINAL_TENS[number // 10]
        remainder = number % 10
        return tens if remainder == 0 else f"{tens}-{_CARDINAL_ONES[remainder]}"
    hundreds = f"{_CARDINAL_ONES[number // 100]} hundred"
    remainder = number % 100
    return hundreds if remainder == 0 else f"{hundreds} {_cardinal(remainder)}"


def _ordinal(number: int) -> str:
    """Spell ``number`` (0-999) as an English ordinal."""
    if number < 20:
        return _ORDINAL_ONES[number]
    if number < 100:
        remainder = number % 10
        if remainder == 0:
            return _ORDINAL_TENS[number // 10]
        return f"{_CARDINAL_TENS[number // 10]}-{_ORDINAL_ONES[remainder]}"
    remainder = number % 100
    if remainder == 0:
        return f"{_CARDINAL_ONES[number // 100]} hundredth"
    return f"{_CARDINAL_ONES[number // 100]} hundred {_ordinal(remainder)}"


def spell_number(value: str) -> Optional[str]:
    """Spell a numeric string in English.

    Coverage is deliberately narrow -- cardinals ``0``-``999`` and their
    ordinal forms -- because the only consumer is
    :attr:`~acronymkit.enums.NumeralPolicy.WORD`, which needs nothing but the
    leading character. Anything outside that range (decimals, grouped
    thousands, non-numeric input) returns ``None``.

    Args:
        value: Candidate numeric string, e.g. ``"7"``, ``"21st"``.

    Returns:
        The spelled form, or ``None`` when ``value`` is not a supported
        numeral.

    Example:
        >>> spell_number("3")
        'three'
        >>> spell_number("1st")
        'first'
        >>> spell_number("21st")
        'twenty-first'
        >>> spell_number("3.5") is None
        True
    """
    text = value.strip()
    if not text:
        return None
    ordinal_match = _ORDINAL_RE.fullmatch(text)
    if ordinal_match is not None:
        number = int(ordinal_match.group(1))
        return _ordinal(number) if 0 <= number <= 999 else None
    if _DIGITS_RE.fullmatch(text) is not None:
        number = int(text)
        return _cardinal(number) if 0 <= number <= 999 else None
    return None


# ---------------------------------------------------------------------------
# Private token helpers
# ---------------------------------------------------------------------------


def _digit_string(value: str) -> str:
    """Return only the decimal digits of ``value``, in order."""
    return "".join(char for char in value if char.isdigit())


def _alphabetic_prefix(value: str, limit: int) -> str:
    """Return the first ``limit`` alphabetic characters of ``value``, uppercased."""
    collected = ""
    for char in value:
        if char.isalpha():
            collected += char.upper()
            if len(collected) >= limit:
                break
    return collected[:limit]


def _component_initial(component: str) -> str:
    """Return the uppercased first alphabetic character of ``component``."""
    for char in component:
        if char.isalpha():
            return char.upper()[:1]
    return ""


def _looks_like_acronym(value: str) -> bool:
    """Return whether ``value`` is an existing all-caps acronym.

    Requires at least two characters, at least one uppercase letter and no
    lowercase letter. A single uppercase letter is explicitly *not* an acronym,
    and caseless scripts (CJK) never qualify.
    """
    if len(value) < 2:
        return False
    if any(char.islower() for char in value):
        return False
    return any(char.isupper() for char in value)


def _split_compound(value: str) -> list[str]:
    """Split ``value`` on hyphen-family separators, solidi and case boundaries."""
    components: list[str] = []
    for piece in _COMPOUND_SPLIT_RE.split(value):
        if piece:
            components.extend(split_camel_case(piece))
    return [component for component in components if component]


def _split_elisions(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """Split an apostrophe-bearing span into elision spans.

    Only the first apostrophe of the span is examined. When the characters
    before it form a known Romance clitic (``l'``, ``d'``, ``qu'`` ...) the span
    is cut in two and the remainder re-examined; otherwise the span is an
    English-style contraction and is returned whole.

    Args:
        text: The original text (offsets are relative to it).
        start: Inclusive start offset of the span.
        end: Exclusive end offset of the span.

    Returns:
        One or more ``(start, end)`` offset pairs covering the span.
    """
    surface = text[start:end]
    for offset, char in enumerate(surface):
        if char in _APOSTROPHES:
            prefix = surface[:offset]
            suffix = surface[offset + 1 :]
            if prefix and suffix and prefix.casefold() in _ELISION_PREFIXES:
                head = [(start, start + offset)]
                return head + _split_elisions(text, start + offset + 1, end)
            break
    return [(start, end)]


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


class Tokenizer:
    """Configuration-driven, deterministic tokenizer.

    A tokenizer is cheap to construct but caches the resolved stop-word
    registry and the derived letter budget, so reuse it across calls. Instances
    hold no mutable state and are safe to share between threads.

    Attributes are exposed read-only through :attr:`config` and
    :attr:`stop_words`.
    """

    __slots__ = ("_config", "_letter_limit", "_stop_words", "_suppressed")

    def __init__(self, config: Config, stop_words: Optional[StopWordRegistry] = None) -> None:
        """Build a tokenizer.

        Args:
            config: Engine configuration. ``language``, ``stop_words_path``,
                ``custom_stop_words`` and ``custom_keep_words`` select the
                stop-word registry when one is not supplied.
            stop_words: Pre-built registry to use instead of loading one.

        Raises:
            ResourceNotFoundError: If no stop-word resource exists for
                ``config.language`` and ``config.strict`` is set. Without
                ``strict`` the tokenizer degrades to an empty registry so that
                Tier 0 generation still works.
        """
        self._config = config
        self._stop_words = stop_words if stop_words is not None else self._load_registry(config)
        self._suppressed = config.suppressed_categories
        self._letter_limit = (
            max(1, config.max_letters_per_token) if config.allow_multi_letter_tokens else 1
        )

    # -- construction ------------------------------------------------------
    @staticmethod
    def _load_registry(config: Config) -> StopWordRegistry:
        """Load the stop-word registry described by ``config``.

        Args:
            config: Engine configuration.

        Returns:
            The configured registry, or an empty one when the resource is
            missing and ``config.strict`` is false.

        Raises:
            ResourceNotFoundError: If the resource is missing under ``strict``.
        """
        try:
            return StopWordRegistry.load(
                config.language,
                path=config.stop_words_path,
                extra=config.custom_stop_words,
                keep=config.custom_keep_words,
            )
        except ResourceNotFoundError:
            if config.strict:
                raise
            return StopWordRegistry.empty(config.language)

    # -- properties --------------------------------------------------------
    @property
    def config(self) -> Config:
        """The configuration this tokenizer was built from."""
        return self._config

    @property
    def stop_words(self) -> StopWordRegistry:
        """The resolved stop-word registry."""
        return self._stop_words

    # -- public API --------------------------------------------------------
    def tokenize(self, text: str) -> list[Token]:
        """Split ``text`` into analysed tokens.

        Punctuation-only runs are discarded; every returned token satisfies
        ``text[token.start:token.end] == token.text``. An empty or
        whitespace-only input returns ``[]`` rather than raising, so the caller
        can decide whether that is an
        :class:`~acronymkit.exceptions.EmptyPhraseError`.

        Args:
            text: Source text.

        Returns:
            The ordered token list.

        Raises:
            TokenizationError: If ``text`` is not a :class:`str`.

        Example:
            >>> from acronymkit.config import Config
            >>> tokenizer = Tokenizer(Config())
            >>> [t.text for t in tokenizer.tokenize("Portable Document Format")]
            ['Portable', 'Document', 'Format']
            >>> [t.letters for t in tokenizer.tokenize("Portable Document Format")]
            ['PO', 'DO', 'FO']

            Compounds keep their parts, existing acronyms are preserved, and
            the offsets round-trip exactly:

            >>> source = "Multi-Factor Authentication (API)"
            >>> tokens = tokenizer.tokenize(source)
            >>> [(t.text, t.role.value, t.letters) for t in tokens]
            [('Multi-Factor', 'content', 'MF'), ('Authentication', 'content', 'AU'), \
('API', 'acronym', 'API')]
            >>> tokens[0].subtokens
            ['Multi', 'Factor']
            >>> all(source[t.start:t.end] == t.text for t in tokens)
            True
        """
        if not isinstance(text, str):
            raise TokenizationError(f"tokenize() expects a str, got {type(text).__name__}")
        if not text.strip():
            return []
        tokens: list[Token] = []
        for match in _TOKEN_RE.finditer(text):
            for start, end in _split_elisions(text, match.start(), match.end()):
                if end > start:
                    tokens.append(self._build_token(text, start, end, len(tokens)))
        return tokens

    def split_sentences(self, text: str) -> list[tuple[int, int]]:
        """Return ``(start, end)`` offsets of each sentence in ``text``.

        A lightweight, dependency-free splitter. A terminal ``.``/``!``/``?``
        (or their CJK equivalents) ends a sentence only when it is followed by
        whitespace or end-of-text and the next non-space character is not
        lowercase. A period additionally does not end a sentence when the
        preceding word is a known abbreviation (``e.g.``, ``i.e.``, ``Dr.``,
        ``Fig.``, ``vs.``, ``et al.``, ``cf.``, ``approx.``, ``No.``) or a
        single initial (``J. R. R.``).

        Leading and trailing whitespace is excluded from every span, so
        ``text[start:end]`` is the trimmed sentence.

        Args:
            text: Source text.

        Returns:
            Ordered, non-overlapping offset pairs; ``[]`` for blank input.

        Example:
            >>> from acronymkit.config import Config
            >>> tokenizer = Tokenizer(Config())
            >>> body = "Dr. Smith works at NASA. He left."
            >>> [body[s:e] for s, e in tokenizer.split_sentences(body)]
            ['Dr. Smith works at NASA.', 'He left.']
        """
        if not isinstance(text, str) or not text.strip():
            return []
        spans: list[tuple[int, int]] = []
        length = len(text)
        start: Optional[int] = None
        position = 0
        while position < length:
            char = text[position]
            if start is None:
                if char.isspace():
                    position += 1
                    continue
                start = position
            if char in _TERMINALS:
                cursor = position + 1
                while cursor < length and text[cursor] in _TERMINALS:
                    cursor += 1
                run_length = cursor - position
                while cursor < length and text[cursor] in _CLOSERS:
                    cursor += 1
                if self._is_sentence_break(text, position, cursor, run_length):
                    spans.append((start, cursor))
                    start = None
                position = cursor
                continue
            position += 1
        if start is not None:
            end = length
            while end > start and text[end - 1].isspace():
                end -= 1
            if end > start:
                spans.append((start, end))
        return spans

    # -- internals ---------------------------------------------------------
    @staticmethod
    def _is_sentence_break(text: str, punct: int, after: int, run_length: int) -> bool:
        """Decide whether the terminator at ``punct`` really ends a sentence.

        Args:
            text: Source text.
            punct: Offset of the first terminator character.
            after: Offset one past the terminator run and any closing quotes.
            run_length: Number of consecutive terminator characters.

        Returns:
            ``True`` when a sentence boundary should be placed at ``after``.
        """
        length = len(text)
        if after < length and not text[after].isspace():
            return False
        cursor = after
        while cursor < length and text[cursor].isspace():
            cursor += 1
        if cursor >= length:
            return True
        if text[cursor].islower():
            return False
        if run_length == 1 and text[punct] == ".":
            tail_match = _ABBREV_TAIL_RE.search(text[:punct])
            if tail_match is not None:
                tail = tail_match.group(0)
                if len(tail) == 1 and tail.isalpha():
                    return False
                if tail.casefold() in _ABBREVIATIONS:
                    return False
        return True

    def _build_token(self, text: str, start: int, end: int, index: int) -> Token:
        """Build one :class:`~acronymkit.models.Token` for ``text[start:end]``.

        Args:
            text: Source text.
            start: Inclusive start offset.
            end: Exclusive end offset.
            index: Zero-based position in the emitted token sequence.

        Returns:
            A fully populated, frozen token.
        """
        surface = text[start:end]
        normalized = normalize(surface)
        config = self._config
        limit = self._letter_limit

        role = TokenRole.CONTENT
        category: Optional[StopWordCategory] = None
        subtokens: list[str] = []
        eligible = True

        if _CJK_RUN_RE.fullmatch(surface) is not None:
            # Caseless scripts have no initial-letter convention: donate the
            # leading character only.
            letters = surface[:1]
        elif _NUMERAL_RE.fullmatch(surface) is not None:
            role = TokenRole.NUMERAL
            letters, eligible = self._numeral_letters(surface)
        elif config.preserve_existing_acronyms and _looks_like_acronym(surface):
            role = TokenRole.ACRONYM
            letters = "".join(char for char in surface if char.isalnum()).upper()
            components = _split_compound(surface)
            if len(components) > 1:
                subtokens = components
        else:
            components = _split_compound(surface)
            if len(components) > 1:
                subtokens = components
            category = self._stop_words.category(normalized)
            if category is not None:
                role = TokenRole.FUNCTION
                eligible = not self._stop_words.is_suppressed(normalized, self._suppressed)
            letters = self._letters_for(surface, components, limit)

        if (
            role not in (TokenRole.ACRONYM, TokenRole.NUMERAL)
            and len(surface) < config.min_word_length
        ):
            eligible = False

        is_critical = role in (TokenRole.CONTENT, TokenRole.ACRONYM) and eligible

        return Token(
            text=surface,
            normalized=normalized,
            index=index,
            start=start,
            end=end,
            role=role,
            stop_word_category=category,
            is_critical=is_critical,
            is_eligible=eligible,
            letters=letters,
            subtokens=subtokens,
        )

    def _numeral_letters(self, surface: str) -> tuple[str, bool]:
        """Return ``(letters, is_eligible)`` for a numeric token.

        ``DIGIT`` donates the token's decimal digits verbatim (``"3.5"`` gives
        ``"35"``), ``WORD`` donates the initial of :func:`spell_number` and
        falls back to the digit string for numbers outside its range, and
        ``SKIP`` donates nothing.

        Args:
            surface: The token's exact surface form.

        Returns:
            The letters the token may donate and whether it stays eligible.
        """
        policy = self._config.numeral_policy
        digits = _digit_string(surface)
        if policy is NumeralPolicy.SKIP:
            return "", False
        if policy is NumeralPolicy.WORD:
            spelled = spell_number(surface)
            if spelled:
                return spelled[0].upper()[:1], True
            return digits, True
        return digits, True

    def _letters_for(self, surface: str, components: list[str], limit: int) -> str:
        """Compute the donatable characters of a non-numeric, non-acronym token.

        Args:
            surface: The token's exact surface form.
            components: Compound components from :func:`_split_compound`.
            limit: Maximum number of characters this token may donate.

        Returns:
            An uppercased character budget of at most ``limit`` characters
            (``FIRST_ONLY`` always yields at most one).
        """
        policy = self._config.hyphen_policy
        if len(components) > 1:
            if policy is HyphenPolicy.FIRST_ONLY:
                return _component_initial(components[0])
            if policy is HyphenPolicy.SPLIT:
                collected = ""
                for component in components:
                    initial = _component_initial(component)
                    if not initial:
                        continue
                    collected += initial
                    if len(collected) >= limit:
                        break
                return collected[:limit]
        return _alphabetic_prefix(surface, limit)

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return (
            f"Tokenizer(language={self._config.language.value!r}, "
            f"hyphen_policy={self._config.hyphen_policy.value!r}, "
            f"numeral_policy={self._config.numeral_policy.value!r})"
        )
