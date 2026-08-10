"""Data-transfer objects returned by the governed subsystem.

Every model here is a frozen Pydantic v2 model that forbids unknown fields, and
:meth:`_FrozenModel.to_dict` renders one to a plain JSON-compatible ``dict`` with
enums as their string values — the same house style as
:mod:`acronymkit.models`.

Two things differ from that module on purpose.

**Sequence fields are tuples, not lists.** ``acronymkit.models`` documents at
length that ``frozen=True`` blocks attribute rebinding but does not deep-freeze
a ``list`` field, so its results are read-only by convention and are not
hashable. These models have no list fields at all. Every sequence is a
``tuple``, which buys three properties that matter more here than they do for a
generation result:

* an audit record cannot be edited in place after it is handed out;
* two entries built from one source list cannot alias each other's candidate
  set, so layering an overlay can never mutate the dictionary underneath it;
* the models are genuinely hashable, so a resolved expansion can be used as a
  cache key or put in a set — which is what a batch job over a million column
  names ends up wanting.

**The base class is local rather than imported.** Reusing
``acronymkit.models._Frozen`` would be less code and would drag the entire
generation DTO layer — thirteen models and their Pydantic core schemas — into
any process that only wanted to expand ``TXN_ID``. The package ``__init__``
treats that schema-building cost as the thing worth deferring, and importing it
sideways from here would quietly undo that. The duplication is a handful of
lines and it is the cheaper of the two mistakes.

Style contract, as elsewhere in the package: PEP 585 builtin generics
(``tuple[str, ...]``) but ``typing.Optional`` rather than PEP 604 ``X | None``,
so the package stays importable on Python 3.9.

Worked examples use the fictional **Northwind Data Standards** (``NDS``)
catalog with synthetic ids; nothing here reflects a real organisation's naming
standard.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import ComplianceReasonCode, EntryKind, ExpansionSource, Verdict

__all__ = [
    "ComplianceReason",
    "ComplianceResult",
    "GovernedEntry",
    "IdentifierExpansion",
    "PhysicalName",
    "PhysicalToken",
    "TokenExpansion",
]


class _FrozenModel(BaseModel):
    """Shared configuration: frozen, strict about extras, JSON-ready."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
        validate_assignment=False,
        ser_json_inf_nan="constants",
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a plain JSON-compatible ``dict`` (enums rendered as strings)."""
        return self.model_dump(mode="json")

    def to_json(self, *, indent: Optional[int] = None) -> str:
        """Serialise to a JSON string.

        Args:
            indent: Passed through to :func:`json.dumps`; ``None`` yields the
                compact representation preferred for wire transfer.
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class GovernedEntry(_FrozenModel):
    """One record in a governed vocabulary: a token and what it officially means.

    An entry answers three questions at once, and keeping them apart is what
    makes the audit trail worth carrying:

    * what the governed long form *is* — :attr:`canonical`;
    * what it was chosen *over* — :attr:`candidates` and :attr:`pin`;
    * how far the catalog stands behind it — :attr:`confidence`,
      :attr:`entry_id` and :attr:`kind`.

    Example:
        >>> from acronymkit.governed import EntryKind, ExpansionSource, GovernedEntry
        >>> entry = GovernedEntry(
        ...     token="TXN",
        ...     canonical="Transaction",
        ...     candidates=("Transaction", "Transmission"),
        ...     pin="Transaction",
        ...     kind=EntryKind.AMBIGUOUS_PINNED,
        ...     entry_id="NDS-TXN",
        ...     source=ExpansionSource.PINNED,
        ... )
        >>> entry.canonical
        'Transaction'
    """

    token: str = Field(
        description="Upper-cased lookup key. Lookup is case-insensitive, so the index is "
        "built once in one casing rather than folding on every query."
    )
    canonical: str = Field(
        description="The single governed long form. This is the answer; every other field "
        "on the entry exists to explain it."
    )
    candidates: tuple[str, ...] = Field(
        default=(),
        description="Every long form the source catalog carried for this token, in the "
        "source's own order, including the canonical one. Order is load-bearing twice: "
        "ResolutionMode.MOST_COMMON takes the first element, and the audit trail reports "
        "the rest as beaten.",
    )
    pin: Optional[str] = Field(
        default=None,
        description="Which candidate the catalog decided is canonical. None means the "
        "token was never ambiguous — an absent pin reads as 'no collision', never as "
        "'collision left unresolved'.",
    )
    kind: EntryKind = Field(
        description="What kind of record this is, and therefore how it behaves; see EntryKind."
    )
    keep_as_abbrev: bool = Field(
        default=False,
        description="True when this token IS the governed physical form. A catalog that has "
        "settled on a short form still carries it as a token, and a resolver that helpfully "
        "rewrote it would be undoing the standard it exists to enforce. Such a token is "
        "approved on the strength of its own entry, with no allow-list row needed, and it is "
        "what the reverse direction emits for the corresponding word rather than hunting for "
        "something shorter. It must never be 'corrected'.",
    )
    class_word: Optional[str] = Field(
        default=None,
        description="The class word this entry designates, when it designates one. Only the "
        "trailing token of an identifier is read for this, because that is the only position "
        "where a class word means anything.",
    )
    entry_id: Optional[str] = Field(
        default=None,
        description="Provenance handle: which catalog row produced this answer. Fixture ids "
        "in this project take the synthetic form NDS-<TOKEN>. Optional because a dictionary "
        "built from a plain mapping has no rows to point at, and inventing an id would make "
        "the audit trail claim a provenance that does not exist.",
    )
    source: ExpansionSource = Field(
        description="The provenance this entry claims when it wins. The resolver may report a "
        "different member when the route to the entry differs from the entry's own claim — a "
        "collision settled by score reports SCORED whatever the entry says."
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="How far the catalog stands behind this entry. 1.0 is a confirmed record. "
        "Anything lower marks an entry that was derived, inferred at load time, or recorded "
        "against a placeholder rather than a confirmed term — and an unconfirmed entry must "
        "never report 1.0. That rule is the entire value of the field: a consumer filtering on "
        "an exact 1.0 is asking to see only what the standard confirms, and one unconfirmed "
        "row claiming a full score makes that filter worthless for every other row.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Free text the catalog recorded alongside the entry, and where the "
        "resolver explains a demotion (an overlay refused under allow_override=False, say). "
        "Not machine-read: anything a program must branch on belongs in a field of its own.",
    )

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.token} = {self.canonical}"


class TokenExpansion(_FrozenModel):
    """One token's governed expansion, with where the answer came from.

    This is the unit of the whole subsystem. Everything else is either a
    collection of these or a transformation of one.
    """

    raw: str = Field(
        description="The token exactly as it appeared, before upper-casing or splitting, so "
        "a caller can align the result back onto its own input."
    )
    long: str = Field(
        description="The expansion. Empty string for empty input: the expansion of nothing "
        "is nothing, and returning it rather than raising keeps a batch from stopping on a "
        "blank cell."
    )
    is_known: bool = Field(
        description="Whether the governed vocabulary produced this answer. False only for a "
        "passthrough. This is the field a pipeline filters on, and the reason a miss is "
        "recoverable: an unknown reported as unknown can be routed to whoever owns the "
        "catalog, while an unknown quietly approximated cannot."
    )
    source: ExpansionSource = Field(description="Which resolution rule fired; see ExpansionSource.")
    entry_id: Optional[str] = Field(
        description="The catalog row behind the answer, or None when no row was involved "
        "(a passthrough, or a dictionary built from a plain mapping)."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Carried through from the winning entry. A passthrough carries 0.0, which "
        "is not low confidence in an answer but the absence of one.",
    )
    class_word: Optional[str] = Field(
        default=None,
        description="The class word this token designates, when it designates one.",
    )
    beat: tuple[str, ...] = Field(
        default=(),
        description="The candidate long forms this expansion won against, in the entry's "
        "declared order, winner excluded. Empty when there was nothing to beat. This is the "
        "explainability payoff, and the reason candidates are kept on the entry at all: "
        "'TXN means Transaction' is a claim, while 'TXN means Transaction, and the catalog had "
        "also seen Transmission' is a decision a reviewer can check. It is also the only way "
        "to tell a token that was never ambiguous from one whose ambiguity was resolved — both "
        "yield a single long form, and only one of them was a choice.",
    )
    kind: Optional[EntryKind] = Field(
        default=None,
        description="The kind of entry behind the answer, when there was one.",
    )

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.raw} -> {self.long}"


class IdentifierExpansion(_FrozenModel):
    """A whole identifier expanded token by token.

    Example:
        ``TXN_APPLNT_ID`` becomes the phrase "Transaction Applicant Identifier",
        three :class:`TokenExpansion` records, and the class word read off the
        trailing token.
    """

    identifier: str = Field(description="The identifier exactly as supplied.")
    phrase: str = Field(
        description="The token expansions joined into readable text — the string a data "
        "dictionary shows a person."
    )
    tokens: tuple[TokenExpansion, ...] = Field(
        description="One record per token, in identifier order, each carrying its own "
        "provenance. Empty for an identifier that tokenises to nothing."
    )
    class_word: Optional[str] = Field(
        description="Read from the TRAILING token only, and None when that token designates "
        "none. Position is the whole rule: a class word anywhere but the end is an ordinary "
        "word, so APPLNT_VERIF_DT names a date while DT_APPLNT_VERIF does not."
    )
    is_fully_known: bool = Field(
        description="True when every token is known. The one-bit summary a pipeline gates on: "
        "a partially expanded identifier is a governed answer with guesses mixed in, and that "
        "has to be visible without walking the token list."
    )

    @property
    def unknown_tokens(self) -> tuple[TokenExpansion, ...]:
        """The tokens the vocabulary did not contain, in identifier order.

        The actionable half of :attr:`is_fully_known`: these are the rows to
        send to whoever owns the catalog.
        """
        return tuple(token for token in self.tokens if not token.is_known)

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.identifier} -> {self.phrase}"


class PhysicalToken(_FrozenModel):
    """One logical word and the governed short form it becomes."""

    word: str = Field(description="The logical word, as it appeared in the logical name.")
    abbrev: str = Field(
        description="Its governed short form, or the word upper-cased when the catalog has "
        "none (FRAUD, MODEL). Never clipped to fit: shortening a word the catalog has not "
        "abbreviated would be inventing an abbreviation, which is the one thing this package "
        "will not do."
    )
    source: ExpansionSource = Field(
        description="Which rule produced the short form; PASSTHROUGH when the word was simply "
        "upper-cased."
    )
    entry_id: Optional[str] = Field(
        description="The catalog row behind the short form, or None when there was none."
    )


class PhysicalName(_FrozenModel):
    """A logical name rendered as a governed physical name."""

    logical: str = Field(description="The logical name as supplied.")
    physical: str = Field(description="The governed physical name, in UPPER_SNAKE form.")
    tokens: tuple[PhysicalToken, ...] = Field(
        description="One record per logical word, in order, each carrying its own provenance."
    )
    term_id: Optional[str] = Field(
        default=None,
        description="Glossary id for the whole logical name, when the term index holds one. "
        "Distinct from the per-token entry ids: it says the *name* is a governed term, not "
        "merely that its words are. Fixture ids take the synthetic form TRM-<6 digits>.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="The weakest link across the name. Below 1.0 whenever any part of the "
        "answer rests on an unconfirmed entry or a placeholder term id.",
    )
    truncated: bool = Field(
        default=False,
        description="Always False. Nothing in this package shortens a name, under any policy. "
        "The field exists so the invariant can be read off the payload instead of inferred "
        "from its absence — a consumer auditing output should see the claim stated, and a test "
        "should have something to fail on. It is deliberately not validated to False, because "
        "a field that cannot hold another value is a constant rather than evidence; it is "
        "written by this package, and this package writes it False. See "
        "NamingPolicy.enforce_name_length for why a name that is too long is flagged instead.",
    )

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.logical} -> {self.physical}"


class ComplianceReason(_FrozenModel):
    """One finding from a compliance check: a verdict, a code and an explanation."""

    token: Optional[str] = Field(
        description="The token this finding is about, or None for a whole-name finding "
        "(missing class word, casing, length, empty input)."
    )
    verdict: Verdict = Field(
        description="PASS or FAIL. Passing findings are recorded too, so a review can see why "
        "a name was accepted and not merely that it was."
    )
    code: ComplianceReasonCode = Field(
        description="The stable, machine-readable reason. Filter, count and route on this."
    )
    detail: str = Field(
        description="One sentence for a person. Written for reading, and free to be reworded "
        "between releases — which is exactly why nothing should branch on it."
    )
    fix: Optional[str] = Field(
        default=None,
        description="The concrete thing to write instead, when there is one. None for a "
        "passing finding, and None when the library has nothing better to offer than 'this is "
        "not approved': suggesting a replacement it cannot justify would be guessing, which is "
        "the failure this package exists to avoid.",
    )

    def __str__(self) -> str:  # pragma: no cover - display helper
        subject = self.token if self.token is not None else "<name>"
        return f"{self.verdict.value.upper()} {subject}: {self.code.value}"


class ComplianceResult(_FrozenModel):
    """The verdict on one physical name, with every finding that produced it.

    Never a bare boolean. :attr:`compliant` is the summary, but a name that
    fails is only actionable if the caller can see which token failed and what
    to write instead, and a name that passes is only auditable if the reasons it
    passed are recorded alongside.
    """

    name: str = Field(description="The name that was checked, as supplied.")
    compliant: bool = Field(
        description="True when no finding carries a FAIL verdict. A name with no findings at "
        "all is compliant; an empty name is not, and says so with EMPTY_NAME."
    )
    reasons: tuple[ComplianceReason, ...] = Field(
        description="Every finding, passing ones included, in the order they were produced: "
        "per-token findings first, then whole-name ones."
    )
    ends_in_class_word: bool = Field(
        description="Whether the trailing token is a class word. Reported separately from the "
        "findings because it is the single structural fact most naming standards turn on, and "
        "a caller should not have to scan reason codes to learn it."
    )
    class_word: Optional[str] = Field(
        description="The trailing class word, or None when there is not one."
    )

    @property
    def failures(self) -> tuple[ComplianceReason, ...]:
        """Only the findings that carry a FAIL verdict, in order."""
        return tuple(reason for reason in self.reasons if reason.verdict is Verdict.FAIL)

    def __str__(self) -> str:  # pragma: no cover - display helper
        state = "compliant" if self.compliant else f"{len(self.failures)} failure(s)"
        return f"{self.name}: {state}"
