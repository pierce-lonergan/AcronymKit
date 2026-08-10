"""Readers that normalise gold-standard abbreviation corpora to one type.

Every corpus in this space uses its own format and its own conventions about
what counts as an annotation. The job here is to turn each into a
:class:`GoldDocument` so the scorer never has to know which corpus it is
looking at — and so adding a corpus is a reader, not a new evaluation.

Corpora are fetched by ``tools/fetch_data.py`` into the git-ignored ``data/``
directory. Nothing here is imported by the library.
"""

from __future__ import annotations

import functools
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, Optional, Sequence

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
# SDU@AAAI-21 shared task 2 — acronym disambiguation
# ---------------------------------------------------------------------------
#
# A different task, so deliberately a different type. MED1250 asks "which spans
# in this document are definitions?"; this corpus asks "this token is an
# acronym, which of its known expansions is meant here?" — the candidate set is
# given, so there is nothing to extract and nothing to pair. Forcing it into
# GoldDocument would mean inventing a document/pair structure the annotation
# does not have, which is exactly the objection bench/splits.toml raises against
# deriving pairs from span corpora.
#
# Record format (dataset/dev.json, per the shared task README), a JSON list of::
#
#     {"id": "DEV-0",
#      "tokens": ["In", ",", "we", "investigated", "the", "FL", "loss", ...],
#      "acronym": 5,                       <- index into tokens
#      "expansion": "federated learning"}  <- verbatim key from diction.json
#
# and dataset/diction.json, a JSON object ``{acronym: [expansion, ...]}`` whose
# values are the *only* legal predictions. Gold expansions are lower-cased
# strings drawn from it, and the official scorer compares by exact string
# equality, so an expansion re-cased or re-spaced is a wrong answer.

SDU21_AD_DEV_FILENAME = "sdu21_ad_dev.json"
SDU21_AD_TRAIN_FILENAME = "sdu21_ad_train.json"
SDU21_AD_DICTION_FILENAME = "sdu21_ad_diction.json"

_SDU21_AD_FILES = {
    "dev": (SDU21_AD_DEV_FILENAME, "sdu21-ad-dev"),
    "train": (SDU21_AD_TRAIN_FILENAME, "sdu21-ad-train"),
}


@dataclass(frozen=True)
class DisambiguationInstance:
    """One acronym occurrence to be resolved against a fixed candidate set.

    Attributes:
        uid: The corpus-native sample id (``"DEV-0"``), unique by construction
            and used as the prediction key, exactly as the shared task's own
            scorer does.
        tokens: The sentence as the corpus tokenised it.
        acronym_index: Index into ``tokens`` of the occurrence to resolve.
        expansion: The gold expansion, verbatim from the dictionary.
    """

    uid: str
    tokens: tuple[str, ...]
    acronym_index: int
    expansion: str

    @property
    def acronym(self) -> str:
        """The surface form of the acronym token being resolved."""
        return self.tokens[self.acronym_index]

    @property
    def context(self) -> str:
        """The sentence as a single string.

        The corpus ships tokens, not text, so *some* join is unavoidable. A
        plain space join is chosen because it invents nothing: any smarter
        detokenisation is a guess about the original punctuation spacing, and a
        guess in the harness is a guess in the number.
        """
        return " ".join(self.tokens)


def _sdu21_ad_source(path: Optional[Path], split: str) -> Path:
    """Resolve and check the file backing one split."""
    if split not in _SDU21_AD_FILES:
        raise SystemExit(f"unknown SDU21-AD split {split!r}; known: {sorted(_SDU21_AD_FILES)}")
    filename, key = _SDU21_AD_FILES[split]
    source = path or (DATA_DIR / filename)
    if not source.is_file():
        raise SystemExit(f"missing {source}\nRun: python tools/fetch_data.py {key}")
    return source


def read_sdu21_ad(path: Optional[Path] = None, split: str = "dev") -> list[DisambiguationInstance]:
    """Parse an SDU@AAAI-21 acronym-disambiguation split.

    Args:
        path: Override the default ``data/sdu21_ad_<split>.json`` location.
        split: ``"dev"`` (the evaluation set) or ``"train"`` (used only to build
            the shared task's most-frequent-expansion baseline).

    Returns:
        One :class:`DisambiguationInstance` per sample, in file order.

    Raises:
        SystemExit: If the split has not been fetched, or the document is not
            the list of records the format specifies.
    """
    source = _sdu21_ad_source(path, split)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit(
            f"{source} should hold a JSON list of samples, got {type(payload).__name__}"
        )

    instances: list[DisambiguationInstance] = []
    for record in payload:
        tokens = tuple(record["tokens"])
        index = int(record["acronym"])
        if not 0 <= index < len(tokens):
            raise SystemExit(
                f"{source}: sample {record.get('id')!r} indexes token {index} of {len(tokens)}"
            )
        instances.append(
            DisambiguationInstance(
                uid=str(record["id"]),
                tokens=tokens,
                acronym_index=index,
                expansion=str(record["expansion"]),
            )
        )
    return instances


def read_sdu21_ad_diction(path: Optional[Path] = None) -> dict[str, list[str]]:
    """Parse ``diction.json`` into ``{acronym: [expansion, ...]}``.

    Returned as a plain mapping rather than an
    :class:`~acronymkit.disambiguation.ExpansionDictionary` so the reader stays
    independent of the library under test, and so a baseline that has nothing to
    do with acronymkit can consume the same candidate sets.

    Args:
        path: Override the default ``data/sdu21_ad_diction.json`` location.

    Returns:
        The dictionary, key order preserved. Candidate order is preserved too:
        the shared task's own baseline breaks frequency ties on it.

    Raises:
        SystemExit: If the dictionary has not been fetched or is malformed.
    """
    source = path or (DATA_DIR / SDU21_AD_DICTION_FILENAME)
    if not source.is_file():
        raise SystemExit(f"missing {source}\nRun: python tools/fetch_data.py sdu21-ad-diction")
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{source} should hold a JSON object, got {type(payload).__name__}")
    return {str(key): [str(value) for value in values] for key, values in payload.items()}


# ---------------------------------------------------------------------------
# PLOD-CW — abbreviation *span* detection, and deliberately not pairing
# ---------------------------------------------------------------------------
#
# PLOD (Zilio et al., LREC 2022) is BIO token classification over sentences
# taken from PLOS journal articles. ``PLOD-CW`` is the small teaching subset the
# University of Surrey publishes: 1,072 / 126 / 153 sentences, 50,000 tokens.
#
# Record format — one ``token POS_TAG BIO_TAG`` line per token, blank line
# between sentences, fields separated by single spaces::
#
#     dithiothreitol NOUN B-LF
#     ( PUNCT B-O
#     DTT PROPN B-AC
#     ) PUNCT B-O
#
# Note ``B-O`` rather than the usual ``O`` for outside. Labels are ``AC``
# (abbreviation) and ``LF`` (long form). In this release every ``AC`` span is a
# single token — there is no ``I-AC`` anywhere in train, dev or test — while
# ``LF`` spans run ``B-LF I-LF*``.
#
# Three properties of this corpus decide how it may honestly be used, and each
# of them is a *difference from MED1250*, not a defect:
#
# 1. **It does not pair.** The annotation says "this token is an abbreviation"
#    and "these tokens are a long form". It never says which long form belongs
#    to which abbreviation. Recovering pairs needs an adjacency assumption, and
#    ``bench/splits.toml`` already rejected that: a gold standard we partly
#    invented cannot adjudicate our own system. So this reader returns spans and
#    nothing else, and the harness scores PLOD's own task.
#
# 2. **It tags every mention, not every definition.** ``SDS`` is tagged in
#    "a discontinuous SDS gel" with no expansion in sight; ``pY232`` is tagged
#    four times in one sentence; ``wk`` is tagged as an abbreviation of "week".
#    A Schwartz & Hearst extractor answers a different question — "which
#    parenthetical definitions does this text contain?" — so its recall here is
#    bounded far below 100 % by the corpus's convention rather than by its own
#    ability. ``bench/run_spans.py`` measures that bound rather than assuming it.
#
# 3. **It ships tokens, not text.** Our extractor consumes running prose, so the
#    text has to be reconstructed. That is an approximation and it is the single
#    largest arbitrary choice in the harness, which is why :func:`detokenise`
#    offers both a join that invents nothing and a join that reconstructs
#    prose — and why ``run_spans.py`` reports every system under both.

PLOD_CW_FILENAMES = {
    "train": "plod_cw_train.conll",
    "dev": "plod_cw_dev.conll",
    "test": "plod_cw_test.conll",
}

#: Splits accepted by :func:`read_plod_cw`. ``"all"`` concatenates the three in
#: train/dev/test order. acronymkit reads no training data and nothing here was
#: tuned on any of it, so the split boundary carries no contamination meaning for
#: us — ``"all"`` exists purely to quadruple a very small sample.
PLOD_CW_SPLITS = ("train", "dev", "test", "all")

#: Detokenisation styles. See :func:`detokenise`.
DETOKENISE_STYLES = ("tight", "spaced")

#: Curly quotes and the ellipsis, written as escapes rather than literals for
#: the reason ``bench/scoring.py`` gives about its dashes: a reader (and a
#: linter) cannot tell an intended smart quote from a stray one.
_RIGHT_DOUBLE_QUOTE = "\u201d"
_RIGHT_SINGLE_QUOTE = "\u2019"
_LEFT_DOUBLE_QUOTE = "\u201c"
_LEFT_SINGLE_QUOTE = "\u2018"
_ELLIPSIS = "\u2026"

#: Tokens welded to the preceding token: closing brackets, sentence punctuation
#: and English clitics. spaCy split these off; the join puts them back.
_ATTACH_LEFT = frozenset(
    {
        ",", ".", ";", ":", "!", "?", "%", ")", "]", "}", "'", '"',
        _RIGHT_DOUBLE_QUOTE, _RIGHT_SINGLE_QUOTE, _ELLIPSIS,
        "''", "n't", "'s", "'re", "'ve", "'ll", "'d", "'m",
    }
)  # fmt: skip

#: Tokens welded to the following token: opening brackets and currency marks.
_ATTACH_RIGHT = frozenset({"(", "[", "{", "$", "#", _LEFT_DOUBLE_QUOTE, _LEFT_SINGLE_QUOTE, "``"})

#: Tokens welded on both sides. Restricted to the ASCII hyphen and the slash
#: because those are the two spaCy splits that are genuinely intra-word in this
#: corpus ("SDS - PAGE", "1,4 - dithiothreitol", "and / or"). The en and em
#: dashes are deliberately *not* here: in prose they take spaces, and welding
#: them would invent a compound the source did not have.
_ATTACH_BOTH = frozenset({"-", "/"})


def detokenise(
    tokens: Sequence[str], style: str = "tight"
) -> tuple[str, tuple[tuple[int, int], ...]]:
    """Rebuild running text from a token list, recording each token's offsets.

    The corpus ships no text, so *some* join is unavoidable and every join is a
    guess about the original whitespace. Two are offered and both are reported,
    because picking one silently would put an arbitrary choice inside a number:

    ``"spaced"``
        A single space between every pair of tokens. Invents nothing — the same
        reasoning :meth:`DisambiguationInstance.context` gives — but it is not
        prose: it yields ``"( DTT )"`` and ``"1,4 - dithiothreitol"``, and the
        algorithm under test is defined over text where a bracket abuts the
        abbreviation it encloses.
    ``"tight"``
        Punctuation, brackets, clitics, hyphens and slashes are welded back on.
        Closer to the source, and the inverse of what spaCy's tokeniser did to
        produce these tokens in the first place — but it *is* a reconstruction,
        and it can weld a compound the author spaced.

    The returned offsets are exact under either style: a token's span covers its
    own characters only, so mapping a character span back to token indices is
    lossless whatever the join did between tokens.

    Args:
        tokens: The corpus's tokens, in order.
        style: One of :data:`DETOKENISE_STYLES`.

    Returns:
        ``(text, offsets)`` where ``offsets[i]`` is the half-open character span
        of ``tokens[i]`` within ``text``.

    Raises:
        SystemExit: For an unknown style.
    """
    if style not in DETOKENISE_STYLES:
        raise SystemExit(f"unknown detokenise style {style!r}; known: {list(DETOKENISE_STYLES)}")

    parts: list[str] = []
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for index, token in enumerate(tokens):
        separator = ""
        if index:
            previous = tokens[index - 1]
            welded = style == "tight" and (
                token in _ATTACH_LEFT
                or previous in _ATTACH_RIGHT
                or token in _ATTACH_BOTH
                or previous in _ATTACH_BOTH
            )
            separator = "" if welded else " "
        parts.append(separator + token)
        cursor += len(separator)
        offsets.append((cursor, cursor + len(token)))
        cursor += len(token)
    return "".join(parts), tuple(offsets)


@dataclass(frozen=True)
class SpanDocument:
    """One sentence with its annotated abbreviation and long-form spans.

    Deliberately not a :class:`GoldDocument`. That type promises
    ``pairs``, and this corpus has none; widening it would let a pair-scoring
    runner consume a span corpus and report a number that means nothing.

    Attributes:
        uid: Prediction key, unique across splits.
        identifier: Corpus-native position, for display.
        tokens: The sentence as PLOD tokenised it.
        pos_tags: The corpus's spaCy POS tags, carried through unused.
        ner_tags: The raw BIO tags, carried through so a consumer can audit the
            span extraction rather than trust it.
        short_form_spans: Half-open ``(start, end)`` token index ranges tagged
            ``AC``. Every one is a single token in this release.
        long_form_spans: The same for ``LF``.
    """

    uid: str
    identifier: str
    tokens: tuple[str, ...] = field(default_factory=tuple)
    pos_tags: tuple[str, ...] = field(default_factory=tuple)
    ner_tags: tuple[str, ...] = field(default_factory=tuple)
    short_form_spans: tuple[tuple[int, int], ...] = field(default_factory=tuple)
    long_form_spans: tuple[tuple[int, int], ...] = field(default_factory=tuple)

    def render(self, style: str = "tight") -> tuple[str, tuple[tuple[int, int], ...]]:
        """Reconstructed text and per-token character offsets; see :func:`detokenise`."""
        return detokenise(self.tokens, style)


def _bio_spans(tags: Sequence[str], wanted: str) -> tuple[tuple[int, int], ...]:
    """Collect half-open token index ranges carrying the ``wanted`` entity type.

    An ``I-`` tag with no preceding ``B-`` opens a span rather than being
    dropped; PLOD-CW contains no such case, but silently discarding annotation
    on a malformed line is the kind of harness bug that quietly moves recall.
    """
    spans: list[tuple[int, int]] = []
    start: Optional[int] = None
    for index, tag in enumerate(tags):
        prefix, _, kind = tag.partition("-")
        if not kind:
            prefix, kind = "B", tag
        if kind != wanted:
            if start is not None:
                spans.append((start, index))
                start = None
        elif prefix == "B":
            if start is not None:
                spans.append((start, index))
            start = index
        elif start is None:
            start = index
    if start is not None:
        spans.append((start, len(tags)))
    return tuple(spans)


def _plod_cw_source(path: Optional[Path], split: str) -> Path:
    """Resolve and check the file backing one split."""
    source = path or (DATA_DIR / PLOD_CW_FILENAMES[split])
    if not source.is_file():
        raise SystemExit(f"missing {source}\nRun: python tools/fetch_data.py plod-cw-{split}")
    return source


def read_plod_cw(path: Optional[Path] = None, split: str = "test") -> list[SpanDocument]:
    """Parse a PLOD-CW CoNLL split into span-annotated sentences.

    Args:
        path: Override the default ``data/plod_cw_<split>.conll`` location.
            Ignored when ``split="all"``, which reads three files.
        split: One of :data:`PLOD_CW_SPLITS`.

    Returns:
        One :class:`SpanDocument` per sentence, in file order.

    Raises:
        SystemExit: For an unknown split, a missing file, or a line that is not
            three space-separated fields.
    """
    if split not in PLOD_CW_SPLITS:
        raise SystemExit(f"unknown PLOD-CW split {split!r}; known: {list(PLOD_CW_SPLITS)}")
    if split == "all":
        documents: list[SpanDocument] = []
        for part in ("train", "dev", "test"):
            documents.extend(read_plod_cw(split=part))
        return documents

    source = _plod_cw_source(path, split)
    raw = source.read_text(encoding="utf-8", errors="replace")

    documents = []
    for position, block in enumerate(raw.split("\n\n")):
        tokens: list[str] = []
        pos_tags: list[str] = []
        tags: list[str] = []
        for line in block.split("\n"):
            if not line.strip():
                continue
            # rsplit, not split: the token itself is the only field that could
            # contain a space, and the two tag fields never do.
            fields = line.rsplit(" ", 2)
            if len(fields) != 3:
                raise SystemExit(f"{source}: malformed line {line!r}")
            tokens.append(fields[0])
            pos_tags.append(fields[1])
            tags.append(fields[2])
        if not tokens:
            continue
        documents.append(
            SpanDocument(
                uid=f"{split}:{position:05d}",
                identifier=f"{split}#{position}",
                tokens=tuple(tokens),
                pos_tags=tuple(pos_tags),
                ner_tags=tuple(tags),
                short_form_spans=_bio_spans(tags, "AC"),
                long_form_spans=_bio_spans(tags, "LF"),
            )
        )
    return documents


def read_plod_cw_text(split: str = "test", style: str = "tight") -> list[GoldDocument]:
    """PLOD-CW as *text only*, so out-of-process baselines can be fed the same input.

    ``bench/external.py`` runs a competing extractor under a foreign interpreter
    and reaches the corpus through :func:`load`, which promises
    :class:`GoldDocument`. PLOD has no pairs, so the documents returned here
    carry ``pairs=()``.

    That is deliberate and it is also a trap, so it is spelled out: scoring a
    *pair* extractor against these documents is meaningless by construction —
    ``bench/run_extraction.py --corpus plod_cw_test`` would report zero gold
    pairs and a precision of zero, and the zero gold-pair count is the tell.
    The only correct consumer is ``bench/run_spans.py``, which scores span
    detection against :func:`read_plod_cw`.

    Args:
        split: One of :data:`PLOD_CW_SPLITS`.
        style: One of :data:`DETOKENISE_STYLES`. It is part of the corpus
            identity here, because the corpus ships no text.

    Returns:
        One text-bearing, pair-less :class:`GoldDocument` per sentence, keyed by
        the same ``uid`` :func:`read_plod_cw` uses.
    """
    return [
        GoldDocument(
            uid=document.uid,
            identifier=document.identifier,
            text=document.render(style)[0],
            pairs=(),
        )
        for document in read_plod_cw(split=split)
    ]


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------
READERS: dict[str, Callable[[], list[GoldDocument]]] = {"med1250": read_med1250}

#: Text-only views of PLOD-CW, registered so ``bench/external.py`` can load the
#: same reconstructed strings under a foreign interpreter. They hold no pairs;
#: see :func:`read_plod_cw_text` for why that is a trap worth naming.
for _split in ("test", "all"):
    for _style in DETOKENISE_STYLES:
        _suffix = "" if _style == "tight" else f"_{_style}"
        READERS[f"plod_cw_{_split}{_suffix}"] = functools.partial(
            read_plod_cw_text, split=_split, style=_style
        )

#: Disambiguation corpora are kept in their own registry because they return a
#: different type. ``load()`` promises GoldDocument objects and must keep doing
#: so; silently widening it would break the property the scorer relies on.
DISAMBIGUATION_READERS = {"sdu21_ad": read_sdu21_ad}

#: Span-detection corpora, for the same reason: they return SpanDocument, which
#: has spans and no pairs.
SPAN_READERS = {"plod_cw": read_plod_cw}


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
