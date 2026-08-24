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

Nothing here reaches the network or needs a fetched corpus.
"""

from __future__ import annotations

import datetime
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional

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


splits = _load_tool()
corpora = _load_corpora()

#: 3.9 and 3.10 have no ``tomllib``, and ``tomli`` is not a declared dev
#: dependency, so on those interpreters there is no parser to test with. The
#: dedicated CI step runs on 3.12, where this is never skipped.
_NO_PARSER = sys.version_info < (3, 11) and importlib.util.find_spec("tomli") is None

pytestmark = [
    pytest.mark.skipif(not SPLITS.is_file(), reason="not a source checkout"),
    pytest.mark.skipif(_NO_PARSER, reason="tomllib is 3.11+; tomli not installed"),
]


@pytest.fixture(scope="module")
def manifest() -> object:
    """The real manifest, parsed by the real loader."""
    return splits.load(SPLITS)


def _write(tmp_path: Path, body: str) -> Path:
    """A throwaway manifest, so a negative test never edits the real file."""
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

    def test_every_task_in_the_vocabulary_has_a_registry_and_a_gold_unit(self) -> None:
        """A task with no type behind it is a word, which is what the vocabulary is not."""
        assert set(corpora.TASK_REGISTRIES) == set(splits.TASKS)
        assert set(splits.TASK_GOLD_UNIT) == set(splits.TASKS)
        for task in splits.TASKS:
            assert splits.TASK_GOLD_UNIT[task].strip(), task

    def test_med1250_is_still_a_tuning_split(self, manifest: object) -> None:
        """Operating rule 2, in the file it lives in."""
        assert manifest.corpus("med1250").is_tuning
        assert manifest.corpus("med1250").label() == "tuning split, contaminated"

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

    def test_headline_capable_refuses_a_task_nobody_declared(self, tmp_path: Path) -> None:
        """A typo must raise, not return ``()``.

        An empty tuple reads as "no corpus covers this", which is a plausible
        answer to a question that was never asked -- and it would silently make
        a runner refuse, or an advisory fire, for a reason nobody could find.
        """
        manifest = splits.load(_write(tmp_path, _MINIMAL))
        with pytest.raises(splits.SplitsError, match="is not one of"):
            manifest.headline_capable("identifier_segmenation")

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
