#!/usr/bin/env python3
"""Micro-benchmarks: per-call latency and cold import cost.

These are the numbers the README quotes about the library itself rather than
about a corpus, so they need the same traceability as the accuracy figures. All
of them are recorded into ``bench/results.json``.

Cold import is measured in a **subprocess** — measuring it in-process would time
a warm module cache and report roughly zero, which is the classic way to publish
a flattering import-time number by accident.

Three import figures, not one
-----------------------------
``acronymkit/__init__.py`` resolves its re-exports lazily (:pep:`562`), so a
single "cold import" number would be easy to quote misleadingly. Quoting the
bare figure on its own would be exactly the sort of flattering measurement this
harness exists to prevent, so the runner records all three and the ratio between
them is visible in ``results.json``:

``cold_import_ms``
    ``import acronymkit``. What a process pays to have the package present —
    for :data:`acronymkit.__version__`, for a ``TYPE_CHECKING`` reference, or
    because a dependency imports it. This is the figure comparable to the
    ``import <package>`` column other libraries are measured on.

``cold_import_engine_ms``
    ``from acronymkit import AcronymEngine``. What a process pays to have the
    engine and the Pydantic DTO layer. This is where the library's real import
    cost lives, and lazy re-export moves it here rather than removing it.

``cold_first_result_ms``
    Import, construct an engine, and generate once. Time to first answer, with
    nowhere for deferred work to hide. If lazy import were merely shuffling
    cost around, this is the number that would show it.

Usage::

    python bench/run_micro.py --save
"""

from __future__ import annotations

import argparse
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

#: Phrase used for the hot-path latency measurement.
PHRASE = "Portable Document Format"

#: Iterations after warm-up.
ITERATIONS = 5_000

#: Subprocess repeats behind every cold-import median.
IMPORT_REPEATS = 9

#: ``{result key: statement timed in a fresh interpreter}``. See the module
#: docstring for why there are three rather than one.
IMPORT_CASES = {
    "cold_import_ms": "import acronymkit",
    "cold_import_engine_ms": "from acronymkit import AcronymEngine",
    "cold_first_result_ms": (
        f"from acronymkit import AcronymEngine;AcronymEngine().generate({PHRASE!r})"
    ),
}


def cold_ms(statement: str, repeats: int = IMPORT_REPEATS) -> float:
    """Median cost of ``statement`` in a fresh interpreter, in milliseconds.

    The timer starts *after* interpreter start-up, so what is reported is the
    package's own cost and not CPython's.

    Args:
        statement: Python source executed once, in a subprocess.
        repeats: Fresh interpreters to sample; the median is returned so a
            single scheduling hiccup cannot set the figure.

    Returns:
        Median wall-clock milliseconds.

    Raises:
        subprocess.CalledProcessError: If any of the subprocesses fails.
    """
    script = (
        "import sys, time;"
        f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r});"
        "t=time.perf_counter();"
        f"{statement};"
        "print(time.perf_counter()-t)"
    )
    samples = []
    for _ in range(repeats):
        out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        out.check_returncode()
        samples.append(float(out.stdout.strip()) * 1000)
    return statistics.median(samples)


def cold_import_measurements() -> dict[str, float]:
    """Run every case in :data:`IMPORT_CASES` and return ``{key: median_ms}``."""
    return {key: cold_ms(statement) for key, statement in IMPORT_CASES.items()}


def generate_microseconds(preset_fast: bool) -> dict[str, float]:
    """Per-call ``generate`` latency, warm, in microseconds.

    Returns:
        ``min``, ``median`` and ``p95`` — dispersion included, because a single
        figure with no spread is not a measurement.
    """
    from acronymkit import AcronymEngine, Config

    engine = AcronymEngine(Config.fast() if preset_fast else Config())
    for _ in range(200):
        engine.generate(PHRASE)  # warm caches and let the interpreter specialise

    samples = []
    for _ in range(ITERATIONS):
        started = time.perf_counter()
        engine.generate(PHRASE)
        samples.append((time.perf_counter() - started) * 1e6)
    samples.sort()
    return {
        "min": round(samples[0], 2),
        "median": round(statistics.median(samples), 2),
        "p95": round(samples[int(len(samples) * 0.95)], 2),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument(
        "--only",
        choices=("all", "import", "latency"),
        default="all",
        help=(
            "restrict the run to one half. A change that touches only the import path has "
            "no effect on per-call latency, so re-recording the latency entries would move "
            "a published figure by run-to-run noise alone -- which is precisely the size of "
            "difference this project reverts changes for. Use '--only import' then."
        ),
    )
    args = parser.parse_args(argv)

    entries: dict[str, dict] = {}

    if args.only in ("all", "import"):
        cold = cold_import_measurements()
        print(f"import acronymkit               : {cold['cold_import_ms']:8.1f} ms")
        print(f"from acronymkit import Engine   : {cold['cold_import_engine_ms']:8.1f} ms")
        print(f"import + first generate         : {cold['cold_first_result_ms']:8.1f} ms")
        entries["micro.import"] = {
            **{key: round(value, 1) for key, value in cold.items()},
            "iterations": IMPORT_REPEATS,
        }

    if args.only in ("all", "latency"):
        fast = generate_microseconds(preset_fast=True)
        default = generate_microseconds(preset_fast=False)
        print(
            f"generate, Config.fast()         : {fast['median']:8.1f} us median "
            f"(min {fast['min']}, p95 {fast['p95']})"
        )
        print(
            f"generate, Config()              : {default['median']:8.1f} us median "
            f"(min {default['min']}, p95 {default['p95']})"
        )
        entries["micro.generate_fast"] = {**fast, "iterations": ITERATIONS, "phrase": PHRASE}
        entries["micro.generate_default"] = {**default, "iterations": ITERATIONS, "phrase": PHRASE}

    if args.save:
        from run_extraction import save_results

        print(f"saved {len(entries)} run(s) to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
