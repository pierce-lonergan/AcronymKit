"""Calibrated refusal for disambiguation: split conformal prediction.

What this is for
----------------
:class:`~acronymkit.disambiguation.LexicalDisambiguator` already reports a
``margin`` and will refuse below one the caller names. That refusal has no
guarantee attached to it: a margin is a difference of two unnormalised blends,
it is not a probability, and ``docs/EVALUATION.md`` publishes the whole
coverage/accuracy curve precisely because *no threshold this library can defend
is the caller's*.

This module changes what the caller has to supply. Instead of a threshold they
supply a target error rate ``alpha`` and a **calibration set drawn from their own
data**, and a split-conformal pass converts the pair into a threshold with a
distribution-free guarantee -- distribution-free, and *not* assumption-free: it
assumes the calibration data and the deployment data are exchangeable, which is
stated in full below and repeated everywhere the guarantee is. No model is
fitted, no data ships with the library, no dependency is added, and nothing here
is on by default: a :class:`ConformalGate` exists only when a caller builds
one.

The guarantee, and the assumption it rests on
---------------------------------------------
Stated once here and re-stated by :meth:`ConformalGate.guarantee` at runtime,
because the two halves must never be quoted apart:

    Marginally over the joint draw of the calibration set and one new instance,
    the prediction set contains the true expansion with probability at least
    ``1 - alpha``. This holds **only if** the calibration instances and the
    instances the gate is later asked about are exchangeable -- drawn from the
    same distribution, in no informative order. An out-of-domain caller violates
    exactly that, and the guarantee then says nothing at all.

Three further limits, all of which this project has measured rather than
asserted (run ids ``conformal.sdu21.*`` in ``bench/results.json``):

**It is a guarantee about the SET, not about the answer.** The library answers
only when the prediction set is a singleton. That inherits
``P(answered and wrong) <= alpha`` -- a *joint* rate over all instances. The
error rate **among answered instances** is that divided by the answer rate, so
it is larger, and on the measured corpus it is several times ``alpha``. A
sentence promising "at most ``alpha`` of the answers are wrong" is an overclaim
and this module does not make it.

**It is marginal, not conditional.** Coverage averages over instances. Split by
candidate-set size it can be far from nominal in either direction, which is what
:func:`arity_group` and the ``group_by`` argument exist for: Mondrian
(group-conditional) calibration gives the guarantee separately inside each group
at the price of needing enough calibration instances in each.

**A finite calibration set has a floor.** ``alpha`` below ``1 / (n + 1)`` is
unreachable no matter what the scores look like, so :meth:`ConformalGate.calibrate`
refuses rather than silently returning a gate that abstains on everything.

Determinism
-----------
No randomness and no clock. Calibration sorts the nonconformity scores and takes
an order statistic; every score is rounded to
:data:`NONCONFORMITY_PRECISION` places so the same inputs give the same
threshold on every platform.

Import policy
-------------
This module imports :mod:`acronymkit.models` and :mod:`acronymkit.exceptions`
and nothing else from the package, so
``disambiguation -> conformal -> {models, exceptions}`` stays acyclic and
:mod:`acronymkit.disambiguation` may import it at module level.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Optional, Sequence

from .exceptions import ConfigurationError
from .models import DisambiguationResult

__all__ = [
    "ASSUMPTION",
    "ConformalDecision",
    "ConformalGate",
    "GroupCalibration",
    "arity_group",
    "group_counts",
    "nonconformity",
    "smallest_calibration_size",
]


#: Decimal places every nonconformity score is rounded to. Two candidates whose
#: normalised confidences differ below this are treated as tied, which makes
#: prediction sets reproducible across platforms and makes coverage
#: *conservative* (a tie admits both candidates) rather than optimistic.
NONCONFORMITY_PRECISION = 9

#: The exchangeability assumption, in one sentence. Held as a constant rather
#: than repeated in prose so that no surface can state the guarantee without it:
#: :meth:`ConformalGate.guarantee` concatenates the two, and
#: ``tests/test_conformal.py`` asserts that every guarantee-bearing paragraph in
#: this module, in ``docs/EVALUATION.md`` and in every string this class returns
#: names it.
ASSUMPTION = (
    "This holds only under exchangeability between the calibration instances and "
    "the instances the gate is asked about; an out-of-domain caller violates that "
    "and is given no guarantee at all."
)

#: Reason codes on :attr:`ConformalDecision.reason`. Exhaustive.
ANSWERED = "answered"
AMBIGUOUS = "ambiguous"
NO_PLAUSIBLE_CANDIDATE = "no_plausible_candidate"
NO_CANDIDATES = "no_candidates"
UNCALIBRATED_GROUP = "uncalibrated_group"


def smallest_calibration_size(alpha: float) -> int:
    """Smallest calibration set for which ``alpha`` is reachable at all.

    Split conformal takes the ``ceil((n + 1) * (1 - alpha))``-th smallest
    calibration score as its threshold. When that rank exceeds ``n`` there is no
    such order statistic and the only valid threshold is "admit everything",
    which is a gate that can never answer. The smallest ``n`` avoiding that is
    ``ceil(1 / alpha) - 1``.

    Args:
        alpha: Target error rate, in ``(0, 1)``.

    Returns:
        The minimum usable calibration count.

    Example:
        >>> smallest_calibration_size(0.10)
        9
        >>> smallest_calibration_size(0.01)
        99
    """
    return math.ceil(1.0 / alpha) - 1


def nonconformity(result: DisambiguationResult) -> tuple[tuple[str, float], ...]:
    """Score every candidate of ``result``; lower is more conforming.

    The score is ``1 - p`` where ``p`` is the candidate's share of the total
    candidate score. Normalising is what makes a two-way and a fifteen-way
    result comparable at all; it introduces **no fitted parameter** -- there is
    no temperature, no calibration curve and nothing read off a tuning split,
    which is the whole reason a softmax was not used.

    Conformal validity does not require this to be a probability. It requires
    only that the same function is applied to calibration and to deployment,
    which is why it is one public function with no arguments beyond the result.

    Args:
        result: A disambiguation result. Candidates are read in the order the
            library emitted them, which is already ``(-score, expansion)``.

    Returns:
        ``(expansion, score)`` pairs, in the result's candidate order. Empty
        when the result has no candidates.

    Example:
        >>> from acronymkit.config import Config
        >>> from acronymkit.disambiguation import ExpansionDictionary, LexicalDisambiguator
        >>> index = ExpansionDictionary({"BP": ["blood pressure", "boiling point"]})
        >>> engine = LexicalDisambiguator(Config(), index)
        >>> scored = nonconformity(engine.disambiguate("BP", "The reading was taken twice."))
        >>> len(scored), scored[0][0]
        (2, 'boiling point')
    """
    candidates = result.candidates
    if not candidates:
        return ()
    total = math.fsum(candidate.score for candidate in candidates)
    if total <= 0.0:
        share = 1.0 / len(candidates)
        return tuple(
            (candidate.expansion, round(1.0 - share, NONCONFORMITY_PRECISION))
            for candidate in candidates
        )
    return tuple(
        (candidate.expansion, round(1.0 - candidate.score / total, NONCONFORMITY_PRECISION))
        for candidate in candidates
    )


def _true_label_score(result: DisambiguationResult, expansion: str) -> float:
    """Nonconformity of the *gold* expansion, or ``inf`` when it was never proposed.

    ``inf`` is the correct value and not a sentinel: a label the candidate set
    does not contain can never be in a prediction set drawn from that candidate
    set, so no finite threshold covers it. Using ``1.0`` instead would let an
    uncoverable instance raise the threshold as if it were merely a hard one.

    Args:
        result: The result the gold belongs to.
        expansion: The gold expansion, compared verbatim.

    Returns:
        The gold's nonconformity, or ``math.inf``.
    """
    for candidate_expansion, score in nonconformity(result):
        if candidate_expansion == expansion:
            return score
    return math.inf


def arity_group(result: DisambiguationResult) -> str:
    """Group a result by candidate-set size, for Mondrian calibration.

    A convenience for the commonest grouping, offered because
    :attr:`~acronymkit.models.DisambiguationResult.margin`'s documented failure
    is that it does not mean the same thing on a two-way choice as on a
    fifteen-way one. The buckets match the ones
    ``disambiguation.sdu21.abstention_curve`` is decomposed by, so the two
    tables can be read against each other.

    **The buckets are a choice, not a measurement.** Any callable of the same
    shape may be passed to :meth:`ConformalGate.calibrate` instead; a caller
    whose data is grouped by document, by source system or by nothing at all
    should say so rather than inherit these.

    Args:
        result: The result to bucket.

    Returns:
        ``"0"``, ``"1"`` ... ``"5"``, ``"6-9"`` or ``"10+"``.

    Example:
        >>> from acronymkit.config import Config
        >>> from acronymkit.disambiguation import ExpansionDictionary, LexicalDisambiguator
        >>> index = ExpansionDictionary({"BP": ["blood pressure", "boiling point"]})
        >>> engine = LexicalDisambiguator(Config(), index)
        >>> arity_group(engine.disambiguate("BP", "The reading was taken twice."))
        '2'
    """
    size = len(result.candidates)
    if size <= 5:
        return str(size)
    if size <= 9:
        return "6-9"
    return "10+"


def _marginal_group(result: DisambiguationResult) -> str:
    """Grouping used when the caller asks for no grouping: one group, always."""
    del result
    return ""


@dataclass(frozen=True)
class GroupCalibration:
    """The calibration of one group: what was seen, and what threshold it bought.

    Attributes:
        key: The group key, ``""`` for an ungrouped (marginal) calibration.
        count: Calibration instances in this group.
        threshold: The order statistic. A candidate is admitted to the
            prediction set when its nonconformity is at most this.
        rank: Which order statistic, one-based, so the arithmetic is auditable
            without re-deriving it.
        uncovered: Calibration instances whose gold expansion was not among the
            candidates at all. They are counted here because they cap what any
            threshold can achieve, and because a caller whose calibration set is
            full of them should know before they read a coverage figure.
    """

    key: str
    count: int
    threshold: float
    rank: int
    uncovered: int


@dataclass(frozen=True)
class ConformalDecision:
    """What the gate decided about one result, and why.

    Attributes:
        expansion: The answer, or ``None`` when the gate refused.
        prediction_set: Every candidate the calibration admits, in the result's
            own candidate order. This is the object the guarantee is about.
        abstained: ``True`` when ``expansion`` is ``None``.
        reason: One of ``"answered"``, ``"ambiguous"``,
            ``"no_plausible_candidate"``, ``"no_candidates"`` or
            ``"uncalibrated_group"``.
        group: The group key the result fell in.
        threshold: The threshold applied, or ``None`` for an uncalibrated group.
    """

    expansion: Optional[str]
    prediction_set: tuple[str, ...]
    abstained: bool
    reason: str
    group: str
    threshold: Optional[float]


class ConformalGate:
    """A calibrated refusal policy, built from the caller's own data.

    Construct one with :meth:`calibrate`; the initialiser takes an already-computed
    set of thresholds and exists so that a gate can be round-tripped without
    re-running a corpus.

    Instances are immutable and hold no per-call state.

    Example:
        Three labelled instances are not a calibration set -- ``alpha = 0.5``
        needs one instance and is used here only to keep the example short.

        >>> from acronymkit.config import Config
        >>> from acronymkit.disambiguation import ExpansionDictionary, LexicalDisambiguator
        >>> index = ExpansionDictionary({"BP": ["blood pressure", "boiling point"]})
        >>> engine = LexicalDisambiguator(Config(), index)
        >>> labelled = [
        ...     (engine.disambiguate("BP", "Blood pressure was elevated."), "blood pressure"),
        ...     (engine.disambiguate("BP", "The boiling point of water."), "boiling point"),
        ... ]
        >>> gate = ConformalGate.calibrate(labelled, alpha=0.5)
        >>> gate.alpha, gate.calibration_size
        (0.5, 2)
        >>> "exchangeab" in gate.guarantee()
        True
    """

    __slots__ = ("_alpha", "_group_by", "_grouped", "_groups")

    def __init__(
        self,
        *,
        alpha: float,
        groups: Sequence[GroupCalibration],
        group_by: Optional[Callable[[DisambiguationResult], str]] = None,
    ) -> None:
        """Build a gate from thresholds that have already been computed.

        Args:
            alpha: The target error rate the thresholds were computed for.
                Recorded, and used for nothing else -- the thresholds are the
                policy.
            groups: One :class:`GroupCalibration` per group. Marginal gates carry
                exactly one, keyed ``""``.
            group_by: The grouping the thresholds were computed under, or
                ``None`` for marginal. It must be the same callable used at
                calibration time; a different one silently re-points every
                threshold, which is why :meth:`calibrate` is the supported entry
                point.

        Raises:
            ConfigurationError: If ``groups`` is empty, if two groups share a
                key, if a marginal gate does not carry exactly one group keyed
                ``""``, or if a grouped gate uses ``""`` -- that key is reserved
                so that "marginal" and "one group that happens to be unnamed"
                cannot be confused by anything reading the thresholds back.
        """
        if not groups:
            raise ConfigurationError("a ConformalGate needs at least one calibrated group")
        keys = [group.key for group in groups]
        if len(set(keys)) != len(keys):
            raise ConfigurationError(f"duplicate group key(s) in {keys!r}")
        grouped = group_by is not None
        if not grouped and keys != [""]:
            raise ConfigurationError(
                f"a marginal gate carries exactly one group keyed '', got keys {keys!r}"
            )
        if grouped and "" in keys:
            raise ConfigurationError(
                "'' is reserved for marginal calibration; a group_by must return a non-empty key"
            )
        self._alpha = float(alpha)
        self._groups = {group.key: group for group in groups}
        self._group_by = group_by if group_by is not None else _marginal_group
        self._grouped = grouped

    @classmethod
    def calibrate(
        cls,
        labelled: Iterable[tuple[DisambiguationResult, str]],
        *,
        alpha: float,
        group_by: Optional[Callable[[DisambiguationResult], str]] = None,
    ) -> ConformalGate:
        """Fit a gate to a calibration set. One pass, no model, no randomness.

        Args:
            labelled: ``(result, gold_expansion)`` pairs from the caller's own
                data. The gold is compared verbatim to the candidate's
                ``expansion``, matching the convention the shared task's scorer
                uses; a gold that no candidate carries is scored ``inf`` and
                counted in :attr:`GroupCalibration.uncovered`.
            alpha: Target error rate in ``(0, 1)``. Read the class docstring
                before reading this as "the fraction of answers that will be
                wrong": it is a bound on the prediction set missing the truth,
                which is a different and smaller quantity.
            group_by: ``None`` for a marginal calibration -- one threshold, one
                guarantee averaged over everything. A callable for a Mondrian
                (group-conditional) calibration: each group gets its own
                threshold from its own instances, and the guarantee then holds
                inside each group. :func:`arity_group` is the obvious choice and
                is not the default, because the default must not choose a
                grouping on the caller's behalf.

        Returns:
            The fitted gate.

        Raises:
            ConfigurationError: If ``alpha`` is not a real number in ``(0, 1)``,
                if the calibration set is empty, or if any group holds fewer than
                :func:`smallest_calibration_size` instances. The last is a
                refusal and not a warning: below that size no order statistic
                exists, and the gate that would be returned abstains on
                everything while appearing to carry a guarantee.
        """
        numeric = _validated_alpha(alpha)
        buckets: dict[str, list[float]] = {}
        key_of = group_by if group_by is not None else _marginal_group
        for result, expansion in labelled:
            buckets.setdefault(key_of(result), []).append(_true_label_score(result, expansion))
        if not buckets:
            raise ConfigurationError(
                "the calibration set is empty; split conformal has nothing to take a quantile of"
            )
        minimum = smallest_calibration_size(numeric)
        undersized = sorted(key for key, scores in buckets.items() if len(scores) < minimum)
        if undersized:
            shown = ", ".join(f"{key or '<marginal>'}={len(buckets[key])}" for key in undersized)
            raise ConfigurationError(
                f"alpha={numeric!r} needs at least {minimum} calibration instance(s) per group "
                f"and these are short: {shown}. Raise alpha, coarsen group_by, or calibrate on "
                "more data -- a threshold taken from fewer carries no guarantee."
            )
        groups = []
        for key in sorted(buckets):
            scores = sorted(buckets[key])
            count = len(scores)
            rank = math.ceil((count + 1) * (1.0 - numeric))
            groups.append(
                GroupCalibration(
                    key=key,
                    count=count,
                    threshold=scores[rank - 1],
                    rank=rank,
                    uncovered=sum(1 for score in scores if math.isinf(score)),
                )
            )
        return cls(alpha=numeric, groups=groups, group_by=group_by)

    # -- properties --------------------------------------------------------
    @property
    def alpha(self) -> float:
        """The target error rate this gate was calibrated for."""
        return self._alpha

    @property
    def is_grouped(self) -> bool:
        """Whether this is a Mondrian (group-conditional) calibration."""
        return self._grouped

    @property
    def groups(self) -> tuple[GroupCalibration, ...]:
        """Every calibrated group, ordered by key."""
        return tuple(self._groups[key] for key in sorted(self._groups))

    @property
    def calibration_size(self) -> int:
        """Total calibration instances across all groups."""
        return sum(group.count for group in self._groups.values())

    # -- public API --------------------------------------------------------
    def guarantee(self) -> str:
        """The guarantee and its assumption, in one string that cannot be split.

        Returns:
            A sentence naming ``alpha``, what is bounded, what is *not* bounded,
            and :data:`ASSUMPTION`. The assumption is concatenated here rather
            than left to the caller because a guarantee quoted without it is the
            most expensive overclaim this subsystem can make.

        Example:
            >>> from acronymkit.config import Config
            >>> from acronymkit.disambiguation import ExpansionDictionary, LexicalDisambiguator
            >>> index = ExpansionDictionary({"BP": ["blood pressure", "boiling point"]})
            >>> engine = LexicalDisambiguator(Config(), index)
            >>> pairs = [
            ...     (engine.disambiguate("BP", "Blood pressure was elevated."), "blood pressure"),
            ...     (engine.disambiguate("BP", "The boiling point of water."), "boiling point"),
            ... ]
            >>> ConformalGate.calibrate(pairs, alpha=0.5).guarantee().startswith("Marginally")
            True
        """
        # ASSUMPTION is concatenated below and is never optional: exchangeability
        # between calibration and deployment is the condition the whole bound
        # rests on, and this string is where most callers will meet it.
        scope = (
            f"within each of the {len(self._groups)} calibrated group(s)"
            if self._grouped
            else "averaged over all instances"
        )
        return (
            f"Marginally over the calibration draw and one new instance, {scope}, the prediction "
            f"set contains the true expansion with probability at least {1.0 - self._alpha:.4g}. "
            f"An answer is returned only when that set is a singleton, which bounds the JOINT rate "
            f"of answering and being wrong by {self._alpha:.4g} -- it does NOT bound the error rate "
            f"among answered instances, which is that divided by the answer rate and is larger. "
            f"{ASSUMPTION}"
        )

    def prediction_set(self, result: DisambiguationResult) -> tuple[str, ...]:
        """Every candidate the calibration admits for ``result``.

        Args:
            result: The result to build a set for.

        Returns:
            Admitted expansions in the result's candidate order. Empty when no
            candidate is plausible, when the result has no candidates, or when
            the result falls in a group this gate never calibrated.
        """
        group = self._groups.get(self._group_by(result))
        if group is None:
            return ()
        return tuple(
            expansion for expansion, score in nonconformity(result) if score <= group.threshold
        )

    def decide(self, result: DisambiguationResult) -> ConformalDecision:
        """Answer or refuse, with the reason and the set attached.

        The rule is the whole policy and it is one line: **answer when the
        prediction set is a singleton, refuse otherwise.** A set of two or more
        is a genuine ambiguity at this ``alpha``; an empty set is the calibration
        saying no candidate is plausible at all, which is a different refusal and
        is reported as one.

        An instance whose group this gate never calibrated is refused rather
        than fitted to the nearest group or to a pooled threshold. Both of those
        would return an answer under a guarantee that was never computed for it.

        Args:
            result: The result to decide.

        Returns:
            The decision.

        Example:
            >>> from acronymkit.config import Config
            >>> from acronymkit.disambiguation import ExpansionDictionary, LexicalDisambiguator
            >>> index = ExpansionDictionary({"BP": ["blood pressure", "boiling point"]})
            >>> engine = LexicalDisambiguator(Config(), index)
            >>> pairs = [
            ...     (engine.disambiguate("BP", "Blood pressure was elevated."), "blood pressure"),
            ...     (engine.disambiguate("BP", "The boiling point of water."), "boiling point"),
            ... ]
            >>> gate = ConformalGate.calibrate(pairs, alpha=0.5)
            >>> decision = gate.decide(engine.disambiguate("BP", "Nothing to go on here."))
            >>> decision.reason, decision.prediction_set
            ('no_plausible_candidate', ())

            Two calibration points at ``alpha = 0.5`` buy a tight threshold, and
            a sentence with no evidence in it clears none of it. That refusal is
            reported separately from ``'ambiguous'`` because the two mean
            different things to whoever has to act on them: nothing was
            plausible, rather than several things were.
        """
        key = self._group_by(result)
        group = self._groups.get(key)
        if group is None:
            return ConformalDecision(
                expansion=None,
                prediction_set=(),
                abstained=True,
                reason=UNCALIBRATED_GROUP,
                group=key,
                threshold=None,
            )
        admitted = tuple(
            expansion for expansion, score in nonconformity(result) if score <= group.threshold
        )
        if not result.candidates:
            reason = NO_CANDIDATES
        elif len(admitted) == 1:
            reason = ANSWERED
        elif admitted:
            reason = AMBIGUOUS
        else:
            reason = NO_PLAUSIBLE_CANDIDATE
        return ConformalDecision(
            expansion=admitted[0] if reason == ANSWERED else None,
            prediction_set=admitted,
            abstained=reason != ANSWERED,
            reason=reason,
            group=key,
            threshold=group.threshold,
        )

    def __repr__(self) -> str:  # pragma: no cover - display helper
        kind = "mondrian" if self._grouped else "marginal"
        return (
            f"ConformalGate({kind}, alpha={self._alpha!r}, "
            f"groups={len(self._groups)}, n={self.calibration_size})"
        )


def _validated_alpha(value: object) -> float:
    """Return ``value`` as a usable target error rate, or raise.

    Args:
        value: The caller's ``alpha``.

    Returns:
        The rate as a ``float``.

    Raises:
        ConfigurationError: If it is not a real number strictly inside
            ``(0, 1)``. ``bool`` is refused for the same reason
            ``min_margin=True`` is: nobody writing it meant ``alpha = 1.0``.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"alpha must be a number in (0.0, 1.0), not {value!r}")
    numeric = float(value)
    if not 0.0 < numeric < 1.0:
        raise ConfigurationError(
            f"alpha={numeric!r} is outside (0.0, 1.0); alpha=0 asks for a guarantee no finite "
            "calibration set can give and alpha=1 asks for none at all"
        )
    return numeric


def group_counts(
    labelled: Iterable[tuple[DisambiguationResult, str]],
    group_by: Callable[[DisambiguationResult], str],
) -> Mapping[str, int]:
    """Count a calibration set by group, so a caller can size ``alpha`` first.

    Mondrian calibration fails loudly when a group is too small, which is
    correct and is a poor way to find out. This answers the question before
    :meth:`ConformalGate.calibrate` is called.

    Args:
        labelled: The same ``(result, gold)`` pairs calibration would take.
        group_by: The grouping to count under.

    Returns:
        Group key to instance count.
    """
    counts: dict[str, int] = {}
    for result, _ in labelled:
        key = group_by(result)
        counts[key] = counts.get(key, 0) + 1
    return counts
