"""Engine configuration objects.

:class:`Config` is the single knob-bag threaded through every subsystem. It is
a frozen Pydantic model, so a configured :class:`~acronymkit.engine.AcronymEngine`
is safe to share across threads and event loops.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic import ValidationError as PydanticValidationError

from .enums import (
    CaseStyle,
    EngineTier,
    HyphenPolicy,
    Language,
    NumeralPolicy,
    ScoringStrategy,
    StopWordCategory,
)
from .exceptions import ConfigurationError

__all__ = ["STRATEGY_WEIGHTS", "Config", "ScoringWeights"]


def _describe_validation_error(exc: PydanticValidationError) -> str:
    """Render a Pydantic validation error as a compact, actionable message.

    Args:
        exc: The error raised while validating a :class:`Config`.

    Returns:
        One ``field: message`` clause per problem, joined with ``"; "``. A
        problem with no location (a whole-model check) is reported unqualified.
    """
    problems = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = error.get("msg", "invalid value")
        problems.append(f"{location}: {message}" if location else message)
    return "; ".join(problems) or str(exc)


class ScoringWeights(BaseModel):
    """Coefficients of the composite objective function.

    ``S(A, T) = alpha * sum(omega) + beta * Phi(A) + gamma * Lambda(A)
    - delta * Psi(T, A)``

    The three ``*_weight`` fields are the piecewise values of ``omega`` itself
    and default to the 10/3/2 schedule from the reference formulation.

    Why ``length_penalty`` is non-zero by default
    ---------------------------------------------
    The positional term is a *sum*, so it grows monotonically with acronym
    length: every extra character taken from a token adds ``contiguous_weight``
    and never subtracts anything. Used as a generation objective that is
    degenerate — "Portable Document Format" scores ``PODOFO`` above ``PDF``.
    The reference formulation is a *ranking* function for candidates of a given
    length, so it never had to address this.

    ``length_penalty`` closes the gap, and its default is chosen so the marginal
    economics come out right rather than by taste. With
    ``length_penalty=6`` and ``preferred_length=2`` each additional character
    costs 6, so:

    * covering one more token nets ``initial_weight - 6 = +4``  -> encouraged;
    * taking a second letter from a token already used nets
      ``contiguous_weight - 6 = -4``  -> discouraged;
    * dropping a critical token to shorten the acronym costs ``delta`` and
      forfeits ``initial_weight``, far outweighing the 6 saved -> discouraged.

    Setting ``length_penalty`` between ``contiguous_weight`` and
    ``initial_weight`` therefore makes "one letter per token, cover everything"
    the optimum by construction, while ``gamma`` (a dictionary hit) and ``beta``
    (pronounceability) remain free to tip genuinely close calls. Set it to
    ``0.0`` to recover the unmodified published objective.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    alpha: float = Field(default=1.0, ge=0.0, description="Positional mapping coefficient.")
    beta: float = Field(default=1.0, ge=0.0, description="Phonotactic coefficient.")
    gamma: float = Field(default=12.0, ge=0.0, description="Lexical match coefficient.")
    delta: float = Field(default=15.0, ge=0.0, description="Information-loss coefficient.")

    initial_weight: float = Field(
        default=10.0, description="omega when the character is a token's initial."
    )
    internal_weight: float = Field(
        default=3.0, description="omega for an internal or terminal character."
    )
    contiguous_weight: float = Field(
        default=2.0, description="omega when the character continues a matched run."
    )
    unmapped_penalty: float = Field(
        default=4.0,
        ge=0.0,
        description="Deduction per acronym character with no source token.",
    )
    length_penalty: float = Field(
        default=6.0,
        ge=0.0,
        description="Deduction per character beyond the preferred acronym length. Keeps the "
        "monotone-in-length positional sum from favouring needlessly long acronyms; see the "
        "class docstring. Set to 0.0 for the unmodified published objective.",
    )
    preferred_length: int = Field(
        default=2, ge=1, description="Acronym length exempt from ``length_penalty``."
    )

    def scaled(self, factor: float) -> ScoringWeights:
        """Return a copy with all four primary coefficients scaled uniformly."""
        return self.model_copy(
            update={
                "alpha": self.alpha * factor,
                "beta": self.beta * factor,
                "gamma": self.gamma * factor,
                "delta": self.delta * factor,
            }
        )


#: Preset weighting vectors selected by :class:`~acronymkit.enums.ScoringStrategy`.
#:
#: These are calibrated, not guessed. ``BALANCED_PRONOUNCEABLE`` and
#: ``STRICT_INITIALISM`` were grid-searched against a canonical corpus of
#: textbook initialisms (API, PDF, NASA, HTML, RAM, CPU, GPU, SCUBA, LASER,
#: SQL, CRM, QA, TCP, SOAP, BIOS, ROM) and reproduce all sixteen as the primary
#: result. The winning region is a broad plateau — 266 of 640 sampled vectors
#: satisfy every case — so the defaults are robust rather than overfitted.
#: ``tests/test_scoring_presets.py`` pins the corpus so retuning cannot silently
#: regress it.
STRATEGY_WEIGHTS: dict[ScoringStrategy, ScoringWeights] = {
    # Positional fidelity dominates; pronounceability and dictionary hits are
    # nearly ignored and dropping a critical token is punished hard.
    ScoringStrategy.STRICT_INITIALISM: ScoringWeights(
        alpha=1.0, beta=0.25, gamma=2.0, delta=25.0, length_penalty=8.0, preferred_length=2
    ),
    # Default. Coverage first; pronounceability and dictionary hits break ties.
    ScoringStrategy.BALANCED_PRONOUNCEABLE: ScoringWeights(
        alpha=1.0, beta=1.0, gamma=12.0, delta=15.0, length_penalty=6.0, preferred_length=2
    ),
    # Phonotactics dominate and longer, word-like forms are cheap. For product
    # and project naming, where saying the acronym out loud matters more than
    # representing every token.
    ScoringStrategy.MAX_PRONOUNCEABLE: ScoringWeights(
        alpha=1.0, beta=4.0, gamma=18.0, delta=6.0, length_penalty=2.0, preferred_length=3
    ),
    # A real dictionary word outweighs almost anything else, so backronyms
    # surface whenever one is reachable in the search space. delta stays high
    # enough that the search cannot win by discarding most of the phrase to
    # reach a two-letter word.
    ScoringStrategy.DICTIONARY_BACKRONYM: ScoringWeights(
        alpha=1.0, beta=1.0, gamma=60.0, delta=22.0, length_penalty=3.0, preferred_length=3
    ),
    ScoringStrategy.CUSTOM: ScoringWeights(),
}


class Config(BaseModel):
    """Complete engine configuration.

    Example:
        >>> from acronymkit import Config
        >>> from acronymkit.enums import EngineTier, ScoringStrategy
        >>> config = Config(
        ...     engine_tier=EngineTier.HYBRID_NLP,
        ...     scoring_strategy=ScoringStrategy.BALANCED_PRONOUNCEABLE,
        ...     include_articles=False,
        ...     min_word_length=2,
        ...     max_acronym_length=6,
        ... )
        >>> config.max_acronym_length
        6
    """

    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)

    # -- runtime selection -------------------------------------------------
    engine_tier: EngineTier = Field(
        default=EngineTier.ZERO_DEPENDENCY, description="Requested execution tier."
    )
    scoring_strategy: ScoringStrategy = Field(
        default=ScoringStrategy.BALANCED_PRONOUNCEABLE,
        description="Named preset for the objective-function coefficients.",
    )
    scoring_weights: Optional[ScoringWeights] = Field(
        default=None,
        description="Explicit coefficients. When set, overrides the strategy preset.",
    )
    language: Language = Field(default=Language.EN)
    strict: bool = Field(
        default=False,
        description="Raise TierUnavailableError instead of degrading to a lower tier.",
    )

    # -- token filtering ---------------------------------------------------
    include_articles: bool = Field(
        default=False, description="Allow articles ('the', 'a', 'an') to donate letters."
    )
    include_prepositions: bool = Field(default=False)
    include_conjunctions: bool = Field(default=False)
    include_pronouns: bool = Field(default=False)
    include_auxiliaries: bool = Field(default=False)
    min_word_length: int = Field(
        default=2, ge=1, description="Tokens shorter than this are ineligible."
    )
    custom_stop_words: frozenset[str] = Field(
        default_factory=frozenset, description="Extra case-insensitive words to suppress."
    )
    custom_keep_words: frozenset[str] = Field(
        default_factory=frozenset,
        description="Words that always stay eligible, overriding stop-word filtering.",
    )
    preserve_existing_acronyms: bool = Field(
        default=True,
        description="Treat all-caps tokens ('API', 'XML') as atomic units to reuse verbatim.",
    )

    # -- generation shape --------------------------------------------------
    min_acronym_length: int = Field(default=2, ge=1)
    max_acronym_length: int = Field(default=6, ge=1)
    max_candidates: int = Field(default=25, ge=1, description="Alternatives returned.")
    max_letters_per_token: int = Field(
        default=2, ge=1, description="Upper bound on characters drawn from one token."
    )
    allow_multi_letter_tokens: bool = Field(
        default=True,
        description="Permit a token to donate more than its initial character.",
    )
    allow_token_skipping: bool = Field(
        default=True, description="Permit candidates that omit eligible tokens."
    )
    case_style: CaseStyle = Field(default=CaseStyle.UPPER)
    hyphen_policy: HyphenPolicy = Field(default=HyphenPolicy.SPLIT)
    numeral_policy: NumeralPolicy = Field(default=NumeralPolicy.DIGIT)
    require_dictionary_word: bool = Field(
        default=False, description="Discard candidates that are not real words."
    )
    require_vowel: bool = Field(
        default=False, description="Discard candidates containing no vowel."
    )

    # -- search budget -----------------------------------------------------
    search_beam_width: int = Field(
        default=250, ge=1, description="Beam retained between generation steps."
    )
    max_search_nodes: int = Field(
        default=50_000, ge=1, description="Hard ceiling on enumerated partial candidates."
    )
    search_time_budget_ms: Optional[float] = Field(
        default=None, gt=0.0, description="Wall-clock budget; results are marked truncated."
    )

    # -- resources ---------------------------------------------------------
    lexicon_path: Optional[Path] = Field(
        default=None, description="Override the bundled dictionary used by Lambda(A)."
    )
    ngram_model_path: Optional[Path] = Field(
        default=None, description="Override the bundled character n-gram model."
    )
    stop_words_path: Optional[Path] = Field(
        default=None, description="Override the bundled categorised stop-word resource."
    )
    include_breakdown: bool = Field(
        default=True, description="Attach a ScoreBreakdown to every candidate."
    )

    # -- extraction --------------------------------------------------------
    extraction_max_short_form_length: int = Field(default=10, ge=1)
    extraction_min_short_form_length: int = Field(default=2, ge=1)
    extraction_capture_sentences: bool = Field(
        default=False, description="Attach the enclosing sentence to each extracted pair."
    )

    # ---------------------------------------------------------------------
    @model_validator(mode="after")
    def _validate(self) -> Config:
        if self.min_acronym_length > self.max_acronym_length:
            raise ConfigurationError(
                f"min_acronym_length ({self.min_acronym_length}) exceeds "
                f"max_acronym_length ({self.max_acronym_length})"
            )
        if self.extraction_min_short_form_length > self.extraction_max_short_form_length:
            raise ConfigurationError(
                "extraction_min_short_form_length exceeds extraction_max_short_form_length"
            )
        if self.scoring_strategy is ScoringStrategy.CUSTOM and self.scoring_weights is None:
            raise ConfigurationError("scoring_strategy=CUSTOM requires explicit scoring_weights")
        if not self.allow_multi_letter_tokens and self.max_letters_per_token > 1:
            object.__setattr__(self, "max_letters_per_token", 1)
        return self

    # ---------------------------------------------------------------------
    def __init__(self, **data: Any) -> None:
        """Validate and freeze a configuration.

        Pydantic wraps anything raised inside a validator in its own
        ``ValidationError``, which is not an :class:`AcronymKitError`. That would
        break the contract documented in :mod:`acronymkit.exceptions` — that a
        single ``except AcronymKitError`` at a service boundary catches
        everything this library raises. So the wrapper is unwrapped here and
        re-raised as :class:`~acronymkit.exceptions.ConfigurationError`, which is
        also a ``ValueError`` and therefore still catchable the conventional way.

        Args:
            **data: Field values; see the class attributes.

        Raises:
            ConfigurationError: If any field is invalid or the combination of
                fields is internally inconsistent.
        """
        try:
            super().__init__(**data)
        except ConfigurationError:
            raise
        except PydanticValidationError as exc:
            raise ConfigurationError(_describe_validation_error(exc)) from exc

    # ---------------------------------------------------------------------
    @property
    def weights(self) -> ScoringWeights:
        """Effective coefficients: explicit ``scoring_weights`` or the strategy preset."""
        if self.scoring_weights is not None:
            return self.scoring_weights
        return STRATEGY_WEIGHTS[self.scoring_strategy]

    @property
    def suppressed_categories(self) -> frozenset[StopWordCategory]:
        """Stop-word categories excluded from letter donation under this config."""
        suppressed: set[StopWordCategory] = {
            StopWordCategory.PARTICLE,
            StopWordCategory.DETERMINER,
            StopWordCategory.OTHER,
        }
        if not self.include_articles:
            suppressed.add(StopWordCategory.ARTICLE)
        if not self.include_prepositions:
            suppressed.add(StopWordCategory.PREPOSITION)
        if not self.include_conjunctions:
            suppressed.add(StopWordCategory.CONJUNCTION)
        if not self.include_pronouns:
            suppressed.add(StopWordCategory.PRONOUN)
        if not self.include_auxiliaries:
            suppressed.add(StopWordCategory.AUXILIARY)
        return frozenset(suppressed)

    def with_overrides(self, **overrides: Any) -> Config:
        """Return a validated copy with ``overrides`` applied."""
        return Config(**{**self.model_dump(), **overrides})

    @classmethod
    def preset(cls, strategy: ScoringStrategy, **overrides: Any) -> Config:
        """Build a config from a named strategy preset."""
        return cls(scoring_strategy=ScoringStrategy.coerce(strategy), **overrides)

    @classmethod
    def fast(cls, **overrides: Any) -> Config:
        """Latency-optimised Tier 0 preset for high-throughput pipelines."""
        defaults: dict[str, Any] = {
            "engine_tier": EngineTier.ZERO_DEPENDENCY,
            "scoring_strategy": ScoringStrategy.STRICT_INITIALISM,
            "max_candidates": 5,
            "allow_multi_letter_tokens": False,
            "search_beam_width": 32,
            "include_breakdown": False,
        }
        defaults.update(overrides)
        return cls(**defaults)
