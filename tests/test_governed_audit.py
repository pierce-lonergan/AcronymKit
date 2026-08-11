"""Acceptance gate for :mod:`acronymkit.governed.audit`.

The audit is arithmetic over answers the three verbs already gave, so the
strongest thing this suite can assert is exactly that: for every count, running
the verbs by hand over the same corpus produces the same number. A test that
re-implemented the audit's own reduction would only prove the reduction was
written twice. So the expectations here come from two places and nowhere else —
the verbs themselves, called one identifier at a time, and the fixture corpus's
own recorded shape.

What is asserted
----------------
* **Nothing is invented.** Every corpus count equals the same count taken by
  calling ``expand_identifier``, ``is_compliant``, ``to_physical_name`` and
  ``normalize`` in a loop. Every unknown token is one the expansion reported
  unknown, and no token the vocabulary covers reaches the backlog.
* **The ranking is total.** Occurrences first, then the token, so two runs over
  one corpus cannot order the backlog differently.
* **The counts partition the corpus.** Known and partially known, compliant and
  not, and the three round-trip outcomes each add up to the total — which is
  what makes it safe to quote one of them on its own.
* **A repeated identifier is expanded once**, asserted by counting the
  vocabulary lookups rather than by timing anything.
* **The proposal fence holds.** A suggestion for a token the catalog is silent
  about carries no wording at all, a candidate-only reverse match is refused,
  and no suggestion ever claims to be governed.

The corpus and catalog are the ones ``tests/test_governed.py`` assembles from
``tests/fixtures/governed``. They are imported rather than rebuilt so that the
two suites cannot end up auditing different vocabularies while appearing to
agree.

The fixture catalog is the fictional **Northwind Data Standards** (``NDS``).
Nothing here describes a real organisation's naming standard.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from typing import Any, Optional

import pytest

from acronymkit.exceptions import ConfigurationError
from acronymkit.governed import (
    ComplianceReasonCode,
    EntryKind,
    ExpansionSource,
    GovernedDictionary,
    GovernedEntry,
    NamingPolicy,
    UnknownPolicy,
    Verdict,
    expand_identifier,
    is_compliant,
    normalize,
    to_physical_name,
)
from acronymkit.governed.audit import (
    CatalogSuggestion,
    CorpusAudit,
    audit_identifiers,
    render_audit,
    suggest_catalog_additions,
)
from test_governed import ALL_POLICIES, CORPUS, EMPTY, NDS

# --------------------------------------------------------------------------
# One audit of the fixture corpus, shared by every test that only reads it
# --------------------------------------------------------------------------
#: Module-level rather than a fixture: it is frozen, it is the same object for
#: every test, and computing it once keeps this file from running the whole
#: corpus through four verbs several dozen times.
AUDIT = audit_identifiers(CORPUS, NDS)

#: An overlay that makes the reverse index disagree with the forward direction:
#: it claims "Account" for a token the standard does not approve, so rendering
#: an expanded phrase reaches ``AC`` while ``normalize`` leaves the approved
#: ``ACCT`` alone. This is the shape of a genuine catalog inconsistency, built
#: deliberately because the fixture catalog does not contain one.
ALIAS = GovernedEntry(
    token="AC",
    canonical="Account",
    kind=EntryKind.APPROVED_ABBREV,
    keep_as_abbrev=True,
    entry_id="LOCAL-AC-0001",
    source=ExpansionSource.CUSTOM,
)


def _unknown_tokens(identifier: str) -> list[str]:
    """The tokens the expansion reported unknown, upper-cased, letters only.

    Args:
        identifier: One physical name.

    Returns:
        One entry per unknown appearance, in identifier order, so a token used
        twice appears twice.
    """
    return [
        token.raw.upper()
        for token in expand_identifier(identifier, NDS).unknown_tokens
        if any(character.isalpha() for character in token.raw)
    ]


# --------------------------------------------------------------------------
# The audit invents nothing
# --------------------------------------------------------------------------
def test_the_coverage_counts_equal_calling_the_verbs_one_at_a_time() -> None:
    """Every headline count is the same count taken by hand.

    This is the whole contract of the module: it reduces answers the verbs gave
    and adds no judgement of its own. If it ever starts disagreeing with a loop
    over the same corpus, one of the two is wrong and it is not the loop.
    """
    known = sum(expand_identifier(name, NDS).is_fully_known for name in CORPUS)
    compliant = sum(is_compliant(name, NDS).compliant for name in CORPUS)
    assert AUDIT.total == len(CORPUS)
    assert AUDIT.distinct == len(set(CORPUS))
    assert AUDIT.fully_known == known
    assert AUDIT.partially_known == len(CORPUS) - known
    assert AUDIT.compliant == compliant
    assert AUDIT.non_compliant == len(CORPUS) - compliant


def test_the_unknown_token_counts_equal_calling_the_verbs_one_at_a_time() -> None:
    """Occurrences and identifier counts both match a hand-taken tally.

    The two are counted separately because they answer different questions, and
    counting them separately is also where an off-by-one would hide: a token
    appearing six times inside one name must read as six occurrences in one
    identifier, not as six identifiers.
    """
    occurrences: dict[str, int] = {}
    identifiers: dict[str, int] = {}
    for name in CORPUS:
        found = _unknown_tokens(name)
        for token in found:
            occurrences[token] = occurrences.get(token, 0) + 1
        for token in set(found):
            identifiers[token] = identifiers.get(token, 0) + 1
    assert {item.token: item.occurrences for item in AUDIT.unknown_tokens} == occurrences
    assert {item.token: item.identifier_count for item in AUDIT.unknown_tokens} == identifiers


def test_the_finding_counts_equal_calling_the_verbs_one_at_a_time() -> None:
    """The tally by reason code matches the failing findings, code by code.

    This is the number a governance function quotes — "so many columns do not
    end in a class word" — so it is the number most worth pinning to the check
    that produced it.
    """
    occurrences: dict[ComplianceReasonCode, int] = {}
    identifiers: dict[ComplianceReasonCode, int] = {}
    for name in CORPUS:
        codes = [reason.code for reason in is_compliant(name, NDS).failures]
        for code in codes:
            occurrences[code] = occurrences.get(code, 0) + 1
        for code in set(codes):
            identifiers[code] = identifiers.get(code, 0) + 1
    assert {item.code: item.occurrences for item in AUDIT.findings} == occurrences
    assert {item.code: item.identifier_count for item in AUDIT.findings} == identifiers


def test_only_failing_findings_are_tallied() -> None:
    """A passing finding never reaches the tally.

    Passing findings are recorded per name so a review can see why a name was
    accepted. A corpus-level count of them is not a work item, and if one ever
    appeared here it would be indistinguishable from a problem.
    """
    passing = {
        reason.code
        for name in CORPUS
        for reason in is_compliant(name, NDS).reasons
        if reason.verdict is Verdict.PASS
    }
    failing = {
        reason.code
        for name in CORPUS
        for reason in is_compliant(name, NDS).reasons
        if reason.verdict is Verdict.FAIL
    }
    tallied = {item.code for item in AUDIT.findings}
    assert tallied == failing
    assert not tallied & (passing - failing)


def test_the_fixture_corpus_has_the_shape_the_fixtures_record() -> None:
    """The literal counts for the corpus as it stands today.

    Written out rather than derived, so that a change to the fixture corpus or
    the catalog has to be acknowledged here rather than silently absorbed by a
    test that recomputes both sides of its own assertion.
    """
    assert (AUDIT.total, AUDIT.distinct, AUDIT.empty) == (40, 40, 0)
    assert (AUDIT.fully_known, AUDIT.partially_known) == (29, 11)
    assert (AUDIT.compliant, AUDIT.non_compliant) == (27, 13)
    assert AUDIT.unknown_token_count == 11
    assert AUDIT.ordinal_occurrences == 2
    assert [(item.code.value, item.occurrences) for item in AUDIT.findings] == [
        ("unapproved_abbrev", 66),
        ("missing_class_word", 3),
    ]


# --------------------------------------------------------------------------
# The counts partition the corpus
# --------------------------------------------------------------------------
@pytest.mark.parametrize("policy", ALL_POLICIES, ids=lambda item: item.mode.value + str(item))
def test_every_count_partitions_the_corpus_under_every_policy(policy: NamingPolicy) -> None:
    """Known/partial, compliant/not, and the three round-trip outcomes each add up.

    A count that does not sum to the total is one a reader cannot quote on its
    own, and the round-trip triple is the one most likely to drift: it is the
    only place an identifier is classified rather than merely counted.
    """
    audit = audit_identifiers(CORPUS, NDS, policy)
    assert audit.fully_known + audit.partially_known == audit.total
    assert audit.compliant + audit.non_compliant == audit.total
    assert (
        audit.round_trip_stable + audit.round_trip_corrected + audit.round_trip_inconsistent
        == audit.total
    )


def test_the_counts_are_over_the_corpus_as_supplied_not_the_distinct_names() -> None:
    """A name that appears in forty tables counts forty times.

    The question the audit answers is how much of a schema is affected, so
    de-duplication has to be invisible in every number except ``distinct``.
    """
    doubled = audit_identifiers([*CORPUS, *CORPUS], NDS)
    assert (doubled.total, doubled.distinct) == (2 * AUDIT.total, AUDIT.distinct)
    assert doubled.fully_known == 2 * AUDIT.fully_known
    assert doubled.non_compliant == 2 * AUDIT.non_compliant
    assert [item.occurrences for item in doubled.unknown_tokens] == [
        2 * item.occurrences for item in AUDIT.unknown_tokens
    ]


# --------------------------------------------------------------------------
# The backlog
# --------------------------------------------------------------------------
def test_the_backlog_is_ranked_by_occurrence_and_then_by_token() -> None:
    """Two runs over one corpus cannot order the backlog differently.

    Occurrence count is the priority a catalog owner wants; the token is the
    tie-break, and it is there so the order is total rather than dependent on
    the order a dict happened to be filled in.
    """
    ranked = [(item.occurrences, item.token) for item in AUDIT.unknown_tokens]
    assert ranked == sorted(ranked, key=lambda item: (-item[0], item[1]))
    assert [item.token for item in audit_identifiers(CORPUS, NDS).unknown_tokens] == [
        item.token for item in AUDIT.unknown_tokens
    ]


def test_every_backlog_token_is_one_the_expansion_reported_unknown() -> None:
    """Nothing reaches the backlog that the vocabulary actually covers.

    The backlog is the output a team acts on first, and a token in it that the
    catalog already carries is a row somebody writes twice.
    """
    reported = {token for name in CORPUS for token in _unknown_tokens(name)}
    assert {item.token for item in AUDIT.unknown_tokens} == reported
    for item in AUDIT.unknown_tokens:
        assert NDS.resolve(item.token) is None, f"{item.token} is in the catalog after all"


def test_an_ordinal_is_counted_apart_from_the_backlog() -> None:
    """The 1 and 2 of ``ADDR_LINE_1_TXT`` are not catalog gaps.

    They are unknown tokens by the expansion contract and no catalog row would
    fix them, so ranking them would put two rows nobody can act on at the top of
    a list whose whole value is that every row is actionable. The compliance
    check makes the same call for the same reason.
    """
    assert not [item.token for item in AUDIT.unknown_tokens if item.token.isdigit()]
    ordinals = sum(
        1
        for name in CORPUS
        for token in expand_identifier(name, NDS).unknown_tokens
        if not any(character.isalpha() for character in token.raw)
    )
    assert AUDIT.ordinal_occurrences == ordinals == 2


def test_a_token_repeated_inside_one_name_counts_once_as_an_identifier() -> None:
    """Six appearances in one name are six occurrences and one identifier."""
    wallet = next(item for item in AUDIT.unknown_tokens if item.token == "WLT")
    assert (wallet.occurrences, wallet.identifier_count) == (6, 1)


def test_examples_are_capped_and_name_identifiers_the_token_appears_in() -> None:
    """The examples are there to be looked at, not to be a second corpus."""
    repeated = audit_identifiers([*CORPUS, *CORPUS], NDS, max_examples=2)
    for item in repeated.unknown_tokens:
        assert len(item.examples) <= 2
        assert len(set(item.examples)) == len(item.examples), "a repeat became two examples"
        for example in item.examples:
            assert item.token in _unknown_tokens(example)


def test_zero_examples_retains_none_and_changes_no_count() -> None:
    """``max_examples=0`` is the supported way to ask for counts alone."""
    lean = audit_identifiers(CORPUS, NDS, max_examples=0)
    assert not any(item.examples for item in lean.unknown_tokens)
    assert not any(item.examples for item in lean.findings)
    assert [item.occurrences for item in lean.unknown_tokens] == [
        item.occurrences for item in AUDIT.unknown_tokens
    ]


def test_an_overlay_takes_a_token_off_the_backlog() -> None:
    """Declaring what the catalog could not know removes it from the work list.

    The overlay is layered once for the whole audit rather than once per name,
    and this is what notices if that layering is ever dropped.
    """
    overlaid = audit_identifiers(CORPUS, NDS, custom={"KYC": "Know Your Customer"})
    assert "KYC" in {item.token for item in AUDIT.unknown_tokens}
    assert "KYC" not in {item.token for item in overlaid.unknown_tokens}
    assert overlaid.fully_known > AUDIT.fully_known


# --------------------------------------------------------------------------
# The round trip
# --------------------------------------------------------------------------
def test_a_corrected_round_trip_is_the_one_normalize_would_have_made() -> None:
    """The names the trip moves are exactly the names ``normalize`` rewrites.

    Reported apart from the breaks because it is not a fault: the standard
    correcting an unapproved token is the package doing its job, and counting it
    as evidence of an inconsistent catalog would bury the cases that are.
    """
    rewritten = [name for name in CORPUS if normalize(name, NDS) != name]
    assert AUDIT.round_trip_corrected == len(rewritten) == 4
    assert AUDIT.round_trip_inconsistent == 0
    assert AUDIT.round_trip_breaks == ()
    for name in rewritten:
        detail = next(item for item in AUDIT.details if item.identifier == name)
        assert detail.round_trip == detail.governed_form == normalize(name, NDS)


def test_the_corpus_exercises_both_halves_of_the_round_trip() -> None:
    """The corpus contains names the trip moves and names it does not.

    Without this the two assertions above would pass on a corpus where the trip
    never moved anything, which would make them much weaker than they read.
    """
    assert AUDIT.round_trip_stable > 0
    assert AUDIT.round_trip_corrected > 0


def test_a_name_without_a_class_word_is_not_reported_as_a_broken_round_trip() -> None:
    """Rendering appends a class word and ``normalize`` does not; that is not a break.

    On a schema written before the standard, thousands of names lack a class
    word. Comparing an appended rendering against an unappended correction would
    report every one of them as a catalog disagreeing with itself, which is both
    false and loud enough to hide the handful of real ones. The shortfall is
    still reported, once, as a compliance finding.
    """
    name = "FRAUD_MODEL_RISK_SCORE"
    phrase = expand_identifier(name, NDS).phrase
    assert to_physical_name(phrase, NDS).physical == f"{name}_VAL"

    audit = audit_identifiers([name], NDS)
    assert (audit.round_trip_stable, audit.round_trip_inconsistent) == (1, 0)
    assert ComplianceReasonCode.MISSING_CLASS_WORD in {item.code for item in audit.findings}


def test_a_reverse_index_that_disagrees_with_the_catalog_is_reported_as_a_break() -> None:
    """The case the round trip exists to catch, built because the fixture has none.

    ``AC`` claims the long form "Account" without being approved, so expanding
    ``ACCT_BAL_AM`` and rendering the phrase back reaches ``AC`` while the
    verifier leaves the approved ``ACCT`` alone. Landing on neither the name nor
    its governed form is what makes this a break rather than a correction.
    """
    audit = audit_identifiers(["ACCT_BAL_AM"], NDS, custom={"AC": ALIAS})
    assert audit.round_trip_inconsistent == 1
    (break_,) = audit.round_trip_breaks
    assert break_.identifier == "ACCT_BAL_AM"
    assert break_.phrase == "Account Balance Amount"
    assert break_.physical == "AC_BAL_AM"
    assert break_.governed_form == "ACCT_BAL_AM"
    assert break_.physical != break_.identifier
    assert break_.physical != break_.governed_form


def test_a_repeated_break_is_recorded_once_and_counted_every_time() -> None:
    """One record per distinct name, one count per appearance.

    The record is what a reviewer reads and reading it forty times says nothing
    more than reading it once; the count is how much of the schema is affected,
    and there the repeats are the point.
    """
    audit = audit_identifiers(["ACCT_BAL_AM"] * 4, NDS, custom={"AC": ALIAS})
    assert audit.round_trip_inconsistent == 4
    assert len(audit.round_trip_breaks) == 1


# --------------------------------------------------------------------------
# Cost
# --------------------------------------------------------------------------
class _CountingDictionary(GovernedDictionary):
    """A vocabulary that counts how often it was asked to resolve a token.

    Counting lookups rather than timing the call is what makes the
    de-duplication assertion below deterministic: a timing test on a fast
    operation measures the machine, and this measures the thing that was
    claimed.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Build the vocabulary and start the counter."""
        super().__init__(*args, **kwargs)
        self.resolutions = 0

    def resolve(
        self, token: Optional[str], policy: Optional[NamingPolicy] = None
    ) -> Optional[GovernedEntry]:
        """Count the call and answer it exactly as the base class would."""
        self.resolutions += 1
        return super().resolve(token, policy)


def _counting() -> _CountingDictionary:
    """Rebuild the fixture vocabulary as a counting one.

    Returns:
        The same catalog rows and allow-lists, with a lookup counter attached.
    """
    return _CountingDictionary(
        NDS.entries,
        approved_abbreviations=NDS.approved_abbreviations,
        common_keywords=NDS.common_keywords,
        short_full_words=NDS.short_full_words,
        class_words=NDS.class_words,
    )


def test_a_repeated_identifier_is_expanded_once() -> None:
    """Auditing one name forty times costs what auditing it once costs.

    A warehouse repeats ``LAST_CHG_TS`` across every table it has, so the
    de-duplication is not an optimisation for a synthetic case — it is the
    difference between an audit of a schema and an audit of a column list.
    """
    name = CORPUS[0]
    once = _counting()
    audit_identifiers([name], once)
    many = _counting()
    audit_identifiers([name] * 40, many)
    assert many.resolutions == once.resolutions > 0


def test_distinct_identifiers_are_each_expanded_once() -> None:
    """And the corpus as a whole costs one pass, not one per repeat."""
    single = _counting()
    audit_identifiers(CORPUS, single)
    doubled = _counting()
    audit_identifiers([*CORPUS, *CORPUS], doubled)
    assert doubled.resolutions == single.resolutions


def test_the_corpus_is_consumed_once() -> None:
    """A generator over a schema export is a supported argument.

    Reading the input twice would work on a list and fail on the shape a caller
    reaches for when the corpus is large, which is the worst way for it to fail.
    """
    consumed = 0

    def stream() -> Any:
        nonlocal consumed
        for name in CORPUS:
            consumed += 1
            yield name

    audit = audit_identifiers(stream(), NDS)
    assert consumed == len(CORPUS) == audit.total


# --------------------------------------------------------------------------
# Detail
# --------------------------------------------------------------------------
def test_details_are_kept_only_for_identifiers_there_is_something_to_say_about() -> None:
    """A clean name contributes a count and nothing else.

    On a corpus of fifty thousand columns the per-name records would otherwise
    be the largest thing in the payload, and every one of them for a clean name
    would repeat what the counts already say.
    """
    detailed = {item.identifier for item in AUDIT.details}
    for name in CORPUS:
        expansion = expand_identifier(name, NDS)
        compliance = is_compliant(name, NDS)
        moved = normalize(name, NDS) != name
        interesting = not expansion.is_fully_known or not compliance.compliant or moved
        assert (name in detailed) is interesting


def test_a_detail_record_carries_what_the_verbs_said_about_that_name() -> None:
    """Field by field, against the verbs, for every name that has a record."""
    for item in AUDIT.details:
        expansion = expand_identifier(item.identifier, NDS)
        compliance = is_compliant(item.identifier, NDS)
        assert item.is_fully_known == expansion.is_fully_known
        assert item.compliant == compliance.compliant
        assert item.occurrences == CORPUS.count(item.identifier)
        assert set(item.unknown_tokens) == {token.raw.upper() for token in expansion.unknown_tokens}
        assert set(item.codes) == {reason.code for reason in compliance.failures}


def test_turning_details_off_changes_nothing_else() -> None:
    """``keep_details=False`` drops the records and no count with them."""
    lean = audit_identifiers(CORPUS, NDS, keep_details=False)
    assert lean.details == ()
    assert lean.to_dict() | {"details": []} == AUDIT.to_dict() | {"details": []}


def test_a_repeated_identifier_has_one_record_carrying_its_count() -> None:
    """The record says how many columns it stands for."""
    name = AUDIT.details[0].identifier
    audit = audit_identifiers([name] * 3, NDS)
    (detail,) = audit.details
    assert (detail.identifier, detail.occurrences) == (name, 3)


# --------------------------------------------------------------------------
# Suggestions are questions, not answers
# --------------------------------------------------------------------------
def test_a_suggestion_never_claims_to_be_governed() -> None:
    """Not for any token, under any route, ever.

    The library's whole thesis is that an unknown token comes back marked
    unknown. A suggestion is a request for a human decision and the payload has
    to say so on its face, because the process reading it is not the person who
    asked for it.
    """
    suggestions = suggest_catalog_additions(AUDIT)
    assert suggestions
    for item in suggestions:
        assert item.is_governed is False
    assert "confidence" not in {field.name for field in fields(CatalogSuggestion)}, (
        "a confidence on a suggestion invites comparing it against a governed answer"
    )


def test_suggestions_follow_the_audit_ranking() -> None:
    """The queue is already in the order that clears the most columns per row."""
    suggestions = suggest_catalog_additions(AUDIT)
    assert [item.token for item in suggestions] == [item.token for item in AUDIT.unknown_tokens]
    assert [item.occurrences for item in suggestions] == [
        item.occurrences for item in AUDIT.unknown_tokens
    ]


def test_a_token_the_catalog_is_silent_about_gets_no_proposed_wording() -> None:
    """``TRNCH`` appears six times and the library still declines to say what it means.

    This is the case the fence exists for, and it is the majority of any real
    backlog. Frequency is evidence about how much a gap costs and no evidence at
    all about what fills it.
    """
    for item in suggest_catalog_additions(AUDIT):
        assert item.proposed_long_form is None
        assert item.proposed_abbreviation is None
        assert item.basis is None


def test_a_spelled_out_governed_word_is_proposed_out_of_the_catalogs_own_row() -> None:
    """The one inference: the schema wrote the word, the catalog already has it.

    Reading the reverse index is not guessing — the row is there, with an id to
    go and look at. What the suggestion asks for is a decision about the column
    names, not about what the token means.
    """
    audit = audit_identifiers(["CUSTOMER_ACCOUNT_IDENTIFIER"], NDS)
    proposals = {item.token: item for item in suggest_catalog_additions(audit)}
    customer = proposals["CUSTOMER"]
    assert customer.proposed_long_form == "Customer"
    assert customer.proposed_abbreviation == "CUST"
    assert customer.entry_id == "NDS-CUST"
    assert customer.basis is not None and "CUST" in customer.basis
    assert customer.is_governed is False
    assert proposals["ACCOUNT"].proposed_abbreviation == "ACCT"


def test_a_candidate_only_reverse_match_is_refused() -> None:
    """``DEPARTMENT`` reaches the ``DEP`` row, and ``DEP`` means Deposit.

    The reverse index carries every long form a row ever listed, so matching one
    is not the same as the row meaning it. Without this condition the audit
    would tell a team to write its department columns as deposit ones, citing a
    catalog row that says the opposite — which is worse than saying nothing,
    because it comes with an entry id attached.
    """
    entry = NDS.abbreviate("DEPARTMENT")
    assert entry is not None
    assert (entry.token, entry.canonical) == ("DEP", "Deposit")

    audit = audit_identifiers(["DEPARTMENT_CD"], NDS)
    (suggestion,) = [
        item for item in suggest_catalog_additions(audit) if item.token == "DEPARTMENT"
    ]
    assert suggestion.proposed_long_form is None
    assert suggestion.proposed_abbreviation is None
    assert suggestion.basis is None


def test_a_proposal_is_refused_when_the_short_form_it_names_is_not_approved() -> None:
    """Rewriting an unapproved token to another unapproved one has fixed nothing.

    The same rule the compliance check applies before it proposes a fix, applied
    here for the same reason. The fixture catalog has no long form whose reverse
    winner is unapproved, so the row that makes one is added to it — the catalog
    is otherwise the fixture's own, and the row is the whole difference.
    """
    unapproved = GovernedEntry(
        token="ESCRW",
        canonical="Escrow",
        kind=EntryKind.UNAPPROVED_EXPANSION,
        entry_id="LOCAL-ESCRW-0001",
        source=ExpansionSource.GOVERNED,
        confidence=0.6,
    )
    catalog = GovernedDictionary(
        (*NDS.entries, unapproved),
        approved_abbreviations=NDS.approved_abbreviations,
        common_keywords=NDS.common_keywords,
        short_full_words=NDS.short_full_words,
        class_words=NDS.class_words,
    )
    assert catalog.abbreviate("ESCROW") is unapproved
    assert not catalog.is_approved("ESCRW")

    audit = audit_identifiers(["ESCROW_ACCT_ID"], catalog)
    (suggestion,) = [item for item in suggest_catalog_additions(audit) if item.token == "ESCROW"]
    assert suggestion.proposed_abbreviation is None
    assert suggestion.proposed_long_form is None


def test_the_limit_truncates_from_the_top_of_the_ranking() -> None:
    """A limited queue is the highest-value rows, not an arbitrary slice."""
    everything = suggest_catalog_additions(AUDIT)
    assert suggest_catalog_additions(AUDIT, limit=3) == everything[:3]
    assert suggest_catalog_additions(AUDIT, limit=0) == ()
    assert suggest_catalog_additions(AUDIT, limit=len(everything) + 10) == everything


def test_a_negative_limit_is_refused() -> None:
    """Rather than silently reading from the wrong end of the ranking."""
    with pytest.raises(ConfigurationError):
        suggest_catalog_additions(AUDIT, limit=-1)


def test_suggestions_can_be_taken_from_an_audit_that_kept_no_details() -> None:
    """Only the ranked backlog is read, so the memory-lean audit is a full argument."""
    lean = audit_identifiers(CORPUS, NDS, keep_details=False)
    assert suggest_catalog_additions(lean) == suggest_catalog_additions(AUDIT)


# --------------------------------------------------------------------------
# Empty, absent and refused input
# --------------------------------------------------------------------------
def test_blank_and_absent_identifiers_are_counted_rather_than_skipped() -> None:
    """A schema export with holes in it must not quietly shrink the denominator.

    An identifier that tokenises to nothing is fully known vacuously — that is
    what the expansion says about it — so counting it without also counting it
    as empty would make a half-blank corpus look like a well-covered one.
    """
    audit = audit_identifiers(["TXN_ID", "", None, "___"], NDS)
    assert (audit.total, audit.empty) == (4, 3)
    assert audit.fully_known == 4
    assert audit.non_compliant == 3


def test_an_empty_corpus_audits_to_zeroes() -> None:
    """Nothing to report is a report, not an error."""
    audit = audit_identifiers([], NDS)
    assert (audit.total, audit.distinct, audit.fully_known) == (0, 0, 0)
    assert audit.unknown_tokens == audit.findings == audit.details == ()


def test_an_empty_vocabulary_reports_every_token_as_unknown() -> None:
    """The supported spelling of "audit against a standard that governs nothing"."""
    audit = audit_identifiers(["TXN_APPLNT_ID"], EMPTY)
    assert {item.token for item in audit.unknown_tokens} == {"TXN", "APPLNT", "ID"}
    assert audit.fully_known == 0


def test_a_missing_vocabulary_is_refused() -> None:
    """A governed verb with no governed vocabulary is a contradiction."""
    with pytest.raises(ConfigurationError, match="GovernedDictionary"):
        audit_identifiers(CORPUS, None)


def test_a_policy_that_rejects_unknown_tokens_is_refused() -> None:
    """It would stop at the first token the audit exists to report.

    Refused up front rather than allowed to raise part-way through, because a
    ``LexiconError`` out of an audit tells the caller that the corpus has at
    least one gap when what they asked was how many.
    """
    with pytest.raises(ConfigurationError, match="REJECT"):
        audit_identifiers(CORPUS, NDS, NamingPolicy(unknown=UnknownPolicy.REJECT))


def test_a_negative_example_cap_is_refused() -> None:
    """Zero is the way to ask for no examples; below zero means nothing."""
    with pytest.raises(ConfigurationError, match="max_examples"):
        audit_identifiers(CORPUS, NDS, max_examples=-1)


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------
def test_the_report_holds_every_corpus_level_count() -> None:
    """A view, not a summary that leaves something out.

    Every count on the audit appears in the text, so a reader who has the report
    does not have to go back to the payload to answer an obvious question.
    """
    report = render_audit(AUDIT, limit=None)
    for value in (
        AUDIT.total,
        AUDIT.distinct,
        AUDIT.fully_known,
        AUDIT.partially_known,
        AUDIT.compliant,
        AUDIT.non_compliant,
        AUDIT.empty,
        AUDIT.round_trip_stable,
        AUDIT.round_trip_corrected,
        AUDIT.round_trip_inconsistent,
        AUDIT.ordinal_occurrences,
    ):
        assert str(value) in report
    for item in AUDIT.unknown_tokens:
        assert item.token in report
    for item in AUDIT.findings:
        assert item.code.value in report


def test_the_report_is_plain_ascii() -> None:
    """So it survives a log file, a CI pane and a Windows console equally."""
    report = render_audit(AUDIT)
    report.encode("ascii")
    assert not report.endswith("\n")


def test_the_report_says_when_it_truncated_a_table() -> None:
    """A silently shortened list reads as a complete one."""
    assert "further token" in render_audit(AUDIT, limit=1)
    assert "further" not in render_audit(AUDIT, limit=None)


def test_the_report_of_a_clean_corpus_says_there_is_nothing_to_do() -> None:
    """An empty table is a result and should read as one."""
    report = render_audit(audit_identifiers(["TXN_APPLNT_ID"], NDS))
    assert "none: the vocabulary covered every token" in report
    assert "none: every identifier in the corpus is compliant" in report
    assert "none over the names in this corpus" in report


def test_the_report_names_a_short_form_the_catalog_already_has() -> None:
    """The rows a team can clear with an edit rather than a decision."""
    audit = audit_identifiers(["CUSTOMER_ACCOUNT_IDENTIFIER"], NDS)
    lines = [line for line in render_audit(audit).splitlines() if "CUSTOMER" in line]
    assert any("CUST" in line for line in lines)


def test_the_report_shows_a_broken_round_trip_in_full() -> None:
    """Both halves of the disagreement, because one of them is not readable alone."""
    audit = audit_identifiers(["ACCT_BAL_AM"], NDS, custom={"AC": ALIAS})
    report = render_audit(audit)
    assert "AC_BAL_AM" in report
    assert "ACCT_BAL_AM" in report


# --------------------------------------------------------------------------
# The wire shape
# --------------------------------------------------------------------------
def test_the_audit_serialises_to_json_with_enums_as_strings() -> None:
    """The payload crosses a process boundary, so this is the surface that matters."""
    payload = AUDIT.to_dict()
    assert payload["findings"][0]["code"] == "unapproved_abbrev"
    assert isinstance(payload["unknown_tokens"][0]["examples"], list)
    assert AUDIT.to_json().startswith("{")


def test_every_model_is_frozen_and_forbids_unknown_fields() -> None:
    """The house rule for an audit record: it cannot be edited after it is handed out.

    Asserted through behaviour rather than through a declaration. These are
    frozen dataclasses, so "frozen" means an assignment raises and "forbids
    unknown fields" means the constructor refuses a keyword it does not declare
    — which is what a caller actually meets, and it stays the right test however
    the records are built.
    """
    for model in (CorpusAudit, CatalogSuggestion):
        assert model.__dataclass_params__.frozen is True, f"{model.__name__} is not frozen"
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            model(nope=1)  # type: ignore[call-arg]
    with pytest.raises(FrozenInstanceError):
        AUDIT.total = 1  # type: ignore[misc]
