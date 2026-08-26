"""Every appeal to an externally published figure carries a source and a read date.

The defect this exists for
--------------------------
``docs/EVALUATION.md`` claimed for months that this library's reproduction of
``pyab3p`` "lands within half a point of the figures published for Ab3P on
MED1250, which is the strongest available evidence that this harness, reader and
scorer are correct." Three things were wrong with it and only one of them was a
number: the pair it quoted matched neither ``bench/results.json`` nor the table
five lines above it, it was uncited so no ratchet could see it, and **there is no
such citation anywhere in this repository** -- the paper was never read. It stood
through six audits, two adversarial passes and four documentation sweeps, and it
was found by reading the document cold.

``tools/check_claims.py`` could not have caught it. That gate adjudicates numbers
against ``bench/results.json``: it asks *is this figure ours, and is it current*.
An appeal to somebody else's figure is the opposite shape -- the number is
correct nowhere in this repository by construction, and the thing that has to be
checked is the **provenance sentence around it**. Nothing checked that. This
file is the check.

The rule, which is operating rule 4 applied to figures instead of licences
-----------------------------------------------------------------------------
R4 says an external fact carries its source and the date it was read, because a
source with no read date records a conclusion and destroys the evidence for it.
Applied here:

    An appeal to an externally published figure carries, in the same sentence,
    ``<!--external: <source> | read YYYY-MM-DD-->``  (Markdown)
    ``# external: <source> | read YYYY-MM-DD``        (Python, TOML)

    or it is withdrawn.

The marker is deliberately **self-contained** rather than a key into a registry.
A registry buys deduplication and costs an indirection whose only exercised path
would be in tests: no sentence in this tree can currently be marked, because no
external paper in this project has been read on a recorded date. An indirection
with zero live users is the shape this round was sent to delete, so it was not
built.

What arms a sentence, and why both conditions are needed
--------------------------------------------------------
A sentence is checked only when it carries **both**:

1. an **appeal phrase** from :data:`APPEAL_PATTERNS` -- a tight vocabulary of
   constructions that name somebody else's publication, and
2. a **figure** -- a decimal or a percentage, after code spans, fenced blocks and
   ``<!--claim:-->``-cited values have been masked out.

Either condition alone is unusable. Phrase alone fires on "recovers the published
objective exactly" and "no gate on the published curve wins until ``0.15``", both
of which are about this project. Figure alone is every number in the tree. The
conjunction is what makes the rate low enough that nobody turns it off, and the
price is measured here rather than asserted::

    python tools/check_external.py --audit    -- command output, not a benchmark measurement

      armed appeals in SCAN_GLOBS:              3    <- what this gate fires on
      appeal phrase but no figure (discarded): 27    <- what condition 2 throws away
      armed appeals outside SCAN_GLOBS:         0

Two of the three firings are real defects. The third is the retraction that
*quotes* the sentence it withdraws, which this gate cannot tell from an
assertion. **So one false positive in three, against twenty-eight in thirty for
the same vocabulary with condition 2 removed** -- which is the prose linter
somebody disables. Each firing carries its disposition in
:data:`UNCITED_LEDGER` below.

Three honesty notes on those counts, because a gate that quotes its own accuracy
is the last place to be casual about it.

* **The discarded population is not all noise.** ``CHANGELOG.md``'s "The
  published Schwartz & Hearst range is ``~86-89 % F1 on Ab3P``" is a real
  uncited appeal whose figure is code-spanned, so condition 2 drops at least one
  true positive along with the twenty-seven.
* **The second number moves with the documents, and it moved three times inside
  the round that measured it** -- 24, then 25, then 27, as this round's own
  records were written. It is command output under a printed command for exactly
  that reason, and quoting it into prose elsewhere would go stale the way the
  sentence this gate exists for went stale.
* **The first number is the one to attack.** Three firings is a small enough
  denominator that one reclassification moves the rate by a third, and the
  reclassification is a judgement -- whether a retraction quoting its own
  withdrawn claim is a false positive -- not a measurement.

**This gate is not in ``.github/gates.toml`` yet.** That register is owned
elsewhere and the entry for this check was reported to its owner rather than
written here, so until it lands the only thing running this gate is
``tests/test_check_external.py`` under ``python -m pytest tests``. Saying so is
the point: a gate that believes it runs in CI and does not is the defect
``docs/GATES.md`` exists for.

Masking ``<!--claim:-->`` values is the load-bearing half of condition 2 that is
easy to miss. ``91.37<!--claim:governed_gold...-->`` is one of *our* measurements
with a run id attached; a sentence containing only cited figures is appealing to
this repository, not out of it.

What it cannot see, stated before anybody quotes a coverage number off it
-------------------------------------------------------------------------
* **A figure inside a code span or a fenced block is invisible**, exactly as in
  ``tools/check_claims.py``. D-052 established that fencing silences the claims
  gate and is mechanically indistinguishable from hiding; this gate inherits the
  same hole, deliberately, because the alternative -- arming numbers inside
  backticks -- fires on every configuration value in the tree. ``CHANGELOG.md``
  carries a live example: "The published Schwartz & Hearst range is
  ``~86-89 % F1 on Ab3P``" is a genuine uncited external appeal that this gate
  does not see, because the figure is code-spanned.
* **The appeal vocabulary is a list, so a paraphrase escapes it.** "the authors
  measured 99.9 %" contains no listed phrase. This is the same class of hole
  ``check_claims`` has in its arming vocabulary (D-060: it cannot see a latency
  claim), and it is why ``docs/SECOND-READER.md`` exists.
* **It scans prose, not runners.** :data:`SCAN_GLOBS` is ``check_claims``'s set.
  ``bench/`` and ``tools/`` are outside it; ``--audit`` reports what is there so
  the omission is a number rather than an assumption.

The ledger
----------
:data:`UNCITED_LEDGER` records the appeals already in the tree that this
workstream could not close, keyed by **content digest** rather than by count, so
that removing one appeal and adding a different one is still red. Semantics match
``check_claims``'s deferred register: exact in both directions, absent means
zero, and a file added to :data:`SCAN_GLOBS` tomorrow cites from its first line.
``--ledger`` prints the literal to paste when an entry is genuinely closed.

Usage::

    python tools/check_external.py            # the gate: rc=0 clean, rc=1 otherwise
    python tools/check_external.py --report   # every armed appeal, marked or not
    python tools/check_external.py --audit    # the near misses and the unscanned dirs
    python tools/check_external.py --ledger   # the UNCITED_LEDGER literal for this tree
"""

import argparse
import datetime as _datetime
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

#: The prose this gate adjudicates. Deliberately ``tools/check_claims.py``'s
#: ``SCAN_GLOBS`` and not a superset: the defect was in user-facing prose, the
#: two gates should disagree about a file for a reason somebody wrote down, and
#: a wider net is a higher false-positive rate paid for coverage nobody asked
#: for. ``--audit`` prints what the omitted directories hold.
SCAN_GLOBS: Tuple[str, ...] = (
    "README.md",
    "CHANGELOG.md",
    "docs/*.md",
    "docs/notes/*.md",
    "src/acronymkit/*.py",
    "src/acronymkit/**/*.py",
    "bench/splits.toml",
)

#: Directories held out of :data:`SCAN_GLOBS`, reported by ``--audit`` with the
#: count of armed appeals each one holds. Named so the coverage gap is a
#: measurement rather than an omission nobody looked at.
AUDIT_GLOBS: Tuple[str, ...] = ("bench/*.py", "tools/*.py", "data/LICENSES.md", "CONTRIBUTING.md")

#: This file, which ``--audit`` skips. Its own docstrings quote the defect it
#: was built for, so counting them would make the gate evidence about itself.
_SELF = Path(__file__).resolve()

#: A capitalised word, or an ampersand, that may sit between ``published`` and
#: the noun it qualifies: "published **Schwartz & Hearst** figures". Without
#: this the tightest pattern below misses the live instance in this tree,
#: because an external figure is almost always attributed to a named system.
#:
#: ``(?-i:...)`` and the ``{0,4}`` bound are both load-bearing and both were put
#: there by a false positive. The whole appeal expression is compiled
#: ``IGNORECASE``, which makes a bare ``[A-Z]`` match lowercase as well -- an
#: unbounded run of any words. It fired on "3.65% is published as a lower bound
#: with the strict **figure** beside it", a sentence about this project's own
#: measurement, by eating "as a lower bound with the strict" as an attribution.
_ATTRIBUTION = r"(?:\s+(?-i:[A-Z][\w.'-]*|&|and)){0,4}"

#: Constructions that appeal to somebody else's published measurement.
#:
#: Each entry is ``(name, pattern)`` and the name is what ``--report`` prints, so
#: a firing says which rule fired. The vocabulary is tight on purpose. Every
#: pattern here was written against the tree and checked for what it does *not*
#: match -- "the published curve", "the published objective", "published
#: metadata", "published as 9,370 of 25,210 source lines" and "unpublished for
#: three releases" are all this project talking about itself or about a
#: non-numeric external fact, and none of them matches.
APPEAL_PATTERNS: Tuple[Tuple[str, str], ...] = (
    # "the figures published for Ab3P", "scores published by the authors".
    ("published-for", r"\bpublished\s+(?:for|by)\b"),
    # "the published Schwartz & Hearst figures", "its published official scores".
    (
        "published-figures",
        r"\bpublished" + _ATTRIBUTION + r"\s+(?:figures?|scores?|numbers?|results?|values?"
        r"|ranges?|accuracy|precision|recall|F1|F-?scores?|baselines?|benchmarks?)\b",
    ),
    # "the figures published", "the F1 published".
    (
        "figures-published",
        r"\b(?:figures?|scores?|numbers?|results?|values?|ranges?|accuracy|precision"
        r"|recall|F1|F-?scores?)\s+published\b",
    ),
    # "as published", used to assert agreement with an outside source.
    ("as-published", r"\bas published\b"),
    # "reported in the paper", "reported by the authors".
    (
        "reported-in",
        r"\breported\s+(?:in|by)\s+(?:the\s+)?"
        r"(?:papers?|originals?|authors?|literature|READMEs?|repositor(?:y|ies)|shared task)\b",
    ),
    # "the paper reports", "the authors report".
    (
        "paper-reports",
        r"\b(?:papers?|authors?|literature)(?:'s)?\s+"
        r"(?:reports?|publishes?|published|gives?|quotes?|claims?)\b",
    ),
    # "its official scores" -- a shared task's own published baseline.
    ("official-scores", r"\bofficial\s+(?:scores?|figures?|numbers?|results?|baselines?)\b"),
    # "in the original paper".
    ("in-the-paper", r"\bin the (?:original|published) paper\b"),
    # "literature reports", "literature values".
    ("literature", r"\bliterature\s+(?:reports?|values?)\b"),
    # "quoted from the paper", "quoted against the literature".
    ("quoted-from", r"\bquoted\s+(?:from|against)\s+(?:the\s+)?(?:paper|literature|README)\b"),
)

_APPEAL = re.compile(
    "|".join(f"(?P<{name.replace('-', '_')}>{pattern})" for name, pattern in APPEAL_PATTERNS),
    re.IGNORECASE,
)

#: A figure: a decimal, or an integer carrying a percent sign. A trailing
#: ``(?!\.\d)`` keeps ``0.3.0`` and ``3.9.7`` out -- a version is not a
#: measurement, and version strings are the commonest decimal in this tree.
_FIGURE = re.compile(
    r"(?<![\w.])~?\d+(?:,\d{3})*\.\d+(?!\.?\d)"  # 89.03, 1,221.5
    r"|(?<![\w.])~?\d+(?:,\d{3})*(?:\.\d+)?\s*%"  # 96 %, 86.5%
)

#: ``<!--external: <source> | read YYYY-MM-DD-->`` and its ``#`` form.
_MARKER = re.compile(r"(?:#|<!--)\s*external:\s*(?P<body>[^\n>]*?)\s*(?:-->|$)")

#: The two halves R4 requires, split on the pipe.
_MARKER_BODY = re.compile(r"^(?P<source>.+?)\s*\|\s*read\s+(?P<read_on>\d{4}-\d{2}-\d{2})$")

#: An inline code span: Markdown ``` `x` ``` and reStructuredText ``` ``x`` ```.
#: Same expression ``tools/check_claims.py`` uses, for the same reason.
_INLINE_CODE = re.compile(r"(`+)[^`\n]*\1")

#: An opening or closing fence for a Markdown code block.
_FENCE = re.compile(r"^(?:`{3,}|~{3,})")

#: A rendered claim citation and the value in front of it. Masked out because a
#: number with a run id attached is one of ours: a sentence whose only figures
#: are cited is appealing into ``bench/results.json``, not out of the project.
_CLAIM_CITED = re.compile(r"[+-]?\d[\d,]*(?:\.\d+)?%?<!--\s*claim:[^\n>]*?-->")

#: End of a sentence, for splitting a paragraph into checkable units. Prose here
#: is hard-wrapped near column 100, so a line is the wrong unit: ``CHANGELOG.md``
#: puts "The published" at the end of one line and "Schwartz & Hearst range" at
#: the start of the next, and a line-keyed check reads neither.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'*`(\[])")

#: Appeals already in the tree that this workstream could not close, keyed by the
#: digest of the normalised sentence so that swapping one uncited appeal for
#: another is still red. Exact in both directions: absent means zero, and an
#: entry that stops matching must be deleted in the commit that closes it.
#: ``--ledger`` prints the literal.
#:
#: * ``ca6d9ae7273c`` ``docs/DECISIONS.md`` -- "The published Schwartz & Hearst
#:   figures are ~86-89 % F1 on Ab3P with recall the weak side." A historical
#:   record. D-063 settled that rewriting a D-record to match a later tree is
#:   how a record stops being evidence. DISPOSITION: **permanent**, because the
#:   file is a record and the sentence is what somebody believed on that day.
#: * ``25b06b014e4e`` ``docs/EVALUATION.md`` -- "reproduces its published
#:   official scores to the digit (89.03 / 44.94 / 59.73)", under a bold
#:   **Harness validated.** This is a **live second instance of the defect this
#:   gate was built for**: the same document, the same shape of argument, an
#:   appeal to somebody else's numbers offered as proof that a harness is
#:   correct. Its source half-exists -- ``bench/run_disambiguation.py``'s
#:   ``PUBLISHED_MOST_FREQUENT`` names "README.md of the pinned repository" --
#:   and **no read date was ever recorded anywhere**, so the marker cannot be
#:   written without inventing one. DISPOSITION: **blocked on a decision outside
#:   this workstream's brief** -- cite it with a read date somebody actually
#:   read it on, or withdraw it the way the Ab3P sentence was withdrawn.
#: * ``d8ea35c38e20`` ``docs/EVALUATION.md`` -- the retraction itself, which
#:   quotes the withdrawn sentence in full and therefore carries its figures.
#:   The gate cannot distinguish a claim from a quotation of a claim, and this
#:   is the one false positive on the current tree. DISPOSITION: **permanent**
#:   -- a correction that did not quote what it corrected would be worth less
#:   than the false positive costs.
UNCITED_LEDGER: Dict[str, Tuple[str, ...]] = {
    "docs/DECISIONS.md": ("ca6d9ae7273c",),
    "docs/EVALUATION.md": ("25b06b014e4e", "d8ea35c38e20"),
}


class ExternalError(Exception):
    """A malformed marker, or a scan that could not be performed."""


@dataclass(frozen=True)
class Appeal:
    """One sentence that appeals to an externally published figure."""

    path: str
    line: int
    rule: str
    sentence: str
    figures: Tuple[str, ...]
    marker: Optional[str]

    @property
    def digest(self) -> str:
        """A stable twelve-hex key for the sentence, whitespace-normalised."""
        return digest_of(self.sentence)

    @property
    def marker_problem(self) -> Optional[str]:
        """Why this appeal's marker does not satisfy R4, or ``None``.

        Three states, and the middle one is the one worth having: no marker at
        all is a candidate for the ledger, a *malformed* marker is always a hard
        failure. A marker that names a source and forgets the read date is
        exactly the half-compliance R4 was written against -- and it is what
        ``bench/run_disambiguation.py`` currently carries.
        """
        if self.marker is None:
            return None
        parsed = _MARKER_BODY.match(self.marker)
        if parsed is None:
            return (
                f"external marker {self.marker!r} is not "
                "'<source> | read YYYY-MM-DD'. R4 wants both halves: a source with no "
                "read date records a conclusion and destroys the evidence for it"
            )
        try:
            read_on = _datetime.date.fromisoformat(parsed.group("read_on"))
        except ValueError:
            return f"external marker read date {parsed.group('read_on')!r} is not a real date"
        if read_on > _datetime.date.today():
            return f"external marker read date {read_on.isoformat()} is in the future"
        if not parsed.group("source").strip():
            return "external marker names no source"
        return None


def digest_of(sentence: str) -> str:
    """Twelve hex characters keyed to the sentence's words, not its wrapping.

    Whitespace is collapsed first so that reflowing a paragraph does not move a
    ledger entry; changing a word does.
    """
    normalised = " ".join(sentence.split())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:12]


def _mask(text: str) -> str:
    """Blank out spans this gate must not read figures from, keeping length.

    Length is preserved so that offsets into the masked text still index the
    original -- the sentence a reader is shown is the unmasked one, while the
    figures counted are the unmasked-and-unfenced ones.
    """
    out = text
    for pattern in (_CLAIM_CITED, _INLINE_CODE):
        out = pattern.sub(lambda match: " " * len(match.group(0)), out)
    return out


@dataclass(frozen=True)
class _Paragraph:
    """A run of prose lines, with the file line each character came from."""

    text: str
    masked: str
    lines: Tuple[int, ...]


def paragraphs(text: str) -> List[_Paragraph]:
    """Split a file into prose paragraphs, dropping fenced blocks entirely.

    A fenced block is not prose and D-052 already settled that its contents are
    outside every gate in this repository. Dropping it here rather than masking
    it keeps a fence from joining the paragraphs on either side of it.
    """
    out: List[_Paragraph] = []
    buffer: List[Tuple[int, str]] = []
    in_fence = False

    def flush() -> None:
        if not buffer:
            return
        pieces: List[str] = []
        lines: List[int] = []
        for number, content in buffer:
            if pieces:
                pieces.append(" ")
                lines.append(number)
            pieces.append(content)
            lines.extend([number] * len(content))
        joined = "".join(pieces)
        out.append(_Paragraph(text=joined, masked=_mask(joined), lines=tuple(lines)))
        buffer.clear()

    for number, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line.lstrip()):
            in_fence = not in_fence
            flush()
            continue
        if in_fence:
            continue
        if not line.strip():
            flush()
            continue
        buffer.append((number, line.rstrip()))
    flush()
    return out


def appeals_in(path: Path, relative: str) -> List[Appeal]:
    """Every armed appeal in one file, in document order."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:  # pragma: no cover - unreadable file
        raise ExternalError(f"{relative}: {error}") from error

    found: List[Appeal] = []
    for paragraph in paragraphs(text):
        start = 0
        for sentence in _SENTENCE_SPLIT.split(paragraph.text):
            offset = paragraph.text.index(sentence, start)
            start = offset + len(sentence)
            masked = paragraph.masked[offset : offset + len(sentence)]
            appeal = _APPEAL.search(masked)
            if appeal is None:
                continue
            figures = tuple(match.group(0).strip() for match in _FIGURE.finditer(masked))
            if not figures:
                continue
            marker = _MARKER.search(sentence)
            rule = next(
                (name for name, value in (appeal.groupdict() or {}).items() if value is not None),
                "appeal",
            )
            found.append(
                Appeal(
                    path=relative,
                    line=paragraph.lines[offset] if offset < len(paragraph.lines) else 0,
                    rule=rule.replace("_", "-"),
                    sentence=" ".join(sentence.split()),
                    figures=figures,
                    marker=marker.group("body").strip() if marker else None,
                )
            )
    return found


def scan(root: Path, globs: Sequence[str] = SCAN_GLOBS) -> List[Appeal]:
    """Every armed appeal under ``root``, sorted by file then line."""
    seen: Dict[str, Path] = {}
    for glob in globs:
        for path in sorted(root.glob(glob)):
            if path.is_file() and path.resolve() != _SELF:
                seen.setdefault(path.relative_to(root).as_posix(), path)
    found: List[Appeal] = []
    for relative in sorted(seen):
        found.extend(appeals_in(seen[relative], relative))
    return found


def ledger_literal(found: Sequence[Appeal]) -> Dict[str, Tuple[str, ...]]:
    """What :data:`UNCITED_LEDGER` would have to say about this tree."""
    out: Dict[str, List[str]] = {}
    for appeal in found:
        if appeal.marker is None:
            out.setdefault(appeal.path, []).append(appeal.digest)
    return {path: tuple(sorted(digests)) for path, digests in sorted(out.items())}


def check(root: Path, found: Optional[Sequence[Appeal]] = None) -> List[str]:
    """Problems, one string each. Empty means the tree satisfies the rule.

    Args:
        root: The tree to judge.
        found: A scan already taken. Passed by :func:`main` so the gate reads
            every file **once**: scanning twice and printing a count from the
            second scan let a concurrently-edited tree report a problem count
            and an appeal count that disagreed, which happened during
            construction and is exactly the kind of inconsistency a gate must
            not manufacture.
    """
    found = scan(root) if found is None else found
    problems: List[str] = []

    for appeal in found:
        defect = appeal.marker_problem
        if defect is not None:
            problems.append(f"{appeal.path}:{appeal.line}: {defect}\n    {appeal.sentence[:160]}")

    live = ledger_literal(found)
    for path in sorted(set(live) | set(UNCITED_LEDGER)):
        actual = live.get(path, ())
        expected = UNCITED_LEDGER.get(path, ())
        if actual == expected:
            continue
        if not (root / path).is_file():
            # The ledger is keyed to the repository tree. A ``--root`` pointed
            # at a fixture holds none of those files, and reporting every entry
            # as stale there would make the tool unusable against anything but
            # its own checkout -- which is how a check ends up with two
            # implementations. A file that EXISTS and has lost its entry is
            # still reported, which is the case that matters.
            continue
        added = [d for d in actual if d not in expected]
        removed = [d for d in expected if d not in actual]
        for appeal in found:
            if appeal.path == path and appeal.digest in added:
                problems.append(
                    f"{path}:{appeal.line}: appeals to an externally published figure "
                    f"{', '.join(appeal.figures)} with no source and no read date "
                    f"(rule {appeal.rule}). Add "
                    "'<!--external: <source> | read YYYY-MM-DD-->' to the sentence, or "
                    "withdraw the appeal.\n"
                    f"    {appeal.sentence[:160]}"
                )
        for stale in removed:
            problems.append(
                f"{path}: UNCITED_LEDGER holds {stale} and no such appeal is in the file. "
                "An appeal that was closed lowers the ledger in the same commit -- run "
                "'python tools/check_external.py --ledger' for the literal."
            )
    return problems


def _print_report(found: Sequence[Appeal]) -> None:
    """``--report``: every armed appeal, whether or not it is marked."""
    print(f"{len(found)} armed appeal(s) across {len({a.path for a in found})} file(s)")
    for appeal in found:
        state = "MARKED  " if appeal.marker else "uncited "
        print(f"  {state} {appeal.path}:{appeal.line}  rule={appeal.rule}  {appeal.digest}")
        print(f"           figures: {', '.join(appeal.figures)}")
        print(f"           {appeal.sentence[:150]}")


def _print_audit(root: Path, found: Sequence[Appeal]) -> None:
    """``--audit``: the near misses, so the blind spots carry counts.

    Three numbers, and the first is the one to read: how many sentences carry an
    appeal phrase but no figure. That is the population the second condition
    discards, and it is the measure of how much a phrase-only linter would have
    fired.
    """
    phrase_only = 0
    for glob in SCAN_GLOBS:
        for path in sorted(root.glob(glob)):
            if not path.is_file():
                continue
            for paragraph in paragraphs(path.read_text(encoding="utf-8")):
                for sentence in _SENTENCE_SPLIT.split(paragraph.masked):
                    if _APPEAL.search(sentence) and not _FIGURE.search(sentence):
                        phrase_only += 1
    print(f"armed appeals in SCAN_GLOBS:            {len(found)}")
    print(f"appeal phrase but no figure (discarded): {phrase_only}")
    outside = scan(root, AUDIT_GLOBS)
    print(f"armed appeals outside SCAN_GLOBS:        {len(outside)}  ({', '.join(AUDIT_GLOBS)})")
    for appeal in outside:
        print(f"  {appeal.path}:{appeal.line}  rule={appeal.rule}")
        print(f"      {appeal.sentence[:150]}")


def _print_ledger(found: Sequence[Appeal]) -> None:
    """``--ledger``: the literal to paste into :data:`UNCITED_LEDGER`."""
    print("UNCITED_LEDGER: Dict[str, Tuple[str, ...]] = {")
    for path, digests in ledger_literal(found).items():
        rendered = ", ".join(f'"{digest}"' for digest in digests)
        print(f'    "{path}": ({rendered},),')
    print("}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point.

    Returns:
        ``0`` when every armed appeal is either marked to R4's shape or held in
        :data:`UNCITED_LEDGER` exactly, ``1`` otherwise.
    """
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true", help="the gate (this is the default)")
    parser.add_argument("--report", action="store_true", help="print every armed appeal")
    parser.add_argument("--audit", action="store_true", help="print the near misses and the gaps")
    parser.add_argument("--ledger", action="store_true", help="print the UNCITED_LEDGER literal")
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent, help="tree to scan"
    )
    args = parser.parse_args(argv)

    root = args.root
    if args.report or args.audit or args.ledger:
        found = scan(root)
        if args.report:
            _print_report(found)
        if args.audit:
            _print_audit(root, found)
        if args.ledger:
            _print_ledger(found)
        return 0

    found = scan(root)
    problems = check(root, found)
    print(
        f"external citations: {len(found)} armed appeal(s), "
        f"{sum(len(v) for v in UNCITED_LEDGER.values())} in the ledger, {len(problems)} problem(s)"
    )
    if not problems:
        print(
            "external citation check OK: every appeal to an externally published figure "
            "carries a source and a read date, or is held in UNCITED_LEDGER with a disposition"
        )
        return 0
    print(f"\n{len(problems)} problem(s):\n", file=sys.stderr)
    for problem in problems:
        print(f"  {problem}", file=sys.stderr)
    print(
        "\nR4: an external figure carries its source and the date it was read. A number\n"
        "borrowed from a paper nobody in this repository has read is not evidence of\n"
        "anything -- docs/EVALUATION.md carried exactly that sentence for months, offered\n"
        "as the strongest available proof that the extraction harness was correct.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
