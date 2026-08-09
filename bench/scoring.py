"""Metrics for abbreviation-definition extraction.

Why this file is longer than "compute P, R and F1"
--------------------------------------------------
Published numbers in this field are not directly comparable, because the papers
disagree about what counts as a correct answer. The two conventions that matter:

**Exact match.** The predicted long form must equal the annotated one after
whitespace normalisation and case folding. Strict, unambiguous, and the harder
target — a predicted ``"the central nervous system"`` fails against a gold
``"central nervous system"``.

**Relaxed match.** The predicted long form need only agree with the annotation
up to leading determiners and surrounding punctuation. This is closer to what
several published evaluations actually did, and it isolates *boundary*
disagreements from genuine misses.

Both are reported here, always, and labelled. Quoting one number without saying
which convention produced it is how comparisons in this area become dishonest by
accident.

The scorer is deliberately independent of :mod:`acronymkit`: it takes predicted
pairs as plain tuples, so a competing system can be dropped in and scored by the
same code. Numbers produced by different harnesses are not comparable; numbers
produced by this one are.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

Pair = tuple[str, str]

#: Leading words stripped under the relaxed convention. Annotators are
#: inconsistent about whether a determiner belongs to the long form, and that
#: disagreement says nothing about whether a system found the definition.
_LEADING_NOISE = re.compile(r"^(?:the|a|an|its|their|our|this|these|those)\s+", re.IGNORECASE)

#: Punctuation trimmed from either end under the relaxed convention. The en and
#: em dashes are written as escapes rather than literals so the character class
#: is unambiguous to a reader (and to the linter, which cannot tell a stray en
#: dash from an intended one).
_EN_DASH = "\u2013"
_EM_DASH = "\u2014"
_EDGE_PUNCT_CLASS = r"\s\-" + _EN_DASH + _EM_DASH + r",;:.'" + '"' + r"()\[\]"
_EDGE_PUNCT = re.compile(f"^[{_EDGE_PUNCT_CLASS}]+|[{_EDGE_PUNCT_CLASS}]+$")
_WHITESPACE = re.compile(r"\s+")


def normalise_exact(value: str) -> str:
    """Whitespace-collapse and case-fold, and nothing else."""
    return _WHITESPACE.sub(" ", value).strip().casefold()


def normalise_relaxed(value: str) -> str:
    """Also strip edge punctuation and a leading determiner."""
    text = _EDGE_PUNCT.sub("", _WHITESPACE.sub(" ", value).strip())
    text = _LEADING_NOISE.sub("", text)
    return _EDGE_PUNCT.sub("", text).strip().casefold()


@dataclass(frozen=True)
class Score:
    """Precision, recall and F1 for one matching convention."""

    convention: str
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def f1(self) -> float:
        precision, recall = self.precision, self.recall
        total = precision + recall
        return 2 * precision * recall / total if total else 0.0

    def as_row(self) -> str:
        """One aligned table row."""
        return (
            f"{self.convention:<10} {self.precision * 100:7.2f} {self.recall * 100:7.2f} "
            f"{self.f1 * 100:7.2f} {self.true_positives:7d} {self.false_positives:7d} "
            f"{self.false_negatives:7d}"
        )


@dataclass
class Evaluation:
    """Full result of scoring a system against a corpus."""

    corpus: str
    system: str
    documents: int
    gold_pairs: int
    predicted_pairs: int
    scores: dict[str, Score]
    missed: list[tuple[str, Pair]]
    spurious: list[tuple[str, Pair]]
    elapsed_seconds: float = 0.0

    def table(self) -> str:
        """Aligned P/R/F1 table across both conventions."""
        header = f"{'MATCH':<10} {'P%':>7} {'R%':>7} {'F1%':>7} {'TP':>7} {'FP':>7} {'FN':>7}"
        rule = "-" * len(header)
        rows = [self.scores[name].as_row() for name in ("exact", "relaxed") if name in self.scores]
        return "\n".join([header, rule, *rows])


def _count(gold: Sequence[str], predicted: Sequence[str], convention: str) -> Score:
    """Multiset-aware TP/FP/FN over normalised keys.

    A document that legitimately defines the same abbreviation twice should not
    have the second occurrence counted as a false positive, so matching consumes
    from a multiset rather than a set.
    """
    remaining = list(gold)
    true_positives = 0
    for item in predicted:
        if item in remaining:
            remaining.remove(item)
            true_positives += 1
    return Score(
        convention=convention,
        true_positives=true_positives,
        false_positives=len(predicted) - true_positives,
        false_negatives=len(remaining),
    )


def evaluate(
    documents: Iterable,
    predictions: dict[str, list[Pair]],
    *,
    corpus: str,
    system: str,
    elapsed_seconds: float = 0.0,
    error_limit: Optional[int] = 40,
) -> Evaluation:
    """Score ``predictions`` against the gold annotations.

    Args:
        documents: :class:`~bench.corpora.GoldDocument` objects.
        predictions: ``{document identifier: [(short_form, long_form), ...]}``.
        corpus: Corpus name, for the report.
        system: System name, for the report.
        elapsed_seconds: Wall-clock time the system took, for the report.
        error_limit: Cap on retained error examples; ``None`` keeps all.

    Returns:
        The :class:`Evaluation`, scored under both conventions.
    """
    gold_exact: list[str] = []
    pred_exact: list[str] = []
    gold_relaxed: list[str] = []
    pred_relaxed: list[str] = []
    missed: list[tuple[str, Pair]] = []
    spurious: list[tuple[str, Pair]] = []
    document_count = 0
    gold_total = 0
    predicted_total = 0

    for document in documents:
        document_count += 1
        predicted = predictions.get(document.uid, [])
        gold_total += len(document.pairs)
        predicted_total += len(predicted)

        def key(pair: Pair, relaxed: bool) -> str:
            short, long_form = pair
            fold = normalise_relaxed if relaxed else normalise_exact
            return f"{normalise_exact(short)}\x00{fold(long_form)}"

        gold_pairs = [(p.short_form, p.long_form) for p in document.pairs]
        for relaxed, gold_bucket, pred_bucket in (
            (False, gold_exact, pred_exact),
            (True, gold_relaxed, pred_relaxed),
        ):
            gold_bucket.extend(key(p, relaxed) for p in gold_pairs)
            pred_bucket.extend(key(p, relaxed) for p in predicted)

        # Error examples use the relaxed convention: an exact-only mismatch is a
        # boundary quibble, not the kind of error worth reading a list of.
        gold_keys = [key(p, True) for p in gold_pairs]
        pred_keys = [key(p, True) for p in predicted]
        for pair, k in zip(gold_pairs, gold_keys):
            if k not in pred_keys and (error_limit is None or len(missed) < error_limit):
                missed.append((document.identifier, pair))
        for pair, k in zip(predicted, pred_keys):
            if k not in gold_keys and (error_limit is None or len(spurious) < error_limit):
                spurious.append((document.identifier, pair))

    return Evaluation(
        corpus=corpus,
        system=system,
        documents=document_count,
        gold_pairs=gold_total,
        predicted_pairs=predicted_total,
        scores={
            "exact": _count(gold_exact, pred_exact, "exact"),
            "relaxed": _count(gold_relaxed, pred_relaxed, "relaxed"),
        },
        missed=missed,
        spurious=spurious,
        elapsed_seconds=elapsed_seconds,
    )
