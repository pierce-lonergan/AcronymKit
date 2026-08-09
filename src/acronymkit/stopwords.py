"""Categorised stop-word registry.

Unlike a flat stop-word list, :class:`StopWordRegistry` remembers *which
grammatical class* every function word belongs to. That is what lets
:attr:`~acronymkit.config.Config.suppressed_categories` toggle articles,
prepositions, conjunctions, pronouns and auxiliaries independently: a token is
only barred from donating letters when its category is in the suppressed set.

Resource format (see the build spec) is a JSON document of the shape::

    {"language": "en", "categories": {"article": ["a", "an", "the"], ...}}

with one list per :class:`~acronymkit.enums.StopWordCategory` value.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from contextlib import suppress
from functools import cache
from pathlib import Path
from typing import AbstractSet, Any, Optional

from .enums import Language, StopWordCategory
from .exceptions import AcronymKitError, ResourceNotFoundError
from .resources import read_json_resource

__all__ = ["StopWordRegistry"]

#: Template for the bundled per-language stop-word resource.
_RESOURCE_TEMPLATE = "stopwords_{language}.json"


def _normalise(word: str) -> str:
    """Return the case-insensitive lookup key for ``word``."""
    return word.strip().casefold()


def _coerce_category(key: object, source: str) -> StopWordCategory:
    """Coerce a resource key to a :class:`StopWordCategory`.

    Args:
        key: Raw mapping key read from the resource.
        source: Human-readable resource name, used in error messages.

    Returns:
        The matching category member.

    Raises:
        AcronymKitError: If ``key`` names no known category.
    """
    try:
        return StopWordCategory.coerce(key)
    except ValueError as exc:
        raise AcronymKitError(
            f"Stop-word resource {source!r} contains unknown category {key!r}"
        ) from exc


def _categories_from_payload(
    payload: object, source: str
) -> dict[StopWordCategory, frozenset[str]]:
    """Extract the ``category -> words`` mapping from a parsed resource.

    Accepts either the canonical ``{"categories": {...}}`` envelope or a bare
    ``{category: [words]}`` mapping.

    Args:
        payload: Parsed JSON document.
        source: Human-readable resource name, used in error messages.

    Returns:
        A mapping of category to frozen set of casefolded words.

    Raises:
        AcronymKitError: If the document is not shaped like a stop-word
            resource, or names an unknown category.
    """
    if isinstance(payload, Mapping) and isinstance(payload.get("categories"), Mapping):
        raw = payload["categories"]
    elif isinstance(payload, Mapping):
        raw = payload
    else:
        raise AcronymKitError(
            f"Stop-word resource {source!r} must be a JSON object, got {type(payload).__name__}"
        )

    categories: dict[StopWordCategory, set[str]] = {}
    for key, value in raw.items():
        if key in {"language", "description", "version", "source"}:
            continue
        if isinstance(value, str) or not isinstance(value, Iterable):
            raise AcronymKitError(
                f"Stop-word resource {source!r} category {key!r} must be a list of words"
            )
        category = _coerce_category(key, source)
        bucket = categories.setdefault(category, set())
        for word in value:
            if not isinstance(word, str):
                raise AcronymKitError(
                    f"Stop-word resource {source!r} category {key!r} contains a "
                    f"non-string entry {word!r}"
                )
            normalised = _normalise(word)
            if normalised:
                bucket.add(normalised)
    return {category: frozenset(words) for category, words in categories.items()}


class StopWordRegistry:
    """Immutable, case-insensitive lookup of categorised function words.

    Instances are hashable-free but effectively immutable: the constructor
    copies every input into frozen containers, so a registry produced by
    :meth:`load` can be cached and shared across threads.

    Precedence rules:

    * ``keep`` wins over everything. A kept word reports
      :meth:`category` ``is None`` and :meth:`is_suppressed` ``False`` even when
      the bundled resource lists it.
    * ``extra`` wins over the bundled categories and is reported as
      :attr:`~acronymkit.enums.StopWordCategory.OTHER`, which
      :attr:`~acronymkit.config.Config.suppressed_categories` always suppresses.
    """

    __slots__ = ("_categories", "_extra", "_keep", "_language", "_lookup", "_words")

    def __init__(
        self,
        language: Language,
        categories: Mapping[StopWordCategory, frozenset[str]],
        *,
        extra: Iterable[str] = (),
        keep: Iterable[str] = (),
    ) -> None:
        """Build a registry from an in-memory category mapping.

        Args:
            language: Language the word lists describe.
            categories: Mapping of category to the words in that category.
                Keys may be :class:`~acronymkit.enums.StopWordCategory` members
                or their string values; words are casefolded on the way in.
            extra: Additional words to suppress, treated as
                :attr:`~acronymkit.enums.StopWordCategory.OTHER`.
            keep: Words that must never be suppressed, overriding both the
                bundled categories and ``extra``.

        Raises:
            AcronymKitError: If a category key is not a known
                :class:`~acronymkit.enums.StopWordCategory`.
        """
        self._language: Language = Language.coerce(language)
        self._keep: frozenset[str] = frozenset(key for key in (_normalise(w) for w in keep) if key)
        self._extra: frozenset[str] = frozenset(
            key for key in (_normalise(w) for w in extra) if key
        )

        lookup: dict[str, StopWordCategory] = {}
        for raw_category, words in categories.items():
            category = _coerce_category(raw_category, "<in-memory>")
            for word in words:
                key = _normalise(word)
                if key:
                    lookup[key] = category
        for key in self._extra:
            lookup[key] = StopWordCategory.OTHER
        for key in self._keep:
            lookup.pop(key, None)

        self._lookup: dict[str, StopWordCategory] = lookup
        self._words: frozenset[str] = frozenset(lookup)
        grouped: dict[StopWordCategory, set[str]] = {}
        for key, category in lookup.items():
            grouped.setdefault(category, set()).add(key)
        self._categories: dict[StopWordCategory, frozenset[str]] = {
            category: frozenset(words) for category, words in grouped.items()
        }

    # -- construction ------------------------------------------------------
    @classmethod
    def load(
        cls,
        language: Language,
        *,
        path: Optional[Path] = None,
        extra: Iterable[str] = (),
        keep: Iterable[str] = (),
    ) -> StopWordRegistry:
        """Load (and memoise) the registry for a language.

        The result is cached on ``(cls, language, str(path), frozenset(extra),
        frozenset(keep))``, so repeated engine construction with the same
        configuration reuses one instance.

        Args:
            language: Language whose bundled resource should be read.
            path: Optional override pointing at a JSON stop-word file.
            extra: Additional words to suppress, treated as ``OTHER``.
            keep: Words that must never be suppressed.

        Returns:
            A shared, immutable :class:`StopWordRegistry`.

        Raises:
            ResourceNotFoundError: If no resource exists for ``language``, or
                ``path`` does not point at a readable file.
            AcronymKitError: If the resource is malformed.
        """
        resolved = Language.coerce(language)
        owner: Any = cls  # class objects are hashable; typed loosely for the cache wrapper
        return _load_registry(
            owner,
            resolved,
            None if path is None else str(path),
            frozenset(_normalise(w) for w in extra),
            frozenset(_normalise(w) for w in keep),
        )

    @classmethod
    def from_path(
        cls,
        path: Path,
        language: Language = Language.EN,
        *,
        extra: Iterable[str] = (),
        keep: Iterable[str] = (),
    ) -> StopWordRegistry:
        """Build a registry from a JSON file on disk.

        Args:
            path: Location of the stop-word JSON document.
            language: Language recorded on the registry; a ``"language"`` key
                inside the document takes precedence when it is valid.
            extra: Additional words to suppress, treated as ``OTHER``.
            keep: Words that must never be suppressed.

        Returns:
            A new :class:`StopWordRegistry`.

        Raises:
            ResourceNotFoundError: If the file is missing or unreadable.
            AcronymKitError: If the document is malformed.
        """
        source = Path(path)
        try:
            text = source.read_text(encoding="utf-8")
        except OSError as exc:
            raise ResourceNotFoundError(
                f"Stop-word resource {source!s} could not be read: {exc}"
            ) from exc
        try:
            payload = json.loads(text)
        except ValueError as exc:
            raise AcronymKitError(
                f"Stop-word resource {source!s} is not valid JSON: {exc}"
            ) from exc
        return cls._from_payload(payload, str(source), language, extra=extra, keep=keep)

    @classmethod
    def bundled(
        cls,
        language: Language = Language.EN,
        *,
        extra: Iterable[str] = (),
        keep: Iterable[str] = (),
    ) -> StopWordRegistry:
        """Build a registry from the resource bundled for ``language``.

        Args:
            language: Language whose bundled resource should be read.
            extra: Additional words to suppress, treated as ``OTHER``.
            keep: Words that must never be suppressed.

        Returns:
            A new :class:`StopWordRegistry`.

        Raises:
            ResourceNotFoundError: If no resource is bundled for ``language``.
            AcronymKitError: If the resource is malformed.
        """
        resolved: Language = Language.coerce(language)
        name = _RESOURCE_TEMPLATE.format(language=resolved.value)
        payload = read_json_resource(name)
        return cls._from_payload(payload, name, resolved, extra=extra, keep=keep)

    @classmethod
    def empty(cls, language: Language = Language.EN) -> StopWordRegistry:
        """Return a registry that recognises no stop words at all.

        Args:
            language: Language recorded on the registry.

        Returns:
            An empty :class:`StopWordRegistry`.
        """
        return cls(Language.coerce(language), {})

    @classmethod
    def _from_payload(
        cls,
        payload: object,
        source: str,
        language: Language,
        *,
        extra: Iterable[str] = (),
        keep: Iterable[str] = (),
    ) -> StopWordRegistry:
        """Build a registry from an already-parsed JSON document."""
        resolved: Language = Language.coerce(language)
        if isinstance(payload, Mapping):
            declared = payload.get("language")
            if isinstance(declared, str):
                with suppress(ValueError):
                    resolved = Language.coerce(declared)
        categories = _categories_from_payload(payload, source)
        return cls(resolved, categories, extra=extra, keep=keep)

    # -- lookups -----------------------------------------------------------
    def category(self, word: str) -> Optional[StopWordCategory]:
        """Return the grammatical class of ``word``.

        Args:
            word: Surface form; matched case-insensitively.

        Returns:
            The word's :class:`~acronymkit.enums.StopWordCategory`, or ``None``
            when it is not a stop word (including every ``keep`` word).
        """
        return self._lookup.get(_normalise(word))

    def is_stop_word(self, word: str) -> bool:
        """Return whether ``word`` is a known stop word.

        Args:
            word: Surface form; matched case-insensitively.

        Returns:
            ``True`` when the word has a category, ``False`` otherwise.
        """
        return _normalise(word) in self._lookup

    def is_suppressed(self, word: str, suppressed: AbstractSet[StopWordCategory]) -> bool:
        """Return whether ``word`` is barred from donating acronym letters.

        Args:
            word: Surface form; matched case-insensitively.
            suppressed: Categories excluded by the active configuration,
                typically :attr:`acronymkit.config.Config.suppressed_categories`.

        Returns:
            ``True`` only when the word is a stop word *and* its category is in
            ``suppressed``. ``keep`` words always return ``False``; ``extra``
            words are evaluated as
            :attr:`~acronymkit.enums.StopWordCategory.OTHER`.
        """
        category = self._lookup.get(_normalise(word))
        if category is None or not suppressed:
            return False
        if category in suppressed:
            return True
        # Tolerate a set of plain strings; str-enum members compare by value.
        return any(category == entry for entry in suppressed)

    def words_in(self, category: StopWordCategory) -> frozenset[str]:
        """Return every word belonging to ``category``.

        Args:
            category: Category to inspect.

        Returns:
            A frozen set of casefolded words; empty when the category is unused.
        """
        resolved = StopWordCategory.coerce(category)
        return self._categories.get(resolved, frozenset())

    # -- properties --------------------------------------------------------
    @property
    def words(self) -> frozenset[str]:
        """Every casefolded stop word, excluding ``keep`` overrides."""
        return self._words

    @property
    def language(self) -> Language:
        """Language these word lists describe."""
        return self._language

    @property
    def categories(self) -> dict[StopWordCategory, frozenset[str]]:
        """A fresh ``category -> words`` mapping (the registry keeps its own copy)."""
        return dict(self._categories)

    @property
    def keep_words(self) -> frozenset[str]:
        """Casefolded words that are never suppressed."""
        return self._keep

    @property
    def extra_words(self) -> frozenset[str]:
        """Casefolded caller-supplied words treated as ``OTHER``."""
        return self._extra

    # -- dunder ------------------------------------------------------------
    def __contains__(self, word: object) -> bool:
        """Return whether ``word`` is a stop word (case-insensitive)."""
        return isinstance(word, str) and self.is_stop_word(word)

    def __len__(self) -> int:
        """Return the number of distinct stop words."""
        return len(self._words)

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return (
            f"StopWordRegistry(language={self._language.value!r}, "
            f"words={len(self._words)}, keep={len(self._keep)})"
        )


@cache
def _load_registry(
    cls: Any,
    language: Language,
    path: Optional[str],
    extra: frozenset[str],
    keep: frozenset[str],
) -> StopWordRegistry:
    """Memoised backing implementation of :meth:`StopWordRegistry.load`.

    Args:
        cls: The (sub)class being constructed; part of the cache key.
        language: Resolved language.
        path: Stringified override path, or ``None`` for the bundled resource.
        extra: Frozen set of already-normalised extra stop words.
        keep: Frozen set of already-normalised keep words.

    Returns:
        The shared registry instance for this key.

    Raises:
        ResourceNotFoundError: If the resource cannot be found or read.
        AcronymKitError: If the resource is malformed.
    """
    if path is not None:
        return cls.from_path(Path(path), language, extra=extra, keep=keep)
    return cls.bundled(language, extra=extra, keep=keep)
