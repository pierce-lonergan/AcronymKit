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
``bench/results.json``, matched at the precision written. This is how roughly
seventy existing claims are backed and it is kept working deliberately -- a
flag day would be worse -- but it cannot tell a correct claim from a number
that coincidentally equals an unrelated measurement. ``--migrate`` lists which
value-matched claims are ambiguous under that test, and those are exactly the
ones whose backing means nothing. The summary line reports how many claims sit
on each path so the migration can be tracked rather than hoped for.

Two further escapes exist, both narrow:

* a trailing ``# measured: <run-id>`` / ``<!-- measured: <run-id> -->`` marker,
  which now *validates* that the run id exists; and
* ``tools/claims_allowlist.txt``, for figures published by other authors.

What counts as a claim
----------------------
A free-standing number in **prose**, within :data:`_PROXIMITY` characters of a
metric keyword used as a word.

Each of those three conditions removes a class of false positive that this
check used to raise, and none of them is a special case for a character:

* *free-standing* -- the number must be the whole token a reader sees, so the
  ``25`` in ``R@25``, the ``012`` in ``D-012``, the ``1250`` in ``MED1250`` and
  the ``402`` in a ``2008;9:402`` citation are not claims. They are parts of
  identifiers, not numbers in their own right.
* *in prose* -- fenced code blocks, inline code spans and, in Python files,
  everything that is not a comment or a string literal. ``max(0.0, min(1.0,
  precision))`` is code; ``length_penalty = 8.0`` is a default, not a result.
* *keyword used as a word* -- ``f1`` inside ``Lf1chSf`` and ``precision``
  inside ``SCORE_PRECISION`` do not make their line a claim about performance.

Usage::

    python tools/check_claims.py                  # scan and report; the CI gate
    python tools/check_claims.py --list           # show every claim and how it is backed
    python tools/check_claims.py --migrate        # which run ids could supply each value-matched claim
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
SCAN_GLOBS = (
    "README.md",
    "docs/*.md",
    "docs/notes/*.md",
    "src/acronymkit/*.py",
    "src/acronymkit/**/*.py",
)

#: A number is a claim when it sits within this many characters of a keyword.
_PROXIMITY = 48

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
    """

    root: Path
    results_path: Path
    allowlist_path: Path

    @classmethod
    def at(cls, root: Path) -> Project:
        """Build a project rooted at ``root`` with the conventional layout."""
        root = Path(root).resolve()
        return cls(
            root=root,
            results_path=root / "bench" / "results.json",
            allowlist_path=root / "tools" / "claims_allowlist.txt",
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
    """A claim-shaped number found in prose, with how it is backed."""

    path: Path
    line_number: int
    text: str
    line: str
    backing: str
    detail: str = ""


#: The backing kinds a :class:`Claim` can carry, in reporting order.
BACKINGS = ("marker", "allowlist", "value", "unbacked")


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


def scan_file(path: Path) -> Iterator[Tuple[int, str, str]]:
    """Yield ``(line_number, number_text, line)`` for every claim in ``path``.

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
        keywords = keyword_positions(raw)
        if not keywords:
            continue
        prose = citation_free[number - 1] if number - 1 < len(citation_free) else ""
        for offset, claim in iter_claim_numbers(prose):
            if any(abs(offset - position) <= _PROXIMITY for position in keywords):
                yield number, claim, raw.strip()


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
        for line_number, number, line in scan_file(path):
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
                    )
                )
                continue
            backed = _matches_measurement(number, measured)
            claims.append(
                Claim(
                    path=path,
                    line_number=line_number,
                    text=number,
                    line=line,
                    backing="value" if backed else "unbacked",
                    detail="matched by value only" if backed else "no measurement has this value",
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
    markdown = suffix != ".py"
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
    """The one line that tracks the migration off value matching."""
    counts = dict.fromkeys(BACKINGS, 0)
    for claim in claims:
        counts[claim.backing] = counts.get(claim.backing, 0) + 1
    return (
        f"claims: {len(claims) + cited} total | "
        f"cited {cited} | "
        f"value-matched {counts['value']} | "
        f"allowlisted {counts['allowlist']} | "
        f"marker {counts['marker']} | "
        f"unbacked {counts['unbacked']}"
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

    print(f"scanned {len(paths)} files, found {len(claims)} claim-shaped numbers")
    print(_summarise(claims, len(citations)))

    stale = _unused_allowlist(allowlist, claims)
    if stale:
        print(f"note: {len(stale)} allowlist entry(ies) back nothing any more: {', '.join(stale)}")

    unbacked = [claim for claim in claims if claim.backing == "unbacked"]
    if not unbacked and not citation_problems:
        print(
            f"all backed by {_relative(project.results_path, project)}, a citation, or the allowlist"
        )
        return 0

    sys.stdout.flush()
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
