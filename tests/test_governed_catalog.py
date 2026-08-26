"""The catalog-versus-empty-catalog harness, pinned.

``bench/run_governed_catalog.py`` produces the only gated evidence bearing on
``docs/POSITIONING.md``'s first reversal condition, and its figures reverse the
audit's reading of the same question. A number that overturns a record is the
number most worth attacking, so the parts of the derivation that could be wrong
are pinned here rather than trusted.

What this file pins, and why each item is here
----------------------------------------------
* **The scorer is the gold runner's scorer.** ``phrase_words`` equality and
  ``run_governed_gold.cuts`` equality must agree on every pair the gold runner
  admits -- that is the whole justification for scoring this question with a
  different metric, and the saved run
  ``governed_catalog.socrata.scorer_agreement`` is only meaningful if the
  identity is a property and not a coincidence of one corpus.
* **The empty arm's zero on the live subset is a derivation.** If a caption's
  alphanumerics differ from its identifier's, an empty catalog cannot produce
  it. The runner prints `0.00 %` there and a reader is owed a proof rather than
  a measurement, because a harness that could produce a non-zero would be
  broken in a way no delta would reveal.
* **Win/loss tallies are counted on integers.** The first version of the sweep
  counted them on a rounded delta, and a catalog that breaks one pair in
  `31,348` rounds to ``-0.0`` -- which is not less than zero in Python, so
  three real losses were filed as ties. The percentages are for reading; the
  counts are for counting.
* **The null control really is null.** An empty catalog scored against an empty
  catalog must move nothing at all.
* **A catalog is built by majority, and identity wins are not rows.** A row
  whose expansion is the token cannot change a word tuple, so emitting it would
  inflate the catalog's size without touching any number derived from it.
* **The split is portal-disjoint.** A portal that trained the catalog must not
  also be scored by it, or the transfer claim is empty.

Nothing here reaches the network. Every fixture is a literal.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "bench" / "run_governed_catalog.py"
GOLD_RUNNER = REPO_ROOT / "bench" / "run_governed_gold.py"


def _load(path: Path, name: str) -> ModuleType:
    """Import a script by path; ``bench/`` is a directory of scripts, not a package."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pytestmark = pytest.mark.skipif(
    not (RUNNER.is_file() and GOLD_RUNNER.is_file()), reason="not a source checkout"
)

# Imported at module scope for the same reason ``tests/test_governed_gold.py``
# does it: ``pytestmark`` skips at collection, which is later than import. The
# sdist ships ``tests/`` and deliberately not ``bench/*.py``.
catalog = _load(RUNNER, "_governed_catalog_under_test") if RUNNER.is_file() else None
gold = catalog.gold if catalog is not None else None


# ---------------------------------------------------------------------------
# the scorer, and its identity with the gold runner's
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text, expected",
    [
        ("Incident Number", ("incident", "number")),
        ("Available-for-Sale", ("available", "for", "sale")),
        ("Accounts Payable, Current", ("accounts", "payable", "current")),
        ("Total (#)", ("total",)),
        ("2013 Q1 Actual", ("2013", "q1", "actual")),
        ("", ()),
        ("   ", ()),
    ],
)
def test_phrase_words_cuts_on_any_punctuation(text: str, expected: Tuple[str, ...]) -> None:
    assert catalog.phrase_words(text) == expected


#: Pairs the gold runner admits: same alphanumerics, caption carries whitespace.
#: Half agree on the cut and half do not, so the identity below is exercised in
#: both directions rather than only where both verdicts are ``True``.
ADMITTED: List[Tuple[str, str]] = [
    ("incident_number", "Incident Number"),
    ("ContractWithCustomer", "Contract with Customer"),
    ("AccountsPayableCurrent", "Accounts Payable, Current"),
    ("DebtSecuritiesAvailableForSale", "Debt Securities, Available-for-Sale"),
    ("_0_4_years", "0-4 years"),
    ("total", "Total (#)"),
    ("casenumber", "Case Number"),
    ("_2013_q1_actual", "2013 Q1 Actual"),
    ("enddate", "End Date"),
    ("covid19", "Covid 19"),
]


@pytest.mark.parametrize("identifier, caption", ADMITTED)
def test_the_two_scorers_return_the_same_verdict_on_every_admitted_pair(
    identifier: str, caption: str
) -> None:
    """The justification for scoring this question with a different metric.

    On a shared character stream, "the cut sets are equal" and "the word tuples
    are equal" are the same statement. The gold runner's admission rule fixes
    the stream, so on its population the two metrics cannot disagree -- and if
    they ever did, every figure this harness publishes would be incomparable
    with ``governed_gold.socrata.*`` rather than a decomposition of it.
    """
    from acronymkit.governed import GovernedDictionary, expand_identifier

    assert gold.admits(identifier, caption), "fixture is not an admitted pair"
    produced = expand_identifier(identifier, GovernedDictionary({})).phrase
    assert gold.gold_key(produced) == gold.gold_key(caption)
    by_cuts = gold.cuts(produced) == gold.cuts(caption)
    by_words = catalog.phrase_words(produced) == catalog.phrase_words(caption)
    assert by_cuts == by_words


def test_the_fixture_set_exercises_both_verdicts() -> None:
    """Otherwise the test above passes on a set where nothing is ever wrong."""
    from acronymkit.governed import GovernedDictionary, expand_identifier

    empty = GovernedDictionary({})
    verdicts = {
        catalog.phrase_words(expand_identifier(identifier, empty).phrase)
        == catalog.phrase_words(caption)
        for identifier, caption in ADMITTED
    }
    assert verdicts == {True, False}


# ---------------------------------------------------------------------------
# the classification
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "identifier, caption, expected",
    [
        ("incident_number", "Incident Number", "identical"),
        ("casenumber", "Case Number", "identical"),
        ("qty", "Quantity", "expansion_strict"),
        ("qty_ordered", "Quantity Ordered", "expansion_strict"),
        ("dob_dt", "Date of Birth Date", "expansion"),
        ("unit_number", "Unit Num", "other"),
        ("computed_region_92fq", "City Council Districts 2", "other"),
        # An identifier that is a subsequence of the caption but not by token:
        # the caption interleaves a word, so no per-token alignment exists.
        ("ab_cd", "Alpha Bravo Charlie Delta", "expansion"),
    ],
)
def test_classify(identifier: str, caption: str, expected: str) -> None:
    assert catalog.classify(identifier, caption) == expected


def test_an_empty_catalog_cannot_score_a_non_identical_pair() -> None:
    """The derivation behind the `0.00 %` the runner prints on the live subset.

    The empty catalog passes every token through, so the alphanumerics of what
    it produces are the identifier's. On any pair whose caption has different
    alphanumerics, the word tuples cannot be equal. This is why that zero is
    reported as a derivation and not as evidence.
    """
    from acronymkit.governed import GovernedDictionary, expand_identifier

    empty = GovernedDictionary({})
    for identifier, caption in [
        ("qty", "Quantity"),
        ("qty_ordered", "Quantity Ordered"),
        ("dob_dt", "Date of Birth Date"),
        ("unit_number", "Unit Num"),
    ]:
        assert catalog.classify(identifier, caption) != "identical"
        produced = expand_identifier(identifier, empty).phrase
        assert catalog.phrase_words(produced) != catalog.phrase_words(caption)


# ---------------------------------------------------------------------------
# harvesting and catalog construction
# ---------------------------------------------------------------------------
def test_equal_count_refuses_a_pair_whose_word_count_differs() -> None:
    assert catalog.align("qty_ordered", "Quantity Ordered", "equal_count") == [
        ("qty", "quantity"),
        ("ordered", "ordered"),
    ]
    assert catalog.align("qty_ordered", "Quantity of Things Ordered", "equal_count") is None


def test_abbrev_only_drops_the_identity_votes_that_would_veto_an_abbreviation() -> None:
    assert catalog.align("qty_ordered", "Quantity Ordered", "abbrev_only") == [("qty", "quantity")]


def test_consistent_keeps_only_subsequence_votes() -> None:
    """``career`` captioned ``Opportunities`` is an alignment artefact, not a row."""
    assert catalog.align("career_x", "Opportunities X", "equal_count") == [
        ("career", "opportunities"),
        ("x", "x"),
    ]
    assert catalog.align("career_x", "Opportunities X", "consistent") == [("x", "x")]


def test_monotone_may_skip_a_caption_word_but_never_a_token() -> None:
    assert catalog.align("dt_yr", "Date Of Year", "monotone") == [("dt", "date"), ("yr", "year")]
    assert catalog.align("zzz_qqq", "Quantity Ordered", "monotone") is None
    # `dob` is a subsequence of no word in this caption, so the whole pair casts
    # no vote rather than casting a partial one -- a partial alignment is a
    # guess about which token the missing word belonged to.
    assert catalog.align("dob_dt", "Date of Birth Date", "monotone") is None


def test_a_majority_expansion_that_is_the_token_is_counted_and_not_emitted() -> None:
    """An identity row cannot move a word tuple, so emitting it would only
    inflate the catalog's published size."""
    training = [
        ("no_x", "No X"),
        ("no_y", "No Y"),
        ("no_z", "Number Z"),
    ]
    built = catalog.build_catalog(training, "equal_count", 2, 0.5)
    assert [entry.token for entry in built.entries] == []
    assert built.identity_rows == 1
    assert built.as_dict()["rows_including_identity"] == 1
    assert built.harvested_pairs == 3


def test_min_votes_and_min_share_both_bite() -> None:
    training = [("qty_a", "Quantity A"), ("qty_b", "Quantity B"), ("qty_c", "Quality C")]
    assert [e.token for e in catalog.build_catalog(training, "equal_count", 2, 0.5).entries] == [
        "qty"
    ]
    assert catalog.build_catalog(training, "equal_count", 4, 0.5).entries == []
    assert catalog.build_catalog(training, "equal_count", 2, 0.9).entries == []


def test_a_built_catalog_actually_changes_the_answer() -> None:
    """Otherwise every delta in this harness is a measurement of nothing."""
    from acronymkit.governed import GovernedDictionary, expand_identifier

    built = catalog.build_catalog(
        [("qty_a", "Quantity A"), ("qty_b", "Quantity B")], "equal_count", 2, 0.5
    )
    voted = GovernedDictionary(built.entries)
    assert catalog.phrase_words(expand_identifier("qty_ordered", voted).phrase) == (
        "quantity",
        "ordered",
    )


# ---------------------------------------------------------------------------
# the tally, and the rounding defect it was found by
# ---------------------------------------------------------------------------
def test_a_cell_carries_raw_counts_beside_its_percentages() -> None:
    """The regression pin for the defect that mis-filed three sweep cells.

    A catalog that breaks exactly one pair in a large population produces a
    delta that rounds to ``-0.0``, and ``-0.0 < 0`` is ``False``. Counting a
    sweep on the rounded delta therefore files a loss as a tie. Every tally in
    the runner is counted on ``empty_exact`` and ``voted_exact``.
    """
    cell = catalog.Cell()
    for index in range(31348):
        right = index != 0
        cell.add(empty_right=True, voted_right=right, moved=not right)
    figures = cell.as_dict()
    assert figures["empty_exact"] == 31348
    assert figures["voted_exact"] == 31347
    assert figures["delta_points"] == 0.0  # -0.0 == 0.0, which is the trap
    assert not figures["voted_exact"] > figures["empty_exact"]
    assert figures["voted_exact"] < figures["empty_exact"]
    assert figures["catalog_fired_pairs"] == 1


def test_an_empty_subset_reports_null_rather_than_zero() -> None:
    figures = catalog.Cell().as_dict()
    assert figures["pairs"] == 0
    assert figures["empty_exact_pct"] is None
    assert figures["voted_exact_pct"] is None


# ---------------------------------------------------------------------------
# scoring a fold
# ---------------------------------------------------------------------------
def _fold(scored: List[Tuple[str, str]]) -> object:
    return catalog.Fold(
        name="fold_test",
        train_half="a",
        test_half="b",
        training=[],
        scored=scored,
        train_portals=1,
        test_portals=1,
        test_occurrences=len(scored),
    )


def _score(scored: List[Tuple[str, str]], entries: object) -> dict:
    from acronymkit.governed import GovernedDictionary, expand_identifier

    empty = GovernedDictionary({})
    buckets = {pair: catalog.classify(*pair) for pair in scored}
    phrases = {
        pair: catalog.phrase_words(expand_identifier(pair[0], empty).phrase) for pair in scored
    }
    built = catalog.Catalog(
        entries=list(entries),  # type: ignore[call-overload]
        identity_rows=0,
        distinct_tokens=0,
        harvested_pairs=0,
        training_pairs=0,
        mode="test",
        min_votes=0,
        min_share=0.0,
    )
    return catalog.score(_fold(scored), built, buckets, phrases)


def test_the_null_control_moves_nothing() -> None:
    scored = [("incident_number", "Incident Number"), ("qty", "Quantity"), ("x_y", "Y X")]
    result = _score(scored, [])
    assert result["all"]["delta_points"] == 0.0
    assert result["all"]["catalog_fired_pairs"] == 0
    assert result["all"]["empty_only_correct"] == 0
    assert result["all"]["voted_only_correct"] == 0


def test_a_catalog_is_scored_where_it_helps_and_where_it_hurts() -> None:
    """One pair each way, so the decomposition is exercised in both directions."""
    built = catalog.build_catalog(
        [("qty_a", "Quantity A"), ("qty_b", "Quantity B")], "equal_count", 2, 0.5
    )
    scored = [("qty_ordered", "Quantity Ordered"), ("qty", "Qty")]
    result = _score(scored, built.entries)
    assert result["live"]["pairs"] == 1
    assert result["live"]["voted_exact_pct"] == 100.0
    assert result["live"]["empty_exact_pct"] == 0.0
    assert result["identical"]["pairs"] == 1
    assert result["identical"]["empty_exact_pct"] == 100.0
    assert result["identical"]["voted_exact_pct"] == 0.0
    assert result["all"]["catalog_fired_pairs"] == 2


def test_abbreviated_tokens_are_counted_only_where_the_token_differs() -> None:
    built = catalog.build_catalog(
        [("qty_a", "Quantity A"), ("qty_b", "Quantity B")], "equal_count", 2, 0.5
    )
    result = _score([("qty_ordered", "Quantity Ordered")], built.entries)
    tokens = result["abbreviated_tokens"]
    assert tokens["tokens"] == 1, "'ordered' matches its caption word and is not an atom"
    assert tokens["empty_correct"] == 0
    assert tokens["voted_correct"] == 1


def test_the_entry_says_it_was_selected_on() -> None:
    """Both disclosures travel inside the saved entry, not only in prose."""
    result = _score([("qty", "Quantity")], [])
    assert result["selection_on_this_corpus"] is True
    assert result["empty_arm_zero_on_live_is_a_derivation"] is True


# ---------------------------------------------------------------------------
# the split
# ---------------------------------------------------------------------------
def test_the_split_is_the_gold_runners_split_and_is_stable() -> None:
    """A split that moves between runs is not a split, and two splits are worse.

    The portal digest is imported from ``run_governed_gold`` rather than
    re-implemented, so the fold boundary here and the robustness halves gated at
    ``governed_gold.socrata.portal_half_*`` are the same boundary by
    construction.
    """
    assert catalog.gold.portal_half is gold.portal_half
    portals = ["data.cityofnewyork.us", "data.seattle.gov", "www.dallasopendata.com"]
    once = [gold.portal_half(portal) for portal in portals]
    assert once == [gold.portal_half(portal) for portal in portals]
    assert set(once) <= {"a", "b"}


def test_the_declared_role_comes_from_the_manifest_and_not_from_this_file() -> None:
    """Operating rule 2: ask ``bench/splits.toml``, do not assume."""
    assert catalog.gold.declared_role is gold.declared_role
    assert gold.declared_role("socrata") in {
        "held_out",
        "tuning",
        "single_annotator_reference",
    } or (gold.declared_role("socrata").startswith("UNDECLARED"))
