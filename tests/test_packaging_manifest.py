"""The sdist must carry everything its own test suite reads.

This distribution has now shipped assertions without their evidence three
times, in three different disguises:

* ``bench/results.json`` -- the docs made accuracy claims and
  ``tools/check_claims.py`` shipped as the gate that backs them, but the
  measurements did not, so the shipped checker could not pass inside the
  shipped artifact;
* ``data/LICENSES.md`` -- ``SECURITY.md`` cited it as the evidence for the
  pinned-and-checksummed asset claim, and the link was unresolvable for anyone
  holding a distribution rather than a checkout;
* ``tests/fixtures/governed/*.json`` -- ``recursive-include tests *.py`` took
  the test code and left its data, so ``pytest`` inside the sdist died on a
  missing file.

Each was fixed by adding a line to ``MANIFEST.in``, and each fix was specific
to the file that had just broken. That is why it happened three times. The test
here does not name any file: it reads the tree, works out which files the suite
needs, and asserts the manifest covers them. A fixture in a format nobody has
used yet fails here, on a laptop, rather than in the release job.
"""

from __future__ import annotations

import ast
import shlex
from fnmatch import fnmatch
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "MANIFEST.in"

#: Directories whose contents are test *data*. Test code is already covered by
#: ``recursive-include tests *.py``; these hold everything that is not code.
FIXTURE_ROOTS = (REPO_ROOT / "tests" / "fixtures",)

#: Never shipped, never checked.
_IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".hypothesis"}


def _manifest_patterns() -> list[str]:
    """Return every path pattern ``MANIFEST.in`` includes, repo-relative.

    ``recursive-include <dir> <pat>...`` is expanded to ``<dir>/**/<pat>`` so a
    single :func:`fnmatch` per pattern decides the question. ``exclude`` and
    ``prune`` are deliberately not modelled: this test asks whether a file is
    *named*, and a distribution that both includes and prunes the same path is
    a different bug that would show up as a missing file in the sdist job.

    Returns:
        Glob patterns, repo-relative, POSIX-separated.
    """
    patterns: list[str] = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        fields = shlex.split(line, comments=True)
        if not fields:
            continue
        directive, rest = fields[0], fields[1:]
        if directive == "include":
            patterns.extend(rest)
        elif directive == "recursive-include" and len(rest) > 1:
            root, globs = rest[0].replace("\\", "/").rstrip("/"), rest[1:]
            for glob in globs:
                patterns.append(f"{root}/{glob}")
                patterns.append(f"{root}/**/{glob}")
    return patterns


def _fixture_data_files() -> list[Path]:
    """Return every non-Python file the test suite reads as data."""
    found: list[Path] = []
    for root in FIXTURE_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix == ".py":
                continue
            if _IGNORED_PARTS.intersection(path.parts):
                continue
            found.append(path)
    return found


def _is_covered(path: Path, patterns: list[str]) -> bool:
    """Return whether ``path`` matches any manifest pattern."""
    relative = path.relative_to(REPO_ROOT).as_posix()
    return any(fnmatch(relative, pattern) for pattern in patterns)


@pytest.mark.skipif(not MANIFEST.is_file(), reason="not a source checkout")
def test_every_fixture_data_file_is_named_by_the_manifest() -> None:
    """No test data may be left behind by the sdist.

    Asserted over the tree rather than over a list, so a fixture added in a
    format this manifest has never seen fails here instead of in the release
    job.
    """
    files = _fixture_data_files()
    assert files, "no fixture data found; this test would pass vacuously"

    patterns = _manifest_patterns()
    missing = [
        path.relative_to(REPO_ROOT).as_posix() for path in files if not _is_covered(path, patterns)
    ]

    assert not missing, (
        "MANIFEST.in does not ship these test data files, so `pytest` inside "
        f"the sdist cannot run: {missing}"
    )


@pytest.mark.skipif(not MANIFEST.is_file(), reason="not a source checkout")
def test_the_manifest_covers_the_conftest_the_suite_cannot_start_without() -> None:
    """A guard on the guard: the pattern set must actually match something real.

    ``_manifest_patterns`` parses a file format by hand. If that parsing broke
    and returned nothing, the test above would report every fixture missing and
    be obviously wrong -- but if it broke and returned something over-broad, the
    test above would pass while proving nothing. Anchoring on a file known to be
    both present and named keeps the parser honest in that direction.
    """
    patterns = _manifest_patterns()
    assert _is_covered(REPO_ROOT / "tests" / "conftest.py", patterns)
    assert not _is_covered(REPO_ROOT / "MANIFEST.in.nope", patterns)


#: Directories a test may reference by path that the sdist does NOT ship.
#: `bench/*.py` is the live case: the runners need fetched corpora and optional
#: dependencies an sdist has no business assuming, so they are deliberately left
#: out, and `MANIFEST.in` says so.
_UNSHIPPED_ROOTS = ("bench",)


def _unshipped_path_names(tree: ast.Module) -> set:
    """Names bound at module level to a path inside an unshipped directory.

    Matched structurally — any assignment whose right-hand side mentions one of
    :data:`_UNSHIPPED_ROOTS` as a string literal — so the binding is found
    regardless of how the path is spelled or which helper consumes it.
    """
    bound = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        literals = {
            child.value
            for child in ast.walk(node)
            if isinstance(child, ast.Constant) and isinstance(child.value, str)
        }
        if not literals.intersection(_UNSHIPPED_ROOTS):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                bound.add(target.id)
    return bound


def _functions_reaching_unshipped(tree: ast.Module) -> set:
    """Functions in this module whose own body builds an unshipped path.

    The second thing the earlier versions of this check could not see. A
    module-level ``corpora = _load_corpora()`` mentions no path at all — the
    path is built inside the function — so a check that only looks at the call
    site is blind to it, which is exactly how the fifth breakage got through.
    One level of indirection is enough to catch every instance this repository
    has actually produced; a deeper chain would need real call-graph analysis
    and has never occurred here.
    """
    reaching = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        literals = {
            child.value
            for child in ast.walk(node)
            if isinstance(child, ast.Constant) and isinstance(child.value, str)
        }
        if literals.intersection(_UNSHIPPED_ROOTS):
            reaching.add(node.name)
    return reaching


def _unguarded_module_level_uses(source: str) -> list:
    """Module-level statements that CONSUME an unshipped path without a guard.

    The earlier version of this check matched the text ``= _load(NAME``, which
    tied it to one helper's name. The fifth breakage of this class was spelled
    ``_load_corpora`` and sailed straight through — a guard that varied
    everything except the spelling the bug used, which is the failure shape this
    file exists to catch. Structure, not spelling: walk the module's top-level
    statements, find the ones that call something with an unshipped-path name in
    the call, and accept only those whose statement also tests the path.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover - a broken test file fails elsewhere
        return []

    bound = _unshipped_path_names(tree)
    reaching = _functions_reaching_unshipped(tree)
    if not bound and not reaching:
        return []

    offenders = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.Expr)):
            continue
        calls = [child for child in ast.walk(node) if isinstance(child, ast.Call)]
        if not calls:
            continue
        mentioned = {
            child.id
            for child in ast.walk(node)
            if isinstance(child, ast.Name) and child.id in bound
        }
        # A path constant may also be USED to build another constant, which is
        # inert. Only a call is a load.
        called = {call.func.id for call in calls if isinstance(call.func, ast.Name)}
        uses_path = (
            bool(mentioned)
            or bool(called.intersection(reaching))
            or any(
                isinstance(child, ast.Constant)
                and isinstance(child.value, str)
                and child.value in _UNSHIPPED_ROOTS
                for call in calls
                for child in ast.walk(call)
            )
        )
        if not uses_path:
            continue
        # Accepted guards: a conditional expression, or an `is_file`/`exists`
        # test anywhere in the same statement.
        guarded = any(isinstance(child, ast.IfExp) for child in ast.walk(node)) or any(
            isinstance(child, ast.Attribute) and child.attr in {"is_file", "exists"}
            for child in ast.walk(node)
        )
        if not guarded:
            offenders.append(getattr(node, "lineno", 0))
    return offenders


@pytest.mark.skipif(not MANIFEST.is_file(), reason="not a source checkout")
def test_no_test_imports_an_unshipped_path_at_module_level() -> None:
    """A test may reference `bench/` — but not while it is being imported.

    This is the third time this distribution has shipped a test without the
    thing it reads: `bench/results.json`, then `data/LICENSES.md`, then the
    governed fixtures. Each fix named the file that had just broken, which is
    why there was a next one. The two earlier shapes are covered above by
    checking the manifest against the tree.

    This is the remaining shape, and it is not a manifest problem at all: the
    file is *correctly* absent, and the defect is a module body that reads it
    anyway. `pytest.mark.skipif` looks like it guards that and does not — the
    mark runs at collection, the module body at import. The fix is always to
    make the load conditional on the path existing.

    Caught in CI's sdist job, where the suite runs inside the built artifact.
    Caught here means caught on a laptop instead.
    """
    offenders: dict[str, list[int]] = {}
    for path in sorted((REPO_ROOT / "tests").rglob("test_*.py")):
        lines = _unguarded_module_level_uses(path.read_text(encoding="utf-8"))
        if lines:
            offenders[path.name] = lines

    assert not offenders, (
        "these tests load an unshipped path while being imported, so "
        f"`pytest.mark.skipif` cannot save them inside an sdist: {offenders}"
    )
