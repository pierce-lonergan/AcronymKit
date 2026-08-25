#!/usr/bin/env python3
"""Fail the build when a performance or accuracy claim is not backed by a measurement.

Why this exists
---------------
A docstring in this repository once said a change "raises F1 from 84.78 to
89.87". The 89.87 was never measured -- it was written while implementing the
change and would have shipped had it not been caught by hand. A rule that
depends on being caught by hand is not a rule.

So: every number that reads as a *claim* must be traceable to
``bench/results.json``, which only the benchmark runners write.

Two ways to be traceable, and only one of them is sound
-------------------------------------------------------
**Cited (strict).** The prose names the measurement it came from::

    {{claim:extraction.med1250.acronymkit.exact_f1}}

That reference is resolved against ``bench/results.json`` by run id and field.
If it does not resolve, the build fails. That is the whole point: a citation
can be *wrong*, and being wrong is detectable.

**Value-matched (fallback, unsound).** The number appears somewhere in
``bench/results.json``, matched at the precision written. This is how the 87
existing claims are backed and it is kept working deliberately -- a flag day
would be worse -- but it cannot tell a correct claim from a number that
coincidentally equals an unrelated measurement. ``--migrate`` lists which
value-matched claims are ambiguous under that test, and those are exactly the
ones whose backing means nothing. The summary line reports how many claims sit
on each path so the migration can be tracked rather than hoped for.

Why value matching had to stop being a *path a new claim may take*
-------------------------------------------------------------------
Value matching does not verify a claim; it verifies that *some* measurement
somewhere happens to have that value. The August 2026 audit found what that
costs: ``docs/DECISIONS.md`` said "Headroom today is 113,269 bytes", the figure
had been derived under a budget that no longer existed, and **two independent
auditors re-quoted it as current**. Nothing failed, because nothing was
checking that the number came from where the sentence said it came from.

So the fallback is now a **ratchet** rather than an open door.
:data:`VALUE_MATCHED_BASELINE` records how many value-matched claims each file
is allowed to carry -- the 87 that existed when the ratchet was installed. The
count per file must match exactly:

* **more** than the baseline means a new claim was written without a citation.
  That is the enforcement: new claims must use ``{{claim:<run-id>.<field>}}``,
  which names its source and can therefore be *wrong*, which is the only
  property that makes a check worth running.
* **fewer** means a claim was migrated to a citation, which is the goal --
  lower the number in the same commit. ``--update-baseline`` prints the block
  to paste. It is deliberately a source edit and not a file the tool rewrites
  itself: the diff is the record of which direction the migration went.

The ratchet only engages when scanning **this** checkout. Pointed at any other
root -- which is how the tool's own tests drive it -- it is off, because the
baseline is a fact about these documents and not about the algorithm.

Two further escapes exist, both narrow:

* a trailing ``# measured: <run-id>`` / ``<!-- measured: <run-id> -->`` marker,
  which now *validates* that the run id exists; and
* ``tools/claims_allowlist.txt``, for figures published by other authors.

What counts as a claim
----------------------
A free-standing number in **prose** that some *arming rule* picks up. Two rules
arm, and they fail in different directions:

* **proximity** -- the number sits within :data:`_PROXIMITY` characters of a
  metric keyword used as a word. This is the original rule.
* **unit** -- the number is immediately followed by a metric unit (:data:`_UNIT_AFTER_NUMBER`):
  ``96 %``, ``62.40 µs``, ``4,219 docs/s``. No keyword required.

Either way the number must be free-standing and in prose, and each of those two
conditions removes a class of false positive this check used to raise, without
a special case for any character:

* *free-standing* -- the number must be the whole token a reader sees, so the
  ``25`` in ``R@25``, the ``012`` in ``D-012``, the ``1250`` in ``MED1250`` and
  the ``402`` in a ``2008;9:402`` citation are not claims. They are parts of
  identifiers, not numbers in their own right.
* *in prose* -- fenced code blocks, inline code spans and, in Python files,
  everything that is not a comment or a string literal. ``max(0.0, min(1.0,
  precision))`` is code; ``length_penalty = 8.0`` is a default, not a result.

and a keyword only arms when it stands as a word: ``f1`` inside ``Lf1chSf`` and
``precision`` inside ``SCORE_PRECISION`` do not make their line a claim about
performance.

The second rule exists because the first has a failure mode that no tuning of
:data:`_PROXIMITY` can reach. README carried ``F₁ > 96 %`` and the gate never
saw it -- not because 96 was too far from a keyword, but because that line has
*no keyword on it at all*: ``F₁`` is U+2081 SUBSCRIPT ONE, not the ASCII ``f1``
in :data:`_KEYWORDS`. Proximity is a rule about distance, and the miss was about
vocabulary. Widening the window from 48 to 480 would not have armed it; a rule
that reads the number's own shape does.

Nothing is dropped silently
---------------------------
A prose number that no rule arms used to be discarded inside the scanner, which
made it **invisible rather than un-backed**: counted in no total, named in no
report, and absent from a summary line that read as if it covered the document.
That is worse than a false positive. A flagged number gets argued about; an
invisible one is indistinguishable from a document with nothing to check.

So every claim-shaped prose number now becomes a :class:`Claim`, and the ones no
rule armed carry ``backing="unexamined"``. They never fail the build. They are
counted in the summary, listed by ``--list``, and reported by ``--residue``.

**Unexamined numbers are deliberately not value-matched.** That is not an
oversight and it is the load-bearing decision here. Measured on this checkout
before the change: of the fifteen prose numbers README had that the gate could
not see, nine equalled some value in ``bench/results.json`` -- and every one of
the nine was ``AMBIGUOUS`` under :func:`classify`. ``100`` equals 117 distinct
measurements; ``2`` equals 97. Feeding the residue through value matching would
have relabelled 1,144 invisible numbers "backed" across the tree -- 792 of them
AMBIGUOUS on their own report -- most of them
publication years, parameter defaults and rank cutoffs. That reproduces the
original defect one level up and makes it harder to see, because an invisible
number at least does not claim to be backed.

Two ledgers, because widening coverage must not launder into the old one
------------------------------------------------------------------------
Widening the gate -- the unit rule, plus ``CHANGELOG.md`` and
``bench/splits.toml`` entering ``SCAN_GLOBS`` -- surfaced **316 numbers across 11
files that no run of this tool had ever counted**, and **76 of them match no
measurement in bench/results.json at all**. Thirty-five are in
``docs/DECISIONS.md``, thirty-four in ``docs/notes/pydantic-cost.md``
(``139.60 ms`` and its table), four in ``CHANGELOG.md`` including the ``62.40``
of a governed-naming latency row that has been in a release note since it was
written. The summary line said ``unbacked 0`` the whole time, and it was true of
the armed subset.

Letting the 240 that *do* equal something fall onto the value path would have
forced :data:`VALUE_MATCHED_BASELINE` from 71 up past 300 -- exactly the move
that ratchet exists to make expensive, for numbers nobody had adjudicated.

So there are two registers, and **which one a bare uncited number lands on is
decided by whether the gate could already see it**:

* it could -> :data:`VALUE_MATCHED_BASELINE`, untouched at 71 across 4 files, and
  a keyword-armed number matching nothing still fails hard exactly as before.
* it could not -> ``backing="deferred"``, against :data:`DEFERRED_BASELINE`: a
  second per-file ledger with the same semantics -- exact match in both
  directions, absent means zero, lower it in the commit that migrates. A file
  with no entry admits **no** deferred number, so a document added to
  :data:`SCAN_GLOBS` tomorrow cites from its first line.

Where those figures come from, since this file is the one that adjudicates
figures: ``316 across 11 files`` is not a quoted number, it is
:data:`DEFERRED_BASELINE`, and CI re-derives and re-checks it on every run -- if
it drifts, the build says so. The rest (``76``, ``1,144``, ``792``) are counts of
one run, and the command that regenerates each is ``--residue``. None of them is
a measurement of the library, and no runner can ``--save`` a property of the
documents.

The cost is named rather than hidden: a document at its budget cannot gain a
figure without citing it. ``docs/DECISIONS.md``'s deferred count rose from 97 to
115 over the eight commits before this change, so the next round that writes a
percentage into a D-record will find the gate red and will have to cite it, mark
it, or record the figure in the baseline as a visible source edit. That friction
is R1's actual price, and it was previously being paid by a blind spot.

How this fails
--------------
**The gate still does not check most numbers, and now says so.** 1,468 remain
unexamined against 316 on the ledger, so the unit rule reaches about one number
in six of what proximity misses. "Nothing is dropped silently" is the claim;
"everything is checked" is not, and the summary prints both counts side by side
precisely so the second cannot be read into the first.

**316 is a floor on the debt, not a measure of it.** It is the count under
*this* unit vocabulary. Adding ``KB``, ``MB``, ``bytes`` or a speedup ``x`` to
:data:`_UNIT_AFTER_NUMBER` would move more of the 1,468 across, and each such
widening is another ratchet-lowering commit rather than a free win.

**The residue count inherits :func:`iter_claim_numbers`'s idea of a number.**
117 of the 1,468 are fragments of ISO dates -- ``2026-08-23`` is split by the
hyphenated-range rule into three "numbers", two of which are a month and a day.
That rule is shared with the armed path and predates this change, so fixing it
would move the value ledger too and needs its own measurement.

**The escape hatches are unchanged, and one of them is a habit rather than a
mechanism.** A figure can be fenced, cited, marked ``measured: <run-id>`` or
allowlisted. Fencing is what ``docs/notes/`` already does, and it silences the
gate completely rather than recording anything -- so a deferred count falling
is not by itself evidence that a figure was adjudicated.

Usage::

    python tools/check_claims.py                  # scan and report; the CI gate
    python tools/check_claims.py --list           # show every claim and how it is backed
    python tools/check_claims.py --residue        # every number surfaced but not verified
    python tools/check_claims.py --migrate        # which run ids could supply each value-matched claim
    python tools/check_claims.py --update-baseline    # the ratchet blocks to paste after a migration
    python tools/check_claims.py --render --dry-run   # what --render would rewrite
    python tools/check_claims.py --render         # rewrite {{claim:...}} to current values
"""

from __future__ import annotations

import argparse
import difflib
import io
import json
import re
import string
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = REPO_ROOT / "bench" / "results.json"
ALLOWLIST_PATH = REPO_ROOT / "tools" / "claims_allowlist.txt"

#: Files scanned for claims. Deliberately not the whole tree: test files are
#: full of legitimate hard-coded numbers that are assertions, not claims.
#:
#: ``CHANGELOG.md`` and ``bench/splits.toml`` were both outside this tuple while
#: publishing measured figures, which made the scan set a third place the gate
#: declined to look:
#:
#: * ``CHANGELOG.md`` is the most-read document a release has. It quotes the
#:   import triple, the MED1250 headline and a governed-naming latency table --
#:   and ``62.40`` in that table matches **no measurement in results.json at
#:   all**, which is the failure this whole tool exists to raise.
#: * ``bench/splits.toml`` publishes ``shortform_recall_ceiling_pct`` for two
#:   corpora and says of itself which of its figures are un-gated. Both ceilings
#:   do resolve (``shortform.sdu22_ae_legal_dev.corpus.ceiling_pct`` and its
#:   scientific twin), so the file was right about itself -- but nothing was
#:   checking, and "right about itself" is the state value matching cannot
#:   distinguish from luck. A manifest that publishes figures is a document.
#:
#: ``bench/splits.toml`` is not in ``MANIFEST.in``, so inside an sdist this
#: target is absent and the scan set shrinks by one file. That is reported by
#: name rather than failing, because a checker that cannot pass inside the
#: artifact is how the sdist broke the first time -- but it is *said out loud*,
#: which is the only property being defended here.
SCAN_GLOBS = (
    "README.md",
    "CHANGELOG.md",
    "docs/*.md",
    "docs/notes/*.md",
    "src/acronymkit/*.py",
    "src/acronymkit/**/*.py",
    "bench/splits.toml",
)

#: How many value-matched claims each file may carry. This is the ratchet
#: described in the module docstring: value matching backs what is already
#: written and admits nothing new, because it cannot tell a correct claim from a
#: coincidence and a stale re-quote survived two audits on exactly that gap.
#:
#: A file absent from this mapping is allowed **zero**, which is what makes new
#: documents cite by run id from the start. Regenerate after a migration with
#: ``python tools/check_claims.py --update-baseline``.
#:
#: Recorded 2026-08-23: 87 claims across 5 files. 71 across 4 as of 2026-08-24.
VALUE_MATCHED_BASELINE: Dict[str, int] = {
    # Lowered from 12 and 28 when the MED1250 extraction headline was migrated to
    # run-id citations after `balanced_trim` shipped (D-032). The ratchet only
    # works if a freed slot is closed rather than left open for the next bare
    # number to occupy quietly, which is why this moves in the same commit as
    # the migration.
    #
    # `README.md` was 5 and is now ABSENT, which the rule above reads as zero:
    # the import figure, the per-call latency figure, both CMUdict figures and
    # the disambiguation headline were migrated to run-id citations in the same
    # commit as this deletion. The README is the document a first reader lands
    # on, so it is the right one to take to zero first -- and an absent entry is
    # a stronger statement than `0`, because re-adding the key is a visible edit
    # rather than a number nudged upward.
    "docs/DECISIONS.md": 42,
    "docs/EVALUATION.md": 24,
    "docs/notes/scoring-objective.md": 3,
    "src/acronymkit/enums.py": 2,
}

#: How many unit-armed numbers each file may leave uncited. The second ratchet,
#: built exactly like :data:`VALUE_MATCHED_BASELINE` and kept separate from it on
#: purpose: these are the numbers the *unit* rule surfaced, and folding them into
#: the value budget would have raised a ratchet R1 pins shut, for figures nobody
#: had adjudicated yet.
#:
#: A file absent from this mapping is allowed **zero**. The counts below are the
#: state of the tree the day the unit rule was turned on, and they are a debt
#: register, not a licence: 69 of these 255 match no measurement in
#: ``bench/results.json`` at all, and ``--residue`` names every one.
#:
#: Regenerate after a migration with ``python tools/check_claims.py --update-baseline``.
#:
#: Recorded 2026-08-24 against commit 6cc9a01, and verified identical against a
#: clean ``git archive HEAD`` export -- three other workstreams were editing the
#: tree while this was written, so the counts were taken twice and only recorded
#: because both readings agreed.
DEFERRED_BASELINE: Dict[str, int] = {
    "CHANGELOG.md": 28,
    "README.md": 2,
    "bench/splits.toml": 32,
    "docs/ARCHITECTURE.md": 1,
    "docs/DECISIONS.md": 115,
    "docs/DEFINITION-OF-DONE.md": 1,
    "docs/EVALUATION.md": 60,
    "docs/OFFLINE.md": 3,
    "docs/notes/pydantic-cost.md": 70,
    "docs/notes/scoring-objective.md": 3,
    "src/acronymkit/governed/models.py": 1,
}

#: Documents that were outside :data:`SCAN_GLOBS` until the scan set was widened.
#: Their keyword-armed uncited numbers go on the deferred ledger rather than
#: failing the build, because they are figures the gate has never adjudicated
#: rather than regressions -- one of them, ``CHANGELOG.md``'s ``62.40``, matches
#: no measurement at all and has been published in a release note the whole time.
#:
#: This set only shrinks. Emptying it is what "the scan set widened and the debt
#: was paid" looks like, and every entry costs a line in :data:`DEFERRED_BASELINE`
#: that ``--residue`` prints back with the number and its line.
_COVERAGE_GRANDFATHER = frozenset({"CHANGELOG.md", "bench/splits.toml"})

#: A number is a claim when it sits within this many characters of a keyword.
_PROXIMITY = 48

#: A metric unit written immediately after a number, which arms it on its own.
#: This is the rule that reads the number's shape rather than its neighbourhood,
#: and it is what catches ``F₁ > 96 %`` on a line carrying no ASCII keyword.
#:
#: Only whitespace may sit between the number and the unit, which is what keeps
#: it structural: ``4 tools/scripts`` does not match (``s`` is not at a word
#: boundary there) and neither does a number followed by ordinary prose.
_UNIT_AFTER_NUMBER = re.compile(
    r"^[ \t]*(?:"
    r"%"  # 92.32 %, 92.32%
    r"|[µμumn]s\b"  # 62.40 µs / µs / us / ms / ns
    r"|[A-Za-z]*/(?:s|sec|second)s?\b"  # 4,219 docs/s, 96,532 identifiers/second
    r")"
)

#: Keywords that turn a nearby number into a performance or accuracy claim.
#: Matched as words: a keyword welded into a longer identifier does not count.
_KEYWORDS = (
    "f1",
    "precision",
    "recall",
    "r@",
    "docs/s",
    "us/call",
    "\u00b5s/call",
    "throughput",
    "accuracy",
    "exact match",
    "mean absolute error",
)

#: Characters that weld a keyword into a longer word. Underscore is *not* one
#: of them: ``HIGH_PRECISION`` and ``exact_f1`` are how this project names its
#: metrics, and a rule that stopped reading those would drop whole measured
#: table rows off the gate. What must not count is a keyword buried in an
#: unrelated word -- the ``f1`` in ``Lf1chSf``, which is a filename.
_IDENTIFIER_CHARS = frozenset(string.ascii_letters + string.digits)

#: Characters that end a token as a reader sees it. Everything else -- notably
#: ``-``, ``.``, ``,``, ``:``, ``@`` and ``/`` -- *binds*, which is what makes
#: ``D-012``, ``R@25`` and ``9:402`` single tokens rather than stray numbers.
_ATOM_SEPARATORS = frozenset(
    " \t\r\n\f\v"
    "|*()[]{}<>\"'`=!?~^&#\\"
    "\u2013"  # en dash
    "\u2014"  # em dash
    "\u2212"  # minus sign
    "\u00a0"  # no-break space
)

#: Punctuation that may sit at the edge of a number without being part of it.
_EDGE_PUNCTUATION = "%.,;:+-\u2019\u201c\u201d"

#: A token that is a number and nothing else.
_NUMERIC_ATOM = re.compile(r"^\d+(?:,\d{3})*(?:\.\d+)?$")

#: ``# measured: <run-id>`` / ``<!-- measured: <run-id> -->``.
_MARKER = re.compile(r"(?:#|<!--)\s*measured:\s*([\w.\-]+)")

#: An unrendered citation: ``{{claim:<reference>[:<format>]}}``. A format spec
#: may not contain ``=``, ``{`` or ``}``.
_BRACE_PATTERN = r"\{\{claim:(?P<body>[^{}\n]*)\}\}"
_CITATION_BRACE = re.compile(_BRACE_PATTERN)

#: A rendered citation in Markdown: ``83.85<!--claim:<reference>[:<format>]-->``.
#: A reader sees only the number; the reference survives in the comment so the
#: document can be re-rendered when the measurement changes, and so the next
#: check can notice that the number went stale.
_COMMENT_PATTERN = r"(?P<value>[+-]?\d[\d,]*(?:\.\d+)?%?)?<!--\s*claim:(?P<body>[^\n>]*?)\s*-->"
_CITATION_COMMENT = re.compile(_COMMENT_PATTERN)

#: Both forms, for masking. The comment form swallows the number in front of
#: it, which must therefore not also be counted as a bare value-matched claim.
_CITATION_ANY = re.compile(
    _COMMENT_PATTERN.replace("?P<value>", "?P<rendered_value>").replace("?P<body>", "?P<a>")
    + "|"
    + _BRACE_PATTERN.replace("?P<body>", "?P<b>")
)

#: A value the comment form can carry. Anything else (a string field, say)
#: keeps the brace form, because the comment form has to be able to find its
#: own value again by looking left.
_COMMENT_VALUE = re.compile(r"^[+-]?\d[\d,]*(?:\.\d+)?%?$")

#: An inline code span: one or more backticks, no backtick inside, same fence
#: to close. Covers Markdown ``` `x` ``` and reStructuredText ``` ``x`` ```.
_INLINE_CODE = re.compile(r"(`+)[^`\n]*\1")

#: An opening or closing fence for a Markdown code block.
_FENCE = re.compile(r"^(?:`{3,}|~{3,})")


class CitationError(Exception):
    """A ``{{claim:...}}`` reference that does not name a real measurement."""


@dataclass(frozen=True)
class Project:
    """Where the three files this tool needs live.

    Exists so the check can be pointed at a fixture directory in tests rather
    than only at the repository it happens to sit in.

    Attributes:
        root: Checkout being scanned.
        results_path: ``bench/results.json``.
        allowlist_path: ``tools/claims_allowlist.txt``.
        value_baseline: Per-file ceiling on value-matched claims, or ``None``
            for "ratchet off". It is ``None`` for every root except this
            repository's, because :data:`VALUE_MATCHED_BASELINE` is a fact about
            *these documents*. Applying it to a fixture directory would be the
            tool asserting a property of the checkout it lives in against a
            checkout it was handed, which is a different tool.
        deferred_baseline: The same, for uncited numbers the widened coverage
            revealed, against :data:`DEFERRED_BASELINE`. Off (``None``) for the
            same reason and under the same condition, so the ratchets are never
            half-on.
        coverage_grandfather: Which documents entered ``SCAN_GLOBS`` with this
            change, from :data:`_COVERAGE_GRANDFATHER`. Empty for every root but
            this one, and for the same reason as the baselines: "``CHANGELOG.md``
            was not being read until now" is a fact about *these* documents. Any
            other checkout gets the plain rule, so a fixture can still show a
            changelog figure failing the way it will once the debt is paid.
    """

    root: Path
    results_path: Path
    allowlist_path: Path
    value_baseline: Optional[Dict[str, int]] = None
    deferred_baseline: Optional[Dict[str, int]] = None
    coverage_grandfather: frozenset = frozenset()

    @classmethod
    def at(cls, root: Path) -> Project:
        """Build a project rooted at ``root`` with the conventional layout."""
        root = Path(root).resolve()
        here = root == REPO_ROOT
        return cls(
            root=root,
            results_path=root / "bench" / "results.json",
            allowlist_path=root / "tools" / "claims_allowlist.txt",
            value_baseline=dict(VALUE_MATCHED_BASELINE) if here else None,
            deferred_baseline=dict(DEFERRED_BASELINE) if here else None,
            coverage_grandfather=_COVERAGE_GRANDFATHER if here else frozenset(),
        )


@dataclass(frozen=True)
class Citation:
    """One citation found in a scanned file, rendered or not."""

    path: Path
    line_number: int
    start: int
    end: int
    reference: str
    spec: str
    rendered: Optional[str]
    style: str = "brace"
    text: str = ""

    @property
    def body(self) -> str:
        """``<reference>`` or ``<reference>:<format>``."""
        return f"{self.reference}:{self.spec}" if self.spec else self.reference

    @property
    def raw(self) -> str:
        """The citation exactly as it appears in the file."""
        return self.text

    def with_value(self, value: str, *, markdown: bool) -> str:
        """The citation rewritten to carry ``value``.

        Markdown gets the comment form so a reader sees the number alone; a
        placeholder that survived rendering visibly would make every published
        table unreadable, and deleting the reference instead would make the
        document un-regenerable. Everything else keeps the brace form.
        """
        if markdown and _COMMENT_VALUE.match(value):
            return f"{value}<!--claim:{self.body}-->"
        return "{{claim:" + self.body + "=" + value + "}}"


@dataclass(frozen=True)
class Claim:
    """A claim-shaped number found in prose, with how it is backed.

    Attributes:
        arming: Which rule picked the number up -- ``"keyword"``, ``"unit"``, or
            ``""`` for none, which is the ``unexamined`` case. It is carried
            rather than recomputed because it decides which ratchet the number
            falls under, and a number that two rules could arm belongs to the
            older ledger.
    """

    path: Path
    line_number: int
    text: str
    line: str
    backing: str
    detail: str = ""
    arming: str = ""


#: The backing kinds a :class:`Claim` can carry, in reporting order.
#:
#: ``deferred`` and ``unexamined`` are both "the gate has not verified this",
#: and they are separate because they fail differently. A ``deferred`` number
#: was armed, is capped by :data:`DEFERRED_BASELINE` and cannot grow. An
#: ``unexamined`` number was armed by nothing, is uncapped, and is reported
#: precisely so that "uncapped" is a visible fact rather than a silent one.
BACKINGS = ("marker", "allowlist", "value", "deferred", "unexamined", "unbacked")


# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------
def load_results(project: Optional[Project] = None) -> dict:
    """Load the measured-results file.

    Args:
        project: Which checkout to read. Defaults to the one this file is in.

    Returns:
        The parsed document, or an empty skeleton when it does not exist yet.
    """
    path = project.results_path if project else RESULTS_PATH
    if not path.is_file():
        return {"runs": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_leaves(node: object, prefix: str) -> Iterator[Tuple[str, object]]:
    """Yield ``(dotted path, leaf value)`` for every leaf under ``node``."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _iter_leaves(value, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _iter_leaves(value, f"{prefix}.{index}" if prefix else str(index))
    else:
        yield prefix, node


def build_index(results: dict) -> Dict[str, object]:
    """Flatten ``results["runs"]`` into ``{"<run id>.<field path>": value}``.

    Run ids contain dots and so do nested field paths, so the flattened key is
    simply their concatenation -- which means a plain dictionary lookup is the
    whole of citation resolution. A collision between two different
    ``(run, field)`` pairs would make that lookup ambiguous, so it is an error
    rather than a silent last-one-wins.

    Args:
        results: The parsed ``bench/results.json`` document.

    Returns:
        Leaf path to leaf value.

    Raises:
        CitationError: If two distinct measurements flatten to the same path.
    """
    index: Dict[str, object] = {}
    seen: Dict[str, str] = {}
    for run_id, run in sorted(results.get("runs", {}).items()):
        for field, value in _iter_leaves(run, ""):
            path = f"{run_id}.{field}" if field else run_id
            if path in index and seen.get(path) != run_id:
                raise CitationError(
                    f"two measurements flatten to the same citation path {path!r} "
                    f"(runs {seen.get(path)!r} and {run_id!r}); rename one run id"
                )
            index[path] = value
            seen[path] = run_id
    return index


def render_value(value: object, spec: str = "") -> str:
    """Render a stored measurement the way a document should carry it.

    Args:
        value: The leaf value from ``bench/results.json``.
        spec: An optional :func:`format` spec, e.g. ``",.0f"`` for ``4,219``.

    Returns:
        The text to substitute for the citation.

    Raises:
        CitationError: If the format spec does not apply to the value.
    """
    if not spec:
        return str(value)
    try:
        return format(value, spec)
    except (TypeError, ValueError) as error:
        raise CitationError(f"format spec {spec!r} does not apply to {value!r}: {error}") from error


def resolve(reference: str, index: Dict[str, object]) -> object:
    """Look up a citation reference, or explain precisely why it fails.

    Args:
        reference: A dotted ``<run id>.<field>`` path.
        index: The flattened measurement index from :func:`build_index`.

    Returns:
        The measured value.

    Raises:
        CitationError: If the reference names no measurement. The message
            distinguishes "no such run", "no such field on that run" and
            "that is a group of measurements, not one measurement", because a
            citation that fails should say what to write instead.
    """
    if reference in index:
        return index[reference]

    group_prefix = reference + "."
    children = sorted(path for path in index if path.startswith(group_prefix))
    if children:
        fields = ", ".join(path[len(group_prefix) :] for path in children[:8])
        more = "" if len(children) <= 8 else f", ... ({len(children)} fields)"
        raise CitationError(
            f"{reference!r} names a group of measurements, not one measurement. "
            f"Cite a field: {fields}{more}"
        )

    close = difflib.get_close_matches(reference, index, n=3, cutoff=0.6)
    hint = f" Did you mean: {', '.join(close)}?" if close else ""
    raise CitationError(f"{reference!r} is not in bench/results.json.{hint}")


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------
def load_allowlist(project: Optional[Project] = None) -> Dict[str, str]:
    """Parse the allowlist into ``{number_text: reason}``.

    Format is ``<number>  <reason>`` per line; ``#`` comments and blanks ignored.
    """
    path = project.allowlist_path if project else ALLOWLIST_PATH
    if not path.is_file():
        return {}
    entries: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        number, _, reason = line.partition(" ")
        entries[number.strip()] = reason.strip() or "(no reason given)"
    return entries


# ---------------------------------------------------------------------------
# Prose extraction
# ---------------------------------------------------------------------------
def _blank(text: str) -> str:
    """A same-length blank stand-in for ``text`` that keeps line structure."""
    return "".join("\n" if character == "\n" else " " for character in text)


def _mask_spans(text: str, pattern: re.Pattern[str]) -> str:
    """Blank out every match of ``pattern``, preserving every offset."""
    return pattern.sub(lambda match: _blank(match.group(0)), text)


def _mask_fenced_blocks(text: str) -> str:
    """Blank out Markdown fenced code blocks, fences included."""
    out: List[str] = []
    inside = False
    for line in text.split("\n"):
        if _FENCE.match(line.lstrip()):
            inside = not inside
            out.append(_blank(line))
            continue
        out.append(_blank(line) if inside else line)
    return "\n".join(out)


def _mask_python_code(text: str) -> str:
    """Keep only comments and string literals; blank out executable code.

    A number in running code is a parameter, a default or an arithmetic
    constant. It is never a claim about how well the library performs, and
    treating it as one is how ``max(0.0, min(1.0, precision))`` came to be
    reported as an unbacked accuracy figure.

    Args:
        text: The whole source file.

    Returns:
        Same-length text with non-prose regions replaced by spaces. On a
        tokenisation error the original text is returned unchanged, because
        scanning too much is a false alarm and scanning too little is a hole.
    """
    kept = list(_blank(text))
    starts: List[int] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        starts.append(offset)
        offset += len(line)
    starts.append(offset)

    def absolute(position: Tuple[int, int]) -> int:
        row, column = position
        if row - 1 >= len(starts) - 1:
            return len(text)
        return min(starts[row - 1] + column, len(text))

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):  # pragma: no cover - defensive
        return text
    for item in tokens:
        if item.type not in (tokenize.COMMENT, tokenize.STRING):
            continue
        begin, end = absolute(item.start), absolute(item.end)
        kept[begin:end] = list(text[begin:end])
    return "".join(kept)


def prose_of(text: str, suffix: str) -> str:
    """Blank out everything in ``text`` that is code rather than prose.

    Offsets and line numbers are preserved exactly, so a position in the result
    is a position in the original file.

    Args:
        text: File contents.
        suffix: The file's extension, e.g. ``".md"`` or ``".py"``.

    Returns:
        Same-length text with code regions replaced by spaces.
    """
    masked = _mask_python_code(text) if suffix == ".py" else _mask_fenced_blocks(text)
    return _mask_spans(masked, _INLINE_CODE)


# ---------------------------------------------------------------------------
# Claim detection
# ---------------------------------------------------------------------------
def keyword_positions(line: str) -> List[int]:
    """Offsets of every metric keyword in ``line`` that stands as a word.

    ``precision`` in ``SCORE_PRECISION`` and ``f1`` in ``Lf1chSf`` are parts of
    identifiers, so they do not make their line a performance claim. Every
    occurrence is reported, not only the first: a table row mentions several.
    """
    lowered = line.lower()
    positions: List[int] = []
    for keyword in _KEYWORDS:
        start = 0
        while True:
            found = lowered.find(keyword, start)
            if found < 0:
                break
            start = found + 1
            if found and lowered[found - 1] in _IDENTIFIER_CHARS:
                continue
            end = found + len(keyword)
            if (
                keyword[-1] in _IDENTIFIER_CHARS
                and end < len(lowered)
                and lowered[end] in _IDENTIFIER_CHARS
            ):
                continue
            positions.append(found)
    return sorted(positions)


def _iter_atoms(line: str) -> Iterator[Tuple[int, str]]:
    """Yield ``(offset, token)`` for every token a reader would see as one word."""
    start: Optional[int] = None
    for index, character in enumerate(line):
        if character in _ATOM_SEPARATORS:
            if start is not None:
                yield start, line[start:index]
                start = None
        elif start is None:
            start = index
    if start is not None:
        yield start, line[start:]


def _is_claim_shaped(core: str) -> bool:
    """Whether a bare number is written the way a measurement is written.

    A single digit is a count or an index; ``8.0`` and ``4,219`` and ``25`` are
    the shapes a reported figure takes. This is the original rule, unchanged.
    """
    if "." in core or "," in core:
        return True
    return len(core) >= 2


def iter_claim_numbers(line: str) -> Iterator[Tuple[int, str]]:
    """Yield ``(offset, number_text)`` for every free-standing number in ``line``.

    Free-standing means the number is the whole token: ``D-012``, ``R@25``,
    ``MED1250`` and ``9:402`` yield nothing, because in each of them the digits
    are part of an identifier rather than a quantity. A hyphenated range of
    plain numbers (``86-89``) is the one token deliberately split, since both
    halves really are numbers.
    """
    for offset, atom in _iter_atoms(line):
        core = atom.strip(_EDGE_PUNCTUATION)
        if not core:
            continue
        lead = len(atom) - len(atom.lstrip(_EDGE_PUNCTUATION))
        if _NUMERIC_ATOM.match(core):
            if _is_claim_shaped(core):
                yield offset + lead, core
            continue
        if any(character.isalpha() for character in core) or "-" not in core:
            continue
        parts = core.split("-")
        if len(parts) < 2 or not all(_NUMERIC_ATOM.match(part) for part in parts):
            continue
        cursor = offset + lead
        for part in parts:
            if _is_claim_shaped(part):
                yield cursor, part
            cursor += len(part) + 1


def arming_of(line: str, offset: int, number: str, keywords: Sequence[int]) -> str:
    """Which rule arms the number at ``offset``, or ``""`` for none.

    Args:
        line: The prose-only, citation-masked line the number was found in.
        offset: Where the number starts in ``line``.
        number: The number as written.
        keywords: Keyword offsets from :func:`keyword_positions`, read from the
            *raw* line so a metric named inside a code span still arms.

    Returns:
        ``"keyword"``, ``"unit"``, or ``""``.

    Proximity is checked first and wins ties. That ordering is what keeps the
    value-matched ratchet at exactly the count it was pinned at: every number
    that armed before this rule existed still arms the same way, so turning the
    unit rule on could only add to the new ledger and never move the old one.
    """
    if any(abs(offset - position) <= _PROXIMITY for position in keywords):
        return "keyword"
    if _UNIT_AFTER_NUMBER.match(line[offset + len(number) :]):
        return "unit"
    return ""


def iter_prose_numbers(path: Path) -> Iterator[Tuple[int, str, str, str]]:
    """Yield ``(line_number, number_text, line, arming)`` for every prose number.

    *Every* one -- including the numbers no rule arms, which is the difference
    between this and :func:`scan_file`. The scanner used to drop them where they
    were found, so a figure out of a keyword's reach was not un-backed but
    absent: no total counted it and no report named it.

    Keywords are read from the raw line and numbers from the prose-only view of
    it, so a metric named in a sentence still arms the check while the numbers
    inside code spans and executable code do not become claims.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    raw_lines = text.splitlines()
    prose_lines = prose_of(text, path.suffix).splitlines()
    citation_free = [_mask_spans(line, _CITATION_ANY) for line in prose_lines]
    for number, raw in enumerate(raw_lines, start=1):
        prose = citation_free[number - 1] if number - 1 < len(citation_free) else ""
        if not prose.strip():
            continue
        keywords = keyword_positions(raw)
        for offset, claim in iter_claim_numbers(prose):
            yield number, claim, raw.strip(), arming_of(prose, offset, claim, keywords)


def scan_file(path: Path) -> Iterator[Tuple[int, str, str]]:
    """Yield ``(line_number, number_text, line)`` for every *armed* claim.

    The numbers this drops are not discarded any more: :func:`iter_prose_numbers`
    yields them with an empty arming, and :func:`collect_claims` records them as
    ``unexamined``.
    """
    for line_number, claim, line, arming in iter_prose_numbers(path):
        if arming:
            yield line_number, claim, line


def _citations_in_line(line: str, path: Path, line_number: int) -> Iterator[Citation]:
    """Yield every citation on one already-prose-masked line."""
    for match in _CITATION_COMMENT.finditer(line):
        reference, _, spec = match.group("body").partition(":")
        yield Citation(
            path=path,
            line_number=line_number,
            start=match.start(),
            end=match.end(),
            reference=reference.strip(),
            spec=spec.strip(),
            rendered=match.group("value"),
            style="comment",
            text=match.group(0),
        )
    for match in _CITATION_BRACE.finditer(line):
        head, separator, rendered = match.group("body").partition("=")
        reference, _, spec = head.partition(":")
        yield Citation(
            path=path,
            line_number=line_number,
            start=match.start(),
            end=match.end(),
            reference=reference.strip(),
            spec=spec.strip(),
            rendered=rendered if separator else None,
            style="brace",
            text=match.group(0),
        )


def iter_citations(path: Path) -> Iterator[Citation]:
    """Yield every citation written in prose in ``path``.

    Citations inside fenced code blocks and inline code spans are inert, so the
    syntax can be documented without the documentation failing the build.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    prose = prose_of(text, path.suffix)
    for number, line in enumerate(prose.splitlines(), start=1):
        yield from _citations_in_line(line, path, number)


# ---------------------------------------------------------------------------
# Backing
# ---------------------------------------------------------------------------
def _matches_measurement(text: str, measured: Sequence[float]) -> bool:
    """Whether ``text`` equals a measured value at the precision it is written.

    ``84.78`` matches a stored ``84.7812``; ``84.79`` does not. Integers with
    thousands separators are compared after stripping them.
    """
    cleaned = text.replace(",", "")
    try:
        claimed = float(cleaned)
    except ValueError:
        return False
    decimals = len(cleaned.partition(".")[2])
    for value in measured:
        if round(value, decimals) == claimed:
            return True
        # Percentages are stored as fractions in some runners.
        if round(value * 100, decimals) == claimed:
            return True
    return False


def candidates_for(text: str, index: Dict[str, object]) -> List[Tuple[str, object, bool]]:
    """Every measurement that could have supplied the claim ``text``.

    Args:
        text: The number as written in the document.
        index: The flattened measurement index.

    Returns:
        ``(citation path, stored value, scaled_by_100)`` for each match, where
        ``scaled_by_100`` marks the fraction-stored-as-percentage case.
    """
    cleaned = text.replace(",", "")
    try:
        claimed = float(cleaned)
    except ValueError:
        return []
    decimals = len(cleaned.partition(".")[2])
    found: List[Tuple[str, object, bool]] = []
    for path, value in index.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if round(float(value), decimals) == claimed:
            found.append((path, value, False))
        elif round(float(value) * 100, decimals) == claimed:
            found.append((path, value, True))
    return sorted(found, key=lambda item: item[0])


def classify(candidates: Sequence[Tuple[str, object, bool]]) -> str:
    """Label how well a value-matched claim identifies its own source.

    ``UNIQUE`` -- one measurement has this value, so the backing is effectively
    a citation already. ``REPLICATED`` -- several runs record the same field at
    the same value, so the field is unambiguous but the run is not. ``AMBIGUOUS``
    -- measurements of *different* things share the value, which is the case
    where value matching backs a claim it cannot possibly have verified.
    """
    if not candidates:
        return "UNRESOLVED"
    if len(candidates) == 1:
        return "UNIQUE"
    fields = {path.rsplit(".", 1)[-1] for path, _, _ in candidates}
    return "REPLICATED" if len(fields) == 1 else "AMBIGUOUS"


# ---------------------------------------------------------------------------
# Scanning a project
# ---------------------------------------------------------------------------
def scan_paths(project: Project) -> List[Path]:
    """Every file the check looks at, deduplicated and ordered."""
    paths: List[Path] = []
    for pattern in SCAN_GLOBS:
        paths.extend(sorted(project.root.glob(pattern)))
    return sorted(set(paths))


def absent_targets(project: Project) -> List[str]:
    """Scan globs naming one literal file that is not there.

    A wildcard matching nothing is a directory that happens to be empty; a
    literal path matching nothing is a file the gate was told to read and did
    not. ``bench/splits.toml`` is the live case: it is outside ``MANIFEST.in``,
    so the checker shipped in an sdist scans one document fewer than the one in
    a checkout. That is tolerable and it is not allowed to be quiet, which is
    the same rule the rest of this change is made of.
    """
    missing: List[str] = []
    for pattern in SCAN_GLOBS:
        if any(character in pattern for character in "*?["):
            continue
        if not (project.root / pattern).is_file():
            missing.append(pattern)
    return sorted(missing)


def _relative(path: Path, project: Project) -> str:
    """``path`` as written in a report."""
    try:
        return path.relative_to(project.root).as_posix()
    except ValueError:  # pragma: no cover - defensive
        return str(path)


def collect_citations(
    project: Project, index: Dict[str, object]
) -> Tuple[List[Citation], List[str]]:
    """Resolve every citation, returning the citations and any failures."""
    citations: List[Citation] = []
    problems: List[str] = []
    for path in scan_paths(project):
        for citation in iter_citations(path):
            citations.append(citation)
            where = f"{_relative(path, project)}:{citation.line_number}"
            if not citation.reference:
                problems.append(f"  {where}\n    empty citation: {citation.raw}")
                continue
            try:
                value = resolve(citation.reference, index)
                expected = render_value(value, citation.spec)
            except CitationError as error:
                problems.append(f"  {where}\n    {error}")
                continue
            if citation.rendered is not None and citation.rendered != expected:
                problems.append(
                    f"  {where}\n"
                    f"    stale rendered value: file says {citation.rendered!r}, "
                    f"{citation.reference} is now {expected!r}. "
                    f"Run: python tools/check_claims.py --render"
                )
    return citations, problems


def _outside_value_ledger(project: Project, path: Path, arming: str) -> bool:
    """Whether an uncited bare number belongs to the deferred ledger.

    Two ways in, and both are the same fact -- **the gate's coverage grew, and
    the value-matched budget must not grow with it**:

    * the *unit* rule armed it, so no keyword did and no earlier run of this
      tool ever saw it; or
    * it lives in a file :data:`_COVERAGE_GRANDFATHER` names, which is a file
      that was outside ``SCAN_GLOBS`` until the scan set was widened.

    What is deliberately **not** here: a keyword-armed number in a document the
    gate was already reading. Those keep the classification they have always
    had, including the hard ``unbacked`` failure. A coverage change may reveal
    verdicts; it may not soften one the gate had already reached, and the live
    case proved the point -- ``34,096`` was landing in ``docs/OFFLINE.md`` while
    this was being written, the unmodified gate fails on it, and an earlier draft
    of this function would have turned that red into a grandfathered ledger row.

    When the ratchet is off (any root but this one) only the unit rule applies,
    so a keyword-armed number value-matches exactly as it always did.
    """
    if arming == "unit":
        return True
    return _relative(path, project) in project.coverage_grandfather


def collect_claims(
    project: Project,
    index: Dict[str, object],
    allowlist: Dict[str, str],
) -> List[Claim]:
    """Classify every claim-shaped number in the project."""
    measured = sorted(
        float(value)
        for value in index.values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    )
    run_ids = set(index)
    claims: List[Claim] = []
    for path in scan_paths(project):
        for line_number, number, line, arming in iter_prose_numbers(path):
            if not arming:
                # No rule armed it, so the gate has not looked at it. Recorded
                # rather than dropped, and deliberately *not* value-matched:
                # the residue is mostly years, defaults and rank cutoffs, and
                # value matching would hand every round one of them a
                # "backed" label it cannot have earned.
                claims.append(
                    Claim(
                        path=path,
                        line_number=line_number,
                        text=number,
                        line=line,
                        backing="unexamined",
                        detail="no arming rule reaches this number",
                        arming=arming,
                    )
                )
                continue
            marker = _MARKER.search(line)
            if marker:
                run_id = marker.group(1)
                known = run_id in run_ids or any(
                    known_path.startswith(run_id + ".") for known_path in index
                )
                claims.append(
                    Claim(
                        path=path,
                        line_number=line_number,
                        text=number,
                        line=line,
                        backing="marker" if known else "unbacked",
                        detail=(
                            f"measured: {run_id}"
                            if known
                            else f"marker names unknown run id {run_id!r}"
                        ),
                        arming=arming,
                    )
                )
                continue
            if number in allowlist:
                claims.append(
                    Claim(
                        path=path,
                        line_number=line_number,
                        text=number,
                        line=line,
                        backing="allowlist",
                        detail=allowlist[number],
                        arming=arming,
                    )
                )
                continue
            backed = _matches_measurement(number, measured)
            if _outside_value_ledger(project, path, arming):
                # The value ledger is closed: 71 claims across the 4 files
                # VALUE_MATCHED_BASELINE names, and R1 allows that number to
                # move down and never up. So everything widening the gate's
                # coverage revealed -- a new arming rule, or a document that
                # was never scanned -- lands here instead of being laundered
                # into a budget it predates.
                #
                # It lands here whether or not some measurement equals it.
                # "Equals a measurement" is exactly the property that cannot
                # tell a real figure from a coincidence, and 186 of these do
                # equal one. Capped by DEFERRED_BASELINE, never fatal on its
                # own, and named line by line by --residue.
                claims.append(
                    Claim(
                        path=path,
                        line_number=line_number,
                        text=number,
                        line=line,
                        backing="deferred",
                        detail=(
                            f"{arming}-armed, uncited; "
                            + (
                                "a measurement has this value"
                                if backed
                                else "NO measurement has this value"
                            )
                        ),
                        arming=arming,
                    )
                )
                continue
            claims.append(
                Claim(
                    path=path,
                    line_number=line_number,
                    text=number,
                    line=line,
                    backing="value" if backed else "unbacked",
                    detail="matched by value only" if backed else "no measurement has this value",
                    arming=arming,
                )
            )
    return claims


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_text(text: str, suffix: str, index: Dict[str, object]) -> str:
    """Rewrite every ``{{claim:...}}`` in ``text`` to carry its current value.

    The placeholder survives rendering by design. A generator that consumed its
    own source could not regenerate a document when the numbers changed, which
    is the entire reason for the mode -- and keeping the reference in place is
    what lets the next check run notice that the value went stale.

    Args:
        text: File contents.
        suffix: The file's extension, used to decide what counts as prose.
        index: The flattened measurement index.

    Returns:
        The rewritten text. Unresolvable citations are left untouched; the
        check reports them, so rendering never silently drops one.
    """
    prose = prose_of(text, suffix)
    # The comment form is Markdown's, not "anything that is not Python": now
    # that a `.toml` manifest is scanned, writing `<!--claim:...-->` into it
    # would produce a file no TOML parser accepts. Everything else keeps the
    # brace form, which survives inside a `#` comment or a string value.
    markdown = suffix == ".md"
    edits: List[Tuple[int, int, str]] = []
    offset = 0
    for number, line in enumerate(prose.split("\n"), start=1):
        for citation in _citations_in_line(line, Path("<memory>"), number):
            try:
                value = render_value(resolve(citation.reference, index), citation.spec)
            except CitationError:
                continue
            edits.append(
                (
                    offset + citation.start,
                    offset + citation.end,
                    citation.with_value(value, markdown=markdown),
                )
            )
        offset += len(line) + 1
    if not edits:
        return text
    out: List[str] = []
    cursor = 0
    for start, end, replacement in sorted(edits):
        out.append(text[cursor:start])
        out.append(replacement)
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


def render_project(
    project: Project, index: Dict[str, object], *, write: bool
) -> List[Tuple[Path, str, str]]:
    """Render every scanned file.

    Args:
        project: What to scan.
        index: The flattened measurement index.
        write: Whether to write the result back. ``False`` is the dry run.

    Returns:
        ``(path, before, after)`` for each file whose contents would change.
    """
    changed: List[Tuple[Path, str, str]] = []
    for path in scan_paths(project):
        try:
            before = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):  # pragma: no cover - defensive
            continue
        after = render_text(before, path.suffix, index)
        if after == before:
            continue
        changed.append((path, before, after))
        if write:
            path.write_text(after, encoding="utf-8")
    return changed


def _changed_lines(before: str, after: str) -> List[Tuple[int, str, str]]:
    """Line-by-line differences, for the dry-run report."""
    old = before.splitlines()
    new = after.splitlines()
    out: List[Tuple[int, str, str]] = []
    for number, (was, now) in enumerate(zip(old, new), start=1):
        if was != now:
            out.append((number, was.strip(), now.strip()))
    return out


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def _summarise(claims: Sequence[Claim], cited: int) -> str:
    """The two lines that track the migration, and what is still not checked.

    The second line exists because the first used to be read as a statement
    about the document and was only ever a statement about the armed subset of
    it. A total that omits what it declined to look at reads as complete.
    """
    counts = dict.fromkeys(BACKINGS, 0)
    for claim in claims:
        counts[claim.backing] = counts.get(claim.backing, 0) + 1
    verified = len(claims) - counts["deferred"] - counts["unexamined"] + cited
    return (
        f"claims: {verified} checked | "
        f"cited {cited} | "
        f"value-matched {counts['value']} | "
        f"allowlisted {counts['allowlist']} | "
        f"marker {counts['marker']} | "
        f"unbacked {counts['unbacked']}\n"
        f"not checked: {counts['deferred'] + counts['unexamined']} prose number(s) | "
        f"deferred {counts['deferred']} (visible, capped) | "
        f"unexamined {counts['unexamined']} (no arming rule reaches them) | "
        "python tools/check_claims.py --residue"
    )


def report_residue(project: Project, index: Dict[str, object], claims: Sequence[Claim]) -> None:
    """Print every number the gate surfaced but did not verify.

    This is the report that did not exist, and its absence is the whole defect:
    a figure out of a keyword's reach was not merely un-backed, it was counted
    in no total and named nowhere, so a summary line reading ``unbacked 0`` was
    true of the armed subset and read as true of the document.
    """
    residue = [claim for claim in claims if claim.backing in ("deferred", "unexamined")]
    by_file: Dict[str, List[Claim]] = {}
    for claim in residue:
        by_file.setdefault(_relative(claim.path, project), []).append(claim)

    print("numbers the gate has surfaced but not verified\n")
    for path in sorted(by_file):
        rows = by_file[path]
        deferred = [claim for claim in rows if claim.backing == "deferred"]
        print(f"  {path}  ({len(deferred)} deferred, {len(rows) - len(deferred)} unexamined)")
        for claim in rows:
            if claim.backing != "deferred":
                continue
            resolvable = "" if candidates_for(claim.text, index) else "  NO MEASUREMENT MATCHES"
            print(f"      :{claim.line_number}  {claim.text}{resolvable}")
            print(f"          {claim.line[:100]}")
    orphans = [claim for claim in residue if claim.backing == "deferred"]
    unmatched = [claim for claim in orphans if not candidates_for(claim.text, index)]
    print(
        f"\nresidue summary: deferred {len(orphans)} | "
        f"of those, {len(unmatched)} match no measurement at all | "
        f"unexamined {len(residue) - len(orphans)}"
    )
    print(
        "  deferred    the gate can see it and nothing cites it, and it is here rather than\n"
        "              failing because widening coverage revealed it. Capped per file by\n"
        "              DEFERRED_BASELINE; the cap may be lowered, never raised.\n"
        "  unexamined  no arming rule reaches it. Uncapped, and listed per file above so\n"
        "              that 'uncapped' is a number somebody can read rather than a silence.\n"
        "              Deliberately NOT value-matched: the residue is mostly years, defaults\n"
        "              and rank cutoffs, and every one that would have matched is AMBIGUOUS."
    )


def report_migration(project: Project, index: Dict[str, object], claims: Sequence[Claim]) -> None:
    """Print, for each value-matched claim, which run ids could supply it."""
    buckets: Dict[str, int] = {"UNIQUE": 0, "REPLICATED": 0, "AMBIGUOUS": 0, "UNRESOLVED": 0}
    print("value-matched claims and the measurements that could supply them\n")
    for claim in claims:
        if claim.backing != "value":
            continue
        candidates = candidates_for(claim.text, index)
        verdict = classify(candidates)
        buckets[verdict] = buckets.get(verdict, 0) + 1
        fields = {path.rsplit(".", 1)[-1] for path, _, _ in candidates}
        print(
            f"  {_relative(claim.path, project)}:{claim.line_number}  {claim.text}"
            f"  [{verdict}: {len(candidates)} candidate(s), {len(fields)} distinct field(s)]"
        )
        for path, value, scaled in candidates[:12]:
            note = "  (stored as a fraction)" if scaled else ""
            print(f"      {{{{claim:{path}}}}}  -> {value}{note}")
        if len(candidates) > 12:
            print(f"      ... {len(candidates) - 12} more")
    print(
        "\nmigration summary: "
        f"unique {buckets['UNIQUE']} | "
        f"replicated {buckets['REPLICATED']} | "
        f"ambiguous {buckets['AMBIGUOUS']} | "
        f"unresolved {buckets['UNRESOLVED']}"
    )
    print(
        "  UNIQUE     one measurement has this value; the citation is mechanical.\n"
        "  REPLICATED several runs record the same field at the same value; pick the run.\n"
        "  AMBIGUOUS  unrelated measurements share the value. Value matching cannot have\n"
        "             verified these, and a wrong number here passes the gate today.\n"
        "  UNRESOLVED no measurement has this value (allowlist or marker territory)."
    )


def counts_by_file(project: Project, claims: Sequence[Claim], backing: str) -> Dict[str, int]:
    """How many claims with ``backing`` each scanned file currently carries.

    Keyed by repo-relative POSIX path, so the baselines in the source read the
    same on every platform.
    """
    counts: Dict[str, int] = {}
    for claim in claims:
        if claim.backing != backing:
            continue
        key = _relative(claim.path, project)
        counts[key] = counts.get(key, 0) + 1
    return counts


def value_matched_counts(project: Project, claims: Sequence[Claim]) -> Dict[str, int]:
    """How many value-matched claims each scanned file currently carries."""
    return counts_by_file(project, claims, "value")


def _ratchet_problems(
    counts: Dict[str, int],
    baseline: Dict[str, int],
    *,
    label: str,
    over: str,
    under: str,
) -> List[str]:
    """One message per file whose count does not equal its recorded budget.

    An increase is a new number written without a citation; a decrease is a
    successful migration whose baseline was not lowered in the same commit.
    Both are reported, because a ratchet that only tightens on request is a
    ratchet with slack -- migrate one claim, leave the number alone, and the
    slot is free for the next uncited number.
    """
    problems: List[str] = []
    for path in sorted(set(counts) | set(baseline)):
        actual = counts.get(path, 0)
        allowed = baseline.get(path, 0)
        if actual == allowed:
            continue
        head = f"  {path}\n    {actual} {label}, baseline {allowed}. "
        if actual > allowed:
            problems.append(head + over.format(delta=actual - allowed))
        else:
            problems.append(head + under.format(delta=allowed - actual))
    return problems


def baseline_problems(project: Project, claims: Sequence[Claim]) -> List[str]:
    """Where either ratchet has been broken.

    Args:
        project: The checkout being scanned. When the baselines are ``None``
            the ratchets are off and this returns nothing.
        claims: Every classified claim.

    Returns:
        Messages for the value-matched ledger first, then the deferred one.
    """
    problems: List[str] = []
    if project.value_baseline is not None:
        problems += _ratchet_problems(
            value_matched_counts(project, claims),
            project.value_baseline,
            label="value-matched claim(s)",
            over=(
                "{delta} new number(s) here are backed only by the fact that "
                "some measurement happens to equal them.\n"
                "    Cite the measurement instead: {{{{claim:<run-id>.<field>}}}}. Run\n"
                "      python tools/check_claims.py --migrate\n"
                "    to see which run ids could supply each one."
            ),
            under=(
                "{delta} were migrated or removed -- lower the baseline in\n"
                "    tools/check_claims.py so the slot cannot be silently reused:\n"
                "      python tools/check_claims.py --update-baseline"
            ),
        )
    if project.deferred_baseline is not None:
        problems += _ratchet_problems(
            counts_by_file(project, claims, "deferred"),
            project.deferred_baseline,
            label="uncited bare number(s) on the deferred ledger",
            over=(
                "{delta} new figure(s) here carry a metric unit and cite nothing.\n"
                "    The unit rule armed them; the deferred ledger is a debt register that\n"
                "    was closed at the counts in tools/check_claims.py and may not grow.\n"
                "    Cite them: {{{{claim:<run-id>.<field>}}}}, or run\n"
                "      python tools/check_claims.py --residue\n"
                "    to see which ones match no measurement at all."
            ),
            under=(
                "{delta} were migrated or removed -- lower DEFERRED_BASELINE in\n"
                "    tools/check_claims.py in the same commit:\n"
                "      python tools/check_claims.py --update-baseline"
            ),
        )
    return problems


def _unused_allowlist(allowlist: Dict[str, str], claims: Sequence[Claim]) -> List[str]:
    """Allowlist entries no claim needs any more."""
    used = {claim.text for claim in claims if claim.backing == "allowlist"}
    return sorted(entry for entry in allowlist if entry not in used)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point.

    Returns:
        ``0`` when every claim is backed and every citation resolves, ``1``
        otherwise. ``--render --dry-run`` returns ``1`` when a document is out
        of date, so CI can require rendered docs to be current.
    """
    # --list, --residue and --migrate echo source lines back, and source lines in
    # this repository carry characters no Windows console code page encodes (F with
    # a subscript one, em dashes, arrows). Redirecting any of them to a file died
    # with UnicodeEncodeError and a non-zero exit, which reads exactly like the gate
    # failing. The summary path never hit it because it prints no source lines, so
    # the crash lived in the three reports nobody redirects until they need to.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:  # pragma: no cover - stream-dependent
            reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--list", action="store_true", help="print every claim found")
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="report which run ids could supply each value-matched claim",
    )
    parser.add_argument(
        "--residue",
        action="store_true",
        help="list every number the gate surfaced but did not verify",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="print both ratchet blocks to paste after a migration",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="rewrite {{claim:...}} placeholders to their current values",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="with --render, report what would change without writing",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="checkout to scan (default: the one this script lives in)",
    )
    args = parser.parse_args(argv)

    project = Project.at(args.repo_root)
    results = load_results(project)
    try:
        index = build_index(results)
    except CitationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    allowlist = load_allowlist(project)

    if not index:
        print(
            f"warning: {_relative(project.results_path, project)} holds no measurements.\n"
            "         Run the benchmarks with --save before relying on this check.",
            file=sys.stderr,
        )

    if args.render:
        changed = render_project(project, index, write=not args.dry_run)
        if args.dry_run:
            for path, before, after in changed:
                for number, was, now in _changed_lines(before, after):
                    print(f"  {_relative(path, project)}:{number}")
                    print(f"    - {was[:110]}")
                    print(f"    + {now[:110]}")
            if not changed:
                print("render: up to date, nothing would change")
                return 0
            print(f"\nrender: {len(changed)} file(s) would change; rerun without --dry-run")
            return 1
        print(f"render: rewrote {len(changed)} file(s)")
        return 0

    citations, citation_problems = collect_citations(project, index)
    claims = collect_claims(project, index, allowlist)
    paths = scan_paths(project)

    if args.list:
        for claim in claims:
            print(
                f"  {_relative(claim.path, project)}:{claim.line_number}  "
                f"{claim.text}  [{claim.backing}] {claim.detail}"
            )
        for citation in citations:
            print(
                f"  {_relative(citation.path, project)}:{citation.line_number}  "
                f"{citation.reference}  [cited]"
            )

    if args.migrate:
        report_migration(project, index, claims)
        return 0

    if args.residue:
        report_residue(project, index, claims)
        return 0

    if args.update_baseline:
        print("# Paste into tools/check_claims.py, replacing both blocks.")
        for name, backing in (
            ("VALUE_MATCHED_BASELINE", "value"),
            ("DEFERRED_BASELINE", "deferred"),
        ):
            counts = counts_by_file(project, claims, backing)
            print(f"# {sum(counts.values())} {backing} claim(s) across {len(counts)} file(s).")
            print(f"{name}: Dict[str, int] = {{")
            for path in sorted(counts):
                print(f'    "{path}": {counts[path]},')
            print("}")
        return 0

    missing = absent_targets(project)
    absence = f" ({len(missing)} scan target(s) absent: {', '.join(missing)})" if missing else ""
    print(f"scanned {len(paths)} files, found {len(claims)} claim-shaped numbers{absence}")
    print(_summarise(claims, len(citations)))

    ratchet = baseline_problems(project, claims)
    if project.value_baseline is None or project.deferred_baseline is None:
        print("ratchets: off (not this checkout)")
    else:
        print(
            f"value-matched ratchet: {sum(value_matched_counts(project, claims).values())}"
            f" of {sum(project.value_baseline.values())} budgeted across "
            f"{len(project.value_baseline)} file(s); new claims must cite a run id"
        )
        print(
            f"deferred ratchet: "
            f"{sum(counts_by_file(project, claims, 'deferred').values())}"
            f" of {sum(project.deferred_baseline.values())} budgeted across "
            f"{len(project.deferred_baseline)} file(s); this register may not grow"
        )

    stale = _unused_allowlist(allowlist, claims)
    if stale:
        print(f"note: {len(stale)} allowlist entry(ies) back nothing any more: {', '.join(stale)}")

    unbacked = [claim for claim in claims if claim.backing == "unbacked"]
    if not unbacked and not citation_problems and not ratchet:
        print(
            f"every checked number is backed by {_relative(project.results_path, project)}, "
            "a citation, or the allowlist"
        )
        return 0

    sys.stdout.flush()
    if ratchet:
        print(f"\n{len(ratchet)} file(s) break the value-matched ratchet:\n", file=sys.stderr)
        for problem in ratchet:
            print(problem, file=sys.stderr)
        print(
            "\nValue matching does not verify a claim; it verifies that some measurement\n"
            "somewhere happens to equal it. That is how 'Headroom today is 113,269 bytes'\n"
            "survived two audits after the budget it was derived under had been replaced.\n"
            "New numbers cite their source: {{claim:<run-id>.<field>}}.",
            file=sys.stderr,
        )
    if citation_problems:
        print(f"\n{len(citation_problems)} broken citation(s):\n", file=sys.stderr)
        for problem in citation_problems:
            print(problem, file=sys.stderr)
        print(
            "\nA {{claim:...}} reference must name a run id and field in "
            "bench/results.json.\nList what is available with: "
            "python -c \"import json;print('\\n'.join(json.load(open('bench/results.json'))['runs']))\"",
            file=sys.stderr,
        )

    if unbacked:
        print(f"\n{len(unbacked)} unbacked claim(s):\n", file=sys.stderr)
        for claim in unbacked:
            print(f"  {_relative(claim.path, project)}:{claim.line_number}", file=sys.stderr)
            print(f"    {claim.text!r} in: {claim.line[:110]}", file=sys.stderr)
        print(
            "\nEvery performance or accuracy number must be traceable. Either:\n"
            "  - cite the measurement: {{claim:<run-id>.<field>}} (checked strictly),\n"
            "  - regenerate it into bench/results.json via a benchmark runner --save,\n"
            "  - mark the line 'measured: <run-id>' if it is a recorded historical result,\n"
            "  - or add it to tools/claims_allowlist.txt with a reason (published figures,\n"
            "    illustrative examples, changelog history).",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
