#!/usr/bin/env python3
"""Select among Schwartz & Hearst's own candidates by per-candidate term statistics.

Experiment seven on the same gap
--------------------------------
D-011 established that our own candidate space already contains far more gold
than the greedy rule returns, so the right span is present and discarded. D-012
established *why* the obvious fix failed: pseudo-precision scores the matching
*strategy*, and for the overwhelming majority of brackets the gold span ties with
the top score, because the competing spans are explained by the same rule.

So the required signal is per-candidate — something that differs between two
spans one rule explains. :mod:`acronymkit._term_stats` derives three such things
from unlabelled text: document frequency, adjacent-word association, and a
left-boundary statistic. This runner uses them as the selection rule and changes
nothing else.

Protocol
--------
* Statistics are built from the **dev** half only, reading no labels at all.
* Every configuration choice is made on the **dev** half; the **test** half is
  reported.
* The split is ``bench.run_cascade.split_corpus``, imported rather than
  reimplemented, so it is bit-identical to every other experiment here.
* The candidate space is ``bench/run_rerank.py``'s enumeration verbatim — every
  start boundary in a 14-word window — because experiments one to five changed
  the space and the selector together and none of them could be attributed.

Two families of selection rule, and the difference matters
----------------------------------------------------------
``argmax``
    Score every admissible candidate and take the best. This is what
    ``run_rerank.py`` does with pseudo-precision, and it is the obvious thing to
    do with a per-candidate statistic. It is reported here because it fails, and
    it fails in the direction two earlier experiments failed in: a global argmax
    over fourteen starts will always find some far-left start whose first two
    words happen to collocate, so it over-extends.

``extend``
    Start from the span the greedy rule would return and move the left edge
    outward one admissible candidate at a time, for as long as *every* adjacency
    the extension introduces clears a threshold. Stop at the first junction the
    corpus has no evidence for. This is the same statistic used as a local
    decision rather than a global ranking, and it inherits the greedy rule's
    bias toward the shorter span — which D-008 and D-010 both found expensive to
    abandon.

Controls, and they are the point
--------------------------------
Selecting from this space requires an admissibility gate, and attributing a
result to the statistics means measuring what the gate and the rule *shape* do
without them:

``shortest``
    The gate, then the shortest surviving candidate — the greedy rule
    re-expressed over this space. Isolates the gate.
``extend/content-word``
    The extension rule driven by a hard-coded function-word list instead of the
    statistics. If the derived table cannot beat a stop list, it is reproducing
    one and should be replaced by one.

Usage::

    python bench/run_termfreq.py --save
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit._strategies import SKIPPABLE, STRATEGIES, match, split_long_form  # noqa: E402
from acronymkit.extractor import is_valid_long_form, is_valid_short_form  # noqa: E402
from bench import corpora, scoring  # noqa: E402
from bench.run_cascade import SPLIT_SEED, split_corpus  # noqa: E402
from bench.run_extraction import dedupe_per_document, predict_acronymkit, save_results  # noqa: E402
from bench.term_stats import TermStatistics, build_statistics  # noqa: E402

Pair = Tuple[str, str]

_PAREN = re.compile(r"\(([^()]{1,30})\)")

#: Window width in words. Identical to ``bench/run_rerank.py`` and to the oracle
#: measurement, so the ceiling reported there is the ceiling measured against.
_WINDOW = 14

#: The Schwartz & Hearst rule expressed as a strategy: the first short-form
#: character must sit on the head word's initial, the rest may fall anywhere
#: inside the span in order, and intervening words may contribute nothing.
#:
#: This is the admissibility gate. It is deliberately *not*
#: ``extractor.find_best_long_form``, and the difference is not cosmetic. That
#: function is the greedy matcher: it walks right-to-left and returns the first
#: alignment it reaches, so asking it whether a span validates from its own head
#: answers "is the greedy answer this span", not "does an alignment from this
#: head exist". Used as a gate it silently discards every candidate longer than
#: the greedy one — precisely the set a truncation fix has to choose from. A
#: first pass of this experiment used it and had ``proton pump inhibitors`` and
#: ``International Index of Erectile Function`` absent from the candidate set
#: entirely; no signal could have recovered them.
_REFERENCE_RULE = next(s for s in STRATEGIES if s.name == "anchInit_placeWithin_skipAny")


# ---------------------------------------------------------------------------
# candidate space -- run_rerank.py's enumeration, plus the admissibility gate
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Candidate:
    """One long-form span the greedy walk could legitimately have returned.

    Attributes:
        span: The span exactly as it would be reported.
        words: Case-folded tokens of the span, in order.
        previous: Case-folded token immediately before the span, or ``None``.
            Read for context only; it never enlarges the candidate space.
    """

    span: str
    words: Tuple[str, ...]
    previous: Optional[str]


@dataclass(frozen=True)
class BracketCase:
    """A bracketed short form and the admissible spans preceding it, shortest first."""

    short_form: str
    candidates: Tuple[Candidate, ...]


def enumerate_case(text: str, bracket: re.Match[str]) -> Optional[BracketCase]:
    """Build the candidate set for one bracket.

    The enumeration is ``bench/run_rerank.py``'s, unchanged: every start boundary
    in the trailing 14-word window, latest start first so that an equal score
    keeps the shorter span.

    Args:
        text: The source document.
        bracket: A match of the parenthetical pattern.

    Returns:
        The case, or ``None`` when the bracket is not a short form or nothing
        admissible precedes it.
    """
    short_form = bracket.group(1).strip()
    if not is_valid_short_form(short_form, min_length=2, max_length=10):
        return None
    every = split_long_form(text[: bracket.start()])
    words = every[-_WINDOW:]
    offset = len(every) - len(words)
    folded_all = [word.casefold() for word, _start, _end in words]
    folded_short = short_form.casefold()

    candidates: List[Candidate] = []
    for index in reversed(range(len(words))):
        span = text[words[index][1] : bracket.start()].strip().rstrip(",;:( ").strip()
        if not span:
            continue
        folded = tuple(folded_all[index:])
        if match(folded_short, folded, _REFERENCE_RULE, 0) is None:
            continue  # no alignment anchored on this span's own head word
        if not is_valid_long_form(short_form, span):
            continue
        before = offset + index - 1
        candidates.append(
            Candidate(
                span=span,
                words=folded,
                previous=every[before][0].casefold() if before >= 0 else None,
            )
        )
    if not candidates:
        return None
    return BracketCase(short_form=short_form, candidates=tuple(candidates))


def build_cases(documents: Sequence) -> Dict[str, List[BracketCase]]:
    """Enumerate every bracket's candidate set once, for reuse across arms."""
    cases: Dict[str, List[BracketCase]] = {}
    for document in documents:
        found: List[BracketCase] = []
        for bracket in _PAREN.finditer(document.text):
            case = enumerate_case(document.text, bracket)
            if case is not None:
                found.append(case)
        cases[document.uid] = found
    return cases


# ---------------------------------------------------------------------------
# selection rules
# ---------------------------------------------------------------------------
Rule = Callable[[TermStatistics, BracketCase], Candidate]


def rule_shortest(_stats: TermStatistics, case: BracketCase) -> Candidate:
    """Control: the shortest admissible span, which is the greedy rule's answer."""
    return case.candidates[0]


def _argmax(
    stats: TermStatistics, case: BracketCase, score: Callable[[Candidate], float]
) -> Candidate:
    """Highest-scoring candidate; ties keep the shorter span."""
    chosen = case.candidates[0]
    best = score(chosen)
    for candidate in case.candidates[1:]:
        value = score(candidate)
        if value > best:
            chosen, best = candidate, value
    return chosen


def rule_argmax_contrast(stats: TermStatistics, case: BracketCase) -> Candidate:
    """Argmax of the span's left-edge contrast."""
    return _argmax(stats, case, lambda c: stats.edge_contrast(c.previous, c.words))


def rule_argmax_cohesion(stats: TermStatistics, case: BracketCase) -> Candidate:
    """Argmax of the span's mean internal association."""
    return _argmax(stats, case, lambda c: stats.cohesion(c.words))


def rule_argmax_both(stats: TermStatistics, case: BracketCase) -> Candidate:
    """Argmax of contrast plus cohesion, unweighted."""
    return _argmax(
        stats, case, lambda c: stats.edge_contrast(c.previous, c.words) + stats.cohesion(c.words)
    )


def rule_argmax_full(stats: TermStatistics, case: BracketCase) -> Candidate:
    """Argmax over all three statistics, unweighted apart from the head terms.

    Deliberately not fitted. A weight vector tuned on the dev half would make the
    result a statement about the fit rather than about the statistics, and this
    project has already paid once for a preset tuned to what it could see.
    """
    return _argmax(
        stats,
        case,
        lambda c: (
            stats.edge_contrast(c.previous, c.words)
            + stats.cohesion(c.words)
            + 0.5 * stats.left_boundary(c.words[0])
            + 0.5 * stats.specificity(c.words[0])
        ),
    )


def rule_extend_content(_stats: TermStatistics, case: BracketCase) -> Candidate:
    """Control: extend left while every word added is not a function word.

    The extension rule's shape with a hard-coded stop list in place of the
    statistics. Statistics that cannot beat this have not earned their size.
    """
    chosen = case.candidates[0]
    for candidate in case.candidates[1:]:
        added = len(candidate.words) - len(chosen.words)
        if all(word not in SKIPPABLE for word in candidate.words[:added]):
            chosen = candidate
        else:
            break
    return chosen


def make_extend_rule(threshold: float) -> Rule:
    """Build the association-driven left-extension rule.

    Starting from the greedy answer, the left edge moves outward one admissible
    candidate at a time. An extension is accepted only when *every* adjacency it
    introduces — including the junction with the previous head word — reaches
    ``threshold``. The walk stops at the first junction the corpus has no
    evidence for, so a span can never grow across a boundary the language does
    not support.

    Args:
        threshold: Minimum association for a newly introduced adjacency.

    Returns:
        The selection rule.
    """

    def rule(stats: TermStatistics, case: BracketCase) -> Candidate:
        chosen = case.candidates[0]
        for candidate in case.candidates[1:]:
            added = len(candidate.words) - len(chosen.words)
            if all(
                stats.association(candidate.words[index], candidate.words[index + 1]) >= threshold
                for index in range(added)
            ):
                chosen = candidate
            else:
                break
        return chosen

    return rule


def select(
    cases: Dict[str, List[BracketCase]], stats: TermStatistics, rule: Rule
) -> Dict[str, List[Pair]]:
    """Apply ``rule`` to every bracket.

    Args:
        cases: Pre-enumerated candidate sets.
        stats: Statistics derived from the dev half.
        rule: Selection rule.

    Returns:
        ``{document uid: [(short form, long form), ...]}``.
    """
    predictions: Dict[str, List[Pair]] = {}
    for uid, bracket_cases in cases.items():
        predictions[uid] = [(case.short_form, rule(stats, case).span) for case in bracket_cases]
    return predictions


# ---------------------------------------------------------------------------
# diagnostics
# ---------------------------------------------------------------------------
def _gold_keys(document: object) -> set:
    """Scorer-compatible ``(short form, long form)`` keys for one document."""
    return {
        (pair.short_form.casefold(), " ".join(pair.long_form.split()).casefold())
        for pair in document.pairs  # type: ignore[attr-defined]
    }


def _key(case: BracketCase, candidate: Candidate) -> Tuple[str, str]:
    """Scorer-compatible key for one candidate."""
    return (case.short_form.casefold(), " ".join(candidate.span.split()).casefold())


def reachability(
    documents: Sequence, cases: Dict[str, List[BracketCase]]
) -> Tuple[int, int, int, int]:
    """What selectors of increasing ambition could reach over this space.

    Three ceilings, and they are not the same number:

    * **space** — gold present among the enumerated start boundaries. This is
      the quantity D-011 measured and the one every selection experiment has
      been reported against.
    * **gated** — gold that also survives the admissibility gate. The shortfall
      against *space* is gold no alignment anchored on that span's own head can
      explain, so no rule that respects the matching constraint may return it.
    * **greedy already right** — gold that *is* the shortest admissible
      candidate. This is what the greedy rule gets for free over this space, and
      the shortfall of *gated* against it is the entire headroom available to any
      rule that only moves the left edge outward.

    Args:
        documents: Gold documents.
        cases: Pre-enumerated candidate sets.

    Returns:
        ``(gold pairs, space, gated, greedy already right)``.
    """
    gold_total = ungated = gated = already = 0
    for document in documents:
        gold = _gold_keys(document)
        gold_total += len(gold)
        after: set = set()
        greedy: set = set()
        for case in cases.get(document.uid, []):
            greedy.add(_key(case, case.candidates[0]))
            for candidate in case.candidates:
                after.add(_key(case, candidate))
        already += len(gold & greedy)
        before: set = set()
        for bracket in _PAREN.finditer(document.text):
            short_form = bracket.group(1).strip()
            if not is_valid_short_form(short_form, min_length=2, max_length=10):
                continue
            for _word, start, _end in split_long_form(document.text[: bracket.start()])[-_WINDOW:]:
                span = document.text[start : bracket.start()].strip().rstrip(",;:( ").strip()
                if span:
                    before.add((short_form.casefold(), " ".join(span.split()).casefold()))
        ungated += len(gold & before)
        gated += len(gold & after)
    return gold_total, ungated, gated, already


def evidence_audit(
    documents: Sequence, cases: Dict[str, List[BracketCase]], stats: TermStatistics
) -> Tuple[int, int]:
    """How much evidence the corpus holds where a left extension is actually needed.

    For every bracket whose gold span is admissible but is *not* the shortest
    admissible span, the extension rule must clear every adjacency it introduces.
    This counts how often the weakest of those adjacencies has no evidence at all
    — the pair was seen fewer than :attr:`TermStatistics.min_count` times — which
    separates "the signal is wrong" from "the corpus is too small to carry it".

    Args:
        documents: Gold documents.
        cases: Pre-enumerated candidate sets.
        stats: The derived statistics.

    Returns:
        ``(brackets needing an extension, of which the weakest new junction has
        no evidence)``.
    """
    needed = blind = 0
    for document in documents:
        gold = _gold_keys(document)
        for case in cases.get(document.uid, []):
            target = next((i for i, c in enumerate(case.candidates) if _key(case, c) in gold), None)
            if target is None or target == 0:
                continue
            needed += 1
            base, goal = case.candidates[0], case.candidates[target]
            added = len(goal.words) - len(base.words)
            weakest = min(
                stats.association(goal.words[index], goal.words[index + 1])
                for index in range(added)
            )
            if weakest <= 0.0:
                blind += 1
    return needed, blind


def extension_audit(
    documents: Sequence, cases: Dict[str, List[BracketCase]], stats: TermStatistics, rule: Rule
) -> Tuple[int, int, int]:
    """What the rule's departures from the greedy answer actually cost.

    Args:
        documents: Gold documents.
        cases: Pre-enumerated candidate sets.
        stats: The derived statistics.
        rule: Selection rule.

    Returns:
        ``(spans moved off the greedy answer, of those that reached gold, of
        those that destroyed a greedy answer which was already correct)``.
    """
    moved = reached = destroyed = 0
    for document in documents:
        gold = _gold_keys(document)
        for case in cases.get(document.uid, []):
            base = case.candidates[0]
            chosen = rule(stats, case)
            if chosen is base:
                continue
            moved += 1
            if _key(case, chosen) in gold:
                reached += 1
            elif _key(case, base) in gold:
                destroyed += 1
    return moved, reached, destroyed


def score_arm(
    half: Sequence, cases: Dict[str, List[BracketCase]], stats: TermStatistics, rule: Rule
) -> scoring.Score:
    """Exact-match P/R/F1 for one arm on one half."""
    return scoring.evaluate(
        half,
        dedupe_per_document(select(cases, stats, rule)),
        corpus="med1250",
        system="termfreq",
    ).scores["exact"]


def row(label: str, score: scoring.Score) -> str:
    """One aligned result line."""
    return (
        f"{label:<36} {score.precision * 100:7.2f} {score.recall * 100:7.2f} {score.f1 * 100:7.2f}"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="*",
        default=[0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40],
        help="association thresholds for the extension rule, swept on the dev half",
    )
    parser.add_argument("--min-count", type=int, default=3, help="evidence floor for a pair")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    dev, test = split_corpus(corpora.load("med1250"))
    stats = build_statistics((document.text for document in dev), min_count=args.min_count)
    words, pairs = stats.size()
    print(f"split (seed {SPLIT_SEED}): dev {len(dev)} docs, test {len(test)} docs")
    print(f"statistics from dev text only, no labels read: {words} words, {pairs} adjacent pairs")

    dev_cases = build_cases(dev)
    test_cases = build_cases(test)
    gold, ungated, gated, already = reachability(test, test_cases)
    needed, blind = evidence_audit(dev, dev_cases, stats)
    print(f"\ntest gold pairs                          : {gold}")
    print(f"  reachable in the enumerated space      : {ungated}")
    print(f"  reachable after the admissibility gate : {gated}")
    print(f"  already the shortest admissible span   : {already}")
    print("\ndev brackets where gold needs a left extension at all")
    print(f"  count                                  : {needed}")
    print(f"  weakest new junction has no evidence   : {blind}")

    arms: List[Tuple[str, str, Rule]] = [
        ("shortest", "termfreq.med1250_test.shortest", rule_shortest),
        (
            "extend/content-word (control)",
            "termfreq.med1250_test.extend_content",
            rule_extend_content,
        ),
        ("argmax/contrast", "termfreq.med1250_test.argmax_contrast", rule_argmax_contrast),
        ("argmax/cohesion", "termfreq.med1250_test.argmax_cohesion", rule_argmax_cohesion),
        ("argmax/contrast+cohesion", "termfreq.med1250_test.argmax_both", rule_argmax_both),
        ("argmax/full", "termfreq.med1250_test.argmax_full", rule_argmax_full),
    ]
    for threshold in args.thresholds:
        arms.append(
            (
                f"extend/association >= {threshold:.2f}",
                f"termfreq.med1250_test.extend_t{threshold:.2f}",
                make_extend_rule(threshold),
            )
        )

    # -- everything decided on dev -----------------------------------------
    dev_baseline = scoring.evaluate(
        dev, dedupe_per_document(predict_acronymkit(dev)), corpus="med1250", system="tier0"
    ).scores["exact"]
    print(f"\nDEV (every choice is made here){'':<5} {'P %':>7} {'R %':>7} {'F1 %':>7}")
    print("-" * 60)
    print(row("tier0 greedy (Schwartz & Hearst)", dev_baseline))
    dev_scores: Dict[str, scoring.Score] = {}
    best_label: Optional[str] = None
    best_f1 = -1.0
    for label, _run_id, rule in arms:
        score = score_arm(dev, dev_cases, stats, rule)
        dev_scores[label] = score
        print(row(label, score))
        if label.startswith(("argmax", "extend/association")) and score.f1 > best_f1:
            best_f1, best_label = score.f1, label

    # -- reported on test ---------------------------------------------------
    baseline = scoring.evaluate(
        test, dedupe_per_document(predict_acronymkit(test)), corpus="med1250", system="tier0"
    ).scores["exact"]
    print(f"\nTEST (held out){'':<21} {'P %':>7} {'R %':>7} {'F1 %':>7}")
    print("-" * 60)
    print(row("tier0 greedy (Schwartz & Hearst)", baseline))
    recorded: Dict[str, dict] = {
        "termfreq.med1250_test.tier0": {
            "split_seed": SPLIT_SEED,
            "test_documents": len(test),
            "dev_exact_f1": round(dev_baseline.f1 * 100, 2),
            "exact_precision": round(baseline.precision * 100, 2),
            "exact_recall": round(baseline.recall * 100, 2),
            "exact_f1": round(baseline.f1 * 100, 2),
        },
        "termfreq.med1250_test.space": {
            "split_seed": SPLIT_SEED,
            "test_gold_pairs": gold,
            "space_reachable": ungated,
            "gated_reachable": gated,
            "greedy_already_correct": already,
            "statistics_words": words,
            "statistics_pairs": pairs,
            "statistics_min_count": args.min_count,
            "dev_brackets_needing_extension": needed,
            "dev_extensions_without_evidence": blind,
        },
    }
    for label, run_id, rule in arms:
        score = score_arm(test, test_cases, stats, rule)
        moved, reached, destroyed = extension_audit(test, test_cases, stats, rule)
        selected = label == best_label
        print(
            row(label + ("  <- dev-selected" if selected else ""), score)
            + f"   moved {moved:4d}  reached {reached:3d}  destroyed {destroyed:3d}"
        )
        recorded[run_id] = {
            "split_seed": SPLIT_SEED,
            "rule": label,
            "dev_selected": selected,
            "dev_exact_f1": round(dev_scores[label].f1 * 100, 2),
            "exact_precision": round(score.precision * 100, 2),
            "exact_recall": round(score.recall * 100, 2),
            "exact_f1": round(score.f1 * 100, 2),
            "spans_moved_off_greedy": moved,
            "moves_reaching_gold": reached,
            "moves_destroying_a_correct_answer": destroyed,
        }

    if best_label is not None:
        chosen = next(run_id for label, run_id, _ in arms if label == best_label)
        print(
            f"\ndev-selected arm: {best_label}\n"
            f"  dev  F1 {recorded[chosen]['dev_exact_f1']:.2f} "
            f"against tier0 {recorded['termfreq.med1250_test.tier0']['dev_exact_f1']:.2f}\n"
            f"  test F1 {recorded[chosen]['exact_f1']:.2f} "
            f"against tier0 {recorded['termfreq.med1250_test.tier0']['exact_f1']:.2f}"
        )

    if args.save:
        print(f"\nsaved to {save_results(recorded).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
