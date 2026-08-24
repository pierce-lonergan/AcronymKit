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


def _module_level_path_loads(source: str) -> list[str]:
    """Return module-level names that build a path into an unshipped directory.

    Deliberately crude — a textual scan for a `REPO_ROOT / "<root>" / ...`
    assignment at column zero. A test that does this at import time cannot be
    rescued by ``pytest.mark.skipif``, because the mark is consulted at
    collection and the module body has already run by then.
    """
    found: list[str] = []
    for line in source.splitlines():
        if line.startswith((" ", "\t", "#")) or "REPO_ROOT" not in line:
            continue
        for root in _UNSHIPPED_ROOTS:
            if f'"{root}"' in line and "=" in line:
                found.append(line.split("=", 1)[0].strip())
    return found


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
    offenders: dict[str, list[str]] = {}
    for path in sorted((REPO_ROOT / "tests").rglob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        names = _module_level_path_loads(source)
        if not names:
            continue
        # A constant is fine; executing it unconditionally is not.
        for name in names:
            unguarded = f"= _load({name}" in source.replace(" ", "").replace("=_load(", "= _load(")
            if unguarded and f"if {name}.is_file()" not in source:
                offenders.setdefault(path.name, []).append(name)

    assert not offenders, (
        "these tests load an unshipped path while being imported, so "
        f"`pytest.mark.skipif` cannot save them inside an sdist: {offenders}"
    )
