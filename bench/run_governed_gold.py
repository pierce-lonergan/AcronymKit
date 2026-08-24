#!/usr/bin/env python3
"""Accuracy for the governed subsystem, against gold written by the people who own the schemas.

Why this runner exists
----------------------
The governed half of this package is 9,370 of 25,210 source lines and until now
carried no accuracy number at all. The justification on file was that it is
"exact by construction", which is a tautology rather than a measurement: a
lookup table is exact about whatever the caller put in it, and that says nothing
about the one thing in the subsystem that decides anything on its own.

That one thing is :func:`~acronymkit.governed.tokenizer.split_identifier`. Its
own docstring says so -- "the only function here that decides anything on its
own ... A boundary placed in the wrong character position produces a token no
catalog contains, and no amount of governed vocabulary downstream can recover
the word that was cut in half." So the accuracy question for this subsystem is
exactly: **does it cut identifiers where the people who named them cut them?**

The gold, and the rule that makes it defensible
-----------------------------------------------
Two public sources publish, for the same column, a machine identifier *and* a
human caption written by the same organisation. That caption is the gold. It is
not an annotation commissioned for a benchmark, which is the point: nobody was
instructed to produce it, so nobody could be instructed to produce it wrongly.
(The August 2026 audit's first killed finding is the counter-example: a corpus
of column names whose annotators were instructed to *invent* abbreviations, then
scored as if it were real schema text. See ``docs/AUDIT-2026-08.md`` section 0.)

A caption is admitted as gold only when both hold:

1. its alphanumeric characters, case-folded, **equal** the identifier's; and
2. it contains whitespace.

Rule 1 throws away every pair where the caption expands, abbreviates,
reorders, or annotates -- ``qty`` / ``Quantity Ordered`` is discarded, because
scoring it would be scoring expansion, which is the catalog's job and not the
splitter's. Rule 2 throws away pairs that carry no cut at all. What survives is
a population where the caption and the identifier are the same characters and
**only cut placement can differ**, so a disagreement is a segmentation
disagreement and nothing else. That is the whole design: the admission rule is
what turns a noisy field into a single-variable experiment.

It also means the gold is *small and biased on purpose*. Roughly 87 % of real
Socrata field/caption pairs are already unabbreviated, and this rule keeps a
subset of those. It is not a sample of schema columns; it is a sample of
schema columns whose caption can adjudicate a cut.

Rule 2 is taken literally in both directions, and both consequences are
disclosed rather than patched around after seeing the data.

*It admits captions with no cut.* ``Total (#)`` has whitespace, one
alphanumeric word and zero cuts. Such a pair still adjudicates -- it asserts
that no cut belongs inside ``total`` -- but it is an easier assertion than a
four-word one, so every arm is broken down by caption word count and the
one-word bucket is visible there rather than folded into the headline.

*It refuses captions cut only by punctuation.* ``Available-for-Sale`` places
two cuts and carries no whitespace, so it is thrown away. Widening rule 2 to
"contains a cut" would admit it and would raise the SEC numbers, which is
exactly why the rule is left as specified: a rule loosened after seeing which
direction it moves the result is not a rule.

What is scored
--------------
``expand_identifier(identifier, GovernedDictionary({}))``. The public entry
point, through the shipped code path, with an **empty** catalog -- and the empty
catalog is forced by the admission rule rather than chosen for convenience. A
populated catalog would rewrite ``TXN`` to ``Transaction``, which changes the
character stream, and the metric is defined on a shared character stream. So
what is measured here is cut placement as delivered by the public API, and
*not* catalog resolution, class-word detection, compliance or naming. Those are
lookups against data the caller supplies; this is the judgement the package
makes on its own.

Two metrics, on the alphanumeric character stream both strings share:

``exact``
    The predicted cut set equals the gold cut set. Whole-identifier, all or
    nothing, which is the granularity a governance pipeline consumes.

``boundary P / R / F1``
    Per-cut. A cut is a position in the shared character stream. Punctuation
    inside the caption counts as a cut, not only whitespace: ``Available-for-Sale``
    is three words, because ``-`` is a separator under the splitter's own rule 2
    and pretending otherwise would score a hyphen as an error.

The ceiling, printed in the same table
--------------------------------------
An identifier either marks a cut or it does not. ``END_DATE`` marks one;
``enddate`` marks nothing, and no procedure that refuses to guess can recover
it. So every table here also carries **boundary recall ceiling**: the share of
gold cuts that sit at a position the identifier itself marks, under the four
conventions the splitter reads -- a separator, a lower-to-upper case change, a
letter-to-digit change, or the end of a capital run. A recall figure quoted
without that bound is unreadable, and this project has published a
recall-ceiling artifact before (``bench/splits.toml``,
``shortform_recall_ceiling_pct``).

Decomposed, never pooled
------------------------
Every arm reports ``marked`` (the identifier carries at least one separator or
case change) beside ``unmarked`` (it carries none), and the unmarked row is
where the number is bad. It is published anyway and beside the headline,
because it is the honest price of a subsystem whose thesis is that it refuses to
guess. Identifier shape is reported too, and it is the load-bearing caveat:
this gold holds no UPPER_SNAKE identifier at all and barely any dotted one, so
nothing here transfers to a schema written that way. A shape with a zero beside
it in ``identifier_shapes`` is a shape the measurement is silent about, and a
counted zero is a stronger caveat than a hedge in prose.

The SEC gold is the identifier's own source, and that changes what it means
--------------------------------------------------------------------------
XBRL element names are written by the LC3 convention -- Label CamelCase
Concatenation -- under which the element name **is** the standard label with
its spaces and punctuation removed and each word capitalised. FRTA states it as
"element names MUST be based on an appropriate presentation label for the
element", and notes that LC3 has no formal specification, so each taxonomy
applies it its own way.

That is not the NameGuess failure the audit killed: the tag is a real
identifier in production use and the label is the real caption beside it, so
both halves of the pair are things that exist. But it does mean the SEC arms
measure **inverting a documented, mechanical name-generation rule**, which is
easier than segmenting an identifier somebody typed. Quote the SEC figures as
that, never as "accuracy on schema identifiers".

It also predicts, and the run confirms, where the two SEC taxonomies part
company. ``us-gaap`` capitalises after stripping a hyphen, so ``Paid-in``
becomes ``PaidIn`` and the cut survives; the IFRS taxonomy does not, so
``paid-in`` becomes ``Paidin`` and the cut is destroyed by the naming rule
before this package ever sees the string. Same corpus, same fetch, same
scorer, twelve points apart -- which is why they are two arms and not one.

Sources, endpoints and licences
-------------------------------
Both are fetched by this runner, so anyone with a network connection can
re-derive the table. Licences read from the terms, with the URL and the read
date, per operating rule 4 -- never from a badge.

``sec_xbrl``
    SEC DERA *Financial Statement Data Sets*, member ``tag.txt`` of the
    quarterly archive, columns ``tag`` and ``tlabel``. Fetched with HTTP range
    requests against the ZIP central directory, so a 122 MB archive costs about
    3.4 MB on the wire. Three arms, because they have three different authors:
    ``us_gaap`` and ``ifrs`` labels come from the respective taxonomy editors,
    and ``filer_extension`` labels are written by the filing registrant.

``socrata``
    The Socrata Discovery API catalog, fields ``columns_field_name`` and
    ``columns_name``, paged by ``scroll_id``. Captions are written by the
    publishing agency of each portal.

Neither corpus was used to tune anything, and this runner tunes nothing: it has
no thresholds, no configuration and no arms to choose between. It reports the
shipped code path once.

Usage::

    python bench/run_governed_gold.py                 # report, record nothing
    python bench/run_governed_gold.py --save          # record into bench/results.json
    python bench/run_governed_gold.py --only socrata  # one corpus
    python bench/run_governed_gold.py --refresh       # re-fetch, ignoring the cache

Set ``ACRONYMKIT_SEC_CONTACT`` to a real mailbox before a heavy or repeated run:
the SEC's access policy asks a caller to declare one, and the default here names
the project rather than the person, because a benchmark must not put somebody's
address into a third party's request log just because the code knew it.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _datetime
import hashlib
import importlib.util
import io
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit.governed import GovernedDictionary, expand_identifier  # noqa: E402

#: Where fetched payloads are cached. Inside the git-ignored ``data/``, like
#: every other fetched evaluation asset; nothing here is committed or packaged.
CACHE_DIR = REPO_ROOT / "data" / "governed_gold"

#: The quarter of the SEC archive to read. Pinned, because the population
#: changes every quarter and an unpinned default would make two runs of this
#: file report different numbers with no visible cause.
SEC_QUARTER = "2025q1"

#: Socrata catalog pages to walk, 100 datasets each. Pinned for the same reason,
#: with the same caveat: the live catalog moves under it, so this bounds the
#: work rather than freezing the corpus. See ``re-derivability`` in the report.
SOCRATA_PAGES = 80

SEC_URL_TEMPLATE = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/{quarter}.zip"
SOCRATA_URL = "https://api.us.socrata.com/api/catalog/v1?only=dataset&limit=100"

#: SEC's access policy requires a declared User-Agent naming the requester, and
#: answers an undeclared request with 403. The default names the project and a
#: project mailbox, and deliberately says nothing about whoever is running the
#: benchmark -- a runner must not put a person's address into a third party's
#: request log because the code happened to know it. Set
#: ``ACRONYMKIT_SEC_CONTACT`` to declare a real contact, which is what the SEC
#: is asking for and what a heavy or repeated run should do.
SEC_USER_AGENT = "acronymkit benchmark harness ({contact})".format(
    contact=os.environ.get("ACRONYMKIT_SEC_CONTACT", "acronymkit-bench@example.invalid")
)
SOCRATA_USER_AGENT = "acronymkit-bench (https://github.com/pierce-lonergan/AcronymKit)"

#: Licence findings, read from the terms on the dates given, and quoted rather
#: than summarised. Operating rule 4: a badge, a footer, or an API's licence
#: *guess* is not a licence for the thing being fetched. Both entries record
#: what the terms actually say, including where they say nothing -- and in the
#: Socrata case, where the only licence statement in sight covers a different
#: artifact from the one being read.
LICENCES = {
    "sec_xbrl": {
        "licence": (
            'sec.gov terms, "Website Dissemination": "Information presented on sec.gov is '
            "considered public information and may be copied or further distributed by users "
            "of the web site without the SEC's permission. Please consider appropriate "
            "citation to the SEC as the source.\" The archive's own readme.htm carries no "
            "copyright, licence, or terms statement at all. CAVEAT that stops this being a "
            "clean grant: the SEC cannot license text it does not own, and it does not own "
            'these labels -- readme.htm section 5.2 says tlabel is "the label text provided '
            'by the taxonomy" for a standard tag and "the text provided by the filer" '
            "otherwise, so us-gaap labels are FASB's and ifrs labels are the IFRS "
            "Foundation's. Benchmark use only. Not vendorable."
        ),
        "licence_url": "https://www.sec.gov/privacy",
        "licence_read_on": "2026-08-23",
    },
    "socrata": {
        "licence": (
            "No licence covers the catalog metadata. The Discovery API indexes third-party "
            "portals, and each dataset carries terms set by its publishing agency; the "
            "catalog is an index over those, not a work with a licence of its own. The one "
            'licence statement on the developer site -- "Licensed by Tyler Technologies '
            'under CC BY-NC-SA 3.0", in the footer of dev.socrata.com -- covers the '
            "DOCUMENTATION, not the API responses, and reading it as the data's licence "
            "would be exactly the badge mistake operating rule 4 exists to stop. Only "
            "column metadata (field name and caption) is read here, never dataset rows. "
            "Benchmark use only. Not vendorable."
        ),
        "licence_url": "https://dev.socrata.com/docs/other/discovery",
        "licence_read_on": "2026-08-23",
    },
}


# ---------------------------------------------------------------------------
# the metric
# ---------------------------------------------------------------------------
def alphanumerics(text: str) -> str:
    """The alphanumeric characters of ``text``, in order, case preserved."""
    return "".join(character for character in text if character.isalnum())


def gold_key(text: str) -> str:
    """The comparison key the admission rule is stated in terms of."""
    return alphanumerics(text).casefold()


def admits(identifier: str, caption: str) -> bool:
    """Whether a publisher caption may serve as gold for this identifier.

    The rule, exactly as ``docs/EVALUATION.md`` states it: the caption's
    alphanumerics case-fold equal to the identifier's, **and** the caption
    contains whitespace. Nothing else is admitted, so nothing in the scored
    population differs from its identifier by anything except where the words
    were cut.

    Args:
        identifier: The machine name, as published.
        caption: The human caption, as published.

    Returns:
        True when the pair may be scored.
    """
    if not identifier or not caption:
        return False
    if not any(character.isspace() for character in caption):
        return False
    key = gold_key(identifier)
    return bool(key) and key == gold_key(caption)


def cuts(text: str) -> Set[int]:
    """Cut positions in the alphanumeric stream of ``text``.

    A cut sits at index ``n`` when the ``n``-th alphanumeric character is
    preceded, in the source string, by at least one non-alphanumeric character
    and is not the first. Whitespace is not privileged over other punctuation:
    ``Available-for-Sale`` and ``Available for Sale`` produce the same two cuts,
    because ``-`` is a separator under the splitter's own rule 2 and scoring it
    as an error would be scoring the caption's typography.

    Args:
        text: A caption or a produced phrase.

    Returns:
        The cut positions.
    """
    positions: Set[int] = set()
    seen = 0
    gap = False
    for character in text:
        if character.isalnum():
            if gap and seen:
                positions.add(seen)
            gap = False
            seen += 1
        else:
            gap = True
    return positions


#: The four cut signals the splitter reads, in the order its docstring numbers
#: them: a separator (rule 2), a camelCase change (rule 3), the end of a capital
#: run (rule 4) and a letter-digit change (rule 5). A cut at any other position
#: is one the identifier does not mark.
SIGNAL_NAMES = ("separator", "camel_case", "acronym_run", "letter_digit")


def signals(identifier: str) -> Dict[str, Set[int]]:
    """Where the identifier itself marks a cut, by which convention marks it.

    This is the ceiling's basis. A splitter that refuses to guess -- no
    dictionary, no language model, no frequency table -- can only place a cut
    where the characters say one belongs, so the gold cuts that land on one of
    these positions are the recoverable ones and the rest are not.

    Args:
        identifier: The machine name, as published.

    Returns:
        ``{signal name: positions}`` over the alphanumeric stream.
    """
    stream: List[str] = []
    separator: Set[int] = set()
    gap = False
    for character in identifier:
        if character.isalnum():
            if gap and stream:
                separator.add(len(stream))
            gap = False
            stream.append(character)
        else:
            gap = True

    camel: Set[int] = set()
    run: Set[int] = set()
    digit: Set[int] = set()
    for index in range(1, len(stream)):
        previous, current = stream[index - 1], stream[index]
        if previous.isdigit() != current.isdigit():
            digit.add(index)
        elif previous.islower() and current.isupper():
            camel.add(index)
        elif (
            previous.isupper()
            and current.isupper()
            and index + 1 < len(stream)
            and stream[index + 1].islower()
        ):
            run.add(index)
    return {
        "separator": separator,
        "camel_case": camel,
        "acronym_run": run,
        "letter_digit": digit,
    }


def is_marked(marks: Dict[str, Set[int]]) -> bool:
    """Whether the identifier carries a word boundary mark a reader would see.

    Separators and case changes count; a letter-digit change deliberately does
    not. ``covid19`` is flatcase with a number in it, not a segmented name, and
    filing it under ``marked`` would move the hardest population into the row
    the headline is read off.
    """
    return bool(marks["separator"] or marks["camel_case"] or marks["acronym_run"])


def shape_of(identifier: str, marks: Dict[str, Set[int]]) -> str:
    """The identifier's written shape, for the transfer caveat.

    Named for what a schema owner would call it. The point of reporting this is
    negative: a shape with zero pairs in it is a shape this measurement says
    nothing about, and counting that is stronger than asserting it in prose.

    ``marks`` is passed in rather than recomputed so that "is this separated?"
    is decided by the same code that decides "is this marked?". They disagreed
    in the first draft over a *leading* separator -- Socrata prefixes a field
    name that starts with a digit with ``_`` -- and ``_casenumber`` was counted
    as snake_lower in one table and unmarked in the other. One definition, one
    place.

    Args:
        identifier: The machine name, as published.
        marks: The output of :func:`signals` for it.

    Returns:
        A shape name.
    """
    letters = [character for character in identifier if character.isalpha()]
    upper = any(character.isupper() for character in letters)
    lower = any(character.islower() for character in letters)
    if marks["separator"] and _has_internal(identifier, "."):
        return "dotted"
    if marks["separator"]:
        if upper and lower:
            return "snake_mixed"
        return "snake_upper" if upper else "snake_lower"
    if upper and lower:
        return "camel"
    if not letters:
        return "digits_only"
    return "flat_upper" if upper else "flat_lower"


def _has_internal(text: str, character: str) -> bool:
    """Whether ``character`` occurs between two alphanumerics of ``text``."""
    index = text.find(character)
    while index > 0:
        if text[index - 1].isalnum() and any(rest.isalnum() for rest in text[index + 1 :]):
            return True
        index = text.find(character, index + 1)
    return False


@dataclass
class Tally:
    """Counters for one subset of one arm.

    Attributes:
        pairs: Scored pairs.
        exact: Pairs whose predicted cut set equals the gold cut set.
        hits: Predicted cuts that are gold cuts.
        spurious: Predicted cuts that are not.
        missed: Gold cuts that were not predicted.
        gold_cuts: Gold cuts seen.
        reachable: Gold cuts sitting at a position the identifier marks.
    """

    pairs: int = 0
    exact: int = 0
    hits: int = 0
    spurious: int = 0
    missed: int = 0
    gold_cuts: int = 0
    reachable: int = 0

    def add(self, *, exact: bool, hits: int, spurious: int, missed: int, reachable: int) -> None:
        """Fold one scored pair in."""
        self.pairs += 1
        self.exact += int(exact)
        self.hits += hits
        self.spurious += spurious
        self.missed += missed
        self.gold_cuts += hits + missed
        self.reachable += reachable

    def as_dict(self) -> Dict[str, Optional[float]]:
        """The published shape of this subset.

        Percentages are rounded to two decimals because that is the precision
        the documents quote at, and a claim citation resolves to whatever is
        stored here.

        An undefined ratio is stored as ``null``, never as ``0.0``. The two
        SEC taxonomy arms have no flatcase pairs at all, and a stored
        ``boundary_precision_pct: 0.0`` for an empty subset reads as "got
        everything wrong" while meaning "made no predictions" -- and it is a
        citable path, so somebody would eventually cite it. ``null`` makes a
        citation to an empty subset fail instead, which is the only property
        that makes a citation worth writing.
        """
        predicted = self.hits + self.spurious
        precision = self.hits / predicted if predicted else None
        recall = self.hits / self.gold_cuts if self.gold_cuts else None
        f1: Optional[float] = None
        if precision is not None and recall is not None and precision + recall:
            f1 = 2 * precision * recall / (precision + recall)
        return {
            "pairs": self.pairs,
            "exact_pct": round(self.exact / self.pairs * 100, 2) if self.pairs else None,
            "boundary_precision_pct": None if precision is None else round(precision * 100, 2),
            "boundary_recall_pct": None if recall is None else round(recall * 100, 2),
            "boundary_f1_pct": None if f1 is None else round(f1 * 100, 2),
            "boundary_recall_ceiling_pct": (
                round(self.reachable / self.gold_cuts * 100, 2) if self.gold_cuts else None
            ),
            "gold_boundaries": self.gold_cuts,
        }


@dataclass
class Arm:
    """One scored population: a corpus, an author, a set of pairs."""

    corpus: str
    name: str
    source_url: str
    pairs: Sequence[Tuple[str, str]] = field(default_factory=tuple)
    #: Distinct ``(identifier, caption)`` pairs in the source population, before
    #: admission. Distinct on both sides of the ratio, because a deduplicated
    #: numerator over a raw denominator is not a rate of anything.
    columns_seen: int = 0
    #: Column occurrences behind those distinct pairs, duplicates included.
    occurrences_seen: int = 0
    fetched_on: str = ""
    #: Print only the pooled row for this arm. Set on the split halves, whose
    #: mark decomposition is the parent arm's and would triple the table.
    summary_only: bool = False
    #: Distinct publishing portals behind the arm; 0 when the notion does not
    #: apply, as it does not to a taxonomy.
    portals: int = 0


def evaluate(arm: Arm) -> Dict[str, object]:
    """Score one arm and return the entry that goes into ``bench/results.json``.

    Args:
        arm: The population, already admitted.

    Returns:
        The measurement, decomposed by mark and by shape, with provenance.
    """
    catalog = GovernedDictionary({})
    overall, marked, unmarked = Tally(), Tally(), Tally()
    by_signal: Dict[str, int] = dict.fromkeys(SIGNAL_NAMES, 0)
    unsignalled_spurious = 0
    missed_marked = 0
    missed_unmarked = 0
    shapes: Dict[str, int] = {}
    # Words in the caption, bucketed. A longer name has more cuts to get right,
    # so a whole-identifier metric must fall with length; if it did not, the
    # metric would be measuring something other than what it says.
    by_words: Dict[str, List[int]] = {}
    skew = 0

    for identifier, caption in arm.pairs:
        phrase = expand_identifier(identifier, catalog).phrase
        # The admission rule fixes the character stream, and the expander is not
        # supposed to move it. If it did, the pair cannot be scored on a shared
        # stream and is dropped rather than silently mis-aligned. `skew` is
        # published so that "dropped" can never become invisible.
        if gold_key(phrase) != gold_key(caption):
            skew += 1
            continue

        gold, predicted = cuts(caption), cuts(phrase)
        marks = signals(identifier)
        reachable_positions = set().union(*marks.values()) if marks else set()

        hits = len(predicted & gold)
        spurious = predicted - gold
        missed = gold - predicted
        reachable = len(gold & reachable_positions)

        for position in spurious:
            for signal_name in SIGNAL_NAMES:
                if position in marks[signal_name]:
                    by_signal[signal_name] += 1
                    break
            else:  # pragma: no cover - the splitter cuts only where it is signalled
                unsignalled_spurious += 1
        for position in missed:
            if position in reachable_positions:
                missed_marked += 1
            else:
                missed_unmarked += 1

        shape = shape_of(identifier, marks)
        shapes[shape] = shapes.get(shape, 0) + 1
        words = len(gold) + 1
        bucket = str(words) if words < 6 else "6+"
        tally = by_words.setdefault(bucket, [0, 0])
        tally[0] += 1
        tally[1] += int(predicted == gold)
        sample = {
            "exact": predicted == gold,
            "hits": hits,
            "spurious": len(spurious),
            "missed": len(missed),
            "reachable": reachable,
        }
        overall.add(**sample)
        (marked if is_marked(marks) else unmarked).add(**sample)

    licence = LICENCES[arm.corpus]
    return {
        "corpus": arm.corpus,
        "arm": arm.name,
        "system": "acronymkit.governed.expand_identifier, empty catalog",
        "source_url": arm.source_url,
        "fetched_on": arm.fetched_on,
        "distinct_pairs_seen": arm.columns_seen,
        "occurrences_seen": arm.occurrences_seen,
        "admitted": len(arm.pairs),
        "admission_rate_pct": (
            round(len(arm.pairs) / arm.columns_seen * 100, 2) if arm.columns_seen else 0.0
        ),
        "unscorable_stream_skew": skew,
        "portals": arm.portals,
        "summary_only": arm.summary_only,
        "all": overall.as_dict(),
        "marked": marked.as_dict(),
        "unmarked": unmarked.as_dict(),
        "false_positives_by_signal": {**by_signal, "unsignalled": unsignalled_spurious},
        "false_negatives_marked": missed_marked,
        "false_negatives_unmarked": missed_unmarked,
        "identifier_shapes": dict(sorted(shapes.items())),
        "exact_pct_by_caption_words": {
            bucket: round(hit / seen * 100, 2)
            for bucket, (seen, hit) in sorted(by_words.items())
            if seen
        },
        "pairs_by_caption_words": {
            bucket: seen for bucket, (seen, _hit) in sorted(by_words.items())
        },
        **licence,
    }


def gold_conflict(occurrences: Sequence[Tuple[str, str]]) -> Dict[str, object]:
    """How often two publishers cut the same identifier differently.

    The gold here is one organisation's caption, not a ruling from a
    data-governance function, and the cheapest available check on how much that
    matters is whether the *other* publishers agree. An identifier that two
    portals caption with different cuts has no single right answer, so the share
    of contested identifiers is a floor under the disagreement any system will
    record against this gold, however good it is.

    Args:
        occurrences: Admitted ``(identifier, caption)`` pairs, **not** deduped;
            the same identifier from different datasets must appear repeatedly
            or there is nothing to disagree about.

    Returns:
        Counts by type and by occurrence.
    """
    by_identifier: Dict[str, Set[frozenset]] = {}
    for identifier, caption in occurrences:
        by_identifier.setdefault(gold_key(identifier), set()).add(frozenset(cuts(caption)))
    contested = {key for key, variants in by_identifier.items() if len(variants) > 1}

    total_occurrences = len(occurrences)
    contested_occurrences = sum(
        1 for identifier, _caption in occurrences if gold_key(identifier) in contested
    )
    return {
        "distinct_identifiers": len(by_identifier),
        "contested_identifiers": len(contested),
        "contested_identifiers_pct": (
            round(len(contested) / len(by_identifier) * 100, 2) if by_identifier else 0.0
        ),
        "occurrences": total_occurrences,
        "contested_occurrences": contested_occurrences,
        "contested_occurrences_pct": (
            round(contested_occurrences / total_occurrences * 100, 2) if total_occurrences else 0.0
        ),
    }


# ---------------------------------------------------------------------------
# fetching
# ---------------------------------------------------------------------------
class RangedHTTPFile:
    """A seekable read-only file over an HTTP resource, backed by range requests.

    :mod:`zipfile` reads the central directory from the end of an archive and
    then only the members it is asked for, so handing it one of these turns a
    122 MB download into about 3.4 MB. Deliberately not an :class:`io.RawIOBase`
    subclass: that base class routes reads through ``readinto`` and the duck type
    :mod:`zipfile` actually needs is ``read``/``seek``/``tell``/``seekable``.

    Attributes:
        requests: Range requests issued, so the report can state the wire cost.
        downloaded: Bytes received.
    """

    def __init__(self, url: str, headers: Dict[str, str]) -> None:
        self.url = url
        self.headers = headers
        self.position = 0
        self.requests = 0
        self.downloaded = 0
        probe = urllib.request.Request(url, headers={**headers, "Range": "bytes=0-0"})
        with urllib.request.urlopen(probe, timeout=60) as response:
            content_range = response.headers.get("Content-Range")
            if not content_range:
                raise RuntimeError(f"{url} does not honour HTTP range requests")
            self.size = int(content_range.rsplit("/", 1)[-1])

    def seekable(self) -> bool:
        """Always true; that is the point of the class."""
        return True

    def tell(self) -> int:
        """Current offset."""
        return self.position

    def seek(self, offset: int, whence: int = 0) -> int:
        """Move the offset, with the usual ``whence`` semantics."""
        if whence == 0:
            self.position = offset
        elif whence == 1:
            self.position += offset
        else:
            self.position = self.size + offset
        return self.position

    def read(self, count: int = -1) -> bytes:
        """Read ``count`` bytes from the current offset via one range request."""
        if count is None or count < 0:
            count = self.size - self.position
        if count == 0 or self.position >= self.size:
            return b""
        last = min(self.position + count, self.size) - 1
        request = urllib.request.Request(
            self.url, headers={**self.headers, "Range": f"bytes={self.position}-{last}"}
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = response.read()
        self.requests += 1
        self.downloaded += len(payload)
        self.position += len(payload)
        return payload

    def close(self) -> None:
        """No connection is held open, so this is a no-op."""


def _cache_path(name: str) -> Path:
    """Where a fetched payload is cached."""
    return CACHE_DIR / name


def _read_cache(name: str) -> Optional[Dict[str, object]]:
    """The cached envelope for ``name``, or ``None``."""
    path = _cache_path(name)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_cache(name: str, payload: object) -> Dict[str, object]:
    """Cache ``payload`` with the date it was fetched, and return the envelope."""
    envelope = {"fetched_on": _datetime.date.today().isoformat(), "payload": payload}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(name).write_text(json.dumps(envelope), encoding="utf-8")
    return envelope


def fetch_sec_tags(quarter: str, *, refresh: bool = False) -> Dict[str, object]:
    """SEC XBRL ``(tag, label, taxonomy)`` triples for one quarter.

    Args:
        quarter: e.g. ``"2025q1"``.
        refresh: Ignore any cached copy.

    Returns:
        ``{"fetched_on": ..., "payload": [[tag, label, taxonomy], ...]}``.

    Raises:
        SystemExit: If the archive cannot be fetched and nothing is cached.
    """
    name = f"sec_xbrl_{quarter}.json"
    if not refresh:
        cached = _read_cache(name)
        if cached is not None:
            return cached

    url = SEC_URL_TEMPLATE.format(quarter=quarter)
    try:
        handle = RangedHTTPFile(url, {"User-Agent": SEC_USER_AGENT})
        archive = zipfile.ZipFile(handle)  # type: ignore[arg-type]
        raw = archive.read("tag.txt").decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, zipfile.BadZipFile) as error:
        raise SystemExit(
            f"could not fetch {url}: {error}\n"
            "This runner fetches its own corpora so the table is re-derivable. "
            "Re-run with a network connection, or point --quarter at a cached quarter."
        ) from error

    print(
        f"  sec: {handle.requests} range requests, "
        f"{handle.downloaded / 1e6:.1f} MB of a {handle.size / 1e6:.0f} MB archive"
    )
    rows: List[List[str]] = []
    for row in csv.DictReader(io.StringIO(raw), delimiter="\t"):
        taxonomy = "filer_extension" if row.get("custom") == "1" else _taxonomy(row.get("version"))
        rows.append([row.get("tag") or "", row.get("tlabel") or "", taxonomy])
    return _write_cache(name, rows)


def _taxonomy(version: Optional[str]) -> str:
    """The taxonomy family a standard tag belongs to.

    ``us-gaap/2024`` and ``ifrs/2023`` are different editorial conventions, and
    the difference is measurable: IFRS element names drop a hyphen without
    capitalising the next word, so ``paid-in`` becomes ``Paidin`` and the cut
    stops being marked. Pooling them would hide that behind an average.
    """
    family = (version or "").split("/", 1)[0].strip().lower()
    return family.replace("-", "_") or "unknown"


def fetch_socrata_columns(pages: int, *, refresh: bool = False) -> Dict[str, object]:
    """Socrata ``(field name, caption)`` pairs from the Discovery API catalog.

    Paged with ``scroll_id``, which orders by dataset id and therefore walks the
    same datasets in the same order on every run -- as far as a live catalog
    allows, which is the honest limit on re-derivability here and is reported
    beside the number.

    Args:
        pages: Catalog pages of 100 datasets.
        refresh: Ignore any cached copy.

    Returns:
        ``{"fetched_on": ..., "payload": [[field, caption, portal], ...]}`` with
        one entry per column *occurrence*, not per distinct pair. The portal is
        carried so the population can be split disjointly by publisher.

    Raises:
        SystemExit: If the catalog cannot be reached and nothing is cached.
    """
    name = f"socrata_{pages}pages_v2.json"
    if not refresh:
        cached = _read_cache(name)
        if cached is not None:
            return cached

    columns: List[List[str]] = []
    scroll: Optional[str] = None
    for page in range(pages):
        url = SOCRATA_URL + (f"&scroll_id={scroll}" if scroll else "")
        request = urllib.request.Request(url, headers={"User-Agent": SOCRATA_USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                document = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise SystemExit(
                f"could not fetch {url}: {error}\n"
                "This runner fetches its own corpora so the table is re-derivable. "
                "Re-run with a network connection."
            ) from error
        results = document.get("results") or []
        if not results:
            break
        for entry in results:
            resource = entry.get("resource") or {}
            portal = str((entry.get("metadata") or {}).get("domain") or "")
            fields = resource.get("columns_field_name") or []
            captions = resource.get("columns_name") or []
            for identifier, caption in zip(fields, captions):
                columns.append([identifier or "", caption or "", portal])
        scroll = (results[-1].get("resource") or {}).get("id")
        if not scroll:
            break
        if (page + 1) % 20 == 0:
            print(f"  socrata: {page + 1} pages, {len(columns):,} columns")
    return _write_cache(name, columns)


# ---------------------------------------------------------------------------
# split discipline
# ---------------------------------------------------------------------------
def declared_role(corpus: str) -> str:
    """What ``bench/splits.toml`` declares about ``corpus``, via ``tools/splits.py``.

    Operating rule 2 says to ask the manifest rather than assume, and this
    runner asks. When the corpus is not declared the run does **not** stop --
    these two corpora are new and their manifest entries are written by whoever
    owns that file -- but the gap is printed loudly and recorded in the saved
    entry, so a figure derived from an undeclared corpus carries the fact that
    it was undeclared wherever it goes. Silence is the failure the manifest
    exists to prevent.

    Args:
        corpus: The manifest corpus name.

    Returns:
        The declared role, or a string beginning ``"UNDECLARED"``.

    Raises:
        SystemExit: If the corpus is declared ``role = "tuning"``. A tuning
            figure may not be presented as evidence of generalisation, and
            nothing this runner produces is labelled as a tuning number.
    """
    tool = REPO_ROOT / "tools" / "splits.py"
    if not tool.is_file():  # pragma: no cover - not a source checkout
        return "UNDECLARED (tools/splits.py not present)"
    spec = importlib.util.spec_from_file_location("_governed_gold_splits", tool)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        return "UNDECLARED (tools/splits.py not importable)"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    try:
        entry = module.load().corpus(corpus)
    except Exception:  # any manifest problem at all means "not declared here"
        return f"UNDECLARED ({corpus} is not in bench/splits.toml)"
    if entry.role == "tuning":
        raise SystemExit(
            f"bench/splits.toml declares {corpus} role='tuning'. Operating rule 2: a tuning "
            "figure may never be presented as evidence of generalisation, and this runner "
            "does not label its output as one."
        )
    return str(entry.role)


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def render(entries: Dict[str, Dict[str, object]]) -> str:
    """The console table, worst row beside the headline.

    Operating rule 5: every accuracy table ships its worst row beside its
    headline, and the ceiling is in the same table as the recall it bounds.
    """
    lines = [
        "",
        f"{'arm':<34}{'subset':<10}{'n':>8}{'exact %':>10}"
        f"{'bP %':>8}{'bR %':>8}{'bF1 %':>8}{'ceiling':>9}",
        "-" * 95,
    ]
    for run_id, entry in entries.items():
        if "all" not in entry:
            continue
        label = run_id.replace("governed_gold.", "")
        subsets = ("all",) if entry.get("summary_only") else ("all", "marked", "unmarked")
        for subset in subsets:
            figures = entry[subset]
            assert isinstance(figures, dict)
            if not figures["pairs"]:
                continue
            lines.append(
                f"{label if subset == 'all' else '':<34}{subset:<10}"
                f"{figures['pairs']:>8,}{figures['exact_pct']:>10.2f}"
                f"{figures['boundary_precision_pct']:>8.2f}"
                f"{figures['boundary_recall_pct']:>8.2f}"
                f"{figures['boundary_f1_pct']:>8.2f}"
                f"{figures['boundary_recall_ceiling_pct']:>9.2f}"
            )
        lines.append("")
    return "\n".join(lines)


def render_detail(entries: Dict[str, Dict[str, object]]) -> str:
    """Error decomposition and shape coverage, which is where the caveats come from."""
    lines = []
    for run_id, entry in entries.items():
        if "all" not in entry or entry.get("summary_only"):
            continue
        lines.append(f"{run_id}")
        by_signal = entry["false_positives_by_signal"]
        assert isinstance(by_signal, dict)
        fired = ", ".join(f"{name} {count:,}" for name, count in by_signal.items() if count)
        lines.append(f"    cut where the publisher did not : {fired or 'none'}")
        lines.append(
            f"    publisher cut, identifier unmarked: {entry['false_negatives_unmarked']:,}"
            f"   marked but missed: {entry['false_negatives_marked']:,}"
        )
        shapes = entry["identifier_shapes"]
        assert isinstance(shapes, dict)
        lines.append(
            "    shapes                           : "
            + ", ".join(f"{name} {count:,}" for name, count in shapes.items())
        )
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def sec_arms(quarter: str, *, refresh: bool) -> List[Arm]:
    """The three SEC arms, admitted and deduplicated to distinct pairs."""
    envelope = fetch_sec_tags(quarter, refresh=refresh)
    rows = envelope["payload"]
    assert isinstance(rows, list)
    url = SEC_URL_TEMPLATE.format(quarter=quarter)
    arms = []
    for taxonomy in ("us_gaap", "ifrs", "filer_extension"):
        seen = [row for row in rows if row[2] == taxonomy]
        # Deduplicated: tag.txt carries one row per (tag, filing version), so the
        # same element recurs thousands of times and an occurrence-weighted
        # figure would be a popularity contest between filers.
        distinct = {(row[0], row[1]) for row in seen}
        pairs = sorted(pair for pair in distinct if admits(*pair))
        arms.append(
            Arm(
                corpus="sec_xbrl",
                name=taxonomy,
                source_url=f"{url}#tag.txt",
                pairs=pairs,
                columns_seen=len(distinct),
                occurrences_seen=len(seen),
                fetched_on=str(envelope["fetched_on"]),
            )
        )
    return arms


def portal_half(portal: str) -> str:
    """Which half of the publisher-disjoint split a portal falls in.

    A stable digest rather than :func:`hash`, whose string seed is randomised
    per process -- a split that moves between runs is not a split.
    """
    digest = hashlib.sha256(portal.encode("utf-8")).digest()
    return "a" if digest[0] % 2 == 0 else "b"


def socrata_arms(pages: int, *, refresh: bool) -> Tuple[List[Arm], List[Tuple[str, str]]]:
    """The Socrata arms, plus the un-deduplicated occurrences the conflict check needs.

    Three arms: the whole population, and the two halves of a **publisher-disjoint**
    split. The split is the cheap answer to "is this number an artifact of a
    handful of big portals?" -- no portal contributes to both halves, so two
    halves that agree are two independent samples of the same phenomenon and two
    that disagree say the pooled figure is a weighted average of unlike things.
    It is a robustness check, not a train/test split: nothing is fitted here, so
    there is nothing to hold out from.

    Args:
        pages: Catalog pages of 100 datasets.
        refresh: Ignore any cached copy.

    Returns:
        The arms, and every admitted occurrence with its duplicates intact.
    """
    envelope = fetch_socrata_columns(pages, refresh=refresh)
    rows = envelope["payload"]
    assert isinstance(rows, list)
    fetched_on = str(envelope["fetched_on"])
    admitted = [row for row in rows if admits(row[0], row[1])]
    occurrences = [(row[0], row[1]) for row in admitted]

    def arm(name: str, chosen: Sequence[Sequence[str]], source: Sequence[Sequence[str]]) -> Arm:
        return Arm(
            corpus="socrata",
            name=name,
            source_url=SOCRATA_URL,
            pairs=sorted({(row[0], row[1]) for row in chosen}),
            columns_seen=len({(row[0], row[1]) for row in source}),
            occurrences_seen=len(source),
            portals=len({row[2] for row in source if len(row) > 2}),
            fetched_on=fetched_on,
        )

    whole = arm("columns", admitted, rows)
    arms = [whole]
    for half in ("a", "b"):
        chosen = [row for row in admitted if portal_half(row[2] if len(row) > 2 else "") == half]
        source = [row for row in rows if portal_half(row[2] if len(row) > 2 else "") == half]
        portal_arm = arm(f"portal_half_{half}", chosen, source)
        portal_arm.summary_only = True
        arms.append(portal_arm)
    return arms, occurrences


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument(
        "--only",
        choices=("all", "sec", "socrata"),
        default="all",
        help="restrict the run to one corpus",
    )
    parser.add_argument("--quarter", default=SEC_QUARTER, help=f"SEC quarter ({SEC_QUARTER})")
    parser.add_argument(
        "--pages", type=int, default=SOCRATA_PAGES, help=f"Socrata pages ({SOCRATA_PAGES})"
    )
    parser.add_argument("--refresh", action="store_true", help="re-fetch, ignoring the cache")
    args = parser.parse_args(argv)

    entries: Dict[str, Dict[str, object]] = {}

    if args.only in ("all", "sec"):
        role = declared_role("sec_xbrl")
        print(f"sec_xbrl: bench/splits.toml says {role}")
        for arm in sec_arms(args.quarter, refresh=args.refresh):
            entry = evaluate(arm)
            entry["splits_declaration"] = role
            entry["sec_quarter"] = args.quarter
            entries[f"governed_gold.sec_xbrl.{arm.name}"] = entry

    if args.only in ("all", "socrata"):
        role = declared_role("socrata")
        print(f"socrata : bench/splits.toml says {role}")
        arms, occurrences = socrata_arms(args.pages, refresh=args.refresh)
        for arm in arms:
            entry = evaluate(arm)
            entry["splits_declaration"] = role
            entry["socrata_pages"] = args.pages
            entries[f"governed_gold.socrata.{arm.name}"] = entry
        conflict = gold_conflict(occurrences)
        conflict["splits_declaration"] = role
        conflict["source_url"] = SOCRATA_URL
        conflict["fetched_on"] = arms[0].fetched_on
        entries["governed_gold.socrata.gold_conflict"] = conflict

    print(render(entries))
    print(render_detail(entries))
    if "governed_gold.socrata.gold_conflict" in entries:
        conflict = entries["governed_gold.socrata.gold_conflict"]
        print(
            "gold conflict: "
            f"{conflict['contested_identifiers']:,} of {conflict['distinct_identifiers']:,} "
            f"identifiers ({conflict['contested_identifiers_pct']} %) are captioned with two "
            "different cut placements by two different publishers"
        )

    if args.save:
        from run_extraction import save_results

        print(f"\nsaved {len(entries)} run(s) to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
