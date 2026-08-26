""":file:`.github/gates.toml` must parse, validate, and refuse — because a register nobody checks is a paragraph.

Four defects shipped in one round and every one was the same shape: a check that
could not fail in the environment where it ran (D-058). The register exists so
that shape is countable rather than anecdotal, and this file exists because a
register with no validator would reproduce the defect one level up — a document
asserting coverage, checked by nothing, going quietly false.

What this file pins, and why each item is here
----------------------------------------------
* **The validator has one implementation and these tests drive it.** They import
  ``tools/gates.py`` by path — the same module the ``lint`` job runs and the same
  module ``.github/workflows/gate-mutation.yml`` drives. Three readers with three
  notions of "valid" is how a rule ends up with three behaviours, which is the
  argument ``tests/test_splits_manifest.py`` already makes about
  ``tools/splits.py``.

* **Every rule is mutation-tested, not asserted.** A validator is only worth what
  it refuses. Each rule below gets a deliberately broken manifest and must report
  it — a job in a workflow that the register does not declare, a gate pointing at
  a step that does not exist, an automated mutation with no edits, a refusal with
  no reason, two gates writing one artifact path, a coverage row naming a gate
  that is not declared, an empty ``stops_at``.

* **The anti-rot rule gets its own tests, in both directions.** "Every job in
  every workflow is registered" is the only rule here that checks the register
  against the *tree*; every other rule checks it against itself, and a register
  that has rotted still agrees with itself perfectly. So it is tested that an
  unregistered job is refused and that a fully registered set is accepted.

* **The scanner is tested for the failure that would make everything vacuous.**
  ``scan_workflow`` is an indentation scanner, not a YAML parser. A scanner
  returning nothing makes every rule above trivially true, which is precisely the
  defect being catalogued — so a workflow that scans to zero jobs must be an
  error, and the real workflow files must scan to the jobs they actually have.
  This is the same anchoring the MANIFEST.in parser got in ``ed05317``: a parser
  that returns nothing makes the main test report everything missing, and one
  that returns too much makes it pass while proving nothing.

* **The mutation runner puts the tree back.** The restore is not politeness. It
  is the second half of every demonstration: without it, a gate failing for an
  unrelated reason reads as a successful demonstration. It is exercised against a
  throwaway root rather than the repository, because a test that mutates the
  working tree of a repository several agents are editing is a defect and not a
  test.

* **No probe file survives a run.** ``tools/_gate_probe_*.py`` are created by
  mutations and deleted by the restore. One of them left behind is the visible
  symptom of a restore that did not happen, and it is cheaper to assert than to
  discover.

Nothing here reaches the network, opens a corpus, or edits the repository.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable, List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LOADER = REPO_ROOT / "tools" / "gates.py"
GATES = REPO_ROOT / ".github" / "gates.toml"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

# THE GUARD, PLACED BEFORE THE LOAD AND NOT ON A MARK.
#
# `pytest.mark.skipif` is consulted at COLLECTION and a module body runs at
# IMPORT, which is earlier — the lesson of the fourth and fifth historical
# packaging breakages, both of which shipped past a `skipif` that could not
# help. `tools/` ships in the sdist and is no part of an installed
# distribution, so under the `installed-suite` job the next load would raise
# FileNotFoundError and this file would fail to COLLECT rather than skip.
#
# It is a skip on ONE named condition, deliberately: a module-wide blanket is
# what hid 74 tests in `tests/test_splits_manifest.py` for as long as that file
# existed, and any OTHER error here must still reach the job. `EXPECTED_
# NON_PASSING` in `.github/workflows/ci.yml` is not grown for this file.
if not LOADER.is_file():  # pragma: no cover - CI job only
    pytest.skip(
        "tools/ is not part of an installed distribution; these tests belong to a checkout",
        allow_module_level=True,
    )


def _load_tool() -> ModuleType:
    """Import ``tools/gates.py`` by path.

    ``tools/`` is a directory of scripts and must not become a package: making
    it importable for a test's convenience would change the shape of the thing
    under test. Same mechanism as ``tests/test_splits_manifest.py`` and
    ``tests/test_check_claims.py``.
    """
    spec = importlib.util.spec_from_file_location("_gates_under_test", LOADER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before execution: ``@dataclass`` resolves annotations through
    # ``sys.modules[cls.__module__]`` while the class body is still running.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gates = _load_tool()

#: 3.9 and 3.10 have no ``tomllib`` and ``tomli`` is not a declared dev
#: dependency, so on those interpreters there is no parser to test with. The
#: dedicated CI step runs on 3.12, where this is never skipped.
_NO_PARSER = sys.version_info < (3, 11) and importlib.util.find_spec("tomli") is None

pytestmark = pytest.mark.skipif(_NO_PARSER, reason="tomllib is 3.11+; tomli not installed")

#: For the tests that read the register this repository actually ships.
#:
#: STALE WHEN IT WAS WRITTEN AND CORRECTED HERE: this note used to say
#: `MANIFEST.in` ships `.github/workflows/*.yml` "and nothing else from that
#: directory, so `.github/gates.toml` is absent inside an sdist". `a62f99a`
#: added `include .github/gates.toml` to `MANIFEST.in`, so the register DOES
#: ship and this mark does not fire in the extracted tree. The mark stays,
#: because an installed distribution still has neither — and a guard whose
#: condition is checked rather than assumed costs nothing when it is wrong.
needs_register = pytest.mark.skipif(
    not GATES.is_file(), reason=".github/gates.toml is absent (an installed distribution)"
)


# ---------------------------------------------------------------------------
# a minimal, valid register, and the levers that break it
# ---------------------------------------------------------------------------
_MINIMAL = """
[manifest]
schema_version = 1
stops_at = "at the controls, which a human sees"

[environments.only]
workflow = "w.yml"
job = "solo"
runs_on = "ubuntu-latest"

[gates.thing]
environment = "only"
step = "Do the thing"
defect_class = "behaviour"
cost_rank = 1
blast_radius = "installed_behaviour"
silence = "silent"
redundancy = "sole"
cost_if_inert = "the thing goes wrong and nothing says so"
detects = "a thing going wrong"
[gates.thing.mutation]
kind = "manual"
reason = "the environment cannot be built here"

[[defect_coverage]]
id = "x"
summary = "a real defect, once"
fixed_in = "abc1234"
caught_by = ["thing"]
missed_by = []
measured_on = 2026-08-24
"""

#: What the synthetic workflow scan returns. Passed to ``validate`` explicitly so
#: these tests never depend on the repository's own workflow files.
_WORKFLOWS = {"w.yml": {"solo": ["Do the thing"]}}


@pytest.fixture
def write(tmp_path: Path) -> Callable[[str], object]:
    """Write a register into a temporary directory and load it."""

    def _write(text: str) -> object:
        path = tmp_path / "gates.toml"
        path.write_text(text, encoding="utf-8")
        return gates.load(path)

    return _write


def _problems(manifest: object, workflows: object = None) -> List[str]:
    return gates.validate(manifest, workflows if workflows is not None else _WORKFLOWS)


class TestTheMinimalRegisterIsValid:
    """The control. Without it every refusal below could be a refusal of anything."""

    def test_it_parses_and_validates(self, write: Callable[[str], object]) -> None:
        assert _problems(write(_MINIMAL)) == []

    def test_it_carries_what_the_accessors_promise(self, write: Callable[[str], object]) -> None:
        manifest = write(_MINIMAL)
        assert list(manifest.gates) == ["thing"]
        assert manifest.gates_in("only")[0].name == "thing"
        assert manifest.automated() == []
        assert manifest.with_in_situ_evidence() == []


class TestTheValidatorCatchesWhatItClaimsTo:
    """One deliberately broken register per rule. A validator is what it refuses."""

    def test_an_unregistered_job_is_refused(self, write: Callable[[str], object]) -> None:
        # THE ANTI-ROT RULE. The only rule here that checks the register against
        # the tree rather than against itself.
        extra = {"w.yml": {"solo": ["Do the thing"], "newcomer": ["Something"]}}
        problems = _problems(write(_MINIMAL), extra)
        assert any("newcomer" in p and "not declared" in p for p in problems), problems

    def test_a_registered_job_with_no_gates_needs_a_reason(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL + '\n[environments.spare]\nworkflow = "w.yml"\njob = "second"\n'
        two = {"w.yml": {"solo": ["Do the thing"], "second": []}}
        problems = _problems(write(text), two)
        assert any("no_gates_reason" in p for p in problems), problems

    def test_a_reason_and_a_gate_together_are_refused(self, write: Callable[[str], object]) -> None:
        text = _MINIMAL.replace(
            'runs_on = "ubuntu-latest"', 'runs_on = "ubuntu-latest"\nno_gates_reason = "none"'
        )
        problems = _problems(write(text))
        assert any("One of the two is wrong" in p for p in problems), problems

    def test_a_gate_naming_a_step_that_does_not_exist_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL.replace('step = "Do the thing"', 'step = "Do the renamed thing"')
        problems = _problems(write(text))
        assert any("is not a step of" in p for p in problems), problems

    def test_a_gate_naming_an_undeclared_environment_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL.replace('environment = "only"', 'environment = "elsewhere"')
        problems = _problems(write(text))
        assert any("is not declared" in p for p in problems), problems

    def test_an_unknown_defect_class_is_refused(self, write: Callable[[str], object]) -> None:
        text = _MINIMAL.replace('defect_class = "behaviour"', 'defect_class = "vibes"')
        problems = _problems(write(text))
        assert any("defect_class" in p for p in problems), problems

    def test_a_refusal_with_no_reason_is_refused(self, write: Callable[[str], object]) -> None:
        # R14: a refusal ships with a disposition.
        text = _MINIMAL.replace('reason = "the environment cannot be built here"', "")
        problems = _problems(write(text))
        assert any("refusal ships with a disposition" in p for p in problems), problems

    def test_an_automated_mutation_with_no_edits_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL.replace(
            'kind = "manual"\nreason = "the environment cannot be built here"',
            'kind = "automated"\nartifact = "a.log"',
        ).replace('detects = "a thing going wrong"', 'detects = "x"\ncommand = "python -V"')
        problems = _problems(write(text))
        assert any("requires at least one edit" in p for p in problems), problems

    def test_an_automated_mutation_with_no_command_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL.replace(
            'kind = "manual"\nreason = "the environment cannot be built here"',
            'kind = "automated"\nartifact = "a.log"\nedits = [ { file = "pyproject.toml", '
            'append = "\\n" } ]',
        )
        problems = _problems(write(text))
        assert any("declares no `command`" in p for p in problems), problems

    def test_an_automated_mutation_with_no_artifact_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL.replace(
            'kind = "manual"\nreason = "the environment cannot be built here"',
            'kind = "automated"\nedits = [ { file = "pyproject.toml", append = "\\n" } ]',
        ).replace('detects = "a thing going wrong"', 'detects = "x"\ncommand = "python -V"')
        problems = _problems(write(text))
        assert any("requires an `artifact` path" in p for p in problems), problems

    def test_a_refusal_carrying_edits_is_refused(self, write: Callable[[str], object]) -> None:
        text = _MINIMAL.replace(
            'reason = "the environment cannot be built here"',
            'reason = "no"\nedits = [ { file = "pyproject.toml", append = "\\n" } ]',
        )
        problems = _problems(write(text))
        assert any("declares edits it will never apply" in p for p in problems), problems

    def test_an_unknown_gate_key_is_refused(self, write: Callable[[str], object]) -> None:
        text = _MINIMAL.replace('step = "Do the thing"', 'step = "Do the thing"\nvibe = "good"')
        with pytest.raises(gates.GatesError, match="unknown key"):
            write(text)

    def test_an_unknown_mutation_key_is_refused(self, write: Callable[[str], object]) -> None:
        # The asymmetry `bench/splits.toml` paid for: a misspelt key silently
        # drops the field the structure exists to require.
        text = _MINIMAL.replace('kind = "manual"', 'kind = "manual"\nresaon = "typo"')
        with pytest.raises(gates.GatesError, match="unknown mutation key"):
            write(text)

    def test_an_unknown_mutation_kind_is_refused(self, write: Callable[[str], object]) -> None:
        text = _MINIMAL.replace('kind = "manual"', 'kind = "probably fine"')
        with pytest.raises(gates.GatesError, match="is not one of"):
            write(text)

    def test_an_edit_declaring_two_operations_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL.replace(
            'reason = "the environment cannot be built here"',
            'reason = "no"\nedits = [ { file = "x", append = "a", delete = true } ]',
        )
        with pytest.raises(gates.GatesError, match="exactly one operation"):
            write(text)

    def test_an_edit_naming_a_file_that_does_not_exist_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL.replace(
            'kind = "manual"\nreason = "the environment cannot be built here"',
            'kind = "automated"\nartifact = "a.log"\n'
            'edits = [ { file = "no/such/file.py", append = "x" } ]',
        ).replace('detects = "a thing going wrong"', 'detects = "x"\ncommand = "python -V"')
        problems = _problems(write(text))
        assert any("does not exist, so this mutation cannot be applied" in p for p in problems), (
            problems
        )

    def test_two_gates_writing_one_artifact_are_refused(
        self, write: Callable[[str], object]
    ) -> None:
        text = (
            (
                _MINIMAL
                + """
[gates.twin]
environment = "only"
step = "Do the thing"
defect_class = "behaviour"
command = "python -V"
detects = "the same file"
[gates.twin.mutation]
kind = "automated"
artifact = "a.log"
edits = [ { file = "pyproject.toml", append = "\\n" } ]
"""
            )
            .replace(
                'kind = "manual"\nreason = "the environment cannot be built here"',
                'kind = "automated"\nartifact = "a.log"\n'
                'edits = [ { file = "pyproject.toml", append = "\\n" } ]',
            )
            .replace('detects = "a thing going wrong"', 'detects = "x"\ncommand = "python -V"')
        )
        problems = _problems(write(text))
        assert any("is already used by" in p for p in problems), problems

    def test_an_empty_stops_at_is_refused(self, write: Callable[[str], object]) -> None:
        # The regress does not close on its own. A blank field pretends it does.
        text = _MINIMAL.replace('stops_at = "at the controls, which a human sees"', 'stops_at = ""')
        problems = _problems(write(text))
        assert any("pretends the regress is closed" in p for p in problems), problems

    def test_a_coverage_row_naming_an_undeclared_gate_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL.replace('caught_by = ["thing"]', 'caught_by = ["ghost"]')
        problems = _problems(write(text))
        assert any("which is not declared" in p for p in problems), problems

    def test_a_coverage_row_naming_no_gate_at_all_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL.replace('caught_by = ["thing"]', "caught_by = []")
        problems = _problems(write(text))
        assert any("names no gate at all" in p for p in problems), problems

    def test_a_coverage_row_both_catching_and_missing_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL.replace("missed_by = []", 'missed_by = ["thing"]')
        problems = _problems(write(text))
        assert any("is both caught and missed" in p for p in problems), problems

    def test_a_coverage_row_with_no_date_is_refused(self, write: Callable[[str], object]) -> None:
        text = _MINIMAL.replace("measured_on = 2026-08-24", "")
        problems = _problems(write(text))
        assert any("a coverage claim has a date" in p for p in problems), problems

    def test_a_coverage_row_with_no_commit_is_refused(self, write: Callable[[str], object]) -> None:
        text = _MINIMAL.replace('fixed_in = "abc1234"', 'fixed_in = "sometime last spring"')
        problems = _problems(write(text))
        assert any("is not a commit name" in p for p in problems), problems

    def test_an_in_situ_date_with_no_run_id_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        # Operating rule 1, applied to a gate instead of to a number.
        text = _MINIMAL.replace(
            'kind = "manual"', 'kind = "manual"\nverified_in_situ_on = 2026-08-24'
        )
        problems = _problems(write(text))
        assert any("A date with no run id" in p for p in problems), problems

    def test_an_in_situ_date_with_no_commit_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        # A run id says a demonstration happened. Only the commit says WHICH
        # gate was demonstrated, and a register whose evidence cannot be tied to
        # a tree is a register of claims about runs nobody can re-open.
        text = _MINIMAL.replace(
            'kind = "manual"',
            'kind = "manual"\nverified_in_situ_on = 2026-08-24\nverified_in_situ_run = "1"',
        )
        problems = _problems(write(text))
        assert any("no `verified_in_situ_commit`" in p for p in problems), problems

    def test_an_in_situ_commit_that_is_not_a_commit_name_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL.replace(
            'kind = "manual"',
            'kind = "manual"\nverified_in_situ_commit = "last tuesday"',
        )
        problems = _problems(write(text))
        assert any("is not a commit name" in p for p in problems), problems

    def test_a_workflow_scanning_to_zero_jobs_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        # The failure that would make every rule above vacuously true.
        problems = _problems(write(_MINIMAL), {"w.yml": {"solo": ["Do the thing"]}, "z.yml": {}})
        assert any("scanned to ZERO jobs" in p for p in problems), problems


# ---------------------------------------------------------------------------
# the cost-if-inert ordering
# ---------------------------------------------------------------------------
_GATE_BODY = """environment = "only"
step = "Do the thing"
defect_class = "behaviour"
cost_rank = {rank}
blast_radius = "{blast}"
silence = "{silence}"
redundancy = "{redundancy}"
cost_if_inert = "something breaks"
detects = "a thing going wrong"
"""


def _ranked_pair(
    first: Tuple[int, str, str, str],
    second: Tuple[int, str, str, str],
) -> str:
    """Two gates with declared factors, so an inversion can be constructed."""
    head, _, tail = _MINIMAL.partition("[gates.thing]")
    body, _, coverage = tail.partition("[[defect_coverage]]")
    del body
    parts = [head]
    for name, spec in (("first", first), ("second", second)):
        rank, blast, silence, redundancy = spec
        parts.append(f"[gates.{name}]\n")
        parts.append(
            _GATE_BODY.format(rank=rank, blast=blast, silence=silence, redundancy=redundancy)
        )
        parts.append(f'[gates.{name}.mutation]\nkind = "manual"\nreason = "not here"\n\n')
    parts.append("[[defect_coverage]]")
    parts.append(coverage.replace('caught_by = ["thing"]', 'caught_by = ["first"]'))
    return "".join(parts)


class TestTheCostRanking:
    """``cost_rank`` is a total order derived from declared factors, or it is an opinion.

    ``--check`` printed ``CARRYING IN-SITU EVIDENCE: 0 of 36`` on every CI run
    for a phase. The line was honest and it was useless: it told a reader with
    one afternoon nothing about which gate to fix. These tests are what stop the
    replacement being a column of integers somebody nudges.
    """

    def test_a_ranked_pair_is_valid(self, write: Callable[[str], object]) -> None:
        # The control. Without it every refusal below could be a refusal of
        # anything at all in the two-gate register.
        text = _ranked_pair(
            (1, "published_numbers", "silent", "sole"), (2, "repository", "loud", "sole")
        )
        assert _problems(write(text)) == []

    def test_an_unranked_gate_is_refused(self, write: Callable[[str], object]) -> None:
        text = _MINIMAL.replace("cost_rank = 1\n", "")
        problems = _problems(write(text))
        assert any("permutation of 1..1" in p for p in problems), problems

    def test_a_duplicate_rank_is_refused(self, write: Callable[[str], object]) -> None:
        text = _ranked_pair(
            (1, "published_numbers", "silent", "sole"), (1, "repository", "loud", "sole")
        )
        problems = _problems(write(text))
        assert any("1 repeated [1]" in p for p in problems), problems

    def test_a_gap_in_the_ranks_is_refused(self, write: Callable[[str], object]) -> None:
        text = _ranked_pair(
            (1, "published_numbers", "silent", "sole"), (3, "repository", "loud", "sole")
        )
        problems = _problems(write(text))
        assert any("missing [2]" in p for p in problems), problems

    def test_a_rank_that_inverts_its_own_factors_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        # THE RULE THAT MAKES THE ORDERING FALSIFIABLE. Moving a gate up the
        # list costs an argument about blast radius or silence, in a field,
        # rather than a nudged integer.
        text = _ranked_pair(
            (1, "repository", "loud", "sole"),
            (2, "published_numbers", "silent", "sole"),
        )
        problems = _problems(write(text))
        assert any("may not invert the factors" in p for p in problems), problems

    def test_silence_breaks_ties_within_one_blast_radius(
        self, write: Callable[[str], object]
    ) -> None:
        # A loud gate ranked above a silent one at the same blast radius is the
        # D-058 lesson inverted: every one of those four defects was silent
        # here and loud on a runner.
        text = _ranked_pair(
            (1, "installed_behaviour", "loud", "sole"),
            (2, "installed_behaviour", "silent", "sole"),
        )
        problems = _problems(write(text))
        assert any("may not invert the factors" in p for p in problems), problems

    def test_redundancy_does_not_decide_the_order(self, write: Callable[[str], object]) -> None:
        # DECLARED, PRINTED, AND DELIBERATELY OUT OF THE KEY. As a third
        # lexicographic factor it ranked a resource-consistency check above the
        # whole test suite, purely because the suite is partly duplicated.
        text = _ranked_pair(
            (1, "installed_behaviour", "silent", "partial"),
            (2, "installed_behaviour", "silent", "sole"),
        )
        assert _problems(write(text)) == []

    @pytest.mark.parametrize(
        "field, value",
        [
            ("blast_radius", "catastrophic"),
            ("silence", "quiet"),
            ("redundancy", "none at all"),
        ],
    )
    def test_an_unknown_factor_is_refused(
        self, write: Callable[[str], object], field: str, value: str
    ) -> None:
        text = re.sub(rf'^{field} = ".*"$', f'{field} = "{value}"', _MINIMAL, flags=re.M)
        problems = _problems(write(text))
        assert any(f"{field} {value!r} is not one of" in p for p in problems), problems

    def test_a_gate_with_no_cost_if_inert_is_refused(self, write: Callable[[str], object]) -> None:
        text = _MINIMAL.replace('cost_if_inert = "the thing goes wrong and nothing says so"\n', "")
        problems = _problems(write(text))
        assert any("`cost_if_inert` is required" in p for p in problems), problems

    def test_a_non_integer_rank_is_refused_at_load(self, tmp_path: Path) -> None:
        path = tmp_path / "gates.toml"
        path.write_text(_MINIMAL.replace("cost_rank = 1", 'cost_rank = "first"'), encoding="utf-8")
        with pytest.raises(gates.GatesError, match="must be an integer"):
            gates.load(path)


# ---------------------------------------------------------------------------
# the in-situ evidence quota
# ---------------------------------------------------------------------------
class TestTheInSituQuota:
    """The quota is a ceiling on the DEBT, and every test here is about why.

    A floor on the coverage count is satisfied by a round that adds five gates
    and demonstrates none: ``13 of 36`` becomes ``13 of 41``, the floor holds,
    and the register reports health while going backwards. A ceiling on
    ``gates - in_situ`` cannot be satisfied that way, and the first test below
    is that exact round being refused.
    """

    @staticmethod
    def _manifest(write: Callable[[str], object], gate_count: int, evidenced: int) -> object:
        """A register with ``gate_count`` gates, ``evidenced`` of them in situ."""
        head, _, tail = _MINIMAL.partition("[gates.thing]")
        _, _, coverage = tail.partition("[[defect_coverage]]")
        parts = [head]
        for index in range(gate_count):
            parts.append(f"[gates.g{index}]\n")
            parts.append(
                _GATE_BODY.format(
                    rank=index + 1,
                    blast="installed_behaviour",
                    silence="silent",
                    redundancy="sole",
                )
            )
            parts.append(f'[gates.g{index}.mutation]\nkind = "manual"\nreason = "not here"\n')
            if index < evidenced:
                parts.append(
                    "verified_in_situ_on = 2026-08-25\n"
                    'verified_in_situ_run = "1"\nverified_in_situ_commit = "abc1234"\n'
                )
            parts.append("\n")
        parts.append("[[defect_coverage]]")
        parts.append(coverage.replace('caught_by = ["thing"]', 'caught_by = ["g0"]'))
        return write("".join(parts))

    def test_a_round_that_adds_a_gate_without_evidence_cannot_satisfy_the_quota(
        self, write: Callable[[str], object]
    ) -> None:
        # THE FAILURE MODE THE QUOTA EXISTS FOR, and the one a coverage floor
        # would wave through.
        manifest = self._manifest(write, gate_count=11, evidenced=5)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(label="after", gates=11, in_situ=5),
            ),
        )
        assert any("in-situ debt ROSE" in p for p in problems), problems
        assert any("may not satisfy this quota" in p for p in problems), problems

    def test_a_round_that_adds_a_gate_with_its_evidence_is_accepted(
        self, write: Callable[[str], object]
    ) -> None:
        # The same edit, paid for. The debt holds at five and the round passes.
        manifest = self._manifest(write, gate_count=11, evidenced=6)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(
                    label="after",
                    gates=11,
                    in_situ=6,
                    run="1",
                    commit="abc1234",
                    waiver="the debt held flat rather than falling",
                ),
            ),
            top_ranks=0,
        )
        assert problems == [], problems

    def test_a_debt_that_rises_is_refused_even_with_a_waiver(
        self, write: Callable[[str], object]
    ) -> None:
        # NOT WAIVABLE, on purpose. Every other rule here has a named escape.
        manifest = self._manifest(write, gate_count=11, evidenced=5)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(label="after", gates=11, in_situ=5, waiver="we were busy"),
            ),
        )
        assert any("in-situ debt ROSE" in p for p in problems), problems

    def test_a_round_below_the_quota_with_no_waiver_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        manifest = self._manifest(write, gate_count=10, evidenced=6)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(label="after", gates=10, in_situ=6, run="1", commit="abc1234"),
            ),
            quota=3,
            top_ranks=0,
        )
        assert any("against a quota of 3" in p for p in problems), problems

    def test_the_same_round_with_a_waiver_is_accepted(self, write: Callable[[str], object]) -> None:
        manifest = self._manifest(write, gate_count=10, evidenced=6)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(
                    label="after",
                    gates=10,
                    in_situ=6,
                    run="1",
                    commit="abc1234",
                    waiver="the demonstrable set is exhausted; the next payment is an extraction",
                ),
            ),
            quota=3,
            top_ranks=0,
        )
        assert problems == [], problems

    def test_new_evidence_with_no_run_id_is_refused(self, write: Callable[[str], object]) -> None:
        manifest = self._manifest(write, gate_count=10, evidenced=9)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(label="after", gates=10, in_situ=9),
            ),
            top_ranks=0,
        )
        assert any("names no run id and commit" in p for p in problems), problems

    def test_evidence_deleted_without_a_waiver_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        manifest = self._manifest(write, gate_count=6, evidenced=3)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(label="after", gates=6, in_situ=3),
            ),
            top_ranks=0,
        )
        assert any("in-situ evidence fell from 5 to 3" in p for p in problems), problems

    def test_paying_the_quota_by_deleting_a_check_needs_a_sentence(
        self, write: Callable[[str], object]
    ) -> None:
        # Removing an undemonstrated gate lowers `gates - in_situ` exactly as
        # demonstrating one does, and no arithmetic can tell paying a debt from
        # repudiating it. This is the one rule that asks for prose instead.
        manifest = self._manifest(write, gate_count=6, evidenced=5)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(label="after", gates=6, in_situ=5),
            ),
            top_ranks=0,
        )
        assert any("the register shrank from 10 to 6" in p for p in problems), problems

    def test_a_trajectory_that_disagrees_with_the_live_register_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        # THE COUPLING. Editing the register without appending a round reddens
        # `--check` immediately, which is what makes the trajectory a fact about
        # the tree rather than a note beside it.
        manifest = self._manifest(write, gate_count=10, evidenced=8)
        problems = gates.in_situ_problems(
            manifest,
            (gates.InSituRound(label="stale", gates=9, in_situ=8, run="1", commit="abc1234"),),
            top_ranks=0,
        )
        assert any("says the register holds 9 gate(s); it holds 10" in p for p in problems), (
            problems
        )

    def test_a_trajectory_that_overstates_the_evidence_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        manifest = self._manifest(write, gate_count=10, evidenced=4)
        problems = gates.in_situ_problems(
            manifest,
            (gates.InSituRound(label="stale", gates=10, in_situ=8, run="1", commit="abc1234"),),
            top_ranks=0,
        )
        assert any("says 8 gate(s) carry in-situ evidence; 4 do" in p for p in problems), problems

    def test_the_top_of_the_ranking_must_carry_evidence(
        self, write: Callable[[str], object]
    ) -> None:
        # Ranking the gates and then demonstrating whichever were easiest to
        # mutate is the failure this whole exercise is about.
        manifest = self._manifest(write, gate_count=10, evidenced=0)
        problems = gates.in_situ_problems(
            manifest,
            (gates.InSituRound(label="only", gates=10, in_situ=0),),
            top_ranks=2,
        )
        named = [p for p in problems if "by cost-if-inert" in p]
        assert len(named) == 2, problems
        assert "gates.g0" in named[0] and "gates.g1" in named[1]

    def test_an_empty_trajectory_is_refused(self, write: Callable[[str], object]) -> None:
        manifest = self._manifest(write, gate_count=2, evidenced=2)
        problems = gates.in_situ_problems(manifest, ())
        assert any("IN_SITU_TRAJECTORY is empty" in p for p in problems), problems

    def test_duplicate_round_labels_are_refused(self, write: Callable[[str], object]) -> None:
        manifest = self._manifest(write, gate_count=2, evidenced=2)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="same", gates=2, in_situ=2, run="1", commit="abc1234"),
                gates.InSituRound(label="same", gates=2, in_situ=2, run="1", commit="abc1234"),
            ),
            quota=0,
            top_ranks=0,
        )
        assert any("two rounds labelled" in p for p in problems), problems

    def test_a_demonstrable_gate_with_no_evidence_is_a_debt_rather_than_a_limit(
        self, write: Callable[[str], object]
    ) -> None:
        # An `automated` gate is one whose own command a runner can invoke
        # today, so "we have not" and "we cannot" are different answers and the
        # register has to give the first one.
        head, _, tail = _MINIMAL.partition("[gates.thing]")
        _, _, coverage = tail.partition("[[defect_coverage]]")
        text = (
            head
            + "[gates.runnable]\n"
            + _GATE_BODY.format(
                rank=1, blast="repository", silence="loud", redundancy="sole"
            ).replace('step = "Do the thing"', 'step = "Do the thing"\ncommand = "python -c pass"')
            + '[gates.runnable.mutation]\nkind = "automated"\nexpect = "fail"\n'
            + 'artifact = "a.log"\nedits = [ { file = "README.md", append = "x" } ]\n\n'
            + "[[defect_coverage]]"
            + coverage.replace('caught_by = ["thing"]', 'caught_by = ["runnable"]')
        )
        manifest = write(text)
        problems = gates.in_situ_problems(
            manifest,
            (gates.InSituRound(label="only", gates=1, in_situ=0),),
            top_ranks=0,
        )
        assert any("this harness can mutate carry no in-situ evidence" in p for p in problems), (
            problems
        )

    def test_a_manifest_with_no_manifest_table_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "gates.toml"
        path.write_text("[gates]\n", encoding="utf-8")
        with pytest.raises(gates.GatesError, match=r"\[manifest\] table is required"):
            gates.load(path)

    def test_a_file_that_is_not_toml_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "gates.toml"
        path.write_text("this = = not toml\n", encoding="utf-8")
        with pytest.raises(gates.GatesError, match="not valid TOML"):
            gates.load(path)

    def test_a_missing_file_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(gates.GatesError, match="does not exist"):
            gates.load(tmp_path / "absent.toml")


class TestTheWorkflowScanner:
    """It is a scanner, not a parser, and both directions are anchored."""

    def test_it_finds_jobs_and_step_names(self, tmp_path: Path) -> None:
        path = tmp_path / "w.yml"
        path.write_text(
            "name: X\non:\n  push:\njobs:\n"
            "  first:\n    name: First\n    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - name: Alpha\n        run: true\n"
            "  second:\n    steps:\n      - name: Beta\n        run: true\n",
            encoding="utf-8",
        )
        assert gates.scan_workflow(path) == {"first": ["Alpha"], "second": ["Beta"]}

    def test_a_jobs_key_is_not_confused_with_a_top_level_key(self, tmp_path: Path) -> None:
        # The scanner stops at column zero. Without that, `permissions:` written
        # after `jobs:` would swallow the rest of the file.
        path = tmp_path / "w.yml"
        path.write_text(
            "jobs:\n  only:\n    steps:\n      - name: Alpha\n        run: true\npermissions:\n"
            "  contents: read\n",
            encoding="utf-8",
        )
        assert gates.scan_workflow(path) == {"only": ["Alpha"]}

    def test_it_agrees_with_a_real_yaml_parser_when_one_is_installed(self) -> None:
        """The strongest anchor available, and it costs nothing when absent.

        PyYAML is not a dev dependency of this project and must not become one
        for a validator that reads four files. But when it happens to be
        installed -- it often is, transitively -- the scanner's answer can be
        checked against a real parser instead of against itself. A scanner that
        agrees with itself is the failure mode; this is the one assertion here
        that could catch a scanner quietly reading the wrong thing.
        """
        yaml = pytest.importorskip("yaml")
        for path in sorted(WORKFLOWS.glob("*.yml")):
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            assert set(gates.scan_workflow(path)) == set(document["jobs"]), path.name

    @needs_register
    def test_the_real_workflows_scan_to_the_jobs_they_have(self) -> None:
        # The over-broad direction. A scanner reporting nothing makes the
        # register vacuous; one reporting everything makes it noise.
        scanned = gates.scan_workflows(WORKFLOWS)
        assert "ci.yml" in scanned
        assert {"lint", "test", "build", "installed-suite", "air-gap"} <= set(scanned["ci.yml"])
        assert "Mypy" in scanned["ci.yml"]["lint"]
        assert all(jobs for jobs in scanned.values()), scanned


@needs_register
class TestTheRegisterThisRepositoryShips:
    """The file itself, not a synthetic one."""

    def test_it_validates(self) -> None:
        manifest = gates.load(GATES)
        assert gates.validate(manifest) == []

    def test_every_workflow_job_is_registered(self) -> None:
        manifest = gates.load(GATES)
        declared = {(e.workflow, e.job) for e in manifest.environments.values()}
        for name, jobs in gates.scan_workflows(WORKFLOWS).items():
            for job in jobs:
                assert (name, job) in declared, f"{name}:{job} is not registered"

    def test_the_five_historical_breakages_are_all_recorded(self) -> None:
        manifest = gates.load(GATES)
        assert {d.id for d in manifest.defects} == {"a", "b", "c", "d", "e"}

    def test_the_measured_coverage_totals_are_what_the_docs_say(self) -> None:
        # 4 of 5 for build's extracted tree, 2 of 5 for installed-suite,
        # re-measured 2026-08-24 rather than copied from D-050. If a gate is
        # renamed or a row is edited, this is what says the published totals
        # moved.
        manifest = gates.load(GATES)

        def caught(gate: str) -> int:
            return sum(1 for d in manifest.defects if gate in d.caught_by)

        assert caught("sdist_extracted_tree_suite") == 4, "build's extracted tree"
        assert caught("installed_expected_non_passing") == 2, "installed-suite"
        assert caught("sdist_file_list") == 2, "the test -f lines"
        # Every row classifies every one of the three, in one direction or the
        # other. A gate silently omitted from a row is a coverage claim nobody
        # made, and it would read as coverage.
        for defect in manifest.defects:
            classified = set(defect.caught_by) | set(defect.missed_by)
            assert {
                "sdist_file_list",
                "sdist_extracted_tree_suite",
                "installed_expected_non_passing",
            } <= classified, defect.id

    def test_the_in_situ_count_is_reported_rather_than_assumed(self) -> None:
        # Not an assertion that it is zero -- it should stop being zero. An
        # assertion that the register can answer the question at all, which is
        # the whole content of R11.
        manifest = gates.load(GATES)
        assert isinstance(manifest.with_in_situ_evidence(), list)
        for gate in manifest.gates.values():
            if gate.mutation.verified_in_situ_on is not None:
                assert gate.mutation.verified_in_situ_run

    def test_no_probe_file_survived_a_mutation_run(self) -> None:
        # A restore that did not happen leaves one of these behind.
        left = sorted(p.name for p in (REPO_ROOT / "tools").glob("_gate_probe_*"))
        assert left == [], left


class TestTheMutationRunner:
    """Applied, required to fail, restored, and required to pass again."""

    @staticmethod
    def _root(tmp_path: Path) -> Path:
        script = tmp_path / "probe_gate.py"
        script.write_text(
            "import pathlib, sys\nsys.exit(1 if pathlib.Path('broken.txt').exists() else 0)\n",
            encoding="utf-8",
        )
        (tmp_path / "subject.txt").write_text("fine\n", encoding="utf-8")
        return tmp_path

    def _gate(self, kind: str = "automated", **edits: object) -> object:
        return gates.Gate(
            name="probe",
            environment="only",
            step="Do the thing",
            defect_class="behaviour",
            detects="a probe",
            command="python probe_gate.py",
            mutation=gates.Mutation(
                kind=kind,
                artifact="probe.log",
                edits=(gates.Edit(**edits),) if edits else (),
            ),
        )

    def test_a_live_gate_is_demonstrated_and_the_tree_is_restored(self, tmp_path: Path) -> None:
        root = self._root(tmp_path)
        outcome = gates.mutate(
            self._gate(file="broken.txt", create="x\n"), root=root, artifacts=tmp_path / "art"
        )
        assert outcome.verdict == "demonstrated", outcome.detail
        assert outcome.mutated_rc == 1
        assert outcome.restored_rc == 0
        assert not (root / "broken.txt").exists()
        assert (tmp_path / "art" / "probe.log").is_file()

    def test_a_gate_that_does_not_notice_is_reported_INERT(self, tmp_path: Path) -> None:
        # The finding, not an error. A gate ran against a tree carrying the
        # defect it exists to catch and did not fail.
        root = self._root(tmp_path)
        outcome = gates.mutate(self._gate(file="subject.txt", append="ignored\n"), root=root)
        assert outcome.verdict == "INERT", outcome.detail
        assert not outcome.ok
        assert (root / "subject.txt").read_text(encoding="utf-8") == "fine\n"

    def test_a_negative_control_passes_when_the_mutation_changes_nothing(
        self, tmp_path: Path
    ) -> None:
        root = self._root(tmp_path)
        gate = gates.Gate(
            name="probe",
            environment="only",
            step="Do the thing",
            defect_class="positive_control",
            detects="a probe",
            command="python probe_gate.py",
            mutation=gates.Mutation(
                kind="automated",
                expect="pass",
                artifact="probe.log",
                edits=(gates.Edit(file="subject.txt", append="ignored\n"),),
            ),
        )
        outcome = gates.mutate(gate, root=root)
        assert outcome.verdict == "demonstrated", outcome.detail

    def test_an_already_failing_gate_is_reported_UNRESTORED(self, tmp_path: Path) -> None:
        # Without this half, a broken checkout reads as a successful
        # demonstration for every gate in the register.
        root = self._root(tmp_path)
        (root / "broken.txt").write_text("already\n", encoding="utf-8")
        outcome = gates.mutate(self._gate(file="subject.txt", append="x\n"), root=root)
        assert outcome.verdict == "UNRESTORED", outcome.detail

    def test_a_refusal_is_skipped_rather_than_run(self, tmp_path: Path) -> None:
        gate = gates.Gate(
            name="probe",
            environment="only",
            step="Do the thing",
            defect_class="behaviour",
            detects="a probe",
            mutation=gates.Mutation(kind="inline", reason="a heredoc"),
        )
        outcome = gates.mutate(gate, root=self._root(tmp_path))
        assert outcome.verdict == "skipped"
        assert outcome.ok
        assert outcome.detail == "a heredoc"

    def test_a_replace_edit_with_an_ambiguous_anchor_is_refused(self, tmp_path: Path) -> None:
        root = self._root(tmp_path)
        (root / "subject.txt").write_text("a\na\n", encoding="utf-8")
        with pytest.raises(gates.GatesError, match="anchor occurs 2 times"):
            gates.mutate(
                self._gate(file="subject.txt", find="a", replace="b"),
                root=root,
            )
        assert (root / "subject.txt").read_text(encoding="utf-8") == "a\na\n"


class TestTheEnvironmentAssertion:
    """`holds` and `lacks` are globs so they can be checked, not admired."""

    def test_a_missing_hold_is_reported(self, tmp_path: Path) -> None:
        env = gates.Environment(name="e", workflow="w.yml", job="j", holds=("nothing/here.txt",))
        problems = gates.assert_environment(env, root=tmp_path)
        assert any("HOLDS" in p for p in problems), problems

    def test_a_present_lack_is_reported(self, tmp_path: Path) -> None:
        (tmp_path / "corpus.json").write_text("{}", encoding="utf-8")
        env = gates.Environment(name="e", workflow="w.yml", job="j", lacks=("corpus.json",))
        problems = gates.assert_environment(env, root=tmp_path)
        assert any("LACKS" in p and "tautology" in p for p in problems), problems

    def test_an_environment_that_matches_reports_nothing(self, tmp_path: Path) -> None:
        (tmp_path / "present.txt").write_text("x", encoding="utf-8")
        env = gates.Environment(
            name="e", workflow="w.yml", job="j", holds=("present.txt",), lacks=("absent.txt",)
        )
        assert gates.assert_environment(env, root=tmp_path) == []


class TestStaleness:
    """A note, never a failure."""

    def test_an_old_verification_is_noted(self, write: Callable[[str], object]) -> None:
        import datetime

        text = _MINIMAL.replace(
            'kind = "manual"',
            'kind = "manual"\nverified_locally_on = 2020-01-01',
        )
        manifest = write(text)
        notes = gates.stale_notes(manifest, today=datetime.date(2026, 8, 24))
        assert notes and "last verified" in notes[0]
        # And it is a note: validate() says nothing about it.
        assert not any("verified" in p for p in _problems(manifest))

    def test_a_recent_verification_is_not_noted(self, write: Callable[[str], object]) -> None:
        import datetime

        text = _MINIMAL.replace(
            'kind = "manual"',
            'kind = "manual"\nverified_locally_on = 2026-08-20',
        )
        manifest = write(text)
        assert gates.stale_notes(manifest, today=datetime.date(2026, 8, 24)) == []


class TestTheVerdictRestsOnANamedLine:
    """``rc != 0`` is not evidence that a gate caught anything.

    ``gates.suite`` is the case this rule was written from and it is worth the
    paragraph. Its probe edits ``tests/test_splits_manifest.py``, which is also
    the file its own register entry anchors on -- so while the mutation is
    applied, ``test_gate_manifest.py`` correctly reports the anchor no longer
    matches and the suite goes red on THAT, whether or not the D-058 defect is
    caught. Measured with ``data/`` present, where the register predicts the
    gate is inert: rc=1, and the only failure is the anchor check.

    So the gate's automated verdict could not have come back ``INERT`` for any
    tree. ``docs/GATES.md`` already said "take the evidence from the line, not
    from the verdict"; nothing enforced it. These tests are the enforcement.
    """

    def test_an_automated_fail_mutation_must_name_its_line(
        self, write: Callable[[str], object]
    ) -> None:
        text = _MINIMAL.replace(
            '[gates.thing.mutation]\nkind = "manual"\n'
            'reason = "the environment cannot be built here"',
            '[gates.thing.mutation]\nkind = "automated"\nexpect = "fail"\n'
            'artifact = "a.log"\nedits = [{ file = "gates.toml", append = "x" }]',
        ).replace('step = "Do the thing"', 'step = "Do the thing"\ncommand = "python -c pass"', 1)
        problems = _problems(write(text))
        assert any("requires `expect_failure_matching`" in p for p in problems), problems

    def test_a_refusal_may_not_declare_one(self, write: Callable[[str], object]) -> None:
        text = _MINIMAL.replace(
            'reason = "the environment cannot be built here"',
            'reason = "the environment cannot be built here"\nexpect_failure_matching = "boom"',
        )
        problems = _problems(write(text))
        assert any("only a mutation this harness runs can use" in p for p in problems), problems

    def test_a_refusal_may_not_declare_a_setup(self, write: Callable[[str], object]) -> None:
        text = _MINIMAL.replace(
            'reason = "the environment cannot be built here"',
            'reason = "the environment cannot be built here"\nsetup = "python -c pass"',
        )
        problems = _problems(write(text))
        assert any("`setup`" in p for p in problems), problems

    def test_a_negative_control_may_not_name_a_failure_line(
        self, write: Callable[[str], object]
    ) -> None:
        # A mutation that must NOT be detected has no failure output to match.
        text = _MINIMAL.replace(
            '[gates.thing.mutation]\nkind = "manual"\n'
            'reason = "the environment cannot be built here"',
            '[gates.thing.mutation]\nkind = "automated"\nexpect = "pass"\n'
            'expect_failure_matching = "boom"\nartifact = "a.log"\n'
            'edits = [{ file = "gates.toml", append = "x" }]',
        ).replace('step = "Do the thing"', 'step = "Do the thing"\ncommand = "python -c pass"', 1)
        problems = _problems(write(text))
        assert any('expect = "pass"' in p for p in problems), problems

    def test_a_failure_without_the_named_line_is_inert(self, tmp_path: Path) -> None:
        # The whole rule, end to end: the gate DID exit non-zero, and it is
        # still not a demonstration, because the failure is not the one the
        # register predicted.
        root = TestTheMutationRunner._root(tmp_path)
        gate = gates.Gate(
            name="probe",
            environment="only",
            step="Do the thing",
            defect_class="behaviour",
            detects="a probe",
            command="python probe_gate.py",
            mutation=gates.Mutation(
                kind="automated",
                artifact="probe.log",
                expect_failure_matching="a line this probe never prints",
                edits=(gates.Edit(file="broken.txt", create="x\n"),),
            ),
        )
        outcome = gates.mutate(gate, root=root)
        assert outcome.mutated_rc == 1
        assert outcome.verdict == "INERT", outcome.detail
        assert "does not contain" in outcome.detail

    def test_the_same_mutation_with_the_right_line_is_demonstrated(self, tmp_path: Path) -> None:
        # The control. Without it the test above would pass against a harness
        # that had simply stopped reporting demonstrations.
        root = tmp_path
        (root / "probe_gate.py").write_text(
            "import pathlib, sys\n"
            "if pathlib.Path('broken.txt').exists():\n"
            "    print('PROBE GATE FAILED')\n"
            "    sys.exit(1)\n",
            encoding="utf-8",
        )
        gate = gates.Gate(
            name="probe",
            environment="only",
            step="Do the thing",
            defect_class="behaviour",
            detects="a probe",
            command="python probe_gate.py",
            mutation=gates.Mutation(
                kind="automated",
                artifact="probe.log",
                expect_failure_matching="PROBE GATE FAILED",
                edits=(gates.Edit(file="broken.txt", create="x\n"),),
            ),
        )
        assert gates.mutate(gate, root=root).verdict == "demonstrated"


class TestTheSetupCommand:
    """For the one gate whose environment puts the code out of the tree's reach.

    ``ci.yml``'s ``import-time`` job installs NON-EDITABLY on purpose, so an
    edit to ``src/`` never reaches the interpreter that gate measures. Without a
    re-install the mutation is inert there by construction -- which reads as a
    blind gate when the harness simply never touched what the gate looks at.
    """

    def test_the_setup_runs_before_the_gate(self, tmp_path: Path) -> None:
        (tmp_path / "make.py").write_text(
            "import pathlib; pathlib.Path('installed.txt').write_text('yes')\n",
            encoding="utf-8",
        )
        (tmp_path / "probe_gate.py").write_text(
            "import pathlib, sys\n"
            "if not pathlib.Path('installed.txt').exists():\n"
            "    sys.exit('setup did not run')\n"
            "if pathlib.Path('broken.txt').exists():\n"
            "    print('PROBE GATE FAILED')\n"
            "    sys.exit(1)\n",
            encoding="utf-8",
        )
        gate = gates.Gate(
            name="probe",
            environment="only",
            step="Do the thing",
            defect_class="behaviour",
            detects="a probe",
            command="python probe_gate.py",
            mutation=gates.Mutation(
                kind="automated",
                artifact="probe.log",
                setup="python make.py",
                expect_failure_matching="PROBE GATE FAILED",
                edits=(gates.Edit(file="broken.txt", create="x\n"),),
            ),
        )
        outcome = gates.mutate(gate, root=tmp_path)
        assert outcome.verdict == "demonstrated", outcome.detail

    def test_a_setup_that_fails_is_not_a_demonstration(self, tmp_path: Path) -> None:
        (tmp_path / "probe_gate.py").write_text("import sys; sys.exit(1)\n", encoding="utf-8")
        gate = gates.Gate(
            name="probe",
            environment="only",
            step="Do the thing",
            defect_class="behaviour",
            detects="a probe",
            command="python probe_gate.py",
            mutation=gates.Mutation(
                kind="automated",
                artifact="probe.log",
                setup="python no_such_setup.py",
                expect_failure_matching="PROBE GATE FAILED",
                edits=(gates.Edit(file="broken.txt", create="x\n"),),
            ),
        )
        outcome = gates.mutate(gate, root=tmp_path)
        assert outcome.verdict == "UNRESTORED", outcome.detail
        assert "never ran against the mutated tree" in outcome.detail
        assert not (tmp_path / "broken.txt").exists()


class TestWithdrawingEvidence:
    """A count that can only rise is not a measurement.

    Until this round the debt-may-not-rise rule fired first and was declared not
    waivable, so retiring a demonstration was arithmetically impossible: the
    debt goes up by one and every escape was refused before it was consulted.
    That also made ``docs/GATES.md``'s own documented waiver -- *"a round that
    adds an `automated` gate it could not run in CI in the same commit"* --
    unreachable, because adding such a gate raises the debt too.

    So a rise is now allowed when it is ATTRIBUTED, and refused when it is not.
    """

    _manifest = staticmethod(TestTheInSituQuota._manifest)

    def test_an_unattributed_rise_is_still_refused(self, write: Callable[[str], object]) -> None:
        manifest = self._manifest(write, gate_count=11, evidenced=5)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(label="after", gates=11, in_situ=5, waiver="we were busy"),
            ),
            top_ranks=0,
        )
        assert any("in-situ debt ROSE" in p for p in problems), problems

    def test_a_rise_attributed_to_a_gate_owed_forward_is_accepted(
        self, write: Callable[[str], object]
    ) -> None:
        manifest = self._manifest(write, gate_count=11, evidenced=5)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(
                    label="after",
                    gates=11,
                    in_situ=5,
                    owed_forward=1,
                    waiver="the run that demonstrates it is the one this commit triggers",
                ),
            ),
            top_ranks=0,
        )
        assert problems == [], problems

    def test_an_attribution_without_a_waiver_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        # The attribution says WHAT rose. The waiver is where somebody says why
        # that was the right thing to do.
        manifest = self._manifest(write, gate_count=11, evidenced=5)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(label="after", gates=11, in_situ=5, owed_forward=1),
            ),
            top_ranks=0,
        )
        assert any("and no waiver" in p for p in problems), problems

    def test_a_withdrawal_names_the_gate(self, write: Callable[[str], object]) -> None:
        manifest = self._manifest(write, gate_count=10, evidenced=4)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(label="after", gates=10, in_situ=4, waiver="it was unsound"),
            ),
            top_ranks=0,
        )
        assert any("named in `withdrawn_gates`" in p for p in problems), problems

    def test_a_named_withdrawal_is_accepted(self, write: Callable[[str], object]) -> None:
        manifest = self._manifest(write, gate_count=10, evidenced=4)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(label="before", gates=10, in_situ=5),
                gates.InSituRound(
                    label="after",
                    gates=10,
                    in_situ=4,
                    withdrawn_gates=("g4",),
                    owed_forward=1,
                    waiver="its verdict was reachable with the defect uncaught",
                ),
            ),
            top_ranks=0,
        )
        assert problems == [], problems

    def test_withdrawing_a_gate_that_still_carries_evidence_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        manifest = self._manifest(write, gate_count=10, evidenced=5)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(
                    label="only",
                    gates=10,
                    in_situ=5,
                    withdrawn_gates=("g0",),
                    waiver="said so",
                ),
            ),
            top_ranks=0,
        )
        assert any("still carries a verified_in_situ_run" in p for p in problems), problems

    def test_withdrawing_a_gate_that_does_not_exist_is_refused(
        self, write: Callable[[str], object]
    ) -> None:
        manifest = self._manifest(write, gate_count=10, evidenced=5)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(
                    label="only",
                    gates=10,
                    in_situ=5,
                    withdrawn_gates=("ghost",),
                    waiver="said so",
                ),
            ),
            top_ranks=0,
        )
        assert any("not a gate in this register" in p for p in problems), problems

    def test_a_withdrawn_top_ranked_gate_is_allowed_only_while_it_is_owed_forward(
        self, write: Callable[[str], object]
    ) -> None:
        # Withdrawal matters MOST at the top of the ranking, which is exactly
        # where the old rule made it unsayable. It is allowed, and only while a
        # re-take is owed.
        import dataclasses

        manifest = self._manifest(write, gate_count=10, evidenced=0)
        owed = gates.InSituRound(
            label="only",
            gates=10,
            in_situ=0,
            withdrawn_gates=("g0",),
            owed_forward=1,
            waiver="the harness verdict for it carried no information",
        )
        problems = gates.in_situ_problems(manifest, (owed,), top_ranks=1)
        assert not any("by cost-if-inert" in p for p in problems), problems

        forgotten = dataclasses.replace(owed, owed_forward=0)
        problems = gates.in_situ_problems(manifest, (forgotten,), top_ranks=1)
        assert any("by cost-if-inert" in p for p in problems), problems

    def test_a_promise_owed_forward_has_a_due_date(self, write: Callable[[str], object]) -> None:
        # `owed_forward` is a promise that the next CI run takes the evidence.
        # A promise nothing checks is the shape this register catalogues.
        manifest = self._manifest(write, gate_count=10, evidenced=5)
        problems = gates.in_situ_problems(
            manifest,
            (
                gates.InSituRound(
                    label="promised", gates=10, in_situ=5, owed_forward=2, waiver="next run"
                ),
                gates.InSituRound(label="later", gates=10, in_situ=5),
            ),
            quota=0,
            top_ranks=0,
        )
        assert any("owed 2 gate(s) forward" in p for p in problems), problems


class TestEvidenceProvenance:
    """The proof that licensed the first harvest had a one-commit lifetime.

    All thirteen demonstrations rested on one sentence: that ``git diff
    <harvest commit> HEAD`` over eight paths was EMPTY. That was true when it
    was written and false on the very next commit. What replaces it is a
    per-gate dependency set, computed rather than asserted.
    """

    def test_the_dependency_set_is_edits_plus_command_plus_workflow(
        self, write: Callable[[str], object]
    ) -> None:
        manifest = write(_MINIMAL)
        depends, unbounded = gates.evidence_dependencies(manifest.gates["thing"], manifest)
        assert ".github/workflows/w.yml" in depends
        assert unbounded is True

    def test_a_command_naming_a_file_closes_the_set(self, write: Callable[[str], object]) -> None:
        text = _MINIMAL.replace(
            'step = "Do the thing"',
            'step = "Do the thing"\ncommand = "python tools/gates.py --check"',
            1,
        )
        manifest = write(text)
        depends, unbounded = gates.evidence_dependencies(manifest.gates["thing"], manifest)
        assert "tools/gates.py" in depends
        assert unbounded is False

    def test_a_command_naming_no_file_is_reported_unbounded_rather_than_empty(
        self, write: Callable[[str], object]
    ) -> None:
        # An empty changed-set would read as "nothing this gate depends on has
        # moved", which is the flattering answer and the false one.
        text = _MINIMAL.replace(
            'step = "Do the thing"', 'step = "Do the thing"\ncommand = "python -m pytest"', 1
        )
        manifest = write(text)
        _, unbounded = gates.evidence_dependencies(manifest.gates["thing"], manifest)
        assert unbounded is True

    @needs_register
    def test_the_live_register_answers_the_question_for_every_demonstrated_gate(self) -> None:
        manifest = gates.load(GATES)
        records = gates.evidence_provenance(manifest)
        assert len(records) == len(manifest.with_in_situ_evidence())
        for record in records:
            assert record.state in ("describes HEAD", "predates a change", "unknown")


class TestTheRestoreNoticesAConcurrentWrite:
    """One declared mutation deletes ``bench/results.json`` for a gate run, and
    this repository is edited by several agents at once."""

    def test_a_file_written_under_the_mutation_is_reported(self, tmp_path: Path) -> None:
        target = tmp_path / "subject.txt"
        target.write_text("original\n", encoding="utf-8")
        saved = [gates._apply(gates.Edit(file="subject.txt", append="mutated\n"), tmp_path)]
        target.write_text("somebody else wrote this\n", encoding="utf-8")
        notes = gates._restore(saved)
        assert notes and "is not as the mutation left it" in notes[0]
        assert target.read_text(encoding="utf-8") == "original\n"

    def test_an_undisturbed_restore_says_nothing(self, tmp_path: Path) -> None:
        target = tmp_path / "subject.txt"
        target.write_text("original\n", encoding="utf-8")
        saved = [gates._apply(gates.Edit(file="subject.txt", append="mutated\n"), tmp_path)]
        assert gates._restore(saved) == []
        assert target.read_text(encoding="utf-8") == "original\n"
