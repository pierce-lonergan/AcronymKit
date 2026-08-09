#!/usr/bin/env python3
"""Categorise extraction misses by cause, and record the taxonomy.

An F1 number says how much is missed; it does not say *what*. The taxonomy is
what turns "recall is 76.99 %" into a work queue, and it is what showed that a
sixth of the misses are configuration rather than algorithm.

Every count here lands in ``bench/results.json`` so the percentages quoted in
``docs/EVALUATION.md`` are traceable rather than retyped.

Usage::

    python bench/analyse_misses.py --save
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from bench import corpora, scoring  # noqa: E402
from bench.run_extraction import dedupe_per_document, predict_acronymkit, save_results  # noqa: E402

#: Causes, in the order they are tested. The first match wins, so the order
#: encodes precedence: a short form that is both single-character and contains a
#: digit is reported as the configuration rejection, because that is the reason
#: the extractor never considered it.
CAUSES = (
    "short form < 2 chars (config)",
    "no uppercase in short form (config)",
    "brackets inside short form",
    "multi-word short form",
    "digits in short form",
    "characters not present in order",
    "long form exceeds word budget",
    "long-form boundary disagreement",
)

#: Causes that are configuration decisions rather than algorithmic limits.
CONFIG_CAUSES = ("short form < 2 chars (config)", "no uppercase in short form (config)")


def classify_miss(short_form: str, long_form: str) -> str:
    """Attribute one missed gold pair to a single cause.

    Args:
        short_form: The annotated abbreviation.
        long_form: The annotated expansion.

    Returns:
        One of :data:`CAUSES`.
    """
    if len(short_form) < 2:
        return "short form < 2 chars (config)"
    if not any(character.isupper() for character in short_form):
        return "no uppercase in short form (config)"
    if re.search(r"[()\[\]]", short_form):
        return "brackets inside short form"
    if len(short_form.split()) > 1:
        return "multi-word short form"
    if any(character.isdigit() for character in short_form):
        return "digits in short form"
    letters = [c for c in short_form.lower() if c.isalpha()]
    stream = iter(long_form.lower())
    if not all(character in stream for character in letters):
        return "characters not present in order"
    if len(long_form.split()) > len(short_form) + 5:
        return "long form exceeds word budget"
    return "long-form boundary disagreement"


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="med1250", choices=sorted(corpora.READERS))
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    documents = corpora.load(args.corpus)
    evaluation = scoring.evaluate(
        documents,
        dedupe_per_document(predict_acronymkit(documents)),
        corpus=args.corpus,
        system="acronymkit",
        error_limit=None,
    )
    counts = Counter(classify_miss(short, long_form) for _, (short, long_form) in evaluation.missed)
    total = sum(counts.values())

    print(f"corpus  : {args.corpus}")
    print(f"misses  : {total} (relaxed convention)\n")
    print(f"{'share':>7}  {'count':>5}  cause")
    print("-" * 60)
    for cause, count in counts.most_common():
        print(f"{count / total * 100:6.1f}%  {count:5}  {cause}")

    config_total = sum(counts[cause] for cause in CONFIG_CAUSES)
    print(
        f"\nconfiguration rather than algorithm: {config_total} "
        f"({config_total / total * 100:.1f}% of misses)"
    )

    if args.save:
        entry = {
            "corpus": args.corpus,
            "total_misses": total,
            "config_attributable": config_total,
            "config_attributable_pct": round(config_total / total * 100, 2),
            **{
                "pct_" + re.sub(r"[^a-z0-9]+", "_", cause.lower()).strip("_"): round(
                    counts[cause] / total * 100, 2
                )
                for cause in CAUSES
            },
            **{
                "n_" + re.sub(r"[^a-z0-9]+", "_", cause.lower()).strip("_"): counts[cause]
                for cause in CAUSES
            },
        }
        path = save_results({f"analysis.{args.corpus}.miss_taxonomy": entry})
        print(f"saved to {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
