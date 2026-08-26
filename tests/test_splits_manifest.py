"""``bench/splits.toml`` must parse and validate, because a rule nothing reads is a habit.

The project's second operating rule is that train/test separation is declared
before any knob is touched, and ``bench/splits.toml`` is where that declaration
lives. It was not valid TOML: a ``status`` key was written twice inside
``[corpora.plod]`` while adding a correction block, and nothing noticed for
months because nothing in the repository ever loaded the file. Eleven places
cited it in prose; zero parsed it.

That is the failure worth guarding against, and it is not really about TOML. A
governance artifact that no tool reads degrades into a document people believe
is enforced.

What this file pins, and why each item is here
----------------------------------------------
* **The manifest loads through the real loader.** These tests drive
  ``tools/splits.py`` -- the same module CI runs and the same module
  ``bench/corpora.py`` consults -- rather than re-implementing a parse. Three
  readers with three notions of "valid" is how a rule ends up with three
  behaviours, and it is why the loader has exactly one :func:`validate`.
* **Role, task and licence are required.** A corpus with no declared role is
  exempt from the headline rule by accident.
* **A licence URL and a read date are required.** Operating rule 4: licences
  come from terms, never from a badge. A bare licence string records a
  conclusion and destroys the evidence for it, and this project has recorded a
  corpus as more permissive than it is three times -- both SDU-21 entries, and
  GLADIS during the August 2026 audit. Every correction came from a person
  opening the actual terms.
* **A badge URL is refused.** GLADIS is the cautionary tale in one line: the
  GitHub badge said CC0, Zenodo said CC BY 4.0, and the repository's own source
  table listed UMLS, which is not redistributable. A validator that accepted
  ``shields.io`` would be enforcing the habit rather than the rule.
* **A declared recall ceiling must carry its derivation.** A ceiling nobody
  wrote the derivation for cannot be checked, and it would be quoted.
* **A headline is capable per task, never in general.** ``headline_capable``
  was task-blind: it returned every uncontaminated held-out corpus whatever it
  was annotated for. Harmless while every declared corpus was a pair or a span
  corpus; a hole the moment an ``identifier_segmentation`` corpus was
  registered ``held_out``, because a corpus that scores *where an identifier is
  cut* would have satisfied a headline requirement for *extracting definitions
  from prose*. Nothing would have failed. A table would simply have been
  published against a corpus structurally incapable of showing the phenomenon.
  That is mutated below rather than trusted.
* **The task a corpus declares must match the registry its reader is in.**
  ``TASKS`` is closed *because* ``bench/corpora.py`` returns a different type
  per task -- a sentence that lived in two docstrings and was checked by
  nothing, so a corpus declared ``disambiguation`` could have been registered
  in ``SPAN_READERS`` with no complaint.
* **A reserved arm must be reserved for something, and must refuse a read.**
  Two arms of two corpora are spoken for, and until this round both
  reservations were prose. D-043 and D-047 each say the same thing about
  themselves: *nothing refuses a run against a reserved split; the guard is
  that somebody reads a note.* That is the shape of the original bug in this
  file -- eleven prose citations, zero parsers -- one level up. The structure
  is mutated below exactly the way the licence-URL rule is: a reservation with
  no trigger, a spend that was never declared, and two reservations
  contradicting each other must each fail, and the shipped manifest must pass.

Nothing here reaches the network or needs a fetched corpus. **Nothing here
opens a reserved arm either**: every reservation test works on the declaration,
and the one test that drives the wired reader asserts the refusal, which
happens before the path is resolved.
"""

from __future__ import annotations

import dataclasses
import datetime
import importlib.util
import io
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SPLITS = REPO_ROOT / "bench" / "splits.toml"
LOADER = REPO_ROOT / "tools" / "splits.py"


def _load_tool() -> ModuleType:
    """Import ``tools/splits.py`` by path.

    ``tools/`` is not a package and must not become one: it is a directory of
    scripts, and making it importable for the benefit of a test would be the
    test changing the shape of the thing it tests. Same reasoning, and same
    mechanism, as ``tests/test_check_claims.py``.
    """
    spec = importlib.util.spec_from_file_location("_splits_under_test", LOADER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before execution: ``@dataclass`` resolves annotations through
    # ``sys.modules[cls.__module__]`` while the class body is still running.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_corpora() -> ModuleType:
    """Import ``bench/corpora.py`` by path, for the registry/task binding only.

    The two older tests below read ``bench/corpora.py`` as *source* and say why:
    ``bench`` is not installed, and a reader in it reaches for a fetched corpus.
    That reasoning covers *calling* a reader, not importing the module -- import
    only builds dataclasses and dicts, and it is what makes the registry
    contract checkable at all. Regex-parsing a nested ``{task: (registry, ...)}``
    table out of source would be a second, weaker parser of the thing under
    test.
    """
    spec = importlib.util.spec_from_file_location(
        "_corpora_under_test", REPO_ROOT / "bench" / "corpora.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# THE SAME GUARD THE `bench/` LOAD BELOW ALREADY CARRIES, FINALLY APPLIED TO THE
# `tools/` LOAD ITSELF. `tools/` ships in the sdist and is no part of an
# installed distribution, so under the installed-suite CI job the next line
# raises `FileNotFoundError` and this file fails to COLLECT. It has been covered
# by a file-keyed entry in `EXPECTED_NON_PASSING` in `.github/workflows/ci.yml`,
# and that list's own comment records what the entry cost: while a FILE sits
# there the job cannot see a second defect anywhere in it -- measured, by
# reintroducing a real breakage into a listed file and getting a run identical
# to a clean one. A skip on one named condition absorbs that condition and
# nothing else, so any other error here now reaches the job. The entry is
# deleted in the same commit.
if not LOADER.is_file():  # pragma: no cover - CI job only
    pytest.skip(
        "tools/ is not part of an installed distribution; these tests belong to a checkout",
        allow_module_level=True,
    )

splits = _load_tool()
# Guarded, and the guard has to be here rather than on `pytestmark`: the mark is
# consulted at COLLECTION and this line runs at IMPORT, which is earlier. The
# sdist ships `tests/` but deliberately not `bench/*.py`, so this module is
# imported without its subject every time CI runs the suite from the artifact.
# That has now broken the build five times in a row, in five different spellings.
CORPORA_SOURCE = REPO_ROOT / "bench" / "corpora.py"
corpora = _load_corpora() if CORPORA_SOURCE.is_file() else None

#: 3.9 and 3.10 have no ``tomllib``, and ``tomli`` is not a declared dev
#: dependency, so on those interpreters there is no parser to test with. The
#: dedicated CI step runs on 3.12, where this is never skipped.
_NO_PARSER = sys.version_info < (3, 11) and importlib.util.find_spec("tomli") is None

pytestmark = [
    pytest.mark.skipif(not SPLITS.is_file(), reason="not a source checkout"),
    pytest.mark.skipif(_NO_PARSER, reason="tomllib is 3.11+; tomli not installed"),
]

#: For the tests that reach through the manifest into `bench/corpora.py`.
#:
#: THESE WERE NOT SKIPPED BEFORE; THEY WERE NOT RUNNING AT ALL. `SPLITS` is
#: `bench/splits.toml`, which the sdist did not ship until the claims gate
#: started reading it, so the first `pytestmark` above skipped this ENTIRE
#: module in the extracted-tree job -- every test in the file, silently, for
#: as long as the file has existed. Shipping `splits.toml` un-skipped it and
#: surfaced fourteen tests that need `bench/corpora.py`, which the sdist
#: deliberately does not ship and should not: its readers want fetched corpora
#: and optional dependencies an sdist has no business assuming.
#:
#: The narrow mark is the point. A module-wide skip is what hid these, and
#: replacing one blanket with another would keep the rest of the file dark.
needs_corpora = pytest.mark.skipif(
    corpora is None, reason="bench/corpora.py is not shipped in the sdist"
)


@pytest.fixture(scope="module")
def manifest() -> object:
    """The real manifest, parsed by the real loader."""
    return splits.load(SPLITS)


def _write(tmp_path: Path, body: str) -> Path:
    """A throwaway manifest, so a negative test never edits the real file.

    The directory is created rather than assumed, so a test that needs a
    *second* manifest -- a mutation and its control, loaded in one test -- can
    ask for ``tmp_path / "control"`` without the write failing for a reason that
    has nothing to do with what it checks.
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "splits.toml"
    path.write_text(body, encoding="utf-8")
    return path


_MINIMAL = """
[policy]
headline_requires = "held_out"

[corpora.example]
role = "tuning"
task = "extraction"
licence = "Public domain"
licence_url = "https://example.org/terms.txt"
licence_read_on = 2026-08-23
"""


def _declared_as(source: str) -> tuple[set, set]:
    """``(reader names, manifest names)`` from ``bench/corpora.py``'s DECLARED_AS.

    Parsed out of the source rather than imported: ``bench`` is not installed,
    and importing it would pull a module that reaches for a fetched corpus on
    some paths. The parse is deliberately literal, so a reformatted table makes
    the test fail loudly rather than silently check nothing -- which is why both
    callers assert the result is non-empty before using it.
    """
    block = source.partition("DECLARED_AS = {")[2].partition("}")[0]
    rows = [
        line.split(":", 1)
        for line in block.splitlines()
        if ":" in line and not line.strip().startswith("#")
    ]
    return (
        {left.strip().strip("\"'") for left, _ in rows},
        {right.strip().strip('",').strip("'") for _, right in rows},
    )


#: A reservation that passes every rule, so a mutation of it fails for the
#: reason under test and not for a second reason nobody noticed.
_CLEAN_RESERVATION = {
    "arm": '"train"',
    "state": '"allocated"',
    "decided_in": '"D-047"',
    "allocated_to": "'the legend flag precision cost; W8 owns the read'",
    "spend_trigger": "'W8 elects to publish the cost on an unmined arm'",
    "lapse_trigger": "'a structurally capable uncontaminated corpus is registered'",
}


def _with_reservation(**overrides: Optional[str]) -> str:
    """``_MINIMAL`` plus one reservation, with fields overridden or dropped.

    ``None`` removes a field, which is how "a reservation with no trigger" is
    written -- the case D-043 says makes a reservation not a reservation.
    """
    fields = dict(_CLEAN_RESERVATION)
    fields.update({key: value for key, value in overrides.items() if value is not None})
    for key, value in overrides.items():
        if value is None:
            fields.pop(key, None)
    body = "\n".join(f"{key} = {value}" for key, value in fields.items())
    return _MINIMAL + "\n[[corpora.example.reservations]]\n" + body + "\n"


def _ledgers() -> list:
    """Every declared-spend ledger this process holds.

    There is more than one, and that is a real property rather than a test
    artifact: ``tools/splits.py`` is imported *by path*, so this file's copy and
    ``bench/corpora.py``'s copy are two module objects with two module-level
    dicts. ``bench.corpora.declare_spend`` exists so runners only ever touch
    one of them; the fixture below restores both, because a spend leaking out
    of a test would let a later test open a reserved arm for real.
    """
    found = [splits._DECLARED_SPENDS]
    if corpora is not None:
        module = corpora._splits_module()
        if module is not None and module._DECLARED_SPENDS is not splits._DECLARED_SPENDS:
            found.append(module._DECLARED_SPENDS)
    return found


@pytest.fixture(autouse=True)
def _no_spend_leaks() -> object:
    """A spend declared by one test must not open an arm for the next one.

    The ledger is process-local by design -- see ``tools/splits.py`` on why it
    is not written back to the manifest -- and process-local state that leaks
    between tests would make the refusal look flaky rather than wrong.
    """
    saved = [(ledger, dict(ledger)) for ledger in _ledgers()]
    yield
    for ledger, before in saved:
        ledger.clear()
        ledger.update(before)


#: A valid ``single_annotator_reference`` entry, so a mutation of it fails for
#: the reason under test rather than for a second reason nobody noticed. It is
#: built from ``_MINIMAL`` rather than written out, so a new *universally*
#: required field breaks this fixture in the same commit as every other.
_SINGLE_ANNOTATOR_FIELDS = (
    'adjudicators = ["a. person (author of the pooled extractor)"]',
    'pooling_recipe = "one parenthesis scanner plus an all-caps proposer"',
)

#: The contamination half, kept separate and switchable. **This is not tidiness.**
#: ``headline_capable`` excludes a corpus for three independent reasons -- wrong
#: task, contaminated, never-headline role -- and a fixture that trips two of
#: them cannot show which one is doing the work. Deleting the role filter from
#: ``headline_capable`` left the whole suite green precisely because the fixture
#: was contaminated as well, so the exclusion under test was being demonstrated
#: by a different rule. The mutation found it; the split is the fix.
_CONTAMINATION_FIELDS = (
    "contaminated = true",
    'contamination_reason = "the adjudicator authored a pooled system"',
)


def _single_annotator(*, drop: Optional[str] = None, contaminated: bool = True) -> str:
    """``_MINIMAL`` re-roled to ``single_annotator_reference``, optionally missing a field.

    Args:
        drop: A role-required field to leave out, which is how "a corpus that
            claims the role without recording who decided" is written.
        contaminated: Whether to carry the contamination flag. Pass ``False``
            when the test is about the *role* excluding a corpus from a headline,
            so that the contamination rule cannot excuse it first.
    """
    body = _mutated("role", '"single_annotator_reference"')
    fields = _SINGLE_ANNOTATOR_FIELDS + (_CONTAMINATION_FIELDS if contaminated else ())
    extra = [line for line in fields if drop is None or not line.startswith(drop + " =")]
    return body + "\n".join(extra) + "\n"


def _mutated(field: str, value: Optional[str]) -> str:
    """``_MINIMAL`` with one field replaced, or removed when ``value`` is ``None``."""
    out = []
    for line in _MINIMAL.strip().splitlines():
        if line.startswith(field + " ="):
            if value is None:
                continue
            out.append(f"{field} = {value}")
        else:
            out.append(line)
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# the real file
# ---------------------------------------------------------------------------
def _unreserved_filename(resolve: Callable[[], Path]) -> str:
    """The file an *unreserved* arm resolves to, fetched or not.

    The controls in the reservation tests exist to show the guard is arm-scoped:
    that an arm carrying no reservation is not refused by it. They do not need
    the corpus on disk, and asserting on a returned path quietly made them need
    it -- green in a checkout with `data/` fetched, and three failures on every
    CI runner, where `data/` is not vendored. The docstrings already claimed the
    refusal fires "before the path is resolved"; this is the controls finally
    being written the way the docstrings describe.

    Both outcomes prove the same thing and both name the same file: a resolved
    path when the corpus is present, and the fetch refusal when it is not. What
    neither may be is the reservation, which is what this asserts.
    """
    try:
        return Path(resolve()).name
    except SystemExit as exc:
        message = str(exc)
        assert "RESERVED" not in message, (
            f"the reservation fired on an arm that carries none: {message}"
        )
        first = message.splitlines()[0]
        assert first.startswith("missing "), (
            f"expected a resolved path or the fetch refusal, got: {message}"
        )
        return Path(first[len("missing ") :]).name


class TestTheRealManifest:
    """The manifest this repository actually ships."""

    def test_it_parses(self, manifest: object) -> None:
        """The file the train/test rule rests on must be machine-readable."""
        assert manifest.corpora, "no corpora declared; the manifest guards nothing"

    def test_it_validates(self, manifest: object) -> None:
        """Zero findings, through the same validator CI runs."""
        problems = splits.validate(manifest)
        assert not problems, "bench/splits.toml is invalid:\n  " + "\n  ".join(problems)

    def test_the_cli_check_agrees_with_the_library(self) -> None:
        """``--check`` and :func:`validate` must not be able to disagree."""
        assert splits.main(["--check", "--path", str(SPLITS)]) == 0

    def test_every_corpus_declares_the_required_fields(self, manifest: object) -> None:
        """Role, task, licence, and the two fields that make the licence checkable."""
        for name in manifest.names:
            corpus = manifest.corpus(name)
            for declared in splits.REQUIRED_FIELDS:
                assert not splits._is_absent(corpus, declared), f"{name} is missing {declared}"

    def test_no_licence_was_read_from_a_badge(self, manifest: object) -> None:
        """Operating rule 4, checked rather than trusted.

        Three repositories in this project's registry publish a machine-readable
        licence field that is wrong about their own data. Reading the terms is
        the rule; citing where you read them is what makes it auditable.
        """
        for name in manifest.names:
            url = manifest.corpus(name).licence_url
            assert splits._licence_url_problem(url) is None, f"{name}: {url}"

    def test_no_licence_was_read_in_the_future(self, manifest: object) -> None:
        today = datetime.date.today()
        for name in manifest.names:
            read_on = manifest.corpus(name).licence_read_on
            assert read_on <= today, f"{name} claims a licence read on {read_on}"

    def test_a_declared_recall_ceiling_carries_its_derivation(self, manifest: object) -> None:
        """R9.6: a ceiling gets published beside a recall figure, so it must be checkable."""
        for name in manifest.names:
            corpus = manifest.corpus(name)
            if corpus.shortform_recall_ceiling_pct is None:
                continue
            assert 0.0 < corpus.shortform_recall_ceiling_pct <= 100.0
            assert corpus.shortform_recall_ceiling_basis.strip(), name

    def test_a_contaminated_corpus_says_why(self, manifest: object) -> None:
        """An unexplained contamination flag can never be argued down later."""
        for name in manifest.names:
            corpus = manifest.corpus(name)
            if corpus.contaminated:
                assert corpus.contamination_reason.strip(), name

    def test_the_sdu22_ae_splits_are_not_presented_as_held_out(self, manifest: object) -> None:
        """The corpus is new, non-biomedical, and still not a blind split.

        Its test files carry zero labels and its dev files were mined for a miss
        taxonomy by the August 2026 audit -- the same act that contaminated
        MED1250. Filing it as held out would repeat the PLOD mistake in the week
        the audit warned about it.
        """
        for name in ("sdu22_ae_legal", "sdu22_ae_scientific"):
            corpus = manifest.corpus(name)
            assert corpus.is_tuning, f"{name} must not be presented as generalisation evidence"
            assert corpus.contaminated

    def test_the_two_governed_corpora_are_declared(self, manifest: object) -> None:
        """R2 was broken by the workstream that satisfied the goal, and this is the close.

        ``bench/run_governed_gold.py`` published 67 run-id citations off SEC
        XBRL and Socrata while neither was in this file, so every figure carried
        ``splits_declaration = "UNDECLARED"``. A corpus that is measured but not
        declared is exempt from the train/test rule *by omission*, which is the
        exact failure the manifest exists to prevent.
        """
        for name in ("sec_xbrl", "socrata"):
            corpus = manifest.corpus(name)
            assert corpus.task == "identifier_segmentation", name
            assert corpus.role in splits.ROLES, name
            assert corpus.licence_url and splits._licence_url_problem(corpus.licence_url) is None
            assert corpus.licence_read_on > datetime.date.min, name
            assert corpus.vendorable is False, f"{name}: third-party terms, benchmark use only"

    def test_a_segmentation_corpus_does_not_back_a_pair_headline(self, manifest: object) -> None:
        """The quiet hole, on the real file rather than on a fixture.

        Both corpora are ``held_out`` and uncontaminated, so under the
        task-blind ``headline_capable()`` they were eligible sources for *any*
        headline. They score where an identifier is cut. They contain no
        abbreviation, no passage and no annotator, so they are structurally
        incapable of showing anything about extracting definitions from prose.
        """
        for task in ("extraction", "span_detection", "disambiguation"):
            eligible = {corpus.name for corpus in manifest.headline_capable(task)}
            assert "sec_xbrl" not in eligible, task
            assert "socrata" not in eligible, task
        segmentation = {
            corpus.name for corpus in manifest.headline_capable("identifier_segmentation")
        }
        assert segmentation == {"sec_xbrl", "socrata"}

    def test_registering_them_did_not_silence_the_headline_gap(self, manifest: object) -> None:
        """The consequence claimed for this registration last round, checked rather than assumed.

        D-031 recorded a worry that registering these corpora would silence the
        "no uncontaminated held-out corpus" advisory. Under the pooled advisory
        it was already silent, and under the per-task one it cannot be silenced
        by a corpus for a different task: the extraction and disambiguation gaps
        are still open and still printed.
        """
        reported = " ".join(splits.notes(manifest))
        assert "task='extraction'" in reported
        assert "task='disambiguation'" in reported

    def test_the_federal_register_reference_set_is_declared_at_the_third_role(
        self, manifest: object
    ) -> None:
        """D-056 refused to write this entry because ``ROLES`` could not say what it is.

        The refusal was right and its permanence was never argued -- it stood
        because a five-line tuple had not been extended. The tuple is extended;
        this is the entry.
        """
        corpus = manifest.corpus("federal_register_rules_2024q1")
        assert corpus.role == "single_annotator_reference"
        assert corpus.task == "extraction"
        assert corpus.vendorable is False
        assert corpus.contaminated is True
        assert corpus.contamination_reason.strip()
        assert splits._licence_url_problem(corpus.licence_url) is None

    def test_it_names_its_adjudicator_and_how_the_pool_was_proposed(self, manifest: object) -> None:
        """The two facts the role exists to require, on the real file.

        They are the reason the artifact is not a gold standard, and until this
        entry existed they lived only inside a frozen JSON envelope in a
        git-ignored directory -- somewhere the governance file could not see
        them.
        """
        corpus = manifest.corpus("federal_register_rules_2024q1")
        assert corpus.adjudicator_count == 1
        assert "author of acronymkit" in corpus.adjudicators[0]
        assert corpus.pooling_recipe.strip()
        assert "Schwartz & Hearst" in corpus.pooling_recipe, (
            "the recipe must say the pooled systems are one algorithm, which is "
            "the finding that makes their agreement not corroboration"
        )
        assert "unproposed_parenthetical" in corpus.pooling_recipe

    def test_it_is_headline_capable_for_no_task_at_all(self, manifest: object) -> None:
        """Asserted, not inferred from ``[policy] headline_requires`` happening to differ.

        The brief for this registration was explicit that accidental exclusion
        is not exclusion. The corpus is checked out of **every** task's headline
        list, and the role property that puts it there is checked separately, so
        the two cannot both be satisfied by one editable line.
        """
        corpus = manifest.corpus("federal_register_rules_2024q1")
        assert corpus.may_back_a_headline is False
        assert corpus.role in splits.NEVER_HEADLINE_ROLES
        for task in splits.TASKS:
            eligible = {entry.name for entry in manifest.headline_capable(task)}
            assert "federal_register_rules_2024q1" not in eligible, task

    def test_registering_it_did_not_move_the_extraction_gap(self, manifest: object) -> None:
        """The number that would look like progress, and is not.

        Registering an extraction corpus raises the *declared* count for
        ``extraction`` while leaving the headline slot exactly as empty as it
        was. A per-task advisory that printed only the declared count would read
        as a near miss, so it prints the count in the headline role beside it,
        and that count is zero.
        """
        reported = " ".join(splits.notes(manifest))
        assert "task='extraction'" in reported
        assert "0 in that role" in reported
        assert manifest.headline_capable("extraction") == ()
        assert "NEVER headline-capable" in reported

    def test_the_entry_records_the_premises_that_died(self, manifest: object) -> None:
        """A corpus entry documenting why it is weak is worth more than one saying it exists.

        Three premises this corpus was funded on were refuted by measurement,
        and an entry that carried only the licence and the role would leave the
        next round to rediscover them. The figures themselves are un-gated and
        sit in fenced blocks; what is asserted here is that the *findings* are
        written down, because a fenced number nobody explains is indistinguishable
        from a hidden one.
        """
        note = manifest.corpus("federal_register_rules_2024q1").note
        assert "PREMISE 1, REFUTED" in note
        assert "PREMISE 2, REFUTED" in note
        assert "SF--LF" in note and "SF = LF" in note, (
            "the legend syntax is the operative half of premise 1: the shipped "
            "reader sees none of these legends"
        )
        assert "UN-GATED" in note and "run id" in note, (
            "every figure in this entry is un-gated and the entry must say so"
        )
        assert "mirror" in note, "the reproduction property is the strong half"
        assert "NOT re-derivable from this repository" in note, (
            "three rows of the proposer table need two external packages the shipped "
            "pipeline never drives; an entry that repeated them as though checked would "
            "be laundering a transcription into a measurement"
        )
        assert "CASE-FOLDED" in note and "EXACT-CASE" in note, (
            "the two rows that DO re-derive only match under case-folded edge identity, "
            "and no record said which identity was used"
        )

    @needs_corpora
    def test_every_registry_key_declares_the_task_its_registry_is_for(self) -> None:
        """``TASKS`` is closed *because* ``bench/corpora.py`` returns a type per task.

        That sentence sat in two docstrings and was checked by nothing: a corpus
        declared ``disambiguation`` could have been registered in
        ``SPAN_READERS``, which is the exact mis-filing the closed vocabulary
        claims to prevent. This walks every registry key through ``DECLARED_AS``
        into the manifest and asserts the declared task matches.
        """
        manifest = splits.load(SPLITS)
        checked = 0
        for task, registry_names in corpora.TASK_REGISTRIES.items():
            assert task in splits.TASKS, task
            for registry_name in registry_names:
                registry = getattr(corpora, registry_name)
                for key in registry:
                    if key in corpora.TEXT_ONLY_VIEWS:
                        continue  # named exception; checked on its own below
                    target = corpora.DECLARED_AS.get(key, key)
                    corpus = manifest.corpus(target)
                    assert corpus.task == task, (
                        f"{key!r} is in {registry_name} (task {task!r}) but "
                        f"bench/splits.toml declares {target!r} as {corpus.task!r}"
                    )
                    checked += 1
        assert checked, "no registry keys walked; this test is checking nothing"

    @needs_corpora
    def test_the_one_registry_exception_is_enumerated_and_still_true(self) -> None:
        """``READERS`` holds four span-corpus keys on purpose, and only those four.

        Found by the binding check above on its first run, which is the argument
        for having it. ``plod`` is declared ``span_detection`` and four
        ``plod_cw_*`` keys sit in ``READERS`` -- the ``GoldDocument`` registry --
        because ``bench/external.py`` needs text-bearing documents for an
        out-of-process baseline. That is deliberate, it carries ``pairs=()``, and
        ``read_plod_cw_text`` has documented it in prose since it was written.
        Prose is not consultable, so the exception is now a set: it must be
        non-empty, every member must really be in ``READERS``, and every member
        must really be declared for another task -- otherwise the exemption is
        quietly excusing something it no longer describes.
        """
        assert corpora.TEXT_ONLY_VIEWS, "the exemption set is empty; nothing needs exempting"
        manifest = splits.load(SPLITS)
        for key in corpora.TEXT_ONLY_VIEWS:
            assert key in corpora.READERS, f"{key} is exempted but not registered"
            corpus = manifest.corpus(corpora.DECLARED_AS.get(key, key))
            assert corpus.task != "extraction", (
                f"{key} is exempted from the task binding but its corpus IS an "
                "extraction corpus; the exemption is excusing nothing"
            )

    @needs_corpora
    def test_every_task_in_the_vocabulary_has_a_registry_and_a_gold_unit(self) -> None:
        """A task with no type behind it is a word, which is what the vocabulary is not."""
        assert set(corpora.TASK_REGISTRIES) == set(splits.TASKS)
        assert set(splits.TASK_GOLD_UNIT) == set(splits.TASKS)
        for task in splits.TASKS:
            assert splits.TASK_GOLD_UNIT[task].strip(), task

    def test_the_gold_unit_states_the_edge_and_not_only_the_shape(self) -> None:
        """D-048's owed edit, pinned so it cannot be compressed back out.

        ``extraction`` and ``span_detection`` gold both hold short forms and
        long forms inside a passage, so on *shape* alone they read as one task
        under two names. The difference is relational: extraction gold asserts
        an edge between the two and span gold asserts none. That is why a
        held-out span corpus cannot back the claim this project leads with, and
        why two systems differing only in their pairing score identically
        through the span scorer. Stating the shape and not the edge is what let
        that argument live in a decision record instead of in the vocabulary.
        """
        extraction = splits.TASK_GOLD_UNIT["extraction"]
        spans = splits.TASK_GOLD_UNIT["span_detection"]
        assert "EDGE" in extraction, "extraction gold IS an edge; the entry must say so"
        assert "UNLINKED" in spans, "span gold is two unlinked vertex sets; the entry must say so"
        # And the wider extension, which is the other half of D-048's table:
        # span corpora tag every occurrence, defined or not.
        assert "occurrence" in spans

    def test_med1250_is_still_a_tuning_split(self, manifest: object) -> None:
        """Operating rule 2, in the file it lives in."""
        assert manifest.corpus("med1250").is_tuning
        assert manifest.corpus("med1250").label() == "tuning split, contaminated"

    @needs_corpora
    def test_every_reader_in_bench_maps_to_a_declared_corpus(self, manifest: object) -> None:
        """``bench/corpora.py`` binds each reader to a declaration; the map must resolve.

        Read out of the source rather than by importing ``bench``, which is not
        installed and which reaches for a fetched corpus on some paths.
        """
        source = (REPO_ROOT / "bench" / "corpora.py").read_text(encoding="utf-8")
        keys, targets = _declared_as(source)
        assert targets, "DECLARED_AS did not parse; the binding is not being checked"
        undeclared = sorted(targets - set(manifest.names))
        assert not undeclared, f"bench/corpora.py reads undeclared corpora: {undeclared}"
        assert keys, "DECLARED_AS keys did not parse"

    def test_the_two_prose_reservations_are_now_structures(self, manifest: object) -> None:
        """D-043 and D-047 allocated an arm each in prose, and prose refuses nothing.

        Both records say so about themselves. The point of this test is that the
        allocation is now a *parsed* thing with a state, a record and a trigger,
        so the next round can be refused by it rather than reminded of it.
        """
        reserved = {(entry.corpus, entry.arm): entry for entry in manifest.reserved_arms()}
        assert ("sdu21_ad", "test") in reserved, "D-043's reservation is not declared"
        assert ("sdu22_ae_legal", "train") in reserved, "D-047's allocation is not declared"
        assert ("sdu22_ae_scientific", "train") in reserved, "D-047's non-allocation is not a state"

        assert reserved[("sdu21_ad", "test")].decided_in == "D-043"
        assert reserved[("sdu22_ae_legal", "train")].decided_in == "D-047"
        # SPENT since the legend workstream took the read D-047 allocated. This
        # assertion read ``"allocated"`` until then, and updating it is the
        # whole cost of the arm having been used: a reservation is a state
        # machine and ``spent`` is a terminal state, not a missing one. The
        # ledger line is what makes the spend arguable afterwards -- an arm
        # marked spent with nothing to point at is a contamination with no
        # evidence, which the validator refuses one level up.
        assert reserved[("sdu22_ae_legal", "train")].state == "spent"
        assert reserved[("sdu22_ae_legal", "train")].spent_in.strip(), (
            "the legal train arm is spent and names nothing that spent it"
        )
        assert not reserved[("sdu22_ae_legal", "train")].allocated_to, (
            "a spent arm may not still name what it was allocated to"
        )
        # UNALLOCATED is a state D-047 chose, not the absence of one: assigning
        # this split a use today would mean inventing one.
        assert reserved[("sdu22_ae_scientific", "train")].state == "unallocated"
        assert not reserved[("sdu22_ae_scientific", "train")].allocated_to

    def test_every_reserved_arm_names_the_trigger_that_would_fire_it(
        self, manifest: object
    ) -> None:
        """The field the whole structure exists for, on the real file.

        A reservation with no trigger survives each round because nobody
        happened to want it, which is not the same as being reserved *for*
        something -- D-043's finding, and the reason it gave AD ``test.json``
        a use in the first place.
        """
        entries = manifest.reserved_arms()
        assert entries, "no reserved arms declared; this test is checking nothing"
        for entry in entries:
            assert entry.spend_trigger.strip(), f"{entry.corpus}:{entry.arm} has no spend_trigger"
            assert entry.decided_in, f"{entry.corpus}:{entry.arm} names no record"
            if entry.state == "allocated":
                assert entry.lapse_trigger.strip(), f"{entry.corpus}:{entry.arm} cannot be released"

    def test_a_reserved_arm_refuses_a_read_that_did_not_declare_a_spend(
        self, manifest: object
    ) -> None:
        """R3, as a refusal rather than as a note somebody has to read.

        Nothing is opened here: the refusal is on the declaration and fires
        before any path is resolved.

        ``sdu22_ae_legal:train`` is deliberately **not** in the list any more.
        It was spent under D-047, and a spent arm refuses nothing -- the cost
        has been paid and the corpus entry is where the contamination is
        recorded. Asserting a refusal there would pin the guard to a state the
        manifest has left, which is the failure mode this file exists to make
        expensive. It is asserted the other way instead, below.
        """
        for name, arm in (
            ("sdu21_ad", "test"),
            ("sdu22_ae_scientific", "train"),
        ):
            with pytest.raises(splits.SplitsError, match="RESERVED"):
                manifest.corpus(name).require_unreserved(arm)
        # The spent arm: it is still a declared reservation, and it no longer
        # refuses. Both halves matter -- the entry has to survive being spent so
        # the record of what was paid survives with it.
        assert manifest.corpus("sdu22_ae_legal").reservation("train") is not None
        manifest.corpus("sdu22_ae_legal").require_unreserved("train")
        # The control: the arms beside them are free, and the guard is silent.
        manifest.corpus("sdu22_ae_legal").require_unreserved("dev")
        manifest.corpus("sdu21_ad").require_unreserved("train")
        manifest.corpus("med1250").require_unreserved("all")

    def test_the_unallocated_arm_refuses_even_a_declared_spend(self, manifest: object) -> None:
        """ "First-come is refused" is a rule D-047 wrote and could not enforce.

        An unallocated arm cannot be spent by naming the record that declined to
        allocate it. Its first spend needs its own record, and the manifest has
        to carry the allocation before a runner can claim it.
        """
        with pytest.raises(splits.SplitsError, match="UNALLOCATED"):
            manifest.corpus("sdu22_ae_scientific").declare_spend(
                "train", decision="D-047", purpose="a number this round", stream=io.StringIO()
            )

    @needs_corpora
    def test_the_reader_that_would_spend_the_allocated_arm_is_wired(self) -> None:
        """The guard is LIVE, not merely available, and this is the difference.

        ``data/sdu22_ae_legal_train.json`` is already fetched, so before the
        reservation existed a single ``read_sdu22_ae(domain="legal",
        split="train")`` mined the last unmined arm of the corpus and printed
        nothing. The refusal fires inside ``_sdu22_ae_source`` *before* the path
        is resolved, which is why this test can assert it without opening the
        file.

        **The legal arm has since been spent (D-047), so it is the control here
        rather than the case.** That is the interesting direction: the guard has
        to stop refusing when the manifest says the cost was paid, or the next
        workstream routes around it, and a guard people route around is worse
        than no guard. The scientific arm is still unallocated and still
        refuses, so the live half is asserted on that one.
        """
        with pytest.raises(SystemExit, match="RESERVED"):
            corpora._sdu22_ae_source(None, "scientific", "train")
        # The spent arm resolves, and the dev arms beside it -- which never
        # carried a reservation -- resolve for a different reason. Both are
        # filename assertions so this passes with the corpus absent too.
        assert _unreserved_filename(
            lambda: corpora._sdu22_ae_source(None, "legal", "train")
        ).endswith("legal_train.json")
        assert _unreserved_filename(
            lambda: corpora._sdu22_ae_source(None, "legal", "dev")
        ).endswith("legal_dev.json")

    @needs_corpora
    def test_the_ad_reservation_is_refused_before_the_split_is_called_a_typo(self) -> None:
        """D-043's arm, and the ordering that makes its reservation live rather than lucky.

        ``test`` is not in the AD registry and has no fetch entry, so it was
        refused as an unknown split -- an accident that reads like a guard.
        Asking the manifest first means whoever adds the registry entry meets
        the reservation instead of removing the only thing in front of the
        project's last blind disambiguation arm.
        """
        with pytest.raises(SystemExit, match="RESERVED"):
            corpora._sdu21_ad_source(None, "test")
        # Controls: the unreserved arms are untouched, and a real typo is still
        # reported as a typo rather than swallowed by the guard.
        assert _unreserved_filename(lambda: corpora._sdu21_ad_source(None, "dev")).endswith(
            "sdu21_ad_dev.json"
        )
        with pytest.raises(SystemExit, match="unknown SDU21-AD split"):
            corpora._sdu21_ad_source(None, "tset")

    @needs_corpora
    def test_the_runner_facing_door_writes_the_ledger_the_reader_reads(self) -> None:
        """One door, one ledger -- the part most likely to be quietly wrong.

        ``tools/splits.py`` is imported by path, so this file's copy of it and
        ``bench/corpora.py``'s copy are two module objects with two module-level
        ledgers. A runner that declared its spend against the wrong one would be
        refused by the reader anyway and would have no idea why.
        ``bench.corpora.declare_spend`` is the single door that cannot go wrong.

        This resolves a path and does not read the file; ``_no_spend_leaks``
        puts the ledger back so no later test inherits an open arm.
        """
        corpora.declare_spend(
            "sdu22_ae_legal",
            "train",
            decision="D-047",
            purpose="legend precision cost on an unmined arm, two_word row saved beside it",
        )
        assert _unreserved_filename(
            lambda: corpora._sdu22_ae_source(None, "legal", "train")
        ).endswith("legal_train.json")
        # And the declaration is arm-scoped: it opens one arm of one corpus.
        with pytest.raises(SystemExit, match="RESERVED"):
            corpora._sdu22_ae_source(None, "scientific", "train")

    @needs_corpora
    def test_every_registry_key_in_bench_is_one_the_manifest_can_answer_for(self) -> None:
        """No reader may be registered under a name ``label_for`` cannot resolve.

        Found while exercising the wiring: ``CHAR_SPAN_READERS`` was keyed
        ``"sdu22_ae"``, a *family* name covering two declared corpora, so it was
        the one entry in the module whose role could not be looked up. A corpus
        whose role cannot be looked up is precisely the gap the manifest exists
        to close, so the shape is checked rather than remembered.
        """
        source = (REPO_ROOT / "bench" / "corpora.py").read_text(encoding="utf-8")
        keys, _ = _declared_as(source)
        registered: set = set()
        for registry in ("DISAMBIGUATION_READERS", "SPAN_READERS", "CHAR_SPAN_READERS"):
            block = source.partition(registry + " = {")[2].partition("}")[0]
            registered |= {
                line.split(":")[0].strip().strip("\"'")
                for line in block.splitlines()
                if ":" in line and not line.strip().startswith("#")
            }
        assert registered, "no registries parsed; this test is checking nothing"
        unmapped = sorted(registered - keys)
        assert not unmapped, f"registry keys with no DECLARED_AS entry: {unmapped}"


# ---------------------------------------------------------------------------
# the validator, mutated
# ---------------------------------------------------------------------------
class TestTheValidatorCatchesWhatItClaimsTo:
    """Each rule, broken deliberately.

    A validator whose failure modes are untested is a validator nobody has seen
    fail, which is indistinguishable from one that cannot.
    """

    def test_the_baseline_is_clean(self, tmp_path: Path) -> None:
        """Otherwise every mutation below would pass for the wrong reason."""
        assert splits.validate(splits.load(_write(tmp_path, _MINIMAL))) == []

    def test_a_duplicate_key_is_a_parse_error(self, tmp_path: Path) -> None:
        """The original bug, in the shape it originally had."""
        body = _MINIMAL + 'status = "one"\nstatus = "two"\n'
        with pytest.raises(splits.SplitsError, match="not valid TOML"):
            splits.load(_write(tmp_path, body))

    def test_a_manifest_with_no_corpora_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(splits.SplitsError, match="guards nothing"):
            splits.load(_write(tmp_path, "[policy]\nheadline_requires = 'held_out'\n"))

    @pytest.mark.parametrize("field", ["role", "task", "licence", "licence_url", "licence_read_on"])
    def test_a_missing_required_field_is_reported(self, tmp_path: Path, field: str) -> None:
        problems = splits.validate(splits.load(_write(tmp_path, _mutated(field, None))))
        assert any(field in problem for problem in problems), problems

    def test_an_unknown_role_is_reported(self, tmp_path: Path) -> None:
        problems = splits.validate(splits.load(_write(tmp_path, _mutated("role", '"heldout"'))))
        assert any("role" in problem for problem in problems), problems

    def test_an_unknown_task_is_reported(self, tmp_path: Path) -> None:
        problems = splits.validate(splits.load(_write(tmp_path, _mutated("task", '"vibes"'))))
        assert any("task" in problem for problem in problems), problems

    @pytest.mark.parametrize(
        "url",
        [
            "https://img.shields.io/github/license/tigerchen52/GLADIS",
            "https://api.github.com/repos/tigerchen52/GLADIS/license",
            "https://example.org/badge/licence.svg",
            "CC-BY-4.0",
            "ftp://example.org/LICENSE",
        ],
    )
    def test_a_badge_or_a_bare_label_is_refused(self, tmp_path: Path, url: str) -> None:
        """Every one of these is a licence *label*, not licence *text*."""
        problems = splits.validate(
            splits.load(_write(tmp_path, _mutated("licence_url", f'"{url}"')))
        )
        assert any("licence_url" in problem for problem in problems), problems

    def test_an_unparseable_read_date_is_not_mistaken_for_a_present_one(
        self, tmp_path: Path
    ) -> None:
        """The trap in the date field: its "absent" sentinel is truthy."""
        body = _mutated("licence_read_on", '"last Tuesday"')
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("licence_read_on" in problem for problem in problems), problems

    def test_a_future_read_date_is_reported(self, tmp_path: Path) -> None:
        ahead = datetime.date.today() + datetime.timedelta(days=2)
        body = _mutated("licence_read_on", ahead.isoformat())
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("future" in problem for problem in problems), problems

    def test_a_ceiling_without_a_basis_is_reported(self, tmp_path: Path) -> None:
        body = _MINIMAL + "shortform_recall_ceiling_pct = 55.15\n"
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("basis" in problem for problem in problems), problems

    def test_a_ceiling_outside_0_to_100_is_reported(self, tmp_path: Path) -> None:
        body = _MINIMAL + (
            "shortform_recall_ceiling_pct = 155.0\nshortform_recall_ceiling_basis = 'counted'\n"
        )
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("percent" in problem for problem in problems), problems

    def test_contamination_without_a_reason_is_reported(self, tmp_path: Path) -> None:
        problems = splits.validate(
            splits.load(_write(tmp_path, _MINIMAL + "contaminated = true\n"))
        )
        assert any("contamination_reason" in problem for problem in problems), problems

    def test_a_contaminated_corpus_cannot_hold_the_headline_role(self, tmp_path: Path) -> None:
        """The MED1250 invariant, and the one an author is most tempted to break.

        Found by mutating the real manifest: promoting ``sdu22_ae_legal`` to
        ``held_out`` while leaving ``contaminated = true`` passed the validator,
        and only a hand-written assertion about that one corpus caught it. A
        rule that has to be restated per corpus is not a rule.
        """
        body = _mutated("role", '"held_out"') + (
            "contaminated = true\ncontamination_reason = 'its misses were read'\n"
        )
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("adjudicates nothing blind" in problem for problem in problems), problems

    def test_a_recall_ceiling_on_a_task_with_no_short_forms_is_reported(
        self, tmp_path: Path
    ) -> None:
        """An identifier-segmentation corpus annotates no abbreviation anywhere.

        So ``shortform_recall_ceiling_pct`` on one is not a cautious extra: it
        is a number with nothing behind it that would end up printed beside a
        recall figure measuring a different quantity, which is precisely what
        the field was introduced to stop.
        """
        body = _mutated("task", '"identifier_segmentation"') + (
            "shortform_recall_ceiling_pct = 55.15\n"
            "shortform_recall_ceiling_basis = 'counted from the corpus'\n"
        )
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("no short forms" in problem for problem in problems), problems

    def test_a_segmentation_corpus_cannot_satisfy_a_pair_headline(self, tmp_path: Path) -> None:
        """The mutation the task-blind version would have passed.

        The fixture is a corpus that is ``held_out``, uncontaminated and
        perfectly valid -- so it clears every check the validator makes -- and
        is annotated for a task that has nothing to do with pairs. Under the old
        signature it was returned to a caller asking "may I publish a headline?"
        with no way to notice. The two assertions are the mutation and its
        control: the corpus IS in the headline role, and it is STILL not
        eligible for an extraction headline.
        """
        body = _mutated("role", '"held_out"').replace(
            'task = "extraction"', 'task = "identifier_segmentation"'
        )
        manifest = splits.load(_write(tmp_path, body))
        assert splits.validate(manifest) == []
        held_out = [corpus.name for corpus in manifest.with_role("held_out")]
        assert held_out == ["example"], "the mutation did not take; the test proves nothing"
        assert manifest.headline_capable("extraction") == ()
        assert manifest.headline_capable("span_detection") == ()
        assert manifest.headline_capable("disambiguation") == ()
        assert [corpus.name for corpus in manifest.headline_capable("identifier_segmentation")] == [
            "example"
        ]

    # -- the third role, and the one property it exists to enforce -------------

    def test_a_single_annotator_reference_corpus_passes_when_it_declares_both_fields(
        self, tmp_path: Path
    ) -> None:
        """The control. Without it the four mutations below could pass for the wrong reason."""
        manifest = splits.load(_write(tmp_path, _single_annotator()))
        assert splits.validate(manifest) == []
        assert manifest.corpus("example").adjudicator_count == 1

    @pytest.mark.parametrize("field", ["adjudicators", "pooling_recipe"])
    def test_the_role_required_fields_are_required(self, tmp_path: Path, field: str) -> None:
        """A role that adds no obligation is a synonym for whichever role the reader assumes."""
        problems = splits.validate(splits.load(_write(tmp_path, _single_annotator(drop=field))))
        assert any(field in problem for problem in problems), problems

    def test_an_empty_adjudicator_list_is_not_an_adjudicator(self, tmp_path: Path) -> None:
        """``adjudicators = []`` reads as present and records nobody."""
        body = _single_annotator().replace(
            'adjudicators = ["a. person (author of the pooled extractor)"]', "adjudicators = []"
        )
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("adjudicators" in problem for problem in problems), problems

    def test_a_bare_string_of_names_is_refused_rather_than_counted_as_one(
        self, tmp_path: Path
    ) -> None:
        """``adjudicators = "a, b"`` reads as two people to a human and counts as one.

        The count is the single thing this field is read for -- one adjudicator
        is a reference set and two *may* be a gold standard -- so the shorthand
        is refused instead of wrapped.
        """
        body = _single_annotator().replace(
            'adjudicators = ["a. person (author of the pooled extractor)"]',
            'adjudicators = "a. person, b. person"',
        )
        manifest = splits.load(_write(tmp_path, body))
        problems = splits.validate(manifest)
        assert any("array of names" in problem for problem in problems), problems
        assert manifest.corpus("example").adjudicator_count == 0, (
            "the malformed value must not silently coerce to one adjudicator"
        )

    def test_the_never_headline_role_may_not_be_made_the_headline_role(
        self, tmp_path: Path
    ) -> None:
        """**The test that fails if someone later makes this role headline-capable.**

        Two independent guards, mutated together, because the corpus this role
        was added for is a self-adjudicated set whose wrong filing is one word
        away at all times (D-056). The mutation is that one word: ``[policy]
        headline_requires`` pointed at the role itself.

        The first assertion is that :func:`validate` refuses the edit. The second
        is the one that matters, and it is deliberately not the same check:
        ``headline_capable`` must return the corpus **not at all**, for **every**
        task, even under the bad policy the validator just rejected -- because a
        rule enforced only by a gate is a rule that holds only while the gate is
        run.

        **The fixture is deliberately UNCONTAMINATED**, and the first draft was
        not. ``headline_capable`` excludes a corpus for three independent
        reasons; a contaminated fixture trips two of them, and the assertions
        below then pass with the role filter deleted -- which is exactly what
        happened when the filter was mutated out. Every other exclusion is
        switched off here so the one under test is the only one left.

        The control underneath is the other half: the same fixture with
        ``role = "held_out"`` and the same ``[policy]`` *is* headline-capable, so
        the empty result above is a property of the role and not of the fixture.
        """
        body = _single_annotator(contaminated=False).replace(
            'headline_requires = "held_out"',
            'headline_requires = "single_annotator_reference"',
        )
        manifest = splits.load(_write(tmp_path, body))

        problems = splits.validate(manifest)
        assert any("NEVER_HEADLINE_ROLES" in problem for problem in problems), problems
        assert not any("contaminated" in problem for problem in problems), (
            "the fixture is contaminated, so the exclusion below is not the role's"
        )

        assert manifest.policy.headline_requires == "single_annotator_reference", (
            "the mutation did not take; this test proves nothing"
        )
        assert [corpus.name for corpus in manifest.with_role("single_annotator_reference")] == [
            "example"
        ], "the corpus is not in the mutated headline role; this test proves nothing"
        assert manifest.corpus("example").contaminated is False
        assert manifest.corpus("example").task == "extraction"
        for task in splits.TASKS:
            assert manifest.headline_capable(task) == (), task

        control = splits.load(
            _write(
                tmp_path / "control",
                _single_annotator(contaminated=False).replace(
                    'role = "single_annotator_reference"', 'role = "held_out"'
                ),
            )
        )
        assert [corpus.name for corpus in control.headline_capable("extraction")] == ["example"], (
            "the control is not headline-capable either, so the exclusion above "
            "is a property of the fixture rather than of the role"
        )

    def test_the_never_headline_filter_fires_in_a_shipped_command_that_never_validates(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """**The reason the inner filter is not dead code, run through the CLI.**

        D-063 disclosed that under the shipped ``[policy] headline_requires =
        "held_out"`` the never-headline filter inside ``headline_capable``
        evaluates **zero times**, and that *the braces have only ever fired in a
        test*. The test above is that test: it builds a :class:`Manifest` and
        calls the method. It proves the rule and it does not prove the rule is
        reachable from anything a person runs.

        This one closes that. ``python tools/splits.py --json`` returns before
        :func:`validate` is ever called -- read :func:`main`: ``--json`` prints
        :func:`as_dict` and returns ``0``, and ``problems = validate(manifest)``
        is three lines further down. :func:`as_dict` calls
        ``headline_capable`` for every task. So a manifest whose ``[policy]``
        the validator would refuse still renders a headline-capable list, at
        ``rc=0``, in a shipped command -- and the inner filter is the only rule
        standing between that list and a self-adjudicated corpus.

        The fixture is uncontaminated for the reason the test above gives, and
        here it matters more: on the **real** manifest the one
        ``single_annotator_reference`` corpus is also ``contaminated = true``,
        so deleting the role filter changes no output there under any policy at
        all. That masking is measured in the test below. A corpus in this role
        that nobody has read the misses of yet is the case where this filter is
        the only rule left, and it is the case a fresh single-adjudicator pilot
        produces.
        """
        body = _single_annotator(contaminated=False).replace(
            'headline_requires = "held_out"',
            'headline_requires = "single_annotator_reference"',
        )
        path = _write(tmp_path, body)

        assert splits.main(["--json", "--path", str(path)]) == 0, (
            "--json refused a manifest it does not validate; the premise of this test is gone"
        )
        rendered = json.loads(capsys.readouterr().out)

        assert rendered["policy"]["headline_requires"] == "single_annotator_reference", (
            "the mutation did not take; this test proves nothing"
        )
        assert rendered["corpora"]["example"]["contaminated"] is False, (
            "the fixture is contaminated, so an exclusion below is not the role's"
        )
        assert rendered["corpora"]["example"]["task"] == "extraction"
        for task in splits.TASKS:
            assert rendered["headline_capable"][task] == [], task

        # The control, and it is the half that makes the empty lists mean
        # something: the same fixture, the same unvalidated command, the role
        # and the policy agreeing on a role that is *not* never-headline, and
        # the corpus appears. Without it, four empty lists are equally
        # consistent with `--json` never rendering anything.
        control = _write(
            tmp_path / "control",
            _single_annotator(contaminated=False).replace(
                'role = "single_annotator_reference"', 'role = "held_out"'
            ),
        )
        assert splits.main(["--json", "--path", str(control)]) == 0
        assert json.loads(capsys.readouterr().out)["headline_capable"]["extraction"] == ["example"]

    def test_the_role_filter_changes_no_output_on_the_shipped_manifest(
        self, manifest: object
    ) -> None:
        """**R12's firing count for the never-headline filter, on real data.**

        D-063 reported zero firings under the shipped policy and attributed it
        to ``with_role`` excluding the corpus upstream. That is true and it is
        not the whole reason. Re-derived here across **every** value
        :data:`ROLES` admits, not just the shipped one:

        * ``headline_requires = "held_out"``   -- the filter is evaluated for
          each held-out corpus and each task, and returns ``False`` **never**.
        * ``headline_requires = "tuning"``     -- same, ``False`` **never**.
        * ``headline_requires = "single_annotator_reference"`` -- the filter
          returns ``False`` every time, and **the result is identical either
          way**, because ``federal_register_rules_2024q1`` is also
          ``contaminated = true`` and the contamination rule excludes it on its
          own.

        So on the shipped manifest the braces are redundant three ways rather
        than the one D-063 named, and this test pins that rather than letting
        the next reader believe the filter is load-bearing on real data. It
        recomputes ``headline_capable`` with the role filter dropped -- in the
        test, not by mutating the source -- and asserts the two agree.

        **The day it stops agreeing is the day this test earns its keep.** A
        ``single_annotator_reference`` corpus registered uncontaminated -- a
        fresh pilot whose misses nobody has analysed yet -- makes the role
        filter the only rule left, and this assertion is what says so.
        """
        for role in splits.ROLES:
            probe = dataclasses.replace(
                manifest,  # type: ignore[type-var]
                policy=dataclasses.replace(manifest.policy, headline_requires=role),  # type: ignore[attr-defined]
            )
            for task in splits.TASKS:
                wanted = {corpus.name for corpus in probe.with_task(task)}
                without_the_role_filter = tuple(
                    corpus
                    for corpus in probe.with_role(role)
                    if not corpus.contaminated and corpus.name in wanted
                )
                assert probe.headline_capable(task) == without_the_role_filter, (
                    f"the never-headline filter now changes the answer for role={role!r} "
                    f"task={task!r}. That is not a failure -- it means a corpus in a "
                    "NEVER_HEADLINE role is no longer excluded by anything else, so the "
                    "filter is now the only rule between it and a headline slot. Confirm "
                    "that is intended, then update this test and D-063's firing count."
                )

        never_headline = [
            corpus
            for name in manifest.names  # type: ignore[attr-defined]
            for corpus in [manifest.corpora[name]]  # type: ignore[attr-defined]
            if corpus.role in splits.NEVER_HEADLINE_ROLES
        ]
        assert never_headline, "no corpus holds a never-headline role; this test measures nothing"
        assert all(corpus.contaminated for corpus in never_headline), (
            "a never-headline corpus is uncontaminated, which is exactly the case the "
            "assertion above says makes the role filter load-bearing"
        )

    def test_every_never_headline_role_is_a_role(self) -> None:
        """An exclusion naming a role that does not exist excludes nothing."""
        assert splits.NEVER_HEADLINE_ROLES, "the exclusion list is empty; nothing is excluded"
        assert set(splits.NEVER_HEADLINE_ROLES) <= set(splits.ROLES)
        assert set(splits.ROLE_REQUIRED_FIELDS) <= set(splits.ROLES)
        assert set(splits.ROLE_LABEL) == set(splits.ROLES), (
            "a role with no label renders as UNRECOGNISED; give it one or drop it"
        )

    def test_a_role_label_is_never_borrowed_from_another_role(self, tmp_path: Path) -> None:
        """``label()`` was ``"tuning split" if is_tuning else "held out"``.

        Correct for two roles and a silent overclaim for the third: a
        single-annotator reference set would have printed "held out" in every
        runner header, which is the standing the role exists to deny it.
        """
        manifest = splits.load(_write(tmp_path, _single_annotator()))
        label = manifest.corpus("example").label()
        assert "held out" not in label, label
        assert "single-annotator reference" in label
        assert "1 adjudicator(s)" in label

    def test_headline_capable_refuses_a_task_nobody_declared(self, tmp_path: Path) -> None:
        """A typo must raise, not return ``()``.

        An empty tuple reads as "no corpus covers this", which is a plausible
        answer to a question that was never asked -- and it would silently make
        a runner refuse, or an advisory fire, for a reason nobody could find.
        """
        manifest = splits.load(_write(tmp_path, _MINIMAL))
        with pytest.raises(splits.SplitsError, match="is not one of"):
            manifest.headline_capable("identifier_segmenation")

    # -- reservations, mutated the way the licence-URL rule is -----------------

    def test_a_clean_reservation_passes(self, tmp_path: Path) -> None:
        """The control. Without it every mutation below could pass for the wrong reason."""
        manifest = splits.load(_write(tmp_path, _with_reservation()))
        assert splits.validate(manifest) == []
        assert [entry.arm for entry in manifest.reserved_arms()] == ["train"]

    def test_a_reservation_with_no_trigger_is_reported(self, tmp_path: Path) -> None:
        """The headline case, and the one D-043 is a whole record about.

        An arm reserved with no firing condition is not reserved *for* anything.
        It survives each round because nobody happened to want it, and then
        attracts a proposal it cannot serve -- which is exactly what happened to
        AD ``test.json`` before D-043 gave it a trigger.
        """
        body = _with_reservation(spend_trigger=None)
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("spend_trigger" in problem for problem in problems), problems

    def test_an_allocation_with_no_way_to_lapse_is_reported(self, tmp_path: Path) -> None:
        """Permanent by omission is not the same as permanent by decision.

        D-047 wrote a lapse trigger because priority must not transfer by
        default -- and must not be immovable either.
        """
        body = _with_reservation(lapse_trigger=None)
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("lapse_trigger" in problem for problem in problems), problems

    def test_two_reservations_on_one_arm_are_reported(self, tmp_path: Path) -> None:
        """The collision D-043 found and D-047 had to resolve by hand.

        One unread split, two live claims, and whichever runner touches it first
        decides. Written as two structures it is a contradiction the file can
        refuse before anybody runs anything.
        """
        body = _with_reservation() + (
            "\n[[corpora.example.reservations]]\n"
            'arm = "train"\n'
            'state = "allocated"\n'
            'decided_in = "D-032"\n'
            "allocated_to = 'experiment nine, the two-word bracketed short form'\n"
            "spend_trigger = 'experiment nine is reopened'\n"
            "lapse_trigger = 'experiment nine is closed for good'\n"
        )
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("CONTRADICT" in problem for problem in problems), problems

    def test_an_unallocated_arm_that_names_an_allocation_is_reported(self, tmp_path: Path) -> None:
        """The other contradiction shape: a state at odds with its own fields."""
        body = _with_reservation(state='"unallocated"', lapse_trigger=None)
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("Contradiction" in problem for problem in problems), problems

    def test_a_lapse_trigger_on_something_that_is_not_an_allocation_is_reported(
        self, tmp_path: Path
    ) -> None:
        body = _with_reservation(state='"unallocated"', allocated_to=None)
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("only an allocation can lapse" in problem for problem in problems), problems

    def test_one_event_as_both_triggers_is_reported(self, tmp_path: Path) -> None:
        """An allocation that lapses on the event that fires it cannot be acted on."""
        body = _with_reservation(
            spend_trigger="'the legend workstream publishes a cost'",
            lapse_trigger="'the legend workstream publishes a cost'",
        )
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("same event" in problem for problem in problems), problems

    def test_a_spent_arm_must_say_what_spent_it(self, tmp_path: Path) -> None:
        """A spend nobody can point at is a contamination with no evidence."""
        body = _with_reservation(state='"spent"', allocated_to=None, lapse_trigger=None)
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("spent_in" in problem for problem in problems), problems

    def test_an_unknown_reservation_key_is_refused(self, tmp_path: Path) -> None:
        """A misspelt trigger key would drop the trigger silently.

        The corpus table preserves unknown keys in ``extra``; a reservation
        refuses them, and the asymmetry is the whole difference between a field
        that is decoration and a field that is load-bearing. ``train_allocation``
        itself was such a key -- valid TOML the loader neither validated nor
        rendered.
        """
        body = _with_reservation() + "laps_trigger = 'a typo that eats the trigger'\n"
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("unrecognised key" in problem for problem in problems), problems

    def test_an_arm_written_as_a_filename_is_refused(self, tmp_path: Path) -> None:
        """The guard is a literal match, so the reserved string must be the runner's.

        Reserving ``"train.json"`` while every reader passes ``split="train"``
        is a guard that can never fire -- a reservation that validates, renders,
        and refuses nothing, which is the failure being fixed wearing the new
        schema.
        """
        body = _with_reservation(arm='"train.json"')
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("split token" in problem for problem in problems), problems

    @pytest.mark.parametrize("value", ['"held"', '"D047"', "None"])
    def test_a_reservation_with_no_usable_record_is_reported(
        self, tmp_path: Path, value: str
    ) -> None:
        """ "Reserved" with no record behind it cannot be argued down or re-designated."""
        body = _with_reservation(decided_in=None if value == "None" else value)
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("decided_in" in problem for problem in problems), problems

    def test_an_unknown_reservation_state_is_reported(self, tmp_path: Path) -> None:
        body = _with_reservation(state='"pencilled_in"')
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("state" in problem for problem in problems), problems

    def test_a_reservation_written_as_prose_again_is_reported(self, tmp_path: Path) -> None:
        """The regression that matters: the old ``train_allocation`` shape, renamed.

        A structural defect is reported beside the other findings rather than
        raised over them, so one malformed entry does not suppress the report
        that would have listed the other nine.
        """
        body = _MINIMAL + '\nreservations = "ALLOCATED. 3,564 unread samples, one read."\n'
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("array of tables" in problem for problem in problems), problems

    def test_a_reservations_element_that_is_not_a_table_is_reported(self, tmp_path: Path) -> None:
        body = _MINIMAL + '\nreservations = ["train"]\n'
        problems = splits.validate(splits.load(_write(tmp_path, body)))
        assert any("is not a table" in problem for problem in problems), problems

    def test_the_cli_exits_non_zero_on_a_contradictory_reservation(self, tmp_path: Path) -> None:
        """The CI contract: a malformed reservation reds the build like any other rule."""
        body = _with_reservation(spend_trigger=None)
        assert splits.main(["--check", "--path", str(_write(tmp_path, body))]) == 1

    def test_the_cli_exits_non_zero_on_an_invalid_manifest(self, tmp_path: Path) -> None:
        """The CI step's contract: an invalid manifest reds the build."""
        path = _write(tmp_path, _mutated("licence_url", None))
        assert splits.main(["--check", "--path", str(path)]) == 1

    def test_the_cli_exits_non_zero_on_an_unparseable_manifest(self, tmp_path: Path) -> None:
        assert splits.main(["--check", "--path", str(tmp_path / "absent.toml")]) == 1


# ---------------------------------------------------------------------------
# the accessor
# ---------------------------------------------------------------------------
class TestTheAccessor:
    """The typed half, which is what makes a runner able to consult the file."""

    def test_an_undeclared_corpus_says_what_is_declared(self, manifest: object) -> None:
        with pytest.raises(splits.SplitsError) as caught:
            manifest.corpus("no_such_corpus")
        assert "med1250" in str(caught.value)

    def test_require_role_refuses_a_mislabelled_figure(self, manifest: object) -> None:
        """Operating rule 2, made mechanical for a runner that prints a label."""
        manifest.corpus("med1250").require_role("tuning")
        with pytest.raises(splits.SplitsError, match="not 'held_out'"):
            manifest.corpus("med1250").require_role("held_out")

    def test_require_task_refuses_a_corpus_of_the_wrong_shape(self, manifest: object) -> None:
        """The partner of :meth:`require_role`, and it guards the other half of the contract.

        A runner that scores cut placement is claiming its corpus holds
        identifier/caption pairs. That claim used to live only in a docstring.
        """
        manifest.corpus("sec_xbrl").require_task("identifier_segmentation")
        with pytest.raises(splits.SplitsError, match="not 'extraction'"):
            manifest.corpus("sec_xbrl").require_task("extraction")

    def test_headline_capable_reports_the_gap_rather_than_hiding_it(self, manifest: object) -> None:
        """There is still no uncontaminated held-out pair corpus, and that must show."""
        assert manifest.headline_capable("extraction") == ()
        for task in splits.TASKS:
            for corpus in manifest.headline_capable(task):
                assert corpus.is_held_out and not corpus.contaminated
                assert corpus.task == task

    def test_declaring_the_spend_is_what_opens_a_reserved_arm(self, tmp_path: Path) -> None:
        """The handshake, end to end: refused, declared, permitted.

        The declaration is process-local on purpose -- a runner that could mark
        its own arm spent in ``bench/splits.toml`` would be spending it with no
        commit and no review.
        """
        manifest = splits.load(_write(tmp_path, _with_reservation()))
        corpus = manifest.corpus("example")
        with pytest.raises(splits.SplitsError, match="RESERVED"):
            corpus.require_unreserved("train")

        log = io.StringIO()
        spent = corpus.declare_spend(
            "train",
            decision="D-047",
            purpose="legend precision cost, with the two_word row saved beside it",
            stream=log,
        )
        assert spent is not None and spent.arm == "train"
        assert "SPENDING A RESERVED ARM" in log.getvalue()
        assert "two_word" in log.getvalue(), "the purpose must reach the run log"
        corpus.require_unreserved("train")
        assert splits.declared_spends()[("example", "train")].startswith("legend precision")

    def test_a_spend_must_name_the_record_that_allocated_the_arm(self, tmp_path: Path) -> None:
        """Spending under another record is a RE-ALLOCATION, not an argument.

        D-047's own words: priority does not transfer by default. A runner that
        could name any record would be re-allocating the arm at run time,
        which is the collision the allocation was written to settle.
        """
        corpus = splits.load(_write(tmp_path, _with_reservation())).corpus("example")
        with pytest.raises(splits.SplitsError, match="RE-ALLOCATION"):
            corpus.declare_spend(
                "train", decision="D-032", purpose="experiment nine", stream=io.StringIO()
            )
        with pytest.raises(splits.SplitsError, match="purpose"):
            corpus.declare_spend("train", decision="D-047", purpose="  ", stream=io.StringIO())
        assert splits.declared_spends() == {}, "a refused spend must not open the arm"

    def test_declaring_a_spend_on_an_unreserved_arm_costs_nothing(self, tmp_path: Path) -> None:
        """The ergonomic claim, checked rather than argued.

        A reader may call the guard unconditionally without knowing which arms
        are spoken for. If complying were more expensive than that, runners
        would route around it -- which is the failure mode the mechanism is
        designed against, not a hypothetical.
        """
        corpus = splits.load(_write(tmp_path, _with_reservation())).corpus("example")
        log = io.StringIO()
        assert corpus.declare_spend("dev", decision="D-047", purpose="x", stream=log) is None
        assert log.getvalue() == ""
        corpus.require_unreserved("dev")

    def test_a_spent_arm_no_longer_refuses_anything(self, tmp_path: Path) -> None:
        """The cost has been paid; the corpus entry above is where it is recorded.

        Keeping a spent arm refusing would push the next reader to delete the
        reservation, which is how the record of what was spent disappears.
        """
        body = (
            _with_reservation(state='"spent"', allocated_to=None, lapse_trigger=None)
            + "spent_in = 'shortform.sdu22_ae_legal_train.legend_cost'\n"
        )
        manifest = splits.load(_write(tmp_path, body))
        assert splits.validate(manifest) == []
        manifest.corpus("example").require_unreserved("train")

    def test_the_ledger_cannot_be_opened_by_mutating_the_copy(self, tmp_path: Path) -> None:
        """``declared_spends()`` hands out a copy; ``declare_spend`` is the only door."""
        corpus = splits.load(_write(tmp_path, _with_reservation())).corpus("example")
        splits.declared_spends()[("example", "train")] = "granted by a caller"
        with pytest.raises(splits.SplitsError, match="RESERVED"):
            corpus.require_unreserved("train")

    def test_notes_never_fail_a_build(self, manifest: object) -> None:
        """Advisories are advisories: a gate that reds with the passage of time
        fires on an unrelated commit, which is the gate people learn to ignore."""
        assert isinstance(splits.notes(manifest), list)
        far_future = datetime.date.today() + datetime.timedelta(days=10_000)
        assert splits.notes(manifest, today=far_future)
        assert splits.validate(manifest, today=far_future) == []

    def test_as_dict_is_json_safe(self, manifest: object) -> None:
        import json

        json.dumps(splits.as_dict(manifest))

    def test_as_dict_reports_the_reserved_arms(self, manifest: object) -> None:
        """ "What may this round not touch?" is now one question against one file."""
        rendered = splits.as_dict(manifest)
        reserved = {(row["corpus"], row["arm"]) for row in rendered["reserved_arms"]}
        assert ("sdu22_ae_legal", "train") in reserved
        assert ("sdu21_ad", "test") in reserved
        assert rendered["corpora"]["sdu22_ae_scientific"]["reserved_arms"] == ["train"]
        assert rendered["corpora"]["plod"]["reserved_arms"] == []

    def test_as_dict_reports_headline_capability_per_task(self, manifest: object) -> None:
        """The JSON view offers no pooled list, because a pooled list was the hole."""
        rendered = splits.as_dict(manifest)
        assert set(rendered["headline_capable"]) == set(splits.TASKS)
        assert rendered["headline_capable"]["extraction"] == []
        assert sorted(rendered["headline_capable"]["identifier_segmentation"]) == [
            "sec_xbrl",
            "socrata",
        ]


# ---------------------------------------------------------------------------
# the segmentation reader
# ---------------------------------------------------------------------------
@needs_corpora
class TestTheSegmentationReader:
    """``bench/corpora.py`` returns a type for the new task, and refuses to guess.

    No network and no fetched corpus: every case below is a cache envelope
    written into ``tmp_path``, which is the shape
    ``bench/run_governed_gold.py`` writes.
    """

    ENVELOPE = (
        '{"fetched_on": "2026-08-24", "payload": '
        '[["_2013_q1_actual", "2013 Q1 Actual", "portal.example"], '
        '["end_date", "End Date", "portal.example"]]}'
    )

    def test_it_returns_a_container_that_names_its_own_population(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The fetch date is part of the corpus's identity, so the type carries it.

        Socrata's catalog is live and re-orders under the scroll. A reader that
        returned bare rows would hand back a population nobody could name.
        """
        monkeypatch.setattr(corpora, "GOVERNED_GOLD_CACHE", tmp_path)
        (tmp_path / "socrata_80pages_v2.json").write_text(self.ENVELOPE, encoding="utf-8")
        loaded = corpora.read_governed_gold("socrata")
        assert loaded.fetched_on == "2026-08-24"
        assert loaded.source == "socrata_80pages_v2.json"
        assert [pair.identifier for pair in loaded.pairs] == ["_2013_q1_actual", "end_date"]
        assert loaded.pairs[0].caption == "2013 Q1 Actual"
        assert loaded.pairs[0].author == "portal.example"

    def test_it_is_not_a_document_corpus(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The separation that makes the task safe, asserted rather than described.

        ``read_plod_cw_text`` documents a *soft* trap: it returns a real
        ``GoldDocument`` with ``pairs=()``, so a pair runner reports a
        meaningless zero. A segmentation record cannot do even that -- it has no
        ``text`` and no ``tokens``, so a pair or span consumer dies rather than
        producing a number.
        """
        monkeypatch.setattr(corpora, "GOVERNED_GOLD_CACHE", tmp_path)
        (tmp_path / "sec_xbrl_2025q1.json").write_text(self.ENVELOPE, encoding="utf-8")
        pair = corpora.read_governed_gold("sec_xbrl").pairs[0]
        assert not hasattr(pair, "text")
        assert not hasattr(pair, "tokens")
        assert not hasattr(pair, "pairs")

    def test_two_snapshots_are_refused_rather_than_ranked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Two caches are two populations of a live catalog, not two files.

        Picking the newest would put the choice of *which corpus was measured*
        inside the number, silently. Both are on disk in this repository right
        now, which is why this is a designed failure rather than a hypothetical.
        """
        monkeypatch.setattr(corpora, "GOVERNED_GOLD_CACHE", tmp_path)
        (tmp_path / "socrata_80pages.json").write_text(self.ENVELOPE, encoding="utf-8")
        (tmp_path / "socrata_80pages_v2.json").write_text(self.ENVELOPE, encoding="utf-8")
        with pytest.raises(SystemExit, match="different populations"):
            corpora.read_governed_gold("socrata")
        named = corpora.read_governed_gold("socrata", path=tmp_path / "socrata_80pages.json")
        assert named.source == "socrata_80pages.json"

    def test_a_missing_snapshot_says_how_to_get_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(corpora, "GOVERNED_GOLD_CACHE", tmp_path)
        with pytest.raises(SystemExit, match="run_governed_gold"):
            corpora.read_governed_gold("sec_xbrl")

    def test_a_file_that_is_not_a_cache_envelope_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(corpora, "GOVERNED_GOLD_CACHE", tmp_path)
        (tmp_path / "sec_xbrl_2025q1.json").write_text("[[1, 2]]", encoding="utf-8")
        with pytest.raises(SystemExit, match="cache envelope"):
            corpora.read_governed_gold("sec_xbrl")

    def test_load_names_the_right_registry_for_a_corpus_of_another_shape(self) -> None:
        """``unknown corpus`` reads like a typo, and sends the caller hunting for one."""
        with pytest.raises(SystemExit, match="SEGMENTATION_READERS"):
            corpora.load("sec_xbrl")
        with pytest.raises(SystemExit, match="DISAMBIGUATION_READERS"):
            corpora.load("sdu21_ad")
        with pytest.raises(SystemExit, match="unknown corpus"):
            corpora.load("no_such_corpus")
