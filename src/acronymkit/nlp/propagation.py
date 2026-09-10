"""Document-scoped propagation of a confirmed abbreviation definition (A2).

What this is for
----------------
:meth:`~acronymkit.nlp.extractor.AbbreviationExtractor.extract` answers where a
definition is *written*. It says nothing about the other places the document
writes the same short form, and on article body text that is most of them: on
PMC Open Access, the occurrences a document-scoped rule would license outside
every definition sentence are
``one_sense.pmc_oa.a2.high_precision.a2_new_coverage_multiple_of_current``
times the occurrences the sentence-scoped mechanism reaches -- **a multiple of
the new half over the old half, not of total coverage.**

This module ships that rule and nothing else. It is **opt-in**: no engine, no
config flag and no default path reaches it, and
:func:`~acronymkit.nlp.extractor.AbbreviationExtractor.extract` is byte-identical to
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

The two gates, and which quantity each one bounds
-------------------------------------------------
:func:`propagate` accepts two caller-built gates and neither is on by default.
``gate=`` is a :class:`~acronymkit.conformal.ConformalGate` and buys a **joint**
bound. ``selective=`` is a
:class:`~acronymkit.core.selective.SelectiveRiskGate` and buys a bound on the
**answers**, which is the quantity the joint bound was being misread as. They
are independent, they may be supplied together, and the sections below say what
each does and does not close. **Read them before relying on either, because for
``gate=`` the natural reading is the wrong one and its wrongness has a measured
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
returns both halves in one string, and ``docs/EVALUATION.md``.

**Bounding the selective rate needs risk-controlled selective classification,
and this paragraph is the one that said "when it lands, this paragraph is what
has to change". It landed, and it is a second bound rather than a repair of the
joint one.** ``selective=`` takes a
:class:`~acronymkit.core.selective.SelectiveRiskGate`, calibrated by
Learn-Then-Test over the caller's own labelled occurrences, and a short form
then propagates only where that gate admits :func:`selective_score` of the
committed definition in the
:data:`~acronymkit.core.selective.MODE_PROPAGATED` stratum. What it carries is
``P(wrong | answered) <= alpha`` with probability at least ``1 - delta`` over the
calibration draw, **under exchangeability between the calibration documents and
the deployment documents, and under independence of the accepted calibration
units** -- Learn-Then-Test changes which functional is bounded and repeals
neither condition. On ``selective.modes.ltt`` the held-out selective error came
in under nominal at every alpha where anything certified, at an answer rate that
is reported beside every bound because a gate that answers nothing satisfies
every selective bound there is.

It does **not** tighten ``gate=``. The two are separate parameters because they
are separate guarantees, and folding one into the other would put a caller who
passed only ``gate=`` under a bound nobody computed for them.

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
:mod:`acronymkit.nlp.extractor`, so ``extractor -> propagation`` is available to a
later round and no cycle exists today.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from ..core.conformal import ANSWERED, ConformalGate
from ..core.exceptions import ConfigurationError
from ..core.selective import MODE_PROPAGATED, SelectiveRiskGate
from ..core.spans import Span
from ..enums import EngineTier
from ..models import AcronymPair, DisambiguationCandidate, DisambiguationResult, EngineMetadata

__all__ = [
    "JOINT_NOT_SELECTIVE",
    "NOT_TERM_SHAPED",
    "PROPAGATION_GAP",
    "SELECTIVE_IS_NOT_ONE_SENSE",
    "SOURCE_DEFINITION",
    "SOURCE_PROPAGATED",
    "Occurrence",
    "PropagationResult",
    "document_result",
    "gate_disclosure",
    "propagate",
    "selective_score",
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
    "governance caller would set the threshold. Bounding the selective rate "
    "needs risk-controlled selective classification, and that is what the "
    "separate selective= parameter supplies -- gate= alone still bounds only "
    "the joint rate and this sentence is about gate=."
)

#: What a SELECTIVE gate does and does not close. Held as a constant for the same
#: reason as its two neighbours: the sentence that follows the good news is the
#: one a reader skips, so it is not allowed to be a separate string.
#:
#: **Learn-Then-Test bounds the definition decision and not the transfer.** It
#: replaces the joint rate with the larger rate among answers, the one D-104
#: measured at 4.38 times alpha and the one no conformal argument ever bounded.
#: It does not touch one-sense-per-discourse, which is a different unguaranteed
#: step in the same composition, and a caller who reads a selective certificate
#: as covering both has made the second half of the same mistake with the first
#: half fixed.
SELECTIVE_IS_NOT_ONE_SENSE = (
    "A selective certificate bounds the share of the gate's ANSWERS about the "
    "committed definition that are wrong, with probability at least 1 - delta "
    "over the calibration draw. It closes the joint-versus-selective gap and it "
    "closes nothing else: whether a licensed occurrence means what its "
    "definition meant is one-sense-per-discourse, which no risk-control argument "
    "bounds, and the two unguaranteed steps in this module were never the same "
    "step. Learn-Then-Test also does not repeal exchangeability."
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

#: Refusals a :class:`~acronymkit.core.selective.SelectiveRiskGate` adds. Three,
#: matching its three refusal reasons one for one, prefixed so a reader of a
#: refusal list can tell which of the two gates declined without consulting the
#: call site.
SELECTIVE_UNCALIBRATED = "selective_uncalibrated_stratum"
SELECTIVE_UNCERTIFIED = "selective_uncertified_stratum"
SELECTIVE_ABOVE_THRESHOLD = "selective_above_threshold"

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


def gate_disclosure(
    gate: Optional[ConformalGate] = None,
    selective: Optional[SelectiveRiskGate] = None,
) -> str:
    """Everything a caller must read before trusting either gate, in one string.

    Each gate's own ``guarantee()`` first -- those are the only surfaces carrying
    the exchangeability assumption -- then the standing caveat that belongs to
    it, which for ``gate=`` is that its bound is the joint one, then
    :data:`PROPAGATION_GAP`, which belongs to neither gate and to this module.
    Concatenated here rather than left to a caller because each part is a
    different reader's failure mode, and quoting one is how the rest get lost.

    ``PROPAGATION_GAP`` comes last and is emitted **whichever** gate was passed,
    because it is the gap neither of them closes: risk control replaces a joint
    bound with a selective one and leaves one-sense-per-discourse untouched.

    Args:
        gate: The conformal gate being disclosed, if any.
        selective: The selective-risk gate being disclosed, if any.

    Returns:
        The parts, space-joined, conformal first.

    Raises:
        ConfigurationError: If neither gate is supplied. A disclosure about no
            gate would be a paragraph of caveats attached to nothing, which
            reads as reassurance and carries none.

    Example:
        >>> from acronymkit.conformal import ConformalGate
        >>> from acronymkit.core.selective import Observation, SelectiveRiskGate
        >>> from acronymkit.models import AcronymPair
        >>> pairs = [AcronymPair(short_form="AB", long_form="alpha beta")]
        >>> calibration = [(document_result("AB", pairs), "alpha beta")] * 20
        >>> disclosure = gate_disclosure(ConformalGate.calibrate(calibration, alpha=0.2))
        >>> "JOINT" in disclosure and "one-sense-per-discourse" in disclosure
        True
        >>> "exchangeab" in disclosure
        True

        The selective disclosure carries the exchangeability assumption too --
        Learn-Then-Test does not repeal it -- and still carries the propagation
        gap, because that one is nobody's to close but this module's.

        >>> units = [Observation("propagated", 0.0, 0)] * 60
        >>> risk = SelectiveRiskGate.calibrate(units, alpha=0.2, delta=0.05)
        >>> selective_disclosure = gate_disclosure(selective=risk)
        >>> "exchangeab" in selective_disclosure
        True
        >>> "one-sense-per-discourse" in selective_disclosure
        True
    """
    if gate is None and selective is None:
        raise ConfigurationError(
            "gate_disclosure() needs at least one gate; a disclosure about no gate is a "
            "paragraph of caveats attached to nothing, which reads as reassurance."
        )
    parts: list[str] = []
    if gate is not None:
        parts.append(gate.guarantee())
        parts.append(JOINT_NOT_SELECTIVE)
    if selective is not None:
        parts.append(selective.guarantee())
        parts.append(SELECTIVE_IS_NOT_ONE_SENSE)
    parts.append(PROPAGATION_GAP)
    return " ".join(parts)


def _gate_refusal(reason: str) -> str:
    """Map a :class:`~acronymkit.conformal.ConformalDecision` reason onto ours."""
    return {
        "ambiguous": GATE_AMBIGUOUS,
        "no_plausible_candidate": GATE_NO_PLAUSIBLE_CANDIDATE,
        "no_candidates": GATE_NO_CANDIDATES,
        "uncalibrated_group": GATE_UNCALIBRATED_GROUP,
    }.get(reason, reason)


def selective_score(definition: AcronymPair) -> float:
    """The selection score a selective gate reads off the committed definition.

    ``1 - confidence``, so that **lower is more confident** -- the direction
    :func:`~acronymkit.core.conformal.nonconformity` uses and the direction
    :class:`~acronymkit.core.selective.SelectiveRiskGate` compares in. It is one
    public function with no arguments beyond the pair for the reason
    ``nonconformity`` is: risk control is valid only when the same score is
    applied to calibration and to deployment, and two spellings of "the score"
    is how that stops being true.

    Args:
        definition: The definition A2 committed to -- the *first* in document
            order, which is what ``propagate`` licenses from.

    Returns:
        The score, in ``[0, 1]`` for any confidence in ``[0, 1]``.

    Example:
        >>> from acronymkit.models import AcronymPair
        >>> selective_score(AcronymPair(short_form="BP", long_form="blood pressure",
        ...                             confidence=0.8))
        0.19999999999999996
    """
    return 1.0 - definition.confidence


def _selective_refusal(reason: str) -> str:
    """Map a :class:`~acronymkit.core.selective.SelectiveRiskGate` reason onto ours."""
    return {
        "uncalibrated_stratum": SELECTIVE_UNCALIBRATED,
        "uncertified_stratum": SELECTIVE_UNCERTIFIED,
        "above_threshold": SELECTIVE_ABOVE_THRESHOLD,
    }.get(reason, reason)


def propagate(
    text: str,
    pairs: Iterable[AcronymPair],
    *,
    gate: Optional[ConformalGate] = None,
    selective: Optional[SelectiveRiskGate] = None,
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

    **What ``selective`` changes, which is the first of those two and not the
    second.** With ``selective`` supplied, a short form propagates only where the
    gate admits :func:`selective_score` of the committed definition in the
    :data:`~acronymkit.core.selective.MODE_PROPAGATED` stratum. That carries a
    bound on the share of *answers* that are wrong rather than on the joint rate,
    which is the ``4.38``-times-``alpha`` gap closed rather than restated -- and
    it holds with probability at least ``1 - delta`` over the calibration draw,
    under exchangeability between the calibration documents and the deployment
    documents. It leaves one-sense-per-discourse exactly where it was. See
    :data:`SELECTIVE_IS_NOT_ONE_SENSE`, which
    :func:`gate_disclosure` returns and which says so in one string.

    The two are independent and may be supplied together, in which case both must
    admit. Neither is on by default and neither is constructed here.

    Args:
        text: The document the pairs were extracted from. Offsets are read
            against it, so it must be the same string.
        pairs: Extracted definitions. Pairs whose short form is not
            :func:`term_shaped` are refused, and pairs whose recorded span does
            not hold their own short form in ``text`` are ignored outright --
            that identity is one :meth:`AbbreviationExtractor.extract
            <acronymkit.nlp.extractor.AbbreviationExtractor.extract>` documents, so
            a violation means the text and the pairs do not belong together.
        gate: Optional calibrated conformal gate. See above for what it does and
            does not promise.
        selective: Optional calibrated
            :class:`~acronymkit.core.selective.SelectiveRiskGate`. Refusals are
            reported under :data:`SELECTIVE_UNCALIBRATED`,
            :data:`SELECTIVE_UNCERTIFIED` and :data:`SELECTIVE_ABOVE_THRESHOLD`.
            An uncertified stratum refuses **everything**, which is the correct
            behaviour and the expensive one: the bound was never computed for it.

    Returns:
        The occurrences and the refusals.

    Raises:
        ConfigurationError: If ``gate`` is not a
            :class:`~acronymkit.conformal.ConformalGate`, or if ``selective`` is
            not a :class:`~acronymkit.core.selective.SelectiveRiskGate`.

    Example:
        >>> from acronymkit.config import Config
        >>> from acronymkit.nlp.extractor import AbbreviationExtractor
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
    if selective is not None and not isinstance(selective, SelectiveRiskGate):
        raise ConfigurationError(
            f"selective must be a SelectiveRiskGate or None, not {type(selective).__name__}. "
            "Build one with SelectiveRiskGate.calibrate() over your own labelled data."
        )
    if not text:
        return PropagationResult()

    kept = [
        pair for pair in pairs if Span.of(pair.short_form_span).text_of(text) == pair.short_form
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
        if selective is not None:
            declined = selective.refusal(MODE_PROPAGATED, selective_score(first))
            if declined:
                refused.append((short_form, _selective_refusal(declined)))
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
                    span=Span(start, start + len(short_form)).as_tuple(),
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
