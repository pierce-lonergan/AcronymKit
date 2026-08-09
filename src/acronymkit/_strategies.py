"""Parameterised short-form/long-form matching strategies.

Background
----------
Schwartz & Hearst apply exactly one matching rule. Ab3P (Sohn et al., 2008)
applies seventeen, ordered by estimated reliability, and takes the first that
succeeds — which is why it recovers definitions the single greedy rule
truncates or misses. This module supplies the strategy family; the ordering
comes from :mod:`acronymkit._pseudo_precision`.

Relationship to Ab3P
--------------------
This is **not** a transcription of Ab3P's seventeen rules. Their names
(``FirstLet``, ``FirstLetGenStp``, ``WithinWrdFLetSkp``, ``ContLetSkp``,
``AnyLet``, …) decompose into a small number of orthogonal dimensions, and a
parameterised family spanning those dimensions is easier to reason about, easier
to test, and — critically — lets the reliability of each dimension be measured
rather than inherited. Ab3P's published table is used only to sanity-check that
our derived ordering agrees with theirs.

The dimensions, recovered from their naming:

``anchor``
    Where the *first* short-form character may sit. Schwartz & Hearst require a
    word initial; that constraint is what gives the method its precision.
``placement``
    Where subsequent characters may sit: word initials only, anywhere inside a
    word, or contiguously inside one word.
``skip``
    Which long-form words may be passed over without contributing: none, stop
    words only, or any.
``plural_s``
    Whether a trailing ``s`` on the short form may match a plural ``s`` that the
    long form spells on a different word.

Tier 0 pure: standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import cache
from typing import Optional, Sequence

__all__ = [
    "STRATEGIES",
    "Alignment",
    "Anchor",
    "Placement",
    "Skip",
    "Strategy",
    "best_match",
    "split_long_form",
]

#: Function words a ``Skip.STOP_WORDS`` strategy may pass over. Deliberately
#: small: these are the words an author actually omits when coining an acronym
#: ("National Aeronautics *and* Space Administration" -> NASA).
SKIPPABLE = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "into",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
)


class Anchor(str, Enum):
    """Where the first short-form character is permitted to match."""

    WORD_INITIAL = "word_initial"
    ANYWHERE = "anywhere"


class Placement(str, Enum):
    """Where the remaining short-form characters may match."""

    WORD_INITIAL = "word_initial"
    WITHIN_WORD = "within_word"
    CONTIGUOUS = "contiguous"


class Skip(str, Enum):
    """Which long-form words may contribute nothing."""

    NONE = "none"
    STOP_WORDS = "stop_words"
    ANY = "any"


@dataclass(frozen=True)
class Strategy:
    """One matching rule.

    Attributes:
        name: Stable identifier; used as the key for its estimated precision.
        anchor: Constraint on the first short-form character.
        placement: Constraint on subsequent characters.
        skip: Which words may be passed over.
        plural_s: Whether a trailing ``s`` may match a plural elsewhere.
    """

    name: str
    anchor: Anchor
    placement: Placement
    skip: Skip
    plural_s: bool = False

    @property
    def strictness(self) -> tuple[int, int, int, int]:
        """A total order from most to least constrained.

        Used only as a deterministic tie-break when two strategies have
        identical estimated precision; the ordering that matters is measured.
        """
        return (
            0 if self.anchor is Anchor.WORD_INITIAL else 1,
            {Placement.WORD_INITIAL: 0, Placement.CONTIGUOUS: 1, Placement.WITHIN_WORD: 2}[
                self.placement
            ],
            {Skip.NONE: 0, Skip.STOP_WORDS: 1, Skip.ANY: 2}[self.skip],
            1 if self.plural_s else 0,
        )


@dataclass(frozen=True)
class Alignment:
    """A successful match of a short form onto long-form words.

    Attributes:
        strategy: The rule that produced it.
        word_span: ``(first, last)`` indices of the long-form words used,
            inclusive. The long form is the slice they delimit.
        positions: ``(word_index, char_index)`` per short-form character.
    """

    strategy: str
    word_span: tuple[int, int]
    positions: tuple[tuple[int, int], ...]

    @property
    def initial_count(self) -> int:
        """How many short-form characters landed on a word initial."""
        return sum(1 for _, char_index in self.positions if char_index == 0)


def split_long_form(text: str) -> list[tuple[str, int, int]]:
    """Split ``text`` into ``(word, start, end)`` triples.

    Words break on whitespace and on hyphens and slashes, mirroring the
    reference implementation's tokenizer so that ``"non-Hodgkin lymphoma"``
    counts as three words.

    Args:
        text: The candidate long-form window.

    Returns:
        Non-empty words with their character offsets into ``text``.
    """
    words: list[tuple[str, int, int]] = []
    start: Optional[int] = None
    for index, character in enumerate(text):
        if character.isalnum():
            if start is None:
                start = index
        elif start is not None:
            words.append((text[start:index], start, index))
            start = None
    if start is not None:
        words.append((text[start:], start, len(text)))
    return words


def _skippable(word: str, skip: Skip) -> bool:
    """Whether ``word`` may contribute nothing under ``skip``."""
    if skip is Skip.ANY:
        return True
    if skip is Skip.STOP_WORDS:
        return word.casefold() in SKIPPABLE
    return False


def match(
    short_form: str, words: Sequence[str], strategy: Strategy, start: int = 0
) -> Optional[tuple[tuple[int, int], ...]]:
    """Attempt to align ``short_form`` onto ``words[start:]`` under ``strategy``.

    The search is a depth-first walk over ``(character, word, offset)`` states,
    memoised, so its cost is polynomial rather than exponential in the number of
    words.

    ``start`` matters. A long form is a *suffix* of the candidate window: the
    window is a fixed span of preceding text and the definition occupies only its
    tail. Words before ``start`` are outside the long form entirely and are not
    subject to the skip policy — requiring them to be skippable would mean only
    ``Skip.ANY`` strategies could ever fire on a wide window, which is precisely
    the bug this parameter fixes. From ``start`` onward every word must either
    contribute a character or be skippable, and the last word must contribute.

    Args:
        short_form: Alphanumeric short form, already case-folded.
        words: Case-folded window words.
        strategy: The rule to apply.
        start: Index of the first long-form word.

    Returns:
        ``(word_index, char_index)`` per short-form character, or ``None`` when
        no alignment exists.
    """
    characters = [c for c in short_form if c.isalnum()]
    if not characters or not words or start >= len(words):
        return None

    target = list(characters)
    if strategy.plural_s and len(target) > 1 and target[-1] == "s":
        target = target[:-1]  # the plural is carried by the long form, not matched

    word_count = len(words)

    @cache
    def solve(
        char_index: int, word_index: int, offset: int, used_current: bool
    ) -> Optional[tuple[tuple[int, int], ...]]:
        if char_index == len(target):
            # Every remaining word must be skippable, and the current word must
            # have contributed something.
            if not used_current:
                return None
            for remaining in range(word_index + 1, word_count):
                if not _skippable(words[remaining], strategy.skip):
                    return None
            return ()
        if word_index >= word_count:
            return None

        wanted = target[char_index]
        word = words[word_index]
        results: Optional[tuple[tuple[int, int], ...]] = None

        # -- consume `wanted` from the current word -------------------------
        first = char_index == 0
        if first:
            allowed = range(1) if strategy.anchor is Anchor.WORD_INITIAL else range(len(word))
        elif strategy.placement is Placement.WORD_INITIAL:
            allowed = range(1) if offset == 0 else range(0)
        elif strategy.placement is Placement.CONTIGUOUS:
            allowed = range(offset, offset + 1) if used_current else range(len(word))
        else:
            allowed = range(offset, len(word))

        for position in allowed:
            if position < len(word) and word[position] == wanted:
                tail = solve(char_index + 1, word_index, position + 1, True)
                if tail is not None:
                    results = ((word_index, position), *tail)
                    break
                # or continue this character's run in the next word
                tail = solve(char_index + 1, word_index + 1, 0, False)
                if tail is not None:
                    results = ((word_index, position), *tail)
                    break
        if results is not None:
            return results

        # -- move to the next word ------------------------------------------
        if used_current or _skippable(word, strategy.skip):
            return solve(char_index, word_index + 1, 0, False)
        return None

    try:
        return solve(0, start, 0, False)
    finally:
        solve.cache_clear()


def _build_strategies() -> tuple[Strategy, ...]:
    """Enumerate the strategy family.

    The cross product of the dimensions, minus combinations that are either
    degenerate or strictly dominated. ``Anchor.ANYWHERE`` with
    ``Placement.WITHIN_WORD`` and ``Skip.ANY`` is the loosest rule expressible —
    Ab3P's ``AnyLet``, whose measured precision is the lowest of their set.
    """
    strategies: list[Strategy] = []
    for anchor in Anchor:
        for placement in Placement:
            for skip in Skip:
                for plural in (False, True):
                    # A word-initial placement with no anchor constraint is the
                    # same rule twice; keep the anchored form only.
                    if anchor is Anchor.ANYWHERE and placement is Placement.WORD_INITIAL:
                        continue
                    name = "_".join(
                        [
                            "anch" + ("Init" if anchor is Anchor.WORD_INITIAL else "Any"),
                            {
                                Placement.WORD_INITIAL: "placeInit",
                                Placement.WITHIN_WORD: "placeWithin",
                                Placement.CONTIGUOUS: "placeCont",
                            }[placement],
                            {
                                Skip.NONE: "skipNone",
                                Skip.STOP_WORDS: "skipStop",
                                Skip.ANY: "skipAny",
                            }[skip],
                        ]
                        + (["plural"] if plural else [])
                    )
                    strategies.append(Strategy(name, anchor, placement, skip, plural))
    return tuple(sorted(strategies, key=lambda s: s.strictness))


#: The strategy family, ordered by structural strictness. The *applied* order is
#: by measured precision; see :mod:`acronymkit._pseudo_precision`.
STRATEGIES: tuple[Strategy, ...] = _build_strategies()


def best_match(
    short_form: str, words: Sequence[str], strategy: Strategy
) -> Optional[tuple[tuple[int, int], ...]]:
    """Find the alignment beginning as early in the window as ``strategy`` allows.

    Earliest-first is the deliberate choice, and it is where this differs from
    the reference algorithm. Schwartz & Hearst walks right-to-left and accepts
    the first alignment it reaches, which is by construction the *shortest* — the
    behaviour that truncates ``"International Index of Erectile Function"`` to
    ``"Index of Erectile Function"``.

    Preferring the earliest start does not simply grab more text, because the
    strategy still has to be satisfied across everything from that start onward.
    Under ``Skip.NONE`` an over-long span fails immediately, since some word
    would contribute nothing. The constraint does the limiting; the preference
    only decides among spans that are all valid.

    Args:
        short_form: Case-folded short form.
        words: Case-folded window words.
        strategy: The rule to apply.

    Returns:
        Positions for the earliest valid alignment, or ``None``.
    """
    for start in reversed(range(len(words))):
        positions = match(short_form, words, strategy, start)
        if positions is not None:
            return positions
    return None
