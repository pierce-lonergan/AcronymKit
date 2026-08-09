"""Behavioural tests for :mod:`acronymkit.generator`.

The generator owns the *search*; :mod:`acronymkit.scoring` owns the arithmetic.
These tests therefore assert on the search contract — ordering, filters,
budgets, atomicity of existing acronyms and determinism — and pin numbers only
where the mathematical contract fixes them exactly (an all-``INITIAL``
alignment of ``k`` tokens has positional term ``k * initial_weight``).
"""

from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
import time
from functools import cache
from pathlib import Path
from typing import Optional, Sequence

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import acronymkit
from acronymkit import generator as generator_module
from acronymkit.config import STRATEGY_WEIGHTS, Config, ScoringWeights
from acronymkit.enums import CaseStyle, MappingKind, ScoringStrategy, TokenRole
from acronymkit.exceptions import NoCandidateError
from acronymkit.generator import ForwardGenerator
from acronymkit.lexicon import Lexicon
from acronymkit.models import AcronymCandidate, LetterMapping, Token
from acronymkit.phonetics import CharNGramModel, has_vowel
from acronymkit.scoring import Scorer, build_mappings
from acronymkit.tokenizer import Tokenizer
from conftest import CANONICAL_ACRONYMS

# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------

#: Every non-sentinel strategy preset. ``CUSTOM`` needs explicit weights and is
#: therefore not constructible from a bare ``Config(scoring_strategy=...)``.
STRATEGIES = [strategy for strategy in ScoringStrategy if strategy is not ScoringStrategy.CUSTOM]

#: Content words used to build synthetic phrases. All are >= 5 characters and
#: none is a stop word, so every one of them is eligible under any config.
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


@cache
def pipeline(config: Config) -> tuple[Tokenizer, ForwardGenerator]:
    """Build the tokenizer/generator pair the engine would build for ``config``.

    Mirrors ``AcronymEngine``'s wiring (shared scorer, bundled lexicon and
    n-gram model) without paying for the engine's tier resolution. Cached on the
    frozen config so repeated parametrisations reuse one pipeline.
    """
    lexicon = Lexicon.load(config.language, path=config.lexicon_path)
    ngram = CharNGramModel.load(config.language, path=config.ngram_model_path)
    return Tokenizer(config), ForwardGenerator(config, Scorer(config, lexicon, ngram))


def generate(config: Config, phrase: str) -> tuple[list[Token], list[AcronymCandidate], int, bool]:
    """Tokenize ``phrase`` and run the generator over it."""
    tokenizer, generator = pipeline(config)
    tokens = tokenizer.tokenize(phrase)
    candidates, evaluated, truncated = generator.generate(tokens)
    return tokens, candidates, evaluated, truncated


def acronyms(config: Config, phrase: str) -> list[str]:
    """Return just the acronym strings the generator produced for ``phrase``."""
    return [candidate.acronym for candidate in generate(config, phrase)[1]]


def order_key(candidate: AcronymCandidate) -> tuple[float, int, str]:
    """The documented total order: ``(-score, len(acronym), acronym)``."""
    return (-candidate.score, len(candidate.acronym), candidate.acronym)


def eligible_tokens(tokens: Sequence[Token]) -> list[Token]:
    """The tokens the search is allowed to draw characters from."""
    return [token for token in tokens if token.is_eligible and token.letters]


def letters_per_token(candidate: AcronymCandidate) -> dict[int, int]:
    """Count how many acronym characters each token donated."""
    counts: dict[int, int] = {}
    for mapping in candidate.mappings:
        if mapping.token_index is not None:
            counts[mapping.token_index] = counts.get(mapping.token_index, 0) + 1
    return counts


def plain_initialism(config: Config, tokens: Sequence[Token]) -> str:
    """The first letter of every eligible token, cased and length-capped."""
    letters = "".join(token.letters[:1] for token in eligible_tokens(tokens))
    return config.case_style.apply(letters[: config.max_acronym_length])


def exhaustive_best(config: Config, tokens: Sequence[Token]) -> AcronymCandidate:
    """Score *every* reachable alignment and return the best-ranked candidate.

    A deliberately naive oracle: it takes the cross product of the per-token
    branches with :func:`itertools.product` and scores each combination with the
    same :class:`~acronymkit.scoring.Scorer` the engine uses. It therefore
    answers "what *should* the search have returned?" while sharing none of the
    search's own code, which is what makes it usable as an optimality check.
    """
    _, generator = pipeline(config)
    scorer = generator.scorer
    weights = scorer.weights

    options: list[list[Optional[tuple[int, str]]]] = []
    for token in eligible_tokens(tokens):
        if token.role is TokenRole.ACRONYM:
            pieces = [token.letters]
        else:
            cap = min(config.max_letters_per_token, len(token.letters))
            pieces = [token.letters[:count] for count in range(1, cap + 1)]
        choices: list[Optional[tuple[int, str]]] = [(token.index, piece) for piece in pieces]
        if config.allow_token_skipping:
            choices.append(None)
        options.append(choices)

    best: Optional[AcronymCandidate] = None
    for combination in itertools.product(*options):
        taken = [choice for choice in combination if choice is not None]
        chars = "".join(piece for _, piece in taken)
        if not config.min_acronym_length <= len(chars) <= config.max_acronym_length:
            continue
        cased = config.case_style.apply(chars)
        if config.require_vowel and not has_vowel(cased):
            continue
        assignments: list[tuple[int, Optional[int], Optional[int]]] = []
        position = 0
        for index, piece in taken:
            for offset in range(len(piece)):
                assignments.append((position, index, offset))
                position += 1
        candidate = scorer.build_candidate(
            cased,
            tokens,
            build_mappings(cased, assignments, tokens, weights),
            {index for index, _ in taken},
        )
        if best is None or order_key(candidate) < order_key(best):
            best = candidate
    assert best is not None, "the oracle found no alignment inside the length bounds"
    return best


ORDERING_PHRASES = [
    "Portable Document Format",
    "Application Programming Interface",
    "National Aeronautics and Space Administration",
    "Self Contained Underwater Breathing Apparatus",
    "Light Amplification by Stimulated Emission of Radiation",
    "Rapid Analysis of Modern Systems Engineering Data Platform",
    "Multi-Factor Authentication for the API",
    "3 Dimensional Printing Service",
]

ORDERING_CONFIGS = {
    "default": Config(),
    "strict": Config(scoring_strategy=ScoringStrategy.STRICT_INITIALISM),
    "max-pronounceable": Config(scoring_strategy=ScoringStrategy.MAX_PRONOUNCEABLE),
    "dictionary": Config(scoring_strategy=ScoringStrategy.DICTIONARY_BACKRONYM),
    "single-letter": Config(allow_multi_letter_tokens=False),
    "no-skipping": Config(allow_token_skipping=False),
    "lower": Config(case_style=CaseStyle.LOWER),
    "narrow-top-n": Config(max_candidates=3),
    "fast-preset": Config.fast(),
}


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phrase", ORDERING_PHRASES)
@pytest.mark.parametrize("config_id", sorted(ORDERING_CONFIGS))
def test_candidates_are_sorted_by_score_then_length_then_alphabetically(
    config_id: str, phrase: str
) -> None:
    """The returned list obeys ``(-score, len(acronym), acronym)`` exactly."""
    _, candidates, _, _ = generate(ORDERING_CONFIGS[config_id], phrase)
    keys = [order_key(candidate) for candidate in candidates]
    assert keys == sorted(keys)


@pytest.mark.parametrize("phrase", ORDERING_PHRASES)
def test_acronym_strings_are_unique(phrase: str) -> None:
    """De-duplication keys on the cased acronym, so no string repeats."""
    names = acronyms(Config(), phrase)
    assert len(names) == len(set(names))


def test_ordering_tie_break_prefers_shorter_then_alphabetical() -> None:
    """Equal scores are broken by length first, then lexicographically.

    ``beta`` and ``gamma`` are zeroed so the phonotactic and lexical terms stop
    separating otherwise-equivalent candidates and genuine exact-float ties
    appear for the tie-break to resolve.
    """
    config = Config(
        scoring_strategy=ScoringStrategy.CUSTOM,
        scoring_weights=ScoringWeights(beta=0.0, gamma=0.0),
    )
    _, candidates, _, _ = generate(config, "Rapid Analysis of Modern Systems Engineering Data")
    by_score: dict[float, list[AcronymCandidate]] = {}
    for candidate in candidates:
        by_score.setdefault(candidate.score, []).append(candidate)
    ties = [group for group in by_score.values() if len(group) > 1]
    assert ties, "expected at least one exact score tie once beta and gamma are zero"
    for group in ties:
        pairs = [(len(candidate.acronym), candidate.acronym) for candidate in group]
        assert pairs == sorted(pairs)


# ---------------------------------------------------------------------------
# The plain-initialism guarantee
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(("phrase", "expected"), CANONICAL_ACRONYMS)
@pytest.mark.parametrize("strategy", STRATEGIES)
def test_plain_initialism_is_always_returned(
    strategy: ScoringStrategy, phrase: str, expected: str
) -> None:
    """The textbook initialism is present whatever the ranking preset says.

    Presence is guaranteed; being *primary* is not — the strategy decides rank.
    """
    assert expected in acronyms(Config(scoring_strategy=strategy), phrase)


def test_initialism_survives_top_n_truncation_without_breaking_the_order() -> None:
    """A low-ranked initialism keeps the final slot and the list stays sorted."""
    phrase = "Rapid Analysis Modern Systems Engineering Data Platform Vector Signal Adaptive"
    for max_candidates in (3, 5, 10):
        config = Config(max_candidates=max_candidates)
        tokens, candidates, _, _ = generate(config, phrase)
        initialism = "".join(token.letters[:1] for token in eligible_tokens(tokens))
        initialism = initialism[: config.max_acronym_length]
        names = [candidate.acronym for candidate in candidates]
        assert initialism in names
        keys = [order_key(candidate) for candidate in candidates]
        assert keys == sorted(keys)


def test_initialism_is_still_subject_to_the_dictionary_filter() -> None:
    """The safety net does not smuggle a non-word past ``require_dictionary_word``."""
    names = acronyms(Config(require_dictionary_word=True), "Portable Document Format")
    assert "PDF" not in names
    assert names, "a dictionary hit exists for this phrase"


# ---------------------------------------------------------------------------
# Length bounds
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(("minimum", "maximum"), [(1, 3), (2, 4), (2, 6), (3, 5), (4, 8)])
@pytest.mark.parametrize("phrase", ORDERING_PHRASES[:5])
def test_every_candidate_length_is_within_the_configured_bounds(
    minimum: int, maximum: int, phrase: str
) -> None:
    """No candidate escapes ``[min_acronym_length, max_acronym_length]``."""
    config = Config(min_acronym_length=minimum, max_acronym_length=maximum)
    for candidate in generate(config, phrase)[1]:
        assert minimum <= len(candidate.acronym) <= maximum
        assert candidate.length == len(candidate.acronym)


def test_unreachable_length_window_raises_no_candidate() -> None:
    """Two tokens cannot fill a five-character minimum, so the pool empties."""
    config = Config(min_acronym_length=5, max_acronym_length=6)
    with pytest.raises(NoCandidateError):
        generate(config, "Quality Assurance")


# ---------------------------------------------------------------------------
# Final filters
# ---------------------------------------------------------------------------
def test_require_vowel_rejects_every_vowel_free_candidate() -> None:
    names = acronyms(Config(require_vowel=True), "Portable Document Format")
    assert names
    assert all(has_vowel(name) for name in names)
    assert "PDF" not in names


def test_require_vowel_with_no_reachable_vowel_raises() -> None:
    with pytest.raises(NoCandidateError, match="require_vowel"):
        generate(Config(require_vowel=True), "Strong Ships Trend")


def test_require_dictionary_word_keeps_only_real_words(english_lexicon: Lexicon) -> None:
    names = acronyms(Config(require_dictionary_word=True), "Portable Document Format")
    assert names
    for name in names:
        assert name.casefold() in english_lexicon


def test_require_dictionary_word_with_no_reachable_word_raises() -> None:
    """An unreachable target raises rather than returning an empty list."""
    with pytest.raises(NoCandidateError, match="require_dictionary_word"):
        generate(Config(require_dictionary_word=True), "Zzz Qqq Xxx")


def test_dictionary_candidates_are_flagged(english_lexicon: Lexicon) -> None:
    """``is_dictionary_word`` agrees with the lexicon for every candidate."""
    for candidate in generate(Config(), "Portable Document Format")[1]:
        assert candidate.is_dictionary_word == (candidate.acronym.casefold() in english_lexicon)


# ---------------------------------------------------------------------------
# Search-shape switches
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "phrase",
    [
        "Portable Document Format Engine",
        "Random Access Memory",
        "Rapid Analysis Modern Systems",
    ],
)
def test_no_token_skipping_means_every_candidate_covers_every_eligible_token(
    phrase: str,
) -> None:
    config = Config(allow_token_skipping=False)
    tokens, candidates, _, _ = generate(config, phrase)
    wanted = {token.index for token in eligible_tokens(tokens)}
    assert candidates
    for candidate in candidates:
        assert set(candidate.covered_token_indices) == wanted
        assert candidate.skipped_token_indices == []


@pytest.mark.parametrize(
    "phrase",
    [
        "Portable Document Format Engine",
        "Central Processing Unit",
        "Rapid Analysis Modern Systems Engineering",
    ],
)
def test_single_letter_mode_takes_exactly_one_character_per_covered_token(
    phrase: str,
) -> None:
    config = Config(allow_multi_letter_tokens=False)
    _, candidates, _, _ = generate(config, phrase)
    assert candidates
    for candidate in candidates:
        counts = letters_per_token(candidate)
        assert counts, "a candidate must be backed by at least one token"
        assert set(counts.values()) == {1}
        assert len(candidate.acronym) == len(counts)
        assert all(mapping.kind is MappingKind.INITIAL for mapping in candidate.mappings)


def test_single_letter_mode_forces_max_letters_per_token_to_one() -> None:
    """``Config`` normalises the letter budget so the two switches cannot disagree."""
    assert (
        Config(allow_multi_letter_tokens=False, max_letters_per_token=4).max_letters_per_token == 1
    )


# ---------------------------------------------------------------------------
# Existing acronyms are atomic
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "phrase",
    [
        "Simple Interface for the API",
        "Extended Markup for the API",
        "Secure Gateway for the API",
    ],
)
def test_acronym_role_tokens_are_never_split(phrase: str) -> None:
    """A token the tokenizer already read as an acronym is all-or-nothing."""
    tokens, candidates, _, _ = generate(Config(), phrase)
    atomic = [token for token in tokens if token.role is TokenRole.ACRONYM]
    assert atomic, "the phrase must contain a preserved acronym for this to mean anything"
    used_in_full = False
    for candidate in candidates:
        counts = letters_per_token(candidate)
        for token in atomic:
            taken = counts.get(token.index, 0)
            assert taken in (0, len(token.letters)), (
                f"{candidate.acronym!r} took {taken} of {len(token.letters)} characters "
                f"from the atomic token {token.text!r}"
            )
            used_in_full = used_in_full or taken == len(token.letters)
    assert used_in_full, "at least one candidate should reuse the acronym verbatim"


def test_acronym_role_token_is_not_split_when_the_initialism_overflows() -> None:
    """An atomic ACRONYM token is dropped whole, never clipped, by the safety net.

    Regression test. ``_plain_initialism`` used to clip the atomic piece with
    ``piece[:room]`` when the injected initialism overflowed
    ``max_acronym_length``, so this phrase yielded ``"ANDIAP"`` — two of the
    three characters of the ``"API"`` token. That contradicted the module
    docstring's promise that ``"API"`` can never degrade into ``"AP"`` or
    ``"A"``. The beam search always treated the token as indivisible; only the
    injected safety net did not.
    """
    phrase = "Advanced Network Data Interchange for the API"
    tokens, candidates, _, _ = generate(Config(), phrase)
    atomic = [token for token in tokens if token.role is TokenRole.ACRONYM]
    assert atomic
    for candidate in candidates:
        counts = letters_per_token(candidate)
        for token in atomic:
            assert counts.get(token.index, 0) in (0, len(token.letters))


# ---------------------------------------------------------------------------
# Casing
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("style", "check"),
    [
        (CaseStyle.UPPER, lambda value: value == value.upper()),
        (CaseStyle.LOWER, lambda value: value == value.lower()),
        (CaseStyle.TITLE, lambda value: value == value[:1].upper() + value[1:].lower()),
    ],
    ids=["upper", "lower", "title"],
)
def test_case_style_is_applied_to_the_returned_strings(style: CaseStyle, check) -> None:
    _, candidates, _, _ = generate(Config(case_style=style), "Portable Document Format")
    assert candidates
    for candidate in candidates:
        assert check(candidate.acronym)


def test_case_style_only_re_cases_the_same_letters() -> None:
    """Changing the case style permutes nothing but the casing."""
    upper = acronyms(Config(case_style=CaseStyle.UPPER), "Portable Document Format")
    lower = acronyms(Config(case_style=CaseStyle.LOWER), "Portable Document Format")
    title = acronyms(Config(case_style=CaseStyle.TITLE), "Portable Document Format")
    assert [name.lower() for name in upper] == lower
    assert [name.lower() for name in title] == lower


# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------
BUDGET_PHRASE = "Self Contained Underwater Breathing Apparatus"


def test_tiny_node_budget_sets_truncated_without_raising() -> None:
    _, candidates, evaluated, truncated = generate(Config(max_search_nodes=1), BUDGET_PHRASE)
    assert truncated is True
    assert candidates, "the injected initialism survives even an exhausted budget"
    assert evaluated >= 0


def test_tiny_time_budget_sets_truncated_without_raising() -> None:
    _, candidates, _, truncated = generate(Config(search_time_budget_ms=1e-9), BUDGET_PHRASE)
    assert truncated is True
    assert candidates


def test_generous_budgets_do_not_report_truncation() -> None:
    """Five eligible tokens fit the node budget whole, so nothing is cut."""
    _, _, _, truncated = generate(Config(), BUDGET_PHRASE)
    assert truncated is False


def test_node_budget_bounds_the_enumerated_states() -> None:
    """``candidates_evaluated`` overruns the cap by at most one expansion round."""
    config = Config(max_search_nodes=50, search_beam_width=8)
    _, _, evaluated, truncated = generate(config, BUDGET_PHRASE)
    assert truncated is True
    assert evaluated < 10 * config.max_search_nodes


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------
def test_empty_token_sequence_raises_no_candidate() -> None:
    _, generator = pipeline(Config())
    with pytest.raises(NoCandidateError, match="empty token sequence"):
        generator.generate([])


def test_all_ineligible_tokens_raises_no_candidate() -> None:
    tokenizer, generator = pipeline(Config())
    with pytest.raises(NoCandidateError, match="no eligible tokens"):
        generator.generate(tokenizer.tokenize("the of and"))


# ---------------------------------------------------------------------------
# Scoring integration — pinned because the arithmetic fixes the value
# ---------------------------------------------------------------------------
def test_plain_initialism_positional_term_is_exactly_k_initial_weights() -> None:
    """``PDF`` is three ``INITIAL`` mappings, so ``SUM omega == 3 * 10``."""
    config = Config()
    _, candidates, _, _ = generate(config, "Portable Document Format")
    pdf = next(candidate for candidate in candidates if candidate.acronym == "PDF")
    weights = config.weights
    assert [mapping.kind for mapping in pdf.mappings] == [MappingKind.INITIAL] * 3
    assert pdf.breakdown is not None
    assert pdf.breakdown.positional == pytest.approx(3 * weights.initial_weight)
    assert pdf.breakdown.information_loss == 0.0
    assert pdf.breakdown.lexical == 0.0
    assert pdf.score == pytest.approx(pdf.breakdown.total)


def test_second_letter_from_one_token_is_contiguous_not_internal() -> None:
    """``PODF`` continues a matched run, so the extra character is worth 2, not 3."""
    config = Config()
    _, candidates, _, _ = generate(config, "Portable Document Format")
    podf = next(candidate for candidate in candidates if candidate.acronym == "PODF")
    kinds = [mapping.kind for mapping in podf.mappings]
    assert kinds == [
        MappingKind.INITIAL,
        MappingKind.CONTIGUOUS,
        MappingKind.INITIAL,
        MappingKind.INITIAL,
    ]
    weights = config.weights
    assert podf.breakdown is not None
    assert podf.breakdown.positional == pytest.approx(
        3 * weights.initial_weight + weights.contiguous_weight
    )


def test_covered_and_skipped_indices_partition_the_eligible_tokens() -> None:
    tokens, candidates, _, _ = generate(Config(), "Rapid Analysis Modern Systems Engineering")
    wanted = {token.index for token in tokens if token.is_eligible}
    for candidate in candidates:
        covered = set(candidate.covered_token_indices)
        skipped = set(candidate.skipped_token_indices)
        assert covered.isdisjoint(skipped)
        assert wanted <= covered | skipped
        assert candidate.covered_token_indices == sorted(covered)
        assert candidate.skipped_token_indices == sorted(skipped)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
DETERMINISM_PHRASES = [
    "Portable Document Format",
    "Light Amplification by Stimulated Emission of Radiation",
    "Rapid Analysis of Modern Systems Engineering Data Platform",
]


@pytest.mark.parametrize("phrase", DETERMINISM_PHRASES)
def test_repeated_calls_return_identical_output(phrase: str) -> None:
    config = Config()
    first = generate(config, phrase)
    second = generate(config, phrase)
    assert [candidate.to_dict() for candidate in first[1]] == [
        candidate.to_dict() for candidate in second[1]
    ]
    assert first[2:] == second[2:]


#: Executed in a child interpreter under different ``PYTHONHASHSEED`` values.
_HASH_SEED_SCRIPT = """
import json
import sys

from acronymkit.config import Config
from acronymkit.generator import ForwardGenerator
from acronymkit.lexicon import Lexicon
from acronymkit.phonetics import CharNGramModel
from acronymkit.scoring import Scorer
from acronymkit.tokenizer import Tokenizer

config = Config()
scorer = Scorer(
    config,
    Lexicon.load(config.language),
    CharNGramModel.load(config.language),
)
tokenizer = Tokenizer(config)
generator = ForwardGenerator(config, scorer)

payload = []
for phrase in sys.argv[1:]:
    candidates, evaluated, truncated = generator.generate(tokenizer.tokenize(phrase))
    payload.append(
        {
            "phrase": phrase,
            "evaluated": evaluated,
            "truncated": truncated,
            "candidates": [candidate.to_dict() for candidate in candidates],
        }
    )
sys.stdout.write(json.dumps(payload, sort_keys=True))
"""


def _run_under_hash_seed(seed: str, phrases: Sequence[str]) -> str:
    """Generate ``phrases`` in a child interpreter with ``PYTHONHASHSEED=seed``."""
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = seed
    environment["PYTHONIOENCODING"] = "utf-8"
    package_root = str(Path(acronymkit.__file__).resolve().parent.parent)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        package_root if not existing else package_root + os.pathsep + existing
    )
    completed = subprocess.run(
        [sys.executable, "-c", _HASH_SEED_SCRIPT, *phrases],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=180,
    )
    return completed.stdout


def test_output_is_identical_across_hash_seeds() -> None:
    """No set-iteration-order leakage: the payload is byte-identical per seed."""
    phrases = [
        "Portable Document Format",
        "Rapid Analysis of Modern Systems Engineering Data Platform",
    ]
    outputs = [_run_under_hash_seed(seed, phrases) for seed in ("0", "1", "524287")]
    assert outputs[0] == outputs[1] == outputs[2]
    decoded = json.loads(outputs[0])
    assert [entry["phrase"] for entry in decoded] == phrases
    assert "PDF" in [candidate["acronym"] for candidate in decoded[0]["candidates"]]


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------
TWELVE_TOKEN_PHRASE = (
    "Portable Document Format Engine Rapid Lightweight Modular Kernel Vector Signal Adaptive Neural"
)
TWENTY_TOKEN_PHRASE = (
    TWELVE_TOKEN_PHRASE + " Beacon Quantum Fabric Storage Layer Optimal Transfer Gateway"
)


@pytest.mark.slow
def test_twelve_eligible_tokens_generate_in_well_under_100ms() -> None:
    config = Config()
    tokenizer, generator = pipeline(config)
    tokens = tokenizer.tokenize(TWELVE_TOKEN_PHRASE)
    assert len(eligible_tokens(tokens)) == 12
    generator.generate(tokens)  # warm the caches the first call would pay for
    timings = []
    for _ in range(3):
        started = time.perf_counter()
        generator.generate(tokens)
        timings.append(time.perf_counter() - started)
    assert min(timings) < 0.1


@pytest.mark.slow
def test_node_count_grows_gently_from_twelve_to_twenty_tokens() -> None:
    """Beam search is linear in tokens; an exponential blow-up would dwarf 4x.

    Both phrases are far too large to enumerate whole, so both run in beam mode
    and both report ``truncated=True``: a cut is exactly the event that can cost
    the caller the optimum, so it is signalled rather than swallowed.
    """
    config = Config()
    tokenizer, generator = pipeline(config)
    twelve = tokenizer.tokenize(TWELVE_TOKEN_PHRASE)
    twenty = tokenizer.tokenize(TWENTY_TOKEN_PHRASE)
    assert len(eligible_tokens(twelve)) == 12
    assert len(eligible_tokens(twenty)) == 20

    _, evaluated_12, truncated_12 = generator.generate(twelve)
    _, evaluated_20, truncated_20 = generator.generate(twenty)
    assert truncated_12 is True
    assert truncated_20 is True
    assert evaluated_12 > 0
    assert evaluated_20 <= 4 * evaluated_12


# ---------------------------------------------------------------------------
# Exhaustive search, beam admissibility and the truncation signal
# ---------------------------------------------------------------------------

#: Seven eligible tokens of two-plus letters: three branches each, so the whole
#: space is 3**7 and sits well inside the default ``max_search_nodes``. Its
#: optimum under DICTIONARY_BACKRONYM is a short dictionary word, not the long
#: full-coverage prefix a positional-only ranking key prefers.
BACKRONYM_PHRASE = "Modular Object Oriented Dynamic Learning Environment Platform"


def test_a_small_search_space_is_searched_exhaustively_and_yields_the_optimum() -> None:
    """The whole space fits ``max_search_nodes``, so the ranking must be exact.

    Regression: the frontier used to be cut to ``search_beam_width`` ranked by
    ``alpha * positional`` alone, which ignores both ``gamma * Lambda`` and
    ``delta * Psi``. Short dictionary prefixes were pruned at rounds 6-7 and the
    global optimum ``MOLE`` (28.6774, a dictionary word) never reached the final
    ranking; the engine returned ``MOOLEP`` (26.1497) and reported
    ``truncated=False``, so nothing signalled the loss.
    """
    config = Config(scoring_strategy=ScoringStrategy.DICTIONARY_BACKRONYM)
    tokens, candidates, evaluated, truncated = generate(config, BACKRONYM_PHRASE)
    assert len(eligible_tokens(tokens)) == 7

    best = exhaustive_best(config, tokens)
    assert best.is_dictionary_word is True
    assert candidates[0].acronym == best.acronym
    assert candidates[0].score == pytest.approx(best.score)
    assert best.acronym in [candidate.acronym for candidate in candidates]
    # Nothing was cut, so nothing is reported, and the budget was never in play.
    assert truncated is False
    assert evaluated <= config.max_search_nodes


@pytest.mark.parametrize("phrase", ["Portable Document Format", BUDGET_PHRASE])
@pytest.mark.parametrize("strategy", STRATEGIES)
def test_exhaustive_mode_agrees_with_a_brute_force_oracle(
    strategy: ScoringStrategy, phrase: str
) -> None:
    """Under every preset, a space that fits the budget returns its true optimum."""
    config = Config(scoring_strategy=strategy)
    tokens, candidates, _, truncated = generate(config, phrase)
    assert truncated is False
    best = exhaustive_best(config, tokens)
    assert candidates[0].acronym == best.acronym
    assert candidates[0].score == pytest.approx(best.score)


def test_the_beam_bound_keeps_a_live_dictionary_prefix_when_a_cut_is_forced() -> None:
    """With exhaustive mode off, the admissible key still reaches the optimum.

    ``max_search_nodes`` sits below the phrase's 3279-successor bound, so the
    beam engages; it also sits far above the ~220 successors a 16-wide beam
    actually enumerates, so no budget binds and the ranking key is the only
    thing under test. Under the old positional-only key ``MOLE`` was pruned at
    every beam width tried, including the shipped 250.
    """
    config = Config(
        scoring_strategy=ScoringStrategy.DICTIONARY_BACKRONYM,
        search_beam_width=16,
        max_search_nodes=3000,
    )
    tokens, candidates, evaluated, truncated = generate(config, BACKRONYM_PHRASE)
    assert evaluated < config.max_search_nodes, "no node budget may bind here"
    assert truncated is True, "a beam cut is reported"

    best = exhaustive_best(config, tokens)
    assert best.is_dictionary_word is True
    assert candidates[0].acronym == best.acronym
    assert candidates[0].score == pytest.approx(best.score)


def test_a_large_search_space_respects_the_budgets_and_reports_truncation() -> None:
    """Twenty tokens cannot be enumerated whole: the beam cuts, and says so."""
    config = Config()
    tokenizer, generator = pipeline(config)
    tokens = tokenizer.tokenize(TWENTY_TOKEN_PHRASE)
    assert len(eligible_tokens(tokens)) == 20

    candidates, evaluated, truncated = generator.generate(tokens)
    assert truncated is True
    assert evaluated <= config.max_search_nodes
    assert len(candidates) <= config.max_candidates
    assert plain_initialism(config, tokens) in [candidate.acronym for candidate in candidates]


def test_a_tight_node_budget_forces_beam_mode_on_a_space_that_would_have_fitted() -> None:
    """``max_search_nodes`` is the dial between exactness and latency."""
    phrase = BACKRONYM_PHRASE
    roomy = Config(scoring_strategy=ScoringStrategy.DICTIONARY_BACKRONYM)
    tight = roomy.with_overrides(max_search_nodes=200)
    assert generate(roomy, phrase)[3] is False
    assert generate(tight, phrase)[3] is True
    assert generate(tight, phrase)[2] <= 10 * tight.max_search_nodes


# ---------------------------------------------------------------------------
# The documented guarantees
# ---------------------------------------------------------------------------
INITIALISM_PHRASE = "Rapid Analysis Modern Systems Engineering Data Platform Vector Signal Adaptive"


def test_max_candidates_one_keeps_the_top_ranked_candidate() -> None:
    """The single slot belongs to rank, not to the safety net.

    ``_limit`` reserves the last slot for the plain initialism only from
    ``max_candidates >= 2``, because at one the swap could only ever replace the
    best candidate with something that scored strictly lower — which would turn
    ``AcronymResult.primary_acronym`` into the initialism for every
    latency-sensitive caller. The guarantee is documented with that bound (see
    :func:`test_the_initialism_guarantee_is_documented_with_its_bound`) rather
    than promised unconditionally and then broken.
    """
    config = Config()
    tokens, ranked, _, _ = generate(config, INITIALISM_PHRASE)
    initialism = plain_initialism(config, tokens)
    names = [candidate.acronym for candidate in ranked]
    assert initialism in names
    assert names[0] != initialism, "this phrase must out-rank the initialism to be a test"

    single = acronyms(Config(max_candidates=1), INITIALISM_PHRASE)
    assert single == [names[0]]
    # ... and it really is one slot away.
    assert initialism in acronyms(Config(max_candidates=2), INITIALISM_PHRASE)


def test_the_initialism_guarantee_is_documented_with_its_bound() -> None:
    """Module, method and ``_limit`` docstrings must all state the same rule.

    Regression: all three promised the initialism unconditionally while
    :meth:`ForwardGenerator._limit` skipped the reservation whenever
    ``max_candidates <= 1``, so the documented guarantee was false as written.
    """
    docs = {
        "module": generator_module.__doc__ or "",
        "generate": ForwardGenerator.generate.__doc__ or "",
        "_limit": ForwardGenerator._limit.__doc__ or "",
    }
    for name, text in docs.items():
        assert "max_candidates == 1" in text, f"{name} docstring omits the bound"
    for name in ("module", "generate"):
        assert "max_candidates >= 2" in docs[name], f"{name} docstring omits the guarantee"


def test_the_module_docstring_quotes_the_shipped_coefficients() -> None:
    """Every coefficient the prose argues from must match ``config.py``.

    Regression: the docstring justified its ranking behaviour with "a dictionary
    hit is worth ``gamma = 25`` while a dropped critical token costs only
    ``delta = 8``", which inverts the shipped relationship
    (``gamma=12.0 < delta=15.0``) and with it the conclusion that a real word
    omitting a token outranks the literal initialism.
    """
    doc = generator_module.__doc__ or ""
    balanced = STRATEGY_WEIGHTS[ScoringStrategy.BALANCED_PRONOUNCEABLE]
    backronym = STRATEGY_WEIGHTS[ScoringStrategy.DICTIONARY_BACKRONYM]

    assert "gamma = 25" not in doc
    assert "delta = 8" not in doc
    for name in ("alpha", "beta", "gamma", "delta", "length_penalty"):
        assert f"``{name}={getattr(balanced, name)}``" in doc
    assert f"``preferred_length={balanced.preferred_length}``" in doc
    for name in ("gamma", "delta", "length_penalty"):
        assert f"``{name}={getattr(backronym, name)}``" in doc
    assert f"``initial_weight = {balanced.initial_weight:g}``" in doc
    assert f"``contiguous_weight = {balanced.contiguous_weight:g}``" in doc

    # The two worked examples must balance with the shipped numbers.
    balanced_trade = (
        balanced.gamma + balanced.length_penalty - balanced.delta - balanced.initial_weight
    )
    backronym_trade = (
        backronym.gamma + backronym.length_penalty - backronym.delta - backronym.initial_weight
    )
    assert balanced_trade == -7.0
    assert backronym_trade == 31.0
    assert f"= {balanced_trade:+g}``" in doc
    assert f"= {backronym_trade:+g}``" in doc


def test_the_default_preset_ranks_the_initialism_above_a_token_dropping_word() -> None:
    """The corrected prose, checked against the engine rather than restated.

    ``gamma=12`` cannot pay for ``delta=15`` plus the forfeited
    ``initial_weight=10``, so under BALANCED_PRONOUNCEABLE the full-coverage
    acronym beats the dictionary word that drops a token — and the relationship
    flips under DICTIONARY_BACKRONYM, where ``gamma=60`` covers it easily.
    """
    balanced = Config()
    best_overall = generate(balanced, BACKRONYM_PHRASE)[1][0]
    best_word = generate(balanced.with_overrides(require_dictionary_word=True), BACKRONYM_PHRASE)[
        1
    ][0]
    assert best_overall.is_dictionary_word is False
    assert best_word.is_dictionary_word is True
    assert best_overall.score > best_word.score
    assert len(best_word.skipped_token_indices) > len(best_overall.skipped_token_indices)

    backronym = Config(scoring_strategy=ScoringStrategy.DICTIONARY_BACKRONYM)
    assert generate(backronym, BACKRONYM_PHRASE)[1][0].is_dictionary_word is True


# ---------------------------------------------------------------------------
# Property-based invariants
# ---------------------------------------------------------------------------
phrases = st.lists(st.sampled_from(WORD_POOL), min_size=1, max_size=6).map(" ".join)


@given(phrase=phrases)
@settings(max_examples=60, deadline=None)
def test_property_ordering_and_bounds_hold_for_any_phrase(phrase: str) -> None:
    config = Config()
    _, candidates, _, _ = generate(config, phrase)
    assert candidates
    keys = [order_key(candidate) for candidate in candidates]
    assert keys == sorted(keys)
    assert len(candidates) <= config.max_candidates
    for candidate in candidates:
        assert config.min_acronym_length <= len(candidate.acronym) <= config.max_acronym_length


@given(phrase=phrases)
@settings(max_examples=40, deadline=None)
def test_property_generation_is_deterministic(phrase: str) -> None:
    config = Config()
    first = generate(config, phrase)
    second = generate(config, phrase)
    assert [candidate.to_dict() for candidate in first[1]] == [
        candidate.to_dict() for candidate in second[1]
    ]


@given(phrase=phrases)
@settings(max_examples=40, deadline=None)
def test_property_mappings_describe_the_acronym_they_belong_to(phrase: str) -> None:
    config = Config()
    tokens, candidates, _, _ = generate(config, phrase)
    by_index = {token.index: token for token in tokens}
    for candidate in candidates:
        assert len(candidate.mappings) == len(candidate.acronym)
        for position, mapping in enumerate(candidate.mappings):
            assert mapping.position == position
            assert mapping.character == candidate.acronym[position]
            assert mapping.token_index is not None
            token = by_index[mapping.token_index]
            assert token.is_eligible
            assert mapping.char_offset is not None
            assert 0 <= mapping.char_offset < len(token.letters)
            assert token.letters[mapping.char_offset].upper() == mapping.character.upper()
        assert set(candidate.covered_token_indices) == {
            mapping.token_index for mapping in candidate.mappings
        }


@given(phrase=phrases)
@settings(max_examples=30, deadline=None)
def test_property_letter_mappings_round_trip_through_json(phrase: str) -> None:
    _, candidates, _, _ = generate(Config(), phrase)
    for candidate in candidates:
        payloads = json.loads(json.dumps([mapping.to_dict() for mapping in candidate.mappings]))
        restored = [LetterMapping.model_validate(payload) for payload in payloads]
        assert restored == candidate.mappings
