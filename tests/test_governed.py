"""Acceptance gate for :mod:`acronymkit.governed`.

The governed subsystem's whole claim is that its answers come from a written-down
vocabulary rather than from a model, so a test suite that derived its
expectations by calling the subsystem would prove nothing at all. Every
behavioural expectation here is therefore written down *outside* the code, in
``tests/fixtures/governed/golden/*.jsonl``: one JSON object per line carrying the
call, the expected payload and a ``proves`` sentence saying what would break if
the line failed. The Python in this module is a driver, not an oracle.

The same rule applies to the fixture corpus itself. ``term_glossary.csv`` records
a physical name for every logical name, ``ambiguity_pins.json`` records the pin
sheet, ``policies.json`` records the four policies field by field. Those files
were authored as a specification of the catalog, so the tests assert the code
against them rather than the other way round, and a cross-file disagreement
(the pin sheet saying one thing and ``dictionary.json`` another) fails here.

What is asserted, beyond the golden files
-----------------------------------------
* **The round trip lands on the governed correction.** For every identifier in
  the corpus, rendering its expanded phrase back into a physical name gives
  exactly what ``normalize`` would have produced. Where that is not the identity
  it is not arbitrary: it is the standard correcting an unapproved token, which
  is a stronger and more honest claim than excluding the names where the
  identity fails.
* **``normalize`` is idempotent**, over the whole corpus and under every named
  policy.
* **Nothing is ever shortened.** No policy produces fewer tokens than any other,
  ``truncated`` stays ``False``, an over-long name comes back over-long, and a
  word the catalog does not abbreviate is upper-cased rather than clipped.
* **The tokenizer's properties**, with Hypothesis: it never raises, never emits
  an empty token, keeps every letter and digit in order, and is stable under
  rejoining.
* **Tier 0 purity**, in a subprocess, because the pytest interpreter has already
  imported half the optional dependency surface by the time this module runs.

Nothing here expresses the governed-mode guarantee as an accuracy figure. "A
governed hit resolves from the dictionary under every policy" is an invariant
that is true by construction — a lookup table returns what is in the lookup
table — and it is tested as one, on the ``policy_contrast`` lines that carry the
same answer under all three policies. Attaching a percentage to it would dress a
tautology up as a measurement.

The fixture catalog is the fictional **Northwind Data Standards** (``NDS``).
Nothing in this file or the files it reads describes a real organisation's
naming standard.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional, Union

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from acronymkit.exceptions import ConfigurationError, LexiconError
from acronymkit.governed import (
    ComplianceReasonCode,
    ExpansionSource,
    GovernedDictionary,
    GovernedEntry,
    NamingPolicy,
    UnknownPolicy,
    Verdict,
    canonical_form_score,
    expand_identifier,
    expand_token,
    is_compliant,
    normalize,
    score_breakdown,
    split_identifier,
    to_physical_name,
)
from conftest import REPO_ROOT, SRC

# --------------------------------------------------------------------------
# The fixture corpus
# --------------------------------------------------------------------------
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "governed"
GOLDEN = FIXTURES / "golden"


def _read_json(name: str) -> Any:
    """Parse one fixture file.

    Args:
        name: File name inside ``tests/fixtures/governed``.

    Returns:
        The parsed document.
    """
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


_ALLOW_LIST = _read_json("allowlist.json")
_CLASS_WORDS = _read_json("class_words.json")["abbreviations"]
_CATALOG_DOCUMENT = _read_json("dictionary.json")
_OVERLAY_DOCUMENT = _read_json("custom_overlay.json")

#: The four named policies, field by field, as ``policies.json`` records them.
POLICY_SPECS: dict[str, dict[str, Any]] = _read_json("policies.json")["policies"]

#: The pin sheet, with the ``_meta`` block and every other underscore-prefixed
#: key dropped — the same convention the fixture file documents for itself.
PIN_SHEET: dict[str, Any] = {
    token: record
    for token, record in _read_json("ambiguity_pins.json").items()
    if not token.startswith("_")
}

#: Tokens deliberately held out of the catalog so passthrough has something to
#: be tested on. Passthrough is the *absence* of a row, so it cannot have one.
RESERVED_ABSENT: list[str] = _CATALOG_DOCUMENT["reserved_absent"]

with (FIXTURES / "term_glossary.csv").open(encoding="utf-8", newline="") as _handle:
    GLOSSARY: list[dict[str, str]] = list(csv.DictReader(_handle))

#: Logical name to glossary term id, which is what ``GovernedDictionary`` takes.
TERM_INDEX = {row["logical_name"]: row["term_id"] for row in GLOSSARY}

#: The synthetic identifier corpus, one UPPER_SNAKE name per line.
CORPUS: list[str] = [
    line.strip()
    for line in (FIXTURES / "corpus_sample.txt").read_text(encoding="utf-8").splitlines()
    if line.strip()
]


def _overlay_values(layer: dict[str, Any]) -> dict[str, Union[str, GovernedEntry]]:
    """Turn one JSON overlay layer into what a ``custom=`` argument accepts.

    An overlay value is either a bare long form or a whole entry. JSON cannot
    hold a :class:`~acronymkit.governed.models.GovernedEntry`, so an object value
    is constructed into one here — which is also the only place the distinction
    between the two accepted shapes is exercised end to end.

    Args:
        layer: One mapping out of ``custom_overlay.json``'s ``layers``.

    Returns:
        The layer with object values built into entries.
    """
    return {
        token: (GovernedEntry(**value) if isinstance(value, dict) else value)
        for token, value in layer.items()
    }


OVERLAY_LAYERS: dict[str, dict[str, Union[str, GovernedEntry]]] = {
    name: _overlay_values(layer) for name, layer in _OVERLAY_DOCUMENT["layers"].items()
}

#: The governed vocabulary the whole suite runs against, assembled from the five
#: fixture files exactly as a caller would assemble it from a real standard's
#: five files. Module-level rather than a fixture: it is immutable, it is shared
#: by the Hypothesis-driven tests, and a function-scoped fixture inside a
#: ``@given`` test is a health-check failure.
NDS = GovernedDictionary.from_json(
    FIXTURES / "dictionary.json",
    approved_abbreviations=_ALLOW_LIST["approved_abbreviations"],
    common_keywords=_ALLOW_LIST["common_keywords"],
    short_full_words=_ALLOW_LIST["short_full_words"],
    class_words=_CLASS_WORDS,
    term_index=TERM_INDEX,
)

#: The supported spelling of "no governed vocabulary": it knows nothing,
#: approves nothing and passes every token through.
EMPTY = GovernedDictionary()

#: The same catalog with every pin removed, so that a collision the catalog had
#: already ruled on falls through to the score instead. Only ``CTL`` and ``REG``
#: are genuinely unpinned in the fixture, which would leave the penalty table
#: exercised on two rows out of fifteen; stripping the pins puts every collision
#: set through the scored path without inventing a second corpus to do it with.
UNPINNED = GovernedDictionary(entry.model_copy(update={"pin": None}) for entry in NDS.entries)

#: Every named policy, for the invariants that must hold under all of them.
ALL_POLICIES = [
    NamingPolicy.governed_default(),
    NamingPolicy.frequency_baseline(),
    NamingPolicy.neural_optin(),
    NamingPolicy.strict_length(),
]


# --------------------------------------------------------------------------
# Golden-file driver
# --------------------------------------------------------------------------
#: Every golden file, in the order the acceptance criteria list them.
GOLDEN_FILES = [
    "expand_token.jsonl",
    "expand_identifier.jsonl",
    "to_physical_name.jsonl",
    "is_compliant.jsonl",
    "provenance.jsonl",
    "custom_precedence.jsonl",
    "policy_contrast.jsonl",
    "edge_cases.jsonl",
]


def _load_golden(name: str) -> list[dict[str, Any]]:
    """Read one golden file into its cases.

    Args:
        name: File name inside ``tests/fixtures/governed/golden``.

    Returns:
        One dict per line, in file order.

    Raises:
        AssertionError: If the file is missing or empty. An empty golden file
            would parametrise to zero tests and pass in silence, which is the
            one failure mode a fixture-driven suite cannot afford.
    """
    path = GOLDEN / name
    assert path.is_file(), f"missing golden file {path}"
    cases = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert cases, f"golden file {name} holds no cases"
    return cases


def _case_id(index: int, case: dict[str, Any]) -> str:
    """Build a readable pytest id naming the call the line makes."""
    spec = case["input"]
    return f"{index:02d}-{spec['verb']}-{spec.get('arg')!r}"


def _parametrize(name: str) -> Any:
    """Return the ``pytest.mark.parametrize`` decorator for one golden file."""
    cases = _load_golden(name)
    return pytest.mark.parametrize(
        "case",
        cases,
        ids=[_case_id(index, case) for index, case in enumerate(cases)],
    )


def _policy(spec: Union[None, str, dict[str, Any]]) -> Optional[NamingPolicy]:
    """Resolve a golden file's ``policy`` field.

    Args:
        spec: ``None`` for the verb's own default, the name of a named
            constructor, or a mapping of field overrides. The mapping form is
            what lets a line vary one flag — ``allow_override`` — without
            dragging in the other three changes a named preset would make.

    Returns:
        The policy, or ``None``.
    """
    if spec is None:
        return None
    if isinstance(spec, str):
        return getattr(NamingPolicy, spec)()
    return NamingPolicy(**spec)


def _custom(spec: dict[str, Any]) -> Optional[dict[str, Union[str, GovernedEntry]]]:
    """Resolve a golden file's call-scoped overlay.

    Args:
        spec: The line's ``input`` object. ``custom`` is an inline mapping;
            ``custom_layer`` names a layer from ``custom_overlay.json``.

    Returns:
        The overlay, or ``None`` when the line supplies neither.
    """
    if spec.get("custom_layer") is not None:
        return OVERLAY_LAYERS[spec["custom_layer"]]
    inline = spec.get("custom")
    return _overlay_values(inline) if inline is not None else None


def _dictionary(spec: dict[str, Any]) -> GovernedDictionary:
    """Resolve a golden file's vocabulary, with any layers already applied.

    Args:
        spec: The line's ``input`` object. ``dictionary`` selects the fixture
            catalog or the empty one; ``dictionary_layers`` names overlay layers
            to compose onto it, in order, later winning.

    Returns:
        The vocabulary to call the verb with.
    """
    catalog = EMPTY if spec.get("dictionary") == "empty" else NDS
    for layer in spec.get("dictionary_layers", ()):
        catalog = catalog.with_custom(OVERLAY_LAYERS[layer])
    return catalog


def _invoke(spec: dict[str, Any], policy: Optional[NamingPolicy]) -> dict[str, Any]:
    """Make the call a golden line describes and return its payload as a dict.

    Args:
        spec: The line's ``input`` object.
        policy: The already-resolved policy.

    Returns:
        The result's ``to_dict()``. ``normalize`` returns a bare string, so it is
        wrapped under ``normalized`` to keep one comparison shape for every file.

    Raises:
        AssertionError: If the line names a verb this driver does not know.
    """
    catalog = _dictionary(spec)
    custom = _custom(spec)
    verb = spec["verb"]
    argument = spec.get("arg")
    if verb == "expand_token":
        return expand_token(argument, catalog, policy, custom=custom).to_dict()
    if verb == "expand_identifier":
        return expand_identifier(argument, catalog, policy, custom=custom).to_dict()
    if verb == "to_physical_name":
        return to_physical_name(argument, catalog, policy, custom=custom).to_dict()
    if verb == "is_compliant":
        return is_compliant(argument, catalog, policy, custom=custom).to_dict()
    if verb == "normalize":
        return {"normalized": normalize(argument, catalog, policy, custom=custom)}
    raise AssertionError(f"golden file names an unknown verb {verb!r}")


def _assert_matches(actual: Any, expected: Any, path: str = "") -> None:
    """Assert that ``actual`` carries everything ``expected`` states.

    A golden line names the fields it is about and stays silent on the rest, so
    a mapping is matched key by key rather than whole. Sequences are matched
    element by element *and* on length, because a missing or extra token is
    exactly the kind of regression these files exist to catch.

    Args:
        actual: The payload the call produced.
        expected: The golden line's expectation, or part of it.
        path: Dotted location, for a failure message that names the field.
    """
    where = path or "<result>"
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{where}: expected an object, got {type(actual).__name__}"
        for key, value in expected.items():
            assert key in actual, f"{where}: no field {key!r} in {sorted(actual)}"
            _assert_matches(actual[key], value, f"{path}.{key}" if path else key)
    elif isinstance(expected, list):
        assert isinstance(actual, list), f"{where}: expected a list, got {type(actual).__name__}"
        assert len(actual) == len(expected), (
            f"{where}: expected {len(expected)} items, got {len(actual)}: {actual!r}"
        )
        for index, (item, wanted) in enumerate(zip(actual, expected)):
            _assert_matches(item, wanted, f"{where}[{index}]")
    else:
        assert actual == expected, f"{where}: expected {expected!r}, got {actual!r}"


def _check(case: dict[str, Any]) -> None:
    """Run one golden line and assert its expectation.

    A line that stated nothing would pass against any output at all, so both the
    expectation and the sentence explaining it are required to be non-empty. That
    is the one way a fixture-driven suite can go green while testing nothing.

    Args:
        case: The parsed line.
    """
    assert case.get("proves", "").strip(), "every golden line states what it proves"
    assert case.get("expected"), "every golden line states at least one expected field"
    _assert_matches(_invoke(case["input"], _policy(case["input"].get("policy"))), case["expected"])


# --------------------------------------------------------------------------
# The golden files
# --------------------------------------------------------------------------
@_parametrize("expand_token.jsonl")
def test_expand_token_golden(case: dict[str, Any]) -> None:
    """Single-token expansion: every resolution rule, and the empty input."""
    _check(case)


@_parametrize("expand_identifier.jsonl")
def test_expand_identifier_golden(case: dict[str, Any]) -> None:
    """Whole-identifier expansion: splitting, the class-word rule, provenance."""
    _check(case)


@_parametrize("to_physical_name.jsonl")
def test_to_physical_name_golden(case: dict[str, Any]) -> None:
    """The reverse direction, including the words that must not be shortened."""
    _check(case)


@_parametrize("is_compliant.jsonl")
def test_is_compliant_golden(case: dict[str, Any]) -> None:
    """Per-token verdicts, the whole-name findings, and the false-positive guard."""
    _check(case)


@_parametrize("provenance.jsonl")
def test_provenance_golden(case: dict[str, Any]) -> None:
    """Where each answer came from, what it beat, and how far the catalog backs it."""
    _check(case)


@_parametrize("custom_precedence.jsonl")
def test_custom_precedence_golden(case: dict[str, Any]) -> None:
    """The overlay contract: precedence, the demotion, layering and provenance."""
    _check(case)


@_parametrize("edge_cases.jsonl")
def test_edge_cases_golden(case: dict[str, Any]) -> None:
    """Blank, separator-only, digit-bearing and over-long input, plus the empty vocabulary."""
    _check(case)


@_parametrize("policy_contrast.jsonl")
def test_policy_contrast_golden(case: dict[str, Any]) -> None:
    """The same token under three policies, expectations recorded per policy.

    This is where the governed-mode guarantee is asserted, and it is asserted as
    an invariant: the lines for ``TXN`` and ``DT`` carry the identical payload
    under all three policies, because an unambiguous catalog row is not something
    a policy is allowed to have an opinion about. No figure is attached to that
    and none would mean anything if it were.
    """
    assert case.get("proves", "").strip(), "every golden line states what it proves"
    spec = case["input"]
    assert sorted(case["expected"]) == sorted(spec["policies"]), (
        "every policy the line names must carry an expectation, and no others"
    )
    for name in spec["policies"]:
        assert case["expected"][name], f"<{name}>: no expected field stated"
        _assert_matches(_invoke(spec, _policy(name)), case["expected"][name], f"<{name}>")


def test_every_golden_file_is_driven_by_a_test() -> None:
    """The eight files this suite promises to run are all present and non-empty.

    A golden file nobody loads is a specification nobody checks, and it fails
    silently: the test that should have read it simply parametrises to nothing.
    """
    on_disk = sorted(path.name for path in GOLDEN.glob("*.jsonl"))
    assert on_disk == sorted(GOLDEN_FILES)
    for name in GOLDEN_FILES:
        assert _load_golden(name)


# --------------------------------------------------------------------------
# The round trip
# --------------------------------------------------------------------------
@pytest.mark.parametrize("identifier", CORPUS)
def test_the_round_trip_lands_on_the_governed_correction(identifier: str) -> None:
    """Expanding then re-rendering an identifier gives what ``normalize`` gives.

    The identity form of this claim — ``x`` comes back as ``x`` — is false for
    any identifier carrying an unapproved token, and excluding those names would
    test the invariant only where it is easy. The sharper statement holds
    everywhere: where the trip is not the identity it is the governed
    correction, the same rewrite the verifier would have proposed.
    """
    phrase = expand_identifier(identifier, NDS).phrase
    assert to_physical_name(phrase, NDS).physical == normalize(identifier, NDS)


def test_the_corpus_exercises_both_halves_of_the_round_trip() -> None:
    """The corpus contains names the trip changes and names it does not.

    Without this the invariant above could pass on a corpus where every name is
    already its own normal form, which would make it a much weaker claim than it
    reads as.
    """
    unchanged = [name for name in CORPUS if normalize(name, NDS) == name]
    corrected = [name for name in CORPUS if normalize(name, NDS) != name]
    assert unchanged, "no corpus identifier is already its own normal form"
    assert corrected, "no corpus identifier is corrected, so the trip is never non-trivial"


@pytest.mark.parametrize("identifier", CORPUS)
def test_normalize_is_idempotent_under_every_policy(identifier: str) -> None:
    """``normalize(normalize(x)) == normalize(x)``, for every policy.

    It holds by construction — a rewrite is proposed only when its target is
    approved, so the second pass has nothing to propose — but "by construction"
    is a claim about the code as written, and this is what notices when the code
    stops being written that way.
    """
    for policy in ALL_POLICIES:
        once = normalize(identifier, NDS, policy)
        assert normalize(once, NDS, policy) == once


def test_the_reverse_index_resolves_a_contested_long_form_by_the_documented_rule() -> None:
    """Eight long forms are claimed by two tokens each, and the approved one wins.

    The pairs and the winners are written down in the fixture README's tie-break
    table. ``Number`` is the row that needs the third rule: ``NBR`` and ``NUM``
    are the same length, so only the lexicographic fallback separates them, and
    it is the first row to break if the rule order ever changes.
    """
    contested = {
        "Account": "ACCT",
        "Amount": "AM",
        "Customer": "CUST",
        "Date": "DT",
        "Effective": "EFF",
        "Payment": "PYMT",
        "Transaction": "TXN",
        "Number": "NBR",
    }
    for long_form, token in contested.items():
        entry = NDS.abbreviate(long_form)
        assert entry is not None, f"{long_form!r} is claimed by no token"
        assert entry.token == token, f"{long_form!r} reversed to {entry.token}, not {token}"


def test_expansion_and_abbreviation_are_not_inverses_and_say_so() -> None:
    """A non-canonical candidate reverses to its token; expanding gives the pin.

    ``Line`` is one of ``LN``'s candidates and ``Loan`` is the one it pins, so
    the trip out and back does not return ``Line``. That is a property of
    inverting a many-to-one map, not a defect, and the honest response is to
    assert the asymmetry rather than to quietly avoid it.
    """
    entry = NDS.abbreviate("Line")
    assert entry is not None and entry.token == "LN"
    assert expand_token("LN", NDS).long == "Loan"
    assert expand_token("LN", NDS).beat == ("Line", "Length")


# --------------------------------------------------------------------------
# Length: a flag, never a truncation
# --------------------------------------------------------------------------
@pytest.mark.parametrize("identifier", CORPUS)
def test_no_policy_produces_a_shorter_token_list_than_any_other(identifier: str) -> None:
    """Every policy renders the same tokens; none of them drops one.

    ``enforce_name_length`` may only ever cause a finding. The way to test "no
    code path truncates" is not to look for a truncation but to show that
    turning the setting on changes nothing about the name at all — same tokens,
    same string, ``truncated`` still ``False``.
    """
    phrase = expand_identifier(identifier, NDS).phrase
    baseline = to_physical_name(phrase, NDS, NamingPolicy.governed_default())
    for policy in ALL_POLICIES:
        rendered = to_physical_name(phrase, NDS, policy)
        assert rendered.truncated is False
        assert len(rendered.tokens) == len(baseline.tokens)
        assert rendered.physical == baseline.physical
        assert normalize(identifier, NDS, policy) == normalize(identifier, NDS)


@pytest.mark.parametrize("identifier", CORPUS)
def test_an_unabbreviated_word_is_upper_cased_and_never_clipped(identifier: str) -> None:
    """A word the catalog does not abbreviate comes back whole, in capitals.

    Clipping it would be inventing an abbreviation, which is the one thing this
    package will not do — and the place a length limit would otherwise be
    tempting.
    """
    phrase = expand_identifier(identifier, NDS).phrase
    for token in to_physical_name(phrase, NDS, NamingPolicy.strict_length()).tokens:
        if token.source is ExpansionSource.PASSTHROUGH:
            assert token.abbrev == token.word.upper()


def test_an_over_long_name_is_flagged_and_returned_whole() -> None:
    """The longest corpus name is reported over the limit and comes back intact."""
    policy = NamingPolicy.strict_length()
    longest = max(CORPUS, key=len)
    result = is_compliant(longest, NDS, policy)
    assert result.name == longest
    assert ComplianceReasonCode.EXCEEDS_MAX_LENGTH in {reason.code for reason in result.failures}

    rendered = to_physical_name(expand_identifier(longest, NDS).phrase, NDS, policy)
    assert rendered.truncated is False
    assert len(rendered.physical) > policy.max_name_length, (
        "the rendered name came back inside the limit, which means something shortened it"
    )


# --------------------------------------------------------------------------
# The glossary, the pin sheet and the policy sheet
# --------------------------------------------------------------------------
@pytest.mark.parametrize("row", GLOSSARY, ids=[row["logical_name"] for row in GLOSSARY])
def test_every_glossary_row_renders_to_its_recorded_physical_name(row: dict[str, str]) -> None:
    """``term_glossary.csv`` is an expectation written before the code ran.

    Each row records a logical name, the physical name a governed rendering must
    produce for it, the term id and the class word the name has to end in. The
    file was authored as a specification of the catalog, so it is the authority
    here and the code is what is under test.
    """
    result = to_physical_name(row["logical_name"], NDS)
    assert result.physical == row["physical_name"]
    assert result.term_id == row["term_id"]
    assert result.truncated is False
    assert result.tokens[-1].abbrev == row["class_word"]


@pytest.mark.parametrize("token", sorted(PIN_SHEET), ids=sorted(PIN_SHEET))
def test_the_pin_sheet_and_the_catalog_record_the_same_decision(token: str) -> None:
    """``ambiguity_pins.json`` and ``dictionary.json`` must not drift apart.

    Two files record the same collision sets and the same pins. Neither is
    derived from the other, so a disagreement between them is a real defect in
    the corpus — and a ``null`` pin in the sheet must correspond to an entry with
    no pin, which is the row that falls through to the score.
    """
    record = PIN_SHEET[token]
    entry = NDS.lookup(token)
    assert entry is not None, f"the pin sheet names {token}, which the catalog does not carry"
    assert list(entry.candidates) == record["candidates"]
    assert entry.pin == record["_pin"]


@pytest.mark.parametrize("name", sorted(POLICY_SPECS), ids=sorted(POLICY_SPECS))
def test_each_named_policy_still_produces_the_recorded_fields(name: str) -> None:
    """``policies.json`` pins all nine fields of each named constructor.

    A preset is auditable only if "this pipeline runs under ``governed_default``"
    means a fixed set of values, so the values are written down outside the code
    and compared whole rather than field by field.
    """
    assert getattr(NamingPolicy, name)().model_dump(mode="json") == POLICY_SPECS[name]


@pytest.mark.parametrize("token", RESERVED_ABSENT)
def test_a_held_out_token_is_reported_unknown_rather_than_approximated(token: str) -> None:
    """The eight reserved tokens have no row, and must come back saying so.

    This is the design thesis in its smallest form: the library is willing to
    say it does not know. An unknown reported as unknown is recoverable, because
    a pipeline can filter on ``is_known`` and route the miss to whoever owns the
    catalog; an unknown quietly approximated is not.
    """
    result = expand_token(token, NDS)
    assert result.is_known is False
    assert result.source is ExpansionSource.PASSTHROUGH
    assert result.confidence == 0.0
    assert result.entry_id is None
    assert result.beat == ()


# --------------------------------------------------------------------------
# The penalty table, on every collision set in the corpus
# --------------------------------------------------------------------------
#: What ``canonical_form_score`` selects for each collision set, worked out from
#: the published penalty table rather than from the code: +100 for a US state
#: against a 2-letter token, +50 for a gerund, +40 for an ``-ly`` word, +30 for
#: an unexempt ``-ed``, +20 for an unexempt ``-s``, +10 for a phrase and +1 per
#: character, with ties broken lexicographically.
#:
#: This reproduces the "canonical_form_score takes" column of the fixture
#: README's disagreement table, with one correction. That table says the score
#: takes ``Secured`` for ``SEC``; it does not. ``Secured`` is exempt from the
#: past-tense penalty and ``Section`` trips nothing, so both cost 7 and the
#: lexicographic rule separates them - ``Sect`` sorts before ``Secu``, so the
#: score takes ``Section``. Nothing in the library's behaviour turns on it,
#: because ``SEC`` is pinned to ``Security`` and the score is never consulted for
#: it, but the README and the entry's own note both say otherwise.
SCORER_CHOICE = {
    "ID": "Identity",
    "SRC": "Source",
    "PROC": "Process",
    "MO": "Month",
    "REC": "Record",
    "CHG": "Change",
    "SEC": "Section",
    "ACT": "Action",
    "ORIG": "Original",
    "DEP": "Deposit",
    "PROD": "Product",
    "APP": "Approval",
    "LN": "Line",
    "CTL": "Control",
    "REG": "Regional",
}


@pytest.mark.parametrize("token", sorted(SCORER_CHOICE), ids=sorted(SCORER_CHOICE))
def test_an_unpinned_collision_resolves_to_what_the_penalty_table_selects(token: str) -> None:
    """With the pins stripped, every collision falls to the score, and it is total.

    Six of these fifteen sets are decided only by the lexicographic tie-break -
    ``CHG``, ``SEC``, ``ACT``, ``LN`` and ``REG`` all contain candidates that
    cost exactly the same - so this is where a change to the tie-break shows up.
    A sort that fell back on input order instead would make a resolution depend
    on how the catalog file happened to be sorted, which is the failure the rule
    exists to prevent.
    """
    result = expand_token(token, UNPINNED)
    assert result.source is ExpansionSource.SCORED
    assert result.long == SCORER_CHOICE[token]


@pytest.mark.parametrize("token", sorted(SCORER_CHOICE), ids=sorted(SCORER_CHOICE))
def test_the_pin_is_what_the_catalog_says_whatever_the_score_thinks(token: str) -> None:
    """A pinned collision reports the pin, and seven of them differ from the score.

    This is the whole thesis in one assertion. On these rows the governed answer
    is not the one a scorer would reach and not the one a most-frequent rule
    would reach; it is the one somebody wrote down. A resolver that quietly
    preferred either of the other two would be overruling a decision a data
    governance function already signed off.
    """
    pin = PIN_SHEET[token]["_pin"]
    result = expand_token(token, NDS)
    if pin is None:
        assert result.source is ExpansionSource.SCORED
        assert result.long == SCORER_CHOICE[token]
    else:
        assert result.source is ExpansionSource.PINNED
        assert result.long == pin


def test_the_pin_disagrees_with_both_other_mechanisms_on_seven_rows() -> None:
    """The corpus is built so the three mechanisms visibly part company.

    If every pin happened to agree with the score and with the first declared
    candidate, the tests above would pass while proving nothing about
    precedence. Counted from the fixture files rather than asserted as a
    remembered figure.
    """
    disagreements = [
        token
        for token, record in PIN_SHEET.items()
        if record["_pin"] is not None
        and record["_pin"] != SCORER_CHOICE[token]
        and record["_pin"] != record["candidates"][0]
    ]
    assert sorted(disagreements) == ["ACT", "APP", "CHG", "ID", "LN", "ORIG", "SEC"]


def test_the_state_penalty_fires_on_the_pairing_and_not_on_the_word() -> None:
    """``Idaho`` is only a bad answer because the token is two letters long.

    A longer token that expands to a state name is a geography column doing its
    job, so the rule is keyed on the pairing. Without it ``Idaho`` costs five and
    beats ``Identifier`` on length alone, and a column named ``ID`` expands to a
    state.
    """
    assert score_breakdown("Idaho", "ID")["us_state"] == 100.0
    assert score_breakdown("Idaho", "ST_CD")["us_state"] == 0.0
    assert canonical_form_score("Idaho", "ID") > canonical_form_score("Identifier", "ID")
    assert canonical_form_score("Idaho", "ST_CD") < canonical_form_score("Identifier", "ST_CD")


def test_the_two_exemption_sets_keep_uninflected_nouns_out_of_trouble() -> None:
    """``Address`` is not a plural and ``Secured`` is not a past tense.

    Without the exemptions both are punished for their spelling, and ``Address``
    and ``Status`` are two of the most common class words there are.
    """
    assert score_breakdown("Address", "ADDR")["plural"] == 0.0
    assert score_breakdown("Accounts", "ACCT")["plural"] == 20.0
    assert score_breakdown("Secured", "SEC")["past_tense"] == 0.0
    assert score_breakdown("Charged", "CHG")["past_tense"] == 30.0


# --------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------
def test_reject_raises_rather_than_answering_for_an_unknown_token() -> None:
    """``UnknownPolicy.REJECT`` stops the call and names the missing token."""
    policy = NamingPolicy(unknown=UnknownPolicy.REJECT)
    with pytest.raises(LexiconError) as caught:
        expand_token("KYC", NDS, policy)
    assert "KYC" in str(caught.value)
    assert expand_token("TXN", NDS, policy).long == "Transaction"


@pytest.mark.parametrize(
    ("verb", "argument"),
    [
        (expand_token, "TXN"),
        (expand_identifier, "TXN_ID"),
        (to_physical_name, "Transaction Identifier"),
        (is_compliant, "TXN_ID"),
        (normalize, "TXN_ID"),
    ],
    ids=["expand_token", "expand_identifier", "to_physical_name", "is_compliant", "normalize"],
)
def test_a_governed_verb_refuses_a_missing_vocabulary(verb: Any, argument: str) -> None:
    """``dictionary=None`` is a contradiction and is refused by name.

    The coherent reading of "no dictionary" is an empty one, which passes
    everything through, so the refusal points at it rather than guessing which
    was meant.
    """
    with pytest.raises(ConfigurationError):
        verb(argument, None)


# --------------------------------------------------------------------------
# Tokenizer properties
# --------------------------------------------------------------------------
#: A small alphabet packed with the characters that drive the boundary rules:
#: the five named separators, punctuation that is not one of them, digits, both
#: cases, an accented letter and a caseless one. Every character here answers
#: ``isalpha`` and ``isdigit`` unambiguously, which is what lets
#: :func:`test_split_identifier_retains_exactly_the_letters_and_digits` assert
#: the documented retention rule as an equation rather than an inclusion.
_IDENTIFIER_CHARS = "aZ9_-./ #$(\",;:@%&*+=[]|~^'\u00e9\u4e2d"

#: Two of the 163 code points that answer ``isupper()`` True and ``isalpha()``
#: False: CIRCLED LATIN CAPITAL LETTER A and ROMAN NUMERAL ONE. Written as
#: escapes so this file stays pure ASCII, as the rest of the suite does.
_CIRCLED_CAPITAL_A = "\u24b6"
_ROMAN_NUMERAL_ONE = "\u2160"

#: Realistic input: the two synthetic alphabets and the corpus itself.
IDENTIFIER_STRATEGY = st.one_of(
    st.text(alphabet=_IDENTIFIER_CHARS, max_size=30),
    st.sampled_from(CORPUS),
)

#: Anything at all, including the Unicode oddities the restricted alphabet
#: leaves out. Used for the properties that must hold for every string a schema
#: export could conceivably contain.
ANY_TEXT_STRATEGY = st.one_of(st.text(max_size=60), IDENTIFIER_STRATEGY)


def _is_subsequence(needle: str, haystack: str) -> bool:
    """Whether ``needle``'s characters appear in ``haystack``, in order.

    Args:
        needle: The characters that must be present.
        haystack: The string to find them in.

    Returns:
        ``True`` when every character of ``needle`` can be matched in order.
    """
    remaining = iter(haystack)
    return all(character in remaining for character in needle)


@settings(max_examples=300, deadline=None)
@given(ANY_TEXT_STRATEGY)
def test_split_identifier_never_raises_and_never_emits_an_empty_token(text: str) -> None:
    """A blank cell in a schema export is normal input, not an error.

    An empty token would also be poison downstream: it looks up to nothing,
    Title Cases to nothing, and would put a stray separator in a rendered name.
    """
    tokens = split_identifier(text)
    assert isinstance(tokens, tuple)
    assert all(tokens), f"{text!r} produced an empty token: {tokens!r}"


@settings(max_examples=300, deadline=None)
@given(ANY_TEXT_STRATEGY)
def test_split_identifier_drops_no_letter_or_digit_and_invents_nothing(text: str) -> None:
    """For any string at all: nothing alphanumeric is lost, nothing is added.

    This is the half of the retention rule that has to hold universally. A
    dropped letter destroys a token outright — the catalog is asked about a word
    that was cut in half, and no governed vocabulary downstream can recover it —
    and an invented character does the same thing from the other direction.
    Stated as two subsequence checks rather than one equation because the
    "nothing extra is kept" half has a known exception; see
    :func:`test_a_cased_non_letter_should_separate_like_any_other_symbol`.
    """
    retained = "".join(split_identifier(text))
    assert _is_subsequence(retained, text), "a token holds something the input did not"
    alphanumeric = "".join(
        character for character in text if character.isalpha() or character.isdigit()
    )
    assert _is_subsequence(alphanumeric, retained), "a letter or digit was dropped"


@settings(max_examples=300, deadline=None)
@given(IDENTIFIER_STRATEGY)
def test_split_identifier_retains_exactly_the_letters_and_digits(text: str) -> None:
    """Over realistic input, the retention rule holds as an equation.

    The splitter is documented as placing boundaries and nothing else: no case
    folding, no normalisation, no accent stripping, nothing dropped, and nothing
    kept that a catalog entry could not contain. Every character in this
    strategy's alphabet — the five named separators, a dozen other punctuation
    marks, digits, both cases, an accent and a caseless letter — has an
    unambiguous answer to "is this a letter or a digit", so the promise can be
    asserted whole here.
    """
    kept = "".join(character for character in text if character.isalpha() or character.isdigit())
    assert "".join(split_identifier(text)) == kept


@pytest.mark.xfail(
    strict=True,
    reason=(
        "_classify tests isupper()/islower() before isalpha(), and 163 code points answer "
        "the first pair True and isalpha() False - U+24B6 CIRCLED LATIN CAPITAL LETTER A, "
        "U+2160 ROMAN NUMERAL ONE and the rest. Those are classified as cased letters and "
        "survive inside a token, against the module's own rule that anything which is "
        "neither a letter nor a digit separates."
    ),
)
def test_a_cased_non_letter_should_separate_like_any_other_symbol() -> None:
    """A symbol glued to a token turns a resolvable name into an unknown.

    ``TXN#ID`` splits to ``('TXN', 'ID')`` and resolves; the same name written
    with a circled capital A splits to ``('TXN<U+24B6>', 'ID')`` and the first
    token matches no catalog row. That is exactly the failure the wide separator
    set exists to prevent, so it is recorded as a strict expected failure rather
    than left out: fixing the classifier turns this test green, which fails the
    suite until the marker comes off.
    """
    assert split_identifier(f"TXN{_CIRCLED_CAPITAL_A}_ID") == ("TXN", "ID")
    assert split_identifier(f"TXN{_ROMAN_NUMERAL_ONE}_ID") == ("TXN", "ID")


@settings(max_examples=300, deadline=None)
@given(ANY_TEXT_STRATEGY)
def test_split_identifier_is_stable_under_rejoining(text: str) -> None:
    """Splitting, joining with ``_`` and splitting again is a fixed point.

    Every verb here rebuilds a name from its tokens, so a splitter that produced
    a different answer on its own output would make ``normalize`` non-idempotent
    and would make a round trip drift a token at a time.
    """
    tokens = split_identifier(text)
    assert split_identifier("_".join(tokens)) == tokens


@settings(max_examples=200, deadline=None)
@given(ANY_TEXT_STRATEGY)
def test_split_identifier_is_deterministic_and_returns_substrings(text: str) -> None:
    """Two runs agree, and every token appears verbatim in the input."""
    tokens = split_identifier(text)
    assert split_identifier(text) == tokens
    for token in tokens:
        assert token in text


@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("TXN_APPLNT_DOB_DT", ("TXN", "APPLNT", "DOB", "DT")),
        ("TXN__APPLNT", ("TXN", "APPLNT")),
        ("_TXN_", ("TXN",)),
        ("creditBureauVendorCode", ("credit", "Bureau", "Vendor", "Code")),
        ("ETLTimestamp", ("ETL", "Timestamp")),
        ("MDMHubID", ("MDM", "Hub", "ID")),
        ("address2line1", ("address", "2", "line", "1")),
        ("7Code", ("7", "Code")),
        ("ISO8601Date", ("ISO", "8601", "Date")),
        ("1MM", ("1", "MM")),
        ("nds.risk-model / SCORE", ("nds", "risk", "model", "SCORE")),
        ("", ()),
        ("   ", ()),
        ("___", ()),
    ],
)
def test_split_identifier_follows_the_stated_rules(
    identifier: str, expected: tuple[str, ...]
) -> None:
    """The five splitting rules, one case each, as the contract writes them.

    ``1MM`` splits here on purpose: nothing in the string says it should not, it
    has exactly the shape of ``7Code``, and the repair belongs to the second,
    dictionary-aware pass rather than to a splitter that would then depend on
    somebody's vocabulary.
    """
    assert split_identifier(identifier) == expected


def test_split_identifier_accepts_none() -> None:
    """``None`` yields no tokens rather than a ``TypeError``."""
    assert split_identifier(None) == ()


# --------------------------------------------------------------------------
# Tier 0 purity
# --------------------------------------------------------------------------
#: Distributions the governed subsystem must never pull in. Same list the
#: packaging suite uses; a base install stays stdlib plus pydantic.
FORBIDDEN_AT_TIER_ZERO = ["click", "spacy", "nltk", "onnxruntime", "transformers", "numpy"]

_PURITY_SCRIPT = """
import json
import sys

sys.path.insert(0, {src!r})

from acronymkit.governed import (
    GovernedDictionary,
    NamingPolicy,
    expand_identifier,
    expand_token,
    is_compliant,
    normalize,
    to_physical_name,
)

fixtures = {fixtures!r}

with open(fixtures + "/allowlist.json", encoding="utf-8") as handle:
    allow = json.load(handle)
with open(fixtures + "/class_words.json", encoding="utf-8") as handle:
    class_words = json.load(handle)["abbreviations"]

catalog = GovernedDictionary.from_json(
    fixtures + "/dictionary.json",
    approved_abbreviations=allow["approved_abbreviations"],
    common_keywords=allow["common_keywords"],
    short_full_words=allow["short_full_words"],
    class_words=class_words,
    term_index={{"Transaction Identifier": "TRM-400009"}},
)

for policy in (
    NamingPolicy.governed_default(),
    NamingPolicy.frequency_baseline(),
    NamingPolicy.neural_optin(),
    NamingPolicy.strict_length(),
):
    expand_token("ID", catalog, policy)
    expand_identifier("txnApplntId", catalog, policy, custom={{"KYC": "Know Your Customer"}})
    to_physical_name("Transaction Identifier", catalog, policy)
    is_compliant("CUSTMR_ACCNT_NUM", catalog, policy)
    normalize("custmrAccntNum", catalog, policy)

forbidden = {forbidden!r}
print(json.dumps(sorted(name for name in forbidden if name in sys.modules)))
"""


def test_the_governed_api_pulls_in_no_optional_dependency(tmp_path: Path) -> None:
    """Loading a catalog and running all five verbs stays Tier 0.

    Run out of process on purpose. By the time this module executes, the pytest
    interpreter has imported ``click`` for the CLI tests and probed for NLTK, so
    ``sys.modules`` in here would prove nothing either way.
    """
    script = _PURITY_SCRIPT.format(
        src=str(SRC),
        fixtures=FIXTURES.as_posix(),
        forbidden=FORBIDDEN_AT_TIER_ZERO,
    )
    path = tmp_path / "governed_purity.py"
    path.write_text(script, encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    leaked = json.loads(completed.stdout.strip().splitlines()[-1])
    assert leaked == [], f"the governed API imported {leaked}"


# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------
@pytest.mark.parametrize("identifier", CORPUS[:10])
def test_two_runs_produce_byte_identical_audit_records(identifier: str) -> None:
    """Nothing here reads a clock, a random source or a set's iteration order.

    An audit trail that differed between runs would be unusable as evidence, and
    the failure mode it guards against is quiet: a resolution that depends on
    set ordering agrees with itself for a whole test session and disagrees
    across processes.
    """
    assert (
        expand_identifier(identifier, NDS).to_json() == expand_identifier(identifier, NDS).to_json()
    )
    phrase = expand_identifier(identifier, NDS).phrase
    assert to_physical_name(phrase, NDS).to_json() == to_physical_name(phrase, NDS).to_json()
    assert is_compliant(identifier, NDS).to_json() == is_compliant(identifier, NDS).to_json()


def test_a_compliance_result_reports_a_finding_for_every_lettered_token() -> None:
    """Every token that could be an abbreviation is judged, and none is skipped.

    Findings are per token, so a name with six tokens and one problem has to
    produce six findings and not one. Tokens holding no letters — the ordinals
    of ``ADDR_LINE_1_TXT`` — are the documented exception: no reason code
    describes an ordinal honestly, so none is invented for it.
    """
    name = "CUST_ACCT_ADDR_LINE_1_TXT"
    result = is_compliant(name, NDS)
    lettered = [token for token in split_identifier(name) if any(c.isalpha() for c in token)]
    per_token = [reason for reason in result.reasons if reason.token is not None]
    assert [reason.token for reason in per_token] == lettered
    assert all(reason.verdict is Verdict.PASS for reason in per_token)
