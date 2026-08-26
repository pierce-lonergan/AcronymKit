#!/usr/bin/env python3
"""Reintroduce each historical packaging breakage against a real sdist, one at a time.

Why this is a separate script from ``tools/gates.py``
----------------------------------------------------
Every other gate in ``.github/gates.toml`` is a command. These are not. The two
environments measured here -- ``build``'s extracted tree and the
``installed-suite`` run directory -- are multi-step sequences: build an sdist,
extract it, install it, lay out a directory that is not a checkout, then run a
suite and parse its log. There is no single command a mutation harness can
invoke, so this script **reproduces** the sequences.

**A reproduction is not the gate**, and that cost used to be paid in full: this
file carried its own copy of ``EXPECTED_NON_PASSING``, its own ``PASS_FLOOR``,
its own log parser and its own ``test -f`` list, and the guard that was supposed
to make those copies safe printed a ``WARNING:`` and carried on.

**The two ASSERTIONS are now invoked rather than reproduced.**
``tools/gate_installed_suite.py`` and ``tools/gate_sdist_files.py`` are the
single implementations; ``ci.yml`` runs them and this file imports them. There
is nothing left for them to drift from.

**The SEQUENCE around them is still reproduced, and that is refused rather than
hidden.** ``installed-suite``'s sequence spans ``$RUNNER_TEMP``,
``$GITHUB_WORKSPACE`` and a virtual environment the workflow creates; a job's
``run:`` block is not addressable from outside the workflow at all, so there is
no way to invoke it from here. What is checkable is that every command this file
copies still appears in the file it was copied from, and
:func:`sequence_drift` asserts exactly that -- fatally, before any case runs,
because a table produced by a reproduction of the wrong sequence gets quoted
onward. :data:`KNOWN_DIVERGENCES` names the places the reproduction is
deliberately not identical.

What it measures
----------------
Five real breakages, each the subject of a real fix commit:

===  ==========  =============================================================
id   fixed in    the breakage
===  ==========  =============================================================
a    9d6bb21     ``bench/results.json`` left out of the sdist, so the shipped
                 claims gate could not pass inside the shipped artifact
b    ade807f     ``data/LICENSES.md`` left out, so two shipped documents cite
                 evidence that resolves to nothing
c    ed053171    ``tests/fixtures/*`` left out, so the artifact's own suite
                 could not start
d    b9bf728     ``tests/test_governed_gold.py`` loads ``bench/`` at module
                 level with no guard -- a ``skipif`` cannot save a module body
                 that already ran
e    da8b222     ``tests/test_splits_manifest.py``, the same defect, in a
                 different spelling, past a guard written to catch it
===  ==========  =============================================================

and reports, per breakage, which environment caught it. That table is
``[[defect_coverage]]`` in ``.github/gates.toml``, and a disagreement between
this run and that table is a finding in one of them.

The unmutated control runs first and must be green in both environments. Without
it, a broken checkout produces five "caught" verdicts and reads as a triumph.

Why an ``*.egg-info`` sweep is the first thing it does
------------------------------------------------------
Three of D-050's verdicts were wrong the first time for one reason: a stale
``src/acronymkit.egg-info/SOURCES.txt`` makes setuptools ship files
``MANIFEST.in`` no longer names, so three mutations were run against unmutated
artifacts and all three reported "not caught". The uncaught version of that
error reaches a conclusion by luck, on false evidence. Every working copy here
is swept before it is built.

Usage::

    python tools/gate_packaging_mutation.py --out artifacts/packaging
    python tools/gate_packaging_mutation.py --out DIR --only a,e

Nothing here touches the network beyond what ``pip install`` already does in the
job that runs it.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent


def _sibling(name: str) -> Any:
    """Load a sibling ``tools/`` script by path.

    ``tools/`` is a directory of scripts and must not become a package: making
    it importable for one caller's convenience would change the shape of the
    thing under test. Same mechanism as ``tests/test_gate_manifest.py``.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(f"_{name}_under_test", TOOLS / f"{name}.py")
    if spec is None or spec.loader is None:  # pragma: no cover - unreachable in a checkout
        raise SystemExit(f"cannot load tools/{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


#: THE TWO ASSERTIONS ARE INVOKED, NOT REPRODUCED, AND THAT IS THE CHANGE.
#:
#: This file used to carry its own copy of ``EXPECTED_NON_PASSING``, its own
#: ``PASS_FLOOR``, its own log parser and its own ``test -f`` list, so it could
#: reproduce two of ``ci.yml``'s gates. A harness that re-implements a gate is
#: testing its own copy -- and the guard that was supposed to make the copy safe
#: (``check_expected_non_passing_is_current``) only ever printed a WARNING.
#:
#: Both are now single implementations that ``ci.yml`` runs and this file
#: imports. There is nothing left for them to drift from.
_installed_suite = _sibling("gate_installed_suite")
_sdist_files = _sibling("gate_sdist_files")

EXPECTED_NON_PASSING = set(_installed_suite.EXPECTED_NON_PASSING)
PASS_FLOOR = _installed_suite.PASS_FLOOR
TEST_F_LINES = tuple(name for name, _why in _sdist_files.REQUIRED)


def _drop_manifest_line(tree: Path, needle: str) -> None:
    path = tree / "MANIFEST.in"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [line for line in lines if needle not in line]
    if len(kept) == len(lines):
        raise SystemExit(f"no MANIFEST.in line matched {needle!r}; the mutation is stale")
    path.write_text("".join(kept), encoding="utf-8")


def _replace(tree: Path, rel: str, old: str, new: str) -> None:
    path = tree / rel
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(
            f"{rel}: the anchor occurs {text.count(old)} times, expected exactly one. "
            "The mutation no longer describes the historical breakage and must be re-derived "
            "from the fix commit rather than nudged."
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


Mutator = Callable[[Path], None]

BREAKAGES: Dict[str, Tuple[str, str, Mutator]] = {
    "a": (
        "9d6bb21",
        "bench/results.json out of the sdist",
        lambda tree: _drop_manifest_line(tree, "include bench/results.json"),
    ),
    "b": (
        "ade807f",
        "data/LICENSES.md out of the sdist",
        lambda tree: _drop_manifest_line(tree, "include data/LICENSES.md"),
    ),
    "c": (
        "ed05317",
        "tests/fixtures/* out of the sdist",
        lambda tree: _drop_manifest_line(tree, "recursive-include tests/fixtures"),
    ),
    "d": (
        "b9bf728",
        "test_governed_gold.py loads bench/ at module level, unguarded",
        lambda tree: _replace(
            tree,
            "tests/test_governed_gold.py",
            'gold = _load(RUNNER, "_governed_gold_under_test") if RUNNER.is_file() else None',
            'gold = _load(RUNNER, "_governed_gold_under_test")',
        ),
    ),
    "e": (
        "da8b222",
        "test_splits_manifest.py loads bench/corpora.py at module level, unguarded",
        lambda tree: _replace(
            tree,
            "tests/test_splits_manifest.py",
            "corpora = _load_corpora() if CORPORA_SOURCE.is_file() else None",
            "corpora = _load_corpora()",
        ),
    ),
}


#: THE RESIDUE, DECLARED. Every literal this file's reproduction depends on,
#: paired with what it reproduces. :func:`sequence_drift` requires each to be
#: present in ``ci.yml``; a rename or a flag change there reddens this run
#: instead of silently making the reproduction describe a sequence CI no longer
#: performs.
#:
#: This is the WEAKER half of the fix and it is labelled as such. The two
#: assertions above are invoked. The multi-step sequence around them cannot be:
#: it spans ``$RUNNER_TEMP``, ``$GITHUB_WORKSPACE`` and a virtual environment
#: the workflow creates, none of which exists outside a runner, and a job's
#: ``run:`` block is not addressable from outside the workflow at all. So the
#: sequence stays reproduced, and what is checkable about it is that every
#: command it copies still appears in the file it was copied from.
SEQUENCE_FRAGMENTS: Tuple[Tuple[str, str], ...] = (
    ("python -m build --sdist", "the sdist build in installed-suite"),
    ("python -m build\n", "the sdist+wheel build in build"),
    ("--strip-components=1", "how both jobs extract the sdist"),
    ("python -m pytest -q -x", "build's extracted-tree suite"),
    (
        "--continue-on-collection-errors --tb=short -rfEs",
        "installed-suite's pytest invocation",
    ),
    ('COLUMNS: "200"', "the terminal width the log parser depends on"),
    ('cp -r "$RUNNER_TEMP/sdist/tests" "$RUNNER_TEMP/run/tests"', "the run-directory layout"),
    ('cp "$RUNNER_TEMP/sdist/pyproject.toml"', "pytest configuration travelling with the tests"),
    ('test ! -e "$RUNNER_TEMP/run/src"', "the assertion that no source tree is reachable"),
    ("tools/gate_installed_suite.py", "the adjudicator this file imports"),
    ("tools/gate_sdist_files.py", "the file list this file imports"),
)

#: DIVERGENCES THIS FILE KNOWS IT HAS, written down because an undeclared
#: divergence is what cost the whole of run 32808357572. Each is a place the
#: reproduction is deliberately not identical to the job, with the reason.
KNOWN_DIVERGENCES: Tuple[str, ...] = (
    "installs the sdist with `--no-deps --force-reinstall` into the AMBIENT "
    "interpreter; `installed-suite` installs `${sdist}[dev]` into a fresh venv. "
    "A venv per case would multiply a six-case run by a full dependency resolve, "
    "and the measurement is about which files the artifact carries.",
    "adds `-p no:cacheprovider` to the extracted-tree run, which `build` does not, "
    "so six cases do not write six `.pytest_cache` directories into scratch trees.",
    "runs in a temp directory rather than under `$RUNNER_TEMP`, and copies the run "
    "directory with `shutil` rather than `cp -r`.",
    "does not re-run `build`'s wheel steps at all: `wheel_budget`, `wheel_resources` "
    "and `installed_wheel_smoke` are outside this harness and remain `inline`.",
)


def sequence_drift(root: Path = REPO_ROOT) -> List[str]:
    """Every command this file reproduces that ``ci.yml`` no longer contains.

    **This is the check that replaces a comment.** The previous guard here
    compared one copied list against the workflow and printed a WARNING if they
    disagreed; a warning in a log nobody reads is how a reproduction drifts for
    a whole phase. The two copied *lists* are gone -- they are imported now --
    and what is left is the sequence, which cannot be invoked from outside the
    workflow. So the sequence's literals are asserted instead, and a miss is a
    non-zero exit rather than a line of output.
    """
    workflow = root / ".github" / "workflows" / "ci.yml"
    if not workflow.is_file():
        return [f"{workflow} does not exist; the reproduction cannot be checked at all"]
    text = workflow.read_text(encoding="utf-8")
    problems = []
    for fragment, what in SEQUENCE_FRAGMENTS:
        if fragment not in text:
            problems.append(
                f"ci.yml no longer contains {fragment!r} ({what}). This file REPRODUCES that "
                "sequence and can only be reproducing something else now. Re-derive the "
                "reproduction from the workflow, or update SEQUENCE_FRAGMENTS and say what "
                "moved."
            )
    return problems


def _run(argv: Sequence[str], cwd: Path) -> Tuple[int, str]:
    done = subprocess.run(
        [str(part) for part in argv],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        errors="replace",
    )
    return done.returncode, done.stdout + done.stderr


def _installed_suite_gate(log: str) -> Dict[str, Any]:
    """The gate from ``ci.yml``'s installed-suite job, INVOKED rather than copied.

    One line, and the line is the point: ``tools/gate_installed_suite.py`` is
    what the job runs, so what is applied to this log is the gate and not a
    re-implementation of it.
    """
    verdict = dict(_installed_suite.adjudicate(log))
    verdict["gate_rc"] = verdict.pop("rc")
    return verdict


def _extract(
    tar: tarfile.TarFile, destination: Path, members: Optional[List[tarfile.TarInfo]] = None
) -> None:
    """``extractall`` without the 3.14 deprecation noise, on every supported version.

    The ``filter`` parameter arrived in 3.12; passing it unconditionally would
    break the 3.9 floor this project supports, and not passing it prints a
    warning on 3.13 that would sit in the middle of the coverage table this
    script exists to print.
    """
    if sys.version_info >= (3, 12):
        tar.extractall(destination, members=members, filter="data")
    else:  # pragma: no cover - 3.9-3.11 path
        _extract(tar, destination, members)


def _export_head(destination: Path) -> None:
    """A clean export of the working tree, with nothing untracked in it.

    ``git archive`` rather than a copy: the working copy holds ``data/``, a
    ``.venv``, caches and build output, and every one of those changes what the
    sdist contains or what the suite can reach. The measurement is about the
    tracked tree.
    """
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination.parent / "head.tar"
    with archive.open("wb") as handle:
        done = subprocess.run(
            ["git", "archive", "HEAD", "--format=tar"],
            cwd=str(REPO_ROOT),
            stdout=handle,
            stderr=subprocess.PIPE,
            text=True,
        )
    if done.returncode != 0:
        raise SystemExit(f"git archive failed: {done.stderr}")
    with tarfile.open(archive) as tar:
        _extract(tar, destination)
    archive.unlink()


def _extract_sdist(sdist: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(sdist) as tar:
        members = []
        for member in tar.getmembers():
            parts = Path(member.name).parts
            if len(parts) <= 1:
                continue
            member.name = str(Path(*parts[1:]))
            members.append(member)
        _extract(tar, destination, members)


def measure_one(case: str, base: Path, work: Path, python: str) -> Dict[str, Any]:
    """Build an sdist with one breakage reintroduced, and run both environments."""
    unmutated: Tuple[str, str, Mutator] = ("", "unmutated control", lambda _t: None)
    fixed_in, label, mutate = BREAKAGES.get(case, unmutated)
    tree = work / f"tree_{case}"
    shutil.rmtree(tree, ignore_errors=True)
    shutil.copytree(base, tree)
    # See the module docstring: a stale SOURCES.txt made three of D-050's
    # verdicts wrong, by shipping files MANIFEST.in no longer named.
    for junk in tree.rglob("*.egg-info"):
        shutil.rmtree(junk, ignore_errors=True)
    mutate(tree)

    record: Dict[str, Any] = {"case": case, "label": label, "fixed_in": fixed_in}
    started = time.time()
    # THE COMMAND IS THE GATE'S COMMAND, AND IT DID NOT USED TO BE.
    #
    # This line read `--no-isolation` until the first CI run of
    # `gate-mutation.yml` was read. `ci.yml`'s `build` job and its
    # `installed-suite` job both run a plain `python -m build`, with isolation,
    # so `--no-isolation` was the reproduction drifting from the thing it
    # reproduces -- the exact cost `.github/gates.toml` records beside
    # `gates.installed_expected_non_passing` and `gates.sdist_file_list`,
    # realised.
    #
    # It cost the whole measurement. A developer machine has `setuptools`
    # installed, so the isolated backend was never needed there; a GitHub
    # runner on 3.12 does not, and every one of the six builds died with
    # `BackendUnavailable: Cannot import 'setuptools.build_meta'`. All five
    # historical breakages came back `0 of 5` against a void control, and the
    # job reported success -- see the `| tee` in `gate-mutation.yml`.
    rc, out = _run([python, "-m", "build", "--sdist", "--outdir", "dist"], tree)
    if rc != 0:
        record["sdist_build"] = {"rc": rc, "tail": out[-3000:]}
        record["verdict"] = "SDIST BUILD FAILED"
        return record
    sdist = sorted((tree / "dist").glob("*.tar.gz"))[-1]

    extracted = work / f"ext_{case}"
    shutil.rmtree(extracted, ignore_errors=True)
    _extract_sdist(sdist, extracted)

    # INVOKED, not copied: `tools/gate_sdist_files.py` is what `build` runs.
    absent = _sdist_files.missing(extracted)
    record["test_f"] = {"missing": [name for name, _why in absent], "rc": 1 if absent else 0}

    rc, out = _run([python, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"], extracted)
    record["extracted_tree"] = {"rc": rc, "tail": out[-4000:]}

    _run(
        [python, "-m", "pip", "install", "--quiet", "--no-deps", "--force-reinstall", str(sdist)],
        work,
    )
    rundir = work / f"run_{case}"
    shutil.rmtree(rundir, ignore_errors=True)
    rundir.mkdir(parents=True)
    shutil.copytree(extracted / "tests", rundir / "tests")
    shutil.copy2(extracted / "pyproject.toml", rundir / "pyproject.toml")
    if (rundir / "src").exists():  # pragma: no cover - defensive
        raise SystemExit("a src/ tree got into the run directory; the measurement is void")
    environ = dict(os.environ, COLUMNS="200")
    done = subprocess.run(
        [
            python,
            "-m",
            "pytest",
            "--continue-on-collection-errors",
            "--tb=short",
            "-rfEs",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(rundir),
        capture_output=True,
        text=True,
        errors="replace",
        env=environ,
    )
    log = done.stdout + done.stderr
    record["installed_suite"] = _installed_suite_gate(log)
    record["installed_suite_tail"] = log[-4000:]
    record["seconds"] = round(time.time() - started, 1)

    shutil.rmtree(extracted, ignore_errors=True)
    shutil.rmtree(rundir, ignore_errors=True)
    shutil.rmtree(tree, ignore_errors=True)
    return record


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="where to write the artifacts")
    parser.add_argument("--only", default="", help="comma-separated breakage ids")
    parser.add_argument(
        "--work", type=Path, default=None, help="working root (default: a temp dir)"
    )
    parser.add_argument(
        "--check-drift",
        action="store_true",
        help="only check this file's reproduction against ci.yml, and exit",
    )
    args = parser.parse_args(argv)

    # THE DRIFT CHECK RUNS FIRST AND IS FATAL, WHICH IT WAS NOT BEFORE.
    #
    # `check_expected_non_passing_is_current()` printed `WARNING:` and carried
    # on, on the reasoning that "a harness that refuses to start because a list
    # moved is a harness people delete". That reasoning is wrong in the one
    # direction that matters: a reproduction that no longer reproduces the gate
    # produces a coverage TABLE, and the table is quoted onward. A number about
    # the wrong sequence is worse than no number.
    drift = sequence_drift()
    if drift:
        print(f"{len(drift)} drift(s) between this reproduction and ci.yml:", file=sys.stderr)
        for problem in drift:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(
        f"reproduction check: {len(SEQUENCE_FRAGMENTS)} sequence fragment(s) still present in "
        f"ci.yml; {len(KNOWN_DIVERGENCES)} divergence(s) declared; the two ASSERTIONS "
        "(EXPECTED_NON_PASSING/PASS_FLOOR and the sdist file list) are imported from the "
        "scripts ci.yml runs, not copied"
    )
    for divergence in KNOWN_DIVERGENCES:
        print(f"  declared divergence: {divergence}")
    if args.check_drift:
        return 0

    cases = ["control"] + (args.only.split(",") if args.only else list(BREAKAGES))
    unknown = [c for c in cases if c != "control" and c not in BREAKAGES]
    if unknown:
        print(f"no such breakage: {unknown}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    temp = None
    if args.work is None:
        temp = tempfile.mkdtemp(prefix="gatepkg")
        work = Path(temp)
    else:
        work = args.work
        work.mkdir(parents=True, exist_ok=True)
    base = work / "base"
    _export_head(base)

    results: Dict[str, Any] = {}
    print(f"{'case':<8}{'test -f':<10}{'extracted tree':<18}{'installed-suite':<18}label")
    for case in cases:
        record = measure_one(case, base, work, sys.executable)
        results[case] = record
        if record.get("verdict") == "SDIST BUILD FAILED":
            print(f"{case:<8}SDIST BUILD FAILED")
            continue
        test_f = "FAILS" if record["test_f"]["rc"] else "passes"
        ext = "FAILS" if record["extracted_tree"]["rc"] else "passes"
        inst = "FAILS" if record["installed_suite"]["gate_rc"] else "passes"
        print(f"{case:<8}{test_f:<10}{ext:<18}{inst:<18}{record['label']}")

    control = results.get("control", {})
    control_clean = (
        isinstance(control, dict)
        and control.get("test_f", {}).get("rc") == 0
        and control.get("extracted_tree", {}).get("rc") == 0
        and control.get("installed_suite", {}).get("gate_rc") == 0
    )
    caught_extracted = sum(
        1
        for case, r in results.items()
        if case != "control" and isinstance(r, dict) and r.get("extracted_tree", {}).get("rc")
    )
    caught_installed = sum(
        1
        for case, r in results.items()
        if case != "control" and isinstance(r, dict) and r.get("installed_suite", {}).get("gate_rc")
    )
    total = len(results) - 1
    print()
    print(f"build/extracted tree catches {caught_extracted} of {total}")
    print(f"installed-suite catches      {caught_installed} of {total}")
    print(
        "unmutated control: "
        + (
            "green in both environments"
            if control_clean
            else "NOT GREEN -- every verdict above is void"
        )
    )

    (args.out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    if temp is not None:
        shutil.rmtree(temp, ignore_errors=True)
    unbuilt = sorted(
        case
        for case, record in results.items()
        if isinstance(record, dict) and record.get("verdict") == "SDIST BUILD FAILED"
    )
    if unbuilt:
        # A CASE THAT COULD NOT BE BUILT IS NOT A CASE THAT WAS MEASURED, and
        # the first CI run of this script is why that is stated separately from
        # the control check below. Every one of the six builds failed there, the
        # table printed `0 of 5` twice, and the run was green -- so the number a
        # reader would have taken from it was not merely wrong, it was a number
        # about nothing at all.
        print(
            f"\n{len(unbuilt)} case(s) never produced an sdist: {unbuilt}. "
            "The tail of each is in results.json. Nothing in the table above is a "
            "measurement of packaging coverage; it is a measurement of a build that "
            "did not happen.",
            file=sys.stderr,
        )
        return 1
    if not control_clean:
        print(
            "\nThe control is the whole basis of the table. A broken checkout produces five "
            "'caught' verdicts and reads as a triumph, which is how three of D-050's "
            "measurements came out wrong the first time.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
