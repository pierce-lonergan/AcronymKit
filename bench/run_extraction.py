#!/usr/bin/env python3
"""Evaluate abbreviation extraction against a gold-standard corpus.

Usage::

    python bench/run_extraction.py                     # acronymkit on MED1250
    python bench/run_extraction.py --errors            # plus error examples
    python bench/run_extraction.py --system scispacy   # baseline, if installed
    python bench/run_extraction.py --markdown          # docs/EVALUATION.md body

The point of the harness is comparability. Numbers lifted from papers are not
comparable to numbers produced here — different tokenisation, different match
conventions, sometimes a different subset of the corpus. Only same-harness
numbers are, which is why the baselines run through the same reader and the same
scorer rather than being quoted.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from bench import corpora, scoring  # noqa: E402

Pair = tuple[str, str]


# ---------------------------------------------------------------------------
# systems under test
# ---------------------------------------------------------------------------
def predict_acronymkit(documents: Sequence, **config_overrides: object) -> dict[str, list[Pair]]:
    """Run this library's extractor over every document."""
    from acronymkit import AcronymEngine, Config

    engine = AcronymEngine(Config(**config_overrides))
    return {
        document.uid: [
            (pair.short_form, pair.long_form) for pair in engine.extract_definitions(document.text)
        ]
        for document in documents
    }


#: Baselines that must run under a different interpreter. ``pyab3p`` ships
#: wheels only up to CPython 3.12 and ``scispacy`` declares
#: ``requires-python <3.13``, so both are driven out-of-process via
#: ``bench/external.py``. Point ``--interpreter`` at a Python that has them.
EXTERNAL_SYSTEMS = ("abbreviations", "abbreviation_extractor", "pyab3p", "scispacy")

SYSTEMS = {"acronymkit": predict_acronymkit}


def predict_external(
    system: str, documents: Sequence, interpreter: str, corpus: str, limit: Optional[int]
) -> tuple[dict[str, list[Pair]], float, float]:
    """Run a competing extractor under ``interpreter`` and read its JSON back.

    Args:
        system: Key in :data:`bench.external.PREDICTORS`.
        documents: Only used for the error message when nothing comes back.
        interpreter: Path to a Python that has the baseline installed.
        corpus: Corpus name, re-read on the far side so the two processes agree.
        limit: Optional document cap, mirrored on the far side.

    Returns:
        ``(predictions, elapsed_seconds, import_seconds)``.

    Raises:
        SystemExit: If the subprocess fails, with its stderr attached.
    """
    command = [
        interpreter,
        str(REPO_ROOT / "bench" / "external.py"),
        "--system",
        system,
        "--corpus",
        corpus,
    ]
    if limit:
        command += ["--limit", str(limit)]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise SystemExit(f"{system} failed under {interpreter}:\n{completed.stderr[-2000:]}")
    payload = json.loads(completed.stdout)
    predictions = {
        uid: [(pair[0], pair[1]) for pair in pairs] for uid, pairs in payload["predictions"].items()
    }
    if not predictions and documents:
        raise SystemExit(f"{system} returned no predictions at all")
    return predictions, payload["elapsed_seconds"], payload["import_seconds"]


def dedupe_per_document(predictions: dict[str, list[Pair]]) -> dict[str, list[Pair]]:
    """Collapse repeated identical pairs within a document, for every system alike.

    Systems disagree about what one "result" is. scispaCy's ``AbbreviationDetector``
    reports every *mention* of an abbreviation, so a document defining three terms
    and then using them yields far more rows than it has definitions -- 3,419
    predictions against 1,221 gold pairs on MED1250, which scores as
    2,493 false positives and a precision of 27 %. That measures the adapter, not
    the system.

    The gold standard records definitions, so predictions are reduced to distinct
    ``(short form, long form)`` pairs per document. Applied uniformly, because
    applying it only to the system it happens to help would be worse than not
    applying it at all.

    The cost is small and shared: MED1250 does contain a handful of documents that
    genuinely define the same pair twice, and the second one becomes unreachable
    for every system equally.

    Args:
        predictions: ``{document uid: [(short, long), ...]}``.

    Returns:
        The same mapping with within-document duplicates removed, order preserved.
    """
    reduced: dict[str, list[Pair]] = {}
    for uid, pairs in predictions.items():
        seen: set[tuple[str, str]] = set()
        kept: list[Pair] = []
        for short_form, long_form in pairs:
            key = (short_form.casefold(), " ".join(long_form.split()).casefold())
            if key not in seen:
                seen.add(key)
                kept.append((short_form, long_form))
        reduced[uid] = kept
    return reduced


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def environment() -> str:
    """One-line description of the machine, for the results table."""
    return f"Python {platform.python_version()} on {platform.system()} {platform.machine()}"


def save_results(entries: dict) -> Path:
    """Merge ``entries`` into ``bench/results.json``, the one file claims may cite.

    Prose is not allowed to hardcode a performance number; ``tools/check_claims.py``
    verifies every claim against this file. Runners are the only writers.

    Args:
        entries: ``{run_id: {...measurements...}}``.

    Returns:
        Path to the results file.
    """
    path = REPO_ROOT / "bench" / "results.json"
    document = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"runs": {}}
    document.setdefault("runs", {}).update(entries)
    document["environment"] = environment()
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def render(evaluation: scoring.Evaluation, *, errors: bool) -> str:
    """Human-readable report."""
    lines = [
        f"corpus      : {evaluation.corpus}",
        f"system      : {evaluation.system}",
        f"documents   : {evaluation.documents:,}",
        f"gold pairs  : {evaluation.gold_pairs:,}",
        f"predicted   : {evaluation.predicted_pairs:,}",
        f"elapsed     : {evaluation.elapsed_seconds:.2f}s "
        f"({evaluation.documents / max(evaluation.elapsed_seconds, 1e-9):.0f} docs/s)",
        f"environment : {environment()}",
        "",
        evaluation.table(),
    ]
    if errors:
        lines += ["", f"MISSED (false negatives, showing {len(evaluation.missed)}):"]
        lines += [
            f"  [{identifier}] {short!r} -> {long_form!r}"
            for identifier, (short, long_form) in evaluation.missed
        ]
        lines += ["", f"SPURIOUS (false positives, showing {len(evaluation.spurious)}):"]
        lines += [
            f"  [{identifier}] {short!r} -> {long_form!r}"
            for identifier, (short, long_form) in evaluation.spurious
        ]
    return "\n".join(lines)


def render_markdown(evaluations: Sequence[scoring.Evaluation]) -> str:
    """Results table for ``docs/EVALUATION.md``."""
    lines = [
        "| System | Match | P % | R % | F1 % | TP | FP | FN |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for evaluation in evaluations:
        for name in ("exact", "relaxed"):
            score = evaluation.scores[name]
            lines.append(
                f"| `{evaluation.system}` | {name} | {score.precision * 100:.2f} | "
                f"{score.recall * 100:.2f} | **{score.f1 * 100:.2f}** | "
                f"{score.true_positives} | {score.false_positives} | "
                f"{score.false_negatives} |"
            )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--corpus", default="med1250", choices=sorted(corpora.READERS))
    parser.add_argument(
        "--system",
        action="append",
        choices=sorted(set(SYSTEMS) | set(EXTERNAL_SYSTEMS)),
        help="repeatable; external baselines need --interpreter",
    )
    parser.add_argument(
        "--interpreter",
        default=sys.executable,
        help="Python that has the external baselines installed. pyab3p ships "
        "wheels only up to 3.12 and scispacy requires <3.13, so they need a "
        "separate interpreter from the one running this script.",
    )
    parser.add_argument("--errors", action="store_true", help="list missed and spurious pairs")
    parser.add_argument("--markdown", action="store_true", help="emit a markdown table")
    parser.add_argument("--limit", type=int, help="score only the first N documents")
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    args = parser.parse_args(argv)

    documents = corpora.load(args.corpus)
    if args.limit:
        documents = documents[: args.limit]

    evaluations = []
    for system in args.system or ["acronymkit"]:
        if system in EXTERNAL_SYSTEMS:
            predictions, elapsed, _ = predict_external(
                system, documents, args.interpreter, args.corpus, args.limit
            )
        else:
            started = time.perf_counter()
            predictions = SYSTEMS[system](documents)
            elapsed = time.perf_counter() - started
        evaluation = scoring.evaluate(
            documents,
            dedupe_per_document(predictions),
            corpus=args.corpus,
            system=system,
            elapsed_seconds=elapsed,
            error_limit=None if args.errors else 40,
        )
        evaluations.append(evaluation)
        if not args.markdown:
            print(render(evaluation, errors=args.errors))
            print()

    if args.markdown:
        print(render_markdown(evaluations))
    if args.save:
        entries = {
            f"extraction.{args.corpus}.{ev.system}": {
                "corpus": ev.corpus,
                "system": ev.system,
                "documents": ev.documents,
                "gold_pairs": ev.gold_pairs,
                "predicted_pairs": ev.predicted_pairs,
                "elapsed_seconds": round(ev.elapsed_seconds, 4),
                "docs_per_second": round(ev.documents / max(ev.elapsed_seconds, 1e-9), 1),
                **{
                    f"{name}_{metric}": round(getattr(ev.scores[name], metric) * 100, 2)
                    for name in ("exact", "relaxed")
                    for metric in ("precision", "recall", "f1")
                },
                **{
                    f"{name}_{metric}": getattr(ev.scores[name], metric)
                    for name in ("exact", "relaxed")
                    for metric in ("true_positives", "false_positives", "false_negatives")
                },
            }
            for ev in evaluations
        }
        print(f"saved {len(entries)} run(s) to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
