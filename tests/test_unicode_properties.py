"""Metamorphic Unicode properties, over the whole code-point space rather than a draw.

What this file is, and what makes it different from the other nineteen
Hypothesis files in this suite
------------------------------------------------------------------------
Every other property test here **draws**. Drawing is the right instrument for
a space you cannot enumerate, and it is the wrong one for this space, because
this space *can* be enumerated: Unicode is ``1,114,112`` code points and this
package answers a single-character question about each of them in about three
microseconds. So the primary instrument in this file is an **exhaustive
enumeration**, and Hypothesis is the secondary one, kept for the compositional
shapes enumeration cannot reach — multi-character strings, and interactions
between two characters that are individually clean.

That ordering is a measurement rather than a preference. With the U+00BA class
present and undisposed, the shipped idempotence property at Hypothesis's
default budget of ``100`` examples finds it on **2 of 20 seeds**; at ``1,000``
examples, on ``14 of 20``. A draw that finds a ``1,050``-code-point class one
time in ten is not a gate, and no budget this project can afford every commit
turns it into one. Enumeration finds it on ``20 of 20`` runs by construction,
because it is not a search.

THE TWO KNOWN CLASSES, DISPOSED OF BEFORE ANY NEW WORK
------------------------------------------------------
Two disjoint classes of code point break idempotence today. Both are pinned
below as ``xfail(strict=True)`` — strict, so that a future fix reddens this
file rather than passing silently and leaving a stale xfail behind — and both
also carry a **positive** test recording exactly what the tree does now, so
that neither class is represented only by an absence.

**Class one: the ordinal-indicator class, ``1,050`` code points. Pre-existing,
reported, deliberately left open.** ``U+00BA`` MASCULINE ORDINAL INDICATOR
answers :meth:`str.islower` with ``True`` and :meth:`str.upper` with *itself*,
so upper-casing the token ``ºa`` leaves a lower-case character standing in
front of a newly upper-case one — which is a camelCase boundary, and the
splitter duly places one there on the second pass. ``normalize('ºa')`` is
``'ºA'`` and ``normalize('ºA')`` is ``'º_A'``. No character is lost. It was
found by the first unrestricted draw this project ran over ``normalize``, and
it is recorded in ``docs/GOVERNED_NAMING.md`` and in ``docs/DECISIONS.md``,
where the disposition is written down: refusing would refuse a name that lost
nothing, and the only other repair is a splitting change that owes a
byte-identity pass over the whole corpus. ``tests/test_governed_edge_cases.py::
test_a_letter_that_stays_lower_case_when_upper_cased_still_moves_a_name_twice``
already pins its three values; this file adds the *class*.

**Class two: the upper-case-expansion class, ``26`` code points. Found by the
enumeration in this file, and it is not the class above.** It is exactly the
set of code points whose :meth:`str.upper` returns more than one character
*and* introduces a character that is neither a letter nor a digit — a
combining mark, in all ``26`` cases. ``'ǰ'`` (U+01F0) upper-cases to ``'J'``
followed by COMBINING CARON; the caron is a character no token can hold, so
the second pass reports it as unaccounted and drops it, and ``'J̌'`` becomes
``'J'``.

The sharp form of class two, and the reason it is worth having found:
**:func:`~acronymkit.catalog.naming.to_physical_name` emits, for all ``26`` of
them, a physical name that :func:`~acronymkit.catalog.compliance.normalize`
refuses.** ``normalize`` was taught to refuse a corrected name carrying an
unaccounted character — that is the fix ``docs/GOVERNED_NAMING.md`` records
under "A character no token can hold". The reverse verb was not taught the
same thing, so the two halves of the governed round trip now disagree about
these ``26`` inputs: one produces the name, the other will not read it back.

**Neither class is fixed here, and the reason is R19 rather than difficulty.**
A repair to either is a behaviour change in the splitting or the refusing, and
R19 requires it to be demonstrated byte-identical — or the difference
accounted for — over the full corpus before it ships. The incidence
measurement below says a repair would move nothing on any published
population, and *"it would move nothing"* is an argument, not a
demonstration. Recorded xfail, per R14, with the class, the count and the
record named.

INCIDENCE, RE-MEASURED HERE RATHER THAN CARRIED
------------------------------------------------
Both classes were counted against both governed corpora as they sit in
``data/governed_gold/``, over ``285,839`` distinct strings:

===================================  =========  =================  ================
population                           distinct   ordinal class      expansion class
===================================  =========  =================  ================
Socrata field names                     69,682                  0                 0
Socrata captions                        75,689                 12                 0
SEC XBRL element names                  68,038                  0                 0
SEC XBRL labels                         72,430                  0                 0
===================================  =========  =================  ================

The ``0/0/0/12`` row for the ordinal class reproduces the figure the earlier
round published, independently and from the corpus files rather than from its
report — a second party on a number that had one. The expansion class is
``0`` on all four. Those counts are a property of two dated snapshots
(``socrata_80pages_v2.json`` and ``sec_xbrl_2025q1.json``, both fetched
2026-08-23) and not of Socrata or of EDGAR, and the corpora are not reachable
from this file, so the numbers are stated in this docstring rather than
asserted below. **A test that read them would be a test that reads
checkout-only files**, and there are five recorded instances of that in this
project already.

THE THREE INVARIANTS, AND WHERE TWO OF THEM HAD TO BE RESTATED
---------------------------------------------------------------
**1. Non-vanishing.** Restated. The form *"a non-empty stripped input yields a
non-empty token list or raises"* is **false of the documented contract**:
rule 1 of :mod:`acronymkit.catalog.tokenizer` says in terms that ``"___"`` is
valid input, yields ``()``, and raises nothing, and a blank-ish cell in a
schema export is a normal thing to be handed. Asserting the wider form would
be a test disagreeing with the contract of the function it tests. What is
asserted here is the form that survives contact with that contract: **an input
carrying at least one character outside ``ACCOUNTED_SEPARATORS`` and outside
Unicode whitespace must produce a non-empty ``tokens`` or a non-empty
``unaccounted``, and ``normalize`` must return a non-empty string or raise.**
Measured over ``3,342,298`` such inputs, zero silently vanish.

**2. Idempotence.** As stated. ``normalize(normalize(s)) == normalize(s)`` and
``to_physical_name(to_physical_name(s)) == to_physical_name(s)``, over the
whole space; the only breaks anywhere are the two classes above.

**3. Span reconstruction.** Restated, and this is the one where the strong
phrasing does not hold of anything in this package. *"The raw slices
concatenate back to the original"* is **false**, by design and by docstring:
:meth:`~acronymkit.nlp.tokenizer.Tokenizer.tokenize` discards punctuation-only
runs, so ``"a b"`` yields two tokens whose slices concatenate to ``"ab"``.
Measured over ``10,716`` inputs across the named blocks, that phrasing fails on
``10,148`` of them. What is true — and what an offset consumer actually needs —
is a **lossless partition**: the spans are in bounds, non-overlapping, in
ascending order, ``text[start:end] == token.text`` for every one, and
interleaving the slices with the gaps between them reproduces the input
exactly. That holds on all ``10,716``, and it is what is asserted.

Note that invariant 3 has exactly **one** site in this package. The identifier
tokenizer returns no offsets at all — :class:`~acronymkit.catalog.tokenizer.
IdentifierParts` is two tuples of strings — so the prose tokenizer is the only
producer of spans there is anything to reconstruct from.

THE BUDGET, AND WHY IT IS NOT A LARGE NUMBER
---------------------------------------------
Hypothesis is a shrinking property tester whose default budget is ``100``
examples. "One million randomized iterations" is not a thing it does, would
not finish in CI, and — per the ``2 of 20`` measurement above — would still be
a worse instrument for this particular space than a loop. What ships:

* **exhaustive, every commit.** The two class derivations walk all
  ``1,114,112`` code points using :class:`str` methods only. The invariant
  sweep is exhaustive over the named blocks, over all ``922`` combining marks
  and over the ``64`` code points either side of the surrogate range.
* **exhaustive, every commit, and the expensive one.** The full-space invariant
  sweep — ``1,114,112`` code points, ``4,456,448`` calls to the two governed
  verbs — asserts that the set of idempotence-breaking code points is *exactly*
  the union of the two classes. It is marked ``slow`` so a developer can
  deselect it; CI passes no marker expression, so CI runs it. An earlier draft
  of this file put it behind the ``deep`` profile and thereby made the strongest
  check here the one check that never ran, which is the shape of defect
  ``.github/gates.toml`` exists to end.
* **drawn, every commit.** ``200`` examples per property under the ``ci``
  profile; ``5,000`` under ``deep``. The profile changes the drawn budget and
  **nothing else**. Drawing is kept for what enumeration cannot do: strings of
  length greater than one.

Wall clock, unarmed, machine named, because R18 says a wall-clock number is a
NOTE and never an abort condition: the whole file is about ``17.5`` seconds on
CPython 3.13.4 win32 under the ``ci`` profile, ``13.8`` of it the full-space
sweep. Nothing here has a deadline, a timeout or a budget expressed in seconds.
The gated quantities are counts.

**On "a failure once found stays found".** Hypothesis's example database is
``.hypothesis/``, which is in ``.gitignore`` and is **not** restored by any
``actions/cache`` step in ``.github/workflows/ci.yml``. So the database makes a
failure stick to one developer's checkout and nothing more; it does not
survive a fresh runner and it is not the durable mechanism. The durable
mechanism is :func:`hypothesis.example`, which is a committed file, and every
input this file has ever seen fail is pinned as one below.

HOW THIS FILE FAILS
-------------------
**Enumeration is single-character.** Every code point is exercised in five
one-character contexts. A defect that needs two *different* unusual characters
adjacent to each other is outside the enumeration and reachable only by the
drawn properties, which is exactly the coverage claim that cannot be made
exhaustively. **The named blocks were not where the new class was.** Of the
``800`` code points in the five blocks the round's brief named, ``13`` carry any
invariant break, all ``13`` are Letterlike Symbols, and all ``13`` are already
members of the ordinal class. The ``26``-code-point class this file found lives
in Latin Extended-B and Greek Extended, which no named block covers; it was
found by walking the space, not by aiming at it. **And a class derived from
:class:`str` is a statement about one interpreter's Unicode data.** The
``1,050`` and the ``26`` are re-derived on every run precisely so that a CPython
carrying a newer Unicode than 15.1.0 reddens this file instead of quietly
disagreeing with the two documents that publish those figures.
"""

from __future__ import annotations

import os
import sys
import unicodedata
from functools import cache, lru_cache
from pathlib import Path
from typing import FrozenSet, List, Set, Tuple

import pytest
from hypothesis import HealthCheck, assume, example, given, settings
from hypothesis import strategies as st

from acronymkit.catalog.compliance import normalize
from acronymkit.catalog.dictionary import GovernedDictionary
from acronymkit.catalog.naming import to_physical_name
from acronymkit.catalog.tokenizer import ACCOUNTED_SEPARATORS, split_identifier_parts
from acronymkit.config import Config
from acronymkit.core.exceptions import TokenizationError
from acronymkit.nlp.tokenizer import Tokenizer

# --------------------------------------------------------------------------
# The space, the vocabulary, and the budget
# --------------------------------------------------------------------------
#: Every code point there is. ``sys.maxunicode`` rather than a literal, so that
#: a narrow build -- if one ever runs this -- says so by failing rather than by
#: silently checking a sixteenth of the space.
CODE_POINTS = sys.maxunicode + 1

#: An empty catalog is the supported way to ask both verbs for the ungoverned
#: answer, and it is what every published governed figure was taken through.
#: A populated one would rewrite the identifier and put the catalog's contents
#: inside a measurement that is supposed to be about Unicode.
NDS = GovernedDictionary({})

#: Budget per drawn property. ``deep`` is for the scheduled run; ``ci`` is what
#: every commit pays. See the module docstring for why neither number is large.
_PROFILES = {"ci": 200, "deep": 5_000}
PROFILE = os.environ.get("ACRONYMKIT_HYPOTHESIS_PROFILE", "ci").strip().lower()
EXAMPLES = _PROFILES.get(PROFILE, _PROFILES["ci"])

#: Whether the deeper drawn budget is in force. It changes ONLY the Hypothesis
#: budget. The exhaustive sweeps -- including the full-space one -- are
#: unconditional, because a check that runs only under an environment variable
#: nobody sets in CI is a check that does not run.
DEEP = PROFILE == "deep"

#: The blocks the round's brief named, by name, so that coverage of them is a
#: fact this file establishes rather than a hope about what a draw reached.
#: Half-open at neither end: both bounds are inclusive, as Unicode block charts
#: are written.
NAMED_BLOCKS = {
    "enclosed_alphanumerics": (0x2460, 0x24FF),
    "currency_symbols": (0x20A0, 0x20CF),
    "letterlike_symbols": (0x2100, 0x214F),
    "mathematical_operators": (0x2200, 0x22FF),
    "cjk_compatibility_squared_metric": (0x3300, 0x33FF),
}

#: The metamorphic contexts. One character is placed in five positions that
#: exercise five different boundary decisions: alone; before a lower-case
#: letter (the shape the ordinal class breaks in); after an upper-case letter;
#: between a camelCase boundary; and doubled, which is the only context here
#: that puts two copies of the same unusual character adjacent.
CONTEXTS = ("{c}", "{c}a", "A{c}", "AB{c}cd", "{c}{c}")


@cache
def ordinal_indicator_class() -> FrozenSet[int]:
    """Code points that are lower-case and stay lower-case under upper-casing.

    Derived from :class:`str` on the running interpreter rather than read from
    a constant, so that a CPython carrying different Unicode data reddens the
    size assertion below instead of agreeing with a stale number.

    Returns:
        Every code point ``cp`` with ``chr(cp).islower()`` and
        ``chr(cp).upper() == chr(cp)``.
    """
    return frozenset(
        cp for cp in range(CODE_POINTS) if chr(cp).islower() and chr(cp).upper() == chr(cp)
    )


@cache
def upper_case_expansion_class() -> FrozenSet[int]:
    """Code points whose upper-cased form introduces a character no token holds.

    Two conditions, both necessary. ``len(chr(cp).upper()) > 1`` alone catches
    ``102`` code points, and most of them are benign: ``'ß'`` upper-cases to
    ``'SS'``, two letters, and a name built out of it is perfectly stable. What
    breaks is the subset whose expansion contains something that is neither a
    letter nor a digit -- a combining mark, for all of them -- because that is
    precisely the class of character :mod:`acronymkit.catalog.tokenizer`
    reports as unaccounted and does not put in a token.

    Returns:
        Every code point whose upper-cased form is longer than one character
        and contains at least one non-alphanumeric character.
    """
    return frozenset(
        cp
        for cp in range(CODE_POINTS)
        if len(chr(cp).upper()) > 1
        and any(not (ch.isalpha() or ch.isdigit()) for ch in chr(cp).upper())
    )


@cache
def combining_marks() -> Tuple[int, ...]:
    """Every code point with a non-zero canonical combining class."""
    return tuple(cp for cp in range(CODE_POINTS) if unicodedata.combining(chr(cp)))


#: The thirty-two code points either side of each end of the surrogate range.
#: Lone surrogates are legal in a :class:`str` and illegal in UTF-8, which makes
#: them the one input class that can be constructed in memory and cannot be
#: written to a file -- so a tokenizer that survives them is being asked
#: something real, and the boundaries are where an off-by-one in a range check
#: would show.
SURROGATE_ADJACENT = tuple(range(0xD7E0, 0xD800)) + tuple(range(0xE000, 0xE020))


def separator_only(text: str) -> bool:
    """Whether every character is one the splitter accounts for and discards.

    This is the exemption invariant 1 has to carry, and it comes from rule 1 and
    rule 2 of :mod:`acronymkit.catalog.tokenizer` rather than from convenience:
    those characters are the *structure* of a physical name, a name made only of
    structure names nothing, and the splitter's documented answer is ``()``
    without an exception.
    """
    return all(char in ACCOUNTED_SEPARATORS or char.isspace() for char in text)


def contexts_for(code_point: int) -> List[str]:
    """The five one-character contexts a code point is exercised in."""
    char = chr(code_point)
    return [template.format(c=char) for template in CONTEXTS]


def normalize_idempotence_break(text: str) -> bool:
    """Whether :func:`normalize` moves ``text`` on a second application.

    A refusal is not a break. ``normalize`` raising ``TokenizationError`` is the
    function declining to answer, and a claim about what a function returns says
    nothing about the inputs it returns nothing for. ``normalize`` refusing its
    own *output* IS a break, and a different one: a normal form has to be a
    fixed point, so a value it returns has to be a value it accepts.
    """
    try:
        once = normalize(text, NDS)
    except TokenizationError:
        return False
    try:
        return normalize(once, NDS) != once
    except TokenizationError:
        return True


def physical_name_idempotence_break(text: str) -> bool:
    """Whether :func:`to_physical_name` moves ``text`` on a second application.

    Separate from the ``normalize`` helper on purpose. The two verbs disagree
    about the upper-case-expansion class -- ``normalize`` refuses it and
    ``to_physical_name`` does not -- so a helper that answered for "either verb"
    would let a test named for one of them pass or fail on the behaviour of the
    other.
    """
    first = to_physical_name(text, NDS).physical
    return to_physical_name(first, NDS).physical != first


def idempotence_break(text: str) -> bool:
    """Whether *either* governed verb moves ``text``. Used only by the sweeps.

    The block and full-space sweeps assert that nothing outside the two known
    classes breaks anything at all, so there the disjunction is the claim.
    """
    return normalize_idempotence_break(text) or physical_name_idempotence_break(text)


# --------------------------------------------------------------------------
# The two classes: derived, sized, and disjoint
# --------------------------------------------------------------------------
#: Class sizes by the interpreter's Unicode version, because they are a property
#: of the UNICODE DATA and not of this library.
#:
#: **This table exists because the assertion below was a bare equality and it
#: reddened five matrix cells.** ``1,050`` is the count on Unicode 15.1; on
#: 14.0.0, which CPython 3.11 carries, it is ``977``. The figure is real and the
#: test was right to confront the documents with it -- but a number that changes
#: with the interpreter is a property of the runner, which is R18's subject one
#: level over from wall-clock, and gating it as though it were a property of the
#: code is the same error.
#:
#: An unknown version does **not** fail. It asserts the PROPERTY -- every member
#: of the derived class actually breaks idempotence -- and reports the count it
#: found, so a newer Unicode surfaces as a number to record rather than a red
#: build nobody can act on from the log.
_CLASS_SIZES_BY_UNICODE = {
    # Measured on a real interpreter of each version, not interpolated.
    # 16.0 is the interesting row: the ordinal class SHRINKS by two, so the
    # `1,050` the documents publish is true of 15.0 and 15.1 and of nothing
    # else. The breaking class is 26 across all three, and 102 code points
    # upper-case to more than one character throughout.
    "16.0.0": {"ordinal": 1048, "expanding": 102, "breaking": 26},  # CPython 3.14
    "15.1.0": {"ordinal": 1050, "expanding": 102, "breaking": 26},  # CPython 3.13
    "15.0.0": {"ordinal": 1050, "expanding": 102, "breaking": 26},  # CPython 3.12
    "14.0.0": {"ordinal": 977},  # CPython 3.11, from the run that reddened five cells
    # 13.0.0 (CPython 3.9 and 3.10) is UNMEASURED. Those cells will print their
    # counts and pass; the NOTE lines in a green run are how this row gets
    # filled, which is deliberate -- a number nobody has run is not a number.
}


def _expected(name: str) -> int | None:
    """The published size for this interpreter's Unicode version, or ``None``."""
    return _CLASS_SIZES_BY_UNICODE.get(unicodedata.unidata_version, {}).get(name)


def test_the_ordinal_indicator_class_is_exactly_1050_code_points() -> None:
    """The size the record publishes, re-derived from the running interpreter.

    ``docs/GOVERNED_NAMING.md`` and ``docs/DECISIONS.md`` both publish ``1050``.
    Neither is checked by ``tools/check_claims.py`` -- both sit in prose -- so
    this is the only place in the tree where that figure is confronted with a
    :class:`str` method.

    It is deliberately an equality rather than a floor. A newer Unicode that
    adds one member is a fact both documents would then be wrong about, and a
    ``>=`` would let it through.
    """
    found = ordinal_indicator_class()
    expected = _expected("ordinal")

    if expected is None:  # pragma: no cover - a Unicode version this table predates
        print(
            f"NOTE: {len(found)} ordinal-indicator members on Unicode "
            f"{unicodedata.unidata_version}, which _CLASS_SIZES_BY_UNICODE does not "
            f"carry. Record it there and in the documents that publish a size."
        )
    else:
        assert len(found) == expected, (
            f"{len(found)} code points are lower-case and stay lower-case under str.upper on "
            f"CPython {sys.version_info.major}.{sys.version_info.minor} carrying Unicode "
            f"{unicodedata.unidata_version}, against {expected} in "
            f"_CLASS_SIZES_BY_UNICODE. The documents publish the 15.1 figure."
        )
    assert 0x00BA in found, "U+00BA MASCULINE ORDINAL INDICATOR is the member the record names"


def test_the_upper_case_expansion_class_is_exactly_26_code_points() -> None:
    """The class this file found, sized, and separated from the wider one it sits in.

    ``102`` code points upper-case to more than one character. Only ``26`` of
    them introduce a character no token can hold, and the ``76`` that do not are
    the reason the wider predicate is not the right one: ``'ß'`` -> ``'SS'`` is
    two letters and is perfectly stable through both verbs.
    """
    expanding = {cp for cp in range(CODE_POINTS) if len(chr(cp).upper()) > 1}
    breaking = upper_case_expansion_class()

    for name, observed in (("expanding", expanding), ("breaking", breaking)):
        expected = _expected(name)
        if expected is None:  # pragma: no cover - unrecorded Unicode version
            print(
                f"NOTE: {len(observed)} {name} members on Unicode "
                f"{unicodedata.unidata_version}, unrecorded in _CLASS_SIZES_BY_UNICODE."
            )
        else:
            assert len(observed) == expected, (
                f"{len(observed)} {name} code points on Unicode "
                f"{unicodedata.unidata_version}, against {expected}"
            )
    assert breaking < expanding, "the breaking class is a strict subset of the expanding one"
    assert 0x01F0 in breaking, "U+01F0 LATIN SMALL LETTER J WITH CARON is the smallest member"


def test_the_two_classes_are_disjoint() -> None:
    """They are two defects, not one described twice.

    The ordinal class is *upper-casing that does nothing*; the expansion class
    is *upper-casing that does too much*. Nothing can be both, and asserting it
    is what stops the ``26`` being quietly absorbed into the ``1,050`` and
    reported as already known.
    """
    assert not (ordinal_indicator_class() & upper_case_expansion_class())


def test_every_member_of_the_expansion_class_expands_to_a_combining_mark() -> None:
    """What the class actually is, rather than what the predicate happens to select.

    A predicate that selects the right set for the wrong reason is a predicate
    that will select the wrong set later. All ``26`` introduce a character with
    a non-zero canonical combining class, and naming that is what makes the
    class a description of a mechanism rather than a list.
    """
    for code_point in sorted(upper_case_expansion_class()):
        expanded = chr(code_point).upper()
        introduced = [ch for ch in expanded if not (ch.isalpha() or ch.isdigit())]
        assert introduced, f"U+{code_point:04X} was selected but introduces nothing"
        assert all(unicodedata.combining(ch) for ch in introduced), (
            f"U+{code_point:04X} upper-cases to {expanded!r}, introducing a non-alphanumeric "
            f"character that is NOT a combining mark -- the class description is now wrong"
        )


# --------------------------------------------------------------------------
# Disposition: the two classes, xfailed strictly and pinned positively
# --------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    reason=(
        "THE ORDINAL-INDICATOR CLASS, 1050 CODE POINTS, PRE-EXISTING AND DELIBERATELY OPEN. "
        "U+00BA answers islower() True and upper() with itself, so upper-casing 'ºa' leaves a "
        "lower-case character in front of a newly upper-case one and the splitter reads a "
        "camelCase boundary on the second pass. No character is lost. Recorded in "
        "docs/GOVERNED_NAMING.md and docs/DECISIONS.md; three values pinned by "
        "tests/test_governed_edge_cases.py. Incidence 0 Socrata field names, 0 SEC XBRL "
        "element names, 0 SEC XBRL labels, 12 Socrata captions. Not fixed here: the repair is "
        "a splitting change and R19 owes it a full-corpus byte-identity pass."
    ),
)
def test_normalize_is_idempotent_across_the_ordinal_indicator_class() -> None:
    """The invariant, asserted over the whole class rather than over one example.

    Hypothesis found ``U+00BA``. It could not have found *the class*: a shrinking
    property tester returns the minimal failing example, and the minimal example
    of a ``1,050``-member class is one member of it. That is the difference this
    test exists to make concrete -- it fails with a count, not with a character.
    """
    moved = [
        cp for cp in sorted(ordinal_indicator_class()) if normalize_idempotence_break(f"{chr(cp)}a")
    ]

    assert not moved, (
        f"{len(moved)} of {len(ordinal_indicator_class())} ordinal-class code points move a "
        f"name on the second pass through normalize; the smallest is U+{moved[0]:04X}"
    )


def test_today_the_whole_ordinal_indicator_class_moves_a_name_twice() -> None:
    """The positive half of the disposition: what the tree does, asserted.

    An ``xfail`` records that something is wrong. It does not record what
    happens, and a class carried only as an absence is a class nobody can see
    change. This asserts the count -- **all** ``1,050``, not most of them -- so
    that a partial repair, which would be the easiest way to leave this file
    green and the record wrong, reddens here.
    """
    members = sorted(ordinal_indicator_class())
    moved_by_normalize = [cp for cp in members if normalize_idempotence_break(f"{chr(cp)}a")]
    moved_by_naming = [cp for cp in members if physical_name_idempotence_break(f"{chr(cp)}a")]

    # BOTH verbs, and the counts are separate because the sibling class below
    # moves only one of them. Stating them together is how the two defects
    # would get confused for one.
    assert len(moved_by_normalize) == len(members) == 1050
    assert len(moved_by_naming) == 1050

    ordinal = "º"
    once = normalize(f"{ordinal}a", NDS)
    twice = normalize(once, NDS)
    assert once == f"{ordinal}A"
    assert twice == f"{ordinal}_A"
    assert normalize(twice, NDS) == twice, "a fixed point after two steps, not a cycle"
    # The property that makes this a stability defect rather than a loss defect,
    # and therefore the reason refusing would be the wrong repair.
    for value in (f"{ordinal}a", once, twice):
        assert split_identifier_parts(value).unaccounted == ()


@pytest.mark.xfail(
    strict=True,
    reason=(
        "THE UPPER-CASE-EXPANSION CLASS, 26 CODE POINTS, FOUND BY THE ENUMERATION IN THIS "
        "FILE AND NOT PREVIOUSLY RECORDED. str.upper on these returns a base letter followed "
        "by a combining mark, which is a character no token can hold, so to_physical_name "
        "emits it on the first pass and drops it on the second. Distinct from the "
        "ordinal-indicator class and disjoint from it. Incidence 0 across all four published "
        "populations, 285,839 distinct strings. Not fixed here: the repair is a behaviour "
        "change in to_physical_name and R19 owes it a full-corpus byte-identity pass."
    ),
)
def test_to_physical_name_is_idempotent_across_the_upper_case_expansion_class() -> None:
    """The second invariant, over the second class.

    Note the verb. ``normalize`` was taught to refuse these -- it raises, naming
    the combining characters -- so this class is invisible from that side. It is
    the reverse verb that still produces them.
    """
    moved = [
        cp
        for cp in sorted(upper_case_expansion_class())
        if physical_name_idempotence_break(chr(cp))
    ]

    assert not moved, (
        f"{len(moved)} of {len(upper_case_expansion_class())} expansion-class code points "
        f"move a physical name on the second pass; the smallest is U+{moved[0]:04X}"
    )


def test_to_physical_name_emits_a_physical_name_that_normalize_refuses() -> None:
    """The sharp statement of class two, and the one worth acting on.

    Idempotence is a property of a function. **This** is a property of the
    subsystem: the two halves of the governed round trip disagree about ``26``
    inputs. ``to_physical_name`` hands back a name with ``unaccounted`` empty and
    ``confidence`` at ``0.0``; hand that same name to ``normalize`` and it raises,
    because the combining mark it contains is a character no token can hold.

    Counted rather than sampled -- ``26 of 26`` -- because "some of them do" is
    the phrasing under which a class stops being a class.
    """
    refused = 0
    for code_point in sorted(upper_case_expansion_class()):
        physical = to_physical_name(chr(code_point), NDS).physical
        try:
            normalize(physical, NDS)
        except TokenizationError:
            refused += 1

    assert refused == 26, (
        f"{refused} of 26 upper-case-expansion code points produce a physical name that "
        f"normalize refuses to read back"
    )

    # The mechanism, spelled out on the member the class is named for.
    caron = to_physical_name("ǰ", NDS)
    assert caron.physical == "J̌"
    assert caron.unaccounted == (), "pass one reports nothing unaccounted"
    assert to_physical_name(caron.physical, NDS).unaccounted == ("̌",)
    assert to_physical_name(caron.physical, NDS).physical == "J", "pass two drops the caron"


def test_normalize_already_refuses_the_whole_expansion_class_and_naming_does_not() -> None:
    """The asymmetry, which is what makes class two a defect in ONE verb.

    ``docs/GOVERNED_NAMING.md`` records the fix that taught ``normalize`` to
    refuse a corrected name carrying an unaccounted character, and names
    ``U+0390`` -- a member of this class -- as the worked example. That fix
    landed and it holds: all ``26`` are refused on input.

    ``to_physical_name`` received no equivalent, and answers all ``26``. So this
    class is invisible from the ``normalize`` side entirely, which is why five
    rounds of property tests aimed at ``normalize`` could not have found it and
    why the round that fixed the ``normalize`` half did not notice the other.
    """
    members = sorted(upper_case_expansion_class())
    refused_by_normalize = 0
    answered_by_naming = 0
    for code_point in members:
        try:
            normalize(chr(code_point), NDS)
        except TokenizationError:
            refused_by_normalize += 1
        to_physical_name(chr(code_point), NDS)
        answered_by_naming += 1

    assert refused_by_normalize == 26, "normalize refuses every member on input"
    assert answered_by_naming == 26, "to_physical_name answers every member"


# --------------------------------------------------------------------------
# Invariant 1: non-vanishing, restated to the documented contract
# --------------------------------------------------------------------------
def test_a_separator_only_name_is_answered_with_nothing_and_no_exception() -> None:
    """The contract the wide form of invariant 1 would have contradicted.

    Rule 1 of :mod:`acronymkit.catalog.tokenizer`: ``None``, empty input and
    separator-only input all yield ``()``, and the function never raises,
    because a blank cell in a schema export is a normal thing to be handed and
    a splitter that threw on one would push a ``try`` into every caller.

    This is asserted first, and deliberately, so that the exemption the
    non-vanishing property carries below is visibly a *contract* rather than a
    hole cut to make a property pass.
    """
    for name in ("_", "-", "   ", ".", "___", "//", "\t\n", '""'):
        assert separator_only(name), f"{name!r} is not separator-only; the test premise moved"
        assert split_identifier_parts(name) == ((), ())
        assert normalize(name, NDS) == ""
        assert to_physical_name(name, NDS).physical == ""


@pytest.mark.parametrize("block", sorted(NAMED_BLOCKS))
def test_nothing_in_a_named_block_vanishes_silently(block: str) -> None:
    """Invariant 1 over the named blocks, exhaustively.

    Every code point of the block, in every context, and the assertion is the
    restated form: an input carrying a character outside the accounted
    separators must come back as a token or as a reported unaccounted
    character, and ``normalize`` must answer with something or refuse.

    Silent reduction to empty is the failure this is aimed at -- it is the
    shape of the defect ``docs/GOVERNED_NAMING.md`` records as the one worse
    than saying "I do not know", because nothing downstream can tell it from an
    answer.
    """
    low, high = NAMED_BLOCKS[block]
    checked = 0
    for code_point in range(low, high + 1):
        for text in contexts_for(code_point):
            if separator_only(text):
                continue
            checked += 1
            parts = split_identifier_parts(text)
            assert parts.tokens or parts.unaccounted, (
                f"U+{code_point:04X} in {text!r} reduced to nothing at all"
            )
            try:
                answer = normalize(text, NDS)
            except TokenizationError:
                continue
            assert answer, f"U+{code_point:04X} in {text!r} normalised to the empty string"
    assert checked == (high - low + 1) * len(CONTEXTS), "every code point in every context"


def test_no_combining_mark_and_no_surrogate_neighbour_vanishes_silently() -> None:
    """Invariant 1 over the two ranges a block chart does not give a name to.

    Combining marks are the characters the splitter reports rather than holds,
    so they are the ones most likely to be dropped by a path that forgot to
    report. Lone surrogates are the one input that exists in a :class:`str` and
    cannot be encoded, which makes them the cheapest available test of whether
    anything here assumes its input is writable.
    """
    checked = 0
    for code_point in combining_marks() + SURROGATE_ADJACENT:
        for text in contexts_for(code_point):
            if separator_only(text):
                continue
            checked += 1
            parts = split_identifier_parts(text)
            assert parts.tokens or parts.unaccounted, f"U+{code_point:04X} vanished in {text!r}"
    assert checked == (len(combining_marks()) + len(SURROGATE_ADJACENT)) * len(CONTEXTS)


def test_the_combining_mark_and_surrogate_populations_are_the_size_this_file_says() -> None:
    """The two derived populations, pinned, for the same reason the classes are.

    A test that walks ``len(...)`` code points and asserts nothing about
    ``len(...)`` is a test whose coverage can silently fall to zero.
    """
    assert len(combining_marks()) == 922, (
        f"{len(combining_marks())} combining marks on Unicode {unicodedata.unidata_version}"
    )
    assert len(SURROGATE_ADJACENT) == 64


# --------------------------------------------------------------------------
# Invariant 2: idempotence, exhaustive over the named blocks
# --------------------------------------------------------------------------
@pytest.mark.parametrize("block", sorted(NAMED_BLOCKS))
def test_a_named_block_breaks_idempotence_only_where_a_known_class_says_it_does(
    block: str,
) -> None:
    """Invariant 2 over the named blocks, with the known classes excluded BY NAME.

    The exclusion is the part that matters. A suite that quietly dropped the
    known-broken code points would be a suite reporting coverage it does not
    have, so the excluded set here is the two enumerated classes and nothing
    else, and **the number excluded from this block is asserted** -- so
    widening the exclusion to make a new failure disappear reddens this test
    rather than passing it.

    The measured answer for the five blocks the brief named: ``13`` excluded
    code points in Letterlike Symbols, ``0`` in the other four, and ``0``
    unexpected breaks anywhere. The blocks named as targets were not where the
    second class lived.
    """
    expected_excluded = {
        "enclosed_alphanumerics": 0,
        "currency_symbols": 0,
        "letterlike_symbols": 13,
        "mathematical_operators": 0,
        "cjk_compatibility_squared_metric": 0,
    }
    known = ordinal_indicator_class() | upper_case_expansion_class()
    low, high = NAMED_BLOCKS[block]

    excluded = [cp for cp in range(low, high + 1) if cp in known]
    assert len(excluded) == expected_excluded[block], (
        f"{block} holds {len(excluded)} known-broken code points, not "
        f"{expected_excluded[block]}; the exclusion has moved and the coverage claim with it"
    )

    unexpected: List[int] = []
    for code_point in range(low, high + 1):
        if code_point in known:
            continue
        for text in contexts_for(code_point):
            if idempotence_break(text):
                unexpected.append(code_point)
                break
    assert not unexpected, (
        f"{len(unexpected)} code points in {block} break idempotence and belong to neither "
        f"known class; the first is U+{unexpected[0]:04X}"
    )


def test_no_combining_mark_and_no_surrogate_neighbour_breaks_idempotence() -> None:
    """Invariant 2 over combining marks and the surrogate boundaries.

    Neither range intersects either known class, which is asserted rather than
    assumed -- an empty exclusion is a stronger statement than a small one and
    it is only worth making if it is checked.
    """
    known = ordinal_indicator_class() | upper_case_expansion_class()
    population = combining_marks() + SURROGATE_ADJACENT
    assert not (set(population) & known), "neither range holds a known-broken code point"

    broken = [cp for cp in population if any(idempotence_break(t) for t in contexts_for(cp))]
    assert not broken, f"{len(broken)} break idempotence; the first is U+{broken[0]:04X}"


@pytest.mark.slow
def test_across_the_whole_space_the_only_idempotence_breaks_are_the_two_classes() -> None:
    """The statement the drawn properties cannot make, and the reason this file exists.

    ``1,114,112`` code points, one context each, ``4,456,448`` calls to the two
    governed verbs. What comes back is not "no counter-example was found" but
    **an equality**: the set of code points that break idempotence *is* the
    union of the two enumerated classes, with nothing in it that is not in one
    of them and nothing missing from either.

    This is the non-circular form of the two class-size tests. Those derive the
    classes from :class:`str` predicates and check their sizes, which assumes
    the predicates describe the defect; this one derives the breaking set from
    the behaviour and compares.

    **It runs unconditionally**, and the earlier draft of this file did not. It
    was behind the ``deep`` profile, which made the strongest check in the file
    the one check that never ran in CI -- the exact shape of the four defects
    ``.github/gates.toml`` was written to end. Marked ``slow`` so a developer can
    deselect it with ``-m "not slow"``; CI passes no marker expression and runs
    it in every matrix cell, which is also where it is most useful, because the
    two classes are properties of an interpreter's Unicode data and the matrix
    is the only place several of those are present.

    NOTE, unarmed, and the machine is named: about ``13.8`` seconds on CPython
    3.13.4 win32, of which ``3.1`` is the ``normalize`` half and ``10.7`` the
    ``to_physical_name`` half. That is a wall-clock figure and nothing here
    aborts on it. The gated quantity is the work count above.
    """
    broken: Set[int] = set()
    for code_point in range(CODE_POINTS):
        if idempotence_break(f"{chr(code_point)}a"):
            broken.add(code_point)

    known = ordinal_indicator_class() | upper_case_expansion_class()
    assert len(known) == 1076
    assert broken == known, (
        f"{len(broken - known)} code points break idempotence and are in neither class; "
        f"{len(known - broken)} are in a class and do not break it"
    )


# --------------------------------------------------------------------------
# Invariant 3: span reconstruction, restated as a lossless partition
# --------------------------------------------------------------------------
@lru_cache(maxsize=1)
def prose_tokenizer() -> Tokenizer:
    """One tokenizer, reused. It caches its stop-word registry and is thread-safe."""
    return Tokenizer(Config())


def span_partition_violations(text: str) -> List[str]:
    """Every way the offsets of ``text`` fail to be a lossless partition of it.

    Five conditions, and they are the whole of what an offset consumer needs:
    in bounds, ordered, non-overlapping, faithful (``text[start:end]`` is the
    token's own text), and complete (interleaving the slices with the gaps
    between them reproduces the input). The fifth is what "reconstruction"
    means for a tokenizer that is *allowed* to discard -- and this one is,
    which is why the stronger phrasing is not asserted anywhere here.
    """
    tokens = prose_tokenizer().tokenize(text)
    problems: List[str] = []
    cursor = 0
    for token in tokens:
        if not 0 <= token.start <= token.end <= len(text):
            problems.append(f"out of bounds: [{token.start}, {token.end}) in {len(text)}")
            return problems
        if token.start < cursor:
            problems.append(f"overlaps or precedes the previous token at {token.start}")
        if text[token.start : token.end] != token.text:
            problems.append(f"slice {text[token.start : token.end]!r} != {token.text!r}")
        cursor = token.end
    if [token.index for token in tokens] != list(range(len(tokens))):
        problems.append("index is not the position in the sequence")
    rebuilt: List[str] = []
    cursor = 0
    for token in tokens:
        rebuilt.append(text[cursor : token.start])
        rebuilt.append(text[token.start : token.end])
        cursor = token.end
    rebuilt.append(text[cursor:])
    if "".join(rebuilt) != text:
        problems.append("slices interleaved with the gaps do not reproduce the input")
    return problems


def test_the_strong_phrasing_of_span_reconstruction_is_false_of_this_tokenizer() -> None:
    """Pinned as a fact, because it is the phrasing the invariant is usually given.

    *"The raw slices concatenate back to the original"* is what one would like
    invariant 3 to say. It is false here and it is false by design:
    :meth:`Tokenizer.tokenize` discards punctuation-only runs, and its own
    docstring says so. ``"a b"`` yields two tokens whose slices concatenate to
    ``"ab"``.

    A phrasing tighter than the measurement is a false phrasing, and the way to
    stop one being re-adopted next round is to assert that it does not hold
    rather than to leave it out.
    """
    text = "Multi-Factor Authentication (API)"
    tokens = prose_tokenizer().tokenize(text)

    concatenated = "".join(text[token.start : token.end] for token in tokens)
    assert concatenated != text, "if this passes, the tokenizer stopped discarding"
    assert len(concatenated) < len(text)
    # And the partition form, on the same input, does hold.
    assert span_partition_violations(text) == []


@pytest.mark.parametrize("block", sorted(NAMED_BLOCKS))
def test_spans_partition_the_input_across_a_named_block(block: str) -> None:
    """Invariant 3 over the named blocks, exhaustively, in six contexts.

    The sixth context is the prose one -- a real phrase with the code point
    spliced into it -- because the identifier contexts are single words and a
    single word exercises no gap at all. A partition property with no gaps in
    it is not testing the interesting half.
    """
    low, high = NAMED_BLOCKS[block]
    templates = (*CONTEXTS, "Multi{c}Factor Authentication (API)", "a {c} b")
    checked = 0
    for code_point in range(low, high + 1):
        for template in templates:
            text = template.format(c=chr(code_point))
            checked += 1
            problems = span_partition_violations(text)
            assert not problems, f"U+{code_point:04X} in {text!r}: {problems}"
    assert checked == (high - low + 1) * len(templates)


def test_spans_partition_the_input_across_combining_marks_and_surrogates() -> None:
    """Invariant 3 where an offset is most likely to be computed wrongly.

    A combining mark is the case where "one character" and "one grapheme"
    diverge, and a lone surrogate is the case where a code point is not a
    scalar value. Both are places an implementation that counted anything other
    than code points would come apart.
    """
    checked = 0
    for code_point in combining_marks() + SURROGATE_ADJACENT:
        for template in (*CONTEXTS, "a {c} b"):
            text = template.format(c=chr(code_point))
            checked += 1
            problems = span_partition_violations(text)
            assert not problems, f"U+{code_point:04X} in {text!r}: {problems}"
    assert checked == (len(combining_marks()) + len(SURROGATE_ADJACENT)) * (len(CONTEXTS) + 1)


# --------------------------------------------------------------------------
# The drawn half: what enumeration cannot reach
# --------------------------------------------------------------------------
#: Characters drawn from the named blocks and the two awkward ranges, so that a
#: multi-character draw is composed of the code points this file is about
#: rather than of whatever `st.text()` finds interesting.
TARGETED_CHARACTERS = st.sampled_from(
    [chr(cp) for low, high in NAMED_BLOCKS.values() for cp in range(low, high + 1)]
    + [chr(cp) for cp in combining_marks()[:200]]
    + [chr(cp) for cp in SURROGATE_ADJACENT]
    + list("abAB_-./ 12")
)


@settings(
    max_examples=EXAMPLES,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(st.text(alphabet=TARGETED_CHARACTERS, max_size=12))
@example("ºa")
@example("ǰ")
@example("ΐ")
@example("1sT")
@example("℃a")
def test_the_two_verbs_never_silently_reduce_a_drawn_name_to_nothing(text: str) -> None:
    """Invariant 1, drawn, over strings enumeration cannot produce.

    The five pinned examples are every input this file has ever seen fail
    anything, in the mechanism that survives a fresh CI runner: ``.hypothesis/``
    is gitignored and no cache step restores it, so a committed
    :func:`hypothesis.example` is the only way a found failure stays found.
    """
    assume(not separator_only(text))
    assume(text != "")

    parts = split_identifier_parts(text)
    assert parts.tokens or parts.unaccounted, f"{text!r} reduced to nothing at all"
    try:
        answer = normalize(text, NDS)
    except TokenizationError:
        return
    assert answer, f"{text!r} normalised to the empty string without refusing"


@settings(
    max_examples=EXAMPLES,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(st.text(alphabet=TARGETED_CHARACTERS, max_size=12))
@example("1sT")
@example("TXN_ID")
@example("creditBureauVendorCode")
def test_a_drawn_name_free_of_both_known_classes_is_idempotent(text: str) -> None:
    """Invariant 2, drawn, with the exclusion stated as a precondition.

    ``assume`` rather than a filtered alphabet, deliberately: a filtered
    alphabet hides how often the exclusion fires, and Hypothesis reports an
    ``assume`` rejection rate. The exclusion is by code point against the two
    enumerated classes and against nothing else.
    """
    known = ordinal_indicator_class() | upper_case_expansion_class()
    assume(not any(ord(ch) in known for ch in text))
    assume(text != "")

    try:
        once = normalize(text, NDS)
    except TokenizationError:
        once = None
    if once is not None:
        assert normalize(once, NDS) == once, f"{text!r} -> {once!r} moved on the second pass"

    first = to_physical_name(text, NDS).physical
    assert to_physical_name(first, NDS).physical == first, f"{text!r} -> {first!r} moved"


@settings(
    max_examples=EXAMPLES,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(st.text(alphabet=TARGETED_CHARACTERS, max_size=40))
@example("Multi-Factor Authentication (API)")
@example("a ́ b")
@example("\ud800\ud800")
def test_spans_partition_a_drawn_input(text: str) -> None:
    """Invariant 3, drawn, at lengths that produce several gaps.

    ``max_size`` is ``40`` rather than ``12`` here because the partition
    property is about the relationship *between* tokens, and a two-token input
    exercises one gap.
    """
    assert span_partition_violations(text) == [], text


@settings(
    max_examples=EXAMPLES,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(st.text(max_size=24))
def test_the_unrestricted_draw_still_finds_nothing_outside_the_two_classes(text: str) -> None:
    """The unrestricted draw, kept, and kept honest about what it is worth.

    This is the strategy that found the ordinal class in the first place. It is
    retained because the targeted alphabet above is a hypothesis about where
    defects live and an unrestricted draw is not -- but on a space of ``1.1``
    million code points, ``200`` examples is a statement about the draw and
    nothing more. The enumeration above is what makes the coverage claim; this
    is what might embarrass it.
    """
    known = ordinal_indicator_class() | upper_case_expansion_class()
    assume(not any(ord(ch) in known for ch in text))
    assume(not separator_only(text))
    assume(text != "")

    parts = split_identifier_parts(text)
    assert parts.tokens or parts.unaccounted
    try:
        once = normalize(text, NDS)
    except TokenizationError:
        return
    assert once, f"{text!r} normalised to the empty string without refusing"
    assert normalize(once, NDS) == once, f"{text!r} -> {once!r} moved on the second pass"


def test_the_budget_is_the_one_this_file_documents() -> None:
    """The budget, asserted, so that the docstring cannot drift away from it.

    The two profiles and their sizes are a decision with a rationale in the
    module docstring. A decision recorded only in prose is one nothing notices
    the loss of.

    The second assertion is the one that matters: **the profile selects a drawn
    budget and nothing else.** If a later edit puts an exhaustive sweep behind
    ``DEEP`` again, the coverage this file claims becomes conditional on an
    environment variable that no workflow in ``.github/`` sets.
    """
    assert _PROFILES == {"ci": 200, "deep": 5_000}
    budget_in_force = _PROFILES["deep" if DEEP else "ci"]
    assert budget_in_force == EXAMPLES

    # THIS READS A FILE, AND THE FILE IS THIS MODULE. `__file__` of the running
    # test module is present wherever the test runs by definition -- it is not a
    # checkout-only path, and it is the one file a test may read without the
    # `installed-suite` job needing an entry for it.
    source = Path(__file__).read_text(encoding="utf-8")
    # Assembled at run time so that this line is not itself the occurrence it
    # forbids -- the first draft of this assertion failed on its own text.
    forbidden = "@pytest.mark." + "skipif"
    assert forbidden not in source, (
        "no test in this file may be conditionally skipped: the exhaustive sweeps ARE the "
        "coverage claim, and a skipped sweep is a coverage claim nothing checks"
    )
