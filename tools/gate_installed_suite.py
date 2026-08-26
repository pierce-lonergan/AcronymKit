#!/usr/bin/env python3
"""Adjudicate a pytest log produced by the installed-suite run.

Why this is a script and not a heredoc, and why that matters more here
----------------------------------------------------------------------
``.github/workflows/ci.yml``'s ``installed-suite`` job runs the whole suite
against the *installed* distribution and then applies a gate to the log: every
non-passing node id must be on a closed list of tests that structurally cannot
run without a source checkout, every entry on that list must actually have been
non-passing, and the pass count must clear a floor.

That gate used to live in a heredoc, and ``tools/gate_packaging_mutation.py``
carried a **second copy** of it -- the same set of node ids, the same floor and
a re-implementation of the same log parser -- so that the packaging mutation
harness could reproduce the job. The register recorded the cost of that beside
``gates.installed_expected_non_passing``: *"a reproduction is not the gate ...
the two can drift and nothing will say so."*

**A harness that re-implements the gate is testing its own copy.** The copy is
now gone. This file is the one implementation; ``ci.yml`` invokes it and
``tools/gate_packaging_mutation.py`` imports it. What remains reproduced rather
than invoked is the *sequence* around it -- build an sdist, install it into a
venv, lay out a run directory, run pytest -- and that residue is checked by
:func:`tools.gate_packaging_mutation.sequence_drift` rather than trusted.

What the list is, and what listing a file used to cost
-----------------------------------------------------
Every entry is a **missing guard in the test**, not a defect in the package, and
every entry is node-keyed. The two *file*-keyed entries this list used to carry
(``tests/test_check_claims.py`` and ``tests/test_splits_manifest.py``) were the
subject of D-058: while a file sat on this list, the job could not see a second
defect anywhere inside it, which was measured by reintroducing the fifth
historical packaging breakage and getting a log identical to a clean run. Both
now carry ``pytest.skip(..., allow_module_level=True)`` before the load instead.

Usage::

    python tools/gate_installed_suite.py path/to/pytest.log

Standard library only. It reads a log and returns a verdict; it does not run
anything, which is what makes it testable against a recorded log.

Exit codes:
    ``0`` the run is accounted for exactly, ``1`` it is not.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

#: Tests that CANNOT run from an installed package, and why.
#:
#: This is not a list of things that broke. It is the complete set of places
#: where this suite reaches for a source checkout, and the gate asserts it
#: EXACTLY: an entry that starts passing fails just as loudly as a test that
#: starts failing. The list cannot rot into a blanket exemption and it cannot be
#: grown by accident.
#:
#: The first two read the source text of ``src/acronymkit/__init__.py`` and
#: parse it with ``ast`` to check the lazy export table against the
#: ``TYPE_CHECKING`` block; an installed package has no source tree to read.
#: The remaining four assert on ``serialization.SCHEMA_PATH``, which is
#: ``<package>/../../schemas/...`` and therefore names the checkout copy by
#: construction.
EXPECTED_NON_PASSING = frozenset(
    {
        "tests/test_package.py::test_the_lazy_path_and_the_eager_path_expose_identical_names",
        "tests/test_package.py::test_every_lazy_export_is_the_object_its_own_module_defines",
        "tests/test_serialization.py::test_schema_path_points_at_the_checkout_copy",
        "tests/test_serialization.py::test_the_checkout_and_bundled_schema_copies_are_semantically_equal",
        "tests/test_serialization.py::test_load_schema_ignores_a_decoy_planted_at_the_schema_directory",
        "tests/test_serialization.py::test_validation_still_works_beside_a_hijacked_schema_directory",
    }
)

#: A floor, not a target. It exists so this gate cannot go green after something
#: quietly stops the suite from collecting -- a green job that ran eleven tests
#: would satisfy every other assertion here. Never lower this to make a red run
#: green.
PASS_FLOOR = 4_000

#: Printed on every failure. See ``tools/gate_schema_copies.py`` for why a
#: non-zero exit is not on its own an attributable verdict.
FAILURE_MARKER = "INSTALLED SUITE GATE FAILED"


def parse_log(log: str) -> Dict[str, Any]:
    """Node ids that did not pass, and the counts from pytest's last line."""
    observed: Set[str] = set()
    for line in log.splitlines():
        if not line.startswith(("FAILED ", "ERROR ")):
            continue
        # `FAILED <nodeid> - <reason>` / `ERROR <nodeid>` / `ERROR <file> - <exc>`
        nodeid = line.split(" ", 1)[1].split(" - ", 1)[0].strip()
        observed.add(nodeid.replace("\\", "/"))
    body = [line for line in log.splitlines() if line.strip()]
    summary = body[-1].strip().strip("=").strip() if body else ""
    counts = {word: int(n) for n, word in re.findall(r"(\d+) (\w+)", summary)}
    return {"observed": sorted(observed), "summary": summary, "counts": counts}


def adjudicate(
    log: str,
    expected: Sequence[str] = tuple(sorted(EXPECTED_NON_PASSING)),
    floor: int = PASS_FLOOR,
) -> Dict[str, Any]:
    """Apply the gate to one log. ``rc`` is what the CI step exits with."""
    got = parse_log(log)
    observed = set(got["observed"])
    wanted = set(expected)
    problems: List[str] = []

    unexpected = sorted(observed - wanted)
    if unexpected:
        problems.append(
            f"{FAILURE_MARKER}: these failed against the INSTALLED distribution and pass "
            "in a checkout:\n  "
            + "\n  ".join(unexpected)
            + "\n\nThat is the whole point of this job. Either the artifact does not ship "
            "what the package needs, or a test reaches outside it. Fix the artifact or "
            "guard the test -- adding a name to EXPECTED_NON_PASSING is only correct when "
            "the test structurally cannot run without a source checkout, and the comment "
            "beside it has to say which structure."
        )
    stale = sorted(wanted - observed)
    if stale:
        problems.append(
            f"{FAILURE_MARKER}: these are listed as unable to run from an installed "
            "package, and just ran:\n  "
            + "\n  ".join(stale)
            + "\n\nGood news, and the list is now wrong. Delete those lines from "
            "EXPECTED_NON_PASSING in tools/gate_installed_suite.py."
        )
    passed = int(got["counts"].get("passed", 0))
    if passed < floor:
        problems.append(
            f"{FAILURE_MARKER}: only {passed} tests passed, under the {floor} floor. "
            "Something stopped the suite collecting; the exclusions above are not the "
            "explanation and the floor is not the thing to change."
        )

    got["problems"] = problems
    got["rc"] = 1 if problems else 0
    got["passed"] = passed
    got["skipped"] = int(got["counts"].get("skipped", 0))
    return got


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("log", type=Path, help="the pytest log to adjudicate")
    args = parser.parse_args(argv)

    if not args.log.is_file():
        print(f"{FAILURE_MARKER}: {args.log} does not exist", file=sys.stderr)
        return 1
    text = args.log.read_text(encoding="utf-8", errors="replace")
    verdict = adjudicate(text)

    print(f"summary: {verdict['summary']}")
    print(f"skipped {verdict['skipped']}; skip reasons, as reported:")
    for line in text.splitlines():
        if line.startswith("SKIPPED "):
            print(f"  {line}")
    if verdict["problems"]:
        print("\n\n".join(verdict["problems"]), file=sys.stderr)
        return 1
    print(
        f"OK: {verdict['passed']} tests passed from the installed distribution, "
        f"{verdict['skipped']} skipped, {len(EXPECTED_NON_PASSING)} checkout-only entries "
        "accounted for exactly."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
