#!/usr/bin/env python3
"""How often does one short form carry two expansions inside one document?

The question this runner exists to settle
-----------------------------------------
Mandate III's A2 would make ``extract()`` a **document-level resolver** rather
than a sentence-level pair finder: one definition anywhere in a document
licenses every later occurrence of that short form. The premise is
one-sense-per-discourse, a 1990s result nobody in this family exploits because
the family works per sentence -- ``src/acronymkit/extractor.py``'s candidate
window "never crosses a sentence boundary", which is the commitment A2 breaks.

**It is an assumption, not a law**, A2 is a breaking API change, and it moves
every published recall figure. So the violation rate is measured before anybody
relies on it.

Why this is a second file rather than an arm of ``bench/run_genre.py``
----------------------------------------------------------------------
``bench/run_genre.py`` owns the same corpus and this runner imports its fetcher,
its pins, its JATS reader and its roster admission rule rather than writing a
second one. It is not extended, for three reasons that are about the *unit* and
not about tidiness:

* its unit of measurement is the **half** -- abstract against body -- and every
  record it writes is per-half or a paired contrast between halves. This
  question has no halves: A2 resolves over a whole document, and cutting the
  document in two is the one thing that would hide a violation whose two
  definitions straddle the cut.
* its unit of *evidence* is a located gold pair. This runner's population is a
  **short-form group**: one document, one short form, every expansion offered
  for it. Nothing in that runner computes such a group.
* it already runs three halves times every proposer in the pool. Adding an arm
  would double the cost of a run whose existing consumers want none of it.

The instrument is free, and it is also the weaker half of the answer
--------------------------------------------------------------------
PMC Open Access articles carry their own ``<def-list>`` abbreviation roster in
``<back>``. That roster is author-authored, sits in neither the abstract nor the
body, and no abbreviation-detection system is anywhere in its construction. It
is the gold ``bench/run_genre.py`` uses and it is reused here unchanged.

**What it can support:** whether an author, writing a glossary for their own
article, ever declares two expansions for one term. That is a real question and
it has a clean answer.

**What it cannot support, and this is the load-bearing limit:** a glossary is a
curated one-to-one table. An author who writes ``CI`` for two things almost
never rosters both -- the roster is the place inconsistency gets *fixed*, not
the place it shows. So the roster's rate is a **floor** on within-document
ambiguity and it is not an estimate of one. Read alone it would answer a
different question than A2 asks: *do authors declare two senses*, rather than
*does a document contain two senses*.

So there are two instruments, and neither is sufficient alone
--------------------------------------------------------------
1. :func:`roster_groups` -- **the roster instrument**. Author-declared, no
   detector in the loop, and reported both before and after
   ``bench/run_genre.py``'s admission rule, because that rule was written to
   measure the Schwartz & Hearst blind spot and its effect on *this* question
   had never been measured.
2. :func:`resolver_groups` -- **the resolver instrument**. Every definition
   ``extract_definitions`` offers over the whole document, grouped by short
   form. It needs no gold because it is not a recall measurement: it is the
   population A2 would actually have to arbitrate, and a second expansion in it
   is a decision A2 must take whether or not the second expansion is correct.
   **That is the point.** A2 does not get to arbitrate only real ambiguities; it
   inherits the extractor's false positives and licenses them document-wide.

The two disagree by two orders of magnitude, and the disagreement is the
finding rather than a defect in either.

The decomposition, because a pooled rate mixes two different problems
----------------------------------------------------------------------
A surface variant of one expansion (``Mueller Hinton broth`` against
``Mueller-Hinton broth``) is a **normalisation** problem. A genuine second sense
(``SD`` as standard deviation and as swelling degree) is a **correctness**
problem. Pooling them is a phrasing tighter than the measurement, so
:func:`classify_group` puts every violating group in one of three mechanical
classes:

``surface``
    Every expansion collapses to one string under a stated ladder: Unicode
    NFKD and dash folding, case folding, whitespace collapse, non-alphanumeric
    removal, a crude singulariser, a closed stop-word list, and -- because it is
    a document-level operation and therefore exactly A2's kind -- one pass of
    **nested abbreviation expansion** using the document's own unambiguous
    definitions, which is what makes ``cone-beam CT`` and
    ``cone-beam computed tomography`` one expansion.
``refinement``
    Not collapsible, but one expansion's word sequence is a whole-word
    subsequence of another's: ``water vapor transmission rate`` against
    ``water vapor transmission rate permeability``.
``distinct``
    Neither. **This class is not "genuine ambiguity" and must never be quoted as
    if it were.** It holds real second senses, near-synonyms, typographical
    variants, truncations, and long forms that are not expansions of anything.
    Separating those is not mechanical, so :data:`AUDIT_LABELS` is a seeded,
    hand-adjudicated sample of it, by one annotator, reported as such.

What A2 would get wrong, in A2's own terms
-------------------------------------------
:func:`a2_record` models A2 as: **commit to the first definition in document
order, license every occurrence of that short form at or after it.** Then for a
group with more than one expansion:

* the **floor** on wrong licensed occurrences is the definition sites of the
  expansions A2 did not commit to. Each one is a position where A2 returns a
  string the document is at that very moment defining differently, so it is
  wrong by construction and needs no annotation to establish.
* the **ceiling** is every licensed occurrence of that group except the
  committed definition site itself.

Both bounds are reported by class, because the ``surface`` share of them is a
byte-difference and the ``distinct`` share is a wrong answer.

**And the error rate A2 replaces is zero, which is the sharpest thing on this
page.** The mechanism A2 displaces does not answer wrongly at an out-of-sentence
occurrence; it does not answer at all. So A2 buys coverage and pays in
correctness, and :func:`a2_record` prices both sides:
``licensed_occurrences_outside_every_definition_sentence`` is the whole of what
A2 wins, computed from the pairs' own captured sentences.

How this fails
--------------
**The roster is not a recall corpus and this runner does not make it one.**
``bench/splits.toml``'s entry for this corpus says every figure it backs should
be a difference between two halves where the authors' declaration habits cancel.
The roster figures here are absolute, and they are absolute *about the roster*:
"of the pairs an author chose to declare, how many collide" is a property of
declaration habits and is reported as one. No roster number here is a claim
about how often documents contain two senses.

**One domain, and the convention may be the cause.** PMC is biomedical, and
biomedicine has a rostering convention. A field that rosters its abbreviations
is a field whose authors have been made to look at their own abbreviation list,
which is precisely the intervention that would suppress within-document
collisions. Prose nobody rosters -- a regulation, a filing, a schema's
documentation -- has had no such pass, and nothing here transfers to it.

**The resolver instrument has no gold at all.** It measures what a document-level
resolver must arbitrate, not what is true. A ``distinct`` group where one long
form is extractor noise is counted, deliberately, because A2 would have to
arbitrate it -- but that means the rate is a property of the operating point as
much as of the documents, which is why every profile is reported separately.

Usage::

    python bench/run_one_sense.py                 # measure and print
    python bench/run_one_sense.py --save          # ... and record run ids
    python bench/run_one_sense.py --audit-sample  # print the groups to adjudicate

Fetching, pinning and verification all live in ``bench/run_genre.py`` and are
not duplicated here: run ``python bench/run_genre.py --fetch`` first.
"""

from __future__ import annotations

import argparse
import math
import random
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from bisect import bisect_right
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from acronymkit.config import Config  # noqa: E402
from acronymkit.enums import ExtractionProfile  # noqa: E402
from acronymkit.tokenizer import Tokenizer  # noqa: E402
from bench.run_genre import (  # noqa: E402
    DATA_DIR,
    Article,
    _local,
    load_articles,
    pinned_pmcids,
)
from bench.run_monoculture import (  # noqa: E402
    PROFILES,
    environment,
    normalise,
    save_results,
)

Pair = Tuple[str, str]

# ---------------------------------------------------------------------------
# 1. Constants, all of them stated rather than tuned
# ---------------------------------------------------------------------------
#: Stop words dropped by the surface-variant ladder. A closed list, short on
#: purpose: every word here is one whose presence or absence never changes which
#: concept an expansion names. Anything longer starts folding real distinctions.
LADDER_STOP_WORDS: FrozenSet[str] = frozenset(
    ["a", "an", "and", "by", "for", "in", "of", "on", "the", "to", "with"]
)

#: Unicode dashes mapped to ASCII ``-`` before anything else. PMC body text uses
#: U+2010 and U+2011 inside chemical and gene names, and an expansion written
#: once with each is one expansion.
_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")

_WORD_SPLIT = re.compile(r"[^0-9a-z]+")

#: Seed for the hand-adjudication draw over the ``distinct`` class. Separate
#: from every seed in ``bench/run_genre.py`` so that re-drawing there cannot
#: silently move the sample somebody adjudicated by hand.
AUDIT_SEED = 20260826

#: How many groups of each mechanical class were drawn for adjudication. The
#: ``distinct`` frame gets the most because it is the residual the mechanical
#: rules cannot split; the other two are sampled because a ladder that folds a
#: real second sense into ``surface`` is the failure that would make every
#: correctness figure on this page too small.
AUDIT_SAMPLE_SIZES: Dict[str, int] = {"distinct": 120, "surface": 40, "refinement": 40}

#: Added to :data:`AUDIT_SEED` per class so the three draws do not share a
#: shuffle. Fixed, and not chosen after seeing any output.
AUDIT_CLASS_SALT: Dict[str, int] = {"distinct": 0, "surface": 1, "refinement": 2}

#: The closed label vocabulary. A label outside it would vanish from every count.
AUDIT_LABEL_VOCABULARY: FrozenSet[str] = frozenset(["genuine", "variant", "artefact", "unclear"])

#: The profile the adjudicated sample was drawn from. Named because a sample
#: drawn from one operating point is not a sample of another.
AUDIT_PROFILE = "biomedical"

#: How many documents :func:`splitter_agreement_record` re-runs under the
#: engine's own ``extraction_capture_sentences`` path, to show that the cached
#: span table this runner builds puts every definition in the sentence the
#: shipped code would have attached to it.
SPLITTER_CHECK_DOCUMENTS = 40

#: The character ceiling on the documents those checks may draw from. The
#: shipped splitter is quadratic (``one_sense.pmc_oa.splitter_cost``), so a
#: whole-document split of a long article does not finish. The cap is a stated
#: bias in the checks -- they see the short half of the corpus and nothing
#: about the long half.
WHOLE_DOCUMENT_CHECK_CHARACTERS = 20_000

#: Blank-line separator between paragraph blocks, which is what
#: ``bench/run_genre.py``'s renderer emits between JATS block elements.
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")

#: One annotator's verdict on each drawn group, keyed by ``PMC<id>\t<short>``.
#:
#: **This is a single-annotator adjudication and it is the only judgement in
#: this file.** The corpus is registered ``single_annotator_reference`` and this
#: is why. Four labels:
#:
#: ``genuine``   two different concepts share the short form in this document.
#: ``variant``   one concept, written two ways the ladder could not fold --
#:               near-synonym, typographical variant, truncation, derivational
#:               morphology (``microscope`` / ``microscopy``).
#: ``artefact``  at least one long form is not an expansion of the short form.
#:               The extractor proposed it; a document-level licence would
#:               inherit it.
#: ``unclear``   the annotator could not decide from the two strings alone.
#:
#: The runner reports how many labels matched a group in the current population
#: and how many did not, so a population that moves is visible rather than
#: silently re-weighted.
AUDIT_LABELS: Dict[str, str] = {
    "PMC10049361\tIr": "artefact",
    "PMC10049361\tNAL": "variant",
    "PMC10098097\tmiRs": "artefact",
    "PMC10130531\tQPM": "variant",
    "PMC10146953\tPerfG": "artefact",
    "PMC10218224\tHR": "artefact",
    "PMC10235610\tAOF": "variant",
    "PMC10235610\tPBMC": "variant",
    "PMC10254352\tMUM": "artefact",
    "PMC10256645\tHATS": "variant",
    "PMC10256645\tLATS": "variant",
    "PMC10273532\tDEGs": "variant",
    "PMC10333182\tLPSI": "artefact",
    "PMC10354073\tHDT": "variant",
    "PMC10512251\tCAT": "variant",
    "PMC10512251\tSOD": "variant",
    "PMC10532005\tSEM": "variant",
    "PMC10647726\tSEM": "variant",
    "PMC10682373\tAPC": "artefact",
    "PMC10689540\tCPCRN": "variant",
    "PMC10763362\tHR": "genuine",
    "PMC10853344\tTMAO": "variant",
    "PMC10882737\tMRSA": "variant",
    "PMC10902389\tHMM": "variant",
    "PMC10902389\tMuMMI": "artefact",
    "PMC10929173\tPS": "variant",
    "PMC10990044\tALE": "artefact",
    "PMC11065956\tTS": "artefact",
    "PMC11088107\tAUC": "artefact",
    "PMC11102075\tMKPs": "artefact",
    "PMC11142665\tAIAN": "variant",
    "PMC11143008\ths-CRP": "variant",
    "PMC11148399\tFRF": "variant",
    "PMC11171404\tEP": "variant",
    "PMC11175786\tCI": "variant",
    "PMC11199256\tHD-sEMG": "variant",
    "PMC11208694\tLNPs": "variant",
    "PMC11208694\tlncRNAs": "variant",
    "PMC11237663\tMyHC": "genuine",
    "PMC11239017\tLHON": "variant",
    "PMC11246427\tGFP-LACE": "artefact",
    "PMC11290961\tGnRH": "variant",
    "PMC11292135\tcryo-EM": "variant",
    "PMC11395504\tBMT": "variant",
    "PMC11403411\tMA": "variant",
    "PMC11406483\tXAS": "variant",
    "PMC11430382\tIDO": "variant",
    "PMC11492079\tDSC": "variant",
    "PMC11493799\tMOR": "artefact",
    "PMC11501923\tMDR": "variant",
    "PMC11505919\tMAD": "artefact",
    "PMC11575446\taOR": "artefact",
    "PMC11595597\tFDI": "variant",
    "PMC11672922\tCNN": "variant",
    "PMC11678115\tONT": "variant",
    "PMC11749566\tCoSCs": "variant",
    "PMC11767186\tATR-FTIR": "variant",
    "PMC11795430\tPRSEA": "variant",
    "PMC11799297\tMHC": "artefact",
    "PMC11814855\tVAS": "variant",
    "PMC11848911\tTD-DFT": "variant",
    "PMC11940830\tECG": "variant",
    "PMC11946615\tDSC": "variant",
    "PMC2584948\tSrcwt": "variant",
    "PMC2875658\tFigure": "artefact",
    "PMC3157158\tHHRP": "variant",
    "PMC3208529\tCNC": "artefact",
    "PMC3427187\tHSB": "variant",
    "PMC3530754\tACC": "variant",
    "PMC3674619\tPAS": "variant",
    "PMC3907517\tIMCL": "variant",
    "PMC3912177\tNPP": "variant",
    "PMC3934447\tWEP": "variant",
    "PMC3979045\tIFN": "artefact",
    "PMC3997863\tDA-CVAFS": "variant",
    "PMC4074427\tFW": "variant",
    "PMC4074427\tLW": "variant",
    "PMC4129920\tETS": "variant",
    "PMC4166016\tMRSA": "variant",
    "PMC4251634\tFA": "variant",
    "PMC4320612\tEch": "variant",
    "PMC4428002\tSD": "artefact",
    "PMC4431600\tMBD": "variant",
    "PMC4617722\tTSDR": "variant",
    "PMC4647617\tAl": "artefact",
    "PMC4647617\tOXO": "variant",
    "PMC4660435\tTG": "variant",
    "PMC4776122\tOF": "artefact",
    "PMC4875637\tWES": "variant",
    "PMC4883255\tMOR": "artefact",
    "PMC4883255\tOR": "artefact",
    "PMC4899386\tROC": "variant",
    "PMC4923065\tgRNA": "artefact",
    "PMC4978964\tLMP": "variant",
    "PMC5037914\tTEER": "artefact",
    "PMC5328395\tBDI-II": "artefact",
    "PMC5393560\tTSS": "artefact",
    "PMC5469673\tRD": "unclear",
    "PMC5479852\tJA-Ile": "variant",
    "PMC5524659\tLAB": "artefact",
    "PMC5591433\tCVRA": "variant",
    "PMC5814582\tSNPs": "artefact",
    "PMC5837087\tMIC": "artefact",
    "PMC5877123\tRT": "variant",
    "PMC5893836\tTOC": "artefact",
    "PMC5974003\tVMM": "artefact",
    "PMC6034791\tFTIR": "variant",
    "PMC6071392\tHR": "variant",
    "PMC6155261\tFig": "artefact",
    "PMC6163620\tLCST": "variant",
    "PMC6163620\tTEM": "variant",
    "PMC6199288\tFC": "variant",
    "PMC6199288\teRIC": "variant",
    "PMC6208160\tEOMs": "artefact",
    "PMC6266111\tSWFoL": "variant",
    "PMC6278552\tpNPP": "artefact",
    "PMC6423225\tPVN": "variant",
    "PMC6445897\tIONM": "variant",
    "PMC6539107\tLC-TGA": "variant",
    "PMC6547457\tALS": "artefact",
    "PMC6587114\tLM-OVA": "variant",
    "PMC6723041\tRPE": "variant",
    "PMC6771964\tPPI": "variant",
    "PMC6838213\tAB": "variant",
    "PMC6890729\tHIL": "variant",
    "PMC6930756\tHA": "variant",
    "PMC6952441\tOL": "variant",
    "PMC6952441\tTDRL": "variant",
    "PMC7020495\ttRNAs": "artefact",
    "PMC7096404\tMDAR": "variant",
    "PMC7113522\tSDHA": "variant",
    "PMC7201527\tVAP-1": "variant",
    "PMC7201527\tVIC": "variant",
    "PMC7229812\tCNVs": "variant",
    "PMC7247690\tTCSs": "variant",
    "PMC7346167\tJAK2": "artefact",
    "PMC7346167\tSM22\u03b1": "artefact",
    "PMC7346655\tNKTCL": "variant",
    "PMC7366672\tNEXAFS": "variant",
    "PMC7382178\tMF": "variant",
    "PMC7411018\tDOY": "variant",
    "PMC7439208\teNOS": "variant",
    "PMC7483446\tHS/SPME\u2013GC\u2013MS": "variant",
    "PMC7483446\tPCA": "variant",
    "PMC7582155\tSFG": "artefact",
    "PMC7614201\tML": "genuine",
    "PMC7696101\tP5CS": "variant",
    "PMC7828388\tDDK": "variant",
    "PMC7874631\tOSI": "variant",
    "PMC7943417\tBMT": "variant",
    "PMC8049941\taPIAT": "variant",
    "PMC8073038\tHe": "variant",
    "PMC8076642\tEndMT": "variant",
    "PMC8115455\tLPS": "variant",
    "PMC8184778\tLQTS3": "variant",
    "PMC8199287\tTCGA": "variant",
    "PMC8218558\tSAV": "variant",
    "PMC8224647\tColl": "artefact",
    "PMC8268430\tN43": "artefact",
    "PMC8326911\tHDP-MSN": "variant",
    "PMC8326911\tMSN": "variant",
    "PMC8343990\tCP": "variant",
    "PMC8357370\tSDC-1": "variant",
    "PMC8446553\tMHOS": "variant",
    "PMC8480522\tDNA-PK": "variant",
    "PMC8481544\tRT-qPCR": "variant",
    "PMC8529229\tPLA": "variant",
    "PMC8531107\tfBIC": "variant",
    "PMC8545561\tLPS": "variant",
    "PMC8545561\tmTORC1": "variant",
    "PMC8546232\tLA": "genuine",
    "PMC8564527\tICP-OES": "variant",
    "PMC8677803\tCPD": "variant",
    "PMC8677803\tFT-IR": "variant",
    "PMC8677803\tTPY": "variant",
    "PMC8703844\tOR": "artefact",
    "PMC8718613\tSP": "genuine",
    "PMC8759662\tTADS": "variant",
    "PMC8856557\tRBD": "variant",
    "PMC8860281\tOR": "artefact",
    "PMC8869144\tSREBP-1c": "variant",
    "PMC8912838\tHns": "artefact",
    "PMC8946504\tCMap": "artefact",
    "PMC9078012\tCol": "variant",
    "PMC9086555\tHIF": "variant",
    "PMC9221552\tDL": "variant",
    "PMC9289680\tCOG": "artefact",
    "PMC9395532\tGE": "unclear",
    "PMC9403742\tSR-10": "artefact",
    "PMC9598096\tADAR": "variant",
    "PMC9601419\tFISH": "variant",
    "PMC9653400\tIFN": "variant",
    "PMC9670373\tVIP": "variant",
    "PMC9792607\tOR": "artefact",
    "PMC9859466\tOH": "artefact",
    "PMC9859466\tUCA": "artefact",
    "PMC9886624\tMS": "artefact",
    "PMC9913704\tHR": "genuine",
    "PMC9939121\tAND": "artefact",
    "PMC9958934\tPANSS": "variant",
}


# ---------------------------------------------------------------------------
# 2. The surface-variant ladder
# ---------------------------------------------------------------------------
def fold_text(value: str) -> str:
    """Case-fold, strip accents, unify dashes and collapse whitespace.

    Args:
        value: Any expansion string.

    Returns:
        The folded string. This is rung one of the ladder and it is the only
        rung that touches nothing but presentation.
    """
    decomposed = unicodedata.normalize("NFKD", value).translate(_DASHES)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped).strip().casefold()


def singularise(word: str) -> str:
    """A crude English singulariser, stated rather than imported.

    It is deliberately small and it is deliberately wrong in places -- it maps
    ``analyses`` to ``analys`` and leaves ``analysis`` alone, so that pair does
    **not** fold. A stemmer good enough to fold it would also fold distinctions
    this measurement is about.

    Args:
        word: One lowercase alphanumeric token.

    Returns:
        The token with a plural suffix removed where one of three rules fires.
    """
    if len(word) > 3 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith(("ses", "xes", "zes", "ches", "shes")):
        return word[:-2]
    if len(word) > 2 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def ladder_words(value: str) -> Tuple[str, ...]:
    """The expansion as content words: folded, split on non-alphanumerics, singular.

    Args:
        value: An expansion string.

    Returns:
        The tuple of content words, stop words removed.
    """
    tokens = [token for token in _WORD_SPLIT.split(fold_text(value)) if token]
    return tuple(singularise(token) for token in tokens if token not in LADDER_STOP_WORDS)


def ladder_squash(value: str) -> str:
    """:func:`ladder_words` with the word boundaries thrown away.

    This is the rung that folds a hyphen sitting *inside* a word:
    ``non-metric multidimensional scaling`` splits into three tokens and
    ``nonmetric multidimensional scaling`` into two, so
    :func:`ladder_words` keeps them apart and this rung does not.

    Args:
        value: An expansion string.

    Returns:
        The content words concatenated.
    """
    return "".join(ladder_words(value))


def is_word_subsequence(shorter: Sequence[str], longer: Sequence[str]) -> bool:
    """Is ``shorter`` a whole-word subsequence of ``longer``?

    Args:
        shorter: Candidate subsequence.
        longer: Candidate supersequence.

    Returns:
        True when every word of ``shorter`` appears in ``longer`` in order.
    """
    cursor = iter(longer)
    return all(word in cursor for word in shorter)


def expand_nested(value: str, unambiguous: Dict[str, str]) -> str:
    """Substitute this document's own unambiguous abbreviations into an expansion.

    One pass, no recursion, and only for short forms the same document defines
    **exactly once** -- substituting an ambiguous one would import the very
    ambiguity under test. This is a document-level operation and it is included
    because it is A2's own kind of operation: if A2 is right that a document
    licenses a short form globally, then a nested abbreviation inside a long
    form is resolvable by the same licence.

    Args:
        value: An expansion string.
        unambiguous: ``{short form: its one expansion}`` for this document.

    Returns:
        The expansion with nested abbreviations replaced. Non-word runs are
        preserved so that spacing and punctuation survive the substitution.
    """
    parts = re.split(r"(\W+)", value)
    out: List[str] = []
    for part in parts:
        replacement = unambiguous.get(part)
        if replacement is not None and normalise(replacement) != normalise(part):
            out.append(replacement)
        else:
            out.append(part)
    return "".join(out)


def classify_group(expansions: Sequence[str], unambiguous: Dict[str, str]) -> str:
    """Put one violating short-form group in ``surface``, ``refinement`` or ``distinct``.

    Args:
        expansions: Every distinct expansion offered for this short form in this
            document. Two or more, or the caller should not be here.
        unambiguous: This document's singly-defined short forms, for
            :func:`expand_nested`.

    Returns:
        One of ``"surface"``, ``"refinement"``, ``"distinct"``.
    """
    for candidates in (
        list(expansions),
        [expand_nested(value, unambiguous) for value in expansions],
    ):
        words = {ladder_words(value) for value in candidates}
        if len(words) == 1 or len({ladder_squash(value) for value in candidates}) == 1:
            return "surface"
        ordered = sorted(words, key=len)
        covers_all = all(is_word_subsequence(ordered[0], other) for other in ordered[1:])
        inside_one = all(is_word_subsequence(other, ordered[-1]) for other in ordered[:-1])
        if covers_all or inside_one:
            return "refinement"
    return "distinct"


# ---------------------------------------------------------------------------
# 3. The abbreviation-shaped filter, transcribed from the roster rule
# ---------------------------------------------------------------------------
def term_shaped(term: str) -> bool:
    """The **term half** of ``bench/run_genre.py``'s roster admission rule.

    That rule was written by another workstream, for another question, before
    this one was asked -- which is exactly why it is the filter used here rather
    than one chosen after looking at the output. It admits two-to-fifteen
    characters, no whitespace, at least one letter and at least one capital, so
    it refuses ``i.e``, ``e.g``, ``p``, ``set`` and every single character.

    ``tests/test_one_sense.py`` pins this against
    :func:`bench.run_genre.roster_pair_admissible` over a battery of terms, so a
    transcription that drifts turns the suite red.

    Args:
        term: A candidate short form.

    Returns:
        True when the term half of the roster rule admits it.
    """
    if not 2 <= len(term) <= 15 or any(character.isspace() for character in term):
        return False
    if not any(character.isalpha() for character in term):
        return False
    return any(character.isupper() for character in term)


def bounded_occurrences(text: str, needle: str) -> List[int]:
    """Every start offset where ``needle`` appears as a whole token.

    ``bench/run_monoculture.py``'s ``_occurrences`` is a bare substring search
    with no word boundary, which is right for locating a gold span and wrong for
    counting occurrences: it finds ``CT`` inside ``fact``. Both counts are
    recorded by :func:`a2_record` so the difference between them is visible
    rather than assumed away.

    Args:
        text: The document.
        needle: The short form.

    Returns:
        Start offsets, leftmost first.
    """
    if not needle:
        return []
    pattern = re.compile(r"(?<![0-9A-Za-z])" + re.escape(needle) + r"(?![0-9A-Za-z])")
    return [match.start() for match in pattern.finditer(text)]


# ---------------------------------------------------------------------------
# 4. Instrument R -- the author's own roster
# ---------------------------------------------------------------------------
def raw_roster(pmcid: int) -> List[Pair]:
    """Every ``<def-item>`` in ``<back>``, with **no admission rule applied**.

    ``bench.run_genre.parse_article`` filters as it parses and does not expose
    the pre-filter population, so the walk is repeated here. That duplication is
    deliberate and is the whole point of the record it feeds: the admission rule
    is itself under test, and a rule cannot be measured through itself.

    Args:
        pmcid: Numeric PMC identifier.

    Returns:
        ``(term, definition)`` in document order, deduplicated only on exact
        normalised equality of both halves.
    """
    path = DATA_DIR / f"PMC{pmcid}.1.xml"
    if not path.is_file():
        return []
    try:
        root = ET.fromstring(path.read_bytes())
    except ET.ParseError:
        return []
    back = root.find("back")
    if back is None:
        return []
    seen: Set[Pair] = set()
    pairs: List[Pair] = []
    for def_list in back.iter():
        if _local(def_list.tag) != "def-list":
            continue
        for item in def_list.iter():
            if _local(item.tag) != "def-item":
                continue
            term_element = next((c for c in item if _local(c.tag) == "term"), None)
            def_element = next((c for c in item if _local(c.tag) == "def"), None)
            if term_element is None or def_element is None:
                continue
            term = " ".join("".join(term_element.itertext()).split())
            definition = " ".join("".join(def_element.itertext()).split())
            key = (normalise(term), normalise(definition))
            if key in seen:
                continue
            seen.add(key)
            pairs.append((term, definition))
    return pairs


def group_pairs(pairs: Iterable[Pair], *, fold_key: bool) -> Dict[str, List[str]]:
    """Group ``(short, long)`` pairs by short form, keeping distinct expansions.

    Args:
        pairs: The pairs from one document.
        fold_key: Case-fold the short form before grouping. **This choice is a
            finding rather than a detail** -- see :func:`roster_record`.

    Returns:
        ``{short form key: [distinct expansion, ...]}``, expansions in first-seen
        order, deduplicated on :func:`bench.run_monoculture.normalise`.
    """
    grouped: Dict[str, List[str]] = {}
    seen: Dict[str, Set[str]] = {}
    for short, long_form in pairs:
        key = normalise(short) if fold_key else short
        bucket = grouped.setdefault(key, [])
        marks = seen.setdefault(key, set())
        folded = normalise(long_form)
        if folded in marks:
            continue
        marks.add(folded)
        bucket.append(long_form)
    return grouped


def roster_record(
    articles: Sequence[Article], *, fold_key: bool, admitted: bool, context: dict
) -> dict:
    """What the authors' own rosters say about one short form carrying two expansions.

    Two keyings are run and both are published, because the difference between
    them is one of this round's results. Biology marks case: ``Bdnf`` is the
    mouse gene and ``BDNF`` the human one, ``ms`` is a millisecond and ``MS`` is
    multiple sclerosis. A resolver whose key is case-folded **manufactures**
    ambiguity that the document does not contain, and the manufactured groups
    are enumerated in the record rather than summarised.

    Args:
        articles: The sample, in draw order.
        fold_key: Case-fold the short form before grouping.
        admitted: Use the admitted roster (``Article.roster``) rather than
            :func:`raw_roster`.
        context: Fields copied into the record.

    Returns:
        The record.
    """
    record: dict = dict(context)
    record["instrument"] = "roster"
    record["population"] = "admitted by roster_pair_admissible" if admitted else "every <def-item>"
    record["short_form_key"] = "case-folded" if fold_key else "case-sensitive"
    groups = 0
    violations: List[dict] = []
    articles_with_a_roster = 0
    pairs_total = 0
    articles_with_a_violation: Set[int] = set()
    classes: Counter = Counter()
    for article in articles:
        pairs = list(article.roster) if admitted else raw_roster(article.pmcid)
        if not pairs:
            continue
        articles_with_a_roster += 1
        pairs_total += len(pairs)
        grouped = group_pairs(pairs, fold_key=fold_key)
        unambiguous = {short: forms[0] for short, forms in grouped.items() if len(forms) == 1}
        for short, forms in grouped.items():
            groups += 1
            if len(forms) < 2:
                continue
            label = classify_group(forms, unambiguous)
            classes[label] += 1
            articles_with_a_violation.add(article.pmcid)
            violations.append(
                {
                    "pmcid": article.pmcid,
                    "short_form": short,
                    "expansions": sorted(forms),
                    "class": label,
                }
            )
    record["articles"] = len(articles)
    record["articles_with_a_roster"] = articles_with_a_roster
    record["roster_pairs"] = pairs_total
    record["short_form_groups"] = groups
    record["groups_with_two_or_more_expansions"] = len(violations)
    record["violation_pct"] = round(100 * len(violations) / max(groups, 1), 4)
    record["articles_with_a_violation"] = len(articles_with_a_violation)
    for label in ("surface", "refinement", "distinct"):
        record[f"class_{label}"] = classes[label]
    record["violations"] = violations
    record["note"] = (
        "A roster is a curated one-to-one table, so this rate is a FLOOR on within-document "
        "ambiguity and is not an estimate of one. It answers 'do authors declare two senses', "
        "which is a question about declaration habits."
    )
    return record


# ---------------------------------------------------------------------------
# 5. Instrument X -- what a document-level resolver would arbitrate
# ---------------------------------------------------------------------------
class Definition:
    """One definition the extractor offered, with the offsets A2 would need.

    Attributes:
        short_form: The abbreviation as written.
        long_form: The expansion as written.
        short_start: Character offset of the short form in the document.
        sentence_span: ``(start, end)`` of the enclosing sentence, or ``None``
            when the extractor could not identify one.
    """

    __slots__ = ("long_form", "sentence_span", "short_form", "short_start")

    def __init__(
        self,
        short_form: str,
        long_form: str,
        short_start: int,
        sentence_span: Optional[Tuple[int, int]],
    ) -> None:
        self.short_form = short_form
        self.long_form = long_form
        self.short_start = short_start
        self.sentence_span = sentence_span


class DocumentGroups:
    """Every short-form group in one document, under one operating point.

    Attributes:
        pmcid: Numeric PMC identifier.
        text: The document -- abstract and body concatenated, which is the unit
            A2 resolves over.
        groups: ``{short form: [Definition, ...]}`` in document order.
    """

    __slots__ = ("groups", "pmcid", "text")

    def __init__(self, pmcid: int, text: str, groups: Dict[str, List[Definition]]) -> None:
        self.pmcid = pmcid
        self.text = text
        self.groups = groups

    def expansions(self, short_form: str) -> List[str]:
        """Distinct expansions offered for ``short_form``, first-seen order."""
        seen: Set[str] = set()
        out: List[str] = []
        for definition in self.groups[short_form]:
            folded = normalise(definition.long_form)
            if folded in seen:
                continue
            seen.add(folded)
            out.append(definition.long_form)
        return out

    def unambiguous(self) -> Dict[str, str]:
        """``{short form: its one expansion}`` for the singly-defined short forms."""
        out: Dict[str, str] = {}
        for short_form in self.groups:
            forms = self.expansions(short_form)
            if len(forms) == 1:
                out[short_form] = forms[0]
        return out


def document_text(article: Article) -> str:
    """The unit A2 resolves over: one article's abstract followed by its body.

    ``<back>`` is excluded, so the roster the other instrument reads is not part
    of the text this one measures. That is not a nicety: a roster inside the
    measured text would hand the extractor every definition twice and turn a
    glossary into a second definition site.

    Args:
        article: One parsed article.

    Returns:
        The concatenated text.
    """
    return article.abstract + "\n\n" + article.body


def enclosing_sentence(spans: Sequence[Tuple[int, int]], offset: int) -> Optional[Tuple[int, int]]:
    """The sentence span containing ``offset``, by binary search.

    Args:
        spans: Sentence spans in order, as ``Tokenizer.split_sentences`` returns.
        offset: A character offset into the same text.

    Returns:
        The containing span, or ``None`` when the offset falls in none.
    """
    index = bisect_right([start for start, _ in spans], offset) - 1
    if index < 0:
        return None
    start, end = spans[index]
    return (start, end) if start <= offset < end else None


def paragraph_blocks(text: str) -> List[Tuple[int, int]]:
    """Split a document at blank lines, keeping offsets.

    Args:
        text: The document.

    Returns:
        ``(start, end)`` of each non-empty block, in order, covering every
        character that is not part of a separating blank run.
    """
    blocks: List[Tuple[int, int]] = []
    cursor = 0
    for chunk in _PARAGRAPH_BREAK.split(text):
        at = text.index(chunk, cursor) if chunk else cursor
        if chunk.strip():
            blocks.append((at, at + len(chunk)))
        cursor = at + len(chunk)
    return blocks


def split_document(tokenizer: Tokenizer, text: str) -> List[Tuple[int, int]]:
    """Sentence spans over a whole document, taken one paragraph block at a time.

    **This is a cost fix and it is also the more faithful reading, which is the
    only reason it is acceptable.** ``Tokenizer.split_sentences`` is quadratic in
    the length of the string it is handed -- measured, and recorded as
    ``one_sense.pmc_oa.splitter_cost`` -- so handing it a whole PMC article does
    not finish in a time anybody would wait for. Splitting at blank lines first
    makes the total linear in the document.

    It is not merely cheaper. ``src/acronymkit/extractor.py``'s own candidate
    window "never crosses a sentence boundary, a paragraph break, or a"
    section start, so a sentence that spanned a blank line could never carry a
    definition anyway. The chunked split is therefore at least as close to the
    extractor's own notion of locality as the whole-document split is, and
    :func:`sentence_span_table` measures the difference rather than asserting it
    is zero.

    Args:
        tokenizer: The shipped splitter.
        text: The document.

    Returns:
        ``(start, end)`` sentence spans in document offsets, in order.
    """
    spans: List[Tuple[int, int]] = []
    for block_start, block_end in paragraph_blocks(text):
        block = text[block_start:block_end]
        for span_start, span_end in tokenizer.split_sentences(block):
            spans.append((block_start + int(span_start), block_start + int(span_end)))
    return spans


def splitter_cost_record(context: dict) -> dict:
    """The shipped sentence splitter's cost curve, because A2 is a document-level feature.

    **R18: the counts are the property of the code and the seconds are the
    property of this machine.** Characters and sentences are gated; the timings
    are an unarmed note carrying the machine's name, and no conclusion here
    rests on their absolute size -- only on the ratio between consecutive rows,
    which doubles the input and roughly quadruples the time.

    This is in the record rather than in a comment because it bears directly on
    the workstream that commissioned the measurement: A2 makes ``extract()``
    document-scoped, and the library's own sentence splitter costs
    ``O(n squared)`` in the length of the string handed to it.

    Args:
        context: Fields copied into the record.

    Returns:
        The record.
    """
    tokenizer = Tokenizer(Config())
    unit = "The standard deviation (SD) was small in every cohort we examined. "
    record: dict = dict(context)
    record["machine"] = environment()
    record["measurement"] = "wall clock, unarmed; only the ratio between rows is read"
    rows: List[dict] = []
    for repeats in (100, 200, 400, 800):
        text = unit * repeats
        started = time.perf_counter()
        sentences = tokenizer.split_sentences(text)
        elapsed = time.perf_counter() - started
        rows.append(
            {
                "characters": len(text),
                "sentences": len(sentences),
                "splitter_calls": 1,
                "seconds_unarmed_note": round(elapsed, 4),
            }
        )
    for index, row in enumerate(rows):
        for key, value in row.items():
            record[f"row{index}.{key}"] = value
        if index:
            previous = rows[index - 1]["seconds_unarmed_note"]
            record[f"row{index}.seconds_ratio_to_previous_row_unarmed_note"] = round(
                row["seconds_unarmed_note"] / max(previous, 1e-9), 2
            )
    record["note"] = (
        "Doubling the input doubles the sentence count and roughly quadruples the time. "
        "A linear splitter would show a ratio near 2; a quadratic one near 4."
    )
    return record


def sentence_span_table(
    articles: Sequence[Article],
) -> Tuple[Dict[int, List[Tuple[int, int]]], dict]:
    """Split every document into sentences **once**, through the shipped splitter.

    Three facts forced this design and each is measured rather than assumed.

    **The extractor's fallback splitter cannot be used on this corpus.**
    ``acronymkit.extractor._fallback_sentence_spans`` treats a period as a
    terminator only when the preceding word is longer than one character, which
    is the guard against ``J. R.``. PMC body text rendered with its ``<xref>``
    citations removed is full of ``space period space``, so the preceding word
    is *empty* and the guard fires on every one of them. Measured against the
    shipped path it agreed on ``31.45`` % of definitions and its median sentence
    was ``371`` characters against ``204``. It is not used here and this
    paragraph is the reason.

    **The shipped path is quadratic, so it is fed paragraph blocks rather than
    documents.** See :func:`split_document` and ``one_sense.pmc_oa.splitter_cost``.
    The diagnostics carry how many sampled documents produce **byte-equal** span
    lists under the chunked split and under the whole-document split, so the
    substitution is measured rather than argued. Only documents below
    :data:`WHOLE_DOCUMENT_CHECK_CHARACTERS` are checked, because the
    whole-document split of a long article is the thing that does not finish --
    which is a stated bias in the check and not a hidden one.

    **The splitter is profile-independent, and that is checked rather than
    believed.** ``Tokenizer`` is built from a ``Config``, so a profile could in
    principle change the split. A shortfall in
    ``profile_agreement_documents_identical`` invalidates sharing the table.

    Args:
        articles: The sample.

    Returns:
        ``({pmcid: [(start, end), ...]}, work counts)``.
    """
    tokenizer = Tokenizer(Config.for_profile(ExtractionProfile[AUDIT_PROFILE.upper()]))
    others = [
        Tokenizer(Config.for_profile(ExtractionProfile[name.upper()]))
        for name in PROFILES
        if name != AUDIT_PROFILE
    ]
    rng = random.Random(AUDIT_SEED)
    short = [
        index
        for index, article in enumerate(articles)
        if len(document_text(article)) <= WHOLE_DOCUMENT_CHECK_CHARACTERS
    ]
    checked = set(rng.sample(short, min(SPLITTER_CHECK_DOCUMENTS, len(short))))
    table: Dict[int, List[Tuple[int, int]]] = {}
    work: Dict[str, int] = {
        "sentence_splitter_calls": 0,
        "paragraph_blocks": 0,
        "sentences": 0,
        "characters": 0,
        "documents_short_enough_to_check_whole": len(short),
        "profile_agreement_documents_checked": 0,
        "profile_agreement_documents_identical": 0,
        "whole_document_agreement_documents_checked": 0,
        "whole_document_agreement_documents_identical": 0,
        "whole_document_sentences": 0,
        "chunked_sentences_on_the_same_documents": 0,
    }
    started = time.perf_counter()
    for index, article in enumerate(articles):
        text = document_text(article)
        blocks = paragraph_blocks(text)
        spans = split_document(tokenizer, text)
        work["sentence_splitter_calls"] += len(blocks)
        work["paragraph_blocks"] += len(blocks)
        work["sentences"] += len(spans)
        work["characters"] += len(text)
        table[article.pmcid] = spans
        if index in checked:
            work["profile_agreement_documents_checked"] += 1
            if all(split_document(other, text) == spans for other in others):
                work["profile_agreement_documents_identical"] += 1
            work["whole_document_agreement_documents_checked"] += 1
            whole = [(int(a), int(b)) for a, b in tokenizer.split_sentences(text)]
            if whole == spans:
                work["whole_document_agreement_documents_identical"] += 1
            work["whole_document_sentences"] += len(whole)
            work["chunked_sentences_on_the_same_documents"] += len(spans)
    diagnostics: Dict[str, object] = dict(work)
    diagnostics["wall_clock_seconds_unarmed_note"] = round(time.perf_counter() - started, 2)
    diagnostics["machine"] = environment()
    return table, diagnostics


def resolver_groups(
    articles: Sequence[Article], profile: str, sentences: Dict[int, List[Tuple[int, int]]]
) -> Tuple[List[DocumentGroups], dict]:
    """Run one operating point over every document and group its definitions.

    Args:
        articles: The sample.
        profile: One of ``bench.run_monoculture.PROFILES``.
        sentences: The shared span table from :func:`sentence_span_table`.

    Returns:
        ``(per-document groups, work counts)``. The work counts are the point:
        a rate over an unstated number of extractor calls is not a rate.
    """
    from acronymkit import AcronymEngine

    engine = AcronymEngine(Config.for_profile(ExtractionProfile[profile.upper()]))
    documents: List[DocumentGroups] = []
    work: Dict[str, int] = {
        "documents": 0,
        "characters": 0,
        "extractor_calls": 0,
        "definition_pairs_offered": 0,
        "definition_pairs_landing_in_no_sentence_span": 0,
    }
    started = time.perf_counter()
    for article in articles:
        text = document_text(article)
        work["documents"] += 1
        work["characters"] += len(text)
        work["extractor_calls"] += 1
        spans = sentences[article.pmcid]
        groups: Dict[str, List[Definition]] = {}
        for pair in engine.extract_definitions(text):
            work["definition_pairs_offered"] += 1
            span = pair.short_form_span
            start = int(span[0]) if span else 0
            sentence_span = enclosing_sentence(spans, start)
            if sentence_span is None:
                work["definition_pairs_landing_in_no_sentence_span"] += 1
            groups.setdefault(pair.short_form, []).append(
                Definition(pair.short_form, pair.long_form, start, sentence_span)
            )
        documents.append(DocumentGroups(article.pmcid, text, groups))
    diagnostics: Dict[str, object] = dict(work)
    diagnostics["wall_clock_seconds_unarmed_note"] = round(time.perf_counter() - started, 2)
    diagnostics["machine"] = environment()
    return documents, diagnostics


def splitter_agreement_record(
    articles: Sequence[Article], sentences: Dict[int, List[Tuple[int, int]]], context: dict
) -> dict:
    """What the paragraph-chunked split costs **the number this file publishes**.

    R11's question applied to a substitution, and asked at the right level. The
    obvious check -- are the two span lists byte-equal -- answers *no* by
    construction and says nothing: chunking at a blank line adds a boundary at
    every blank line, so the lists differ wherever a paragraph's last fragment
    would otherwise have run into the next paragraph's first sentence. That
    difference matters only if it moves the published quantity, so the published
    quantity is what is compared.

    On a seeded sample of documents short enough for the quadratic
    whole-document split to finish, this recomputes
    ``a2_new_coverage_pct_of_licensed`` twice -- once from the chunked table the
    run uses, once from a whole-document split -- and reports both. It also
    reports two diagnostics: how often the engine's own attached sentence is the
    one the chunked table assigns, and whether turning
    ``extraction_capture_sentences`` on changes which pairs are found at all,
    since the coverage figure must be about the shipped pair set.

    Args:
        articles: The sample to draw from.
        sentences: The shared span table.
        context: Fields copied into the record.

    Returns:
        The record.
    """
    from acronymkit import AcronymEngine

    rng = random.Random(AUDIT_SEED)
    short = [
        article
        for article in articles
        if len(document_text(article)) <= WHOLE_DOCUMENT_CHECK_CHARACTERS
    ]
    drawn = rng.sample(short, min(SPLITTER_CHECK_DOCUMENTS, len(short)))
    config = Config.for_profile(ExtractionProfile[AUDIT_PROFILE.upper()])
    plain = AcronymEngine(config)
    capturing = AcronymEngine(config.model_copy(update={"extraction_capture_sentences": True}))
    tokenizer = Tokenizer(config)
    record: dict = dict(context)
    record["profile"] = AUDIT_PROFILE
    record["seed"] = AUDIT_SEED
    record["documents"] = len(drawn)
    record["documents_short_enough_to_check"] = len(short)
    record["document_character_ceiling"] = WHOLE_DOCUMENT_CHECK_CHARACTERS
    agreeing = 0
    disagreeing = 0
    uncaptured = 0
    pair_sets_identical = 0
    chunked_documents: List[DocumentGroups] = []
    whole_documents: List[DocumentGroups] = []
    for article in drawn:
        text = document_text(article)
        chunked_spans = sentences[article.pmcid]
        whole_spans = [(int(a), int(b)) for a, b in tokenizer.split_sentences(text)]
        without = [(p.short_form, p.long_form) for p in plain.extract_definitions(text)]
        pairs = list(capturing.extract_definitions(text))
        if [(p.short_form, p.long_form) for p in pairs] == without:
            pair_sets_identical += 1
        chunked: Dict[str, List[Definition]] = {}
        whole: Dict[str, List[Definition]] = {}
        for pair in pairs:
            span = pair.short_form_span
            at = int(span[0]) if span else 0
            chunked.setdefault(pair.short_form, []).append(
                Definition(
                    pair.short_form, pair.long_form, at, enclosing_sentence(chunked_spans, at)
                )
            )
            whole.setdefault(pair.short_form, []).append(
                Definition(pair.short_form, pair.long_form, at, enclosing_sentence(whole_spans, at))
            )
            if not pair.sentence:
                uncaptured += 1
                continue
            mine = enclosing_sentence(chunked_spans, at)
            surface = text[mine[0] : mine[1]].strip() if mine else ""
            if surface == pair.sentence.strip():
                agreeing += 1
            else:
                disagreeing += 1
        chunked_documents.append(DocumentGroups(article.pmcid, text, chunked))
        whole_documents.append(DocumentGroups(article.pmcid, text, whole))
    chunked_a2 = a2_record(chunked_documents, AUDIT_PROFILE, {})
    whole_a2 = a2_record(whole_documents, AUDIT_PROFILE, {})
    record["documents_whose_pair_set_is_identical_with_capture_on"] = pair_sets_identical
    record["definitions_whose_sentence_matches_the_engines"] = agreeing
    record["definitions_whose_sentence_differs_from_the_engines"] = disagreeing
    record["definitions_the_engine_captured_no_sentence_for"] = uncaptured
    record["definition_sentence_agreement_pct"] = round(
        100 * agreeing / max(agreeing + disagreeing, 1), 2
    )
    record["licensed_occurrences_on_the_sample"] = chunked_a2["licensed_occurrences"]
    record["coverage_pct_chunked_split"] = chunked_a2["a2_new_coverage_pct_of_licensed"]
    record["coverage_pct_whole_document_split"] = whole_a2["a2_new_coverage_pct_of_licensed"]
    record["coverage_pct_difference"] = round(
        chunked_a2["a2_new_coverage_pct_of_licensed"] - whole_a2["a2_new_coverage_pct_of_licensed"],
        2,
    )
    record["note"] = (
        "The sample is the short half of the corpus by construction, because the "
        "whole-document arm is the one that does not finish on a long article. Nothing here "
        "says the two splits agree as well on documents longer than the ceiling."
    )
    return record


def resolver_record(
    documents: Sequence[DocumentGroups], profile: str, work: dict, context: dict
) -> Tuple[dict, Dict[str, List[Tuple[int, str]]]]:
    """The violation rate a document-level resolver would face, and its decomposition.

    Two populations are reported side by side and neither is the headline on its
    own. The unrestricted one counts every short form the extractor keyed,
    including ``i.e`` and single letters, because A2 as specified would key those
    too. The ``term_shaped`` one is the sub-population an abbreviation roster
    rule admits, and it is the population a caller would recognise as
    abbreviations.

    Args:
        documents: Per-document groups.
        profile: The operating point.
        work: Work counts from :func:`resolver_groups`.
        context: Fields copied into the record.

    Returns:
        ``(record, {class: group keys})``. The second value is the frame the
        hand adjudication draws from, **per class**: the ladder has to be
        measured in both directions, so ``surface`` and ``refinement`` are
        adjudicated too. A ladder that folds a genuine second sense into
        ``surface`` would understate the correctness problem, and nothing but a
        read of those groups could show it.
    """
    record: dict = dict(context)
    record["instrument"] = "resolver"
    record["profile"] = profile
    record.update(work)
    totals = {"all": [0, 0], "term_shaped": [0, 0]}
    classes: Dict[str, Counter] = {"all": Counter(), "term_shaped": Counter()}
    frames: Dict[str, List[Tuple[int, str]]] = {
        "surface": [],
        "refinement": [],
        "distinct": [],
    }
    documents_with_a_violation: Set[int] = set()
    for document in documents:
        unambiguous = document.unambiguous()
        for short_form in document.groups:
            forms = document.expansions(short_form)
            shaped = term_shaped(short_form)
            for population in ("all", "term_shaped"):
                if population == "term_shaped" and not shaped:
                    continue
                totals[population][0] += 1
                if len(forms) > 1:
                    totals[population][1] += 1
            if len(forms) < 2:
                continue
            label = classify_group(forms, unambiguous)
            classes["all"][label] += 1
            documents_with_a_violation.add(document.pmcid)
            if shaped:
                classes["term_shaped"][label] += 1
                frames[label].append((document.pmcid, short_form))
    for population in ("all", "term_shaped"):
        groups, violations = totals[population]
        record[f"{population}.short_form_groups"] = groups
        record[f"{population}.groups_with_two_or_more_expansions"] = violations
        record[f"{population}.violation_pct"] = round(100 * violations / max(groups, 1), 2)
        for label in ("surface", "refinement", "distinct"):
            record[f"{population}.class_{label}"] = classes[population][label]
            record[f"{population}.class_{label}_pct_of_violations"] = round(
                100 * classes[population][label] / max(violations, 1), 2
            )
            record[f"{population}.class_{label}_pct_of_groups"] = round(
                100 * classes[population][label] / max(groups, 1), 2
            )
    violating_types: Counter = Counter()
    for document in documents:
        for short_form in document.groups:
            if term_shaped(short_form) and len(document.expansions(short_form)) > 1:
                violating_types[short_form] += 1
    record["term_shaped.distinct_violating_short_form_types"] = len(violating_types)
    if violating_types:
        top, top_count = violating_types.most_common(1)[0]
        record["term_shaped.most_frequent_violating_short_form"] = top
        record["term_shaped.most_frequent_violating_short_form_documents"] = top_count
    record["documents_with_a_violation"] = len(documents_with_a_violation)
    record["documents_with_a_violation_pct"] = round(
        100 * len(documents_with_a_violation) / max(len(documents), 1), 2
    )
    record["note"] = (
        "No gold. This is the population A2 must arbitrate, not the population that is "
        "genuinely ambiguous: a group whose second expansion is extractor noise is counted "
        "because A2 would still have to choose, and would license the choice document-wide."
    )
    return record, frames


# ---------------------------------------------------------------------------
# 6. A2 in A2's own terms
# ---------------------------------------------------------------------------
def a2_record(documents: Sequence[DocumentGroups], profile: str, context: dict) -> dict:
    """Price A2: what it wins, what it would get wrong, and against what.

    The model is A2 as specified -- commit to the first definition in document
    order, license every occurrence of that short form at or after it. Only
    ``term_shaped`` short forms are licensed, which is the **generous** reading:
    licensing single letters as well would raise every error figure here.

    Args:
        documents: Per-document groups.
        profile: The operating point.
        context: Fields copied into the record.

    Returns:
        The record.
    """
    record: dict = dict(context)
    record["profile"] = profile
    record["model"] = (
        "commit to the first definition in document order; license every whole-token "
        "occurrence of that short form at or after it; term_shaped short forms only"
    )
    licensed = 0
    licensed_unbounded = 0
    outside_sentence = 0
    inside_sentence = 0
    floor: Counter = Counter()
    ceiling: Counter = Counter()
    licensed_by_class: Counter = Counter()
    groups_by_class: Counter = Counter()
    scans = 0
    for document in documents:
        unambiguous = document.unambiguous()
        for short_form, definitions in document.groups.items():
            if not term_shaped(short_form):
                continue
            forms = document.expansions(short_form)
            ordered = sorted(definitions, key=lambda d: d.short_start)
            first = ordered[0].short_start
            scans += 1
            offsets = [at for at in bounded_occurrences(document.text, short_form) if at >= first]
            unbounded = document.text.count(short_form)
            licensed += len(offsets)
            licensed_unbounded += unbounded
            sentences = [d.sentence_span for d in ordered if d.sentence_span is not None]
            for at in offsets:
                covered = any(start <= at < end for start, end in sentences)
                if covered:
                    inside_sentence += 1
                else:
                    outside_sentence += 1
            label = "unambiguous" if len(forms) < 2 else classify_group(forms, unambiguous)
            groups_by_class[label] += 1
            licensed_by_class[label] += len(offsets)
            if len(forms) < 2:
                continue
            committed = normalise(ordered[0].long_form)
            # Intersected with the licensed set on purpose. A definition site is
            # normally a whole-token occurrence, but nothing guarantees it -- a
            # short form inside a hyphenated compound is not -- and a floor that
            # counted a position the model never licenses would be an error
            # attributed to A2 that A2 could not commit.
            licensed_here = set(offsets)
            wrong_sites = {
                d.short_start
                for d in ordered
                if normalise(d.long_form) != committed and d.short_start in licensed_here
            }
            floor[label] += len(wrong_sites)
            ceiling[label] += max(len(offsets) - 1, 0)
    record["licensed_occurrences"] = licensed
    record["licensed_occurrences_unbounded_substring_count"] = licensed_unbounded
    # The occurrence-weighted counterpart of the group rate. A short form with two
    # expansions is not one observation: it is however many times the document
    # writes it, and the two rates are not the same number.
    multi = sum(licensed_by_class[label] for label in ("surface", "refinement", "distinct"))
    record["licensed_occurrences_under_multi_expansion_groups"] = multi
    record["licensed_occurrences_under_multi_expansion_groups_pct"] = round(
        100 * multi / max(licensed, 1), 2
    )
    record["short_form_groups_licensed"] = sum(groups_by_class.values())
    record["occurrence_scans"] = scans
    record["licensed_occurrences_inside_a_definition_sentence"] = inside_sentence
    record["licensed_occurrences_outside_every_definition_sentence"] = outside_sentence
    record["a2_new_coverage_pct_of_licensed"] = round(100 * outside_sentence / max(licensed, 1), 2)
    record["a2_new_coverage_multiple_of_current"] = round(
        outside_sentence / max(inside_sentence, 1), 2
    )
    for label in ("unambiguous", "surface", "refinement", "distinct"):
        record[f"groups_{label}"] = groups_by_class[label]
        record[f"licensed_occurrences_{label}"] = licensed_by_class[label]
        record[f"licensed_occurrences_{label}_pct"] = round(
            100 * licensed_by_class[label] / max(licensed, 1), 2
        )
        if label == "unambiguous":
            continue
        record[f"wrong_floor_{label}"] = floor[label]
        record[f"wrong_floor_{label}_pct_of_licensed"] = round(
            100 * floor[label] / max(licensed, 1), 4
        )
        record[f"wrong_ceiling_{label}"] = ceiling[label]
        record[f"wrong_ceiling_{label}_pct_of_licensed"] = round(
            100 * ceiling[label] / max(licensed, 1), 2
        )
    correctness_floor = floor["distinct"] + floor["refinement"]
    correctness_ceiling = ceiling["distinct"] + ceiling["refinement"]
    record["wrong_floor_correctness_pct_of_licensed"] = round(
        100 * correctness_floor / max(licensed, 1), 4
    )
    record["wrong_ceiling_correctness_pct_of_licensed"] = round(
        100 * correctness_ceiling / max(licensed, 1), 2
    )
    record["comparator"] = (
        "the mechanism A2 replaces answers at NONE of the "
        f"{outside_sentence} out-of-sentence occurrences, so its error rate there is 0 by "
        "declining rather than by being right. A2 buys coverage and pays in correctness."
    )
    return record


# ---------------------------------------------------------------------------
# 7. Instrument G -- how much the roster undercounts
# ---------------------------------------------------------------------------
def bridge_record(
    articles: Sequence[Article],
    documents: Sequence[DocumentGroups],
    profile: str,
    context: dict,
) -> dict:
    """Where the author declared one sense, does the document contain a competitor?

    This is the measurement that says how far the roster's rate is from the
    document's. For every short form an author rostered exactly once, it asks
    whether the extractor offered an expansion for that same short form in the
    same document that the roster's own expansion does not fold into.

    Args:
        articles: The sample.
        documents: Per-document groups under ``profile``.
        profile: The operating point.
        context: Fields copied into the record.

    Returns:
        The record.
    """
    record: dict = dict(context)
    record["profile"] = profile
    by_id = {document.pmcid: document for document in documents}
    singly_rostered = 0
    reached = 0
    competing = 0
    classes: Counter = Counter()
    examples: List[dict] = []
    for article in articles:
        if not article.roster:
            continue
        document = by_id.get(article.pmcid)
        if document is None:
            continue
        unambiguous = document.unambiguous()
        grouped = group_pairs(article.roster, fold_key=False)
        for short_form, forms in grouped.items():
            if len(forms) != 1:
                continue
            singly_rostered += 1
            offered = document.groups.get(short_form)
            if not offered:
                continue
            reached += 1
            candidates = [forms[0], *document.expansions(short_form)]
            if len({normalise(value) for value in candidates}) < 2:
                continue
            competing += 1
            label = classify_group(candidates, unambiguous)
            classes[label] += 1
            if len(examples) < 40:
                examples.append(
                    {
                        "pmcid": article.pmcid,
                        "short_form": short_form,
                        "rostered": forms[0],
                        "offered": document.expansions(short_form),
                        "class": label,
                    }
                )
    record["singly_rostered_short_forms"] = singly_rostered
    record["also_defined_in_the_text_by_the_extractor"] = reached
    record["with_an_expansion_the_roster_does_not_carry"] = competing
    record["competing_pct_of_reached"] = round(100 * competing / max(reached, 1), 2)
    for label in ("surface", "refinement", "distinct"):
        record[f"class_{label}"] = classes[label]
    record["examples"] = examples
    record["note"] = (
        "A competitor here is not proof of a second sense: the extractor has no gold. "
        "It is proof that the roster does not settle the question, which is what the "
        "roster's own rate would otherwise be read as doing."
    )
    return record


# ---------------------------------------------------------------------------
# 8. The hand adjudication of the `distinct` class
# ---------------------------------------------------------------------------
def audit_sample(keys: Sequence[Tuple[int, str]], size: int, salt: int) -> List[Tuple[int, str]]:
    """A seeded draw over one class's frame, in a fixed order.

    Args:
        keys: Every group of one class under :data:`AUDIT_PROFILE`, restricted to
            ``term_shaped`` short forms.
        size: How many to draw.
        salt: Added to :data:`AUDIT_SEED` so the three classes do not share a
            shuffle.

    Returns:
        Up to ``size`` keys, sorted before shuffling so the draw does not
        inherit dictionary order.
    """
    frame = sorted(set(keys))
    rng = random.Random(AUDIT_SEED + salt)
    rng.shuffle(frame)
    return frame[:size]


def audit_record(
    documents: Sequence[DocumentGroups],
    frames: Dict[str, List[Tuple[int, str]]],
    context: dict,
) -> dict:
    """What one annotator found inside each mechanical class.

    **The ladder is adjudicated in both directions and that is the point.** A
    sample of ``distinct`` says how much of the residual class is a real second
    sense, a near-synonym, or extractor noise. Samples of ``surface`` and
    ``refinement`` say whether the ladder ever folds a real second sense into a
    class this page describes as a normalisation problem -- which is the failure
    that would make every correctness figure here too small, and the one a
    ``distinct``-only audit could not see.

    Args:
        documents: Per-document groups under :data:`AUDIT_PROFILE`.
        frames: ``{class: group keys}`` from :func:`resolver_record`.
        context: Fields copied into the record.

    Returns:
        The record, including the labels that matched no drawn group -- a firing
        count that makes a moved population visible rather than silently
        re-weighted.
    """
    record: dict = dict(context)
    record["profile"] = AUDIT_PROFILE
    record["seed"] = AUDIT_SEED
    record["adjudicators"] = 1
    record["annotator"] = "the author of this runner; no second reader"
    record["label_vocabulary"] = sorted(AUDIT_LABEL_VOCABULARY)
    by_id = {document.pmcid: document for document in documents}
    rows: List[dict] = []
    drawn_keys: Set[str] = set()
    unlabelled: List[str] = []
    for klass, salt in AUDIT_CLASS_SALT.items():
        size = AUDIT_SAMPLE_SIZES[klass]
        frame = frames.get(klass, [])
        drawn = audit_sample(frame, size, salt)
        record[f"{klass}.frame_size"] = len(set(frame))
        record[f"{klass}.sample_size"] = len(drawn)
        record[f"{klass}.sample_pct_of_frame"] = round(
            100 * len(drawn) / max(len(set(frame)), 1), 2
        )
        labels: Counter = Counter()
        for pmcid, short_form in drawn:
            key = f"PMC{pmcid}\t{short_form}"
            drawn_keys.add(key)
            label = AUDIT_LABELS.get(key)
            if label is None:
                unlabelled.append(key)
            else:
                labels[label] += 1
            document = by_id.get(pmcid)
            rows.append(
                {
                    "class": klass,
                    "pmcid": pmcid,
                    "short_form": short_form,
                    "expansions": document.expansions(short_form) if document else [],
                    "label": label,
                }
            )
        record[f"{klass}.labels_applied"] = sum(labels.values())
        for label in sorted(AUDIT_LABEL_VOCABULARY):
            record[f"{klass}.label_{label}"] = labels[label]
            record[f"{klass}.label_{label}_pct"] = round(
                100 * labels[label] / max(sum(labels.values()), 1), 2
            )
    record["labels_in_the_table_matching_no_drawn_group"] = sorted(set(AUDIT_LABELS) - drawn_keys)
    record["drawn_groups_with_no_label"] = unlabelled
    record["rows"] = rows
    record["note"] = (
        "One annotator, one operating point, one domain, and the annotator wrote the ladder "
        "being adjudicated. A rate off this sample is a rate about one class under "
        "AUDIT_PROFILE and nothing wider. Every frame is term_shaped only, so it excludes "
        "every single-letter and discourse-marker key the extractor also collides."
    )
    return record


def clopper_pearson(successes: int, trials: int, *, level: float = 0.95) -> Tuple[float, float]:
    """An exact binomial interval, by bisection on the binomial tail.

    Written out rather than imported because this package has no numerical
    dependency and is not acquiring one for a benchmark. Bisection on a
    monotone tail is exact to the tolerance below, and
    ``tests/test_one_sense.py`` pins three published Clopper-Pearson intervals
    against it.

    Args:
        successes: Events observed.
        trials: Draws.
        level: Coverage.

    Returns:
        ``(low, high)`` as proportions. ``(0.0, 0.0)`` for zero trials.
    """
    if trials <= 0:
        return 0.0, 0.0
    alpha = (1.0 - level) / 2.0

    def upper_tail(probability: float) -> float:
        """P(X >= successes) under this probability."""
        total = 0.0
        for k in range(successes, trials + 1):
            total += math.comb(trials, k) * probability**k * (1 - probability) ** (trials - k)
        return total

    def lower_tail(probability: float) -> float:
        """P(X <= successes) under this probability."""
        total = 0.0
        for k in range(0, successes + 1):
            total += math.comb(trials, k) * probability**k * (1 - probability) ** (trials - k)
        return total

    def bisect(target: float, tail: Callable[[float], float], rising: bool) -> float:
        low, high = 0.0, 1.0
        for _ in range(80):
            middle = (low + high) / 2.0
            value = tail(middle)
            if (value < target) == rising:
                low = middle
            else:
                high = middle
        return (low + high) / 2.0

    low = 0.0 if successes == 0 else bisect(alpha, upper_tail, True)
    high = 1.0 if successes == trials else bisect(alpha, lower_tail, False)
    return low, high


def a2_projection_record(audit: dict, a2: dict, resolver: dict, context: dict) -> dict:
    """Deliverable three: A2's error rate, split by what the ambiguity actually is.

    The mechanical classes say how many groups carry two expansions. The hand
    adjudication says what share of each class is a **second sense** rather than
    a spelling, a truncation or extractor noise. This multiplies the two, so
    that the correctness figure a reader takes away is about genuine ambiguity
    and not about the whole violating population.

    **Every label is projected, not only ``genuine``, and the ``artefact`` rows
    are the ones the commissioning question did not ask about.** A2's exposure
    turns out not to be dominated by one-sense-per-discourse at all: the largest
    adjudicated share of the residual class is a long form that is not an
    expansion of anything, which a document-level licence would propagate from
    one sentence to a whole article. That is a different failure from ambiguity
    and it is bigger.

    **Every interval here is the sampling interval on the adjudication and
    nothing else.** It carries no uncertainty about the annotator, who is one
    person and wrote the ladder being adjudicated; and it carries none about
    the extractor, which supplied the population.

    Args:
        audit: The adjudication record.
        a2: The A2 record for :data:`AUDIT_PROFILE`.
        resolver: The resolver record for the same profile.
        context: Fields copied into the record.

    Returns:
        The record.
    """
    record: dict = dict(context)
    record["profile"] = AUDIT_PROFILE
    record["method"] = (
        "per label and per class, the adjudicated share times that class's group count, "
        "licensed occurrences and error bounds; intervals are Clopper-Pearson on the "
        "adjudication draw alone"
    )
    licensed = max(int(a2["licensed_occurrences"]), 1)
    shaped_groups = max(int(resolver["term_shaped.short_form_groups"]), 1)
    for label in sorted(AUDIT_LABEL_VOCABULARY):
        groups = 0.0
        groups_low = 0.0
        groups_high = 0.0
        floor = 0.0
        ceiling = 0.0
        ceiling_low = 0.0
        ceiling_high = 0.0
        occurrences = 0.0
        for klass in sorted(AUDIT_SAMPLE_SIZES):
            successes = int(audit[f"{klass}.label_{label}"])
            trials = int(audit[f"{klass}.labels_applied"])
            frame = int(audit[f"{klass}.frame_size"])
            share = successes / trials if trials else 0.0
            low, high = clopper_pearson(successes, trials)
            record[f"{label}.{klass}.of_sample"] = f"{successes} of {trials}"
            record[f"{label}.{klass}.share_pct"] = round(100 * share, 2)
            record[f"{label}.{klass}.share_ci_low_pct"] = round(100 * low, 2)
            record[f"{label}.{klass}.share_ci_high_pct"] = round(100 * high, 2)
            record[f"{label}.{klass}.projected_groups"] = round(frame * share, 1)
            groups += frame * share
            groups_low += frame * low
            groups_high += frame * high
            floor += float(a2.get(f"wrong_floor_{klass}", 0)) * share
            ceiling += float(a2.get(f"wrong_ceiling_{klass}", 0)) * share
            ceiling_low += float(a2.get(f"wrong_ceiling_{klass}", 0)) * low
            ceiling_high += float(a2.get(f"wrong_ceiling_{klass}", 0)) * high
            occurrences += float(a2.get(f"licensed_occurrences_{klass}", 0)) * share
        record[f"{label}.projected_groups"] = round(groups, 1)
        record[f"{label}.projected_groups_ci_low"] = round(groups_low, 1)
        record[f"{label}.projected_groups_ci_high"] = round(groups_high, 1)
        record[f"{label}.projected_groups_pct_of_term_shaped_groups"] = round(
            100 * groups / shaped_groups, 3
        )
        record[f"{label}.projected_groups_ci_low_pct_of_term_shaped_groups"] = round(
            100 * groups_low / shaped_groups, 3
        )
        record[f"{label}.projected_groups_ci_high_pct_of_term_shaped_groups"] = round(
            100 * groups_high / shaped_groups, 3
        )
        record[f"{label}.projected_licensed_occurrences"] = round(occurrences, 1)
        record[f"{label}.projected_licensed_occurrences_pct"] = round(
            100 * occurrences / licensed, 3
        )
        record[f"{label}.projected_wrong_floor"] = round(floor, 1)
        record[f"{label}.projected_wrong_floor_pct_of_licensed"] = round(100 * floor / licensed, 4)
        record[f"{label}.projected_wrong_ceiling"] = round(ceiling, 1)
        record[f"{label}.projected_wrong_ceiling_pct_of_licensed"] = round(
            100 * ceiling / licensed, 3
        )
        record[f"{label}.projected_wrong_ceiling_ci_low_pct_of_licensed"] = round(
            100 * ceiling_low / licensed, 3
        )
        record[f"{label}.projected_wrong_ceiling_ci_high_pct_of_licensed"] = round(
            100 * ceiling_high / licensed, 3
        )
    record["artefact_note"] = (
        "For an `artefact` group the label says one of its expansions is not an expansion at "
        "all; it does NOT say which one came first, and A2 commits to whichever did. So the "
        "artefact rows are EXPOSURE and not error: the error is somewhere between zero and "
        "the ceiling, and this measurement does not locate it."
    )
    record["comparator_error_rate_pct"] = 0.0
    record["comparator"] = (
        "the sentence-scoped mechanism A2 replaces answers at none of the out-of-sentence "
        "occurrences, so the rate A2 is measured against is zero by declining rather than by "
        "being right"
    )
    record["note"] = (
        "The ceiling assumes every licensed occurrence of a genuinely ambiguous short form "
        "except the committed definition site carries the other sense, which no document does. "
        "It is a bound, not an estimate, and the floor below it is the part that needs no "
        "annotation at all."
    )
    return record


# ---------------------------------------------------------------------------
# 9. Entry point
# ---------------------------------------------------------------------------
def build(
    articles: Sequence[Article], profiles: Sequence[str]
) -> Tuple[dict, Dict[str, List[Tuple[int, str]]]]:
    """Every record this runner writes.

    Args:
        articles: The sample.
        profiles: Operating points to run.

    Returns:
        ``({run id: record}, {class: group keys} under AUDIT_PROFILE)``.
    """
    context = {
        "corpus": "pmc_oa_same_article_genre",
        "unit": "one (document, short form) group over abstract + body of one JATS file",
        "gold_provenance": "roster instrument: each article's own <def-list>; "
        "resolver instrument: none, by design",
        "pooled_gold": False,
        "role": "single_annotator_reference",
    }
    recorded: Dict[str, dict] = {}
    recorded["one_sense.pmc_oa.sample"] = {
        **context,
        "articles": len(articles),
        "articles_with_a_roster": sum(1 for article in articles if article.roster),
        "roster_pairs_declared": sum(len(article.roster) for article in articles),
        "characters": sum(len(document_text(article)) for article in articles),
        "profiles": list(profiles),
        "ladder_stop_words": sorted(LADDER_STOP_WORDS),
        "audit_seed": AUDIT_SEED,
        "audit_sample_sizes": dict(AUDIT_SAMPLE_SIZES),
    }
    for admitted in (True, False):
        for fold_key in (False, True):
            slug = "admitted" if admitted else "raw"
            keying = "case_folded" if fold_key else "case_sensitive"
            recorded[f"one_sense.pmc_oa.roster.{slug}.{keying}"] = roster_record(
                articles, fold_key=fold_key, admitted=admitted, context=context
            )
    recorded["one_sense.pmc_oa.splitter_cost"] = splitter_cost_record(context)
    sentences, splitter_work = sentence_span_table(articles)
    recorded["one_sense.pmc_oa.sample"].update(
        {f"sentence_table.{key}": value for key, value in splitter_work.items()}
    )
    recorded["one_sense.pmc_oa.splitter_agreement"] = splitter_agreement_record(
        articles, sentences, context
    )
    audit_frames: Dict[str, List[Tuple[int, str]]] = {}
    audit_documents: List[DocumentGroups] = []
    for profile in profiles:
        documents, work = resolver_groups(articles, profile, sentences)
        record, frames = resolver_record(documents, profile, work, context)
        recorded[f"one_sense.pmc_oa.resolver.{profile}"] = record
        recorded[f"one_sense.pmc_oa.a2.{profile}"] = a2_record(documents, profile, context)
        recorded[f"one_sense.pmc_oa.bridge.{profile}"] = bridge_record(
            articles, documents, profile, context
        )
        if profile == AUDIT_PROFILE:
            audit_frames = frames
            audit_documents = documents
    if audit_documents:
        audit = audit_record(audit_documents, audit_frames, context)
        recorded["one_sense.pmc_oa.audit"] = audit
        recorded["one_sense.pmc_oa.a2_projected_genuine"] = a2_projection_record(
            audit,
            recorded[f"one_sense.pmc_oa.a2.{AUDIT_PROFILE}"],
            recorded[f"one_sense.pmc_oa.resolver.{AUDIT_PROFILE}"],
            context,
        )
    return recorded, audit_frames


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument(
        "--profile", action="append", choices=list(PROFILES), help="restrict to these profiles"
    )
    parser.add_argument(
        "--audit-sample",
        action="store_true",
        help="print the drawn distinct groups for hand adjudication and stop",
    )
    args = parser.parse_args(argv)

    articles, _ = load_articles(pinned_pmcids())
    profiles = list(args.profile or PROFILES)
    if args.audit_sample and AUDIT_PROFILE not in profiles:
        profiles.append(AUDIT_PROFILE)
    recorded, _audit_keys = build(articles, profiles)

    if args.audit_sample:
        for row in recorded["one_sense.pmc_oa.audit"]["rows"]:
            print(f"PMC{row['pmcid']}\t{row['short_form']}\t{row['expansions']}\t{row['label']}")
        return 0

    for slug in ("admitted", "raw"):
        for keying in ("case_sensitive", "case_folded"):
            record = recorded[f"one_sense.pmc_oa.roster.{slug}.{keying}"]
            print(
                f"roster {slug:<8} {keying:<14} "
                f"{record['groups_with_two_or_more_expansions']:>4} of "
                f"{record['short_form_groups']:>6} groups  "
                f"{record['violation_pct']:.4f} %  "
                f"surface {record['class_surface']} refinement {record['class_refinement']} "
                f"distinct {record['class_distinct']}"
            )
    print()
    for profile in profiles:
        record = recorded[f"one_sense.pmc_oa.resolver.{profile}"]
        print(
            f"resolver {profile:<15} all {record['all.groups_with_two_or_more_expansions']:>5} of "
            f"{record['all.short_form_groups']:>6} ({record['all.violation_pct']:.2f} %)   "
            f"term_shaped {record['term_shaped.groups_with_two_or_more_expansions']:>5} of "
            f"{record['term_shaped.short_form_groups']:>6} "
            f"({record['term_shaped.violation_pct']:.2f} %)"
        )
        print(
            f"  classes on term_shaped: surface {record['term_shaped.class_surface']}, "
            f"refinement {record['term_shaped.class_refinement']}, "
            f"distinct {record['term_shaped.class_distinct']}"
        )
        a2 = recorded[f"one_sense.pmc_oa.a2.{profile}"]
        print(
            f"  A2 licenses {a2['licensed_occurrences']:,} occurrences; "
            f"{a2['licensed_occurrences_outside_every_definition_sentence']:,} of them "
            f"({a2['a2_new_coverage_pct_of_licensed']:.2f} %) are new coverage"
        )
        print(
            f"  wrong, correctness classes: floor "
            f"{a2['wrong_floor_correctness_pct_of_licensed']:.4f} %  ceiling "
            f"{a2['wrong_ceiling_correctness_pct_of_licensed']:.2f} %"
        )
        bridge = recorded[f"one_sense.pmc_oa.bridge.{profile}"]
        print(
            f"  bridge: {bridge['with_an_expansion_the_roster_does_not_carry']} of "
            f"{bridge['also_defined_in_the_text_by_the_extractor']} singly-rostered short forms "
            f"the extractor also reached carry a competitor "
            f"({bridge['competing_pct_of_reached']:.2f} %)"
        )
        print()
    audit = recorded.get("one_sense.pmc_oa.audit")
    if audit:
        for klass in sorted(AUDIT_SAMPLE_SIZES):
            print(
                f"audit {klass:<11} {audit[f'{klass}.labels_applied']:>3} of "
                f"{audit[f'{klass}.sample_size']:>3} drawn from a frame of "
                f"{audit[f'{klass}.frame_size']:>4}  "
                f"genuine {audit[f'{klass}.label_genuine']:>3} "
                f"variant {audit[f'{klass}.label_variant']:>3} "
                f"artefact {audit[f'{klass}.label_artefact']:>3} "
                f"unclear {audit[f'{klass}.label_unclear']:>3}"
            )
        print()

    if args.save:
        path = save_results(recorded)
        print(f"saved {len(recorded)} run(s) to {path.relative_to(REPO_ROOT)}")
    print(environment())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
