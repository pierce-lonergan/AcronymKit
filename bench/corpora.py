"""Readers that normalise gold-standard abbreviation corpora to one type.

Every corpus in this space uses its own format and its own conventions about
what counts as an annotation. The job here is to turn each into a
:class:`GoldDocument` so the scorer never has to know which corpus it is
looking at — and so adding a corpus is a reader, not a new evaluation.

Corpora are fetched by ``tools/fetch_data.py`` into the git-ignored ``data/``
directory. Nothing here is imported by the library.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


@dataclass(frozen=True)
class GoldPair:
    """One annotated short-form/long-form definition.

    Attributes:
        short_form: The abbreviation as annotated.
        long_form: Its expansion as annotated.
    """

    short_form: str
    long_form: str

    def key(self, *, case_sensitive: bool = False) -> tuple[str, str]:
        """Comparison key, whitespace-collapsed and optionally case-folded."""
        short = " ".join(self.short_form.split())
        long_form = " ".join(self.long_form.split())
        if not case_sensitive:
            short, long_form = short.casefold(), long_form.casefold()
        return short, long_form


@dataclass(frozen=True)
class GoldDocument:
    """A document plus the pairs a human annotated in it.

    Attributes:
        uid: Unique key for this record. Predictions are mapped by ``uid``, not
            by ``identifier``, because a corpus identifier is not guaranteed
            unique -- MED1250 contains two PubMed IDs twice. Keying on the
            identifier silently merges those records and mis-scores both.
        identifier: The corpus-native identifier (a PubMed ID for MED1250),
            kept for display and error reporting.
        text: The span the annotations refer to.
        pairs: The human-annotated definitions.
    """

    uid: str
    identifier: str
    text: str
    pairs: tuple[GoldPair, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# MED1250 (Ab3P gold standard)
# ---------------------------------------------------------------------------
#
# Record format, per the Ab3P README:
#
#     PubMed ID
#     Title
#     Abstract
#       sf|lf                 <- two leading spaces
#     <blank line>
#
# Lines beginning ``//`` are comments, and the README assigns several of them a
# specific meaning. They are *not* part of the gold standard:
#
#     //*  sf|lf   synonym: identified by annotators, deliberately excluded
#     //!syn       no matching character (e.g. MeHg|methyl mercury)
#     //!out       long form does not appear earlier in the same sentence
#     //!ord       matching characters out of order (Y73SV|Sarcoma Virus Y73)
#     //!num       a number matches a word (2D|two dimension)
#     //!nch       long form found but some characters do not match
#     //!cnj       conjunction complicates long-form determination
#
# Treating any of those as gold would inflate recall against a target the
# corpus explicitly does not ask for. Only uncommented ``  sf|lf`` lines count.

MED1250_FILENAME = "MED1250_labeled"

_COMMENT = re.compile(r"^\s*//")

#: A record boundary: a line that is nothing but a PubMed ID.
_PUBMED_ID = re.compile(r"^\d{1,9}\s*$")


def read_med1250(path: Optional[Path] = None) -> list[GoldDocument]:
    """Parse ``MED1250_labeled`` into normalised documents.

    Args:
        path: Override the default ``data/MED1250_labeled`` location.

    Returns:
        One :class:`GoldDocument` per record, in file order. ``text`` is the
        title and abstract joined by a space, which is the span the annotations
        refer to.

    Raises:
        SystemExit: If the corpus has not been fetched.
    """
    source = path or (DATA_DIR / MED1250_FILENAME)
    if not source.is_file():
        raise SystemExit(f"missing {source}\nRun: python tools/fetch_data.py med1250")

    raw = source.read_text(encoding="utf-8", errors="replace")

    # Records are delimited by a bare PubMed ID, NOT by blank lines. Splitting
    # on "\n\n" looks right and is wrong: two abstracts in this corpus contain a
    # blank line, so that split produced 1,252 "documents", two of which had a
    # sentence as their identifier and their own definitions stranded in the
    # half that no longer contained the defining text. A silent 2-document
    # corruption is exactly the kind of harness bug that makes a headline F1
    # dishonest, so the record boundary is anchored on the ID instead.
    records: list[list[str]] = []
    for line in raw.split("\n"):
        if _PUBMED_ID.match(line):
            records.append([line.strip()])
        elif records:
            records[-1].append(line)

    documents: list[GoldDocument] = []
    for position, lines in enumerate(records):
        identifier = lines[0]
        body: list[str] = []
        pairs: list[GoldPair] = []
        for line in lines[1:]:
            if _COMMENT.match(line):
                continue  # synonyms and excluded categories: not gold
            if line.startswith("  ") and "|" in line:
                short, _, long_form = line.strip().partition("|")
                short, long_form = short.strip(), long_form.strip()
                if short and long_form:
                    pairs.append(GoldPair(short, long_form))
            elif line.strip():
                body.append(line.strip())
        if body:
            documents.append(
                GoldDocument(
                    uid=f"{position:04d}:{identifier}",
                    identifier=identifier,
                    text=" ".join(body),
                    pairs=tuple(pairs),
                )
            )
    return documents


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------
READERS = {"med1250": read_med1250}


def load(name: str) -> list[GoldDocument]:
    """Load a corpus by registry name.

    Args:
        name: Key in :data:`READERS`.

    Returns:
        The normalised documents.

    Raises:
        SystemExit: For an unknown corpus name.
    """
    if name not in READERS:
        raise SystemExit(f"unknown corpus {name!r}; known: {sorted(READERS)}")
    return READERS[name]()


def iter_pairs(documents: list[GoldDocument]) -> Iterator[GoldPair]:
    """Yield every gold pair across ``documents``."""
    for document in documents:
        yield from document.pairs
