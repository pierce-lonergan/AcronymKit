"""Unit tests for :mod:`acronymkit.scoring` — the mathematical core.

Every numeric expectation in this module is *derived* from the contract stated
in the build spec and in the ``acronymkit.scoring`` module docstring::

    S(A, T) = alpha * SUM_i omega(c_i, w_j(i))
            + beta  * Phi(A)
            + gamma * Lambda(A)
            - delta * Psi(T, A)
            - length_penalty * max(0, len(A) - preferred_length)

None of the numbers below were read off an observed run: the weight bundles are
pinned locally so that each expected total can be checked by hand from the
formula above.

The scorer duck-types both collaborators (it needs ``contains`` from the
lexicon and ``score``/``normalized_score`` from the n-gram model), so the tests
inject trivial stubs instead of loading resource files. That keeps the
arithmetic exact and the tests independent of resource retraining.
"""

from __future__ import annotations

from typing import Optional

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from acronymkit.config import Config, ScoringWeights
from acronymkit.enums import MappingKind, TokenRole
from acronymkit.models import LetterMapping, ScoreBreakdown, Token
from acronymkit.scoring import Scorer, build_mappings

# ---------------------------------------------------------------------------
# Fixtures of the "pin the arithmetic" kind
# ---------------------------------------------------------------------------
#: The reference 10/3/2 schedule with the documented default coefficients.
#: Declared explicitly rather than borrowed from ``Config()`` so that retuning
#: ``STRATEGY_WEIGHTS`` cannot silently invalidate the hand computations here;
#: ``tests/test_scoring_presets.py`` is where the *calibration* is pinned.
EXACT_WEIGHTS = ScoringWeights(
    alpha=1.0,
    beta=1.0,
    gamma=12.0,
    delta=15.0,
    initial_weight=10.0,
    internal_weight=3.0,
    contiguous_weight=2.0,
    unmapped_penalty=4.0,
    length_penalty=6.0,
    preferred_length=2,
)

#: A second bundle with alpha != 1 and beta != 1, so that a test can catch a
#: coefficient that is applied to the wrong term (or not applied at all).
SCALED_WEIGHTS = ScoringWeights(
    alpha=2.0,
    beta=0.5,
    gamma=3.0,
    delta=4.0,
    initial_weight=10.0,
    internal_weight=3.0,
    contiguous_weight=2.0,
    unmapped_penalty=4.0,
    length_penalty=1.5,
    preferred_length=3,
)

#: Fixed ``Phi(A)`` returned by :class:`StubNGram` in the hand-computed cases.
STUB_PHI = -2.5

#: Fixed ``normalized_score`` returned by :class:`StubNGram`.
STUB_PRONOUNCEABILITY = 0.9

TOL = 1e-9


class StubLexicon:
    """Exact-match membership oracle standing in for :class:`~acronymkit.lexicon.Lexicon`.

    Deliberately **not** case-insensitive: the real lexicon folds case itself,
    so an exact-match stub is what proves that :meth:`Scorer.lexical_term`
    case-folds before delegating.
    """

    def __init__(self, *words: str) -> None:
        self.words = frozenset(words)
        self.calls: list[str] = []

    def contains(self, word: str) -> bool:
        """Return whether ``word`` matches an entry byte-for-byte."""
        self.calls.append(word)
        return word in self.words


class StubNGram:
    """Constant-output stand-in for :class:`~acronymkit.phonetics.CharNGramModel`."""

    def __init__(self, phi: float = STUB_PHI, normalized: float = STUB_PRONOUNCEABILITY) -> None:
        self.phi = phi
        self.normalized = normalized

    def score(self, acronym: str) -> float:
        """Return the fixed ``Phi(A)``."""
        return self.phi

    def normalized_score(self, acronym: str) -> float:
        """Return the fixed pronounceability index."""
        return self.normalized


class ContentNGram:
    """Deterministic, content-dependent n-gram stub for the property tests."""

    def score(self, acronym: str) -> float:
        """Return a pure function of ``acronym`` in ``[-9.6, 0]``."""
        return -float(sum(ord(char) for char in acronym) % 97) / 10.0

    def normalized_score(self, acronym: str) -> float:
        """Return a pure function of ``acronym`` in ``[0, 1)``."""
        return float(sum(ord(char) for char in acronym) % 101) / 100.0


def make_token(
    index: int,
    text: str = "Word",
    *,
    is_critical: bool = True,
    is_eligible: bool = True,
    letters: Optional[str] = None,
    role: TokenRole = TokenRole.CONTENT,
) -> Token:
    """Build a minimal :class:`~acronymkit.models.Token` for scoring tests."""
    return Token(
        text=text,
        normalized=text.casefold(),
        index=index,
        start=0,
        end=len(text),
        role=role,
        is_critical=is_critical,
        is_eligible=is_eligible,
        letters=text.upper() if letters is None else letters,
    )


def make_tokens(count: int, **kwargs: object) -> list[Token]:
    """Build ``count`` tokens whose ``index`` matches their list position."""
    return [make_token(position, **kwargs) for position in range(count)]  # type: ignore[arg-type]


def exact_scorer(
    *,
    weights: ScoringWeights = EXACT_WEIGHTS,
    lexicon: Optional[StubLexicon] = None,
    ngram: Optional[StubNGram] = None,
    include_breakdown: bool = True,
) -> Scorer:
    """Build a scorer whose arithmetic is fully determined by ``weights``."""
    config = Config(scoring_weights=weights, include_breakdown=include_breakdown)
    return Scorer(config, lexicon, ngram)


# ---------------------------------------------------------------------------
# build_mappings: the classification truth table
# ---------------------------------------------------------------------------
INITIAL = MappingKind.INITIAL
INTERNAL = MappingKind.INTERNAL
CONTIGUOUS = MappingKind.CONTIGUOUS
UNMAPPED = MappingKind.UNMAPPED


@pytest.mark.parametrize(
    ("assignments", "expected"),
    [
        # -- UNMAPPED wins outright whenever there is no source token --------
        ([(0, None, None)], [UNMAPPED]),
        ([(0, None, 0)], [UNMAPPED]),
        ([(0, None, 3)], [UNMAPPED]),
        # -- INITIAL: char_offset == 0 ---------------------------------------
        ([(0, 0, 0)], [INITIAL]),
        ([(0, 1, 0)], [INITIAL]),
        # -- INTERNAL: mapped, non-zero offset, nothing to continue ----------
        ([(0, 0, 1)], [INTERNAL]),
        ([(0, 0, 7)], [INTERNAL]),
        # A mapped character with an unknown offset can be neither INITIAL nor
        # CONTIGUOUS, so it must fall through to INTERNAL.
        ([(0, 0, None)], [INTERNAL]),
        # -- CONTIGUOUS: same token, offset exactly previous + 1 -------------
        ([(0, 0, 0), (1, 0, 1)], [INITIAL, CONTIGUOUS]),
        ([(0, 0, 0), (1, 0, 1), (2, 0, 2)], [INITIAL, CONTIGUOUS, CONTIGUOUS]),
        ([(0, 0, 3), (1, 0, 4)], [INTERNAL, CONTIGUOUS]),
        # -- a different token_index breaks the run --------------------------
        ([(0, 0, 0), (1, 1, 1)], [INITIAL, INTERNAL]),
        ([(0, 0, 1), (1, 1, 2)], [INTERNAL, INTERNAL]),
        # -- the offset must advance by exactly one --------------------------
        ([(0, 0, 1), (1, 0, 1)], [INTERNAL, INTERNAL]),
        ([(0, 0, 1), (1, 0, 3)], [INTERNAL, INTERNAL]),
        ([(0, 0, 2), (1, 0, 1)], [INTERNAL, INTERNAL]),
        # -- an intervening UNMAPPED breaks the run --------------------------
        ([(0, 0, 0), (1, None, None), (2, 0, 1)], [INITIAL, UNMAPPED, INTERNAL]),
        # ... even when the unmapped character carried an offset of its own.
        ([(0, 0, 0), (1, None, 0), (2, 0, 1)], [INITIAL, UNMAPPED, INTERNAL]),
        # -- a broken run can restart ----------------------------------------
        (
            [(0, 0, 0), (1, 1, 0), (2, 1, 1), (3, 1, 2)],
            [INITIAL, INITIAL, CONTIGUOUS, CONTIGUOUS],
        ),
    ],
)
def test_build_mappings_classification_truth_table(
    assignments: list[tuple[int, Optional[int], Optional[int]]],
    expected: list[MappingKind],
) -> None:
    """Every branch of the documented precedence order is exercised."""
    acronym = "ABCD"[: len(assignments)]
    mappings = build_mappings(acronym, assignments, make_tokens(2), EXACT_WEIGHTS)
    assert [mapping.kind for mapping in mappings] == expected


def test_initial_outranks_contiguous_at_offset_zero() -> None:
    """``char_offset == 0`` is INITIAL even when the CONTIGUOUS test would pass.

    A preceding offset of ``-1`` is the only value for which ``0 ==
    previous + 1`` holds, so it is the only input that can distinguish the two
    branches. The contract puts INITIAL first, so the second character must be
    INITIAL and carry ``initial_weight``, not ``contiguous_weight``.
    """
    mappings = build_mappings("AB", [(0, 0, -1), (1, 0, 0)], make_tokens(1), EXACT_WEIGHTS)
    assert [mapping.kind for mapping in mappings] == [INTERNAL, INITIAL]
    assert mappings[1].weight == pytest.approx(EXACT_WEIGHTS.initial_weight)


def test_unmapped_outranks_initial() -> None:
    """``token_index is None`` is UNMAPPED even when ``char_offset == 0``."""
    mappings = build_mappings("A", [(0, None, 0)], make_tokens(1), EXACT_WEIGHTS)
    assert mappings[0].kind is UNMAPPED
    assert mappings[0].weight == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("kind", "assignment", "expected_weight"),
    [
        (INITIAL, (0, 0, 0), EXACT_WEIGHTS.initial_weight),
        (INTERNAL, (0, 0, 4), EXACT_WEIGHTS.internal_weight),
        (UNMAPPED, (0, None, None), 0.0),
    ],
)
def test_build_mappings_assigns_omega_from_the_weight_bundle(
    kind: MappingKind,
    assignment: tuple[int, Optional[int], Optional[int]],
    expected_weight: float,
) -> None:
    """``omega`` comes from ``ScoringWeights``, never from a literal."""
    mapping = build_mappings("A", [assignment], make_tokens(1), EXACT_WEIGHTS)[0]
    assert mapping.kind is kind
    assert mapping.weight == pytest.approx(expected_weight)


def test_build_mappings_assigns_contiguous_weight() -> None:
    """CONTIGUOUS needs two characters, so it gets its own case."""
    mappings = build_mappings("AB", [(0, 0, 0), (1, 0, 1)], make_tokens(1), EXACT_WEIGHTS)
    assert mappings[1].kind is CONTIGUOUS
    assert mappings[1].weight == pytest.approx(EXACT_WEIGHTS.contiguous_weight)


def test_build_mappings_preserves_order_and_characters() -> None:
    """Each mapping records the acronym character at its declared position."""
    acronym = "XYZ"
    assignments = [(2, 0, 0), (0, 1, 1), (1, None, None)]
    mappings = build_mappings(acronym, assignments, make_tokens(2), EXACT_WEIGHTS)
    assert [mapping.position for mapping in mappings] == [2, 0, 1]
    assert [mapping.character for mapping in mappings] == ["Z", "X", "Y"]
    assert [mapping.token_index for mapping in mappings] == [0, 1, None]
    assert [mapping.char_offset for mapping in mappings] == [0, 1, None]


def test_build_mappings_accepts_an_empty_assignment_list() -> None:
    """No assignments means no mappings, not an error."""
    assert build_mappings("", [], make_tokens(1), EXACT_WEIGHTS) == []


@pytest.mark.parametrize("position", [-1, 3, 99])
def test_build_mappings_rejects_out_of_range_position(position: int) -> None:
    """A position outside the acronym is a programming error, not a soft miss."""
    with pytest.raises(ValueError, match="position"):
        build_mappings("ABC", [(position, 0, 0)], make_tokens(2), EXACT_WEIGHTS)


@pytest.mark.parametrize("token_index", [-1, 2, 50])
def test_build_mappings_rejects_out_of_range_token_index(token_index: int) -> None:
    """A token_index outside the token sequence is likewise rejected."""
    with pytest.raises(ValueError, match="token_index"):
        build_mappings("ABC", [(0, token_index, 0)], make_tokens(2), EXACT_WEIGHTS)


def test_build_mappings_allows_none_token_index_with_no_tokens() -> None:
    """The bounds check only applies to mapped characters."""
    mappings = build_mappings("A", [(0, None, None)], [], EXACT_WEIGHTS)
    assert mappings[0].kind is UNMAPPED


# ---------------------------------------------------------------------------
# positional_term
# ---------------------------------------------------------------------------
def test_positional_term_is_hand_computed() -> None:
    """``10 + 2 + 3 + 0 + 0`` less ``2 * unmapped_penalty(4)`` is ``7``."""
    assignments = [
        (0, 0, 0),  # INITIAL     -> +10
        (1, 0, 1),  # CONTIGUOUS  -> +2
        (2, 1, 3),  # INTERNAL    -> +3
        (3, None, None),  # UNMAPPED -> +0, -4
        (4, None, None),  # UNMAPPED -> +0, -4
    ]
    mappings = build_mappings("ABCDE", assignments, make_tokens(2), EXACT_WEIGHTS)
    assert [mapping.kind for mapping in mappings] == [
        INITIAL,
        CONTIGUOUS,
        INTERNAL,
        UNMAPPED,
        UNMAPPED,
    ]
    assert exact_scorer().positional_term(mappings) == pytest.approx(7.0, abs=TOL)


def test_positional_term_of_nothing_is_zero() -> None:
    """An empty alignment contributes nothing."""
    assert exact_scorer().positional_term([]) == pytest.approx(0.0)


@pytest.mark.parametrize("penalty", [0.0, 1.0, 4.0, 12.5])
def test_positional_term_subtracts_exactly_one_penalty_per_unmapped(
    penalty: float,
) -> None:
    """The penalty scales linearly with the number of UNMAPPED characters."""
    weights = EXACT_WEIGHTS.model_copy(update={"unmapped_penalty": penalty})
    scorer = exact_scorer(weights=weights)
    assignments = [(0, 0, 0), (1, None, None), (2, 1, 0), (3, None, None)]
    mappings = build_mappings("ABCD", assignments, make_tokens(2), weights)
    expected = 10.0 + 0.0 + 10.0 + 0.0 - 2 * penalty
    assert scorer.positional_term(mappings) == pytest.approx(expected, abs=TOL)


# ---------------------------------------------------------------------------
# phonotactic / lexical / information-loss terms in isolation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("acronym", ["", "A", "PDF", "SCUBA"])
def test_phonotactic_term_is_zero_without_a_model(acronym: str) -> None:
    """``ngram=None`` degrades ``Phi(A)`` to a flat ``0.0``."""
    assert exact_scorer().phonotactic_term(acronym) == 0.0


def test_phonotactic_term_delegates_verbatim_to_the_model() -> None:
    """``Phi(A)`` is whatever the model says; the scorer adds no arithmetic."""
    scorer = exact_scorer(ngram=StubNGram(phi=-4.25))
    assert scorer.phonotactic_term("HTML") == pytest.approx(-4.25, abs=TOL)


@pytest.mark.parametrize("acronym", ["", "RAM", "SOAP"])
def test_lexical_term_is_zero_without_a_lexicon(acronym: str) -> None:
    """``lexicon=None`` degrades ``Lambda(A)`` to a flat ``0.0``."""
    assert exact_scorer().lexical_term(acronym) == 0.0


@pytest.mark.parametrize("acronym", ["ram", "RAM", "RaM", "rAm"])
def test_lexical_term_is_case_insensitive(acronym: str) -> None:
    """The scorer case-folds before consulting the (exact-match) lexicon."""
    lexicon = StubLexicon("ram")
    assert exact_scorer(lexicon=lexicon).lexical_term(acronym) == 1.0
    assert lexicon.calls == [acronym.casefold()]


@pytest.mark.parametrize("acronym", ["rom", "ROM", "ramp", ""])
def test_lexical_term_is_zero_on_a_miss(acronym: str) -> None:
    """``Lambda(A)`` is a strict indicator: no partial credit."""
    assert exact_scorer(lexicon=StubLexicon("ram")).lexical_term(acronym) == 0.0


def test_information_loss_counts_only_uncovered_critical_tokens() -> None:
    """``Psi`` counts ``is_critical`` tokens whose ``index`` is not covered.

    The token ``index`` field — not the list position — is what ``covered``
    refers to, so the tokens here carry deliberately non-consecutive indices.
    """
    tokens = [
        make_token(5, is_critical=True),
        make_token(7, is_critical=False),
        make_token(9, is_critical=True),
        make_token(11, is_critical=True),
    ]
    scorer = exact_scorer()
    assert scorer.information_loss(tokens, set()) == pytest.approx(3.0)
    assert scorer.information_loss(tokens, {5}) == pytest.approx(2.0)
    assert scorer.information_loss(tokens, {5, 9}) == pytest.approx(1.0)
    assert scorer.information_loss(tokens, {5, 9, 11}) == pytest.approx(0.0)
    # Covering a non-critical token buys nothing...
    assert scorer.information_loss(tokens, {7}) == pytest.approx(3.0)
    # ... and neither does covering an index no token claims.
    assert scorer.information_loss(tokens, {5, 9, 11, 404}) == pytest.approx(0.0)


def test_information_loss_of_no_tokens_is_zero() -> None:
    """Nothing critical means nothing to lose."""
    assert exact_scorer().information_loss([], set()) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# score(): full hand-computed assemblies
# ---------------------------------------------------------------------------
def test_score_hand_computed_perfect_initialism() -> None:
    """``RAM`` over three fully covered critical tokens.

    positional = 10 + 10 + 10               = 30
    phonotactic = Phi(A)                    = -2.5
    lexical = Lambda(A)                     = 1.0
    information_loss = Psi(T, A)            = 0
    excess = max(0, len("RAM") - 2)         = 1

    total = 1*30 + 1*(-2.5) + 12*1 - 15*0 - 6*1 = 33.5
    """
    scorer = exact_scorer(lexicon=StubLexicon("ram", "soap"), ngram=StubNGram())
    tokens = make_tokens(3)
    mappings = build_mappings("RAM", [(0, 0, 0), (1, 1, 0), (2, 2, 0)], tokens, EXACT_WEIGHTS)
    breakdown = scorer.score("RAM", tokens, mappings, {0, 1, 2})

    assert breakdown.positional == pytest.approx(30.0, abs=TOL)
    assert breakdown.phonotactic == pytest.approx(-2.5, abs=TOL)
    assert breakdown.lexical == pytest.approx(1.0, abs=TOL)
    assert breakdown.information_loss == pytest.approx(0.0, abs=TOL)
    assert breakdown.total == pytest.approx(33.5, abs=TOL)


def test_score_hand_computed_with_information_loss() -> None:
    """``SCUX``: a mixed alignment that drops two critical tokens.

    positional = 10 + 2 + 3 + 0 - 4 (one unmapped) = 11
    phonotactic = Phi(A)                           = -2.5
    lexical = Lambda(A)                            = 0.0   ("scux" is unknown)
    information_loss = Psi(T, A)                   = 2     (tokens 2 and 3)
    excess = max(0, len("SCUX") - 2)               = 2

    total = 1*11 + 1*(-2.5) + 12*0 - 15*2 - 6*2 = -33.5
    """
    scorer = exact_scorer(lexicon=StubLexicon("ram", "soap"), ngram=StubNGram())
    tokens = make_tokens(4)
    assignments = [
        (0, 0, 0),  # INITIAL    -> +10
        (1, 0, 1),  # CONTIGUOUS -> +2
        (2, 1, 2),  # INTERNAL   -> +3
        (3, None, None),  # UNMAPPED -> +0, -4
    ]
    mappings = build_mappings("SCUX", assignments, tokens, EXACT_WEIGHTS)
    breakdown = scorer.score("SCUX", tokens, mappings, {0, 1})

    assert breakdown.positional == pytest.approx(11.0, abs=TOL)
    assert breakdown.phonotactic == pytest.approx(-2.5, abs=TOL)
    assert breakdown.lexical == pytest.approx(0.0, abs=TOL)
    assert breakdown.information_loss == pytest.approx(2.0, abs=TOL)
    assert breakdown.total == pytest.approx(-33.5, abs=TOL)


def test_score_hand_computed_with_non_unit_coefficients() -> None:
    """``SOAP`` under ``SCALED_WEIGHTS``: alpha=2, beta=0.5, gamma=3, delta=4.

    positional = 4 * 10                        = 40
    excess = max(0, len("SOAP") - 3)           = 1

    total = 2*40 + 0.5*(-2.5) + 3*1 - 4*0 - 1.5*1 = 80.25
    """
    scorer = exact_scorer(
        weights=SCALED_WEIGHTS,
        lexicon=StubLexicon("ram", "soap"),
        ngram=StubNGram(),
    )
    tokens = make_tokens(4)
    assignments = [(0, 0, 0), (1, 1, 0), (2, 2, 0), (3, 3, 0)]
    mappings = build_mappings("SOAP", assignments, tokens, SCALED_WEIGHTS)
    breakdown = scorer.score("SOAP", tokens, mappings, {0, 1, 2, 3})

    assert breakdown.positional == pytest.approx(40.0, abs=TOL)
    assert breakdown.total == pytest.approx(80.25, abs=TOL)
    assert (breakdown.alpha, breakdown.beta) == (2.0, 0.5)
    assert (breakdown.gamma, breakdown.delta) == (3.0, 4.0)


def test_score_applies_no_length_penalty_at_or_below_preferred_length() -> None:
    """``max(0, len(A) - preferred_length)`` is zero for a two-character acronym.

    total = 1*20 + 1*(-2.5) + 12*0 - 15*0 - 6*0 = 17.5
    """
    scorer = exact_scorer(lexicon=StubLexicon("ram"), ngram=StubNGram())
    tokens = make_tokens(2)
    mappings = build_mappings("QA", [(0, 0, 0), (1, 1, 0)], tokens, EXACT_WEIGHTS)
    assert scorer.score("QA", tokens, mappings, {0, 1}).total == pytest.approx(17.5, abs=TOL)


@pytest.mark.parametrize(("length", "expected_excess"), [(1, 0), (2, 0), (3, 1), (4, 2), (6, 4)])
def test_length_penalty_grows_linearly_past_the_preferred_length(
    length: int, expected_excess: int
) -> None:
    """Each character beyond ``preferred_length`` costs exactly one penalty."""
    scorer = exact_scorer()
    acronym = "A" * length
    tokens = make_tokens(1, is_critical=False)
    breakdown = scorer.score(acronym, tokens, [], set())
    expected = -EXACT_WEIGHTS.length_penalty * expected_excess
    assert breakdown.total == pytest.approx(expected, abs=TOL)


def test_score_records_the_coefficients_in_force() -> None:
    """The breakdown is self-describing: it carries its own alpha/beta/gamma/delta."""
    breakdown = exact_scorer().score("AB", make_tokens(1, is_critical=False), [], set())
    assert breakdown.alpha == EXACT_WEIGHTS.alpha
    assert breakdown.beta == EXACT_WEIGHTS.beta
    assert breakdown.gamma == EXACT_WEIGHTS.gamma
    assert breakdown.delta == EXACT_WEIGHTS.delta


# ---------------------------------------------------------------------------
# ScoreBreakdown.explain()
# ---------------------------------------------------------------------------
def test_explain_shows_every_coefficient_and_the_total() -> None:
    """``explain()`` is a full arithmetic trace, not a summary."""
    scorer = exact_scorer(lexicon=StubLexicon("ram"), ngram=StubNGram())
    tokens = make_tokens(4)
    assignments = [(0, 0, 0), (1, 0, 1), (2, 1, 2), (3, None, None)]
    mappings = build_mappings("SCUX", assignments, tokens, EXACT_WEIGHTS)
    text = scorer.score("SCUX", tokens, mappings, {0, 1}).explain()

    assert text.startswith("S = ")
    assert "1*11.000" in text  # alpha * positional
    assert "1*-2.500" in text  # beta  * phonotactic
    assert "12*0.000" in text  # gamma * lexical
    assert "15*2.000" in text  # delta * information_loss
    assert text.endswith("= -33.500")


def test_explain_is_pure() -> None:
    """Calling ``explain()`` twice yields the identical string."""
    breakdown = ScoreBreakdown(
        positional=11.0,
        phonotactic=-2.5,
        lexical=0.0,
        information_loss=2.0,
        alpha=1.0,
        beta=1.0,
        gamma=12.0,
        delta=15.0,
        total=-33.5,
    )
    assert breakdown.explain() == breakdown.explain()


# ---------------------------------------------------------------------------
# build_candidate
# ---------------------------------------------------------------------------
def test_build_candidate_populates_every_field() -> None:
    """A candidate is a complete record: no field is left at its default."""
    scorer = exact_scorer(lexicon=StubLexicon("ram", "soap"), ngram=StubNGram())
    tokens = make_tokens(3)
    mappings = build_mappings("RAM", [(0, 0, 0), (1, 1, 0), (2, 2, 0)], tokens, EXACT_WEIGHTS)
    candidate = scorer.build_candidate("RAM", tokens, mappings, {0, 1, 2})

    assert candidate.acronym == "RAM"
    assert candidate.length == 3
    assert candidate.score == pytest.approx(33.5, abs=TOL)
    assert candidate.is_dictionary_word is True
    assert candidate.pronounceability_score == pytest.approx(STUB_PRONOUNCEABILITY)
    assert candidate.raw_phonotactic_score == pytest.approx(STUB_PHI, abs=TOL)
    assert candidate.mappings == list(mappings)
    assert candidate.covered_token_indices == [0, 1, 2]
    assert candidate.skipped_token_indices == []
    assert candidate.breakdown is not None
    assert candidate.score == pytest.approx(candidate.breakdown.total, abs=TOL)
    assert candidate.raw_phonotactic_score == pytest.approx(
        candidate.breakdown.phonotactic, abs=TOL
    )


def test_build_candidate_sorts_index_collections() -> None:
    """``covered``/``skipped`` are sorted, so the payload is set-order independent."""
    scorer = exact_scorer()
    tokens = [
        make_token(2, is_eligible=True),
        make_token(11, is_eligible=True),
        make_token(7, is_eligible=True),
        make_token(4, is_eligible=False),
        make_token(9, is_eligible=True),
    ]
    mappings = build_mappings("AB", [(0, 0, 0), (1, 2, 0)], tokens, EXACT_WEIGHTS)
    candidate = scorer.build_candidate("AB", tokens, mappings, {11, 2, 7})

    assert candidate.covered_token_indices == [2, 7, 11]
    assert candidate.covered_token_indices == sorted(candidate.covered_token_indices)
    # Eligible-but-uncovered only: index 4 is ineligible and never "skipped".
    assert candidate.skipped_token_indices == [9]
    assert candidate.skipped_token_indices == sorted(candidate.skipped_token_indices)


def test_build_candidate_skipped_equals_eligible_minus_covered() -> None:
    """The invariant, stated directly, over a mixed-eligibility token set."""
    scorer = exact_scorer()
    tokens = [
        make_token(0, is_eligible=True),
        make_token(1, is_eligible=False),
        make_token(2, is_eligible=True),
        make_token(3, is_eligible=True),
        make_token(4, is_eligible=False),
    ]
    covered = {0, 4}
    candidate = scorer.build_candidate("A", tokens, [], covered)
    eligible = {token.index for token in tokens if token.is_eligible}
    assert candidate.skipped_token_indices == sorted(eligible - covered)


@pytest.mark.parametrize("include_breakdown", [True, False])
def test_build_candidate_attaches_breakdown_iff_configured(
    include_breakdown: bool,
) -> None:
    """``breakdown`` is present exactly when ``config.include_breakdown`` is set."""
    scorer = exact_scorer(include_breakdown=include_breakdown)
    tokens = make_tokens(1)
    mappings = build_mappings("A", [(0, 0, 0)], tokens, EXACT_WEIGHTS)
    candidate = scorer.build_candidate("A", tokens, mappings, {0})
    assert (candidate.breakdown is not None) is include_breakdown
    # The score itself is unaffected by whether the trace is retained.
    assert candidate.score == pytest.approx(10.0, abs=TOL)


def test_build_candidate_falls_back_to_neutral_pronounceability() -> None:
    """Without an n-gram model the reported pronounceability is the neutral 0.5."""
    scorer = exact_scorer()
    tokens = make_tokens(2)
    mappings = build_mappings("AB", [(0, 0, 0), (1, 1, 0)], tokens, EXACT_WEIGHTS)
    candidate = scorer.build_candidate("AB", tokens, mappings, {0, 1})
    assert candidate.pronounceability_score == pytest.approx(0.5)
    assert candidate.raw_phonotactic_score == pytest.approx(0.0)


def test_build_candidate_is_dictionary_word_tracks_lambda() -> None:
    """``is_dictionary_word`` is exactly ``Lambda(A) >= 1``."""
    scorer = exact_scorer(lexicon=StubLexicon("soap"))
    tokens = make_tokens(4)
    hit = scorer.build_candidate("SOAP", tokens, [], set())
    miss = scorer.build_candidate("SOAX", tokens, [], set())
    assert hit.is_dictionary_word is True
    assert miss.is_dictionary_word is False


def test_build_candidate_serialises_to_json() -> None:
    """A candidate renders to a JSON-compatible payload with enums as strings."""
    scorer = exact_scorer(lexicon=StubLexicon("ram"), ngram=StubNGram())
    tokens = make_tokens(3)
    mappings = build_mappings("RAM", [(0, 0, 0), (1, 1, 0), (2, 2, 0)], tokens, EXACT_WEIGHTS)
    candidate = scorer.build_candidate("RAM", tokens, mappings, {0, 1, 2})
    payload = candidate.to_dict()
    assert payload["acronym"] == "RAM"
    assert payload["length"] == 3
    assert [mapping["kind"] for mapping in payload["mappings"]] == [
        "initial",
        "initial",
        "initial",
    ]


# ---------------------------------------------------------------------------
# Determinism and statelessness
# ---------------------------------------------------------------------------
_ACRONYM_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@st.composite
def alignments(draw: st.DrawFn) -> tuple[str, int, list[tuple[int, Optional[int], Optional[int]]]]:
    """Draw an ``(acronym, token_count, assignments)`` triple that is always legal."""
    acronym = draw(st.text(alphabet=_ACRONYM_ALPHABET, min_size=1, max_size=8))
    token_count = draw(st.integers(min_value=1, max_value=5))
    assignments: list[tuple[int, Optional[int], Optional[int]]] = []
    for position in range(len(acronym)):
        token_index = draw(
            st.one_of(st.none(), st.integers(min_value=0, max_value=token_count - 1))
        )
        char_offset = None if token_index is None else draw(st.integers(min_value=0, max_value=4))
        assignments.append((position, token_index, char_offset))
    return acronym, token_count, assignments


@given(alignments())
@settings(max_examples=150, deadline=None)
def test_scoring_the_same_inputs_twice_is_identical(
    alignment: tuple[str, int, list[tuple[int, Optional[int], Optional[int]]]],
) -> None:
    """Property: the whole pipeline is a pure function of its inputs."""
    acronym, token_count, assignments = alignment
    tokens = make_tokens(token_count)
    scorer = Scorer(
        Config(scoring_weights=EXACT_WEIGHTS),
        StubLexicon("ram", "soap", "abc"),
        ContentNGram(),
    )
    covered = {token_index for _, token_index, _ in assignments if token_index is not None}

    first = build_mappings(acronym, assignments, tokens, scorer.weights)
    second = build_mappings(acronym, assignments, tokens, scorer.weights)
    assert first == second

    assert scorer.score(acronym, tokens, first, covered) == scorer.score(
        acronym, tokens, second, covered
    )
    assert scorer.build_candidate(acronym, tokens, first, covered) == scorer.build_candidate(
        acronym, tokens, second, covered
    )


@given(alignments())
@settings(max_examples=150, deadline=None)
def test_mapping_invariants_hold_for_every_alignment(
    alignment: tuple[str, int, list[tuple[int, Optional[int], Optional[int]]]],
) -> None:
    """Property: kinds, weights and characters agree with the contract."""
    acronym, token_count, assignments = alignment
    tokens = make_tokens(token_count)
    mappings = build_mappings(acronym, assignments, tokens, EXACT_WEIGHTS)
    expected_weight = {
        INITIAL: EXACT_WEIGHTS.initial_weight,
        INTERNAL: EXACT_WEIGHTS.internal_weight,
        CONTIGUOUS: EXACT_WEIGHTS.contiguous_weight,
        UNMAPPED: 0.0,
    }

    assert len(mappings) == len(assignments)
    for mapping, (position, token_index, char_offset) in zip(mappings, assignments):
        assert mapping.position == position
        assert mapping.character == acronym[position]
        assert mapping.token_index == token_index
        assert mapping.char_offset == char_offset
        assert mapping.weight == pytest.approx(expected_weight[mapping.kind])
        if token_index is None:
            assert mapping.kind is UNMAPPED
        elif char_offset == 0:
            assert mapping.kind is INITIAL
        else:
            assert mapping.kind in (INTERNAL, CONTIGUOUS)


@given(alignments())
@settings(max_examples=150, deadline=None)
def test_positional_term_matches_its_definition(
    alignment: tuple[str, int, list[tuple[int, Optional[int], Optional[int]]]],
) -> None:
    """Property: ``sum(omega) - unmapped_penalty * |UNMAPPED|``, always."""
    acronym, token_count, assignments = alignment
    tokens = make_tokens(token_count)
    mappings = build_mappings(acronym, assignments, tokens, EXACT_WEIGHTS)
    unmapped = sum(1 for mapping in mappings if mapping.kind is UNMAPPED)
    expected = (
        sum(mapping.weight for mapping in mappings) - EXACT_WEIGHTS.unmapped_penalty * unmapped
    )
    scorer = exact_scorer()
    assert scorer.positional_term(mappings) == pytest.approx(expected, abs=TOL)


def test_scorer_holds_no_mutable_state() -> None:
    """Two evaluations in either order give the same answers on one instance."""
    scorer = exact_scorer(lexicon=StubLexicon("ram", "soap"), ngram=StubNGram())
    tokens_a = make_tokens(3)
    mappings_a = build_mappings("RAM", [(0, 0, 0), (1, 1, 0), (2, 2, 0)], tokens_a, EXACT_WEIGHTS)
    tokens_b = make_tokens(4)
    mappings_b = build_mappings(
        "SCUX",
        [(0, 0, 0), (1, 0, 1), (2, 1, 2), (3, None, None)],
        tokens_b,
        EXACT_WEIGHTS,
    )

    forward_a = scorer.build_candidate("RAM", tokens_a, mappings_a, {0, 1, 2})
    forward_b = scorer.build_candidate("SCUX", tokens_b, mappings_b, {0, 1})

    reverse = exact_scorer(lexicon=StubLexicon("ram", "soap"), ngram=StubNGram())
    reverse_b = reverse.build_candidate("SCUX", tokens_b, mappings_b, {0, 1})
    reverse_a = reverse.build_candidate("RAM", tokens_a, mappings_a, {0, 1, 2})

    assert forward_a == reverse_a
    assert forward_b == reverse_b
    # And a third pass on the already-used instance still agrees.
    assert scorer.build_candidate("RAM", tokens_a, mappings_a, {0, 1, 2}) == forward_a


def test_scorer_exposes_its_collaborators_without_an_instance_dict() -> None:
    """``__slots__`` means there is nowhere to stash per-call state."""
    lexicon = StubLexicon("ram")
    ngram = StubNGram()
    config = Config(scoring_weights=EXACT_WEIGHTS)
    scorer = Scorer(config, lexicon, ngram)

    assert scorer.config is config
    assert scorer.lexicon is lexicon
    assert scorer.ngram is ngram
    assert scorer.weights == EXACT_WEIGHTS
    assert not hasattr(scorer, "__dict__")


def test_scorer_weights_follow_the_config() -> None:
    """``Scorer.weights`` is exactly ``Config.weights``, override included."""
    plain = Scorer(Config())
    assert plain.weights == Config().weights
    overridden = Scorer(Config(scoring_weights=SCALED_WEIGHTS))
    assert overridden.weights == SCALED_WEIGHTS


def test_mappings_are_frozen_records() -> None:
    """``LetterMapping`` is immutable, so a scored candidate cannot drift."""
    mapping = build_mappings("A", [(0, 0, 0)], make_tokens(1), EXACT_WEIGHTS)[0]
    assert isinstance(mapping, LetterMapping)
    with pytest.raises(ValueError, match="frozen"):
        mapping.weight = 99.0  # type: ignore[misc]
