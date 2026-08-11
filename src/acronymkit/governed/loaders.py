"""File front ends for a governed vocabulary: CSV exports and bundle directories.

:class:`~acronymkit.governed.dictionary.GovernedDictionary` already knows how to
be built from a mapping, from an inverted long-to-short mapping and from JSON.
What it does not do is read a file that a person exported from a spreadsheet,
and that is the shape a real catalog arrives in. A data-governance function
keeps its standard in a workbook: one sheet of long form and preferred
abbreviation, one sheet of tokens that may stand in a physical name, one sheet
of class words, a pin sheet for the collisions somebody has ruled on, and a term
glossary. Nobody hands out a JSON array of ``GovernedEntry`` rows.

So the cost of trying this library used to be a script: open five files, decide
what each one means, invert one of them, merge the results and only then call a
constructor. That script is the same script for every caller, it is easy to get
subtly wrong, and every copy of it is a place where somebody's catalog is
misread. It lives here instead.

Four functions, and one of them matters more than the others
------------------------------------------------------------
:func:`load_long_to_short_csv` is the important one, because long → short is the
direction a governed catalog is authored and stored in, and inverting it is what
makes the collisions visible that
:func:`~acronymkit.governed.scoring.canonical_form_score` exists to settle. The
semantics of that inversion are
:meth:`~acronymkit.governed.dictionary.GovernedDictionary.from_long_to_short`'s
and are documented there; this module is only the file-reading front end for it.

:func:`load_csv` is the short → long direction, for a catalog already stored
that way. :func:`load_term_index_csv` reads a glossary. :func:`load_bundle`
reads a whole standard — catalog, allow-lists, class words, pin sheet, glossary —
out of one directory or one JSON object and returns a vocabulary that is ready
to use.

What these loaders refuse to guess
----------------------------------
The column names are keyword arguments with **no defaults**. There is no
conventional header for "the long form" — a real export says ``Long Name``, or
``Business Term``, or ``Data Element Name`` — and picking one would be this
package guessing about the caller's file, which is the one thing it does not do.
The bundle is the exception, and only because a bundle is a layout *this module
defines*: its file names and its glossary columns are a convention, they are
written down below, and both can be overridden.

Encoding is explicit at every read. The default is ``utf-8-sig``, which is
plain UTF-8 plus a tolerance for the byte-order mark Excel writes; nothing here
consults the locale, so a container running with ``LANG=C`` reads the same bytes
the same way as a developer laptop does.

Duplicate keys are resolved by one rule, everywhere: **the last row wins**, which
is what a Python mapping does with a repeated key and what
:class:`~acronymkit.governed.dictionary.GovernedDictionary` already documents for
two catalog rows carrying the same token. It is stated on each function because a
silent overwrite that nobody wrote down is a bug waiting to be blamed on the
library.

Worked examples use the fictional **Northwind Data Standards** catalog (``NDS``),
synthetic entry ids and generic industry tokens. Nothing here describes a real
organisation's standard.
"""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Optional, Union

from ..exceptions import LexiconError
from .dictionary import DERIVED_ENTRY_CONFIDENCE, GovernedDictionary
from .enums import EntryKind, ExpansionSource
from .models import GovernedEntry
from .scoring import rank_candidates

__all__ = [
    "BUNDLE_FILES",
    "load_bundle",
    "load_csv",
    "load_long_to_short_csv",
    "load_term_index_csv",
]

#: Anything :func:`os.fspath` accepts. Text is a path, never file content — the
#: same rule :meth:`GovernedDictionary.from_json` states for its own argument.
_PathLike = Union[str, "os.PathLike[str]"]

#: The encoding every read here defaults to. UTF-8 with the byte-order mark
#: tolerated rather than treated as data, because a spreadsheet export written
#: on Windows usually carries one and a leading ``﻿`` welded onto the first
#: header name is the single most common reason a column "does not exist".
DEFAULT_ENCODING = "utf-8-sig"

#: Bundle section -> the file stems :func:`load_bundle` accepts for it, and the
#: suffixes it will read. The first stem of each row is the name the fixture
#: corpus uses; the others are there because a standard exported by somebody
#: else will not have read this docstring. Two files matching one section is an
#: error rather than a coin toss.
BUNDLE_FILES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("catalog", ("dictionary", "catalog", "entries"), (".json",)),
    ("allow_lists", ("allowlist", "allowlists", "allow_lists"), (".json",)),
    ("class_words", ("class_words", "classwords"), (".json",)),
    ("pins", ("ambiguity_pins", "pins"), (".json",)),
    ("terms", ("term_glossary", "terms", "glossary"), (".csv", ".json")),
)

#: Bundle section -> the keys :func:`load_bundle` accepts for it in the
#: single-object form. Consulted in order, first hit wins.
_BUNDLE_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("catalog", ("catalog", "dictionary", "entries")),
    ("allow_lists", ("allowlist", "allowlists", "allow_lists")),
    ("class_words", ("class_words", "classwords")),
    ("pins", ("ambiguity_pins", "pins")),
    ("terms", ("term_index", "term_glossary", "terms", "glossary")),
)

#: The three allow-list keys, in the order the standard consults them.
_ALLOW_LIST_KEYS = ("approved_abbreviations", "common_keywords", "short_full_words")

#: Default glossary columns for :func:`load_bundle`. Overridable, and named here
#: rather than inside the function so a caller can read the convention.
DEFAULT_TERM_COLUMNS = ("logical_name", "term_id")

_PIN_CONTRIBUTED_NOTE = (
    "The pin on this row came from the bundle's pin sheet rather than from the catalog row."
)

_CANDIDATES_CONTRIBUTED_NOTE = "The candidate set on this row came from the bundle's pin sheet."

_MINTED_NOTE = (
    "Minted from the bundle's pin sheet: the sheet records a collision for this token and the "
    "catalog carries no row for it. The entry has no entry_id, because there is no catalog row "
    "to point at."
)

_MINTED_SCORED_NOTE = (
    "The sheet records no decision, so canonical_form_score chose {winner!r} over {beaten}. "
    "Recording a pin replaces this rule of thumb with a decision."
)


def _phrase_key(text: Optional[str]) -> str:
    """Return the comparison key for a long form.

    A local copy of the dictionary module's own rule — casefolded, whitespace
    collapsed — rather than an import of its private helper. Two spellings of
    one comparison is a real cost; reaching across a module boundary for a
    name with a leading underscore is a larger one.

    Args:
        text: A long form, or ``None``.

    Returns:
        The key, or ``""`` when there is nothing to key on.
    """
    return " ".join(text.split()).casefold() if text else ""


def _joined_notes(existing: Optional[str], addition: str) -> str:
    """Append a loader note to whatever the catalog row already recorded.

    Args:
        existing: The row's own ``notes``, if it had any.
        addition: The note this loader wants to add.

    Returns:
        Both, space-joined, or the addition alone.
    """
    return f"{existing} {addition}" if existing else addition


def _header_index(source: Path, header: Sequence[str], column: str) -> int:
    """Locate one requested column in a CSV header row.

    Header names are compared with surrounding whitespace stripped, because a
    spreadsheet export routinely writes ``"Long Name "``, and a caller who has
    to guess how many spaces their own header carries has been given a puzzle
    rather than a loader. Nothing else is normalised: case and punctuation are
    the caller's, and matching them loosely would let a file resolve to a column
    the caller did not name.

    Args:
        source: The file, named in any error raised.
        header: The header row exactly as read.
        column: The column name the caller asked for.

    Returns:
        The zero-based position of the column.

    Raises:
        LexiconError: If the column is absent — the message lists the headers
            actually found, because "no such column" without them is not
            actionable — or if two columns carry the name, which makes the
            choice between them undecidable.
    """
    names = [name.strip() for name in header]
    wanted = column.strip()
    found = [index for index, name in enumerate(names) if name == wanted]
    if not found:
        listed = ", ".join(repr(name) for name in names) or "(no columns)"
        raise LexiconError(
            f"{source!s} has no column {column!r}. Its header row is: {listed}. "
            "Pass the column name this file actually uses."
        )
    if len(found) > 1:
        raise LexiconError(
            f"{source!s} carries the column name {column!r} more than once, so which one holds "
            "the data cannot be decided. Rename or remove the duplicates."
        )
    return found[0]


def _read_pairs(
    path: _PathLike,
    key_column: str,
    value_column: str,
    *,
    encoding: str,
    delimiter: str,
) -> list[tuple[str, str]]:
    """Read two named columns out of a CSV, in file order.

    The shared reader behind every CSV loader here. It handles what a real
    export contains: a byte-order mark (through the ``utf-8-sig`` default), CRLF
    line endings and embedded newlines (the file is opened with ``newline=""``,
    which is what :mod:`csv` requires to keep both correct), quoted fields
    holding the delimiter, blank rows, and rows shorter than the header.

    Rows are skipped, never guessed at, in three cases: a row with nothing in
    it, a row whose key cell is blank, and a row whose value cell is blank. A
    half-filled row is a gap in the catalog, and turning it into an entry would
    mean claiming to know something the file did not say.

    Args:
        path: The CSV file.
        key_column: Header name of the column read as the mapping key.
        value_column: Header name of the column read as the mapping value.
        encoding: The codec to decode with. Explicit, never the locale's.
        delimiter: The field separator.

    Returns:
        ``(key, value)`` pairs, whitespace-stripped, in the order the file
        listed them. Order is load-bearing: it becomes candidate order in
        :meth:`GovernedDictionary.from_long_to_short`, and
        ``NamingPolicy.frequency_baseline()`` reads position zero.

    Raises:
        LexiconError: If the file is missing, unreadable, not decodable with
            ``encoding``, empty, malformed as CSV, or missing a requested
            column.
    """
    source = Path(os.fspath(path))
    pairs: list[tuple[str, str]] = []
    try:
        with source.open(encoding=encoding, newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            header = next(reader, None)
            if header is None:
                raise LexiconError(
                    f"{source!s} is empty. A governed CSV needs a header row naming "
                    f"{key_column!r} and {value_column!r}."
                )
            key_at = _header_index(source, header, key_column)
            value_at = _header_index(source, header, value_column)
            for row in reader:
                if not any(cell.strip() for cell in row):
                    continue
                key = row[key_at].strip() if key_at < len(row) else ""
                value = row[value_at].strip() if value_at < len(row) else ""
                if not key or not value:
                    continue
                pairs.append((key, value))
    except UnicodeDecodeError as exc:
        raise LexiconError(
            f"{source!s} is not decodable as {encoding}: {exc}. Pass encoding= naming the codec "
            "the export actually used."
        ) from exc
    except OSError as exc:
        raise LexiconError(f"{source!s} could not be read: {exc}") from exc
    except csv.Error as exc:
        raise LexiconError(f"{source!s} is not readable as CSV: {exc}") from exc
    return pairs


def load_csv(
    path: _PathLike,
    *,
    token_column: str,
    canonical_column: str,
    encoding: str = DEFAULT_ENCODING,
    delimiter: str = ",",
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
    approved_abbreviations: Iterable[str] = (),
    common_keywords: Iterable[str] = (),
    short_full_words: Iterable[str] = (),
    class_words: Optional[Mapping[str, str]] = None,
    term_index: Optional[Mapping[str, str]] = None,
) -> GovernedDictionary:
    """Load a short → long catalog from a two-column CSV.

    The direction a catalog is stored in when somebody has already inverted it:
    one row per token, naming what that token expands to. Every row is
    unambiguous by construction, so nothing here is ever settled by score — the
    semantics are
    :meth:`~acronymkit.governed.dictionary.GovernedDictionary.from_mapping`'s,
    including the absence of an ``entry_id`` on every row, because a CSV cell is
    not a catalog row identifier and minting one would make the audit trail
    claim a provenance that does not exist.

    **A repeated token is resolved last-wins and silently**, exactly as a
    mapping resolves a repeated key. That is the honest limit of this direction:
    two rows saying ``ID,Identifier`` and ``ID,Identity`` are a collision the
    file has flattened, and a short → long file has nowhere to record that it
    happened. If the catalog you hold has collisions in it, store it long →
    short and use :func:`load_long_to_short_csv`, which keeps both forms as
    candidates and says which one it chose.

    Args:
        path: The CSV file.
        token_column: Header name of the short-form column. Required, and
            deliberately without a default: there is no conventional name for
            it and guessing at the caller's file is the one thing this package
            does not do.
        canonical_column: Header name of the long-form column. Required, for
            the same reason.
        encoding: The codec to decode with. Defaults to UTF-8 with a tolerated
            byte-order mark; never the locale's.
        delimiter: The field separator, for a tab- or semicolon-separated
            export.
        custom: As :meth:`GovernedDictionary.__init__`.
        approved_abbreviations: As :meth:`GovernedDictionary.__init__`.
        common_keywords: As :meth:`GovernedDictionary.__init__`.
        short_full_words: As :meth:`GovernedDictionary.__init__`.
        class_words: As :meth:`GovernedDictionary.__init__`.
        term_index: As :meth:`GovernedDictionary.__init__`.

    Returns:
        The indexed vocabulary.

    Raises:
        LexiconError: If the file cannot be read, cannot be decoded with
            ``encoding``, is empty, is not valid CSV, or lacks a requested
            column. The message names the headers that were found.
    """
    mapping: dict[str, str] = {}
    for token, canonical in _read_pairs(
        path, token_column, canonical_column, encoding=encoding, delimiter=delimiter
    ):
        mapping[token] = canonical
    return GovernedDictionary.from_mapping(
        mapping,
        custom=custom,
        approved_abbreviations=approved_abbreviations,
        common_keywords=common_keywords,
        short_full_words=short_full_words,
        class_words=class_words,
        term_index=term_index,
    )


def load_long_to_short_csv(
    path: _PathLike,
    *,
    long_column: str,
    short_column: str,
    encoding: str = DEFAULT_ENCODING,
    delimiter: str = ",",
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
    approved_abbreviations: Iterable[str] = (),
    common_keywords: Iterable[str] = (),
    short_full_words: Iterable[str] = (),
    class_words: Optional[Mapping[str, str]] = None,
    term_index: Optional[Mapping[str, str]] = None,
) -> GovernedDictionary:
    """Load a long → short catalog from a CSV and invert it.

    This is the loader a real standard needs. A governed catalog is authored in
    one direction — *Transaction* is abbreviated ``TXN``, *Identifier* is ``ID``
    — and stored that way, one answer per row, with nobody who wrote it having
    had to think about ambiguity. Expansion reads it backwards, and the inverse
    is not a mapping: *Identifier*, *Identification*, *Identity* and, in any
    catalog that also has address columns, *Idaho* all shorten to ``ID``.
    Inverting is what makes that visible, and
    :meth:`~acronymkit.governed.dictionary.GovernedDictionary.from_long_to_short`
    is where the visible collisions are settled and recorded. This function is
    its file-reading front end and adds no semantics of its own.

    Two order facts are worth relying on. Candidate order for a colliding token
    is the order the file listed its long forms, so
    ``NamingPolicy.frequency_baseline()``, which reads position zero, sees what
    the file put first; and a long form repeated on two rows with **different**
    tokens is resolved last-wins, because that is what the mapping the inversion
    consumes can hold. The many-to-one direction that matters — several long
    forms to one token — is kept whole, which is the entire point of reading the
    file this way round.

    Args:
        path: The CSV file.
        long_column: Header name of the long-form column, such as
            ``"Long Name"``. Required and without a default: guessing it would
            be guessing about the caller's file.
        short_column: Header name of the abbreviation column, such as
            ``"Preferred Abbreviation"``. Required, for the same reason.
        encoding: The codec to decode with. Defaults to UTF-8 with a tolerated
            byte-order mark; never the locale's.
        delimiter: The field separator.
        custom: As :meth:`GovernedDictionary.__init__`.
        approved_abbreviations: As :meth:`GovernedDictionary.__init__`.
        common_keywords: As :meth:`GovernedDictionary.__init__`.
        short_full_words: As :meth:`GovernedDictionary.__init__`.
        class_words: As :meth:`GovernedDictionary.__init__`.
        term_index: As :meth:`GovernedDictionary.__init__`.

    Returns:
        The indexed vocabulary, with every collision the file contained resolved
        by :func:`~acronymkit.governed.scoring.canonical_form_score` and
        recorded — ``source`` ``scored``, confidence below full, and a note
        naming what was chosen over what.

    Raises:
        LexiconError: If the file cannot be read, cannot be decoded with
            ``encoding``, is empty, is not valid CSV, or lacks a requested
            column.
    """
    mapping: dict[str, str] = {}
    for long_form, token in _read_pairs(
        path, long_column, short_column, encoding=encoding, delimiter=delimiter
    ):
        mapping[long_form] = token
    return GovernedDictionary.from_long_to_short(
        mapping,
        custom=custom,
        approved_abbreviations=approved_abbreviations,
        common_keywords=common_keywords,
        short_full_words=short_full_words,
        class_words=class_words,
        term_index=term_index,
    )


def load_term_index_csv(
    path: _PathLike,
    *,
    name_column: str,
    term_id_column: str,
    encoding: str = DEFAULT_ENCODING,
    delimiter: str = ",",
) -> dict[str, str]:
    """Read a term glossary into the ``{logical name: term id}`` mapping.

    A glossary export carries more columns than this — a physical name, a
    domain, a confidentiality class — and every one of them is ignored. The
    dictionary's ``term_index`` answers one question, whether a whole logical
    name is a governed term, and a loader that quietly imported the other
    columns would be inventing a second contract for them.

    Args:
        path: The CSV file.
        name_column: Header name of the logical-name column.
        term_id_column: Header name of the term-id column.
        encoding: The codec to decode with.
        delimiter: The field separator.

    Returns:
        Logical name to term id, in file order. A logical name repeated is
        last-wins.

    Raises:
        LexiconError: As :func:`load_csv`.
    """
    index: dict[str, str] = {}
    for name, term_id in _read_pairs(
        path, name_column, term_id_column, encoding=encoding, delimiter=delimiter
    ):
        index[name] = term_id
    return index


def _read_json(path: Path) -> Any:
    """Parse one JSON file of a bundle.

    Args:
        path: The file.

    Returns:
        The parsed document.

    Raises:
        LexiconError: If the file cannot be read, is not valid UTF-8, or is not
            valid JSON. Bundle files are UTF-8 by definition of the format;
            a bundle whose files are not is not a bundle this loader reads.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise LexiconError(f"Bundle file {path!s} is not valid UTF-8: {exc}") from exc
    except OSError as exc:
        raise LexiconError(f"Bundle file {path!s} could not be read: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LexiconError(f"Bundle file {path!s} is not valid JSON: {exc}") from exc


def _public_items(document: Mapping[str, Any]) -> Iterable[tuple[str, Any]]:
    """Yield a document's entries with the metadata keys dropped.

    A leading underscore marks a key written for a person rather than for a
    loader — ``_meta``, ``_notes`` — and the fixture corpus documents that
    convention for itself. Honouring it is what lets a governed file carry an
    explanation of itself next to its data.

    Args:
        document: A parsed JSON object.

    Yields:
        ``(key, value)`` for every key not beginning with an underscore.
    """
    for key, value in document.items():
        if not str(key).startswith("_"):
            yield str(key), value


def _string_list(document: Mapping[str, Any], key: str, origin: str) -> tuple[str, ...]:
    """Read one allow-list array out of the allow-list document.

    Args:
        document: The parsed allow-list object.
        key: Which list to read.
        origin: What to name in an error — a file path, or the bundle object.

    Returns:
        The tokens, or an empty tuple when the document does not carry that
        list. An absent allow-list is not an error: a standard may approve
        tokens through catalog rows alone.

    Raises:
        LexiconError: If the value is not an array of strings.
    """
    values = document.get(key)
    if values is None:
        return ()
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise LexiconError(
            f"{origin}: {key!r} must be an array of tokens, got {type(values).__name__}."
        )
    for value in values:
        if not isinstance(value, str):
            raise LexiconError(
                f"{origin}: {key!r} must hold only tokens, got a {type(value).__name__}."
            )
    return tuple(values)


def _class_word_map(document: Any, origin: str) -> dict[str, str]:
    """Read the class-word map out of the class-word document.

    Two shapes are accepted and mean the same thing. A file that describes
    itself keeps the map under ``"abbreviations"`` alongside whatever else it
    records — the spelled-out forms, a trailing-token policy — and a document
    that is nothing but the map is taken as the map. The first shape is what the
    fixture corpus writes; the second is what a caller assembles by hand.

    Args:
        document: The parsed class-word object.
        origin: What to name in an error.

    Returns:
        Abbreviation to spelled-out form.

    Raises:
        LexiconError: If the document is not an object, or if a value under the
            map is not a string — which is what happens when a file keeps extra
            sections beside the map without putting the map under
            ``"abbreviations"``, and the message names the key that failed.
    """
    if not isinstance(document, Mapping):
        raise LexiconError(
            f"{origin}: the class-word map must be a JSON object, got {type(document).__name__}."
        )
    nested = document.get("abbreviations")
    source: Mapping[str, Any] = nested if isinstance(nested, Mapping) else document
    mapped: dict[str, str] = {}
    for key, value in _public_items(source):
        if not isinstance(value, str):
            raise LexiconError(
                f"{origin}: class word {key!r} must map to its spelled-out form as a string, got "
                f"{type(value).__name__}. A file that keeps other sections beside the map should "
                'put the map under "abbreviations".'
            )
        mapped[key] = value
    return mapped


def _term_index_map(document: Any, origin: str) -> dict[str, str]:
    """Read a glossary supplied as JSON rather than as CSV.

    Args:
        document: The parsed glossary object, ``{logical name: term id}``.
        origin: What to name in an error.

    Returns:
        Logical name to term id.

    Raises:
        LexiconError: If the document is not an object of strings.
    """
    if not isinstance(document, Mapping):
        raise LexiconError(
            f"{origin}: the term glossary must be a JSON object mapping a logical name to a term "
            f"id, got {type(document).__name__}."
        )
    index: dict[str, str] = {}
    for name, term_id in _public_items(document):
        if not isinstance(term_id, str):
            raise LexiconError(
                f"{origin}: term id for {name!r} must be a string, got {type(term_id).__name__}."
            )
        index[name] = term_id
    return index


def _pin_sheet(document: Any, origin: str) -> dict[str, tuple[tuple[str, ...], Optional[str]]]:
    """Read the pin sheet into ``token -> (candidates, pin)``.

    The pin key is accepted spelled either ``"pin"`` or ``"_pin"``. The fixture
    corpus writes the underscored form deliberately, so that a loader which
    drops metadata keys without thinking produces an *unpinned* collision rather
    than a wrong pin; this loader reads it on purpose and says so here, because
    a convention that only one file knows about is a trap.

    A null pin is a decision not to decide. It is preserved as ``None``, and
    :func:`_apply_pins` never lets it erase a pin the catalog carries.

    Args:
        document: The parsed pin sheet.
        origin: What to name in an error.

    Returns:
        Token to its candidate set and its pin.

    Raises:
        LexiconError: If the sheet is not an object, if a record is not an
            object, or if the candidates are not an array of strings.
    """
    if not isinstance(document, Mapping):
        raise LexiconError(
            f"{origin}: the pin sheet must be a JSON object keyed by token, got "
            f"{type(document).__name__}."
        )
    sheet: dict[str, tuple[tuple[str, ...], Optional[str]]] = {}
    for token, record in _public_items(document):
        if not isinstance(record, Mapping):
            raise LexiconError(
                f"{origin}: pin sheet record for {token!r} must be a JSON object carrying "
                f'"candidates" and a pin, got {type(record).__name__}.'
            )
        raw = record.get("candidates", ())
        if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
            raise LexiconError(
                f"{origin}: pin sheet candidates for {token!r} must be an array of long forms, "
                f"got {type(raw).__name__}."
            )
        for candidate in raw:
            if not isinstance(candidate, str):
                raise LexiconError(
                    f"{origin}: pin sheet candidates for {token!r} must hold only long forms, "
                    f"got a {type(candidate).__name__}."
                )
        pin = record["pin"] if "pin" in record else record.get("_pin")
        if pin is not None and not isinstance(pin, str):
            raise LexiconError(
                f"{origin}: pin for {token!r} must be a long form or null, got "
                f"{type(pin).__name__}."
            )
        sheet[token.strip().upper()] = (tuple(raw), pin)
    return sheet


def _minted_entry(token: str, candidates: tuple[str, ...], pin: Optional[str]) -> GovernedEntry:
    """Build the row for a pin-sheet token the catalog has no entry for.

    A decision recorded about a token the catalog never gave a row to is still a
    decision, and dropping it would make the pin sheet's effect depend on
    whether somebody remembered to add the row. So the sheet's record becomes an
    entry — with **no** ``entry_id``, because there is no catalog row to point
    at and minting an identifier would make the audit trail claim a provenance
    that does not exist.

    Args:
        token: The upper-cased token.
        candidates: The sheet's candidate set.
        pin: The sheet's decision, or ``None`` when it recorded none.

    Returns:
        The entry. A pinned record reports ``PINNED`` at full confidence; an
        unpinned one is settled by
        :func:`~acronymkit.governed.scoring.rank_candidates` and reports
        ``SCORED`` at :data:`~acronymkit.governed.dictionary.DERIVED_ENTRY_CONFIDENCE`,
        the same way an inverted long-to-short catalog records a collision it
        settled itself.
    """
    if pin:
        return GovernedEntry(
            token=token,
            canonical=pin,
            candidates=candidates,
            pin=pin,
            kind=EntryKind.AMBIGUOUS_PINNED,
            source=ExpansionSource.PINNED,
            notes=_MINTED_NOTE,
        )
    ranked = rank_candidates(candidates, token)
    # A record with neither a pin nor a candidate is filtered out before it
    # reaches here, so `ranked` is empty only in a shape that cannot occur. The
    # fallback is the token standing as its own expansion, which is what an
    # allow-list entry does and is the one answer that invents nothing.
    winner = ranked[0] if ranked else token
    beaten = ", ".join(repr(form) for form in candidates if form != winner) or "nothing"
    return GovernedEntry(
        token=token,
        canonical=winner,
        candidates=candidates,
        kind=EntryKind.AMBIGUOUS_PINNED,
        source=ExpansionSource.SCORED,
        confidence=DERIVED_ENTRY_CONFIDENCE,
        notes=_joined_notes(_MINTED_NOTE, _MINTED_SCORED_NOTE.format(winner=winner, beaten=beaten)),
    )


def _apply_pins(
    rows: Sequence[GovernedEntry],
    sheet: Mapping[str, tuple[tuple[str, ...], Optional[str]]],
    origin: str,
) -> list[GovernedEntry]:
    """Merge the pin sheet into the catalog rows.

    The sheet fills gaps and is not allowed to overwrite. Where a catalog row
    already carries a pin, or already carries candidates, the row stands; where
    it carries neither, the sheet supplies them and the merged row records in
    ``notes`` that it did, so a reviewer can tell a decision the catalog stated
    from one that arrived beside it.

    **A genuine disagreement raises rather than resolving.** Two files pinning
    one token to two different long forms is a governance question, not a
    loading question, and picking one silently would be this package overruling
    a decision somebody signed off — with no way for anyone downstream to know
    it happened. The message names the token and both long forms.

    Args:
        rows: The catalog rows, already parsed and validated.
        sheet: The pin sheet, as :func:`_pin_sheet` returns it.
        origin: What to name in an error.

    Returns:
        The merged rows: every catalog row, plus one minted row for each
        pin-sheet token the catalog had none for and that carries something to
        say.

    Raises:
        LexiconError: If a token's pin or candidate set differs between the two
            files.
    """
    merged: list[GovernedEntry] = []
    seen: set[str] = set()
    for row in rows:
        token = row.token
        seen.add(token)
        record = sheet.get(token)
        if record is None:
            merged.append(row)
            continue
        candidates, pin = record
        if row.pin and pin and _phrase_key(row.pin) != _phrase_key(pin):
            raise LexiconError(
                f"{origin}: the catalog pins {token!r} to {row.pin!r} and the pin sheet pins it "
                f"to {pin!r}. Two files recording different decisions for one token is a "
                "governance disagreement, and this loader will not choose between them."
            )
        if row.candidates and candidates and set(row.candidates) != set(candidates):
            raise LexiconError(
                f"{origin}: the catalog and the pin sheet carry different candidate sets for "
                f"{token!r}: {list(row.candidates)} against {list(candidates)}. Reconcile the "
                "files; a merge here would decide which collision is real."
            )
        update: dict[str, Any] = {}
        notes = row.notes
        if pin and not row.pin:
            update["pin"] = pin
            update["source"] = ExpansionSource.PINNED
            notes = _joined_notes(notes, _PIN_CONTRIBUTED_NOTE)
        if candidates and not row.candidates:
            update["candidates"] = candidates
            notes = _joined_notes(notes, _CANDIDATES_CONTRIBUTED_NOTE)
        if not update:
            merged.append(row)
            continue
        update["notes"] = notes
        merged.append(row.model_copy(update=update))

    for token, (candidates, pin) in sheet.items():
        if token in seen or not (candidates or pin):
            continue
        merged.append(_minted_entry(token, candidates, pin))
    return merged


def _bundle_documents(path: Path) -> tuple[dict[str, Any], dict[str, Path], str]:
    """Resolve a bundle path into its per-section documents.

    Two layouts, one assembly. A **directory** is scanned for the file names in
    :data:`BUNDLE_FILES`; a **file** is parsed as one JSON object whose keys name
    the sections. Both produce the same five optional documents, so everything
    downstream is written once.

    Args:
        path: The directory or file.

    Returns:
        The per-section documents, the per-section source files (empty for the
        single-object form, and used only to read a glossary CSV), and a string
        naming the bundle for error messages.

    Raises:
        LexiconError: If the path does not exist, if two files in a directory
            claim one section, if the single-file form is not a JSON object, or
            if no section is recognised at all — an empty result would build an
            empty vocabulary that silently passes every token through, which is
            the failure this package is least willing to produce quietly.
    """
    if path.is_dir():
        origin = f"Bundle directory {path!s}"
        documents: dict[str, Any] = {}
        files: dict[str, Path] = {}
        for section, stems, suffixes in BUNDLE_FILES:
            found = [
                candidate
                for stem in stems
                for suffix in suffixes
                if (candidate := path / f"{stem}{suffix}").is_file()
            ]
            if len(found) > 1:
                listed = ", ".join(sorted(item.name for item in found))
                raise LexiconError(
                    f"{origin}: {listed} all claim the {section!r} section. Keep one and remove "
                    "the others; choosing between them would be a coin toss."
                )
            if found:
                files[section] = found[0]
                if found[0].suffix != ".csv":
                    documents[section] = _read_json(found[0])
        if not files:
            wanted = ", ".join(f"{stems[0]}{suffixes[0]}" for _, stems, suffixes in BUNDLE_FILES)
            present = ", ".join(sorted(item.name for item in path.iterdir())) or "(nothing)"
            raise LexiconError(
                f"{origin} holds no file this loader recognises. It looks for {wanted} (with the "
                f"aliases listed in acronymkit.governed.loaders.BUNDLE_FILES) and found: "
                f"{present}."
            )
        return documents, files, origin

    if not path.exists():
        raise LexiconError(
            f"Bundle {path!s} does not exist. Pass a directory holding the standard's files, or "
            "one JSON object holding its sections."
        )

    origin = f"Bundle file {path!s}"
    document = _read_json(path)
    if not isinstance(document, Mapping):
        raise LexiconError(
            f"{origin}: the single-file form must be a JSON object whose keys name the bundle's "
            f"sections, got {type(document).__name__}."
        )
    documents = {}
    for section, keys in _BUNDLE_KEYS:
        for key in keys:
            if key in document:
                # "entries" is both a bundle key and the key the catalog object
                # form uses for its rows, and from_json reads either shape, so
                # the whole document is handed over when the rows sit at the top
                # level rather than under a section of their own.
                documents[section] = document if key == "entries" else document[key]
                break
    if any(key in document for key in _ALLOW_LIST_KEYS):
        documents.setdefault("allow_lists", document)
    if not documents:
        listed = ", ".join(sorted(str(key) for key, _ in _public_items(document))) or "(nothing)"
        raise LexiconError(
            f"{origin} holds no section this loader recognises. It looks for the keys in "
            f"acronymkit.governed.loaders.BUNDLE_FILES and found: {listed}."
        )
    return documents, {}, origin


def load_bundle(
    path: _PathLike,
    *,
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
    term_columns: tuple[str, str] = DEFAULT_TERM_COLUMNS,
    encoding: str = DEFAULT_ENCODING,
) -> GovernedDictionary:
    """Assemble a whole governed standard from a directory or a single object.

    A standard is not one file. It is a catalog, three allow-lists saying which
    tokens may stand in a physical name, a class-word map, a pin sheet recording
    the collisions somebody has ruled on, and a term glossary — five files that
    every caller was previously merging by hand, identically, in a script of
    their own. This reads all five and returns the vocabulary ready to use.

    Layouts
    -------
    **A directory.** File names are looked up from :data:`BUNDLE_FILES`; the
    fixture corpus under ``tests/fixtures/governed/`` is exactly this shape, so
    ``load_bundle("tests/fixtures/governed")`` is a complete worked catalog. Two
    files claiming one section is an error rather than a coin toss. Every
    section is optional, and a directory in which nothing is recognised raises
    rather than returning an empty vocabulary that would pass every token
    through in silence.

    **One JSON object.** The same sections, as keys, for a caller who ships
    their standard as a single document. Both the section-shaped value
    (``"class_words": {"abbreviations": {...}}``) and the plain one
    (``"class_words": {"DT": "Date"}``) are read.

    How the pin sheet is merged
    ---------------------------
    The sheet fills gaps and never overwrites: it supplies a pin or a candidate
    set only where the catalog row has none, and the merged row records in
    ``notes`` that it did. A token in the sheet with no catalog row becomes a
    row with no ``entry_id``. A token the two files pin **differently** raises,
    because choosing between two recorded decisions is not a loading question.

    What is deliberately not read
    -----------------------------
    A caller overlay is not part of a bundle even when a file beside it holds
    one. An overlay is the caller's, not the standard's, and a loader that
    quietly applied one would return a vocabulary that disagrees with the
    catalog with nothing at the call site to say so. Pass it as ``custom=``, or
    layer it afterwards with
    :meth:`~acronymkit.governed.dictionary.GovernedDictionary.with_custom`.

    Args:
        path: A directory holding the standard's files, or one JSON object.
        custom: A caller-supplied overlay, layered onto the assembled
            vocabulary. As :meth:`GovernedDictionary.__init__`.
        term_columns: The glossary CSV's ``(logical name, term id)`` column
            names. These have a default where the CSV loaders do not, because
            the bundle layout is a convention this module defines rather than a
            guess about a file it has never seen.
        encoding: The codec to decode a glossary CSV with. Bundle JSON files are
            UTF-8 by definition of the format.

    Returns:
        The indexed vocabulary.

    Raises:
        LexiconError: If the path does not exist; if a file cannot be read,
            decoded or parsed; if a section holds the wrong shape; if two files
            claim one section; if nothing is recognised; or if the catalog and
            the pin sheet record different decisions for one token.

    Example:
        >>> from acronymkit.governed.loaders import load_bundle
        >>> nds = load_bundle("tests/fixtures/governed")   # doctest: +SKIP
        >>> nds.lookup("TXN").canonical                    # doctest: +SKIP
        'Transaction'
    """
    source = Path(os.fspath(path))
    documents, files, origin = _bundle_documents(source)

    catalog = documents.get("catalog")
    rows: Sequence[GovernedEntry] = ()
    if catalog is not None:
        # from_json parses and validates the rows with the same messages a
        # direct JSON load would give, including the row position of a bad row.
        # The indexes it builds are thrown away; the merged rows are indexed
        # once more below, which costs one dictionary build per bundle load.
        rows = GovernedDictionary.from_json(catalog).entries

    sheet = _pin_sheet(documents["pins"], origin) if "pins" in documents else {}
    merged = _apply_pins(rows, sheet, origin) if sheet else list(rows)

    allow_lists = documents.get("allow_lists")
    if allow_lists is not None and not isinstance(allow_lists, Mapping):
        raise LexiconError(
            f"{origin}: the allow-list section must be a JSON object carrying "
            f"{', '.join(repr(key) for key in _ALLOW_LIST_KEYS)}, got "
            f"{type(allow_lists).__name__}."
        )
    lists: Mapping[str, Any] = allow_lists if allow_lists is not None else {}

    class_words: dict[str, str] = {}
    if "class_words" in documents:
        class_words = _class_word_map(documents["class_words"], origin)

    terms_file = files.get("terms")
    if terms_file is not None and terms_file.suffix == ".csv":
        term_index = load_term_index_csv(
            terms_file,
            name_column=term_columns[0],
            term_id_column=term_columns[1],
            encoding=encoding,
        )
    elif "terms" in documents:
        term_index = _term_index_map(documents["terms"], origin)
    else:
        term_index = {}

    return GovernedDictionary(
        merged,
        custom=custom,
        approved_abbreviations=_string_list(lists, "approved_abbreviations", origin),
        common_keywords=_string_list(lists, "common_keywords", origin),
        short_full_words=_string_list(lists, "short_full_words", origin),
        class_words=class_words,
        term_index=term_index,
    )
