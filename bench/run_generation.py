#!/usr/bin/env python3
"""Evaluate acronym *generation* by inverting an extraction gold standard.

Generation has had no external evaluation at all — only sixteen textbook
initialisms, which is a smoke test wearing an evaluation's clothes. But a corpus
of ``(short form, long form)`` pairs is already a generation gold standard read
backwards: feed the long form in, and ask whether the human's short form comes
back, and at what rank.

That gives ``recall@k`` over 1,221 real pairs instead of 16 hand-picked ones.

What this metric is and is not
------------------------------
Gold acronyms are **what humans chose**, not what is optimal. Several expansions
have more than one defensible abbreviation, and the corpus records only the one
that appeared. So ``recall@1`` is a lower bound on quality, not an accuracy
score, and the rank *distribution* is more informative than any single number.

More importantly, MED1250 is biomedical and full of pairs that no initialism
generator can produce by construction:

* ``DAP -> 2,6-diaminopurine`` — the short form draws on characters inside a
  single word;
* ``T3 -> triiodothyronine`` — a digit that appears nowhere in the expansion;
* ``[Ca2+]i -> intracellular Ca2+ concentration`` — punctuation and subscripts.

Scoring those as failures would measure the corpus, not the generator. Every
pair is therefore classified before scoring, and the headline is reported over
the *reachable* subset with the excluded counts shown alongside. Both numbers
appear; neither is hidden.

The coverage ceiling
--------------------
All four presets converge to roughly the same ``recall@25`` over the initialism
bucket, which means they are re-ranking one shared candidate pool and that
about a tenth of the bucket is never in that pool at all. ``--coverage``
diagnoses it: it enumerates the pairs no preset produces at *any* rank,
attributes each to a single cause with committed precedence, and runs the one
experiment that decides where the next effort belongs — the same bucket under a
deliberately enormous search budget. If recall rises the ceiling is *budget*; if
it does not, the ceiling is *tokenisation* or *representability*, and no beam
width will move it.

Usage::

    python bench/run_generation.py                       # default preset
    python bench/run_generation.py --all-presets         # per-preset comparison
    python bench/run_generation.py --examples            # sample failures
    python bench/run_generation.py --coverage --save     # diagnose the ceiling
"""

from __future__ import annotations

import argparse
import itertools
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from bench import corpora  # noqa: E402

if TYPE_CHECKING:  # the library is imported lazily, inside the functions
    from acronymkit.models import Token
    from acronymkit.tokenizer import Tokenizer

#: Ranks reported in the recall curve.
CUTOFFS = (1, 5, 10, 25)

#: Upper bound on generated acronym length for the evaluation. Chosen once, for
#: every system and preset, rather than per pair: sizing the search to the
#: answer would be fitting to the test set.
MAX_ACRONYM_LENGTH = 10

#: Lower bound, matching ``Config.min_acronym_length``. Both bounds are
#: non-binding inside the initialism bucket, whose classifier already requires
#: ``2 <= len(short_form) <= MAX_ACRONYM_LENGTH``; they are named here so the
#: reachability model and the generator agree by construction rather than by
#: coincidence.
MIN_ACRONYM_LENGTH = 2

#: Presets compared by ``--all-presets`` and unioned by ``--coverage``.
PRESETS = (
    "strict_initialism",
    "balanced_pronounceable",
    "max_pronounceable",
    "dictionary_backronym",
)

#: Depth at which the runner stops asking "where does the gold acronym rank"
#: and starts asking "is it in the candidate pool at all". ``max_candidates``
#: truncates the ranked list but never changes the search, so raising it exposes
#: the entire pool the search produced. Coverage is a property of that pool;
#: ``recall@k`` is a property of the ranking over it, and conflating the two is
#: what makes a coverage ceiling look like a ranking failure.
POOL_DEPTH = 100_000

#: A deliberately enormous search budget for the ceiling experiment. Nothing
#: here touches tokenisation, the objective or the filters: only the beam, the
#: node ceiling and the length bounds move, so any recall it buys is
#: attributable to the search budget and to nothing else. At these values the
#: generator runs exhaustively for every phrase in the corpus.
ENORMOUS_BUDGET: dict[str, object] = {
    "search_beam_width": 100_000,
    "max_search_nodes": 5_000_000,
    "min_acronym_length": 1,
    "max_acronym_length": 12,
}

#: Letters one token may donate in the tokenisation-relaxed arm. Four is the
#: widest compound the initialism bucket contains; the arm exists to separate
#: "tokenisation" from "representability" in the verdict, and is a diagnostic
#: upper bound rather than a proposed default.
RELAXED_LETTERS_PER_TOKEN = 4

_ALPHA = re.compile(r"^[A-Za-z]+$")


@dataclass
class Bucket:
    """Counts for one subset of the corpus."""

    name: str
    total: int = 0
    hits: Counter = field(default_factory=Counter)
    ranks: list[int] = field(default_factory=list)

    def record(self, rank: Optional[int]) -> None:
        """Record one pair's outcome; ``rank`` is 1-based, ``None`` for a miss."""
        self.total += 1
        if rank is None:
            return
        self.ranks.append(rank)
        for cutoff in CUTOFFS:
            if rank <= cutoff:
                self.hits[cutoff] += 1

    def recall_at(self, cutoff: int) -> float:
        return self.hits[cutoff] / self.total if self.total else 0.0


def classify(short_form: str, long_form: str) -> str:
    """Bucket a gold pair by whether an initialism generator could produce it.

    Args:
        short_form: The annotated abbreviation.
        long_form: The annotated expansion.

    Returns:
        ``"initialism"`` when every short-form letter is the initial of a
        long-form word, in order — the case the generator is designed for;
        ``"unreachable"`` when the short form is out of length bounds or is not
        purely alphabetic; ``"subword"`` for everything else, meaning the short
        form draws on characters inside words.
    """
    if not _ALPHA.match(short_form):
        return "unreachable"
    if not 2 <= len(short_form) <= MAX_ACRONYM_LENGTH:
        return "unreachable"
    initials = [word[0].lower() for word in re.split(r"[\s\-/]+", long_form) if word]
    cursor = 0
    for character in short_form.lower():
        while cursor < len(initials) and initials[cursor] != character:
            cursor += 1
        if cursor == len(initials):
            return "subword"
        cursor += 1
    return "initialism"


def evaluate_preset(
    pairs: Sequence[tuple[str, str]], strategy_name: Optional[str], examples: int
) -> tuple[dict[str, Bucket], float, list[tuple[str, str, list[str]]]]:
    """Run the generator over every long form and record the gold rank.

    Args:
        pairs: ``(short_form, long_form)`` gold pairs.
        strategy_name: ``ScoringStrategy`` value, or ``None`` for the default.
        examples: How many initialism-bucket failures to retain.

    Returns:
        ``(buckets, elapsed_seconds, failures)``.
    """
    from acronymkit import AcronymEngine, Config
    from acronymkit.enums import ScoringStrategy
    from acronymkit.exceptions import AcronymKitError

    options: dict[str, object] = {
        "max_acronym_length": MAX_ACRONYM_LENGTH,
        "max_candidates": max(CUTOFFS),
        "include_breakdown": False,
    }
    if strategy_name:
        options["scoring_strategy"] = ScoringStrategy.coerce(strategy_name)
    engine = AcronymEngine(Config(**options))

    buckets = {name: Bucket(name) for name in ("initialism", "subword", "unreachable")}
    failures: list[tuple[str, str, list[str]]] = []
    started = time.perf_counter()
    for short_form, long_form in pairs:
        bucket = buckets[classify(short_form, long_form)]
        try:
            candidates = engine.generate(long_form).alternatives
        except AcronymKitError:
            bucket.record(None)
            continue
        produced = [candidate.acronym for candidate in candidates]
        target = short_form.upper()
        rank = produced.index(target) + 1 if target in produced else None
        bucket.record(rank)
        if rank is None and bucket.name == "initialism" and len(failures) < examples:
            failures.append((short_form, long_form, produced[:5]))
    return buckets, time.perf_counter() - started, failures


# ---------------------------------------------------------------------------
# coverage diagnosis
# ---------------------------------------------------------------------------
#: Causes of a coverage miss, in the order they are tested. The **first match
#: wins**, so this tuple is the precedence, committed in code rather than left
#: to the reader.
#:
#: The ordering says: a pair the shipped tokenisation could already build was
#: lost by the search and nothing else, so that is tested first and is disjoint
#: from everything below it. Then come the three configuration defaults, in
#: descending order of how far upstream they act — a token that is not eligible
#: never reaches the letter budget. Then the two structural properties of the
#: token stream (prefix-only compound donation, atomic acronyms), which no
#: setting can change. The combination buckets come last, so a pair is only
#: reported as needing several knobs when no single one accounts for it.
COVERAGE_CAUSES = (
    "search budget: beam pruning",
    "one-letter word dropped by min_word_length (config)",
    "word suppressed as a stop word (config)",
    "compound capped by max_letters_per_token (config)",
    "compound donates prefixes only",
    "existing acronym is atomic",
    "numeral donates digits, not an initial",
    "several configuration causes at once",
    "several tokenisation causes at once",
    "unrepresentable from any token stream",
)

#: Causes that are configuration defaults rather than algorithmic limits — the
#: subset a caller could in principle buy back by changing a setting.
CONFIG_COVERAGE_CAUSES = (
    "one-letter word dropped by min_word_length (config)",
    "word suppressed as a stop word (config)",
    "compound capped by max_letters_per_token (config)",
    "several configuration causes at once",
)

#: ``(tokenisation variant, cause)`` pairs tested in order between the search
#: cause and the combination buckets. Each variant relaxes exactly one thing, so
#: a pair it recovers has exactly that one thing to blame.
_SINGLE_CAUSE_VARIANTS = (
    ("min_word_length", "one-letter word dropped by min_word_length (config)"),
    ("stop_words", "word suppressed as a stop word (config)"),
    ("letters_per_token", "compound capped by max_letters_per_token (config)"),
    ("prefix_only", "compound donates prefixes only"),
    ("atomic_acronym", "existing acronym is atomic"),
    ("numeral_policy", "numeral donates digits, not an initial"),
)


def rank_pairs(
    pairs: Sequence[tuple[str, str]],
    strategy_name: Optional[str] = None,
    **overrides: object,
) -> tuple[list[Optional[int]], float]:
    """Return the rank at which each gold short form comes back.

    Args:
        pairs: ``(short_form, long_form)`` gold pairs.
        strategy_name: ``ScoringStrategy`` value, or ``None`` for the default.
        **overrides: ``Config`` fields layered over the evaluation defaults.

    Returns:
        ``(ranks, elapsed_seconds)``. ``ranks[i]`` is the 1-based rank of
        ``pairs[i]``'s short form among the returned candidates, or ``None``
        when it never came back at all.
    """
    from acronymkit import AcronymEngine, Config
    from acronymkit.enums import ScoringStrategy
    from acronymkit.exceptions import AcronymKitError

    options: dict[str, object] = {
        "max_acronym_length": MAX_ACRONYM_LENGTH,
        "max_candidates": max(CUTOFFS),
        "include_breakdown": False,
    }
    if strategy_name:
        options["scoring_strategy"] = ScoringStrategy.coerce(strategy_name)
    options.update(overrides)
    engine = AcronymEngine(Config(**options))

    ranks: list[Optional[int]] = []
    started = time.perf_counter()
    for short_form, long_form in pairs:
        try:
            produced = [candidate.acronym for candidate in engine.generate(long_form).alternatives]
        except AcronymKitError:
            ranks.append(None)
            continue
        target = short_form.upper()
        ranks.append(produced.index(target) + 1 if target in produced else None)
    return ranks, time.perf_counter() - started


def recall_at(ranks: Sequence[Optional[int]], cutoff: int) -> float:
    """Percentage of ``ranks`` at or above ``cutoff``."""
    if not ranks:
        return 0.0
    return sum(1 for rank in ranks if rank is not None and rank <= cutoff) / len(ranks) * 100


def pool_recall(ranks: Sequence[Optional[int]]) -> float:
    """Percentage of ``ranks`` produced at *any* rank — the coverage measure."""
    if not ranks:
        return 0.0
    return sum(1 for rank in ranks if rank is not None) / len(ranks) * 100


def _donations(token: Token, limit: int, *, subsequence: bool) -> tuple[str, ...]:
    """Return every letter piece ``token`` may contribute to a candidate.

    Mirrors ``ForwardGenerator._branches``: an ``ACRONYM``-role token is atomic
    and offers its whole ``letters`` string, every other token offers the
    prefixes of ``letters`` up to ``limit``.

    Args:
        token: A tokenizer output record.
        limit: ``Config.max_letters_per_token`` for the variant.
        subsequence: When set, a *compound* token additionally offers every
            ordered subsequence of its component initials. That models a
            generator that could take the second component of a hyphenated word
            without taking the first; no configuration can express it, which is
            precisely why it is a separate cause.

    Returns:
        The distinct pieces, sorted for determinism.
    """
    from acronymkit.enums import TokenRole

    letters = token.letters
    if token.role is TokenRole.ACRONYM:
        return (letters,)
    cap = min(limit, len(letters))
    pieces = {letters[:count] for count in range(1, cap + 1)}
    if subsequence and token.subtokens:
        for size in range(1, len(letters) + 1):
            for combination in itertools.combinations(letters, size):
                pieces.add("".join(combination))
    return tuple(sorted(pieces))


def is_representable(
    short_form: str,
    tokens: Sequence[Token],
    limit: int,
    *,
    subsequence: bool = False,
) -> bool:
    """Whether an *unpruned* search over ``tokens`` could build ``short_form``.

    This is the generator's search space with the beam, the node budget and the
    time budget all removed — the exact quantity that separates "the candidate
    was never generated" from "the candidate was generated and pruned". A short
    forward reachability set over character positions is enough, because the
    search is strictly left-to-right and every branch appends a known string.

    ``allow_token_skipping`` is assumed to be ``True``, which it is in every
    variant compared here and in the shipped default; the skip branch is what
    makes the "always available" successor below legal.

    Args:
        short_form: The annotated abbreviation, compared case-insensitively.
        tokens: The eligible, letter-bearing tokens in phrase order.
        limit: ``Config.max_letters_per_token`` for the variant.
        subsequence: Passed through to :func:`_donations`.

    Returns:
        ``True`` when some legal sequence of donations spells ``short_form``.
    """
    target = short_form.upper()
    if not MIN_ACRONYM_LENGTH <= len(target) <= MAX_ACRONYM_LENGTH:
        return False
    reached = {0}
    for token in tokens:
        pieces = _donations(token, limit, subsequence=subsequence)
        successors = set(reached)  # the skip branch, always available
        for position in reached:
            for piece in pieces:
                if target.startswith(piece, position):
                    successors.add(position + len(piece))
        reached = successors
    return len(target) in reached


def all_stop_words() -> frozenset[str]:
    """Return every word the bundled English stop-word registry knows.

    Passed as ``Config.custom_keep_words`` this disables stop-word filtering
    outright: a ``keep`` word is never suppressed whatever its category, which
    covers ``PARTICLE``, ``DETERMINER`` and ``OTHER`` — the three categories no
    ``include_*`` flag can reach.

    Returns:
        The casefolded surface forms.
    """
    from acronymkit import Config
    from acronymkit.enums import StopWordCategory
    from acronymkit.stopwords import StopWordRegistry

    registry = StopWordRegistry.load(Config().language)
    return frozenset(word for category in StopWordCategory for word in registry.words_in(category))


def coverage_streams() -> dict[str, tuple[Tokenizer, int, bool]]:
    """Build the tokenisation variants a coverage miss is attributed against.

    Every variant differs from ``base`` in exactly one respect, except the two
    deliberate combinations at the end, so an attribution is a statement about a
    single knob rather than a guess.

    Returns:
        ``{variant name: (tokenizer, letters_per_token, allow_subsequence)}``.
    """
    from acronymkit import Config
    from acronymkit.enums import NumeralPolicy
    from acronymkit.tokenizer import Tokenizer

    base: dict[str, object] = {"max_acronym_length": MAX_ACRONYM_LENGTH}
    every_stop_word = all_stop_words()
    unlimited_letters: dict[str, object] = {"max_letters_per_token": MAX_ACRONYM_LENGTH}
    config_relaxations: dict[str, object] = {
        "min_word_length": 1,
        "custom_keep_words": every_stop_word,
        **unlimited_letters,
    }
    variants: dict[str, tuple[dict[str, object], bool]] = {
        "base": ({}, False),
        "min_word_length": ({"min_word_length": 1}, False),
        "stop_words": ({"custom_keep_words": every_stop_word}, False),
        "letters_per_token": (unlimited_letters, False),
        "prefix_only": (unlimited_letters, True),
        "atomic_acronym": ({"preserve_existing_acronyms": False}, False),
        "numeral_policy": ({"numeral_policy": NumeralPolicy.WORD}, False),
        "config_combination": (config_relaxations, False),
        "everything": (
            {
                **config_relaxations,
                "preserve_existing_acronyms": False,
                "numeral_policy": NumeralPolicy.WORD,
            },
            True,
        ),
    }
    streams: dict[str, tuple[Tokenizer, int, bool]] = {}
    for name, (overrides, subsequence) in variants.items():
        config = Config(**{**base, **overrides})
        streams[name] = (Tokenizer(config), config.max_letters_per_token, subsequence)
    return streams


def classify_coverage_miss(
    short_form: str, long_form: str, streams: dict[str, tuple[Tokenizer, int, bool]]
) -> str:
    """Attribute one never-produced pair to a single cause.

    Args:
        short_form: The annotated abbreviation.
        long_form: Its expansion.
        streams: Variants from :func:`coverage_streams`.

    Returns:
        One of :data:`COVERAGE_CAUSES`, chosen by first match in that order.
    """

    def reachable(variant: str) -> bool:
        tokenizer, limit, subsequence = streams[variant]
        tokens = [
            token for token in tokenizer.tokenize(long_form) if token.is_eligible and token.letters
        ]
        return is_representable(short_form, tokens, limit, subsequence=subsequence)

    if reachable("base"):
        # The shipped token stream could already spell it, so nothing upstream
        # of the search is to blame; only a beam cut can have lost it.
        return "search budget: beam pruning"
    for variant, cause in _SINGLE_CAUSE_VARIANTS:
        if reachable(variant):
            return cause
    if reachable("config_combination"):
        return "several configuration causes at once"
    if reachable("everything"):
        return "several tokenisation causes at once"
    return "unrepresentable from any token stream"


def _slug(cause: str) -> str:
    """Return the ``results.json`` key fragment for ``cause``."""
    return re.sub(r"[^a-z0-9]+", "_", cause.lower()).strip("_")


def render_curve(label: str, ranks: Sequence[Optional[int]], pool: Sequence[Optional[int]]) -> str:
    """Format one row of the recall/coverage table."""
    cells = " ".join(f"{recall_at(ranks, cutoff):6.2f}%" for cutoff in CUTOFFS)
    return f"{label:<34} {len(ranks):>5} {cells} {pool_recall(pool):9.2f}%"


def curve_entry(ranks: Sequence[Optional[int]], pool: Sequence[Optional[int]]) -> dict:
    """Recall curve plus pool coverage, rounded for ``results.json``."""
    return {
        **{f"recall_at_{cutoff}": round(recall_at(ranks, cutoff), 2) for cutoff in CUTOFFS},
        "pool_recall": round(pool_recall(pool), 2),
        "in_pool": sum(1 for rank in pool if rank is not None),
    }


def run_coverage(pairs: Sequence[tuple[str, str]], corpus: str) -> dict[str, dict]:
    """Diagnose the generation coverage ceiling and print the report.

    Args:
        pairs: Every gold pair in the corpus.
        corpus: Corpus name, used in the recorded run ids.

    Returns:
        ``{run id: measurements}`` ready for ``save_results``.
    """
    bucketed: dict[str, list[tuple[str, str]]] = {
        "initialism": [],
        "subword": [],
        "unreachable": [],
    }
    for short_form, long_form in pairs:
        bucketed[classify(short_form, long_form)].append((short_form, long_form))
    initialism = bucketed["initialism"]
    subword = bucketed["subword"]
    total = len(initialism)
    started = time.perf_counter()

    header = (
        f"{'arm':<34} {'n':>5} "
        + " ".join(f"{'R@' + str(c):>7}" for c in CUTOFFS)
        + f" {'pool':>10}"
    )
    rule = "-" * len(header)

    # -- 1. the shared candidate pool, per preset and unioned ---------------
    ranked: dict[str, list[Optional[int]]] = {}
    pooled: dict[str, list[Optional[int]]] = {}
    print("1. CANDIDATE POOL OVER THE INITIALISM BUCKET")
    print(
        "   'pool' is membership at any rank, measured at max_candidates="
        f"{POOL_DEPTH:,}:\n   coverage, as opposed to the ranking that R@k reports.\n"
    )
    print(header)
    print(rule)
    for preset in PRESETS:
        ranked[preset], _ = rank_pairs(initialism, preset)
        pooled[preset], _ = rank_pairs(initialism, preset, max_candidates=POOL_DEPTH)
        print(render_curve(preset, ranked[preset], pooled[preset]))

    top_cutoff = max(CUTOFFS)

    def within_top(rank: Optional[int]) -> bool:
        """Whether a rank exists and is inside the deepest reported cutoff."""
        return rank is not None and rank <= top_cutoff

    union_25 = [any(within_top(ranked[p][i]) for p in PRESETS) for i in range(total)]
    union_pool = [any(pooled[p][i] is not None for p in PRESETS) for i in range(total)]
    never = [initialism[i] for i in range(total) if not union_pool[i]]
    deep = [initialism[i] for i in range(total) if union_pool[i] and not union_25[i]]
    print(rule)
    print(
        f"{'UNION of all presets':<34} {total:>5} "
        f"{'':>{8 * (len(CUTOFFS) - 1)}}{sum(union_25) / total * 100:6.2f}% "
        f"{sum(union_pool) / total * 100:9.2f}%"
    )
    print(
        f"\n   never produced at any rank by any preset : {len(never)} "
        f"({len(never) / total * 100:.2f} % of the bucket)  <- the ceiling"
    )
    print(
        f"   produced, but beyond rank 25 everywhere : {len(deep)} "
        f"({len(deep) / total * 100:.2f} %)  <- ranking, not coverage"
    )
    for short, long_form in deep:
        print(f"     {short:<10} {long_form}")
    print()

    # -- 2. cause taxonomy ---------------------------------------------------
    streams = coverage_streams()
    attributed = [
        (classify_coverage_miss(short, long_form, streams), short, long_form)
        for short, long_form in never
    ]
    counts = Counter(cause for cause, _short, _long in attributed)
    config_total = sum(counts[cause] for cause in CONFIG_COVERAGE_CAUSES)
    print("2. WHY THOSE PAIRS ARE NEVER GENERATED")
    print(f"   {len(never)} pairs, one cause each, first match in the committed order wins.\n")
    print(f"   {'share':>7}  {'count':>5}  cause")
    print("   " + "-" * 60)
    for cause in COVERAGE_CAUSES:
        if counts[cause]:
            print(f"   {counts[cause] / len(never) * 100:6.1f}%  {counts[cause]:5}  {cause}")
    print(
        f"\n   configuration rather than algorithm: {config_total} "
        f"({config_total / len(never) * 100:.1f} % of the ceiling)\n"
    )
    print("   the ceiling set in full, grouped by cause:")
    for cause in COVERAGE_CAUSES:
        members = [(short, long_form) for name, short, long_form in attributed if name == cause]
        if not members:
            continue
        print(f"\n   {cause} ({len(members)})")
        for short, long_form in members:
            print(f"     {short:<10} {long_form}")
    print()

    # -- 3. the experiment that decides where effort belongs -----------------
    print("3. KEY EXPERIMENT -- does a bigger search budget move the ceiling?")
    print(
        f"   beam {ENORMOUS_BUDGET['search_beam_width']:,}, nodes "
        f"{ENORMOUS_BUDGET['max_search_nodes']:,}, length bounds "
        f"{ENORMOUS_BUDGET['min_acronym_length']}-{ENORMOUS_BUDGET['max_acronym_length']}. "
        "Tokenisation untouched.\n"
    )
    print(header)
    print(rule)
    budget_ranked: dict[str, list[Optional[int]]] = {}
    budget_pooled: dict[str, list[Optional[int]]] = {}
    for preset in PRESETS:
        print(render_curve(f"{preset} / control", ranked[preset], pooled[preset]))
        budget_ranked[preset], _ = rank_pairs(initialism, preset, **ENORMOUS_BUDGET)
        budget_pooled[preset], _ = rank_pairs(
            initialism, preset, max_candidates=POOL_DEPTH, **ENORMOUS_BUDGET
        )
        print(render_curve(f"{preset} / budget", budget_ranked[preset], budget_pooled[preset]))

    default = PRESETS[0]
    budget_delta = recall_at(budget_ranked[default], max(CUTOFFS)) - recall_at(
        ranked[default], max(CUTOFFS)
    )
    budget_pool_delta = pool_recall(budget_pooled[default]) - pool_recall(pooled[default])

    # The budget arm answers "is it budget?". It cannot separate the two other
    # candidates named in the verdict, so a second arm relaxes tokenisation on
    # top of it: if coverage jumps there, the ceiling is tokenisation, and what
    # survives both arms is genuinely unrepresentable.
    relaxed_options: dict[str, object] = dict(
        ENORMOUS_BUDGET,
        min_word_length=1,
        custom_keep_words=all_stop_words(),
        max_letters_per_token=RELAXED_LETTERS_PER_TOKEN,
        preserve_existing_acronyms=False,
    )
    relaxed_ranked, _ = rank_pairs(initialism, default, **relaxed_options)
    relaxed_pooled, _ = rank_pairs(
        initialism, default, max_candidates=POOL_DEPTH, **relaxed_options
    )
    print(render_curve(f"{default} / budget+tokens", relaxed_ranked, relaxed_pooled))
    print(rule)
    relaxed_pool_delta = pool_recall(relaxed_pooled) - pool_recall(pooled[default])
    verdict = (
        "BUDGET"
        if budget_delta >= 1.0
        else ("TOKENISATION" if relaxed_pool_delta >= 1.0 else "REPRESENTABILITY")
    )
    print(
        f"\n   enormous budget moves R@{max(CUTOFFS)} by {budget_delta:+.2f} points "
        f"and pool coverage by {budget_pool_delta:+.2f}."
    )
    print(
        f"   relaxing tokenisation as well moves pool coverage by {relaxed_pool_delta:+.2f} points."
    )
    print(f"   VERDICT: the ceiling is {verdict}.\n")

    # -- 4. the subword bucket, reported on its own --------------------------
    print("4. SUBWORD BUCKET -- where MappingKind.CONTIGUOUS has to earn its keep")
    print(
        "   Short forms drawing on characters inside words. Never reported\n"
        "   separately before; the generator is not designed for these, and the\n"
        "   pool column says how many it can reach at all.\n"
    )
    print(header)
    print(rule)
    subword_entries: dict[str, dict] = {}
    for preset in PRESETS:
        sub_ranked, _ = rank_pairs(subword, preset)
        sub_pooled, _ = rank_pairs(subword, preset, max_candidates=POOL_DEPTH)
        print(render_curve(preset, sub_ranked, sub_pooled))
        subword_entries[preset] = curve_entry(sub_ranked, sub_pooled)
    elapsed = time.perf_counter() - started
    print(f"\n(elapsed {elapsed:.2f}s)\n")

    prefix = f"generation.{corpus}.coverage"
    recorded: dict[str, dict] = {
        f"{prefix}.ceiling": {
            "corpus": corpus,
            "elapsed_seconds": round(elapsed, 4),
            "initialism_n": total,
            "union_recall_at_25": round(sum(union_25) / total * 100, 2),
            "union_pool_recall": round(sum(union_pool) / total * 100, 2),
            "never_produced": len(never),
            "never_produced_pct": round(len(never) / total * 100, 2),
            "beyond_rank_25": len(deep),
            "beyond_rank_25_pct": round(len(deep) / total * 100, 2),
            "pool_depth": POOL_DEPTH,
            **{
                f"{preset}_pool_recall": round(pool_recall(pooled[preset]), 2) for preset in PRESETS
            },
        },
        f"{prefix}.taxonomy": {
            "corpus": corpus,
            "total_misses": len(never),
            "config_attributable": config_total,
            "config_attributable_pct": round(config_total / len(never) * 100, 2),
            **{f"n_{_slug(cause)}": counts[cause] for cause in COVERAGE_CAUSES},
            **{
                f"pct_{_slug(cause)}": round(counts[cause] / len(never) * 100, 2)
                for cause in COVERAGE_CAUSES
            },
        },
        f"{prefix}.budget_experiment": {
            "corpus": corpus,
            "verdict": verdict,
            "search_beam_width": ENORMOUS_BUDGET["search_beam_width"],
            "max_search_nodes": ENORMOUS_BUDGET["max_search_nodes"],
            "budget_recall_at_25_delta": round(budget_delta, 2),
            "budget_pool_recall_delta": round(budget_pool_delta, 2),
            "tokenisation_pool_recall_delta": round(relaxed_pool_delta, 2),
            **{
                f"control_{preset}_{key}": value
                for preset in PRESETS
                for key, value in curve_entry(ranked[preset], pooled[preset]).items()
            },
            **{
                f"budget_{preset}_{key}": value
                for preset in PRESETS
                for key, value in curve_entry(budget_ranked[preset], budget_pooled[preset]).items()
            },
            **{
                f"budget_tokenisation_{default}_{key}": value
                for key, value in curve_entry(relaxed_ranked, relaxed_pooled).items()
            },
        },
        f"{prefix}.subword": {
            "corpus": corpus,
            "subword_n": len(subword),
            **{
                f"{preset}_{key}": value
                for preset, entry in subword_entries.items()
                for key, value in entry.items()
            },
        },
    }
    return recorded


def render(
    label: str, buckets: dict[str, Bucket], elapsed: float, *, show_header: bool = True
) -> str:
    """Format one preset's results."""
    lines = []
    if show_header:
        lines.append(
            f"{'preset':<24} {'bucket':<12} {'n':>5} "
            + " ".join(f"{'R@' + str(c):>7}" for c in CUTOFFS)
            + f" {'median':>7}"
        )
        lines.append("-" * (24 + 12 + 6 + 8 * len(CUTOFFS) + 8))
    for name in ("initialism", "subword", "unreachable"):
        bucket = buckets[name]
        if not bucket.total:
            continue
        median = sorted(bucket.ranks)[len(bucket.ranks) // 2] if bucket.ranks else 0
        cells = " ".join(f"{bucket.recall_at(c) * 100:6.1f}%" for c in CUTOFFS)
        lines.append(
            f"{label:<24} {name:<12} {bucket.total:>5} {cells} {median if median else '-':>7}"
        )
    lines.append(f"{'':<24} {'(elapsed ' + format(elapsed, '.2f') + 's)':<12}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--corpus", default="med1250", choices=sorted(corpora.READERS))
    parser.add_argument("--all-presets", action="store_true")
    parser.add_argument("--examples", type=int, default=0, help="show N initialism failures")
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="diagnose the coverage ceiling instead of reporting the recall table",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    args = parser.parse_args(argv)

    documents = corpora.load(args.corpus)
    pairs = [(pair.short_form, pair.long_form) for document in documents for pair in document.pairs]
    if args.limit:
        pairs = pairs[: args.limit]

    distribution = Counter(classify(short, long_form) for short, long_form in pairs)
    print(f"corpus      : {args.corpus}")
    print(f"gold pairs  : {len(pairs):,}")
    print(
        "buckets     : "
        + ", ".join(f"{name} {count:,}" for name, count in distribution.most_common())
    )
    print(
        "note        : recall is reported per bucket. Only 'initialism' is a fair\n"
        "              target for an initialism generator; the rest are shown so the\n"
        "              exclusion is visible rather than hidden.\n"
    )

    recorded: dict[str, dict] = {}
    if args.coverage:
        recorded = run_coverage(pairs, args.corpus)
        if args.save:
            from run_extraction import save_results

            print(
                f"saved {len(recorded)} run(s) to {save_results(recorded).relative_to(REPO_ROOT)}"
            )
        return 0

    presets: list[Optional[str]] = list(PRESETS) if args.all_presets else [None]
    first = True
    for preset in presets:
        buckets, elapsed, failures = evaluate_preset(pairs, preset, args.examples)
        print(render(preset or "default", buckets, elapsed, show_header=first))
        first = False
        label = preset or "default"
        recorded[f"generation.{args.corpus}.{label}"] = {
            "corpus": args.corpus,
            "preset": label,
            "gold_pairs": len(pairs),
            "elapsed_seconds": round(elapsed, 4),
            **{
                f"{bucket}_n": buckets[bucket].total
                for bucket in ("initialism", "subword", "unreachable")
            },
            **{
                f"{bucket}_recall_at_{cutoff}": round(buckets[bucket].recall_at(cutoff) * 100, 2)
                for bucket in ("initialism", "subword", "unreachable")
                for cutoff in CUTOFFS
            },
        }
        if failures:
            print("\n  initialism-bucket failures (gold not in top 25):")
            for short_form, long_form, produced in failures:
                print(f"    {short_form:<10} gold for {long_form!r}")
                print(f"    {'':<10} generated {produced}")
            print()
    if args.save:
        from run_extraction import save_results

        print(f"saved {len(recorded)} run(s) to {save_results(recorded).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
