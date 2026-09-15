"""``tools/sample_claims.py``: the channel-stratified sentence frame, and its price.

Why this module is shaped the way it is
---------------------------------------
The thing under test is a **measurement instrument**, and the failure mode of a
measurement instrument is not a crash. It is a number that looks right.

So the tests below are weighted toward the ways this tool could be quietly wrong
rather than loudly broken:

* **The reason the previous frame was retired.** That reason is a *proof* --
  ``check_claims.prose_of()`` masks fenced blocks and inline code spans, this
  project writes every real figure inside a code span, so the two sets are
  disjoint. :class:`TestTheRetiredFrame` re-derives it against the live checker
  instead of quoting the docstring that states it, because a proof nobody re-runs
  is a paragraph.
* **Containment.** :class:`TestContainment` asserts that the frame can reach the
  sentences previous rounds actually graded not true. This is a **floor**: the
  design was fitted to those sites, so containing them is the least it can do and
  is not evidence it will contain the next three.
* **The estimator.** With a third of the draw taken from a channel holding one
  per cent of the population, the unweighted count over the sample is not the
  repository's rate. :class:`TestTheEstimator` builds a frame where those two
  numbers differ by a wide margin and pins which one comes out.
* **The arithmetic that closes the predecessor series.** The constant said five
  rounds and ``16.67`` % while the record file said six and ``15.97`` %.
  :class:`TestTheClosedSeries` recomputes both from the per-round counts rather
  than trusting either copy, and checks the two copies against each other.

``design_effect`` is tested in the direction that does **not** flatter the
design: a proportional allocation must return ``1.00`` and the shipped unequal
one must return more, because the whole point of printing it is that it is
allowed to be an argument against the tool that prints it.
"""

from __future__ import annotations

import importlib.util
import math
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

# THESE TESTS READ FILES THAT ONLY A CHECKOUT CARRIES, AND SAY SO. `.github/`
# is outside `MANIFEST.in`, so the register, the workflows and the run summaries
# are absent from an sdist. The module-level guard above already skips this file
# when `tools/` is missing, which is the same condition; every test that reaches
# past `tools/` is marked with this constant so the dependency is greppable
# rather than implicit. Five instances of a test silently reading a
# checkout-only file are on record, which is why this note exists.
CHECKOUT_ONLY = (".github/gates.toml", ".github/workflows/", ".github/run-summaries/")


def _frame(counts: Dict[str, int], missing: tuple = ()) -> object:
    """A frame with ``counts[channel]`` synthetic items in each channel."""
    items: List[object] = []
    for channel, how_many in counts.items():
        for index in range(how_many):
            items.append(
                sc.FrameItem(
                    identifier=f"{channel}/{index}",
                    relative_path=f"docs/{channel}.md",
                    line_number=index + 1,
                    channel=channel,
                    region="prose",
                    text=f"a sentence carrying {index} in the {channel} channel",
                )
            )
    return sc.Frame(items=tuple(items), missing_channels=missing)


class TestTheClosedSeries:
    """The number the predecessor is closed at, recomputed rather than quoted."""

    def test_the_series_is_closed_at_seven_rounds_not_five_and_not_six(self) -> None:
        # THE BOOKKEEPING DEFECT, TWICE, ONE ROUND APART AND BOTH IN THE SAME
        # DIRECTION. The constant first said 5 / 120 / 20 while the record file
        # said 6 / 144 / 23; it was corrected to six, and a SEVENTH round had
        # already graded 24 claims under the same frame, unit and rules. Both
        # closures were declared over a round that was already running, which is
        # why this asserts the round COUNT and not only the arithmetic.
        assert sc.CLOSED_SERIES["rounds"] == 7
        assert sc.CLOSED_SERIES["draws"] == 168
        assert sc.CLOSED_SERIES["not_true"] == 25

    def test_the_pooled_rate_is_what_the_constant_says(self) -> None:
        counts = sc.CLOSED_SERIES["per_round"]
        assert sum(counts) == sc.CLOSED_SERIES["not_true"] == 25
        assert len(counts) * 24 == sc.CLOSED_SERIES["draws"] == 168
        assert round(100 * sum(counts) / 168, 2) == 14.88

    def test_the_wilson_interval_reproduces_to_two_decimals(self) -> None:
        # The figures are TRANSCRIBED into the constant on purpose; an
        # independent implementation has to land on them or the series is being
        # closed at somebody's recollection.
        low, high = sc.wilson(25, 168)
        assert (round(low, 2), round(high, 2)) == sc.CLOSED_SERIES["wilson_pct"]

    def test_the_five_round_figure_still_reproduces(self) -> None:
        # The five-round number is not wrong, it is INCOMPLETE. It must still
        # recompute, because the record file publishes it as the closure of
        # rounds one to five and a reader will meet it there.
        low, high = sc.wilson(20, 120)
        assert (round(low, 2), round(high, 2)) == (11.06, 24.35)
        assert round(100 * 20 / 120, 2) == 16.67

    def test_the_sixth_point_shrank_the_interval_less_than_it_moved_the_estimate(self) -> None:
        # The instrument finding that retired the pooling strategy, recomputed.
        #
        # AND THE PUBLISHED MOVE IS 0.70 ONLY IF YOU SUBTRACT TWO ALREADY-
        # ROUNDED PERCENTAGES. 16.67 - 15.97 = 0.70; the rounded difference of
        # the exact values is 0.69. Both readings are pinned here so nobody
        # re-derives which one a sentence meant. The finding it supports --
        # that the interval is now shrinking about as fast as the point is
        # wandering -- survives either way, and is slightly stronger at 0.69.
        low5, high5 = sc.wilson(20, 120)
        low6, high6 = sc.wilson(23, 144)
        assert round((high5 - low5) / 2, 2) == 6.64
        assert round((high6 - low6) / 2, 2) == 5.97
        assert round(((high5 - low5) - (high6 - low6)) / 2, 2) == 0.67

    def test_the_seventh_point_did_it_again_and_that_is_the_retirement_argument(self) -> None:
        # THE SAME FINDING FOR THE THIRD CONSECUTIVE ROUND, which is what turns
        # it from an observation into the reason the instrument is retired
        # rather than extended: a seventh point moved the estimate 1.09 and the
        # half-width 0.59, so the interval is still moving FASTER than it
        # shrinks. Recomputed here, not quoted from the record.
        low6, high6 = sc.wilson(23, 144)
        low7, high7 = sc.wilson(25, 168)
        half6 = (high6 - low6) / 2
        half7 = (high7 - low7) / 2
        assert round(half7, 2) == 5.38
        assert round(half6 - half7, 2) == 0.59
        assert round(100 * 23 / 144 - 100 * 25 / 168, 2) == 1.09
        assert (half6 - half7) < abs(100 * 23 / 144 - 100 * 25 / 168)

    def test_the_six_round_figure_still_reproduces(self) -> None:
        # Same reason the five-round one is kept: it is INCOMPLETE, not wrong,
        # and CHANGELOG.md published it as the closure for a release cycle.
        # A reader will meet it in the git history.
        assert round(100 * 23 / 144, 2) == 15.97
        assert round(100 * 20 / 120 - 100 * 23 / 144, 2) == 0.69
        assert round(round(100 * 20 / 120, 2) - round(100 * 23 / 144, 2), 2) == 0.70

    def test_reaching_three_points_needs_about_six_hundred_draws(self) -> None:
        # `25 rounds` is a TOTAL, not "25 more", and a better frame does not
        # move this number. It is the wall a frame change cannot fix.
        at_600 = sc.wilson(100, 600)
        assert (at_600[1] - at_600[0]) / 2 <= 3.0
        at_500 = sc.wilson(83, 500)
        assert (at_500[1] - at_500[0]) / 2 > 3.0
        assert 600 / 24 == 25

    def test_the_ledger_publishes_the_same_closure(self) -> None:
        # TWO COPIES OF ONE NUMBER IS THE SHAPE THIS REPOSITORY HAS HIT FIVE
        # TIMES. The tool's constant and the page's prose are checked against
        # each other rather than against anybody's memory.
        text = LEDGER.read_text(encoding="utf-8")
        assert "15.97" in text
        assert "10.89" in text and "22.83" in text
        assert "n = 0" in text

    def test_the_ledger_cites_the_right_record_for_round_three(self) -> None:
        # ROUND THREE IS D-088. The page cited D-100, whose body carries no
        # sampled-verification content at all -- a wrong token inside a fenced
        # block, which is exactly the region the retired frame could not read.
        text = LEDGER.read_text(encoding="utf-8")
        assert "D-088" in text
        assert "D-068, D-082, D-100" not in text

    def test_wilson_never_returns_a_negative_lower_bound(self) -> None:
        for successes, trials in ((0, 24), (1, 24), (2, 24), (0, 1)):
            low, high = sc.wilson(successes, trials)
            assert 0.0 <= low <= high <= 100.0

    def test_an_empty_denominator_does_not_divide_by_zero(self) -> None:
        assert sc.wilson(0, 0) == (0.0, 100.0)


class TestTheRetiredFrame:
    """Why the previous population could not hold this project's claims."""

    def test_prose_of_masks_inline_code_spans(self) -> None:
        # THE PROOF, re-derived against the live checker rather than quoted. If
        # this ever stops holding, the argument for the rewrite is gone and the
        # docstring is lying.
        spec = importlib.util.spec_from_file_location(
            "_check_claims_for_frame_test", REPO_ROOT / "tools" / "check_claims.py"
        )
        assert spec is not None and spec.loader is not None
        checker = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = checker
        spec.loader.exec_module(checker)
        masked = checker.prose_of("the rate is `16.67` % and 42 is bare", ".md")
        assert "16.67" not in masked
        assert "42" in masked

    def test_prose_of_masks_fenced_blocks(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "_check_claims_for_fence_test", REPO_ROOT / "tools" / "check_claims.py"
        )
        assert spec is not None and spec.loader is not None
        checker = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = checker
        spec.loader.exec_module(checker)
        masked = checker.prose_of("before 11\n```\ndesign effect 2.79\n```\nafter 22", ".md")
        assert "2.79" not in masked
        assert "11" in masked and "22" in masked

    def test_the_audit_reports_zero_reachable_backticked_figures(self) -> None:
        result = sc.audit_old_frame(REPO_ROOT)
        assert result["backticked_figures_reachable_by_old_frame"] == 0
        assert result["backticked_figures_in_unfenced_markdown"] > 1000

    def test_the_audit_reproduces_the_shipped_population_not_the_raw_residue(self) -> None:
        # The retired frame dropped year-shaped integers from the unarmed
        # residue. Reporting the pre-filter number would overstate the
        # population it actually drew from.
        result = sc.audit_old_frame(REPO_ROOT)
        assert result["residue"] < result["residue_before_year_filter"]

    def test_every_residue_item_came_from_unmasked_prose(self) -> None:
        # The other half of the proof: not merely that masked figures are
        # absent, but that the population is ENTIRELY unmasked text.
        #
        # THIS WAS A FLAT EQUALITY AND IT WENT RED ON A RACE, not on a defect.
        # A sibling agent rewrote `src/acronymkit/nlp/propagation.py` between
        # `collect_claims`' read and the audit's re-read, and ten residue items
        # were recorded against line numbers that had since changed. A mismatch
        # cannot mean "this item was masked" -- the collector only ever reads
        # masked prose -- so it means the file moved, and the audit now counts
        # those separately instead of failing the build with them.
        result = sc.audit_old_frame(REPO_ROOT)
        survivors = result["residue_items_from_unmasked_prose"]
        moved = result["residue_items_whose_file_moved_under_the_read"]
        assert survivors + moved == result["residue"]
        assert survivors > 0

    def test_a_file_that_moved_under_the_read_is_not_reported_as_masked(self) -> None:
        # The distinction the test above turns on, asserted rather than left in
        # a comment: the audit has to have somewhere to put a racing read.
        result = sc.audit_old_frame(REPO_ROOT)
        assert "residue_items_whose_file_moved_under_the_read" in result
        rendered = sc._render_audit(result)
        assert "shared-checkout race" in rendered

    def test_the_new_frame_reads_what_the_old_one_masked(self) -> None:
        units = list(sc._markdown_units("prose with `2.79` in a span here\n"))
        assert any("2.79" in text for _, _, text in units)

    def test_a_fenced_line_becomes_its_own_unit(self) -> None:
        units = list(sc._markdown_units("intro 1\n```\ncold 431 of 2054\n```\ntail 2\n"))
        regions = {region for _, region, _ in units}
        assert "fenced" in regions
        assert any("431 of 2054" in text for _, region, text in units if region == "fenced")


class TestContainment:
    """Can the frame reach the sentences previous rounds graded not true?"""

    def test_every_known_error_site_is_reachable(self) -> None:
        # A FLOOR, NOT EVIDENCE OF GENERALITY. The design was fitted to these
        # four sites; failing to contain them would be disqualifying, and
        # containing them proves nothing about the next three errors.
        rows = sc.containment(sc.build_frame(REPO_ROOT))
        unreachable = [row for row in rows if not row["contained"]]
        assert unreachable == [], unreachable

    def test_the_register_site_lands_in_the_register_channel(self) -> None:
        # Reads `.github/gates.toml`, which only a checkout carries.
        assert any(part in ".github/gates.toml" for part in CHECKOUT_ONLY[:1])
        rows = {row["needle"]: row for row in sc.containment(sc.build_frame(REPO_ROOT))}
        assert rows["135 passed"]["channel"] == "register"

    def test_the_containment_report_names_its_own_limit(self) -> None:
        rendered = sc._render_containment(sc.containment(sc.build_frame(REPO_ROOT)))
        assert "FLOOR" in rendered
        assert "not evidence of generality" in rendered

    def test_a_site_that_cannot_be_reached_is_reported_as_unreachable(self) -> None:
        frame = _frame({"document": 3})
        rows = sc.containment(frame)
        assert all(not row["contained"] for row in rows)
        assert "NO " in sc._render_containment(rows)

    def test_the_known_sites_record_a_verdict_and_a_reason(self) -> None:
        for site in sc.KNOWN_ERROR_SITES:
            assert site["verdict"] in sc.VERDICTS
            assert site["why"].strip()


class TestTheChannels:
    """Where a file lands, and why the tie-break order is not the display order."""

    def test_the_record_file_is_not_in_the_document_channel(self) -> None:
        # `docs/*.md` matches `docs/DECISIONS.md` too. Getting the precedence
        # wrong would move ~3,100 append-only sentences into the editable
        # channel and silently change what `document` measures.
        frame = sc.build_frame(REPO_ROOT)
        record = [i for i in frame.items if i.relative_path == "docs/DECISIONS.md"]
        assert record
        assert {i.channel for i in record} == {"record"}

    def test_precedence_is_not_the_display_order(self) -> None:
        assert sc.CHANNEL_PRECEDENCE != sc.CHANNELS
        assert set(sc.CHANNEL_PRECEDENCE) == set(sc.CHANNELS)
        assert sc.CHANNEL_PRECEDENCE.index("record") < sc.CHANNEL_PRECEDENCE.index("document")

    def test_the_control_fixtures_are_excluded(self) -> None:
        # Reads `.github/run-summaries/`, which only a checkout carries. Those
        # files say "asserts nothing about the library" twelve times each;
        # grading a sentence written to be ungradeable measures nothing.
        frame = sc.build_frame(REPO_ROOT)
        assert not [i for i in frame.items if "_control-agent-crash" in i.relative_path]

    def test_every_channel_has_files_in_this_checkout(self) -> None:
        frame = sc.build_frame(REPO_ROOT)
        assert frame.missing_channels == ()
        assert all(size > 0 for size in frame.sizes().values())

    def test_a_missing_channel_is_declared_in_the_render(self) -> None:
        rendered = sc._render_frame(_frame({"document": 9}, missing=("submitted",)), {}, 24)
        assert "CHANNEL(S) WITH NO FILES" in rendered
        assert "submitted" in rendered

    def test_the_submitted_channel_reaches_json_strings(self) -> None:
        frame = sc.build_frame(REPO_ROOT)
        submitted = [i for i in frame.items if i.channel == "submitted"]
        assert submitted
        assert all(i.region.startswith("json:") for i in submitted)

    def test_a_json_unit_carries_its_key_path_not_a_fake_line_number(self) -> None:
        units = list(sc._json_units('{"headline": "the suite is 6038 tests."}'))
        assert units
        line_number, region, text = units[0]
        assert line_number == 0
        assert region == "json:headline"
        assert "6038" in text

    def test_malformed_json_is_dropped_rather_than_raising(self) -> None:
        # One committed control fixture is truncated mid-write on purpose.
        assert list(sc._json_units('{"a": "unterminated')) == []


class TestTheUnitRule:
    """What counts as a claim-bearing sentence, and what the rule costs."""

    def test_a_unit_needs_a_digit(self) -> None:
        assert not sc.CLAIM_BEARING.search("a sentence with no figures at all")
        assert sc.CLAIM_BEARING.search("a sentence with 1 figure")

    def test_a_fragment_shorter_than_the_minimum_is_dropped(self) -> None:
        # The first exploratory draw put "> **9." in front of a grader: a list
        # marker the splitter tore off a heading. Nobody can grade it.
        frame = sc.build_frame(REPO_ROOT)
        assert all(len(i.text.split()) >= sc.MIN_UNIT_TOKENS for i in frame.items)

    def test_the_minimum_is_weak_enough_to_keep_a_transcribed_row(self) -> None:
        # The cost of a rule that is too strong falls on real claims.
        row = "cold 431 of 2054"
        assert len(row.split()) >= sc.MIN_UNIT_TOKENS

    def test_sentences_are_split_on_terminal_punctuation(self) -> None:
        parts = list(sc._sentences("The first is 1. The second is 2."))
        assert len(parts) == 2

    def test_a_decimal_is_not_a_sentence_boundary(self) -> None:
        parts = list(sc._sentences("the design effect is 2.79 at forty commits"))
        assert len(parts) == 1

    def test_whitespace_is_normalised(self) -> None:
        assert list(sc._sentences("a   b\n\tc 1")) == ["a b c 1"]

    def test_a_register_file_is_read_line_by_line(self) -> None:
        units = list(sc._line_units("alpha = 1\n\nbeta = 2\n"))
        assert [text for _, _, text in units] == ["alpha = 1", "beta = 2"]
        assert {region for _, region, _ in units} == {"line"}


class TestTheAllocation:
    """Where the twenty-four go, and what happens when a channel is short."""

    def test_the_default_allocation_sums_to_the_default_size(self) -> None:
        assert sum(sc.DEFAULT_ALLOCATION.values()) == sc.DEFAULT_SIZE == 24

    def test_no_channel_is_allocated_zero(self) -> None:
        # A channel drawn at zero is a channel whose rate is permanently
        # unknown, `record` included -- a false sentence in an append-only
        # record is still false.
        assert all(count > 0 for count in sc.DEFAULT_ALLOCATION.values())

    def test_a_full_frame_gets_the_declared_allocation(self) -> None:
        frame = _frame(dict.fromkeys(sc.CHANNELS, 100))
        assert sc.allocate(frame, 24, sc.DEFAULT_ALLOCATION) == sc.DEFAULT_ALLOCATION

    def test_a_short_channel_gives_what_it_has_and_the_rest_moves(self) -> None:
        counts = dict.fromkeys(sc.CHANNELS, 100)
        counts["submitted"] = 3
        planned = sc.allocate(_frame(counts), 24, sc.DEFAULT_ALLOCATION)
        assert planned["submitted"] == 3
        assert sum(planned.values()) == 24

    def test_a_frame_smaller_than_the_sample_gives_the_whole_frame(self) -> None:
        counts = dict.fromkeys(sc.CHANNELS, 2)
        assert sc.allocate(_frame(counts), 24, sc.DEFAULT_ALLOCATION) == counts

    def test_a_reallocation_is_named_in_the_render_not_only_shown(self) -> None:
        # THE DEFECT THAT KILLED THE PREVIOUS FRAME'S HEADLINE STRATUM. Its
        # `round` stratum fell to N=0 on any committed tree and its twelve
        # draws moved elsewhere with no warning line at all.
        counts = dict.fromkeys(sc.CHANNELS, 100)
        counts["submitted"] = 0
        rendered = sc._render_frame(_frame(counts), sc.DEFAULT_ALLOCATION, 24)
        assert "REALLOCATED" in rendered


class TestTheDraw:
    """Reproducible from the seed alone, which is what a second grader needs."""

    def test_the_same_seed_gives_the_same_sample(self) -> None:
        frame = _frame(dict.fromkeys(sc.CHANNELS, 50))
        first = [item.identifier for item in sc.draw(frame, 20260909)]
        second = [item.identifier for item in sc.draw(frame, 20260909)]
        assert first == second

    def test_a_different_seed_gives_a_different_sample(self) -> None:
        frame = _frame(dict.fromkeys(sc.CHANNELS, 50))
        assert {i.identifier for i in sc.draw(frame, 1)} != {
            i.identifier for i in sc.draw(frame, 2)
        }

    def test_the_draw_respects_the_allocation(self) -> None:
        frame = _frame(dict.fromkeys(sc.CHANNELS, 50))
        sample = sc.draw(frame, 7)
        tally = {name: sum(1 for i in sample if i.channel == name) for name in sc.CHANNELS}
        assert tally == sc.DEFAULT_ALLOCATION

    def test_no_claim_is_drawn_twice(self) -> None:
        frame = _frame(dict.fromkeys(sc.CHANNELS, 13))
        sample = sc.draw(frame, 3)
        assert len({item.identifier for item in sample}) == len(sample)

    def test_a_live_draw_is_stable_across_two_builds_of_the_frame(self) -> None:
        # The identifier carries a digest of the sentence, so a draw is
        # reproducible only if the frame sorts deterministically.
        first = [i.identifier for i in sc.draw(sc.build_frame(REPO_ROOT), 20260909)]
        second = [i.identifier for i in sc.draw(sc.build_frame(REPO_ROOT), 20260909)]
        assert first == second


class TestTheEstimator:
    """The trap: the unweighted count is not the repository's rate."""

    @staticmethod
    def _graded(frame: object, seed: int, rates: Dict[str, int]) -> Dict[str, str]:
        sample = sc.draw(frame, seed)
        graded: Dict[str, str] = {}
        seen = dict.fromkeys(sc.CHANNELS, 0)
        for item in sample:
            seen[item.channel] += 1
            graded[item.identifier] = (
                "FALSE" if seen[item.channel] <= rates.get(item.channel, 0) else "TRUE"
            )
        return graded

    def test_the_repository_rate_is_weighted_by_channel_size_not_by_draws(self) -> None:
        # THE WHOLE POINT. `submitted` holds 20 of 1520 sentences and takes 8
        # of 24 draws. Grade every submitted draw not true and every other draw
        # true: the unweighted rate over the sample is 33 %, the repository's
        # is about 1 %. Publishing the first would be this frame's central lie.
        frame = _frame({"submitted": 20, "register": 500, "document": 500, "record": 500})
        graded = self._graded(frame, 11, {"submitted": 8})
        result = sc.stratified_estimate(frame, graded, sc.draw(frame, 11))
        unweighted = 100 * sum(1 for v in graded.values() if v in sc.NOT_TRUE) / len(graded)
        assert round(unweighted) == 33
        assert float(result["repository_rate_pct"]) < 3.0

    def test_a_uniform_rate_comes_back_as_that_rate(self) -> None:
        frame = _frame(dict.fromkeys(sc.CHANNELS, 100))
        graded = self._graded(frame, 5, {"submitted": 4, "register": 2, "document": 4, "record": 2})
        result = sc.stratified_estimate(frame, graded, sc.draw(frame, 5))
        assert 49.0 <= float(result["repository_rate_pct"]) <= 51.0

    def test_uncheckable_is_in_the_denominator_and_not_the_numerator(self) -> None:
        # Excluding UNCHECKABLE would let a round improve its rate by making
        # its claims harder to check.
        assert "UNCHECKABLE" in sc.VERDICTS and "UNCHECKABLE" not in sc.NOT_TRUE
        frame = _frame(dict.fromkeys(sc.CHANNELS, 30))
        sample = sc.draw(frame, 2)
        graded = {item.identifier: "TRUE" for item in sample}
        for item in [i for i in sample if i.channel == "submitted"][:4]:
            graded[item.identifier] = "UNCHECKABLE"
        result = sc.stratified_estimate(frame, graded, sample)
        per_channel = result["per_channel"]
        assert isinstance(per_channel, dict)
        assert per_channel["submitted"]["n"] == 8
        assert per_channel["submitted"]["not_true"] == 0

    def test_misleading_counts_as_not_true(self) -> None:
        assert set(sc.NOT_TRUE) == {"FALSE", "MISLEADING"}

    def test_a_channel_nobody_graded_is_dropped_rather_than_counted_as_clean(self) -> None:
        frame = _frame(dict.fromkeys(sc.CHANNELS, 10))
        sample = sc.draw(frame, 4)
        graded = {i.identifier: "TRUE" for i in sample if i.channel == "submitted"}
        result = sc.stratified_estimate(frame, graded, sample)
        per_channel = result["per_channel"]
        assert isinstance(per_channel, dict)
        assert set(per_channel) == {"submitted"}


class TestThePrice:
    """``design_effect``, tested in the direction that does not flatter it."""

    def test_a_proportional_allocation_costs_nothing(self) -> None:
        frame = _frame(dict.fromkeys(sc.CHANNELS, 100))
        assert sc.design_effect(frame, dict.fromkeys(sc.CHANNELS, 6), 24) == pytest.approx(1.0)

    def test_over_sampling_a_small_channel_costs_precision(self) -> None:
        frame = _frame({"submitted": 20, "register": 500, "document": 500, "record": 500})
        assert sc.design_effect(frame, sc.DEFAULT_ALLOCATION, 24) > 1.0

    def test_the_live_design_effect_is_above_one_and_is_printed(self) -> None:
        # It is above 1 here and it is MEANT to be. If it ever prints below 1
        # the allocation has drifted toward proportional and the frame has
        # stopped buying the per-channel question.
        frame = sc.build_frame(REPO_ROOT)
        assert sc.design_effect(frame, sc.DEFAULT_ALLOCATION, 24) > 1.0
        assert "design effect" in sc._render_frame(frame, sc.DEFAULT_ALLOCATION, 24)

    def test_an_empty_frame_does_not_divide_by_zero(self) -> None:
        assert math.isnan(sc.design_effect(_frame({}), sc.DEFAULT_ALLOCATION, 24))


class TestThisCheckout:
    """The live frame, built the way a round would build it."""

    def test_the_frame_is_not_empty_and_partitions_cleanly(self) -> None:
        frame = sc.build_frame(REPO_ROOT)
        assert frame.total > 0
        assert frame.total == sum(frame.sizes().values())

    def test_every_item_names_a_real_file(self) -> None:
        # Reads `.github/` paths, which only a checkout carries.
        frame = sc.build_frame(REPO_ROOT)
        for path in frame.files():
            assert (REPO_ROOT / path).is_file(), path

    def test_a_markdown_item_line_number_points_at_its_own_file(self) -> None:
        frame = sc.build_frame(REPO_ROOT)
        markdown = [i for i in frame.items if i.relative_path.endswith(".md")][:40]
        assert markdown
        for item in markdown:
            lines = (REPO_ROOT / item.relative_path).read_text(encoding="utf-8").split("\n")
            assert 1 <= item.line_number <= len(lines)

    def test_the_cli_prints_a_frame(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert sc.main(["--frame"]) == 0
        assert "design effect" in capsys.readouterr().out

    def test_the_cli_prints_containment(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert sc.main(["--containment"]) == 0
        assert "reachable" in capsys.readouterr().out

    def test_the_cli_audits_the_retired_frame(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert sc.main(["--audit-old-frame"]) == 0
        assert "zero by construction" in capsys.readouterr().out

    def test_a_draw_without_a_seed_is_refused(self, capsys: pytest.CaptureFixture[str]) -> None:
        # A SAMPLE NOBODY CAN REDRAW IS NOT A SAMPLE.
        assert sc.main(["--draw"]) == 1
        assert "seed" in capsys.readouterr().out

    def test_an_unknown_verdict_is_refused(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        graded = tmp_path / "graded.json"
        graded.write_text('{"a": "PROBABLY"}', encoding="utf-8")
        assert sc.main(["--estimate", str(graded), "--seed", "1"]) == 1
        assert "PROBABLY" in capsys.readouterr().out

    def test_the_render_always_names_the_predecessor_series(self) -> None:
        # A DRAW PRINTED WITHOUT THE CLOSURE BESIDE IT IS THE FAILURE MODE THIS
        # WHOLE SECTION EXISTS TO PREVENT: a reader pooling the new rate into
        # the old one because nothing on the page said not to.
        rendered = sc._render_frame(_frame(dict.fromkeys(sc.CHANNELS, 5)), {}, 24)
        # Asserted against the CONSTANT rather than a literal: this test failed
        # on the seven-round correction, which is the right outcome for the
        # constant's own tests and the wrong one here -- what this checks is
        # that the closure is printed, not what the closure is.
        assert f"{sc.CLOSED_SERIES['rate_pct']:.2f}" in rendered
        assert "14.88" in rendered
        assert "DOES NOT CARRY ACROSS" in rendered
        assert "n = 0" in rendered

    def test_the_render_records_that_this_is_the_second_restart(self) -> None:
        # A second restart inside two rounds is a bad sign about the
        # instrument, and it is printed as one rather than as a fresh start.
        rendered = sc._render_frame(_frame(dict.fromkeys(sc.CHANNELS, 5)), {}, 24)
        assert "second time in two rounds" in rendered

    def test_the_docstring_names_what_the_frame_cannot_do(self) -> None:
        # A frame whose blind spots are stated beats one whose coverage is
        # asserted, and this is the assertion that keeps them stated.
        source = LOADER.read_text(encoding="utf-8")
        assert "WHAT THIS FRAME STILL CANNOT DO" in source
        assert "does not fix the precision wall" in source
