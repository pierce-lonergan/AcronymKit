#!/usr/bin/env python3
"""Load, validate and mutate ``.github/gates.toml`` -- the register of every CI check.

Why this exists
---------------
Four defects shipped in one round and every one was the same shape: **a check
that could not fail in the environment where it ran** (D-058). The claims gate
could not fail in a checkout holding every file it scans. The suite could not
fail on a machine holding ``data/`` and ``tools/``. The type checker could not
fail against a ``click`` predating ``match``. ``tests/test_splits_manifest.py``
had never once executed in the extracted tree, hiding a whole module behind a
green ``build`` job.

None of those was found by a gate. All four were found by the one environment
that differed, which was CI. A green tick was read as evidence and was not
evidence, because nobody had ever established that the tick could go red.

So this file is the register, and the rule it exists to serve is R11:

    A gate must be DEMONSTRATED CAPABLE OF FAILING in the environment where it
    runs. Not locally. Not in principle. In situ, by mutation, with the failure
    captured.

Three things at once, deliberately -- the same shape as ``tools/splits.py``, and
for the same reason: one implementation of "valid" driven by a CI step, a test
module and a runner cannot drift into three behaviours.

* a **typed accessor** (:class:`GateManifest`, :class:`Gate`,
  :class:`Environment`) so a workflow, a doc page and a test all ask the same
  object what a gate is for;
* a **validator** (:func:`validate`) with one implementation, driven by the
  ``lint`` CI step and by ``tests/test_gate_manifest.py``; and
* a **mutation runner** (``--mutate``) that applies a declared edit, runs the
  gate's own command, and *requires* it to fail -- then restores the tree and
  requires the same command to pass again.

What the validator enforces, and why each rule is here
------------------------------------------------------
``every job in every workflow is accounted for``
    This is the rule that keeps the manifest from rotting, and it is the only
    one that is not about the manifest's own contents. Every job in every file
    under ``.github/workflows`` must either carry at least one gate or declare a
    ``no_gates_reason``. A new job added tomorrow fails ``--check`` until someone
    says what it checks or says that it checks nothing. Without it this file is
    a paragraph that was true once -- which is the failure mode
    ``bench/splits.toml`` recorded eleven times over before anything parsed it.

``a declared step must exist in the workflow``
    A gate naming a step that has been renamed or deleted is a pointer into
    nothing, and the register would still print it as covered. The step name is
    matched against the workflow text, so a rename is a red ``--check`` rather
    than a silent orphan.

``a mutation is required, or a refusal with a disposition``
    R14: refusal is a deliverable and ships with a disposition. A gate may
    declare ``kind = "automated"`` (an edit this file can apply and revert), or
    it may decline -- but then it carries a ``reason``, and the reason is printed
    in the summary rather than buried. ``kind = "inline"`` is the commonest
    refusal here and it names a real architectural fact: a gate whose
    implementation is a heredoc inside ``ci.yml`` has no command a runner can
    invoke, so a mutation harness could only ever run a *copy* of it -- and
    D-018 already closed the question of whether a copy may stand in for the
    thing (it may not).

``unknown keys are refused on every table``
    ``bench/splits.toml`` learned this the expensive way: a misspelt
    ``laps_trigger`` silently drops the one field the structure exists to
    require. Same asymmetry is *not* offered here -- there is no ``extra`` bag on
    a gate, because every field of a gate is load-bearing.

``in-situ evidence is counted, never assumed``
    A mutation verified on a developer's machine is not R11 evidence: three of
    the four defects that motivated this file were invisible locally. So
    :class:`Mutation` carries ``verified_in_situ``, ``--check`` prints how many
    gates have it, and the count is printed on every CI run whether it is
    flattering or not. **On the day this file was written that count was zero**,
    and the summary line says so rather than implying otherwise.

What this file does NOT do
--------------------------
It does not run the gates. It runs *one* gate under *one* mutation, on demand,
and asserts the outcome. The gates themselves are run by
``.github/workflows/ci.yml`` and nothing here changes that -- a register that
also executed the things it registers would be a second implementation of CI.

Usage::

    python tools/gates.py --check                 # the CI gate
    python tools/gates.py --list                  # the register as a table
    python tools/gates.py --json                  # the register as JSON
    python tools/gates.py --mutate lint.mypy      # one mutation, with restore
    python tools/gates.py --mutate-environment lint --artifacts DIR

Nothing here is imported by the library, and nothing here touches the network.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
GATES_PATH = REPO_ROOT / ".github" / "gates.toml"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

#: What a gate is *for*. Closed, because a free-text class is a label rather
#: than a category, and the point of the register is to be able to ask "which
#: gates cover this shape of defect" and get an answer that is not a grep.
#:
#: ``artifact_contents``   the distribution ships (or omits) a file.
#: ``environment_drift``   the runner differs from a developer machine.
#: ``static_analysis``     the source is ill-formed, ill-typed or ill-styled.
#: ``behaviour``           the code does the wrong thing when run.
#: ``claim_backing``       a published number or a governance declaration.
#: ``budget``              a size, a time or a count against a ceiling.
#: ``supply_chain``        provenance, signing, dependency and scanning checks.
#: ``positive_control``    a check on the *harness*, not on the tree: it exists
#:                         to prove that the assertions around it could fail.
DEFECT_CLASSES = (
    "artifact_contents",
    "environment_drift",
    "static_analysis",
    "behaviour",
    "claim_backing",
    "budget",
    "supply_chain",
    "positive_control",
)

#: How a gate's capacity to fail is established.
#:
#: ``automated``  an edit declared below; this file can apply it, run the gate's
#:                own command, require a failure, and put the tree back.
#: ``inline``     the gate's implementation is a heredoc inside a workflow file.
#:                There is no command to invoke, so a harness could only run a
#:                copy. Refused, with the extraction named as the fix.
#: ``control``    the step IS a positive control -- it exists to prove that its
#:                neighbours can fail. Mutating a control is a different task and
#:                is recorded as such.
#: ``manual``     mutable, but only by hand and only in an environment this
#:                harness cannot create (a release, a privileged namespace).
#: ``none``       no mutation is proposed, and the reason says why.
MUTATION_KINDS = ("automated", "inline", "control", "manual", "none")

#: Every key a ``[gates.<id>]`` table may carry.
GATE_FIELDS = (
    "environment",
    "step",
    "command",
    "defect_class",
    "detects",
    "blind_to",
    "mutation",
)

#: Every key a ``[gates.<id>.mutation]`` table may carry.
MUTATION_FIELDS = (
    "kind",
    "reason",
    "expect",
    "artifact",
    "edits",
    "verified_locally_on",
    "verified_in_situ_on",
    "verified_in_situ_run",
    "note",
)

#: Every key an ``[environments.<id>]`` table may carry.
ENVIRONMENT_FIELDS = (
    "workflow",
    "job",
    "runs_on",
    "holds",
    "lacks",
    "note",
    "no_gates_reason",
)

#: Every key an edit inside ``mutation.edits`` may carry. One operation per
#: table; the validator refuses a table declaring two, because "find/replace and
#: also delete the file" has no defined order and would revert wrongly.
EDIT_FIELDS = ("file", "find", "replace", "delete_line_containing", "append", "create", "delete")

#: Every key a ``[[defect_coverage]]`` table may carry.
DEFECT_FIELDS = (
    "id",
    "summary",
    "fixed_in",
    "caught_by",
    "missed_by",
    "not_applicable",
    "measured_on",
    "measured_in",
    "note",
)

#: A git object name, short or long.
_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")

#: How long a recorded verification may stand before ``--check`` mentions it.
#: A NOTE and never a failure, for the reason ``tools/splits.py`` gives about
#: its own staleness window: a gate that turns red with the passage of time
#: fires on an unrelated commit.
STALE_AFTER_DAYS = 120


class GatesError(Exception):
    """The manifest could not be read, or names something that does not exist."""


def _load_toml(path: Path) -> Dict[str, Any]:
    """Parse ``path`` as TOML on any supported interpreter.

    Same reasoning as ``tools/splits.py``: ``tomllib`` is 3.11+ and ``tomli`` is
    not a declared dev dependency, so on 3.9 and 3.10 there may be no parser.
    That is an error rather than a silent pass -- a validator that succeeds
    because it could not read the file is the exact defect this register exists
    to catalogue.
    """
    if sys.version_info >= (3, 11):
        import tomllib as _toml
    else:  # pragma: no cover - 3.9/3.10 path
        try:
            import tomli as _toml
        except ImportError as error:
            raise GatesError(
                "no TOML parser available: tomllib is 3.11+ and tomli is not installed. "
                f"Cannot validate {path}."
            ) from error
    try:
        with path.open("rb") as handle:
            return _toml.load(handle)
    except FileNotFoundError as error:
        raise GatesError(f"{path} does not exist") from error
    except Exception as error:  # tomllib.TOMLDecodeError, and anything it wraps
        raise GatesError(f"{path} is not valid TOML: {error}") from error


# ---------------------------------------------------------------------------
# the workflow scanner
# ---------------------------------------------------------------------------
#: A top-level job key inside a workflow's ``jobs:`` block.
_JOB_RE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")

#: A step's ``name:``. Steps sit at six spaces under ``steps:``; the job's own
#: ``name:`` sits at four and is deliberately not matched.
_STEP_RE = re.compile(r"^      - name: (.+?)\s*$")


def scan_workflow(path: Path) -> Dict[str, List[str]]:
    """Job name -> step names, read structurally from a workflow file.

    **This is a scanner, not a YAML parser, and the difference is stated rather
    than glossed.** It keys off indentation, which is the one property GitHub's
    own schema fixes: jobs are two-space keys under ``jobs:``, step names are
    ``- name:`` at six spaces. A workflow written with four-space indentation
    would read as empty here -- which is why :func:`validate` refuses a workflow
    that scans to zero jobs. A parser that returns nothing makes every rule
    built on it vacuously true, and that is the failure this whole register
    exists to catalogue.

    PyYAML is not a dev dependency of this project and adding one so a validator
    can read four files is a worse trade than a scanner that says what it is.
    """
    jobs: Dict[str, List[str]] = {}
    current: Optional[str] = None
    in_jobs = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("jobs:"):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        if line and not line.startswith(" ") and not line.startswith("#"):
            # Back to column zero: the jobs block has ended.
            in_jobs = False
            continue
        job = _JOB_RE.match(line)
        if job:
            current = job.group(1)
            jobs.setdefault(current, [])
            continue
        step = _STEP_RE.match(line)
        if step and current is not None:
            jobs[current].append(step.group(1))
    return jobs


def scan_workflows(directory: Path = WORKFLOW_DIR) -> Dict[str, Dict[str, List[str]]]:
    """Every workflow file, scanned. Keyed by file name."""
    if not directory.is_dir():
        raise GatesError(f"{directory} does not exist")
    return {path.name: scan_workflow(path) for path in sorted(directory.glob("*.yml"))}


# ---------------------------------------------------------------------------
# the typed objects
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Edit:
    """One reversible change to one file."""

    file: str
    find: Optional[str] = None
    replace: Optional[str] = None
    delete_line_containing: Optional[str] = None
    append: Optional[str] = None
    create: Optional[str] = None
    delete: bool = False

    @property
    def operation(self) -> str:
        if self.find is not None:
            return "replace"
        if self.delete_line_containing is not None:
            return "delete_line"
        if self.append is not None:
            return "append"
        if self.create is not None:
            return "create"
        if self.delete:
            return "delete"
        return "none"


@dataclass(frozen=True)
class Mutation:
    """How a gate's capacity to fail is established, or why it is not."""

    kind: str
    reason: str = ""
    expect: str = "fail"
    artifact: str = ""
    edits: Tuple[Edit, ...] = ()
    verified_locally_on: Optional[_datetime.date] = None
    verified_in_situ_on: Optional[_datetime.date] = None
    verified_in_situ_run: str = ""
    note: str = ""

    @property
    def is_automated(self) -> bool:
        return self.kind == "automated"

    @property
    def has_in_situ_evidence(self) -> bool:
        return self.verified_in_situ_on is not None and bool(self.verified_in_situ_run)


@dataclass(frozen=True)
class Gate:
    """One check that can fail CI."""

    name: str
    environment: str
    step: str
    defect_class: str
    detects: str
    command: str = ""
    blind_to: str = ""
    mutation: Mutation = field(default_factory=lambda: Mutation(kind="none", reason="undeclared"))


@dataclass(frozen=True)
class Environment:
    """Where a gate runs, and what that place does and does not hold."""

    name: str
    workflow: str
    job: str
    runs_on: str = ""
    holds: Tuple[str, ...] = ()
    lacks: Tuple[str, ...] = ()
    note: str = ""
    no_gates_reason: str = ""


@dataclass(frozen=True)
class DefectCoverage:
    """A real, historical defect, and which gates were measured to catch it."""

    id: str
    summary: str
    fixed_in: str
    caught_by: Tuple[str, ...]
    missed_by: Tuple[str, ...]
    not_applicable: Tuple[str, ...] = ()
    measured_on: Optional[_datetime.date] = None
    measured_in: str = ""
    note: str = ""


@dataclass(frozen=True)
class GateManifest:
    """The whole register."""

    path: Path
    stops_at: str
    environments: Dict[str, Environment]
    gates: Dict[str, Gate]
    defects: Tuple[DefectCoverage, ...]

    def gates_in(self, environment: str) -> List[Gate]:
        return [g for g in self.gates.values() if g.environment == environment]

    def automated(self) -> List[Gate]:
        return [g for g in self.gates.values() if g.mutation.is_automated]

    def with_in_situ_evidence(self) -> List[Gate]:
        return [g for g in self.gates.values() if g.mutation.has_in_situ_evidence]


def _as_date(value: Any, where: str) -> Optional[_datetime.date]:
    if value is None:
        return None
    if isinstance(value, _datetime.datetime):
        return value.date()
    if isinstance(value, _datetime.date):
        return value
    raise GatesError(f"{where}: expected a bare TOML date, got {value!r}")


def _as_tuple(value: Any, where: str) -> Tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise GatesError(f"{where}: expected a list of strings, got {value!r}")
    return tuple(value)


def _edit(raw: Mapping[str, Any], where: str) -> Edit:
    unknown = sorted(set(raw) - set(EDIT_FIELDS))
    if unknown:
        raise GatesError(f"{where}: unknown edit key(s) {unknown}; allowed: {list(EDIT_FIELDS)}")
    if "file" not in raw:
        raise GatesError(f"{where}: an edit must name a file")
    edit = Edit(
        file=str(raw["file"]),
        find=raw.get("find"),
        replace=raw.get("replace"),
        delete_line_containing=raw.get("delete_line_containing"),
        append=raw.get("append"),
        create=raw.get("create"),
        delete=bool(raw.get("delete", False)),
    )
    declared = sum(
        1
        for present in (
            edit.find is not None,
            edit.delete_line_containing is not None,
            edit.append is not None,
            edit.create is not None,
            edit.delete,
        )
        if present
    )
    if declared != 1:
        raise GatesError(
            f"{where}: an edit declares exactly one operation, this one declares {declared}. "
            "Two operations on one file have no defined order and would revert wrongly."
        )
    if (edit.find is None) != (edit.replace is None):
        raise GatesError(f"{where}: `find` and `replace` travel together")
    return edit


def _mutation(raw: Mapping[str, Any], where: str) -> Mutation:
    unknown = sorted(set(raw) - set(MUTATION_FIELDS))
    if unknown:
        raise GatesError(
            f"{where}: unknown mutation key(s) {unknown}; allowed: {list(MUTATION_FIELDS)}"
        )
    kind = raw.get("kind")
    if kind not in MUTATION_KINDS:
        raise GatesError(f"{where}: kind {kind!r} is not one of {list(MUTATION_KINDS)}")
    edits = raw.get("edits") or []
    if not isinstance(edits, list):
        raise GatesError(f"{where}: `edits` must be a list of tables")
    return Mutation(
        kind=str(kind),
        reason=str(raw.get("reason", "")),
        expect=str(raw.get("expect", "fail")),
        artifact=str(raw.get("artifact", "")),
        edits=tuple(_edit(item, f"{where}.edits[{n}]") for n, item in enumerate(edits)),
        verified_locally_on=_as_date(raw.get("verified_locally_on"), where),
        verified_in_situ_on=_as_date(raw.get("verified_in_situ_on"), where),
        verified_in_situ_run=str(raw.get("verified_in_situ_run", "")),
        note=str(raw.get("note", "")),
    )


def load(path: Path = GATES_PATH) -> GateManifest:
    """Parse the register into typed objects. Structural errors raise here."""
    raw = _load_toml(path)

    meta = raw.get("manifest")
    if not isinstance(meta, dict):
        raise GatesError(f"{path}: a [manifest] table is required")
    stops_at = str(meta.get("stops_at", "")).strip()

    environments: Dict[str, Environment] = {}
    for name, body in (raw.get("environments") or {}).items():
        where = f"environments.{name}"
        if not isinstance(body, dict):
            raise GatesError(f"{where}: expected a table")
        unknown = sorted(set(body) - set(ENVIRONMENT_FIELDS))
        if unknown:
            raise GatesError(
                f"{where}: unknown key(s) {unknown}; allowed: {list(ENVIRONMENT_FIELDS)}"
            )
        for required in ("workflow", "job"):
            if not body.get(required):
                raise GatesError(f"{where}: `{required}` is required")
        environments[name] = Environment(
            name=name,
            workflow=str(body["workflow"]),
            job=str(body["job"]),
            runs_on=str(body.get("runs_on", "")),
            holds=_as_tuple(body.get("holds"), where),
            lacks=_as_tuple(body.get("lacks"), where),
            note=str(body.get("note", "")),
            no_gates_reason=str(body.get("no_gates_reason", "")),
        )

    gates: Dict[str, Gate] = {}
    for name, body in (raw.get("gates") or {}).items():
        where = f"gates.{name}"
        if not isinstance(body, dict):
            raise GatesError(f"{where}: expected a table")
        unknown = sorted(set(body) - set(GATE_FIELDS))
        if unknown:
            raise GatesError(f"{where}: unknown key(s) {unknown}; allowed: {list(GATE_FIELDS)}")
        for required in ("environment", "step", "defect_class", "detects"):
            if not body.get(required):
                raise GatesError(f"{where}: `{required}` is required")
        mutation_raw = body.get("mutation")
        if not isinstance(mutation_raw, dict):
            raise GatesError(f"{where}: a [gates.{name}.mutation] table is required")
        gates[name] = Gate(
            name=name,
            environment=str(body["environment"]),
            step=str(body["step"]),
            defect_class=str(body["defect_class"]),
            detects=str(body["detects"]).strip(),
            command=str(body.get("command", "")).strip(),
            blind_to=str(body.get("blind_to", "")).strip(),
            mutation=_mutation(mutation_raw, f"{where}.mutation"),
        )

    defects: List[DefectCoverage] = []
    for n, body in enumerate(raw.get("defect_coverage") or []):
        where = f"defect_coverage[{n}]"
        if not isinstance(body, dict):
            raise GatesError(f"{where}: expected a table")
        unknown = sorted(set(body) - set(DEFECT_FIELDS))
        if unknown:
            raise GatesError(f"{where}: unknown key(s) {unknown}; allowed: {list(DEFECT_FIELDS)}")
        for required in ("id", "summary", "fixed_in"):
            if not body.get(required):
                raise GatesError(f"{where}: `{required}` is required")
        defects.append(
            DefectCoverage(
                id=str(body["id"]),
                summary=str(body["summary"]).strip(),
                fixed_in=str(body["fixed_in"]),
                caught_by=_as_tuple(body.get("caught_by"), where),
                missed_by=_as_tuple(body.get("missed_by"), where),
                not_applicable=_as_tuple(body.get("not_applicable"), where),
                measured_on=_as_date(body.get("measured_on"), where),
                measured_in=str(body.get("measured_in", "")),
                note=str(body.get("note", "")).strip(),
            )
        )

    return GateManifest(
        path=path,
        stops_at=stops_at,
        environments=environments,
        gates=gates,
        defects=tuple(defects),
    )


# ---------------------------------------------------------------------------
# the validator
# ---------------------------------------------------------------------------
def validate(
    manifest: GateManifest,
    workflows: Optional[Mapping[str, Mapping[str, Sequence[str]]]] = None,
) -> List[str]:
    """Every problem with the register, as a list of sentences.

    Returns the empty list when the register is sound. Never raises for a
    content problem -- a validator that stops at the first error makes a reader
    fix one thing per run.
    """
    scanned: Mapping[str, Mapping[str, Sequence[str]]] = (
        scan_workflows() if workflows is None else workflows
    )
    problems: List[str] = []

    if not manifest.stops_at:
        problems.append(
            "[manifest] stops_at is empty. The regress -- a gate, then a mutation proving "
            "the gate can fail, then a check on the mutation -- does not close on its own, "
            "and this field is where the register says where it was stopped and why. "
            "Leaving it blank pretends the regress is closed."
        )

    # -- the workflow files named actually exist, and scan to something -----
    for name, jobs in scanned.items():
        if not jobs:
            problems.append(
                f".github/workflows/{name} scanned to ZERO jobs. Either the file has no jobs "
                "or the scanner in tools/gates.py no longer matches its indentation -- and a "
                "scanner returning nothing makes every rule below vacuously true, which is "
                "the exact defect this register exists to catalogue."
            )

    # -- every environment points at a real job ----------------------------
    for env in manifest.environments.values():
        if env.workflow == "local":
            continue
        found = scanned.get(env.workflow)
        if found is None:
            problems.append(
                f"environments.{env.name}: workflow {env.workflow!r} is not a file in "
                f".github/workflows ({sorted(scanned)})"
            )
            continue
        if env.job not in found:
            problems.append(
                f"environments.{env.name}: job {env.job!r} is not in {env.workflow} "
                f"({sorted(found)})"
            )

    # -- every job in every workflow is accounted for -----------------------
    # THE ANTI-ROT RULE. Everything else here checks the register against
    # itself; this one checks it against the tree.
    declared_jobs = {(e.workflow, e.job) for e in manifest.environments.values()}
    for name, jobs in scanned.items():
        for job in jobs:
            if (name, job) not in declared_jobs:
                problems.append(
                    f"{name}: job {job!r} is not declared in .github/gates.toml. Every job that "
                    "can fail CI carries an [environments.<id>] entry, and one that checks "
                    "nothing carries a `no_gates_reason`. A job nobody registered is a job "
                    "nobody has asked whether it can fail."
                )

    # -- an environment with no gates has to say why ------------------------
    for env in manifest.environments.values():
        if not manifest.gates_in(env.name) and not env.no_gates_reason:
            problems.append(
                f"environments.{env.name}: no gate declares this environment and no "
                "`no_gates_reason` is given. Say what it checks, or say that it checks nothing."
            )
        if manifest.gates_in(env.name) and env.no_gates_reason:
            problems.append(
                f"environments.{env.name}: carries a `no_gates_reason` and "
                f"{len(manifest.gates_in(env.name))} gate(s). One of the two is wrong."
            )

    seen_artifacts: Dict[str, str] = {}
    for gate in manifest.gates.values():
        where = f"gates.{gate.name}"
        home = manifest.environments.get(gate.environment)
        if home is None:
            problems.append(f"{where}: environment {gate.environment!r} is not declared")
            continue
        if gate.defect_class not in DEFECT_CLASSES:
            problems.append(
                f"{where}: defect_class {gate.defect_class!r} is not one of {list(DEFECT_CLASSES)}"
            )
        # -- the step it names must exist in the workflow -------------------
        if home.workflow != "local":
            steps = scanned.get(home.workflow, {}).get(home.job, [])
            if gate.step not in steps:
                problems.append(
                    f"{where}: step {gate.step!r} is not a step of {home.workflow}:{home.job}. "
                    "A gate pointing at a renamed or deleted step is a register entry for "
                    f"nothing. Steps present: {list(steps)}"
                )
        # -- the mutation ---------------------------------------------------
        mutation = gate.mutation
        if mutation.kind == "automated":
            if not gate.command:
                problems.append(
                    f"{where}: mutation kind is `automated` but the gate declares no `command`. "
                    "An automated mutation runs the gate's own command and requires it to "
                    "fail; with no command there is nothing to run but a copy."
                )
            if not mutation.edits:
                problems.append(f"{where}.mutation: kind `automated` requires at least one edit")
            if not mutation.artifact:
                problems.append(
                    f"{where}.mutation: kind `automated` requires an `artifact` path, which is "
                    "where the captured failure is written"
                )
            if mutation.reason:
                problems.append(
                    f"{where}.mutation: `reason` explains a refusal and this mutation is not "
                    "one. Put the explanation in `note`."
                )
        else:
            if not mutation.reason:
                problems.append(
                    f"{where}.mutation: kind {mutation.kind!r} is a refusal, and R14 says a "
                    "refusal ships with a disposition. Say why, in `reason`."
                )
            if mutation.edits:
                problems.append(
                    f"{where}.mutation: kind {mutation.kind!r} declares edits it will never apply"
                )
        if mutation.expect not in ("fail", "pass"):
            problems.append(f"{where}.mutation: expect must be `fail` or `pass`")
        if mutation.artifact:
            other = seen_artifacts.get(mutation.artifact)
            if other:
                problems.append(
                    f"{where}.mutation: artifact path {mutation.artifact!r} is already used by "
                    f"gates.{other}. Two gates writing one file means one failure overwrites "
                    "the other and the register reports both as captured."
                )
            seen_artifacts[mutation.artifact] = gate.name
        if mutation.verified_in_situ_on and not mutation.verified_in_situ_run:
            problems.append(
                f"{where}.mutation: `verified_in_situ_on` with no `verified_in_situ_run`. A date "
                "with no run id is a claim with no evidence, which is operating rule 1 applied "
                "to a gate instead of to a number."
            )
        # -- the edits must be applicable ------------------------------------
        for n, edit in enumerate(mutation.edits):
            target = REPO_ROOT / edit.file
            if edit.operation == "create":
                if target.exists():
                    problems.append(
                        f"{where}.mutation.edits[{n}]: `create` names {edit.file}, which "
                        "already exists, so restoring would delete a tracked file"
                    )
                continue
            if not target.is_file():
                problems.append(
                    f"{where}.mutation.edits[{n}]: {edit.file} does not exist, so this "
                    "mutation cannot be applied and the gate has no demonstration"
                )
                continue
            text = target.read_text(encoding="utf-8")
            if edit.find is not None and text.count(edit.find) != 1:
                problems.append(
                    f"{where}.mutation.edits[{n}]: the anchor occurs {text.count(edit.find)} "
                    f"times in {edit.file}; an anchor must be unique or the mutation is not "
                    "the one described"
                )
            if edit.delete_line_containing is not None:
                needle = edit.delete_line_containing
                hits = sum(1 for line in text.splitlines() if needle in line)
                if hits != 1:
                    problems.append(
                        f"{where}.mutation.edits[{n}]: {hits} line(s) of {edit.file} contain "
                        f"{edit.delete_line_containing!r}; exactly one is required"
                    )

    # -- the historical defect record --------------------------------------
    for n, defect in enumerate(manifest.defects):
        where = f"defect_coverage[{n}] ({defect.id})"
        if not _COMMIT_RE.match(defect.fixed_in):
            problems.append(f"{where}: fixed_in {defect.fixed_in!r} is not a commit name")
        classified = set(defect.caught_by) | set(defect.missed_by) | set(defect.not_applicable)
        for gate_name in classified:
            if gate_name not in manifest.gates:
                problems.append(f"{where}: names gate {gate_name!r}, which is not declared")
        overlap = set(defect.caught_by) & set(defect.missed_by)
        if overlap:
            problems.append(f"{where}: {sorted(overlap)} is both caught and missed")
        if not defect.caught_by and not defect.missed_by:
            problems.append(
                f"{where}: names no gate at all. A defect nothing was measured against is a "
                "story, and the point of this table is that coverage is counted rather than "
                "asserted."
            )
        if defect.measured_on is None:
            problems.append(f"{where}: `measured_on` is required -- a coverage claim has a date")

    return problems


def assert_environment(env: Environment, root: Path = REPO_ROOT) -> List[str]:
    """Check that this machine really is the environment ``env`` describes.

    ``holds`` and ``lacks`` are repo-relative path globs, not prose, and this is
    what makes them worth writing down. Every rule in this register about what a
    gate can detect rests on an unstated premise about where it runs -- and
    D-058 is three defects that all came from that premise being wrong: the
    developer machine had ``data/``, had ``tools/``, and resolved an older
    ``click``.

    The pattern is not new here. ``ci.yml``'s ``air-gap`` job already opens with
    *"Prove the network namespace really has no route"* and refuses to let a
    later step be a tautology. That job is the only one in this repository that
    was built this way. This function is that step, generalised, so any
    environment can be checked instead of one.
    """
    problems: List[str] = []
    for pattern in env.holds:
        if not list(root.glob(pattern)):
            problems.append(
                f"environments.{env.name} declares it HOLDS {pattern!r} and nothing matches it "
                "here. Either this is not that environment, or the register is wrong about it."
            )
    for pattern in env.lacks:
        hits = sorted(str(p.relative_to(root)) for p in root.glob(pattern))
        if hits:
            problems.append(
                f"environments.{env.name} declares it LACKS {pattern!r} and {len(hits)} path(s) "
                f"match: {hits[:5]}. Every gate that depends on that absence is now a "
                "tautology here, which is exactly the state R11 exists to make visible."
            )
    return problems


def stale_notes(manifest: GateManifest, today: Optional[_datetime.date] = None) -> List[str]:
    """Verifications old enough to be worth re-running. Notes, never failures."""
    today = today or _datetime.date.today()
    notes: List[str] = []
    for gate in manifest.gates.values():
        for label, when in (
            ("in situ", gate.mutation.verified_in_situ_on),
            ("locally", gate.mutation.verified_locally_on),
        ):
            if when and (today - when).days > STALE_AFTER_DAYS:
                notes.append(
                    f"gates.{gate.name}: last verified {label} on {when}, "
                    f"{(today - when).days} days ago"
                )
    return notes


# ---------------------------------------------------------------------------
# the mutation runner
# ---------------------------------------------------------------------------
@dataclass
class MutationOutcome:
    """What happened when one gate was mutated."""

    gate: str
    kind: str
    applied: bool
    mutated_rc: Optional[int] = None
    restored_rc: Optional[int] = None
    verdict: str = "skipped"
    detail: str = ""
    mutated_output: str = ""
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return self.verdict in ("demonstrated", "skipped")


def _apply(edit: Edit, root: Path) -> Tuple[Path, Optional[bytes]]:
    """Apply one edit; return the file and its previous bytes (``None`` if new)."""
    target = root / edit.file
    before: Optional[bytes] = target.read_bytes() if target.is_file() else None
    if edit.operation == "create":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(edit.create or "", encoding="utf-8")
    elif edit.operation == "delete":
        target.unlink()
    elif edit.operation == "append":
        with target.open("a", encoding="utf-8") as handle:
            handle.write(edit.append or "")
    elif edit.operation == "replace":
        text = target.read_text(encoding="utf-8")
        assert edit.find is not None and edit.replace is not None
        if text.count(edit.find) != 1:
            raise GatesError(
                f"{edit.file}: anchor occurs {text.count(edit.find)} times, expected exactly one"
            )
        target.write_text(text.replace(edit.find, edit.replace, 1), encoding="utf-8")
    elif edit.operation == "delete_line":
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        needle = edit.delete_line_containing or ""
        kept = [ln for ln in lines if needle not in ln]
        if len(kept) == len(lines):
            raise GatesError(f"{edit.file}: no line contains {edit.delete_line_containing!r}")
        target.write_text("".join(kept), encoding="utf-8")
    else:  # pragma: no cover - _edit() refuses this
        raise GatesError(f"{edit.file}: no operation declared")
    return target, before


def _restore(saved: Iterable[Tuple[Path, Optional[bytes]]]) -> None:
    for target, before in reversed(list(saved)):
        if before is None:
            if target.exists():
                target.unlink()
        else:
            target.write_bytes(before)


def run_gate_command(command: str, root: Path = REPO_ROOT) -> Tuple[int, str]:
    """Run a gate's own command and return ``(returncode, combined output)``.

    ``shlex.split`` with ``posix=False`` on Windows keeps drive letters intact.
    The command is never handed to a shell: a register entry is data, and data
    that reaches a shell is an injection surface in a file several people edit.
    """
    argv = shlex.split(command, posix=(sys.platform != "win32"))
    argv = [part.strip('"') for part in argv]
    if argv and argv[0] == "python":
        argv[0] = sys.executable
    done = subprocess.run(argv, cwd=str(root), capture_output=True, text=True, errors="replace")
    return done.returncode, (done.stdout + done.stderr)


def mutate(
    gate: Gate,
    root: Path = REPO_ROOT,
    artifacts: Optional[Path] = None,
) -> MutationOutcome:
    """Apply ``gate``'s declared mutation, require the gate to fail, restore.

    The restore is not politeness. The second half of the demonstration is that
    the same command passes again on the unmutated tree: without it a gate that
    fails for an unrelated reason -- a broken checkout, a missing dependency --
    reads as a successful demonstration, which is a false green wearing a red
    coat.
    """
    import time

    outcome = MutationOutcome(gate=gate.name, kind=gate.mutation.kind, applied=False)
    if not gate.mutation.is_automated:
        outcome.detail = gate.mutation.reason
        return outcome
    started = time.time()
    saved: List[Tuple[Path, Optional[bytes]]] = []
    try:
        for edit in gate.mutation.edits:
            saved.append(_apply(edit, root))
        outcome.applied = True
        rc, output = run_gate_command(gate.command, root)
        outcome.mutated_rc = rc
        outcome.mutated_output = output[-8000:]
    finally:
        _restore(saved)
    restored_rc, _ = run_gate_command(gate.command, root)
    outcome.restored_rc = restored_rc
    outcome.seconds = round(time.time() - started, 1)

    wanted_failure = gate.mutation.expect == "fail"
    failed = (outcome.mutated_rc or 0) != 0
    if failed != wanted_failure:
        outcome.verdict = "INERT"
        outcome.detail = (
            f"the mutation was applied and the gate exited {outcome.mutated_rc}. "
            f"Expected {gate.mutation.expect}. This gate cannot fail here on this defect."
        )
    elif restored_rc != 0:
        outcome.verdict = "UNRESTORED"
        outcome.detail = (
            f"the gate still exits {restored_rc} after the tree was put back, so the failure "
            "above is not attributable to the mutation."
        )
    else:
        outcome.verdict = "demonstrated"
        outcome.detail = f"mutated rc={outcome.mutated_rc}, restored rc={restored_rc}"

    if artifacts is not None and gate.mutation.artifact:
        path = artifacts / gate.mutation.artifact
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = _datetime.datetime.now(_datetime.timezone.utc).isoformat(timespec="seconds")
        path.write_text(
            f"gate:      {gate.name}\n"
            f"command:   {gate.command}\n"
            f"expect:    {gate.mutation.expect}\n"
            f"verdict:   {outcome.verdict}\n"
            f"mutated:   rc={outcome.mutated_rc}\n"
            f"restored:  rc={outcome.restored_rc}\n"
            f"captured:  {stamp}\n"
            f"platform:  {sys.platform} python {sys.version.split()[0]}\n"
            f"edits:     {[e.file + ':' + e.operation for e in gate.mutation.edits]}\n"
            "--- output of the gate under mutation " + "-" * 40 + "\n" + outcome.mutated_output,
            encoding="utf-8",
        )
    return outcome


# ---------------------------------------------------------------------------
# the script
# ---------------------------------------------------------------------------
def _summary_lines(manifest: GateManifest) -> List[str]:
    automated = manifest.automated()
    in_situ = manifest.with_in_situ_evidence()
    by_kind: Dict[str, int] = {}
    for gate in manifest.gates.values():
        by_kind[gate.mutation.kind] = by_kind.get(gate.mutation.kind, 0) + 1
    kinds = ", ".join(f"{kind} {count}" for kind, count in sorted(by_kind.items()))
    return [
        f"gate manifest: {len(manifest.gates)} gate(s) across {len(manifest.environments)} "
        f"environment(s) in {len(scan_workflows())} workflow file(s)",
        f"mutation kind: {kinds}",
        f"demonstrable by this harness: {len(automated)} of {len(manifest.gates)}",
        f"CARRYING IN-SITU EVIDENCE:   {len(in_situ)} of {len(manifest.gates)}"
        + ("" if in_situ else "   <- R11 is not satisfied for any gate here"),
    ]


def _cmd_check(manifest: GateManifest) -> int:
    problems = validate(manifest)
    for note in stale_notes(manifest):
        print(f"note: {note}")
    if problems:
        print(f"{manifest.path}: {len(problems)} problem(s)")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    for line in _summary_lines(manifest):
        print(line)
    print(
        "gate manifest OK: every job in every workflow is registered, every gate names a step "
        "that exists, and every gate either carries a mutation or a reason it has none"
    )
    return 0


def _cmd_list(manifest: GateManifest) -> int:
    for env in sorted(manifest.environments.values(), key=lambda e: (e.workflow, e.job)):
        gates = manifest.gates_in(env.name)
        print(f"\n{env.workflow}:{env.job}  [{env.runs_on or 'n/a'}]")
        if env.lacks:
            print(f"  lacks: {', '.join(env.lacks)}")
        if not gates:
            print(f"  (no gates) {env.no_gates_reason}")
        for gate in sorted(gates, key=lambda g: g.name):
            mark = "in-situ" if gate.mutation.has_in_situ_evidence else gate.mutation.kind
            print(f"  {gate.name:<38} {gate.defect_class:<20} {mark}")
    print()
    for line in _summary_lines(manifest):
        print(line)
    return 0


def _cmd_json(manifest: GateManifest) -> int:
    payload = {
        "stops_at": manifest.stops_at,
        "environments": {
            name: {
                "workflow": env.workflow,
                "job": env.job,
                "runs_on": env.runs_on,
                "holds": list(env.holds),
                "lacks": list(env.lacks),
                "no_gates_reason": env.no_gates_reason,
            }
            for name, env in manifest.environments.items()
        },
        "gates": {
            name: {
                "environment": gate.environment,
                "step": gate.step,
                "command": gate.command,
                "defect_class": gate.defect_class,
                "mutation_kind": gate.mutation.kind,
                "artifact": gate.mutation.artifact,
                "verified_locally_on": str(gate.mutation.verified_locally_on or ""),
                "verified_in_situ_on": str(gate.mutation.verified_in_situ_on or ""),
                "verified_in_situ_run": gate.mutation.verified_in_situ_run,
            }
            for name, gate in manifest.gates.items()
        },
        "defect_coverage": [
            {
                "id": d.id,
                "summary": d.summary,
                "fixed_in": d.fixed_in,
                "caught_by": list(d.caught_by),
                "missed_by": list(d.missed_by),
                "not_applicable": list(d.not_applicable),
                "measured_on": str(d.measured_on or ""),
            }
            for d in manifest.defects
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_mutate(manifest: GateManifest, names: Sequence[str], artifacts: Optional[Path]) -> int:
    outcomes = [mutate(manifest.gates[name], artifacts=artifacts) for name in names]
    failed = 0
    for outcome in outcomes:
        if outcome.verdict == "skipped":
            print(f"{outcome.gate:<38} SKIPPED   ({outcome.kind}) {outcome.detail}")
            continue
        print(f"{outcome.gate:<38} {outcome.verdict.upper():<13} {outcome.detail}")
        if not outcome.ok:
            failed += 1
            print("    --- gate output under mutation, last 20 lines ---")
            for line in outcome.mutated_output.splitlines()[-20:]:
                print(f"    {line}")
    demonstrated = sum(1 for o in outcomes if o.verdict == "demonstrated")
    skipped = sum(1 for o in outcomes if o.verdict == "skipped")
    print(f"\n{demonstrated} demonstrated, {failed} INERT or UNRESTORED, {skipped} not automated")
    if failed:
        print(
            "\nAn INERT verdict is the finding, not an error in this harness: the gate ran "
            "against a tree carrying the defect it exists to catch and did not fail."
        )
    return 1 if failed else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", type=Path, default=GATES_PATH)
    parser.add_argument("--check", action="store_true", help="validate the register (the CI gate)")
    parser.add_argument("--list", action="store_true", help="print the register as a table")
    parser.add_argument("--json", action="store_true", help="print the register as JSON")
    parser.add_argument("--mutate", action="append", default=[], metavar="GATE")
    parser.add_argument("--mutate-environment", metavar="ENV")
    parser.add_argument(
        "--assert-environment",
        metavar="ENV",
        help="check that this machine holds and lacks what the register says it does",
    )
    parser.add_argument("--artifacts", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        manifest = load(args.path)
    except GatesError as error:
        print(f"gate manifest: {error}", file=sys.stderr)
        return 1

    if args.assert_environment:
        env = manifest.environments.get(args.assert_environment)
        if env is None:
            print(f"no such environment: {args.assert_environment!r}", file=sys.stderr)
            return 1
        problems = assert_environment(env)
        for problem in problems:
            print(f"  - {problem}")
        if problems:
            print(f"environments.{env.name}: {len(problems)} premise(s) do not hold here")
            return 1
        print(
            f"environments.{env.name}: holds {len(env.holds)} declared path(s), "
            f"lacks {len(env.lacks)} declared path(s) -- this is that environment"
        )
        return 0

    if args.mutate or args.mutate_environment:
        names = list(args.mutate)
        if args.mutate_environment:
            names += [
                g.name
                for g in sorted(manifest.gates_in(args.mutate_environment), key=lambda g: g.name)
            ]
        unknown = [n for n in names if n not in manifest.gates]
        if unknown:
            print(f"no such gate(s): {unknown}", file=sys.stderr)
            return 1
        if not names:
            print(f"no gate declares environment {args.mutate_environment!r}", file=sys.stderr)
            return 1
        return _cmd_mutate(manifest, names, args.artifacts)
    if args.list:
        return _cmd_list(manifest)
    if args.json:
        return _cmd_json(manifest)
    return _cmd_check(manifest)


if __name__ == "__main__":
    raise SystemExit(main())
