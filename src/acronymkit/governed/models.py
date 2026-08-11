"""Data-transfer objects returned by the governed subsystem.

Every model here is a frozen :func:`~dataclasses.dataclass` that renders to a
plain JSON-compatible ``dict`` through :meth:`_FrozenModel.to_dict`, with enums
as their string values and every sequence as a JSON array. The emitted shape is
specified, field by field, in ``docs/notes/governed-json-contract.md``; a change
to a key, to key order, or to a value's JSON type is a break in that contract
rather than a refactor.

Three things differ from :mod:`acronymkit.models` on purpose.

**Nothing here imports pydantic.** That module's DTOs are Pydantic v2 models;
these are dataclasses, and the difference is not a preference. ``pydantic`` v2
ships ``pydantic_core``, a compiled Rust extension, and a compiled extension is
what stops this subsystem being embedded in a JVM through GraalPy — the
difference between a consumer needing a Python subprocess and a consumer taking
a Maven dependency. ``docs/notes/pydantic-cost.md`` measured the other half of
the case: the dependency was 84.6 % of this distribution's import cost, almost
all of it a fixed toll paid the first time any model class is built.

What that trades away is stated plainly, because it is a real trade.
Construction-time validation is now written out rather than derived from the
annotations, and it is applied where untrusted data enters and not everywhere:
:class:`GovernedEntry` is loaded from catalog files, CSV exports and caller
overlays, so every one of its fields is checked; the result DTOs below are built
by this package out of values it computed itself, so they normalise their
sequences and keep their range bounds and check nothing else. A caller who hand-
builds a :class:`TokenExpansion` with a non-string ``raw`` is no longer stopped.
The alternative — re-deriving a type check for every field of every record, on a
path that answers tens of thousands of identifiers a second — is paying pydantic's
price without pydantic.

**Sequence fields are tuples, not lists.** ``acronymkit.models`` documents at
length that a frozen model blocks attribute rebinding but does not deep-freeze a
``list`` field, so its results are read-only by convention and are not hashable.
These models have no list fields at all. Every sequence is a ``tuple``, which
buys three properties that matter more here than they do for a generation
result:

* an audit record cannot be edited in place after it is handed out;
* two entries built from one source list cannot alias each other's candidate
  set, so layering an overlay can never mutate the dictionary underneath it;
* the models are genuinely hashable, so a resolved expansion can be used as a
  cache key or put in a set — which is what a batch job over a million column
  names ends up wanting.

**The base class is local rather than imported.** Reusing
``acronymkit.models._Frozen`` would drag the entire generation DTO layer —
thirteen models and their Pydantic core schemas — into any process that only
wanted to expand ``TXN_ID``, and would put a compiled extension back in the
import graph this module exists to keep clear. The duplication is a handful of
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
from copy import deepcopy
from dataclasses import MISSING, dataclass
from enum import Enum
from typing import Any, ClassVar, Mapping, Optional, Sequence, Tuple, Type, TypeVar

from ..exceptions import ConfigurationError
from .enums import ComplianceReasonCode, EntryKind, ExpansionSource, Verdict

__all__ = [
    "ComplianceReason",
    "ComplianceResult",
    "GovernedEntry",
    "GovernedValidationError",
    "IdentifierExpansion",
    "PhysicalName",
    "PhysicalToken",
    "TokenExpansion",
]

_Model = TypeVar("_Model", bound="_FrozenModel")

#: One ``(field, message)`` pair per thing wrong with a constructor's arguments.
_Problems = Tuple[Tuple[str, str], ...]


class GovernedValidationError(ConfigurationError):
    """Raised when a governed DTO is handed a value it cannot hold.

    Derives from :class:`~acronymkit.exceptions.ConfigurationError`, and
    therefore from both :class:`~acronymkit.exceptions.AcronymKitError` and
    :class:`ValueError`. That is a deliberate improvement on what it replaces:
    a bad field value used to surface as ``pydantic.ValidationError``, which is
    a ``ValueError`` but is *not* an ``AcronymKitError``, so it leaked straight
    past the single ``except AcronymKitError`` that :mod:`acronymkit.exceptions`
    promises catches everything this library raises.

    Every problem with a constructor's arguments is reported at once rather than
    the first one, because a hand-authored catalog row is usually wrong in more
    than one way and fixing it one round trip at a time is the slow way to read
    an error message.

    Args:
        model: The class that refused the values, for the message.
        problems: One ``(field, message)`` pair per problem, in field
            declaration order with any unknown fields last.

    Attributes:
        model: As the argument.
        problems: As the argument, as a tuple.
    """

    def __init__(self, model: str, problems: Sequence[Tuple[str, str]]) -> None:
        self.model = model
        self.problems: _Problems = tuple(problems)
        super().__init__(f"{model}: {_describe_problems(self.problems)}")


def _describe_problems(problems: Sequence[Tuple[str, str]]) -> str:
    """Render validation problems as compact ``field: message`` clauses.

    The rendering the loaders wrap in their own message, so that "this catalog
    row is malformed" is followed by which field and why rather than by a
    paragraph.

    Args:
        problems: The pairs, in the order to report them.

    Returns:
        One clause per problem, joined with ``"; "``.
    """
    return "; ".join(f"{field}: {message}" for field, message in problems)


# --------------------------------------------------------------------------
# Field checks
# --------------------------------------------------------------------------
# Deliberately a handful of small functions rather than a declarative layer.
# The messages match what this package emitted while it was built on pydantic,
# because they are what a person reading a broken catalog file sees and several
# of them are quoted in the loaders' own errors.


class _Required:
    """Stand-in for a required field that has to be declared with a default.

    A dataclass cannot declare a field with no default after one that has a
    default, and :class:`GovernedEntry` has exactly that shape: ``kind`` and
    ``source`` are required and both sit after optional fields, because the
    field *order* is the wire contract and reordering them would change every
    payload this subsystem emits. So the two are declared with this sentinel and
    :meth:`GovernedEntry.__post_init__` reports a leftover sentinel as a missing
    field, which is where pydantic used to report it.
    """

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return "<required>"


#: The sentinel itself, typed :class:`~typing.Any` so that a field annotated
#: with its real type may take it as a default without a type checker objecting.
_REQUIRED: Any = _Required()


def _expected_member(enum_cls: Type[Enum]) -> str:
    """Say which values a closed vocabulary accepts.

    Args:
        enum_cls: The enum the field is declared as.

    Returns:
        The message, listing every member value in declaration order.
    """
    values = [repr(member.value) for member in enum_cls]
    if len(values) == 1:
        return f"Input should be {values[0]}"
    return f"Input should be {', '.join(values[:-1])} or {values[-1]}"


def _member(value: Any, enum_cls: Type[Enum], name: str, problems: list[Tuple[str, str]]) -> Any:
    """Resolve a closed-vocabulary field to its enum member.

    A plain string is accepted and matched against member *values*,
    case-sensitively — the same acceptance the subsystem has always had, and
    deliberately narrower than :meth:`acronymkit.enums._StrEnum.coerce`, which
    also takes member names, mixed case and hyphens. Widening it here would make
    the wire contract accept spellings the contract does not list.

    Args:
        value: Whatever the caller supplied.
        enum_cls: The vocabulary.
        name: The field name, for the message.
        problems: Collected problems, appended to in place.

    Returns:
        The member, or ``value`` unchanged when it could not be resolved.
    """
    if isinstance(value, enum_cls):
        return value
    if value is _REQUIRED:
        problems.append((name, "Field required"))
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            pass
    problems.append((name, _expected_member(enum_cls)))
    return value


def _text(value: Any, name: str, problems: list[Tuple[str, str]]) -> Any:
    """Check a required string field.

    Args:
        value: Whatever the caller supplied, or :data:`_REQUIRED` when a loader
            found the key absent.
        name: The field name, for the message.
        problems: Collected problems, appended to in place.

    Returns:
        ``value`` unchanged; this check never rewrites.
    """
    if value is _REQUIRED:
        problems.append((name, "Field required"))
    elif not isinstance(value, str):
        problems.append((name, "Input should be a valid string"))
    return value


def _optional_text(value: Any, name: str, problems: list[Tuple[str, str]]) -> Any:
    """Check a nullable string field.

    Args:
        value: Whatever the caller supplied.
        name: The field name, for the message.
        problems: Collected problems, appended to in place.

    Returns:
        ``value`` unchanged.
    """
    if value is not None and not isinstance(value, str):
        problems.append((name, "Input should be a valid string"))
    return value


def _flag(value: Any, name: str, problems: list[Tuple[str, str]]) -> Any:
    """Check a boolean field, accepting only a real boolean.

    Narrower than what this subsystem accepted while it ran on pydantic, which
    read ``1``, ``"yes"`` and ``"false"`` as booleans, and the narrowing is
    deliberate. JSON and CSV both have a spelling for true, a catalog is
    authored by hand, and a row writing ``"keep_as_abbrev": "false"`` is a row
    somebody got wrong — reading it as ``False`` happens to be right and reading
    ``"no"`` as ``True`` would have been wrong, with nothing to distinguish the
    two cases at the point it matters. A named field and a refusal is the
    outcome that can be fixed.

    Args:
        value: Whatever the caller supplied.
        name: The field name, for the message.
        problems: Collected problems, appended to in place.

    Returns:
        ``value`` unchanged.
    """
    if not isinstance(value, bool):
        problems.append((name, "Input should be a valid boolean"))
    return value


def _items(value: Any, name: str, problems: list[Tuple[str, str]]) -> Any:
    """Normalise a sequence field to a tuple.

    A bare string is refused rather than exploded into characters, which is the
    one mistake this normalisation could otherwise turn into a plausible-looking
    answer: a catalog row writing ``"candidates": "Deposit"`` would become seven
    one-letter candidates and resolve to ``'D'``.

    Args:
        value: Whatever the caller supplied.
        name: The field name, for the message.
        problems: Collected problems, appended to in place.

    Returns:
        The values as a tuple, or ``()`` when the input was not a sequence.
    """
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    problems.append((name, "Input should be a valid tuple"))
    return ()


def _texts(value: Any, name: str, problems: list[Tuple[str, str]]) -> Any:
    """Normalise a sequence of strings, checking every element.

    Args:
        value: Whatever the caller supplied.
        name: The field name, for the message.
        problems: Collected problems, appended to in place.

    Returns:
        The values as a tuple.
    """
    items = _items(value, name, problems)
    for index, item in enumerate(items):
        if not isinstance(item, str):
            problems.append((f"{name}.{index}", "Input should be a valid string"))
    return items


def _unit_interval(value: Any, name: str, problems: list[Tuple[str, str]]) -> Any:
    """Coerce a confidence to ``float`` and hold it inside ``[0.0, 1.0]``.

    The one range bound kept on every model rather than only on the ones that
    read untrusted input. ``confidence`` is the field a consumer filters on to
    see what the standard confirms, so a value outside the interval is not a
    slightly wrong number — it is a filter that silently stops meaning anything.

    Coercing to ``float`` is load-bearing for the wire contract as well as for
    arithmetic: a catalog row writing ``"confidence": 1`` must still serialise
    as ``1.0``, because a port comparing payloads compares JSON types.

    Args:
        value: Whatever the caller supplied.
        name: The field name, for the message.
        problems: Collected problems, appended to in place.

    Returns:
        The value as a ``float``, or unchanged when it is not a number.
    """
    if not isinstance(value, (int, float)):
        problems.append((name, "Input should be a valid number"))
        return value
    number = float(value)
    if number < 0.0:
        problems.append((name, "Input should be greater than or equal to 0"))
    elif number > 1.0:
        problems.append((name, "Input should be less than or equal to 1"))
    return number


def _freeze_sequences(record: Any, *names: str) -> None:
    """Normalise a record's sequence fields to tuples while it is being built.

    Called from ``__post_init__``, which is the only moment a frozen record may
    still be written to. Every sequence a governed model carries is a tuple —
    see the module docstring for the three properties that buys — so a caller
    who hands one a list gets a record that keeps the promise rather than one
    that quietly does not.

    Args:
        record: The record under construction.
        *names: Its sequence fields, in declaration order.

    Raises:
        GovernedValidationError: If any of them holds something that is neither
            a list nor a tuple.
    """
    problems: list[Tuple[str, str]] = []
    for name in names:
        object.__setattr__(record, name, _items(getattr(record, name), name, problems))
    if problems:
        raise GovernedValidationError(type(record).__name__, problems)


def _freeze_confidence(record: Any) -> None:
    """Coerce a record's ``confidence`` to ``float`` and bound it to ``[0, 1]``.

    Args:
        record: The record under construction.

    Raises:
        GovernedValidationError: If the value is not a number, or is outside the
            interval.
    """
    problems: list[Tuple[str, str]] = []
    object.__setattr__(
        record, "confidence", _unit_interval(record.confidence, "confidence", problems)
    )
    if problems:
        raise GovernedValidationError(type(record).__name__, problems)


#: Field values that are already JSON, tested by exact type rather than by
#: ``isinstance``. Most fields on most records are one of these — a string, a
#: flag, a count, a confidence, a ``None`` — and an exact-type set membership is
#: one hash where the ``isinstance`` chain below is three failed calls. Exact
#: rather than ``isinstance`` because the enums here *are* ``str`` subclasses and
#: must not be caught by this test; ``type(EntryKind.APPROVED_ABBREV)`` is
#: ``EntryKind``, so they fall through to the enum branch where they belong.
_JSON_SCALARS = frozenset({str, bool, int, float, type(None)})


def _jsonable(value: Any) -> Any:
    """Render one field value as JSON-compatible data.

    Args:
        value: A field value: a scalar, an enum member, a tuple, or a nested
            model.

    Returns:
        The value with enums replaced by their string values, tuples by lists
        and nested models by their own ``to_dict``.
    """
    if type(value) in _JSON_SCALARS:
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, _FrozenModel):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    return value


class _FrozenModel:
    """Shared behaviour for every governed DTO: JSON rendering and copying.

    Not a dataclass itself. Every subclass is decorated with
    ``@dataclass(frozen=True)`` and this class carries only the methods, so that
    a subclass's own field order — which *is* the emitted key order — is
    whatever it declares, with nothing inherited in front of it.
    """

    #: Declared by ``@dataclass`` on every subclass; annotated here so that the
    #: methods below can read the field order without a type checker objecting.
    #: Annotation only: binding a value would make ``@dataclass`` treat this
    #: class as a dataclass base and fail looking for its parameters.
    __dataclass_fields__: ClassVar[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a plain JSON-compatible ``dict`` (enums rendered as strings).

        Key order is field declaration order, which the wire contract fixes.

        Returns:
            One key per field, in declaration order.
        """
        values = self.__dict__
        return {name: _jsonable(values[name]) for name in self.__dataclass_fields__}

    def to_json(self, *, indent: Optional[int] = None) -> str:
        """Serialise to a JSON string.

        Args:
            indent: Passed through to :func:`json.dumps`; ``None`` yields the
                compact representation preferred for wire transfer. Note that
                ``json.dumps`` defaults are used throughout, so "compact" still
                means ``", "`` and ``": "`` separators — the contract document
                says so, and a port comparing text rather than parsed documents
                has to match it.
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
        """Return the fields as a ``dict``.

        Kept from the Pydantic era because callers and neighbouring modules use
        it. ``mode="json"`` is :meth:`to_dict`; anything else returns the field
        values as they are held, with enums as members and sequences as tuples.

        Args:
            mode: ``"json"`` for the wire rendering, ``"python"`` for the raw
                values.

        Returns:
            One key per field, in declaration order.
        """
        if mode == "json":
            return self.to_dict()
        values = self.__dict__
        return {name: values[name] for name in self.__dataclass_fields__}

    def model_copy(
        self: _Model,
        *,
        update: Optional[Mapping[str, Any]] = None,
        deep: bool = False,
    ) -> _Model:
        """Return a copy with ``update`` applied, without re-validating.

        Kept from the Pydantic era, and kept with its semantics: the values in
        ``update`` are written as given rather than checked, which is what the
        resolver relies on when it rewrites three fields of a catalog row it
        already validated at load time. A caller passing something the
        constructor would have refused gets a record that holds it.

        Args:
            update: Field values to replace, or ``None`` for a plain copy.
            deep: Whether to deep-copy the field values. Every field of every
                model here is immutable, so this can only be observed through
                ``is`` on a nested record; it is accepted so the signature does
                not narrow.

        Returns:
            A new instance. The receiver is unchanged.
        """
        values = dict(self.__dict__)
        if update:
            values.update(update)
        if deep:
            values = deepcopy(values)
        clone = object.__new__(type(self))
        # Written straight into the instance dict rather than field by field:
        # this runs once per resolved token on a batch path, and the frozen
        # ``__setattr__`` would have to be bypassed for every one of them anyway.
        clone.__dict__.update(values)
        return clone


@dataclass(frozen=True)
class GovernedEntry(_FrozenModel):
    """One record in a governed vocabulary: a token and what it officially means.

    An entry answers three questions at once, and keeping them apart is what
    makes the audit trail worth carrying:

    * what the governed long form *is* — :attr:`canonical`;
    * what it was chosen *over* — :attr:`candidates` and :attr:`pin`;
    * how far the catalog stands behind it — :attr:`confidence`,
      :attr:`entry_id` and :attr:`kind`.

    This is the one model in the file that is built from data nobody in this
    package wrote — a catalog JSON file, a CSV export, a caller's overlay — so
    it is the one that checks every field, and it reports every problem it finds
    rather than the first.

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

    Raises:
        GovernedValidationError: If any field is missing or holds a value of the
            wrong shape.
    """

    #: Upper-cased lookup key. Lookup is case-insensitive, so the index is built
    #: once in one casing rather than folding on every query.
    token: str

    #: The single governed long form. This is the answer; every other field on
    #: the entry exists to explain it.
    canonical: str

    #: Every long form the source catalog carried for this token, in the
    #: source's own order, including the canonical one. Order is load-bearing
    #: twice: ResolutionMode.MOST_COMMON takes the first element, and the audit
    #: trail reports the rest as beaten.
    candidates: tuple[str, ...] = ()

    #: Which candidate the catalog decided is canonical. None means the token
    #: was never ambiguous — an absent pin reads as "no collision", never as
    #: "collision left unresolved".
    pin: Optional[str] = None

    #: What kind of record this is, and therefore how it behaves; see EntryKind.
    #: Required, and declared with a sentinel default only because the field
    #: order below it is the wire contract; see :class:`_Required`.
    kind: EntryKind = _REQUIRED

    #: True when this token IS the governed physical form. A catalog that has
    #: settled on a short form still carries it as a token, and a resolver that
    #: helpfully rewrote it would be undoing the standard it exists to enforce.
    #: Such a token is approved on the strength of its own entry, with no
    #: allow-list row needed, and it is what the reverse direction emits for the
    #: corresponding word rather than hunting for something shorter. It must
    #: never be "corrected".
    keep_as_abbrev: bool = False

    #: The class word this entry designates, when it designates one. Only the
    #: trailing token of an identifier is read for this, because that is the
    #: only position where a class word means anything.
    class_word: Optional[str] = None

    #: Provenance handle: which catalog row produced this answer. Fixture ids in
    #: this project take the synthetic form NDS-<TOKEN>. Optional because a
    #: dictionary built from a plain mapping has no rows to point at, and
    #: inventing an id would make the audit trail claim a provenance that does
    #: not exist.
    entry_id: Optional[str] = None

    #: The provenance this entry claims when it wins. The resolver may report a
    #: different member when the route to the entry differs from the entry's own
    #: claim — a collision settled by score reports SCORED whatever the entry
    #: says. Required; see :attr:`kind` for why it carries a sentinel default.
    source: ExpansionSource = _REQUIRED

    #: How far the catalog stands behind this entry. 1.0 is a confirmed record.
    #: Anything lower marks an entry that was derived, inferred at load time, or
    #: recorded against a placeholder rather than a confirmed term — and an
    #: unconfirmed entry must never report 1.0. That rule is the entire value of
    #: the field: a consumer filtering on an exact 1.0 is asking to see only what
    #: the standard confirms, and one unconfirmed row claiming a full score makes
    #: that filter worthless for every other row.
    confidence: float = 1.0

    #: Free text the catalog recorded alongside the entry, and where the resolver
    #: explains a demotion (an overlay refused under allow_override=False, say).
    #: Not machine-read: anything a program must branch on belongs in a field of
    #: its own.
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        """Check and normalise every field, reporting all problems at once.

        Raises:
            GovernedValidationError: If anything is missing or malformed.
        """
        problems: list[Tuple[str, str]] = []
        _text(self.token, "token", problems)
        _text(self.canonical, "canonical", problems)
        set_field = object.__setattr__
        set_field(self, "candidates", _texts(self.candidates, "candidates", problems))
        _optional_text(self.pin, "pin", problems)
        set_field(self, "kind", _member(self.kind, EntryKind, "kind", problems))
        _flag(self.keep_as_abbrev, "keep_as_abbrev", problems)
        _optional_text(self.class_word, "class_word", problems)
        _optional_text(self.entry_id, "entry_id", problems)
        set_field(self, "source", _member(self.source, ExpansionSource, "source", problems))
        set_field(self, "confidence", _unit_interval(self.confidence, "confidence", problems))
        _optional_text(self.notes, "notes", problems)
        if problems:
            raise GovernedValidationError("GovernedEntry", problems)

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.token} = {self.canonical}"


#: Every field a catalog row may carry, in declaration order.
_ENTRY_FIELDS: tuple[str, ...] = tuple(GovernedEntry.__dataclass_fields__)

#: The four it must carry. Derived rather than listed, so that adding a required
#: field to the model cannot leave a loader accepting rows without it.
_ENTRY_REQUIRED: tuple[str, ...] = tuple(
    name
    for name, field in GovernedEntry.__dataclass_fields__.items()
    if field.default is MISSING or field.default is _REQUIRED
)


def _entry_from_mapping(values: Mapping[str, Any]) -> GovernedEntry:
    """Build a :class:`GovernedEntry` from a mapping nobody in this package wrote.

    The route every loader takes: a parsed JSON row, a CSV record, a caller's
    overlay. It differs from calling the constructor in the two ways an
    untrusted mapping needs.

    **A key the model does not have is refused by name.** The constructor would
    raise ``TypeError`` naming the function, which tells a person editing a
    catalog file nothing about which of the row's eleven keys is wrong.

    **A required key that is absent is reported as a field rather than as an
    arity error**, and reported alongside every other problem in the row, in
    field order with the unknown keys last. A hand-authored row is usually wrong
    in more than one way.

    Args:
        values: The row, with any metadata keys already dropped by the caller —
            this function does not know the ``_``-prefix convention.

    Returns:
        The entry.

    Raises:
        GovernedValidationError: If the row is missing a required field, carries
            a field the model does not have, or holds a malformed value.
    """
    unknown = [
        (name, "Extra inputs are not permitted") for name in values if name not in _ENTRY_FIELDS
    ]
    supplied = {name: value for name, value in values.items() if name in _ENTRY_FIELDS}
    for name in _ENTRY_REQUIRED:
        supplied.setdefault(name, _REQUIRED)
    try:
        entry = GovernedEntry(**supplied)
    except GovernedValidationError as exc:
        raise GovernedValidationError("GovernedEntry", (*exc.problems, *unknown)) from None
    if unknown:
        raise GovernedValidationError("GovernedEntry", unknown)
    return entry


@dataclass(frozen=True)
class TokenExpansion(_FrozenModel):
    """One token's governed expansion, with where the answer came from.

    This is the unit of the whole subsystem. Everything else is either a
    collection of these or a transformation of one.
    """

    #: The token exactly as it appeared, before upper-casing or splitting, so a
    #: caller can align the result back onto its own input.
    raw: str

    #: The expansion. Empty string for empty input: the expansion of nothing is
    #: nothing, and returning it rather than raising keeps a batch from stopping
    #: on a blank cell.
    long: str

    #: Whether the governed vocabulary produced this answer. False only for a
    #: passthrough. This is the field a pipeline filters on, and the reason a
    #: miss is recoverable: an unknown reported as unknown can be routed to
    #: whoever owns the catalog, while an unknown quietly approximated cannot.
    is_known: bool

    #: Which resolution rule fired; see ExpansionSource.
    source: ExpansionSource

    #: The catalog row behind the answer, or None when no row was involved (a
    #: passthrough, or a dictionary built from a plain mapping). Required and
    #: nullable: the caller must decide, and the decision may be "there was none".
    entry_id: Optional[str]

    #: Carried through from the winning entry. A passthrough carries 0.0, which
    #: is not low confidence in an answer but the absence of one.
    confidence: float

    #: The class word this token designates, when it designates one.
    class_word: Optional[str] = None

    #: The candidate long forms this expansion won against, in the entry's
    #: declared order, winner excluded. Empty when there was nothing to beat.
    #: This is the explainability payoff, and the reason candidates are kept on
    #: the entry at all: "TXN means Transaction" is a claim, while "TXN means
    #: Transaction, and the catalog had also seen Transmission" is a decision a
    #: reviewer can check. It is also the only way to tell a token that was never
    #: ambiguous from one whose ambiguity was resolved — both yield a single long
    #: form, and only one of them was a choice.
    beat: tuple[str, ...] = ()

    #: The kind of entry behind the answer, when there was one.
    kind: Optional[EntryKind] = None

    def __post_init__(self) -> None:
        """Normalise the beaten-candidate tuple and bound the confidence.

        Raises:
            GovernedValidationError: If ``beat`` is not a sequence, or
                ``confidence`` is outside ``[0, 1]``.
        """
        _freeze_sequences(self, "beat")
        _freeze_confidence(self)

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.raw} -> {self.long}"


@dataclass(frozen=True)
class IdentifierExpansion(_FrozenModel):
    """A whole identifier expanded token by token.

    The record accounts for the whole input, not only the part of it that
    became words. Every character of ``identifier`` is either inside one of the
    ``tokens``, or one of the separators
    :mod:`~acronymkit.governed.tokenizer` names, or listed in
    :attr:`unaccounted` — and :attr:`is_fully_known` is ``True`` only when the
    catalog answered for every token *and* there was nothing in the third
    bucket. A caller that reads those two fields has seen everything that
    happened to the name it passed in.

    Example:
        ``TXN_APPLNT_ID`` becomes the phrase "Transaction Applicant Identifier",
        three :class:`TokenExpansion` records, and the class word read off the
        trailing token.
    """

    #: The identifier exactly as supplied.
    identifier: str

    #: The token expansions joined into readable text — the string a data
    #: dictionary shows a person.
    phrase: str

    #: One record per token, in identifier order, each carrying its own
    #: provenance. Empty for an identifier that tokenises to nothing.
    tokens: tuple[TokenExpansion, ...]

    #: Read from the TRAILING token only, and None when that token designates
    #: none. Position is the whole rule: a class word anywhere but the end is an
    #: ordinary word, so APPLNT_VERIF_DT names a date while DT_APPLNT_VERIF does
    #: not.
    class_word: Optional[str]

    #: True when every token is known AND nothing in the identifier went
    #: unaccounted for. The one-bit summary a pipeline gates on, and it
    #: summarises the whole answer or it is worth nothing: a partially expanded
    #: identifier is a governed answer with guesses mixed in, and an identifier
    #: holding a character the splitter could not read is a governed answer to a
    #: question that was not quite the one asked. Both have to be visible without
    #: walking the token list.
    is_fully_known: bool

    #: Characters of the identifier that ended up in no token and are not one of
    #: the separators the splitter accounts for: an emoji pasted out of a
    #: spreadsheet, a currency sign, a combining accent left by a decomposed
    #: Unicode spelling, a control character from a bad export. One entry per
    #: occurrence, in input order. Empty for essentially every name a schema
    #: actually contains, and the reason the field exists is the case where it is
    #: not - answering "Transaction Identifier, fully known" for a column whose
    #: name also held a character that was quietly discarded is a confident
    #: description of a name nobody wrote. Separate from unknown_tokens because
    #: the two are different work: an unknown token is a catalog row somebody
    #: owes, and an unaccounted character is a question about the name itself
    #: that no catalog row can settle. Written by expand_identifier; the
    #: compliance and reverse directions do not carry it, and such a character
    #: reaches is_compliant as a NOT_UPPER_SNAKE finding or as nothing at all.
    unaccounted: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Normalise the two sequence fields to tuples.

        Raises:
            GovernedValidationError: If either is not a sequence.
        """
        _freeze_sequences(self, "tokens", "unaccounted")

    @property
    def unknown_tokens(self) -> tuple[TokenExpansion, ...]:
        """The tokens the vocabulary did not contain, in identifier order.

        The actionable half of :attr:`is_fully_known`: these are the rows to
        send to whoever owns the catalog.
        """
        return tuple(token for token in self.tokens if not token.is_known)

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.identifier} -> {self.phrase}"


@dataclass(frozen=True)
class PhysicalToken(_FrozenModel):
    """One logical word and the governed short form it becomes."""

    #: The logical word, as it appeared in the logical name.
    word: str

    #: Its governed short form, or the word upper-cased when the catalog has
    #: none (FRAUD, MODEL). Never clipped to fit: shortening a word the catalog
    #: has not abbreviated would be inventing an abbreviation, which is the one
    #: thing this package will not do.
    abbrev: str

    #: Which rule produced the short form; PASSTHROUGH when the word was simply
    #: upper-cased.
    source: ExpansionSource

    #: The catalog row behind the short form, or None when there was none.
    entry_id: Optional[str]


@dataclass(frozen=True)
class PhysicalName(_FrozenModel):
    """A logical name rendered as a governed physical name."""

    #: The logical name as supplied.
    logical: str

    #: The governed physical name, in UPPER_SNAKE form.
    physical: str

    #: One record per logical word, in order, each carrying its own provenance.
    tokens: tuple[PhysicalToken, ...]

    #: Glossary id for the whole logical name, when the term index holds one.
    #: Distinct from the per-token entry ids: it says the *name* is a governed
    #: term, not merely that its words are. Fixture ids take the synthetic form
    #: TRM-<6 digits>.
    term_id: Optional[str] = None

    #: The weakest link across the name. Below 1.0 whenever any part of the
    #: answer rests on an unconfirmed entry or a placeholder term id.
    confidence: float = 1.0

    #: Always False. Nothing in this package shortens a name, under any policy.
    #: The field exists so the invariant can be read off the payload instead of
    #: inferred from its absence — a consumer auditing output should see the
    #: claim stated, and a test should have something to fail on. It is
    #: deliberately not validated to False, because a field that cannot hold
    #: another value is a constant rather than evidence; it is written by this
    #: package, and this package writes it False. See
    #: NamingPolicy.enforce_name_length for why a name that is too long is
    #: flagged instead.
    truncated: bool = False

    def __post_init__(self) -> None:
        """Normalise the token tuple and bound the confidence.

        Raises:
            GovernedValidationError: If ``tokens`` is not a sequence, or
                ``confidence`` is outside ``[0, 1]``.
        """
        _freeze_sequences(self, "tokens")
        _freeze_confidence(self)

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.logical} -> {self.physical}"


@dataclass(frozen=True)
class ComplianceReason(_FrozenModel):
    """One finding from a compliance check: a verdict, a code and an explanation."""

    #: The token this finding is about, or None for a whole-name finding
    #: (missing class word, casing, length, empty input).
    token: Optional[str]

    #: PASS or FAIL. Passing findings are recorded too, so a review can see why
    #: a name was accepted and not merely that it was.
    verdict: Verdict

    #: The stable, machine-readable reason. Filter, count and route on this.
    code: ComplianceReasonCode

    #: One sentence for a person. Written for reading, and free to be reworded
    #: between releases — which is exactly why nothing should branch on it.
    detail: str

    #: The concrete thing to write instead, when there is one. None for a
    #: passing finding, and None when the library has nothing better to offer
    #: than "this is not approved": suggesting a replacement it cannot justify
    #: would be guessing, which is the failure this package exists to avoid.
    fix: Optional[str] = None

    def __str__(self) -> str:  # pragma: no cover - display helper
        subject = self.token if self.token is not None else "<name>"
        return f"{self.verdict.value.upper()} {subject}: {self.code.value}"


@dataclass(frozen=True)
class ComplianceResult(_FrozenModel):
    """The verdict on one physical name, with every finding that produced it.

    Never a bare boolean. :attr:`compliant` is the summary, but a name that
    fails is only actionable if the caller can see which token failed and what
    to write instead, and a name that passes is only auditable if the reasons it
    passed are recorded alongside.
    """

    #: The name that was checked, as supplied.
    name: str

    #: True when no finding carries a FAIL verdict. A name with no findings at
    #: all is compliant; an empty name is not, and says so with EMPTY_NAME.
    compliant: bool

    #: Every finding, passing ones included, in the order they were produced:
    #: per-token findings first, then whole-name ones.
    reasons: tuple[ComplianceReason, ...]

    #: Whether the trailing token is a class word. Reported separately from the
    #: findings because it is the single structural fact most naming standards
    #: turn on, and a caller should not have to scan reason codes to learn it.
    ends_in_class_word: bool

    #: The trailing class word, or None when there is not one.
    class_word: Optional[str]

    def __post_init__(self) -> None:
        """Normalise the findings to a tuple.

        Raises:
            GovernedValidationError: If ``reasons`` is not a sequence.
        """
        _freeze_sequences(self, "reasons")

    @property
    def failures(self) -> tuple[ComplianceReason, ...]:
        """Only the findings that carry a FAIL verdict, in order."""
        return tuple(reason for reason in self.reasons if reason.verdict is Verdict.FAIL)

    def __str__(self) -> str:  # pragma: no cover - display helper
        state = "compliant" if self.compliant else f"{len(self.failures)} failure(s)"
        return f"{self.name}: {state}"
