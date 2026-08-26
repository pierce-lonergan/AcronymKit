#!/usr/bin/env python3
"""Measure cold ``import acronymkit`` in a subprocess and enforce the ceiling.

Why this is a script and not a heredoc
--------------------------------------
It was a ``python - <<'PY'`` block inside ``.github/workflows/ci.yml``'s
``import-time`` job, and ``.github/gates.toml`` recorded it as ``inline`` with
the note *"the mutation that matters is one line ... and it is blocked on the
same extraction as gates.schema_copies_match and gates.tier_zero_purity. Three
gates, one fix."* This file is that fix for the third of them.

**The extraction is behaviour-preserving on purpose.** The ceiling, the repeat
count, the two halves and the exit messages are the heredoc's, moved. Nothing
about what CI enforces changed in the commit that moved them, because a commit
that both moves a gate and changes it cannot say which of the two an altered
verdict came from.

Why 30 ms
---------
``import acronymkit`` measures 2.3 ms on the development box
(``bench/results.json``, ``micro.import.cold_import_ms``), nearly all of it
``typing``; the package ``__init__`` is a lookup table and two functions. The
regression this gate exists to catch is the Pydantic DTO layer being re-exported
eagerly again, which measures 128.1 ms on that same box
(``micro.import.cold_import_engine_ms``) and would be worse on a shared runner.

So the ceiling only has to separate ~2 ms from ~130 ms, and 30 ms sits in the
middle of that two-order-of-magnitude gap: 13x headroom over what we achieve --
enough to absorb a slow runner, a cold page cache and first-import bytecode
compilation -- and still 4x below the regression. It is deliberately *not* a
certification of the measured figure; that is ``bench/run_micro.py``'s job, and
its numbers live in ``bench/results.json`` where claims can cite them.

If this ever fires, read the median printed below before touching the ceiling: a
real regression lands near 130 ms, not near 31.

The half that carries the demonstration, and the half that cannot
----------------------------------------------------------------
**The structural half is the one a mutation can prove.** A bare
``import acronymkit`` must not have bound ``pydantic`` or a single
``acronymkit.*`` submodule; that is a property of the code and is identical on
every machine. The registered mutation adds one eager submodule import and this
half rejects it.

**The wall-clock half is a property of the runner and cannot be demonstrated by
mutation at all.** No edit to this tree reliably takes a 2 ms import past 30 ms
without also breaking the structural half first, so the recorded demonstration
covers the structural half and nothing else. R18 would have this half be an
unarmed note with the machine named rather than a gate; changing that is a
change to what CI enforces and belongs in a commit that argues for it, not in
the commit that moved the code. **It is registered here as an open divergence
rather than fixed in passing.**

Usage::

    python tools/gate_import_ceiling.py

Standard library only, and the measurement itself is a subprocess so nothing
this file imports can pollute what is being timed.

Exit codes:
    ``0`` nothing is eagerly bound and the median is under the ceiling,
    ``1`` otherwise.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from typing import List, Optional, Sequence, Tuple

#: The ceiling, in milliseconds. See the module docstring for the derivation --
#: it is a two-order-of-magnitude separator, not a performance target.
CEILING_MS = 30.0

#: How many cold-import subprocesses to time. Odd, so the median is a sample.
REPEATS = 9

#: Printed on every failure, and required by the registered mutation's
#: ``expect_failure_matching``. A non-zero exit on its own is not attributable:
#: a broken interpreter, a missing package or a syntax error here would all
#: produce one and would read as a successful demonstration.
FAILURE_MARKER = "IMPORT CEILING FAILED"

_TIMED = "import time;t = time.perf_counter();import acronymkit;print(time.perf_counter() - t)"

_STRUCTURAL = (
    "import sys, json;"
    "import acronymkit;"
    "print(json.dumps(sorted(m for m in sys.modules"
    " if m == 'pydantic' or m.startswith('acronymkit.'))))"
)


def _probe(source: str) -> Tuple[int, str, str]:
    done = subprocess.run(
        [sys.executable, "-c", source], capture_output=True, text=True, errors="replace"
    )
    return done.returncode, done.stdout, done.stderr


def eager_bindings() -> Tuple[Optional[List[str]], List[str]]:
    """What a bare ``import acronymkit`` bound, or a problem saying why not.

    Returns ``(bindings, problems)``. ``bindings`` is ``None`` when the probe
    could not run -- which is itself a failure of this gate, because a package
    whose bare import raises has failed the thing the gate is about.
    """
    rc, out, err = _probe(_STRUCTURAL)
    if rc != 0:
        return None, [
            f"{FAILURE_MARKER}: `import acronymkit` in a clean subprocess exited {rc}. "
            "The package must import on its own before anything about its cost is "
            f"meaningful.\n{err.strip()[-2000:]}"
        ]
    try:
        return list(json.loads(out.strip())), []
    except ValueError as error:
        return None, [
            f"{FAILURE_MARKER}: the structural probe printed something that is not JSON "
            f"({error}): {out.strip()[:400]!r}"
        ]


def cold_import_samples() -> Tuple[List[float], List[str]]:
    """``REPEATS`` cold-import timings in milliseconds, sorted ascending."""
    samples: List[float] = []
    for _ in range(REPEATS):
        rc, out, err = _probe(_TIMED)
        if rc != 0:
            return samples, [
                f"{FAILURE_MARKER}: a timing subprocess exited {rc}.\n{err.strip()[-2000:]}"
            ]
        try:
            samples.append(float(out.strip()) * 1000)
        except ValueError:
            return samples, [
                f"{FAILURE_MARKER}: a timing subprocess printed {out.strip()[:200]!r}, "
                "which is not a duration."
            ]
    samples.sort()
    return samples, []


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)

    problems: List[str] = []

    samples, timing_problems = cold_import_samples()
    problems.extend(timing_problems)
    median = statistics.median(samples) if samples else float("nan")
    if samples:
        print("samples (ms): " + ", ".join(f"{s:.2f}" for s in samples))
        print(f"median {median:.2f} ms, ceiling {CEILING_MS:.0f} ms")

    eager, structural_problems = eager_bindings()
    problems.extend(structural_problems)
    if eager is not None:
        print(f"bound by a bare import: {eager}")
        if eager:
            problems.append(
                f"{FAILURE_MARKER}: `import acronymkit` eagerly bound {eager}. The package "
                "__init__ must resolve its re-exports lazily; see its Import policy "
                "docstring."
            )

    if samples and median > CEILING_MS:
        problems.append(
            f"{FAILURE_MARKER}: cold import regressed to {median:.2f} ms, over the "
            f"{CEILING_MS:.0f} ms ceiling. Something was added to acronymkit/__init__.py "
            "at module scope."
        )

    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    print("cold import OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
