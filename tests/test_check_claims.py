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

Every fixture is a synthetic project under ``tmp_path``, so nothing here
depends on today's contents of ``bench/results.json`` -- except the one test
that deliberately does, which asserts the real checkout is green.
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
