"""Data-transfer objects for the ``acronymkit`` public surface.

Every model is a Pydantic v2 ``BaseModel`` configured as frozen, and the library
itself never mutates a model after construction. Results are therefore safe to
share across threads and to cache. Enum fields serialise to their string values,
making :meth:`AcronymResult.to_dict` directly JSON-encodable and conformant with
``schemas/acronym-engine-result.schema.json``.

Scope of ``frozen`` (please read)
---------------------------------
``frozen=True`` blocks *attribute rebinding* — ``result.primary_acronym = "X"``
raises. It does **not** deep-freeze container fields: ``list`` and ``dict``
fields such as :attr:`AcronymResult.alternatives`,
:attr:`AcronymCandidate.mappings`, :attr:`Token.subtokens`,
:attr:`EngineMetadata.warnings` and :attr:`BatchResult.errors` are ordinary
mutable containers. Calling ``result.alternatives.pop()`` will silently corrupt
the object, and helpers such as :attr:`AcronymResult.primary` may then fail.

Treat every returned model as read-only. If you need a sorted or filtered view,
copy first (``sorted(result.alternatives, key=...)``), and use
``model_copy(update=...)`` to derive a changed model.

For the same reason these models are **not hashable** despite being frozen:
``hash(result)`` raises ``TypeError`` because of the list fields. Key caches on
``result.source_phrase`` or ``result.to_json()`` instead.

Converting the container fields to true immutable sequences is tracked for a
future release; it is a breaking change to the type annotations, so it is not
being made in a patch.

Style contract for contributors: annotations use PEP 585 builtin generics
(``list[str]``) but ``typing.Optional`` rather than PEP 604 ``X | None``, so the
package remains importable on Python 3.9.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from .enums import EngineTier, Language, MappingKind, StopWordCategory, TokenRole

__all__ = [
    "AcronymCandidate",
    "AcronymPair",
    "AcronymResult",
    "BackronymCandidate",
    "BackronymResult",
    "BatchResult",
    "DisambiguationCandidate",
    "DisambiguationResult",
    "EngineMetadata",
    "ExtractionResult",
    "LetterMapping",
    "ScoreBreakdown",
    "Token",
]


class _Frozen(BaseModel):
    """Shared configuration: frozen, enum-values-on-dump, strict extras."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
        validate_assignment=False,
        ser_json_inf_nan="constants",
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a plain JSON-compatible ``dict`` (enums rendered as strings)."""
        return self.model_dump(mode="json")

    def to_json(self, *, indent: Optional[int] = None) -> str:
        """Serialise to a JSON string.

        Args:
            indent: Passed through to :func:`json.dumps`; ``None`` yields the
                compact representation preferred for wire transfer.
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class Token(_Frozen):
    """A single analysed unit of the source phrase."""

    text: str = Field(description="Surface form exactly as it appeared in the input.")
    normalized: str = Field(description="Case-folded, accent-preserving form used for matching.")
    index: int = Field(ge=0, description="Zero-based position in the token sequence.")
    start: int = Field(ge=0, description="Character offset of the token start.")
    end: int = Field(ge=0, description="Character offset one past the token end.")
    role: TokenRole = Field(
        default=TokenRole.UNKNOWN, description="Semantic role used by Psi(T, A)."
    )
    stop_word_category: Optional[StopWordCategory] = Field(
        default=None,
        description="Grammatical class when the token is a known function word.",
    )
    pos: Optional[str] = Field(
        default=None, description="Universal POS tag, when a Tier 1 backend supplied one."
    )
    lemma: Optional[str] = Field(default=None, description="Lemma, when available.")
    is_critical: bool = Field(
        default=False,
        description="Member of T_critical; omission is penalised by Psi(T, A).",
    )
    is_eligible: bool = Field(
        default=True,
        description="Whether the active configuration permits this token to donate letters.",
    )
    letters: str = Field(
        default="",
        description="Ordered characters this token may contribute to a candidate.",
    )
    subtokens: list[str] = Field(
        default_factory=list,
        description="Compound components for hyphenated/slashed/camelCase tokens.",
    )


class LetterMapping(_Frozen):
    """Alignment of one acronym character to a source token.

    Records the piecewise ``omega(c_i, w_j(i))`` decision so that scoring is
    fully auditable from the result payload.
    """

    character: str = Field(min_length=1, max_length=1)
    position: int = Field(ge=0, description="Index of the character within the acronym.")
    token_index: Optional[int] = Field(
        default=None, description="Index of the aligned token, or ``None`` if unmapped."
    )
    char_offset: Optional[int] = Field(
        default=None, description="Offset of the character inside the aligned token."
    )
    kind: MappingKind = Field(default=MappingKind.UNMAPPED)
    weight: float = Field(default=0.0, description="Value of omega for this mapping.")


class ScoreBreakdown(_Frozen):
    """Per-term decomposition of the composite objective ``S(A, T)``.

    ``total = alpha * positional + beta * phonotactic + gamma * lexical
    - delta * information_loss``
    """

    positional: float = Field(description="Sum of omega over all mapped characters.")
    phonotactic: float = Field(description="Phi(A): mean character-bigram log-likelihood.")
    lexical: float = Field(description="Lambda(A): 1.0 on a dictionary hit, else 0.0.")
    information_loss: float = Field(description="Psi(T, A): count of dropped critical tokens.")
    alpha: float
    beta: float
    gamma: float
    delta: float
    total: float

    def explain(self) -> str:
        """Human-readable one-line arithmetic trace of the score."""
        return (
            f"S = {self.alpha:g}*{self.positional:.3f} "
            f"+ {self.beta:g}*{self.phonotactic:.3f} "
            f"+ {self.gamma:g}*{self.lexical:.3f} "
            f"- {self.delta:g}*{self.information_loss:.3f} "
            f"= {self.total:.3f}"
        )


class AcronymCandidate(_Frozen):
    """A single scored acronym proposal."""

    acronym: str
    score: float
    is_dictionary_word: bool = False
    pronounceability_score: float = Field(
        default=0.0,
        description="Phi(A) rescaled to [0, 1]; 1.0 is maximally word-like.",
    )
    raw_phonotactic_score: float = Field(
        default=0.0, description="Unscaled Phi(A) in log space (always <= 0)."
    )
    mappings: list[LetterMapping] = Field(default_factory=list)
    covered_token_indices: list[int] = Field(default_factory=list)
    skipped_token_indices: list[int] = Field(default_factory=list)
    breakdown: Optional[ScoreBreakdown] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def length(self) -> int:
        """Number of characters in the acronym."""
        return len(self.acronym)


class EngineMetadata(_Frozen):
    """Observability envelope attached to every engine result."""

    engine_tier: EngineTier
    execution_time_ms: float = Field(ge=0.0)
    tokens_processed: int = Field(ge=0)
    candidates_evaluated: int = Field(default=0, ge=0)
    language: Language = Language.EN
    library_version: str = ""
    nlp_backend: Optional[str] = Field(
        default=None, description="Resolved Tier 1 backend name, e.g. 'spacy' or 'nltk'."
    )
    requested_tier: Optional[EngineTier] = Field(
        default=None,
        description="Tier asked for before availability resolution; differs from "
        "``engine_tier`` when the engine degraded.",
    )
    warnings: list[str] = Field(default_factory=list)
    truncated: bool = Field(
        default=False,
        description="True when the candidate search hit a beam or time budget.",
    )


class AcronymResult(_Frozen):
    """Result of forward acronym generation.

    Serialises to a payload conformant with the ``AcronymEngineResult`` JSON
    Schema published in ``schemas/acronym-engine-result.schema.json``.
    """

    source_phrase: str
    primary_acronym: str
    score: float = Field(default=0.0, description="Score of the primary acronym.")
    alternatives: list[AcronymCandidate] = Field(default_factory=list)
    tokens: list[Token] = Field(default_factory=list)
    metadata: EngineMetadata

    @property
    def primary(self) -> Optional[AcronymCandidate]:
        """The full candidate record backing :attr:`primary_acronym`."""
        for candidate in self.alternatives:
            if candidate.acronym == self.primary_acronym:
                return candidate
        return self.alternatives[0] if self.alternatives else None

    def top(self, n: int = 5) -> list[AcronymCandidate]:
        """Return the ``n`` highest-scoring candidates."""
        return self.alternatives[:n]

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.primary_acronym} ({self.score:.2f}) <- {self.source_phrase!r}"


class AcronymPair(_Frozen):
    """A short-form/long-form pair recovered from running text."""

    short_form: str
    long_form: str
    short_form_span: tuple[int, int] = Field(
        default=(0, 0), description="Character offsets of the short form in the source."
    )
    long_form_span: tuple[int, int] = Field(
        default=(0, 0), description="Character offsets of the long form in the source."
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    pattern: str = Field(
        default="long(short)",
        description="Which parenthetical arrangement matched: 'long(short)' or 'short(long)'.",
    )
    sentence: Optional[str] = Field(
        default=None, description="Enclosing sentence, when sentence context was retained."
    )

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.short_form} = {self.long_form}"


class ExtractionResult(_Frozen):
    """Result of extractive parenthetical abbreviation detection."""

    source_text: str
    pairs: list[AcronymPair] = Field(default_factory=list)
    metadata: EngineMetadata

    def as_mapping(self) -> dict[str, str]:
        """Collapse the pairs into a ``{short_form: long_form}`` dictionary.

        The first occurrence of each short form wins, matching the convention
        that a document defines an abbreviation once, on first use.
        """
        mapping: dict[str, str] = {}
        for pair in self.pairs:
            mapping.setdefault(pair.short_form, pair.long_form)
        return mapping


class BackronymCandidate(_Frozen):
    """One alignment of a source phrase onto a fixed target word."""

    target_word: str
    expansion: list[str] = Field(
        default_factory=list, description="Chosen source word per target letter."
    )
    expansion_text: str = ""
    score: float = 0.0
    coverage: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Fraction of target letters that were mapped."
    )
    mappings: list[LetterMapping] = Field(default_factory=list)
    unmapped_letters: list[str] = Field(default_factory=list)
    breakdown: Optional[ScoreBreakdown] = None


class BackronymResult(_Frozen):
    """Result of backronym synthesis against a target word."""

    source_phrase: str
    target_word: str
    primary_expansion: str = ""
    score: float = 0.0
    candidates: list[BackronymCandidate] = Field(default_factory=list)
    metadata: EngineMetadata


class DisambiguationCandidate(_Frozen):
    """A scored expansion hypothesis for an ambiguous standalone acronym."""

    expansion: str
    score: float
    source: str = Field(
        default="dictionary",
        description="Provenance: 'inline' (document-local definition), "
        "'dictionary' (expansion index) or 'neural'.",
    )
    evidence: list[str] = Field(
        default_factory=list, description="Context terms that supported this hypothesis."
    )


class DisambiguationResult(_Frozen):
    """Resolution of one acronym occurrence within its context."""

    acronym: str
    context: str
    primary_expansion: Optional[str] = None
    candidates: list[DisambiguationCandidate] = Field(default_factory=list)
    metadata: EngineMetadata


class BatchResult(_Frozen):
    """Envelope returned by the batch/async APIs.

    ``results`` is positionally aligned with the submitted inputs; a ``None``
    entry marks an input that failed, with the reason recorded in
    :attr:`errors` under the same index.
    """

    results: list[Optional[AcronymResult]] = Field(default_factory=list)
    errors: dict[int, str] = Field(default_factory=dict)
    total_execution_time_ms: float = 0.0

    @property
    def succeeded(self) -> list[AcronymResult]:
        """Non-``None`` results, in submission order."""
        return [r for r in self.results if r is not None]

    @property
    def failure_count(self) -> int:
        return len(self.errors)
