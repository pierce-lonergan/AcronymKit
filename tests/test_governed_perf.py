"""The two shortcuts :mod:`acronymkit.governed` takes, and the proof they are free.

Nothing in this file times anything. Wall-clock budgets belong in ``bench/``,
where the environment is pinned and dispersion is reported; what belongs here is
the *correctness* of two optimisations whose whole justification is that they
change no answer, and which would otherwise be tested only by the suites they are
invisible to.

The two shortcuts
-----------------
**An ASCII identifier is split by a regular expression** rather than by the
character-by-character scan the tokenizer's rules are written as. That is two
readings of one set of rules, and a second reading that agreed with the first on
the fixture corpus and diverged somewhere else would be the worst outcome
available — a splitter is the one component here whose mistakes no catalog row
can repair. So the two are run against each other over arbitrary ASCII text and
over every string up to length four in the alphabets where the rules interact.
When they disagree the scan is right, by definition; the test says so.

**A resolved token is remembered on the dictionary that resolved it.** A memo is
a wrong answer waiting to happen if any part of its key is dropped, so each part
is checked on its own: the same token under two policies, the same token with and
without a call-time overlay, the same token before and after ``with_custom``, and
a token whose policy is supposed to *raise* rather than answer. The memo also has
to stay bounded and has to stay out of the way of the unknown-token contract,
both of which are asserted here rather than assumed — and, since it is the one
thing in this package written to after construction, several threads are pointed
at one dictionary and every answer they get is compared against the answer a
dictionary nothing had warmed gave.

The vocabulary is a miniature of the fictional **Northwind Data Standards**
(``NDS``) catalog with synthetic ids, written inline so each expectation reads
next to the rows that produced it. Nothing here describes a real organisation's
standard.
"""

from __future__ import annotations

import itertools
import random
import string
import threading

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from acronymkit.exceptions import LexiconError
from acronymkit.governed import (
    ExpansionSource,
    GovernedDictionary,
    NamingPolicy,
    UnknownPolicy,
    expand_identifier,
    expand_token,
    is_compliant,
)
from acronymkit.governed.dictionary import _MEMO_LIMIT, _MEMO_POLICY_LIMIT
from acronymkit.governed.tokenizer import _scan, split_identifier, split_identifier_parts

# --------------------------------------------------------------------------
# A miniature catalog
# --------------------------------------------------------------------------
#: Small enough to read, and carrying the one row whose answer depends on the
#: policy: ``ID`` is pinned to "Identifier" while its first declared candidate is
#: "Identity", so ``governed_default`` and ``frequency_baseline`` disagree about
#: it and a memo that ignored the policy would be caught by that disagreement.
NDS = GovernedDictionary.from_json(
    [
        {
            "token": "ID",
            "canonical": "Identifier",
            "candidates": ["Identity", "Identifier", "Idaho"],
            "pin": "Identifier",
            "kind": "ambiguous_pinned",
            "entry_id": "NDS-ID",
            "source": "pinned",
        },
        {
            "token": "TXN",
            "canonical": "Transaction",
            "kind": "approved_abbrev",
            "keep_as_abbrev": True,
            "entry_id": "NDS-TXN",
            "source": "governed",
        },
        {
            "token": "DT",
            "canonical": "Date",
            "kind": "class_word_abbrev",
            "class_word": "Date",
            "entry_id": "NDS-DT",
            "source": "governed",
        },
    ],
    approved_abbreviations=["TXN", "ID", "DT"],
    class_words={"DT": "Date"},
)


# --------------------------------------------------------------------------
# One set of rules, two readings of it
# --------------------------------------------------------------------------
#: ASCII text, plus text drawn from the alphabets where the splitting rules
#: interact: the ordinal suffixes in both cases, the case boundaries, the digits,
#: the named separators, SQL quoting and a character that belongs to no class the
#: tokenizer names.
ASCII_TEXT = st.one_of(
    st.text(alphabet=st.characters(max_codepoint=127), max_size=60),
    st.text(alphabet="Aa1SsTtNnDdRrHh_", max_size=24),
    st.text(alphabet="ABab019_-./\"'`[]# \t", max_size=40),
)


def _fast_and_slow(text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Run both readings of the rules over ``text``.

    Args:
        text: Any ASCII string.

    Returns:
        What the published functions answered and what the reference scan
        answered, in the same shape, ready to be compared.
    """
    parts = split_identifier_parts(text)
    tokens, unaccounted = _scan(text) if text else ([], [])
    return (parts.tokens, parts.unaccounted), (tuple(tokens), tuple(unaccounted))


@settings(max_examples=600, deadline=None)
@given(ASCII_TEXT)
def test_the_ascii_shortcut_answers_exactly_what_the_scan_answers(text: str) -> None:
    """The pattern and the scan are one set of rules, or the pattern is a bug.

    The published functions take a regular-expression path for ASCII input, which
    is very nearly all input. It cannot be derived from the character classifier
    the way the unaccounted-character class can, so it is checked against the
    scan instead — over arbitrary text rather than over names anybody would
    write, because agreement on realistic names is what a divergence would hide
    behind.
    """
    assert _fast_and_slow(text)[0] == _fast_and_slow(text)[1]


@pytest.mark.parametrize("alphabet", ["1SsTtNn_", "Aa1St#"])
def test_the_two_readings_agree_on_every_short_string_over_the_hard_alphabets(
    alphabet: str,
) -> None:
    """Exhaustive where the rules collide, because sampling can miss a corner.

    The ordinal exception is the one rule that reads two characters ahead, and it
    interacts with the camelCase rule, the acronym-run rule and the letter/digit
    rule at the same position. Four rules meeting on four characters is a small
    enough space to enumerate, so it is enumerated: every string up to length
    four over each alphabet, which is where a hand-written pattern goes wrong.
    """
    for length in range(1, 5):
        for combination in itertools.product(alphabet, repeat=length):
            text = "".join(combination)
            fast, slow = _fast_and_slow(text)
            assert fast == slow, f"{text!r}: pattern {fast}, scan {slow}"


def test_a_lower_then_upper_ordinal_suffix_is_not_an_ordinal() -> None:
    """``1sT`` is ``1|s|T``: rule 3 outranks rule 6, and it has to.

    A capital following a lowercase letter is the writer saying a new word starts
    there, and everywhere else in the tokenizer that signal *is* the boundary. So
    rule 6 does not fire across it, and the three other spellings — which nobody
    writes with a case change inside them — are ordinals as before.

    The condition is not a tie-break between two defensible answers. Letting rule
    6 fire here emitted the token ``1s``, and ``"1s".upper()`` is ``"1S"``, which
    splits back to two tokens — so ``normalize`` moved on every pass over a name
    containing one. The property that broke is asserted in
    ``tests/test_governed_edge_cases.py``. Both readings of the rules have to
    agree about this string either way, which is why the answer is pinned here
    rather than left to whichever path an input happens to take.
    """
    assert split_identifier("1sT") == ("1", "s", "T")
    assert split_identifier("1St") == ("1St",)
    assert split_identifier("1ST") == ("1ST",)
    assert split_identifier("1st") == ("1st",)


def test_a_non_ascii_identifier_still_goes_through_the_scan() -> None:
    """The shortcut is guarded on ``isascii``, and the guard is the whole of it.

    A name with a character outside ASCII takes the reference path, where the
    accounting for an unreadable character lives. Asserted through the published
    answer rather than by reaching for the branch: what matters is that the
    guarantee holds, not which code produced it.
    """
    parts = split_identifier_parts("TXN_€_ID")

    assert parts.tokens == ("TXN", "ID")
    assert parts.unaccounted == ("€",)


# --------------------------------------------------------------------------
# The memo cannot drop any part of its key
# --------------------------------------------------------------------------
def test_a_call_time_overlay_is_never_served_the_answer_from_underneath_it() -> None:
    """The failure a memo would cause, if it forgot that ``custom=`` had happened.

    Asked first without an overlay and then with one, on the same dictionary,
    inside one process. A memo keyed on the token alone would answer the second
    call with the first call's answer and be fast and wrong; ``custom=`` builds a
    different vocabulary, and a different vocabulary has its own memo.
    """
    catalog = GovernedDictionary.from_mapping({"TXN": "Transaction"})

    assert expand_token("TXN", catalog).long == "Transaction"
    assert expand_token("TXN", catalog, custom={"TXN": "Transmission"}).long == "Transmission"
    assert expand_token("TXN", catalog).long == "Transaction"


def test_the_overlay_answer_does_not_leak_back_the_other_way() -> None:
    """And the same in the other order, which is the one a warm cache reaches first."""
    catalog = GovernedDictionary.from_mapping({"TXN": "Transaction"})

    assert expand_token("TXN", catalog, custom={"TXN": "Transmission"}).long == "Transmission"
    assert expand_token("TXN", catalog).long == "Transaction"


def test_with_custom_does_not_inherit_what_the_dictionary_it_came_from_remembered() -> None:
    """A layered dictionary is a new vocabulary, so it starts having answered nothing."""
    base = GovernedDictionary.from_mapping({"TXN": "Transaction"})
    base.resolve("TXN")

    layered = base.with_custom({"TXN": "Transmission"})

    assert layered.resolve("TXN").canonical == "Transmission"
    assert base.resolve("TXN").canonical == "Transaction"


def test_two_policies_get_two_answers_for_one_token_in_either_order() -> None:
    """The policy is part of the key, and ``ID`` is the row that proves it.

    ``ID`` is pinned to "Identifier" and declares "Identity" first, so the
    governed policy and the frequency baseline disagree about it. Both orders are
    asserted, because a memo that dropped the policy would return whichever
    answer was asked for first and would look correct from the other direction.
    """
    governed = NamingPolicy.governed_default()
    baseline = NamingPolicy.frequency_baseline()

    forwards = GovernedDictionary.from_json([entry.to_dict() for entry in NDS.entries])
    assert forwards.resolve("ID", governed).canonical == "Identifier"
    assert forwards.resolve("ID", baseline).canonical == "Identity"

    backwards = GovernedDictionary.from_json([entry.to_dict() for entry in NDS.entries])
    assert backwards.resolve("ID", baseline).canonical == "Identity"
    assert backwards.resolve("ID", governed).canonical == "Identifier"


def test_a_policy_equal_to_the_last_one_shares_its_answers() -> None:
    """Matched by value, not by identity: ``policy=None`` builds a new default each call.

    Every verb defaults ``policy=None`` to a freshly constructed
    ``governed_default()``, so a memo that recognised only the same *object*
    would miss on every call a caller made without naming a policy. Equal
    policies are the same policy, and the answer is the same answer.
    """
    catalog = GovernedDictionary.from_mapping({"TXN": "Transaction"})

    first = catalog.resolve("TXN", NamingPolicy.governed_default())
    second = catalog.resolve("TXN", NamingPolicy())

    assert first is second


def test_more_policies_than_the_limit_still_answer_correctly() -> None:
    """Dropping every memo is allowed; answering from the wrong one is not."""
    catalog = GovernedDictionary.from_json([entry.to_dict() for entry in NDS.entries])
    policies = [
        NamingPolicy(max_name_length=length) for length in range(10, 10 + _MEMO_POLICY_LIMIT + 3)
    ]

    for policy in policies * 3:
        assert catalog.resolve("ID", policy).canonical == "Identifier"
    assert catalog.resolve("ID", NamingPolicy.frequency_baseline()).canonical == "Identity"


def test_a_reject_policy_still_raises_on_a_token_another_policy_expanded() -> None:
    """A memo must never answer a question that was supposed to stop the pipeline.

    ``UnknownPolicy.REJECT`` exists for a caller whose catalog being out of date
    is a reason to halt. The token is expanded first under the default policy, so
    that anything remembering passthroughs has had its chance to remember this
    one, and then asked again under the policy that must refuse it.
    """
    catalog = GovernedDictionary.from_mapping({"TXN": "Transaction"})
    reject = NamingPolicy(unknown=UnknownPolicy.REJECT)

    assert expand_token("KYC", catalog).is_known is False
    with pytest.raises(LexiconError, match="KYC"):
        expand_token("KYC", catalog, reject)


def test_the_surface_spelling_survives_a_second_call_with_a_different_one() -> None:
    """``raw`` reports what it was given, so the memo is keyed on what it was given.

    ``txn`` and ``TXN`` resolve to one catalog row and do not expand to one
    record: each reports the spelling the caller used. A memo keyed on the lookup
    key would hand the second caller the first caller's ``raw``.
    """
    catalog = GovernedDictionary.from_mapping({"TXN": "Transaction"})

    assert expand_token("TXN", catalog).raw == "TXN"
    assert expand_token("txn", catalog).raw == "txn"
    assert expand_token("Txn", catalog).long == "Transaction"


def test_an_unknown_token_is_reported_unknown_however_often_it_is_asked_about() -> None:
    """The passthrough contract does not soften on the second call.

    Passthroughs are deliberately not remembered — see ``_Memo`` — so this is
    also the assertion that the road not taken stays not taken: every call
    re-reaches the same answer rather than being served one.
    """
    catalog = GovernedDictionary.from_mapping({"TXN": "Transaction"})

    for _ in range(3):
        expansion = expand_token("KYC", catalog)
        assert (expansion.long, expansion.is_known, expansion.confidence) == ("Kyc", False, 0.0)
        assert expansion.source is ExpansionSource.PASSTHROUGH


def test_the_memo_holds_governed_answers_and_nothing_else() -> None:
    """The bound is structural: what is remembered is keyed by the vocabulary.

    A memo that also recorded misses would be keyed by whatever names the caller
    happened to have, which is the shape that grows without limit. Reaching into
    the memo is reaching into an implementation detail, and it is done here
    because "small" is the property being claimed and the only way to see it is
    to look.
    """
    catalog = GovernedDictionary.from_mapping({"TXN": "Transaction"})
    policy = NamingPolicy.governed_default()

    expand_identifier("_".join(f"ZZ{index}" for index in range(200)), catalog)
    memo = catalog._memo(policy)

    assert memo.resolved == {}
    assert memo.expanded == {}

    expand_identifier("TXN_TXN_TXN", catalog)

    assert list(memo.expanded) == ["TXN"]


def test_the_memo_stops_growing_at_its_limit() -> None:
    """A vocabulary larger than the limit, and the memo still fits in the limit.

    The limit is reachable two ways: a catalog with more rows than it, which is
    what is used here because it is the shorter test, or a caller sending enough
    distinct spellings of one token. Both are bounded by the same line, and what
    it has to hold is that answering stays correct across the boundary — a memo
    emptying itself must cost a recomputation and nothing else.
    """
    catalog = GovernedDictionary.from_mapping(
        {f"T{index:05d}": f"Term {index}" for index in range(_MEMO_LIMIT + 50)}
    )
    policy = NamingPolicy.governed_default()

    for index in range(_MEMO_LIMIT + 50):
        assert expand_token(f"T{index:05d}", catalog, policy).long == f"Term {index}"

    assert len(catalog._memo(policy).expanded) <= _MEMO_LIMIT
    assert len(catalog._memo(policy).resolved) <= _MEMO_LIMIT
    assert expand_token("T00000", catalog, policy).long == "Term 0"


def test_a_remembered_answer_is_the_same_answer_a_fresh_dictionary_gives() -> None:
    """The whole claim, end to end: warm and cold agree on every fixture name.

    Two dictionaries with the same rows, one asked about the corpus twice and one
    asked once, compared record by record. If the memo changed any answer — a
    class word, a provenance, a confidence, a beaten candidate — this is where it
    would show.
    """
    warm = GovernedDictionary.from_json([entry.to_dict() for entry in NDS.entries])
    names = ["TXN_ID", "txn_dt", "TXN_KYC_DT", "ID", "1ST_TXN_DT", "TXN_ID"]

    for name in names:
        warm_result = expand_identifier(name, warm)
        cold = GovernedDictionary.from_json([entry.to_dict() for entry in NDS.entries])

        assert warm_result == expand_identifier(name, cold)
        assert is_compliant(name, warm) == is_compliant(name, cold)


def test_the_same_token_twice_is_the_same_object_twice() -> None:
    """The memo is meant to be there, and this is the only way to see it without a clock.

    Identity is not part of the published contract — the models are frozen and
    equal ones are interchangeable — so this is the one assertion in the suite
    that looks at it, and it looks at it to catch the memo silently ceasing to
    work rather than to fix an object graph.
    """
    catalog = GovernedDictionary.from_mapping({"TXN": "Transaction"})
    result = expand_identifier("TXN_TXN", catalog)

    assert result.tokens[0] is result.tokens[1]
    assert expand_identifier("TXN", catalog).tokens[0] is result.tokens[0]


# --------------------------------------------------------------------------
# The reverse index's early rejection
# --------------------------------------------------------------------------
def test_a_phrase_longer_than_every_long_form_is_refused_and_a_short_one_is_not() -> None:
    """``abbreviate`` measures before it normalises, and measuring decides nothing else.

    The reverse direction asks about every run of words in a name, so most of
    what it asks about is far too long to be a catalog term. Rejecting on length
    is exact rather than approximate for ASCII text — collapsing whitespace only
    shortens a string and folding an ASCII letter keeps its length — so the
    shortcut can only ever refuse phrases the index does not hold.
    """
    catalog = GovernedDictionary.from_mapping({"TXN": "Transaction"})

    assert catalog.abbreviate("Transaction").token == "TXN"
    assert catalog.abbreviate("  transaction  ").token == "TXN"
    assert catalog.abbreviate("Transaction Identifier Date Name") is None
    assert catalog.abbreviate("x" * 500) is None


@settings(max_examples=300, deadline=None)
@given(st.text(alphabet=string.ascii_letters + " \t", max_size=30))
def test_the_length_shortcut_never_refuses_a_phrase_the_index_holds(text: str) -> None:
    """The shortcut against the index it is a shortcut for, over arbitrary phrases.

    ``abbreviate`` must answer exactly what a lookup of the normalised key
    answers. Checked against the index itself rather than against a second
    implementation of the rejection rule, so the test cannot be wrong in the same
    way the code is.
    """
    from acronymkit.governed.dictionary import _phrase_key

    catalog = GovernedDictionary.from_mapping(
        {"TXN": "Transaction", "XREF": "Cross Reference", "AM": "Amount"}
    )
    expected = catalog._by_long_form.get(_phrase_key(text))

    assert catalog.abbreviate(text) is expected


def test_a_long_non_ascii_phrase_is_not_refused_on_length() -> None:
    """Case folding can lengthen a string, so the bound is claimed for ASCII only.

    ``ß`` folds to ``ss``, so a non-ASCII phrase can produce a key longer than
    itself and a length test on the phrase would refuse a term the index holds.
    Such a phrase takes the ordinary path.
    """
    catalog = GovernedDictionary.from_mapping({"STR": "Strasse"})

    assert catalog.abbreviate("Straße").token == "STR"


# --------------------------------------------------------------------------
# The memo under concurrent readers
# --------------------------------------------------------------------------
def test_one_dictionary_answers_the_same_under_several_threads() -> None:
    """Thread safety asserted rather than argued.

    The module docstring reasons about it — a memo is only ever added to or
    emptied, and the pair of "policy and its memo" is published as one tuple so a
    reader cannot see half of an update — and reasoning is what a race defeats.
    So the answers are computed once single-threaded on dictionaries nothing has
    warmed, and then eight threads hammer one shared dictionary with the policies
    interleaved, which is the arrangement that exercises the per-policy split, the
    identity fast path and the policy-limit clear all at once.

    A race here would not raise; it would return the other policy's answer. That
    is why every answer is compared rather than only checked for an exception.
    """
    names = ["TXN_ID", "ID", "txn_dt", "TXN_KYC_DT", "1ST_TXN_DT", "TXN_ID_DT"]
    policies = [
        NamingPolicy.governed_default(),
        NamingPolicy.frequency_baseline(),
        NamingPolicy.strict_length(),
        NamingPolicy(max_name_length=11),
        NamingPolicy(max_name_length=12),
        NamingPolicy(),
    ]
    rows = [entry.to_dict() for entry in NDS.entries]
    expected = {
        (index, name): expand_identifier(name, GovernedDictionary.from_json(rows), policy).to_dict()
        for index, policy in enumerate(policies)
        for name in names
    }

    shared = GovernedDictionary.from_json(rows)
    wrong: list[tuple[int, str]] = []

    def hammer(seed: int) -> None:
        generator = random.Random(seed)
        for _ in range(400):
            index = generator.randrange(len(policies))
            name = generator.choice(names)
            answer = expand_identifier(name, shared, policies[index]).to_dict()
            if answer != expected[(index, name)]:
                wrong.append((index, name))

    threads = [threading.Thread(target=hammer, args=(seed,)) for seed in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert wrong == []
