#!/usr/bin/env python3
"""Assert the bundled schema copy is byte-identical to the canonical one.

Why this is a script and not a heredoc
--------------------------------------
It used to be six lines of Python inside ``.github/workflows/ci.yml``'s
``resources`` job. That made it a gate **nothing could invoke** -- so
``.github/gates.toml`` recorded its mutation as ``kind = "inline"``, with the
disposition *"a harness could only run a COPY of it, and D-018 settled that a
copy may not stand in for the thing"*. A gate that cannot be invoked cannot be
mutated, and a gate that cannot be mutated has never been shown able to fail.

Extracting it changes nothing about what CI checks and everything about what can
be checked *about* CI: ``python tools/gates.py --mutate schema_copies_match``
now edits one byte of the bundled copy, runs this file, and requires it to exit
non-zero.

What it detects, and what it deliberately does not
--------------------------------------------------
Two copies of one contract. ``schemas/acronym-engine-result.schema.json`` is
the document a caller reads; ``src/acronymkit/resources/`` holds the copy that
ships in the wheel and that :func:`acronymkit.serialization.load_schema`
actually resolves. Inert, the shipped validator accepts what the documented
schema rejects, and a caller who wrote to the document is wrong in production
with no error anywhere.

**The comparison is a digest and not a semantic one, on purpose.** A trailing
newline is a divergence here and is not one to ``json.load``. That asymmetry is
real and it is the point: ``tests/test_serialization.py`` already asserts the
two copies are *semantically* equal, so a semantic check here would be the
second copy of an existing test rather than the only check on the bytes that
ship. The mutation registered against this gate is exactly one appended
newline, which this gate catches and that test does not.

Usage::

    python tools/gate_schema_copies.py

Only the standard library is imported: this runs in a job that installs the
package with no extras, and a gate that needs a dependency is a gate that can
fail for a reason it does not describe.

Exit codes:
    ``0`` the two copies are byte-identical, ``1`` they are not or one is
    missing.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The document a caller reads, and the copy that ships. Order matters only for
#: the ``cp`` hint printed on failure.
CANONICAL = Path("schemas/acronym-engine-result.schema.json")
BUNDLED = Path("src/acronymkit/resources/acronym-engine-result.schema.json")

#: Printed on every failure, and **required** by the gate's registered mutation
#: (``expect_failure_matching`` in ``.github/gates.toml``).
#:
#: A non-zero exit is not by itself evidence that a gate caught anything -- a
#: syntax error in this file would also exit non-zero, and would read as a
#: successful demonstration. The marker is what makes the verdict attributable
#: to the assertion rather than to the run.
FAILURE_MARKER = "SCHEMA COPIES DIVERGED"


def compare(root: Path = REPO_ROOT) -> Tuple[List[str], List[str]]:
    """Return ``(problems, report lines)`` for the two schema copies."""
    problems: List[str] = []
    report: List[str] = []
    digests = {}
    for relative in (CANONICAL, BUNDLED):
        path = root / relative
        if not path.is_file():
            problems.append(
                f"{FAILURE_MARKER}: {relative.as_posix()} does not exist, so the two copies "
                "cannot be compared and the shipped validator is unchecked."
            )
            continue
        digests[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    if problems:
        return problems, report
    for relative, digest in digests.items():
        report.append(f"{digest}  {relative.as_posix()}")
    if len(set(digests.values())) != 1:
        problems.append(
            f"{FAILURE_MARKER}: schemas/ and the bundled resource copy have diverged. "
            f"Run: cp {CANONICAL.as_posix()} {BUNDLED.as_posix()}"
        )
    return problems, report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)

    problems, report = compare(args.root)
    for line in report:
        print(line)
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    digest = report[0].split()[0] if report else ""
    print(f"schema copies match ({digest[:16]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
