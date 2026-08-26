"""The bring-your-own-catalog kit, pinned — because a stranger runs this once and never again.

``tools/byoc_eval.py`` exists to close the standing unknown ``docs/POSITIONING.md``
names as the first cost of the governance commitment: nobody has measured whether
a real governed catalog beats an empty one on a real schema. The kit turns the ask
from *send us your proprietary glossary* into *run this and send two numbers*, and
that trade only holds if two properties hold with it.

What this file pins, and why each item is here
----------------------------------------------
* **The report may not carry a string from the input.** That is the whole basis
  on which somebody agrees to run it, and it is enforced by an allow-list in
  :func:`~tools.byoc_eval.redaction_problems` rather than by a scan for
  known-bad content. So it is tested in both directions: a clean report passes,
  and a report carrying a column name, a label, a glossary term or a leaked
  dictionary **key** is refused and named. Operating rule 11 applies to a guard
  as much as to a CI gate — it is demonstrated capable of failing here, in the
  process that runs it, by mutation, with the refusal captured.

* **A run that never fired must not read as a run that found no difference.**
  Those are opposite findings and they produce identical tables: zero delta,
  zero discordant pairs. The verdict set separates them and the ordering is
  tested, because operating rule 12 is the rule this project keeps having to
  re-learn and this is the first place it has been mechanised into a shipped
  artifact.

* **The circularity check has to be able to read zero.** The August 2026 audit's
  catalog was inferred from the labels it was scored against, which is why its
  result was thrown away. A leakage detector that always reported ``100`` would
  be indistinguishable from a working one on that catalog, so a control catalog
  whose expansions appear in no label must read ``0``.

* **The sample-size constant is derived, not chosen.**
  ``MIN_DISCORDANT_PAIRS`` must equal what ``power_table`` computes, so a later
  edit that nudges the constant without redoing the power analysis turns the
  build red. The two-column shape is pinned too: the exact test's power is not
  monotone in ``n``, and a criterion set at the first crossing sits at a sample
  size the test dips back below.

* **The metrics do not report ``null`` where they mean zero.** An arm that
  predicted words and hit none of them has an F1 of ``0.0``. The first draft
  stored ``null`` there, and the shipped fixture printed it — a real result
  reading as an absent one, which is the same defect class as an empty subset
  reading as a total failure.

Nothing here reaches the network, and nothing writes outside ``tmp_path``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
KIT = REPO_ROOT / "tools" / "byoc_eval.py"

# `pytest.mark.skipif` is consulted at COLLECTION and a module body runs at
# IMPORT, which is earlier. `tools/` ships in the sdist and is no part of an
# installed distribution, so under the `installed-suite` job the load below
# would raise FileNotFoundError and this file would fail to COLLECT rather than
# skip. Same shape as `tests/test_gate_manifest.py`, and for the same reason.
#
# ONE named condition, deliberately. A module-wide blanket is what hid 74 tests
# in `tests/test_splits_manifest.py`; any other error here must still reach the
# job, and `EXPECTED_NON_PASSING` is not grown for this file.
if not KIT.is_file():  # pragma: no cover - CI job only
    pytest.skip(
        "tools/ is not part of an installed distribution; these tests belong to a checkout",
        allow_module_level=True,
    )


def _load_tool() -> ModuleType:
    """Import ``tools/byoc_eval.py`` by path.

    ``tools/`` is a directory of scripts and must not become a package: making
    it importable for a test's convenience would change the shape of the thing
    under test. Same mechanism as ``tests/test_gate_manifest.py``.
    """
    spec = importlib.util.spec_from_file_location("_byoc_eval_under_test", KIT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before execution: ``@dataclass`` resolves annotations through
    # ``sys.modules[cls.__module__]`` while the class body is still running.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


byoc = _load_tool()


def _write(path: Path, text: str) -> Path:
    """Write a CSV fixture and return its path."""
    path.write_text(text, encoding="utf-8")
    return path


SCHEMA_CSV = (
    "identifier,label\n"
    "TXN_ID,Transaction Identifier\n"
    "ACCT_BAL,Account Balance\n"
    "customer_name,Customer Name\n"
)

CATALOG_CSV = "token,expansion\nTXN,Transaction\nID,Identifier\nACCT,Account\nBAL,Balance\n"


# ---------------------------------------------------------------------------
# the property somebody agrees to run this on
# ---------------------------------------------------------------------------
class TestNothingButNumbersLeaves:
    """The report must carry no string the caller supplied."""

    def test_a_clean_report_passes(self) -> None:
        report = byoc.build_report(byoc.POSITIVE_SCHEMA, byoc.POSITIVE_CATALOG)
        assert byoc.redaction_problems(report) == []

    def test_a_leaked_value_is_named(self) -> None:
        """The guard is demonstrated capable of failing, by mutation, here."""
        report: Dict[str, Any] = byoc.build_report(byoc.POSITIVE_SCHEMA, byoc.POSITIVE_CATALOG)
        report["arms"]["all"]["worst_identifier"] = "PATIENT_MRN_HASHED"
        problems = byoc.redaction_problems(report)
        assert problems, "a column name reached the report and the guard did not say so"
        assert any("PATIENT_MRN_HASHED" in problem for problem in problems)

    def test_a_leaked_key_is_named(self) -> None:
        report: Dict[str, Any] = byoc.build_report(byoc.POSITIVE_SCHEMA, byoc.POSITIVE_CATALOG)
        report["by_column"] = {"Patient Medical Record Number": 3}
        problems = byoc.redaction_problems(report)
        assert any("Patient Medical Record Number" in problem for problem in problems)

    def test_a_leaked_value_nested_in_a_list_is_named(self) -> None:
        report: Dict[str, Any] = byoc.build_report(byoc.POSITIVE_SCHEMA, byoc.POSITIVE_CATALOG)
        report["examples"] = [{"label": "Reinsurance Recoverable Balance"}]
        assert byoc.redaction_problems(report)

    def test_digests_timestamps_and_versions_are_allowed(self, tmp_path: Path) -> None:
        """The allow-list must not be so tight that a real report cannot pass."""
        schema = _write(tmp_path / "s.csv", SCHEMA_CSV)
        catalog = _write(tmp_path / "c.csv", CATALOG_CSV)
        rows = byoc.read_schema(schema, identifier_column="identifier", label_column="label")
        mapping = byoc.read_catalog(catalog, token_column="token", expansion_column="expansion")
        report = byoc.build_report(
            rows.pairs,
            mapping,
            rows=rows,
            schema_digest=byoc.digest(schema),
            catalog_digest=byoc.digest(catalog),
        )
        assert byoc.redaction_problems(report) == []
        assert byoc._SHA256.match(report["inputs"]["schema_sha256"])
        assert byoc._TIMESTAMP.match(report["kit"]["generated_utc"])

    def test_the_declared_key_set_is_neither_stale_nor_short(self) -> None:
        """Both directions, because a declaration only checked one way rots quietly.

        Short: a key the report writes but nobody declared would be refused at
        the moment somebody runs this for real, which is the worst moment to
        find out. Stale: a declared key no report carries is a hole standing
        open for a future field to occupy without review.
        """

        def keys_of(node: object) -> set:
            found: set = set()
            if isinstance(node, dict):
                for key, value in node.items():
                    found.add(key)
                    found |= keys_of(value)
            return found

        shipped = keys_of(byoc.build_report(byoc.POSITIVE_SCHEMA, byoc.POSITIVE_CATALOG))
        shipped |= keys_of(byoc.build_report(byoc.NEGATIVE_SCHEMA, byoc.POSITIVE_CATALOG))
        declared = set(byoc._ALLOWED_REPORT_KEYS)
        assert shipped - declared == set(), "the report writes a key nobody declared"
        assert declared - shipped == set(), "a declared key no report carries"

    def test_main_refuses_to_write_a_leaking_report(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """In situ: the refusal is exercised through ``main``, not through the guard alone.

        A guard tested only by direct call proves the guard works, not that the
        entry point consults it. This mutates the body builder so the report
        carries a label, drives ``main``, and requires a non-zero exit **and**
        no file on disk.
        """
        schema = _write(tmp_path / "s.csv", SCHEMA_CSV)
        catalog = _write(tmp_path / "c.csv", CATALOG_CSV)
        out = tmp_path / "report.json"

        original = byoc.evaluate

        def leaking(pairs: Any, catalog_mapping: Any) -> Dict[str, Any]:
            body = original(pairs, catalog_mapping)
            body["oops"] = "Applicant Verification Date"
            return body

        monkeypatch.setattr(byoc, "evaluate", leaking)
        code = byoc.main(["--schema", str(schema), "--catalog", str(catalog), "--out", str(out)])
        captured = capsys.readouterr()
        assert code == 1
        assert not out.exists()
        assert "REPORT NOT WRITTEN" in captured.err

    def test_the_same_run_writes_the_report_once_the_mutation_is_reverted(
        self, tmp_path: Path
    ) -> None:
        """The other half of the mutation: restored, the same command succeeds."""
        schema = _write(tmp_path / "s.csv", SCHEMA_CSV)
        catalog = _write(tmp_path / "c.csv", CATALOG_CSV)
        out = tmp_path / "report.json"
        assert (
            byoc.main(["--schema", str(schema), "--catalog", str(catalog), "--out", str(out)]) == 0
        )
        assert byoc.redaction_problems(json.loads(out.read_text(encoding="utf-8"))) == []


# ---------------------------------------------------------------------------
# the firing count, and the verdict that depends on it
# ---------------------------------------------------------------------------
class TestTheFiringCountComesFirst:
    """Operating rule 12, mechanised: zero firings is not a null result."""

    def test_a_catalog_that_never_fires_says_it_measured_nothing(self) -> None:
        report = byoc.build_report(byoc.NEGATIVE_SCHEMA, byoc.POSITIVE_CATALOG)
        assert report["firing"]["catalog_fired_pairs"] == 0
        assert report["firing"]["nothing_measured"] is True
        assert report["firing"]["note"] == byoc.NOTHING_MEASURED_SENTENCE
        assert report["verdict"] == byoc.VERDICT_NOTHING_MEASURED

    def test_that_run_is_not_reported_as_no_difference(self) -> None:
        """The two findings look identical in a table and must not share a verdict."""
        report = byoc.build_report(byoc.NEGATIVE_SCHEMA, byoc.POSITIVE_CATALOG)
        assert report["verdict"] != byoc.VERDICT_NO_DIFFERENCE
        assert report["paired"]["exact_pct_delta"] == 0.0
        assert report["paired"]["discordant_pairs"] == 0

    def test_the_sentence_is_printed_not_only_stored(self) -> None:
        report = byoc.build_report(byoc.NEGATIVE_SCHEMA, byoc.POSITIVE_CATALOG)
        assert byoc.NOTHING_MEASURED_SENTENCE in byoc.render(report)

    def test_no_catalog_at_all_is_its_own_verdict(self) -> None:
        report = byoc.build_report(byoc.POSITIVE_SCHEMA, {})
        assert report["verdict"] == byoc.VERDICT_NO_CATALOG

    def test_firing_counts_entries_not_only_rows(self) -> None:
        report = byoc.build_report(byoc.POSITIVE_SCHEMA, byoc.POSITIVE_CATALOG)
        assert report["firing"]["catalog_fired_pairs"] == len(byoc.POSITIVE_SCHEMA)
        assert report["firing"]["catalog_entries_that_fired"] == len(byoc.POSITIVE_CATALOG)


@pytest.mark.parametrize(
    "has_catalog, fired, discordant, catalog_only, expected",
    [
        (False, 0, 0, 0, byoc.VERDICT_NO_CATALOG),
        (True, 0, 0, 0, byoc.VERDICT_NOTHING_MEASURED),
        (True, 10, 8, 8, byoc.VERDICT_UNDERPOWERED),
        (True, 400, 60, 30, byoc.VERDICT_NO_DIFFERENCE),
        (True, 400, 60, 45, byoc.VERDICT_CATALOG_BETTER),
        (True, 400, 60, 15, byoc.VERDICT_EMPTY_BETTER),
    ],
)
def test_verdict_ordering(
    has_catalog: bool, fired: int, discordant: int, catalog_only: int, expected: str
) -> None:
    """The cheapest disqualification wins, so a weak run cannot borrow a strong verdict."""
    assert byoc.verdict_for(has_catalog, fired, discordant, catalog_only) == expected


# ---------------------------------------------------------------------------
# the circularity check
# ---------------------------------------------------------------------------
class TestTheCircularityCheck:
    """A detector that always reads 100 cannot tell a circular catalog from a real one."""

    def test_a_catalog_read_off_the_labels_reads_high(self) -> None:
        found = byoc.leakage(byoc.POSITIVE_CATALOG, byoc.POSITIVE_SCHEMA)
        assert found["entries_present_in_gold_pct"] == 100.0

    def test_a_catalog_that_is_not_reads_zero(self) -> None:
        found = byoc.leakage(byoc.LEAKAGE_CONTROL_CATALOG, byoc.POSITIVE_SCHEMA)
        assert found["entries_present_in_gold_pct"] == 0.0

    def test_a_multi_word_expansion_is_matched_as_a_run_not_as_words(self) -> None:
        """``Transaction Amount`` must not count as present because both words occur apart."""
        pairs = (("A", "Transaction Identifier"), ("B", "Account Amount"))
        found = byoc.leakage({"TA": "Transaction Amount"}, pairs)
        assert found["entries_present_in_gold"] == 0

    def test_an_empty_catalog_reads_null_rather_than_zero(self) -> None:
        found = byoc.leakage({}, byoc.POSITIVE_SCHEMA)
        assert found["entries_present_in_gold_pct"] is None


# ---------------------------------------------------------------------------
# the statistics
# ---------------------------------------------------------------------------
class TestThePairedTest:
    """McNemar exact, and the sample size it implies."""

    @pytest.mark.parametrize(
        "successes, trials, expected",
        [
            (0, 0, None),
            (0, 1, 1.0),
            (1, 1, 1.0),
            (0, 8, 2.0 / 256),
            (4, 8, 1.0),
            (8, 8, 2.0 / 256),
        ],
    )
    def test_known_values(self, successes: int, trials: int, expected: float) -> None:
        found = byoc.exact_binomial_two_sided(successes, trials)
        if expected is None:
            assert found is None
        else:
            assert found == pytest.approx(expected)

    def test_no_discordant_pairs_is_not_a_p_value_of_one(self) -> None:
        """The absence of a test and a test that failed to reject are different facts."""
        assert byoc.exact_binomial_two_sided(0, 0) is None

    def test_the_minimum_is_derived_from_the_power_table(self) -> None:
        rows = {row["effect"]: row for row in byoc.power_table()}
        assert rows[byoc.POWER_EFFECT]["stable_n_at_target"] == byoc.MIN_DISCORDANT_PAIRS

    def test_power_is_not_monotone_so_the_two_columns_differ(self) -> None:
        """If they were equal, the second column would be decoration."""
        rows = byoc.power_table()
        assert any(row["stable_n_at_target"] != row["first_n_at_target"] for row in rows)
        for row in rows:
            assert row["stable_n_at_target"] >= row["first_n_at_target"]

    def test_power_at_the_stable_count_meets_the_target(self) -> None:
        for row in byoc.power_table():
            assert row["power_at_stable_n"] >= byoc.POWER_TARGET


# ---------------------------------------------------------------------------
# the metrics
# ---------------------------------------------------------------------------
class TestTheMetrics:
    """What the two numbers mean, pinned so a later edit cannot redefine them quietly."""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("Transaction Identifier", ["transaction", "identifier"]),
            ("transaction  identifier", ["transaction", "identifier"]),
            ("Transaction-Identifier", ["transaction", "identifier"]),
            ("  ", []),
        ],
    )
    def test_typography_is_not_scored(self, text: str, expected: list) -> None:
        assert byoc.words(text) == expected

    def test_stream_key_separates_expansion_from_cut_placement(self) -> None:
        assert byoc.stream_key("END_DATE") == byoc.stream_key("End Date")
        assert byoc.stream_key("DT") != byoc.stream_key("Date")

    def test_an_arm_that_hits_nothing_reports_zero_f1_not_null(self) -> None:
        """The first draft stored ``null`` here and the shipped fixture printed it."""
        tally = byoc.Tally()
        tally.add(exact=False, fully_known=False, hits=0, predicted=2, gold=2)
        assert tally.as_dict()["word_f1_pct"] == 0.0

    def test_an_arm_that_was_never_asked_reports_null_not_zero(self) -> None:
        assert byoc.Tally().as_dict()["exact_pct"] is None
        assert byoc.Tally().as_dict()["word_f1_pct"] is None

    def test_the_subsets_are_nested_the_way_the_report_claims(self) -> None:
        report = byoc.build_report(byoc.POSITIVE_SCHEMA, byoc.POSITIVE_CATALOG)
        assert (
            report["arms"]["fired"]["catalog"]["pairs"] <= report["arms"]["all"]["catalog"]["pairs"]
        )
        assert (
            report["arms"]["expanding"]["catalog"]["pairs"]
            <= report["arms"]["all"]["catalog"]["pairs"]
        )

    def test_a_schema_already_spelled_out_is_reported_as_such(self) -> None:
        report = byoc.build_report(byoc.NEGATIVE_SCHEMA, byoc.POSITIVE_CATALOG)
        assert report["population"]["pairs_where_label_expands"] == 0


# ---------------------------------------------------------------------------
# input handling
# ---------------------------------------------------------------------------
class TestInput:
    """A stranger's first run fails on their column names, and must say so."""

    def test_a_missing_column_names_the_header_it_found(self, tmp_path: Path) -> None:
        schema = _write(tmp_path / "s.csv", "col,caption\nTXN_ID,Transaction Identifier\n")
        with pytest.raises(KeyError) as error:
            byoc.read_schema(schema, identifier_column="identifier", label_column="label")
        assert "col" in str(error.value) and "caption" in str(error.value)

    def test_blank_and_duplicate_rows_are_counted_not_dropped_silently(
        self, tmp_path: Path
    ) -> None:
        schema = _write(
            tmp_path / "s.csv",
            "identifier,label\n"
            "TXN_ID,Transaction Identifier\n"
            "TXN_ID,Transaction Id\n"
            ",Orphan Label\n"
            "NO_LABEL,\n",
        )
        rows = byoc.read_schema(schema, identifier_column="identifier", label_column="label")
        assert rows.rows_read == 4
        assert len(rows.pairs) == 1
        assert rows.rejected == {
            "duplicate_identifier": 1,
            "empty_identifier": 1,
            "empty_label": 1,
        }

    def test_rejection_reasons_are_module_constants_and_survive_redaction(
        self, tmp_path: Path
    ) -> None:
        schema = _write(tmp_path / "s.csv", "identifier,label\n,Orphan Label\nA,Alpha\n")
        rows = byoc.read_schema(schema, identifier_column="identifier", label_column="label")
        report = byoc.build_report(rows.pairs, {}, rows=rows)
        assert report["inputs"]["schema_rows_rejected"] == {"empty_identifier": 1}
        assert byoc.redaction_problems(report) == []

    def test_the_template_round_trips_through_the_reader(self, tmp_path: Path) -> None:
        assert byoc.main(["--template", str(tmp_path / "example")]) == 0
        rows = byoc.read_schema(
            tmp_path / "example" / "schema.csv",
            identifier_column="identifier",
            label_column="label",
        )
        mapping = byoc.read_catalog(
            tmp_path / "example" / "catalog.csv",
            token_column="token",
            expansion_column="expansion",
        )
        assert len(rows.pairs) == len(byoc.POSITIVE_SCHEMA)
        assert mapping == byoc.POSITIVE_CATALOG

    def test_an_unreadable_schema_exits_one_rather_than_raising(self, tmp_path: Path) -> None:
        assert byoc.main(["--schema", str(tmp_path / "absent.csv")]) == 1

    def test_a_schema_with_no_scorable_row_exits_one(self, tmp_path: Path) -> None:
        schema = _write(tmp_path / "s.csv", "identifier,label\n,\n")
        assert byoc.main(["--schema", str(schema)]) == 1


# ---------------------------------------------------------------------------
# the whole thing, end to end
# ---------------------------------------------------------------------------
class TestEndToEnd:
    """What the person on the other end of the ask actually runs."""

    def test_self_test_passes_and_carries_its_own_negative_control(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert byoc.main(["--self-test"]) == 0
        captured = capsys.readouterr().out
        assert "SELF-TEST PASSED" in captured
        assert "negative control" in captured

    def test_power_mode_prints_the_constant_it_derives(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert byoc.main(["--power"]) == 0
        assert str(byoc.MIN_DISCORDANT_PAIRS) in capsys.readouterr().out

    def test_a_full_run_writes_a_parseable_report(self, tmp_path: Path) -> None:
        schema = _write(tmp_path / "s.csv", SCHEMA_CSV)
        catalog = _write(tmp_path / "c.csv", CATALOG_CSV)
        out = tmp_path / "report.json"
        assert (
            byoc.main(["--schema", str(schema), "--catalog", str(catalog), "--out", str(out)]) == 0
        )
        report = json.loads(out.read_text(encoding="utf-8"))
        assert report["firing"]["catalog_fired_pairs"] == 2
        assert report["arms"]["all"]["catalog"]["pairs"] == 3
        assert report["inputs"]["schema_rows_scored"] == 3

    def test_two_runs_on_one_input_agree_on_everything_but_the_clock(self, tmp_path: Path) -> None:
        """A report that moved between runs would not be a measurement of anything."""
        schema = _write(tmp_path / "s.csv", SCHEMA_CSV)
        catalog = _write(tmp_path / "c.csv", CATALOG_CSV)
        rows = byoc.read_schema(schema, identifier_column="identifier", label_column="label")
        mapping = byoc.read_catalog(catalog, token_column="token", expansion_column="expansion")
        first = byoc.build_report(rows.pairs, mapping, rows=rows)
        second = byoc.build_report(rows.pairs, mapping, rows=rows)
        first["kit"].pop("generated_utc")
        second["kit"].pop("generated_utc")
        assert first == second

    def test_the_kit_imports_nothing_that_could_reach_a_network(self) -> None:
        """The offer is that the data never moves; an import of ``urllib`` would end it."""
        source = KIT.read_text(encoding="utf-8")
        for banned in ("import urllib", "import socket", "import http", "import requests"):
            assert banned not in source, f"{KIT.name} names {banned!r}"
