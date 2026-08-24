"""The governed vocabulary: its rows, its indexes, and the precedence chain.

:class:`GovernedDictionary` is the ground truth of this subsystem. Everything
else — the verbs, the compliance check, the reverse direction — is a loop over
what this class answers. It holds catalog rows, three allow-lists, a class-word
map, a glossary index and a caller-supplied overlay, and it answers four
questions about a token: what row do you have for it (:meth:`lookup`), what does
it resolve to under this policy (:meth:`resolve`), may it stand in a physical
name (:meth:`is_approved`), and what class word does it designate
(:meth:`class_word_for`). :meth:`abbreviate` answers the fifth question, in the
other direction: which token is this word's governed short form.

Precedence, which is the whole design
-------------------------------------
One order, highest first, applied to every token::

    1. custom overlay        -> ExpansionSource.CUSTOM
    2. entry pin             -> PINNED
    3. entry canonical       -> APPROVED if keep_as_abbrev, else GOVERNED
    4. allow-list, no row    -> APPROVED, and the expansion is the token itself
    5. collision, no pin     -> SCORED, settled by canonical_form_score
    6. nothing               -> no entry at all; the caller emits a passthrough

Rules 3 and 5 never compete for the same entry, and it is worth saying why the
numbering does not decide between them. ``canonical`` is a required field, so
every row has one; if rule 3 fired for every row that has a canonical, rule 5
could never fire at all. Rule 5 is not a later attempt at the same row — it is a
different *shape* of row. An entry whose ``candidates`` hold more than one long
form and whose ``pin`` is empty is a collision nobody has ruled on, and that
shape goes to the score. Every other shape goes to ``canonical``. The two are
mutually exclusive, which is why their relative position in the list never
arbitrates anything.

Rule 1 and the demotion
-----------------------
``NamingPolicy.allow_override=False`` does not switch the overlay off. It
demotes exactly one case: an overlay that **contradicts** what the catalog
already says. An overlay for a token the catalog has never heard of is applied
whatever the policy says, because overriding nothing is not an override — there
is no governed decision for it to overrule, and refusing it would leave the
caller with an unknown token and no way to fix it. See
:meth:`GovernedDictionary.resolve` for how "contradicts" is decided and where
the refusal is recorded.

Determinism
-----------
Every index is built once in :meth:`GovernedDictionary.__init__` and never
mutated, so an instance is safe to share across threads and to hold on a
long-lived service object. Nothing here reads a clock, a random source or an
environment variable, and no answer depends on the iteration order of a set: the
reverse index resolves a contested long form by a written-down tie-break, and a
collision with no pin is settled by :func:`~acronymkit.governed.scoring.rank_candidates`,
which is total. Two processes given the same rows produce the same answers and
the same audit records.

Memoisation, and the three things that make it safe
---------------------------------------------------
:meth:`GovernedDictionary.resolve` is a pure function of ``(this dictionary,
this token, this policy)``, and a schema repeats tokens enormously — every table
has an id, a date and a code column — so the answer is remembered. What makes
that a cache rather than a bug is that all three parts of the key are honoured:

* **This dictionary.** The memo lives on the instance, and
  :meth:`~GovernedDictionary.with_custom` builds a *new* instance with an empty
  one. A call-scoped ``custom=`` overlay therefore cannot be served an answer
  computed without it, because it is not asking the same object.
* **This policy.** Memos are kept per policy, matched by value, so two policies
  that differ in any field never share one. Nothing enumerates which fields
  ``resolve`` happens to read, because that list is exactly the kind of thing
  that goes stale and returns a wrong answer quickly.
* **This token.** Keyed on the normalised lookup key, which is what the answer
  depends on; the surface spelling is the caller's and is not part of it.

What is *not* remembered is that a token is unknown. That keeps the memo keyed by
the vocabulary — a set the dictionary fixes when it is built — rather than by
whatever names the caller happens to have, which is the shape that grows without
limit in a service that runs for a month. :data:`_MEMO_LIMIT` is the second
bound, for the residue a case-insensitive lookup leaves behind; both are
described there. The cost is that a recurring unknown token is passed through
afresh every time, and that was measured against the alternative before it was
chosen: remembering the misses is faster on a corpus that repeats them and
meaningfully *slower* on one that does not, because the bookkeeping is then paid
on every token and returns nothing.

Entries are frozen models, so handing the same object to two callers is not
observable except by ``is``. Concurrent readers are safe: a memo is only ever
added to or emptied, the pair of "policy and its memo" is published as one tuple
so a reader cannot see half of an update, and the worst a race can cost is that
two threads compute the same answer. That argument is also exercised rather than
left as an argument — ``tests/test_governed_perf.py`` points several threads at
one dictionary with the policies interleaved and compares every answer against
the one a dictionary nothing had warmed gave, because the failure a race would
cause here is a wrong answer rather than an exception.

Where ``GovernedEntry`` lives
-----------------------------
The package layout in the contract lists ``GovernedEntry`` alongside
``GovernedDictionary`` here, while the DTO section declares it with the other
frozen models. It is declared once, in :mod:`acronymkit.governed.models`, and
merely imported here; a second declaration would be a second spelling of the
same record. It is deliberately not re-exported from this module, so there is
exactly one import path for it.

Vocabulary note: worked examples use the fictional **Northwind Data Standards**
catalog (``NDS``), synthetic entry ids (``NDS-<TOKEN>``) and generic industry
tokens (``TXN``, ``APPLNT``, ``DT``). Nothing here describes a real
organisation's standard.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple, Optional, TypeVar, Union

from ..exceptions import LexiconError
from .enums import EntryKind, ExpansionSource, ResolutionMode
from .models import (
    GovernedEntry,
    GovernedValidationError,
    TokenExpansion,
    _describe_problems,
    _entry_from_mapping,
)
from .policy import NamingPolicy
from .scoring import rank_candidates

__all__ = ["DERIVED_ENTRY_CONFIDENCE", "GovernedDictionary"]


#: Confidence recorded for an entry whose long form was chosen at load time by
#: :func:`~acronymkit.governed.scoring.rank_candidates` rather than by a person.
#:
#: The value is not a probability, is not calibrated against anything, and
#: should not be read as one. What carries meaning is that it is below 1.0,
#: which is what marks the entry as derived — :attr:`GovernedEntry.confidence`
#: promises that an unconfirmed row never claims a full score, and a consumer
#: filtering on an exact 1.0 is asking to see only what the catalog confirms.
#: The midpoint was picked so the value sorts well clear of every confirmed row
#: and is visibly not a near miss.
DERIVED_ENTRY_CONFIDENCE = 0.5


_DEMOTION_NOTE = (
    "Custom override refused: the overlay long form {overlay!r} contradicts the governed "
    "entry {governed!r} and policy.allow_override is False, so the catalog answer stands."
)

_MODE_NOTE = (
    "Resolved under ResolutionMode.MOST_COMMON: the first declared candidate was taken and "
    "the governed choice {governed!r} was not applied."
)

_ALLOW_LIST_NOTE = (
    "Approved by an allow list with no catalog row behind it, so the token stands as its "
    "own expansion."
)

_INVERSION_NOTE = (
    "Derived by inverting a long-to-short catalog: {count} long forms shorten to this token "
    "and none is pinned, so canonical_form_score chose {winner!r} over {beaten}. Recording a "
    "pin replaces this rule of thumb with a decision."
)

#: What :meth:`GovernedDictionary.from_json` accepts: a path, or an already
#: parsed document in either of the two layouts described on that method.
_JsonSource = Union[str, "os.PathLike[str]", Mapping[str, Any], Sequence[Any]]

#: Distinct answers one memo holds before it is emptied and starts again.
#:
#: A second bound behind the structural one. Only *governed* answers are
#: memoised, so the keys are catalog, allow-list and overlay tokens — a set the
#: vocabulary fixes at construction — and the memo cannot grow past the
#: vocabulary however many names it is shown. What this limit catches is the
#: residue: lookup is case-insensitive and the expansion memo is keyed on the
#: spelling it was given, so a caller sending ``TXN``, ``Txn`` and ``tXn`` has
#: three keys for one row, and a mixed-case export could in principle produce
#: many. That is caller input again, and an unbounded map keyed by caller input is
#: a leak whatever it is called.
#:
#: Emptying rather than evicting the least-used entry is deliberate. An eviction
#: order costs bookkeeping on every hit, which is the operation worth keeping
#: cheap; the tokens that matter are the frequent ones, and they refill an
#: emptied memo within a few names. The size is chosen against the workload
#: rather than tuned: it holds a real catalog's whole token set several times
#: over, and the worst case it admits is a few thousand frozen models.
_MEMO_LIMIT = 4096

#: Distinct policies one dictionary memoises for before all of them are dropped.
#: A pipeline runs under one policy, or two while a standard is being changed;
#: four is room for that and a bound on the memory the per-policy split can cost.
_MEMO_POLICY_LIMIT = 4

_Answer = TypeVar("_Answer")


class _Memo(NamedTuple):
    """What one dictionary has already worked out under one policy.

    Two maps rather than one because two modules answer two different questions
    about the same token and their keys would otherwise collide: ``TXN`` names a
    catalog entry in one and a whole expansion in the other.

    Neither map records that a token is **unknown**, and that is the decision
    that keeps both of them small. A memo of governed answers is keyed by the
    vocabulary — finite, and fixed when the dictionary was built. Add the misses
    and it is keyed by whatever names the caller has, which is the shape a cache
    should not have; a corpus of one-off tokens would then fill and empty it over
    and over, paying the bookkeeping on every token and getting nothing back,
    which is measurably worse than not caching at all. What it costs is that a
    recurring unknown token is Title Cased afresh each time. That is the cheap
    branch — the catalog was already asked and said nothing — and it is the one
    worth paying twice.

    Attributes:
        resolved: Normalised token key to the entry
            :meth:`GovernedDictionary.resolve` found. Never holds ``None``.
        expanded: Surface token to its :class:`~acronymkit.governed.models.TokenExpansion`,
            for tokens the vocabulary answered for. Filled by
            :mod:`acronymkit.governed.expansion`, which owns the shape of that
            answer; it is declared here because the memo has to live for exactly
            as long as the dictionary it is an answer about, and the dictionary is
            the only object with that lifetime. Keyed on the **surface** token,
            not the lookup key, because a token expansion reports the spelling it
            was given.
    """

    resolved: dict[str, GovernedEntry]
    expanded: dict[str, TokenExpansion]


def _remember(memo: dict[str, _Answer], key: str, answer: _Answer) -> _Answer:
    """Record an answer in a bounded memo and return it.

    Args:
        memo: The map to write to. Only ever holds answers the vocabulary
            supplied, so a plain ``get`` returning ``None`` means "not
            remembered" rather than "remembered as nothing".
        key: The lookup key.
        answer: What was worked out. Never ``None``.

    Returns:
        ``answer``, unchanged, so a caller can memoise and return in one line.
    """
    if len(memo) >= _MEMO_LIMIT:
        memo.clear()
    memo[key] = answer
    return answer


def _token_key(token: Optional[str]) -> str:
    """Return the upper-cased lookup key for a token.

    Lookup is case-insensitive, so the folding happens once per index rather
    than once per query. Surrounding whitespace is dropped because a token that
    reaches this library from a spreadsheet column often carries some.

    Args:
        token: A short-form token, or ``None``.

    Returns:
        The key, or ``""`` when there is no token to key on.
    """
    return token.strip().upper() if token else ""


def _phrase_key(text: Optional[str]) -> str:
    """Return the lookup key for a long form or a logical name.

    Casefolded rather than lower-cased, matching :mod:`acronymkit.lexicon`, and
    whitespace-collapsed so that ``"Cross  Reference"`` and ``"Cross
    Reference"`` are one term written twice rather than two terms.

    Args:
        text: A long form, a logical name, or ``None``.

    Returns:
        The key, or ``""`` when there is nothing to key on.
    """
    return " ".join(text.split()).casefold() if text else ""


def _key_set(values: Iterable[str]) -> frozenset[str]:
    """Normalise an allow-list into upper-cased keys, dropping blanks.

    Args:
        values: Tokens as the standard wrote them.

    Returns:
        The tokens as lookup keys.
    """
    return frozenset(key for key in map(_token_key, values) if key)


def _join_notes(existing: Optional[str], addition: str) -> str:
    """Append a resolver note to whatever the catalog already recorded.

    Args:
        existing: The entry's own ``notes``, if it had any.
        addition: The note this resolution wants to add.

    Returns:
        Both, space-joined, or the addition alone.
    """
    return f"{existing} {addition}" if existing else addition


def _overlay_index(
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]],
) -> dict[str, GovernedEntry]:
    """Normalise a caller's overlay into entries keyed by token.

    Two input shapes are accepted, and they mean the same thing at different
    levels of detail. A bare string (``{"XYZ": "Exchange"}``) is the common case
    and is turned into an entry that claims nothing beyond the long form: no
    ``entry_id``, because there is no catalog row to point at, and
    ``EntryKind.APPROVED_ABBREV``, because a caller who has declared a short
    form has approved it. A whole :class:`GovernedEntry` is passed through as
    the caller authored it, so an overlay can carry its own provenance handle,
    its own confidence and its own kind.

    Two things are rewritten on the way in. ``source`` is forced to
    ``ExpansionSource.CUSTOM``, because an entry reached through the overlay
    came from the overlay whatever it says about itself; and ``token`` is set to
    the mapping key, because the key is what the index is built on and a record
    that disagreed with its own key would make the audit trail wrong.

    An overlay whose long form is blank is dropped. Applying it would produce an
    expansion that reports ``is_known=True`` with nothing in it, which is worse
    than reporting the token unknown — the one outcome this package exists to
    avoid is a confident answer that is not an answer.

    Args:
        custom: The overlay mapping, or ``None``.

    Returns:
        Token key to overlay entry. Empty when ``custom`` is ``None`` or holds
        nothing usable.
    """
    index: dict[str, GovernedEntry] = {}
    for raw_token, value in (custom or {}).items():
        key = _token_key(raw_token)
        if not key:
            continue
        if isinstance(value, GovernedEntry):
            if not value.canonical.strip():
                continue
            index[key] = value.model_copy(update={"token": key, "source": ExpansionSource.CUSTOM})
            continue
        if isinstance(value, Mapping):
            # An overlay read from JSON, which is how a caller supplies one in
            # practice: `json.load(open("my_acronyms.json"))` yields plain
            # dicts, not GovernedEntry objects. Falling through to the string
            # branch below would stringify the mapping and hand back an
            # "expansion" that is the repr of a dict, reported as known with
            # full confidence -- a confident answer that is not an answer,
            # which is the one outcome this package exists to prevent. Build
            # the entry instead, and let a malformed one raise rather than
            # quietly becoming text.
            try:
                entry = _entry_from_mapping(
                    {
                        **{
                            str(field): item
                            for field, item in value.items()
                            if not str(field).startswith("_")
                        },
                        "token": key,
                        "source": ExpansionSource.CUSTOM,
                    }
                )
            except GovernedValidationError as exc:
                raise LexiconError(
                    f"Custom overlay entry {raw_token!r} is not a valid governed entry: "
                    f"{_describe_problems(exc.problems)}"
                ) from exc
            if not entry.canonical.strip():
                continue
            index[key] = entry
            continue
        canonical = " ".join(str(value).split())
        if not canonical:
            continue
        index[key] = GovernedEntry(
            token=key,
            canonical=canonical,
            kind=EntryKind.APPROVED_ABBREV,
            source=ExpansionSource.CUSTOM,
        )
    return index


def _too_long_to_match(text: str, longest: int) -> bool:
    """Whether ``text`` is too long to be any long form the index holds.

    An exact rejection, not an estimate, and it is worth reading the three
    conditions as one argument rather than as three tests.
    :func:`_phrase_key` collapses whitespace and case-folds, so what has to be
    bounded from below is the length of the *key*, and the only thing that can
    make a key shorter than its text is whitespace collapsing:

    * **ASCII**, because folding can lengthen a string — ``ß`` folds to ``ss`` —
      and then a key can be longer than the text it came from;
    * **printable**, because every ASCII whitespace character except the space
      itself is unprintable, so this is what makes "the spaces are all the
      whitespace there is" true rather than assumed. Drop it and a phrase
      separated by a tab reads as one long word and is refused although the index
      holds it;
    * with both of those, the key is at least ``len(text) - text.count(" ")``
      characters, since collapsing removes only spaces and puts one back between
      every pair of words.

    The reverse direction asks the index about every run of words in a name, and
    nearly all of them are many times longer than any term a catalog abbreviates,
    so measuring before normalising is most of the work avoided. Anything the
    three conditions do not cover simply takes the ordinary path.

    Args:
        text: The phrase as the caller wrote it.
        longest: Length of the longest key in the indexes being consulted.

    Returns:
        ``True`` only when no key of ``text`` can be in an index that long.
    """
    return (
        len(text) > longest
        and text.isascii()
        and text.isprintable()
        and len(text) - text.count(" ") > longest
    )


def _longest_long_form(*indexes: Mapping[str, GovernedEntry]) -> int:
    """Length of the longest key across some reverse indexes.

    The bound :meth:`GovernedDictionary.abbreviate` rejects on; see
    :func:`_too_long_to_match` for why a length is enough to decide with.

    Args:
        *indexes: The reverse indexes to measure, keyed as
            :func:`_phrase_key` produces.

    Returns:
        The longest key length, or ``0`` when every index is empty.
    """
    return max((len(key) for index in indexes for key in index), default=0)


def _longest_long_form_words(*indexes: Mapping[str, GovernedEntry]) -> int:
    """How many words the wordiest long form in these indexes has.

    The companion to :func:`_longest_long_form`, in words rather than
    characters, and it exists for a different consumer.
    :mod:`acronymkit.governed.naming` matches longest-first: at each position it
    asks the reverse index about the run of words from here to the end of the
    name, then one shorter, and so on. On an eighteen-word name that is 171
    questions, and every one longer than the wordiest catalog term is asking
    whether an index that holds nothing above four words holds an eighteen-word
    key. Knowing the ceiling turns the scan from quadratic in the name into
    linear in the name and bounded by the catalog, which is the right shape:
    names get longer, catalog terms do not.

    Args:
        *indexes: Reverse indexes keyed as :func:`_phrase_key` produces, whose
            keys are therefore already whitespace-collapsed.

    Returns:
        The largest word count, or ``0`` when every index is empty.
    """
    return max((key.count(" ") + 1 for index in indexes for key in index), default=0)


def _reverse_index(entries: Iterable[GovernedEntry]) -> dict[str, GovernedEntry]:
    """Build the long-form → entry index that :meth:`GovernedDictionary.abbreviate` reads.

    Every long form an entry carries claims the entry: its ``canonical`` and
    every member of its ``candidates``. That is what makes the reverse direction
    useful — ``abbreviate("Identity")`` finds ``ID`` even though ``ID`` is
    pinned to ``Identifier`` — and it is also what makes long forms contested,
    because two tokens can legitimately carry the same word.

    The contest is settled by a written-down rule so that two processes loading
    the same rows agree:

    1. prefer the entry whose ``canonical`` is this long form, over one that
       merely lists it as a candidate — a token the catalog says *means* this
       word beats a token that only *might*;
    2. then the shortest token, because the shorter of two approved forms is the
       one a physical name wants;
    3. then the token that sorts first, which decides nothing on merit and is
       there so the rule is total rather than dependent on file order.

    Args:
        entries: The rows to index. Tokens must already be unique.

    Returns:
        Long-form key to the winning entry.
    """
    claims: dict[str, list[tuple[int, int, str, GovernedEntry]]] = {}
    for entry in entries:
        canonical_key = _phrase_key(entry.canonical)
        forms = {canonical_key} if canonical_key else set()
        forms.update(key for key in map(_phrase_key, entry.candidates) if key)
        for key in forms:
            rank = 0 if key == canonical_key else 1
            claims.setdefault(key, []).append((rank, len(entry.token), entry.token, entry))
    return {key: min(bids, key=lambda bid: bid[:3])[3] for key, bids in claims.items()}


def _governed_choice(entry: GovernedEntry, token: str) -> str:
    """Return what the catalog says this token means, ignoring policy.

    The governed answer for an entry is its pin when it has one, the winner of
    :func:`~acronymkit.governed.scoring.rank_candidates` when it is an
    unresolved collision, and its ``canonical`` otherwise. Deliberately
    independent of :class:`~acronymkit.governed.policy.NamingPolicy`: this is
    the statement an overlay is measured against when deciding whether it
    contradicts the catalog, and whether a caller may overrule the catalog is a
    separate question from what the catalog said.

    Args:
        entry: The catalog row.
        token: The upper-cased token, needed only by the US-state scoring rule.

    Returns:
        The governed long form.
    """
    if entry.pin:
        return entry.pin
    if len(entry.candidates) > 1:
        ranked = rank_candidates(entry.candidates, token)
        if ranked:
            return ranked[0]
    return entry.canonical


def _resolved(
    entry: GovernedEntry,
    token: str,
    policy: NamingPolicy,
    note: Optional[str],
) -> GovernedEntry:
    """Apply rules 2, 3 and 5 to a catalog row and report which one fired.

    The returned entry is the row with three fields rewritten: ``canonical``
    becomes the long form this resolution chose, ``source`` becomes the rule
    that chose it, and ``notes`` gains a sentence whenever something happened
    that a reviewer would otherwise have to reconstruct. Everything else —
    ``candidates``, ``pin``, ``entry_id``, ``confidence``, ``kind`` — is carried
    through untouched, which is what lets the caller report what the answer
    beat and where it came from.

    Under ``ResolutionMode.MOST_COMMON`` the pin is not consulted at all and the
    first declared candidate wins. That answer is reported as ``GOVERNED``,
    because it is a long form the catalog carried, and it is annotated whenever
    it differs from the governed choice so that the audit record does not read
    as though the catalog had agreed. No member of ``ExpansionSource`` names
    "chosen by position in the candidate list"; ``GOVERNED`` plus the note is
    the closest honest pair.

    Args:
        entry: The catalog row.
        token: The upper-cased token.
        policy: The active policy; only ``mode`` is read here.
        note: A demotion note from a refused overlay, or ``None``.

    Returns:
        The row, resolved.
    """
    notes = entry.notes
    if policy.mode is ResolutionMode.MOST_COMMON:
        winner = entry.candidates[0] if entry.candidates else entry.canonical
        source = (
            ExpansionSource.APPROVED
            if entry.keep_as_abbrev and winner == entry.canonical
            else ExpansionSource.GOVERNED
        )
        governed = _governed_choice(entry, token)
        if winner != governed:
            notes = _join_notes(notes, _MODE_NOTE.format(governed=governed))
    elif entry.pin:
        winner = entry.pin
        source = ExpansionSource.PINNED
    elif len(entry.candidates) > 1:
        ranked = rank_candidates(entry.candidates, token)
        winner = ranked[0] if ranked else entry.canonical
        source = ExpansionSource.SCORED
    else:
        winner = entry.canonical
        source = ExpansionSource.APPROVED if entry.keep_as_abbrev else ExpansionSource.GOVERNED
    if note:
        notes = _join_notes(notes, note)
    return entry.model_copy(update={"canonical": winner, "source": source, "notes": notes})


def _entry_rows(document: Any) -> Sequence[Any]:
    """Pull the row list out of a parsed catalog document.

    Two on-disk layouts are accepted. A bare JSON array *is* the rows. An object
    carries them under ``"entries"`` alongside whatever else the file wants to
    record — a catalog name, a synthetic-data flag, a list of tokens
    deliberately held out. The contract does not fix the layout, so neither does
    this: refusing the object form would make a catalog file unable to describe
    itself.

    Args:
        document: The parsed JSON.

    Returns:
        The rows, unvalidated.

    Raises:
        LexiconError: If the document is neither shape, or the object form has
            no ``"entries"`` key.
    """
    if isinstance(document, Mapping):
        rows = document.get("entries")
        if rows is None:
            raise LexiconError(
                'Governed dictionary object form must carry an "entries" key holding the '
                "entry rows; a bare JSON array of rows is also accepted."
            )
    else:
        rows = document
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        raise LexiconError(
            f"Governed dictionary entries must be a JSON array of objects, got "
            f"{type(rows).__name__}."
        )
    return rows


def _entry_from_row(row: Any, position: int) -> GovernedEntry:
    """Build one :class:`GovernedEntry` from a parsed JSON object.

    Keys beginning with an underscore are dropped before construction. The
    fixture corpus uses a leading underscore to mark metadata that is written
    for a person rather than for a loader, and :class:`GovernedEntry` forbids
    unknown fields, so a comment left next to a row would otherwise fail the
    whole file.

    Args:
        row: One element of the entry array.
        position: Its index, used only to make an error message locatable.

    Returns:
        The entry.

    Raises:
        LexiconError: If the row is not an object, or is missing a required
            field, or carries a field the model does not have.
    """
    if not isinstance(row, Mapping):
        raise LexiconError(
            f"Governed dictionary entry at position {position} must be a JSON object, got "
            f"{type(row).__name__}."
        )
    fields = {str(key): value for key, value in row.items() if not str(key).startswith("_")}
    try:
        return _entry_from_mapping(fields)
    except GovernedValidationError as exc:
        raise LexiconError(
            f"Governed dictionary entry at position {position} is malformed: "
            f"{_describe_problems(exc.problems)}"
        ) from exc


class GovernedDictionary:
    """A governed vocabulary, indexed for expansion, approval and abbreviation.

    Every index is materialised once and never written to again, so lookups are
    dictionary hits rather than scans and an instance can be shared across
    threads without locking. The one part that *is* written after construction is
    the memo — see the module docstring for what makes concurrent readers safe,
    and note that "immutable" here means no answer ever changes, not that no
    attribute ever does.

    Construction takes the catalog rows plus the material a naming standard
    keeps beside them: the three allow-lists that say which tokens may stand in
    a physical name, the class-word map, a glossary index from logical name to
    term id, and a caller-supplied overlay that outranks all of it.

    ``GovernedDictionary()`` with no arguments is a valid, empty vocabulary. It
    knows nothing, approves nothing and passes every token through — which is
    the honest shape of "no governed vocabulary was supplied", and the reason
    the verbs refuse ``dictionary=None`` rather than treating it as this.

    Example:
        >>> from acronymkit.governed import EntryKind, ExpansionSource
        >>> from acronymkit.governed import GovernedDictionary, GovernedEntry
        >>> catalog = GovernedDictionary(
        ...     [
        ...         GovernedEntry(
        ...             token="TXN",
        ...             canonical="Transaction",
        ...             kind=EntryKind.APPROVED_ABBREV,
        ...             entry_id="NDS-TXN",
        ...             source=ExpansionSource.GOVERNED,
        ...         )
        ...     ],
        ...     class_words={"DT": "Date"},
        ... )
        >>> catalog.lookup("txn").canonical
        'Transaction'
        >>> catalog.class_word_for("DT")
        'Date'
        >>> catalog.lookup("KYC") is None
        True
    """

    __slots__ = (
        "_approved",
        "_by_long_form",
        "_class_word_full_forms",
        "_class_words",
        "_common",
        "_custom",
        "_custom_by_long_form",
        "_entries",
        "_longest_long_form",
        "_longest_long_form_words",
        "_memo_recent",
        "_memos",
        "_short_words",
        "_term_index",
    )

    def __init__(
        self,
        entries: Iterable[GovernedEntry] = (),
        *,
        custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
        approved_abbreviations: Iterable[str] = (),
        common_keywords: Iterable[str] = (),
        short_full_words: Iterable[str] = (),
        class_words: Optional[Mapping[str, str]] = None,
        term_index: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Index a governed vocabulary.

        Args:
            entries: The catalog rows. Tokens are upper-cased into the index, so
                a row may be authored in any casing. Two rows with the same
                token are not an error; the later one wins, which is what makes
                a list of rows layerable in the same last-wins way as an
                overlay.
            custom: A caller-supplied overlay, ``{token: long form}`` or
                ``{token: GovernedEntry}``, which outranks every catalog row.
                See :meth:`resolve` for the one case a policy can demote.
            approved_abbreviations: Short forms the standard permits in a
                physical name.
            common_keywords: Vocabulary the standard permits everywhere without
                approving it as an abbreviation.
            short_full_words: Whole words short enough to be mistaken for
                abbreviations (``RISK``, ``MODEL``), listed so a compliance
                check can say "this is a word" rather than "this is an
                unapproved abbreviation".
            class_words: Class-word abbreviation to its spelled-out form,
                ``{"DT": "Date"}``. Both halves are matched by
                :meth:`class_word_for`, so a name that ends in ``DATE`` is
                recognised as well as one that ends in ``DT``.
            term_index: Logical name to glossary term id. Matched
                case-insensitively with whitespace collapsed.

        Raises:
            ValueError: If ``entries`` yields something that is not a
                :class:`~acronymkit.governed.models.GovernedEntry`; the
                attribute access fails at that point rather than producing an
                index with a hole in it.
        """
        rows: dict[str, GovernedEntry] = {}
        for entry in entries:
            key = _token_key(entry.token)
            if not key:
                continue
            rows[key] = entry if entry.token == key else entry.model_copy(update={"token": key})
        self._entries: dict[str, GovernedEntry] = rows
        self._custom: dict[str, GovernedEntry] = _overlay_index(custom)

        self._approved: frozenset[str] = _key_set(approved_abbreviations)
        self._common: frozenset[str] = _key_set(common_keywords)
        self._short_words: frozenset[str] = _key_set(short_full_words)

        mapped: dict[str, str] = {}
        full_forms: dict[str, str] = {}
        for abbrev, full in (class_words or {}).items():
            key = _token_key(abbrev)
            word = " ".join(full.split()) if full else ""
            if not key or not word:
                continue
            mapped[key] = word
            full_forms.setdefault(_token_key(word), word)
        self._class_words: dict[str, str] = mapped
        self._class_word_full_forms: dict[str, str] = full_forms

        self._term_index: dict[str, str] = {
            _phrase_key(name): term_id
            for name, term_id in (term_index or {}).items()
            if _phrase_key(name) and term_id
        }

        self._by_long_form: dict[str, GovernedEntry] = _reverse_index(rows.values())
        self._custom_by_long_form: dict[str, GovernedEntry] = _reverse_index(self._custom.values())
        self._longest_long_form: int = _longest_long_form(
            self._by_long_form, self._custom_by_long_form
        )
        self._longest_long_form_words: int = _longest_long_form_words(
            self._by_long_form, self._custom_by_long_form
        )

        self._memos: dict[NamingPolicy, _Memo] = {}
        self._memo_recent: Optional[tuple[NamingPolicy, _Memo]] = None

    # -- construction ------------------------------------------------------
    @classmethod
    def from_json(
        cls,
        path_or_obj: _JsonSource,
        *,
        custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
        approved_abbreviations: Iterable[str] = (),
        common_keywords: Iterable[str] = (),
        short_full_words: Iterable[str] = (),
        class_words: Optional[Mapping[str, str]] = None,
        term_index: Optional[Mapping[str, str]] = None,
    ) -> GovernedDictionary:
        """Load a catalog from a JSON file or an already-parsed document.

        A :class:`str` or :class:`os.PathLike` argument is a **path**, never
        JSON text. That is the one ambiguity worth being firm about: the
        parameter is a source, and a caller who has the document in memory
        should pass the parsed object rather than re-serialising it.

        Both on-disk layouts described on :func:`_entry_rows` are accepted. Keys
        of the object form other than ``"entries"`` are ignored, so a file may
        record its own name, a synthetic-data flag or a list of tokens held out
        of the catalog without this loader having to know what they mean.

        The allow-lists, class words and glossary are separate arguments because
        a governed standard keeps them in separate files; this loader reads the
        catalog and nothing else.

        Args:
            path_or_obj: A path to a UTF-8 JSON file, or a parsed document —
                either the bare array of rows or an object carrying them under
                ``"entries"``.
            custom: As :meth:`__init__`.
            approved_abbreviations: As :meth:`__init__`.
            common_keywords: As :meth:`__init__`.
            short_full_words: As :meth:`__init__`.
            class_words: As :meth:`__init__`.
            term_index: As :meth:`__init__`.

        Returns:
            The indexed vocabulary.

        Raises:
            LexiconError: If the file is missing, unreadable, not valid UTF-8 or
                not valid JSON; if the document is neither accepted layout; or
                if any row is malformed. The message names the row position,
                because a catalog is long and "one row is wrong" is not
                actionable on its own.
        """
        document: Any
        if isinstance(path_or_obj, (str, os.PathLike)):
            source = Path(os.fspath(path_or_obj))
            try:
                text = source.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise LexiconError(
                    f"Governed dictionary {source!s} is not valid UTF-8: {exc}"
                ) from exc
            except OSError as exc:
                raise LexiconError(
                    f"Governed dictionary {source!s} could not be read: {exc}"
                ) from exc
            try:
                document = json.loads(text)
            except json.JSONDecodeError as exc:
                raise LexiconError(
                    f"Governed dictionary {source!s} is not valid JSON: {exc}"
                ) from exc
        else:
            document = path_or_obj
        rows = [
            _entry_from_row(row, position) for position, row in enumerate(_entry_rows(document))
        ]
        return cls(
            rows,
            custom=custom,
            approved_abbreviations=approved_abbreviations,
            common_keywords=common_keywords,
            short_full_words=short_full_words,
            class_words=class_words,
            term_index=term_index,
        )

    @classmethod
    def from_mapping(
        cls,
        short_to_long: Mapping[str, str],
        *,
        custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
        approved_abbreviations: Iterable[str] = (),
        common_keywords: Iterable[str] = (),
        short_full_words: Iterable[str] = (),
        class_words: Optional[Mapping[str, str]] = None,
        term_index: Optional[Mapping[str, str]] = None,
    ) -> GovernedDictionary:
        """Build a catalog from a plain ``{token: long form}`` mapping.

        The smallest useful vocabulary, and the shape a caller reaches for when
        trying the library out. Every row is unambiguous by construction — a
        mapping cannot express a collision — so no entry gets a ``candidates``
        set, no entry gets a pin, and nothing here is ever settled by score.

        Entries carry no ``entry_id``. A mapping has no rows to point at, and
        minting an identifier for one would make the audit trail claim a
        provenance that does not exist. Their kind is
        ``EntryKind.APPROVED_ABBREV``: a caller who wrote the mapping has said
        what the token means, and there is nothing else in the input to
        distinguish one kind of row from another.

        Args:
            short_to_long: Token to its single governed long form. Tokens are
                upper-cased; blank tokens and blank long forms are skipped.
            custom: As :meth:`__init__`.
            approved_abbreviations: As :meth:`__init__`.
            common_keywords: As :meth:`__init__`.
            short_full_words: As :meth:`__init__`.
            class_words: As :meth:`__init__`.
            term_index: As :meth:`__init__`.

        Returns:
            The indexed vocabulary.

        Example:
            >>> from acronymkit.governed import GovernedDictionary
            >>> catalog = GovernedDictionary.from_mapping({"txn": "Transaction"})
            >>> catalog.lookup("TXN").canonical
            'Transaction'
        """
        rows: list[GovernedEntry] = []
        for token, long_form in short_to_long.items():
            key = _token_key(token)
            canonical = " ".join(long_form.split()) if long_form else ""
            if not key or not canonical:
                continue
            rows.append(
                GovernedEntry(
                    token=key,
                    canonical=canonical,
                    kind=EntryKind.APPROVED_ABBREV,
                    source=ExpansionSource.GOVERNED,
                )
            )
        return cls(
            rows,
            custom=custom,
            approved_abbreviations=approved_abbreviations,
            common_keywords=common_keywords,
            short_full_words=short_full_words,
            class_words=class_words,
            term_index=term_index,
        )

    @classmethod
    def from_long_to_short(
        cls,
        mapping: Mapping[str, str],
        *,
        custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
        approved_abbreviations: Iterable[str] = (),
        common_keywords: Iterable[str] = (),
        short_full_words: Iterable[str] = (),
        class_words: Optional[Mapping[str, str]] = None,
        term_index: Optional[Mapping[str, str]] = None,
    ) -> GovernedDictionary:
        """Invert a real catalog: ``{long form: token}`` into expandable entries.

        This is the loader that matters, because it is the shape a governed
        catalog is actually stored in, and inverting it is where the problem
        this package exists for appears.

        A standard is authored in one direction. Somebody writes down that
        *Transaction* is abbreviated ``TXN``, *Date* is ``DT``, *Identifier* is
        ``ID``. Read that way it is a mapping with one answer per row, and
        nobody authoring it has to think about ambiguity at all.

        Expansion reads it the other way, and the inverse of a long → short
        catalog is **not** a mapping. Distinct terms shorten to the same token
        constantly: *Identifier*, *Identification*, *Identity* and — in any
        catalog that also has address columns — *Idaho* all shorten to ``ID``.
        Inverting turns those four rows into one token with four candidate long
        forms and no row anywhere saying which one a bare ``ID`` in a column
        name stood for. The ambiguity is not introduced by the inversion; it was
        always in the catalog, and reading it backwards is what makes it
        visible.

        So each token gets one entry, and the entry is one of two shapes:

        * **one long form** — an unambiguous row. ``canonical`` is that form,
          ``candidates`` records it as the single-member collision set the
          source actually produced, and confidence is full, because the answer
          is exactly what the catalog said.
        * **several long forms** — a collision, and nobody has ruled on it, so
          :func:`~acronymkit.governed.scoring.rank_candidates` chooses and the
          entry records that it did: ``source`` is ``SCORED``, ``pin`` stays
          empty, ``confidence`` is :data:`DERIVED_ENTRY_CONFIDENCE` rather than
          full, and ``notes`` names the winner and what it beat. A derived
          answer that claimed the same confidence as a governed one would make
          the confidence field worthless for every other row.

        Candidate order is the mapping's own iteration order, which for a
        ``dict`` is insertion order — so a catalog file read top to bottom
        produces candidates in file order, and
        ``NamingPolicy.frequency_baseline()``, which reads position zero, sees
        what the file put first.

        ``EntryKind`` has no member for a collision that nobody pinned, so these
        entries are filed as ``AMBIGUOUS_PINNED`` with an empty ``pin``. The
        kind names the archetype and the ``pin`` field alone says whether a
        decision exists; an ``AMBIGUOUS_UNPINNED`` member would say it better.

        Args:
            mapping: Long form to its governed token, as the catalog stores it.
                Blank keys and blank values are skipped; a long form repeated
                for the same token is recorded once.
            custom: As :meth:`__init__`.
            approved_abbreviations: As :meth:`__init__`.
            common_keywords: As :meth:`__init__`.
            short_full_words: As :meth:`__init__`.
            class_words: As :meth:`__init__`.
            term_index: As :meth:`__init__`.

        Returns:
            The indexed vocabulary, with every collision resolved and every
            resolution recorded.

        Example:
            Three catalog rows, one token, and a state name in the middle of
            them. The score keeps ``Idaho`` out and the entry records that no
            pin was involved.

            >>> from acronymkit.governed import GovernedDictionary
            >>> catalog = GovernedDictionary.from_long_to_short(
            ...     {"Idaho": "ID", "Identification": "ID", "Identifier": "ID"}
            ... )
            >>> entry = catalog.lookup("ID")
            >>> entry.canonical, entry.source.value, entry.pin
            ('Identifier', 'scored', None)
            >>> entry.candidates
            ('Idaho', 'Identification', 'Identifier')
            >>> entry.confidence < 1.0
            True
        """
        collisions: dict[str, list[str]] = {}
        for long_form, token in mapping.items():
            key = _token_key(token)
            canonical = " ".join(long_form.split()) if long_form else ""
            if not key or not canonical:
                continue
            bucket = collisions.setdefault(key, [])
            if canonical not in bucket:
                bucket.append(canonical)

        rows: list[GovernedEntry] = []
        for key, forms in collisions.items():
            if len(forms) == 1:
                rows.append(
                    GovernedEntry(
                        token=key,
                        canonical=forms[0],
                        candidates=tuple(forms),
                        kind=EntryKind.APPROVED_ABBREV,
                        source=ExpansionSource.GOVERNED,
                    )
                )
                continue
            ranked = rank_candidates(forms, key)
            winner = ranked[0] if ranked else forms[0]
            beaten = ", ".join(repr(form) for form in forms if form != winner)
            rows.append(
                GovernedEntry(
                    token=key,
                    canonical=winner,
                    candidates=tuple(forms),
                    kind=EntryKind.AMBIGUOUS_PINNED,
                    source=ExpansionSource.SCORED,
                    confidence=DERIVED_ENTRY_CONFIDENCE,
                    notes=_INVERSION_NOTE.format(count=len(forms), winner=winner, beaten=beaten),
                )
            )
        return cls(
            rows,
            custom=custom,
            approved_abbreviations=approved_abbreviations,
            common_keywords=common_keywords,
            short_full_words=short_full_words,
            class_words=class_words,
            term_index=term_index,
        )

    def with_custom(
        self, custom: Optional[Mapping[str, Union[str, GovernedEntry]]]
    ) -> GovernedDictionary:
        """Return a new dictionary with ``custom`` layered on top of this one.

        Layers compose and the last one wins, so
        ``base.with_custom(house).with_custom(project)`` gives the project layer
        the final say on any token both mention, and leaves the house layer in
        force on every token the project layer is silent about. That is
        composition rather than set union, and it is what makes an overlay usable
        as a stack of increasingly local decisions.

        Cheap by construction. The catalog rows, the allow-lists, the class-word
        map, the glossary and the reverse index are shared with the receiver by
        reference — none of them is ever mutated after construction, so sharing
        them is safe — and only the overlay and its own small reverse index are
        rebuilt. A verb called with ``custom=`` layers for that call and throws
        the result away, so this has to stay cheap enough to sit inside a loop
        over a schema.

        The memos are **not** shared, and that is a correctness requirement
        rather than an optimisation choice. An overlay changes what a token
        resolves to, so an answer worked out without it must never be served to a
        caller who supplied it. The new dictionary starts with nothing
        remembered, which is also why a per-call ``custom=`` overlay gets no
        benefit from memoisation: it is a new vocabulary every call, and it is
        answered as one.

        A subclass keeps its own state
        ------------------------------
        The clone is built with ``object.__new__(type(self))`` and its fields are
        assigned one by one rather than through ``__init__``, because rebuilding
        the indexes would cost more than the layering does and there is nothing
        to rebuild them from. That skips a subclass's ``__init__`` too, so
        anything a subclass set on the instance has to be carried across here or
        it is silently absent from the copy.

        This class declares ``__slots__``, so ``self.__dict__`` exists only when
        a subclass added one — which is exactly the case that needs copying, and
        the exact base class pays nothing. Without it the loss did not surface at
        the call: it surfaced later, as an ``AttributeError`` raised from inside a
        lookup on an object that was still the right type and answered every
        other question correctly. Subclass attributes are copied by reference,
        the same way every index above is; ``with_custom`` copies a vocabulary,
        it does not deep-copy a caller's objects.

        Args:
            custom: The overlay to layer. ``None`` and an empty mapping both
                yield an equivalent dictionary rather than the receiver itself.

        Returns:
            A new instance of the receiver's own class. The receiver is
            unchanged.
        """
        layered = dict(self._custom)
        layered.update(_overlay_index(custom))
        clone = object.__new__(type(self))
        # Before the slots below, so that a subclass attribute can never shadow
        # one of them: a slot is a data descriptor on the class and wins over an
        # instance dict either way, and copying first keeps that fact local.
        subclass_state = getattr(self, "__dict__", None)
        if subclass_state:
            clone.__dict__.update(subclass_state)
        clone._entries = self._entries
        clone._approved = self._approved
        clone._common = self._common
        clone._short_words = self._short_words
        clone._class_words = self._class_words
        clone._class_word_full_forms = self._class_word_full_forms
        clone._term_index = self._term_index
        clone._by_long_form = self._by_long_form
        clone._custom = layered
        clone._custom_by_long_form = _reverse_index(layered.values())
        clone._longest_long_form = _longest_long_form(
            self._by_long_form, clone._custom_by_long_form
        )
        clone._longest_long_form_words = _longest_long_form_words(
            self._by_long_form, clone._custom_by_long_form
        )
        clone._memos = {}
        clone._memo_recent = None
        return clone

    # -- lookups -----------------------------------------------------------
    def lookup(self, token: Optional[str]) -> Optional[GovernedEntry]:
        """Return the record this vocabulary holds for ``token``, if any.

        Case-insensitive, and it honours the one precedence rule that needs no
        policy to decide: an overlay entry outranks a catalog row. Nothing else
        is applied — no pin, no score, no allow-list. This is "what row do you
        have", and :meth:`resolve` is "what does it mean under these rules".

        The split matters for the demotion in :meth:`resolve`. This method
        always reports the overlay when there is one, because the row exists
        whatever a policy thinks of it; whether the overlay may *beat* the
        catalog is a policy question and is answered there.

        Args:
            token: A short-form token. ``None``, ``""`` and whitespace all
                return ``None``.

        Returns:
            The overlay entry, else the catalog row, else ``None``. A token with
            no row is not an error — it is rule 6, and the caller turns it into
            a passthrough.
        """
        key = _token_key(token)
        if not key:
            return None
        overlay = self._custom.get(key)
        return overlay if overlay is not None else self._entries.get(key)

    def resolve(
        self, token: Optional[str], policy: Optional[NamingPolicy] = None
    ) -> Optional[GovernedEntry]:
        """Resolve ``token`` under ``policy``, reporting which rule decided.

        The precedence chain, in full, is in the module docstring. The returned
        entry is the winning record with ``canonical`` set to the long form this
        resolution chose and ``source`` set to the rule that chose it; the
        candidate set, the pin, the entry id, the confidence and the kind are
        carried through, so the caller can report what the answer beat and where
        it came from.

        The overlay demotion
        --------------------
        ``policy.allow_override=False`` refuses exactly one thing: an overlay
        that **contradicts** the catalog. Contradiction is decided against what
        the *catalog* says the token means — its pin, or its canonical, or the
        score's pick for an unruled collision — and deliberately not against
        what this call is about to answer, because whether a caller may overrule
        the standard is a different question from which standard is in force.
        Long forms are compared with case and incidental whitespace ignored, so
        an overlay that merely restates the catalog is not a contradiction and
        is applied; applying it changes nothing anyway.

        An overlay for a token the catalog does not know is applied under every
        policy. There is no governed decision for it to overrule, so it is not
        an override, and refusing it would leave a caller holding an unknown
        token with no way to fix it.

        When an overlay is refused, the answer is the governed one and the
        returned entry's ``notes`` says the override was declined and what it
        proposed. The note rides on the entry because that is where free text
        lives; :class:`~acronymkit.governed.models.TokenExpansion` has no
        ``notes`` field, so a caller that only reads the expansion sees the
        governed answer without the explanation. That is a gap in the DTO
        surface rather than a decision, and it is recorded here so it is not
        mistaken for one.

        Args:
            token: A short-form token, matched case-insensitively.
            policy: The rules to apply. ``None`` means
                :meth:`~acronymkit.governed.policy.NamingPolicy.governed_default`.

        Returns:
            The resolved entry, or ``None`` when nothing in the vocabulary
            matches — which is rule 6, and is the caller's cue to emit a
            passthrough rather than an error.

        Example:
            >>> from acronymkit.governed import EntryKind, ExpansionSource
            >>> from acronymkit.governed import GovernedDictionary, GovernedEntry
            >>> catalog = GovernedDictionary(
            ...     [
            ...         GovernedEntry(
            ...             token="ID",
            ...             canonical="Identifier",
            ...             candidates=("Identity", "Identifier", "Idaho"),
            ...             pin="Identifier",
            ...             kind=EntryKind.AMBIGUOUS_PINNED,
            ...             source=ExpansionSource.PINNED,
            ...         )
            ...     ]
            ... )
            >>> catalog.resolve("ID").source.value
            'pinned'
            >>> overlaid = catalog.with_custom({"ID": "Identity"})
            >>> overlaid.resolve("ID").canonical
            'Identity'
            >>> from acronymkit.governed import NamingPolicy
            >>> strict = NamingPolicy(allow_override=False)
            >>> overlaid.resolve("ID", strict).canonical
            'Identifier'
        """
        key = _token_key(token)
        if not key:
            return None
        active = policy if policy is not None else NamingPolicy.governed_default()
        memo = self._memo(active).resolved
        remembered = memo.get(key)
        if remembered is not None:
            return remembered
        answer = self._decide(key, active)
        return answer if answer is None else _remember(memo, key, answer)

    def is_approved(self, token: Optional[str]) -> bool:
        """Return whether ``token`` may stand as written in a physical name.

        The shared predicate behind the compliance check. A token is approved
        when any of three things is true, and they are three genuinely different
        statements:

        * it is in the caller's overlay — the caller has declared it;
        * it has a catalog row with ``keep_as_abbrev`` set — the catalog says
          this token *is* the governed physical form, so it needs no allow-list
          row to stand;
        * it is in any of the three allow-lists.

        Approval is not the same as being known. ``NUM`` has a row and expands
        to ``Number``, and it is not approved, because the standard's approved
        form is ``NBR``. That pair is the reason a compliance check can say
        "write NBR" instead of "unknown token".

        Args:
            token: A short-form token, matched case-insensitively.

        Returns:
            ``True`` when the token may stand. ``False`` for empty input.
        """
        key = _token_key(token)
        if not key:
            return False
        if key in self._custom:
            return True
        entry = self._entries.get(key)
        if entry is not None and entry.keep_as_abbrev:
            return True
        return key in self._approved or key in self._common or key in self._short_words

    def class_word_for(self, token: Optional[str]) -> Optional[str]:
        """Return the class word ``token`` designates, if it designates one.

        A class word is the trailing noun that says what kind of value a column
        holds — ``DT`` for a date, ``CD`` for a code, ``AMT`` for an amount. This
        method answers only "does this token name one"; whether it is in the
        position where that means anything is the caller's question, and
        :class:`~acronymkit.governed.models.IdentifierExpansion` reads it from
        the trailing token alone.

        Consulted in order: the overlay or catalog row's own ``class_word``,
        then the class-word map's abbreviation keys, then its spelled-out
        values. The last of those is what lets a name written out in full be
        recognised — a logical name ending in ``Date`` designates the same class
        word as a physical name ending in ``DT``, and a standard that accepts
        both forms should not need two maps to say so.

        Args:
            token: A token or a whole word, matched case-insensitively.

        Returns:
            The class word in its spelled-out form, or ``None``.
        """
        key = _token_key(token)
        if not key:
            return None
        entry = self.lookup(key)
        if entry is not None and entry.class_word:
            return entry.class_word
        mapped = self._class_words.get(key)
        if mapped:
            return mapped
        return self._class_word_full_forms.get(key)

    @property
    def longest_long_form_words(self) -> int:
        """Word count of the wordiest long form this vocabulary can match.

        A caller matching longest-first has no reason to ask about a run of
        words longer than this: no key in the reverse index can be that long, so
        every such question is answered ``None`` by construction. Exposed so
        :func:`~acronymkit.governed.naming.to_physical_name` can bound its scan
        by the catalog instead of by the name it was handed.

        Returns:
            The largest word count in the reverse index, or ``0`` when the
            vocabulary holds no long form at all.
        """
        return self._longest_long_form_words

    def abbreviate(self, word: Optional[str]) -> Optional[GovernedEntry]:
        """Return the entry whose token is ``word``'s governed short form.

        The reverse index, built once at construction from every entry's
        ``canonical`` and every member of its ``candidates``; the tie-break for a
        long form claimed by two tokens is documented on :func:`_reverse_index`.
        Overlay entries are indexed separately and consulted first, so a caller
        who has declared a short form gets it in both directions.

        **This is not the inverse of expansion, and the difference is a property
        of governed catalogs rather than a defect here.** A token means one
        thing; several words can legitimately point at the same token. So
        ``abbreviate("Line")`` can find ``LN`` while expanding ``LN`` gives
        ``Loan``, because *Line* is one of the candidates the catalog carried
        and *Loan* is the one it pinned. Round-tripping a non-canonical
        candidate does not return it, and a round-trip test should assert that
        asymmetry rather than assume it away.

        Args:
            word: A long form, matched case-insensitively with whitespace
                collapsed.

        Returns:
            The winning entry, or ``None`` when no entry carries the word. The
            whole entry is returned rather than the bare token, because the
            caller needs the entry id and source to record where the short form
            came from.
        """
        if word is not None and _too_long_to_match(word, self._longest_long_form):
            return None
        key = _phrase_key(word)
        if not key:
            return None
        overlay = self._custom_by_long_form.get(key)
        return overlay if overlay is not None else self._by_long_form.get(key)

    def term_id_for(self, logical_name: Optional[str]) -> Optional[str]:
        """Return the glossary term id for a whole logical name.

        Distinct from a per-token entry id: a term id says the *name* is a
        governed term, not merely that its words are. Most well-formed names
        have no term id, and that is not a fault — a glossary records the terms
        an organisation has agreed on, and a name can be correctly composed of
        governed words without being one of them.

        Args:
            logical_name: The whole logical name, matched case-insensitively
                with whitespace collapsed.

        Returns:
            The term id, or ``None``.
        """
        key = _phrase_key(logical_name)
        if not key:
            return None
        return self._term_index.get(key)

    # -- internals ---------------------------------------------------------
    def _memo(self, policy: NamingPolicy) -> _Memo:
        """Return what this dictionary has already worked out under ``policy``.

        Also called from :mod:`acronymkit.governed.expansion`, which fills the
        second half of the memo; see :class:`_Memo` for why the two live
        together and the module docstring for why the split by policy is by
        value rather than by identity.

        Policies are matched by identity first and by value second, and the pair
        earns its two lines. Every verb in this package resolves its policy once
        and hands the same object to every token of a name, so the identity check
        answers all but the first token of a call at the cost of a pointer
        comparison. The lookup behind it is what catches two policies that are
        equal without being the same object — which is what a verb building its
        own default produces, as the compliance and reverse directions still do
        on every call. Matching by value is also the safe half: it is what makes
        two policies share a memo only when they say the same thing.

        Args:
            policy: The active policy.

        Returns:
            The memo for this policy, created empty if there is none.
        """
        recent = self._memo_recent
        if recent is not None and recent[0] is policy:
            return recent[1]
        memo = self._memos.get(policy)
        if memo is None:
            if len(self._memos) >= _MEMO_POLICY_LIMIT:
                self._memos.clear()
                self._memo_recent = None
            memo = _Memo({}, {})
            self._memos[policy] = memo
        # Published as one tuple, so a reader in another thread cannot see this
        # policy paired with the previous policy's memo.
        self._memo_recent = (policy, memo)
        return memo

    def _decide(self, key: str, policy: NamingPolicy) -> Optional[GovernedEntry]:
        """Work out what ``key`` resolves to, without consulting the memo.

        The precedence chain itself; :meth:`resolve` is this function plus the
        normalisation of its arguments and the memo in front of it. Split out so
        that the rules and the remembering are separately readable, and so that a
        test can exercise the chain with nothing cached in front of it.

        Args:
            key: An already-normalised token key, never empty.
            policy: The active policy, already defaulted.

        Returns:
            The resolved entry, or ``None`` when nothing in the vocabulary
            matches.
        """
        overlay = self._custom.get(key)
        entry = self._entries.get(key)

        if overlay is not None and (entry is None or policy.allow_override):
            return overlay

        note: Optional[str] = None
        if overlay is not None and entry is not None:
            governed = _governed_choice(entry, key)
            if _phrase_key(overlay.canonical) == _phrase_key(governed):
                return overlay
            note = _DEMOTION_NOTE.format(overlay=overlay.canonical, governed=governed)

        if entry is not None:
            return _resolved(entry, key, policy, note)
        return self._allow_list_entry(key)

    def _allow_list_entry(self, key: str) -> Optional[GovernedEntry]:
        """Synthesise rule 4's entry: approved by an allow-list, with no row.

        A standard's allow-lists carry tokens the catalog never gave a long form
        to — ``MGMT``, ``MSG``, ``SVC``. They are known and they are approved,
        and their expansion is the token itself: there is nothing to expand
        them *to*, and inventing something would be the guess this package
        refuses to make. So the synthesised entry has ``keep_as_abbrev`` set and
        its own token as its canonical, which is the same shape a catalog row
        for an approved short form has.

        The canonical is the upper-cased token and is deliberately **not** Title
        Cased. An approved token is the governed physical form, and re-casing it
        would be correcting the standard — the same reason a proper-noun acronym
        stays ``ZIP`` rather than becoming ``Zip``. The visible consequence is
        that such a token keeps its shape inside an expanded phrase, so
        ``ADDR_LINE_1`` reads "Address LINE 1" when ``LINE`` is approved by an
        allow-list rather than expanded by a catalog row. Give the token a
        catalog row if the phrase should say "Line".

        The lists are consulted in the order the contract states — approved
        abbreviations, then common keywords, then short full words — so a token
        in two of them is reported by the first. That order is a decision, and
        it is the reason it is written down rather than left to set iteration.

        ``EntryKind`` has no member for a common keyword, so a token approved
        only by that list is filed as ``APPROVED_ABBREV``, which names how it
        behaves rather than what it is. The allow-list sets themselves stay the
        authority on which list a token came from; a compliance check reads
        them, not this kind.

        Args:
            key: An already-normalised token key.

        Returns:
            The synthesised entry, or ``None`` when no list holds the token.
        """
        if key in self._approved or key in self._common:
            kind = EntryKind.APPROVED_ABBREV
        elif key in self._short_words:
            kind = EntryKind.SHORT_FULL_WORD
        else:
            return None
        return GovernedEntry(
            token=key,
            canonical=key,
            kind=kind,
            keep_as_abbrev=True,
            class_word=self.class_word_for(key),
            source=ExpansionSource.APPROVED,
            notes=_ALLOW_LIST_NOTE,
        )

    # -- properties --------------------------------------------------------
    @property
    def entries(self) -> tuple[GovernedEntry, ...]:
        """Every catalog row, in ascending token order. Excludes the overlay."""
        return tuple(self._entries[key] for key in sorted(self._entries))

    @property
    def custom(self) -> dict[str, GovernedEntry]:
        """The layered overlay, token to entry. A copy; editing it changes nothing."""
        return dict(self._custom)

    @property
    def approved_abbreviations(self) -> frozenset[str]:
        """Short forms the standard permits in a physical name, upper-cased."""
        return self._approved

    @property
    def common_keywords(self) -> frozenset[str]:
        """Vocabulary permitted everywhere without being an approved abbreviation."""
        return self._common

    @property
    def short_full_words(self) -> frozenset[str]:
        """Whole words short enough to be mistaken for abbreviations, upper-cased."""
        return self._short_words

    @property
    def class_words(self) -> dict[str, str]:
        """Class-word abbreviation to its spelled-out form. A copy."""
        return dict(self._class_words)

    # -- dunder ------------------------------------------------------------
    def __contains__(self, token: object) -> bool:
        """Return whether a row exists for ``token`` (overlay or catalog).

        Membership is about rows, not about approval: a token can be approved by
        an allow-list with no row, and :meth:`is_approved` is the predicate for
        that question.

        Args:
            token: Any object; non-strings are never members.

        Returns:
            ``True`` when :meth:`lookup` would return an entry.
        """
        return isinstance(token, str) and self.lookup(token) is not None

    def __len__(self) -> int:
        """Return the number of catalog rows, not counting the overlay."""
        return len(self._entries)

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return (
            f"GovernedDictionary(entries={len(self._entries)}, custom={len(self._custom)}, "
            f"approved={len(self._approved)}, class_words={len(self._class_words)})"
        )
