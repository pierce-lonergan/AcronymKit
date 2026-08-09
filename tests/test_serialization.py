"""Tests for :mod:`acronymkit.serialization` and the interchange contract.

``schemas/acronym-engine-result.schema.json`` is a cross-language specification:
both this package and the planned ``acronym4j`` port must emit payloads that
validate against it. The heart of this module is therefore the corpus sweep in
:func:`test_canonical_corpus_validates_against_the_schema` — every result the
engine produces for the canonical phrases is checked against the published
schema, not against a hand-written expectation.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from acronymkit import AcronymEngine, Config
from acronymkit.enums import EngineTier, Language, ScoringStrategy
from acronymkit.models import (
    AcronymCandidate,
    AcronymPair,
    AcronymResult,
    BackronymResult,
    Token,
)
from acronymkit.serialization import (
    SCHEMA_PATH,
    export_model_schema,
    load_schema,
    to_json,
    validate_result,
)
from conftest import CANONICAL_ACRONYMS, requires_jsonschema

PHRASES = [phrase for phrase, _ in CANONICAL_ACRONYMS]


# ---------------------------------------------------------------------------
# load_schema
# ---------------------------------------------------------------------------
def test_load_schema_returns_the_published_contract() -> None:
    """The schema is discoverable from a source checkout and correctly named."""
    schema = load_schema()
    assert isinstance(schema, dict)
    assert schema["title"] == "AcronymEngineResult"
    assert schema["$id"] == (
        "https://raw.githubusercontent.com/pierce-lonergan/AcronymKit/main/"
        "schemas/acronym-engine-result.schema.json"
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object"
    assert set(schema["required"]) == {
        "source_phrase",
        "primary_acronym",
        "alternatives",
        "metadata",
    }


def test_schema_path_points_at_the_checkout_copy() -> None:
    """``SCHEMA_PATH`` names the repository file the tests are validating against."""
    assert SCHEMA_PATH.name == "acronym-engine-result.schema.json"
    assert SCHEMA_PATH.parent.name == "schemas"
    assert SCHEMA_PATH.is_file()
    assert json.loads(SCHEMA_PATH.read_text(encoding="utf-8")) == load_schema()


def test_load_schema_hands_out_a_private_document() -> None:
    """The cached source text is re-parsed, so mutation cannot leak between callers."""
    first = load_schema()
    first["title"] = "mutated"
    assert load_schema()["title"] == "AcronymEngineResult"


# ---------------------------------------------------------------------------
# Schema conformance of real engine output
# ---------------------------------------------------------------------------
@requires_jsonschema
@pytest.mark.parametrize("phrase", PHRASES, ids=PHRASES)
def test_canonical_corpus_validates_against_the_schema(engine: AcronymEngine, phrase: str) -> None:
    """Every canonical result conforms to the published interchange contract."""
    result = engine.generate(phrase)
    validate_result(result.to_dict())


@requires_jsonschema
@pytest.mark.parametrize("phrase", PHRASES, ids=PHRASES)
def test_validate_result_accepts_the_model_directly(engine: AcronymEngine, phrase: str) -> None:
    """``validate_result`` dumps a model for you rather than demanding a dict."""
    validate_result(engine.generate(phrase))


@requires_jsonschema
@pytest.mark.parametrize(
    "config",
    [
        Config(),
        Config(include_breakdown=False),
        Config(max_candidates=1),
        Config(case_style="lower"),
        Config(scoring_strategy=ScoringStrategy.MAX_PRONOUNCEABLE),
        Config.fast(),
        Config(engine_tier=EngineTier.AUTO),
    ],
    ids=[
        "default",
        "no-breakdown",
        "single-candidate",
        "lower-case",
        "max-pronounceable",
        "fast",
        "auto-tier",
    ],
)
def test_schema_conformance_survives_configuration_changes(config: Config) -> None:
    """Configuration must not be able to produce a non-conformant payload."""
    engine = AcronymEngine(config)
    for phrase in PHRASES[:6]:
        validate_result(engine.generate(phrase).to_dict())


@requires_jsonschema
def test_result_with_warnings_still_validates() -> None:
    """A degraded run carries warnings, which the schema permits."""
    engine = AcronymEngine(Config(engine_tier=EngineTier.NEURAL))
    result = engine.generate("Portable Document Format")
    assert result.metadata.warnings  # the degradation notice is present
    validate_result(result.to_dict())


@requires_jsonschema
@pytest.mark.parametrize("field", ["source_phrase", "primary_acronym", "alternatives", "metadata"])
def test_validate_result_rejects_a_payload_missing_a_required_field(
    engine: AcronymEngine, field: str
) -> None:
    """Dropping any required top-level field is a validation failure."""
    import jsonschema

    payload = engine.generate("Portable Document Format").to_dict()
    del payload[field]
    with pytest.raises(jsonschema.exceptions.ValidationError) as excinfo:
        validate_result(payload)
    assert field in str(excinfo.value)


@requires_jsonschema
@pytest.mark.parametrize(
    ("pointer", "value"),
    [
        (("primary_acronym",), 42),
        (("score",), "not-a-number"),
        (("alternatives",), {"acronym": "PDF"}),
        (("metadata", "engine_tier"), "quantum"),
        (("metadata", "tokens_processed"), -1),
        (("metadata", "execution_time_ms"), -0.5),
        (("alternatives", 0, "pronounceability_score"), 1.5),
        (("alternatives", 0, "raw_phonotactic_score"), 3.0),
        (("alternatives", 0, "mappings", 0, "kind"), "sideways"),
        (("tokens", 0, "role"), "verb"),
    ],
    ids=lambda value: str(value),
)
def test_schema_rejects_out_of_contract_values(
    engine: AcronymEngine, pointer: tuple, value: Any
) -> None:
    """The schema is a real constraint, not a rubber stamp."""
    import jsonschema

    payload = engine.generate("Portable Document Format").to_dict()
    target: Any = payload
    for key in pointer[:-1]:
        target = target[key]
    target[pointer[-1]] = value
    with pytest.raises(jsonschema.exceptions.ValidationError):
        validate_result(payload)


@requires_jsonschema
def test_schema_permits_additional_diagnostic_properties() -> None:
    """Implementations may attach richer diagnostics, as the description promises."""
    engine = AcronymEngine(Config())
    payload = engine.generate("Portable Document Format").to_dict()
    payload["vendor_diagnostics"] = {"beam_states": 17}
    validate_result(payload)


@requires_jsonschema
def test_backronym_and_extraction_payloads_are_plain_json() -> None:
    """Non-generation results are still ordinary JSON documents."""
    engine = AcronymEngine(Config())
    backronym = engine.generate_backronym("Next Generation eXchange Utility System", "NEXUS")
    extraction = engine.extract("The World Health Organization (WHO) issued guidance.")
    for model in (backronym, extraction):
        assert json.loads(model.to_json()) == model.to_dict()


# ---------------------------------------------------------------------------
# to_json / to_dict round trips
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phrase", PHRASES, ids=PHRASES)
def test_to_json_round_trips_through_json_loads(engine: AcronymEngine, phrase: str) -> None:
    """``json.loads(result.to_json()) == result.to_dict()`` exactly."""
    result = engine.generate(phrase)
    assert json.loads(result.to_json()) == result.to_dict()


@pytest.mark.parametrize("indent", [None, 0, 2, 4], ids=repr)
def test_module_level_to_json_round_trips_at_every_indent(
    engine: AcronymEngine, indent: int
) -> None:
    """``serialization.to_json`` matches the model's own serialisation."""
    result = engine.generate("Application Programming Interface")
    assert json.loads(to_json(result, indent)) == result.to_dict()


def test_to_json_accepts_a_plain_payload() -> None:
    """Already-plain data passes straight through :func:`json.dumps`."""
    payload = {"short_form": "API", "long_form": "Application Programming Interface"}
    assert json.loads(to_json(payload)) == payload


def test_to_json_emits_non_ascii_verbatim() -> None:
    """Accented source phrases stay readable rather than being escaped."""
    pair = AcronymPair(short_form="ÉN", long_form="École Nationale")
    text = to_json(pair)
    assert "École" in text
    assert "\\u" not in text


def test_to_json_rejects_unencodable_payloads() -> None:
    """A plain payload holding a non-JSON value is a ``TypeError``."""
    with pytest.raises(TypeError):
        to_json({"bad": object()})


@pytest.mark.parametrize("phrase", PHRASES[:6], ids=PHRASES[:6])
def test_result_rebuilds_from_its_own_payload(engine: AcronymEngine, phrase: str) -> None:
    """The wire payload is complete: a result can be reconstructed from it."""
    result = engine.generate(phrase)
    payload = json.loads(result.to_json())
    for candidate in payload["alternatives"]:
        candidate.pop("length")  # computed, not a constructor field
    rebuilt = AcronymResult(**payload)
    assert rebuilt.primary_acronym == result.primary_acronym
    assert rebuilt.to_dict() == result.to_dict()


# ---------------------------------------------------------------------------
# Enum serialisation
# ---------------------------------------------------------------------------
def test_enum_fields_serialise_as_strings_in_engine_output(
    engine: AcronymEngine,
) -> None:
    """No enum object survives into the payload."""
    payload = engine.generate("Portable Document Format").to_dict()
    metadata = payload["metadata"]
    assert metadata["engine_tier"] == EngineTier.ZERO_DEPENDENCY.value
    assert metadata["requested_tier"] == EngineTier.ZERO_DEPENDENCY.value
    assert metadata["language"] == Language.EN.value
    for key in ("engine_tier", "requested_tier", "language"):
        assert type(metadata[key]) is str
    for token in payload["tokens"]:
        assert type(token["role"]) is str
        assert token["stop_word_category"] is None or type(token["stop_word_category"]) is str
    for candidate in payload["alternatives"]:
        for mapping in candidate["mappings"]:
            assert type(mapping["kind"]) is str


def test_json_text_contains_no_enum_reprs(engine: AcronymEngine) -> None:
    """``EngineTier.ZERO_DEPENDENCY`` must never appear in the wire form."""
    text = engine.generate("Central Processing Unit").to_json()
    for name in ("EngineTier.", "TokenRole.", "MappingKind.", "Language."):
        assert name not in text


# ---------------------------------------------------------------------------
# export_model_schema
# ---------------------------------------------------------------------------
def test_export_model_schema_defaults_to_acronym_result() -> None:
    """With no argument the payload the interchange schema governs is described."""
    schema = export_model_schema()
    assert schema["title"] == "AcronymResult"
    assert schema["type"] == "object"
    assert set(schema["properties"]) >= {
        "source_phrase",
        "primary_acronym",
        "score",
        "alternatives",
        "tokens",
        "metadata",
    }


@pytest.mark.parametrize(
    "model",
    [AcronymResult, AcronymCandidate, Token, AcronymPair, BackronymResult],
    ids=lambda model: model.__name__,
)
def test_export_model_schema_describes_any_model(model: type) -> None:
    """Every DTO can publish a schema, and it is JSON-encodable."""
    schema = export_model_schema(model)
    assert schema["title"] == model.__name__
    json.dumps(schema)


def test_export_model_schema_is_in_serialisation_mode() -> None:
    """Computed fields appear because the schema describes ``to_dict()`` output."""
    schema = export_model_schema(AcronymCandidate)
    assert "length" in schema["properties"]


@pytest.mark.parametrize(
    "not_a_model", [object(), dict, "AcronymResult", 42, None.__class__], ids=repr
)
def test_export_model_schema_rejects_non_models(not_a_model: object) -> None:
    """A non-Pydantic argument is a ``TypeError`` with a clear message."""
    with pytest.raises(TypeError, match="BaseModel"):
        export_model_schema(not_a_model)  # type: ignore[arg-type]


def test_export_model_schema_returns_a_private_dict() -> None:
    """Callers may edit the exported schema without corrupting later exports."""
    schema = export_model_schema()
    schema["title"] = "mutated"
    assert export_model_schema()["title"] == "AcronymResult"
