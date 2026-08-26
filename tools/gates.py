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

``every gate is ranked by what it costs if it silently stops working``
    A count is not a plan. ``0 of 36`` was printed on every CI run for a phase
    and told nobody which gate to fix first. :func:`cost_ranking_problems`
    requires ``cost_rank`` to be a permutation of ``1..n`` and refuses one that
    inverts its own declared factors -- :data:`BLAST_RADII` and
    :data:`SILENCE_CLASSES` -- so moving a gate up the list costs an argument
    rather than a nudged integer.

``the in-situ debt has a quota, and it is a ceiling rather than a floor``
    :func:`in_situ_problems`, built the way ``MIGRATION_QUOTA`` is built in
    ``tools/check_claims.py``. The quota is on ``gates - in_situ`` and not on
    ``in_situ``, because a floor on the coverage count is satisfied by a round
    that adds five gates and demonstrates none: ``13 of 36`` becomes
    ``13 of 41``, the floor holds, and the register reports health while going
    backwards. A ceiling on the debt cannot be satisfied that way.

What this file does NOT do
--------------------------
It does not run the gates. It runs *one* gate under *one* mutation, on demand,
and asserts the outcome. The gates themselves are run by
``.github/workflows/ci.yml`` and nothing here changes that -- a register that
also executed the things it registers would be a second implementation of CI.

Usage::

    python tools/gates.py --check                 # the CI gate
    python tools/gates.py --list                  # the register as a table
    python tools/gates.py --ranking               # cost if inert, worst first
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

#: HOW FAR THE DAMAGE TRAVELS if this gate silently stops working. Ordered,
#: worst first, and the order is load-bearing: :func:`cost_ranking_problems`
#: refuses a ``cost_rank`` ordering that inverts it.
#:
#: ``published_numbers``      the defect reaches a figure or a corpus
#:                            declaration a reader acts on. For a governance
#:                            instrument this is the top tier by construction:
#:                            the numbers ARE the product.
#: ``installed_behaviour``    the defect reaches what the installed package
#:                            does for somebody who imported it.
#: ``release_provenance``     the defect reaches the release's identity --
#:                            version, checksums, SBOM, metadata, size.
#: ``distribution_contents``  the defect reaches which files the distribution
#:                            carries. A reader holding an sdist finds a
#:                            broken reference or a suite that cannot run.
#: ``evidence_apparatus``     only this repository's own evidence apparatus is
#:                            wrong: a register that has stopped describing CI,
#:                            or a positive control that has stopped
#:                            controlling. Nothing user-facing moves TODAY.
#: ``repository``             the tree acquires a defect that stays in the tree.
BLAST_RADII = (
    "published_numbers",
    "installed_behaviour",
    "release_provenance",
    "distribution_contents",
    "evidence_apparatus",
    "repository",
)

#: HOW THE FAILURE ANNOUNCES ITSELF **to this project** if the gate is inert.
#: Ordered, worst first. This is the D-058 axis: all four defects of that record
#: were silent here and loud somewhere else, which is why a silent gate costs
#: more than a loud one at the same blast radius.
SILENCE_CLASSES = ("silent", "delayed", "loud")

#: Whether any OTHER registered gate covers the same defect.
#:
#: **Declared, printed, and deliberately NOT part of the ordering key.** A
#: lexicographic third factor produced orderings this register would not defend
#: -- it ranked a resource-consistency check above the whole test suite, purely
#: because the suite is partly duplicated by ``installed-suite``. A factor that
#: decides ranks nobody will defend is worse than a factor that informs them.
#: Where a value here says ``partial``, ``[[defect_coverage]]`` is the evidence
#: unless the gate's ``cost_if_inert`` names another.
REDUNDANCY_CLASSES = ("sole", "partial", "covered")

#: Every key a ``[gates.<id>]`` table may carry.
GATE_FIELDS = (
    "environment",
    "step",
    "command",
    "defect_class",
    "detects",
    "blind_to",
    "cost_rank",
    "blast_radius",
    "silence",
    "redundancy",
    "cost_if_inert",
    "mutation",
)

#: Every key a ``[gates.<id>.mutation]`` table may carry.
MUTATION_FIELDS = (
    "kind",
    "reason",
    "expect",
    "artifact",
    "edits",
    "setup",
    "expect_failure_matching",
    "verified_locally_on",
    "verified_in_situ_on",
    "verified_in_situ_run",
    "verified_in_situ_commit",
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

#: How far the in-situ debt must fall in a round that touches this register.
#:
#: **Built the way ``tools/check_claims.py``'s ``MIGRATION_QUOTA`` is built, and
#: for the same reason: an honest count with no rate attached is a backlog with
#: better manners.** ``--check`` printed ``0 of 36`` on every CI run for a whole
#: phase and nothing about that line obliged anybody to move it.
#:
#: The quota is stated on the DEBT -- ``uncovered = gates - in_situ`` -- and not
#: on the coverage count, and that choice is the whole design. A floor on the
#: coverage count is satisfied by a round that adds five gates and demonstrates
#: none: the count holds, the ratio falls, and the register reports health while
#: going backwards. A ceiling on the debt cannot be satisfied that way, because
#: a gate added without evidence raises the debt by one.
IN_SITU_QUOTA = 3

#: Every gate at or above this rank in the cost-if-inert ordering must carry
#: in-situ evidence. Three, because ranks 1-3 are the three highest-cost gates
#: that this harness can mutate at all: rank 4 is ``airgap_suite_under_guard``,
#: whose environment is a privileged network namespace nothing here can build.
#: Raising this is what closing the next rank down looks like; it may not fall.
TOP_RANKS_REQUIRING_IN_SITU = 3


@dataclass(frozen=True)
class InSituRound:
    """One round's standing on in-situ evidence, as the round left it.

    Args:
        label: An id. Duplicates are refused, the way ``LedgerRound`` labels are.
        gates: How many gates the register held when the round ended.
        in_situ: How many of them carried in-situ evidence.
        run: The CI run the evidence was taken from. Required whenever
            ``in_situ`` rises: a count with no run id is a claim with no
            evidence, which is operating rule 1 applied to a gate.
        commit: The commit that run was taken on, so a reader can check that
            the gate demonstrated there is the gate shipping here.
        waiver: Why this round is allowed to miss :data:`IN_SITU_QUOTA`.
        withdrawn_gates: Gates whose in-situ evidence this round RETIRED, by
            name. A count that can only rise is not a measurement, and until
            this field existed the debt rule made retirement impossible: the
            debt-may-not-rise rule fired first and was declared not waivable, so
            "we found our evidence is weaker than we thought" could not be
            said. Every name here is checked against the live register.
        owed_forward: Gates this round ADDED, or un-refused, that carry no
            evidence and whose demonstration the next CI run is expected to
            take. ``docs/GATES.md`` already described a waiver for exactly this
            case -- *"a round that adds an `automated` gate it could not run in
            CI in the same commit"* -- and that waiver was UNREACHABLE, because
            adding such a gate raises the debt and the rise was refused before
            any waiver was consulted. This is the attribution that makes it
            reachable, and :func:`in_situ_problems` puts a due date on it.
        note: What moved, and what it cost.
    """

    label: str
    gates: int
    in_situ: int
    run: str = ""
    commit: str = ""
    waiver: str = ""
    withdrawn_gates: Tuple[str, ...] = ()
    owed_forward: int = 0
    note: str = ""

    @property
    def uncovered(self) -> int:
        """Gates carrying no in-situ evidence. The quantity the quota is on."""
        return self.gates - self.in_situ

    @property
    def attributed(self) -> int:
        """How much debt rise this round has an accounting for."""
        return len(self.withdrawn_gates) + self.owed_forward


#: Where the in-situ count has been, newest **last**.
#:
#: Checked rather than decorative (:func:`in_situ_problems`): the last row must
#: equal the live register, the debt may never rise, and a round that pays less
#: than :data:`IN_SITU_QUOTA` must write down why. The coupling to the live
#: register is what makes this a fact about the tree rather than a note about
#: it -- adding a gate to ``.github/gates.toml`` reddens ``--check`` until a row
#: is appended, and the appended row cannot be a healthy one unless the evidence
#: came with the gate.
IN_SITU_TRAJECTORY: Tuple[InSituRound, ...] = (
    InSituRound(
        label="M2-P3 X5 (register opened)",
        gates=36,
        in_situ=0,
        note=(
            "the count the day the register was written. The workstream that built it could "
            "not run GitHub Actions, so every mutation it recorded was taken on a developer "
            "machine -- precisely the evidence R11 says does not count."
        ),
    ),
    InSituRound(
        label="M2-P4 (the first harvest)",
        gates=36,
        in_situ=13,
        run="32808357572",
        commit="3173126",
        note=(
            "gate-mutation.yml HAD run -- once, on 2026-08-25, green, with all five artifact "
            "bundles uploaded -- and nothing in this repository had harvested it. All 13 "
            "automated gates came back `demonstrated` on ubuntu-latest/CPython 3.12. The 23 "
            "that remain are the 8 inline, 13 manual and 2 control refusals, none of which "
            "this harness can mutate; the next payment is the heredoc extraction that would "
            "close three of the eight at once."
        ),
    ),
    InSituRound(
        label="M3-PA (the heredoc extraction)",
        gates=36,
        in_situ=12,
        withdrawn_gates=("suite",),
        owed_forward=4,
        waiver=(
            "THE DEBT ROSE BY ONE AND THE COUNT FELL BY ONE, AND BOTH ARE THE POINT OF THE "
            "ROUND. Three inline gates -- schema_copies_match, tier_zero_purity, "
            "import_ceiling -- were extracted into tools/ scripts and are now `automated`, so "
            "the set this harness can mutate went from 13 to 16. None of the three can carry "
            "in-situ evidence in the commit that creates them, because the CI run that would "
            "take it happens after the push; that is the case docs/GATES.md already described "
            "a waiver for, and the waiver was UNREACHABLE until this round because the "
            "debt-may-not-rise rule fired first and was declared not waivable. "
            "gates.suite's evidence is WITHDRAWN: its recorded verdict was measured to be "
            "reachable with the declared defect uncaught, through the probe's own side effect "
            "on the register anchor, so the harness could not have returned INERT for any "
            "tree. Four gates are owed forward and gate-mutation.yml triggers on every path "
            "this commit touches, so the run that owes them is the one that lands it."
        ),
        note=(
            "Extraction, not harvest. `demonstrable by this harness` 13 -> 16, `inline` 8 -> "
            "5, in-situ 13 -> 12, debt 23 -> 24. The five inline gates that remain are NOT "
            "another afternoon: airgap_public_api_probe is a 150-line probe inside a network "
            "namespace, and wheel_budget, wheel_resources and installed_wheel_smoke all need "
            "a built wheel that exists only mid-job, so extracting them buys a script and no "
            "demonstration. import_ceiling is the measured refutation of this register's own "
            "costing: extraction alone left it inert in its own environment, because that job "
            "installs non-editably, and it needed a new `setup` field to be demonstrable at "
            "all."
        ),
    ),
)


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
    setup: str = ""
    expect_failure_matching: str = ""
    verified_locally_on: Optional[_datetime.date] = None
    verified_in_situ_on: Optional[_datetime.date] = None
    verified_in_situ_run: str = ""
    verified_in_situ_commit: str = ""
    note: str = ""

    @property
    def is_automated(self) -> bool:
        return self.kind == "automated"

    @property
    def has_in_situ_evidence(self) -> bool:
        return (
            self.verified_in_situ_on is not None
            and bool(self.verified_in_situ_run)
            and bool(self.verified_in_situ_commit)
        )


@dataclass(frozen=True)
class Gate:
    """One check that can fail CI."""

    name: str
    environment: str
    step: str
    defect_class: str
    detects: str
    cost_rank: int = 0
    blast_radius: str = ""
    silence: str = ""
    redundancy: str = ""
    cost_if_inert: str = ""
    command: str = ""
    blind_to: str = ""
    mutation: Mutation = field(default_factory=lambda: Mutation(kind="none", reason="undeclared"))

    @property
    def cost_key(self) -> Tuple[int, int]:
        """The ordering key ``cost_rank`` must not invert.

        Two factors, not three. :data:`REDUNDANCY_CLASSES` is declared and
        printed and stays out of this tuple; the reason is on that constant.
        """
        blast = BLAST_RADII.index(self.blast_radius) if self.blast_radius in BLAST_RADII else -1
        quiet = SILENCE_CLASSES.index(self.silence) if self.silence in SILENCE_CLASSES else -1
        return (blast, quiet)


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

    def by_cost(self) -> List[Gate]:
        """Every gate, most expensive first if it silently stopped working."""
        return sorted(self.gates.values(), key=lambda g: (g.cost_rank, g.name))

    def demonstrable_without_evidence(self) -> List[Gate]:
        """Gates this harness CAN mutate that have never been mutated in situ.

        The one number that separates "we cannot demonstrate it" from "we have
        not". Everything here is a gate whose own command a runner could invoke
        today, so a non-empty list is a debt rather than a limit.
        """
        return sorted(
            (g for g in self.automated() if not g.mutation.has_in_situ_evidence),
            key=lambda g: g.cost_rank,
        )


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
        setup=str(raw.get("setup", "")).strip(),
        expect_failure_matching=str(raw.get("expect_failure_matching", "")).strip(),
        verified_locally_on=_as_date(raw.get("verified_locally_on"), where),
        verified_in_situ_on=_as_date(raw.get("verified_in_situ_on"), where),
        verified_in_situ_run=str(raw.get("verified_in_situ_run", "")),
        verified_in_situ_commit=str(raw.get("verified_in_situ_commit", "")),
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
        rank = body.get("cost_rank", 0)
        if not isinstance(rank, int) or isinstance(rank, bool):
            raise GatesError(f"{where}: `cost_rank` must be an integer, got {rank!r}")
        gates[name] = Gate(
            name=name,
            environment=str(body["environment"]),
            step=str(body["step"]),
            defect_class=str(body["defect_class"]),
            detects=str(body["detects"]).strip(),
            cost_rank=rank,
            blast_radius=str(body.get("blast_radius", "")),
            silence=str(body.get("silence", "")),
            redundancy=str(body.get("redundancy", "")),
            cost_if_inert=str(body.get("cost_if_inert", "")).strip(),
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
        # -- the cost-if-inert factors ---------------------------------------
        for attribute, allowed in (
            ("blast_radius", BLAST_RADII),
            ("silence", SILENCE_CLASSES),
            ("redundancy", REDUNDANCY_CLASSES),
        ):
            value = getattr(gate, attribute)
            if value not in allowed:
                problems.append(
                    f"{where}: {attribute} {value!r} is not one of {list(allowed)}. "
                    "Every gate declares what it costs if it silently stops working, "
                    "because a register that ranks nothing tells a reader with one "
                    "afternoon which gate to fix by leaving them to guess."
                )
        if not gate.cost_if_inert:
            problems.append(
                f"{where}: `cost_if_inert` is required. Say what breaks and how far it "
                "travels if this gate goes inert -- the three factors above are the "
                "ordering, and this is the sentence that has to be true for them."
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
            # -- THE VERDICT MUST REST ON A NAMED LINE, NOT ON A RETURN CODE --
            #
            # ``gates.suite`` is why this rule exists and it is worth reading in
            # full. Its probe edits ``tests/test_splits_manifest.py``, which is
            # also the file its own register entry anchors on -- so while the
            # mutation is applied, ``tests/test_gate_manifest.py`` correctly
            # reports that the anchor no longer matches, and the suite goes red
            # on THAT whether or not the D-058 defect is caught. Measured on
            # 2026-08-25: with the mutation applied and ``data/`` present, the
            # only failing test is the anchor check. ``rc != 0`` was therefore
            # satisfiable in BOTH environments by the probe's own side effect,
            # which made this gate's automated verdict carry no information at
            # all -- a check that could not fail, inside the harness built to
            # catalogue checks that cannot fail.
            #
            # ``docs/GATES.md`` already said "take the evidence from the line,
            # not from the verdict". Nothing enforced it. This does.
            if mutation.expect == "fail" and not mutation.expect_failure_matching:
                problems.append(
                    f'{where}.mutation: kind `automated` with `expect = "fail"` requires '
                    "`expect_failure_matching`, a substring the gate's own output must "
                    "contain when the mutation is applied. A non-zero exit is not on its own "
                    "attributable: a broken checkout, a missing dependency or the probe's own "
                    "side effect all produce one and all read as a successful demonstration."
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
            for field_name in ("setup", "expect_failure_matching"):
                if getattr(mutation, field_name):
                    problems.append(
                        f"{where}.mutation: kind {mutation.kind!r} declares `{field_name}`, "
                        "which only a mutation this harness runs can use."
                    )
        if mutation.expect == "pass" and mutation.expect_failure_matching:
            problems.append(
                f'{where}.mutation: `expect_failure_matching` with `expect = "pass"`. '
                "A mutation that must NOT be detected has no failure output to match."
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
        if mutation.verified_in_situ_on and not mutation.verified_in_situ_commit:
            problems.append(
                f"{where}.mutation: `verified_in_situ_on` with no `verified_in_situ_commit`. A "
                "run id says a demonstration happened; the commit says WHICH gate was "
                "demonstrated. Without it nobody can check that the gate that failed there is "
                "the gate shipping here."
            )
        if mutation.verified_in_situ_commit and not _COMMIT_RE.match(
            mutation.verified_in_situ_commit
        ):
            problems.append(
                f"{where}.mutation: verified_in_situ_commit "
                f"{mutation.verified_in_situ_commit!r} is not a commit name"
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

    problems.extend(cost_ranking_problems(manifest))
    # THE QUOTA IS A FACT ABOUT *THIS* REGISTER, so it is checked only when this
    # register is what was loaded. Same asymmetry, and the same reasoning, as
    # ``Project.value_baseline`` in ``tools/check_claims.py``: applying a
    # trajectory recorded for these gates to a manifest somebody handed the tool
    # would be the validator asserting a property of the checkout it lives in
    # against a checkout it was given. :func:`in_situ_problems` takes an explicit
    # trajectory so a test can drive every rule of it against a synthetic pair.
    if manifest.path == GATES_PATH:
        problems.extend(in_situ_problems(manifest))
    return problems


def cost_ranking_problems(manifest: GateManifest) -> List[str]:
    """Where the declared cost ordering disagrees with its own factors.

    ``cost_rank`` is a total order over every gate: rank ``1`` is the gate whose
    silent failure costs this project the most. It is not free text and it is
    not a mood. Two rules hold it down:

    * **it is a permutation of ``1..n``** -- no gaps, no ties, nothing
      unranked, so "which gate do I fix first" has exactly one answer; and
    * **it may not invert its own factors.** Sorting by rank must give a
      non-decreasing sequence of :attr:`Gate.cost_key`. Moving a gate up the
      list therefore costs an argument about *blast radius* or *silence*, in a
      field, rather than a nudged integer -- which is the difference between a
      ranking and an opinion with numbers on it.

    Ties on the key are left free: within one bucket the order is judgement, and
    ``cost_if_inert`` is where that judgement is written down.
    """
    problems: List[str] = []
    gates = list(manifest.gates.values())
    if not gates:
        return problems

    ranks = sorted(gate.cost_rank for gate in gates)
    expected = list(range(1, len(gates) + 1))
    if ranks != expected:
        missing = sorted(set(expected) - set(ranks))
        repeated = sorted({rank for rank in ranks if ranks.count(rank) > 1})
        problems.append(
            f"cost_rank is not a permutation of 1..{len(gates)}: "
            f"{len(repeated)} repeated {repeated[:5]}, {len(missing)} missing {missing[:5]}. "
            "Every gate carries exactly one rank and no two share one, or the register "
            "cannot answer the only question a reader with one afternoon has."
        )
        return problems

    ordered = sorted(gates, key=lambda gate: gate.cost_rank)
    for higher, lower in zip(ordered, ordered[1:]):
        if higher.cost_key > lower.cost_key:
            problems.append(
                f"gates.{lower.name} ranks {lower.cost_rank} below gates.{higher.name} at "
                f"{higher.cost_rank}, and its factors are strictly worse: "
                f"({lower.blast_radius}, {lower.silence}) against "
                f"({higher.blast_radius}, {higher.silence}). "
                "A rank may not invert the factors it is derived from -- change a factor "
                "and say why, or leave the rank where the factors put it."
            )
    return problems


def in_situ_problems(
    manifest: GateManifest,
    trajectory: Sequence[InSituRound] = IN_SITU_TRAJECTORY,
    *,
    quota: int = IN_SITU_QUOTA,
    top_ranks: int = TOP_RANKS_REQUIRING_IN_SITU,
) -> List[str]:
    """Where the in-situ evidence quota is not met.

    The quota is on the **debt**, and every rule below follows from that:

    ``the debt may not rise``
        A round that adds a gate without adding evidence raises
        ``gates - in_situ`` by one and cannot satisfy this. That failure mode is
        the reason the quota is not a floor on the coverage count: a floor is
        satisfied by a round that adds five gates and demonstrates none, while
        ``13 of 36`` quietly becomes ``13 of 41``. **Not waivable.**

    ``the last row must equal the live register``
        The coupling. Editing ``.github/gates.toml`` without appending a round
        reddens ``--check`` immediately, so the trajectory is a fact about the
        tree rather than a note beside it. Same rule, same reason, as
        ``LEDGER_TRAJECTORY``'s last-row check. **Not waivable.**

    ``the top of the ranking carries evidence``
        Ranking gates and then demonstrating whichever were easiest is the
        failure this whole exercise is about. **Not waivable.**

    ``a round pays the quota, or writes down why it could not``
        Waivable, and deliberately: the demonstrable set is finite, and once it
        is exhausted the only currency left is extracting an inline gate into a
        script. A rule with no escape gets deleted; one with a named escape gets
        argued with.

    ``every automated gate carries evidence``
        Waivable through the same door. A gate whose own command a runner can
        invoke and that has never been mutated on a runner is a debt, not a
        limit -- but the commit that ADDS such a gate cannot also hold its CI
        run, so the waiver is what lets that commit land.
    """
    problems: List[str] = []
    if not trajectory:
        return [
            "  IN_SITU_TRAJECTORY is empty. The in-situ count may not move without a "
            "recorded round -- that is what stopped `0 of 36` being a line nobody owed anything "
            "against."
        ]

    labels = [entry.label for entry in trajectory]
    for label in sorted({label for label in labels if labels.count(label) > 1}):
        problems.append(f"  IN_SITU_TRAJECTORY has two rounds labelled {label!r}. Labels are ids.")

    for previous, entry in zip(trajectory, trajectory[1:]):
        where = f"  IN_SITU_TRAJECTORY[{entry.label!r}]\n    "
        # NAMING A WITHDRAWAL COMES FIRST, before the arithmetic rules, because
        # "you retired evidence and did not say for which gate" is a more
        # useful sentence than "the debt rose" -- and the debt rule below
        # `continue`s, so anything after it would never be reached in exactly
        # the case this is about.
        fell = previous.in_situ - entry.in_situ
        if fell > 0 and len(entry.withdrawn_gates) < fell and entry.gates >= previous.gates:
            problems.append(
                where + f"in-situ evidence fell by {fell} and only "
                f"{len(entry.withdrawn_gates)} gate(s) are named in `withdrawn_gates`. "
                "Retiring a demonstration is a per-gate decision and the gate gets named, "
                "the way a deleted gate does -- arithmetic cannot tell a withdrawal from a "
                "loss."
            )
        rise = entry.uncovered - previous.uncovered
        if rise > 0 and rise > entry.attributed:
            problems.append(
                where + f"the in-situ debt ROSE from {previous.uncovered} to {entry.uncovered} "
                f"({previous.gates} gates and {previous.in_situ} demonstrated, then "
                f"{entry.gates} and {entry.in_situ}), and only {entry.attributed} of that "
                f"rise is accounted for ({len(entry.withdrawn_gates)} withdrawn, "
                f"{entry.owed_forward} owed forward). A round that adds gates without adding "
                "evidence may not satisfy this quota: the count would go backwards while the "
                "coverage number looked healthy. Demonstrate the new gate, or pay for it by "
                "demonstrating another."
            )
            continue
        if rise > 0 and not entry.waiver:
            problems.append(
                where + f"the in-situ debt rose by {rise} with an attribution "
                f"({len(entry.withdrawn_gates)} withdrawn, {entry.owed_forward} owed forward) "
                "and no waiver. The attribution says WHAT rose; the waiver is where somebody "
                "says why that was the right thing to do."
            )
        # THE DUE DATE. `owed_forward` is a promise that the next CI run takes
        # the evidence. A promise nothing checks is the shape this whole
        # register exists to catalogue, so the round after one that made the
        # promise has to show it kept -- or say why not.
        paid = previous.uncovered - entry.uncovered
        if previous.owed_forward and paid < previous.owed_forward and not entry.waiver:
            problems.append(
                where + f"the previous round ({previous.label!r}) owed {previous.owed_forward} "
                f"gate(s) forward and this one cut the debt by {paid}. Demonstrate them, "
                "withdraw them, or write down in `waiver` why the run that was going to "
                "take that evidence did not."
            )
        if entry.gates < previous.gates and not entry.waiver:
            # DELETING A GATE PAYS THE QUOTA EXACTLY AS DEMONSTRATING ONE DOES,
            # because both lower `gates - in_situ`. Nothing in arithmetic can
            # tell paying a debt from repudiating it, so this is the one place
            # the rule asks for a sentence instead.
            problems.append(
                where + f"the register shrank from {previous.gates} to {entry.gates} gate(s) "
                "with no waiver. Removing a check lowers the in-situ debt exactly as "
                "demonstrating one does, and the arithmetic cannot tell those apart. Name the "
                "gate that left and why it left."
            )
        if fell > 0 and not entry.waiver:
            problems.append(
                where + f"in-situ evidence fell from {previous.in_situ} to {entry.in_situ} "
                "with no waiver. Evidence is deleted when a gate is deleted or a "
                "demonstration is withdrawn; both are decisions and both get written down."
            )
        if entry.in_situ > previous.in_situ and not (entry.run and entry.commit):
            problems.append(
                where + f"claims {entry.in_situ - previous.in_situ} more demonstrated gate(s) "
                "and names no run id and commit. R11 evidence is a run in the environment the "
                "gate runs in; a round that cannot name one did not take any."
            )
        fall = previous.uncovered - entry.uncovered
        if fall < quota and not entry.waiver:
            problems.append(
                where + f"cut the in-situ debt by {fall} against a quota of {quota}, and "
                "records no waiver. Either demonstrate more gates in situ or write down why "
                "this round could not."
            )

    last = trajectory[-1]
    live_gates = len(manifest.gates)
    live_in_situ = len(manifest.with_in_situ_evidence())
    if last.gates != live_gates:
        problems.append(
            f"  IN_SITU_TRAJECTORY[{last.label!r}]\n"
            f"    says the register holds {last.gates} gate(s); it holds {live_gates}.\n"
            "    Adding or removing a gate IS a round. Append an InSituRound in the same "
            "commit, and it may not raise the debt."
        )
    if last.in_situ != live_in_situ:
        problems.append(
            f"  IN_SITU_TRAJECTORY[{last.label!r}]\n"
            f"    says {last.in_situ} gate(s) carry in-situ evidence; {live_in_situ} do.\n"
            "    An in-situ count that moves without a recorded round is a coverage claim "
            "nobody can audit."
        )

    for name in last.withdrawn_gates:
        gate = manifest.gates.get(name)
        if gate is None:
            problems.append(
                f"  IN_SITU_TRAJECTORY[{last.label!r}] withdraws evidence for {name!r}, which "
                "is not a gate in this register."
            )
        elif gate.mutation.has_in_situ_evidence:
            problems.append(
                f"  IN_SITU_TRAJECTORY[{last.label!r}] says {name!r}'s evidence was withdrawn "
                "and the register still carries a verified_in_situ_run for it. Delete the "
                "evidence or delete the withdrawal; one of the two is wrong."
            )

    for gate in manifest.by_cost():
        if gate.cost_rank <= top_ranks and not gate.mutation.has_in_situ_evidence:
            # A WITHDRAWAL AT THE TOP OF THE RANKING IS THE CASE THIS RULE WAS
            # HARDEST ON AND IS EXACTLY WHERE WITHDRAWAL MATTERS MOST. The rule
            # exists so nobody demonstrates the easy gates and calls it
            # coverage; it should not also mean that finding the top gate's
            # evidence unsound is unsayable. Naming it in `withdrawn_gates`
            # says it out loud, and `owed_forward` puts a due date on it.
            if gate.name in last.withdrawn_gates and last.owed_forward:
                continue
            problems.append(
                f"  gates.{gate.name} ranks {gate.cost_rank} of {live_gates} by cost-if-inert "
                "and carries no in-situ evidence.\n"
                f"    The top {top_ranks} of the ranking must be demonstrated where they run. "
                "Demonstrating whichever gates were easiest to mutate is the failure this "
                "register exists to end."
            )

    owed = manifest.demonstrable_without_evidence()
    if owed and not last.waiver:
        problems.append(
            f"  {len(owed)} gate(s) this harness can mutate carry no in-situ evidence: "
            f"{[gate.name for gate in owed[:6]]}.\n"
            "    Their own commands are runnable on a runner today, so this is a debt and "
            "not a limit. Run .github/workflows/gate-mutation.yml and record the run, or "
            f"put a waiver on IN_SITU_TRAJECTORY[{last.label!r}] saying why not."
        )
    return problems


def in_situ_line(manifest: GateManifest, trajectory: Sequence[InSituRound]) -> str:
    """The one-line quota summary printed under the in-situ count."""
    live = len(manifest.gates) - len(manifest.with_in_situ_evidence())
    if not trajectory:
        return "in-situ quota: no rounds recorded"
    last = trajectory[-1]
    moved = (trajectory[-2].uncovered - last.uncovered) if len(trajectory) > 1 else 0
    return (
        f"in-situ quota: debt {live}, ceiling {last.uncovered} | "
        f"{len(trajectory)} round(s) | {last.label} cut {moved}"
        + (f" (run {last.run} at {last.commit})" if last.run else "")
        + (f", withdrew {list(last.withdrawn_gates)}" if last.withdrawn_gates else "")
        + (f", owes {last.owed_forward} forward" if last.owed_forward else "")
        + f" | quota {IN_SITU_QUOTA} per round, top {TOP_RANKS_REQUIRING_IN_SITU} of the "
        "ranking must be demonstrated"
    )


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


@dataclass(frozen=True)
class EvidenceProvenance:
    """Whether a gate's recorded demonstration still describes the gate."""

    gate: str
    commit: str
    depends_on: Tuple[str, ...]
    changed: Tuple[str, ...]
    unbounded: bool
    error: str = ""

    @property
    def state(self) -> str:
        if self.error:
            return "unknown"
        if self.changed:
            return "predates a change"
        return "describes HEAD"


def evidence_dependencies(gate: Gate, manifest: GateManifest) -> Tuple[Tuple[str, ...], bool]:
    """Repo paths a gate's demonstration rests on, and whether that set is closed.

    Three sources, and each one is a way the recorded demonstration can stop
    describing the shipped gate:

    * **the files its mutation edits** -- the defect it was shown to catch;
    * **the file its command runs** -- the gate's own implementation, wherever
      the command names one; and
    * **the workflow its environment lives in** -- the step it *is*.

    The second is the one that does not always close. ``python -m pytest`` and
    ``python -m mypy`` name no file, so their dependency set is the whole tree
    and no useful diff can be taken over it. That is returned as ``unbounded``
    rather than as an empty set, because an empty set would read as *nothing
    this gate depends on has changed* -- the flattering answer, and the false
    one.
    """
    paths: List[str] = [edit.file for edit in gate.mutation.edits]
    home = manifest.environments.get(gate.environment)
    if home is not None and home.workflow != "local":
        paths.append(f".github/workflows/{home.workflow}")
    named_a_file = False
    for token in gate.command.split():
        token = token.strip('"')
        if "/" in token and (REPO_ROOT / token).is_file():
            paths.append(token)
            named_a_file = True
    return tuple(sorted(set(paths))), not named_a_file


def evidence_provenance(manifest: GateManifest, root: Path = REPO_ROOT) -> List[EvidenceProvenance]:
    """For every gate carrying evidence, what has changed under it since.

    **This replaces a proof that has expired.** All thirteen demonstrations in
    this register were licensed by one sentence in ``docs/GATES.md``: that
    ``git diff <harvest commit> HEAD`` over eight paths was *empty*. That proof
    was true when it was written and it is a proof that cannot stay true -- it
    fails on the next commit to any of those paths, and it failed on the very
    next one. A proof with a one-commit lifetime is not a mechanism.

    So the question is asked per gate and per commit instead, and the answer is
    computed rather than asserted. It is a **note, never a failure**: a change
    to a file a gate is made of does not establish that the gate stopped
    catching anything, and a rule that reddened the build on the passage of
    ordinary commits would be deleted within a week. What it does establish is
    which evidence is worth re-taking, which is the question a reader with one
    afternoon actually has.
    """
    # ONE `git diff` PER DISTINCT COMMIT, not one per gate. Thirteen
    # subprocesses on every `--check` is a cost the lint job pays on every push,
    # and a shallow checkout (`actions/checkout` fetches depth 1 by default)
    # makes every one of them fail identically. Failing once is enough.
    per_commit: Dict[str, Tuple[Optional[frozenset], str]] = {}

    def changed_since(commit: str) -> Tuple[Optional[frozenset], str]:
        if commit not in per_commit:
            done = subprocess.run(
                ["git", "diff", "--name-only", commit, "HEAD"],
                cwd=str(root),
                capture_output=True,
                text=True,
                errors="replace",
            )
            if done.returncode != 0:
                tail = done.stderr.strip().splitlines()
                per_commit[commit] = (None, tail[-1] if tail else "git diff failed")
            else:
                per_commit[commit] = (frozenset(filter(None, done.stdout.split())), "")
        return per_commit[commit]

    records: List[EvidenceProvenance] = []
    for gate in sorted(manifest.with_in_situ_evidence(), key=lambda g: g.cost_rank):
        commit = gate.mutation.verified_in_situ_commit
        depends_on, unbounded = evidence_dependencies(gate, manifest)
        moved, error = changed_since(commit)
        changed = () if moved is None else tuple(sorted(set(depends_on) & moved))
        records.append(
            EvidenceProvenance(
                gate=gate.name,
                commit=commit,
                depends_on=depends_on,
                changed=changed,
                unbounded=unbounded,
                error=error,
            )
        )
    return records


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


def _apply(edit: Edit, root: Path) -> Tuple[Path, Optional[bytes], Optional[bytes]]:
    """Apply one edit; return ``(file, bytes before, bytes after)``.

    ``None`` for *before* means the file did not exist; ``None`` for *after*
    means the edit removed it. The *after* bytes are what :func:`_restore` uses
    to tell "this file is as I left it" from "something else wrote it".
    """
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
    after: Optional[bytes] = target.read_bytes() if target.is_file() else None
    return target, before, after


def _restore(saved: Iterable[Tuple[Path, Optional[bytes], Optional[bytes]]]) -> List[str]:
    """Put every touched file back, and report anything that moved under us.

    **The report is not fussiness.** This repository is edited by several agents
    at once, and one of the declared mutations DELETES ``bench/results.json`` --
    the file every published claim is verified against -- for the duration of a
    gate run. If another process writes it inside that window, the restore
    silently overwrites their work with bytes read before it happened. The
    window cannot be closed from here; what can be done is to notice, so a lost
    update is a printed sentence rather than a mystery.
    """
    notes: List[str] = []
    for target, before, after in reversed(list(saved)):
        current: Optional[bytes] = target.read_bytes() if target.is_file() else None
        if current != after:
            notes.append(
                f"{target}: is not as the mutation left it. Something else wrote or removed "
                "this file while the gate was running, and the restore below overwrites that "
                "with the bytes read beforehand -- so if another process was writing, its "
                "write is lost and this run's verdict is not attributable to the mutation."
            )
        if before is None:
            if target.exists():
                target.unlink()
            continue
        target.write_bytes(before)
    return notes


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


def _run_setup(gate: Gate, root: Path) -> Tuple[int, str]:
    """Run a mutation's declared ``setup`` command, if it has one.

    **Why a gate would need one, stated on the only gate that does.**
    ``ci.yml``'s ``import-time`` job installs the package NON-EDITABLY, on
    purpose: *"an editable install adds a path finder of its own, and what is
    being measured is what a user actually installs."* So an edit to
    ``src/acronymkit/__init__.py`` does not reach the interpreter that job
    measures, and the mutation would be inert there **by construction** -- not
    because the gate is blind, but because the harness never touched what the
    gate looks at. Without a re-install the demonstration would be a tautology
    in the other direction.

    It runs before the mutated command AND before the restored command, because
    the installed copy has to be put back too.
    """
    if not gate.mutation.setup:
        return 0, ""
    return run_gate_command(gate.mutation.setup, root)


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
    saved: List[Tuple[Path, Optional[bytes], Optional[bytes]]] = []
    restore_notes: List[str] = []
    try:
        for edit in gate.mutation.edits:
            saved.append(_apply(edit, root))
        outcome.applied = True
        setup_rc, setup_output = _run_setup(gate, root)
        if setup_rc != 0:
            outcome.mutated_rc = None
            outcome.mutated_output = setup_output[-8000:]
            outcome.verdict = "UNRESTORED"
            outcome.detail = (
                f"the mutation's `setup` command exited {setup_rc}, so the gate never ran "
                "against the mutated tree and nothing here is a verdict about the gate."
            )
            return outcome
        rc, output = run_gate_command(gate.command, root)
        outcome.mutated_rc = rc
        outcome.mutated_output = output[-8000:]
    finally:
        restore_notes = _restore(saved)
    for note in restore_notes:
        print(f"  restore note: {note}")
    _run_setup(gate, root)
    restored_rc, _ = run_gate_command(gate.command, root)
    outcome.restored_rc = restored_rc
    outcome.seconds = round(time.time() - started, 1)

    wanted_failure = gate.mutation.expect == "fail"
    failed = (outcome.mutated_rc or 0) != 0
    marker = gate.mutation.expect_failure_matching
    if failed != wanted_failure:
        outcome.verdict = "INERT"
        outcome.detail = (
            f"the mutation was applied and the gate exited {outcome.mutated_rc}. "
            f"Expected {gate.mutation.expect}. This gate cannot fail here on this defect."
        )
    elif wanted_failure and marker and marker not in outcome.mutated_output:
        # THE VERDICT RESTS ON THE NAMED LINE, NOT ON THE RETURN CODE.
        # `gates.suite` is the case this exists for: its probe reddens the suite
        # through a side effect of its own, so `rc=1` was reachable with the
        # declared defect uncaught. See the same note in `validate`.
        outcome.verdict = "INERT"
        outcome.detail = (
            f"the gate exited {outcome.mutated_rc}, but its output does not contain "
            f"{marker!r}. Something here failed; it was not this gate catching this "
            "defect, and a return code cannot tell those apart."
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
            f"setup:     {gate.mutation.setup or '-'}\n"
            f"expect:    {gate.mutation.expect}\n"
            f"must say:  {gate.mutation.expect_failure_matching or '-'}\n"
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
    ranked = manifest.by_cost()
    top = [g for g in ranked if g.cost_rank <= TOP_RANKS_REQUIRING_IN_SITU]
    top_done = sum(1 for g in top if g.mutation.has_in_situ_evidence)
    return [
        f"gate manifest: {len(manifest.gates)} gate(s) across {len(manifest.environments)} "
        f"environment(s) in {len(scan_workflows())} workflow file(s)",
        f"mutation kind: {kinds}",
        f"demonstrable by this harness: {len(automated)} of {len(manifest.gates)}, "
        f"{len(manifest.demonstrable_without_evidence())} of them still owed",
        f"CARRYING IN-SITU EVIDENCE:   {len(in_situ)} of {len(manifest.gates)}"
        + ("" if in_situ else "   <- R11 is not satisfied for any gate here"),
        f"top of the cost ranking:     {top_done} of {len(top)} demonstrated  ("
        + ", ".join(f"{g.cost_rank} {g.name}" for g in top)
        + ")",
        in_situ_line(manifest, IN_SITU_TRAJECTORY),
    ]


def _cmd_provenance(manifest: GateManifest) -> int:
    """Which recorded demonstrations still describe the gate they name."""
    records = evidence_provenance(manifest)
    print(
        "recorded in-situ evidence, and what has changed under it since the commit it was\n"
        "taken on. A NOTE, never a failure: a changed file does not establish that a gate\n"
        "stopped catching anything, it establishes which evidence is worth re-taking.\n"
    )
    print(f"{'gate':<34} {'at':<9} {'state':<18} changed under it")
    for record in records:
        detail = ", ".join(record.changed[:3]) or ("-" if not record.error else record.error)
        if record.unbounded:
            detail += "  [command names no file; dependency set is the whole tree]"
        print(f"{record.gate:<34} {record.commit:<9} {record.state:<18} {detail}")
    stale = [r for r in records if r.changed]
    print(
        f"\n{len(stale)} of {len(records)} gate(s) carry evidence taken before a change to a "
        "file the gate is made of."
    )
    return 0


def _cmd_check(manifest: GateManifest) -> int:
    problems = validate(manifest)
    for note in stale_notes(manifest):
        print(f"note: {note}")
    if manifest.path == GATES_PATH:
        records = evidence_provenance(manifest)
        stale = [r for r in records if r.changed]
        if records:
            print(
                f"note: evidence provenance -- {len(stale)} of {len(records)} demonstrated "
                "gate(s) carry evidence taken before a change to a file the gate is made of; "
                "`--evidence-provenance` says which"
            )
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
        for gate in sorted(gates, key=lambda g: g.cost_rank):
            mark = "in-situ" if gate.mutation.has_in_situ_evidence else gate.mutation.kind
            print(f"  #{gate.cost_rank:<3} {gate.name:<34} {gate.defect_class:<20} {mark}")
    print()
    for line in _summary_lines(manifest):
        print(line)
    return 0


def _cmd_ranking(manifest: GateManifest) -> int:
    """Every gate, most expensive first if it silently stopped working."""
    print(
        "cost if inert, worst first. `evidence` is R11: a mutation run in the environment\n"
        "the gate runs in, with the failure captured. `-` is a gate that has never had one.\n"
    )
    print(
        f"{'#':>3}  {'gate':<34} {'blast radius':<22} {'silent?':<8} {'other cover':<12} evidence"
    )
    for gate in manifest.by_cost():
        mark = (
            f"{gate.mutation.verified_in_situ_on} run {gate.mutation.verified_in_situ_run}"
            if gate.mutation.has_in_situ_evidence
            else f"-  ({gate.mutation.kind})"
        )
        print(
            f"{gate.cost_rank:>3}  {gate.name:<34} {gate.blast_radius:<22} "
            f"{gate.silence:<8} {gate.redundancy:<12} {mark}"
        )
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
                "cost_rank": gate.cost_rank,
                "blast_radius": gate.blast_radius,
                "silence": gate.silence,
                "redundancy": gate.redundancy,
                "cost_if_inert": gate.cost_if_inert,
                "mutation_kind": gate.mutation.kind,
                "artifact": gate.mutation.artifact,
                "expect_failure_matching": gate.mutation.expect_failure_matching,
                "setup": gate.mutation.setup,
                "verified_locally_on": str(gate.mutation.verified_locally_on or ""),
                "verified_in_situ_on": str(gate.mutation.verified_in_situ_on or ""),
                "verified_in_situ_run": gate.mutation.verified_in_situ_run,
                "verified_in_situ_commit": gate.mutation.verified_in_situ_commit,
            }
            for name, gate in manifest.gates.items()
        },
        "in_situ_trajectory": [
            {
                "label": entry.label,
                "gates": entry.gates,
                "in_situ": entry.in_situ,
                "uncovered": entry.uncovered,
                "run": entry.run,
                "commit": entry.commit,
                "waiver": entry.waiver,
                "withdrawn_gates": list(entry.withdrawn_gates),
                "owed_forward": entry.owed_forward,
            }
            for entry in IN_SITU_TRAJECTORY
        ],
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
    parser.add_argument(
        "--ranking",
        action="store_true",
        help="every gate ordered by what it costs if it silently stops working",
    )
    parser.add_argument("--json", action="store_true", help="print the register as JSON")
    parser.add_argument(
        "--evidence-provenance",
        action="store_true",
        help="which recorded demonstrations predate a change to the gate they describe",
    )
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
    if args.ranking:
        return _cmd_ranking(manifest)
    if args.evidence_provenance:
        return _cmd_provenance(manifest)
    if args.json:
        return _cmd_json(manifest)
    return _cmd_check(manifest)


if __name__ == "__main__":
    raise SystemExit(main())
