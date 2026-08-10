"""Packaging and import-purity contract for the ``acronymkit`` distribution.

Four promises are pinned here, all of which are invisible to the functional
tests and all of which are easy to break by accident:

* **The public surface is stable.** ``acronymkit.__all__`` is asserted as an
  exact sorted list, so removing or renaming an export is a failing test rather
  than a silent downstream ``ImportError``.
* **The lazy and the eager surfaces are the same surface.** The package
  ``__init__`` resolves its re-exports through :pep:`562`, with the real
  imports living in an ``if TYPE_CHECKING:`` block for static analysis. Two
  parallel lists is two lists that can drift, and drift between them is
  invisible to both mypy and the runtime — so the drift itself is asserted.
* **Tier 0 is pure.** Importing the package and running the four headline
  operations must not pull in ``click``, spaCy, NLTK, ONNX Runtime,
  ``transformers`` or NumPy. Asserted in a *subprocess* so that no other test in
  the session — several of which deliberately import ``click`` — can make the
  check pass or fail spuriously.
* **Every module stands alone.** Each public module is imported by itself in a
  fresh interpreter, which is what catches an import cycle that the package
  ``__init__`` would otherwise paper over.

Nothing here asserts a wall-clock threshold. Laziness is checked structurally —
which modules a bare import binds — because that is the property, and because a
hard-coded millisecond ceiling in the correctness suite is a claim about
somebody else's CPU (see ``docs/DECISIONS.md``, D-003). The timing lives in
``bench/run_micro.py`` and the CI ``import-time`` job.
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

import acronymkit
from conftest import REPO_ROOT, SRC

#: The exact public surface. Built from what is exported today; an accidental
#: removal, rename or unreviewed addition fails this list.
EXPECTED_ALL = [
    "AcronymCandidate",
    "AcronymEngine",
    "AcronymKitError",
    "AcronymPair",
    "AcronymResult",
    "BackronymCandidate",
    "BackronymResult",
    "BatchResult",
    "CaseStyle",
    "Config",
    "ConfigurationError",
    "DisambiguationCandidate",
    "DisambiguationResult",
    "EmptyPhraseError",
    "EngineMetadata",
    "EngineTier",
    "ExpansionDictionary",
    "ExtractionResult",
    "GenerationError",
    "GovernedDictionary",
    "GovernedEntry",
    "HyphenPolicy",
    "Language",
    "LetterMapping",
    "LexiconError",
    "MappingKind",
    "NamingPolicy",
    "NoCandidateError",
    "NumeralPolicy",
    "OfflineError",
    "ResourceNotFoundError",
    "STRATEGY_WEIGHTS",
    "ScoreBreakdown",
    "ScoringStrategy",
    "ScoringWeights",
    "StopWordCategory",
    "TierUnavailableError",
    "Token",
    "TokenRole",
    "TokenizationError",
    "__version__",
    "capabilities",
    "expand_identifier",
    "expand_token",
    "format_report",
    "is_compliant",
    "normalize_name",
    "to_physical_name",
]

#: Every module a user may import directly. ``nlp`` and ``governed`` are the
#: sub-packages.
PUBLIC_MODULES = [
    "resources",
    "stopwords",
    "tokenizer",
    "lexicon",
    "phonetics",
    "scoring",
    "generator",
    "backronym",
    "extractor",
    "disambiguation",
    "engine",
    "batch",
    "serialization",
    "cli",
    "nlp",
    "governed",
]

#: Distributions Tier 0 must never import, directly or transitively.
FORBIDDEN_AT_TIER_ZERO = [
    "click",
    "spacy",
    "nltk",
    "onnxruntime",
    "transformers",
    "numpy",
]


# ---------------------------------------------------------------------------
# subprocess helper
# ---------------------------------------------------------------------------
def run_in_subprocess(script: str, tmp_path: Path, name: str) -> subprocess.CompletedProcess:
    """Execute ``script`` in a fresh interpreter and return the completed process.

    Args:
        script: Python source to run.
        tmp_path: Directory the script file is written to.
        name: File name for the script, for readable failure output.

    Returns:
        The :class:`subprocess.CompletedProcess`, never checked for you.
    """
    path = tmp_path / name
    path.write_text(script, encoding="utf-8")
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=environment,
        check=False,
    )


#: Preamble putting the checkout's ``src/`` first, so a stale installed copy of
#: the distribution cannot be what gets tested.
_PREAMBLE = "import sys\nsys.path.insert(0, {src!r})\n"


# ---------------------------------------------------------------------------
# public surface
# ---------------------------------------------------------------------------
def test_all_is_the_expected_sorted_surface() -> None:
    """The export list is pinned exactly, so a removal cannot slip through."""
    assert sorted(acronymkit.__all__) == EXPECTED_ALL


def test_all_has_no_duplicates() -> None:
    """A duplicated export usually means a merge went wrong."""
    assert len(acronymkit.__all__) == len(set(acronymkit.__all__))


@pytest.mark.parametrize("name", EXPECTED_ALL)
def test_every_exported_name_is_present(name: str) -> None:
    """Everything ``__all__`` advertises is actually an attribute of the package."""
    assert hasattr(acronymkit, name), f"acronymkit.__all__ advertises missing name {name!r}"
    assert getattr(acronymkit, name) is not None


def test_star_import_binds_exactly_the_public_surface() -> None:
    """``from acronymkit import *`` yields ``__all__`` and nothing else."""
    namespace: dict[str, object] = {}
    exec("from acronymkit import *", namespace)  # the star-import is the behaviour under test
    namespace.pop("__builtins__", None)
    assert sorted(namespace) == EXPECTED_ALL


def test_version_is_a_non_empty_string() -> None:
    """``__version__`` is always usable, installed distribution or source checkout."""
    assert isinstance(acronymkit.__version__, str)
    assert acronymkit.__version__.strip()
    assert acronymkit.__version__ == acronymkit.__version__.strip()


def test_version_is_reported_on_engine_metadata() -> None:
    """The package version is the single source of truth for result metadata."""
    result = acronymkit.AcronymEngine().generate("Portable Document Format")
    assert result.metadata.library_version == acronymkit.__version__


# ---------------------------------------------------------------------------
# lazy re-export
# ---------------------------------------------------------------------------
def static_export_surface() -> tuple[dict[str, str], set[str]]:
    """Read the package ``__init__``'s ``if TYPE_CHECKING:`` block with ``ast``.

    That block is what mypy, IDEs and :pep:`561` consumers resolve; the runtime
    lookup table beside it is what an actual attribute access resolves. Reading
    the source rather than importing it is the point — importing tells you about
    the runtime path only, and it is the *static* path that would otherwise rot
    unobserved.

    Returns:
        ``({name: source submodule}, {statically annotated name, ...})``. The
        second set exists for ``__version__``, which is declared rather than
        imported because it is computed from the distribution metadata.
    """
    tree = ast.parse((SRC / "acronymkit" / "__init__.py").read_text(encoding="utf-8"))
    imported: dict[str, str] = {}
    annotated: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if not (isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING"):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.ImportFrom) and child.module:
                for alias in child.names:
                    imported[alias.asname or alias.name] = child.module
            elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                annotated.add(child.target.id)
    return imported, annotated


def test_the_lazy_path_and_the_eager_path_expose_identical_names() -> None:
    """The runtime lookup table and the type-checker imports are one surface.

    Three lists describe the same set of exports — ``__all__``, the
    ``TYPE_CHECKING`` imports and the runtime ``_EXPORT_SOURCES`` table — and
    nothing but this test notices when one of them drifts. Adding an export to
    the runtime table alone type-checks and runs; adding it to the
    ``TYPE_CHECKING`` block alone type-checks and raises ``AttributeError``.
    """
    imported, annotated = static_export_surface()
    assert sorted(set(imported) | annotated) == EXPECTED_ALL
    assert annotated == {"__version__"}, "only __version__ is computed rather than imported"
    assert imported == acronymkit._EXPORT_SOURCES, (
        "the TYPE_CHECKING imports and the runtime lazy table disagree; "
        "a name resolves for mypy but not at runtime, or the reverse"
    )


def test_every_lazy_export_is_the_object_its_own_module_defines() -> None:
    """Attribute access returns the very object an eager import would have bound.

    A handful of exports are renamed on the way out — ``normalize_name`` is
    ``governed.compliance.normalize`` — so the name to look up in the defining
    module comes from ``_EXPORT_ALIASES`` rather than from the export itself.
    That table is the only place the two spellings are tied together, which is
    why it is read here instead of the alias being repeated.
    """
    imported, _ = static_export_surface()
    for name, module in imported.items():
        source = importlib.import_module(f"acronymkit.{module}")
        defined_as = acronymkit._EXPORT_ALIASES.get(name, name)
        assert getattr(acronymkit, name) is getattr(source, defined_as), (
            f"acronymkit.{name} is not acronymkit.{module}.{defined_as}"
        )


def test_a_bare_import_binds_no_submodule_and_no_pydantic(tmp_path: Path) -> None:
    """``import acronymkit`` costs nothing because it does nothing.

    This is the structural form of the import-time budget: the package
    ``__init__`` must not have imported a single submodule, and therefore must
    not have built a single Pydantic core schema, which is where essentially all
    of this package's import cost used to go.
    """
    script = _PREAMBLE.format(src=str(SRC)) + (
        "import json\n"
        "import acronymkit\n"
        "print(json.dumps(sorted(m for m in sys.modules\n"
        "                        if m == 'pydantic' or m.startswith('acronymkit.'))))\n"
    )
    completed = run_in_subprocess(script, tmp_path, "lazy_import.py")
    assert completed.returncode == 0, completed.stderr
    bound = json.loads(completed.stdout.strip().splitlines()[-1])
    assert bound == [], f"a bare import of acronymkit eagerly bound {bound}"


def test_resolving_one_export_imports_only_the_module_that_defines_it(tmp_path: Path) -> None:
    """Naming an enum must not drag in the Pydantic DTO layer behind it."""
    script = _PREAMBLE.format(src=str(SRC)) + (
        "import json\n"
        "import acronymkit\n"
        "assert acronymkit.Language.EN.value == 'en'\n"
        "print(json.dumps(sorted(m for m in sys.modules\n"
        "                        if m == 'pydantic' or m.startswith('acronymkit.'))))\n"
    )
    completed = run_in_subprocess(script, tmp_path, "lazy_one_export.py")
    assert completed.returncode == 0, completed.stderr
    bound = json.loads(completed.stdout.strip().splitlines()[-1])
    assert bound == ["acronymkit.enums"], f"resolving Language bound {bound}"


def test_a_resolved_name_is_cached_in_the_module_globals() -> None:
    """The second access is a plain dict hit, not another ``__getattr__`` call."""
    module = importlib.import_module("acronymkit")
    name = "ScoringWeights"
    vars(module).pop(name, None)
    assert name not in vars(module)
    first = getattr(module, name)
    assert name in vars(module), "__getattr__ did not memoise the resolved export"
    assert vars(module)[name] is first


def test_submodules_stay_reachable_as_package_attributes() -> None:
    """``import acronymkit; acronymkit.tokenizer`` worked before and still does.

    Every submodule listed here used to be bound as a side effect of the eager
    re-exports. Losing that silently would break callers for no reason.
    """
    for name in sorted(acronymkit._SUBMODULES):
        assert getattr(acronymkit, name) is importlib.import_module(f"acronymkit.{name}")


def test_an_unknown_attribute_fails_like_any_other_module() -> None:
    """A lazy miss is indistinguishable from an ordinary one, message included."""
    missing = "definitely_not_exported"
    with pytest.raises(AttributeError, match=r"module 'acronymkit' has no attribute"):
        getattr(acronymkit, missing)


def test_dir_lists_the_whole_surface() -> None:
    """``dir()`` must not depend on which names happen to have been resolved yet."""
    listed = dir(acronymkit)
    assert listed == sorted(set(listed)), "dir() is neither sorted nor de-duplicated"
    for name in EXPECTED_ALL:
        assert name in listed
    for name in acronymkit._SUBMODULES:
        assert name in listed


def test_results_and_config_survive_a_pickle_round_trip() -> None:
    """Pickle resolves classes through their defining module, not the package.

    Worth pinning explicitly: lazy re-export changes what ``acronymkit``
    *itself* holds, and a naive implementation that rebound classes onto the
    package would break ``pickle``, which looks them up by ``__module__``.
    """
    config = acronymkit.Config(max_candidates=3)
    assert pickle.loads(pickle.dumps(config)) == config

    result = acronymkit.AcronymEngine(config).generate("Portable Document Format")
    restored = pickle.loads(pickle.dumps(result))
    assert restored.primary_acronym == result.primary_acronym
    assert restored.to_dict() == result.to_dict()


# ---------------------------------------------------------------------------
# module layout
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("module", PUBLIC_MODULES)
def test_public_module_is_importable_in_process(module: str) -> None:
    """Every public module resolves and declares an ``__all__``."""
    imported = importlib.import_module(f"acronymkit.{module}")
    assert hasattr(imported, "__all__"), f"acronymkit.{module} declares no __all__"
    for name in imported.__all__:
        assert hasattr(imported, name), f"acronymkit.{module}.__all__ names missing {name!r}"


@pytest.mark.parametrize("module", PUBLIC_MODULES)
def test_public_module_imports_cleanly_in_isolation(module: str, tmp_path: Path) -> None:
    """Each module imports first, alone, in a fresh interpreter.

    Importing ``acronymkit`` pulls the whole package in, which hides import
    cycles: a module that depends on a sibling only because ``__init__`` already
    imported it will still work. A fresh interpreter that imports exactly one
    module does not offer that crutch.
    """
    script = _PREAMBLE.format(src=str(SRC)) + (
        f"import importlib\nimportlib.import_module('acronymkit.{module}')\nprint('OK')\n"
    )
    completed = run_in_subprocess(script, tmp_path, f"import_{module}.py")
    assert completed.returncode == 0, (
        f"acronymkit.{module} failed to import in isolation:\n{completed.stderr}"
    )
    assert completed.stdout.strip() == "OK"
    assert completed.stderr == "", f"acronymkit.{module} wrote to stderr on import"


def test_py_typed_marker_ships_in_the_package_directory() -> None:
    """PEP 561: without this file, downstream type checkers ignore the package."""
    package_directory = Path(acronymkit.__file__).resolve().parent
    marker = package_directory / "py.typed"
    assert marker.is_file(), f"py.typed missing from {package_directory}"
    assert marker.read_text(encoding="utf-8").strip()


def test_py_typed_is_declared_as_package_data() -> None:
    """The marker must be shipped, not merely present in the checkout."""
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "py.typed" in pyproject


# ---------------------------------------------------------------------------
# Tier 0 import purity
# ---------------------------------------------------------------------------
_PURITY_SCRIPT = """
import json
import sys

sys.path.insert(0, {src!r})

import acronymkit

engine = acronymkit.AcronymEngine(
    acronymkit.Config(engine_tier=acronymkit.EngineTier.ZERO_DEPENDENCY)
)
engine.generate("Application Programming Interface")
engine.extract("The National Aeronautics and Space Administration (NASA) launched it.")
engine.generate_backronym("Next Generation High Performance Storage System", "NEXUS")
engine.disambiguate("BP", "Blood pressure (BP) was elevated at admission.")

forbidden = {forbidden!r}
print(json.dumps(sorted(name for name in forbidden if name in sys.modules)))
"""


def test_tier_zero_imports_nothing_optional(tmp_path: Path) -> None:
    """Tier 0 stays pure across generate, extract, backronym and disambiguate.

    Run out of process: other tests in this session import ``click`` and probe
    for NLTK, so ``sys.modules`` in the pytest interpreter proves nothing.
    """
    script = _PURITY_SCRIPT.format(src=str(SRC), forbidden=FORBIDDEN_AT_TIER_ZERO)
    completed = run_in_subprocess(script, tmp_path, "purity.py")
    assert completed.returncode == 0, completed.stderr
    leaked = json.loads(completed.stdout.strip().splitlines()[-1])
    assert leaked == [], f"Tier 0 pulled in optional dependencies: {leaked}"


def test_importing_the_package_alone_imports_nothing_optional(tmp_path: Path) -> None:
    """A bare ``import acronymkit`` is cheap even before anything is called."""
    script = _PREAMBLE.format(src=str(SRC)) + (
        "import json\n"
        "import acronymkit\n"
        f"forbidden = {FORBIDDEN_AT_TIER_ZERO!r}\n"
        "print(json.dumps(sorted(n for n in forbidden if n in sys.modules)))\n"
    )
    completed = run_in_subprocess(script, tmp_path, "import_purity.py")
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout.strip().splitlines()[-1]) == []


@pytest.mark.parametrize(
    "module",
    [
        "resources",
        "stopwords",
        "tokenizer",
        "lexicon",
        "phonetics",
        "scoring",
        "generator",
        "backronym",
        "extractor",
        "serialization",
    ],
)
def test_tier_zero_modules_import_nothing_optional(module: str, tmp_path: Path) -> None:
    """The modules the build spec declares Tier 0 stay stdlib + pydantic only."""
    script = _PREAMBLE.format(src=str(SRC)) + (
        "import json\n"
        f"import acronymkit.{module}\n"
        f"forbidden = {FORBIDDEN_AT_TIER_ZERO!r}\n"
        "print(json.dumps(sorted(n for n in forbidden if n in sys.modules)))\n"
    )
    completed = run_in_subprocess(script, tmp_path, f"pure_{module}.py")
    assert completed.returncode == 0, completed.stderr
    leaked = json.loads(completed.stdout.strip().splitlines()[-1])
    assert leaked == [], f"acronymkit.{module} imported {leaked} at module scope"


def test_nlp_subpackage_imports_without_any_optional_runtime(tmp_path: Path) -> None:
    """``acronymkit.nlp`` is importable on a machine with neither spaCy nor NLTK."""
    script = _PREAMBLE.format(src=str(SRC)) + (
        "import json\n"
        "import acronymkit.nlp as nlp\n"
        "assert nlp.HeuristicBackend().is_available() is True\n"
        "print(json.dumps(sorted(n for n in ('spacy', 'nltk') if n in sys.modules)))\n"
    )
    completed = run_in_subprocess(script, tmp_path, "nlp_import.py")
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout.strip().splitlines()[-1]) == []
