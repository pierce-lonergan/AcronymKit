"""The figure pipeline: a number inside an image is a claim nothing else reads.

Why this file exists
--------------------
``tools/check_claims.py`` adjudicates every published number in this repository
and its ``SCAN_GLOBS`` names markdown, Python and one TOML file. **It cannot read
an SVG.** In the formats it *can* read, the latency hole D-060 found is now
closed -- ``tests/test_claims_gate_coverage.py`` drives that same uncited figure
through the real gate and asserts it **fails** -- but the same module pins four
classes of performance claim the widened vocabulary still cannot see, and none of
the arming rules reads a canvas at all. A chart is that defect with better
typography and a wider blast radius, because a chart is screenshotted and
re-published without its source.

``tools/render_figures.py`` is the answer and this file is the part of the answer
that can fail. What is pinned here, and why each item is here rather than trusted:

* **Every committed figure is byte-identical to what ``bench/results.json``
  renders, in both themes.** That is the gate's own claim; asserted here so that
  a figure hand-edited in a text editor fails in the suite as well as in ``lint``.

* **Rendering twice from an unchanged source gives the same bytes.** A byte-diff
  gate over a non-deterministic generator is a flake generator, and it would be
  discovered by a red build on somebody else's machine rather than here.

* **NO NUMBER REACHES A CANVAS WITHOUT A CITATION.** ``TestNoNumberOnACanvasIsUncited``
  is the heart of R16 and it is the one test in this file that the generator
  cannot substitute for: :class:`~tools.render_figures.Measurements` records every
  number that goes *through* it, and nothing whatever stops a figure function
  passing a typed literal straight to ``label()``. Two did. So every ``<text>``
  element of every committed figure is read back, every numeric token extracted,
  and each one must be a value the ``<desc>`` cites -- against one allowlist of
  axis ticks, declared below, that a new number cannot join without an edit a
  reviewer can see.

* **A stale figure names the measurement that moved.** A gate whose failure says
  only "the bytes differ" tells the next reader nothing about whether the drawing
  or the measurement moved.

* **The gate can fail in the tree it runs in (R11).** ``TestTheGateCanFailWhereItRuns``
  edits the real ``bench/results.json``, runs the real command in a subprocess,
  restores the file and re-asserts the digest. Every other test here drives the
  module in-process, and an in-process demonstration is not a demonstration that
  the *command CI runs* goes red.

* **The register, ``ci.yml`` and this file agree on what is being tested.** The
  gate was registered by a different workstream from the one that wrote the
  script, so the failure marker is a literal in two places; ``ci.yml`` running
  something the register does not describe is the D-058 shape exactly.

Nothing here reaches the network and nothing here writes to ``docs/figures/``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, Iterator, List, Set, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS = REPO_ROOT / "tools"
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
GATES = REPO_ROOT / ".github" / "gates.toml"
RESULTS = REPO_ROOT / "bench" / "results.json"

# THE GUARD, PLACED BEFORE THE LOAD AND NOT ON A MARK.
#
# `pytest.mark.skipif` is consulted at COLLECTION and a module body runs at
# IMPORT, which is earlier. `tools/` ships in the sdist and is no part of an
# installed distribution, so under the `installed-suite` job the load below
# would raise and this file would fail to COLLECT rather than skip. One named
# condition, deliberately: any OTHER error here must still reach the job.
if not (TOOLS / "render_figures.py").is_file():  # pragma: no cover - CI job only
    pytest.skip(
        "tools/ is not part of an installed distribution; these tests belong to a checkout",
        allow_module_level=True,
    )


def _load(name: str) -> ModuleType:
    """Import a ``tools/`` script by path.

    ``tools/`` is a directory of scripts and must not become a package: making it
    importable for a test's convenience would change the shape of the thing under
    test. Same mechanism as ``tests/test_gate_scripts.py``.
    """
    spec = importlib.util.spec_from_file_location(f"_{name}_under_test", TOOLS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


figs = _load("render_figures")

#: ``tomllib`` is 3.11+ and ``requires-python`` is ``>=3.9``; ``tomli`` is not a
#: declared dev dependency, so on 3.9 and 3.10 there is no parser to read the
#: register with. The identical guard, for the identical reason, as
#: ``tests/test_gate_scripts.py`` and ``tests/test_splits_manifest.py`` -- this is
#: the check that broke four matrix cells last round by being omitted.
_NO_PARSER = sys.version_info < (3, 11) and importlib.util.find_spec("tomli") is None

needs_parser = pytest.mark.skipif(_NO_PARSER, reason="tomllib is 3.11+; tomli not installed")
needs_register = pytest.mark.skipif(
    _NO_PARSER or not GATES.is_file(),
    reason="the register needs a TOML parser, and is absent from an installed distribution",
)
needs_workflow = pytest.mark.skipif(
    not CI.is_file(), reason=".github/workflows/ci.yml is absent (an installed distribution)"
)
#: ``MANIFEST.in`` ships ``docs/*.md`` and NOT ``docs/figures/*.svg``, so the
#: committed drawings are absent from an extracted sdist while the generator that
#: makes them is present. The tests that read a committed file skip there; the
#: ones that drive the generator still run, which is the useful half in that
#: environment.
needs_committed = pytest.mark.skipif(
    not figs.FIGURES_DIR.is_dir(), reason="docs/figures/ is not shipped in an sdist"
)

VARIANTS: Tuple[Tuple[object, str], ...] = tuple(
    (figure, theme) for figure in figs.FIGURES for theme in figs.THEMES
)
VARIANT_IDS: Tuple[str, ...] = tuple(f"{f.name}-{t}" for f, t in VARIANTS)  # type: ignore[attr-defined]


def _variants() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(("figure", "theme"), VARIANTS, ids=VARIANT_IDS)


# ---------------------------------------------------------------------------
# reading a drawing back
# ---------------------------------------------------------------------------
_TEXT = re.compile(r"<text\b[^>]*>(?P<body>.*?)</text>", re.DOTALL)

#: A number in prose. The lookbehind drops the digits inside an identifier --
#: ``AAAI-21``, ``sdu21``, ``PLOD-CW`` -- which are names rather than claims, and
#: the same structural exclusion ``tools/check_claims.py`` applies to ``D-012``
#: and ``MED1250``. It is also the first thing to widen if a figure ever carries
#: a number this misses.
_NUMBER = re.compile(r"(?<![\w.,\-])\d+(?:,\d{3})*(?:\.\d+)?(?![\d.])")

#: THE ONLY NUMBERS A FIGURE MAY CARRY THAT NO MEASUREMENT BACKS. Axis ticks on a
#: 0-100 percentage scale, plus the ``100`` in "does not sum to 100", which is
#: arithmetic about the other three and not a measurement of anything. Adding a
#: member is a visible edit to a test, which is the whole mechanism: a figure
#: cannot acquire an unbacked number quietly.
AXIS_TICKS: Tuple[str, ...] = ("0", "20", "40", "60", "80", "100")


def _unescape(body: str) -> str:
    """Undo :func:`tools.render_figures.esc` for one element's text content."""
    for entity, character in (
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&quot;", '"'),
        ("&apos;", "'"),
        ("&amp;", "&"),
    ):
        body = body.replace(entity, character)
    return body


def visible_text(svg: str) -> List[str]:
    """Every ``<text>`` element's content, which is what a reader actually sees.

    The ``<desc>`` is excluded because it is provenance rather than drawing, and
    a check that read its own citations back as evidence would pass on anything.
    """
    end = svg.find("</desc>")
    body = svg[end:] if end >= 0 else svg
    return [_unescape(found.group("body")) for found in _TEXT.finditer(body)]


def numbers_on_canvas(svg: str) -> List[Tuple[str, str]]:
    """``(token, the line it was drawn on)`` for every number a reader can see."""
    found: List[Tuple[str, str]] = []
    for row in visible_text(svg):
        for token in _NUMBER.finditer(row):
            found.append((token.group(0), row))
    return found


def uncited_numbers(svg: str, extra_allowed: Tuple[str, ...] = ()) -> List[Tuple[str, str]]:
    """Every visible number the figure's own ``<desc>`` does not account for."""
    allowed: Set[str] = set(figs.cited_lines(svg).values())
    allowed.update(AXIS_TICKS)
    allowed.update(extra_allowed)
    return [(token, row) for token, row in numbers_on_canvas(svg) if token not in allowed]


def _rendered(figure: object, theme: str) -> str:
    svg, _alt, _m = figs.render(figure, theme)
    return str(svg)


@pytest.fixture(scope="module")
def results_bytes() -> Iterator[bytes]:
    """The real ``bench/results.json``, for the tests that mutate it in place."""
    original = RESULTS.read_bytes()
    try:
        yield original
    finally:
        if RESULTS.read_bytes() != original:  # pragma: no cover - only on a failed restore
            with open(RESULTS, "wb") as handle:
                handle.write(original)


# ---------------------------------------------------------------------------
class TestWhatIsCommitted:
    """The committed drawings against the measurements they claim to come from."""

    @needs_committed
    def test_check_is_green_on_this_tree(self) -> None:
        assert figs.check() == []

    @needs_committed
    @_variants()
    def test_the_committed_bytes_are_what_the_measurements_render(
        self, figure: object, theme: str
    ) -> None:
        committed = figure.path(theme).read_bytes()  # type: ignore[attr-defined]
        assert committed == _rendered(figure, theme).encode("utf-8")

    @needs_committed
    @_variants()
    def test_the_committed_file_has_no_carriage_returns(self, figure: object, theme: str) -> None:
        # CRLF here would byte-diff green on Windows and red on a runner, which
        # is the D-058 shape: a check that cannot fail in one environment and
        # cannot pass in another.
        assert b"\r" not in figure.path(theme).read_bytes()  # type: ignore[attr-defined]

    @_variants()
    def test_rendering_twice_gives_the_same_bytes(self, figure: object, theme: str) -> None:
        # A byte-diff gate over a non-deterministic generator turns red for no
        # reason on somebody else's machine, and the fix arrives as "re-run it".
        assert _rendered(figure, theme) == _rendered(figure, theme)

    @needs_committed
    def test_every_svg_in_the_directory_is_one_the_register_produces(self) -> None:
        # An orphan SVG is exactly the artefact this gate exists to forbid: a
        # drawing nothing regenerates and nothing diffs, sitting in the directory
        # a reader trusts because the other files in it are checked.
        expected = {
            figure.path(theme).name  # type: ignore[attr-defined]
            for figure, theme in VARIANTS
        }
        assert {path.name for path in figs.FIGURES_DIR.glob("*.svg")} == expected

    @needs_committed
    @_variants()
    def test_the_intrinsic_size_is_twice_the_layout_box(self, figure: object, theme: str) -> None:
        svg = figure.path(theme).read_text(encoding="utf-8")  # type: ignore[attr-defined]
        width = re.search(r'\bwidth="([\d.]+)"', svg)
        view = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
        assert width is not None and view is not None
        assert float(view.group(1)) == figs.CANVAS
        assert float(width.group(1)) == figs.CANVAS * figs.INTRINSIC_SCALE


class TestTheProvenanceIsDerived:
    """The ``<desc>`` and the alt text are a function of the drawing, not a list."""

    @_variants()
    def test_the_alt_text_names_every_run_the_drawing_read(
        self, figure: object, theme: str
    ) -> None:
        _svg, alt, m = figs.render(figure, theme)
        assert m.runs_used()
        for run_id in m.runs_used():
            assert run_id in alt

    @_variants()
    def test_the_desc_carries_every_leaf_the_drawing_read(self, figure: object, theme: str) -> None:
        svg, _alt, m = figs.render(figure, theme)
        # `cited_lines` parses the XML-escaped `<desc>`, so a derivation whose
        # name holds an ampersand ("the S&H family") comes back escaped. That is
        # right for `check()`, which diffs escaped against escaped; it is wrong
        # for a caller comparing against the unescaped source, and this is the
        # only place in the tree that does.
        rows = {_unescape(key): _unescape(value) for key, value in figs.cited_lines(svg).items()}
        for path, value in m.cited.items():
            assert rows.get(path) == value, path
        for name, value, _operands in m.derivations:
            assert rows.get(name) == value, name

    @needs_committed
    @_variants()
    def test_every_citation_in_the_committed_desc_still_resolves(
        self, figure: object, theme: str
    ) -> None:
        # THE PROPERTY THE MANDATE ASKED FOR IN THOSE WORDS: a chart whose run id
        # is dead fails the build, exactly as a dead citation does in prose. Run
        # against the COMMITTED bytes rather than a fresh render, because a fresh
        # render is where the paths come from and could not disagree with itself.
        index = figs.check_claims.build_index(figs.check_claims.load_results())
        svg = figure.path(theme).read_text(encoding="utf-8")  # type: ignore[attr-defined]
        paths = [key for key in figs.cited_lines(svg) if " " not in key]
        assert paths, "the committed file carries no citation at all"
        for path in paths:
            figs.check_claims.resolve(path, index)

    def test_both_themes_cite_exactly_the_same_measurements(self) -> None:
        # A theme is a palette. If the two variants disagreed about a number, one
        # of them would be an unchecked claim wearing the other one's evidence.
        for figure in figs.FIGURES:
            per_theme = [figs.render(figure, theme)[2] for theme in figs.THEMES]
            first = per_theme[0]
            for other in per_theme[1:]:
                assert other.cited == first.cited
                assert other.derivations == first.derivations

    def test_a_derivation_may_not_name_a_leaf_the_drawing_never_read(self) -> None:
        m = figs.Measurements(index={"a.b": 1.0}, run_ids=("a",))
        with pytest.raises(figs.FigureError, match="has not cited"):
            m.derive("something", 2.0, ".2f", ["a.b"])

    def test_a_dead_run_id_fails_the_drawing(self) -> None:
        index = figs.check_claims.build_index(figs.check_claims.load_results())
        m = figs.Measurements(index=index, run_ids=())
        with pytest.raises(figs.FigureError):
            m.number("monoculture.nope.gold.long_form.overlap.class.sh_family_recall_pct")

    def test_a_leaf_that_is_not_a_number_is_refused_as_one(self) -> None:
        m = figs.Measurements(index={"a.b": "text"}, run_ids=("a",))
        with pytest.raises(figs.FigureError, match="not a number"):
            m.number("a.b")


class TestNoNumberOnACanvasIsUncited:
    """R16 itself. Every number a reader can see, read back off the drawing.

    The generator records what passes through ``Measurements``. It has no opinion
    about what a figure function types into a label, and until this test existed
    two figures carried numbers no measurement stood behind: figure one's
    subtitle spelled its threshold range ``0.00 to 0.20`` as literals, and the
    same figure published two percentages through the coordinate formatter, which
    strips trailing zeros -- so a crossing at ``20.00`` % would have been drawn
    ``20`` % while the ``<desc>`` said ``20.00``.
    """

    @needs_committed
    @_variants()
    def test_every_number_a_reader_can_see_is_one_the_desc_cites(
        self, figure: object, theme: str
    ) -> None:
        svg = figure.path(theme).read_text(encoding="utf-8")  # type: ignore[attr-defined]
        assert numbers_on_canvas(svg), "a figure with no numbers on it is not being tested"
        assert uncited_numbers(svg, figs._GATES) == []

    @needs_committed
    def test_a_typed_number_would_be_caught(self) -> None:
        # THE NEGATIVE CONTROL. Without it this class asserts only that the tree
        # is currently clean, which is what every check that could not fail has
        # always asserted. The injected sentence is the shape of the one that sat
        # in README.md through a green build on 2026-08-25.
        svg = figs.FIGURES[0].path(figs.THEMES[0]).read_text(encoding="utf-8")
        injected = svg.replace(
            "</svg>",
            '<text x="10" y="10" fill="#000" font-family="x" font-size="13" '
            'font-weight="400" text-anchor="start">median latency 41.20 ms</text></svg>',
        )
        assert [token for token, _row in uncited_numbers(injected, figs._GATES)] == ["41.20"]

    @needs_committed
    def test_every_allowed_literal_is_one_some_figure_actually_draws(self) -> None:
        # An allowlist entry nothing uses is a hole nobody is paying for. This is
        # the direction that rots: a figure changes, an axis goes, and the
        # exemption stays behind covering a number somebody types next year.
        drawn: Set[str] = set()
        for figure, theme in VARIANTS:
            svg = figure.path(theme).read_text(encoding="utf-8")  # type: ignore[attr-defined]
            drawn.update(token for token, _row in numbers_on_canvas(svg))
        assert set(AXIS_TICKS) <= drawn

    @needs_committed
    def test_the_swept_thresholds_on_the_canvas_are_the_ones_the_citations_use(self) -> None:
        # `_GATES` is allowed above because the citation paths on that chart are
        # built out of these exact strings: a sweep that moved would fail to
        # resolve rather than leave the subtitle describing the old one.
        svg = figs.FIGURES[0].path(figs.THEMES[0]).read_text(encoding="utf-8")
        rows = figs.cited_lines(svg)
        for gate in figs._GATES:
            assert f"{figs._CURVE}.gate_{gate}_coverage_pct" in rows, gate

    @needs_committed
    @_variants()
    def test_no_label_is_drawn_below_the_type_floor(self, figure: object, theme: str) -> None:
        svg = figure.path(theme).read_text(encoding="utf-8")  # type: ignore[attr-defined]
        sizes = [float(size) for size in re.findall(r'font-size="([\d.]+)"', svg)]
        assert sizes
        assert min(sizes) >= figs.MIN_TYPE


class TestWhatAStaleFigureSays:
    """A stale figure names the field that moved, or the gate is uninformative."""

    @staticmethod
    def _with_moved_leaf(run_id: str, field: str, value: object) -> Dict[str, object]:
        """``bench/results.json`` with one leaf changed. ``runs`` is a flat map."""
        results = json.loads(RESULTS.read_text(encoding="utf-8"))
        assert field in results["runs"][run_id], (run_id, field)
        results["runs"][run_id][field] = value
        return dict(results)

    @needs_committed
    def test_a_moved_measurement_is_named_with_both_values(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        moved = self._with_moved_leaf("disambiguation.sdu21.most_frequent", "accuracy", 11.11)
        monkeypatch.setattr(figs.check_claims, "load_results", lambda *a, **k: moved)
        problems = "\n".join(figs.check())
        assert "disambiguation.sdu21.most_frequent.accuracy" in problems
        assert "72.84" in problems  # what the committed file says
        assert "11.11" in problems  # what the source now measures
        assert "is STALE" in problems

    @needs_committed
    def test_the_marker_the_register_waits_for_is_one_the_tool_prints(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        moved = self._with_moved_leaf("disambiguation.sdu21.most_frequent", "accuracy", 11.11)
        monkeypatch.setattr(figs.check_claims, "load_results", lambda *a, **k: moved)
        assert figs.main(["--check"]) == 1
        assert "the following do not match:" in capsys.readouterr().err

    def test_a_missing_committed_file_is_reported_as_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Inside the repository rather than in `tmp_path`: `check()` reports each
        # figure by its path relative to the root, so a directory outside the
        # tree makes it raise instead of report. Worth knowing, and not worth
        # guarding -- nothing moves FIGURES_DIR but a test.
        monkeypatch.setattr(figs, "FIGURES_DIR", REPO_ROOT / "docs" / "figures-absent")
        problems = "\n".join(figs.check())
        assert "not committed" in problems

    def test_a_figure_that_cannot_be_drawn_is_reported_as_such(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(figs, "FIGURES", (figs.FIGURES[0],))
        monkeypatch.setattr(figs.check_claims, "load_results", lambda *a, **k: {"runs": {}})
        problems = "\n".join(figs.check())
        assert "cannot be drawn" in problems

    @needs_committed
    def test_the_unmutated_tree_is_the_control(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert figs.main(["--check"]) == 0
        assert "figures OK" in capsys.readouterr().out


class TestTheLayoutCannotOverflowSilently:
    """SVG does not wrap, so a label one word too long is invisible to a diff."""

    @needs_committed
    @_variants()
    def test_no_text_element_is_anchored_outside_the_canvas(
        self, figure: object, theme: str
    ) -> None:
        svg = figure.path(theme).read_text(encoding="utf-8")  # type: ignore[attr-defined]
        for found in re.finditer(r'<text x="(?P<x>-?[\d.]+)"', svg):
            x = float(found.group("x"))
            assert -0.5 <= x <= figs.CANVAS + 0.5, x

    @needs_committed
    @_variants()
    def test_no_start_anchored_line_runs_off_the_right_edge(
        self, figure: object, theme: str
    ) -> None:
        # Only `text-anchor="start"` can be measured this way without knowing the
        # reader's font metrics; `middle` and `end` are placed from a computed
        # centre and their own overflow is what `Canvas.paragraph` refuses. That
        # is a real limit of this test and it is stated rather than papered over.
        svg = figure.path(theme).read_text(encoding="utf-8")  # type: ignore[attr-defined]
        pattern = (
            r'<text x="(?P<x>-?[\d.]+)"[^>]*font-family="(?P<family>[^"]*)"'
            r'[^>]*font-size="(?P<size>[\d.]+)"[^>]*text-anchor="start"[^>]*>(?P<body>[^<]*)<'
        )
        seen = 0
        for found in re.finditer(pattern, svg):
            if "transform" in found.group(0):
                continue
            seen += 1
            width = figs.measure(
                _unescape(found.group("body")),
                float(found.group("size")),
                figs.MONO if found.group("family") == figs.MONO else figs.SANS,
            )
            assert float(found.group("x")) + width <= figs.CANVAS + 0.5, found.group("body")
        assert seen, "no start-anchored text was measured, so this asserted nothing"

    def test_a_block_that_needs_more_lines_than_reserved_is_an_error(self) -> None:
        canvas = figs.Canvas(palette=figs.PALETTES["light"])
        with pytest.raises(figs.FigureError, match="line"):
            canvas.paragraph(0.0, "word " * 200, "#000", 13.0, 400.0, max_lines=1)

    def test_a_block_wider_than_the_canvas_is_an_error(self) -> None:
        canvas = figs.Canvas(palette=figs.PALETTES["light"])
        with pytest.raises(figs.FigureError, match="does not fit"):
            canvas.paragraph(40.0, "short", "#000", 13.0, figs.CANVAS, max_lines=1)

    def test_type_below_the_floor_is_refused(self) -> None:
        with pytest.raises(figs.FigureError, match="floor"):
            figs.label(0.0, 0.0, "small", "#000", figs.MIN_TYPE - 0.5)

    def test_wrapping_keeps_every_word(self) -> None:
        body = "the quick brown fox jumps over the lazy dog " * 6
        assert " ".join(figs.wrap(body, 13.0, 200.0)).split() == body.split()

    def test_a_coordinate_renders_the_same_way_twice(self) -> None:
        assert figs.num(120.0) == figs.num(120.004) == "120"
        assert figs.num(-0.001) == "0"


@needs_workflow
@needs_register
class TestTheRegisterAndCiAgree:
    """The thing CI runs, the thing the register mutates, and this file's subject."""

    def _register(self) -> Dict[str, object]:
        if sys.version_info >= (3, 11):
            import tomllib
        else:  # pragma: no cover - 3.9/3.10 matrix cells only
            import tomli as tomllib  # type: ignore[no-redef]

        with GATES.open("rb") as handle:
            return tomllib.load(handle)

    @needs_parser
    def test_the_register_declares_the_gate_with_a_cost_rank(self) -> None:
        gate = self._register()["gates"]["figures"]  # type: ignore[index]
        assert gate["command"] == "python tools/render_figures.py --check"
        assert isinstance(gate["cost_rank"], int)

    def test_ci_runs_the_generator_in_check_mode(self) -> None:
        assert "python tools/render_figures.py --check" in CI.read_text(encoding="utf-8")

    @needs_parser
    @needs_committed
    def test_the_registered_mutation_edits_a_file_that_exists(self) -> None:
        # `needs_committed` BECAUSE THIS FAILED IN THE ONE ENVIRONMENT NOBODY
        # RUNS LOCALLY. The register's mutation edits a committed SVG and
        # `MANIFEST.in` ships `docs/*.md` only, so in an extracted sdist this
        # asserted the absence of a file the sdist was never given -- red in the
        # `build` job's extracted-tree step and green everywhere it was written.
        # Found by renaming `docs/figures/` and re-running, which is the only way
        # this class is ever found (D-058).
        # A mutation whose target moved is a mutation that cannot fire, and the
        # register would go on reporting a demonstrable gate.
        gate = self._register()["gates"]["figures"]  # type: ignore[index]
        edits = gate["mutation"]["edits"]  # type: ignore[index]
        assert edits
        for edit in edits:
            target = REPO_ROOT / str(edit["file"])
            assert target.is_file(), edit["file"]
            assert str(edit["find"]) in target.read_text(encoding="utf-8"), edit


class TestTheGateCanFailWhereItRuns:
    """R11: the command CI runs, mutated in the real tree, restored and verified.

    Every other test in this file drives the module in-process. That is not a
    demonstration that ``python tools/render_figures.py --check`` goes red -- it
    is a demonstration that a function does, which is the distinction D-058 was
    written about.
    """

    @needs_committed
    def test_moving_a_measurement_turns_the_real_command_red(self, results_bytes: bytes) -> None:
        before = hashlib.md5(results_bytes).hexdigest()
        results = json.loads(results_bytes.decode("utf-8"))
        assert results["runs"]["disambiguation.sdu21.most_frequent"]["accuracy"] == 72.84
        results["runs"]["disambiguation.sdu21.most_frequent"]["accuracy"] = 11.11
        moved = json.dumps(results, indent=2).encode("utf-8")

        control = self._run()
        assert control.returncode == 0, control.stderr

        try:
            with open(RESULTS, "wb") as handle:
                handle.write(moved)
            mutated = self._run()
        finally:
            with open(RESULTS, "wb") as handle:
                handle.write(results_bytes)

        assert mutated.returncode == 1
        assert "the following do not match:" in mutated.stderr
        assert "disambiguation.sdu21.most_frequent.accuracy" in mutated.stderr

        restored = self._run()
        assert restored.returncode == 0, restored.stderr
        assert hashlib.md5(RESULTS.read_bytes()).hexdigest() == before

    @staticmethod
    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(TOOLS / "render_figures.py"), "--check"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            errors="replace",
        )
