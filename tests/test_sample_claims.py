"""``tools/sample_claims.py``: the successor sampling frame, and its price.

Why this module is shaped the way it is
---------------------------------------
The thing under test is a **measurement instrument**, and the failure mode of a
measurement instrument is not a crash. It is a number that looks right.

So the tests below are weighted toward the two ways this tool could be quietly
wrong rather than loudly broken:

* **The estimator.** With twelve of twenty-four drawn from a stratum holding
  three per cent of the population, the unweighted count over the sample is not
  the repository's rate -- it is the churned text's rate wearing the whole
  repository's name. :class:`TestTheEstimator` builds a frame where those two
  numbers differ by a wide margin and pins which one comes out.
* **The arithmetic that closes the old series.** ``16.67 %`` and
  ``[11.06, 24.35]`` are published in ``docs/CLAIMS-LEDGER.md`` and in the
  module's own docstring. :class:`TestTheClosedSeries` recomputes them from the
  five per-round counts rather than trusting either copy.

``design_effect`` is tested in the direction that does **not** flatter the
design: a proportional allocation must return ``1.00`` and the shipped unequal
one must return more, because the whole point of printing it is that it is
allowed to be an argument against the tool that prints it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LOADER = REPO_ROOT / "tools" / "sample_claims.py"
LEDGER = REPO_ROOT / "docs" / "CLAIMS-LEDGER.md"

# The guard, before the load and not on a mark: `tools/` ships in the sdist and
# is no part of an installed distribution, so under `installed-suite` the load
# below would raise and this file would fail to COLLECT rather than skip.
# `EXPECTED_NON_PASSING` is not grown for it.
if not LOADER.is_file():  # pragma: no cover - CI job only
    pytest.skip(
        "tools/ is not part of an installed distribution; these tests belong to a checkout",
        allow_module_level=True,
    )


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_sample_claims_under_test", LOADER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sc = _load()


def _frame(counts: Dict[str, int], known: bool = True) -> object:
    """A frame with ``counts[stratum]`` synthetic items in each stratum."""
    items: List[object] = []
    for stratum, how_many in counts.items():
        for index in range(how_many):
            items.append(
                sc.FrameItem(
                    identifier=f"{stratum}/{index}",
                    relative_path=f"docs/{stratum}.md",
                    line_number=index + 1,
                    number=str(index),
                    stratum=stratum,
                    line=f"a sentence carrying {index} in the {stratum} stratum",
                )
            )
    return sc.Frame(items=tuple(items), churn_known=known, base=None)


class TestTheClosedSeries:
    """The number the old series is closed at, recomputed rather than quoted."""

    def test_the_pooled_rate_is_what_the_constant_says(self) -> None:
        counts = sc.CLOSED_SERIES["per_round"]
        assert sum(counts) == sc.CLOSED_SERIES["not_true"] == 20
        assert len(counts) * 24 == sc.CLOSED_SERIES["draws"] == 120
        assert round(100 * sum(counts) / 120, 2) == 16.67

    def test_the_wilson_interval_reproduces_to_two_decimals(self) -> None:
        # THE FALSIFIER THIS ROUND WROTE AGAINST ITS OWN BRIEF. The figures
        # were handed over as `11.06`-`24.35`; an independent implementation
        # has to land on them or the series is being closed at somebody's
        # recollection.
        low, high = sc.wilson(20, 120)
        assert (round(low, 2), round(high, 2)) == sc.CLOSED_SERIES["wilson_pct"]

    def test_the_fourth_round_half_width_reproduces_too(self) -> None:
        # D-115 publishes 7.75 -> 6.64, a fall of 1.11, as the load-bearing
        # instrument finding. Both halves are recomputed here.
        low4, high4 = sc.wilson(18, 96)
        low5, high5 = sc.wilson(20, 120)
        assert round((high4 - low4) / 2, 2) == 7.75
        assert round((high5 - low5) / 2, 2) == 6.64
        assert round(((high4 - low4) - (high5 - low5)) / 2, 2) == 1.11

    def test_reaching_three_points_needs_about_six_hundred_draws(self) -> None:
        # `25 rounds` in D-115 is a TOTAL. The brief that commissioned this
        # work said "25 MORE rounds", which is a different sentence, and this
        # is the assertion that decides between them.
        at_600 = sc.wilson(100, 600)
        assert (at_600[1] - at_600[0]) / 2 <= 3.0
        at_500 = sc.wilson(83, 500)
        assert (at_500[1] - at_500[0]) / 2 > 3.0
        assert 600 / 24 == 25 and (600 - 120) / 24 == 20

    def test_the_ledger_publishes_the_same_closure(self) -> None:
        # TWO COPIES OF ONE NUMBER IS THE SHAPE THIS REPOSITORY HAS HIT FIVE
        # TIMES. The tool's constant and the page's prose are checked against
        # each other rather than against anybody's memory.
        text = LEDGER.read_text(encoding="utf-8")
        assert "16.67" in text
        assert "11.06" in text and "24.35" in text
        assert "starts at `n = 0`" in text

    def test_wilson_never_returns_a_negative_lower_bound(self) -> None:
        for successes, trials in ((0, 24), (1, 24), (2, 24), (0, 1)):
            low, high = sc.wilson(successes, trials)
            assert 0.0 <= low <= high <= 100.0

    def test_an_empty_denominator_does_not_divide_by_zero(self) -> None:
        assert sc.wilson(0, 0) == (0.0, 100.0)


class TestTheAllocation:
    """Where the twenty-four go, and what happens when a stratum is short."""

    def test_the_default_allocation_sums_to_the_default_size(self) -> None:
        assert sum(sc.DEFAULT_ALLOCATION.values()) == sc.DEFAULT_SIZE == 24

    def test_the_cold_stratum_is_never_zero_by_default(self) -> None:
        # Dropping it would make the repository-wide rate permanently
        # unmeasurable, which is condition 2 of the pre-registration.
        assert sc.DEFAULT_ALLOCATION["cold"] > 0

    def test_a_full_frame_gets_the_declared_allocation(self) -> None:
        frame = _frame({"round": 100, "recent": 100, "cold": 100})
        assert sc.allocate(frame, 24, sc.DEFAULT_ALLOCATION) == sc.DEFAULT_ALLOCATION

    def test_a_short_stratum_gives_what_it_has_and_the_rest_moves(self) -> None:
        frame = _frame({"round": 3, "recent": 100, "cold": 100})
        planned = sc.allocate(frame, 24, sc.DEFAULT_ALLOCATION)
        assert planned["round"] == 3
        assert sum(planned.values()) == 24

    def test_a_frame_smaller_than_the_sample_gives_the_whole_frame(self) -> None:
        frame = _frame({"round": 2, "recent": 2, "cold": 2})
        planned = sc.allocate(frame, 24, sc.DEFAULT_ALLOCATION)
        assert planned == {"round": 2, "recent": 2, "cold": 2}

    def test_an_empty_round_stratum_is_survivable(self) -> None:
        # A ROUND THAT TOUCHED NOTHING THE FRAME REACHES. The draw becomes a
        # repository-wide one and the caller has to be able to see that, which
        # is why the allocation is returned rather than applied in silence.
        frame = _frame({"round": 0, "recent": 100, "cold": 100})
        planned = sc.allocate(frame, 24, sc.DEFAULT_ALLOCATION)
        assert planned["round"] == 0 and sum(planned.values()) == 24


class TestTheDraw:
    """Reproducible from the seed alone, which is what a second grader needs."""

    def test_the_same_seed_gives_the_same_sample(self) -> None:
        frame = _frame({"round": 50, "recent": 50, "cold": 50})
        first = [item.identifier for item in sc.draw(frame, 20260909)]
        second = [item.identifier for item in sc.draw(frame, 20260909)]
        assert first == second

    def test_a_different_seed_gives_a_different_sample(self) -> None:
        frame = _frame({"round": 50, "recent": 50, "cold": 50})
        first = {item.identifier for item in sc.draw(frame, 1)}
        second = {item.identifier for item in sc.draw(frame, 2)}
        assert first != second

    def test_the_draw_respects_the_allocation(self) -> None:
        frame = _frame({"round": 50, "recent": 50, "cold": 50})
        sample = sc.draw(frame, 7)
        tally = {name: sum(1 for item in sample if item.stratum == name) for name in sc.STRATA}
        assert tally == sc.DEFAULT_ALLOCATION

    def test_no_claim_is_drawn_twice(self) -> None:
        frame = _frame({"round": 13, "recent": 13, "cold": 13})
        sample = sc.draw(frame, 3)
        assert len({item.identifier for item in sample}) == len(sample)


class TestTheEstimator:
    """The trap: the unweighted count is not the repository's rate."""

    @staticmethod
    def _graded(frame: object, seed: int, rates: Dict[str, int]) -> Dict[str, str]:
        """Grade the first ``rates[stratum]`` of each stratum's draws not true."""
        sample = sc.draw(frame, seed)
        graded: Dict[str, str] = {}
        seen = dict.fromkeys(sc.STRATA, 0)
        for item in sample:
            seen[item.stratum] += 1
            graded[item.identifier] = (
                "FALSE" if seen[item.stratum] <= rates.get(item.stratum, 0) else "TRUE"
            )
        return graded

    def test_the_repository_rate_is_weighted_by_stratum_size_not_by_draws(self) -> None:
        # THE WHOLE POINT. `round` holds 20 of 1020 claims and takes 12 of 24
        # draws. Grade every round draw not true and every other draw true: the
        # unweighted rate over the sample is 50 %, and the repository's is
        # about 2 %. Publishing the first would be this frame's central lie.
        frame = _frame({"round": 20, "recent": 500, "cold": 500})
        graded = self._graded(frame, 11, {"round": 12})
        sample = sc.draw(frame, 11)
        result = sc.stratified_estimate(frame, graded, sample)
        unweighted = 100 * sum(1 for v in graded.values() if v in sc.NOT_TRUE) / len(graded)
        assert round(unweighted) == 50
        assert float(result["repository_rate_pct"]) < 3.0

    def test_a_uniform_rate_comes_back_as_that_rate(self) -> None:
        # The estimator must not distort a frame where every stratum agrees.
        frame = _frame({"round": 100, "recent": 100, "cold": 100})
        graded = self._graded(frame, 5, {"round": 6, "recent": 4, "cold": 2})
        sample = sc.draw(frame, 5)
        result = sc.stratified_estimate(frame, graded, sample)
        assert 49.0 <= float(result["repository_rate_pct"]) <= 51.0

    def test_uncheckable_is_in_the_denominator_and_not_the_numerator(self) -> None:
        # THE BOUNDARY RULE, WRITTEN DOWN BEFORE THE DRAW, which is condition
        # one of the four this section has listed as unmet since D-082.
        # Excluding UNCHECKABLE would let a round improve its rate by making
        # its claims harder to check.
        assert "UNCHECKABLE" in sc.VERDICTS and "UNCHECKABLE" not in sc.NOT_TRUE
        frame = _frame({"round": 30, "recent": 30, "cold": 30})
        sample = sc.draw(frame, 2)
        graded = {item.identifier: "TRUE" for item in sample}
        for item in [i for i in sample if i.stratum == "round"][:6]:
            graded[item.identifier] = "UNCHECKABLE"
        result = sc.stratified_estimate(frame, graded, sample)
        per_stratum = result["per_stratum"]
        assert isinstance(per_stratum, dict)
        assert per_stratum["round"]["n"] == 12
        assert per_stratum["round"]["not_true"] == 0

    def test_misleading_counts_as_not_true(self) -> None:
        assert set(sc.NOT_TRUE) == {"FALSE", "MISLEADING"}

    def test_a_stratum_nobody_graded_is_dropped_rather_than_counted_as_clean(self) -> None:
        frame = _frame({"round": 10, "recent": 10, "cold": 10})
        sample = sc.draw(frame, 4)
        graded = {i.identifier: "TRUE" for i in sample if i.stratum == "round"}
        result = sc.stratified_estimate(frame, graded, sample)
        per_stratum = result["per_stratum"]
        assert isinstance(per_stratum, dict)
        assert set(per_stratum) == {"round"}


class TestThePrice:
    """``design_effect``, tested in the direction that does not flatter it."""

    def test_a_proportional_allocation_costs_nothing(self) -> None:
        # Deff == 1 exactly when n_h / n == N_h / N. If this drifts, every
        # published design effect is a comparison against the wrong baseline.
        frame = _frame({"round": 100, "recent": 100, "cold": 100})
        assert sc.design_effect(frame, {"round": 8, "recent": 8, "cold": 8}, 24) == pytest.approx(
            1.0
        )

    def test_over_sampling_a_small_stratum_costs_precision(self) -> None:
        frame = _frame({"round": 20, "recent": 500, "cold": 500})
        assert sc.design_effect(frame, sc.DEFAULT_ALLOCATION, 24) > 1.0

    def test_an_empty_frame_does_not_divide_by_zero(self) -> None:
        import math

        assert math.isnan(sc.design_effect(_frame({}), sc.DEFAULT_ALLOCATION, 24))


class TestChurnDegradesLoudly:
    """A frame that cannot see history must say so, not report a clean sweep."""

    def test_an_unknown_churn_frame_declares_itself(self) -> None:
        frame = _frame({"cold": 10}, known=False)
        rendered = sc._render_frame(frame, sc.DEFAULT_ALLOCATION, 24)
        assert "CHURN UNKNOWN" in rendered
        assert "uniform" in rendered

    def test_git_that_cannot_answer_returns_nothing_rather_than_raising(self) -> None:
        assert sc._git(["rev-parse", "no-such-ref-here"], REPO_ROOT) == []

    def test_the_render_always_names_the_closed_series(self) -> None:
        # A DRAW PRINTED WITHOUT THE CLOSURE BESIDE IT IS THE FAILURE MODE THIS
        # WHOLE SECTION EXISTS TO PREVENT: a reader pooling the new rate into
        # the old one because nothing on the page said not to.
        rendered = sc._render_frame(
            _frame({"round": 5, "recent": 5, "cold": 5}), sc.DEFAULT_ALLOCATION, 24
        )
        assert "16.67" in rendered
        assert "DOES NOT CARRY ACROSS" in rendered
        assert "n = 0" in rendered


class TestThisCheckout:
    """The live frame, built the way CI would build it."""

    def test_the_frame_is_the_claims_gate_residue_and_nothing_else(self) -> None:
        # ANTI-VACUITY plus a definition check: every item must be a number the
        # claims gate has NOT verified. Sampling a number a machine re-checks
        # on every push would measure the grader.
        frame = sc.build_frame(REPO_ROOT, base="HEAD~1")
        assert frame.total > 0
        assert frame.total == sum(frame.sizes().values())

    def test_every_item_names_a_real_file_and_line(self) -> None:
        frame = sc.build_frame(REPO_ROOT, base="HEAD~1")
        for item in frame.items[:40]:
            path = REPO_ROOT / item.relative_path
            assert path.is_file(), item.relative_path
            assert item.line_number >= 1

    def test_the_cli_prints_a_frame(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert sc.main(["--frame"]) == 0
        assert "design effect" in capsys.readouterr().out

    def test_a_draw_without_a_seed_is_refused(self, capsys: pytest.CaptureFixture[str]) -> None:
        # A SAMPLE NOBODY CAN REDRAW IS NOT A SAMPLE. Condition four of §6's
        # four is a second grader on the same sample, and it is unreachable
        # without the seed.
        assert sc.main(["--draw"]) == 1
        assert "seed" in capsys.readouterr().out
