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


splits = _load_tool()

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

    def test_headline_capable_reports_the_gap_rather_than_hiding_it(self, manifest: object) -> None:
        """There is still no uncontaminated held-out pair corpus, and that must show."""
        for corpus in manifest.headline_capable():
            assert corpus.is_held_out and not corpus.contaminated

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
