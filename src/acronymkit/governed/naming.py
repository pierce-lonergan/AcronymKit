"""The reverse direction: a logical name rendered as a governed physical name.

``expand_identifier`` reads ``TXN_ID`` and answers "Transaction Identifier".
:func:`to_physical_name` reads "Transaction Identifier" and answers ``TXN_ID``.
Together they are what makes this package a bidirectional engine over one
vocabulary rather than a lookup table with a nice output format, and the reason
both live here is that two directions maintained in two places disagree — a
catalog change that moves an abbreviation would fix one and quietly break the
other.

How a name is built
-------------------
The logical name is split by :func:`~acronymkit.governed.tokenizer.split_identifier`
— the same splitter the forward direction uses, so the two cannot disagree about
where a word ends — and each word is looked up in the dictionary's **reverse
index** (``GovernedDictionary.abbreviate``, long form → entry). The entry's
token is the governed short form. The tokens are joined with ``_`` and the
result is the physical name.

Three rules make the loop more than a ``dict.get``:

**A word already written as a governed token is left alone.** Logical names
arrive half-abbreviated — "Transaction ID", "Customer Acct Balance" — and so does
every phrase the forward direction produces for a token the catalog approves
without expanding, since rule 4 of the resolution order answers ``SYSTEM`` with
``SYSTEM``. Sending such a word through the reverse index does real damage:
"Monthly" is a candidate long form of ``MO``, so an already-governed ``MONTHLY``
would come back as ``MO`` and a compliant name would be silently rewritten. The
signal is capitalisation, and it is deliberately the only signal — see
:func:`_already_governed`.

**Longest match first.** A governed catalog contains multi-word terms —
``XREF`` for "Cross Reference", ``1MM`` for "One Million" — and a strict
word-by-word walk can never reach them: it asks for "Cross", gets nothing, and
emits ``CROSS_REFERENCE`` for a term the catalog abbreviates in one token. So
each position tries the longest run of remaining words the reverse index knows,
then shorter runs, then the single word.

**A word with no governed abbreviation is upper-cased, never clipped.**
``FRAUD``, ``MODEL``, ``STATE``. Shortening a word the catalog has not
abbreviated would be inventing an abbreviation, which is the one thing this
package will not do — the same rule, in the same spirit, as the length invariant
below.

The round-trip invariant
------------------------
This is the strongest claim the package makes, and it is worth stating exactly
rather than generously. For an identifier ``x``::

    to_physical_name(expand_identifier(x, catalog).phrase, catalog).physical == x

holds whenever, for every token of ``x``:

1. the token resolves against the vocabulary (``IdentifierExpansion.is_fully_known``);
2. the reverse index maps that token's long form **back to that same token**; and
3. the identifier already ends in a class word, or the policy is not appending
   one (see below).

Condition 2 is the whole of the difficulty, because expansion and abbreviation
are not inverses of each other and cannot be made so. A governed catalog is
authored long → short with one approved row per term, and inverting it produces
a many-to-one map in *both* directions:

* **Two tokens claim one long form.** A catalog that carries both the approved
  ``DT`` and the unapproved ``DTE`` for "Date" has to send "Date" to one of them,
  and the reverse index's documented tie-break sends it to ``DT``. So
  ``DTE`` → "Date" → ``DT``: the round trip does not return ``DTE``, it *corrects*
  it. That is the behaviour a governance pipeline wants and it is exactly what
  :func:`~acronymkit.governed.compliance.normalize` is for.
* **A token's long form is not the one the reverse index reversed.** ``LN`` is
  pinned to "Loan" while "Line" is also among its candidates, so
  ``abbreviate("Line")`` is ``LN`` and expanding ``LN`` gives "Loan". Start from
  the identifier and the trip is clean; start from the *word* "Line" and it is
  not, because the catalog records what a token means and several words can
  legitimately point at one token.
* **A word the catalog has never seen** passes through untouched in both
  directions — Title Cased on the way out, upper-cased on the way back — so it
  round-trips, but on the strength of nothing.

None of these is a fault to be patched. They are properties of inverting a
many-to-one map, and the honest response is to say where the invariant holds and
where it does not, which is what the three conditions above do.

There is a sharper way to put the same thing, and it is the statement worth
testing. Where the trip is not the identity it is not arbitrary — it is the
governed correction::

    to_physical_name(expand_identifier(x, c).phrase, c).physical == normalize(x, c)

An identifier built only from tokens the vocabulary approves is already its own
normal form, so the two readings agree and the trip returns ``x`` unchanged. An
identifier carrying an unapproved token comes back with that token replaced by
the approved one, which is the same rewrite ``normalize`` would have made. This
holds for every identifier in the fixture corpus and it is what a round-trip
test should assert, because it says something true about the names where the
identity does not hold instead of excluding them.

Length is a flag, never a truncation
------------------------------------
``NamingPolicy.enforce_name_length`` is not consulted here at all, and
:attr:`~acronymkit.governed.models.PhysicalName.truncated` is written ``False``
unconditionally. No policy, no argument and no code path in this function drops
or shortens a token. A pipeline that silently trimmed
``TXN_APPLNT_VERIF_STAT_CD`` to fit a platform limit would be inventing an
identifier nobody governs, at the exact moment the caller most needs to be told,
so an over-long name is reported by
:func:`~acronymkit.governed.compliance.is_compliant` with
``ComplianceReasonCode.EXCEEDS_MAX_LENGTH`` and returned in full.

The class word this function may append
---------------------------------------
``NamingPolicy.append_class_word_when_missing`` says a rendered name that does
not end in a class word should gain one, and neither ``NamingPolicy`` nor
``GovernedDictionary`` carries a field naming *which* class word that is. Rather
than invent one, this module names a default — :data:`DEFAULT_CLASS_WORD` — and
appends it **only when the caller's own vocabulary designates that token as a
class word**. A catalog that does not govern it gets nothing appended and the
shortfall is reported by ``is_compliant`` instead. So the function can restate
the caller's standard but never step outside it. The gap is reported: a
``NamingPolicy.default_class_word`` field would settle it in one line.

What is shared, and why it is shared rather than repeated
---------------------------------------------------------
Three verbs read the same names, and anything they could disagree about is kept
in exactly one place.

The digit-leading token repair — ``1MM`` splitting to ``('1', 'MM')`` and being
put back — is imported from :mod:`~acronymkit.governed.expansion`, where the
contract puts it. If expansion thought ``1MM`` was one token and this module
thought it was two, the package would render a name it had just expanded and get
a different one back. :data:`DEFAULT_CLASS_WORD` runs the other way:
:mod:`~acronymkit.governed.compliance` imports it from here, so the class word
``to_physical_name`` appends is the same one ``is_compliant`` suggests, and the
renderer cannot produce names the verifier then rejects.

Both are private cross-module imports, which is the price of the contract having
no shared-internals module. That is reported rather than worked around: a third
copy of either rule would be worse than the import.

Determinism
-----------
No I/O, no clock, no randomness, no module state. The answer is a function of
``(logical, dictionary, policy, custom)`` alone, so two processes with the same
vocabulary produce byte-identical audit records.

Worked examples use the fictional **Northwind Data Standards** (``NDS``) catalog
with synthetic ids. Nothing here describes a real organisation's standard.
"""

from __future__ import annotations

from typing import Mapping, NamedTuple, Optional, Union

from ..exceptions import ConfigurationError
from .dictionary import GovernedDictionary
from .enums import ExpansionSource
from .expansion import _rejoin_digit_tokens
from .models import GovernedEntry, PhysicalName, PhysicalToken
from .policy import NamingPolicy
from .tokenizer import split_identifier

__all__ = ["DEFAULT_CLASS_WORD", "to_physical_name"]


#: The class word appended to a name that lacks one, when
#: ``NamingPolicy.append_class_word_when_missing`` is on **and** the caller's
#: vocabulary designates this token as a class word. ``VAL``/"Value" is the
#: least opinionated class word there is: it says the column holds a value and
#: nothing more, so appending it adds a required structural element without
#: asserting anything about the data that the logical name did not already say.
#:
#: It is a module constant rather than a policy field because the contract has
#: no field for it. That is a gap, not a design: a catalog whose neutral class
#: word is ``IND`` or ``CD`` cannot express that here, and for such a catalog
#: this constant simply never fires — the append is guarded on
#: ``GovernedDictionary.class_word_for`` recognising it, so no name ever gains a
#: token the caller's own standard does not govern.
DEFAULT_CLASS_WORD = "VAL"


class _Rendered(NamedTuple):
    """One rendered token and the confidence the catalog attaches to it.

    :class:`~acronymkit.governed.models.PhysicalToken` carries no confidence
    field — a per-token confidence would be noise on a name whose summary is a
    single weakest-link figure — but the figure has to be computed from
    somewhere, so the entry's confidence is carried alongside the token until
    the name is assembled and then dropped.
    """

    token: PhysicalToken
    confidence: float


def _already_governed(dictionary: GovernedDictionary, word: str) -> Optional[_Rendered]:
    """Recognise a word that is already a governed token, and leave it alone.

    Logical names in the wild are not fully spelled out: "Transaction ID" and
    "Customer Acct Balance" arrive in schema-documentation exports every day, and
    so does every phrase the forward direction produces for a token the catalog
    approves without expanding — rule 4 of the resolution order answers ``SYSTEM``
    with ``SYSTEM``. Sending such a word through the reverse index does active
    harm: "Monthly" is a candidate long form of ``MO``, so an already-governed
    ``MONTHLY`` would come back as ``MO`` and the round trip would silently
    rewrite a compliant name.

    Checked **before** the reverse index for exactly that reason, and the signal
    is that the word is **written in capitals**. That is deliberately narrow.
    Matching any word that happens to equal a token would read the "in" of "Loan
    in Default" as the ``IN`` indicator class word and the "act" of an act of law
    as ``ACT``/Activity — turning a helpful rule into a source of silent,
    plausible-looking mistakes. A word a writer capitalised is a word they meant
    as an abbreviation; a word in title case is a word.

    Args:
        dictionary: The vocabulary to consult.
        word: A single word from the logical name.

    Returns:
        The rendered token, or ``None`` when the word is not capitalised or the
        vocabulary neither carries nor approves it.
    """
    if not word.isupper() or not any(character.isalpha() for character in word):
        return None
    entry = dictionary.lookup(word)
    if entry is not None:
        return _from_entry(word, entry)
    if dictionary.is_approved(word):
        # Approved with no catalog row to cite: an allow-list member, which is
        # rule 4 of the resolution order read backwards.
        return _Rendered(
            PhysicalToken(
                word=word,
                abbrev=word,
                source=ExpansionSource.APPROVED,
                entry_id=None,
            ),
            1.0,
        )
    return None


def _entry_source(entry: GovernedEntry) -> ExpansionSource:
    """Which provenance to record for a short form taken from ``entry``.

    This mirrors rule 3 of the resolution order — ``APPROVED`` when the token is
    itself the governed physical form, ``GOVERNED`` otherwise — with the overlay
    taking precedence as rule 1 requires.

    ``PINNED`` and ``SCORED`` are deliberately unreachable here. Both name a
    decision about *which long form a token means*, and the reverse direction is
    not asking that question: it starts from the long form. Recording ``PINNED``
    on a physical token because the entry behind it happens to carry a pin would
    claim that a pin settled this answer, when what settled it was the reverse
    index's own tie-break between tokens.

    Args:
        entry: The winning catalog entry.

    Returns:
        The provenance member to write on the :class:`PhysicalToken`.
    """
    if entry.source is ExpansionSource.CUSTOM:
        return ExpansionSource.CUSTOM
    if entry.keep_as_abbrev:
        return ExpansionSource.APPROVED
    return ExpansionSource.GOVERNED


def _governed_entry(
    base: GovernedDictionary,
    layered: GovernedDictionary,
    text: str,
    allow_override: bool,
) -> Optional[GovernedEntry]:
    """Resolve one word or phrase, honouring ``NamingPolicy.allow_override``.

    ``GovernedDictionary.abbreviate`` takes no policy argument, so the reverse
    index cannot apply the demotion rule itself. It is applied here, on the same
    terms the resolution order sets out for the forward direction: an overlay
    entry that **contradicts** a governed answer is refused, and an overlay entry
    for something the catalog says nothing about is kept, because overriding
    nothing is not an override.

    The demotion reaches only the overlay this call layered. An overlay already
    built into ``base`` cannot be peeled off — ``abbreviate`` offers no way to
    ask what the catalog would have said without it — and that is the
    dictionary's own business, settled when it was constructed.

    Args:
        base: The dictionary as supplied, without this call's overlay.
        layered: The same dictionary with this call's ``custom=`` overlay on top.
        text: One word, or a run of words joined by single spaces.
        allow_override: ``NamingPolicy.allow_override``.

    Returns:
        The entry that supplies the short form, or ``None``.
    """
    entry = layered.abbreviate(text)
    if entry is None or allow_override or entry.source is not ExpansionSource.CUSTOM:
        return entry
    governed = base.abbreviate(text)
    return governed if governed is not None else entry


def _from_entry(text: str, entry: GovernedEntry) -> _Rendered:
    """Build the record for a word or phrase the catalog abbreviates.

    Args:
        text: The logical word, or the run of words, that matched.
        entry: The catalog entry supplying the short form.

    Returns:
        The rendered token, carrying the entry's own provenance and confidence
        rather than the caller's — an overlay entry that says ``0.9`` must not
        be reported as though the catalog had confirmed it.
    """
    return _Rendered(
        PhysicalToken(
            word=text,
            abbrev=entry.token,
            source=_entry_source(entry),
            entry_id=entry.entry_id,
        ),
        entry.confidence,
    )


def _unabbreviated(dictionary: GovernedDictionary, word: str) -> _Rendered:
    """Render a word the reverse index does not abbreviate: upper-case it.

    The emitted string is ``word.upper()`` either way — this function never
    shortens anything — and what it decides is only what the audit record may
    claim. Two outcomes:

    * the upper-cased form is a token the vocabulary **approves** even though no
      catalog row expands it, so ``Score`` → ``SCORE`` and ``Total`` → ``TOTAL``
      are governed answers rather than fallbacks. Without this a name built
      entirely from permitted vocabulary would report zero confidence, which is
      the exact opposite of the truth;
    * nothing knows it, so it is marked ``PASSTHROUGH`` with zero confidence —
      not low confidence in an answer but, as in the forward direction, the
      absence of one.

    Args:
        dictionary: The vocabulary, with any call-time overlay applied.
        word: A single word from the logical name.

    Returns:
        The rendered token. An allow-listed word carries confidence ``1.0``: the
        list is the standard saying the token may stand, and there is no entry to
        carry anything lower.
    """
    upper = word.upper()
    approved = dictionary.is_approved(upper)
    return _Rendered(
        PhysicalToken(
            word=word,
            abbrev=upper,
            source=ExpansionSource.APPROVED if approved else ExpansionSource.PASSTHROUGH,
            entry_id=None,
        ),
        1.0 if approved else 0.0,
    )


def _render(
    words: tuple[str, ...],
    base: GovernedDictionary,
    layered: GovernedDictionary,
    allow_override: bool,
) -> tuple[_Rendered, ...]:
    """Turn logical words into governed short forms, longest match first.

    At each position the longest remaining run of words the reverse index knows
    wins, so a multi-word catalog term is reached as one token rather than
    spelled out word by word. A single-word walk would be linear but could never
    reach ``XREF`` or ``1MM``, so the longest match has to stay.

    **The scan is bounded by the catalog, not by the name.** It used to run from
    the end of the name back to the current position, which is quadratic in the
    words: eighteen words cost 171 lookups. Almost all of them were asking
    whether a reverse index whose wordiest key is two words long contains an
    eighteen-word key — a question whose answer is fixed at construction. The
    window is now capped at
    :attr:`~acronymkit.governed.dictionary.GovernedDictionary.longest_long_form_words`,
    which cannot change the outcome because a run longer than the wordiest key
    cannot match anything, and makes the cost linear in the name and bounded by
    the vocabulary. Names get longer; catalog terms do not.

    Args:
        words: The logical name's words, in order, as they were written.
        base: The dictionary as supplied.
        layered: The same dictionary with this call's overlay on top.
        allow_override: ``NamingPolicy.allow_override``.

    Returns:
        One record per emitted token, in order. A multi-word match yields a
        single record whose ``word`` is the whole matched phrase, because the
        phrase is the unit the catalog abbreviated.
    """
    rendered: list[_Rendered] = []
    total = len(words)
    start = 0
    while start < total:
        verbatim = _already_governed(layered, words[start])
        if verbatim is not None:
            rendered.append(verbatim)
            start += 1
            continue
        # At least one word, so a name is always made progress on even when the
        # vocabulary holds no long form at all and the bound is zero.
        window = max(layered.longest_long_form_words, 1)
        for end in range(min(total, start + window), start, -1):
            text = " ".join(words[start:end])
            entry = _governed_entry(base, layered, text, allow_override)
            if entry is not None:
                rendered.append(_from_entry(text, entry))
                start = end
                break
        else:
            # Not even the single word is a governed long form, so it is
            # upper-cased exactly as it stands; see _unabbreviated for what the
            # audit record may then claim about it.
            rendered.append(_unabbreviated(layered, words[start]))
            start += 1
    return tuple(rendered)


def _appendable_class_word(
    dictionary: GovernedDictionary,
    policy: NamingPolicy,
    rendered: tuple[_Rendered, ...],
) -> Optional[_Rendered]:
    """The class word to append to a name that lacks one, if there is one.

    Returns ``None`` — leaving the name exactly as rendered — when the policy
    does not ask for an append, when the name already ends in a class word (which
    covers a name that *is* a class word, so ``ID`` never becomes ``ID_VAL``), or
    when the caller's vocabulary does not govern :data:`DEFAULT_CLASS_WORD`. That
    last case is the honest failure mode: with no field naming the class word to
    append, appending one the catalog has never approved would produce a name
    that fails its own standard.

    Args:
        dictionary: The vocabulary, with this call's overlay applied.
        policy: The active policy.
        rendered: The tokens rendered so far.

    Returns:
        The record to append, or ``None``.
    """
    if not policy.append_class_word_when_missing or not rendered:
        return None
    if dictionary.class_word_for(rendered[-1].token.abbrev) is not None:
        return None
    long_form = dictionary.class_word_for(DEFAULT_CLASS_WORD)
    if long_form is None:
        return None
    entry = dictionary.lookup(DEFAULT_CLASS_WORD)
    if entry is not None:
        return _from_entry(long_form, entry)
    # The class word is designated by the class-word map but has no catalog row
    # of its own, so there is no entry id to cite and nothing to lower the
    # confidence: the map is the governed source here.
    return _Rendered(
        PhysicalToken(
            word=long_form,
            abbrev=DEFAULT_CLASS_WORD,
            source=ExpansionSource.GOVERNED,
            entry_id=None,
        ),
        1.0,
    )


def to_physical_name(
    logical: str,
    dictionary: GovernedDictionary,
    policy: Optional[NamingPolicy] = None,
    *,
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
) -> PhysicalName:
    """Render a logical name as a governed physical name, in ``UPPER_SNAKE``.

    Each word is abbreviated through the dictionary's reverse index, longest
    catalog term first; a word the catalog does not abbreviate is upper-cased
    exactly as it stands and is never shortened. Every emitted token carries the
    catalog row behind it, so the answer can be audited word by word.

    See the module docstring for the round-trip invariant this function is one
    half of, and for the three ways the reverse index is not a mathematical
    inverse of expansion.

    Args:
        logical: The logical name — "Transaction Identifier", "customer account
            open date", "Fraud Risk Score". Split by
            :func:`~acronymkit.governed.tokenizer.split_identifier`, so any of
            the separator, camelCase and letter/digit conventions it understands
            are accepted. An empty or separator-only name yields an empty
            physical name rather than an error, so a blank cell does not stop a
            batch.
        dictionary: The governed vocabulary. Required: a governed verb with no
            governed vocabulary is a contradiction. An **empty**
            ``GovernedDictionary()`` is the supported way to ask for
            upper-casing with nothing governed.
        policy: How to apply the vocabulary. ``None`` means
            :meth:`~acronymkit.governed.policy.NamingPolicy.governed_default`.
            Only ``allow_override`` and ``append_class_word_when_missing`` are
            read here; ``enforce_name_length`` is deliberately not consulted, and
            no setting of it can shorten a name.
        custom: A caller-supplied overlay layered for this call only, as a plain
            ``{"XYZ": "Exchange"}`` mapping or with full
            :class:`~acronymkit.governed.models.GovernedEntry` values. Under
            ``allow_override=False`` an overlay entry that contradicts the
            catalog is refused while one for a word the catalog does not know is
            still applied.

    Returns:
        A :class:`~acronymkit.governed.models.PhysicalName`. ``truncated`` is
        always ``False``; ``term_id`` is set when the term index holds the whole
        logical name; ``confidence`` is the weakest link across the tokens, where
        a word the catalog does not govern contributes ``0.0`` — not low
        confidence in an answer but, as in the forward direction, the absence of
        one. The word that caused it is the token whose ``source`` is
        ``PASSTHROUGH``.

    Raises:
        ConfigurationError: If ``dictionary`` is ``None``.

    Example:
        >>> from acronymkit.governed import GovernedDictionary, to_physical_name
        >>> catalog = GovernedDictionary.from_long_to_short(
        ...     {"Transaction": "TXN", "Identifier": "ID"}
        ... )
        >>> to_physical_name("Transaction Identifier", catalog).physical
        'TXN_ID'
        >>> to_physical_name("Transaction Fraud Identifier", catalog).physical
        'TXN_FRAUD_ID'
    """
    if dictionary is None:
        raise ConfigurationError(
            "to_physical_name requires a governed vocabulary, and dictionary was None. "
            "Pass a GovernedDictionary; an empty GovernedDictionary() is the supported "
            "way to ask for a name with nothing governed."
        )
    active = NamingPolicy.governed_default() if policy is None else policy
    layered = dictionary.with_custom(custom) if custom else dictionary

    words = _rejoin_digit_tokens(split_identifier(logical), layered, active)
    rendered = _render(words, dictionary, layered, active.allow_override)
    appended = _appendable_class_word(layered, active, rendered)
    if appended is not None:
        rendered = (*rendered, appended)

    return PhysicalName(
        logical=logical,
        physical="_".join(item.token.abbrev for item in rendered),
        tokens=tuple(item.token for item in rendered),
        term_id=layered.term_id_for(logical),
        confidence=min((item.confidence for item in rendered), default=0.0),
        # Never anything else, under any policy. See the module docstring.
        truncated=False,
    )
