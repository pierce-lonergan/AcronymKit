"""Behavioural tests for :mod:`acronymkit.config`.

``Config`` is the single knob-bag threaded through every subsystem, and it is
frozen, so the interesting behaviour is all in validation, derived properties
and copy-with-overrides.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from acronymkit.config import STRATEGY_WEIGHTS, Config, ScoringWeights
from acronymkit.enums import (
    CaseStyle,
    EngineTier,
    HyphenPolicy,
    Language,
    NumeralPolicy,
    ScoringStrategy,
    StopWordCategory,
)
from acronymkit.exceptions import AcronymKitError, ConfigurationError


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
# Every configuration failure surfaces as ``ConfigurationError``. Pydantic would
# otherwise wrap validator errors in its own ``ValidationError``, which is not an
# ``AcronymKitError``; ``Config.__init__`` unwraps it so the hierarchy documented
# in ``acronymkit.exceptions`` holds. ``ConfigurationError`` is also a
# ``ValueError``, so a conventional ``except ValueError`` still works.
@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"min_acronym_length": 5, "max_acronym_length": 3},
            "min_acronym_length",
        ),
        (
            {"min_acronym_length": 7, "max_acronym_length": 6},
            "max_acronym_length",
        ),
        (
            {
                "extraction_min_short_form_length": 9,
                "extraction_max_short_form_length": 3,
            },
            "extraction_min_short_form_length",
        ),
        (
            {"scoring_strategy": ScoringStrategy.CUSTOM},
            "requires explicit scoring_weights",
        ),
        (
            {"scoring_strategy": "custom"},
            "requires explicit scoring_weights",
        ),
    ],
    ids=[
        "min-above-max-acronym-length",
        "min-above-max-acronym-length-adjacent",
        "min-above-max-short-form-length",
        "custom-strategy-without-weights",
        "custom-strategy-as-string-without-weights",
    ],
)
def test_invalid_configurations_are_rejected(kwargs: dict, message: str) -> None:
    """Each documented inconsistency raises with a message naming the culprit."""
    with pytest.raises(ConfigurationError) as excinfo:
        Config(**kwargs)
    assert message in str(excinfo.value)
    # One ``except AcronymKitError`` at a service boundary catches everything the
    # library raises; ConfigurationError is also a ValueError for callers who
    # prefer the conventional clause.
    assert isinstance(excinfo.value, AcronymKitError)
    assert isinstance(excinfo.value, ValueError)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_acronym_length": 3, "max_acronym_length": 3},
        {"extraction_min_short_form_length": 4, "extraction_max_short_form_length": 4},
        {
            "scoring_strategy": ScoringStrategy.CUSTOM,
            "scoring_weights": ScoringWeights(alpha=2.0),
        },
    ],
    ids=["equal-acronym-bounds", "equal-short-form-bounds", "custom-with-weights"],
)
def test_boundary_configurations_are_accepted(kwargs: dict) -> None:
    """``min == max`` is legal; CUSTOM is legal once weights are supplied."""
    assert Config(**kwargs) is not None


def test_unknown_fields_are_rejected() -> None:
    """``extra='forbid'`` catches typos in configuration keys."""
    with pytest.raises(ConfigurationError):
        Config(maximum_acronym_length=4)


@given(
    low=st.integers(min_value=1, max_value=12),
    span=st.integers(min_value=0, max_value=12),
)
def test_any_ordered_length_pair_validates(low: int, span: int) -> None:
    """Property: ``min <= max`` always validates and round-trips unchanged."""
    config = Config(min_acronym_length=low, max_acronym_length=low + span)
    assert config.min_acronym_length == low
    assert config.max_acronym_length == low + span


@given(
    low=st.integers(min_value=2, max_value=12),
    gap=st.integers(min_value=1, max_value=12),
)
def test_any_inverted_length_pair_is_rejected(low: int, gap: int) -> None:
    """Property: ``min > max`` is always a validation failure."""
    with pytest.raises(ConfigurationError):
        Config(min_acronym_length=low + gap, max_acronym_length=low)


# ---------------------------------------------------------------------------
# with_overrides
# ---------------------------------------------------------------------------
def test_with_overrides_returns_a_validated_copy_and_does_not_mutate() -> None:
    """The receiver is untouched and the copy differs only where asked."""
    original = Config(max_acronym_length=6, max_candidates=25)
    snapshot = original.model_dump()

    updated = original.with_overrides(max_acronym_length=8, max_candidates=3)

    assert updated is not original
    assert (updated.max_acronym_length, updated.max_candidates) == (8, 3)
    assert (original.max_acronym_length, original.max_candidates) == (6, 25)
    assert original.model_dump() == snapshot
    # Everything not overridden is carried over verbatim.
    changed = {key for key, value in updated.model_dump().items() if snapshot[key] != value}
    assert changed == {"max_acronym_length", "max_candidates"}


def test_with_overrides_revalidates() -> None:
    """An override that breaks an invariant is rejected, not silently applied."""
    config = Config(min_acronym_length=3, max_acronym_length=6)
    with pytest.raises(ConfigurationError):
        config.with_overrides(max_acronym_length=1)


def test_with_overrides_with_no_arguments_reproduces_the_original() -> None:
    """A no-op override is a faithful, equal copy."""
    config = Config(scoring_weights=ScoringWeights(alpha=3.0), include_articles=True)
    copy = config.with_overrides()
    assert copy == config
    assert copy is not config


def test_with_overrides_preserves_explicit_weights() -> None:
    """A nested ``ScoringWeights`` survives the dump/rebuild round trip."""
    weights = ScoringWeights(alpha=2.5, beta=0.5, gamma=7.0, delta=9.0)
    config = Config(scoring_weights=weights).with_overrides(max_candidates=2)
    assert config.weights == weights


@given(candidates=st.integers(min_value=1, max_value=50))
def test_with_overrides_round_trips_any_valid_candidate_count(candidates: int) -> None:
    """Property: overriding a scalar field is exact."""
    config = Config().with_overrides(max_candidates=candidates)
    assert config.max_candidates == candidates


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------
def test_fast_preset() -> None:
    """``Config.fast`` is the latency-tuned Tier 0 bundle."""
    config = Config.fast()
    assert config.engine_tier is EngineTier.ZERO_DEPENDENCY
    assert config.scoring_strategy is ScoringStrategy.STRICT_INITIALISM
    assert config.max_candidates == 5
    assert config.allow_multi_letter_tokens is False
    assert config.max_letters_per_token == 1
    assert config.search_beam_width == 32
    assert config.include_breakdown is False


def test_fast_preset_accepts_overrides() -> None:
    """Overrides win over the preset's own defaults."""
    config = Config.fast(max_candidates=11, include_breakdown=True)
    assert config.max_candidates == 11
    assert config.include_breakdown is True
    # Untouched preset values survive.
    assert config.search_beam_width == 32


@pytest.mark.parametrize(
    "strategy",
    [
        ScoringStrategy.STRICT_INITIALISM,
        ScoringStrategy.BALANCED_PRONOUNCEABLE,
        ScoringStrategy.MAX_PRONOUNCEABLE,
        ScoringStrategy.DICTIONARY_BACKRONYM,
    ],
    ids=lambda strategy: strategy.value,
)
def test_preset_selects_the_strategy_weights(strategy: ScoringStrategy) -> None:
    """``Config.preset`` binds the named preset's coefficient vector."""
    config = Config.preset(strategy)
    assert config.scoring_strategy is strategy
    assert config.weights == STRATEGY_WEIGHTS[strategy]


@pytest.mark.parametrize(
    "strategy", ["max_pronounceable", "MAX-PRONOUNCEABLE", "Max_Pronounceable"], ids=repr
)
def test_preset_coerces_string_strategies(strategy: str) -> None:
    """A plain string is accepted wherever the enum is."""
    assert Config.preset(strategy).scoring_strategy is ScoringStrategy.MAX_PRONOUNCEABLE


def test_preset_accepts_overrides() -> None:
    """``preset`` forwards keyword overrides to the constructor."""
    config = Config.preset(ScoringStrategy.STRICT_INITIALISM, max_acronym_length=4)
    assert config.max_acronym_length == 4
    assert config.scoring_strategy is ScoringStrategy.STRICT_INITIALISM


def test_preset_custom_still_requires_weights() -> None:
    """The CUSTOM sentinel is not a way around the weights requirement."""
    with pytest.raises(ConfigurationError):
        Config.preset(ScoringStrategy.CUSTOM)


# ---------------------------------------------------------------------------
# suppressed_categories
# ---------------------------------------------------------------------------
#: Categories that are always suppressed, whatever the include flags say.
ALWAYS_SUPPRESSED = {
    StopWordCategory.PARTICLE,
    StopWordCategory.DETERMINER,
    StopWordCategory.OTHER,
}

#: ``include_*`` flag paired with the category it unlocks.
FLAG_CATEGORIES = [
    ("include_articles", StopWordCategory.ARTICLE),
    ("include_prepositions", StopWordCategory.PREPOSITION),
    ("include_conjunctions", StopWordCategory.CONJUNCTION),
    ("include_pronouns", StopWordCategory.PRONOUN),
    ("include_auxiliaries", StopWordCategory.AUXILIARY),
]


def test_default_config_suppresses_every_toggleable_category() -> None:
    """By default no function word may donate a letter."""
    suppressed = Config().suppressed_categories
    assert suppressed == frozenset(StopWordCategory)


@pytest.mark.parametrize(("flag", "category"), FLAG_CATEGORIES, ids=lambda x: str(x))
def test_include_flag_unsuppresses_exactly_its_own_category(
    flag: str, category: StopWordCategory
) -> None:
    """Flipping one flag removes one category and touches nothing else."""
    baseline = Config().suppressed_categories
    suppressed = Config(**{flag: True}).suppressed_categories
    assert category not in suppressed
    assert baseline - suppressed == {category}


@pytest.mark.parametrize(("flag", "category"), FLAG_CATEGORIES, ids=lambda x: str(x))
def test_include_flag_defaults_to_suppressed(flag: str, category: StopWordCategory) -> None:
    """Each toggleable category is suppressed while its flag is ``False``."""
    assert category in Config(**{flag: False}).suppressed_categories


def test_all_include_flags_leave_only_the_hard_coded_suppressions() -> None:
    """Particles, determiners and 'other' are never unlocked by a flag."""
    config = Config(**{flag: True for flag, _ in FLAG_CATEGORIES})
    assert config.suppressed_categories == frozenset(ALWAYS_SUPPRESSED)


def test_suppressed_categories_is_an_immutable_frozenset() -> None:
    """The derived set cannot be mutated into the configuration."""
    suppressed = Config().suppressed_categories
    assert isinstance(suppressed, frozenset)
    with pytest.raises(AttributeError):
        suppressed.add(StopWordCategory.ARTICLE)  # type: ignore[attr-defined]


@given(flags=st.lists(st.booleans(), min_size=5, max_size=5))
def test_suppressed_categories_tracks_every_flag_combination(
    flags: list[bool],
) -> None:
    """Property: the suppressed set is exactly the flags' complement plus the
    three always-suppressed categories."""
    kwargs = {flag: value for (flag, _), value in zip(FLAG_CATEGORIES, flags)}
    expected = set(ALWAYS_SUPPRESSED) | {
        category for (_, category), value in zip(FLAG_CATEGORIES, flags) if not value
    }
    assert Config(**kwargs).suppressed_categories == frozenset(expected)


# ---------------------------------------------------------------------------
# weights resolution
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("strategy", list(ScoringStrategy), ids=lambda strategy: strategy.value)
def test_weights_fall_back_to_the_strategy_preset(strategy: ScoringStrategy) -> None:
    """With no explicit vector, the strategy's preset is authoritative."""
    kwargs: dict = {"scoring_strategy": strategy}
    if strategy is ScoringStrategy.CUSTOM:
        # CUSTOM cannot be built without weights; its preset is still reachable.
        assert STRATEGY_WEIGHTS[strategy] == ScoringWeights()
        return
    assert Config(**kwargs).weights is STRATEGY_WEIGHTS[strategy]


@pytest.mark.parametrize("strategy", list(ScoringStrategy), ids=lambda strategy: strategy.value)
def test_explicit_weights_beat_the_strategy_preset(strategy: ScoringStrategy) -> None:
    """``scoring_weights`` wins over the preset for every strategy."""
    explicit = ScoringWeights(alpha=9.0, beta=8.0, gamma=7.0, delta=6.0)
    config = Config(scoring_strategy=strategy, scoring_weights=explicit)
    assert config.weights is explicit
    assert config.weights != STRATEGY_WEIGHTS[strategy]


def test_strategy_weights_table_covers_every_strategy() -> None:
    """No strategy can be selected without a preset behind it."""
    assert set(STRATEGY_WEIGHTS) == set(ScoringStrategy)


def test_scoring_weights_scaled_scales_only_the_four_coefficients() -> None:
    """``scaled`` is a uniform rescale of alpha/beta/gamma/delta."""
    weights = ScoringWeights(alpha=1.0, beta=2.0, gamma=3.0, delta=4.0)
    scaled = weights.scaled(2.5)
    assert (scaled.alpha, scaled.beta, scaled.gamma, scaled.delta) == (
        2.5,
        5.0,
        7.5,
        10.0,
    )
    assert scaled.initial_weight == weights.initial_weight
    assert scaled.length_penalty == weights.length_penalty
    assert weights.alpha == 1.0  # the receiver is untouched


# ---------------------------------------------------------------------------
# allow_multi_letter_tokens
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("requested", [1, 2, 3, 9])
def test_disallowing_multi_letter_tokens_forces_one_letter(requested: int) -> None:
    """``allow_multi_letter_tokens=False`` clamps the per-token budget to 1."""
    config = Config(allow_multi_letter_tokens=False, max_letters_per_token=requested)
    assert config.max_letters_per_token == 1


@pytest.mark.parametrize("requested", [1, 2, 3, 9])
def test_allowing_multi_letter_tokens_keeps_the_requested_budget(
    requested: int,
) -> None:
    """The clamp only fires when multi-letter tokens are disallowed."""
    config = Config(allow_multi_letter_tokens=True, max_letters_per_token=requested)
    assert config.max_letters_per_token == requested


def test_clamp_survives_serialisation() -> None:
    """The clamped value is what a dump/rebuild sees, not the requested one."""
    config = Config(allow_multi_letter_tokens=False, max_letters_per_token=4)
    assert config.model_dump()["max_letters_per_token"] == 1
    assert config.with_overrides().max_letters_per_token == 1


# ---------------------------------------------------------------------------
# Frozen-ness and value semantics
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_acronym_length", 9),
        ("language", Language.FR),
        ("case_style", CaseStyle.LOWER),
        ("include_articles", True),
    ],
    ids=lambda value: str(value),
)
def test_config_is_frozen(field: str, value: object) -> None:
    """Assignment to a configured engine's config is a hard error.

    Rebinding an attribute never goes through ``Config.__init__``, so this is
    raised by Pydantic's own frozen-instance guard rather than translated into
    :class:`~acronymkit.exceptions.ConfigurationError`. It is still a
    ``ValueError``.
    """
    config = Config()
    with pytest.raises(ValidationError):
        setattr(config, field, value)


def test_scoring_weights_is_frozen() -> None:
    """The coefficient bundle is immutable too."""
    weights = ScoringWeights()
    with pytest.raises(ValidationError):
        weights.alpha = 2.0


def test_config_compares_and_hashes_by_value() -> None:
    """Two independently built identical configs are equal."""
    left = Config(max_acronym_length=5, language=Language.FR, include_articles=True)
    right = Config(max_acronym_length=5, language=Language.FR, include_articles=True)
    assert left == right
    assert left is not right
    assert Config() != left


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_acronym_length", 5),
        ("language", Language.DE),
        ("hyphen_policy", HyphenPolicy.MERGE),
        ("numeral_policy", NumeralPolicy.SKIP),
        ("require_vowel", True),
    ],
    ids=lambda value: str(value),
)
def test_a_single_differing_field_breaks_equality(field: str, value: object) -> None:
    """Value equality is field-wise, not identity- or subset-based."""
    assert Config(**{field: value}) != Config()


def test_enum_fields_accept_plain_strings() -> None:
    """Callers need not import the enum types."""
    config = Config(
        engine_tier="hybrid_nlp",
        language="fr",
        case_style="lower",
        hyphen_policy="merge",
        numeral_policy="skip",
        scoring_strategy="strict_initialism",
    )
    assert config.engine_tier is EngineTier.HYBRID_NLP
    assert config.language is Language.FR
    assert config.case_style is CaseStyle.LOWER
    assert config.hyphen_policy is HyphenPolicy.MERGE
    assert config.numeral_policy is NumeralPolicy.SKIP
    assert config.scoring_strategy is ScoringStrategy.STRICT_INITIALISM
