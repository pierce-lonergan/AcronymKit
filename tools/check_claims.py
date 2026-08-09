#!/usr/bin/env python3
"""Fail the build when a performance or accuracy claim is not backed by a measurement.

Why this exists
---------------
A docstring in this repository once said a change "raises F1 from 84.78 to
89.87". The 89.87 was never measured — it was written while implementing the
change and would have shipped had it not been caught by hand. A rule that
depends on being caught by hand is not a rule.

So: every number that reads as a *claim* must be traceable to
``bench/results.json``, which only the benchmark runners write.

What counts as a claim
----------------------
A number adjacent to a claim keyword (``F1``, ``precision``, ``recall``,
``R@k``, ``docs/s``, ``us/call``, ``ms``) inside a scanned file. That keeps the
check narrow enough to be useful: ``max_length=6`` is not a claim, and neither
is a version number or a weight coefficient.

Three ways to satisfy the check:

1. The number appears in ``bench/results.json`` (matched to the precision
   written, so ``84.78`` matches a stored ``84.7812…``).
2. The line carries a trailing ``# measured: <run-id>`` / ``<!-- measured:
   <run-id> -->`` marker naming a results entry.
3. The number is listed in ``tools/claims_allowlist.txt`` with a reason —
   for historical results quoted in a changelog, or figures attributed to a
   published paper rather than claimed as ours.

Usage::

    python tools/check_claims.py            # scan and report
    python tools/check_claims.py --list     # show every claim found
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterator, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = REPO_ROOT / "bench" / "results.json"
ALLOWLIST_PATH = REPO_ROOT / "tools" / "claims_allowlist.txt"

#: Files scanned for claims. Deliberately not the whole tree: test files are
#: full of legitimate hard-coded numbers that are assertions, not claims.
SCAN_GLOBS = (
    "README.md",
    "docs/*.md",
    "docs/notes/*.md",
    "src/acronymkit/*.py",
    "src/acronymkit/**/*.py",
)

#: A number is a claim when it sits within this many characters of a keyword.
_PROXIMITY = 48

#: Keywords that turn a nearby number into a performance or accuracy claim.
_KEYWORDS = (
    "f1",
    "precision",
    "recall",
    "r@",
    "docs/s",
    "us/call",
    "µs/call",
    "throughput",
    "accuracy",
    "exact match",
    "mean absolute error",
)

_NUMBER = re.compile(r"\d+\.\d+|\d+(?:,\d{3})+|\b\d{2,}\b")
_MARKER = re.compile(r"(?:#|<!--)\s*measured:\s*([\w.\-]+)")


def load_results() -> dict:
    """Load the measured-results file.

    Returns:
        The parsed document, or an empty skeleton when it does not exist yet.
    """
    if not RESULTS_PATH.is_file():
        return {"runs": {}}
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


def iter_numbers(results: object) -> Iterator[float]:
    """Yield every numeric leaf in the results document."""
    if isinstance(results, dict):
        for value in results.values():
            yield from iter_numbers(value)
    elif isinstance(results, list):
        for value in results:
            yield from iter_numbers(value)
    elif isinstance(results, bool):
        return
    elif isinstance(results, (int, float)):
        yield float(results)


def load_allowlist() -> dict[str, str]:
    """Parse the allowlist into ``{number_text: reason}``.

    Format is ``<number>  <reason>`` per line; ``#`` comments and blanks ignored.
    """
    if not ALLOWLIST_PATH.is_file():
        return {}
    entries: dict[str, str] = {}
    for line in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        number, _, reason = line.partition(" ")
        entries[number.strip()] = reason.strip() or "(no reason given)"
    return entries


def _matches_measurement(text: str, measured: Sequence[float]) -> bool:
    """Whether ``text`` equals a measured value at the precision it is written.

    ``84.78`` matches a stored ``84.7812``; ``84.79`` does not. Integers with
    thousands separators are compared after stripping them.
    """
    cleaned = text.replace(",", "")
    try:
        claimed = float(cleaned)
    except ValueError:
        return False
    decimals = len(cleaned.partition(".")[2])
    for value in measured:
        if round(value, decimals) == claimed:
            return True
        # Percentages are stored as fractions in some runners.
        if round(value * 100, decimals) == claimed:
            return True
    return False


def scan_file(path: Path) -> Iterator[tuple[int, str, str]]:
    """Yield ``(line_number, number_text, line)`` for every claim in ``path``."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    for number, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        positions = [lowered.find(keyword) for keyword in _KEYWORDS]
        keyword_positions = [p for p in positions if p >= 0]
        if not keyword_positions:
            continue
        for match in _NUMBER.finditer(line):
            # A rank cutoff such as the "25" in "R@25" names a column; it is not
            # a claim about performance. Skip anything bound to an '@'.
            if match.start() and line[match.start() - 1] == "@":
                continue
            if any(abs(match.start() - position) <= _PROXIMITY for position in keyword_positions):
                yield number, match.group(0), line.strip()


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point.

    Returns:
        ``0`` when every claim is backed, ``1`` otherwise.
    """
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--list", action="store_true", help="print every claim found")
    args = parser.parse_args(argv)

    results = load_results()
    measured = sorted(set(iter_numbers(results)))
    allowlist = load_allowlist()

    if not measured:
        print(
            f"warning: {RESULTS_PATH.relative_to(REPO_ROOT)} holds no measurements.\n"
            "         Run the benchmarks with --save before relying on this check.",
            file=sys.stderr,
        )

    paths: list[Path] = []
    for pattern in SCAN_GLOBS:
        paths.extend(sorted(REPO_ROOT.glob(pattern)))

    unbacked: list[tuple[Path, int, str, str]] = []
    total = 0
    for path in sorted(set(paths)):
        for line_number, number, line in scan_file(path):
            total += 1
            if args.list:
                print(f"  {path.relative_to(REPO_ROOT)}:{line_number}  {number}")
            if _MARKER.search(line):
                continue
            if number in allowlist:
                continue
            if _matches_measurement(number, measured):
                continue
            unbacked.append((path, line_number, number, line))

    print(f"scanned {len(set(paths))} files, found {total} claim-shaped numbers")
    if not unbacked:
        print(f"all backed by {RESULTS_PATH.relative_to(REPO_ROOT)} or the allowlist")
        return 0

    print(f"\n{len(unbacked)} unbacked claim(s):\n", file=sys.stderr)
    for path, line_number, number, line in unbacked:
        print(f"  {path.relative_to(REPO_ROOT)}:{line_number}", file=sys.stderr)
        print(f"    {number!r} in: {line[:110]}", file=sys.stderr)
    print(
        "\nEvery performance or accuracy number must be traceable. Either:\n"
        "  - regenerate it into bench/results.json via a benchmark runner --save,\n"
        "  - mark the line 'measured: <run-id>' if it is a recorded historical result,\n"
        "  - or add it to tools/claims_allowlist.txt with a reason (published figures,\n"
        "    illustrative examples, changelog history).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
