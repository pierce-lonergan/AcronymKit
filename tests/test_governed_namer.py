"""Acceptance gate for :class:`acronymkit.governed.namer.GovernedNamer`.

The facade adds no naming logic, so almost nothing here is about naming. What it
adds is *binding* — one vocabulary, one policy, one overlay, fixed once — and the
risk that comes with binding is that a bound argument stops matching the one a
free function would have used. So the load-bearing test is
``::test_every_verb_matches_the_free_function_over_the_whole_corpus``: every verb,
every identifier in the fixture corpus, compared field for field against the
function it forwards to. If the facade ever starts answering differently from the
subsystem it wraps, that fails, and everything else in this file is detail.

The ergonomics, before and after
--------------------------------
This is the task the facade exists to shorten: load the fixture standard, apply a
non-default policy and a house overlay, then expand, check and correct one name.

Before — seven statements of setup, four of them file handling, and then four
arguments at every call site::

    allow = json.loads((FIXTURES / "allowlist.json").read_text(encoding="utf-8"))
    words = json.loads((FIXTURES / "class_words.json").read_text(encoding="utf-8"))
    with (FIXTURES / "term_glossary.csv").open(encoding="utf-8", newline="") as handle:
        terms = {row["logical_name"]: row["term_id"] for row in csv.DictReader(handle)}
    nds = GovernedDictionary.from_json(
        FIXTURES / "dictionary.json",
        approved_abbreviations=allow["approved_abbreviations"],
        common_keywords=allow["common_keywords"],
        short_full_words=allow["short_full_words"],
        class_words=words["abbreviations"],
        term_index=terms,
    )
    policy = NamingPolicy.strict_length()
    house = {"KYC": "Know Your Customer"}

    expand_identifier("CUST_ACCT_KYC_ID", nds, policy, custom=house)
    is_compliant("CUST_ACCT_KYC_ID", nds, policy, custom=house)
    normalize("custmr_acct_num", nds, policy, custom=house)

After — one statement of setup, one argument at each call site, and no way for
two call sites to disagree about the rules because there is one policy object::

    nds = GovernedNamer.from_bundle(
        FIXTURES, NamingPolicy.strict_length(), custom={"KYC": "Know Your Customer"}
    )

    nds.expand_identifier("CUST_ACCT_KYC_ID")
    nds.is_compliant("CUST_ACCT_KYC_ID")
    nds.normalize("custmr_acct_num")

``::test_the_before_and_after_in_the_module_docstring_agree`` runs both halves and
asserts they produce the same answers, so the comparison above is checked rather
than claimed — and the "before" column is not a strawman, because it is the same
assembly ``tests/test_governed.py`` performs for real.

The one thing the short version does that the long version does not is merge the
pin sheet, which the hand-written assembly quietly omits. That is not a rhetorical
flourish; it is the argument for the loader existing, and it is why the two halves
are compared on a vocabulary whose pins the catalog already carries.

The fixture catalog is the fictional **Northwind Data Standards** (``NDS``).
"""

from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from acronymkit.exceptions import ConfigurationError, LexiconError
from acronymkit.governed import (
    GovernedDictionary,
    NamingPolicy,
    UnknownPolicy,
    expand_identifier,
    expand_token,
    is_compliant,
    normalize,
    to_physical_name,
)
from acronymkit.governed.loaders import load_bundle
from acronymkit.governed.namer import GovernedNamer

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "governed"

#: The synthetic identifier corpus, one UPPER_SNAKE name per line.
CORPUS: list[str] = [
    line.strip()
    for line in (FIXTURES / "corpus_sample.txt").read_text(encoding="utf-8").splitlines()
    if line.strip()
]

#: Logical names, for the reverse direction.
with (FIXTURES / "term_glossary.csv").open(encoding="utf-8", newline="") as _handle:
    LOGICAL_NAMES: list[str] = [row["logical_name"] for row in csv.DictReader(_handle)]

#: The vocabulary every test here runs against. Module-level because it is
#: immutable and shared; a namer is designed to be exactly this.
NDS = load_bundle(FIXTURES)

#: Every named policy, for the tests that must hold whatever the rules are.
ALL_POLICIES = [
    NamingPolicy.governed_default(),
    NamingPolicy.frequency_baseline(),
    NamingPolicy.neural_optin(),
    NamingPolicy.strict_length(),
]


# --------------------------------------------------------------------------
# The facade forwards, and forwards exactly
# --------------------------------------------------------------------------
@pytest.mark.parametrize("policy", ALL_POLICIES, ids=lambda item: item.mode.value + "-policy")
def test_every_verb_matches_the_free_function_over_the_whole_corpus(
    policy: NamingPolicy,
) -> None:
    """The facade must be indistinguishable from the functions it binds.

    Run under all four named policies, over all forty corpus identifiers and
    every glossary logical name, comparing whole result objects rather than a
    field or two — the audit fields are the product here, and a facade that got
    the phrase right while dropping ``entry_id`` would be worse than one that
    failed outright.

    Args:
        policy: The named policy to bind and to pass, in turn.
    """
    namer = GovernedNamer(NDS, policy)

    for identifier in CORPUS:
        assert namer.expand_identifier(identifier) == expand_identifier(identifier, NDS, policy)
        assert namer.is_compliant(identifier) == is_compliant(identifier, NDS, policy)
        assert namer.normalize(identifier) == normalize(identifier, NDS, policy)
    for logical in LOGICAL_NAMES:
        assert namer.to_physical_name(logical) == to_physical_name(logical, NDS, policy)
    for token in ("TXN", "ID", "CTL", "KYC", "custmr", ""):
        assert namer.expand_token(token) == expand_token(token, NDS, policy)


def test_the_before_and_after_in_the_module_docstring_agree() -> None:
    """The ergonomics comparison in the module docstring is executed, not asserted in prose.

    A "before and after" that nobody runs is a sales pitch. Both halves are run
    here on the fixture standard and their answers compared, so the shorter one
    is shorter *and* the same.
    """
    allow = json.loads((FIXTURES / "allowlist.json").read_text(encoding="utf-8"))
    words = json.loads((FIXTURES / "class_words.json").read_text(encoding="utf-8"))
    with (FIXTURES / "term_glossary.csv").open(encoding="utf-8", newline="") as handle:
        terms = {row["logical_name"]: row["term_id"] for row in csv.DictReader(handle)}
    catalog = GovernedDictionary.from_json(
        FIXTURES / "dictionary.json",
        approved_abbreviations=allow["approved_abbreviations"],
        common_keywords=allow["common_keywords"],
        short_full_words=allow["short_full_words"],
        class_words=words["abbreviations"],
        term_index=terms,
    )
    policy = NamingPolicy.strict_length()
    house = {"KYC": "Know Your Customer"}

    namer = GovernedNamer.from_bundle(FIXTURES, NamingPolicy.strict_length(), custom=house)

    assert namer.expand_identifier("CUST_ACCT_KYC_ID") == expand_identifier(
        "CUST_ACCT_KYC_ID", catalog, policy, custom=house
    )
    assert namer.is_compliant("CUST_ACCT_KYC_ID") == is_compliant(
        "CUST_ACCT_KYC_ID", catalog, policy, custom=house
    )
    assert namer.normalize("custmr_acct_num") == normalize(
        "custmr_acct_num", catalog, policy, custom=house
    )


def test_the_bound_policy_is_the_one_that_is_applied() -> None:
    """Binding a policy has to *do* something, or it is decoration.

    ``strict_length`` is the preset with the most visible consequence, so it is
    the one used to show that the namer's policy reaches the compliance ladder
    and that the default namer does not inherit it.
    """
    long_name = "CUST_ACCT_PRIMARY_OWNER_PARTY_VERIFICATION_STAT_CD"

    strict = GovernedNamer(NDS, NamingPolicy.strict_length()).is_compliant(long_name)
    default = GovernedNamer(NDS).is_compliant(long_name)

    codes = {reason.code.value for reason in strict.reasons}
    assert "exceeds_max_length" in codes
    assert "exceeds_max_length" not in {reason.code.value for reason in default.reasons}


def test_an_absent_policy_is_resolved_at_construction_rather_than_per_call() -> None:
    """``.policy`` must name the rules actually in force, never ``None``.

    A caller reading a namer to find out what a run used should get an answer.
    Leaving the field ``None`` and resolving it inside each call would make the
    property lie by omission at precisely the moment somebody is auditing.
    """
    namer = GovernedNamer(NDS)

    assert namer.policy == NamingPolicy.governed_default()
    assert namer.with_policy(None).policy == NamingPolicy.governed_default()


def test_a_namer_with_no_vocabulary_is_refused_at_construction() -> None:
    """The failure belongs where the mistake was made.

    The free verbs refuse ``dictionary=None`` at the call; a facade that stored
    it would raise on the first expansion instead, with a stack trace pointing
    at a call site that did nothing wrong. The message repeats the subsystem's
    own advice, because the fix is the same one: pass an empty
    ``GovernedDictionary()`` if passing everything through is what you meant.
    """
    with pytest.raises(ConfigurationError) as caught:
        GovernedNamer(None)  # type: ignore[arg-type]

    assert "GovernedDictionary()" in str(caught.value)


# --------------------------------------------------------------------------
# Layering
# --------------------------------------------------------------------------
def test_an_overlay_bound_once_equals_an_overlay_passed_at_every_call() -> None:
    """The convenience must not be a different behaviour wearing a shorter name.

    Layering at construction and layering per call are the same operation, and
    the demotion rule under ``allow_override=False`` has to survive the move —
    an overlay refused at the call must be refused by the namer too, or the
    facade would quietly grant callers a power the policy denies them.
    """
    house = {"ID": "Identity", "KYC": "Know Your Customer"}
    strict = NamingPolicy(allow_override=False)

    permissive = GovernedNamer(NDS, custom=house)
    refusing = GovernedNamer(NDS, strict, custom=house)

    assert permissive.expand_token("ID") == expand_token("ID", NDS, custom=house)
    assert permissive.expand_token("ID").long == "Identity"
    assert refusing.expand_token("ID") == expand_token("ID", NDS, strict, custom=house)
    assert refusing.expand_token("ID").long == "Identifier"
    assert refusing.expand_token("KYC").long == "Know Your Customer"


def test_layers_compose_and_the_last_one_wins() -> None:
    """A project layer overrides a house layer and inherits the rest of it.

    The same composition
    :meth:`~acronymkit.governed.dictionary.GovernedDictionary.with_custom`
    promises, asserted through the facade because that is where a caller will
    reach for it.
    """
    house = GovernedNamer(NDS).with_custom({"KYC": "Know Your Customer", "WLT": "Wallet"})
    project = house.with_custom({"KYC": "Know Your Counterparty"})

    assert house.expand_token("KYC").long == "Know Your Customer"
    assert project.expand_token("KYC").long == "Know Your Counterparty"
    assert project.expand_token("WLT").long == "Wallet"


def test_layering_and_repolicying_leave_the_receiver_alone() -> None:
    """A shared namer must survive being specialised by one caller.

    The whole point of holding one namer as a module-level constant is that
    another thread cannot change it. Both ``with_`` methods return new objects,
    and the receiver's answers after the call are the answers it gave before.
    """
    base = GovernedNamer(NDS)

    layered = base.with_custom({"KYC": "Know Your Customer"})
    restricted = base.with_policy(NamingPolicy.strict_length())

    assert layered is not base
    assert restricted is not base
    assert base.expand_token("KYC").is_known is False
    assert base.policy == NamingPolicy.governed_default()
    assert restricted.dictionary is base.dictionary


def test_a_namer_cannot_be_written_to_after_construction() -> None:
    """Immutability is the claim the thread-safety note rests on.

    ``__slots__`` makes an accidental ``namer.policy = ...`` an error rather
    than a second, divergent copy of the bound rules that nothing would ever
    report.
    """
    namer = GovernedNamer(NDS)

    with pytest.raises(AttributeError):
        namer.policy = NamingPolicy.strict_length()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        namer.cache = {}  # type: ignore[attr-defined]


def test_a_namer_is_safe_to_share_across_threads() -> None:
    """One namer, several threads, identical answers.

    The class documents that an instance may be a module-level constant in a
    service, which is a claim about concurrency and therefore has to be run
    concurrently. Nothing here can be sensitive to interleaving unless a cache
    or a mutable field appears later — which is exactly when this test would
    start failing.
    """
    namer = GovernedNamer(NDS, NamingPolicy.strict_length())
    expected = namer.expand_many(CORPUS)

    with ThreadPoolExecutor(max_workers=8) as pool:
        # Every task is submitted before any result is read, so the calls
        # genuinely overlap; resolving each future at submission time would
        # serialise them and the test would prove nothing.
        futures = [pool.submit(namer.expand_many, CORPUS) for _ in range(8)]
        results = [future.result() for future in futures]

    assert all(result == expected for result in results)


# --------------------------------------------------------------------------
# Batches
# --------------------------------------------------------------------------
def test_a_batch_equals_the_same_calls_made_one_at_a_time() -> None:
    """The batch is a call shape, not a second implementation.

    Stated as equality rather than as spot checks, because the moment a batch
    method is allowed to differ from the single call it becomes a second place
    where a governed decision is made.
    """
    namer = GovernedNamer(NDS)

    assert namer.expand_many(CORPUS) == tuple(namer.expand_identifier(item) for item in CORPUS)
    assert namer.check_many(CORPUS) == tuple(namer.is_compliant(item) for item in CORPUS)


def test_results_correspond_to_inputs_by_position_including_duplicates() -> None:
    """Positional correspondence is the contract a parallel version must keep.

    A caller aligns results back onto their own rows by index, so no
    implementation may deduplicate, filter or reorder — and a corpus with
    repeats is the case where a well-meaning cache would be tempted to.
    """
    namer = GovernedNamer(NDS)
    identifiers = ["TXN_ID", "CUST_ACCT_OPEN_DT", "TXN_ID", "CUSTMR_ACCT_NUM", "TXN_ID"]

    results = namer.expand_many(identifiers)

    assert len(results) == len(identifiers)
    assert [result.identifier for result in results] == identifiers
    assert results[0] == results[2] == results[4]


def test_a_batch_accepts_any_iterable_and_returns_a_tuple() -> None:
    """A generator is what a pipeline has; a tuple is what a caller should get back.

    Returning a list would hand out something a caller can edit in place, and
    the results of a governed call are evidence rather than a working buffer.
    """
    namer = GovernedNamer(NDS)

    from_generator = namer.expand_many(item for item in CORPUS[:5])
    checked = namer.check_many(iter(CORPUS[:5]))

    assert isinstance(from_generator, tuple)
    assert isinstance(checked, tuple)
    assert len(from_generator) == len(checked) == 5


def test_an_empty_batch_is_an_empty_tuple_rather_than_an_error() -> None:
    """A table with no columns to check is a fact, not a failure.

    A sweep that raised on an empty input would make every caller write a guard
    around it, and the guard would be wrong somewhere.
    """
    namer = GovernedNamer(NDS)

    assert namer.expand_many([]) == ()
    assert namer.check_many([]) == ()


def test_a_blank_cell_does_not_stop_a_batch() -> None:
    """A schema export has empty cells in it, and a sweep has to survive them.

    The single-call behaviour — blank input returns an expansion whose ``long``
    is empty rather than raising — has to hold through the batch, or the batch
    is only usable on data somebody has already cleaned.
    """
    namer = GovernedNamer(NDS)

    results = namer.expand_many(["TXN_ID", "", None, "CUST_ID"])

    assert len(results) == 4
    assert results[1].phrase == ""
    assert results[2].phrase == ""


def test_a_rejecting_policy_raises_rather_than_returning_a_short_batch() -> None:
    """A partial tuple would break the correspondence every caller relies on.

    ``UnknownPolicy.REJECT`` is for pipelines where an unrecognised token means
    the catalog is out of date and processing should stop. Stopping means
    raising: returning the results gathered so far would hand back a tuple whose
    positions no longer line up with the input, which is worse than the error it
    was trying to avoid.
    """
    namer = GovernedNamer(NDS, NamingPolicy(unknown=UnknownPolicy.REJECT))

    assert namer.expand_identifier("TXN_ID").is_fully_known is True
    with pytest.raises(LexiconError):
        namer.expand_many(["TXN_ID", "CUST_ACCT_KYC_ID", "CUST_ID"])


# --------------------------------------------------------------------------
# Construction
# --------------------------------------------------------------------------
def test_from_bundle_is_the_loader_plus_the_binding() -> None:
    """The classmethods must add nothing but the binding.

    If a constructor here could produce a different vocabulary from the loader
    it mirrors, there would be two answers to "what does this standard say" and
    no way to tell which one a run used.
    """
    namer = GovernedNamer.from_bundle(FIXTURES, NamingPolicy.strict_length())

    assert namer.dictionary.entries == load_bundle(FIXTURES).entries
    assert namer.policy == NamingPolicy.strict_length()


def test_from_mapping_is_the_smallest_working_namer() -> None:
    """The two-line onboarding path, which is what a first-time caller writes."""
    namer = GovernedNamer.from_mapping({"TXN": "Transaction", "ID": "Identifier"})

    assert namer.expand_identifier("TXN_ID").phrase == "Transaction Identifier"
    assert namer.expand_token("KYC").is_known is False


def test_from_json_reads_the_catalog_and_nothing_else() -> None:
    """A catalog file is not a standard, and the namer must not pretend otherwise.

    ``from_json`` mirrors :meth:`GovernedDictionary.from_json`: it loads rows.
    The allow-lists that decide compliance come from other files, so a namer
    built this way answers expansion questions and refuses to invent approval —
    which is why :meth:`from_bundle` is the one the documentation points at.
    """
    namer = GovernedNamer.from_json(FIXTURES / "dictionary.json")

    assert namer.expand_identifier("TXN_APPLNT_ID").phrase == "Transaction Applicant Identifier"
    assert namer.dictionary.approved_abbreviations == frozenset()


def test_from_csv_and_from_long_to_short_csv_bind_what_their_loaders_produce(
    tmp_path: Path,
) -> None:
    """Both CSV constructors mirror their loaders, including the inversion's semantics.

    Args:
        tmp_path: Scratch directory for the two exports.
    """
    short_to_long = tmp_path / "short.csv"
    short_to_long.write_bytes(b"token,canonical\nTXN,Transaction\nID,Identifier\n")
    long_to_short = tmp_path / "long.csv"
    long_to_short.write_bytes(
        b"Long Name,Preferred Abbreviation\nTransaction,TXN\nIdaho,ID\nIdentifier,ID\n"
    )

    plain = GovernedNamer.from_csv(
        short_to_long, token_column="token", canonical_column="canonical"
    )
    inverted = GovernedNamer.from_long_to_short_csv(
        long_to_short,
        NamingPolicy.strict_length(),
        long_column="Long Name",
        short_column="Preferred Abbreviation",
    )

    assert plain.expand_identifier("TXN_ID").phrase == "Transaction Identifier"
    assert inverted.expand_token("ID").long == "Identifier"
    assert inverted.expand_token("ID").beat == ("Idaho",)
    assert inverted.policy == NamingPolicy.strict_length()


def test_a_classmethod_overlay_reaches_the_bound_vocabulary() -> None:
    """``custom=`` on a constructor is the same overlay as ``custom=`` on the class."""
    namer = GovernedNamer.from_bundle(FIXTURES, custom={"KYC": "Know Your Customer"})

    assert namer.expand_token("KYC").long == "Know Your Customer"
    assert namer.dictionary.lookup("KYC") is not None


def test_the_repr_names_the_vocabulary_and_the_rules() -> None:
    """A namer in a traceback should say which standard and which rules it holds."""
    text = repr(GovernedNamer(NDS, NamingPolicy.frequency_baseline()))

    assert "GovernedNamer(" in text
    assert "most_common" in text
