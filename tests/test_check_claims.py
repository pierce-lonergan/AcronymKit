"""Tests for ``tools/check_claims.py``, the gate every other number depends on.

This tool decides whether a performance figure in the README, in ``docs/`` or in
a docstring is allowed to exist. It has caught real drift four times and it had
no tests at all, which means the one check that adjudicates every claim in the
project was itself unadjudicated.

What is pinned here:

* **Citation resolution is strict.** ``{{claim:<run id>.<field>}}`` resolves
  against ``bench/results.json`` or the build fails -- including the three ways
  it can fail (no such run, no such field, a group rather than a measurement)
  and the fourth that only exists once documents are rendered (a rendered value
  that has gone stale). This is the property value matching can never have.
* **Value matching still backs the claims already written.** Roughly seventy of
  them, in files this change deliberately does not touch. A flag day would be
  worse than the unsoundness, so the fallback stays and is *counted* instead.
* **The ambiguity report is honest.** A value with several unrelated
  measurements behind it is reported ``AMBIGUOUS``, because value matching
  cannot have verified it.
* **``--render`` is idempotent and can be dry-run.** A docs generator that
  cannot be dry-run will not be trusted, and one that is not idempotent cannot
  be run in CI.
* **The not-a-claim cases stay out.** ``R@25``, ``D-012``, ``MED1250``,
  ``9:402``, ``f1`` inside a filename, and numbers inside code. Each of these
  used to be flagged; each is excluded by a structural rule rather than by a
  special case for a character, so the next identifier of that shape is
  excluded too.
* **Nothing is dropped silently.** A prose number no arming rule reaches is
  recorded as ``unexamined``, counted, and listed -- and never value-matched,
  because a number nobody looked at must not acquire a "backed" label from a
  coincidence. ``TestArming`` and ``TestUnexamined``.
* **Both ratchets, both directions.** ``TestRatchets`` drives
  ``baseline_problems`` on a project with the baselines armed, which
  ``Project.at`` does only for the real checkout. That left R1's mechanism
  reachable only where it is green by construction, so it had no test at all.
* **A widened gate may not soften a verdict it had already reached.**
  ``TestCoverageMayNotWeakenAVerdict`` pins the case that forced the rule: a
  keyword-armed number matching no measurement still fails hard, even in a file
  the value ledger never named.
* **The burn-down has a rate, and the rate is checked.** ``TestLedgerTrajectory``
  drives ``trajectory_problems`` through all four of its rules, in both
  directions, on synthetic trajectories -- and then asserts the *recorded* one
  agrees with the live baselines, which is what makes a future migration that
  forgets to append a round fail in CI rather than only under someone's eye.
* **The classification says which verdicts it derived and which a person
  assigned.** ``TestDetectors`` pins where each structural rule must *decline*
  -- a date part that is also a count, a dotted number with no version context,
  and above all a unit-armed number, which no detector may reach at all.
  ``TestClassifyDebt`` pins that an unarmed number can never be called
  ``gate-able``, which is D-052's refusal to value-match the residue, restated
  where it would be easiest to lose.
* **A judgement is anchored to a sentence, not to a line.** The first draft
  keyed on ``<path>:<line>:<number>`` and an entry went stale inside one
  session, because a workstream inserted seven lines above it in a file nobody
  had touched. Two tests pin the replacement: a judgement survives its sentence
  moving, and is reported stale when its sentence is gone.

Every fixture is a synthetic project under ``tmp_path``, so nothing here
depends on today's contents of ``bench/results.json`` -- except the one test
that deliberately does, which asserts the real checkout is green. The fixtures
are checked for *absence* of a metric keyword where a test is about the unit
rule: several first drafts armed on a keyword nobody noticed was there
(``throughput``, ``docs/s``), which would have made the test pass for the wrong
reason.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from fnmatch import fnmatch
from pathlib import Path
from types import ModuleType
from typing import Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_PATH = REPO_ROOT / "tools" / "check_claims.py"


def _load_tool() -> ModuleType:
    """Import ``tools/check_claims.py`` by path.

    ``tools/`` is not a package and must not become one: it is a directory of
    scripts, and making it importable for the benefit of a test would be the
    test changing the shape of the thing it tests.
    """
    spec = importlib.util.spec_from_file_location("_check_claims_under_test", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# THE SAME GUARD THE `bench/` LOAD BELOW ALREADY CARRIES, FINALLY APPLIED TO THE
# `tools/` LOAD ITSELF. `tools/` ships in the sdist and is no part of an
# installed distribution, so under the installed-suite CI job the next line
# raises `FileNotFoundError` and this file fails to COLLECT. It has been covered
# by a file-keyed entry in `EXPECTED_NON_PASSING` in `.github/workflows/ci.yml`,
# and that list's own comment records what the entry cost: while a FILE sits
# there the job cannot see a second defect anywhere in it -- measured, by
# reintroducing a real breakage into a listed file and getting a run identical
# to a clean one. A skip on one named condition absorbs that condition and
# nothing else, so any other error here now reaches the job. The entry is
# deleted in the same commit.
if not TOOL_PATH.is_file():  # pragma: no cover - CI job only
    pytest.skip(
        "tools/ is not part of an installed distribution; these tests belong to a checkout",
        allow_module_level=True,
    )

check_claims = _load_tool()


#: A small results document with deliberate structure:
#:
#: * ``83.85`` is unique -- one measurement has it.
#: * ``92.32`` is replicated -- the same field, recorded by two runs.
#: * ``76.99`` is ambiguous -- an F1 and a recall happen to share it.
RESULTS = {
    "environment": "test",
    "runs": {
        "extraction.med1250.acronymkit": {
            "corpus": "med1250",
            "docs_per_second": 4218.9,
            "exact_f1": 83.85,
            "exact_precision": 92.32,
            "exact_recall": 76.99,
            "gold_pairs": 1221,
        },
        "profile.med1250_test.high_precision": {
            "exact_precision": 92.32,
            "exact_f1": 76.99,
        },
        "generation.med1250.coverage.ceiling": {
            "never_produced_pct": 0.0934,
        },
        "disambiguation.sdu21.acronymkit": {
            "accuracy_by_candidate_count": {"2": 55.28, "10+": 27.11},
        },
    },
}


def make_project(
    root: Path,
    files: Optional[dict] = None,
    *,
    results: Optional[dict] = None,
    allowlist: Optional[str] = None,
) -> Path:
    """Write a synthetic checkout the tool can be pointed at.

    Args:
        root: Directory to build in.
        files: ``{relative path: contents}`` for the files to scan.
        results: The ``bench/results.json`` document. Defaults to ``RESULTS``.
        allowlist: Contents of ``tools/claims_allowlist.txt``, if any.

    Returns:
        ``root``, for chaining.
    """
    (root / "bench").mkdir(parents=True, exist_ok=True)
    (root / "bench" / "results.json").write_text(
        json.dumps(RESULTS if results is None else results, indent=2),
        encoding="utf-8",
    )
    if allowlist is not None:
        (root / "tools").mkdir(parents=True, exist_ok=True)
        (root / "tools" / "claims_allowlist.txt").write_text(allowlist, encoding="utf-8")
    for name, contents in (files or {}).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    return root


def run(root: Path, *args: str) -> int:
    """Invoke the tool's entry point against ``root``."""
    return check_claims.main(["--repo-root", str(root), *args])


@pytest.fixture
def index() -> dict:
    """The flattened measurement index for :data:`RESULTS`."""
    return check_claims.build_index(RESULTS)


# --------------------------------------------------------------------------
# The measurement index
# --------------------------------------------------------------------------
class TestIndex:
    """Flattening runs into citable paths."""

    def test_leaf_paths_join_run_id_and_field(self, index: dict) -> None:
        assert index["extraction.med1250.acronymkit.exact_f1"] == 83.85

    def test_nested_fields_are_citable(self, index: dict) -> None:
        # A run may hold a sub-table; every leaf in it must be reachable, or the
        # breakdown tables in docs/EVALUATION.md could never be cited.
        assert index["disambiguation.sdu21.acronymkit.accuracy_by_candidate_count.10+"] == 27.11

    def test_string_fields_are_indexed_too(self, index: dict) -> None:
        assert index["extraction.med1250.acronymkit.corpus"] == "med1250"

    def test_colliding_paths_are_an_error(self) -> None:
        # Two run ids that flatten onto the same citation path would make a
        # citation ambiguous, which is the exact failure this syntax exists to
        # remove. Refuse rather than pick one.
        colliding = {
            "runs": {
                "a.b": {"c.d": 1.0},
                "a.b.c": {"d": 2.0},
            }
        }
        with pytest.raises(check_claims.CitationError, match="same citation path"):
            check_claims.build_index(colliding)


# --------------------------------------------------------------------------
# Citation resolution
# --------------------------------------------------------------------------
class TestResolution:
    """``{{claim:...}}`` against ``bench/results.json``."""

    def test_resolves_a_real_measurement(self, index: dict) -> None:
        assert check_claims.resolve("extraction.med1250.acronymkit.exact_f1", index) == 83.85

    def test_unknown_run_raises(self, index: dict) -> None:
        with pytest.raises(check_claims.CitationError, match=r"not in bench/results\.json"):
            check_claims.resolve("extraction.med9999.acronymkit.exact_f1", index)

    def test_unknown_field_suggests_a_near_miss(self, index: dict) -> None:
        with pytest.raises(check_claims.CitationError, match="Did you mean"):
            check_claims.resolve("extraction.med1250.acronymkit.exact_f2", index)

    def test_group_reference_is_not_a_measurement(self, index: dict) -> None:
        with pytest.raises(check_claims.CitationError, match="group of measurements"):
            check_claims.resolve("extraction.med1250.acronymkit", index)

    def test_format_spec_is_applied(self, index: dict) -> None:
        value = check_claims.resolve("extraction.med1250.acronymkit.docs_per_second", index)
        assert check_claims.render_value(value, ",.0f") == "4,219"

    def test_bad_format_spec_is_an_error(self) -> None:
        with pytest.raises(check_claims.CitationError, match="does not apply"):
            check_claims.render_value("med1250", ",.0f")


class TestCitationGate:
    """What a citation does to the exit code."""

    def test_resolvable_citation_passes(self, tmp_path: Path) -> None:
        make_project(
            tmp_path,
            {"README.md": "Exact F1 is {{claim:extraction.med1250.acronymkit.exact_f1}}.\n"},
        )
        assert run(tmp_path) == 0

    @pytest.mark.parametrize(
        "reference",
        [
            "extraction.med9999.acronymkit.exact_f1",  # no such run
            "extraction.med1250.acronymkit.exact_f2",  # no such field
            "extraction.med1250.acronymkit",  # a group, not a measurement
            "",  # empty
        ],
    )
    def test_unresolvable_citation_fails_the_build(self, tmp_path: Path, reference: str) -> None:
        # This is the whole point of the syntax: a citation can be wrong, and
        # being wrong is detectable. Value matching cannot do this.
        make_project(tmp_path, {"README.md": f"F1 is {{{{claim:{reference}}}}}.\n"})
        assert run(tmp_path) == 1

    def test_a_wrong_but_plausible_number_is_caught(self, tmp_path: Path) -> None:
        # 92.32 is a real measurement, so value matching backs it happily. As a
        # rendered citation of exact_f1 it is simply false, and fails.
        make_project(
            tmp_path,
            {"README.md": "F1 is 92.32<!--claim:extraction.med1250.acronymkit.exact_f1-->.\n"},
        )
        assert run(tmp_path) == 1

    def test_documented_syntax_is_inert(self, tmp_path: Path) -> None:
        # The syntax has to be documentable. A fenced example and an inline code
        # span are code, not claims, so a fake run id inside them is not a
        # broken citation.
        make_project(
            tmp_path,
            {
                "docs/GUIDE.md": (
                    "How to cite an F1 figure:\n\n"
                    "```\n"
                    "{{claim:not.a.real.run.at.all}}\n"
                    "```\n\n"
                    "or inline, `{{claim:also.not.real}}`, for recall.\n"
                )
            },
        )
        assert run(tmp_path) == 0


# --------------------------------------------------------------------------
# The value-matching fallback
# --------------------------------------------------------------------------
class TestValueFallback:
    """Backward compatibility for the claims already written."""

    def test_value_match_still_backs_a_claim(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"README.md": "Exact F1 is 83.85 on MED1250.\n"})
        assert run(tmp_path) == 0

    def test_an_unmeasured_number_still_fails(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"README.md": "Exact F1 is 89.87 on MED1250.\n"})
        assert run(tmp_path) == 1

    def test_matched_at_the_precision_written(self) -> None:
        assert check_claims._matches_measurement("4218.9", [4218.9])
        assert check_claims._matches_measurement("4219", [4218.9])
        assert not check_claims._matches_measurement("4218", [4218.9])

    def test_fractions_stored_by_a_runner_still_match_a_percentage(self) -> None:
        # never_produced_pct is stored as 0.0934 and written as 9.34 %.
        assert check_claims._matches_measurement("9.34", [0.0934])

    def test_allowlist_backs_a_number_nobody_measured(self, tmp_path: Path) -> None:
        make_project(
            tmp_path,
            {"README.md": "Published F1 for the original is ~86 %.\n"},
            allowlist="86  published figure, attributed\n",
        )
        assert run(tmp_path) == 0

    def test_marker_backs_a_line(self, tmp_path: Path) -> None:
        make_project(
            tmp_path,
            {
                "README.md": (
                    "Exact F1 was 11.11 <!-- measured: extraction.med1250.acronymkit -->\n"
                )
            },
        )
        assert run(tmp_path) == 0

    def test_marker_naming_an_unknown_run_fails(self, tmp_path: Path) -> None:
        # The marker used to be an unchecked escape hatch: any run id at all
        # silenced the line. A citation that names nothing is not a citation.
        make_project(
            tmp_path,
            {"README.md": "Exact F1 was 11.11 <!-- measured: extraction.nope.nothing -->\n"},
        )
        assert run(tmp_path) == 1


# --------------------------------------------------------------------------
# Not claims
# --------------------------------------------------------------------------
#: Lines that used to be flagged, or would be under a naive rule, and are not
#: claims about anything. The comment on each says which structural rule keeps
#: it out -- none of them is a special case for a character.
NOT_CLAIMS = [
    pytest.param("| Preset | R@25 | recall |\n", id="rank-cutoff-in-a-column-header"),
    pytest.param("## D-012 - Pseudo-precision cannot select.\n", id="decision-id"),
    pytest.param("Recall over MED1250 is unchanged.\n", id="corpus-name"),
    pytest.param(
        "> automatic precision estimates.* BMC Bioinformatics. 2008;9:402.\n",
        id="bibliographic-citation",
    ),
    pytest.param(
        "resources (`SingTermFreq.dat` is 31 MB) and `Lf1chSf` (48 KB) matter.\n",
        id="f1-inside-a-filename",
    ),
    pytest.param("Precision is discussed in `84.78` terms only.\n", id="inline-code-span"),
    pytest.param("Recall notes:\n\n```\nprecision = 84.78\n```\n", id="fenced-code-block"),
    pytest.param("On SDU@AAAI-21 the accuracy is unchanged.\n", id="workshop-name"),
]


class TestNotClaims:
    """Numbers that are parts of identifiers, or code, are not claims."""

    @pytest.mark.parametrize("line", NOT_CLAIMS)
    def test_no_claim_is_found(self, tmp_path: Path, line: str) -> None:
        make_project(tmp_path, {"docs/NOTE.md": line})
        found = list(check_claims.scan_file(tmp_path / "docs" / "NOTE.md"))
        assert found == []

    def test_python_code_is_not_prose(self, tmp_path: Path) -> None:
        # ``max(0.0, min(1.0, precision))`` was reported as an accuracy claim.
        # It is arithmetic.
        source = (
            '"""Estimated precision, or ``0.0`` when never observed."""\n'
            "\n"
            "\n"
            "def clamp(precision: float, minimum_precision: float = 0.0) -> float:\n"
            "    return max(0.0, min(1.0, precision))\n"
        )
        make_project(tmp_path, {"src/acronymkit/estimator.py": source})
        found = list(check_claims.scan_file(tmp_path / "src" / "acronymkit" / "estimator.py"))
        assert found == []

    def test_a_docstring_is_prose(self, tmp_path: Path) -> None:
        # The exclusion is "code", not "Python file". A number asserted in a
        # docstring is exactly the case that started this tool.
        source = '"""The extractor reaches 89.87 % precision on MED1250."""\n'
        make_project(tmp_path, {"src/acronymkit/engine.py": source})
        assert run(tmp_path) == 1

    def test_a_real_claim_beside_an_identifier_is_still_found(self, tmp_path: Path) -> None:
        # The positive control for every case above: excluding identifiers must
        # not exclude the number sitting next to one.
        line = "| `HIGH_PRECISION` (defaults) | 92.32 | 76.99 |\n"
        make_project(tmp_path, {"docs/NOTE.md": line})
        found = [number for _, number, _ in check_claims.scan_file(tmp_path / "docs" / "NOTE.md")]
        assert found == ["92.32", "76.99"]

    def test_a_metric_named_with_an_underscore_still_arms_the_check(self, tmp_path: Path) -> None:
        # HIGH_PRECISION and exact_f1 are how this project names its metrics.
        make_project(tmp_path, {"docs/NOTE.md": "| exact_f1 | 11.11 |\n"})
        assert run(tmp_path) == 1

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("F1 84.78 here", ["84.78"]),
            ("recall 1,221 pairs", ["1,221"]),
            ("F1 of **83.85**, up", ["83.85"]),
            ("F1 range ~86-89 % published", ["86", "89"]),
            ("recall@25 is 89.7 %", ["89.7"]),
            # Sentence punctuation sits outside the number.
            ("F1 rose to 84.78.", ["84.78"]),
            ("precision 92.32%, up from before", ["92.32"]),
            ("recall: 76.99; precision: 92.07", ["76.99", "92.07"]),
        ],
    )
    def test_free_standing_numbers_are_found(self, line: str, expected: list) -> None:
        assert [number for _, number in check_claims.iter_claim_numbers(line)] == expected

    @pytest.mark.parametrize(
        "line",
        ["R@25 column", "D-012 decision", "MED1250 corpus", "2008;9:402 citation", "v0.2.0 tag"],
    )
    def test_identifier_bound_digits_are_not_numbers(self, line: str) -> None:
        assert list(check_claims.iter_claim_numbers(line)) == []

    @pytest.mark.parametrize(
        ("line", "found"),
        [
            ("precision is", True),
            ("Pseudo-precision rates", True),
            # Underscore does not weld: these are metric names, not other words.
            ("HIGH_PRECISION defaults", True),
            ("exact_f1 column", True),
            # Welded on both sides -- a filename.
            ("Lf1chSf is a file", False),
            # Welded on the right only.
            ("F1000 Research published", False),
            # Welded on the left only: 'r@' inside an email address.
            ("mail user@example.com about it", False),
        ],
    )
    def test_keywords_are_matched_as_words(self, line: str, found: bool) -> None:
        assert bool(check_claims.keyword_positions(line)) is found


# --------------------------------------------------------------------------
# --migrate
# --------------------------------------------------------------------------
class TestMigrationReport:
    """Which run ids could supply a value-matched claim, and how many could."""

    def test_unique_value_names_one_measurement(self, index: dict) -> None:
        candidates = check_claims.candidates_for("83.85", index)
        assert [path for path, _, _ in candidates] == ["extraction.med1250.acronymkit.exact_f1"]
        assert check_claims.classify(candidates) == "UNIQUE"

    def test_same_field_in_two_runs_is_replicated_not_ambiguous(self, index: dict) -> None:
        # Two runs recording exact_precision at the same value leave the field
        # certain and the run open. That is a weaker problem than sharing a
        # value with an unrelated metric, and is labelled differently.
        candidates = check_claims.candidates_for("92.32", index)
        assert len(candidates) == 2
        assert check_claims.classify(candidates) == "REPLICATED"

    def test_unrelated_measurements_sharing_a_value_are_ambiguous(self, index: dict) -> None:
        # 76.99 is both a recall and an F1 here. A claim backed by "76.99 is in
        # results.json somewhere" has not been verified against anything.
        candidates = check_claims.candidates_for("76.99", index)
        assert {path.rsplit(".", 1)[-1] for path, _, _ in candidates} == {
            "exact_recall",
            "exact_f1",
        }
        assert check_claims.classify(candidates) == "AMBIGUOUS"

    def test_no_candidate_is_unresolved(self, index: dict) -> None:
        assert check_claims.classify(check_claims.candidates_for("11.11", index)) == "UNRESOLVED"

    def test_report_names_the_ambiguous_claims(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        make_project(
            tmp_path,
            {
                "README.md": "Exact F1 is 83.85 and recall is 76.99 on MED1250.\n",
            },
        )
        assert run(tmp_path, "--migrate") == 0
        out = capsys.readouterr().out
        assert "AMBIGUOUS" in out
        assert "{{claim:extraction.med1250.acronymkit.exact_recall}}" in out
        assert "{{claim:profile.med1250_test.high_precision.exact_f1}}" in out
        assert "ambiguous 1" in out
        assert "unique 1" in out

    def test_migrate_does_not_fail_the_build(self, tmp_path: Path) -> None:
        # It is a report about work to do, not a verdict on the current state.
        make_project(tmp_path, {"README.md": "Exact F1 is 83.85.\n"})
        assert run(tmp_path, "--migrate") == 0


class TestSummaryCounts:
    """The line that lets the migration be tracked rather than hoped for."""

    def test_each_path_is_counted_separately(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        make_project(
            tmp_path,
            {
                "README.md": (
                    "Exact F1 is {{claim:extraction.med1250.acronymkit.exact_f1}}.\n"
                    "Recall is 76.99 by value matching.\n"
                    "Published F1 is ~86 %.\n"
                )
            },
            allowlist="86  published figure, attributed\n",
        )
        assert run(tmp_path) == 0
        out = capsys.readouterr().out
        assert "cited 1" in out
        assert "value-matched 1" in out
        assert "allowlisted 1" in out
        assert "unbacked 0" in out

    def test_dead_allowlist_entries_are_reported(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        make_project(
            tmp_path,
            {"README.md": "Exact F1 is 83.85.\n"},
            allowlist="99.99  nothing needs this any more\n",
        )
        assert run(tmp_path) == 0
        assert "back nothing any more" in capsys.readouterr().out


# --------------------------------------------------------------------------
# --render
# --------------------------------------------------------------------------
MARKDOWN_SOURCE = (
    "Exact F1 is {{claim:extraction.med1250.acronymkit.exact_f1}} at "
    "{{claim:extraction.med1250.acronymkit.docs_per_second:,.0f}} docs/s.\n"
)


class TestRender:
    """Regenerating documents from measurements rather than hand-editing them."""

    def test_render_writes_the_current_value(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"README.md": MARKDOWN_SOURCE})
        assert run(tmp_path, "--render") == 0
        rendered = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert rendered.startswith("Exact F1 is 83.85<!--claim:")
        assert "4,219<!--claim:" in rendered

    def test_a_reader_sees_only_the_number(self, tmp_path: Path) -> None:
        # The reference survives rendering, because a generator that consumes
        # its own source cannot regenerate. In Markdown it survives inside an
        # HTML comment, so the published page shows "83.85" and nothing else.
        make_project(tmp_path, {"README.md": MARKDOWN_SOURCE})
        run(tmp_path, "--render")
        rendered = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "{{claim:" not in rendered
        assert "extraction.med1250.acronymkit.exact_f1" in rendered

    def test_render_is_idempotent(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"README.md": MARKDOWN_SOURCE})
        run(tmp_path, "--render")
        once = (tmp_path / "README.md").read_text(encoding="utf-8")
        run(tmp_path, "--render")
        twice = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert once == twice

    def test_render_updates_a_changed_measurement(self, tmp_path: Path) -> None:
        # The reason the reference has to survive: when the benchmark moves,
        # the document follows without anybody retyping a number.
        make_project(tmp_path, {"README.md": MARKDOWN_SOURCE})
        run(tmp_path, "--render")
        moved = json.loads(json.dumps(RESULTS))
        moved["runs"]["extraction.med1250.acronymkit"]["exact_f1"] = 84.01
        (tmp_path / "bench" / "results.json").write_text(json.dumps(moved), encoding="utf-8")
        assert run(tmp_path, "--render") == 0
        assert "84.01<!--claim:" in (tmp_path / "README.md").read_text(encoding="utf-8")

    def test_a_stale_rendered_value_fails_the_check(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"README.md": MARKDOWN_SOURCE})
        run(tmp_path, "--render")
        moved = json.loads(json.dumps(RESULTS))
        moved["runs"]["extraction.med1250.acronymkit"]["exact_f1"] = 84.01
        (tmp_path / "bench" / "results.json").write_text(json.dumps(moved), encoding="utf-8")
        assert run(tmp_path) == 1

    def test_dry_run_writes_nothing(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"README.md": MARKDOWN_SOURCE})
        before = (tmp_path / "README.md").read_text(encoding="utf-8")
        run(tmp_path, "--render", "--dry-run")
        assert (tmp_path / "README.md").read_text(encoding="utf-8") == before

    def test_dry_run_reports_what_would_change(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        make_project(tmp_path, {"README.md": MARKDOWN_SOURCE})
        assert run(tmp_path, "--render", "--dry-run") == 1
        out = capsys.readouterr().out
        assert "README.md:1" in out
        assert "+ Exact F1 is 83.85<!--claim:" in out

    def test_dry_run_is_green_once_rendered(self, tmp_path: Path) -> None:
        # This is the CI contract: "the docs are up to date" is a check, not a
        # habit. Exit 0 only when rendering would be a no-op.
        make_project(tmp_path, {"README.md": MARKDOWN_SOURCE})
        run(tmp_path, "--render")
        assert run(tmp_path, "--render", "--dry-run") == 0

    def test_render_leaves_documented_examples_alone(self, tmp_path: Path) -> None:
        source = (
            "Cite it like this:\n\n```\n{{claim:extraction.med1250.acronymkit.exact_f1}}\n```\n"
        )
        make_project(tmp_path, {"docs/GUIDE.md": source})
        assert run(tmp_path, "--render") == 0
        assert (tmp_path / "docs" / "GUIDE.md").read_text(encoding="utf-8") == source

    def test_render_leaves_an_unresolvable_citation_untouched(self, tmp_path: Path) -> None:
        # Rendering must never quietly delete a citation it cannot resolve --
        # the check is what reports it, and it can only report what is there.
        source = "F1 is {{claim:extraction.nope.exact_f1}}.\n"
        make_project(tmp_path, {"README.md": source})
        run(tmp_path, "--render")
        assert (tmp_path / "README.md").read_text(encoding="utf-8") == source
        assert run(tmp_path) == 1

    def test_python_keeps_the_brace_form(self, tmp_path: Path) -> None:
        # An HTML comment in a docstring would be nonsense, so the placeholder
        # stays visible there.
        source = '"""F1 is {{claim:extraction.med1250.acronymkit.exact_f1}} on MED1250."""\n'
        make_project(tmp_path, {"src/acronymkit/engine.py": source})
        assert run(tmp_path, "--render") == 0
        rendered = (tmp_path / "src" / "acronymkit" / "engine.py").read_text(encoding="utf-8")
        assert "{{claim:extraction.med1250.acronymkit.exact_f1=83.85}}" in rendered

    def test_a_rendered_value_is_not_also_counted_as_a_value_match(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        make_project(tmp_path, {"README.md": MARKDOWN_SOURCE})
        run(tmp_path, "--render")
        capsys.readouterr()
        assert run(tmp_path) == 0
        out = capsys.readouterr().out
        assert "cited 2" in out
        assert "value-matched 0" in out


# --------------------------------------------------------------------------
# Arming: which rule picks a number up, and what happens to the ones no rule does
# --------------------------------------------------------------------------
class TestArming:
    """The two arming rules, and the failure the second one exists for."""

    def test_a_keyword_arms_a_nearby_number(self) -> None:
        line = "exact precision was 92.32 on this split"
        offset = line.index("92.32")
        keywords = check_claims.keyword_positions(line)
        assert check_claims.arming_of(line, offset, "92.32", keywords) == "keyword"

    @pytest.mark.parametrize(
        ("line", "number"),
        [
            # The live case. F-subscript-one is U+2081, so this line carries no
            # keyword at all -- widening _PROXIMITY to any value never arms it.
            ("Rule-based extractors reach F₁ > 96 % on inline definitions", "96"),
            ("`expand_identifier` fell to 10.70 µs on the schema arm", "10.70"),
            ("the harness sustained 4,219 rows/s", "4,219"),
            ("the corpus ran at 96,532 identifiers/second", "96,532"),
            ("attributed at 92.32% by the original authors", "92.32"),
        ],
    )
    def test_a_unit_arms_a_number_with_no_keyword_anywhere(self, line: str, number: str) -> None:
        assert check_claims.keyword_positions(line) == [], "fixture must carry no keyword"
        offset = line.index(number)
        assert check_claims.arming_of(line, offset, number, []) == "unit"

    @pytest.mark.parametrize(
        ("line", "number"),
        [
            # A unit is a unit only when it is the next thing on the line.
            ("published in 2003 by Schwartz & Hearst", "2003"),
            ("the top 25 candidates are considered", "25"),
            ("SCOWL size cut 60, giving 76,879 entries", "76,879"),
            # `s` inside a longer word is not seconds, and a path is not a rate.
            ("we ship 12 useful presets", "12"),
            ("all 44 tools/scripts are runnable", "44"),
            ("that is 30 milliseconds of headroom", "30"),
        ],
    )
    def test_ordinary_prose_numbers_arm_nothing(self, line: str, number: str) -> None:
        offset = line.index(number)
        keywords = check_claims.keyword_positions(line)
        assert check_claims.arming_of(line, offset, number, keywords) == ""

    def test_proximity_wins_a_tie_with_the_unit_rule(self) -> None:
        # Load-bearing: it is what keeps VALUE_MATCHED_BASELINE at exactly the
        # count it was pinned at. If the unit rule could steal a number the
        # keyword rule already had, turning it on would have moved the old
        # ledger, which R1 ratchets shut.
        line = "precision 92.32%"
        offset = line.index("92.32")
        keywords = check_claims.keyword_positions(line)
        assert check_claims.arming_of(line, offset, "92.32", keywords) == "keyword"

    def test_an_unarmed_number_is_recorded_rather_than_dropped(self, tmp_path: Path) -> None:
        # The defect this whole section exists for. The scanner used to discard
        # these where it found them, so a figure out of a keyword's reach was
        # counted in no total and named in no report.
        make_project(tmp_path, {"docs/NOTE.md": "The corpus was published in 2003.\n"})
        found = list(check_claims.iter_prose_numbers(tmp_path / "docs" / "NOTE.md"))
        assert [(number, arming) for _, number, _, arming in found] == [("2003", "")]

    def test_scan_file_still_yields_only_armed_numbers(self, tmp_path: Path) -> None:
        # The old entry point keeps its old meaning: "claims the gate checks".
        make_project(
            tmp_path,
            {"docs/NOTE.md": "Exact recall was 76.99 on the split.\n\nPublished in 2003.\n"},
        )
        found = [number for _, number, _ in check_claims.scan_file(tmp_path / "docs" / "NOTE.md")]
        assert found == ["76.99"]


class TestUnexamined:
    """The residue: counted, reported, and never value-matched."""

    def test_an_unarmed_number_never_fails_the_build(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"docs/NOTE.md": "ACRONYM (Cook, 2019) spells real words.\n"})
        assert run(tmp_path) == 0

    def test_the_residue_is_counted_in_the_summary(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        make_project(tmp_path, {"docs/NOTE.md": "ACRONYM (Cook, 2019) spells real words.\n"})
        assert run(tmp_path) == 0
        out = capsys.readouterr().out
        assert "unexamined 1" in out
        assert "not checked: 1 prose number(s)" in out

    def test_an_unexamined_number_is_not_value_matched(self, tmp_path: Path) -> None:
        # 83.85 is a real measurement, so the fallback would happily "back" it.
        # Out of a keyword's reach and carrying no unit it is not a claim at
        # all, and calling it backed is how the residue would have been
        # laundered: 1,144 of this repository's would have matched something,
        # 792 of them AMBIGUOUSLY.
        make_project(tmp_path, {"docs/NOTE.md": "Serial number 83.85 on the chassis.\n"})
        project = check_claims.Project.at(tmp_path)
        index = check_claims.build_index(RESULTS)
        claims = check_claims.collect_claims(project, index, {})
        assert [(claim.text, claim.backing) for claim in claims] == [("83.85", "unexamined")]

    def test_the_residue_report_names_the_file_and_line(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        make_project(
            tmp_path,
            {"docs/NOTE.md": "Serial 83.85 here.\nThe rerun sat at 11.11 % of it.\n"},
        )
        assert run(tmp_path, "--residue") == 0
        out = capsys.readouterr().out
        assert "docs/NOTE.md  (1 deferred, 1 unexamined)" in out
        assert ":2  11.11  NO MEASUREMENT MATCHES" in out

    def test_residue_does_not_fail_the_build(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"docs/NOTE.md": "Serial 83.85 here.\n"})
        assert run(tmp_path, "--residue") == 0


class TestDeferredLedger:
    """The second ratchet, and the one property it must never have."""

    def test_a_unit_armed_uncited_number_is_deferred_not_value_matched(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        # 83.85 equals exact_f1. On the value path it would read as backed and
        # spend a slot in the ledger R1 pins shut; it is a number nobody has
        # adjudicated, so it goes on the register that only shrinks.
        make_project(tmp_path, {"docs/NOTE.md": "The run sat at 83.85 % throughout.\n"})
        assert run(tmp_path) == 0
        out = capsys.readouterr().out
        assert "value-matched 0" in out
        assert "deferred 1" in out

    def test_the_deferred_report_separates_matched_from_unmatched(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        make_project(
            tmp_path,
            {"docs/NOTE.md": "First 83.85 % and then 11.11 % on the rerun.\n"},
        )
        run(tmp_path, "--residue")
        out = capsys.readouterr().out
        assert "of those, 1 match no measurement at all" in out

    def test_a_cited_number_never_reaches_the_deferred_ledger(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        make_project(
            tmp_path,
            {"docs/NOTE.md": "Sat at {{claim:extraction.med1250.acronymkit.exact_f1}} %.\n"},
        )
        assert run(tmp_path) == 0
        out = capsys.readouterr().out
        assert "cited 1" in out
        assert "deferred 0" in out

    def test_update_baseline_prints_both_registers(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        make_project(
            tmp_path,
            {"docs/NOTE.md": "Exact recall was 76.99.\n\nThe rerun sat at 83.85 % after.\n"},
        )
        assert run(tmp_path, "--update-baseline") == 0
        out = capsys.readouterr().out
        assert "VALUE_MATCHED_BASELINE" in out
        assert "DEFERRED_BASELINE" in out
        assert '"docs/NOTE.md": 1,' in out


def _ratcheted(root: Path, *, value: dict, deferred: dict) -> object:
    """A project with both ratchets armed, which ``Project.at`` only does here.

    The baselines are facts about the real checkout, so ``at()`` leaves them off
    for any other root. That is right, and it left the mechanism R1 rests on
    with no test of its own -- reachable only by running the tool against the
    repository, where it is green by construction and therefore proves nothing.
    """
    return check_claims.Project(
        root=root.resolve(),
        results_path=root / "bench" / "results.json",
        allowlist_path=root / "tools" / "claims_allowlist.txt",
        value_baseline=value,
        deferred_baseline=deferred,
    )


class TestRatchets:
    """Both registers, both directions. Neither had a test before."""

    def _claims(self, root: Path, project: object) -> list:
        index = check_claims.build_index(RESULTS)
        return check_claims.collect_claims(project, index, {})

    def test_an_uncited_number_over_budget_is_reported(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"docs/NOTE.md": "Exact recall was 76.99 on the split.\n"})
        project = _ratcheted(tmp_path, value={}, deferred={})
        problems = check_claims.baseline_problems(project, self._claims(tmp_path, project))
        assert len(problems) == 1
        assert "1 value-matched claim(s), baseline 0" in problems[0]

    def test_a_migration_that_leaves_the_baseline_alone_is_reported(self, tmp_path: Path) -> None:
        # The slack a ratchet must not have: migrate one claim, leave the
        # number, and the freed slot is open for the next uncited figure.
        make_project(tmp_path, {"docs/NOTE.md": "Exact recall was 76.99 on the split.\n"})
        project = _ratcheted(tmp_path, value={"docs/NOTE.md": 2}, deferred={})
        problems = check_claims.baseline_problems(project, self._claims(tmp_path, project))
        assert len(problems) == 1
        assert "lower the baseline" in problems[0]

    def test_an_exact_match_is_silent(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"docs/NOTE.md": "Exact recall was 76.99 on the split.\n"})
        project = _ratcheted(tmp_path, value={"docs/NOTE.md": 1}, deferred={})
        assert check_claims.baseline_problems(project, self._claims(tmp_path, project)) == []

    def test_the_deferred_register_may_not_grow(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"docs/NOTE.md": "The rerun sat at 83.85 % after.\n"})
        project = _ratcheted(tmp_path, value={}, deferred={})
        problems = check_claims.baseline_problems(project, self._claims(tmp_path, project))
        assert len(problems) == 1
        assert "deferred ledger is a debt register" in problems[0]

    def test_the_deferred_register_must_shrink_in_the_same_commit(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"docs/NOTE.md": "The rerun sat at 83.85 % after.\n"})
        project = _ratcheted(tmp_path, value={}, deferred={"docs/NOTE.md": 4})
        problems = check_claims.baseline_problems(project, self._claims(tmp_path, project))
        assert len(problems) == 1
        assert "lower DEFERRED_BASELINE" in problems[0]

    def test_the_two_registers_are_counted_separately(self, tmp_path: Path) -> None:
        # A file may sit at budget on one and over on the other, and the
        # message must name which. Folding them would let a unit-armed figure
        # spend a slot in the ledger R1 pins shut.
        make_project(
            tmp_path,
            {"docs/NOTE.md": "Exact recall was 76.99.\n\nThe rerun sat at 83.85 % after.\n"},
        )
        project = _ratcheted(tmp_path, value={"docs/NOTE.md": 1}, deferred={})
        problems = check_claims.baseline_problems(project, self._claims(tmp_path, project))
        assert len(problems) == 1
        assert "deferred" in problems[0]

    def test_a_file_with_no_entry_admits_nothing(self, tmp_path: Path) -> None:
        # What makes a document added to SCAN_GLOBS tomorrow cite from its
        # first line, on both registers.
        make_project(tmp_path, {"docs/NEW.md": "The rerun sat at 83.85 % after.\n"})
        project = _ratcheted(tmp_path, value={}, deferred={"docs/OTHER.md": 3})
        problems = check_claims.baseline_problems(project, self._claims(tmp_path, project))
        assert len(problems) == 2
        assert any("docs/NEW.md" in problem for problem in problems)
        assert any("docs/OTHER.md" in problem for problem in problems)


class TestCoverageMayNotWeakenAVerdict:
    """The rule that keeps a widened gate from softening an existing failure."""

    def test_a_keyword_armed_unmeasured_number_still_fails_hard(self, tmp_path: Path) -> None:
        # The live case that forced this: `34,096` landed in docs/OFFLINE.md
        # while this change was being written. It is keyword-armed, it matches
        # no measurement, and the unmodified gate fails on it. An earlier draft
        # routed every number in a file outside VALUE_MATCHED_BASELINE onto the
        # deferred ledger, which would have turned that red into a ledger row.
        make_project(tmp_path, {"docs/OFFLINE.md": "| `pseudo_precision_en.json` | 34,096 |\n"})
        assert run(tmp_path) == 1

    def test_only_the_named_newly_scanned_files_are_grandfathered(self) -> None:
        # The grandfather set is a closed list of documents the gate could not
        # previously see, not a category. It only shrinks.
        assert frozenset({"CHANGELOG.md", "bench/splits.toml"}) == (
            check_claims._COVERAGE_GRANDFATHER
        )


class TestScanCoverage:
    """Which files the gate reads, and saying so when one is not there."""

    @pytest.mark.parametrize("name", ["CHANGELOG.md", "bench/splits.toml"])
    def test_the_previously_unscanned_documents_are_scanned(self, name: str) -> None:
        assert name in check_claims.SCAN_GLOBS

    def test_a_changelog_number_is_seen(self, tmp_path: Path) -> None:
        make_project(tmp_path, {"CHANGELOG.md": "Extraction F1 was 89.87 in this release.\n"})
        assert run(tmp_path) == 1

    def test_a_manifest_figure_is_seen(self, tmp_path: Path) -> None:
        # bench/splits.toml publishes recall ceilings as bare assignments. TOML
        # has no fenced blocks, so the figure is prose and the gate reads it.
        make_project(tmp_path, {"bench/splits.toml": "shortform_recall_ceiling_pct = 89.87\n"})
        found = [
            number for _, number, _ in check_claims.scan_file(tmp_path / "bench" / "splits.toml")
        ]
        assert found == ["89.87"]

    def test_an_absent_literal_target_is_named(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        # bench/splits.toml is outside MANIFEST.in, so inside an sdist the scan
        # set is one file smaller. That is tolerable and it may not be silent.
        make_project(tmp_path, {"docs/NOTE.md": "nothing here\n"})
        run(tmp_path)
        out = capsys.readouterr().out
        assert "scan target(s) absent" in out
        assert "bench/splits.toml" in out

    def test_a_wildcard_matching_nothing_is_not_an_absent_target(self, tmp_path: Path) -> None:
        # An empty docs/ directory is not a file the gate was told to read.
        make_project(tmp_path, {"README.md": "x\n", "CHANGELOG.md": "x\n"})
        (tmp_path / "bench" / "splits.toml").write_text("x = 1\n", encoding="utf-8")
        assert check_claims.absent_targets(check_claims.Project.at(tmp_path)) == []

    def test_toml_keeps_the_brace_form_when_rendered(self, tmp_path: Path) -> None:
        # An HTML comment in a TOML file is not TOML. The comment form is
        # Markdown's, not "anything that is not Python".
        source = "ceiling = 0.0  # {{claim:extraction.med1250.acronymkit.exact_f1}}\n"
        make_project(tmp_path, {"bench/splits.toml": source})
        assert run(tmp_path, "--render") == 0
        rendered = (tmp_path / "bench" / "splits.toml").read_text(encoding="utf-8")
        assert "<!--claim:" not in rendered
        assert "{{claim:extraction.med1250.acronymkit.exact_f1=83.85}}" in rendered


# --------------------------------------------------------------------------
# The real checkout
# --------------------------------------------------------------------------
class TestThisRepository:
    """The gate, run against the repository it guards."""

    def test_the_checkout_is_green(self) -> None:
        # Duplicates the CI step deliberately: a claims failure should surface
        # in the suite that a contributor runs, not only in the workflow.
        assert check_claims.main([]) == 0

    def test_rendering_would_change_nothing(self) -> None:
        assert check_claims.main(["--render", "--dry-run"]) == 0

    def test_every_scanned_file_exists_and_is_readable(self) -> None:
        paths = check_claims.scan_paths(check_claims.Project.at(REPO_ROOT))
        assert paths, "the scan globs match nothing, so the gate guards nothing"
        assert all(path.is_file() for path in paths)

    def test_the_sdist_ships_the_evidence_for_the_docs_it_ships(self) -> None:
        # The sdist ships `docs/` and `src/`, which make accuracy claims, and
        # `tools/check_claims.py`, which is the gate that backs them. It once
        # shipped all three without `bench/results.json`, so the gate could not
        # pass inside the artifact and CI caught it only after a push. Checking
        # the manifest here makes the invariant fail in the local suite instead.
        manifest = REPO_ROOT / "MANIFEST.in"
        if not manifest.is_file():
            pytest.skip("no MANIFEST.in; not a source checkout")

        includes: list[tuple[str, tuple[str, ...]]] = []
        for line in manifest.read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if fields[:1] == ["include"]:
                includes.append(("", tuple(fields[1:])))
            elif fields[:1] == ["recursive-include"] and len(fields) > 2:
                includes.append((fields[1], tuple(fields[2:])))

        def shipped(path: Path) -> bool:
            relative = path.relative_to(REPO_ROOT).as_posix()
            return any(
                any(
                    fnmatch(relative, f"{prefix}/{pattern}" if prefix else pattern)
                    for pattern in patterns
                )
                or (
                    bool(prefix)
                    and relative.startswith(f"{prefix}/")
                    and any(fnmatch(path.name, pattern) for pattern in patterns)
                )
                for prefix, patterns in includes
            )

        for needed in (check_claims.RESULTS_PATH, check_claims.ALLOWLIST_PATH):
            assert shipped(needed), (
                f"{needed.relative_to(REPO_ROOT).as_posix()} is not in MANIFEST.in, so the "
                "sdist ships claims the shipped checker cannot back"
            )


# --------------------------------------------------------------------------
# The burn-down: classification and the trajectory
# --------------------------------------------------------------------------
def _claim(
    tmp_path: Path,
    line: str,
    *,
    number: str,
    arming: str = "",
    backing: str = "unexamined",
    name: str = "docs/NOTE.md",
) -> object:
    """One classified-shaped claim, built without going through a scan."""
    return check_claims.Claim(
        path=tmp_path / name,
        line_number=1,
        text=number,
        line=line,
        backing=backing,
        arming=arming,
    )


def _judging(monkeypatch: pytest.MonkeyPatch, anchor: str) -> None:
    """Install one synthetic judgement over ``docs/NOTE.md``'s ``83.85``.

    ``monkeypatch`` rather than assign-and-restore because the module under
    test is loaded by path and is therefore a bare ``ModuleType``: mypy allows
    reading an attribute off one and refuses to let a test write to it, so the
    assign-and-restore form typed clean only while ``tests/`` sat outside the
    checker's ``files``. That is the shape D-058 is about.
    """
    monkeypatch.setattr(
        check_claims,
        "DEBT_JUDGEMENTS",
        (
            check_claims.Judgement(
                path="docs/NOTE.md",
                number="83.85",
                anchor=anchor,
                bucket="stale",
                reason="the split it was measured on is gone",
            ),
        ),
    )


class TestDetectors:
    """The structural rules that say a number is not a claim.

    Each of these is a *derived* verdict on the residue, so each one can be
    wrong about a real figure. The tests that matter here are the ones pinning
    where a detector must decline.
    """

    def test_a_date_part_is_not_a_claim(self, tmp_path: Path) -> None:
        claim = _claim(tmp_path, "Verified 2026-08-23 against the pinned commit.", number="08")
        assert check_claims.detector_for(claim) == "iso-date-fragment"

    def test_a_date_detector_declines_when_the_number_is_also_a_count(self, tmp_path: Path) -> None:
        # `23` is a day here and a count on the same line. Answering "any
        # occurrence is a date part" would relabel the count, so the rule is
        # "every occurrence", and when they disagree the detector declines.
        claim = _claim(tmp_path, "Verified 2026-08-23 across 23 portals.", number="23")
        assert check_claims.detector_for(claim) == ""

    def test_a_year_is_not_a_claim(self, tmp_path: Path) -> None:
        claim = _claim(tmp_path, "The August 2026 audit reported it.", number="2026")
        assert check_claims.detector_for(claim) == "year-shaped"

    def test_an_interpreter_version_is_not_a_claim(self, tmp_path: Path) -> None:
        claim = _claim(tmp_path, "The floor is Python 3.9 and the ceiling 3.13.", number="3.9")
        assert check_claims.detector_for(claim) == "version-number"

    def test_a_dotted_number_with_no_version_context_is_not_a_version(self, tmp_path: Path) -> None:
        claim = _claim(tmp_path, "The gap is 3.9 points on this split.", number="3.9")
        assert check_claims.detector_for(claim) == ""

    def test_a_list_marker_is_not_a_claim(self, tmp_path: Path) -> None:
        claim = _claim(tmp_path, "2. The presets differ enormously at rank 1.", number="2")
        assert check_claims.detector_for(claim) == "section-or-list-ordinal"

    def test_a_sentence_that_opens_with_a_count_is_not_a_list_item(self, tmp_path: Path) -> None:
        # A real defect, found by sampling the detector's own output rather
        # than by reasoning about it. The first draft made the `.` after a list
        # number optional, so `26 to 39 symbols that never appear ...` was read
        # as list item 26 and a real count was labelled not-a-claim. Twenty
        # numbers were wrong that way.
        claim = _claim(tmp_path, "26 to 39 symbols never appear in a candidate.", number="26")
        assert check_claims.detector_for(claim) == ""

    def test_a_byte_size_is_not_a_claim(self, tmp_path: Path) -> None:
        claim = _claim(tmp_path, "The bundle is 205,920 B on disk.", number="205,920")
        assert check_claims.detector_for(claim) == "byte-size"

    def test_no_detector_may_reach_a_unit_armed_number(self, tmp_path: Path) -> None:
        # The load-bearing guard. `2026 %` is nonsense, but the principle is
        # not: a number carrying a metric unit is a metric by its own shape,
        # and a year-shaped rule that could reach one would be the classifier
        # arguing a measured figure off the ledger.
        claim = _claim(tmp_path, "It moved 2026 % in a year.", number="2026", arming="unit")
        assert check_claims.detector_for(claim) == ""


class TestClassifyDebt:
    """Which bucket an unverified number lands in, and on what basis."""

    def test_an_armed_number_with_a_measurement_is_gate_able(
        self, tmp_path: Path, index: dict
    ) -> None:
        project = check_claims.Project.at(tmp_path)
        claim = _claim(
            tmp_path, "F1 was 83.85 here.", number="83.85", arming="keyword", backing="deferred"
        )
        bucket, basis = check_claims.classify_debt(claim, index, project)
        assert bucket == "gate-able"
        assert basis.startswith("derived:")

    def test_an_armed_number_with_no_measurement_is_blocked(
        self, tmp_path: Path, index: dict
    ) -> None:
        project = check_claims.Project.at(tmp_path)
        claim = _claim(
            tmp_path, "F1 was 11.11 here.", number="11.11", arming="keyword", backing="deferred"
        )
        assert check_claims.classify_debt(claim, index, project)[0] == "blocked"

    def test_an_unarmed_number_is_never_gate_able(self, tmp_path: Path, index: dict) -> None:
        # The rule that keeps D-052's refusal intact. `83.85` equals a
        # measurement, but no arming rule reaches it, so "cite it" is not the
        # fix and the classifier does not pretend it is.
        project = check_claims.Project.at(tmp_path)
        claim = _claim(tmp_path, "Serial 83.85 was stamped on the case.", number="83.85")
        assert check_claims.classify_debt(claim, index, project)[0] == "unclassified"

    def test_a_metric_table_column_reaches_a_number_no_arming_rule_does(
        self, tmp_path: Path, index: dict
    ) -> None:
        # The blind spot both arming rules share: a table names its metric once
        # in the header and then writes bare numbers under it.
        make_project(
            tmp_path,
            {"docs/NOTE.md": "| System | F1 % |\n|---|---:|\n| ours | 83.85 |\n"},
        )
        project = check_claims.Project.at(tmp_path)
        claims = check_claims.collect_claims(project, index, {})
        rows = check_claims.classified_rows(project, index, claims)
        buckets = {claim.text: bucket for claim, bucket, _ in rows}
        assert buckets["83.85"] == "gate-able"
        basis = {claim.text: basis for claim, _, basis in rows}["83.85"]
        assert "metric column" in basis

    def test_a_judgement_beats_every_derived_rule(
        self, tmp_path: Path, index: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = check_claims.Project.at(tmp_path)
        claim = _claim(
            tmp_path, "F1 was 83.85 here.", number="83.85", arming="keyword", backing="deferred"
        )
        _judging(monkeypatch, "F1 was")
        bucket, basis = check_claims.classify_debt(claim, index, project)
        assert bucket == "stale"
        assert basis.startswith("judged:")

    def test_a_judgement_whose_sentence_moved_still_matches(
        self, tmp_path: Path, index: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Why the anchor is a substring and not a line number. An entry keyed
        # on a line went stale inside one session because a workstream inserted
        # seven lines above it in a file nobody had touched.
        project = check_claims.Project.at(tmp_path)
        _judging(monkeypatch, "F1 was")
        moved = check_claims.Claim(
            path=tmp_path / "docs/NOTE.md",
            line_number=9999,
            text="83.85",
            line="F1 was 83.85 here.",
            backing="deferred",
            arming="keyword",
        )
        assert check_claims.classify_debt(moved, index, project)[0] == "stale"

    def test_a_judgement_whose_sentence_is_gone_is_reported_stale(
        self, tmp_path: Path, index: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        make_project(tmp_path, {"docs/NOTE.md": "Exact recall was 76.99 on the split.\n"})
        project = check_claims.Project.at(tmp_path)
        claims = check_claims.collect_claims(project, index, {})
        _judging(monkeypatch, "a sentence nobody ever wrote")
        assert len(check_claims.stale_judgements(project, claims)) == 1

    def test_a_whole_file_judgement_reaches_only_the_ledger(
        self, tmp_path: Path, index: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A file-wide verdict is a statement about the figures the gate can
        # see. Letting it swallow the unexamined residue too would make one
        # line speak for every digit in the document.
        project = check_claims.Project.at(tmp_path)
        deferred = _claim(
            tmp_path, "F1 was 83.85 here.", number="83.85", arming="unit", backing="deferred"
        )
        unexamined = _claim(tmp_path, "Serial 83.85 on the case.", number="83.85")
        monkeypatch.setitem(
            check_claims.DEBT_FILE_JUDGEMENTS, "docs/NOTE.md", ("blocked", "no runner saves it")
        )
        assert check_claims.classify_debt(deferred, index, project)[0] == "blocked"
        assert check_claims.classify_debt(unexamined, index, project)[0] == "unclassified"

    def test_every_bucket_carries_a_meaning(self) -> None:
        assert set(check_claims.DEBT_BUCKETS) == set(check_claims.BUCKET_MEANINGS)

    def test_every_recorded_judgement_names_a_real_bucket(self) -> None:
        for judgement in check_claims.DEBT_JUDGEMENTS:
            assert judgement.bucket in check_claims.DEBT_BUCKETS, judgement.key
            assert judgement.reason, judgement.key
            assert judgement.anchor, judgement.key
        for key, (bucket, reason) in check_claims.DEBT_FILE_JUDGEMENTS.items():
            assert bucket in check_claims.DEBT_BUCKETS, key
            assert reason, key

    def test_no_recorded_judgement_has_gone_stale(self) -> None:
        # A judgement is keyed by line number and lines move. This is the check
        # that says so out loud rather than letting the entry rot silently.
        project = check_claims.Project.at(check_claims.REPO_ROOT)
        results = check_claims.load_results(project)
        real_index = check_claims.build_index(results)
        claims = check_claims.collect_claims(
            project, real_index, check_claims.load_allowlist(project)
        )
        assert check_claims.stale_judgements(project, claims) == []

    def test_classify_reports_and_changes_nothing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        make_project(tmp_path, {"docs/NOTE.md": "Exact recall was 76.99 on the split.\n"})
        assert run(tmp_path, "--classify") == 0
        out = capsys.readouterr().out
        assert "gate-able" in out
        assert "unclassified" in out
        assert "Nothing in this report moves any ratchet." in out


class TestLedgerTrajectory:
    """The quota, and the four things the gate checks about a recorded round."""

    def _round(self, label: str, deferred: int, **kwargs: object) -> object:
        return check_claims.LedgerRound(label=label, deferred=deferred, value_matched=0, **kwargs)

    def test_a_sound_trajectory_is_silent(self) -> None:
        trajectory = (
            self._round("first", 100),
            self._round("second", 80, by_citation=20),
        )
        assert (
            check_claims.trajectory_problems(trajectory, deferred_total=80, value_total=0, quota=12)
            == []
        )

    def test_lowering_a_baseline_without_a_round_is_reported(self) -> None:
        # The coupling the whole policy rests on: a ratchet that moves with no
        # recorded round is a burn-down nobody can audit.
        trajectory = (self._round("first", 100),)
        problems = check_claims.trajectory_problems(
            trajectory, deferred_total=88, value_total=0, quota=12
        )
        assert len(problems) == 1
        assert "Append a LedgerRound" in problems[0]

    def test_a_round_that_does_not_add_up_is_reported(self) -> None:
        trajectory = (
            self._round("first", 100),
            self._round("second", 80, by_citation=5),
        )
        problems = check_claims.trajectory_problems(
            trajectory, deferred_total=80, value_total=0, quota=12
        )
        assert len(problems) == 1
        assert "accounts for 5" in problems[0]

    def test_fencing_counts_toward_the_arithmetic_and_is_reported_apart(self) -> None:
        # Fencing is a migration of the measurement, not of the debt. It has to
        # balance the books like anything else, and it has to be visible.
        trajectory = (
            self._round("first", 100),
            self._round("second", 80, by_citation=6, by_fencing=14),
        )
        assert (
            check_claims.trajectory_problems(trajectory, deferred_total=80, value_total=0, quota=12)
            == []
        )
        line = check_claims.trajectory_line(trajectory)
        assert "fencing 14" in line

    def test_missing_the_quota_without_a_waiver_is_reported(self) -> None:
        trajectory = (
            self._round("first", 100),
            self._round("second", 97, by_citation=3),
        )
        problems = check_claims.trajectory_problems(
            trajectory, deferred_total=97, value_total=0, quota=12
        )
        assert len(problems) == 1
        assert "records no waiver" in problems[0]

    def test_a_waiver_admits_a_short_round(self) -> None:
        trajectory = (
            self._round("first", 100),
            self._round("second", 97, by_citation=3, waiver="the reachable population is empty"),
        )
        assert (
            check_claims.trajectory_problems(trajectory, deferred_total=97, value_total=0, quota=12)
            == []
        )

    def test_the_deferred_column_may_not_rise(self) -> None:
        trajectory = (
            self._round("first", 80),
            self._round("second", 100),
        )
        problems = check_claims.trajectory_problems(
            trajectory, deferred_total=100, value_total=0, quota=12
        )
        assert any("may not grow" in problem for problem in problems)

    def test_by_other_needs_a_note(self) -> None:
        trajectory = (
            self._round("first", 100),
            self._round("second", 80, by_other=20),
        )
        problems = check_claims.trajectory_problems(
            trajectory, deferred_total=80, value_total=0, quota=12
        )
        assert any("no note" in problem for problem in problems)

    def test_an_empty_trajectory_is_refused(self) -> None:
        problems = check_claims.trajectory_problems((), deferred_total=0, value_total=0)
        assert len(problems) == 1

    def test_the_recorded_trajectory_matches_the_live_baselines(self) -> None:
        # The one test here that reads the real checkout: it is what makes a
        # future migration that forgets to append a round fail in CI rather
        # than only under someone's eye.
        assert (
            check_claims.trajectory_problems(
                check_claims.LEDGER_TRAJECTORY,
                deferred_total=sum(check_claims.DEFERRED_BASELINE.values()),
                value_total=sum(check_claims.VALUE_MATCHED_BASELINE.values()),
            )
            == []
        )

    def test_round_labels_are_unique(self) -> None:
        labels = [entry.label for entry in check_claims.LEDGER_TRAJECTORY]
        assert len(labels) == len(set(labels))
