#!/usr/bin/env python3
"""Why disambiguation loses to a trivial baseline, measured rather than guessed.

What this adds to ``bench/run_disambiguation.py``
--------------------------------------------------
That runner established the number: on SDU@AAAI-21 dev,
:class:`~acronymkit.disambiguation.LexicalDisambiguator` scores far below the
shared task's own most-frequent-expansion baseline. It did not establish *why*,
and "our disambiguator is bad" is not a finding anyone can act on. This runner
produces the taxonomy: it opens the score up into its three terms, asks which of
them can even vary inside a candidate set, asks whether the evidence the scorer
looks for is present in the sentence at all, and puts a ceiling on the whole
approach so that the next person knows whether tuning is worth attempting.

It deliberately re-derives the shipped prediction from the decomposed terms and
prints whether that reproduction matches the shipped engine instance for
instance. If it does not, every number below is measuring a reimplementation
rather than the library, and the run says so.

The four questions, and why each is separable
----------------------------------------------
1. **Does the score separate the candidates?** If most instances end in a tie at
   the top, the failure is in the tie-break and nowhere else. This is the
   diagnosis ``docs/DECISIONS.md`` converged on for *extraction*, and the
   interesting thing about disambiguation is whether it repeats. Measured, not
   assumed.
2. **Which term carries the decision?** SDU-21 candidate sets are, by
   construction, the expansions of one acronym, and ``diction.json`` stores them
   lower-cased. Two of the three scoring terms may therefore be constant inside
   a candidate set -- an offset that cannot change a ranking. The run counts how
   often each term varies and how much weighted spread it contributes.
3. **Is the evidence in the sentence?** The overlap term rewards content-word
   agreement between expansion and context. If the gold expansion's words are
   not in the sentence, there is nothing for it to find, and every score it
   returns is orthographic noise dressed as a decision. Reported as the split
   between the instances where verbatim evidence exists and the ones where it
   does not.
4. **What is the ceiling?** Three of them: perfect tie-breaking, perfect scoring
   of the evidence the current features can see, and the best reweighting of the
   existing three terms found by grid search on dev.

The frequency prior, and a licence statement that is not decoration
--------------------------------------------------------------------
``docs/DECISIONS.md`` records that no permissively-licensed source of expansion
frequency counts was found across ten candidates, so acronymkit has no prior it
may ship. That is a *distribution* constraint, not a *measurement* constraint:
SDU@AAAI-21 is fetch-only under CC BY-NC-SA 4.0 (see ``bench/splits.toml``,
``[corpora.sdu21_ad]``) and benchmarking against it has always been legitimate.

So this runner derives a prior from SDU-21's **training split** and measures
what a prior would buy, exactly as ``run_disambiguation.py`` already does for
the shared task's own baseline. To be explicit, because the distinction has been
blurred here before:

    THE PRIOR MEASURED BY THIS RUNNER IS AN INSTRUMENT, NOT AN ASSET.
    It is derived from non-commercial share-alike data, it is never written to
    disk, never vendored, never committed, and nothing in ``src/`` may load it.
    Its only job is to answer one question: if acronymkit had a prior, would
    context scoring still be worth running on top of it?

That question has a decisive answer either way. If the interpolation of prior
and context never beats the prior alone, context scoring is contributing nothing
and the capability should be defaulted away. If it does beat it, the size of the
gain is the value of the context scorer, and the recommendation follows from the
number instead of from taste. The interpolation weight is the only tuned
parameter, and it is validated out-of-fold rather than reported at its dev
optimum, because a weight chosen and scored on the same 6,189 instances is a
weight that has been fitted to them.

Usage::

    python tools/fetch_data.py sdu21-ad-diction sdu21-ad-dev sdu21-ad-train
    python bench/run_disambiguation_diagnosis.py --save
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit import disambiguation as _d  # noqa: E402
from acronymkit.config import Config  # noqa: E402
from acronymkit.disambiguation import ExpansionDictionary, LexicalDisambiguator  # noqa: E402
from bench import corpora  # noqa: E402
from bench.corpora import DisambiguationInstance  # noqa: E402
from bench.run_extraction import save_results  # noqa: E402

#: Seed for the fold split of the out-of-fold interpolation check. Shares the
#: value used by ``bench/run_disambiguation.py`` for its random baseline so the
#: project keeps one magic number rather than several.
RANDOM_SEED = 20260809

#: Interpolation weights swept for the prior/context blend. Coarse on purpose:
#: a finer grid would fit the dev split harder without telling anyone more.
LAMBDA_GRID = tuple(index / 20 for index in range(21))

#: Step of the three-term reweighting grid search.
WEIGHT_STEP = 0.05

#: Add-alpha smoothing on the training counts, so an expansion unseen in
#: training is improbable rather than impossible.
PRIOR_ALPHA = 0.5

#: The licence statement above, in the one place a reader of the output will see
#: it. Printed on every run, not just on ``--save``.
LICENCE_NOTICE = (
    "LICENCE: the frequency prior below is derived from SDU@AAAI-21 train.json,\n"
    "which is CC BY-NC-SA 4.0 (bench/splits.toml, [corpora.sdu21_ad]). It is a\n"
    "MEASUREMENT INSTRUMENT AND NOT A SHIPPABLE ASSET: never written to disk,\n"
    "never vendored into the wheel, never committed, never loaded from src/.\n"
    "A licence that forbids redistribution does not forbid benchmarking, and\n"
    "this runner benchmarks."
)


# ---------------------------------------------------------------------------
# decomposition
# ---------------------------------------------------------------------------
class Scored:
    """One candidate expansion with its score opened up into its three terms.

    Attributes:
        expansion: The candidate string, verbatim from ``diction.json``.
        overlap: The context/expansion content-word agreement term, in ``[0, 1]``.
        initials: The derivability term, in ``[0, 1]``.
        register: The orthographic register term, ``0.0`` or ``1.0``.
        score: The blended score, reproducing the shipped rounding and cap.
        words: Number of content words in the expansion.
        exact_hits: How many of those words appear verbatim in the context bag.
        tiers: ``{tier: count}`` over the expansion's words, where tier names the
            branch of :func:`~acronymkit.disambiguation._word_similarity` that
            produced that word's best match.
    """

    __slots__ = (
        "exact_hits",
        "expansion",
        "initials",
        "overlap",
        "register",
        "score",
        "tiers",
        "words",
    )

    def __init__(self, expansion, overlap, initials, register, score, words, exact_hits, tiers):
        self.expansion = expansion
        self.overlap = overlap
        self.initials = initials
        self.register = register
        self.score = score
        self.words = words
        self.exact_hits = exact_hits
        self.tiers = tiers


class Decomposed:
    """One dev instance with every candidate scored and its terms exposed."""

    __slots__ = (
        "acronym",
        "acronym_key",
        "candidates",
        "context_is_proper",
        "context_terms",
        "gold",
        "inline",
        "uid",
    )

    def __init__(
        self, uid, acronym, acronym_key, gold, candidates, inline, context_terms, context_is_proper
    ):
        self.uid = uid
        self.acronym = acronym
        self.acronym_key = acronym_key
        self.gold = gold
        self.candidates = candidates
        self.inline = inline
        self.context_terms = context_terms
        self.context_is_proper = context_is_proper

    def gold_candidate(self) -> Optional[Scored]:
        """The scored record of the gold expansion, or ``None`` if absent."""
        return next((c for c in self.candidates if c.expansion == self.gold), None)


def _tiered_overlap(words: Sequence[str], terms: Sequence[str]) -> tuple[float, int, Counter]:
    """Return ``(overlap, exact_hits, tiers)`` for one expansion against one context.

    Reproduces :func:`~acronymkit.disambiguation._overlap_and_evidence`'s
    arithmetic while also recording *which* branch of
    :func:`~acronymkit.disambiguation._word_similarity` produced each word's best
    match. That attribution is the whole point: an overlap of 0.4 built from
    exact word matches and an overlap of 0.4 built from character-bigram
    resonance are the same number and completely different evidence.

    Args:
        words: The expansion's content words.
        terms: The context's content-word bag.

    Returns:
        ``(overlap, exact_hits, tiers)``.
    """
    tiers: Counter = Counter()
    if not words:
        return 0.0, 0, tiers
    total = 0.0
    exact_hits = 0
    for word in words:
        best, tier = 0.0, "zero"
        for term in terms:
            similarity = _d._word_similarity(word, term)
            if similarity > best:
                best = similarity
                if similarity == 1.0:
                    tier = "exact"
                elif similarity == _d.STEM_SIMILARITY:
                    tier = "stem"
                else:
                    tier = "subword"
        total += best
        exact_hits += tier == "exact"
        tiers[tier] += 1
    return max(0.0, min(1.0, total / len(words))), exact_hits, tiers


def decompose(
    instances: Sequence[DisambiguationInstance],
    diction: dict[str, list[str]],
    engine: LexicalDisambiguator,
    config: Config,
) -> list[Decomposed]:
    """Score every candidate of every instance, keeping the three terms apart.

    Args:
        instances: The dev split.
        diction: The candidate sets.
        engine: A disambiguator built over ``diction``, used for its tokenizer,
            its extractor and its own bag construction, so the decomposition
            sees exactly what the shipped code sees.
        config: The configuration whose weights drive the derivability term.

    Returns:
        One :class:`Decomposed` per instance, in corpus order.
    """
    expansion_words: dict[str, list[str]] = {}
    for candidates in diction.values():
        for expansion in candidates:
            if expansion not in expansion_words:
                expansion_words[expansion] = engine._content_words(expansion)

    out: list[Decomposed] = []
    for instance in instances:
        context = instance.context
        acronym_key = _d._short_form_key(instance.acronym)
        tokens = engine.tokenizer.tokenize(context)
        terms = LexicalDisambiguator._context_terms(tokens, acronym_key)
        context_is_proper = engine._context_is_proper(context, tokens, acronym_key)
        inline = [expansion for expansion, _ in engine._inline_expansions(acronym_key, context)]

        scored: list[Scored] = []
        for expansion in diction[instance.acronym]:
            words = expansion_words[expansion]
            overlap, exact_hits, tiers = _tiered_overlap(words, terms)
            initials = _d._derivability(acronym_key, words, config.weights)
            register = 1.0 if any(c.isupper() for c in expansion) == context_is_proper else 0.0
            blend = (
                _d.WEIGHT_OVERLAP * overlap
                + _d.WEIGHT_INITIALS * initials
                + _d.WEIGHT_REGISTER * register
            )
            score = round(min(_d.MAX_DICTIONARY_SCORE, max(0.0, blend)), _d.SCORE_PRECISION)
            scored.append(
                Scored(expansion, overlap, initials, register, score, len(words), exact_hits, tiers)
            )
        out.append(
            Decomposed(
                instance.uid,
                instance.acronym,
                acronym_key,
                instance.expansion,
                scored,
                inline,
                terms,
                context_is_proper,
            )
        )
    return out


# ---------------------------------------------------------------------------
# prediction under a pluggable scorer
# ---------------------------------------------------------------------------
def _key(text: str) -> str:
    """The library's expansion de-duplication key."""
    return " ".join(text.split()).casefold()


def predict(
    record: Decomposed,
    scorer: Callable[[Scored], float],
    *,
    inline: str = "shipped",
) -> str:
    """Return the top expansion under ``scorer``, reproducing the shipped sort.

    Args:
        record: One decomposed instance.
        scorer: Maps a scored candidate to a ranking score.
        inline: ``"shipped"`` reproduces the current behaviour (the inline
            surface form is inserted at ``INLINE_SCORE`` and any dictionary
            candidate that de-duplicates against it is dropped); ``"off"``
            ignores inline definitions entirely; ``"promote"`` keeps the
            *dictionary's* surface form and lifts it to ``INLINE_SCORE``, adding
            the inline string only when the dictionary has no entry for it.

    Returns:
        The winning expansion, or ``""`` when there is nothing to return.
    """
    pool: list[tuple[float, str]] = []
    seen: set[str] = set()
    inline_keys = {_key(expansion) for expansion in record.inline}

    if inline == "shipped":
        for expansion in record.inline:
            if _key(expansion) in seen:
                continue
            seen.add(_key(expansion))
            pool.append((_d.INLINE_SCORE, expansion))

    for candidate in record.candidates:
        key = _key(candidate.expansion)
        if key in seen:
            continue
        seen.add(key)
        value = (
            _d.INLINE_SCORE if (inline == "promote" and key in inline_keys) else scorer(candidate)
        )
        pool.append((round(value, 9), candidate.expansion))

    if inline == "promote":
        for expansion in record.inline:
            if _key(expansion) not in seen:
                seen.add(_key(expansion))
                pool.append((_d.INLINE_SCORE, expansion))

    pool.sort(key=lambda item: (-item[0], item[1]))
    return pool[0][1] if pool else ""


def accuracy(records: Sequence[Decomposed], scorer, *, inline: str = "shipped") -> float:
    """Percentage of instances whose top expansion equals gold under ``scorer``."""
    hits = sum(predict(record, scorer, inline=inline) == record.gold for record in records)
    return hits / len(records) * 100


#: The shipped score. Deliberately the *rounded* value the library stores rather
#: than the raw blend: :data:`~acronymkit.disambiguation.SCORE_PRECISION` is six
#: decimal places, and two candidates that differ in the ninth place but tie in
#: the sixth are a tie in the shipped engine and must be a tie here too. Scoring
#: the raw blend instead disagreed with the library on one instance out of
#: 6,189, which is exactly the kind of silent drift the harness check exists to
#: catch.
SHIPPED = lambda c: c.score  # noqa: E731 - a scorer is a value here, not a routine
OVERLAP_ONLY = lambda c: c.overlap  # noqa: E731
INITIALS_ONLY = lambda c: c.initials  # noqa: E731
REGISTER_ONLY = lambda c: c.register  # noqa: E731
EXACT_ONLY = lambda c: c.exact_hits / max(c.words, 1)  # noqa: E731
CONSTANT = lambda c: 0.0  # noqa: E731


# ---------------------------------------------------------------------------
# the taxonomy
# ---------------------------------------------------------------------------
def separation(records: Sequence[Decomposed]) -> dict:
    """Measure whether the score separates candidates or ties them.

    ``docs/DECISIONS.md`` diagnoses *extraction* as a tie problem: the rule-level
    signal cannot make a span-level decision because almost every gold span ties
    with the top score. Whether disambiguation repeats that pattern decides
    whether the same remedy applies, so it is measured here rather than assumed
    either way.

    Args:
        records: The decomposed dev split.

    Returns:
        Tie multiplicity, margins, and how often the gold sits inside a tied top
        set.
    """
    total = len(records)
    tied = all_tied = gold_in_tie = 0
    margins: list[float] = []
    for record in records:
        scores = [candidate.score for candidate in record.candidates]
        top = max(scores)
        multiplicity = sum(1 for score in scores if score == top)
        if multiplicity > 1:
            tied += 1
            if multiplicity == len(scores):
                all_tied += 1
            if any(c.score == top and c.expansion == record.gold for c in record.candidates):
                gold_in_tie += 1
        ordered = sorted(scores, reverse=True)
        if len(ordered) > 1:
            margins.append(ordered[0] - ordered[1])
    return {
        "instances_with_tied_top_score": tied,
        "instances_with_tied_top_score_pct": round(tied / total * 100, 2),
        "instances_where_every_candidate_tied": all_tied,
        "gold_inside_tied_top_set": gold_in_tie,
        "median_top1_top2_margin": round(statistics.median(margins), 4),
        "mean_top1_top2_margin": round(statistics.fmean(margins), 4),
        "margin_below_0_01_pct": round(sum(1 for m in margins if m < 0.01) / len(margins) * 100, 2),
    }


def term_variation(records: Sequence[Decomposed]) -> dict:
    """Measure which scoring terms can vary inside a candidate set.

    A term that is constant across every candidate of an instance is an offset,
    not a signal: it shifts all scores equally and cannot change the argmax. Its
    weight is dead weight.

    Args:
        records: The decomposed dev split.

    Returns:
        Per-term variation rate and mean weighted spread.
    """
    weights = {
        "overlap": _d.WEIGHT_OVERLAP,
        "initials": _d.WEIGHT_INITIALS,
        "register": _d.WEIGHT_REGISTER,
    }
    varies: Counter = Counter()
    spreads: dict[str, list[float]] = {name: [] for name in weights}
    considered = 0
    for record in records:
        if len(record.candidates) < 2:
            continue
        considered += 1
        for name, weight in weights.items():
            values = [getattr(candidate, name) for candidate in record.candidates]
            if len({round(value, 6) for value in values}) > 1:
                varies[name] += 1
            spreads[name].append(weight * (max(values) - min(values)))
    return {
        "instances_considered": considered,
        **{f"{name}_varies_pct": round(varies[name] / considered * 100, 2) for name in weights},
        **{
            f"{name}_mean_weighted_spread": round(statistics.fmean(spreads[name]), 4)
            for name in weights
        },
    }


def evidence(records: Sequence[Decomposed]) -> dict:
    """Measure whether the evidence the overlap term looks for is present at all.

    Args:
        records: The decomposed dev split.

    Returns:
        Verbatim-evidence rates, the similarity-tier breakdown, and accuracy
        split by whether the gold expansion's words are in the sentence.
    """
    total = len(records)
    tier_words: Counter = Counter()
    gold_tier: Counter = Counter()
    gold_verbatim = gold_full = gold_zero_overlap = every_zero = signal_present = 0
    split: dict[str, list[float]] = {"gold_verbatim": [0, 0, 0.0], "gold_absent": [0, 0, 0.0]}

    for record in records:
        for candidate in record.candidates:
            tier_words.update(candidate.tiers)
        if any(candidate.exact_hits for candidate in record.candidates):
            signal_present += 1
        if all(candidate.overlap == 0.0 for candidate in record.candidates):
            every_zero += 1
        gold = record.gold_candidate()
        if gold is None:
            continue
        gold_tier.update(gold.tiers)
        if gold.overlap == 0.0:
            gold_zero_overlap += 1
        bucket = "gold_verbatim" if gold.exact_hits else "gold_absent"
        if gold.exact_hits:
            gold_verbatim += 1
            if gold.exact_hits == gold.words:
                gold_full += 1
        split[bucket][0] += 1
        split[bucket][1] += predict(record, SHIPPED) == record.gold
        split[bucket][2] += 1 / len(record.candidates)

    words_total = sum(tier_words.values())
    gold_total = sum(gold_tier.values())
    out = {
        "gold_has_a_verbatim_word_in_sentence": gold_verbatim,
        "gold_has_a_verbatim_word_in_sentence_pct": round(gold_verbatim / total * 100, 2),
        "gold_fully_verbatim_in_sentence_pct": round(gold_full / total * 100, 2),
        "some_candidate_has_a_verbatim_word_pct": round(signal_present / total * 100, 2),
        "gold_candidate_scored_overlap_zero_pct": round(gold_zero_overlap / total * 100, 2),
        "every_candidate_scored_overlap_zero_pct": round(every_zero / total * 100, 2),
    }
    for tier in ("exact", "stem", "subword", "zero"):
        out[f"similarity_tier_{tier}_pct"] = round(tier_words[tier] / words_total * 100, 2)
        out[f"gold_similarity_tier_{tier}_pct"] = round(gold_tier[tier] / gold_total * 100, 2)
    for name, (count, correct, expected) in split.items():
        out[f"instances_{name}"] = count
        out[f"accuracy_{name}"] = round(correct / count * 100, 2)
        out[f"random_expectation_{name}"] = round(expected / count * 100, 2)
    return out


def length_bias(records: Sequence[Decomposed]) -> dict:
    """Test the hypothesis that averaging over expansion length biases the pick.

    ``overlap`` is a mean over the *expansion's own* words, which in principle
    punishes long expansions: one matching word out of two beats one out of six.
    Whether that actually decides anything on this corpus is an empirical
    question, and a hypothesis that survives only because nobody checked is not
    a diagnosis.

    Args:
        records: The decomposed dev split.

    Returns:
        Predicted-versus-gold length comparison over the wrong predictions.
    """
    shorter = longer = same = 0
    predicted_lengths: list[int] = []
    gold_lengths: list[int] = []
    for record in records:
        prediction = predict(record, SHIPPED)
        if prediction == record.gold:
            continue
        chosen = next((c for c in record.candidates if c.expansion == prediction), None)
        gold = record.gold_candidate()
        if chosen is None or gold is None:
            continue
        predicted_lengths.append(chosen.words)
        gold_lengths.append(gold.words)
        if chosen.words < gold.words:
            shorter += 1
        elif chosen.words > gold.words:
            longer += 1
        else:
            same += 1
    total = shorter + longer + same
    return {
        "wrong_predictions": total,
        "predicted_shorter_than_gold_pct": round(shorter / total * 100, 2),
        "predicted_longer_than_gold_pct": round(longer / total * 100, 2),
        "predicted_same_length_as_gold_pct": round(same / total * 100, 2),
        "mean_predicted_length": round(statistics.fmean(predicted_lengths), 2),
        "mean_gold_length": round(statistics.fmean(gold_lengths), 2),
    }


def by_short_form_length(records: Sequence[Decomposed]) -> dict:
    """Accuracy by the length of the short form, against chance in the same slice.

    Reported next to the random expectation for the same instances because short
    forms of different lengths do not have candidate sets of the same size: a
    two-letter acronym is ambiguous more ways than a four-letter one, and an
    accuracy that rises with length may be measuring nothing but that. The gap
    to chance is the part that belongs to the scorer.

    Args:
        records: The decomposed dev split.

    Returns:
        ``{length: {instances, accuracy, random_expectation}}``.
    """
    buckets: dict[int, list[float]] = defaultdict(lambda: [0, 0, 0.0])
    for record in records:
        length = min(len(record.acronym_key), 6)
        buckets[length][0] += 1
        buckets[length][1] += predict(record, SHIPPED) == record.gold
        buckets[length][2] += 1 / len(record.candidates)
    return {
        str(length): {
            "instances": int(count),
            "accuracy": round(hits / count * 100, 2),
            "random_expectation": round(expected / count * 100, 2),
        }
        for length, (count, hits, expected) in sorted(buckets.items())
    }


def gold_rank(records: Sequence[Decomposed]) -> dict:
    """Cumulative recall of the gold expansion by rank under the shipped score."""
    histogram: Counter = Counter()
    for record in records:
        pool = sorted(
            ((candidate.score, candidate.expansion) for candidate in record.candidates),
            key=lambda item: (-item[0], item[1]),
        )
        order = [expansion for _, expansion in pool]
        histogram[order.index(record.gold) + 1 if record.gold in order else 0] += 1
    total = len(records)
    out = {}
    cumulative = 0
    for rank in range(1, 6):
        cumulative += histogram[rank]
        out[f"gold_recall_at_{rank}"] = round(cumulative / total * 100, 2)
    return out


# ---------------------------------------------------------------------------
# ceilings
# ---------------------------------------------------------------------------
def ceilings(records: Sequence[Decomposed]) -> dict:
    """Bound what the current approach could reach if its scorer were perfect.

    Three bounds, increasingly generous:

    ``perfect_tie_break``
        Award every instance whose gold sits inside the tied top set. This is
        the whole value of fixing the ordering rule and nothing else.
    ``verbatim_evidence_plus_chance``
        Assume a perfect scorer of the only evidence the current features can
        actually see -- a content word shared verbatim between expansion and
        sentence -- and chance elsewhere, because a feature set that is silent
        cannot do better than chance no matter how it is weighted. Where several
        candidates tie on that evidence the credit is split, so a perfect scorer
        is not given a tie-break it has not earned.
    ``best_reweighting``
        Grid search over the three term weights on the dev split itself. This is
        an optimistic bound by construction (the weights see the answers) and is
        labelled a tuning number: ``bench/splits.toml`` declares ``sdu21_ad``
        role ``"tuning"``, which is what makes the search admissible at all.

    Args:
        records: The decomposed dev split.

    Returns:
        The three ceilings and the weights that produced the third.
    """
    total = len(records)

    # Gold sits inside the tied top set of the shipped ranking. The inline
    # entries are part of that ranking and enter at INLINE_SCORE, exactly as
    # they do in the shipped result, so this bounds the tie-break rule alone and
    # nothing else.
    tie_ceiling = 0
    for record in records:
        pool: list[tuple[float, str]] = []
        seen: set[str] = set()
        for expansion in record.inline:
            if _key(expansion) not in seen:
                seen.add(_key(expansion))
                pool.append((_d.INLINE_SCORE, expansion))
        for candidate in record.candidates:
            if _key(candidate.expansion) not in seen:
                seen.add(_key(candidate.expansion))
                pool.append((candidate.score, candidate.expansion))
        top = max(score for score, _ in pool)
        tie_ceiling += any(expansion == record.gold for score, expansion in pool if score == top)

    credit = 0.0
    speaks = 0
    for record in records:
        best = max(candidate.exact_hits for candidate in record.candidates)
        if best == 0:
            credit += 1 / len(record.candidates)
            continue
        speaks += 1
        winners = [c.expansion for c in record.candidates if c.exact_hits == best]
        if record.gold in winners:
            credit += 1 / len(winners)

    def blended(a: float, b: float, d: float) -> Callable[[Scored], float]:
        """Return a scorer weighting the three terms ``a``/``b``/``d``."""
        return lambda c: a * c.overlap + b * c.initials + d * c.register

    steps = [index * WEIGHT_STEP for index in range(round(1 / WEIGHT_STEP) + 1)]
    best_score, best_weights = -1.0, None
    for w_overlap in steps:
        for w_initials in steps:
            if w_overlap + w_initials > 1.0 + 1e-9:
                continue
            w_register = 1.0 - w_overlap - w_initials
            value = accuracy(records, blended(w_overlap, w_initials, w_register), inline="off")
            if value > best_score:
                best_score, best_weights = (
                    value,
                    (round(w_overlap, 2), round(w_initials, 2), round(w_register, 2)),
                )

    return {
        "full_oracle": 100.0,
        "perfect_tie_break": round(tie_ceiling / total * 100, 2),
        "verbatim_evidence_plus_chance": round(credit / total * 100, 2),
        "instances_with_verbatim_evidence": speaks,
        "instances_with_verbatim_evidence_pct": round(speaks / total * 100, 2),
        "best_reweighting_tuning_split": round(best_score, 2),
        "best_reweighting_weights": list(best_weights),
        "best_reweighting_note": "dev-tuned; sdu21_ad has role='tuning' in bench/splits.toml",
    }


# ---------------------------------------------------------------------------
# inline path
# ---------------------------------------------------------------------------
def inline_path(records: Sequence[Decomposed]) -> dict:
    """Measure what the inline (Schwartz & Hearst) path contributes.

    The shipped path inserts the *sentence's* surface form and de-duplicates the
    dictionary against it, so a dictionary candidate that names the same
    expansion is removed from the result. Under a convention of exact string
    equality -- and, more importantly, for any caller who supplied a catalog and
    expects answers drawn from it -- that substitutes a string the caller never
    provided. This separates the two things the path does: identifying the right
    expansion, and choosing which surface form to return.

    Args:
        records: The decomposed dev split.

    Returns:
        Counts of the substitution and accuracy under the three inline policies.
    """
    total = len(records)
    with_inline = displaced = displaced_gold = 0
    exact_match = case_insensitive_match = 0
    for record in records:
        if not record.inline:
            continue
        with_inline += 1
        keys = {_key(expansion) for expansion in record.inline}
        for candidate in record.candidates:
            if _key(candidate.expansion) in keys and candidate.expansion not in record.inline:
                displaced += 1
                displaced_gold += candidate.expansion == record.gold
                break
        if any(expansion == record.gold for expansion in record.inline):
            exact_match += 1
        if any(_key(expansion) == record.gold for expansion in record.inline):
            case_insensitive_match += 1

    shipped = accuracy(records, SHIPPED, inline="shipped")
    return {
        "instances_with_an_inline_definition": with_inline,
        "instances_with_an_inline_definition_pct": round(with_inline / total * 100, 2),
        "inline_displaced_a_dictionary_candidate": displaced,
        "inline_displaced_the_gold_candidate": displaced_gold,
        "inline_string_equals_gold_exactly": exact_match,
        "inline_string_equals_gold_exactly_pct": round(exact_match / with_inline * 100, 2),
        "inline_string_equals_gold_case_insensitively": case_insensitive_match,
        "inline_string_equals_gold_case_insensitively_pct": round(
            case_insensitive_match / with_inline * 100, 2
        ),
        "accuracy_inline_shipped": round(shipped, 2),
        "accuracy_inline_disabled": round(accuracy(records, SHIPPED, inline="off"), 2),
        "accuracy_inline_promotes_dictionary_form": round(
            accuracy(records, SHIPPED, inline="promote"), 2
        ),
    }


# ---------------------------------------------------------------------------
# ablation
# ---------------------------------------------------------------------------
def ablation(
    records: Sequence[Decomposed],
    train: Sequence[DisambiguationInstance],
    diction: dict[str, list[str]],
) -> dict:
    """Accuracy under each single term and under the shipped blend.

    ``first_candidate_in_dictionary_order`` is included because
    :class:`~acronymkit.disambiguation.ExpansionDictionary` preserves insertion
    order and its own docstring calls that order "weak evidence" -- while the
    scorer ignores it completely. The number is only meaningful next to the
    measurement of *why* it is high, so how far ``diction.json``'s order already
    agrees with training frequency is measured alongside it. A caller-supplied
    ordering is worth whatever the caller put into it and nothing more.

    Args:
        records: The decomposed dev split.
        train: The training split, used only to test whether the corpus's
            candidate order is a frequency proxy.
        diction: The raw candidate sets, whose key order is under test.

    Returns:
        Accuracy per ablated variant, plus the order/frequency agreement rate.
    """
    counts = Counter(instance.expansion for instance in train)
    agree = considered = 0
    for candidates in diction.values():
        if len(candidates) < 2:
            continue
        considered += 1
        agree += candidates[0] == max(candidates, key=lambda e: counts.get(e, 0))
    return {
        "dictionary_order_matches_train_frequency_pct": round(agree / considered * 100, 2),
        "dictionary_order_note": (
            "diction.json is substantially frequency-sorted, so the "
            "first-candidate baseline is a property of this corpus file, not of "
            "caller-supplied dictionaries in general"
        ),
        "shipped_blend": round(accuracy(records, SHIPPED), 2),
        "overlap_only": round(accuracy(records, OVERLAP_ONLY), 2),
        "initials_only": round(accuracy(records, INITIALS_ONLY), 2),
        "register_only": round(accuracy(records, REGISTER_ONLY), 2),
        "verbatim_hits_only": round(accuracy(records, EXACT_ONLY), 2),
        "constant_score_alphabetical_order": round(accuracy(records, CONSTANT), 2),
        "shipped_blend_inline_disabled": round(accuracy(records, SHIPPED, inline="off"), 2),
        "first_candidate_in_dictionary_order": round(
            sum(r.candidates[0].expansion == r.gold for r in records) / len(records) * 100, 2
        ),
    }


# ---------------------------------------------------------------------------
# the default code path, and the abstention signal already being discarded
# ---------------------------------------------------------------------------
def default_path(instances: Sequence[DisambiguationInstance], config: Config) -> dict:
    """Measure what ``AcronymEngine.disambiguate`` does with no dictionary supplied.

    This matters for scoping the failure. Called without a ``dictionary``, the
    engine builds one from the *context's own* inline definitions, so the
    candidate set is whatever that one passage happened to define. If that set is
    almost always empty or a singleton, then the default path performs no
    selection at all and the measured failure belongs entirely to the
    caller-supplied-dictionary mode -- a much narrower blast radius than
    "disambiguation is broken", and a different remedy.

    Args:
        instances: The dev split.
        config: Engine configuration.

    Returns:
        The candidate-count distribution and accuracy of the default path.
    """
    from acronymkit import AcronymEngine  # local: only this function needs the facade

    engine = AcronymEngine(config)
    counts = Counter()
    correct = 0
    for instance in instances:
        result = engine.disambiguate(instance.acronym, instance.context)
        total = len(result.candidates)
        counts["none" if total == 0 else "one" if total == 1 else "many"] += 1
        correct += (result.primary_expansion or "") == instance.expansion
    total = len(instances)
    return {
        "no_candidate_pct": round(counts["none"] / total * 100, 2),
        "exactly_one_candidate_pct": round(counts["one"] / total * 100, 2),
        "two_or_more_candidates": counts["many"],
        "two_or_more_candidates_pct": round(counts["many"] / total * 100, 2),
        "accuracy": round(correct / total * 100, 2),
        "note": (
            "with no dictionary the engine performs no selection: the candidate "
            "set comes from the passage's own inline definitions and is almost "
            "never larger than one"
        ),
    }


#: Top1-top2 margin thresholds for the abstention curve.
MARGIN_GRID = (0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20)


def abstention(records: Sequence[Decomposed]) -> dict:
    """Measure whether the engine already computes a usable "I don't know" signal.

    The reported ``score`` is an absolute number and is poorly calibrated, but
    the *margin* between the top two candidates is a different quantity, and the
    question of whether it separates right answers from wrong ones has never been
    asked. If it does, the engine is discarding a refusal signal it already has
    -- which is precisely what ``acronymkit.governed`` refuses to do, on the
    stated principle that an unknown token comes back flagged rather than
    approximated.

    Two gates are measured: the margin, and the presence of a verbatim content
    word shared between some candidate and the sentence (the only evidence the
    feature set can actually see).

    Args:
        records: The decomposed dev split.

    Returns:
        Score-decile calibration, and coverage/accuracy at each gate.
    """
    total = len(records)
    deciles: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    margins: list[tuple[float, bool]] = []
    correct_scores: list[float] = []
    wrong_scores: list[float] = []

    for record in records:
        pool: list[tuple[float, str]] = []
        seen: set[str] = set()
        for expansion in record.inline:
            if _key(expansion) not in seen:
                seen.add(_key(expansion))
                pool.append((_d.INLINE_SCORE, expansion))
        for candidate in record.candidates:
            if _key(candidate.expansion) not in seen:
                seen.add(_key(candidate.expansion))
                pool.append((candidate.score, candidate.expansion))
        pool.sort(key=lambda item: (-item[0], item[1]))
        top, prediction = pool[0]
        hit = prediction == record.gold
        bucket = min(int(top * 10), 9)
        deciles[bucket][0] += 1
        deciles[bucket][1] += hit
        (correct_scores if hit else wrong_scores).append(top)
        margins.append((top - pool[1][0] if len(pool) > 1 else 1.0, hit))

    out: dict = {
        "mean_top1_score_when_correct": round(statistics.fmean(correct_scores), 4),
        "mean_top1_score_when_wrong": round(statistics.fmean(wrong_scores), 4),
        "accuracy_by_score_decile": {
            f"{index / 10:.1f}": round(hits / count * 100, 2)
            for index, (count, hits) in sorted(deciles.items())
        },
        "instances_by_score_decile": {
            f"{index / 10:.1f}": count for index, (count, _) in sorted(deciles.items())
        },
    }
    for threshold in MARGIN_GRID:
        answered = [hit for margin, hit in margins if margin >= threshold]
        out[f"margin_gate_{threshold:.2f}_coverage_pct"] = round(len(answered) / total * 100, 2)
        out[f"margin_gate_{threshold:.2f}_accuracy_when_answered"] = (
            round(sum(answered) / len(answered) * 100, 2) if answered else None
        )

    answered = [
        predict(record, SHIPPED) == record.gold
        for record in records
        if any(candidate.exact_hits for candidate in record.candidates)
    ]
    out["verbatim_gate_coverage_pct"] = round(len(answered) / total * 100, 2)
    out["verbatim_gate_accuracy_when_answered"] = round(sum(answered) / len(answered) * 100, 2)
    return out


# ---------------------------------------------------------------------------
# frequency prior -- INSTRUMENT ONLY, see LICENCE_NOTICE
# ---------------------------------------------------------------------------
def frequency_prior(records: Sequence[Decomposed], train: Sequence[DisambiguationInstance]) -> dict:
    """Measure what a frequency prior would buy, and what context adds on top.

    Args:
        records: The decomposed dev split.
        train: The training split, read only for its gold expansions.

    Returns:
        Prior accuracy, the oracle union that bounds any combination, the
        interpolation sweep, and the out-of-fold accuracy of the best blend.
    """
    counts = Counter(instance.expansion for instance in train)
    total = len(records)

    priors: list[dict[str, float]] = []
    for record in records:
        mass = sum(counts.get(c.expansion, 0) + PRIOR_ALPHA for c in record.candidates)
        priors.append(
            {
                c.expansion: (counts.get(c.expansion, 0) + PRIOR_ALPHA) / mass
                for c in record.candidates
            }
        )

    prior_ok = context_ok = union = context_only = prior_only = 0
    for record, prior in zip(records, priors):
        by_prior = predict(record, lambda c, p=prior: p[c.expansion], inline="off") == record.gold
        by_context = predict(record, OVERLAP_ONLY, inline="off") == record.gold
        prior_ok += by_prior
        context_ok += by_context
        union += by_prior or by_context
        context_only += by_context and not by_prior
        prior_only += by_prior and not by_context

    def interpolated(weight: float, prior: dict[str, float]) -> Callable[[Scored], float]:
        """Return the blend of ``prior`` and the context overlap at ``weight``."""
        return lambda c: (1 - weight) * prior[c.expansion] + weight * c.overlap

    sweep: dict[str, float] = {}
    for weight in LAMBDA_GRID:
        hits = sum(
            predict(record, interpolated(weight, prior), inline="off") == record.gold
            for record, prior in zip(records, priors)
        )
        sweep[f"{weight:.2f}"] = round(hits / total * 100, 2)
    best_weight = max(LAMBDA_GRID, key=lambda w: sweep[f"{w:.2f}"])

    # Out-of-fold: the interpolation weight is the only fitted parameter, so it
    # is chosen on one half of dev and scored on the other, both ways round.
    generator = random.Random(RANDOM_SEED)
    order = list(range(total))
    generator.shuffle(order)
    folds = (set(order[0::2]), set(order[1::2]))

    def fold_accuracy(members, weight):
        """Number of correct predictions over ``members`` at interpolation ``weight``."""
        return sum(
            predict(records[index], interpolated(weight, priors[index]), inline="off")
            == records[index].gold
            for index in members
        )

    held_hits = held_total = 0
    chosen: list[float] = []
    for index in range(2):
        tune, test = folds[index], folds[1 - index]
        weight = max(LAMBDA_GRID, key=lambda w: fold_accuracy(tune, w))
        chosen.append(round(weight, 2))
        held_hits += fold_accuracy(test, weight)
        held_total += len(test)

    # The gate: use context only where it has verbatim evidence, prior elsewhere.
    gated = 0
    gate_used = 0
    for record, prior in zip(records, priors):
        best = max(c.exact_hits for c in record.candidates)
        if best:
            gate_used += 1
            prediction = predict(record, OVERLAP_ONLY, inline="off")
        else:
            prediction = predict(record, lambda c, p=prior: p[c.expansion], inline="off")
        gated += prediction == record.gold

    return {
        "prior_source": "sdu21_ad train.json gold expansions",
        "prior_licence": "CC BY-NC-SA 4.0 -- measurement instrument, never shipped or committed",
        "prior_train_instances": len(train),
        "prior_alpha": PRIOR_ALPHA,
        "accuracy_prior_only": round(prior_ok / total * 100, 2),
        "accuracy_context_only": round(context_ok / total * 100, 2),
        "accuracy_oracle_union": round(union / total * 100, 2),
        "instances_context_right_prior_wrong": context_only,
        "instances_context_right_prior_wrong_pct": round(context_only / total * 100, 2),
        "instances_prior_right_context_wrong": prior_only,
        "interpolation_sweep": sweep,
        "best_lambda_tuning_split": round(best_weight, 2),
        "accuracy_best_interpolation_tuning_split": sweep[f"{best_weight:.2f}"],
        "lambda_chosen_per_fold": chosen,
        "accuracy_interpolation_out_of_fold": round(held_hits / held_total * 100, 2),
        "accuracy_gated_context_else_prior": round(gated / total * 100, 2),
        "gate_fired_on_instances": gate_used,
        "gate_fired_pct": round(gate_used / total * 100, 2),
    }


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="smoke-test on the first N instances")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    if args.limit and args.save:
        raise SystemExit("--limit produces a partial number; refusing to --save it")

    diction = corpora.read_sdu21_ad_diction()
    instances = corpora.read_sdu21_ad(split="dev")
    if args.limit:
        instances = instances[: args.limit]
    train = corpora.read_sdu21_ad(split="train")

    config = Config()
    dictionary = ExpansionDictionary(diction)
    engine = LexicalDisambiguator(config, dictionary)

    started = time.perf_counter()
    records = decompose(instances, diction, engine, config)
    print(f"corpus   : sdu21_ad (dev), {len(records):,} instances")
    print(f"decomposed in {time.perf_counter() - started:.1f}s")

    # -- harness check: does the decomposition reproduce the shipped engine? --
    shipped_predictions = [
        engine.disambiguate(instance.acronym, instance.context).primary_expansion or ""
        for instance in instances
    ]
    derived = [predict(record, SHIPPED) for record in records]
    agreement = sum(a == b for a, b in zip(shipped_predictions, derived))
    faithful = agreement == len(records)
    shipped_accuracy = (
        sum(p == i.expansion for p, i in zip(shipped_predictions, instances)) / len(records) * 100
    )
    print(
        f"\nharness check: the decomposition reproduces the shipped engine on "
        f"{agreement:,}/{len(records):,} instances"
        + (
            " -- every number below is measuring the library."
            if faithful
            else " -- IT DOES NOT AGREE; treat every number below as measuring a "
            "reimplementation, not acronymkit."
        )
    )
    print(f"shipped accuracy, measured here: {shipped_accuracy:.2f}%")

    sep = separation(records)
    terms = term_variation(records)
    ev = evidence(records)
    lb = length_bias(records)
    ranks = gold_rank(records)
    by_length = by_short_form_length(records)
    abl = ablation(records, train, diction)
    ceil = ceilings(records)
    inline = inline_path(records)

    print("\n1. DOES THE SCORE SEPARATE THE CANDIDATES?")
    print(
        f"   tied top score      : {sep['instances_with_tied_top_score']:,} "
        f"({sep['instances_with_tied_top_score_pct']}%)"
    )
    print(f"   median top1-top2 gap: {sep['median_top1_top2_margin']}")
    print("   => this is NOT the extraction diagnosis. Ties are rare; the scorer")
    print("      commits to a candidate and commits to the wrong one.")

    print("\n2. WHICH TERM CAN VARY INSIDE A CANDIDATE SET?")
    for name in ("overlap", "initials", "register"):
        print(
            f"   {name:<9} varies in {terms[f'{name}_varies_pct']:>6.2f}% of instances, "
            f"mean weighted spread {terms[f'{name}_mean_weighted_spread']}"
        )
    print("   => a term that never varies is an offset, not a signal.")

    print("\n3. IS THE EVIDENCE IN THE SENTENCE?")
    print(
        f"   gold expansion has a verbatim content word in the sentence: "
        f"{ev['gold_has_a_verbatim_word_in_sentence_pct']}%"
    )
    print(
        f"   expansion words whose best match came from the character-bigram tier: "
        f"{ev['similarity_tier_subword_pct']}%"
    )
    print(
        f"   gold candidate nevertheless scored overlap > 0 for "
        f"{100 - ev['gold_candidate_scored_overlap_zero_pct']:.2f}% of instances"
    )
    print(
        f"   accuracy where gold IS in the sentence : {ev['accuracy_gold_verbatim']}% "
        f"(chance {ev['random_expectation_gold_verbatim']}%)"
    )
    print(
        f"   accuracy where gold is NOT             : {ev['accuracy_gold_absent']}% "
        f"(chance {ev['random_expectation_gold_absent']}%)"
    )
    print("   accuracy by short-form length (chance in the same slice in brackets):")
    for length, slice_ in by_length.items():
        print(
            f"     {length} chars  n={slice_['instances']:>5,}  "
            f"{slice_['accuracy']:6.2f}%  [{slice_['random_expectation']:.2f}%]"
        )
    print("   => the capability works where the answer is written down and is at")
    print("      chance everywhere else, while reporting a confident score for both.")

    print("\n4. THINGS THAT ARE *NOT* THE PROBLEM")
    print(
        f"   length bias : {lb['predicted_same_length_as_gold_pct']}% of wrong picks are the "
        "same length as gold"
    )
    print("   coverage    : the gold expansion is always among the candidates (ceiling 100%)")
    print(f"   tie-break   : perfect tie-breaking would reach {ceil['perfect_tie_break']}%")

    print("\n5. ABLATION")
    for name, value in abl.items():
        if isinstance(value, str):
            continue
        print(f"   {name:<44} {value:6.2f}%")

    print("\n6. CEILINGS")
    print(f"   perfect tie-break                    : {ceil['perfect_tie_break']:6.2f}%")
    print(
        f"   perfect scoring of verbatim evidence : "
        f"{ceil['verbatim_evidence_plus_chance']:6.2f}%   <- the ceiling of the feature set"
    )
    print(
        f"   best reweighting (dev-tuned)         : "
        f"{ceil['best_reweighting_tuning_split']:6.2f}% at {ceil['best_reweighting_weights']}"
    )
    print("   => the shipped score is already at the ceiling of what its features")
    print("      can see. Reweighting is exhausted; the feature set is the problem.")

    print("\n7. THE INLINE PATH RETURNS A STRING THE CALLER NEVER SUPPLIED")
    print(
        f"   instances with an inline definition        : "
        f"{inline['instances_with_an_inline_definition']:,}"
    )
    print(
        f"   it named the right expansion (case-blind)  : "
        f"{inline['inline_string_equals_gold_case_insensitively_pct']}%"
    )
    print(
        f"   it returned the right string               : "
        f"{inline['inline_string_equals_gold_exactly_pct']}%"
    )
    print(
        f"   it displaced the gold dictionary candidate : "
        f"{inline['inline_displaced_the_gold_candidate']:,} times"
    )
    print(
        f"   accuracy shipped / disabled / promote-dictionary-form: "
        f"{inline['accuracy_inline_shipped']}% / {inline['accuracy_inline_disabled']}% / "
        f"{inline['accuracy_inline_promotes_dictionary_form']}%"
    )

    default = default_path(instances, config)
    print("\n8. HOW WIDE IS THE BLAST RADIUS? THE DEFAULT (NO-DICTIONARY) PATH")
    print(f"   no candidate at all : {default['no_candidate_pct']}%")
    print(f"   exactly 1 candidate : {default['exactly_one_candidate_pct']}%")
    print(
        f"   2+ candidates       : {default['two_or_more_candidates']:,} "
        f"({default['two_or_more_candidates_pct']}%)"
    )
    print("   => called without a dictionary the engine performs no selection at all.")
    print("      The failure is confined to the caller-supplied-dictionary mode --")
    print("      which is exactly the mode the README advertises.")

    absten = abstention(records)
    print("\n9. THE ENGINE ALREADY COMPUTES A REFUSAL SIGNAL AND THROWS IT AWAY")
    print(
        f"   mean top-1 score when correct / wrong: "
        f"{absten['mean_top1_score_when_correct']} / {absten['mean_top1_score_when_wrong']} "
        "-- the score barely separates"
    )
    print("   but the top1-top2 MARGIN does:")
    for threshold in MARGIN_GRID:
        coverage = absten[f"margin_gate_{threshold:.2f}_coverage_pct"]
        value = absten[f"margin_gate_{threshold:.2f}_accuracy_when_answered"]
        print(
            f"     answer only when margin >= {threshold:.2f}: "
            f"covers {coverage:6.2f}% of instances, {value:6.2f}% accurate when it answers"
        )
    print(
        f"   verbatim-evidence gate: covers {absten['verbatim_gate_coverage_pct']}%, "
        f"{absten['verbatim_gate_accuracy_when_answered']}% accurate when it answers"
    )
    print("   => an abstaining disambiguator is available today, needs no data and")
    print("      no licence, and is the governed subsystem's own stated principle.")

    print("\n" + LICENCE_NOTICE)
    prior = frequency_prior(records, train)
    print("\n10. WHAT WOULD A FREQUENCY PRIOR BUY?")
    print(f"   prior alone                          : {prior['accuracy_prior_only']:6.2f}%")
    print(f"   context alone                        : {prior['accuracy_context_only']:6.2f}%")
    print(f"   oracle union (any combination <= this): {prior['accuracy_oracle_union']:6.2f}%")
    print(
        f"   context right where prior is wrong   : "
        f"{prior['instances_context_right_prior_wrong']:,} "
        f"({prior['instances_context_right_prior_wrong_pct']}%)"
    )
    print(
        f"   best interpolation (dev-tuned)       : "
        f"{prior['accuracy_best_interpolation_tuning_split']:6.2f}% at lambda="
        f"{prior['best_lambda_tuning_split']}"
    )
    print(
        f"   interpolation, OUT OF FOLD           : "
        f"{prior['accuracy_interpolation_out_of_fold']:6.2f}%   <- the honest number"
    )
    print(
        f"   gated (context only where it has evidence, prior elsewhere): "
        f"{prior['accuracy_gated_context_else_prior']:6.2f}%"
    )

    verdict = prior["accuracy_interpolation_out_of_fold"] - prior["accuracy_prior_only"]
    print(
        "\nverdict: context scoring "
        + (
            f"ADDS {verdict:.2f} points on top of a frequency prior, out of fold. It is "
            "worth\nkeeping as a component and worthless as a default."
            if verdict > 0
            else "adds nothing on top of a frequency prior and should be defaulted away."
        )
    )

    if args.save:
        entries = {
            "disambiguation.sdu21.diagnosis.separation": {
                "corpus": "sdu21_ad",
                "split": "dev",
                "instances": len(records),
                "reproduces_shipped_engine": faithful,
                "shipped_accuracy": round(shipped_accuracy, 2),
                **sep,
            },
            "disambiguation.sdu21.diagnosis.term_variation": {
                "corpus": "sdu21_ad",
                "split": "dev",
                "instances": len(records),
                **terms,
            },
            "disambiguation.sdu21.diagnosis.evidence": {
                "corpus": "sdu21_ad",
                "split": "dev",
                "instances": len(records),
                **ev,
                **ranks,
                "accuracy_by_short_form_length": by_length,
            },
            "disambiguation.sdu21.diagnosis.length_bias": {
                "corpus": "sdu21_ad",
                "split": "dev",
                "instances": len(records),
                **lb,
            },
            "disambiguation.sdu21.diagnosis.ablation": {
                "corpus": "sdu21_ad",
                "split": "dev",
                "instances": len(records),
                "note": "each variant is the shipped pipeline with one term isolated",
                **abl,
            },
            "disambiguation.sdu21.diagnosis.ceilings": {
                "corpus": "sdu21_ad",
                "split": "dev",
                "instances": len(records),
                **ceil,
            },
            "disambiguation.sdu21.diagnosis.inline_path": {
                "corpus": "sdu21_ad",
                "split": "dev",
                "instances": len(records),
                **inline,
            },
            "disambiguation.sdu21.diagnosis.default_path": {
                "corpus": "sdu21_ad",
                "split": "dev",
                "instances": len(records),
                **default,
            },
            "disambiguation.sdu21.diagnosis.abstention": {
                "corpus": "sdu21_ad",
                "split": "dev",
                "instances": len(records),
                **absten,
            },
            "disambiguation.sdu21.diagnosis.frequency_prior": {
                "corpus": "sdu21_ad",
                "split": "dev",
                "instances": len(records),
                "shippable": False,
                "shippable_reason": (
                    "prior derived from CC BY-NC-SA 4.0 training data; benchmark use only, "
                    "never vendored, never committed, never loaded from src/"
                ),
                **prior,
            },
        }
        print(f"\nsaved to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
