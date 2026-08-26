"""Tests for ``bench/run_roundtrip_verifier.py``.

Four of these are the deliverable rather than a check on it.

**The node budget must force the beam without starving the search.** The whole
beam sweep sets ``max_search_nodes`` per pair to ``exhaustive_bound(...) - 1``,
because the generator consults its beam only when the space fails to fit the
budget. If that arithmetic is wrong by one, every "recall at beam b" figure is a
node-budget figure wearing a beam's name.
:class:`TestTheBudgetThatForcesBeamMode` pins both halves: at ``bound`` the run
is exhaustive, at ``bound - 1`` it is not, and a beam too wide to cut leaves the
output **byte-identical** to the exhaustive run.

**The instrument must be able to report both answers.** A recall harness that
returns a plausible middling number is indistinguishable from one that is
broken. :class:`TestTheHarnessCanReportEitherAnswer` drives it over a corpus of
pairs the generator trivially reaches and over one it cannot reach at all, and
requires ``100.00`` and ``0.00``.

**``prefix_alignable`` must not be the aligner.** It exists to separate a miss
the generator can never fix from one a configuration is causing, and it is only
worth anything if the two instruments disagree. A pair whose short form takes a
character from *inside* a word is accepted by ``find_best_long_form`` and
refused here; if that assertion ever fails, the ceiling number has silently
become a second copy of the aligner's reach.

**The negatives must be negative.** The 2x2 rests on them, and a "negative" that
is a gold pair under another name turns the discrimination figure into noise.

Every assertion here was run once against a deliberately broken implementation
and observed red before being left green (R11).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "bench" / "run_roundtrip_verifier.py"

# A GUARD, NOT A LINE IN `EXPECTED_NON_PASSING`, for the reason
# tests/test_genre.py gives at the same place: the sdist ships `bench/` as a
# package directory and deliberately ships none of its modules, so the import
# below raises `ImportError` there and this file would fail to COLLECT. A
# `skipif` mark is consulted at collection and a module body runs at import, so
# the mark is too late. The condition named is exactly the one that differs, so
# any other error in this file still reaches the job.
if not RUNNER.is_file():  # pragma: no cover - installed/sdist runs only
    pytest.skip(
        "bench/run_roundtrip_verifier.py is not part of an installed distribution",
        allow_module_level=True,
    )

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bench import run_roundtrip_verifier as rt  # noqa: E402

from acronymkit.config import Config  # noqa: E402
from acronymkit.engine import AcronymEngine  # noqa: E402
from acronymkit.generator import ForwardGenerator  # noqa: E402
from acronymkit.scoring import Scorer  # noqa: E402
from acronymkit.tokenizer import Tokenizer  # noqa: E402

#: Phrases spanning one to seven eligible tokens, so the bound arithmetic is
#: exercised where the search space is tiny and where it is not.
PHRASES = (
    "genome",
    "multiple sclerosis",
    "portable document format",
    "high density lipoprotein cholesterol",
    "national institute of allergy and infectious diseases",
    "chronic obstructive pulmonary disease exacerbation severity index",
)


@pytest.fixture(scope="module")
def collaborators():
    """The engine's lexicon and n-gram model, so scoring matches the shipped path."""
    engine = AcronymEngine(Config())
    return engine.lexicon, engine.ngram


def _generate(phrase: str, config: Config, collaborators) -> tuple:
    """Run the forward generator over ``phrase`` under ``config``."""
    lexicon, ngram = collaborators
    tokens = Tokenizer(config).tokenize(phrase)
    generator = ForwardGenerator(config, Scorer(config, lexicon, ngram))
    candidates, evaluated, truncated = generator.generate(tokens)
    return tuple(candidate.acronym for candidate in candidates), evaluated, truncated


class TestTheBudgetThatForcesBeamMode:
    """``exhaustive_bound`` is load-bearing for every beam figure in the sweep."""

    def test_at_the_bound_the_search_is_exhaustive(self, collaborators) -> None:
        """``max_search_nodes == bound`` fits, so no beam is consulted.

        Driven with ``search_beam_width=1``: a beam of one would collapse the
        frontier to a single state and change the output beyond recognition, so
        an identical output is evidence the beam was never read.
        """
        for phrase in PHRASES:
            base = Config(max_candidates=rt.UNBOUNDED_TOP_N)
            tokens = Tokenizer(base).tokenize(phrase)
            bound = rt.exhaustive_bound(tokens, base)
            assert bound > 0, phrase
            at_bound = Config(
                max_candidates=rt.UNBOUNDED_TOP_N, max_search_nodes=bound, search_beam_width=1
            )
            wide = Config(max_candidates=rt.UNBOUNDED_TOP_N, max_search_nodes=rt.EXHAUSTIVE_NODES)
            assert (
                _generate(phrase, at_bound, collaborators)[0]
                == _generate(phrase, wide, collaborators)[0]
            ), phrase
            assert _generate(phrase, at_bound, collaborators)[2] is False, phrase

    def test_one_below_the_bound_the_beam_is_read(self, collaborators) -> None:
        """``bound - 1`` does not fit, so a beam of one truncates.

        The single-token phrase is excluded: with one eligible token there is no
        second round for a cut to happen in, which is a property of the search
        and not a hole in the budget.
        """
        cut = 0
        for phrase in PHRASES:
            base = Config(max_candidates=rt.UNBOUNDED_TOP_N)
            tokens = Tokenizer(base).tokenize(phrase)
            budget = max(1, rt.exhaustive_bound(tokens, base) - 1)
            narrow = Config(
                max_candidates=rt.UNBOUNDED_TOP_N, max_search_nodes=budget, search_beam_width=1
            )
            acronyms, _, truncated = _generate(phrase, narrow, collaborators)
            if len([t for t in tokens if t.is_eligible and t.letters]) > 1:
                assert truncated is True, phrase
                cut += 1
            assert len(acronyms) >= 1, phrase
        assert cut >= 4

    def test_the_budget_never_starves_a_beam_too_wide_to_cut(self, collaborators) -> None:
        """The control the sweep publishes, asserted here as well.

        With the same ``bound - 1`` budget and a beam wider than any frontier,
        nothing can cut and nothing may truncate -- so the output must be
        **byte-identical** to the exhaustive run. If it is not, the per-pair
        budget is stopping the search and every beam figure is confounded.
        """
        for phrase in PHRASES:
            base = Config(max_candidates=rt.UNBOUNDED_TOP_N)
            tokens = Tokenizer(base).tokenize(phrase)
            budget = max(1, rt.exhaustive_bound(tokens, base) - 1)
            control = Config(
                max_candidates=rt.UNBOUNDED_TOP_N,
                max_search_nodes=budget,
                search_beam_width=rt.BEAM_CONTROL_WIDTH,
            )
            wide = Config(max_candidates=rt.UNBOUNDED_TOP_N, max_search_nodes=rt.EXHAUSTIVE_NODES)
            control_out, _, control_truncated = _generate(phrase, control, collaborators)
            assert control_truncated is False, phrase
            assert control_out == _generate(phrase, wide, collaborators)[0], phrase


class TestTheHarnessCanReportEitherAnswer:
    """A recall harness that cannot report ``0`` or ``100`` is not an instrument."""

    def _corpus(self, pairs) -> rt.PairCorpus:
        return rt.PairCorpus(
            name="synthetic",
            label="synthetic (not a declared corpus)",
            pairs=tuple(pairs),
            documents=0,
            occurrences=len(pairs),
        )

    def test_reachable_pairs_score_one_hundred(self, collaborators) -> None:
        """Plain initialisms are injected unconditionally, so these cannot miss."""
        lexicon, ngram = collaborators
        corpus = self._corpus(
            [
                ("PDF", "portable document format"),
                ("MS", "multiple sclerosis"),
                ("HDL", "high density lipoprotein"),
            ]
        )
        arm = rt.Arm("exhaustive", Config(max_candidates=rt.UNBOUNDED_TOP_N), False, "")
        record, vector = rt.run_arm(arm, corpus, lexicon, ngram)
        assert record["recall_pct"] == 100.0
        assert vector == (True, True, True)

    def test_unreachable_pairs_score_zero(self, collaborators) -> None:
        """Short forms whose characters are nowhere near a word start."""
        lexicon, ngram = collaborators
        corpus = self._corpus(
            [
                ("ZZQ", "portable document format"),
                ("XKW", "multiple sclerosis"),
                ("QJV", "high density lipoprotein"),
            ]
        )
        arm = rt.Arm("exhaustive", Config(max_candidates=rt.UNBOUNDED_TOP_N), False, "")
        record, vector = rt.run_arm(arm, corpus, lexicon, ngram)
        assert record["recall_pct"] == 0.0
        assert vector == (False, False, False)

    def test_the_memo_does_not_change_a_verdict(self, collaborators) -> None:
        """Every throughput figure ships with a memo hit rate, so the memo must be exact.

        The same long form appears three times; the second and third lookups are
        memo hits, and all three verdicts must still be the ones a cold run
        gives.
        """
        lexicon, ngram = collaborators
        corpus = self._corpus(
            [
                ("PDF", "portable document format"),
                ("PD", "portable document format"),
                ("ZZQ", "portable document format"),
            ]
        )
        arm = rt.Arm("exhaustive", Config(max_candidates=rt.UNBOUNDED_TOP_N), False, "")
        record, vector = rt.run_arm(arm, corpus, lexicon, ngram)
        assert record["work"]["generator_calls"] == 1
        assert record["work"]["memo_hits"] == 2
        assert record["work"]["memo_hit_rate_pct"] == pytest.approx(66.67, abs=0.01)
        assert vector == (True, True, False)


class TestPrefixAlignabilityIsNotTheAligner:
    """The ceiling must measure the generator's space, not the aligner's reach."""

    def test_an_inside_word_character_is_refused_here_and_accepted_there(self) -> None:
        """The one difference that produces the whole recall gap.

        ``5HT`` over ``5-hydroxytryptamine`` takes ``T`` from the middle of a
        word. Schwartz & Hearst allows that; a prefix walk cannot.
        """
        short, long_form = "5HT", "5-hydroxytryptamine"
        assert rt.aligner_verdict(short, long_form) is True
        assert rt.prefix_alignable(short, long_form, 0) is False

    def test_a_plain_initialism_is_accepted_by_both(self) -> None:
        """The control on the assertion above: the two agree where they should."""
        assert rt.prefix_alignable("PDF", "portable document format", 1) is True
        assert rt.aligner_verdict("PDF", "portable document format") is True

    def test_the_letter_cap_is_the_dial_it_claims_to_be(self) -> None:
        """``AmB`` needs two characters from one word and one from the next."""
        assert rt.prefix_alignable("AmB", "amphotericin B", 1) is False
        assert rt.prefix_alignable("AmB", "amphotericin B", 2) is True

    def test_the_aligner_verdict_composes_all_three_shipped_rules(self) -> None:
        """A pair that fails only the short-form rule must be rejected."""
        # 'portable' is eleven characters and three words' worth of nothing: the
        # short-form admissibility rule refuses it before any alignment runs.
        assert rt.aligner_verdict("a much longer than ten", "anything at all here") is False
        # Lower-cased short forms are refused by `require_uppercase`, which is
        # why the corpora keep case rather than folding it.
        assert rt.aligner_verdict("pdf", "portable document format") is False
        assert rt.aligner_verdict("PDF", "portable document format") is True


class TestTheNegativesAreNegative:
    """The 2x2's discrimination figure rests entirely on this."""

    def test_no_negative_reproduces_a_gold_pair(self) -> None:
        corpus = rt.PairCorpus(
            name="synthetic",
            label="synthetic",
            pairs=(
                ("PDF", "portable document format"),
                ("MS", "multiple sclerosis"),
                ("HDL", "high density lipoprotein"),
                ("GA", "general anesthesia"),
            ),
            documents=0,
            occurrences=4,
        )
        drawn = rt.negatives(corpus)
        assert len(drawn) == len(corpus.pairs)
        gold = set(corpus.pairs)
        for (short, long_form), (gold_short, gold_long) in zip(drawn, corpus.pairs):
            assert short == gold_short
            assert long_form != gold_long
            assert (short, long_form) not in gold

    def test_the_draw_is_seeded_and_reproducible(self) -> None:
        corpus = rt.PairCorpus(
            name="synthetic",
            label="synthetic",
            pairs=tuple((f"S{index}", f"long form number {index}") for index in range(20)),
            documents=0,
            occurrences=20,
        )
        assert rt.negatives(corpus) == rt.negatives(corpus)


class TestTheStatistics:
    """No dependency computes these, so they are pinned against known values."""

    def test_pearson_of_a_perfect_line(self) -> None:
        assert rt.pearson([1.0, 2.0, 3.0, 4.0], [2.0, 4.0, 6.0, 8.0]) == pytest.approx(1.0)
        assert rt.pearson([1.0, 2.0, 3.0, 4.0], [8.0, 6.0, 4.0, 2.0]) == pytest.approx(-1.0)

    def test_pearson_refuses_a_constant_and_a_short_sample(self) -> None:
        assert rt.pearson([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None
        assert rt.pearson([1.0, 2.0], [1.0, 2.0]) is None

    def test_spearman_sees_a_monotone_relation_pearson_understates(self) -> None:
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [1.0, 2.0, 4.0, 8.0, 16.0]
        assert rt.spearman(xs, ys) == pytest.approx(1.0)
        assert rt.pearson(xs, ys) < 0.97

    def test_phi_of_a_perfect_and_of_an_independent_table(self) -> None:
        assert rt.phi(10, 0, 0, 10) == pytest.approx(1.0)
        assert rt.phi(5, 5, 5, 5) == pytest.approx(0.0)
        assert rt.phi(10, 0, 10, 0) is None


class TestTheVerdictItself:
    """What "the short form appears in the output" is allowed to mean."""

    def test_the_strict_verdict_is_case_insensitive(self) -> None:
        probe = rt.Probe(acronyms=("pdf",), scores={"pdf": 1.0})
        assert rt.roundtrip_hit(probe, "PDF") is True
        assert rt.roundtrip_hit(probe, "PdF") is True
        assert rt.roundtrip_hit(probe, "PD") is False

    def test_the_relaxed_verdict_ignores_punctuation_the_generator_cannot_emit(self) -> None:
        probe = rt.Probe(acronyms=("ohd",), scores={"ohd": 1.0})
        assert rt.roundtrip_hit(probe, "(OH)D") is False
        assert rt.roundtrip_hit_alnum(probe, "(OH)D") is True
        assert rt.roundtrip_hit_alnum(probe, "(OH)E") is False


class TestTheMissDecomposition:
    """The disposition rests on separating unbuyable misses from buyable ones."""

    def test_an_inside_word_miss_is_architectural_and_a_filtered_one_is_not(self) -> None:
        corpus = rt.PairCorpus(
            name="synthetic",
            label="synthetic",
            pairs=(
                ("PDF", "portable document format"),
                ("5HT", "5-hydroxytryptamine"),
                ("NOA", "national office of accounts"),
            ),
            documents=0,
            occurrences=3,
        )
        record = rt.miss_record(corpus, (True, False, False), None)
        assert record["misses"] == 2
        # `5HT` takes a character from inside a word: unreachable at every setting.
        assert record["misses_architectural"] == 1
        # `NOA` needs `of` -- a preposition the shipped stop-word policy refuses
        # to let donate. Reachable in principle, refused by configuration.
        assert record["misses_configurational"] == 1
        assert record["recovered_by_verification_config"] is None

    def test_the_recovery_column_reads_the_widened_arm(self) -> None:
        corpus = rt.PairCorpus(
            name="synthetic",
            label="synthetic",
            pairs=(("NOA", "national office of accounts"),),
            documents=0,
            occurrences=1,
        )
        assert rt.miss_record(corpus, (False,), (True,))["recovered_by_verification_config"] == 1
        assert rt.miss_record(corpus, (False,), (False,))["recovered_by_verification_config"] == 0


class TestTheBeamBoundDisposition:
    """The refusal to touch ``_beam_bound`` has to be arithmetic, not a preference."""

    def test_it_prices_the_repair_against_the_ceiling(self) -> None:
        """An oracle bound can only ever recover the gap the beam opened.

        The record is derived from arms already measured, so the test drives it
        with a synthetic ``recall`` dict and checks the arithmetic rather than
        re-running a corpus.
        """
        recall = {
            "shipped": {"pairs": 1000, "truncated_pairs": 2},
            "beam_1": {"recall_pct": 33.0},
            "beam_250": {"recall_pct": 42.0},
            "beam_control_never_cuts": {"recall_pct": 42.1},
        }
        record = rt.beam_bound_disposition(recall)
        assert record["unpruned_ceiling_pct"] == 42.1
        assert record["max_points_an_oracle_bound_could_recover_at_width_1"] == 9.1
        assert record["max_points_an_oracle_bound_could_recover_at_width_250"] == 0.1
        assert record["shipped_pairs_where_the_beam_is_read"] == 2
        assert record["max_points_an_oracle_bound_could_recover_at_shipped_defaults"] == 0.2
        assert record["points_below_a_perfect_verifier_at_the_ceiling"] == 57.9

    def test_a_beam_that_cost_everything_would_say_so(self) -> None:
        """The control on the assertion above: the record can report a large repair."""
        recall = {
            "shipped": {"pairs": 1000, "truncated_pairs": 900},
            "beam_1": {"recall_pct": 5.0},
            "beam_250": {"recall_pct": 20.0},
            "beam_control_never_cuts": {"recall_pct": 90.0},
        }
        record = rt.beam_bound_disposition(recall)
        assert record["max_points_an_oracle_bound_could_recover_at_width_250"] == 70.0
        assert record["max_points_an_oracle_bound_could_recover_at_shipped_defaults"] == 90.0


class TestThePrecisionFilterQuestion:
    """Rejecting half the proposals is only worth something if it rejects the wrong half."""

    def test_a_filter_that_cannot_tell_right_from_wrong_reports_zero_discrimination(
        self, collaborators
    ) -> None:
        """The control that makes the discrimination figure readable.

        Two proposals, one gold and one not, whose long forms both reach their
        short form. Nothing is rejected, so the filter buys nothing and the
        record must say ``0.0`` rather than a plausible-looking number.
        """
        lexicon, ngram = collaborators
        corpus = rt.PairCorpus(
            name="synthetic",
            label="synthetic",
            pairs=(("PDF", "portable document format"),),
            documents=1,
            occurrences=1,
            texts=(
                "The portable document format (PDF) is a format. "
                "The multiple sclerosis (MS) study ran for years.",
            ),
        )
        prober = rt.Prober(Config(max_candidates=rt.UNBOUNDED_TOP_N), lexicon, ngram)
        record = rt.extractor_proposal_record(corpus, prober)
        high = record["high_precision"]
        assert high["distinct_proposed_pairs"] == 2
        assert high["proposals_matching_gold"] == 1
        assert high["proposals_not_matching_gold"] == 1
        assert high["roundtrip_rejects"] == 0
        assert high["discrimination_points"] == 0.0
        assert high["precision_before_filter_pct"] == 50.0
        assert high["precision_after_filter_pct"] == 50.0

    def test_a_corpus_with_no_text_says_so_rather_than_reporting_zero(self) -> None:
        """An empty record and a measured zero must not look alike."""
        corpus = rt.PairCorpus(
            name="synthetic", label="synthetic", pairs=(("A", "alpha"),), documents=0, occurrences=1
        )
        record = rt.extractor_proposal_record(corpus, None)  # type: ignore[arg-type]
        assert record["pairs"] == 0
        assert "extractor was not run" in record["note"]
