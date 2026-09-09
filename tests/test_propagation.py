"""Tests for :mod:`acronymkit.propagation` -- A2, document-scoped propagation.

Three groups, and the third is the one this round exists for:

* :class:`TestTheRule` -- the four clauses of the measured rule, one test each,
  each written so that dropping the clause turns it red.
* :class:`TestTheGate` -- every :class:`~acronymkit.conformal.ConformalDecision`
  outcome reaching :func:`~acronymkit.propagation.propagate`, plus the one
  refusal this module adds on top of them.
* :class:`TestTheClaim` -- a prose rule over the surfaces that describe the gate
  to a caller. ``docs/DECISIONS.md`` D-104 found that split conformal's bound is
  **joint** and that the selective reading is out by a measured factor of four;
  shipping propagation under the selective reading would reproduce that defect
  in a new subsystem with a fresh audience. The rule is crude, it is stated to
  be crude, and it is the same instrument D-104 shipped one page earlier.
"""

from __future__ import annotations

import dataclasses
import doctest
import json
import re
from pathlib import Path
from typing import List

import pytest

from acronymkit import propagation
from acronymkit.config import Config
from acronymkit.conformal import ConformalGate
from acronymkit.enums import EngineTier
from acronymkit.exceptions import ConfigurationError
from acronymkit.extractor import AbbreviationExtractor
from acronymkit.models import (
    AcronymPair,
    DisambiguationCandidate,
    DisambiguationResult,
    EngineMetadata,
)
from acronymkit.propagation import (
    GATE_AMBIGUOUS,
    GATE_DISAGREED,
    GATE_NO_CANDIDATES,
    GATE_UNCALIBRATED_GROUP,
    JOINT_NOT_SELECTIVE,
    NOT_TERM_SHAPED,
    PROPAGATION_GAP,
    SOURCE_DEFINITION,
    SOURCE_PROPAGATED,
    Occurrence,
    document_result,
    gate_disclosure,
    propagate,
    term_shaped,
    whole_token_occurrences,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Files whose prose describes the gate to a caller and is held to the rule at
#: the bottom of this file. A docstring reaches a reader through ``help()``
#: exactly as Markdown reaches them through a browser, so both are in.
CLAIM_FILES = (
    "src/acronymkit/propagation.py",
    "docs/EVALUATION.md",
    "README.md",
    "CHANGELOG.md",
)

#: A paragraph asserting a bound. Deliberately wider than the phrases a bound is
#: usually written in, because the failure this guards is a *loose* sentence and
#: not a precise wrong one.
BOUND_MARKERS = ("alpha", "at most", "bounds the", "bounded by", "guarantee")

#: Phrases that assert the selective reading outright. A blocklist is evadable by
#: rewording and is not the primary instrument; it is here because these exact
#: sentences are the ones a reader would write, and it costs nothing.
FORBIDDEN_PHRASES = (
    "bounds the error rate among",
    "bounds the selective error",
    "at most alpha of the propagated",
    "at most alpha of propagated",
    "of propagated occurrences are wrong",
    "which is the same quantity",
)

#: A sentence subject that is the *selective* rate. Naming it is fine; naming it
#: without saying it is bigger than the bound is the overclaim.
SELECTIVE_SUBJECTS = (
    "error rate among",
    "rate among answers",
    "among the answers",
    "among answered",
    "among answers",
    "among the instances it answers",
    "among the gate's answers",
    "selective error",
)

#: What makes naming it honest: the sentence has to deny it is bounded, or say
#: how much bigger it is. Crude, and the crudeness is the point -- a positive
#: rule that can be satisfied by any nearby word is what went inert in D-104.
DISCLAIMERS = ("not", "never", "larger", "greater", "times", "divided by", "no bound")

#: Sentences of ``src/acronymkit/propagation.py`` that carry the disclosure, and
#: that must appear EXACTLY ONCE each. This is the ``expect_failure_matching``
#: move ``docs/GATES.md`` argues for, applied to prose: a presence rule over a
#: common word is satisfiable by an unrelated mention elsewhere in the paragraph,
#: which is exactly how two of D-104's ten mutations came back green. Pinning the
#: fragment makes a rewrite deliberate rather than accidental.
REQUIRED_FRAGMENTS = (
    "*joint* rate of answering and being wrong",
    "it does not bound the share of the",
)

#: The same rule over the two constants, checked as **values** rather than as
#: source text: they are written as adjacent string literals, so the source
#: carries quote characters the value does not.
REQUIRED_IN_CONSTANTS = (
    (JOINT_NOT_SELECTIVE, "It does not bound the error rate among the instances it answers"),
    (JOINT_NOT_SELECTIVE, "risk-controlled selective classification"),
    (PROPAGATION_GAP, "which no conformal argument bounds at all"),
)


def sentences(text: str) -> List[str]:
    """Whitespace-normalised sentences, split on terminal punctuation.

    A part containing ``|`` is dropped: a Markdown table row is a row of labelled
    cells and not a sentence, and ``docs/EVALUATION.md`` publishes the joint and
    selective rates as adjacent *columns* -- which is the clearest possible
    presentation of the distinction and would read as an offender here.
    """
    flat = " ".join(text.split())
    parts = re.split(r"(?<=[.;:])\s+", flat)
    return [part for part in parts if part.strip() and "|" not in part]


def paragraphs(text: str) -> List[str]:
    """Split ``text`` into blank-line-separated paragraphs."""
    return [block for block in re.split(r"\n\s*\n", text) if block.strip()]


def pair(short: str, long_form: str, at: int, confidence: float = 1.0) -> AcronymPair:
    """An ``AcronymPair`` whose short-form span really holds ``short``."""
    return AcronymPair(
        short_form=short,
        long_form=long_form,
        short_form_span=(at, at + len(short)),
        confidence=confidence,
    )


def result_with(acronym: str, scored: List[tuple]) -> DisambiguationResult:
    """A result carrying exactly ``(expansion, score)``, for calibration."""
    return DisambiguationResult(
        acronym=acronym,
        context="",
        primary_expansion=scored[0][0] if scored else None,
        candidates=[
            DisambiguationCandidate(expansion=expansion, score=score, source="inline")
            for expansion, score in scored
        ],
        metadata=EngineMetadata(
            engine_tier=EngineTier.ZERO_DEPENDENCY,
            execution_time_ms=0.0,
            tokens_processed=0,
        ),
    )


# ---------------------------------------------------------------------------
# the rule
# ---------------------------------------------------------------------------
class TestTheRule:
    """The four clauses of the model ``bench/run_one_sense.py`` priced."""

    def test_the_first_definition_in_document_order_wins(self) -> None:
        """Not the highest-confidence one, and not the last one.

        The second definition carries the higher confidence, so a rule that
        committed by score rather than by position would propagate the other
        long form and this test would go red.
        """
        text = "AB is one. Later AB is two. AB again."
        pairs = [pair("AB", "alpha beta", 0, 0.6), pair("AB", "atomic bomb", 17, 0.99)]
        result = propagate(text, pairs)
        assert [o.long_form for o in result.propagated] == ["alpha beta"]
        assert result.propagated[0].span == (28, 30)

    def test_occurrences_before_the_definition_are_not_licensed(self) -> None:
        """A document may use a short form before defining it; the rule does not reach back."""
        text = "AB was mentioned. The alpha beta (AB) came later. Then AB again."
        pairs = AbbreviationExtractor(Config()).extract(text)
        result = propagate(text, pairs)
        licensed = [o.span for o in result.propagated]
        assert licensed == [(55, 57)]
        assert text[:2] == "AB" and (0, 2) not in licensed

    def test_a_substring_is_not_an_occurrence(self) -> None:
        """``CT`` is inside ``fact``; a bare substring search would license it."""
        text = "The computed tomography (CT) fact is that CT works."
        pairs = AbbreviationExtractor(Config()).extract(text)
        result = propagate(text, pairs)
        assert [o.span for o in result.propagated] == [(42, 44)]
        assert text[29:33] == "fact"

    def test_short_forms_outside_the_measured_frame_are_refused(self) -> None:
        """Single letters and lower-case markers are outside the priced population."""
        assert term_shaped("HIV") and not term_shaped("A") and not term_shaped("abc")
        text = "The alpha (A) and A and A."
        pairs = [pair("A", "alpha", 11)]
        result = propagate(text, pairs)
        assert result.refused == (("A", NOT_TERM_SHAPED),)
        assert result.propagated == ()

    def test_a_definition_site_is_never_dropped_by_a_refusal(self) -> None:
        """A refusal withholds propagation, never the definition ``extract`` found."""
        text = "The alpha (A) and A."
        result = propagate(text, [pair("A", "alpha", 11)])
        assert [o.source for o in result.occurrences] == [SOURCE_DEFINITION]

    def test_pairs_whose_span_does_not_hold_their_short_form_are_ignored(self) -> None:
        """The pairs and the text must belong together; a mismatch is not guessed at."""
        text = "Nothing here."
        assert propagate(text, [pair("AB", "alpha beta", 0)]).occurrences == ()

    def test_every_span_holds_its_own_short_form(self) -> None:
        """The identity ``extract`` documents, carried by every emitted occurrence."""
        text = (
            "The World Health Organization (WHO) met. WHO then met again. "
            "The computed tomography (CT) scan; CT again, and CT-guided too."
        )
        pairs = AbbreviationExtractor(Config()).extract(text)
        occurrences = propagate(text, pairs).occurrences
        assert occurrences
        for occurrence in occurrences:
            start, end = occurrence.span
            assert text[start:end] == occurrence.short_form

    def test_occurrences_come_back_in_document_order(self) -> None:
        text = "The World Health Organization (WHO) met. WHO. The alpha beta (AB). AB. WHO."
        pairs = AbbreviationExtractor(Config()).extract(text)
        spans = [o.span for o in propagate(text, pairs).occurrences]
        assert spans == sorted(spans)

    def test_empty_text_and_no_pairs_are_both_empty_results(self) -> None:
        assert propagate("", []).occurrences == ()
        assert propagate("Some text with no definitions.", []).occurrences == ()

    def test_whole_token_occurrences_of_an_empty_needle(self) -> None:
        assert whole_token_occurrences("anything", "") == ()

    def test_confidence_is_the_definitions_and_is_not_reearned(self) -> None:
        """A propagated site inherits its definition's number rather than earning one."""
        text = "AB is the alpha beta (AB). AB again."
        pairs = AbbreviationExtractor(Config()).extract(text)
        result = propagate(text, pairs)
        assert result.propagated
        for occurrence in result.propagated:
            assert occurrence.confidence == pairs[0].confidence
            assert occurrence.licensed_by == pairs[0].short_form_span


# ---------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------
class TestTheGate:
    """Every decision the gate can reach, and what propagation does with it."""

    @staticmethod
    def _gate(alpha: float = 0.2, points: int = 40) -> ConformalGate:
        """A marginal gate calibrated so a clear winner is answered."""
        calibration = [
            (result_with("XX", [("first", 0.9), ("second", 0.1)]), "first") for _ in range(points)
        ]
        return ConformalGate.calibrate(calibration, alpha=alpha)

    @staticmethod
    def _permissive_gate(alpha: float = 0.2) -> ConformalGate:
        """A gate whose threshold admits a genuine two-way tie, so it reads AMBIGUOUS.

        A quarter of the calibration points have the *lower*-scoring candidate as
        gold, which pushes the order statistic past the tie's nonconformity. A
        gate calibrated only on clear winners refuses a tie under
        ``no_plausible_candidate`` instead, which is a different refusal and is
        exercised by its own test.
        """
        clear = [(result_with("XX", [("first", 0.9), ("second", 0.1)]), "first") for _ in range(30)]
        hard = [(result_with("XX", [("first", 0.9), ("second", 0.1)]), "second") for _ in range(10)]
        return ConformalGate.calibrate(clear + hard, alpha=alpha)

    def test_a_gate_that_answers_the_committed_definition_propagates(self) -> None:
        text = "The alpha beta (AB) is here. AB again, and AB once more."
        pairs = AbbreviationExtractor(Config()).extract(text)
        ungated = propagate(text, pairs)
        gated = propagate(text, pairs, gate=self._gate())
        assert gated.refused == ()
        assert [o.span for o in gated.propagated] == [o.span for o in ungated.propagated]

    def test_a_gate_that_abstains_licenses_nothing_beyond_the_definitions(self) -> None:
        """Two definitions of one short form at the same score is the ambiguous case."""
        text = "The alpha beta (AB) here; the atomic bomb (AB) there. AB again."
        pairs = AbbreviationExtractor(Config()).extract(text)
        assert len({p.long_form for p in pairs if p.short_form == "AB"}) == 2
        gated = propagate(text, pairs, gate=self._permissive_gate())
        assert [reason for _, reason in gated.refused] == [GATE_AMBIGUOUS]
        assert gated.propagated == ()

    def test_an_uncalibrated_group_is_refused_rather_than_fitted(self) -> None:
        """A Mondrian gate that never saw arity 1 must not answer about it."""
        calibration = [
            (result_with("XX", [("first", 0.9), ("second", 0.1)]), "first") for _ in range(40)
        ]
        gate = ConformalGate.calibrate(
            calibration, alpha=0.2, group_by=lambda r: str(len(r.candidates))
        )
        text = "The alpha beta (AB) is here. AB again."
        pairs = AbbreviationExtractor(Config()).extract(text)
        gated = propagate(text, pairs, gate=gate)
        assert [reason for _, reason in gated.refused] == [GATE_UNCALIBRATED_GROUP]
        assert gated.propagated == ()

    def test_a_gate_answering_something_other_than_the_commitment_is_a_disagreement(self) -> None:
        """A2 commits by position and the gate answers by score; a split is refused.

        Constructed rather than found: the second definition carries the higher
        confidence, so ``document_result`` ranks it first and the gate answers
        it, while A2 has committed to the first one in document order. Neither
        component is wrong and the pair of them do not agree, which is a refusal
        and not an answer.
        """
        text = "AB is the alpha beta. AB is the atomic bomb. AB again."
        pairs = [pair("AB", "alpha beta", 0, 0.10), pair("AB", "atomic bomb", 22, 0.90)]
        gated = propagate(text, pairs, gate=self._gate())
        assert gated.refused == (("AB", GATE_DISAGREED),)
        assert gated.propagated == ()

    def test_a_result_with_no_candidates_is_its_own_refusal(self) -> None:
        """Reachable only through a hand-built result; kept so the code path is exercised."""
        assert propagation._gate_refusal("no_candidates") == GATE_NO_CANDIDATES

    def test_a_gate_of_the_wrong_type_is_refused_loudly(self) -> None:
        with pytest.raises(ConfigurationError, match="ConformalGate"):
            propagate("AB (alpha beta). AB.", [pair("AB", "alpha beta", 0)], gate=object())

    def test_gating_never_licenses_more_than_not_gating(self) -> None:
        """P4 of this round's pre-registration, pinned rather than asserted.

        A gate is a refusal policy: over any document and any calibration it may
        withhold propagation and may never invent it.
        """
        text = (
            "The alpha beta (AB) here; the atomic bomb (AB) there. AB again. "
            "The World Health Organization (WHO) met. WHO again."
        )
        pairs = AbbreviationExtractor(Config()).extract(text)
        ungated = {o.span for o in propagate(text, pairs).propagated}
        for alpha in (0.05, 0.10, 0.20):
            gated = {
                o.span for o in propagate(text, pairs, gate=self._gate(alpha=alpha)).propagated
            }
            assert gated <= ungated


class TestDocumentResult:
    """The choice a gate is asked about, built from one document."""

    def test_the_primary_is_positional_and_the_candidates_are_scored(self) -> None:
        pairs = [pair("AB", "alpha beta", 0, 0.10), pair("AB", "atomic bomb", 22, 0.90)]
        result = document_result("AB", pairs)
        assert result.primary_expansion == "alpha beta"
        assert [c.expansion for c in result.candidates] == ["atomic bomb", "alpha beta"]

    def test_other_short_forms_are_ignored(self) -> None:
        pairs = [pair("AB", "alpha beta", 0), pair("CD", "charlie delta", 20)]
        assert [c.expansion for c in document_result("AB", pairs).candidates] == ["alpha beta"]

    def test_a_short_form_the_document_never_defines_has_no_candidates(self) -> None:
        result = document_result("ZZ", [pair("AB", "alpha beta", 0)])
        assert result.candidates == [] and result.primary_expansion is None

    def test_a_repeated_long_form_keeps_its_highest_confidence(self) -> None:
        pairs = [pair("AB", "alpha beta", 0, 0.3), pair("AB", "alpha beta", 20, 0.8)]
        candidates = document_result("AB", pairs).candidates
        assert len(candidates) == 1 and candidates[0].score == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# the claim
# ---------------------------------------------------------------------------
#: Every source this class reads as TEXT, not as an import.
#:
#: An installed distribution carries none of them: `src/` is not laid down,
#: `README.md` and `CHANGELOG.md` are metadata rather than files on disk, and
#: `bench/results.json` is a checkout artefact. The class read them unguarded and
#: contributed twelve unexpected failures to the installed-suite job on its first
#: CI run -- the fourth instance this project has recorded of a test that reads
#: checkout-only files without saying so.
#:
#: A CLASS-level skip and not a module-level one, deliberately: the other 49
#: tests in this file exercise `propagate()` through the imported package and
#: must keep running against the installed distribution, which is where a
#: packaging defect in the new module would actually show up.
_CLAIM_SOURCES = (*CLAIM_FILES, "bench/results.json")


@pytest.mark.skipif(
    not all((REPO_ROOT / name).is_file() for name in _CLAIM_SOURCES),
    reason="the prose rule reads source text an installed distribution does not carry",
)
class TestTheClaim:
    """The B6 trap, guarded in the crudest way that can actually fail."""

    @pytest.mark.parametrize("relative", CLAIM_FILES)
    def test_no_paragraph_asserts_a_bound_over_propagation_without_naming_it_joint(
        self, relative: str
    ) -> None:
        """A bound stated beside propagation must say which rate it bounds.

        The failure this guards is a *loose* sentence rather than a precise wrong
        one: "only propagate when the definition is confident enough" reads to
        every caller as a promise about the propagations that follow, and the
        measured selective error on ``conformal.sdu21.exchangeable`` is
        ``4.38`` times ``alpha``. Requiring the word ``joint`` in the same
        paragraph is the smallest rule that makes the omission mechanical.

        **It has a false-positive class and it fired on one during authoring**:
        ``bounded by`` is also how one writes about a *recall ceiling*, which is
        not a probabilistic bound at all. The paragraph was reworded rather than
        the rule narrowed, because a rule narrow enough never to misfire is the
        rule that went inert in D-104.
        """
        offenders = [
            block
            for block in paragraphs((REPO_ROOT / relative).read_text(encoding="utf-8"))
            if "propagat" in block.lower()
            and any(marker in block.lower() for marker in BOUND_MARKERS)
            and "joint" not in block.lower()
        ]
        assert not offenders, (
            f"{relative}: {len(offenders)} paragraph(s) state a bound beside propagation "
            f"without naming it joint. First:\n{offenders[0][:400]}"
        )

    @pytest.mark.parametrize("relative", CLAIM_FILES)
    def test_no_file_states_the_selective_reading_outright(self, relative: str) -> None:
        """The blocklist half. Evadable by rewording, and said to be."""
        body = " ".join((REPO_ROOT / relative).read_text(encoding="utf-8").lower().split())
        found = [phrase for phrase in FORBIDDEN_PHRASES if phrase in body]
        assert not found, f"{relative} contains the selective reading: {found}"

    @pytest.mark.parametrize("relative", CLAIM_FILES)
    def test_no_sentence_names_the_selective_rate_without_disowning_it(self, relative: str) -> None:
        """Naming the selective rate is fine; naming it as the bound is not.

        This is the rule that catches a *reworded* overclaim, which the paragraph
        rule above cannot: "it also bounds the error rate among the gate's
        answers, which is the same quantity" contains the word ``joint``
        somewhere in its paragraph and passes there, and fails here.
        """
        offenders = [
            sentence
            for sentence in sentences((REPO_ROOT / relative).read_text(encoding="utf-8"))
            if any(subject in sentence.lower() for subject in SELECTIVE_SUBJECTS)
            and not any(word in sentence.lower() for word in DISCLAIMERS)
        ]
        assert not offenders, (
            f"{relative}: {len(offenders)} sentence(s) name the selective rate without "
            f"denying it is the bound. First: {offenders[0][:300]}"
        )

    @pytest.mark.parametrize("constant,fragment", REQUIRED_IN_CONSTANTS)
    def test_each_constant_carries_its_load_bearing_clause(
        self, constant: str, fragment: str
    ) -> None:
        """The constant is the surface a caller reads; the prose is a copy of it."""
        assert fragment in constant, f"{fragment!r} is no longer in the disclosure constant"

    @pytest.mark.parametrize("fragment", REQUIRED_FRAGMENTS)
    def test_each_disclosure_sentence_survives_verbatim_exactly_once(self, fragment: str) -> None:
        """A disclosure that can be diluted by an unrelated mention is not a disclosure."""
        body = (REPO_ROOT / "src/acronymkit/propagation.py").read_text(encoding="utf-8")
        flat = " ".join(body.split())
        assert flat.count(" ".join(fragment.split())) == 1, (
            f"the disclosure fragment {fragment!r} appears "
            f"{flat.count(' '.join(fragment.split()))} time(s), not once"
        )

    def test_the_disclosure_carries_all_three_parts_and_cannot_be_split(self) -> None:
        """``gate_disclosure`` is the runtime surface; prose is the copy of it."""
        gate = TestTheGate._gate()
        disclosure = gate_disclosure(gate)
        assert gate.guarantee() in disclosure
        assert JOINT_NOT_SELECTIVE in disclosure
        assert PROPAGATION_GAP in disclosure
        assert "exchangeab" in disclosure
        assert disclosure.index(JOINT_NOT_SELECTIVE) < disclosure.index(PROPAGATION_GAP)

    @pytest.mark.parametrize(
        "constant,rendered,run_id,field",
        [
            (
                "JOINT_NOT_SELECTIVE",
                "21.92 %",
                "conformal.sdu21.exchangeable",
                ("mondrian_by_arity.alpha_0.05", "selective_error_pct"),
            ),
            (
                "JOINT_NOT_SELECTIVE",
                "37.02 %",
                "conformal.sdu21.exchangeable",
                ("mondrian_by_arity.alpha_0.20", "selective_error_pct"),
            ),
            (
                "PROPAGATION_GAP",
                "0.581 %",
                "one_sense.pmc_oa.a2.high_precision",
                ("wrong_floor_correctness_pct_of_licensed",),
            ),
            (
                "PROPAGATION_GAP",
                "9.68 %",
                "one_sense.pmc_oa.a2.high_precision",
                ("wrong_ceiling_correctness_pct_of_licensed",),
            ),
        ],
    )
    def test_every_number_in_the_disclosure_still_equals_its_measurement(
        self, constant: str, rendered: str, run_id: str, field: tuple
    ) -> None:
        """The four numbers a caller reads at runtime, checked against the runs.

        ``tools/check_claims.py`` can only reach these through a ``# measured:``
        marker, which asserts the run id exists and says nothing about the value:
        a shipped string is not Markdown and carries no rendered citation. This
        test is the value half, and it is the half that catches a re-measurement
        the constant did not follow.
        """
        payload = json.loads((REPO_ROOT / "bench/results.json").read_text(encoding="utf-8"))
        record = payload["runs"][run_id]
        # Keys in bench/results.json contain literal dots, so the path is a
        # tuple of exact keys rather than a dotted string that would be split
        # in the wrong places.
        for part in field:
            record = record[part]
        number, _, unit = rendered.partition(" ")
        places = len(number.split(".")[1]) if "." in number else 0
        assert f"{float(record):.{places}f}{(' ' + unit) if unit else ''}" == rendered, (
            f"{constant} says {rendered!r}; {run_id} {field} is {record!r}"
        )
        assert rendered in getattr(propagation, constant)

    def test_the_module_names_the_measured_multiple_beside_the_gate(self) -> None:
        """D-104's factor is quoted at the call site, not left in a decision record."""
        body = (REPO_ROOT / "src/acronymkit/propagation.py").read_text(encoding="utf-8")
        assert "4.38" in body, "the measured selective/alpha multiple is not at the call site"
        assert "21.92" in body, "the measured selective error rate is not at the call site"
        assert "risk-controlled selective classification" in body

    def test_the_module_says_the_gate_does_not_reach_the_licensed_occurrences(self) -> None:
        """The second gap, which is this module's own rather than conformal's."""
        body = (REPO_ROOT / "src/acronymkit/propagation.py").read_text(encoding="utf-8").lower()
        assert "one-sense-per-" in body
        assert "the gate cannot see it" in body


# ---------------------------------------------------------------------------
# housekeeping
# ---------------------------------------------------------------------------
def test_occurrence_is_frozen() -> None:
    """An occurrence is a record of what was decided, not a mutable buffer."""
    occurrence = Occurrence("AB", "alpha beta", (0, 2), SOURCE_PROPAGATED, (0, 2), 1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        occurrence.span = (1, 3)  # type: ignore[misc]


def test_the_submodule_is_reachable_as_a_package_attribute() -> None:
    """``import acronymkit; acronymkit.propagation`` -- the gap ``conformal`` fell into."""
    import importlib

    import acronymkit

    assert acronymkit.propagation is importlib.import_module("acronymkit.propagation")
    assert acronymkit.conformal is importlib.import_module("acronymkit.conformal")


def test_module_doctests_pass() -> None:
    """Every example in the module runs and prints what it says it prints."""
    results = doctest.testmod(propagation, verbose=False, report=False)
    assert results.failed == 0, f"{results.failed} doctest failure(s)"
    assert results.attempted > 0, "no doctests collected"
