"""The catalog-gap report, pinned — because its whole value is that it is exact.

``acronymkit.governed.gap`` makes a stronger claim than anything else in this
package: not *this is usually right* but *no catalog-free method can ever reach
these columns*. A report that is merely usually right about that is worth
nothing, because the reader's next action is to spend somebody's afternoon
writing catalog rows.

So the tests here are about the boundary rather than about the happy path:

* **The column-level rule is a property of two strings**, and it is pinned in
  both directions — a label that only re-cuts the identifier is reachable, a
  label carrying one extra character is not, and neither verdict depends on
  case, separators or punctuation.
* **The token-level attribution is a necessary condition and not a sufficient
  one.** A column where every token *is* a label word must produce no work item
  at all, and must still be counted as unreachable. That is the quarter of the
  gap the ranked table does not carry, and a test that only checked the ranked
  table would have missed it.
* **The composition with ``tools/byoc_eval.py`` is checked by running both.**
  The two agree on ``columns`` and on ``unreachable``/``pairs_where_label_expands``
  or the sentence in ``docs/SOURCING.md`` that sends a stranger to both tools is
  false.
* **The work counts are asserted, not just present.** ``catalog_lookups`` is
  ``0`` with no catalog, and that zero is what "needs no catalog" means in work
  rather than in prose. R17.
* **Every filter is demonstrated capable of changing the answer**, because a
  knob that cannot move the output is a knob that was never wired up — and one
  of them moves it in a direction a reader would not guess, so the test says
  which way.

Nothing here reaches the network. The Socrata-scale figures live in
``bench/run_catalog_gap.py``; this file is about behaviour.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable, NamedTuple

import pytest

from acronymkit.cli import EXIT_OK, EXIT_USAGE, main
from acronymkit.exceptions import ConfigurationError
from acronymkit.governed import GovernedDictionary
from acronymkit.governed.gap import (
    CatalogGap,
    GapToken,
    catalog_gap,
    label_words,
    render_gap,
    stream_key,
)
from conftest import REPO_ROOT, requires_click

#: The bring-your-own-catalog kit, present in a checkout and absent from an
#: installed distribution. Only the one test that compares against it is skipped
#: when it is missing; the rest of this file is about the library.
KIT = REPO_ROOT / "tools" / "byoc_eval.py"

#: A small schema whose four columns cover the four outcomes exactly once:
#: reachable, unreachable-and-attributed, unreachable-and-unattributed, and a
#: second column sharing a token with the first unreachable one.
SCHEMA: tuple[tuple[str, str], ...] = (
    ("CUSTOMER_NAME", "Customer Name"),
    ("TXN_APPLNT_ID", "Transaction Applicant Identifier"),
    ("APPLNT_DT", "Applicant Date"),
    ("LEGAL_DESCRIPTION", "Property Legal Description"),
)


class Invocation(NamedTuple):
    """Outcome of one :func:`acronymkit.cli.main` call."""

    exit_code: int
    stdout: str
    stderr: str


@pytest.fixture
def run(capsys: pytest.CaptureFixture[str]) -> Callable[..., Invocation]:
    """Return a callable running ``main`` and capturing both streams."""

    def _run(*argv: str) -> Invocation:
        capsys.readouterr()
        code = main(list(argv))
        captured = capsys.readouterr()
        return Invocation(code, captured.out, captured.err)

    return _run


@pytest.fixture
def schema_csv(tmp_path: Path) -> Path:
    """:data:`SCHEMA` written as the two-column CSV both tools read."""
    path = tmp_path / "schema.csv"
    rows = "\n".join(f"{identifier},{label}" for identifier, label in SCHEMA)
    path.write_text(f"identifier,label\n{rows}\n", encoding="utf-8")
    return path


def tokens(gap: CatalogGap) -> list[str]:
    """The head's tokens, in the order the report ranked them."""
    return [row.token for row in gap.head]


# ---------------------------------------------------------------------------
# the two string rules
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("identifier", "label", "same"),
    [
        ("TXN_DT", "txn dt", True),
        ("TXN_DT", "Txn-Dt", True),
        ("TXN_DT", "TxnDt", True),
        ("TXN_DT", "Transaction Date", False),
        ("TXN_DT", "Txn Dt!", True),
        ("TXN_DT", "Txn Dts", False),
        ("n_mero", "Número", False),
    ],
)
def test_stream_key_is_invariant_to_cutting_and_casing_and_nothing_else(
    identifier: str, label: str, same: bool
) -> None:
    """Separators, punctuation and case may move; a character may not appear."""
    assert (stream_key(identifier) == stream_key(label)) is same


def test_label_words_does_not_fold_accents_away() -> None:
    """``Número`` is one word, not ``n`` and ``mero``.

    The ASCII rule ``tools/byoc_eval.py`` scores with splits it into fragments
    and then finds an identifier's fragments present, reporting a column as
    fully attributed when it is not. The distance between the two rules is
    measured at ``catalog_gap.socrata.label_word_rule``; this pins the direction.
    """
    assert label_words("Número") == frozenset({"número"})
    assert "mero" not in label_words("Número")
    assert label_words("E-mail (work)") == frozenset({"e", "mail", "work"})
    assert label_words(None) == frozenset()
    assert label_words("---") == frozenset()


# ---------------------------------------------------------------------------
# the classification
# ---------------------------------------------------------------------------
def test_the_four_outcomes_are_counted_exactly_once_each() -> None:
    """One reachable column, three unreachable, one of them with no work item."""
    gap = catalog_gap(SCHEMA)
    assert (gap.columns, gap.labelled_columns, gap.unlabelled_columns) == (4, 4, 0)
    assert gap.reachable_columns == 1
    assert gap.unreachable_columns == 3
    assert gap.attributed_columns + gap.unattributed_columns == gap.unreachable_columns


def test_a_label_that_says_more_than_the_identifier_carries_no_work_item() -> None:
    """``LEGAL_DESCRIPTION`` -> *Property Legal Description* is unreachable and unrankable.

    Every token of the identifier is a word of the label, so no token is
    individually a proof of impossibility — and the column is unreachable all
    the same, because the label carries a whole word the identifier does not.
    This is the case a report that only published the ranked table would lose.
    """
    gap = catalog_gap([("LEGAL_DESCRIPTION", "Property Legal Description")])
    assert gap.unreachable_columns == 1
    assert gap.unattributed_columns == 1
    assert gap.attributed_columns == 0
    assert gap.head == ()
    assert gap.unattributed_pct == 100.0


def test_a_token_that_is_a_label_word_never_reaches_the_work_list() -> None:
    """The necessary condition, in the direction that could produce a false work item."""
    gap = catalog_gap(SCHEMA)
    assert "customer" not in tokens(gap)
    assert "legal" not in tokens(gap)
    assert set(tokens(gap)) == {"applnt", "dt", "id", "txn"}


def test_ranking_is_by_columns_cleared_and_ties_break_by_token() -> None:
    """``applnt`` touches two columns and outranks the three that touch one."""
    gap = catalog_gap(SCHEMA)
    assert tokens(gap)[0] == "applnt"
    assert gap.head[0].columns == 2
    assert tokens(gap)[1:] == ["dt", "id", "txn"]


def test_occurrences_and_columns_are_different_numbers() -> None:
    """A token used twice in one column counts twice in one, once in the other."""
    gap = catalog_gap([("QTY_QTY_TOTAL", "Quantity Quantity Total")])
    row = next(item for item in gap.head if item.token == "qty")
    assert (row.columns, row.occurrences) == (1, 2)


def test_an_unlabelled_column_is_counted_and_not_classified() -> None:
    """No label, no verdict. Nothing here is guessed from an identifier alone."""
    gap = catalog_gap([("TXN_APPLNT_ID", ""), ("CUSTOMER_NAME", "Customer Name")])
    assert gap.columns == 2
    assert gap.unlabelled_columns == 1
    assert gap.labelled_columns == 1
    assert gap.unreachable_columns == 0
    assert gap.head == ()
    assert gap.classified_tokens == 2
    assert gap.distinct_tokens == 5


def test_rows_are_deduplicated_on_the_identifier_case_insensitively() -> None:
    """First occurrence wins, which is the rule ``tools/byoc_eval.py`` applies."""
    gap = catalog_gap(
        [
            ("TXN_DT", "Transaction Date"),
            ("txn_dt", "something else entirely"),
            ("", "Orphan"),
        ]
    )
    assert gap.rows_offered == 3
    assert gap.rows_duplicated == 1
    assert gap.rows_without_identifier == 1
    assert gap.columns == 1
    assert gap.head[0].example_label == "Transaction Date"


def test_an_unaccounted_character_is_reported_separately() -> None:
    """A character the tokenizer could not read is a second reason a trip cannot close."""
    gap = catalog_gap([("TXN@DT", "Transaction Date")])
    assert gap.columns_with_unaccounted == 1
    assert catalog_gap([("TXN_DT", "Transaction Date")]).columns_with_unaccounted == 0


# ---------------------------------------------------------------------------
# the catalog arm
# ---------------------------------------------------------------------------
def test_with_no_catalog_the_report_performs_zero_lookups() -> None:
    """R17: the zero is what "needs no catalog" means in work rather than in prose."""
    gap = catalog_gap(SCHEMA)
    assert gap.catalog_lookups == 0
    assert gap.catalog_covered_tokens == 0
    assert gap.work_list_tokens == gap.unreachable_tokens


def test_a_catalog_row_takes_its_token_off_the_work_list() -> None:
    """The one thing supplying a vocabulary changes, and it changes only that."""
    catalog = GovernedDictionary.from_mapping({"APPLNT": "Applicant"})
    gap = catalog_gap(SCHEMA, catalog)
    assert gap.catalog_lookups == gap.unreachable_tokens
    assert gap.catalog_covered_tokens == 1
    assert "applnt" not in tokens(gap)
    assert gap.work_list_tokens == gap.unreachable_tokens - 1


def test_the_catalog_does_not_change_the_column_level_verdict() -> None:
    """Reachability is a property of two strings; a vocabulary cannot move it."""
    catalog = GovernedDictionary.from_mapping({"APPLNT": "Applicant", "TXN": "Transaction"})
    bare, loaded = catalog_gap(SCHEMA), catalog_gap(SCHEMA, catalog)
    assert bare.unreachable_columns == loaded.unreachable_columns
    assert bare.reachable_columns == loaded.reachable_columns
    assert bare.unattributed_columns == loaded.unattributed_columns


# ---------------------------------------------------------------------------
# the ranking control
# ---------------------------------------------------------------------------
def test_the_greedy_control_can_beat_the_ranking_and_the_cost_is_their_difference() -> None:
    """A schema built so frequency picks a redundant token and a cover does not.

    ``a`` and ``b`` both break the same two columns; ``c`` breaks a third alone.
    With a budget of two, ranking by column count takes ``a`` and ``b`` and
    reaches two columns; a greedy cover takes ``a`` then ``c`` and reaches three.
    If this test ever reports no difference, the control has stopped controlling.
    """
    schema = [
        ("A_B_ONE", "Alpha"),
        ("A_B_TWO", "Alpha"),
        ("C_THREE", "Alpha"),
    ]
    gap = catalog_gap(schema, head=2)
    assert gap.head_columns == 2
    assert gap.greedy_columns == 3
    assert gap.ranking_cost_points == pytest.approx(
        round(gap.greedy_coverage_pct - gap.head_coverage_pct, 2)
    )
    assert gap.ranking_cost_points > 0
    assert gap.greedy_set_operations > 0


def test_the_greedy_control_reports_zero_cost_when_the_ranking_is_already_a_cover() -> None:
    """The other half of the control: it must be able to read zero."""
    gap = catalog_gap(SCHEMA, head=20)
    assert gap.head_columns == gap.greedy_columns == gap.work_list_columns
    assert gap.ranking_cost_points == 0.0


# ---------------------------------------------------------------------------
# the filters
# ---------------------------------------------------------------------------
def test_the_filters_move_a_column_out_of_the_ranked_table_and_into_the_residue() -> None:
    """Dropping a fragment does not make its column reachable; it makes it unrankable.

    This is the direction a reader would not guess and the reason the filters are
    off by default. ``1`` is the only token of ``ADDR_LINE_1`` missing from the
    label, so admitting it puts the column on the work list and excluding it
    moves the same column into ``unattributed_columns`` — the gap does not
    shrink, the accounting for it does.
    """
    schema = [("ADDR_LINE_1", "Addr Line")]
    loose = catalog_gap(schema)
    strict = catalog_gap(schema, min_token_length=2, require_letter=True)
    assert loose.unreachable_columns == strict.unreachable_columns == 1
    assert loose.attributed_columns == 1 and loose.unattributed_columns == 0
    assert strict.attributed_columns == 0 and strict.unattributed_columns == 1
    assert tokens(loose) == ["1"] and strict.head == ()


def test_the_head_counts_its_own_fragments() -> None:
    """A head full of single characters is debris, and the report says the number."""
    gap = catalog_gap([("A_B_1_CUSTMR", "Alpha Beta One Customer")])
    assert tokens(gap) == ["1", "a", "b", "custmr"]
    assert gap.head_single_character == 3
    assert gap.head_without_letter == 1
    assert "READ THIS FIRST" in render_gap(gap)


def test_a_clean_head_does_not_print_the_warning() -> None:
    """The warning has to be able to be absent, or it is decoration."""
    gap = catalog_gap([("CUSTMR_ADDR", "Customer Address")])
    assert (gap.head_single_character, gap.head_without_letter) == (0, 0)
    assert "READ THIS FIRST" not in render_gap(gap)


# ---------------------------------------------------------------------------
# refusals
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "kwargs",
    [
        {"head": -1},
        {"min_token_length": -1},
        {"max_examples": -1},
    ],
)
def test_negative_sizes_are_refused(kwargs: dict[str, int]) -> None:
    """A negative budget is a caller error, not a silently empty report."""
    with pytest.raises(ConfigurationError):
        catalog_gap(SCHEMA, **kwargs)


def test_a_dictionary_of_the_wrong_type_is_refused_and_none_is_not() -> None:
    """``None`` means *no catalog yet*, which is the case this report is for."""
    with pytest.raises(ConfigurationError) as caught:
        catalog_gap(SCHEMA, {"TXN": "Transaction"})  # type: ignore[arg-type]
    assert "GovernedDictionary or None" in str(caught.value)
    assert catalog_gap(SCHEMA, None).columns == 4


def test_an_empty_schema_reports_zeroes_rather_than_dividing_by_one() -> None:
    """Every percentage is defined on an empty corpus."""
    gap = catalog_gap([])
    assert gap.columns == 0
    assert gap.head_coverage_pct == gap.greedy_coverage_pct == gap.unattributed_pct == 0.0
    assert "nothing to write" in render_gap(gap)


# ---------------------------------------------------------------------------
# the record and its rendering
# ---------------------------------------------------------------------------
def test_the_record_round_trips_through_json() -> None:
    """It is a wire payload before it is a table, so the JSON shape is the contract."""
    gap = catalog_gap(SCHEMA)
    payload = json.loads(gap.to_json())
    assert payload["unreachable_columns"] == 3
    assert payload["head"][0]["token"] == "applnt"
    assert isinstance(payload["head"][0]["examples"], list)
    assert isinstance(GapToken(token="x", columns=1, occurrences=1), GapToken)


def test_render_names_the_residue_the_table_does_not_carry() -> None:
    """The unattributed count is on the report, not in a footnote somewhere else."""
    text = render_gap(catalog_gap(SCHEMA))
    assert "UNREACHABLE" in text
    assert "unattributed" in text
    assert "the label says more than the identifier" in text


def test_work_counts_are_per_distinct_column_not_per_occurrence() -> None:
    """R17, stated as an equality rather than as a claim in a docstring."""
    gap = catalog_gap((*SCHEMA, ("CUSTOMER_NAME", "Customer Name")))
    assert gap.tokenizer_passes == gap.columns == 4
    assert gap.label_word_sets == gap.unreachable_columns == 3
    assert gap.token_occurrences == 9


def test_module_doctests_pass() -> None:
    """The worked examples in ``gap.py`` are executed, not merely read."""
    import doctest

    from acronymkit.governed import gap as module

    results = doctest.testmod(module, verbose=False, report=False)
    assert results.failed == 0, f"{results.failed} doctest failure(s)"
    assert results.attempted > 0, "no doctests collected"


# ---------------------------------------------------------------------------
# composition with tools/byoc_eval.py
# ---------------------------------------------------------------------------
def _load_kit() -> ModuleType:
    """Import ``tools/byoc_eval.py`` by path, the way its own test does."""
    spec = importlib.util.spec_from_file_location("_byoc_eval_for_gap", KIT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(
    not KIT.is_file(), reason="tools/ belongs to a checkout, not to an installed distribution"
)
def test_the_two_tools_put_the_same_numbers_under_the_same_population() -> None:
    """``docs/SOURCING.md`` sends a stranger to both over one CSV. Checked by running both.

    Agreement on the *column* count and on the *expanding* count is the whole of
    the composition claim: the gap report says what a glossary would have to
    contain and the kit says what one is worth, and a reader comparing the two
    outputs must not have to reconcile two denominators.
    """
    kit = _load_kit()
    scored = 0
    expanding = 0
    seen: set[str] = set()
    for identifier, label in SCHEMA:
        if identifier.casefold() in seen:
            continue
        seen.add(identifier.casefold())
        scored += 1
        if kit.stream_key(identifier) != kit.stream_key(label):
            expanding += 1
    gap = catalog_gap(SCHEMA)
    assert gap.labelled_columns == scored
    assert gap.unreachable_columns == expanding


# ---------------------------------------------------------------------------
# the command line
# ---------------------------------------------------------------------------
@requires_click
def test_cli_reports_without_a_dictionary(run: Callable[..., Invocation], schema_csv: Path) -> None:
    """The one governed command that does not require ``--dictionary``."""
    outcome = run("governed-gap", str(schema_csv))
    assert outcome.exit_code == EXIT_OK
    assert "catalog gap" in outcome.stdout
    assert "applnt" in outcome.stdout


@requires_click
def test_cli_json_is_the_record(run: Callable[..., Invocation], schema_csv: Path) -> None:
    """``--format json`` emits the payload, not a rendering of it."""
    outcome = run("governed-gap", str(schema_csv), "--format", "json")
    assert outcome.exit_code == EXIT_OK
    payload = json.loads(outcome.stdout)
    assert payload["columns"] == 4
    assert payload["unreachable_columns"] == 3
    assert payload["catalog_lookups"] == 0


@requires_click
def test_cli_names_the_columns_it_could_not_find(
    run: Callable[..., Invocation], tmp_path: Path
) -> None:
    """A CSV with the wrong headers is a usage error that says which headers it has."""
    path = tmp_path / "wrong.csv"
    path.write_text("col,caption\nTXN_DT,Transaction Date\n", encoding="utf-8")
    outcome = run("governed-gap", str(path))
    assert outcome.exit_code == EXIT_USAGE
    assert "identifier" in outcome.stderr
    assert "col, caption" in outcome.stderr


@requires_click
def test_cli_accepts_the_alternate_column_names(
    run: Callable[..., Invocation], tmp_path: Path
) -> None:
    """The escape hatch the previous test points at actually works."""
    path = tmp_path / "wrong.csv"
    path.write_text("col,caption\nTXN_DT,Transaction Date\n", encoding="utf-8")
    outcome = run(
        "governed-gap",
        str(path),
        "--identifier-column",
        "col",
        "--label-column",
        "caption",
        "--format",
        "json",
    )
    assert outcome.exit_code == EXIT_OK
    assert json.loads(outcome.stdout)["unreachable_columns"] == 1


@requires_click
def test_cli_filters_reach_the_report(run: Callable[..., Invocation], tmp_path: Path) -> None:
    """``--min-token-length`` and ``--require-letter`` change the payload."""
    path = tmp_path / "schema.csv"
    path.write_text("identifier,label\nADDR_LINE_1,Addr Line\n", encoding="utf-8")
    loose = json.loads(run("governed-gap", str(path), "--format", "json").stdout)
    strict = json.loads(
        run(
            "governed-gap",
            str(path),
            "--min-token-length",
            "2",
            "--require-letter",
            "--format",
            "json",
        ).stdout
    )
    assert loose["attributed_columns"] == 1
    assert strict["attributed_columns"] == 0
    assert loose["unreachable_columns"] == strict["unreachable_columns"] == 1


@requires_click
def test_cli_takes_a_dictionary_when_one_exists(
    run: Callable[..., Invocation], tmp_path: Path, schema_csv: Path
) -> None:
    """Supplying a vocabulary marks the rows it already covers and nothing else."""
    catalog = tmp_path / "nds.json"
    catalog.write_text(json.dumps({"APPLNT": "Applicant"}), encoding="utf-8")
    outcome = run("governed-gap", str(schema_csv), "--dictionary", str(catalog), "--format", "json")
    assert outcome.exit_code == EXIT_OK
    payload = json.loads(outcome.stdout)
    assert payload["catalog_covered_tokens"] == 1
    assert payload["catalog_lookups"] == payload["unreachable_tokens"]
    assert "applnt" not in [row["token"] for row in payload["head"]]
