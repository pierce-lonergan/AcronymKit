"""Immutable character-span coordinates, and the one question asked of them.

Why this is in ``core`` and not beside the extractor
----------------------------------------------------
A span is a pair of integers into a string. It is the one piece of vocabulary
the prose half and the identifier half of this package share that carries **no
lexical commitment at all**: it knows nothing about whitespace, punctuation,
casing, ``#``/``%``/``_``/``:``/``/``, or whether the characters between the two
integers are a word, a token or a column name. That is exactly the property
:mod:`acronymkit.core` is defined by, and it is why the type lives here rather
than in the package that happens to produce the most spans.

Nothing in this module compiles a regular expression, normalises a string, or
reads a bundled asset. It slices and it compares integers.

Half-open, always
-----------------
``Span(start, end)`` means ``text[start:end]``, so ``end`` is one past the last
character and ``start == end`` is a legal empty span at a position. Every span
in this package has been half-open since the extractor was written; this module
is the first place that says so in a type rather than in a docstring.

**The wire format did not change.** Every DTO field that held a
``tuple[int, int]`` still holds one -- :attr:`acronymkit.models.AcronymPair.short_form_span`,
:attr:`acronymkit.nlp.propagation.Occurrence.span` and the rest. This type is
the arithmetic's home, not the field's, so no serialised record, no JSON payload
and no benchmark output moves because it exists.

What is deliberately NOT here
-----------------------------
An ``overlaps`` predicate, an ``earliest_start`` reducer and a
``contains``. Each was written, and each was removed before this module shipped
for the same reason: **there is no site in this tree that computes it.** Nothing
in ``extractor.py``, ``propagation.py`` or ``disambiguation.py`` tests two
character spans for intersection -- the one place that looks like it does,
``_overlap_and_evidence``, overlaps *content words* and never touches an offset.
A convenience method with no caller is indistinguishable from a design
commitment nobody made, and this module is small enough that the difference is
visible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .exceptions import TokenizationError

__all__ = ["Span"]


@dataclass(frozen=True, order=True)
class Span:
    """Half-open character offsets into a string.

    Frozen and ordered, so a span is hashable, usable as a dictionary key, and
    sortable in the ``(start, end)`` order every consumer here already sorts by.

    Args:
        start: Index of the first character.
        end: Index one past the last character.

    Raises:
        TokenizationError: If ``start`` is negative or ``end`` precedes
            ``start``. Both are coordinates that cannot describe a substring of
            anything, and a silently-empty slice is how a wrong offset survives
            long enough to become a wrong output.
            :class:`~acronymkit.core.exceptions.TokenizationError` is the right
            base here precisely because it is the one both tokenizers raise and
            neither owns.

    Example:
        >>> span = Span(4, 9)
        >>> span.text_of("the quick brown fox")
        'quick'
        >>> span.as_tuple()
        (4, 9)
        >>> len(span)
        5
        >>> Span(9, 4)
        Traceback (most recent call last):
        acronymkit.core.exceptions.TokenizationError: span end 4 precedes start 9
    """

    start: int
    end: int

    def __post_init__(self) -> None:
        """Refuse coordinates that cannot name a substring."""
        if self.start < 0:
            raise TokenizationError(f"span start may not be negative: {self.start}")
        if self.end < self.start:
            raise TokenizationError(f"span end {self.end} precedes start {self.start}")

    def __len__(self) -> int:
        """Number of characters the span covers."""
        return self.end - self.start

    @classmethod
    def of(cls, span: Tuple[int, int]) -> Span:
        """Build one from the ``tuple[int, int]`` the DTO layer carries.

        Args:
            span: A ``(start, end)`` pair.

        Returns:
            The equivalent :class:`Span`.
        """
        return cls(span[0], span[1])

    def as_tuple(self) -> Tuple[int, int]:
        """Return ``(start, end)``, the form every DTO field stores."""
        return (self.start, self.end)

    def text_of(self, text: str) -> str:
        """Slice ``text`` with these coordinates.

        Args:
            text: The document the coordinates index into.

        Returns:
            ``text[start:end]``. Coordinates past the end of ``text`` slice short
            exactly as Python's own slicing does; this method does not add a
            bounds check its callers never had, because adding one would change
            what they return.
        """
        return text[self.start : self.end]
