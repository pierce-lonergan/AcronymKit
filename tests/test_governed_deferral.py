"""The deferral census, pinned — because a negative result rots as easily as a positive one.

``bench/run_governed_deferral.py`` is the instrument that retired the
lazy-provenance workstream. Its conclusion rests on three properties, and every
one of them is a property of *this repository* rather than of lazy evaluation in
general, so every one can stop being true without anybody noticing:

* **the read rate.** Three consumer shapes in this tree reach provenance on
  every record and two do not, and which is which is what decides whether the
  deferral has a population at all;
* **the object counts.** The shipped token memo shares one provenance record
  across every occurrence of a token. A span is per-occurrence, so a deferred
  route cannot share and pays materialisation per occurrence instead;
* **byte-identity.** A deferred route that changed one ``entry_id`` in ten
  million would be catastrophic for a governance instrument and invisible to a
  benchmark, which is R19.

This file drives the runner on the committed fixture corpus and the committed
fixture catalog, so it runs in the fifteen matrix cells of ``gates.suite``, which
is a gate that already carries in-situ evidence. That was the choice: enforcement
riding a demonstrated gate rather than a forty-third gate that could not carry a
demonstration in the commit that creates it.

**And the identity check is shown capable of failing**, at the end, by breaking
the materialiser and requiring the comparison to catch it -- because a check that
has only ever reported zero mismatches is indistinguishable from one that cannot
report anything else. D-058 is four instances of exactly that.

Nothing here times anything.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, Tuple

import pytest

from acronymkit.catalog import GovernedDictionary, GovernedEntry
from acronymkit.catalog.enums import EntryKind, ExpansionSource
from acronymkit.catalog.models import IdentifierExpansion
from acronymkit.catalog.policy import NamingPolicy

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "bench" / "run_governed_deferral.py"


def _load(path: Path, name: str) -> ModuleType:
    """Import a script by path; ``bench/`` is a directory of scripts, not a package."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if not RUNNER.is_file():  # pragma: no cover - only reachable in an extracted sdist
    # Same shape as tests/test_governed_perf_runner.py, and for the same reason:
    # the sdist ships tests/ and not bench/*.py, and skipping at collection would
    # be too late because the import below runs first.
    pytest.skip(
        "bench/run_governed_deferral.py is absent; not a source checkout",
        allow_module_level=True,
    )

deferral = _load(RUNNER, "bench_run_governed_deferral")

#: A vocabulary with the one row that makes the zero-copy premise fail:
#: ``1MM``. ``_rejoin_digit_tokens`` only puts ``1_MM`` back together when a
#: catalog vouches for the joined token, so without this row the defect is
#: unreachable -- which is exactly why it is invisible on every published
#: governed arm, all of which use an empty catalog.
CATALOG_ROWS = (
    GovernedEntry(
        token="TXN",
        canonical="Transaction",
        kind=EntryKind.APPROVED_ABBREV,
        entry_id="NDS-TXN",
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

#: Every branch of the shipped path at least once, one repeat so the memo is
#: consulted rather than only filled, and the digit rejoin among them.
CORPUS = (
    "TXN_APPLNT_ID",
    "TXN_APPLNT_ID",
    "txn_dt",
    "ADDR_LINE_1",
    "AMT_1_MM",
    "AMT_1MM",
    "E_9_1_1",
    "db.schema.TXN_ID",
    "PAY€AMT",
    "TRÄGER_ID",
    "___",
    "",
    "KYC_UNKNOWN_TOKEN",
)


def catalog() -> GovernedDictionary:
    """A vocabulary that answers for three tokens, one of them digit-leading.

    Returns:
        The vocabulary.
    """
    return GovernedDictionary(CATALOG_ROWS, class_words={"ID": "Identifier"})


def empty_catalog() -> GovernedDictionary:
    """The empty vocabulary every published governed figure is taken with.

    Returns:
        The vocabulary.
    """
    return GovernedDictionary({})


CATALOGS: Dict[str, Callable[[], GovernedDictionary]] = {
    "populated": catalog,
    "empty": empty_catalog,
}


@pytest.fixture(scope="module")
def reads() -> Dict[str, Any]:
    """One read census over the fixture corpus and the populated catalog.

    Returns:
        What :func:`read_census` produced.
    """
    return deferral.read_census(CORPUS, catalog)


@pytest.fixture(scope="module")
def counts() -> Dict[str, Any]:
    """One deferral census over the fixture corpus and the populated catalog.

    Returns:
        What :func:`deferral_census` produced.
    """
    return deferral.deferral_census(CORPUS, catalog)


# ---------------------------------------------------------------------------
# the read rate: which consumer shapes reach provenance, measured by execution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("arm", ["audit", "to_json", "to_dict"])
def test_every_real_consumer_shape_forces_every_record(reads: Dict[str, Any], arm: str) -> None:
    """The three shapes that exist in ``src/`` and ``bench/`` read provenance on all of them."""
    figures = reads[arm]
    assert figures["forcing"] == figures["records"]
    assert figures["forcing_pct"] == 100.0


@pytest.mark.parametrize("arm", ["phrase_only", "gate_only"])
def test_the_two_shapes_a_deferral_could_serve_force_nothing(
    reads: Dict[str, Any], arm: str
) -> None:
    """``.phrase`` and ``.is_fully_known`` are eager fields; reading them forces no token."""
    figures = reads[arm]
    assert figures["forcing"] == 0
    assert figures["read_tokens"] == 0
    assert figures["read_dict"] == 0


def test_no_record_is_built_and_then_never_looked_at(reads: Dict[str, Any]) -> None:
    """A record nobody reads is the one population maximal deferral would serve.

    There is none, on any arm. That is what makes the question "which fields"
    rather than "whether".
    """
    for arm in deferral.ARM_ORDER:
        assert reads[arm]["never_read"] == 0, arm


def test_the_census_distinguishes_a_forcing_read_from_an_eager_one(
    reads: Dict[str, Any],
) -> None:
    """The instrument would be useless if every arm came back the same.

    This is the arms-must-differ guard: a spy that recorded nothing, or recorded
    everything, would satisfy each test above on its own.
    """
    forcing = {arm: reads[arm]["forcing_pct"] for arm in deferral.ARM_ORDER}
    assert sorted(set(forcing.values())) == [0.0, 100.0]


# ---------------------------------------------------------------------------
# the object counts: what each route allocates
# ---------------------------------------------------------------------------


def test_the_deferred_route_never_allocates_fewer_objects(counts: Dict[str, Any]) -> None:
    """On every arm, including the strongest form of the bet."""
    for arm in deferral.DEFERRAL_ARMS:
        figures = counts[arm]
        assert figures["lazy_objects"] >= figures["eager_objects"], arm


@pytest.mark.parametrize("arm", ["phrase_only", "gate_only"])
def test_where_deferral_is_possible_it_breaks_exactly_even(
    counts: Dict[str, Any], arm: str
) -> None:
    """One object per call becomes one object per call, and the difference is the side table.

    The integer array replaces the tuple of records; the deferred record replaces
    the identifier record; the compact answer replaces the token record. Every
    substitution is one-for-one, which is why the saving is zero rather than
    small.
    """
    figures = counts[arm]
    assert figures["lazy_minus_eager"] == figures["lazy_synthesised_tables"]
    assert figures["lazy_materialised_token_records"] == 0


@pytest.mark.parametrize("arm", ["audit", "to_json", "to_dict", "to_json_shared"])
def test_where_deferral_is_impossible_it_multiplies_the_objects(
    counts: Dict[str, Any], arm: str
) -> None:
    """Materialisation is per occurrence; the shipped memo shares per token."""
    assert counts[arm]["lazy_over_eager"] > 1.0


def test_sharing_materialised_records_helps_and_still_loses(counts: Dict[str, Any]) -> None:
    """The strongest form of the bet is measured rather than dismissed.

    A deferred route may cache materialised records by ``(answer, raw)``, which
    is the shipped token memo rebuilt one layer out. It costs less than the plain
    deferred route and it still costs more than not deferring.
    """
    assert counts["to_json_shared"]["lazy_objects"] < counts["to_json"]["lazy_objects"]
    assert counts["to_json_shared"]["lazy_objects"] > counts["to_json_shared"]["eager_objects"]
    assert counts["to_json_shared"]["lazy_materialisation_shared_hits"] > 0


def test_the_population_the_ranking_rests_on_is_re_derived_rather_than_quoted(
    counts: Dict[str, Any],
) -> None:
    """D-086 ranked lazy provenance first on ``3.728`` records per identifier.

    Two rounds of memo and construction work moved that number and nothing in
    this repository recomputed it. This assertion is not about the value; it is
    that a value exists, is derived from the counts beside it, and cannot be
    quoted from a decision record that has gone stale.
    """
    settled = counts["to_json"]
    assert counts["provenance_records_constructed"] == (
        settled["eager_identifier_records"] + settled["eager_token_records"]
    )
    assert counts["provenance_records_per_identifier"] == pytest.approx(
        counts["provenance_records_constructed"] / counts["identifiers"], abs=1e-4
    )
    assert 0.0 < counts["provenance_records_per_identifier"] < 4.0


# ---------------------------------------------------------------------------
# R19, and the demonstration that it can fail
# ---------------------------------------------------------------------------


def test_the_deferred_route_is_byte_identical_to_the_shipped_one(
    counts: Dict[str, Any],
) -> None:
    """Every field of every record, in both renderings, with the control probe fired."""
    assert counts["identity_records"] == len(CORPUS)
    assert counts["identity_json_mismatches"] == 0
    assert counts["identity_repr_mismatches"] == 0
    assert counts["json_identical"] is True
    assert counts["repr_identical"] is True
    assert counts["control_probe_fired"] is True


@pytest.mark.parametrize("label", sorted(CATALOGS))
def test_identity_holds_on_both_catalogs(label: str) -> None:
    """The empty catalog is the arm every published figure uses; the populated one is not."""
    figures = deferral.identity_arm(CORPUS, CATALOGS[label], NamingPolicy.governed_default())
    assert figures["identity_json_mismatches"] == 0
    assert figures["identity_repr_mismatches"] == 0


def test_the_identity_check_can_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Break the materialiser and the comparison must catch it.

    Without this the three assertions above are compatible with a comparison
    that never looks at anything, which is the defect the whole gate register
    exists to catalogue.
    """
    real = deferral._materialise

    def broken(raw: str, answer: Tuple[Any, ...]) -> Any:
        return real(raw, ("MUTATED", *answer[1:]))

    monkeypatch.setattr(deferral, "_materialise", broken)
    figures = deferral.identity_arm(CORPUS, catalog, NamingPolicy.governed_default())
    assert figures["identity_json_mismatches"] > 0
    assert figures["identity_repr_mismatches"] > 0
    assert figures["json_identical"] is False


# ---------------------------------------------------------------------------
# the structural finding: `raw` is not always a slice of the identifier
# ---------------------------------------------------------------------------


def test_a_rejoined_digit_token_is_not_a_substring_of_its_own_identifier() -> None:
    """``AMT_1_MM`` yields the token ``1MM``, and no pair of offsets addresses it.

    This is the zero-copy premise failing, and it fails only where a catalog
    vouches for the joined token -- so an integer-span representation would have
    passed R19 on every published governed arm and lost a character on the first
    real catalog.
    """
    counts = deferral._new_counts()
    produced = deferral.expand_deferred(
        "AMT_1_MM",
        catalog(),
        NamingPolicy.governed_default(),
        [],
        {},
        {},
        counts,
    )
    assert counts["lazy_tokens_not_a_slice"] == 1
    assert counts["lazy_synthesised_tables"] == 1
    assert [token.raw for token in produced.tokens] == ["AMT", "1MM"]
    assert "1MM" not in "AMT_1_MM"


def test_the_same_identifier_costs_nothing_extra_on_an_empty_catalog() -> None:
    """No catalog, no rejoin, no synthesised token -- which is why it is invisible."""
    counts = deferral._new_counts()
    deferral.expand_deferred(
        "AMT_1_MM",
        empty_catalog(),
        NamingPolicy.governed_default(),
        [],
        {},
        {},
        counts,
    )
    assert counts["lazy_tokens_not_a_slice"] == 0


# ---------------------------------------------------------------------------
# the instrument puts the interpreter back
# ---------------------------------------------------------------------------


def test_the_read_spy_leaves_no_trace(reads: Dict[str, Any]) -> None:
    """A spy left on the class would make every later measurement in the process wrong."""
    assert reads["identifiers"] == len(CORPUS)
    assert "__getattribute__" not in vars(IdentifierExpansion)


def test_the_read_spy_refuses_to_stack() -> None:
    """Nesting would restore by deletion and remove somebody else's override."""

    def nested() -> None:
        """Enter a second ledger, which must refuse."""
        with deferral.read_ledger():
            pass  # pragma: no cover - the context manager raises on entry

    with deferral.read_ledger():
        pytest.raises(RuntimeError, nested).match("already defines")
    assert "__getattribute__" not in vars(IdentifierExpansion)


def test_the_memo_levels_are_restored() -> None:
    """The deferred route silences the shipped memos and must give them back."""
    from acronymkit.catalog import dictionary as dictionary_module

    before = dict(dictionary_module._MEMO_LEVELS)
    with deferral.shipped_memos_off():
        assert not any(dictionary_module._MEMO_LEVELS.values())
    assert dict(dictionary_module._MEMO_LEVELS) == before
