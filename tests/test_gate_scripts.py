"""The gates that used to be heredocs, and the two the packaging harness used to copy.

Why this file exists
--------------------
Five CI gates whose implementation lived inside a YAML string are now scripts in
``tools/``. That was worth doing for one reason and it is the reason this file
exists: **a gate inside a heredoc cannot be invoked, so it cannot be mutated,
tested, or shown able to fail.** ``.github/gates.toml`` recorded eight such
gates as ``kind = "inline"`` with that exact disposition, and D-018 already
settled the alternative -- a harness that runs a *copy* of a gate is testing its
copy.

What is pinned here, and why each item is here
----------------------------------------------
* **Each script fails on the defect it exists to catch, and passes otherwise.**
  Both halves: a script that always failed would also "catch" everything.

* **The failure marker in the script equals the one in the register.** Every
  extracted gate declares ``expect_failure_matching`` -- the substring its
  output must contain before the mutation harness will call a non-zero exit a
  demonstration. If the script's wording drifts from the register's copy, every
  future demonstration of that gate silently becomes ``INERT`` and the register
  reports a gate nobody can demonstrate. That is a two-copy problem in the
  machinery built to find two-copy problems, so it is checked rather than
  trusted.

* **``ci.yml`` invokes the script the register names.** The extraction is only
  worth anything if the thing CI runs and the thing the harness mutates are the
  same file. A rename that updates one and not the other is exactly the drift
  the packaging harness spent a phase paying for.

* **The packaging harness's reproduction is checked against ``ci.yml``.**
  ``sequence_drift`` replaced a guard that printed ``WARNING:`` and carried on,
  after a run in which every one of six sdist builds failed and the job was
  green. Tested in both directions: the live workflow must pass it, and a
  workflow missing one fragment must not.

Nothing here reaches the network. ``tools/gate_import_ceiling.py`` is exercised
through a stubbed probe rather than by timing real imports: the wall-clock half
of that gate is a property of the runner, this suite runs on fifteen matrix
cells, and a test that can fail because a shared runner was busy is a test that
gets deleted.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import List

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS = REPO_ROOT / "tools"
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
GATES = REPO_ROOT / ".github" / "gates.toml"

# THE GUARD, PLACED BEFORE THE LOAD AND NOT ON A MARK.
#
# `pytest.mark.skipif` is consulted at COLLECTION and a module body runs at
# IMPORT, which is earlier -- the lesson of the fourth and fifth historical
# packaging breakages, both of which shipped past a `skipif` that could not
# help. `tools/` ships in the sdist and is no part of an installed
# distribution, so under the `installed-suite` job the loads below would raise
# and this file would fail to COLLECT rather than skip.
#
# One named condition, deliberately: a module-wide blanket is what hid 74 tests
# in `tests/test_splits_manifest.py`, and any OTHER error here must still reach
# the job.
if not (TOOLS / "gate_schema_copies.py").is_file():  # pragma: no cover - CI job only
    pytest.skip(
        "tools/ is not part of an installed distribution; these tests belong to a checkout",
        allow_module_level=True,
    )


def _load(name: str) -> ModuleType:
    """Import a ``tools/`` script by path.

    ``tools/`` is a directory of scripts and must not become a package: making
    it importable for a test's convenience would change the shape of the thing
    under test. Same mechanism as ``tests/test_gate_manifest.py``.
    """
    spec = importlib.util.spec_from_file_location(f"_{name}_under_test", TOOLS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


schema_copies = _load("gate_schema_copies")
sdist_files = _load("gate_sdist_files")
installed_suite = _load("gate_installed_suite")
import_ceiling = _load("gate_import_ceiling")

#: 3.9 and 3.10 have no ``tomllib`` and ``tomli`` is not a declared dev
#: dependency, so the register cannot be parsed there. Only the tests that read
#: it are skipped.
_NO_PARSER = sys.version_info < (3, 11) and importlib.util.find_spec("tomli") is None
#: `MANIFEST.in` ships BOTH `.github/gates.toml` and `.github/workflows/*.yml`,
#: so neither mark fires inside an extracted sdist -- these tests really do run
#: there. What they guard is an INSTALLED distribution, which has neither file
#: and no `tools/` either (the module-level skip above catches that first).
needs_register = pytest.mark.skipif(
    _NO_PARSER or not GATES.is_file(),
    reason="the register needs a TOML parser, and is absent from an installed distribution",
)
needs_workflow = pytest.mark.skipif(
    not CI.is_file(), reason=".github/workflows/ci.yml is absent (an installed distribution)"
)


def _register() -> dict:
    import tomllib

    with GATES.open("rb") as handle:
        return tomllib.load(handle)


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOLS / script), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        errors="replace",
    )


# ---------------------------------------------------------------------------
# the schema-copy digest
# ---------------------------------------------------------------------------
class TestSchemaCopiesMatch:
    """A byte comparison of two copies of one contract."""

    def test_the_shipped_tree_passes(self) -> None:
        done = _run("gate_schema_copies.py")
        assert done.returncode == 0, done.stdout + done.stderr
        assert "schema copies match" in done.stdout

    def test_one_byte_of_divergence_is_caught(self, tmp_path: Path) -> None:
        # The registered mutation, exactly: one appended newline. It is the
        # smallest divergence there is and it is the one a SEMANTIC comparison
        # cannot see -- which is the coverage this gate has that
        # `tests/test_serialization.py` does not.
        for relative in (schema_copies.CANONICAL, schema_copies.BUNDLED):
            (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / relative).write_text('{"title": "x"}\n', encoding="utf-8")
        assert schema_copies.compare(tmp_path)[0] == []
        with (tmp_path / schema_copies.BUNDLED).open("a", encoding="utf-8") as handle:
            handle.write("\n")
        problems, _ = schema_copies.compare(tmp_path)
        assert len(problems) == 1
        assert schema_copies.FAILURE_MARKER in problems[0]

    def test_a_missing_copy_is_a_failure_and_not_a_pass(self, tmp_path: Path) -> None:
        # A comparison of one file against nothing has no right to report
        # agreement, which is the shape `--require` exists for elsewhere.
        (tmp_path / schema_copies.CANONICAL).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / schema_copies.CANONICAL).write_text("{}\n", encoding="utf-8")
        problems, _ = schema_copies.compare(tmp_path)
        assert problems and schema_copies.FAILURE_MARKER in problems[0]


# ---------------------------------------------------------------------------
# Tier 0 purity
# ---------------------------------------------------------------------------
class TestTierZeroPurity:
    """Run in a subprocess, always.

    ``check()`` inspects ``sys.modules`` for optional packages. Calling it
    inside a pytest process would ask whether *pytest's* process had imported
    ``numpy``, which is a question about the test runner and not about Tier 0.
    """

    def test_the_shipped_tree_passes(self) -> None:
        done = _run("gate_tier_zero.py")
        assert done.returncode == 0, done.stdout + done.stderr
        assert "Tier 0 purity OK" in done.stdout

    def test_a_leak_is_reported_through_the_marker(self) -> None:
        # The leak half, provoked without touching the tree: a subprocess that
        # imports one of the optional packages before running the check sees
        # exactly what a package that leaked it would produce.
        source = (
            "import importlib.util, sys, pathlib\n"
            f"spec = importlib.util.spec_from_file_location('g', r'{TOOLS / 'gate_tier_zero.py'}')\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "sys.modules['numpy'] = sys\n"
            "print(m.check())\n"
        )
        done = subprocess.run(
            [sys.executable, "-c", source],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            errors="replace",
        )
        assert done.returncode == 0, done.stderr
        assert "TIER 0 PURITY FAILED" in done.stdout
        assert "numpy" in done.stdout


# ---------------------------------------------------------------------------
# the cold-import ceiling
# ---------------------------------------------------------------------------
class TestImportCeiling:
    """Stubbed probes, because the wall-clock half belongs to the runner."""

    def test_an_eager_binding_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            import_ceiling, "_probe", lambda source: (0, '["acronymkit.enums"]\n', "")
        )
        monkeypatch.setattr(import_ceiling, "cold_import_samples", lambda: ([1.0], []))
        assert import_ceiling.main([]) == 1

    def test_a_clean_import_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(import_ceiling, "_probe", lambda source: (0, "[]\n", ""))
        monkeypatch.setattr(import_ceiling, "cold_import_samples", lambda: ([1.0, 2.0, 3.0], []))
        assert import_ceiling.main([]) == 0

    def test_a_median_over_the_ceiling_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(import_ceiling, "_probe", lambda source: (0, "[]\n", ""))
        monkeypatch.setattr(
            import_ceiling,
            "cold_import_samples",
            lambda: ([import_ceiling.CEILING_MS + 100] * 3, []),
        )
        assert import_ceiling.main([]) == 1

    def test_a_probe_that_cannot_run_is_a_failure_and_not_a_pass(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The heredoc used `check=True`, so a package whose bare import raised
        # produced a traceback rather than a verdict. A gate that dies is not a
        # gate that passed.
        monkeypatch.setattr(import_ceiling, "_probe", lambda source: (1, "", "ImportError: no"))
        monkeypatch.setattr(import_ceiling, "cold_import_samples", lambda: ([1.0], []))
        assert import_ceiling.main([]) == 1


# ---------------------------------------------------------------------------
# the sdist file list
# ---------------------------------------------------------------------------
class TestSdistFileList:
    def test_every_required_path_carries_its_reason(self) -> None:
        # A list of names is the wrong shape and this list will stay a list.
        # What it can do is say why each name is on it, at the moment it fires.
        assert sdist_files.REQUIRED
        for name, why in sdist_files.REQUIRED:
            assert why.strip(), name

    def test_the_checkout_holds_all_of_them(self) -> None:
        assert sdist_files.missing(REPO_ROOT) == []

    def test_an_absence_is_reported_with_its_reason(self, tmp_path: Path) -> None:
        for name, _why in sdist_files.REQUIRED[1:]:
            (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / name).write_text("x", encoding="utf-8")
        absent = sdist_files.missing(tmp_path)
        assert [name for name, _ in absent] == [sdist_files.REQUIRED[0][0]]

    def test_data_licenses_is_on_the_list(self) -> None:
        # Held by this list and by nothing else in the repository: the
        # extracted-tree suite passes with it gone, because no test reads it,
        # and two shipped documents cite it as evidence. Deleting this entry
        # removes the only check on it.
        assert "data/LICENSES.md" in [name for name, _ in sdist_files.REQUIRED]


# ---------------------------------------------------------------------------
# the installed-suite adjudicator
# ---------------------------------------------------------------------------
GREEN_LOG = "\n".join(
    ["SKIPPED [1] tests/test_x.py:1: not a checkout"]
    + [f"FAILED {node} - AssertionError" for node in sorted(installed_suite.EXPECTED_NON_PASSING)]
    + ["= 4218 passed, 66 skipped, 6 failed in 60.00s ="]
)


class TestTheInstalledSuiteAdjudicator:
    """One implementation, applied to a log. ``ci.yml`` runs it; the packaging
    harness imports it."""

    def test_a_run_that_is_accounted_for_exactly_passes(self) -> None:
        assert installed_suite.adjudicate(GREEN_LOG)["rc"] == 0

    def test_an_unexpected_failure_is_refused(self) -> None:
        log = GREEN_LOG.replace(
            "= 4218 passed", "FAILED tests/test_new.py::test_thing - Boom\n= 4218 passed"
        )
        verdict = installed_suite.adjudicate(log)
        assert verdict["rc"] == 1
        assert "tests/test_new.py::test_thing" in verdict["problems"][0]

    def test_a_stale_entry_that_starts_passing_is_refused(self) -> None:
        # An entry that starts passing fails as loudly as a test that starts
        # failing. The list cannot rot into a blanket exemption.
        dropped = sorted(installed_suite.EXPECTED_NON_PASSING)[0]
        log = "\n".join(line for line in GREEN_LOG.splitlines() if dropped not in line)
        verdict = installed_suite.adjudicate(log)
        assert verdict["rc"] == 1
        assert dropped in verdict["problems"][0]

    def test_a_collection_collapse_is_caught_by_the_floor(self) -> None:
        # A green job that ran eleven tests satisfies every other assertion
        # here. The floor is the only thing that notices.
        log = GREEN_LOG.replace("4218 passed", "11 passed")
        verdict = installed_suite.adjudicate(log)
        assert verdict["rc"] == 1
        assert str(installed_suite.PASS_FLOOR) in verdict["problems"][-1]

    def test_every_entry_is_node_keyed_rather_than_file_keyed(self) -> None:
        # THE D-058 SHAPE. While a FILE sat on this list, the job could not see
        # a second defect anywhere inside it -- measured, by reintroducing the
        # fifth historical packaging breakage and getting a log identical to a
        # clean run. Both file-keyed entries were replaced by module-level
        # skips; this is what stops them coming back.
        for node in installed_suite.EXPECTED_NON_PASSING:
            assert "::" in node, node

    def test_windows_separators_in_node_ids_are_normalised(self) -> None:
        log = GREEN_LOG.replace("tests/", "tests\\")
        assert installed_suite.adjudicate(log)["rc"] == 0


# ---------------------------------------------------------------------------
# the two-copy problems that are gone, and the one that is left
# ---------------------------------------------------------------------------
@needs_workflow
class TestTheWorkflowAndTheScriptsAgree:
    def test_ci_invokes_each_extracted_script(self) -> None:
        text = CI.read_text(encoding="utf-8")
        for script in (
            "tools/gate_schema_copies.py",
            "tools/gate_tier_zero.py",
            "tools/gate_import_ceiling.py",
            "tools/gate_installed_suite.py",
            "tools/gate_sdist_files.py",
        ):
            assert script in text, script

    def test_no_heredoc_is_left_for_an_extracted_gate(self) -> None:
        # The extraction is only worth something if the heredoc went away. A
        # workflow carrying both would run one and mutate the other.
        text = CI.read_text(encoding="utf-8")
        for gone in ("EXPECTED_NON_PASSING = {", "CEILING_MS = 30.0", "Tier 0 purity OK"):
            assert gone not in text, gone

    def test_the_packaging_reproduction_still_matches_the_workflow(self) -> None:
        packaging = _load("gate_packaging_mutation")
        assert packaging.sequence_drift(REPO_ROOT) == []

    def test_the_drift_check_can_actually_fail(self, tmp_path: Path) -> None:
        # The guard this replaced printed `WARNING:` and carried on, through a
        # run in which all six sdist builds failed and the job was green. A
        # drift check that cannot fail would be the same defect again.
        packaging = _load("gate_packaging_mutation")
        fragment = packaging.SEQUENCE_FRAGMENTS[0][0]
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
            CI.read_text(encoding="utf-8").replace(fragment, "python -m nothing"),
            encoding="utf-8",
        )
        problems: List[str] = packaging.sequence_drift(tmp_path)
        assert problems and fragment in problems[0]

    def test_the_harness_imports_the_gate_rather_than_copying_it(self) -> None:
        # The whole point of the round. If these ever diverge, one of them is a
        # copy again.
        packaging = _load("gate_packaging_mutation")
        assert set(installed_suite.EXPECTED_NON_PASSING) == packaging.EXPECTED_NON_PASSING
        assert packaging.PASS_FLOOR == installed_suite.PASS_FLOOR
        assert tuple(name for name, _ in sdist_files.REQUIRED) == packaging.TEST_F_LINES


@needs_register
class TestTheRegisterAndTheScriptsAgree:
    """A marker that drifts turns every future demonstration into ``INERT``."""

    def test_each_extracted_gate_declares_the_marker_its_script_prints(self) -> None:
        register = _register()["gates"]
        for gate, module in (
            ("schema_copies_match", schema_copies),
            ("tier_zero_purity", _load("gate_tier_zero")),
            ("import_ceiling", import_ceiling),
        ):
            declared = register[gate]["mutation"]["expect_failure_matching"]
            assert declared == module.FAILURE_MARKER, gate

    def test_each_extracted_gate_declares_the_command_ci_runs(self) -> None:
        register = _register()["gates"]
        for gate, script in (
            ("schema_copies_match", "gate_schema_copies.py"),
            ("tier_zero_purity", "gate_tier_zero.py"),
            ("import_ceiling", "gate_import_ceiling.py"),
        ):
            assert register[gate]["command"] == f"python tools/{script}"
            assert register[gate]["mutation"]["kind"] == "automated"
