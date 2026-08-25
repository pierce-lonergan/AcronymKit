#!/usr/bin/env python3
"""Measure how much of this field's evaluation ecosystem is one algorithm.

The question, stated so it can be wrong
---------------------------------------
D-056 found that pooling four abbreviation extractors over thirty Federal
Register rules produced a union that was ``93.74 %`` acronymkit, and gave the
reason: every pooled system descends from Schwartz & Hearst 2003, so the pool is
one algorithm with four implementations. Read beside ``bench/run_spans.py`` --
where a one-line all-caps rule beats every definition extractor on PLOD short
forms -- a thesis assembles itself:

    the corpora that certify abbreviation extractors were built by pooling
    systems that share one algorithm's blind spot, so the gold standard
    certifies the blind spot.

This runner exists to measure that, not to argue it. It produces four things:

1. **The Schwartz & Hearst commitment, transcribed and executable.**
   :func:`sh_alignable` is the 2003 paper's ``findBestLongForm`` -- a
   right-to-left greedy character-subsequence walk over the long form, with the
   short form's first character required to land on a word-initial character.
   Every "S&H descendant" in the table below accepts a pair only if this
   predicate holds, and generates candidates only from a bracketed window. Those
   are the two commitments; a proposer that makes neither is independent, and
   the independence is then a *measurement* -- what share of its proposals fail
   :func:`sh_alignable` -- rather than an assertion about lineage.

2. **A proposer that provably makes neither commitment.** :func:`propose_shapecue`
   finds short forms by orthographic shape, and long forms by a lexical cue
   (``hereinafter``, ``stands for``, ``also known as``) or by an abbreviation
   **roster** -- the figure legends and table footnotes that read
   ``EPI = Echo planar imaging`` or
   ``BMI: body mass index; CE: cholesteryl ester``. It never reads a bracket and
   it never compares a character of the short form against the long form. Its
   independence is demonstrated three ways: by construction in
   ``tests/test_monoculture.py``, on a pair sharing no character with its own
   abbreviation; and mechanically here on both axes, as ``sh_unalignable_pct``
   (the validator would refuse this edge) and ``bracketless_edges_pct`` (the
   candidate generator never sees it). The second is the load-bearing one,
   because most real abbreviations *are* alignable -- a proposer can be fully
   independent of the validator and still emit alignable pairs, so a low
   ``sh_unalignable_pct`` is not evidence of descent.

   The roster rule was added because the measurement demanded it and the record
   says so: with the cue rule alone this proposer emitted **three edges across
   2.06 MB of text**, which is not a sample and cannot support an independence
   measurement (R12).

3. **The pairwise overlap matrix and the union gain per proposer** (R13).
   A proposer whose union gain is under a few percent is decoration, and the
   table says so in a column rather than in prose.

4. **The class of gold that no S&H descendant proposes**, decomposed by cause,
   on corpora whose gold was *not* pooled from S&H descendants.

Which corpora can answer question 4, and why
--------------------------------------------
A union gain measured against gold that was itself pooled from S&H descendants
is circular by construction. Two of the corpora here are not:

* **PLOD-CW.** Its annotations come from each PLOS article's own *Abbreviations*
  section -- the glossary the journal requires the authors to submit -- matched
  back onto the body text. Zilio et al. (LREC 2022, arXiv:2204.12061) describe
  parsing the article XML and say they "extracted short and long forms from the
  'Abbreviations' section". The arbiter is the paper's author and no
  abbreviation-detection system is anywhere in that pipeline, which is what makes
  this corpus able to answer the question at all. Read live from the paper on
  2026-08-24. PLOD is also ``role = "held_out"`` and uncontaminated in
  ``bench/splits.toml``.

  **Its own error rate is published and is not small**: the same paper's
  validation sample reports wrong annotation in one segment in twenty and
  *missing* annotation in more than a quarter. Every "unreached" figure this
  runner produces therefore has a denominator that is itself incomplete, in an
  unknown direction.
* **SDU@AAAI-22 AE.** Manually annotated with inter-annotator agreement reported
  (Veyseh et al., COLING 2022). Both dev arms are ``contaminated = true`` here --
  their miss taxonomies have been read -- so they corroborate rather than lead,
  and both ``train`` arms are reserved and are not touched.

**MED1250 is the control and is not independent of the pool.** It is Ab3P's own
evaluation corpus and ``pyab3p`` in this table is Ab3P. Its row is here precisely
so the contrast is visible: on the corpus built for these systems the pool
reaches most of the gold; on corpora built by other means it does not.

What this runner does NOT do
----------------------------
It does not build a better extractor. Knowing the field shares a blind spot does
not say how to fill it, and the two are separate pieces of work (R6).

No LLM proposer was built. One would be non-deterministic and network-touching,
could not ship, and is a corpus-construction instrument rather than a measuring
one; the disposition is recorded in ``docs/EVALUATION.md``.

Usage::

    python bench/run_monoculture.py --interpreter C:/akbench/Scripts/python.exe --save
    python bench/run_monoculture.py --corpus plod_test --interpreter <python>
    python bench/run_monoculture.py --demo        # the independence demonstration

The external baselines need an interpreter that has them installed; ``pyab3p``
ships wheels only to CPython 3.12 and ``scispacy`` declares ``<3.13``. Without
``--interpreter`` the runner still works, and every record it writes names the
proposers that were present -- a matrix computed over a subset is not the same
matrix, and ``proposers`` is written into every record so it cannot be read as
one.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

Pair = tuple[str, str]
CharSpan = tuple[int, int]


# ---------------------------------------------------------------------------
# 1. The Schwartz & Hearst commitment, transcribed
# ---------------------------------------------------------------------------
def sh_alignable(short_form: str, long_form: str) -> bool:
    """Would Schwartz & Hearst's 2003 validator accept this pair?

    A transcription of ``findBestLongForm`` from *A simple algorithm for
    identifying abbreviation definitions in biomedical text* (PSB 2003), which
    is the acceptance test every implementation in :data:`SH_FAMILY` inherits:

    * walk the short form right to left, skipping non-alphanumerics;
    * for each character, walk the long form left-ward to the next occurrence,
      **greedily** -- the first match wins and is never revisited;
    * the short form's **first** character must land on a character that begins
      a word in the long form.

    So the algorithm's commitment is that a short form is a *character
    subsequence* of its long form under a word-initial anchor. That is what a
    proposer must not do to be independent of it, and it is why
    :func:`propose_shapecue` compares no characters at all.

    Args:
        short_form: The abbreviation.
        long_form: The candidate expansion.

    Returns:
        ``True`` when the greedy right-to-left walk consumes the whole short
        form. ``False`` for an empty short form, a short form with no
        alphanumeric character, or a walk that runs off the left edge.
    """
    if not short_form or not long_form:
        return False
    if not any(character.isalnum() for character in short_form):
        return False
    short_index = len(short_form) - 1
    long_index = len(long_form) - 1
    while short_index >= 0:
        current = short_form[short_index].lower()
        if not current.isalnum():
            short_index -= 1
            continue
        while long_index >= 0 and (
            long_form[long_index].lower() != current
            or (short_index == 0 and long_index > 0 and long_form[long_index - 1].isalnum())
        ):
            long_index -= 1
        if long_index < 0:
            return False
        long_index -= 1
        short_index -= 1
    return True


#: External systems that make **both** Schwartz & Hearst commitments: candidates
#: come from a bracketed window, and a candidate is accepted only if
#: :func:`sh_alignable` holds. Naming them is a claim about mechanism and each
#: one is checkable:
#:
#: * ``abbreviations`` -- a pure-Python transcription of the 2003 pseudocode.
#: * ``abbreviation_extractor`` -- a Rust transcription of the same.
#: * ``pyab3p`` -- bindings around NLM's Ab3P, which scores candidates drawn from
#:   the same parenthetical window under the same alignment.
#: * ``scispacy`` -- ``AbbreviationDetector``, documented by its authors as an
#:   implementation of Schwartz & Hearst.
#:
#: ``acronymkit`` itself is the fifth, in three operating points: see
#: ``src/acronymkit/extractor.py``, which scans bracketed regions and validates
#: with its own character alignment.
EXTERNAL_SH_SYSTEMS = ("abbreviations", "abbreviation_extractor", "pyab3p", "scispacy")

#: acronymkit operating points, matching ``bench/run_spans.py``'s rows.
PROFILES = ("high_precision", "general", "biomedical")

#: The independent proposers. ``allcaps`` is the trivial rule already in
#: ``bench/run_spans.py``, re-implemented here over character offsets so it can
#: run on the character-span corpora too; ``shapecue`` is this runner's.
INDEPENDENT_PROPOSERS = ("allcaps", "shapecue")


def sh_family(present: Sequence[str]) -> list[str]:
    """The S&H descendants among ``present``, in a stable order."""
    return [name for name in present if name not in INDEPENDENT_PROPOSERS]


# ---------------------------------------------------------------------------
# 2. A proposer that makes neither commitment
# ---------------------------------------------------------------------------
_TOKEN = re.compile(r"\S+")
_EDGE_JUNK = re.compile(r"^[^0-9A-Za-z]+|[^0-9A-Za-z]+$")

#: Cues where the long form comes **before** the cue and the short form after
#: it: "the Global Environment Facility, hereinafter GEF".
CUES_LONG_FORM_FIRST: tuple[tuple[str, ...], ...] = (
    ("hereinafter", "referred", "to", "as"),
    ("hereinafter", "called"),
    ("hereinafter",),
    ("hereafter", "referred", "to", "as"),
    ("hereafter",),
    ("also", "known", "as"),
    ("otherwise", "known", "as"),
    ("also", "called"),
    ("referred", "to", "as"),
    ("abbreviated", "as"),
    ("abbreviated",),
    ("or", "simply"),
    ("for", "short"),
)

#: Cues where the short form comes **before** the cue: "GEF stands for the
#: Global Environment Facility".
CUES_SHORT_FORM_FIRST: tuple[tuple[str, ...], ...] = (
    ("stands", "for"),
    ("is", "short", "for"),
    ("is", "an", "abbreviation", "for"),
    ("is", "the", "abbreviation", "for"),
    ("is", "an", "acronym", "for"),
    ("is", "the", "acronym", "for"),
    ("is", "shorthand", "for"),
)

#: How many whitespace tokens of long form a cue may reach. **A constant, and
#: deliberately not a function of the short form's length** -- Schwartz &
#: Hearst's window is ``min(|SF| + 5, |SF| * 2)`` words, so making this depend on
#: ``|SF|`` would import half of the commitment this proposer exists to avoid.
CUE_WINDOW = 12

#: Suffixes that end a long form. Brackets are handled separately and are a
#: *stop*, never evidence -- the opposite of what S&H does with one.
_STOP_SUFFIXES = (".", ";", ":", "?", "!")
_BRACKETS = frozenset("()[]{}")

#: Trimmed off the front of a long form: function words an English long form
#: does not begin with. No character of the short form is consulted.
_LEADING_FUNCTION_WORDS = frozenset(
    {
        "a",
        "also",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "but",
        "by",
        "can",
        "could",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "may",
        "might",
        "of",
        "on",
        "or",
        "our",
        "shall",
        "she",
        "should",
        "so",
        "such",
        "than",
        "that",
        "the",
        "their",
        "then",
        "these",
        "they",
        "this",
        "those",
        "to",
        "was",
        "we",
        "were",
        "when",
        "which",
        "while",
        "will",
        "with",
        "would",
        "you",
    }
)


def _tokens(text: str) -> list[tuple[int, int, str]]:
    """Whitespace tokens as ``(start, end, surface)`` over ``text``."""
    return [(match.start(), match.end(), match.group()) for match in _TOKEN.finditer(text)]


def _core(start: int, _end: int, surface: str) -> Optional[tuple[int, int, str]]:
    """Strip non-alphanumeric edges from one token, keeping the offsets honest."""
    stripped = _EDGE_JUNK.sub("", surface)
    if not stripped:
        return None
    offset = surface.index(stripped)
    return start + offset, start + offset + len(stripped), stripped


def is_shape_short_form(surface: str) -> bool:
    """Does this token look like an abbreviation, on orthography alone?

    The shared task's own organisers' rule (``AAAI-22-SDU-shared-task-1-AE``,
    ``code/baseline.py``): at least two characters, and at least 60 % of its
    letters upper case. **Only the short-form half of that baseline is used
    here.** Its long-form half -- "if the initial characters of the preceding
    words can form the acronym" -- is a character alignment, which is the exact
    commitment this proposer must not make.
    """
    core = _EDGE_JUNK.sub("", surface)
    if len(core) < 2:
        return False
    letters = [character for character in core if character.isalpha()]
    if not letters:
        return False
    upper = sum(1 for character in letters if character.isupper())
    return upper / len(letters) >= 0.6


def is_all_caps(surface: str) -> bool:
    """``bench/run_spans.py``'s trivial rule, over a raw whitespace token.

    Kept character-for-character equivalent to ``predict_all_caps`` so the two
    runners' ``allcaps`` rows mean the same thing: length two or more, equal to
    its own upper case, and holding at least one letter.
    """
    return len(surface) >= 2 and surface == surface.upper() and any(c.isalpha() for c in surface)


def _trim_right(span: CharSpan, text: str) -> Optional[CharSpan]:
    """Drop trailing non-alphanumeric characters from a span."""
    start, end = span
    while end > start and not text[end - 1].isalnum():
        end -= 1
    return (start, end) if end > start else None


def _long_form_before(
    tokens: list[tuple[int, int, str]], stop: int, text: str
) -> Optional[CharSpan]:
    """The long form ending at token ``stop - 1``, walking left."""
    if stop <= 0:
        return None
    first = stop
    for index in range(stop - 1, max(-1, stop - 1 - CUE_WINDOW), -1):
        surface = tokens[index][2]
        if any(bracket in surface for bracket in _BRACKETS):
            break
        first = index
        if surface.endswith(_STOP_SUFFIXES):
            first = index + 1
            break
    while first < stop and _EDGE_JUNK.sub("", tokens[first][2]).lower() in _LEADING_FUNCTION_WORDS:
        first += 1
    if first >= stop:
        return None
    return _trim_right((tokens[first][0], tokens[stop - 1][1]), text)


def _long_form_after(
    tokens: list[tuple[int, int, str]], begin: int, text: str
) -> Optional[CharSpan]:
    """The long form beginning at token ``begin``, walking right."""
    if begin >= len(tokens):
        return None
    first = begin
    while (
        first < len(tokens)
        and _EDGE_JUNK.sub("", tokens[first][2]).lower() in _LEADING_FUNCTION_WORDS
    ):
        first += 1
    last = first - 1
    for index in range(first, min(len(tokens), first + CUE_WINDOW)):
        surface = tokens[index][2]
        if any(bracket in surface for bracket in _BRACKETS):
            break
        last = index
        if surface.endswith(_STOP_SUFFIXES) or surface.endswith(","):
            break
    if last < first:
        return None
    return _trim_right((tokens[first][0], tokens[last][1]), text)


def _matches_cue(lowered: Sequence[str], index: int, cue: Sequence[str]) -> bool:
    """Does the token run at ``index`` spell ``cue``, ignoring edge punctuation?"""
    if index + len(cue) > len(lowered):
        return False
    return all(
        _EDGE_JUNK.sub("", lowered[index + offset]) == word for offset, word in enumerate(cue)
    )


#: One entry of an abbreviation roster: a figure legend, a table footnote or an
#: "Abbreviations:" run. Three separators, no bracket anywhere in the pattern.
#: Anchored on a run start, a semicolon, a newline or a colon, which is what
#: makes it a *roster* reader rather than a comma reader.
_ROSTER_ITEM = re.compile(
    r"(?:^|[;\n:])[ \t]*([^\s;:=,()\[\]]{2,20})[ \t]*([:=,])[ \t]*([^;\n]{2,90})"
)

#: Rule names, spelled in words. The separator itself would be the obvious
#: label and cannot be used: the name reaches ``bench/results.json`` as part of a
#: field key, and ``tools/check_claims.py`` splits a citation on its first
#: ``:``, so a field called ``cue_fired_roster_:`` could never be cited. A key
#: nobody can cite is a measurement nobody may quote.
ROSTER_NAMES = {":": "roster_colon", ",": "roster_comma", "=": "roster_equals"}

#: A ``:`` or ``,`` roster entry is only believed when the passage holds at least
#: this many of them. One comma is a sentence; three in a semicolon-delimited run
#: is a legend. ``=`` is exempt because it is unambiguous on its own.
ROSTER_QUORUM = 2


def _roster_edges(text: str) -> list[tuple[CharSpan, CharSpan, str]]:
    """Read an abbreviation roster: ``SF: LF; SF: LF`` and ``SF = LF``.

    This is the third rule, and it exists because the measurement demanded it:
    the gold long forms no S&H descendant proposes are dominated by figure
    legends and table footnotes -- ``EPI = Echo planar imaging.``,
    ``BMI: body mass index; CE: cholesteryl ester; ...``,
    ``Abbreviations: Ct, cycle threshold; n/a, not applicable; ...``. With only
    the cue rule, ``shapecue`` proposed **three edges across every corpus this
    runner reads**, which is not a sample and cannot support an independence
    measurement (R12).

    It is independent on both axes, and both are checkable rather than asserted:
    the pattern contains no bracket, so it is outside Schwartz & Hearst's
    candidate generator, and it compares no character of the short form against
    the long form, so it is outside their validator.
    """
    candidates: list[tuple[CharSpan, CharSpan, str, str]] = []
    separators: dict[str, int] = {}
    for match in _ROSTER_ITEM.finditer(text):
        short, separator, long_form = match.group(1), match.group(2), match.group(3)
        # The quorum counts every entry of the shape, not every entry this
        # proposer would emit. Whether a region *is* a roster is evidence about
        # the region, and it does not depend on which of its rows happen to pass
        # an orthographic filter -- `Ct`, `nd` and `Unk` are all real
        # abbreviations that :func:`is_shape_short_form` refuses.
        separators[separator] = separators.get(separator, 0) + 1
        if not is_shape_short_form(short):
            continue
        if not any(character.isalpha() for character in long_form):
            continue
        short_span = (match.start(1), match.end(1))
        long_span = _trim_right((match.start(3), match.end(3)), text)
        if long_span is None:
            continue
        # A roster entry ends at the sentence that ends it, never inside one.
        stop = text.find(". ", long_span[0], long_span[1])
        if stop != -1:
            long_span = _trim_right((long_span[0], stop), text)
            if long_span is None:
                continue
        candidates.append((short_span, long_span, ROSTER_NAMES[separator], separator))
    return [
        (short_span, long_span, name)
        for short_span, long_span, name, separator in candidates
        if separator == "=" or separators.get(separator, 0) >= ROSTER_QUORUM
    ]


def propose_shapecue(text: str) -> tuple[list[CharSpan], list[tuple[CharSpan, CharSpan, str]]]:
    """Propose abbreviation vertices and edges without reading a bracket or a character.

    Two rules, reported separately because they behave completely differently:

    * **shape** -- every token whose orthography says "abbreviation"
      (:func:`is_shape_short_form`). Vertices only: a short-form span with no
      long form, which is what a pool of bracket scanners can never contain.
    * **cue** -- a lexical cue phrase links a short form to a long form. The
      long form's extent is a fixed token window trimmed at clause boundaries.
      **No character of the short form is compared against the long form at any
      point**, which is what makes an edge here un-derivable by
      :func:`sh_alignable` and therefore by any S&H descendant.

    Returns:
        ``(vertex_spans, edges)`` where each edge is
        ``(short_form_span, long_form_span, cue)``.
    """
    tokens = _tokens(text)
    lowered = [surface.lower() for _, _, surface in tokens]

    vertices: list[CharSpan] = []
    for token in tokens:
        if not is_shape_short_form(token[2]):
            continue
        core = _core(*token)
        if core is not None:
            vertices.append((core[0], core[1]))

    edges: list[tuple[CharSpan, CharSpan, str]] = []
    for index in range(len(tokens)):
        for cue in CUES_LONG_FORM_FIRST:
            if not _matches_cue(lowered, index, cue):
                continue
            after = index + len(cue)
            for offset in range(after, min(len(tokens), after + 3)):
                if not is_shape_short_form(tokens[offset][2]):
                    continue
                core = _core(*tokens[offset])
                long_span = _long_form_before(tokens, index, text)
                if core is not None and long_span is not None:
                    edges.append(((core[0], core[1]), long_span, " ".join(cue)))
                break
            break
        for cue in CUES_SHORT_FORM_FIRST:
            if not _matches_cue(lowered, index, cue):
                continue
            for offset in range(index - 1, max(-1, index - 4), -1):
                if not is_shape_short_form(tokens[offset][2]):
                    continue
                core = _core(*tokens[offset])
                long_span = _long_form_after(tokens, index + len(cue), text)
                if core is not None and long_span is not None:
                    edges.append(((core[0], core[1]), long_span, " ".join(cue)))
                break
            break
    edges.extend(_roster_edges(text))
    return vertices, edges


def propose_allcaps(text: str) -> list[CharSpan]:
    """Vertices only, by the all-caps rule, over character offsets."""
    spans: list[CharSpan] = []
    for token in _tokens(text):
        if not is_all_caps(token[2]):
            continue
        core = _core(*token)
        if core is not None:
            spans.append((core[0], core[1]))
    return spans


# ---------------------------------------------------------------------------
# 3. One representation for three corpora
# ---------------------------------------------------------------------------
_WHITESPACE = re.compile(r"\s+")


def normalise(value: str) -> str:
    """Whitespace-collapse and case-fold, as ``bench/scoring.py`` does."""
    return _WHITESPACE.sub(" ", value).strip().casefold()


class Passage:
    """One text with its gold spans, in **character offsets**, whatever the source.

    Three corpora with three native annotation units meet here: PLOD ships token
    indices, SDU@AAAI-22 AE ships character offsets, MED1250 ships pairs of
    strings and no offsets at all. A cross-corpus finding computed under three
    conventions is not a cross-corpus finding, so every one is projected into
    character offsets over running text before anything is counted.

    The projection costs something and the cost is named: PLOD's published
    numbers in ``bench/results.json`` under ``spans.plod.*`` are **token**-space
    and are not comparable to the ones here.
    """

    __slots__ = ("gold_long", "gold_pairs", "gold_short", "text", "uid")

    def __init__(
        self,
        uid: str,
        text: str,
        gold_short: Sequence[CharSpan] = (),
        gold_long: Sequence[CharSpan] = (),
        gold_pairs: Sequence[Pair] = (),
    ) -> None:
        self.uid = uid
        self.text = text
        self.gold_short = tuple(gold_short)
        self.gold_long = tuple(gold_long)
        self.gold_pairs = tuple(gold_pairs)

    def surface(self, span: CharSpan) -> str:
        """The text a span covers."""
        return self.text[span[0] : span[1]]


#: The corpora this runner can read, with the provenance claim each one carries.
#: ``pooled_gold`` is the field the whole exercise turns on: ``True`` means the
#: gold standard was assembled by pooling the systems under test, which makes a
#: union gain measured on it circular.
CORPORA: dict[str, dict[str, object]] = {
    "plod_all": {
        "corpus": "plod_cw_all",
        "gold_provenance": "PLOS article Abbreviations sections, matched onto body text",
        "pooled_gold": False,
        "role": "held_out",
    },
    "plod_test": {
        "corpus": "plod_cw_test",
        "gold_provenance": "PLOS article Abbreviations sections, matched onto body text",
        "pooled_gold": False,
        "role": "held_out",
    },
    "sdu22_legal_dev": {
        "corpus": "sdu22_ae_legal",
        "gold_provenance": "human annotators, inter-annotator agreement published",
        "pooled_gold": False,
        "role": "tuning",
    },
    "sdu22_scientific_dev": {
        "corpus": "sdu22_ae_scientific",
        "gold_provenance": "human annotators, inter-annotator agreement published",
        "pooled_gold": False,
        "role": "tuning",
    },
    "med1250": {
        "corpus": "med1250",
        "gold_provenance": "Ab3P's own evaluation corpus; pyab3p in this table IS Ab3P",
        "pooled_gold": True,
        "role": "tuning",
    },
}


def load_passages(key: str) -> list[Passage]:
    """Read one corpus into :class:`Passage` objects.

    Raises:
        SystemExit: For an unknown key, or a corpus whose files are absent.
    """
    from bench import corpora

    if key in ("plod_all", "plod_test"):
        # `read_sdu22_ae` and `load` both consult `bench/splits.toml` before they
        # open anything; `read_plod_cw` does not, and neither does
        # `bench/run_spans.py`, which is the reader this one is modelled on. The
        # lookup is done here rather than left out, because the whole point of
        # this runner is a cross-corpus comparison and one corpus opened without
        # its declaration is one corpus whose role and contamination nobody
        # checked. The gap in `bench/corpora.py` is reported, not patched (R8).
        corpora.declaration("plod")
        split = "all" if key == "plod_all" else "test"
        passages = []
        for document in corpora.read_plod_cw(split=split):
            text, offsets = document.render("tight")
            passages.append(
                Passage(
                    document.uid,
                    text,
                    [(offsets[a][0], offsets[b - 1][1]) for a, b in document.short_form_spans],
                    [(offsets[a][0], offsets[b - 1][1]) for a, b in document.long_form_spans],
                )
            )
        return passages

    if key.startswith("sdu22_"):
        domain = "legal" if "legal" in key else "scientific"
        return [
            Passage(d.uid, d.text, d.short_form_spans, d.long_form_spans)
            for d in corpora.read_sdu22_ae(domain=domain, split="dev")
        ]

    if key == "med1250":
        return [
            Passage(d.uid, d.text, gold_pairs=[(p.short_form, p.long_form) for p in d.pairs])
            for d in corpora.load("med1250")
        ]

    raise SystemExit(f"unknown corpus {key!r}; known: {sorted(CORPORA)}")


# ---------------------------------------------------------------------------
# 4. Running the proposers
# ---------------------------------------------------------------------------
class Proposals:
    """What one proposer said about one corpus.

    Attributes:
        short_spans: ``{uid: [char span, ...]}`` -- every abbreviation surface
            proposed, whether or not it carries a long form.
        long_spans: The same for long forms.
        edges: ``{uid: [(short, long), ...]}`` as strings, which is the unit the
            Federal Register pool's ``93.74 %`` was computed in.
    """

    __slots__ = (
        "edge_spans",
        "edges",
        "elapsed_seconds",
        "long_spans",
        "notes",
        "short_spans",
    )

    def __init__(self) -> None:
        self.short_spans: dict[str, list[CharSpan]] = {}
        self.long_spans: dict[str, list[CharSpan]] = {}
        self.edges: dict[str, list[Pair]] = {}
        self.edge_spans: dict[str, list[tuple[CharSpan, CharSpan]]] = {}
        self.elapsed_seconds = 0.0
        self.notes: dict[str, object] = {}


def _distinct(spans: Sequence[CharSpan]) -> list[CharSpan]:
    """Drop repeats and empties, order preserved. Applied to every proposer alike."""
    seen: set[CharSpan] = set()
    kept: list[CharSpan] = []
    for span in spans:
        if span[1] > span[0] and span not in seen:
            seen.add(span)
            kept.append(span)
    return kept


def _occurrences(text: str, needle: str) -> list[CharSpan]:
    """Every place ``needle`` appears, verbatim first then whitespace-flexibly."""
    if not needle:
        return []
    found: list[CharSpan] = []
    start = text.find(needle)
    while start != -1:
        found.append((start, start + len(needle)))
        start = text.find(needle, start + 1)
    if found:
        return found
    parts = [part for part in _WHITESPACE.split(needle.strip()) if part]
    if not parts:
        return []
    pattern = r"\s*".join(re.escape(part) for part in parts)
    return [(m.start(), m.end()) for m in re.finditer(pattern, text)]


def locate_pair(text: str, short: str, long_form: str) -> Optional[tuple[CharSpan, CharSpan]]:
    """The occurrence of each form that best explains them as one definition.

    Identical in behaviour to ``bench/run_spans.py``'s function of the same name,
    and re-stated here rather than imported because this module has to load under
    a foreign interpreter that has never heard of ``acronymkit``. Ties break
    leftmost, so it is deterministic.
    """
    shorts = _occurrences(text, short)
    longs = _occurrences(text, long_form)
    if not shorts or not longs:
        return None
    ranked = [
        (max(0, max(s[0], lf[0]) - min(s[1], lf[1])), s[0], lf[0], s, lf)
        for s in shorts
        for lf in longs
    ]
    _, _, _, best_short, best_long = min(ranked)
    return best_short, best_long


def from_string_pairs(
    passages: Sequence[Passage], predicted: dict[str, list[Pair]]
) -> tuple[Proposals, int, int]:
    """Localise ``(short, long)`` strings into spans, uniformly for every system.

    Returns:
        ``(proposals, unlocated, total)``. Losses are counted rather than
        absorbed: a localiser that quietly drops predictions would understate
        whichever system phrases its output least literally.
    """
    proposals = Proposals()
    unlocated = 0
    total = 0
    for passage in passages:
        shorts: list[CharSpan] = []
        longs: list[CharSpan] = []
        edges: list[Pair] = []
        edge_spans: list[tuple[CharSpan, CharSpan]] = []
        for short, long_form in predicted.get(passage.uid, []):
            total += 1
            edges.append((short, long_form))
            found = locate_pair(passage.text, short, long_form)
            if found is None:
                unlocated += 1
                continue
            shorts.append(found[0])
            longs.append(found[1])
            edge_spans.append(found)
        proposals.short_spans[passage.uid] = _distinct(shorts)
        proposals.long_spans[passage.uid] = _distinct(longs)
        proposals.edges[passage.uid] = edges
        proposals.edge_spans[passage.uid] = edge_spans
    return proposals, unlocated, total


def run_acronymkit(passages: Sequence[Passage], profile: str) -> Proposals:
    """One acronymkit operating point, through the same localiser as everyone."""
    from acronymkit import AcronymEngine, Config
    from acronymkit.enums import ExtractionProfile

    engine = AcronymEngine(Config.for_profile(ExtractionProfile[profile.upper()]))
    started = time.perf_counter()
    predicted = {
        passage.uid: [
            (pair.short_form, pair.long_form) for pair in engine.extract_definitions(passage.text)
        ]
        for passage in passages
    }
    elapsed = time.perf_counter() - started
    proposals, unlocated, total = from_string_pairs(passages, predicted)
    proposals.elapsed_seconds = elapsed
    proposals.notes = {"unlocated_pairs": unlocated, "offered_pairs": total}
    return proposals


def run_external(passages: Sequence[Passage], system: str, interpreter: str) -> Proposals:
    """Drive one competing extractor under a foreign interpreter.

    The texts are handed over as JSON rather than by corpus name, which is what
    lets the character-span corpora take part: ``bench/external.py`` can only
    load a corpus registered in ``bench.corpora.READERS``, and SDU@AAAI-22 AE is
    deliberately not in it.
    """
    with tempfile.TemporaryDirectory() as directory:
        payload = Path(directory) / "texts.json"
        payload.write_text(json.dumps({p.uid: p.text for p in passages}), encoding="utf-8")
        command = [
            interpreter,
            str(Path(__file__).resolve()),
            "--external-worker",
            system,
            "--texts",
            str(payload),
        ]
        # `encoding` and `errors` are not decoration. Without them Windows
        # decodes both pipes with the console code page, and a single byte a
        # baseline happens to print on **stderr** kills the reader thread with
        # `UnicodeDecodeError` -- observed, from `scispacy`, at 13 kB into its
        # warnings. The payload itself is `ensure_ascii` JSON and was never at
        # risk; the run was, and a run that dies on a warning's punctuation is
        # not a measurement instrument. `PYTHONIOENCODING` pins the child's end
        # of the same pipe rather than trusting the same code page twice.
        child_environment = dict(os.environ, PYTHONIOENCODING="utf-8")
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=child_environment,
        )
    if completed.returncode != 0:
        raise SystemExit(f"{system} failed under {interpreter}:\n{completed.stderr[-2000:]}")
    body = json.loads(completed.stdout)
    predicted = {uid: [(a, b) for a, b in pairs] for uid, pairs in body["predictions"].items()}
    proposals, unlocated, total = from_string_pairs(passages, predicted)
    proposals.elapsed_seconds = body["elapsed_seconds"]
    proposals.notes = {"unlocated_pairs": unlocated, "offered_pairs": total}
    return proposals


def run_allcaps(passages: Sequence[Passage]) -> Proposals:
    """The trivial independent rule: vertices only, no long forms ever."""
    proposals = Proposals()
    started = time.perf_counter()
    for passage in passages:
        proposals.short_spans[passage.uid] = _distinct(propose_allcaps(passage.text))
        proposals.long_spans[passage.uid] = []
        proposals.edges[passage.uid] = []
        proposals.edge_spans[passage.uid] = []
    proposals.elapsed_seconds = time.perf_counter() - started
    proposals.notes = {"unlocated_pairs": 0, "offered_pairs": 0}
    return proposals


def run_shapecue(passages: Sequence[Passage]) -> Proposals:
    """This runner's independent proposer, with its rules' firing counts (R12)."""
    proposals = Proposals()
    cue_firings: dict[str, int] = {}
    started = time.perf_counter()
    for passage in passages:
        vertices, edges = propose_shapecue(passage.text)
        shorts = list(vertices)
        longs: list[CharSpan] = []
        strings: list[Pair] = []
        spans: list[tuple[CharSpan, CharSpan]] = []
        for short_span, long_span, cue in edges:
            cue_firings[cue] = cue_firings.get(cue, 0) + 1
            shorts.append(short_span)
            longs.append(long_span)
            spans.append((short_span, long_span))
            strings.append((passage.surface(short_span), passage.surface(long_span)))
        proposals.short_spans[passage.uid] = _distinct(shorts)
        proposals.long_spans[passage.uid] = _distinct(longs)
        proposals.edges[passage.uid] = strings
        proposals.edge_spans[passage.uid] = spans
    proposals.elapsed_seconds = time.perf_counter() - started
    proposals.notes = {
        "unlocated_pairs": 0,
        "offered_pairs": sum(len(v) for v in proposals.edges.values()),
        "cue_firings_total": sum(cue_firings.values()),
        "cue_firings_distinct_cues": len(cue_firings),
    }
    for cue, count in sorted(cue_firings.items()):
        proposals.notes[f"cue_fired_{cue.replace(' ', '_')}"] = count
    return proposals


# ---------------------------------------------------------------------------
# 5. The foreign-interpreter worker
# ---------------------------------------------------------------------------
def external_worker(system: str, texts_path: str) -> int:
    """Run one baseline over ``{uid: text}`` and print predictions as JSON.

    Runs under a *different* interpreter from the rest of this file, so it must
    touch nothing but the standard library and the baseline itself. Everything
    above this point that it reaches is pure stdlib for the same reason.
    """
    payload = json.loads(Path(texts_path).read_text(encoding="utf-8"))
    uids = list(payload)
    texts = [payload[uid] for uid in uids]

    def _abbreviations(items: Sequence[str]) -> list[list[Pair]]:
        from abbreviations import schwartz_hearst

        return [
            list(schwartz_hearst.extract_abbreviation_definition_pairs(doc_text=text).items())
            for text in items
        ]

    def _abbreviation_extractor(items: Sequence[str]) -> list[list[Pair]]:
        import abbreviation_extractor

        return [
            [
                (found.abbreviation, found.definition)
                for found in abbreviation_extractor.extract_abbreviation_definition_pairs(text)
            ]
            for text in items
        ]

    def _pyab3p(items: Sequence[str]) -> list[list[Pair]]:
        import pyab3p

        engine = pyab3p.Ab3p()
        return [[(a.short_form, a.long_form) for a in engine.get_abbrs(text)] for text in items]

    def _scispacy(items: Sequence[str]) -> list[list[Pair]]:
        import spacy
        from scispacy.abbreviation import AbbreviationDetector  # noqa: F401

        try:
            nlp = spacy.load("en_core_sci_sm", disable=["ner", "lemmatizer", "tagger"])
        except OSError:
            nlp = spacy.blank("en")
        if "abbreviation_detector" not in nlp.pipe_names:
            nlp.add_pipe("abbreviation_detector")
        return [
            [(str(a), str(a._.long_form)) for a in doc._.abbreviations]
            for doc in nlp.pipe(items, batch_size=64)
        ]

    predictors = {
        "abbreviations": _abbreviations,
        "abbreviation_extractor": _abbreviation_extractor,
        "pyab3p": _pyab3p,
        "scispacy": _scispacy,
    }
    started = time.perf_counter()
    predicted = predictors[system](texts)
    elapsed = time.perf_counter() - started
    json.dump(
        {
            "system": system,
            "interpreter": sys.version.split()[0],
            "elapsed_seconds": elapsed,
            "predictions": {
                uid: [[short, long_form] for short, long_form in pairs]
                for uid, pairs in zip(uids, predicted)
            },
        },
        sys.stdout,
    )
    return 0


# ---------------------------------------------------------------------------
# 6. Overlap, union gain, and the gold class
# ---------------------------------------------------------------------------
def vertex_keys(proposals: Proposals, passages: Sequence[Passage]) -> set[tuple[str, str]]:
    """``{(uid, casefolded short form)}`` -- the unit a vertex is counted in."""
    by_uid = {passage.uid: passage for passage in passages}
    keys: set[tuple[str, str]] = set()
    for uid, spans in proposals.short_spans.items():
        passage = by_uid.get(uid)
        if passage is None:
            continue
        for span in spans:
            keys.add((uid, normalise(passage.surface(span))))
    return keys


def edge_keys(proposals: Proposals) -> set[tuple[str, str, str]]:
    """``{(uid, short, long)}`` normalised -- D-056's unit, so the two agree."""
    return {
        (uid, normalise(short), normalise(long_form))
        for uid, pairs in proposals.edges.items()
        for short, long_form in pairs
        if short and long_form
    }


def overlap_record(sets: dict[str, set], unit: str, context: dict) -> dict:
    """The pairwise overlap matrix and the union gain per proposer (R13).

    Every cell is a count, and the derived percentages are named so a reader can
    tell which denominator each uses:

    * ``share_pct_<system>`` -- that system's proposals as a share of the union.
      This is the ``93.74 %`` statistic of D-056, recomputed here.
    * ``union_gain_pct_<system>`` -- what the union LOSES if that system is
      removed, as a share of the full union. This is the number that says
      whether a proposer is doing anything, and a proposer under a few percent
      is decoration.
    * ``jaccard_<a>__<b>`` -- symmetric agreement, so a large system and a small
      one are not compared by raw overlap alone.
    """
    names = sorted(sets)
    union: set = set()
    for name in names:
        union |= sets[name]
    record: dict = dict(context)
    record["unit"] = unit
    record["proposers"] = names
    record["union_total"] = len(union)
    for name in names:
        others: set = set()
        for other in names:
            if other != name:
                others |= sets[other]
        unique = sets[name] - others
        record[f"n_{name}"] = len(sets[name])
        record[f"share_pct_{name}"] = round(100 * len(sets[name]) / max(len(union), 1), 2)
        record[f"unique_{name}"] = len(unique)
        record[f"union_gain_pct_{name}"] = round(100 * len(unique) / max(len(union), 1), 2)
    for index, first in enumerate(names):
        for second in names[index + 1 :]:
            both = len(sets[first] & sets[second])
            either = len(sets[first] | sets[second])
            record[f"overlap_{first}__{second}"] = both
            record[f"jaccard_{first}__{second}"] = round(100 * both / max(either, 1), 2)
    family = sh_family(names)
    if family:
        family_union: set = set()
        for name in family:
            family_union |= sets[name]
        record["sh_family"] = family
        record["sh_family_union_total"] = len(family_union)
        record["sh_family_share_pct"] = round(100 * len(family_union) / max(len(union), 1), 2)
        record["independent_gain_pct"] = round(
            100 * len(union - family_union) / max(len(union), 1), 2
        )
    return record


def alignment_record(
    proposals: dict[str, Proposals], passages: Sequence[Passage], context: dict
) -> dict:
    """How many of each proposer's edges Schwartz & Hearst would refuse.

    This is the mechanical half of the independence argument. A system that
    validates with :func:`sh_alignable` cannot emit an edge that fails it, so
    ``sh_unalignable_pct`` is ``0.00`` for every descendant **by construction and
    not by measurement** -- the row is there to show the instrument firing, and
    the number that carries information is the independent proposer's.
    """
    by_uid = {passage.uid: passage for passage in passages}
    record: dict = dict(context)
    for name, proposal in sorted(proposals.items()):
        edges = [pair for pairs in proposal.edges.values() for pair in pairs]
        unalignable = sum(1 for short, long_form in edges if not sh_alignable(short, long_form))
        located = 0
        bracketless = 0
        for uid, spans in proposal.edge_spans.items():
            passage = by_uid.get(uid)
            if passage is None:
                continue
            for short_span, _ in spans:
                located += 1
                if not bracket_adjacent(passage.text, short_span):
                    bracketless += 1
        record[f"edges_{name}"] = len(edges)
        record[f"sh_unalignable_{name}"] = unalignable
        record[f"sh_unalignable_pct_{name}"] = round(100 * unalignable / max(len(edges), 1), 2)
        record[f"located_edges_{name}"] = located
        record[f"bracketless_edges_{name}"] = bracketless
        record[f"bracketless_edges_pct_{name}"] = round(100 * bracketless / max(located, 1), 2)
    return record


def _span_set(span: CharSpan) -> frozenset:
    """A character span as the set of offsets it covers."""
    return frozenset(range(span[0], span[1]))


def matched_gold(
    gold: Sequence[CharSpan], predicted: Sequence[CharSpan], convention: str
) -> set[int]:
    """Indices of the gold spans a proposer got, matched one-to-one.

    ``exact`` needs identical offsets; ``overlap`` needs a shared character and
    consumes the gold span it claims, so one sprawling prediction cannot claim
    several. Greedy in corpus order, which is equivalent to a maximum matching
    here because gold spans within a passage are disjoint.
    """
    gold_sets = [_span_set(span) for span in gold]
    claimed: set[int] = set()
    for span in predicted:
        candidate = _span_set(span)
        for index, gold_span in enumerate(gold_sets):
            if index in claimed:
                continue
            hit = candidate == gold_span if convention == "exact" else bool(candidate & gold_span)
            if hit:
                claimed.add(index)
                break
    return claimed


def score_spans(
    passages: Sequence[Passage], proposal: Proposals, label: str, convention: str
) -> dict[str, float]:
    """Precision, recall and F1 for one proposer against one gold label.

    Independence without coverage is a curiosity, so every proposer carries this
    beside its independence figures. ``allcaps`` and ``shapecue`` are scored on
    exactly the same gold, by exactly the same matcher, as the systems they are
    being compared against.
    """
    true_positives = 0
    predicted_total = 0
    gold_total = 0
    for passage in passages:
        gold = passage.gold_short if label == "short_form" else passage.gold_long
        source = proposal.short_spans if label == "short_form" else proposal.long_spans
        predicted = source.get(passage.uid, [])
        gold_total += len(gold)
        predicted_total += len(predicted)
        true_positives += len(matched_gold(gold, predicted, convention))
    precision = true_positives / predicted_total if predicted_total else 0.0
    recall = true_positives / gold_total if gold_total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        f"{label}.{convention}_true_positives": true_positives,
        f"{label}.{convention}_false_positives": predicted_total - true_positives,
        f"{label}.{convention}_false_negatives": gold_total - true_positives,
        f"{label}.{convention}_precision": round(100 * precision, 2),
        f"{label}.{convention}_recall": round(100 * recall, 2),
        f"{label}.{convention}_f1": round(100 * f1, 2),
    }


def gold_reach(
    passages: Sequence[Passage],
    proposals: dict[str, Proposals],
    label: str,
    convention: str,
) -> dict[str, set[tuple[str, int]]]:
    """Which gold spans each proposer reached, as ``{system: {(uid, index)}}``."""
    reached: dict[str, set[tuple[str, int]]] = {name: set() for name in proposals}
    for passage in passages:
        gold = passage.gold_short if label == "short_form" else passage.gold_long
        if not gold:
            continue
        for name, proposal in proposals.items():
            source = proposal.short_spans if label == "short_form" else proposal.long_spans
            for index in matched_gold(gold, source.get(passage.uid, []), convention):
                reached[name].add((passage.uid, index))
    return reached


_OPEN_BRACKETS = frozenset("([{")
_CLOSE_BRACKETS = frozenset(")]}")


def bracket_adjacent(text: str, span: CharSpan) -> bool:
    """Could a *parenthetical* algorithm reach this span at all?

    True when the span sits immediately inside a bracket, or immediately in
    front of one. Both arrangements count, which is deliberately the generous
    reading: counting only ``long form (SF)`` would shrink the denominator and
    flatter every S&H descendant in the table.
    """
    start, end = span
    before = start - 1
    while before >= 0 and text[before].isspace():
        before -= 1
    after = end
    while after < len(text) and text[after].isspace():
        after += 1
    opened = before >= 0 and text[before] in _OPEN_BRACKETS
    closed = after < len(text) and text[after] in _CLOSE_BRACKETS
    follows = after < len(text) and text[after] in _OPEN_BRACKETS
    return opened or closed or follows


def gold_class_record(
    passages: Sequence[Passage],
    proposals: dict[str, Proposals],
    label: str,
    convention: str,
    context: dict,
) -> dict:
    """The class of gold spans NO Schwartz & Hearst descendant proposes.

    The headline is ``unproposed_pct``: the share of this corpus's gold that the
    **union** of every S&H descendant present fails to reach. It is decomposed,
    because the raw figure conflates three very different things and quoting it
    undecomposed would be the strongest available misreading:

    ``surface_proposed_in_passage``
        The same abbreviation string *is* proposed by the pool elsewhere in the
        same passage -- a repeat mention. This is an annotation-convention
        mismatch (the corpus tags every occurrence; a definition extractor emits
        one span per definition) and it is **not** an algorithmic blind spot.
    ``surface_proposed_in_corpus``
        Proposed somewhere else in the corpus but not here.
    ``never_proposed_anywhere``
        No S&H descendant proposed this string anywhere in the corpus. This is
        the blind spot proper.
    ``bracket_adjacent``
        Cross-cuts all three: whether a parenthetical algorithm could have
        reached the span at all. A gold span that is not bracket-adjacent is
        outside the S&H candidate generator by construction, whatever its
        validator would have said.

    For long forms one more column is computed and it is the sharpest one:
    ``alignable_from_gold_short_form`` counts unreached long forms that some gold
    short form in the same passage *does* align into under :func:`sh_alignable`.
    Those are pairs S&H's **validator** would accept and its **candidate
    generator** never offers, which separates the two commitments empirically
    rather than by argument.
    """
    family = sh_family(sorted(proposals))
    if not family:
        raise SystemExit("no Schwartz & Hearst descendant present; nothing to measure against")
    reach = gold_reach(passages, proposals, label, convention)
    family_union: set[tuple[str, int]] = set()
    for name in family:
        family_union |= reach[name]
    everything: set[tuple[str, int]] = set()
    for name in proposals:
        everything |= reach[name]

    proposed_by_passage: dict[str, set[str]] = {}
    proposed_in_corpus: set[str] = set()
    by_uid = {passage.uid: passage for passage in passages}
    for name in family:
        source = (
            proposals[name].short_spans if label == "short_form" else proposals[name].long_spans
        )
        for uid, spans in source.items():
            passage = by_uid.get(uid)
            if passage is None:
                continue
            bucket = proposed_by_passage.setdefault(uid, set())
            for span in spans:
                surface = normalise(passage.surface(span))
                bucket.add(surface)
                proposed_in_corpus.add(surface)

    total = 0
    unproposed = 0
    buckets = {
        "bracket_adjacent": 0,
        "surface_proposed_in_passage": 0,
        "surface_proposed_in_corpus": 0,
        "never_proposed_anywhere": 0,
        "alignable_from_gold_short_form": 0,
        "reached_by_an_independent_proposer": 0,
    }
    examples: list[str] = []
    alignable_examples: list[str] = []
    for passage in passages:
        gold = passage.gold_short if label == "short_form" else passage.gold_long
        for index, span in enumerate(gold):
            total += 1
            if (passage.uid, index) in family_union:
                continue
            unproposed += 1
            surface = normalise(passage.surface(span))
            if bracket_adjacent(passage.text, span):
                buckets["bracket_adjacent"] += 1
            if surface in proposed_by_passage.get(passage.uid, ()):
                buckets["surface_proposed_in_passage"] += 1
            elif surface in proposed_in_corpus:
                buckets["surface_proposed_in_corpus"] += 1
            else:
                buckets["never_proposed_anywhere"] += 1
                if len(examples) < 25:
                    examples.append(passage.surface(span))
            if label == "long_form":
                aligned = [
                    passage.surface(short_span)
                    for short_span in passage.gold_short
                    if sh_alignable(passage.surface(short_span), passage.surface(span))
                ]
                if aligned:
                    buckets["alignable_from_gold_short_form"] += 1
                    if len(alignable_examples) < 25:
                        alignable_examples.append(f"{aligned[0]} <- {passage.surface(span)}")
            if (passage.uid, index) in everything:
                buckets["reached_by_an_independent_proposer"] += 1

    record: dict = dict(context)
    record["label"] = label
    record["convention"] = convention
    record["sh_family"] = family
    record["gold_spans"] = total
    record["reached_by_sh_family"] = len(family_union)
    record["sh_family_recall_pct"] = round(100 * len(family_union) / max(total, 1), 2)
    record["unproposed"] = unproposed
    record["unproposed_pct"] = round(100 * unproposed / max(total, 1), 2)
    record["reached_by_all_proposers"] = len(everything)
    record["all_proposers_recall_pct"] = round(100 * len(everything) / max(total, 1), 2)
    for name, count in buckets.items():
        if label == "short_form" and name == "alignable_from_gold_short_form":
            continue
        record[f"unproposed_{name}"] = count
        record[f"unproposed_{name}_pct_of_gold"] = round(100 * count / max(total, 1), 2)
    record["examples_never_proposed_anywhere"] = examples
    if label == "long_form":
        record["examples_unproposed_but_alignable"] = alignable_examples
    return record


def gold_pair_record(
    passages: Sequence[Passage], proposals: dict[str, Proposals], context: dict
) -> dict:
    """MED1250's gold is pairs, not spans, so it gets its own reach computation.

    Exact match on both forms after whitespace collapse and case folding, which
    is ``bench/scoring.py``'s ``exact`` convention. This row is the control: on
    the corpus these systems were built and tuned against, the pool should reach
    most of the gold, and if it does not the instrument is wrong rather than the
    field.
    """
    gold = {
        (passage.uid, normalise(short), normalise(long_form))
        for passage in passages
        for short, long_form in passage.gold_pairs
    }
    reach = {name: edge_keys(proposal) & gold for name, proposal in proposals.items()}
    record = overlap_record(reach, "gold pair reached", {**context, "gold_pairs": len(gold)})
    record["union_recall_pct"] = round(100 * record["union_total"] / max(len(gold), 1), 2)
    family_union: set = set()
    for name in sh_family(sorted(reach)):
        family_union |= reach[name]
    record["sh_family_recall_pct"] = round(100 * len(family_union) / max(len(gold), 1), 2)
    return record


def corpus_record(key: str, passages: Sequence[Passage], context: dict) -> dict:
    """What the corpus is, before any system touches it.

    The load-bearing columns are the bracket-adjacency ones, and they answer the
    thesis **without needing a proposer at all**. If a corpus's gold is almost
    entirely parenthetical then that corpus cannot reward -- or even see -- a
    system that reads a definition written any other way, whatever that system
    does. Read across corpora, this column says whether the gold standard was
    drawn around what a parenthetical algorithm can reach.

    ``gold_pairs_*`` exists because MED1250 annotates definitions rather than
    occurrences, so its short-form spans have to be located before they can be
    asked the same question. The long-form column is the honest cross-corpus
    comparison: **every** corpus here annotates a long form only where a
    definition is present, so that column compares definitions with definitions,
    while the short-form column compares definitions against every occurrence.
    """
    short_spans = sum(len(p.gold_short) for p in passages)
    long_spans = sum(len(p.gold_long) for p in passages)
    record: dict = {**context, **CORPORA[key]}
    record["passages"] = len(passages)
    record["characters"] = sum(len(p.text) for p in passages)
    record["gold_short_form_spans"] = short_spans
    record["gold_long_form_spans"] = long_spans
    record["gold_pairs"] = sum(len(p.gold_pairs) for p in passages)

    for label, spans_of in (
        ("short_form", lambda passage: passage.gold_short),
        ("long_form", lambda passage: passage.gold_long),
    ):
        total = sum(len(spans_of(passage)) for passage in passages)
        bracketed = sum(
            1
            for passage in passages
            for span in spans_of(passage)
            if bracket_adjacent(passage.text, span)
        )
        record[f"gold_{label}_spans_bracket_adjacent"] = bracketed
        record[f"gold_{label}_spans_bracket_adjacent_pct"] = round(
            100 * bracketed / max(total, 1), 2
        )

    located = 0
    short_bracketed = 0
    long_bracketed = 0
    for passage in passages:
        for short, long_form in passage.gold_pairs:
            found = locate_pair(passage.text, short, long_form)
            if found is None:
                continue
            located += 1
            short_bracketed += bracket_adjacent(passage.text, found[0])
            long_bracketed += bracket_adjacent(passage.text, found[1])
    record["gold_pairs_located"] = located
    record["gold_pairs_short_form_bracket_adjacent"] = short_bracketed
    record["gold_pairs_short_form_bracket_adjacent_pct"] = round(
        100 * short_bracketed / max(located, 1), 2
    )
    record["gold_pairs_long_form_bracket_adjacent"] = long_bracketed
    record["gold_pairs_long_form_bracket_adjacent_pct"] = round(
        100 * long_bracketed / max(located, 1), 2
    )
    return record


# ---------------------------------------------------------------------------
# 7. The independence demonstration
# ---------------------------------------------------------------------------
#: A sentence whose abbreviation shares **no character** with its own long form.
#: Every Schwartz & Hearst descendant must refuse it, because
#: :func:`sh_alignable` refuses it; ``shapecue`` proposes it, because it compares
#: no characters. This is the demonstration, not an illustration of one.
DISJOINT_CASE = "The Bureau of Weights, hereinafter QQQ, met in June."

#: The canonical Schwartz & Hearst arrangement, with no cue anywhere.
#: ``shapecue`` must propose no edge here at all, which is the other half: it
#: does not generate candidates from a bracketed window.
PARENTHETICAL_CASE = "We used the World Health Organization (WHO) criteria."


def demonstrate() -> str:
    """Print the two cases that make the independence claim falsifiable."""
    lines = ["independence demonstration", "=" * 60, ""]
    _, edges = propose_shapecue(DISJOINT_CASE)
    lines.append(f"  case 1, no shared character: {DISJOINT_CASE!r}")
    for short_span, long_span, cue in edges:
        short = DISJOINT_CASE[short_span[0] : short_span[1]]
        long_form = DISJOINT_CASE[long_span[0] : long_span[1]]
        lines.append(f"    shapecue proposes  {short!r} <- {long_form!r}   (cue {cue!r})")
        lines.append(f"    sh_alignable       {sh_alignable(short, long_form)}")
    if not edges:
        lines.append("    shapecue proposed NOTHING -- the demonstration has failed")
    lines.append("")
    _, edges = propose_shapecue(PARENTHETICAL_CASE)
    lines.append(f"  case 2, canonical parenthetical: {PARENTHETICAL_CASE!r}")
    lines.append(f"    shapecue edges proposed: {len(edges)} (must be 0)")
    lines.append(
        f"    sh_alignable('WHO', 'World Health Organization'): "
        f"{sh_alignable('WHO', 'World Health Organization')}"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 8. Entry point
# ---------------------------------------------------------------------------
def environment() -> str:
    """Interpreter and platform, in the exact wording every other runner uses.

    Deliberately identical to ``bench/run_extraction.py``'s: the string is a
    single shared top-level key in ``bench/results.json``, so a runner that
    phrases it differently rewrites a field that belongs to every other run in
    the file.
    """
    import platform

    return f"Python {platform.python_version()} on {platform.system()} {platform.machine()}"


def save_results(entries: dict) -> Path:
    """Merge ``entries`` into ``bench/results.json``, the one file claims may cite."""
    path = REPO_ROOT / "bench" / "results.json"
    document = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"runs": {}}
    document.setdefault("runs", {}).update(entries)
    document["environment"] = environment()
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return path


def render_matrix(record: dict) -> str:
    """The pairwise overlap matrix as a square table, plus the gain column."""
    names = list(record["proposers"])
    width = max(len(name) for name in names) + 2
    header = f"{'':<{width}}" + "".join(f"{name[:9]:>10}" for name in names)
    lines = [header, "-" * len(header)]
    for first in names:
        cells = []
        for second in names:
            if first == second:
                cells.append(f"{record[f'n_{first}']:>10,}")
            else:
                key = (
                    f"overlap_{first}__{second}"
                    if f"overlap_{first}__{second}" in record
                    else f"overlap_{second}__{first}"
                )
                cells.append(f"{record[key]:>10,}")
        lines.append(f"{first:<{width}}" + "".join(cells))
    lines.append("")
    lines.append(f"{'proposer':<{width}}{'n':>10}{'share%':>10}{'unique':>10}{'gain%':>10}")
    for name in names:
        lines.append(
            f"{name:<{width}}{record[f'n_{name}']:>10,}{record[f'share_pct_{name}']:>10.2f}"
            f"{record[f'unique_{name}']:>10,}{record[f'union_gain_pct_{name}']:>10.2f}"
        )
    lines.append(f"{'UNION':<{width}}{record['union_total']:>10,}")
    if "sh_family_share_pct" in record:
        lines.append(
            f"  Schwartz & Hearst family share of union: {record['sh_family_share_pct']:.2f} %"
            f"   independent gain: {record['independent_gain_pct']:.2f} %"
        )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--corpus", action="append", choices=sorted(CORPORA))
    parser.add_argument(
        "--system",
        action="append",
        choices=sorted(EXTERNAL_SH_SYSTEMS),
        help="external S&H descendant to include; repeatable, needs --interpreter",
    )
    parser.add_argument("--interpreter", help="a Python that has the external baselines")
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument("--demo", action="store_true", help="print the independence demonstration")
    parser.add_argument("--external-worker", help=argparse.SUPPRESS)
    parser.add_argument("--texts", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.external_worker:
        if not args.texts:
            raise SystemExit("--external-worker needs --texts")
        return external_worker(args.external_worker, args.texts)

    if args.demo:
        print(demonstrate())
        if not args.corpus:
            return 0

    externals = list(args.system or (EXTERNAL_SH_SYSTEMS if args.interpreter else ()))
    if externals and not args.interpreter:
        raise SystemExit("--system needs --interpreter")

    recorded: dict[str, dict] = {}
    for key in args.corpus or sorted(CORPORA):
        passages = load_passages(key)
        context = {
            "corpus": CORPORA[key]["corpus"],
            "split": key,
            "gold_provenance": CORPORA[key]["gold_provenance"],
            "pooled_gold": CORPORA[key]["pooled_gold"],
        }
        recorded[f"monoculture.{key}.corpus"] = corpus_record(key, passages, context)
        proposals: dict[str, Proposals] = {}
        for profile in PROFILES:
            proposals[f"acronymkit/{profile}"] = run_acronymkit(passages, profile)
        for system in externals:
            proposals[system] = run_external(passages, system, args.interpreter)
        proposals["allcaps"] = run_allcaps(passages)
        proposals["shapecue"] = run_shapecue(passages)

        recorded[f"monoculture.{key}.independence"] = alignment_record(proposals, passages, context)
        recorded[f"monoculture.{key}.proposals.vertices"] = overlap_record(
            {name: vertex_keys(p, passages) for name, p in proposals.items()},
            "distinct (passage, short form)",
            context,
        )
        edges_by_proposer = {name: edge_keys(p) for name, p in proposals.items()}
        recorded[f"monoculture.{key}.proposals.edges"] = overlap_record(
            edges_by_proposer,
            "distinct (passage, short form, long form)",
            context,
        )
        # The same matrix over the Schwartz & Hearst rows ALONE, which is the
        # arrangement D-056 measured on the Federal Register pool and reported as
        # `93.74 %`. Recorded separately rather than derived in prose, because
        # the two unions have different denominators and a reader comparing the
        # full-table share against D-056's figure would be comparing two things.
        recorded[f"monoculture.{key}.proposals.edges_sh_only"] = overlap_record(
            {name: edges_by_proposer[name] for name in sh_family(sorted(edges_by_proposer))},
            "distinct (passage, short form, long form), S&H descendants only",
            context,
        )
        for name, proposal in sorted(proposals.items()):
            slug = name.replace("/", "_")
            scores: dict[str, float] = {}
            for label in ("short_form", "long_form"):
                if not any(
                    (p.gold_short if label == "short_form" else p.gold_long) for p in passages
                ):
                    continue
                for convention in ("exact", "overlap"):
                    scores.update(score_spans(passages, proposal, label, convention))
            recorded[f"monoculture.{key}.proposer.{slug}"] = {
                **context,
                "system": name,
                "elapsed_seconds": round(proposal.elapsed_seconds, 4),
                "short_form_spans": sum(len(v) for v in proposal.short_spans.values()),
                "long_form_spans": sum(len(v) for v in proposal.long_spans.values()),
                **scores,
                **proposal.notes,
            }

        print(f"=== {key} ({CORPORA[key]['corpus']}) ===")
        print(
            f"  {len(passages):,} passages, "
            f"{sum(len(p.gold_short) for p in passages):,} gold short-form spans, "
            f"{sum(len(p.gold_long) for p in passages):,} gold long-form spans, "
            f"{sum(len(p.gold_pairs) for p in passages):,} gold pairs"
        )
        print(f"  gold provenance: {CORPORA[key]['gold_provenance']}")
        described = recorded[f"monoculture.{key}.corpus"]
        for label in ("short_form", "long_form"):
            if described[f"gold_{label}_spans"]:
                print(
                    f"  gold {label} spans bracket-adjacent: "
                    f"{described[f'gold_{label}_spans_bracket_adjacent']:,} / "
                    f"{described[f'gold_{label}_spans']:,} = "
                    f"{described[f'gold_{label}_spans_bracket_adjacent_pct']:.2f} %"
                )
        if described["gold_pairs_located"]:
            print(
                f"  gold pairs bracket-adjacent: short form "
                f"{described['gold_pairs_short_form_bracket_adjacent_pct']:.2f} %, "
                f"long form {described['gold_pairs_long_form_bracket_adjacent_pct']:.2f} % "
                f"of {described['gold_pairs_located']:,} located"
            )
        print()
        print("-- proposals, unit = distinct (passage, short form, long form) edge --")
        print(render_matrix(recorded[f"monoculture.{key}.proposals.edges"]))
        print()
        print("-- proposals, unit = distinct (passage, short form) vertex --")
        print(render_matrix(recorded[f"monoculture.{key}.proposals.vertices"]))
        print()

        if any(p.gold_pairs for p in passages):
            record = gold_pair_record(passages, proposals, context)
            recorded[f"monoculture.{key}.gold.pairs"] = record
            print("-- gold pairs reached --")
            print(render_matrix(record))
            print()

        if any(p.gold_short or p.gold_long for p in passages):
            for label in ("short_form", "long_form"):
                if not any(
                    (p.gold_short if label == "short_form" else p.gold_long) for p in passages
                ):
                    continue
                for convention in ("exact", "overlap"):
                    gain = overlap_record(
                        gold_reach(passages, proposals, label, convention),
                        f"gold {label} span reached ({convention})",
                        context,
                    )
                    recorded[f"monoculture.{key}.gold.{label}.{convention}.gain"] = gain
                    klass = gold_class_record(passages, proposals, label, convention, context)
                    recorded[f"monoculture.{key}.gold.{label}.{convention}.class"] = klass
                    print(
                        f"-- gold {label}, {convention} match: "
                        f"S&H family reaches {klass['sh_family_recall_pct']:.2f} %, "
                        f"unproposed {klass['unproposed']:,} of {klass['gold_spans']:,} "
                        f"({klass['unproposed_pct']:.2f} %) --"
                    )
                    for name in sorted(
                        k
                        for k in klass
                        if k.startswith("unproposed_") and k.endswith("_pct_of_gold")
                    ):
                        stem = name[len("unproposed_") : -len("_pct_of_gold")]
                        print(
                            f"     {stem:<40} {klass[f'unproposed_{stem}']:>7,}  {klass[name]:>6.2f} % of gold"
                        )
                    print()

        independence = recorded[f"monoculture.{key}.independence"]
        print("-- independence of each proposer from the two S&H commitments --")
        print(
            f"     {'proposer':<28} {'edges':>7}  "
            f"{'unalignable':>11} {'pct':>7}  {'bracketless':>11} {'pct':>7}"
        )
        for name in sorted(proposals):
            print(
                f"     {name:<28} {independence[f'edges_{name}']:>7,}  "
                f"{independence[f'sh_unalignable_{name}']:>11,} "
                f"{independence[f'sh_unalignable_pct_{name}']:>6.2f} %  "
                f"{independence[f'bracketless_edges_{name}']:>11,} "
                f"{independence[f'bracketless_edges_pct_{name}']:>6.2f} %"
            )
        print(
            "     unalignable = the validator would refuse it; "
            "bracketless = the candidate generator never sees it"
        )
        print()

    if args.save:
        print(f"saved {len(recorded)} run(s) to {save_results(recorded).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
