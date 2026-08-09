"""End-to-end tests for the ``acronymkit`` command line.

The whole module is gated on :data:`conftest.requires_click` because ``click``
is an optional extra. Two entry points are exercised deliberately:

* :func:`acronymkit.cli.main` — the console-script wrapper, which returns an
  exit code and never raises. Used for exit-status and stderr assertions
  because it separates the streams the same way a shell does, independently of
  which ``click`` release supplies ``CliRunner``.
* :func:`acronymkit.cli.build_cli` with :class:`click.testing.CliRunner` — used
  where a fake stdin is convenient. Note that ``acronymkit.cli.cli`` is a
  *function* wrapping ``Group.main``, not a ``click.Group``; passing it to
  ``CliRunner.invoke`` would not work, which is why ``build_cli()`` is the
  object under test.

The one case that cannot use either is "``click`` is not installed": that is
verified by re-running the import in a subprocess whose meta-path refuses to
resolve ``click``, plus an in-process variant that pokes ``sys.modules``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, NamedTuple, Sequence

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from acronymkit import __version__
from acronymkit.cli import EXIT_FAILURE, EXIT_OK, EXIT_USAGE, build_cli, main
from acronymkit.enums import EngineTier
from conftest import REPO_ROOT, SRC, requires_click, requires_jsonschema

pytestmark = requires_click


# ---------------------------------------------------------------------------
# fixtures and helpers
# ---------------------------------------------------------------------------
#: A document with exactly one Schwartz & Hearst definition.
DOCUMENT = "The National Aeronautics and Space Administration (NASA) launched the mission."

#: Phrase used wherever a command just needs something well-formed to chew on.
PHRASE = "Application Programming Interface"

#: Phrase/target pair used for the backronym command.
BACKRONYM_PHRASE = "Next Generation High Performance Storage System"


class Invocation(NamedTuple):
    """Outcome of one :func:`acronymkit.cli.main` call."""

    exit_code: int
    stdout: str
    stderr: str

    @property
    def text(self) -> str:
        """Both streams concatenated, for "the message appeared somewhere" checks."""
        return self.stdout + self.stderr


@pytest.fixture
def run(capsys: pytest.CaptureFixture[str]) -> Callable[..., Invocation]:
    """Return a callable running ``main`` and capturing both streams."""

    def _run(*argv: str) -> Invocation:
        capsys.readouterr()  # discard anything an earlier call left behind
        code = main(list(argv))
        captured = capsys.readouterr()
        return Invocation(code, captured.out, captured.err)

    return _run


@pytest.fixture
def runner() -> Any:
    """A ``click.testing.CliRunner``; imported lazily so a bare install can skip."""
    from click.testing import CliRunner

    return CliRunner()


@pytest.fixture
def document(tmp_path: Path) -> Path:
    """``DOCUMENT`` written to a UTF-8 file inside ``tmp_path``."""
    path = tmp_path / "paper.txt"
    path.write_text(DOCUMENT, encoding="utf-8")
    return path


def write_config(tmp_path: Path, payload: object, name: str = "config.json") -> str:
    """Write ``payload`` as JSON under ``tmp_path`` and return its path."""
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def heading_line(text: str, first_column: str) -> str:
    """Return the table heading line whose first cell is ``first_column``.

    Args:
        text: Rendered command output.
        first_column: The heading of the left-most column.

    Returns:
        The matching line, stripped of trailing whitespace.

    Raises:
        AssertionError: If no line starts with ``first_column``.
    """
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] == first_column:
            return line
    raise AssertionError(f"no table heading starting with {first_column!r} in:\n{text}")


def runner_output(result: Any) -> str:
    """Return a ``CliRunner`` result's output, whichever way click captured it."""
    text = result.output or ""
    try:
        error = result.stderr or ""
    except (AttributeError, ValueError):  # click < 8.2 mixes the streams
        error = ""
    return text if error in text else text + error


# ---------------------------------------------------------------------------
# module surface
# ---------------------------------------------------------------------------
def test_cli_module_exports_main_and_cli() -> None:
    """The documented ``__all__`` is what the console script relies on."""
    import acronymkit.cli as cli_module

    assert sorted(cli_module.__all__) == ["cli", "main"]
    assert callable(cli_module.main)
    assert callable(cli_module.cli)


def test_build_cli_returns_a_memoised_group() -> None:
    """``build_cli`` yields a real ``click.Group``, and the same one every time."""
    import click

    group = build_cli()
    assert isinstance(group, click.Group)
    assert build_cli() is group
    assert sorted(group.commands) == [
        "backronym",
        "extract",
        "generate",
        "schema",
        "score",
        "synthesize",
        "tokens",
        "version",
    ]


# ---------------------------------------------------------------------------
# text rendering
# ---------------------------------------------------------------------------
TEXT_TABLES = [
    pytest.param(
        ("generate", PHRASE),
        ["RANK", "ACRONYM", "SCORE", "PRONOUNCE", "DICT"],
        id="generate",
    ),
    pytest.param(
        ("backronym", BACKRONYM_PHRASE, "NEXUS"),
        ["RANK", "EXPANSION", "SCORE", "COVERAGE", "UNMAPPED"],
        id="backronym",
    ),
    pytest.param(
        ("synthesize", "RAM"),
        ["RANK", "EXPANSION", "SCORE", "COVERAGE", "UNMAPPED"],
        id="synthesize",
    ),
    pytest.param(
        ("score", "PDF", "Portable Document Format"),
        ["POS", "CHAR", "TOKEN", "OFFSET", "KIND", "OMEGA"],
        id="score",
    ),
    pytest.param(
        ("tokens", "Multi-Factor Authentication"),
        ["#", "TEXT", "ROLE", "POS", "STOPWORD", "ELIGIBLE", "CRITICAL", "LETTERS", "SPAN"],
        id="tokens",
    ),
]


@pytest.mark.parametrize(("argv", "headers"), TEXT_TABLES)
def test_text_format_renders_the_expected_table(
    run: Callable[..., Invocation], argv: Sequence[str], headers: list[str]
) -> None:
    """Every tabular command emits its documented heading row, then a rule."""
    outcome = run(*argv)
    assert outcome.exit_code == EXIT_OK
    heading = heading_line(outcome.stdout, headers[0])
    assert heading.split() == headers
    lines = outcome.stdout.splitlines()
    rule = lines[lines.index(heading) + 1]
    assert set(rule.split()) == {"-" * len(cell) for cell in rule.split()}
    assert rule.replace("-", "").strip() == ""


def test_extract_text_format_renders_the_pair_table(
    run: Callable[..., Invocation], document: Path
) -> None:
    """``extract`` reports a count line and a table with both span columns."""
    outcome = run("extract", str(document))
    assert outcome.exit_code == EXIT_OK
    assert "1 definition(s) found." in outcome.stdout
    heading = heading_line(outcome.stdout, "SHORT")
    for header in ("SHORT", "LONG", "CONF", "PATTERN", "SHORT SPAN", "LONG SPAN"):
        assert header in heading
    assert "NASA" in outcome.stdout
    assert "National Aeronautics and Space Administration" in outcome.stdout


def test_extract_reports_an_empty_document_without_failing(
    run: Callable[..., Invocation], tmp_path: Path
) -> None:
    """A document defining nothing is a successful, explicit "nothing here"."""
    path = tmp_path / "plain.txt"
    path.write_text("There is nothing to extract in this sentence.", encoding="utf-8")
    outcome = run("extract", str(path))
    assert outcome.exit_code == EXIT_OK
    assert outcome.stdout.strip() == "No abbreviation definitions found."


def test_generate_text_shows_the_primary_and_its_breakdown(
    run: Callable[..., Invocation],
) -> None:
    """The headline lines and the audit block are both present by default."""
    outcome = run("generate", PHRASE)
    assert outcome.exit_code == EXIT_OK
    assert f"Phrase:  {PHRASE}" in outcome.stdout
    assert "Primary: API" in outcome.stdout
    assert "Score breakdown for API:" in outcome.stdout
    assert heading_line(outcome.stdout, "TERM").split() == [
        "TERM",
        "VALUE",
        "COEFF",
        "CONTRIBUTION",
    ]
    assert "S = " in outcome.stdout


def test_score_text_reports_the_normalisation(run: Callable[..., Invocation]) -> None:
    """A punctuated acronym is scored as its normalised form, and says so."""
    outcome = run("score", "p.d.f.", "Portable Document Format")
    assert outcome.exit_code == EXIT_OK
    assert "Acronym: PDF" in outcome.stdout
    assert "normalised from 'p.d.f.'" in outcome.stdout


def test_synthesize_reports_an_impossible_target(run: Callable[..., Invocation]) -> None:
    """A target with no alphanumeric letters yields an explanation, not an error."""
    outcome = run("synthesize", "...")
    assert outcome.exit_code == EXIT_OK
    assert "No expansion could be built" in outcome.stdout


def test_tokens_counts_eligible_tokens(run: Callable[..., Invocation]) -> None:
    """The header line reports how many tokens may donate letters."""
    outcome = run("tokens", "The Portable Document Format")
    assert outcome.exit_code == EXIT_OK
    assert "4 token(s), 3 eligible to donate letters." in outcome.stdout


def test_version_text_matches_the_package(run: Callable[..., Invocation]) -> None:
    """``version`` prints exactly what ``acronymkit.__version__`` says."""
    outcome = run("version")
    assert outcome.exit_code == EXIT_OK
    assert outcome.stdout.strip() == f"acronymkit {__version__}"


# ---------------------------------------------------------------------------
# JSON rendering
# ---------------------------------------------------------------------------
JSON_COMMANDS = [
    pytest.param(("generate", PHRASE), dict, ["source_phrase", "primary_acronym"], id="generate"),
    pytest.param(
        ("backronym", BACKRONYM_PHRASE, "NEXUS"),
        dict,
        ["target_word", "candidates"],
        id="backronym",
    ),
    pytest.param(("synthesize", "RAM"), dict, ["target_word", "candidates"], id="synthesize"),
    pytest.param(
        ("score", "PDF", "Portable Document Format"),
        dict,
        ["acronym", "score", "mappings"],
        id="score",
    ),
    pytest.param(("tokens", "Multi-Factor Authentication"), list, [], id="tokens"),
    pytest.param(("schema",), dict, ["title", "properties"], id="schema"),
    pytest.param(("version",), dict, ["name", "version"], id="version"),
]


@pytest.mark.parametrize(("argv", "kind", "keys"), JSON_COMMANDS)
def test_json_format_is_parseable(
    run: Callable[..., Invocation], argv: Sequence[str], kind: type, keys: list[str]
) -> None:
    """``--format json`` emits one parseable document of the documented shape."""
    outcome = run(*argv, "--format", "json")
    assert outcome.exit_code == EXIT_OK
    payload = json.loads(outcome.stdout)
    assert isinstance(payload, kind)
    for key in keys:
        assert key in payload


def test_extract_json_is_parseable(run: Callable[..., Invocation], document: Path) -> None:
    """``extract --format json`` emits the full ``ExtractionResult`` payload."""
    outcome = run("extract", str(document), "--format", "json")
    assert outcome.exit_code == EXIT_OK
    payload = json.loads(outcome.stdout)
    assert payload["source_text"] == DOCUMENT
    assert [pair["short_form"] for pair in payload["pairs"]] == ["NASA"]
    start, end = payload["pairs"][0]["long_form_span"]
    assert DOCUMENT[start:end] == "National Aeronautics and Space Administration"


@pytest.mark.parametrize("indent", [0, 1, 4])
def test_indent_controls_json_layout(run: Callable[..., Invocation], indent: int) -> None:
    """``--indent 0`` compacts to one line; any other width pretty-prints."""
    outcome = run("version", "--format", "json", "--indent", str(indent))
    assert outcome.exit_code == EXIT_OK
    assert json.loads(outcome.stdout) == {"name": "acronymkit", "version": __version__}
    assert (len(outcome.stdout.strip().splitlines()) == 1) is (indent == 0)


def test_tokens_json_spans_slice_back_to_the_phrase(
    run: Callable[..., Invocation],
) -> None:
    """Token offsets in the payload address the original phrase exactly."""
    phrase = "Multi-Factor Authentication of the XML 2 Parser"
    outcome = run("tokens", phrase, "--format", "json")
    assert outcome.exit_code == EXIT_OK
    tokens = json.loads(outcome.stdout)
    assert tokens
    for token in tokens:
        assert phrase[token["start"] : token["end"]] == token["text"]


def test_tokens_json_of_a_blank_phrase_is_an_empty_list(
    run: Callable[..., Invocation],
) -> None:
    """``tokens`` is an inspection command: nothing to show is not a failure."""
    outcome = run("tokens", "   ", "--format", "json")
    assert outcome.exit_code == EXIT_OK
    assert json.loads(outcome.stdout) == []


def test_schema_command_emits_the_interchange_schema(
    run: Callable[..., Invocation],
) -> None:
    """``schema`` prints the same document ``serialization.load_schema`` loads."""
    from acronymkit.serialization import load_schema

    outcome = run("schema")
    assert outcome.exit_code == EXIT_OK
    assert json.loads(outcome.stdout) == load_schema()


@requires_jsonschema
def test_generate_json_validates_against_the_schema(
    run: Callable[..., Invocation],
) -> None:
    """The generate payload is what the published interchange contract promises."""
    from acronymkit.serialization import validate_result

    outcome = run("generate", PHRASE, "--format", "json")
    assert outcome.exit_code == EXIT_OK
    validate_result(json.loads(outcome.stdout))


@requires_jsonschema
@pytest.mark.parametrize(("phrase", "expected"), [(PHRASE, "API"), ("Read Only Memory", "ROM")])
def test_generate_json_stays_conformant_across_phrases(
    run: Callable[..., Invocation], phrase: str, expected: str
) -> None:
    """Conformance is a property of the payload, not of one lucky phrase."""
    from acronymkit.serialization import validate_result

    outcome = run("generate", phrase, "--format", "json")
    payload = json.loads(outcome.stdout)
    validate_result(payload)
    assert payload["primary_acronym"] == expected


# ---------------------------------------------------------------------------
# input sources
# ---------------------------------------------------------------------------
def test_extract_reads_stdin_when_the_file_is_a_dash(runner: Any) -> None:
    """``-`` is the conventional "read the pipe" argument."""
    result = runner.invoke(build_cli(), ["extract", "-"], input=DOCUMENT)
    assert result.exit_code == EXIT_OK
    assert "NASA" in runner_output(result)


def test_extract_reads_stdin_when_no_file_is_given(runner: Any) -> None:
    """Omitting FILE behaves like ``-`` as long as stdin is not a terminal."""
    result = runner.invoke(build_cli(), ["extract"], input=DOCUMENT)
    assert result.exit_code == EXIT_OK
    assert "NASA" in runner_output(result)


def test_extract_from_file_and_from_stdin_agree(runner: Any, document: Path) -> None:
    """The source of the bytes cannot change the extraction."""
    from_file = runner.invoke(build_cli(), ["extract", str(document), "--format", "json"])
    from_stdin = runner.invoke(build_cli(), ["extract", "-", "--format", "json"], input=DOCUMENT)
    assert from_file.exit_code == from_stdin.exit_code == EXIT_OK
    assert json.loads(from_file.output)["pairs"] == json.loads(from_stdin.output)["pairs"]


def test_extract_rejects_a_missing_file(run: Callable[..., Invocation], tmp_path: Path) -> None:
    """A path click cannot open is a usage error, not a traceback."""
    outcome = run("extract", str(tmp_path / "absent.txt"))
    assert outcome.exit_code == EXIT_USAGE
    assert "absent.txt" in outcome.text


def test_extract_rejects_a_directory(run: Callable[..., Invocation], tmp_path: Path) -> None:
    """``dir_okay=False`` is enforced before the engine is ever built."""
    outcome = run("extract", str(tmp_path))
    assert outcome.exit_code == EXIT_USAGE


# ---------------------------------------------------------------------------
# configuration layering
# ---------------------------------------------------------------------------
def test_config_file_supplies_the_base_layer(
    run: Callable[..., Invocation], tmp_path: Path
) -> None:
    """Fields with no flag of their own are still reachable through --config."""
    path = write_config(tmp_path, {"max_candidates": 3, "case_style": "lower"})
    outcome = run("generate", "Portable Document Format", "--config", path, "--format", "json")
    assert outcome.exit_code == EXIT_OK
    payload = json.loads(outcome.stdout)
    assert payload["primary_acronym"] == "pdf"
    assert len(payload["alternatives"]) == 3


def test_explicit_flags_override_the_config_file(
    run: Callable[..., Invocation], tmp_path: Path
) -> None:
    """The flag layer wins over the file layer for the same ``Config`` field."""
    path = write_config(tmp_path, {"max_candidates": 3, "max_acronym_length": 4})
    outcome = run("generate", PHRASE, "--config", path, "--top", "1", "--format", "json")
    assert outcome.exit_code == EXIT_OK
    payload = json.loads(outcome.stdout)
    assert len(payload["alternatives"]) == 1
    assert max(len(item["acronym"]) for item in payload["alternatives"]) <= 4


def test_unset_flags_do_not_shadow_the_config_file(
    run: Callable[..., Invocation], tmp_path: Path
) -> None:
    """An omitted boolean pair stays ``None``, so the file keeps its value."""
    path = write_config(tmp_path, {"include_articles": True})
    outcome = run("tokens", "The Portable Document Format", "--config", path, "--format", "json")
    assert outcome.exit_code == EXIT_OK
    tokens = json.loads(outcome.stdout)
    assert tokens[0]["text"] == "The"
    assert tokens[0]["is_eligible"] is True


def test_no_include_articles_flag_overrides_a_permissive_file(
    run: Callable[..., Invocation], tmp_path: Path
) -> None:
    """The negative half of the boolean pair reaches ``Config`` as ``False``."""
    path = write_config(tmp_path, {"include_articles": True})
    outcome = run(
        "tokens",
        "The Portable Document Format",
        "--config",
        path,
        "--no-include-articles",
        "--format",
        "json",
    )
    assert outcome.exit_code == EXIT_OK
    tokens = json.loads(outcome.stdout)
    assert tokens[0]["text"] == "The"
    assert tokens[0]["is_eligible"] is False


CONFIG_FILE_FAILURES = [
    pytest.param("{ not json", "not valid JSON", id="malformed"),
    pytest.param("[1, 2]", "must contain a JSON object", id="not-an-object"),
    pytest.param('{"nope": 1}', "invalid configuration", id="unknown-field"),
    pytest.param(
        '{"min_acronym_length": 6, "max_acronym_length": 2}',
        "invalid configuration",
        id="inconsistent",
    ),
]


@pytest.mark.parametrize(("body", "message"), CONFIG_FILE_FAILURES)
def test_bad_config_files_are_usage_errors(
    run: Callable[..., Invocation], tmp_path: Path, body: str, message: str
) -> None:
    """Every way a --config file can be wrong exits 2 with an explanation."""
    path = tmp_path / "broken.json"
    path.write_text(body, encoding="utf-8")
    outcome = run("generate", PHRASE, "--config", str(path))
    assert outcome.exit_code == EXIT_USAGE
    assert message in outcome.text


def test_missing_config_file_is_a_usage_error(
    run: Callable[..., Invocation], tmp_path: Path
) -> None:
    """``click.Path(exists=True)`` rejects the path before anything is read."""
    outcome = run("generate", PHRASE, "--config", str(tmp_path / "absent.json"))
    assert outcome.exit_code == EXIT_USAGE


def test_inconsistent_length_flags_are_a_usage_error(
    run: Callable[..., Invocation],
) -> None:
    """A cross-field ``Config`` rule failing is the user's mistake, not the engine's."""
    outcome = run("generate", PHRASE, "--min-length", "6", "--max-length", "2")
    assert outcome.exit_code == EXIT_USAGE
    assert "invalid configuration" in outcome.text


# ---------------------------------------------------------------------------
# exit codes
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(("generate", ""), id="generate-empty"),
        pytest.param(("generate", "   "), id="generate-blank"),
        pytest.param(("generate", "the of and"), id="generate-all-stopwords"),
        pytest.param(("backronym", "", "NEXUS"), id="backronym-empty"),
        pytest.param(("score", "PDF", ""), id="score-empty-phrase"),
        pytest.param(("score", "...", "Portable Document Format"), id="score-no-letters"),
        pytest.param(
            ("generate", "Quality Assurance", "--min-length", "5"), id="generate-no-candidate"
        ),
    ],
)
def test_engine_refusals_exit_one(run: Callable[..., Invocation], argv: Sequence[str]) -> None:
    """A blank phrase or an unsatisfiable constraint is exit 1 on stderr."""
    outcome = run(*argv)
    assert outcome.exit_code == EXIT_FAILURE
    assert outcome.stderr.startswith("error: ")
    assert outcome.stdout == ""


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(("generate", PHRASE, "--nope"), id="unknown-flag"),
        pytest.param(("generate",), id="missing-argument"),
        pytest.param(("nosuchcommand",), id="unknown-command"),
        pytest.param(("generate", PHRASE, "--format", "yaml"), id="bad-format"),
        pytest.param(("generate", PHRASE, "--strategy", "bogus"), id="bad-strategy"),
        pytest.param(("generate", PHRASE, "--language", "xx"), id="bad-language"),
        pytest.param(("generate", PHRASE, "--top", "0"), id="out-of-range"),
    ],
)
def test_usage_mistakes_exit_two(run: Callable[..., Invocation], argv: Sequence[str]) -> None:
    """Everything click itself rejects is exit 2, with nothing on stdout."""
    outcome = run(*argv)
    assert outcome.exit_code == EXIT_USAGE
    assert outcome.stdout == ""
    assert "Error" in outcome.stderr or "Usage" in outcome.stderr


def test_invalid_tier_lists_every_valid_choice(run: Callable[..., Invocation]) -> None:
    """The diagnostic is actionable: it names all five tiers."""
    outcome = run("generate", PHRASE, "--tier", "bogus")
    assert outcome.exit_code == EXIT_USAGE
    assert "bogus" in outcome.stderr
    for tier in EngineTier:
        assert tier.value in outcome.stderr


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(("--help",), id="group"),
        pytest.param(("-h",), id="group-short"),
        pytest.param(("generate", "--help"), id="generate"),
        pytest.param(("backronym", "--help"), id="backronym"),
        pytest.param(("synthesize", "--help"), id="synthesize"),
        pytest.param(("extract", "--help"), id="extract"),
        pytest.param(("score", "--help"), id="score"),
        pytest.param(("tokens", "--help"), id="tokens"),
        pytest.param(("schema", "--help"), id="schema"),
        pytest.param(("version", "--help"), id="version"),
    ],
)
def test_help_exits_zero(run: Callable[..., Invocation], argv: Sequence[str]) -> None:
    """Help is a successful outcome and always mentions its own usage line."""
    outcome = run(*argv)
    assert outcome.exit_code == EXIT_OK
    assert "Usage:" in outcome.stdout


def test_every_command_appears_in_the_group_help(run: Callable[..., Invocation]) -> None:
    """The eight documented commands are all reachable from the root help."""
    outcome = run("--help")
    for command in (
        "generate",
        "backronym",
        "synthesize",
        "extract",
        "score",
        "tokens",
        "schema",
        "version",
    ):
        assert command in outcome.stdout


# ---------------------------------------------------------------------------
# determinism
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(("generate", PHRASE, "--format", "json"), id="generate"),
        pytest.param(("synthesize", "RAM", "--format", "json"), id="synthesize"),
        pytest.param(("tokens", "Multi-Factor Authentication", "--format", "json"), id="tokens"),
    ],
)
def test_repeated_invocations_agree(run: Callable[..., Invocation], argv: Sequence[str]) -> None:
    """Output is deterministic once the timing envelope is removed."""

    def strip_timing(text: str) -> object:
        payload = json.loads(text)
        if isinstance(payload, dict) and isinstance(payload.get("metadata"), dict):
            payload["metadata"].pop("execution_time_ms", None)
        return payload

    first = run(*argv)
    second = run(*argv)
    assert first.exit_code == second.exit_code == EXIT_OK
    assert strip_timing(first.stdout) == strip_timing(second.stdout)


@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    words=st.lists(
        st.text(alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"), min_size=1, max_size=8),
        min_size=1,
        max_size=6,
    )
)
def test_tokens_json_offsets_are_exact_for_any_phrase(words: list[str]) -> None:
    """Whatever the phrase, every reported span slices back to its own token text."""
    from click.testing import CliRunner

    phrase = " ".join(words)
    result = CliRunner().invoke(build_cli(), ["tokens", phrase, "--format", "json"])
    assert result.exit_code == EXIT_OK
    tokens = json.loads(result.output)
    assert [token["index"] for token in tokens] == list(range(len(tokens)))
    for token in tokens:
        assert phrase[token["start"] : token["end"]] == token["text"]
        assert token["start"] < token["end"]


# ---------------------------------------------------------------------------
# the optional dependency itself
# ---------------------------------------------------------------------------
_NO_CLICK_SCRIPT = """
import sys

sys.path.insert(0, {src!r})


class _RefuseClick:
    def find_spec(self, name, path=None, target=None):
        if name == "click" or name.startswith("click."):
            raise ImportError("click is unavailable in this test")
        return None


sys.meta_path.insert(0, _RefuseClick())

import acronymkit.cli as cli_module

assert "click" not in sys.modules
print("IMPORT_OK")
print("EXIT", cli_module.main(["version"]))
"""


def test_main_reports_a_missing_click_in_a_subprocess(tmp_path: Path) -> None:
    """With click unimportable the module still imports and ``main`` returns 2.

    Run out of process so the meta-path hook cannot leak into the rest of the
    session, and so ``click`` is genuinely absent from ``sys.modules`` rather
    than merely shadowed.
    """
    script = tmp_path / "no_click.py"
    script.write_text(_NO_CLICK_SCRIPT.format(src=str(SRC)), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "IMPORT_OK" in completed.stdout
    assert "EXIT 2" in completed.stdout
    assert "pip install" in completed.stdout + completed.stderr
    assert "acronymkit[cli]" in completed.stdout + completed.stderr


def test_main_reports_a_missing_click_in_process(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The same path in process: ``sys.modules['click'] = None`` breaks the import.

    ``monkeypatch.setitem`` restores the real entry at teardown, so the rest of
    the module keeps working.
    """
    monkeypatch.setitem(sys.modules, "click", None)
    capsys.readouterr()
    assert main(["version"]) == EXIT_USAGE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "acronymkit[cli]" in captured.err


def test_click_is_restored_after_the_simulation(run: Callable[..., Invocation]) -> None:
    """Guards the two tests above: the monkeypatched module was really put back."""
    assert run("version").exit_code == EXIT_OK
