"""acronymkit — bi-directional, multi-tiered acronym engine.

One library for the three things production systems do with acronyms:
*generate* them from a phrase, *extract* the ones a document already defines,
and *disambiguate* the ones it does not. Ranking is a single explicit objective
function, ``S(A, T) = alpha * SUM omega + beta * Phi(A) + gamma * Lambda(A)
- delta * Psi(T, A)``, and every result carries the term-by-term breakdown that
produced it.

Example:
    >>> from acronymkit import AcronymEngine, Config
    >>> engine = AcronymEngine(Config(max_candidates=5))
    >>> engine.generate("Portable Document Format").primary_acronym
    'PDF'
    >>> engine.generate_backronym(
    ...     phrase="Next Generation High Performance Storage System",
    ...     target_word="NEXUS",
    ... ).target_word
    'NEXUS'
    >>> pair = engine.extract_definitions(
    ...     "The World Health Organization (WHO) issued guidance."
    ... )[0]
    >>> (pair.short_form, pair.long_form)
    ('WHO', 'World Health Organization')

Import policy:
    Importing this package pulls in the standard library and ``pydantic`` and
    nothing else. spaCy, NLTK, ONNX Runtime, transformers and ``click`` are
    optional extras imported lazily, inside the functions that need them, so
    ``import acronymkit`` stays cheap on a bare production image.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

from .config import STRATEGY_WEIGHTS, Config, ScoringWeights
from .disambiguation import ExpansionDictionary
from .engine import AcronymEngine
from .enums import (
    CaseStyle,
    EngineTier,
    HyphenPolicy,
    Language,
    MappingKind,
    NumeralPolicy,
    ScoringStrategy,
    StopWordCategory,
    TokenRole,
)
from .exceptions import (
    AcronymKitError,
    ConfigurationError,
    EmptyPhraseError,
    GenerationError,
    LexiconError,
    NoCandidateError,
    ResourceNotFoundError,
    TierUnavailableError,
    TokenizationError,
)
from .models import (
    AcronymCandidate,
    AcronymPair,
    AcronymResult,
    BackronymCandidate,
    BackronymResult,
    BatchResult,
    DisambiguationCandidate,
    DisambiguationResult,
    EngineMetadata,
    ExtractionResult,
    LetterMapping,
    ScoreBreakdown,
    Token,
)

try:
    #: Installed distribution version; the single source of truth for
    #: ``EngineMetadata.library_version``.
    __version__ = _distribution_version("acronymkit")
except PackageNotFoundError:  # pragma: no cover - un-installed source checkout
    __version__ = "0.1.0"

__all__ = [
    "STRATEGY_WEIGHTS",
    "AcronymCandidate",
    "AcronymEngine",
    "AcronymKitError",
    "AcronymPair",
    "AcronymResult",
    "BackronymCandidate",
    "BackronymResult",
    "BatchResult",
    "CaseStyle",
    "Config",
    "ConfigurationError",
    "DisambiguationCandidate",
    "DisambiguationResult",
    "EmptyPhraseError",
    "EngineMetadata",
    "EngineTier",
    "ExpansionDictionary",
    "ExtractionResult",
    "GenerationError",
    "HyphenPolicy",
    "Language",
    "LetterMapping",
    "LexiconError",
    "MappingKind",
    "NoCandidateError",
    "NumeralPolicy",
    "ResourceNotFoundError",
    "ScoreBreakdown",
    "ScoringStrategy",
    "ScoringWeights",
    "StopWordCategory",
    "TierUnavailableError",
    "Token",
    "TokenRole",
    "TokenizationError",
    "__version__",
]
