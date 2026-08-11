"""The edges of :mod:`acronymkit.governed`: what happens to input nobody meant.

The acceptance gate in ``tests/test_governed.py`` drives a golden replay set over
names a governed standard would recognise. This file is the other half: the
names a schema export actually hands a pipeline. A column whose name carries an
emoji pasted out of a spreadsheet, a currency sign, a decomposed accent, a
control character from a bad extract, a quoted SQL identifier, a qualified path,
an ordinal, two hundred characters of one word, no letters at all.

Why these are worth their own file
----------------------------------
Every case here was found by probing rather than by reading the code, and each
one was decided on its merits before being written down. Some were bugs and are
fixed; the rest are behaviours that looked surprising, turned out to be right,
and are pinned so that "right" does not quietly become "whatever the code does
this month". A test that records a decision is worth as much as a test that
catches a regression, and the two are the same test.

**The headline was a bug.** ``split_identifier`` treated every character that is
neither a letter nor a digit as a separator, and a separator disappears. So
``TXN_<emoji>_ID`` expanded to "Transaction Identifier" with
``is_fully_known=True`` — a confident, complete-looking answer produced by
discarding part of the name it was asked about. For a tool that tells a
governance function what a database column means, that is the one failure mode
worse than saying "I do not know": it is not recoverable, because nothing
downstream can tell it from an answer.

The fix draws a line between the characters a physical name is *made of* —
``_``, ``-``, ``.``, ``/``, whitespace, and the quoting the SQL dialects wrap an
identifier in — and everything else, which is now reported on
``IdentifierExpansion.unaccounted`` and makes ``is_fully_known`` false. The
guarantee that replaces the old silence is asserted here with Hypothesis, over
arbitrary text, as a counting equation: every character of the input is either
inside a token, or one of the accounted separators, or reported.

The vocabulary below is a miniature of the fictional **Northwind Data
Standards** (``NDS``) catalog the rest of the suite uses, with synthetic entry
ids. It is written inline rather than loaded from the fixture corpus because
every assertion in this file is about the *splitting and accounting*, and a
four-line catalog keeps each expectation readable next to the input that
produced it. Nothing here describes a real organisation's naming standard.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from acronymkit.governed import (
    ComplianceReasonCode,
    ExpansionSource,
    GovernedDictionary,
    IdentifierExpansion,
    expand_identifier,
    expand_token,
    is_compliant,
    normalize,
)
from acronymkit.governed.tokenizer import (
    ACCOUNTED_SEPARATORS,
    IdentifierParts,
    split_identifier,
    split_identifier_parts,
    strip_qualifier,
)

# --------------------------------------------------------------------------
# A miniature catalog
# --------------------------------------------------------------------------
#: Enough governed vocabulary to make a phrase, and no more. Every token here
#: also carries an allow-list entry, so a name built from them is compliant and
#: a failure in these tests is about the input rather than about the catalog.
NDS = GovernedDictionary.from_mapping(
    {
        "TXN": "Transaction",
        "ID": "Identifier",
        "DT": "Date",
        "NM": "Name",
        "ADDR": "Address",
        "QTR": "Quarter",
        "PARTY": "Party",
        "STATE": "State",
    },
    approved_abbreviations=["TXN", "ID", "DT", "NM", "ADDR", "QTR", "PARTY", "STATE"],
    class_words={"ID": "Identifier", "DT": "Date", "NM": "Name"},
)

#: Characters that are none of: a letter, a digit, an accounted separator. Each
#: is a real thing that has arrived in a column name — an emoji pasted from a
#: spreadsheet, the sign on a currency column, a copyright mark from a header
#: row, a hash from a temp-table convention, and a control byte from an export
#: that went through the wrong encoding. Written as escapes throughout this file:
#: two of the cases below turn on the difference between two spellings that look
#: identical, and one of them is a combining mark with no glyph of its own.
UNACCOUNTABLE = ["\U0001f600", "\u20ac", "\u00a9", "#", "\x00"]


# --------------------------------------------------------------------------
# The headline: characters are no longer lost in silence
# --------------------------------------------------------------------------
@pytest.mark.parametrize("character", UNACCOUNTABLE, ids=lambda c: f"U+{ord(c):04X}")
def test_a_character_the_tokenizer_cannot_read_is_reported_not_discarded(character: str) -> None:
    """The bug this file exists for: the phrase was right and the answer was not.

    ``TXN_<x>_ID`` still expands to "Transaction Identifier", because that *is*
    what the two tokens mean and inventing a word for ``<x>`` would be the guess
    this package refuses. What changed is that the result no longer claims to be
    a complete account of the name: the character is listed, and
    ``is_fully_known`` says false, so a pipeline gating on that one bit routes
    the row to a person instead of writing "fully known" beside a name nobody
    wrote.
    """
    result = expand_identifier(f"TXN_{character}_ID", NDS)

    assert result.phrase == "Transaction Identifier"
    assert result.unaccounted == (character,)
    assert result.is_fully_known is False
    assert result.unknown_tokens == (), "no token failed; the name did"


@pytest.mark.parametrize("character", UNACCOUNTABLE, ids=lambda c: f"U+{ord(c):04X}")
def test_an_unreadable_character_still_separates(character: str) -> None:
    """Reporting it does not mean keeping it, and keeping it would be worse.

    A token is a lookup key. Gluing a stray character onto one turns a name the
    catalog knows into a name it does not, which is exactly the failure the wide
    separator set was written to prevent — so the character still ends the token
    it interrupts. Both halves matter: it separates *and* it is reported.
    """
    parts = split_identifier_parts(f"TXN{character}ID")

    assert parts.tokens == ("TXN", "ID")
    assert parts.unaccounted == (character,)


def test_an_identifier_made_only_of_unreadable_characters_is_not_vacuously_known() -> None:
    """The empty-input case and the everything-was-junk case are different.

    ``expand_identifier("")`` reports ``is_fully_known`` true vacuously, because
    nothing failed to resolve. A name consisting of one emoji tokenises to
    nothing too, and inheriting that verdict would be the worst reading in the
    file: a name that is entirely a character the splitter could not read,
    answered "fully known" with an empty phrase.
    """
    result = expand_identifier("\U0001f600", NDS)

    assert result.tokens == ()
    assert result.phrase == ""
    assert result.unaccounted == ("\U0001f600",)
    assert result.is_fully_known is False

    empty = expand_identifier("", NDS)
    assert empty.unaccounted == ()
    assert empty.is_fully_known is True


def test_every_occurrence_is_listed_in_input_order() -> None:
    """Two of the same character are two findings, not one.

    ``unaccounted`` is the accounting, not a set of what was seen: the counting
    guarantee below is stated in multiplicities, and a caller reconstructing what
    it sent needs the same character twice when it sent it twice.
    """
    parts = split_identifier_parts("\u20acTXN\u00a9ID\u20ac")

    assert parts.tokens == ("TXN", "ID")
    assert parts.unaccounted == ("\u20ac", "\u00a9", "\u20ac")


def test_expand_token_has_nothing_to_account_for() -> None:
    """One token is looked up whole, so nothing can fall out of it.

    ``expand_token`` does no splitting: an unreadable character stays inside the
    lookup key, the key matches no row, and the token is reported unknown. There
    is no third outcome to report and no ``unaccounted`` field on the result.
    """
    expansion = expand_token("TX\U0001f600N", NDS)

    assert expansion.raw == "TX\U0001f600N"
    assert expansion.is_known is False
    assert expansion.source is ExpansionSource.PASSTHROUGH


# --------------------------------------------------------------------------
# The guarantee, over arbitrary text
# --------------------------------------------------------------------------
#: Arbitrary text, plus text drawn from an alphabet packed with the characters
#: that drive the rules: the named separators, SQL quoting, digits, both cases, a
#: cased letter with an accent, a caseless letter, a combining mark and two
#: characters that belong to no class this module names.
_EDGE_CHARS = "aZ9_-./ \"'`[]\u00e9\u4e2d\u0301\u20ac\U0001f600"
ANY_TEXT = st.one_of(st.text(max_size=60), st.text(alphabet=_EDGE_CHARS, max_size=40))


@settings(max_examples=400, deadline=None)
@given(ANY_TEXT)
def test_nothing_leaves_without_being_kept_or_reported(text: str) -> None:
    """The losslessness guarantee, as an equation over every character.

    For any string at all: a character that is not one of the separators this
    module accounts for occurs in the tokens plus the unaccounted list exactly as
    many times as it occurs in the input, and a character that *is* accounted for
    occurs in neither. Nothing is invented, nothing is duplicated, and nothing is
    dropped in silence.

    Stated as counts rather than as a rejoin because the splitter does not record
    *where* the separators were, so the input is not reconstructible character by
    character — and the honest guarantee is the one that can be checked rather
    than the one that reads best.
    """
    tokens, unaccounted = split_identifier_parts(text)
    joined = "".join(tokens)

    for character in set(text):
        seen = joined.count(character) + unaccounted.count(character)
        if character in ACCOUNTED_SEPARATORS or character.isspace():
            assert seen == 0, f"accounted separator {character!r} survived the split"
        else:
            assert seen == text.count(character), f"{character!r} was lost or invented"


@settings(max_examples=400, deadline=None)
@given(ANY_TEXT)
def test_the_reported_characters_are_never_ones_that_could_have_been_a_token(text: str) -> None:
    """Nothing that belongs in a word is filed as junk.

    ``unaccounted`` is a work queue for a person, and a letter or a digit landing
    on it would mean the splitter had thrown away material a catalog row could
    have answered for. The two lists answer two different questions and this is
    the line between them.
    """
    for character in split_identifier_parts(text).unaccounted:
        assert not character.isalpha(), f"{character!r} is a letter and belongs in a token"
        assert not character.isdigit(), f"{character!r} is a digit and belongs in a token"


@settings(max_examples=400, deadline=None)
@given(ANY_TEXT)
def test_the_two_splitters_return_the_same_tokens(text: str) -> None:
    """The cheap call and the lossless one differ in what they report, not in what they find.

    ``split_identifier`` is what the compliance and reverse directions call, and
    a second implementation of the boundary rules that agreed with the first on
    the fixture corpus and diverged somewhere else would be the worst possible
    outcome of adding the accounting.
    """
    assert split_identifier(text) == split_identifier_parts(text).tokens


@settings(max_examples=300, deadline=None)
@given(ANY_TEXT)
def test_a_fully_known_identifier_accounted_for_all_of_itself(text: str) -> None:
    """``is_fully_known`` is a claim about the whole name, not about the tokens it kept.

    This is the property the reported bug violated, asserted over arbitrary text
    rather than over the five characters that happened to be probed.
    """
    result = expand_identifier(text, NDS)

    if result.is_fully_known:
        assert result.unaccounted == ()
        assert all(token.is_known for token in result.tokens)
    else:
        assert result.unaccounted or not all(token.is_known for token in result.tokens)


# --------------------------------------------------------------------------
# Ordinals
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("1ST_TXN_DT", ("1ST", "TXN", "DT")),
        ("2ND_QTR_DT", ("2ND", "QTR", "DT")),
        ("3RD_PARTY_ID", ("3RD", "PARTY", "ID")),
        ("4TH_QTR_DT", ("4TH", "QTR", "DT")),
        ("21ST_TXN_DT", ("21ST", "TXN", "DT")),
        ("1st_txn_dt", ("1st", "txn", "dt")),
        ("ADDR1ST", ("ADDR", "1ST")),
    ],
)
def test_an_ordinal_suffix_stays_with_its_digits(
    identifier: str, expected: tuple[str, ...]
) -> None:
    """``1ST`` is one word, and the letter/digit rule read alone cut it in half.

    The old split produced ``1|ST``, which asked the catalog about ``ST`` — a
    token no standard carries in that position — and rendered the phrase "1 St".
    Real column names carry ordinals, so the rule earns its place: the suffix set
    is closed, it is matched without regard to case, and it fires only where the
    two letters end the token.
    """
    assert split_identifier(identifier) == expected


@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("1STATE_CD", ("1", "STATE", "CD")),
        ("1STDay", ("1", "ST", "Day")),
        ("1MM", ("1", "MM")),
        ("7Code", ("7", "Code")),
        ("address2line1", ("address", "2", "line", "1")),
        ("ISO8601Date", ("ISO", "8601", "Date")),
    ],
)
def test_the_ordinal_rule_does_not_reach_past_the_suffix(
    identifier: str, expected: tuple[str, ...]
) -> None:
    """Two letters that merely *start* like an ordinal are not one.

    ``1STATE`` runs on past the suffix and nothing in the string says where the
    writer meant the word to break, so joining ``1`` to the first two letters of
    a longer word would invent a boundary rather than find one. The letter/digit
    rule is otherwise untouched, ``1MM`` included — its repair is still the
    dictionary-aware second pass, and still only where a catalog vouches for it.
    """
    assert split_identifier(identifier) == expected


def test_an_ordinal_is_a_token_the_catalog_can_be_asked_about() -> None:
    """The point of the rule, end to end.

    An ordinal nothing governs is still reported unknown, which is the honest
    answer — but it is reported unknown as ``1ST``, which is a row somebody can
    write, rather than as ``ST``, which is a word the column does not contain.
    """
    result = expand_identifier("1ST_TXN_DT", NDS)

    assert result.phrase == "1st Transaction Date"
    assert [token.raw for token in result.unknown_tokens] == ["1ST"]
    assert result.is_fully_known is False
    assert result.unaccounted == ()


def test_a_separator_still_keeps_an_ordinal_apart() -> None:
    """The rule does not reach across a boundary somebody wrote themselves."""
    assert split_identifier("ADDR_1_ST") == ("ADDR", "1", "ST")


def test_a_lower_then_upper_ordinal_suffix_is_not_one() -> None:
    """``1sT`` is ``1|s|T``, because the writer's own capital says so.

    Rule 6 does not fire across a camelCase boundary. Nobody writes an ordinal
    with a case change inside it, and reading a capital after a lowercase letter
    as a word break is the judgement rule 3 makes about every other string.

    The alternative was tried and is what the property below rules out: joining
    the digit to the lowercase letter emitted the token ``1s``, and ``1S`` splits
    back into two.
    """
    assert split_identifier("1sT") == ("1", "s", "T")
    assert normalize("1sT", NDS) == "1_S_T"
    assert normalize(normalize("1sT", NDS), NDS) == "1_S_T"


# --------------------------------------------------------------------------
# A token has to survive being upper-cased
# --------------------------------------------------------------------------
#: ASCII, and the restriction is the point rather than an oversight — see the
#: test below for why the property is false outside it.
ASCII_TEXT = st.one_of(
    st.text(alphabet=st.characters(max_codepoint=127), max_size=60),
    st.text(alphabet="Aa1SsTtNnDdRrHh_", max_size=24),
)


@settings(max_examples=400, deadline=None)
@given(ASCII_TEXT)
def test_an_ascii_token_upper_cased_splits_back_to_exactly_itself(text: str) -> None:
    """The property ``normalize``'s idempotence rests on.

    ``normalize`` rebuilds a name by upper-casing the tokens the splitter found
    and joining them with ``_``, and the second pass splits that result again. So
    "idempotent by construction" is only sound while the splitter reads its own
    upper-cased output the way it read the input. A token whose upper-cased form
    splits into two makes a name that changes every time it is normalised, which
    is what an ordinal suffix written ``1sT`` used to produce.

    ASCII only. Upper-casing is not length-preserving in Unicode and can even
    introduce characters that are not letters — ``"\\u0390".upper()`` is a
    capital iota followed by two combining marks, and a combining mark is
    unaccounted — so the property is genuinely false outside ASCII, and the test
    below pins the exception rather than hiding it.
    """
    for token in split_identifier(text):
        upper = token.upper()
        assert split_identifier(upper) == (upper,), f"{token!r} -> {upper!r}"


def test_normalize_is_not_idempotent_when_upper_casing_creates_a_combining_mark() -> None:
    """The one exception, pinned so the invariant is read with its limit attached.

    U+0390 is a single lowercase letter whose upper-case form is three characters
    — a capital iota and two combining marks — and a combining mark is not a
    letter, so the splitter reports it as unaccounted and the second pass drops
    it. ``normalize`` therefore moves twice for this input.

    Nothing here shortens a name on purpose, and this is not that: it is
    ``str.upper`` producing characters no token can hold. Fixing it would mean
    either normalising Unicode (which rewrites text, and the tokenizer refuses
    to) or declining to upper-case a word, and both are worse than saying where
    the invariant stops.
    """
    # Written as escapes: the point of the case is that one character becomes
    # three, and two of the three have no glyph of their own.
    letter = "\u0390"  # GREEK SMALL LETTER IOTA WITH DIALYTIKA AND TONOS
    iota = "\u0399"  # GREEK CAPITAL LETTER IOTA
    marks = ("\u0308", "\u0301")  # combining diaeresis, combining acute
    once = normalize(letter, NDS)
    twice = normalize(once, NDS)

    assert letter.upper() == iota + "".join(marks)
    assert once == letter.upper()
    assert twice == iota
    assert expand_identifier(once, NDS).unaccounted == marks


# --------------------------------------------------------------------------
# Qualified names
# --------------------------------------------------------------------------
def test_a_qualified_path_brings_its_qualifier_into_the_phrase() -> None:
    """Today's behaviour, pinned deliberately rather than fixed.

    ``.`` is an ordinary separator in a physical name — ``nds.risk-model`` is one
    name with a dot in it — so nothing in ``db.schema.TXN_ID`` distinguishes a
    qualifier from part of the name. A splitter that assumed one would be
    guessing about a caller's naming convention, which is the thing this package
    does not do, so the parents stay in the phrase and the caller who knows
    better says so.
    """
    result = expand_identifier("db.schema.TXN_ID", NDS)

    assert result.phrase == "Db Schema Transaction Identifier"
    assert [token.raw for token in result.tokens] == ["db", "schema", "TXN", "ID"]


@pytest.mark.parametrize(
    ("qualified", "leaf"),
    [
        ("db.schema.TXN_ID", "TXN_ID"),
        ("TXN_ID", "TXN_ID"),
        ("[db].[TXN_ID]", "[TXN_ID]"),
        ("TXN_ID.", "TXN_ID"),
        ("a.b.", "b"),
        ("...", "..."),
        ("", ""),
        (None, ""),
    ],
)
def test_strip_qualifier_returns_the_leaf(qualified: str, leaf: str) -> None:
    """The opt-in the caller applies when they know the input is a path.

    Empty segments are skipped, so a trailing dot cannot swallow the name, and an
    input with no non-empty segment comes back unchanged rather than as ``""`` —
    losing a whole name to a punctuation accident is the failure this package
    exists to avoid, and there is no honest leaf to return instead.
    """
    assert strip_qualifier(qualified) == leaf


def test_the_leaf_of_a_qualified_path_expands_on_its_own() -> None:
    """Composing the helper with the verb is the whole of the supported route.

    No verb applies :func:`strip_qualifier` for the caller. That keeps the five
    verbs one shape, and keeps the decision — "these dots are a path" — with the
    only party that has the evidence for it.
    """
    result = expand_identifier(strip_qualifier("db.schema.TXN_ID"), NDS)

    assert result.phrase == "Transaction Identifier"
    assert result.is_fully_known is True


# --------------------------------------------------------------------------
# SQL quoting
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "quoted",
    ['"TXN_ID"', "[TXN_ID]", "`TXN_ID`", "'TXN_ID'", '"TXN"."ID"'],
    ids=["ansi", "t-sql", "mysql", "apostrophe", "ansi-qualified"],
)
def test_a_quoted_identifier_reads_as_the_bare_one(quoted: str) -> None:
    """Load-bearing for anything sourced from a catalog query, and untested until now.

    A name that made a round trip through ``information_schema`` comes back
    quoted, and it is the same name. The quoting characters separate, they are
    discarded, and — this is the half worth pinning — they are **not** reported
    as unaccounted, so a schema read out of the database does not arrive with
    every row flagged.
    """
    result = expand_identifier(quoted, NDS)

    assert result.phrase == "Transaction Identifier"
    assert result.unaccounted == ()
    assert result.is_fully_known is True


def test_the_accounted_separators_are_the_published_ones() -> None:
    """The set is part of the contract, because the guarantee is stated against it.

    A caller checking losslessness for itself has to know where the line is
    drawn, and a port has to reproduce it. Whitespace is accounted for too and is
    not listable, which is why the constant carries the punctuation only.
    """
    assert frozenset("_-./\"'`[]") == ACCOUNTED_SEPARATORS


# --------------------------------------------------------------------------
# Unicode spelling
# --------------------------------------------------------------------------
def test_a_composed_accent_is_part_of_its_letter_and_is_not_normalised() -> None:
    """``CLIENT`` spelled with an accent keeps the accent, in the token and in the phrase.

    The splitter applies no NFKC, no case folding and no accent stripping, and
    the reason is sharper than consistency with ``acronymkit.tokenizer`` — which
    normalises to build a *matching key* and keeps the surface form beside it.
    NFKC rewrites text: it turns a ligature into two letters and a Roman numeral
    into Latin capitals. A normalising splitter would return tokens that are not
    substrings of the identifier, ``raw`` would stop showing the token as the
    schema spelled it, and the counting guarantee would have nothing to count.
    """
    parts = split_identifier_parts("CLI\u00c9NT_NM")

    assert parts.tokens == ("CLI\u00c9NT", "NM")
    assert parts.unaccounted == ()
    assert expand_identifier("CLI\u00c9NT_NM", NDS).phrase == "Cli\u00e9nt Name"


def test_a_decomposed_accent_is_reported_rather_than_lost() -> None:
    """The same name in NFD form is a different name here, and says so.

    A combining mark is not a letter, so it cannot join a token and it cannot be
    a word. Under the old rule it vanished and ``CLIENT`` arrived as two junk
    tokens with nothing to say why. It is now reported, which is the signal a
    caller needs to normalise upstream — where the rewrite is visible and where
    the decision about which normal form a catalog is written in belongs.

    This is a limit stated honestly rather than a behaviour to admire: the tokens
    are still cut in the wrong place. What changed is that the result no longer
    hides it.
    """
    parts = split_identifier_parts("CLIE\u0301NT_NM")

    assert parts.tokens == ("CLIE", "NT", "NM")
    assert parts.unaccounted == ("\u0301",)
    assert expand_identifier("CLIE\u0301NT_NM", NDS).is_fully_known is False


def test_a_caseless_script_still_forms_tokens() -> None:
    """A letter with no case of its own is a letter, and is never junk.

    CJK, Hebrew and Devanagari take part in the letter/digit rules and in nothing
    else, because a case boundary is meaningless next to a character that has no
    case to change. Refusing such a name, or filing it as unreadable, would be
    enforcing an alphabet rather than a naming convention.
    """
    parts = split_identifier_parts("TXN_\u4e2d\u6587_ID")

    assert parts.tokens == ("TXN", "\u4e2d\u6587", "ID")
    assert parts.unaccounted == ()


# --------------------------------------------------------------------------
# Shape and size
# --------------------------------------------------------------------------
def test_a_very_long_token_is_neither_split_nor_clipped() -> None:
    """No length anywhere in this package is a boundary or a truncation.

    A two-hundred character word is one token, expands to one Title Cased word,
    and comes back whole. Length is a *finding* under ``strict_length`` and
    nothing else; a splitter with an opinion about it would be inventing a
    boundary at whatever position the limit happened to fall.
    """
    word = "X" * 200
    parts = split_identifier_parts(f"{word}_ID")

    assert parts.tokens == (word, "ID")
    assert expand_identifier(f"{word}_ID", NDS).tokens[0].raw == word


@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("A", ("A",)),
        ("1", ("1",)),
        ("_", ()),
        ("123456", ("123456",)),
        ("2024", ("2024",)),
        ("TXN_TXN_TXN", ("TXN", "TXN", "TXN")),
        ("__TXN__ID__", ("TXN", "ID")),
        ("_TXN_ID", ("TXN", "ID")),
        ("TXN_ID_", ("TXN", "ID")),
        ("TXN___ID", ("TXN", "ID")),
        ("  TXN  ID  ", ("TXN", "ID")),
    ],
)
def test_degenerate_shapes_behave_sanely(identifier: str, expected: tuple[str, ...]) -> None:
    """A single character, all digits, repeats, and separators in every position.

    None of these was wrong; all of them are the kind of input a schema export
    produces at three in the morning, and none of them had a test. Runs of
    separators collapse, leading and trailing ones contribute no empty token, a
    repeated token is repeated rather than deduplicated — the tokens are the
    name, not a set of the words in it — and nothing here raises.
    """
    assert split_identifier(identifier) == expected


def test_an_all_digit_identifier_is_a_token_the_catalog_is_silent_about() -> None:
    """Digits are tokens, and a catalog that says nothing about them says so.

    ``2024`` expands to itself, unknown, with zero confidence. That is the
    passthrough contract doing its job on input that is not a word: the fix, if a
    caller wants one, is an allow-list entry or ``custom=``, and the report is
    what tells them a fix is needed.
    """
    result = expand_identifier("2024", NDS)

    assert [token.raw for token in result.tokens] == ["2024"]
    assert result.tokens[0].is_known is False
    assert result.tokens[0].confidence == 0.0
    assert result.is_fully_known is False
    assert result.unaccounted == ()


def test_a_repeated_token_resolves_the_same_way_every_time() -> None:
    """Context-free means context-free: position cannot change an answer.

    The same token three times over is three identical records. This is the
    property that makes the subsystem usable across a million-row table, and it
    is cheap to assert exactly once.
    """
    result = expand_identifier("TXN_TXN_TXN", NDS)

    assert result.phrase == "Transaction Transaction Transaction"
    assert len({token.long for token in result.tokens}) == 1
    assert len({token.source for token in result.tokens}) == 1


# --------------------------------------------------------------------------
# The DTO contract
# --------------------------------------------------------------------------
def test_unaccounted_defaults_to_empty_for_a_caller_that_never_heard_of_it() -> None:
    """The field is additive, and existing constructions keep working.

    The golden fixtures, and any consumer that builds an ``IdentifierExpansion``
    of its own, predate this field. It has a default for that reason: adding a
    required field to a published DTO would be a breaking change dressed up as a
    bug fix.
    """
    expansion = IdentifierExpansion(
        identifier="TXN_ID",
        phrase="Transaction Identifier",
        tokens=(),
        class_word=None,
        is_fully_known=True,
    )

    assert expansion.unaccounted == ()
    assert expansion.to_dict()["unaccounted"] == []


def test_unaccounted_serialises_last_and_as_an_array() -> None:
    """Key order is the wire contract, so a new field goes on the end.

    The JSON contract in ``docs/notes/governed-json-contract.md`` numbers every
    field and a port emits them in that order. Appending leaves the existing
    numbering alone; inserting would renumber four fields to no purpose.
    """
    payload = expand_identifier("TXN_\U0001f600_ID", NDS).to_dict()

    assert list(payload) == [
        "identifier",
        "phrase",
        "tokens",
        "class_word",
        "is_fully_known",
        "unaccounted",
    ]
    assert payload["unaccounted"] == ["\U0001f600"]


def test_identifier_parts_unpacks_as_a_pair() -> None:
    """The tokenizer's result is a plain named tuple, and stays one.

    ``tokens, unaccounted = split_identifier_parts(name)`` is the ergonomics this
    buys, and the reason it is not a Pydantic model: this module is imported by
    every verb in the package and is the one part of the subsystem that costs
    nothing to import. Validating a pair of string tuples would buy no safety and
    would put a schema build in front of every caller that only wanted to split a
    name.
    """
    parts = split_identifier_parts("TXN_ID")
    tokens, unaccounted = parts

    assert isinstance(parts, IdentifierParts)
    assert isinstance(parts, tuple)
    assert (tokens, unaccounted) == (("TXN", "ID"), ())


# --------------------------------------------------------------------------
# What the other verbs do with the same input
# --------------------------------------------------------------------------
def test_the_compliance_direction_does_not_carry_the_accounting() -> None:
    """A gap, recorded rather than papered over.

    ``ComplianceResult`` has no field for an unaccounted character, so a name
    carrying one fails for the reason it *also* fails — it is not upper-snake —
    and the suggested fix is the name with the character gone. That is a
    defensible correction and it is visible, but it is visible as a casing
    finding rather than as what it is, and ``normalize`` applies it without
    comment. Closing the gap means a reason code and a field on a DTO this change
    did not touch; until then the behaviour is pinned so it cannot drift while
    nobody is looking.
    """
    result = is_compliant("TXN_\U0001f600_ID", NDS)

    assert result.compliant is False
    codes = [reason.code for reason in result.reasons if reason.verdict.value == "fail"]
    assert codes == [ComplianceReasonCode.NOT_UPPER_SNAKE]
    assert [reason.fix for reason in result.reasons if reason.fix] == ["TXN_ID"]
    assert normalize("TXN_\U0001f600_ID", NDS) == "TXN_ID"


def test_a_quoted_name_normalises_to_the_bare_one() -> None:
    """The corrected form of a quoted identifier is the identifier.

    Which is the other reason the quoting characters are accounted for rather
    than reported: this rewrite is not a loss, it is the point of asking.
    """
    assert normalize('"txn_id"', NDS) == "TXN_ID"
    assert normalize("[txn_id]", NDS) == "TXN_ID"
