#!/usr/bin/env python3
"""First external evaluation of ``acronymkit.disambiguation``.

Why this exists
---------------
``docs/EVALUATION.md`` has said for three rounds that "generation, backronym
alignment and disambiguation have no external evaluation at all". Generation now
has one. This closes disambiguation, which is a third of the library's public
surface and until now had nothing behind it but doctests.

The corpus is SDU@AAAI-21 shared task 2 (acronym disambiguation). It is the
right corpus for exactly one reason: it ships ``diction.json``, a candidate set
per acronym, so the task it poses is *selection* — which is precisely and only
what :class:`~acronymkit.disambiguation.LexicalDisambiguator` does. No pairing
assumption, no derived gold, nothing invented (see ``bench/splits.toml`` for why
that mattered enough to leave this undone for three rounds).

The convention, taken from the shared task's own ``scorer.py``
-------------------------------------------------------------
Read the pinned copy at ``data/sdu21_ad_scorer.py``; it is reimplemented here
rather than imported so that a checkout without the download still runs, and it
is reimplemented *faithfully*, quirks included:

* A prediction is correct iff it is **exactly equal** to the gold expansion
  string. Gold expansions are verbatim keys from ``diction.json``, so re-casing
  or re-spacing an otherwise right answer scores zero. There is no relaxed
  convention here and inventing one would make our number incomparable.
* The **headline metric is macro-averaged P/R/F1** over gold expansion classes,
  not accuracy. Accuracy is reported by ``-v`` and is what most readers actually
  want, so both are reported here, always labelled.
* Two quirks are reproduced deliberately. Macro precision credits a gold class
  that was *never predicted* with a precision of ``1.0`` (``scorer.py`` line 39,
  ``... if exp in pred_per_expansion else 1``), and classes predicted but never
  gold contribute to no average at all. This inflates macro precision for a
  system that predicts few distinct expansions — which is why the shared task's
  own baseline posts 89.03 % precision against 44.94 % recall. Deviating would
  make our numbers incomparable with the published ones; correcting someone
  else's metric silently is worse than reporting it as defined.
* Every instance receives exactly one prediction, so micro P, micro R, micro F1
  and accuracy are all the same number by construction. Reported once as
  accuracy, with the identity stated rather than four columns of the same digit.

The harness is validated the way ``run_extraction.py`` is validated by
``pyab3p``: the shared task publishes official scores for its own
most-frequent-expansion baseline, this file reimplements that baseline, and the
run prints whether the reproduction lands on the published figures. If it does
not, the reader or the scorer is wrong and no other number on the page is worth
reading.

Systems
-------
``acronymkit``
    :class:`~acronymkit.disambiguation.LexicalDisambiguator` at stock
    :class:`~acronymkit.config.Config` defaults, given the sentence as context.
    Nothing is tuned. It reads no training data.
``most_frequent``
    The shared task's own baseline: pick the expansion with the highest count in
    ``train.json``, ties broken by dictionary order. **This is the number that
    matters.** If picking the most common expansion beats context scoring, then
    context scoring is contributing nothing, and that is the single most
    important thing this evaluation can report.
``random``
    Uniform choice among the candidates under a frozen seed, to give the other
    two a scale. Reported next to the analytic expectation ``mean(1/k)``.

Usage::

    python tools/fetch_data.py sdu21-ad-diction sdu21-ad-dev sdu21-ad-train
    python bench/run_disambiguation.py --save
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit.config import Config  # noqa: E402
from acronymkit.disambiguation import ExpansionDictionary, LexicalDisambiguator  # noqa: E402
from bench import corpora  # noqa: E402
from bench.corpora import DisambiguationInstance  # noqa: E402
from bench.run_extraction import save_results  # noqa: E402

#: Frozen seed for the random baseline. Shares the value used by
#: ``bench/run_cascade.py`` for its document split so the project has one magic
#: number rather than two; it selects nothing here, it only makes the noise
#: floor reproducible.
RANDOM_SEED = 20260809

#: Official scores published for the shared task's own most-frequent baseline on
#: ``dev.json`` (README.md of the pinned repository, macro P / R / F1 as
#: percentages). Not a claim of ours: a fixture our reimplementation is checked
#: against, the way pyab3p's published MED1250 figures check the extraction
#: harness.
PUBLISHED_MOST_FREQUENT = (89.03, 44.94, 59.73)

#: Candidate-count buckets. 2-way and 20-way disambiguation are different
#: problems and a single accuracy hides that completely, so the small arities
#: are reported exactly and only the sparse tail is grouped.
BUCKETS: tuple[tuple[str, int, int], ...] = (
    ("2", 2, 2),
    ("3", 3, 3),
    ("4", 4, 4),
    ("5", 5, 5),
    ("6-9", 6, 9),
    ("10+", 10, 10**6),
)


#: Tokens that a detokeniser would glue to the preceding word. Used only by the
#: robustness check below, never by the reported run.
_CLOSING = set(",.;:)]}%!?") | {"'s", "n't", "'re", "'ve", "'ll", "'m", "'d"}


def attached_context(instance: DisambiguationInstance) -> str:
    """Rejoin the tokens with punctuation attached rather than spaced.

    The corpus ships tokens, so the harness has to pick a join, and a harness
    choice that moves the result is a harness that is measuring itself. This is
    the plausible alternative to :attr:`DisambiguationInstance.context`; the run
    scores both and prints the difference so the choice is visible rather than
    assumed harmless.

    Args:
        instance: The instance whose tokens to join.

    Returns:
        The sentence with closing punctuation and clitics attached to the token
        before them, and nothing inserted after an opening bracket.
    """
    parts: list[str] = []
    for token in instance.tokens:
        if parts and (token in _CLOSING or parts[-1][-1:] in "([{"):
            parts[-1] += token
        else:
            parts.append(token)
    return " ".join(parts)


def bucket_of(candidate_count: int) -> str:
    """Return the label of the candidate-count bucket ``candidate_count`` falls in."""
    for label, low, high in BUCKETS:
        if low <= candidate_count <= high:
            return label
    raise ValueError(f"no bucket for {candidate_count} candidates")  # pragma: no cover


# ---------------------------------------------------------------------------
# the shared task's metric, reimplemented
# ---------------------------------------------------------------------------
def score_expansion(gold: Sequence[str], predicted: Sequence[str]) -> dict[str, float]:
    """Score predictions exactly as ``scorer.py`` from the shared task does.

    Args:
        gold: Gold expansions, one per instance.
        predicted: Predicted expansions, aligned with ``gold``.

    Returns:
        ``accuracy``, ``micro_precision``/``micro_recall``/``micro_f1`` and
        ``macro_precision``/``macro_recall``/``macro_f1``, all as percentages.

    Raises:
        ValueError: If the two sequences differ in length, which would silently
            misalign every instance.
    """
    if len(gold) != len(predicted):
        raise ValueError(f"gold has {len(gold)} instances, predictions {len(predicted)}")

    correct_per_expansion: dict[str, int] = defaultdict(int)
    total_per_expansion: dict[str, int] = defaultdict(int)
    pred_per_expansion: dict[str, int] = defaultdict(int)
    expansions: set[str] = set()

    for want, got in zip(gold, predicted):
        expansions.add(want)
        total_per_expansion[want] += 1
        pred_per_expansion[got] += 1
        if want == got:
            correct_per_expansion[want] += 1

    correct = sum(correct_per_expansion.values())
    accuracy = correct / len(gold) if gold else 0.0

    micro_precision = correct / sum(pred_per_expansion.values())
    micro_recall = correct / sum(total_per_expansion.values())
    micro_f1 = _f1(micro_precision, micro_recall)

    # The ``else 1`` is verbatim from the reference scorer: a gold class nobody
    # predicted is credited with perfect precision. See the module docstring.
    precisions = [
        (correct_per_expansion[exp] / pred_per_expansion[exp]) if exp in pred_per_expansion else 1.0
        for exp in expansions
    ]
    recalls = [correct_per_expansion[exp] / total_per_expansion[exp] for exp in expansions]
    macro_precision = sum(precisions) / len(precisions)
    macro_recall = sum(recalls) / len(recalls)

    return {
        "accuracy": accuracy * 100,
        "micro_precision": micro_precision * 100,
        "micro_recall": micro_recall * 100,
        "micro_f1": micro_f1 * 100,
        "macro_precision": macro_precision * 100,
        "macro_recall": macro_recall * 100,
        "macro_f1": _f1(macro_precision, macro_recall) * 100,
    }


def _f1(precision: float, recall: float) -> float:
    """Harmonic mean, zero when both operands are zero."""
    total = precision + recall
    return 2 * precision * recall / total if total else 0.0


# ---------------------------------------------------------------------------
# systems
# ---------------------------------------------------------------------------
def predict_acronymkit(
    instances: Sequence[DisambiguationInstance],
    dictionary: ExpansionDictionary,
    *,
    context_of: Optional[object] = None,
) -> tuple[list[str], float, dict[str, int]]:
    """Run the shipped disambiguator over every instance.

    Stock ``Config()``. The prediction is ``result.primary_expansion`` — what a
    caller gets from the public API — with no post-processing and no snapping
    back to the dictionary. A caller who asked "what does this acronym mean" is
    handed that string, so that string is what gets scored.

    Args:
        instances: The corpus.
        dictionary: Candidate index, built from ``diction.json``.
        context_of: Optional callable overriding how a context string is built
            from an instance; used only by the detokenisation robustness check.

    Returns:
        ``(predictions, elapsed_seconds, diagnostics)``. Diagnostics count how
        often an inline definition won the top slot and how often that inline
        win overrode a dictionary candidate that was in fact correct.
    """
    engine = LexicalDisambiguator(Config(), dictionary)
    to_context = context_of if callable(context_of) else (lambda item: item.context)

    predictions: list[str] = []
    diagnostics = {"inline_top1": 0, "inline_override_cost": 0, "no_candidate": 0}

    started = time.perf_counter()
    for instance in instances:
        result = engine.disambiguate(instance.acronym, to_context(instance))
        predictions.append(result.primary_expansion or "")
        if not result.candidates:
            diagnostics["no_candidate"] += 1
            continue
        if result.candidates[0].source != "inline":
            continue
        diagnostics["inline_top1"] += 1
        if result.primary_expansion == instance.expansion:
            continue
        from_dictionary = [c for c in result.candidates if c.source == "dictionary"]
        if from_dictionary and from_dictionary[0].expansion == instance.expansion:
            diagnostics["inline_override_cost"] += 1
    elapsed = time.perf_counter() - started
    return predictions, elapsed, diagnostics


def predict_most_frequent(
    instances: Sequence[DisambiguationInstance],
    diction: dict[str, list[str]],
    train: Sequence[DisambiguationInstance],
) -> list[str]:
    """The shared task's own baseline, reimplemented from ``code/most_frequent.py``.

    Counts every gold expansion in ``train.json`` and, for each instance, picks
    the candidate with the highest count. Ties go to whichever tied candidate
    appears first in the dictionary, and an acronym whose candidates were all
    unseen in training falls back to the first listed — both behaviours are the
    reference implementation's, reproduced so the published figures are
    reachable.

    Args:
        instances: The instances to predict.
        diction: The candidate sets.
        train: Training instances, read only for their gold expansions.

    Returns:
        One prediction per instance.
    """
    frequency: dict[str, int] = {
        expansion: 0 for expansions in diction.values() for expansion in expansions
    }
    for instance in train:
        if instance.expansion in frequency:
            frequency[instance.expansion] += 1

    predictions: list[str] = []
    for instance in instances:
        candidates = diction[instance.acronym]
        best, best_score = "", 0
        for candidate in candidates:
            if frequency.get(candidate, 0) > best_score:
                best, best_score = candidate, frequency[candidate]
        predictions.append(best or candidates[0])
    return predictions


def predict_random(
    instances: Sequence[DisambiguationInstance],
    diction: dict[str, list[str]],
    seed: int = RANDOM_SEED,
) -> tuple[list[str], float]:
    """Uniform choice among the candidates.

    Args:
        instances: The instances to predict.
        diction: The candidate sets.
        seed: Frozen seed, so the noise floor is reproducible.

    Returns:
        ``(predictions, expected_accuracy_pct)``, the second being the analytic
        expectation ``mean(1/k)`` — reported alongside the sampled figure
        because a single seed is itself a measurement with variance.
    """
    generator = random.Random(seed)
    predictions = [generator.choice(diction[instance.acronym]) for instance in instances]
    expected = sum(1 / len(diction[i.acronym]) for i in instances) / len(instances)
    return predictions, expected * 100


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def accuracy_by_bucket(
    instances: Sequence[DisambiguationInstance],
    diction: dict[str, list[str]],
    predicted: Sequence[str],
) -> dict[str, tuple[int, int]]:
    """Return ``{bucket: (instances, correct)}`` keyed by candidate count."""
    tally: dict[str, list[int]] = {label: [0, 0] for label, _, _ in BUCKETS}
    for instance, prediction in zip(instances, predicted):
        label = bucket_of(len(diction[instance.acronym]))
        tally[label][0] += 1
        tally[label][1] += int(prediction == instance.expansion)
    return {label: (counts[0], counts[1]) for label, counts in tally.items()}


def ceiling(
    instances: Sequence[DisambiguationInstance], dictionary: ExpansionDictionary
) -> tuple[int, int]:
    """How many instances a perfect selector could get right.

    The analogue of ``bench/run_oracle.py``'s own-candidate-space measurement: a
    selector cannot return what it was never offered, so every accuracy below
    should be read against this number rather than against 100.

    The candidate sets are taken from the :class:`ExpansionDictionary` the
    disambiguator actually queries, not from the raw JSON, because the index
    normalises short forms and de-duplicates expansions. If that normalisation
    merged two acronyms or dropped a gold expansion, the ceiling would fall and
    the run would say so.

    Args:
        instances: The corpus.
        dictionary: The index under test.

    Returns:
        ``(instances, reachable)``.
    """
    reachable = sum(1 for i in instances if i.expansion in dictionary.candidates(i.acronym))
    return len(instances), reachable


def _row(label: str, scores: dict[str, float], extra: str = "") -> str:
    """One aligned system row."""
    return (
        f"{label:<16} {scores['accuracy']:8.2f} {scores['macro_precision']:8.2f} "
        f"{scores['macro_recall']:8.2f} {scores['macro_f1']:8.2f}  {extra}"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="dev", choices=("dev", "train"))
    parser.add_argument("--limit", type=int, default=0, help="smoke-test on the first N instances")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    if args.limit and args.save:
        raise SystemExit("--limit produces a partial number; refusing to --save it")

    diction = corpora.read_sdu21_ad_diction()
    instances = corpora.read_sdu21_ad(split=args.split)
    train = corpora.read_sdu21_ad(split="train")
    if args.limit:
        instances = instances[: args.limit]

    dictionary = ExpansionDictionary(diction)
    gold = [instance.expansion for instance in instances]

    total, reachable = ceiling(instances, dictionary)
    mean_candidates = sum(len(diction[i.acronym]) for i in instances) / total

    print(f"corpus            : sdu21_ad ({args.split})")
    print(f"instances         : {total:,}")
    print(f"distinct acronyms : {len({i.acronym for i in instances}):,}")
    print(f"dictionary        : {len(dictionary):,} short forms, {len(diction):,} raw keys")
    print(f"mean candidates   : {mean_candidates:.2f}")
    print("convention        : exact string equality; macro P/R/F1 is the official metric")
    print(
        f"\nCEILING: the gold expansion is among the candidates for "
        f"{reachable:,} of {total:,} instances ({reachable / total * 100:.2f}%)."
    )
    print(
        "Nothing here is a coverage problem. Every point below the ceiling is a\n"
        "selection failure, which is the only kind of failure this corpus can show."
    )

    predictions: dict[str, list[str]] = {}
    scores: dict[str, dict[str, float]] = {}

    ours, elapsed, diagnostics = predict_acronymkit(instances, dictionary)
    predictions["acronymkit"] = ours
    predictions["most_frequent"] = predict_most_frequent(instances, diction, train)
    random_predictions, random_expected = predict_random(instances, diction)
    predictions["random"] = random_predictions

    for system, predicted in predictions.items():
        scores[system] = score_expansion(gold, predicted)

    print(f"\n{'system':<16} {'acc %':>8} {'macroP':>8} {'macroR':>8} {'macroF1':>8}")
    print("-" * 62)
    print(_row("acronymkit", scores["acronymkit"], f"{total / max(elapsed, 1e-9):,.0f} inst/s"))
    print(_row("most_frequent", scores["most_frequent"], "shared task baseline"))
    print(_row("random", scores["random"], f"expected {random_expected:.2f}%"))
    print("-" * 62)
    print("accuracy == micro P == micro R == micro F1: every instance gets one prediction.")

    published = (
        abs(scores["most_frequent"]["macro_precision"] - PUBLISHED_MOST_FREQUENT[0]) < 0.01
        and abs(scores["most_frequent"]["macro_recall"] - PUBLISHED_MOST_FREQUENT[1]) < 0.01
        and abs(scores["most_frequent"]["macro_f1"] - PUBLISHED_MOST_FREQUENT[2]) < 0.01
    )
    print(
        "\nharness check: our reimplementation of the shared task's baseline "
        + ("REPRODUCES" if published else "DOES NOT reproduce")
        + " its published\nofficial scores"
        + (
            ", so the reader and the scorer agree with the task's own."
            if published
            else " -- treat every number above as unverified until this is fixed."
        )
    )

    print(f"\naccuracy % by number of candidate expansions\n{'system':<16}", end="")
    for label, _, _ in BUCKETS:
        print(f"{label:>9}", end="")
    print()
    buckets = {
        system: accuracy_by_bucket(instances, diction, predicted)
        for system, predicted in predictions.items()
    }
    print(f"{'n':<16}", end="")
    for label, _, _ in BUCKETS:
        print(f"{buckets['acronymkit'][label][0]:>9,}", end="")
    print()
    for system in predictions:
        print(f"{system:<16}", end="")
        for label, _, _ in BUCKETS:
            count, correct = buckets[system][label]
            print(f"{correct / count * 100:>9.2f}" if count else f"{'-':>9}", end="")
        print()

    print(
        f"\ndiagnostics: an inline definition took the top slot for "
        f"{diagnostics['inline_top1']:,} instances "
        f"({diagnostics['inline_top1'] / total * 100:.2f}%);\n"
        f"in {diagnostics['inline_override_cost']:,} of those it overrode a dictionary "
        "candidate that was correct. Inline\nexpansions are copied from the sentence, so they "
        "rarely match a lower-cased dictionary\nkey exactly -- under this convention preferring "
        "them can only cost."
    )

    attached, _, _ = predict_acronymkit(instances, dictionary, context_of=attached_context)
    attached_accuracy = score_expansion(gold, attached)["accuracy"]
    print(
        f"harness check: rejoining the tokens with punctuation attached instead of spaced "
        f"scores\n{attached_accuracy:.2f}% against {scores['acronymkit']['accuracy']:.2f}%. "
        "The one arbitrary choice in this harness does not\ncarry the result."
    )

    gap = scores["most_frequent"]["accuracy"] - scores["acronymkit"]["accuracy"]
    print(
        "\nverdict: "
        + (
            "context scoring LOSES to the majority-class prior. Quote the two "
            "accuracies, not the gap."
            if gap > 0
            else "context scoring beats the majority-class prior."
        )
    )

    if args.save:
        entries = {
            "disambiguation.sdu21.ceiling": {
                "corpus": "sdu21_ad",
                "split": args.split,
                "instances": total,
                "gold_in_candidates": reachable,
                "ceiling_accuracy": round(reachable / total * 100, 2),
                "dictionary_short_forms": len(dictionary),
                "dictionary_raw_keys": len(diction),
                "distinct_acronyms": len({i.acronym for i in instances}),
                "distinct_gold_expansions": len(set(gold)),
                "mean_candidates": round(mean_candidates, 2),
                "instances_by_candidate_count": {
                    label: buckets["acronymkit"][label][0] for label, _, _ in BUCKETS
                },
            }
        }
        for system in predictions:
            entry = {
                "corpus": "sdu21_ad",
                "split": args.split,
                "instances": total,
                "convention": "exact string equality; official metric is macro P/R/F1",
                **{key: round(value, 2) for key, value in scores[system].items()},
                "accuracy_by_candidate_count": {
                    label: round(correct / count * 100, 2) if count else None
                    for label, (count, correct) in buckets[system].items()
                },
            }
            if system == "acronymkit":
                entry["instances_per_second"] = round(total / max(elapsed, 1e-9), 1)
                entry["inline_top1"] = diagnostics["inline_top1"]
                entry["inline_override_cost"] = diagnostics["inline_override_cost"]
                entry["no_candidate"] = diagnostics["no_candidate"]
                entry["config"] = "stock Config() defaults; no tuning"
                entry["accuracy_punctuation_attached_context"] = round(attached_accuracy, 2)
            if system == "random":
                entry["seed"] = RANDOM_SEED
                entry["expected_accuracy"] = round(random_expected, 2)
            if system == "most_frequent":
                entry["trained_on"] = "sdu21_ad train.json"
                entry["train_instances"] = len(train)
                entry["reproduces_published_official_scores"] = published
            entries[f"disambiguation.sdu21.{system}"] = entry
        print(f"\nsaved to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
