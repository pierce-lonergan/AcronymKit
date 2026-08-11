"""Corpus-level audit: what a governed vocabulary does to a whole schema.

The other verbs answer one name at a time. A team adopting a standard has a
different question and has it on the first day — *what will this do to our
schema, and what is our catalog missing?* — and answering it means calling
:func:`~acronymkit.governed.expansion.expand_identifier` once per column and
reducing the results. The reduction is mechanical, every team would write it
slightly differently, and the differences would all be in the same two places:
what counts as an unknown token worth acting on, and what a round trip that
does not return its input actually means. So it is written once, here.

:func:`audit_identifiers` makes one pass over a corpus of physical names and
returns a :class:`CorpusAudit`. :func:`suggest_catalog_additions` turns the
unknown-token half of that into a work list, and :func:`render_audit` prints
the whole thing for a person to read.

The ranked unknown-token list is the part to look at first
----------------------------------------------------------
It is the catalog's backlog in priority order: every token the vocabulary does
not cover, how often it appears, in how many of the corpus's identifiers, and an
example column to look at. A standard that has never been pointed at a live
schema is mostly complete in the places somebody thought about; the ranked list
is where the gap between the standard and the data shows up, and it is the one
output that turns "our catalog is incomplete" into a finite list of rows to write.

This module adds no judgement of its own
----------------------------------------
Every count here is a count of something one of the existing verbs already
said. Nothing is re-derived, no token is resolved by a rule that lives in this
file, and an audit run twice over one corpus and one vocabulary produces the
same payload — the subsystem is context-free, so a corpus cannot change what a
token means. This module is arithmetic over the answers, and if a figure here
looks wrong the verb that produced it is where to look.

The one inference, and the fence around it
------------------------------------------
Exactly one thing in this module is not a count. When an unknown token is
itself a **word the catalog governs** — a schema that spells out ``CUSTOMER``
where the standard says ``CUST`` — the reverse index already knows it, and
saying so is reading the catalog rather than guessing at it. That row is
carried on :attr:`UnknownToken.governed_word` and it is fenced by three
conditions, each of which exists to stop a guess getting through: the row's
``canonical`` must **be** that word rather than merely list it as a candidate,
the short form it names must itself be approved, and it must differ from the
token. Without the first, ``LINE`` would reach ``LN`` and ``LN`` means *Loan*.

Everything else is left alone. :class:`CatalogSuggestion` exists to carry an
unknown token to the person who owns the catalog, and its ``proposed_long_form``
is empty for every token the catalog is silent about — which is most of them,
and is the point. A suggestion is a request for a decision, never an answer,
and the class says so in every field that could be mistaken for one.

Reading the round trip honestly
-------------------------------
``to_physical_name(expand_identifier(x).phrase).physical != x`` is the sharpest
signal a corpus gives about a catalog, and reported as a bare count it is
misleading, because most of the names it flags are working exactly as designed.
Expansion and abbreviation are not inverses — see
:mod:`acronymkit.governed.naming` — so an identifier carrying an unapproved
token comes back with the approved one in its place. That is the standard
correcting the schema, not the catalog disagreeing with itself.

So the trip is reported three ways, not two:

* **stable** — the name came back as it was written;
* **corrected** — it came back as ``normalize`` would have rewritten it, which
  is the governed correction and is expected;
* **broken** — it came back as neither, which is the case worth investigating,
  and the only one whose identifiers are retained in full.

A corpus with no broken round trips says the catalog is internally consistent
over the names that corpus contains. It says nothing about names it does not.

One setting is taken out of the comparison, and only one:
``append_class_word_when_missing``. Rendering appends a class word and
``normalize`` never does, so leaving it on would report every name that predates
the standard as evidence of a catalog disagreeing with itself. That shortfall is
already reported once, by ``MISSING_CLASS_WORD``, and reporting it a second time
as something it is not would bury the handful of names where the two directions
genuinely part. See :func:`_trip_policy`.

What this costs
---------------
Four calls per **distinct** identifier — expand, check, render back, and
``normalize`` only where the trip moved — so an audit costs a small multiple of
a single expansion, and the dominant term is the corpus size rather than the
catalog size. Identifiers are de-duplicated as they stream, which matters
because one warehouse schema repeats ``LAST_CHG_TS`` across every table it has.
The audit holds one small record per distinct identifier, which is what
de-duplication requires; nothing holds a whole
:class:`~acronymkit.governed.models.IdentifierExpansion`, because a corpus of
fifty thousand names would be a million token records and none of them survives
into the answer.

Worked examples use the fictional **Northwind Data Standards** (``NDS``)
catalog with synthetic ids. Nothing here describes a real organisation's schema
or standard.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Optional, Union

from pydantic import Field

from ..exceptions import ConfigurationError
from .compliance import is_compliant, normalize
from .dictionary import GovernedDictionary, _phrase_key
from .enums import ComplianceReasonCode, UnknownPolicy, Verdict
from .expansion import expand_identifier
from .models import GovernedEntry, _FrozenModel
from .naming import to_physical_name
from .policy import NamingPolicy

__all__ = [
    "CatalogSuggestion",
    "CorpusAudit",
    "FindingTally",
    "IdentifierAudit",
    "RoundTripBreak",
    "UnknownToken",
    "audit_identifiers",
    "render_audit",
    "suggest_catalog_additions",
]


# --------------------------------------------------------------------------
# The payload
# --------------------------------------------------------------------------
class UnknownToken(_FrozenModel):
    """One token the vocabulary does not cover, and how much of the corpus it costs.

    Ranked by :attr:`occurrences`, so the tuple of these on a
    :class:`CorpusAudit` reads top to bottom as the order to write catalog rows
    in.

    Only tokens holding at least one letter appear. An ordinal — the ``1`` and
    ``2`` of ``ADDR_LINE_1_TXT`` — is an unknown token by the expansion
    contract and is not a gap in anybody's catalog, so it is counted apart in
    :attr:`CorpusAudit.ordinal_occurrences` rather than ranked here. That is the
    same call :mod:`acronymkit.governed.compliance` makes when it declines to
    give an ordinal a reason code, made again for the same reason: no catalog
    row would fix it.
    """

    token: str = Field(
        description="The token, upper-cased. Lookup is case-insensitive, so a schema that "
        "writes both custmr and CUSTMR contributes to one row here rather than two."
    )
    occurrences: int = Field(
        description="How many times the token appears across the corpus, counting every "
        "appearance — a name that uses it three times contributes three. This is the ranking "
        "key, because it is the size of the hole."
    )
    identifier_count: int = Field(
        description="How many identifiers contain it at least once. Reported alongside the "
        "occurrence count because the two say different things: one token used forty times "
        "inside one name is a naming quirk, and the same token in forty names is a gap in the "
        "standard."
    )
    examples: tuple[str, ...] = Field(
        default=(),
        description="Identifiers the token was seen in, in corpus order, capped by the "
        "audit's max_examples. Enough to go and look at, and deliberately not the full list: "
        "on a large corpus the full list is most of the corpus.",
    )
    governed_word: Optional[GovernedEntry] = Field(
        default=None,
        description="The catalog row that already governs this token read as a WORD rather "
        "than as an abbreviation — the schema spelled out CUSTOMER where the standard says "
        "CUST. When this is set the item is not a missing row at all; it is a name to rewrite, "
        "and the row names what to write. None for every token the catalog is silent about, "
        "which is the common case. The conditions under which it is set are in the module "
        "docstring, and they exist so that a candidate-only match (LINE reaching LN, which "
        "means Loan) can never produce one.",
    )

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.token} x{self.occurrences}"


class FindingTally(_FrozenModel):
    """One compliance reason code, and how much of the corpus carries it.

    The reason a corpus-level audit exists at all: "four thousand columns do not
    end in a class word" is one line a governance function can act on, and four
    thousand individual findings saying the same thing is not.

    Only codes carried by a ``FAIL`` verdict are tallied. Passing findings are
    recorded per name by
    :func:`~acronymkit.governed.compliance.is_compliant` — a review of one name
    needs to see why it was accepted — but a corpus-level count of names that
    passed is not a work item, and carrying it would double this tuple to say
    nothing actionable.
    """

    code: ComplianceReasonCode = Field(
        description="The machine-readable reason. This is what to filter and route on; the "
        "free-text detail that accompanies it per name is deliberately not aggregated, "
        "because it names a token and a corpus-level count of it would be meaningless."
    )
    occurrences: int = Field(
        description="How many findings across the corpus carry this code. A name can "
        "contribute several — six unapproved tokens in one name are six findings."
    )
    identifier_count: int = Field(
        description="How many identifiers carry the code at least once. This is the number to "
        "quote as 'how many columns have this problem'."
    )
    examples: tuple[str, ...] = Field(
        default=(),
        description="Identifiers carrying the code, in corpus order, capped by the audit's "
        "max_examples.",
    )

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.code.value} x{self.occurrences}"


class RoundTripBreak(_FrozenModel):
    """An identifier whose round trip came back as neither itself nor its governed form.

    The strongest evidence a corpus gives that a catalog disagrees with itself:
    expanding the name and rendering the phrase back produced a third name, so
    the forward and reverse readings of the vocabulary do not agree about it.
    The usual cause is two rows claiming one long form in a way the reverse
    index's tie-break settles the other way; see the limits section of
    ``docs/GOVERNED_NAMING.md``.

    An identifier that comes back as ``normalize`` would have rewritten it is
    **not** one of these. That is the standard correcting an unapproved token,
    it is what the package is for, and it is counted separately in
    :attr:`CorpusAudit.round_trip_corrected`.
    """

    identifier: str = Field(description="The identifier as supplied.")
    phrase: str = Field(
        description="The phrase the forward direction produced, carried because it is the "
        "half of the trip a reviewer has to read to see where the two directions part."
    )
    physical: str = Field(description="What rendering the phrase back produced.")
    governed_form: str = Field(
        description="What normalize would have produced. The trip landing here instead of on "
        "this is what makes the row a break rather than a correction."
    )

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.identifier} -> {self.physical}"


class IdentifierAudit(_FrozenModel):
    """What the audit found about one identifier.

    Retained only for identifiers there is something to say about — not fully
    known, not compliant, or the round trip moved. A clean name's record would
    carry nothing the corpus counts do not already hold, and on a corpus of
    fifty thousand columns the tuple of them would be the largest thing in the
    payload. Turn the whole tuple off with ``keep_details=False``.
    """

    identifier: str = Field(description="The identifier as supplied.")
    occurrences: int = Field(
        description="How many times this exact identifier appeared in the corpus. One in a "
        "column list from a single table; more when a name repeats across tables, which is "
        "the normal case for a warehouse."
    )
    is_fully_known: bool = Field(
        description="Carried through from IdentifierExpansion: every token resolved. True "
        "vacuously for an identifier that tokenises to nothing, because no token failed."
    )
    compliant: bool = Field(description="Carried through from ComplianceResult.")
    unknown_tokens: tuple[str, ...] = Field(
        default=(),
        description="The tokens that did not resolve, upper-cased, in identifier order and "
        "de-duplicated. Ordinals are included here, unlike in the ranked corpus list, because "
        "at the level of one name they are part of the reason it is not fully known.",
    )
    codes: tuple[ComplianceReasonCode, ...] = Field(
        default=(),
        description="The distinct failing reason codes, in the order the check produced them. "
        "The findings themselves are not carried: they hold a sentence per token, and "
        "re-running is_compliant on one name is cheap.",
    )
    round_trip: Optional[str] = Field(
        default=None,
        description="What the round trip produced, when that is not the identifier itself. "
        "None means the name came back exactly as it was written.",
    )
    governed_form: Optional[str] = Field(
        default=None,
        description="What normalize produces for this identifier, filled in only when the "
        "round trip moved — comparing the two is what separates a governed correction from a "
        "catalog inconsistency, and computing it for a name that did not move would be work "
        "spent on an answer nobody reads.",
    )

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.identifier}: {'compliant' if self.compliant else 'not compliant'}"


class CorpusAudit(_FrozenModel):
    """What one governed vocabulary does to one corpus of physical names.

    Every field is a count of something the three verbs said, or a ranking of
    those counts. Nothing here is inferred; see the module docstring for the one
    exception and the fence around it.
    """

    total: int = Field(
        description="Identifiers audited, exactly as supplied — duplicates counted again, "
        "blanks counted. This is the denominator for every other count."
    )
    distinct: int = Field(
        description="How many of them were distinct. The gap between this and total is what "
        "de-duplication saved, and it is also worth reading: a schema export whose column "
        "names are largely repeats is one where a small catalog goes a long way."
    )
    empty: int = Field(
        description="Identifiers that tokenised to nothing — blank cells and separator-only "
        "rows. Counted rather than skipped so that a corpus which is half empty cannot look "
        "like a corpus that is fully known."
    )
    fully_known: int = Field(
        description="Identifiers every token of which resolved. An empty identifier is "
        "counted here, vacuously, because that is what IdentifierExpansion.is_fully_known "
        "says about it and this module reports the verbs rather than reinterpreting them."
    )
    partially_known: int = Field(
        description="Identifiers with at least one token the vocabulary does not contain. "
        "Together with fully_known this exhausts the corpus."
    )
    compliant: int = Field(description="Identifiers with no failing compliance finding.")
    non_compliant: int = Field(
        description="Identifiers with at least one. Together with compliant this exhausts "
        "the corpus. Note that being fully known and being compliant are different "
        "properties: NUM expands to Number and is not approved."
    )
    unknown_tokens: tuple[UnknownToken, ...] = Field(
        default=(),
        description="Every letter-bearing token the vocabulary does not cover, ranked by "
        "occurrence count and then by token so the order is total. This is the catalog "
        "backlog.",
    )
    ordinal_occurrences: int = Field(
        default=0,
        description="Appearances of unknown tokens holding no letters — the 1 and 2 of "
        "ADDR_LINE_1_TXT. Kept out of the ranking because no catalog row would cover one, "
        "and reported here rather than dropped so that the two numbers still add up.",
    )
    findings: tuple[FindingTally, ...] = Field(
        default=(),
        description="Failing compliance findings collapsed by reason code, ranked by "
        "occurrence count and then by code.",
    )
    round_trip_stable: int = Field(
        default=0,
        description="Identifiers the round trip returned unchanged.",
    )
    round_trip_corrected: int = Field(
        default=0,
        description="Identifiers the round trip returned as normalize would have rewritten "
        "them. Expected, not a fault: the standard correcting an unapproved token is the "
        "package working.",
    )
    round_trip_inconsistent: int = Field(
        default=0,
        description="Identifiers the round trip returned as neither. These three counts are "
        "over the corpus as supplied and together they exhaust it.",
    )
    round_trip_breaks: tuple[RoundTripBreak, ...] = Field(
        default=(),
        description="One record per DISTINCT inconsistent identifier, in corpus order, so "
        "this tuple is shorter than round_trip_inconsistent whenever a name repeats. Retained "
        "in full rather than capped, because this is the finding an audit exists to surface "
        "and a count alone would not be actionable.",
    )
    details: tuple[IdentifierAudit, ...] = Field(
        default=(),
        description="Per-identifier records, in corpus order, for the identifiers there is "
        "something to say about. Empty when the audit ran with keep_details=False.",
    )

    @property
    def unknown_token_count(self) -> int:
        """How many distinct letter-bearing tokens the vocabulary does not cover."""
        return len(self.unknown_tokens)

    def __str__(self) -> str:  # pragma: no cover - display helper
        return (
            f"{self.total} identifiers, {self.fully_known} fully known, "
            f"{self.unknown_token_count} unknown tokens"
        )


class CatalogSuggestion(_FrozenModel):
    """A request for a human decision about one token the catalog does not cover.

    **This is not an expansion and must never be used as one.** Nothing on it
    may be fed back into
    :func:`~acronymkit.governed.expansion.expand_token` or
    :func:`~acronymkit.governed.naming.to_physical_name` as though the catalog
    had said it. The library's contract is that an unknown token comes back
    marked unknown with zero confidence; a suggestion does not change that, and
    the only thing that does is somebody adding a row.

    There is deliberately **no confidence field**. A number here would invite a
    consumer to compare a suggestion against a governed answer on one scale,
    and there is no scale on which the two belong: one is what the standard
    says and the other is a question waiting for somebody to answer it.

    :attr:`proposed_long_form` is empty for every token the catalog is silent
    about, which is most of them. When it is set, it is the catalog's own
    wording read back out of the reverse index rather than anything this module
    thought of — and in that case the item is usually not a missing row at all
    but a column name to rewrite.
    """

    token: str = Field(description="The unknown token, upper-cased.")
    occurrences: int = Field(description="How many times it appears across the corpus.")
    identifier_count: int = Field(description="How many identifiers contain it.")
    examples: tuple[str, ...] = Field(
        default=(),
        description="Identifiers to look at while deciding, in corpus order.",
    )
    proposed_long_form: Optional[str] = Field(
        default=None,
        description="A PROPOSAL, not a governed answer, and None unless the catalog itself "
        "supplied the wording: it is set only when the token is a word the reverse index "
        "already carries as some row's canonical long form. No other route can fill it — "
        "nothing here stems, matches fuzzily or asks a model — so None is the honest and "
        "common answer, and a consumer that treats a filled value as an expansion has "
        "misread the field.",
    )
    proposed_abbreviation: Optional[str] = Field(
        default=None,
        description="The approved short form the catalog already names for that long form, "
        "when there is one. This is the actionable half: the decision being asked for is "
        "usually not 'what does this token mean' but 'should these columns be written this "
        "way instead'. Set and unset together with proposed_long_form.",
    )
    entry_id: Optional[str] = Field(
        default=None,
        description="The catalog row the proposal was read out of, so a reviewer can go and "
        "look at it instead of taking this payload's word for anything.",
    )
    basis: Optional[str] = Field(
        default=None,
        description="One sentence saying where the proposal came from and what decision it "
        "asks for. None when there is no proposal, which is the case where the honest thing "
        "to say is nothing at all.",
    )
    is_governed: bool = Field(
        default=False,
        description="Always False. Every other object this package returns carries an "
        "ExpansionSource saying which rule produced it, and a consumer that has learned to "
        "check provenance should find an answer here rather than a missing field. It is "
        "written by this module and this module writes it False.",
    )

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.token} x{self.occurrences} (undecided)"


# --------------------------------------------------------------------------
# The pass
# --------------------------------------------------------------------------
class _Observation:
    """What one distinct identifier contributes, computed once and reused.

    A plain slotted object rather than one of the frozen models above: it is
    private, it is mutated once per repeat to count occurrences, and there is
    one of these per distinct identifier — on a corpus of fifty thousand columns
    the difference between this and a validated model is the difference between
    a few megabytes and a few tens of them.
    """

    __slots__ = (
        "backlog",
        "codes",
        "compliant",
        "empty",
        "governed_form",
        "is_fully_known",
        "occurrences",
        "ordinals",
        "phrase",
        "round_trip",
        "unknown",
    )

    def __init__(
        self,
        *,
        unknown: tuple[str, ...],
        backlog: tuple[tuple[str, int], ...],
        ordinals: int,
        is_fully_known: bool,
        compliant: bool,
        codes: tuple[tuple[ComplianceReasonCode, int], ...],
        empty: bool,
        phrase: str,
        round_trip: Optional[str],
        governed_form: str,
    ) -> None:
        """Record one identifier's contribution.

        Args:
            unknown: Every distinct unknown token, in identifier order, for the
                per-identifier record — where an ordinal belongs, because at the
                level of one name it is part of why the name is not fully known.
            backlog: The letter-bearing ones with their count inside this
                identifier, which is what the corpus ranking is built from. Held
                apart from ``unknown`` so the corpus loop does not re-decide
                which tokens are ordinals once per repeat of a name.
            ordinals: Appearances of unknown tokens holding no letters.
            is_fully_known: From the expansion.
            compliant: From the compliance check.
            codes: Failing reason codes with their count inside this identifier.
            empty: Whether the identifier tokenised to nothing.
            phrase: The expanded phrase, kept only when the round trip moved.
            round_trip: What the trip produced, when it is not the identifier.
                ``None`` is the one flag saying the trip did not move, and the
                two fields below are read only when it is not ``None``.
            governed_form: What ``normalize`` produces, when the trip moved, and
                ``""`` when it did not — not because that is the answer, but
                because it was never asked for.
        """
        self.unknown = unknown
        self.backlog = backlog
        self.ordinals = ordinals
        self.is_fully_known = is_fully_known
        self.compliant = compliant
        self.codes = codes
        self.empty = empty
        self.phrase = phrase
        self.round_trip = round_trip
        self.governed_form = governed_form
        self.occurrences = 0

    @property
    def notable(self) -> bool:
        """Whether there is anything to say about this identifier beyond a count."""
        return not self.is_fully_known or not self.compliant or self.round_trip is not None


def _trip_policy(policy: NamingPolicy) -> NamingPolicy:
    """The policy the round trip is rendered under: the caller's, minus the append.

    ``append_class_word_when_missing`` is the one setting that would make the
    trip disagree with ``normalize`` for a reason that says nothing about the
    catalog. A name that does not end in a class word comes back with one
    appended, ``normalize`` never appends, and the two therefore differ on every
    such name — which on a schema that predates the standard is thousands of
    them, all reported as evidence of a catalog that disagrees with itself when
    the only thing that happened is that a renderer added a token a verifier
    would not.

    The shortfall is not lost by switching it off: it is exactly what
    ``ComplianceReasonCode.MISSING_CLASS_WORD`` already reports, once, in the
    findings tally. And the invariant this comparison is testing is stated with
    the same carve-out — see the round-trip conditions in
    :mod:`acronymkit.governed.naming`, whose third condition is that the
    identifier already ends in a class word or the policy is not appending one.
    This makes the second half of that condition true rather than testing the
    invariant outside the domain it was stated over.

    Args:
        policy: The caller's policy.

    Returns:
        The same policy when it does not append, and a copy that does not
        otherwise. Everything else the caller set is carried through.
    """
    if not policy.append_class_word_when_missing:
        return policy
    return policy.model_copy(update={"append_class_word_when_missing": False})


def _observe(
    identifier: str,
    dictionary: GovernedDictionary,
    policy: NamingPolicy,
    trip_policy: NamingPolicy,
) -> _Observation:
    """Run the three verbs over one identifier and keep only what the audit needs.

    ``normalize`` is the fourth call and is made only when the round trip moved,
    which on a corpus written to the standard is a small minority of names. It
    is what separates a governed correction from a catalog inconsistency, and
    computing it for a name that came back unchanged would answer a question
    nobody asked.

    Args:
        identifier: One physical name, already coerced to a string.
        dictionary: The vocabulary, with any overlay already layered on.
        policy: The resolved policy.
        trip_policy: The policy the reverse direction is rendered under; see
            :func:`_trip_policy` for the one field that differs and why.

    Returns:
        The observation, with its occurrence count still at zero — the caller
        owns that, because the same observation serves every repeat.
    """
    expansion = expand_identifier(identifier, dictionary, policy)
    compliance = is_compliant(identifier, dictionary, policy)
    physical = to_physical_name(expansion.phrase, dictionary, trip_policy).physical

    unknown: dict[str, int] = {}
    ordinals = 0
    for token in expansion.tokens:
        if token.is_known:
            continue
        key = token.raw.strip().upper()
        if not key:
            continue
        unknown[key] = unknown.get(key, 0) + 1
        if not any(character.isalpha() for character in key):
            ordinals += 1

    codes: dict[ComplianceReasonCode, int] = {}
    for reason in compliance.reasons:
        if reason.verdict is Verdict.FAIL:
            codes[reason.code] = codes.get(reason.code, 0) + 1

    moved = physical != identifier
    return _Observation(
        unknown=tuple(unknown),
        backlog=tuple(
            (token, count)
            for token, count in unknown.items()
            if any(character.isalpha() for character in token)
        ),
        ordinals=ordinals,
        is_fully_known=expansion.is_fully_known,
        compliant=compliance.compliant,
        codes=tuple(codes.items()),
        empty=not expansion.tokens,
        phrase=expansion.phrase if moved else "",
        round_trip=physical if moved else None,
        governed_form=normalize(identifier, dictionary, policy) if moved else "",
    )


class _Tally:
    """A running count of one key, with the identifiers it was first seen in.

    Occurrences and identifier counts are kept apart because they answer
    different questions — see :attr:`UnknownToken.identifier_count` — and the
    examples are capped so that a key appearing in most of the corpus does not
    retain most of the corpus.
    """

    __slots__ = ("examples", "identifiers", "occurrences")

    def __init__(self) -> None:
        """Start an empty tally."""
        self.occurrences = 0
        self.identifiers = 0
        self.examples: list[str] = []

    def add(self, count: int, identifier: str, first_seen: bool, max_examples: int) -> None:
        """Fold in one identifier's contribution.

        Args:
            count: Appearances of the key inside this identifier.
            identifier: The identifier, for the example list.
            first_seen: Whether this is the identifier's first appearance in the
                corpus. Examples are recorded only then, so a name repeated
                across forty tables does not fill the list forty times.
            max_examples: How many examples to retain.
        """
        self.occurrences += count
        self.identifiers += 1
        if first_seen and len(self.examples) < max_examples:
            self.examples.append(identifier)


def _governed_word(dictionary: GovernedDictionary, token: str) -> Optional[GovernedEntry]:
    """The catalog row that governs ``token`` read as a word, if there is one.

    The single inference in this module, and the three conditions are the fence
    around it:

    1. the reverse index must know the word at all;
    2. the row's ``canonical`` must **be** that word, not merely list it among
       its candidates — without this, ``LINE`` reaches the ``LN`` row, whose
       canonical is *Loan*, and the audit would propose rewriting a line number
       as a loan;
    3. the short form the row names must itself be approved, which is the same
       rule :func:`~acronymkit.governed.compliance._approved_form` applies for
       the same reason: rewriting an unapproved token to another unapproved
       token has fixed nothing.

    The comparison uses the reverse index's own key function, so a row is
    matched here exactly when the index would have matched it.

    Args:
        dictionary: The vocabulary, with any overlay layered on.
        token: An unknown token, upper-cased.

    Returns:
        The row, or ``None`` — which is the answer for every token the catalog
        is silent about, and there is nothing further this module will try.
    """
    entry = dictionary.abbreviate(token)
    if entry is None or entry.token == token:
        return None
    if _phrase_key(entry.canonical) != _phrase_key(token):
        return None
    return entry if dictionary.is_approved(entry.token) else None


def _require(dictionary: Optional[GovernedDictionary], policy: NamingPolicy) -> GovernedDictionary:
    """Refuse the two argument combinations an audit cannot be run under.

    A governed verb with no governed vocabulary is a contradiction, exactly as
    it is for every other verb here.

    ``UnknownPolicy.REJECT`` is the second, and it is refused rather than
    allowed to raise later: that policy stops at the first token the catalog
    does not contain, and reporting those tokens is what an audit is for. A
    caller who gets a :class:`~acronymkit.exceptions.LexiconError` out of an
    audit has learned only that the corpus has at least one gap, having asked
    how many.

    Args:
        dictionary: The caller's vocabulary, possibly ``None``.
        policy: The resolved policy.

    Returns:
        The vocabulary, unchanged.

    Raises:
        ConfigurationError: If there is no vocabulary, or if the policy rejects
            unknown tokens.
    """
    if dictionary is None:
        raise ConfigurationError(
            "audit_identifiers() requires a governed vocabulary, and dictionary=None is not "
            "one. Pass a GovernedDictionary. Auditing a corpus against a vocabulary that "
            "governs nothing is spelled GovernedDictionary(), and reports every token as "
            "unknown."
        )
    if policy.unknown is UnknownPolicy.REJECT:
        raise ConfigurationError(
            "audit_identifiers() cannot run under UnknownPolicy.REJECT: that policy raises on "
            "the first token the catalog does not contain, and listing those tokens is what "
            "this call is for. Audit under a policy whose unknown handling is "
            "PASSTHROUGH_TITLECASE, and use REJECT in the pipeline afterwards if an unknown "
            "token should stop it."
        )
    return dictionary


def audit_identifiers(
    identifiers: Iterable[Optional[str]],
    dictionary: Optional[GovernedDictionary],
    policy: Optional[NamingPolicy] = None,
    *,
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
    keep_details: bool = True,
    max_examples: int = 3,
) -> CorpusAudit:
    """Audit a whole corpus of physical names against a governed vocabulary.

    One pass, one record per distinct identifier, and four calls per distinct
    identifier at most. The corpus is consumed once, so a generator reading a
    schema export line by line is a supported argument and is the shape to reach
    for on a large one.

    The counts are over the corpus **as supplied**: a name that appears in forty
    tables counts forty times, because the question being asked is how much of a
    schema is affected and not how many distinct strings it contains.
    De-duplication is an implementation detail of the cost, not of the answer,
    and :attr:`CorpusAudit.distinct` reports what it saw.

    Args:
        identifiers: The physical names — a column list, a schema export, an
            information-schema query result. ``None`` and blank entries are
            counted as empty rather than skipped or raised on, so an export with
            holes in it does not stop the audit or quietly shrink the
            denominator.
        dictionary: The governed vocabulary. Required.
        policy: The rules to apply, shared by all four calls. ``None`` means
            :meth:`~acronymkit.governed.policy.NamingPolicy.governed_default`.
            ``UnknownPolicy.REJECT`` is refused; see :func:`_require`.
        custom: A caller-supplied overlay, layered **once** for the whole audit
            rather than once per name.
        keep_details: Whether to retain the per-identifier records. ``True``
            keeps one for every identifier there is something to say about;
            ``False`` keeps none, for a corpus large enough that the tuple would
            be the largest thing in the answer. Every corpus-level count is
            produced either way.
        max_examples: How many example identifiers to retain per unknown token
            and per reason code. Small on purpose: the examples exist to be
            looked at, and the full list of names carrying a common finding is
            most of the corpus.

    Returns:
        The :class:`CorpusAudit`.

    Raises:
        ConfigurationError: If ``dictionary`` is ``None``, if the policy rejects
            unknown tokens, or if ``max_examples`` is negative.

    Example:
        >>> from acronymkit.governed import GovernedDictionary
        >>> from acronymkit.governed.audit import audit_identifiers
        >>> nds = GovernedDictionary.from_long_to_short(
        ...     {"Transaction": "TXN", "Identifier": "ID"},
        ...     approved_abbreviations=["TXN", "ID"],
        ...     class_words={"ID": "Identifier"},
        ... )
        >>> audit = audit_identifiers(["TXN_ID", "TXN_KYC_ID", "TXN_KYC_DT"], nds)
        >>> audit.total, audit.fully_known, audit.partially_known
        (3, 1, 2)
        >>> [(token.token, token.occurrences) for token in audit.unknown_tokens]
        [('KYC', 2), ('DT', 1)]
    """
    active = NamingPolicy.governed_default() if policy is None else policy
    catalog = _require(dictionary, active)
    if max_examples < 0:
        raise ConfigurationError(
            f"audit_identifiers() takes max_examples >= 0, not {max_examples}. Zero retains "
            "no examples and is the way to ask for counts alone."
        )
    if custom:
        catalog = catalog.with_custom(custom)
    trip = _trip_policy(active)

    seen: dict[str, _Observation] = {}
    unknown: dict[str, _Tally] = {}
    findings: dict[ComplianceReasonCode, _Tally] = {}
    breaks: list[RoundTripBreak] = []

    total = empty = fully_known = compliant = 0
    ordinals = stable = corrected = inconsistent = 0

    for raw in identifiers:
        name = raw or ""
        observation = seen.get(name)
        first_seen = observation is None
        if observation is None:
            observation = _observe(name, catalog, active, trip)
            seen[name] = observation
        observation.occurrences += 1

        total += 1
        empty += observation.empty
        fully_known += observation.is_fully_known
        compliant += observation.compliant
        ordinals += observation.ordinals

        for token, count in observation.backlog:
            tally = unknown.get(token)
            if tally is None:
                tally = unknown[token] = _Tally()
            tally.add(count, name, first_seen, max_examples)
        for code, count in observation.codes:
            tally = findings.get(code)
            if tally is None:
                tally = findings[code] = _Tally()
            tally.add(count, name, first_seen, max_examples)

        if observation.round_trip is None:
            stable += 1
        elif observation.round_trip == observation.governed_form:
            corrected += 1
        else:
            inconsistent += 1
            if first_seen:
                breaks.append(
                    RoundTripBreak(
                        identifier=name,
                        phrase=observation.phrase,
                        physical=observation.round_trip,
                        governed_form=observation.governed_form,
                    )
                )

    details: tuple[IdentifierAudit, ...] = ()
    if keep_details:
        details = tuple(
            IdentifierAudit(
                identifier=identifier,
                occurrences=observation.occurrences,
                is_fully_known=observation.is_fully_known,
                compliant=observation.compliant,
                unknown_tokens=observation.unknown,
                codes=tuple(code for code, _ in observation.codes),
                round_trip=observation.round_trip,
                governed_form=(
                    observation.governed_form if observation.round_trip is not None else None
                ),
            )
            for identifier, observation in seen.items()
            if observation.notable
        )

    return CorpusAudit(
        total=total,
        distinct=len(seen),
        empty=empty,
        fully_known=fully_known,
        partially_known=total - fully_known,
        compliant=compliant,
        non_compliant=total - compliant,
        unknown_tokens=tuple(
            UnknownToken(
                token=token,
                occurrences=tally.occurrences,
                identifier_count=tally.identifiers,
                examples=tuple(tally.examples),
                governed_word=_governed_word(catalog, token),
            )
            for token, tally in sorted(
                unknown.items(), key=lambda item: (-item[1].occurrences, item[0])
            )
        ),
        ordinal_occurrences=ordinals,
        findings=tuple(
            FindingTally(
                code=code,
                occurrences=tally.occurrences,
                identifier_count=tally.identifiers,
                examples=tuple(tally.examples),
            )
            for code, tally in sorted(
                findings.items(), key=lambda item: (-item[1].occurrences, item[0].value)
            )
        ),
        round_trip_stable=stable,
        round_trip_corrected=corrected,
        round_trip_inconsistent=inconsistent,
        round_trip_breaks=tuple(breaks),
        details=details,
    )


def suggest_catalog_additions(
    audit: CorpusAudit,
    *,
    limit: Optional[int] = None,
) -> tuple[CatalogSuggestion, ...]:
    """Turn the unknown-token half of an audit into a queue of decisions.

    One suggestion per unknown token, in the audit's own ranking, so the queue
    is already in the order that clears the most columns per row written.

    A suggestion is a **question for whoever owns the catalog**, never an
    answer, and :class:`CatalogSuggestion` says so in every field that could be
    mistaken for one. Most items carry no proposed wording at all, because the
    catalog is silent about the token and this library does not guess; the item
    is still the useful part, since knowing that ``TRNCH`` appears in six
    hundred columns is what gets a row written.

    Where the catalog *does* supply wording — the token is a word it already
    governs — the item is usually not a missing row but a set of column names
    that should be using an existing short form. Those are worth doing first:
    they need no decision from anybody, only an edit.

    Args:
        audit: A completed audit. Only its ranked unknown tokens are read, so
            an audit run with ``keep_details=False`` is a perfectly good
            argument.
        limit: How many suggestions to return, highest-ranked first. ``None``
            returns them all.

    Returns:
        The suggestions, ranked. Empty when the vocabulary covered every
        letter-bearing token in the corpus.

    Raises:
        ConfigurationError: If ``limit`` is negative.

    Example:
        >>> from acronymkit.governed import GovernedDictionary
        >>> from acronymkit.governed.audit import (
        ...     audit_identifiers, suggest_catalog_additions,
        ... )
        >>> nds = GovernedDictionary.from_long_to_short({"Transaction": "TXN"})
        >>> audit = audit_identifiers(["TXN_KYC", "KYC_DT"], nds)
        >>> [(item.token, item.proposed_long_form) for item in suggest_catalog_additions(audit)]
        [('KYC', None), ('DT', None)]
    """
    if limit is not None and limit < 0:
        raise ConfigurationError(
            f"suggest_catalog_additions() takes limit >= 0 or None, not {limit}."
        )
    ranked = audit.unknown_tokens if limit is None else audit.unknown_tokens[:limit]
    return tuple(_suggestion(token) for token in ranked)


def _suggestion(token: UnknownToken) -> CatalogSuggestion:
    """Build one suggestion from one ranked unknown token.

    Args:
        token: The ranked entry, carrying whatever the reverse index knew.

    Returns:
        The suggestion. Its proposal fields are filled only from
        ``token.governed_word``, which is the only route in this module that
        produces wording at all.
    """
    entry = token.governed_word
    basis = (
        None
        if entry is None
        else (
            f"The catalog already carries this word: {entry.entry_id or 'a row with no id'} "
            f"records {entry.canonical!r} with the approved short form {entry.token}. The "
            f"decision is whether these columns should be written {entry.token}, not what "
            f"{token.token} means."
        )
    )
    return CatalogSuggestion(
        token=token.token,
        occurrences=token.occurrences,
        identifier_count=token.identifier_count,
        examples=token.examples,
        proposed_long_form=None if entry is None else entry.canonical,
        proposed_abbreviation=None if entry is None else entry.token,
        entry_id=None if entry is None else entry.entry_id,
        basis=basis,
        is_governed=False,
    )


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------
#: How wide an example identifier may be before it is clipped in the report.
#: Physical names in a real schema run long, and one of them is not worth
#: wrapping the whole table around.
_EXAMPLE_WIDTH = 44


def _clip(text: str, width: int) -> str:
    """Shorten ``text`` to ``width`` characters, marking that it was shortened.

    Args:
        text: The text to fit.
        width: The column width, at least four.

    Returns:
        The text, or its head followed by an ellipsis.
    """
    return text if len(text) <= width else text[: width - 3] + "..."


def _pairs(rows: Sequence[tuple[str, str]]) -> list[str]:
    """Lay out a label-and-value block with the values in one column.

    Args:
        rows: Label and value, in the order to print them.

    Returns:
        One indented line per row.
    """
    width = max(len(label) for label, _ in rows)
    return [f"  {label.ljust(width)}  {value}" for label, value in rows]


def _rows(headers: Sequence[str], rows: Sequence[Sequence[str]], right: Sequence[int]) -> list[str]:
    """Lay out one table as fixed-width text lines.

    Args:
        headers: Column headings.
        rows: The cells, one sequence per row, each the same length as
            ``headers``.
        right: Indices of the columns to right-align — the counts, so they can
            be compared down the column.

    Returns:
        The heading line followed by one line per row, indented.
    """
    widths = [
        max(len(headers[column]), *(len(row[column]) for row in rows))
        if rows
        else len(headers[column])
        for column in range(len(headers))
    ]
    lines = []
    for cells in (headers, *rows):
        rendered = [
            cell.rjust(widths[column]) if column in right else cell.ljust(widths[column])
            for column, cell in enumerate(cells)
        ]
        lines.append("  " + "  ".join(rendered).rstrip())
    return lines


def render_audit(audit: CorpusAudit, *, limit: Optional[int] = 20) -> str:
    """Render an audit as plain text for a person to read.

    The first thing anyone does with an audit is look at it, and a payload of
    counts is not a thing you look at. This is deliberately plain — ASCII, no
    colour, fixed-width columns — so that it survives a log file, a CI pane and
    a Windows console equally, and so that a Java process that captured it can
    paste it into a ticket.

    It is a view, not a summary that leaves something out: every corpus-level
    count in the audit appears somewhere below, and the only things truncated
    are the two ranked tables, which say so when they are.

    Args:
        audit: The audit to render.
        limit: How many rows of each ranked table to show, highest first.
            ``None`` shows every row.

    Returns:
        The report, newline-separated, with no trailing newline.

    Example:
        >>> from acronymkit.governed import GovernedDictionary
        >>> from acronymkit.governed.audit import audit_identifiers, render_audit
        >>> nds = GovernedDictionary.from_long_to_short({"Transaction": "TXN"})
        >>> print(render_audit(audit_identifiers(["TXN_KYC"], nds)).splitlines()[0])
        Governed naming audit
    """
    lines = ["Governed naming audit", "=" * len("Governed naming audit"), ""]

    lines.append("Coverage")
    lines.extend(
        _pairs(
            [
                ("identifiers", f"{audit.total} ({audit.distinct} distinct)"),
                ("fully known", str(audit.fully_known)),
                ("partially known", str(audit.partially_known)),
                ("compliant", str(audit.compliant)),
                ("not compliant", str(audit.non_compliant)),
                ("empty", str(audit.empty)),
            ]
        )
    )
    lines.append("")

    lines.append("Round trip")
    lines.extend(
        _pairs(
            [
                ("unchanged", str(audit.round_trip_stable)),
                ("governed correction", str(audit.round_trip_corrected)),
                ("inconsistent", str(audit.round_trip_inconsistent)),
            ]
        )
    )
    lines.append("")

    lines.extend(_unknown_section(audit, limit))
    lines.append("")
    lines.extend(_findings_section(audit, limit))
    lines.append("")
    lines.extend(_breaks_section(audit, limit))
    return "\n".join(lines)


def _unknown_section(audit: CorpusAudit, limit: Optional[int]) -> list[str]:
    """Render the ranked unknown-token table.

    Args:
        audit: The audit.
        limit: Row cap, or ``None``.

    Returns:
        The section's lines.
    """
    shown = audit.unknown_tokens if limit is None else audit.unknown_tokens[:limit]
    header = "Unknown tokens -- the catalog backlog"
    total = sum(token.occurrences for token in audit.unknown_tokens)
    lines = [
        header,
        f"  {audit.unknown_token_count} distinct, {total} occurrences"
        + (
            f"; {audit.ordinal_occurrences} letterless occurrences set aside"
            if audit.ordinal_occurrences
            else ""
        ),
    ]
    if not shown:
        lines.append("  none: the vocabulary covered every token in the corpus")
        return lines

    # The "governed" column is only printed when some row has something to put
    # in it. A column of blanks reads as a column that failed to fill rather
    # than as one that had nothing to say, and most backlogs have nothing.
    governed = any(token.governed_word is not None for token in shown)
    headers = (
        ("occ", "ids", "token", "governed", "example")
        if governed
        else (
            "occ",
            "ids",
            "token",
            "example",
        )
    )
    lines.extend(
        _rows(
            headers,
            [
                (
                    str(token.occurrences),
                    str(token.identifier_count),
                    token.token,
                    *(
                        (token.governed_word.token if token.governed_word is not None else "",)
                        if governed
                        else ()
                    ),
                    _clip(token.examples[0] if token.examples else "", _EXAMPLE_WIDTH),
                )
                for token in shown
            ],
            right=(0, 1),
        )
    )
    lines.extend(_more(len(audit.unknown_tokens) - len(shown), "token"))
    return lines


def _findings_section(audit: CorpusAudit, limit: Optional[int]) -> list[str]:
    """Render the compliance findings table.

    Args:
        audit: The audit.
        limit: Row cap, or ``None``.

    Returns:
        The section's lines.
    """
    shown = audit.findings if limit is None else audit.findings[:limit]
    lines = ["Compliance findings by reason code"]
    if not shown:
        lines.append("  none: every identifier in the corpus is compliant")
        return lines
    lines.extend(
        _rows(
            ("occ", "ids", "code", "example"),
            [
                (
                    str(finding.occurrences),
                    str(finding.identifier_count),
                    finding.code.value,
                    _clip(finding.examples[0] if finding.examples else "", _EXAMPLE_WIDTH),
                )
                for finding in shown
            ],
            right=(0, 1),
        )
    )
    lines.extend(_more(len(audit.findings) - len(shown), "code"))
    return lines


def _breaks_section(audit: CorpusAudit, limit: Optional[int]) -> list[str]:
    """Render the round-trip inconsistencies.

    Args:
        audit: The audit.
        limit: Row cap, or ``None``.

    Returns:
        The section's lines.
    """
    shown = audit.round_trip_breaks if limit is None else audit.round_trip_breaks[:limit]
    lines = ["Round-trip inconsistencies"]
    if not shown:
        lines.append("  none over the names in this corpus")
        return lines
    for item in shown:
        lines.append(f"  {_clip(item.identifier, _EXAMPLE_WIDTH)}")
        lines.append(f"    came back as {_clip(item.physical, _EXAMPLE_WIDTH)}")
        lines.append(f"    governed form {_clip(item.governed_form, _EXAMPLE_WIDTH)}")
    lines.extend(_more(len(audit.round_trip_breaks) - len(shown), "identifier"))
    return lines


def _more(hidden: int, noun: str) -> list[str]:
    """Say how many rows a table left out, when it left any out.

    Args:
        hidden: How many rows were not shown.
        noun: What the rows are, singular.

    Returns:
        One line, or none at all.
    """
    if hidden <= 0:
        return []
    return [f"  ... and {hidden} further {noun}{'' if hidden == 1 else 's'}"]
