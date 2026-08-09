"""Tests for :class:`acronymkit.engine.AcronymEngine`, the public facade.

Three things are pinned here that nothing else can pin: the documented examples
in the README and the docstrings, the structural invariants of
:class:`~acronymkit.models.AcronymResult` (the primary is always
``alternatives[0]``), and the tier-resolution policy — including the
degradation paths, which are what a bare install actually exercises.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import acronymkit
from acronymkit import AcronymEngine, Config
from acronymkit.disambiguation import ExpansionDictionary
from acronymkit.enums import EngineTier, MappingKind
from acronymkit.exceptions import EmptyPhraseError, NoCandidateError, TierUnavailableError
from acronymkit.models import AcronymCandidate, AcronymResult
from conftest import CANONICAL_ACRONYMS, HAS_NLP_BACKEND

PHRASES = [phrase for phrase, _ in CANONICAL_ACRONYMS]

#: The degradation paths only exist when no Tier 1 runtime is importable; with
#: spaCy or NLTK installed the engine legitimately reaches Tier 1 instead.
requires_no_nlp = pytest.mark.skipif(
    HAS_NLP_BACKEND,
    reason="a Tier 1 NLP backend is installed, so nothing degrades",
)

#: The complementary gate, for the assertions that need a backend present.
requires_nlp_backend = pytest.mark.skipif(
    not HAS_NLP_BACKEND,
    reason="no Tier 1 NLP backend installed (pip install 'acronymkit[nlp]')",
)


def _stable(result: AcronymResult) -> dict:
    """Result payload with the wall-clock reading neutralised for comparison."""
    payload = result.to_dict()
    payload["metadata"]["execution_time_ms"] = 0.0
    return payload


# ---------------------------------------------------------------------------
# The documented public examples
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("Application Programming Interface", "API"),
        ("Portable Document Format", "PDF"),
    ],
    ids=["API", "PDF"],
)
def test_documented_quickstart_examples(phrase: str, expected: str) -> None:
    """The two examples in the README and every docstring must hold literally."""
    assert AcronymEngine().generate(phrase).primary_acronym == expected


@pytest.mark.parametrize(("phrase", "expected"), CANONICAL_ACRONYMS, ids=PHRASES)
def test_canonical_corpus_yields_its_textbook_initialism(
    engine: AcronymEngine, phrase: str, expected: str
) -> None:
    """Retuning the scoring presets must not regress a single canonical case."""
    assert engine.generate(phrase).primary_acronym == expected


def test_extract_definitions_on_the_nasa_sentence(engine: AcronymEngine) -> None:
    """The documented extraction example returns exactly one correct pair."""
    text = "The National Aeronautics and Space Administration (NASA) launched the mission."
    pairs = engine.extract_definitions(text)

    assert len(pairs) == 1
    pair = pairs[0]
    assert pair.short_form == "NASA"
    assert pair.long_form == "National Aeronautics and Space Administration"
    assert pair.pattern == "long(short)"
    # The spans are exact offsets into the original text.
    assert text[slice(*pair.short_form_span)] == pair.short_form
    assert text[slice(*pair.long_form_span)] == pair.long_form
    assert 0.0 <= pair.confidence <= 1.0


def test_extract_wraps_the_same_pairs_with_metadata(engine: AcronymEngine) -> None:
    """``extract`` is ``extract_definitions`` plus the observability envelope."""
    text = "The World Health Organization (WHO) issued guidance."
    result = engine.extract(text)

    assert result.source_text == text
    assert result.pairs == engine.extract_definitions(text)
    assert result.metadata.candidates_evaluated == len(result.pairs)
    assert result.as_mapping() == {"WHO": "World Health Organization"}


# ---------------------------------------------------------------------------
# AcronymResult invariants
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phrase", PHRASES, ids=PHRASES)
def test_primary_acronym_and_score_come_from_the_first_alternative(
    engine: AcronymEngine, phrase: str
) -> None:
    """``alternatives[0]`` is the primary, by construction."""
    result = engine.generate(phrase)

    assert result.alternatives, "generate must never return an empty ranked list"
    assert result.primary_acronym == result.alternatives[0].acronym
    assert result.score == result.alternatives[0].score
    assert result.source_phrase == phrase


@pytest.mark.parametrize("phrase", PHRASES, ids=PHRASES)
def test_primary_property_returns_the_matching_candidate(
    engine: AcronymEngine, phrase: str
) -> None:
    """``result.primary`` resolves back to the record behind ``primary_acronym``."""
    result = engine.generate(phrase)
    primary = result.primary

    assert isinstance(primary, AcronymCandidate)
    assert primary is result.alternatives[0]
    assert primary.acronym == result.primary_acronym
    assert primary.score == result.score
    assert primary.length == len(result.primary_acronym)


@pytest.mark.parametrize("phrase", PHRASES, ids=PHRASES)
def test_alternatives_are_ranked_best_first(engine: AcronymEngine, phrase: str) -> None:
    """The ranked list is sorted by descending score with a total tie-break."""
    alternatives = engine.generate(phrase).alternatives
    scores = [candidate.score for candidate in alternatives]
    assert scores == sorted(scores, reverse=True)
    keys = [
        (-candidate.score, len(candidate.acronym), candidate.acronym) for candidate in alternatives
    ]
    assert keys == sorted(keys)


@pytest.mark.parametrize("phrase", PHRASES, ids=PHRASES)
def test_alternatives_are_distinct(engine: AcronymEngine, phrase: str) -> None:
    """Candidates are de-duplicated by their cased acronym string."""
    acronyms = [candidate.acronym for candidate in engine.generate(phrase).alternatives]
    assert len(set(acronyms)) == len(acronyms)


@pytest.mark.parametrize("max_candidates", [1, 2, 3, 5, 10, 25], ids=repr)
def test_alternatives_never_exceed_max_candidates(max_candidates: int) -> None:
    """The ranked list is truncated to the configured budget."""
    engine = AcronymEngine(Config(max_candidates=max_candidates))
    for phrase in PHRASES:
        result = engine.generate(phrase)
        assert 1 <= len(result.alternatives) <= max_candidates
        assert result.primary_acronym == result.alternatives[0].acronym


def test_truncating_the_candidate_list_does_not_change_the_winner() -> None:
    """``max_candidates`` is a display budget, not a search constraint."""
    wide = AcronymEngine(Config(max_candidates=25))
    narrow = AcronymEngine(Config(max_candidates=1))
    for phrase in PHRASES:
        assert narrow.generate(phrase).primary_acronym == (wide.generate(phrase).primary_acronym)


@pytest.mark.parametrize("phrase", PHRASES, ids=PHRASES)
def test_candidate_records_are_internally_consistent(engine: AcronymEngine, phrase: str) -> None:
    """Every candidate's derived fields agree with its own mappings."""
    result = engine.generate(phrase)
    token_count = len(result.tokens)
    for candidate in result.alternatives:
        assert candidate.length == len(candidate.acronym)
        assert 0.0 <= candidate.pronounceability_score <= 1.0
        assert candidate.raw_phonotactic_score <= 0.0
        assert len(candidate.mappings) == len(candidate.acronym)
        assert [mapping.position for mapping in candidate.mappings] == list(
            range(len(candidate.acronym))
        )
        assert "".join(mapping.character for mapping in candidate.mappings) == (candidate.acronym)
        for index in candidate.covered_token_indices:
            assert 0 <= index < token_count
        assert not set(candidate.covered_token_indices) & set(candidate.skipped_token_indices)
        if candidate.breakdown is not None:
            assert candidate.breakdown.total == pytest.approx(candidate.score)


def test_breakdown_total_includes_the_length_penalty(engine: AcronymEngine) -> None:
    """``total`` is ``S(A, T)`` *minus* the length penalty, not the four terms alone.

    ``ScoreBreakdown`` records only the four terms of ``S(A, T)``, while
    ``Scorer.score`` also subtracts
    ``length_penalty * max(0, len(A) - preferred_length)``. For "PDF" under the
    default weights that is ``6.0 * (3 - 2) == 6.0``, so the recorded terms sit
    exactly ``6.0`` above ``total`` and ``ScoreBreakdown.explain()`` prints a
    sum that does not balance.
    """
    candidate = engine.score("PDF", "Portable Document Format")
    breakdown = candidate.breakdown
    assert breakdown is not None

    weights = engine.config.weights
    four_terms = (
        weights.alpha * breakdown.positional
        + weights.beta * breakdown.phonotactic
        + weights.gamma * breakdown.lexical
        - weights.delta * breakdown.information_loss
    )
    expected_penalty = weights.length_penalty * max(0, len("PDF") - weights.preferred_length)
    assert expected_penalty == pytest.approx(6.0)
    assert four_terms - expected_penalty == pytest.approx(breakdown.total)


def test_zeroing_the_length_penalty_recovers_the_published_objective() -> None:
    """With ``length_penalty=0`` the four recorded terms *are* the total."""
    from acronymkit.config import ScoringWeights

    weights = ScoringWeights(length_penalty=0.0)
    engine = AcronymEngine(Config(scoring_weights=weights))
    breakdown = engine.score("PDF", "Portable Document Format").breakdown
    assert breakdown is not None
    assert (
        weights.alpha * breakdown.positional
        + weights.beta * breakdown.phonotactic
        + weights.gamma * breakdown.lexical
        - weights.delta * breakdown.information_loss
    ) == pytest.approx(breakdown.total)


# ---------------------------------------------------------------------------
# EngineMetadata
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phrase", PHRASES, ids=PHRASES)
def test_metadata_is_populated(engine: AcronymEngine, phrase: str) -> None:
    """Every result carries a complete observability envelope."""
    result = engine.generate(phrase)
    metadata = result.metadata

    assert metadata.requested_tier is EngineTier.ZERO_DEPENDENCY
    assert metadata.engine_tier is EngineTier.ZERO_DEPENDENCY
    assert metadata.nlp_backend == engine.nlp_backend
    assert metadata.library_version == acronymkit.__version__
    assert metadata.execution_time_ms >= 0.0
    assert metadata.tokens_processed == len(result.tokens)
    assert metadata.candidates_evaluated >= len(result.alternatives)
    assert metadata.language is engine.config.language
    assert list(metadata.warnings) == list(engine.warnings)


def test_requested_tier_records_what_was_asked_for_not_what_ran() -> None:
    """``requested_tier`` and ``engine_tier`` are deliberately separate fields."""
    engine = AcronymEngine(Config(engine_tier=EngineTier.AUTO))
    metadata = engine.generate("Portable Document Format").metadata
    assert metadata.requested_tier is EngineTier.AUTO
    assert metadata.engine_tier is engine.engine_tier
    assert metadata.engine_tier is not EngineTier.AUTO


@requires_no_nlp
def test_zero_dependency_engine_uses_the_heuristic_backend(
    engine: AcronymEngine,
) -> None:
    """Tier 0 is the pure-stdlib path; its backend is named ``heuristic``."""
    assert engine.nlp_backend == "heuristic"
    assert engine.generate("Random Access Memory").metadata.nlp_backend == "heuristic"


@requires_nlp_backend
def test_a_tier_one_engine_reports_its_real_backend() -> None:
    """With a runtime installed, the metadata names it rather than 'heuristic'."""
    engine = AcronymEngine(Config(engine_tier=EngineTier.STATISTICAL_NLP))
    metadata = engine.generate("Portable Document Format").metadata
    assert metadata.nlp_backend in {"spacy", "nltk"}
    assert metadata.engine_tier is EngineTier.STATISTICAL_NLP
    assert metadata.requested_tier is EngineTier.STATISTICAL_NLP


@pytest.mark.parametrize("phrase", PHRASES[:6], ids=PHRASES[:6])
def test_tokens_processed_matches_the_returned_token_count(
    engine: AcronymEngine, phrase: str
) -> None:
    """``tokens_processed`` counts the tokens actually attached to the result."""
    result = engine.generate(phrase)
    assert result.metadata.tokens_processed == len(result.tokens)
    assert result.metadata.tokens_processed == len(engine.tokenize(phrase))
    assert result.metadata.tokens_processed > 0


def test_library_version_matches_the_package_attribute(engine: AcronymEngine) -> None:
    """The engine borrows ``acronymkit.__version__`` rather than re-deriving it."""
    version = engine.generate("Quality Assurance").metadata.library_version
    assert version == acronymkit.__version__
    assert version


def test_execution_time_is_non_negative_on_every_entry_point(
    engine: AcronymEngine,
) -> None:
    """Timing is monotonic-clock based, so it can never come out negative."""
    results = [
        engine.generate("Portable Document Format"),
        engine.extract("The World Health Organization (WHO) met."),
        engine.generate_backronym("Next Generation eXchange Utility System", "NEXUS"),
        engine.synthesize_backronym("RAM", vocabulary=["rapid", "agile", "modern"]),
        engine.disambiguate("BP", "Blood pressure (BP) was elevated."),
    ]
    for result in results:
        assert result.metadata.execution_time_ms >= 0.0


# ---------------------------------------------------------------------------
# Empty and degenerate input
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "phrase",
    ["", " ", "   ", "\t", "\n", "\t \n ", "the of and", "the", "a an the", "of, and!"],
    ids=repr,
)
def test_empty_phrase_error(engine: AcronymEngine, phrase: str) -> None:
    """Blank, whitespace-only and all-stop-word phrases are all ``EmptyPhraseError``."""
    with pytest.raises(EmptyPhraseError):
        engine.generate(phrase)


def test_empty_phrase_error_is_a_value_error(engine: AcronymEngine) -> None:
    """The exception is catchable both as a library error and as a ``ValueError``."""
    with pytest.raises(ValueError):
        engine.generate("")
    with pytest.raises(acronymkit.TokenizationError):
        engine.generate("")


def test_empty_phrase_message_distinguishes_the_two_causes(
    engine: AcronymEngine,
) -> None:
    """ "Nothing there" and "everything was filtered out" are different diagnoses."""
    with pytest.raises(EmptyPhraseError) as blank:
        engine.generate("   ")
    with pytest.raises(EmptyPhraseError) as filtered:
        engine.generate("the of and")
    assert "no tokens" in str(blank.value)
    assert "no acronym-eligible tokens" in str(filtered.value)


def test_stop_words_become_eligible_when_their_category_is_included() -> None:
    """The all-stop-word phrase is only empty because of the active filters."""
    permissive = AcronymEngine(
        Config(
            include_articles=True,
            include_prepositions=True,
            include_conjunctions=True,
            min_word_length=1,
        )
    )
    assert permissive.generate("the of and").primary_acronym


@pytest.mark.parametrize("text", ["", "   ", "no definitions in this sentence"], ids=repr)
def test_extraction_of_a_document_that_defines_nothing(engine: AcronymEngine, text: str) -> None:
    """Extraction returns an empty list rather than raising on barren input."""
    assert engine.extract_definitions(text) == []
    assert engine.extract(text).pairs == []


# ---------------------------------------------------------------------------
# Tier policy
# ---------------------------------------------------------------------------
@requires_no_nlp
def test_statistical_nlp_without_a_backend_raises() -> None:
    """Tier 1 promises Tier 1 fidelity and must not silently degrade."""
    with pytest.raises(TierUnavailableError) as excinfo:
        AcronymEngine(Config(engine_tier=EngineTier.STATISTICAL_NLP))
    assert excinfo.value.tier is EngineTier.STATISTICAL_NLP
    assert "spacy" in excinfo.value.missing
    assert "nltk" in excinfo.value.missing
    assert "acronymkit[nlp]" in str(excinfo.value)


def test_tier_unavailable_error_is_a_runtime_error() -> None:
    """The exception keeps its stdlib ancestry for integrators."""
    assert issubclass(TierUnavailableError, RuntimeError)
    assert issubclass(TierUnavailableError, acronymkit.AcronymKitError)


@requires_no_nlp
def test_hybrid_nlp_degrades_and_records_a_warning() -> None:
    """Hybrid is the "use it if you have it" tier: it degrades, loudly."""
    engine = AcronymEngine(Config(engine_tier=EngineTier.HYBRID_NLP))

    assert engine.engine_tier is EngineTier.ZERO_DEPENDENCY
    assert engine.nlp_backend == "heuristic"
    assert len(engine.warnings) == 1
    assert "degrading" in engine.warnings[0]
    assert "acronymkit[nlp]" in engine.warnings[0]

    result = engine.generate("Portable Document Format")
    assert result.primary_acronym == "PDF"
    assert result.metadata.requested_tier is EngineTier.HYBRID_NLP
    assert result.metadata.engine_tier is EngineTier.ZERO_DEPENDENCY
    assert list(result.metadata.warnings) == list(engine.warnings)


def test_neural_degrades_with_a_warning_naming_tier_2() -> None:
    """Tier 2 is a Phase 3 seam; selecting it today says so explicitly."""
    engine = AcronymEngine(Config(engine_tier=EngineTier.NEURAL))

    assert engine.engine_tier is not EngineTier.NEURAL
    assert engine.warnings
    assert any("Tier 2" in warning for warning in engine.warnings)

    result = engine.generate("Portable Document Format")
    assert result.primary_acronym == "PDF"
    assert result.metadata.requested_tier is EngineTier.NEURAL
    assert any("Tier 2" in warning for warning in result.metadata.warnings)


@requires_no_nlp
def test_neural_reports_both_degradation_steps() -> None:
    """Two independent degradations produce two independent warnings."""
    warnings = AcronymEngine(Config(engine_tier=EngineTier.NEURAL)).warnings
    assert len(warnings) == 2
    assert any("Tier 2" in warning for warning in warnings)
    assert any("No Tier 1 NLP backend" in warning for warning in warnings)


@pytest.mark.parametrize(
    "tier",
    [EngineTier.NEURAL, EngineTier.HYBRID_NLP, EngineTier.STATISTICAL_NLP],
    ids=lambda tier: tier.value,
)
def test_strict_turns_degradation_into_a_raise(tier: EngineTier) -> None:
    """``strict=True`` forbids receiving a lower tier than the one requested."""
    if tier is not EngineTier.NEURAL and HAS_NLP_BACKEND:
        pytest.skip("a Tier 1 backend is installed, so this tier is honoured")
    with pytest.raises(TierUnavailableError) as excinfo:
        AcronymEngine(Config(engine_tier=tier, strict=True))
    assert excinfo.value.tier is tier


@pytest.mark.parametrize(
    "tier",
    [EngineTier.NEURAL, EngineTier.HYBRID_NLP],
    ids=lambda tier: tier.value,
)
def test_the_same_tier_succeeds_without_strict(tier: EngineTier) -> None:
    """Strictness is the only thing separating a warning from an exception."""
    engine = AcronymEngine(Config(engine_tier=tier, strict=False))
    assert engine.generate("Portable Document Format").primary_acronym == "PDF"


@pytest.mark.parametrize("strict", [False, True], ids=["lenient", "strict"])
def test_zero_dependency_never_raises(strict: bool) -> None:
    """Tier 0 depends on nothing, so it is always available."""
    engine = AcronymEngine(Config(engine_tier=EngineTier.ZERO_DEPENDENCY, strict=strict))
    assert engine.engine_tier is EngineTier.ZERO_DEPENDENCY
    assert engine.warnings == ()


@pytest.mark.parametrize("strict", [False, True], ids=["lenient", "strict"])
def test_auto_never_raises_and_never_warns(strict: bool) -> None:
    """AUTO asks for the best available, so nothing it gets is a degradation."""
    engine = AcronymEngine(Config(engine_tier=EngineTier.AUTO, strict=strict))
    assert engine.warnings == ()
    assert engine.generate("Central Processing Unit").primary_acronym == "CPU"


# ---------------------------------------------------------------------------
# score()
# ---------------------------------------------------------------------------
def test_score_returns_a_scored_candidate_for_a_user_supplied_acronym(
    engine: AcronymEngine,
) -> None:
    """A caller's own acronym is aligned and scored exactly like a generated one."""
    candidate = engine.score("PDF", "Portable Document Format")

    assert isinstance(candidate, AcronymCandidate)
    assert candidate.acronym == "PDF"
    assert candidate.length == 3
    assert [mapping.kind for mapping in candidate.mappings] == [MappingKind.INITIAL] * 3
    assert candidate.covered_token_indices == [0, 1, 2]
    assert candidate.skipped_token_indices == []
    assert candidate.breakdown is not None
    assert candidate.breakdown.information_loss == 0.0
    assert candidate.breakdown.positional == pytest.approx(30.0)


def test_score_is_comparable_with_generated_candidates(engine: AcronymEngine) -> None:
    """The scores come from the same objective, so they can be compared directly."""
    phrase = "Portable Document Format"
    scored = engine.score("PDF", phrase)
    generated = engine.generate(phrase)
    assert scored.score == pytest.approx(generated.score)
    assert scored.acronym == generated.primary_acronym


@pytest.mark.parametrize("supplied", ["PDF", "pdf", "p.d.f.", "P-D-F", " pdf ", "Pdf"], ids=repr)
def test_score_normalises_case_and_punctuation(engine: AcronymEngine, supplied: str) -> None:
    """``"p.d.f."`` is scored as ``"PDF"``."""
    candidate = engine.score(supplied, "Portable Document Format")
    assert candidate.acronym == "PDF"


def test_score_penalises_a_worse_acronym(engine: AcronymEngine) -> None:
    """The objective must actually rank: the textbook form beats a mangled one."""
    phrase = "Portable Document Format"
    assert engine.score("PDF", phrase).score > engine.score("PD", phrase).score
    assert engine.score("PDF", phrase).score > engine.score("PXQ", phrase).score


def test_score_records_unmapped_characters(engine: AcronymEngine) -> None:
    """A letter no token can supply is reported rather than silently dropped."""
    candidate = engine.score("PDFZ", "Portable Document Format")
    kinds = [mapping.kind for mapping in candidate.mappings]
    assert MappingKind.UNMAPPED in kinds
    unmapped = [mapping for mapping in candidate.mappings if mapping.kind is MappingKind.UNMAPPED]
    assert all(mapping.token_index is None for mapping in unmapped)
    assert all(mapping.weight == 0.0 for mapping in unmapped)


def test_score_rejects_an_acronym_with_no_alphanumeric_characters(
    engine: AcronymEngine,
) -> None:
    """There is nothing to align, so this is a ``NoCandidateError``."""
    with pytest.raises(NoCandidateError):
        engine.score("...", "Portable Document Format")


@pytest.mark.parametrize("phrase", ["", "   "], ids=repr)
def test_score_rejects_an_empty_phrase(engine: AcronymEngine, phrase: str) -> None:
    """There is nothing to align *against*, so this is an ``EmptyPhraseError``."""
    with pytest.raises(EmptyPhraseError):
        engine.score("PDF", phrase)


# ---------------------------------------------------------------------------
# disambiguate()
# ---------------------------------------------------------------------------
def test_disambiguate_builds_a_dictionary_from_inline_definitions(
    engine: AcronymEngine,
) -> None:
    """With no dictionary supplied, the context's own definitions are used."""
    context = "Blood pressure (BP) was elevated at admission. The BP fell overnight."
    result = engine.disambiguate("BP", context)

    assert result.primary_expansion == "Blood pressure"
    assert result.acronym == "BP"
    assert result.context == context
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.expansion == "Blood pressure"
    assert candidate.score == pytest.approx(1.0)
    assert candidate.source == "inline"
    assert result.metadata.candidates_evaluated == len(result.candidates)


def test_disambiguate_with_no_definition_and_no_dictionary_proposes_nothing(
    engine: AcronymEngine,
) -> None:
    """``primary_expansion`` is ``None`` rather than a guess."""
    result = engine.disambiguate("XYZ", "A sentence that defines nothing at all.")
    assert result.primary_expansion is None
    assert result.candidates == []


def test_disambiguate_prefers_a_supplied_dictionary(engine: AcronymEngine) -> None:
    """An explicit dictionary replaces the inline-definition derivation."""
    dictionary = ExpansionDictionary({"BP": ["Blood Pressure", "British Petroleum", "Base Pair"]})
    result = engine.disambiguate(
        "BP", "The patient blood test showed the BP reading was high.", dictionary
    )

    assert result.primary_expansion == "Blood Pressure"
    assert {candidate.expansion for candidate in result.candidates} == {
        "Blood Pressure",
        "British Petroleum",
        "Base Pair",
    }
    scores = [candidate.score for candidate in result.candidates]
    assert scores == sorted(scores, reverse=True)


def test_disambiguate_is_deterministic(engine: AcronymEngine) -> None:
    """Two identical calls produce identical candidate orderings."""
    dictionary = ExpansionDictionary({"BP": ["Blood Pressure", "British Petroleum"]})
    context = "The refinery and the pressure gauge were both inspected."
    first = engine.disambiguate("BP", context, dictionary)
    second = engine.disambiguate("BP", context, dictionary)
    assert [(c.expansion, c.score) for c in first.candidates] == [
        (c.expansion, c.score) for c in second.candidates
    ]


# ---------------------------------------------------------------------------
# Determinism and thread safety
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phrase", PHRASES, ids=PHRASES)
def test_generate_is_deterministic(engine: AcronymEngine, phrase: str) -> None:
    """Repeated calls on one engine produce byte-identical payloads."""
    assert _stable(engine.generate(phrase)) == _stable(engine.generate(phrase))


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(index=st.integers(min_value=0, max_value=len(PHRASES) - 1))
def test_generate_is_deterministic_across_engine_instances(index: int) -> None:
    """Property: an engine holds no state that can alter a later answer."""
    phrase = PHRASES[index]
    first = AcronymEngine(Config()).generate(phrase)
    second = AcronymEngine(Config()).generate(phrase)
    assert _stable(first) == _stable(second)


def test_generate_is_thread_safe(engine: AcronymEngine) -> None:
    """Concurrent generation over the canonical corpus matches the sequential run."""
    sequential = [_stable(engine.generate(phrase)) for phrase in PHRASES]

    with ThreadPoolExecutor(max_workers=8) as pool:
        concurrent = list(pool.map(engine.generate, PHRASES))

    assert [_stable(result) for result in concurrent] == sequential
    assert [result.primary_acronym for result in concurrent] == [
        acronym for _, acronym in CANONICAL_ACRONYMS
    ]


def test_concurrent_first_use_of_the_lazy_resources_is_safe() -> None:
    """A cold engine hit by many threads at once still answers correctly.

    The lexicon and n-gram model are populated by unlocked double-checked
    assignment; this exercises the race the engine's docstring argues is benign.
    """
    cold = AcronymEngine(Config())
    phrases = PHRASES * 4

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(cold.generate, phrases))

    expected = [acronym for _, acronym in CANONICAL_ACRONYMS] * 4
    assert [result.primary_acronym for result in results] == expected


def test_mixed_concurrent_entry_points_are_safe(engine: AcronymEngine) -> None:
    """Generation, scoring, extraction and disambiguation may interleave freely."""

    def work(index: int) -> Optional[str]:
        phrase = PHRASES[index % len(PHRASES)]
        if index % 4 == 0:
            return engine.generate(phrase).primary_acronym
        if index % 4 == 1:
            return engine.score("ABC", phrase).acronym
        if index % 4 == 2:
            return str(len(engine.extract_definitions(f"{phrase} (XYZ) follows.")))
        return engine.disambiguate("XYZ", f"{phrase} (XYZ) follows.").primary_expansion

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(work, range(64)))

    assert len(outcomes) == 64
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert list(pool.map(work, range(64))) == outcomes


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------
def test_construction_is_lazy_about_the_expensive_resources() -> None:
    """Building an engine must not read the lexicon or the n-gram model."""
    engine = AcronymEngine(Config())
    assert engine._lexicon is None
    assert engine._ngram is None
    assert engine._scorer is None
    assert engine._generator is None

    engine.generate("Portable Document Format")
    assert engine._lexicon is not None
    assert engine._ngram is not None


def test_repeated_construction_is_safe_and_cheap() -> None:
    """Constructing many engines is neither slow nor order-dependent."""
    engines = [AcronymEngine(Config()) for _ in range(50)]
    assert len({id(engine) for engine in engines}) == 50
    for engine in (engines[0], engines[-1]):
        assert engine.generate("Portable Document Format").primary_acronym == "PDF"


def test_construction_does_not_touch_shared_state() -> None:
    """A second engine with a different config cannot disturb the first."""
    default = AcronymEngine(Config())
    lower = AcronymEngine(Config(case_style="lower"))
    assert default.generate("Portable Document Format").primary_acronym == "PDF"
    assert lower.generate("Portable Document Format").primary_acronym == "pdf"
    assert default.generate("Portable Document Format").primary_acronym == "PDF"


def test_engine_exposes_its_configuration() -> None:
    """``engine.config`` is the object it was built from, unmodified."""
    config = Config(max_candidates=7, include_articles=True)
    engine = AcronymEngine(config)
    assert engine.config is config


def test_engine_defaults_to_the_shipped_configuration() -> None:
    """``AcronymEngine()`` is ``AcronymEngine(Config())``."""
    assert AcronymEngine().config == Config()


def test_concurrent_construction_is_safe() -> None:
    """Engines may be built from several threads at once."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        engines = list(pool.map(lambda _: AcronymEngine(Config()), range(32)))
    assert len(engines) == 32
    assert all(engine.nlp_backend == engines[0].nlp_backend for engine in engines)


# ---------------------------------------------------------------------------
# tokenize()
# ---------------------------------------------------------------------------
def test_tokenize_returns_the_stream_the_result_carries(engine: AcronymEngine) -> None:
    """``result.tokens`` is exactly ``engine.tokenize(phrase)``."""
    phrase = "Self Contained Underwater Breathing Apparatus"
    assert engine.tokenize(phrase) == engine.generate(phrase).tokens


@pytest.mark.parametrize("text", ["", "   ", "\n\t"], ids=repr)
def test_tokenize_returns_an_empty_list_for_blank_input(engine: AcronymEngine, text: str) -> None:
    """Tokenising blank text is not an error; only generating from it is."""
    assert engine.tokenize(text) == []


@pytest.mark.parametrize("phrase", PHRASES, ids=PHRASES)
def test_token_offsets_index_back_into_the_original_text(
    engine: AcronymEngine, phrase: str
) -> None:
    """``phrase[token.start:token.end] == token.text`` for every token."""
    tokens = engine.tokenize(phrase)
    assert tokens
    for position, token in enumerate(tokens):
        assert token.index == position
        assert phrase[token.start : token.end] == token.text
        assert token.start < token.end
