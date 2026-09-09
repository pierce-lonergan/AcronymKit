"""Tests for :mod:`acronymkit.conformal`.

Three of these are not ordinary unit tests and are the reason this file exists
in the shape it does:

* :func:`test_finite_sample_coverage_is_exact_on_synthetic_exchangeable_data`
  checks the *theorem*, not the code's opinion of itself: coverage on data that
  is exchangeable by construction must land inside
  ``[1 - alpha, 1 - alpha + 1/(n+1)]``. A conformal implementation that is wrong
  passes every reason-code test and fails this one.
* :func:`test_every_paragraph_stating_the_guarantee_names_exchangeability`
  is the mechanism behind the third deliverable of this workstream. A guarantee
  quoted without its assumption is the overclaim this subsystem exists not to
  make, and prose is exactly what no other gate in this repository can read.
* :func:`test_forcing_the_feature_off_is_identical_to_not_having_it` is R19 at
  unit scale; ``bench/run_conformal.py`` runs the corpus-scale version.
"""

from __future__ import annotations

import doctest
import random
import re
from pathlib import Path
from typing import List, Tuple

import pytest

from acronymkit import conformal
from acronymkit.config import Config
from acronymkit.conformal import (
    ASSUMPTION,
    ConformalGate,
    arity_group,
    group_counts,
    nonconformity,
    smallest_calibration_size,
)
from acronymkit.core import conformal as core_conformal
from acronymkit.disambiguation import ExpansionDictionary, LexicalDisambiguator
from acronymkit.enums import EngineTier
from acronymkit.exceptions import ConfigurationError
from acronymkit.models import DisambiguationCandidate, DisambiguationResult, EngineMetadata

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Phrases that assert a distribution-free guarantee. Any paragraph containing
#: one must also name the assumption; see the test at the bottom of this file.
GUARANTEE_MARKERS = ("distribution-free", "probability at least", "coverage guarantee")

#: Files whose prose is held to that rule. Source and documentation alike: the
#: defect this guards against is a sentence, and a sentence in a docstring
#: reaches a reader through ``help()`` exactly as one in Markdown reaches them
#: through a browser.
#:
#: **``src/acronymkit/conformal.py`` is now a compatibility shim and passes this
#: rule VACUOUSLY**, and the entry is kept rather than dropped. The definitions
#: moved to ``src/acronymkit/core/conformal.py`` when the package was split at
#: the lexer contract seam; that path is listed first and is where every
#: guarantee sentence in this package's source now lives. The shim is listed
#: second because a future edit could put a guarantee sentence on the
#: compatibility page -- but a reader should know that of the five cases below,
#: exactly one contributes no offender because it contains no prose to offend,
#: which is the shape D-110 named: a green parametrised case that is
#: indistinguishable from a file being correct.
GUARANTEE_FILES = (
    "src/acronymkit/core/conformal.py",
    "src/acronymkit/conformal.py",
    "src/acronymkit/disambiguation.py",
    "bench/run_conformal.py",
    "docs/EVALUATION.md",
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def result_with(scores: List[float]) -> DisambiguationResult:
    """Build a result carrying exactly ``scores``, highest first.

    Constructed rather than produced by the disambiguator so that the score
    distribution is under the test's control; the conformal machinery reads
    nothing else off a result.

    Args:
        scores: Candidate scores, any order.

    Returns:
        A result whose candidates are sorted the way the library sorts them.
    """
    candidates = [
        DisambiguationCandidate(expansion=f"e{index}", score=score, source="dictionary")
        for index, score in enumerate(scores)
    ]
    candidates.sort(key=lambda candidate: (-candidate.score, candidate.expansion))
    return DisambiguationResult(
        acronym="XX",
        context="",
        primary_expansion=candidates[0].expansion if candidates else None,
        candidates=candidates,
        metadata=EngineMetadata(
            engine_tier=EngineTier.ZERO_DEPENDENCY, execution_time_ms=0.0, tokens_processed=0
        ),
    )


def synthetic_corpus(count: int, seed: int) -> List[Tuple[DisambiguationResult, str]]:
    """Labelled instances drawn i.i.d., so exchangeability holds by construction.

    Args:
        count: How many instances.
        seed: Frozen seed.

    Returns:
        ``(result, gold)`` pairs.
    """
    rng = random.Random(seed)
    pairs: List[Tuple[DisambiguationResult, str]] = []
    for _ in range(count):
        arity = rng.choice([2, 3, 4, 5])
        scores = [round(rng.random(), 6) for _ in range(arity)]
        result = result_with(scores)
        gold = rng.choice([candidate.expansion for candidate in result.candidates])
        pairs.append((result, gold))
    return pairs


def paragraphs(text: str) -> List[str]:
    """Split ``text`` into blank-line-separated paragraphs."""
    return [block for block in re.split(r"\n\s*\n", text) if block.strip()]


# ---------------------------------------------------------------------------
# the arithmetic
# ---------------------------------------------------------------------------
class TestTheQuantile:
    """The order statistic, which is the whole of the method."""

    @pytest.mark.parametrize(
        ("alpha", "expected"), [(0.5, 1), (0.1, 9), (0.05, 19), (0.01, 99), (0.2, 4)]
    )
    def test_smallest_calibration_size(self, alpha: float, expected: int) -> None:
        assert smallest_calibration_size(alpha) == expected

    @pytest.mark.parametrize(
        ("count", "alpha", "rank"),
        [
            (9, 0.1, 9),  # ceil(10 * 0.90) = 9, the largest
            (10, 0.1, 10),  # ceil(11 * 0.90) = 10; ceil(10 * 0.90) would be 9
            (10, 0.2, 9),  # ceil(11 * 0.80) = 9;  ceil(10 * 0.80) would be 8
            (19, 0.05, 19),
            (99, 0.01, 99),
            (200, 0.3, 141),  # ceil(201 * 0.70) = 141; the n+1 is load-bearing here
        ],
    )
    def test_the_threshold_is_the_named_order_statistic(
        self, count: int, alpha: float, rank: int
    ) -> None:
        """``ceil((n + 1) * (1 - alpha))``, one-based, pinned at sizes where the
        ``+ 1`` changes the answer.

        The first version of this test used only ``n = 9`` at ``alpha = 0.1``,
        where dropping the ``+ 1`` gives the same rank -- so a mutation that
        deleted it went green here and green through a 2,000-instance coverage
        check, where a one-place shift in an order statistic is invisible. The
        cases above are chosen so that the two formulas disagree.
        """
        pairs = [(result_with([1.0, 0.0]), "e0") for _ in range(count)]
        gate = ConformalGate.calibrate(pairs, alpha=alpha)
        (group,) = gate.groups
        assert (group.count, group.rank) == (count, rank)

    def test_the_threshold_is_the_value_at_that_rank(self) -> None:
        """The threshold is the order statistic itself, not an interpolation."""
        pairs = [(result_with([1.0 - step / 100.0, step / 100.0]), "e0") for step in range(1, 21)]
        gate = ConformalGate.calibrate(pairs, alpha=0.2)
        (group,) = gate.groups
        scores = sorted(round(1.0 - (1.0 - step / 100.0), 9) for step in range(1, 21))
        assert group.rank == 17
        assert group.threshold == pytest.approx(scores[16])

    def test_a_calibration_set_too_small_for_alpha_is_refused(self) -> None:
        pairs = [(result_with([1.0, 0.0]), "e0") for _ in range(8)]
        with pytest.raises(ConfigurationError) as caught:
            ConformalGate.calibrate(pairs, alpha=0.1)
        assert "at least 9 calibration instance(s)" in str(caught.value)

    def test_an_empty_calibration_set_is_refused(self) -> None:
        with pytest.raises(ConfigurationError, match="calibration set is empty"):
            ConformalGate.calibrate([], alpha=0.1)

    @pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.5, True, "0.1", None])
    def test_alpha_is_validated(self, alpha: object) -> None:
        pairs = [(result_with([1.0, 0.0]), "e0") for _ in range(99)]
        with pytest.raises(ConfigurationError):
            ConformalGate.calibrate(pairs, alpha=alpha)  # type: ignore[arg-type]

    def test_a_gold_no_candidate_carries_is_scored_infinite_and_counted(self) -> None:
        pairs = [(result_with([1.0, 0.0]), "not-a-candidate") for _ in range(19)]
        gate = ConformalGate.calibrate(pairs, alpha=0.05)
        (group,) = gate.groups
        assert group.uncovered == 19
        # Every calibration score is infinite, so the threshold is too and every
        # candidate is admitted: the gate degrades to refusing on ambiguity
        # rather than to answering confidently.
        assert gate.decide(result_with([1.0, 0.0])).reason == "ambiguous"


class TestTheScore:
    """The nonconformity function."""

    def test_it_is_one_minus_the_normalised_share(self) -> None:
        scored = nonconformity(result_with([0.6, 0.4]))
        assert scored == (("e0", 0.4), ("e1", 0.6))

    def test_all_zero_scores_fall_back_to_uniform(self) -> None:
        scored = nonconformity(result_with([0.0, 0.0, 0.0]))
        assert [round(score, 6) for _, score in scored] == [0.666667] * 3

    def test_no_candidates_scores_nothing(self) -> None:
        assert nonconformity(result_with([])) == ()

    def test_the_ordering_matches_the_library_candidate_ordering(self) -> None:
        result = result_with([0.1, 0.9, 0.5])
        scored = nonconformity(result)
        assert [name for name, _ in scored] == [c.expansion for c in result.candidates]


# ---------------------------------------------------------------------------
# the theorem
# ---------------------------------------------------------------------------
class TestCoverage:
    """What the guarantee actually promises, checked against a construction."""

    @pytest.mark.parametrize("alpha", [0.05, 0.1, 0.2, 0.4])
    def test_finite_sample_coverage_is_exact_on_synthetic_exchangeable_data(
        self, alpha: float
    ) -> None:
        """Coverage must land in ``[1 - alpha, 1 - alpha + 1/(n+1)]``.

        Split conformal's guarantee is two-sided on exchangeable data, and the
        upper half is the one that catches an implementation that is merely
        conservative -- a gate that admits every candidate covers everything and
        satisfies the lower bound while being worthless.
        """
        pairs = synthetic_corpus(4000, seed=7)
        calibration, evaluation = pairs[:2000], pairs[2000:]
        gate = ConformalGate.calibrate(calibration, alpha=alpha)
        covered = sum(1 for result, gold in evaluation if gold in gate.prediction_set(result))
        empirical = covered / len(evaluation)
        slack = 1.0 / (len(calibration) + 1)
        # A finite evaluation set adds sampling noise on top of the theorem's
        # own interval; three standard errors of a Bernoulli at this n is under
        # two points, and the interval is widened by exactly that rather than by
        # whatever made the test pass.
        noise = 3.0 * (alpha * (1 - alpha) / len(evaluation)) ** 0.5
        assert (1 - alpha) - noise <= empirical <= (1 - alpha) + slack + noise

    def test_mondrian_gives_each_group_its_own_threshold(self) -> None:
        pairs = synthetic_corpus(4000, seed=11)
        gate = ConformalGate.calibrate(pairs, alpha=0.1, group_by=arity_group)
        keys = {group.key for group in gate.groups}
        assert keys == {"2", "3", "4", "5"}
        thresholds = {group.threshold for group in gate.groups}
        assert len(thresholds) == len(keys), "one threshold per group, and they differ"

    def test_a_group_too_small_for_alpha_is_refused_by_name(self) -> None:
        pairs = [(result_with([0.9, 0.1]), "e0") for _ in range(99)]
        pairs += [(result_with([0.9, 0.1, 0.05]), "e0") for _ in range(3)]
        with pytest.raises(ConfigurationError) as caught:
            ConformalGate.calibrate(pairs, alpha=0.05, group_by=arity_group)
        assert "3=3" in str(caught.value)

    def test_group_counts_answers_the_question_before_calibrate_raises(self) -> None:
        pairs = [(result_with([0.9, 0.1]), "e0") for _ in range(4)]
        pairs += [(result_with([0.9, 0.1, 0.05]), "e0") for _ in range(2)]
        assert dict(group_counts(pairs, arity_group)) == {"2": 4, "3": 2}


# ---------------------------------------------------------------------------
# the decision
# ---------------------------------------------------------------------------
class TestTheDecision:
    """Answer, or refuse, and say which refusal this is."""

    @staticmethod
    def gate(alpha: float = 0.2) -> ConformalGate:
        pairs = synthetic_corpus(400, seed=3)
        return ConformalGate.calibrate(pairs, alpha=alpha)

    def test_a_singleton_set_is_answered(self) -> None:
        decision = self.gate().decide(result_with([0.99, 0.001]))
        assert (decision.reason, decision.abstained) == ("answered", False)
        assert decision.expansion == "e0"

    def test_a_flat_result_is_refused_as_ambiguous(self) -> None:
        decision = self.gate().decide(result_with([0.5, 0.5, 0.5]))
        assert decision.reason == "ambiguous"
        assert decision.expansion is None
        assert len(decision.prediction_set) >= 2

    def test_no_candidates_is_a_different_refusal_from_ambiguity(self) -> None:
        decision = self.gate().decide(result_with([]))
        assert decision.reason == "no_candidates"
        assert decision.prediction_set == ()

    def test_a_threshold_below_every_candidate_refuses_with_an_empty_set(self) -> None:
        # Calibrating on results whose gold is always the runaway winner drives
        # the threshold to the bottom, so a flat result admits nobody.
        pairs = [(result_with([1.0, 0.0, 0.0, 0.0]), "e0") for _ in range(19)]
        gate = ConformalGate.calibrate(pairs, alpha=0.05)
        decision = gate.decide(result_with([0.25, 0.25, 0.25, 0.25]))
        assert decision.reason == "no_plausible_candidate"
        assert decision.prediction_set == ()

    def test_an_uncalibrated_group_is_refused_and_never_fitted_to_a_neighbour(self) -> None:
        pairs = [(result_with([0.9, 0.1]), "e0") for _ in range(99)]
        gate = ConformalGate.calibrate(pairs, alpha=0.05, group_by=arity_group)
        decision = gate.decide(result_with([0.5, 0.3, 0.2]))
        assert decision.reason == "uncalibrated_group"
        assert (decision.expansion, decision.threshold) == (None, None)

    def test_calibration_is_deterministic(self) -> None:
        pairs = synthetic_corpus(500, seed=5)
        first = ConformalGate.calibrate(pairs, alpha=0.1)
        second = ConformalGate.calibrate(list(reversed(pairs)), alpha=0.1)
        assert [group.threshold for group in first.groups] == [
            group.threshold for group in second.groups
        ]


class TestTheGateObject:
    """Construction invariants that keep a threshold from being re-pointed."""

    def test_a_marginal_gate_needs_the_reserved_key(self) -> None:
        group = conformal.GroupCalibration(key="2", count=9, threshold=0.5, rank=9, uncovered=0)
        with pytest.raises(ConfigurationError, match="exactly one group keyed"):
            ConformalGate(alpha=0.1, groups=[group])

    def test_a_grouped_gate_may_not_use_the_reserved_key(self) -> None:
        group = conformal.GroupCalibration(key="", count=9, threshold=0.5, rank=9, uncovered=0)
        with pytest.raises(ConfigurationError, match="reserved for marginal"):
            ConformalGate(alpha=0.1, groups=[group], group_by=arity_group)

    def test_duplicate_group_keys_are_refused(self) -> None:
        group = conformal.GroupCalibration(key="2", count=9, threshold=0.5, rank=9, uncovered=0)
        with pytest.raises(ConfigurationError, match="duplicate group key"):
            ConformalGate(alpha=0.1, groups=[group, group], group_by=arity_group)

    def test_no_groups_at_all_is_refused(self) -> None:
        with pytest.raises(ConfigurationError, match="at least one calibrated group"):
            ConformalGate(alpha=0.1, groups=[])


# ---------------------------------------------------------------------------
# wiring into the disambiguator
# ---------------------------------------------------------------------------
class TestTheDisambiguatorSeam:
    """The feature is off until a caller builds a gate, and off means absent."""

    @staticmethod
    def index() -> ExpansionDictionary:
        return ExpansionDictionary(
            {"BP": ["blood pressure", "boiling point", "British Petroleum"], "MS": ["multiple"]}
        )

    def test_the_default_is_off(self) -> None:
        engine = LexicalDisambiguator(Config(), self.index())
        assert engine.calibration is None
        assert engine.disambiguate("BP", "Nothing here.").primary_expansion is not None

    def test_forcing_the_feature_off_is_identical_to_not_having_it(self) -> None:
        contexts = [
            "Blood pressure (BP) was elevated.",
            "The reading was taken twice.",
            "British Petroleum reported a loss.",
            "",
            "The boiling point of the solvent.",
        ]
        absent = LexicalDisambiguator(Config(), self.index())
        forced_off = LexicalDisambiguator(Config(), self.index(), calibration=None)
        for context in contexts:
            left = absent.disambiguate("BP", context).model_dump(mode="json")
            right = forced_off.disambiguate("BP", context).model_dump(mode="json")
            left["metadata"].pop("execution_time_ms")
            right["metadata"].pop("execution_time_ms")
            assert left == right

    def test_a_calibrated_gate_can_withhold_an_answer(self) -> None:
        engine = LexicalDisambiguator(Config(), self.index())
        labelled = [
            (engine.disambiguate("BP", "Blood pressure was elevated."), "blood pressure")
            for _ in range(19)
        ]
        gate = ConformalGate.calibrate(labelled, alpha=0.05)
        picky = LexicalDisambiguator(Config(), self.index(), calibration=gate)
        refused = picky.disambiguate("BP", "The reading was taken twice.")
        assert refused.primary_expansion is None
        assert refused.abstained is True
        assert len(refused.candidates) == 3, "the refused candidates stay visible"

    def test_the_two_refusal_policies_may_not_be_composed(self) -> None:
        engine = LexicalDisambiguator(Config(), self.index())
        labelled = [
            (engine.disambiguate("BP", "Blood pressure was elevated."), "blood pressure")
            for _ in range(19)
        ]
        gate = ConformalGate.calibrate(labelled, alpha=0.05)
        with pytest.raises(ConfigurationError, match="two refusal policies"):
            LexicalDisambiguator(Config(), self.index(), min_margin=0.1, calibration=gate)


# ---------------------------------------------------------------------------
# the sentence
# ---------------------------------------------------------------------------
class TestTheGuaranteeIsNeverQuotedWithoutItsAssumption:
    """The third deliverable, as a check rather than a promise."""

    def test_the_runtime_sentence_names_the_assumption(self) -> None:
        pairs = synthetic_corpus(200, seed=13)
        sentence = ConformalGate.calibrate(pairs, alpha=0.1).guarantee()
        assert ASSUMPTION in sentence
        assert "exchangeab" in sentence

    def test_the_runtime_sentence_refuses_the_tempting_overclaim(self) -> None:
        """The disclaimer is pinned as a contiguous clause, not as two loose words.

        The first version asserted ``"does NOT bound the error rate"`` and
        ``"among answered instances"`` separately, and a mutation that changed
        the clause between them to *"among answered instances too, which is the
        same quantity"* -- reinstating the exact overclaim this module exists to
        avoid -- passed both. It is pinned whole here.
        """
        pairs = synthetic_corpus(200, seed=13)
        sentence = ConformalGate.calibrate(pairs, alpha=0.1).guarantee()
        assert "does NOT bound the error rate among answered instances" in sentence
        assert "which is that divided by the answer rate and is larger" in sentence

    @pytest.mark.parametrize("relative", GUARANTEE_FILES)
    def test_every_paragraph_stating_the_guarantee_names_exchangeability(
        self, relative: str
    ) -> None:
        """No paragraph may assert the guarantee without its assumption.

        This is the only rule in this repository that reads prose, and it reads
        it in the crudest way that can fail: a paragraph containing
        ``distribution-free``, ``probability at least`` or ``coverage
        guarantee`` must also contain ``exchangeab``. It cannot tell a good
        sentence from a bad one. It can tell a guarantee standing on its own,
        which is the defect that matters.
        """
        path = REPO_ROOT / relative
        if not path.is_file():  # pragma: no cover - tree guard
            pytest.skip(f"{relative} is not in this tree")
        offenders = [
            block
            for block in paragraphs(path.read_text(encoding="utf-8"))
            if any(marker in block for marker in GUARANTEE_MARKERS) and "exchangeab" not in block
        ]
        assert not offenders, (
            f"{relative}: {len(offenders)} paragraph(s) assert a distribution-free guarantee "
            f"with no exchangeability assumption in the same paragraph. First:\n"
            f"{offenders[0][:400]}"
        )


def test_module_doctests_pass() -> None:
    """Every example in the module runs, because an example nobody runs rots.

    Aimed at ``acronymkit.core.conformal``, the defining module. It used to be
    aimed at ``acronymkit.conformal``, and when that path became a
    compatibility shim this assertion is what caught it: a shim carries no
    ``>>>`` line, so ``attempted`` fell to zero while ``failed`` stayed at
    zero. **A doctest suite that collects nothing reports success**, and the
    only reason this did not pass silently is that somebody wrote the
    ``attempted > 0`` line when there was nothing wrong.
    """
    results = doctest.testmod(core_conformal, verbose=False, report=False)
    assert results.failed == 0, f"{results.failed} doctest failure(s)"
    assert results.attempted > 0, "no doctests collected"


def test_the_compatibility_path_re_exports_the_same_objects() -> None:
    """``acronymkit.conformal`` must BE the core objects, not copies of them.

    Identity rather than equality, and the reason is specific to this module: a
    caller who calibrates a gate through one path and asks it a question
    through the other must be talking about one class, or the guarantee they
    were given describes a different object than the one deciding. A shim that
    rebound the names to fresh classes would satisfy every equality assertion
    in this file and fail at exactly that moment.
    """
    for name in conformal.__all__:
        assert getattr(conformal, name) is getattr(core_conformal, name), name
    assert conformal.__all__ == core_conformal.__all__
