#!/usr/bin/env python3
"""Render every committed figure from ``bench/results.json``, and check them.

Why this exists
---------------
``tools/check_claims.py`` adjudicates every published number in this repository.
Its ``SCAN_GLOBS`` names markdown, Python and one TOML file. **It cannot read an
SVG, a PNG or a ``<title>``.** So the moment a chart with a figure baked into it
lands on a page, that figure is an unchecked claim -- the same shape as the
invented latency figure ``docs/DECISIONS.md`` D-060 records, with better
typography and no gate.

This file is written **before any chart exists**, because after is too late. The
rule it enforces is R16:

    A figure inside an image is an unchecked claim. No figure ships unless a
    committed script regenerates it from ``bench/results.json`` and CI diffs it.

Four properties, and each one is a way a chart otherwise goes wrong:

* **every number on a chart is either a cited leaf of ``bench/results.json`` or
  a recorded arithmetic expression over cited leaves.** :class:`Measurements` is
  the only way to get a number into a drawing and it records every access. A
  figure cannot carry a hand-typed value **because a test reads every one back
  off the canvas**, not because this file makes one impossible. It does not:
  :func:`label` takes arbitrary text, and figure one's subtitle carried the swept
  threshold range as two literals until that test was written.
  ``tests/test_render_figures.py`` extracts every numeric token from every
  ``<text>`` element of every committed figure and refuses any that the
  ``<desc>`` does not cite, against one allowlist of axis ticks declared in the
  test that a new number cannot join without a visible edit.
* **the ``<desc>`` and the alt text are DERIVED from what the drawing actually
  read**, not from a list somebody maintains beside it. You cannot cite a run id
  the chart does not use, and you cannot use a number that does not appear in
  the ``<desc>``. A hand-kept provenance list is the thing that goes stale.
* **``--check`` reports the field that moved, not just that bytes differ.** The
  committed file's own ``<desc>`` block is parsed back and diffed against the
  regenerated one, so a stale figure names the measurement rather than the file.
  A gate whose failure cannot be attributed carries very little information.
* **text that does not fit is an error, not a rendering.** SVG does not wrap, so
  a label one word too long silently runs off the canvas and nobody notices
  until a reader sees it. :meth:`Canvas.paragraph` wraps and refuses a block
  that needs more lines than its caller reserved, and :func:`label` refuses type
  below :data:`MIN_TYPE`.

Citation resolution is imported from ``tools/check_claims.py`` rather than
reimplemented, so a dead run id fails here exactly as a dead citation does in
prose -- one implementation of "that measurement exists", driven by two gates.

Size, and what "2x" means for a vector
--------------------------------------
The layout is written in a coordinate system :data:`CANVAS` units wide, which is
about GitHub's content column. The emitted ``width``/``height`` attributes are
:data:`INTRINSIC_SCALE` times that, with the ``viewBox`` left in layout units --
so the intrinsic size is 2x the column, GitHub fits it back to the column, and
the smallest type on the page lands at :data:`MIN_TYPE` device pixels there. A
raster export at the intrinsic size is 2x for free.

Light and dark from one generator
---------------------------------
GitHub renders both themes and a chart unreadable in one is broken, so every
figure is emitted twice from the same drawing code with the palette swapped.
Nothing in a figure function knows which theme it is drawing.

What this file does NOT do
--------------------------
It does not decide where a figure is *placed*. Nothing here edits ``README.md``
or any other page, and no shipped document links to ``docs/figures/``. That
matters for more than tidiness: it is why this gate is evidence apparatus rather
than a published-numbers gate, and the day a figure is embedded in a shipped
page that rank becomes wrong.

Usage::

    python tools/render_figures.py            # write docs/figures/*
    python tools/render_figures.py --check    # the CI gate
    python tools/render_figures.py --list     # every figure and its citations

Nothing here is imported by the library and nothing here touches the network.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ONE IMPLEMENTATION OF "THAT MEASUREMENT EXISTS", NOT TWO. Citation resolution,
# near-miss suggestions and value rendering all come from the gate that
# adjudicates prose, so a dead run id inside an SVG fails with the same message
# a dead run id in a paragraph does. Imported as a sibling module rather than as
# `tools.check_claims` because `tools/` has no `__init__.py` and mypy refuses a
# file it can reach under two module names. Same idiom as `tools/build_lexicons.py`.
import check_claims  # noqa: E402

FIGURES_DIR = REPO_ROOT / "docs" / "figures"
GENERATOR = "tools/render_figures.py"
SOURCE = "bench/results.json"

#: Emitted per figure, from one drawing pass each.
THEMES: Tuple[str, ...] = ("light", "dark")

#: Layout width in user units. GitHub's content column is about this wide, and a
#: figure whose layout is wider is a figure the reader meets shrunk further than
#: it was designed for.
CANVAS = 880.0

#: The emitted ``width``/``height`` are this multiple of the layout box while the
#: ``viewBox`` stays in layout units. Vector art has no pixels, so "2x" can only
#: mean the intrinsic size, and this is what makes it true.
INTRINSIC_SCALE = 2.0

#: No type smaller than this, in layout units. At the intrinsic size that is
#: twice this many device pixels; fitted back into the content column it is
#: exactly this many. Enforced in :func:`label` rather than asserted in a
#: comment, because every legibility rule anybody has ever written in a comment
#: has been broken by the next person in a hurry.
MIN_TYPE = 12.0

#: One sans for labels, one mono for run ids. Both are stacks of faces already on
#: the machine: a figure that fetched a font would be a network dependency inside
#: a governance artifact and would render differently depending on whether the
#: fetch succeeded.
SANS = "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

#: Advance width of one character as a fraction of the font size, used only for
#: wrapping. Deliberately generous: the face is whatever the reader has, and a
#: layout that only fits in the author's font is a layout that breaks for
#: everybody else. Mono is wider than sans and is measured separately.
CHAR_WIDTH = 0.55
CHAR_WIDTH_MONO = 0.62

#: The ``<desc>`` line that carries one number's provenance. Parsed back out of a
#: committed file by :func:`cited_lines` so ``--check`` can say what moved.
_DESC_CITED = re.compile(r"^\s{4}(?P<key>\S.*?) = (?P<value>.*)$")


class FigureError(Exception):
    """A figure could not be drawn, or does not match what is committed."""


@dataclass(frozen=True)
class Palette:
    """Every colour a figure may use. One accent, and everything else grey.

    The accent marks **the series the project is making a claim about** and
    nothing else. A chart that colours five series five ways has decided all five
    are the point, which is the same as deciding none of them is.
    """

    background: str
    ink: str
    muted: str
    grid: str
    rule: str
    baseline_subset: str
    baseline_flat: str
    accent: str
    band: str
    bar_strong: str
    bar_weak: str
    on_strong: str
    on_accent: str


PALETTES: Dict[str, Palette] = {
    "light": Palette(
        background="#ffffff",
        ink="#161b22",
        muted="#57606a",
        grid="#e4e7eb",
        rule="#8c949d",
        baseline_subset="#6e7781",
        baseline_flat="#24292f",
        accent="#9a4210",
        band="#eef0f2",
        bar_strong="#5a6169",
        bar_weak="#ced3d8",
        on_strong="#ffffff",
        on_accent="#ffffff",
    ),
    "dark": Palette(
        background="#0d1117",
        ink="#e6edf3",
        muted="#9198a1",
        grid="#21262d",
        rule="#6e7681",
        baseline_subset="#9198a1",
        baseline_flat="#e6edf3",
        accent="#f0883e",
        band="#1c222b",
        bar_strong="#8b939d",
        bar_weak="#30363d",
        on_strong="#0d1117",
        on_accent="#0d1117",
    ),
}


# ---------------------------------------------------------------------------
# measurements
# ---------------------------------------------------------------------------
@dataclass
class Measurements:
    """The only way a number reaches a drawing, and it records every one.

    Two kinds of number are allowed on a figure and there is no third:

    ``cited``
        a leaf of ``bench/results.json``, reached through
        ``tools/check_claims.resolve`` -- so a dead run id fails here exactly as
        a dead citation fails in prose, with the same message and the same
        near-miss suggestions.
    ``derived``
        arithmetic over cited leaves, where the **expression and its operands are
        recorded** alongside the result. A remainder is a real number a reader
        needs; an unexplained remainder is a number nobody can check.

    Both land in the ``<desc>``, which is what makes the provenance a function of
    the drawing rather than a list maintained beside it.
    """

    index: Dict[str, object]
    run_ids: Tuple[str, ...]
    cited: Dict[str, str] = field(default_factory=dict)
    derivations: List[Tuple[str, str, Tuple[str, ...]]] = field(default_factory=list)

    def number(self, path: str, spec: str = ".2f") -> float:
        """A numeric leaf, recorded, as a float."""
        value = self._resolve(path)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise FigureError(f"{path!r} is {value!r}, which is not a number")
        self.cited[path] = check_claims.render_value(value, spec)
        return float(value)

    def count(self, path: str) -> int:
        """An integer leaf, recorded, rendered with thousands separators."""
        value = self._resolve(path)
        if not isinstance(value, int) or isinstance(value, bool):
            raise FigureError(f"{path!r} is {value!r}, which is not a whole number")
        self.cited[path] = check_claims.render_value(value, ",")
        return value

    def phrase(self, path: str) -> str:
        """A string leaf, recorded. Corpus roles and conventions live here."""
        value = self._resolve(path)
        if not isinstance(value, str):
            raise FigureError(f"{path!r} is {value!r}, which is not a string")
        self.cited[path] = value
        return value

    def items(self, path: str) -> Tuple[str, ...]:
        """Every element of a list-of-strings leaf, each one recorded separately.

        ``check_claims`` flattens a list into ``<path>.<index>`` leaves, so a
        list is read by probing indices until one is absent. That is what makes
        "seven operating points" a **counted** statement rather than a remembered
        one: the count becomes a derivation over leaves the reader can look up,
        and it moves when the run does.
        """
        elements: List[str] = []
        while f"{path}.{len(elements)}" in self.index:
            elements.append(self.phrase(f"{path}.{len(elements)}"))
        if not elements:
            raise FigureError(f"{path!r} is not a non-empty list of strings")
        return tuple(elements)

    def derive(self, name: str, value: float, spec: str, operands: Sequence[str]) -> float:
        """Record one arithmetic result over cited leaves, with its expression.

        ``operands`` are citation paths that must already have been read. That is
        checked rather than trusted: a derivation naming a leaf the drawing never
        read is a derivation nobody can reproduce.
        """
        for operand in operands:
            if operand not in self.cited:
                raise FigureError(
                    f"derivation {name!r} names {operand!r}, which this figure has not cited. "
                    "A derived number is arithmetic over numbers the reader can see."
                )
        self.derivations.append((name, check_claims.render_value(value, spec), tuple(operands)))
        return value

    def whole(self, name: str, value: int, operands: Sequence[str]) -> int:
        """:meth:`derive` for a count, so no derived integer renders as ``368.0``."""
        return int(self.derive(name, float(value), ",.0f", operands))

    def _resolve(self, path: str) -> object:
        try:
            return check_claims.resolve(path, self.index)
        except check_claims.CitationError as error:
            raise FigureError(str(error)) from error

    def runs_used(self) -> Tuple[str, ...]:
        """Every run id this drawing read from, in citation order.

        The run id is the longest declared run whose name prefixes the citation
        path. Longest rather than first because run ids nest --
        ``monoculture.plod_all.gold.long_form.overlap.class`` sits under no
        shorter run today and nothing stops one appearing tomorrow.
        """
        seen: List[str] = []
        for path in self.cited:
            best = ""
            for run_id in self.run_ids:
                if (path == run_id or path.startswith(run_id + ".")) and len(run_id) > len(best):
                    best = run_id
            if best and best not in seen:
                seen.append(best)
        return tuple(seen)


# ---------------------------------------------------------------------------
# svg primitives
# ---------------------------------------------------------------------------
def esc(body: str) -> str:
    """XML-escape a string bound for element content or an attribute."""
    return (
        body.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def num(value: float) -> str:
    """One float formatter for every coordinate in every figure.

    Determinism is the whole point: ``--check`` byte-diffs, so two runs that
    disagree in the last digit of a coordinate would turn the build red for no
    reason. Trailing zeros are stripped so ``120.0`` and ``120`` cannot both
    occur for the same coordinate.
    """
    body = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if body in ("", "-0") else body


def rect(x: float, y: float, w: float, h: float, fill: str, extra: str = "") -> str:
    """One filled rectangle."""
    return (
        f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" '
        f'fill="{fill}"{(" " + extra) if extra else ""}/>'
    )


def line(x1: float, y1: float, x2: float, y2: float, stroke: str, extra: str = "") -> str:
    """One straight stroke."""
    return (
        f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" '
        f'stroke="{stroke}"{(" " + extra) if extra else ""}/>'
    )


def label(
    x: float,
    y: float,
    body: str,
    fill: str,
    size: float = 13.5,
    anchor: str = "start",
    family: str = SANS,
    weight: str = "400",
    extra: str = "",
) -> str:
    """One line of text, refused below :data:`MIN_TYPE`."""
    if size < MIN_TYPE:
        raise FigureError(
            f"type at {num(size)} units is below the {num(MIN_TYPE)}-unit floor, which is what "
            f"keeps this figure legible once GitHub fits it back into the content column: {body[:50]!r}"
        )
    return (
        f'<text x="{num(x)}" y="{num(y)}" fill="{fill}" font-family="{family}" '
        f'font-size="{num(size)}" font-weight="{weight}" text-anchor="{anchor}"'
        f"{(' ' + extra) if extra else ''}>{esc(body)}</text>"
    )


def polyline(points: Sequence[Tuple[float, float]], stroke: str, extra: str = "") -> str:
    """An unfilled connected path through measured points."""
    joined = " ".join(f"{num(x)},{num(y)}" for x, y in points)
    return (
        f'<polyline points="{joined}" fill="none" stroke="{stroke}"'
        f"{(' ' + extra) if extra else ''}/>"
    )


def dot(x: float, y: float, fill: str, radius: float = 4.0) -> str:
    """A marker at one measured point. Every point on every curve carries one."""
    return f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(radius)}" fill="{fill}"/>'


def measure(body: str, size: float, family: str = SANS) -> float:
    """Estimated rendered width of one line of text, in layout units."""
    per = CHAR_WIDTH_MONO if family == MONO else CHAR_WIDTH
    return len(body) * size * per


def wrap(body: str, size: float, max_width: float, family: str = SANS) -> List[str]:
    """Greedy word wrap against :func:`measure`."""
    lines: List[str] = []
    current = ""
    for word in body.split():
        candidate = f"{current} {word}".strip()
        if current and measure(candidate, size, family) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


# ---------------------------------------------------------------------------
# the canvas
# ---------------------------------------------------------------------------
@dataclass
class Canvas:
    """Elements, a palette and a vertical cursor.

    The cursor exists because the two things that go wrong in a hand-placed SVG
    are both invisible until a human looks: text that overruns the right edge,
    and a block that lands on top of the one above it. Flowing the prose off one
    cursor removes the second, and :meth:`paragraph` refusing to overrun removes
    the first.
    """

    palette: Palette
    width: float = CANVAS
    y: float = 0.0
    elements: List[str] = field(default_factory=list)

    def add(self, *items: str) -> None:
        """Append drawn elements in drawing order."""
        self.elements.extend(items)

    def gap(self, amount: float) -> None:
        """Advance the cursor without drawing."""
        self.y += amount

    def paragraph(
        self,
        x: float,
        body: str,
        fill: str,
        size: float,
        max_width: float,
        *,
        leading: Optional[float] = None,
        weight: str = "400",
        family: str = SANS,
        max_lines: int = 3,
    ) -> None:
        """Wrapped text flowed from the cursor, or an error if it does not fit.

        ``max_lines`` is the caller saying how much room it reserved. A block
        that needs more turns the build red rather than silently colliding with
        whatever is beneath it -- which is the only way a layout defect in a
        generated image gets noticed at all.
        """
        step = leading if leading is not None else size * 1.35
        lines = wrap(body, size, max_width, family)
        if len(lines) > max_lines:
            raise FigureError(
                f"a text block wraps to {len(lines)} line(s) and the layout reserved "
                f"{max_lines}: {body[:70]!r}. Shorten it or reserve more room; SVG does not "
                "wrap, so the overflow would be invisible here and visible to a reader."
            )
        if x + max_width > self.width + 0.5 or x < -0.5:
            raise FigureError(
                f"a text block at x={num(x)} with width {num(max_width)} does not fit a "
                f"{num(self.width)}-unit canvas"
            )
        for row in lines:
            self.add(label(x, self.y, row, fill, size, family=family, weight=weight))
            self.y += step


@dataclass(frozen=True)
class Drawing:
    """What a figure function returns: elements, its alt sentence, its height."""

    elements: List[str]
    headline: str
    height: float


# ---------------------------------------------------------------------------
# figure one -- the refusal curve
# ---------------------------------------------------------------------------
#: The abstention thresholds the run sweeps, spelled as the field names spell
#: them. Order is drawing order and therefore ``<desc>`` order.
_GATES: Tuple[str, ...] = ("0.00", "0.01", "0.02", "0.05", "0.10", "0.15", "0.20")

_CURVE = "disambiguation.sdu21.abstention_curve"
_TRIVIAL = "disambiguation.sdu21.most_frequent"


def refusal_curve(m: Measurements, p: Palette) -> Drawing:
    """Coverage against accuracy-when-answered, with the trivial baseline flat.

    The chart the mandate asked for, plus the line it did not ask for: the
    most-frequent baseline appears **twice**, because there are two of it and
    they say different things. The flat one is that baseline answering
    everything, which is what a caller who never refuses gets for free. The
    moving one is the same baseline restricted to whatever subset the gated
    system chose to answer, which is the fair comparison and is the number the
    run itself computes. Drawing only the flat line would flatter the system on
    the left; drawing only the moving line would hide that the whole corpus is
    available to anybody for nothing.
    """
    left, right = 78.0, 852.0
    plot_height = 268.0
    margin = 28.0
    column = CANVAS - 2 * margin

    c = Canvas(palette=p)

    coverage = [m.number(f"{_CURVE}.gate_{g}_coverage_pct") for g in _GATES]
    answered = [m.number(f"{_CURVE}.gate_{g}_accuracy_when_answered") for g in _GATES]
    subset = [m.number(f"{_CURVE}.gate_{g}_most_frequent_accuracy_same_subset") for g in _GATES]
    flat = m.number(f"{_TRIVIAL}.accuracy")
    instances = m.count(f"{_CURVE}.instances")
    role = m.phrase(f"{_CURVE}.split_role")
    arity_share = m.number(f"{_CURVE}.instances_in_those_arities_pct")
    reference = m.number(f"{_CURVE}.reference_gate")
    stubborn = m.items(f"{_CURVE}.arities_most_frequent_still_wins_at_reference_gate")

    # THE REGION WHERE THE BASELINE WINS, TAKEN FROM MEASURED POINTS AND NOT FROM
    # AN INTERPOLATION. The crossing lies between two sweep points, and naming a
    # crossover coverage would put a number on a chart that no run holds -- which
    # is the class of figure this whole file exists to prevent. So the shaded
    # region starts at the LOWEST measured coverage at which the system is still
    # below the flat baseline, that point included, and the two bracketing
    # measured points are printed instead of the crossing.
    every_point = [f"{_CURVE}.gate_{g}_coverage_pct" for g in _GATES] + [
        f"{_CURVE}.gate_{g}_accuracy_when_answered" for g in _GATES
    ]
    losing = [cov for cov, acc in zip(coverage, answered) if acc < flat]
    winning = [cov for cov, acc in zip(coverage, answered) if acc >= flat]
    band_from = m.derive(
        "lowest measured coverage at which the gated system is still below the flat baseline",
        min(losing) if losing else 0.0,
        ".2f",
        [*every_point, f"{_TRIVIAL}.accuracy"],
    )
    band_to = m.derive(
        "highest measured coverage at which the gated system is at or above the flat baseline",
        max(winning) if winning else 0.0,
        ".2f",
        [*every_point, f"{_TRIVIAL}.accuracy"],
    )

    c.add(rect(0, 0, CANVAS, 10_000, p.background))
    c.y = 44.0
    c.paragraph(
        margin,
        f"Refusing buys accuracy, and at {band_from:.2f} % coverage and above the trivial "
        "baseline beats every bit of it",
        p.ink,
        19,
        column,
        leading=25,
        weight="600",
        max_lines=2,
    )
    c.gap(8)
    c.paragraph(
        margin,
        # THE RANGE IS BUILT FROM `_GATES`, NOT TYPED. Those strings are the
        # field-name fragments every citation on this chart is assembled from, so
        # a sweep that moved would fail to resolve rather than leave this
        # sentence describing the old one. Typed, they were the only two numbers
        # on either figure that no measurement stood behind.
        "SDU@AAAI-21 AD, acronym disambiguation. Each point is one abstention threshold from "
        f"{_GATES[0]} to {_GATES[-1]} over the same {instances:,} instances. "
        f"Split role: {role}.",
        p.muted,
        13.5,
        column,
        leading=18,
        max_lines=2,
    )

    top = c.y + 26.0
    bottom = top + plot_height

    def sx(value: float) -> float:
        return left + (right - left) * (value / 100.0)

    def sy(value: float) -> float:
        return bottom - plot_height * (value / 100.0)

    c.add(rect(sx(band_from), top, sx(100.0) - sx(band_from), plot_height, p.band))
    c.add(
        line(
            sx(band_from),
            top,
            sx(band_from),
            bottom,
            p.rule,
            'stroke-width="1" stroke-dasharray="3 3"',
        )
    )

    # BOTH AXES RUN 0 TO 100 AND BOTH START AT ZERO. Neither is cropped, so no
    # part of this chart needs the loud disclaimer that a truncated axis does.
    for value in (0, 20, 40, 60, 80, 100):
        c.add(line(left, sy(value), right, sy(value), p.grid, 'stroke-width="1"'))
        c.add(label(left - 12, sy(value) + 4.5, str(value), p.muted, 13, anchor="end"))
        c.add(line(sx(value), bottom, sx(value), bottom + 6, p.rule, 'stroke-width="1"'))
        c.add(label(sx(value), bottom + 24, str(value), p.muted, 13, anchor="middle"))
    c.add(line(left, top, left, bottom, p.rule, 'stroke-width="1.25"'))
    c.add(line(left, bottom, right, bottom, p.rule, 'stroke-width="1.25"'))
    c.add(
        label(
            (left + right) / 2,
            bottom + 48,
            "coverage: share of instances answered rather than refused (%)",
            p.ink,
            14,
            anchor="middle",
        )
    )
    c.add(
        label(
            0,
            0,
            "accuracy on the answered subset (%)",
            p.ink,
            14,
            anchor="middle",
            extra=f'transform="translate({num(left - 50)},{num((top + bottom) / 2)}) rotate(-90)"',
        )
    )

    c.add(
        label(
            sx(band_from) + 10,
            top + 22,
            "the trivial baseline wins in here",
            p.ink,
            13.5,
            weight="600",
        )
    )
    c.add(
        label(
            sx(band_from) + 10,
            top + 40,
            f"every measured point from {band_from:.2f} % coverage rightward",
            p.muted,
            12.5,
        )
    )

    c.add(
        line(
            left,
            sy(flat),
            right,
            sy(flat),
            p.baseline_flat,
            'stroke-width="2" stroke-dasharray="7 5"',
        )
    )

    subset_points = [(sx(cov), sy(acc)) for cov, acc in zip(coverage, subset)]
    c.add(polyline(subset_points, p.baseline_subset, 'stroke-width="2"'))
    for x, y in subset_points:
        c.add(dot(x, y, p.baseline_subset, 3.5))

    curve = [(sx(cov), sy(acc)) for cov, acc in zip(coverage, answered)]
    c.add(polyline(curve, p.accent, 'stroke-width="2.75"'))
    for x, y in curve:
        c.add(dot(x, y, p.background, 5.5), dot(x, y, p.accent, 4))
    # BELOW the point rather than beside it: the curve descends into this corner,
    # and at `sy(...) + 5` the stroke ran straight through the text. Caught by
    # looking at the rendered file, which is the only way this class of defect is
    # ever caught.
    c.add(
        label(
            sx(coverage[0]) - 12,
            sy(answered[0]) + 24,
            f"{answered[0]:.2f} % answering everything",
            p.accent,
            13,
            anchor="end",
            weight="600",
        )
    )
    c.add(
        label(
            sx(coverage[-1]) + 10,
            sy(answered[-1]) - 12,
            f"{answered[-1]:.2f} % at {coverage[-1]:.2f} % coverage",
            p.accent,
            13,
            weight="600",
        )
    )

    # THE LEGEND SITS OUTSIDE THE PLOT, AND THAT IS NOT A PREFERENCE. Direct
    # labelling is better where there is room; here there is not. The gated curve
    # crosses the flat baseline a few units from a measured point, so an in-plot
    # label for either one lands on the other.
    c.y = bottom + 74.0
    swatch = margin
    for stroke, dashes, name in (
        (p.accent, "", "acronymkit, gated"),
        (p.baseline_subset, "", "most frequent, same answered subset"),
        (p.baseline_flat, ' stroke-dasharray="7 5"', f"most frequent, everything -- {flat:.2f} %"),
    ):
        c.add(
            line(swatch, c.y - 4, swatch + 26, c.y - 4, stroke, 'stroke-width="2.5"' + dashes),
            label(swatch + 34, c.y, name, p.muted, 12.5),
        )
        swatch += 34 + measure(name, 12.5) + 26
    c.gap(26)
    for note in (
        f"The crossing lies between the measured points at {band_to:.2f} % and "
        f"{band_from:.2f} % coverage. Nothing here interpolates.",
        f"At the reference gate {reference:.2f} the trivial baseline is still at least as "
        f"accurate at candidate-set sizes {' and '.join(stubborn)}, which are "
        f"{arity_share:.2f} % of instances. The pooled crossing does not hold there.",
        "Both baselines are one instrument at two denominators. Every threshold here is fitted "
        "to, or read off, a split declared contaminated, so no value on this chart is evidence "
        "of generalisation.",
    ):
        c.paragraph(margin, note, p.muted, 12.5, column, leading=17, max_lines=2)
        c.gap(5)

    c.gap(12)
    c.paragraph(margin, " * ".join(m.runs_used()), p.muted, 12, column, family=MONO, max_lines=2)

    headline = (
        f"Line chart. Coverage on the x axis from 0 to 100 %, accuracy on the answered subset on "
        f"the y axis from 0 to 100 %. The gated system rises from {answered[0]:.2f} % at "
        f"{coverage[0]:.2f} % coverage to {answered[-1]:.2f} % at {coverage[-1]:.2f} % coverage. "
        f"A flat dashed line at {flat:.2f} % is the most-frequent-sense baseline answering every "
        f"instance; it is above the gated system at every measured point from {band_from:.2f} % "
        f"coverage rightward, and that region is shaded. A second grey line is the same baseline "
        f"restricted to whatever subset was answered, moving from {subset[0]:.2f} % to "
        f"{subset[-1]:.2f} % as coverage falls."
    )
    return Drawing(elements=c.elements, headline=headline, height=math.ceil(c.y + 8.0))


# ---------------------------------------------------------------------------
# figure two -- the monoculture band
# ---------------------------------------------------------------------------
_MONO_RUN = "monoculture.plod_all.gold.long_form.overlap.class"


def monoculture_band(m: Measurements, p: Palette) -> Drawing:
    """PLOD-CW gold long forms: who reaches them, and what nobody offers.

    **The mandate specified this as one stacked bar of three shares and those
    three do not stack.** The reason is in the run: ``unproposed`` is
    ``gold_spans - reached_by_sh_family`` -- unproposed *by the Schwartz & Hearst
    family* -- and ``unproposed_alignable_from_gold_short_form`` is a subset of
    THAT, cutting across the split between what non-S&H proposers add and what
    nothing reaches at all. Inclusion-exclusion puts a floor on how many of the
    alignable spans a non-S&H proposer already reaches, and the figure prints it.

    So this is two bars over one denominator: a stack that really does partition
    the gold, and beneath it the region the family misses, decomposed on a
    different axis, with the overlap stated rather than drawn away.
    """
    margin = 40.0
    left, right = margin, CANVAS - margin
    column = right - left

    c = Canvas(palette=p)

    spans = m.count(f"{_MONO_RUN}.gold_spans")
    sh_pct = m.number(f"{_MONO_RUN}.sh_family_recall_pct")
    sh_n = m.count(f"{_MONO_RUN}.reached_by_sh_family")
    all_pct = m.number(f"{_MONO_RUN}.all_proposers_recall_pct")
    all_n = m.count(f"{_MONO_RUN}.reached_by_all_proposers")
    added_pct = m.number(f"{_MONO_RUN}.unproposed_reached_by_an_independent_proposer_pct_of_gold")
    added_n = m.count(f"{_MONO_RUN}.unproposed_reached_by_an_independent_proposer")
    missed_pct = m.number(f"{_MONO_RUN}.unproposed_pct")
    missed_n = m.count(f"{_MONO_RUN}.unproposed")
    band_pct = m.number(f"{_MONO_RUN}.unproposed_alignable_from_gold_short_form_pct_of_gold")
    band_n = m.count(f"{_MONO_RUN}.unproposed_alignable_from_gold_short_form")
    provenance = m.phrase(f"{_MONO_RUN}.gold_provenance")
    family = m.items(f"{_MONO_RUN}.sh_family")

    members = [f"{_MONO_RUN}.sh_family.{n}" for n in range(len(family))]
    points = m.whole("operating points in the S&H family", len(family), members)
    codebases = m.whole(
        "distinct implementations behind those operating points, taking the text before the "
        "profile separator",
        len({member.split("/")[0] for member in family}),
        members,
    )
    ours = m.whole(
        "operating points that are this library",
        sum(1 for member in family if member.startswith("acronymkit/")),
        members,
    )
    nothing_pct = m.derive(
        "reached by no proposer at all, as a share of gold long forms",
        100.0 - all_pct,
        ".2f",
        [f"{_MONO_RUN}.all_proposers_recall_pct"],
    )
    nothing_n = m.whole(
        "reached by no proposer at all, in spans",
        spans - all_n,
        [f"{_MONO_RUN}.gold_spans", f"{_MONO_RUN}.reached_by_all_proposers"],
    )
    rest_pct = m.derive(
        "missed by the S&H family and NOT cleanly alignable, as a share of gold long forms",
        missed_pct - band_pct,
        ".2f",
        [
            f"{_MONO_RUN}.unproposed_pct",
            f"{_MONO_RUN}.unproposed_alignable_from_gold_short_form_pct_of_gold",
        ],
    )
    overlap_n = m.whole(
        "lower bound on alignable spans a non-S&H proposer already reaches, by "
        "inclusion-exclusion inside the spans the family misses",
        band_n + added_n - missed_n,
        [
            f"{_MONO_RUN}.unproposed_alignable_from_gold_short_form",
            f"{_MONO_RUN}.unproposed_reached_by_an_independent_proposer",
            f"{_MONO_RUN}.unproposed",
        ],
    )

    def sx(pct: float) -> float:
        return left + column * (pct / 100.0)

    c.add(rect(0, 0, CANVAS, 10_000, p.background))
    c.y = 42.0
    c.paragraph(
        margin,
        f"{band_pct:.2f} % of PLOD-CW's gold long forms are pairs no bracket scanner offers",
        p.ink,
        19,
        column,
        leading=25,
        weight="600",
        max_lines=2,
    )
    c.gap(8)
    c.paragraph(
        margin,
        f"{spans:,} gold long-form spans, overlap convention. Gold provenance: {provenance}.",
        p.muted,
        13.5,
        column,
        leading=18,
        max_lines=2,
    )

    bar_y, bar_h = c.y + 22.0, 56.0
    segments = (
        (0.0, sh_pct, p.bar_strong, p.on_strong, sh_n, ("reached by the", "S&H family")),
        (sh_pct, added_pct, p.bar_weak, p.ink, added_n, ("added by non-S&H", "proposers")),
        (all_pct, nothing_pct, p.band, p.ink, nothing_n, ("reached by no", "proposer at all")),
    )
    for start, span, fill, _on, _n, _caption in segments:
        c.add(rect(sx(start), bar_y, sx(start + span) - sx(start), bar_h, fill))
    for start, _span, _fill, _on, _n, _caption in segments[1:]:
        c.add(line(sx(start), bar_y, sx(start), bar_y + bar_h, p.rule, 'stroke-width="1"'))
    c.add(rect(left, bar_y, column, bar_h, "none", f'stroke="{p.rule}" stroke-width="1"'))
    for start, span, _fill, on, count, caption in segments:
        centre = sx(start + span / 2.0)
        c.add(
            label(centre, bar_y + 31, f"{span:.2f} %", on, 16, anchor="middle", weight="600"),
            label(centre, bar_y + 48, f"{count:,} spans", on, 12, anchor="middle", family=MONO),
        )
        for n, part in enumerate(caption):
            c.add(label(centre, bar_y + bar_h + 21 + n * 16, part, p.muted, 12.5, anchor="middle"))

    bracket_y = bar_y + bar_h + 86.0
    c.add(
        line(sx(sh_pct), bracket_y, right, bracket_y, p.rule, 'stroke-width="1.25"'),
        line(sx(sh_pct), bracket_y, sx(sh_pct), bracket_y + 8, p.rule, 'stroke-width="1.25"'),
        line(right, bracket_y, right, bracket_y + 8, p.rule, 'stroke-width="1.25"'),
        label(
            (sx(sh_pct) + right) / 2,
            bracket_y - 9,
            f"the {missed_pct:.2f} % the S&H family misses",
            p.muted,
            12.5,
            anchor="middle",
        ),
    )

    band_y, band_h = bracket_y + 20.0, 46.0
    c.add(
        rect(sx(sh_pct), band_y, sx(sh_pct + band_pct) - sx(sh_pct), band_h, p.accent),
        rect(sx(sh_pct + band_pct), band_y, right - sx(sh_pct + band_pct), band_h, p.bar_weak),
        rect(
            sx(sh_pct),
            band_y,
            right - sx(sh_pct),
            band_h,
            "none",
            f'stroke="{p.rule}" stroke-width="1"',
        ),
        label(
            (sx(sh_pct) + sx(sh_pct + band_pct)) / 2,
            band_y + 21,
            f"{band_pct:.2f} % of all gold -- {band_n:,} spans",
            p.on_accent,
            15,
            anchor="middle",
            weight="600",
        ),
        label(
            (sx(sh_pct) + sx(sh_pct + band_pct)) / 2,
            band_y + 38,
            "pairs no bracket scanner offers",
            p.on_accent,
            13,
            anchor="middle",
            weight="600",
        ),
        label(
            right,
            band_y + band_h + 20,
            f"the other {rest_pct:.2f} % the family misses is not cleanly alignable",
            p.muted,
            12.5,
            anchor="end",
        ),
    )

    c.y = band_y + band_h + 52.0
    c.paragraph(
        margin,
        "That band is not a slice of the bar above, and drawing it as one would be wrong.",
        p.ink,
        13.5,
        column,
        leading=19,
        weight="600",
        max_lines=1,
    )
    c.gap(4)
    for note in (
        f"The {band_n:,} alignable spans sit inside the {missed_n:,} the S&H family misses, which "
        f"span both segments right of {sh_pct:.2f} %. At least {overlap_n:,} of them are already "
        f"reached by a non-S&H proposer: {band_n:,} + {added_n:,} - {missed_n:,}.",
        f"So {sh_pct:.2f} + {added_pct:.2f} + {band_pct:.2f} does not sum to 100 and never could. "
        f"The first two partition the {spans:,} spans together with {nothing_pct:.2f} %; the third "
        "cuts across them.",
        f"{points} operating points across {codebases} implementations make up the S&H family "
        f"here, and {ours} of the {points} are this library at {ours} profiles. The bar measures "
        "one algorithm about as much as it measures a field.",
    ):
        c.paragraph(margin, note, p.muted, 12.5, column, leading=17, max_lines=2)
        c.gap(5)

    c.gap(12)
    c.paragraph(margin, " * ".join(m.runs_used()), p.muted, 12, column, family=MONO, max_lines=2)

    headline = (
        f"Two stacked bars over {spans:,} PLOD-CW gold long-form spans. The upper bar partitions "
        f"them: {sh_pct:.2f} % reached by the Schwartz & Hearst family, {added_pct:.2f} % added by "
        f"non-S&H proposers, {nothing_pct:.2f} % reached by no proposer at all. The lower bar "
        f"decomposes the {missed_pct:.2f} % the family misses on a different axis: {band_pct:.2f} "
        f"% of all gold long forms, {band_n:,} spans, are cleanly alignable with a gold short form "
        f"in the same passage and are highlighted as pairs no bracket scanner offers; the "
        f"remaining {rest_pct:.2f} % are not. The highlighted band cuts across the upper bar "
        f"rather than slicing it, and at least {overlap_n:,} of its spans are already reached by a "
        f"non-S&H proposer."
    )
    return Drawing(elements=c.elements, headline=headline, height=math.ceil(c.y + 8.0))


# ---------------------------------------------------------------------------
# the figure register
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Figure:
    """One chart, drawn once per theme from one function."""

    name: str
    title: str
    draw: Callable[[Measurements, Palette], Drawing]

    def path(self, theme: str) -> Path:
        """Where this figure's theme variant is committed."""
        return FIGURES_DIR / f"{self.name}-{theme}.svg"


FIGURES: Tuple[Figure, ...] = (
    Figure(name="refusal-curve", title="Refusal curve, SDU@AAAI-21 AD", draw=refusal_curve),
    Figure(
        name="monoculture-band",
        title="Monoculture band, PLOD-CW gold long forms",
        draw=monoculture_band,
    ),
)


def _index() -> Tuple[Dict[str, object], Tuple[str, ...]]:
    """The flattened citation index and every declared run id."""
    results = check_claims.load_results()
    return check_claims.build_index(results), tuple(sorted(results.get("runs", {})))


def render(figure: Figure, theme: str) -> Tuple[str, str, Measurements]:
    """Draw one figure in one theme.

    Args:
        figure: The registered figure to draw.
        theme: A key of :data:`PALETTES`.

    Returns:
        ``(svg text, alt text, the measurements the drawing read)``.

    Raises:
        FigureError: If the drawing cites a measurement that does not resolve,
            or does not fit its canvas.
    """
    index, run_ids = _index()
    m = Measurements(index=index, run_ids=run_ids)
    drawing = figure.draw(m, PALETTES[theme])
    runs = m.runs_used()
    if not runs:
        raise FigureError(f"figure {figure.name!r} cites no run at all")
    alt = f"{drawing.headline} Run ids: {', '.join(runs)}."

    desc: List[str] = [drawing.headline, "", "Run ids:"]
    desc.extend(f"    {run_id}" for run_id in runs)
    desc.extend(["", f"Cited from {SOURCE}:"])
    desc.extend(f"    {path} = {value}" for path, value in m.cited.items())
    if m.derivations:
        desc.extend(["", "Derived from those, with the expression named:"])
        for name, value, operands in m.derivations:
            desc.append(f"    {name} = {value}")
            desc.extend(f"        over {operand}" for operand in operands)
    desc.extend(
        [
            "",
            f"Generated by {GENERATOR} from {SOURCE}. Do not edit this file: "
            f"`python {GENERATOR} --check` byte-diffs it, and every number above is a citation "
            "the same resolver that adjudicates prose can look up.",
        ]
    )

    head = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{num(CANVAS * INTRINSIC_SCALE)}" '
        f'height="{num(drawing.height * INTRINSIC_SCALE)}" '
        f'viewBox="0 0 {num(CANVAS)} {num(drawing.height)}" '
        f'role="img" aria-label="{esc(alt)}">',
        f"<title>{esc(figure.title)} ({theme})</title>",
        "<desc>",
    ]
    head.extend(esc(row) for row in desc)
    head.append("</desc>")
    return "\n".join(head + drawing.elements + ["</svg>", ""]), alt, m


def cited_lines(svg: str) -> Dict[str, str]:
    """The ``key = value`` provenance rows out of a rendered figure's ``<desc>``.

    Used only by :func:`check`, and it is what turns "these bytes differ" into
    "this measurement moved". Parsing back the file this tool wrote is not
    round-tripping for its own sake: the committed SVG is the only record of what
    the figure claimed *last* time, so it is the only thing a value diff can be
    taken against.
    """
    start = svg.find("<desc>")
    end = svg.find("</desc>")
    if start < 0 or end < 0:
        return {}
    rows: Dict[str, str] = {}
    for row in svg[start + len("<desc>") : end].splitlines():
        found = _DESC_CITED.match(row)
        if found:
            rows[found.group("key")] = found.group("value")
    return rows


def write(figure: Figure, theme: str) -> Path:
    """Render one figure and put it on disk with LF endings."""
    svg, _, _ = render(figure, theme)
    target = figure.path(theme)
    target.parent.mkdir(parents=True, exist_ok=True)
    # `Path.write_text(newline=...)` is 3.10+ and `requires-python` is >=3.9;
    # that exact call is what the `gates.mypy` probe mutation-tests for. CRLF
    # here would make the byte-diff fail on Windows and pass on a runner, which
    # is the D-058 shape exactly. `.gitattributes` says `* text=auto eol=lf`, so
    # the committed bytes are LF in every checkout.
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(svg)
    return target


def check() -> List[str]:
    """Every way a committed figure disagrees with ``bench/results.json``.

    Returns:
        One line per problem, empty when every figure is exactly what the
        measurements say it should be.
    """
    problems: List[str] = []
    for figure in FIGURES:
        for theme in THEMES:
            target = figure.path(theme)
            relative = target.relative_to(REPO_ROOT).as_posix()
            try:
                svg, _, _ = render(figure, theme)
            except FigureError as error:
                problems.append(
                    f"{relative}: figure {figure.name!r} cannot be drawn from {SOURCE}: {error}"
                )
                continue
            if not target.is_file():
                problems.append(
                    f"{relative}: registered in {GENERATOR} and not committed. "
                    f"Run `python {GENERATOR}`."
                )
                continue
            committed = target.read_bytes()
            if committed == svg.encode("utf-8"):
                continue
            problems.append(
                f"{relative} is STALE: the committed bytes are not what {SOURCE} now renders."
            )
            was = cited_lines(committed.decode("utf-8", errors="replace"))
            now = cited_lines(svg)
            moved = sorted(key for key in set(was) | set(now) if was.get(key) != now.get(key))
            for key in moved:
                problems.append(
                    f"    cited value moved: {key}\n"
                    f"        committed: {was.get(key, '<absent>')}\n"
                    f"        measured:  {now.get(key, '<absent>')}"
                )
            if not moved:
                problems.append(
                    "    no cited value moved, so the difference is in the drawing rather than "
                    f"in the measurements. Re-run `python {GENERATOR}` and commit the result."
                )
    return problems


def describe() -> List[str]:
    """Every figure, its themes, and every measurement it rests on."""
    rows: List[str] = []
    for figure in FIGURES:
        _, alt, m = render(figure, THEMES[0])
        rows.append(f"{figure.name}  ({', '.join(theme + '.svg' for theme in THEMES)})")
        rows.append(f"  runs      {', '.join(m.runs_used())}")
        rows.append(f"  cited     {len(m.cited)} leaf value(s), {len(m.derivations)} derived")
        for path, value in m.cited.items():
            rows.append(f"      {path} = {value}")
        for name, value, _operands in m.derivations:
            rows.append(f"      [derived] {name} = {value}")
        rows.append(f"  alt       {len(alt)} characters")
        rows.append("")
    return rows


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Render, check or list. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        description="Render every committed figure from bench/results.json, and check them."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if any committed figure is not what bench/results.json renders",
    )
    parser.add_argument(
        "--list", action="store_true", help="print every figure and the measurements it cites"
    )
    args = parser.parse_args(argv)

    if args.list:
        for row in describe():
            print(row)
        return 0

    if args.check:
        try:
            problems = check()
        except check_claims.CitationError as error:
            print(f"bench/results.json cannot be indexed: {error}", file=sys.stderr)
            return 1
        if problems:
            print(
                f"{len(FIGURES) * len(THEMES)} figure(s) checked against {SOURCE}; "
                "the following do not match:",
                file=sys.stderr,
            )
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            print(
                "\nA figure is an unchecked claim unless a script regenerates it and CI diffs "
                f"it (R16). Re-run `python {GENERATOR}` and commit what it writes.",
                file=sys.stderr,
            )
            return 1
        print(
            f"figures OK: {len(FIGURES)} figure(s) x {len(THEMES)} theme(s) are byte-identical "
            f"to what {SOURCE} renders, and every run id they cite resolves"
        )
        return 0

    for figure in FIGURES:
        for theme in THEMES:
            print(write(figure, theme).relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
