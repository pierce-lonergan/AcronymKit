"""Composite scoring engine — the mathematical core of :mod:`acronymkit`.

This module holds the single implementation of the objective function
``S(A, T)`` that ranks a candidate acronym ``A`` against the token sequence
``T`` it was derived from. Forward generation, backronym alignment and the
public ``score`` API all funnel through :class:`Scorer`, so the arithmetic is
defined in exactly one place.

Mathematical contract
---------------------

::

    S(A, T) = alpha * SUM_i omega(c_i, w_j(i))
            + beta  * Phi(A)
            + gamma * Lambda(A)
            - delta * Psi(T, A)

    omega(c_i, w) = 10 if c_i is the INITIAL character of w
                     3 if c_i is an INTERNAL or TERMINAL character of w
                     2 if c_i directly FOLLOWS a previously matched character in w
                     0 if UNMAPPED  (and costs `weights.unmapped_penalty` off
                                     the positional term)

    Phi(A) = (1 / (k - 1)) * SUM_{m=1}^{k-1} log P(c_{m+1} | c_m)   # k = len(A)
    Lambda(A) = 1.0 if A is in the target-language lexicon else 0.0
    Psi(T, A) = count of tokens in T_critical (``Token.is_critical is True``)
                not represented in A

The numeric constants ``10 / 3 / 2`` are *not* hard-coded here: they live in
:attr:`~acronymkit.config.ScoringWeights.initial_weight`,
:attr:`~acronymkit.config.ScoringWeights.internal_weight` and
:attr:`~acronymkit.config.ScoringWeights.contiguous_weight`. The coefficients
``alpha``/``beta``/``gamma``/``delta`` live on the same object and are resolved
through :attr:`~acronymkit.config.Config.weights`, which honours either an
explicit ``scoring_weights`` override or the active ``ScoringStrategy`` preset.

:class:`~acronymkit.enums.MappingKind.CONTIGUOUS` takes precedence over
``INTERNAL`` when a character is both internal *and* directly follows the
previously matched character of the *same* token. ``INITIAL`` outranks both:
character offset ``0`` is always ``INITIAL``, never ``CONTIGUOUS``.

On top of ``S(A, T)``, :meth:`Scorer.score` applies the configurable
length penalty declared by :class:`~acronymkit.config.ScoringWeights`::

    total = S(A, T) - weights.length_penalty
                      * max(0, len(A) - weights.preferred_length)

``length_penalty`` defaults to ``6.0`` with ``preferred_length`` of ``2``, so
``total`` is **not** identical to ``S(A, T)`` under the shipped defaults: an
acronym of length ``k`` is charged ``6 * max(0, k - 2)``.

That deduction is deliberate and is what makes the objective usable for
*generation* rather than only for ranking. The positional term is a sum, so it
grows monotonically with length — without a length term the search prefers
``PODOFO`` to ``PDF``, since every extra character adds
``contiguous_weight`` and subtracts nothing. See
:class:`~acronymkit.config.ScoringWeights` for the marginal-cost reasoning
behind the default value.

Set ``length_penalty=0.0`` to recover the unmodified published objective, in
which case ``total == S(A, T)`` exactly.

Dependency policy
-----------------

:class:`~acronymkit.lexicon.Lexicon` and
:class:`~acronymkit.phonetics.CharNGramModel` are imported **only** under
``typing.TYPE_CHECKING``, purely to type the constructor. At run time the
scorer is duck-typed and imports neither module:

* the lexicon needs only ``contains(word: str) -> bool``;
* the n-gram model needs only ``score(acronym: str) -> float`` and
  ``normalized_score(acronym: str) -> float``.

That keeps the package dependency graph acyclic — ``generator``, ``backronym``
and ``engine`` all depend on ``scoring``, while ``scoring`` itself depends on
nothing beyond the frozen ``config``/``enums``/``models`` triple — makes this
module importable in isolation, and lets tests inject trivial stubs instead of
loading real resource files.

Determinism
-----------

Every function here is pure: no I/O, no clock, no randomness, no
set-iteration-order dependence in any returned value (index collections are
sorted before they leave the module). :class:`Scorer` stores only immutable
references and therefore holds no mutable state, so a single instance is safe
to share across threads. A *substituted* scorer inherits none of that by
default, which is why :class:`~acronymkit.engine.AcronymEngine` documents its
thread-safety guarantee as conditional on what was injected.

Substituting a scorer
---------------------

:class:`~acronymkit.engine.AcronymEngine` accepts ``scorer=``. A custom scorer
owns the ranking of every candidate the engine returns and owns none of the
search that produced them — see "Substituting a scorer" on :class:`Scorer` for
the exact boundary, and for the result field that reports when it binds.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, AbstractSet, Optional, Sequence

from .config import Config, ScoringWeights
from .enums import MappingKind
from .models import AcronymCandidate, LetterMapping, ScoreBreakdown, Token

if TYPE_CHECKING:  # pragma: no cover - typing only, never imported at run time
    from .lexicon import Lexicon
    from .phonetics import CharNGramModel

__all__ = ["Scorer", "build_mappings"]

#: ``omega`` for an unmapped acronym character. The character additionally
#: costs :attr:`ScoringWeights.unmapped_penalty` off the positional term.
_UNMAPPED_WEIGHT = 0.0

#: Pronounceability reported when no n-gram model is available. Neutral by
#: construction: the midpoint of ``[0, 1]`` asserts neither that the acronym is
#: word-like nor that it is unpronounceable.
_NEUTRAL_PRONOUNCEABILITY = 0.5

#: An acronym is a dictionary word when ``Lambda(A)`` reaches this value.
_LEXICAL_HIT = 1.0


def _omega(kind: MappingKind, weights: ScoringWeights) -> float:
    """Return the positional weight ``omega`` for a single mapping kind.

    Args:
        kind: The classification produced by :func:`build_mappings`.
        weights: Coefficient bundle supplying the 10/3/2 schedule.

    Returns:
        ``weights.initial_weight``, ``weights.contiguous_weight``,
        ``weights.internal_weight`` or ``0.0`` for ``UNMAPPED``.
    """
    if kind == MappingKind.INITIAL:
        return float(weights.initial_weight)
    if kind == MappingKind.CONTIGUOUS:
        return float(weights.contiguous_weight)
    if kind == MappingKind.INTERNAL:
        return float(weights.internal_weight)
    return _UNMAPPED_WEIGHT


def _classify(
    token_index: Optional[int],
    char_offset: Optional[int],
    previous_token_index: Optional[int],
    previous_char_offset: Optional[int],
) -> MappingKind:
    """Classify one acronym character against the mapping that preceded it.

    The decision order encodes the precedence rule from the mathematical
    contract: ``UNMAPPED`` > ``INITIAL`` > ``CONTIGUOUS`` > ``INTERNAL``.

    Args:
        token_index: Aligned token index, or ``None`` when the character has no
            source token.
        char_offset: Offset of the character inside the aligned token, or
            ``None`` when unknown.
        previous_token_index: ``token_index`` of the immediately preceding
            mapping, if any.
        previous_char_offset: ``char_offset`` of the immediately preceding
            mapping, if any.

    Returns:
        The :class:`~acronymkit.enums.MappingKind` describing the alignment.
        A mapped character with an unknown (``None``) offset can be neither
        ``INITIAL`` nor ``CONTIGUOUS`` and is therefore ``INTERNAL``.
    """
    if token_index is None:
        return MappingKind.UNMAPPED
    if char_offset == 0:
        return MappingKind.INITIAL
    if (
        char_offset is not None
        and previous_char_offset is not None
        and token_index == previous_token_index
        and char_offset == previous_char_offset + 1
    ):
        return MappingKind.CONTIGUOUS
    return MappingKind.INTERNAL


def build_mappings(
    acronym: str,
    assignments: Sequence[tuple[int, Optional[int], Optional[int]]],
    tokens: Sequence[Token],
    weights: ScoringWeights,
) -> list[LetterMapping]:
    """Turn raw ``(position, token_index, char_offset)`` triples into mappings.

    Each entry of ``assignments`` describes one character of ``acronym``:
    ``assignments[i] == (position, token_index, char_offset)`` where
    ``position`` indexes into ``acronym``, ``token_index`` indexes into
    ``tokens`` (``None`` when the character came from nowhere) and
    ``char_offset`` is the character's offset inside that token (``0`` for the
    token's initial).

    Classification, in precedence order:

    * ``token_index is None`` -> ``UNMAPPED`` (weight ``0``);
    * ``char_offset == 0`` -> ``INITIAL`` (``weights.initial_weight``);
    * same ``token_index`` as the previous mapping **and**
      ``char_offset == previous char_offset + 1`` -> ``CONTIGUOUS``
      (``weights.contiguous_weight``);
    * otherwise ``INTERNAL`` (``weights.internal_weight``).

    "Previous" means the immediately preceding element of ``assignments``,
    whatever its kind; a preceding ``UNMAPPED`` character therefore breaks a
    contiguous run.

    Args:
        acronym: The candidate acronym string the assignments describe.
        assignments: Ordered ``(position, token_index, char_offset)`` triples.
        tokens: Token sequence the ``token_index`` values refer to; used to
            bounds-check the alignment.
        weights: Coefficient bundle supplying ``omega``.

    Returns:
        A list of :class:`~acronymkit.models.LetterMapping`, one per entry of
        ``assignments``, in the order supplied.

    Raises:
        ValueError: If a ``position`` is outside ``acronym`` or a non-``None``
            ``token_index`` is outside ``tokens``.
    """
    mappings: list[LetterMapping] = []
    acronym_length = len(acronym)
    token_count = len(tokens)
    previous_token_index: Optional[int] = None
    previous_char_offset: Optional[int] = None

    for position, token_index, char_offset in assignments:
        if not 0 <= position < acronym_length:
            raise ValueError(
                f"assignment position {position} is outside acronym {acronym!r} "
                f"of length {acronym_length}"
            )
        if token_index is not None and not 0 <= token_index < token_count:
            raise ValueError(
                f"assignment token_index {token_index} is outside the token "
                f"sequence of length {token_count}"
            )
        kind = _classify(token_index, char_offset, previous_token_index, previous_char_offset)
        mappings.append(
            LetterMapping(
                character=acronym[position],
                position=position,
                token_index=token_index,
                char_offset=char_offset,
                kind=kind,
                weight=_omega(kind, weights),
            )
        )
        previous_token_index = token_index
        previous_char_offset = char_offset

    return mappings


class Scorer:
    """Evaluate ``S(A, T)`` for candidate acronyms.

    The scorer is immutable and side-effect free; construct one per engine and
    share it freely across threads.

    Both optional collaborators are duck-typed and may be ``None``:

    * ``lexicon is None`` -> ``Lambda(A)`` is always ``0.0``;
    * ``ngram is None`` -> ``Phi(A)`` is ``0.0`` and the reported
      pronounceability is the neutral ``0.5``.

    Substituting a scorer
    ---------------------
    This is a plain class, so a caller may subclass it, override :meth:`score`
    or :meth:`build_candidate`, and hand the result to
    :class:`~acronymkit.engine.AcronymEngine` as ``scorer=``. Doing so decides
    the ranking of every candidate the engine returns, everywhere: forward
    generation, backronym alignment and :meth:`AcronymEngine.score
    <acronymkit.engine.AcronymEngine.score>` all read
    :attr:`~acronymkit.models.AcronymCandidate.score` off this object.

    It decides the ranking. It does **not** decide which candidates exist, and
    the difference is not a detail. Forward generation is a search, and the
    search ranks its own partial frontier with
    ``ForwardGenerator._beam_bound``, which re-derives the objective in closed
    form from :class:`~acronymkit.config.ScoringWeights` — the ``alpha``,
    ``gamma`` and ``delta`` coefficients, the ``omega`` schedule and the length
    penalty — and never calls this object at all. A custom term therefore
    re-ranks the states the search retained; it cannot cause the search to
    retain a state it would otherwise have cut, no matter how large the term
    is. Nor can it change the search *space*: that is fixed by
    ``max_acronym_length``, ``max_letters_per_token``,
    ``allow_multi_letter_tokens`` and ``allow_token_skipping``, which a scorer
    does not see.

    **The limit binds only when the search actually discards something, and
    the result usually says whether it did.**
    :attr:`~acronymkit.models.EngineMetadata.truncated` is ``True`` exactly when
    a frontier cut, a node budget or a time budget cost the search states it
    never scored. When it is ``False`` — which covers the exhaustive regime
    :mod:`acronymkit.generator` documents, and every beam-mode call whose
    frontier never overflowed — no cut and no budget discarded anything, so a
    custom scorer ranked every candidate the search reached and the limit above
    is vacuous.

    One configuration escapes that reading, and a caller substituting a scorer
    is the caller most likely to hit it. With ``allow_token_skipping=False`` and
    a ``max_acronym_length`` that every remaining branch of some later token
    overflows, the search cannot continue: it abandons the whole frontier
    unscored and the result is the injected plain initialism alone — with
    ``truncated`` still ``False``, because neither a cut nor a budget was
    responsible. A custom scorer is handed exactly one candidate there,
    whatever it would have preferred. ``len(result.alternatives) == 1`` on a
    multi-token phrase is the symptom.

    The supported way to buy that regime back on a phrase where it does not
    hold is to raise :attr:`~acronymkit.config.Config.max_search_nodes` until
    the whole space fits, which removes the frontier cut entirely rather than
    biasing it; :mod:`acronymkit.generator` documents what that costs. Widening
    :attr:`~acronymkit.config.Config.search_beam_width` narrows the gap without
    closing it. Neither is a workaround for a missing hook — the exhaustive
    regime is the generator's documented exactness guarantee, and it is the
    only regime in which any objective, custom or shipped, ranks the complete
    space.

    Extraction and disambiguation do not consult a scorer at all, so nothing
    here applies to them.

    Example:
        >>> from acronymkit.config import Config
        >>> from acronymkit.enums import MappingKind
        >>> from acronymkit.models import LetterMapping
        >>> scorer = Scorer(Config())
        >>> mapping = LetterMapping(
        ...     character="A", position=0, token_index=0, char_offset=0,
        ...     kind=MappingKind.INITIAL, weight=10.0,
        ... )
        >>> scorer.positional_term([mapping])
        10.0

    Args:
        config: Engine configuration; supplies the effective weights via
            :attr:`~acronymkit.config.Config.weights` and controls whether a
            :class:`~acronymkit.models.ScoreBreakdown` is attached to
            candidates.
        lexicon: Object exposing ``contains(word: str) -> bool``, used for
            ``Lambda(A)``. Optional.
        ngram: Object exposing ``score(acronym: str) -> float`` and
            ``normalized_score(acronym: str) -> float``, used for ``Phi(A)``
            and the pronounceability index. Optional.
    """

    __slots__ = ("_config", "_lexicon", "_ngram", "_weights")

    def __init__(
        self,
        config: Config,
        lexicon: Optional[Lexicon] = None,
        ngram: Optional[CharNGramModel] = None,
    ) -> None:
        self._config = config
        self._lexicon = lexicon
        self._ngram = ngram
        self._weights = config.weights

    # -- collaborators -----------------------------------------------------
    @property
    def config(self) -> Config:
        """The configuration this scorer was built from."""
        return self._config

    @property
    def weights(self) -> ScoringWeights:
        """Effective coefficients resolved from :attr:`config`."""
        return self._weights

    @property
    def lexicon(self) -> Optional[Lexicon]:
        """The lexicon backing ``Lambda(A)``, or ``None``."""
        return self._lexicon

    @property
    def ngram(self) -> Optional[CharNGramModel]:
        """The character n-gram model backing ``Phi(A)``, or ``None``."""
        return self._ngram

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return (
            f"Scorer(strategy={self._config.scoring_strategy.value!r}, "
            f"lexicon={self._lexicon is not None}, ngram={self._ngram is not None})"
        )

    # -- individual terms --------------------------------------------------
    def positional_term(self, mappings: Sequence[LetterMapping]) -> float:
        """Return ``SUM_i omega(c_i, w_j(i))`` net of unmapped penalties.

        Args:
            mappings: The per-character alignments, typically produced by
                :func:`build_mappings`.

        Returns:
            The sum of every mapping weight, minus
            ``weights.unmapped_penalty`` for each ``UNMAPPED`` mapping. An
            empty sequence scores ``0.0``.
        """
        penalty = float(self._weights.unmapped_penalty)
        total = 0.0
        for mapping in mappings:
            total += float(mapping.weight)
            if mapping.kind == MappingKind.UNMAPPED:
                total -= penalty
        return total

    def phonotactic_term(self, acronym: str) -> float:
        """Return ``Phi(A)``: the mean character-bigram log-likelihood.

        The computation is delegated verbatim to the n-gram model, which owns
        the reference formula (including its documented convention for strings
        shorter than two characters).

        Args:
            acronym: The candidate acronym.

        Returns:
            ``ngram.score(acronym)``, or ``0.0`` when no model is configured.
        """
        if self._ngram is None:
            return 0.0
        return float(self._ngram.score(acronym))

    def lexical_term(self, acronym: str) -> float:
        """Return ``Lambda(A)``: ``1.0`` on a dictionary hit, else ``0.0``.

        The lookup is case-insensitive: the acronym is case-folded before it
        reaches the lexicon.

        Args:
            acronym: The candidate acronym.

        Returns:
            ``1.0`` when the lexicon knows the word; ``0.0`` otherwise,
            including when no lexicon is configured or the acronym is empty.
        """
        if self._lexicon is None or not acronym:
            return 0.0
        return _LEXICAL_HIT if self._lexicon.contains(acronym.casefold()) else 0.0

    def information_loss(self, tokens: Sequence[Token], covered: AbstractSet[int]) -> float:
        """Return ``Psi(T, A)``: the count of dropped critical tokens.

        Args:
            tokens: The full token sequence for the source phrase.
            covered: Indices (``Token.index``) that the acronym represents.

        Returns:
            The number of tokens with ``is_critical is True`` whose ``index``
            is absent from ``covered``, as a float.
        """
        dropped = 0
        for token in tokens:
            if token.is_critical and token.index not in covered:
                dropped += 1
        return float(dropped)

    # -- composite ---------------------------------------------------------
    def score(
        self,
        acronym: str,
        tokens: Sequence[Token],
        mappings: Sequence[LetterMapping],
        covered: AbstractSet[int],
    ) -> ScoreBreakdown:
        """Evaluate ``S(A, T)`` and return its full decomposition.

        ::

            total = alpha * positional
                  + beta  * phonotactic
                  + gamma * lexical
                  - delta * information_loss
                  - length_penalty * max(0, len(A) - preferred_length)

        Args:
            acronym: The candidate acronym, already cased as it will be
                returned.
            tokens: The full token sequence for the source phrase.
            mappings: Per-character alignments for ``acronym``.
            covered: Token indices the acronym represents.

        Returns:
            A :class:`~acronymkit.models.ScoreBreakdown` recording each term,
            the four coefficients in force, and the composite ``total``.
        """
        weights = self._weights
        positional = self.positional_term(mappings)
        phonotactic = self.phonotactic_term(acronym)
        lexical = self.lexical_term(acronym)
        loss = self.information_loss(tokens, covered)
        excess = max(0, len(acronym) - weights.preferred_length)
        total = (
            weights.alpha * positional
            + weights.beta * phonotactic
            + weights.gamma * lexical
            - weights.delta * loss
            - weights.length_penalty * excess
        )
        return ScoreBreakdown(
            positional=positional,
            phonotactic=phonotactic,
            lexical=lexical,
            information_loss=loss,
            alpha=weights.alpha,
            beta=weights.beta,
            gamma=weights.gamma,
            delta=weights.delta,
            total=total,
        )

    def build_candidate(
        self,
        acronym: str,
        tokens: Sequence[Token],
        mappings: Sequence[LetterMapping],
        covered: AbstractSet[int],
    ) -> AcronymCandidate:
        """Score ``acronym`` and package it as a complete candidate record.

        Every field of :class:`~acronymkit.models.AcronymCandidate` is
        populated. Index collections are sorted so the payload is stable
        regardless of the iteration order of ``covered``.

        Args:
            acronym: The candidate acronym, already cased as it will be
                returned.
            tokens: The full token sequence for the source phrase.
            mappings: Per-character alignments for ``acronym``.
            covered: Token indices the acronym represents.

        Returns:
            The scored candidate. ``breakdown`` is attached only when
            ``config.include_breakdown`` is set; ``pronounceability_score``
            falls back to ``0.5`` when no n-gram model is configured, and
            ``skipped_token_indices`` lists the eligible tokens the acronym
            left out.
        """
        breakdown = self.score(acronym, tokens, mappings, covered)
        pronounceability = (
            _NEUTRAL_PRONOUNCEABILITY
            if self._ngram is None
            else float(self._ngram.normalized_score(acronym))
        )
        skipped = sorted(
            token.index for token in tokens if token.is_eligible and token.index not in covered
        )
        return AcronymCandidate(
            acronym=acronym,
            score=breakdown.total,
            is_dictionary_word=breakdown.lexical >= _LEXICAL_HIT,
            pronounceability_score=pronounceability,
            raw_phonotactic_score=breakdown.phonotactic,
            mappings=list(mappings),
            covered_token_indices=sorted(covered),
            skipped_token_indices=skipped,
            breakdown=breakdown if self._config.include_breakdown else None,
        )
