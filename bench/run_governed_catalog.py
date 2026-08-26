#!/usr/bin/env python3
"""Is a governed catalog worth anything on a real schema? The gated re-run.

Why this runner exists
----------------------
``docs/POSITIONING.md`` commits this library to being a governance instrument,
and its first reversal condition is *the lead is wrong if a catalog is worth
nothing on a real schema.* The only measurement anybody had taken of that was an
un-gated adversarial pass recorded at ``docs/AUDIT-2026-08.md`` section 3.1 --
a voted catalog scoring `48.60 %` exact against an empty catalog's `49.55 %` on
held-out Socrata portals. Un-gated figures may not be quoted into a scanned
document, so the reversal condition shipped with no number in it.

This file turns that comparison into run ids. It changes nothing about the
library; it measures the one thing ``bench/run_governed_gold.py`` structurally
cannot.

Why this is a second runner and not a flag on the first
-------------------------------------------------------
``bench/run_governed_gold.py``'s admission rule is *the caption's alphanumerics
case-fold equal to the identifier's.* That rule is the whole defence of the
segmentation figure -- it leaves a population where only cut placement can
differ -- and it is **the exact complement of the population this question
lives in.** A pair a catalog could help is a pair whose caption is *not* the
identifier's characters re-cut. So the gold runner's admission rule cannot be
reused here: applied to this question it admits an empty population, and the
answer would be `0/0`.

Its **scorer** is reused, and the reuse is demonstrated rather than asserted.
The gold runner scores a set of integer cut positions over a shared character
stream, which a populated catalog destroys the moment it rewrites ``QTY`` to
``Quantity``. What is scored here is the case-folded tuple of alphanumeric words
-- and on the population where both metrics are defined, they are the same
metric. ``--save`` writes that as a measurement of its own:
``governed_catalog.socrata.scorer_agreement`` re-scores every pair the gold
runner admits, both ways, and records the agreement count and both percentages.
Two scorers for one question is how a project acquires a number it later cannot
compare; one scorer with a published identity is how it avoids that.

What is compared
----------------
Two arms, both through the public entry point
``expand_identifier(identifier, catalog)``:

``empty``
    ``GovernedDictionary({})``. The arm every published governed figure is
    taken with.

``voted``
    A catalog inferred from the field/caption pairs of the **held-in** portals
    and applied to the **held-out** ones. Portal-disjoint, by the same
    :func:`~run_governed_gold.portal_half` digest the gold runner's robustness
    split uses, so no portal contributes a training vote and a scored pair.

The catalog is circular in the way the audit named: it is inferred from labels
of the same kind as the labels being scored. That is not fixable with public
data and it is exactly why reversal one asks for a proprietary glossary. What
the portal-disjoint split buys is that the circularity is at the *corpus* level
and not at the *pair* level.

The decomposition that decides the question
-------------------------------------------
Pooling this comparison over all pairs is what made the audit's figure
unreadable, because the two arms act on disjoint populations of very different
size. Every pair is classified once, by comparing the case-folded alphanumerics
of identifier and caption:

``identical``
    Same characters. The caption re-cuts the identifier and nothing else. **A
    catalog can only do damage here**, and this is most of the corpus.

``expansion``
    The identifier's characters are a subsequence of the caption's and the
    caption is longer -- the caption spells something out. **The live subset.**

``expansion_strict``
    ``expansion``, and additionally the token count matches the caption's word
    count and every token is a subsequence of its aligned word. The cleanest
    live pairs, and the only ones where a token-level score is well defined.

``other``
    Everything else: reordered, annotated, or a caption that *abbreviates* the
    identifier (``unit_number`` captioned ``Unit Num``). Nothing an expander can
    do reaches these.

On ``expansion`` and ``expansion_strict`` the empty arm scores `0.00 %` **by
construction, not by measurement** -- its output's alphanumerics are the
identifier's, and the gold's are not. That zero is a derivation and this runner
prints it as one; it is reported anyway because it is the positive control on
the harness, and a harness that produced a non-zero there would be broken.

The catalogs, and why there is a sweep
--------------------------------------
A vote is cast by aligning the identifier's tokens to the caption's words. Five
harvesting rules ship, because the answer must not depend on which one was
chosen:

``equal_count``
    Align only when the token count equals the word count. Every aligned pair
    votes, identity votes included, and the majority wins.
``consistent``
    ``equal_count``, keeping only votes where the token is a subsequence of the
    word.
``monotone``
    A leftmost-greedy monotone alignment where every token consumes one word and
    surplus caption words may be skipped, each token a subsequence of its word.
``abbrev_only``
    ``equal_count``, counting **only** votes where the word differs from the
    token. No identity vote can veto an abbreviation.
``abbrev_consistent``
    ``abbrev_only``, keeping only subsequence-consistent votes.

Each is swept over ``min_votes`` and ``min_share``. Every cell is saved. Two
cells are named in the report -- ``voted``, the reconstruction of the audit's
catalog, and ``eager``, whichever cell scores highest on the live subset, so the
catalog arm is quoted at its best rather than at a convenient setting.

What this does to the corpus's split declaration
------------------------------------------------
``bench/splits.toml`` declares ``socrata`` ``role = "held_out"``,
``contaminated = false``, and the reason it gives is that although the miss
decomposition was published, "nothing was selected on it: the runner has no
thresholds, no configuration and no arms to choose between." **This runner has
all three.** It sweeps forty catalog configurations against this corpus and
quotes a maximum over them. Nothing here is held-out evidence, every saved entry
carries ``selection_on_this_corpus = true`` saying so, and whether the manifest
entry should still read ``contaminated = false`` is a question for whoever owns
``bench/splits.toml``. It is reported here and not fixed here.

Corpus, and why the cache rather than the wire
-----------------------------------------------
``run_governed_gold.fetch_socrata_columns`` -- the same function, the same cache
file, the same population the gated segmentation figures were taken on. Passing
``--refresh`` walks a live catalog that has moved since, which makes the
comparison to ``governed_gold.socrata.*`` a comparison of two populations.

Usage::

    python bench/run_governed_catalog.py                 # report, record nothing
    python bench/run_governed_catalog.py --save          # record into bench/results.json
    python bench/run_governed_catalog.py --no-sweep      # named cells only, much faster
"""

from __future__ import annotations

import argparse
import collections
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(BENCH_DIR))


def _load_gold() -> Any:
    """Import ``bench/run_governed_gold.py`` by path.

    ``bench/`` is a directory of scripts and not a package, and making it one
    for this file's convenience would change the shape of the thing under test.
    Same mechanism ``tests/test_governed_gold.py`` uses to reach it.

    Returns:
        The imported module.
    """
    path = BENCH_DIR / "run_governed_gold.py"
    spec = importlib.util.spec_from_file_location("run_governed_gold", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise SystemExit(f"could not import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gold = _load_gold()

from acronymkit.governed import (  # noqa: E402
    EntryKind,
    ExpansionSource,
    GovernedDictionary,
    GovernedEntry,
    expand_identifier,
)
from acronymkit.governed.tokenizer import split_identifier  # noqa: E402

#: Harvesting rules, in the order the report prints them. See the module
#: docstring for what each one aligns.
MODES = ("equal_count", "consistent", "monotone", "abbrev_only", "abbrev_consistent")

#: The sweep. Forty cells per fold, all saved, none discarded.
SWEEP_MIN_VOTES = (1, 2, 3, 5)
SWEEP_MIN_SHARE = (0.5, 0.9)

#: The reconstruction of the audit's catalog: every aligned vote counts, a
#: token must be seen twice, and a simple majority wins.
VOTED_CELL = ("equal_count", 2, 0.5)

#: Subsets, in the order every table prints them.
SUBSETS = ("all", "identical", "expansion", "expansion_strict", "live", "other")


# ---------------------------------------------------------------------------
# the metric
# ---------------------------------------------------------------------------
def phrase_words(text: str) -> Tuple[str, ...]:
    """The case-folded alphanumeric words of ``text``.

    This is the whole metric. Two strings are *exact* when their word tuples are
    equal, which generalises ``run_governed_gold.cuts`` off the shared character
    stream that a populated catalog destroys: where both are defined -- the gold
    runner's admitted population -- they agree pair for pair, and
    ``governed_catalog.socrata.scorer_agreement`` records that they do.

    Punctuation separates words exactly as it does there, so
    ``Available-for-Sale`` is three words and not one.

    Args:
        text: A caption or a produced phrase.

    Returns:
        The words, case-folded, in order.
    """
    out: List[str] = []
    current: List[str] = []
    for character in text:
        if character.isalnum():
            current.append(character)
        elif current:
            out.append("".join(current))
            current = []
    if current:
        out.append("".join(current))
    return tuple(word.casefold() for word in out)


def is_subsequence(short: str, long: str) -> bool:
    """Whether every character of ``short`` occurs in ``long``, in order.

    The abbreviation-consistency test this package already applies in
    ``backronym.align``: it is necessary for ``short`` to be an abbreviation of
    ``long`` and it is not sufficient, which is why the classification it feeds
    is published as a *superset* of the truly abbreviated pairs.

    Args:
        short: The candidate abbreviation, case-folded by the caller.
        long: The candidate expansion, case-folded by the caller.

    Returns:
        True when ``short`` is a subsequence of ``long``.
    """
    iterator = iter(long)
    return all(character in iterator for character in short)


def tokens_of(identifier: str) -> Tuple[str, ...]:
    """The identifier's tokens, case-folded, as the shipped tokenizer cuts them."""
    return tuple(token.casefold() for token in split_identifier(identifier))


def classify(identifier: str, caption: str) -> str:
    """Which population this pair belongs to.

    Args:
        identifier: The machine name, as published.
        caption: The human caption, as published.

    Returns:
        One of ``identical``, ``expansion_strict``, ``expansion``, ``other``.
    """
    machine, human = gold.gold_key(identifier), gold.gold_key(caption)
    if machine == human:
        return "identical"
    if len(human) > len(machine) and is_subsequence(machine, human):
        tokens, words = tokens_of(identifier), phrase_words(caption)
        if len(tokens) == len(words) and all(
            is_subsequence(token, word) for token, word in zip(tokens, words)
        ):
            return "expansion_strict"
        return "expansion"
    return "other"


def align(identifier: str, caption: str, mode: str) -> Optional[List[Tuple[str, str]]]:
    """Token-to-word alignment for one training pair, under one harvesting rule.

    Args:
        identifier: The machine name.
        caption: The publisher's caption.
        mode: One of :data:`MODES`.

    Returns:
        The aligned ``(token, word)`` votes, or ``None`` when this pair casts no
        vote at all under this rule.
    """
    tokens, words = tokens_of(identifier), phrase_words(caption)
    if not tokens:
        return None
    if mode == "monotone":
        return _align_monotone(tokens, words)
    if len(tokens) != len(words):
        return None
    pairs = list(zip(tokens, words))
    if mode in ("consistent", "abbrev_consistent"):
        pairs = [(token, word) for token, word in pairs if is_subsequence(token, word)]
    if mode in ("abbrev_only", "abbrev_consistent"):
        pairs = [(token, word) for token, word in pairs if token != word]
    return pairs or None


def _align_monotone(tokens: Sequence[str], words: Sequence[str]) -> Optional[List[Tuple[str, str]]]:
    """Leftmost-greedy monotone alignment: every token consumes one word.

    Surplus caption words may be skipped; tokens may not. A token may align only
    to a word it is a subsequence of.
    """
    wanted, available = len(tokens), len(words)
    if wanted == 0 or wanted > available:
        return None
    out: List[Tuple[str, str]] = []
    cursor = 0
    for index, token in enumerate(tokens):
        still_needed = wanted - index
        found = None
        while cursor <= available - still_needed:
            if is_subsequence(token, words[cursor]):
                found = cursor
                break
            cursor += 1
        if found is None:
            return None
        out.append((token, words[found]))
        cursor = found + 1
    return out


# ---------------------------------------------------------------------------
# the catalog
# ---------------------------------------------------------------------------
@dataclass
class Catalog:
    """One inferred vocabulary, with the counts that say how it was made.

    Attributes:
        entries: The rows that can change an answer.
        identity_rows: Rows suppressed because the winning expansion *is* the
            token. They are counted rather than emitted because they cannot move
            the metric, and because the audit's `6,548`-row figure is only
            comparable with the two counts added together.
        distinct_tokens: Tokens that received at least one vote.
        harvested_pairs: Training pairs that cast at least one vote. The firing
            count for the harvest, per operating rule 12.
        training_pairs: Training pairs offered.
        mode: The harvesting rule.
        min_votes: Votes a token needed.
        min_share: Share of them the winner needed.
    """

    entries: List[GovernedEntry]
    identity_rows: int
    distinct_tokens: int
    harvested_pairs: int
    training_pairs: int
    mode: str
    min_votes: int
    min_share: float

    def as_dict(self) -> Dict[str, object]:
        """The published shape of this catalog's provenance."""
        return {
            "mode": self.mode,
            "min_votes": self.min_votes,
            "min_share": self.min_share,
            "acting_rows": len(self.entries),
            "identity_rows": self.identity_rows,
            "rows_including_identity": len(self.entries) + self.identity_rows,
            "distinct_tokens_voted_on": self.distinct_tokens,
            "harvested_training_pairs": self.harvested_pairs,
            "training_pairs": self.training_pairs,
            "harvest_rate_pct": (
                round(self.harvested_pairs / self.training_pairs * 100, 2)
                if self.training_pairs
                else None
            ),
        }


def build_catalog(
    training: Sequence[Tuple[str, str]], mode: str, min_votes: int, min_share: float
) -> Catalog:
    """Infer a catalog from the held-in portals' field/caption pairs.

    Args:
        training: Distinct ``(identifier, caption)`` pairs from the held-in half.
        mode: One of :data:`MODES`.
        min_votes: Total votes a token needs before it may produce a row.
        min_share: Share of those votes the winning expansion needs.

    Returns:
        The catalog and its provenance.
    """
    votes: Dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    harvested = 0
    for identifier, caption in training:
        aligned = align(identifier, caption, mode)
        if not aligned:
            continue
        harvested += 1
        for token, word in aligned:
            votes[token][word] += 1

    entries: List[GovernedEntry] = []
    identity = 0
    for token, counter in sorted(votes.items()):
        total = sum(counter.values())
        word, winning = counter.most_common(1)[0]
        if total < min_votes or winning / total < min_share:
            continue
        if word == token:
            identity += 1
            continue
        entries.append(
            GovernedEntry(
                token=token,
                canonical=word.title(),
                kind=EntryKind.APPROVED_ABBREV,
                entry_id=f"VOTED-{token}",
                source=ExpansionSource.GOVERNED,
            )
        )
    return Catalog(
        entries=entries,
        identity_rows=identity,
        distinct_tokens=len(votes),
        harvested_pairs=harvested,
        training_pairs=len(training),
        mode=mode,
        min_votes=min_votes,
        min_share=min_share,
    )


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------
@dataclass
class Cell:
    """Counters for one subset of one arm-versus-arm comparison.

    Attributes:
        pairs: Pairs scored.
        empty_exact: Pairs the empty catalog got exactly right.
        voted_exact: Pairs the voted catalog got exactly right.
        fired: Pairs where the two arms produced different word tuples. The
            firing count, per operating rule 12: a delta on a subset where this
            is zero did not come from the catalog.
        empty_only: Pairs only the empty arm got right.
        voted_only: Pairs only the voted arm got right.
    """

    pairs: int = 0
    empty_exact: int = 0
    voted_exact: int = 0
    fired: int = 0
    empty_only: int = 0
    voted_only: int = 0

    def add(self, *, empty_right: bool, voted_right: bool, moved: bool) -> None:
        """Fold one scored pair in."""
        self.pairs += 1
        self.empty_exact += int(empty_right)
        self.voted_exact += int(voted_right)
        self.fired += int(moved)
        self.empty_only += int(empty_right and not voted_right)
        self.voted_only += int(voted_right and not empty_right)

    def as_dict(self) -> Dict[str, Optional[float]]:
        """The published shape. An undefined ratio is ``null``, never ``0.0``."""
        if not self.pairs:
            return {
                "pairs": 0,
                "empty_exact_pct": None,
                "voted_exact_pct": None,
                "delta_points": None,
                "catalog_fired_pairs": 0,
                "catalog_fired_pct": None,
                "empty_only_correct": 0,
                "voted_only_correct": 0,
            }
        return {
            "pairs": self.pairs,
            # The raw counts travel beside the percentages because the rounded
            # delta cannot carry the sign of a small loss: a catalog that breaks
            # one pair in 31,348 rounds to -0.0, and -0.0 < 0 is False, so a
            # sweep counted on the percentage files three real losses as ties.
            # Every win/loss tally in this file is counted on these two integers.
            "empty_exact": self.empty_exact,
            "voted_exact": self.voted_exact,
            "empty_exact_pct": round(self.empty_exact / self.pairs * 100, 2),
            "voted_exact_pct": round(self.voted_exact / self.pairs * 100, 2),
            "delta_points": round((self.voted_exact - self.empty_exact) / self.pairs * 100, 2),
            "catalog_fired_pairs": self.fired,
            "catalog_fired_pct": round(self.fired / self.pairs * 100, 2),
            "empty_only_correct": self.empty_only,
            "voted_only_correct": self.voted_only,
        }


@dataclass
class Fold:
    """One portal-disjoint fold: a training half and a scored half.

    Attributes:
        name: e.g. ``fold_ab``.
        train_half: The portal half the catalog is inferred from.
        test_half: The portal half that is scored.
        training: Distinct pairs in the training half.
        scored: Distinct pairs in the scored half.
        train_portals: Portals behind the training half.
        test_portals: Portals behind the scored half.
        test_occurrences: Column occurrences behind the scored pairs.
    """

    name: str
    train_half: str
    test_half: str
    training: Sequence[Tuple[str, str]]
    scored: Sequence[Tuple[str, str]]
    train_portals: int
    test_portals: int
    test_occurrences: int


def score(
    fold: Fold,
    catalog: Catalog,
    buckets: Dict[Tuple[str, str], str],
    empty_phrases: Dict[Tuple[str, str], Tuple[str, ...]],
) -> Dict[str, object]:
    """Score one fold, empty arm against voted arm, decomposed by population.

    Args:
        fold: The fold.
        catalog: The catalog inferred from ``fold.training``.
        buckets: Pre-computed classification per pair.
        empty_phrases: Pre-computed empty-catalog output per pair. The empty arm
            does not depend on the catalog, so it is computed once for the whole
            sweep rather than once per cell.

    Returns:
        The entry that goes into ``bench/results.json``.
    """
    voted = GovernedDictionary(catalog.entries)
    cells: Dict[str, Cell] = {name: Cell() for name in SUBSETS}
    abbreviated = 0
    abbreviated_empty = 0
    abbreviated_voted = 0
    abbreviated_fired = 0

    for pair in fold.scored:
        identifier, caption = pair
        goldwords = phrase_words(caption)
        empty_out = empty_phrases[pair]
        voted_out = phrase_words(expand_identifier(identifier, voted).phrase)
        bucket = buckets[pair]
        sample = {
            "empty_right": empty_out == goldwords,
            "voted_right": voted_out == goldwords,
            "moved": empty_out != voted_out,
        }
        cells["all"].add(**sample)
        cells[bucket].add(**sample)
        if bucket in ("expansion", "expansion_strict"):
            cells["live"].add(**sample)
        if bucket == "expansion_strict":
            tokens = tokens_of(identifier)
            if len(tokens) == len(goldwords) == len(empty_out) == len(voted_out):
                for index, (token, word) in enumerate(zip(tokens, goldwords)):
                    if token == word:
                        continue
                    abbreviated += 1
                    abbreviated_empty += int(empty_out[index] == word)
                    abbreviated_voted += int(voted_out[index] == word)
                    abbreviated_fired += int(empty_out[index] != voted_out[index])

    entry: Dict[str, object] = {
        "corpus": "socrata",
        "arm": fold.name,
        "system": (
            "acronymkit.governed.expand_identifier, empty catalog against a "
            f"{len(catalog.entries)}-row catalog voted from held-in portals"
        ),
        "train_portal_half": fold.train_half,
        "test_portal_half": fold.test_half,
        "train_portals": fold.train_portals,
        "test_portals": fold.test_portals,
        "test_occurrences": fold.test_occurrences,
        "catalog": catalog.as_dict(),
        "abbreviated_tokens": {
            "tokens": abbreviated,
            "empty_correct": abbreviated_empty,
            "voted_correct": abbreviated_voted,
            "empty_correct_pct": (
                round(abbreviated_empty / abbreviated * 100, 2) if abbreviated else None
            ),
            "voted_correct_pct": (
                round(abbreviated_voted / abbreviated * 100, 2) if abbreviated else None
            ),
            "catalog_fired_tokens": abbreviated_fired,
        },
        "selection_on_this_corpus": True,
        "empty_arm_zero_on_live_is_a_derivation": True,
    }
    for name in SUBSETS:
        entry[name] = cells[name].as_dict()
    return entry


# ---------------------------------------------------------------------------
# the corpus
# ---------------------------------------------------------------------------
def load_folds(pages: int, *, refresh: bool) -> Tuple[List[Fold], Dict[str, object]]:
    """Read the Socrata cache and split it portal-disjointly.

    Args:
        pages: Catalog pages of 100 datasets, passed straight to the gold
            runner's fetcher so both runners read one cache file.
        refresh: Ignore the cache and walk the live catalog.

    Returns:
        The two folds, and the census entry.
    """
    envelope = gold.fetch_socrata_columns(pages, refresh=refresh)
    rows = envelope["payload"]
    assert isinstance(rows, list)
    usable = [
        row
        for row in rows
        if len(row) > 2 and row[0] and row[1] and gold.gold_key(row[0]) and gold.gold_key(row[1])
    ]

    halves: Dict[str, List[Sequence[str]]] = {"a": [], "b": []}
    for row in usable:
        halves[gold.portal_half(row[2])].append(row)

    pairs = {half: sorted({(row[0], row[1]) for row in halves[half]}) for half in ("a", "b")}
    portals = {half: len({row[2] for row in halves[half]}) for half in ("a", "b")}

    folds = [
        Fold(
            name=f"fold_{train}{test}",
            train_half=train,
            test_half=test,
            training=pairs[train],
            scored=pairs[test],
            train_portals=portals[train],
            test_portals=portals[test],
            test_occurrences=len(halves[test]),
        )
        for train, test in (("a", "b"), ("b", "a"))
    ]
    return folds, census(usable, str(envelope["fetched_on"]), pages)


def census(usable: Sequence[Sequence[str]], fetched_on: str, pages: int) -> Dict[str, object]:
    """How much of a real schema needs a catalog at all.

    This is the measurement that decides how to read everything else. If most of
    the corpus is already spelled out, a catalog winning nothing over the pooled
    population is weak evidence about catalogs and strong evidence about
    Socrata. It has no arms, no thresholds and nothing chosen.

    Args:
        usable: Every column occurrence with a non-empty identifier and caption.
        fetched_on: The cache's fetch date.
        pages: Catalog pages walked.

    Returns:
        The census entry.
    """
    distinct = sorted({(row[0], row[1]) for row in usable})
    buckets = {pair: classify(*pair) for pair in distinct}
    by_pair: collections.Counter[str] = collections.Counter(buckets.values())
    by_occurrence: collections.Counter[str] = collections.Counter(
        buckets[(row[0], row[1])] for row in usable
    )
    pairs_total, occurrences_total = len(distinct), len(usable)

    mismatch = sum(
        1
        for pair in distinct
        if buckets[pair] != "identical" and len(tokens_of(pair[0])) != len(phrase_words(pair[1]))
    )
    non_identical = pairs_total - by_pair["identical"]
    abbreviated_tokens = 0
    for identifier, caption in distinct:
        if buckets[(identifier, caption)] != "expansion_strict":
            continue
        abbreviated_tokens += sum(
            1 for token, word in zip(tokens_of(identifier), phrase_words(caption)) if token != word
        )

    live_pairs = by_pair["expansion"] + by_pair["expansion_strict"]
    live_occurrences = by_occurrence["expansion"] + by_occurrence["expansion_strict"]
    subsets: Dict[str, object] = {}
    for name in ("identical", "expansion", "expansion_strict", "other"):
        subsets[name] = {
            "pairs": by_pair[name],
            "pairs_pct": round(by_pair[name] / pairs_total * 100, 2),
            "occurrences": by_occurrence[name],
            "occurrences_pct": round(by_occurrence[name] / occurrences_total * 100, 2),
        }
    return {
        "corpus": "socrata",
        "arm": "census",
        "system": "population census, no arms and no thresholds",
        "source_url": gold.SOCRATA_URL,
        "fetched_on": fetched_on,
        "socrata_pages": pages,
        "distinct_pairs": pairs_total,
        "occurrences": occurrences_total,
        "portals": len({row[2] for row in usable}),
        "unabbreviated_pairs": by_pair["identical"],
        "unabbreviated_pairs_pct": round(by_pair["identical"] / pairs_total * 100, 2),
        "unabbreviated_occurrences": by_occurrence["identical"],
        "unabbreviated_occurrences_pct": round(
            by_occurrence["identical"] / occurrences_total * 100, 2
        ),
        "live_pairs": live_pairs,
        "live_pairs_pct": round(live_pairs / pairs_total * 100, 2),
        "live_occurrences": live_occurrences,
        "live_occurrences_pct": round(live_occurrences / occurrences_total * 100, 2),
        "subsets": subsets,
        "non_identical_pairs": non_identical,
        "token_word_count_mismatch_pairs": mismatch,
        "token_word_count_mismatch_pct": (
            round(mismatch / non_identical * 100, 2) if non_identical else None
        ),
        "abbreviated_tokens": abbreviated_tokens,
        "selection_on_this_corpus": True,
        **gold.LICENCES["socrata"],
    }


def scorer_agreement(pages: int, *, refresh: bool) -> Dict[str, object]:
    """Prove this file's scorer is the gold runner's scorer, where both are defined.

    Re-scores every pair ``run_governed_gold.admits`` admits, once with that
    runner's cut-set equality and once with this file's word-tuple equality, and
    records how often the two verdicts differ. They must not differ at all: on a
    shared character stream, equal cut sets and equal word tuples are the same
    statement. The percentage must reproduce
    ``governed_gold.socrata.columns.all.exact_pct`` to the digit.

    Args:
        pages: Catalog pages, passed to the gold runner's fetcher.
        refresh: Ignore the cache.

    Returns:
        The agreement entry.
    """
    envelope = gold.fetch_socrata_columns(pages, refresh=refresh)
    rows = envelope["payload"]
    assert isinstance(rows, list)
    admitted = sorted({(row[0], row[1]) for row in rows if gold.admits(row[0], row[1])})
    catalog = GovernedDictionary({})
    cut_exact = word_exact = agree = skew = 0
    for identifier, caption in admitted:
        produced = expand_identifier(identifier, catalog).phrase
        if gold.gold_key(produced) != gold.gold_key(caption):
            skew += 1
            continue
        by_cuts = gold.cuts(produced) == gold.cuts(caption)
        by_words = phrase_words(produced) == phrase_words(caption)
        cut_exact += int(by_cuts)
        word_exact += int(by_words)
        agree += int(by_cuts == by_words)
    total = len(admitted)
    return {
        "corpus": "socrata",
        "arm": "scorer_agreement",
        "system": "run_governed_gold.cuts equality against run_governed_catalog.phrase_words equality",
        "gated_run_id": "governed_gold.socrata.columns.all.exact_pct",
        "fetched_on": str(envelope["fetched_on"]),
        "socrata_pages": pages,
        "admitted_pairs": total,
        "unscorable_stream_skew": skew,
        "cut_set_exact": cut_exact,
        "cut_set_exact_pct": round(cut_exact / total * 100, 2) if total else None,
        "word_tuple_exact": word_exact,
        "word_tuple_exact_pct": round(word_exact / total * 100, 2) if total else None,
        "verdicts_agreeing": agree,
        "verdicts_disagreeing": total - skew - agree,
    }


# ---------------------------------------------------------------------------
# the sweep
# ---------------------------------------------------------------------------
def sweep(
    folds: Sequence[Fold],
    buckets: Dict[Tuple[str, str], str],
    empty_phrases: Dict[Tuple[str, str], Tuple[str, ...]],
) -> Dict[str, object]:
    """Every catalog configuration, on both folds, all of them saved.

    A maximum quoted out of a sweep is only honest if the whole sweep is on the
    record, so the whole sweep is on the record.

    Args:
        folds: The two portal-disjoint folds.
        buckets: Pre-computed classification per pair.
        empty_phrases: Pre-computed empty-arm output per pair.

    Returns:
        The sweep entry, cells keyed ``<mode>.<min_votes>.<min_share>.<fold>``.
    """
    cells: Dict[str, object] = {}
    for mode in MODES:
        for min_votes in SWEEP_MIN_VOTES:
            for min_share in SWEEP_MIN_SHARE:
                for fold in folds:
                    catalog = build_catalog(fold.training, mode, min_votes, min_share)
                    scored = score(fold, catalog, buckets, empty_phrases)
                    live = scored["live"]
                    overall = scored["all"]
                    tokens = scored["abbreviated_tokens"]
                    assert isinstance(live, dict) and isinstance(overall, dict)
                    assert isinstance(tokens, dict)
                    key = f"{mode}.v{min_votes}.s{round(min_share * 100)}.{fold.name}"
                    cells[key] = {
                        "key": key,
                        "mode": mode,
                        "min_votes": min_votes,
                        "min_share": min_share,
                        "fold": fold.name,
                        "acting_rows": catalog.as_dict()["acting_rows"],
                        "all_pairs": overall["pairs"],
                        "all_empty_exact": overall["empty_exact"],
                        "all_voted_exact": overall["voted_exact"],
                        "all_empty_exact_pct": overall["empty_exact_pct"],
                        "all_voted_exact_pct": overall["voted_exact_pct"],
                        "all_delta_points": overall["delta_points"],
                        "live_pairs": live["pairs"],
                        "live_empty_exact": live["empty_exact"],
                        "live_voted_exact": live["voted_exact"],
                        "live_empty_exact_pct": live["empty_exact_pct"],
                        "live_voted_exact_pct": live["voted_exact_pct"],
                        "live_delta_points": live["delta_points"],
                        "live_catalog_fired_pairs": live["catalog_fired_pairs"],
                        "abbreviated_tokens": tokens["tokens"],
                        "abbreviated_tokens_voted_correct": tokens["voted_correct"],
                        "abbreviated_tokens_voted_correct_pct": tokens["voted_correct_pct"],
                    }

    values = [cell for cell in cells.values() if isinstance(cell, dict)]
    pooled_margin = [int(cell["all_voted_exact"]) - int(cell["all_empty_exact"]) for cell in values]
    live_margin = [int(cell["live_voted_exact"]) - int(cell["live_empty_exact"]) for cell in values]
    pooled_deltas = [float(cell["all_delta_points"]) for cell in values]
    live_voted = [float(cell["live_voted_exact_pct"]) for cell in values]
    token_pcts = [
        float(cell["abbreviated_tokens_voted_correct_pct"])
        for cell in values
        if cell["abbreviated_tokens_voted_correct_pct"] is not None
    ]
    # Deterministic, and every term of the ordering is stated: the catalog arm is
    # quoted at the cell that recovers most of the live subset, ties broken by
    # token-level recovery, then by the least damage done to the pooled figure,
    # then by key. A tie-break nobody can reproduce is a selection nobody can audit.
    best = max(
        values,
        key=lambda cell: (
            float(cell["live_voted_exact_pct"]),
            float(cell["abbreviated_tokens_voted_correct_pct"] or 0.0),
            float(cell["all_delta_points"]),
            str(cell["key"]),
        ),
    )
    return {
        "corpus": "socrata",
        "arm": "sweep",
        "system": "empty catalog against every voted catalog in the declared grid",
        "cells_run": len(values),
        "cells_where_voted_beats_empty_pooled": sum(1 for value in pooled_margin if value > 0),
        "cells_where_voted_loses_pooled": sum(1 for value in pooled_margin if value < 0),
        "cells_where_voted_ties_pooled": sum(1 for value in pooled_margin if value == 0),
        "cells_where_voted_beats_empty_live": sum(1 for value in live_margin if value > 0),
        "cells_where_voted_loses_live": sum(1 for value in live_margin if value < 0),
        "cells_where_voted_ties_live": sum(1 for value in live_margin if value == 0),
        "cells_with_no_acting_rows": sum(1 for cell in values if not int(cell["acting_rows"])),
        "pooled_delta_points_best": round(max(pooled_deltas), 2),
        "pooled_delta_points_worst": round(min(pooled_deltas), 2),
        "live_voted_exact_pct_best": round(max(live_voted), 2),
        "abbreviated_tokens_voted_correct_pct_best": round(max(token_pcts), 2)
        if token_pcts
        else None,
        "best_live_cell": best["key"],
        "best_live_mode": best["mode"],
        "best_live_min_votes": best["min_votes"],
        "best_live_min_share": best["min_share"],
        "best_live_fold": best["fold"],
        "selection_on_this_corpus": True,
        "cells": cells,
    }


def null_control(
    folds: Sequence[Fold],
    buckets: Dict[Tuple[str, str], str],
    empty_phrases: Dict[Tuple[str, str], Tuple[str, ...]],
) -> Dict[str, object]:
    """The harness's own positive control: an empty catalog against itself.

    Every delta must be exactly `0.00` and every firing count exactly `0`. A
    harness that reported a difference between an arm and itself would make
    every other number on this page a coincidence, and this is the cheapest
    check that it does not.
    """
    empty = Catalog(
        entries=[],
        identity_rows=0,
        distinct_tokens=0,
        harvested_pairs=0,
        training_pairs=0,
        mode="none",
        min_votes=0,
        min_share=0.0,
    )
    out: Dict[str, object] = {
        "corpus": "socrata",
        "arm": "null_control",
        "system": "empty catalog against empty catalog",
    }
    for fold in folds:
        scored = score(fold, empty, buckets, empty_phrases)
        overall = scored["all"]
        assert isinstance(overall, dict)
        out[fold.name] = {
            "pairs": overall["pairs"],
            "delta_points": overall["delta_points"],
            "catalog_fired_pairs": overall["catalog_fired_pairs"],
        }
    return out


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def render(entries: Dict[str, Dict[str, object]]) -> str:
    """The console table: every subset, both arms, the firing count beside them."""
    lines = [
        "",
        f"{'arm':<38}{'subset':<18}{'n':>8}{'empty %':>9}{'voted %':>9}"
        f"{'delta':>8}{'fired':>8}{'E-only':>8}{'V-only':>8}",
        "-" * 114,
    ]
    for run_id, entry in entries.items():
        if "all" not in entry:
            continue
        label = run_id.replace("governed_catalog.socrata.", "")
        for subset in SUBSETS:
            figures = entry[subset]
            assert isinstance(figures, dict)
            if not figures["pairs"]:
                continue
            lines.append(
                f"{label if subset == 'all' else '':<38}{subset:<18}"
                f"{figures['pairs']:>8,}{figures['empty_exact_pct']:>9.2f}"
                f"{figures['voted_exact_pct']:>9.2f}{figures['delta_points']:>+8.2f}"
                f"{figures['catalog_fired_pairs']:>8,}{figures['empty_only_correct']:>8,}"
                f"{figures['voted_only_correct']:>8,}"
            )
        tokens = entry["abbreviated_tokens"]
        assert isinstance(tokens, dict)
        lines.append(
            f"{'':<38}{'abbrev tokens':<18}{tokens['tokens']:>8,}"
            f"{tokens['empty_correct_pct'] or 0.0:>9.2f}"
            f"{tokens['voted_correct_pct'] or 0.0:>9.2f}"
            f"{'':>8}{tokens['catalog_fired_tokens']:>8,}"
        )
        lines.append("")
    return "\n".join(lines)


def render_census(entry: Dict[str, object]) -> str:
    """The population census, which decides how to read the table above."""
    subsets = entry["subsets"]
    assert isinstance(subsets, dict)
    lines = [
        "population census -- distinct (identifier, caption) pairs, and column occurrences",
        f"  fetched {entry['fetched_on']}, {entry['socrata_pages']} pages, "
        f"{entry['portals']} portals",
        f"{'':<20}{'pairs':>10}{'%':>8}{'occurrences':>14}{'%':>8}",
    ]
    for name, figures in subsets.items():
        assert isinstance(figures, dict)
        lines.append(
            f"  {name:<18}{figures['pairs']:>10,}{figures['pairs_pct']:>8.2f}"
            f"{figures['occurrences']:>14,}{figures['occurrences_pct']:>8.2f}"
        )
    lines.append(
        f"  {'LIVE (both expansion rows)':<18}{entry['live_pairs']:>10,}"
        f"{entry['live_pairs_pct']:>8.2f}{entry['live_occurrences']:>14,}"
        f"{entry['live_occurrences_pct']:>8.2f}"
    )
    lines.append(
        f"  of the {entry['non_identical_pairs']:,} non-identical pairs, "
        f"{entry['token_word_count_mismatch_pairs']:,} "
        f"({entry['token_word_count_mismatch_pct']} %) have a token count that does not "
        "match the caption's word count"
    )
    lines.append(
        f"  abbreviated tokens inside expansion_strict pairs: {entry['abbreviated_tokens']:,}"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="catalog against empty catalog, Socrata")
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument(
        "--pages", type=int, default=gold.SOCRATA_PAGES, help="Socrata catalog pages"
    )
    parser.add_argument("--refresh", action="store_true", help="re-fetch, ignoring the cache")
    parser.add_argument(
        "--no-sweep", action="store_true", help="named cells only; skip the 80-cell grid"
    )
    args = parser.parse_args(argv)

    role = gold.declared_role("socrata")
    print(f"socrata : bench/splits.toml says {role}")
    print(
        "          this runner sweeps catalog configurations against that corpus and quotes a\n"
        "          maximum over them, so nothing here is held-out evidence whatever the role says"
    )

    folds, census_entry = load_folds(args.pages, refresh=args.refresh)
    every_pair: Iterable[Tuple[str, str]] = {pair for fold in folds for pair in fold.scored}
    buckets = {pair: classify(*pair) for pair in every_pair}
    empty_catalog = GovernedDictionary({})
    empty_phrases = {
        pair: phrase_words(expand_identifier(pair[0], empty_catalog).phrase) for pair in buckets
    }

    entries: Dict[str, Dict[str, object]] = {}
    census_entry["splits_declaration"] = role
    entries["governed_catalog.socrata.census"] = census_entry
    entries["governed_catalog.socrata.scorer_agreement"] = scorer_agreement(
        args.pages, refresh=args.refresh
    )

    mode, min_votes, min_share = VOTED_CELL
    for fold in folds:
        catalog = build_catalog(fold.training, mode, min_votes, min_share)
        entry = score(fold, catalog, buckets, empty_phrases)
        entry["splits_declaration"] = role
        entries[f"governed_catalog.socrata.voted.{fold.name}"] = entry

    if not args.no_sweep:
        grid = sweep(folds, buckets, empty_phrases)
        entries["governed_catalog.socrata.sweep"] = grid
        best_mode = str(grid["best_live_mode"])
        best_votes = int(str(grid["best_live_min_votes"]))
        best_share = float(str(grid["best_live_min_share"]))
        for fold in folds:
            catalog = build_catalog(fold.training, best_mode, best_votes, best_share)
            entry = score(fold, catalog, buckets, empty_phrases)
            entry["splits_declaration"] = role
            entry["chosen_as"] = (
                "the cell maximising live-subset exact match across the declared sweep, "
                f"selected after seeing it; the winning cell is {grid['best_live_cell']}"
            )
            entries[f"governed_catalog.socrata.eager.{fold.name}"] = entry

    entries["governed_catalog.socrata.null_control"] = null_control(folds, buckets, empty_phrases)

    print()
    print(render_census(census_entry))
    print(render(entries))

    agreement = entries["governed_catalog.socrata.scorer_agreement"]
    print(
        f"scorer agreement: {agreement['verdicts_agreeing']:,} of "
        f"{agreement['admitted_pairs']:,} admitted pairs agree; cut-set "
        f"{agreement['cut_set_exact_pct']} % against word-tuple "
        f"{agreement['word_tuple_exact_pct']} % "
        f"(gated at {agreement['gated_run_id']})"
    )
    control = entries["governed_catalog.socrata.null_control"]
    for fold in folds:
        figures = control[fold.name]
        assert isinstance(figures, dict)
        print(
            f"null control {fold.name}: delta {figures['delta_points']} points, "
            f"fired {figures['catalog_fired_pairs']}"
        )
    if "governed_catalog.socrata.sweep" in entries:
        grid = entries["governed_catalog.socrata.sweep"]
        print(
            f"sweep: {grid['cells_run']} cells, counted on pair counts and not on a "
            "rounded delta.\n"
            f"  pooled : voted wins {grid['cells_where_voted_beats_empty_pooled']}, "
            f"loses {grid['cells_where_voted_loses_pooled']}, "
            f"ties {grid['cells_where_voted_ties_pooled']} "
            f"({grid['cells_with_no_acting_rows']} of the ties have an empty catalog)\n"
            f"  live   : voted wins {grid['cells_where_voted_beats_empty_live']}, "
            f"loses {grid['cells_where_voted_loses_live']}, "
            f"ties {grid['cells_where_voted_ties_live']}"
        )

    if args.save:
        from run_extraction import save_results

        print(f"\nsaved {len(entries)} run(s) to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
