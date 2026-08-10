"""Identifier splitting — the one place this package judges English orthography.

What it does
------------
:func:`split_identifier` turns a physical name — ``TXN_APPLNT_DOB_DT``,
``creditBureauVendorCode``, ``address2line1`` — into the ordered surface tokens
that a governed lookup is then performed against. Expansion, class-word
detection and compliance checking are all loops over what this function returns.

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
2. Split on ``_``, ``-``, ``.``, ``/`` and whitespace. Runs of separators
   collapse, so ``TXN__APPLNT`` and ``TXN_APPLNT`` split identically and a
   leading or trailing separator contributes no empty token.
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
6. Digit-leading catalog tokens are **not** special-cased here. See below.

Rule 6 and the two-pass join
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

What it deliberately does not do
--------------------------------
No case folding, no normalisation, no accent stripping, no stemming, no
de-pluralisation, no dictionary. Tokens come back exactly as they appeared in
the input, in input order, and concatenating them recovers the identifier minus
its separators. Anything that maps a token to a lookup key is a later step, and
keeping it later is what lets an audit record show the token as the schema
actually spelled it.

Determinism and purity
----------------------
Pure standard library, no I/O, no clock, no randomness, no module state, no
configuration. The output depends on the argument and nothing else, which is
what makes this function safe to property-test and safe to share across threads.

Vocabulary note: worked examples use the fictional **Northwind Data Standards**
catalog (``NDS``) and generic industry tokens (``TXN``, ``APPLNT``, ``DT``).
Nothing here describes a real organisation's schema.
"""

from __future__ import annotations

from typing import Optional

__all__ = ["split_identifier"]


# Character classes. Plain ints rather than an enum: this is an inner loop over
# every character of every identifier in a schema, and the classification is
# read three times per character (previous, current, lookahead).
_SEPARATOR = 0
_UPPER = 1
_LOWER = 2
_CASELESS = 3
_DIGIT = 4


def _classify(char: str) -> int:
    """Classify one character for the boundary rules.

    Separator status is decided by exclusion rather than by a list. The contract
    names ``_``, ``-``, ``.``, ``/`` and whitespace, and those are what appear in
    practice — but a token is about to be used as a dictionary lookup key, and
    every other punctuation mark that can reach this function (``#``, ``$``,
    ``(``, ``"``, a stray comma from a hand-edited CSV of column names) is a
    character no catalog entry contains. Gluing one onto a token turns a
    resolvable name into an unknown, so anything that is neither a letter nor a
    digit separates.

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
    return _SEPARATOR


#: Letter classes, for the rules that care that a character is a letter without
#: caring which case it is.
_LETTERS = (_UPPER, _LOWER, _CASELESS)


def _is_boundary(previous: int, current: int, following: int) -> bool:
    """Whether a token boundary falls immediately before the current character.

    Called only when a token is already open, so ``previous`` is never
    :data:`_SEPARATOR` — a separator closes the token itself and no boundary
    decision is needed after one.

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


def split_identifier(identifier: Optional[str]) -> tuple[str, ...]:
    """Split a physical identifier into its surface tokens.

    Applies, in order: separator splitting, camelCase boundaries, acronym-run
    boundaries and letter/digit boundaries. See the module docstring for the
    rules and for why digit-leading catalog tokens such as ``1MM`` are the
    caller's problem rather than this function's.

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
        >>> split_identifier("nds.risk-model / SCORE")
        ('nds', 'risk', 'model', 'SCORE')
        >>> split_identifier("1MM")  # rejoined later, by the caller, if the catalog has it
        ('1', 'MM')
        >>> split_identifier(None), split_identifier(""), split_identifier("___")
        ((), (), ())
    """
    if not identifier:
        return ()

    classes = [_classify(char) for char in identifier]
    total = len(classes)
    tokens: list[str] = []
    current: list[str] = []
    previous = _SEPARATOR

    for position, char in enumerate(identifier):
        kind = classes[position]
        if kind == _SEPARATOR:
            if current:
                tokens.append("".join(current))
                current = []
            previous = _SEPARATOR
            continue
        following = classes[position + 1] if position + 1 < total else _SEPARATOR
        if current and _is_boundary(previous, kind, following):
            tokens.append("".join(current))
            current = []
        current.append(char)
        previous = kind

    if current:
        tokens.append("".join(current))
    return tuple(tokens)
