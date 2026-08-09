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
import platform
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

    engine = AcronymEngine(Config(**config_overrides))  # type: ignore[arg-type]
    return {
        document.uid: [
            (pair.short_form, pair.long_form) for pair in engine.extract_definitions(document.text)
        ]
        for document in documents
    }


def predict_scispacy(documents: Sequence) -> dict[str, list[Pair]]:
    """Run scispaCy's AbbreviationDetector, the de facto Python baseline.

    Raises:
        SystemExit: If scispaCy or its model is not installed. It is a heavy
            optional dependency and deliberately not required to run the suite.
    """
    try:
        import spacy
        from scispacy.abbreviation import AbbreviationDetector  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "scispacy is not installed. Install with:\n"
            "  pip install scispacy spacy\n"
            "  pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/"
            "releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz"
        ) from exc

    try:
        nlp = spacy.load("en_core_sci_sm")
    except OSError:
        nlp = spacy.blank("en")
        nlp.add_pipe("sentencizer")
    if "abbreviation_detector" not in nlp.pipe_names:
        nlp.add_pipe("abbreviation_detector")

    results: dict[str, list[Pair]] = {}
    for document in documents:
        doc = nlp(document.text)
        results[document.identifier] = [
            (str(abbreviation), str(abbreviation._.long_form))
            for abbreviation in doc._.abbreviations
        ]
    return results


SYSTEMS = {
    "acronymkit": predict_acronymkit,
    "scispacy": predict_scispacy,
}


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def environment() -> str:
    """One-line description of the machine, for the results table."""
    return f"Python {platform.python_version()} on {platform.system()} {platform.machine()}"


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
    parser.add_argument("--system", action="append", choices=sorted(SYSTEMS), help="repeatable")
    parser.add_argument("--errors", action="store_true", help="list missed and spurious pairs")
    parser.add_argument("--markdown", action="store_true", help="emit a markdown table")
    parser.add_argument("--limit", type=int, help="score only the first N documents")
    args = parser.parse_args(argv)

    documents = corpora.load(args.corpus)
    if args.limit:
        documents = documents[: args.limit]

    evaluations = []
    for system in args.system or ["acronymkit"]:
        started = time.perf_counter()
        predictions = SYSTEMS[system](documents)
        elapsed = time.perf_counter() - started
        evaluation = scoring.evaluate(
            documents,
            predictions,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
