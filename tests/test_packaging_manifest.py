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
