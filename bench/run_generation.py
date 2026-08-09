#!/usr/bin/env python3
"""Evaluate acronym *generation* by inverting an extraction gold standard.

Generation has had no external evaluation at all — only sixteen textbook
initialisms, which is a smoke test wearing an evaluation's clothes. But a corpus
of ``(short form, long form)`` pairs is already a generation gold standard read
backwards: feed the long form in, and ask whether the human's short form comes
back, and at what rank.

That gives ``recall@k`` over 1,221 real pairs instead of 16 hand-picked ones.

What this metric is and is not
------------------------------
Gold acronyms are **what humans chose**, not what is optimal. Several expansions
have more than one defensible abbreviation, and the corpus records only the one
that appeared. So ``recall@1`` is a lower bound on quality, not an accuracy
score, and the rank *distribution* is more informative than any single number.

More importantly, MED1250 is biomedical and full of pairs that no initialism
generator can produce by construction:

* ``DAP -> 2,6-diaminopurine`` — the short form draws on characters inside a
  single word;
* ``T3 -> triiodothyronine`` — a digit that appears nowhere in the expansion;
* ``[Ca2+]i -> intracellular Ca2+ concentration`` — punctuation and subscripts.

Scoring those as failures would measure the corpus, not the generator. Every
pair is therefore classified before scoring, and the headline is reported over
the *reachable* subset with the excluded counts shown alongside. Both numbers
appear; neither is hidden.

Usage::

    python bench/run_generation.py                       # default preset
    python bench/run_generation.py --all-presets         # per-preset comparison
    python bench/run_generation.py --examples            # sample failures
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from bench import corpora  # noqa: E402

#: Ranks reported in the recall curve.
CUTOFFS = (1, 5, 10, 25)

#: Upper bound on generated acronym length for the evaluation. Chosen once, for
#: every system and preset, rather than per pair: sizing the search to the
#: answer would be fitting to the test set.
MAX_ACRONYM_LENGTH = 10

_ALPHA = re.compile(r"^[A-Za-z]+$")


@dataclass
class Bucket:
    """Counts for one subset of the corpus."""

    name: str
    total: int = 0
    hits: Counter = field(default_factory=Counter)
    ranks: list[int] = field(default_factory=list)

    def record(self, rank: Optional[int]) -> None:
        """Record one pair's outcome; ``rank`` is 1-based, ``None`` for a miss."""
        self.total += 1
        if rank is None:
            return
        self.ranks.append(rank)
        for cutoff in CUTOFFS:
            if rank <= cutoff:
                self.hits[cutoff] += 1

    def recall_at(self, cutoff: int) -> float:
        return self.hits[cutoff] / self.total if self.total else 0.0


def classify(short_form: str, long_form: str) -> str:
    """Bucket a gold pair by whether an initialism generator could produce it.

    Args:
        short_form: The annotated abbreviation.
        long_form: The annotated expansion.

    Returns:
        ``"initialism"`` when every short-form letter is the initial of a
        long-form word, in order — the case the generator is designed for;
        ``"unreachable"`` when the short form is out of length bounds or is not
        purely alphabetic; ``"subword"`` for everything else, meaning the short
        form draws on characters inside words.
    """
    if not _ALPHA.match(short_form):
        return "unreachable"
    if not 2 <= len(short_form) <= MAX_ACRONYM_LENGTH:
        return "unreachable"
    initials = [word[0].lower() for word in re.split(r"[\s\-/]+", long_form) if word]
    cursor = 0
    for character in short_form.lower():
        while cursor < len(initials) and initials[cursor] != character:
            cursor += 1
        if cursor == len(initials):
            return "subword"
        cursor += 1
    return "initialism"


def evaluate_preset(
    pairs: Sequence[tuple[str, str]], strategy_name: Optional[str], examples: int
) -> tuple[dict[str, Bucket], float, list[tuple[str, str, list[str]]]]:
    """Run the generator over every long form and record the gold rank.

    Args:
        pairs: ``(short_form, long_form)`` gold pairs.
        strategy_name: ``ScoringStrategy`` value, or ``None`` for the default.
        examples: How many initialism-bucket failures to retain.

    Returns:
        ``(buckets, elapsed_seconds, failures)``.
    """
    from acronymkit import AcronymEngine, Config
    from acronymkit.enums import ScoringStrategy
    from acronymkit.exceptions import AcronymKitError

    options: dict[str, object] = {
        "max_acronym_length": MAX_ACRONYM_LENGTH,
        "max_candidates": max(CUTOFFS),
        "include_breakdown": False,
    }
    if strategy_name:
        options["scoring_strategy"] = ScoringStrategy.coerce(strategy_name)
    engine = AcronymEngine(Config(**options))  # type: ignore[arg-type]

    buckets = {name: Bucket(name) for name in ("initialism", "subword", "unreachable")}
    failures: list[tuple[str, str, list[str]]] = []
    started = time.perf_counter()
    for short_form, long_form in pairs:
        bucket = buckets[classify(short_form, long_form)]
        try:
            candidates = engine.generate(long_form).alternatives
        except AcronymKitError:
            bucket.record(None)
            continue
        produced = [candidate.acronym for candidate in candidates]
        target = short_form.upper()
        rank = produced.index(target) + 1 if target in produced else None
        bucket.record(rank)
        if rank is None and bucket.name == "initialism" and len(failures) < examples:
            failures.append((short_form, long_form, produced[:5]))
    return buckets, time.perf_counter() - started, failures


def render(
    label: str, buckets: dict[str, Bucket], elapsed: float, *, show_header: bool = True
) -> str:
    """Format one preset's results."""
    lines = []
    if show_header:
        lines.append(
            f"{'preset':<24} {'bucket':<12} {'n':>5} "
            + " ".join(f"{'R@' + str(c):>7}" for c in CUTOFFS)
            + f" {'median':>7}"
        )
        lines.append("-" * (24 + 12 + 6 + 8 * len(CUTOFFS) + 8))
    for name in ("initialism", "subword", "unreachable"):
        bucket = buckets[name]
        if not bucket.total:
            continue
        median = sorted(bucket.ranks)[len(bucket.ranks) // 2] if bucket.ranks else 0
        cells = " ".join(f"{bucket.recall_at(c) * 100:6.1f}%" for c in CUTOFFS)
        lines.append(
            f"{label:<24} {name:<12} {bucket.total:>5} {cells} {median if median else '-':>7}"
        )
    lines.append(f"{'':<24} {'(elapsed ' + format(elapsed, '.2f') + 's)':<12}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--corpus", default="med1250", choices=sorted(corpora.READERS))
    parser.add_argument("--all-presets", action="store_true")
    parser.add_argument("--examples", type=int, default=0, help="show N initialism failures")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    args = parser.parse_args(argv)

    documents = corpora.load(args.corpus)
    pairs = [(pair.short_form, pair.long_form) for document in documents for pair in document.pairs]
    if args.limit:
        pairs = pairs[: args.limit]

    distribution = Counter(classify(short, long_form) for short, long_form in pairs)
    print(f"corpus      : {args.corpus}")
    print(f"gold pairs  : {len(pairs):,}")
    print(
        "buckets     : "
        + ", ".join(f"{name} {count:,}" for name, count in distribution.most_common())
    )
    print(
        "note        : recall is reported per bucket. Only 'initialism' is a fair\n"
        "              target for an initialism generator; the rest are shown so the\n"
        "              exclusion is visible rather than hidden.\n"
    )

    presets = (
        ["strict_initialism", "balanced_pronounceable", "max_pronounceable", "dictionary_backronym"]
        if args.all_presets
        else [None]
    )
    first = True
    recorded: dict[str, dict] = {}
    for preset in presets:
        buckets, elapsed, failures = evaluate_preset(pairs, preset, args.examples)
        print(render(preset or "default", buckets, elapsed, show_header=first))
        first = False
        label = preset or "default"
        recorded[f"generation.{args.corpus}.{label}"] = {
            "corpus": args.corpus,
            "preset": label,
            "gold_pairs": len(pairs),
            "elapsed_seconds": round(elapsed, 4),
            **{
                f"{bucket}_n": buckets[bucket].total
                for bucket in ("initialism", "subword", "unreachable")
            },
            **{
                f"{bucket}_recall_at_{cutoff}": round(buckets[bucket].recall_at(cutoff) * 100, 2)
                for bucket in ("initialism", "subword", "unreachable")
                for cutoff in CUTOFFS
            },
        }
        if failures:
            print("\n  initialism-bucket failures (gold not in top 25):")
            for short_form, long_form, produced in failures:
                print(f"    {short_form:<10} gold for {long_form!r}")
                print(f"    {'':<10} generated {produced}")
            print()
    if args.save:
        from run_extraction import save_results

        print(f"saved {len(recorded)} run(s) to {save_results(recorded).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
