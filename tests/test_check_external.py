"""``tools/check_external.py`` must be able to fail, and must not fire on this project.

Two properties, and the second one decides whether the gate survives contact
with a maintainer. A prose linter that reddens the build on every sentence
containing the word *published* is a linter somebody disables in the round after
the one that shipped it, and the disabling commit will be right.

So this file pins both directions:

* **It fires.** An appeal to an externally published figure with no source and
  no read date is a problem, in a fixture and -- in the last class -- in the real
  tree, through the real command, which is what operating rule 11 asks for.
* **It does not fire on us.** Every construction in this repository that talks
  about *our* published numbers is pinned as silent: "the published curve", "the
  published objective", "published metadata", "published as 9,370 of 25,210
  source lines", "unpublished for three releases", and the one that was a real
  false positive during construction -- "3.65% is published as a lower bound with
  the strict figure beside it", which fired because the appeal expression is
  compiled ``IGNORECASE`` and a bare ``[A-Z]`` therefore matched an unbounded run
  of lowercase words.

The blind spots are pinned too, as **passing** tests with names that say what is
not covered. A hole nothing asserts is a hole the next reader rediscovers.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_PATH = REPO_ROOT / "tools" / "check_external.py"


def _load_tool() -> ModuleType:
    """Import ``tools/check_external.py`` by path.

    ``tools/`` is a directory of scripts and must not become a package for a
    test's convenience -- same mechanism and same reasoning as
    ``tests/test_splits_manifest.py`` and ``tests/test_check_claims.py``.
    """
    spec = importlib.util.spec_from_file_location("_check_external_under_test", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if not TOOL_PATH.is_file():  # pragma: no cover - installed-distribution job only
    pytest.skip(
        "tools/ is not part of an installed distribution; these tests belong to a checkout",
        allow_module_level=True,
    )

external = _load_tool()


def _tree(tmp_path: Path, body: str, name: str = "README.md") -> Path:
    """A one-file tree the tool can be pointed at with ``--root``."""
    (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / name).write_text(body, encoding="utf-8")
    return tmp_path


#: An appeal that must fire: an outside publication, a figure, no citation.
_UNCITED = "The paper reports 91.4 % on the same corpus, which is where our number comes from.\n"

#: The same sentence, cited to R4's shape.
_CITED = (
    "The paper reports 91.4 % on the same corpus, which is where our number comes "
    "from.<!--external: Smith et al., Table 3 | read 2026-08-25-->\n"
)


class TestItFires:
    """The gate detects the defect it was built for."""

    def test_an_uncited_external_figure_is_a_problem(self, tmp_path: Path) -> None:
        problems = external.check(_tree(tmp_path, _UNCITED))
        assert len(problems) == 1, problems
        assert "no source and no read date" in problems[0]
        assert "91.4 %" in problems[0]

    def test_a_marker_with_a_source_and_a_read_date_is_accepted(self, tmp_path: Path) -> None:
        assert external.check(_tree(tmp_path, _CITED)) == []

    def test_a_source_with_no_read_date_is_refused(self, tmp_path: Path) -> None:
        """The half-compliance R4 exists for, and the half the tree already has.

        ``bench/run_disambiguation.py`` names its source -- "README.md of the
        pinned repository" -- and records no date anybody read it on. A source
        with no read date states a conclusion and destroys the evidence for it,
        which is the sentence operating rule 4 is made of.
        """
        body = _CITED.replace(" | read 2026-08-25", "")
        problems = external.check(_tree(tmp_path, body))
        assert len(problems) == 1, problems
        assert "read YYYY-MM-DD" in problems[0]

    def test_a_read_date_in_the_future_is_refused(self, tmp_path: Path) -> None:
        body = _CITED.replace("2026-08-25", "2099-01-01")
        problems = external.check(_tree(tmp_path, body))
        assert len(problems) == 1 and "in the future" in problems[0], problems

    def test_a_read_date_that_is_not_a_date_is_refused(self, tmp_path: Path) -> None:
        body = _CITED.replace("2026-08-25", "2026-13-45")
        problems = external.check(_tree(tmp_path, body))
        assert len(problems) == 1 and "not a real date" in problems[0], problems

    def test_an_appeal_split_across_a_hard_wrap_still_fires(self, tmp_path: Path) -> None:
        """Prose here wraps near column 100, so a line is the wrong unit.

        ``CHANGELOG.md`` puts "The published" at the end of one line and
        "Schwartz & Hearst range" at the start of the next. A line-keyed check
        reads neither half as an appeal.
        """
        body = "Both claimed too much. The published\nSchwartz & Hearst range is 86.5 % F1.\n"
        problems = external.check(_tree(tmp_path, body))
        assert len(problems) == 1 and "86.5 %" in problems[0], problems


class TestItDoesNotFireOnUs:
    """Every construction in this tree that is about *our* numbers stays silent.

    Each string here was taken from the repository, not invented. Together they
    are the reason the shipped gate fires three times where a phrase-only linter
    fired eighteen.
    """

    @pytest.mark.parametrize(
        "sentence",
        [
            # README.md and docs/DEFINITION-OF-DONE.md: our abstention curve.
            "No coverage level on the published curve wins until gate 0.15 exactly.",
            # docs/notes/scoring-objective.md: an external *formula*, not a figure.
            "Setting length_penalty to 0.0 recovers the published objective exactly.",
            # docs/notes/pydantic-cost.md: an external fact that is not a number.
            "That the sdist needs maturin and rustc 1.75 is read from the published metadata.",
            # docs/DECISIONS.md: our own source-line count.
            "The governed half was published as 9,370.5 of 25,210 source lines here.",
            # docs/RELEASE_CHECKLIST.md: 'unpublished for' contains 'published for'.
            "Why the package was unpublished for three releases, at 0.1.2 and after.",
            # The real false positive found during construction: IGNORECASE made
            # [A-Z] match lowercase, so 'as a lower bound with the strict' was
            # eaten as an attribution and 'figure' completed the pattern.
            "A first pass flagged 6.33% and 3.65% is published as a lower bound "
            "with the strict figure beside it.",
        ],
    )
    def test_a_sentence_about_this_project_is_not_an_external_appeal(
        self, tmp_path: Path, sentence: str
    ) -> None:
        assert external.check(_tree(tmp_path, sentence + "\n")) == [], sentence

    def test_a_figure_carrying_a_claim_citation_is_ours(self, tmp_path: Path) -> None:
        """A number with a run id attached appeals into ``bench/results.json``.

        Without this the gate would fire on any sentence that mentions an
        outside system beside one of our own cited figures, which is most of
        ``docs/EVALUATION.md``'s comparison prose.
        """
        body = (
            "The paper reports a comparable result and our own harness scores "
            "84.21<!--claim:extraction.med1250.acronymkit.exact_f1:.2f--> % on it.\n"
        )
        assert external.check(_tree(tmp_path, body)) == []


class TestTheHolesAreNamedRatherThanDiscovered:
    """Passing tests whose names are the coverage gaps.

    Every assertion in this class is that the gate is **silent**, and every one
    of them is a hole somebody could quote a coverage number over.
    """

    def test_a_code_spanned_figure_is_invisible(self, tmp_path: Path) -> None:
        """D-052's hole, inherited on purpose.

        Arming numbers inside backticks fires on every configuration value in
        the tree. ``CHANGELOG.md`` carries a live instance this cannot see:
        "The published Schwartz & Hearst range is ``~86-89 % F1 on Ab3P``".
        """
        body = "The published Schwartz & Hearst range is `~86-89 % F1 on Ab3P` there.\n"
        assert external.check(_tree(tmp_path, body)) == []

    def test_a_fenced_block_is_invisible(self, tmp_path: Path) -> None:
        body = "```\nThe paper reports 91.4 % on the same corpus.\n```\n"
        assert external.check(_tree(tmp_path, body)) == []

    def test_a_paraphrase_outside_the_vocabulary_is_invisible(self, tmp_path: Path) -> None:
        """The same class of hole ``check_claims`` has in its arming vocabulary.

        D-060 found that gate unable to see a latency claim. This one cannot see
        "the authors measured", "their system reaches", or any other phrasing
        nobody added to :data:`APPEAL_PATTERNS`.
        """
        body = "The authors measured 99.9 % on this corpus and we land near it.\n"
        assert external.check(_tree(tmp_path, body)) == []

    def test_runners_are_outside_the_scanned_set(self) -> None:
        """``bench/`` and ``tools/`` are not scanned, and ``--audit`` says so."""
        assert not any(glob.startswith("bench/run") for glob in external.SCAN_GLOBS)
        assert "bench/*.py" in external.AUDIT_GLOBS


class TestTheLedgerIsKeyedByContent:
    """A count-keyed ledger lets one uncited appeal be swapped for another."""

    def test_an_appeal_in_the_ledger_is_accepted(self, tmp_path: Path) -> None:
        root = _tree(tmp_path, _UNCITED)
        digest = external.scan(root)[0].digest
        saved = dict(external.UNCITED_LEDGER)
        try:
            external.UNCITED_LEDGER.clear()
            external.UNCITED_LEDGER["README.md"] = (digest,)
            assert external.check(root) == []
        finally:
            external.UNCITED_LEDGER.clear()
            external.UNCITED_LEDGER.update(saved)

    def test_a_different_appeal_at_the_same_count_is_still_a_problem(self, tmp_path: Path) -> None:
        """The property a per-file count cannot have.

        Swapping one uncited external appeal for a different one leaves the
        count unchanged. ``check_claims``'s deferred register has exactly this
        weakness and this gate declines to inherit it.
        """
        root = _tree(tmp_path, _UNCITED)
        digest = external.scan(root)[0].digest
        swapped = _tree(tmp_path, _UNCITED.replace("91.4 %", "88.2 %"))
        saved = dict(external.UNCITED_LEDGER)
        try:
            external.UNCITED_LEDGER.clear()
            external.UNCITED_LEDGER["README.md"] = (digest,)
            problems = external.check(swapped)
        finally:
            external.UNCITED_LEDGER.clear()
            external.UNCITED_LEDGER.update(saved)
        assert len(problems) == 2, problems
        assert any("no source and no read date" in problem for problem in problems)
        assert any("lowers the ledger in the same commit" in problem for problem in problems)

    def test_a_closed_appeal_must_leave_the_ledger_in_the_same_commit(self, tmp_path: Path) -> None:
        root = _tree(tmp_path, _CITED)
        saved = dict(external.UNCITED_LEDGER)
        try:
            external.UNCITED_LEDGER.clear()
            external.UNCITED_LEDGER["README.md"] = ("deadbeefcafe",)
            problems = external.check(root)
        finally:
            external.UNCITED_LEDGER.clear()
            external.UNCITED_LEDGER.update(saved)
        assert len(problems) == 1 and "deadbeefcafe" in problems[0], problems

    def test_the_digest_survives_a_reflow_and_not_a_word_change(self, tmp_path: Path) -> None:
        wrapped = _tree(tmp_path, "The paper reports 91.4 % on the same\ncorpus, which is ours.\n")
        flat = _tree(
            tmp_path / "flat", "The paper reports 91.4 % on the same corpus, which is ours.\n"
        )
        assert external.scan(wrapped)[0].digest == external.scan(flat)[0].digest
        changed = _tree(
            tmp_path / "changed", "The paper reports 91.5 % on the same corpus, which is ours.\n"
        )
        assert external.scan(changed)[0].digest != external.scan(flat)[0].digest


class TestTheLedgerMatchesThisTree:
    """The shipped ledger describes the tree it ships with.

    Both directions, because an entry nobody can reach is as bad as an appeal
    nobody has an entry for -- one of them is a comment claiming a defect exists.
    """

    def test_every_ledger_entry_names_a_live_appeal(self) -> None:
        live = external.ledger_literal(external.scan(REPO_ROOT))
        assert live == external.UNCITED_LEDGER, (
            "UNCITED_LEDGER and the tree disagree. Run "
            "'python tools/check_external.py --ledger' for the literal."
        )

    def test_the_uncited_appeals_are_the_three_this_round_measured(self) -> None:
        """Pinned so a silent change of population is visible.

        Three **uncited** armed appeals: one in ``docs/DECISIONS.md`` (a
        historical record), and two in ``docs/EVALUATION.md`` -- the live
        disambiguation baseline, and the retraction that quotes the sentence it
        withdraws. Deliberately keyed to the uncited population rather than to
        every armed appeal: a later round that *cites* a new external figure
        correctly has done the right thing and must not turn this red.
        """
        uncited = [appeal for appeal in external.scan(REPO_ROOT) if appeal.marker is None]
        assert len(uncited) == 3, [f"{a.path}:{a.line} {a.sentence[:60]}" for a in uncited]
        assert sorted({appeal.path for appeal in uncited}) == [
            "docs/DECISIONS.md",
            "docs/EVALUATION.md",
        ]


class TestTheGateCanFailWhereItRuns:
    """R11: run the real command, in the real tree, and make it fail.

    The classes above drive :func:`check` against fixtures. That is not the
    environment the gate runs in -- the tool resolves :data:`SCAN_GLOBS` against
    the repository root, so a fixture tree is a different thing under test. This
    class runs ``python tools/check_external.py`` from ``REPO_ROOT``, exactly as
    CI would, and the control above each mutation is the half without which a
    red run proves nothing.

    **It ADDS a file rather than editing one, and that is a correction to the
    house pattern rather than a preference.** ``tests/test_check_claims.py`` and
    ``tests/test_claims_gate_coverage.py`` both mutate a real document in place
    -- read the bytes, write a mutation, run the gate, write the bytes back.
    That is destructive under concurrency: a second process that reads the file
    inside the mutation window and writes it back afterwards silently keeps the
    injected text, and the restore silently discards whatever the second process
    wrote. It happened during construction of this file: an injected sentence
    survived a restore into ``docs/EVALUATION.md`` and had to be removed by hand.
    A probe file is additive -- nothing another process wrote can be lost, and a
    crashed run leaves an obviously-named untracked file rather than a corrupted
    document.

    **The cost of that choice, stated rather than discovered.** The probe lands
    inside ``docs/``, which the gate scans, so for the fraction of a second it
    exists a *concurrent* run of ``python tools/check_external.py`` sees it and
    reports one extra appeal. That was observed while this file was written. In
    CI the steps are sequential and the window does not exist; on a machine where
    two processes share one checkout it does. It is the strictly better half of
    the trade -- the in-place alternative has the same window and loses data in
    it -- and it is a reason not to read a count taken while a suite is running.
    """

    #: Inside ``docs/*.md``, so the real scan reaches it. Named so that a
    #: leftover from a crashed run is unmistakable in ``git status``.
    PROBE = REPO_ROOT / "docs" / "zz-gate-mutation-probe.md"

    def _gate(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(TOOL_PATH)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def _with_probe(self, body: str) -> subprocess.CompletedProcess:
        if not (REPO_ROOT / "docs").is_dir():  # pragma: no cover - checkout only
            pytest.skip("docs/ is not part of an installed distribution")
        assert not self.PROBE.exists(), (
            f"{self.PROBE.name} already exists; a previous run did not clean up and this "
            "test would be scoring somebody else's file"
        )
        try:
            self.PROBE.write_text(body, encoding="utf-8")
            return self._gate()
        finally:
            self.PROBE.unlink(missing_ok=True)

    def test_the_tree_without_the_probe_is_green(self) -> None:
        if not (REPO_ROOT / "docs").is_dir():  # pragma: no cover - checkout only
            pytest.skip("docs/ is not part of an installed distribution")
        completed = self._gate()
        assert completed.returncode == 0, completed.stdout + completed.stderr

    def test_an_uncited_appeal_in_a_new_document_reddens_the_real_gate(self) -> None:
        """A document added to SCAN_GLOBS cites from its first line.

        This is the exact sentence shape that stood in ``docs/EVALUATION.md``
        through six audits, two adversarial passes and four documentation
        sweeps: an outside publication, a figure, and an argument about this
        harness resting on the agreement.
        """
        completed = self._with_probe(
            "# probe\n\nThe paper reports 99.4 % on MED1250, which is within a point of ours "
            "and is the strongest available evidence that this harness is correct.\n"
        )
        assert completed.returncode == 1, (
            "an appeal to an externally published figure with no source and no read date did "
            "not fail the gate in the tree the gate reads."
        )
        assert "99.4 %" in completed.stdout + completed.stderr
        assert self._gate().returncode == 0, "the probe was not cleaned up"

    def test_the_same_appeal_cited_to_r4s_shape_stays_green(self) -> None:
        """The positive control, and the one that keeps the gate honest.

        Without it, a gate that reddened on the word "reports" regardless of the
        marker would pass the test above.
        """
        completed = self._with_probe(
            "# probe\n\nThe paper reports 99.4 % on MED1250, which is within a point of "
            "ours.<!--external: Ab3P, Sohn et al. 2008, Table 2 | read 2026-08-25-->\n"
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr

    def test_a_source_with_no_read_date_reddens_the_real_gate(self) -> None:
        completed = self._with_probe(
            "# probe\n\nThe paper reports 99.4 % on MED1250, which is within a point of "
            "ours.<!--external: Ab3P, Sohn et al. 2008, Table 2-->\n"
        )
        assert completed.returncode == 1, completed.stdout + completed.stderr
        assert "read YYYY-MM-DD" in completed.stdout + completed.stderr

    def test_a_code_spanned_figure_in_a_new_document_stays_green(self) -> None:
        """The declared hole, demonstrated in situ rather than only in a fixture."""
        completed = self._with_probe(
            "# probe\n\nThe published Schwartz & Hearst range is `~86-89 % F1 on Ab3P`.\n"
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
