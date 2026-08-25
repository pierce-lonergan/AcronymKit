#!/usr/bin/env python3
"""Load and validate ``bench/splits.toml``, the file the train/test rule rests on.

Why this exists
---------------
``bench/splits.toml`` declares, per corpus, what it may be used for: its
``role`` (tuning or held out), its ``task``, its ``licence``, and whether it is
contaminated. Operating rule 2 -- every MED1250 figure is a tuning figure -- is
that file. So is the licence discipline that decides what may be shipped.

For months nothing loaded it. Eleven places cited it in prose; zero parsed it.
It was not even valid TOML: a ``status`` key was written twice inside
``[corpora.plod]`` while adding a correction block, and nothing noticed, because
noticing would have required a reader. **A governance artifact no tool reads is
a habit, not a rule**, and the habit had already decayed into an invalid file.

This module is the reader. It is deliberately three things at once:

* a **typed accessor** (:class:`Manifest`, :class:`Corpus`) so a bench runner
  asks the manifest what a corpus is for instead of hard-coding the answer in a
  docstring, which is how ``[corpora.plod]`` came to call PLOS journal text a
  "non-biomedical counterweight" in one file and be corrected in another;
* a **validator** (:func:`validate`) with one implementation, driven by the CI
  step, by ``tests/test_splits_manifest.py`` and by ``bench/corpora.py``, so the
  three cannot drift apart; and
* a **script** (``--check``) that CI runs.

What the validator enforces, and why each rule is here
------------------------------------------------------
``role``/``task``/``licence``
    A corpus with no declared role is exempt from the headline rule by
    accident. A corpus with no declared licence is one nobody read the terms
    for -- which has now happened three times in this repository (SDU-21 AD,
    SDU-21 AI, and GLADIS in the August 2026 audit).

``task``, and why widening :data:`TASKS` is a decision
    ``task`` is a closed vocabulary because ``bench/corpora.py`` returns a
    **different type per task**, and a corpus filed under the wrong one is how a
    pair scorer comes to be pointed at a span corpus. :data:`TASK_GOLD_UNIT`
    records what one gold record *is* for each, so the contract is written down
    where the vocabulary is, rather than inferred from whichever reader happened
    to be registered.

    ``identifier_segmentation`` was added for the SEC XBRL and Socrata
    identifier/caption corpora. It is the first task in this file whose gold is
    **not an annotation inside a passage**: there is no text, no span and no
    annotator, only two surface strings made of the same characters and the set
    of positions where one of them is cut.

``headline_capable`` is asked per task, never in general
    :meth:`Manifest.headline_capable` requires the task the headline is a claim
    about. Task-blindness was harmless while every declared corpus was a pair or
    a span corpus and stopped being harmless the moment a segmentation corpus
    entered the ``held_out`` role: a corpus that scores where an identifier is
    cut would have satisfied a headline requirement for extracting definitions
    from prose. That failure is quieter than an undeclared corpus, because
    nothing about it looks wrong.

``licence_url`` and ``licence_read_on``
    Operating rule 4: **licences come from terms, never from a badge.** A
    licence string on its own records a conclusion and destroys the evidence.
    These two fields record *where the text was read* and *when*, so the
    finding is reproducible by someone who does not trust it.

    The URL is checked against :data:`BADGE_HOSTS`. GLADIS is the cautionary
    tale: its GitHub badge says CC0, Zenodo says CC BY 4.0, and the repository's
    own source table lists UMLS, which is not redistributable. Three sources,
    three answers. A badge URL is therefore not an acceptable citation, and this
    validator refuses one rather than trusting the author to remember.

``reservations``, and why a reservation in prose is not a reservation
    Two arms of two corpora are spoken for: SDU-21 AD ``test.json`` (D-043) and
    SDU-22 legal ``train.json`` (D-047). Both allocations were written as prose
    -- in a decision record and, for the second, in a manifest note -- and both
    records say the same thing about themselves in their *How it fails*
    sections: **nothing refuses a run against a reserved split; the guard is
    that somebody reads a note.** That is the shape this repository has already
    paid for: eleven places cited ``bench/splits.toml`` in prose and none of
    them parsed it, and the file had been invalid TOML for months.

    A reservation is therefore a validated table, not a paragraph. Each one
    names the ``arm``, its ``state``, the record that decided it, what it is
    ``allocated_to``, the ``spend_trigger`` that would fire it and the
    ``lapse_trigger`` that would reverse it. :func:`validate` refuses a
    reservation with no trigger, a state that contradicts its own fields, two
    reservations claiming one arm, and an unrecognised key -- the last because
    a misspelt ``laps_trigger`` would drop the trigger silently, which is the
    prose reservation again wearing a schema.

    The second half is the accessor. :meth:`Corpus.require_unreserved` refuses
    by default and :meth:`Corpus.declare_spend` is the only way past it, so a
    runner that opens a reserved arm has to say so, in the record's own name,
    with a purpose that lands in the run log. See :meth:`Corpus.declare_spend`
    for the ergonomics argument, which is the part that decides whether the
    guard is used or routed around.

``shortform_recall_ceiling_pct``
    Optional, and **required to travel with its basis** -- which is the whole
    point of the pair. Where a corpus annotates every acronym *occurrence* while
    this library reports only *defined pairs*, raw recall against it understates
    the extractor by a structural margin, and publishing the recall without the
    margin misleads.

    The basis is mandatory because the word "ceiling" is dangerous in this
    repository specifically. ``41.53`` was published as "the ceiling of the
    feature set" and the run that published it exceeded the figure four times;
    the August 2026 audit kept the finding and killed the word. So a number in
    this field is never self-explanatory: the basis must say what it is, and in
    particular whether it is a hard bound or -- as with SDU-22 AE -- the point
    past which recall is bought against the corpus's own annotation. The
    validator enforces the pairing; only a reader can enforce the honesty, and
    an empty basis denies them the chance.

    The field is refused outright on a task whose gold holds no short forms
    (:data:`SHORT_FORM_TASKS`). An identifier-segmentation corpus annotates no
    abbreviation anywhere, so a "short-form recall ceiling" on one is not a
    cautious extra: it is a number that would be printed beside a recall figure
    measuring a different quantity.

Usage::

    python tools/splits.py --check      # the CI gate
    python tools/splits.py --list       # the manifest as a table
    python tools/splits.py --json       # the manifest as JSON

Nothing here is imported by the library, and nothing here touches the network.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
SPLITS_PATH = REPO_ROOT / "bench" / "splits.toml"

#: Roles the policy recognises. A typo silently exempts a corpus from the
#: headline rule, so the vocabulary is closed rather than free text.
ROLES = ("tuning", "held_out")

#: Tasks a corpus can be scored on. Also closed, for the same reason and one
#: more: ``bench/corpora.py`` returns a *different type* per task, and a corpus
#: filed under the wrong one is how a pair scorer comes to be pointed at a span
#: corpus and report a meaningless zero.
#:
#: Widening this tuple is a decision about that type contract and never a
#: one-word edit. :data:`TASK_GOLD_UNIT` states, per task, what one gold record
#: *is*; ``bench/corpora.py`` states which registry returns it. Adding a task
#: without both is how the vocabulary stops protecting anything.
TASKS = ("extraction", "span_detection", "disambiguation", "identifier_segmentation")

#: What one gold record **is**, per task. This is the property the closed
#: vocabulary exists to protect, written down rather than implied.
#:
#: The first three tasks all annotate *inside a passage*: each gold record
#: carries text (or tokens) and points into it. ``identifier_segmentation`` does
#: not. Its record is a pair of surface strings that are the *same characters* --
#: a machine identifier and a human caption of it -- and its gold is a set of
#: integer cut positions in the character stream they share. There is no
#: passage, no offsets into prose, no annotator and no candidate set, which is
#: why it cannot be read by a pair reader or a span reader even by accident.
#:
#: **The shape of a record is not the whole contract, and the half that was
#: implicit here is the load-bearing one.** ``extraction`` and
#: ``span_detection`` both hold short forms and long forms inside a passage, so
#: on shape alone they read as the same task under two names. They are not:
#: extraction gold asserts an *edge* between the two, span gold asserts none
#: (D-048). Each entry below now says so, because the difference is what decides
#: whether a held-out span corpus can back the claim this project leads with,
#: and the answer is no.
TASK_GOLD_UNIT = {
    "extraction": (
        "a passage, plus the short-form/long-form pairs a human annotated in it; "
        "each record asserts an EDGE -- that this short form and this long form "
        "stand in a definition relation -- and the edge is the whole of the gold, "
        "so a system emitting both surfaces and pairing them wrongly is wrong "
        "(bench.corpora.GoldDocument)"
    ),
    "span_detection": (
        "a passage, plus the index ranges tagged short form or long form; the "
        "annotation never says which belongs to which, so the gold is two UNLINKED "
        "vertex sets carrying no edge at all, over a wider extension -- every "
        "occurrence is tagged, defined or not "
        "(bench.corpora.SpanDocument, bench.corpora.CharSpanDocument)"
    ),
    "disambiguation": (
        "one acronym occurrence in a sentence, plus the fixed candidate set it "
        "must resolve against (bench.corpora.DisambiguationInstance)"
    ),
    "identifier_segmentation": (
        "a machine identifier and a human caption whose alphanumerics are the "
        "same characters, so only cut placement can differ; the gold is the set "
        "of cut positions and nothing else (bench.corpora.IdentifierCaptionPair)"
    ),
}

#: Tasks whose gold contains short forms at all, and therefore the only tasks
#: for which ``shortform_recall_ceiling_pct`` is a meaningful field. An
#: identifier-segmentation corpus has no short forms in it -- no abbreviation is
#: annotated anywhere -- so a recall ceiling declared on one is a category
#: error, not a conservative extra.
SHORT_FORM_TASKS = ("extraction", "span_detection")

#: Every corpus must declare these.
REQUIRED_FIELDS = ("role", "task", "licence", "licence_url", "licence_read_on")

#: Hosts and path fragments that serve a licence *badge* or a licence *label*
#: rather than licence *text*. Operating rule 4 exists because a badge was
#: believed three times in this repository's history, and the fix each time came
#: from a person opening the actual terms.
BADGE_HOSTS = ("shields.io", "img.shields.io", "badgen.net", "badge.fury.io")

#: Path fragments that mark a URL as metadata about a licence rather than the
#: licence itself. ``api.github.com/repos/<x>/license`` returns GitHub's
#: *guess*, which is what reported CC0 for a corpus assembled partly from UMLS.
BADGE_PATH_FRAGMENTS = ("/badge", "/license.svg", "/licence.svg")

#: A licence read this long ago is reported as worth re-reading. It is a NOTE
#: and never a failure: a gate that turns red with the passage of time fires on
#: an unrelated commit, which is the failure mode this repository already
#: refused for the entry-point purity gate.
STALE_AFTER_DAYS = 730

#: States a reservation can be in. Closed for the same reason :data:`ROLES` is:
#: a typo would make a reserved arm look like an unreserved one, which is the
#: precise failure the structure exists to end.
#:
#: ``allocated``    spoken for, by a named question, with both triggers written.
#: ``unallocated``  deliberately reserved *for nothing yet*. D-047 keeps SDU-22
#:                  scientific ``train.json`` in this state on purpose: assigning
#:                  it a use today would mean inventing one, which is the failure
#:                  D-043 corrected. It is a state, not a drift, and it still
#:                  refuses a spend.
#: ``spent``        the arm has been read. It no longer refuses anything -- the
#:                  cost has been paid and the corpus entry above is where the
#:                  contamination is recorded.
RESERVATION_STATES = ("allocated", "unallocated", "spent")

#: Every key a ``[[corpora.<name>.reservations]]`` table may carry. Unknown keys
#: are **refused**, unlike on a corpus table where they are preserved in
#: :attr:`Corpus.extra`, and the asymmetry is the point: an unrecognised corpus
#: key costs nothing, while a misspelt ``laps_trigger`` would silently drop the
#: one field this whole structure exists to require. A reservation with a
#: quietly missing trigger is the prose reservation again, wearing a schema.
RESERVATION_FIELDS = (
    "arm",
    "state",
    "decided_in",
    "allocated_to",
    "spend_trigger",
    "lapse_trigger",
    "not_a_trigger",
    "spent_in",
    "file",
    "note",
)

#: A decision-record id. ``decided_in`` is required on every reservation
#: because "reserved" with no record behind it is exactly how AD ``test.json``
#: spent six rounds reserved *for* nothing in particular: each round it survived
#: because nobody happened to want it, which is not the same as being reserved
#: for something (D-043).
_DECISION_RE = re.compile(r"^D-\d{3}$")

#: An arm name is the split token a **runner already holds** -- ``"train"``,
#: ``"test"`` -- and never the upstream filename. A guard is only reachable if
#: the string the manifest reserves is the string the caller has in a variable;
#: reserving ``"train.json"`` while every reader passes ``split="train"`` is a
#: guard that can never fire. The upstream path goes in ``file``, for the human.
_ARM_RE = re.compile(r"^[a-z][a-z0-9_]*$")

#: Spends declared in **this process**, ``(corpus, arm) -> purpose``. Written
#: only by :meth:`Corpus.declare_spend`, read only by
#: :meth:`Corpus.require_unreserved`.
#:
#: Process-local and in-memory on purpose. The alternative -- having
#: ``declare_spend`` rewrite ``bench/splits.toml`` -- would let a runner mark
#: its own arm spent with no commit, no review and no record, which is a worse
#: hole than the one being closed. Recording the spend stays a manifest edit
#: that a person makes beside the number.
_DECLARED_SPENDS: Dict[Tuple[str, str], str] = {}


def declared_spends() -> Dict[Tuple[str, str], str]:
    """Every spend declared in this process, as ``(corpus, arm) -> purpose``.

    A copy, so a caller cannot grant itself a spend by mutating the ledger --
    :meth:`Corpus.declare_spend` is the only door.
    """
    return dict(_DECLARED_SPENDS)


class SplitsError(Exception):
    """The manifest could not be read, or names something that does not exist."""


def _load_toml(path: Path) -> Dict[str, Any]:
    """Parse ``path`` as TOML on any supported interpreter.

    ``tomllib`` is 3.11+, and ``tomli`` is not a declared dev dependency, so on
    3.9 and 3.10 there may be no parser at all. That is stated as an error
    rather than papered over: a validator that silently passes because it could
    not read the file is worse than one that is absent.
    """
    if sys.version_info >= (3, 11):
        import tomllib as _toml
    else:  # pragma: no cover - 3.9/3.10 path
        try:
            import tomli as _toml  # type: ignore[no-redef]
        except ImportError as error:
            raise SplitsError(
                "no TOML parser available: tomllib is 3.11+ and tomli is not installed. "
                f"Cannot validate {path}."
            ) from error
    try:
        with path.open("rb") as handle:
            return _toml.load(handle)
    except FileNotFoundError as error:
        raise SplitsError(f"{path} does not exist") from error
    except Exception as error:  # tomllib.TOMLDecodeError, and anything it wraps
        raise SplitsError(f"{path} is not valid TOML: {error}") from error


def _first_line(text: str) -> str:
    """The first non-empty line of a block, for a message that must stay short.

    A refusal that reprints three paragraphs of allocation prose is a refusal
    people learn to scroll past. The message carries the first line of each
    field and names the manifest entry and the record for the rest.
    """
    for line in text.strip().splitlines():
        if line.strip():
            stripped = line.strip()
            return stripped if len(stripped) <= 96 else stripped[:93] + "..."
    return ""


@dataclass(frozen=True)
class Reservation:
    """One arm of one corpus, spoken for -- as a structure rather than a note.

    Attributes:
        corpus: The corpus whose arm this is.
        arm: The split token a runner passes, e.g. ``"train"``. Matched
            literally by :meth:`Corpus.require_unreserved`, which is why it must
            be the runner's spelling and not the upstream filename.
        state: One of :data:`RESERVATION_STATES`.
        decided_in: The decision record that put the arm in this state, e.g.
            ``"D-047"``. Required, and checked against a pattern: a reservation
            with no record behind it cannot be argued down, re-designated or
            audited, and is indistinguishable from an arm nobody happened to
            want.
        allocated_to: The question the arm is allocated to answer, and who owns
            the read. Required when ``state`` is ``"allocated"`` and refused
            otherwise.
        spend_trigger: The event that would fire the spend. **This is the field
            the whole structure is for.** A reservation without one is not a
            reservation: it survives each round because nobody had a reason to
            spend it, which is the drift D-043 was written to stop.
        lapse_trigger: The event that reverses the allocation and releases the
            arm. Required on an allocation, refused on anything else -- only an
            allocation can lapse.
        not_a_trigger: Events that look like the trigger and are not. Optional,
            and worth writing: both existing reservations attracted a proposal
            that could not serve them.
        spent_in: What spent it -- a run id, or a record. Required when
            ``state`` is ``"spent"``.
        file: The upstream path, for a human. Never matched against.
        note: The reservation's prose, carried through verbatim.
        unknown_keys: Keys the manifest carried that this reader does not model.
            Reported as a validation failure rather than preserved: see
            :data:`RESERVATION_FIELDS`.
    """

    corpus: str
    arm: str
    state: str
    decided_in: str = ""
    allocated_to: str = ""
    spend_trigger: str = ""
    lapse_trigger: str = ""
    not_a_trigger: str = ""
    spent_in: str = ""
    file: str = ""
    note: str = ""
    unknown_keys: Tuple[str, ...] = ()

    @property
    def is_spent(self) -> bool:
        """Whether the arm has already been read, and so guards nothing further."""
        return self.state == "spent"

    def refusal(self) -> str:
        """Why a run may not open this arm, and the one call that would change that."""
        where = f"[corpora.{self.corpus}] reservations, arm={self.arm!r}"
        lines = [
            f"{self.corpus} arm {self.arm!r} is RESERVED in bench/splits.toml and this run "
            "has not declared a spend.",
            f"  state          {self.state}",
            f"  decided in     {self.decided_in or '(none)'}",
        ]
        if self.allocated_to:
            lines.append(f"  allocated to   {_first_line(self.allocated_to)}")
        if self.spend_trigger:
            lines.append(f"  spends when    {_first_line(self.spend_trigger)}")
        if self.lapse_trigger:
            lines.append(f"  lapses when    {_first_line(self.lapse_trigger)}")
        if self.not_a_trigger:
            lines.append(f"  NOT a trigger  {_first_line(self.not_a_trigger)}")
        lines.extend(
            [
                f"  read in full   {where}, and docs/DECISIONS.md {self.decided_in}",
                "",
                "If this run is the spend that reservation names, say so before opening it:",
                f"    bench.corpora.declare_spend({self.corpus!r}, {self.arm!r},",
                f"        decision={self.decided_in!r},",
                '        purpose="one line, and it lands in the run log")',
                "A sanity check, a second look, or a re-run after a tokenizer change is not "
                "that spend; it is what the reservation refuses.",
            ]
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class Corpus:
    """One corpus declaration, typed.

    Attributes:
        name: The table key, e.g. ``"med1250"``.
        role: One of :data:`ROLES`. ``"tuning"`` means every figure measured on
            this corpus is a tuning figure and must be labelled one.
        task: One of :data:`TASKS`. It decides which *type* of gold record the
            corpus holds -- see :data:`TASK_GOLD_UNIT` -- and therefore which
            runners may read it and which headlines it can back.
        licence: The licence as read from its terms, not as inferred.
        licence_url: Where those terms were read.
        licence_read_on: When they were read.
        status: Free text: how far the corpus has been taken.
        contaminated: Whether the corpus has been looked at closely enough that
            it can no longer adjudicate anything blind.
        contamination_reason: What was looked at. Required when
            ``contaminated`` is true, because "contaminated" with no reason is
            unfalsifiable and cannot be argued down later.
        vendorable: Whether the corpus may ship inside the wheel. ``None`` when
            the entry does not say.
        domain: What the text actually is, which is not always what the corpus
            calls itself -- see ``[corpora.sdu22_ae_legal]``.
        shortform_recall_ceiling_pct: Where short-form recall lands for a
            definition-only extractor on this corpus, or ``None``. Read
            :attr:`shortform_recall_ceiling_basis` before quoting it: whether
            the figure is a hard bound or merely the point past which recall is
            bought against the annotation is a per-corpus fact, and the field
            name is optimistic about it on purpose-built corpora.
        shortform_recall_ceiling_basis: How the figure was derived, and what
            kind of limit it is. Required whenever the figure is present.
        note: The entry's prose, carried through verbatim.
        reservations: Arms of this corpus that are spoken for, typed. See
            :class:`Reservation`, and :meth:`require_unreserved` for what they
            do rather than what they say.
        reservation_defects: Structural problems found while parsing the
            ``reservations`` array -- an entry that is not a table, or an array
            that is not one. Carried rather than raised so :func:`validate`
            reports them beside everything else.
        extra: Any key this reader does not model, so an unrecognised field is
            preserved rather than silently dropped.
    """

    name: str
    role: str
    task: str
    licence: str
    licence_url: str
    licence_read_on: _datetime.date
    status: str = ""
    contaminated: bool = False
    contamination_reason: str = ""
    vendorable: Optional[bool] = None
    domain: str = ""
    shortform_recall_ceiling_pct: Optional[float] = None
    shortform_recall_ceiling_basis: str = ""
    note: str = ""
    reservations: Tuple[Reservation, ...] = ()
    reservation_defects: Tuple[str, ...] = ()
    extra: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_tuning(self) -> bool:
        """Whether every figure from this corpus is a tuning figure."""
        return self.role == "tuning"

    @property
    def is_held_out(self) -> bool:
        """Whether this corpus may back a headline number."""
        return self.role == "held_out"

    def require_role(self, expected: str) -> None:
        """Assert the declared role, so a runner cannot mislabel its own output.

        This is operating rule 2 made mechanical. A runner that prints
        "tuning split" in its header is making a claim about the manifest; this
        turns that claim into a check.

        Raises:
            SplitsError: If the declared role is not ``expected``.
        """
        if self.role != expected:
            raise SplitsError(
                f"{self.name} is declared role={self.role!r} in bench/splits.toml, not {expected!r}"
            )

    def require_task(self, expected: str) -> None:
        """Assert the declared task, so a runner cannot score the wrong shape of gold.

        The exact partner of :meth:`require_role`, and it guards the other half
        of the manifest's contract. A runner that scores cut placement is making
        a claim that its corpus is an ``identifier_segmentation`` corpus; a
        runner that scores pairs is claiming ``extraction``. Both claims are
        currently made in a docstring, where nothing can check them, and the
        cost of getting one wrong is a number rather than an error --
        ``bench/corpora.py``'s ``read_plod_cw_text`` documents that trap in
        prose because there was no mechanism to state it in.

        Raises:
            SplitsError: If the declared task is not ``expected``.
        """
        if self.task != expected:
            raise SplitsError(
                f"{self.name} is declared task={self.task!r} in bench/splits.toml, "
                f"not {expected!r}. A gold record for {expected!r} is "
                f"{TASK_GOLD_UNIT.get(expected, 'a different shape entirely')}."
            )

    def label(self) -> str:
        """The label any figure from this corpus must carry.

        Returns:
            ``"tuning split"`` or ``"held out"``, plus ``", contaminated"`` when
            the entry says so.
        """
        base = "tuning split" if self.is_tuning else "held out"
        return f"{base}, contaminated" if self.contaminated else base

    def reservation(self, arm: str) -> Optional[Reservation]:
        """The reservation on ``arm``, or ``None`` when the arm is free.

        Args:
            arm: The split token, exactly as a runner spells it.
        """
        for entry in self.reservations:
            if entry.arm == arm:
                return entry
        return None

    def require_unreserved(self, arm: str) -> None:
        """Refuse to let this run open ``arm`` unless a spend was declared for it.

        **This is the mechanism D-043 and D-047 both say they lack.** Both
        records allocate an arm in prose and both say the same thing in their
        own *How it fails*: nothing refuses a run against a reserved split, and
        the guard is that somebody reads a note. This is the refusal.

        Call it at the point a reader turns ``(corpus, split)`` into a path --
        one line, unconditional. It is a no-op for every arm that carries no
        reservation, which is all but two arms in this repository, so a reader
        does not have to know which corpora are spoken for.

        Args:
            arm: The split token about to be opened.

        Raises:
            SplitsError: If ``arm`` is reserved and unspent and this process has
                not declared a spend for it through :meth:`declare_spend`. The
                message carries the state, the record, both triggers and the
                literal call that would permit the read.
        """
        entry = self.reservation(arm)
        if entry is None or entry.is_spent:
            return
        if (self.name, arm) in _DECLARED_SPENDS:
            return
        raise SplitsError(entry.refusal())

    def declare_spend(
        self, arm: str, *, decision: str, purpose: str, stream: Any = None
    ) -> Optional[Reservation]:
        """Say, before opening it, that this run is the spend a reservation names.

        The runner that owns the read calls this once, at the top of its
        ``main``; every subsequent :meth:`require_unreserved` for that
        ``(corpus, arm)`` in the same process then passes. Nothing else opens
        the door.

        **The ergonomics, argued rather than assumed, because a guard people
        route around is worse than no guard.** Three properties do the work:

        * *One call, and it is free when there is nothing to declare.* On an
          unreserved arm this returns ``None`` and does nothing, so a runner may
          call it unconditionally without first knowing what is reserved. The
          cost of complying is one line; the cost of bypassing is reimplementing
          a reader.
        * *No flag, no environment variable, no config.* A ``--force`` is a
          thing people type without reading and an environment variable does not
          appear in a run log. A keyword argument naming a decision record is
          read by whoever wrote it and by whoever reviews the diff.
        * *It asks for what the caller already knows and nothing else.* The
          record id and one line of purpose. It does not ask the runner to
          restate the trigger, copy the allocation prose, or thread a token
          through its call graph -- duplication is what D-045 warns goes stale.

        **One door, because there is more than one ledger.** This module is
        imported *by path* by ``bench/corpora.py`` and again by
        ``tests/test_splits_manifest.py``, so those are two module objects with
        two :data:`_DECLARED_SPENDS` dicts. A runner that imported the loader
        itself, declared a spend, and then went through ``bench.corpora`` would
        be refused by a ledger it never wrote to. Runners call
        ``bench.corpora.declare_spend``, which is the door the reader consults.

        What it deliberately does **not** do is edit ``bench/splits.toml``. A
        runner that could mark its own arm spent would be spending it with no
        commit and no review. Recording the spend stays a manifest edit
        (``state = "spent"``, ``spent_in = "<run id>"``) made beside the number,
        which is the same pairing R1 requires of a claim and its baseline.

        Args:
            arm: The split token about to be opened.
            decision: The record that allocates the arm, e.g. ``"D-047"``. It
                must be the reservation's own ``decided_in``: spending under a
                different record is a *re-allocation*, and a re-allocation is a
                manifest edit plus a record, never a runner argument.
            purpose: One line saying what this run buys. Non-empty, and printed,
                so the spend is visible in the log rather than inferred later
                from a file's mtime.
            stream: Where the banner goes. Defaults to :data:`sys.stderr`;
                injectable so a test does not have to capture the process's.

        Returns:
            The :class:`Reservation` that was spent, or ``None`` when ``arm``
            carries no reservation at all.

        Raises:
            SplitsError: If the arm is ``unallocated`` (its first spend needs
                its own record -- first-come is refused), if ``decision`` is not
                the record that allocated it, or if ``purpose`` is empty.
        """
        out = sys.stderr if stream is None else stream
        entry = self.reservation(arm)
        if entry is None:
            return None
        if entry.is_spent:
            print(
                f"note: {self.name} arm {arm!r} was already spent ({entry.spent_in or 'unrecorded'}). "
                "It is mined and adjudicates nothing blind; label the figure accordingly.",
                file=out,
            )
            return entry
        if not purpose.strip():
            raise SplitsError(
                f"{self.name} arm {arm!r}: a spend needs a purpose. One line, and it goes in "
                "the run log -- 'what this run buys' is the thing nobody can reconstruct "
                "afterwards from the fact that a file was read."
            )
        if entry.state == "unallocated":
            raise SplitsError(
                f"{self.name} arm {arm!r} is UNALLOCATED and first-come is refused "
                f"({entry.decided_in} says so). Its first spend needs its own decision record, "
                'and the manifest must then carry a reservation with state = "allocated" '
                "naming it. Write the record, edit bench/splits.toml, then run.\n"
                f"  reserved because: {_first_line(entry.spend_trigger)}"
            )
        if decision.strip() != entry.decided_in:
            raise SplitsError(
                f"{self.name} arm {arm!r} is allocated by {entry.decided_in} and this run names "
                f"{decision!r}. Spending an arm under a different record is a RE-ALLOCATION, not "
                "an argument: amend the reservation in bench/splits.toml and say why in a record, "
                "in the same commit as the number. Priority does not transfer by default."
            )
        _DECLARED_SPENDS[(self.name, arm)] = purpose.strip()
        print(
            "\n".join(
                [
                    "SPENDING A RESERVED ARM",
                    f"  corpus       {self.name}",
                    f"  arm          {arm}" + (f"  ({entry.file})" if entry.file else ""),
                    f"  allocated by {entry.decided_in} to: {_first_line(entry.allocated_to)}",
                    f"  purpose      {purpose.strip()}",
                    "  After this run the arm is MINED. Record it in the same commit as the",
                    '  number: state = "spent", spent_in = "<run id>" on the reservation.',
                ]
            ),
            file=out,
        )
        return entry


@dataclass(frozen=True)
class Policy:
    """The ``[policy]`` table.

    Attributes:
        headline_requires: The role a headline number must come from.
        label_tuning_numbers: Whether tuning figures must be labelled as such.
    """

    headline_requires: str = "held_out"
    label_tuning_numbers: bool = True


@dataclass(frozen=True)
class Manifest:
    """The whole of ``bench/splits.toml``, parsed."""

    path: Path
    policy: Policy
    corpora: Mapping[str, Corpus]

    @property
    def names(self) -> Tuple[str, ...]:
        """Every declared corpus name, sorted."""
        return tuple(sorted(self.corpora))

    def corpus(self, name: str) -> Corpus:
        """Look up one corpus, or say what is available.

        Raises:
            SplitsError: If ``name`` is not declared. This is the point of the
                accessor: a corpus that is measured but never declared is
                exactly the gap the manifest exists to close, and a
                ``KeyError`` would not say so.
        """
        try:
            return self.corpora[name]
        except KeyError:
            raise SplitsError(
                f"{name!r} is not declared in {self.path.name}. "
                f"Declared corpora: {', '.join(self.names)}. "
                "A corpus that is measured but not declared is exempt from the "
                "train/test rule by omission; add an entry rather than skipping it."
            ) from None

    def reserved_arms(self) -> Tuple[Reservation, ...]:
        """Every reserved arm in the manifest, in corpus then declaration order.

        The list a person wants when asking "what may this round not touch?",
        which until now could only be answered by reading two decision records
        and a manifest note.

        Named for what it returns rather than ``reservations``, which is the
        *attribute* on :class:`Corpus`. A caller who wrote ``manifest.
        reservations`` without the parentheses would get a bound method --
        truthy, iterable of nothing useful, and silent.
        """
        out: List[Reservation] = []
        for name in self.names:
            out.extend(self.corpora[name].reservations)
        return tuple(out)

    def require_unreserved(self, name: str, arm: str) -> None:
        """:meth:`Corpus.require_unreserved`, for a caller holding only names.

        Raises:
            SplitsError: If ``name`` is undeclared, or ``arm`` is reserved and
                unspent with no declared spend.
        """
        self.corpus(name).require_unreserved(arm)

    def declare_spend(
        self, name: str, arm: str, *, decision: str, purpose: str, stream: Any = None
    ) -> Optional[Reservation]:
        """:meth:`Corpus.declare_spend`, for a caller holding only names."""
        return self.corpus(name).declare_spend(
            arm, decision=decision, purpose=purpose, stream=stream
        )

    def with_role(self, role: str) -> Tuple[Corpus, ...]:
        """Every corpus carrying ``role``, sorted by name."""
        return tuple(self.corpora[name] for name in self.names if self.corpora[name].role == role)

    def with_task(self, task: str) -> Tuple[Corpus, ...]:
        """Every corpus declared for ``task``, sorted by name.

        Raises:
            SplitsError: If ``task`` is not in :data:`TASKS`. A typo would
                otherwise return an empty tuple, which reads as "no corpus
                covers this" -- a true-looking answer to a question nobody
                asked.
        """
        if task not in TASKS:
            raise SplitsError(f"task={task!r} is not one of {list(TASKS)}")
        return tuple(self.corpora[name] for name in self.names if self.corpora[name].task == task)

    def headline_capable(self, task: str) -> Tuple[Corpus, ...]:
        """Every corpus a headline number **about** ``task`` may legitimately come from.

        ``task`` is required, and that is the whole point of the signature.
        This function used to be task-blind: it returned every uncontaminated
        corpus in the headline role whatever it was annotated for. That was
        harmless only while every declared corpus happened to be a pair or a
        span corpus, and it stopped being harmless the moment an
        ``identifier_segmentation`` corpus was registered as ``held_out`` --
        because a corpus that scores *where an identifier is cut* would have
        become an eligible source for a headline about *extracting definitions
        from prose*. Nothing would have failed; a table would simply have been
        published against a corpus structurally incapable of showing the
        phenomenon it claimed to measure.

        Making the argument required rather than optional is deliberate. A
        default of "any task" leaves the hole open under a shorter call, and the
        caller who most needs to be asked what their headline is about is
        exactly the caller who would have omitted the argument.

        Args:
            task: One of :data:`TASKS`. What the headline number is a claim
                *about*.

        Returns:
            The uncontaminated corpora declared for ``task`` in the role
            ``[policy] headline_requires`` names, sorted by name. Empty means
            no number about ``task`` currently satisfies the headline rule --
            which is a fact worth printing, not an error.

        Raises:
            SplitsError: If ``task`` is not in :data:`TASKS`.
        """
        # Compared by name, not by identity or value: ``Corpus`` is frozen but
        # carries a ``dict`` in ``extra``, so it is not hashable and a set
        # membership test would raise rather than filter.
        wanted = {corpus.name for corpus in self.with_task(task)}
        return tuple(
            corpus
            for corpus in self.with_role(self.policy.headline_requires)
            if not corpus.contaminated and corpus.name in wanted
        )


def _as_bool(value: Any) -> Optional[bool]:
    """Coerce a TOML value to ``bool``, or ``None`` when it is absent."""
    return bool(value) if isinstance(value, bool) else None


def _as_date(value: Any) -> Optional[_datetime.date]:
    """Coerce a TOML value to a date.

    TOML has a native date type, so a bare ``2026-08-23`` parses to
    :class:`datetime.date` already; a quoted ``"2026-08-23"`` arrives as a
    string. Both are accepted and anything else is rejected by the validator.
    """
    if isinstance(value, _datetime.datetime):
        return value.date()
    if isinstance(value, _datetime.date):
        return value
    if isinstance(value, str):
        try:
            return _datetime.date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


_MODELLED = frozenset(
    {
        "role",
        "task",
        "licence",
        "licence_url",
        "licence_read_on",
        "status",
        "contaminated",
        "contamination_reason",
        "vendorable",
        "domain",
        "shortform_recall_ceiling_pct",
        "shortform_recall_ceiling_basis",
        "note",
        "reservations",
    }
)


def _text(spec: Mapping[str, Any], key: str) -> str:
    """One reservation field as stripped text, whatever TOML made of it."""
    value = spec.get(key, "")
    return str(value).strip() if value is not None else ""


def _reservation_from(corpus_name: str, spec: Mapping[str, Any]) -> Reservation:
    """Build one :class:`Reservation`, coercing nothing away.

    Unrecognised keys are *recorded*, not dropped and not merged into anything:
    :func:`validate` reports them. See :data:`RESERVATION_FIELDS` for why this
    differs from the corpus table's permissive ``extra``.
    """
    return Reservation(
        corpus=corpus_name,
        arm=_text(spec, "arm"),
        state=_text(spec, "state"),
        decided_in=_text(spec, "decided_in"),
        allocated_to=_text(spec, "allocated_to"),
        spend_trigger=_text(spec, "spend_trigger"),
        lapse_trigger=_text(spec, "lapse_trigger"),
        not_a_trigger=_text(spec, "not_a_trigger"),
        spent_in=_text(spec, "spent_in"),
        file=_text(spec, "file"),
        note=_text(spec, "note"),
        unknown_keys=tuple(sorted(key for key in spec if key not in RESERVATION_FIELDS)),
    )


def _reservations_from(
    name: str, spec: Mapping[str, Any]
) -> Tuple[Tuple[Reservation, ...], Tuple[str, ...]]:
    """``(reservations, structural defects)`` for one corpus table."""
    raw = spec.get("reservations")
    if raw is None:
        return (), ()
    if not isinstance(raw, list):
        return (), (
            f"reservations must be an array of tables ([[corpora.{name}.reservations]]), "
            f"not {type(raw).__name__}",
        )
    entries: List[Reservation] = []
    defects: List[str] = []
    for index, item in enumerate(raw):
        if isinstance(item, dict):
            entries.append(_reservation_from(name, item))
        else:
            defects.append(f"reservations[{index}] is not a table")
    return tuple(entries), tuple(defects)


def _corpus_from(name: str, spec: Mapping[str, Any]) -> Corpus:
    """Build a :class:`Corpus` from one raw table, coercing nothing away.

    Fields that fail to coerce become their falsy defaults so the *validator*
    reports them, rather than this constructor raising. Two different error
    reports for one malformed file is how a check ends up with two behaviours.
    """
    ceiling = spec.get("shortform_recall_ceiling_pct")
    reservations, reservation_defects = _reservations_from(name, spec)
    return Corpus(
        name=name,
        role=str(spec.get("role", "") or ""),
        task=str(spec.get("task", "") or ""),
        licence=str(spec.get("licence", "") or ""),
        licence_url=str(spec.get("licence_url", "") or ""),
        licence_read_on=_as_date(spec.get("licence_read_on")) or _datetime.date.min,
        status=str(spec.get("status", "") or ""),
        contaminated=bool(spec.get("contaminated", False)),
        contamination_reason=str(spec.get("contamination_reason", "") or ""),
        vendorable=_as_bool(spec.get("vendorable")),
        domain=str(spec.get("domain", "") or ""),
        shortform_recall_ceiling_pct=(
            float(ceiling)
            if isinstance(ceiling, (int, float)) and not isinstance(ceiling, bool)
            else None
        ),
        shortform_recall_ceiling_basis=str(spec.get("shortform_recall_ceiling_basis", "") or ""),
        note=str(spec.get("note", "") or ""),
        reservations=reservations,
        reservation_defects=reservation_defects,
        extra={key: value for key, value in spec.items() if key not in _MODELLED},
    )


def load(path: Optional[Path] = None) -> Manifest:
    """Parse the manifest into typed objects.

    Args:
        path: Override the default ``bench/splits.toml`` location, so tests can
            drive the same code against a fixture rather than against whatever
            the repository happens to hold today.

    Returns:
        The parsed manifest.

    Raises:
        SplitsError: If the file is missing, unparseable, or has no ``corpora``
            table at all. Everything softer than that is a *validation* finding
            and is reported by :func:`validate`, so one bad field does not stop
            the report that would have listed the other nine.
    """
    location = Path(path) if path is not None else SPLITS_PATH
    document = _load_toml(location)

    raw_corpora = document.get("corpora")
    if not isinstance(raw_corpora, dict) or not raw_corpora:
        raise SplitsError(f"{location} declares no corpora; the manifest guards nothing")

    raw_policy = document.get("policy") or {}
    policy = Policy(
        headline_requires=str(raw_policy.get("headline_requires", "held_out")),
        label_tuning_numbers=bool(raw_policy.get("label_tuning_numbers", True)),
    )
    corpora = {
        name: _corpus_from(name, spec)
        for name, spec in raw_corpora.items()
        if isinstance(spec, dict)
    }
    return Manifest(path=location, policy=policy, corpora=corpora)


def _licence_url_problem(url: str) -> Optional[str]:
    """Why ``url`` is not an acceptable citation for licence terms, if it is not."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return f"licence_url={url!r} is not an http(s) URL"
    host = parts.netloc.lower()
    if any(host == badge or host.endswith("." + badge) for badge in BADGE_HOSTS):
        return (
            f"licence_url={url!r} points at a badge host. Operating rule 4: read the terms. "
            "GLADIS's badge said CC0 while its own source table listed UMLS."
        )
    lowered = parts.path.lower()
    if any(fragment in lowered for fragment in BADGE_PATH_FRAGMENTS):
        return f"licence_url={url!r} points at a badge image, not licence text"
    if host == "api.github.com" and lowered.endswith("/license"):
        return (
            f"licence_url={url!r} is GitHub's licence *guess* for a repository, not the terms. "
            "It reported MIT for three corpora in this project whose data is CC BY-NC-SA."
        )
    return None


def _is_absent(corpus: Corpus, declared: str) -> bool:
    """Whether ``corpus`` failed to declare ``declared``.

    A date needs its own emptiness test: :func:`_corpus_from` writes
    :attr:`datetime.date.min` when the field is missing *or* unparseable, and
    that value is truthy, so a plain falsiness check would pass a corpus whose
    ``licence_read_on`` reads ``"last Tuesday"``.
    """
    if declared == "licence_read_on":
        return corpus.licence_read_on == _datetime.date.min
    return not getattr(corpus, declared)


def _reservation_problems(corpus: Corpus) -> List[str]:
    """Every way this corpus's reservations fail to be reservations.

    The rules, and the failure each one is named after:

    * **No trigger.** A reservation whose firing condition is unwritten is
      reserved *for* nothing: it survives round after round because nobody
      happened to want it, and then attracts a proposal it cannot serve. That is
      D-043's finding about AD ``test.json``, in the sentence that gave the
      reservation a trigger in the first place.
    * **A state contradicting its own fields.** ``unallocated`` with an
      ``allocated_to``; a lapse trigger on something that is not an allocation;
      a spent arm with nothing recorded as having spent it. Each reads as
      governance and means nothing.
    * **Two reservations on one arm.** This is the exact collision D-043 found
      and D-047 resolved -- one unread split claimed by two live questions,
      where whichever runner touches it first decides. Written as two structures
      it is a contradiction the file can refuse.
    * **The same event as both triggers.** An allocation that lapses on the
      event that fires it is unfalsifiable.
    * **An unrecognised key.** See :data:`RESERVATION_FIELDS`.
    """
    where = f"[corpora.{corpus.name}]"
    problems = [f"{where} {defect}" for defect in corpus.reservation_defects]
    seen: Dict[str, int] = {}

    for index, entry in enumerate(corpus.reservations):
        at = f"{where} reservations[{index}]"

        if entry.unknown_keys:
            problems.append(
                f"{at} carries unrecognised key(s): {', '.join(entry.unknown_keys)}. A "
                f"reservation may hold only {list(RESERVATION_FIELDS)} -- a misspelt trigger "
                "key would drop the trigger silently, which is the prose reservation again "
                "wearing a schema."
            )

        if not entry.arm:
            problems.append(f"{at} declares no arm; a reservation over nothing guards nothing")
        elif not _ARM_RE.match(entry.arm):
            problems.append(
                f"{at} arm={entry.arm!r} is not a split token. Use the string a RUNNER passes "
                "('train'), and put the upstream filename in `file`: the guard is a literal "
                "match, so reserving a filename nobody passes is a guard that cannot fire."
            )
        elif entry.arm in seen:
            problems.append(
                f"{at} and reservations[{seen[entry.arm]}] both reserve arm={entry.arm!r}. Two "
                "reservations on one arm CONTRADICT: whichever runner touches it first decides, "
                "which is the collision D-043 found and D-047 had to resolve by hand. Allocate "
                "it once, and name the loser in the winning entry."
            )
        else:
            seen[entry.arm] = index

        if entry.state not in RESERVATION_STATES:
            problems.append(f"{at} state={entry.state!r} is not one of {list(RESERVATION_STATES)}")
        if not _DECISION_RE.match(entry.decided_in):
            problems.append(
                f"{at} decided_in={entry.decided_in!r} is not a decision record id (D-nnn). A "
                "reservation with no record behind it cannot be argued down or re-designated, "
                "and is indistinguishable from an arm nobody has wanted yet."
            )

        if entry.state in ("allocated", "unallocated") and not entry.spend_trigger:
            problems.append(
                f"{at} has no spend_trigger. THIS IS THE FIELD THE STRUCTURE EXISTS FOR: without "
                "it the arm is not reserved for anything, it is merely unspent, and each round "
                "it survives because nobody happened to want it."
            )

        if entry.state == "allocated":
            if not entry.allocated_to:
                problems.append(
                    f"{at} is state='allocated' with no allocated_to. Allocated to what?"
                )
            if not entry.lapse_trigger:
                problems.append(
                    f"{at} is state='allocated' with no lapse_trigger. An allocation with no way "
                    "to be released is permanent by omission; D-047 wrote one because priority "
                    "must not transfer by default, and must not be immovable either."
                )
        else:
            if entry.allocated_to:
                problems.append(
                    f"{at} is state={entry.state!r} and names allocated_to. Contradiction: only "
                    "an allocation is allocated to something."
                )
            if entry.lapse_trigger:
                problems.append(
                    f"{at} is state={entry.state!r} and names a lapse_trigger. Contradiction: "
                    "only an allocation can lapse."
                )

        if entry.state == "spent" and not entry.spent_in:
            problems.append(
                f"{at} is state='spent' with no spent_in. A spend nobody can point at is a "
                "contamination with no evidence, which is the shape contamination_reason "
                "already refuses one level up."
            )

        if entry.spend_trigger and entry.spend_trigger == entry.lapse_trigger:
            problems.append(
                f"{at} gives the same event as spend_trigger and lapse_trigger. An allocation "
                "that lapses on the event that fires it cannot be acted on either way."
            )

    return problems


def validate(manifest: Manifest, *, today: Optional[_datetime.date] = None) -> List[str]:
    """Every way this manifest fails the rules it exists to encode.

    Args:
        manifest: A loaded manifest.
        today: The date to judge ``licence_read_on`` against. Injectable so the
            test suite does not depend on the wall clock.

    Returns:
        Problems, one string each, in corpus order. Empty means valid.
    """
    now = today or _datetime.date.today()
    problems: List[str] = []

    if manifest.policy.headline_requires not in ROLES:
        problems.append(
            f"[policy] headline_requires={manifest.policy.headline_requires!r} "
            f"is not one of {list(ROLES)}"
        )

    for name in manifest.names:
        corpus = manifest.corpora[name]
        where = f"[corpora.{name}]"

        missing = [declared for declared in REQUIRED_FIELDS if _is_absent(corpus, declared)]
        if missing:
            problems.append(f"{where} is missing or empty: {', '.join(missing)}")

        if corpus.role and corpus.role not in ROLES:
            problems.append(f"{where} role={corpus.role!r} is not one of {list(ROLES)}")
        if corpus.task and corpus.task not in TASKS:
            problems.append(f"{where} task={corpus.task!r} is not one of {list(TASKS)}")

        if corpus.licence_url:
            problem = _licence_url_problem(corpus.licence_url)
            if problem:
                problems.append(f"{where} {problem}")

        if corpus.licence_read_on != _datetime.date.min and corpus.licence_read_on > now:
            problems.append(
                f"{where} licence_read_on={corpus.licence_read_on.isoformat()} is in the future"
            )

        if corpus.contaminated and not corpus.contamination_reason.strip():
            problems.append(
                f"{where} is contaminated=true with no contamination_reason. "
                "An unexplained contamination flag can never be argued down."
            )

        if corpus.contaminated and corpus.role == manifest.policy.headline_requires:
            problems.append(
                f"{where} is contaminated=true and role={corpus.role!r}, which is the role "
                "[policy] headline_requires. A corpus whose misses have been read adjudicates "
                "nothing blind, so it cannot be the one a headline number comes from. This is "
                "the MED1250 story: it was a test set until its miss taxonomy was analysed, and "
                "it could not be un-tuned afterwards."
            )

        ceiling = corpus.shortform_recall_ceiling_pct
        if ceiling is not None:
            if not 0.0 < ceiling <= 100.0:
                problems.append(f"{where} shortform_recall_ceiling_pct={ceiling} is not a percent")
            if not corpus.shortform_recall_ceiling_basis.strip():
                problems.append(
                    f"{where} declares a recall ceiling with no "
                    "shortform_recall_ceiling_basis. A ceiling whose derivation is "
                    "not written down cannot be checked, and it would be quoted."
                )
            if corpus.task and corpus.task not in SHORT_FORM_TASKS:
                problems.append(
                    f"{where} declares shortform_recall_ceiling_pct on task={corpus.task!r}, "
                    f"whose gold contains no short forms: it is "
                    f"{TASK_GOLD_UNIT.get(corpus.task, 'a different shape entirely')}. "
                    "A ceiling on a quantity the corpus does not annotate is not a "
                    "conservative extra; it is a number that would be quoted beside a "
                    "recall figure measuring something else."
                )

        problems.extend(_reservation_problems(corpus))
    return problems


def notes(manifest: Manifest, *, today: Optional[_datetime.date] = None) -> List[str]:
    """Advisories that must never fail a build.

    A licence read long ago is worth re-reading, and a project with no
    uncontaminated held-out corpus should be reminded of it. Neither is a defect
    in the commit being tested, so neither reds the build -- the gate that fires
    on an unrelated commit is the gate people learn to ignore.

    **The headline-gap advisory is reported per task, and that is a correction
    rather than a refinement.** The single pooled line it replaced said nothing
    once *any* corpus qualified: registering two held-out
    ``identifier_segmentation`` corpora would have silenced it while the project
    still had no uncontaminated held-out corpus for extraction and none for
    disambiguation. A pooled advisory over a per-task rule reports the union and
    hides every gap inside it.
    """
    now = today or _datetime.date.today()
    out: List[str] = []
    for name in manifest.names:
        corpus = manifest.corpora[name]
        if corpus.licence_read_on == _datetime.date.min:
            continue
        age = (now - corpus.licence_read_on).days
        if age > STALE_AFTER_DAYS:
            out.append(
                f"[corpora.{name}] licence last read {age} days ago "
                f"({corpus.licence_read_on.isoformat()}); worth re-reading"
            )
    for task in TASKS:
        declared = [corpus for corpus in manifest.corpora.values() if corpus.task == task]
        if not declared:
            continue
        if not manifest.headline_capable(task):
            out.append(
                f"no uncontaminated corpus carries role="
                f"{manifest.policy.headline_requires!r} for task={task!r} "
                f"({len(declared)} declared, none eligible), so no {task} number in this "
                "project currently satisfies the headline rule"
            )
    return out


def as_dict(manifest: Manifest) -> Dict[str, Any]:
    """The manifest as plain JSON-safe data, for ``--json`` and for tests."""
    return {
        "policy": {
            "headline_requires": manifest.policy.headline_requires,
            "label_tuning_numbers": manifest.policy.label_tuning_numbers,
        },
        # Per task, never pooled. A single flat list of headline-capable
        # corpora is the shape that let a segmentation corpus look like an
        # eligible source for a pair headline, so the JSON view does not offer
        # one.
        "headline_capable": {
            task: [corpus.name for corpus in manifest.headline_capable(task)] for task in TASKS
        },
        "gold_unit": dict(TASK_GOLD_UNIT),
        # Flat as well as per corpus, because "what may this round not touch?"
        # is a question about the manifest and not about any one entry, and it
        # was previously answerable only by reading two decision records.
        "reserved_arms": [
            {
                "corpus": entry.corpus,
                "arm": entry.arm,
                "state": entry.state,
                "decided_in": entry.decided_in,
                "allocated_to": entry.allocated_to,
                "spend_trigger": entry.spend_trigger,
                "lapse_trigger": entry.lapse_trigger,
                "not_a_trigger": entry.not_a_trigger,
                "spent_in": entry.spent_in,
                "file": entry.file,
            }
            for entry in manifest.reserved_arms()
        ],
        "corpora": {
            name: {
                "role": corpus.role,
                "task": corpus.task,
                "licence": corpus.licence,
                "licence_url": corpus.licence_url,
                "licence_read_on": corpus.licence_read_on.isoformat(),
                "status": corpus.status,
                "contaminated": corpus.contaminated,
                "domain": corpus.domain,
                "vendorable": corpus.vendorable,
                "shortform_recall_ceiling_pct": corpus.shortform_recall_ceiling_pct,
                "label": corpus.label(),
                "reserved_arms": [entry.arm for entry in corpus.reservations],
            }
            for name, corpus in ((n, manifest.corpora[n]) for n in manifest.names)
        },
    }


def _render_reservations(manifest: Manifest) -> str:
    """The reserved arms, as a block ``--check`` and ``--list`` both print.

    Printed on every run for the same reason the per-task headline gap is: the
    person about to spend an arm is not reading a decision record, they are
    running a benchmark, and this is the surface in front of them.
    """
    entries = manifest.reserved_arms()
    if not entries:
        return "reserved arms: none declared"
    lines = [f"{len(entries)} reserved arm(s) -- no runner may open one without declaring a spend:"]
    for entry in entries:
        head = f"  {entry.corpus}:{entry.arm}"
        lines.append(f"{head:38} {entry.state:12} {entry.decided_in}")
        detail = entry.allocated_to or entry.spend_trigger
        if detail:
            lines.append(f"{'':38} {_first_line(detail)}")
    return "\n".join(lines)


def _render_table(manifest: Manifest) -> str:
    """The manifest as a table a person can read at a glance."""
    # The TASK column is 24 wide, not 16, because "identifier_segmentation" is
    # 23 characters: a format spec narrower than its widest value does not
    # truncate, it overflows and shears every column to its right.
    lines = [
        f"{'CORPUS':22} {'ROLE':9} {'TASK':24} {'READ':11} {'CEILING':>8}  LICENCE",
        f"{'-' * 22} {'-' * 9} {'-' * 24} {'-' * 11} {'-' * 8}  {'-' * 40}",
    ]
    for name in manifest.names:
        corpus = manifest.corpora[name]
        read = (
            "never"
            if corpus.licence_read_on == _datetime.date.min
            else corpus.licence_read_on.isoformat()
        )
        ceiling = (
            f"{corpus.shortform_recall_ceiling_pct:.2f}%"
            if corpus.shortform_recall_ceiling_pct is not None
            else "-"
        )
        role = corpus.role + ("*" if corpus.contaminated else "")
        lines.append(
            f"{name:22} {role:9} {corpus.task:24} {read:11} {ceiling:>8}  {corpus.licence}"
        )
    lines.append("")
    lines.append(
        "* contaminated: the corpus has been read closely enough that it adjudicates nothing blind."
    )
    lines.append("")
    lines.append(_render_reservations(manifest))
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point.

    Returns:
        ``0`` when the manifest parses and validates, ``1`` otherwise.
    """
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true", help="validate and exit non-zero on error")
    parser.add_argument("--list", action="store_true", help="print the manifest as a table")
    parser.add_argument("--json", action="store_true", help="print the manifest as JSON")
    parser.add_argument(
        "--path",
        type=Path,
        default=SPLITS_PATH,
        help="manifest to read (default: bench/splits.toml)",
    )
    args = parser.parse_args(argv)

    try:
        manifest = load(args.path)
    except SplitsError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(as_dict(manifest), indent=2, sort_keys=True))
        return 0
    if args.list:
        print(_render_table(manifest))
        return 0

    problems = validate(manifest)
    print(
        f"{args.path}: {len(manifest.corpora)} corpora, "
        f"{len(manifest.reserved_arms())} reserved arm(s), {len(problems)} problem(s)"
    )
    for note in notes(manifest):
        print(f"  note: {note}")
    print(_render_reservations(manifest))
    if not problems:
        print(
            "splits manifest OK: every corpus declares a role, a task, and a licence read "
            "from its terms at a recorded URL on a recorded date"
        )
        return 0
    print(f"\n{len(problems)} problem(s):\n", file=sys.stderr)
    for problem in problems:
        print(f"  {problem}", file=sys.stderr)
    print(
        "\nbench/splits.toml is the file operating rules 2, 3 and 4 rest on. Every corpus must\n"
        "declare role, task, licence, licence_url and licence_read_on -- the last two because\n"
        "a licence string on its own records a conclusion and destroys the evidence for it.\n"
        "Every reserved arm must declare a state, the record that decided it and the trigger\n"
        "that would fire it, because a reservation with no trigger is reserved for nothing.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
