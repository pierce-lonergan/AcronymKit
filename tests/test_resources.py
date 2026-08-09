"""Tests for :mod:`acronymkit.resources` and the data files it serves.

Two halves:

1. **API behaviour** -- lookup, caching, mutation isolation, comment/blank-line
   stripping, transparent gunzip, and the ``ResourceNotFoundError`` contract.
2. **Structural validation of every bundled resource** -- the formats frozen in
   the build spec. These assertions are the runtime twin of
   ``tools/validate_resources.py``: a hand-edited data file that violates the
   format fails here rather than silently degrading ``Lambda(A)`` or ``Phi(A)``.

The file is pure ASCII: non-ASCII data is written with escape sequences.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Iterator

import pytest

from acronymkit import resources as resources_module
from acronymkit.enums import Language, StopWordCategory
from acronymkit.exceptions import ResourceNotFoundError
from acronymkit.resources import (
    available_languages,
    has_resource,
    read_json_resource,
    read_lines_resource,
    read_text_resource,
    resource_path,
)
from conftest import LEXICON_LANGUAGES, NGRAM_LANGUAGES, STOPWORD_LANGUAGES

KINDS = ["stopwords", "lexicon", "ngram"]
# Per-resource-kind, because only English ships a lexicon and n-gram model;
# stop words ship for every language. See conftest for why.
BUNDLED_LANGUAGES = list(STOPWORD_LANGUAGES)

STOPWORD_RESOURCES = [f"stopwords_{code}.json" for code in BUNDLED_LANGUAGES]
LEXICON_RESOURCES = [f"lexicon_{code}.txt" for code in LEXICON_LANGUAGES]
NGRAM_RESOURCES = [f"ngram_{code}.json" for code in NGRAM_LANGUAGES]

_LANGUAGES_BY_KIND = {
    "stopwords": STOPWORD_LANGUAGES,
    "lexicon": LEXICON_LANGUAGES,
    "ngram": NGRAM_LANGUAGES,
}
ALL_RESOURCES = STOPWORD_RESOURCES + LEXICON_RESOURCES + NGRAM_RESOURCES

#: Names that must never resolve, either because they are absent or because
#: they try to escape the resource directory.
BAD_NAMES = [
    "definitely_not_a_resource.txt",
    "stopwords_zz.json",
    "lexicon_zz.txt",
    "ngram_zz.json",
    "",
    ".",
    "..",
    "../pyproject.toml",
    "sub/dir.txt",
    "sub\\dir.txt",
]


@pytest.fixture
def fake_resource() -> Iterator[dict]:
    """Serve synthetic bytes under caller-chosen resource names.

    Patches the module's private byte reader so a test can exercise the
    decoding layer (gzip, BOM, UTF-8 validity) without writing into the
    installed package. Every memoised lookup is dropped on the way in and out.
    """
    store: dict = {}
    original = resources_module._read_bytes

    def reader(name: str) -> bytes:
        if name in store:
            return store[name]
        return original(name)

    resources_module._clear_caches()
    resources_module._read_bytes = reader  # type: ignore[assignment]
    try:
        yield store
    finally:
        resources_module._read_bytes = original  # type: ignore[assignment]
        resources_module._clear_caches()


# --------------------------------------------------------------------------
# resource_path
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", ALL_RESOURCES)
def test_resource_path_points_at_a_real_file(name: str) -> None:
    path = resource_path(name)

    assert isinstance(path, Path)
    assert path.is_file()
    assert path.name == name


def test_resource_path_is_memoised() -> None:
    assert resource_path("lexicon_en.txt") is resource_path("lexicon_en.txt")


@pytest.mark.parametrize("name", BAD_NAMES)
def test_resource_path_rejects_unknown_and_escaping_names(name: str) -> None:
    with pytest.raises(ResourceNotFoundError):
        resource_path(name)


# --------------------------------------------------------------------------
# has_resource
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", ALL_RESOURCES)
def test_has_resource_finds_every_bundled_file(name: str) -> None:
    assert has_resource(name) is True


@pytest.mark.parametrize("name", BAD_NAMES)
def test_has_resource_is_false_rather_than_raising(name: str) -> None:
    assert has_resource(name) is False


@pytest.mark.parametrize("value", [None, 42, b"lexicon_en.txt"])
def test_has_resource_is_false_for_non_strings(value: object) -> None:
    assert has_resource(value) is False  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# read_text_resource
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", ALL_RESOURCES)
def test_read_text_resource_returns_non_empty_text(name: str) -> None:
    text = read_text_resource(name)

    assert isinstance(text, str)
    assert text.strip()


def test_read_text_resource_matches_the_file_on_disk() -> None:
    name = "stopwords_en.json"

    assert read_text_resource(name) == resource_path(name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", BAD_NAMES)
def test_read_text_resource_raises_for_bad_names(name: str) -> None:
    with pytest.raises(ResourceNotFoundError):
        read_text_resource(name)


def test_gzipped_resources_are_transparently_decompressed(fake_resource: dict) -> None:
    fake_resource["fake_lexicon.txt.gz"] = gzip.compress(b"alpha\nbravo\n")

    assert read_text_resource("fake_lexicon.txt.gz") == "alpha\nbravo\n"
    assert read_lines_resource("fake_lexicon.txt.gz") == ["alpha", "bravo"]


def test_invalid_gzip_payload_raises(fake_resource: dict) -> None:
    fake_resource["fake_broken.txt.gz"] = b"not gzip at all"

    with pytest.raises(ResourceNotFoundError):
        read_text_resource("fake_broken.txt.gz")


def test_byte_order_mark_is_stripped(fake_resource: dict) -> None:
    fake_resource["fake_bom.txt"] = "\ufeffalpha\n".encode()

    assert read_text_resource("fake_bom.txt") == "alpha\n"


def test_undecodable_bytes_raise(fake_resource: dict) -> None:
    fake_resource["fake_binary.txt"] = b"\xff\xfe\x00binary"

    with pytest.raises(ResourceNotFoundError):
        read_text_resource("fake_binary.txt")


# --------------------------------------------------------------------------
# read_json_resource
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", STOPWORD_RESOURCES + NGRAM_RESOURCES)
def test_read_json_resource_parses_every_json_file(name: str) -> None:
    payload = read_json_resource(name)

    assert isinstance(payload, dict)
    assert payload


def test_read_json_resource_hands_back_a_private_object() -> None:
    """The text is cached but the JSON is re-parsed, so callers cannot alias."""
    first = read_json_resource("ngram_en.json")
    second = read_json_resource("ngram_en.json")

    assert first is not second
    assert first == second

    first["injected"] = True
    assert "injected" not in read_json_resource("ngram_en.json")


def test_read_json_resource_raises_on_malformed_json(fake_resource: dict) -> None:
    fake_resource["fake_bad.json"] = b"{ not json"

    with pytest.raises(ResourceNotFoundError):
        read_json_resource("fake_bad.json")


@pytest.mark.parametrize("name", BAD_NAMES)
def test_read_json_resource_raises_for_bad_names(name: str) -> None:
    with pytest.raises(ResourceNotFoundError):
        read_json_resource(name)


# --------------------------------------------------------------------------
# read_lines_resource
# --------------------------------------------------------------------------
def test_read_lines_resource_strips_comment_and_blank_lines(fake_resource: dict) -> None:
    payload = "# leading comment\n\n   \nalpha\n   # indented comment\nbravo   \n\t\ncharlie\n"
    fake_resource["fake_lines.txt"] = payload.encode("utf-8")

    assert read_lines_resource("fake_lines.txt") == ["alpha", "bravo", "charlie"]


@pytest.mark.parametrize("name", LEXICON_RESOURCES)
def test_bundled_lexicons_lose_exactly_their_comment_and_blank_lines(name: str) -> None:
    raw = read_text_resource(name).splitlines()
    dropped = [line for line in raw if not line.strip() or line.lstrip().startswith("#")]

    lines = read_lines_resource(name)

    assert len(lines) == len(raw) - len(dropped)
    assert dropped, "the bundled lexicons carry an explanatory comment header"
    assert all(line.strip() for line in lines)
    assert not any(line.lstrip().startswith("#") for line in lines)


def test_read_lines_resource_returns_a_fresh_list() -> None:
    first = read_lines_resource("lexicon_en.txt")
    second = read_lines_resource("lexicon_en.txt")

    assert first is not second
    assert first == second

    # The sentinel must be a string the bundled lexicon cannot contain. The
    # original sentinel here was "injected", which is a perfectly good English
    # word and duly appeared once the real SCOWL lexicon replaced the
    # model-authored one -- the test then failed for a reason that had nothing
    # to do with cache aliasing.
    sentinel = "\x00not-a-word-sentinel\x00"
    first.append(sentinel)
    assert sentinel not in read_lines_resource("lexicon_en.txt")


@pytest.mark.parametrize("name", BAD_NAMES)
def test_read_lines_resource_raises_for_bad_names(name: str) -> None:
    with pytest.raises(ResourceNotFoundError):
        read_lines_resource(name)


# --------------------------------------------------------------------------
# available_languages
# --------------------------------------------------------------------------
@pytest.mark.parametrize("kind", KINDS)
def test_available_languages_lists_every_bundled_language(kind: str) -> None:
    assert available_languages(kind) == list(_LANGUAGES_BY_KIND[kind])


@pytest.mark.parametrize("kind", KINDS)
def test_available_languages_reports_what_each_kind_actually_ships(kind: str) -> None:
    """Not every Language has every resource, and the loader must say so.

    Stop words ship for all four languages; lexicons and n-gram models ship for
    English alone, because the French, Spanish and German word lists would have
    to come from copyleft Hunspell dictionaries. Asserting equality with the
    whole ``Language`` enum would re-encode the assumption this release removed.
    """
    reported = available_languages(kind)
    assert reported == list(_LANGUAGES_BY_KIND[kind])
    assert set(reported) <= {language.value for language in Language}
    assert reported == sorted(reported)


def test_available_languages_returns_a_fresh_list() -> None:
    first = available_languages("lexicon")
    second = available_languages("lexicon")

    assert first is not second
    assert first == second

    first.clear()
    assert available_languages("lexicon") == list(LEXICON_LANGUAGES)


@pytest.mark.parametrize("kind", ["", "words", "stopword", "LEXICON", "ngrams"])
def test_available_languages_rejects_unknown_kinds(kind: str) -> None:
    with pytest.raises(ValueError):
        available_languages(kind)


# --------------------------------------------------------------------------
# Structural validation: stop-word resources
# --------------------------------------------------------------------------
@pytest.mark.parametrize("code", BUNDLED_LANGUAGES)
def test_stopword_resource_declares_its_language(code: str) -> None:
    payload = read_json_resource(f"stopwords_{code}.json")

    assert payload["language"] == code
    assert isinstance(payload["categories"], dict)


@pytest.mark.parametrize("code", BUNDLED_LANGUAGES)
def test_stopword_resource_has_exactly_the_eight_categories(code: str) -> None:
    categories = read_json_resource(f"stopwords_{code}.json")["categories"]

    assert set(categories) == {member.value for member in StopWordCategory}
    assert all(categories[key] for key in categories), "no category may be empty"


@pytest.mark.parametrize("code", BUNDLED_LANGUAGES)
def test_stopword_categories_are_disjoint(code: str) -> None:
    categories = read_json_resource(f"stopwords_{code}.json")["categories"]
    seen: dict = {}
    for key, words in categories.items():
        for word in words:
            assert word not in seen, f"{word!r} is in both {seen.get(word)!r} and {key!r}"
            seen[word] = key


@pytest.mark.parametrize("code", BUNDLED_LANGUAGES)
def test_stopword_categories_are_sorted_deduped_and_lowercase(code: str) -> None:
    categories = read_json_resource(f"stopwords_{code}.json")["categories"]
    for key, words in categories.items():
        assert all(isinstance(word, str) for word in words), key
        assert words == sorted(words), f"{key} is not sorted"
        assert len(set(words)) == len(words), f"{key} has duplicates"
        assert all(word == word.lower() for word in words), f"{key} is not lowercase"
        assert all(word.strip() == word and word for word in words), key


# --------------------------------------------------------------------------
# Structural validation: lexicons
# --------------------------------------------------------------------------
@pytest.mark.parametrize("code", LEXICON_LANGUAGES)
def test_lexicon_is_sorted_unique_and_non_empty(code: str) -> None:
    words = read_lines_resource(f"lexicon_{code}.txt")

    assert words
    assert words == sorted(words), "lexicon must be sorted ascending"
    assert len(set(words)) == len(words), "lexicon must be deduplicated"


@pytest.mark.parametrize("code", LEXICON_LANGUAGES)
def test_lexicon_entries_are_lowercase_letters_only(code: str) -> None:
    for word in read_lines_resource(f"lexicon_{code}.txt"):
        assert word == word.strip()
        assert word.isalpha(), f"{word!r} contains non-letters"
        assert word == word.lower(), f"{word!r} is not lowercase"


# --------------------------------------------------------------------------
# Structural validation: n-gram models
# --------------------------------------------------------------------------
NGRAM_REQUIRED_KEYS = {
    "language",
    "order",
    "alphabet",
    "boundary_start",
    "boundary_end",
    "backoff_log_prob",
    "vocabulary_size",
    "transitions",
}


@pytest.mark.parametrize("code", NGRAM_LANGUAGES)
def test_ngram_header_fields(code: str) -> None:
    payload = read_json_resource(f"ngram_{code}.json")

    assert set(payload) >= NGRAM_REQUIRED_KEYS
    assert payload["language"] == code
    assert payload["order"] == 2
    assert payload["boundary_start"] == "^"
    assert payload["boundary_end"] == "$"
    assert payload["vocabulary_size"] > 0
    assert payload["backoff_log_prob"] < 0.0


@pytest.mark.parametrize("code", NGRAM_LANGUAGES)
def test_ngram_alphabet_is_sorted_and_deduplicated(code: str) -> None:
    alphabet = read_json_resource(f"ngram_{code}.json")["alphabet"]

    assert alphabet
    assert list(alphabet) == sorted(alphabet)
    assert len(set(alphabet)) == len(alphabet)
    assert all(char.isalpha() and char == char.lower() for char in alphabet)


@pytest.mark.parametrize("code", NGRAM_LANGUAGES)
def test_ngram_log_probabilities_are_non_positive(code: str) -> None:
    """These are natural-log conditional probabilities, so every value is <= 0."""
    payload = read_json_resource(f"ngram_{code}.json")
    for context, row in payload["transitions"].items():
        for successor, log_prob in row.items():
            assert isinstance(log_prob, float), (context, successor)
            assert log_prob <= 0.0, f"log P({successor!r}|{context!r}) = {log_prob}"


@pytest.mark.parametrize("code", NGRAM_LANGUAGES)
def test_ngram_transitions_are_consistent_with_the_alphabet(code: str) -> None:
    payload = read_json_resource(f"ngram_{code}.json")
    alphabet = set(payload["alphabet"])
    start = payload["boundary_start"]
    end = payload["boundary_end"]
    transitions = payload["transitions"]

    assert set(transitions) == alphabet | {start}, "every context must be a known symbol"
    assert end not in transitions, "the end boundary is never a context"
    for context, row in transitions.items():
        assert set(row) == alphabet | {end}, f"row {context!r} is not dense over the alphabet"
        assert start not in row, "the start boundary is never a successor"


@pytest.mark.parametrize("code", LEXICON_LANGUAGES)
def test_ngram_alphabet_matches_the_lexicon_it_was_trained_on(code: str) -> None:
    """``CharNGramModel.train`` derives the alphabet from the case-folded corpus."""
    payload = read_json_resource(f"ngram_{code}.json")
    words = read_lines_resource(f"lexicon_{code}.txt")
    folded = {char for word in words for char in word.casefold() if char.isalpha()}

    assert set(payload["alphabet"]) == folded
    assert payload["vocabulary_size"] == len(words)


@pytest.mark.parametrize("name", NGRAM_RESOURCES)
def test_ngram_files_are_valid_utf8_json_on_disk(name: str) -> None:
    on_disk = json.loads(resource_path(name).read_text(encoding="utf-8"))

    assert on_disk == read_json_resource(name)
