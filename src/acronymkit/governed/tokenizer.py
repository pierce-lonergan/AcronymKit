"""Identifier splitting — the one place this package judges English orthography.

What it does
------------
:func:`split_identifier` turns a physical name — ``TXN_APPLNT_DOB_DT``,
``creditBureauVendorCode``, ``address2line1`` — into the ordered surface tokens
that a governed lookup is then performed against. Expansion, class-word
detection and compliance checking are all loops over what this function returns.
:func:`split_identifier_parts` returns those same tokens *and* the characters
the splitter could not account for, which is what the losslessness guarantee
below is stated in terms of.

Everything else in this package can be re-derived from the catalog: if an answer
is wrong, the fix is a dictionary row. Not this. A boundary placed in the wrong
character position produces a token no catalog contains, and no amount of
governed vocabulary downstream can recover the word that was cut in half. It is
also the only function here that decides anything on its own — the rest of the
package is a lookup table with an audit trail wrapped around it.

The rules, in order
-------------------
1. ``None``, empty input and input consisting only of separators all yield
   ``()``. The function never raises. A blank cell in a schema export is a
   normal thing to be handed, and a splitter that threw on one would push a
   ``try`` into every caller.
2. Split on the named separators — ``_``, ``-``, ``.``, ``/`` and whitespace.
   Runs of separators collapse, so ``TXN__APPLNT`` and ``TXN_APPLNT`` split
   identically and a leading or trailing separator contributes no empty token.
3. Split camelCase boundaries **before** any case folding:
   ``creditBureauVendorCode`` → ``credit|Bureau|Vendor|Code``. The order matters
   and is the reason this function returns surface forms rather than upper-cased
   lookup keys. Case *is* the boundary information; fold first and
   ``creditBureauVendorCode`` becomes an unsplittable twenty-two character word.
   Upper-casing for lookup is the caller's business, and it is safe to do after.
4. Split acronym-run boundaries: ``ETLTimestamp`` → ``ETL|Timestamp``. Inside a
   run of capitals, a boundary goes before the *last* capital when a lowercase
   letter follows it, because that capital starts the next word rather than
   ending the acronym. Without this rule the run swallows the following word's
   initial and yields ``ETLT|imestamp``; with it, ``MDMHubID`` →
   ``MDM|Hub|ID``.
5. Split letter↔digit boundaries in both directions: ``address2line1`` →
   ``address|2|line|1``, ``7Code`` → ``7|Code``, ``ISO8601Date`` →
   ``ISO|8601|Date``. Digits in a physical name are ordinals and version
   markers, and they are word boundaries in both directions.
6. An English ordinal suffix stays with the digits it belongs to, as the one
   exception to rule 5: ``1ST_TXN_DT`` → ``1ST|TXN|DT``, not ``1|ST|TXN|DT``.
   Rule 3 wins over it: a suffix written lower-then-upper is two words by the
   writer's own capitalisation, so ``1sT`` is ``1|s|T``. See below.
7. Identifier quoting separates and is discarded without comment: the double
   quote, the apostrophe, the backtick and square brackets. See below.
8. Every other character that is neither a letter nor a digit separates too,
   and is **reported** rather than discarded. See below.
9. Digit-leading catalog tokens are **not** special-cased here. See below.

Rule 6 and the ordinals
-----------------------
``1ST``, ``2ND``, ``3RD`` and ``4TH`` are single words, and rule 5 read alone
cuts each of them in half — which produces the token ``ST``, which no catalog
carries, and the phrase "1 St", which is not what the column is called. The
suffix set is closed (``st``, ``nd``, ``rd``, ``th``), it is matched without
regard to case, and two conditions have to hold together.

**The two letters must end the token.** ``1STATE`` is still ``1|STATE``, because
the letters run on past the suffix and nothing says where the word was meant to
break.

**They must not straddle a camelCase boundary.** ``1sT`` is ``1|s|T``, not
``1s|T`` and not ``1sT``, because a capital following a lowercase letter is the
writer saying a new word starts there — and everywhere else in this module that
signal is what a boundary *is*. Rule 6 exists because ``1ST`` is one word;
nobody writes an ordinal as ``1sT``, and reading the writer's own capitalisation
as a word break is the same judgement rule 3 makes about every other string.
Letting rule 6 fire there produced the token ``1s``, whose upper-cased form
``1S`` splits back to ``1|S`` — so it was a token that was not stable under the
upper-casing every governed name goes through, which is what
:func:`~acronymkit.governed.compliance.normalize` rebuilds a name out of.

This is orthography, in the same sense rule 4 is, which is why it lives here and
not behind a dictionary. It is also English-only, and says so: a catalog whose
ordinals are written ``1ER`` or ``1E`` gets rule 5 and nothing else. The rule
does not reach across a separator either, so ``ADDR_1_ST`` keeps the two tokens
somebody wrote separately.

Rules 7 and 8: nothing is dropped without a signal
--------------------------------------------------
Rules 2 and 7 name every character this module discards quietly. Rule 2's are
the structure of a physical name and a caller who wrote ``TXN_ID`` does not need
to be told it contained an underscore; rule 7's are how the four common SQL
dialects quote an identifier, so ``"TXN_ID"``, ``[TXN_ID]`` and a backtick-quoted
name read exactly like the bare one. A name that made a round trip through a
catalog query is the same name.

Everything else is rule 8, and rule 8 is the point. An emoji pasted out of a
spreadsheet, a currency sign, a combining accent left behind by a decomposed
Unicode spelling, a control character from a bad export: each of those was part
of the name somebody wrote, none of them can be part of a token, and losing one
in silence turns a governance tool into a confident source of names nobody
wrote. They separate — gluing one to a token would turn a resolvable name into
an unknown — and each occurrence is recorded in
:attr:`IdentifierParts.unaccounted`.

**The guarantee, exactly.** For any input string, and for any character that is
not one of the accounted separators, the number of times that character occurs
in the input equals the number of times it occurs across the returned tokens
plus the number of times it appears in ``unaccounted``. Nothing is invented, and
nothing leaves without being either kept or reported.

An unaccounted character is deliberately *not* made into a token of its own.
A token is a lookup key and it is a word: it goes to the catalog, it comes back
``is_known=False`` when the catalog is silent, and that miss is a row somebody
owes. "This name contains a character I could not read" is a different fact from
"the catalog is missing a row", the second is fixable by writing the row and the
first is not, and a token list is also what ``normalize`` rebuilds a corrected
name out of. Keeping the two facts in two fields keeps the work queue clean.

Rule 9 and the two-pass join
----------------------------
Some governed catalogs contain a token that starts with a digit — ``1MM`` for a
one-million unit, ``2FA``, ``3DS``. Rule 5 splits ``1MM`` into ``1`` and ``MM``,
and there is nothing in the string ``1MM`` that says it should not: it has
exactly the shape of ``7Code``, which must split.

The repair belongs to the caller. ``expand_identifier`` makes a second,
dictionary-aware pass over this function's output: before expanding a digit
token it tries that token joined to the one after it as a lookup key, consumes
both when the joined form is a catalog entry, and otherwise falls back to the
split tokens exactly as they came. One literal pass, then one greedy pass —
hence "two-pass", and hence a joined token surviving only where a governed
vocabulary actually vouches for it.

Doing it here instead would mean a tokenizer that consults a dictionary, which
is not a tokenizer. Its output would stop being a function of its input: the
same identifier would split one way against a catalog holding ``1MM`` and
another way against a catalog that does not, a fixture recording its output
would be a fixture of somebody's vocabulary rather than of a splitter, and a
property test over arbitrary identifiers could assert nothing without first
pinning a dictionary. The boundary is worth stating because the temptation is
real — ``1MM`` is a token real catalogs really carry.

Qualified names keep their qualifier
------------------------------------
``.`` is a separator, so ``db.schema.TXN_ID`` splits to four tokens and expands
to a phrase that begins "Db Schema". That is the honest reading of the string on
its own: nothing in ``nds.risk-model`` says its dot introduces a leaf, and a
splitter that assumed one would be guessing about the caller's naming
convention. :func:`strip_qualifier` is there for the caller who *knows* their
input is a qualified path, and no verb applies it on the caller's behalf.

What it deliberately does not do
--------------------------------
No case folding, no Unicode normalisation, no accent stripping, no stemming, no
de-pluralisation, no dictionary. Tokens come back exactly as they appeared in
the input, in input order.

The normalisation question is worth answering rather than implying, because
``acronymkit.tokenizer`` does apply NFKC. It applies it to build a *matching
key* — ``surface`` is kept beside it, untouched — and the governed subsystem's
matching key is ``dictionary._token_key``, not this function's output. So the
two splitters already agree: neither normalises what it returns. Here the reason
is sharper than symmetry. NFKC rewrites text — it turns a ligature into two
letters and a Roman numeral into Latin capitals — so a normalising splitter
would return tokens that are not substrings of the identifier, ``raw`` would
stop showing the token as the schema actually spelled it, and the counting
guarantee above would have nothing left to count. A caller whose source emits
decomposed spellings should normalise upstream, where the change is visible;
until then a combining mark arrives here as an unaccounted character and is
reported as one.

Two readings of an ASCII name, and why there are two
----------------------------------------------------
Splitting is the largest single cost in expanding an identifier, and a
character-by-character Python loop is an expensive way to spend it on the shape
of name a schema actually holds. So an all-ASCII identifier — which is very
nearly every identifier — is tokenised by :data:`_ASCII_TOKEN`, one call into the
regex engine, and everything else goes through :func:`_scan`, which is the
reference reading of the rules and is what the rules above describe.

That is two implementations of one set of rules, which is exactly the drift this
module warns about everywhere else, so it is worth saying what is done about it.
Rules 2, 7 and 8 — which characters are separators, which are quoting, which are
reported — still have exactly one statement: :func:`_classify`, from which the
pattern that finds unaccounted characters is *derived* at import. Rules 3 to 6 —
where a boundary falls inside a run of letters and digits — genuinely are stated
twice, once as a loop and once as a pattern, and a pattern cannot be derived from
a loop. What keeps them honest is a property test that runs both readings over
arbitrary ASCII text, plus an exhaustive check over the alphabets where the rules
interact; agreement on the fixture corpus alone would not be evidence. If the two
ever disagree, :func:`_scan` is right by definition and the pattern is the bug.

Determinism and purity
----------------------
Pure standard library, no I/O, no clock, no randomness, no module state, no
configuration. The output depends on the argument and nothing else, which is
what makes these functions safe to property-test and safe to share across
threads.

Vocabulary note: worked examples use the fictional **Northwind Data Standards**
catalog (``NDS``) and generic industry tokens (``TXN``, ``APPLNT``, ``DT``).
Nothing here describes a real organisation's schema.
"""

from __future__ import annotations

import re
from typing import NamedTuple, Optional

__all__ = [
    "ACCOUNTED_SEPARATORS",
    "IdentifierParts",
    "split_identifier",
    "split_identifier_parts",
    "strip_qualifier",
]


#: Punctuation this module discards without reporting it: the four named
#: separators of rule 2 and the identifier quoting of rule 7. Every Unicode
#: whitespace character — anything ``str.isspace`` accepts — is accounted for
#: too, and is not listable here. Published because it is the other half of the
#: losslessness guarantee: a character outside this set, and outside whitespace,
#: is either inside a token or inside ``unaccounted``, and a caller checking that
#: for itself needs to know where the line is drawn.
ACCOUNTED_SEPARATORS = frozenset("_-./\"'`[]")

#: The closed set of English ordinal suffixes, lower-cased for comparison.
#: Rule 6 is exactly this set and nothing else; there is no morphology behind it
#: and there is not meant to be.
_ORDINAL_SUFFIXES = frozenset({"st", "nd", "rd", "th"})


# Character classes. Plain ints rather than an enum: this is an inner loop over
# every character of every identifier in a schema, and the classification is
# read three times per character (previous, current, lookahead). The two classes
# that close a token rather than joining one sort lowest, so "does this end a
# token" is one comparison.
_SEPARATOR = 0
_UNACCOUNTED = 1
_UPPER = 2
_LOWER = 3
_CASELESS = 4
_DIGIT = 5


def _classify(char: str) -> int:
    """Classify one character for the boundary rules.

    Anything that is neither a letter nor a digit separates. A token is about to
    be used as a dictionary lookup key and no catalog entry contains
    punctuation, so gluing a stray character onto a token would turn a
    resolvable name into an unknown.

    What such a character *also* does is split into two cases, and the split is
    the whole of this module's honesty. A separator the design names, or the
    quoting a SQL dialect wrapped the name in, carries no information a caller
    needs back: it is :data:`_SEPARATOR` and it disappears. Everything else — an
    emoji, a currency sign, a combining accent, a control character — was part
    of the name and is not part of any token, so it is :data:`_UNACCOUNTED`, it
    separates exactly the same way, and the scan records it. A stray comma from
    a hand-edited CSV of column names is the everyday case and is precisely the
    one worth a signal.

    Letters with no case of their own — CJK ideographs, Hebrew, Devanagari — get
    their own class instead of being folded into one of the cased ones. They take
    part in the letter/digit rules and in nothing else, because a case boundary
    is meaningless next to a character that has no case to change.

    Args:
        char: A single character.

    Returns:
        One of the module-level class constants.
    """
    if char.isupper():
        return _UPPER
    if char.islower():
        return _LOWER
    if char.isdigit():
        return _DIGIT
    if char.isalpha():
        return _CASELESS
    if char in ACCOUNTED_SEPARATORS or char.isspace():
        return _SEPARATOR
    return _UNACCOUNTED


#: Letter classes, for the rules that care that a character is a letter without
#: caring which case it is.
_LETTERS = (_UPPER, _LOWER, _CASELESS)

#: Every ASCII character rule 8 reports, as a character class, so that finding
#: them is one call into the regex engine rather than a loop. **Derived** from
#: :func:`_classify` at import rather than written out: which characters are
#: accounted for is stated once in this module and this is not a second
#: statement of it. The escaping matters — the set contains ``\``, ``^``, ``]``
#: and ``-``, each of which means something inside a class.
_ASCII_UNACCOUNTED = re.compile(
    "["
    + re.escape("".join(chr(code) for code in range(128) if _classify(chr(code)) == _UNACCOUNTED))
    + "]"
)

#: Rules 3 to 6 over ASCII, as one pattern. See "Two readings of an ASCII name"
#: in the module docstring for why a second statement of those rules is accepted
#: here and what is done to keep it honest.
#:
#: The alternatives are ordered, and the order is load-bearing:
#:
#: 1. **Rule 6, whole.** A digit run and an English ordinal suffix that ends the
#:    token are one word: ``1ST``, ``21st``, ``3Rd``. The lookahead is rule 6's
#:    first condition — the suffix must *end* the token, so ``1STATE`` is not an
#:    ordinal. A digit after the suffix is fine, and ends the token by rule 5.
#:    Rule 6's second condition is expressed by the alternation itself: the four
#:    spellings listed are upper-then-either and lower-then-lower, and the
#:    lower-then-upper spelling ``sT`` is deliberately absent, because a capital
#:    after a lowercase letter is a camelCase boundary and rule 3 keeps it.
#: 2. **Rule 5.** A digit run, which is a boundary in both directions.
#: 3. **Rule 4.** An acronym run: capitals not followed by a lowercase letter, so
#:    the last capital before a lowercase one starts the next word and
#:    ``ETLTimestamp`` is ``ETL|Timestamp`` rather than ``ETLT|imestamp``.
#: 4. **Rule 3.** A word: an optional leading capital and its lowercase tail.
#:
#: Nothing here matches a character that is not a letter or a digit, so a
#: separator, a quote or an unaccounted character ends a token by not being part
#: of one — which is what rules 2, 7 and 8 say it does.
_ASCII_TOKEN = re.compile(
    r"[0-9]+(?:S[Tt]|N[Dd]|R[Dd]|T[Hh]|st|nd|rd|th)(?![A-Za-z])"
    r"|[0-9]+"
    r"|[A-Z]+(?![a-z])"
    r"|[A-Z]?[a-z]+"
)


def _classes(identifier: str) -> list[int]:
    """Classify every character of ``identifier``.

    Args:
        identifier: A non-empty identifier.

    Returns:
        One class constant per character, in input order.
    """
    return [_classify(char) for char in identifier]


class IdentifierParts(NamedTuple):
    """Everything :func:`split_identifier_parts` found, kept apart by kind.

    A plain :class:`typing.NamedTuple` rather than one of the Pydantic models in
    :mod:`acronymkit.governed.models`: this module is imported by every verb in
    the package and by the compliance path in particular, and it is the one part
    of the subsystem that costs nothing to import. Validating a pair of string
    tuples would buy no safety here and would put the Pydantic schema build in
    front of every caller that only wanted to split a name.

    Attributes:
        tokens: The surface tokens, in input order, with their original casing —
            exactly what :func:`split_identifier` returns.
        unaccounted: Every character that ended up in no token and is not an
            accounted separator, one entry per occurrence, in input order. Empty
            for essentially every name a schema actually contains, which is what
            makes a non-empty one worth acting on.
    """

    tokens: tuple[str, ...]
    unaccounted: tuple[str, ...]


def _is_boundary(previous: int, current: int, following: int) -> bool:
    """Whether a token boundary falls immediately before the current character.

    Called only when a token is already open, so ``previous`` is never
    :data:`_SEPARATOR` or :data:`_UNACCOUNTED` — either of those closes the token
    itself and no boundary decision is needed after one.

    The ordinal exception of rule 6 is not applied here. It needs two characters
    of lookahead into the identifier rather than one class of it, and paying for
    that on every character to serve a rule that fires only after a digit would
    be the wrong trade; :func:`_closes_an_ordinal` is consulted by the scan
    instead, and only where this function has already said yes.

    Args:
        previous: Class of the preceding character.
        current: Class of the character being placed.
        following: Class of the next character, or :data:`_SEPARATOR` at the end
            of the input. Only the acronym-run rule looks ahead, and it needs
            exactly one character of lookahead: whether the capital being placed
            is the last of its run.

    Returns:
        ``True`` when the current character starts a new token.
    """
    if current == _DIGIT:
        return previous in _LETTERS
    if previous == _DIGIT:
        return current in _LETTERS
    if current == _UPPER:
        if previous == _LOWER:
            return True
        if previous == _UPPER:
            return following == _LOWER
    return False


def _closes_an_ordinal(identifier: str, classes: list[int], position: int) -> bool:
    """Whether an English ordinal suffix starts here and ends the token.

    Rule 6. Consulted only where the previous character is a digit and
    :func:`_is_boundary` has already found a letter/digit boundary, so the two
    characters read here are the start of what would otherwise become a new
    token.

    Three conditions are needed. The suffix must be one of the four — anything
    else after a digit is an ordinary boundary. It must be the end of the token,
    because ``1STATE`` and ``1STDay`` say nothing about where the writer meant
    the word to break and joining ``1`` to the first two letters of a longer word
    would invent one. And it must not be written lower-then-upper: a capital
    after a lowercase letter is a camelCase boundary, which is the writer saying
    a word starts there, so ``1sT`` is three tokens and not an ordinal.

    That last condition is rule 3 taking precedence over rule 6, and it is worth
    saying why rather than leaving it as a tie-break. Without it the scan emitted
    the token ``1s`` — rule 6 joined the digit to the lowercase letter and rule 4
    then cut before the capital — and ``"1s".upper()`` is ``"1S"``, which splits
    back to ``("1", "S")``. A token that does not survive upper-casing is a token
    :func:`~acronymkit.governed.compliance.normalize` cannot rebuild a name out
    of, and its idempotence is stated as holding by construction.

    Args:
        identifier: The whole input, read two characters forward from
            ``position``.
        classes: The per-character classes of ``identifier``.
        position: Index of the first letter after the digit run.

    Returns:
        ``True`` when the digits and these two letters are one word.
    """
    suffix = identifier[position : position + 2]
    # The length is checked rather than inferred from membership. Lower-casing is
    # not length-preserving in Unicode, so "one character whose lower-case form
    # is two" is a shape that exists, and reading classes[position + 1] off the
    # back of a set membership would be trusting the Unicode tables to keep it
    # out of this set.
    if len(suffix) != 2 or suffix.lower() not in _ORDINAL_SUFFIXES:
        return False
    if classes[position] == _LOWER and classes[position + 1] == _UPPER:
        return False
    after = position + 2
    return after >= len(classes) or classes[after] not in _LETTERS


def _scan(identifier: str) -> tuple[list[str], list[str]]:
    """Walk the input once, building the tokens and the unaccounted characters.

    The reference reading of every rule in this module, and the shared body of
    both public functions, so that the boundary rules and the accounting cannot
    drift apart into two readings of one string. An all-ASCII identifier is
    answered by :data:`_ASCII_TOKEN` instead, for speed; where that pattern and
    this function disagree, this function is right by definition.

    Args:
        identifier: A non-empty identifier.

    Returns:
        The tokens in input order, and the unaccounted characters in input
        order, one entry per occurrence.
    """
    classes = _classes(identifier)
    total = len(classes)
    tokens: list[str] = []
    unaccounted: list[str] = []
    current: list[str] = []
    previous = _SEPARATOR

    for position, char in enumerate(identifier):
        kind = classes[position]
        if kind <= _UNACCOUNTED:
            if kind == _UNACCOUNTED:
                unaccounted.append(char)
            if current:
                tokens.append("".join(current))
                current = []
            previous = _SEPARATOR
            continue
        following = classes[position + 1] if position + 1 < total else _SEPARATOR
        if (
            current
            and _is_boundary(previous, kind, following)
            and (previous != _DIGIT or not _closes_an_ordinal(identifier, classes, position))
        ):
            tokens.append("".join(current))
            current = []
        current.append(char)
        previous = kind

    if current:
        tokens.append("".join(current))
    return tokens, unaccounted


def split_identifier(identifier: Optional[str]) -> tuple[str, ...]:
    """Split a physical identifier into its surface tokens.

    Applies, in order: separator splitting, camelCase boundaries, acronym-run
    boundaries, letter/digit boundaries and the ordinal exception. See the module
    docstring for the rules and for why digit-leading catalog tokens such as
    ``1MM`` are the caller's problem rather than this function's.

    Characters that are neither letters, digits nor accounted separators end a
    token exactly as a separator does, and are not returned here.
    :func:`split_identifier_parts` returns them alongside the tokens, and is what
    a caller who must not lose part of a name should use.

    Args:
        identifier: A physical name — a column, table or attribute identifier.
            ``None``, ``""`` and separator-only strings are all valid input.

    Returns:
        The tokens in input order, with their original casing. Empty when the
        input holds no letters or digits. Never ``None``, and this function
        raises nothing for any string input.

    Example:
        >>> split_identifier("TXN_APPLNT_DOB_DT")
        ('TXN', 'APPLNT', 'DOB', 'DT')
        >>> split_identifier("creditBureauVendorCode")
        ('credit', 'Bureau', 'Vendor', 'Code')
        >>> split_identifier("ETLTimestamp")
        ('ETL', 'Timestamp')
        >>> split_identifier("address2line1")
        ('address', '2', 'line', '1')
        >>> split_identifier("7Code")
        ('7', 'Code')
        >>> split_identifier("1ST_TXN_DT")
        ('1ST', 'TXN', 'DT')
        >>> split_identifier("nds.risk-model / SCORE")
        ('nds', 'risk', 'model', 'SCORE')
        >>> split_identifier('"TXN_ID"'), split_identifier("[TXN_ID]")
        (('TXN', 'ID'), ('TXN', 'ID'))
        >>> split_identifier("1MM")  # rejoined later, by the caller, if the catalog has it
        ('1', 'MM')
        >>> split_identifier(None), split_identifier(""), split_identifier("___")
        ((), (), ())
    """
    if not identifier:
        return ()
    if identifier.isascii():
        return tuple(_ASCII_TOKEN.findall(identifier))
    return tuple(_scan(identifier)[0])


def split_identifier_parts(identifier: Optional[str]) -> IdentifierParts:
    """Split an identifier and report what could not be made into a token.

    The lossless form of :func:`split_identifier`, and the one to reach for when
    the answer is going to be acted on rather than displayed. The tokens are
    identical; what is added is the characters that were part of the name, are
    part of no token, and are not one of the separators this module accounts for.

    The guarantee it exists to make good on: for any character outside
    :data:`ACCOUNTED_SEPARATORS` and outside Unicode whitespace, its occurrences
    in the input are exactly its occurrences across ``tokens`` plus its
    occurrences in ``unaccounted``. A caller that reads both fields has seen
    every character it passed in.

    Args:
        identifier: A physical name. ``None``, ``""`` and separator-only strings
            are all valid input and yield two empty tuples.

    Returns:
        The tokens and the unaccounted characters, both in input order.

    Example:
        >>> split_identifier_parts("TXN_ID")
        IdentifierParts(tokens=('TXN', 'ID'), unaccounted=())
        >>> emoji = split_identifier_parts("TXN_\\U0001F600_ID")
        >>> emoji.tokens, emoji.unaccounted == ("\\U0001F600",)
        (('TXN', 'ID'), True)
        >>> split_identifier_parts("PAY\\u20acAMT").unaccounted == ("\\u20ac",)
        True
        >>> split_identifier_parts('"TXN_ID"').unaccounted
        ()
    """
    if not identifier:
        return IdentifierParts((), ())
    if identifier.isascii():
        # Two passes over the string, both in C. The second is skipped outright
        # for the overwhelmingly common name that has nothing to report, which
        # is why it is a search before it is a findall.
        found = (
            tuple(_ASCII_UNACCOUNTED.findall(identifier))
            if _ASCII_UNACCOUNTED.search(identifier) is not None
            else ()
        )
        return IdentifierParts(tuple(_ASCII_TOKEN.findall(identifier)), found)
    tokens, unaccounted = _scan(identifier)
    return IdentifierParts(tuple(tokens), tuple(unaccounted))


def strip_qualifier(identifier: Optional[str]) -> str:
    """Return the leaf of a dot-qualified name — the part after the last dot.

    ``db.schema.TXN_ID`` is a column called ``TXN_ID``, and a caller expanding it
    usually wants "Transaction Identifier" rather than "Db Schema Transaction
    Identifier". Nothing in the string says so, though: ``.`` is an ordinary
    separator in a physical name, and ``nds.risk-model`` is one name with a dot
    in it rather than a qualified path. **This function is for a caller who knows
    which of the two they have.** No verb in this package applies it, because
    applying it would mean deciding, on the caller's behalf and without evidence,
    that a dot introduces a leaf.

    Empty segments are skipped, so a trailing dot cannot silently swallow the
    name, and an input with no non-empty segment at all comes back unchanged
    rather than as ``""`` — losing the whole name to a punctuation accident is
    the failure this package exists to avoid, and there is no honest leaf to
    return.

    Args:
        identifier: A physical name, qualified or not. ``None`` and ``""``
            return ``""``.

    Returns:
        The last non-empty dot-separated segment, verbatim and with no
        normalisation, or the input unchanged when there is none.

    Example:
        >>> strip_qualifier("db.schema.TXN_ID")
        'TXN_ID'
        >>> strip_qualifier("TXN_ID")
        'TXN_ID'
        >>> strip_qualifier("[db].[TXN_ID]")
        '[TXN_ID]'
        >>> strip_qualifier("TXN_ID.")
        'TXN_ID'
        >>> strip_qualifier("...")
        '...'
        >>> strip_qualifier(None)
        ''
    """
    if not identifier:
        return ""
    segments = [segment for segment in identifier.split(".") if segment.strip()]
    return segments[-1] if segments else identifier
