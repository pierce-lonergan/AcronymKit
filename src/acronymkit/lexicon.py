"""Word lists backing the lexical term ``Lambda(A)`` of the scoring function.

:class:`Lexicon` is a read-only, case-insensitive membership oracle over a
frozen set of casefolded words, plus two immutable indexes that make the
"which words have length *n*" and "which words start with *p*" queries cheap
enough to sit inside a search loop.

Design contract:

* **Immutable and thread-safe.** Every index is built once in
  :meth:`Lexicon.__init__` and never mutated afterwards, so instances need no
  locking and can be shared freely between threads and cached engines.
* **Graceful degradation.** :meth:`Lexicon.load` never raises because a
  language has no bundled ``lexicon_<lang>.txt``; it returns
  :meth:`Lexicon.empty` instead, which makes ``Lambda(A)`` evaluate to ``0.0``
  rather than aborting generation. An *explicit* path supplied through
  :attr:`acronymkit.config.Config.lexicon_path` is a caller promise, so an
  unreadable or malformed file there raises
  :class:`~acronymkit.exceptions.LexiconError`.
* **Deterministic.** Iteration and every returned tuple are in ascending
  lexicographic order of the casefolded form.

Resource format (see the build spec): plain UTF-8, one lowercase word per
line, sorted ascending, no duplicates. A leading ``#`` comment block is
permitted and blank lines are ignored.

Note:
    Words are stored casefolded, not merely lowercased. For German this means
    ``"straße"`` is indexed as ``"strasse"`` -- but because lookups are
    casefolded too, ``"Straße" in lexicon`` still answers correctly. Length and
    prefix indexes are keyed by the casefolded form.
"""

from __future__ import annotations

import bisect
from collections.abc import Iterable, Iterator
from functools import cache
from pathlib import Path
from typing import Any, Optional

from .enums import Language
from .exceptions import LexiconError, ResourceNotFoundError
from .resources import read_lines_resource

__all__ = ["Lexicon"]

#: Template for the bundled per-language lexicon resource.
_RESOURCE_TEMPLATE = "lexicon_{language}.txt"

#: Lines whose first non-whitespace character is this are comments.
_COMMENT_PREFIX = "#"


def _normalise(word: str) -> str:
    """Return the case-insensitive lookup key for ``word``.

    Args:
        word: Surface form, possibly padded with whitespace.

    Returns:
        The stripped, casefolded form used as the storage and lookup key.
    """
    return word.strip().casefold()


def _entries_from_lines(lines: Iterable[str], source: str) -> list[str]:
    """Parse lexicon file lines into validated word entries.

    Blank lines and ``#`` comment lines are skipped. Applied to *file* sources
    only: in-memory construction via :meth:`Lexicon.__init__` deliberately
    trusts its caller and performs no format validation.

    Args:
        lines: Raw lines, in file order.
        source: Human-readable origin used in error messages.

    Returns:
        The surviving entries, in file order.

    Raises:
        LexiconError: If an entry contains internal whitespace, which means the
            file is not the documented one-word-per-line format (for example a
            tab-separated frequency list).
    """
    entries: list[str] = []
    for number, raw in enumerate(lines, start=1):
        entry = raw.strip()
        if not entry or entry.startswith(_COMMENT_PREFIX):
            continue
        if any(char.isspace() for char in entry):
            raise LexiconError(
                f"Lexicon source {source!s} line {number} is malformed: expected one "
                f"word per line, got {entry!r}"
            )
        entries.append(entry)
    return entries


class Lexicon:
    """An immutable, case-insensitive dictionary of known words.

    The backing store is a :class:`frozenset` of casefolded words. Two derived
    indexes are materialised once at construction time:

    * ``length -> tuple(words)`` powering :meth:`words_of_length`;
    * ``first letter -> tuple(words)`` powering :meth:`starting_with`, which
      narrows a multi-character prefix inside the bucket with :mod:`bisect`.

    Both index values are sorted, so every public accessor returns results in a
    stable order without sorting at call time.

    Example:
        >>> lexicon = Lexicon(["Radar", "sonar", " lidar "], Language.EN)
        >>> "RADAR" in lexicon
        True
        >>> lexicon.words_of_length(5)
        ('lidar', 'radar', 'sonar')
        >>> lexicon.starting_with("s")
        ('sonar',)
    """

    __slots__ = ("_by_length", "_by_prefix", "_language", "_sorted", "_words")

    def __init__(self, words: Iterable[str], language: Language = Language.EN) -> None:
        """Build a lexicon from an in-memory word list.

        Entries are stripped and casefolded; blank entries and duplicates are
        discarded. The iterable is consumed exactly once.

        Args:
            words: Words to admit. Order is irrelevant; the lexicon re-sorts.
            language: Language the word list describes. Accepts a
                :class:`~acronymkit.enums.Language` member or its string value.

        Raises:
            LexiconError: If ``words`` yields a non-string entry.
            ValueError: If ``language`` names no known language.
        """
        self._language: Language = Language.coerce(language)

        unique: set[str] = set()
        for word in words:
            if not isinstance(word, str):
                raise LexiconError(
                    f"Lexicon entries must be strings, got {type(word).__name__}: {word!r}"
                )
            key = _normalise(word)
            if key:
                unique.add(key)

        self._words: frozenset[str] = frozenset(unique)
        self._sorted: tuple[str, ...] = tuple(sorted(unique))

        by_length: dict[int, list[str]] = {}
        by_prefix: dict[str, list[str]] = {}
        for word in self._sorted:
            by_length.setdefault(len(word), []).append(word)
            by_prefix.setdefault(word[0], []).append(word)
        self._by_length: dict[int, tuple[str, ...]] = {
            size: tuple(bucket) for size, bucket in by_length.items()
        }
        self._by_prefix: dict[str, tuple[str, ...]] = {
            letter: tuple(bucket) for letter, bucket in by_prefix.items()
        }

    # -- construction ------------------------------------------------------
    @classmethod
    def load(cls, language: Language = Language.EN, *, path: Optional[Path] = None) -> Lexicon:
        """Load (and memoise) the lexicon for a language.

        The result is cached on ``(cls, language, str(path) or None)``, so
        repeated engine construction with the same configuration reuses one
        instance and reads the file once.

        Missing bundled data is **not** an error: a language with no bundled
        ``lexicon_<lang>.txt`` yields :meth:`empty`, which degrades
        ``Lambda(A)`` to ``0.0``. Nothing is logged; the engine is responsible
        for surfacing a warning. An explicit ``path`` is held to a higher
        standard and propagates its failure.

        Args:
            language: Language whose bundled resource should be read.
            path: Optional override pointing at a UTF-8 word-list file,
                typically :attr:`acronymkit.config.Config.lexicon_path`.

        Returns:
            A shared, immutable :class:`Lexicon`.

        Raises:
            LexiconError: If ``path`` is given and is unreadable or malformed.
            ValueError: If ``language`` names no known language.
        """
        resolved: Language = Language.coerce(language)
        owner: Any = cls  # class objects are hashable; typed loosely for the cache wrapper
        return _load_lexicon(owner, resolved, None if path is None else str(path))

    @classmethod
    def bundled(cls, language: Language = Language.EN) -> Lexicon:
        """Build a lexicon from the resource bundled for ``language``.

        Args:
            language: Language whose bundled resource should be read.

        Returns:
            A new :class:`Lexicon`.

        Raises:
            ResourceNotFoundError: If no lexicon is bundled for ``language``.
            LexiconError: If the bundled resource is not one word per line.
            ValueError: If ``language`` names no known language.
        """
        resolved: Language = Language.coerce(language)
        name = _RESOURCE_TEMPLATE.format(language=resolved.value)
        lines = read_lines_resource(name)
        return cls(_entries_from_lines(lines, name), resolved)

    @classmethod
    def from_path(cls, path: Path, language: Language = Language.EN) -> Lexicon:
        """Build a lexicon from a word-list file on disk.

        Blank lines and lines whose first non-whitespace character is ``#`` are
        skipped, matching the bundled resource format.

        Args:
            path: Location of the UTF-8 word list.
            language: Language recorded on the lexicon.

        Returns:
            A new :class:`Lexicon`.

        Raises:
            LexiconError: If the file is missing, unreadable, not valid UTF-8,
                or not in the documented one-word-per-line format.
            ValueError: If ``language`` names no known language.
        """
        source = Path(path)
        try:
            text = source.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise LexiconError(f"Lexicon file {source!s} is not valid UTF-8: {exc}") from exc
        except OSError as exc:
            raise LexiconError(f"Lexicon file {source!s} could not be read: {exc}") from exc
        return cls(_entries_from_lines(text.splitlines(), str(source)), language)

    @classmethod
    def empty(cls, language: Language = Language.EN) -> Lexicon:
        """Return a lexicon containing no words at all.

        Used as the graceful-degradation value when a language has no bundled
        word list; every membership test is ``False`` so ``Lambda(A) == 0.0``.

        Args:
            language: Language recorded on the lexicon.

        Returns:
            An empty :class:`Lexicon`.
        """
        return cls((), language)

    # -- lookups -----------------------------------------------------------
    def contains(self, word: str) -> bool:
        """Return whether ``word`` is in the lexicon.

        Args:
            word: Surface form; matched case-insensitively and tolerant of
                surrounding whitespace.

        Returns:
            ``True`` when the word is known, ``False`` otherwise (including for
            the empty string).
        """
        return _normalise(word) in self._words

    def words_of_length(self, n: int) -> tuple[str, ...]:
        """Return every word of exactly ``n`` characters.

        Backed by an index built at construction time, so the call is a single
        dictionary lookup rather than a scan.

        Args:
            n: Word length, measured on the casefolded form.

        Returns:
            An ascending tuple of words; empty when no word has that length or
            ``n`` is not positive.
        """
        return self._by_length.get(n, ())

    def starting_with(self, prefix: str) -> tuple[str, ...]:
        """Return every word beginning with ``prefix``.

        A single-character prefix is an O(1) index lookup. Longer prefixes
        binary-search the (already sorted) first-letter bucket, so the cost is
        logarithmic in the bucket size plus the number of results.

        Args:
            prefix: Prefix to match; casefolded and stripped before comparison.

        Returns:
            An ascending tuple of matching words. An empty or whitespace-only
            prefix returns every word in the lexicon.
        """
        key = _normalise(prefix)
        if not key:
            return self._sorted
        bucket = self._by_prefix.get(key[0], ())
        if len(key) == 1:
            return bucket
        start = bisect.bisect_left(bucket, key)
        end = start
        while end < len(bucket) and bucket[end].startswith(key):
            end += 1
        return bucket[start:end]

    # -- properties --------------------------------------------------------
    @property
    def language(self) -> Language:
        """Language this word list describes."""
        return self._language

    @property
    def words(self) -> frozenset[str]:
        """Every casefolded word, as an immutable set."""
        return self._words

    @property
    def lengths(self) -> tuple[int, ...]:
        """Ascending word lengths present in the lexicon."""
        return tuple(sorted(self._by_length))

    # -- dunder ------------------------------------------------------------
    def __contains__(self, word: object) -> bool:
        """Return whether ``word`` is a known word (case-insensitive).

        Args:
            word: Any object; non-strings are never members.

        Returns:
            ``True`` when ``word`` is a string present in the lexicon.
        """
        return isinstance(word, str) and self.contains(word)

    def __len__(self) -> int:
        """Return the number of distinct words."""
        return len(self._words)

    def __iter__(self) -> Iterator[str]:
        """Iterate the words in ascending lexicographic order."""
        return iter(self._sorted)

    def __bool__(self) -> bool:
        """Return whether the lexicon holds at least one word."""
        return bool(self._words)

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return f"Lexicon(language={self._language.value!r}, words={len(self._words)})"


@cache
def _load_lexicon(cls: Any, language: Language, path: Optional[str]) -> Lexicon:
    """Memoised backing implementation of :meth:`Lexicon.load`.

    Args:
        cls: The (sub)class being constructed; part of the cache key.
        language: Resolved language.
        path: Stringified override path, or ``None`` for the bundled resource.

    Returns:
        The shared lexicon instance for this key.

    Raises:
        LexiconError: If ``path`` is not ``None`` and cannot be read or parsed.
            A failure of the *bundled* lookup is swallowed and degrades to
            :meth:`Lexicon.empty`.
    """
    if path is not None:
        return cls.from_path(Path(path), language)
    try:
        return cls.bundled(language)
    except (ResourceNotFoundError, LexiconError, OSError, ValueError):
        return cls.empty(language)


def _clear_caches() -> None:
    """Drop every memoised :meth:`Lexicon.load` result.

    Intended for tests and for tooling that writes resource files inside a live
    interpreter; not part of the public API.
    """
    _load_lexicon.cache_clear()
