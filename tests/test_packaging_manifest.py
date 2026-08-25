"""``MANIFEST.in`` must name every fixture file the tree holds.

The narrow half of a file that used to hold two checks. ``MANIFEST.in`` has been
patched three times for the same class of defect -- ``bench/results.json``, then
``data/LICENSES.md``, then ``tests/fixtures/governed/*.json``, each fix naming
the file that had just broken -- and this test does not name a file: it reads
the tree, and asserts the manifest covers what it finds. A fixture in a format
nobody has used yet fails here, on a laptop.

What it covers that the two sdist jobs in CI do not
---------------------------------------------------
Both of those jobs are *structural*: they run the suite against a built
artifact, so a fixture the sdist failed to ship simply is not there and the
test that reads it dies. That is a stronger check than this one wherever a
running test reads the fixture -- and it is silent where none does yet.

.. code-block:: text

   un-gated, workstream measurement, 2026-08-24, CPython 3.13, scratch copy of
   the tree. Add tests/fixtures/governed/policies.yaml -- a fixture in a format
   `recursive-include tests/fixtures *.json *.jsonl *.csv *.txt *.md` does not
   name -- and build the sdist:
     the file is absent from the sdist                        (confirmed)
     build / extracted-tree `pytest -q -x`   rc=0             PASSES
     installed-suite                         gate rc=0        PASSES
     this test                               names the file   FAILS

A fixture is committed before, or in the same commit as, the test that reads
it. Until that reader exists and runs, this is the only check that sees the
file leaving the artifact. Its sibling guard -- an AST scan for module-level
loads of an unshipped path -- was retired in the same commit as that
measurement, because for *that* shape one structural job, ``build``'s
extracted-tree run, was shown to catch both cases the guard caught, by import
rather than by pattern, with this file deleted from the tree so the failure
could not be coming from the guard. Not `installed-suite`, which sees one of
the two. See the `installed-suite` job comment in ``.github/workflows/ci.yml``
for the five-case table.
"""

from __future__ import annotations

import importlib.util
import shlex
import sys
from fnmatch import fnmatch
from pathlib import Path
from types import ModuleType

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


def _load_check_claims() -> ModuleType:
    """Import the claims gate by path.

    ``tools/`` is a directory of scripts and deliberately not a package; the two
    test modules that already exercise it record the same reasoning.
    """
    path = REPO_ROOT / "tools" / "check_claims.py"
    spec = importlib.util.spec_from_file_location("_check_claims_for_manifest_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _is_covered(path: Path, patterns: list[str]) -> bool:
    """Return whether ``path`` matches any manifest pattern."""
    relative = path.relative_to(REPO_ROOT).as_posix()
    return any(fnmatch(relative, pattern) for pattern in patterns)


@pytest.mark.skipif(not MANIFEST.is_file(), reason="not a source checkout")
def test_every_fixture_data_file_is_named_by_the_manifest() -> None:
    """No test data may be left behind by the sdist.

    Asserted over the tree rather than over a list, so a fixture added in a
    format this manifest has never seen fails here. Measured: it fails *only*
    here until a test that runs reads it -- both sdist jobs stayed green on a
    dropped ``policies.yaml``, because nothing looked for it. See this module's
    docstring.
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
def test_every_file_the_claims_gate_reads_is_shipped_by_the_manifest() -> None:
    """Whatever the gate reads, the sdist ships -- derived, not remembered.

    This distribution has now shipped a checker it could not satisfy four times,
    each in the same shape and each caught by a different accident: first
    ``bench/results.json``, then ``data/LICENSES.md``, then a fixture, then
    ``bench/splits.toml`` when `tools/check_claims.py` gained it as a scan
    target and nothing connected the two facts. The failure is invisible in a
    checkout by construction -- every scan target is present there -- so it can
    only appear in the extracted tree, which is the slowest place to find it.

    Walking ``SCAN_GLOBS`` closes that: adding a scan target without a manifest
    line fails here, locally, in the commit that adds it. The gate's own glob
    syntax is `pathlib`-style, so each is expanded against the tree and every
    resulting file checked; a glob matching nothing is itself an error, since a
    scan target that names no file is a gate reading nothing.
    """
    tool = _load_check_claims()
    globs = list(tool.SCAN_GLOBS)
    assert globs, "SCAN_GLOBS is empty; this test would pass vacuously"

    patterns = _manifest_patterns()
    unmatched: list[str] = []
    missing: list[str] = []
    for glob in globs:
        hits = [p for p in REPO_ROOT.glob(glob) if p.is_file()]
        if not hits:
            unmatched.append(glob)
            continue
        missing.extend(
            p.relative_to(REPO_ROOT).as_posix() for p in hits if not _is_covered(p, patterns)
        )

    assert not unmatched, f"these SCAN_GLOBS entries match no file in the tree: {unmatched}"
    assert not missing, (
        "tools/check_claims.py reads these files, and MANIFEST.in does not ship "
        "them -- the sdist would carry a gate that cannot pass: "
        f"{sorted(set(missing))}"
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
