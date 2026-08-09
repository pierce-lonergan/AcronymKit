"""Enumerations shared across every ``acronymkit`` subsystem.

All enums derive from :class:`str` so that they serialise transparently to JSON
and can be supplied as plain strings by callers who do not wish to import the
enum types (``Config(engine_tier="hybrid_nlp")`` is equivalent to
``Config(engine_tier=EngineTier.HYBRID_NLP)``).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Type, TypeVar

_E = TypeVar("_E", bound="_StrEnum")

__all__ = [
    "CaseStyle",
    "EngineTier",
    "HyphenPolicy",
    "Language",
    "MappingKind",
    "NumeralPolicy",
    "ScoringStrategy",
    "StopWordCategory",
    "TokenRole",
]


class _StrEnum(str, Enum):
    """Base class giving every member a stable ``str`` identity."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)

    @classmethod
    def coerce(cls: Type[_E], value: object) -> _E:
        """Return the member matching ``value`` by value *or* case-insensitive name.

        Generic in the concrete enum, so ``Language.coerce(x)`` narrows to
        ``Language`` rather than widening to the base class.

        Raises:
            ValueError: if ``value`` does not correspond to any member.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalised = value.strip().lower().replace("-", "_")
            for member in cls:
                if member.value == normalised or member.name.lower() == normalised:
                    return member
        raise ValueError(
            f"{value!r} is not a valid {cls.__name__}; expected one of {[m.value for m in cls]}"
        )


class EngineTier(_StrEnum):
    """Execution tier selecting the cost/accuracy trade-off of the engine.

    The tiers form the multi-tiered runtime described in the architecture:

    ``ZERO_DEPENDENCY``
        Tier 0. Pure-stdlib deterministic path: optimised regular expressions,
        categorised stop-word filtering and character-position rules. Targets
        sub-millisecond execution on resource-constrained instances.
    ``STATISTICAL_NLP``
        Tier 1. Requires an installed NLP runtime (spaCy or NLTK). Uses
        part-of-speech tags and lemmas so that syntactically essential tokens
        outrank auxiliary function words. Raises if no backend is installed.
    ``HYBRID_NLP``
        Tier 1 with automatic Tier 0 degradation: uses an NLP backend when one
        is importable and silently falls back to the deterministic path
        otherwise, recording a warning on the result metadata.
    ``NEURAL``
        Tier 2. Contextual transformer embeddings for acronym disambiguation.
        Reserved for the Phase 3 milestone; selecting it today degrades to the
        lexical disambiguation backend unless ``Config.strict`` is set.
    ``AUTO``
        Resolve to the highest tier whose dependencies are importable.
    """

    ZERO_DEPENDENCY = "zero_dependency"
    STATISTICAL_NLP = "statistical_nlp"
    HYBRID_NLP = "hybrid_nlp"
    NEURAL = "neural"
    AUTO = "auto"

    @property
    def rank(self) -> int:
        """Numeric tier index (``AUTO`` reports ``-1``; it is resolved first)."""
        return _TIER_RANKS[self]

    @property
    def requires_nlp(self) -> bool:
        """Whether the tier needs an optional NLP runtime to reach full fidelity."""
        return self in (
            EngineTier.STATISTICAL_NLP,
            EngineTier.HYBRID_NLP,
            EngineTier.NEURAL,
        )

    @property
    def allows_degradation(self) -> bool:
        """Whether unmet dependencies may silently downgrade instead of raising."""
        return self in (EngineTier.HYBRID_NLP, EngineTier.AUTO)


_TIER_RANKS = {
    EngineTier.AUTO: -1,
    EngineTier.ZERO_DEPENDENCY: 0,
    EngineTier.STATISTICAL_NLP: 1,
    EngineTier.HYBRID_NLP: 1,
    EngineTier.NEURAL: 2,
}


class ScoringStrategy(_StrEnum):
    """Named preset for the ``(alpha, beta, gamma, delta)`` weighting vector.

    Each preset re-balances the composite objective ``S(A, T)``:

    ``STRICT_INITIALISM``
        **Default.** Maximise positional fidelity. Reproduces the classic
        first-letter initialism ("Portable Document Format" -> "PDF") across
        the whole canonical corpus, robustly.
    ``BALANCED_PRONOUNCEABLE``
        Trades positional fidelity for phonotactic quality and rewards
        dictionary hits. This is a real trade, not a safer default: it will
        return "QUA" for "Quality Assurance", because "qua" is a word and the
        strategy values that over the literal initialism. Pick it when you want
        a sayable acronym and can accept a deviation.
    ``MAX_PRONOUNCEABLE``
        Dominated by the phonotactic index; suitable for product naming.
    ``DICTIONARY_BACKRONYM``
        Dominated by the lexical match indicator; only real words survive
        ranking when a dictionary hit exists.
    ``CUSTOM``
        Sentinel indicating that ``Config.scoring_weights`` is authoritative.
    """

    STRICT_INITIALISM = "strict_initialism"
    BALANCED_PRONOUNCEABLE = "balanced_pronounceable"
    MAX_PRONOUNCEABLE = "max_pronounceable"
    DICTIONARY_BACKRONYM = "dictionary_backronym"
    CUSTOM = "custom"


class TokenRole(_StrEnum):
    """Semantic role assigned to a token by the tokenizer / NLP backend.

    ``CONTENT`` tokens are the ones counted by the information-loss penalty
    ``Psi(T, A)``; dropping them costs the candidate score.
    """

    CONTENT = "content"
    FUNCTION = "function"
    NUMERAL = "numeral"
    SYMBOL = "symbol"
    ACRONYM = "acronym"
    UNKNOWN = "unknown"


class StopWordCategory(_StrEnum):
    """Grammatical class of a stop word.

    Categorising rather than flattening the stop-word list is what allows
    ``Config.include_articles`` / ``include_prepositions`` /
    ``include_conjunctions`` to be toggled independently.
    """

    ARTICLE = "article"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    PRONOUN = "pronoun"
    AUXILIARY = "auxiliary"
    DETERMINER = "determiner"
    PARTICLE = "particle"
    OTHER = "other"


class CaseStyle(_StrEnum):
    """Casing applied to generated acronym strings."""

    UPPER = "upper"
    LOWER = "lower"
    TITLE = "title"
    PRESERVE = "preserve"

    def apply(self, value: str) -> str:
        """Return ``value`` re-cased according to this style."""
        if self is CaseStyle.UPPER:
            return value.upper()
        if self is CaseStyle.LOWER:
            return value.lower()
        if self is CaseStyle.TITLE:
            return value[:1].upper() + value[1:].lower() if value else value
        return value


class MappingKind(_StrEnum):
    """Kind of alignment between an acronym character and a source token.

    Mirrors the piecewise definition of the positional mapping weight
    ``omega(c_i, w_j(i))``: ``INITIAL`` scores 10, ``INTERNAL`` scores 3,
    ``CONTIGUOUS`` scores 2 and ``UNMAPPED`` scores 0 (and additionally
    attracts the unmapped-letter penalty).
    """

    INITIAL = "initial"
    INTERNAL = "internal"
    CONTIGUOUS = "contiguous"
    UNMAPPED = "unmapped"


class Language(_StrEnum):
    """Languages with bundled stop-word, lexicon and n-gram resources."""

    EN = "en"
    FR = "fr"
    ES = "es"
    DE = "de"

    @property
    def display_name(self) -> str:
        return _LANGUAGE_NAMES[self]

    @classmethod
    def from_tag(cls, tag: str) -> Language:
        """Parse a BCP-47-ish tag (``"en-GB"``, ``"fr_FR"``) into a member."""
        primary = tag.replace("_", "-").split("-", 1)[0]
        return cls.coerce(primary)


_LANGUAGE_NAMES = {
    Language.EN: "English",
    Language.FR: "French",
    Language.ES: "Spanish",
    Language.DE: "German",
}


class HyphenPolicy(_StrEnum):
    """How hyphenated / slashed compounds contribute candidate letters.

    ``SPLIT``
        ``"Multi-Factor"`` yields the letters ``M`` and ``F`` (two sub-tokens).
    ``MERGE``
        ``"Multi-Factor"`` is a single token contributing ``M``.
    ``FIRST_ONLY``
        Sub-tokens are retained for text offsets but only the first may donate
        an initial character.
    """

    SPLIT = "split"
    MERGE = "merge"
    FIRST_ONLY = "first_only"


class NumeralPolicy(_StrEnum):
    """How numeric tokens are rendered inside a generated acronym.

    ``DIGIT``
        ``"3 Dimensional"`` -> ``"3D"``.
    ``WORD``
        The numeral is spelled out and its initial taken: ``"3"`` -> ``"T"``.
    ``SKIP``
        Numeric tokens never donate characters.
    """

    DIGIT = "digit"
    WORD = "word"
    SKIP = "skip"


def coerce_optional(enum_cls: Type[_E], value: object) -> Optional[_E]:
    """Coerce ``value`` to ``enum_cls`` unless it is ``None``.

    Args:
        enum_cls: Any :class:`_StrEnum` subclass declared in this module.
        value: The value to coerce, or ``None``.

    Returns:
        The matching member, or ``None`` when ``value`` is ``None``.

    Raises:
        ValueError: if ``value`` is neither ``None`` nor a valid member.
    """
    if value is None:
        return None
    return enum_cls.coerce(value)
