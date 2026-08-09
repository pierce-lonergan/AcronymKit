"""Packaging and import-purity contract for the ``acronymkit`` distribution.

Three promises are pinned here, all of which are invisible to the functional
tests and all of which are easy to break by accident:

* **The public surface is stable.** ``acronymkit.__all__`` is asserted as an
  exact sorted list, so removing or renaming an export is a failing test rather
  than a silent downstream ``ImportError``.
* **Tier 0 is pure.** Importing the package and running the four headline
  operations must not pull in ``click``, spaCy, NLTK, ONNX Runtime,
  ``transformers`` or NumPy. Asserted in a *subprocess* so that no other test in
  the session — several of which deliberately import ``click`` — can make the
  check pass or fail spuriously.
* **Every module stands alone.** Each public module is imported by itself in a
  fresh interpreter, which is what catches an import cycle that the package
  ``__init__`` would otherwise paper over.
"""

from __future__ import annotations

import importlib
import json
import os
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
    "HyphenPolicy",
    "Language",
    "LetterMapping",
    "LexiconError",
    "MappingKind",
    "NoCandidateError",
    "NumeralPolicy",
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
]

#: Every module a user may import directly. ``nlp`` is the sub-package.
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
