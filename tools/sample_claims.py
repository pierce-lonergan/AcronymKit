#!/usr/bin/env python3
"""Draw a stratified sample of this project's claim-bearing sentences.

WHAT THIS MODULE USED TO BE, AND WHY THAT VERSION IS RETIRED UNGRADED
=====================================================================
Until this rewrite this file drew a **churn-weighted** sample of *claim-shaped
numbers* -- the residue of :mod:`tools.check_claims`, partitioned into ``round``
/ ``recent`` / ``cold`` by how lately their file was touched. **It never graded
a single claim.** It stood at ``n = 0`` from the day it shipped to the day it
was retired, so retiring it destroys no data, and nothing below is a
re-interpretation of a measurement somebody already made.

It is retired because its population **cannot contain this project's claims, and
that is a proof rather than a sample.**

    ``check_claims.prose_of()`` masks Markdown fenced blocks and then masks
    every inline code span (``_mask_fenced_blocks`` followed by
    ``_mask_spans(..., _INLINE_CODE)``). Claims are collected from that masked
    text. This project's house style writes every real figure inside an inline
    code span. **Therefore the set of house-style figures and the set of frame
    items are disjoint by construction** -- not rare in it, absent from it.

Measured with ``--audit-old-frame``. **Only the second row is stable**: ``0``
reachable is a consequence of ``prose_of``, not a count, so it does not drift.
Every other row moves with the tree, and moved measurably while this docstring
was being written, so re-run the command rather than quoting these.

===============================================================  =============
unfenced backticked figures in the scanned Markdown               ``3,279``
of those reachable by the old frame                               ``0``
Markdown characters in the scan set hidden inside fences          ``8.5`` %
old frame's population                                            ``2,139``
of it, one- and two-digit integers                                ``666`` (``31.1`` %)
its five commonest items  ``08`` 78, ``10`` 55, ``23`` 34, ``3.9`` 33, ``11`` 32
===============================================================  =============

A sibling workstream reported ``15`` backticked items in that population and
this rewrite first reproduced ``18``. **Both numbers are artefacts of the same
naive detector** -- it asked whether the claim's *text* occurred inside a span
somewhere on the line, and matched the digits of ``3.9`` inside ``` `>=3.9` ``
while the claim was the bare ``3.8`` further along. Checked against the masked
text the collector actually reads, all ``18`` came from unmasked prose. The
true count is ``0`` and it is ``0`` for a structural reason.

WHAT THE THREE OBSERVED MISSES ACTUALLY WERE
--------------------------------------------
The round that measured the old frame from the inside reported that its three
not-true verdicts fell outside the frame, and gave three different reasons. Two
of the three reasons are wrong, and the corrected account is what this design
is built on:

=========  ===========================  =========================================
verdict    reported reason              re-derived here
=========  ===========================  =========================================
claim 1    "lives in no document"       **false.** ``2.01`` and ``2.79`` are in
                                        ``docs/CLAIMS-LEDGER.md`` at four sites,
                                        two fenced and two in code spans
claim 15   outside ``SCAN_GLOBS``       correct -- ``.github/gates.toml`` -- *and*
                                        the figure is inside a code span there too
claim 10   "wrong clause, right digit"  correct, and its digits ``4,215`` are
                                        backticked, so they are masked as well
=========  ===========================  =========================================

**So one of the three lived outside the scanned file set, not two, and all three
were invisible for one shared reason: masking.** Widening the file set -- the
repair that suggested itself -- would have reached one of the three. Reading
code spans and fences reaches two. Changing the unit from a number to a sentence
reaches the third.

WHAT THIS FRAME IS
==================
Unit
    A **claim-bearing sentence**: a sentence of prose, a line of a fenced block,
    a line of a register file, or one sentence of a string in a committed run
    summary, that carries at least one digit. Nothing is masked. A figure in
    backticks is *more* likely to be a claim here, not less.

Population
    Four **channels**, because the errors this project makes are located by
    where a sentence was written rather than by how recently its file moved.

Armed numbers are **in** the population, deliberately, and this is the reversal
that matters most. The old frame sampled only what no gate backed, on the
argument that spending a grader on a machine-checked number measures the
grader. That argument holds for the *number* and fails for the *sentence around
it*: claim 10's ``4,215`` was correct and its clause named the wrong two
corpora. **A gate that re-derives a digit says nothing about the sentence it
sits in**, so a frame that skips armed figures cannot see this project's most
recent error at all.

WHY CHURN IS GONE
-----------------
It explained nothing and it was measured not to. ``docs/CLAIMS-LEDGER.md``
recorded that widening the window to ``40`` commits leaves ``14`` of ``2054``
numbers in a file nobody has touched, and called the premise "weak here" in the
same paragraph that shipped it. The round that graded under it drew exactly one
cold-stratum claim, so no stratum comparison was ever possible. And on a
**committed** tree the ``round`` stratum is empty: ``churn()`` with no ``--base``
diffs the working tree against ``HEAD``, so the moment a round commits its work
the headline stratum falls to ``N = 0`` and its ``12`` draws are silently
reallocated. Nothing on disk said the tool had to be run with ``--base``.

WHAT THIS FRAME STILL CANNOT DO, STATED RATHER THAN ASSERTED AWAY
==================================================================
1. **A claim with no digit and no quantifier is outside it.** Round two's
   worst catch was an identifier that had never existed in any revision. No
   sentence-shaped rule reaches that; it needs a symbol resolver.
2. **It cannot see a self-report that was never committed.** ``submitted`` draws
   from ``.github/run-summaries/``, and most workstreams file to a scratch
   directory instead. The forty-first gate already records that nothing in this
   repository writes those files for a real round.
3. **It cannot see a number that is in no file.** If a workstream computes a
   figure, states it in a report that is never committed and nobody re-derives
   it, no document-scanning frame reaches it, and this one does not either.
4. **It does not fix the precision wall.** Round five measured that: reaching a
   half-width of ``3`` points needs about ``600`` draws, roughly ``25`` rounds
   of ``24`` in total. **A better frame does not move that number.** It changes
   what the estimate is *of* -- from "the rate at which unbacked residue numbers
   are wrong", which nobody asked, to "the rate at which this project's written
   claims are wrong", which is the question. Precision is unchanged and the
   estimand is different. That is the whole of what the change buys.
5. **It is fitted to observations it cannot generalise from.** FIFTEEN of the
   twenty-three not-true verdicts across six rounds are attributable to a
   sentence; the design was argued from those. Round three's six are not
   itemised in its record and round four's two are given as counts only, so
   eight of twenty-three -- over a third -- say nothing about where errors
   live. The next three errors will be different in a way this rewrite cannot
   anticipate. ``--containment`` exists so that the coverage
   claim is a command anybody can re-run rather than a sentence in a docstring.

THE SERIES, AND THE BOOKKEEPING THAT WAS LEFT OPEN
===================================================
:data:`CLOSED_SERIES` used to record ``5`` rounds, ``120`` draws, ``20`` not
true. **Six rounds ran.** The closure was declared by this module before the
sixth round graded anything, and the sixth round then graded ``24`` claims under
the old frame anyway. The record file already carries the corrected arithmetic;
the constant here did not, and the round that found the mismatch declined to
change a sibling's constant and its tests at the end of a round and named it for
the next one instead. **This is that round**, so the constant now matches the
record: ``23`` of ``144`` = ``15.97`` %, Wilson ``[10.89, 22.83]``.

That series is closed **at six rounds, not five**, and this frame starts at
``n = 0`` for the second time in two rounds. **A second restart inside two
rounds is a bad sign about the instrument and it is recorded as one.** The
defence is narrow and it is the only one available: the frame being retired
never graded a claim, so no draw is being discarded and no rate is being
re-based. The R15 series is not reopened -- its unit was a sentence a workstream
volunteered about its own round, and a self-selected pool is the weakest frame
available -- but its ``144`` draws are the evidence this design was fitted to,
and its ``submitted`` channel is the nearest successor to it.

Nothing here is imported by the library and nothing here touches the network.

Usage::

    python tools/sample_claims.py --frame
    python tools/sample_claims.py --containment
    python tools/sample_claims.py --audit-old-frame
    python tools/sample_claims.py --draw --seed 20260909
    python tools/sample_claims.py --estimate GRADED.json --seed 20260909
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The channels, ordered. The allocation below is positional, so a reordered
#: tuple would silently re-aim the whole draw.
#:
#: ``submitted``  what a workstream said about its own round, committed.
#: ``register``   what a machine reads: the gate register and the workflows.
#: ``document``   live prose a reader lands on and a maintainer may edit.
#: ``record``     ``docs/DECISIONS.md``, which is append-only by policy.
CHANNELS: Tuple[str, ...] = ("submitted", "register", "document", "record")

#: Which files belong to which channel. Order matters: the first channel whose
#: patterns match a path wins, so ``docs/DECISIONS.md`` lands in ``record``
#: rather than in ``document`` even though ``docs/*.md`` also matches it.
CHANNEL_GLOBS: Dict[str, Tuple[str, ...]] = {
    "submitted": (".github/run-summaries/**/*.json",),
    "register": (".github/gates.toml", ".github/workflows/*.yml"),
    "record": ("docs/DECISIONS.md",),
    "document": (
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "docs/*.md",
        "docs/notes/*.md",
    ),
}

#: Paths excluded from every channel, with the reason each is here.
#:
#: A run-summary directory whose name begins with ``_`` is a **control
#: fixture**: three files that exist to make the forty-first gate fail on
#: demand. Their own text says *"this file is a control fixture and asserts
#: nothing about the library"* twelve times each. Measured before excluding
#: them: they were ``25`` of the ``136`` sentences in ``submitted`` -- ``18.4``
#: %% of the most valuable channel in the frame -- and the first exploratory
#: draw took ``3`` of its ``8`` submitted rows from them. Grading a sentence
#: that was written to be ungradeable measures nothing.
#:
#: One of those three files is also deliberately truncated mid-write and does
#: not parse; :func:`_json_units` drops it silently, which is correct and is
#: why the exclusion is by path rather than by parse failure.
EXCLUDED = (".github/run-summaries/_",)

#: The order in which a file is offered to the channels, first match winning.
#: **Not** :data:`CHANNELS`, which is display order: ``docs/*.md`` matches
#: ``docs/DECISIONS.md`` too, so ``record`` has to be offered the file first or
#: the append-only record lands in the editable channel.
CHANNEL_PRECEDENCE: Tuple[str, ...] = ("submitted", "register", "record", "document")

#: How many of a sample of :data:`DEFAULT_SIZE` each channel gets.
#:
#: **THIS IS NOT PROPORTIONAL AND THE PRICE IS PRINTED ON EVERY DRAW.**
#: Proportional allocation would give ``submitted`` zero draws -- it is under
#: two per cent of the population -- and ``submitted`` is the channel where
#: errors are *made*. :func:`design_effect` reports what the unequal allocation
#: costs the repository-wide estimate, whether or not it flatters the design.
#:
#: ``record`` keeps a non-zero allocation even though a finding there can never
#: be edited away: a false sentence in an append-only record is still false, the
#: project's own convention is to amend it with a new record, and a channel
#: drawn at zero is a channel whose rate is permanently unknown.
DEFAULT_ALLOCATION: Dict[str, int] = {
    "submitted": 8,
    "register": 4,
    "document": 8,
    "record": 4,
}

#: The per-round draw. Twenty-four, unchanged across both discontinuities, so
#: that the GRADER'S EFFORT is held fixed and a later comparison of what three
#: successive frames bought per unit of attention is possible.
DEFAULT_SIZE = 24

#: Verdicts a grader may return. ``UNCHECKABLE`` is IN the denominator and NOT
#: in the numerator: a claim nobody can check is not a claim shown to be true,
#: and excluding it would let a round improve its rate by making claims harder
#: to check.
VERDICTS: Tuple[str, ...] = ("TRUE", "FALSE", "MISLEADING", "UNCHECKABLE")

#: Which verdicts count as **not true**. Fixed in code, before any draw, because
#: the one thing every round of the predecessor series agreed on is that a
#: boundary reconstructed from prose after the fact is not a boundary.
NOT_TRUE: Tuple[str, ...] = ("FALSE", "MISLEADING")

#: A sentence must carry one of these to enter the frame. Digits only: every
#: quantifier-based rule tried here either admitted most of the tree or turned
#: on a word list nobody could defend, and blind spot 1 in the module docstring
#: is the honest statement of what that costs.
CLAIM_BEARING = re.compile(r"\d")

#: How many whitespace-separated tokens a unit needs before a grader can be
#: asked about it.
#:
#: **ADDED AFTER THE FIRST EXPLORATORY DRAW AND BEFORE THE FIRST GRADED ONE,
#: WHICH IS THE ONLY MOMENT IT IS FREE**, and the same moment at which the
#: retired frame took its one refinement. That draw put ``"> **9."`` and
#: ``"See `docs/DECISIONS.md` D-034."`` in front of a grader: the first is a
#: list marker the sentence splitter tore off a heading, the second is a
#: cross-reference whose only digit is a record number. Neither is a claim, and
#: neither can be graded ``TRUE`` or ``FALSE`` by anybody.
#:
#: Four, not more. Deliberately weak, because the cost of a rule that is too
#: strong falls on real claims: ``cold 431 of 2054`` is four tokens and is
#: exactly the kind of transcribed row this frame exists to reach. A frame
#: edited after a graded round would invalidate that round; this series stands
#: at ``n = 0``, so it does not.
MIN_UNIT_TOKENS = 4

#: The predecessor series, recorded here so that a future round comparing
#: against it compares against a number with a name on it rather than a memory.
#:
#: ``wilson_pct`` is TRANSCRIBED from the record file rather than computed;
#: ``tests/test_sample_claims.py`` recomputes it from ``per_round`` with
#: :func:`wilson` and requires agreement to two decimals. A constant derived
#: from the function it is checked against would check nothing.
CLOSED_SERIES: Dict[str, Any] = {
    "rounds": 6,
    "draws": 144,
    "not_true": 23,
    "rate_pct": 100.0 * 23 / 144,
    "wilson_pct": (10.89, 22.83),
    "per_round": (5, 5, 6, 2, 2, 3),
    "frame": "uniform draw from workstream-submitted claims_for_sampling sentences",
    "closed_at_five_until": (
        "this rewrite. The constant said 5 rounds / 120 draws / 20 not true while the record "
        "file said 6 / 144 / 23; the sixth round graded 24 claims under a frame this module "
        "had already declared closed."
    ),
}

#: Sites of claims a previous round GRADED NOT TRUE, kept so that the frame's
#: coverage is a command rather than an assertion. ``--containment`` reports how
#: many the live frame can actually reach.
#:
#: **These are the observations this design was fitted to, so containment of
#: them is a floor and not evidence of generality.** A site whose text has since
#: been corrected is kept: the frame's job is to be able to *reach* that
#: sentence, and the corrected sentence sits where the wrong one sat.
KNOWN_ERROR_SITES: Tuple[Dict[str, str], ...] = (
    {
        "round": "six",
        "verdict": "FALSE",
        "path": "docs/CLAIMS-LEDGER.md",
        "needle": "2.79",
        "why": "a design-effect pair spliced from two trees; fenced and code-spanned",
    },
    {
        "round": "six",
        "verdict": "FALSE",
        "path": ".github/gates.toml",
        "needle": "135 passed",
        "why": "a mutation count that is 137 on the tree that shipped; outside the old file set",
    },
    {
        "round": "six",
        "verdict": "MISLEADING",
        "path": "docs/ARCHITECTURE.md",
        "needle": "4,215",
        "why": "a right digit inside a clause naming the wrong two corpora",
    },
    {
        "round": "this one",
        "verdict": "FALSE",
        "path": "docs/CLAIMS-LEDGER.md",
        "needle": "D-068, D-082",
        "why": "the five-round transcription cites D-100 for round three; round three is D-088",
    },
)


class SamplerError(Exception):
    """The frame could not be built."""


# ---------------------------------------------------------------------------
# Reading files into claim-bearing units
# ---------------------------------------------------------------------------

#: A sentence boundary: terminal punctuation, whitespace, then something that
#: can begin a sentence. Deliberately conservative -- it will not split
#: ``1.02`` or ``D-088.`` mid-token, and it would rather return one long unit
#: than two wrong ones, because a grader can read a long sentence and cannot
#: recover a claim that was cut in half.
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z*`\[(#-])")

#: An opening or closing Markdown fence.
_FENCE = re.compile(r"^\s*(?:`{3,}|~{3,})")


def _sentences(text: str) -> Iterator[str]:
    """Split prose into sentences, whitespace-normalised, empties dropped."""
    for chunk in _SENTENCE.split(text):
        collapsed = " ".join(chunk.split())
        if collapsed:
            yield collapsed


def _markdown_units(text: str) -> Iterator[Tuple[int, str, str]]:
    """Yield ``(line_number, region, sentence)`` for one Markdown file.

    Fenced blocks are yielded **line by line** and prose is yielded sentence by
    sentence, because the two carry claims in different shapes: a fence here is
    almost always transcribed command output, where the unit is a row, and
    prose is where a clause wraps a figure.

    Nothing is masked. That is the entire point of the rewrite.
    """
    prose: List[Tuple[int, str]] = []
    inside = False
    for number, line in enumerate(text.split("\n"), start=1):
        if _FENCE.match(line):
            inside = not inside
            continue
        if inside:
            if line.strip():
                yield (number, "fenced", " ".join(line.split()))
        else:
            prose.append((number, line))

    buffer: List[str] = []
    start: Optional[int] = None
    for number, line in [*prose, (0, "")]:
        if line.strip():
            if start is None:
                start = number
            buffer.append(line)
            continue
        if buffer and start is not None:
            for sentence in _sentences(" ".join(buffer)):
                yield (start, "prose", sentence)
        buffer = []
        start = None


def _line_units(text: str) -> Iterator[Tuple[int, str, str]]:
    """Yield one unit per non-blank line, for TOML and YAML register files."""
    for number, line in enumerate(text.split("\n"), start=1):
        stripped = " ".join(line.split())
        if stripped:
            yield (number, "line", stripped)


def _json_units(text: str) -> Iterator[Tuple[int, str, str]]:
    """Yield one unit per sentence of every string in a run summary.

    The line number is ``0``: a JSON string's sentence has no line of its own,
    and inventing one would put a number in an identifier that no reader could
    check. The dotted key path is carried in the region instead, which is what
    a grader actually needs to find it again.
    """
    try:
        document = json.loads(text)
    except (ValueError, UnicodeDecodeError):
        return

    def walk(value: Any, path: str) -> Iterator[Tuple[int, str, str]]:
        if isinstance(value, str):
            for sentence in _sentences(value):
                yield (0, f"json:{path or '.'}", sentence)
        elif isinstance(value, list):
            for item in value:
                yield from walk(item, path)
        elif isinstance(value, dict):
            for key, item in value.items():
                yield from walk(item, f"{path}.{key}" if path else str(key))

    yield from walk(document, "")


def _units_for(path: Path, text: str) -> Iterator[Tuple[int, str, str]]:
    """Dispatch on suffix: ``.md`` prose, ``.json`` strings, everything else lines."""
    if path.suffix == ".md":
        yield from _markdown_units(text)
    elif path.suffix == ".json":
        yield from _json_units(text)
    else:
        yield from _line_units(text)


# ---------------------------------------------------------------------------
# The frame
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrameItem:
    """One claim-bearing sentence: where it is, what it says, which channel."""

    identifier: str
    relative_path: str
    line_number: int
    channel: str
    region: str
    text: str

    @property
    def sentence(self) -> str:
        """The text, trimmed to something a grader can read in a table."""
        return self.text if len(self.text) <= 200 else self.text[:197] + "..."


@dataclass(frozen=True)
class Frame:
    """The whole population, partitioned by channel."""

    items: Tuple[FrameItem, ...]
    missing_channels: Tuple[str, ...]

    def sizes(self) -> Dict[str, int]:
        """``N_h`` for every channel, zeroes included."""
        tally = dict.fromkeys(CHANNELS, 0)
        for item in self.items:
            tally[item.channel] = tally.get(item.channel, 0) + 1
        return tally

    @property
    def total(self) -> int:
        """``N``."""
        return len(self.items)

    def files(self) -> Tuple[str, ...]:
        """Every distinct path the frame reaches, sorted."""
        return tuple(sorted({item.relative_path for item in self.items}))


def _channel_files(root: Path) -> Dict[str, List[Path]]:
    """Resolve every channel's globs against the checkout, first match winning.

    Precedence is :data:`CHANNEL_PRECEDENCE` and not :data:`CHANNELS`, because
    ``docs/*.md`` and ``docs/DECISIONS.md`` both match the record file and the
    display order is not the tie-break order. Getting this wrong would put
    ``3,302`` append-only sentences into the editable channel and quietly triple
    the ``document`` stratum.
    """
    seen: Dict[str, str] = {}
    resolved: Dict[str, List[Path]] = {name: [] for name in CHANNELS}
    for channel in CHANNEL_PRECEDENCE:
        for pattern in CHANNEL_GLOBS[channel]:
            for path in sorted(root.glob(pattern)):
                if not path.is_file():
                    continue
                relative = path.relative_to(root).as_posix()
                if relative in seen or relative.startswith(EXCLUDED):
                    continue
                seen[relative] = channel
                resolved[channel].append(path)
    return resolved


def build_frame(root: Path = REPO_ROOT) -> Frame:
    """Every claim-bearing sentence in the four channels.

    Args:
        root: The checkout.

    Returns:
        The :class:`Frame`. ``missing_channels`` names any channel that resolved
        to no file at all -- an sdist, a shallow checkout or a tree with no
        committed run summaries -- because a channel silently at ``N = 0`` would
        hand its draws to another channel and print a header claiming coverage
        it does not have.
    """
    resolved = _channel_files(root)
    items: List[FrameItem] = []
    for channel in CHANNELS:
        for path in resolved[channel]:
            relative = path.relative_to(root).as_posix()
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:  # pragma: no cover - unreadable file
                continue
            for line_number, region, sentence in _units_for(path, text):
                if not CLAIM_BEARING.search(sentence):
                    continue
                if len(sentence.split()) < MIN_UNIT_TOKENS:
                    continue
                digest = hashlib.sha1(sentence.encode("utf-8")).hexdigest()[:8]
                items.append(
                    FrameItem(
                        identifier=f"{relative}:{line_number}:{digest}",
                        relative_path=relative,
                        line_number=line_number,
                        channel=channel,
                        region=region,
                        text=sentence,
                    )
                )
    missing = tuple(name for name in CHANNELS if not resolved[name])
    items.sort(key=lambda item: item.identifier)
    return Frame(items=tuple(items), missing_channels=missing)


def allocate(frame: Frame, size: int, allocation: Dict[str, int]) -> Dict[str, int]:
    """How many to draw from each channel, given how many are there.

    A channel smaller than its allocation gives what it has and the remainder
    goes to the others in :data:`CHANNELS` order. The reallocation is visible in
    the printed table, and :func:`_render_frame` warns about it in words --
    which the retired frame did not, and which is how its ``round`` stratum
    could fall to zero on a committed tree without anybody noticing.
    """
    planned = dict.fromkeys(CHANNELS, 0)
    sizes = frame.sizes()
    remaining = size
    for name in CHANNELS:
        want = min(allocation.get(name, 0), sizes[name], remaining)
        planned[name] = want
        remaining -= want
    for name in CHANNELS:
        if remaining <= 0:
            break
        extra = min(sizes[name] - planned[name], remaining)
        planned[name] += extra
        remaining -= extra
    return planned


def draw(
    frame: Frame,
    seed: int,
    size: int = DEFAULT_SIZE,
    allocation: Optional[Dict[str, int]] = None,
) -> List[FrameItem]:
    """The sample, reproducible from ``seed`` alone.

    ``random.Random(seed)`` over a sorted frame: the same tree and the same seed
    give the same twenty-four rows on any machine, which is what makes **a
    second grader on the same sample** possible. That is the condition
    ``docs/CLAIMS-LEDGER.md`` has listed as unmet for six rounds, and it is
    unmeetable without exactly this property.
    """
    planned = allocate(frame, size, allocation or DEFAULT_ALLOCATION)
    rng = random.Random(seed)
    chosen: List[FrameItem] = []
    for name in CHANNELS:
        pool = [item for item in frame.items if item.channel == name]
        if planned[name]:
            chosen.extend(rng.sample(pool, planned[name]))
    return chosen


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> Tuple[float, float]:
    """The Wilson score interval, as percentages.

    Wilson rather than the normal approximation, for the reason every
    small-sample rate on this project uses it: at ``2 of 24`` the normal
    interval includes negative rates, and a lower bound below zero is a sentence
    that cannot be published.
    """
    if trials <= 0:
        return (0.0, 100.0)
    proportion = successes / trials
    denominator = 1 + z * z / trials
    centre = (proportion + z * z / (2 * trials)) / denominator
    half = (z / denominator) * math.sqrt(
        proportion * (1 - proportion) / trials + z * z / (4 * trials * trials)
    )
    return (100 * max(0.0, centre - half), 100 * min(1.0, centre + half))


def design_effect(frame: Frame, allocation: Dict[str, int], size: int = DEFAULT_SIZE) -> float:
    """How much precision the unequal allocation costs, at equal rates.

    ``Deff = n * sum_h (W_h^2 / n_h)`` with ``W_h = N_h / N``, computed under
    the null that every channel carries the same rate -- which is what makes the
    number a property of the DESIGN rather than of any measurement.

    Above ``1`` this draw is *less* precise about the repository as a whole than
    a uniform draw of the same size. **It is above 1 here and it is meant to
    be**: ``submitted`` is under two per cent of the population and gets a third
    of the sample, because that is the channel where errors are made. The price
    is printed on every draw rather than argued about.
    """
    planned = allocate(frame, size, allocation)
    total = frame.total
    drawn = sum(planned.values())
    if total <= 0 or drawn <= 0:
        return float("nan")
    sizes = frame.sizes()
    accumulated = 0.0
    for name in CHANNELS:
        if planned[name] <= 0:
            continue
        weight = sizes[name] / total
        accumulated += weight * weight / planned[name]
    return drawn * accumulated


def stratified_estimate(
    frame: Frame,
    graded: Dict[str, str],
    sample: Sequence[FrameItem],
) -> Dict[str, Any]:
    """Per-channel rates and the design-weighted repository-wide rate.

    The pooled figure is ``sum_h W_h p_h``, **not** the raw count over the
    sample. Reporting the raw count would be this frame's central trap: with a
    third of the draw taken from a channel holding under two per cent of the
    population, the unweighted rate is an estimate of the self-report channel's
    rate wearing the whole repository's name.
    """
    sizes = frame.sizes()
    total = frame.total
    per_channel: Dict[str, Dict[str, Any]] = {}
    weighted = 0.0
    variance = 0.0
    for name in CHANNELS:
        drawn = [item for item in sample if item.channel == name]
        verdicts = [graded[item.identifier] for item in drawn if item.identifier in graded]
        if not verdicts:
            continue
        bad = sum(1 for verdict in verdicts if verdict in NOT_TRUE)
        proportion = bad / len(verdicts)
        weight = sizes[name] / total if total else 0.0
        weighted += weight * proportion
        variance += weight * weight * proportion * (1 - proportion) / len(verdicts)
        per_channel[name] = {
            "N": sizes[name],
            "n": len(verdicts),
            "not_true": bad,
            "rate_pct": 100 * proportion,
            "wilson_pct": wilson(bad, len(verdicts)),
        }
    half = 1.959963984540054 * math.sqrt(variance) if variance > 0 else 0.0
    return {
        "per_channel": per_channel,
        "repository_rate_pct": 100 * weighted,
        "repository_half_width_pct": 100 * half,
        "graded": sum(int(row["n"]) for row in per_channel.values()),
    }


def containment(frame: Frame) -> List[Dict[str, Any]]:
    """Can this frame reach each site a previous round graded not true?

    Returns one row per entry of :data:`KNOWN_ERROR_SITES`, each carrying
    whether the live frame holds an item in that file whose text contains the
    needle. **A floor, not evidence of generality**: these are the observations
    the design was fitted to, so containing them is the least it can do.
    """
    rows: List[Dict[str, Any]] = []
    for site in KNOWN_ERROR_SITES:
        hits = [
            item
            for item in frame.items
            if item.relative_path == site["path"] and site["needle"] in item.text
        ]
        rows.append(
            {
                "round": site["round"],
                "verdict": site["verdict"],
                "path": site["path"],
                "needle": site["needle"],
                "why": site["why"],
                "contained": bool(hits),
                "hits": len(hits),
                "channel": hits[0].channel if hits else None,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# The audit of the frame this one replaces
# ---------------------------------------------------------------------------


def audit_old_frame(root: Path = REPO_ROOT) -> Dict[str, Any]:
    """Re-derive the measurement that retired the churn-weighted number frame.

    Imports ``tools/check_claims.py`` by path -- the mechanism
    ``tests/test_gate_manifest.py`` uses, because ``tools/`` is a directory of
    scripts and must not become a package -- and reports, for the scanned
    Markdown, how many backticked figures exist and how many of them survive the
    masking that the retired frame's population was built on top of.

    The answer to the second is structurally ``0``. This function exists so that
    the docstring's proof is a command rather than a paragraph.
    """
    import importlib.util

    path = root / "tools" / "check_claims.py"
    if not path.is_file():  # pragma: no cover - source checkouts only
        raise SamplerError(f"{path} is not here; this tool belongs to a checkout")
    spec = importlib.util.spec_from_file_location("_check_claims_for_audit", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise SamplerError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    project = module.Project.at(root)
    claims = module.collect_claims(
        project,
        module.build_index(module.load_results(project)),
        module.load_allowlist(project),
    )
    raw = [claim for claim in claims if claim.backing in ("deferred", "unexamined")]
    # The retired frame dropped a bare four-digit integer in 1900-2199 from the
    # UNARMED residue only, as a date. Reproduced here rather than approximated,
    # so that this audit reports the population that actually shipped (2,095)
    # and not the population before that filter (2,226).
    year_like = re.compile(r"^(?:19|20|21)\d{2}$")
    residue = [
        claim
        for claim in raw
        if not (claim.backing == "unexamined" and year_like.match(claim.text))
    ]

    ticked = re.compile(r"`([0-9][0-9,.]*\s*%?)`")
    backticked = 0
    masked_chars = 0
    total_chars = 0
    for source in sorted({claim.path for claim in claims}):
        if source.suffix != ".md":
            continue
        text = source.read_text(encoding="utf-8", errors="replace")
        unfenced = module._mask_fenced_blocks(text)
        backticked += len(ticked.findall(unfenced))
        total_chars += len(text)
        masked_chars += sum(1 for a, b in zip(text, unfenced) if b == " " and a != " ")

    # THE SURVIVOR CHECK RE-READS FILES `collect_claims` HAS ALREADY READ, AND
    # ON A SHARED WORKING TREE THAT IS A RACE. It was written as a flat equality
    # and went red the first time a sibling agent rewrote
    # `src/acronymkit/nlp/propagation.py` between the two reads: ten residue
    # items recorded against line numbers that, seconds later, held different
    # text. That is not a masking result and must not be reported as one.
    #
    # So each file is read once here, and a claim whose recorded line no longer
    # matches the file is counted as MOVED rather than as masked. The masking
    # claim is then made only over the claims that could actually be checked.
    cache: Dict[Path, List[str]] = {}
    survivors = 0
    moved = 0
    for claim in residue:
        if claim.path not in cache:
            body = claim.path.read_text(encoding="utf-8", errors="replace")
            cache[claim.path] = module.prose_of(body, claim.path.suffix).split("\n")
        lines = cache[claim.path]
        index = claim.line_number - 1
        if index < 0 or index >= len(lines):
            moved += 1
        elif claim.text in lines[index]:
            survivors += 1
        else:
            moved += 1

    small = sum(1 for claim in residue if re.fullmatch(r"\d{1,2}", claim.text))
    return {
        "residue": len(residue),
        "residue_before_year_filter": len(raw),
        "residue_files": len({claim.path for claim in residue}),
        "small_integers": small,
        "small_integer_pct": 100.0 * small / len(residue) if residue else 0.0,
        "backticked_figures_in_unfenced_markdown": backticked,
        "backticked_figures_reachable_by_old_frame": 0,
        "residue_items_from_unmasked_prose": survivors,
        "residue_items_whose_file_moved_under_the_read": moved,
        "markdown_chars": total_chars,
        "markdown_chars_hidden_by_fences": masked_chars,
        "fenced_pct": 100.0 * masked_chars / total_chars if total_chars else 0.0,
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_frame(frame: Frame, allocation: Dict[str, int], size: int) -> str:
    lines: List[str] = []
    sizes = frame.sizes()
    planned = allocate(frame, size, allocation)
    lines.append(
        f"frame: {frame.total} claim-bearing sentence(s) across {len(frame.files())} file(s)"
    )
    if frame.missing_channels:
        lines.append(
            "  CHANNEL(S) WITH NO FILES: "
            + ", ".join(frame.missing_channels)
            + " -- their draws went elsewhere. Do not report this as a four-channel sample."
        )
    for name in CHANNELS:
        share = 100 * sizes[name] / frame.total if frame.total else 0.0
        want = allocation.get(name, 0)
        note = "" if planned[name] == want else f"  (WANTED {want}, REALLOCATED)"
        lines.append(
            f"  {name:<10} N {sizes[name]:>5}  ({share:5.1f} % of the frame)  "
            f"draw {planned[name]}{note}"
        )
    lines.append(f"  design effect at equal rates: {design_effect(frame, allocation, size):.2f}")
    lines.append(
        "    above 1.00 means this allocation is LESS precise about the repository than a "
        "uniform draw of the same size. It buys the per-channel question instead, and the "
        "per-channel question is the one a round needs."
    )
    lines.append(
        f"  the predecessor series: {CLOSED_SERIES['not_true']} of {CLOSED_SERIES['draws']} = "
        f"{CLOSED_SERIES['rate_pct']:.2f} % over {CLOSED_SERIES['rounds']} rounds, Wilson "
        f"{CLOSED_SERIES['wilson_pct'][0]:.2f}-{CLOSED_SERIES['wilson_pct'][1]:.2f}. "
        "IT DOES NOT CARRY ACROSS. This frame starts at n = 0, for the second time in two "
        "rounds, and that is recorded as a bad sign rather than as a fresh start."
    )
    return "\n".join(lines)


def _render_containment(rows: Sequence[Dict[str, Any]]) -> str:
    lines = [
        "containment: can this frame REACH the sentences previous rounds graded not true?",
        "  A FLOOR, not evidence of generality -- the design was fitted to these.",
    ]
    for row in rows:
        mark = "yes" if row["contained"] else "NO "
        where = f"{row['channel']}, {row['hits']} item(s)" if row["contained"] else "unreachable"
        lines.append(f"  [{mark}] round {row['round']:<9} {row['path']}  ({where})")
        lines.append(f"        needle {row['needle']!r} -- {row['why']}")
    reached = sum(1 for row in rows if row["contained"])
    lines.append(f"  {reached} of {len(rows)} reachable")
    return "\n".join(lines)


def _render_audit(result: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "the retired frame, re-derived. Command output, not a benchmark measurement.",
            f"  population as it shipped                   {result['residue']:>6}"
            f"  across {result['residue_files']} file(s)",
            f"  the same residue before its year filter    "
            f"{result['residue_before_year_filter']:>6}",
            f"  of it, one- and two-digit integers         {result['small_integers']:>6}"
            f"  ({result['small_integer_pct']:.1f} %)",
            f"  backticked figures in unfenced Markdown    "
            f"{result['backticked_figures_in_unfenced_markdown']:>6}",
            f"  of those, reachable by the retired frame   "
            f"{result['backticked_figures_reachable_by_old_frame']:>6}"
            "   <- zero by construction, not by chance",
            f"  residue items that came from unmasked prose {result['residue_items_from_unmasked_prose']:>5}"
            f" of {result['residue']}",
            f"  ... and {result['residue_items_whose_file_moved_under_the_read']} whose file moved"
            " under the read, which is a shared-checkout race and not a masking result",
            f"  Markdown hidden inside fences             {result['fenced_pct']:>6.1f} %"
            f"  ({result['markdown_chars_hidden_by_fences']} of {result['markdown_chars']} chars)",
            "  prose_of() masks fenced blocks AND inline code spans before claims are",
            "  collected, so a figure in this project's house style cannot be in that",
            "  population. That is why the frame was retired rather than widened.",
        ]
    )


def _render_estimate(result: Dict[str, Any]) -> str:
    lines = ["stratified estimate. A grading pass, not a benchmark measurement."]
    per_channel = result["per_channel"]
    assert isinstance(per_channel, dict)
    for name in CHANNELS:
        row = per_channel.get(name)
        if row is None:
            continue
        low, high = row["wilson_pct"]
        lines.append(
            f"  {name:<10} {row['not_true']:>2} of {row['n']:>2} not true = "
            f"{float(row['rate_pct']):6.2f} %  Wilson [{low:5.2f}, {high:5.2f}]  N {row['N']}"
        )
    lines.append(
        f"  repository-wide, DESIGN-WEIGHTED: {float(result['repository_rate_pct']):.2f} % "
        f"+/- {float(result['repository_half_width_pct']):.2f} (normal approximation to a "
        "stratified estimator; Wilson has no closed form here)"
    )
    lines.append(
        f"  NOT comparable with the predecessor's {CLOSED_SERIES['rate_pct']:.2f} % over "
        f"{CLOSED_SERIES['draws']} draws: different population, different unit, different "
        "inclusion probabilities."
    )
    return "\n".join(lines)


def _sample_rows(sample: Iterable[FrameItem]) -> List[Dict[str, Any]]:
    return [
        {
            "id": item.identifier,
            "channel": item.channel,
            "region": item.region,
            "path": item.relative_path,
            "line": item.line_number,
            "sentence": item.sentence,
        }
        for item in sample
    ]


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command line entry point."""
    parser = argparse.ArgumentParser(
        prog="sample_claims.py",
        description=(
            "Draw a channel-stratified sample of this project's claim-bearing sentences. "
            "Successor to the churn-weighted number frame, which is retired ungraded."
        ),
    )
    parser.add_argument("--frame", action="store_true", help="print the channels and their sizes")
    parser.add_argument("--draw", action="store_true", help="draw a sample")
    parser.add_argument("--estimate", metavar="FILE", help="a JSON map of identifier -> verdict")
    parser.add_argument(
        "--containment",
        action="store_true",
        help="can the frame reach the sentences previous rounds graded not true?",
    )
    parser.add_argument(
        "--audit-old-frame",
        action="store_true",
        help="re-derive the measurement that retired the previous frame",
    )
    parser.add_argument("--seed", type=int, default=None, help="the published seed")
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--root", default=str(REPO_ROOT), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    root = Path(args.root)

    if args.audit_old_frame:
        result = audit_old_frame(root)
        print(json.dumps(result, indent=2) if args.json else _render_audit(result))
        return 0

    frame = build_frame(root)

    if args.containment:
        rows = containment(frame)
        print(json.dumps(rows, indent=2) if args.json else _render_containment(rows))
        return 0

    if args.estimate:
        graded = json.loads(Path(args.estimate).read_text(encoding="utf-8"))
        unknown = sorted({str(v) for v in graded.values() if v not in VERDICTS})
        if unknown:
            print(f"verdict(s) {unknown} are not in {list(VERDICTS)}")
            return 1
        if args.seed is None:
            print("--estimate needs the --seed the sample was drawn under")
            return 1
        result = stratified_estimate(frame, graded, draw(frame, args.seed, args.size))
        print(json.dumps(result, indent=2, default=list) if args.json else _render_estimate(result))
        return 0

    if args.draw:
        if args.seed is None:
            print("--draw needs a --seed, and the seed is published with the sample")
            return 1
        sample = draw(frame, args.seed, args.size)
        if args.json:
            print(json.dumps(_sample_rows(sample), indent=2))
        else:
            print(_render_frame(frame, DEFAULT_ALLOCATION, args.size))
            print(f"\nsample of {len(sample)} under seed {args.seed}:")
            for item in sample:
                print(f"  [{item.channel:<9} {item.region:<24}] {item.identifier}")
                print(f"           {item.sentence}")
        return 0

    print(_render_frame(frame, DEFAULT_ALLOCATION, args.size))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
