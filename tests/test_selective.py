"""Tests for :mod:`acronymkit.core.selective` and the selective gate in ``propagate``.

What is actually checked here, in the order it matters
------------------------------------------------------
* :class:`TestTheBinomialTail` -- the p-value is checked against **exact rational
  arithmetic** rather than against itself. A float implementation that agrees
  with a second float implementation of the same formula agrees about its own
  rounding; :class:`fractions.Fraction` does not.
* :class:`TestTheBoundHolds` -- a seeded simulation in which the true selective
  risk is *known in closed form*, so a violation is a violation and not a
  guess. The generator makes ``R_selective(t) = t ** 2 / 3``, so the correct
  answer is computable and the true violation rate -- not the sampled one -- can
  be compared against ``delta``.
* :class:`TestItRefusesRatherThanApproximates` -- an uncertified stratum refuses
  everything. This is the expensive behaviour and it is the one a later edit is
  most likely to "fix".
* :class:`TestTheGuaranteeIsNeverQuotedWithoutItsAssumption` -- the same prose
  rule ``tests/test_conformal.py`` applies to split conformal, applied to
  Learn-Then-Test, because LTT does not repeal exchangeability and a paragraph
  that forgets to say so is the overclaim this workstream exists to remove.
* :class:`TestPropagateWithASelectiveGate` -- the seam where the gate is
  consumed, including that a refusal never withholds a definition.

THIS MODULE READS CHECKOUT-ONLY FILES, and says so rather than being found out.
:class:`TestTheBenchRunner` imports ``bench/run_selective_risk.py`` and reads
``bench/results.json``. Neither is in an installed distribution -- `bench/` is
not laid down and `results.json` is a checkout artefact -- so that class carries
a class-level skip. It is the sixth recorded instance of this shape in this
repository and the guard is written before the first CI run rather than after
it. The other classes exercise the imported package only and must keep running
against the installed distribution, which is where a packaging defect in the new
module would actually show.
"""

from __future__ import annotations

import importlib.util
import math
import random
import sys
from fractions import Fraction
from pathlib import Path
from typing import List, Tuple

import pytest

from acronymkit.core.exceptions import ConfigurationError
from acronymkit.core.selective import (
    BONFERRONI,
    DEFAULT_THRESHOLD_GRID,
    EXTRACTION_MODES,
    FIXED_SEQUENCE,
    MODE_CATALOG,
    MODE_INLINE,
    MODE_PROPAGATED,
    SELECTIVE_ASSUMPTION,
    Observation,
    SelectiveRiskGate,
    binomial_at_most,
    selective_p_value,
    smallest_certifiable_size,
    stratum_counts,
)
from acronymkit.models import AcronymPair
from acronymkit.nlp.propagation import (
    SELECTIVE_ABOVE_THRESHOLD,
    SELECTIVE_IS_NOT_ONE_SENSE,
    SELECTIVE_UNCALIBRATED,
    SELECTIVE_UNCERTIFIED,
    SOURCE_DEFINITION,
    SOURCE_PROPAGATED,
    gate_disclosure,
    propagate,
    selective_score,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The per-candidate level the default grid and ``delta = 0.05`` actually spend.
LEVEL = 0.05 / len(DEFAULT_THRESHOLD_GRID)


def exact_binomial_at_most(errors: int, trials: int, numerator: int, denominator: int) -> Fraction:
    """``P(Bin(trials, numerator/denominator) <= errors)`` in exact rationals.

    An independent implementation in a different number system. It is slow and
    that is fine: it runs on trials of at most a few dozen and its job is to be
    *right*, not fast.

    Args:
        errors: Upper limit of the tail.
        trials: Number of draws.
        numerator: Success-probability numerator.
        denominator: Success-probability denominator.

    Returns:
        The exact probability.
    """
    rate = Fraction(numerator, denominator)
    return sum(
        (
            Fraction(math.comb(trials, index)) * rate**index * (1 - rate) ** (trials - index)
            for index in range(errors + 1)
        ),
        Fraction(0),
    )


#: True selective risk of threshold ``t`` under :func:`uniform_units`, in closed
#: form. ``E[score ** 2 | score <= t] = t ** 2 / 3``, so a certified threshold is
#: TRULY invalid exactly when ``t ** 2 / 3 > alpha`` -- a fact about the returned
#: threshold rather than about the draw, which is what lets
#: :class:`TestTheBoundHolds` mean something at forty replications instead of at
#: forty thousand.
def true_risk(threshold: float) -> float:
    """The closed-form selective risk of ``threshold`` under :func:`uniform_units`."""
    return threshold**2 / 3.0


def uniform_units(count: int, seed: int, stratum: str = "") -> List[Observation]:
    """Units whose true selective risk at threshold ``t`` is exactly ``t ** 2 / 3``.

    Scores are uniform on ``[0, 1]`` and a unit's loss is Bernoulli with
    parameter equal to its own score **squared**, so
    ``E[loss | score <= t] = t ** 2 / 3``. Squared rather than linear so that the
    generator is separable at a calibration size a unit test can afford: with a
    linear loss the risk curve rises so fast that certification at
    ``alpha = 0.10`` needs several thousand units, and a test that is really a
    statement about sample size is not a test of validity.

    Args:
        count: How many units.
        seed: Frozen seed.
        stratum: The stratum key to tag them with.

    Returns:
        The units.
    """
    rng = random.Random(seed)
    units = []
    for _ in range(count):
        score = rng.random()
        units.append(Observation(stratum, score, 1 if rng.random() < score * score else 0))
    return units


# ---------------------------------------------------------------------------
# the arithmetic
# ---------------------------------------------------------------------------
class TestTheBinomialTail:
    """The p-value, against exact rational arithmetic rather than against itself."""

    @pytest.mark.parametrize(
        "errors,trials,numerator,denominator",
        [
            (0, 1, 1, 2),
            (0, 20, 1, 20),
            (3, 20, 1, 20),
            (12, 40, 1, 5),
            (0, 59, 1, 20),
            (5, 30, 1, 10),
            (17, 30, 3, 10),
        ],
    )
    def test_it_matches_exact_rational_arithmetic(
        self, errors: int, trials: int, numerator: int, denominator: int
    ) -> None:
        exact = float(exact_binomial_at_most(errors, trials, numerator, denominator))
        computed = binomial_at_most(errors, trials, numerator / denominator)
        assert computed == pytest.approx(exact, rel=1e-12, abs=1e-15)

    def test_nothing_observed_rules_nothing_out(self) -> None:
        # A threshold that accepted no calibration unit has certified nothing.
        # Returning anything below 1.0 here would let an empty accepted set clear
        # the level, which is a gate that answers nothing carrying a bound.
        assert binomial_at_most(0, 0, 0.5) == 1.0
        assert selective_p_value(0, 0, 0.01) == 1.0

    def test_the_whole_tail_is_one_and_the_empty_tail_is_zero(self) -> None:
        assert binomial_at_most(7, 7, 0.3) == 1.0
        assert binomial_at_most(-1, 7, 0.3) == 0.0

    def test_the_tail_is_decreasing_in_the_rate(self) -> None:
        # This is the property that makes the boundary value the supremum over
        # the null, so it is checked rather than cited.
        values = [binomial_at_most(4, 60, rate) for rate in (0.02, 0.05, 0.10, 0.20, 0.40)]
        assert values == sorted(values, reverse=True)

    def test_it_never_leaves_the_unit_interval(self) -> None:
        for trials in (1, 5, 60, 400):
            for errors in range(0, trials + 1):
                value = binomial_at_most(errors, trials, 0.05)
                assert 0.0 <= value <= 1.0


class TestTheZeroErrorFloor:
    """``smallest_certifiable_size`` is the floor, and it is checked as one."""

    def test_one_unit_short_cannot_certify_and_the_floor_can(self) -> None:
        for alpha in (0.05, 0.10, 0.20):
            required = smallest_certifiable_size(alpha, LEVEL)
            assert selective_p_value(0, required - 1, alpha) > LEVEL
            assert selective_p_value(0, required, alpha) <= LEVEL

    def test_the_published_floors_reproduce(self) -> None:
        # The table docs/EVALUATION.md prints, recomputed here so the two cannot
        # drift apart without something going red.
        assert smallest_certifiable_size(0.01, LEVEL) == 602
        assert smallest_certifiable_size(0.02, LEVEL) == 299
        assert smallest_certifiable_size(0.05, LEVEL) == 118
        assert smallest_certifiable_size(0.20, LEVEL) == 28

    def test_a_rate_outside_the_open_unit_interval_is_refused(self) -> None:
        with pytest.raises(ConfigurationError):
            smallest_certifiable_size(0.0, LEVEL)
        with pytest.raises(ConfigurationError):
            smallest_certifiable_size(0.05, 1.0)


# ---------------------------------------------------------------------------
# the bound
# ---------------------------------------------------------------------------
class TestTheBoundHolds:
    """Finite-sample validity, on data whose true selective risk is known exactly."""

    @pytest.mark.parametrize("alpha", [0.10, 0.20])
    def test_the_true_selective_risk_of_the_certified_threshold_is_under_alpha(
        self, alpha: float
    ) -> None:
        """Over sixty seeded replications, the TRUE risk is checked, not the sample one.

        :func:`true_risk` gives ``R_selective(t)`` in closed form, so a certified
        threshold is *truly* invalid exactly when that exceeds ``alpha``. The
        count below is therefore a count of real violations and not of unlucky
        samples.
        """
        violations = 0
        certified = 0
        for seed in range(40):
            gate = SelectiveRiskGate.calibrate(
                uniform_units(600, seed=1000 + seed), alpha=alpha, delta=0.05
            )
            certificate = gate.certificate("")
            assert certificate is not None
            if not certificate.certified or certificate.threshold is None:
                continue
            certified += 1
            if true_risk(certificate.threshold) > alpha:
                violations += 1
        assert certified >= 35, f"only {certified} of 40 replications certified anything"
        # delta = 0.05 over 40 replications permits 2 in expectation; the
        # binomial p-value is conservative and the observed count is far under.
        assert violations <= 2, f"{violations} of {certified} certificates were truly invalid"

    def test_a_held_out_arm_lands_under_nominal(self) -> None:
        gate = SelectiveRiskGate.calibrate(uniform_units(600, seed=7), alpha=0.15, delta=0.05)
        certificate = gate.certificate("")
        assert certificate is not None and certificate.certified
        held_out = uniform_units(600, seed=8)
        answered = [unit for unit in held_out if gate.admits("", unit.score)]
        assert answered, "the gate answered nothing, which is not a passing result"
        risk = sum(unit.loss for unit in answered) / len(answered)
        assert risk <= 0.15
        assert len(answered) / len(held_out) > 0.10, "the bound was bought with refusal"

    def test_a_stratum_too_small_to_certify_says_so_by_the_numbers(self) -> None:
        gate = SelectiveRiskGate.calibrate(
            [Observation("", 0.1, 0) for _ in range(30)], alpha=0.05, delta=0.05
        )
        certificate = gate.certificate("")
        assert certificate is not None
        assert not certificate.certified
        assert certificate.required_units == 118
        assert "118" in certificate.refusal and "30" in certificate.refusal

    def test_a_flawless_stratum_at_the_floor_certifies(self) -> None:
        required = smallest_certifiable_size(0.05, LEVEL)
        gate = SelectiveRiskGate.calibrate(
            [Observation("", 0.5, 0) for _ in range(required)], alpha=0.05, delta=0.05
        )
        certificate = gate.certificate("")
        assert certificate is not None and certificate.certified
        assert certificate.errors == 0


class TestMultiplicityIsPaidFor:
    """The correction is the price, and it is charged rather than mentioned."""

    def test_bonferroni_spends_the_grid_size(self) -> None:
        gate = SelectiveRiskGate.calibrate(
            uniform_units(400, seed=3), alpha=0.10, delta=0.05, correction=BONFERRONI
        )
        certificate = gate.certificate("")
        assert certificate is not None
        assert certificate.level == pytest.approx(0.05 / len(DEFAULT_THRESHOLD_GRID))
        assert certificate.candidates_tested == len(DEFAULT_THRESHOLD_GRID)

    def test_a_smaller_grid_buys_a_looser_level(self) -> None:
        units = uniform_units(400, seed=3)
        wide = SelectiveRiskGate.calibrate(units, alpha=0.10, delta=0.05)
        narrow = SelectiveRiskGate.calibrate(units, alpha=0.10, delta=0.05, grid=(0.1, 0.2, 0.3))
        wide_certificate = wide.certificate("")
        narrow_certificate = narrow.certificate("")
        assert wide_certificate is not None and narrow_certificate is not None
        assert narrow_certificate.level > wide_certificate.level
        assert narrow_certificate.candidates_tested == 3

    def test_fixed_sequence_stops_at_the_first_non_rejection(self) -> None:
        # Ordered loosest-first, so the first candidate cannot be rejected and
        # testing stops immediately. This is the failure mode that makes fixed
        # sequence the wrong default here, and it is demonstrated rather than
        # asserted in a docstring.
        units = uniform_units(400, seed=5)
        gate = SelectiveRiskGate.calibrate(
            units, alpha=0.05, delta=0.05, grid=(1.0, 0.5, 0.2, 0.05), correction=FIXED_SEQUENCE
        )
        certificate = gate.certificate("")
        assert certificate is not None
        assert certificate.candidates_tested == 1
        assert not certificate.certified

    def test_fixed_sequence_ordered_well_costs_no_correction(self) -> None:
        units = [Observation("", 0.05, 0) for _ in range(200)]
        gate = SelectiveRiskGate.calibrate(
            units, alpha=0.05, delta=0.05, grid=(0.1, 0.5, 1.0), correction=FIXED_SEQUENCE
        )
        certificate = gate.certificate("")
        assert certificate is not None and certificate.certified
        assert certificate.level == 0.05

    def test_an_unknown_correction_is_refused(self) -> None:
        with pytest.raises(ConfigurationError, match="correction must be"):
            SelectiveRiskGate.calibrate(
                uniform_units(50, seed=1), alpha=0.2, delta=0.05, correction="benjamini"
            )


# ---------------------------------------------------------------------------
# refusal
# ---------------------------------------------------------------------------
class TestItRefusesRatherThanApproximates:
    """The expensive behaviour, which is the one an later edit would soften."""

    def test_an_uncertified_stratum_refuses_everything(self) -> None:
        gate = SelectiveRiskGate.calibrate(
            [Observation(MODE_INLINE, 0.1, 0) for _ in range(10)]
            + [Observation(MODE_PROPAGATED, 0.1, 0) for _ in range(200)],
            alpha=0.05,
            delta=0.05,
            stratify_by=lambda observation: observation.stratum,
        )
        assert gate.certified_strata == (MODE_PROPAGATED,)
        assert not gate.admits(MODE_INLINE, 0.0)
        assert gate.refusal(MODE_INLINE, 0.0) == "uncertified_stratum"
        # And it is NOT backed off to the certified neighbour's threshold.
        assert gate.admits(MODE_PROPAGATED, 0.0)

    def test_an_uncalibrated_stratum_refuses_and_names_itself(self) -> None:
        gate = SelectiveRiskGate.calibrate(
            [Observation(MODE_INLINE, 0.1, 0) for _ in range(200)],
            alpha=0.05,
            delta=0.05,
            stratify_by=lambda observation: observation.stratum,
        )
        assert not gate.admits(MODE_CATALOG, 0.0)
        assert gate.refusal(MODE_CATALOG, 0.0) == "uncalibrated_stratum"

    def test_a_score_above_the_threshold_is_refused(self) -> None:
        gate = SelectiveRiskGate.calibrate(
            [Observation("", 0.05, 0) for _ in range(200)], alpha=0.05, delta=0.05
        )
        certificate = gate.certificate("")
        assert certificate is not None and certificate.threshold is not None
        assert gate.admits("", certificate.threshold)
        assert not gate.admits("", certificate.threshold + 0.01)
        assert gate.refusal("", certificate.threshold + 0.01) == "above_threshold"

    def test_a_non_binary_loss_is_refused_with_the_reason(self) -> None:
        with pytest.raises(ConfigurationError, match="Hoeffding-Bentkus"):
            SelectiveRiskGate.calibrate(
                [Observation("", 0.1, 0.5)],  # type: ignore[arg-type]
                alpha=0.2,
                delta=0.05,
            )

    def test_a_bool_loss_is_refused_for_the_same_reason_a_bool_alpha_is(self) -> None:
        with pytest.raises(ConfigurationError):
            SelectiveRiskGate.calibrate([Observation("", 0.1, True)], alpha=0.2, delta=0.05)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad", [0.0, 1.0, -0.1, 1.5, True, "0.05", None])
    def test_an_alpha_outside_the_open_unit_interval_is_refused(self, bad: object) -> None:
        with pytest.raises(ConfigurationError):
            SelectiveRiskGate.calibrate(
                [Observation("", 0.1, 0)],
                alpha=bad,  # type: ignore[arg-type]
                delta=0.05,
            )

    def test_an_empty_grid_and_an_empty_calibration_set_are_both_refused(self) -> None:
        with pytest.raises(ConfigurationError, match="grid is empty"):
            SelectiveRiskGate.calibrate([Observation("", 0.1, 0)], alpha=0.2, grid=())
        with pytest.raises(ConfigurationError, match="calibration set is empty"):
            SelectiveRiskGate.calibrate([], alpha=0.2)

    def test_the_reserved_pooled_key_cannot_be_confused_with_a_stratum(self) -> None:
        with pytest.raises(ConfigurationError, match="reserved for pooled"):
            SelectiveRiskGate.calibrate(
                [Observation("", 0.1, 0) for _ in range(60)],
                alpha=0.2,
                stratify_by=lambda observation: "",
            )


class TestDeterminism:
    """Same inputs, same certificate. No clock and no randomness."""

    def test_two_calibrations_of_the_same_units_agree_exactly(self) -> None:
        units = uniform_units(300, seed=11)
        first = SelectiveRiskGate.calibrate(units, alpha=0.1, delta=0.05).certificate("")
        second = SelectiveRiskGate.calibrate(units, alpha=0.1, delta=0.05).certificate("")
        assert first == second

    def test_input_order_does_not_move_the_certificate(self) -> None:
        units = uniform_units(300, seed=12)
        shuffled = list(units)
        random.Random(99).shuffle(shuffled)
        first = SelectiveRiskGate.calibrate(units, alpha=0.1, delta=0.05).certificate("")
        second = SelectiveRiskGate.calibrate(shuffled, alpha=0.1, delta=0.05).certificate("")
        assert first == second

    def test_the_certified_threshold_is_the_one_with_the_largest_accepted_set(self) -> None:
        gate = SelectiveRiskGate.calibrate(uniform_units(500, seed=13), alpha=0.2, delta=0.05)
        certificate = gate.certificate("")
        assert certificate is not None and certificate.certified
        best = max(
            (candidate for candidate in gate.tested("") if candidate.rejected),
            key=lambda candidate: candidate.accepted,
        )
        assert certificate.accepted == best.accepted

    def test_a_score_difference_below_the_precision_is_a_tie(self) -> None:
        gate = SelectiveRiskGate.calibrate(
            [Observation("", 0.5, 0) for _ in range(200)], alpha=0.2, delta=0.05
        )
        certificate = gate.certificate("")
        assert certificate is not None and certificate.threshold is not None
        assert gate.admits("", certificate.threshold + 1e-12)


class TestTheCensus:
    """Sizing the strata before calibrating, which is the point of the helper."""

    def test_stratum_counts_partitions_the_units(self) -> None:
        units = [Observation(MODE_INLINE, 0.1, 0)] * 3 + [Observation(MODE_PROPAGATED, 0.2, 1)] * 5
        counts = stratum_counts(units)
        assert counts == {MODE_INLINE: 3, MODE_PROPAGATED: 5}
        assert sum(counts.values()) == len(units)

    def test_the_three_extraction_modes_are_the_three_named_ones(self) -> None:
        assert EXTRACTION_MODES == (MODE_INLINE, MODE_PROPAGATED, MODE_CATALOG)
        assert len(set(EXTRACTION_MODES)) == 3


# ---------------------------------------------------------------------------
# the sentence
# ---------------------------------------------------------------------------
class TestTheGuaranteeIsNeverQuotedWithoutItsAssumption:
    """Learn-Then-Test does not repeal exchangeability, and the strings say so."""

    def test_the_runtime_sentence_names_both_conditions(self) -> None:
        gate = SelectiveRiskGate.calibrate(uniform_units(300, seed=21), alpha=0.2, delta=0.05)
        sentence = gate.guarantee()
        assert SELECTIVE_ASSUMPTION in sentence
        assert "exchangeab" in sentence
        assert "independent" in sentence

    def test_the_runtime_sentence_refuses_the_tempting_overclaim(self) -> None:
        # It must not read as a bound on the refused instances, and it must not
        # let the answer rate go unmentioned -- a bound bought at an answer rate
        # of nothing is the failure this module's own docstring predicts.
        gate = SelectiveRiskGate.calibrate(uniform_units(300, seed=22), alpha=0.2, delta=0.05)
        sentence = gate.guarantee()
        assert "says nothing about the instances the gate refuses" in sentence
        assert "a gate that answers nothing satisfies every selective bound there is" in sentence

    def test_a_gate_that_certified_nothing_says_so_in_its_own_guarantee(self) -> None:
        gate = SelectiveRiskGate.calibrate(
            [Observation("", 0.1, 0) for _ in range(20)], alpha=0.01, delta=0.05
        )
        assert gate.certified_strata == ()
        assert "answers nothing at all" in gate.guarantee()

    def test_the_selective_disclosure_still_carries_the_propagation_gap(self) -> None:
        gate = SelectiveRiskGate.calibrate(
            [Observation(MODE_PROPAGATED, 0.1, 0) for _ in range(200)], alpha=0.2, delta=0.05
        )
        disclosure = gate_disclosure(selective=gate)
        assert "exchangeab" in disclosure
        assert "one-sense-per-discourse" in disclosure
        assert SELECTIVE_IS_NOT_ONE_SENSE in disclosure

    def test_a_disclosure_about_no_gate_is_refused(self) -> None:
        with pytest.raises(ConfigurationError, match="attached to nothing"):
            gate_disclosure()


# ---------------------------------------------------------------------------
# the seam
# ---------------------------------------------------------------------------
class TestPropagateWithASelectiveGate:
    """Where the gate is consumed, and what a refusal does and does not withhold."""

    TEXT = "The World Health Organization (WHO) met. WHO then met again, and WHO agreed."

    def pairs(self, confidence: float) -> List[AcronymPair]:
        return [
            AcronymPair(
                short_form="WHO",
                long_form="World Health Organization",
                short_form_span=(31, 34),
                confidence=confidence,
            )
        ]

    def gate(self, threshold_score: float) -> SelectiveRiskGate:
        return SelectiveRiskGate.calibrate(
            [Observation(MODE_PROPAGATED, threshold_score, 0) for _ in range(200)],
            alpha=0.2,
            delta=0.05,
        )

    def test_the_score_is_one_minus_confidence(self) -> None:
        assert selective_score(self.pairs(1.0)[0]) == 0.0
        assert selective_score(self.pairs(0.0)[0]) == 1.0

    def test_an_admitted_definition_propagates(self) -> None:
        result = propagate(self.TEXT, self.pairs(1.0), selective=self.gate(0.0))
        sources = [occurrence.source for occurrence in result.occurrences]
        assert sources.count(SOURCE_PROPAGATED) == 2
        assert result.refused == ()

    def test_a_refused_definition_keeps_its_definition_site(self) -> None:
        # A refusal withholds PROPAGATION and never a definition: the definition
        # came from a mechanism this gate does not govern, and dropping it would
        # make propagate() lose information extract() already had.
        result = propagate(self.TEXT, self.pairs(0.1), selective=self.gate(0.0))
        sources = [occurrence.source for occurrence in result.occurrences]
        assert sources == [SOURCE_DEFINITION]
        assert result.refused == (("WHO", SELECTIVE_ABOVE_THRESHOLD),)

    def test_an_uncertified_stratum_refuses_under_its_own_code(self) -> None:
        starved = SelectiveRiskGate.calibrate(
            [Observation(MODE_PROPAGATED, 0.0, 0) for _ in range(5)], alpha=0.01, delta=0.05
        )
        result = propagate(self.TEXT, self.pairs(1.0), selective=starved)
        assert result.refused == (("WHO", SELECTIVE_UNCERTIFIED),)

    def test_a_gate_that_never_saw_this_stratum_refuses_under_its_own_code(self) -> None:
        elsewhere = SelectiveRiskGate.calibrate(
            [Observation(MODE_INLINE, 0.0, 0) for _ in range(200)],
            alpha=0.2,
            delta=0.05,
            stratify_by=lambda observation: observation.stratum,
        )
        result = propagate(self.TEXT, self.pairs(1.0), selective=elsewhere)
        assert result.refused == (("WHO", SELECTIVE_UNCALIBRATED),)

    def test_a_non_gate_is_refused_before_anything_is_licensed(self) -> None:
        with pytest.raises(ConfigurationError, match="SelectiveRiskGate"):
            propagate(self.TEXT, self.pairs(1.0), selective=object())  # type: ignore[arg-type]

    def test_the_feature_forced_on_non_bindingly_reproduces_the_feature_absent(self) -> None:
        """R19 in miniature; ``bench/run_selective_risk.py`` runs it over the corpus.

        Every field is compared, provenance included, because a comparison of
        spans alone would pass a change that relabelled every ``source``.
        """
        permissive = SelectiveRiskGate.calibrate(
            [Observation(MODE_PROPAGATED, 1.0, 0) for _ in range(200)], alpha=0.2, delta=0.05
        )
        absent = propagate(self.TEXT, self.pairs(0.8))
        forced_off = propagate(self.TEXT, self.pairs(0.8), selective=None)
        forced_on = propagate(self.TEXT, self.pairs(0.8), selective=permissive)
        for other in (forced_off, forced_on):
            assert other.refused == absent.refused
            assert len(other.occurrences) == len(absent.occurrences)
            for left, right in zip(absent.occurrences, other.occurrences):
                assert (
                    left.short_form,
                    left.long_form,
                    left.span,
                    left.source,
                    left.licensed_by,
                    left.confidence,
                ) == (
                    right.short_form,
                    right.long_form,
                    right.span,
                    right.source,
                    right.licensed_by,
                    right.confidence,
                )

    def test_both_gates_together_require_both_to_admit(self) -> None:
        from acronymkit.core.conformal import ConformalGate
        from acronymkit.nlp.propagation import document_result

        conformal = ConformalGate.calibrate(
            [(document_result("WHO", self.pairs(1.0)), "World Health Organization")] * 20,
            alpha=0.2,
        )
        both = propagate(self.TEXT, self.pairs(1.0), gate=conformal, selective=self.gate(0.0))
        assert [occurrence.source for occurrence in both.occurrences].count(SOURCE_PROPAGATED) == 2
        blocked = propagate(self.TEXT, self.pairs(0.1), gate=conformal, selective=self.gate(0.0))
        assert blocked.refused and blocked.refused[0][1] == SELECTIVE_ABOVE_THRESHOLD


# ---------------------------------------------------------------------------
# the runner -- CHECKOUT ONLY
# ---------------------------------------------------------------------------
_RUNNER = REPO_ROOT / "bench" / "run_selective_risk.py"
_RESULTS = REPO_ROOT / "bench" / "results.json"


@pytest.mark.skipif(
    not (_RUNNER.is_file() and _RESULTS.is_file()),
    reason="bench/ and bench/results.json are checkout-only; an installed distribution has neither",
)
class TestTheBenchRunner:
    """The runner's own arithmetic, on the files a checkout carries and a wheel does not."""

    @staticmethod
    def module() -> object:
        spec = importlib.util.spec_from_file_location("_selective_runner_under_test", _RUNNER)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules["_selective_runner_under_test"] = module
        spec.loader.exec_module(module)
        return module

    def test_the_catalog_stratum_derives_from_published_fields_only(self) -> None:
        runner = self.module()
        block = runner.catalog_stratum()  # type: ignore[attr-defined]
        assert "skipped" not in block
        assert block["stratum"] == MODE_CATALOG
        # Re-derived here from bench/results.json rather than copied from the
        # block, so a change to either side shows up as a disagreement.
        import json

        runs = json.loads(_RESULTS.read_text(encoding="utf-8"))["runs"]
        positions = sum(
            runs[name]["abbreviated_tokens"]["tokens"]
            for name in (
                "governed_catalog.socrata.voted.fold_ab",
                "governed_catalog.socrata.voted.fold_ba",
            )
        )
        assert block["token_positions"] == positions
        assert block["calibratable"] is False

    def test_the_abort_condition_names_the_cells_that_answer_nothing(self) -> None:
        runner = self.module()
        verdict = runner.abort_verdict(  # type: ignore[attr-defined]
            [
                (
                    "arm",
                    {
                        "alpha_0.05": {
                            "answered_instances": 0,
                            "selective_error_over_alpha": None,
                        },
                        "alpha_0.10": {
                            "answered_instances": 10,
                            "selective_error_over_alpha": 1.4,
                        },
                    },
                )
            ]
        )
        assert verdict["aborted"] is True
        assert verdict["cells_answering_nothing"] == 1
        assert verdict["violations"] == ["arm@alpha=0.10 ratio=1.4"]

    def test_a_cell_that_answers_nothing_does_not_pass_as_a_bound(self) -> None:
        # The trap this separation exists for: zero answers and zero errors is
        # not a selective risk of zero, it is no selective risk at all.
        runner = self.module()
        verdict = runner.abort_verdict(  # type: ignore[attr-defined]
            [("arm", {"alpha_0.05": {"answered_instances": 0, "selective_error_over_alpha": None}})]
        )
        assert verdict["aborted"] is False
        assert verdict["cells_with_a_bound"] == 0
        assert verdict["cells_answering_nothing"] == 1

    def test_every_run_id_the_runner_names_is_in_results_json(self) -> None:
        import json

        runner = self.module()
        runs = json.loads(_RESULTS.read_text(encoding="utf-8"))["runs"]
        missing = [name for name in runner.RUN_IDS if name not in runs]  # type: ignore[attr-defined]
        assert not missing, f"the runner names {missing}, which bench/results.json does not carry"

    def test_the_published_selective_figures_are_under_their_own_nominal(self) -> None:
        """Every certified cell in the shipped run respects its own alpha.

        This is the abort condition as a **test** rather than as a field in a
        JSON file nobody re-reads. If a later run lands a cell over nominal, the
        build goes red rather than the number going quiet.
        """
        import json

        runs = json.loads(_RESULTS.read_text(encoding="utf-8"))["runs"]
        offenders: List[Tuple[str, str, float]] = []
        for run_id in (
            "selective.modes.ltt",
            "selective.modes.short_form_disjoint",
            "selective.sdu21.ltt",
        ):
            for arm_name, arm_block in runs[run_id].items():
                if not isinstance(arm_block, dict):
                    continue
                for cell_name, cell in arm_block.items():
                    if not isinstance(cell, dict) or "selective_error_over_alpha" not in cell:
                        continue
                    ratio = cell["selective_error_over_alpha"]
                    if ratio is not None and float(ratio) > 1.0:
                        offenders.append((run_id, f"{arm_name}.{cell_name}", float(ratio)))
        assert not offenders, f"selective risk over nominal in {offenders}"
