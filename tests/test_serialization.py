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
from pathlib import Path
from typing import Any, Iterator

import pytest

from acronymkit import AcronymEngine, Config
from acronymkit import serialization as serialization_module
from acronymkit.enums import EngineTier, Language, ScoringStrategy
from acronymkit.exceptions import AcronymKitError, ResourceNotFoundError
from acronymkit.models import (
    AcronymCandidate,
    AcronymPair,
    AcronymResult,
    BackronymResult,
    Token,
)
from acronymkit.resources import read_text_resource
from acronymkit.serialization import (
    SCHEMA_FILENAME,
    SCHEMA_PATH,
    _remote_refs,
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


# ---------------------------------------------------------------------------
# Schema provenance: the directory-hijack regression
# ---------------------------------------------------------------------------
# ``load_schema`` used to search the filesystem before falling back to the
# bundled copy: ``<repo>/schemas/`` and the same directory under two ancestors
# of the package directory. In an installed wheel those ancestors are
# ``<site-packages>/schemas/`` and ``<venv>/Lib/schemas/`` -- directories this
# package does not own, that carry no ``RECORD`` hash, and that any other
# distribution may create. ``schemas`` is a real, installable name on PyPI, so
# claiming one of them takes a line in a requirements file rather than write
# access to the machine.
#
# The audit ran the chain to the end: a planted document was returned in
# preference to the bundled one, and because a JSON Schema may carry a remote
# ``$ref``, ``jsonschema`` then issued a real outbound HTTP GET to fetch it --
# while reporting the attacker's document as valid. The search is gone, and the
# tests below are the proof rather than the changelog entry.
#
# Every decoy here points at the reserved ``.invalid`` TLD (RFC 2606), which
# never resolves. If one of these tests ever regresses, it fails with a name
# resolution error rather than sending a request to a machine somebody else
# controls -- a test suite that reaches the network to prove it does not reach
# the network would be its own bug.

#: A hostile stand-in for the interchange contract. It validates anything, and
#: resolving its ``$ref`` would be an outbound request.
DECOY_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://attacker.invalid/acronym-engine-result.schema.json",
    "title": "HijackedSchema",
    "type": "object",
    "properties": {"anything": {"$ref": "https://attacker.invalid/remote.json"}},
    "additionalProperties": True,
}

#: A schema whose only defect is the remote reference, used to check that
#: ``validate_result`` refuses rather than letting ``jsonschema`` fetch it.
POISONED_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "PoisonedSchema",
    "type": "object",
    "properties": {"metadata": {"$ref": "https://attacker.invalid/metadata.json"}},
}


def all_refs(node: Any) -> list[str]:
    """Return every ``$ref`` string in a decoded JSON document, at any depth.

    Deliberately simpler and broader than
    :func:`acronymkit.serialization._remote_refs`: it collects local fragments
    and relative names too, so a test can assert something about *all* of the
    references in the shipped schema rather than only the ones the production
    check flags.

    Args:
        node: Any decoded-JSON value.

    Returns:
        The ``$ref`` values found, in document order.
    """
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(all_refs(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(all_refs(value))
    return found


@pytest.fixture
def cleared_schema_cache() -> Iterator[None]:
    """Drop the memoised schema text either side of a test.

    ``_schema_source`` is ``lru_cache``d, so by the time any hijack test runs
    the cache is already warm with the real document. Without this fixture such
    a test passes because nothing re-read anything, not because the loader
    ignored the decoy -- which is precisely the kind of false green that would
    have let the original bug through.
    """
    serialization_module._schema_source.cache_clear()
    try:
        yield
    finally:
        serialization_module._schema_source.cache_clear()


@pytest.fixture
def hijacked_checkout_schema(cleared_schema_cache: None) -> Iterator[Path]:
    """Plant :data:`DECOY_SCHEMA` at :data:`SCHEMA_PATH`, then restore the original.

    The original bytes are captured before the write and written back in a
    ``finally``, so a failing assertion leaves the checkout unchanged.

    Yields:
        The hijacked path, for tests that want to assert on it.
    """
    original = SCHEMA_PATH.read_bytes()
    SCHEMA_PATH.write_text(json.dumps(DECOY_SCHEMA, indent=2), encoding="utf-8")
    try:
        yield SCHEMA_PATH
    finally:
        SCHEMA_PATH.write_bytes(original)


def test_load_schema_ignores_a_decoy_planted_at_the_schema_directory(
    hijacked_checkout_schema: Path,
) -> None:
    """**Directory-hijack regression.** A document at ``SCHEMA_PATH`` is not the schema.

    This is the fix's proof. With a hostile document sitting at the exact path
    the loader used to prefer, ``load_schema`` must still return the copy that
    shipped inside the wheel and is hashed in its ``RECORD``.
    """
    assert json.loads(hijacked_checkout_schema.read_text(encoding="utf-8")) == DECOY_SCHEMA

    schema = load_schema()

    assert schema["title"] == "AcronymEngineResult"
    assert schema["$id"].endswith("schemas/acronym-engine-result.schema.json")
    assert "attacker.invalid" not in json.dumps(schema)


def test_load_schema_does_not_consult_the_schema_path_attribute(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, cleared_schema_cache: None
) -> None:
    """Repointing ``SCHEMA_PATH`` cannot change what ``load_schema`` returns.

    The companion to the test above, from the other direction: that one proves
    the *file* is ignored, this one proves the *attribute* is. Together they
    rule out both shapes the old search could come back in.
    """
    decoy = tmp_path / "acronym-engine-result.schema.json"
    decoy.write_text(json.dumps(DECOY_SCHEMA), encoding="utf-8")
    monkeypatch.setattr(serialization_module, "SCHEMA_PATH", decoy)

    assert load_schema()["title"] == "AcronymEngineResult"


def test_load_schema_reads_the_bundled_resource(cleared_schema_cache: None) -> None:
    """The single source is the ``acronymkit.resources`` data file, and nothing else."""
    assert load_schema() == json.loads(read_text_resource(SCHEMA_FILENAME))


def test_load_schema_calls_a_missing_bundled_resource_a_damaged_installation(
    monkeypatch: pytest.MonkeyPatch, cleared_schema_cache: None
) -> None:
    """With no bundled copy there is no fallback left, and the message says so.

    Removing the filesystem search removed the fallback with it, so this branch
    is now reachable in a way it was not before. It must not read as "unusual
    deployment"; the schema is listed in ``RECORD``, so its absence means the
    install is broken.
    """
    monkeypatch.setattr(serialization_module, "has_resource", lambda name: False)

    with pytest.raises(ResourceNotFoundError) as excinfo:
        load_schema()

    message = str(excinfo.value)
    assert SCHEMA_FILENAME in message
    assert "damaged" in message
    assert "reinstall" in message


@requires_jsonschema
def test_validation_still_works_beside_a_hijacked_schema_directory(
    engine: AcronymEngine, hijacked_checkout_schema: Path
) -> None:
    """End to end: a planted schema neither validates the payload nor is fetched.

    The decoy would accept anything and would need a network round trip to
    resolve. Real output validating cleanly here means the bundled contract is
    what was applied.
    """
    validate_result(engine.generate("Portable Document Format").to_dict())


def test_the_checkout_and_bundled_schema_copies_are_semantically_equal() -> None:
    """The two copies of the contract must not drift apart.

    ``schemas/acronym-engine-result.schema.json`` is what the cross-language
    port and external tooling read; the bundled resource is what this package
    reads. Nothing kept them in step, which is how they were free to diverge
    without anything going red.

    Equality is asserted on the decoded documents rather than on the bytes,
    and deliberately so: a checkout under ``core.autocrlf=true`` hands this
    test two files that differ by one byte per line while the committed blobs
    are identical. A byte comparison here would fail on Windows and pass on
    Linux, which is a test that reports the checkout rather than the contract.
    CI asserts the byte equality separately, against the checked-out tree
    where line endings are already normalised. What matters here is that a key
    cannot exist in one copy and not the other.
    """
    checkout = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    bundled = json.loads(read_text_resource(SCHEMA_FILENAME))

    assert checkout == bundled


# ---------------------------------------------------------------------------
# _remote_refs: what would become an outbound request
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "uri",
    [
        "http://attacker.invalid/s.json",
        "https://attacker.invalid/s.json",
        "ftp://attacker.invalid/s.json",
        "ftps://attacker.invalid/s.json",
        "file:///etc/passwd",
        "HTTPS://ATTACKER.INVALID/S.JSON",
    ],
    ids=repr,
)
def test_remote_refs_flags_every_fetchable_scheme(uri: str) -> None:
    """Any scheme-bearing reference is a fetch, including an upper-cased one.

    ``file://`` counts: it is not a network hop, but it is still a document
    from outside the wheel deciding what "valid" means.
    """
    assert _remote_refs({"$ref": uri}) == [f"# -> {uri}"]


def test_remote_refs_walks_dictionaries_to_any_depth() -> None:
    """A reference buried in nested objects is found, and its pointer is reported."""
    document = {
        "properties": {
            "metadata": {"$defs": {"deep": {"$ref": "https://attacker.invalid/deep.json"}}}
        }
    }

    assert _remote_refs(document) == [
        "#/properties/metadata/$defs/deep -> https://attacker.invalid/deep.json"
    ]


def test_remote_refs_walks_lists() -> None:
    """Array positions are traversed too, and indexed in the reported pointer.

    ``allOf`` / ``anyOf`` / ``oneOf`` are lists, so a walk that only recursed
    into dictionaries would miss the most natural place to hide a reference.
    """
    document = {
        "allOf": [
            {"type": "object"},
            {"anyOf": [{"type": "null"}, {"$ref": "http://attacker.invalid/list.json"}]},
        ]
    }

    assert _remote_refs(document) == ["#/allOf/1/anyOf/1 -> http://attacker.invalid/list.json"]


def test_remote_refs_reports_every_hit_not_just_the_first() -> None:
    """A document with three remote references yields three findings."""
    document = {
        "$ref": "https://attacker.invalid/a.json",
        "properties": {"x": {"$ref": "ftp://attacker.invalid/b.json"}},
        "allOf": [{"$ref": "file:///etc/hosts"}],
    }

    assert len(_remote_refs(document)) == 3


@pytest.mark.parametrize(
    "ref",
    ["#", "#/$defs/Token", "#/properties/metadata", "#/$defs/AcronymCandidate/properties/score"],
    ids=repr,
)
def test_remote_refs_ignores_local_fragment_references(ref: str) -> None:
    """A fragment resolves inside the document already in hand, so it is not a fetch."""
    assert _remote_refs({"properties": {"anything": {"$ref": ref}}}) == []


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"type": "object"},
        {"properties": {"score": {"type": "number"}}},
        {"allOf": [{"type": "object"}, {"required": ["metadata"]}]},
        {"$ref": 42},
        [1, "two", None],
        "not a document",
        None,
    ],
    ids=repr,
)
def test_remote_refs_returns_nothing_for_a_local_only_document(document: Any) -> None:
    """No reference, no finding -- and a non-mapping input is not an error."""
    assert _remote_refs(document) == []


# ---------------------------------------------------------------------------
# The shipped schema, as an enforced invariant
# ---------------------------------------------------------------------------
def test_the_shipped_schema_contains_no_remote_reference() -> None:
    """ "Our schema happens to have no remote ``$ref``" becomes a checked invariant.

    ``validate_result`` refuses at run time if this ever stops holding, but by
    then it is a production failure. Asserting it here means adding one to the
    document fails in review instead.
    """
    assert _remote_refs(load_schema()) == []


def test_all_refs_finds_the_reference_shapes_remote_refs_ignores() -> None:
    """The invariant below leans on this helper, so the helper is pinned here.

    ``test_the_shipped_schema_uses_only_local_fragment_references`` passes
    vacuously today -- the shipped document carries no ``$ref`` at all -- so a
    silently broken ``all_refs`` would keep it green forever, including on the
    day somebody adds the relative reference it exists to catch. Checking the
    walk against a document holding one of each shape makes that test's vacuity
    a property of the schema rather than of the helper.

    The second assertion is the gap itself, written down as an executable fact:
    ``_remote_refs`` reports the scheme-bearing reference and says nothing about
    ``common.json``, which ``jsonschema`` would resolve against this schema's
    ``https://`` ``$id`` and fetch.
    """
    document = {
        "$ref": "#/$defs/Token",
        "properties": {"a": {"$ref": "common.json"}},
        "allOf": [{"$ref": "https://attacker.invalid/x.json"}],
    }

    assert all_refs(document) == [
        "#/$defs/Token",
        "common.json",
        "https://attacker.invalid/x.json",
    ]
    assert _remote_refs(document) == ["#/allOf/0 -> https://attacker.invalid/x.json"]


def test_the_shipped_schema_uses_only_local_fragment_references() -> None:
    """Every ``$ref`` in the contract starts with ``#`` -- today there are none at all.

    Stronger than the test above, and deliberately so. ``_remote_refs`` flags
    references that name a scheme; it does not flag a *relative* one such as
    ``common.json``, which ``jsonschema`` resolves against the base URI -- and
    this schema's ``$id`` is an ``https://`` URL, so a relative reference would
    resolve to a fetch that the production check would let through.

    The shipped document is currently reference-free, so this passes vacuously
    right now and is written for the day it stops being: the natural way to
    factor a growing schema is ``$defs`` plus fragments, and the natural way to
    share one across the cross-language port is a sibling file. The first is
    safe, the second is not, and only this test tells them apart.
    """
    refs = all_refs(load_schema())

    assert all(ref.startswith("#") for ref in refs), refs


# ---------------------------------------------------------------------------
# validate_result refuses a poisoned schema
# ---------------------------------------------------------------------------
@requires_jsonschema
def test_validate_result_refuses_a_schema_carrying_a_remote_reference(
    monkeypatch: pytest.MonkeyPatch, engine: AcronymEngine
) -> None:
    """Validation is where a foreign document would turn into a socket, so it checks first.

    ``jsonschema.validate`` is replaced with a tripwire: the refusal has to
    happen *before* the validator is handed a document it would resolve
    references from. A check that ran afterwards would be decoration.
    """
    import jsonschema

    def must_not_run(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("jsonschema.validate must not be reached with a poisoned schema")

    monkeypatch.setattr(
        serialization_module, "load_schema", lambda: json.loads(json.dumps(POISONED_SCHEMA))
    )
    monkeypatch.setattr(jsonschema, "validate", must_not_run)

    with pytest.raises(AcronymKitError) as excinfo:
        validate_result(engine.generate("Portable Document Format").to_dict())

    message = str(excinfo.value)
    assert "https://attacker.invalid/metadata.json" in message, "the message must name the ref"
    assert "#/properties/metadata" in message, "the message must locate the ref"
    assert "network" in message


@requires_jsonschema
def test_the_refusal_counts_every_remote_reference_it_found(
    monkeypatch: pytest.MonkeyPatch, engine: AcronymEngine
) -> None:
    """Two poisoned references are reported as two, and both are named."""
    poisoned = json.loads(json.dumps(POISONED_SCHEMA))
    poisoned["properties"]["tokens"] = {"$ref": "http://attacker.invalid/tokens.json"}
    monkeypatch.setattr(serialization_module, "load_schema", lambda: poisoned)

    with pytest.raises(AcronymKitError) as excinfo:
        validate_result(engine.generate("Portable Document Format").to_dict())

    message = str(excinfo.value)
    assert "2 remote $ref" in message
    assert "https://attacker.invalid/metadata.json" in message
    assert "http://attacker.invalid/tokens.json" in message
