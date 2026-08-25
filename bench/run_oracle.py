#!/usr/bin/env python3
"""Measure what the five systems collectively can and cannot find.

The question this answers
-------------------------
Four attempts to close the gap to ``pyab3p`` have failed. Before a fifth, it is
worth knowing which *kind* of problem is left, and the union of the systems'
predictions answers that directly:

* **Union recall much higher than ours** — the right answer is being generated
  somewhere and discarded. That is a *selection* problem, and a better ranking
  rule is the correct next move.
* **Union recall close to ours** — everyone is blind to the same pairs. That is a
  *coverage* problem, no ranking rule can help, and the effort belongs in data.

Also reported:

* the pairwise disagreement matrix — who finds what nobody else does;
* our exclusive wins, which decide whether we are strictly dominated;
* universal misses, the corpus's irreducible floor, which should be subtracted
  from any headline before anyone treats 100 % as available.

Usage::

    python bench/run_oracle.py --interpreter C:/akbench/Scripts/python.exe --save
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

from acronymkit._strategies import split_long_form  # noqa: E402
from acronymkit.extractor import is_valid_short_form  # noqa: E402
from bench import corpora  # noqa: E402
from bench.run_extraction import (  # noqa: E402
    EXTERNAL_SYSTEMS,
    dedupe_per_document,
    predict_acronymkit,
    predict_external,
    save_results,
)

SYSTEM_ORDER = ("acronymkit", "pyab3p", "abbreviation_extractor", "abbreviations", "scispacy")


def normalise(short_form: str, long_form: str) -> tuple[str, str]:
    """The comparison key used by the scorer, so counts here match its counts."""
    return short_form.casefold(), " ".join(long_form.split()).casefold()


def own_candidate_space(documents: Sequence) -> tuple[int, int]:
    """How much gold our *own* matcher could return, versus what it does return.

    The cross-system union conflates two different things: systems differ in how
    they *generate* candidates as well as how they *select* among them, so a pair
    only pyab3p finds may be outside our reach entirely. This measures the
    quantity that actually decides whether a better ranking rule can help —
    whether the gold long form is among the spans our own Schwartz & Hearst
    matcher could legitimately return, and is simply not the one it picks.

    The candidate space is every start boundary in the window, which is exactly
    the set the greedy right-to-left walk chooses one element from.

    Args:
        documents: Gold documents.

    Returns:
        ``(gold_total, reachable)``.
    """
    paren = re.compile(r"\(([^()]{1,30})\)")
    gold_total = reachable = 0
    for document in documents:
        gold = {
            (pair.short_form.casefold(), " ".join(pair.long_form.split()).casefold())
            for pair in document.pairs
        }
        gold_total += len(gold)
        space: set[tuple[str, str]] = set()
        for bracket in paren.finditer(document.text):
            short_form = bracket.group(1).strip()
            if not is_valid_short_form(
                short_form, min_length=1, max_length=14, require_uppercase=False
            ):
                continue
            window = document.text[: bracket.start()]
            for _word, start, _end in split_long_form(window)[-14:]:
                candidate = document.text[start : bracket.start()].strip().rstrip(",;:( ").strip()
                if candidate:
                    space.add((short_form.casefold(), " ".join(candidate.split()).casefold()))
        reachable += len(gold & space)
    return gold_total, reachable


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interpreter", default=sys.executable)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    documents = corpora.load("med1250")
    gold = {
        document.uid: {normalise(p.short_form, p.long_form) for p in document.pairs}
        for document in documents
    }
    gold_total = sum(len(pairs) for pairs in gold.values())

    found: dict[str, dict[str, set]] = {}
    for system in SYSTEM_ORDER:
        if system in EXTERNAL_SYSTEMS:
            raw, _, _ = predict_external(system, documents, args.interpreter, "med1250", None)
        else:
            raw = predict_acronymkit(documents)
        reduced = dedupe_per_document(raw)
        found[system] = {
            uid: {normalise(s, lf) for s, lf in pairs} & gold.get(uid, set())
            for uid, pairs in reduced.items()
        }

    def correct(system: str) -> int:
        return sum(len(v) for v in found[system].values())

    union_correct = 0
    universal_miss = 0
    exclusive: Counter = Counter()
    for uid, pairs in gold.items():
        for pair in pairs:
            finders = [s for s in SYSTEM_ORDER if pair in found[s].get(uid, set())]
            if finders:
                union_correct += 1
                if len(finders) == 1:
                    exclusive[finders[0]] += 1
            else:
                universal_miss += 1

    print(f"gold pairs                : {gold_total}")
    print(f"{'system':<24} {'correct':>8} {'recall %':>9} {'exclusive':>10}")
    print("-" * 55)
    for system in SYSTEM_ORDER:
        n = correct(system)
        print(f"{system:<24} {n:>8} {n / gold_total * 100:>8.2f}% {exclusive[system]:>10}")
    print("-" * 55)
    print(f"{'ORACLE UNION':<24} {union_correct:>8} {union_correct / gold_total * 100:>8.2f}%")
    print(f"{'universal miss':<24} {universal_miss:>8} {universal_miss / gold_total * 100:>8.2f}%")

    ours = correct("acronymkit")
    headroom = union_correct - ours
    print(
        f"\nheadroom available to a perfect selector: {headroom} pairs "
        f"({headroom / gold_total * 100:.2f} points of recall)"
    )
    print(
        "verdict: "
        + (
            "SELECTION -- the answers exist and are being discarded."
            if headroom >= 0.05 * gold_total
            else "COVERAGE -- the answers are not being generated at all."
        )
    )

    print(f"\ndisagreement matrix (row finds, column misses)\n{'':<24}", end="")
    for system in SYSTEM_ORDER:
        print(f"{system[:10]:>11}", end="")
    print()
    for row in SYSTEM_ORDER:
        print(f"{row:<24}", end="")
        for column in SYSTEM_ORDER:
            n = sum(len(found[row].get(uid, set()) - found[column].get(uid, set())) for uid in gold)
            print(f"{n:>11}", end="")
        print()

    _, reachable = own_candidate_space(documents)
    own_headroom = reachable - ours
    print(
        f"\nOUR OWN candidate space contains {reachable} of {gold_total} gold pairs "
        f"({reachable / gold_total * 100:.2f}%)"
    )
    print(
        f"selector headroom within our own space: {own_headroom} pairs "
        f"({own_headroom / gold_total * 100:.2f} points) -- reachable with no new data"
    )

    if args.save:
        entry = {
            "own_space_reachable": reachable,
            "own_space_recall": round(reachable / gold_total * 100, 2),
            "own_space_headroom_pairs": own_headroom,
            "own_space_headroom_points": round(own_headroom / gold_total * 100, 2),
            "corpus": "med1250",
            "gold_pairs": gold_total,
            "oracle_union_correct": union_correct,
            "oracle_union_recall": round(union_correct / gold_total * 100, 2),
            "universal_miss": universal_miss,
            "universal_miss_pct": round(universal_miss / gold_total * 100, 2),
            "acronymkit_correct": ours,
            "selector_headroom_pairs": headroom,
            "selector_headroom_points": round(headroom / gold_total * 100, 2),
            **{f"exclusive_{s}": exclusive[s] for s in SYSTEM_ORDER},
            **{f"recall_{s}": round(correct(s) / gold_total * 100, 2) for s in SYSTEM_ORDER},
        }
        print(f"\nsaved to {save_results({'oracle.med1250': entry}).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
