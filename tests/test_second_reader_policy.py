"""The cold-read policy must execute, and its trigger must be able to return nothing.

Why this file exists
--------------------
``docs/SECOND-READER.md`` published a trigger command that **returned nothing at
the only moment it fires**. The policy places the cold read before the recorder
commits, so ``git diff --name-only <round-base>..HEAD`` compares ``HEAD`` with
itself; and ``git diff`` cannot see a file that exists under neither revision,
which is what the round's most important page was. A reader who trusted the
command would have concluded the round touched nothing and stopped.

It was corrected in place, and **a corrected command in a document is the same
artifact as the wrong one**: prose, unexecuted, trusted. So the correction is a
function now, and this file is the part that makes it a check rather than a
transcript. R11 asks for a mutation in the environment where the thing runs; a
transcript of one is in section 9 of the policy page, and the sentence this
repository has written three times and acted on twice is that *a check that
exists only in a transcript is not a check*.

What is pinned here, and why each one
-------------------------------------
* **The trigger returns a modified tracked file AND a new untracked one.** Those
  are the two halves the published command missed, and they are asserted
  together because the repair for the first (drop the revision range) does not
  fix the second.

* **The trigger can return nothing.** Two states: a clean tree, and a tree where
  only the excluded files changed. A trigger that always fires is not a trigger,
  and the negative direction is the half a transcript taken mid-round cannot
  reach without destroying the round.

* **The superseded command still fails, in the same tree, in the same test.**
  The defect is pinned rather than described, so a future round cannot quietly
  reintroduce the range and get a green suite.

* **The page and the code agree about the pathspec.** ``PATHSPEC`` lives in
  ``tools/second_reader.py`` and is printed in section 3. A pathspec in two
  places is a pathspec that will disagree with itself, and the last disagreement
  on this page cost a round. This is check C6 of the protocol, aimed at the
  protocol.

* **The rotation cursor is derivable, and the page agrees with the ledger.** The
  policy's only state used to be a sentence. D-072 found that its rule --
  *oldest-read first* -- was uncomputable, because no per-file read dates exist
  anywhere.

* **Every rule the ledger validator enforces is mutation-tested**, not asserted.
  A validator is worth exactly what it refuses, and the rule that matters most is
  the one that refuses ``applied_by`` equal to the reader who raised the finding:
  the cold reader reports and somebody else applies, and that is here because a
  sentence saying so did not hold.

* **Every command the gate list publishes is run.** ``--help`` on each ``tools/``
  gate, with the flag the document names required to appear in it. The document
  said "the six local ones" and CI runs seven.

What this file does NOT do
--------------------------
It never mutates this repository's working tree. Every trigger test builds a
throwaway git repository under ``tmp_path``; the two tests that touch this
checkout are read-only and assert a direction rather than an equality. That is
the same rule ``tests/test_gate_manifest.py`` states about its own mutation
runner: a test that edits the tree several agents are working in is a defect and
not a test.

Nothing here reaches the network or opens a corpus.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Callable, List, Optional, Sequence, Tuple

import pytest

NL = chr(10)

REPO_ROOT = Path(__file__).resolve().parent.parent
LOADER = REPO_ROOT / "tools" / "second_reader.py"
POLICY = REPO_ROOT / "docs" / "SECOND-READER.md"
LEDGER = REPO_ROOT / "docs" / "cold-reads.toml"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"

# THE GUARD, PLACED BEFORE THE LOAD AND NOT ON A MARK.
#
# `pytest.mark.skipif` is consulted at COLLECTION and a module body runs at
# IMPORT, which is earlier -- the lesson of the fourth and fifth historical
# packaging breakages, both of which shipped past a `skipif` that could not
# help. `tools/` ships in the sdist and is no part of an installed
# distribution, so under the `installed-suite` job the load below would raise
# FileNotFoundError and this file would fail to COLLECT rather than skip.
#
# It is a skip on ONE named condition. `EXPECTED_NON_PASSING` in
# `.github/workflows/ci.yml` is not grown for this file, and any other error
# here must still reach the job.
if not LOADER.is_file():  # pragma: no cover - CI job only
    pytest.skip(
        "tools/ is not part of an installed distribution; these tests belong to a checkout",
        allow_module_level=True,
    )


def _load_tool() -> ModuleType:
    """Import ``tools/second_reader.py`` by path.

    ``tools/`` is a directory of scripts and must not become a package: making
    it importable for a test's convenience would change the shape of the thing
    under test. Same mechanism as ``tests/test_gate_manifest.py``.
    """
    spec = importlib.util.spec_from_file_location("_second_reader_under_test", LOADER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sr = _load_tool()

#: 3.9 and 3.10 have no ``tomllib``, and ``tomli`` is not a declared dev
#: dependency, so on those interpreters there is no parser to read the ledger
#: with. The trigger tests need none and go on running.
_NO_PARSER = sys.version_info < (3, 11) and importlib.util.find_spec("tomli") is None
needs_parser = pytest.mark.skipif(_NO_PARSER, reason="tomllib is 3.11+; tomli not installed")

#: ``MANIFEST.in`` ships ``docs/*.md`` and nothing else from ``docs/``, so the
#: ledger is absent inside an sdist exactly as ``.github/gates.toml`` is. The
#: mark is narrow on purpose: the synthetic-ledger tests need no such file.
needs_ledger = pytest.mark.skipif(
    not LEDGER.is_file(), reason="docs/cold-reads.toml is not shipped in the sdist"
)

_GIT = shutil.which("git")
needs_git = pytest.mark.skipif(_GIT is None, reason="git is not on PATH")
needs_checkout = pytest.mark.skipif(
    _GIT is None or not (REPO_ROOT / ".git").exists(),
    reason="this is not a git checkout (an extracted sdist is not one)",
)


# ---------------------------------------------------------------------------
# a throwaway repository, because the trigger reads git and nothing else
# ---------------------------------------------------------------------------
def _git(root: Path, *args: str) -> str:
    """Run git in ``root`` and return stdout, failing the test on a non-zero exit."""
    completed = subprocess.run(
        [
            str(_GIT),
            # A throwaway fixture repository, so identity and signing are
            # supplied inline rather than inherited: a developer machine with
            # `commit.gpgsign = true` in its global config would otherwise make
            # every test here fail for a reason that has nothing to do with the
            # trigger.
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "user.name=fixture",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=str(root),
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"git {' '.join(args)} failed in {root}: "
        f"{completed.stderr.decode('utf-8', 'replace').strip()}"
    )
    return completed.stdout.decode("utf-8", "replace")


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


#: The tracked files every fixture repository starts with: one file from each
#: class the trigger has to tell apart.
_SEED = {
    "README.md": "front page\n",
    "CHANGELOG.md": "changes\n",
    "CONTRIBUTING.md": "contributing\n",
    "SECURITY.md": "security\n",
    "pyproject.toml": '[project]\nname = "fixture"\n',
    "docs/EVALUATION.md": "numbers\n",
    "docs/DECISIONS.md": "a historical record, excluded\n",
    "docs/AUDIT-2026-08.md": "a historical record, excluded\n",
    "docs/notes/w11.md": "a scoped note, excluded\n",
    "docs/cold-reads.toml": "# machine state, excluded\n",
    "src/acronymkit/__init__.py": "# not user-facing\n",
}


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A committed, clean git repository shaped like this one."""
    root = tmp_path / "fixture"
    root.mkdir()
    _git(root, "init", "--quiet")
    for relative, text in _SEED.items():
        _write(root, relative, text)
    _git(root, "add", "-A")
    _git(root, "commit", "--quiet", "-m", "seed")
    # ANTI-VACUITY. If the seed did not commit, every "returns nothing" test
    # below would pass for the wrong reason and every "returns both" test would
    # fail confusingly. `tests/test_gate_manifest.py` makes the same argument
    # about a scanner that returns zero jobs.
    assert _git(root, "ls-files").strip(), "the fixture committed no files"
    assert not _git(root, "status", "--porcelain").strip(), "the fixture is not clean"
    return root


# ---------------------------------------------------------------------------
# the trigger: the state it actually fires in
# ---------------------------------------------------------------------------
@needs_git
def test_the_trigger_returns_a_modified_tracked_file_and_a_new_untracked_one(repo: Path) -> None:
    """The two halves the published command missed, asserted together.

    They are one test on purpose. Dropping the revision range repairs the first
    half and leaves the second exactly as broken, and the round that found this
    introduced its headline document as a new file.
    """
    _write(repo, "README.md", "front page, rewritten this round\n")
    _write(repo, "docs/POSITIONING.md", "a brand new page nobody has committed\n")

    assert _git(repo, "status", "--porcelain").strip(), "the mutation did not dirty the tree"
    assert sr.trigger_a(repo) == ["README.md", "docs/POSITIONING.md"]


@needs_git
def test_the_trigger_returns_nothing_on_a_clean_tree(repo: Path) -> None:
    """A trigger that cannot return nothing is not a trigger."""
    assert sr.trigger_a(repo) == []


@needs_git
def test_the_trigger_returns_nothing_when_only_excluded_files_changed(repo: Path) -> None:
    """The exclusions are the half a mid-round transcript cannot demonstrate.

    Historical records, scoped notes, the policy's own machine state and source
    code all change constantly. If any of them fired the trigger, every round
    would owe a cold read and the policy would be ignored within two of them.
    """
    _write(repo, "docs/DECISIONS.md", "a new D-record\n")
    _write(repo, "docs/AUDIT-2026-08.md", "an audit revision\n")
    _write(repo, "docs/notes/w11.md", "a note revision\n")
    _write(repo, "docs/cold-reads.toml", "# a finding was re-affirmed\n")
    _write(repo, "src/acronymkit/__init__.py", "# a code change\n")
    _write(repo, "docs/notes/new-note.md", "an untracked note\n")

    assert _git(repo, "status", "--porcelain").strip(), "the mutation did not dirty the tree"
    assert sr.trigger_a(repo) == []


@needs_git
def test_the_superseded_command_returns_nothing_in_the_tree_the_trigger_reads_two_files_from(
    repo: Path,
) -> None:
    """The defect, pinned rather than described.

    This is the whole reason section 3 was rewritten, and it is the assertion a
    future round would have to delete on purpose in order to reintroduce the
    range. The middle case matters as much as the first: removing the range is
    the obvious repair and it still misses the new file.
    """
    _write(repo, "README.md", "front page, rewritten this round\n")
    _write(repo, "docs/POSITIONING.md", "a brand new page nobody has committed\n")
    pathspec = list(sr.PATHSPEC)

    empty_range = _git(repo, "diff", "--name-only", "HEAD..HEAD", "--", *pathspec)
    no_range = _git(repo, "diff", "--name-only", "--", *pathspec)

    assert empty_range.split() == [], "the superseded command is no longer blind; re-read D-072"
    assert no_range.split() == ["README.md"], "dropping the range should still miss the new file"
    assert sr.trigger_a(repo) == ["README.md", "docs/POSITIONING.md"]


@needs_git
def test_the_trigger_sees_the_line_pypi_renders(repo: Path) -> None:
    """``pyproject.toml`` is in the pathspec because its ``description`` is that line."""
    _write(repo, "pyproject.toml", '[project]\nname = "fixture"\ndescription = "rewritten"\n')
    assert sr.trigger_a(repo) == ["pyproject.toml"]


@needs_git
def test_a_renamed_document_reports_both_of_its_paths(repo: Path) -> None:
    """A rename is two facts: a page to read, and a link elsewhere that now dangles."""
    _git(repo, "mv", "docs/EVALUATION.md", "docs/MEASUREMENTS.md")
    assert sr.trigger_a(repo) == ["docs/EVALUATION.md", "docs/MEASUREMENTS.md"]


@needs_git
def test_a_path_with_a_space_survives_the_parse(repo: Path) -> None:
    """The reason the tool passes ``-z``.

    Without it git quotes any path holding a space or a non-ASCII byte, and a
    naive split hands back a name with quotation marks welded to it -- which
    would then fail every existence check downstream for a reason nobody could
    read.
    """
    _write(repo, "docs/a new page.md", "spaces in the name\n")
    assert sr.trigger_a(repo) == ["docs/a new page.md"]


@needs_git
def test_a_deleted_document_still_reaches_the_reader(repo: Path) -> None:
    """A round that removes a user-facing page has changed one, and owes a read of the removal."""
    (repo / "docs" / "EVALUATION.md").unlink()
    assert sr.trigger_a(repo) == ["docs/EVALUATION.md"]


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("README.md", True),
        ("CHANGELOG.md", True),
        ("CONTRIBUTING.md", True),
        ("SECURITY.md", True),
        ("pyproject.toml", True),
        ("docs/POSITIONING.md", True),
        ("docs/notes/w11.md", False),
        ("docs/DECISIONS.md", False),
        ("docs/AUDIT-2026-08.md", False),
        ("docs/cold-reads.toml", False),
        ("src/acronymkit/__init__.py", False),
        ("bench/results.json", False),
        (".github/workflows/ci.yml", False),
        ("", False),
    ],
)
def test_the_user_facing_filter(path: str, expected: bool) -> None:
    assert sr.is_user_facing(path) is expected


def test_windows_separators_do_not_smuggle_an_excluded_file_through() -> None:
    """``git`` reports forward slashes; a caller passing a native path must not fool the filter."""
    assert sr.is_user_facing("docs\\notes\\w11.md") is False
    assert sr.is_user_facing("docs\\POSITIONING.md") is True


# ---------------------------------------------------------------------------
# in situ: this checkout, read-only
# ---------------------------------------------------------------------------
@needs_checkout
def test_the_trigger_misses_nothing_git_plumbing_can_see_in_this_checkout() -> None:
    """The in-situ half, and it asserts a direction rather than an equality.

    The old command's failure was **under**-reporting, so the assertion that
    matters is that the trigger is a superset of what a different family of git
    commands sees. ``git status`` is the porcelain; ``git ls-files`` and
    ``git diff --cached`` are plumbing, and they do not share a code path with
    the porcelain's rename detection or its untracked walk.

    The equality is deliberately not asserted: this tree is edited by other
    workstreams while the suite runs, so an equality would be flaky for a reason
    unrelated to the trigger.
    """
    plumbing: List[str] = []
    for args in (
        ("ls-files", "--modified"),
        ("ls-files", "--others", "--exclude-standard"),
        ("ls-files", "--deleted"),
        ("diff", "--name-only", "--cached"),
    ):
        plumbing.extend(_git(REPO_ROOT, *args).splitlines())
    expected = {p.strip() for p in plumbing if sr.is_user_facing(p.strip())}

    reported = set(sr.trigger_a(REPO_ROOT))
    assert expected <= reported, f"the trigger did not report {sorted(expected - reported)}"
    assert all(sr.is_user_facing(name) for name in reported)


@needs_checkout
def test_every_pathspec_root_exists_in_this_repository() -> None:
    """A pathspec naming a path that is not here matches nothing and fails silently."""
    missing = [name for name in sr.PATHSPEC if not (REPO_ROOT / name).exists()]
    assert not missing, f"the trigger pathspec names paths this repository does not have: {missing}"


# ---------------------------------------------------------------------------
# the policy page: rotation set, cursor, and the command it publishes
# ---------------------------------------------------------------------------
def _policy_text() -> str:
    return POLICY.read_text(encoding="utf-8")


@needs_checkout
def test_the_rotation_reaches_every_user_facing_file_in_this_repository() -> None:
    """The rotation is checked against the tree, not against itself.

    A set checked only against itself agrees with itself perfectly. Deleting an
    entry from the block was invisible to every other assertion here: the
    survivors all existed, none repeated, and the cursor still resolved. This is
    the direction that catches it, and it also catches the case that motivated
    the last amendment -- a new user-facing page no trigger could ever serve.
    """
    rotation = sr.parse_rotation(_policy_text())
    unreachable = [name for name in sr.user_facing_files(REPO_ROOT) if name not in rotation]
    assert not unreachable, f"no trigger can ever reach: {unreachable}"


@needs_checkout
def test_the_user_facing_enumeration_is_not_empty_and_excludes_the_records() -> None:
    """ANTI-VACUITY for the rule above: an enumeration returning nothing satisfies it."""
    found = sr.user_facing_files(REPO_ROOT)
    assert "README.md" in found and "docs/POSITIONING.md" in found
    assert "docs/DECISIONS.md" not in found
    assert "docs/cold-reads.toml" not in found
    assert not any(name.startswith("docs/notes/") for name in found)
    assert not any(name.startswith("docs/AUDIT-") for name in found)


def test_every_in_page_anchor_on_the_policy_page_resolves() -> None:
    """Check C5 -- follow the pointer -- aimed at the page that publishes C5.

    The only mechanical defect the second read found in eleven thousand words of
    ``docs/GOVERNED_NAMING.md`` was a broken in-page anchor, and nothing in this
    repository looks for one. This page grew four sections' worth of
    cross-references in the round that made it executable, which is exactly when
    that class appears.
    """
    text = _policy_text()
    slugs = set()
    for line in text.splitlines():
        if line.startswith("#"):
            title = line.lstrip("#").strip().lower()
            slugs.add(re.sub(r"[^a-z0-9 -]", "", title).replace(" ", "-"))
    assert slugs, "no headings were parsed; this test would pass vacuously"
    broken = [a for a in re.findall(r"\]\(#([^)]+)\)", text) if a not in slugs]
    assert not broken, f"these in-page anchors resolve to no heading: {broken}"


def test_the_rotation_set_parses_and_every_entry_is_in_the_tree() -> None:
    rotation = sr.parse_rotation(_policy_text())
    assert rotation, "an empty rotation set would make every check below vacuous"
    assert len(rotation) == len(set(rotation)), "the rotation set repeats a file"
    missing = [name for name in rotation if not (REPO_ROOT / name).exists()]
    assert not missing, f"the rotation names files that are not here: {missing}"


def test_the_policy_page_holds_exactly_one_rotation_block() -> None:
    """The set was restated in section 8, and the two copies had already diverged.

    Section 8 recorded the amendment appending ``docs/POSITIONING.md``; section 3
    never got it; the page told a reader fourteen while its own section 8 said
    fifteen. One copy, parsed.
    """
    text = _policy_text()
    assert text.count(sr._ROTATION_FENCE) == 1
    assert text.count(sr._CURSOR_FENCE) == 1
    assert text.count(sr._TRIGGER_FENCE) == 1


def test_the_published_pathspec_is_the_pathspec_the_tool_runs() -> None:
    """Check C6 of the protocol, aimed at the protocol.

    A prose claim about a tool's configuration is unguarded by construction, and
    the last one on this page cost a round. This is the guard.
    """
    assert tuple(sr.parse_trigger_pathspec(_policy_text())) == sr.PATHSPEC


def test_the_cursor_parses_and_names_a_rotation_entry_that_exists() -> None:
    text = _policy_text()
    cursor = sr.parse_cursor(text)
    assert cursor in sr.parse_rotation(text)
    assert (REPO_ROOT / cursor).exists()


@needs_parser
@needs_ledger
def test_the_cursor_on_the_page_is_the_one_the_ledger_derives() -> None:
    """The policy's only state, checked against the record instead of remembered."""
    text = _policy_text()
    ledger = sr.load(LEDGER)
    newest = ledger.newest_read
    assert newest is not None, "the ledger records no cold read at all"
    assert sr.parse_cursor(text) == newest.cursor_after
    assert newest.cursor_after == sr.successor(sr.parse_rotation(text), newest.rotation_served)


@pytest.mark.parametrize(
    ("rotation", "name", "expected"),
    [
        (["a", "b", "c"], "a", "b"),
        (["a", "b", "c"], "b", "c"),
        (["a", "b", "c"], "c", "a"),
    ],
)
def test_the_cursor_rule_is_rotation_order_and_it_wraps(
    rotation: List[str], name: str, expected: str
) -> None:
    assert sr.successor(rotation, name) == expected


def test_the_cursor_rule_refuses_a_file_that_is_not_in_the_rotation() -> None:
    with pytest.raises(sr.SecondReaderError):
        sr.successor(["a", "b"], "c")


# ---------------------------------------------------------------------------
# the ledger: shape
# ---------------------------------------------------------------------------
_MINIMAL_LEDGER = """
[ledger]
schema_version = 1
policy = "docs/SECOND-READER.md"

[[reads]]
id = "2026-01-01"
reader = "r1"
rotation_served = ""
cursor_after = "A.md"
note = "the first read; trigger B did not exist yet"
"""


@needs_parser
def test_a_minimal_ledger_loads(tmp_path: Path) -> None:
    path = tmp_path / "cold-reads.toml"
    path.write_text(_MINIMAL_LEDGER, encoding="utf-8")
    ledger = sr.load(path)
    assert ledger.schema_version == 1
    assert [r.id for r in ledger.reads] == ["2026-01-01"]


@needs_parser
@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("[ledger]\nschema_version = 1\n[oops]\nx = 1\n", "unknown top-level"),
        ('[[reads]]\nid = "x"\n', "no [ledger] table"),
        ("[nope]\nx = 1\n", "unknown top-level"),
        ("[ledger]\nschema_version = 1\nwat = 2\n", "unknown key"),
        ('[ledger]\nschema_version = "one"\n', "must be an integer"),
        (_MINIMAL_LEDGER + '[[reads]]\nid = "x"\n', "missing required key"),
        (_MINIMAL_LEDGER.replace('reader = "r1"', 'reader = "r1"\nwat = 1'), "unknown key"),
        (_MINIMAL_LEDGER.replace('reader = "r1"', "reader = 1"), "must be a string"),
        (_MINIMAL_LEDGER.replace('cursor_after = "A.md"', "cursor_after = 1"), "must be a string"),
        (_MINIMAL_LEDGER + "covered = 1\n", "covered must be a list"),
        ("[ledger\n", "not valid TOML"),
    ],
)
def test_the_loader_refuses_a_malformed_ledger(tmp_path: Path, text: str, fragment: str) -> None:
    """A typo that is swallowed is a field that silently does not exist.

    ``bench/splits.toml`` records the same argument about a misspelt
    ``laps_trigger``: an unknown key must be an error, or the schema is advisory.
    """
    path = tmp_path / "cold-reads.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(sr.SecondReaderError) as raised:
        sr.load(path)
    assert fragment in str(raised.value)


@needs_parser
def test_the_loader_refuses_a_ledger_that_is_not_there(tmp_path: Path) -> None:
    """Absent is an error, not a pass. A validator that succeeds because it could
    not read the file is the defect every register here exists to refuse."""
    with pytest.raises(sr.SecondReaderError) as raised:
        sr.load(tmp_path / "nothing.toml")
    assert "does not exist" in str(raised.value)


@needs_parser
def test_a_findings_line_number_must_be_an_integer(tmp_path: Path) -> None:
    path = tmp_path / "cold-reads.toml"
    path.write_text(
        _MINIMAL_LEDGER
        + """
[[findings]]
id = "F-1"
raised_in = "2026-01-01"
reviewed_in = "2026-01-01"
file = "A.md"
line = "twelve"
quote = "q"
refutation = "r"
owner = "unowned"
disposition = "open"
""",
        encoding="utf-8",
    )
    with pytest.raises(sr.SecondReaderError) as raised:
        sr.load(path)
    assert "line must be an integer" in str(raised.value)


# ---------------------------------------------------------------------------
# the ledger: semantics, one mutation per rule
# ---------------------------------------------------------------------------
#: Real user-facing names, because the completeness rule reads the tree: the
#: rotation must reach every user-facing file that exists, so a synthetic root
#: full of ``A.md`` would make that rule vacuous in every test below.
ROTATION = ["README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "docs/SECOND-READER.md"]

#: A user-facing name the synthetic root deliberately does NOT hold, for the
#: mutations that need a rotation entry or a cursor pointing at nothing.
ABSENT = "docs/GATES.md"


def _synthetic_policy(
    rotation: Sequence[str] = tuple(ROTATION),
    cursor: str = "CHANGELOG.md",
    pathspec: Optional[Sequence[str]] = None,
) -> str:
    spec = " ".join(pathspec if pathspec is not None else sr.PATHSPEC)
    return (
        f"{sr._TRIGGER_FENCE}\n```\ngit status --porcelain -- {spec}\n```\n\n"
        f"{sr._ROTATION_FENCE}\n```\n" + " · ".join(rotation) + "\n```\n\n"
        f"{sr._CURSOR_FENCE}\n```\ncursor {cursor}\n```\n"
    )


def _synthetic_root(tmp_path: Path) -> Path:
    """A tree holding exactly the rotation, so the completeness rule is satisfiable.

    Nothing else user-facing is created: no ``pyproject.toml``, no other
    ``docs/*.md``. Any extra would make every base-is-clean assertion below fail
    on the completeness rule rather than on the thing under test.
    """
    root = tmp_path / "tree"
    (root / "docs").mkdir(parents=True)
    for name in ROTATION:
        (root / name).write_text("x\n", encoding="utf-8")
    return root


def _base_ledger(tmp_path: Path) -> sr.Ledger:
    """Two reads and three findings, one per disposition that has a required field."""
    return sr.Ledger(
        path=tmp_path / "cold-reads.toml",
        schema_version=1,
        policy="docs/SECOND-READER.md",
        reads=[
            sr.Read(
                id="2026-01-01",
                reader="r1",
                rotation_served="",
                cursor_after="README.md",
                note="the first read; trigger B did not exist yet",
            ),
            sr.Read(
                id="2026-02-01",
                reader="r2",
                rotation_served="README.md",
                cursor_after="CHANGELOG.md",
                note="served what the cursor pointed at",
            ),
        ],
        findings=[
            sr.Finding(
                id="F-1",
                raised_in="2026-02-01",
                reviewed_in="2026-02-01",
                file="README.md",
                line=12,
                quote="a sentence",
                refutation="a command",
                owner="unowned",
                disposition="open",
            ),
            sr.Finding(
                id="F-2",
                raised_in="2026-01-01",
                reviewed_in="2026-02-01",
                file="CHANGELOG.md",
                line=1,
                quote="a sentence",
                refutation="a command",
                owner="unowned",
                disposition="blocked",
                blocked_on="D-999",
            ),
            sr.Finding(
                id="F-3",
                raised_in="2026-01-01",
                reviewed_in="2026-02-01",
                file="CONTRIBUTING.md",
                line=0,
                quote="a sentence",
                refutation="a command",
                owner="w1",
                disposition="fixed",
                applied_by="somebody-who-is-not-r1",
                applied_in="round 7",
            ),
        ],
    )


def test_the_base_ledger_is_clean(tmp_path: Path) -> None:
    """ANTI-VACUITY. Every mutation below is meaningless if the base is already red."""
    root = _synthetic_root(tmp_path)
    assert sr.validate(_base_ledger(tmp_path), _synthetic_policy(), root) == []


def _swap_read(ledger: sr.Ledger, index: int, **changes: object) -> sr.Ledger:
    ledger.reads[index] = replace(ledger.reads[index], **changes)  # type: ignore[arg-type]
    return ledger


def _swap_finding(ledger: sr.Ledger, index: int, **changes: object) -> sr.Ledger:
    ledger.findings[index] = replace(ledger.findings[index], **changes)  # type: ignore[arg-type]
    return ledger


LedgerMutation = Callable[["sr.Ledger"], "sr.Ledger"]


def _a_third_read_arrives_and_nobody_applied_f2(ledger: sr.Ledger) -> sr.Ledger:
    """The escalation needs a third read to reach, which is the whole point of it.

    ``F-2`` was raised at the first read. At the second it is still allowed to be
    open -- that is the grace the limit buys. At the third it is not, and the
    only ways off ``open`` all require somebody to have written down a name or a
    reason.
    """
    ledger.reads.append(
        sr.Read(
            id="2026-03-01",
            reader="r3",
            rotation_served="CHANGELOG.md",
            cursor_after="CONTRIBUTING.md",
            note="served what the cursor pointed at",
        )
    )
    return _swap_finding(ledger, 1, disposition="open", blocked_on="", reviewed_in="2026-03-01")


#: (name, mutation, fragment the refusal must contain). One row per rule.
_LEDGER_MUTATIONS: List[Tuple[str, LedgerMutation, str]] = [
    ("read id is not a date", lambda ledg: _swap_read(ledg, 1, id="soon"), "must be an ISO date"),
    (
        "two reads share an id",
        lambda ledg: _swap_read(ledg, 1, id="2026-01-01"),
        "duplicate read id",
    ),
    (
        "reads are out of order",
        lambda ledg: _swap_read(ledg, 0, id="2026-03-01"),
        "ascending date order",
    ),
    ("the reader is unnamed", lambda ledg: _swap_read(ledg, 1, reader="  "), "reader is empty"),
    (
        "the cursor left points outside the rotation",
        lambda ledg: _swap_read(ledg, 1, cursor_after=ABSENT),
        "is not in the rotation set",
    ),
    (
        "trigger B served a file outside the rotation",
        lambda ledg: _swap_read(ledg, 1, rotation_served=ABSENT),
        "is not in the rotation set",
    ),
    (
        "the cursor is not the rotation successor",
        lambda ledg: _swap_read(
            ledg, 1, rotation_served="CHANGELOG.md", cursor_after="CHANGELOG.md"
        ),
        "rotation order after",
    ),
    (
        "trigger B ignored the cursor it was handed",
        lambda ledg: _swap_read(
            ledg, 1, rotation_served="CHANGELOG.md", cursor_after="CONTRIBUTING.md"
        ),
        "The cursor is followed, not announced",
    ),
    (
        "trigger B did not fire and nothing says why",
        lambda ledg: _swap_read(ledg, 0, note="   "),
        "no note says why trigger B did not fire",
    ),
    (
        "two findings share an id",
        lambda ledg: _swap_finding(ledg, 1, id="F-1"),
        "duplicate finding id",
    ),
    (
        "a finding was raised in a read nobody declared",
        lambda ledg: _swap_finding(ledg, 0, raised_in="2025-01-01"),
        "names no declared read",
    ),
    (
        "a finding was reviewed in a read nobody declared",
        lambda ledg: _swap_finding(ledg, 1, reviewed_in="2025-01-01"),
        "names no declared read",
    ),
    (
        "a finding was reviewed before it was raised",
        lambda ledg: _swap_finding(ledg, 0, reviewed_in="2026-01-01"),
        "precedes raised_in",
    ),
    (
        "the sentence is not quoted",
        lambda ledg: _swap_finding(ledg, 0, quote=" "),
        "quote is empty",
    ),
    (
        "the finding has no refutation",
        lambda ledg: _swap_finding(ledg, 0, refutation=""),
        "is an opinion",
    ),
    ("nobody owns it, not even nobody", lambda ledg: _swap_finding(ledg, 0, owner=""), "owner is"),
    ("a negative line number", lambda ledg: _swap_finding(ledg, 0, line=-1), "line must be zero"),
    (
        "an invented disposition",
        lambda ledg: _swap_finding(ledg, 0, disposition="wontfix"),
        "is not one of",
    ),
    (
        "fixed with nobody named as having applied it",
        lambda ledg: _swap_finding(ledg, 2, applied_by=""),
        "fixed requires applied_by",
    ),
    (
        "THE READ-ONLY BOUNDARY: the reader closed its own finding",
        lambda ledg: _swap_finding(ledg, 2, applied_by="r1"),
        "The cold reader reports; somebody else applies",
    ),
    (
        "fixed with no round or commit named",
        lambda ledg: _swap_finding(ledg, 2, applied_in=" "),
        "fixed requires applied_in",
    ),
    (
        "blocked on nothing in particular",
        lambda ledg: _swap_finding(ledg, 1, blocked_on=""),
        "blocked requires blocked_on",
    ),
    (
        "permanent with no reason",
        lambda ledg: _swap_finding(ledg, 1, disposition="permanent", blocked_on=""),
        "permanent requires reason",
    ),
    (
        "THE DISPOSITION RULE: an open finding nobody re-affirmed",
        lambda ledg: _swap_finding(ledg, 0, reviewed_in="2026-01-01", raised_in="2026-01-01"),
        "re-affirmed at every cold read",
    ),
    (
        "THE ESCALATION: open across more reads than the limit",
        _a_third_read_arrives_and_nobody_applied_f2,
        "It does not stay open",
    ),
    (
        "a finding about a file that is not there",
        lambda ledg: _swap_finding(ledg, 0, file="docs/GONE.md"),
        "is not in the tree",
    ),
]


@pytest.mark.parametrize(
    ("mutation", "fragment"),
    [pytest.param(m, f, id=name) for name, m, f in _LEDGER_MUTATIONS],
)
def test_the_validator_refuses(tmp_path: Path, mutation: LedgerMutation, fragment: str) -> None:
    root = _synthetic_root(tmp_path)
    problems = sr.validate(mutation(_base_ledger(tmp_path)), _synthetic_policy(), root)
    assert any(fragment in problem for problem in problems), (
        f"expected a refusal containing {fragment!r}; got {problems}"
    )


def test_open_at_exactly_the_limit_is_allowed(tmp_path: Path) -> None:
    """The other direction, and it is the half that makes the rule a limit rather than a ban.

    A finding raised at one read and still open at the next is inside the grace.
    Without this, the escalation test above would also pass against a validator
    that simply refused every open finding, which would refuse the first entry
    anybody ever wrote.
    """
    root = _synthetic_root(tmp_path)
    ledger = _swap_finding(_base_ledger(tmp_path), 1, disposition="open", blocked_on="")
    assert sr.validate(ledger, _synthetic_policy(), root) == []


@pytest.mark.parametrize(
    ("policy", "fragment"),
    [
        pytest.param(
            _synthetic_policy(rotation=[ROTATION[0], *ROTATION]),
            "duplicate entr",
            id="the rotation repeats a file",
        ),
        pytest.param(
            _synthetic_policy(rotation=[*ROTATION, "docs/GONE.md"]),
            "trigger B cannot serve it",
            id="the rotation names a file that is not there",
        ),
        pytest.param(
            _synthetic_policy(rotation=ROTATION[:-1]),
            "no trigger can ever reach",
            id="THE MUTATION THAT GOT THROUGH: the rotation quietly loses an entry",
        ),
        pytest.param(
            _synthetic_policy(cursor=ABSENT),
            "is not in the rotation set",
            id="the cursor points outside the rotation",
        ),
        pytest.param(
            _synthetic_policy(cursor="SECURITY.md"),
            "exactly one failure mode",
            id="the page and the ledger disagree about the cursor",
        ),
        pytest.param(
            _synthetic_policy(pathspec=["README.md", "docs"]),
            "returned nothing at the moment it fired",
            id="the published pathspec is narrower than the one the tool runs",
        ),
        pytest.param(
            f"{sr._TRIGGER_FENCE}\n```\ngit status --porcelain\n```\n"
            f"{sr._ROTATION_FENCE}\n```\nA.md\n```\n{sr._CURSOR_FENCE}\n```\ncursor A.md\n```\n",
            "no `--` pathspec",
            id="the published command has no pathspec at all",
        ),
        pytest.param(
            f"{sr._ROTATION_FENCE}\n```\n\n```\n",
            "pass vacuously",
            id="the rotation block is empty",
        ),
        pytest.param(
            f"{sr._ROTATION_FENCE}\n```\nA.md\n```\n{sr._ROTATION_FENCE}\n```\nB.md\n```\n",
            "appears more than once",
            id="the page holds two rotation blocks",
        ),
        pytest.param("no markers here at all\n", "is not in the page", id="the marker is gone"),
    ],
)
def test_the_validator_refuses_a_broken_policy_page(
    tmp_path: Path, policy: str, fragment: str
) -> None:
    root = _synthetic_root(tmp_path)
    problems = sr.validate(_base_ledger(tmp_path), policy, root)
    assert any(fragment in problem for problem in problems), (
        f"expected a refusal containing {fragment!r}; got {problems}"
    )


# ---------------------------------------------------------------------------
# the register this repository actually ships
# ---------------------------------------------------------------------------
@needs_parser
@needs_ledger
def test_the_shipped_ledger_and_the_shipped_policy_validate() -> None:
    assert sr.validate(sr.load(LEDGER), _policy_text(), REPO_ROOT) == []


@needs_parser
@needs_ledger
def test_the_shipped_ledger_is_not_empty() -> None:
    """ANTI-VACUITY. Every rule above passes trivially over no findings at all."""
    ledger = sr.load(LEDGER)
    assert ledger.reads, "no cold read is recorded; the policy has never run"
    assert ledger.findings, "no finding is recorded; the hand-off has nothing to hand off"


@needs_parser
@needs_ledger
def test_no_finding_names_a_reader_as_having_applied_its_own_report() -> None:
    """Stated separately from the validator, because it is the point of the file."""
    ledger = sr.load(LEDGER)
    for finding in ledger.findings:
        if finding.disposition == "fixed":
            assert finding.applied_by != ledger.reader_of(finding.raised_in)


# ---------------------------------------------------------------------------
# the gate list the protocol tells a reader to run
# ---------------------------------------------------------------------------
def _documented_gate_commands() -> List[str]:
    """The fenced command block under ``## The gates`` in ``CONTRIBUTING.md``."""
    text = CONTRIBUTING.read_text(encoding="utf-8")
    at = text.index("## The gates")
    opening = text.index("```", at)
    body_start = text.index("\n", opening)
    closing = text.index("```", body_start)
    return [line.strip() for line in text[body_start:closing].splitlines() if line.strip()]


@pytest.mark.skipif(not CONTRIBUTING.is_file(), reason="not a source checkout")
def test_every_gate_the_contributing_guide_publishes_can_actually_be_run() -> None:
    """Protocol question 3 says *run them*. This asserts they are runnable.

    A published command that does not execute is the defect class this whole
    policy exists to catch, and section 4.1 of the policy page had the count
    wrong -- it said six, and the ``lint`` job runs seven.
    """
    commands = _documented_gate_commands()
    assert len(commands) >= 7, f"the gate block lists {len(commands)} commands; CI runs seven"
    assert any("tools/gates.py --check" in c for c in commands), (
        "python tools/gates.py --check runs in the lint job and belongs in this list"
    )
    for command in commands:
        tokens = command.split()
        assert tokens[0] == "python", command
        if tokens[1] == "-m":
            assert importlib.util.find_spec(tokens[2]) is not None, f"{tokens[2]} is not importable"
            continue
        script = REPO_ROOT / tokens[1]
        assert script.is_file(), f"{command}: {tokens[1]} is not in the tree"
        flags = [t for t in tokens[2:] if t.startswith("--")]
        completed = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, f"{command}: --help exited {completed.returncode}"
        help_text = completed.stdout.decode("utf-8", "replace")
        for flag in flags:
            assert flag in help_text, f"{command}: {flag} is not a flag {tokens[1]} accepts"


# ---------------------------------------------------------------------------
# the CLI
# ---------------------------------------------------------------------------
@needs_parser
@needs_ledger
@needs_checkout
def test_the_check_command_is_green_on_this_tree(capsys: pytest.CaptureFixture[str]) -> None:
    assert sr.main(["--check"]) == 0
    printed = capsys.readouterr().out
    assert "OPEN AND AT THE LIMIT" in printed, "the count that makes the escalation visible is gone"


@needs_parser
def test_the_check_command_is_red_on_a_ledger_that_is_not_there(tmp_path: Path) -> None:
    """The positive control for the command a CI job would run."""
    assert sr.main(["--check", "--ledger", str(tmp_path / "nothing.toml")]) == 1


@needs_git
def test_the_trigger_command_prints_the_files(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(repo, "README.md", "changed\n")
    assert sr.main(["--trigger", "--root", str(repo)]) == 0
    assert "README.md" in capsys.readouterr().out


@needs_git
def test_the_trigger_command_says_so_when_no_cold_read_is_due(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert sr.main(["--trigger", "--root", str(repo)]) == 0
    assert "no cold read is due" in capsys.readouterr().out


@needs_checkout
def test_the_cost_command_derives_the_corpus_rather_than_quoting_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 6's costing had drifted in all three figures, so it is computed now."""
    assert sr.main(["--cost"]) == 0
    printed = capsys.readouterr().out
    assert "the full user-facing corpus" in printed
    assert "the median file" in printed


@needs_parser
@needs_ledger
@needs_checkout
def test_every_command_the_policy_page_tells_a_reader_to_run_exits_zero() -> None:
    """Protocol check C3, aimed at the protocol: a pasted command is a claim.

    Every ``python tools/second_reader.py --<flag>`` this page publishes is run
    here. The page's previous published command returned an empty list at the
    only moment it fires and nothing noticed for a round, which is the entire
    reason this file exists.
    """
    published = sorted(
        set(re.findall(r"python tools/second_reader\.py (--[a-z-]+)", _policy_text()))
    )
    assert published, "the page publishes no command; this test would pass vacuously"
    assert {"--trigger", "--check"} <= set(published)
    for flag in published:
        completed = subprocess.run(
            [sys.executable, str(LOADER), flag],
            cwd=str(REPO_ROOT),
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, (
            f"the page publishes `python tools/second_reader.py {flag}` and it exited "
            f"{completed.returncode}: {completed.stderr.decode('utf-8', 'replace').strip()}"
        )


@needs_parser
@needs_ledger
def test_the_open_command_prints_the_apply_worklist(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """``--open`` must print a worklist when there is one and say so when there is not.

    This test used to assert the worklist header against the **live** ledger,
    which passed only while a backlog existed. It went red the first time the
    backlog was actually cleared -- a test that fails when the thing it guards
    starts working, which is the same family as a check that cannot fail where it
    runs, inverted. Both branches are now driven from fixtures, so the live
    ledger's state is not part of the assertion.
    """
    # The empty branch: whatever the live ledger holds, an all-fixed ledger says so.
    empty = tmp_path / "none.toml"
    empty.write_text(
        LEDGER.read_text(encoding="utf-8").replace(
            'disposition = "open"', 'disposition = "permanent"'
        ),
        encoding="utf-8",
    )
    assert sr.main(["--open", "--ledger", str(empty)]) == 0
    assert "no open findings" in capsys.readouterr().out

    # The populated branch. Splicing the live ledger was tried first and made
    # invalid TOML: a line filter aimed at one finding reaches every finding.
    # APPENDING one synthetic finding cannot corrupt what is already there, and
    # it is the only shape that stays valid however the real ledger grows.
    populated = tmp_path / "one.toml"
    synthetic = NL.join(
        [
            "",
            "[[findings]]",
            'id = "F-fixture-01"',
            'raised_in = "2026-08-26"',
            'reviewed_in = "2026-08-26"',
            'file = "docs/EVALUATION.md"',
            "line = 1",
            'quote = "a sentence that exists only in this fixture"',
            'refutation = "synthetic; this finding is constructed by a test"',
            'owner = "unowned"',
            'disposition = "open"',
            "",
        ]
    )
    populated.write_text(LEDGER.read_text(encoding="utf-8") + synthetic, encoding="utf-8")
    assert sr.main(["--open", "--ledger", str(populated)]) == 0
    printed = capsys.readouterr().out
    assert "open finding(s) -- the apply worklist" in printed
    assert "F-fixture-01" in printed, "the worklist must name the finding, not just count it"
