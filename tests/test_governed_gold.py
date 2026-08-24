"""The governed-gold scorer, pinned — because a scorer nobody tests measures whatever it does.

``bench/run_governed_gold.py`` produces the governed subsystem's first accuracy
figures, and those figures now sit in ``docs/EVALUATION.md`` behind claim
citations. A published number is only as trustworthy as the code that derived
it, and the derivation here is not obvious: it turns two strings into a set of
integer cut positions, and every judgement about what counts as a boundary is a
line in that translation.

What this file pins, and why each item is here
----------------------------------------------
* **The admission rule, exactly as documented.** It is the whole defence of the
  measurement: equal alphanumerics plus whitespace means only cut placement can
  differ, so a disagreement is a segmentation disagreement and nothing else. An
  admission rule that quietly widened would turn the exact-match figure into a
  figure about abbreviation expansion, which is a different and much harder
  task -- and publishing one as the other is precisely the mistake the August
  2026 audit killed in section 0.
* **Punctuation is a cut.** ``Available-for-Sale`` is three words. Scoring only
  whitespace was the first draft, and it cost the SEC arm three points of exact
  match by counting every hyphen in the taxonomy as a segmentation error.
* **The ceiling is a real bound.** Boundary recall may never exceed the share of
  gold cuts the identifier actually marks. If it could, the ceiling would be
  decoration; the whole point of printing it in the same table is that it bounds
  the number beside it.
* **One definition of "separated".** ``shape_of`` and ``is_marked`` disagreed in
  the first draft over a *leading* underscore -- Socrata prefixes a field name
  starting with a digit -- so ``_casenumber`` was snake_lower in one table and
  unmarked in the other. Two notions of the same word is how two tables in one
  report come to contradict each other.
* **The split is stable.** ``portal_half`` uses a digest and not :func:`hash`,
  whose string seed is randomised per process. A split that moves between runs
  is not a split.
* **Licence URLs are not badges.** The runner records a licence URL and a read
  date for each corpus, and those are checked against the same badge rule
  ``tools/splits.py`` applies to the manifest. Operating rule 4 does not stop
  applying because the URL lives in a runner instead of a TOML file.

Nothing here reaches the network. The fetchers are exercised only for their
failure path, with :mod:`urllib` stubbed, because a test that needed the SEC to
be up would be a test that is red for reasons that are not the code's.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "bench" / "run_governed_gold.py"
SPLITS_TOOL = REPO_ROOT / "tools" / "splits.py"


def _load(path: Path, name: str) -> ModuleType:
    """Import a script by path.

    ``bench/`` and ``tools/`` are directories of scripts, not packages, and
    making one importable for a test's convenience would change the shape of
    the thing under test. Same mechanism as ``tests/test_splits_manifest.py``.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before execution: ``@dataclass`` resolves annotations through
    # ``sys.modules[cls.__module__]`` while the class body is still running.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pytestmark = pytest.mark.skipif(not RUNNER.is_file(), reason="not a source checkout")

gold = _load(RUNNER, "_governed_gold_under_test")


# ---------------------------------------------------------------------------
# the admission rule
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "identifier, caption",
    [
        ("incident_number", "Incident Number"),
        ("ContractWithCustomer", "Contract with Customer"),
        ("AccountsPayableCurrent", "Accounts Payable, Current"),
        ("_0_4_years", "0-4 years"),
        ("DebtSecuritiesAvailableForSale", "Debt Securities, Available-for-Sale"),
        # Rule 2 is literal: whitespace, not a cut. A caption with one
        # alphanumeric word still adjudicates -- it asserts no cut belongs.
        ("total", "Total (#)"),
    ],
)
def test_admits_pairs_that_differ_only_in_cuts(identifier: str, caption: str) -> None:
    assert gold.admits(identifier, caption)


@pytest.mark.parametrize(
    "identifier, caption, why",
    [
        ("qty", "Quantity Ordered", "the caption expands; that is the catalog's job"),
        ("cust_id", "Customer Identifier", "an abbreviation, not a cut"),
        ("date_time", "Date_Time", "no whitespace, so there is nothing to adjudicate"),
        ("date", "Date", "no whitespace"),
        # Rule 2 is literal in both directions, and this is the cost: a caption
        # cut only by hyphens is refused even though it does place cuts. The
        # rule is stated as written rather than widened after seeing the data.
        ("AvailableForSale", "Available-for-Sale", "hyphens are not whitespace"),
        ("incident_number", "Incident No", "alphanumerics differ"),
        ("incident_number", "Incident Numbers", "alphanumerics differ by one character"),
        ("", "Some Caption", "no identifier"),
        ("something", "", "no caption"),
        ("___", "  ", "no alphanumerics at all"),
    ],
)
def test_refuses_pairs_that_differ_by_more_than_cuts(
    identifier: str, caption: str, why: str
) -> None:
    assert not gold.admits(identifier, caption), why


def test_admission_ignores_case_and_punctuation_but_not_characters() -> None:
    assert gold.admits("TXNAPPLNTDOB", "txn applnt dob")
    assert not gold.admits("TXNAPPLNTDOB", "txn applnt d o b x")


# ---------------------------------------------------------------------------
# cuts
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text, expected",
    [
        ("Incident Number", {8}),
        ("incident_number", {8}),
        # Punctuation is a cut, not only whitespace. Three words.
        ("Available-for-Sale", {9, 12}),
        ("Accounts Payable, Current", {8, 15}),
        # Leading and trailing punctuation cut nothing: there is no word before
        # the first character or after the last.
        ("  Total  ", set()),
        ("(#) Total", set()),
        ("$100,000- under $150,000", {3, 6, 11, 14}),
        ("", set()),
        ("Total", set()),
    ],
)
def test_cuts_are_positions_in_the_alphanumeric_stream(text: str, expected: set) -> None:
    assert gold.cuts(text) == expected


def test_a_run_of_punctuation_is_one_cut() -> None:
    assert gold.cuts("Birds -- In Shelter") == gold.cuts("Birds In Shelter")


# ---------------------------------------------------------------------------
# signals and marks
# ---------------------------------------------------------------------------
def test_each_signal_fires_where_the_splitter_documents_it() -> None:
    assert gold.signals("TXN_APPLNT")["separator"] == {3}
    assert gold.signals("creditBureau")["camel_case"] == {6}
    assert gold.signals("ETLTimestamp")["acronym_run"] == {3}
    assert gold.signals("address2line1")["letter_digit"] == {7, 8, 12}


def test_a_leading_separator_marks_nothing() -> None:
    """Socrata prefixes a field name that starts with a digit with ``_``.

    There is no word before it, so it is not a boundary between two words, and
    counting it as one would file every such field under ``marked``.
    """
    assert gold.signals("_casenumber")["separator"] == set()
    assert not gold.is_marked(gold.signals("_casenumber"))
    assert gold.signals("_0_24_pop")["separator"] == {1, 3}


def test_digits_alone_do_not_make_an_identifier_marked() -> None:
    """``covid19`` is flatcase with a number in it, not a segmented name.

    Filing it under ``marked`` would move the hardest population into the row
    the headline is read off, which is the pooling operating rule 5 forbids.
    """
    assert gold.signals("covid19")["letter_digit"] == {5}
    assert not gold.is_marked(gold.signals("covid19"))
    assert gold.is_marked(gold.signals("covid_19"))


# ---------------------------------------------------------------------------
# shape
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "identifier, expected",
    [
        ("incident_number", "snake_lower"),
        ("TXN_APPLNT_DOB", "snake_upper"),
        ("Txn_Applnt", "snake_mixed"),
        ("ContractWithCustomer", "camel"),
        ("casenumber", "flat_lower"),
        ("CASENUMBER", "flat_upper"),
        ("db.schema.txn_id", "dotted"),
        ("2013", "digits_only"),
    ],
)
def test_shape_names_what_a_schema_owner_would_call_it(identifier: str, expected: str) -> None:
    assert gold.shape_of(identifier, gold.signals(identifier)) == expected


def test_shape_and_mark_share_one_definition_of_separated() -> None:
    """The bug this test exists for: two tables in one report disagreeing.

    A leading underscore made ``_casenumber`` ``snake_lower`` in the shape table
    and ``unmarked`` in the accuracy table, so the two decompositions of the same
    population did not add up.
    """
    for identifier in ("_casenumber", "_0_24_pop", "casenumber", "TXN_ID", "camelCase"):
        marks = gold.signals(identifier)
        separated = gold.shape_of(identifier, marks).startswith(("snake", "dotted"))
        assert separated == bool(marks["separator"])


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------
def _arm(pairs: List[Tuple[str, str]], corpus: str = "socrata") -> object:
    """A scorable arm over hand-written pairs, with no fetch behind it."""
    return gold.Arm(
        corpus=corpus,
        name="fixture",
        source_url="fixture://",
        pairs=tuple(pairs),
        columns_seen=len(pairs),
        occurrences_seen=len(pairs),
        fetched_on="2026-08-23",
    )


def test_a_perfectly_segmented_arm_scores_100() -> None:
    entry = gold.evaluate(_arm([("incident_number", "Incident Number"), ("case_id", "Case Id")]))
    assert entry["all"]["pairs"] == 2
    assert entry["all"]["exact_pct"] == 100.0
    assert entry["all"]["boundary_precision_pct"] == 100.0
    assert entry["all"]["boundary_recall_pct"] == 100.0
    assert entry["false_negatives_marked"] == 0
    assert entry["false_negatives_unmarked"] == 0


def test_an_unmarked_identifier_is_scored_and_reported_separately() -> None:
    """The row that is the honest cost of refusing to guess.

    ``casenumber`` carries no mark, the publisher cut it in two, and the
    splitter cannot recover that without guessing. It is a miss, it is counted
    as one, and it lands in the ``unmarked`` row rather than being excluded.
    """
    entry = gold.evaluate(_arm([("casenumber", "Case Number")]))
    assert entry["unmarked"]["pairs"] == 1
    assert entry["unmarked"]["exact_pct"] == 0.0
    assert entry["unmarked"]["boundary_recall_pct"] == 0.0
    assert entry["unmarked"]["boundary_recall_ceiling_pct"] == 0.0
    assert entry["false_negatives_unmarked"] == 1
    assert entry["marked"]["pairs"] == 0


def test_a_cut_the_publisher_did_not_make_is_attributed_to_the_rule_that_made_it() -> None:
    """``q1`` is one word to the publisher and two to rule 5.

    The dominant disagreement on Socrata, and the report has to say which rule
    produced it or the number is a complaint rather than a diagnosis.
    """
    entry = gold.evaluate(_arm([("_2013_q1_actual", "2013 Q1 Actual")]))
    assert entry["all"]["exact_pct"] == 0.0
    assert entry["false_positives_by_signal"]["letter_digit"] == 1
    assert entry["false_positives_by_signal"]["separator"] == 0
    assert entry["false_negatives_marked"] == 0


def test_boundary_recall_never_exceeds_the_ceiling() -> None:
    """The ceiling is a bound, not a decoration.

    A cut the identifier does not mark cannot be produced by a splitter that
    reads only the identifier, so recall is capped by the marked share. If this
    ever failed, either the ceiling is computed from the wrong signals or the
    splitter is guessing.
    """
    pairs = [
        ("incident_number", "Incident Number"),
        ("casenumber", "Case Number"),
        ("_2013_q1_actual", "2013 Q1 Actual"),
        ("ContractWithCustomer", "Contract with Customer"),
        ("AvailableForSale", "Available-for-Sale"),
        ("Paidin", "Paid-in"),
        ("MDMHubID", "MDM Hub ID"),
        ("address2line1", "Address 2 Line 1"),
    ]
    entry = gold.evaluate(_arm(pairs))
    for subset in ("all", "marked", "unmarked"):
        figures = entry[subset]
        if figures["pairs"]:
            assert figures["boundary_recall_pct"] <= figures["boundary_recall_ceiling_pct"] + 1e-9


def test_every_pair_lands_in_exactly_one_of_marked_and_unmarked() -> None:
    pairs = [
        ("incident_number", "Incident Number"),
        ("casenumber", "Case Number"),
        ("covid19cases", "Covid19 Cases"),
    ]
    entry = gold.evaluate(_arm(pairs))
    assert entry["marked"]["pairs"] + entry["unmarked"]["pairs"] == entry["all"]["pairs"] == 3
    assert sum(entry["identifier_shapes"].values()) == 3
    assert sum(entry["pairs_by_caption_words"].values()) == 3


def test_an_empty_subset_reports_null_and_not_zero() -> None:
    """``0.00`` precision reads as "got everything wrong"; it would mean "made no guesses".

    The two SEC taxonomy arms have no flatcase pairs at all, and every field in
    ``bench/results.json`` is a citable path, so a stored zero for an empty
    subset is a wrong number waiting for somebody to quote it. ``null`` makes
    the citation fail instead.
    """
    entry = gold.evaluate(_arm([("incident_number", "Incident Number")]))
    assert entry["unmarked"]["pairs"] == 0
    for figure in (
        "exact_pct",
        "boundary_precision_pct",
        "boundary_recall_pct",
        "boundary_f1_pct",
        "boundary_recall_ceiling_pct",
    ):
        assert entry["unmarked"][figure] is None, figure


def test_the_entry_carries_the_licence_it_was_measured_under() -> None:
    entry = gold.evaluate(_arm([("incident_number", "Incident Number")]))
    assert entry["licence_url"] == gold.LICENCES["socrata"]["licence_url"]
    assert entry["licence_read_on"] == "2026-08-23"
    assert entry["system"].startswith("acronymkit.governed.expand_identifier")


# ---------------------------------------------------------------------------
# gold conflict
# ---------------------------------------------------------------------------
def test_gold_conflict_finds_publishers_who_disagree_with_each_other() -> None:
    """Two portals, one identifier, two cut placements: the gold has no answer.

    This is the floor under any system's disagreement with this gold, and it is
    measured rather than asserted because "the gold is only one publisher's
    opinion" is otherwise an unfalsifiable caveat.
    """
    conflict = gold.gold_conflict(
        [
            ("lastname", "Last Name"),
            ("lastname", "Lastname (#)"),
            ("incident_number", "Incident Number"),
            ("incident_number", "Incident Number"),
        ]
    )
    assert conflict["distinct_identifiers"] == 2
    assert conflict["contested_identifiers"] == 1
    assert conflict["contested_identifiers_pct"] == 50.0
    assert conflict["occurrences"] == 4
    assert conflict["contested_occurrences"] == 2


def test_gold_conflict_of_an_empty_population_is_zero_and_not_a_crash() -> None:
    conflict = gold.gold_conflict([])
    assert conflict["distinct_identifiers"] == 0
    assert conflict["contested_identifiers_pct"] == 0.0


# ---------------------------------------------------------------------------
# the split, and the licences
# ---------------------------------------------------------------------------
def test_the_portal_split_is_stable_and_disjoint() -> None:
    """``hash`` on a string is seeded per process; a split that moves is not a split."""
    portals = [f"data{index}.example.gov" for index in range(200)]
    halves = {portal: gold.portal_half(portal) for portal in portals}
    assert set(halves.values()) == {"a", "b"}
    assert all(gold.portal_half(portal) == halves[portal] for portal in portals)
    assert gold.portal_half("data.cityofchicago.org") == gold.portal_half("data.cityofchicago.org")


def test_licence_urls_pass_the_same_badge_rule_the_manifest_uses() -> None:
    """Operating rule 4 does not stop applying because the URL lives in a runner.

    GLADIS is the one-line cautionary tale: the GitHub badge said CC0, Zenodo
    said CC BY 4.0, and the repository's own source table listed UMLS.
    """
    if not SPLITS_TOOL.is_file():  # pragma: no cover - not a source checkout
        pytest.skip("tools/splits.py not present")
    splits = _load(SPLITS_TOOL, "_splits_for_governed_gold")
    for corpus, entry in gold.LICENCES.items():
        assert entry["licence"].strip(), corpus
        assert entry["licence_read_on"], corpus
        assert splits._licence_url_problem(entry["licence_url"]) is None, corpus


# ---------------------------------------------------------------------------
# no network in the scoring path
# ---------------------------------------------------------------------------
def test_scoring_opens_no_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fetching and scoring are separate, and only fetching may touch the wire."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the scoring path must not open a connection")

    monkeypatch.setattr(gold.urllib.request, "urlopen", refuse)
    entry = gold.evaluate(_arm([("incident_number", "Incident Number")]))
    assert entry["all"]["exact_pct"] == 100.0
    assert gold.admits("a_b", "A B")
    assert gold.cuts("A B") == {1}


def test_a_fetch_failure_says_what_to_do_rather_than_traceback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A runner that fetches its own corpus has to fail legibly when it cannot."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise OSError("network unreachable")

    monkeypatch.setattr(gold, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(gold.urllib.request, "urlopen", refuse)
    with pytest.raises(SystemExit) as failure:
        gold.fetch_socrata_columns(1)
    assert "network" in str(failure.value).lower()
    with pytest.raises(SystemExit):
        gold.fetch_sec_tags("2025q1")
