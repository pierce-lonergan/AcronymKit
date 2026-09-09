"""The hot-path record builders, and the instrument that proved they are free.

``expand_identifier`` spends most of its time constructing provenance, and most
of *that* on two things a frozen dataclass does per record that this package
does not need done: the generated ``__init__`` writing nine fields through
``object.__setattr__``, and ``__post_init__`` re-normalising two of them that
were already normal. :func:`~acronymkit.governed.models._new_token_expansion`
and :func:`~acronymkit.governed.models._new_identifier_expansion` skip both by
writing the fields straight into a fresh instance.

That is a behaviour change to shipped governance code, so what this file pins is
not that it is faster. It is:

* **that the two routes produce the same record** -- same values, same *types*,
  on a corpus that exercises every field, including the two the fast route no
  longer normalises;
* **that the routes are genuinely different code**, demonstrated by the one
  input on which they disagree -- because two branches that cannot be told apart
  are not a switch, and the identity gate over them would be measuring nothing;
* **that the public constructors are unchanged**: ``TokenExpansion(...)`` still
  refuses a confidence outside ``[0, 1]`` and still turns a list into a tuple,
  with the switch on;
* **that the shipped call sites never hand the builder something it would keep
  wrong** -- every field of every record from a real expansion has the type the
  validating route would have produced;
* and **that the runner's new instruments can fail**: the replay's construction
  count, the route parity check, the exact field-write counter and the identity
  gate's positive control.

Nothing here times anything.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

import pytest

from acronymkit.governed import (
    GovernedDictionary,
    GovernedEntry,
    expand_identifier,
    expand_token,
)
from acronymkit.governed import models as models_module
from acronymkit.governed.enums import EntryKind, ExpansionSource
from acronymkit.governed.models import (
    GovernedValidationError,
    IdentifierExpansion,
    TokenExpansion,
    _new_identifier_expansion,
    _new_token_expansion,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "bench" / "run_governed_perf.py"


#: A vocabulary that makes every field of a ``TokenExpansion`` non-trivial: an
#: entry with an ``entry_id``, one that carries its own class word, one that
#: does not, one with candidates so ``beat`` is non-empty, and a digit-leading
#: token so the rejoin fires.
CATALOG_ROWS = (
    GovernedEntry(
        token="TXN",
        canonical="Transaction",
        candidates=["Transaction", "Transmission"],
        kind=EntryKind.APPROVED_ABBREV,
        entry_id="NDS-TXN",
        source=ExpansionSource.GOVERNED,
        confidence=0.9,
    ),
    GovernedEntry(
        token="DT",
        canonical="Date",
        class_word="Date",
        kind=EntryKind.APPROVED_ABBREV,
        entry_id="NDS-DT",
        source=ExpansionSource.GOVERNED,
    ),
    GovernedEntry(
        token="ID",
        canonical="Identifier",
        kind=EntryKind.APPROVED_ABBREV,
        entry_id="NDS-ID",
        source=ExpansionSource.GOVERNED,
    ),
    GovernedEntry(
        token="1MM",
        canonical="One Million",
        kind=EntryKind.APPROVED_ABBREV,
        entry_id="NDS-1MM",
        source=ExpansionSource.GOVERNED,
    ),
)

#: The same awkward shapes the perf runner's own test file names, plus the
#: repeat that makes the expansion memo fire and the unknown token that makes
#: the passthrough branch fire. A record type is only pinned on a corpus that
#: reaches every branch that builds one.
CORPUS = (
    "TXN_APPLNT_ID",
    "TXN_APPLNT_ID",
    "txn_dt",
    "ADDR_LINE_1",
    "AMT_1MM",
    "E_9_1_1",
    "db.schema.TXN_ID",
    "PAY€AMT",
    "TRÄGER_ID",
    "___",
    "",
    "   ",
    "KYC_UNKNOWN_TOKEN",
)

#: The type every field of a record is allowed to hold, checked per field rather
#: than pooled, so a failure names the field.
TOKEN_FIELD_TYPES: dict[str, tuple[type, ...]] = {
    "raw": (str,),
    "long": (str,),
    "is_known": (bool,),
    "source": (ExpansionSource,),
    "entry_id": (str, type(None)),
    "confidence": (float,),
    "class_word": (str, type(None)),
    "beat": (tuple,),
    "kind": (EntryKind, type(None)),
}

IDENTIFIER_FIELD_TYPES: dict[str, tuple[type, ...]] = {
    "identifier": (str,),
    "phrase": (str,),
    "tokens": (tuple,),
    "class_word": (str, type(None)),
    "is_fully_known": (bool,),
    "unaccounted": (tuple,),
}


def catalog() -> GovernedDictionary:
    """A populated vocabulary that has answered nothing."""
    return GovernedDictionary(CATALOG_ROWS, class_words={"ID": "Identifier"})


def empty_catalog() -> GovernedDictionary:
    """The empty vocabulary every published governed figure is taken with."""
    return GovernedDictionary({})


CATALOGS = {"populated": catalog, "empty": empty_catalog}


def _expand_all(factory: Any) -> list[IdentifierExpansion]:
    """Every name in :data:`CORPUS` through one fresh vocabulary."""
    vocabulary = factory()
    return [expand_identifier(name, vocabulary) for name in CORPUS]


def _forced(flag: bool, factory: Any) -> list[IdentifierExpansion]:
    """:func:`_expand_all` with the construction switch held at ``flag``."""
    saved = models_module._FAST_CONSTRUCTION
    try:
        models_module._FAST_CONSTRUCTION = flag
        return _expand_all(factory)
    finally:
        models_module._FAST_CONSTRUCTION = saved


# ---------------------------------------------------------------------------
# the two routes produce the same record
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", sorted(CATALOGS))
def test_the_two_routes_agree_on_every_record_by_repr(label: str) -> None:
    """``repr`` and not ``==``: equality would call a list beat equal to a tuple."""
    off = _forced(False, CATALOGS[label])
    on = _forced(True, CATALOGS[label])
    assert [repr(record) for record in on] == [repr(record) for record in off]


@pytest.mark.parametrize("label", sorted(CATALOGS))
def test_the_two_routes_agree_on_every_record_on_the_wire(label: str) -> None:
    """The JSON contract, character for character, including key order."""
    off = _forced(False, CATALOGS[label])
    on = _forced(True, CATALOGS[label])
    assert [record.to_json() for record in on] == [record.to_json() for record in off]


@pytest.mark.parametrize("label", sorted(CATALOGS))
def test_the_fast_route_fills_every_declared_field(label: str) -> None:
    """A field left unset would be an ``AttributeError`` on a reader, not a value."""
    token_fields = {field.name for field in dataclasses.fields(TokenExpansion)}
    identifier_fields = {field.name for field in dataclasses.fields(IdentifierExpansion)}
    for record in _forced(True, CATALOGS[label]):
        assert set(record.__dict__) == identifier_fields
        for token in record.tokens:
            assert set(token.__dict__) == token_fields


@pytest.mark.parametrize("label", sorted(CATALOGS))
def test_every_field_of_every_shipped_record_has_the_validated_type(label: str) -> None:
    """The caller's obligation, checked against what the call sites actually pass.

    The fast builder writes what it is handed. What makes that safe is that the
    three sites in ``expansion`` hand it a tuple where a tuple is declared and a
    bounded float where a float is declared. This is that premise, measured on
    every record the corpus produces rather than read off the source.
    """
    for record in _forced(True, CATALOGS[label]):
        for name, allowed in IDENTIFIER_FIELD_TYPES.items():
            assert isinstance(getattr(record, name), allowed), name
        for token in record.tokens:
            for name, allowed in TOKEN_FIELD_TYPES.items():
                assert isinstance(getattr(token, name), allowed), name
            assert 0.0 <= token.confidence <= 1.0


@pytest.mark.parametrize("label", sorted(CATALOGS))
def test_expand_token_agrees_too_including_the_empty_expansion(label: str) -> None:
    """The one builder call site ``expand_identifier`` never reaches.

    ``_empty_expansion`` answers a blank token, and only ``expand_token`` can
    reach it: a blank identifier tokenises to nothing and yields an
    ``IdentifierExpansion`` with no tokens rather than an empty
    ``TokenExpansion``. The identity gate in ``bench/run_governed_perf.py``
    drives ``expand_identifier`` over whole corpora and therefore does not cover
    this branch at all, which is why it is covered here rather than assumed to
    be.
    """
    tokens = ("TXN", "txn", "", "   ", None, "KYC", "1MM", "ID", "€")
    saved = models_module._FAST_CONSTRUCTION
    try:
        models_module._FAST_CONSTRUCTION = False
        vocabulary = CATALOGS[label]()
        off = [repr(expand_token(token, vocabulary)) for token in tokens]
        off_wire = [expand_token(token, vocabulary).to_json() for token in tokens]
        models_module._FAST_CONSTRUCTION = True
        vocabulary = CATALOGS[label]()
        on = [repr(expand_token(token, vocabulary)) for token in tokens]
        on_wire = [expand_token(token, vocabulary).to_json() for token in tokens]
    finally:
        models_module._FAST_CONSTRUCTION = saved
    assert on == off
    assert on_wire == off_wire
    assert "long=''" in on[2]  # the empty expansion did run


def test_a_fast_built_record_still_hashes_copies_and_dumps() -> None:
    """Everything ``_FrozenModel`` offers works on a record no ``__init__`` built."""
    record = _forced(True, catalog)[0]
    assert hash(record.tokens[0]) == hash(_forced(False, catalog)[0].tokens[0])
    assert record.tokens[0] == _forced(False, catalog)[0].tokens[0]
    assert record.to_dict() == _forced(False, catalog)[0].to_dict()
    assert record.model_dump() == _forced(False, catalog)[0].model_dump()
    assert record.model_copy(update={"phrase": "x"}).phrase == "x"
    assert record.unknown_tokens == _forced(False, catalog)[0].unknown_tokens
    assert str(record) == str(_forced(False, catalog)[0])


# ---------------------------------------------------------------------------
# the routes are genuinely different code
# ---------------------------------------------------------------------------


def test_the_switch_selects_two_routes_that_can_be_told_apart() -> None:
    """The one input the two routes disagree on, which is what makes it a switch.

    A ``beat`` handed in as a list is normalised to a tuple by ``__post_init__``
    and kept as a list by the builder. No shipped call site passes one -- the
    test above measures that -- so this is not a defect; it is the demonstration
    that forcing the switch off reaches different code, without which the
    identity gate would be comparing a route with itself.
    """
    saved = models_module._FAST_CONSTRUCTION
    try:
        models_module._FAST_CONSTRUCTION = False
        slow = _new_token_expansion(
            "TXN", "Transaction", True, ExpansionSource.GOVERNED, None, 1, None, ["A"], None
        )
        models_module._FAST_CONSTRUCTION = True
        fast = _new_token_expansion(
            "TXN", "Transaction", True, ExpansionSource.GOVERNED, None, 1, None, ["A"], None
        )
    finally:
        models_module._FAST_CONSTRUCTION = saved
    assert slow.beat == ("A",) and isinstance(slow.beat, tuple)
    assert fast.beat == ["A"]
    assert isinstance(slow.confidence, float) and slow.confidence == 1.0
    assert fast.confidence == 1 and not isinstance(fast.confidence, float)


def test_the_identifier_builder_has_the_same_two_routes() -> None:
    """The six-field half of the switch, told apart the same way."""
    saved = models_module._FAST_CONSTRUCTION
    try:
        models_module._FAST_CONSTRUCTION = False
        slow = _new_identifier_expansion("A", "A", (), None, True, ["x"])
        models_module._FAST_CONSTRUCTION = True
        fast = _new_identifier_expansion("A", "A", (), None, True, ["x"])
    finally:
        models_module._FAST_CONSTRUCTION = saved
    assert slow.unaccounted == ("x",)
    assert fast.unaccounted == ["x"]


# ---------------------------------------------------------------------------
# the public constructors are unchanged
# ---------------------------------------------------------------------------


def test_the_public_constructor_still_normalises_with_the_switch_on() -> None:
    """The switch narrows the hot path; it does not widen the published API."""
    assert models_module._FAST_CONSTRUCTION is True
    record = TokenExpansion(
        raw="TXN",
        long="Transaction",
        is_known=True,
        source=ExpansionSource.GOVERNED,
        entry_id=None,
        confidence=1,
        beat=["Transmission"],
    )
    assert record.beat == ("Transmission",)
    assert isinstance(record.confidence, float)


def test_the_public_constructor_still_refuses_an_out_of_range_confidence() -> None:
    """The one range bound every governed model keeps."""
    with pytest.raises(GovernedValidationError):
        TokenExpansion(
            raw="TXN",
            long="Transaction",
            is_known=True,
            source=ExpansionSource.GOVERNED,
            entry_id=None,
            confidence=2.0,
        )


def test_the_public_identifier_constructor_still_refuses_a_non_sequence() -> None:
    """A string handed to a sequence field is the mistake that reads as an answer."""
    with pytest.raises(GovernedValidationError):
        IdentifierExpansion(
            identifier="A",
            phrase="A",
            tokens=(),
            class_word=None,
            is_fully_known=True,
            unaccounted="abc",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# the runner's new instruments, and whether they can fail
# ---------------------------------------------------------------------------


def _load(path: Path, name: str) -> ModuleType:
    """Import a script by path; ``bench/`` is a directory of scripts."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


#: The runner module, loaded at most once, on demand.
_PERF: Optional[ModuleType] = None


def _runner() -> ModuleType:
    """The perf runner, loaded by the tests that need it and not at import.

    The sdist ships ``tests/`` and deliberately not ``bench/*.py``, so the runner
    tests below cannot run against an extracted distribution. A module-level
    ``pytest.skip`` would be the usual answer and it is the wrong one **here**:
    it would take the record-builder tests above with it, and those need nothing
    but the installed package. Those are the tests that say the shipped
    optimisation changes no record, and the extracted tree is exactly the
    environment where nobody would otherwise notice they had stopped running.

    Returns:
        The imported runner.
    """
    global _PERF
    if not RUNNER.is_file():  # pragma: no cover - only in an extracted sdist
        pytest.skip("bench/run_governed_perf.py is absent; not a source checkout")
    if _PERF is None:
        _PERF = _load(RUNNER, "bench_run_governed_perf_records")
    return _PERF


def test_the_capture_reproduces_the_shipped_construction_count() -> None:
    """One captured argument tuple per record the profiler saw constructed.

    Both sides run under ``decomposition_memo_levels``, which is the
    configuration ``capture_construction_arguments`` takes its records in. The
    identifier memo removes constructions rather than making them cheaper, so
    comparing a capture taken with it off against a count taken with it on
    compares two different amounts of work.
    """
    token_args, identifier_args, _ = _runner().capture_construction_arguments(CORPUS, catalog())
    with _runner().decomposition_memo_levels():
        counted = _runner().work_counts(CORPUS, catalog())
    assert len(token_args) == counted["token_expansions_constructed"]
    assert len(identifier_args) == counted["identifier_expansions_constructed"]


def test_the_capture_cross_check_can_fire(monkeypatch: pytest.MonkeyPatch) -> None:
    """The guard that protects the whole decomposition, shown failing.

    ``record_costs`` refuses to publish anything if the captured construction
    count disagrees with the profiled one. That guard is not decoration: it is
    what caught this workstream's replay counting one construction per call on a
    tree where a sibling workstream had just given ``expand_identifier`` a memo.
    Here it is fired on purpose, by moving the profiled count by one.
    """
    runner = _runner()
    real = runner.work_counts

    def inflated(identifiers: Any, vocabulary: Any) -> dict:
        counts = dict(real(identifiers, vocabulary))
        counts["token_expansions_constructed"] += 1
        return counts

    monkeypatch.setattr(runner, "work_counts", inflated)
    with pytest.raises(SystemExit) as raised:
        runner.record_costs(
            "unit", CORPUS, "populated", catalog, rounds=1, repeats=1, source="tests"
        )
    assert "token constructions" in str(raised.value)


def test_the_capture_deduplicates_by_identity_and_not_by_value() -> None:
    """A memo hit is one construction; two equal records built apart are two."""
    repeated = ("TXN_ID", "TXN_ID", "TXN_ID")
    token_args, identifier_args, _ = _runner().capture_construction_arguments(repeated, catalog())
    assert len(identifier_args) == 3
    assert len(token_args) == 2  # TXN and ID, each built once and memoised


def test_every_route_rebuilds_the_shipped_records_exactly() -> None:
    """Parity across all three constructing routes, by ``repr`` and by JSON."""
    token_args, identifier_args, reference = _runner().capture_construction_arguments(
        CORPUS, catalog()
    )
    mismatches = _runner().route_parity(token_args, identifier_args, reference)
    assert mismatches == {"alloc": 0, "init": 0, "full": 0}


def test_the_route_parity_check_can_report_a_mismatch() -> None:
    """A check that has only ever reported zero is indistinguishable from a stub."""
    token_args, identifier_args, reference = _runner().capture_construction_arguments(
        CORPUS, catalog()
    )
    moved = [dataclasses.replace(record, phrase=record.phrase + "!") for record in reference]
    mismatches = _runner().route_parity(token_args, identifier_args, moved)
    assert mismatches["full"] > 0


def test_the_field_write_counter_is_exact_on_both_routes() -> None:
    """Eleven writes per token record and eight per identifier record, or none.

    The arithmetic is a property of the code: nine fields written by the
    generated ``__init__`` plus one each from ``_freeze_sequences`` and
    ``_freeze_confidence``; six plus two for the identifier record. The counter
    is not asked to agree with a plausible number, it is asked to agree with
    that one.
    """
    token_args, identifier_args, _ = _runner().capture_construction_arguments(CORPUS, catalog())

    def replay(label: str) -> int:
        make_token, make_identifier = _runner()._route_functions(label)
        with _runner()._route_installed(label):
            return _runner().count_field_writes(
                lambda: _runner().replay(token_args, identifier_args, make_token, make_identifier)
            )

    expected = 11 * len(token_args) + 8 * len(identifier_args)
    assert replay("full") == expected
    assert replay("alloc") == 0


def test_the_route_context_manager_restores_the_module_even_on_a_raise() -> None:
    """A benchmark that left the switch off would silently unship the change."""
    before = models_module._FAST_CONSTRUCTION
    post_init = TokenExpansion.__post_init__
    with pytest.raises(RuntimeError), _runner()._route_installed("init"):
        raise RuntimeError("probe")
    assert models_module._FAST_CONSTRUCTION is before
    assert TokenExpansion.__post_init__ is post_init


def test_the_identity_control_fires_and_moves_both_digests() -> None:
    """The gate's own positive control: one ``entry_id`` moved in one record."""
    shapes, wire, fired = _runner().identity_control(CORPUS, catalog)
    clean = _runner().identity_digests(CORPUS, catalog)
    assert fired is True
    assert shapes != clean[0]
    assert wire != clean[1]


def test_the_identity_arm_reports_identical_on_this_corpus() -> None:
    """R19 in miniature, on the corpus that reaches every branch."""
    entry = _runner().identity_arm("unit", CORPUS, "populated", catalog, source="tests")
    assert entry["repr_identical"] is True
    assert entry["json_identical"] is True
    assert entry["control_repr_differs"] is True
    assert entry["control_json_differs"] is True
    assert entry["records_compared"] > len(CORPUS)


def test_the_freeze_helpers_are_allowed_to_be_zero_and_the_builders_are_not() -> None:
    """The counters moved with the code, and the guard moved with them."""
    assert "sequence_validations" in _runner().COUNTED_OPTIONAL
    assert "confidence_validations" in _runner().COUNTED_OPTIONAL
    assert _runner().COUNTED["token_expansions_constructed"] is models_module._new_token_expansion
    assert (
        _runner().COUNTED["identifier_expansions_constructed"]
        is models_module._new_identifier_expansion
    )
    counted = _runner().work_counts(CORPUS, catalog())
    assert counted["sequence_validations"] == 0
    assert counted["confidence_validations"] == 0
    assert counted["token_expansions_constructed"] > 0
