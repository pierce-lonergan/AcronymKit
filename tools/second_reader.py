#!/usr/bin/env python3
"""Execute and validate ``docs/SECOND-READER.md`` -- the cold-read policy -- as code.

Why this exists
---------------
``docs/SECOND-READER.md`` is a policy about catching prose that no ratchet can
see. Its first execution as policy found three defects **in itself**, and two of
them were the same class it was written to catch:

* its published trigger command read *committed history* while the policy places
  the read *before the commit*, so the command returned an empty list on a round
  that had rewritten the front page;
* ``git diff`` cannot see a file that does not exist under either revision, and
  that round introduced its most important page as a new file;
* its pathspec could not reach ``pyproject.toml``, whose ``description`` is the
  sentence PyPI renders.

The command was corrected in place. **A corrected command in a document is the
same artifact as the wrong one** -- prose, unexecuted, trusted. This module is
the correction made executable: the trigger is a function, the rotation set and
the cursor are parsed out of the page rather than remembered, and the findings
the reader produces are a validated table rather than a paragraph.

The three things this module owns
---------------------------------
**1. The trigger (:func:`trigger_a`).** It reads the *working tree*, because
that is the state the policy fires in, and it reports untracked files, because
the round that motivated this introduced a new one. The published command and
:data:`PATHSPEC` are checked against each other by :func:`validate`, so the
sentence in the document cannot drift from the code the way the last one did.

**2. The rotation cursor.** D-072 recorded that the policy's only state was "a
cursor it does not define": section 3 said *oldest-read-first* and no per-file
read dates existed anywhere, so the reader used rotation order instead. That is
settled here in favour of **rotation order, wrapping** -- the rule both executed
reads actually followed -- because it is derivable from one recorded field and a
rule nobody can compute is not a rule. :func:`successor` derives it,
:func:`validate` refuses a cursor that does not match, and refuses a read whose
trigger-B file is not the one the cursor pointed at. The cursor is therefore
*followed* rather than *announced*.

**3. The hand-off.** The cold reader **reports**; somebody else **applies**.
Section 5 said that in a sentence and the sentence did not hold: the first
execution edited a page another workstream had written that round, and flagged
itself for doing so. A sentence will not hold it next time either, so the
schema holds it instead -- ``disposition = "fixed"`` requires an ``applied_by``
that is **not** the reader who raised the finding. A reader cannot close its own
finding by editing prose, because closing takes a second name.

Why the disposition rule is the load-bearing half
--------------------------------------------------
A read-only reviewer whose findings rot is worse than one who fixes things, and
this repository has the measurement: the first pass's C1 finding -- two pages
claiming the air-gap job drives *"every CLI subcommand"* while the probe drives
thirteen of the sixteen -- was unaltered in all three places one round later,
**after** somebody had found it and written down where it is. So:

* a finding is born ``open``;
* an ``open`` finding must be re-affirmed at **every** cold read
  (``reviewed_in`` names the newest read), which costs one field and cannot be
  forgotten quietly;
* an ``open`` finding may survive at most :data:`OPEN_READ_LIMIT` reads. On the
  next one it must be ``fixed``, ``blocked`` naming a decision, or ``permanent``
  naming a reason. It never stops being a finding; it stops being *silent*
  (R14).

What this module deliberately does **not** do: force anybody to apply anything.
A reader that could assign work to strangers would be authoring by another
route. What is enforced is that nothing rots without a name against it.

How it fails
------------
**Nothing here reads a sentence either.** ``--check`` adjudicates the shape of
the ledger, the arithmetic of the cursor and the agreement between the page's
command and this file's constants. It cannot tell a true finding from an
invented one, and section 7 of the policy already says the only defence is that
each finding ships the command that refutes it.

**Corrected 2026-08-26: the ledger IS in the sdist.** This said ``MANIFEST.in``
ships ``docs/*.md`` so ``docs/cold-reads.toml`` is absent from a distribution
exactly as ``.github/gates.toml`` is. ``387f739`` added explicit ``include``
lines for both, and both are present in a tarball built from this tree. This was
the third copy of one false sentence and **the only one no second-reader trigger
can reach**, because ``PATHSPEC`` does not cover ``tools/``. ``--check`` fails loudly there rather than passing
vacuously, which means this gate belongs to a checkout environment; it is
reported as such in the gate register rather than assumed.

**The rotation rule this file settles makes a newly appended page wait a full
turn.** ``docs/POSITIONING.md`` was appended to the end of a fifteen-file set,
so the first read of the page that states what the library is for is fourteen
rounds away under the very rule that made the cursor checkable.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO_ROOT / "docs" / "SECOND-READER.md"
LEDGER_PATH = REPO_ROOT / "docs" / "cold-reads.toml"

#: The trigger-A pathspec, handed to ``git status`` verbatim.
#:
#: ``pyproject.toml`` is here for the reason D-072 gives: its ``description`` is
#: the line PyPI renders under the package name, it was rewritten by the round
#: that first ran this policy, and no trigger on the page would have looked at
#: it. :func:`validate` checks this tuple against the command printed in section
#: 3 of the policy, because a pathspec that lives in two places is a pathspec
#: that will disagree with itself.
PATHSPEC: Tuple[str, ...] = (
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "pyproject.toml",
    "docs",
)

#: Root files the trigger treats as user-facing, by name.
ROOT_USER_FACING: Tuple[str, ...] = (
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "pyproject.toml",
)

#: Excluded from the trigger even though the pathspec reaches them. The policy's
#: own wording: historical records rather than instructions to a user, and scoped
#: technical notes read by somebody who arrived from a link that already warned
#: them.
EXCLUDED_GLOBS: Tuple[str, ...] = (
    "docs/DECISIONS.md",
    "docs/AUDIT-*.md",
    "docs/notes/*",
)

#: How many cold reads a finding may remain ``open`` across, counting the read
#: that raised it. At the limit ``--check`` warns; past it, it fails.
OPEN_READ_LIMIT = 2

DISPOSITIONS: Tuple[str, ...] = ("open", "fixed", "blocked", "permanent")

READ_FIELDS: Tuple[str, ...] = (
    "id",
    "reader",
    "rotation_served",
    "cursor_after",
    "covered",
    "transcribed_from",
    "note",
)
READ_REQUIRED: Tuple[str, ...] = ("id", "reader", "rotation_served", "cursor_after", "note")

FINDING_FIELDS: Tuple[str, ...] = (
    "id",
    "raised_in",
    "file",
    "line",
    "quote",
    "refutation",
    "owner",
    "disposition",
    "reviewed_in",
    "applied_by",
    "applied_in",
    "blocked_on",
    "reason",
)
FINDING_REQUIRED: Tuple[str, ...] = (
    "id",
    "raised_in",
    "file",
    "line",
    "quote",
    "refutation",
    "owner",
    "disposition",
    "reviewed_in",
)

#: The fenced block in section 3 that holds the rotation set, and the one in
#: section 8 that holds the cursor. Both are parsed rather than restated, so the
#: page has exactly one copy of each and this module reads it.
_ROTATION_FENCE = "<!-- rotation-set -->"
_CURSOR_FENCE = "<!-- rotation-cursor -->"
_TRIGGER_FENCE = "<!-- trigger-a-command -->"

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SecondReaderError(Exception):
    """A ledger or policy page that could not be read at all."""


# ---------------------------------------------------------------------------
# the trigger
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Change:
    """One entry from ``git status``: its two-letter code and its path."""

    status: str
    path: str


def is_user_facing(path: str) -> bool:
    """Is ``path`` a document a stranger decides whether to trust this library on?

    The pathspec is the coarse filter and this is the fine one. ``docs`` reaches
    ``docs/DECISIONS.md``, ``docs/AUDIT-*.md`` and ``docs/notes/*``, which the
    policy excludes, and it reaches non-Markdown files under ``docs/`` -- the
    findings ledger itself among them -- which are machine state rather than
    prose.
    """
    norm = path.replace("\\", "/").strip()
    if not norm:
        return False
    if norm in ROOT_USER_FACING:
        return True
    if not norm.startswith("docs/") or not norm.endswith(".md"):
        return False
    return not any(fnmatch.fnmatch(norm, pattern) for pattern in EXCLUDED_GLOBS)


def git_changes(root: Path = REPO_ROOT, pathspec: Sequence[str] = PATHSPEC) -> List[Change]:
    """Every working-tree change under ``pathspec``, tracked and untracked.

    ``--porcelain -z`` rather than ``--porcelain``: the NUL form needs no
    unquoting, which matters because the un-zed form quotes any path with a
    space or a non-ASCII byte and a naive split would hand back a mangled name.
    ``--untracked-files=all`` rather than the default: the default collapses a
    brand-new directory to a single ``dir/`` entry, and the round that motivated
    this policy correction added a new file.
    """
    command = ["git", "status", "--porcelain", "-z", "--untracked-files=all", "--"]
    command.extend(pathspec)
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            check=False,
        )
    except OSError as error:  # pragma: no cover - git absent
        raise SecondReaderError(f"could not run git in {root}: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise SecondReaderError(f"git status failed in {root}: {detail}")
    records = [r for r in completed.stdout.decode("utf-8", "replace").split("\0") if r]
    changes: List[Change] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if len(record) < 4:
            continue
        code, path = record[:2], record[3:]
        changes.append(Change(status=code, path=path.replace("\\", "/")))
        # A rename carries a second path. Both are reported: the destination is
        # what a reader opens, and the source is what a link elsewhere in the
        # tree may still point at.
        if ("R" in code or "C" in code) and index < len(records):
            changes.append(Change(status=code, path=records[index].replace("\\", "/")))
            index += 1
    return changes


def user_facing_files(root: Path = REPO_ROOT) -> List[str]:
    """Every user-facing file in the tree, whether or not anything reads it.

    This exists because of a mutation that got through. Deleting an entry from
    the rotation set was invisible to the validator and to the suite: the
    remaining entries all existed, none repeated, and the cursor still resolved.
    D-061's lesson in a second place -- **shrinking a list is not the same as
    growing coverage** -- and the page that motivated the last rotation amendment
    said the same thing about itself: it was the one user-facing document no
    trigger could ever reach.

    So the rotation is checked against the tree rather than against itself.
    :func:`validate` requires every file this returns to be in the rotation set,
    which catches a silent deletion and catches a new document that never
    entered.
    """
    found = [name for name in ROOT_USER_FACING if (root / name).is_file()]
    docs = root / "docs"
    if docs.is_dir():
        for path in sorted(docs.rglob("*.md")):
            relative = path.relative_to(root).as_posix()
            if is_user_facing(relative):
                found.append(relative)
    return sorted(found)


def trigger_a(root: Path = REPO_ROOT, pathspec: Sequence[str] = PATHSPEC) -> List[str]:
    """The user-facing files this round touched, read from the working tree.

    This is the whole of trigger A. It returns an empty list when the tree is
    clean under the pathspec -- demonstrated on a clean worktree of this
    repository rather than assumed, because a trigger that cannot return nothing
    is not a trigger.
    """
    return sorted({c.path for c in git_changes(root, pathspec) if is_user_facing(c.path)})


# ---------------------------------------------------------------------------
# the policy page: rotation set, cursor, and the command it publishes
# ---------------------------------------------------------------------------
def _fenced_after(text: str, marker: str, where: str) -> str:
    """Return the body of the first fenced block following ``marker``."""
    at = text.find(marker)
    if at < 0:
        raise SecondReaderError(f"{where}: marker {marker} is not in the page")
    if text.find(marker, at + len(marker)) >= 0:
        raise SecondReaderError(
            f"{where}: marker {marker} appears more than once; the page must hold one copy"
        )
    opening = text.find("```", at)
    if opening < 0:
        raise SecondReaderError(f"{where}: no fenced block follows {marker}")
    body_start = text.find("\n", opening)
    closing = text.find("```", body_start)
    if body_start < 0 or closing < 0:
        raise SecondReaderError(f"{where}: the block after {marker} is not closed")
    return text[body_start + 1 : closing]


def parse_rotation(policy_text: str) -> List[str]:
    """The trigger-B rotation set, in order, parsed from the policy page.

    Entries are separated by ``·`` and by newlines, which is how the page has
    always printed them. The set is the one thing in this policy a later reader
    has to take on trust, so it is read from the page rather than duplicated
    here -- and :func:`validate` requires every entry to exist in the tree.
    """
    body = _fenced_after(policy_text, _ROTATION_FENCE, "rotation set")
    entries: List[str] = []
    for chunk in body.replace("·", "\n").splitlines():
        name = chunk.strip().strip("`")
        if name:
            entries.append(name)
    return entries


def parse_cursor(policy_text: str) -> str:
    """The rotation cursor: the file trigger B serves next."""
    body = _fenced_after(policy_text, _CURSOR_FENCE, "rotation cursor")
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("cursor"):
            return stripped.split(None, 1)[1].strip().strip("`") if " " in stripped else ""
    raise SecondReaderError("rotation cursor: the block declares no `cursor` line")


def parse_trigger_pathspec(policy_text: str) -> List[str]:
    """The pathspec in the trigger-A command the page publishes.

    This is the check the last correction needed and did not have. The page
    prints a command; this module runs a pathspec; a reader who follows the page
    and a gate that follows the code must be looking at the same files.
    """
    body = _fenced_after(policy_text, _TRIGGER_FENCE, "trigger A command")
    for line in body.splitlines():
        if "git status" not in line:
            continue
        if " -- " not in line:
            raise SecondReaderError("trigger A command: the published command has no `--` pathspec")
        return [token for token in line.split(" -- ", 1)[1].split() if token]
    raise SecondReaderError("trigger A command: the block publishes no `git status` command")


def successor(rotation: Sequence[str], name: str) -> str:
    """The rotation entry after ``name``, wrapping.

    Rotation order, not oldest-read-first. D-072 recorded that *oldest-read-first*
    is uncomputable here -- no per-file read dates exist anywhere and the first
    pass left none -- and that both executed reads used list order instead. A
    rule two readers already followed and a machine can check beats a rule
    neither could evaluate.
    """
    try:
        index = list(rotation).index(name)
    except ValueError as error:
        raise SecondReaderError(f"{name!r} is not in the rotation set") from error
    return rotation[(index + 1) % len(rotation)]


# ---------------------------------------------------------------------------
# the findings ledger
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Read:
    """One executed cold read."""

    id: str
    reader: str
    rotation_served: str
    cursor_after: str
    covered: Tuple[str, ...] = ()
    transcribed_from: str = ""
    note: str = ""


@dataclass(frozen=True)
class Finding:
    """One entry of the report, in the shape section 5 specifies."""

    id: str
    raised_in: str
    file: str
    line: int
    quote: str
    refutation: str
    owner: str
    disposition: str
    reviewed_in: str
    applied_by: str = ""
    applied_in: str = ""
    blocked_on: str = ""
    reason: str = ""


@dataclass
class Ledger:
    """``docs/cold-reads.toml``, parsed."""

    path: Path
    schema_version: int
    policy: str
    reads: List[Read] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)

    @property
    def newest_read(self) -> Optional[Read]:
        return self.reads[-1] if self.reads else None

    def read_index(self, read_id: str) -> int:
        for position, read in enumerate(self.reads):
            if read.id == read_id:
                return position
        return -1

    def reader_of(self, read_id: str) -> str:
        position = self.read_index(read_id)
        return self.reads[position].reader if position >= 0 else ""


def _load_toml(path: Path) -> Dict[str, Any]:
    """Parse ``path`` as TOML on any supported interpreter.

    Same reasoning as ``tools/gates.py`` and ``tools/splits.py``: ``tomllib`` is
    3.11+ and ``tomli`` is not a declared dev dependency, so on 3.9 and 3.10
    there may be no parser at all. That is an error rather than a silent pass --
    a validator that succeeds because it could not read the file is the defect
    every register in this repository exists to refuse.
    """
    if sys.version_info >= (3, 11):
        import tomllib as _toml
    else:  # pragma: no cover - 3.9/3.10 path
        try:
            import tomli as _toml
        except ImportError as error:
            raise SecondReaderError(
                "no TOML parser available: tomllib is 3.11+ and tomli is not installed. "
                f"Cannot validate {path}."
            ) from error
    try:
        with path.open("rb") as handle:
            return _toml.load(handle)
    except FileNotFoundError as error:
        raise SecondReaderError(
            f"{path} does not exist. The cold-read ledger is the policy's only machine-readable "
            "state; without it there is nothing to validate."
        ) from error
    except Exception as error:  # tomllib.TOMLDecodeError, and anything it wraps
        raise SecondReaderError(f"{path} is not valid TOML: {error}") from error


def _string(raw: Mapping[str, Any], key: str, where: str, default: str = "") -> str:
    value = raw.get(key, default)
    if not isinstance(value, str):
        raise SecondReaderError(f"{where}: {key} must be a string, got {value!r}")
    return value


def load(path: Path = LEDGER_PATH) -> Ledger:
    """Read and shape-check ``docs/cold-reads.toml``. Semantics are :func:`validate`."""
    raw = _load_toml(path)
    unknown = sorted(set(raw) - {"ledger", "reads", "findings"})
    if unknown:
        raise SecondReaderError(f"{path}: unknown top-level table(s): {unknown}")
    header = raw.get("ledger")
    if not isinstance(header, dict):
        raise SecondReaderError(f"{path}: no [ledger] table")
    header_unknown = sorted(set(header) - {"schema_version", "policy"})
    if header_unknown:
        raise SecondReaderError(f"{path}: [ledger] has unknown key(s): {header_unknown}")
    version = header.get("schema_version")
    if not isinstance(version, int):
        raise SecondReaderError(f"{path}: [ledger].schema_version must be an integer")

    reads: List[Read] = []
    for position, entry in enumerate(raw.get("reads", [])):
        where = f"{path}: reads[{position}]"
        if not isinstance(entry, dict):
            raise SecondReaderError(f"{where}: expected a table")
        extra = sorted(set(entry) - set(READ_FIELDS))
        if extra:
            raise SecondReaderError(f"{where}: unknown key(s): {extra}")
        missing = [k for k in READ_REQUIRED if k not in entry]
        if missing:
            raise SecondReaderError(f"{where}: missing required key(s): {missing}")
        covered = entry.get("covered", [])
        if not isinstance(covered, list) or any(not isinstance(c, str) for c in covered):
            raise SecondReaderError(f"{where}: covered must be a list of strings")
        reads.append(
            Read(
                id=_string(entry, "id", where),
                reader=_string(entry, "reader", where),
                rotation_served=_string(entry, "rotation_served", where),
                cursor_after=_string(entry, "cursor_after", where),
                covered=tuple(covered),
                transcribed_from=_string(entry, "transcribed_from", where),
                note=_string(entry, "note", where),
            )
        )

    findings: List[Finding] = []
    for position, entry in enumerate(raw.get("findings", [])):
        where = f"{path}: findings[{position}]"
        if not isinstance(entry, dict):
            raise SecondReaderError(f"{where}: expected a table")
        extra = sorted(set(entry) - set(FINDING_FIELDS))
        if extra:
            raise SecondReaderError(f"{where}: unknown key(s): {extra}")
        missing = [k for k in FINDING_REQUIRED if k not in entry]
        if missing:
            raise SecondReaderError(f"{where}: missing required key(s): {missing}")
        line = entry.get("line")
        if not isinstance(line, int) or isinstance(line, bool):
            raise SecondReaderError(f"{where}: line must be an integer")
        findings.append(
            Finding(
                id=_string(entry, "id", where),
                raised_in=_string(entry, "raised_in", where),
                file=_string(entry, "file", where),
                line=line,
                quote=_string(entry, "quote", where),
                refutation=_string(entry, "refutation", where),
                owner=_string(entry, "owner", where),
                disposition=_string(entry, "disposition", where),
                reviewed_in=_string(entry, "reviewed_in", where),
                applied_by=_string(entry, "applied_by", where),
                applied_in=_string(entry, "applied_in", where),
                blocked_on=_string(entry, "blocked_on", where),
                reason=_string(entry, "reason", where),
            )
        )

    return Ledger(
        path=path,
        schema_version=version,
        policy=_string(header, "policy", f"{path}: [ledger]"),
        reads=reads,
        findings=findings,
    )


def _validate_reads(ledger: Ledger, rotation: Sequence[str]) -> List[str]:
    problems: List[str] = []
    seen: Dict[str, int] = {}
    previous: Optional[Read] = None
    for position, read in enumerate(ledger.reads):
        where = f"reads[{position}] ({read.id or '<no id>'})"
        if not _ISO_DATE.match(read.id):
            problems.append(f"{where}: id must be an ISO date, got {read.id!r}")
        if read.id in seen:
            problems.append(f"{where}: duplicate read id, first declared at reads[{seen[read.id]}]")
        seen[read.id] = position
        if previous is not None and read.id <= previous.id:
            problems.append(f"{where}: reads must be in ascending date order (after {previous.id})")
        if not read.reader.strip():
            problems.append(f"{where}: reader is empty; a cold read with no reader is unattributed")
        if read.cursor_after and read.cursor_after not in rotation:
            problems.append(
                f"{where}: cursor_after {read.cursor_after!r} is not in the rotation set"
            )
        if read.rotation_served:
            if read.rotation_served not in rotation:
                problems.append(
                    f"{where}: rotation_served {read.rotation_served!r} is not in the rotation set"
                )
            elif read.cursor_after != successor(rotation, read.rotation_served):
                problems.append(
                    f"{where}: cursor_after is {read.cursor_after!r}; rotation order after "
                    f"{read.rotation_served!r} is {successor(rotation, read.rotation_served)!r}"
                )
            if (
                previous is not None
                and previous.cursor_after
                and read.rotation_served != previous.cursor_after
            ):
                problems.append(
                    f"{where}: trigger B served {read.rotation_served!r} but the cursor left by "
                    f"{previous.id} pointed at {previous.cursor_after!r}. The cursor is "
                    "followed, not announced."
                )
        elif not read.note.strip():
            problems.append(
                f"{where}: rotation_served is empty and no note says why trigger B did not fire"
            )
        previous = read
    return problems


def _validate_findings(ledger: Ledger, root: Path) -> List[str]:
    problems: List[str] = []
    newest = ledger.newest_read
    seen: Dict[str, int] = {}
    for position, finding in enumerate(ledger.findings):
        where = f"findings[{position}] ({finding.id or '<no id>'})"
        if not finding.id.strip():
            problems.append(f"{where}: id is empty")
        if finding.id in seen:
            problems.append(f"{where}: duplicate finding id, first at findings[{seen[finding.id]}]")
        seen[finding.id] = position
        raised_at = ledger.read_index(finding.raised_in)
        if raised_at < 0:
            problems.append(f"{where}: raised_in {finding.raised_in!r} names no declared read")
        reviewed_at = ledger.read_index(finding.reviewed_in)
        if reviewed_at < 0:
            problems.append(f"{where}: reviewed_in {finding.reviewed_in!r} names no declared read")
        elif raised_at >= 0 and reviewed_at < raised_at:
            problems.append(f"{where}: reviewed_in {finding.reviewed_in!r} precedes raised_in")
        if not finding.quote.strip():
            problems.append(f"{where}: quote is empty; a finding quotes the sentence it refutes")
        if not finding.refutation.strip():
            problems.append(
                f"{where}: refutation is empty. A finding with no command or reading behind it is "
                "an opinion, and section 7 names that as the only defence this policy has."
            )
        if not finding.owner.strip():
            problems.append(f"{where}: owner is empty; use 'unowned' and let the rule bite")
        if finding.line < 0:
            problems.append(f"{where}: line must be zero (unlocated) or positive")
        if finding.disposition not in DISPOSITIONS:
            problems.append(
                f"{where}: disposition {finding.disposition!r} is not one of {list(DISPOSITIONS)}"
            )
            continue
        if finding.disposition == "fixed":
            if not finding.applied_by.strip():
                problems.append(f"{where}: fixed requires applied_by naming who applied it")
            elif finding.applied_by.strip() == ledger.reader_of(finding.raised_in).strip():
                problems.append(
                    f"{where}: applied_by is the reader who raised it ({finding.applied_by!r}). "
                    "The cold reader reports; somebody else applies -- that is the whole of the "
                    "read-only boundary, and it is here rather than in a sentence because a "
                    "sentence did not hold it."
                )
            if not finding.applied_in.strip():
                problems.append(f"{where}: fixed requires applied_in naming the round or commit")
        elif finding.disposition == "blocked":
            if not finding.blocked_on.strip():
                problems.append(f"{where}: blocked requires blocked_on naming the decision (R14)")
        elif finding.disposition == "permanent":
            if not finding.reason.strip():
                problems.append(f"{where}: permanent requires reason (R14)")
        else:  # open
            if newest is not None and finding.reviewed_in != newest.id:
                problems.append(
                    f"{where}: open, but reviewed_in is {finding.reviewed_in!r} and the newest "
                    f"read is {newest.id!r}. Every open finding is re-affirmed at every cold read; "
                    "that is what keeps a finding nobody applies from rotting quietly."
                )
            if raised_at >= 0 and newest is not None:
                spanned = ledger.read_index(newest.id) - raised_at + 1
                if spanned > OPEN_READ_LIMIT:
                    problems.append(
                        f"{where}: open across {spanned} cold reads; the limit is "
                        f"{OPEN_READ_LIMIT}. It is applied, or it is blocked on a named decision, "
                        "or it is permanent with a reason. It does not stay open."
                    )
        if finding.disposition != "fixed" and finding.file and not (root / finding.file).exists():
            problems.append(
                f"{where}: file {finding.file!r} is not in the tree, and the finding is not "
                "recorded as fixed"
            )
    return problems


def validate(
    ledger: Ledger,
    policy_text: str,
    root: Path = REPO_ROOT,
) -> List[str]:
    """Every problem with the ledger and the policy page, as a list of sentences.

    Empty means the policy's state is internally consistent, its cursor is
    derivable rather than declared, its published command names the pathspec this
    module actually uses, and no finding is rotting without a name against it.
    """
    problems: List[str] = []

    try:
        rotation = parse_rotation(policy_text)
    except SecondReaderError as error:
        return [str(error)]
    if not rotation:
        return ["rotation set: the block is empty; every check below would pass vacuously"]
    duplicates = sorted({name for name in rotation if rotation.count(name) > 1})
    if duplicates:
        problems.append(f"rotation set: duplicate entr(ies) {duplicates}")
    for name in rotation:
        if not (root / name).exists():
            problems.append(f"rotation set: {name!r} is not in the tree; trigger B cannot serve it")
    unreachable = [name for name in user_facing_files(root) if name not in rotation]
    if unreachable:
        problems.append(
            f"rotation set: {len(unreachable)} user-facing file(s) no trigger can ever reach: "
            f"{unreachable}. Trigger A only fires on a file a round changes, so a document nobody "
            "edits is a document nobody re-reads -- which is the count that bought trigger B in the "
            "first place."
        )

    try:
        published = parse_trigger_pathspec(policy_text)
    except SecondReaderError as error:
        problems.append(str(error))
    else:
        if tuple(published) != PATHSPEC:
            problems.append(
                "trigger A: the pathspec the page publishes is "
                f"{published} and the pathspec this module runs is {list(PATHSPEC)}. The last time "
                "these disagreed, the published command returned nothing at the moment it fired."
            )

    try:
        cursor = parse_cursor(policy_text)
    except SecondReaderError as error:
        problems.append(str(error))
        cursor = ""
    if cursor and cursor not in rotation:
        problems.append(f"rotation cursor: {cursor!r} is not in the rotation set")

    problems.extend(_validate_reads(ledger, rotation))
    problems.extend(_validate_findings(ledger, root))

    newest = ledger.newest_read
    if newest is None:
        problems.append("the ledger declares no cold read at all")
    elif cursor and newest.cursor_after and cursor != newest.cursor_after:
        problems.append(
            f"rotation cursor: the policy page says {cursor!r} and the newest read "
            f"({newest.id}) left {newest.cursor_after!r}. A policy whose only memory is a "
            "sentence in a document has exactly one failure mode, and this is it."
        )
    if ledger.policy and not (root / ledger.policy).exists():
        problems.append(f"[ledger].policy names {ledger.policy!r}, which is not in the tree")
    return problems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _open_findings(ledger: Ledger) -> List[Finding]:
    return [f for f in ledger.findings if f.disposition == "open"]


def _summary_lines(ledger: Ledger, rotation: Sequence[str], cursor: str) -> List[str]:
    counts: Dict[str, int] = dict.fromkeys(DISPOSITIONS, 0)
    for finding in ledger.findings:
        counts[finding.disposition] = counts.get(finding.disposition, 0) + 1
    newest = ledger.newest_read
    at_limit = 0
    if newest is not None:
        newest_at = ledger.read_index(newest.id)
        for finding in _open_findings(ledger):
            raised_at = ledger.read_index(finding.raised_in)
            if raised_at >= 0 and newest_at - raised_at + 1 == OPEN_READ_LIMIT:
                at_limit += 1
    lines = [
        f"cold reads: {len(ledger.reads)} recorded; newest {newest.id if newest else 'none'}",
        f"rotation: {len(rotation)} file(s); trigger B serves {cursor or '<unset>'} next",
        "findings: "
        + ", ".join(f"{name} {counts.get(name, 0)}" for name in DISPOSITIONS)
        + f"  (of {len(ledger.findings)})",
    ]
    lines.append(
        f"OPEN AND AT THE LIMIT: {at_limit} of {counts.get('open', 0)}"
        + (
            "   <- refused at the next cold read unless applied, blocked or made permanent"
            if at_limit
            else ""
        )
    )
    return lines


def _cmd_check(ledger_path: Path, policy_path: Path, root: Path) -> int:
    try:
        ledger = load(ledger_path)
    except SecondReaderError as error:
        print(f"cold-read ledger: {error}", file=sys.stderr)
        return 1
    try:
        policy_text = policy_path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"cold-read policy: cannot read {policy_path}: {error}", file=sys.stderr)
        return 1
    problems = validate(ledger, policy_text, root)
    if problems:
        print(f"{ledger_path}: {len(problems)} problem(s)")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    rotation = parse_rotation(policy_text)
    for line in _summary_lines(ledger, rotation, parse_cursor(policy_text)):
        print(line)
    print(
        "cold-read policy OK: the cursor is derivable and agrees with the page, the published "
        "trigger names the pathspec this module runs, and every finding carries a disposition"
    )
    return 0


def _cmd_trigger(root: Path) -> int:
    try:
        touched = trigger_a(root)
    except SecondReaderError as error:
        print(f"trigger A: {error}", file=sys.stderr)
        return 1
    if not touched:
        print("trigger A: no user-facing file is changed in the working tree; no cold read is due")
        return 0
    print(f"trigger A: {len(touched)} user-facing file(s) changed in the working tree")
    for name in touched:
        print(f"  {name}")
    return 0


def _cmd_cost(policy_path: Path, root: Path) -> int:
    """Print the size of the corpus one round of this protocol has to cover.

    A costing is the class of number a page publishes once and never re-runs:
    section 6's block was two files and roughly a third of the corpus light by
    the time anybody looked. It is derived here rather than quoted there, so
    that going stale is not one of the things it can do.
    """
    try:
        rotation = parse_rotation(policy_path.read_text(encoding="utf-8"))
    except (OSError, SecondReaderError) as error:
        print(f"cold-read policy: {error}", file=sys.stderr)
        return 1
    sized = []
    for name in rotation:
        path = root / name
        if not path.is_file():
            print(f"rotation: {name} is not in the tree", file=sys.stderr)
            return 1
        sized.append((len(path.read_text(encoding="utf-8", errors="replace").split()), name))
    sized.sort()
    total = sum(words for words, _ in sized)
    median = sized[len(sized) // 2]
    print(f"the full user-facing corpus   {total:>7,} words across {len(sized)} files")
    print(f"the largest single file       {sized[-1][0]:>7,} words   {sized[-1][1]}")
    print(f"the median file               {median[0]:>7,} words   {median[1]}")
    print(f"the smallest                  {sized[0][0]:>7,} words   {sized[0][1]}")
    return 0


def _cmd_open(ledger_path: Path) -> int:
    try:
        ledger = load(ledger_path)
    except SecondReaderError as error:
        print(f"cold-read ledger: {error}", file=sys.stderr)
        return 1
    findings = _open_findings(ledger)
    if not findings:
        print("no open findings")
        return 0
    print(f"{len(findings)} open finding(s) -- the apply worklist")
    for finding in findings:
        where = f"{finding.file}:{finding.line}" if finding.line else finding.file
        print(f"  {finding.id}  {where}  owner={finding.owner}  raised {finding.raised_in}")
        print(f"      {finding.refutation}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the ledger and the policy page (the CI gate)",
    )
    parser.add_argument(
        "--trigger",
        action="store_true",
        help="print the user-facing files this round touched (trigger A)",
    )
    parser.add_argument(
        "--cost",
        action="store_true",
        help="print the size of the corpus one round of the protocol covers",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        dest="open_findings",
        help="print the findings nobody has applied yet",
    )
    args = parser.parse_args(argv)

    if args.trigger:
        return _cmd_trigger(args.root)
    if args.cost:
        return _cmd_cost(args.policy, args.root)
    if args.open_findings:
        return _cmd_open(args.ledger)
    return _cmd_check(args.ledger, args.policy, args.root)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
