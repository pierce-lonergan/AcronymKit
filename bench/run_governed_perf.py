#!/usr/bin/env python3
"""What dominates the governed hot path, decomposed by cost centre.

Mandate III lists five optimisations for :mod:`acronymkit.governed` and then says
plainly that none of them is worth doing until it is known what dominates. This
runner is that measurement and nothing else: **it optimises nothing.** Every
figure it writes is a description of the shipped code on a real corpus.

The four cost centres, and why they are measured by ablation rather than by a
profiler's attribution
----------------------------------------------------------------------------
``expand_identifier`` does four separable things: it **tokenises** the name, it
**looks each token up** in the catalog, it **assembles a phrase** out of the long
forms, and it **constructs provenance** -- one frozen
:class:`~acronymkit.governed.models.TokenExpansion` per token and one
:class:`~acronymkit.governed.models.IdentifierExpansion` per call, each with a
validating ``__post_init__``.

A profiler can tell you what each *function* cost. It cannot tell you what each
*centre* cost, because the generated ``__init__`` of a frozen dataclass is a code
object called from the expansion path, and attributing it by caller puts
provenance's cost inside assembly's bucket. Rather than guess a split, this
runner measures five nested stages over the same corpus and subtracts:

============================  ==============================================
stage                         what it runs
============================  ==============================================
``tokenise``                  ``split_identifier_parts`` per identifier
``lookup``                    ``tokenise`` + the digit rejoin + a memoised
                              ``resolve`` per token
``phrase``                    ``lookup`` + the long form per token +
                              ``" ".join``
``class_word``                ``phrase`` + ``class_word_for`` where the
                              shipped path calls it
``full``                      ``expand_identifier``
============================  ==============================================

``tokenise``, ``lookup - tokenise``, ``phrase - lookup`` and ``full - phrase``
are the **four cost centres**, and they sum to the whole call. ``class_word`` is
a split *inside* the fourth -- ``class_word - phrase`` is the one provenance
field that costs a second index lookup, ``full - class_word`` is the record
construction itself -- and it is reported beside the four rather than instead of
them. The decomposition is additive by construction and needs no attribution
rule.

**The stages are checked against the shipped path three ways, because a stage
that does less work is a fiction that looks like a finding.**

* the ``phrase`` stage's output is compared **byte for byte** with
  ``expand_identifier(name, catalog).phrase`` on every identifier, and the
  mismatch count is saved: it is ``0`` or the arm is not a measurement;
* the ``phrase`` stage's ``resolve`` and ``split_identifier_parts`` call counts
  are compared with the shipped path's, and the excess is saved;
* the ``class_word`` stage's ``class_word_for`` call count likewise.

The second check is not decoration. The first draft of ``stage_lookup`` resolved
every token instead of consulting a memo first, so on the arm where the catalog
answers it did *more* work than the call it was subtracted from and the assembly
centre came out at ``-7.78 %``. A negative cost centre is the loud version of
that failure; the quiet version is a stage that skips lookups while agreeing on
every phrase, and only a count catches it.

R17: a performance number without a work count is a null result
---------------------------------------------------------------
So every throughput entry here carries, beside the rate: identifiers processed,
distinct identifiers, token occurrences, distinct tokens, catalog lookups
actually performed, how many of those reached the index rather than the memo,
expansion-memo hit rate, tokenizer passes, and how many provenance records were
constructed. A pass that got fast by not doing the work is visible in those
counts and invisible in the rate.

R18: counts are gated, nanoseconds are a note
---------------------------------------------
Call counts and construction counts are properties of the code and are
deterministic: two runs on two machines produce the same integers. Wall-clock is
a property of the runner. Both are saved -- a saved figure is not the same as a
cited one -- and ``docs/EVALUATION.md`` cites the counts in prose and prints the
nanoseconds inside a fenced block with the machine named. The stage *shares* are
derived from wall-clock and are therefore in the second class, not the first,
however much they look like structure.

The mechanism the counts come from, and what it costs
------------------------------------------------------
:mod:`cProfile`, over a separate pass from the timed one. Call counts under
``cProfile`` are exact and deterministic; the profiler perturbs *time* and cannot
perturb a count. Functions are identified by their code objects rather than by
name, so a rename in ``src/`` breaks this runner loudly instead of silently
counting nothing. ``--only overhead`` measures what the profiler costs on this
machine and saves it, because "we counted with a profiler" is not a statement
about accuracy until the overhead is a number.

:mod:`tracemalloc` is deliberately **not** used. It traces the blocks that are
currently live, not the allocations that happened, so it cannot answer "how many
allocations" at all. What it would report is a peak, and a peak over a streaming
pass is a property of the garbage collector's schedule. Object constructions are
counted instead, exactly, as ``__post_init__`` calls.

The corpora, and what their distribution actually is
-----------------------------------------------------
A profiler measures the workload it is given, and a synthetic identifier
distribution reports whatever was built into it. So the two real corpora are
used as they were fetched, in occurrence order, and ``--only census`` publishes
their distribution rather than assuming it.

``socrata``
    Every field name in the cached Socrata metadata fetch, as it occurs. Real
    portal schemas, ``snake_lower`` and ``flat_lower``.

``sec_xbrl``
    Every element name in the cached SEC XBRL fetch. ``CamelCase``, much longer
    names, so a different token-per-identifier profile.

``fixture_schema``
    The synthetic arm ``bench/run_governed.py`` already uses: identifiers drawn
    from the fixture catalog's own token pool. **It is the only arm in this
    runner where the catalog ever answers**, because no public catalog exists
    for the two real corpora, and it is therefore the only arm where the memo
    can fire at all. Its distribution is a fixture's and it is labelled as such.

Both real corpora are **schema** corpora. Nothing here says what a prose caller's
hot path looks like, and no figure in this file may be quoted about one.

Usage::

    python bench/run_governed_perf.py                     # report, record nothing
    python bench/run_governed_perf.py --save              # record into bench/results.json
    python bench/run_governed_perf.py --only census       # distribution only
    python bench/run_governed_perf.py --limit 20000       # a short pass, for a smoke test
"""

from __future__ import annotations

import argparse
import ast
import cProfile
import csv
import json
import platform
import pstats
import random
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from types import CodeType
from typing import Any, Callable, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit.governed import (  # noqa: E402
    GovernedDictionary,
    expand_identifier,
)
from acronymkit.governed import dictionary as dictionary_module  # noqa: E402
from acronymkit.governed import expansion as expansion_module  # noqa: E402
from acronymkit.governed import models as models_module  # noqa: E402
from acronymkit.governed import tokenizer as tokenizer_module  # noqa: E402
from acronymkit.governed.tokenizer import split_identifier, split_identifier_parts  # noqa: E402

#: The governed-gold cache the two real corpora are read out of.
GOVERNED_GOLD_CACHE = REPO_ROOT / "data" / "governed_gold"

#: The fixture catalog ``bench/run_governed.py`` builds its schema arm from.
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "governed"

#: Which cache file each real corpus is read from. Named rather than globbed:
#: ``bench/corpora.py`` refuses to choose between two snapshots of a live
#: catalog, and this runner must not make that choice implicitly either.
SNAPSHOTS = {
    "socrata": "socrata_80pages_v2.json",
    "sec_xbrl": "sec_xbrl_2025q1.json",
}

#: Identifiers in the synthetic fixture arm. Small, because it is a control on
#: the two real corpora rather than a population in its own right.
FIXTURE_SCHEMA_IDENTIFIERS = 20_000

#: Timed repeats behind every stage figure within one round; the minimum is
#: taken, because the minimum of a CPU-bound pass is the one statistic a
#: scheduler cannot inflate.
STAGE_REPEATS = 2

#: Independent decompositions behind every saved share. Three, because the
#: quantity being reported is a difference of two timings and the first version
#: of this runner published a point estimate of it that moved by ten points
#: between two runs on one machine.
DECOMPOSITION_ROUNDS = 3

#: The counts this runner claims are inherited rather than measured, so that the
#: claim and its re-derivation sit in one saved entry. Both come from
#: ``docs/AUDIT-2026-08.md``; neither population was ever saved.
INHERITED_SOCRATA_PAIRS = 164_652
INHERITED_IDENTIFIER_CORPUS = 107_012
INHERITED_IDENTIFIER_SOURCES = 8


def environment() -> str:
    """One-line description of the machine, for the results table."""
    return f"Python {platform.python_version()} on {platform.system()} {platform.machine()}"


def machine_note() -> str:
    """The machine named, for the unarmed wall-clock note R18 requires."""
    processor = platform.processor() or platform.machine()
    return f"{environment()}; {processor}"


# ---------------------------------------------------------------------------
# corpora
# ---------------------------------------------------------------------------


def read_snapshot(name: str) -> tuple[tuple[str, ...], str, str]:
    """Read one governed-gold cache file and return its identifiers in order.

    The identifiers are returned **as they occur**, not deduplicated, because the
    repetition is the property every memoisation figure in this file is about.

    Args:
        name: ``"socrata"`` or ``"sec_xbrl"``.

    Returns:
        The identifiers in cache order, the file name read, and the fetch date.

    Raises:
        SystemExit: If the corpus is unknown or the cache file is absent.
    """
    if name not in SNAPSHOTS:
        raise SystemExit(f"unknown corpus {name!r}; known: {sorted(SNAPSHOTS)}")
    source = GOVERNED_GOLD_CACHE / SNAPSHOTS[name]
    if not source.is_file():
        raise SystemExit(f"missing {source}\nRun: python bench/run_governed_gold.py --only {name}")
    envelope = json.loads(source.read_text(encoding="utf-8"))
    payload = envelope.get("payload")
    if not isinstance(payload, list):
        raise SystemExit(f"{source} is not a run_governed_gold cache envelope")
    identifiers = tuple(
        str(row[0]) for row in payload if isinstance(row, list) and row and str(row[0]).strip()
    )
    return identifiers, source.name, str(envelope.get("fetched_on") or "unknown")


def build_fixture_dictionary() -> GovernedDictionary:
    """Assemble the Northwind Data Standards fixture vocabulary.

    The same five files ``bench/run_governed.py`` builds from, so the two runners
    are talking about one catalog.

    Returns:
        The fixture vocabulary.
    """
    allow_list = json.loads((FIXTURES / "allowlist.json").read_text(encoding="utf-8"))
    class_words = json.loads((FIXTURES / "class_words.json").read_text(encoding="utf-8"))
    with (FIXTURES / "term_glossary.csv").open(encoding="utf-8", newline="") as handle:
        glossary = {row["logical_name"]: row["term_id"] for row in csv.DictReader(handle)}
    return GovernedDictionary.from_json(
        FIXTURES / "dictionary.json",
        approved_abbreviations=allow_list["approved_abbreviations"],
        common_keywords=allow_list["common_keywords"],
        short_full_words=allow_list["short_full_words"],
        class_words=class_words["abbreviations"],
        term_index=glossary,
    )


def fixture_schema_corpus(count: int, *, seed: int = 0) -> tuple[str, ...]:
    """Distinct identifiers with the fixture corpus's token-frequency profile.

    A copy of ``bench/run_governed.py``'s ``schema_corpus`` rather than an import,
    because that runner's module-level constants would drag its whole measurement
    surface in. The recipe is the same and the seed is the same, so the corpus is
    the same.

    Args:
        count: How many identifiers to produce.
        seed: The generator seed.

    Returns:
        ``count`` distinct identifiers.
    """
    text = (FIXTURES / "corpus_sample.txt").read_text(encoding="utf-8")
    names = [line.strip() for line in text.splitlines() if line.strip()]
    splits = [split_identifier(name) for name in names]
    pool = [token for tokens in splits for token in tokens]
    lengths = [len(tokens) for tokens in splits]
    rng = random.Random(seed)

    corpus: list[str] = []
    seen: set[str] = set()
    while len(corpus) < count:
        candidate = "_".join(rng.choice(pool) for _ in range(rng.choice(lengths)))
        if candidate in seen:
            continue
        seen.add(candidate)
        corpus.append(candidate)
    return tuple(corpus)


# ---------------------------------------------------------------------------
# the census: the entire ceiling of the memoisation workstream, in one pass
# ---------------------------------------------------------------------------


def census(identifiers: Sequence[str]) -> dict[str, Any]:
    """Distinctness and skew, at identifier level and at token level.

    This is the whole of what can be said about a memo's ceiling without running
    one: a memo cannot be worth more than the share of work that repeats, and the
    share of work that repeats is a property of the corpus alone.

    ``hapax`` is the share that occurs exactly once -- the part no memo can ever
    serve, and the part whose bookkeeping a memo pays for and gets nothing back.

    Args:
        identifiers: The corpus, in occurrence order, not deduplicated.

    Returns:
        Counts and percentages. Percentages are rounded to two places; the counts
        they are derived from are saved beside them so the rounding is auditable.
    """
    identifier_counts = Counter(identifiers)
    tokens = [token for name in identifiers for token in split_identifier(name)]
    token_counts = Counter(tokens)
    occurrences = len(tokens)
    ranked = token_counts.most_common()

    def share(top: int) -> float:
        return 100.0 * sum(count for _, count in ranked[:top]) / occurrences if occurrences else 0.0

    identifier_hapax = sum(1 for count in identifier_counts.values() if count == 1)
    token_hapax = sum(1 for count in token_counts.values() if count == 1)
    return {
        "identifiers": len(identifiers),
        "distinct_identifiers": len(identifier_counts),
        "distinct_identifiers_pct": round(100.0 * len(identifier_counts) / len(identifiers), 2),
        "identifier_hapax": identifier_hapax,
        "identifier_hapax_pct_of_distinct": round(
            100.0 * identifier_hapax / len(identifier_counts), 2
        ),
        "token_occurrences": occurrences,
        "distinct_tokens": len(token_counts),
        "distinct_tokens_pct": round(100.0 * len(token_counts) / occurrences, 2)
        if occurrences
        else 0.0,
        "tokens_per_identifier": round(occurrences / len(identifiers), 3),
        "top1_token_occurrence_pct": round(share(1), 2),
        "top5_token_occurrence_pct": round(share(5), 2),
        "top20_token_occurrence_pct": round(share(20), 2),
        "top100_token_occurrence_pct": round(share(100), 2),
        "token_hapax": token_hapax,
        "token_hapax_pct_of_distinct": round(100.0 * token_hapax / len(token_counts), 2)
        if token_counts
        else 0.0,
        "token_hapax_pct_of_occurrences": round(100.0 * token_hapax / occurrences, 2)
        if occurrences
        else 0.0,
        # The shipped memo is a fixed-size map that CLEARS when it fills; it has
        # no eviction order. So the ceiling on memoisation is not the repeat rate
        # alone, it is the repeat rate given a working set this size. Read out of
        # the module rather than written down here, so the day the constant moves
        # this figure moves with it.
        "memo_limit": dictionary_module._MEMO_LIMIT,
        "distinct_tokens_per_memo_limit": round(
            len(token_counts) / dictionary_module._MEMO_LIMIT, 2
        ),
        "tokens_within_memo_limit_occurrence_pct": round(
            100.0
            * sum(count for _, count in ranked[: dictionary_module._MEMO_LIMIT])
            / occurrences,
            2,
        )
        if occurrences
        else 0.0,
    }


def top_tokens(identifiers: Sequence[str], count: int = 10) -> str:
    """The commonest tokens, comma-separated, for the console and the entry.

    Args:
        identifiers: The corpus, in occurrence order.
        count: How many to name.

    Returns:
        ``"id,name,date"`` -- lower-cased, so the string is stable across a
        corpus whose casing convention differs.
    """
    tokens = Counter(token.lower() for name in identifiers for token in split_identifier(name))
    return ",".join(token for token, _ in tokens.most_common(count))


# ---------------------------------------------------------------------------
# the four nested stages
# ---------------------------------------------------------------------------


def stage_tokenise(identifiers: Sequence[str], catalog: GovernedDictionary) -> None:
    """Tokenise every identifier and do nothing with the result.

    Args:
        identifiers: The corpus.
        catalog: Unused; the signature is shared with the other three stages so
            they can be driven from one table.
    """
    del catalog
    for name in identifiers:
        split_identifier_parts(name)


def stage_lookup(identifiers: Sequence[str], catalog: GovernedDictionary) -> None:
    """Tokenise, repair a digit-leading catalog token, and resolve every token.

    The digit rejoin is included because it is the shipped path's second source
    of catalog lookups, and leaving it out would credit its cost to provenance.

    **The memo short-circuit is included too, and the first draft of this runner
    left it out.** ``_expand`` consults the expansion memo *before* it calls
    ``resolve``, so on a corpus where the catalog answers, the shipped path takes
    far fewer lookups than a naive "resolve every token" loop. Without the
    short-circuit this stage did more work than the stage above it and the
    assembly centre came out at ``-7.78 %`` on the fixture arm -- a negative cost
    centre, which is the instrument saying it is wrong rather than the code being
    strange. The memo here records only that a token was known, never what it
    expanded to; deciding the long form is the next stage's job and is exactly
    the difference the subtraction is supposed to isolate.

    Args:
        identifiers: The corpus.
        catalog: The vocabulary.
    """
    policy = expansion_module._DEFAULT_POLICY
    rejoin = expansion_module._rejoin_digit_tokens
    known: set[str] = set()
    for name in identifiers:
        parts = split_identifier_parts(name)
        for token in rejoin(parts.tokens, catalog, policy):
            if token in known:
                continue
            if catalog.resolve(token, policy) is not None:
                known.add(token)


def stage_phrase(identifiers: Sequence[str], catalog: GovernedDictionary) -> None:
    """Everything ``stage_lookup`` does, plus the phrase, and no DTO at all.

    This is the counterfactual behind the whole provenance question: exactly the
    work a caller who reads only ``.phrase`` needs done, and none of the work a
    caller who reads ``.tokens`` needs done.

    The long-form memo mirrors
    :class:`~acronymkit.governed.dictionary._Memo` on the one property that
    matters here -- it remembers hits and never remembers misses -- so the two
    paths take the same number of lookups. :func:`verify_phrase_parity` is what
    turns that from an intention into a check.

    Args:
        identifiers: The corpus.
        catalog: The vocabulary.
    """
    policy = expansion_module._DEFAULT_POLICY
    rejoin = expansion_module._rejoin_digit_tokens
    title_case = expansion_module._title_case
    memo: dict[str, str] = {}
    for name in identifiers:
        parts = split_identifier_parts(name)
        longs: list[str] = []
        for token in rejoin(parts.tokens, catalog, policy):
            remembered = memo.get(token)
            if remembered is not None:
                longs.append(remembered)
                continue
            entry = catalog.resolve(token, policy)
            if entry is None:
                longs.append(title_case(token))
            else:
                memo[token] = entry.canonical
                longs.append(entry.canonical)
        " ".join(long_form for long_form in longs if long_form)


def stage_class_word(identifiers: Sequence[str], catalog: GovernedDictionary) -> None:
    """Everything ``stage_phrase`` does, plus the one provenance field that costs
    a second catalog lookup.

    ``class_word`` is the only field on a
    :class:`~acronymkit.governed.models.TokenExpansion` that is not already in
    hand by the time the record is built: every other field is read off the
    entry or off the token, and this one is a second index lookup per token. It
    is therefore worth separating from the cost of *constructing* the record,
    because a lazy-provenance design that deferred the record would still have
    to decide whether to defer this, and the two decisions have different
    prices.

    The call pattern mirrors ``_expand`` and ``_passthrough`` exactly: an entry
    whose own ``class_word`` is set does not trigger a lookup, a memo hit
    triggers neither, and an unknown token triggers one every time because
    passthroughs are never memoised. :func:`measure_arm` checks the resulting
    count against the shipped path's rather than trusting this paragraph.

    Args:
        identifiers: The corpus.
        catalog: The vocabulary.
    """
    policy = expansion_module._DEFAULT_POLICY
    rejoin = expansion_module._rejoin_digit_tokens
    title_case = expansion_module._title_case
    memo: dict[str, str] = {}
    for name in identifiers:
        parts = split_identifier_parts(name)
        longs: list[str] = []
        for token in rejoin(parts.tokens, catalog, policy):
            remembered = memo.get(token)
            if remembered is not None:
                longs.append(remembered)
                continue
            entry = catalog.resolve(token, policy)
            if entry is None:
                catalog.class_word_for(token)
                longs.append(title_case(token))
            else:
                if not entry.class_word:
                    catalog.class_word_for(token)
                memo[token] = entry.canonical
                longs.append(entry.canonical)
        " ".join(long_form for long_form in longs if long_form)


def stage_full(identifiers: Sequence[str], catalog: GovernedDictionary) -> None:
    """The shipped call, once per identifier.

    Args:
        identifiers: The corpus.
        catalog: The vocabulary.
    """
    for name in identifiers:
        expand_identifier(name, catalog)


#: The nested stages, cheapest first. The order is the subtraction order.
STAGES: tuple[tuple[str, Callable[[Sequence[str], GovernedDictionary], None]], ...] = (
    ("tokenise", stage_tokenise),
    ("lookup", stage_lookup),
    ("phrase", stage_phrase),
    ("class_word", stage_class_word),
    ("full", stage_full),
)

#: Which centre each subtraction names. The first four are the four cost centres
#: the brief asks for and they sum to the whole call. The last two are a split
#: **inside** ``provenance`` and are reported beside it rather than instead of
#: it, because a reader comparing this table against the brief must find the
#: four it names.
CENTRES = (
    ("tokenise", "tokenise", None),
    ("catalog", "lookup", "tokenise"),
    ("assembly", "phrase", "lookup"),
    ("provenance", "full", "phrase"),
)

#: The two halves of the provenance centre, reported separately.
PROVENANCE_SPLIT = (
    ("provenance_class_word", "class_word", "phrase"),
    ("provenance_records", "full", "class_word"),
)


def verify_phrase_parity(
    identifiers: Sequence[str], catalog_factory: Callable[[], GovernedDictionary]
) -> int:
    """Count identifiers where the ``phrase`` stage and the real call disagree.

    Run on freshly built vocabularies so neither side is served an answer the
    other one taught the dictionary. The comparison is on the string, character
    for character; this is not "the accuracy matched".

    Args:
        identifiers: The corpus.
        catalog_factory: Builds an unused vocabulary; called twice.

    Returns:
        The mismatch count. Anything but zero invalidates the arm.
    """
    policy = expansion_module._DEFAULT_POLICY
    rejoin = expansion_module._rejoin_digit_tokens
    title_case = expansion_module._title_case

    reference_catalog = catalog_factory()
    stage_catalog = catalog_factory()
    memo: dict[str, str] = {}
    mismatches = 0
    for name in identifiers:
        parts = split_identifier_parts(name)
        longs: list[str] = []
        for token in rejoin(parts.tokens, stage_catalog, policy):
            remembered = memo.get(token)
            if remembered is not None:
                longs.append(remembered)
                continue
            entry = stage_catalog.resolve(token, policy)
            if entry is None:
                longs.append(title_case(token))
            else:
                memo[token] = entry.canonical
                longs.append(entry.canonical)
        staged = " ".join(long_form for long_form in longs if long_form)
        if staged != expand_identifier(name, reference_catalog).phrase:
            mismatches += 1
    return mismatches


def time_stage(
    runner: Callable[[Sequence[str], GovernedDictionary], None],
    identifiers: Sequence[str],
    catalog_factory: Callable[[], GovernedDictionary],
    repeats: int,
) -> int:
    """Fastest of ``repeats`` timed passes, in nanoseconds.

    Every repeat gets a vocabulary that has answered nothing, because a
    dictionary remembers what it was asked and a second pass over one object is
    not the same question as the first.

    Args:
        runner: The stage.
        identifiers: The corpus.
        catalog_factory: Builds an unused vocabulary.
        repeats: Timed passes.

    Returns:
        The minimum elapsed nanoseconds.
    """
    samples: list[int] = []
    for _ in range(repeats):
        catalog = catalog_factory()
        started = time.perf_counter_ns()
        runner(identifiers, catalog)
        samples.append(time.perf_counter_ns() - started)
    return min(samples)


def decompose_once(
    identifiers: Sequence[str],
    catalog_factory: Callable[[], GovernedDictionary],
    repeats: int,
) -> dict[str, float]:
    """One complete five-stage decomposition, as percentages of the full call.

    Args:
        identifiers: The corpus.
        catalog_factory: Builds an unused vocabulary.
        repeats: Timed passes per stage; the fastest is taken.

    Returns:
        ``{centre: percent}`` for the four centres and the two provenance halves,
        plus ``full_ns`` and ``phrase_only_speedup`` for this round.
    """
    elapsed = {
        name: time_stage(runner, identifiers, catalog_factory, repeats) for name, runner in STAGES
    }
    total = elapsed["full"]
    round_figures: dict[str, float] = {
        "full_ns": float(total),
        "phrase_only_speedup": total / elapsed["phrase"] if elapsed["phrase"] else 0.0,
    }
    for centre, upper, lower in CENTRES + PROVENANCE_SPLIT:
        delta = elapsed[upper] - (elapsed[lower] if lower else 0)
        round_figures[centre] = 100.0 * delta / total if total else 0.0
    return round_figures


def decompose(
    identifiers: Sequence[str],
    catalog_factory: Callable[[], GovernedDictionary],
    *,
    rounds: int,
    repeats: int,
) -> dict[str, Any]:
    """``rounds`` independent decompositions, reported with their spread.

    **A single share with no spread is not a measurement, and on this
    decomposition it is a misleading one.** Three of the four centres are
    *differences* of two large, similar timings, so each inherits the noise of
    both and its share is far less stable than the underlying figures. Measured
    across three full runs of this runner on one machine, the provenance share of
    the Socrata arm moved between ``58.75`` and ``68.56`` while every work count
    in the same entries stayed byte-identical -- which is R18's argument arriving
    inside its own benchmark rather than as a principle.

    So the saved figure is the **median** of ``rounds`` decompositions, and the
    minimum and maximum are saved beside it. A reader who wants one number should
    take the ordering, not the magnitude.

    Args:
        identifiers: The corpus.
        catalog_factory: Builds an unused vocabulary.
        rounds: Independent decompositions.
        repeats: Timed passes per stage within a round.

    Returns:
        ``{f"stage_{centre}_pct": median}`` plus ``_min`` and ``_max`` for each,
        and the same three for ``phrase_only_speedup`` and ``full_ns``.
    """
    observed = [decompose_once(identifiers, catalog_factory, repeats) for _ in range(rounds)]
    figures: dict[str, Any] = {"decomposition_rounds": rounds}
    for centre, _, _ in CENTRES + PROVENANCE_SPLIT:
        values = sorted(round_figures[centre] for round_figures in observed)
        figures[f"stage_{centre}_pct"] = round(statistics.median(values), 2)
        figures[f"stage_{centre}_pct_min"] = round(values[0], 2)
        figures[f"stage_{centre}_pct_max"] = round(values[-1], 2)
    for field, places in (("phrase_only_speedup", 3), ("full_ns", 0)):
        values = sorted(round_figures[field] for round_figures in observed)
        figures[field] = round(statistics.median(values), places)
        figures[f"{field}_min"] = round(values[0], places)
        figures[f"{field}_max"] = round(values[-1], places)
    return figures


# ---------------------------------------------------------------------------
# the work counts
# ---------------------------------------------------------------------------


def _key(function: object) -> tuple[str, int, str]:
    """The ``pstats`` key for a Python function, taken from its code object.

    Identifying a function by its code object rather than by ``(file, name)``
    means a rename or a move in ``src/acronymkit/governed`` makes this runner
    fail to find it, rather than quietly report zero calls for it.

    Args:
        function: Any Python function or method.

    Returns:
        ``(filename, first line, name)``.
    """
    code: CodeType = function.__code__  # type: ignore[attr-defined]
    return (code.co_filename, code.co_firstlineno, code.co_name)


#: The functions whose call counts are the work counts, and which must run at
#: least once or the decomposition is describing a path the code no longer
#: takes. Values are the field name each lands under in the saved entry.
COUNTED = {
    "tokenizer_passes": split_identifier_parts,
    "call_preparations": expansion_module._prepare,
    "sequence_validations": models_module._freeze_sequences,
    "confidence_validations": models_module._freeze_confidence,
    "catalog_lookups": GovernedDictionary.resolve,
    "catalog_index_decisions": GovernedDictionary._decide,
    "class_word_lookups": GovernedDictionary.class_word_for,
    "token_expands": expansion_module._expand,
    "token_expansions_constructed": models_module.TokenExpansion.__post_init__,
    "identifier_expansions_constructed": models_module.IdentifierExpansion.__post_init__,
    "memo_partitions_consulted": GovernedDictionary._memo,
    "token_keys_folded": dictionary_module._token_key,
}

#: Counted the same way, and allowed to be **zero**, because zero is the
#: interesting answer rather than a broken lookup.
#:
#: ``_scan`` is the character-by-character reference reading of the tokenisation
#: rules, and ``split_identifier_parts`` takes an all-C regex path for any
#: identifier that ``str.isascii``. ``docs/AUDIT-2026-08.md`` question 6 records
#: that zero of the audit's real identifiers were non-ASCII; this runner
#: re-derives that on the two corpora it reads, as a count rather than as a
#: recollection. ``_passthrough`` is zero exactly when every token in the corpus
#: is in the catalog, which is true of the synthetic fixture arm and of nothing
#: else here. ``_title_case`` is zero under exactly the same condition, because
#: it renders a passthrough and nothing else.
#:
#: A rename in ``src/`` still breaks this runner, because both are reached by
#: attribute access at import time rather than by string lookup in the profile.
COUNTED_OPTIONAL = {
    "tokenizer_scans": tokenizer_module._scan,
    "title_casings": expansion_module._title_case,
    "token_passthroughs": expansion_module._passthrough,
}


# ---------------------------------------------------------------------------
# the caller census: the premise underneath the lazy-provenance bet
# ---------------------------------------------------------------------------
#
# "Every call builds a full record and most callers read only ``.phrase``" is
# the sentence the whole lazy-provenance workstream rests on. The second half of
# it is a claim about *callers*, and it had never been measured against anything.
# It cannot be measured against strangers -- this project has zero confirmed
# adopters on two independent instruments -- but it can be measured exactly
# against the one caller population that exists, which is this repository.
#
# That is a small population and a biased one, and it is named as such wherever
# the figure appears. What it is not is nothing.

#: Roots searched for callers, grouped, because the pooled figure is the least
#: informative reading available and it was the first one this runner produced.
#:
#: ``library``
#:     ``src/acronymkit`` -- the package's own callers of its own verb. Three
#:     sites, and what they read is the strongest evidence here about what an
#:     ``IdentifierExpansion`` is for.
#: ``harness``
#:     ``bench``, ``tools`` and ``examples`` -- code that scores segmentation or
#:     demonstrates the API. Every phrase-only site in this repository is in this
#:     group, and that is a fact about what a benchmark needs rather than about
#:     what a caller needs.
#: ``tests``
#:     Reported and never pooled. A test reads every field on purpose, so folding
#:     it in manufactures the answer in whichever direction the suite leans.
CALLER_GROUPS = (
    ("library", ("src/acronymkit",)),
    ("harness", ("bench", "tools", "examples")),
    ("tests", ("tests",)),
)

#: This file is excluded from its own census. It calls ``expand_identifier`` in
#: the parity check and in ``stage_full``, and a measurement that counts its own
#: call sites among the population it is measuring is circular -- here, in the
#: flattering direction, since one of them reads only ``.phrase``.
CALLER_CENSUS_EXCLUDES = frozenset({"run_governed_perf.py"})

#: The attribute a caller can read without any provenance being built. The
#: identifier is the input echoed back, so it costs nothing either.
PHRASE_ONLY_FIELDS = frozenset({"phrase", "identifier"})

#: The attribute a caller can read without any provenance being built. The
#: identifier is the input echoed back, so it costs nothing either.
PHRASE_ONLY_FIELDS = frozenset({"phrase", "identifier"})


def _enclosing_scope(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.AST:
    """The nearest function or module containing ``node``."""
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            return current
    return current


def _call_name(call: ast.Call) -> Optional[str]:
    """The called function's bare name, for ``f()`` and for ``mod.f()`` alike."""
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def caller_sites(path: Path) -> list[tuple[int, str, tuple[str, ...]]]:
    """Every ``expand_identifier`` call in one file, and the fields it reads.

    Three shapes are recognised, and the third is reported rather than guessed
    at:

    * ``expand_identifier(...).phrase`` -- the field is on the call;
    * ``result = expand_identifier(...)`` -- the fields are every attribute read
      on that name anywhere in the enclosing function;
    * anything else -- passed onward, returned, appended to a list. Counted as
      ``unclassified``, because a call whose result leaves the scope could read
      any field at all and "no fields" would be a false zero.

    Args:
        path: A Python source file.

    Returns:
        ``(line, shape, fields)`` per call site. ``fields`` is empty for the
        unclassified shape.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    found: list[tuple[int, str, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node) != "expand_identifier":
            continue
        parent = parents.get(node)
        if isinstance(parent, ast.Attribute):
            found.append((node.lineno, "attribute", (parent.attr,)))
            continue
        bound: Optional[str] = None
        if isinstance(parent, ast.Assign) and len(parent.targets) == 1:
            target = parent.targets[0]
            if isinstance(target, ast.Name):
                bound = target.id
        elif isinstance(parent, (ast.AnnAssign, ast.NamedExpr)) and isinstance(
            parent.target, ast.Name
        ):
            bound = parent.target.id
        if bound is None:
            found.append((node.lineno, "unclassified", ()))
            continue
        scope = _enclosing_scope(node, parents)
        fields = {
            read.attr
            for read in ast.walk(scope)
            if isinstance(read, ast.Attribute)
            and isinstance(read.value, ast.Name)
            and read.value.id == bound
        }
        found.append((node.lineno, "bound", tuple(sorted(fields))))
    return found


def caller_census() -> dict[str, Any]:
    """How this repository's own callers use an ``IdentifierExpansion``.

    Returns:
        The saveable entry. ``phrase_only`` counts the classified sites whose
        every read is in :data:`PHRASE_ONLY_FIELDS`; ``provenance_reading``
        counts the rest. Unclassified sites are counted and excluded from both,
        rather than being assigned to whichever answer is convenient.
    """
    entry: dict[str, Any] = {}
    for label, roots in CALLER_GROUPS:
        sites = 0
        classified = 0
        phrase_only = 0
        unclassified = 0
        for root in roots:
            for path in sorted((REPO_ROOT / root).rglob("*.py")):
                if path.name in CALLER_CENSUS_EXCLUDES:
                    continue
                for _, shape, fields in caller_sites(path):
                    sites += 1
                    if shape == "unclassified" or not fields:
                        unclassified += 1
                        continue
                    classified += 1
                    if set(fields) <= PHRASE_ONLY_FIELDS:
                        phrase_only += 1
        entry[f"{label}_sites"] = sites
        entry[f"{label}_classified"] = classified
        entry[f"{label}_phrase_only"] = phrase_only
        entry[f"{label}_provenance_reading"] = classified - phrase_only
        entry[f"{label}_unclassified"] = unclassified
        entry[f"{label}_phrase_only_pct"] = (
            round(100.0 * phrase_only / classified, 2) if classified else 0.0
        )
    entry["excludes"] = ",".join(sorted(CALLER_CENSUS_EXCLUDES))
    return entry


def work_counts(identifiers: Sequence[str], catalog: GovernedDictionary) -> dict[str, int]:
    """Exact call counts for one full pass, from :mod:`cProfile`.

    Counts, not times: the profiler perturbs the second and cannot perturb the
    first. Two runs of this function on two machines return the same integers,
    which is the property R18 asks a gated figure to have.

    Args:
        identifiers: The corpus.
        catalog: A vocabulary that has answered nothing.

    Returns:
        ``{field: count}`` for every entry in :data:`COUNTED`, plus the total
        Python-level call count and the two derived memo splits.

    Raises:
        SystemExit: If a counted function never appeared in the profile, which
            means it was renamed, moved, or is no longer on the path -- all
            three of which are findings rather than zeroes.
    """
    profiler = cProfile.Profile()
    profiler.enable()
    for name in identifiers:
        expand_identifier(name, catalog)
    profiler.disable()
    stats = pstats.Stats(profiler).stats  # type: ignore[attr-defined]

    counts: dict[str, int] = {}
    for field, function in COUNTED.items():
        key = _key(function)
        if key not in stats:
            raise SystemExit(
                f"{field}: {key[2]} at {key[0]}:{key[1]} never ran during the pass. "
                "It was renamed, moved, or has left the hot path; this runner's "
                "cost centres are stale and the counts must not be saved."
            )
        counts[field] = int(stats[key][1])
    for field, function in COUNTED_OPTIONAL.items():
        key = _key(function)
        counts[field] = int(stats[key][1]) if key in stats else 0

    counts["python_calls_total"] = sum(int(row[1]) for row in stats.values())

    # Which of the resolve calls came from the token path, so the expansion memo
    # and the resolve memo can be reported separately rather than pooled.
    resolve_callers = stats[_key(GovernedDictionary.resolve)][4]
    from_expand = int(resolve_callers.get(_key(expansion_module._expand), (0, 0, 0.0, 0.0))[1])
    counts["catalog_lookups_from_token_path"] = from_expand
    counts["catalog_lookups_from_digit_rejoin"] = counts["catalog_lookups"] - from_expand
    counts["expansion_memo_hits"] = counts["token_expands"] - from_expand
    counts["catalog_memo_hits"] = counts["catalog_lookups"] - counts["catalog_index_decisions"]
    return counts


def stage_phrase_counts(identifiers: Sequence[str], catalog: GovernedDictionary) -> dict[str, int]:
    """Catalog lookups and tokenizer passes taken by the ``phrase`` stage.

    The parity check that makes the subtraction legitimate. Byte-identical
    output (:func:`verify_phrase_parity`) says the stage produced the same
    answer; this says it produced it by doing the same amount of catalog work. A
    stage that agreed on every phrase while taking half the lookups would make
    ``full - phrase`` charge provenance for the lookups it skipped, and nothing
    in the output would look wrong.

    Args:
        identifiers: The corpus.
        catalog: A vocabulary that has answered nothing.

    Returns:
        ``{"stage_catalog_lookups": n, "stage_tokenizer_passes": n}``.
    """
    profiler = cProfile.Profile()
    profiler.enable()
    stage_phrase(identifiers, catalog)
    profiler.disable()
    stats = pstats.Stats(profiler).stats  # type: ignore[attr-defined]

    def calls(function: object) -> int:
        key = _key(function)
        return int(stats[key][1]) if key in stats else 0

    return {
        "stage_catalog_lookups": calls(GovernedDictionary.resolve),
        "stage_tokenizer_passes": calls(split_identifier_parts),
    }


def stage_class_word_counts(
    identifiers: Sequence[str], catalog: GovernedDictionary
) -> dict[str, int]:
    """Class-word lookups taken by the ``class_word`` stage.

    Args:
        identifiers: The corpus.
        catalog: A vocabulary that has answered nothing.

    Returns:
        ``{"stage_class_word_lookups": n}``, to be checked against the shipped
        path's ``class_word_lookups``.
    """
    profiler = cProfile.Profile()
    profiler.enable()
    stage_class_word(identifiers, catalog)
    profiler.disable()
    stats = pstats.Stats(profiler).stats  # type: ignore[attr-defined]
    key = _key(GovernedDictionary.class_word_for)
    return {"stage_class_word_lookups": int(stats[key][1]) if key in stats else 0}


def profiler_overhead(
    identifiers: Sequence[str], catalog_factory: Callable[[], GovernedDictionary]
) -> dict[str, Any]:
    """What the counting mechanism costs, so "we used a profiler" is a number.

    Args:
        identifiers: The corpus to time both ways.
        catalog_factory: Builds an unused vocabulary; called twice.

    Returns:
        Both elapsed times in nanoseconds and the ratio.
    """
    clean_catalog = catalog_factory()
    started = time.perf_counter_ns()
    stage_full(identifiers, clean_catalog)
    clean = time.perf_counter_ns() - started

    profiled_catalog = catalog_factory()
    profiler = cProfile.Profile()
    started = time.perf_counter_ns()
    profiler.enable()
    stage_full(identifiers, profiled_catalog)
    profiler.disable()
    profiled = time.perf_counter_ns() - started

    return {
        "identifiers": len(identifiers),
        "unprofiled_ns": clean,
        "profiled_ns": profiled,
        "profiler_cost_ratio": round(profiled / clean, 3) if clean else 0.0,
    }


# ---------------------------------------------------------------------------
# arms
# ---------------------------------------------------------------------------


def measure_arm(
    corpus: str,
    identifiers: Sequence[str],
    catalog_label: str,
    catalog_factory: Callable[[], GovernedDictionary],
    *,
    rounds: int,
    repeats: int,
    source: str,
) -> dict[str, Any]:
    """One (corpus, catalog) arm: work counts, stage times, and the parity check.

    Args:
        corpus: The corpus name, saved on the entry.
        identifiers: The corpus, in occurrence order.
        catalog_label: ``"empty"`` or ``"fixture"``.
        catalog_factory: Builds a vocabulary that has answered nothing.
        rounds: Independent decompositions behind the saved share and its spread.
        repeats: Timed passes per stage within a round.
        source: The cache file, or a description of how a synthetic arm was made.

    Returns:
        The saveable entry.
    """
    counts = work_counts(identifiers, catalog_factory())
    counts.update(stage_phrase_counts(identifiers, catalog_factory()))
    counts.update(stage_class_word_counts(identifiers, catalog_factory()))
    shares = decompose(identifiers, catalog_factory, rounds=rounds, repeats=repeats)
    mismatches = verify_phrase_parity(identifiers, catalog_factory)

    entry: dict[str, Any] = {
        "corpus": corpus,
        "catalog": catalog_label,
        "source": source,
        "identifiers": len(identifiers),
        "distinct_identifiers": len(set(identifiers)),
        "distinct_identifiers_pct": round(100.0 * len(set(identifiers)) / len(identifiers), 2),
        "phrase_mismatches": mismatches,
        "machine": machine_note(),
        "stage_repeats": repeats,
    }
    entry.update(counts)
    entry.update(shares)
    entry["catalog_lookups_per_identifier"] = round(counts["catalog_lookups"] / len(identifiers), 3)
    entry["stage_catalog_lookup_excess"] = (
        counts["stage_catalog_lookups"] - counts["catalog_lookups"]
    )
    entry["stage_tokenizer_pass_excess"] = (
        counts["stage_tokenizer_passes"] - counts["tokenizer_passes"]
    )
    entry["stage_class_word_lookup_excess"] = (
        counts["stage_class_word_lookups"] - counts["class_word_lookups"]
    )
    entry["provenance_records_constructed"] = (
        counts["token_expansions_constructed"] + counts["identifier_expansions_constructed"]
    )
    entry["provenance_records_per_identifier"] = round(
        float(entry["provenance_records_constructed"]) / len(identifiers), 3
    )
    entry["python_calls_per_identifier"] = round(counts["python_calls_total"] / len(identifiers), 2)
    entry["catalog_memo_hit_pct"] = (
        round(100.0 * counts["catalog_memo_hits"] / counts["catalog_lookups"], 2)
        if counts["catalog_lookups"]
        else 0.0
    )
    entry["expansion_memo_hit_pct"] = (
        round(100.0 * counts["expansion_memo_hits"] / counts["token_expands"], 2)
        if counts["token_expands"]
        else 0.0
    )

    total = float(entry["full_ns"])
    entry["ns_per_identifier"] = round(total / len(identifiers), 1)
    entry["identifiers_per_second"] = round(len(identifiers) / (total / 1e9))
    return entry


def inherited_counts(socrata: Sequence[str], sec_xbrl: Sequence[str]) -> dict[str, Any]:
    """Re-derive the two corpus counts this phase inherited as claims.

    Both come from ``docs/AUDIT-2026-08.md``, both were quoted onward, and
    neither population was ever saved. This entry is what "verify both counts;
    they are inherited claims" produces when one of them reproduces as a
    different number and the other one has no corpus behind it at all.

    Args:
        socrata: The Socrata identifiers, in occurrence order.
        sec_xbrl: The SEC XBRL identifiers, in occurrence order.

    Returns:
        The saveable entry.
    """
    union = set(socrata) | set(sec_xbrl)
    return {
        "socrata_pairs_claimed": INHERITED_SOCRATA_PAIRS,
        "socrata_pairs_measured": len(socrata),
        "socrata_pairs_shortfall": INHERITED_SOCRATA_PAIRS - len(socrata),
        "socrata_pairs_shortfall_pct": round(
            100.0 * (INHERITED_SOCRATA_PAIRS - len(socrata)) / INHERITED_SOCRATA_PAIRS, 2
        ),
        "identifier_corpus_claimed": INHERITED_IDENTIFIER_CORPUS,
        "identifier_corpus_sources_claimed": INHERITED_IDENTIFIER_SOURCES,
        "identifier_corpus_sources_present": len(SNAPSHOTS),
        "identifier_corpus_best_reconstruction": len(union),
        "identifier_corpus_reconstruction_pct": round(
            100.0 * len(union) / INHERITED_IDENTIFIER_CORPUS, 2
        ),
        "socrata_distinct_identifiers": len(set(socrata)),
        "sec_xbrl_distinct_identifiers": len(set(sec_xbrl)),
        "sec_xbrl_rows": len(sec_xbrl),
    }


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------


def render_census(name: str, figures: dict[str, Any], tokens: str) -> list[str]:
    """Console lines for one census entry."""
    return [
        f"{name}",
        f"  identifiers            {int(figures['identifiers']):>10,}"
        f"   distinct {figures['distinct_identifiers_pct']:>6.2f} %"
        f"  ({int(figures['distinct_identifiers']):,})",
        f"  token occurrences      {int(figures['token_occurrences']):>10,}"
        f"   distinct {figures['distinct_tokens_pct']:>6.2f} %"
        f"  ({int(figures['distinct_tokens']):,})",
        f"  tokens per identifier  {figures['tokens_per_identifier']:>10.3f}",
        f"  top 1 / 5 / 20 / 100 tokens carry "
        f"{figures['top1_token_occurrence_pct']:.2f} / "
        f"{figures['top5_token_occurrence_pct']:.2f} / "
        f"{figures['top20_token_occurrence_pct']:.2f} / "
        f"{figures['top100_token_occurrence_pct']:.2f} % of occurrences",
        f"  tokens seen exactly once  {figures['token_hapax_pct_of_distinct']:.2f} % of distinct,"
        f" {figures['token_hapax_pct_of_occurrences']:.2f} % of occurrences",
        f"  commonest: {tokens}",
    ]


def render_arm(run_id: str, entry: dict[str, Any]) -> list[str]:
    """Console lines for one arm."""
    lines = [
        f"{run_id}",
        f"  identifiers {int(entry['identifiers']):,} "
        f"({entry['distinct_identifiers_pct']} % distinct), "
        f"phrase mismatches {entry['phrase_mismatches']}, "
        f"stage excess: lookups {entry['stage_catalog_lookup_excess']}, "
        f"class words {entry['stage_class_word_lookup_excess']}",
        "  WORK COUNTS (gated; machine-independent)",
        f"    tokenizer passes            {int(entry['tokenizer_passes']):>12,}"
        f"   (scans {int(entry['tokenizer_scans']):,})",
        f"    catalog lookups             {int(entry['catalog_lookups']):>12,}"
        f"   ({entry['catalog_lookups_per_identifier']} per identifier;"
        f" {int(entry['catalog_lookups_from_digit_rejoin']):,} from the digit rejoin)",
        f"    reached the index           {int(entry['catalog_index_decisions']):>12,}"
        f"   (catalog memo hit {entry['catalog_memo_hit_pct']} %)",
        f"    expansion memo hits         {int(entry['expansion_memo_hits']):>12,}"
        f"   ({entry['expansion_memo_hit_pct']} % of token expansions)",
        f"    provenance records built    {int(entry['provenance_records_constructed']):>12,}"
        f"   ({entry['provenance_records_per_identifier']} per identifier)",
        f"    python calls                {int(entry['python_calls_total']):>12,}"
        f"   ({entry['python_calls_per_identifier']} per identifier)",
        "  COST CENTRES (unarmed note; wall-clock, this machine only)",
    ]
    for centre, _, _ in CENTRES:
        lines.append(
            f"    {centre:<22}{entry[f'stage_{centre}_pct']:>8.2f} %"
            f"   (spread {entry[f'stage_{centre}_pct_min']:.2f} -"
            f" {entry[f'stage_{centre}_pct_max']:.2f})"
        )
    for centre, _, _ in PROVENANCE_SPLIT:
        lines.append(
            f"      of which {centre.replace('provenance_', ''):<11}"
            f"{entry[f'stage_{centre}_pct']:>8.2f} %"
            f"   (spread {entry[f'stage_{centre}_pct_min']:.2f} -"
            f" {entry[f'stage_{centre}_pct_max']:.2f})"
        )
    lines += [
        f"    median of {entry['decomposition_rounds']} decompositions;"
        f" full call {float(entry['full_ns']) / 1e6:.1f} ms",
        f"    {int(entry['ns_per_identifier'])} ns per identifier, "
        f"{int(entry['identifiers_per_second']):,} identifiers/s, "
        f"phrase-only is {entry['phrase_only_speedup']}x faster "
        f"({entry['phrase_only_speedup_min']} - {entry['phrase_only_speedup_max']})",
        f"    machine: {entry['machine']}",
    ]
    return lines


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument(
        "--only",
        choices=("all", "census", "callers", "arms", "overhead"),
        default="all",
        help=(
            "restrict the run. 'census' is the distinct-ratio measurement and needs no timing "
            "at all; 'callers' reads this repository's own call sites; 'arms' is the "
            "cost-centre decomposition; 'overhead' is what the counting profiler costs on this "
            "machine."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="cap each corpus at this many identifiers (0 = the whole corpus)",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=STAGE_REPEATS,
        help=f"timed passes per stage within a round; the fastest is taken "
        f"(default {STAGE_REPEATS})",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=DECOMPOSITION_ROUNDS,
        help=(
            "independent decompositions; the median share is saved and the spread is saved "
            f"beside it (default {DECOMPOSITION_ROUNDS}). One round is a point estimate of a "
            "quantity this runner has measured moving by ten points between runs."
        ),
    )
    args = parser.parse_args(argv)

    socrata, socrata_source, socrata_fetched = read_snapshot("socrata")
    sec_xbrl, sec_source, sec_fetched = read_snapshot("sec_xbrl")
    fixture_schema = fixture_schema_corpus(FIXTURE_SCHEMA_IDENTIFIERS)
    if args.limit:
        socrata = socrata[: args.limit]
        sec_xbrl = sec_xbrl[: args.limit]
        fixture_schema = fixture_schema[: args.limit]

    entries: dict[str, dict[str, Any]] = {}

    if args.only in ("all", "census"):
        entries["governed_perf.inherited_counts"] = inherited_counts(socrata, sec_xbrl)
        for name, corpus, source, fetched in (
            ("socrata", socrata, socrata_source, socrata_fetched),
            ("sec_xbrl", sec_xbrl, sec_source, sec_fetched),
            ("fixture_schema", fixture_schema, "bench fixture pool, seed 0", "n/a"),
        ):
            figures = census(corpus)
            tokens = top_tokens(corpus)
            entry = {**figures, "corpus": name, "source": source, "fetched_on": fetched}
            entry["top_tokens"] = tokens
            entries[f"governed_perf.{name}.census"] = entry
            print("\n".join(render_census(f"governed_perf.{name}.census", figures, tokens)))
            print()

    if args.only in ("all", "callers"):
        callers = caller_census()
        entries["governed_perf.caller_census"] = callers
        print("governed_perf.caller_census")
        for label, _ in CALLER_GROUPS:
            print(
                f"  {label:<8} {callers[f'{label}_sites']:>4} call sites, "
                f"{callers[f'{label}_classified']:>4} classified, "
                f"{callers[f'{label}_phrase_only']:>4} read only .phrase "
                f"({callers[f'{label}_phrase_only_pct']} %), "
                f"{callers[f'{label}_unclassified']:>4} unclassified"
            )
        print()

    if args.only in ("all", "arms"):
        arms = (
            ("governed_perf.socrata.empty", "socrata", socrata, "empty", socrata_source),
            ("governed_perf.socrata.fixture", "socrata", socrata, "fixture", socrata_source),
            ("governed_perf.sec_xbrl.empty", "sec_xbrl", sec_xbrl, "empty", sec_source),
            (
                "governed_perf.fixture_schema.fixture",
                "fixture_schema",
                fixture_schema,
                "fixture",
                "bench fixture pool, seed 0",
            ),
        )
        for run_id, corpus_name, corpus, catalog_label, source in arms:
            factory: Callable[[], GovernedDictionary] = (
                (lambda: GovernedDictionary({}))
                if catalog_label == "empty"
                else build_fixture_dictionary
            )
            entry = measure_arm(
                corpus_name,
                corpus,
                catalog_label,
                factory,
                rounds=args.rounds,
                repeats=args.repeats,
                source=source,
            )
            entries[run_id] = entry
            print("\n".join(render_arm(run_id, entry)))
            print()

    if args.only in ("all", "overhead"):
        sample = socrata[: min(len(socrata), 20_000)]
        overhead = profiler_overhead(sample, lambda: GovernedDictionary({}))
        overhead["machine"] = machine_note()
        entries["governed_perf.profiler_overhead"] = overhead
        print(
            f"governed_perf.profiler_overhead\n"
            f"  cProfile costs {overhead['profiler_cost_ratio']}x wall-clock over "
            f"{int(overhead['identifiers']):,} identifiers -- and zero on the counts,"
            " which is why the counts are what is gated."
        )
        print()

    if args.save:
        from run_extraction import save_results

        print(f"saved {len(entries)} run(s) to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
