"""Behavioural tests for :mod:`acronymkit.backronym`.

Two independent capabilities are covered:

``align``
    Positional alignment of a fixed target onto a source phrase, in
    *non-decreasing* token order -- consecutive letters may share a token when
    their character offsets strictly increase, which is what makes
    ``CONTIGUOUS`` reachable. Numbers are pinned only where the ``omega``
    schedule fixes them (an all-``INITIAL`` alignment of ``k`` letters has
    positional term ``k * initial_weight``; swapping one letter from a word
    initial to a word interior costs exactly
    ``initial_weight - internal_weight``).

``synthesize``
    Per-letter word selection with no source phrase at all.
"""

from __future__ import annotations

import json
import time
from functools import cache
from typing import Optional, Sequence

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from acronymkit.backronym import BackronymGenerator
from acronymkit.config import Config
from acronymkit.engine import AcronymEngine
from acronymkit.enums import MappingKind
from acronymkit.lexicon import Lexicon
from acronymkit.models import BackronymCandidate, Token
from acronymkit.phonetics import CharNGramModel
from acronymkit.scoring import Scorer
from acronymkit.tokenizer import Tokenizer
from conftest import timing_budget

# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------

#: Content words used to build synthetic phrases; none is a stop word and every
#: one is long enough to stay eligible under the default configuration.
WORD_POOL = (
    "portable",
    "document",
    "format",
    "rapid",
    "modern",
    "system",
    "engine",
    "vector",
    "signal",
    "neural",
    "kernel",
    "beacon",
)

#: A vocabulary with a word for every letter of ``RAM`` and none for ``Q``.
SMALL_VOCABULARY = ["rapid", "reliable", "adaptive", "agile", "modular", "modern"]


@cache
def pipeline(config: Config) -> tuple[Tokenizer, BackronymGenerator]:
    """Build the tokenizer/backronym pair the engine would build for ``config``."""
    lexicon = Lexicon.load(config.language, path=config.lexicon_path)
    ngram = CharNGramModel.load(config.language, path=config.ngram_model_path)
    scorer = Scorer(config, lexicon, ngram)
    return Tokenizer(config), BackronymGenerator(config, scorer, lexicon)


def align(
    target: str,
    phrase: str,
    *,
    config: Optional[Config] = None,
    limit: Optional[int] = None,
) -> tuple[list[Token], list[BackronymCandidate]]:
    """Tokenize ``phrase`` and align ``target`` onto it."""
    resolved = Config() if config is None else config
    tokenizer, generator = pipeline(resolved)
    tokens = tokenizer.tokenize(phrase)
    return tokens, generator.align(target, tokens, limit=limit)


def synthesize(
    target: str,
    *,
    vocabulary: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
    config: Optional[Config] = None,
) -> list[BackronymCandidate]:
    """Synthesise expansions for ``target``."""
    resolved = Config() if config is None else config
    _, generator = pipeline(resolved)
    return generator.synthesize(target, vocabulary=vocabulary, limit=limit)


def mapped_indices(candidate: BackronymCandidate) -> list[int]:
    """Token indices the candidate actually used, in acronym order."""
    return [
        mapping.token_index for mapping in candidate.mappings if mapping.token_index is not None
    ]


def mapped_steps(candidate: BackronymCandidate) -> list[tuple[int, int]]:
    """``(token index, char offset)`` per mapped letter, in acronym order."""
    return [
        (mapping.token_index, mapping.char_offset)
        for mapping in candidate.mappings
        if mapping.token_index is not None and mapping.char_offset is not None
    ]


def rendered(candidate: BackronymCandidate) -> str:
    """Re-derive ``expansion_text``: one word per *token*, not per letter."""
    words: list[str] = []
    previous: Optional[int] = None
    for mapping in candidate.mappings:
        if mapping.token_index is None:
            continue
        if mapping.token_index != previous:
            words.append(candidate.expansion[mapping.position])
            previous = mapping.token_index
    return " ".join(words)


# ---------------------------------------------------------------------------
# align — full alignments
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("target", "phrase", "expected_words"),
    [
        ("PDF", "Portable Document Format", ["Portable", "Document", "Format"]),
        (
            "API",
            "Application Programming Interface",
            ["Application", "Programming", "Interface"],
        ),
    ],
)
def test_align_maps_every_letter_to_a_word_initial(
    target: str, phrase: str, expected_words: list[str]
) -> None:
    """The textbook expansion is recovered with full coverage and all initials."""
    _, candidates = align(target, phrase)
    assert candidates
    best = candidates[0]
    assert best.target_word == target
    assert best.coverage == 1.0
    assert best.unmapped_letters == []
    assert best.expansion == expected_words
    assert best.expansion_text == " ".join(expected_words)
    assert [mapping.kind for mapping in best.mappings] == [MappingKind.INITIAL] * len(target)
    assert [mapping.char_offset for mapping in best.mappings] == [0] * len(target)
    assert mapped_indices(best) == list(range(len(target)))


def test_align_positional_term_is_exactly_k_initial_weights() -> None:
    """``PDF`` over three word initials scores ``3 * initial_weight``."""
    config = Config()
    _, candidates = align("PDF", "Portable Document Format", config=config)
    best = candidates[0]
    assert best.breakdown is not None
    assert best.breakdown.positional == pytest.approx(3 * config.weights.initial_weight)
    assert best.breakdown.information_loss == 0.0
    assert best.score == pytest.approx(best.breakdown.total)


def test_align_skips_ineligible_tokens() -> None:
    """The stop-word policy applies to backronyms exactly as to generation."""
    phrase = "National Aeronautics and Space Administration"
    tokens, candidates = align("NASA", phrase)
    stop_word = next(token for token in tokens if token.text == "and")
    assert stop_word.is_eligible is False
    best = candidates[0]
    assert best.coverage == 1.0
    assert stop_word.index not in mapped_indices(best)
    assert best.expansion_text == "National Aeronautics Space Administration"


# ---------------------------------------------------------------------------
# align — unmatched targets
# ---------------------------------------------------------------------------
def test_align_with_no_matching_letters_degrades_instead_of_raising() -> None:
    """``ZZZ`` matches nothing in the phrase, but the call still succeeds."""
    _, candidates = align("ZZZ", "Portable Document Format")
    assert len(candidates) == 1
    only = candidates[0]
    assert only.coverage == 0.0
    assert only.unmapped_letters == ["Z", "Z", "Z"]
    assert len(only.unmapped_letters) == 3
    assert only.expansion == ["", "", ""]
    assert only.expansion_text == ""
    assert [mapping.kind for mapping in only.mappings] == [MappingKind.UNMAPPED] * 3
    assert mapped_indices(only) == []


def test_align_unmapped_letters_cost_the_unmapped_penalty() -> None:
    """Three unmapped letters cost ``3 * unmapped_penalty`` and drop 3 critical tokens."""
    config = Config()
    _, candidates = align("ZZZ", "Portable Document Format", config=config)
    only = candidates[0]
    assert only.breakdown is not None
    assert only.breakdown.positional == pytest.approx(-3 * config.weights.unmapped_penalty)
    assert only.breakdown.information_loss == 3.0


def test_align_on_an_empty_token_sequence_returns_an_all_unmapped_alignment() -> None:
    _, generator = pipeline(Config())
    candidates = generator.align("PDF", [])
    assert len(candidates) == 1
    assert candidates[0].coverage == 0.0
    assert candidates[0].unmapped_letters == ["P", "D", "F"]


@pytest.mark.parametrize("target", ["", "   ", "...", "-"])
def test_align_with_no_alphanumeric_target_returns_empty(target: str) -> None:
    _, candidates = align(target, "Portable Document Format")
    assert candidates == []


@pytest.mark.parametrize("limit", [0, -1])
def test_align_with_a_non_positive_limit_returns_empty(limit: int) -> None:
    _, candidates = align("PDF", "Portable Document Format", limit=limit)
    assert candidates == []


# ---------------------------------------------------------------------------
# align — structural invariants
# ---------------------------------------------------------------------------
ALIGN_CASES = [
    ("RAM", "Rapid Analysis of Modern Systems Engineering Data"),
    ("NEXUS", "Next Generation Extensible Unified Storage"),
    ("PDF", "Portable Document Format"),
    ("SOAP", "Simple Object Access Protocol Service"),
    ("ZEBRA", "Rapid Analysis Modern Systems"),
]


@pytest.mark.parametrize(("target", "phrase"), ALIGN_CASES)
def test_alignment_token_indices_are_non_decreasing(target: str, phrase: str) -> None:
    """Letters read left to right: never backwards, and never twice over a character.

    Sub-word matching means two consecutive letters may share a token (that is
    how ``CONTIGUOUS`` arises), so the token order is *non-decreasing* rather
    than strictly increasing -- but when a token is shared, the character
    offsets inside it must strictly increase.
    """
    _, candidates = align(target, phrase)
    assert candidates
    for candidate in candidates:
        steps = mapped_steps(candidate)
        for (earlier_token, earlier_offset), (later_token, later_offset) in zip(steps, steps[1:]):
            assert earlier_token <= later_token, (
                f"{candidate.expansion_text!r} went backwards: {steps}"
            )
            if earlier_token == later_token:
                assert earlier_offset < later_offset, (
                    f"{candidate.expansion_text!r} reused offset {earlier_offset} "
                    f"of token {earlier_token}: {steps}"
                )


@pytest.mark.parametrize(("target", "phrase"), ALIGN_CASES)
def test_alignment_coverage_equals_mapped_over_total(target: str, phrase: str) -> None:
    _, candidates = align(target, phrase)
    assert candidates
    for candidate in candidates:
        letters = len(candidate.target_word)
        mapped = letters - len(candidate.unmapped_letters)
        assert candidate.coverage == pytest.approx(mapped / letters)
        assert 0.0 <= candidate.coverage <= 1.0


@pytest.mark.parametrize(("target", "phrase"), ALIGN_CASES)
def test_alignment_expansion_has_one_entry_per_target_letter(target: str, phrase: str) -> None:
    """Unmapped letters hold their slot with ``""``; the text names each token once.

    ``expansion`` is per *letter*, so a token donating two letters appears
    twice in it. ``expansion_text`` is the reading of the alignment, so that
    token appears once.
    """
    _, candidates = align(target, phrase)
    assert candidates
    for candidate in candidates:
        letters = candidate.target_word
        assert len(candidate.expansion) == len(letters)
        assert len(candidate.mappings) == len(letters)
        assert candidate.expansion_text == rendered(candidate)
        assert candidate.unmapped_letters == [
            letters[position] for position, word in enumerate(candidate.expansion) if not word
        ]


@pytest.mark.parametrize(("target", "phrase"), ALIGN_CASES)
def test_alignment_candidates_are_ranked_best_first(target: str, phrase: str) -> None:
    _, candidates = align(target, phrase)
    scores = [candidate.score for candidate in candidates]
    assert scores == sorted(scores, reverse=True)
    assert len({candidate.expansion_text for candidate in candidates}) == len(candidates)


@pytest.mark.parametrize("limit", [1, 3, 7])
def test_align_honours_the_candidate_limit(limit: int) -> None:
    _, candidates = align("RAM", "Rapid Analysis of Modern Systems Engineering Data", limit=limit)
    assert len(candidates) == limit


def test_align_defaults_to_max_candidates() -> None:
    config = Config(max_candidates=4)
    _, candidates = align("RAM", "Rapid Analysis of Modern Systems Engineering Data", config=config)
    assert len(candidates) == 4


# ---------------------------------------------------------------------------
# align — INITIAL beats INTERNAL
# ---------------------------------------------------------------------------
def test_initial_alignment_is_preferred_over_an_internal_one() -> None:
    """``B`` can come from ``Album`` (offset 2) or ``Beta`` (offset 0); the initial wins.

    Both alignments are legal — either leaves ``Charlie`` free for ``C`` — so
    the dynamic program has a genuine choice, and the 10/3 gap decides it.
    """
    config = Config()
    _, candidates = align("BC", "Album Beta Charlie", config=config)
    texts = [candidate.expansion_text for candidate in candidates]
    assert "Beta Charlie" in texts
    assert "Album Charlie" in texts
    assert texts.index("Beta Charlie") < texts.index("Album Charlie")

    initial = next(c for c in candidates if c.expansion_text == "Beta Charlie")
    internal = next(c for c in candidates if c.expansion_text == "Album Charlie")
    assert [mapping.kind for mapping in initial.mappings] == [MappingKind.INITIAL] * 2
    assert [mapping.kind for mapping in internal.mappings] == [
        MappingKind.INTERNAL,
        MappingKind.INITIAL,
    ]

    weights = config.weights
    assert initial.breakdown is not None
    assert internal.breakdown is not None
    assert initial.breakdown.positional == pytest.approx(2 * weights.initial_weight)
    assert internal.breakdown.positional == pytest.approx(
        weights.internal_weight + weights.initial_weight
    )
    # Both drop exactly one critical token, so the whole gap is positional.
    assert initial.breakdown.information_loss == internal.breakdown.information_loss
    assert initial.score - internal.score == pytest.approx(
        weights.initial_weight - weights.internal_weight
    )


# ---------------------------------------------------------------------------
# align — sub-word (CONTIGUOUS) matching
# ---------------------------------------------------------------------------
def test_a_letter_with_no_word_initial_is_taken_from_inside_the_previous_word() -> None:
    """``X`` starts no word here, so it comes from ``Exchange`` right after ``E``.

    Under a strictly increasing token order the ``X`` had nowhere to go and was
    left ``UNMAPPED`` at coverage 0.80. The natural reading maps it to offset 1
    of the token the ``E`` already used, which is exactly what
    ``MappingKind.CONTIGUOUS`` and ``ScoringWeights.contiguous_weight`` exist
    to score.
    """
    config = Config()
    _, candidates = align("NEXUS", "Network Exchange Unified Security", config=config)
    best = candidates[0]
    assert best.coverage == 1.0
    assert best.unmapped_letters == []
    assert best.expansion_text == "Network Exchange Unified Security"
    # The token appears once in the reading but twice in the per-letter list.
    assert best.expansion == [
        "Network",
        "Exchange",
        "Exchange",
        "Unified",
        "Security",
    ]
    assert [mapping.kind for mapping in best.mappings] == [
        MappingKind.INITIAL,
        MappingKind.INITIAL,
        MappingKind.CONTIGUOUS,
        MappingKind.INITIAL,
        MappingKind.INITIAL,
    ]
    assert mapped_steps(best) == [(0, 0), (1, 0), (1, 1), (2, 0), (3, 0)]

    weights = config.weights
    assert best.breakdown is not None
    assert best.breakdown.positional == pytest.approx(
        4 * weights.initial_weight + weights.contiguous_weight
    )
    assert best.breakdown.information_loss == 0.0


def test_contiguous_mappings_are_reachable_and_weighted_as_such() -> None:
    """``CONTIGUOUS`` carries ``contiguous_weight``, not the internal one."""
    config = Config()
    _, candidates = align("NEXUS", "Network Exchange Unified Security", config=config)
    contiguous = [
        mapping
        for candidate in candidates
        for mapping in candidate.mappings
        if mapping.kind is MappingKind.CONTIGUOUS
    ]
    assert contiguous
    for mapping in contiguous:
        assert mapping.weight == pytest.approx(config.weights.contiguous_weight)
        assert mapping.char_offset is not None and mapping.char_offset > 0


@pytest.mark.parametrize(
    ("target", "phrase"),
    [
        ("PDF", "Portable Document Format"),
        ("API", "Application Programming Interface"),
    ],
)
def test_one_letter_per_token_alignments_stay_all_initial(target: str, phrase: str) -> None:
    """Sub-word matching must not disturb the textbook one-word-per-letter case."""
    _, candidates = align(target, phrase)
    best = candidates[0]
    assert best.coverage == 1.0
    assert [mapping.kind for mapping in best.mappings] == [MappingKind.INITIAL] * len(target)
    assert mapped_indices(best) == list(range(len(target)))
    assert len(set(mapped_indices(best))) == len(target)


# ---------------------------------------------------------------------------
# align — the full objective decides, at every limit
# ---------------------------------------------------------------------------
def test_a_limit_of_one_still_returns_the_full_objective_best() -> None:
    """``limit=1`` must not hand back a positional-only winner.

    ``DREAM`` cannot be spelled out of this phrase whichever way it is cut, so
    the choice is between alignments that differ in how much of the phrase they
    represent. Dropping ``Portable`` buys positional score but forfeits a
    critical token, which costs ``delta`` -- and truncating the k-best list
    before the full-objective re-rank used to hide that entirely.
    """
    _, alone = align("DREAM", "Portable Document Format", limit=1)
    _, several = align("DREAM", "Portable Document Format", limit=5)
    assert alone[0].expansion_text == "Portable Document Format"
    assert alone[0].to_dict() == several[0].to_dict()
    assert alone[0].score == pytest.approx(max(c.score for c in several))
    # The positional-only winner is still reachable -- just not first.
    runner_up = next(c for c in several if c.expansion_text == "Document Format")
    assert runner_up.breakdown is not None
    assert alone[0].breakdown is not None
    assert runner_up.breakdown.information_loss > alone[0].breakdown.information_loss
    assert runner_up.score < alone[0].score


@pytest.mark.parametrize(
    ("target", "phrase"), [*ALIGN_CASES, ("DREAM", "Portable Document Format")]
)
def test_the_first_candidate_is_the_same_at_every_limit(target: str, phrase: str) -> None:
    """The head of the list never depends on how many alternatives were asked for."""
    _, wide = align(target, phrase, limit=40)
    assert wide
    for limit in (1, 2, 3, 7):
        _, narrow = align(target, phrase, limit=limit)
        assert narrow[0].to_dict() == wide[0].to_dict()
        assert narrow == wide[: len(narrow)]


@pytest.mark.parametrize(("target", "phrase"), ALIGN_CASES)
def test_no_returned_candidate_outscores_the_first(target: str, phrase: str) -> None:
    """The pool is re-ranked by ``S(A, T)`` before it is truncated."""
    _, candidates = align(target, phrase, limit=40)
    assert candidates
    assert candidates[0].score == pytest.approx(max(c.score for c in candidates))


def test_engine_score_reports_the_full_objective(engine: AcronymEngine) -> None:
    """``AcronymEngine.score`` asks for ``limit=1``; it must still get the optimum."""
    scored = engine.score("DREAM", "Portable Document Format")
    _, candidates = align("DREAM", "Portable Document Format", limit=5)
    assert scored.score == pytest.approx(max(c.score for c in candidates))
    assert scored.covered_token_indices == [0, 1, 2]


# ---------------------------------------------------------------------------
# align — target normalisation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("raw", "canonical"),
    [
        ("N.E.X.U.S.", "NEXUS"),
        ("n-e-x-u-s", "NEXUS"),
        ("  nexus  ", "NEXUS"),
        ("Ne.Xu S", "NEXUS"),
    ],
)
def test_non_alphanumeric_target_characters_are_filtered_out(raw: str, canonical: str) -> None:
    """A dotted ``N.E.X.U.S.`` behaves exactly like ``NEXUS``."""
    phrase = "Next Extraordinary Xenon Unified Systems"
    _, decorated = align(raw, phrase)
    _, plain = align(canonical, phrase)
    assert [candidate.target_word for candidate in decorated] == [
        candidate.target_word for candidate in plain
    ]
    assert decorated[0].target_word == canonical
    assert [candidate.to_dict() for candidate in decorated] == [
        candidate.to_dict() for candidate in plain
    ]


def test_lowercase_targets_are_uppercased() -> None:
    _, candidates = align("pdf", "Portable Document Format")
    assert candidates[0].target_word == "PDF"
    assert [mapping.character for mapping in candidates[0].mappings] == ["P", "D", "F"]


# ---------------------------------------------------------------------------
# synthesize
# ---------------------------------------------------------------------------
def test_synthesize_draws_every_word_from_the_lexicon(english_lexicon: Lexicon) -> None:
    """Words come from the bound vocabulary and start with the right letter."""
    candidates = synthesize("NEXUS")
    assert candidates
    for candidate in candidates:
        assert candidate.target_word == "NEXUS"
        assert len(candidate.expansion) == 5
        for letter, word in zip("NEXUS", candidate.expansion):
            if not word:
                assert letter in candidate.unmapped_letters
                continue
            assert word in english_lexicon
            assert word[:1].upper() == letter


def test_synthesize_candidates_are_distinct() -> None:
    candidates = synthesize("NEXUS")
    texts = [candidate.expansion_text for candidate in candidates]
    assert len(texts) == len(set(texts))
    tuples = [tuple(candidate.expansion) for candidate in candidates]
    assert len(tuples) == len(set(tuples))


def test_synthesize_maps_every_word_as_an_initial() -> None:
    config = Config()
    candidates = synthesize("RAM", vocabulary=SMALL_VOCABULARY, config=config)
    assert candidates
    for candidate in candidates:
        assert [mapping.kind for mapping in candidate.mappings] == [MappingKind.INITIAL] * 3
        assert candidate.coverage == 1.0
        assert candidate.breakdown is not None
        assert candidate.breakdown.positional == pytest.approx(3 * config.weights.initial_weight)
        assert candidate.breakdown.information_loss == 0.0


@pytest.mark.parametrize("vocabulary", [[], (), ["   "], ["zebra", "yak"]])
def test_synthesize_with_an_unusable_vocabulary_returns_empty(
    vocabulary: Sequence[str],
) -> None:
    """No word for any letter yields ``[]`` rather than an exception."""
    assert synthesize("RAM", vocabulary=vocabulary) == []


def test_synthesize_records_an_unservable_letter_instead_of_dropping_the_candidate() -> None:
    """``Q`` has no word here, so its slot is empty and the letter is recorded."""
    candidates = synthesize("RQ", vocabulary=["rapid", "robust"])
    assert candidates
    for candidate in candidates:
        assert candidate.target_word == "RQ"
        assert len(candidate.expansion) == 2
        assert candidate.expansion[1] == ""
        assert candidate.expansion[0].startswith("r")
        assert candidate.unmapped_letters == ["Q"]
        assert candidate.coverage == pytest.approx(0.5)
        assert candidate.expansion_text == candidate.expansion[0]
        assert candidate.mappings[1].kind is MappingKind.UNMAPPED


def test_synthesize_prefers_shorter_words_then_alphabetical_order() -> None:
    """``_word_rank_key`` puts 3-12 character words first, shortest, then a-z."""
    candidates = synthesize("A", vocabulary=["alpha", "able", "ab", "astonishing"], limit=4)
    assert [candidate.expansion_text for candidate in candidates] == [
        "able",
        "alpha",
        "astonishing",
        "ab",
    ]


@pytest.mark.parametrize("limit", [1, 2, 5])
def test_synthesize_honours_the_candidate_limit(limit: int) -> None:
    assert len(synthesize("NEXUS", limit=limit)) == limit


@pytest.mark.parametrize("limit", [0, -3])
def test_synthesize_with_a_non_positive_limit_returns_empty(limit: int) -> None:
    assert synthesize("RAM", vocabulary=SMALL_VOCABULARY, limit=limit) == []


@pytest.mark.parametrize("target", ["", "  ", "!!!"])
def test_synthesize_with_no_alphanumeric_target_returns_empty(target: str) -> None:
    assert synthesize(target, vocabulary=SMALL_VOCABULARY) == []


def test_synthesize_round_robins_so_alternatives_differ_in_every_slot() -> None:
    candidates = synthesize("RAM", vocabulary=SMALL_VOCABULARY)
    assert [candidate.expansion for candidate in candidates] == [
        ["rapid", "agile", "modern"],
        ["reliable", "adaptive", "modular"],
    ]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(("target", "phrase"), ALIGN_CASES)
def test_align_is_deterministic(target: str, phrase: str) -> None:
    first = align(target, phrase)[1]
    second = align(target, phrase)[1]
    assert [candidate.to_dict() for candidate in first] == [
        candidate.to_dict() for candidate in second
    ]


@pytest.mark.parametrize("target", ["NEXUS", "RAM", "QZ"])
def test_synthesize_is_deterministic(target: str) -> None:
    first = synthesize(target)
    second = synthesize(target)
    assert [candidate.to_dict() for candidate in first] == [
        candidate.to_dict() for candidate in second
    ]


def test_synthesize_is_insensitive_to_vocabulary_iteration_order() -> None:
    """The ranking key, not the input order, decides the result."""
    forward = synthesize("RAM", vocabulary=SMALL_VOCABULARY)
    backward = synthesize("RAM", vocabulary=list(reversed(SMALL_VOCABULARY)))
    assert [candidate.to_dict() for candidate in forward] == [
        candidate.to_dict() for candidate in backward
    ]


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------
LONG_PHRASE = " ".join(
    (
        "Rapid Analysis Modern Systems Engineering Data Platform Vector Signal",
        "Adaptive Neural Kernel Beacon Quantum Fabric Storage Layer Optimal",
        "Transfer Gateway Cluster Runtime Pipeline Ledger Manifest Telemetry",
        "Observatory",
    )
)


def _align_seconds(phrase: str, target: str = "NEXUS", repeats: int = 3) -> float:
    """Fastest of ``repeats`` alignments, with the first call discarded as warm-up."""
    tokenizer, generator = pipeline(Config())
    tokens = tokenizer.tokenize(phrase)
    generator.align(target, tokens)  # warm the caches the first call would pay for
    best = float("inf")
    for _ in range(repeats):
        started = time.perf_counter()
        candidates = generator.align(target, tokens)
        best = min(best, time.perf_counter() - started)
    assert candidates
    return best


@pytest.mark.slow
def test_alignment_cost_grows_sub_quadratically_in_token_count() -> None:
    """Doubling the phrase must not quadruple the alignment cost.

    This is the machine-independent form of the guarantee: linear work doubles
    and quadratic work quadruples, so a threshold between the two decides the
    question on any hardware. A wall-clock ceiling would instead be a claim
    about somebody else's CPU -- and was, in fact, the first thing to fail on a
    shared CI runner.
    """
    single = _align_seconds(LONG_PHRASE)
    double = _align_seconds(LONG_PHRASE + " " + LONG_PHRASE)
    assert double < 3.0 * max(single, 0.005), (
        f"alignment looks super-linear: {single:.4f}s for one copy, {double:.4f}s for two"
    )


@pytest.mark.slow
def test_alignment_of_a_long_phrase_does_not_hang() -> None:
    """A 27-token phrase completes within a calibrated budget.

    The budget is scaled by :func:`conftest.machine_factor`, so this catches a
    reintroduced blow-up without asserting a performance number the benchmark
    suite is the proper home for.
    """
    tokenizer, generator = pipeline(Config())
    tokens = tokenizer.tokenize(LONG_PHRASE)
    assert len(tokens) >= 25
    started = time.perf_counter()
    candidates = generator.align("NEXUS", tokens)
    elapsed = time.perf_counter() - started
    assert candidates
    assert elapsed < timing_budget(0.1)


#: Sixty copies of one word. Every letter of ``NEXUS`` occurs in it, so the
#: phrase admits C(60, 5)-ish structurally distinct alignments that all read
#: identically -- the shape that used to burn the whole node budget.
REPEATED_PHRASE = " ".join(["nexus"] * 60)

#: The same sixty slots, all different, as the control.
DISTINCT_PHRASE = " ".join(f"nexus{index:02d}" for index in range(60))


@pytest.mark.slow
def test_a_phrase_of_repeated_words_does_not_stall_the_search() -> None:
    """Interchangeable tokens collapse before expansion, not after.

    Sixty identical words used to exhaust ``max_search_nodes`` producing one
    candidate, because the distinctness filter only ran once a complete
    alignment had been popped. It now costs about what sixty distinct words
    cost.
    """
    tokenizer, generator = pipeline(Config())
    repeated = tokenizer.tokenize(REPEATED_PHRASE)
    distinct = tokenizer.tokenize(DISTINCT_PHRASE)
    assert len(repeated) == len(distinct) == 60
    generator.align("NEXUS", repeated)  # warm the caches the first call would pay for
    generator.align("NEXUS", distinct)

    started = time.perf_counter()
    candidates = generator.align("NEXUS", repeated)
    elapsed = time.perf_counter() - started
    assert candidates
    assert elapsed < timing_budget(0.1), f"repeated words took {elapsed:.3f}s"

    started = time.perf_counter()
    control = generator.align("NEXUS", distinct)
    control_elapsed = time.perf_counter() - started
    assert len(control) == Config().max_candidates
    assert control_elapsed < timing_budget(0.1)


@pytest.mark.slow
def test_synthesis_over_the_full_lexicon_stays_fast() -> None:
    _, generator = pipeline(Config())
    generator.synthesize("ACRONYMKIT")
    started = time.perf_counter()
    candidates = generator.synthesize("ACRONYMKIT")
    assert candidates
    assert time.perf_counter() - started < timing_budget(0.5)


# ---------------------------------------------------------------------------
# Property-based invariants
# ---------------------------------------------------------------------------
targets = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=5)
phrases = st.lists(st.sampled_from(WORD_POOL), min_size=1, max_size=6).map(" ".join)


@given(target=targets, phrase=phrases)
@settings(max_examples=60, deadline=None)
def test_property_alignment_invariants(target: str, phrase: str) -> None:
    _, candidates = align(target, phrase, limit=4)
    assert candidates
    for candidate in candidates:
        letters = candidate.target_word
        assert letters == target
        assert len(candidate.expansion) == len(letters)
        assert len(candidate.mappings) == len(letters)

        mapped = len(letters) - len(candidate.unmapped_letters)
        assert candidate.coverage == pytest.approx(mapped / len(letters))
        assert 0.0 <= candidate.coverage <= 1.0

        assert candidate.expansion_text == rendered(candidate)
        indices = mapped_indices(candidate)
        assert len(indices) == mapped

        steps = mapped_steps(candidate)
        assert len(steps) == mapped
        for earlier, later in zip(steps, steps[1:]):
            assert earlier[0] <= later[0]
            if earlier[0] == later[0]:
                assert earlier[1] < later[1]


@given(target=targets, phrase=phrases)
@settings(max_examples=40, deadline=None)
def test_property_alignment_is_deterministic(target: str, phrase: str) -> None:
    first = align(target, phrase, limit=4)[1]
    second = align(target, phrase, limit=4)[1]
    assert [candidate.to_dict() for candidate in first] == [
        candidate.to_dict() for candidate in second
    ]


@given(target=targets, phrase=phrases)
@settings(max_examples=30, deadline=None)
def test_property_candidates_round_trip_through_json(target: str, phrase: str) -> None:
    _, candidates = align(target, phrase, limit=3)
    for candidate in candidates:
        restored = BackronymCandidate.model_validate(json.loads(candidate.to_json()))
        assert restored == candidate


@given(
    raw=st.lists(st.sampled_from(list("ABCDEFabcdef .-_/")), min_size=1, max_size=10).map("".join)
)
@settings(max_examples=60, deadline=None)
def test_property_target_is_reduced_to_uppercase_alphanumerics(raw: str) -> None:
    expected = "".join(char for char in raw.upper() if char.isalnum())
    _, candidates = align(raw, "Portable Document Format", limit=2)
    if not expected:
        assert candidates == []
        return
    assert candidates
    for candidate in candidates:
        assert candidate.target_word == expected
        assert [mapping.character for mapping in candidate.mappings] == list(expected)


@given(
    target=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=4),
    vocabulary=st.lists(st.sampled_from(WORD_POOL), min_size=0, max_size=8),
)
@settings(max_examples=50, deadline=None)
def test_property_synthesis_invariants(target: str, vocabulary: list[str]) -> None:
    candidates = synthesize(target, vocabulary=vocabulary, limit=3)
    served = {word[0].upper() for word in vocabulary}
    if not served & set(target):
        assert candidates == []
        return
    assert candidates
    for candidate in candidates:
        assert candidate.target_word == target
        assert len(candidate.expansion) == len(target)
        for letter, word in zip(target, candidate.expansion):
            if word:
                assert word in vocabulary
                assert word[0].upper() == letter
            else:
                assert letter not in served
        assert candidate.expansion_text == " ".join(word for word in candidate.expansion if word)
        mapped = len(target) - len(candidate.unmapped_letters)
        assert candidate.coverage == pytest.approx(mapped / len(target))
