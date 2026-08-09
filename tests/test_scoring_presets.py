"""Calibration lock for the :data:`~acronymkit.config.STRATEGY_WEIGHTS` presets.

``config.py`` documents its preset vectors as *calibrated, not guessed*, and
names this file as the place that pins the calibration. The tests here are
therefore regression locks rather than unit tests: they assert the behaviour a
retuned weight vector must continue to deliver.

What is pinned:

* every phrase in :data:`conftest.CANONICAL_ACRONYMS` still yields its textbook
  initialism as the primary result, under both the default configuration and
  ``STRICT_INITIALISM``;
* each remaining preset still moves the property it exists to optimise, stated
  as a *relation* between presets rather than as an absolute number, so the
  tests survive a re-trained n-gram model or lexicon;
* ``CUSTOM`` still demands explicit weights, and those weights are the ones the
  engine actually uses;
* the marginal economics that make "one letter per token" optimal still hold
  for the default weights.

Everything runs on the Tier 0 (zero-dependency) path, so the results do not
depend on whether spaCy or NLTK happens to be installed.
"""

from __future__ import annotations

import statistics
from functools import cache

import pytest

from acronymkit import AcronymEngine, Config
from acronymkit.config import STRATEGY_WEIGHTS, ScoringWeights
from acronymkit.enums import EngineTier, ScoringStrategy
from acronymkit.exceptions import AcronymKitError, ConfigurationError
from acronymkit.models import AcronymCandidate
from conftest import CANONICAL_ACRONYMS


@cache
def _default_engine() -> AcronymEngine:
    """An engine on the shipped defaults — the configuration users get for free."""
    return AcronymEngine(Config())


@cache
def _engine_for(strategy: ScoringStrategy) -> AcronymEngine:
    """A Tier 0 engine differing from the default only in scoring strategy."""
    return AcronymEngine(
        Config(
            engine_tier=EngineTier.ZERO_DEPENDENCY,
            scoring_strategy=strategy,
        )
    )


def _primaries(strategy: ScoringStrategy) -> list[AcronymCandidate]:
    """Return the winning candidate for every canonical phrase under ``strategy``."""
    engine = _engine_for(strategy)
    return [engine.generate(phrase).alternatives[0] for phrase, _ in CANONICAL_ACRONYMS]


# ---------------------------------------------------------------------------
# The canonical corpus
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(("phrase", "expected"), CANONICAL_ACRONYMS)
def test_default_config_reproduces_the_canonical_acronym(phrase: str, expected: str) -> None:
    """The shipped defaults return the textbook initialism, for all sixteen."""
    result = _default_engine().generate(phrase)
    assert result.primary_acronym == expected


@pytest.mark.parametrize(("phrase", "expected"), CANONICAL_ACRONYMS)
def test_strict_initialism_reproduces_the_canonical_acronym(phrase: str, expected: str) -> None:
    """STRICT_INITIALISM is the preset whose whole job is positional fidelity."""
    result = _engine_for(ScoringStrategy.STRICT_INITIALISM).generate(phrase)
    assert result.primary_acronym == expected


def test_default_strategy_is_strict_initialism() -> None:
    """The corpus lock above is only meaningful if the default is what we think.

    The default was ``BALANCED_PRONOUNCEABLE`` in v0.1.0 and moved to
    ``STRICT_INITIALISM`` once the real SCOWL lexicon landed: with 77k real
    words there is provably no vector that both weights dictionary hits
    meaningfully and returns every textbook initialism, and the default has to
    be the one that returns "PDF".
    """
    assert Config().scoring_strategy is ScoringStrategy.STRICT_INITIALISM
    assert Config().weights == STRATEGY_WEIGHTS[ScoringStrategy.STRICT_INITIALISM]


# ---------------------------------------------------------------------------
# Each preset moves the property it exists to optimise
# ---------------------------------------------------------------------------
def test_max_pronounceable_raises_mean_pronounceability_over_strict() -> None:
    """MAX_PRONOUNCEABLE must win on the metric it is named for.

    The assertion is a strict inequality between two means measured on the same
    corpus, not a pinned float: re-training the bundled n-gram model may move
    both numbers, but it must never invert their order.
    """
    strict = statistics.mean(
        candidate.pronounceability_score
        for candidate in _primaries(ScoringStrategy.STRICT_INITIALISM)
    )
    pronounceable = statistics.mean(
        candidate.pronounceability_score
        for candidate in _primaries(ScoringStrategy.MAX_PRONOUNCEABLE)
    )
    assert pronounceable > strict, (
        "MAX_PRONOUNCEABLE must produce more word-like primaries than "
        f"STRICT_INITIALISM; got mean {pronounceable!r} vs {strict!r}"
    )


def test_dictionary_backronym_finds_more_real_words_than_strict() -> None:
    """DICTIONARY_BACKRONYM must surface dictionary hits wherever reachable."""
    strict = sum(
        candidate.is_dictionary_word for candidate in _primaries(ScoringStrategy.STRICT_INITIALISM)
    )
    backronym = sum(
        candidate.is_dictionary_word
        for candidate in _primaries(ScoringStrategy.DICTIONARY_BACKRONYM)
    )
    assert backronym > strict, (
        "DICTIONARY_BACKRONYM must yield strictly more dictionary-word primaries "
        f"than STRICT_INITIALISM; got {backronym} vs {strict} of "
        f"{len(CANONICAL_ACRONYMS)}"
    )


def test_dictionary_backronym_reaches_nexus() -> None:
    """The showcase case: a real word is reachable, so it must win."""
    engine = _engine_for(ScoringStrategy.DICTIONARY_BACKRONYM)
    result = engine.generate("Network Exchange Unified Security")
    assert result.primary_acronym == "NEXUS"
    assert result.alternatives[0].is_dictionary_word is True


# ---------------------------------------------------------------------------
# CUSTOM
# ---------------------------------------------------------------------------
def test_custom_strategy_without_weights_is_rejected() -> None:
    """CUSTOM is a sentinel meaning "the caller supplies the vector"."""
    with pytest.raises(ConfigurationError, match="scoring_weights"):
        Config(scoring_strategy=ScoringStrategy.CUSTOM)


def test_custom_strategy_without_weights_raises_configuration_error() -> None:
    """The documented contract: an inconsistent Config raises ConfigurationError.

    Regression test. ``Config._validate`` raises ``ConfigurationError``, but a
    ``mode="after"`` Pydantic validator used to wrap it in
    ``pydantic.ValidationError`` — which is not an
    :class:`~acronymkit.exceptions.AcronymKitError`. That broke the contract
    documented in :mod:`acronymkit.exceptions`, that integrators can install a
    single ``except AcronymKitError`` clause at a service boundary.
    ``Config.__init__`` now unwraps it.
    """
    with pytest.raises(ConfigurationError):
        Config(scoring_strategy=ScoringStrategy.CUSTOM)


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"scoring_strategy": ScoringStrategy.CUSTOM}, id="custom-without-weights"),
        pytest.param({"min_acronym_length": 9, "max_acronym_length": 3}, id="min-above-max"),
        pytest.param({"engine_tier": "turbo"}, id="unknown-enum-value"),
        pytest.param({"max_candidates": "lots"}, id="wrong-type"),
        pytest.param({"max_candidates": 0}, id="out-of-range"),
        pytest.param({"nonexistent_field": 1}, id="unknown-field"),
    ],
)
def test_every_config_error_is_catchable_as_an_acronymkit_error(kwargs: dict) -> None:
    """No configuration failure may escape as a bare Pydantic ValidationError.

    ``ConfigurationError`` is also a ``ValueError``, so both the library-wide
    and the conventional except clause work.
    """
    with pytest.raises(AcronymKitError):
        Config(**kwargs)
    with pytest.raises(ValueError):
        Config(**kwargs)


def test_with_overrides_reports_invalid_values_as_configuration_error() -> None:
    """The copy-with-changes helper validates through the same path."""
    with pytest.raises(ConfigurationError):
        Config().with_overrides(max_candidates=0)


def test_custom_weights_are_the_effective_weights() -> None:
    """``Config.weights`` returns the override verbatim, not the preset."""
    custom = ScoringWeights(
        alpha=2.5,
        beta=0.125,
        gamma=7.0,
        delta=9.0,
        initial_weight=11.0,
        internal_weight=4.0,
        contiguous_weight=1.0,
        unmapped_penalty=3.0,
        length_penalty=5.0,
        preferred_length=4,
    )
    config = Config(scoring_strategy=ScoringStrategy.CUSTOM, scoring_weights=custom)
    assert config.weights == custom
    assert config.weights is custom
    assert config.weights != STRATEGY_WEIGHTS[ScoringStrategy.CUSTOM]
    # The scorer the engine builds inherits them.
    assert AcronymEngine(config).scorer.weights == custom


@pytest.mark.parametrize(
    "strategy",
    [strategy for strategy in ScoringStrategy if strategy is not ScoringStrategy.CUSTOM],
)
def test_explicit_weights_override_any_strategy(strategy: ScoringStrategy) -> None:
    """An explicit vector beats the preset regardless of the named strategy."""
    custom = ScoringWeights(alpha=3.0)
    config = Config(scoring_strategy=strategy, scoring_weights=custom)
    assert config.weights is custom


# ---------------------------------------------------------------------------
# Structural invariants of the preset table
# ---------------------------------------------------------------------------
def test_strategy_weights_covers_every_strategy() -> None:
    """A new ScoringStrategy member without a preset would KeyError at run time."""
    assert set(STRATEGY_WEIGHTS) == set(ScoringStrategy)
    for strategy in ScoringStrategy:
        assert isinstance(STRATEGY_WEIGHTS[strategy], ScoringWeights)


@pytest.mark.parametrize(
    "strategy",
    [strategy for strategy in ScoringStrategy if strategy is not ScoringStrategy.CUSTOM],
)
def test_preset_lookup_matches_the_table(strategy: ScoringStrategy) -> None:
    """``Config.weights`` resolves the strategy through ``STRATEGY_WEIGHTS``.

    ``CUSTOM`` is excluded because it cannot be constructed without an explicit
    override, which by definition bypasses the table.
    """
    assert Config(scoring_strategy=strategy).weights is STRATEGY_WEIGHTS[strategy]


# ---------------------------------------------------------------------------
# The documented marginal economics
# ---------------------------------------------------------------------------
def test_default_weights_make_one_letter_per_token_optimal() -> None:
    """``contiguous_weight < length_penalty < initial_weight`` for the defaults.

    This inequality is the whole reason ``length_penalty`` is non-zero. Reading
    it as marginal economics, with ``length_penalty`` the cost of one extra
    acronym character:

    * covering one more token nets ``initial_weight - length_penalty > 0``, so
      the search is paid to represent another token;
    * taking a second letter from a token it already used nets
      ``contiguous_weight - length_penalty < 0``, so padding is punished.

    Break the inequality and "one letter per token, cover everything" stops
    being the optimum by construction — which is exactly what the canonical
    corpus above depends on.
    """
    weights = Config().weights
    assert weights.contiguous_weight < weights.length_penalty < weights.initial_weight, (
        "the default weights must satisfy "
        "contiguous_weight < length_penalty < initial_weight so that covering an "
        "extra token pays and padding an existing one does not; got "
        f"contiguous_weight={weights.contiguous_weight}, "
        f"length_penalty={weights.length_penalty}, "
        f"initial_weight={weights.initial_weight}"
    )


def test_bare_scoring_weights_share_the_default_economics() -> None:
    """A hand-rolled ``ScoringWeights()`` starts from the same marginal ordering."""
    weights = ScoringWeights()
    assert weights.contiguous_weight < weights.length_penalty < weights.initial_weight


@pytest.mark.parametrize(
    "strategy",
    [
        ScoringStrategy.STRICT_INITIALISM,
        ScoringStrategy.BALANCED_PRONOUNCEABLE,
        ScoringStrategy.DICTIONARY_BACKRONYM,
    ],
)
def test_initialism_oriented_presets_keep_the_marginal_ordering(
    strategy: ScoringStrategy,
) -> None:
    """Every preset that is meant to respect token coverage obeys the inequality."""
    weights = STRATEGY_WEIGHTS[strategy]
    assert weights.contiguous_weight < weights.length_penalty < weights.initial_weight


def test_max_pronounceable_deliberately_relaxes_the_length_penalty() -> None:
    """MAX_PRONOUNCEABLE is the documented exception, and it is intentional.

    Its length penalty is not above ``contiguous_weight``, so extra characters
    are cheap and longer, word-like forms can win. That is the stated purpose of
    the preset ("longer, word-like forms are cheap"), so the departure is pinned
    here rather than left to look like an oversight.
    """
    weights = STRATEGY_WEIGHTS[ScoringStrategy.MAX_PRONOUNCEABLE]
    assert weights.length_penalty <= weights.contiguous_weight
    assert (
        weights.preferred_length
        > STRATEGY_WEIGHTS[ScoringStrategy.STRICT_INITIALISM].preferred_length
    )


@pytest.mark.parametrize("strategy", list(ScoringStrategy))
def test_every_preset_has_non_negative_coefficients(strategy: ScoringStrategy) -> None:
    """All four primary coefficients are non-negative in every shipped preset."""
    weights = STRATEGY_WEIGHTS[strategy]
    assert weights.alpha >= 0.0
    assert weights.beta >= 0.0
    assert weights.gamma >= 0.0
    assert weights.delta >= 0.0
    assert weights.length_penalty >= 0.0
    assert weights.preferred_length >= 1
