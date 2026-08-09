"""Tests for :mod:`acronymkit.stopwords`.

The registry is what makes ``Config.include_articles`` / ``include_prepositions``
/ ... independently toggleable, so the behaviour pinned here is:

* ``load`` memoises on the full ``(language, path, extra, keep)`` key;
* lookups are case-insensitive and category-accurate;
* ``extra`` words behave as :attr:`StopWordCategory.OTHER`;
* ``keep`` words beat both the bundled data and ``extra``, in ``category()``
  *and* in ``is_suppressed()``;
* ``is_suppressed`` consults only the category set it is handed.

The file is pure ASCII: non-ASCII data is written with escape sequences.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import AbstractSet, Optional

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from acronymkit import stopwords as stopwords_module
from acronymkit.enums import Language, StopWordCategory
from acronymkit.exceptions import AcronymKitError, ResourceNotFoundError
from acronymkit.stopwords import StopWordRegistry

ALL_CATEGORIES = frozenset(StopWordCategory)
NO_CATEGORIES: frozenset = frozenset()

EN = StopWordRegistry.load(Language.EN)

#: Sampled from the bundled English resource; verified against it below.
ENGLISH_CATEGORY_CASES = [
    ("the", StopWordCategory.ARTICLE),
    ("a", StopWordCategory.ARTICLE),
    ("an", StopWordCategory.ARTICLE),
    ("of", StopWordCategory.PREPOSITION),
    ("in", StopWordCategory.PREPOSITION),
    ("with", StopWordCategory.PREPOSITION),
    ("and", StopWordCategory.CONJUNCTION),
    ("or", StopWordCategory.CONJUNCTION),
    ("but", StopWordCategory.CONJUNCTION),
    ("it", StopWordCategory.PRONOUN),
    ("they", StopWordCategory.PRONOUN),
    ("is", StopWordCategory.AUXILIARY),
    ("are", StopWordCategory.AUXILIARY),
    ("was", StopWordCategory.AUXILIARY),
    ("this", StopWordCategory.DETERMINER),
    ("these", StopWordCategory.DETERMINER),
    ("not", StopWordCategory.PARTICLE),
    ("up", StopWordCategory.PARTICLE),
]


def _write_resource(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# load() caching
# --------------------------------------------------------------------------
def test_load_memoises_on_the_language() -> None:
    assert StopWordRegistry.load(Language.EN) is StopWordRegistry.load(Language.EN)


def test_load_accepts_a_plain_language_string() -> None:
    assert StopWordRegistry.load("en") is StopWordRegistry.load(Language.EN)


def test_load_cache_key_includes_extra_and_keep() -> None:
    plain = StopWordRegistry.load(Language.EN)
    with_extra = StopWordRegistry.load(Language.EN, extra=["widgetword"])
    with_keep = StopWordRegistry.load(Language.EN, keep=["the"])

    assert with_extra is not plain
    assert with_keep is not plain
    assert with_extra is not with_keep


def test_load_cache_key_is_normalised_so_equivalent_calls_share_an_instance() -> None:
    """Order, container type and casing of ``extra`` must not fork the cache."""
    first = StopWordRegistry.load(Language.EN, extra=["Alpha", "BETA"])
    second = StopWordRegistry.load(Language.EN, extra=("beta", "alpha"))

    assert first is second


def test_bundled_is_not_memoised() -> None:
    """``bundled`` is the uncached constructor behind ``load``."""
    assert StopWordRegistry.bundled(Language.EN) is not StopWordRegistry.bundled(Language.EN)


def test_load_with_a_path_reads_that_file(tmp_path: Path) -> None:
    resource = _write_resource(
        tmp_path / "stopwords_custom.json",
        {"language": "en", "categories": {"article": ["zed"], "other": ["quux"]}},
    )

    registry = StopWordRegistry.load(Language.EN, path=resource)

    assert registry.words == frozenset({"zed", "quux"})
    assert registry.category("ZED") is StopWordCategory.ARTICLE
    assert registry is StopWordRegistry.load(Language.EN, path=Path(str(resource)))


# --------------------------------------------------------------------------
# Case-insensitive lookup
# --------------------------------------------------------------------------
@pytest.mark.parametrize("surface", ["the", "The", "THE", "tHe", "  the  ", "\tTHE\n"])
def test_lookup_is_case_insensitive_and_whitespace_tolerant(surface: str) -> None:
    assert EN.category(surface) is StopWordCategory.ARTICLE
    assert EN.is_stop_word(surface) is True
    assert surface in EN
    assert EN.is_suppressed(surface, {StopWordCategory.ARTICLE}) is True


def test_contains_rejects_non_strings() -> None:
    assert 42 not in EN
    assert None not in EN


def test_len_matches_the_word_set() -> None:
    assert len(EN) == len(EN.words)
    assert len(EN) > 0


# --------------------------------------------------------------------------
# category()
# --------------------------------------------------------------------------
@pytest.mark.parametrize(("word", "category"), ENGLISH_CATEGORY_CASES)
def test_category_of_bundled_english_words(word: str, category: StopWordCategory) -> None:
    assert EN.category(word) is category
    assert word in EN.words_in(category)


@pytest.mark.parametrize("word", ["acronym", "quantum", "zebra", "", "   ", "notarealstopword"])
def test_category_is_none_for_non_stop_words(word: str) -> None:
    assert EN.category(word) is None
    assert EN.is_stop_word(word) is False
    assert EN.is_suppressed(word, ALL_CATEGORIES) is False


def test_categories_partition_the_word_set() -> None:
    """Every word has exactly one category; the buckets tile ``words``."""
    buckets = EN.categories
    union: set = set()
    total = 0
    for words in buckets.values():
        assert union.isdisjoint(words)
        union |= set(words)
        total += len(words)

    assert union == set(EN.words)
    assert total == len(EN.words)


def test_categories_property_returns_a_private_copy() -> None:
    snapshot = EN.categories
    snapshot.pop(StopWordCategory.ARTICLE, None)

    assert StopWordCategory.ARTICLE in EN.categories


def test_words_in_returns_empty_for_an_unused_category() -> None:
    registry = StopWordRegistry(Language.EN, {StopWordCategory.ARTICLE: frozenset({"the"})})

    assert registry.words_in(StopWordCategory.PRONOUN) == frozenset()
    assert registry.words_in("article") == frozenset({"the"})


# --------------------------------------------------------------------------
# extra words
# --------------------------------------------------------------------------
def test_extra_words_are_reported_as_other() -> None:
    registry = StopWordRegistry.load(Language.EN, extra=["Widget", "GADGET"])

    assert registry.category("widget") is StopWordCategory.OTHER
    assert registry.category("gadget") is StopWordCategory.OTHER
    assert registry.extra_words == frozenset({"widget", "gadget"})
    assert {"widget", "gadget"} <= set(registry.words)


def test_extra_words_are_suppressed_only_via_the_other_category() -> None:
    registry = StopWordRegistry.load(Language.EN, extra=["widget"])

    assert registry.is_suppressed("widget", {StopWordCategory.OTHER}) is True
    assert registry.is_suppressed("widget", {StopWordCategory.ARTICLE}) is False
    assert registry.is_suppressed("widget", NO_CATEGORIES) is False


def test_extra_overrides_a_bundled_category() -> None:
    registry = StopWordRegistry.load(Language.EN, extra=["the"])

    assert registry.category("the") is StopWordCategory.OTHER
    assert registry.is_suppressed("the", {StopWordCategory.ARTICLE}) is False
    assert registry.is_suppressed("the", {StopWordCategory.OTHER}) is True


# --------------------------------------------------------------------------
# keep words
# --------------------------------------------------------------------------
@pytest.mark.parametrize("kept", ["the", "The", "THE"])
def test_keep_word_overrides_the_bundled_data(kept: str) -> None:
    registry = StopWordRegistry.load(Language.EN, keep=[kept])

    assert registry.category("the") is None
    assert registry.is_stop_word("the") is False
    assert "the" not in registry.words
    assert registry.is_suppressed("the", ALL_CATEGORIES) is False
    assert registry.keep_words == frozenset({"the"})


def test_keep_word_beats_extra() -> None:
    registry = StopWordRegistry.load(Language.EN, extra=["widget"], keep=["widget"])

    assert registry.category("widget") is None
    assert registry.is_suppressed("widget", ALL_CATEGORIES) is False
    assert "widget" not in registry.words


def test_keep_words_leave_other_words_alone() -> None:
    registry = StopWordRegistry.load(Language.EN, keep=["the"])

    assert registry.category("of") is StopWordCategory.PREPOSITION
    assert registry.is_suppressed("of", {StopWordCategory.PREPOSITION}) is True


# --------------------------------------------------------------------------
# is_suppressed()
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("word", "suppressed", "expected"),
    [
        ("the", {StopWordCategory.ARTICLE}, True),
        ("the", {StopWordCategory.PREPOSITION}, False),
        ("of", {StopWordCategory.PREPOSITION}, True),
        ("of", {StopWordCategory.ARTICLE, StopWordCategory.CONJUNCTION}, False),
        ("and", {StopWordCategory.CONJUNCTION}, True),
        ("it", {StopWordCategory.PRONOUN}, True),
        ("is", {StopWordCategory.AUXILIARY}, True),
        ("this", {StopWordCategory.DETERMINER}, True),
        ("not", {StopWordCategory.PARTICLE}, True),
        ("the", frozenset(), False),
        ("acronym", ALL_CATEGORIES, False),
    ],
)
def test_is_suppressed_consults_only_the_supplied_set(
    word: str, suppressed: AbstractSet[StopWordCategory], expected: bool
) -> None:
    assert EN.is_suppressed(word, suppressed) is expected


def test_is_suppressed_tolerates_plain_string_categories() -> None:
    """``str``-enum members compare by value, so a set of strings still works."""
    assert EN.is_suppressed("the", {"article"}) is True
    assert EN.is_suppressed("the", {"preposition"}) is False


def test_empty_suppressed_set_never_suppresses() -> None:
    for word in ("the", "of", "and", "it", "is", "this", "not"):
        assert EN.is_suppressed(word, NO_CATEGORIES) is False


@settings(max_examples=200, deadline=None)
@given(st.sampled_from(sorted(EN.words)))
def test_every_registered_word_is_categorised_and_suppressible(word: str) -> None:
    category = EN.category(word)
    assert category is not None
    assert EN.is_stop_word(word) is True
    assert EN.is_suppressed(word, {category}) is True
    assert EN.is_suppressed(word, ALL_CATEGORIES) is True
    assert EN.is_suppressed(word.upper(), ALL_CATEGORIES) is True


# --------------------------------------------------------------------------
# Bundled languages
# --------------------------------------------------------------------------
@pytest.mark.parametrize("language", list(Language))
def test_every_bundled_language_loads(language: Language) -> None:
    registry = StopWordRegistry.load(language)

    assert registry.language is language
    assert len(registry) > 0
    assert all(word == word.casefold() for word in registry.words)
    assert all(word.strip() == word for word in registry.words)


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("category", list(StopWordCategory))
def test_every_bundled_language_populates_every_category(
    language: Language, category: StopWordCategory
) -> None:
    assert StopWordRegistry.load(language).words_in(category)


@pytest.mark.parametrize("language", list(Language))
def test_bundled_language_categories_are_disjoint(language: Language) -> None:
    registry = StopWordRegistry.load(language)
    seen: set = set()
    for words in registry.categories.values():
        assert seen.isdisjoint(words)
        seen |= set(words)

    assert seen == set(registry.words)


# --------------------------------------------------------------------------
# Missing / malformed resources
# --------------------------------------------------------------------------
def test_missing_bundled_resource_raises_resource_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unknown language resource must surface as ``ResourceNotFoundError``."""
    monkeypatch.setattr(stopwords_module, "_RESOURCE_TEMPLATE", "stopwords_absent_{language}.json")

    with pytest.raises(ResourceNotFoundError):
        StopWordRegistry.bundled(Language.EN)


def test_unknown_language_code_never_reaches_the_loader() -> None:
    """``Language.coerce`` rejects unknown codes before any resource lookup."""
    with pytest.raises(ValueError):
        StopWordRegistry.load("zz")


def test_missing_override_path_raises_resource_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "not_there.json"

    with pytest.raises(ResourceNotFoundError):
        StopWordRegistry.from_path(missing)
    with pytest.raises(ResourceNotFoundError):
        StopWordRegistry.load(Language.EN, path=missing)


def test_directory_instead_of_file_raises_resource_not_found(tmp_path: Path) -> None:
    with pytest.raises(ResourceNotFoundError):
        StopWordRegistry.from_path(tmp_path)


def test_invalid_json_raises_acronymkit_error(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")

    with pytest.raises(AcronymKitError):
        StopWordRegistry.from_path(broken)


@pytest.mark.parametrize(
    "payload",
    [
        {"categories": {"nonsense": ["x"]}},
        {"categories": {"article": "the"}},
        {"categories": {"article": [1, 2]}},
        ["not", "a", "mapping"],
    ],
)
def test_malformed_payloads_raise_acronymkit_error(tmp_path: Path, payload: object) -> None:
    resource = _write_resource(tmp_path / "bad.json", payload)

    with pytest.raises(AcronymKitError):
        StopWordRegistry.from_path(resource)


def test_unknown_category_key_in_memory_raises() -> None:
    with pytest.raises(AcronymKitError):
        StopWordRegistry(Language.EN, {"nonsense": frozenset({"x"})})


# --------------------------------------------------------------------------
# from_path / constructor behaviour
# --------------------------------------------------------------------------
def test_from_path_accepts_the_canonical_envelope(tmp_path: Path) -> None:
    resource = _write_resource(
        tmp_path / "stopwords_fr.json",
        {
            "language": "fr",
            "description": "ignored",
            "categories": {
                "article": ["le", "la"],
                "preposition": ["de"],
            },
        },
    )

    registry = StopWordRegistry.from_path(resource, Language.EN)

    # The document's own ``language`` key wins over the argument.
    assert registry.language is Language.FR
    assert registry.category("LE") is StopWordCategory.ARTICLE
    assert registry.category("de") is StopWordCategory.PREPOSITION
    assert registry.words == frozenset({"le", "la", "de"})


def test_from_path_accepts_a_bare_category_mapping(tmp_path: Path) -> None:
    resource = _write_resource(tmp_path / "bare.json", {"article": ["the"], "particle": ["not"]})

    registry = StopWordRegistry.from_path(resource, Language.EN)

    assert registry.language is Language.EN
    assert registry.category("the") is StopWordCategory.ARTICLE
    assert registry.category("not") is StopWordCategory.PARTICLE


def test_constructor_accepts_string_category_keys() -> None:
    registry = StopWordRegistry(
        Language.EN, {"article": frozenset({"THE"}), "particle": frozenset({" not "})}
    )

    assert registry.category("the") is StopWordCategory.ARTICLE
    assert registry.category("not") is StopWordCategory.PARTICLE


def test_empty_registry_recognises_nothing() -> None:
    registry = StopWordRegistry.empty(Language.DE)

    assert registry.language is Language.DE
    assert len(registry) == 0
    assert registry.words == frozenset()
    assert registry.category("der") is None
    assert registry.is_suppressed("der", ALL_CATEGORIES) is False


def test_german_sharp_s_folds_to_the_ascii_lookup_key() -> None:
    """``casefold`` maps the sharp s to ``ss``; both spellings must resolve."""
    registry = StopWordRegistry.load(Language.DE)
    sharp_s_word = "au\u00dfer"  # "ausser"
    category: Optional[StopWordCategory] = registry.category(sharp_s_word)

    assert category is not None
    assert registry.category("ausser") is category
