"""Behavioural tests for :mod:`acronymkit.phonetics`.

This module owns ``Phi(A)``, the phonotactic term of the composite objective::

    Phi(A) = (1 / (k - 1)) * SUM_{m=1}^{k-1} log P(c_{m+1} | c_m)

so the tests verify the arithmetic against **hand-built** models whose
transition log-probabilities are chosen here, making every expected value a
closed-form quantity rather than an observation of the implementation.

A note on the add-k contract. ``CharNGramModel.train`` smooths over the symbol
set ``alphabet + {BOUNDARY_START, BOUNDARY_END}`` (size ``V``) but only ever
*emits* the successors ``alphabet + {BOUNDARY_END}`` -- ``BOUNDARY_START`` can
never follow anything. Each stored row therefore carries mass
``1 - k / (N_prev + k * V)``; the missing sliver is exactly the unemitted
``P(BOUNDARY_START | prev)``, and adding it back makes the row a proper
conditional distribution. Both halves of that statement are asserted below:
exactly for hand-built corpora (where ``k`` and ``N_prev`` are known), and to
within the analytic bound ``1 / V`` for the bundled models (where they are not).
"""

from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from acronymkit.enums import Language
from acronymkit.exceptions import ResourceNotFoundError
from acronymkit.phonetics import (
    CONSONANT_RUN_PENALTY,
    MAX_CONSONANT_RUN,
    NO_VOWEL_PENALTY,
    CharNGramModel,
    has_vowel,
    longest_consonant_run,
    pronounceability,
    syllable_count,
    vowel_ratio,
)
from conftest import CANONICAL_ACRONYMS, NGRAM_LANGUAGES

START = CharNGramModel.BOUNDARY_START
END = CharNGramModel.BOUNDARY_END

_LN2 = math.log(2.0)

#: Generic probes for round-trip / range assertions.
_PROBES = ["SCALE", "PDF", "XKCD", "A", "", "NASA", "queue", "rhythm", "3D", "zzzz"]

#: Accented letters each bundled model must know about.
_EXPECTED_ACCENTS = {
    Language.EN: "",
    Language.FR: "àçèéêô",
    Language.ES: "áéíñóú",
    Language.DE: "äöü",
}

#: Slack allowed when comparing accumulated floating-point sums against an
#: analytic bound. Far below any difference the tests care about.
_FLOAT_SLACK = 1e-9

#: Wall-clock health checks are about the host, not about the library.
_PROPERTY_SETTINGS = settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])


# ---------------------------------------------------------------------------
# hand-built models
# ---------------------------------------------------------------------------
_HAND_BACKOFF = -20.0


def _geometric_model() -> CharNGramModel:
    """A tiny model whose log-probabilities are exact multiples of ``ln 2``.

    ``P(b | a) = 1/2``, ``P(c | b) = P(a | b) = 1/4`` and so on, so every
    expected score below is an exact rational multiple of ``ln 2``.
    """
    transitions = {
        START: {"a": -4.0 * _LN2, "b": -6.0 * _LN2},
        "a": {"b": -1.0 * _LN2},
        "b": {"a": -2.0 * _LN2, "c": -2.0 * _LN2},
        "c": {"d": -3.0 * _LN2, END: -5.0 * _LN2},
        "d": {END: -7.0 * _LN2},
    }
    return CharNGramModel(transitions, backoff_log_prob=_HAND_BACKOFF, alphabet="abcd")


_FLAT_ALPHABET = "abcdg"
_FLAT_VALUE = -5.0
_FLAT_BACKOFF = -10.0
#: ``(-5 - -10) / (0 - -10)`` -- the rescaled base of every string over the flat
#: model's alphabet, before the vowel/cluster multipliers.
_FLAT_BASE = 0.5


def _flat_model() -> CharNGramModel:
    """A model giving *every* legal transition the same log-probability.

    Because the value is constant, ``score_with_boundaries`` is exactly ``-5``
    for any string over the alphabet, which isolates the vowel and
    consonant-run multipliers of :meth:`CharNGramModel.normalized_score`.
    """
    successors = [*_FLAT_ALPHABET, END]
    contexts = [*_FLAT_ALPHABET, START]
    transitions = {prev: dict.fromkeys(successors, _FLAT_VALUE) for prev in contexts}
    return CharNGramModel(transitions, backoff_log_prob=_FLAT_BACKOFF, alphabet=_FLAT_ALPHABET)


def _ranked_model() -> CharNGramModel:
    """A model where only the middle character of ``a?a`` moves the score.

    ``^ -> a``, ``? -> a`` and ``a -> $`` are all ``-1``, so for the equal-length
    probes ``"aba" / "aca" / "ada"`` the boundary contributions cancel and
    ``score_with_boundaries`` is a strictly increasing function of ``score``.
    """
    transitions = {
        START: {"a": -1.0},
        "a": {"b": -1.0, "c": -2.0, "d": -3.0, END: -1.0},
        "b": {"a": -1.0},
        "c": {"a": -1.0},
        "d": {"a": -1.0},
    }
    return CharNGramModel(transitions, backoff_log_prob=-10.0, alphabet="abcd")


def _reference_counts(
    words: Sequence[str],
) -> tuple[dict[str, dict[str, int]], dict[str, int], str]:
    """Independently recount the bigrams ``train`` is supposed to observe.

    Args:
        words: The training corpus.

    Returns:
        ``(counts, totals, alphabet)`` where ``counts[prev][next]`` is the raw
        bigram count, ``totals[prev]`` the number of transitions out of ``prev``
        and ``alphabet`` the sorted, de-duplicated set of case-folded letters.
    """
    alphabet = "".join(
        sorted({char for word in words for char in word.strip().casefold() if char.isalpha()})
    )
    allowed = frozenset(alphabet)
    counts: dict[str, dict[str, int]] = {}
    totals: dict[str, int] = {}
    for word in words:
        filtered = "".join(char for char in word.strip().casefold() if char in allowed)
        if not filtered:
            continue
        sequence = f"{START}{filtered}{END}"
        for index in range(len(sequence) - 1):
            prev, nxt = sequence[index], sequence[index + 1]
            row = counts.setdefault(prev, {})
            row[nxt] = row.get(nxt, 0) + 1
            totals[prev] = totals.get(prev, 0) + 1
    return counts, totals, alphabet


def _row_mass(row: Mapping[str, float]) -> float:
    """Return the total emitted probability mass of a transition row."""
    return sum(math.exp(value) for value in row.values())


# ---------------------------------------------------------------------------
# score(): the exact Phi(A) formula
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("acronym", "expected"),
    [
        # 3 characters: (log P(b|a) + log P(c|b)) / 2 = (-1 - 2) * ln2 / 2
        ("abc", -1.5 * _LN2),
        ("ABC", -1.5 * _LN2),
        ("AbC", -1.5 * _LN2),
        # 4 characters: (-1 - 2 - 3) * ln2 / 3
        ("abcd", -2.0 * _LN2),
        ("ABCD", -2.0 * _LN2),
        # 2 characters: one transition, so the mean is that transition
        ("ab", -1.0 * _LN2),
        ("ba", -2.0 * _LN2),
        # (b->a) + (a->b) = (-2 - 1) * ln2 / 2
        ("bab", -1.5 * _LN2),
        # unknown transitions fall back to the backoff floor
        ("ad", _HAND_BACKOFF),
        ("za", _HAND_BACKOFF),
        # one known + one unknown transition: (-1 * ln2 + backoff) / 2
        ("abz", (-1.0 * _LN2 + _HAND_BACKOFF) / 2.0),
    ],
)
def test_score_is_the_mean_bigram_log_likelihood(acronym: str, expected: float) -> None:
    assert _geometric_model().score(acronym) == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("acronym", ["", "a", "A", "z", "5"])
def test_score_of_a_string_shorter_than_two_returns_the_backoff(acronym: str) -> None:
    """Documented convention: no internal transition, so no defined mean."""
    model = _geometric_model()
    assert model.score(acronym) == model.backoff_log_prob == _HAND_BACKOFF


@pytest.mark.parametrize(
    ("acronym", "expected"),
    [
        # (^->a) + (a->b) + (b->c) + (c->$) = (-4 -1 -2 -5) * ln2, over k + 1 = 4
        ("abc", -3.0 * _LN2),
        ("ABC", -3.0 * _LN2),
        # (-4 -1 -2 -3 -7) * ln2 over k + 1 = 5
        ("abcd", -3.4 * _LN2),
        # k = 1: (^->a) + (a->$), and a->$ is unknown
        ("a", (-4.0 * _LN2 + _HAND_BACKOFF) / 2.0),
        # k = 2: (^->a) + (a->b) + (b->$ unknown), over 3
        ("ab", (-4.0 * _LN2 - 1.0 * _LN2 + _HAND_BACKOFF) / 3.0),
    ],
)
def test_score_with_boundaries_adds_both_sentinels_and_divides_by_k_plus_one(
    acronym: str, expected: float
) -> None:
    assert _geometric_model().score_with_boundaries(acronym) == pytest.approx(expected, rel=1e-12)


def test_score_with_boundaries_of_the_empty_string_returns_the_backoff() -> None:
    model = _geometric_model()
    assert model.score_with_boundaries("") == model.backoff_log_prob


def test_score_ignores_boundaries_but_score_with_boundaries_does_not() -> None:
    model = _geometric_model()
    assert model.score("abc") != model.score_with_boundaries("abc")


@pytest.mark.parametrize(
    ("prev", "nxt", "expected"),
    [
        ("a", "b", -1.0 * _LN2),
        ("A", "B", -1.0 * _LN2),
        (START, "a", -4.0 * _LN2),
        ("c", END, -5.0 * _LN2),
        ("a", "z", _HAND_BACKOFF),
        ("z", "a", _HAND_BACKOFF),
        (END, "a", _HAND_BACKOFF),
    ],
)
def test_log_prob_casefolds_and_backs_off(prev: str, nxt: str, expected: float) -> None:
    assert _geometric_model().log_prob(prev, nxt) == pytest.approx(expected, rel=1e-12)


# ---------------------------------------------------------------------------
# train(): add-k smoothing is a proper conditional distribution
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "corpus",
    [
        ["ab", "abc", "ba"],
        ["aa"],
        ["alpha", "beta", "gamma", "alpha"],
        ["Cat", " dog ", "COD"],
        ["été", "thé"],
    ],
    ids=["mixed", "single", "words", "cased", "accented"],
)
@pytest.mark.parametrize("smoothing", [0.25, 0.5, 1.0])
def test_train_emits_exact_add_k_probabilities(corpus: list[str], smoothing: float) -> None:
    """Every stored value must equal ``(count + k) / (N_prev + k * V)`` exactly."""
    model = CharNGramModel.train(corpus, smoothing=smoothing)
    counts, totals, alphabet = _reference_counts(corpus)

    assert model.alphabet == alphabet
    vocabulary = len(alphabet) + 2
    successors = [*alphabet, END]
    contexts = [*alphabet, START]
    assert sorted(model.transitions) == sorted(contexts)

    for prev in contexts:
        row = model.transitions[prev]
        assert sorted(row) == sorted(successors)
        denominator = totals.get(prev, 0) + smoothing * vocabulary
        for nxt in successors:
            expected = (counts.get(prev, {}).get(nxt, 0) + smoothing) / denominator
            assert math.exp(row[nxt]) == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize(
    "corpus",
    [["ab", "abc", "ba"], ["alpha", "beta", "gamma"], ["été", "thé"]],
    ids=["mixed", "words", "accented"],
)
@pytest.mark.parametrize("smoothing", [0.25, 0.5, 1.0])
def test_train_rows_form_a_proper_conditional_distribution(
    corpus: list[str], smoothing: float
) -> None:
    """Emitted mass plus the unemitted ``P(^ | prev)`` must be exactly 1.0."""
    model = CharNGramModel.train(corpus, smoothing=smoothing)
    _, totals, alphabet = _reference_counts(corpus)
    vocabulary = len(alphabet) + 2

    for prev, row in model.transitions.items():
        denominator = totals.get(prev, 0) + smoothing * vocabulary
        emitted = _row_mass(row)
        unemitted_start_mass = smoothing / denominator
        assert emitted + unemitted_start_mass == pytest.approx(1.0, abs=1e-12)
        assert emitted < 1.0


@pytest.mark.parametrize("language", [Language(code) for code in NGRAM_LANGUAGES])
def test_bundled_rows_form_a_proper_conditional_distribution(language: Language) -> None:
    """The same normalisation property, asserted on the shipped models.

    ``k`` and ``N_prev`` are not recoverable from the serialised file, but the
    deficit ``k / (N_prev + k * V)`` is bounded above by ``1 / V``, so the
    emitted mass must sit in ``(1 - 1/V, 1]``.
    """
    model = CharNGramModel.load(language)
    assert not model.is_uniform
    vocabulary = len(model.alphabet) + 2
    successors = sorted([*model.alphabet, END])
    contexts = sorted([*model.alphabet, START])
    assert sorted(model.transitions) == contexts

    for prev, row in model.transitions.items():
        assert sorted(row) == successors, prev
        mass = _row_mass(row)
        assert mass <= 1.0
        assert mass > 1.0 - 1.0 / vocabulary
        assert mass == pytest.approx(1.0, abs=1.0 / vocabulary)


@pytest.mark.parametrize("language", [Language(code) for code in NGRAM_LANGUAGES])
def test_bundled_log_probabilities_are_bounded_by_zero_and_the_backoff(
    language: Language,
) -> None:
    """``backoff_log_prob`` is a genuine global floor, as its docstring claims."""
    model = CharNGramModel.load(language)
    values = [value for row in model.transitions.values() for value in row.values()]
    assert values
    assert max(values) <= 0.0
    assert min(values) >= model.backoff_log_prob


@pytest.mark.parametrize(
    ("corpus", "accents"),
    [
        (["école", "élève", "français", "hôtel", "naïve"], "éèçôï"),
        (["mañana", "niño", "corazón"], "ñó"),
        (["schön", "über", "mädchen"], "öüä"),
    ],
    ids=["fr", "es", "de"],
)
def test_train_derives_its_alphabet_from_the_data(corpus: list[str], accents: str) -> None:
    model = CharNGramModel.train(corpus)
    assert set(accents) <= set(model.alphabet)
    assert model.alphabet == "".join(sorted(set(model.alphabet)))
    for accent in accents:
        assert accent in model.transitions  # usable as a context
        assert accent in model.transitions[START]  # and as a successor


def test_train_casefolds_eszett_into_ss() -> None:
    """``"straße".casefold() == "strasse"``, so ``s`` reaches the alphabet, not ``ß``."""
    model = CharNGramModel.train(["straße"])
    assert "ß" not in model.alphabet
    assert set("strase") <= set(model.alphabet)


@pytest.mark.parametrize("corpus", [[], [""], ["   "], ["123", "!!!"], ["-", "42"]])
def test_train_without_usable_material_returns_a_uniform_model(corpus: list[str]) -> None:
    model = CharNGramModel.train(corpus)
    assert model.is_uniform
    assert model.vocabulary_size == 0


@pytest.mark.parametrize("smoothing", [0.0, -1.0, math.inf, math.nan])
def test_train_rejects_non_positive_smoothing(smoothing: float) -> None:
    with pytest.raises(ValueError, match="smoothing must be"):
        CharNGramModel.train(["alpha"], smoothing=smoothing)


def test_train_records_language_and_vocabulary_size() -> None:
    model = CharNGramModel.train(["chat", "chien", "42"], language=Language.FR)
    assert model.language is Language.FR
    assert model.vocabulary_size == 2  # "42" contributes no letters


def test_train_is_order_independent() -> None:
    corpus = ["alpha", "beta", "gamma", "delta"]
    first = CharNGramModel.train(corpus)
    second = CharNGramModel.train(list(reversed(corpus)))
    assert first.alphabet == second.alphabet
    assert first.backoff_log_prob == second.backoff_log_prob
    assert first.to_dict()["transitions"] == second.to_dict()["transitions"]


# ---------------------------------------------------------------------------
# uniform(): usable without any resource
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("language", [Language(code) for code in NGRAM_LANGUAGES])
def test_uniform_needs_no_resource_and_is_a_real_uniform_distribution(
    language: Language,
) -> None:
    model = CharNGramModel.uniform(language)
    assert model.is_uniform
    assert dict(model.transitions) == {}
    assert model.language is language
    assert model.vocabulary_size == 0
    vocabulary = len(model.alphabet) + 2
    assert model.backoff_log_prob == pytest.approx(-math.log(vocabulary), rel=1e-12)
    # A uniform distribution over V symbols: V * (1/V) == 1.
    assert vocabulary * math.exp(model.backoff_log_prob) == pytest.approx(1.0, rel=1e-12)


@pytest.mark.parametrize(
    ("prev", "nxt"),
    [("a", "b"), ("z", "q"), (START, "a"), ("a", END), ("é", "x"), ("1", "2")],
)
def test_uniform_gives_every_transition_the_same_log_probability(prev: str, nxt: str) -> None:
    model = CharNGramModel.uniform(Language.EN)
    assert model.log_prob(prev, nxt) == model.backoff_log_prob


@pytest.mark.parametrize("probe", ["scale", "pdf", "xyz", "abcdefg", "a", ""])
def test_uniform_score_is_constant(probe: str) -> None:
    model = CharNGramModel.uniform(Language.EN)
    assert model.score(probe) == pytest.approx(model.backoff_log_prob, rel=1e-12)
    assert model.score_with_boundaries(probe) == pytest.approx(model.backoff_log_prob, rel=1e-12)


@pytest.mark.parametrize(
    ("probe", "expected"),
    [
        ("scale", 0.5),
        ("SCALE", 0.5),
        ("pdf", 0.5 * NO_VOWEL_PENALTY),
        ("xkcd", 0.5 * NO_VOWEL_PENALTY * CONSONANT_RUN_PENALTY),
    ],
)
def test_uniform_normalized_score_is_neutral_before_penalties(probe: str, expected: float) -> None:
    model = CharNGramModel.uniform(Language.EN)
    assert model.normalized_score(probe) == pytest.approx(expected, rel=1e-12)


# ---------------------------------------------------------------------------
# normalized_score()
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("probe", "expected"),
    [
        # base only: has a vowel, longest consonant run 1
        ("aba", _FLAT_BASE),
        # run of exactly MAX_CONSONANT_RUN (b, c, d) is tolerated
        ("abcda", _FLAT_BASE),
        # no vowel, run == MAX_CONSONANT_RUN -> vowel penalty only
        ("bcd", _FLAT_BASE * NO_VOWEL_PENALTY),
        # no vowel, run 4 > MAX_CONSONANT_RUN -> both penalties
        ("bcdg", _FLAT_BASE * NO_VOWEL_PENALTY * CONSONANT_RUN_PENALTY),
        # vowel present but run 4 -> cluster penalty only
        ("abcdga", _FLAT_BASE * CONSONANT_RUN_PENALTY),
    ],
    ids=["plain", "run3", "no-vowel", "no-vowel-run4", "vowel-run4"],
)
def test_normalized_score_applies_the_documented_multipliers(probe: str, expected: float) -> None:
    assert _flat_model().normalized_score(probe) == pytest.approx(expected, rel=1e-12)


def test_normalized_score_cluster_threshold_is_exclusive() -> None:
    """A run of exactly ``MAX_CONSONANT_RUN`` is tolerated; one more is not."""
    model = _flat_model()
    assert longest_consonant_run("abcda") == MAX_CONSONANT_RUN
    assert longest_consonant_run("abcdga") == MAX_CONSONANT_RUN + 1
    assert model.normalized_score("abcda") == pytest.approx(_FLAT_BASE, rel=1e-12)
    assert model.normalized_score("abcdga") == pytest.approx(
        _FLAT_BASE * CONSONANT_RUN_PENALTY, rel=1e-12
    )


def test_normalized_score_clamps_above_one() -> None:
    """A (degenerate) positive log-probability must not escape the unit range."""
    model = CharNGramModel({"a": {"b": 5.0}}, backoff_log_prob=-1.0, alphabet="ab")
    assert model.score_with_boundaries("ab") > 0.0
    assert model.normalized_score("ab") == 1.0


def test_normalized_score_clamps_below_zero() -> None:
    model = CharNGramModel({"a": {"b": -50.0}}, backoff_log_prob=-1.0, alphabet="ab")
    assert model.score_with_boundaries("ab") < model.backoff_log_prob
    assert model.normalized_score("ab") == 0.0


@pytest.mark.parametrize(("better", "worse"), [("aba", "aca"), ("aca", "ada"), ("aba", "ada")])
def test_normalized_score_is_monotone_with_score_at_equal_length(better: str, worse: str) -> None:
    """Equal length, same first and last character: the boundary terms cancel."""
    model = _ranked_model()
    assert len(better) == len(worse)
    assert has_vowel(better)
    assert has_vowel(worse)
    assert longest_consonant_run(better) <= MAX_CONSONANT_RUN
    assert longest_consonant_run(worse) <= MAX_CONSONANT_RUN
    assert model.score(better) > model.score(worse)
    assert model.score_with_boundaries(better) > model.score_with_boundaries(worse)
    assert model.normalized_score(better) > model.normalized_score(worse)


def test_normalized_score_ordering_on_real_english(english_ngram: CharNGramModel) -> None:
    """A pronounceable word beats a vowel-free initialism beats a cluster."""
    scale = english_ngram.normalized_score("SCALE")
    pdf = english_ngram.normalized_score("PDF")
    xkcd = english_ngram.normalized_score("XKCD")
    assert scale > pdf > xkcd
    assert xkcd >= 0.0
    assert scale <= 1.0


@pytest.mark.parametrize(("phrase", "acronym"), CANONICAL_ACRONYMS)
def test_normalized_score_of_every_canonical_acronym_is_a_unit_value(
    english_ngram: CharNGramModel, phrase: str, acronym: str
) -> None:
    value = english_ngram.normalized_score(acronym)
    assert 0.0 <= value <= 1.0, phrase
    assert value == english_ngram.normalized_score(acronym)


# ---------------------------------------------------------------------------
# orthographic helpers
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("cake", True),
        ("SYNC", True),  # 'y' counts as a vowel
        ("rhythm", True),
        ("pdf", False),
        ("TXT", False),
        ("www", False),  # 'w' does not count
        ("", False),
        ("3D", False),
        ("ÉLAN", True),  # accented vowel via canonical decomposition
        ("ça", True),
        ("ß", False),
    ],
)
def test_has_vowel(word: str, expected: bool) -> None:
    assert has_vowel(word) is expected


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("cake", 0.5),
        ("aeiou", 1.0),
        ("AEIOU", 1.0),
        ("sync", 0.25),
        ("pdf", 0.0),
        ("", 0.0),
        ("3D", 0.0),  # digits are ignored entirely
        ("123", 0.0),
        ("a-b", 0.5),
    ],
)
def test_vowel_ratio(word: str, expected: float) -> None:
    assert vowel_ratio(word) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("cake", 1),  # silent trailing 'e'
        ("the", 1),  # never below 1
        ("rhythm", 1),  # 'y' is the only nucleus
        ("queue", 1),  # one vowel run, "ueue"
        ("table", 2),  # "-le" keeps its syllable
        ("banana", 3),
        ("acronym", 3),
        ("idea", 2),
        ("code", 1),
        ("silent", 2),
        ("a", 1),
        ("", 0),
        ("123", 0),
    ],
)
def test_syllable_count(word: str, expected: int) -> None:
    assert syllable_count(word) == expected


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("strength", 4),  # n, g, t, h
        ("rhythm", 3),  # t, h, m ('y' breaks the run)
        ("sync", 2),  # n, c
        ("www", 3),  # 'w' is a consonant
        ("aeiou", 0),
        ("", 0),
        ("pdf", 3),
        ("xkcd", 4),
        ("ab-cd", 2),  # non-letters terminate a run
    ],
)
def test_longest_consonant_run(word: str, expected: int) -> None:
    assert longest_consonant_run(word) == expected


# ---------------------------------------------------------------------------
# serialisation round trips
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("language", [Language(code) for code in NGRAM_LANGUAGES])
def test_to_dict_from_dict_preserves_every_score(language: Language) -> None:
    model = CharNGramModel.load(language)
    clone = CharNGramModel.from_dict(model.to_dict())
    assert clone.language is model.language
    assert clone.alphabet == model.alphabet
    assert clone.backoff_log_prob == model.backoff_log_prob
    assert clone.vocabulary_size == model.vocabulary_size
    assert {p: dict(r) for p, r in clone.transitions.items()} == {
        p: dict(r) for p, r in model.transitions.items()
    }
    for probe in _PROBES:
        assert clone.score(probe) == model.score(probe)
        assert clone.score_with_boundaries(probe) == model.score_with_boundaries(probe)
        assert clone.normalized_score(probe) == model.normalized_score(probe)


def test_to_dict_survives_a_json_round_trip() -> None:
    model = CharNGramModel.train(["alpha", "beta", "gamma"], language=Language.ES)
    clone = CharNGramModel.from_dict(json.loads(json.dumps(model.to_dict())))
    for probe in [*_PROBES, "alpha", "gam"]:
        assert clone.score(probe) == pytest.approx(model.score(probe), rel=1e-12)
        assert clone.normalized_score(probe) == pytest.approx(
            model.normalized_score(probe), rel=1e-12
        )


def test_to_dict_returns_a_private_mutable_payload(english_ngram: CharNGramModel) -> None:
    payload = english_ngram.to_dict()
    payload["transitions"]["a"]["b"] = 12345.0
    payload["alphabet"] = "tampered"
    assert english_ngram.alphabet != "tampered"
    assert english_ngram.transitions["a"]["b"] != 12345.0
    assert set(english_ngram.to_dict()) == {
        "alphabet",
        "backoff_log_prob",
        "boundary_end",
        "boundary_start",
        "language",
        "order",
        "transitions",
        "vocabulary_size",
    }


def test_from_dict_remaps_foreign_boundary_symbols() -> None:
    payload = {
        "language": "en",
        "order": 2,
        "alphabet": "ab",
        "boundary_start": "<",
        "boundary_end": ">",
        "backoff_log_prob": -9.0,
        "transitions": {"<": {"a": -1.0}, "a": {">": -2.0, "b": -3.0}},
    }
    model = CharNGramModel.from_dict(payload)
    assert model.log_prob(START, "a") == -1.0
    assert model.log_prob("a", END) == -2.0
    assert sorted(model.transitions) == sorted([START, "a"])


@pytest.mark.parametrize(
    "payload",
    [
        {"alphabet": "ab", "backoff_log_prob": -1.0},
        {"transitions": {}, "backoff_log_prob": -1.0},
        {"transitions": {}, "alphabet": "ab"},
        {"transitions": {}, "alphabet": "ab", "backoff_log_prob": -1.0, "order": 3},
        {"transitions": [], "alphabet": "ab", "backoff_log_prob": -1.0},
        {"transitions": {"a": 1}, "alphabet": "ab", "backoff_log_prob": -1.0},
        {"transitions": {"a": {"b": True}}, "alphabet": "ab", "backoff_log_prob": -1.0},
        {"transitions": {"a": {"b": "x"}}, "alphabet": "ab", "backoff_log_prob": -1.0},
        {"transitions": {}, "alphabet": "ab", "backoff_log_prob": -1.0, "language": "klingon"},
    ],
    ids=[
        "no-transitions",
        "no-alphabet",
        "no-backoff",
        "wrong-order",
        "transitions-not-mapping",
        "row-not-mapping",
        "bool-value",
        "string-value",
        "unknown-language",
    ],
)
def test_from_dict_rejects_malformed_payloads(payload: dict) -> None:
    with pytest.raises(ValueError):
        CharNGramModel.from_dict(payload)


def test_from_dict_rejects_a_non_mapping() -> None:
    with pytest.raises(ValueError, match="must be a mapping"):
        CharNGramModel.from_dict([])  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# file-backed loading
# ---------------------------------------------------------------------------
def test_from_path_reads_plain_and_gzipped_models(tmp_path: Path) -> None:
    model = CharNGramModel.train(["alpha", "beta", "gamma"])
    payload = json.dumps(model.to_dict()).encode("utf-8")
    plain = tmp_path / "ngram_xx.json"
    plain.write_bytes(payload)
    packed = tmp_path / "ngram_xx.json.gz"
    packed.write_bytes(gzip.compress(payload))
    for candidate in (plain, packed):
        loaded = CharNGramModel.from_path(candidate)
        assert loaded.alphabet == model.alphabet
        assert loaded.score("alpha") == pytest.approx(model.score("alpha"), rel=1e-12)


@pytest.mark.parametrize("content", [b"", b"not json", b"[]", b'{"alphabet": "ab"}'])
def test_from_path_rejects_unusable_files(tmp_path: Path, content: bytes) -> None:
    target = tmp_path / "broken.json"
    target.write_bytes(content)
    with pytest.raises(ResourceNotFoundError):
        CharNGramModel.from_path(target)


def test_from_path_rejects_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ResourceNotFoundError, match="could not be read"):
        CharNGramModel.from_path(tmp_path / "absent.json")


def test_load_returns_the_identical_object_for_the_same_key(
    english_ngram: CharNGramModel,
) -> None:
    assert CharNGramModel.load(Language.EN) is english_ngram
    assert CharNGramModel.load("en") is english_ngram
    assert CharNGramModel.load(Language.FR) is not english_ngram


def test_load_with_a_path_is_cached_and_bypasses_the_bundle(tmp_path: Path) -> None:
    model = CharNGramModel.train(["alpha", "beta"])
    target = tmp_path / "custom.json"
    target.write_text(json.dumps(model.to_dict()), encoding="utf-8")
    first = CharNGramModel.load(Language.EN, path=target)
    assert first is CharNGramModel.load(Language.EN, path=Path(str(target)))
    assert first.alphabet == model.alphabet
    assert first is not CharNGramModel.load(Language.EN)


@pytest.mark.parametrize("language", [Language(code) for code in NGRAM_LANGUAGES])
def test_every_bundled_model_loads_with_its_accented_alphabet(language: Language) -> None:
    model = CharNGramModel.load(language)
    assert model.language is language
    assert model.order == 2
    assert not model.is_uniform
    assert model.vocabulary_size > 0
    # 'w' is genuinely absent from the Spanish lexicon.
    assert set("abcdefghijklmnopqrstuvwxyz") - set(model.alphabet) <= {"w"}
    assert set(_EXPECTED_ACCENTS[language]) <= set(model.alphabet)
    assert model.alphabet == "".join(sorted(set(model.alphabet)))


# ---------------------------------------------------------------------------
# construction invariants
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("backoff", [0.5, math.inf, -math.inf, math.nan])
def test_constructor_rejects_an_invalid_backoff(backoff: float) -> None:
    with pytest.raises(ValueError, match="backoff_log_prob must be"):
        CharNGramModel({}, backoff_log_prob=backoff, alphabet="ab")


@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan])
def test_constructor_rejects_non_finite_transitions(value: float) -> None:
    with pytest.raises(ValueError, match="not a finite log-probability"):
        CharNGramModel({"a": {"b": value}}, backoff_log_prob=-1.0, alphabet="ab")


def test_constructor_copies_and_freezes_the_transition_table() -> None:
    source = {"a": {"b": -1.0}}
    model = CharNGramModel(source, backoff_log_prob=-9.0, alphabet="ab")
    source["a"]["b"] = -99.0
    source["c"] = {"d": -1.0}
    assert model.log_prob("a", "b") == -1.0
    assert "c" not in model.transitions
    with pytest.raises(TypeError):
        model.transitions["a"]["b"] = 0.0  # type: ignore[index]
    with pytest.raises(TypeError):
        model.transitions["z"] = {}  # type: ignore[index]


def test_a_zero_span_model_reports_a_perfect_base() -> None:
    """``floor == 0`` leaves no span to rescale, so the base saturates at 1."""
    model = CharNGramModel({"a": {"b": 0.0}}, backoff_log_prob=0.0, alphabet="ab")
    assert not model.is_uniform
    assert model.normalized_score("ab") == 1.0


# ---------------------------------------------------------------------------
# pronounceability convenience wrapper
# ---------------------------------------------------------------------------
def test_pronounceability_defaults_to_the_shared_english_model(
    english_ngram: CharNGramModel,
) -> None:
    assert pronounceability("SCALE") == english_ngram.normalized_score("SCALE")


def test_pronounceability_honours_an_explicit_model() -> None:
    assert pronounceability("aba", _flat_model()) == pytest.approx(_FLAT_BASE, rel=1e-12)


# ---------------------------------------------------------------------------
# property tests
# ---------------------------------------------------------------------------
_text = st.text(max_size=12)
_ascii_text = st.text(alphabet="abcdefghijklmnopqrstuvwxyz 0123456789", max_size=12)
_letters = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8)


@_PROPERTY_SETTINGS
@given(word=_text)
def test_property_vowel_ratio_is_a_unit_fraction(word: str) -> None:
    assert 0.0 <= vowel_ratio(word) <= 1.0


@_PROPERTY_SETTINGS
@given(word=_text)
def test_property_syllable_count_is_never_below_one_for_a_word(word: str) -> None:
    count = syllable_count(word)
    if any(char.isalpha() for char in word):
        assert count >= 1
    else:
        assert count == 0


@_PROPERTY_SETTINGS
@given(word=_text)
def test_property_longest_consonant_run_is_bounded_by_the_letter_count(word: str) -> None:
    run = longest_consonant_run(word)
    assert 0 <= run <= sum(1 for char in word if char.isalpha())
    if run > 0:
        assert not all(has_vowel(char) for char in word if char.isalpha())


@_PROPERTY_SETTINGS
@given(word=_ascii_text)
def test_property_score_is_deterministic_and_case_insensitive(word: str) -> None:
    model = CharNGramModel.load(Language.EN)
    assert model.score(word) == model.score(word)
    assert model.score(word) == model.score(word.upper())
    assert model.score_with_boundaries(word) == model.score_with_boundaries(word.upper())


@_PROPERTY_SETTINGS
@given(word=_text)
def test_property_score_lies_between_the_backoff_and_zero(word: str) -> None:
    model = CharNGramModel.load(Language.EN)
    floor = model.backoff_log_prob - _FLOAT_SLACK
    assert floor <= model.score(word) <= 0.0
    assert floor <= model.score_with_boundaries(word) <= 0.0


@_PROPERTY_SETTINGS
@given(word=_text)
def test_property_normalized_score_is_a_unit_value(word: str) -> None:
    assert 0.0 <= CharNGramModel.load(Language.EN).normalized_score(word) <= 1.0


@_PROPERTY_SETTINGS
@given(first=_letters, second=_letters)
def test_property_normalized_score_tracks_score_with_boundaries(first: str, second: str) -> None:
    """With identical penalty multipliers the mapping is strictly monotone."""
    model = CharNGramModel.load(Language.EN)
    same_penalties = has_vowel(first) == has_vowel(second) and (
        longest_consonant_run(first) > MAX_CONSONANT_RUN
    ) == (longest_consonant_run(second) > MAX_CONSONANT_RUN)
    if not same_penalties:
        return
    raw_order = model.score_with_boundaries(first) - model.score_with_boundaries(second)
    if abs(raw_order) < 1e-12:
        return
    norm_order = model.normalized_score(first) - model.normalized_score(second)
    assert (raw_order > 0.0) == (norm_order > 0.0)
    assert (raw_order < 0.0) == (norm_order < 0.0)


@_PROPERTY_SETTINGS
@given(word=_text)
def test_property_serialization_round_trip_preserves_scores(word: str) -> None:
    model = CharNGramModel.load(Language.EN)
    clone = CharNGramModel.from_dict(model.to_dict())
    assert clone.score(word) == model.score(word)
    assert clone.score_with_boundaries(word) == model.score_with_boundaries(word)
    assert clone.normalized_score(word) == model.normalized_score(word)


@_PROPERTY_SETTINGS
@given(corpus=st.lists(_letters, min_size=1, max_size=8))
def test_property_trained_rows_never_exceed_unit_mass(corpus: list[str]) -> None:
    model = CharNGramModel.train(corpus, smoothing=0.5)
    vocabulary = len(model.alphabet) + 2
    for row in model.transitions.values():
        mass = _row_mass(row)
        assert 1.0 - 1.0 / vocabulary < mass < 1.0
