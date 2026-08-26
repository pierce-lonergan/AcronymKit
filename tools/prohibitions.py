#!/usr/bin/env python3
"""Enumerate this project's prohibitions and sample the claims that justify them.

Why this exists
---------------
D-068 measured, for the first time, how often this project's own reporting is
wrong: ``5`` of ``24`` sampled incidental claims were not true, and the subset
that needed a derivation rather than a lookup failed at ``36.4 %``.

The do-not list is almost entirely derivation-requiring claims. "Covers
``1.124 %`` of real token occurrences", "measured sense coverage is ``4.72 %``",
"a *perfect* selector is worth about a point and a half" -- each is a number
somebody computed once, wrote down once, and nobody has recomputed since,
because the direction it closed is closed and nobody looks at closed
directions. **A wrongly-closed direction costs more than an open one.**

So this module does to the prohibitions what R15's sampler does to a round's
reporting: it states the denominator, draws a seeded sample, and hands the
sample to somebody who re-derives each item from source.

What a prohibition is, mechanically
-----------------------------------
Three strata, each with a stated extraction rule so the denominator can be
disputed rather than trusted:

* **A -- audit do-not items.** ``docs/AUDIT-2026-08.md``. A prohibition is (a)
  any occurrence of the bold lead ``**Do not ``, (b) any row of the table under
  *Five proposals that should not be built*, or (c) any bold-lead paragraph
  under *D. What should stay closed*.
* **B -- closed-direction decision records.** ``docs/DECISIONS.md``. A record is
  in the stratum when :data:`CLOSURE_MARKERS` matches its title line or the
  first segment of its ``**Status:**`` block -- the segment up to the first
  ``·``, which is the status proper rather than the cross-reference fields
  that follow it. Records the mechanical rule misses are added by hand through
  :data:`MANUAL_STRATUM_B`, which is published for exactly that reason.
* **C -- live prohibitions.** The Mandate II Phase IV *PROHIBITED* list and
  ``docs/POSITIONING.md``'s retirements. These are not figures in a file; they
  are standing instructions whose reasons live elsewhere. The stratum is small
  enough to be a **census**, so this module enumerates it and does not sample
  it.

What a claim is, mechanically
-----------------------------
Inside a stratum A or B span, every **free-standing number**: a numeric token
whose neighbouring characters are not alphanumeric or ``-_./``. That rule drops
``D-012``, ``MED1250``, ``2026-08-23`` and ``0.3.0`` -- identifiers and dates
rather than figures -- and keeps the numbers a reader would read as
measurements, including the ones inside code spans and fenced blocks, because
in this repository that is where measurements are written.

The span differs by stratum, and the difference is deliberate:

* **A** -- the whole prohibition, from its lead to the next lead, heading or
  horizontal rule. The case for an audit do-not item is made in the paragraph
  and the fenced block under it.
* **B** -- the record's title line, its status block, and every fenced block in
  the record. **Not** its prose. A closed record runs to a hundred lines of
  commentary; the fenced blocks are where it puts the measurements and the
  title is its head claim. This is a judgement, it narrows the denominator, and
  a reader who disagrees can pass ``--stratum-b-span=all``.

Sampling
--------
``random.Random(seed).sample`` over the frame sorted by claim id, drawn per
stratum so that stratum A -- the small, load-bearing one -- is not swamped by
stratum B. Both allocations are printed with the sample.

Usage
-----
``python tools/prohibitions.py --list``            the prohibitions, by stratum
``python tools/prohibitions.py --frame``           every claim in the frame
``python tools/prohibitions.py --sample``          the seeded sample
``python tools/prohibitions.py --check``           self-consistency, exit 1 on failure
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

AUDIT_DOC = "docs/AUDIT-2026-08.md"
DECISIONS_DOC = "docs/DECISIONS.md"

#: The seed for the sample. Published so the draw is reproducible. It is the
#: date the sample was drawn, in the same form D-068 used for its own seed.
DEFAULT_SEED = 20260825

#: How many claims to draw from each of the two sampled strata.
#:
#: Stratum A is a **census**: the audit's do-not items carry only ``35`` figures
#: between them, which is few enough to check every one, and a census has no
#: sampling error to argue about. ``--draw-a`` above the stratum size is
#: clamped to it, which is what makes ``35`` mean "all of them" rather than a
#: pinned count that goes stale when the audit is edited.
#:
#: Stratum B draws ``13`` from a frame two orders of magnitude larger. One
#: failure there moves that stratum's rate ``7.7`` points; the combined
#: ``48``-item pass moves ``2.1`` points per failure. D-068 checked ``24``.
DEFAULT_DRAW: Dict[str, int] = {"A": 35, "B": 13}

#: Words that mark a decision record as a closed direction, matched
#: case-insensitively against the title line and the first segment of the
#: status block.
#:
#: ``close`` catches "closed as unavailable" and "it closes a line of attack".
#: ``held`` catches D-032's "one shipped, one held, one reverted". ``shipped
#: unchanged`` catches the records that measured a change and did not take it.
CLOSURE_MARKERS: Tuple[str, ...] = (
    "reject",
    "refus",
    "revert",
    "close",
    "not adopted",
    "not shipped",
    "withdraw",
    "retire",
    "declin",
    "abandon",
    "not executed",
    "descope",
    "shipped unchanged",
    "held",
)

#: Records the mechanical rule misses, with the reason each is a closed
#: direction anyway. Published because a hand-added denominator entry is a
#: curation surface and hiding one would be the failure this module measures.
MANUAL_STRATUM_B: Dict[str, str] = {
    "D-001": "the record is itself a do-not list -- scope cut from the v0.2.0 mandate",
    "D-005": "CMUdict validated the heuristic and was not shipped as a table",
    "D-006": "fr/es/de ship no lexicon; a copyleft or invented one was refused",
    "D-007": "BALANCED_PRONOUNCEABLE was refused as the default",
    "D-056": "no corpus registered, no number published -- a registration refusal",
    "D-063": "the corpus that could never back a headline cannot be promoted by policy edit",
}

#: Records the mechanical rule catches whose closure word is incidental **and**
#: which say in their own status that they are open. Only that -- a record that
#: merely reads like a fix keeps its place in the denominator, because a
#: denominator trimmed by taste is the failure this module measures. Published
#: alongside :data:`MANUAL_STRATUM_B` so both edits to the population are
#: visible in one place.
MANUAL_STRATUM_B_EXCLUSIONS: Dict[str, str] = {
    "D-024": "'refuses to guess' describes the subsystem, not the decision; status leaves the tokenisation half open",
    "D-042": "'not a descope' is the record denying a closure; status is 'open fork, recorded rather than decided'",
}

#: Stratum C: the prohibitions that are live instructions rather than lines in
#: a document under ``docs/``. Enumerated in full and never sampled -- a census
#: is strictly better than a sample when the population is this small.
STRATUM_C: Tuple[Tuple[str, str], ...] = (
    ("C1", "no more Schwartz & Hearst descendants in any proposer pool"),
    ("C2", "no re-funding Federal Register legend extraction"),
    ("C3", "no registering the FR set under `held_out` or `tuning`"),
    ("C4", "no re-recording `micro.import` against a foreign environment"),
    ("C5", "no growing `EXPECTED_NON_PASSING`"),
    ("C6", "the three retired breadth sentences do not return in a gentler form"),
    ("C7", "nobody optimises the MED1250 extraction figure again"),
)

_HEADING = re.compile(r"^#{1,6} ")
_DO_NOT = re.compile(r"\*\*Do not ")
_RECORD = re.compile(r"^## (D-\d+) — (.*)$")
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_FENCE = re.compile(r"^\s*```")

_TABLE_SECTION = "### Five proposals that should not be built"
_CLOSED_SECTION = "### D. What should stay closed"

#: Which stratum letter each stratum B span mode produces. ``prose`` is the
#: complement of ``evidence`` inside the same records: everything that is not
#: the title, the status block or a fenced block. It exists because the
#: ``evidence`` rule selects the most checkable text in a record -- the fenced
#: blocks are where this project writes ``bench/results.json, <run id>`` -- so a
#: clean result there says nothing about the prose that surrounds it.
SPAN_MODE_STRATUM: Dict[str, str] = {"evidence": "B", "prose": "P", "all": "F"}


@dataclass(frozen=True)
class Prohibition:
    """One enumerated do-not, with the span its justification occupies."""

    pid: str
    stratum: str
    source: str
    line: int
    label: str
    start: int
    end: int


@dataclass(frozen=True)
class Claim:
    """One free-standing figure inside a prohibition's justification."""

    cid: str
    pid: str
    stratum: str
    source: str
    line: int
    figure: str
    context: str


def _read(rel: str, root: Path) -> List[str]:
    return (root / rel).read_text(encoding="utf-8").splitlines()


def free_standing_numbers(text: str) -> List[Tuple[int, str]]:
    """Return ``(column, figure)`` for every free-standing number in ``text``.

    Free-standing means the reader sees the number as a number: the characters
    either side are not alphanumeric and not one of ``-_./``. ``D-012``,
    ``MED1250``, ``2026-08-23`` and ``0.3.0`` are therefore not figures.
    """
    out: List[Tuple[int, str]] = []
    for match in _NUMBER.finditer(text):
        start, end = match.span()
        before = text[start - 1] if start else ""
        after = text[end] if end < len(text) else ""
        if before and (before.isalnum() or before in "-_./"):
            continue
        if after and (after.isalnum() or after in "-_/"):
            continue
        if after == "." and end + 1 < len(text) and text[end + 1].isdigit():
            continue
        out.append((start, match.group(0)))
    return out


def _audit_prohibitions(lines: Sequence[str]) -> List[Prohibition]:
    """Stratum A: the do-not items in the audit."""
    starts: List[Tuple[int, str]] = []
    in_table = False
    in_closed = False
    fenced = False
    for index, line in enumerate(lines):
        if _FENCE.match(line):
            fenced = not fenced
        if fenced:
            continue
        if line.startswith(_TABLE_SECTION):
            in_table, in_closed = True, False
            continue
        if line.startswith(_CLOSED_SECTION):
            in_table, in_closed = False, True
            continue
        if _HEADING.match(line):
            in_table = in_closed = False
        if (
            in_table
            and line.startswith("| ")
            and not line.startswith("| Proposal")
            and "---" not in line
        ):
            starts.append((index, line.split("|")[1].strip()))
            continue
        if in_closed and line.startswith("**"):
            starts.append((index, line.split("**")[1].strip()))
            continue
        if _DO_NOT.search(line):
            offset = line.index("**Do not ")
            starts.append((index, line[offset:].lstrip("*").strip()))
    boundaries = {index for index, _ in starts}
    out: List[Prohibition] = []
    for ordinal, (index, label) in enumerate(sorted(starts), start=1):
        end = len(lines)
        for probe in range(index + 1, len(lines)):
            if probe in boundaries or _HEADING.match(lines[probe]) or lines[probe].strip() == "---":
                end = probe
                break
        out.append(
            Prohibition(
                pid=f"A{ordinal:02d}",
                stratum="A",
                source=AUDIT_DOC,
                line=index + 1,
                label=label,
                start=index,
                end=end,
            )
        )
    return out


def _status_first_segment(body: Sequence[str]) -> str:
    block: List[str] = []
    started = False
    for line in body:
        if line.startswith("**Status:**"):
            started = True
        if started:
            if not line.strip():
                break
            block.append(line.strip())
    joined = " ".join(block)
    return joined.split("·")[0]


def _decision_prohibitions(lines: Sequence[str], span_mode: str) -> List[Prohibition]:
    """Stratum B: the decision records whose status closes a direction."""
    heads: List[Tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = _RECORD.match(line)
        if match:
            heads.append((index, match.group(1), match.group(2)))
    out: List[Prohibition] = []
    for ordinal, (index, rid, title) in enumerate(heads):
        end = heads[ordinal + 1][0] if ordinal + 1 < len(heads) else len(lines)
        body = lines[index + 1 : end]
        haystack = (title + " " + _status_first_segment(body)).lower()
        matched = any(marker in haystack for marker in CLOSURE_MARKERS)
        if rid in MANUAL_STRATUM_B_EXCLUSIONS:
            continue
        if not (matched or rid in MANUAL_STRATUM_B):
            continue
        out.append(
            Prohibition(
                pid=rid,
                stratum=SPAN_MODE_STRATUM[span_mode],
                source=DECISIONS_DOC,
                line=index + 1,
                label=title,
                start=index,
                end=end,
            )
        )
    out.sort(key=lambda p: p.pid)
    return out


def _decision_claim_lines(
    lines: Sequence[str], prohibition: Prohibition, span_mode: str
) -> List[int]:
    """Line indices inside a stratum B record that the claim frame reads."""
    if span_mode == "all":
        return list(range(prohibition.start, prohibition.end))
    body = lines[prohibition.start + 1 : prohibition.end]
    keep: List[int] = [prohibition.start]
    started = False
    for offset, line in enumerate(body):
        if line.startswith("**Status:**"):
            started = True
        if started:
            if not line.strip():
                break
            keep.append(prohibition.start + 1 + offset)
    fenced = False
    for offset, line in enumerate(body):
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            keep.append(prohibition.start + 1 + offset)
    if span_mode == "evidence":
        return sorted(set(keep))
    everything = set(range(prohibition.start, prohibition.end))
    return sorted(everything - set(keep))


def build_frame(
    root: Path = REPO_ROOT, span_mode: str = "evidence"
) -> Tuple[List[Prohibition], List[Claim]]:
    """Enumerate prohibitions and the claim frame drawn from them."""
    audit = _read(AUDIT_DOC, root)
    decisions = _read(DECISIONS_DOC, root)
    prohibitions = _audit_prohibitions(audit) + _decision_prohibitions(decisions, span_mode)
    claims: List[Claim] = []
    for prohibition in prohibitions:
        if prohibition.stratum == "A":
            lines = audit
            indices = list(range(prohibition.start, prohibition.end))
        else:
            lines = decisions
            indices = _decision_claim_lines(decisions, prohibition, span_mode)
        seen: set = set()
        ordinal = 0
        for index in indices:
            text = lines[index]
            for column, figure in free_standing_numbers(text):
                key = (index, column)
                if key in seen:
                    continue
                seen.add(key)
                ordinal += 1
                claims.append(
                    Claim(
                        cid=f"{prohibition.pid}.{ordinal:03d}",
                        pid=prohibition.pid,
                        stratum=prohibition.stratum,
                        source=prohibition.source,
                        line=index + 1,
                        figure=figure,
                        context=text.strip(),
                    )
                )
    claims.sort(key=lambda c: c.cid)
    return prohibitions, claims


def draw(claims: Sequence[Claim], seed: int, per_stratum: Dict[str, int]) -> List[Claim]:
    """Draw a seeded sample, allocated per stratum."""
    out: List[Claim] = []
    for stratum in sorted(per_stratum):
        pool = [c for c in claims if c.stratum == stratum]
        pool.sort(key=lambda c: c.cid)
        want = min(per_stratum[stratum], len(pool))
        rng = random.Random(f"{seed}:{stratum}")
        out.extend(rng.sample(pool, want))
    out.sort(key=lambda c: c.cid)
    return out


def _print_list(prohibitions: Sequence[Prohibition]) -> None:
    for stratum in sorted({p.stratum for p in prohibitions}):
        rows = [p for p in prohibitions if p.stratum == stratum]
        print(f"stratum {stratum}: {len(rows)} prohibition(s)")
        for row in rows:
            print(f"  {row.pid:<5} {row.source}:{row.line:<5} {row.label[:96]}")
    print(f"stratum C: {len(STRATUM_C)} prohibition(s)  (census, never sampled)")
    for cid, label in STRATUM_C:
        print(f"  {cid:<5} {'mandate/positioning':<24} {label}")
    total = len(prohibitions) + len(STRATUM_C)
    print(f"population: {total} prohibitions across 3 strata")


def _print_frame(claims: Sequence[Claim]) -> None:
    for claim in claims:
        print(f"{claim.cid}\t{claim.source}:{claim.line}\t{claim.figure}\t{claim.context[:120]}")
    for stratum in sorted({c.stratum for c in claims}):
        count = sum(1 for c in claims if c.stratum == stratum)
        print(f"stratum {stratum}: {count} claim(s)")
    print(f"frame: {len(claims)} claims")


def _print_sample(
    claims: Sequence[Claim], sample: Sequence[Claim], seed: int, per_stratum: Dict[str, int]
) -> None:
    print(
        f"seed {seed}; allocation " + ", ".join(f"{k}={v}" for k, v in sorted(per_stratum.items()))
    )
    for stratum in sorted({c.stratum for c in claims}):
        pool = sum(1 for c in claims if c.stratum == stratum)
        drawn = sum(1 for c in sample if c.stratum == stratum)
        rate = (drawn / pool * 100.0) if pool else 0.0
        print(f"stratum {stratum}: {drawn} of {pool} ({rate:.1f} % sampling fraction)")
    for claim in sample:
        print(f"{claim.cid}\t{claim.source}:{claim.line}\t{claim.figure}\t{claim.context[:140]}")


def _check(root: Path) -> int:
    """Self-consistency. Exit 1 when the enumeration cannot be trusted."""
    problems: List[str] = []
    prohibitions, claims = build_frame(root)
    ids = [p.pid for p in prohibitions]
    if len(ids) != len(set(ids)):
        problems.append("prohibition ids are not unique")
    cids = [c.cid for c in claims]
    if len(cids) != len(set(cids)):
        problems.append("claim ids are not unique")
    for prohibition in prohibitions:
        if prohibition.end <= prohibition.start:
            problems.append(f"{prohibition.pid}: empty span")
    if not any(p.stratum == "A" for p in prohibitions):
        problems.append("stratum A is empty; the audit's do-not markers stopped matching")
    if not any(p.stratum == "B" for p in prohibitions):
        problems.append("stratum B is empty; the closure markers stopped matching")
    missing = sorted(set(MANUAL_STRATUM_B) - set(ids))
    if missing:
        problems.append(f"manual stratum B entries not found in the document: {missing}")
    first = draw(claims, DEFAULT_SEED, DEFAULT_DRAW)
    second = draw(claims, DEFAULT_SEED, DEFAULT_DRAW)
    if [c.cid for c in first] != [c.cid for c in second]:
        problems.append("the draw is not reproducible")
    for problem in problems:
        print(f"prohibitions: {problem}")
    if problems:
        print("prohibitions: FAILED")
        return 1
    print(
        f"prohibitions OK: {len(prohibitions)} enumerated in A+B, {len(STRATUM_C)} in C, "
        f"{len(claims)} claims in the frame, draw reproducible at seed {DEFAULT_SEED}"
    )
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository root to read")
    parser.add_argument("--list", action="store_true", help="print the enumerated prohibitions")
    parser.add_argument("--frame", action="store_true", help="print every claim in the frame")
    parser.add_argument("--sample", action="store_true", help="print the seeded sample")
    parser.add_argument("--check", action="store_true", help="self-consistency check")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--draw-a", type=int, default=DEFAULT_DRAW["A"])
    parser.add_argument("--draw-b", type=int, default=DEFAULT_DRAW["B"])
    parser.add_argument(
        "--stratum-b-span",
        choices=tuple(SPAN_MODE_STRATUM),
        default="evidence",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    if args.check:
        return _check(root)
    prohibitions, claims = build_frame(root, span_mode=args.stratum_b_span)
    if args.list:
        _print_list(prohibitions)
    if args.frame:
        _print_frame(claims)
    if args.sample or not (args.list or args.frame):
        allocation = {"A": args.draw_a, SPAN_MODE_STRATUM[args.stratum_b_span]: args.draw_b}
        _print_sample(claims, draw(claims, args.seed, allocation), args.seed, allocation)
    return 0


if __name__ == "__main__":
    sys.exit(main())
