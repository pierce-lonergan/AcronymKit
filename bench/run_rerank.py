#!/usr/bin/env python3
"""Select among Schwartz & Hearst's own candidates by pseudo-precision.

What is different about this experiment
---------------------------------------
Five attempts have now failed to close the gap to ``pyab3p``. Every one of them
changed *which spans were considered*, *how one was chosen*, or both — so none
could attribute its result to a single cause.

This one holds the candidate space fixed at exactly the set
``bench/run_oracle.py`` measured — every start boundary in the window, the set a
greedy right-to-left walk picks one element from — and changes only the
selection rule: pseudo-precision instead of position.

That matters because the oracle established the space is not the problem. It
contains 88.49 % of gold pairs while the greedy rule returns 78.40 %, so the
right answer is present and discarded 121 times. This is the first selection
experiment with a measured ceiling to aim at rather than a hope.

Scoring
-------
A candidate span is scored by the reliability of the *most reliable* strategy
that can explain it — if a word-initial rule accounts for the alignment, that is
what the abbreviation almost certainly is, whatever looser rules also happen to
fit. Candidates no strategy explains score zero and are dropped.

Ties break toward the shorter span. That is the greedy rule's own bias, and two
independent experiments (D-008, D-010) have shown that preferring longer spans
loses more than it gains.

Usage::

    python bench/run_rerank.py --save
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit._pseudo_precision import (  # noqa: E402
    PrecisionTable,
    estimate_precisions,
    harvest_candidates,
    short_form_group,
)
from acronymkit._strategies import STRATEGIES, best_match, split_long_form  # noqa: E402
from acronymkit.extractor import is_valid_short_form  # noqa: E402
from bench import corpora, scoring  # noqa: E402
from bench.run_cascade import split_corpus  # noqa: E402
from bench.run_extraction import dedupe_per_document, predict_acronymkit, save_results  # noqa: E402

Pair = tuple[str, str]

_PAREN = re.compile(r"\(([^()]{1,30})\)")

#: Window width in words. Matches the oracle measurement exactly, so the ceiling
#: reported there is the ceiling this is measured against.
_WINDOW = 14


def score_candidate(short_form: str, words: Sequence[str], table: PrecisionTable) -> float:
    """Reliability of the best strategy that explains this span.

    Args:
        short_form: Case-folded short form.
        words: Case-folded words of the candidate long form.
        table: Estimated precisions.

    Returns:
        The highest estimated precision among matching strategies; ``0.0`` when
        nothing explains the span.
    """
    group = short_form_group(short_form)
    best = 0.0
    for strategy in STRATEGIES:
        precision = table.precision(group, strategy.name)
        if precision <= best:
            continue  # cannot improve on what we already have
        if best_match(short_form, words, strategy) is not None:
            best = precision
    return best


def predict_reranked(
    documents: Sequence, table: PrecisionTable, minimum: float
) -> dict[str, list[Pair]]:
    """Extract by scoring every candidate span and taking the most reliable.

    Args:
        documents: Gold documents (text only is read).
        table: Estimated precisions.
        minimum: Reject a short form whose best candidate scores below this.

    Returns:
        ``{document uid: [(short form, long form), ...]}``.
    """
    predictions: dict[str, list[Pair]] = {}
    for document in documents:
        text = document.text
        found: list[Pair] = []
        for bracket in _PAREN.finditer(text):
            short_form = bracket.group(1).strip()
            if not is_valid_short_form(short_form, min_length=2, max_length=10):
                continue
            window = text[: bracket.start()]
            words = split_long_form(window)[-_WINDOW:]
            if not words:
                continue

            best_score = 0.0
            best_form: Optional[str] = None
            # Latest start first, so an equal score keeps the shorter span.
            for index in reversed(range(len(words))):
                span = text[words[index][1] : bracket.start()].strip().rstrip(",;:( ").strip()
                if not span:
                    continue
                folded = [word.casefold() for word, _, _ in words[index:]]
                value = score_candidate(short_form.casefold(), folded, table)
                if value > best_score:
                    best_score, best_form = value, span
            if best_form is not None and best_score >= minimum:
                found.append((short_form, best_form))
        predictions[document.uid] = found
    return predictions


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thresholds", type=float, nargs="*", default=[0.0, 0.5, 0.8, 0.9, 0.95])
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    dev, test = split_corpus(corpora.load("med1250"))
    table = estimate_precisions(
        harvest_candidates(document.text for document in dev), chance_trials=3
    )
    print(f"dev {len(dev)} docs (estimation, no labels read), test {len(test)} docs")
    print(f"test gold pairs: {sum(len(d.pairs) for d in test)}\n")

    baseline = scoring.evaluate(
        test, dedupe_per_document(predict_acronymkit(test)), corpus="t", system="tier0"
    )
    b = baseline.scores["exact"]
    print(f"{'system':<34} {'P %':>7} {'R %':>7} {'F1 %':>7}")
    print("-" * 58)
    print(
        f"{'tier0 greedy (Schwartz & Hearst)':<34} {b.precision * 100:7.2f} "
        f"{b.recall * 100:7.2f} {b.f1 * 100:7.2f}"
    )

    recorded = {
        "rerank.med1250_test.tier0": {
            "exact_precision": round(b.precision * 100, 2),
            "exact_recall": round(b.recall * 100, 2),
            "exact_f1": round(b.f1 * 100, 2),
        }
    }
    for threshold in args.thresholds:
        evaluation = scoring.evaluate(
            test,
            dedupe_per_document(predict_reranked(test, table, threshold)),
            corpus="t",
            system=f"rerank@{threshold}",
        )
        s = evaluation.scores["exact"]
        print(
            f"{'rerank by pseudo-precision, min ' + format(threshold, '.2f'):<34} "
            f"{s.precision * 100:7.2f} {s.recall * 100:7.2f} {s.f1 * 100:7.2f}"
        )
        recorded[f"rerank.med1250_test.min{threshold:.2f}"] = {
            "minimum_precision": threshold,
            "exact_precision": round(s.precision * 100, 2),
            "exact_recall": round(s.recall * 100, 2),
            "exact_f1": round(s.f1 * 100, 2),
        }

    if args.save:
        print(f"\nsaved to {save_results(recorded).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
