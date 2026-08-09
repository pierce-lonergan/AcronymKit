"""Behavioural tests for :mod:`acronymkit.lexicon`.

The lexicon backs the ``Lambda(A)`` term of the scoring function, so the
properties that matter are (a) membership is a *case- and whitespace-
insensitive* oracle, (b) every accessor is deterministic and sorted, (c)
``load`` memoises, and (d) a missing bundled resource degrades to an empty
lexicon while an explicit bad ``path`` is a hard error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from acronymkit import lexicon as lexicon_module
from acronymkit.enums import Language
from acronymkit.exceptions import LexiconError, ResourceNotFoundError
from acronymkit.lexicon import Lexicon
from conftest import CANONICAL_ACRONYMS

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
#: Words spelled the same way in the bundled English lexicon as they appear as
#: canonical acronyms. Derived from the shared corpus so that a change to
#: ``CANONICAL_ACRONYMS`` cannot silently orphan this test.
_ACRONYMS_THAT_ARE_WORDS = frozenset({"LASER", "RADAR", "SCUBA", "SOAP", "RAM"})


class _UnbundledLexicon(Lexicon):
    """A :class:`Lexicon` whose bundled resource is always missing.

    Exercises the graceful-degradation branch of ``Lexicon.load`` without
    monkeypatching module globals or clearing the shared ``load`` cache (both
    of which would leak into other test modules). ``Lexicon.load`` keys its
    cache on the class, so this subclass gets its own cache entries.
    """

    @classmethod
    def bundled(cls, language: Language = Language.EN) -> Lexicon:
        """Always fail, as though no ``lexicon_<lang>.txt`` were shipped."""
        raise ResourceNotFoundError(f"no bundled lexicon for {language}")


def _expected_entries(words: Iterable[str]) -> list[str]:
    """Return the words a :class:`Lexicon` built from ``words`` must hold."""
    return sorted({word.strip().casefold() for word in words if word.strip()})


#: Word-ish strings with deliberate case and padding noise.
_word_strategy = st.text(alphabet="abcABz ", max_size=6)
_word_list_strategy = st.lists(_word_strategy, max_size=20)

#: Wall-clock health checks are about the host, not about the library.
_PROPERTY_SETTINGS = settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])


# ---------------------------------------------------------------------------
# construction from an in-memory iterable
# ---------------------------------------------------------------------------
def test_construction_from_iterable_normalises_entries() -> None:
    lexicon = Lexicon(["Radar", "sonar", " lidar ", "RADAR", "", "   "])
    assert list(lexicon) == ["lidar", "radar", "sonar"]
    assert len(lexicon) == 3
    assert lexicon.language is Language.EN


def test_construction_consumes_a_one_shot_iterable() -> None:
    lexicon = Lexicon(iter(["beta", "alpha", "alpha"]))
    assert list(lexicon) == ["alpha", "beta"]


def test_construction_accepts_a_language_alias() -> None:
    assert Lexicon((), "fr").language is Language.FR
    assert Lexicon((), Language.DE).language is Language.DE


def test_construction_rejects_an_unknown_language() -> None:
    with pytest.raises(ValueError, match="not a valid Language"):
        Lexicon((), "klingon")


@pytest.mark.parametrize("bad", [1, None, b"bytes", 3.5])
def test_construction_rejects_non_string_entries(bad: object) -> None:
    with pytest.raises(LexiconError, match="must be strings"):
        Lexicon(["alpha", bad])  # type: ignore[list-item]


@pytest.mark.parametrize(
    "probe",
    ["radar", "RADAR", "Radar", "  radar  ", "\tRaDaR\n"],
)
def test_membership_is_case_insensitive_and_whitespace_tolerant(probe: str) -> None:
    lexicon = Lexicon(["Radar", "sonar"])
    assert probe in lexicon
    assert lexicon.contains(probe)


@pytest.mark.parametrize("probe", ["", "   ", "rada", "radars", "zzz"])
def test_non_members_are_rejected(probe: str) -> None:
    lexicon = Lexicon(["Radar", "sonar"])
    assert probe not in lexicon
    assert not lexicon.contains(probe)


@pytest.mark.parametrize("probe", [1, None, b"radar", ("radar",)])
def test_contains_is_false_for_non_strings(probe: object) -> None:
    assert probe not in Lexicon(["radar"])


def test_bool_reflects_emptiness() -> None:
    assert not Lexicon(())
    assert Lexicon(["alpha"])
    assert not Lexicon.empty(Language.ES)
    assert Lexicon.empty(Language.ES).language is Language.ES


def test_words_property_is_an_immutable_snapshot() -> None:
    lexicon = Lexicon(["Alpha", "beta"])
    assert lexicon.words == frozenset({"alpha", "beta"})
    assert isinstance(lexicon.words, frozenset)


# ---------------------------------------------------------------------------
# load(): caching and graceful degradation
# ---------------------------------------------------------------------------
def test_load_returns_the_identical_object_for_the_same_key(english_lexicon: Lexicon) -> None:
    assert Lexicon.load(Language.EN) is english_lexicon
    assert Lexicon.load(Language.EN) is Lexicon.load(Language.EN)
    # ``Language.coerce`` runs before the cache lookup, so a plain string key
    # must land on the very same entry.
    assert Lexicon.load("en") is english_lexicon


def test_load_keys_on_language_and_path(tmp_lexicon_file: Path) -> None:
    assert Lexicon.load(Language.EN) is not Lexicon.load(Language.FR)
    from_path = Lexicon.load(Language.EN, path=tmp_lexicon_file)
    assert from_path is Lexicon.load(Language.EN, path=Path(str(tmp_lexicon_file)))
    assert from_path is not Lexicon.load(Language.EN)
    assert from_path is not Lexicon.load(Language.FR, path=tmp_lexicon_file)


def test_load_without_a_bundled_resource_degrades_to_empty() -> None:
    degraded = _UnbundledLexicon.load(Language.FR)
    assert len(degraded) == 0
    assert list(degraded) == []
    assert degraded.language is Language.FR
    assert "chat" not in degraded
    # Still memoised on the degraded value.
    assert _UnbundledLexicon.load(Language.FR) is degraded


def test_bundled_propagates_a_missing_resource(monkeypatch: pytest.MonkeyPatch) -> None:
    """``bundled`` is the strict accessor; only ``load`` softens the failure."""

    def _boom(name: str) -> list[str]:
        raise ResourceNotFoundError(name)

    monkeypatch.setattr(lexicon_module, "read_lines_resource", _boom)
    with pytest.raises(ResourceNotFoundError):
        Lexicon.bundled(Language.EN)


# ---------------------------------------------------------------------------
# explicit paths are a caller promise: failures are hard errors
# ---------------------------------------------------------------------------
def test_load_with_a_missing_path_raises_lexicon_error(tmp_path: Path) -> None:
    missing = tmp_path / "nope.txt"
    with pytest.raises(LexiconError, match="could not be read"):
        Lexicon.load(Language.EN, path=missing)


def test_load_with_a_malformed_path_raises_lexicon_error(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.txt"
    malformed.write_text("alpha\nbeta\tgamma\n", encoding="utf-8")
    with pytest.raises(LexiconError, match="line 2 is malformed"):
        Lexicon.load(Language.EN, path=malformed)


def test_from_path_rejects_non_utf8_bytes(tmp_path: Path) -> None:
    binary = tmp_path / "binary.txt"
    binary.write_bytes(b"alpha\n\xff\xfe\x00\n")
    with pytest.raises(LexiconError, match="not valid UTF-8"):
        Lexicon.from_path(binary)


def test_from_path_rejects_a_directory(tmp_path: Path) -> None:
    with pytest.raises(LexiconError, match="could not be read"):
        Lexicon.from_path(tmp_path)


def test_malformed_path_reports_the_offending_line_number(tmp_path: Path) -> None:
    malformed = tmp_path / "late.txt"
    malformed.write_text("# header\n\nalpha\nbravo\ntwo words\n", encoding="utf-8")
    with pytest.raises(LexiconError, match="line 5 is malformed"):
        Lexicon.from_path(malformed)


# ---------------------------------------------------------------------------
# indexes: words_of_length / starting_with / iteration
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def sample_lexicon() -> Lexicon:
    """A small, hand-checkable lexicon."""
    return Lexicon(
        ["scale", "scan", "scam", "sonar", "radar", "ram", "lidar", "sc", "SCALE"],
        Language.EN,
    )


@pytest.mark.parametrize(
    ("length", "expected"),
    [
        (0, ()),
        (-1, ()),
        (2, ("sc",)),
        (3, ("ram",)),
        (4, ("scam", "scan")),
        (5, ("lidar", "radar", "scale", "sonar")),
        (9, ()),
    ],
)
def test_words_of_length_is_exact_and_sorted(
    sample_lexicon: Lexicon, length: int, expected: tuple[str, ...]
) -> None:
    assert sample_lexicon.words_of_length(length) == expected


@pytest.mark.parametrize(
    ("prefix", "expected"),
    [
        ("s", ("sc", "scale", "scam", "scan", "sonar")),
        ("sc", ("sc", "scale", "scam", "scan")),
        ("sca", ("scale", "scam", "scan")),
        ("scal", ("scale",)),
        ("SCA", ("scale", "scam", "scan")),
        ("  sca  ", ("scale", "scam", "scan")),
        ("z", ()),
        ("scalene", ()),
    ],
)
def test_starting_with_is_exact_and_sorted(
    sample_lexicon: Lexicon, prefix: str, expected: tuple[str, ...]
) -> None:
    assert sample_lexicon.starting_with(prefix) == expected


def test_starting_with_empty_prefix_returns_everything(sample_lexicon: Lexicon) -> None:
    assert sample_lexicon.starting_with("") == tuple(sample_lexicon)
    assert sample_lexicon.starting_with("   ") == tuple(sample_lexicon)


def test_iteration_is_sorted_and_len_is_the_deduplicated_count(sample_lexicon: Lexicon) -> None:
    words = list(sample_lexicon)
    assert words == sorted(words)
    assert len(words) == len(set(words)) == len(sample_lexicon)
    assert len(sample_lexicon) == 8  # "SCALE" collapses onto "scale"


def test_lengths_property_is_ascending_and_complete(sample_lexicon: Lexicon) -> None:
    assert sample_lexicon.lengths == (2, 3, 4, 5)
    assert sample_lexicon.lengths == tuple(sorted({len(w) for w in sample_lexicon}))


def test_indexes_agree_with_iteration_and_membership(sample_lexicon: Lexicon) -> None:
    from_lengths = [w for n in sample_lexicon.lengths for w in sample_lexicon.words_of_length(n)]
    assert sorted(from_lengths) == list(sample_lexicon)
    for word in sample_lexicon:
        assert word in sample_lexicon
        assert word in sample_lexicon.words_of_length(len(word))
        assert word in sample_lexicon.starting_with(word[0])
        assert word in sample_lexicon.starting_with(word)


# ---------------------------------------------------------------------------
# property tests
# ---------------------------------------------------------------------------
@_PROPERTY_SETTINGS
@given(words=_word_list_strategy)
def test_property_iteration_is_the_sorted_deduplicated_normalised_input(words: list[str]) -> None:
    lexicon = Lexicon(words)
    expected = _expected_entries(words)
    assert list(lexicon) == expected
    assert len(lexicon) == len(expected)
    assert lexicon.words == frozenset(expected)


@_PROPERTY_SETTINGS
@given(words=_word_list_strategy)
def test_property_every_member_is_findable_in_any_casing(words: list[str]) -> None:
    lexicon = Lexicon(words)
    for word in lexicon:
        assert word in lexicon
        assert word.upper() in lexicon
        assert f"  {word}  " in lexicon


@_PROPERTY_SETTINGS
@given(words=_word_list_strategy)
def test_property_words_of_length_partitions_the_lexicon(words: list[str]) -> None:
    lexicon = Lexicon(words)
    seen: list[str] = []
    for size in range(0, 10):
        bucket = lexicon.words_of_length(size)
        assert bucket == tuple(w for w in lexicon if len(w) == size)
        assert list(bucket) == sorted(bucket)
        seen.extend(bucket)
    assert sorted(seen) == list(lexicon)


@_PROPERTY_SETTINGS
@given(words=_word_list_strategy, prefix=st.sampled_from(["", " ", "a", "A", "ab", "b", "z", "q"]))
def test_property_starting_with_matches_a_linear_scan(words: list[str], prefix: str) -> None:
    lexicon = Lexicon(words)
    key = prefix.strip().casefold()
    assert lexicon.starting_with(prefix) == tuple(w for w in lexicon if w.startswith(key))


# ---------------------------------------------------------------------------
# bundled + file-backed resources
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("word", ["the", "language", "memory", "format", "application"])
def test_bundled_english_lexicon_contains_obvious_words(
    english_lexicon: Lexicon, word: str
) -> None:
    assert word in english_lexicon
    assert word.upper() in english_lexicon


def test_bundled_english_lexicon_is_well_formed(english_lexicon: Lexicon) -> None:
    words = list(english_lexicon)
    assert len(words) > 1000
    assert words == sorted(words)
    assert len(words) == len(set(words))
    assert all(word == word.strip().casefold() for word in words)
    assert not any(word.startswith("#") for word in words)
    assert all(word for word in words)


@pytest.mark.parametrize(
    "acronym",
    sorted({acronym for _, acronym in CANONICAL_ACRONYMS} & _ACRONYMS_THAT_ARE_WORDS),
)
def test_canonical_acronyms_that_are_real_words_are_dictionary_hits(
    english_lexicon: Lexicon, acronym: str
) -> None:
    """These are exactly the canonical results for which ``Lambda(A) == 1``."""
    assert acronym in english_lexicon


@pytest.mark.parametrize("acronym", ["API", "PDF", "HTML", "SQL", "CPU"])
def test_canonical_initialisms_are_not_dictionary_hits(
    english_lexicon: Lexicon, acronym: str
) -> None:
    assert acronym not in english_lexicon


@pytest.mark.parametrize("language", list(Language))
def test_every_bundled_language_loads_without_raising(language: Language) -> None:
    lexicon = Lexicon.load(language)
    assert lexicon.language is language
    assert len(lexicon) > 0
    assert list(lexicon) == sorted(lexicon)


def test_tmp_lexicon_file_skips_comments_and_blank_lines(tmp_lexicon_file: Path) -> None:
    lexicon = Lexicon.from_path(tmp_lexicon_file, Language.EN)
    assert list(lexicon) == ["alpha", "bravo", "charlie", "delta", "nexus"]
    assert "#" not in lexicon
    assert "" not in lexicon
    assert "custom test lexicon" not in lexicon
    assert "NEXUS" in lexicon
    assert lexicon.words_of_length(5) == ("alpha", "bravo", "delta", "nexus")
    assert lexicon.starting_with("c") == ("charlie",)


def test_load_with_an_explicit_path_matches_from_path(tmp_lexicon_file: Path) -> None:
    via_load = Lexicon.load(Language.FR, path=tmp_lexicon_file)
    via_path = Lexicon.from_path(tmp_lexicon_file, Language.FR)
    assert list(via_load) == list(via_path)
    assert via_load.language is Language.FR
