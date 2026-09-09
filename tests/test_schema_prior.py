"""The schema-prior transfer harness, pinned — because a null result is easy to fake.

``bench/run_schema_prior.py`` answers a standing unknown in the negative: a
frequency prior harvested from a governed schema does **not** transfer to the
prose disambiguation arm. A negative result is the cheapest kind to manufacture
by accident — a harvest rule that emits nothing, a key normalisation that never
matches, a control that cannot report a difference — so the parts of the
derivation that could produce a false null are pinned here rather than trusted.

What this file pins, and why each item is here
----------------------------------------------
* **Every harvest construction emits what its name says**, on hand fixtures with
  the shapes the schema corpora actually contain. A construction that silently
  emitted nothing would produce exactly the reported finding.
* **The key namespace is the library's.** Keys go through
  ``acronymkit.disambiguation._short_form_key``, the function
  ``ExpansionDictionary`` itself indexes by. A bridge invented in the runner
  would make an overlap census measure the bridge.
* **A prior that covers nothing IS the tie-break.** With no key hit, every
  candidate carries the same smoothed mass, so the prior arm's prediction must
  be byte-identical to the constant-scorer floor's. The runner reports a floor
  arm on that basis and the claim is a derivation, so it is proved rather than
  measured.
* **An unseparated prior cannot re-rank at any blend weight**, which is what
  makes ``blend_disagreements_outside_fired`` an assertion rather than a
  statistic.
* **The permutation control can report a difference and can report none.** A
  control that always says "no difference" cannot falsify anything, and it is
  the one instrument here whose inertness would look exactly like a finding.
* **The reproduction check can fail.** Three arms pin against
  ``bench/results.json``; a checker that returned ``ok`` for a wrong value would
  make the harness's own validity claim empty.
* **The census separates its three levels**, including the case a real corpus
  never shows: a short form with one candidate, where "matched" and "separates"
  come apart.

Nothing here reads a corpus, reaches the network, or times anything.
"""

from __future__ import annotations

import collections
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "bench" / "run_schema_prior.py"


def _load(path: Path, name: str) -> ModuleType:
    """Import a script by path; ``bench/`` is a directory of scripts, not a package."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if not RUNNER.is_file():  # pragma: no cover - only reachable in an extracted sdist
    # The sdist ships ``tests/`` and deliberately not ``bench/*.py``. Skipped
    # **before** the load rather than by a ``pytestmark``, because ``pytestmark``
    # runs at collection and the import below runs earlier -- which is how a
    # module of this shape turns an absent file into a collection error instead
    # of a skip.
    pytest.skip(
        "bench/run_schema_prior.py is absent; not a source checkout",
        allow_module_level=True,
    )

prior_runner = _load(RUNNER, "bench_run_schema_prior")


class Pair:
    """The two fields :func:`harvest` reads off an ``IdentifierCaptionPair``."""

    def __init__(self, identifier: str, caption: str) -> None:
        self.identifier = identifier
        self.caption = caption
        self.author = "fixture"


def _scored(expansion: str, overlap: float = 0.0) -> object:
    """One candidate, with only the two fields any scorer here reads populated."""
    return prior_runner.Scored(expansion, overlap, 0.0, 0.0, overlap, 1, 0, {})


def _record(acronym: str, gold: str, candidates: List[Tuple[str, float]]) -> object:
    """One decomposed instance built from literals rather than from a corpus."""
    return prior_runner.Decomposed(
        f"FIX-{acronym}",
        acronym,
        acronym.upper(),
        gold,
        [_scored(expansion, overlap) for expansion, overlap in candidates],
        [],
        (),
        False,
    )


def _prior(mapping: Dict[str, Dict[Tuple[str, ...], int]]) -> Dict[str, object]:
    """A prior literal, in the runner's ``{key: Counter}`` shape."""
    return {key: collections.Counter(counts) for key, counts in mapping.items()}


# ---------------------------------------------------------------------------
# the harvest: every construction emits what its name says
# ---------------------------------------------------------------------------
class TestTheHarvestConstructions:
    """A construction that emitted nothing would produce the reported finding."""

    def test_token_word_aligns_a_snake_case_identifier_to_its_caption(self) -> None:
        prior, voted, votes = prior_runner.harvest([Pair("unit_number", "Unit Num")], "token_word")
        assert voted == 1
        assert votes >= 1
        assert prior["NUMBER"][("num",)] == 1

    def test_identifier_keys_on_the_whole_name_and_values_on_the_whole_caption(self) -> None:
        prior, _, _ = prior_runner.harvest([Pair("nature_of_call", "Nature of Call")], "identifier")
        assert prior["NATUREOFCALL"][("nature", "of", "call")] == 1

    def test_initialism_all_takes_every_caption_word(self) -> None:
        prior, _, _ = prior_runner.harvest(
            [Pair("nature_of_call", "Nature of Call")], "initialism_all"
        )
        assert prior["NOC"][("nature", "of", "call")] == 1

    def test_initialism_content_drops_function_words(self) -> None:
        prior, _, _ = prior_runner.harvest(
            [Pair("nature_of_call", "Nature of Call")], "initialism_content"
        )
        assert prior["NC"][("nature", "of", "call")] == 1

    def test_initialism_content_does_not_double_count_when_it_agrees(self) -> None:
        # No function word, so the two initialisms coincide and only
        # ``initialism_all`` may record the vote. Double counting here would
        # inflate every frequency in the union prior by an amount that depends
        # on the caption's grammar.
        pairs = [Pair("gross_sales", "Gross Sales")]
        every, _, _ = prior_runner.harvest(pairs, "initialism_all")
        content, voted, votes = prior_runner.harvest(pairs, "initialism_content")
        assert every["GS"][("gross", "sales")] == 1
        assert content == {}
        assert (voted, votes) == (0, 0)

    def test_initialism_window_reaches_a_multi_word_expansion_under_an_acronym_key(self) -> None:
        prior, _, _ = prior_runner.harvest(
            [Pair("ytd_gross_sales", "Year To Date Gross Sales")], "initialism_window"
        )
        assert prior["YTD"][("year", "to", "date")] == 1
        assert prior["GS"][("gross", "sales")] == 1

    def test_windows_respect_their_declared_bounds(self) -> None:
        words = tuple("abcdefgh"[index] for index in range(8))
        lengths = {len(window) for _, window in prior_runner._windows(words)}
        assert lengths == set(
            range(prior_runner.WINDOW_MIN_WORDS, prior_runner.WINDOW_MAX_WORDS + 1)
        )
        assert prior_runner._windows(("solo",)) == []

    def test_an_unknown_construction_is_refused_rather_than_silently_empty(self) -> None:
        with pytest.raises(ValueError, match="unknown construction"):
            prior_runner.harvest([Pair("a_b", "A B")], "no_such_rule")

    def test_keys_are_the_librarys_own_short_form_key(self) -> None:
        # ``ExpansionDictionary`` indexes by ``_short_form_key``. If the runner
        # normalised keys any other way, the overlap census would be measuring a
        # bridge the runner invented.
        prior, _, _ = prior_runner.harvest([Pair("n_a_s_a", "N.A.S.A.")], "identifier")
        assert set(prior) == {prior_runner._d._short_form_key("n_a_s_a")}


# ---------------------------------------------------------------------------
# the floor: a prior that covers nothing IS the tie-break
# ---------------------------------------------------------------------------
class TestTheFloorIsADerivation:
    """The runner reports a floor arm on the strength of this identity."""

    def test_an_empty_prior_predicts_exactly_what_the_constant_scorer_predicts(self) -> None:
        records = [
            _record("MS", "multiple sclerosis", [("multiple sclerosis", 0.4), ("Microsoft", 0.1)]),
            _record("IP", "internet protocol", [("internet protocol", 0.0), ("intellectual", 0.9)]),
        ]
        words_of = {c.expansion: (c.expansion,) for r in records for c in r.candidates}
        masses, keys, values = prior_runner.masses(records, {}, words_of)
        assert (keys, values) == (2, 4)
        for record, mass in zip(records, masses):
            assert len(set(mass.values())) == 1
            assert prior_runner.predict(
                record, prior_runner._scorer(mass), inline="off"
            ) == prior_runner.predict(record, prior_runner.CONSTANT, inline="off")

    def test_an_unseparated_prior_cannot_re_rank_at_any_blend_weight(self) -> None:
        # This is what makes ``blend_disagreements_outside_fired`` an assertion
        # rather than a statistic: the prior term is a constant added to every
        # candidate, so the sort cannot move.
        record = _record("MS", "Microsoft", [("multiple sclerosis", 0.4), ("Microsoft", 0.9)])
        words_of = {c.expansion: (c.expansion,) for c in record.candidates}
        masses, _, _ = prior_runner.masses([record], {}, words_of)
        context = prior_runner.predict(record, prior_runner.OVERLAP_ONLY, inline="off")
        for step in range(21):
            weight = step / 20
            blended = prior_runner.predict(
                record, prior_runner._blend(weight, masses[0]), inline="off"
            )
            if weight:
                assert blended == context


# ---------------------------------------------------------------------------
# the permutation control, in both directions
# ---------------------------------------------------------------------------
class TestThePermutationControlCanFail:
    """A control that always reports no difference cannot falsify anything."""

    def _records(self) -> Tuple[List[object], Dict[str, Tuple[str, ...]]]:
        """Twenty two-way instances whose gold is the same expansion each time."""
        records = [
            _record("XX", "right answer", [("right answer", 0.0), ("wrong answer", 0.0)])
            for _ in range(20)
        ]
        words_of = {"right answer": ("right",), "wrong answer": ("wrong",)}
        return records, words_of

    def test_an_informative_prior_beats_its_own_permutation(self) -> None:
        records, words_of = self._records()
        masses, _, _ = prior_runner.masses(records, _prior({"XX": {("right",): 500}}), words_of)
        measured = sum(
            prior_runner.predict(record, prior_runner._scorer(mass), inline="off") == record.gold
            for record, mass in zip(records, masses)
        )
        control = prior_runner.permutation_control(records, masses, 0.0)
        assert measured == len(records)
        assert control["accuracy_permuted_prior_only_max"] < 100.0

    def test_a_uniform_prior_matches_its_own_permutation_exactly(self) -> None:
        # The other direction, and the one that matters: a control that
        # manufactured a difference out of a prior with no information would
        # make every measured margin unreadable.
        records, words_of = self._records()
        masses, _, _ = prior_runner.masses(records, {}, words_of)
        measured = prior_runner.pct(
            sum(
                prior_runner.predict(record, prior_runner._scorer(mass), inline="off")
                == record.gold
                for record, mass in zip(records, masses)
            ),
            len(records),
        )
        control = prior_runner.permutation_control(records, masses, 0.0)
        assert control["accuracy_permuted_prior_only_min"] == measured
        assert control["accuracy_permuted_prior_only_max"] == measured
        assert control["permutations"] == prior_runner.PERMUTATIONS


# ---------------------------------------------------------------------------
# the census: three levels, and the case a real corpus never shows
# ---------------------------------------------------------------------------
class TestTheCensusLevels:
    """ "Present", "matched" and "separates" are three different questions."""

    def test_a_present_key_with_no_matching_value_is_a_collision_not_coverage(self) -> None:
        instances = [_Instance("MS")]
        diction = {"MS": ["multiple sclerosis", "Microsoft"]}
        words_of = prior_runner.candidate_words(diction)
        row = prior_runner.census(
            instances, diction, _prior({"MS": {("mild", "steel"): 9}}), words_of
        )
        assert row["short_forms_in_prior"] == 1
        assert row["short_forms_with_matched_candidate"] == 0
        assert row["short_forms_in_prior_with_no_matched_candidate"] == 1
        assert row["instances_where_prior_separates"] == 0

    def test_matched_and_separates_come_apart_on_a_one_candidate_short_form(self) -> None:
        # On the measured corpus every short form carries two or more
        # candidates, so the two counts are equal there and the equality reads
        # like a property. It is not one.
        instances = [_Instance("MS")]
        diction = {"MS": ["multiple sclerosis"]}
        words_of = prior_runner.candidate_words(diction)
        counts = {("multiple", "sclerosis"): 4}
        row = prior_runner.census(instances, diction, _prior({"MS": counts}), words_of)
        assert row["instances_with_matched_candidate"] == 1
        assert row["instances_where_prior_separates"] == 0

    def test_two_distinct_nonzero_candidates_is_strictly_narrower_than_separation(self) -> None:
        instances = [_Instance("MS")]
        diction = {"MS": ["multiple sclerosis", "Microsoft"]}
        words_of = prior_runner.candidate_words(diction)
        one_side = _prior({"MS": {("multiple", "sclerosis"): 4}})
        both = _prior({"MS": {("multiple", "sclerosis"): 4, ("microsoft",): 1}})
        assert (
            prior_runner.census(instances, diction, one_side, words_of)[
                "instances_where_prior_separates"
            ]
            == 1
        )
        assert (
            prior_runner.census(instances, diction, one_side, words_of)[
                "instances_with_two_distinct_nonzero_candidates"
            ]
            == 0
        )
        assert (
            prior_runner.census(instances, diction, both, words_of)[
                "instances_with_two_distinct_nonzero_candidates"
            ]
            == 1
        )

    def test_phrase_presence_ignores_the_key_entirely(self) -> None:
        # The figure that separates "the key spaces do not line up" from "the
        # schema does not contain these phrases at all".
        instances = [_Instance("MS")]
        diction = {"MS": ["multiple sclerosis", "Microsoft"]}
        words_of = prior_runner.candidate_words(diction)
        elsewhere = _prior({"ZZ": {("multiple", "sclerosis"): 1}})
        row = prior_runner.census(instances, diction, elsewhere, words_of)
        assert row["short_forms_in_prior"] == 0
        assert row["candidates_present_as_any_schema_value"] == 1


class _Instance:
    """The one field :func:`census` reads off a ``DisambiguationInstance``."""

    def __init__(self, acronym: str) -> None:
        self.acronym = acronym


# ---------------------------------------------------------------------------
# the contract loss, the saturation control, and the typed accessor
# ---------------------------------------------------------------------------
class TestTheSupportingMeasurements:
    """Small derivations that a report line would otherwise assert."""

    def test_the_governed_contract_keeps_one_value_per_token(self) -> None:
        prior = _prior({"NOC": {("nature", "of", "call"): 9, ("network", "operations"): 2}})
        diction = {"MS": ["multiple sclerosis"]}
        arity = prior_runner.contract_arity(diction, prior, prior_runner.candidate_words(diction))
        assert arity["governed_dictionary_rows_built"] == 1
        assert arity["governed_dictionary_rows_resolvable"] == 1
        assert arity["schema_prior_values_lost_to_the_governed_contract"] == 1
        assert arity["schema_prior_keys_with_two_or_more_values"] == 1

    def test_saturation_counts_the_letter_space_it_names(self) -> None:
        space = prior_runner.saturation(_prior({"AB": {("a", "b"): 1}, "A1": {("a",): 1}}))
        assert space["letter_space_2_size"] == 676
        assert space["letter_space_2_covered"] == 1
        assert space["letter_space_1_covered"] == 0

    def test_the_typed_accessor_refuses_a_non_number(self) -> None:
        assert prior_runner.number({"a": 1.5}, "a") == 1.5
        with pytest.raises(TypeError):
            prior_runner.number({"a": "1.5"}, "a")
        # ``bool`` is an ``int`` in Python and every verdict field here is a
        # bool, so formatting one into an accuracy column must be an error.
        with pytest.raises(TypeError):
            prior_runner.number({"a": True}, "a")


# ---------------------------------------------------------------------------
# the reproduction check, shown capable of failing
# ---------------------------------------------------------------------------
class TestTheReproductionCheck:
    """Three arms pin against results.json; the checker must be able to say no."""

    def test_it_passes_on_the_saved_figures_and_fails_on_a_moved_one(self) -> None:
        import json

        runs = json.loads((REPO_ROOT / "bench" / "results.json").read_text(encoding="utf-8"))[
            "runs"
        ]
        good = {arm: float(runs[run_id][field]) for run_id, field, arm in prior_runner.REPRODUCES}
        assert all(ok for _, _, _, ok in prior_runner.reproductions(good))

        moved = dict(good)
        first_arm = prior_runner.REPRODUCES[0][2]
        moved[first_arm] = good[first_arm] + 1.0
        verdicts = prior_runner.reproductions(moved)
        assert verdicts[0][3] is False
        assert all(ok for _, _, _, ok in verdicts[1:])


# ---------------------------------------------------------------------------
# the saved verdict is arithmetic over the pre-registered constants
# ---------------------------------------------------------------------------
class TestTheSavedVerdict:
    """A verdict field named "preregistered" must be the pre-registered rule."""

    def test_the_saved_run_fails_both_halves_of_the_declared_rule(self) -> None:
        import json

        path = REPO_ROOT / "bench" / "results.json"
        entry = json.loads(path.read_text(encoding="utf-8"))["runs"].get(
            "schema_prior.sdu21.transfer"
        )
        if entry is None:  # pragma: no cover - only before the runner has been saved
            pytest.skip("schema_prior.sdu21.transfer has not been saved")
        assert entry["preregistered_transfer_accuracy"] == (
            prior_runner.PREREGISTERED_TRANSFER_ACCURACY
        )
        assert entry["preregistered_control_margin"] == prior_runner.PREREGISTERED_CONTROL_MARGIN
        transfers = (
            entry["blend_best_accuracy_tuning_split"]
            >= prior_runner.PREREGISTERED_TRANSFER_ACCURACY
            and entry["blend_minus_permuted_control_points"]
            >= prior_runner.PREREGISTERED_CONTROL_MARGIN
        )
        assert entry["transfers_under_preregistered_rule"] is transfers
        assert entry["reproduces_gated_figures"] is True
