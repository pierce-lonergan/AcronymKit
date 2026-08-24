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

The three are a triple, and ``--save`` is not a local act
--------------------------------------------------------
``--only import`` exists so that a change touching the import path does not
republish the per-call latency arms as run-to-run noise. It does **not** protect
the three import figures from each other: they are written as one
``micro.import`` entry, so the only way to re-record the flattering one is to
re-record the other two with it.

That matters because the three are quoted *together*, and deliberately so.
``docs/DECISIONS.md`` D-013 keeps ``cold_import_engine_ms`` and
``cold_first_result_ms`` beside ``cold_import_ms`` precisely to stop the first
being read as a win; ``docs/EVALUATION.md``'s import-column caveat,
``docs/notes/pydantic-cost.md``, ``CHANGELOG.md`` and the *why 30 ms* comment in
the ``import-time`` CI job all repeat the triple. None of those five is a
runner's output, so ``--save`` silently ages all of them and nothing fails.

So before saving, ask what changed in the *package*. On 2026-08-24, five
consecutive medians-of-nine on the development box put ``cold_import_ms`` below
the recorded figure while ``cold_import_engine_ms`` and ``cold_first_result_ms``
both sat *above* theirs. Nothing this project did makes the shell cheaper and
the engine dearer in the same measurement, so that is the machine moving and not
the package -- and D-038 already measured the one recent change to the import
path, found it well under a tenth of a millisecond, and recorded it as a
non-result on purpose. Re-saving there would have published drift as a win and
staled the other five documents in the opposite direction. It was not saved.
:func:`render_drift` prints the comparison at the moment ``--save`` is used, so
the next person makes that call with the numbers in front of them.

Usage::

    python bench/run_micro.py --save
    python bench/run_micro.py --only import          # measure, do not record
"""

from __future__ import annotations

import argparse
import json
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


#: Where a saved entry lands, read back so ``--save`` can show what it replaces.
RESULTS_PATH = REPO_ROOT / "bench" / "results.json"

#: Documents that quote the ``micro.import`` triple in prose. None of them is
#: generated, so re-saving that entry ages every one of them silently. Listed
#: here rather than in a comment because the list is what makes the printed
#: drift actionable: it says where the cost of saving lands.
TRIPLE_QUOTED_IN = (
    "docs/DECISIONS.md (D-013's before/after table)",
    "docs/EVALUATION.md (the import-column caveat)",
    "docs/notes/pydantic-cost.md",
    "CHANGELOG.md",
    ".github/workflows/ci.yml (the 'why 30 ms' comment)",
)


def stored_entries(keys: Sequence[str]) -> dict:
    """The measurements ``bench/results.json`` already holds for ``keys``.

    Args:
        keys: Run ids this invocation is about to write.

    Returns:
        ``{run id: entry}`` for the keys that already exist. Missing keys and a
        missing results file both yield nothing, because "there is no previous
        figure" and "there is nothing to compare against" are the same answer
        here.
    """
    if not RESULTS_PATH.is_file():
        return {}
    runs = json.loads(RESULTS_PATH.read_text(encoding="utf-8")).get("runs", {})
    return {key: runs[key] for key in keys if key in runs}


def render_drift(stored: dict, fresh: dict) -> list[str]:
    """``stored -> fresh`` for every numeric field ``--save`` would overwrite.

    A saved figure is quoted in documents no runner regenerates, so overwriting
    one is a change to those documents made from another file. This puts the
    size of that change in front of whoever is about to make it.

    Args:
        stored: Entries currently in ``bench/results.json``, from
            :func:`stored_entries`.
        fresh: Entries this run produced.

    Returns:
        Report lines. Empty when nothing is being replaced, so a first-ever
        save prints no comparison rather than a column of dashes.
    """
    lines: list[str] = []
    for key in sorted(fresh):
        previous = stored.get(key)
        if not previous:
            continue
        for field in sorted(fresh[key]):
            was, now = previous.get(field), fresh[key][field]
            if not isinstance(was, (int, float)) or isinstance(was, bool):
                continue
            if not isinstance(now, (int, float)) or isinstance(now, bool):
                continue
            if was == now:  # a settings field, or a figure that did not move
                continue
            change = "" if was == 0 else f"  {(now - was) / was:+7.1%}"
            lines.append(f"  {key}.{field:<24} {was:>8} -> {now:>8}{change}")
    if lines:
        lines = ["", "replacing measurements already published:", *lines]
        if "micro.import" in fresh and "micro.import" in stored:
            lines += [
                "",
                "  micro.import is quoted as a THREE-FIGURE TRIPLE, in prose, in:",
                *(f"    {where}" for where in TRIPLE_QUOTED_IN),
                "  none of which any runner regenerates. If the three did not move",
                "  together and in a direction some change explains, this is the",
                "  machine and not the package -- do not save it.",
            ]
    return lines


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
            "difference this project reverts changes for. Use '--only import' then. Note "
            "that it does NOT separate the three import figures from each other: they are "
            "one entry, they are quoted together on purpose, and --save moves all three."
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

        for line in render_drift(stored_entries(list(entries)), entries):
            print(line, file=sys.stderr)
        print(f"saved {len(entries)} run(s) to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
