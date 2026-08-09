#!/usr/bin/env python3
"""Tier 0 (Schwartz & Hearst) against Tier 1 (pseudo-precision cascade).

Protocol
--------
MED1250 is split 50/50 by document with a frozen seed. Strategy precisions are
estimated on the **dev** half and every number is reported on the **test** half.

The estimator never reads a label — it works from raw text and a chance rate
measured by pairing short forms with windows that cannot define them — so the
split guards against a weaker form of contamination than usual: which *text* was
looked at, not which answers. It is still a split, and it is still frozen.

Usage::

    python bench/run_cascade.py --save
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit._pseudo_precision import (  # noqa: E402
    best_alignment,
    estimate_precisions,
    harvest_candidates,
)
from acronymkit._strategies import split_long_form  # noqa: E402
from bench import corpora, scoring  # noqa: E402
from bench.run_extraction import dedupe_per_document, predict_acronymkit, save_results  # noqa: E402

Pair = tuple[str, str]

#: Frozen split seed. Changing it invalidates every held-out number.
SPLIT_SEED = 20260809

_PAREN = re.compile(r"\(([^()]{1,30})\)")
_WINDOW_WORDS = 12

#: Short forms that are obviously not abbreviations. Kept minimal on purpose:
#: the cascade is supposed to earn its precision from the estimator, not from a
#: hand-tuned reject list.
_MIN_LENGTH = 2
_MAX_LENGTH = 12


def split_corpus(documents: Sequence) -> tuple[list, list]:
    """Split by document with the frozen seed."""
    order = list(range(len(documents)))
    random.Random(SPLIT_SEED).shuffle(order)
    cut = len(order) // 2
    return (
        [documents[i] for i in sorted(order[:cut])],
        [documents[i] for i in sorted(order[cut:])],
    )


def predict_cascade(documents: Sequence, table, minimum_precision: float) -> dict[str, list[Pair]]:
    """Extract with the reliability-ordered cascade.

    For each bracketed short form the strategies are tried in descending
    estimated precision and the first success wins, so the recovered long form is
    the most reliable available explanation rather than the shortest one.

    Args:
        documents: Gold documents (only their text is read).
        table: Estimated precisions.
        minimum_precision: Abstain below this confidence.

    Returns:
        ``{document uid: [(short form, long form), ...]}``.
    """
    predictions: dict[str, list[Pair]] = {}
    for document in documents:
        text = document.text
        found: list[Pair] = []
        for bracket in _PAREN.finditer(text):
            short_form = bracket.group(1).strip()
            if not (_MIN_LENGTH <= len(short_form) <= _MAX_LENGTH):
                continue
            if not any(character.isalnum() for character in short_form):
                continue
            if not any(character.isupper() for character in short_form):
                continue
            preceding = text[: bracket.start()]
            words = split_long_form(preceding)[-_WINDOW_WORDS:]
            if not words:
                continue
            folded = [word.casefold() for word, _, _ in words]
            result = best_alignment(
                short_form.casefold(),
                folded,
                table,
                minimum_precision=minimum_precision,
            )
            if result is None:
                continue
            _strategy, positions, _confidence = result
            first_word = min(word_index for word_index, _ in positions)
            start = words[first_word][1]
            long_form = text[start : bracket.start()].strip().rstrip(",;:( ").strip()
            if long_form:
                found.append((short_form, long_form))
        predictions[document.uid] = found
    return predictions


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chance-trials", type=int, default=3)
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="*",
        default=[0.0, 0.5, 0.7, 0.8, 0.9],
        help="abstention thresholds to sweep",
    )
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    documents = corpora.load("med1250")
    dev, test = split_corpus(documents)
    print(f"split (seed {SPLIT_SEED}): dev {len(dev)} docs, test {len(test)} docs")
    print(f"test gold pairs: {sum(len(d.pairs) for d in test)}\n")

    candidates = harvest_candidates(document.text for document in dev)
    table = estimate_precisions(candidates, chance_trials=args.chance_trials)
    print(f"estimated from {len(candidates)} unlabelled dev candidates, no labels read")

    baseline = scoring.evaluate(
        test,
        dedupe_per_document(predict_acronymkit(test)),
        corpus="med1250-test",
        system="tier0",
    )
    print(f"\n{'system':<28} {'P %':>7} {'R %':>7} {'F1 %':>7}")
    print("-" * 52)
    b = baseline.scores["exact"]
    print(
        f"{'tier0 (Schwartz & Hearst)':<28} {b.precision * 100:7.2f} "
        f"{b.recall * 100:7.2f} {b.f1 * 100:7.2f}"
    )

    recorded = {
        "cascade.med1250_test.tier0": {
            "split_seed": SPLIT_SEED,
            "test_documents": len(test),
            "exact_precision": round(b.precision * 100, 2),
            "exact_recall": round(b.recall * 100, 2),
            "exact_f1": round(b.f1 * 100, 2),
        }
    }
    for threshold in args.thresholds:
        evaluation = scoring.evaluate(
            test,
            dedupe_per_document(predict_cascade(test, table, threshold)),
            corpus="med1250-test",
            system=f"tier1@{threshold}",
        )
        s = evaluation.scores["exact"]
        print(
            f"{'tier1 cascade, abstain<' + format(threshold, '.2f'):<28} "
            f"{s.precision * 100:7.2f} {s.recall * 100:7.2f} {s.f1 * 100:7.2f}"
        )
        recorded[f"cascade.med1250_test.tier1_t{threshold:.2f}"] = {
            "split_seed": SPLIT_SEED,
            "abstention_threshold": threshold,
            "exact_precision": round(s.precision * 100, 2),
            "exact_recall": round(s.recall * 100, 2),
            "exact_f1": round(s.f1 * 100, 2),
        }

    if args.save:
        print(f"\nsaved to {save_results(recorded).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
