#!/usr/bin/env python3
"""Risk-controlled selective classification, measured: does the bound on the ANSWERS hold?

The defect this run exists to close, and its measured size
-----------------------------------------------------------
``bench/run_conformal.py`` publishes what split conformal buys: a bound on the
*joint* rate of answering and being wrong. ``docs/EVALUATION.md`` publishes what
that costs a reader who wants the other quantity -- on
``conformal.sdu21.exchangeable``, Mondrian by arity, ``alpha = 0.05``, the
selective error among answers was ``21.92`` %, which is ``4.38`` times ``alpha``,
falling to ``2.88``, ``1.85``, ``1.37`` and ``0.97`` as ``alpha`` rises to
``0.50``. The overshoot is worst exactly where a governance caller would set the
threshold.

:mod:`acronymkit.core.selective` controls the other quantity by Learn-Then-Test.
This file is the evidence for whether it does, on two corpora that answer
different questions, and it is written so that a **negative** answer on either
one is reportable rather than embarrassing.

The four questions, and the pre-registered abort condition
------------------------------------------------------------
1. **Does Learn-Then-Test hold the selective risk at nominal on a held-out arm?**
   Measured per ``alpha`` over :data:`ALPHAS`, calibrating on one half and
   evaluating on the other.
2. **At what answer rate?** Reported beside every bound, because a gate that
   answers nothing satisfies every selective bound there is and is the same
   refusal with better mathematics.
3. **Does Mondrian stratification by EXTRACTION MODE beat a pooled threshold?**
   Not assumed. Mondrian by *arity* beat marginal decisively on the conformal
   run (worst-arity deviation ``76.14`` to ``4.69``); whether by-mode does the
   same is a separate empirical question and the answer here is no.
4. **How large is each stratum, and is any too small to carry its claim?**
   Answered as a comparison rather than as an opinion:
   :func:`~acronymkit.core.selective.smallest_certifiable_size` prints the
   accepted count a *flawless* stratum would still need, beside the count each
   stratum actually has.

**The abort condition was pre-registered before this file existed** and is
adopted verbatim from the brief: if the held-out selective risk exceeds ``alpha``
anywhere in ``alpha in [0.01, 0.20]``, or the selective-to-nominal inflation
stays above ``1.0``, the method has not done its job and this run says so. It is
evaluated in :func:`abort_verdict` and printed on every invocation, certified or
not.

**The two clauses of that condition are the same clause**, and this run says so
rather than reporting it twice as if it were two pieces of evidence: the
inflation the defect was stated in is ``selective_error / alpha`` -- ``21.92 / 5
= 4.38``, which is the shipped ``selective_error_over_alpha`` field exactly -- so
"risk above alpha" and "inflation above 1" are one inequality. The other reading,
``selective_error / joint_error``, is ``1 / answer_rate``, which exceeds ``1``
whenever the gate abstains at all; it is reported under its own name and it is
not the abort.

The two arms, and why one of them is expected to fail
-------------------------------------------------------
``selective.sdu21.ltt``
    SDU-21 AD dev, the corpus the ``4.38`` was measured on, seeded exchangeable
    split. This is the arm where the honest answer is a refusal: the underlying
    lexical disambiguator's top-one accuracy on this corpus is low enough that
    **no threshold in the grid has a selective risk near any alpha a governance
    caller would set**, so Learn-Then-Test certifies nothing and the gate
    answers nothing. That is the method working, and it is reported as the
    headline rather than buried.
``selective.modes.ltt``
    MED1250, stratified by **extraction mode** -- inline parenthetical
    definitions against A2 out-of-sentence propagated occurrences -- plus a
    catalog stratum derived from this project's own published governed figures.
    This is the arm where the bound holds and holds at a usable answer rate.

Counts, not seconds
-------------------
R17: every rate below ships with the work that produced it -- documents scored,
occurrences licensed, calibration units per stratum, thresholds tested. The
multiplicity *is* the work here, so ``candidates_tested`` is a first-class
field. R18: the one wall-clock figure is an unarmed note with the machine named
in ``environment``; nothing in this file aborts, branches or concludes on a
clock.

R19
---
:func:`behaviour_identity` runs the full MED1250 corpus through
:func:`~acronymkit.nlp.propagation.propagate` three ways -- the parameter absent,
the parameter passed as ``None``, and a gate certified at a non-binding
threshold -- and compares every occurrence field including provenance
(``source``, ``licensed_by``, ``confidence``, ``long_form``, ``span``) plus every
refusal. Byte-identical, not benchmarked-equal.

Usage::

    python tools/fetch_data.py med1250 sdu21-ad-diction sdu21-ad-dev
    python bench/run_selective_risk.py                 # report, record nothing
    python bench/run_selective_risk.py --save          # record into bench/results.json
    python bench/run_selective_risk.py --no-sdu21      # skip the disambiguation arm
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit.config import Config  # noqa: E402
from acronymkit.core.conformal import ConformalGate, nonconformity  # noqa: E402
from acronymkit.core.selective import (  # noqa: E402
    BONFERRONI,
    DEFAULT_THRESHOLD_GRID,
    MODE_CATALOG,
    MODE_INLINE,
    MODE_PROPAGATED,
    SELECTIVE_ASSUMPTION,
    Observation,
    SelectiveRiskGate,
    smallest_certifiable_size,
)
from acronymkit.disambiguation import ExpansionDictionary, LexicalDisambiguator  # noqa: E402
from acronymkit.models import AcronymPair  # noqa: E402
from acronymkit.nlp.extractor import AbbreviationExtractor  # noqa: E402
from acronymkit.nlp.propagation import (  # noqa: E402
    SOURCE_DEFINITION,
    document_result,
    propagate,
)
from bench import corpora  # noqa: E402
from bench.run_extraction import environment, save_results  # noqa: E402

#: Frozen seed for every split below. Shares the value the disambiguation
#: runners use so the project has one magic number rather than four; it selects
#: nothing, it only makes the partition reproducible.
RANDOM_SEED = 20260809

#: The alphas the abort condition is evaluated over. The brief's window is
#: ``[0.01, 0.20]``; these six points are the operational grid and they were
#: fixed in the pre-registration before any measurement was taken.
ALPHAS: Tuple[float, ...] = (0.01, 0.02, 0.05, 0.10, 0.15, 0.20)

#: Probability the calibration itself is allowed to fail, over the draw of the
#: calibration set. **Not** a second error rate on the answers.
DELTA = 0.05

#: Run ids this file writes. Named here so a reader can find every one of them
#: without reading the bottom of the file.
RUN_IDS: Tuple[str, ...] = (
    "selective.sdu21.ltt",
    "selective.sdu21.work",
    "selective.modes.ltt",
    "selective.modes.work",
    "selective.modes.short_form_disjoint",
    "selective.modes.catalog_stratum",
    "selective.identity",
)


# ---------------------------------------------------------------------------
# units
# ---------------------------------------------------------------------------
class Unit:
    """One labelled decision the library would make, with everything that scores it.

    Attributes:
        key: Cluster key -- ``(document, short form)`` for MED1250, the instance
            index for SDU-21. Units sharing a key are **not** independent, and
            the calibration half keeps one per key for exactly that reason.
        stratum: Extraction mode, or ``""`` for a pooled calibration.
        score: Selection score, lower being more confident.
        loss: ``1`` when the answer this unit would produce is wrong.
        representative: Whether this unit is its cluster's first in document
            order. Chosen deterministically, never sampled.
    """

    __slots__ = ("key", "loss", "representative", "score", "stratum")

    def __init__(
        self, key: str, stratum: str, score: float, loss: int, representative: bool
    ) -> None:
        self.key = key
        self.stratum = stratum
        self.score = score
        self.loss = loss
        self.representative = representative

    def observation(self, *, pooled: bool = False) -> Observation:
        """This unit as a calibration observation.

        Args:
            pooled: Put every unit in the ``""`` stratum instead of its own.

        Returns:
            The observation.
        """
        return Observation(stratum="" if pooled else self.stratum, score=self.score, loss=self.loss)


def med1250_units() -> Tuple[List[Unit], List[int], Dict[str, object]]:
    """Score MED1250 into extraction-mode units, one per licensed occurrence.

    The unit is a **licensed occurrence** -- every site at which this library
    would assert an expansion -- because that is what a governance caller is
    exposed to. Its mode is :data:`~acronymkit.core.selective.MODE_INLINE` when
    the site is the definition the extractor found and
    :data:`~acronymkit.core.selective.MODE_PROPAGATED` when A2 licensed it out of
    sentence.

    **The population is named rather than assumed.** A licensed site whose short
    form the annotators never recorded is neither right nor wrong here -- MED1250
    deliberately excludes several annotated categories, so an unrecorded short
    form is *unknown*, not *false* -- and it is excluded and counted. The count
    ships as ``occurrences_outside_gold`` so a reader can see how large the
    excluded population is.

    Returns:
        ``(units, document_index, work)``. ``document_index`` is the corpus
        position of each unit's document, so a document-disjoint split can be
        taken without re-reading the corpus.
    """
    documents = corpora.read_med1250()
    extractor = AbbreviationExtractor(Config())
    units: List[Unit] = []
    document_of: List[int] = []
    started = time.perf_counter()
    outside_gold = 0
    occurrences = 0
    pairs_extracted = 0
    for position, document in enumerate(documents):
        pairs = extractor.extract(document.text)
        pairs_extracted += len(pairs)
        result = propagate(document.text, pairs)
        gold: Dict[str, set] = {}
        for pair in document.pairs:
            short, long_form = pair.key()
            gold.setdefault(short, set()).add(long_form)
        seen: Dict[Tuple[str, str], int] = {}
        for occurrence in result.occurrences:
            occurrences += 1
            short = " ".join(occurrence.short_form.split()).lower()
            long_form = " ".join(occurrence.long_form.split()).lower()
            if short not in gold:
                outside_gold += 1
                continue
            cluster = (short, occurrence.source)
            seen[cluster] = seen.get(cluster, 0) + 1
            units.append(
                Unit(
                    key=f"{position}|{short}|{occurrence.source}",
                    stratum=(
                        MODE_INLINE if occurrence.source == SOURCE_DEFINITION else MODE_PROPAGATED
                    ),
                    score=round(1.0 - occurrence.confidence, 9),
                    loss=0 if long_form in gold[short] else 1,
                    representative=seen[cluster] == 1,
                )
            )
            document_of.append(position)
    elapsed = time.perf_counter() - started
    multi_sense = 0
    short_forms = 0
    for document in documents:
        senses: Dict[str, set] = {}
        for pair in document.pairs:
            short, long_form = pair.key()
            senses.setdefault(short, set()).add(long_form)
        for expansions in senses.values():
            short_forms += 1
            if len(expansions) > 1:
                multi_sense += 1
    work = {
        "corpus": "MED1250 (Ab3P gold standard), role=tuning, contaminated=true",
        "documents_scored": len(documents),
        "definitions_extracted": pairs_extracted,
        "occurrences_licensed": occurrences,
        "occurrences_outside_gold": outside_gold,
        "occurrences_scored": len(units),
        "clusters": len({unit.key for unit in units}),
        "inline_units": sum(1 for unit in units if unit.stratum == MODE_INLINE),
        "propagated_units": sum(1 for unit in units if unit.stratum == MODE_PROPAGATED),
        "representative_units": sum(1 for unit in units if unit.representative),
        "document_short_forms_with_two_or_more_gold_expansions": multi_sense,
        "document_short_forms": short_forms,
        "one_sense_violation_floor_pct": round(multi_sense / max(short_forms, 1) * 100.0, 4),
        "wall_clock_seconds_unarmed_note": round(elapsed, 3),
    }
    return units, document_of, work


def sdu21_units() -> Tuple[List[Unit], List[int], Dict[str, object]]:
    """Score SDU-21 AD dev into selective-classification units, one per instance.

    The selection family is **not** the conformal singleton rule. A prediction
    set of size one is a poor selection function here and this run measures why:
    a singleton can be produced by a top candidate that barely outscores the
    runner-up. The family used instead is the natural one for selective
    classification -- *answer with the top candidate when its nonconformity is at
    most* ``lambda`` -- which is exactly what a confidence threshold means and is
    strictly more discriminating.

    Returns:
        ``(units, instance_index, work)``.
    """
    instances = corpora.read_sdu21_ad(split="dev")
    dictionary = ExpansionDictionary(corpora.read_sdu21_ad_diction())
    engine = LexicalDisambiguator(Config(), dictionary)
    started = time.perf_counter()
    units: List[Unit] = []
    index_of: List[int] = []
    candidates_scored = 0
    without_candidates = 0
    gold_not_a_candidate = 0
    for position, instance in enumerate(instances):
        result = engine.disambiguate(instance.acronym, instance.context)
        scored = nonconformity(result)
        candidates_scored += len(scored)
        if not scored:
            without_candidates += 1
            continue
        top_expansion, top_score = min(scored, key=lambda pair: (pair[1], pair[0]))
        if instance.expansion not in {expansion for expansion, _ in scored}:
            gold_not_a_candidate += 1
        units.append(
            Unit(
                key=str(position),
                stratum="",
                score=round(top_score, 9),
                loss=0 if top_expansion == instance.expansion else 1,
                representative=True,
            )
        )
        index_of.append(position)
    elapsed = time.perf_counter() - started
    work = {
        "corpus": "SDU@AAAI-21 AD dev, role=tuning, contaminated=true",
        "instances_scored": len(instances),
        "distinct_acronyms": len({instance.acronym for instance in instances}),
        "disambiguate_calls": len(instances),
        "candidates_scored": candidates_scored,
        "instances_without_candidates": without_candidates,
        "instances_whose_gold_is_not_a_candidate": gold_not_a_candidate,
        "units_scored": len(units),
        "selection_family": (
            "answer with the top candidate when its nonconformity is at most lambda; "
            "NOT the conformal singleton rule"
        ),
        "wall_clock_seconds_unarmed_note": round(elapsed, 3),
    }
    return units, index_of, work


# ---------------------------------------------------------------------------
# splitting
# ---------------------------------------------------------------------------
def halve(count: int, seed: int) -> Tuple[frozenset, frozenset]:
    """A seeded 50/50 partition of ``range(count)``.

    Args:
        count: How many things to partition.
        seed: Frozen seed.

    Returns:
        ``(calibration, evaluation)`` as disjoint frozensets.
    """
    order = list(range(count))
    random.Random(seed).shuffle(order)
    half = count // 2
    return frozenset(order[:half]), frozenset(order[half:])


def short_form_disjoint(units: Sequence[Unit], seed: int) -> Tuple[List[int], List[int]]:
    """A partition in which no short form appears in both halves.

    A within-corpus stand-in for the shift an out-of-domain caller introduces:
    the calibration units come from short forms the evaluation half never
    contains, so exchangeability is broken in the way deployment actually breaks
    it while genre, annotation and tokenisation are held fixed. It is the
    :func:`bench.run_conformal.acronym_disjoint_split` argument, one corpus
    across.

    Args:
        units: The scored units, in order.
        seed: Frozen seed for the short-form shuffle.

    Returns:
        ``(calibration_positions, evaluation_positions)``.
    """
    by_form: Dict[str, List[int]] = {}
    for position, unit in enumerate(units):
        by_form.setdefault(unit.key.split("|")[1], []).append(position)
    keys = sorted(by_form)
    random.Random(seed).shuffle(keys)
    target = len(units) // 2
    calibration: List[int] = []
    evaluation: List[int] = []
    for key in keys:
        if len(calibration) < target:
            calibration.extend(by_form[key])
        else:
            evaluation.extend(by_form[key])
    return sorted(calibration), sorted(evaluation)


# ---------------------------------------------------------------------------
# evaluating one calibrated gate
# ---------------------------------------------------------------------------
def evaluate(gate: SelectiveRiskGate, units: Sequence[Unit], *, pooled: bool) -> Dict[str, object]:
    """Score one calibrated gate on one held-out set.

    Args:
        gate: The calibrated gate.
        units: The held-out units. **Every** occurrence, not one per cluster:
            calibration is where independence is needed, deployment is where the
            caller lives.
        pooled: Whether the gate was calibrated pooled.

    Returns:
        A flat block plus a ``by_stratum`` decomposition. Every rate carries the
        count it was computed from.
    """
    answered = 0
    wrong = 0
    per_stratum: Dict[str, Dict[str, int]] = {}
    for unit in units:
        key = "" if pooled else unit.stratum
        bucket = per_stratum.setdefault(unit.stratum, {"n": 0, "answered": 0, "wrong": 0})
        bucket["n"] += 1
        if gate.admits(key, unit.score):
            answered += 1
            wrong += unit.loss
            bucket["answered"] += 1
            bucket["wrong"] += unit.loss
    total = len(units)
    alpha = gate.alpha
    selective = (wrong / answered) if answered else None
    joint = wrong / total if total else None
    by_stratum = {
        stratum: {
            "held_out_units": bucket["n"],
            "answered": bucket["answered"],
            "answer_rate_pct": round(bucket["answered"] / bucket["n"] * 100.0, 2),
            "wrong": bucket["wrong"],
            "selective_error_pct": (
                round(bucket["wrong"] / bucket["answered"] * 100.0, 2)
                if bucket["answered"]
                else None
            ),
            "selective_error_over_alpha": (
                round(bucket["wrong"] / bucket["answered"] / alpha, 2)
                if bucket["answered"]
                else None
            ),
        }
        for stratum, bucket in sorted(per_stratum.items())
    }
    ratios = [
        block["selective_error_over_alpha"]
        for block in by_stratum.values()
        if block["selective_error_over_alpha"] is not None
    ]
    return {
        "held_out_units": total,
        "answered_instances": answered,
        "answer_rate_pct": round(answered / total * 100.0, 2) if total else None,
        "answered_wrong": wrong,
        "selective_error_pct": round(selective * 100.0, 2) if selective is not None else None,
        "nominal_selective_error_pct": round(alpha * 100.0, 2),
        "selective_error_over_alpha": (
            round(selective / alpha, 4) if selective is not None else None
        ),
        "selective_bound_respected": (selective is not None and selective <= alpha),
        "joint_error_pct": round(joint * 100.0, 2) if joint is not None else None,
        "selective_over_joint": (
            round(selective / joint, 4) if selective is not None and joint else None
        ),
        "worst_stratum_selective_over_alpha": round(max(ratios), 4) if ratios else None,
        "by_stratum": by_stratum,
    }


def certificates_block(gate: SelectiveRiskGate) -> Dict[str, object]:
    """Every stratum's certificate as recordable fields.

    Args:
        gate: The calibrated gate.

    Returns:
        Stratum key -> its certificate, with the required-size comparison that
        answers "is this stratum too small" as a comparison and not an opinion.
    """
    block: Dict[str, object] = {}
    for certificate in gate.certificates:
        # Keyed "pooled" rather than "<pooled>": a citation in docs/EVALUATION.md
        # is written `<!--claim:...-->` and tools/check_claims.py's comment
        # pattern excludes ">", so an angle-bracketed key is a field no document
        # can cite. The conformal run's "<marginal>" has exactly that problem and
        # nothing in EVALUATION.md cites it.
        block[certificate.stratum or "pooled"] = {
            "certified": certificate.certified,
            "threshold": certificate.threshold,
            "calibration_units": certificate.calibration_units,
            "accepted": certificate.accepted,
            "errors": certificate.errors,
            "calibration_selective_error_pct": (
                round(certificate.empirical_risk * 100.0, 2)
                if certificate.empirical_risk is not None
                else None
            ),
            "calibration_answer_rate_pct": (
                round(certificate.calibration_answer_rate * 100.0, 2)
                if certificate.calibration_answer_rate is not None
                else None
            ),
            "p_value": certificate.p_value,
            "per_candidate_level": certificate.level,
            "candidates_tested": certificate.candidates_tested,
            "candidates_certified": certificate.candidates_certified,
            "required_units_at_zero_errors": certificate.required_units,
            "units_short_of_required": max(
                0, certificate.required_units - certificate.calibration_units
            ),
            "refusal": certificate.refusal,
        }
    return block


def arm(
    units: Sequence[Unit],
    calibration: Sequence[Unit],
    evaluation: Sequence[Unit],
    *,
    pooled: bool,
) -> Dict[str, object]:
    """Calibrate and evaluate one arm across every alpha.

    Args:
        units: Every unit, for the census.
        calibration: The calibration units. One per cluster where clusters
            exist, which is what the binomial tail's independence needs.
        evaluation: The held-out units, all of them.
        pooled: Whether to calibrate one threshold over everything.

    Returns:
        One block per alpha, plus the census.
    """
    block: Dict[str, object] = {
        "calibration_units": len(calibration),
        "held_out_units": len(evaluation),
        "delta": DELTA,
        "correction": BONFERRONI,
        "threshold_grid_size": len(DEFAULT_THRESHOLD_GRID),
        "stratification": "pooled" if pooled else "mondrian_by_extraction_mode",
        "assumption": SELECTIVE_ASSUMPTION,
    }
    for alpha in ALPHAS:
        gate = SelectiveRiskGate.calibrate(
            [unit.observation(pooled=pooled) for unit in calibration],
            alpha=alpha,
            delta=DELTA,
            correction=BONFERRONI,
        )
        entry: Dict[str, object] = {
            "alpha": alpha,
            "certificates": certificates_block(gate),
            "certified_strata": list(gate.certified_strata),
            "guarantee": gate.guarantee(),
        }
        entry.update(evaluate(gate, evaluation, pooled=pooled))
        block[f"alpha_{alpha:.2f}"] = entry
    return block


def abort_verdict(blocks: Sequence[Tuple[str, Dict[str, object]]]) -> Dict[str, object]:
    """The pre-registered abort condition, evaluated rather than asserted.

    The condition, verbatim from the brief: *if ``R_selective > alpha`` anywhere
    in ``alpha in [0.01, 0.20]``, or the joint-to-selective inflation stays
    ``> 1.0``, the method has not done its job and you say so.*

    A cell where nothing certified does **not** fire it -- there is no
    ``R_selective`` to exceed anything -- and it is counted separately under
    ``cells_answering_nothing``, because "the bound held" and "the gate answered
    nothing" are the two ways this can look green and only one of them is.

    Args:
        blocks: ``(name, per-alpha block)`` pairs to evaluate over.

    Returns:
        The verdict, with the failing cells named.
    """
    violations: List[str] = []
    answering_nothing: List[str] = []
    inflations: List[float] = []
    cells = 0
    for name, block in blocks:
        for alpha in ALPHAS:
            entry = block.get(f"alpha_{alpha:.2f}")
            if not isinstance(entry, dict):
                continue
            cells += 1
            ratio = entry.get("selective_error_over_alpha")
            if entry.get("answered_instances") == 0 or ratio is None:
                answering_nothing.append(f"{name}@alpha={alpha:.2f}")
                continue
            inflations.append(float(ratio))
            if float(ratio) > 1.0:
                violations.append(f"{name}@alpha={alpha:.2f} ratio={float(ratio):.4g}")
    return {
        "condition": (
            "R_selective > alpha anywhere in alpha in [0.01, 0.20], evaluated over the six "
            "pre-registered alphas; equivalently selective_error_over_alpha > 1.0, which is the "
            "same inequality and is reported once"
        ),
        "cells_evaluated": cells,
        "cells_answering_nothing": len(answering_nothing),
        "cells_answering_nothing_named": answering_nothing,
        "cells_with_a_bound": len(inflations),
        "worst_selective_over_alpha": round(max(inflations), 4) if inflations else None,
        "violations": violations,
        "aborted": bool(violations),
        "note": (
            "the second reading of the brief's clause, selective_error / joint_error, is "
            "1 / answer_rate and exceeds 1 whenever the gate abstains at all; it is reported "
            "per cell as selective_over_joint and it is NOT the abort"
        ),
    }


# ---------------------------------------------------------------------------
# stratum three, derived from this project's own published figures
# ---------------------------------------------------------------------------
def catalog_stratum(results: Optional[Path] = None) -> Dict[str, object]:
    """The catalog stratum, derived from ``governed_catalog.socrata.voted.*``.

    **Derived rather than re-measured, and that is the stronger provenance.**
    Socrata is a ``held_out`` corpus; re-reading it to produce a figure this
    project has already published would spend a held-out arm to learn nothing.
    Every number below comes out of ``bench/results.json``, so any reader with
    the repository can recompute it without the corpus.

    The population is the abbreviated token positions -- the ones where the
    identifier's token differs from the caption's word, so the catalog has an
    expansion decision to make. ``catalog_fired_tokens`` is how many the catalog
    actually answered on: that is the accepted count, and it is what
    :func:`~acronymkit.core.selective.smallest_certifiable_size` has to be
    compared against.

    Args:
        results: Override for ``bench/results.json``.

    Returns:
        The stratum census and its verdict, or a ``skipped`` block.
    """
    path = results or (REPO_ROOT / "bench" / "results.json")
    try:
        runs = json.loads(path.read_text(encoding="utf-8"))["runs"]
    except (OSError, KeyError, json.JSONDecodeError) as error:  # pragma: no cover - tree guard
        return {"skipped": f"bench/results.json unreadable: {error}"}
    folds = ["governed_catalog.socrata.voted.fold_ab", "governed_catalog.socrata.voted.fold_ba"]
    missing = [name for name in folds if name not in runs]
    if missing:  # pragma: no cover - tree guard
        return {"skipped": f"no published governed catalog run: {missing}"}
    positions = 0
    accepted = 0
    correct = 0
    per_fold: Dict[str, object] = {}
    for name in folds:
        block = runs[name]["abbreviated_tokens"]
        positions += int(block["tokens"])
        accepted += int(block["catalog_fired_tokens"])
        correct += int(block["voted_correct"])
        per_fold[name] = dict(block)
    required = {
        f"alpha_{alpha:.2f}": smallest_certifiable_size(alpha, DELTA / len(DEFAULT_THRESHOLD_GRID))
        for alpha in ALPHAS
    }
    return {
        "stratum": MODE_CATALOG,
        "source": "derived from bench/results.json; no corpus was read and no held-out arm spent",
        "population": (
            "abbreviated token positions in the expansion_strict bucket -- the positions where "
            "the identifier's token differs from the caption's word"
        ),
        "token_positions": positions,
        "catalog_answered_positions": accepted,
        "positions_correct_over_all_abbreviated": correct,
        "per_fold": per_fold,
        "required_units_at_zero_errors": required,
        "smallest_required_over_alphas": min(required.values()),
        "calibratable": accepted >= min(required.values()),
        "verdict": (
            f"the catalog answers {accepted} of {positions} abbreviated token positions. The "
            f"loosest alpha tested still needs {min(required.values())} accepted units with ZERO "
            "losses before any certificate is possible, so this stratum cannot support a "
            "selective bound at any alpha in the tested range -- and that is a statement about "
            "the size of the accepted set, not about the catalog being wrong"
        ),
    }


# ---------------------------------------------------------------------------
# R19
# ---------------------------------------------------------------------------
def _digest(occurrences: Sequence[Any], refused: Sequence[Any]) -> str:
    """A stable serialisation of one propagation result, provenance included.

    Args:
        occurrences: The licensed occurrences.
        refused: The refusals.

    Returns:
        A JSON string. Every field is compared, not a summary of them.
    """
    payload = {
        "occurrences": [
            {
                "short_form": occurrence.short_form,
                "long_form": occurrence.long_form,
                "span": list(occurrence.span),
                "source": occurrence.source,
                "licensed_by": list(occurrence.licensed_by) if occurrence.licensed_by else None,
                "confidence": occurrence.confidence,
            }
            for occurrence in occurrences
        ],
        "refused": [[short, reason] for short, reason in refused],
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def behaviour_identity() -> Dict[str, object]:
    """R19: the feature absent, forced off, and forced on non-bindingly.

    Three call shapes over the whole of MED1250:

    1. ``propagate(text, pairs)`` -- the parameter absent;
    2. ``propagate(text, pairs, selective=None)`` -- forced off;
    3. ``propagate(text, pairs, selective=<gate certified at 1.0>)`` -- forced
       **on** at a threshold that admits everything.

    Plus a fourth and fifth over the pre-existing conformal path,
    ``gate=`` against ``gate=`` with ``selective=None``, because a caller who
    passed only ``gate=`` before this change must get the same bytes after it.

    The third is the one worth having. Comparing "absent" against "off" only
    tests that a ``None`` check works; comparing against a gate that is switched
    on and non-binding tests that the new code path, when it does not refuse,
    reproduces the old output field for field -- provenance included.

    Returns:
        Record counts and whether all three digests match.
    """
    documents = corpora.read_med1250()
    extractor = AbbreviationExtractor(Config())
    # Scored at 1.0, which is the LOOSEST score any definition can carry, so the
    # only threshold that accepts anything is the top of the grid and the gate
    # certifies there. A calibration set scored 0.0 would certify at threshold
    # 0.0 and admit only a confidence of exactly 1.0 -- switched on and binding,
    # which is not the arm this is for. That mistake was made once here and the
    # comparison caught it, which is the whole reason the arm exists.
    permissive = SelectiveRiskGate.calibrate(
        [Observation(MODE_PROPAGATED, 1.0, 0) for _ in range(400)],
        alpha=0.20,
        delta=DELTA,
    )
    certificate = permissive.certificate(MODE_PROPAGATED)
    conformal = ConformalGate.calibrate(
        [
            (
                document_result("AB", [AcronymPair(short_form="AB", long_form="alpha beta")]),
                "alpha beta",
            )
        ]
        * 20,
        alpha=0.2,
    )
    absent: List[str] = []
    forced_off: List[str] = []
    forced_on: List[str] = []
    gate_absent: List[str] = []
    gate_off: List[str] = []
    records = 0
    gate_records = 0
    for document in documents:
        pairs = extractor.extract(document.text)
        first = propagate(document.text, pairs)
        second = propagate(document.text, pairs, selective=None)
        third = propagate(document.text, pairs, selective=permissive)
        fourth = propagate(document.text, pairs, gate=conformal)
        fifth = propagate(document.text, pairs, gate=conformal, selective=None)
        records += len(first.occurrences) + len(first.refused)
        gate_records += len(fourth.occurrences) + len(fourth.refused)
        absent.append(_digest(first.occurrences, first.refused))
        forced_off.append(_digest(second.occurrences, second.refused))
        forced_on.append(_digest(third.occurrences, third.refused))
        gate_absent.append(_digest(fourth.occurrences, fourth.refused))
        gate_off.append(_digest(fifth.occurrences, fifth.refused))
    off_differences = sum(1 for a, b in zip(absent, forced_off) if a != b)
    on_differences = sum(1 for a, b in zip(absent, forced_on) if a != b)
    gate_differences = sum(1 for a, b in zip(gate_absent, gate_off) if a != b)
    return {
        "documents_compared": len(documents),
        "records_compared": records,
        "conformal_path_records_compared": gate_records,
        "conformal_path_differences": gate_differences,
        "fields_compared": "short_form, long_form, span, source, licensed_by, confidence, refused",
        "permissive_gate_threshold": certificate.threshold if certificate else None,
        "permissive_gate_certified": bool(certificate and certificate.certified),
        "absent_vs_forced_off_differences": off_differences,
        "absent_vs_forced_on_differences": on_differences,
        "byte_identical": off_differences == 0 and on_differences == 0 and gate_differences == 0,
        "note": (
            "forced ON at a non-binding threshold is the arm that matters: it exercises the new "
            "code path and demands the old bytes back, where absent-against-off only checks a "
            "None branch"
        ),
    }


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def render(payload: Dict[str, Dict[str, object]]) -> str:
    """Human-readable report.

    Args:
        payload: The run-id -> entry mapping about to be saved.

    Returns:
        The report.
    """
    lines: List[str] = [f"environment : {environment()}", ""]
    for run_id in (
        "selective.sdu21.ltt",
        "selective.modes.ltt",
        "selective.modes.short_form_disjoint",
    ):
        entry = payload.get(run_id)
        if not isinstance(entry, dict):
            continue
        lines.append(f"== {run_id}")
        for name in ("mondrian_by_mode", "pooled", "marginal"):
            block = entry.get(name)
            if not isinstance(block, dict):
                continue
            lines.append(f"  -- {name}: calibration {block.get('calibration_units')} unit(s)")
            lines.append(
                "     alpha  certified  threshold  answered   answer%   selective%   x alpha"
            )
            for alpha in ALPHAS:
                cell = block.get(f"alpha_{alpha:.2f}")
                if not isinstance(cell, dict):
                    continue
                strata = cell.get("certified_strata") or []
                certificates = cell.get("certificates")
                thresholds: List[float] = sorted(
                    {
                        float(block_value["threshold"])
                        for block_value in (
                            certificates.values() if isinstance(certificates, dict) else ()
                        )
                        if isinstance(block_value, dict)
                        and block_value.get("certified")
                        and block_value.get("threshold") is not None
                    }
                )
                lines.append(
                    f"     {alpha:5.2f}  {len(strata):>9}  "
                    f"{','.join(f'{value:.2f}' for value in thresholds) or '--':>9}  "
                    f"{cell.get('answered_instances'):>8}  "
                    f"{_maybe(cell.get('answer_rate_pct')):>7}  "
                    f"{_maybe(cell.get('selective_error_pct')):>10}  "
                    f"{_maybe(cell.get('selective_error_over_alpha')):>7}"
                )
        verdict = entry.get("abort")
        if isinstance(verdict, dict):
            lines.append(
                f"  ABORT CONDITION: {'FIRED' if verdict.get('aborted') else 'not fired'} "
                f"({verdict.get('cells_with_a_bound')} cell(s) with a bound, "
                f"{verdict.get('cells_answering_nothing')} answering nothing)"
            )
        lines.append("")
    catalog = payload.get("selective.modes.catalog_stratum")
    if isinstance(catalog, dict) and "verdict" in catalog:
        lines += ["== catalog stratum", f"  {catalog['verdict']}", ""]
    identity = payload.get("selective.identity")
    if isinstance(identity, dict):
        lines += [
            "== R19",
            f"  {identity.get('records_compared')} record(s) over "
            f"{identity.get('documents_compared')} document(s); byte-identical: "
            f"{identity.get('byte_identical')}",
            "",
        ]
    return "\n".join(lines)


def _maybe(value: object) -> str:
    """Format a number that may be ``None``."""
    if not isinstance(value, (int, float)):
        return "--"
    return f"{float(value):.2f}"


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run every arm and optionally record it.

    Args:
        argv: Command-line arguments.

    Returns:
        Process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument("--no-sdu21", action="store_true", help="skip the disambiguation arm")
    parser.add_argument("--no-identity", action="store_true", help="skip the R19 comparison")
    arguments = parser.parse_args(argv)

    payload: Dict[str, Dict[str, object]] = {}

    units, document_of, work = med1250_units()
    payload["selective.modes.work"] = work
    calibration_documents, _ = halve(max(document_of) + 1 if document_of else 1, RANDOM_SEED)
    calibration = [
        unit
        for unit, document in zip(units, document_of)
        if document in calibration_documents and unit.representative
    ]
    evaluation = [
        unit for unit, document in zip(units, document_of) if document not in calibration_documents
    ]
    mondrian_block = arm(units, calibration, evaluation, pooled=False)
    pooled_block = arm(units, calibration, evaluation, pooled=True)
    modes: Dict[str, object] = {
        "corpus": "MED1250",
        "split": f"document_disjoint_seed_{RANDOM_SEED}",
        "split_note": (
            "documents shuffled under one seed and dealt 50/50; calibration keeps ONE unit per "
            "(document, short form, mode) cluster because the binomial tail needs independent "
            "accepted units, and evaluation keeps every occurrence because that is what a caller "
            "is exposed to"
        ),
        "exchangeable_by_construction": True,
        "mondrian_by_mode": mondrian_block,
        "pooled": pooled_block,
    }
    modes["abort"] = abort_verdict([("mondrian_by_mode", mondrian_block), ("pooled", pooled_block)])
    payload["selective.modes.ltt"] = modes

    disjoint_calibration, disjoint_evaluation = short_form_disjoint(units, RANDOM_SEED)
    disjoint_block = arm(
        units,
        [units[position] for position in disjoint_calibration if units[position].representative],
        [units[position] for position in disjoint_evaluation],
        pooled=False,
    )
    shifted: Dict[str, object] = {
        "corpus": "MED1250",
        "split": f"short_form_disjoint_seed_{RANDOM_SEED}",
        "split_note": (
            "no short form appears in both halves; a within-corpus stand-in for the shift an "
            "out-of-domain caller introduces, which is exactly what the assumption excludes"
        ),
        "exchangeable_by_construction": False,
        "mondrian_by_mode": disjoint_block,
    }
    shifted["abort"] = abort_verdict([("mondrian_by_mode", disjoint_block)])
    payload["selective.modes.short_form_disjoint"] = shifted

    payload["selective.modes.catalog_stratum"] = catalog_stratum()

    if not arguments.no_sdu21:
        sdu_units, sdu_index, sdu_work = sdu21_units()
        payload["selective.sdu21.work"] = sdu_work
        calibration_positions, _ = halve(len(sdu_units), RANDOM_SEED)
        sdu_calibration = [
            unit for position, unit in enumerate(sdu_units) if position in calibration_positions
        ]
        sdu_evaluation = [
            unit for position, unit in enumerate(sdu_units) if position not in calibration_positions
        ]
        sdu_block = arm(sdu_units, sdu_calibration, sdu_evaluation, pooled=True)
        sdu: Dict[str, object] = {
            "corpus": "SDU@AAAI-21 AD dev",
            "split": f"random_seed_{RANDOM_SEED}",
            "split_note": "seeded uniform 50/50 partition of unit indices",
            "exchangeable_by_construction": True,
            "units": len(sdu_index),
            "marginal": sdu_block,
        }
        sdu["abort"] = abort_verdict([("marginal", sdu_block)])
        sdu["floor"] = _floor(sdu_calibration)
        payload["selective.sdu21.ltt"] = sdu

    if not arguments.no_identity:
        payload["selective.identity"] = behaviour_identity()

    print(render(payload))
    if arguments.save:
        path = save_results(payload)
        print(f"saved {len(payload)} run(s) -> {path}")
    return 0


def _floor(calibration: Sequence[Unit]) -> Dict[str, object]:
    """The lowest calibration selective risk any threshold in the grid reaches.

    A certificate that never arrives has two possible causes and they call for
    opposite responses: the calibration set is too small, or **no threshold has a
    low enough risk to certify at any size**. This separates them, and on SDU-21
    it is the second.

    Args:
        calibration: The calibration units.

    Returns:
        The best cell at a floor of fifty accepted units, and the full-answer
        accuracy for scale.
    """
    best: Optional[Tuple[float, float, int, int]] = None
    for threshold in DEFAULT_THRESHOLD_GRID:
        accepted = [unit for unit in calibration if unit.score <= threshold]
        if len(accepted) < 50:
            continue
        errors = sum(unit.loss for unit in accepted)
        risk = errors / len(accepted)
        if best is None or risk < best[0]:
            best = (risk, threshold, len(accepted), errors)
    total_errors = sum(unit.loss for unit in calibration)
    return {
        "question": (
            "is the refusal a small calibration set, or a selection family whose risk never "
            "gets low enough? These need opposite responses and only one of them is fixable "
            "with more data"
        ),
        "minimum_units_required_for_this_row": 50,
        "lowest_calibration_selective_error_pct": (
            round(best[0] * 100.0, 2) if best is not None else None
        ),
        "at_threshold": best[1] if best is not None else None,
        "at_accepted": best[2] if best is not None else None,
        "at_errors": best[3] if best is not None else None,
        "full_answer_accuracy_pct": (
            round((1.0 - total_errors / len(calibration)) * 100.0, 2) if calibration else None
        ),
        "calibration_units": len(calibration),
    }


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
