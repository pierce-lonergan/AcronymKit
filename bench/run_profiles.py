#!/usr/bin/env python3
"""Measure each extraction profile, selecting on dev and reporting on test.

The extractor has precision to spend -- roughly 92 % precision against 77 %
recall under its defaults -- so no single configuration is right for every
caller. This records what each named operating point actually costs, rather than
picking one and hiding the trade inside a constant.

Usage::

    python bench/run_profiles.py --save
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit.config import EXTRACTION_PROFILES  # noqa: E402
from acronymkit.enums import ExtractionProfile  # noqa: E402
from bench import corpora, scoring  # noqa: E402
from bench.run_cascade import split_corpus  # noqa: E402
from bench.run_extraction import dedupe_per_document, predict_acronymkit, save_results  # noqa: E402


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    dev, test = split_corpus(corpora.load("med1250"))
    print(f"dev {len(dev)} docs, test {len(test)} docs (profiles chosen on dev)\n")
    print(f"{'profile':<16} {'dev F1':>7} | {'test P':>7} {'test R':>7} {'test F1':>8}")
    print("-" * 52)

    recorded = {}
    for profile in ExtractionProfile:
        settings = EXTRACTION_PROFILES[profile]
        scores = {}
        for name, split in (("dev", dev), ("test", test)):
            evaluation = scoring.evaluate(
                split,
                dedupe_per_document(predict_acronymkit(split, **settings)),
                corpus=f"med1250-{name}",
                system=profile.value,
            )
            scores[name] = evaluation.scores["exact"]
        t = scores["test"]
        print(
            f"{profile.value:<16} {scores['dev'].f1 * 100:7.2f} | "
            f"{t.precision * 100:7.2f} {t.recall * 100:7.2f} {t.f1 * 100:8.2f}"
        )
        recorded[f"profile.med1250_test.{profile.value}"] = {
            "profile": profile.value,
            "dev_exact_f1": round(scores["dev"].f1 * 100, 2),
            "exact_precision": round(t.precision * 100, 2),
            "exact_recall": round(t.recall * 100, 2),
            "exact_f1": round(t.f1 * 100, 2),
            **settings,
        }

    if args.save:
        print(f"\nsaved to {save_results(recorded).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
