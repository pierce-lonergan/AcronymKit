#!/usr/bin/env python3
"""Validate a round's machine-readable self-assessment, and reconstruct a round from disk.

Why this exists
---------------
**Three consecutive rounds kept their work and lost their account of it, for
three unrelated reasons.** D-095: four of ten agents finished and then exceeded a
retry cap formatting an over-long report. The first attempt at Phase B: every
agent killed mid-flight by a usage limit, so no report was ever begun. The
second: the recorder died *after* filing twelve records, and nothing said so.

The symptom is one thing and D-098 names it:

    A round's self-assessment is the only artefact a round produces that no gate
    reads. Eight gates check the code, the numbers, the splits, the register and
    the second reader. Nothing checks that the round said what it did.

Each time, the code was recoverable only because it happened to be in the tree.
That is luck. The fix is to split **execution state** from **narrative
reporting**: a small JSON record written straight to disk as the *penultimate*
tool call, before any long prose. An agent that then blows its ceiling composing
paragraphs has already filed.

What this module owns
---------------------
**1. The schema** (:data:`REQUIRED_FIELDS`, :data:`STATUS_VALUES`,
:data:`GATE_KEYS`, :data:`CLAIMS_REQUIRED`) and a validator that refuses an
unknown key. The unknown-key rule is the one ``bench/splits.toml`` learned the
expensive way: a misspelt ``laps_trigger`` silently dropped the single field the
structure existed to require, and nothing was red. A summary with
``how_it_failed`` instead of ``how_it_fails`` would otherwise validate while
carrying none of the thing the field is for.

**2. The reader** (:func:`report`), which reconstructs a round from a directory
when reports are missing. It answers, per workstream: filed, filed but empty, or
never filed at all.

**3. The gate** (:func:`check`, ``--check``), over the rounds committed under
:data:`ROUNDS_ROOT`, plus the agreement between this file's field list and the
copy of it in ``CONTRIBUTING.md``.

Absence is not a directory listing, and this is the load-bearing design decision
--------------------------------------------------------------------------------
D-096 recorded the cost of a check that could not tell *"no read happened"* from
*"a read happened and could not record it"*: the gate stayed green through two
consecutive rounds in which the cold read wrote no ledger row. **An empty
directory cannot distinguish "nobody filed" from "nobody was launched."** So a
round is a directory holding a **roster** -- ``round.toml``, naming the
workstreams that were supposed to file -- and one ``<label>.json`` per summary.
Only against a roster is ``absent`` a finding rather than a shrug.

Six states, and every one of them is reachable and reported separately:

``complete``    filed, valid, substantive, ``status = "complete"``.
``partial``     the same, with ``status = "partial"``.
``vacuous``     filed and structurally valid, and every narrative field is a
                placeholder. **This is deliberately not an error.** A stub filed
                by an agent that knew it was about to die is worth more than
                nothing and must be recordable; what it may not do is read as a
                finished report. Refusing it would buy filler prose, which is the
                opposite of the point.
``invalid``     filed and refused by the schema -- a missing field, an unknown
                key, eleven claims instead of twelve.
``unreadable``  on disk and not parseable. A writer killed *mid-write* lands
                here, and it is a different fact from ``absent``.
``absent``      on the roster and not on disk.

:func:`write_summary` writes through a temporary file and :func:`os.replace`, so
a *killed* writer using it leaves either nothing or a whole file and never a
half one. ``unreadable`` exists because agents also write with shell heredocs
and editor tools, which are not atomic.

Why the round directory lives in ``.github/``
---------------------------------------------
``.github/run-summaries/<round>/``, beside ``.github/gates.toml``, and the
reason is the same reason ``docs/POSITIONING.md`` is in ``docs/``: mechanical,
not aesthetic.

* It is **process apparatus about CI**, not documentation about the library.
  ``CONTRIBUTING.md`` holds every file under ``docs/`` (bar three) to a cold
  read by a second person; a round's raw self-assessment is not a page anybody
  is deciding whether to trust the library on, and putting it there would spend
  the cold-read rotation on machine records.
* ``MANIFEST.in`` ships ``docs/*.md``, so a round directory in ``docs/`` would
  be half-shipped -- the prose in the sdist and the JSON not. Here the whole
  directory ships, by an explicit ``recursive-include``, for the reason
  ``.github/gates.toml`` and ``docs/cold-reads.toml`` already ship: a gate that
  reads a register and a distribution that omits it is a shipped checker that
  cannot pass. **This paragraph said the opposite when it was written** -- "here
  nothing ships, deliberately" -- and
  ``tests/test_packaging_manifest.py`` refuted it in the same commit, because
  ``.github/gates.toml`` names the round file as a mutation target and every
  such path must be shipped.
* It is **outside** ``tools/check_claims.py``'s ``SCAN_GLOBS``, and that is a
  hole rather than a feature. See *How this fails*.

Naming: ``<label>.json`` where the stem **must equal** the ``label`` inside.
The filename is the only part of a record that survives a truncated write, so it
carries the identity; and a label that disagrees with its filename is the
signature of two agents racing on one path, which D-098 reports happening to a
shared scratchpad already.

How this fails
--------------
**This makes a lost report recoverable. It does not make a report happen.** An
agent that dies before its penultimate tool call files nothing, and *no gate in
this repository can tell that from an agent that was never launched.* The roster
narrows it -- it says who was *expected* -- and narrowing is not closing: a
roster is written by hand before the round, so "launched and died at once" and
"never launched" still produce the same ``absent``. Closing it needs something
outside this repository: a launcher that writes a start record when it spawns an
agent, so ``absent`` splits into *started and never filed* and *never started*.
That is a change to whatever runs the round, and nothing here can make it.

**A JSON summary an agent writes about itself is still self-assessment.** It is
cheaper to write than prose and it is not more trustworthy; the measured
not-true rate on sampled claims from this output is 18.75 %. This module checks
*shape*, and the one content rule it has -- that a dotted ``run_ids`` entry
resolves in ``bench/results.json`` -- is a check on citation, not on truth.

**Numbers inside a summary are ungated.** ``.github/run-summaries/`` is in none
of ``tools/check_claims.py``'s seven ``SCAN_GLOBS``, so a ``claims_for_sampling``
sentence reading *"F1 rose to 99.9 %"* is an unbacked claim that nothing reddens.
That is the same shape as the figure hole R16 was written for, one channel
further out. Adding the glob is a change to a ratchet this module does not own
and it is not made here; it is named so the next round can price it.

**The roster is the weakest link and it is unguarded.** Nothing checks that the
roster names every workstream that was actually launched. A workstream missing
from the roster is invisible in exactly the way this module exists to prevent,
and ``roster_complete`` is a self-report about a self-report.

Usage::

    python tools/run_summary.py --check                 # the CI gate
    python tools/run_summary.py --report DIR            # reconstruct a round
    python tools/run_summary.py --report DIR --strict   # ... and exit 1 if any gap
    python tools/run_summary.py --validate FILE         # one summary
    python tools/run_summary.py --template LABEL        # a skeleton to fill in

Nothing here is imported by the library, and nothing here touches the network.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Where committed rounds live. See the module docstring for why ``.github``.
ROUNDS_ROOT = REPO_ROOT / ".github" / "run-summaries"

#: The roster file inside a round directory. Absent it, the round is not
#: reconstructible at all, and ``--report`` says so and exits 2 rather than
#: printing an empty table that reads like a clean round.
ROSTER_NAME = "round.toml"

#: The substring ``.github/gates.toml`` declares as this gate's
#: ``expect_failure_matching``. A marker that drifts turns every future
#: demonstration into ``INERT`` while the register goes on reporting a gate
#: nobody can demonstrate, so ``tests/test_run_summary.py`` pins the two copies
#: against each other.
FAILURE_MARKER = "run-summary register refused"

#: A workstream label, and the stem of its file. Lowercase because the stem is
#: compared to it on a case-insensitive filesystem, where ``A.json`` and
#: ``a.json`` are one file and two labels.
LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

#: What ``status`` may say. Two values, not three: there is no ``failed``,
#: because a workstream that got nowhere still files ``partial`` and says so in
#: ``not_done``. A third value would be a place to hide.
STATUS_VALUES: Tuple[str, ...] = ("complete", "partial")

#: The gate keys every summary reports.
#:
#: **EIGHT, WHERE THE MAINTAINER'S SKETCH HAD SEVEN, AND THE EIGHTH IS THE
#: HARDENING.** The sketch collapsed ``ruff check`` and ``ruff format --check``
#: into one ``ruff`` key. They are two gates in ``.github/gates.toml``
#: (``gates.ruff`` and ``gates.ruff_format``), they run as two steps of the
#: ``lint`` job, and they fail for unrelated reasons -- one is lint, one is
#: whitespace. One key for two commands lets an agent write ``"ruff": "green"``
#: truthfully while the formatter is red, which is the arming asymmetry D-060
#: found in the claims gate, in a smaller place.
#:
#: **There is no ``run_summary`` key, and its absence is deliberate rather than
#: an oversight.** ``python tools/run_summary.py --check`` is a command in
#: ``CONTRIBUTING.md``'s gate block as of this commit, and it is not here because
#: the brief every agent of this round was handed lists eight gates. Adding a
#: ninth key would make every summary written to the standing brief ``invalid``
#: mid-round, which is a schema change wearing a consistency fix's clothes. The
#: key lands when the brief lists nine.
GATE_KEYS: Tuple[str, ...] = (
    "pytest",
    "ruff",
    "ruff_format",
    "mypy",
    "claims",
    "splits",
    "gates",
    "second_reader",
)

#: How many sentences ``claims_for_sampling`` carries. Exactly, not at least:
#: the sampled-verification rounds draw a fixed number and a field that may be
#: short is a field an agent under pressure makes short.
CLAIMS_REQUIRED = 12

#: Below this many characters a narrative field is a placeholder rather than an
#: answer. Twenty is a judgement and it is deliberately low: the rule decides
#: whether a summary is reported as ``vacuous``, never whether it is refused, so
#: a false positive costs a label in a table and not a rejected record.
MIN_NARRATIVE = 20

#: Text that is present and says nothing. Compared after lowercasing and
#: stripping.
DEAD_PHRASES = frozenset({"", "-", "--", "...", "n/a", "na", "none", "tbd", "todo", "?"})

#: Field name -> the kind of value it takes. Ordered, because ``--template``
#: emits them in this order and ``CONTRIBUTING.md`` publishes the same list.
REQUIRED_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("label", "slug"),
    ("status", "status"),
    ("headline", "text"),
    ("shipped", "lines"),
    ("run_ids", "lines"),
    ("files_changed", "lines"),
    ("pre_registration", "text"),
    ("how_it_fails", "text"),
    ("not_done", "lines"),
    ("gates", "gates"),
    ("claims_for_sampling", "claims"),
)

#: The field names alone, in order.
FIELD_NAMES: Tuple[str, ...] = tuple(name for name, _ in REQUIRED_FIELDS)

#: The narrative fields vacuity is decided on. ``headline`` is the sentence a
#: reader meets first; ``pre_registration`` and ``how_it_fails`` are the two
#: fields a round cannot fake cheaply.
NARRATIVE_FIELDS: Tuple[str, ...] = ("headline", "pre_registration", "how_it_fails")

#: Roster keys. Unknown keys are refused here too -- a misspelt
#: ``roster_complete`` would silently become ``False`` and turn a refusal into a
#: shrug.
ROSTER_REQUIRED: Tuple[str, ...] = ("round", "roster_written_by", "roster_complete", "expected")
ROSTER_OPTIONAL: Tuple[str, ...] = ("note",)

#: Worst last. ``--report`` prints in this order and :func:`RoundReport.worst`
#: reads the end of it.
STATES: Tuple[str, ...] = ("complete", "partial", "vacuous", "invalid", "unreadable", "absent")

#: The anchor in ``CONTRIBUTING.md`` before the fenced copy of
#: :data:`FIELD_NAMES`. An HTML comment rather than a heading, because a heading
#: is prose somebody will reword and an anchor is not.
CONTRIBUTING_ANCHOR = "<!-- run-summary:fields -->"


class RunSummaryError(Exception):
    """The round could not be read, or names something that does not exist."""


def _load_toml(path: Path) -> Dict[str, Any]:
    """Parse ``path`` as TOML on any supported interpreter.

    Same reasoning, and the same house guard, as ``tools/splits.py`` and
    ``tools/gates.py``: ``tomllib`` is 3.11+ and ``requires-python`` is
    ``>=3.9``, so on 3.9 and 3.10 there may be no parser at all. That is an
    error and never a silent pass -- a reader that reports a clean round because
    it could not read the roster is the exact defect this module exists to end.
    """
    if sys.version_info >= (3, 11):
        import tomllib as _toml
    else:  # pragma: no cover - 3.9/3.10 path
        try:
            import tomli as _toml
        except ImportError as error:
            raise RunSummaryError(
                "no TOML parser available: tomllib is 3.11+ and tomli is not installed. "
                f"Cannot read the roster {path}."
            ) from error
    try:
        with path.open("rb") as handle:
            return _toml.load(handle)
    except OSError as error:
        raise RunSummaryError(f"{path}: {error}") from error
    except Exception as error:  # pragma: no cover - malformed TOML
        raise RunSummaryError(f"{path}: not valid TOML: {error}") from error


def is_placeholder(value: str) -> bool:
    """Whether a narrative field is present and says nothing."""
    stripped = value.strip()
    return stripped.lower() in DEAD_PHRASES or len(stripped) < MIN_NARRATIVE


def _problems_for(name: str, kind: str, value: Any) -> List[str]:
    """Every way one field of one summary is wrong."""
    problems: List[str] = []
    if kind in ("slug", "status", "text"):
        if not isinstance(value, str):
            return [f"{name!r} must be a string, not {type(value).__name__}"]
        if kind == "slug" and not LABEL_RE.match(value):
            problems.append(
                f"{name!r} is {value!r}, which is not a label matching {LABEL_RE.pattern}"
            )
        if kind == "status" and value not in STATUS_VALUES:
            problems.append(f"status {value!r} is not one of {list(STATUS_VALUES)}")
        return problems
    if kind == "lines":
        if not isinstance(value, list):
            return [f"{name!r} must be a list of strings, not {type(value).__name__}"]
        for index, item in enumerate(value):
            if not isinstance(item, str):
                problems.append(f"{name}[{index}] is {type(item).__name__}, not a string")
        return problems
    if kind == "claims":
        if not isinstance(value, list):
            return [f"{name!r} must be a list of strings, not {type(value).__name__}"]
        if len(value) != CLAIMS_REQUIRED:
            problems.append(
                f"{name!r} carries {len(value)} sentence(s); exactly {CLAIMS_REQUIRED} are required"
            )
        for index, item in enumerate(value):
            if not isinstance(item, str):
                problems.append(f"{name}[{index}] is {type(item).__name__}, not a string")
            elif not item.strip():
                problems.append(f"{name}[{index}] is blank")
        return problems
    if kind == "gates":
        if not isinstance(value, dict):
            return [f"{name!r} must be an object, not {type(value).__name__}"]
        missing = [key for key in GATE_KEYS if key not in value]
        unknown = [str(key) for key in value if key not in GATE_KEYS]
        if missing:
            problems.append(f"{name!r} does not report {missing}")
        if unknown:
            problems.append(f"{name!r} reports unknown gate(s) {sorted(unknown)}")
        for key, reported in value.items():
            if not isinstance(reported, str):
                problems.append(f"{name}[{key!r}] is {type(reported).__name__}, not a string")
        return problems
    raise RunSummaryError(f"no validator for field kind {kind!r}")  # pragma: no cover


def validate_summary(payload: Any, stem: Optional[str] = None) -> List[str]:
    """Every way ``payload`` is not a run summary.

    Args:
        payload: The decoded JSON.
        stem: The filename stem it was read from, when it came from a file. The
            stem and the ``label`` must agree; a disagreement is what two agents
            racing on one path looks like from the outside.

    Returns:
        A list of problems, empty when the payload is valid. Vacuity is **not**
        a problem: see :func:`state_of`.
    """
    if not isinstance(payload, dict):
        return [f"a run summary is a JSON object, not {type(payload).__name__}"]
    problems: List[str] = []
    for name, kind in REQUIRED_FIELDS:
        if name not in payload:
            problems.append(f"{name!r} is missing")
            continue
        problems.extend(_problems_for(name, kind, payload[name]))
    unknown = sorted(str(key) for key in payload if key not in FIELD_NAMES)
    if unknown:
        problems.append(
            f"unknown key(s) {unknown}. A misspelt field is a dropped field, which is how "
            "bench/splits.toml lost the one value its structure existed to require."
        )
    if stem is not None:
        label = payload.get("label")
        if isinstance(label, str) and label != stem:
            problems.append(
                f"label {label!r} does not match the filename stem {stem!r}. The stem is the "
                "only identity a truncated write preserves."
            )
    return problems


def is_vacuous(payload: Mapping[str, Any]) -> bool:
    """Whether every narrative field of a *valid* summary is a placeholder.

    ``every``, not ``any``, and the choice is conservative on purpose: one
    substantive narrative field is enough to be a report. The exhaustive word
    was checked by counting both sides of :data:`NARRATIVE_FIELDS`.
    """
    return all(is_placeholder(str(payload.get(name, ""))) for name in NARRATIVE_FIELDS)


def state_of(payload: Mapping[str, Any], problems: Sequence[str]) -> str:
    """The verdict for a summary that is on disk and was decoded."""
    if problems:
        return "invalid"
    if is_vacuous(payload):
        return "vacuous"
    status = str(payload.get("status", ""))
    return status if status in STATES else "invalid"


@dataclass(frozen=True)
class Verdict:
    """What is on disk for one workstream, and what it amounts to."""

    label: str
    state: str
    path: Optional[Path] = None
    problems: Tuple[str, ...] = ()
    headline: str = ""

    @property
    def filed(self) -> bool:
        """Whether anything at all reached the disk under this label."""
        return self.state != "absent"


@dataclass(frozen=True)
class Roster:
    """Who was supposed to file. The thing that makes ``absent`` sayable."""

    path: Path
    round: str
    roster_written_by: str
    roster_complete: bool
    expected: Tuple[str, ...]
    note: str = ""


@dataclass(frozen=True)
class RoundReport:
    """A round, reconstructed from a directory."""

    directory: Path
    roster: Optional[Roster]
    roster_problems: Tuple[str, ...]
    verdicts: Tuple[Verdict, ...]
    unexpected: Tuple[Verdict, ...]

    def counts(self) -> Dict[str, int]:
        """How many workstreams landed in each state, every state present."""
        tally = dict.fromkeys(STATES, 0)
        for verdict in self.verdicts:
            tally[verdict.state] = tally.get(verdict.state, 0) + 1
        return tally

    @property
    def reconstructible(self) -> bool:
        """Whether this directory is a round at all."""
        return self.roster is not None and not self.roster_problems

    @property
    def gaps(self) -> Tuple[Verdict, ...]:
        """Every workstream whose account is missing, empty or broken."""
        return tuple(v for v in self.verdicts if v.state not in ("complete", "partial"))


def load_roster(directory: Path) -> Tuple[Optional[Roster], List[str]]:
    """Read ``round.toml``, or say why the round cannot be reconstructed."""
    path = directory / ROSTER_NAME
    if not path.is_file():
        return None, [
            f"{directory}: no {ROSTER_NAME}. Without a roster an empty directory cannot be "
            "told from a round nobody filed for, which is the distinction D-096 measured the "
            "cost of."
        ]
    try:
        raw = _load_toml(path)
    except RunSummaryError as error:
        return None, [str(error)]

    problems: List[str] = []
    missing = [key for key in ROSTER_REQUIRED if key not in raw]
    if missing:
        problems.append(f"{path}: roster does not declare {missing}")
    unknown = sorted(str(key) for key in raw if key not in ROSTER_REQUIRED + ROSTER_OPTIONAL)
    if unknown:
        problems.append(f"{path}: unknown roster key(s) {unknown}")
    expected = raw.get("expected", [])
    if not isinstance(expected, list) or not all(isinstance(item, str) for item in expected):
        problems.append(f"{path}: 'expected' must be a list of labels")
        expected = []
    for label in expected:
        if not LABEL_RE.match(str(label)):
            problems.append(f"{path}: expected label {label!r} is not a slug")
    duplicates = sorted({str(x) for x in expected if list(expected).count(x) > 1})
    if duplicates:
        problems.append(f"{path}: 'expected' names {duplicates} more than once; labels are ids")
    if not isinstance(raw.get("roster_complete", False), bool):
        problems.append(f"{path}: 'roster_complete' must be a boolean")
    if problems:
        return None, problems
    return (
        Roster(
            path=path,
            round=str(raw["round"]),
            roster_written_by=str(raw["roster_written_by"]),
            roster_complete=bool(raw["roster_complete"]),
            expected=tuple(str(item) for item in expected),
            note=str(raw.get("note", "")),
        ),
        [],
    )


def read_summary(path: Path) -> Verdict:
    """One file on disk, decoded and judged.

    A file that is present and undecodable is ``unreadable`` and **not**
    ``absent``. That difference is the whole reason this returns a verdict
    rather than an ``Optional``.
    """
    label = path.stem
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return Verdict(label, "unreadable", path, (f"{path}: {error}",))
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        return Verdict(
            label,
            "unreadable",
            path,
            (
                f"{path}: not decodable JSON at line {error.lineno} column {error.colno} "
                f"({error.msg}). {len(text)} byte(s) on disk -- a writer killed mid-write "
                "lands here, and that is a different fact from having filed nothing.",
            ),
        )
    problems = validate_summary(payload, stem=label)
    state = state_of(payload if isinstance(payload, dict) else {}, problems)
    headline = ""
    if isinstance(payload, dict) and isinstance(payload.get("headline"), str):
        headline = str(payload["headline"])
    return Verdict(label, state, path, tuple(problems), headline)


def report(directory: Path) -> RoundReport:
    """Reconstruct a round from ``directory``.

    Every roster label gets exactly one verdict, ``absent`` included, and every
    ``*.json`` that is not on the roster is reported separately rather than
    dropped. A file nobody expected is as interesting as a file nobody wrote.
    """
    roster, roster_problems = load_roster(directory)
    on_disk: Dict[str, Verdict] = {}
    if directory.is_dir():
        for path in sorted(directory.glob("*.json")):
            verdict = read_summary(path)
            on_disk[verdict.label] = verdict
    expected = roster.expected if roster is not None else ()
    verdicts = tuple(on_disk.get(label, Verdict(label, "absent")) for label in expected)
    unexpected = tuple(
        verdict for label, verdict in sorted(on_disk.items()) if label not in expected
    )
    return RoundReport(
        directory=directory,
        roster=roster,
        roster_problems=tuple(roster_problems),
        verdicts=verdicts,
        unexpected=unexpected,
    )


def write_summary(path: Path, payload: Mapping[str, Any]) -> None:
    """Validate, then write ``payload`` so a kill cannot leave half of it.

    Written to a temporary file in the same directory and moved into place with
    :func:`os.replace`, which is atomic on both platforms this project runs on.
    A writer killed while using this leaves either the old file or the whole new
    one. Agents that write with a shell heredoc get no such guarantee, which is
    why ``unreadable`` is a state.
    """
    problems = validate_summary(payload, stem=path.stem)
    if problems:
        raise RunSummaryError(f"{path}: refusing to write an invalid summary: {problems}")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False, sort_keys=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def template(label: str) -> Dict[str, Any]:
    """A skeleton with every field present and nothing said.

    It is deliberately :func:`is_vacuous` -- a template that read as a finished
    report would be the worst possible default. The twelve claim slots carry
    placeholder text rather than empty strings, because a blank claim is
    *refused* and a template that cannot be validated is a template nobody can
    check before filling in.
    """
    return {
        "label": label,
        "status": "partial",
        "headline": "",
        "shipped": [],
        "run_ids": [],
        "files_changed": [],
        "pre_registration": "",
        "how_it_fails": "",
        "not_done": [],
        "gates": dict.fromkeys(GATE_KEYS, ""),
        "claims_for_sampling": [
            f"(claim {n} of {CLAIMS_REQUIRED} -- replace with a checkable sentence)"
            for n in range(1, CLAIMS_REQUIRED + 1)
        ],
    }


def documented_fields(contributing: Path) -> List[str]:
    """The field list published in ``CONTRIBUTING.md``, as it is written there.

    A list of fields in a document is exactly the kind of prose no gate reads,
    and this project has the measurement: ``CONTRIBUTING.md`` told a reader
    there were six gates while the ``lint`` job ran seven, for as long as
    ``tools/gates.py`` had existed. So this copy is read.
    """
    text = contributing.read_text(encoding="utf-8")
    at = text.find(CONTRIBUTING_ANCHOR)
    if at < 0:
        raise RunSummaryError(f"{contributing}: no {CONTRIBUTING_ANCHOR} anchor")
    opening = text.index("```", at)
    body_start = text.index("\n", opening)
    closing = text.index("```", body_start)
    return [line.strip() for line in text[body_start:closing].splitlines() if line.strip()]


def _known_run_ids(results: Path) -> Optional[frozenset]:
    """Every run id ``bench/results.json`` carries, or ``None`` if it is absent."""
    if not results.is_file():
        return None
    try:
        payload = json.loads(results.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    runs = payload.get("runs")
    if not isinstance(runs, dict):
        return None
    return frozenset(str(key) for key in runs)


def _run_id_problems(verdict: Verdict, known: Optional[frozenset]) -> List[str]:
    """A dotted run id in a summary that no measurement carries.

    Only dotted ids are checked. A bare number is a CI run id -- ``34308556192``
    -- which lives in the Actions tab and not in ``bench/results.json``, and a
    rule that demanded both would be wrong about half its inputs.
    """
    if known is None or verdict.path is None or verdict.state in ("absent", "unreadable"):
        return []
    try:
        payload = json.loads(verdict.path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):  # pragma: no cover - already reported
        return []
    if not isinstance(payload, dict):  # pragma: no cover - already reported
        return []
    problems: List[str] = []
    for entry in payload.get("run_ids", []) or []:
        if not isinstance(entry, str) or "." not in entry:
            continue
        if not any(key == entry or key.startswith(entry + ".") for key in known):
            problems.append(
                f"{verdict.path}: run id {entry!r} resolves to no run in bench/results.json. "
                "A cited id that names nothing is operating rule 1 applied to a self-assessment."
            )
    return problems


def check(root: Path = REPO_ROOT) -> List[str]:
    """The CI gate: every committed round, and the copy of the schema in prose.

    What is **not** a problem here, and the omission is the design: ``absent``
    and ``vacuous``. A round in which an agent died must stay committable
    exactly as it happened, or the only way to a green build is to delete the
    roster entry -- which would turn this gate into a machine for hiding the
    thing it was built to reveal. Those two states are printed, loudly, and they
    do not fail the build.
    """
    problems: List[str] = []
    rounds_root = root / ".github" / "run-summaries"
    directories = (
        sorted(p for p in rounds_root.glob("*") if p.is_dir()) if rounds_root.is_dir() else []
    )
    if not directories:
        problems.append(
            f"  {rounds_root} holds no round. This gate is over a register, and a register "
            "with nothing in it passes vacuously -- which is the state D-096 measured the cost "
            "of. Commit the round's directory, roster included."
        )
    known = _known_run_ids(root / "bench" / "results.json")
    for directory in directories:
        summary = report(directory)
        problems.extend(f"  {line}" for line in summary.roster_problems)
        if summary.roster is None:
            continue
        for verdict in summary.verdicts:
            for line in verdict.problems:
                problems.append(f"  {directory.name}/{verdict.label}: {line}")
            problems.extend(f"  {line}" for line in _run_id_problems(verdict, known))
        for verdict in summary.unexpected:
            if summary.roster.roster_complete:
                problems.append(
                    f"  {directory.name}: {verdict.label!r} filed a summary and is not on a "
                    "roster that declares itself complete. Either the roster is wrong or the "
                    "file is."
                )
            for line in verdict.problems:
                problems.append(f"  {directory.name}/{verdict.label}: {line}")

    contributing = root / "CONTRIBUTING.md"
    if contributing.is_file():
        try:
            published = documented_fields(contributing)
        except (RunSummaryError, ValueError) as error:
            problems.append(f"  {error}")
        else:
            if published != list(FIELD_NAMES):
                problems.append(
                    f"  CONTRIBUTING.md publishes {published} and tools/run_summary.py requires "
                    f"{list(FIELD_NAMES)}. A field list in a document that nothing reads is how "
                    "that file told contributors there were six gates while CI ran seven."
                )
    return problems


def render(summary: RoundReport) -> str:
    """The round as a table, worst last, with the roster's own limits printed."""
    lines: List[str] = []
    if summary.roster is None:
        # WHAT SURVIVED IS STILL PRINTED. A reader whose whole job is recovering
        # a round from disk after the reports were lost may not go silent on the
        # directory that matters most -- the one nobody set a roster up for, such
        # as a shared scratchpad an agent wrote into under pressure. What is lost
        # without a roster is the ABSENCES, and only those.
        lines.append(f"{summary.directory}: NOT RECONSTRUCTIBLE")
        lines.extend(f"  {line}" for line in summary.roster_problems)
        if summary.unexpected:
            lines.append(f"  {len(summary.unexpected)} summary file(s) are on disk regardless:")
            for found in summary.unexpected:
                headline = found.headline.strip()
                if len(headline) > 60:
                    headline = headline[:57] + "..."
                lines.append(f"    {found.label:<28} {found.state.upper():<11} {headline}")
        else:
            lines.append("  and no summary is on disk either.")
        lines.append(
            "  NOTE: with no roster, `absent` is not computable at all -- a directory nobody "
            "filed into and a round nobody launched are the same directory."
        )
        return "\n".join(lines)
    roster = summary.roster
    lines.append(f"round {roster.round!r}  ({summary.directory})")
    # First line only: `roster_written_by` is a free-text field and a roster that
    # explains itself at length would push the table off the screen.
    author = (
        roster.roster_written_by.strip().splitlines()[0]
        if roster.roster_written_by.strip()
        else "?"
    )
    lines.append(f"  roster by {author!r}, {len(roster.expected)} workstream(s)")
    order = {state: index for index, state in enumerate(STATES)}
    for verdict in sorted(summary.verdicts, key=lambda v: (order.get(v.state, 99), v.label)):
        headline = verdict.headline.strip()
        if len(headline) > 68:
            headline = headline[:65] + "..."
        lines.append(f"  {verdict.label:<28} {verdict.state.upper():<11} {headline}")
        for problem in verdict.problems[:3]:
            lines.append(f"      {problem}")
    for verdict in summary.unexpected:
        lines.append(f"  {verdict.label:<28} {'UNEXPECTED':<11} not on the roster")
    tally = summary.counts()
    lines.append(
        "  "
        + ", ".join(f"{state} {tally[state]}" for state in STATES)
        + (f", unexpected {len(summary.unexpected)}" if summary.unexpected else "")
    )
    if not roster.roster_complete:
        lines.append(
            "  NOTE: roster_complete = false. The absences above are a LOWER BOUND -- a "
            "workstream nobody listed is invisible here."
        )
    lines.append(
        "  NOTE: `absent` means no summary reached this directory. It does NOT distinguish an "
        "agent that died before filing from one that was never launched; nothing in this "
        "repository can."
    )
    return "\n".join(lines)


def _as_json(summary: RoundReport) -> str:
    return json.dumps(
        {
            "directory": str(summary.directory),
            "round": summary.roster.round if summary.roster else None,
            "roster_complete": summary.roster.roster_complete if summary.roster else None,
            "roster_problems": list(summary.roster_problems),
            "counts": summary.counts(),
            "verdicts": [
                {
                    "label": v.label,
                    "state": v.state,
                    "path": str(v.path) if v.path else None,
                    "problems": list(v.problems),
                    "headline": v.headline,
                }
                for v in summary.verdicts
            ],
            "unexpected": [{"label": v.label, "state": v.state} for v in summary.unexpected],
        },
        indent=2,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command line entry point."""
    parser = argparse.ArgumentParser(
        prog="run_summary.py",
        description=(
            "Validate a round's machine-readable self-assessment, and reconstruct a round "
            "from disk when the reports are missing."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="the CI gate: validate every committed round and the schema copy in CONTRIBUTING.md",
    )
    parser.add_argument("--report", metavar="DIR", help="reconstruct the round in DIR")
    parser.add_argument("--validate", metavar="FILE", help="validate one summary file")
    parser.add_argument("--template", metavar="LABEL", help="print an empty summary to fill in")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="with --report, exit 1 when any workstream is absent, empty or broken",
    )
    parser.add_argument("--root", default=str(REPO_ROOT), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.template:
        print(json.dumps(template(args.template), indent=2))
        return 0

    if args.validate:
        verdict = read_summary(Path(args.validate))
        if args.json:
            print(
                json.dumps({"state": verdict.state, "problems": list(verdict.problems)}, indent=2)
            )
        else:
            print(f"{args.validate}: {verdict.state.upper()}")
            for problem in verdict.problems:
                print(f"  {problem}")
        return 0 if verdict.state in ("complete", "partial", "vacuous") else 1

    if args.report:
        summary = report(Path(args.report))
        print(_as_json(summary) if args.json else render(summary))
        if not summary.reconstructible:
            return 2
        return 1 if (args.strict and summary.gaps) else 0

    if args.check:
        root = Path(args.root)
        problems = check(root)
        rounds_root = root / ".github" / "run-summaries"
        directories = (
            sorted(p for p in rounds_root.glob("*") if p.is_dir()) if rounds_root.is_dir() else []
        )
        filed = gaps = 0
        for directory in directories:
            summary = report(directory)
            filed += sum(1 for v in summary.verdicts if v.filed)
            gaps += len(summary.gaps)
        if problems:
            print(f"{FAILURE_MARKER}: {len(problems)} problem(s)")
            for problem in problems:
                print(problem)
            return 1
        print(
            f"run summaries OK: {len(directories)} round(s), {filed} filed, {gaps} gap(s) "
            "(absent, empty or broken -- reported, never a build failure)"
        )
        print(
            "  note: a lost report is recoverable here; a report that never happened is not "
            "detectable here. See tools/run_summary.py's `How this fails`."
        )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
