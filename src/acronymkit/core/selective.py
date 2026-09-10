"""Risk-controlled selective classification: a bound on the ANSWERS, not on the draw.

What this is for, and what it fixes
-----------------------------------
:mod:`acronymkit.core.conformal` bounds the *joint* rate of answering and being
wrong -- ``P(answered and wrong) <= alpha``, averaged over every instance
including the ones the gate refuses. A governance caller who reads "abstain
unless confident" expects something else and says so in different words:
**of the answers you did give, at most ``alpha`` are wrong.** Those are two
different quantities and the second is the first divided by the answer rate, so
it is always the larger of the two.

The gap has a measured size on this project's own corpus rather than a
rhetorical one. On ``conformal.sdu21.exchangeable`` the Mondrian-by-arity gate at
``alpha = 0.05`` answered ``9.43`` % of instances, kept the joint rate at
``2.07`` % against its bound of ``5.00`` % -- and got ``21.92`` % of its answers
wrong, which is ``4.38`` times ``alpha``. That multiple falls to ``2.88``,
``1.85``, ``1.37`` and ``0.97`` as ``alpha`` rises to ``0.50``, so **the
overshoot is worst exactly where a governance caller would set the threshold.**

This module controls the other quantity. Given a selection function ``g`` and a
0/1 loss ``L``, it calibrates a threshold for which

    ``R_selective = E[L . g(X)] / E[g(X)] <= alpha``

holds with probability at least ``1 - delta`` over the calibration draw, under
exchangeability between calibration and deployment. That is **Learn-Then-Test**:
a family of candidate configurations, an exact p-value per candidate, and a
family-wise error correction across the family. It changes which functional is
controlled; it does not weaken what the data has to look like.

The guarantee, and the assumption it rests on
---------------------------------------------
Stated once here and re-stated by :meth:`SelectiveRiskGate.guarantee` at
runtime, because the two halves must never be quoted apart:

    With probability at least ``1 - delta`` over the draw of the calibration
    set, the selective risk of the returned threshold is at most ``alpha``: of
    the instances this gate answers, the expected share it gets wrong is at most
    ``alpha``. This holds **only if** the calibration instances and the
    instances the gate is later asked about are exchangeable, and only if the
    accepted calibration units are independent. Learn-Then-Test does not repeal
    exchangeability -- it changes which functional is controlled, not what the
    data has to look like. An out-of-domain caller violates exactly that, and
    the guarantee then says nothing at all.

Why the p-value is a binomial tail, and where that is exact
------------------------------------------------------------
Fix one candidate threshold ``lambda`` *before looking at the data*. Its
selection function ``g_lambda`` is then a fixed function, so conditional on
which calibration units it accepts, those units are draws from the conditional
law ``P(. | g_lambda(X) = 1)`` and their losses are i.i.d. Bernoulli with
parameter exactly ``R_selective(lambda)``. Conditional on the accepted count
``n``, the error count is therefore ``Binomial(n, R_selective(lambda))``, and

    ``p(lambda) = P(Binomial(n, alpha) <= errors)``

is an exact (conservative) p-value for ``H_lambda : R_selective(lambda) > alpha``
-- exact conditionally, and therefore valid marginally by the tower property,
which is the form the multiplicity correction needs.

**Two things that are not covered by that sentence, both named rather than
buried.** First, the accepted units must be independent; clustered units -- many
licensed occurrences sharing one committed definition -- inflate the true
variance and the binomial tail understates it. A caller with clustered data
should calibrate on one unit per cluster, which is what
``bench/run_selective_risk.py`` does. Second, the loss must be 0/1:
:meth:`SelectiveRiskGate.calibrate` refuses anything else rather than silently
applying a binomial argument to a bounded loss, for which the correct device is
a Hoeffding-Bentkus bound and which is **not implemented here.**

Multiplicity, which is what Learn-Then-Test actually spends
------------------------------------------------------------
Testing many thresholds and keeping the ones that pass is a multiple-comparisons
problem, and the correction is where the statistical power goes. Two are
offered and neither is free:

``"bonferroni"`` (default)
    Every candidate is tested at ``delta / len(grid)``. Valid whatever the risk
    curve does, which is the reason it is the default: the selective risk of
    this project's own selection families is **not monotone** in the threshold,
    so an ordering argument would be assuming what it needs to prove.
``"fixed_sequence"``
    Candidates are tested in the order given at the full ``delta`` and testing
    stops at the first non-rejection. Free of any correction, and valid **only**
    when the caller can order the family a priori by decreasing confidence of
    rejection. It is offered, it is not the default, and its docstring says
    exactly when using it is unsound.

Determinism
-----------
No randomness and no clock. Every score is rounded to
:data:`SELECTIVE_PRECISION` places, the threshold grid is a fixed arithmetic
sequence rather than a data-dependent set of quantiles, and the binomial tail is
summed with :func:`math.fsum` in a fixed order, which is exactly rounded. The
same inputs give the same certificate on every platform.

Import policy
-------------
Standard library and :mod:`acronymkit.core.exceptions`, and nothing else --
:mod:`acronymkit.core` is a leaf and ``tests/test_architecture_boundaries.py``
walks the syntax tree to keep it one. No regular expression, no lexical asset,
no string normalisation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .exceptions import ConfigurationError

__all__ = [
    "BONFERRONI",
    "DEFAULT_THRESHOLD_GRID",
    "EXTRACTION_MODES",
    "FIXED_SEQUENCE",
    "MODE_CATALOG",
    "MODE_INLINE",
    "MODE_PROPAGATED",
    "SELECTIVE_ASSUMPTION",
    "SELECTIVE_PRECISION",
    "Observation",
    "RiskCandidate",
    "SelectiveRiskGate",
    "StratumCertificate",
    "binomial_at_most",
    "selective_p_value",
    "smallest_certifiable_size",
    "stratum_counts",
]


#: Decimal places every selection score is rounded to before comparison. Same
#: role, same value and same reason as
#: :data:`acronymkit.core.conformal.NONCONFORMITY_PRECISION`: two scores that
#: differ below this are treated as equal, which makes acceptance reproducible
#: across platforms.
SELECTIVE_PRECISION = 9

#: The exchangeability assumption, in one sentence, for the selective bound.
#: Held as a constant rather than repeated in prose so that no surface can state
#: the guarantee without it: :meth:`SelectiveRiskGate.guarantee` concatenates the
#: two, and ``tests/test_selective.py`` asserts that every guarantee-bearing
#: paragraph in this module names it.
#:
#: It names **two** conditions and not one. Exchangeability is the condition
#: split conformal already needed and Learn-Then-Test does not repeal;
#: independence of the accepted units is the extra condition the binomial tail
#: needs, and it is the one a document-scoped caller is most likely to break.
SELECTIVE_ASSUMPTION = (
    "This holds only under exchangeability between the calibration instances and "
    "the instances the gate is asked about, and only if the accepted calibration "
    "units are independent of one another; an out-of-domain caller violates the "
    "first and a caller whose units cluster inside one document violates the "
    "second, and either one is given no guarantee at all."
)

#: Multiplicity corrections. Exhaustive.
BONFERRONI = "bonferroni"
FIXED_SEQUENCE = "fixed_sequence"

#: Extraction modes, as stratum keys. These are the three ways an expansion
#: enters an answer in this library, and they are strings rather than an enum so
#: that :mod:`acronymkit.core` can name them without importing either half of
#: the package it sits under.
#:
#: **Naming them here is not a claim that they behave differently.** Whether
#: stratifying by them buys anything is an empirical question and
#: ``bench/run_selective_risk.py`` answers it; on MED1250 the answer is no.
MODE_INLINE = "inline"
MODE_PROPAGATED = "propagated"
MODE_CATALOG = "catalog"

#: The three, in the order every table in this project prints them.
EXTRACTION_MODES: Tuple[str, ...] = (MODE_INLINE, MODE_PROPAGATED, MODE_CATALOG)

#: The default candidate family: twenty-one evenly spaced thresholds.
#:
#: **Fixed and data-independent on purpose.** A grid of empirical quantiles
#: would put the calibration data inside the family the multiplicity correction
#: is computed over, which is the one thing Learn-Then-Test may not do. Twenty-one
#: is a choice and it is priced: the Bonferroni level is ``delta / 21``, so the
#: grid's size is paid for in statistical power at every alpha.
DEFAULT_THRESHOLD_GRID: Tuple[float, ...] = tuple(round(step / 20.0, 4) for step in range(21))


def binomial_at_most(errors: int, trials: int, rate: float) -> float:
    """``P(Binomial(trials, rate) <= errors)``, summed in a fixed order.

    Computed in log space and summed with :func:`math.fsum`, which is exactly
    rounded, so the result is reproducible bit for bit across platforms rather
    than merely close.

    Args:
        errors: Observed successes (here: losses). May exceed ``trials``.
        trials: Number of draws. ``0`` returns ``1.0``: with nothing observed,
            nothing is ruled out.
        rate: Success probability, in ``[0, 1]``.

    Returns:
        The lower tail probability, in ``[0, 1]``.

    Example:
        >>> round(binomial_at_most(0, 20, 0.5), 6)
        1e-06
        >>> binomial_at_most(3, 3, 0.25)
        1.0
        >>> binomial_at_most(0, 0, 0.5)
        1.0
    """
    if trials <= 0:
        return 1.0
    if errors < 0:
        return 0.0
    if errors >= trials:
        return 1.0
    if rate <= 0.0:
        return 1.0
    if rate >= 1.0:
        return 0.0
    log_rate = math.log(rate)
    log_complement = math.log1p(-rate)
    terms = [
        math.exp(
            math.lgamma(trials + 1)
            - math.lgamma(index + 1)
            - math.lgamma(trials - index + 1)
            + index * log_rate
            + (trials - index) * log_complement
        )
        for index in range(errors + 1)
    ]
    return min(1.0, math.fsum(terms))


def selective_p_value(errors: int, accepted: int, alpha: float) -> float:
    """The Learn-Then-Test p-value for ``H : R_selective > alpha``.

    The supremum of ``P(errors or fewer)`` over the null ``R_selective >= alpha``
    is attained at the boundary ``R_selective = alpha``, because a binomial lower
    tail is decreasing in its rate. So the boundary value *is* the p-value and no
    supremum has to be taken numerically.

    Args:
        errors: Losses among the accepted calibration units.
        accepted: How many units the candidate accepted. ``0`` returns ``1.0``:
            a threshold that accepted nothing has certified nothing, and that is
            a refusal rather than an error.
        alpha: The target selective risk, in ``(0, 1)``.

    Returns:
        The p-value, in ``(0, 1]``.

    Example:
        >>> round(selective_p_value(12, 471, 0.05), 9)
        0.005852888
        >>> selective_p_value(0, 0, 0.05)
        1.0
    """
    return binomial_at_most(errors, accepted, alpha)


def smallest_certifiable_size(alpha: float, level: float) -> int:
    """Accepted units needed to certify ``alpha`` at ``level`` with **zero** losses.

    The most favourable observation possible is zero losses, whose p-value is
    ``(1 - alpha) ** accepted``. Setting that equal to ``level`` and solving gives
    the floor below which no observation whatever can certify, which is the
    number a caller should read *before* splitting a calibration set three ways.

    Args:
        alpha: Target selective risk, in ``(0, 1)``.
        level: The per-candidate level actually spent -- ``delta`` under fixed
            sequence, ``delta / len(grid)`` under Bonferroni. Passing ``delta``
            where the code spends ``delta / 21`` understates this by a factor of
            roughly three, which is why the parameter is the *level* and not the
            ``delta``.

    Returns:
        The minimum accepted count.

    Example:
        >>> smallest_certifiable_size(0.05, 0.05 / 21)
        118
        >>> smallest_certifiable_size(0.20, 0.05 / 21)
        28
    """
    if not 0.0 < alpha < 1.0:
        raise ConfigurationError(f"alpha must be in (0.0, 1.0), not {alpha!r}")
    if not 0.0 < level < 1.0:
        raise ConfigurationError(f"level must be in (0.0, 1.0), not {level!r}")
    return math.ceil(math.log(level) / math.log(1.0 - alpha))


@dataclass(frozen=True)
class Observation:
    """One labelled calibration unit: where it came from, how sure, and was it wrong.

    Attributes:
        stratum: The group this unit calibrates. ``""`` for an unstratified
            (pooled) calibration, exactly as ``""`` means marginal in
            :class:`~acronymkit.core.conformal.GroupCalibration`.
        score: The selection score, **lower is more confident**, matching
            :func:`~acronymkit.core.conformal.nonconformity`. A unit is accepted
            at threshold ``t`` when ``score <= t``.
        loss: ``0`` when the answer this unit would have produced is right,
            ``1`` when it is wrong. Nothing else is accepted; see the module
            docstring for why a bounded loss needs a different bound.
    """

    stratum: str
    score: float
    loss: int


@dataclass(frozen=True)
class RiskCandidate:
    """One threshold under test, and everything the test saw.

    Kept on the certificate so the arithmetic is auditable without re-running the
    corpus: a reader can recompute the p-value from ``errors`` and ``accepted``
    and get the same number.

    Attributes:
        threshold: The candidate threshold.
        accepted: Calibration units it accepts.
        errors: Losses among those.
        p_value: :func:`selective_p_value` of the two, at the gate's ``alpha``.
        rejected: Whether the p-value cleared the per-candidate level. A rejected
            null is a *certified* threshold, and the two words point opposite
            ways, which is why both are recorded.
    """

    threshold: float
    accepted: int
    errors: int
    p_value: float
    rejected: bool

    @property
    def empirical_risk(self) -> Optional[float]:
        """Losses over accepted, or ``None`` when nothing was accepted."""
        if self.accepted <= 0:
            return None
        return self.errors / self.accepted


@dataclass(frozen=True)
class StratumCertificate:
    """What Learn-Then-Test concluded about one stratum, including "nothing".

    A certificate whose :attr:`certified` is ``False`` is a first-class result
    and not an error: it says this stratum's calibration set cannot support this
    ``alpha``, which is the answer a caller needs before they set one.

    Attributes:
        stratum: The stratum key, ``""`` when pooled.
        alpha: Target selective risk.
        delta: Family-wise error budget.
        level: The per-candidate level actually spent.
        correction: :data:`BONFERRONI` or :data:`FIXED_SEQUENCE`.
        calibration_units: Units in this stratum, accepted or not.
        candidates_tested: How many thresholds were actually tested. R17: the
            multiplicity is the work, so the work count ships with the result.
        candidates_certified: How many of them cleared the level.
        threshold: The chosen threshold, or ``None`` when nothing certified.
        accepted: Accepted calibration units at that threshold.
        errors: Losses among them.
        p_value: The chosen candidate's p-value, or the smallest seen when
            nothing certified -- which tells a caller *how far* off it was.
        certified: Whether a threshold carries the bound.
        required_units: :func:`smallest_certifiable_size` at this ``alpha`` and
            ``level``: the accepted count a **flawless** stratum would still
            need. Printed beside :attr:`calibration_units` so that "too small"
            is a comparison rather than an opinion.
        refusal: Why nothing certified, or ``""``.
    """

    stratum: str
    alpha: float
    delta: float
    level: float
    correction: str
    calibration_units: int
    candidates_tested: int
    candidates_certified: int
    threshold: Optional[float]
    accepted: int
    errors: int
    p_value: float
    certified: bool
    required_units: int
    refusal: str

    @property
    def empirical_risk(self) -> Optional[float]:
        """Calibration selective risk at the chosen threshold, or ``None``."""
        if self.accepted <= 0:
            return None
        return self.errors / self.accepted

    @property
    def calibration_answer_rate(self) -> Optional[float]:
        """Share of this stratum's calibration units the threshold accepts.

        ``None`` when the stratum is empty. **Always read beside the bound**: a
        gate that answers nothing satisfies every selective bound there is, and
        is the same refusal with better mathematics.
        """
        if self.calibration_units <= 0:
            return None
        return self.accepted / self.calibration_units


def _validated_rate(value: object, name: str) -> float:
    """Return ``value`` as a rate strictly inside ``(0, 1)``, or raise.

    Args:
        value: The caller's number.
        name: Which parameter, for the message.

    Returns:
        The rate as a ``float``.

    Raises:
        ConfigurationError: If it is not a real number strictly inside
            ``(0, 1)``. ``bool`` is refused for the reason
            :func:`acronymkit.core.conformal._validated_alpha` refuses it:
            nobody writing ``True`` meant ``1.0``.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number in (0.0, 1.0), not {value!r}")
    numeric = float(value)
    if not 0.0 < numeric < 1.0:
        raise ConfigurationError(
            f"{name}={numeric!r} is outside (0.0, 1.0); {name}=0 asks for a guarantee no finite "
            "calibration set can give and 1 asks for none at all"
        )
    return numeric


def _tally(units: Sequence[Observation], threshold: float) -> Tuple[int, int]:
    """Accepted count and loss count for one threshold.

    Args:
        units: The stratum's calibration units.
        threshold: The candidate.

    Returns:
        ``(accepted, errors)``.
    """
    accepted = 0
    errors = 0
    for unit in units:
        if unit.score <= threshold:
            accepted += 1
            errors += unit.loss
    return accepted, errors


def _certify_stratum(
    stratum: str,
    units: Sequence[Observation],
    *,
    alpha: float,
    delta: float,
    grid: Sequence[float],
    correction: str,
) -> Tuple[StratumCertificate, Tuple[RiskCandidate, ...]]:
    """Run Learn-Then-Test over ``grid`` for one stratum.

    Under :data:`BONFERRONI` every candidate is tested at ``delta / len(grid)``
    and the certified set is every candidate that clears it. Under
    :data:`FIXED_SEQUENCE` candidates are tested in the order given at the full
    ``delta`` and testing **stops at the first non-rejection**, so the certified
    set is a prefix.

    Every member of the certified set carries the bound simultaneously, so
    choosing among them is free: the one with the largest accepted count is
    taken, because answer rate is the only thing left to prefer once the risk is
    controlled. Ties go to the smaller threshold, which keeps the choice a
    function of the data and not of dictionary order.

    Args:
        stratum: The stratum key.
        units: Its calibration units.
        alpha: Target selective risk.
        delta: Family-wise error budget.
        grid: The candidate thresholds, in test order.
        correction: Which multiplicity correction to spend it under.

    Returns:
        The certificate and every candidate that was tested.
    """
    level = delta / len(grid) if correction == BONFERRONI else delta
    tested: List[RiskCandidate] = []
    for threshold in grid:
        accepted, errors = _tally(units, threshold)
        p_value = selective_p_value(errors, accepted, alpha)
        rejected = p_value <= level
        tested.append(RiskCandidate(threshold, accepted, errors, p_value, rejected))
        if correction == FIXED_SEQUENCE and not rejected:
            break
    certified = [candidate for candidate in tested if candidate.rejected]
    required = smallest_certifiable_size(alpha, level)
    if certified:
        best = min(certified, key=lambda candidate: (-candidate.accepted, candidate.threshold))
        return (
            StratumCertificate(
                stratum=stratum,
                alpha=alpha,
                delta=delta,
                level=level,
                correction=correction,
                calibration_units=len(units),
                candidates_tested=len(tested),
                candidates_certified=len(certified),
                threshold=best.threshold,
                accepted=best.accepted,
                errors=best.errors,
                p_value=best.p_value,
                certified=True,
                required_units=required,
                refusal="",
            ),
            tuple(tested),
        )
    smallest = min((candidate.p_value for candidate in tested), default=1.0)
    if len(units) < required:
        refusal = (
            f"{len(units)} calibration unit(s) in stratum {stratum or '<pooled>'!r}; "
            f"{required} accepted units with ZERO losses are the floor at alpha={alpha:.4g} "
            f"and level={level:.6g}, so no observation on this stratum could have certified"
        )
    else:
        refusal = (
            f"no threshold in the {len(tested)}-point grid reached level={level:.6g} at "
            f"alpha={alpha:.4g}; the smallest p-value seen was {smallest:.6g}. The gate answers "
            "nothing at this alpha, and an abstention mechanism that answers nothing is not a fix"
        )
    return (
        StratumCertificate(
            stratum=stratum,
            alpha=alpha,
            delta=delta,
            level=level,
            correction=correction,
            calibration_units=len(units),
            candidates_tested=len(tested),
            candidates_certified=0,
            threshold=None,
            accepted=0,
            errors=0,
            p_value=smallest,
            certified=False,
            required_units=required,
            refusal=refusal,
        ),
        tuple(tested),
    )


class SelectiveRiskGate:
    """A calibrated selective-risk policy, built from the caller's own data.

    Construct one with :meth:`calibrate`. Instances are immutable and hold no
    per-call state.

    **A stratum that did not certify refuses everything.** It is not backed off
    to a pooled threshold and not fitted to the nearest neighbour: both would
    return answers under a bound that was never computed for them, which is the
    defect this module exists to remove rather than relocate.

    Example:
        A stratum of forty units with two losses, calibrated at a loose alpha so
        the example stays short. Forty units is not a calibration set.

        >>> units = [Observation("", 0.1, 0) for _ in range(38)]
        >>> units += [Observation("", 0.9, 1), Observation("", 0.95, 1)]
        >>> gate = SelectiveRiskGate.calibrate(units, alpha=0.2, delta=0.05)
        >>> gate.certificate("").certified
        True
        >>> gate.admits("", 0.05), gate.admits("", 0.99)
        (True, False)
        >>> "exchangeab" in gate.guarantee()
        True
    """

    __slots__ = ("_alpha", "_candidates", "_certificates", "_correction", "_delta", "_stratified")

    def __init__(
        self,
        *,
        alpha: float,
        delta: float,
        certificates: Sequence[StratumCertificate],
        correction: str = BONFERRONI,
        stratified: bool = False,
        candidates: Optional[Mapping[str, Sequence[RiskCandidate]]] = None,
    ) -> None:
        """Build a gate from certificates that have already been computed.

        Args:
            alpha: Target selective risk the certificates were computed for.
            delta: Family-wise error budget they were computed at.
            certificates: One per stratum. A pooled gate carries exactly one,
                keyed ``""``.
            correction: Which multiplicity correction was spent.
            stratified: Whether this is a Mondrian (per-stratum) calibration.
            candidates: Every tested threshold per stratum, for audit. Optional.

        Raises:
            ConfigurationError: If ``certificates`` is empty, if two share a
                stratum key, if a pooled gate does not carry exactly one keyed
                ``""``, or if a stratified gate uses ``""`` -- that key is
                reserved so "pooled" and "one stratum that happens to be unnamed"
                cannot be confused by anything reading the thresholds back.
        """
        if not certificates:
            raise ConfigurationError("a SelectiveRiskGate needs at least one stratum certificate")
        keys = [certificate.stratum for certificate in certificates]
        if len(set(keys)) != len(keys):
            raise ConfigurationError(f"duplicate stratum key(s) in {keys!r}")
        if not stratified and keys != [""]:
            raise ConfigurationError(
                f"a pooled gate carries exactly one stratum keyed '', got keys {keys!r}"
            )
        if stratified and "" in keys:
            raise ConfigurationError(
                "'' is reserved for pooled calibration; a stratify_by must return a non-empty key"
            )
        self._alpha = float(alpha)
        self._delta = float(delta)
        self._correction = correction
        self._stratified = stratified
        self._certificates = {certificate.stratum: certificate for certificate in certificates}
        self._candidates = {key: tuple(value) for key, value in (candidates or {}).items()}

    @classmethod
    def calibrate(
        cls,
        observations: Iterable[Observation],
        *,
        alpha: float,
        delta: float = 0.05,
        grid: Sequence[float] = DEFAULT_THRESHOLD_GRID,
        correction: str = BONFERRONI,
        stratify_by: Optional[Callable[[Observation], str]] = None,
    ) -> SelectiveRiskGate:
        """Fit a gate to a calibration set. One pass, no model, no randomness.

        Args:
            observations: Labelled units from the caller's own data. ``stratum``
                is read off each observation, or recomputed by ``stratify_by``.
            alpha: Target selective risk in ``(0, 1)`` -- and this one **is** the
                fraction of answers expected to be wrong, which is the whole
                difference from :meth:`acronymkit.core.conformal.ConformalGate.calibrate`,
                whose ``alpha`` bounds a joint rate several times smaller.
            delta: Probability the whole calibration is allowed to fail, over the
                draw of the calibration set. ``0.05`` by default. It is **not**
                a second error rate on the answers.
            grid: Candidate thresholds. Must be non-empty and must not depend on
                ``observations``; see :data:`DEFAULT_THRESHOLD_GRID`.
            correction: :data:`BONFERRONI` or :data:`FIXED_SEQUENCE`.
            stratify_by: ``None`` for a pooled calibration -- one threshold, one
                bound over everything. A callable for a Mondrian (per-stratum)
                calibration: each stratum gets its own threshold from its own
                units and the bound then holds inside each. Splitting the
                calibration set is not free and this module will not pretend it
                is: each stratum pays :func:`smallest_certifiable_size` on its
                own, so three strata need roughly three times the data.

        Returns:
            The fitted gate. A stratum that cannot be certified is present and
            refuses everything, rather than being dropped.

        Raises:
            ConfigurationError: If ``alpha`` or ``delta`` is not a real number in
                ``(0, 1)``, if ``grid`` is empty, if ``correction`` is unknown,
                if there are no observations, or if any loss is not ``0`` or
                ``1``.
        """
        numeric_alpha = _validated_rate(alpha, "alpha")
        numeric_delta = _validated_rate(delta, "delta")
        if correction not in (BONFERRONI, FIXED_SEQUENCE):
            raise ConfigurationError(
                f"correction must be {BONFERRONI!r} or {FIXED_SEQUENCE!r}, not {correction!r}"
            )
        thresholds = tuple(float(value) for value in grid)
        if not thresholds:
            raise ConfigurationError(
                "the candidate grid is empty; Learn-Then-Test has nothing to test"
            )
        buckets: Dict[str, List[Observation]] = {}
        for observation in observations:
            if observation.loss not in (0, 1) or isinstance(observation.loss, bool):
                raise ConfigurationError(
                    f"loss must be the int 0 or 1, not {observation.loss!r}. The p-value here is a "
                    "binomial tail and is exact only for a 0/1 loss; a bounded loss needs a "
                    "Hoeffding-Bentkus bound, which this module does not implement."
                )
            key = stratify_by(observation) if stratify_by is not None else observation.stratum
            rounded = Observation(
                stratum=key,
                score=round(float(observation.score), SELECTIVE_PRECISION),
                loss=int(observation.loss),
            )
            buckets.setdefault(key, []).append(rounded)
        if not buckets:
            raise ConfigurationError(
                "the calibration set is empty; there is no selective risk to bound"
            )
        stratified = stratify_by is not None or set(buckets) != {""}
        certificates = []
        candidates: Dict[str, Sequence[RiskCandidate]] = {}
        for key in sorted(buckets):
            certificate, tested = _certify_stratum(
                key,
                buckets[key],
                alpha=numeric_alpha,
                delta=numeric_delta,
                grid=thresholds,
                correction=correction,
            )
            certificates.append(certificate)
            candidates[key] = tested
        return cls(
            alpha=numeric_alpha,
            delta=numeric_delta,
            certificates=certificates,
            correction=correction,
            stratified=stratified,
            candidates=candidates,
        )

    # -- properties --------------------------------------------------------
    @property
    def alpha(self) -> float:
        """The selective risk this gate was calibrated to bound."""
        return self._alpha

    @property
    def delta(self) -> float:
        """The probability the calibration itself is allowed to fail."""
        return self._delta

    @property
    def correction(self) -> str:
        """Which multiplicity correction was spent."""
        return self._correction

    @property
    def is_stratified(self) -> bool:
        """Whether this is a Mondrian (per-stratum) calibration."""
        return self._stratified

    @property
    def certificates(self) -> Tuple[StratumCertificate, ...]:
        """Every stratum's certificate, ordered by key."""
        return tuple(self._certificates[key] for key in sorted(self._certificates))

    @property
    def certified_strata(self) -> Tuple[str, ...]:
        """The strata that carry a bound, ordered by key."""
        return tuple(key for key in sorted(self._certificates) if self._certificates[key].certified)

    @property
    def calibration_size(self) -> int:
        """Total calibration units across all strata."""
        return sum(certificate.calibration_units for certificate in self._certificates.values())

    # -- public API --------------------------------------------------------
    def certificate(self, stratum: str = "") -> Optional[StratumCertificate]:
        """The certificate for ``stratum``, or ``None`` if it was never calibrated.

        Args:
            stratum: The stratum key.

        Returns:
            The certificate, including an uncertified one.
        """
        return self._certificates.get(stratum)

    def tested(self, stratum: str = "") -> Tuple[RiskCandidate, ...]:
        """Every threshold tested in ``stratum``, in test order.

        Args:
            stratum: The stratum key.

        Returns:
            The candidates, empty when none were recorded.
        """
        return tuple(self._candidates.get(stratum, ()))

    def admits(self, stratum: str, score: float) -> bool:
        """Whether this gate answers a unit in ``stratum`` scoring ``score``.

        Args:
            stratum: The stratum the unit falls in.
            score: Its selection score, lower being more confident.

        Returns:
            ``False`` for an uncalibrated stratum, for an uncertified one, and
            for a score above the certified threshold. Those three refusals are
            different and :meth:`refusal` names which one fired.
        """
        certificate = self._certificates.get(stratum)
        if certificate is None or not certificate.certified or certificate.threshold is None:
            return False
        return round(float(score), SELECTIVE_PRECISION) <= certificate.threshold

    def refusal(self, stratum: str, score: float) -> str:
        """Why a unit was refused, or ``""`` when it was not.

        Args:
            stratum: The stratum the unit falls in.
            score: Its selection score.

        Returns:
            ``"uncalibrated_stratum"``, ``"uncertified_stratum"``,
            ``"above_threshold"`` or ``""``.
        """
        certificate = self._certificates.get(stratum)
        if certificate is None:
            return "uncalibrated_stratum"
        if not certificate.certified or certificate.threshold is None:
            return "uncertified_stratum"
        if round(float(score), SELECTIVE_PRECISION) > certificate.threshold:
            return "above_threshold"
        return ""

    def guarantee(self) -> str:
        """The guarantee, what it does not say, and its assumption, in one string.

        Returns:
            A sentence naming ``alpha``, ``delta``, what is bounded, the answer
            rate the bound was bought at, and :data:`SELECTIVE_ASSUMPTION`. The
            assumption is concatenated here rather than left to the caller
            because a guarantee quoted without it is the most expensive
            overclaim this subsystem can make -- and Learn-Then-Test does not
            repeal exchangeability, it only changes which functional is bounded.

        Example:
            >>> units = [Observation("", 0.1, 0) for _ in range(60)]
            >>> gate = SelectiveRiskGate.calibrate(units, alpha=0.2, delta=0.05)
            >>> gate.guarantee().startswith("With probability at least")
            True
        """
        certified = self.certified_strata
        scope = (
            f"within each of the {len(certified)} certified stratum/strata of "
            f"{len(self._certificates)}"
            if self._stratified
            else "over all instances"
        )
        rates = [
            certificate.calibration_answer_rate
            for certificate in self.certificates
            if certificate.certified and certificate.calibration_answer_rate is not None
        ]
        answered = (
            f"{min(rates) * 100.0:.4g}% to {max(rates) * 100.0:.4g}% of calibration units"
            if rates
            else "NOTHING -- no stratum certified, so this gate answers nothing at all"
        )
        # SELECTIVE_ASSUMPTION is concatenated below and is never optional. It
        # carries exchangeability between calibration and deployment -- the
        # condition split conformal already needed and Learn-Then-Test does not
        # repeal -- plus independence of the accepted units, which the binomial
        # tail needs and a document-scoped caller is most likely to break.
        return (
            f"With probability at least {1.0 - self._delta:.4g} over the draw of the calibration "
            f"set, {scope}, at most {self._alpha:.4g} of the instances this gate ANSWERS are "
            f"wrong. That is the selective risk and not the joint rate: it is already divided by "
            f"the answer rate, so unlike a split-conformal alpha it needs no such division. It "
            f"says nothing about the instances the gate refuses, and it was bought at an answer "
            f"rate of {answered}, which must be read beside it because a gate that answers "
            f"nothing satisfies every selective bound there is. {SELECTIVE_ASSUMPTION}"
        )

    def __repr__(self) -> str:  # pragma: no cover - display helper
        kind = "mondrian" if self._stratified else "pooled"
        return (
            f"SelectiveRiskGate({kind}, alpha={self._alpha!r}, delta={self._delta!r}, "
            f"strata={len(self._certificates)}, certified={len(self.certified_strata)}, "
            f"n={self.calibration_size})"
        )


def stratum_counts(
    observations: Iterable[Observation],
    stratify_by: Optional[Callable[[Observation], str]] = None,
) -> Mapping[str, int]:
    """Count a calibration set by stratum, so a caller can size ``alpha`` first.

    Three strata means three calibration sets, and the smallest of them is what
    decides whether a per-stratum bound is possible at all. This answers that
    before :meth:`SelectiveRiskGate.calibrate` is called; compare each count
    against :func:`smallest_certifiable_size`.

    Args:
        observations: The same units calibration would take.
        stratify_by: The stratification to count under, or ``None`` to read
            ``Observation.stratum``.

    Returns:
        Stratum key to unit count.
    """
    counts: Dict[str, int] = {}
    for observation in observations:
        key = stratify_by(observation) if stratify_by is not None else observation.stratum
        counts[key] = counts.get(key, 0) + 1
    return counts
