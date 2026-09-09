"""``tools/run_summary.py``: the schema, the reader, the gate -- and a real kill.

Why this module is shaped the way it is
---------------------------------------
The thing under test exists because **three consecutive rounds kept their work
and lost their account of it** (D-095, D-098). Its whole claim is that a record
written before the prose survives an agent that dies writing the prose.

**A mechanism whose point is surviving a crash may not be tested against a clean
run.** So :class:`TestAKilledWriter` spawns a real child process, waits until it
has filed, and kills it -- ``Popen.kill``, which is ``TerminateProcess`` on
Windows and ``SIGKILL`` elsewhere: no handlers run, no buffers flush, no
``finally`` executes. Then it asks the reader what it can see. One child is
killed *after* an atomic write and must come back ``complete``; another is killed
*during* a non-atomic write and must come back ``unreadable`` -- which is a
different fact from ``absent``, and that difference is the deliverable.

The rest is the ordinary shape: every refusal the validator makes is exercised
in both directions, and the two copies of the schema -- this file's, and
``CONTRIBUTING.md``'s -- are checked against the code rather than against each
other's memory.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LOADER = REPO_ROOT / "tools" / "run_summary.py"
GATES = REPO_ROOT / ".github" / "gates.toml"
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

#: `tomllib` is 3.11+ and `tomli` is not a declared dev dependency, so on 3.9
#: and 3.10 there may be no parser for a roster. The house guard.
_NO_PARSER = sys.version_info < (3, 11) and importlib.util.find_spec("tomli") is None
needs_parser = pytest.mark.skipif(_NO_PARSER, reason="tomllib is 3.11+; tomli not installed")
needs_register = pytest.mark.skipif(not GATES.is_file(), reason="not a source checkout")


def _load() -> ModuleType:
    """Import ``tools/run_summary.py`` by path.

    ``tools/`` is a directory of scripts and must not become a package: making
    it importable for a test's convenience would change the shape of the thing
    under test. Same mechanism as ``tests/test_gate_manifest.py``.
    """
    spec = importlib.util.spec_from_file_location("_run_summary_under_test", LOADER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rs = _load()


def _valid(label: str = "alpha", **overrides: Any) -> Dict[str, Any]:
    """A summary that passes, so every mutation below has one thing wrong."""
    payload: Dict[str, Any] = {
        "label": label,
        "status": "complete",
        "headline": "The reader can tell an absence from a stub, and that is the deliverable.",
        "shipped": ["tools/run_summary.py"],
        "run_ids": ["34308556192"],
        "files_changed": ["tools/run_summary.py"],
        "pre_registration": "Falsified if a killed writer's record could not be read back.",
        "how_it_fails": "It makes a lost report recoverable; it does not make a report happen.",
        "not_done": ["a launcher-side start record"],
        "gates": dict.fromkeys(rs.GATE_KEYS, "green"),
        "claims_for_sampling": [f"Checkable sentence number {n}." for n in range(1, 13)],
    }
    payload.update(overrides)
    return payload


def _roster(
    directory: Path,
    expected: List[str],
    complete: bool = False,
    extra: str = "",
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    body = (
        'round = "fixture"\n'
        'roster_written_by = "a test"\n'
        f"roster_complete = {'true' if complete else 'false'}\n"
        f"expected = {json.dumps(expected)}\n"
    )
    (directory / rs.ROSTER_NAME).write_text(body + extra, encoding="utf-8")


def _file(directory: Path, label: str, payload: Any) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{label}.json"
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# the schema
# ---------------------------------------------------------------------------
class TestTheSchema:
    """Every refusal, in both directions. A rule only tested one way is a rule
    that may be firing on everything."""

    def test_a_valid_summary_is_accepted(self) -> None:
        assert rs.validate_summary(_valid(), stem="alpha") == []

    @pytest.mark.parametrize("field", [name for name, _ in rs.REQUIRED_FIELDS])
    def test_every_required_field_is_required(self, field: str) -> None:
        payload = _valid()
        del payload[field]
        problems = rs.validate_summary(payload, stem="alpha")
        assert any(field in problem for problem in problems), (field, problems)

    def test_an_unknown_key_is_refused(self) -> None:
        # bench/splits.toml learned this the expensive way: a misspelt
        # `laps_trigger` silently dropped the one field the structure existed
        # to require, and nothing was red.
        problems = rs.validate_summary(_valid(how_it_failed="typo"), stem="alpha")
        assert any("how_it_failed" in problem for problem in problems), problems

    def test_a_status_outside_the_two_values_is_refused(self) -> None:
        problems = rs.validate_summary(_valid(status="shipped"), stem="alpha")
        assert any("shipped" in problem for problem in problems), problems

    @pytest.mark.parametrize("count", [0, 11, 13])
    def test_the_sampling_claims_are_exactly_twelve(self, count: int) -> None:
        payload = _valid(claims_for_sampling=[f"s{n}" for n in range(count)])
        problems = rs.validate_summary(payload, stem="alpha")
        assert any(str(rs.CLAIMS_REQUIRED) in problem for problem in problems), problems

    def test_a_blank_sampling_claim_is_refused(self) -> None:
        claims = [f"Checkable sentence number {n}." for n in range(1, 13)]
        claims[4] = "   "
        problems = rs.validate_summary(_valid(claims_for_sampling=claims), stem="alpha")
        assert any("blank" in problem for problem in problems), problems

    def test_a_missing_gate_key_is_refused(self) -> None:
        gates = dict.fromkeys(rs.GATE_KEYS, "green")
        del gates["ruff_format"]
        problems = rs.validate_summary(_valid(gates=gates), stem="alpha")
        assert any("ruff_format" in problem for problem in problems), problems

    def test_an_unknown_gate_key_is_refused(self) -> None:
        gates = dict.fromkeys(rs.GATE_KEYS, "green")
        gates["pylint"] = "green"
        problems = rs.validate_summary(_valid(gates=gates), stem="alpha")
        assert any("pylint" in problem for problem in problems), problems

    def test_ruff_and_ruff_format_are_two_keys(self) -> None:
        # The hardening over the maintainer's seven-key sketch: one key for two
        # commands lets an agent report `ruff: green` while the formatter is red.
        assert "ruff" in rs.GATE_KEYS and "ruff_format" in rs.GATE_KEYS
        assert len(rs.GATE_KEYS) == len(set(rs.GATE_KEYS)) == 8

    def test_a_label_that_disagrees_with_its_filename_is_refused(self) -> None:
        problems = rs.validate_summary(_valid(label="alpha"), stem="beta")
        assert any("beta" in problem for problem in problems), problems

    def test_a_label_that_is_not_a_slug_is_refused(self) -> None:
        problems = rs.validate_summary(_valid(label="Alpha Workstream"), stem="Alpha Workstream")
        assert problems

    @pytest.mark.parametrize(
        "field,value",
        [
            ("headline", 3),
            ("shipped", "not a list"),
            ("run_ids", [7]),
            ("gates", "green"),
            ("claims_for_sampling", "twelve"),
        ],
    )
    def test_the_wrong_type_is_refused(self, field: str, value: Any) -> None:
        assert rs.validate_summary(_valid(**{field: value}), stem="alpha")

    def test_a_json_array_is_not_a_summary(self) -> None:
        assert rs.validate_summary([1, 2, 3], stem="alpha")


# ---------------------------------------------------------------------------
# vacuity: filed and saying nothing
# ---------------------------------------------------------------------------
class TestFiledAndSayingNothing:
    """``vacuous`` is reported and never refused, and the asymmetry is the design."""

    def test_the_template_is_vacuous_by_construction(self) -> None:
        skeleton = rs.template("alpha")
        assert rs.validate_summary(skeleton, stem="alpha") == []
        assert rs.is_vacuous(skeleton)

    def test_a_vacuous_summary_is_valid(self) -> None:
        # It must stay writable: a stub filed by an agent that knew it was
        # about to die is worth more than nothing.
        payload = _valid(headline="", pre_registration="  ", how_it_fails="n/a")
        assert rs.validate_summary(payload, stem="alpha") == []
        assert rs.state_of(payload, []) == "vacuous"

    def test_one_substantive_narrative_field_is_enough(self) -> None:
        payload = _valid(headline="", pre_registration="")
        assert not rs.is_vacuous(payload)
        assert rs.state_of(payload, []) == "complete"

    @pytest.mark.parametrize("text", ["", "  ", "-", "n/a", "TODO", "tbd", "short"])
    def test_dead_text_is_a_placeholder(self, text: str) -> None:
        assert rs.is_placeholder(text)

    def test_a_real_sentence_is_not_a_placeholder(self) -> None:
        assert not rs.is_placeholder("A roster is what makes an absence sayable.")


# ---------------------------------------------------------------------------
# the reader
# ---------------------------------------------------------------------------
@needs_parser
class TestTheReader:
    """Six states, and the two that matter are ``absent`` and ``vacuous``."""

    def test_every_state_is_reachable_and_distinct(self, tmp_path: Path) -> None:
        _roster(tmp_path, ["done", "half", "empty", "broken", "torn", "missing"])
        _file(tmp_path, "done", _valid("done"))
        _file(tmp_path, "half", _valid("half", status="partial"))
        _file(tmp_path, "empty", rs.template("empty"))
        _file(tmp_path, "broken", _valid("broken", status="nope"))
        _file(tmp_path, "torn", '{"label": "torn", "status": "comp')

        report = rs.report(tmp_path)
        states = {v.label: v.state for v in report.verdicts}
        assert states == {
            "done": "complete",
            "half": "partial",
            "empty": "vacuous",
            "broken": "invalid",
            "torn": "unreadable",
            "missing": "absent",
        }

    def test_absent_is_not_the_same_verdict_as_saying_nothing(self, tmp_path: Path) -> None:
        # THE DELIVERABLE, ASSERTED DIRECTLY. This is the distinction `--check`
        # could not make for the cold-read ledger, and D-096 records the cost.
        _roster(tmp_path, ["filed-nothing", "never-filed"])
        _file(tmp_path, "filed-nothing", rs.template("filed-nothing"))
        report = rs.report(tmp_path)
        states = {v.label: v.state for v in report.verdicts}
        assert states["filed-nothing"] == "vacuous"
        assert states["never-filed"] == "absent"
        assert states["filed-nothing"] != states["never-filed"]
        filed = {v.label: v.filed for v in report.verdicts}
        assert filed == {"filed-nothing": True, "never-filed": False}

    def test_a_directory_with_no_roster_is_not_a_round(self, tmp_path: Path) -> None:
        _file(tmp_path, "orphan", _valid("orphan"))
        report = rs.report(tmp_path)
        assert not report.reconstructible
        assert report.verdicts == ()
        assert any("roster" in problem for problem in report.roster_problems)

    def test_what_survived_is_printed_even_with_no_roster(self, tmp_path: Path) -> None:
        # THE CRISIS CASE. The directory most likely to have no roster is a
        # shared scratchpad an agent wrote into under pressure, and a reader
        # that went silent on exactly that directory would be useless in the
        # only situation it exists for. What is lost without a roster is the
        # ABSENCES, and only those.
        _file(tmp_path, "orphan", _valid("orphan"))
        printed = rs.render(rs.report(tmp_path))
        assert "orphan" in printed and "COMPLETE" in printed
        assert "not computable" in printed

    def test_a_rosterless_directory_with_nothing_in_it_says_so(self, tmp_path: Path) -> None:
        printed = rs.render(rs.report(tmp_path))
        assert "no summary is on disk either" in printed

    def test_an_empty_directory_and_a_missing_one_both_report_rather_than_crash(
        self, tmp_path: Path
    ) -> None:
        assert not rs.report(tmp_path).reconstructible
        assert not rs.report(tmp_path / "nope").reconstructible

    def test_a_summary_nobody_expected_is_reported_rather_than_dropped(
        self, tmp_path: Path
    ) -> None:
        _roster(tmp_path, ["expected-one"])
        _file(tmp_path, "expected-one", _valid("expected-one"))
        _file(tmp_path, "gatecrasher", _valid("gatecrasher"))
        report = rs.report(tmp_path)
        assert [v.label for v in report.unexpected] == ["gatecrasher"]

    def test_the_counts_name_every_state_even_at_zero(self, tmp_path: Path) -> None:
        # A tally that omits its zeroes reads as a clean round.
        _roster(tmp_path, ["one"])
        _file(tmp_path, "one", _valid("one"))
        assert set(rs.report(tmp_path).counts()) == set(rs.STATES)

    def test_gaps_are_everything_that_is_not_a_report(self, tmp_path: Path) -> None:
        _roster(tmp_path, ["done", "empty", "missing"])
        _file(tmp_path, "done", _valid("done"))
        _file(tmp_path, "empty", rs.template("empty"))
        assert {v.label for v in rs.report(tmp_path).gaps} == {"empty", "missing"}

    def test_a_roster_with_an_unknown_key_is_refused(self, tmp_path: Path) -> None:
        _roster(tmp_path, ["one"], extra="roster_complet = true\n")
        report = rs.report(tmp_path)
        assert not report.reconstructible
        assert any("roster_complet" in problem for problem in report.roster_problems)

    def test_a_roster_missing_a_required_key_is_refused(self, tmp_path: Path) -> None:
        tmp_path.joinpath(rs.ROSTER_NAME).write_text('round = "x"\n', encoding="utf-8")
        assert any("declare" in p for p in rs.report(tmp_path).roster_problems)

    def test_a_duplicated_label_in_the_roster_is_refused(self, tmp_path: Path) -> None:
        _roster(tmp_path, ["one", "one"])
        assert any("more than once" in p for p in rs.report(tmp_path).roster_problems)

    def test_the_render_prints_the_two_limits_it_cannot_close(self, tmp_path: Path) -> None:
        _roster(tmp_path, ["missing"])
        printed = rs.render(rs.report(tmp_path))
        assert "LOWER BOUND" in printed
        assert "never launched" in printed


# ---------------------------------------------------------------------------
# a real kill, which is the only test that can establish the claim
# ---------------------------------------------------------------------------
def _wait_for(path: Path, deadline: float = 30.0) -> bool:
    """Poll until ``path`` exists, or the deadline passes."""
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        if path.exists():
            return True
        time.sleep(0.05)
    return False


def _kill_after(script: str, signal_file: Path, tmp_path: Path) -> None:
    """Run ``script`` and kill it once ``signal_file`` appears.

    ``Popen.kill`` is ``TerminateProcess`` on Windows and ``SIGKILL`` elsewhere:
    no handler runs, nothing is flushed, no ``finally`` executes. That is the
    failure this mechanism exists for and there is no way to establish the claim
    without producing one.
    """
    source = tmp_path / "writer.py"
    source.write_text(script, encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, str(source)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        arrived = _wait_for(signal_file)
        assert arrived, "the writer never reached the point this test kills it at"
    finally:
        process.kill()
        process.wait(timeout=30)


#: A writer stalled *inside* :func:`tools.run_summary.write_summary`, with
#: ``os.replace`` held open so the kill lands in the window between "the bytes
#: are on disk" and "the record is at the path a reader reads".
_STALLED_WRITER = (
    "import importlib.util, json, os, pathlib, sys, time\n"
    "spec = importlib.util.spec_from_file_location('rs', %(loader)r)\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "sys.modules['rs'] = mod\n"
    "spec.loader.exec_module(mod)\n"
    "real = os.replace\n"
    "def stalled(src, dst):\n"
    "    pathlib.Path(%(flag)r).write_text('x', encoding='utf-8')\n"
    "    time.sleep(600)\n"
    "    real(src, dst)\n"
    "mod.os.replace = stalled\n"
    "payload = json.loads(pathlib.Path(%(payload)r).read_text('utf-8'))\n"
    "mod.write_summary(pathlib.Path(%(target)r), payload)\n"
)


@needs_parser
class TestAKilledWriter:
    """The mechanism, tested against a crash rather than against a clean run."""

    def test_a_writer_killed_inside_the_atomic_write_leaves_no_half_record(
        self, tmp_path: Path
    ) -> None:
        # THE TEST THAT STOPS A PHRASING BEING TIGHTER THAN THE MEASUREMENT.
        # `write_summary` claims a killed writer leaves either nothing or a
        # whole file; the two tests below only kill AFTER the write returns,
        # which establishes nothing about the window inside it. Here `os.replace`
        # is stalled, so the kill lands with the bytes in a temporary and the
        # target not yet in place -- and the target must not exist at all. A
        # reader must never see a partial record at the path it reads.
        round_dir = tmp_path / "round"
        _roster(round_dir, ["doomed"])
        target = round_dir / "doomed.json"
        flag = tmp_path / "inside-the-window"
        payload_file = tmp_path / "payload.json"
        payload_file.write_text(json.dumps(_valid("doomed")), encoding="utf-8")

        script = _STALLED_WRITER % {
            "loader": str(LOADER),
            "flag": str(flag),
            "payload": str(payload_file),
            "target": str(target),
        }
        _kill_after(script, flag, tmp_path)

        assert not target.exists(), "a half-written record was visible where a reader reads"
        states = {v.label: v.state for v in rs.report(round_dir).verdicts}
        assert states == {"doomed": "absent"}
        assert [p.name for p in round_dir.iterdir() if p.name.endswith(".tmp")], (
            "the temporary the write goes through was never created, so this test proved nothing"
        )

    def test_a_writer_killed_between_the_json_and_the_prose_is_recovered(
        self, tmp_path: Path
    ) -> None:
        round_dir = tmp_path / "round"
        _roster(round_dir, ["doomed"])
        target = round_dir / "doomed.json"
        prose = tmp_path / "the-long-report.md"
        payload_file = tmp_path / "payload.json"
        payload_file.write_text(json.dumps(_valid("doomed")), encoding="utf-8")

        script = (
            "import importlib.util, json, pathlib, sys, time\n"
            f"spec = importlib.util.spec_from_file_location('rs', {str(LOADER)!r})\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "sys.modules['rs'] = mod\n"
            "spec.loader.exec_module(mod)\n"
            f"payload = json.loads(pathlib.Path({str(payload_file)!r}).read_text('utf-8'))\n"
            f"mod.write_summary(pathlib.Path({str(target)!r}), payload)\n"
            # Everything past this line is the long prose the agent never
            # finishes. The sleep is the ceiling running out.
            "time.sleep(600)\n"
            f"pathlib.Path({str(prose)!r}).write_text('the report', encoding='utf-8')\n"
        )
        _kill_after(script, target, tmp_path)

        assert target.is_file(), "the penultimate write did not survive the kill"
        assert not prose.exists(), "the writer was not killed before its prose"
        report = rs.report(round_dir)
        assert [(v.label, v.state) for v in report.verdicts] == [("doomed", "complete")]
        assert report.gaps == ()

    def test_a_writer_killed_mid_write_is_unreadable_and_not_absent(self, tmp_path: Path) -> None:
        # The distinction the whole deliverable turns on, produced by a real
        # kill rather than by writing a broken file on purpose.
        round_dir = tmp_path / "round"
        _roster(round_dir, ["torn", "never-started"])
        target = round_dir / "torn.json"
        flag = tmp_path / "half-written"

        script = (
            "import json, pathlib, time\n"
            f"text = json.dumps({json.dumps(_valid('torn'))!r})\n"
            f"handle = open({str(target)!r}, 'w', encoding='utf-8')\n"
            "handle.write(text[: len(text) // 2])\n"
            "handle.flush()\n"
            f"pathlib.Path({str(flag)!r}).write_text('x', encoding='utf-8')\n"
            "time.sleep(600)\n"
            "handle.write(text[len(text) // 2 :])\n"
            "handle.close()\n"
        )
        _kill_after(script, flag, tmp_path)

        assert target.is_file()
        states = {v.label: v.state for v in rs.report(round_dir).verdicts}
        assert states["torn"] == "unreadable"
        assert states["never-started"] == "absent"

    def test_no_temporary_file_is_left_where_a_reader_would_read_it(self, tmp_path: Path) -> None:
        # `write_summary` writes a sibling temporary and renames it. A leftover
        # `.tmp` in the round directory would not be read as a summary
        # (`*.json` only), but it would still be litter in the register.
        target = tmp_path / "alpha.json"
        rs.write_summary(target, _valid("alpha"))
        assert sorted(p.name for p in tmp_path.iterdir()) == ["alpha.json"]

    def test_the_writer_refuses_to_file_something_invalid(self, tmp_path: Path) -> None:
        with pytest.raises(rs.RunSummaryError):
            rs.write_summary(tmp_path / "alpha.json", _valid("alpha", status="nope"))
        assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------
def _mirror(tmp_path: Path) -> Path:
    """A root shaped like this repository, holding only what ``check`` reads."""
    root = tmp_path / "root"
    (root / ".github" / "run-summaries" / "r1").mkdir(parents=True)
    root.joinpath("CONTRIBUTING.md").write_text(
        "## Finishing\n\n"
        + rs.CONTRIBUTING_ANCHOR
        + "\n```\n"
        + "\n".join(rs.FIELD_NAMES)
        + "\n```\n",
        encoding="utf-8",
    )
    return root


@needs_parser
class TestTheGate:
    """What reddens the build, and -- as loudly -- what deliberately does not."""

    def test_a_clean_round_passes(self, tmp_path: Path) -> None:
        root = _mirror(tmp_path)
        round_dir = root / ".github" / "run-summaries" / "r1"
        _roster(round_dir, ["one"])
        _file(round_dir, "one", _valid("one"))
        assert rs.check(root) == []

    def test_an_absent_summary_does_not_fail_the_build(self, tmp_path: Path) -> None:
        # THE OMISSION IS THE DESIGN. If absence reddened CI, the cheapest route
        # to green would be deleting the roster entry -- the gate becoming a
        # machine for hiding what it exists to reveal.
        root = _mirror(tmp_path)
        _roster(root / ".github" / "run-summaries" / "r1", ["nobody"])
        assert rs.check(root) == []

    def test_a_vacuous_summary_does_not_fail_the_build(self, tmp_path: Path) -> None:
        root = _mirror(tmp_path)
        round_dir = root / ".github" / "run-summaries" / "r1"
        _roster(round_dir, ["one"])
        _file(round_dir, "one", rs.template("one"))
        assert rs.check(root) == []

    def test_an_invalid_summary_fails_the_build(self, tmp_path: Path) -> None:
        root = _mirror(tmp_path)
        round_dir = root / ".github" / "run-summaries" / "r1"
        _roster(round_dir, ["one"])
        _file(round_dir, "one", _valid("one", status="shipped"))
        assert any("shipped" in problem for problem in rs.check(root))

    def test_an_unreadable_summary_fails_the_build(self, tmp_path: Path) -> None:
        root = _mirror(tmp_path)
        round_dir = root / ".github" / "run-summaries" / "r1"
        _roster(round_dir, ["one"])
        _file(round_dir, "one", "{oops")
        assert any("decodable" in problem for problem in rs.check(root))

    def test_a_round_with_no_roster_fails_the_build(self, tmp_path: Path) -> None:
        root = _mirror(tmp_path)
        _file(root / ".github" / "run-summaries" / "r1", "one", _valid("one"))
        assert any("roster" in problem for problem in rs.check(root))

    def test_a_register_with_no_rounds_fails_rather_than_passing_vacuously(
        self, tmp_path: Path
    ) -> None:
        root = _mirror(tmp_path)
        (root / ".github" / "run-summaries" / "r1").rmdir()
        assert any("vacuously" in problem for problem in rs.check(root))

    def test_a_gatecrasher_is_refused_only_when_the_roster_claims_to_be_complete(
        self, tmp_path: Path
    ) -> None:
        root = _mirror(tmp_path)
        round_dir = root / ".github" / "run-summaries" / "r1"
        _roster(round_dir, ["one"], complete=False)
        _file(round_dir, "one", _valid("one"))
        _file(round_dir, "two", _valid("two"))
        assert rs.check(root) == []
        _roster(round_dir, ["one"], complete=True)
        assert any("complete" in problem for problem in rs.check(root))

    def test_a_dotted_run_id_that_resolves_to_nothing_fails(self, tmp_path: Path) -> None:
        root = _mirror(tmp_path)
        (root / "bench").mkdir()
        root.joinpath("bench", "results.json").write_text(
            json.dumps({"runs": {"governed_gold.socrata.columns": {}}}), encoding="utf-8"
        )
        round_dir = root / ".github" / "run-summaries" / "r1"
        _roster(round_dir, ["one"])
        _file(round_dir, "one", _valid("one", run_ids=["monoculture.nope"]))
        assert any("resolves to no run" in problem for problem in rs.check(root))

    def test_a_bare_ci_run_id_is_not_checked_against_bench_results(self, tmp_path: Path) -> None:
        # A CI run id lives in the Actions tab, not in bench/results.json. A
        # rule demanding both would be wrong about half its inputs.
        root = _mirror(tmp_path)
        (root / "bench").mkdir()
        root.joinpath("bench", "results.json").write_text(
            json.dumps({"runs": {"a.b": {}}}), encoding="utf-8"
        )
        round_dir = root / ".github" / "run-summaries" / "r1"
        _roster(round_dir, ["one"])
        _file(round_dir, "one", _valid("one", run_ids=["34308556192"]))
        assert rs.check(root) == []

    def test_a_drifted_field_list_in_contributing_fails(self, tmp_path: Path) -> None:
        root = _mirror(tmp_path)
        round_dir = root / ".github" / "run-summaries" / "r1"
        _roster(round_dir, ["one"])
        _file(round_dir, "one", _valid("one"))
        contributing = root / "CONTRIBUTING.md"
        contributing.write_text(
            contributing.read_text(encoding="utf-8").replace("how_it_fails", "how_it_failed"),
            encoding="utf-8",
        )
        assert any("CONTRIBUTING.md publishes" in problem for problem in rs.check(root))

    def test_contributing_with_no_anchor_fails(self, tmp_path: Path) -> None:
        root = _mirror(tmp_path)
        round_dir = root / ".github" / "run-summaries" / "r1"
        _roster(round_dir, ["one"])
        _file(round_dir, "one", _valid("one"))
        root.joinpath("CONTRIBUTING.md").write_text("nothing here\n", encoding="utf-8")
        assert any("anchor" in problem for problem in rs.check(root))


# ---------------------------------------------------------------------------
# the CLI
# ---------------------------------------------------------------------------
@needs_parser
class TestTheCommandLine:
    def test_report_exits_two_when_the_round_cannot_be_reconstructed(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert rs.main(["--report", str(tmp_path)]) == 2
        assert "NOT RECONSTRUCTIBLE" in capsys.readouterr().out

    def test_report_exits_zero_on_a_round_with_gaps(self, tmp_path: Path) -> None:
        # A reader that refused to read a broken round would be useless in the
        # only situation it exists for.
        _roster(tmp_path, ["missing"])
        assert rs.main(["--report", str(tmp_path)]) == 0

    def test_strict_exits_one_on_a_gap(self, tmp_path: Path) -> None:
        _roster(tmp_path, ["missing"])
        assert rs.main(["--report", str(tmp_path), "--strict"]) == 1

    def test_the_json_report_carries_every_state(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _roster(tmp_path, ["one", "missing"])
        _file(tmp_path, "one", _valid("one"))
        assert rs.main(["--report", str(tmp_path), "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["counts"]["absent"] == 1
        assert payload["roster_complete"] is False

    def test_validate_exits_one_on_a_broken_file(self, tmp_path: Path) -> None:
        path = _file(tmp_path, "one", _valid("one", status="nope"))
        assert rs.main(["--validate", str(path)]) == 1

    def test_validate_accepts_a_stub(self, tmp_path: Path) -> None:
        path = _file(tmp_path, "one", rs.template("one"))
        assert rs.main(["--validate", str(path)]) == 0

    def test_the_template_round_trips_through_the_validator(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert rs.main(["--template", "alpha"]) == 0
        assert rs.validate_summary(json.loads(capsys.readouterr().out), stem="alpha") == []

    def test_help_names_the_flag_contributing_publishes(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit):
            rs.main(["--help"])
        assert "--check" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# in situ: this checkout
# ---------------------------------------------------------------------------
@needs_parser
class TestThisCheckout:
    """The gate runs green here, and the register agrees with the script."""

    def test_the_gate_is_green_on_this_tree(self) -> None:
        assert rs.check(REPO_ROOT) == []

    def test_this_repository_carries_at_least_one_round(self) -> None:
        # ANTI-VACUITY. Every assertion above about a committed round would
        # pass for the wrong reason against an empty register.
        rounds = [p for p in rs.ROUNDS_ROOT.glob("*") if p.is_dir()]
        assert rounds, "the run-summary register holds no round"

    def test_contributing_publishes_exactly_the_fields_the_code_requires(self) -> None:
        assert rs.documented_fields(CONTRIBUTING) == list(rs.FIELD_NAMES)

    def test_the_gate_command_contributing_publishes_is_the_one_ci_runs(self) -> None:
        text = CONTRIBUTING.read_text(encoding="utf-8")
        assert "python tools/run_summary.py --check" in text
        workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        assert "run: python tools/run_summary.py --check" in workflow


@needs_register
@needs_parser
class TestTheRegisterAndTheScriptAgree:
    """A marker that drifts turns every future demonstration into ``INERT``."""

    @staticmethod
    def _register() -> Dict[str, Any]:
        if sys.version_info >= (3, 11):
            import tomllib as toml
        else:  # pragma: no cover - 3.9/3.10 path
            import tomli as toml  # type: ignore[no-redef]
        with GATES.open("rb") as handle:
            return dict(toml.load(handle))

    def test_the_declared_marker_is_the_one_the_script_prints(self) -> None:
        declared = self._register()["gates"]["run_summary"]["mutation"]
        assert declared["expect_failure_matching"] == rs.FAILURE_MARKER

    def test_the_declared_command_is_the_one_ci_runs(self) -> None:
        entry = self._register()["gates"]["run_summary"]
        assert entry["command"] == "python tools/run_summary.py --check"
        assert entry["mutation"]["kind"] == "automated"

    def test_the_mutation_target_exists(self) -> None:
        # A declared edit against a file that is not there is a gate with no
        # demonstration, and `tools/gates.py --check` says so -- this asserts it
        # from the other side.
        edits = self._register()["gates"]["run_summary"]["mutation"]["edits"]
        assert edits
        for edit in edits:
            target = REPO_ROOT / edit["file"]
            assert target.is_file(), edit["file"]
            assert edit["find"] in target.read_text(encoding="utf-8"), edit["find"]

    def test_the_marker_only_appears_when_the_gate_is_red(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # A marker printed on a green run would make every demonstration
        # meaningless in the other direction.
        root = _mirror(tmp_path)
        round_dir = root / ".github" / "run-summaries" / "r1"
        _roster(round_dir, ["one"])
        _file(round_dir, "one", _valid("one"))
        assert rs.main(["--check", "--root", str(root)]) == 0
        assert rs.FAILURE_MARKER not in capsys.readouterr().out
        _file(round_dir, "one", _valid("one", status="shipped"))
        assert rs.main(["--check", "--root", str(root)]) == 1
        assert rs.FAILURE_MARKER in capsys.readouterr().out


def test_no_optional_field_exists(monkeypatch: Optional[pytest.MonkeyPatch] = None) -> None:
    """Every declared field is required, and the count is pinned.

    An optional field is a field an agent under a ceiling omits.
    """
    assert len(rs.REQUIRED_FIELDS) == len(rs.FIELD_NAMES) == 11
    assert len(set(rs.FIELD_NAMES)) == 11
