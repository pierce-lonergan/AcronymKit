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
import contextlib
import cProfile
import csv
import dataclasses
import hashlib
import json
import os
import platform
import pstats
import random
import statistics
import sys
import threading
import time
from collections import Counter, OrderedDict
from pathlib import Path
from types import CodeType
from typing import Any, Callable, Iterator, Optional, Sequence

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
from acronymkit.governed.models import (  # noqa: E402
    IdentifierExpansion,
    TokenExpansion,
)
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


def replay_bounded(keys: Sequence[str], limit: int) -> tuple[int, int]:
    """Hits and clears from replaying ``keys`` through the shipped memo's rule.

    The shipped rule, exactly: a map that holds ``limit`` answers and **empties
    itself** when it fills. It has no eviction order, which
    :func:`~acronymkit.governed.dictionary._remember` documents as deliberate.
    What that costs is not derivable from a distinct count -- it depends on the
    order the keys arrive in -- so it is replayed rather than estimated.

    Args:
        keys: The corpus, in occurrence order, not deduplicated.
        limit: How many keys the map holds before it empties.

    Returns:
        ``(hits, clears)``.
    """
    memo: set[str] = set()
    hits = 0
    clears = 0
    for key in keys:
        if key in memo:
            hits += 1
            continue
        if len(memo) >= limit:
            memo.clear()
            clears += 1
        memo.add(key)
    return hits, clears


def replay_lru(keys: Sequence[str], limit: int) -> int:
    """Hits from replaying ``keys`` through an LRU map of the same size.

    The counterfactual :func:`~acronymkit.governed.dictionary._remember` declines
    to pay for. It is measured rather than argued about, because "an eviction
    order costs bookkeeping on every hit" is a statement about cost and says
    nothing at all about how many hits are being given up.

    Args:
        keys: The corpus, in occurrence order.
        limit: How many keys the map holds before it evicts the oldest.

    Returns:
        The hit count.
    """
    memo: OrderedDict[str, None] = OrderedDict()
    hits = 0
    for key in keys:
        if key in memo:
            memo.move_to_end(key)
            hits += 1
            continue
        if len(memo) >= limit:
            memo.popitem(last=False)
        memo[key] = None
    return hits


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
    identifier_bounded, identifier_clears = replay_bounded(
        identifiers, dictionary_module._IDENTIFIER_MEMO_LIMIT
    )
    token_bounded, token_clears = replay_bounded(tokens, dictionary_module._MEMO_LIMIT)
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
        # THE CEILING AND THE RESULT, SHIPPED SIDE BY SIDE, BECAUSE THE CEILING
        # READS LIKE THE RESULT AND IS ROUGHLY THREE TIMES IT AT IDENTIFIER
        # LEVEL. The *_repeat_pct pair is what an unbounded memo would serve:
        # arithmetic over the distinct count, and an upper bound nothing can
        # beat. The *_bounded_hit_pct pair is what the shipped map serves --
        # replayed in this corpus's own occurrence order through a map of the
        # shipped size that CLEARS when it fills. The *_lru_hit_pct pair is the
        # same size under least-recently-used eviction, which is the alternative
        # `_remember` declines to pay for; publishing it is what turns that
        # decision into a priced one.
        "identifier_repeat_pct": round(
            100.0 - 100.0 * len(identifier_counts) / len(identifiers), 2
        ),
        "identifier_memo_limit": dictionary_module._IDENTIFIER_MEMO_LIMIT,
        "identifier_memo_bounded_hit_pct": round(100.0 * identifier_bounded / len(identifiers), 2),
        "identifier_memo_clears": identifier_clears,
        "identifier_memo_lru_hit_pct": round(
            100.0
            * replay_lru(identifiers, dictionary_module._IDENTIFIER_MEMO_LIMIT)
            / len(identifiers),
            2,
        ),
        "token_repeat_pct": round(100.0 - 100.0 * len(token_counts) / occurrences, 2)
        if occurrences
        else 0.0,
        "token_memo_bounded_hit_pct": round(100.0 * token_bounded / occurrences, 2)
        if occurrences
        else 0.0,
        "token_memo_clears": token_clears,
        "token_memo_lru_hit_pct": round(
            100.0 * replay_lru(tokens, dictionary_module._MEMO_LIMIT) / occurrences, 2
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


@contextlib.contextmanager
def decomposition_memo_levels() -> Iterator[None]:
    """Turn the identifier memo off for the duration of a cost decomposition.

    **What this is for, stated so it cannot be read as hiding a level.** The four
    cost centres are obtained by timing five nested stages over the same corpus
    and subtracting. That construction measures the work *one call* does. An
    identifier memo does not make any of that work cheaper -- it removes calls,
    and it removes them from the shipped ``full`` stage only, because no stage
    below it holds a whole result to return. Left on, it would put ``full``
    *below* ``class_word`` on a repeating corpus and hand back a negative
    provenance centre; and where it did not, it would lower every count in the
    arm at once while leaving every share alone, which is exactly the shape
    operating rule 17 exists to catch.

    So the decomposition runs with the level off, every arm entry records
    ``memo_levels``, and what the level is worth is measured on its own by
    :func:`measure_memo_arm`.

    Yields:
        Nothing. The previous settings are restored on the way out, including on
        an exception, so a failed round cannot leave the process configured.
    """
    restore = dictionary_module._set_memo_levels(identifiers=False)
    try:
        yield
    finally:
        dictionary_module._set_memo_levels(**restore)


def _stage_remember(memo: dict[str, Any], key: str, answer: Any) -> Any:
    """Mirror ``dictionary._remember`` exactly, bound and clear included.

    The stages have to take the same number of catalog lookups as the shipped
    path or the subtraction is comparing two different amounts of work. That
    means mirroring the **bound**, not just the memo: the shipped maps clear when
    they fill, and a corpus with more distinct tokens than ``_MEMO_LIMIT`` --
    Socrata has six times as many -- re-resolves after every clear. An unbounded
    stage memo would take fewer lookups than the code it stands in for, and the
    excess check in :func:`measure_arm` is what would catch that.

    Args:
        memo: The stage's map.
        key: The surface token.
        answer: Whatever the stage is remembering.

    Returns:
        ``answer``, unchanged.
    """
    if len(memo) >= dictionary_module._MEMO_LIMIT:
        memo.clear()
    memo[key] = answer
    return answer


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
    known: dict[str, Any] = {}
    passed: dict[str, Any] = {}
    for name in identifiers:
        parts = split_identifier_parts(name)
        for token in rejoin(parts.tokens, catalog, policy):
            if token in known or token in passed:
                continue
            if catalog.resolve(token, policy) is not None:
                _stage_remember(known, token, True)
            else:
                _stage_remember(passed, token, True)


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
    known: dict[str, str] = {}
    passed: dict[str, str] = {}
    for name in identifiers:
        parts = split_identifier_parts(name)
        longs: list[str] = []
        for token in rejoin(parts.tokens, catalog, policy):
            remembered = known.get(token)
            if remembered is None:
                remembered = passed.get(token)
            if remembered is not None:
                longs.append(remembered)
                continue
            entry = catalog.resolve(token, policy)
            if entry is None:
                longs.append(_stage_remember(passed, token, title_case(token)))
            else:
                longs.append(_stage_remember(known, token, entry.canonical))
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
    known: dict[str, str] = {}
    passed: dict[str, str] = {}
    for name in identifiers:
        parts = split_identifier_parts(name)
        longs: list[str] = []
        for token in rejoin(parts.tokens, catalog, policy):
            remembered = known.get(token)
            if remembered is None:
                remembered = passed.get(token)
            if remembered is not None:
                longs.append(remembered)
                continue
            entry = catalog.resolve(token, policy)
            if entry is None:
                catalog.class_word_for(token)
                longs.append(_stage_remember(passed, token, title_case(token)))
            else:
                if not entry.class_word:
                    catalog.class_word_for(token)
                longs.append(_stage_remember(known, token, entry.canonical))
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


# ---------------------------------------------------------------------------
# inside the record block: what one provenance record costs, by construction
# route -- and the R19 identity gate over the route that ships
# ---------------------------------------------------------------------------
#
# The stage ablation above answers "how much of the call is provenance". It
# cannot answer "which part of provenance", because every stage below `full`
# builds no record at all and there is nothing between them to subtract. So this
# section replays, out of the expansion path, the exact constructor arguments
# the shipped call produced, and times four ROUTES over them.
#
# Replay rather than re-implementation, for the same reason the stages are
# checked three ways: a driver that re-walked the expansion path would be
# measuring a copy of `expand_identifier` and calling the difference a finding.
# What is replayed here is not a copy of anything -- it is the argument tuples
# the shipped path actually handed the constructors, captured from a real pass,
# and `capture_construction_arguments` cross-checks its own count against the
# profiler's `token_expansions_constructed` before a single figure is timed.
#
# THREE OF THE FOUR ROUTES ARE THE SHIPPED CODE, selected by the shipped switch:
#
#   full         `_new_token_expansion` with `_FAST_CONSTRUCTION = False`
#                -- the generated `__init__` and its per-field
#                `object.__setattr__`, then `__post_init__` and its validation.
#                This is what the subsystem did before this workstream.
#   init         the same, with `__post_init__` replaced by a no-op on the
#                shipped class for the duration of the timing. Isolates the
#                validation from the `__init__` machinery that calls it.
#   alloc        `_new_token_expansion` with `_FAST_CONSTRUCTION = True`
#                -- `object.__new__` and nine writes into the instance dict.
#                This is what the subsystem does now.
#   call_floor   a nine-argument function here that returns `None`. The only
#                bench-local route, and it has to be: no shipped function
#                evaluates these arguments and builds nothing. It prices the
#                call itself, so the three costs below are not inflated by it.
#
# The three differences are the constituents:
#
#   allocation      = alloc - call_floor
#   dataclass_init  = init  - alloc
#   validation      = full  - init
#
# R18: the shares above are wall-clock and are an unarmed note. What is gated is
# `field_writes`, and it is exact rather than derived. `object.__setattr__` is a
# slot wrapper and `cProfile` does not count it -- verified, not assumed, which
# is why this instrument exists at all -- so the builtin `object` is replaced,
# for the duration of a counting pass, by a proxy that increments and delegates:
# in `models.__dict__`, which is where `_freeze_sequences` and
# `_freeze_confidence` look it up, and in the closure cell the generated
# `__init__` reads it out of. Both are put back. If either mechanism is absent
# on the running interpreter -- `dataclasses` has not always used a closure --
# the count is reported as `None` rather than as a plausible number.


#: The nine-argument and six-argument shapes, read off the shipped dataclasses
#: rather than written down, so a field added to either record moves this figure
#: instead of leaving it stale.
TOKEN_FIELDS = tuple(field.name for field in dataclasses.fields(TokenExpansion))
IDENTIFIER_FIELDS = tuple(field.name for field in dataclasses.fields(IdentifierExpansion))

#: Names that exercise the fields the two real corpora do not. Every one of them
#: is a shape `tests/test_governed_perf_runner.py` already names as awkward: an
#: unaccounted character, a non-ASCII name that must leave the regex fast path, a
#: digit-leading catalog token, a quoted and a bracketed name, a name that
#: tokenises to nothing. They are appended to every identity arm, because a gate
#: run only over input whose `unaccounted` is always empty has not been shown
#: capable of failing on `unaccounted`.
IDENTITY_EXTRA_NAMES = (
    "",
    "   ",
    "___",
    "TXN_\U0001f600_ID",
    "PAY\u20acAMT",
    "ADDR_LINE_1",
    "E_9_1_1",
    "db.schema.TXN_ID",
    "caf\u00e9_id",
    "1MM_AMT",
    '"TXN_ID"',
    "[db].[COL]",
    "address2line1",
)


#: Field writes performed while a counting pass is installed.
_FIELD_WRITES = 0


def _counted_setattr(target: Any, name: str, value: Any) -> None:
    """Count one field write and perform it."""
    global _FIELD_WRITES
    _FIELD_WRITES += 1
    object.__setattr__(target, name, value)


def _counted_new(cls: type) -> Any:
    """Allocate, uncounted: an allocation is not a field write."""
    return object.__new__(cls)


#: Stands in for the builtin ``object`` while a pass is counted. Only two
#: attributes are ever read off it and both delegate: the governed models reach
#: ``object.__setattr__`` to write a field of a frozen record and
#: ``object.__new__`` to make one. Nothing is ever instantiated.
#:
#: Built with ``type()`` rather than a ``class`` statement on purpose. A class
#: statement defining ``__setattr__`` declares an override of ``object``'s own,
#: which the type checker is right to reject on the signature; this object is
#: not a subclass of anything and is never used as one, so the dictionary form
#: says what is meant.
_COUNTING_OBJECT = type(
    "_CountingObject",
    (),
    {"__setattr__": staticmethod(_counted_setattr), "__new__": staticmethod(_counted_new)},
)


def _builtins_object_cell(constructor: Any) -> Optional[Any]:
    """The closure cell a generated ``__init__`` reads ``object`` out of.

    Args:
        constructor: A dataclass-generated ``__init__``.

    Returns:
        The cell, or ``None`` if this interpreter's ``dataclasses`` does not use
        one -- in which case the field-write count is reported absent rather
        than guessed at.
    """
    code = constructor.__code__
    closure = constructor.__closure__ or ()
    for index, name in enumerate(code.co_freevars):
        if name == "__dataclass_builtins_object__" and index < len(closure):
            return closure[index]
    return None


def count_field_writes(runner: Callable[[], None]) -> Optional[int]:
    """Exact ``object.__setattr__`` calls performed by one pass.

    Args:
        runner: The pass to count. Called once.

    Returns:
        The count, or ``None`` when the interpreter does not expose the
        mechanism -- see :func:`_builtins_object_cell`.
    """
    global _FIELD_WRITES
    found = [
        _builtins_object_cell(TokenExpansion.__init__),
        _builtins_object_cell(IdentifierExpansion.__init__),
    ]
    cells = [cell for cell in found if cell is not None]
    if len(cells) != len(found):
        return None
    saved = [cell.cell_contents for cell in cells]
    shadowed = "object" in models_module.__dict__
    _FIELD_WRITES = 0
    try:
        models_module.__dict__["object"] = _COUNTING_OBJECT
        for cell in cells:
            cell.cell_contents = _COUNTING_OBJECT
        runner()
    finally:
        for cell, previous in zip(cells, saved):
            cell.cell_contents = previous
        if not shadowed:
            models_module.__dict__.pop("object", None)
    return _FIELD_WRITES


def capture_construction_arguments(
    identifiers: Sequence[str], catalog: GovernedDictionary
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]], list[IdentifierExpansion]]:
    """Every argument tuple the shipped path handed a constructor, in order.

    A token record the expansion memo served twice was constructed once, so the
    token arguments are deduplicated **by object identity** rather than by value:
    two equal records built separately are two constructions and must be replayed
    twice, and one record returned twice is one construction and must not.

    **The identifier memo is forced off here**, under
    :func:`decomposition_memo_levels`, for the same reason the cost decomposition
    forces it off: this function is about what *constructing* a record costs, and
    a level that returns a finished record for a repeated name removes the
    construction rather than making it cheaper. Left on, a corpus with one
    repeated identifier would hand back the same object twice and every route
    replaying these arguments would be replaying a different amount of work from
    the one the shipped path did.

    Args:
        identifiers: The corpus, in occurrence order.
        catalog: A vocabulary that has answered nothing.

    Returns:
        The token argument tuples, the identifier argument tuples, and the
        results themselves -- returned because they own the objects whose
        ``id()`` the deduplication used.
    """
    with decomposition_memo_levels():
        results = [expand_identifier(name, catalog) for name in identifiers]
    seen: set[int] = set()
    token_args: list[tuple[Any, ...]] = []
    identifier_args: list[tuple[Any, ...]] = []
    for result in results:
        for token in result.tokens:
            if id(token) in seen:
                continue
            seen.add(id(token))
            token_args.append(tuple(getattr(token, name) for name in TOKEN_FIELDS))
        identifier_args.append(tuple(getattr(result, name) for name in IDENTIFIER_FIELDS))
    return token_args, identifier_args, results


def _floor_token(
    raw: Any,
    long: Any,
    is_known: Any,
    source: Any,
    entry_id: Any,
    confidence: Any,
    class_word: Any,
    beat: Any,
    kind: Any,
) -> None:
    """Take a token record's nine arguments and build nothing."""


def _floor_identifier(
    identifier: Any,
    phrase: Any,
    tokens: Any,
    class_word: Any,
    is_fully_known: Any,
    unaccounted: Any,
) -> None:
    """Take an identifier record's six arguments and build nothing."""


def replay(
    token_args: Sequence[tuple[Any, ...]],
    identifier_args: Sequence[tuple[Any, ...]],
    make_token: Callable[..., Any],
    make_identifier: Callable[..., Any],
    sink: Optional[list[Any]] = None,
) -> None:
    """Rebuild every captured record once, through one route.

    Args:
        token_args: The captured token argument tuples.
        identifier_args: The captured identifier argument tuples.
        make_token: The token route.
        make_identifier: The identifier route.
        sink: Collects the identifier records, for the parity check. ``None``
            while timing.
    """
    for arguments in token_args:
        make_token(*arguments)
    if sink is None:
        for arguments in identifier_args:
            make_identifier(*arguments)
    else:
        for arguments in identifier_args:
            sink.append(make_identifier(*arguments))


#: The four routes, cheapest first, as ``(label, fast_construction, post_init)``.
#: ``fast_construction`` is what :data:`acronymkit.governed.models._FAST_CONSTRUCTION`
#: is set to; ``post_init`` is whether ``__post_init__`` stays on the class.
#: ``call_floor`` is the one route that is not the shipped builder at all.
RECORD_ROUTES = (
    ("call_floor", None, True),
    ("alloc", True, True),
    ("init", False, False),
    ("full", False, True),
)

#: Which subtraction names which constituent of one record's cost.
RECORD_CONSTITUENTS = (
    ("allocation", "alloc", "call_floor"),
    ("dataclass_init", "init", "alloc"),
    ("validation", "full", "init"),
)


def _no_post_init(self: Any) -> None:
    """Replace ``__post_init__`` for the ``init`` route. Validates nothing."""


def time_route(
    label: str,
    token_args: Sequence[tuple[Any, ...]],
    identifier_args: Sequence[tuple[Any, ...]],
    repeats: int,
) -> int:
    """Fastest of ``repeats`` replays through one route, in nanoseconds.

    The shipped module flag and, for the ``init`` route, the shipped classes'
    ``__post_init__`` are moved for the duration and put back in a ``finally``.

    Args:
        label: One of :data:`RECORD_ROUTES`.
        token_args: The captured token argument tuples.
        identifier_args: The captured identifier argument tuples.
        repeats: Timed passes; the fastest is taken.

    Returns:
        The minimum elapsed nanoseconds.
    """
    make_token, make_identifier = _route_functions(label)
    with _route_installed(label):
        samples = []
        for _ in range(repeats):
            started = time.perf_counter_ns()
            replay(token_args, identifier_args, make_token, make_identifier)
            samples.append(time.perf_counter_ns() - started)
    return min(samples)


def _route_functions(label: str) -> tuple[Callable[..., Any], Callable[..., Any]]:
    """The pair of constructors one route uses."""
    if label == "call_floor":
        return _floor_token, _floor_identifier
    return models_module._new_token_expansion, models_module._new_identifier_expansion


@contextlib.contextmanager
def _route_installed(label: str) -> Iterator[None]:
    """Put the shipped module into the state one route names, then put it back."""
    flags = {name: flag for name, flag, _ in RECORD_ROUTES}
    keeps = {name: keep for name, _, keep in RECORD_ROUTES}
    wanted = flags[label]
    saved_flag = models_module._FAST_CONSTRUCTION
    saved_post = (TokenExpansion.__post_init__, IdentifierExpansion.__post_init__)
    try:
        if wanted is not None:
            models_module._FAST_CONSTRUCTION = wanted
        if not keeps[label]:
            TokenExpansion.__post_init__ = _no_post_init  # type: ignore[method-assign]
            IdentifierExpansion.__post_init__ = _no_post_init  # type: ignore[method-assign]
        yield
    finally:
        models_module._FAST_CONSTRUCTION = saved_flag
        TokenExpansion.__post_init__ = saved_post[0]  # type: ignore[method-assign]
        IdentifierExpansion.__post_init__ = saved_post[1]  # type: ignore[method-assign]


def route_parity(
    token_args: Sequence[tuple[Any, ...]],
    identifier_args: Sequence[tuple[Any, ...]],
    reference: Sequence[IdentifierExpansion],
) -> dict[str, int]:
    """Records each route rebuilds that do not match the shipped pass, by ``repr``.

    ``repr`` rather than ``==``: a dataclass's generated equality compares field
    values and would call a ``beat`` that stayed a ``list`` equal to one that is a
    ``tuple``. The generated ``repr`` prints the difference, and so does
    ``to_json`` for everything the wire contract carries -- both are compared.

    Args:
        token_args: The captured token argument tuples.
        identifier_args: The captured identifier argument tuples.
        reference: The records the shipped pass produced, in order.

    Returns:
        ``{label: mismatches}``. Anything but zero invalidates that route.
    """
    mismatches: dict[str, int] = {}
    for label, _, _ in RECORD_ROUTES:
        if label == "call_floor":
            continue
        make_token, make_identifier = _route_functions(label)
        rebuilt: list[Any] = []
        with _route_installed(label):
            replay(token_args, identifier_args, make_token, make_identifier, rebuilt)
        wrong = 0
        for produced, expected in zip(rebuilt, reference):
            if repr(produced) != repr(expected) or produced.to_json() != expected.to_json():
                wrong += 1
        mismatches[label] = wrong
    return mismatches


def record_costs(
    corpus: str,
    identifiers: Sequence[str],
    catalog_label: str,
    catalog_factory: Callable[[], GovernedDictionary],
    *,
    rounds: int,
    repeats: int,
    source: str,
) -> dict[str, Any]:
    """Decompose one provenance record's cost into its constituents.

    Args:
        corpus: The corpus name.
        identifiers: The corpus, in occurrence order.
        catalog_label: ``"empty"`` or ``"fixture"``.
        catalog_factory: Builds a vocabulary that has answered nothing.
        rounds: Independent decompositions; the median share is saved.
        repeats: Timed replays per route within a round.
        source: The cache file, or how a synthetic arm was made.

    Returns:
        The saveable entry.

    Raises:
        SystemExit: If the captured construction count disagrees with the
            profiler's, which means the replay is not the pass it claims to be.
    """
    token_args, identifier_args, reference = capture_construction_arguments(
        identifiers, catalog_factory()
    )
    # Counted under the SAME memo configuration the capture ran under. The
    # capture forces the identifier level off because this measurement is about
    # what constructing a record costs, and a level that returns a finished
    # record removes the construction rather than making it cheaper. Counting
    # with the level on would compare a distinct-identifier construction count
    # against a per-call one, and the guard below would fire on the mismatch
    # between two correct numbers.
    with decomposition_memo_levels():
        counted = work_counts(identifiers, catalog_factory())
    if len(token_args) != counted["token_expansions_constructed"]:
        raise SystemExit(
            f"{corpus}/{catalog_label}: captured {len(token_args):,} token constructions, "
            f"the profiler counted {counted['token_expansions_constructed']:,}. The replay is "
            "not the pass it claims to be and no figure from it may be saved."
        )
    if len(identifier_args) != counted["identifier_expansions_constructed"]:
        raise SystemExit(
            f"{corpus}/{catalog_label}: captured {len(identifier_args):,} identifier "
            f"constructions against {counted['identifier_expansions_constructed']:,} profiled."
        )

    observed: list[dict[str, float]] = []
    for _ in range(rounds):
        elapsed = {
            label: time_route(label, token_args, identifier_args, repeats)
            for label, _, _ in RECORD_ROUTES
        }
        total = elapsed["full"]
        figures = {
            "route_full_ns": float(total),
            "call_floor_pct": 100.0 * elapsed["call_floor"] / total if total else 0.0,
        }
        for name, upper, lower in RECORD_CONSTITUENTS:
            figures[name] = 100.0 * (elapsed[upper] - elapsed[lower]) / total if total else 0.0
        figures["shipped_route_speedup"] = total / elapsed["alloc"] if elapsed["alloc"] else 0.0
        observed.append(figures)

    entry: dict[str, Any] = {
        "corpus": corpus,
        "catalog": catalog_label,
        "source": source,
        "machine": machine_note(),
        "identifiers": len(identifiers),
        "decomposition_rounds": rounds,
        "route_repeats": repeats,
        "token_records_replayed": len(token_args),
        "identifier_records_replayed": len(identifier_args),
        "records_replayed": len(token_args) + len(identifier_args),
        "token_fields": len(TOKEN_FIELDS),
        "identifier_fields": len(IDENTIFIER_FIELDS),
    }
    for field in (
        "call_floor_pct",
        "allocation",
        "dataclass_init",
        "validation",
        "shipped_route_speedup",
        "route_full_ns",
    ):
        values = sorted(round_figures[field] for round_figures in observed)
        places = 3 if field == "shipped_route_speedup" else (0 if field.endswith("_ns") else 2)
        name = field if field.endswith(("_pct", "_ns", "_speedup")) else f"{field}_pct"
        entry[name] = round(statistics.median(values), places)
        entry[f"{name}_min"] = round(values[0], places)
        entry[f"{name}_max"] = round(values[-1], places)

    for label, mismatched in route_parity(token_args, identifier_args, reference).items():
        entry[f"route_{label}_record_mismatches"] = mismatched

    for label in ("alloc", "full"):
        make_token, make_identifier = _route_functions(label)

        def one_pass(
            make_token: Callable[..., Any] = make_token,
            make_identifier: Callable[..., Any] = make_identifier,
        ) -> None:
            replay(token_args, identifier_args, make_token, make_identifier)

        with _route_installed(label):
            entry[f"field_writes_{label}"] = count_field_writes(one_pass)
    writes_full = entry["field_writes_full"]
    writes_alloc = entry["field_writes_alloc"]
    if writes_full is not None and writes_alloc is not None:
        entry["field_writes_removed"] = writes_full - writes_alloc
        entry["field_writes_per_record_full"] = round(writes_full / entry["records_replayed"], 3)
    entry.update(route_validation_counts(token_args, identifier_args))
    return entry


def route_validation_counts(
    token_args: Sequence[tuple[Any, ...]], identifier_args: Sequence[tuple[Any, ...]]
) -> dict[str, int]:
    """What ``__post_init__`` costs the ``full`` route, counted rather than derived.

    Taken from a profiled replay through the ``full`` route rather than from the
    shipped pass, because the shipped pass no longer validates anything on this
    path: the number wanted here is what the route being replaced did, and the
    only place that route still runs is inside this runner.

    One ``problems`` list is allocated per helper call, so the helper call count
    **is** the list-allocation count.

    Args:
        token_args: The captured token argument tuples.
        identifier_args: The captured identifier argument tuples.

    Returns:
        Helper calls, and the list allocations they imply, for the ``full``
        route.
    """
    make_token, make_identifier = _route_functions("full")
    profiler = cProfile.Profile()
    with _route_installed("full"):
        profiler.enable()
        replay(token_args, identifier_args, make_token, make_identifier)
        profiler.disable()
    stats = pstats.Stats(profiler).stats  # type: ignore[attr-defined]

    def calls(function: object) -> int:
        key = _key(function)
        return int(stats[key][1]) if key in stats else 0

    sequences = calls(models_module._freeze_sequences)
    confidences = calls(models_module._freeze_confidence)
    return {
        "full_route_sequence_validations": sequences,
        "full_route_confidence_validations": confidences,
        "full_route_list_allocations": sequences + confidences,
        "full_route_items_normalisations": calls(models_module._items),
        "full_route_unit_interval_checks": calls(models_module._unit_interval),
    }


def render_record_costs(run_id: str, entry: dict[str, Any]) -> list[str]:
    """Console lines for one record-cost entry."""
    lines = [
        run_id,
        f"  {int(entry['records_replayed']):,} records replayed "
        f"({int(entry['token_records_replayed']):,} token + "
        f"{int(entry['identifier_records_replayed']):,} identifier), "
        f"route mismatches: alloc {entry['route_alloc_record_mismatches']}, "
        f"init {entry['route_init_record_mismatches']}, "
        f"full {entry['route_full_record_mismatches']}",
        "  WORK COUNTS (gated; machine-independent)",
        f"    object.__setattr__ calls, shipped-before  {entry['field_writes_full']:>12,}",
        f"    object.__setattr__ calls, shipped-after   {entry['field_writes_alloc']:>12,}",
        f"    list allocations inside __post_init__     "
        f"{int(entry['full_route_list_allocations']):>12,}",
        "  WHAT ONE RECORD COSTS (unarmed note; wall-clock, this machine only)",
        f"    the nine-argument call itself   {entry['call_floor_pct']:>7.2f} %"
        f"   ({entry['call_floor_pct_min']:.2f} - {entry['call_floor_pct_max']:.2f})",
        f"    allocation + filling __dict__   {entry['allocation_pct']:>7.2f} %"
        f"   ({entry['allocation_pct_min']:.2f} - {entry['allocation_pct_max']:.2f})",
        f"    the generated __init__          {entry['dataclass_init_pct']:>7.2f} %"
        f"   ({entry['dataclass_init_pct_min']:.2f} - {entry['dataclass_init_pct_max']:.2f})",
        f"    __post_init__ validation        {entry['validation_pct']:>7.2f} %"
        f"   ({entry['validation_pct_min']:.2f} - {entry['validation_pct_max']:.2f})",
        f"    replaying every record is {entry['shipped_route_speedup']}x faster through the "
        f"shipped route ({entry['shipped_route_speedup_min']} - "
        f"{entry['shipped_route_speedup_max']})",
        f"    machine: {entry['machine']}",
    ]
    return lines


def identity_digests(
    identifiers: Sequence[str], catalog_factory: Callable[[], GovernedDictionary]
) -> tuple[str, str, int, int]:
    """Digest every record one pass produces, two ways.

    Args:
        identifiers: The names to expand, in order.
        catalog_factory: Builds a vocabulary that has answered nothing.

    Returns:
        The ``repr`` digest, the ``to_json`` digest, the identifiers expanded and
        the token records seen.
    """
    catalog = catalog_factory()
    shapes = hashlib.blake2b(digest_size=16)
    wire = hashlib.blake2b(digest_size=16)
    tokens = 0
    for name in identifiers:
        result = expand_identifier(name, catalog)
        shapes.update(repr(result).encode("utf-8"))
        wire.update(result.to_json().encode("utf-8"))
        tokens += len(result.tokens)
    return shapes.hexdigest(), wire.hexdigest(), len(identifiers), tokens


def identity_control(
    identifiers: Sequence[str], catalog_factory: Callable[[], GovernedDictionary]
) -> tuple[str, str, bool]:
    """Digest the same stream with **one** ``entry_id`` of one token record moved.

    The positive control for :func:`identity_arm`. A digest comparison that has
    only ever reported "identical" is indistinguishable from one that cannot
    report anything else, and the failure this gate exists for is precisely the
    brief's: a change that moves one ``entry_id`` in ten million, which is
    catastrophic for a governance instrument and invisible to a benchmark. So
    the control **is** that failure: the first record with a token gets its
    first token's ``entry_id`` replaced, the rest of the corpus is untouched,
    and the whole stream is digested again.

    Args:
        identifiers: The same names, in the same order, as the two real passes.
        catalog_factory: Builds a vocabulary that has answered nothing.

    Returns:
        The ``repr`` digest, the ``to_json`` digest, and whether the probe
        actually fired -- because a control that never perturbed anything proves
        nothing at all.
    """
    catalog = catalog_factory()
    shapes = hashlib.blake2b(digest_size=16)
    wire = hashlib.blake2b(digest_size=16)
    fired = False
    for name in identifiers:
        result = expand_identifier(name, catalog)
        if not fired and result.tokens:
            moved = dataclasses.replace(result.tokens[0], entry_id="acronymkit-r19-probe")
            result = dataclasses.replace(result, tokens=(moved, *result.tokens[1:]))
            fired = True
        shapes.update(repr(result).encode("utf-8"))
        wire.update(result.to_json().encode("utf-8"))
    return shapes.hexdigest(), wire.hexdigest(), fired


def identity_arm(
    corpus: str,
    identifiers: Sequence[str],
    catalog_label: str,
    catalog_factory: Callable[[], GovernedDictionary],
    *,
    source: str,
) -> dict[str, Any]:
    """R19 for one arm: the whole corpus, forced on and forced off, compared.

    The comparison is on ``repr`` **and** on ``to_json``, because neither alone
    is sufficient: ``to_json`` renders a tuple and a list identically, and
    ``repr`` is not the wire contract. A control follows, in the same process on
    the same corpus, in which one field of one record is perturbed -- because a
    digest comparison that has only ever reported "identical" is
    indistinguishable from one that cannot report anything else.

    Args:
        corpus: The corpus name.
        identifiers: The corpus, plus :data:`IDENTITY_EXTRA_NAMES`.
        catalog_label: ``"empty"`` or ``"fixture"``.
        catalog_factory: Builds a vocabulary that has answered nothing.
        source: The cache file, or how a synthetic arm was made.

    Returns:
        The saveable entry.
    """
    saved = models_module._FAST_CONSTRUCTION
    try:
        models_module._FAST_CONSTRUCTION = False
        off = identity_digests(identifiers, catalog_factory)
        models_module._FAST_CONSTRUCTION = True
        on = identity_digests(identifiers, catalog_factory)
    finally:
        models_module._FAST_CONSTRUCTION = saved

    control = identity_control(identifiers, catalog_factory)

    return {
        "corpus": corpus,
        "catalog": catalog_label,
        "source": source,
        "machine": machine_note(),
        "identifiers_compared": on[2],
        "token_records_compared": on[3],
        "records_compared": on[2] + on[3],
        "extra_names": len(IDENTITY_EXTRA_NAMES),
        "repr_digest_forced_off": off[0],
        "repr_digest_forced_on": on[0],
        "json_digest_forced_off": off[1],
        "json_digest_forced_on": on[1],
        "repr_identical": off[0] == on[0],
        "json_identical": off[1] == on[1],
        "control_probe_fired": control[2],
        "control_repr_digest": control[0],
        "control_json_digest": control[1],
        "control_repr_differs": control[0] != on[0],
        "control_json_differs": control[1] != on[1],
    }


def construction_ab(
    corpus: str,
    identifiers: Sequence[str],
    catalog_label: str,
    catalog_factory: Callable[[], GovernedDictionary],
    *,
    rounds: int,
    repeats: int,
    source: str,
) -> dict[str, Any]:
    """The whole shipped call, forced on against forced off, with both work counts.

    The end-to-end figure, and the only one that answers R17 completely. A pass
    that got fast by not doing the work is indistinguishable from one that got
    fast by doing the work more cheaply -- unless the work counts are taken on
    both sides and compared. Every count here is taken twice, and every one of
    them except the ones that ARE the optimisation must come back identical.

    Args:
        corpus: The corpus name.
        identifiers: The corpus, in occurrence order.
        catalog_label: ``"empty"`` or ``"fixture"``.
        catalog_factory: Builds a vocabulary that has answered nothing.
        rounds: Independent timings; the median is saved.
        repeats: Timed passes per round; the fastest is taken.
        source: The cache file, or how a synthetic arm was made.

    Returns:
        The saveable entry.
    """
    saved = models_module._FAST_CONSTRUCTION
    elapsed: dict[str, list[int]] = {"on": [], "off": []}
    counts: dict[str, dict[str, int]] = {}
    writes: dict[str, Optional[int]] = {}
    try:
        for _ in range(rounds):
            for label, flag in (("off", False), ("on", True)):
                models_module._FAST_CONSTRUCTION = flag
                elapsed[label].append(time_stage(stage_full, identifiers, catalog_factory, repeats))
        for label, flag in (("off", False), ("on", True)):
            models_module._FAST_CONSTRUCTION = flag
            counts[label] = work_counts(identifiers, catalog_factory())
            catalog = catalog_factory()

            def one_pass(catalog: GovernedDictionary = catalog) -> None:
                stage_full(identifiers, catalog)

            writes[label] = count_field_writes(one_pass)
    finally:
        models_module._FAST_CONSTRUCTION = saved

    on = statistics.median(elapsed["on"])
    off = statistics.median(elapsed["off"])
    entry: dict[str, Any] = {
        "corpus": corpus,
        "catalog": catalog_label,
        "source": source,
        "machine": machine_note(),
        "identifiers": len(identifiers),
        "rounds": rounds,
        "stage_repeats": repeats,
        "forced_off_ns": float(off),
        "forced_on_ns": float(on),
        "forced_off_ns_min": float(min(elapsed["off"])),
        "forced_on_ns_min": float(min(elapsed["on"])),
        "speedup": round(off / on, 3) if on else 0.0,
        "call_removed_pct": round(100.0 * (off - on) / off, 2) if off else 0.0,
        "identifiers_per_second_forced_off": round(len(identifiers) / (off / 1e9)),
        "identifiers_per_second_forced_on": round(len(identifiers) / (on / 1e9)),
        "field_writes_forced_off": writes["off"],
        "field_writes_forced_on": writes["on"],
    }
    entry["field_writes_removed"] = (
        writes["off"] - writes["on"]
        if writes["off"] is not None and writes["on"] is not None
        else None
    )
    # Every count, on both sides. The ones that MUST move are the two validation
    # helpers and the two `__post_init__` methods; every other count is the work,
    # and the work is what may not have gone anywhere.
    moved = []
    for field in sorted(counts["off"]):
        entry[f"{field}_forced_off"] = counts["off"][field]
        entry[f"{field}_forced_on"] = counts["on"][field]
        if counts["off"][field] != counts["on"][field]:
            moved.append(field)
    entry["work_counts_compared"] = len(counts["off"])
    entry["work_counts_unchanged"] = len(counts["off"]) - len(moved)
    entry["work_counts_moved"] = ",".join(moved) if moved else ""
    return entry


def render_construction_ab(run_id: str, entry: dict[str, Any]) -> list[str]:
    """Console lines for one A/B entry."""
    return [
        run_id,
        f"  {int(entry['identifiers']):,} identifiers, median of {entry['rounds']} rounds",
        "  WORK COUNTS (gated; machine-independent)",
        f"    counts compared              {int(entry['work_counts_compared']):>12}"
        f"   ({int(entry['work_counts_unchanged'])} identical on both sides)",
        f"    counts that moved            {entry['work_counts_moved'] or 'none'}",
        f"    object.__setattr__ calls     {entry['field_writes_forced_on']:>12,}"
        f"   (forced off {entry['field_writes_forced_off']:,};"
        f" removed {entry['field_writes_removed']:,})",
        "  WALL-CLOCK (unarmed note; this machine only)",
        f"    forced off  {float(entry['forced_off_ns']) / 1e6:9.1f} ms"
        f"   {int(entry['identifiers_per_second_forced_off']):>9,} identifiers/s",
        f"    forced on   {float(entry['forced_on_ns']) / 1e6:9.1f} ms"
        f"   {int(entry['identifiers_per_second_forced_on']):>9,} identifiers/s",
        f"    {entry['speedup']}x, {entry['call_removed_pct']} % of the call removed",
        f"    machine: {entry['machine']}",
    ]


def render_identity(run_id: str, entry: dict[str, Any]) -> list[str]:
    """Console lines for one identity entry."""
    verdict = "IDENTICAL" if entry["repr_identical"] and entry["json_identical"] else "DIFFER"
    return [
        run_id,
        f"  {int(entry['records_compared']):,} records over "
        f"{int(entry['identifiers_compared']):,} identifiers, forced on against forced off",
        f"    repr     off {entry['repr_digest_forced_off']}  on {entry['repr_digest_forced_on']}",
        f"    to_json  off {entry['json_digest_forced_off']}  on {entry['json_digest_forced_on']}",
        f"    {verdict}"
        f"   (control: one entry_id moved in one record of "
        f"{int(entry['records_compared']):,} -- probe fired {entry['control_probe_fired']}, "
        f"repr moved {entry['control_repr_differs']}, "
        f"json moved {entry['control_json_differs']})",
    ]


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
    known: dict[str, str] = {}
    passed: dict[str, str] = {}
    mismatches = 0
    for name in identifiers:
        parts = split_identifier_parts(name)
        longs: list[str] = []
        for token in rejoin(parts.tokens, stage_catalog, policy):
            remembered = known.get(token)
            if remembered is None:
                remembered = passed.get(token)
            if remembered is not None:
                longs.append(remembered)
                continue
            entry = stage_catalog.resolve(token, policy)
            if entry is None:
                longs.append(_stage_remember(passed, token, title_case(token)))
            else:
                longs.append(_stage_remember(known, token, entry.canonical))
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
    "catalog_lookups": GovernedDictionary.resolve,
    "catalog_index_decisions": GovernedDictionary._decide,
    "class_word_lookups": GovernedDictionary.class_word_for,
    "token_expands": expansion_module._expand,
    # THE RECORD COUNTS MOVED, AND THE MOVE IS THE OPTIMISATION.
    # These two used to be `TokenExpansion.__post_init__` and
    # `IdentifierExpansion.__post_init__`, because a validating `__post_init__`
    # ran exactly once per record and was the cheapest reliable place to count
    # one. It no longer runs on this path at all: the governed hot path builds
    # its records through `models._new_token_expansion` and
    # `models._new_identifier_expansion`, which write the fields straight into
    # the instance. So the counter follows the construction rather than the
    # validation, the two fields keep their meaning and their values, and the
    # guard below still fires if either builder is renamed or leaves the path.
    "token_expansions_constructed": models_module._new_token_expansion,
    "identifier_expansions_constructed": models_module._new_identifier_expansion,
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
    # Zero on this path, and zero IS the finding: `_FAST_CONSTRUCTION` routes
    # the two result DTOs around the generated `__init__` that calls
    # `__post_init__`, so no governed identifier expansion validates a sequence
    # or a confidence any more. Both helpers still run on every OTHER governed
    # record -- `GovernedEntry` at catalog load, `PhysicalName` on the reverse
    # direction, `ComplianceResult` -- which is why they are counted here rather
    # than deleted: a non-zero reading on an `expand_identifier` pass means the
    # switch is off or a fourth construction site appeared.
    "sequence_validations": models_module._freeze_sequences,
    "confidence_validations": models_module._freeze_confidence,
    "token_post_inits": models_module.TokenExpansion.__post_init__,
    "identifier_post_inits": models_module.IdentifierExpansion.__post_init__,
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

    Note:
        **The identifier memo is forced off for the whole of this arm, and the
        entry says so in ``memo_levels``.** This decomposition is of the work one
        call does, taken by subtracting nested stages; a memo that returns a
        finished result for a repeated identifier does not make any of that work
        cheaper, it removes calls. Left on, it would delete
        ``identifier_memo_bounded_hit_pct`` of the calls from every stage at once
        and the shares would be unchanged while every count fell -- which is the
        exact shape operating rule 17 exists to catch. What the level is worth is
        measured separately, in :func:`measure_memo_arm`.
    """
    with decomposition_memo_levels():
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
        "memo_levels": "resolved,expanded,passed",
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
# the memo arm: what each level is worth, with its hit rate beside it
# ---------------------------------------------------------------------------

#: The four memo configurations, cheapest first. ``vocabulary`` is what this
#: library shipped before Mandate III Phase B and is kept as the historical
#: control; ``full`` is the shipped default.
#:
#: They are cumulative on purpose. Turning one level off inside a stack that has
#: the others answers "what does this level add", which is the question, and it
#: is not the same question as "what would this level be worth alone".
MEMO_CONFIGURATIONS: tuple[tuple[str, dict[str, bool]], ...] = (
    ("none", {"resolved": False, "expanded": False, "passed": False, "identifiers": False}),
    ("vocabulary", {"resolved": True, "expanded": True, "passed": False, "identifiers": False}),
    ("token", {"resolved": True, "expanded": True, "passed": True, "identifiers": False}),
    ("full", {"resolved": True, "expanded": True, "passed": True, "identifiers": True}),
)


def memo_counts(identifiers: Sequence[str], catalog: GovernedDictionary) -> dict[str, Any]:
    """Work counts for one memo configuration, from the profiler.

    Operating rule 17: a throughput figure without a work count is a null
    result, and a memo is exactly the change that makes throughput rise because
    work stopped happening. So every field here is a count of something the code
    did, and the hit rates are derived from those counts rather than reported by
    the memo about itself.

    ``identifier_memo_hits`` is the identifier count minus the number of
    tokenizer passes, because :func:`~acronymkit.governed.expansion.expand_identifier`
    tokenises exactly once per call whose body runs and not at all on a call the
    identifier memo answers.

    Args:
        identifiers: The corpus, in occurrence order.
        catalog: A vocabulary that has answered nothing.

    Returns:
        The counts.
    """
    integers = work_counts(identifiers, catalog)
    total = len(identifiers)
    hits = total - integers["tokenizer_passes"]
    counts: dict[str, Any] = dict(integers)
    counts["identifier_memo_hits"] = hits
    counts["identifier_memo_hit_pct"] = round(100.0 * hits / total, 2) if total else 0.0
    counts["expansion_memo_hit_pct"] = (
        round(100.0 * integers["expansion_memo_hits"] / integers["token_expands"], 2)
        if integers["token_expands"]
        else 0.0
    )
    counts["provenance_records_constructed"] = (
        integers["token_expansions_constructed"] + integers["identifier_expansions_constructed"]
    )
    return counts


def time_pass(
    identifiers: Sequence[str],
    catalog_factory: Callable[[], GovernedDictionary],
    repeats: int,
) -> int:
    """Fastest of ``repeats`` full passes over the corpus, in nanoseconds.

    A fresh vocabulary per pass, so no pass is served an answer the previous one
    taught the dictionary -- otherwise the second repeat measures a warm memo and
    the minimum is taken over the warmest one.

    Args:
        identifiers: The corpus.
        catalog_factory: Builds a vocabulary that has answered nothing.
        repeats: How many passes.

    Returns:
        The fastest pass, in nanoseconds.
    """
    best = 0
    for index in range(max(1, repeats)):
        catalog = catalog_factory()
        start = time.perf_counter_ns()
        for name in identifiers:
            expand_identifier(name, catalog)
        elapsed = time.perf_counter_ns() - start
        best = elapsed if index == 0 else min(best, elapsed)
    return best


def measure_memo_arm(
    corpus: str,
    identifiers: Sequence[str],
    catalog_label: str,
    catalog_factory: Callable[[], GovernedDictionary],
    *,
    repeats: int,
    source: str,
) -> dict[str, Any]:
    """What each memo level is worth on one (corpus, catalog) arm.

    Every configuration in :data:`MEMO_CONFIGURATIONS` gets a counting pass and a
    timed pass, and every throughput figure in the entry has its hit rate and its
    work counts saved beside it under the same prefix.

    Args:
        corpus: The corpus name.
        identifiers: The corpus, in occurrence order.
        catalog_label: ``"empty"`` or ``"fixture"``.
        catalog_factory: Builds a vocabulary that has answered nothing.
        repeats: Timed passes per configuration; the fastest is taken.
        source: The cache file, or how a synthetic arm was made.

    Returns:
        The saveable entry.
    """
    total = len(identifiers)
    entry: dict[str, Any] = {
        "corpus": corpus,
        "catalog": catalog_label,
        "source": source,
        "identifiers": total,
        "distinct_identifiers": len(set(identifiers)),
        "machine": machine_note(),
        "repeats": repeats,
    }
    for name, levels in MEMO_CONFIGURATIONS:
        restore = dictionary_module._set_memo_levels(**levels)
        try:
            counts = memo_counts(identifiers, catalog_factory())
            elapsed = time_pass(identifiers, catalog_factory, repeats)
        finally:
            dictionary_module._set_memo_levels(**restore)
        for field in (
            "tokenizer_passes",
            "catalog_lookups",
            "provenance_records_constructed",
            "python_calls_total",
            "identifier_memo_hits",
            "identifier_memo_hit_pct",
            "expansion_memo_hits",
            "expansion_memo_hit_pct",
        ):
            entry[f"{name}_{field}"] = counts[field]
        entry[f"{name}_ns"] = elapsed
        entry[f"{name}_identifiers_per_second"] = round(total / (elapsed / 1e9))
    baseline = float(entry["none_ns"])
    for name, _ in MEMO_CONFIGURATIONS:
        entry[f"{name}_speedup_over_none"] = round(baseline / float(entry[f"{name}_ns"]), 3)
    return entry


# ---------------------------------------------------------------------------
# free threading: the collision, measured rather than argued
# ---------------------------------------------------------------------------

#: Thread counts swept. ``1`` is the denominator of every scaling ratio and is
#: run through the same threaded harness as the rest, so the ratio is not
#: comparing a threaded pass against a serial one.
THREAD_COUNTS = (1, 2, 4, 8, 16)

#: How many identifiers the threaded-answer agreement check compares. Capped
#: because it holds two full JSON renderings of every result in memory at once,
#: and because the property it tests -- that a shared memo under many threads
#: serves no wrong answer -- is a property of the code and not of the corpus
#: size. The count is saved on the entry, so nobody has to guess what it covered.
THREAD_AGREEMENT_LIMIT = 40_000

#: The three sharing arms.
#:
#: ``shared`` is what a service does today: one immutable vocabulary held on a
#: long-lived object, its memo shared by every thread. ``per_thread`` is the memo
#: made unshared by giving each thread its own vocabulary -- which is also what a
#: per-batch memo would be, and it costs a smaller working set per thread.
#: ``none`` removes the one piece of shared mutable state in the library, which
#: is the control that says how much of any scaling loss is the memo's.
SHARING_ARMS = ("shared", "per_thread", "none")


def thread_pass(
    partitions: Sequence[Sequence[str]],
    catalogs: Sequence[GovernedDictionary],
) -> int:
    """Run one partition per thread and return the wall-clock in nanoseconds.

    Args:
        partitions: One slice of the corpus per thread; together, the corpus.
        catalogs: One vocabulary per thread. The same object repeated is the
            shared arm; distinct objects are the per-thread arm.

    Returns:
        Nanoseconds from before the first thread starts to after the last joins.
    """

    def work(index: int) -> None:
        catalog = catalogs[index]
        for name in partitions[index]:
            expand_identifier(name, catalog)

    threads = [threading.Thread(target=work, args=(index,)) for index in range(len(partitions))]
    start = time.perf_counter_ns()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return time.perf_counter_ns() - start


def partition(identifiers: Sequence[str], count: int) -> list[Sequence[str]]:
    """Split a corpus into ``count`` contiguous slices.

    Contiguous rather than round-robin, because a schema export arrives table by
    table and a round-robin split would hand every thread the same distribution
    -- which is the flattering assumption for a per-thread memo.

    Args:
        identifiers: The corpus, in occurrence order.
        count: How many slices.

    Returns:
        The slices, in order. Every identifier appears exactly once.
    """
    size = len(identifiers)
    edges = [round(size * index / count) for index in range(count + 1)]
    return [identifiers[edges[index] : edges[index + 1]] for index in range(count)]


def thread_answers_agree(
    identifiers: Sequence[str],
    catalog_factory: Callable[[], GovernedDictionary],
    threads: int,
) -> int:
    """Count identifiers where a shared-memo threaded run disagrees with a serial one.

    The correctness half of the free-threading question, and on a build with no
    GIL it is not a formality: the memo is the library's only shared mutable
    structure, and ``_remember`` reads a length, may clear, and writes. This
    compares the **full JSON** of every result, not the phrase.

    Args:
        identifiers: The corpus.
        catalog_factory: Builds a vocabulary that has answered nothing.
        threads: How many threads to run.

    Returns:
        The mismatch count. Anything but zero invalidates the arm.
    """
    serial = catalog_factory()
    reference = [expand_identifier(name, serial).to_json() for name in identifiers]
    shared = catalog_factory()
    results: dict[int, str] = {}
    lock = threading.Lock()

    def work(slice_index: int, chunk: Sequence[tuple[int, str]]) -> None:
        rendered = [(index, expand_identifier(name, shared).to_json()) for index, name in chunk]
        with lock:
            results.update(dict(rendered))

    numbered = list(enumerate(identifiers))
    chunks = partition(numbered, threads)  # type: ignore[arg-type]
    workers = [
        threading.Thread(target=work, args=(index, chunk)) for index, chunk in enumerate(chunks)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    return sum(1 for index, expected in enumerate(reference) if results.get(index) != expected)


def measure_threads(
    corpus: str,
    identifiers: Sequence[str],
    catalog_label: str,
    catalog_factory: Callable[[], GovernedDictionary],
    *,
    repeats: int,
    source: str,
) -> dict[str, Any]:
    """Scaling over threads, for three sharing arms, with the hit rates beside it.

    **What is a ratio and what is a wall-clock, stated before the numbers.**
    Operating rule 18 puts nanoseconds outside the gate because they are a
    property of the runner. A scaling ratio is a ratio of two wall-clocks taken
    on the same machine minutes apart, so it is *less* machine-dependent than
    either but it is not machine-independent, and it is saved with the machine
    named for that reason. What is machine-independent here is the work: the
    identifiers processed, the distinct identifiers per partition, and the memo
    hit rate each partitioning admits.

    Args:
        corpus: The corpus name.
        identifiers: The corpus, in occurrence order.
        catalog_label: ``"empty"`` or ``"fixture"``.
        catalog_factory: Builds a vocabulary that has answered nothing.
        repeats: Timed passes per cell; the fastest is taken.
        source: The cache file, or how a synthetic arm was made.

    Returns:
        The saveable entry.
    """
    total = len(identifiers)
    entry: dict[str, Any] = {
        "corpus": corpus,
        "catalog": catalog_label,
        "source": source,
        "identifiers": total,
        "distinct_identifiers": len(set(identifiers)),
        "machine": machine_note(),
        "repeats": repeats,
        "gil_enabled": gil_enabled(),
        "interpreter": platform.python_version(),
        "logical_cpus": os.cpu_count() or 0,
        "thread_counts": ",".join(str(count) for count in THREAD_COUNTS),
    }
    for threads in THREAD_COUNTS:
        slices = partition(identifiers, threads)
        # The identifier-memo hit rate each partitioning admits, replayed through
        # the shipped bound. For `shared` the slices are concatenated, which is
        # ONE valid interleaving of the threads and not the one that happens;
        # for `per_thread` each slice gets its own map, which is exact.
        shared_hits, _ = replay_bounded(identifiers, dictionary_module._IDENTIFIER_MEMO_LIMIT)
        per_thread_hits = sum(
            replay_bounded(chunk, dictionary_module._IDENTIFIER_MEMO_LIMIT)[0] for chunk in slices
        )
        prefix = f"t{threads}"
        entry[f"{prefix}_identifiers_processed"] = sum(len(chunk) for chunk in slices)
        entry[f"{prefix}_shared_identifier_memo_hit_pct"] = round(100.0 * shared_hits / total, 2)
        entry[f"{prefix}_per_thread_identifier_memo_hit_pct"] = round(
            100.0 * per_thread_hits / total, 2
        )
        entry[f"{prefix}_none_identifier_memo_hit_pct"] = 0.0
        for arm in SHARING_ARMS:
            levels = dict.fromkeys(("resolved", "expanded", "passed", "identifiers"), arm != "none")
            restore = dictionary_module._set_memo_levels(**levels)
            try:
                best = 0
                for index in range(max(1, repeats)):
                    if arm == "per_thread":
                        catalogs: list[GovernedDictionary] = [
                            catalog_factory() for _ in range(threads)
                        ]
                    else:
                        catalogs = [catalog_factory()] * threads
                    elapsed = thread_pass(slices, catalogs)
                    best = elapsed if index == 0 else min(best, elapsed)
            finally:
                dictionary_module._set_memo_levels(**restore)
            entry[f"{prefix}_{arm}_ns"] = best
            entry[f"{prefix}_{arm}_identifiers_per_second"] = round(total / (best / 1e9))
    for arm in SHARING_ARMS:
        base = float(entry[f"t1_{arm}_ns"])
        for threads in THREAD_COUNTS:
            entry[f"t{threads}_{arm}_scaling"] = round(
                base / float(entry[f"t{threads}_{arm}_ns"]), 3
            )
    checked = identifiers[:THREAD_AGREEMENT_LIMIT]
    entry["thread_answer_identifiers_checked"] = len(checked)
    entry["thread_answer_mismatches"] = thread_answers_agree(
        checked, catalog_factory, max(THREAD_COUNTS)
    )
    return entry


def gil_enabled() -> bool:
    """Whether this interpreter is holding a global interpreter lock.

    Returns:
        ``True`` on a standard build and on a free-threading build started with
        the GIL re-enabled; ``False`` only where PEP 703 is actually in force.
        Read from the interpreter rather than from the version string, because a
        free-threading build can be run either way.
    """
    probe = getattr(sys, "_is_gil_enabled", None)
    return True if probe is None else bool(probe())


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


def MEMO_ARMS_TABLE(  # noqa: N802 - a table, named like the constant it stands in for
    socrata: Sequence[str],
    socrata_source: str,
    sec_xbrl: Sequence[str],
    sec_source: str,
    fixture_schema: Sequence[str],
) -> tuple[tuple[str, str, Sequence[str], str, str], ...]:
    """The (run id, corpus, identifiers, catalog, source) rows the memo arms sweep.

    A function rather than a module constant because the corpora are read at
    start-up and a constant would have to read them at import time, which would
    make ``--help`` depend on a fetched cache.

    Args:
        socrata: The Socrata corpus.
        socrata_source: Its cache file name.
        sec_xbrl: The SEC XBRL corpus.
        sec_source: Its cache file name.
        fixture_schema: The synthetic control corpus.

    Returns:
        The rows.
    """
    return (
        ("governed_perf.memo.socrata_empty", "socrata", socrata, "empty", socrata_source),
        ("governed_perf.memo.socrata_fixture", "socrata", socrata, "fixture", socrata_source),
        ("governed_perf.memo.sec_xbrl_empty", "sec_xbrl", sec_xbrl, "empty", sec_source),
        (
            "governed_perf.memo.fixture_schema_fixture",
            "fixture_schema",
            fixture_schema,
            "fixture",
            "bench fixture pool, seed 0",
        ),
    )


def render_memo_arm(run_id: str, entry: dict[str, Any]) -> list[str]:
    """Console lines for one memo arm, hit rate beside every throughput figure.

    Args:
        run_id: The saved run id.
        entry: The entry.

    Returns:
        The lines.
    """
    lines = [
        f"{run_id}  {int(entry['identifiers']):,} identifiers, "
        f"{int(entry['distinct_identifiers']):,} distinct, catalog={entry['catalog']}",
        "  level stack        id-memo   token-memo   lookups   records      names/s   x none",
    ]
    for name, _ in MEMO_CONFIGURATIONS:
        lines.append(
            f"  {name:<16} "
            f"{entry[f'{name}_identifier_memo_hit_pct']:>7.2f}% "
            f"{entry[f'{name}_expansion_memo_hit_pct']:>10.2f}% "
            f"{int(entry[f'{name}_catalog_lookups']):>9,} "
            f"{int(entry[f'{name}_provenance_records_constructed']):>9,} "
            f"{int(entry[f'{name}_identifiers_per_second']):>12,} "
            f"{entry[f'{name}_speedup_over_none']:>7.3f}"
        )
    return lines


def render_threads(run_id: str, entry: dict[str, Any]) -> list[str]:
    """Console lines for one threading arm.

    Args:
        run_id: The saved run id.
        entry: The entry.

    Returns:
        The lines.
    """
    gil = "GIL on" if entry["gil_enabled"] else "GIL OFF (PEP 703)"
    lines = [
        f"{run_id}  Python {entry['interpreter']}, {gil}, "
        f"{int(entry['logical_cpus'])} logical CPUs, "
        f"{int(entry['identifiers']):,} identifiers, catalog={entry['catalog']}",
        f"  answers under {max(THREAD_COUNTS)} threads sharing one memo: "
        f"{int(entry['thread_answer_mismatches']):,} mismatch(es) against a serial run",
        "  threads   shared x   per-thread x   no-memo x   shared hit%  per-thread hit%",
    ]
    for threads in THREAD_COUNTS:
        prefix = f"t{threads}"
        lines.append(
            f"  {threads:>7}   {entry[f'{prefix}_shared_scaling']:>8.3f}   "
            f"{entry[f'{prefix}_per_thread_scaling']:>12.3f}   "
            f"{entry[f'{prefix}_none_scaling']:>9.3f}   "
            f"{entry[f'{prefix}_shared_identifier_memo_hit_pct']:>10.2f}%  "
            f"{entry[f'{prefix}_per_thread_identifier_memo_hit_pct']:>14.2f}%"
        )
    return lines


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument(
        "--only",
        choices=(
            "all",
            "census",
            "callers",
            "arms",
            "records",
            "ab",
            "identity",
            "overhead",
            "memo",
            "threads",
        ),
        default="all",
        help=(
            "restrict the run. 'census' is the distinct-ratio measurement and needs no timing "
            "at all; 'callers' reads this repository's own call sites; 'arms' is the "
            "cost-centre decomposition; 'records' decomposes one provenance record's cost "
            "inside that centre; 'ab' times the whole call with the record builders forced "
            "on and forced off and takes every work count on both sides; 'identity' is the "
            "R19 gate -- the whole corpus, both routes, every field of every record "
            "compared; 'overhead' is what the counting profiler costs on this "
            "machine; 'memo' is what each memo level is worth with its hit rate beside it; "
            "'threads' is the scaling sweep, which is worth running under a free-threading "
            "interpreter and is saved under a run id that says which one it was."
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

    socrata_all, socrata_source, socrata_fetched = read_snapshot("socrata")
    sec_xbrl_all, sec_source, sec_fetched = read_snapshot("sec_xbrl")
    socrata: Sequence[str] = socrata_all
    sec_xbrl: Sequence[str] = sec_xbrl_all
    fixture_schema: Sequence[str] = fixture_schema_corpus(FIXTURE_SCHEMA_IDENTIFIERS)
    if args.limit:
        socrata = socrata[: args.limit]
        sec_xbrl = sec_xbrl[: args.limit]
        fixture_schema = fixture_schema[: args.limit]

    entries: dict[str, dict[str, Any]] = {}
    factory: Callable[[], GovernedDictionary]

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
            factory = (
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

    if args.only in ("all", "memo"):
        for run_id, corpus_name, corpus, catalog_label, source in MEMO_ARMS_TABLE(
            socrata, socrata_source, sec_xbrl, sec_source, fixture_schema
        ):
            factory = (
                (lambda: GovernedDictionary({}))
                if catalog_label == "empty"
                else build_fixture_dictionary
            )
            entry = measure_memo_arm(
                corpus_name,
                corpus,
                catalog_label,
                factory,
                repeats=args.repeats,
                source=source,
            )
            entries[run_id] = entry
            print("\n".join(render_memo_arm(run_id, entry)))
            print()

    if args.only in ("all", "threads"):
        suffix = "gil" if gil_enabled() else "freethreaded"
        for _, corpus_name, corpus, catalog_label, source in MEMO_ARMS_TABLE(
            socrata, socrata_source, sec_xbrl, sec_source, fixture_schema
        ):
            if catalog_label != "empty":
                continue
            factory = lambda: GovernedDictionary({})  # noqa: E731
            entry = measure_threads(
                corpus_name,
                corpus,
                catalog_label,
                factory,
                repeats=max(1, args.repeats),
                source=source,
            )
            run_id = f"governed_perf.threads.{suffix}.{corpus_name}"
            entries[run_id] = entry
            print("\n".join(render_threads(run_id, entry)))
            print()

    record_arms = (
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

    if args.only in ("all", "records"):
        for run_id, corpus_name, corpus, catalog_label, source in record_arms:
            record_factory: Callable[[], GovernedDictionary] = (
                (lambda: GovernedDictionary({}))
                if catalog_label == "empty"
                else build_fixture_dictionary
            )
            costs = record_costs(
                corpus_name,
                corpus,
                catalog_label,
                record_factory,
                rounds=args.rounds,
                repeats=args.repeats,
                source=source,
            )
            entries[f"{run_id}.record_costs"] = costs
            print("\n".join(render_record_costs(f"{run_id}.record_costs", costs)))
            print()

    if args.only in ("all", "ab"):
        for run_id, corpus_name, corpus, catalog_label, source in record_arms:
            ab_factory: Callable[[], GovernedDictionary] = (
                (lambda: GovernedDictionary({}))
                if catalog_label == "empty"
                else build_fixture_dictionary
            )
            ab = construction_ab(
                corpus_name,
                corpus,
                catalog_label,
                ab_factory,
                rounds=args.rounds,
                repeats=args.repeats,
                source=source,
            )
            entries[f"{run_id}.construction_ab"] = ab
            print("\n".join(render_construction_ab(f"{run_id}.construction_ab", ab)))
            print()

    if args.only in ("all", "identity"):
        for run_id, corpus_name, corpus, catalog_label, source in record_arms:
            identity_factory: Callable[[], GovernedDictionary] = (
                (lambda: GovernedDictionary({}))
                if catalog_label == "empty"
                else build_fixture_dictionary
            )
            identity = identity_arm(
                corpus_name,
                tuple(corpus) + IDENTITY_EXTRA_NAMES,
                catalog_label,
                identity_factory,
                source=source,
            )
            entries[f"{run_id}.identity"] = identity
            print("\n".join(render_identity(f"{run_id}.identity", identity)))
            print()
        failures = [
            run_id
            for run_id, entry in entries.items()
            if run_id.endswith(".identity")
            and not (
                entry["repr_identical"]
                and entry["json_identical"]
                and entry["control_probe_fired"]
                and entry["control_repr_differs"]
                and entry["control_json_differs"]
            )
        ]
        if failures:
            print(f"R19 FAILED on {', '.join(failures)}")
            return 1

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
