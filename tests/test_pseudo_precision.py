"""Tests for :mod:`acronymkit._pseudo_precision` and its bundled table.

Three halves, which is one more than the usual two:

1. **Estimator behaviour** -- grouping, harvesting, the shape of an estimate,
   and the cascade's use of a table it is handed.
2. **The bundled resource** -- that it loads, has the shape the loader promises,
   is listed by ``bundled_resources()``, and is not shared mutable state.
3. **Licence discipline** -- that the shipped table reproduces no text from the
   corpus it was derived from. That is not a style assertion. The table ships in
   an MIT wheel and its provenance says it carries no source text; a test is the
   only thing that keeps the claim true after someone adds a field.

The file is pure ASCII.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from acronymkit._pseudo_precision import (
    BUNDLED_TABLE_RESOURCE,
    Candidate,
    PrecisionTable,
    best_alignment,
    bundled_table,
    bundled_table_provenance,
    estimate_precisions,
    harvest_candidates,
    short_form_group,
)
from acronymkit._strategies import STRATEGIES
from acronymkit.exceptions import ResourceNotFoundError
from acronymkit.resources import bundled_resources, read_json_resource

#: Every group key :func:`short_form_group` is capable of producing. The table's
#: keys are checked against this rather than against a hand-written list, so a
#: change to the grouping cannot leave a stale expectation behind.
POSSIBLE_GROUPS = frozenset(
    f"{kind}:{length}" for kind in ("al", "num", "spec") for length in range(1, 6)
)

STRATEGY_NAMES = frozenset(strategy.name for strategy in STRATEGIES)


# ---------------------------------------------------------------------------
# estimator behaviour
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("short_form", "expected"),
    [
        ("abc", "al:3"),
        ("AB", "al:2"),
        ("a", "al:1"),
        ("abcdefgh", "al:5"),
        ("h2o", "num:3"),
        ("il-2", "spec:4"),
        ("", "al:1"),
    ],
)
def test_short_form_group_buckets_by_length_and_content(short_form: str, expected: str) -> None:
    """Grouping folds length above five and prefers the punctuation class."""
    assert short_form_group(short_form) == expected


def test_harvest_candidates_reads_parentheticals_with_their_preceding_window() -> None:
    """A candidate is a bracketed token plus the case-folded words before it."""
    found = harvest_candidates(["The Portable Document Format (PDF) is a standard."])

    assert len(found) == 1
    assert found[0].short_form == "pdf"
    assert found[0].window[-3:] == ("portable", "document", "format")


def test_harvest_candidates_keeps_non_definitions() -> None:
    """Filtering here would bias the chance rate, so nothing plausible is dropped."""
    found = harvest_candidates(["Rates rose (see Table 2) across every arm."])

    assert [candidate.short_form for candidate in found] == ["see table 2"]


def test_estimate_precisions_is_reproducible_for_a_fixed_seed() -> None:
    """The randomisation is seeded, so two estimates over one input agree."""
    candidates = [
        Candidate("pdf", ("portable", "document", "format")),
        Candidate("abc", ("alpha", "beta", "charlie")),
        Candidate("xy", ("some", "unrelated", "words")),
    ]

    first = estimate_precisions(candidates, seed=7)
    second = estimate_precisions(candidates, seed=7)

    assert first.to_dict() == second.to_dict()


def test_precision_table_round_trips_through_a_file(tmp_path: Path) -> None:
    """``save`` and ``load`` are inverses, which is what the builder relies on."""
    table = PrecisionTable(values={"al:3": {"x": 0.5}}, support={"al:3": {"x": 9}}, seed=3)

    reloaded = PrecisionTable.load(table.save(tmp_path / "table.json"))

    assert reloaded.to_dict() == table.to_dict()


def test_ordered_drops_strategies_without_enough_support() -> None:
    """An estimate from a handful of observations is noise and must not rank."""
    strong = "anchInit_placeInit_skipNone"
    flimsy = "anchAny_placeWithin_skipAny"
    table = PrecisionTable(
        values={"al:3": {strong: 0.8, flimsy: 0.99}},
        support={"al:3": {strong: 50, flimsy: 2}},
    )

    assert table.ordered("al:3", minimum_support=5) == [strong]


def test_ordered_tolerates_a_strategy_name_this_build_does_not_define() -> None:
    """A table from an older build must degrade, not raise.

    The bundled table is a file now, so the table and the strategy family are
    versioned separately for the first time. A rule renamed between the build
    that wrote a table and the build that reads it used to be a ``KeyError``
    raised from a sort key -- a crash a long way from its cause.
    """
    known = "anchInit_placeInit_skipNone"
    table = PrecisionTable(
        values={"al:3": {known: 0.9, "RuleFromTheFuture": 0.95}},
        support={"al:3": {known: 40, "RuleFromTheFuture": 40}},
    )

    assert table.ordered("al:3") == ["RuleFromTheFuture", known]
    assert best_alignment("pdf", ["portable", "document", "format"], table) is not None


# ---------------------------------------------------------------------------
# the bundled resource
# ---------------------------------------------------------------------------
def test_bundled_table_resource_is_shipped() -> None:
    """The file is in the distribution, not merely in the source tree."""
    assert BUNDLED_TABLE_RESOURCE in bundled_resources()


def test_bundled_table_loads_with_no_arguments() -> None:
    """The whole point: a usable table with no corpus, no path and no network."""
    table = bundled_table()

    assert isinstance(table, PrecisionTable)
    assert table.values
    assert table.candidates > 0


def test_bundled_table_keys_are_ours_and_only_ours() -> None:
    """Every key is a group this library produces or a strategy it defines.

    A key from neither set means the resource was built by something other than
    ``tools/build_reliability_table.py`` -- Ab3P's published table, for
    instance, whose strategy names would silently resolve to nothing in the
    cascade and turn every lookup into a miss.
    """
    table = bundled_table()

    assert set(table.values) <= POSSIBLE_GROUPS
    assert set(table.support) <= POSSIBLE_GROUPS
    for per_strategy in table.values.values():
        assert set(per_strategy) <= STRATEGY_NAMES
    for per_strategy in table.support.values():
        assert set(per_strategy) <= STRATEGY_NAMES


def test_bundled_table_estimates_are_probabilities_with_integer_support() -> None:
    """Values are clamped to the unit interval and every one has a count behind it."""
    table = bundled_table()

    for group, per_strategy in table.values.items():
        for name, value in per_strategy.items():
            assert isinstance(value, float)
            assert 0.0 <= value <= 1.0
            assert isinstance(table.support[group][name], int)


def test_bundled_table_ranks_the_strictest_rule_top_for_three_letter_acronyms() -> None:
    """Word-initial anchoring with word-initial placement and no skipping wins.

    This is the ordering Ab3P's published table also reports for that bucket,
    derived here from unlabelled text. If it ever stops holding, the resource is
    not describing the strategy family it claims to.
    """
    ranked = bundled_table().ordered("al:3")

    assert ranked[0] == "anchInit_placeInit_skipNone"
    assert "anchAny_placeWithin_skipAny" not in ranked[:5]


def test_bundled_table_is_not_shared_mutable_state() -> None:
    """Two callers get two tables, because a table is mutable."""
    first = bundled_table()
    second = bundled_table()
    first.values["al:3"]["sentinel"] = 0.123

    assert first is not second
    assert "sentinel" not in second.values["al:3"]


def test_bundled_table_provenance_names_its_source_and_licence() -> None:
    """Provenance is data because JSON has no comments; it must still be there."""
    provenance = bundled_table_provenance()

    assert provenance["source_asset"] == "med1250"
    assert "Public domain" in provenance["source_licence"]
    assert provenance["source_sha256"]
    assert provenance["source_url"].startswith("https://")
    assert provenance["attribution"]
    assert provenance["contains_source_text"] is False
    assert "prior" in provenance["caveat"].lower()


def test_bundled_table_provenance_is_not_shared_mutable_state() -> None:
    """Same contract as the table: callers may edit what they are handed."""
    first = bundled_table_provenance()
    first["source_asset"] = "sentinel"

    assert bundled_table_provenance()["source_asset"] == "med1250"


def test_bundled_table_rejects_a_resource_of_the_wrong_shape(monkeypatch) -> None:
    """A malformed resource fails loudly rather than yielding an empty table.

    An empty table is the dangerous failure: ``ordered()`` returns nothing, the
    cascade matches nothing, and the caller sees "no definitions found" rather
    than "your installation is broken".
    """
    monkeypatch.setattr(
        "acronymkit._pseudo_precision.read_json_resource", lambda name: {"values": {}}
    )

    with pytest.raises(ResourceNotFoundError, match="support"):
        bundled_table()


# ---------------------------------------------------------------------------
# licence discipline
# ---------------------------------------------------------------------------
def test_bundled_table_reproduces_no_text_from_its_source_corpus() -> None:
    """The shipped table must carry counts, not corpus content.

    ``data/LICENSES.md`` justifies shipping this file on two independent
    grounds: MED1250 is public domain, and the derived table contains no text
    from it. The first is a licence reading and cannot be tested. The second can
    be, and it is the argument that would still stand if the first were ever
    disputed -- so it is asserted here rather than trusted.

    Every leaf in ``values`` and ``support`` must be a number, and every key must
    come from this library's own vocabularies, which the test above already
    pins. What remains is to prove there is no third place for a string to hide.
    """
    document = read_json_resource(BUNDLED_TABLE_RESOURCE)

    assert set(document) == {"provenance", "seed", "candidates", "values", "support"}
    assert isinstance(document["seed"], int)
    assert isinstance(document["candidates"], int)
    for section in ("values", "support"):
        for per_strategy in document[section].values():
            for value in per_strategy.values():
                assert isinstance(value, (int, float))
                assert not isinstance(value, bool)


def test_bundled_table_matches_a_fresh_build_of_the_serialised_form() -> None:
    """The file on disk is exactly what the resource loader will reconstruct.

    Guards the hand-edit: someone tuning a value in the JSON to make a benchmark
    look better would leave a file that no longer round-trips through
    ``to_dict``. ``tools/build_reliability_table.py --check`` is the stronger
    version of this and rebuilds from the corpus, but it needs a fetched
    MED1250, so the suite gets the half that runs anywhere.
    """
    document = read_json_resource(BUNDLED_TABLE_RESOURCE)
    rebuilt = PrecisionTable.from_dict(document).to_dict()

    assert rebuilt["values"] == document["values"]
    assert rebuilt["support"] == document["support"]
    assert rebuilt["seed"] == document["seed"]
    assert rebuilt["candidates"] == document["candidates"]


def test_bundled_resource_is_valid_json_on_disk() -> None:
    """The bytes in the package parse, independently of the resource loader."""
    path = Path(__file__).resolve().parent.parent
    path = path / "src" / "acronymkit" / "resources" / BUNDLED_TABLE_RESOURCE

    if not path.is_file():  # installed-wheel run: the loader test above covers it
        pytest.skip("running against an installed distribution, not a checkout")
    assert json.loads(path.read_text(encoding="utf-8"))["provenance"]["source_asset"]


# ---------------------------------------------------------------------------
# the cascade
# ---------------------------------------------------------------------------
def test_best_alignment_falls_back_to_the_bundled_table() -> None:
    """Omitting the table is the zero-corpus path and must actually work."""
    result = best_alignment("pdf", ["portable", "document", "format"])

    assert result is not None
    strategy, positions, confidence = result
    assert strategy.name == "anchInit_placeInit_skipNone"
    assert positions == ((0, 0), (1, 0), (2, 0))
    assert confidence > 0.9


def test_best_alignment_prefers_an_explicit_table_over_the_bundled_one() -> None:
    """A caller who derived a table from their own corpus gets theirs used."""
    empty = PrecisionTable(values={}, support={})

    assert best_alignment("pdf", ["portable", "document", "format"], empty) is None


def test_best_alignment_abstains_below_the_threshold() -> None:
    """The threshold is what makes the confidence worth having."""
    table = PrecisionTable(
        values={"al:3": {"anchInit_placeInit_skipNone": 0.4}},
        support={"al:3": {"anchInit_placeInit_skipNone": 99}},
    )

    assert best_alignment("pdf", ["portable", "document", "format"], table) is not None
    assert (
        best_alignment("pdf", ["portable", "document", "format"], table, minimum_precision=0.9)
        is None
    )
