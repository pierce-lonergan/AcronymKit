"""Acceptance gate for :mod:`acronymkit.governed.loaders`.

These loaders exist so that a caller with a catalog in a spreadsheet does not
have to write a script to get it in, so the tests are written against the
material a caller actually has: files with a byte-order mark, CRLF endings,
quoted fields carrying commas, blank rows, and headers that are not the ones the
call asked for.

The load-bearing test is
``::test_the_bundle_reproduces_the_hand_merged_vocabulary_exactly``. The suite in
``tests/test_governed.py`` assembles the fixture corpus by hand — read five
files, pick the right key out of three of them, build a term index out of a CSV,
then call a constructor with five keyword arguments — and that hand-merge is the
friction :func:`~acronymkit.governed.loaders.load_bundle` removes. Asserting that
the one-line call produces an *equal* vocabulary is what makes the removal safe:
if the loader ever drifts from what a careful caller would have written, this
fails, and no example in this file is trusted to notice it instead.

The fixture catalog is the fictional **Northwind Data Standards** (``NDS``).
Nothing in this file or the files it reads describes a real organisation's
naming standard.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from acronymkit.exceptions import LexiconError
from acronymkit.governed import ExpansionSource, GovernedDictionary
from acronymkit.governed.loaders import (
    BUNDLE_FILES,
    load_bundle,
    load_csv,
    load_long_to_short_csv,
    load_term_index_csv,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "governed"


# --------------------------------------------------------------------------
# The hand-merge these loaders replace
# --------------------------------------------------------------------------
def _hand_merged() -> GovernedDictionary:
    """Assemble the fixture corpus the way a caller had to before ``load_bundle``.

    Deliberately a copy of what ``tests/test_governed.py`` does at module level
    rather than an import of it. The point of the comparison is that this is the
    code every integration was writing for itself, so it belongs here in full,
    where its length is visible.

    Returns:
        The vocabulary, assembled from four files by hand.
    """
    allow_list = json.loads((FIXTURES / "allowlist.json").read_text(encoding="utf-8"))
    class_words = json.loads((FIXTURES / "class_words.json").read_text(encoding="utf-8"))
    with (FIXTURES / "term_glossary.csv").open(encoding="utf-8", newline="") as handle:
        term_index = {row["logical_name"]: row["term_id"] for row in csv.DictReader(handle)}
    return GovernedDictionary.from_json(
        FIXTURES / "dictionary.json",
        approved_abbreviations=allow_list["approved_abbreviations"],
        common_keywords=allow_list["common_keywords"],
        short_full_words=allow_list["short_full_words"],
        class_words=class_words["abbreviations"],
        term_index=term_index,
    )


def _bundle_object() -> dict[str, Any]:
    """Fold the fixture directory into one JSON object, the second bundle layout.

    Returns:
        The single-object form of the same bundle.
    """
    allow_list = json.loads((FIXTURES / "allowlist.json").read_text(encoding="utf-8"))
    with (FIXTURES / "term_glossary.csv").open(encoding="utf-8", newline="") as handle:
        term_index = {row["logical_name"]: row["term_id"] for row in csv.DictReader(handle)}
    return {
        "catalog": json.loads((FIXTURES / "dictionary.json").read_text(encoding="utf-8")),
        "allowlist": {key: allow_list[key] for key in allow_list if not key.startswith("_")},
        "class_words": json.loads((FIXTURES / "class_words.json").read_text(encoding="utf-8")),
        "pins": json.loads((FIXTURES / "ambiguity_pins.json").read_text(encoding="utf-8")),
        "term_index": term_index,
    }


def _write_csv(path: Path, text: str, *, encoding: str = "utf-8") -> Path:
    """Write a CSV byte-for-byte, so line endings and the BOM are the test's choice.

    ``Path.write_text`` would translate newlines through the platform's rules,
    which is exactly the variable under test. Bytes are written instead.

    Args:
        path: Where to write.
        text: The file content, with its line endings already as intended.
        encoding: The codec to encode with.

    Returns:
        ``path``, for chaining.
    """
    path.write_bytes(text.encode(encoding))
    return path


# --------------------------------------------------------------------------
# load_bundle: the whole standard in one call
# --------------------------------------------------------------------------
def test_the_bundle_reproduces_the_hand_merged_vocabulary_exactly() -> None:
    """One call must equal the five-file merge it replaces, field for field.

    This is the claim the module makes and the only one worth gating: not that
    ``load_bundle`` returns *a* vocabulary, but that it returns *the same*
    vocabulary a careful caller would have built. Catalog rows, all three
    allow-lists, the class-word map and the glossary are compared separately,
    because a loader that dropped one of them would still pass a test that only
    looked at the entries.
    """
    hand = _hand_merged()
    loaded = load_bundle(FIXTURES)

    assert loaded.entries == hand.entries
    assert loaded.approved_abbreviations == hand.approved_abbreviations
    assert loaded.common_keywords == hand.common_keywords
    assert loaded.short_full_words == hand.short_full_words
    assert loaded.class_words == hand.class_words
    assert loaded.term_id_for("Customer Account Open Date") == hand.term_id_for(
        "Customer Account Open Date"
    )


def test_the_bundle_directory_and_the_bundle_object_agree(tmp_path: Path) -> None:
    """The two layouts are one format, so they must produce one vocabulary.

    A standard shipped as a directory of files and the same standard shipped as
    a single JSON document are the same standard. If the two front ends could
    disagree, the format would have two meanings and neither would be the
    format.
    """
    single = tmp_path / "bundle.json"
    single.write_text(json.dumps(_bundle_object()), encoding="utf-8")

    from_directory = load_bundle(FIXTURES)
    from_object = load_bundle(single)

    assert from_object.entries == from_directory.entries
    assert from_object.approved_abbreviations == from_directory.approved_abbreviations
    assert from_object.class_words == from_directory.class_words
    assert from_object.term_id_for("Transaction Identifier") == "TRM-400009"


def test_the_assembled_vocabulary_answers_the_verbs() -> None:
    """A bundle is only loaded correctly if the verbs work on it.

    Equality against the hand-merge proves the fields; this proves the fields
    were the right ones. Each assertion touches a different section of the
    bundle — the catalog, an allow-list, the class-word map and the glossary — so
    a section wired to the wrong constructor argument shows up here.
    """
    from acronymkit.governed import expand_identifier, is_compliant, to_physical_name

    nds = load_bundle(FIXTURES)

    assert expand_identifier("TXN_APPLNT_ID", nds).phrase == "Transaction Applicant Identifier"
    assert is_compliant("TXN_APPLNT_ID", nds).compliant is True
    assert nds.class_word_for("DT") == "Date"
    assert to_physical_name("Customer Account Open Date", nds).term_id == "TRM-400001"


def test_a_bundle_load_is_deterministic() -> None:
    """Two loads of one directory must produce identical rows.

    Nothing here may depend on directory iteration order or on set iteration:
    the same files loaded twice in one process are the same vocabulary, or the
    audit trail this subsystem sells is worth nothing.
    """
    assert load_bundle(FIXTURES).entries == load_bundle(FIXTURES).entries


def test_a_missing_bundle_path_is_named_in_the_error(tmp_path: Path) -> None:
    """A path that does not exist says so, and says what a bundle is."""
    with pytest.raises(LexiconError) as caught:
        load_bundle(tmp_path / "no-such-standard")

    assert "does not exist" in str(caught.value)


def test_a_directory_with_nothing_recognisable_refuses_to_return_an_empty_vocabulary(
    tmp_path: Path,
) -> None:
    """Silence is the one answer this loader must not give.

    An empty :class:`GovernedDictionary` is a legitimate object — it passes every
    token through — and it is the worst possible result of a mistyped path,
    because a pipeline built on it reports every column unknown and no error.
    So an unrecognised directory raises, and the message lists both the names
    that were looked for and the names that were there.
    """
    (tmp_path / "standard.xlsx").write_bytes(b"not a bundle")

    with pytest.raises(LexiconError) as caught:
        load_bundle(tmp_path)

    message = str(caught.value)
    assert "dictionary.json" in message
    assert "standard.xlsx" in message


def test_two_files_claiming_one_section_is_an_error_rather_than_a_coin_toss(
    tmp_path: Path,
) -> None:
    """``dictionary.json`` and ``catalog.json`` side by side is a question, not a default.

    Both names are accepted for the catalog section precisely because a standard
    exported by somebody else will not use the fixture corpus's names. That
    tolerance is what makes the ambiguous case possible, so the ambiguous case
    has to be refused: choosing one would silently load half a caller's
    vocabulary.
    """
    (tmp_path / "dictionary.json").write_text('{"entries": []}', encoding="utf-8")
    (tmp_path / "catalog.json").write_text('{"entries": []}', encoding="utf-8")

    with pytest.raises(LexiconError) as caught:
        load_bundle(tmp_path)

    message = str(caught.value)
    assert "catalog.json" in message
    assert "dictionary.json" in message


def test_the_single_file_form_must_be_an_object(tmp_path: Path) -> None:
    """A bare array is a catalog, not a bundle, and the message says which."""
    path = tmp_path / "bundle.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(LexiconError) as caught:
        load_bundle(path)

    assert "JSON object" in str(caught.value)


def test_a_bundle_may_carry_a_caller_overlay_without_the_bundle_holding_one() -> None:
    """``custom=`` layers onto a bundle; a bundle never supplies its own overlay.

    ``custom_overlay.json`` sits in the fixture directory and is deliberately not
    a bundle section. An overlay is the caller's, and a loader that applied one
    it found lying next to the standard would return a vocabulary that disagrees
    with the catalog with nothing at the call site to say so.
    """
    plain = load_bundle(FIXTURES)
    overlaid = load_bundle(FIXTURES, custom={"KYC": "Know Your Customer"})

    assert plain.lookup("KYC") is None
    assert overlaid.resolve("KYC").canonical == "Know Your Customer"
    assert overlaid.resolve("KYC").source is ExpansionSource.CUSTOM
    assert overlaid.entries == plain.entries


# --------------------------------------------------------------------------
# load_bundle: the pin sheet
# --------------------------------------------------------------------------
def _pin_bundle(tmp_path: Path, entries: list[dict[str, Any]], pins: dict[str, Any]) -> Path:
    """Write a two-file bundle holding a catalog and a pin sheet.

    ``source`` is filled in where a row omits it, because
    :class:`~acronymkit.governed.models.GovernedEntry` requires it and the rows
    below are about pins rather than about provenance. Every other field is left
    exactly as the test wrote it.

    Args:
        tmp_path: The directory to write into. Created if it does not exist, so
            a test may use two bundles under one ``tmp_path``.
        entries: Catalog rows.
        pins: The pin sheet.

    Returns:
        The bundle directory.
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    entries = [{"source": "governed", **row} for row in entries]
    (tmp_path / "dictionary.json").write_text(json.dumps({"entries": entries}), encoding="utf-8")
    (tmp_path / "ambiguity_pins.json").write_text(json.dumps(pins), encoding="utf-8")
    return tmp_path


def test_the_pin_sheet_fills_a_gap_in_a_catalog_row_and_records_that_it_did(
    tmp_path: Path,
) -> None:
    """A row with no pin gains the sheet's, and says where the pin came from.

    Provenance is the whole product here. "``ID`` is pinned to Identifier" and
    "``ID`` is pinned to Identifier *by the pin sheet, not by the catalog row*"
    are different facts, and a reviewer chasing a wrong expansion needs the
    second one to know which file to open.
    """
    bundle = _pin_bundle(
        tmp_path,
        [{"token": "ID", "canonical": "Identity", "kind": "ambiguous_pinned"}],
        {"ID": {"candidates": ["Identity", "Identifier", "Idaho"], "_pin": "Identifier"}},
    )

    entry = load_bundle(bundle).lookup("ID")

    assert entry is not None
    assert entry.pin == "Identifier"
    assert entry.candidates == ("Identity", "Identifier", "Idaho")
    assert entry.source is ExpansionSource.PINNED
    assert "pin sheet" in (entry.notes or "")


def test_the_pin_sheet_is_read_whether_the_pin_key_is_underscored_or_not(
    tmp_path: Path,
) -> None:
    """``_pin`` and ``pin`` are one key spelled two ways, and both are honoured.

    The fixture corpus writes ``_pin`` on purpose, so that a loader dropping
    metadata keys without thinking produces an unpinned collision rather than a
    wrong pin. Reading it is therefore a decision, and a decision only one file
    knows about is a trap — so both spellings are supported and this test is
    where that is written down.
    """
    rows = [{"token": "SRC", "canonical": "Sourcing", "kind": "ambiguous_pinned"}]
    sheet = {"candidates": ["Sourcing", "Source"], "pin": "Source"}

    plain = load_bundle(_pin_bundle(tmp_path / "plain", rows, {"SRC": sheet}))
    underscored = load_bundle(
        _pin_bundle(
            tmp_path / "under",
            rows,
            {"SRC": {"candidates": sheet["candidates"], "_pin": sheet["pin"]}},
        )
    )

    assert plain.entries == underscored.entries
    assert plain.lookup("SRC").pin == "Source"


def test_a_null_pin_never_erases_a_pin_the_catalog_recorded(tmp_path: Path) -> None:
    """ "No decision" in one file does not undo a decision in the other.

    A null pin records that governance has deliberately not ruled. That is a
    statement about the pin sheet, not an instruction to discard what the
    catalog says, and treating it as one would let adding a row to a pin sheet
    quietly unpin a token.
    """
    bundle = _pin_bundle(
        tmp_path,
        [
            {
                "token": "CTL",
                "canonical": "Control",
                "pin": "Control",
                "candidates": ["Controlling", "Control"],
                "kind": "ambiguous_pinned",
            }
        ],
        {"CTL": {"candidates": ["Controlling", "Control"], "_pin": None}},
    )

    assert load_bundle(bundle).lookup("CTL").pin == "Control"


def test_a_pin_sheet_token_with_no_catalog_row_becomes_a_row_with_no_entry_id(
    tmp_path: Path,
) -> None:
    """A recorded decision survives the catalog not having caught up.

    Dropping it would make the pin sheet's effect depend on whether somebody
    remembered to add the row. Minting it with an ``entry_id`` would be worse:
    the audit trail would point at a catalog row that does not exist.
    """
    bundle = _pin_bundle(
        tmp_path,
        [],
        {
            "XREF": {
                "candidates": ["Cross Reference", "Cross Referenced"],
                "_pin": "Cross Reference",
            }
        },
    )

    entry = load_bundle(bundle).lookup("XREF")

    assert entry is not None
    assert entry.canonical == "Cross Reference"
    assert entry.entry_id is None
    assert entry.source is ExpansionSource.PINNED


def test_a_minted_row_the_sheet_did_not_pin_is_scored_and_says_so(tmp_path: Path) -> None:
    """An unruled collision is settled by the score and never claims full confidence.

    The same treatment
    :meth:`~acronymkit.governed.dictionary.GovernedDictionary.from_long_to_short`
    gives a collision it settles itself: ``scored``, confidence below full, and
    a note naming what was chosen over what. A derived answer that claimed the
    confidence of a governed one would make the field worthless for every other
    row.
    """
    bundle = _pin_bundle(
        tmp_path,
        [],
        {"PROC": {"candidates": ["Processing", "Process", "Procedure"], "_pin": None}},
    )

    entry = load_bundle(bundle).lookup("PROC")

    assert entry is not None
    assert entry.source is ExpansionSource.SCORED
    assert entry.confidence < 1.0
    assert entry.pin is None
    assert "Processing" in (entry.notes or "")


def test_two_files_pinning_one_token_differently_is_refused(tmp_path: Path) -> None:
    """Choosing between two recorded decisions is not a loading question.

    This is the design thesis applied to file loading. A silent pick would be
    the library overruling a decision a governance function signed off, with
    nothing downstream able to tell it happened — the same failure as guessing
    at an unknown token, arriving one layer earlier.
    """
    bundle = _pin_bundle(
        tmp_path,
        [
            {
                "token": "DEP",
                "canonical": "Deposit",
                "pin": "Deposit",
                "candidates": ["Deposit", "Department"],
                "kind": "ambiguous_pinned",
            }
        ],
        {"DEP": {"candidates": ["Deposit", "Department"], "_pin": "Department"}},
    )

    with pytest.raises(LexiconError) as caught:
        load_bundle(bundle)

    message = str(caught.value)
    assert "'Deposit'" in message
    assert "'Department'" in message


def test_two_files_carrying_different_candidate_sets_is_refused(tmp_path: Path) -> None:
    """A merged candidate set would decide which collision is the real one.

    ``beat`` is an audit field: it says what the winner was chosen over. Union
    the two sets and it reports a contest that never happened; take one and the
    other file's rows are silently ignored.
    """
    bundle = _pin_bundle(
        tmp_path,
        [
            {
                "token": "MO",
                "canonical": "Month",
                "candidates": ["Month", "Monthly"],
                "kind": "ambiguous_pinned",
            }
        ],
        {"MO": {"candidates": ["Month", "Missouri"], "_pin": None}},
    )

    with pytest.raises(LexiconError) as caught:
        load_bundle(bundle)

    assert "candidate sets" in str(caught.value)


# --------------------------------------------------------------------------
# load_bundle: malformed sections
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("file_name", "content", "expected"),
    [
        ("allowlist.json", '{"approved_abbreviations": "TXN"}', "array of tokens"),
        ("allowlist.json", '{"common_keywords": [1, 2]}', "only tokens"),
        ("class_words.json", '{"DT": ["Date"]}', "spelled-out form"),
        ("ambiguity_pins.json", '{"ID": "Identifier"}', "must be a JSON object"),
        ("ambiguity_pins.json", '{"ID": {"candidates": "Identifier"}}', "array of long forms"),
        ("term_glossary.json", '{"Customer Identifier": 4001}', "must be a string"),
    ],
)
def test_a_malformed_bundle_section_names_what_is_wrong(
    tmp_path: Path, file_name: str, content: str, expected: str
) -> None:
    """Every section validates its own shape, and the message is actionable.

    A standard is authored by hand in a text editor, so these are the mistakes
    that will actually be made: a single token where an array belongs, a number
    where a term id belongs, a candidate list written as one string. Each has to
    fail naming the file and the key, because "the bundle is invalid" sends
    somebody to read five files.

    Args:
        tmp_path: A scratch bundle directory.
        file_name: The section file to break.
        content: Its malformed content.
        expected: A fragment the message must carry.
    """
    (tmp_path / file_name).write_text(content, encoding="utf-8")

    with pytest.raises(LexiconError) as caught:
        load_bundle(tmp_path)

    assert expected in str(caught.value)


def test_a_bundle_file_that_is_not_json_names_the_file(tmp_path: Path) -> None:
    """A truncated export must not read as an empty section."""
    (tmp_path / "dictionary.json").write_text('{"entries": [', encoding="utf-8")

    with pytest.raises(LexiconError) as caught:
        load_bundle(tmp_path)

    assert "dictionary.json" in str(caught.value)
    assert "not valid JSON" in str(caught.value)


def test_the_class_word_map_is_read_in_both_of_its_shapes(tmp_path: Path) -> None:
    """A file that describes itself and a file that is only the map mean the same thing.

    ``class_words.json`` in the fixture corpus keeps the map under
    ``"abbreviations"`` beside its spelled-out forms and its trailing-token
    policy; a caller assembling a bundle by hand writes the map and nothing
    else. Both are the class-word map.
    """
    (tmp_path / "class_words.json").write_text('{"DT": "Date", "CD": "Code"}', encoding="utf-8")
    flat = load_bundle(tmp_path)

    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    (nested_dir / "class_words.json").write_text(
        '{"_meta": {"file": "class_words.json"}, "abbreviations": {"DT": "Date", "CD": "Code"}, '
        '"full_words": ["Date", "Code"]}',
        encoding="utf-8",
    )
    nested = load_bundle(nested_dir)

    assert flat.class_words == {"DT": "Date", "CD": "Code"}
    assert nested.class_words == flat.class_words


def test_the_bundle_file_names_are_published_rather_than_hidden() -> None:
    """``BUNDLE_FILES`` is the format, so it is exported and the fixture matches it.

    A layout convention that lives only inside a function body cannot be
    checked by a caller assembling a directory. This asserts the two things a
    caller needs: the table is reachable, and the fixture corpus — the worked
    example the documentation points at — is actually an instance of it.
    """
    stems = {section: names for section, names, _ in BUNDLE_FILES}

    assert set(stems) == {"catalog", "allow_lists", "class_words", "pins", "terms"}
    for _, names, suffixes in BUNDLE_FILES:
        assert any(
            (FIXTURES / f"{stem}{suffix}").is_file() for stem in names for suffix in suffixes
        )


# --------------------------------------------------------------------------
# load_csv: what a spreadsheet export actually contains
# --------------------------------------------------------------------------
def test_a_two_column_short_to_long_csv_loads(tmp_path: Path) -> None:
    """The plain case, and the shape of every other test in this section."""
    path = _write_csv(
        tmp_path / "catalog.csv",
        "token,canonical\nTXN,Transaction\nAPPLNT,Applicant\n",
    )

    catalog = load_csv(path, token_column="token", canonical_column="canonical")

    assert catalog.lookup("TXN").canonical == "Transaction"
    assert catalog.lookup("applnt").canonical == "Applicant"
    assert len(catalog) == 2


def test_the_byte_order_mark_excel_writes_does_not_hide_the_first_column(
    tmp_path: Path,
) -> None:
    """A BOM welded onto the first header is the commonest "column not found".

    Excel writes UTF-8 with a byte-order mark by default. Decoded as plain
    UTF-8, the first header becomes ``"\\ufefftoken"`` and every lookup of
    ``"token"`` fails with a message that looks like the caller's mistake. The
    default encoding here is ``utf-8-sig`` for exactly this reason.
    """
    path = _write_csv(
        tmp_path / "bom.csv",
        "token,canonical\r\nTXN,Transaction\r\n",
        encoding="utf-8-sig",
    )

    catalog = load_csv(path, token_column="token", canonical_column="canonical")

    assert catalog.lookup("TXN").canonical == "Transaction"


def test_crlf_endings_and_quoted_commas_survive(tmp_path: Path) -> None:
    """A Windows export with a comma inside a long form must not shear.

    Both halves matter: a stray ``\\r`` on the last field would end up inside
    the long form, and a naive split on commas would cut "Cross Reference,
    Internal" into two fields and shift every column after it.
    """
    path = _write_csv(
        tmp_path / "crlf.csv",
        'token,canonical\r\nXREF,"Cross Reference, Internal"\r\nTXN,Transaction\r\n',
    )

    catalog = load_csv(path, token_column="token", canonical_column="canonical")

    assert catalog.lookup("XREF").canonical == "Cross Reference, Internal"
    assert catalog.lookup("TXN").canonical == "Transaction"


def test_blank_rows_and_half_filled_rows_are_skipped_rather_than_loaded(
    tmp_path: Path,
) -> None:
    """A gap in the export is a gap in the catalog, not an entry that knows nothing.

    A trailing blank line is what a spreadsheet writes; a row with a token and
    no long form is what somebody leaves behind mid-edit. Loading either would
    produce an entry reporting ``is_known`` with nothing in it, which is the one
    outcome this package exists to prevent.
    """
    path = _write_csv(
        tmp_path / "gappy.csv",
        "token,canonical\nTXN,Transaction\n\n   ,   \nNBR,\n,Number\nACCT,Account\n\n",
    )

    catalog = load_csv(path, token_column="token", canonical_column="canonical")

    assert sorted(entry.token for entry in catalog.entries) == ["ACCT", "TXN"]


def test_a_row_shorter_than_the_header_is_skipped(tmp_path: Path) -> None:
    """A ragged export loses its trailing cells; it must not lose its meaning."""
    path = _write_csv(
        tmp_path / "ragged.csv",
        "token,canonical,domain\nTXN,Transaction,transaction\nNBR\n",
    )

    catalog = load_csv(path, token_column="token", canonical_column="canonical")

    assert len(catalog) == 1


def test_a_repeated_token_resolves_last_wins(tmp_path: Path) -> None:
    """One rule for duplicates, stated on the function and asserted here.

    A short → long file has nowhere to record that two rows collided, so this
    direction flattens them the way a mapping does. The test exists so the rule
    is a decision rather than an accident of implementation — and the docstring
    points a caller with real collisions at the long → short loader instead.
    """
    path = _write_csv(
        tmp_path / "dupes.csv",
        "token,canonical\nID,Identity\nID,Identifier\n",
    )

    catalog = load_csv(path, token_column="token", canonical_column="canonical")

    assert catalog.lookup("ID").canonical == "Identifier"
    assert len(catalog) == 1


def test_a_missing_column_names_the_headers_that_were_actually_found(
    tmp_path: Path,
) -> None:
    """ "No such column" without the real headers is not actionable.

    The caller is looking at a file they did not write, exported by a tool they
    do not control. The one thing they need is the list of names the file
    actually has, so the fix is retyping one argument rather than opening the
    file in another program.
    """
    path = _write_csv(
        tmp_path / "other.csv",
        "Long Name,Preferred Abbreviation\nTransaction,TXN\n",
    )

    with pytest.raises(LexiconError) as caught:
        load_csv(path, token_column="token", canonical_column="canonical")

    message = str(caught.value)
    assert "'token'" in message
    assert "'Long Name'" in message
    assert "'Preferred Abbreviation'" in message


def test_a_header_carrying_incidental_whitespace_still_matches(tmp_path: Path) -> None:
    """``"token "`` and ``"token"`` are one column name written twice.

    Surrounding whitespace in a header is an export artefact, never a
    distinction somebody intended. Nothing else about the name is normalised:
    case and punctuation are the caller's, and matching those loosely would let
    a file resolve to a column the call did not name.
    """
    path = _write_csv(
        tmp_path / "spacey.csv",
        " token , canonical \nTXN,Transaction\n",
    )

    catalog = load_csv(path, token_column="token", canonical_column="canonical")

    assert catalog.lookup("TXN").canonical == "Transaction"


def test_a_duplicated_header_name_is_refused(tmp_path: Path) -> None:
    """Two columns with one name make the choice between them undecidable.

    Silently taking the first or the last would pick a column on the strength
    of nothing, and the caller would have no way to know which one they got.
    """
    path = _write_csv(
        tmp_path / "twice.csv",
        "token,canonical,token\nTXN,Transaction,XYZ\n",
    )

    with pytest.raises(LexiconError) as caught:
        load_csv(path, token_column="token", canonical_column="canonical")

    assert "more than once" in str(caught.value)


def test_an_empty_file_says_what_a_governed_csv_needs(tmp_path: Path) -> None:
    """Zero bytes is a failed export, and reporting zero rows would hide it."""
    path = _write_csv(tmp_path / "empty.csv", "")

    with pytest.raises(LexiconError) as caught:
        load_csv(path, token_column="token", canonical_column="canonical")

    assert "is empty" in str(caught.value)


def test_a_missing_file_is_reported_as_a_lexicon_error(tmp_path: Path) -> None:
    """A typo'd path must not surface as a bare ``FileNotFoundError``.

    Every other loading failure in this subsystem is a ``LexiconError``, and a
    caller writing one ``except`` clause around catalog loading should catch all
    of them.
    """
    with pytest.raises(LexiconError) as caught:
        load_csv(tmp_path / "nope.csv", token_column="token", canonical_column="canonical")

    assert "could not be read" in str(caught.value)


def test_a_non_utf8_export_loads_when_the_encoding_is_named_and_fails_when_it_is_not(
    tmp_path: Path,
) -> None:
    """Encoding is explicit, so a legacy export is loadable and a wrong guess is loud.

    A catalog exported from an older system arrives in a single-byte codepage,
    and the environment this library runs in may have ``LANG=C``. Neither the
    file nor the locale is consulted: the caller names the codec, and naming the
    wrong one raises with the codec in the message rather than decoding into
    mojibake that would become somebody's governed long form.
    """
    path = _write_csv(
        tmp_path / "legacy.csv",
        "token,canonical\nCUR,Devise Étrangère\n",
        encoding="cp1252",
    )

    catalog = load_csv(path, token_column="token", canonical_column="canonical", encoding="cp1252")
    assert catalog.lookup("CUR").canonical == "Devise Étrangère"

    with pytest.raises(LexiconError) as caught:
        load_csv(path, token_column="token", canonical_column="canonical", encoding="utf-8")
    assert "utf-8" in str(caught.value)


def test_a_tab_separated_export_loads(tmp_path: Path) -> None:
    """``delimiter=`` covers the other thing a spreadsheet writes."""
    path = _write_csv(tmp_path / "tabs.tsv", "token\tcanonical\nTXN\tTransaction\n")

    catalog = load_csv(path, token_column="token", canonical_column="canonical", delimiter="\t")

    assert catalog.lookup("TXN").canonical == "Transaction"


def test_the_dictionary_extras_reach_the_constructor(tmp_path: Path) -> None:
    """A catalog CSV is not a whole standard, so the other arguments pass through.

    Without them a caller with a CSV catalog would be back to building the
    dictionary by hand to attach their allow-lists — which is the friction these
    loaders exist to remove.
    """
    path = _write_csv(tmp_path / "catalog.csv", "token,canonical\nTXN,Transaction\n")

    catalog = load_csv(
        path,
        token_column="token",
        canonical_column="canonical",
        approved_abbreviations=["TXN"],
        short_full_words=["FRAUD"],
        class_words={"DT": "Date"},
        term_index={"Transaction Identifier": "TRM-400009"},
    )

    assert catalog.is_approved("TXN") is True
    assert catalog.is_approved("FRAUD") is True
    assert catalog.class_word_for("DT") == "Date"
    assert catalog.term_id_for("transaction  identifier") == "TRM-400009"


# --------------------------------------------------------------------------
# load_long_to_short_csv: the direction a real catalog is stored in
# --------------------------------------------------------------------------
def test_inverting_a_long_to_short_export_surfaces_the_collision(tmp_path: Path) -> None:
    """The whole reason this loader exists, on the catalog's own headers.

    Read long → short, the file is four unambiguous rows and nobody who wrote it
    had to think about ambiguity. Read backwards, it is one token with four
    candidates and no row saying which one a bare ``ID`` meant. The ambiguity was
    always there; inverting is what makes it visible, and the entry records that
    a score rather than a person settled it.
    """
    path = _write_csv(
        tmp_path / "standard.csv",
        "Long Name,Preferred Abbreviation\n"
        "Idaho,ID\n"
        "Identification,ID\n"
        "Identifier,ID\n"
        "Transaction,TXN\n",
    )

    catalog = load_long_to_short_csv(
        path, long_column="Long Name", short_column="Preferred Abbreviation"
    )
    entry = catalog.lookup("ID")

    assert entry.candidates == ("Idaho", "Identification", "Identifier")
    assert entry.canonical == "Identifier"
    assert entry.pin is None
    assert entry.source is ExpansionSource.SCORED
    assert entry.confidence < 1.0
    assert catalog.lookup("TXN").confidence == 1.0


def test_candidate_order_is_file_order(tmp_path: Path) -> None:
    """Position zero is read by a policy, so the file's order must be preserved.

    ``NamingPolicy.frequency_baseline()`` takes the first declared candidate.
    That is only a meaningful contrast arm if "first" means what the catalog put
    first, which makes row order part of this loader's contract rather than an
    implementation detail.
    """
    path = _write_csv(
        tmp_path / "ordered.csv",
        "long,short\nSourcing,SRC\nSource,SRC\nSourced,SRC\n",
    )

    catalog = load_long_to_short_csv(path, long_column="long", short_column="short")

    assert catalog.lookup("SRC").candidates == ("Sourcing", "Source", "Sourced")


def test_one_long_form_claimed_by_two_tokens_resolves_last_wins(tmp_path: Path) -> None:
    """The direction the inversion cannot keep, stated rather than hidden.

    Many long forms to one token is the collision this loader preserves. One
    long form to two tokens is the catalog contradicting itself in the direction
    it was authored in, and the mapping the inversion consumes cannot hold both.
    """
    path = _write_csv(
        tmp_path / "contradiction.csv",
        "long,short\nNumber,NBR\nNumber,NUM\n",
    )

    catalog = load_long_to_short_csv(path, long_column="long", short_column="short")

    assert catalog.lookup("NUM") is not None
    assert catalog.lookup("NBR") is None


def test_the_long_to_short_loader_reports_a_missing_column_the_same_way(
    tmp_path: Path,
) -> None:
    """Both CSV front ends share one reader, so they share one error."""
    path = _write_csv(tmp_path / "standard.csv", "long,short\nTransaction,TXN\n")

    with pytest.raises(LexiconError) as caught:
        load_long_to_short_csv(path, long_column="Long Name", short_column="Preferred Abbreviation")

    assert "'long', 'short'" in str(caught.value)


# --------------------------------------------------------------------------
# load_term_index_csv
# --------------------------------------------------------------------------
def test_the_glossary_loader_reads_two_columns_and_ignores_the_rest() -> None:
    """A glossary export is wide; ``term_index`` answers one question.

    The fixture glossary carries a physical name, a class word, a domain, a
    confidentiality class and a confidence beside the two columns that matter.
    Importing them would invent a second contract for columns nothing here
    reads.
    """
    index = load_term_index_csv(
        FIXTURES / "term_glossary.csv",
        name_column="logical_name",
        term_id_column="term_id",
    )

    assert index["Customer Account Open Date"] == "TRM-400001"
    assert index["Transaction Identifier"] == "TRM-400009"
    assert all(value.startswith("TRM-") for value in index.values())
