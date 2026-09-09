#!/usr/bin/env python3
"""Does a schema-derived frequency prior transfer to prose disambiguation?

Why this runner exists
----------------------
``GovernedDictionary`` and ``ExpansionDictionary`` are two *caller-supplies-the-
data* contracts in one codebase that have never spoken to each other. Under the
governance positioning the caller has a catalog by definition, and a governed
catalog with entry frequencies over the caller's own schema looks like the
frequency prior the disambiguation half has been missing since D-020: no data
shipped, no licence problem, an asset the caller already brought.

``disambiguation.sdu21.diagnosis.frequency_prior`` already measured what a
frequency prior is worth *in domain* -- prior-only against context-only,
blending well above both -- using counts drawn from the evaluation corpus's own
training split. That prior is CC BY-NC-SA 4.0 and unshippable. The question here
is whether the same mechanism survives having its counts come from somewhere a
caller could legally and practically get them: a schema.

**The objection that has to be answered first.** A schema-derived prior is a
*schema* prior and the measured disambiguation deficit is on *computer-science
prose*. This may be the right mechanism aimed at the wrong distribution -- the
objection that killed the analogous PMC work on aim rather than on size. So this
runner measures the aim before it measures anything else, and the vocabulary
census below is deliberately printed before the transfer table.

The mechanism is held constant, which is the whole design
---------------------------------------------------------
Every arm here runs through ``bench/run_disambiguation_diagnosis.py``'s own
``decompose`` and ``predict``. The prior scorer, the add-alpha smoothing, the
interpolation grid, the fold seed and the tie-break are that module's, imported
rather than re-implemented. **Only the source of the counts changes.** Three
arms reproduce figures already in ``bench/results.json`` -- shipped,
context-only and the in-domain train prior -- and the run prints whether they
land on them. If they do not, the harness is broken and no other number here is
worth reading; that check is this file's ``pyab3p``.

What a "schema-derived prior" is, five ways, unioned
----------------------------------------------------
A schema does not ship acronym/expansion pairs. It ships identifiers beside
captions, so a prior has to be harvested, and the harvest rule is exactly where
a null result can be manufactured by choosing badly. Five constructions run and
the reported prior is their union, because the honest question is whether *any*
construction reaches the prose vocabulary:

``token_word``
    ``bench/run_governed_catalog.align`` over all five of its harvesting modes,
    unioned per pair so no pair votes five times. Key is the identifier token
    (``qty``), value is the caption word it aligned to (``quantity``). This is
    the construction a governed catalog is actually built from, and the only one
    that emits a *single-word* value.
``identifier``
    The whole identifier as the key, the whole caption as the value. Catches an
    identifier that is itself an abbreviation of its caption.
``initialism_all``
    The initialism of every caption word as the key, the whole caption as the
    value. ``Nature of Call`` votes for ``NOC``.
``initialism_content``
    The same over content words only, so ``Nature of Call`` also votes for
    ``NC``. Recorded only where its key differs from ``initialism_all``'s, so
    nothing is double-counted.
``initialism_window``
    Every contiguous run of :data:`WINDOW_MIN_WORDS` to :data:`WINDOW_MAX_WORDS`
    caption words votes for its own initialism: ``Year To Date Gross Sales``
    votes ``YTD -> year to date`` as well as ``GS -> gross sales``. This is the
    most generous construction and it exists so that a null result is a fact
    about the two vocabularies rather than about a harvest rule chosen badly.
    Its window bounds bracket every short-form key length the prose arm has.

Keys are normalised by ``acronymkit.disambiguation._short_form_key`` -- the very
function ``ExpansionDictionary`` indexes by -- so the two contracts' key spaces
are compared in one namespace rather than through a bridge invented here. Values
are normalised by ``run_governed_catalog.phrase_words``, the case-folded
alphanumeric word tuple that is already this project's expansion-equality
metric.

What is reported with every accuracy, and why
----------------------------------------------
A prior that covers nothing degenerates into the tie-break, and a tie-break
scores well above zero. So every accuracy on this page ships with a **firing
count** and a **floor arm**:

``floor_constant``
    Every candidate scored ``0.0``; ``predict``'s ``(-score, expansion)`` sort
    decides. This is *exactly* what any prior arm degenerates to where the prior
    has no signal, so it is the number a prior arm has to beat before it has
    measured anything at all.
``instances_prior_discriminates``
    Instances where the prior assigns strictly different mass to at least two
    candidates. An accuracy delta on a subset this does not cover came from the
    tie-break and not from the prior.

Corpora, and what this run does and does not spend
---------------------------------------------------
The prior is harvested from ``socrata`` and ``sec_xbrl``, both declared
``role = "held_out"`` for ``task = "identifier_segmentation"``. **Nothing is
scored on either of them here.** They are read as a *source of counts* for a
different task, no threshold is chosen on them, and no figure about them is
produced, so their held-out role for segmentation is untouched. The evaluation
is ``sdu21_ad`` dev, which ``bench/splits.toml`` already declares
``role = "tuning"``, ``contaminated = true`` -- the blend weight is swept on it,
so every blend figure here is a tuning figure and is saved saying so.

Usage::

    python tools/fetch_data.py sdu21-ad-diction sdu21-ad-dev sdu21-ad-train
    python bench/run_governed_gold.py            # populates data/governed_gold/
    python bench/run_schema_prior.py --save
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit import disambiguation as _d  # noqa: E402
from acronymkit.config import Config  # noqa: E402
from acronymkit.disambiguation import ExpansionDictionary, LexicalDisambiguator  # noqa: E402
from acronymkit.governed import (  # noqa: E402
    EntryKind,
    ExpansionSource,
    GovernedDictionary,
    GovernedEntry,
)
from bench import corpora  # noqa: E402
from bench.corpora import DisambiguationInstance, IdentifierCaptionPair  # noqa: E402
from bench.run_disambiguation_diagnosis import (  # noqa: E402
    CONSTANT,
    LAMBDA_GRID,
    OVERLAP_ONLY,
    PRIOR_ALPHA,
    RANDOM_SEED,
    SHIPPED,
    Decomposed,
    Scored,
    decompose,
    predict,
)
from bench.run_extraction import save_results  # noqa: E402
from bench.run_governed_catalog import MODES, align, phrase_words  # noqa: E402

#: Which cache file each schema corpus is read from. Named rather than globbed,
#: for the reason ``bench/corpora.py`` refuses to choose: two Socrata snapshots
#: on one disk are two populations of a live catalog, and picking the newer one
#: silently would put the choice of corpus inside the number.
SNAPSHOTS = {
    "socrata": "socrata_80pages_v2.json",
    "sec_xbrl": "sec_xbrl_2025q1.json",
}

#: The five harvest constructions, in the order every table prints them.
CONSTRUCTIONS = (
    "token_word",
    "identifier",
    "initialism_all",
    "initialism_content",
    "initialism_window",
)

#: Function words dropped by ``initialism_content``. Small and frozen: this is a
#: second reading of a caption, not a linguistic claim, and a longer list would
#: only widen a key space that is about to be measured for overlap.
CAPTION_FUNCTION_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "is",
        "of",
        "on",
        "or",
        "per",
        "the",
        "to",
        "with",
    }
)

#: Caption word counts an initialism is harvested from. Below two there is no
#: initialism to form; above ten the key is longer than any short form in the
#: prose arm and can only add key-space noise.
INITIALISM_MIN_WORDS = 2
INITIALISM_MAX_WORDS = 10

#: Window bounds for ``initialism_window``. A window of ``n`` words produces a
#: key of ``n`` letters, so these bracket the prose arm's own key lengths --
#: which the run measures and prints rather than assuming, under
#: ``dev_short_form_key_lengths``.
WINDOW_MIN_WORDS = 2
WINDOW_MAX_WORDS = 5

#: Figures already gated in ``bench/results.json`` that three of this run's arms
#: must reproduce, because they are the same code path over the same corpus with
#: only the count source changed. ``(run id, field, arm)``.
REPRODUCES = (
    ("disambiguation.sdu21.acronymkit", "accuracy", "accuracy_shipped"),
    (
        "disambiguation.sdu21.diagnosis.frequency_prior",
        "accuracy_context_only",
        "accuracy_context_only",
    ),
    (
        "disambiguation.sdu21.diagnosis.frequency_prior",
        "accuracy_prior_only",
        "accuracy_train_prior_only",
    ),
)

#: THE PRE-REGISTERED SUCCESS RULE, written before this runner existed and not
#: adjusted after seeing output. The bet transfers iff the blend reaches
#: :data:`PREREGISTERED_TRANSFER_ACCURACY` -- five points over the shipped
#: ``41.65`` -- **and** beats an information-free control of the same shape by
#: :data:`PREREGISTERED_CONTROL_MARGIN`. Two conditions rather than one because a
#: prior that covers nothing degenerates into the tie-break, and a tie-break
#: scores well above zero. The constants are here, and not inside a paragraph, so
#: a later reader can see that the verdict is arithmetic.
PREREGISTERED_TRANSFER_ACCURACY = 46.65
PREREGISTERED_CONTROL_MARGIN = 2.00

#: Permutations of the within-record prior mass used as the null control. Twenty
#: is enough to see whether the measured gain sits inside the permutation's
#: range; it is not enough for a p-value and none is reported.
PERMUTATIONS = 20

#: How close a reproduction has to land. One hundredth of a point: every figure
#: in ``bench/results.json`` is rounded to two places, so anything looser would
#: accept a genuinely different number.
REPRODUCTION_TOLERANCE = 0.01

#: A prior is a mapping from a normalised short form to counts over expansion
#: word tuples. Deliberately not a ``GovernedDictionary``: see
#: :func:`contract_arity`, which measures why it cannot be one.
Prior = Dict[str, "collections.Counter[Tuple[str, ...]]"]


def pct(part: int, whole: int) -> float:
    """``part`` as a percentage of ``whole``, rounded, ``0.0`` on an empty whole."""
    return round(part / whole * 100, 2) if whole else 0.0


def number(mapping: Dict[str, object], key: str) -> float:
    """One numeric field out of a ``Dict[str, object]`` result, as a float.

    The result dictionaries are heterogeneous by design -- they carry corpus
    names and notes beside their measurements -- so every read of one is an
    ``object``. This is the one place that narrowing happens, so a report line
    that reads a field which is not a number fails here rather than formatting
    a repr into a table.
    """
    value = mapping[key]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{key!r} is {type(value).__name__}, not a number")
    return float(value)


# ---------------------------------------------------------------------------
# harvest
# ---------------------------------------------------------------------------
def _initialism(words: Sequence[str]) -> str:
    """The initialism of ``words``, or ``""`` when it is not worth harvesting."""
    if not INITIALISM_MIN_WORDS <= len(words) <= INITIALISM_MAX_WORDS:
        return ""
    return "".join(word[0] for word in words if word).upper()


def _windows(words: Sequence[str]) -> List[Tuple[str, Tuple[str, ...]]]:
    """Every ``(initialism, window)`` vote a caption's contiguous runs cast."""
    out: List[Tuple[str, Tuple[str, ...]]] = []
    for length in range(WINDOW_MIN_WORDS, WINDOW_MAX_WORDS + 1):
        for start in range(0, len(words) - length + 1):
            window = tuple(words[start : start + length])
            key = "".join(word[0] for word in window if word).upper()
            if key:
                out.append((key, window))
    return out


def harvest(pairs: Sequence[IdentifierCaptionPair], construction: str) -> Tuple[Prior, int, int]:
    """Build one construction's prior from one schema corpus.

    Args:
        pairs: Every row of the corpus, raw. Repetition is signal here: a column
            named ``zip_code`` on five hundred portals is a frequency fact about
            the schema world, and a distinct-pair count is saved beside every
            figure so a reader can see how much of the mass that is.
        construction: One of :data:`CONSTRUCTIONS`.

    Returns:
        ``(prior, rows_that_voted, votes_cast)``.

    Raises:
        ValueError: If ``construction`` is not one of :data:`CONSTRUCTIONS`.
    """
    if construction not in CONSTRUCTIONS:
        raise ValueError(f"unknown construction {construction!r}; known: {CONSTRUCTIONS}")

    prior: Prior = collections.defaultdict(collections.Counter)
    voted = 0
    votes = 0
    for pair in pairs:
        cast: List[Tuple[str, Tuple[str, ...]]] = []
        words = phrase_words(pair.caption)
        if construction == "token_word":
            aligned: Set[Tuple[str, str]] = set()
            for mode in MODES:
                aligned.update(align(pair.identifier, pair.caption, mode) or ())
            cast = [(_d._short_form_key(token), (word,)) for token, word in sorted(aligned)]
        elif construction == "identifier":
            key = _d._short_form_key(pair.identifier)
            if key and words:
                cast = [(key, words)]
        elif construction == "initialism_all":
            key = _initialism(words)
            if key:
                cast = [(key, words)]
        elif construction == "initialism_content":
            content = [word for word in words if word not in CAPTION_FUNCTION_WORDS]
            key = _initialism(content)
            if key and key != _initialism(words):
                cast = [(key, words)]
        else:
            cast = _windows(words)

        cast = [(key, value) for key, value in cast if key and value]
        if not cast:
            continue
        voted += 1
        for key, value in cast:
            prior[key][value] += 1
            votes += 1
    return dict(prior), voted, votes


def merge(priors: Sequence[Prior]) -> Prior:
    """Sum several priors into one. Counter addition, key by key."""
    out: Prior = collections.defaultdict(collections.Counter)
    for prior in priors:
        for key, counts in prior.items():
            out[key].update(counts)
    return dict(out)


# ---------------------------------------------------------------------------
# the vocabulary census -- the cheaper explanation, established first
# ---------------------------------------------------------------------------
def candidate_words(diction: Dict[str, List[str]]) -> Dict[str, Tuple[str, ...]]:
    """Every candidate expansion's normalised word tuple, computed once."""
    return {
        expansion: phrase_words(expansion)
        for expansions in diction.values()
        for expansion in expansions
    }


def saturation(prior: Prior) -> Dict[str, object]:
    """How much of the short alphabetic key space the prior simply covers.

    ``short_forms_in_prior_pct`` is the number a reader will want to call
    coverage, and it is only coverage if having the key is informative. With a
    large harvested key set the two- and three-letter spaces are small enough to
    saturate, and a key space that is saturated tells a caller nothing by
    containing their short form -- it would contain any short form. This is the
    control on that reading, and it is arithmetic over the key set rather than
    anything measured on the prose arm.

    Args:
        prior: The harvested prior.

    Returns:
        Covered share of ``A-Z`` strings at each length a short form usually is.
    """
    out: Dict[str, object] = {}
    letters = [chr(code) for code in range(ord("A"), ord("Z") + 1)]
    space: List[str] = [""]
    for length in (1, 2, 3):
        space = [prefix + letter for prefix in space for letter in letters]
        covered = sum(1 for key in space if key in prior)
        out[f"letter_space_{length}_size"] = len(space)
        out[f"letter_space_{length}_covered"] = covered
        out[f"letter_space_{length}_covered_pct"] = pct(covered, len(space))
    return out


def census(
    instances: Sequence[DisambiguationInstance],
    diction: Dict[str, List[str]],
    prior: Prior,
    words_of: Dict[str, Tuple[str, ...]],
) -> Dict[str, object]:
    """How much of the prose arm a schema prior can reach at all.

    Three levels, and the distance between them is the finding either way. A key
    that is present but whose values match no candidate cannot rank anything; a
    key whose values match exactly one candidate ranks it above the rest only
    because the rest are absent, which is still signal; a key that separates two
    candidates by mass is the only case a *frequency* prior is doing work in.

    A fourth figure sits beside them and answers a different question:
    ``candidates_present_as_any_schema_value`` counts prose candidate expansions
    that occur as a harvested value under *any* key at all. That separates "the
    key space does not line up" from "the schema does not contain these phrases",
    which are two different findings with the same accuracy.

    Args:
        instances: The dev split.
        diction: The candidate sets.
        prior: The harvested prior.
        words_of: Normalised word tuple per candidate expansion, from
            :func:`candidate_words`.

    Returns:
        Counts and percentages at short-form level, at dev short-form level and
        at instance level.
    """
    short_forms = {_d._short_form_key(acronym): acronym for acronym in diction}
    dev_keys = {_d._short_form_key(instance.acronym) for instance in instances}

    present: Set[str] = set()
    matched: Set[str] = set()
    separating: Set[str] = set()
    two_nonzero: Set[str] = set()
    for key, acronym in short_forms.items():
        counts = prior.get(key)
        if counts is None:
            continue
        present.add(key)
        masses = [counts.get(words_of[expansion], 0) for expansion in diction[acronym]]
        if any(masses):
            matched.add(key)
        if masses and max(masses) > min(masses):
            separating.add(key)
        # The literal reading of "two candidates carrying distinct non-zero
        # mass". Strictly narrower than ``separating``, which a single non-zero
        # candidate already satisfies, and reported beside it because the two
        # answer different questions: this one is whether the schema has an
        # OPINION about which of two known expansions is commoner, and
        # ``separating`` is whether the ranking can move at all.
        non_zero = [mass for mass in masses if mass]
        if len(non_zero) >= 2 and len(set(non_zero)) >= 2:
            two_nonzero.add(key)

    any_value: Set[Tuple[str, ...]] = set()
    for counts in prior.values():
        any_value.update(counts)
    distinct_candidates = {words_of[e] for expansions in diction.values() for e in expansions}
    anywhere = sum(1 for value in distinct_candidates if value in any_value)

    total = len(instances)
    in_present = sum(1 for i in instances if _d._short_form_key(i.acronym) in present)
    in_matched = sum(1 for i in instances if _d._short_form_key(i.acronym) in matched)
    in_separating = sum(1 for i in instances if _d._short_form_key(i.acronym) in separating)
    in_two_nonzero = sum(1 for i in instances if _d._short_form_key(i.acronym) in two_nonzero)

    return {
        "prior_keys": len(prior),
        "prior_distinct_values": sum(len(counts) for counts in prior.values()),
        "diction_short_forms": len(short_forms),
        "dev_distinct_short_forms": len(dev_keys),
        "instances": total,
        "short_forms_in_prior": len(present),
        "short_forms_in_prior_pct": pct(len(present), len(short_forms)),
        "short_forms_with_matched_candidate": len(matched),
        "short_forms_with_matched_candidate_pct": pct(len(matched), len(short_forms)),
        "dev_short_forms_in_prior": len(present & dev_keys),
        "dev_short_forms_in_prior_pct": pct(len(present & dev_keys), len(dev_keys)),
        "dev_short_forms_with_matched_candidate": len(matched & dev_keys),
        "dev_short_forms_with_matched_candidate_pct": pct(len(matched & dev_keys), len(dev_keys)),
        # The collision rate. A key that is present but carries no expansion the
        # prose arm ever offers is not partial coverage: it is the schema using
        # the same letters for something else, and it is the number this whole
        # census exists to produce.
        "short_forms_in_prior_with_no_matched_candidate": len(present) - len(matched),
        "short_forms_in_prior_with_no_matched_candidate_pct": pct(
            len(present) - len(matched), len(present)
        ),
        "short_forms_where_prior_separates": len(separating),
        "short_forms_where_prior_separates_pct": pct(len(separating), len(short_forms)),
        "distinct_candidate_expansions": len(distinct_candidates),
        "candidates_present_as_any_schema_value": anywhere,
        "candidates_present_as_any_schema_value_pct": pct(anywhere, len(distinct_candidates)),
        "instances_with_prior_key": in_present,
        "instances_with_prior_key_pct": pct(in_present, total),
        "instances_with_matched_candidate": in_matched,
        "instances_with_matched_candidate_pct": pct(in_matched, total),
        "instances_where_prior_separates": in_separating,
        "instances_where_prior_separates_pct": pct(in_separating, total),
        "short_forms_with_two_distinct_nonzero_candidates": len(two_nonzero),
        "instances_with_two_distinct_nonzero_candidates": in_two_nonzero,
        "instances_with_two_distinct_nonzero_candidates_pct": pct(in_two_nonzero, total),
    }


# ---------------------------------------------------------------------------
# the two contracts, measured rather than argued
# ---------------------------------------------------------------------------
def contract_arity(
    diction: Dict[str, List[str]], prior: Prior, words_of: Dict[str, Tuple[str, ...]]
) -> Dict[str, object]:
    """What the two contracts disagree about before any distribution question.

    ``ExpansionDictionary`` maps a short form to a *sequence* of candidates and
    exists to be selected from. ``GovernedDictionary.lookup`` returns at most one
    :class:`~acronymkit.governed.GovernedEntry` per token, because a governed
    catalog is unambiguous *by definition* -- that is what governing a
    vocabulary means. The frequency information a prior would need is therefore
    not in the governed contract at all; it lives in the vote counters a catalog
    build discards. This function measures that rather than asserting it: it
    builds a ``GovernedDictionary`` from the harvested prior and counts what
    survives.

    Args:
        diction: The prose arm's candidate sets.
        prior: The harvested schema prior.
        words_of: Normalised word tuple per candidate expansion.

    Returns:
        Arity on both sides, and the round-trip loss through the governed
        contract.
    """
    ambiguous_keys = sum(1 for counts in prior.values() if len(counts) > 1)
    entries = [
        GovernedEntry(
            token=key,
            canonical=" ".join(counts.most_common(1)[0][0]).title(),
            kind=EntryKind.APPROVED_ABBREV,
            entry_id=f"SCHEMA-{key}",
            source=ExpansionSource.GOVERNED,
        )
        for key, counts in sorted(prior.items())
        if counts
    ]
    governed = GovernedDictionary(entries)
    survives = sum(1 for entry in entries if governed.lookup(entry.token) is not None)

    prose_multi = sum(1 for expansions in diction.values() if len(expansions) > 1)
    prose_candidates = sum(len(expansions) for expansions in diction.values())
    prose_single_word = sum(
        1 for expansions in diction.values() for e in expansions if len(words_of[e]) == 1
    )
    schema_single_word = sum(1 for counts in prior.values() for value in counts if len(value) == 1)
    schema_values = sum(len(counts) for counts in prior.values())

    return {
        "expansion_dictionary_short_forms": len(diction),
        "expansion_dictionary_candidates": prose_candidates,
        "expansion_dictionary_short_forms_with_two_or_more": prose_multi,
        "expansion_dictionary_mean_candidates": (
            round(prose_candidates / len(diction), 2) if diction else 0.0
        ),
        "expansion_dictionary_single_word_candidates": prose_single_word,
        "expansion_dictionary_single_word_candidates_pct": pct(prose_single_word, prose_candidates),
        "governed_dictionary_rows_built": len(entries),
        "governed_dictionary_rows_resolvable": survives,
        "governed_dictionary_expansions_per_token": 1,
        "schema_prior_keys": len(prior),
        "schema_prior_keys_with_two_or_more_values": ambiguous_keys,
        "schema_prior_keys_with_two_or_more_values_pct": pct(ambiguous_keys, len(prior)),
        "schema_prior_values_lost_to_the_governed_contract": schema_values - len(entries),
        "schema_prior_single_word_values": schema_single_word,
        "schema_prior_single_word_values_pct": pct(schema_single_word, schema_values),
    }


# ---------------------------------------------------------------------------
# the transfer measurement
# ---------------------------------------------------------------------------
def masses(
    records: Sequence[Decomposed], prior: Prior, words_of: Dict[str, Tuple[str, ...]]
) -> Tuple[List[Dict[str, float]], int, int]:
    """Smoothed prior mass per candidate, one mapping per record.

    Add-alpha with :data:`~bench.run_disambiguation_diagnosis.PRIOR_ALPHA`, which
    is the in-domain measurement's own smoothing, so an expansion the schema
    never saw is improbable rather than impossible and the two priors are
    directly comparable.

    Returns:
        ``(masses, key_lookups, value_lookups)``. The two counts are R17 work
        counts: a prior arm that got a number by doing no lookups is a null
        result wearing an accuracy.
    """
    out: List[Dict[str, float]] = []
    key_lookups = 0
    value_lookups = 0
    empty: collections.Counter[Tuple[str, ...]] = collections.Counter()
    for record in records:
        key_lookups += 1
        counts = prior.get(record.acronym_key) or empty
        raw = {}
        for candidate in record.candidates:
            value_lookups += 1
            raw[candidate.expansion] = float(counts.get(words_of[candidate.expansion], 0))
        mass = sum(value + PRIOR_ALPHA for value in raw.values())
        out.append({key: (value + PRIOR_ALPHA) / mass for key, value in raw.items()})
    return out, key_lookups, value_lookups


def raw_hits(
    records: Sequence[Decomposed], prior: Prior, words_of: Dict[str, Tuple[str, ...]]
) -> List[List[int]]:
    """Unsmoothed prior counts per candidate. Firing is decided on these."""
    out: List[List[int]] = []
    empty: collections.Counter[Tuple[str, ...]] = collections.Counter()
    for record in records:
        counts = prior.get(record.acronym_key) or empty
        out.append([counts.get(words_of[c.expansion], 0) for c in record.candidates])
    return out


def _scorer(prior_of_record: Dict[str, float]) -> Callable[[Scored], float]:
    """Bind one record's prior by closure, as the in-domain measurement does."""
    return lambda candidate: prior_of_record[candidate.expansion]


def _blend(weight: float, prior_of_record: Dict[str, float]) -> Callable[[Scored], float]:
    """The in-domain measurement's interpolation: ``weight`` is on *context*."""
    return lambda c: (1 - weight) * prior_of_record[c.expansion] + weight * c.overlap


def _predictions(records: Sequence[Decomposed], priors: Sequence[Dict[str, float]]) -> List[str]:
    """Prior-only prediction per record."""
    return [predict(record, _scorer(prior), inline="off") for record, prior in zip(records, priors)]


def permutation_control(
    records: Sequence[Decomposed],
    schema: Sequence[Dict[str, float]],
    weight: float,
) -> Dict[str, object]:
    """What the same prior is worth once it stops pointing at particular candidates.

    The mass vector of every record is permuted *within that record* under a
    frozen seed. Firing rate, mass distribution, candidate count and smoothing
    are all identical to the measured arm; the only thing destroyed is which
    candidate each mass belongs to. A gain the permutation reproduces is a
    property of the shape of the numbers -- an unequal vector pulls the sort off
    the alphabetical tie-break whatever it favours -- and not knowledge the
    schema had. This is the control that decides whether a small gain is a
    finding.

    Args:
        records: The decomposed dev split.
        schema: Smoothed schema-prior mass per candidate.
        weight: The context weight the measured blend was read at, so the
            control is taken at the same operating point.

    Returns:
        Mean, minimum and maximum accuracy over :data:`PERMUTATIONS` draws, for
        the prior-only arm and for the blend.
    """
    generator = random.Random(RANDOM_SEED)
    gold = [record.gold for record in records]
    prior_runs: List[float] = []
    blend_runs: List[float] = []
    for _ in range(PERMUTATIONS):
        shuffled: List[Dict[str, float]] = []
        for record, prior in zip(records, schema):
            values = [prior[c.expansion] for c in record.candidates]
            generator.shuffle(values)
            shuffled.append(
                {
                    candidate.expansion: values[index]
                    for index, candidate in enumerate(record.candidates)
                }
            )
        prior_hits = 0
        blend_hits = 0
        for index, record in enumerate(records):
            prior_hits += predict(record, _scorer(shuffled[index]), inline="off") == gold[index]
            blend_hits += (
                predict(record, _blend(weight, shuffled[index]), inline="off") == gold[index]
            )
        prior_runs.append(pct(prior_hits, len(records)))
        blend_runs.append(pct(blend_hits, len(records)))
    return {
        "permutations": PERMUTATIONS,
        "permutation_seed": RANDOM_SEED,
        "permutation_blend_weight_on_context": round(weight, 2),
        "accuracy_permuted_prior_only_mean": round(sum(prior_runs) / len(prior_runs), 2),
        "accuracy_permuted_prior_only_min": min(prior_runs),
        "accuracy_permuted_prior_only_max": max(prior_runs),
        "accuracy_permuted_blend_mean": round(sum(blend_runs) / len(blend_runs), 2),
        "accuracy_permuted_blend_min": min(blend_runs),
        "accuracy_permuted_blend_max": max(blend_runs),
    }


def transfer(
    records: Sequence[Decomposed],
    schema: Sequence[Dict[str, float]],
    fires: Sequence[List[int]],
    train_counts: collections.Counter[str],
) -> Dict[str, object]:
    """Score the schema prior against the floor, the context and the in-domain prior.

    Args:
        records: The decomposed dev split.
        schema: Smoothed schema-prior mass per candidate, from :func:`masses`.
        fires: Unsmoothed schema counts per candidate, from :func:`raw_hits`.
        train_counts: Gold-expansion counts from ``train.json``, the positive
            control. Same mechanism, in-domain source.

    Returns:
        Every arm's accuracy, the blend sweep and its out-of-fold reading, and
        the firing counts without which none of it is readable.
    """
    total = len(records)
    gold = [record.gold for record in records]

    in_domain: List[Dict[str, float]] = []
    for record in records:
        raw = {c.expansion: float(train_counts.get(c.expansion, 0)) for c in record.candidates}
        mass = sum(value + PRIOR_ALPHA for value in raw.values())
        in_domain.append({key: (value + PRIOR_ALPHA) / mass for key, value in raw.items()})

    floor = [predict(record, CONSTANT, inline="off") for record in records]
    context = [predict(record, OVERLAP_ONLY, inline="off") for record in records]
    shipped = [predict(record, SHIPPED, inline="shipped") for record in records]
    schema_only = _predictions(records, schema)
    train_only = _predictions(records, in_domain)

    def hits(predicted: Sequence[str], members: Optional[Sequence[int]] = None) -> int:
        """Correct predictions over ``members``, or over everything."""
        chosen: Sequence[int] = range(total) if members is None else members
        return sum(1 for index in chosen if predicted[index] == gold[index])

    fired = [
        index for index in range(total) if fires[index] and max(fires[index]) > min(fires[index])
    ]
    matched = [index for index in range(total) if any(fires[index])]
    moved = [index for index in range(total) if schema_only[index] != floor[index]]

    # CONCENTRATION. A gain measured on a subset is a gain measured on however
    # many distinct short forms that subset happens to contain, and a large
    # per-instance delta carried by one short form is an anecdote with a
    # denominator rather than a capability. So the largest contributor is named
    # by size and the subset is re-scored without it.
    by_short_form: collections.Counter[str] = collections.Counter(
        records[index].acronym_key for index in fired
    )
    largest = by_short_form.most_common(1)[0] if by_short_form else ("", 0)
    without_largest = [index for index in fired if records[index].acronym_key != largest[0]]
    largest_members = [index for index in fired if records[index].acronym_key == largest[0]]

    sweep: Dict[str, float] = {}
    blend_evaluations = 0
    for weight in LAMBDA_GRID:
        correct = 0
        for index, record in enumerate(records):
            blend_evaluations += 1
            correct += predict(record, _blend(weight, schema[index]), inline="off") == gold[index]
        sweep[f"{weight:.2f}"] = pct(correct, total)
    best_weight = max(LAMBDA_GRID, key=lambda w: sweep[f"{w:.2f}"])

    generator = random.Random(RANDOM_SEED)
    order = list(range(total))
    generator.shuffle(order)
    folds = (order[0::2], order[1::2])

    def fold_hits(members: Sequence[int], weight: float) -> int:
        """Correct predictions over ``members`` at interpolation ``weight``."""
        return sum(
            1
            for index in members
            if predict(records[index], _blend(weight, schema[index]), inline="off") == gold[index]
        )

    held_hits = held_total = 0
    chosen: List[float] = []
    for index in range(2):
        tune, test = folds[index], folds[1 - index]
        weight = max(LAMBDA_GRID, key=lambda w: fold_hits(tune, w))
        chosen.append(round(weight, 2))
        held_hits += fold_hits(test, weight)
        held_total += len(test)

    # Where the blend's gain comes from, because a pooled sweep cannot say.
    # On an instance the prior does not separate, every candidate carries the
    # same smoothed mass ``alpha / (k * alpha)``, so the prior term is a
    # constant added to every candidate and CANNOT change the ranking. The
    # blend therefore differs from context-only only inside ``fired``, and the
    # whole of any gain is that subset's. That is a derivation, so it is
    # checked rather than asserted: ``blend_disagreements_outside_fired`` is
    # zero or this reasoning is wrong.
    blended = [
        predict(record, _blend(best_weight, schema[index]), inline="off")
        for index, record in enumerate(records)
    ]
    fired_set = set(fired)
    disagreements = [index for index in range(total) if blended[index] != context[index]]
    outside = [index for index in disagreements if index not in fired_set]

    return {
        "instances": total,
        "distinct_short_forms": len({record.acronym_key for record in records}),
        "candidates_considered": sum(len(record.candidates) for record in records),
        "blend_scorer_evaluations": blend_evaluations,
        "accuracy_floor_constant": pct(hits(floor), total),
        "accuracy_context_only": pct(hits(context), total),
        "accuracy_shipped": pct(hits(shipped), total),
        "accuracy_schema_prior_only": pct(hits(schema_only), total),
        "accuracy_train_prior_only": pct(hits(train_only), total),
        "schema_prior_minus_floor_points": round(
            pct(hits(schema_only), total) - pct(hits(floor), total), 2
        ),
        "schema_prior_minus_context_points": round(
            pct(hits(schema_only), total) - pct(hits(context), total), 2
        ),
        "instances_with_matched_candidate": len(matched),
        "instances_with_matched_candidate_pct": pct(len(matched), total),
        "instances_prior_discriminates": len(fired),
        "instances_prior_discriminates_pct": pct(len(fired), total),
        "instances_prediction_moved_off_floor": len(moved),
        "instances_prediction_moved_off_floor_pct": pct(len(moved), total),
        "fired_subset_schema_prior_accuracy": pct(hits(schema_only, fired), len(fired)),
        "fired_subset_floor_accuracy": pct(hits(floor, fired), len(fired)),
        "fired_subset_context_accuracy": pct(hits(context, fired), len(fired)),
        "fired_subset_train_prior_accuracy": pct(hits(train_only, fired), len(fired)),
        "moved_subset_schema_prior_accuracy": pct(hits(schema_only, moved), len(moved)),
        "moved_subset_floor_accuracy": pct(hits(floor, moved), len(moved)),
        "blend_sweep": sweep,
        "blend_best_weight_on_context_tuning_split": round(best_weight, 2),
        "blend_best_accuracy_tuning_split": sweep[f"{best_weight:.2f}"],
        "blend_weight_chosen_per_fold": chosen,
        "blend_accuracy_out_of_fold": pct(held_hits, held_total),
        "blend_prior_dominant_accuracy": sweep["0.10"],
        "blend_instances_disagreeing_with_context": len(disagreements),
        "blend_instances_disagreeing_with_context_pct": pct(len(disagreements), total),
        "blend_disagreements_outside_fired": len(outside),
        "blend_minus_context_points": round(
            sweep[f"{best_weight:.2f}"] - pct(hits(context), total), 2
        ),
        "blend_net_instances_gained_over_context": hits(blended) - hits(context),
        # A net figure with no halves is unreadable: +44 from 44 wins and no
        # losses is a different object from +44 from 107 wins and 63 losses.
        "blend_instances_won_from_context": sum(
            1
            for index in disagreements
            if blended[index] == gold[index] and context[index] != gold[index]
        ),
        "blend_instances_lost_to_context": sum(
            1
            for index in disagreements
            if context[index] == gold[index] and blended[index] != gold[index]
        ),
        "fired_subset_largest_short_form": largest[0],
        "fired_subset_blend_accuracy": pct(hits(blended, fired), len(fired)),
        "fired_subset_instances": len(fired),
        "fired_subset_distinct_short_forms": len(by_short_form),
        "fired_subset_largest_short_form_instances": largest[1],
        "fired_subset_largest_short_form_instances_pct": pct(largest[1], len(fired)),
        "fired_subset_largest_short_form_share_of_correct_pct": pct(
            hits(schema_only, largest_members), max(hits(schema_only, fired), 1)
        ),
        "fired_subset_schema_prior_accuracy_excluding_largest": pct(
            hits(schema_only, without_largest), len(without_largest)
        ),
        "fired_subset_floor_accuracy_excluding_largest": pct(
            hits(floor, without_largest), len(without_largest)
        ),
        "fired_subset_context_accuracy_excluding_largest": pct(
            hits(context, without_largest), len(without_largest)
        ),
        "fired_subset_instances_excluding_largest": len(without_largest),
        "prior_alpha": PRIOR_ALPHA,
    }


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def reproductions(measured: Dict[str, object]) -> List[Tuple[str, float, float, bool]]:
    """Check the three arms that must land on figures already in ``results.json``.

    Args:
        measured: This run's :func:`transfer` result.

    Returns:
        ``(label, want, got, ok)`` per pinned figure. Empty when the results
        file is missing, which a checkout never is.
    """
    path = REPO_ROOT / "bench" / "results.json"
    if not path.is_file():  # pragma: no cover - a checkout always has one
        return []
    runs = json.loads(path.read_text(encoding="utf-8")).get("runs", {})
    out: List[Tuple[str, float, float, bool]] = []
    for run_id, field, arm in REPRODUCES:
        entry = runs.get(run_id)
        if not isinstance(entry, dict) or field not in entry:
            out.append((f"{run_id}.{field}", float("nan"), number(measured, arm), False))
            continue
        want = float(entry[field])
        got = number(measured, arm)
        out.append((f"{run_id}.{field}", want, got, abs(want - got) < REPRODUCTION_TOLERANCE))
    return out


def _census_line(label: str, row: Dict[str, object]) -> str:
    """One row of the vocabulary-overlap table."""
    return (
        f"{label:<22}{row['prior_keys']:>10,}"
        f"{row['dev_short_forms_in_prior']:>8,} {row['dev_short_forms_in_prior_pct']:>6.2f}%"
        f"{row['dev_short_forms_with_matched_candidate']:>7,}"
        f"{row['instances_with_matched_candidate']:>10,}"
        f" {row['instances_with_matched_candidate_pct']:>6.2f}%"
        f"{row['instances_where_prior_separates']:>8,}"
        f" {row['instances_where_prior_separates_pct']:>6.2f}%"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="schema-derived prior on the prose arm")
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument("--limit", type=int, default=0, help="smoke-test on the first N instances")
    args = parser.parse_args(argv)
    if args.limit and args.save:
        raise SystemExit("--limit produces a partial number; refusing to --save it")

    cache = REPO_ROOT / "data" / "governed_gold"
    schema_corpora = {
        name: corpora.read_governed_gold(name, path=cache / filename)
        for name, filename in sorted(SNAPSHOTS.items())
    }

    per_source: Dict[str, Dict[str, Prior]] = {}
    harvest_facts: Dict[str, object] = {}
    for name, corpus in schema_corpora.items():
        per_source[name] = {}
        distinct = len({(p.identifier, p.caption) for p in corpus.pairs})
        harvest_facts[f"{name}_rows"] = len(corpus.pairs)
        harvest_facts[f"{name}_distinct_pairs"] = distinct
        harvest_facts[f"{name}_snapshot"] = corpus.source
        harvest_facts[f"{name}_fetched_on"] = corpus.fetched_on
        for construction in CONSTRUCTIONS:
            prior, voted, votes = harvest(corpus.pairs, construction)
            per_source[name][construction] = prior
            harvest_facts[f"{name}.{construction}.rows_that_voted"] = voted
            harvest_facts[f"{name}.{construction}.votes_cast"] = votes
            harvest_facts[f"{name}.{construction}.keys"] = len(prior)

    union = merge([prior for source in per_source.values() for prior in source.values()])
    harvest_facts["union_votes_cast"] = sum(
        int(number(harvest_facts, key))
        for key in list(harvest_facts)
        if key.endswith(".votes_cast")
    )

    diction = corpora.read_sdu21_ad_diction()
    instances = corpora.read_sdu21_ad(split="dev")
    train = corpora.read_sdu21_ad(split="train")
    if args.limit:
        instances = instances[: args.limit]
    words_of = candidate_words(diction)
    key_lengths = collections.Counter(
        len(_d._short_form_key(instance.acronym)) for instance in instances
    )
    harvest_facts["dev_short_form_key_lengths"] = {
        str(length): count for length, count in sorted(key_lengths.items())
    }
    harvest_facts["window_min_words"] = WINDOW_MIN_WORDS
    harvest_facts["window_max_words"] = WINDOW_MAX_WORDS

    print("SCHEMA CORPORA (prior source; nothing is scored on them here)")
    for name, corpus in schema_corpora.items():
        print(
            f"  {name:<10} {len(corpus.pairs):>8,} rows  "
            f"{harvest_facts[f'{name}_distinct_pairs']:>8,} distinct pairs  "
            f"{corpus.source} fetched {corpus.fetched_on}"
        )
    print(f"  union prior: {len(union):,} keys from {harvest_facts['union_votes_cast']:,} votes")

    print("\nVOCABULARY OVERLAP -- the cheaper explanation, established first")
    print(
        f"{'construction':<22}{'keys':>10}{'dev sf present':>16}"
        f"{'matched':>7}{'inst matched':>18}{'inst separated':>16}"
    )
    census_rows: Dict[str, Dict[str, object]] = {}
    for construction in CONSTRUCTIONS:
        prior = merge([per_source[name][construction] for name in per_source])
        row = census(instances, diction, prior, words_of)
        census_rows[construction] = row
        print(_census_line(construction, row))
    for name in per_source:
        prior = merge(list(per_source[name].values()))
        row = census(instances, diction, prior, words_of)
        census_rows[f"source.{name}"] = row
        print(_census_line("[source] " + name, row))
    overall = census(instances, diction, union, words_of)
    census_rows["union"] = overall
    print(_census_line("UNION -- all five", overall))
    print(
        "'dev sf' is the distinct short forms the dev split actually uses; 'matched' means at\n"
        "least one candidate expansion of that short form appears in the prior; 'separated'\n"
        "means the prior gives two candidates different mass, which is the only case a\n"
        "FREQUENCY prior is doing work in."
    )
    print(
        f"COLLISION: {overall['short_forms_in_prior_with_no_matched_candidate']:,} of the "
        f"{overall['short_forms_in_prior']:,} short forms the union prior has a key for "
        f"({overall['short_forms_in_prior_with_no_matched_candidate_pct']}%) carry no expansion\n"
        "the prose arm ever offers. Those keys are not partial coverage. They are the schema\n"
        "spelling something else with the same letters, and a prior built on them would be a\n"
        "source of confident wrong answers rather than a source of weak right ones."
    )
    print(
        f"PHRASE PRESENCE: {overall['candidates_present_as_any_schema_value']:,} of the "
        f"{overall['distinct_candidate_expansions']:,} distinct candidate expansions "
        f"({overall['candidates_present_as_any_schema_value_pct']}%) occur as a harvested value\n"
        "under ANY key. This separates 'the key spaces do not line up' from 'the schema does\n"
        "not contain these phrases at all', which are two findings with the same accuracy."
    )
    print(
        f"AN OPINION: on {overall['instances_with_two_distinct_nonzero_candidates']:,} instances "
        f"({overall['instances_with_two_distinct_nonzero_candidates_pct']}%) the prior has "
        "non-zero counts for two DIFFERENT candidates and\nthose counts differ -- the only case "
        "where the schema is expressing a preference between\ntwo expansions it has both seen, "
        "rather than ranking one thing it knows above things it does not."
    )

    space = saturation(union)
    print(
        f"SATURATION: the union prior holds "
        f"{space['letter_space_2_covered']:,} of the {space['letter_space_2_size']:,} two-letter "
        f"A-Z strings ({space['letter_space_2_covered_pct']}%) and "
        f"{space['letter_space_3_covered']:,} of the {space['letter_space_3_size']:,} "
        f"three-letter ones ({space['letter_space_3_covered_pct']}%).\n"
        "Read the key-coverage column against that: a key space this dense contains a caller's\n"
        "short form whatever it is, so having the key is not evidence of anything."
    )

    arity = contract_arity(diction, union, words_of)
    print("\nTHE TWO CONTRACTS")
    print(
        f"  ExpansionDictionary : {arity['expansion_dictionary_short_forms']:,} short forms, "
        f"{arity['expansion_dictionary_mean_candidates']} candidates each on average, "
        f"{arity['expansion_dictionary_short_forms_with_two_or_more']:,} with two or more"
    )
    print(
        f"  GovernedDictionary  : {arity['governed_dictionary_rows_built']:,} rows built from the "
        f"union prior, {arity['governed_dictionary_expansions_per_token']} expansion per token by "
        f"construction, {arity['schema_prior_values_lost_to_the_governed_contract']:,} harvested "
        "values discarded to fit"
    )
    print(
        f"  single-word values  : schema {arity['schema_prior_single_word_values_pct']:.2f}% vs "
        f"prose candidates {arity['expansion_dictionary_single_word_candidates_pct']:.2f}%"
    )

    config = Config()
    engine = LexicalDisambiguator(config, ExpansionDictionary(diction))
    records = decompose(instances, diction, engine, config)
    schema_masses, key_lookups, value_lookups = masses(records, union, words_of)
    fires = raw_hits(records, union, words_of)
    train_counts: collections.Counter[str] = collections.Counter(i.expansion for i in train)
    result = transfer(records, schema_masses, fires, train_counts)
    control = permutation_control(
        records,
        schema_masses,
        number(result, "blend_best_weight_on_context_tuning_split"),
    )
    result.update(control)
    result["prior_key_lookups"] = key_lookups
    result["prior_value_lookups"] = value_lookups
    result["train_instances_counted"] = len(train)

    print("\nTRANSFER -- one mechanism, five count sources")
    print(f"{'arm':<34}{'accuracy %':>12}   note")
    print("-" * 66)
    for label, key, note in (
        ("floor_constant (tie-break only)", "accuracy_floor_constant", "the number to beat"),
        ("schema_prior_only", "accuracy_schema_prior_only", "THE ARM UNDER TEST"),
        ("context_only (no prior)", "accuracy_context_only", "pinned reproduction"),
        ("shipped Config()", "accuracy_shipped", "pinned reproduction"),
        ("train_prior_only (in-domain)", "accuracy_train_prior_only", "pinned reproduction"),
    ):
        print(f"{label:<34}{number(result, key):>12.2f}   {note}")
    print("-" * 66)
    print(
        f"work: {result['instances']:,} instances, "
        f"{result['distinct_short_forms']:,} distinct short forms, "
        f"{result['candidates_considered']:,} candidates, "
        f"{key_lookups:,} prior key lookups, {value_lookups:,} value lookups, "
        f"{result['blend_scorer_evaluations']:,} blend evaluations."
    )
    print(
        f"firing: the schema prior gives two candidates different mass on "
        f"{result['instances_prior_discriminates']:,} of {result['instances']:,} instances "
        f"({result['instances_prior_discriminates_pct']}%), and moves the prediction off the\n"
        f"tie-break on {result['instances_prediction_moved_off_floor']:,} "
        f"({result['instances_prediction_moved_off_floor_pct']}%). An accuracy delta outside "
        "that subset did not come from the prior."
    )
    if result["fired_subset_instances"]:
        print(
            f"\nON THE {result['fired_subset_instances']:,} INSTANCES THE PRIOR SEPARATES -- the "
            "only subset where any of this is live"
        )
        for label, key in (
            ("floor_constant", "fired_subset_floor_accuracy"),
            ("schema_prior_only", "fired_subset_schema_prior_accuracy"),
            ("context_only", "fired_subset_context_accuracy"),
            ("blend at the swept weight", "fired_subset_blend_accuracy"),
            ("train_prior_only (in-domain)", "fired_subset_train_prior_accuracy"),
        ):
            print(f"  {label:<32}{number(result, key):>8.2f}%")
        print(
            f"  ...spread over {result['fired_subset_distinct_short_forms']} distinct short forms, "
            f"of which the largest alone is {result['fired_subset_largest_short_form_instances']} "
            f"instances ({result['fired_subset_largest_short_form_instances_pct']}% of the subset)\n"
            f"  and {result['fired_subset_largest_short_form_share_of_correct_pct']}% of the "
            "subset's correct answers. Drop that one short form and the same three arms read\n"
            f"  {result['fired_subset_floor_accuracy_excluding_largest']}% floor, "
            f"{result['fired_subset_schema_prior_accuracy_excluding_largest']}% prior, "
            f"{result['fired_subset_context_accuracy_excluding_largest']}% context over "
            f"{result['fired_subset_instances_excluding_largest']} instances."
        )

    print(
        f"\nblend (weight on context; 0.00 is prior-only): best "
        f"{result['blend_best_weight_on_context_tuning_split']} at "
        f"{result['blend_best_accuracy_tuning_split']}% on the tuning split, "
        f"{result['blend_accuracy_out_of_fold']}% out of fold, "
        f"{result['blend_minus_context_points']:+} points against context alone."
    )
    print(
        f"  prior-dominant (0.10 on context) reads {result['blend_prior_dominant_accuracy']}%. "
        f"It disagrees with context-only on {result['blend_instances_disagreeing_with_context']:,}"
        f" instances, {result['blend_disagreements_outside_fired']} of them outside the\n"
        "  separated subset (which must be zero: an unseparated prior is a constant added to "
        "every\n  candidate and cannot re-rank). Net instances gained over context: "
        f"{result['blend_net_instances_gained_over_context']:+} "
        f"({result['blend_instances_won_from_context']} won, "
        f"{result['blend_instances_lost_to_context']} lost)."
    )
    print(
        f"\nPERMUTATION CONTROL -- the same mass vectors, shuffled within each record, "
        f"{result['permutations']} draws"
    )
    print(
        f"  prior-only      measured {number(result, 'accuracy_schema_prior_only'):.2f}%  vs "
        f"permuted mean {number(result, 'accuracy_permuted_prior_only_mean'):.2f}%  "
        f"(range {number(result, 'accuracy_permuted_prior_only_min'):.2f}-"
        f"{number(result, 'accuracy_permuted_prior_only_max'):.2f})"
    )
    print(
        f"  blend at {result['permutation_blend_weight_on_context']}   measured "
        f"{number(result, 'blend_best_accuracy_tuning_split'):.2f}%  vs "
        f"permuted mean {number(result, 'accuracy_permuted_blend_mean'):.2f}%  "
        f"(range {number(result, 'accuracy_permuted_blend_min'):.2f}-"
        f"{number(result, 'accuracy_permuted_blend_max'):.2f})"
    )
    print(
        "  Firing rate, mass distribution, candidate count and smoothing are identical in both;\n"
        "  only the association between a mass and a candidate is destroyed. A gain the\n"
        "  permutation reproduces is the shape of the numbers, not knowledge the schema had."
    )

    checks = [] if args.limit else reproductions(result)
    print("\nharness check: three arms are the same code path over the same corpus with only")
    print("the count source changed, so each must land on a figure already in results.json.")
    if args.limit:
        print(f"  SKIPPED -- --limit {args.limit} scores a different population than the pins.")
    for label, want, got, ok in checks:
        print(f"  {'OK ' if ok else 'BAD'} {label:<62} want {want:>6.2f}  got {got:>6.2f}")
    if checks and not all(ok for _, _, _, ok in checks):
        print("  AT LEAST ONE ARM DOES NOT REPRODUCE -- treat every number above as unverified.")

    separates = number(overall, "instances_where_prior_separates_pct")
    delta = number(result, "schema_prior_minus_floor_points")
    blend_best = number(result, "blend_best_accuracy_tuning_split")
    control_mean = number(result, "accuracy_permuted_blend_mean")
    over_control = round(blend_best - control_mean, 2)
    transfers = (
        blend_best >= PREREGISTERED_TRANSFER_ACCURACY
        and over_control >= PREREGISTERED_CONTROL_MARGIN
    )
    result["blend_minus_permuted_control_points"] = over_control
    result["transfers_under_preregistered_rule"] = transfers
    result["preregistered_transfer_accuracy"] = PREREGISTERED_TRANSFER_ACCURACY
    result["preregistered_control_margin"] = PREREGISTERED_CONTROL_MARGIN
    print(
        f"\nPRE-REGISTERED RULE: transfers iff the blend reaches "
        f"{PREREGISTERED_TRANSFER_ACCURACY:.2f}% AND beats the information-free\n"
        f"control by {PREREGISTERED_CONTROL_MARGIN:.2f} points. "
        f"Blend {blend_best:.2f}% ({'PASS' if blend_best >= PREREGISTERED_TRANSFER_ACCURACY else 'FAIL'}), "
        f"over control {over_control:+.2f} "
        f"({'PASS' if over_control >= PREREGISTERED_CONTROL_MARGIN else 'FAIL'})."
    )
    print(
        "verdict: "
        + (
            f"the schema prior separates {separates:.2f}% of instances and is {delta:+.2f} "
            "points above the tie-break floor. Transfer is live; wire the contracts."
            if transfers
            else f"DOES NOT TRANSFER. The schema prior separates candidates on {separates:.2f}% "
            f"of instances and moves accuracy {delta:+.2f} points off the tie-break floor. "
            "The two catalog contracts should stay separate."
        )
    )

    if args.save:
        entries: Dict[str, object] = {
            "schema_prior.harvest": {
                "corpora": sorted(SNAPSHOTS),
                "constructions": list(CONSTRUCTIONS),
                "modes_unioned_for_token_word": list(MODES),
                "initialism_min_words": INITIALISM_MIN_WORDS,
                "initialism_max_words": INITIALISM_MAX_WORDS,
                "function_words_dropped": len(CAPTION_FUNCTION_WORDS),
                "union_keys": len(union),
                "scored_on_these_corpora": False,
                **space,
                "note": (
                    "socrata and sec_xbrl are read as a source of counts for a different task. "
                    "No figure is scored on either and no threshold is chosen on either, so "
                    "their held_out role for identifier_segmentation is untouched."
                ),
                **harvest_facts,
            },
            "schema_prior.contracts": {
                "corpus": "sdu21_ad diction.json against the union schema prior",
                **arity,
            },
            "schema_prior.sdu21.transfer": {
                "corpus": "sdu21_ad",
                "split": "dev",
                "prior_source": "socrata + sec_xbrl identifier/caption pairs, five constructions",
                # A statement about the LICENCE and nothing else. It says the
                # obstacle that stops the in-domain prior shipping does not
                # apply here; it does not say this prior is worth shipping.
                "prior_licence_permits_shipping": True,
                "prior_licence_note": (
                    "harvested from the caller's own schema; no corpus data is vendored, and "
                    "the two schema corpora carry no licence that forbids counting. This is a "
                    "licence fact, not a recommendation."
                ),
                "control_prior_source": "sdu21_ad train.json gold expansions (CC BY-NC-SA 4.0)",
                "selection_on_this_corpus": True,
                "mechanism": (
                    "bench/run_disambiguation_diagnosis.decompose and .predict, imported; "
                    "only the count source differs between arms"
                ),
                "reproduces_gated_figures": all(ok for _, _, _, ok in checks),
                **result,
            },
        }
        for label, row in sorted(census_rows.items()):
            entries[f"schema_prior.census.{label}"] = {"corpus": "sdu21_ad", "split": "dev", **row}
        print(f"\nsaved to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
