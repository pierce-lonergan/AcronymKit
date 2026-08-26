"""The cost-centre harness, pinned — because a decomposition can be wrong quietly.

``bench/run_governed_perf.py`` answers the question Mandate III says every
optimisation in it waits on, and it answers it by **subtraction**: four nested
stages are timed over one corpus and the differences are the cost centres. That
design has exactly one failure mode and it is silent. A stage that does less work
than the call above it makes the difference charge somebody else's cost to the
centre being measured, the output stays plausible, and no timing check can see
it.

It already happened once. The first ``stage_lookup`` resolved every token instead
of consulting a memo first, so on the arm where the catalog answers it did *more*
work than ``stage_phrase``, and the assembly centre came out negative. That
version was loud. The dangerous version is the quiet one: a stage that skips
lookups while agreeing on every phrase.

So this file pins the three parity properties the runner's arithmetic rests on,
against the fixture catalog and against a hand-written corpus that includes the
awkward shapes — a digit-leading catalog token, an ordinal, an unaccounted
character, a non-ASCII name that must leave the regex fast path, and a name that
tokenises to nothing at all:

* every stage's phrase is **byte-identical** to ``expand_identifier(...).phrase``;
* every stage takes **exactly** the shipped path's number of ``resolve`` calls;
* the class-word stage takes exactly the shipped path's number of
  ``class_word_for`` calls.

**And all three are shown capable of failing**, at the end of the file, against
a deliberately broken stage — because a check that has only ever reported zero
is indistinguishable from one that cannot report anything else.

Then it pins the guards: that ``work_counts`` refuses to report a zero for a
function that has left the hot path, that the caller census classifies all three
call shapes and excludes the runner from its own population, and that the census
arithmetic is what a hand count says it is.

Nothing here times anything. Wall-clock belongs in ``bench/``; what belongs here
is whether the instrument is measuring what it says.
"""

from __future__ import annotations

import ast
import cProfile
import importlib.util
import pstats
import sys
from pathlib import Path
from types import ModuleType

import pytest

from acronymkit.governed import GovernedDictionary, GovernedEntry
from acronymkit.governed.enums import EntryKind, ExpansionSource

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "bench" / "run_governed_perf.py"


def _load(path: Path, name: str) -> ModuleType:
    """Import a script by path; ``bench/`` is a directory of scripts, not a package."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if not RUNNER.is_file():  # pragma: no cover - only reachable in an extracted sdist
    # The sdist ships ``tests/`` and deliberately not ``bench/*.py``, so this
    # module has no subject there. Skipped **before** the load rather than by a
    # ``pytestmark``, because ``pytestmark`` runs at collection and the import
    # below runs earlier -- which is how a module of this shape turns an absent
    # file into a collection error instead of a skip, and how a suite ends up
    # green while a file's worth of tests never ran.
    pytest.skip(
        "bench/run_governed_perf.py is absent; not a source checkout",
        allow_module_level=True,
    )

perf = _load(RUNNER, "bench_run_governed_perf")


#: A vocabulary with one of everything the stages have a branch for: a plain
#: row, a row that carries its own class word, a row that does not (so
#: ``class_word_for`` is consulted), and a digit-leading token that only exists
#: to make ``_rejoin_digit_tokens`` fire and take an extra lookup.
CATALOG_ROWS = (
    GovernedEntry(
        token="TXN",
        canonical="Transaction",
        kind=EntryKind.APPROVED_ABBREV,
        entry_id="NDS-TXN",
        source=ExpansionSource.GOVERNED,
    ),
    GovernedEntry(
        token="DT",
        canonical="Date",
        class_word="Date",
        kind=EntryKind.APPROVED_ABBREV,
        entry_id="NDS-DT",
        source=ExpansionSource.GOVERNED,
    ),
    GovernedEntry(
        token="ID",
        canonical="Identifier",
        kind=EntryKind.APPROVED_ABBREV,
        entry_id="NDS-ID",
        source=ExpansionSource.GOVERNED,
    ),
    GovernedEntry(
        token="1MM",
        canonical="One Million",
        kind=EntryKind.APPROVED_ABBREV,
        entry_id="NDS-1MM",
        source=ExpansionSource.GOVERNED,
    ),
)

#: Names chosen so that every branch in the shipped path runs at least once, and
#: so that at least one of them repeats: a corpus with no repetition cannot
#: exercise the memo short-circuit, which is the exact thing the first draft of
#: the harness got wrong.
CORPUS = (
    "TXN_APPLNT_ID",
    "TXN_APPLNT_ID",  # a repeat, so the memo is consulted rather than only filled
    "txn_dt",
    "ADDR_LINE_1",
    "AMT_1MM",
    "E_9_1_1",
    "db.schema.TXN_ID",
    "PAY€AMT",  # an unaccounted character
    "TRÄGER_ID",  # non-ASCII: leaves the regex fast path for _scan
    "___",  # tokenises to nothing
    "",
    "KYC_UNKNOWN_TOKEN",
)


def catalog() -> GovernedDictionary:
    """A vocabulary that has answered nothing."""
    return GovernedDictionary(CATALOG_ROWS, class_words={"ID": "Identifier"})


def empty_catalog() -> GovernedDictionary:
    """The empty vocabulary every published governed figure is taken with."""
    return GovernedDictionary({})


CATALOGS = {"populated": catalog, "empty": empty_catalog}


def _calls(runner, corpus, dictionary, function) -> int:  # type: ignore[no-untyped-def]
    """How many times ``function`` ran while ``runner`` processed ``corpus``."""
    profiler = cProfile.Profile()
    profiler.enable()
    runner(corpus, dictionary)
    profiler.disable()
    stats = pstats.Stats(profiler).stats  # type: ignore[attr-defined]
    key = perf._key(function)
    return int(stats[key][1]) if key in stats else 0


# ---------------------------------------------------------------------------
# the three parity properties the subtraction rests on
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", sorted(CATALOGS))
def test_the_phrase_stage_agrees_with_the_shipped_call_byte_for_byte(label: str) -> None:
    """Not "the accuracy matched" -- the same string, on every name."""
    assert perf.verify_phrase_parity(CORPUS, CATALOGS[label]) == 0


class _DropClassWordCalls(ast.NodeTransformer):
    """Delete the class-word lookups, and only those.

    Two shapes and no more: a bare ``catalog.class_word_for(token)`` statement,
    and the ``if not entry.class_word:`` that guards one. Matching on "any
    statement mentioning ``class_word_for`` anywhere below it" was the first
    version and it deleted the whole outer loop, which would have made the
    comparison pass on two bodies that shared nothing but a variable name.
    """

    @staticmethod
    def _is_lookup(node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "class_word_for"
        )

    def _drop(self, node: ast.AST) -> bool:
        if self._is_lookup(node):
            return True
        return (
            isinstance(node, ast.If)
            and not node.orelse
            and len(node.body) == 1
            and self._is_lookup(node.body[0])
        )

    def generic_visit(self, node: ast.AST) -> ast.AST:
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                setattr(node, field, [item for item in value if not self._drop(item)])
        return super().generic_visit(node)


def _stage_body(name: str) -> str:
    """The named stage's body, docstring stripped, as a normalised dump."""
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            body = list(node.body)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                body = body[1:]
            module = ast.Module(body=body, type_ignores=[])
            if name == "stage_class_word":
                module = _DropClassWordCalls().visit(module)
            return ast.dump(ast.fix_missing_locations(module))
    raise AssertionError(f"{name} is not defined in {RUNNER.name}")


def test_the_class_word_stage_is_the_phrase_stage_plus_the_class_word_lookups() -> None:
    """Drift between two hand-copied stage bodies would corrupt one subtraction silently.

    ``stage_class_word`` is ``stage_phrase`` with two ``class_word_for`` calls
    inserted, and the whole meaning of ``class_word - phrase`` is that nothing
    *else* differs. Comparing the two bodies with those calls deleted is a
    stronger check than any output comparison: it fails on a changed variable
    name, a reordered branch or a dropped ``continue``, none of which would
    necessarily change a phrase.
    """
    assert _stage_body("stage_class_word") == _stage_body("stage_phrase")


@pytest.mark.parametrize("label", sorted(CATALOGS))
def test_every_stage_takes_the_shipped_number_of_catalog_lookups(label: str) -> None:
    """A stage that skips a lookup charges its cost to the centre above it."""
    factory = CATALOGS[label]
    shipped = _calls(perf.stage_full, CORPUS, factory(), GovernedDictionary.resolve)
    for stage in (perf.stage_lookup, perf.stage_phrase, perf.stage_class_word):
        assert _calls(stage, CORPUS, factory(), GovernedDictionary.resolve) == shipped, (
            f"{stage.__name__} takes a different number of catalog lookups than "
            "expand_identifier; the subtraction that uses it is not a decomposition"
        )


@pytest.mark.parametrize("label", sorted(CATALOGS))
def test_the_class_word_stage_takes_the_shipped_number_of_class_word_lookups(label: str) -> None:
    """The one provenance field that costs an index lookup, counted both ways."""
    factory = CATALOGS[label]
    shipped = _calls(perf.stage_full, CORPUS, factory(), GovernedDictionary.class_word_for)
    staged = _calls(perf.stage_class_word, CORPUS, factory(), GovernedDictionary.class_word_for)
    assert staged == shipped


@pytest.mark.parametrize("label", sorted(CATALOGS))
def test_every_stage_takes_exactly_one_tokenizer_pass_per_identifier(label: str) -> None:
    """The cheapest stage is the floor, so it must not be doing less than the floor."""
    factory = CATALOGS[label]
    for stage in (perf.stage_tokenise, perf.stage_lookup, perf.stage_phrase, perf.stage_full):
        assert _calls(stage, CORPUS, factory(), perf.split_identifier_parts) == len(CORPUS), (
            f"{stage.__name__} does not tokenise once per identifier"
        )


def test_the_stages_are_nested_in_lookups_rather_than_merely_ordered() -> None:
    """The regression that produced a negative cost centre, pinned as a property.

    ``stage_lookup`` resolving every token instead of consulting a memo made it
    do *more* work than the stages above it on a corpus where the catalog
    answers. The assertion is not "lookup is cheaper"; it is that no stage takes
    more catalog lookups than the full call, which is the property that makes
    every difference non-negative in expectation.
    """
    repeated = ("TXN_DT_ID",) * 50
    shipped = _calls(perf.stage_full, repeated, catalog(), GovernedDictionary.resolve)
    for stage in (perf.stage_lookup, perf.stage_phrase, perf.stage_class_word):
        assert _calls(stage, repeated, catalog(), GovernedDictionary.resolve) <= shipped


# ---------------------------------------------------------------------------
# the guards
# ---------------------------------------------------------------------------


def test_work_counts_refuses_a_zero_for_a_function_that_left_the_hot_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A renamed or bypassed function must fail the run, not report ``0``.

    The whole point of identifying functions by their code objects is that a
    counted function which never runs is a finding. Nothing in the output would
    otherwise distinguish "this costs nothing" from "this is not what the code
    calls any more".
    """

    def never_called() -> None:  # pragma: no cover - it is never called, that is the point
        return None

    monkeypatch.setitem(perf.COUNTED, "a_function_that_left", never_called)
    with pytest.raises(SystemExit) as raised:
        perf.work_counts(CORPUS, empty_catalog())
    assert "a_function_that_left" in str(raised.value)


def test_work_counts_allows_a_zero_only_where_zero_is_the_finding() -> None:
    """``_scan`` is zero on ASCII names, and that is a result rather than a break."""
    counts = perf.work_counts(("TXN_APPLNT_ID", "ADDR_LINE_1"), empty_catalog())
    assert counts["tokenizer_scans"] == 0
    assert counts["tokenizer_passes"] == 2
    # An empty catalog answers for nothing, so every token expansion is a
    # passthrough. Derived rather than hard-coded, so a tokenisation change moves
    # both sides of the equality instead of turning a true assertion red.
    assert counts["token_passthroughs"] == counts["token_expands"]
    assert counts["token_expansions_constructed"] == counts["token_expands"]


def test_a_non_ascii_name_does_reach_the_scan() -> None:
    """The zero above is a property of the corpus, not of the counter."""
    counts = perf.work_counts(("TRÄGER_ID",), empty_catalog())
    assert counts["tokenizer_scans"] == 1


def test_the_memo_split_separates_the_two_memos() -> None:
    """``resolve``'s memo and the expansion memo are different maps and are reported apart.

    On an empty catalog neither can ever fire, because neither records a miss;
    the counts must say so rather than showing a hit rate borrowed from the
    other map.
    """
    counts = perf.work_counts(("TXN_DT_ID",) * 20, empty_catalog())
    assert counts["catalog_memo_hits"] == 0
    assert counts["expansion_memo_hits"] == 0

    # Three known tokens, twenty repeats: sixty token expansions, three of which
    # reach the catalog and fifty-seven of which are served by the memo. Written
    # as the arithmetic rather than as a threshold, because "greater than zero"
    # would pass on a memo that fired once.
    warm = perf.work_counts(("TXN_DT_ID",) * 20, catalog())
    assert warm["token_expands"] == 60
    assert warm["catalog_lookups_from_token_path"] == 3
    assert warm["expansion_memo_hits"] == 57
    assert warm["token_expansions_constructed"] == 3


# ---------------------------------------------------------------------------
# the census
# ---------------------------------------------------------------------------


def test_the_census_arithmetic_is_what_a_hand_count_says() -> None:
    """Six identifiers, three distinct, hand-checked."""
    corpus = ("TXN_ID", "TXN_ID", "TXN_ID", "DT_CD", "AMT", "AMT")
    figures = perf.census(corpus)
    assert figures["identifiers"] == 6
    assert figures["distinct_identifiers"] == 3
    assert figures["distinct_identifiers_pct"] == pytest.approx(50.0, abs=0.01)
    # Only DT_CD occurs once, so one of the three distinct identifiers is hapax.
    assert figures["identifier_hapax"] == 1
    # TXN ID TXN ID TXN ID DT CD AMT AMT -> 10 occurrences, 5 distinct
    assert figures["token_occurrences"] == 10
    assert figures["distinct_tokens"] == 5
    assert figures["tokens_per_identifier"] == pytest.approx(1.667, abs=0.001)
    # DT and CD occur once each: two of five distinct tokens, two of ten occurrences
    assert figures["token_hapax"] == 2
    assert figures["token_hapax_pct_of_occurrences"] == pytest.approx(20.0, abs=0.01)


def test_the_census_reads_the_memo_limit_out_of_the_module() -> None:
    """A ceiling written down twice is a ceiling that goes stale in one of them."""
    from acronymkit.governed import dictionary as dictionary_module

    figures = perf.census(("TXN_ID", "DT_CD"))
    assert figures["memo_limit"] == dictionary_module._MEMO_LIMIT


def test_the_census_top_share_is_monotone() -> None:
    """``top5`` cannot exceed ``top20``; a ranking bug would show up here first."""
    corpus = tuple(f"TXN_{index}_ID" for index in range(200))
    figures = perf.census(corpus)
    assert (
        figures["top1_token_occurrence_pct"]
        <= figures["top5_token_occurrence_pct"]
        <= figures["top20_token_occurrence_pct"]
        <= figures["top100_token_occurrence_pct"]
        <= 100.0
    )


# ---------------------------------------------------------------------------
# the caller census
# ---------------------------------------------------------------------------


SAMPLE_CALLERS = """
from acronymkit.governed import expand_identifier

def reads_only_the_phrase(name, catalog):
    return expand_identifier(name, catalog).phrase

def binds_and_reads_provenance(name, catalog):
    result = expand_identifier(name, catalog)
    if not result.is_fully_known:
        return result.tokens
    return result.phrase

def binds_and_reads_only_the_phrase(name, catalog):
    result = expand_identifier(name, catalog)
    return result.phrase

def hands_it_onward(name, catalog):
    return [expand_identifier(name, catalog)]
"""


def test_the_caller_census_recognises_all_three_call_shapes(tmp_path: Path) -> None:
    """Attribute, bound, and everything else -- the third counted, never guessed at."""
    sample = tmp_path / "sample_callers.py"
    sample.write_text(SAMPLE_CALLERS, encoding="utf-8")
    sites = {line: (shape, fields) for line, shape, fields in perf.caller_sites(sample)}
    assert len(sites) == 4
    shapes = sorted(shape for shape, _ in sites.values())
    assert shapes == ["attribute", "bound", "bound", "unclassified"]

    phrase_only = [
        fields
        for shape, fields in sites.values()
        if fields and set(fields) <= perf.PHRASE_ONLY_FIELDS
    ]
    assert len(phrase_only) == 2
    provenance = [
        fields
        for shape, fields in sites.values()
        if fields and not set(fields) <= perf.PHRASE_ONLY_FIELDS
    ]
    assert len(provenance) == 1
    assert "is_fully_known" in provenance[0]


def test_a_call_whose_result_leaves_the_scope_is_unclassified_rather_than_zero(
    tmp_path: Path,
) -> None:
    """ "No fields read" and "the fields are not visible here" are different answers."""
    sample = tmp_path / "onward.py"
    sample.write_text(
        "from acronymkit.governed import expand_identifier\n"
        "def f(n, c):\n"
        "    return [expand_identifier(n, c)]\n",
        encoding="utf-8",
    )
    (_line, shape, fields) = perf.caller_sites(sample)[0]
    assert shape == "unclassified"
    assert fields == ()


def test_the_caller_census_excludes_the_runner_from_its_own_population() -> None:
    """A measurement that counts its own call sites is measuring itself.

    ``bench/run_governed_perf.py`` calls ``expand_identifier`` in the parity
    check and in ``stage_full``, and one of those reads only ``.phrase``. Left
    in, the harness would push the phrase-only share up by counting the
    instrument.
    """
    assert RUNNER.name in perf.CALLER_CENSUS_EXCLUDES
    own_sites = perf.caller_sites(RUNNER)
    assert own_sites, "the exclusion is only worth having while the runner has call sites"
    entry = perf.caller_census()
    assert entry["excludes"] == RUNNER.name


def test_the_caller_census_never_pools_the_suite_with_the_library() -> None:
    """Three groups, and the library's own callers are reported on their own."""
    labels = [label for label, _ in perf.CALLER_GROUPS]
    assert labels == ["library", "harness", "tests"]
    entry = perf.caller_census()
    for label in labels:
        assert (
            entry[f"{label}_classified"] + entry[f"{label}_unclassified"]
            == (entry[f"{label}_sites"])
        )
        assert (
            entry[f"{label}_phrase_only"] + entry[f"{label}_provenance_reading"]
            == (entry[f"{label}_classified"])
        )


# ---------------------------------------------------------------------------
# the inherited counts, and the dispersion
# ---------------------------------------------------------------------------


def test_the_inherited_counts_report_a_shortfall_rather_than_absorbing_it() -> None:
    """The two corpus sizes this phase was handed are claims, and one does not hold."""
    entry = perf.inherited_counts(("a", "b", "c"), ("d", "e"))
    assert entry["socrata_pairs_claimed"] == perf.INHERITED_SOCRATA_PAIRS
    assert entry["socrata_pairs_measured"] == 3
    assert entry["socrata_pairs_shortfall"] == perf.INHERITED_SOCRATA_PAIRS - 3
    assert entry["identifier_corpus_sources_present"] == len(perf.SNAPSHOTS)
    assert entry["identifier_corpus_sources_present"] < entry["identifier_corpus_sources_claimed"]
    assert entry["identifier_corpus_best_reconstruction"] == 5


def test_the_decomposition_reports_a_spread_and_not_a_point() -> None:
    """min <= median <= max on every centre, over a corpus small enough to be quick."""
    corpus = ("TXN_APPLNT_ID", "ADDR_LINE_1", "txn_dt") * 40
    figures = perf.decompose(corpus, catalog, rounds=2, repeats=1)
    assert figures["decomposition_rounds"] == 2
    for centre, _, _ in perf.CENTRES + perf.PROVENANCE_SPLIT:
        low = figures[f"stage_{centre}_pct_min"]
        mid = figures[f"stage_{centre}_pct"]
        high = figures[f"stage_{centre}_pct_max"]
        assert low <= mid <= high
    assert figures["phrase_only_speedup_min"] <= figures["phrase_only_speedup"]
    assert figures["phrase_only_speedup"] <= figures["phrase_only_speedup_max"]


def test_the_snapshot_map_names_a_file_rather_than_globbing_for_one() -> None:
    """Two snapshots of a live catalog are two populations; the choice is not implicit.

    ``bench/corpora.py`` raises when it finds more than one cached snapshot, and
    two Socrata files are on disk. This runner reads a named file for the same
    reason, and the name is pinned here so that a silent switch to whichever
    file sorts first would fail rather than move a published population.
    """
    assert perf.SNAPSHOTS["socrata"] == "socrata_80pages_v2.json"
    assert perf.SNAPSHOTS["sec_xbrl"] == "sec_xbrl_2025q1.json"


def test_an_unknown_corpus_name_is_refused() -> None:
    """A typo must not silently read nothing."""
    with pytest.raises(SystemExit):
        perf.read_snapshot("nope")


# ---------------------------------------------------------------------------
# the positive controls: every check above, shown capable of failing
# ---------------------------------------------------------------------------
#
# Operating rule 11 applies to a harness's internal checks as much as to a CI
# gate. Three assertions in this file are of the form "the excess is zero", and
# a check that can only ever report zero is indistinguishable from one that
# works. Each is therefore driven once against a deliberately broken stage.


def test_the_phrase_parity_check_can_report_a_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Substitute a reference that answers differently; the count must rise."""
    real = perf.expand_identifier

    def altered(name, dictionary, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = real(name, dictionary, *args, **kwargs)
        return result.model_copy(update={"phrase": result.phrase + "!"})

    clean = perf.verify_phrase_parity(CORPUS, catalog)
    monkeypatch.setattr(perf, "expand_identifier", altered)
    broken = perf.verify_phrase_parity(CORPUS, catalog)
    assert clean == 0
    # Every name disagrees, including the two whose real phrase is empty: "" and
    # "!" are different strings, which is the point of comparing bytes rather
    # than comparing something normalised.
    assert broken == len(CORPUS)


def test_the_lookup_excess_check_can_report_a_shortfall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stage that skips catalog lookups must show up as a negative excess."""
    shipped = perf.work_counts(CORPUS, catalog())["catalog_lookups"]

    def lazy(identifiers, dictionary):  # type: ignore[no-untyped-def]
        for name in identifiers:
            perf.split_identifier_parts(name)

    honest = perf.stage_phrase_counts(CORPUS, catalog())["stage_catalog_lookups"]
    monkeypatch.setattr(perf, "stage_phrase", lazy)
    skipped = perf.stage_phrase_counts(CORPUS, catalog())["stage_catalog_lookups"]
    assert honest - shipped == 0
    assert skipped - shipped < 0


def test_the_class_word_excess_check_can_report_a_shortfall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same control for the one lookup the class-word stage exists to add."""
    shipped = perf.work_counts(CORPUS, catalog())["class_word_lookups"]
    honest = perf.stage_class_word_counts(CORPUS, catalog())["stage_class_word_lookups"]
    assert honest - shipped == 0

    monkeypatch.setattr(perf, "stage_class_word", perf.stage_phrase)
    without = perf.stage_class_word_counts(CORPUS, catalog())["stage_class_word_lookups"]
    assert without == 0
    assert without - shipped < 0
