"""Tests for :mod:`acronymkit.disambiguation`.

Two objects are under test. :class:`~acronymkit.disambiguation.ExpansionDictionary`
is a normalising, order-preserving index -- what is pinned here is its key
canonicalisation, its de-duplication rule, and the fact that ``merge`` is purely
functional. :class:`~acronymkit.disambiguation.LexicalDisambiguator` is a
ranking function -- what is pinned here is the *winner* and the structural
invariants (ordering, score bounds, evidence provenance, determinism), never an
incidental score, except where the blend is small enough to compute by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from acronymkit.config import Config
from acronymkit.disambiguation import ExpansionDictionary, LexicalDisambiguator
from acronymkit.enums import EngineTier, Language
from acronymkit.exceptions import LexiconError, ResourceNotFoundError, TierUnavailableError
from acronymkit.extractor import AbbreviationExtractor
from acronymkit.models import DisambiguationResult, EngineMetadata
from acronymkit.tokenizer import Tokenizer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

#: The three-way "MS" ambiguity used throughout the ranking tests.
MS_EXPANSIONS = ["multiple sclerosis", "Microsoft", "mass spectrometry"]


@pytest.fixture(scope="module")
def config() -> Config:
    """A stock Tier 0 configuration."""
    return Config()


@pytest.fixture(scope="module")
def ms_dictionary() -> ExpansionDictionary:
    """An index holding the three competing expansions of ``MS``."""
    return ExpansionDictionary({"MS": MS_EXPANSIONS})


@pytest.fixture(scope="module")
def ms_disambiguator(config: Config, ms_dictionary: ExpansionDictionary) -> LexicalDisambiguator:
    """A disambiguator over the ``MS`` index."""
    return LexicalDisambiguator(config, ms_dictionary)


def context_word_keys(config: Config, context: str) -> set[str]:
    """Return the normalised word bag of ``context`` using the public tokenizer."""
    tokenizer = Tokenizer(config)
    return {
        "".join(char for char in token.normalized if char.isalnum())
        for token in tokenizer.tokenize(context)
    }


# ===========================================================================
# ExpansionDictionary
# ===========================================================================


@pytest.mark.parametrize(
    "lookup",
    ["MS", "ms", "Ms", "M.S.", "m.s.", "M S", " m s ", "M-S", "(MS)"],
)
def test_keys_are_normalised_across_case_and_punctuation(lookup: str) -> None:
    """Every spelling of the same abbreviation addresses one bucket."""
    index = ExpansionDictionary({"MS": ["multiple sclerosis"]})
    assert lookup in index
    assert index.candidates(lookup) == ("multiple sclerosis",)


def test_distinct_spellings_collapse_into_a_single_entry() -> None:
    """Adding under several spellings grows the bucket, not the key set."""
    index = ExpansionDictionary()
    index.add("MS", "multiple sclerosis")
    index.add("m.s.", "Microsoft")
    index.add(" ms ", "mass spectrometry")
    assert len(index) == 1
    assert list(index) == ["MS"]
    assert index.candidates("MS") == tuple(MS_EXPANSIONS)


def test_membership_rejects_non_strings() -> None:
    """``__contains__`` answers ``False`` rather than raising on a bad key."""
    index = ExpansionDictionary({"MS": ["multiple sclerosis"]})
    assert 42 not in index
    assert None not in index
    assert ("MS",) not in index


def test_length_counts_short_forms_not_expansions() -> None:
    """``len`` is the number of distinct short forms."""
    index = ExpansionDictionary({"MS": MS_EXPANSIONS, "BP": ["blood pressure"]})
    assert len(index) == 2
    assert len(ExpansionDictionary()) == 0


@pytest.mark.parametrize(
    ("duplicates", "expected"),
    [
        (["blood pressure", "blood pressure"], ("blood pressure",)),
        (["blood pressure", "Blood Pressure"], ("blood pressure",)),
        (["blood pressure", "blood  pressure"], ("blood pressure",)),
        (["Blood Pressure", "blood pressure"], ("Blood Pressure",)),
        (
            ["blood pressure", "boiling point", "blood pressure"],
            ("blood pressure", "boiling point"),
        ),
    ],
)
def test_values_are_deduplicated_first_surface_form_wins(
    duplicates: list[str], expected: tuple[str, ...]
) -> None:
    """De-duplication is case- and whitespace-insensitive; the first form is kept."""
    index = ExpansionDictionary({"BP": duplicates})
    assert index.candidates("BP") == expected


def test_values_preserve_insertion_order() -> None:
    """Insertion order is the reported order -- it is itself weak evidence."""
    index = ExpansionDictionary()
    for expansion in ("gamma", "alpha", "beta"):
        index.add("X", expansion)
    assert index.candidates("X") == ("gamma", "alpha", "beta")


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_short_forms_and_expansions_are_ignored(blank: str) -> None:
    """Nothing addressable and nothing meaningful is ever stored."""
    index = ExpansionDictionary()
    index.add(blank, "blood pressure")
    index.add("BP", blank)
    index.add("...", "blood pressure")
    assert len(index) == 0


def test_a_bare_string_value_is_accepted_as_one_expansion() -> None:
    """``{"BP": "blood pressure"}`` is shorthand for a one-element list."""
    index = ExpansionDictionary({"BP": "blood pressure"})
    assert index.candidates("BP") == ("blood pressure",)


def test_unknown_short_form_yields_an_empty_tuple() -> None:
    """Querying an unindexed abbreviation is not an error."""
    assert ExpansionDictionary({"BP": ["blood pressure"]}).candidates("ZZZ") == ()


@pytest.mark.parametrize("value", [5, 5.0, None, [1, 2], ("a", 3), {"a": "b"}])
def test_malformed_values_raise_lexicon_error(value: object) -> None:
    """A value that is neither a string nor a sequence of strings is rejected."""
    with pytest.raises(LexiconError):
        ExpansionDictionary({"BP": value})  # type: ignore[dict-item]


# -- from_pairs -------------------------------------------------------------


def test_from_pairs_builds_the_index_from_extractor_output(config: Config) -> None:
    """A document teaches the disambiguator its own local vocabulary."""
    text = (
        "The World Health Organization (WHO) briefed the United Nations (UN). "
        "The central nervous system (CNS) was discussed."
    )
    pairs = AbbreviationExtractor(config).extract(text)
    index = ExpansionDictionary.from_pairs(pairs)
    assert len(index) == 3
    assert list(index) == ["WHO", "UN", "CNS"]
    assert index.candidates("who") == ("World Health Organization",)
    assert index.candidates("CNS") == ("central nervous system",)


def test_from_pairs_preserves_document_order_per_short_form(config: Config) -> None:
    """Two definitions of one abbreviation stack in the order they appeared."""
    text = "The mass spectrometry (MS) run finished. Later, multiple sclerosis (MS) was diagnosed."
    pairs = AbbreviationExtractor(config).extract(text)
    index = ExpansionDictionary.from_pairs(pairs)
    assert index.candidates("MS") == ("mass spectrometry", "multiple sclerosis")


def test_from_pairs_of_nothing_is_empty() -> None:
    """An empty extraction produces an empty index rather than raising."""
    assert len(ExpansionDictionary.from_pairs([])) == 0


# -- from_json --------------------------------------------------------------


def test_from_json_round_trip(tmp_path: Path) -> None:
    """``to_dict`` -> JSON -> ``from_json`` reproduces the index exactly."""
    original = ExpansionDictionary({"MS": MS_EXPANSIONS, "b.p.": ["blood pressure"]})
    path = tmp_path / "expansions.json"
    path.write_text(json.dumps(original.to_dict()), encoding="utf-8")
    loaded = ExpansionDictionary.from_json(path)
    assert loaded.to_dict() == original.to_dict()
    assert loaded.items() == original.items()


def test_from_json_accepts_bare_string_values(tmp_path: Path) -> None:
    """A scalar value is read as a one-element expansion list."""
    path = tmp_path / "expansions.json"
    path.write_text(json.dumps({"BP": "blood pressure"}), encoding="utf-8")
    assert ExpansionDictionary.from_json(path).candidates("BP") == ("blood pressure",)


@pytest.mark.parametrize(
    "payload",
    ["{not json", "", "{'single': 'quotes'}", '{"BP": ["blood pressure",]}'],
)
def test_from_json_rejects_malformed_json(tmp_path: Path, payload: str) -> None:
    """Unparseable JSON raises ``LexiconError``, not a bare ``ValueError``."""
    path = tmp_path / "broken.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(LexiconError):
        ExpansionDictionary.from_json(path)


@pytest.mark.parametrize("payload", ["[1, 2, 3]", '"a string"', "42", "null"])
def test_from_json_rejects_non_object_documents(tmp_path: Path, payload: str) -> None:
    """The document must be an object mapping short forms to expansions."""
    path = tmp_path / "wrong-shape.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(LexiconError):
        ExpansionDictionary.from_json(path)


def test_from_json_rejects_non_string_expansions(tmp_path: Path) -> None:
    """A numeric expansion is a malformed dictionary."""
    path = tmp_path / "bad-values.json"
    path.write_text(json.dumps({"BP": [1, 2]}), encoding="utf-8")
    with pytest.raises(LexiconError):
        ExpansionDictionary.from_json(path)


def test_from_json_missing_file_raises_resource_not_found(tmp_path: Path) -> None:
    """A path that cannot be read is a resource problem, not a parse problem."""
    with pytest.raises(ResourceNotFoundError):
        ExpansionDictionary.from_json(tmp_path / "does-not-exist.json")


# -- merge ------------------------------------------------------------------


def test_merge_returns_a_new_object_and_mutates_neither_operand() -> None:
    """``merge`` is purely functional."""
    left = ExpansionDictionary({"MS": ["multiple sclerosis"], "BP": ["blood pressure"]})
    right = ExpansionDictionary({"MS": ["Microsoft"], "CNS": ["central nervous system"]})
    left_before = left.to_dict()
    right_before = right.to_dict()

    merged = left.merge(right)

    assert merged is not left
    assert merged is not right
    assert left.to_dict() == left_before
    assert right.to_dict() == right_before
    assert merged.candidates("MS") == ("multiple sclerosis", "Microsoft")
    assert merged.candidates("BP") == ("blood pressure",)
    assert merged.candidates("CNS") == ("central nervous system",)
    assert len(merged) == 3


def test_merge_puts_self_first_and_drops_duplicates() -> None:
    """The receiver's expansions lead; overlapping ones are not repeated."""
    left = ExpansionDictionary({"X": ["one", "two"]})
    right = ExpansionDictionary({"X": ["TWO", "three"]})
    assert left.merge(right).candidates("X") == ("one", "two", "three")
    assert right.merge(left).candidates("X") == ("TWO", "three", "one")


def test_merge_with_an_empty_index_is_a_copy() -> None:
    """Merging nothing in changes nothing but the identity."""
    original = ExpansionDictionary({"MS": MS_EXPANSIONS})
    merged = original.merge(ExpansionDictionary())
    assert merged is not original
    assert merged.to_dict() == original.to_dict()


@pytest.mark.parametrize("other", [{"MS": ["multiple sclerosis"]}, None, "MS", 7])
def test_merge_rejects_foreign_operands(other: object) -> None:
    """``merge`` insists on another :class:`ExpansionDictionary`."""
    with pytest.raises(TypeError):
        ExpansionDictionary().merge(other)  # type: ignore[arg-type]


# ===========================================================================
# LexicalDisambiguator -- the MS cases
# ===========================================================================

MS_CASES = [
    pytest.param(
        "The patient was diagnosed with MS after brain lesions appeared on the "
        "neurological scan; relapsing symptoms and demyelination were noted.",
        "multiple sclerosis",
        id="medical-clinical-notes",
    ),
    pytest.param(
        "MRI revealed multiple demyelinating lesions, and the neurologist "
        "confirmed the MS diagnosis in this patient.",
        "multiple sclerosis",
        id="medical-radiology",
    ),
    pytest.param(
        "Patients with MS often present with optic neuritis, fatigue and "
        "progressive neurological disability.",
        "multiple sclerosis",
        id="medical-symptoms",
    ),
    pytest.param(
        "The MS Windows operating system ships with Office; Microsoft licences "
        "the software to enterprise customers.",
        "Microsoft",
        id="software-licensing",
    ),
    pytest.param(
        "Install the MS Office suite on every Windows workstation before the software rollout.",
        "Microsoft",
        id="software-deployment",
    ),
    pytest.param(
        "The MS analysis used a quadrupole spectrometer to measure the mass to "
        "charge ratio of ionised peptides.",
        "mass spectrometry",
        id="spectrometry-instrument",
    ),
    pytest.param(
        "Tandem MS quantified peptide ions by their mass to charge ratio in the spectrometer.",
        "mass spectrometry",
        id="spectrometry-tandem",
    ),
]


@pytest.mark.parametrize(("context", "winner"), MS_CASES)
def test_context_selects_the_right_expansion(
    ms_disambiguator: LexicalDisambiguator, context: str, winner: str
) -> None:
    """The domain of the surrounding text decides which expansion wins."""
    result = ms_disambiguator.disambiguate("MS", context)
    assert result.primary_expansion == winner
    assert result.candidates[0].expansion == winner
    assert result.candidates[0].source == "dictionary"


@pytest.mark.parametrize(("context", "winner"), MS_CASES)
def test_every_registered_expansion_is_scored(
    ms_disambiguator: LexicalDisambiguator, context: str, winner: str
) -> None:
    """Ranking never silently drops a candidate."""
    result = ms_disambiguator.disambiguate("MS", context)
    assert {candidate.expansion for candidate in result.candidates} == set(MS_EXPANSIONS)
    assert result.metadata.candidates_evaluated == len(MS_EXPANSIONS)


@pytest.mark.parametrize("lookup", ["MS", "ms", "M.S.", "m.s."])
def test_the_acronym_may_be_spelled_any_way(
    ms_disambiguator: LexicalDisambiguator, lookup: str
) -> None:
    """Lookup normalisation applies to the query as well as to the index."""
    context = "The patient had brain lesions and relapsing neurological symptoms."
    result = ms_disambiguator.disambiguate(lookup, context)
    assert result.primary_expansion == "multiple sclerosis"
    assert result.acronym == lookup  # echoed verbatim


# ===========================================================================
# LexicalDisambiguator -- the inline path
# ===========================================================================


def test_inline_definition_resolves_without_any_dictionary(config: Config) -> None:
    """A document that defines its own abbreviation needs no external index."""
    disambiguator = LexicalDisambiguator(config)
    assert len(disambiguator.dictionary) == 0

    result = disambiguator.disambiguate("BP", "Blood pressure (BP) was elevated.")

    assert result.primary_expansion == "Blood pressure"
    assert len(result.candidates) == 1
    assert result.candidates[0].source == "inline"
    assert result.candidates[0].score == 1.0


@pytest.mark.parametrize(
    ("acronym", "context", "expansion"),
    [
        ("BP", "Blood pressure (BP) was elevated.", "Blood pressure"),
        (
            "CNS",
            "The central nervous system (CNS) was imaged.",
            "central nervous system",
        ),
        (
            "MRI",
            "MRI (magnetic resonance imaging) confirmed the finding.",
            "magnetic resonance imaging",
        ),
        (
            "who",
            "The World Health Organization (WHO) responded.",
            "World Health Organization",
        ),
    ],
)
def test_inline_definitions_score_exactly_one(
    config: Config, acronym: str, context: str, expansion: str
) -> None:
    """``1.0`` is reserved for the document's own definition."""
    result = LexicalDisambiguator(config).disambiguate(acronym, context)
    assert result.primary_expansion == expansion
    assert result.candidates[0].score == 1.0
    assert result.candidates[0].source == "inline"


def test_inline_beats_dictionary(config: Config) -> None:
    """No dictionary entry can tie with an inline definition."""
    index = ExpansionDictionary({"BP": ["British Petroleum", "boiling point"]})
    result = LexicalDisambiguator(config, index).disambiguate(
        "BP", "Blood pressure (BP) was elevated in the patient."
    )

    assert result.primary_expansion == "Blood pressure"
    assert result.candidates[0].source == "inline"
    assert [candidate.source for candidate in result.candidates[1:]] == [
        "dictionary",
        "dictionary",
    ]
    assert all(candidate.score < 1.0 for candidate in result.candidates[1:])
    assert {candidate.expansion for candidate in result.candidates} == {
        "Blood pressure",
        "British Petroleum",
        "boiling point",
    }


def test_inline_definition_is_not_duplicated_by_the_dictionary(config: Config) -> None:
    """An expansion present both inline and in the index appears once, as inline."""
    index = ExpansionDictionary({"BP": ["blood pressure"]})
    result = LexicalDisambiguator(config, index).disambiguate(
        "BP", "Blood pressure (BP) was elevated."
    )
    assert len(result.candidates) == 1
    assert result.candidates[0].source == "inline"
    assert result.candidates[0].score == 1.0


def test_a_definition_of_another_acronym_is_ignored(config: Config) -> None:
    """Only a parenthetical defining *this* acronym counts as inline evidence."""
    result = LexicalDisambiguator(config).disambiguate(
        "BP", "The central nervous system (CNS) was imaged."
    )
    assert result.primary_expansion is None
    assert result.candidates == []


# ===========================================================================
# LexicalDisambiguator -- degenerate input
# ===========================================================================


@pytest.mark.parametrize("context", ["", "   ", "\n\t", "no definition here at all"])
def test_empty_dictionary_and_no_definition_resolve_to_nothing(
    config: Config, context: str
) -> None:
    """No candidates, no primary, no exception -- and still valid metadata."""
    result = LexicalDisambiguator(config).disambiguate("XYZ", context)

    assert isinstance(result, DisambiguationResult)
    assert result.primary_expansion is None
    assert result.candidates == []
    assert result.acronym == "XYZ"
    assert result.context == context

    metadata = result.metadata
    assert isinstance(metadata, EngineMetadata)
    assert metadata.execution_time_ms >= 0.0
    assert metadata.candidates_evaluated == 0
    assert metadata.tokens_processed >= 0
    assert metadata.engine_tier is EngineTier.ZERO_DEPENDENCY
    assert metadata.language is Language.EN
    assert metadata.warnings == []


@pytest.mark.parametrize("acronym", ["", "   ", "...", "!!", "---"])
def test_an_acronym_with_no_alphanumerics_yields_no_candidates(
    config: Config, acronym: str
) -> None:
    """A short form that normalises to nothing addresses no bucket."""
    index = ExpansionDictionary({"MS": MS_EXPANSIONS})
    result = LexicalDisambiguator(config, index).disambiguate(
        acronym, "Microsoft ships software to customers."
    )
    assert result.primary_expansion is None
    assert result.candidates == []


def test_scoring_works_with_no_context_at_all(config: Config) -> None:
    """An empty context still ranks the dictionary, on initials and register alone."""
    index = ExpansionDictionary({"MS": MS_EXPANSIONS})
    result = LexicalDisambiguator(config, index).disambiguate("MS", "")
    assert len(result.candidates) == 3
    assert result.primary_expansion is not None
    assert all(candidate.evidence == [] for candidate in result.candidates)
    assert result.metadata.tokens_processed == 0


# ===========================================================================
# LexicalDisambiguator -- ranking invariants
# ===========================================================================

RANKING_CONTEXTS = [
    "",
    "The patient had brain lesions and relapsing neurological symptoms.",
    "Microsoft ships the Windows operating system to enterprise customers.",
    "The spectrometer measured the mass to charge ratio of the peptide ions.",
    "Blood pressure (BP) was elevated, and MS was also noted.",
    "An entirely unrelated sentence about gardening and weather.",
]


@pytest.mark.parametrize("context", RANKING_CONTEXTS)
def test_candidates_are_sorted_by_descending_score_then_alphabetically(
    ms_disambiguator: LexicalDisambiguator, context: str
) -> None:
    """The total ordering makes ties stable and reproducible."""
    candidates = ms_disambiguator.disambiguate("MS", context).candidates
    keys = [(-candidate.score, candidate.expansion) for candidate in candidates]
    assert keys == sorted(keys)


@pytest.mark.parametrize("context", RANKING_CONTEXTS)
def test_all_scores_lie_in_the_unit_interval(
    ms_disambiguator: LexicalDisambiguator, context: str
) -> None:
    """Every term of the blend is bounded, so the blend is too."""
    for candidate in ms_disambiguator.disambiguate("MS", context).candidates:
        assert 0.0 <= candidate.score <= 1.0


@pytest.mark.parametrize("context", RANKING_CONTEXTS)
def test_the_primary_is_the_top_ranked_candidate(
    ms_disambiguator: LexicalDisambiguator, context: str
) -> None:
    """``primary_expansion`` is exactly ``candidates[0].expansion``."""
    result = ms_disambiguator.disambiguate("MS", context)
    if result.candidates:
        assert result.primary_expansion == result.candidates[0].expansion
    else:
        assert result.primary_expansion is None


def test_ties_break_alphabetically() -> None:
    """Two expansions with an identical score sort by expansion string."""
    index = ExpansionDictionary({"ZZ": ["mu mu", "alpha alpha", "nu nu"]})
    candidates = LexicalDisambiguator(Config(), index).disambiguate("ZZ", "").candidates
    scores = {candidate.expansion: candidate.score for candidate in candidates}
    assert scores["alpha alpha"] == scores["mu mu"] == scores["nu nu"]
    assert [candidate.expansion for candidate in candidates] == [
        "alpha alpha",
        "mu mu",
        "nu nu",
    ]


@pytest.mark.parametrize(
    ("acronym", "expansion", "score"),
    [
        # No context, so overlap == 0. "multiple sclerosis" is a perfect
        # initialism (derivability 1.0) and its lower case matches a context
        # with no proper nouns (register 1.0):
        #     0.55 * 0 + 0.30 * 1.0 + 0.15 * 1.0 == 0.45
        ("MS", "multiple sclerosis", 0.45),
        ("MS", "mass spectrometry", 0.45),
        # "Microsoft" gives 'M' on the initial (10) and 's' internally (3),
        # normalised by a perfect initialism (2 * 10): 13 / 20 == 0.65. It is
        # capitalised, so register is 0 against a context with no proper nouns:
        #     0.55 * 0 + 0.30 * 0.65 + 0.15 * 0 == 0.195
        ("MS", "Microsoft", 0.195),
        # Nothing derivable at all: only the register term survives.
        #     0.55 * 0 + 0.30 * 0 + 0.15 * 1.0 == 0.15
        ("MS", "alpha alpha", 0.15),
    ],
)
def test_hand_computed_scores_with_no_context(
    config: Config, acronym: str, expansion: str, score: float
) -> None:
    """With an empty context the blend collapses to two terms and is exact."""
    index = ExpansionDictionary({acronym: [expansion]})
    result = LexicalDisambiguator(config, index).disambiguate(acronym, "")
    assert result.candidates[0].score == pytest.approx(score)


# ===========================================================================
# LexicalDisambiguator -- evidence
# ===========================================================================


@pytest.mark.parametrize(("context", "winner"), MS_CASES)
def test_evidence_terms_occur_in_the_context(
    ms_disambiguator: LexicalDisambiguator, config: Config, context: str, winner: str
) -> None:
    """Every reported evidence term is a word the context actually contains.

    An expansion the context says nothing about is entitled to no evidence at
    all, but the winning expansion must be able to point at something.
    """
    available = context_word_keys(config, context)
    result = ms_disambiguator.disambiguate("MS", context)
    for candidate in result.candidates:
        assert set(candidate.evidence) <= available
    assert result.candidates[0].expansion == winner
    assert result.candidates[0].evidence


def test_inline_evidence_comes_from_the_definition(config: Config) -> None:
    """Inline evidence is the long form's own content words."""
    context = "Blood pressure (BP) was elevated in the patient."
    result = LexicalDisambiguator(config).disambiguate("BP", context)
    assert result.candidates[0].evidence == ["blood", "pressure"]
    assert set(result.candidates[0].evidence) <= context_word_keys(config, context)


@pytest.mark.parametrize("context", RANKING_CONTEXTS)
def test_evidence_is_sorted_deduplicated_and_capped(
    ms_disambiguator: LexicalDisambiguator, context: str
) -> None:
    """Evidence lists are byte-stable: sorted, unique and bounded."""
    for candidate in ms_disambiguator.disambiguate("MS", context).candidates:
        assert candidate.evidence == sorted(candidate.evidence)
        assert len(candidate.evidence) == len(set(candidate.evidence))
        assert len(candidate.evidence) <= 8


def test_the_acronym_itself_is_never_its_own_evidence(config: Config) -> None:
    """The occurrence being resolved is not evidence for anything."""
    index = ExpansionDictionary({"MS": MS_EXPANSIONS})
    context = "MS MS MS multiple sclerosis MS MS"
    for candidate in LexicalDisambiguator(config, index).disambiguate("MS", context).candidates:
        assert "ms" not in candidate.evidence


# ===========================================================================
# LexicalDisambiguator -- determinism and tier handling
# ===========================================================================


@pytest.mark.parametrize("context", RANKING_CONTEXTS)
def test_repeated_calls_return_identical_results(
    ms_disambiguator: LexicalDisambiguator, context: str
) -> None:
    """Nothing in the ranking depends on iteration order or the clock."""
    payloads = [
        ms_disambiguator.disambiguate("MS", context).model_dump(exclude={"metadata"})
        for _ in range(4)
    ]
    assert payloads[1:] == payloads[:-1]


def test_two_disambiguators_over_the_same_index_agree(config: Config) -> None:
    """Construction order does not leak into results."""
    context = "The spectrometer measured the mass to charge ratio."
    first = LexicalDisambiguator(config, ExpansionDictionary({"MS": MS_EXPANSIONS}))
    second = LexicalDisambiguator(config, ExpansionDictionary({"MS": MS_EXPANSIONS}))
    assert first.disambiguate("MS", context).model_dump(
        exclude={"metadata"}
    ) == second.disambiguate("MS", context).model_dump(exclude={"metadata"})


def test_neural_tier_degrades_with_a_warning() -> None:
    """Phase 3 is not implemented, so the tier degrades and says so."""
    disambiguator = LexicalDisambiguator(
        Config(engine_tier=EngineTier.NEURAL), ExpansionDictionary({"MS": MS_EXPANSIONS})
    )
    result = disambiguator.disambiguate("MS", "Microsoft ships Windows.")

    assert result.metadata.engine_tier is EngineTier.ZERO_DEPENDENCY
    assert result.metadata.requested_tier is EngineTier.NEURAL
    assert len(result.metadata.warnings) == 1
    assert "NEURAL" in result.metadata.warnings[0]
    assert result.primary_expansion == "Microsoft"


def test_neural_tier_under_strict_refuses_to_degrade() -> None:
    """``strict`` forbids the silent downgrade."""
    with pytest.raises(TierUnavailableError):
        LexicalDisambiguator(Config(engine_tier=EngineTier.NEURAL, strict=True))


def test_metadata_reports_the_context_token_count(config: Config) -> None:
    """``tokens_processed`` counts the tokens the context actually produced."""
    context = "The patient had brain lesions."
    expected = len(Tokenizer(config).tokenize(context))
    result = LexicalDisambiguator(config).disambiguate("BP", context)
    assert result.metadata.tokens_processed == expected


# ===========================================================================
# Property-based tests
# ===========================================================================

_KEY_ALPHABET = "ABCXYZ.- "
_EXPANSION_ALPHABET = "abcdefgh "


@st.composite
def _expansion_mappings(draw: st.DrawFn) -> dict[str, list[str]]:
    """Generate a ``{short form: [expansion, ...]}`` mapping worth indexing."""
    keys = draw(
        st.lists(
            st.text(alphabet=_KEY_ALPHABET, min_size=1, max_size=6),
            min_size=1,
            max_size=4,
            unique_by=lambda key: "".join(c for c in key if c.isalnum()).upper(),
        )
    )
    mapping: dict[str, list[str]] = {}
    for key in keys:
        assume(any(char.isalnum() for char in key))
        values = draw(
            st.lists(
                st.text(alphabet=_EXPANSION_ALPHABET, min_size=1, max_size=14),
                min_size=1,
                max_size=4,
            )
        )
        mapping[key] = [value for value in values if value.strip()]
        assume(mapping[key])
    return mapping


@given(_expansion_mappings())
@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_to_dict_round_trips_through_the_constructor(
    mapping: dict[str, list[str]],
) -> None:
    """Re-indexing an index's own ``to_dict`` is the identity."""
    index = ExpansionDictionary(mapping)
    assert ExpansionDictionary(index.to_dict()).to_dict() == index.to_dict()


@pytest.fixture(scope="module")
def scratch_json(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One reusable JSON path, so the property test does not litter tmp dirs."""
    return tmp_path_factory.mktemp("expansions") / "index.json"


@given(_expansion_mappings())
@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_json_round_trip_preserves_the_index(
    scratch_json: Path, mapping: dict[str, list[str]]
) -> None:
    """A JSON round trip through ``from_json`` preserves keys, values and order."""
    index = ExpansionDictionary(mapping)
    scratch_json.write_text(json.dumps(index.to_dict()), encoding="utf-8")
    assert ExpansionDictionary.from_json(scratch_json).items() == index.items()


@given(_expansion_mappings(), _expansion_mappings())
@settings(max_examples=120, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_merge_never_loses_an_entry(
    left_mapping: dict[str, list[str]], right_mapping: dict[str, list[str]]
) -> None:
    """The merged index is a superset of both operands, key-wise and value-wise."""
    left = ExpansionDictionary(left_mapping)
    right = ExpansionDictionary(right_mapping)
    merged = left.merge(right)

    for source in (left, right):
        for key, expansions in source.items():
            merged_keys = {" ".join(value.split()).casefold() for value in merged.candidates(key)}
            assert key in merged
            for expansion in expansions:
                assert " ".join(expansion.split()).casefold() in merged_keys


@given(
    st.text(alphabet="ABC", min_size=1, max_size=4),
    st.text(alphabet="abcdefgh ", max_size=60),
)
@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_disambiguation_is_deterministic_and_bounded(acronym: str, context: str) -> None:
    """For arbitrary input the result is reproducible and stays in ``[0, 1]``."""
    disambiguator = LexicalDisambiguator(
        Config(), ExpansionDictionary({"ABC": ["alpha beta charlie", "a big cat"]})
    )
    first = disambiguator.disambiguate(acronym, context)
    second = disambiguator.disambiguate(acronym, context)

    assert first.model_dump(exclude={"metadata"}) == second.model_dump(exclude={"metadata"})
    keys = [(-candidate.score, candidate.expansion) for candidate in first.candidates]
    assert keys == sorted(keys)
    for candidate in first.candidates:
        assert 0.0 <= candidate.score <= 1.0
    if first.candidates:
        assert first.primary_expansion == first.candidates[0].expansion
    else:
        assert first.primary_expansion is None
