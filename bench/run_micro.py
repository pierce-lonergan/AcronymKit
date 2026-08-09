#!/usr/bin/env python3
"""Micro-benchmarks: per-call latency and cold import cost.

These are the numbers the README quotes about the library itself rather than
about a corpus, so they need the same traceability as the accuracy figures. Both
are recorded into ``bench/results.json``.

Cold import is measured in a **subprocess** — measuring it in-process would time
a warm module cache and report roughly zero, which is the classic way to publish
a flattering import-time number by accident.

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


def cold_import_ms(repeats: int = 5) -> float:
    """Median cost of ``import acronymkit`` in a fresh interpreter, in ms."""
    script = (
        "import sys, time;"
        f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r});"
        "t=time.perf_counter();"
        "import acronymkit;"
        "print(time.perf_counter()-t)"
    )
    samples = []
    for _ in range(repeats):
        out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        out.check_returncode()
        samples.append(float(out.stdout.strip()) * 1000)
    return statistics.median(samples)


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
    args = parser.parse_args(argv)

    cold = cold_import_ms()
    fast = generate_microseconds(preset_fast=True)
    default = generate_microseconds(preset_fast=False)

    print(f"cold import (subprocess median) : {cold:8.1f} ms")
    print(
        f"generate, Config.fast()         : {fast['median']:8.1f} us median "
        f"(min {fast['min']}, p95 {fast['p95']})"
    )
    print(
        f"generate, Config()              : {default['median']:8.1f} us median "
        f"(min {default['min']}, p95 {default['p95']})"
    )

    if args.save:
        from run_extraction import save_results

        entries = {
            "micro.import": {"cold_import_ms": round(cold, 1), "iterations": 5},
            "micro.generate_fast": {**fast, "iterations": ITERATIONS, "phrase": PHRASE},
            "micro.generate_default": {**default, "iterations": ITERATIONS, "phrase": PHRASE},
        }
        print(f"saved {len(entries)} run(s) to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
