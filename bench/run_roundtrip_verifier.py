#!/usr/bin/env python3
"""Can the round trip verify? The ceiling on the forward-generator verifier.

Why this runner exists
----------------------
Mandate III's marquee architecture bet is that this library can verify a
candidate pair ``(SF, LF)`` by running the **forward generator** on ``LF`` and
asking whether ``SF`` appears in its output. Every precision signal in every
Schwartz & Hearst descendant is a function of the same character alignment that
proposed the pair; a generator-side verdict would be orthogonal *by
construction*, because the two paths share no knowledge resource.

Structural independence is not the question. It is checked here anyway, in three
closures rather than one (:func:`independence_record`), because the usual form of
the claim compares two *module* closures and ``acronymkit.generator`` does not
import the tokenizer -- the engine does. Measured on the paths a caller runs, the
default extraction path and a real ``generate()`` call share **no** resource
module; turn ``extraction_capture_sentences`` on and they share exactly one,
``acronymkit.stopwords``, which the extractor uses for sentence splitting and
never for eligibility.

The question this runner answers is the one independence does not: **can the
generator reach the true short form at all**, and when it can, does its verdict
ever differ from the aligner's?

The three numbers, and what each is for
---------------------------------------
1. **Recall.** On distinct gold ``(SF, LF)`` pairs, the fraction where the
   casefolded short form appears anywhere in the generator's candidate list.
   This is the ceiling on the whole mechanism: a verifier that cannot reach the
   true short form rejects a correct pair, silently.
2. **Disagreement.** A 2x2 of the aligner's verdict against the round trip's,
   over gold positives *and* seeded mismatched negatives. A verifier that only
   ever confirms what the aligner already liked adds nothing, and the cell that
   says so is ``aligner rejects / round trip accepts``.
3. **Correlation.** The generator's score against the aligner's confidence on
   the same pairs. Sharing no module is not sharing no signal.

Why the beam is swept, and why the sweep is nearly vacuous
-----------------------------------------------------------
``ForwardGenerator._beam_bound`` re-derives the objective from
``ScoringWeights`` and never calls the scorer, which is tolerable in a ranker
and fatal in a verifier. But the generator only consults the beam at all when
the whole search space **fails** to fit ``max_search_nodes``
(``ForwardGenerator._fits_exhaustively``), and a gold long form is a short
phrase. So a beam sweep at fixed ``max_search_nodes`` measures nothing: almost
every pair runs exhaustive and the beam width is never read.

The sweep here therefore sets ``max_search_nodes`` **per pair** to
``exhaustive_bound(...) - 1``, which forces beam mode by construction. That
budget provably cannot starve the search as well: the partial node count after
any round but the last is at most ``bound - factor`` with ``factor >= 2``
whenever skipping is allowed, and the last round's per-state check is reached
with at most ``bound - factor`` spent.

**That argument is not taken on its word.** The ``beam_control_never_cuts`` arm
runs the identical per-pair budget behind a beam too wide to ever cut, so the
only thing left that could truncate is the budget. Its invariant is
``truncated_pairs = 0``: nothing cut and nothing ran out, so that arm enumerated
every state of every space and its recall **is** the ceiling. If it ever comes
back non-zero, every beam figure below it is a node-budget figure wearing a
beam's name, and the sweep should be read as void rather than as a result.

That control also caught something it was not aimed at, which is why the ceiling
is read off it rather than off the arm named ``exhaustive``. A fixed
``max_search_nodes`` of :data:`EXHAUSTIVE_NODES` is *not* enough for every gold
long form -- one PMC roster definition overflows it, drops into beam mode at the
shipped width and loses a hit. The ``exhaustive`` arm reports its own
``truncated_pairs`` so that a reader can see when it stopped deserving its name;
the control arm is the one with nothing left to truncate it.

What is deliberately not measured
---------------------------------
Wall-clock is reported as an unarmed note with the machine named (R18). Every
gated figure here is a count or a ratio of counts: pairs, states enumerated,
candidates scored, generator calls, memo hits. A round trip that got fast by
memoising a long form it had already generated for is indistinguishable from one
that got fast because generation got cheaper, so the memo hit rate ships beside
every throughput-shaped number (R17).

Usage::

    python bench/run_roundtrip_verifier.py
    python bench/run_roundtrip_verifier.py --corpus med1250 --save
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import random
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from acronymkit.config import Config  # noqa: E402
from acronymkit.engine import AcronymEngine  # noqa: E402
from acronymkit.enums import ExtractionProfile, TokenRole  # noqa: E402
from acronymkit.exceptions import AcronymKitError  # noqa: E402
from acronymkit.extractor import (  # noqa: E402
    AbbreviationExtractor,
    _confidence,
    find_best_long_form,
    is_valid_long_form,
    is_valid_short_form,
)
from acronymkit.generator import ForwardGenerator  # noqa: E402
from acronymkit.models import Token  # noqa: E402
from acronymkit.scoring import Scorer  # noqa: E402
from acronymkit.tokenizer import Tokenizer  # noqa: E402
from bench import corpora  # noqa: E402
from bench import scoring as bench_scoring  # noqa: E402

#: Where a saved entry lands.
RESULTS_PATH = REPO_ROOT / "bench" / "results.json"

#: Seed for the mismatched-negative pairing. Fixed so the 2x2 is reproducible;
#: separate from nothing else, because nothing else here is random.
NEGATIVE_SEED = 20260825

#: ``max_candidates`` for every arm that is not the shipped configuration. Large
#: enough that top-N truncation cannot be confused with a search failure -- the
#: two are different defects and only one of them is about the beam.
UNBOUNDED_TOP_N = 100_000

#: ``max_search_nodes`` for the exhaustive arm. Chosen so that no gold long form
#: in either corpus reaches it; ``truncated_pairs`` in that arm's record is the
#: check that the choice held.
EXHAUSTIVE_NODES = 5_000_000

#: Ceiling on the running product inside :func:`exhaustive_bound`. The bound is
#: only ever used as a node budget, and any value above the real total forces
#: exhaustive mode just as well as the total itself, so there is no reason to
#: compute ``3 ** 40``.
BOUND_CAP = 10_000_000

#: Beam widths swept. ``250`` is the shipped default and is included so the
#: sweep carries the operating point somebody actually runs.
BEAM_WIDTHS: Tuple[int, ...] = (1, 2, 4, 8, 16, 32, 64, 250)

#: Beam width for the control arm: wider than any frontier either corpus can
#: produce, so the beam provably never cuts and the only thing left that could
#: truncate is the per-pair node budget.
BEAM_CONTROL_WIDTH = 1_000_000

#: Maximal alphanumeric runs, casefolded. The unit :func:`prefix_alignable`
#: aligns against; deliberately *not* the tokenizer's, because that function
#: measures the search space's shape and not one configuration of it.
_WORD = re.compile(r"[0-9a-z]+")


# ---------------------------------------------------------------------------
# Corpora
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PairCorpus:
    """Distinct gold ``(short form, long form)`` pairs, with their provenance.

    Attributes:
        name: Registry name, for the manifest lookup that labels every figure.
        label: What ``bench/splits.toml`` says this corpus may back.
        pairs: Distinct, whitespace-normalised, **case-preserving** pairs. Case
            is preserved because ``is_valid_short_form`` reads it: casefolding
            the short forms first turns a 94 % admission rate into 0 %.
        documents: How many documents the pairs were drawn from.
        occurrences: How many gold pair occurrences those documents held, before
            de-duplication.
        texts: Document texts, for the arm that asks the extractor to propose.
            Empty when the corpus has no running text to offer.
    """

    name: str
    label: str
    pairs: Tuple[Tuple[str, str], ...]
    documents: int
    occurrences: int
    texts: Tuple[str, ...] = ()


def _normalise(value: str) -> str:
    """Collapse whitespace; change nothing else."""
    return " ".join(value.split())


def load_med1250() -> PairCorpus:
    """MED1250, the Ab3P gold standard: 1,250 abstracts with ``sf|lf`` lines.

    Returns:
        The distinct pairs plus the abstract texts.
    """
    documents = corpora.load("med1250")
    seen: Dict[Tuple[str, str], None] = {}
    occurrences = 0
    for document in documents:
        for pair in document.pairs:
            occurrences += 1
            seen[(_normalise(pair.short_form), _normalise(pair.long_form))] = None
    return PairCorpus(
        name="med1250",
        label=corpora.label_for("med1250"),
        pairs=tuple(sorted(seen)),
        documents=len(documents),
        occurrences=occurrences,
        texts=tuple(document.text for document in documents),
    )


def load_pmc_oa() -> PairCorpus:
    """PMC Open Access rosters -- gold nobody aligned to produce.

    The pairs are each article's own ``<def-list>``, admitted by
    ``bench.run_genre.roster_pair_admissible``, which compares no character of
    the term against the definition. That is the property that makes this
    corpus worth the second pass: MED1250's gold was annotated by the authors of
    a Schwartz & Hearst system against Schwartz & Hearst criteria, so a low
    round-trip recall there could be a fact about the annotation. Here it cannot
    be.

    Returns:
        The distinct roster pairs. No texts: the halves this corpus is built
        around are not what this runner measures.
    """
    from bench import run_genre

    articles, _ = run_genre.load_articles(run_genre.pinned_pmcids())
    seen: Dict[Tuple[str, str], None] = {}
    occurrences = 0
    for article in articles:
        for short, long_form in article.roster:
            if not run_genre.roster_pair_admissible(short, long_form):
                continue
            occurrences += 1
            seen[(_normalise(short), _normalise(long_form))] = None
    return PairCorpus(
        name="pmc_oa_same_article_genre",
        label=corpora.label_for("pmc_oa_same_article_genre"),
        pairs=tuple(sorted(seen)),
        documents=len(articles),
        occurrences=occurrences,
    )


#: Corpus loaders, by the token ``--corpus`` accepts.
LOADERS: Dict[str, Callable[[], PairCorpus]] = {
    "med1250": load_med1250,
    "pmc_oa": load_pmc_oa,
}

#: Run-id stem per ``--corpus`` token. Kept separate from the registry name so a
#: citation path stays readable.
RUN_STEM: Dict[str, str] = {"med1250": "roundtrip.med1250", "pmc_oa": "roundtrip.pmc_oa"}


# ---------------------------------------------------------------------------
# The structural ceiling, computed without the generator
# ---------------------------------------------------------------------------
def prefix_alignable(short_form: str, long_form: str, max_letters: int) -> bool:
    """Can ``short_form`` be cut into prefixes of successive ``long_form`` words?

    This is the search space the forward generator explores, stated without any
    configuration: a left-to-right walk over the long form's words, each word
    donating a prefix of at most ``max_letters`` characters or nothing at all.
    It ignores stop-word filtering, ``min_word_length``, the acronym-length
    bounds and the ``ACRONYM``-role atomicity rule, so it is an **upper bound**
    on what any configuration of the generator can reach.

    It is also the precise statement of how the two instruments differ.
    ``find_best_long_form`` places a short-form character anywhere inside a word;
    this places it only at a word's start, extending contiguously. That single
    difference is what the recall gap below measures.

    Args:
        short_form: The abbreviation. Non-alphanumeric characters are dropped,
            which is generous: the generator cannot emit them either.
        long_form: The expansion.
        max_letters: Characters one word may donate, or ``0`` for unlimited.

    Returns:
        ``True`` when some cut exists.
    """
    chars = "".join(char for char in short_form.casefold() if char.isalnum())
    words = _WORD.findall(long_form.casefold())
    if not chars or not words:
        return False
    target = len(chars)
    reached = {0}
    for word in words:
        nxt = set(reached)
        for index in reached:
            room = target - index
            cap = min(len(word), room) if max_letters == 0 else min(max_letters, len(word), room)
            for take in range(1, cap + 1):
                if chars[index : index + take] != word[:take]:
                    break
                nxt.add(index + take)
        reached = nxt
        if target in reached:
            return True
    return target in reached


def aligner_verdict(short_form: str, long_form: str) -> bool:
    """The shipped Schwartz & Hearst verdict on a candidate pair.

    All three shipped admissibility rules, in the order the extractor applies
    them: the short form must be admissible, a right-to-left character alignment
    must exist over the long form, and the recovered long form must survive the
    post-filter.

    Args:
        short_form: The abbreviation, case preserved.
        long_form: The expansion.

    Returns:
        ``True`` when the aligner would report this pair.
    """
    if not is_valid_short_form(short_form):
        return False
    if find_best_long_form(short_form, long_form) is None:
        return False
    return is_valid_long_form(short_form, long_form)


# ---------------------------------------------------------------------------
# The generator side
# ---------------------------------------------------------------------------
def exhaustive_bound(tokens: Sequence[Token], config: Config) -> int:
    """The node total ``ForwardGenerator._fits_exhaustively`` compares.

    Replicated here rather than called, because the generator's copy exits early
    the moment the running total passes the budget and this needs the total
    itself. The arithmetic is the same: round ``i`` expands at most
    ``prod(factors[:i])`` states into ``factors[i]`` successors each.

    Args:
        tokens: The full token sequence for the phrase.
        config: The configuration whose branching factors apply.

    Returns:
        The total, capped at :data:`BOUND_CAP`. A cap is safe because the value
        is only ever used as a node budget, and any budget below the real total
        forces beam mode just as well.
    """
    limit = config.max_letters_per_token if config.allow_multi_letter_tokens else 1
    limit = max(1, limit)
    skip = 1 if config.allow_token_skipping else 0
    reachable = 1
    total = 0
    for token in tokens:
        if not (token.is_eligible and token.letters):
            continue
        pieces = 1 if token.role is TokenRole.ACRONYM else min(limit, len(token.letters))
        factor = pieces + skip
        total += reachable * factor
        if total >= BOUND_CAP:
            return BOUND_CAP
        reachable *= factor
    return total


@dataclass
class Probe:
    """One generator run over one long form, with its work counts.

    Attributes:
        acronyms: Casefolded candidate strings, in ranked order.
        scores: ``{casefolded acronym: score}``.
        evaluated: Partial states the search enumerated.
        truncated: Whether a beam cut or a budget cost the search states.
        budget: The ``max_search_nodes`` this run was given.
        best_score: Score of the top-ranked candidate, or ``0.0``.
        failed: Whether the generator refused the phrase outright.
    """

    acronyms: Tuple[str, ...] = ()
    scores: Dict[str, float] = field(default_factory=dict)
    evaluated: int = 0
    truncated: bool = False
    budget: int = 0
    best_score: float = 0.0
    failed: bool = False


@dataclass
class Work:
    """Machine-independent work counts for one arm (R17).

    Every one of these is a property of the code rather than of the runner, so
    every one of them is safe to gate. Wall-clock is not here; it is reported
    beside the arm as an unarmed note with the machine named (R18).
    """

    generator_calls: int = 0
    memo_hits: int = 0
    tokenizer_calls: int = 0
    states_evaluated: int = 0
    candidates_scored: int = 0
    generator_refusals: int = 0

    def as_dict(self) -> Dict[str, Any]:
        """The counts, plus the memo hit rate they make readable."""
        lookups = self.generator_calls + self.memo_hits
        return {
            "generator_calls": self.generator_calls,
            "memo_hits": self.memo_hits,
            "memo_lookups": lookups,
            "memo_hit_rate_pct": round(100.0 * self.memo_hits / lookups, 2) if lookups else 0.0,
            "tokenizer_calls": self.tokenizer_calls,
            "states_evaluated": self.states_evaluated,
            "candidates_scored": self.candidates_scored,
            "generator_refusals": self.generator_refusals,
        }


class Prober:
    """Runs the forward generator over long forms, memoised, counting work.

    One instance per arm. The memo is keyed on the long form alone because the
    configuration is fixed for the arm's lifetime -- except in the forced-beam
    arms, where the node budget is per pair and therefore part of the key.

    Args:
        base: The configuration every run shares apart from ``max_search_nodes``.
        lexicon: The engine's lexicon, so ``Lambda(A)`` matches shipped
            behaviour.
        ngram: The engine's n-gram model, for the same reason.
        per_pair_budget: When ``True``, ``max_search_nodes`` is recomputed for
            each long form as ``exhaustive_bound(...) - 1``, which forces the
            beam to be consulted.
    """

    def __init__(
        self,
        base: Config,
        lexicon: Any,
        ngram: Any,
        *,
        per_pair_budget: bool = False,
    ) -> None:
        self._base = base
        self._lexicon = lexicon
        self._ngram = ngram
        self._per_pair = per_pair_budget
        self._tokenizer = Tokenizer(base)
        self._scorer = Scorer(base, lexicon, ngram)
        self._generator = ForwardGenerator(base, self._scorer)
        self._memo: Dict[str, Probe] = {}
        self._tokens: Dict[str, Tuple[Token, ...]] = {}
        self.work = Work()

    def tokens_for(self, long_form: str) -> Tuple[Token, ...]:
        """Tokenise ``long_form``, memoised."""
        cached = self._tokens.get(long_form)
        if cached is None:
            self.work.tokenizer_calls += 1
            cached = tuple(self._tokenizer.tokenize(long_form))
            self._tokens[long_form] = cached
        return cached

    def probe(self, long_form: str) -> Probe:
        """Generate over ``long_form`` and return its candidate set."""
        cached = self._memo.get(long_form)
        if cached is not None:
            self.work.memo_hits += 1
            return cached

        tokens = self.tokens_for(long_form)
        config = self._base
        generator = self._generator
        budget = config.max_search_nodes
        if self._per_pair:
            budget = max(1, exhaustive_bound(tokens, config) - 1)
            config = self._base.model_copy(update={"max_search_nodes": budget})
            generator = ForwardGenerator(config, self._scorer)

        self.work.generator_calls += 1
        try:
            candidates, evaluated, truncated = generator.generate(tokens)
        except AcronymKitError:
            self.work.generator_refusals += 1
            probe = Probe(budget=budget, failed=True)
            self._memo[long_form] = probe
            return probe

        self.work.states_evaluated += evaluated
        self.work.candidates_scored += len(candidates)
        scores = {candidate.acronym.casefold(): candidate.score for candidate in candidates}
        probe = Probe(
            acronyms=tuple(candidate.acronym.casefold() for candidate in candidates),
            scores=scores,
            evaluated=evaluated,
            truncated=truncated,
            budget=budget,
            best_score=candidates[0].score if candidates else 0.0,
        )
        self._memo[long_form] = probe
        return probe


def roundtrip_hit(probe: Probe, short_form: str) -> bool:
    """Does the short form appear anywhere in the generator's output?

    Casefolded string equality. The generator upper-cases its output under the
    shipped ``CaseStyle``, so a case-sensitive test would report zero and say
    nothing.
    """
    return short_form.casefold() in probe.scores


def roundtrip_hit_alnum(probe: Probe, short_form: str) -> bool:
    """The generous variant: compare alphanumeric characters only.

    A gold short form such as ``25(OH)D`` carries punctuation no configuration
    of the generator can emit. Stripping it from both sides asks whether the
    *letters* were reachable, which is the fairer ceiling and is reported beside
    the strict one rather than instead of it.
    """
    target = "".join(char for char in short_form.casefold() if char.isalnum())
    if not target:
        return False
    return any(
        "".join(char for char in acronym if char.isalnum()) == target for acronym in probe.acronyms
    )


# ---------------------------------------------------------------------------
# Statistics, without a dependency
# ---------------------------------------------------------------------------
def pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """Pearson product-moment correlation, or ``None`` when undefined."""
    n = len(xs)
    if n < 3:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    denominator = math.sqrt(sum(v * v for v in dx)) * math.sqrt(sum(v * v for v in dy))
    if denominator == 0.0:
        return None
    return sum(a * b for a, b in zip(dx, dy)) / denominator


def _ranks(values: Sequence[float]) -> List[float]:
    """Fractional ranks, ties averaged."""
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while end + 1 < len(order) and values[order[end + 1]] == values[order[position]]:
            end += 1
        average = (position + end) / 2.0 + 1.0
        for index in range(position, end + 1):
            ranks[order[index]] = average
        position = end + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """Spearman rank correlation, or ``None`` when undefined."""
    if len(xs) < 3:
        return None
    return pearson(_ranks(xs), _ranks(ys))


def phi(a11: int, a10: int, a01: int, a00: int) -> Optional[float]:
    """Phi coefficient for a 2x2 table, or ``None`` when a margin is empty."""
    row1, row0 = a11 + a10, a01 + a00
    col1, col0 = a11 + a01, a10 + a00
    denominator = math.sqrt(float(row1) * row0 * col1 * col0)
    if denominator == 0.0:
        return None
    return (a11 * a00 - a10 * a01) / denominator


def _round(value: Optional[float], digits: int = 4) -> Optional[float]:
    """Round, passing ``None`` through."""
    return None if value is None else round(value, digits)


# ---------------------------------------------------------------------------
# Arms
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Arm:
    """One measured configuration of the round trip.

    Attributes:
        label: Field name under the ``recall`` run id.
        config: The configuration to run.
        per_pair_budget: Whether ``max_search_nodes`` is forced per pair.
        note: One line saying what this arm is for.
    """

    label: str
    config: Config
    per_pair_budget: bool
    note: str


def verification_config() -> Config:
    """The verification-only configuration, and every knob it moves.

    Deliverable 4's disposition (b). Each change buys reach that the shipped
    ranking configuration deliberately does not want:

    * ``max_candidates`` -- a verifier reads the whole pool, not a top-N list.
    * ``max_search_nodes`` -- exhaustive wherever it fits, so no beam is read.
    * ``min_acronym_length = 1`` -- gold short forms of one character exist and
      the shipped floor of ``2`` refuses them before scoring.
    * ``max_acronym_length`` -- raised past every gold short form in either
      corpus.
    * ``max_letters_per_token = 4`` -- a verifier wants the reach; a ranker does
      not want the candidates.
    * the five function-word switches and ``min_word_length = 1`` -- a short
      form may take a letter from a word the generator's stop-word policy
      refuses to let donate.

    Returns:
        The configuration, which is *not* proposed as a shipped default: it
        makes generation useless as generation and is a verifier's setting only.
    """
    return Config(
        max_candidates=UNBOUNDED_TOP_N,
        max_search_nodes=EXHAUSTIVE_NODES,
        min_acronym_length=1,
        max_acronym_length=24,
        max_letters_per_token=4,
        include_articles=True,
        include_prepositions=True,
        include_conjunctions=True,
        include_pronouns=True,
        include_auxiliaries=True,
        min_word_length=1,
    )


def build_arms(*, verify_arm: bool) -> List[Arm]:
    """Every arm measured, in report order."""
    arms = [
        Arm(
            "shipped",
            Config(),
            False,
            "Config() exactly -- what a caller gets today",
        ),
        Arm(
            "unbounded_top_n",
            Config(max_candidates=UNBOUNDED_TOP_N),
            False,
            "shipped search, no top-N truncation -- isolates _limit from the search",
        ),
        Arm(
            "exhaustive",
            Config(max_candidates=UNBOUNDED_TOP_N, max_search_nodes=EXHAUSTIVE_NODES),
            False,
            "no beam consulted anywhere -- the ceiling at shipped weights",
        ),
    ]
    arms.append(
        Arm(
            "beam_control_never_cuts",
            Config(max_candidates=UNBOUNDED_TOP_N, search_beam_width=BEAM_CONTROL_WIDTH),
            True,
            "POSITIVE CONTROL: same per-pair node budget, a beam too wide to ever "
            "cut. truncated_pairs must be 0 and recall must equal the exhaustive "
            "arm's; anything else means the per-pair budget is starving the search "
            "and every beam figure below is a node-budget figure wearing a beam's name",
        )
    )
    for width in BEAM_WIDTHS:
        arms.append(
            Arm(
                f"beam_{width}",
                Config(max_candidates=UNBOUNDED_TOP_N, search_beam_width=width),
                True,
                f"beam mode forced by a per-pair node budget, width {width}",
            )
        )
    if verify_arm:
        arms.append(
            Arm(
                "verification_only",
                verification_config(),
                False,
                "the widened verification-only configuration (R14 disposition)",
            )
        )
    return arms


def run_arm(
    arm: Arm, corpus: PairCorpus, lexicon: Any, ngram: Any
) -> Tuple[Dict[str, Any], Tuple[bool, ...]]:
    """Measure one arm over one corpus.

    Args:
        arm: The configuration to run.
        corpus: The gold pairs.
        lexicon: The engine's lexicon.
        ngram: The engine's n-gram model.

    Returns:
        The arm's record and its per-pair hit vector, in corpus order. The
        vector is what makes the miss decomposition possible: "the round trip
        missed 644 pairs" is a number, and "of those, 434 are unreachable at
        every configuration" is a finding.
    """
    prober = Prober(arm.config, lexicon, ngram, per_pair_budget=arm.per_pair_budget)
    started = time.perf_counter()
    hits = 0
    hits_alnum = 0
    refused = 0
    truncated_pairs = 0
    over_budget_pairs = 0
    truncated_hits = 0
    vector: List[bool] = []
    for short_form, long_form in corpus.pairs:
        probe = prober.probe(long_form)
        if probe.failed:
            refused += 1
            vector.append(False)
            continue
        hit = roundtrip_hit(probe, short_form)
        vector.append(hit)
        hits += int(hit)
        hits_alnum += int(hit or roundtrip_hit_alnum(probe, short_form))
        if probe.truncated:
            truncated_pairs += 1
            truncated_hits += int(hit)
        # Diagnostic only, and deliberately NOT called starvation: the final
        # node count exceeding the budget is what a completed search looks like
        # when the budget was set one below the space's own bound. Whether the
        # budget ever *stopped* a search is what beam_control_never_cuts answers.
        over_budget_pairs += int(probe.evaluated >= probe.budget)
    elapsed = time.perf_counter() - started
    total = len(corpus.pairs)
    record: Dict[str, Any] = {
        "note": arm.note,
        "pairs": total,
        "hits": hits,
        "recall_pct": round(100.0 * hits / total, 2) if total else 0.0,
        "hits_alnum_relaxed": hits_alnum,
        "recall_alnum_relaxed_pct": round(100.0 * hits_alnum / total, 2) if total else 0.0,
        "generator_refused_pairs": refused,
        "truncated_pairs": truncated_pairs,
        "truncated_pairs_pct": round(100.0 * truncated_pairs / total, 2) if total else 0.0,
        "hits_among_truncated": truncated_hits,
        "recall_among_truncated_pct": (
            round(100.0 * truncated_hits / truncated_pairs, 2) if truncated_pairs else 0.0
        ),
        "final_node_count_at_or_above_budget_pairs": over_budget_pairs,
        "search_beam_width": arm.config.search_beam_width,
        "max_candidates": arm.config.max_candidates,
        "max_search_nodes_declared": arm.config.max_search_nodes,
        "per_pair_node_budget": arm.per_pair_budget,
        "work": prober.work.as_dict(),
        "wall_seconds_unarmed_note": round(elapsed, 2),
    }
    return record, tuple(vector)


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------
def census_record(corpus: PairCorpus) -> Dict[str, Any]:
    """What the corpus holds, before anything is measured on it."""
    lengths = [len(short) for short, _ in corpus.pairs]
    over_six = sum(1 for length in lengths if length > 6)
    single = sum(1 for length in lengths if length == 1)
    return {
        "corpus": corpus.name,
        "label": corpus.label,
        "documents": corpus.documents,
        "gold_pair_occurrences": corpus.occurrences,
        "distinct_pairs": len(corpus.pairs),
        "distinct_long_forms": len({long for _, long in corpus.pairs}),
        "distinct_short_forms": len({short for short, _ in corpus.pairs}),
        "short_forms_longer_than_six": over_six,
        "short_forms_longer_than_six_pct": round(100.0 * over_six / len(corpus.pairs), 2),
        "short_forms_of_one_character": single,
    }


def ceiling_record(corpus: PairCorpus) -> Dict[str, Any]:
    """The configuration-free ceiling, and the aligner's reach beside it.

    The generator can only ever emit prefixes of successive words. The aligner
    places a character anywhere inside a word. This record is that difference,
    measured, with no search and no configuration involved -- so a reader can
    tell a search failure from an architectural one.
    """
    total = len(corpus.pairs)
    record: Dict[str, Any] = {"pairs": total}
    for letters in (1, 2, 3, 4, 0):
        key = "inf" if letters == 0 else str(letters)
        hits = sum(prefix_alignable(short, long, letters) for short, long in corpus.pairs)
        record[f"prefix_alignable_at_{key}_letters"] = hits
        record[f"prefix_alignable_at_{key}_letters_pct"] = round(100.0 * hits / total, 2)

    admissible = sum(is_valid_short_form(short) for short, _ in corpus.pairs)
    aligns = sum(find_best_long_form(short, long) is not None for short, long in corpus.pairs)
    accepted = sum(aligner_verdict(short, long) for short, long in corpus.pairs)
    record["aligner_short_form_admissible"] = admissible
    record["aligner_short_form_admissible_pct"] = round(100.0 * admissible / total, 2)
    record["aligner_character_alignment_exists"] = aligns
    record["aligner_character_alignment_exists_pct"] = round(100.0 * aligns / total, 2)
    record["aligner_accepts"] = accepted
    record["aligner_accepts_pct"] = round(100.0 * accepted / total, 2)
    record["aligner_minus_prefix_ceiling_points"] = round(
        100.0 * (accepted - record["prefix_alignable_at_inf_letters"]) / total, 2
    )
    return record


def miss_record(
    corpus: PairCorpus,
    exhaustive_hits: Sequence[bool],
    verification_hits: Optional[Sequence[bool]],
) -> Dict[str, Any]:
    """Split the round trip's misses into architectural and configurational.

    The distinction is the whole disposition. A pair the generator misses
    because a short-form character sits *inside* a word is unreachable at every
    setting of every knob -- the generator emits word prefixes and nothing else,
    and no beam, budget or top-N changes that. A pair it misses because a
    stop-word was not allowed to donate, or because the short form is one
    character long, is a configuration refusing what the search could reach.

    Only the second class is buyable, and :func:`verification_config` is the
    attempt to buy it. ``recovered_by_verification_config`` is what that attempt
    was worth.

    Args:
        corpus: The gold pairs.
        exhaustive_hits: Per-pair hit vector from the exhaustive arm.
        verification_hits: Per-pair hit vector from the widened arm, or ``None``
            when that arm was skipped.

    Returns:
        The record.
    """
    total = len(corpus.pairs)
    misses = [index for index, hit in enumerate(exhaustive_hits) if not hit]
    architectural = 0
    configurational = 0
    recovered = 0
    aligner_accepted_misses = 0
    for index in misses:
        short, long = corpus.pairs[index]
        if prefix_alignable(short, long, 0):
            configurational += 1
            if verification_hits is not None and verification_hits[index]:
                recovered += 1
        else:
            architectural += 1
        if aligner_verdict(short, long):
            aligner_accepted_misses += 1
    return {
        "pairs": total,
        "roundtrip_hits_exhaustive": total - len(misses),
        "misses": len(misses),
        "misses_architectural": architectural,
        "misses_architectural_pct_of_corpus": round(100.0 * architectural / total, 2),
        "misses_configurational": configurational,
        "misses_configurational_pct_of_corpus": round(100.0 * configurational / total, 2),
        "recovered_by_verification_config": recovered if verification_hits is not None else None,
        "misses_the_aligner_accepts": aligner_accepted_misses,
        "misses_the_aligner_accepts_pct_of_corpus": round(
            100.0 * aligner_accepted_misses / total, 2
        ),
    }


def negatives(corpus: PairCorpus) -> Tuple[Tuple[str, str], ...]:
    """Mismatched pairs, seeded, for the half of the 2x2 gold cannot supply.

    A gold-only pool measures how often each instrument *accepts*, which is
    recall wearing a verdict's clothes. The negatives are the only way to see
    whether either instrument discriminates at all.

    Each short form is paired with another pair's long form, rejecting any
    draw that reproduces a real gold pair or reuses the same long form.

    Args:
        corpus: The gold pairs.

    Returns:
        One negative per gold pair, in the gold pairs' order.
    """
    gold = set(corpus.pairs)
    longs = [long for _, long in corpus.pairs]
    rng = random.Random(NEGATIVE_SEED)
    out: List[Tuple[str, str]] = []
    size = len(corpus.pairs)
    for index, (short, long) in enumerate(corpus.pairs):
        for _ in range(64):
            other = longs[rng.randrange(size)]
            if other != long and (short, other) not in gold:
                out.append((short, other))
                break
        else:  # pragma: no cover - a 64-draw failure needs a degenerate corpus
            out.append((short, longs[(index + 1) % size]))
    return tuple(out)


def disagreement_record(
    corpus: PairCorpus, prober: Prober, pool_negatives: Sequence[Tuple[str, str]]
) -> Dict[str, Any]:
    """The 2x2 of aligner verdict against round-trip verdict.

    Computed three times over: on the gold positives alone, on the seeded
    negatives alone, and pooled. The cell that decides whether the mechanism is
    worth building is ``aligner_rejects_roundtrip_accepts``: a verifier that
    only ever subtracts is a threshold on the aligner and not a second opinion.

    Args:
        corpus: The gold pairs.
        prober: A prober on the arm whose verdict is being read.
        pool_negatives: The mismatched pairs from :func:`negatives`.

    Returns:
        The record.
    """

    def table(pairs: Sequence[Tuple[str, str]]) -> Dict[str, int]:
        cells = {"both_accept": 0, "aligner_only": 0, "roundtrip_only": 0, "both_reject": 0}
        for short, long in pairs:
            aligner = aligner_verdict(short, long)
            trip = roundtrip_hit(prober.probe(long), short)
            if aligner and trip:
                cells["both_accept"] += 1
            elif aligner:
                cells["aligner_only"] += 1
            elif trip:
                cells["roundtrip_only"] += 1
            else:
                cells["both_reject"] += 1
        return cells

    positives = table(corpus.pairs)
    negs = table(pool_negatives)
    pooled = {key: positives[key] + negs[key] for key in positives}
    pool_size = sum(pooled.values())
    disagreements = pooled["aligner_only"] + pooled["roundtrip_only"]
    return {
        "gold_positives": {
            **positives,
            "pairs": sum(positives.values()),
            "aligner_accept_pct": round(
                100.0 * (positives["both_accept"] + positives["aligner_only"]) / len(corpus.pairs),
                2,
            ),
            "roundtrip_accept_pct": round(
                100.0
                * (positives["both_accept"] + positives["roundtrip_only"])
                / len(corpus.pairs),
                2,
            ),
        },
        "seeded_negatives": {
            **negs,
            "pairs": sum(negs.values()),
            "aligner_accept_pct": round(
                100.0 * (negs["both_accept"] + negs["aligner_only"]) / len(pool_negatives), 2
            ),
            "roundtrip_accept_pct": round(
                100.0 * (negs["both_accept"] + negs["roundtrip_only"]) / len(pool_negatives), 2
            ),
        },
        "pooled": {
            **pooled,
            "pairs": pool_size,
            "disagreements": disagreements,
            "disagreement_pct": round(100.0 * disagreements / pool_size, 2) if pool_size else 0.0,
            "phi_between_verdicts": _round(
                phi(
                    pooled["both_accept"],
                    pooled["aligner_only"],
                    pooled["roundtrip_only"],
                    pooled["both_reject"],
                )
            ),
        },
        "negative_seed": NEGATIVE_SEED,
    }


def extractor_proposal_record(corpus: PairCorpus, prober: Prober) -> Dict[str, Any]:
    """The literal reading: pairs the extractor actually proposes from text.

    On these the aligner's verdict is ``accept`` by construction -- it proposed
    them -- so the only readable count is how many the round trip rejects. Two
    profiles are run because MED1250 is biomedical text and the shipped default
    refuses a lowercase short form, which would make the pool a different
    population rather than a stricter one.

    Args:
        corpus: A corpus carrying document texts. Returns an empty record when
            it does not.
        prober: A prober on the arm whose verdict is being read.

    Returns:
        The record.
    """
    if not corpus.texts:
        return {"note": "corpus carries no running text; the extractor was not run", "pairs": 0}
    record: Dict[str, Any] = {}
    for profile in (ExtractionProfile.HIGH_PRECISION, ExtractionProfile.BIOMEDICAL):
        extractor = AbbreviationExtractor(Config.for_profile(profile))
        proposed: Dict[Tuple[str, str], None] = {}
        occurrences = 0
        for text in corpus.texts:
            for pair in extractor.extract(text):
                occurrences += 1
                proposed[(_normalise(pair.short_form), _normalise(pair.long_form))] = None
        gold = {
            (bench_scoring.normalise_exact(short), bench_scoring.normalise_exact(long))
            for short, long in corpus.pairs
        }
        rejected = 0
        right_rejected = 0
        right_total = 0
        wrong_rejected = 0
        wrong_total = 0
        for short, long in proposed:
            correct = (
                bench_scoring.normalise_exact(short),
                bench_scoring.normalise_exact(long),
            ) in gold
            miss = not roundtrip_hit(prober.probe(long), short)
            rejected += int(miss)
            if correct:
                right_total += 1
                right_rejected += int(miss)
            else:
                wrong_total += 1
                wrong_rejected += int(miss)
        total = len(proposed)
        false_reject = round(100.0 * right_rejected / right_total, 2) if right_total else 0.0
        true_reject = round(100.0 * wrong_rejected / wrong_total, 2) if wrong_total else 0.0
        kept_right = right_total - right_rejected
        kept_wrong = wrong_total - wrong_rejected
        record[profile.value] = {
            "proposed_occurrences": occurrences,
            "distinct_proposed_pairs": total,
            "roundtrip_rejects": rejected,
            "roundtrip_rejects_pct": round(100.0 * rejected / total, 2) if total else 0.0,
            # The number that decides whether this mechanism is a precision
            # filter or a coin. A filter is worth something only if it rejects
            # the wrong pairs more often than the right ones.
            "proposals_matching_gold": right_total,
            "proposals_not_matching_gold": wrong_total,
            "false_reject_pct_on_gold_matching": false_reject,
            "true_reject_pct_on_non_gold_matching": true_reject,
            "discrimination_points": round(true_reject - false_reject, 2),
            "precision_before_filter_pct": (
                round(100.0 * right_total / total, 2) if total else 0.0
            ),
            "precision_after_filter_pct": (
                round(100.0 * kept_right / (kept_right + kept_wrong), 2)
                if (kept_right + kept_wrong)
                else 0.0
            ),
            "pairs_surviving_the_filter": kept_right + kept_wrong,
        }
    return record


def correlation_record(corpus: PairCorpus, prober: Prober) -> Dict[str, Any]:
    """The generator's score against the aligner's confidence, on the same pairs.

    Reported on the subset where both are defined -- which is exactly the subset
    the round trip accepts, and that restriction is the record's largest
    weakness rather than a detail. The distinct-value count of each variable
    ships beside every coefficient, because a correlation against a variable
    with three distinct values is a null result wearing a coefficient's clothes.

    Two generator signals are correlated, not one: the raw score, and the margin
    to the top-ranked candidate. The margin is the scale-free one, and it is the
    signal a verifier would actually threshold on.
    """
    aligner: List[float] = []
    raw: List[float] = []
    margin: List[float] = []
    for short, long in corpus.pairs:
        probe = prober.probe(long)
        key = short.casefold()
        if key not in probe.scores:
            continue
        aligner.append(_confidence(short, long))
        raw.append(probe.scores[key])
        margin.append(probe.scores[key] - probe.best_score)
    return {
        "pairs_with_both_signals": len(aligner),
        "pairs_offered": len(corpus.pairs),
        "distinct_aligner_confidences": len(set(aligner)),
        "distinct_generator_scores": len(set(raw)),
        "distinct_generator_margins": len(set(margin)),
        "pearson_score_vs_confidence": _round(pearson(raw, aligner)),
        "spearman_score_vs_confidence": _round(spearman(raw, aligner)),
        "pearson_margin_vs_confidence": _round(pearson(margin, aligner)),
        "spearman_margin_vs_confidence": _round(spearman(margin, aligner)),
        "aligner_confidence_min": round(min(aligner), 4) if aligner else None,
        "aligner_confidence_max": round(max(aligner), 4) if aligner else None,
    }


def independence_record() -> Dict[str, Any]:
    """Structural independence, measured rather than asserted.

    Two closures are reported and they are not the same claim:

    * the **module-level** closure of ``acronymkit.extractor``, which is what
      "shares no knowledge resource" is usually taken to mean, and
    * the closure after ``extract()`` has actually run with
      ``extraction_capture_sentences=True``, which reaches the tokenizer and
      therefore the stop-word resource. That path is off by default and it is
      the only place the two halves touch the same file.

    Returns:
        Counts and the shared module names, so a reader can check the claim
        rather than take the count.
    """
    import subprocess

    def closure(source: str) -> List[str]:
        script = (
            "import sys\n"
            f"sys.path.insert(0, {str(REPO_ROOT / 'src')!r})\n"
            f"{source}\n"
            "import json\n"
            "print(json.dumps(sorted(m for m in sys.modules if m.startswith('acronymkit'))))\n"
        )
        out = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, check=True
        )
        return list(json.loads(out.stdout.strip().splitlines()[-1]))

    extractor_only = closure("import acronymkit.extractor")
    generator_only = closure("import acronymkit.generator")
    extractor_run = closure(
        "from acronymkit.config import Config\n"
        "from acronymkit.extractor import AbbreviationExtractor\n"
        "AbbreviationExtractor(Config(extraction_capture_sentences=True))"
        ".extract('The Portable Document Format (PDF) is a format. It has pages.')"
    )
    # The comparison that actually bears on the round trip. `acronymkit.generator`
    # alone does not import the tokenizer -- the engine does -- so intersecting
    # the two *module* closures flatters the claim. This is the closure after a
    # real `generate()` call, which is what the verifier would run.
    generate_run = closure(
        "from acronymkit import AcronymEngine\nAcronymEngine().generate('portable document format')"
    )
    resources = {"acronymkit.lexicon", "acronymkit.phonetics", "acronymkit.stopwords"}
    shared_static = sorted(set(extractor_only) & set(generator_only))
    shared_runtime = sorted(set(extractor_run) & set(generate_run))
    shared_default_path = sorted(set(extractor_only) & set(generate_run))
    return {
        "extractor_module_closure": len(extractor_only),
        "generator_module_closure": len(generator_only),
        "shared_modules_static": len(shared_static),
        "shared_module_names_static": shared_static,
        "shared_resource_modules_static": sorted(set(shared_static) & resources),
        "shared_resource_modules_static_count": len(set(shared_static) & resources),
        "generate_runtime_closure": len(generate_run),
        "generate_runtime_resource_modules": sorted(set(generate_run) & resources),
        "shared_modules_default_paths": len(shared_default_path),
        "shared_resource_modules_default_paths": sorted(set(shared_default_path) & resources),
        "shared_resource_modules_default_paths_count": len(set(shared_default_path) & resources),
        "extractor_runtime_closure_with_sentences": len(extractor_run),
        "shared_modules_runtime_with_sentences": len(shared_runtime),
        "shared_resource_modules_runtime": sorted(set(shared_runtime) & resources),
        "shared_resource_modules_runtime_count": len(set(shared_runtime) & resources),
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def beam_bound_disposition(recall: Dict[str, Any]) -> Dict[str, Any]:
    """What fixing ``ForwardGenerator._beam_bound`` could be worth, in points.

    The brief calls the bound's blindness to a custom scorer term a *fatal*
    precondition for a round-trip verifier. It is a real defect and this record
    is the price of it, derived from arms already measured rather than argued.

    The generous ceiling on any repair -- an oracle bound that never cut the
    eventual optimum -- is the gap between the width-1 arm and the unpruned
    control, because that is the whole of what pruning costs at the most brutal
    width there is. The *shipped* ceiling is much smaller: the beam is only read
    when the space overflows ``max_search_nodes``, and
    ``shipped_pairs_where_the_beam_is_read`` is how often that happens on real
    gold.

    Args:
        recall: The ``recall`` record, keyed by arm label.

    Returns:
        The disposition's figures. The decision itself is a sentence somebody
        writes; these are the numbers it has to survive.
    """
    ceiling = recall["beam_control_never_cuts"]["recall_pct"]
    shipped = recall["shipped"]
    pairs = shipped["pairs"]
    read = shipped["truncated_pairs"]
    return {
        "unpruned_ceiling_pct": ceiling,
        "recall_at_width_1_pct": recall["beam_1"]["recall_pct"],
        "recall_at_shipped_width_pct": recall["beam_250"]["recall_pct"],
        "max_points_an_oracle_bound_could_recover_at_width_1": round(
            ceiling - recall["beam_1"]["recall_pct"], 2
        ),
        "max_points_an_oracle_bound_could_recover_at_width_250": round(
            ceiling - recall["beam_250"]["recall_pct"], 2
        ),
        "shipped_pairs_where_the_beam_is_read": read,
        "shipped_pairs_where_the_beam_is_read_pct": round(100.0 * read / pairs, 2)
        if pairs
        else 0.0,
        "max_points_an_oracle_bound_could_recover_at_shipped_defaults": (
            round(100.0 * read / pairs, 2) if pairs else 0.0
        ),
        # The comparison that decides the disposition: how far the *unpruned*
        # ceiling itself sits below a verifier that never rejects a true pair.
        # Any repair to the bound is spent inside the gap above; this is the gap
        # no beam work can touch.
        "points_below_a_perfect_verifier_at_the_ceiling": round(100.0 - ceiling, 2),
    }


def machine() -> str:
    """The runner, named, so a wall-clock note can be read (R18)."""
    return (
        f"{platform.python_implementation()} {platform.python_version()} "
        f"on {sys.platform}, {platform.machine()}"
    )


def measure(token: str, *, verify_arm: bool = True) -> Dict[str, Dict[str, Any]]:
    """Every record for one corpus.

    Args:
        token: A key of :data:`LOADERS`.
        verify_arm: Whether to run the widened verification-only arm, which is
            an order of magnitude slower than the rest put together.

    Returns:
        ``{run id: record}``.
    """
    corpus = LOADERS[token]()
    stem = RUN_STEM[token]
    engine = AcronymEngine(Config())
    lexicon, ngram = engine.lexicon, engine.ngram

    entries: Dict[str, Dict[str, Any]] = {
        f"{stem}.census": census_record(corpus),
        f"{stem}.ceiling": ceiling_record(corpus),
    }

    recall: Dict[str, Any] = {"machine_unarmed_note": machine()}
    vectors: Dict[str, Tuple[bool, ...]] = {}
    for arm in build_arms(verify_arm=verify_arm):
        record, vector = run_arm(arm, corpus, lexicon, ngram)
        recall[arm.label] = record
        vectors[arm.label] = vector
    entries[f"{stem}.recall"] = recall
    entries[f"{stem}.beam_bound_disposition"] = beam_bound_disposition(recall)
    # The ceiling comes off the control arm and not off `exhaustive`: a fixed
    # node budget is one pair short of exhaustive on PMC, and a miss
    # decomposition taken against an arm that truncated would count a budget
    # overflow as an architectural miss.
    entries[f"{stem}.misses"] = miss_record(
        corpus, vectors["beam_control_never_cuts"], vectors.get("verification_only")
    )

    prober = Prober(
        Config(max_candidates=UNBOUNDED_TOP_N, search_beam_width=BEAM_CONTROL_WIDTH),
        lexicon,
        ngram,
        per_pair_budget=True,
    )
    entries[f"{stem}.disagreement"] = disagreement_record(corpus, prober, negatives(corpus))
    entries[f"{stem}.correlation"] = correlation_record(corpus, prober)
    entries[f"{stem}.extractor_proposed"] = extractor_proposal_record(corpus, prober)
    entries[f"{stem}.verdict_arm_work"] = {
        "note": "work done by the single prober behind disagreement, correlation and proposals",
        **prober.work.as_dict(),
    }
    return entries


def render(entries: Dict[str, Dict[str, Any]]) -> str:
    """A report a reader can check the saved entries against."""
    lines: List[str] = []
    for run_id in sorted(entries):
        record = entries[run_id]
        lines.append("")
        lines.append(run_id)
        lines.append("-" * len(run_id))
        if run_id.endswith(".recall"):
            header = (
                f"  {'arm':<24} {'recall%':>8} {'relaxed%':>9} {'hits':>6} "
                f"{'cut':>6} {'states':>10} {'seconds':>8}"
            )
            lines.append(header)
            for label, arm in record.items():
                if not isinstance(arm, dict):
                    continue
                work = arm["work"]
                lines.append(
                    f"  {label:<24} {arm['recall_pct']:8.2f} "
                    f"{arm['recall_alnum_relaxed_pct']:9.2f} {arm['hits']:6d} "
                    f"{arm['truncated_pairs']:6d} "
                    f"{work['states_evaluated']:10d} {arm['wall_seconds_unarmed_note']:8.1f}"
                )
            continue
        for key, value in record.items():
            if isinstance(value, dict):
                lines.append(f"  {key}:")
                for inner, item in value.items():
                    lines.append(f"    {inner:<40} {item}")
            else:
                lines.append(f"  {key:<42} {value}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Round-trip verification recall and disagreement")
    parser.add_argument(
        "--corpus",
        default="med1250",
        help="comma-separated corpora: " + ",".join(sorted(LOADERS)) + ", or 'all'",
    )
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument(
        "--no-verification-arm",
        action="store_true",
        help="skip the widened verification-only arm, which dominates the runtime",
    )
    args = parser.parse_args(argv)

    tokens = (
        sorted(LOADERS) if args.corpus == "all" else [t.strip() for t in args.corpus.split(",")]
    )
    unknown = [token for token in tokens if token not in LOADERS]
    if unknown:
        parser.error(f"unknown corpus {unknown}; known: {sorted(LOADERS)}")

    entries: Dict[str, Dict[str, Any]] = {"roundtrip.independence": independence_record()}
    for token in tokens:
        entries.update(measure(token, verify_arm=not args.no_verification_arm))

    print(render(entries))

    if args.save:
        from bench.run_extraction import save_results

        path = save_results(entries)
        print(f"\nsaved {len(entries)} run(s) to {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
