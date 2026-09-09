#!/usr/bin/env python3
"""Calibrated refusal, measured: split conformal over the shipped disambiguator.

What this run is for
--------------------
``disambiguation.sdu21.abstention_curve`` publishes what a *margin* gate buys:
precision, at the cost of coverage and F1, at a threshold nobody can defend as
the caller's. :mod:`acronymkit.conformal` replaces the threshold with a target
error rate ``alpha`` plus a calibration set, and hands back a distribution-free
guarantee -- distribution-free, and not assumption-free: it holds under
exchangeability between the calibration data and the data the gate is asked
about, which is question 3 below. This file is the evidence that the machinery
does what the theory says on this corpus, and -- more usefully -- the evidence
for the three places the theory says less than a reader will assume.

The four questions
------------------
1. **Does empirical coverage land on nominal?** Measured on a seeded random
   split of the corpus, which is exchangeable *by construction*, so a divergence
   here is an implementation defect and not a finding.
2. **Does Mondrian (per-arity) calibration beat marginal?** Not assumed. The
   comparison is the worst per-arity deviation from nominal under each.
3. **What does violating exchangeability cost?** Measured by re-splitting so
   that no acronym appears in both halves -- a within-corpus stand-in for the
   out-of-domain caller the guarantee excludes.
4. **Is the answer worth having?** Measured against the shared task's own
   most-frequent-expansion baseline **on conformal's own answered subset**, which
   is the column ``disambiguation.sdu21.abstention_curve`` insists on, and
   against the margin gate at a matched answer rate.

What this run does NOT do
-------------------------
It does not touch SDU-21 AD ``test.json``. That arm is reserved by D-043 for
confirming the cut-point of an abstention policy proposed for on-by-default
shipping, and no such proposal is made here: conformal ships **off** until the
caller supplies a calibration set, which is the opposite of a default. Every
figure below therefore comes from a corpus ``bench/splits.toml`` declares
``role = "tuning"`` and ``contaminated = true``, and none of them is evidence of
generalisation. They are evidence that the machinery is correctly implemented
and that its guarantee is narrower than its name suggests.

Counts, not seconds
-------------------
R17: every rate below ships with the work that produced it -- instances scored,
distinct acronyms, candidates scored, calibration size per group. R18: the one
wall-clock figure is an unarmed note with the machine named in
``environment``.

Usage::

    python tools/fetch_data.py sdu21-ad-diction sdu21-ad-dev sdu21-ad-train
    python bench/run_conformal.py                 # report, record nothing
    python bench/run_conformal.py --save          # record into bench/results.json
    python bench/run_conformal.py --no-governed   # skip the governed-fit probe
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit.config import Config  # noqa: E402
from acronymkit.conformal import (  # noqa: E402
    ASSUMPTION,
    ConformalGate,
    arity_group,
    smallest_calibration_size,
)
from acronymkit.disambiguation import ExpansionDictionary, LexicalDisambiguator  # noqa: E402
from acronymkit.models import DisambiguationResult  # noqa: E402
from bench import corpora  # noqa: E402
from bench.corpora import DisambiguationInstance  # noqa: E402
from bench.run_extraction import environment, save_results  # noqa: E402

#: Frozen seed for the calibration/evaluation split. Shares the value the other
#: disambiguation runners use so the project has one magic number rather than
#: three; it selects nothing, it only makes the split reproducible.
RANDOM_SEED = 20260809

#: Extra seeds for the spread. A single split is one draw from the conformal
#: guarantee's own randomness, and reporting one number from one draw would be
#: the mistake this run exists to avoid making about somebody else's threshold.
SPREAD_SEEDS: Tuple[int, ...] = (20260809, 11, 22, 33, 44, 55, 66, 77)

#: Target error rates. Chosen to bracket the region a caller would plausibly ask
#: for and to include one (``0.50``) where the guarantee is nearly vacuous, so
#: the trend is visible rather than inferred from three points.
ALPHAS: Tuple[float, ...] = (0.05, 0.10, 0.20, 0.30, 0.50)

#: Margin gates swept for the matched-coverage comparison. The values are the
#: published curve's, plus a fine grid so a match can actually be found.
MARGIN_GRID: Tuple[float, ...] = tuple(round(0.005 * step, 4) for step in range(0, 61))


# ---------------------------------------------------------------------------
# scoring one arm
# ---------------------------------------------------------------------------
class Split:
    """One calibration/evaluation partition of the corpus, with its provenance.

    Attributes:
        name: Arm name, used as the run-id segment.
        calibration: Indices into the scored corpus used for calibration.
        evaluation: Indices used for evaluation. Disjoint from ``calibration``.
        exchangeable: Whether the construction preserves exchangeability. A
            random partition does; an acronym-disjoint one does not, and that is
            the whole point of having both.
        note: How the partition was built, in one sentence.
    """

    __slots__ = ("calibration", "evaluation", "exchangeable", "name", "note")

    def __init__(
        self,
        name: str,
        calibration: Sequence[int],
        evaluation: Sequence[int],
        *,
        exchangeable: bool,
        note: str,
    ) -> None:
        self.name = name
        self.calibration = tuple(calibration)
        self.evaluation = tuple(evaluation)
        self.exchangeable = exchangeable
        self.note = note


def random_split(count: int, seed: int) -> Split:
    """A seeded 50/50 partition of the instance indices.

    Args:
        count: Number of instances.
        seed: Frozen seed.

    Returns:
        The split. Exchangeable by construction, which is what makes it the
        control rather than the experiment.
    """
    order = list(range(count))
    random.Random(seed).shuffle(order)
    half = count // 2
    return Split(
        f"random_seed_{seed}",
        order[:half],
        order[half:],
        exchangeable=True,
        note=f"seeded uniform 50/50 partition of instance indices, seed {seed}",
    )


def acronym_disjoint_split(instances: Sequence[DisambiguationInstance], seed: int) -> Split:
    """A partition in which no acronym appears in both halves.

    Every instance of one acronym goes to one side. That is a within-corpus
    stand-in for the shift an out-of-domain caller introduces: the calibration
    scores are drawn from expansions and contexts the evaluation half never
    contains, so the exchangeability the guarantee assumes is broken in the way
    deployment actually breaks it, while genre, tokenisation and annotation are
    held fixed.

    Args:
        instances: The corpus, in order.
        seed: Frozen seed for the acronym shuffle.

    Returns:
        The split, roughly half the instances on each side.

    Raises:
        ValueError: If either half would be empty, which would make every figure
            derived from it undefined rather than merely wrong.
    """
    by_acronym: Dict[str, List[int]] = {}
    for index, instance in enumerate(instances):
        by_acronym.setdefault(instance.acronym, []).append(index)
    keys = sorted(by_acronym)
    random.Random(seed).shuffle(keys)
    target = len(instances) // 2
    calibration: List[int] = []
    evaluation: List[int] = []
    for key in keys:
        if len(calibration) < target:
            calibration.extend(by_acronym[key])
        else:
            evaluation.extend(by_acronym[key])
    if not calibration or not evaluation:
        raise ValueError("acronym-disjoint split produced an empty half")
    return Split(
        f"acronym_disjoint_seed_{seed}",
        sorted(calibration),
        sorted(evaluation),
        exchangeable=False,
        note=(
            f"{len(keys)} distinct acronyms shuffled under seed {seed} and dealt whole to one "
            "half or the other, so no acronym appears in both"
        ),
    )


def evaluate(
    gate: ConformalGate,
    results: Sequence[DisambiguationResult],
    golds: Sequence[str],
    indices: Sequence[int],
) -> Dict[str, object]:
    """Score one calibrated gate on one evaluation set.

    Args:
        gate: The calibrated gate.
        results: Every scored result, indexed by corpus position.
        golds: Gold expansions, aligned with ``results``.
        indices: The evaluation positions.

    Returns:
        A flat block of measurements plus a ``by_arity`` decomposition. Every
        rate carries the count it was computed from, because a coverage figure
        with no denominator is the failure mode this project has a rule about.
    """
    covered = 0
    answered = 0
    answered_correct = 0
    empty_sets = 0
    ambiguous = 0
    uncalibrated = 0
    set_size_total = 0
    per_group: Dict[str, Dict[str, int]] = {}

    for position in indices:
        result = results[position]
        gold = golds[position]
        decision = gate.decide(result)
        group = arity_group(result)
        bucket = per_group.setdefault(group, {"n": 0, "covered": 0, "answered": 0, "correct": 0})
        bucket["n"] += 1
        set_size_total += len(decision.prediction_set)
        if gold in decision.prediction_set:
            covered += 1
            bucket["covered"] += 1
        if decision.reason == "answered":
            answered += 1
            bucket["answered"] += 1
            if decision.expansion == gold:
                answered_correct += 1
                bucket["correct"] += 1
        elif decision.reason == "ambiguous":
            ambiguous += 1
        elif decision.reason == "no_plausible_candidate":
            empty_sets += 1
        elif decision.reason == "uncalibrated_group":
            uncalibrated += 1

    total = len(indices)
    nominal = (1.0 - gate.alpha) * 100.0
    empirical = covered / total * 100.0
    selective_accuracy = (answered_correct / answered * 100.0) if answered else None
    selective_error = (100.0 - selective_accuracy) if selective_accuracy is not None else None
    by_arity = {
        group: {
            "instances": bucket["n"],
            "coverage_pct": round(bucket["covered"] / bucket["n"] * 100.0, 2),
            "coverage_gap_points": round(bucket["covered"] / bucket["n"] * 100.0 - nominal, 2),
            "answer_rate_pct": round(bucket["answered"] / bucket["n"] * 100.0, 2),
            "selective_accuracy_pct": (
                round(bucket["correct"] / bucket["answered"] * 100.0, 2)
                if bucket["answered"]
                else None
            ),
        }
        for group, bucket in sorted(per_group.items())
    }
    gaps = [abs(_as_float(block["coverage_gap_points"])) for block in by_arity.values()]
    return {
        "eval_instances": total,
        "nominal_coverage_pct": round(nominal, 2),
        "empirical_coverage_pct": round(empirical, 2),
        "coverage_gap_points": round(empirical - nominal, 2),
        "covered_instances": covered,
        "answered_instances": answered,
        "answer_rate_pct": round(answered / total * 100.0, 2),
        "answered_correct": answered_correct,
        "selective_accuracy_pct": (
            round(selective_accuracy, 2) if selective_accuracy is not None else None
        ),
        "selective_error_pct": (round(selective_error, 2) if selective_error is not None else None),
        "selective_error_over_alpha": (
            round(selective_error / (gate.alpha * 100.0), 2)
            if selective_error is not None
            else None
        ),
        "joint_answered_and_wrong_pct": round((answered - answered_correct) / total * 100.0, 2),
        "joint_bound_pct": round(gate.alpha * 100.0, 2),
        "joint_bound_respected": (answered - answered_correct) / total <= gate.alpha,
        "refused_ambiguous": ambiguous,
        "refused_no_plausible_candidate": empty_sets,
        "refused_uncalibrated_group": uncalibrated,
        "mean_prediction_set_size": round(set_size_total / total, 4),
        "worst_arity_gap_points": round(max(gaps), 2) if gaps else None,
        "mean_abs_arity_gap_points": round(sum(gaps) / len(gaps), 2) if gaps else None,
        "by_arity": by_arity,
    }


def shipped_gate_admits(result: DisambiguationResult, threshold: float) -> bool:
    """Whether ``LexicalDisambiguator(min_margin=threshold)`` would answer.

    Both of the shipped gate's exemptions are reproduced -- fewer than two
    candidates, and a winner whose source differs from the runner-up's, where
    the gap is fixed by ``INLINE_SCORE - MAX_DICTIONARY_SCORE`` and measures
    nothing. **They are not decorative here.** On this corpus the second
    exemption fires on a non-trivial share of instances, and a comparison column
    that ignored it would be scoring a gate this library does not ship.

    Reproduction is *checked* rather than asserted: :func:`verify_margin_harness`
    runs the real gate and counts disagreements.

    Args:
        result: An ungated result.
        threshold: The gate.

    Returns:
        Whether an answer would be returned.
    """
    margin = result.margin
    if margin is None:
        return True
    if result.candidates[0].source != result.candidates[1].source:
        return True
    return margin >= threshold


def verify_margin_harness(
    instances: Sequence[DisambiguationInstance],
    dictionary: ExpansionDictionary,
    results: Sequence[DisambiguationResult],
    thresholds: Sequence[float],
) -> Dict[str, object]:
    """Check the local copy of the shipped gate against the shipped gate itself.

    Args:
        instances: The corpus.
        dictionary: Candidate index.
        results: The ungated results, aligned with ``instances``.
        thresholds: Gates to check at.

    Returns:
        Disagreement counts, and the boolean the report prints.
    """
    disagreements = 0
    exempt_source = sum(
        1
        for result in results
        if len(result.candidates) >= 2
        and result.candidates[0].source != result.candidates[1].source
    )
    for threshold in thresholds:
        engine = LexicalDisambiguator(Config(), dictionary, min_margin=threshold)
        for item, ungated in zip(instances, results):
            gated = engine.disambiguate(item.acronym, item.context)
            shipped_answered = not gated.abstained
            if shipped_answered != shipped_gate_admits(ungated, threshold):
                disagreements += 1
    return {
        "thresholds_checked": list(thresholds),
        "instances_per_threshold": len(instances),
        "comparisons": len(instances) * len(thresholds),
        "disagreements": disagreements,
        "harness_reproduces_shipped_gate": disagreements == 0,
        "instances_exempt_because_top_two_sources_differ": exempt_source,
        "instances_exempt_pct": round(exempt_source / max(len(instances), 1) * 100.0, 2),
    }


def margin_gate_at_matched_answer_rate(
    results: Sequence[DisambiguationResult],
    golds: Sequence[str],
    indices: Sequence[int],
    target_answer_rate: float,
) -> Dict[str, object]:
    """The published margin gate, at whichever threshold answers as often.

    The comparison a reader wants is not "conformal against no gate" -- it is
    "conformal against the refusal this library already ships, spending the same
    coverage". Sweeping the margin grid and taking the closest answer rate is
    the fairest available form of that, and it is generous to the margin gate:
    the threshold is chosen *on the evaluation set*, which conformal is not
    allowed to do.

    Args:
        results: Every scored result.
        golds: Gold expansions, aligned.
        indices: Evaluation positions.
        target_answer_rate: The answer rate to match, as a percentage.

    Returns:
        The matched threshold and what it scores, or an empty block when the
        grid cannot reach the target at all.
    """
    best: Optional[Dict[str, object]] = None
    for threshold in MARGIN_GRID:
        answered = 0
        correct = 0
        for position in indices:
            result = results[position]
            if not shipped_gate_admits(result, threshold):
                continue
            answered += 1
            if result.candidates[0].expansion == golds[position]:
                correct += 1
        rate = answered / len(indices) * 100.0
        distance = abs(rate - target_answer_rate)
        if best is None or distance < _as_float(best["answer_rate_distance_points"]):
            best = {
                "min_margin": threshold,
                "answered_instances": answered,
                "answer_rate_pct": round(rate, 2),
                "answer_rate_distance_points": round(distance, 4),
                "selective_accuracy_pct": round(correct / answered * 100.0, 2)
                if answered
                else None,
            }
    return best or {}


def most_frequent_on_subset(
    results: Sequence[DisambiguationResult],
    golds: Sequence[str],
    indices: Sequence[int],
    gate: ConformalGate,
    most_frequent: Sequence[str],
) -> Dict[str, object]:
    """The shared task's own baseline, scored on the gate's answered subset.

    D-037 and D-044 both turn on this column: raising a refusal threshold raises
    accuracy among the answered, and if a system that ignores the context
    entirely is *also* more accurate on that same subset, the gate was selecting
    easy questions rather than producing good answers.

    Args:
        results: Every scored result.
        golds: Gold expansions, aligned.
        indices: Evaluation positions.
        gate: The calibrated gate whose answered subset to score on.
        most_frequent: The baseline's prediction per corpus position.

    Returns:
        The baseline's accuracy on that subset, with its denominator.
    """
    answered = 0
    correct = 0
    for position in indices:
        if gate.decide(results[position]).reason != "answered":
            continue
        answered += 1
        if most_frequent[position] == golds[position]:
            correct += 1
    return {
        "subset_instances": answered,
        "most_frequent_accuracy_same_subset_pct": (
            round(correct / answered * 100.0, 2) if answered else None
        ),
    }


# ---------------------------------------------------------------------------
# the corpus, scored once
# ---------------------------------------------------------------------------
def score_corpus(
    instances: Sequence[DisambiguationInstance], dictionary: ExpansionDictionary
) -> Tuple[List[DisambiguationResult], Dict[str, object]]:
    """Run the shipped disambiguator over every instance, once.

    Args:
        instances: The corpus.
        dictionary: Candidate index built from ``diction.json``.

    Returns:
        ``(results, work)`` where ``work`` is the R17 block: what was actually
        done, so that a rate below cannot be read without its denominator.
    """
    engine = LexicalDisambiguator(Config(), dictionary)
    started = time.perf_counter()
    results = [engine.disambiguate(item.acronym, item.context) for item in instances]
    elapsed = time.perf_counter() - started
    candidates_scored = sum(len(result.candidates) for result in results)
    return results, {
        "instances_scored": len(instances),
        "distinct_acronyms": len({item.acronym for item in instances}),
        "distinct_gold_expansions": len({item.expansion for item in instances}),
        "disambiguate_calls": len(instances),
        "candidates_scored": candidates_scored,
        "mean_candidates_per_instance": round(candidates_scored / max(len(instances), 1), 4),
        "instances_with_two_or_more_candidates": sum(
            1 for result in results if len(result.candidates) >= 2
        ),
        "instances_whose_gold_is_not_a_candidate": sum(
            1
            for result, item in zip(results, instances)
            if item.expansion not in {candidate.expansion for candidate in result.candidates}
        ),
        "wall_clock_seconds_unarmed_note": round(elapsed, 3),
    }


def behaviour_identity(
    instances: Sequence[DisambiguationInstance], dictionary: ExpansionDictionary
) -> Dict[str, object]:
    """R19: the feature forced off must be byte-identical to the feature absent.

    Two disambiguators are built over the whole corpus -- one constructed
    without the new keyword at all, one constructed with ``calibration=None`` --
    and every result is serialised and hashed. A refusal policy that changed one
    field on one instance while defaulting to off would be a behaviour change
    smuggled in under a new parameter, and no accuracy figure on this page could
    see it.

    **One field is excluded and the exclusion is the interesting part.** The
    first run of this check came back ``False``, and the difference was
    ``metadata.execution_time_ms`` -- a wall clock, which differs between any two
    runs of anything. A byte-identity check over a record containing a timestamp
    is a check that can only fail, which is the mirror image of the defect R19
    exists to catch, so the digest is taken over the result with that one field
    dropped and the drop is named here rather than hidden in a helper.

    Args:
        instances: The corpus.
        dictionary: Candidate index.

    Returns:
        The two digests, whether they match, and how many results were compared.
    """
    absent = LexicalDisambiguator(Config(), dictionary)
    forced_off = LexicalDisambiguator(Config(), dictionary, calibration=None)
    left = hashlib.sha256()
    right = hashlib.sha256()
    for item in instances:
        left.update(_stable_payload(absent.disambiguate(item.acronym, item.context)))
        right.update(_stable_payload(forced_off.disambiguate(item.acronym, item.context)))
    return {
        "results_compared": len(instances),
        "fields_excluded": ["metadata.execution_time_ms"],
        "fields_excluded_reason": (
            "a wall clock differs between any two runs; including it makes the identity check "
            "one that can only fail"
        ),
        "digest_keyword_absent": left.hexdigest(),
        "digest_calibration_none": right.hexdigest(),
        "byte_identical": left.hexdigest() == right.hexdigest(),
    }


def _stable_payload(result: DisambiguationResult) -> bytes:
    """Serialise a result with the one non-deterministic field removed.

    Args:
        result: The result to serialise.

    Returns:
        Canonical JSON bytes, including the computed ``margin`` and
        ``abstained`` fields, which are exactly the two a refusal policy would
        move.
    """
    payload = result.model_dump(mode="json")
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("execution_time_ms", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------------------
# does the machinery fit the governed half?
# ---------------------------------------------------------------------------
def governed_fit_probe() -> Dict[str, object]:
    """Count the governed token positions a conformal set could ever be built on.

    ``is_fully_known`` is a conjunction over token positions, and it is false
    because of the positions the catalog **declined**. Conformal prediction
    needs a candidate set to take a subset of, so the question is not whether a
    calibrated confidence would be useful on the governed half -- it obviously
    would -- but how many governed token positions carry two or more rival long
    forms for a prediction set to be drawn from.

    Two arms, both taken from ``bench/run_governed_catalog.py`` rather than
    reimplemented, so this probe cannot be accused of building a friendlier
    catalog than the one the project already scores: the empty catalog every
    published governed accuracy figure uses, and the audit-shaped voted catalog
    inferred portal-disjointly from the *other* fold's half.

    Returns:
        Token-position counts by rival-set size, per arm and per fold. A block
        carrying only ``skipped`` when the governed corpus or harness is absent.
    """
    try:
        from acronymkit.governed import GovernedDictionary, expand_identifier
        from bench import run_governed_catalog as catalog_bench
    except Exception as error:  # pragma: no cover - import guard
        return {"skipped": f"governed harness unavailable: {error}"}
    try:
        folds, _census = catalog_bench.load_folds(catalog_bench.gold.SOCRATA_PAGES, refresh=False)
    except (SystemExit, OSError) as error:  # pragma: no cover - corpus guard
        return {"skipped": f"governed gold corpus unavailable: {error}"}

    mode, min_votes, min_share = catalog_bench.VOTED_CELL
    arms: Dict[str, object] = {
        "corpus": "socrata governed gold, portal-disjoint folds (bench/run_governed_catalog.py)",
        "catalog_cell": f"mode={mode}, min_votes={min_votes}, min_share={min_share}",
        "note": (
            "rivals are TokenExpansion.beat -- the long forms the winning one was chosen over. "
            "A position with zero rivals offers a conformal prediction set of at most one "
            "element, which is a set with nothing to refuse."
        ),
        "beat_is_zero_by_construction": (
            "run_governed_catalog.build_catalog emits one canonical per token and sets no "
            "candidates field, so TokenExpansion.beat is empty for every position it can "
            "produce. Read the zero rows below as a derivation, not a result -- the same "
            "distinction D-074 draws about the empty catalog's zero on abbreviated tokens. "
            "The rows that are NOT a derivation are collision_evidence.* below, which count "
            "how often the corpus itself supplies two or more rival expansions for one token."
        ),
    }
    for fold in folds:
        catalog = catalog_bench.build_catalog(fold.training, mode, min_votes, min_share)
        voted = GovernedDictionary(catalog.entries)
        for arm_name, dictionary in (
            ("empty_catalog", GovernedDictionary({})),
            ("voted_catalog", voted),
        ):
            sizes: Dict[int, int] = {}
            declined = 0
            known = 0
            for identifier, _caption in fold.scored:
                expansion = expand_identifier(identifier, dictionary)
                for token in expansion.tokens:
                    rivals = len(token.beat)
                    sizes[rivals] = sizes.get(rivals, 0) + 1
                    if token.is_known:
                        known += 1
                    else:
                        declined += 1
            positions = known + declined
            with_rival = sum(count for size, count in sizes.items() if size >= 1)
            arms[f"{fold.name}.{arm_name}"] = {
                "scored_pairs": len(fold.scored),
                "catalog_acting_rows": len(catalog.entries) if arm_name == "voted_catalog" else 0,
                "token_positions": positions,
                "known_positions": known,
                "declined_positions": declined,
                "declined_pct": round(declined / positions * 100.0, 2) if positions else None,
                "positions_by_rival_count": {str(key): sizes[key] for key in sorted(sizes)},
                "positions_with_at_least_one_rival": with_rival,
                "positions_with_at_least_one_rival_pct": (
                    round(with_rival / positions * 100.0, 2) if positions else None
                ),
            }
        arms[f"{fold.name}.collision_evidence"] = _collision_evidence(catalog_bench, fold, mode)
    return arms


def _collision_evidence(catalog_bench: Any, fold: Any, mode: str) -> Dict[str, object]:
    """How often the corpus itself offers two rival expansions for one token.

    This is the number the ``beat`` counts cannot supply, because the catalog
    builder throws rivals away before the entry is written: it stores one
    canonical per token and no ``candidates`` field at all. Computed from the
    same votes that builder counts, through the same ``align`` and ``tokens_of``,
    so it is an upper bound on what any catalog inferred from this corpus could
    ever put in front of a conformal prediction set.

    Args:
        catalog_bench: The imported ``bench.run_governed_catalog`` module.
        fold: The fold whose training half supplies the votes and whose scored
            half supplies the positions.
        mode: The alignment rule.

    Returns:
        Token and position counts, with their denominators.
    """
    votes: Dict[str, set] = {}
    for identifier, caption in fold.training:
        aligned = catalog_bench.align(identifier, caption, mode)
        if not aligned:
            continue
        for token, word in aligned:
            votes.setdefault(token, set()).add(word.title())
    contested = {token for token, words in votes.items() if len(words) >= 2}
    positions = 0
    contested_positions = 0
    for identifier, _caption in fold.scored:
        for token in catalog_bench.tokens_of(identifier):
            positions += 1
            if token in contested:
                contested_positions += 1
    return {
        "distinct_tokens_voted_on": len(votes),
        "tokens_with_two_or_more_rival_expansions": len(contested),
        "tokens_with_rivals_pct": (
            round(len(contested) / len(votes) * 100.0, 2) if votes else None
        ),
        "scored_token_positions": positions,
        "scored_positions_whose_token_has_rivals": contested_positions,
        "scored_positions_whose_token_has_rivals_pct": (
            round(contested_positions / positions * 100.0, 2) if positions else None
        ),
        "note": (
            "an upper bound on what a conformal prediction set could ever be built over in the "
            "governed half: a token with one candidate has a set of size one and nothing to "
            "refuse. Rival expansions are counted as distinct title-cased canonicals, which is "
            "the form build_catalog would have stored"
        ),
    }


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------
def run_arm(
    split: Split,
    results: Sequence[DisambiguationResult],
    golds: Sequence[str],
    most_frequent: Sequence[str],
    *,
    with_comparisons: bool,
) -> Dict[str, object]:
    """Calibrate and evaluate both modes at every alpha on one split.

    Args:
        split: The partition.
        results: Every scored result.
        golds: Gold expansions, aligned.
        most_frequent: Baseline predictions, aligned.
        with_comparisons: Whether to run the two expensive comparisons (matched
            margin gate, baseline on the answered subset). Off for the seed
            spread, where only coverage is being read.

    Returns:
        One block per ``(mode, alpha)``, plus the split's provenance.
    """
    labelled_calibration = [(results[i], golds[i]) for i in split.calibration]
    block: Dict[str, object] = {
        "split": split.name,
        "split_note": split.note,
        "exchangeable_by_construction": split.exchangeable,
        "calibration_instances": len(split.calibration),
        "eval_instances": len(split.evaluation),
    }
    for mode, group_by in (
        ("marginal", None),
        ("mondrian_by_arity", arity_group),
    ):
        for alpha in ALPHAS:
            key = f"{mode}.alpha_{alpha:.2f}"
            typed: Optional[Callable[[DisambiguationResult], str]] = group_by
            try:
                gate = ConformalGate.calibrate(labelled_calibration, alpha=alpha, group_by=typed)
            except Exception as error:
                block[key] = {"refused": str(error)}
                continue
            measured = evaluate(gate, results, golds, split.evaluation)
            measured["calibration_instances"] = gate.calibration_size
            measured["calibration_groups"] = len(gate.groups)
            measured["smallest_calibration_size_for_alpha"] = smallest_calibration_size(alpha)
            measured["group_thresholds"] = {
                group.key or "<marginal>": {
                    "count": group.count,
                    "rank": group.rank,
                    "threshold": (
                        None if math.isinf(group.threshold) else round(group.threshold, 6)
                    ),
                    "uncovered_calibration_instances": group.uncovered,
                }
                for group in gate.groups
            }
            if with_comparisons:
                measured.update(
                    most_frequent_on_subset(results, golds, split.evaluation, gate, most_frequent)
                )
                measured["margin_gate_at_matched_answer_rate"] = margin_gate_at_matched_answer_rate(
                    results,
                    golds,
                    split.evaluation,
                    _as_float(measured["answer_rate_pct"]),
                )
            block[key] = measured
    for alpha in ALPHAS:
        marginal = block.get(f"marginal.alpha_{alpha:.2f}")
        mondrian = block.get(f"mondrian_by_arity.alpha_{alpha:.2f}")
        if not isinstance(marginal, dict) or not isinstance(mondrian, dict):
            continue
        if "refused" in marginal or "refused" in mondrian:
            continue
        marginal_worst = _as_float(marginal["worst_arity_gap_points"])
        mondrian_worst = _as_float(mondrian["worst_arity_gap_points"])
        block[f"mondrian_vs_marginal.alpha_{alpha:.2f}"] = {
            "marginal_worst_arity_gap_points": marginal_worst,
            "mondrian_worst_arity_gap_points": mondrian_worst,
            "worst_arity_gap_improvement_points": round(marginal_worst - mondrian_worst, 2),
            "marginal_answer_rate_pct": marginal["answer_rate_pct"],
            "mondrian_answer_rate_pct": mondrian["answer_rate_pct"],
            "answer_rate_improvement_points": round(
                _as_float(mondrian["answer_rate_pct"]) - _as_float(marginal["answer_rate_pct"]), 2
            ),
            "mondrian_beats_marginal_on_conditional_coverage": mondrian_worst < marginal_worst,
            "verdict_note": (
                "the comparison is worst per-arity deviation from nominal, not pooled coverage: "
                "both arms hit pooled nominal by construction and only one of them is telling "
                "the truth inside a candidate-set size"
            ),
        }
    return block


def render(payload: Dict[str, Dict[str, object]]) -> str:
    """Human-readable report.

    Args:
        payload: The run blocks, keyed by run id.

    Returns:
        The report.
    """
    lines: List[str] = []
    work = payload["conformal.sdu21.work"]
    lines.append("work done (R17)")
    for name in (
        "instances_scored",
        "distinct_acronyms",
        "candidates_scored",
        "mean_candidates_per_instance",
        "instances_whose_gold_is_not_a_candidate",
    ):
        lines.append(f"  {name:<44} {work[name]}")
    lines.append(f"  environment (R18, unarmed)                   {work['environment']}")
    harness = work["margin_harness"]
    assert isinstance(harness, dict)
    lines.append(
        f"  margin harness reproduces the shipped gate    "
        f"{harness['harness_reproduces_shipped_gate']} "
        f"({harness['disagreements']} disagreement(s) over {harness['comparisons']:,} comparisons; "
        f"{harness['instances_exempt_because_top_two_sources_differ']:,} source-exempt instances)"
    )
    lines.append("")
    for run_id in ("conformal.sdu21.exchangeable", "conformal.sdu21.acronym_disjoint"):
        block = payload[run_id]
        lines.append(f"{run_id}   ({block['split_note']})")
        header = (
            f"  {'mode':<18}{'alpha':>6}{'nominal':>9}{'covered':>9}{'gap':>8}"
            f"{'answer%':>9}{'sel.acc':>9}{'mfreq':>8}{'worst arity gap':>17}"
        )
        lines.append(header)
        for mode in ("marginal", "mondrian_by_arity"):
            for alpha in ALPHAS:
                cell = block.get(f"{mode}.alpha_{alpha:.2f}")
                if not isinstance(cell, dict) or "refused" in cell:
                    reason = cell.get("refused", "?") if isinstance(cell, dict) else "?"
                    lines.append(f"  {mode:<18}{alpha:>6.2f}  refused: {reason[:70]}")
                    continue
                lines.append(
                    f"  {mode:<18}{alpha:>6.2f}"
                    f"{cell['nominal_coverage_pct']:>9.2f}"
                    f"{cell['empirical_coverage_pct']:>9.2f}"
                    f"{cell['coverage_gap_points']:>8.2f}"
                    f"{cell['answer_rate_pct']:>9.2f}"
                    f"{_maybe(cell['selective_accuracy_pct']):>9}"
                    f"{_maybe(cell.get('most_frequent_accuracy_same_subset_pct')):>8}"
                    f"{_maybe(cell['worst_arity_gap_points']):>17}"
                )
        lines.append("")
    spread = payload["conformal.sdu21.seed_spread"]
    lines.append("coverage spread over seeds (marginal, exchangeable split)")
    for alpha in ALPHAS:
        cell = spread[f"alpha_{alpha:.2f}"]
        assert isinstance(cell, dict)
        lines.append(
            f"  alpha {alpha:.2f}  nominal {cell['nominal_coverage_pct']:.2f}  "
            f"mean {cell['mean_coverage_pct']:.2f}  "
            f"min {cell['min_coverage_pct']:.2f}  max {cell['max_coverage_pct']:.2f}  "
            f"over {cell['seeds']} seeds"
        )
    lines.append("")
    identity = payload["conformal.sdu21.identity"]
    lines.append(
        f"R19 identity: {identity['results_compared']} results, "
        f"byte-identical={identity['byte_identical']}"
    )
    governed = payload["conformal.governed.fit"]
    lines.append("")
    lines.append("governed fit probe -- can a conformal set be built there at all?")
    if "skipped" in governed:
        lines.append(f"  skipped: {governed['skipped']}")
    else:
        for key in sorted(governed):
            cell = governed[key]
            if not isinstance(cell, dict):
                continue
            if "token_positions" in cell:
                lines.append(
                    f"  {key:<28} positions {cell['token_positions']:,}  "
                    f"declined {cell['declined_positions']:,} ({cell['declined_pct']} %)  "
                    f"beat-rivals {cell['positions_with_at_least_one_rival']:,} "
                    f"({cell['positions_with_at_least_one_rival_pct']} %)"
                )
            elif "distinct_tokens_voted_on" in cell:
                lines.append(
                    f"  {key:<28} tokens voted on {cell['distinct_tokens_voted_on']:,}  "
                    f"with 2+ rival expansions "
                    f"{cell['tokens_with_two_or_more_rival_expansions']:,} "
                    f"({cell['tokens_with_rivals_pct']} %)  "
                    f"scored positions on such a token "
                    f"{cell['scored_positions_whose_token_has_rivals']:,} "
                    f"({cell['scored_positions_whose_token_has_rivals_pct']} %)"
                )
    lines.append("")
    lines.append(f"the assumption, carried with every figure above: {ASSUMPTION}")
    return "\n".join(lines)


def _as_float(value: object) -> float:
    """Read a number back out of a measurement block.

    The blocks are ``Dict[str, object]`` because they are written straight to
    JSON; this is the one place a value comes back out to be compared, and it is
    a named function so the cast is visible rather than sprinkled.

    Args:
        value: The stored value.

    Returns:
        It, as a float.
    """
    assert isinstance(value, (int, float))
    return float(value)


def _maybe(value: object) -> str:
    """Render a possibly-``None`` number for the table."""
    return "-" if value is None else f"{float(str(value)):.2f}"


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point.

    Args:
        argv: Command line, for testing.

    Returns:
        Process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true", help="write into bench/results.json")
    parser.add_argument("--no-governed", action="store_true", help="skip the governed-fit probe")
    args = parser.parse_args(argv)

    instances = corpora.read_sdu21_ad(split="dev")
    diction = corpora.read_sdu21_ad_diction()
    dictionary = ExpansionDictionary(diction)
    train = corpora.read_sdu21_ad(split="train")

    results, work = score_corpus(instances, dictionary)
    golds = [item.expansion for item in instances]
    from bench.run_disambiguation import predict_most_frequent

    most_frequent = predict_most_frequent(instances, diction, train)
    work["environment"] = environment()
    work["corpus"] = "sdu21_ad"
    work["split_role"] = "tuning (bench/splits.toml); contaminated; not evidence of generalisation"
    work["reserved_arm_untouched"] = "sdu21_ad:test is not read by this runner (D-043)"
    work["train_instances_for_baseline"] = len(train)
    work["margin_harness"] = verify_margin_harness(
        instances, dictionary, results, (0.0, 0.06, 0.15, 0.22, 0.30)
    )

    exchangeable = random_split(len(instances), RANDOM_SEED)
    disjoint = acronym_disjoint_split(instances, RANDOM_SEED)

    payload: Dict[str, Dict[str, object]] = {
        "conformal.sdu21.work": work,
        "conformal.sdu21.exchangeable": run_arm(
            exchangeable, results, golds, most_frequent, with_comparisons=True
        ),
        "conformal.sdu21.acronym_disjoint": run_arm(
            disjoint, results, golds, most_frequent, with_comparisons=True
        ),
    }

    spread: Dict[str, object] = {
        "seeds": len(SPREAD_SEEDS),
        "seed_list": list(SPREAD_SEEDS),
        "mode": "marginal, random 50/50 split, one calibration per seed",
    }
    for alpha in ALPHAS:
        coverages: List[float] = []
        for seed in SPREAD_SEEDS:
            split = random_split(len(instances), seed)
            gate = ConformalGate.calibrate(
                [(results[i], golds[i]) for i in split.calibration], alpha=alpha
            )
            measured = evaluate(gate, results, golds, split.evaluation)
            coverages.append(_as_float(measured["empirical_coverage_pct"]))
        nominal = (1.0 - alpha) * 100.0
        spread[f"alpha_{alpha:.2f}"] = {
            "nominal_coverage_pct": round(nominal, 2),
            "mean_coverage_pct": round(sum(coverages) / len(coverages), 2),
            "min_coverage_pct": round(min(coverages), 2),
            "max_coverage_pct": round(max(coverages), 2),
            "worst_gap_points": round(max(abs(value - nominal) for value in coverages), 2),
            "seeds": len(SPREAD_SEEDS),
        }
    payload["conformal.sdu21.seed_spread"] = spread
    payload["conformal.sdu21.identity"] = behaviour_identity(instances, dictionary)
    payload["conformal.governed.fit"] = (
        {"skipped": "--no-governed"} if args.no_governed else governed_fit_probe()
    )

    print(render(payload))
    if args.save:
        path = save_results(payload)
        print(f"\nsaved -> {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
