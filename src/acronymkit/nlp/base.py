"""Contract, alignment helpers and tier resolution for Tier 1 NLP backends.

A *backend* turns the deterministic :class:`~acronymkit.models.Token` stream
produced by the Tier 0 tokenizer into a linguistically annotated one: it fills
:attr:`~acronymkit.models.Token.pos` (Universal POS) and
:attr:`~acronymkit.models.Token.lemma`, and may re-label a token between
:attr:`~acronymkit.enums.TokenRole.CONTENT` and
:attr:`~acronymkit.enums.TokenRole.FUNCTION` so that the information-loss term
``Psi(T, A)`` counts the syntactically essential words rather than a surface
stop-word list.

Invariants every backend must honour:

* :class:`~acronymkit.models.Token` is frozen — annotation happens through
  :meth:`pydantic.BaseModel.model_copy`, never in place.
* ``text``, ``normalized``, ``index``, ``start`` and ``end`` are never modified.
* :attr:`~acronymkit.enums.TokenRole.ACRONYM` and
  :attr:`~acronymkit.enums.TokenRole.NUMERAL` assignments made by the tokenizer
  survive annotation untouched, as does every ``is_eligible`` decision.
* A token the backend cannot confidently align to is returned unchanged rather
  than annotated with a guess.

Besides the three names in ``__all__`` this module exposes package-internal
helpers (:class:`Annotation`, :func:`align_by_offsets`,
:func:`align_positionally`, :func:`apply_annotations`, :func:`role_for_pos`)
that the concrete backends in this sub-package share.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, NamedTuple, Optional, Protocol, runtime_checkable

from ..config import Config
from ..enums import EngineTier, Language, TokenRole
from ..exceptions import AcronymKitError, TierUnavailableError
from ..models import Token

__all__ = ["BackendUnavailable", "NlpBackend", "resolve_backend"]


#: Universal POS tags that mark a token as semantically load-bearing.
UNIVERSAL_CONTENT_POS: frozenset[str] = frozenset({"NOUN", "PROPN", "VERB", "ADJ", "NUM"})

#: Universal POS tags that mark a token as a grammatical function word.
UNIVERSAL_FUNCTION_POS: frozenset[str] = frozenset(
    {"DET", "ADP", "CCONJ", "SCONJ", "PRON", "AUX", "PART", "INTJ"}
)

#: Roles the tokenizer owns outright; a backend never overrides them.
PRESERVED_ROLES: frozenset[TokenRole] = frozenset(
    {TokenRole.ACRONYM, TokenRole.NUMERAL, TokenRole.SYMBOL}
)

#: Roles that make a token a member of ``T_critical`` (see ``Psi(T, A)``).
CRITICAL_ROLES: frozenset[TokenRole] = frozenset({TokenRole.CONTENT, TokenRole.ACRONYM})

#: Distributions that satisfy the Tier 1 requirement, in preference order.
NLP_DISTRIBUTIONS: tuple[str, ...] = ("spacy", "nltk")

#: Emitted when a degradable tier could not find any Tier 1 runtime.
NLP_UNAVAILABLE_WARNING = (
    "No Tier 1 NLP backend is installed (tried spaCy, then NLTK); degrading to "
    "the zero-dependency heuristic backend. Install one with: "
    "pip install 'acronymkit[nlp]'."
)

#: Emitted whenever ``EngineTier.NEURAL`` is requested in this release.
NEURAL_NOT_IMPLEMENTED_WARNING = (
    "Tier 2 neural disambiguation is not implemented in this release; the "
    "engine is degrading to the statistical (Tier 1) path."
)

#: How far ahead :func:`align_positionally` looks for a matching surface form.
POSITIONAL_LOOKAHEAD = 8


class BackendUnavailable(AcronymKitError):  # noqa: N818 - name fixed by the API spec
    """Raised when a backend is asked to annotate but its runtime is missing.

    Callers are expected to consult :meth:`NlpBackend.is_available` first;
    this exception exists so that a backend which becomes unusable *after* the
    availability probe (deleted model directory, corrupted corpus) fails with a
    library-owned error rather than a third-party one.
    """


@runtime_checkable
class NlpBackend(Protocol):
    """Structural contract implemented by every linguistic annotator.

    Attributes:
        name: Stable identifier recorded on
            :attr:`~acronymkit.models.EngineMetadata.nlp_backend`, e.g.
            ``"spacy"``, ``"nltk"`` or ``"heuristic"``.
    """

    name: str

    def is_available(self) -> bool:
        """Return whether the backend can annotate right now.

        Implementations never raise: a missing package, a missing model, a
        missing corpus or an incompatible version all report ``False``.
        """
        ...  # pragma: no cover - protocol stub

    def annotate(self, text: str, tokens: list[Token]) -> list[Token]:
        """Return an annotated copy of ``tokens``.

        Args:
            text: The original phrase the tokens were produced from.
            tokens: Tokens emitted by the Tier 0 tokenizer.

        Returns:
            A new list of new :class:`~acronymkit.models.Token` objects.
        """
        ...  # pragma: no cover - protocol stub


class Annotation(NamedTuple):
    """One backend observation, prior to alignment onto our own tokens.

    Attributes:
        text: Surface form as the backend tokenised it.
        pos: Universal POS tag, or ``None`` when the backend produced none.
        lemma: Lemma, or ``None`` when the backend produced none.
        start: Character offset into the annotated text, when the backend
            reports offsets (spaCy does; NLTK does not).
        end: Offset one past the last character, paired with ``start``.
    """

    text: str
    pos: Optional[str] = None
    lemma: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None


def role_for_pos(token: Token, pos: str) -> TokenRole:
    """Return the role ``token`` should carry given the backend's ``pos``.

    The mapping is the one documented on :class:`NlpBackend`: content tags
    promote a token to :attr:`~acronymkit.enums.TokenRole.CONTENT`, function
    tags demote it to :attr:`~acronymkit.enums.TokenRole.FUNCTION`, an ``X`` tag
    on a token containing an uppercase character is treated as content (unknown
    proper nouns and product names tag poorly), and anything else leaves the
    tokenizer's decision alone.

    Args:
        token: Token being annotated.
        pos: Universal POS tag supplied by the backend.

    Returns:
        The role to store on the annotated copy; ``token.role`` when the tag
        carries no usable signal or the role is tokenizer-owned.
    """
    if token.role in PRESERVED_ROLES:
        return token.role
    upos = pos.upper()
    if upos in UNIVERSAL_CONTENT_POS:
        return TokenRole.CONTENT
    if upos == "X" and any(character.isupper() for character in token.text):
        return TokenRole.CONTENT
    if upos in UNIVERSAL_FUNCTION_POS:
        return TokenRole.FUNCTION
    return token.role


def apply_annotation(
    token: Token,
    annotation: Optional[Annotation],
    *,
    update_roles: bool = True,
) -> Token:
    """Return ``token`` with ``annotation`` applied.

    Args:
        token: Frozen token to annotate.
        annotation: Aligned observation, or ``None`` when alignment failed.
        update_roles: When ``True`` the role (and, if it changes,
            ``is_critical``) is recomputed from the POS tag. Tier 0 style
            backends pass ``False`` to fill ``pos`` only.

    Returns:
        A new :class:`~acronymkit.models.Token` when ``annotation`` is not
        ``None``, otherwise the original object untouched. ``text``,
        ``normalized``, ``index``, ``start``, ``end``, ``letters``,
        ``subtokens`` and ``is_eligible`` are never modified.
    """
    if annotation is None:
        return token

    update: dict[str, Any] = {}
    pos = annotation.pos or None
    if pos is not None and pos != token.pos:
        update["pos"] = pos
    if annotation.lemma and annotation.lemma != token.lemma:
        update["lemma"] = annotation.lemma
    if update_roles and pos is not None:
        role = role_for_pos(token, pos)
        if role is not token.role:
            update["role"] = role
            update["is_critical"] = role in CRITICAL_ROLES and token.is_eligible
    return token.model_copy(update=update)


def apply_annotations(
    tokens: Sequence[Token],
    annotations: Sequence[Optional[Annotation]],
    *,
    update_roles: bool = True,
) -> list[Token]:
    """Apply an aligned annotation stream to ``tokens``.

    Args:
        tokens: Tokens to annotate, in order.
        annotations: Positionally aligned observations; entries may be ``None``
            where alignment failed. A short sequence is padded with ``None``.
        update_roles: Forwarded to :func:`apply_annotation`.

    Returns:
        A new list of tokens of the same length as ``tokens``.
    """
    result: list[Token] = []
    for position, token in enumerate(tokens):
        annotation = annotations[position] if position < len(annotations) else None
        result.append(apply_annotation(token, annotation, update_roles=update_roles))
    return result


def align_by_offsets(
    tokens: Sequence[Token],
    annotations: Sequence[Annotation],
) -> list[Optional[Annotation]]:
    """Align backend annotations to ``tokens`` using character offsets.

    Both sequences are swept in ascending offset order, so the cost is linear.
    For each token the candidate set is every annotation overlapping
    ``[token.start, token.end)``. An exactly co-extensive annotation always
    wins. Otherwise, when our token spans several backend tokens (a compound
    such as ``"multi-factor"`` or ``"input/output"``), the *last* overlapping
    annotation carrying a content tag is used — the head of an English compound
    is its right-most element — falling back to the first overlapping
    annotation when none is content-tagged.

    Args:
        tokens: Tokens to align onto.
        annotations: Backend observations; entries lacking offsets are ignored.

    Returns:
        A list parallel to ``tokens`` holding the chosen annotation, or ``None``
        for tokens no annotation overlapped.
    """
    ordered = sorted(
        (
            annotation
            for annotation in annotations
            if annotation.start is not None and annotation.end is not None
        ),
        key=lambda annotation: (annotation.start or 0, annotation.end or 0),
    )
    aligned: list[Optional[Annotation]] = [None] * len(tokens)
    if not ordered:
        return aligned

    cursor = 0
    for position, token in enumerate(tokens):
        while cursor < len(ordered) and (ordered[cursor].end or 0) <= token.start:
            cursor += 1
        window: list[Annotation] = []
        probe = cursor
        while probe < len(ordered) and (ordered[probe].start or 0) < token.end:
            candidate = ordered[probe]
            if (candidate.end or 0) > token.start:
                window.append(candidate)
            probe += 1
        if not window:
            continue
        exact = None
        for candidate in window:
            if candidate.start == token.start and candidate.end == token.end:
                exact = candidate
                break
        if exact is not None:
            aligned[position] = exact
            continue
        if len(window) == 1:
            aligned[position] = window[0]
            continue
        heads = [
            candidate
            for candidate in window
            if (candidate.pos or "").upper() in UNIVERSAL_CONTENT_POS
        ]
        aligned[position] = heads[-1] if heads else window[0]
    return aligned


def align_positionally(
    tokens: Sequence[Token],
    annotations: Sequence[Annotation],
) -> list[Optional[Annotation]]:
    """Align backend annotations to ``tokens`` by matching surface strings.

    Used for backends that do not report character offsets (NLTK). The walk is
    monotonic: for each token the next annotation whose surface form matches
    case-insensitively is consumed, searching at most
    :data:`POSITIONAL_LOOKAHEAD` entries ahead so that one tokenisation
    disagreement cannot cascade. Tokens with no match are left unaligned rather
    than paired with a neighbouring word's tag.

    Args:
        tokens: Tokens to align onto.
        annotations: Backend observations, in the order they were produced.

    Returns:
        A list parallel to ``tokens`` holding the chosen annotation, or ``None``
        where no surface form matched.
    """
    aligned: list[Optional[Annotation]] = [None] * len(tokens)
    cursor = 0
    for position, token in enumerate(tokens):
        surface = token.text.casefold()
        limit = min(len(annotations), cursor + POSITIONAL_LOOKAHEAD)
        probe = cursor
        while probe < limit:
            if annotations[probe].text.casefold() == surface:
                aligned[position] = annotations[probe]
                cursor = probe + 1
                break
            probe += 1
    return aligned


def resolve_backend(config: Config) -> tuple[NlpBackend, list[str]]:
    """Select the annotation backend implied by ``config.engine_tier``.

    Policy, per :class:`~acronymkit.enums.EngineTier`:

    ``ZERO_DEPENDENCY``
        Always the heuristic backend; no warnings.
    ``STATISTICAL_NLP``
        spaCy, else NLTK. Raises when neither is usable — this tier promises
        Tier 1 fidelity and must not silently degrade.
    ``HYBRID_NLP``
        spaCy, else NLTK, else the heuristic backend plus a warning. Raises
        instead of degrading when ``config.strict``.
    ``NEURAL``
        Tier 2 is not implemented in this release, so the statistical path is
        used and a warning is always emitted. Because ``strict`` forbids
        receiving a lower tier than the one requested, ``config.strict`` raises
        unconditionally here — spaCy being installed does not make Tier 2
        available.
    ``AUTO``
        Best available backend, degrading silently with no warnings.

    Args:
        config: Engine configuration; ``engine_tier``, ``language`` and
            ``strict`` are consulted.

    Returns:
        A ``(backend, warnings)`` pair. ``warnings`` is ordered and safe to
        copy straight onto :attr:`~acronymkit.models.EngineMetadata.warnings`.

    Raises:
        TierUnavailableError: If the requested tier cannot be honoured and the
            configuration forbids degradation.
    """
    from .heuristic import HeuristicBackend
    from .nltk_backend import NltkBackend
    from .spacy_backend import SpacyBackend

    tier: EngineTier = config.engine_tier
    language: Language = config.language
    warnings: list[str] = []

    if tier is EngineTier.ZERO_DEPENDENCY:
        return HeuristicBackend(language=language), warnings

    if tier is EngineTier.NEURAL:
        warnings.append(NEURAL_NOT_IMPLEMENTED_WARNING)
        if config.strict:
            raise TierUnavailableError(tier, NLP_DISTRIBUTIONS, extra="nlp")

    spacy_backend = SpacyBackend(language=language)
    if spacy_backend.is_available():
        return spacy_backend, warnings
    nltk_backend = NltkBackend(language=language)
    if nltk_backend.is_available():
        return nltk_backend, warnings

    if tier is EngineTier.STATISTICAL_NLP or (config.strict and tier is not EngineTier.AUTO):
        raise TierUnavailableError(tier, NLP_DISTRIBUTIONS, extra="nlp")

    if tier is not EngineTier.AUTO:
        warnings.append(NLP_UNAVAILABLE_WARNING)
    return HeuristicBackend(language=language), warnings
