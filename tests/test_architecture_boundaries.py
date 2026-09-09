"""The package was split at the lexer contract seam. This is what holds it split.

What the seam is
----------------
``acronymkit`` contains two tokenizers whose contracts collide. The prose
tokenizer treats punctuation as a clause boundary, leans on whitespace, pulls
parentheticals out of running morphology and NFKC-normalises what is left. The
identifier tokenizer operates on rigid boundaries, treats ``#``, ``%``, ``_``,
``:`` and ``/`` as *semantic* tokens, and may not lose a character. Each
destroys the other's input, measured as character loss on ``14.6560`` % of
distinct Socrata captions and ``36.0072`` % of distinct SEC XBRL labels. That is
a package boundary rather than a setting:

* :mod:`acronymkit.core` -- conformal risk arithmetic, the exception hierarchy,
  immutable span coordinates. **A leaf**: it imports from neither sibling.
* :mod:`acronymkit.nlp` -- chunking, candidate extraction, parenthetical
  matching, document-scope propagation.
* :mod:`acronymkit.catalog` -- identifier tokenisation, symbol handling, casing
  decomposition, ``to_physical_name``, dictionary conformance.

``catalog`` never imports ``nlp``. ``nlp`` never imports ``catalog``. ``core``
imports neither.

Why an AST walk and not a grep
------------------------------
Five shapes write the same forbidden edge. The AST walker finds all five. A grep
for ``from acronymkit.catalog`` finds **three of the five and misses two** --
``import acronymkit.catalog as _c`` and
``importlib.import_module("acronymkit.catalog.expansion")``.

**That is a smaller number than the brief this was built from claimed, and it is
the measured one.** The brief said the grep misses "``import ... as x``, a
deferred import inside a function, and ``importlib``", which counts the deferred
import as a miss. It is not: a deferred import is still spelled
``from acronymkit.catalog.tokenizer import split_identifier``, so the grep sees
the text. What the grep cannot see is that it is *deferred* -- and the same goes
for the ``TYPE_CHECKING`` shape, which the grep also finds textually. So the
grep's real deficit is two shapes it cannot see at all plus two it can see and
cannot classify, and :func:`TestTheInstrument.test_a_grep_finds_three_of_the_five`
re-derives the ``3`` on every run rather than trusting this paragraph.

The ``TYPE_CHECKING`` shape is the one that matters most in this repository:
deferring an import under it is the house pattern for breaking a runtime
dependency (``scoring.py`` uses it, and so does :mod:`acronymkit.core.conformal`),
so it is exactly the shape a well-meaning type annotation would take -- and a
type annotation is how a leaf stops being one without anybody noticing.

What this CANNOT see, printed rather than footnoted
---------------------------------------------------
**The facade layer is exempt and that is the loophole.** ``engine.py``,
``cli.py``, ``disambiguation.py``, ``models.py`` and the package ``__init__``
are in :data:`SHARED`: they are allowed to import both halves, because
composing them is what a facade is for. Nothing here stops somebody putting a
prose-tokenizer call inside ``engine.py`` and handing the result to the
identifier tokenizer -- the collision would be back, one module further out,
with every rule below green. The rule is about the *dependency graph*, and a
dependency graph cannot see a data flow.

**Nor can it see a string that is not a literal.** ``importlib.import_module(name)``
where ``name`` is computed defeats it entirely, and the walker says so at the
call site rather than pretending otherwise.

**And it is a tautology on two of its three edges today.** ``catalog -> nlp``
and ``nlp -> catalog`` were never present in this tree: the seam was already
clean before the split, which is why the split could be byte-identical. So on
this commit those two rules find nothing and could not have found anything. The
edge this test earns its keep on is ``core -> {nlp, catalog}``, which became
*possible* only because ``core`` now exists -- and the registered mutation in
``.github/gates.toml`` is the only evidence any of the three can fail.
"""

from __future__ import annotations

import ast
import base64
import importlib
import pickle
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Where the package being checked actually lives.
#:
#: **Resolved from the imported package rather than hard-coded to ``src/``, and
#: that is a checkout-only-files decision made the other way on purpose.** Four
#: instances are on record in this repository of a test that reads
#: checkout-only paths and therefore reddens or vacates in the extracted-sdist
#: and installed-wheel jobs; the newest was a prose rule reading ``src/``,
#: ``docs/`` and ``README.md`` as text, which reddened two jobs at once. This
#: rule reads ``.py`` files, and ``.py`` files SHIP -- ``MANIFEST.in`` carries
#: ``recursive-include src/acronymkit *.py`` and the wheel carries them by
#: construction. So pointing at ``acronymkit.__file__`` makes the boundary rule
#: run identically in a checkout, in an extracted sdist and against an installed
#: wheel, rather than being a checkout-only check that goes quiet in the two
#: environments D-058 was written about.
#:
#: The ONE thing here that is checkout-only is
#: :class:`TestTheRegisterAndThisModuleAgree`, which reads
#: ``.github/gates.toml``. It skips with a reason, and it says so.
PACKAGE_ROOT = Path(importlib.import_module("acronymkit").__file__ or "").resolve().parent

#: Printed on every boundary violation, and pinned against
#: ``.github/gates.toml``'s ``expect_failure_matching`` by
#: :func:`test_the_register_and_this_module_agree`. A gate whose failure text
#: drifts from the string its register matches on goes INERT while still
#: returning a non-zero exit, which is the failure ``gates.suite``'s note is
#: about.
FAILURE_MARKER = "architecture boundary crossed"

#: Module prefix -> the layer it belongs to. Longest prefix wins, so
#: ``acronymkit.core.conformal`` resolves before ``acronymkit.core``.
#:
#: The compatibility paths are in the layer they forward to, not in a layer of
#: their own: ``acronymkit.tokenizer`` **is** ``acronymkit.nlp.tokenizer``, and
#: a shim that started importing the other half would be exactly as much of a
#: violation as the module it forwards to doing it.
LAYER_OF: Dict[str, str] = {
    "acronymkit.core": "core",
    "acronymkit.exceptions": "core",
    "acronymkit.conformal": "core",
    "acronymkit.nlp": "nlp",
    "acronymkit.extractor": "nlp",
    "acronymkit.propagation": "nlp",
    "acronymkit.tokenizer": "nlp",
    "acronymkit.catalog": "catalog",
    "acronymkit.governed": "catalog",
}

#: Layer -> the layers it may not reach, by any import shape.
#:
#: ``governed`` and the three top-level nlp shims appear through
#: :data:`LAYER_OF`, so routing an import through a compatibility path does not
#: launder it. That is not hypothetical tidiness: a compatibility shim is the
#: obvious place for a future edit to reach the other half from, precisely
#: because it looks like a path nobody is watching.
FORBIDDEN: Dict[str, Tuple[str, ...]] = {
    "core": ("nlp", "catalog"),
    "nlp": ("catalog",),
    "catalog": ("nlp",),
}

#: Modules in no layer. They may import anything, and the docstring above says
#: what that costs.
SHARED = "shared"

#: What ``core`` may not contain, whatever it imports. These are the three
#: properties the leaf is DEFINED by -- no regular expressions, no lexical
#: assets, no string normalisation -- and they are checked at the syntax tree
#: rather than by reading the module docstring that claims them.
CORE_FORBIDDEN_MODULES = ("re", "regex", "unicodedata", "acronymkit.resources")

#: Attribute calls that normalise a string. ``lower`` is deliberately absent:
#: it is used for comparison in far too many places to carry a meaning here,
#: and a rule that fires on it would be turned off within a round.
CORE_FORBIDDEN_CALLS = ("casefold", "normalize", "encode", "decode")


def module_name(path: Path) -> str:
    """Dotted module name for a file under ``src/``.

    Args:
        path: A ``.py`` file inside the package.

    Returns:
        Its importable dotted name, with ``__init__`` stripped.
    """
    relative = path.relative_to(PACKAGE_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(["acronymkit", *parts])


def layer_of(dotted: str) -> str:
    """The layer a dotted module name belongs to, longest prefix first.

    Args:
        dotted: A module name, absolute.

    Returns:
        ``"core"``, ``"nlp"``, ``"catalog"``, or :data:`SHARED`.
    """
    for prefix in sorted(LAYER_OF, key=len, reverse=True):
        if dotted == prefix or dotted.startswith(prefix + "."):
            return LAYER_OF[prefix]
    return SHARED


def _absolute(module: Optional[str], level: int, importer: str, is_package: bool) -> Optional[str]:
    """Resolve a possibly-relative import target to an absolute dotted name.

    Args:
        module: The ``module`` of an ``ast.ImportFrom``, or ``None`` for
            ``from . import x``.
        level: Its ``level`` -- ``0`` for absolute, ``1`` for ``.``, and so on.
        importer: Dotted name of the module doing the importing.
        is_package: Whether the importer is a package ``__init__``.

    Returns:
        The absolute dotted name, or ``None`` when the relative import walks
        off the top of the tree (which Python itself would reject).
    """
    if level == 0:
        return module
    package = importer if is_package else importer.rsplit(".", 1)[0]
    parts = package.split(".")
    if level > 1:
        if level - 1 > len(parts):
            return None
        parts = parts[: len(parts) - (level - 1)]
    return ".".join([*parts, module] if module else parts)


def imports_of(path: Path) -> List[Tuple[str, int, str]]:
    """Every import target in one file, whatever shape it is written in.

    Five shapes are recognised, and the fifth is the reason this is not a grep:

    1. ``import acronymkit.nlp`` / ``import acronymkit.nlp as x``
    2. ``from acronymkit.nlp import x``
    3. ``from ..nlp import x`` -- relative, resolved against the importer
    4. either of the above nested anywhere: inside a function, a method, a
       ``try``, or an ``if TYPE_CHECKING:`` block. ``ast.walk`` reaches all of
       them because it does not care about scope.
    5. ``importlib.import_module("acronymkit.nlp.tokenizer")`` and
       ``__import__("...")`` with a **literal** first argument, plus an
       f-string whose literal parts already name the target.

    Args:
        path: The file to parse.

    Returns:
        ``(absolute target, line number, shape)`` for every import found.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    importer = module_name(path)
    is_package = path.name == "__init__.py"
    found: List[Tuple[str, int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name, node.lineno, "import"))
        elif isinstance(node, ast.ImportFrom):
            target = _absolute(node.module, node.level, importer, is_package)
            if target is None:
                continue
            found.append((target, node.lineno, "from"))
            for alias in node.names:
                # ``from acronymkit import nlp`` names the submodule in the
                # alias, not in the module. Recording both is what makes that
                # spelling as visible as ``import acronymkit.nlp``.
                found.append((f"{target}.{alias.name}", node.lineno, "from-name"))
        elif isinstance(node, ast.Call):
            for literal in _literal_import_arguments(node):
                found.append((literal, node.lineno, "importlib"))
    return found


def _literal_import_arguments(node: ast.Call) -> Iterable[str]:
    """Literal module names passed to ``import_module`` or ``__import__``.

    A computed name is invisible here and no amount of AST work changes that;
    :func:`test_a_computed_import_name_is_invisible` pins it as a known blind
    spot rather than leaving it to be discovered.

    Args:
        node: A call node.

    Yields:
        Each literal dotted name the call would import.
    """
    function = node.func
    name = function.attr if isinstance(function, ast.Attribute) else getattr(function, "id", "")
    if name not in ("import_module", "__import__"):
        return
    for argument in node.args[:1]:
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            yield argument.value
        elif isinstance(argument, ast.JoinedStr):
            literal = "".join(
                part.value
                for part in argument.values
                if isinstance(part, ast.Constant) and isinstance(part.value, str)
            )
            if literal:
                yield literal


def violations_in(path: Path) -> List[str]:
    """Every forbidden edge one file declares.

    Args:
        path: A module inside the package.

    Returns:
        One human-readable line per violation, each carrying
        :data:`FAILURE_MARKER`.
    """
    importer = module_name(path)
    source_layer = layer_of(importer)
    banned = FORBIDDEN.get(source_layer, ())
    if not banned:
        return []
    problems = []
    for target, line, shape in imports_of(path):
        if not target.startswith("acronymkit"):
            continue
        target_layer = layer_of(target)
        if target_layer in banned:
            problems.append(
                f"{FAILURE_MARKER}: {_where(path)}:{line} "
                f"({shape}) -- {importer} is in layer {source_layer!r} and imports "
                f"{target} in layer {target_layer!r}. "
                f"Layer {source_layer!r} may not reach {banned}."
            )
    return problems


def _where(path: Path) -> str:
    """A repo-relative path when there is one, an absolute path otherwise.

    The instrument tests plant probes under ``tmp_path``, which is not below the
    repository root, and ``Path.relative_to`` raises there rather than falling
    back. A message formatter that can raise turns a clear assertion failure
    into a confusing one.
    """
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def package_modules() -> List[Path]:
    """Every ``.py`` file that ships inside the package, sorted."""
    return sorted(p for p in PACKAGE_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


# ---------------------------------------------------------------------------
# the boundaries themselves
# ---------------------------------------------------------------------------
class TestTheSeam:
    """One rule per edge, over every module in the package."""

    @pytest.mark.parametrize("path", package_modules(), ids=lambda p: module_name(p))
    def test_no_module_crosses_a_forbidden_boundary(self, path: Path) -> None:
        """Per file, so a failure names the file rather than a count."""
        problems = violations_in(path)
        assert not problems, "\n".join(problems)

    def test_core_is_a_leaf(self) -> None:
        """``core`` imports from neither sibling, at any depth, in any shape.

        Stated separately from the parametrised rule above because it is the
        one edge that did not exist before this package existed, and because
        the parametrised form would report it as one red case among a hundred
        green ones.
        """
        problems: List[str] = []
        for path in package_modules():
            if layer_of(module_name(path)) != "core":
                continue
            problems.extend(violations_in(path))
        assert not problems, "\n".join(problems)

    def test_the_seam_has_something_to_say(self) -> None:
        """The census, so a green run reports a size rather than a silence.

        A rule that has never been evaluated is indistinguishable from a rule
        that passes, which is the shape D-110 named in this repository one
        round ago. This asserts the walker actually looked at all three layers
        and found imports in each.
        """
        counted = {"core": 0, "nlp": 0, "catalog": 0, SHARED: 0}
        edges = 0
        for path in package_modules():
            counted[layer_of(module_name(path))] += 1
            edges += len(imports_of(path))
        assert counted["core"] >= 4, counted
        assert counted["nlp"] >= 7, counted
        assert counted["catalog"] >= 14, counted
        assert edges > 200, f"only {edges} import statements parsed; the walker saw nothing"


# ---------------------------------------------------------------------------
# what core is, beyond what it imports
# ---------------------------------------------------------------------------
class TestTheLeafIsActuallyBare:
    """``core`` is defined by three absences, and each is checked in the tree."""

    @pytest.mark.parametrize(
        "path",
        [p for p in package_modules() if layer_of(module_name(p)) == "core"],
        ids=lambda p: module_name(p),
    )
    def test_core_has_no_regex_no_asset_and_no_normalisation(self, path: Path) -> None:
        """No ``re``, no ``unicodedata``, no bundled resource, no case folding."""
        problems = []
        for target, line, _shape in imports_of(path):
            root = target.split(".")[0]
            if root in CORE_FORBIDDEN_MODULES or target in CORE_FORBIDDEN_MODULES:
                problems.append(
                    f"{FAILURE_MARKER}: {_where(path)}:{line} "
                    f"imports {target}. acronymkit.core carries no regular expression, no "
                    f"lexical asset and no string normalisation; that is what makes it the "
                    f"leaf both tokenizers may depend on."
                )
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in CORE_FORBIDDEN_CALLS
            ):
                problems.append(
                    f"{FAILURE_MARKER}: {_where(path)}:"
                    f"{node.lineno} calls .{node.func.attr}(), which normalises a string."
                )
        assert not problems, "\n".join(problems)

    def test_importing_core_binds_no_sibling(self) -> None:
        """Runtime proof, in a fresh interpreter, of what the AST asserts statically.

        The AST rule reads what is written. This reads what happens: after
        ``import acronymkit.core`` and after touching every name in its
        ``__all__``, neither sibling package may be in ``sys.modules``. The two
        can disagree -- a module imported by something ``core`` imports would be
        invisible to the first and caught by the second.
        """
        script = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(REPO_ROOT / "src")!r})
            import acronymkit.core as core
            for name in core.__all__:
                getattr(core, name)
            leaked = sorted(
                m for m in sys.modules
                if m.startswith(("acronymkit.nlp", "acronymkit.catalog",
                                 "acronymkit.governed", "acronymkit.extractor",
                                 "acronymkit.tokenizer", "acronymkit.propagation"))
            )
            print("LEAKED:" + ",".join(leaked))
            """
        )
        completed = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, check=False
        )
        assert completed.returncode == 0, completed.stderr
        line = next(x for x in completed.stdout.splitlines() if x.startswith("LEAKED:"))
        leaked = [x for x in line[len("LEAKED:") :].split(",") if x]
        assert not leaked, f"{FAILURE_MARKER}: import acronymkit.core bound {leaked}"


# ---------------------------------------------------------------------------
# the claim that this is worth more than a grep, measured
# ---------------------------------------------------------------------------
#: Five ways to write one forbidden edge. The first is the only one a grep for
#: ``from acronymkit.catalog`` finds.
_EVASIONS: Sequence[Tuple[str, str]] = (
    ("plain from-import", "from acronymkit.catalog import expand_identifier\n"),
    ("aliased import", "import acronymkit.catalog as _c\n"),
    (
        "deferred, inside a function",
        "def helper():\n    from acronymkit.catalog.tokenizer import split_identifier\n"
        "    return split_identifier\n",
    ),
    (
        "TYPE_CHECKING only",
        "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n"
        "    from acronymkit.catalog.models import GovernedEntry\n",
    ),
    (
        "importlib on a literal",
        "import importlib\n\n_c = importlib.import_module('acronymkit.catalog.expansion')\n",
    ),
)


class TestTheInstrument:
    """The AST-beats-grep claim is a measurement here, not a sentence."""

    @pytest.mark.parametrize("label,body", _EVASIONS, ids=[label for label, _ in _EVASIONS])
    def test_the_walker_sees_every_shape_a_grep_misses(
        self, label: str, body: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Each evasion is planted in a ``core`` module and must be caught."""
        fake_package = tmp_path / "acronymkit"
        (fake_package / "core").mkdir(parents=True)
        (fake_package / "core" / "__init__.py").write_text("", encoding="utf-8")
        planted = fake_package / "core" / "probe.py"
        planted.write_text(body, encoding="utf-8")
        monkeypatch.setattr(sys.modules[__name__], "PACKAGE_ROOT", fake_package)
        problems = violations_in(planted)
        assert problems, f"the walker missed the {label} shape"
        assert FAILURE_MARKER in problems[0]

    def test_a_grep_finds_three_of_the_five(self) -> None:
        """The comparison, run rather than claimed, and the claim was wrong first.

        ``3`` of ``5``, not ``1`` of ``5``. This test was written asserting
        ``1``, because the brief this module was built from listed the deferred
        import among the shapes a grep misses. It fired on its first run: a
        deferred import is still spelled
        ``from acronymkit.catalog.tokenizer import ...``, so ``grep`` sees the
        text -- what it cannot see is the *scope*. The two shapes a grep misses
        outright are the aliased ``import ... as`` and the ``importlib`` literal.

        Left as a test rather than a corrected sentence because the sentence is
        what was wrong: an instrument's advantage over the instrument it
        replaces is a measurement, and a measurement that lives only in a
        docstring is the class this repository keeps finding.
        """
        pattern = "from acronymkit.catalog"
        seen = [label for label, body in _EVASIONS if pattern in body]
        missed = [label for label, body in _EVASIONS if pattern not in body]
        assert len(seen) == 3, f"the grep comparison has drifted: {seen}"
        assert missed == ["aliased import", "importlib on a literal"], missed

    def test_a_computed_import_name_is_invisible(self, tmp_path: Path) -> None:
        """The known blind spot, pinned so it is a property rather than a surprise.

        ``importlib.import_module(name)`` where ``name`` is a variable defeats
        every static instrument, this one included. Asserting that it is missed
        is the only way the limit stays written down: a blind spot nobody has
        written a failing test for is a blind spot somebody will later claim is
        covered.
        """
        fake_package = tmp_path / "acronymkit"
        (fake_package / "core").mkdir(parents=True)
        planted = fake_package / "core" / "probe.py"
        planted.write_text(
            "import importlib\n\n_name = 'acronymkit.' + 'catalog'\n"
            "_c = importlib.import_module(_name)\n",
            encoding="utf-8",
        )
        module = sys.modules[__name__]
        original = module.PACKAGE_ROOT
        module.PACKAGE_ROOT = fake_package
        try:
            assert violations_in(planted) == []
        finally:
            module.PACKAGE_ROOT = original


# ---------------------------------------------------------------------------
# the compatibility paths, which are the other half of the split
# ---------------------------------------------------------------------------
#: Old public path -> where it now lives. Every one of these is named in
#: ``README.md``, ``docs/`` or ``docs/DECISIONS.md``, and the last of those is a
#: file no workstream but the recorder may edit -- so a break here would leave
#: this project's own decision record citing an import path that does not exist.
COMPATIBILITY_PATHS = {
    "acronymkit.governed": "acronymkit.catalog",
    "acronymkit.governed.tokenizer": "acronymkit.catalog.tokenizer",
    "acronymkit.governed.models": "acronymkit.catalog.models",
    "acronymkit.governed.dictionary": "acronymkit.catalog.dictionary",
    "acronymkit.governed.expansion": "acronymkit.catalog.expansion",
    "acronymkit.governed.compliance": "acronymkit.catalog.compliance",
    "acronymkit.governed.naming": "acronymkit.catalog.naming",
    "acronymkit.governed.policy": "acronymkit.catalog.policy",
    "acronymkit.governed.enums": "acronymkit.catalog.enums",
    "acronymkit.governed.scoring": "acronymkit.catalog.scoring",
    "acronymkit.governed.loaders": "acronymkit.catalog.loaders",
    "acronymkit.governed.gap": "acronymkit.catalog.gap",
    "acronymkit.governed.namer": "acronymkit.catalog.namer",
    "acronymkit.governed.audit": "acronymkit.catalog.audit",
    "acronymkit.extractor": "acronymkit.nlp.extractor",
    "acronymkit.propagation": "acronymkit.nlp.propagation",
    "acronymkit.tokenizer": "acronymkit.nlp.tokenizer",
    "acronymkit.exceptions": "acronymkit.core.exceptions",
    "acronymkit.conformal": "acronymkit.core.conformal",
}


class TestTheCompatibilityPaths:
    """A shim that returns a copy is worse than a break, so identity is the rule."""

    @pytest.mark.parametrize("old,new", sorted(COMPATIBILITY_PATHS.items()))
    def test_the_old_path_still_imports(self, old: str, new: str) -> None:
        """Every documented path resolves, and every public name it had resolves."""
        legacy = importlib.import_module(old)
        current = importlib.import_module(new)
        for name in getattr(current, "__all__", []):
            assert hasattr(legacy, name), f"{old} lost {name}"

    @pytest.mark.parametrize("old,new", sorted(COMPATIBILITY_PATHS.items()))
    def test_the_old_path_yields_the_same_objects(self, old: str, new: str) -> None:
        """Identity, not equality.

        A shim that rebound names to fresh classes would satisfy every ``==``
        in this suite and fail the first time somebody wrote ``except`` or
        ``isinstance`` across the two paths -- which is the moment a
        compatibility shim exists for.
        """
        legacy = importlib.import_module(old)
        current = importlib.import_module(new)
        for name in getattr(current, "__all__", []):
            assert getattr(legacy, name) is getattr(current, name), f"{old}.{name} is a copy"

    @pytest.mark.parametrize(
        "old,new",
        sorted((o, n) for o, n in COMPATIBILITY_PATHS.items() if o.count(".") >= 1),
    )
    def test_a_submodule_shim_is_the_module_it_forwards_to(self, old: str, new: str) -> None:
        """One module object per submodule, not two holding equal-looking copies.

        Only the ones that replace themselves in ``sys.modules`` can satisfy
        this; ``acronymkit.governed`` itself and the two ``core`` shims
        deliberately do not, because a package that aliased itself would make
        ``import acronymkit.governed.models`` build a SECOND copy of every class
        under the old dotted name.
        """
        legacy = importlib.import_module(old)
        current = importlib.import_module(new)
        if old in ("acronymkit.governed", "acronymkit.exceptions", "acronymkit.conformal"):
            assert legacy is not current
            return
        assert legacy is current, f"{old} is a distinct module object from {new}"


#: A pickle written by the version BEFORE the split, protocol 4, holding
#: ``(EntryKind.CLASS_WORD_ABBREV, TokenizationError("boom"))``. The payload
#: names ``acronymkit.governed.enums`` and ``acronymkit.exceptions`` inside its
#: own bytes, because that is how ``pickle`` records a class: by
#: ``__module__`` and ``__qualname__``, resolved with ``getattr`` on whatever
#: ``sys.modules`` holds under that name at load time.
#:
#: Produced once, on 2026-09-09, by importing those two paths from a checkout of
#: 18204a1 -- the commit before this package was split -- and never regenerated.
#: Regenerating it from the current tree would make it name the NEW modules and
#: the test would assert nothing at all, which is the vacuous-pass shape this
#: repository keeps finding.
PRE_SPLIT_PICKLE = (
    "gASVfgAAAAAAAACMGWFjcm9ueW1raXQuZ292ZXJuZWQuZW51bXOUjAlFbnRyeUtpbmSUk5SMEWNsYXNz"
    "X3dvcmRfYWJicmV2lIWUUpSMFWFjcm9ueW1raXQuZXhjZXB0aW9uc5SMEVRva2VuaXphdGlvbkVycm9y"
    "lJOUjARib29tlIWUUpSGlC4="
)


class TestAPickleFromBeforeTheSplit:
    """The compatibility promise, tested against bytes rather than against a rerun."""

    def test_it_loads_and_resolves_to_the_current_classes(self) -> None:
        """A pickle naming the old modules must load, and give the NEW classes.

        This is the sharpest test of the shims that exists, because it does not
        go through any import statement this repository controls: ``pickle``
        looks the class up itself, by the dotted name recorded in the payload,
        through ``sys.modules``. If the shims stopped putting the real modules
        under the old names, or started putting COPIES there, this would either
        raise or hand back a class that is not the one the rest of the process
        is using -- and the second failure is the silent one.
        """
        from acronymkit.catalog.enums import EntryKind
        from acronymkit.core.exceptions import TokenizationError

        kind, error = pickle.loads(base64.b64decode(PRE_SPLIT_PICKLE))
        assert type(kind) is EntryKind, f"{FAILURE_MARKER}: unpickled a different EntryKind"
        assert kind is EntryKind.CLASS_WORD_ABBREV
        assert type(error) is TokenizationError, (
            f"{FAILURE_MARKER}: unpickled a different TokenizationError"
        )
        assert str(error) == "boom"

    def test_the_payload_really_names_the_old_paths(self) -> None:
        """Anti-vacuity: the fixture must still be a PRE-split pickle.

        Without this, somebody regenerating the constant from the current tree
        would leave a test that passes because it is asserting the new paths
        against themselves.
        """
        raw = base64.b64decode(PRE_SPLIT_PICKLE)
        assert b"acronymkit.governed.enums" in raw
        assert b"acronymkit.exceptions" in raw
        assert b"acronymkit.catalog" not in raw
        assert b"acronymkit.core" not in raw


# ---------------------------------------------------------------------------
# the register
# ---------------------------------------------------------------------------
class TestTheRegisterAndThisModuleAgree:
    """The marker is copied into ``.github/gates.toml``; copies drift."""

    def test_the_register_matches_on_this_module_s_marker(self) -> None:
        """``expect_failure_matching`` must be a string this module actually prints.

        Without this, a rename here leaves the register matching a string that
        never appears, the mutation harness reports the gate as INERT, and the
        gate keeps returning a non-zero exit for reasons nobody checks.
        """
        register = REPO_ROOT / ".github" / "gates.toml"
        if not register.is_file():  # pragma: no cover - checkout only
            pytest.skip(".github/ is not part of an installed distribution")
        body = register.read_text(encoding="utf-8")
        assert "[gates.architecture_boundaries]" in body, (
            "this gate is not in the register; a check that can fail and is not "
            "registered is the D-058 shape"
        )
        assert f'expect_failure_matching = "{FAILURE_MARKER}"' in body, (
            f"the register does not match on {FAILURE_MARKER!r}"
        )
