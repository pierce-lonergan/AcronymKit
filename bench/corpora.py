"""Readers that normalise gold-standard abbreviation corpora — one type per task.

Every corpus in this space uses its own format and its own conventions about
what counts as an annotation. The job here is to turn each into the type its
*task* is defined over, so a scorer never has to know which corpus it is looking
at — and so adding a corpus is a reader, not a new evaluation.

**One type per task, not one type overall**, and the distinction is the whole
safety property of this module. The opening sentence used to say "to one type",
which stopped being true the moment the second task arrived and was quietly
false for three of them:

===========================  ================================================
task (``tools/splits.py``)   what a record is here
===========================  ================================================
``extraction``               :class:`GoldDocument` — a passage plus the
                             short-form/long-form pairs annotated in it
``span_detection``           :class:`SpanDocument` (token indices) or
                             :class:`CharSpanDocument` (character offsets) —
                             regions, never paired with each other
``disambiguation``           :class:`DisambiguationInstance` — one occurrence
                             and the fixed candidate set it resolves against
``identifier_segmentation``  :class:`SegmentationCorpus` of
                             :class:`IdentifierCaptionPair` — two surface
                             strings made of the same characters, whose gold is
                             where one of them is cut
===========================  ================================================

``TASKS`` in ``tools/splits.py`` is a closed vocabulary *because* of that table:
a corpus filed under the wrong task is how a pair scorer comes to be pointed at
a span corpus and report a meaningless zero. :data:`TASK_REGISTRIES` states
which registry may hold each task, and ``tests/test_splits_manifest.py`` checks
that every registered reader's declared task matches the registry it is in —
which nothing did while the rule was only prose in two docstrings.

Corpora are fetched by ``tools/fetch_data.py`` into the git-ignored ``data/``
directory, except the two identifier-segmentation corpora, which
``bench/run_governed_gold.py`` fetches itself and caches under
``data/governed_gold/``. Nothing here is imported by the library.

Every reader is bound to a declaration
--------------------------------------
``bench/splits.toml`` says what each corpus may be used for. For months nothing
read that file — eleven citations, all prose — and it had silently been invalid
TOML the whole time. This module is now one of its readers: every entry in
:data:`DECLARED_AS` names the manifest corpus a reader draws from, and
:func:`declaration` resolves it through ``tools/splits.py``.

That binding is what makes the manifest load-bearing rather than decorative. A
reader registered for a corpus nobody declared fails here, at the point the
corpus is loaded, instead of quietly producing a number that is exempt from the
train/test rule because nobody wrote the rule down for it.
"""

from __future__ import annotations

import functools
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Callable, Iterator, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# ---------------------------------------------------------------------------
# the manifest
# ---------------------------------------------------------------------------
#: Reader registry name -> the ``[corpora.<name>]`` table it draws from. The
#: two namespaces are deliberately not merged: a reader name encodes a split and
#: a detokenisation style (``plod_cw_test_spaced``), while a manifest name
#: identifies the *corpus*, which is the thing a licence and a role attach to.
#: Four PLOD readers share one declaration because they share one licence and
#: one contamination story.
DECLARED_AS = {
    "med1250": "med1250",
    "plod_cw": "plod",
    "plod_cw_test": "plod",
    "plod_cw_all": "plod",
    "plod_cw_test_spaced": "plod",
    "plod_cw_all_spaced": "plod",
    "sdu21_ad": "sdu21_ad",
    "sdu22_ae_legal": "sdu22_ae_legal",
    "sdu22_ae_scientific": "sdu22_ae_scientific",
    "sec_xbrl": "sec_xbrl",
    "socrata": "socrata",
}

_SPLITS_TOOL = REPO_ROOT / "tools" / "splits.py"


@functools.lru_cache(maxsize=1)
def _splits_module() -> Optional[ModuleType]:
    """Import ``tools/splits.py`` by path, or ``None`` if it cannot be read.

    By path, and not as ``tools.splits``, because ``tools/`` is a directory of
    scripts and must not become a package — the same reasoning
    ``tests/test_check_claims.py`` records for ``check_claims.py``. Importing a
    thing differently for the convenience of a caller changes the shape of the
    thing.
    """
    if not _SPLITS_TOOL.is_file():  # pragma: no cover - not a source checkout
        return None
    spec = importlib.util.spec_from_file_location("_acronymkit_bench_splits", _SPLITS_TOOL)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        return None
    module = importlib.util.module_from_spec(spec)
    # Registered before execution, not after: ``@dataclass`` resolves a field's
    # annotations through ``sys.modules[cls.__module__]`` while the class body
    # is still running, so a by-path import that skips this step dies on the
    # first dataclass in the file with an unrelated-looking AttributeError.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@functools.lru_cache(maxsize=1)
def _manifest() -> Optional[object]:
    """The parsed manifest, or ``None`` when this interpreter cannot parse TOML.

    The distinction matters and is why this returns ``None`` rather than
    raising. "The manifest says this corpus is undeclared" is a rule violation
    and must stop the run. "This interpreter has no TOML parser" (3.9 and 3.10,
    where ``tomllib`` does not exist and ``tomli`` is not a declared dev
    dependency) is an *environment* limitation, and turning it into a hard
    failure would break every bench runner on the interpreters this package
    still supports, to enforce a rule the environment simply cannot check.
    """
    module = _splits_module()
    if module is None:  # pragma: no cover - not a source checkout
        return None
    try:
        return module.load()
    except module.SplitsError as error:  # pragma: no cover - 3.9/3.10 or a broken file
        print(f"bench.corpora: cannot read bench/splits.toml ({error})", file=sys.stderr)
        return None


def declaration(name: str) -> Optional[object]:
    """What ``bench/splits.toml`` declares about the corpus a reader draws from.

    Args:
        name: A reader registry name, e.g. ``"plod_cw_test"``, or a manifest
            corpus name directly.

    Returns:
        The ``tools.splits.Corpus`` for it, or ``None`` when the manifest could
        not be parsed on this interpreter. Callers that need the declaration
        rather than merely preferring it should say so:
        ``corpus = declaration(name); assert corpus is not None``.

    Raises:
        SystemExit: If the manifest parsed and does not declare this corpus.
            That is the rule being enforced, not an accident: a corpus measured
            but never declared is exempt from the train/test rule by omission,
            which is the whole failure ``bench/splits.toml`` exists to prevent.
    """
    manifest = _manifest()
    if manifest is None:
        return None
    module = _splits_module()
    assert module is not None
    target = DECLARED_AS.get(name, name)
    try:
        return manifest.corpus(target)  # type: ignore[attr-defined]
    except module.SplitsError as error:
        raise SystemExit(
            f"corpus {name!r} maps to {target!r}, which bench/splits.toml does not declare.\n"
            f"  {error}\n"
            "Add a [corpora.<name>] table with role, task, licence, licence_url and "
            "licence_read_on before measuring anything on it."
        ) from error


def label_for(name: str) -> str:
    """The label every figure from this corpus must carry, per the manifest.

    A runner that prints "tuning split" in its header is making a claim about
    ``bench/splits.toml``; asking the manifest turns that claim into a lookup.
    """
    corpus = declaration(name)
    if corpus is None:
        return "unlabelled (bench/splits.toml unreadable on this interpreter)"
    return corpus.label()  # type: ignore[attr-defined]


def require_unreserved(name: str, arm: str) -> None:
    """Refuse to open a reserved arm unless this run declared the spend.

    Operating rule 3 made mechanical. ``bench/splits.toml`` reserves individual
    *arms* of corpora -- SDU-22 legal ``train.json`` is allocated to the legend
    flag's precision cost (D-047), SDU-22 scientific ``train.json`` is
    deliberately unallocated, SDU-21 AD ``test.json`` is held for an abstention
    default (D-043). Every one of those was prose until this round, and both
    records say the same thing in their own *How it fails*: nothing refused a
    run against the split, and the guard was that somebody read a note.

    Call this where a reader turns ``(corpus, split)`` into a path. It is a
    no-op for every arm that carries no reservation.

    Args:
        name: A reader registry name or a manifest corpus name.
        arm: The split token about to be opened, e.g. ``"train"``.

    Raises:
        SystemExit: If the arm is reserved and this process has not called
            :func:`declare_spend` for it. That is the only door, and it is in
            this module for the reason that function records.
            ``SystemExit`` rather than the loader's ``SplitsError`` because that
            is what every other refusal in this module raises, and a runner
            should stop with the message rather than a traceback.
    """
    corpus = declaration(name)
    if corpus is None:
        # 3.9/3.10 with no TOML parser. Loud rather than silent, and open rather
        # than closed: the manifest is what says which arms are reserved, so a
        # closed default here would refuse every split of every corpus on those
        # interpreters to protect two files. The hole is real and is recorded
        # with the mechanism rather than discovered later.
        print(
            f"bench.corpora: WARNING -- cannot check reservations on {name}:{arm}; "
            "bench/splits.toml is unreadable on this interpreter. A RESERVED ARM WILL "
            "NOT BE REFUSED ON THIS RUN. Use 3.11+ before spending anything.",
            file=sys.stderr,
        )
        return
    module = _splits_module()
    assert module is not None
    try:
        corpus.require_unreserved(arm)  # type: ignore[attr-defined]
    except module.SplitsError as error:
        raise SystemExit(str(error)) from error


def declare_spend(name: str, arm: str, *, decision: str, purpose: str) -> None:
    """Say, before opening it, that this run is the spend a reservation names.

    **Go through this function and not through ``tools/splits.py`` directly.**
    The ledger of declared spends is module state, and ``tools/splits.py`` is
    imported *by path* here under a private module name -- so a runner that
    imported the loader itself would be writing to a second ledger and would
    still be refused by the reader. One door, so there is one ledger.

    Args:
        name: A reader registry name or a manifest corpus name.
        arm: The split token about to be opened.
        decision: The record that allocates the arm, e.g. ``"D-047"``.
        purpose: One line saying what this run buys. It is printed.

    Raises:
        SystemExit: If the reservation refuses this spend -- an unallocated arm,
            the wrong record, or an empty purpose.
    """
    corpus = declaration(name)
    if corpus is None:
        return
    module = _splits_module()
    assert module is not None
    try:
        corpus.declare_spend(arm, decision=decision, purpose=purpose)  # type: ignore[attr-defined]
    except module.SplitsError as error:
        raise SystemExit(str(error)) from error


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
    """Resolve and check the file backing one split.

    The reservation check runs FIRST, before the unknown-split refusal, and the
    order is the point. ``test`` is not in :data:`_SDU21_AD_FILES` and has no
    fetch entry, so today it is refused as a typo -- an accident that reads like
    a guard. Asking the manifest first means the person who adds the missing
    registry entry gets D-043's reservation, its trigger and its permanent cost,
    instead of discovering that the accident they removed was the only thing
    protecting the project's last blind disambiguation arm.
    """
    require_unreserved("sdu21_ad", split)
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
# SDU@AAAI-22 AE — character-offset span detection over running text
# ---------------------------------------------------------------------------
#
# The project's first corpus that is neither MEDLINE nor PLOS, and the first
# that ships *running text* with character offsets rather than tokens. That
# removes the largest arbitrary choice in the PLOD harness — there is nothing to
# detokenise, so no reconstruction sits inside the number.
#
# Record format, per the README, a JSON list of::
#
#     {"text": "... United Nations Development Programme (UNDP) ...",
#      "acronyms":   [[136, 140]],     <- character offsets
#      "long-forms": [[98, 134]],
#      "ID": "TR-0"}
#
# TWO THINGS THE README SAYS ABOUT THIS FORMAT ARE WRONG, and both are the kind
# of quiet harness bug that moves an F1 without failing anything.
#
# 1. **The offsets are half-open, not inclusive.** The README says each tuple
#    holds "the index of the first and last character". Taken literally that
#    means ``text[start:end + 1]``, and it appends a trailing character to every
#    single span. Measured across all four labelled English splits (14,778 +
#    1,882 + 13,404 + 1,690 = 31,754 gold spans):
#
#        text[start:end]      ends on an alphanumeric   95.8 % - 99.3 %
#        text[start:end + 1]  ends on an alphanumeric    0.7 % -  1.9 %
#
#    and the character sitting at index ``end`` is a space (8,045 times in legal
#    train), a closing bracket (4,657), a comma, a semicolon or a slash. So
#    ``UNDP`` reads as ``UNDP)`` and ``Economic Commission for Latin America and
#    the Caribbean`` gains a trailing space. This reader uses ``text[a:b]``.
#
# 2. **The id key is ``ID``, not ``id``.** The README documents "id: The unique
#    ID of the sample"; the files ship ``"ID"``. The task's own ``scorer.py``
#    reads ``d['ID']``, so the data is right and the prose is wrong.
#
# Neither error can be caught by the official scorer, and that is the point:
# ``scorer.py`` never opens the text. It compares ``"<index>#<start>-<end>"``
# strings between two JSON files, so a reader that misreads the convention
# scores perfectly against itself and mis-scores against everything else. The
# MED1250 record-boundary bug had the same shape.
#
# ROLE. Both splits are declared ``role = "tuning"`` and ``contaminated = true``
# in bench/splits.toml. The August 2026 audit decomposed their *dev* misses by
# legend separator and ranked a recall proposal on the result, which is exactly
# what made MED1250 a tuning split. Only ``train`` is unread.
#
# THE TEST SPLITS ARE UNLABELLED. Both were checked on 2026-08-23: legal/test
# is 446 samples with 0 labels, scientific/test is 498 samples with 0 labels.
# They are deliberately not in the fetch registry, so nothing here can read
# them and mistake an empty gold set for a hard one.

SDU22_AE_DOMAINS = ("legal", "scientific")

#: Splits with labels. ``test`` is excluded on purpose; see above.
SDU22_AE_SPLITS = ("train", "dev")


@dataclass(frozen=True)
class CharSpanDocument:
    """One passage with its annotated spans as character offsets.

    Deliberately neither :class:`GoldDocument` (which promises ``pairs``, and
    this corpus has none) nor :class:`SpanDocument` (whose spans are *token*
    indices over a token list this corpus does not ship). Widening either would
    let a runner consume this corpus and report a number that means nothing,
    which is the trap :func:`read_plod_cw_text` already documents.

    Attributes:
        uid: The corpus-native ``ID``, used as the prediction key exactly as
            the shared task's own scorer does.
        identifier: Same value, kept for display symmetry with the other types.
        text: The passage, as running prose. No reconstruction is involved.
        short_form_spans: Half-open ``(start, end)`` character offsets tagged
            as acronyms.
        long_form_spans: The same for long forms.
    """

    uid: str
    identifier: str
    text: str
    short_form_spans: tuple[tuple[int, int], ...] = field(default_factory=tuple)
    long_form_spans: tuple[tuple[int, int], ...] = field(default_factory=tuple)

    def short_forms(self) -> tuple[str, ...]:
        """The annotated acronym surfaces, sliced with the half-open convention."""
        return tuple(self.text[start:end] for start, end in self.short_form_spans)

    def long_forms(self) -> tuple[str, ...]:
        """The annotated long-form surfaces, sliced with the half-open convention."""
        return tuple(self.text[start:end] for start, end in self.long_form_spans)


def _sdu22_ae_source(path: Optional[Path], domain: str, split: str) -> Path:
    """Resolve and check the file backing one (domain, split).

    **Both ``train`` arms are reserved and this is where that is enforced.**
    Legal train is allocated to the legend flag's precision cost (D-047);
    scientific train is unallocated and its first spend needs its own record.
    Both files are already fetched into ``data/``, so before this check a single
    ``read_sdu22_ae(domain="legal", split="train")`` mined the last unmined arm
    of this corpus silently. It now raises unless the run declared the spend
    through :func:`declare_spend`.
    """
    if domain not in SDU22_AE_DOMAINS:
        raise SystemExit(f"unknown SDU22-AE domain {domain!r}; known: {list(SDU22_AE_DOMAINS)}")
    if split not in SDU22_AE_SPLITS:
        raise SystemExit(
            f"unknown SDU22-AE split {split!r}; known: {list(SDU22_AE_SPLITS)}. "
            "test.json exists upstream and carries ZERO labels (446 and 498 samples, "
            "0 labelled), so it is not registered and cannot be read here."
        )
    require_unreserved(f"sdu22_ae_{domain}", split)
    source = path or (DATA_DIR / f"sdu22_ae_{domain}_{split}.json")
    if not source.is_file():
        raise SystemExit(
            f"missing {source}\nRun: python tools/fetch_data.py sdu22-ae-{domain}-{split}"
        )
    return source


def _sdu22_ae_spans(
    record: dict, key: str, text: str, uid: str, source: Path
) -> tuple[tuple[int, int], ...]:
    """Read one span list, enforcing the half-open convention's own bounds.

    ``0 <= start < end <= len(text)`` is exactly the half-open reading. Under
    the README's literal inclusive reading the last span of a passage ending on
    its annotation would have ``end == len(text)`` and slice one character past
    the string, so this bound is also the assertion that the convention is
    right -- and it holds across all 31,754 gold spans in the four labelled
    English splits.
    """
    out: list[tuple[int, int]] = []
    for pair in record.get(key) or []:
        start, end = int(pair[0]), int(pair[1])
        if not 0 <= start < end <= len(text):
            raise SystemExit(
                f"{source}: sample {uid!r} has {key} span ({start}, {end}) "
                f"outside a {len(text)}-character text"
            )
        out.append((start, end))
    return tuple(out)


def read_sdu22_ae(
    path: Optional[Path] = None, domain: str = "legal", split: str = "dev"
) -> list[CharSpanDocument]:
    """Parse an SDU@AAAI-22 AE English split into span-annotated passages.

    Args:
        path: Override the default ``data/sdu22_ae_<domain>_<split>.json``.
        domain: One of :data:`SDU22_AE_DOMAINS`. ``"legal"`` is the corpus's own
            word and is not a description of the text — see
            ``bench/splits.toml``, ``[corpora.sdu22_ae_legal].domain_finding``.
        split: One of :data:`SDU22_AE_SPLITS`.

    Returns:
        One :class:`CharSpanDocument` per sample, in file order. Unlabelled
        samples (10 in legal train, 1 in legal dev, 1 in scientific train) are
        kept with empty span tuples rather than dropped: they are real passages
        an extractor is scored on, and dropping them would inflate precision.

    Raises:
        SystemExit: For an unknown domain or split, a missing file, or a record
            that is not the shape the format specifies.
    """
    declaration(f"sdu22_ae_{domain}")
    source = _sdu22_ae_source(path, domain, split)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit(
            f"{source} should hold a JSON list of samples, got {type(payload).__name__}"
        )

    documents: list[CharSpanDocument] = []
    for position, record in enumerate(payload):
        text = str(record["text"])
        # "ID", not "id". The README documents the lower-case spelling and the
        # files ship the upper-case one; scorer.py reads d['ID'].
        uid = str(record.get("ID", record.get("id", f"{domain}-{split}-{position}")))
        documents.append(
            CharSpanDocument(
                uid=uid,
                identifier=uid,
                text=text,
                short_form_spans=_sdu22_ae_spans(record, "acronyms", text, uid, source),
                long_form_spans=_sdu22_ae_spans(record, "long-forms", text, uid, source),
            )
        )
    return documents


def sdu22_ae_recall_ceiling(documents: Sequence[CharSpanDocument]) -> dict:
    """Where short-form recall lands for an extractor that emits the annotated definitions.

    This corpus annotates every acronym **occurrence**; acronymkit reports only
    **defined pairs**, and every pair it emits carries exactly one long form. So
    an extractor whose emitted definitions are exactly the annotated ones scores
    ``long_form_spans / short_form_spans`` and no more.

    **It is not a hard bound, and calling it one would be this project's own
    recorded mistake.** ``41.53`` shipped as "the ceiling of the feature set"
    and was exceeded four times in the run that published it. Here the escape
    route is emitting a definition the annotators did not mark: the acronym span
    still counts as a short-form true positive, because the task's scorer scores
    short and long forms separately. On the dev splits, 45.4 % (legal) and
    27.3 % (scientific) of gold acronym spans exceed the definitions their own
    sample records, so the route is wide open.

    The honest statement, and the one to print beside a recall figure: **every
    point above this number is bought by emitting a definition the corpus does
    not annotate, and paid for in long-form precision.**

    It is computed here, from the data, rather than quoted, so the figure
    recorded on the ``bench/splits.toml`` entry is checkable rather than
    asserted. R9.6 requires it to appear in the same table as any recall figure
    from this corpus; this is what produces it.

    Args:
        documents: A parsed split.

    Returns:
        ``{"gold_short_form_spans", "gold_long_form_spans", "ceiling_pct"}``.
    """
    shorts = sum(len(document.short_form_spans) for document in documents)
    longs = sum(len(document.long_form_spans) for document in documents)
    return {
        "gold_short_form_spans": shorts,
        "gold_long_form_spans": longs,
        "ceiling_pct": round(longs / shorts * 100, 2) if shorts else 0.0,
    }


# ---------------------------------------------------------------------------
# SEC XBRL and Socrata — identifier segmentation, and the first task here whose
# gold is not an annotation inside a passage
# ---------------------------------------------------------------------------
#
# Every other corpus in this module annotates something *in a text*. MED1250
# pairs definitions found in an abstract; PLOD and SDU-22 AE label regions of a
# sentence; SDU-21 AD picks a sense for a token in a sentence. All four carry a
# passage and point into it.
#
# This one has no passage. A record is two surface strings — a machine
# identifier and a human caption of the same column — that the admission rule
# guarantees are made of the *same alphanumeric characters*, case-folded. So
# nothing about them can differ except where the words were cut, and the gold is
# a set of integer cut positions in the character stream they share. There is no
# text, no span, no candidate set, and no annotator.
#
# THE GOLD HAS NO ANNOTATOR, AND THAT IS THE POINT. The August 2026 audit's
# first killed finding is a corpus of column names whose annotators were
# *instructed to invent abbreviations*, scored as if it were real schema text
# (docs/AUDIT-2026-08.md section 0). Here nobody was commissioned: the caption is
# production metadata written by the same organisation that wrote the
# identifier — the taxonomy editor or the filing registrant for SEC, the
# publishing agency for Socrata. R9's first question ("what was the annotator
# instructed to produce?") has no annotator to ask.
#
# WHAT THIS MODULE OWNS AND WHAT IT DOES NOT. The admission rule and the cut
# metric live in ``bench/run_governed_gold.py`` and stay there. This reader
# returns the *raw catalog rows*, unfiltered and unscored, because a second
# implementation of the admission rule is a second definition of the gold, and
# two definitions of a gold standard drift silently. What this module owns is
# the **type**: the thing a segmentation corpus is, in a shape no pair reader
# and no span reader can consume.

#: Where ``bench/run_governed_gold.py`` caches what it fetched. Inside the
#: git-ignored ``data/``, like every other fetched evaluation asset.
GOVERNED_GOLD_CACHE = DATA_DIR / "governed_gold"

#: Manifest corpus name -> the cache-file prefix the runner writes it under.
#: A prefix rather than a filename because the runner embeds its pins in the
#: name (``sec_xbrl_2025q1.json``, ``socrata_80pages_v2.json``), and hard-coding
#: those here would make this module quietly disagree with the runner the first
#: time somebody passes ``--quarter``.
GOVERNED_GOLD_PREFIXES = {"sec_xbrl": "sec_xbrl_", "socrata": "socrata_"}


@dataclass(frozen=True)
class IdentifierCaptionPair:
    """One machine identifier beside a human caption of the same characters.

    Deliberately none of the other four types in this module, and the separation
    is stronger than the ones already here. :func:`read_plod_cw_text` documents
    a *soft* trap: it hands back a real :class:`GoldDocument` with ``pairs=()``,
    so a pair runner pointed at it reports a meaningless zero and only the
    gold-pair count gives it away. This type cannot do even that. It has no
    ``text`` and no ``tokens``, so a pair or span consumer pointed at it dies on
    an :class:`AttributeError` rather than producing a number — and a crash is a
    better failure than a plausible figure.

    Attributes:
        identifier: The machine name as published, e.g. ``"_2013_q1_actual"``.
        caption: The human caption as published, e.g. ``"2013 Q1 Actual"``.
            Where the pair is admitted as gold, its alphanumerics case-fold
            equal to the identifier's.
        author: Who wrote the caption. This is an *arm*, never a split, and it
            must not be pooled: ``us_gaap``, ``ifrs`` and ``filer_extension``
            come out of one SEC file and one scorer, and us-gaap and IFRS are
            twelve points apart because the two taxonomies apply the LC3 naming
            convention differently. For Socrata it is the publishing portal.
    """

    identifier: str
    caption: str
    author: str


@dataclass(frozen=True)
class SegmentationCorpus:
    """A fetched identifier/caption population, with the provenance that names it.

    A container rather than a bare list, which is a deliberate asymmetry with
    every other reader here, and the reason is Socrata: **the catalog is live
    and re-orders under the scroll**, so the population is defined by *when* it
    was fetched. A reader that returned rows alone would hand back a corpus
    nobody could identify, and "91.37 % on Socrata" would name a different
    population every quarter with nothing visible to say so.

    It also means the return value is not iterable as documents, so
    ``for document in ...`` — the idiom every other corpus in this module is
    consumed by — fails immediately rather than half-working.

    Attributes:
        name: The manifest corpus name, ``"sec_xbrl"`` or ``"socrata"``.
        source: The cache file actually read, by name, so a report can say which
            snapshot produced it.
        fetched_on: The ISO date the runner fetched it, carried through from the
            cache envelope.
        pairs: Every row in the cache, raw. **Not** the scored population: the
            admission rule that turns these into gold lives in
            ``bench/run_governed_gold.py`` and is not re-implemented here.
    """

    name: str
    source: str
    fetched_on: str
    pairs: tuple[IdentifierCaptionPair, ...] = field(default_factory=tuple)


def _governed_gold_source(name: str, path: Optional[Path]) -> Path:
    """Resolve the cache file backing one segmentation corpus.

    Raises:
        SystemExit: If nothing is cached, or if *several* snapshots are — the
            second case on purpose. Two Socrata caches on one disk are two
            different populations of a live catalog, and choosing between them
            silently would put the choice of which corpus was measured inside a
            number. The caller is told to name one.
    """
    if path is not None:
        source = Path(path)
        if not source.is_file():
            raise SystemExit(f"missing {source}")
        return source
    if name not in GOVERNED_GOLD_PREFIXES:
        raise SystemExit(
            f"unknown segmentation corpus {name!r}; known: {sorted(GOVERNED_GOLD_PREFIXES)}"
        )
    candidates = sorted(GOVERNED_GOLD_CACHE.glob(f"{GOVERNED_GOLD_PREFIXES[name]}*.json"))
    if not candidates:
        raise SystemExit(
            f"no cached {name} snapshot under {GOVERNED_GOLD_CACHE}\n"
            "Run: python bench/run_governed_gold.py --only " + name
        )
    if len(candidates) > 1:
        listed = ", ".join(candidate.name for candidate in candidates)
        raise SystemExit(
            f"{len(candidates)} cached {name} snapshots: {listed}\n"
            "These are different populations, not different files -- the SEC quarter and the "
            "live Socrata catalog both move. Pass path= to say which one is being read; "
            "picking the newest would put that choice inside the number."
        )
    return candidates[0]


def read_governed_gold(name: str, path: Optional[Path] = None) -> SegmentationCorpus:
    """Load one identifier/caption population from the runner's cache.

    Args:
        name: ``"sec_xbrl"`` or ``"socrata"`` — a manifest corpus name.
        path: An explicit cache file, required when more than one snapshot of
            the same corpus is on disk.

    Returns:
        The population, raw and unscored. Filtering it to gold is the runner's
        job and is not duplicated here; see the section comment above.

    Raises:
        SystemExit: If the corpus is undeclared, if the manifest declares it
            under a different task, or if the cache is missing or ambiguous.
    """
    corpus = declaration(name)
    if corpus is not None:
        # The claim "this is a segmentation corpus" is made by every caller of
        # this function. ``require_task`` turns it into a lookup, which is what
        # ``require_role`` already does for the tuning/held-out claim.
        corpus.require_task("identifier_segmentation")  # type: ignore[attr-defined]
    source = _governed_gold_source(name, path)
    envelope = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(envelope, dict) or not isinstance(envelope.get("payload"), list):
        raise SystemExit(
            f"{source} is not a run_governed_gold cache envelope "
            '({"fetched_on": ..., "payload": [[identifier, caption, author], ...]})'
        )
    pairs = tuple(
        IdentifierCaptionPair(
            identifier=str(row[0]),
            caption=str(row[1]),
            author=str(row[2]) if len(row) > 2 else "",
        )
        for row in envelope["payload"]
        if isinstance(row, list) and len(row) >= 2
    )
    return SegmentationCorpus(
        name=name,
        source=source.name,
        fetched_on=str(envelope.get("fetched_on") or "unknown"),
        pairs=pairs,
    )


# ---------------------------------------------------------------------------
# the Federal Register reference set (W10)
# ---------------------------------------------------------------------------
#
# ``headline_capable("extraction")`` returns empty and D-048 established that
# this is a fact rather than a vocabulary artifact: an extraction gold record
# asserts an EDGE, span gold asserts unlinked vertices, and neither derives from
# the other. ``tools/build_gold_corpus.py`` builds the corpus that would close
# it, out of public-domain Federal Register rules.
#
# What lands here is the reader, and it is deliberately **not in any registry**.
# The corpus it reads is adjudicated by one person, and that person is the author
# of the extractor it would be used to score. There is no role in
# ``tools/splits.py`` that says so -- ``ROLES`` is ``("tuning", "held_out")`` --
# and filing it under either would be a lie in a different direction:
# ``held_out`` makes it headline-eligible through ``Manifest.headline_capable``,
# which is exactly what a self-adjudicated set must never be, and ``tuning``
# claims something was fitted to it when nothing was.
#
# So the reader exists, refuses to produce a corpus until the manifest declares
# one, and the honest role is reported rather than approximated. See
# :data:`UNREGISTERED_READERS`.

#: Where ``tools/build_gold_corpus.py`` writes its frozen artifact. Inside the
#: git-ignored ``data/``, like every other fetched evaluation asset.
FEDERAL_REGISTER_CACHE = DATA_DIR / "federal_register"

#: The ``[corpora.<name>]`` table this reader would draw from. It does not exist
#: yet, on purpose: ``bench/splits.toml`` is not this workstream's file, and the
#: entry it needs declares a role the validator would reject today.
FEDERAL_REGISTER_CORPUS = "federal_register_rules_2024q1"

#: Readers that exist and are deliberately absent from every registry, with the
#: reason each one is held back.
#:
#: This is a set for the same reason :data:`TEXT_ONLY_VIEWS` is a set: the
#: alternative is a paragraph, and ``tests/test_splits_manifest.py`` cannot
#: consult a paragraph. An entry here is a promise that the omission is
#: deliberate and that the manifest gap is the thing blocking it -- so when the
#: entry lands, the test that reads this constant is what says the exemption is
#: no longer describing anything.
UNREGISTERED_READERS = {
    FEDERAL_REGISTER_CORPUS: (
        "single-annotator reference set adjudicated by the author of the extractor it "
        "would score; tools/splits.py ROLES cannot express that, and neither 'tuning' "
        "nor 'held_out' is true of it"
    ),
}


@dataclass(frozen=True)
class ReferenceSet:
    """An adjudicated pair corpus that is **not** a gold standard, and says so.

    A sixth container, and the separation is about provenance rather than about
    type: its ``documents`` really are :class:`GoldDocument` objects and a pair
    scorer could consume them tomorrow. That is precisely why the type exists.
    :class:`SegmentationCorpus` protects against a consumer of the wrong *shape*;
    this protects against a consumer of the wrong *standing*, which is the
    quieter failure -- nothing would crash, a table would simply be published
    against a corpus one interested party decided the answers to.

    So the documents are reachable only through
    :meth:`documents_for_scoring`, which states what it is handing over, and
    :meth:`require_headline_eligible` refuses outright while the adjudicator
    count is one. ``bench/splits.toml``'s own rule is the authority here: *a gold
    standard I partly invented cannot adjudicate my own system.*

    Attributes:
        name: The manifest corpus name this would be declared under.
        source: The frozen artifact actually read, by name.
        frozen_on: ISO date the split was frozen. A freeze that happened *after*
            the tuning it adjudicates is not a freeze, so the date is carried
            with the corpus rather than in a commit message.
        adjudicators: Who decided. Empty is refused at read time.
        artifact_kind: The artifact's own description of itself.
        domain: What the text is. Federal Register rulemaking is one more
            domain, not general text, and this string travels with every figure.
        licence: As read from terms.
        documents: The adjudicated pairs, per document.
        provenance: The rest of the envelope -- selection, pins, pooling recipe,
            stratum populations and the pilot report -- carried through whole so
            a consumer never has to re-open the artifact to say where it came
            from.
    """

    name: str
    source: str
    frozen_on: str
    adjudicators: tuple[str, ...]
    artifact_kind: str
    domain: str
    licence: str
    documents: tuple[GoldDocument, ...] = field(default_factory=tuple)
    exhaustive: tuple[str, ...] = field(default_factory=tuple)
    provenance: dict = field(default_factory=dict)

    @property
    def adjudicator_count(self) -> int:
        """How many people decided. One is a reference set; two may be a gold standard."""
        return len(self.adjudicators)

    @property
    def is_gold_standard(self) -> bool:
        """Never true on one adjudicator, and not automatic on two.

        Two adjudicators are *necessary* and not sufficient: their agreement has
        to be computed and published first. This property answers the necessary
        half only, which is why :meth:`require_headline_eligible` raises with the
        remaining condition spelled out rather than returning this value.
        """
        return self.adjudicator_count >= 2

    def label(self) -> str:
        """The label every figure from this corpus must carry."""
        return (
            f"{self.artifact_kind}, {self.adjudicator_count} adjudicator(s), "
            f"frozen {self.frozen_on}, domain: Federal Register rulemaking"
        )

    def require_headline_eligible(self) -> None:
        """Refuse to back a headline number.

        Raises:
            SystemExit: Always, while one person adjudicated. The message names
                the two things that would have to change, because "not eligible"
                without them reads as a permanent verdict when it is a list of
                unmet conditions.
        """
        if not self.is_gold_standard:
            raise SystemExit(
                f"{self.name} is a {self.artifact_kind} with "
                f"{self.adjudicator_count} adjudicator(s): "
                f"{', '.join(self.adjudicators) or 'none recorded'}.\n"
                "It may not back a headline number. Two things would have to change:\n"
                "  1. a second, independent adjudicator, not an author of the systems pooled\n"
                "  2. their agreement computed and published beside the corpus\n"
                "See bench/splits.toml: a gold standard I partly invented cannot adjudicate "
                "my own system."
            )
        raise SystemExit(  # pragma: no cover - needs two adjudicators
            f"{self.name} has {self.adjudicator_count} adjudicators but no published "
            "agreement statistic. Compute and publish it before quoting a headline."
        )

    def documents_for_scoring(self) -> tuple[GoldDocument, ...]:
        """The documents this corpus may legitimately be scored against.

        Named at length on purpose. The attribute could simply have been public;
        a call whose name says "for scoring" is what a reader trips over when
        they are about to publish the result. It also enforces the two conditions
        a frozen artifact can silently fail, both of which produce a plausible
        number rather than an error:

        **Exhaustiveness.** A pilot adjudicates a *sample*, so a document's pair
        list holds the sampled candidates that adjudicated as definitions and not
        every definition in the document. Scoring against a partial annotation is
        wrong in both directions at once -- recall is undefined because the
        denominator is unknown, and precision is understated because a correct
        pair that was never sampled counts as a false positive. Only documents
        the artifact lists as exhaustively annotated are returned.

        **Text.** ``extraction`` gold is a passage plus the pairs annotated in
        it. A ``GoldDocument`` with an empty ``text`` hands every extractor an
        empty string, which yields no predictions and scores as total recall
        failure -- the exact shape of quiet wrongness ``read_plod_cw_text``
        documents for its own trap.

        Returns:
            The exhaustively annotated documents, each carrying its text.

        Raises:
            SystemExit: If no document is exhaustively annotated, or if any
                returned document has no text.
        """
        usable = tuple(document for document in self.documents if document.uid in self.exhaustive)
        if not usable:
            raise SystemExit(
                f"{self.name} has no exhaustively annotated document, so it cannot be "
                "scored against.\n"
                f"  {self.provenance.get('scorable_note', '')}\n"
                "A pilot produces none by construction: adjudicate every pooled candidate "
                "belonging to a document before that document can carry a metric."
            )
        textless = [document.uid for document in usable if not document.text]
        if textless:
            raise SystemExit(
                f"{self.name}: {len(textless)} document(s) carry no text "
                f"({', '.join(textless[:5])}). extraction gold is a passage plus the pairs "
                "annotated in it; an empty passage yields no predictions and scores as "
                "total recall failure.\n"
                "Run: python tools/build_gold_corpus.py fetch"
            )
        return usable


def _reference_bodies(envelope: dict, directory: Path) -> dict:
    """Cached document texts, keyed by document number, verified against the pins.

    The envelope carries the pin table, so this needs no second copy of it. Each
    cached body is checked against the digest the artifact was frozen with, and a
    body that fails is dropped rather than returned: a corpus scored against text
    that has drifted under its pin produces a number nothing would record the
    cause of.

    The digest is over the normalised text and not over the fetched bytes -- see
    ``tools/build_gold_corpus.py`` for the measurement that forced that, which is
    that both hosts rewrite e-mail addresses per response.
    """
    bodies: dict = {}
    for pin in envelope.get("documents") or []:
        if not isinstance(pin, dict):
            continue
        number = str(pin.get("document_number", ""))
        cached = directory / f"{number}.txt"
        if not number or not cached.is_file():
            continue
        text = cached.read_text(encoding="utf-8")
        expected = str(pin.get("text_sha256", ""))
        if expected and hashlib.sha256(text.encode("utf-8")).hexdigest() != expected:
            continue
        bodies[number] = text
    return bodies


def parse_reference_set(
    name: str, source: str, envelope: dict, bodies: Optional[dict] = None
) -> ReferenceSet:
    """Build a :class:`ReferenceSet` from a frozen artifact's envelope.

    Split out from :func:`read_federal_register_reference` so the parse is
    testable without a manifest entry the repository does not yet have. The
    reader is the half that enforces governance; this is the half that reads
    JSON, and mixing them would make the governance check untestable or the
    parse unreachable.

    Args:
        name: Manifest corpus name.
        source: File name, for reporting.
        envelope: The parsed artifact.

    Returns:
        The reference set.

    Raises:
        SystemExit: If the envelope is not one of these artifacts, if it records
            no adjudicator, or if it claims to be a gold standard while carrying
            fewer than two. The last check is the one that matters: the artifact
            is written by a tool in this repository, and a field a tool writes is
            a field a later tool can be told to write differently.
    """
    if not isinstance(envelope, dict) or not isinstance(envelope.get("payload"), dict):
        raise SystemExit(
            f"{source} is not a build_gold_corpus freeze envelope "
            '({"adjudicators": [...], "payload": {document: [[short, long], ...]}})'
        )
    adjudicators = tuple(str(person) for person in envelope.get("adjudicators") or ())
    if not adjudicators:
        raise SystemExit(
            f"{source} records no adjudicator. Who decided is part of what this artifact "
            "claims; an unattributed corpus is one nobody can weigh."
        )
    if envelope.get("is_gold_standard") and len(adjudicators) < 2:
        raise SystemExit(
            f"{source} claims is_gold_standard with {len(adjudicators)} adjudicator(s). "
            "Refusing to read it: the claim and the evidence in the same file disagree."
        )
    supplied = bodies or {}
    documents = tuple(
        GoldDocument(
            uid=str(document),
            identifier=str(document),
            text=str(supplied.get(str(document), "")),
            pairs=tuple(
                GoldPair(short_form=str(row[0]), long_form=str(row[1]))
                for row in rows
                if isinstance(row, list) and len(row) >= 2
            ),
        )
        for document, rows in sorted(envelope["payload"].items())
    )
    return ReferenceSet(
        name=name,
        source=source,
        frozen_on=str(envelope.get("frozen_on") or "unknown"),
        adjudicators=adjudicators,
        artifact_kind=str(envelope.get("artifact_kind") or "unlabelled artifact"),
        domain=str(envelope.get("domain") or ""),
        licence=str(envelope.get("licence") or ""),
        documents=documents,
        exhaustive=tuple(
            str(document) for document in envelope.get("exhaustively_annotated_documents") or ()
        ),
        provenance={
            key: value for key, value in envelope.items() if key not in ("payload", "adjudicators")
        },
    )


def read_federal_register_reference(path: Optional[Path] = None) -> ReferenceSet:
    """Load the frozen Federal Register reference set.

    This **will raise today**, and that is the design rather than a gap. The
    corpus is not declared in ``bench/splits.toml``, :func:`declaration` refuses
    an undeclared corpus, and the refusal is the manifest doing the job it exists
    to do: a corpus that is measured but never declared is exempt from the
    train/test rule by omission.

    The entry it needs cannot be written yet either, and the reason is in
    :data:`UNREGISTERED_READERS`. That is the finding this reader carries, and it
    is more useful in the repository than a reader that quietly filed a
    self-adjudicated corpus as ``held_out`` to make an import work.

    Args:
        path: An explicit artifact, so the parse can be exercised against a
            fixture. The declaration check runs either way; passing a path is not
            a way around it.

    Returns:
        The reference set.

    Raises:
        SystemExit: If the corpus is undeclared, if the artifact is missing, or
            if the envelope fails :func:`parse_reference_set`.
    """
    declaration(FEDERAL_REGISTER_CORPUS)
    source = Path(path) if path is not None else FEDERAL_REGISTER_CACHE / "reference_set.json"
    if not source.is_file():
        raise SystemExit(
            f"missing {source}\n"
            "Run: python tools/build_gold_corpus.py fetch && "
            "python tools/build_gold_corpus.py pool --interpreter <python-with-a-baseline>"
        )
    envelope = json.loads(source.read_text(encoding="utf-8"))
    return parse_reference_set(
        FEDERAL_REGISTER_CORPUS,
        source.name,
        envelope,
        bodies=_reference_bodies(envelope, source.parent / "bodies"),
    )


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------
READERS: dict[str, Callable[[], list[GoldDocument]]] = {"med1250": read_med1250}

_TEXT_ONLY: set[str] = set()

#: Text-only views of PLOD-CW, registered so ``bench/external.py`` can load the
#: same reconstructed strings under a foreign interpreter. They hold no pairs;
#: see :func:`read_plod_cw_text` for why that is a trap worth naming.
for _split in ("test", "all"):
    for _style in DETOKENISE_STYLES:
        _suffix = "" if _style == "tight" else f"_{_style}"
        _key = f"plod_cw_{_split}{_suffix}"
        READERS[_key] = functools.partial(read_plod_cw_text, split=_split, style=_style)
        _TEXT_ONLY.add(_key)

#: The keys in :data:`READERS` that are **not** pair corpora, enumerated.
#:
#: This is the one place in this module where the registry's *type* and the
#: manifest's *task* legitimately disagree: ``plod`` is declared
#: ``span_detection``, and these four keys return :class:`GoldDocument` anyway
#: because ``bench/external.py`` needs text-bearing documents to hand a foreign
#: interpreter. Every one carries ``pairs=()`` by construction.
#:
#: It is a set rather than a paragraph because it was a paragraph.
#: :func:`read_plod_cw_text` has warned since it was written that scoring a pair
#: extractor against these is meaningless by construction -- and a warning in
#: prose is not something a check can consult, so nothing distinguished this
#: deliberate exception from an accidental mis-filing. Adding a fifth entry to
#: ``READERS`` for a corpus declared under another task now fails
#: ``tests/test_splits_manifest.py`` unless it is named here on purpose.
TEXT_ONLY_VIEWS = frozenset(_TEXT_ONLY)

#: Disambiguation corpora are kept in their own registry because they return a
#: different type. ``load()`` promises GoldDocument objects and must keep doing
#: so; silently widening it would break the property the scorer relies on.
DISAMBIGUATION_READERS = {"sdu21_ad": read_sdu21_ad}

#: Span-detection corpora, for the same reason: they return SpanDocument, which
#: has spans and no pairs.
SPAN_READERS = {"plod_cw": read_plod_cw}

#: Character-offset span corpora. A fourth registry rather than a widening of
#: :data:`SPAN_READERS`, because ``CharSpanDocument`` carries offsets into real
#: text while ``SpanDocument`` carries token indices into a token list. Mixing
#: them would let a consumer index one with the other's numbers.
#:
#: Keyed per *domain* rather than by a single ``sdu22_ae`` family name, so every
#: key in every registry here is a name :data:`DECLARED_AS` resolves. A family
#: key would have been the one entry in this module for which ``label_for`` had
#: no answer — and a corpus whose role cannot be looked up is the exact gap the
#: manifest exists to close.
CHAR_SPAN_READERS = {
    "sdu22_ae_legal": functools.partial(read_sdu22_ae, domain="legal"),
    "sdu22_ae_scientific": functools.partial(read_sdu22_ae, domain="scientific"),
}

#: Identifier-segmentation corpora. A fifth registry, and the strongest
#: separation of the five: these do not return a list at all, they return a
#: :class:`SegmentationCorpus`, because for a live catalog the fetch date is
#: part of the corpus's identity. Nothing that iterates documents can consume
#: one by accident.
SEGMENTATION_READERS = {
    "sec_xbrl": functools.partial(read_governed_gold, "sec_xbrl"),
    "socrata": functools.partial(read_governed_gold, "socrata"),
}

#: The type contract, written down: which registries may hold a corpus declared
#: for each ``tools/splits.py`` task.
#:
#: ``TASKS`` in ``tools/splits.py`` is a closed vocabulary *because this module
#: returns a different type per task* — that sentence has been in both files for
#: months as prose, and nothing checked it. Nothing stopped a corpus declared
#: ``task = "disambiguation"`` from being registered in ``SPAN_READERS``, which
#: is precisely the mis-filing the closed vocabulary is supposed to prevent.
#: ``tests/test_splits_manifest.py`` walks every registry key through
#: :data:`DECLARED_AS` into the manifest and asserts the declared task matches
#: the registry it is registered in.
#:
#: ``span_detection`` maps to two registries and that is not a wrinkle to
#: tidy away: ``SpanDocument`` carries *token indices* into a token list and
#: ``CharSpanDocument`` carries *character offsets* into running text. They are
#: the same task over two annotation units, and indexing one with the other's
#: numbers is the reason they are separate types in the first place. So the
#: mapping is task -> registries, plural, rather than a bijection nobody could
#: honestly claim.
TASK_REGISTRIES = {
    "extraction": ("READERS",),
    "span_detection": ("SPAN_READERS", "CHAR_SPAN_READERS"),
    "disambiguation": ("DISAMBIGUATION_READERS",),
    "identifier_segmentation": ("SEGMENTATION_READERS",),
}


def load(name: str) -> list[GoldDocument]:
    """Load a corpus by registry name, after checking it is declared.

    The declaration lookup is not a formality. ``bench/splits.toml`` is where a
    corpus says whether its figures are tuning figures and whether its licence
    permits anything beyond measurement, and for months nothing read it. Doing
    the lookup *here* means the rule is checked at the moment the corpus is
    opened, which is the last point before a number exists.

    Args:
        name: Key in :data:`READERS`.

    Returns:
        The normalised documents.

    Raises:
        SystemExit: For an unknown corpus name, for a corpus registered under a
            different task, or for a corpus that ``bench/splits.toml`` does not
            declare.
    """
    if name not in READERS:
        # "unknown corpus" reads like a typo, and for a corpus that exists but
        # holds a different *shape* of gold that message sends the caller
        # looking for a spelling mistake. Say which registry has it, and what
        # its records are, so the answer is "wrong runner" rather than "wrong
        # word".
        for registry_name, registry in (
            ("DISAMBIGUATION_READERS", DISAMBIGUATION_READERS),
            ("SPAN_READERS", SPAN_READERS),
            ("CHAR_SPAN_READERS", CHAR_SPAN_READERS),
            ("SEGMENTATION_READERS", SEGMENTATION_READERS),
        ):
            if name in registry:
                raise SystemExit(
                    f"{name!r} is registered in {registry_name}, not in READERS. "
                    f"load() promises GoldDocument objects -- a passage plus the pairs a "
                    f"human annotated in it -- and {name!r} holds a different type of gold. "
                    "Call its reader directly; widening load() would let a pair scorer "
                    "consume it and report a number that means nothing."
                )
        raise SystemExit(f"unknown corpus {name!r}; known: {sorted(READERS)}")
    declaration(name)
    return READERS[name]()


def iter_pairs(documents: list[GoldDocument]) -> Iterator[GoldPair]:
    """Yield every gold pair across ``documents``."""
    for document in documents:
        yield from document.pairs
