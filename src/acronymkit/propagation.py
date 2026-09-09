"""Document-scoped propagation of a confirmed abbreviation definition (A2).

What this is for
----------------
:meth:`~acronymkit.extractor.AbbreviationExtractor.extract` answers where a
definition is *written*. It says nothing about the other places the document
writes the same short form, and on article body text that is most of them: on
PMC Open Access, the occurrences a document-scoped rule would license outside
every definition sentence are
``one_sense.pmc_oa.a2.high_precision.a2_new_coverage_multiple_of_current``
times the occurrences the sentence-scoped mechanism reaches -- **a multiple of
the new half over the old half, not of total coverage.**

This module ships that rule and nothing else. It is **opt-in**: no engine, no
config flag and no default path reaches it, and
:func:`~acronymkit.extractor.AbbreviationExtractor.extract` is byte-identical to
what it was before this module existed.

The rule, and it is the one that was measured
---------------------------------------------
*Commit to the first definition of a short form in document order; license every
whole-token occurrence of that short form at or after it.*

Every word of that is load-bearing and each was fixed before the cost was
measured, so changing any of them invalidates the bounds below:

``first ... in document order``
    not the highest-confidence definition and not the last one.
``whole-token``
    ``(?<![0-9A-Za-z]) ... (?![0-9A-Za-z])``. A bare substring search finds
    ``CT`` inside ``fact``; :func:`whole_token_occurrences` does not.
``at or after it``
    a document may use a short form before defining it, and this rule does not
    reach backwards.
``term-shaped short forms only``
    :func:`term_shaped`. Single letters and discourse markers are excluded, which
    is the *generous* reading -- licensing them would raise every error figure
    below.

What it costs, measured rather than assumed
-------------------------------------------
``bench/run_one_sense.py`` priced this rule on PMC Open Access before it was
built (``one_sense.pmc_oa.a2.*``, and see ``docs/EVALUATION.md``). One-sense-per-
discourse is an **assumption**, and its violation was bounded on both sides:
between ``wrong_floor_correctness_pct_of_licensed`` and
``wrong_ceiling_correctness_pct_of_licensed`` of licensed occurrences carry a
long form the document does not support there. The ceiling is not small, and the
comparator makes the trade worse rather than better: the sentence-scoped
mechanism this extends has an error rate of exactly **zero** on those
occurrences, because it declines to answer at all. A2 buys coverage and pays in
correctness. That is the whole trade and a caller has to want it.

The conformal gate, and the guarantee it is NOT
-----------------------------------------------
:func:`propagate` accepts a caller-built
:class:`~acronymkit.conformal.ConformalGate` and then propagates only where the
gate answers on the committed definition. What that buys is a **joint** bound
and not a selective one. **Read the next two paragraphs before relying on it,
because the natural reading is the wrong one and its wrongness has a measured
size.**

The gate's bound is on the *joint* rate of answering and being wrong -- over
**all** instances, including the ones it refuses. It is not a bound on the error
rate among the instances it answers. On ``conformal.sdu21.exchangeable``, at
``alpha = 0.05`` the joint rate came in at ``2.07`` % against its bound of
``5.00`` % while the selective error **among answers** was ``21.92`` %, which is
``4.38`` times ``alpha``. **That multiple is the maximum and it falls as
``alpha`` rises** -- ``4.38``, ``2.88``, ``1.85``, ``1.37`` and ``0.97`` across
``alpha`` of ``0.05``, ``0.10``, ``0.20``, ``0.30`` and ``0.50``, so at the
loosest setting the selective rate is finally *under* its nominal. Quoting
``4.38`` alone overstates the general case and understates the specific one:
**the overshoot is worst exactly where a governance caller would set the
threshold.** So ``gate=ConformalGate.calibrate(..., alpha=0.05)`` does **not**
mean one propagation in twenty is wrong. See :meth:`ConformalGate.guarantee`, which
returns both halves in one string, and ``docs/EVALUATION.md``. Bounding the
selective rate needs risk-controlled selective classification, which is not
implemented here; when it lands, this gate tightens and this paragraph is what
has to change.

**And there is a second gap on top of the first, which is this module's own.**
The joint bound is about *the definition*. Nothing it says transfers to the
occurrences the definition then licenses -- that transfer is one-sense-per-
discourse, whose violation is bounded above by the measured ceiling and is not
bounded by any conformal argument at all. A confident definition propagated into
a document that reuses the short form for something else is wrong at every
licensed site, and the gate cannot see it.

Import policy
-------------
Standard library, :mod:`acronymkit.conformal`, :mod:`acronymkit.enums`,
:mod:`acronymkit.exceptions` and :mod:`acronymkit.models`. Nothing here imports
:mod:`acronymkit.extractor`, so ``extractor -> propagation`` is available to a
later round and no cycle exists today.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from .conformal import ANSWERED, ConformalGate
from .enums import EngineTier
from .exceptions import ConfigurationError
from .models import AcronymPair, DisambiguationCandidate, DisambiguationResult, EngineMetadata

__all__ = [
    "JOINT_NOT_SELECTIVE",
    "NOT_TERM_SHAPED",
    "PROPAGATION_GAP",
    "SOURCE_DEFINITION",
    "SOURCE_PROPAGATED",
    "Occurrence",
    "PropagationResult",
    "document_result",
    "gate_disclosure",
    "propagate",
    "term_shaped",
    "whole_token_occurrences",
]

#: What a conformal gate on this rule does and does not bound, in one string that
#: cannot be split. Held as a constant for the reason
#: :data:`acronymkit.conformal.ASSUMPTION` is: the two halves of this are only
#: honest together, and a surface that quotes the first without the second is the
#: overclaim ``docs/DECISIONS.md`` D-104 measured at four times its nominal size.
JOINT_NOT_SELECTIVE = (
    "The gate bounds the JOINT rate of answering and being wrong, over all "
    "instances including the ones it refuses. It does not bound the error rate "
    "among the instances it answers: that is the joint rate divided by the "
    "answer rate, and on conformal.sdu21.exchangeable it was 21.92 % at "  # measured: conformal.sdu21.exchangeable
    "alpha = 0.05 -- 4.38 times alpha -- and 37.02 % at alpha = 0.20. That "  # measured: conformal.sdu21.exchangeable
    "multiple is a MAXIMUM: it falls monotonically as alpha rises and is under "
    "1 at the loosest alpha measured, so the overshoot is worst exactly where a "
    "governance caller would set the threshold. Bounding "
    "the selective rate needs risk-controlled selective classification, which "
    "is not implemented here; when it lands this gate tightens."
)

#: The second gap, which is this module's own and not conformal's. Nothing a gate
#: says about a definition transfers to the occurrences that definition licenses.
PROPAGATION_GAP = (
    "That bound is about the definition alone. Whether a licensed occurrence "
    "means what its definition meant is one-sense-per-discourse, which no "
    "conformal argument bounds at all; bench/run_one_sense.py bounds it between "
    "0.581 % and 9.68 % of licensed occurrences on PMC Open Access, and the "  # measured: one_sense.pmc_oa.a2.high_precision
    "ceiling is not small."
)

#: ``Occurrence.source`` for a site the extractor itself reported.
SOURCE_DEFINITION = "definition"

#: ``Occurrence.source`` for a site this module licensed.
SOURCE_PROPAGATED = "propagated"

#: Refusal reasons on :attr:`PropagationResult.refused`. Exhaustive. The five
#: ``gate_*`` codes are the four ``ConformalDecision`` refusals plus the one this
#: module adds: a gate that answers something other than the committed
#: definition is a disagreement, not an abstention, and is reported as one.
NOT_TERM_SHAPED = "not_term_shaped"
GATE_AMBIGUOUS = "gate_ambiguous"
GATE_NO_PLAUSIBLE_CANDIDATE = "gate_no_plausible_candidate"
GATE_NO_CANDIDATES = "gate_no_candidates"
GATE_UNCALIBRATED_GROUP = "gate_uncalibrated_group"
GATE_DISAGREED = "gate_disagreed_with_commitment"

#: Shortest and longest short form this rule will license, and the admission
#: rule's other two clauses. Held as constants because ``bench/run_one_sense.py``
#: measured the cost bounds under exactly these values; a caller who widens them
#: is outside every figure this module's docstring quotes.
TERM_MIN_LENGTH = 2
TERM_MAX_LENGTH = 15


def term_shaped(short_form: str) -> bool:
    """Is ``short_form`` in the population the measured bounds were taken over?

    Four clauses, all of them ``bench/run_one_sense.py``'s and none of them this
    module's invention: length between :data:`TERM_MIN_LENGTH` and
    :data:`TERM_MAX_LENGTH` inclusive, no whitespace, at least one letter, at
    least one upper-case character.

    **This is an exclusion and not a quality judgement.** Single-letter short
    forms and lower-case discourse markers are the keys an extractor collides on
    most often, and they are excluded here because they were excluded from the
    frame the error bounds were measured over -- so this module has no figure
    about them, rather than a good one.

    Args:
        short_form: The candidate short form.

    Returns:
        Whether the rule admits it.

    Example:
        >>> term_shaped("HIV"), term_shaped("i"), term_shaped("the")
        (True, False, False)
    """
    if not TERM_MIN_LENGTH <= len(short_form) <= TERM_MAX_LENGTH:
        return False
    if any(character.isspace() for character in short_form):
        return False
    if not any(character.isalpha() for character in short_form):
        return False
    return any(character.isupper() for character in short_form)


def whole_token_occurrences(text: str, needle: str) -> tuple[int, ...]:
    """Every start offset where ``needle`` stands as a whole token.

    A token boundary here is ``[0-9A-Za-z]`` on either side and nothing else, so
    ``CT`` is found in ``"the CT scan"`` and in ``"CT-guided"`` and is **not**
    found inside ``"fact"``. Hyphens and slashes are boundaries, which is the
    same convention ``bench/run_one_sense.py`` measured under.

    Args:
        text: The document.
        needle: The short form. Empty yields no offsets.

    Returns:
        Start offsets, leftmost first.

    Example:
        >>> whole_token_occurrences("A CT scan; the fact is CT-guided.", "CT")
        (2, 23)
    """
    if not needle:
        return ()
    pattern = re.compile(r"(?<![0-9A-Za-z])" + re.escape(needle) + r"(?![0-9A-Za-z])")
    return tuple(match.start() for match in pattern.finditer(text))


@dataclass(frozen=True)
class Occurrence:
    """One site in a document where a short form carries a long form.

    Attributes:
        short_form: The short form, verbatim from the document.
        long_form: The long form committed to it.
        span: Half-open character offsets of the short form in the document.
            ``text[span[0]:span[1]] == short_form`` always holds.
        source: :data:`SOURCE_DEFINITION` where the extractor reported the pair
            itself, :data:`SOURCE_PROPAGATED` where this module licensed it.
        licensed_by: Short-form span of the definition this site was committed
            to. Equal to :attr:`span` on a definition site.
        confidence: The extractor's confidence in the *definition*, carried
            unchanged. It is not a confidence about this site: nothing measured
            the probability that a licensed occurrence means what its definition
            meant, and a propagated site inherits the definition's number rather
            than earning one.
    """

    short_form: str
    long_form: str
    span: tuple[int, int]
    source: str
    licensed_by: tuple[int, int]
    confidence: float


@dataclass(frozen=True)
class PropagationResult:
    """What propagation licensed, and every short form it refused.

    Attributes:
        occurrences: Definition and propagated sites together, in document
            order by :attr:`Occurrence.span`.
        refused: ``(short form, reason)`` for every short form that carried a
            definition and licensed nothing beyond it. Reasons are the module
            constants; the list is here because a silent refusal and a document
            with no repeats are indistinguishable from the occurrences alone.
    """

    occurrences: tuple[Occurrence, ...] = ()
    refused: tuple[tuple[str, str], ...] = ()

    @property
    def propagated(self) -> tuple[Occurrence, ...]:
        """Only the sites this module licensed."""
        return tuple(o for o in self.occurrences if o.source == SOURCE_PROPAGATED)


def document_result(
    short_form: str, pairs: Sequence[AcronymPair], context: str = ""
) -> DisambiguationResult:
    """Build the choice a conformal gate would be asked about, from one document.

    The candidate set is the distinct long forms **this document** defines for
    ``short_form``, scored by the highest extractor confidence each was seen
    with, ordered ``(-score, expansion)`` the way the library orders every
    candidate list. It is offered so a caller has something to calibrate on and
    something to decide about that come from the same function.

    **It is not a dictionary lookup and must not be read as one.** A short form
    the document defines once produces a one-candidate result, which every
    grouping in :mod:`acronymkit.conformal` treats as arity ``1``; whether that
    group is calibrated at all is the caller's problem and the gate refuses it
    if it is not.

    Args:
        short_form: The short form to build the choice for.
        pairs: The document's extracted pairs. Pairs for other short forms are
            ignored.
        context: Text recorded on the result. Not read by any scoring.

    Returns:
        The result. ``primary_expansion`` is the **first definition in document
        order**, which is what A2 commits to, and may differ from
        ``candidates[0]``, which is the highest-scoring one.

    Example:
        >>> from acronymkit.models import AcronymPair
        >>> pairs = [
        ...     AcronymPair(short_form="BP", long_form="blood pressure", confidence=0.9),
        ...     AcronymPair(
        ...         short_form="BP", long_form="boiling point",
        ...         short_form_span=(40, 42), confidence=0.7,
        ...     ),
        ... ]
        >>> result = document_result("BP", pairs)
        >>> result.primary_expansion, [c.expansion for c in result.candidates]
        ('blood pressure', ['blood pressure', 'boiling point'])
    """
    mine = [pair for pair in pairs if pair.short_form == short_form]
    ordered = sorted(mine, key=lambda pair: pair.short_form_span[0])
    best: dict[str, float] = {}
    for pair in ordered:
        previous = best.get(pair.long_form)
        if previous is None or pair.confidence > previous:
            best[pair.long_form] = pair.confidence
    candidates = [
        DisambiguationCandidate(expansion=expansion, score=score, source="inline")
        for expansion, score in sorted(best.items(), key=lambda item: (-item[1], item[0]))
    ]
    return DisambiguationResult(
        acronym=short_form,
        context=context,
        primary_expansion=ordered[0].long_form if ordered else None,
        candidates=candidates,
        metadata=EngineMetadata(
            engine_tier=EngineTier.ZERO_DEPENDENCY,
            execution_time_ms=0.0,
            tokens_processed=0,
            candidates_evaluated=len(candidates),
        ),
    )


def gate_disclosure(gate: ConformalGate) -> str:
    """Everything a caller must read before trusting ``gate=``, in one string.

    :meth:`ConformalGate.guarantee` first -- it is the only surface carrying the
    exchangeability assumption -- then :data:`JOINT_NOT_SELECTIVE`, then
    :data:`PROPAGATION_GAP`. Concatenated here rather than left to a caller
    because each is a different reader's failure mode, and quoting one is how the
    other two get lost.

    Args:
        gate: The gate whose guarantee is being disclosed.

    Returns:
        The three parts, space-joined, in that order.

    Example:
        >>> from acronymkit.conformal import ConformalGate
        >>> from acronymkit.models import AcronymPair
        >>> pairs = [AcronymPair(short_form="AB", long_form="alpha beta")]
        >>> calibration = [(document_result("AB", pairs), "alpha beta")] * 20
        >>> disclosure = gate_disclosure(ConformalGate.calibrate(calibration, alpha=0.2))
        >>> "JOINT" in disclosure and "one-sense-per-discourse" in disclosure
        True
        >>> "exchangeab" in disclosure
        True
    """
    return f"{gate.guarantee()} {JOINT_NOT_SELECTIVE} {PROPAGATION_GAP}"


def _gate_refusal(reason: str) -> str:
    """Map a :class:`~acronymkit.conformal.ConformalDecision` reason onto ours."""
    return {
        "ambiguous": GATE_AMBIGUOUS,
        "no_plausible_candidate": GATE_NO_PLAUSIBLE_CANDIDATE,
        "no_candidates": GATE_NO_CANDIDATES,
        "uncalibrated_group": GATE_UNCALIBRATED_GROUP,
    }.get(reason, reason)


def propagate(
    text: str,
    pairs: Iterable[AcronymPair],
    *,
    gate: Optional[ConformalGate] = None,
) -> PropagationResult:
    """License a document's later occurrences of every short form it defines.

    The rule is the module docstring's, verbatim: commit to the first definition
    in document order, license every whole-token occurrence of that short form at
    or after it, term-shaped short forms only.

    **What a gate changes, and the sentence that would be wrong.** With ``gate``
    supplied, a short form propagates only where the gate answers on
    :func:`document_result` *and* its answer is the definition A2 committed to.
    That gates the **definition**. It bounds the joint rate of the gate answering
    and being wrong about that definition; it does not bound the share of the
    gate's answers that are wrong -- measured at up to ``4.38`` times ``alpha``
    on ``conformal.sdu21.exchangeable``, that being the multiple at the tightest
    ``alpha`` of five measured -- and it says nothing whatever about
    whether a licensed occurrence means what its definition meant, which is
    one-sense-per-discourse and is bounded only by ``one_sense.pmc_oa.a2.*``.
    Two unguaranteed steps compose here and neither is the other's warrant.

    Args:
        text: The document the pairs were extracted from. Offsets are read
            against it, so it must be the same string.
        pairs: Extracted definitions. Pairs whose short form is not
            :func:`term_shaped` are refused, and pairs whose recorded span does
            not hold their own short form in ``text`` are ignored outright --
            that identity is one :meth:`AbbreviationExtractor.extract
            <acronymkit.extractor.AbbreviationExtractor.extract>` documents, so
            a violation means the text and the pairs do not belong together.
        gate: Optional calibrated gate. See above for what it does and does not
            promise.

    Returns:
        The occurrences and the refusals.

    Raises:
        ConfigurationError: If ``gate`` is not a
            :class:`~acronymkit.conformal.ConformalGate`.

    Example:
        >>> from acronymkit.config import Config
        >>> from acronymkit.extractor import AbbreviationExtractor
        >>> text = (
        ...     "The World Health Organization (WHO) met. "
        ...     "WHO then met again, and WHO agreed."
        ... )
        >>> pairs = AbbreviationExtractor(Config()).extract(text)
        >>> result = propagate(text, pairs)
        >>> [(o.span, o.source) for o in result.occurrences]
        [((31, 34), 'definition'), ((41, 44), 'propagated'), ((65, 68), 'propagated')]

        Without a gate this is exactly the measured rule, so the measured cost is
        exactly the cost: on ``one_sense.pmc_oa.a2.high_precision`` between
        ``0.581`` % and ``9.68`` % of licensed occurrences carry a long form the
        document does not support there.
    """
    if gate is not None and not isinstance(gate, ConformalGate):
        raise ConfigurationError(
            f"gate must be a ConformalGate or None, not {type(gate).__name__}. "
            "Build one with ConformalGate.calibrate() over your own labelled data."
        )
    if not text:
        return PropagationResult()

    kept = [
        pair
        for pair in pairs
        if text[pair.short_form_span[0] : pair.short_form_span[1]] == pair.short_form
    ]
    groups: dict[str, list[AcronymPair]] = {}
    for pair in kept:
        groups.setdefault(pair.short_form, []).append(pair)

    occurrences: list[Occurrence] = []
    refused: list[tuple[str, str]] = []
    for short_form in sorted(groups):
        definitions = sorted(groups[short_form], key=lambda pair: pair.short_form_span[0])
        first = definitions[0]
        anchor = first.short_form_span
        if not term_shaped(short_form):
            refused.append((short_form, NOT_TERM_SHAPED))
            occurrences.extend(_definition_sites(definitions))
            continue
        if gate is not None:
            decision = gate.decide(document_result(short_form, definitions, text))
            if decision.reason != ANSWERED:
                refused.append((short_form, _gate_refusal(decision.reason)))
                occurrences.extend(_definition_sites(definitions))
                continue
            if decision.expansion != first.long_form:
                refused.append((short_form, GATE_DISAGREED))
                occurrences.extend(_definition_sites(definitions))
                continue
        defined_at = {pair.short_form_span[0] for pair in definitions}
        for start in whole_token_occurrences(text, short_form):
            if start < anchor[0]:
                continue
            if start in defined_at:
                continue
            occurrences.append(
                Occurrence(
                    short_form=short_form,
                    long_form=first.long_form,
                    span=(start, start + len(short_form)),
                    source=SOURCE_PROPAGATED,
                    licensed_by=anchor,
                    confidence=first.confidence,
                )
            )
        occurrences.extend(_definition_sites(definitions))

    occurrences.sort(key=lambda occurrence: (occurrence.span, occurrence.short_form))
    return PropagationResult(tuple(occurrences), tuple(refused))


def _definition_sites(definitions: Sequence[AcronymPair]) -> list[Occurrence]:
    """The extractor's own sites, unchanged and always emitted.

    A refusal withholds propagation and never withholds a definition: the
    definition was found by a mechanism this module does not govern, and dropping
    it would make ``propagate`` lose information ``extract`` already had.
    """
    return [
        Occurrence(
            short_form=pair.short_form,
            long_form=pair.long_form,
            span=pair.short_form_span,
            source=SOURCE_DEFINITION,
            licensed_by=pair.short_form_span,
            confidence=pair.confidence,
        )
        for pair in definitions
    ]
