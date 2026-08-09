"""Behavioural tests for :mod:`acronymkit.models`.

The DTOs carry the library's public contract: they are frozen, they reject
unknown fields, and ``to_dict()`` must be plain JSON. Everything else the models
do is a small number of derived helpers, all pinned here.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel, ValidationError

from acronymkit.enums import EngineTier, Language, MappingKind, StopWordCategory, TokenRole
from acronymkit.models import (
    AcronymCandidate,
    AcronymPair,
    AcronymResult,
    BackronymCandidate,
    BackronymResult,
    BatchResult,
    DisambiguationCandidate,
    DisambiguationResult,
    EngineMetadata,
    ExtractionResult,
    LetterMapping,
    ScoreBreakdown,
    Token,
)

# ---------------------------------------------------------------------------
# One representative, fully populated instance of every model
# ---------------------------------------------------------------------------
TOKEN = Token(
    text="Portable",
    normalized="portable",
    index=0,
    start=0,
    end=8,
    role=TokenRole.CONTENT,
    stop_word_category=None,
    pos="ADJ",
    lemma="portable",
    is_critical=True,
    is_eligible=True,
    letters="PO",
    subtokens=[],
)

FUNCTION_TOKEN = Token(
    text="of",
    normalized="of",
    index=1,
    start=9,
    end=11,
    role=TokenRole.FUNCTION,
    stop_word_category=StopWordCategory.PREPOSITION,
    is_critical=False,
    is_eligible=False,
    letters="",
)

MAPPING = LetterMapping(
    character="P",
    position=0,
    token_index=0,
    char_offset=0,
    kind=MappingKind.INITIAL,
    weight=10.0,
)

UNMAPPED = LetterMapping(character="Z", position=2, kind=MappingKind.UNMAPPED, weight=0.0)

BREAKDOWN = ScoreBreakdown(
    positional=30.0,
    phonotactic=-6.5,
    lexical=1.0,
    information_loss=2.0,
    alpha=1.0,
    beta=2.0,
    gamma=12.0,
    delta=15.0,
    total=17.5,
)

CANDIDATE = AcronymCandidate(
    acronym="PDF",
    score=17.5,
    is_dictionary_word=False,
    pronounceability_score=0.42,
    raw_phonotactic_score=-6.5,
    mappings=[MAPPING],
    covered_token_indices=[0, 1, 2],
    skipped_token_indices=[],
    breakdown=BREAKDOWN,
)

METADATA = EngineMetadata(
    engine_tier=EngineTier.ZERO_DEPENDENCY,
    execution_time_ms=1.25,
    tokens_processed=3,
    candidates_evaluated=9,
    language=Language.EN,
    library_version="0.1.0",
    nlp_backend="heuristic",
    requested_tier=EngineTier.AUTO,
    warnings=["degraded"],
    truncated=False,
)

RESULT = AcronymResult(
    source_phrase="Portable Document Format",
    primary_acronym="PDF",
    score=17.5,
    alternatives=[CANDIDATE],
    tokens=[TOKEN, FUNCTION_TOKEN],
    metadata=METADATA,
)

PAIR = AcronymPair(
    short_form="NASA",
    long_form="National Aeronautics and Space Administration",
    short_form_span=(50, 54),
    long_form_span=(4, 49),
    confidence=1.0,
    pattern="long(short)",
    sentence="The National Aeronautics and Space Administration (NASA) launched it.",
)

EXTRACTION = ExtractionResult(
    source_text="The National Aeronautics and Space Administration (NASA) launched it.",
    pairs=[PAIR],
    metadata=METADATA,
)

BACKRONYM_CANDIDATE = BackronymCandidate(
    target_word="NEXUS",
    expansion=["Next", "Generation", "eXchange", "Utility", "System"],
    expansion_text="Next Generation eXchange Utility System",
    score=31.0,
    coverage=1.0,
    mappings=[MAPPING],
    unmapped_letters=[],
    breakdown=BREAKDOWN,
)

BACKRONYM_RESULT = BackronymResult(
    source_phrase="Next Generation eXchange Utility System",
    target_word="NEXUS",
    primary_expansion="Next Generation eXchange Utility System",
    score=31.0,
    candidates=[BACKRONYM_CANDIDATE],
    metadata=METADATA,
)

DISAMBIGUATION_CANDIDATE = DisambiguationCandidate(
    expansion="Blood pressure",
    score=1.0,
    source="inline",
    evidence=["blood", "pressure"],
)

DISAMBIGUATION_RESULT = DisambiguationResult(
    acronym="BP",
    context="Blood pressure (BP) was elevated.",
    primary_expansion="Blood pressure",
    candidates=[DISAMBIGUATION_CANDIDATE],
    metadata=METADATA,
)

BATCH = BatchResult(
    results=[RESULT, None],
    errors={1: "EmptyPhraseError: phrase '' contains no tokens"},
    total_execution_time_ms=4.5,
)

#: ``(label, instance)`` for every model in ``acronymkit.models.__all__``.
INSTANCES: list[tuple[str, BaseModel]] = [
    ("Token", TOKEN),
    ("LetterMapping", MAPPING),
    ("ScoreBreakdown", BREAKDOWN),
    ("AcronymCandidate", CANDIDATE),
    ("EngineMetadata", METADATA),
    ("AcronymResult", RESULT),
    ("AcronymPair", PAIR),
    ("ExtractionResult", EXTRACTION),
    ("BackronymCandidate", BACKRONYM_CANDIDATE),
    ("BackronymResult", BACKRONYM_RESULT),
    ("DisambiguationCandidate", DISAMBIGUATION_CANDIDATE),
    ("DisambiguationResult", DISAMBIGUATION_RESULT),
    ("BatchResult", BATCH),
]

MODEL_CLASSES = [type(instance) for _, instance in INSTANCES]

IDS = [label for label, _ in INSTANCES]


def test_every_exported_model_is_covered() -> None:
    """The instance table above stays in step with ``models.__all__``."""
    from acronymkit import models

    assert sorted(IDS) == sorted(models.__all__)


# ---------------------------------------------------------------------------
# Frozen-ness
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(("label", "instance"), INSTANCES, ids=IDS)
def test_every_model_is_frozen(label: str, instance: BaseModel) -> None:
    """Assignment to any declared field raises rather than mutating."""
    for field in type(instance).model_fields:
        before = getattr(instance, field)
        with pytest.raises(ValidationError):
            setattr(instance, field, before)
        assert getattr(instance, field) == before


@pytest.mark.parametrize(("label", "instance"), INSTANCES, ids=IDS)
def test_models_reject_undeclared_attributes(label: str, instance: BaseModel) -> None:
    """A typo'd attribute name is an error, not a silently created field."""
    with pytest.raises(ValueError):
        instance.definitely_not_a_field = 1


@pytest.mark.parametrize("model_cls", MODEL_CLASSES, ids=IDS)
def test_extra_construction_fields_are_rejected(model_cls: type) -> None:
    """``extra='forbid'`` catches a payload the model does not understand."""
    with pytest.raises(ValidationError) as excinfo:
        model_cls(unexpected_field="boom")
    assert "unexpected_field" in str(excinfo.value)


# ---------------------------------------------------------------------------
# model_copy
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("instance", "update"),
    [
        (TOKEN, {"letters": "PDF", "role": TokenRole.ACRONYM}),
        (MAPPING, {"kind": MappingKind.INTERNAL, "weight": 3.0}),
        (BREAKDOWN, {"total": 99.0}),
        (CANDIDATE, {"acronym": "PODOFO", "score": -1.0}),
        (METADATA, {"truncated": True, "tokens_processed": 42}),
        (RESULT, {"primary_acronym": "PD"}),
        (PAIR, {"confidence": 0.6}),
        (BACKRONYM_CANDIDATE, {"coverage": 0.5}),
        (DISAMBIGUATION_CANDIDATE, {"source": "dictionary"}),
        (BATCH, {"total_execution_time_ms": 0.0}),
    ],
    ids=lambda value: type(value).__name__ if isinstance(value, BaseModel) else "update",
)
def test_model_copy_applies_updates_without_touching_the_original(
    instance: BaseModel, update: dict
) -> None:
    """``model_copy(update=...)`` is the supported way to derive a frozen DTO."""
    before = instance.model_dump()
    copy = instance.model_copy(update=update)

    assert copy is not instance
    for field, value in update.items():
        assert getattr(copy, field) == value
        assert getattr(instance, field) == before[field]
    assert instance.model_dump() == before


def test_model_copy_recomputes_computed_fields() -> None:
    """``length`` follows the copied acronym, not the original."""
    copy = CANDIDATE.model_copy(update={"acronym": "SCUBA"})
    assert copy.length == 5
    assert CANDIDATE.length == 3


def test_model_copy_deep_leaves_the_original_alone() -> None:
    """A deep copy shares nothing mutable with its source."""
    copy = RESULT.model_copy(deep=True)
    assert copy == RESULT
    assert copy.alternatives is not RESULT.alternatives
    assert copy.tokens[0] == RESULT.tokens[0]


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(("label", "instance"), INSTANCES, ids=IDS)
def test_to_dict_is_json_serialisable(label: str, instance: BaseModel) -> None:
    """``to_dict()`` never contains anything :mod:`json` cannot encode."""
    payload = instance.to_dict()
    assert isinstance(payload, dict)
    encoded = json.dumps(payload)  # would raise on an enum, Path, set or tuple
    assert json.loads(encoded) == payload


@pytest.mark.parametrize(("label", "instance"), INSTANCES, ids=IDS)
def test_to_json_round_trips_to_to_dict(label: str, instance: BaseModel) -> None:
    """``json.loads(to_json()) == to_dict()`` for every model."""
    assert json.loads(instance.to_json()) == instance.to_dict()
    assert json.loads(instance.to_json(indent=2)) == instance.to_dict()


@pytest.mark.parametrize(
    ("instance", "field", "expected"),
    [
        (TOKEN, "role", "content"),
        (FUNCTION_TOKEN, "stop_word_category", "preposition"),
        (MAPPING, "kind", "initial"),
        (UNMAPPED, "kind", "unmapped"),
        (METADATA, "engine_tier", "zero_dependency"),
        (METADATA, "requested_tier", "auto"),
        (METADATA, "language", "en"),
    ],
    ids=lambda value: str(value),
)
def test_enum_fields_serialise_as_their_string_values(
    instance: BaseModel, field: str, expected: str
) -> None:
    """Enums leave the library as plain strings, never as ``EngineTier.AUTO``."""
    value = instance.to_dict()[field]
    assert value == expected
    assert type(value) is str


def test_optional_enum_field_serialises_as_null() -> None:
    """An absent optional enum is JSON ``null``, not the string ``'None'``."""
    assert TOKEN.to_dict()["stop_word_category"] is None


def test_tuple_span_serialises_as_a_json_array() -> None:
    """``AcronymPair`` spans survive as two-element arrays."""
    payload = PAIR.to_dict()
    assert payload["short_form_span"] == [50, 54]
    assert payload["long_form_span"] == [4, 49]


def test_batch_result_error_keys_survive_json() -> None:
    """Integer error indices become JSON object keys and come back parseable."""
    payload = json.loads(BATCH.to_json())
    assert {int(key) for key in payload["errors"]} == set(BATCH.errors)


def test_acronym_result_to_dict_includes_the_computed_length() -> None:
    """Computed fields are part of the wire payload."""
    payload = RESULT.to_dict()
    assert payload["alternatives"][0]["length"] == 3


@given(
    acronym=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", max_size=12),
    score=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
)
def test_candidate_serialisation_round_trips(acronym: str, score: float) -> None:
    """Property: dump -> JSON -> load -> rebuild is the identity."""
    candidate = AcronymCandidate(acronym=acronym, score=score)
    payload = json.loads(candidate.to_json())
    assert payload["acronym"] == acronym
    assert payload["length"] == len(acronym)
    # ``length`` is computed, so it is not a constructor argument.
    payload.pop("length")
    assert AcronymCandidate(**payload) == candidate


# ---------------------------------------------------------------------------
# AcronymCandidate
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("acronym", ["", "A", "PDF", "SCUBA", "A1B2C3", "É"], ids=repr)
def test_candidate_length_is_the_acronym_length(acronym: str) -> None:
    """``length`` is exactly ``len(acronym)``, including for the empty string."""
    assert AcronymCandidate(acronym=acronym, score=0.0).length == len(acronym)


def test_candidate_length_is_not_settable() -> None:
    """``length`` is derived, so it is not a constructor field."""
    with pytest.raises(ValidationError):
        AcronymCandidate(acronym="PDF", score=0.0, length=99)


# ---------------------------------------------------------------------------
# AcronymResult helpers
# ---------------------------------------------------------------------------
def test_primary_returns_the_matching_candidate() -> None:
    """``primary`` resolves ``primary_acronym`` back to its full record."""
    second = CANDIDATE.model_copy(update={"acronym": "PD", "score": 1.0})
    result = RESULT.model_copy(
        update={"alternatives": [second, CANDIDATE], "primary_acronym": "PDF"}
    )
    assert result.primary is CANDIDATE


def test_primary_is_none_when_there_are_no_alternatives() -> None:
    """An empty candidate list yields ``None`` rather than an IndexError."""
    result = RESULT.model_copy(update={"alternatives": []})
    assert result.primary is None


def test_top_truncates_the_ranked_list() -> None:
    """``top(n)`` is a prefix of ``alternatives``."""
    alternatives = [CANDIDATE.model_copy(update={"acronym": name}) for name in ("A", "B", "C", "D")]
    result = RESULT.model_copy(update={"alternatives": alternatives})
    assert result.top(2) == alternatives[:2]
    assert result.top(99) == alternatives


# ---------------------------------------------------------------------------
# ExtractionResult.as_mapping
# ---------------------------------------------------------------------------
def test_as_mapping_keeps_the_first_long_form_per_short_form() -> None:
    """A document defines an abbreviation on first use; later uses do not win."""
    first = AcronymPair(short_form="BP", long_form="Blood Pressure")
    later = AcronymPair(short_form="BP", long_form="British Petroleum")
    other = AcronymPair(short_form="MRI", long_form="Magnetic Resonance Imaging")
    extraction = EXTRACTION.model_copy(update={"pairs": [first, later, other]})

    assert extraction.as_mapping() == {
        "BP": "Blood Pressure",
        "MRI": "Magnetic Resonance Imaging",
    }


def test_as_mapping_is_empty_for_a_document_that_defines_nothing() -> None:
    """No pairs means no mapping, not a ``None``."""
    assert EXTRACTION.model_copy(update={"pairs": []}).as_mapping() == {}


def test_as_mapping_returns_a_fresh_mutable_dict() -> None:
    """The helper hands out a private dict, not a view onto the frozen model."""
    mapping = EXTRACTION.as_mapping()
    mapping["EXTRA"] = "added by the caller"
    assert "EXTRA" not in EXTRACTION.as_mapping()


@given(short_forms=st.lists(st.sampled_from(["BP", "MRI", "API", "SVM"]), min_size=1, max_size=8))
def test_as_mapping_is_first_wins_for_any_pair_sequence(
    short_forms: list[str],
) -> None:
    """Property: each key maps to the long form of its first occurrence."""
    pairs = [
        AcronymPair(short_form=short, long_form=f"expansion {index}")
        for index, short in enumerate(short_forms)
    ]
    mapping = ExtractionResult(source_text="", pairs=pairs, metadata=METADATA).as_mapping()
    for short in set(short_forms):
        assert mapping[short] == f"expansion {short_forms.index(short)}"


# ---------------------------------------------------------------------------
# BatchResult
# ---------------------------------------------------------------------------
def test_batch_succeeded_and_failure_count() -> None:
    """``succeeded`` drops the ``None`` slots; ``failure_count`` counts errors."""
    assert BATCH.succeeded == [RESULT]
    assert BATCH.failure_count == 1
    assert len(BATCH.results) == 2


def test_batch_succeeded_preserves_submission_order() -> None:
    """Successes come back in the order they were submitted."""
    second = RESULT.model_copy(update={"primary_acronym": "RAM"})
    batch = BatchResult(results=[RESULT, None, second], errors={1: "boom"})
    assert [item.primary_acronym for item in batch.succeeded] == ["PDF", "RAM"]


def test_empty_batch_has_no_successes_and_no_failures() -> None:
    """The empty envelope is well defined."""
    empty = BatchResult()
    assert empty.results == []
    assert empty.succeeded == []
    assert empty.failure_count == 0
    assert empty.total_execution_time_ms == 0.0


@given(
    flags=st.lists(st.booleans(), min_size=0, max_size=10),
)
def test_failure_count_equals_the_number_of_none_slots(flags: list[bool]) -> None:
    """Property: ``failure_count`` and the ``None`` slots agree."""
    results: list[Any] = [RESULT if ok else None for ok in flags]
    errors = {index: "boom" for index, ok in enumerate(flags) if not ok}
    batch = BatchResult(results=results, errors=errors)
    assert batch.failure_count == results.count(None)
    assert len(batch.succeeded) == len(results) - batch.failure_count


# ---------------------------------------------------------------------------
# ScoreBreakdown.explain
# ---------------------------------------------------------------------------
def test_explain_traces_the_four_terms_and_the_total() -> None:
    """``explain`` is the printable form of ``S = a*P + b*Phi + g*L - d*Psi``."""
    assert BREAKDOWN.explain() == ("S = 1*30.000 + 2*-6.500 + 12*1.000 - 15*2.000 = 17.500")


@pytest.mark.parametrize(
    "breakdown",
    [
        BREAKDOWN,
        BREAKDOWN.model_copy(update={"positional": 0.0, "total": 0.0}),
        BREAKDOWN.model_copy(update={"alpha": 0.5, "beta": 0.25}),
        ScoreBreakdown(
            positional=-2.0,
            phonotactic=-9.0,
            lexical=0.0,
            information_loss=3.0,
            alpha=1.0,
            beta=1.0,
            gamma=1.0,
            delta=1.0,
            total=-14.0,
        ),
    ],
    ids=["default", "zeroed", "rescaled", "negative"],
)
def test_explain_mentions_every_coefficient_and_term(
    breakdown: ScoreBreakdown,
) -> None:
    """The trace is complete: nothing in the formula is left implicit."""
    text = breakdown.explain()
    assert text.startswith("S = ")
    assert text.endswith(f"= {breakdown.total:.3f}")
    for value in (
        breakdown.positional,
        breakdown.phonotactic,
        breakdown.lexical,
        breakdown.information_loss,
    ):
        assert f"{value:.3f}" in text


def test_explain_prints_the_four_terms_but_not_the_length_penalty() -> None:
    """The trace shows ``S(A, T)``'s four terms and ``total``, and only those.

    ``total`` additionally carries ``-length_penalty * max(0, len(A) -
    preferred_length)`` (see :meth:`acronymkit.scoring.Scorer.score`), which
    ``explain`` does not render. The printed arithmetic therefore need not
    balance whenever a length penalty applied — pinned here so the discrepancy
    is a known, deliberate one rather than a surprise.
    """
    four_terms = (
        BREAKDOWN.alpha * BREAKDOWN.positional
        + BREAKDOWN.beta * BREAKDOWN.phonotactic
        + BREAKDOWN.gamma * BREAKDOWN.lexical
        - BREAKDOWN.delta * BREAKDOWN.information_loss
    )
    # 1*30 + 2*(-6.5) + 12*1 - 15*2 = 30 - 13 + 12 - 30 = -1.0
    assert four_terms == pytest.approx(-1.0)
    assert BREAKDOWN.explain().endswith("= 17.500")


def test_explain_balances_when_no_length_penalty_applied() -> None:
    """With the length term inactive the printed sum does reconstruct ``total``."""
    balanced = ScoreBreakdown(
        positional=30.0,
        phonotactic=-6.0,
        lexical=1.0,
        information_loss=0.0,
        alpha=1.0,
        beta=1.0,
        gamma=12.0,
        delta=15.0,
        total=36.0,
    )
    assert balanced.explain() == "S = 1*30.000 + 1*-6.000 + 12*1.000 - 15*0.000 = 36.000"
    assert (
        balanced.alpha * balanced.positional
        + balanced.beta * balanced.phonotactic
        + balanced.gamma * balanced.lexical
        - balanced.delta * balanced.information_loss
    ) == pytest.approx(balanced.total)
