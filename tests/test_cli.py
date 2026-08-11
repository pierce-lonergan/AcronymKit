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

import errno
import io
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
        "check-name",
        "doctor",
        "expand-identifier",
        "expand-token",
        "extract",
        "generate",
        "governed-audit",
        "governed-batch",
        "normalize-name",
        "physical-name",
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
        pytest.param(("doctor", "--help"), id="doctor"),
        pytest.param(("expand-token", "--help"), id="expand-token"),
        pytest.param(("expand-identifier", "--help"), id="expand-identifier"),
        pytest.param(("physical-name", "--help"), id="physical-name"),
        pytest.param(("normalize-name", "--help"), id="normalize-name"),
        pytest.param(("check-name", "--help"), id="check-name"),
        pytest.param(("governed-batch", "--help"), id="governed-batch"),
        pytest.param(("governed-audit", "--help"), id="governed-audit"),
    ],
)
def test_help_exits_zero(run: Callable[..., Invocation], argv: Sequence[str]) -> None:
    """Help is a successful outcome and always mentions its own usage line.

    ``--help`` on a governed command must not require ``--dictionary``, even
    though the flag is otherwise mandatory. Asking someone to supply a
    vocabulary before they may read what the command does would be a poor
    trade, and click's own ordering gives it away for free.
    """
    outcome = run(*argv)
    assert outcome.exit_code == EXIT_OK
    assert "Usage:" in outcome.stdout


def test_every_command_appears_in_the_group_help(run: Callable[..., Invocation]) -> None:
    """Every documented command is reachable from the root help."""
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
        "doctor",
        "expand-token",
        "expand-identifier",
        "physical-name",
        "normalize-name",
        "check-name",
        "governed-batch",
        "governed-audit",
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


# ---------------------------------------------------------------------------
# governed naming commands
# ---------------------------------------------------------------------------
#: A catalog small enough to read in the test and complete enough to exercise
#: every branch the governed commands have: an approved abbreviation, a pinned
#: collision, a class word, and a genuine short word that a naive "2-5 upper
#: letters is an abbreviation" rule would wrongly flag.
GOVERNED_CATALOG: list[dict[str, Any]] = [
    {
        "token": "TXN",
        "canonical": "Transaction",
        "kind": "approved_abbrev",
        "keep_as_abbrev": True,
        "entry_id": "NDS-TXN",
        "source": "approved",
    },
    {
        "token": "ID",
        "canonical": "Identifier",
        "candidates": ["Identity", "Identifier", "Identification"],
        "pin": "Identifier",
        "kind": "ambiguous_pinned",
        "keep_as_abbrev": True,
        "class_word": "Identifier",
        "entry_id": "NDS-ID",
        "source": "pinned",
    },
    {
        "token": "DT",
        "canonical": "Date",
        "kind": "class_word_abbrev",
        "keep_as_abbrev": True,
        "class_word": "Date",
        "entry_id": "NDS-DT",
        "source": "approved",
    },
    {
        "token": "APPLNT",
        "canonical": "Applicant",
        "kind": "approved_abbrev",
        "keep_as_abbrev": True,
        "entry_id": "NDS-APPLNT",
        "source": "approved",
    },
    {
        "token": "FRAUD",
        "canonical": "Fraud",
        "kind": "short_full_word",
        "entry_id": "NDS-FRAUD",
        "source": "governed",
    },
]


@pytest.fixture
def catalog(tmp_path: Path) -> str:
    """The governed catalog written to a JSON file, as ``--dictionary`` wants it."""
    return write_config(tmp_path, GOVERNED_CATALOG, name="nds.json")


def test_expand_token_resolves_from_the_supplied_catalog(runner: Any, catalog: str) -> None:
    """``expand-token`` is the CLI face of a governed lookup."""
    result = runner.invoke(build_cli(), ["expand-token", "TXN", "--dictionary", catalog])

    assert result.exit_code == 0, runner_output(result)
    assert "Transaction" in runner_output(result)


def test_expand_token_reports_an_unknown_token_as_unknown(runner: Any, catalog: str) -> None:
    """The passthrough contract has to survive the trip through the CLI.

    A governed tool that renders "Zzz" for an unrecognised token without saying
    it was a guess is worse than one that errors: the caller cannot tell the
    difference between an answer and a shrug.
    """
    result = runner.invoke(
        build_cli(), ["expand-token", "ZZZ", "--dictionary", catalog, "--format", "json"]
    )

    assert result.exit_code == 0, runner_output(result)
    payload = json.loads(runner_output(result))
    assert payload["is_known"] is False
    assert payload["source"] == "passthrough"


def test_custom_acronyms_beat_the_catalog_over_the_cli(runner: Any, catalog: str) -> None:
    """``--custom`` is the whole reason this command takes two vocabularies.

    A caller with house acronyms must be able to supply them at the call site
    and see, in the output, that theirs is what answered.
    """
    result = runner.invoke(
        build_cli(),
        [
            "expand-token",
            "TXN",
            "--dictionary",
            catalog,
            "--custom",
            '{"TXN": "Transfer"}',
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, runner_output(result)
    payload = json.loads(runner_output(result))
    assert payload["long"] == "Transfer"
    assert payload["source"] == "custom"


def test_a_custom_override_is_refused_when_the_policy_forbids_it(runner: Any, catalog: str) -> None:
    """``--policy frequency_baseline`` sets ``allow_override=False``.

    The overlay contradicts a governed entry, so the catalog answer stands.
    Pinned here because the demotion is the subtle half of the precedence rule
    and is invisible from the default policy.
    """
    result = runner.invoke(
        build_cli(),
        [
            "expand-token",
            "TXN",
            "--dictionary",
            catalog,
            "--custom",
            '{"TXN": "Taxation"}',
            "--policy",
            "frequency_baseline",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, runner_output(result)
    payload = json.loads(runner_output(result))
    assert payload["long"] == "Transaction"
    assert payload["source"] != "custom"


def test_expand_identifier_returns_the_phrase_and_its_class_word(runner: Any, catalog: str) -> None:
    """The unit of work in a schema pipeline is the identifier, not the token."""
    result = runner.invoke(
        build_cli(),
        ["expand-identifier", "APPLNT_TXN_DT", "--dictionary", catalog, "--format", "json"],
    )

    assert result.exit_code == 0, runner_output(result)
    payload = json.loads(runner_output(result))
    assert payload["phrase"] == "Applicant Transaction Date"
    assert payload["class_word"] == "Date"


def test_physical_name_runs_the_reverse_direction(runner: Any, catalog: str) -> None:
    """``physical-name`` closes the loop the other way, against the same catalog."""
    result = runner.invoke(
        build_cli(),
        [
            "physical-name",
            "Applicant Transaction Date",
            "--dictionary",
            catalog,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, runner_output(result)
    assert json.loads(runner_output(result))["physical"] == "APPLNT_TXN_DT"


def test_check_name_exits_zero_when_the_name_complies(runner: Any, catalog: str) -> None:
    """A compliant name is a successful run."""
    result = runner.invoke(build_cli(), ["check-name", "APPLNT_TXN_DT", "--dictionary", catalog])

    assert result.exit_code == 0, runner_output(result)


def test_check_name_exits_non_zero_when_it_does_not(runner: Any, catalog: str) -> None:
    """The exit status is the feature.

    ``check-name`` exists to be a gate in someone else's CI, and a gate that
    reports a violation on stdout while exiting 0 is not a gate. ``APPLNT_TXN``
    has no trailing class word.
    """
    result = runner.invoke(build_cli(), ["check-name", "APPLNT_TXN", "--dictionary", catalog])

    assert result.exit_code == EXIT_FAILURE
    assert "class word" in runner_output(result).lower()


def test_a_malformed_catalog_is_a_usage_error(runner: Any, tmp_path: Path) -> None:
    """A catalog named on the command line that cannot be read is exit 2, not 1."""
    broken = write_config(tmp_path, [{"token": "TXN"}], name="broken.json")
    result = runner.invoke(build_cli(), ["expand-token", "TXN", "--dictionary", broken])

    assert result.exit_code == EXIT_USAGE, runner_output(result)


def test_the_governed_commands_require_a_dictionary(runner: Any) -> None:
    """A governed verb with no governed vocabulary is a contradiction, not a default.

    Silently falling back to an empty catalog would make every token a
    passthrough and every answer a guess dressed as a result.
    """
    result = runner.invoke(build_cli(), ["expand-token", "TXN"])

    assert result.exit_code == EXIT_USAGE


def test_expand_identifier_shows_the_characters_it_could_not_account_for(
    runner: Any, catalog: str
) -> None:
    """``Fully known: no`` has to say what made it false.

    Every token here resolves, so a reader looking at the token table alone
    would see nothing wrong and would be told the name failed anyway. The
    copyright sign is neither a letter, a digit nor one of the separators the
    splitter accounts for, and it is the whole reason for the verdict.
    """
    result = runner.invoke(build_cli(), ["expand-identifier", "TXN©ID", "--dictionary", catalog])

    assert result.exit_code == 0, runner_output(result)
    text = runner_output(result)
    assert "Fully known: no" in text
    assert "Unaccounted: ©" in text


# ---------------------------------------------------------------------------
# the vocabulary flags shared by every governed command
# ---------------------------------------------------------------------------
#: The worked fixture standard, in the bundle layout ``load_bundle`` reads.
GOVERNED_BUNDLE = str(REPO_ROOT / "tests" / "fixtures" / "governed")

#: A long form -> token catalog, the direction a real standard is authored in.
LONG_TO_SHORT_CSV = "long_form,abbreviation\nTransaction,TXN\nIdentifier,ID\nDate,DT\n"


@pytest.fixture
def catalog_csv(tmp_path: Path) -> str:
    """``LONG_TO_SHORT_CSV`` written to a file, as a spreadsheet export would be."""
    path = tmp_path / "nds.csv"
    path.write_text(LONG_TO_SHORT_CSV, encoding="utf-8")
    return str(path)


def test_a_directory_is_read_as_a_whole_standard(runner: Any) -> None:
    """A standard is five files, and asking for one of them is asking for a fifth of it.

    The catalog alone answers what a token means and nothing about whether it
    may stand in a physical name, so a directory has to reach ``load_bundle``
    for the allow-lists and the class-word map to be in force.
    """
    result = runner.invoke(
        build_cli(),
        [
            "expand-identifier",
            "CUST_ACCT_OPEN_DT",
            "--dictionary",
            GOVERNED_BUNDLE,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, runner_output(result)
    payload = json.loads(runner_output(result))
    assert payload["phrase"] == "Customer Account OPEN Date"
    assert payload["class_word"] == "Date"


def test_a_csv_catalog_is_refused_until_its_direction_is_declared(
    runner: Any, catalog_csv: str
) -> None:
    """The same two columns are a valid vocabulary read either way round.

    Guessing would silently produce a vocabulary meaning something the caller
    did not ask for, which is the same reason ``auto`` never picks
    ``long_to_short`` for a JSON mapping. The refusal names both flags that fix
    it.
    """
    result = runner.invoke(build_cli(), ["expand-token", "TXN", "--dictionary", catalog_csv])

    assert result.exit_code == EXIT_USAGE
    text = runner_output(result)
    assert "long_to_short_csv" in text
    assert "--columns" in text


def test_a_csv_catalog_loads_once_the_direction_and_columns_are_given(
    runner: Any, catalog_csv: str
) -> None:
    """The shape a governance function's standard actually arrives in.

    A caller whose catalog is a spreadsheet export should not have to write a
    conversion script before they can find out what this library does.
    """
    result = runner.invoke(
        build_cli(),
        [
            "expand-identifier",
            "TXN_ID",
            "--dictionary",
            catalog_csv,
            "--dictionary-format",
            "long_to_short_csv",
            "--columns",
            "long_form,abbreviation",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, runner_output(result)
    assert json.loads(runner_output(result))["phrase"] == "Transaction Identifier"


def test_columns_is_refused_when_nothing_reads_a_csv(runner: Any, catalog: str) -> None:
    """A flag that is quietly ignored teaches the caller it did something."""
    result = runner.invoke(
        build_cli(), ["expand-token", "TXN", "--dictionary", catalog, "--columns", "a,b"]
    )

    assert result.exit_code == EXIT_USAGE
    assert "--columns" in runner_output(result)


@pytest.mark.parametrize("value", ["long_form", "a,b,c", "long_form,"])
def test_columns_must_name_exactly_two_headers(runner: Any, catalog_csv: str, value: str) -> None:
    """One name, three names and a blank name are each undecidable, not a default."""
    result = runner.invoke(
        build_cli(),
        [
            "expand-token",
            "TXN",
            "--dictionary",
            catalog_csv,
            "--dictionary-format",
            "long_to_short_csv",
            "--columns",
            value,
        ],
    )

    assert result.exit_code == EXIT_USAGE
    assert "two" in runner_output(result)


def test_a_directory_with_a_file_layout_is_a_usage_error(runner: Any) -> None:
    """Nothing but a bundle is a directory, so the two flags contradict each other."""
    result = runner.invoke(
        build_cli(),
        [
            "expand-token",
            "TXN",
            "--dictionary",
            GOVERNED_BUNDLE,
            "--dictionary-format",
            "catalog",
        ],
    )

    assert result.exit_code == EXIT_USAGE
    assert "directory" in runner_output(result)


# ---------------------------------------------------------------------------
# governed-batch: one process for a whole schema
# ---------------------------------------------------------------------------
@pytest.fixture
def batch(
    run: Callable[..., Invocation], monkeypatch: pytest.MonkeyPatch
) -> Callable[..., Invocation]:
    """Run a command with ``text`` on standard input, with the streams kept apart.

    ``main`` plus ``capsys`` rather than ``CliRunner`` because a batch writes its
    records to stdout and its summary to stderr, and a runner that mixes the two
    cannot tell a record from a report.
    """

    def _batch(text: str, *argv: str) -> Invocation:
        monkeypatch.setattr(sys, "stdin", io.StringIO(text))
        return run(*argv)

    return _batch


def batch_records(outcome: Invocation) -> list[dict[str, Any]]:
    """Parse the record stream a batch wrote to stdout."""
    return [json.loads(line) for line in outcome.stdout.splitlines() if line.strip()]


def test_governed_batch_answers_every_line_in_order(
    batch: Callable[..., Invocation],
) -> None:
    """One record in, one record out, and the input on every one of them.

    The echoed input is what lets a caller join the stream back onto its own
    rows without trusting the order it read them in — which is the difference
    between a pipe another process can use and one it has to be careful with.
    """
    outcome = batch(
        "TXN_APPLNT_ID\nCUST_ACCT_KYC_ID\n",
        "governed-batch",
        "--dictionary",
        GOVERNED_BUNDLE,
    )

    assert outcome.exit_code == EXIT_OK, outcome.text
    records = batch_records(outcome)
    assert [record["line"] for record in records] == [1, 2]
    assert [record["input"] for record in records] == ["TXN_APPLNT_ID", "CUST_ACCT_KYC_ID"]
    assert records[0]["result"]["phrase"] == "Transaction Applicant Identifier"
    assert records[0]["result"]["is_fully_known"] is True
    assert records[1]["result"]["is_fully_known"] is False


def test_governed_batch_echoes_a_caller_supplied_key(
    batch: Callable[..., Invocation],
) -> None:
    """A pipeline holding a row id needs it back, untouched, on the answer."""
    outcome = batch(
        '{"id": "col-0007", "identifier": "TXN_ID"}\n',
        "governed-batch",
        "--dictionary",
        GOVERNED_BUNDLE,
    )

    assert outcome.exit_code == EXIT_OK, outcome.text
    record = batch_records(outcome)[0]
    assert record["id"] == "col-0007"
    assert record["input"] == "TXN_ID"


def test_one_bad_line_costs_one_record_and_not_the_run(
    batch: Callable[..., Invocation],
) -> None:
    """The whole point of the record envelope.

    Losing forty-nine thousand answers to one unparseable line is a worse
    outcome than any error message, so the failure goes on the record and the
    run continues. The exit status still reports it, so the command remains
    usable as a gate.
    """
    outcome = batch(
        'TXN_ID\n{"identifier": 7}\nAPPLNT_BRTH_DT\n',
        "governed-batch",
        "--dictionary",
        GOVERNED_BUNDLE,
    )

    assert outcome.exit_code == EXIT_FAILURE
    records = batch_records(outcome)
    assert [record["ok"] for record in records] == [True, False, True]
    assert records[1]["error_type"] == "InputError"
    assert "identifier" in records[1]["error"]
    assert records[2]["result"]["phrase"] == "Applicant Birth Date"


def test_a_non_compliant_name_is_an_answer_and_not_a_failure(
    batch: Callable[..., Invocation],
) -> None:
    """The exit status reports records that failed, never findings.

    A batch that exited non-zero because the schema it was handed is imperfect
    would be a gate on the wrong thing: reporting that imperfection is what the
    command was asked to do.
    """
    outcome = batch(
        "APPLNT_TXN\n",
        "governed-batch",
        "--dictionary",
        GOVERNED_BUNDLE,
        "--op",
        "check",
    )

    assert outcome.exit_code == EXIT_OK, outcome.text
    record = batch_records(outcome)[0]
    assert record["ok"] is True
    assert record["result"]["compliant"] is False


def test_the_summary_goes_to_stderr_so_stdout_stays_a_record_stream(
    batch: Callable[..., Invocation],
) -> None:
    """A caller has to be able to confirm it received every record it sent.

    On stdout that count would be a line their parser has to know to skip; on
    stderr it is a report, and every line of stdout is a record.
    """
    outcome = batch(
        "TXN_ID\n\n\nAPPLNT_BRTH_DT\n",
        "governed-batch",
        "--dictionary",
        GOVERNED_BUNDLE,
    )

    assert outcome.exit_code == EXIT_OK, outcome.text
    assert len(batch_records(outcome)) == 2
    summary = json.loads(outcome.stderr.strip())
    assert summary == {"op": "expand", "records": 2, "failed": 0, "skipped": 2}


@pytest.mark.parametrize(
    ("op", "subject", "key", "expected"),
    [
        pytest.param("expand", "TXN_APPLNT_ID", "phrase", "Transaction Applicant Identifier"),
        pytest.param("physical", "Customer Account Open Date", "physical", "CUST_ACCT_OPEN_DT"),
        pytest.param("check", "TXN_APPLNT_ID", "compliant", True),
        pytest.param("normalize", "custmr_acct_num", "normalized", "CUST_ACCT_NBR"),
        pytest.param("audit", "CUST_ACCT_KYC_ID", "unknown_tokens", ["KYC"]),
    ],
)
def test_each_op_returns_what_its_verb_returns(
    batch: Callable[..., Invocation], op: str, subject: str, key: str, expected: Any
) -> None:
    """The batch adds an envelope and no opinions.

    Each record's ``result`` is the payload the matching verb produces for that
    one name, so a caller can read the same JSON contract whether they called
    the library once or fifty thousand times.
    """
    outcome = batch(
        f"{subject}\n",
        "governed-batch",
        "--dictionary",
        GOVERNED_BUNDLE,
        "--op",
        op,
    )

    assert outcome.exit_code == EXIT_OK, outcome.text
    assert batch_records(outcome)[0]["result"][key] == expected


def test_the_audit_op_answers_for_a_name_it_has_nothing_to_say_about(
    batch: Callable[..., Invocation],
) -> None:
    """A batch owes an answer for every line, including the clean ones.

    ``audit_identifiers`` keeps a detail record only for identifiers worth
    looking at, which is right for a corpus report and wrong for a stream where
    a missing line is indistinguishable from a lost one.
    """
    outcome = batch(
        "TXN_APPLNT_ID\n",
        "governed-batch",
        "--dictionary",
        GOVERNED_BUNDLE,
        "--op",
        "audit",
    )

    assert outcome.exit_code == EXIT_OK, outcome.text
    record = batch_records(outcome)[0]["result"]
    assert record["identifier"] == "TXN_APPLNT_ID"
    assert record["is_fully_known"] is True
    assert record["compliant"] is True
    assert record["unknown_tokens"] == []


def test_the_record_stream_is_ascii_whatever_the_identifier_holds(
    batch: Callable[..., Invocation],
) -> None:
    """The stream crosses a process boundary, where the code page is not ours.

    Escaping every non-ASCII character keeps a record readable by a consumer on
    any console encoding, and JSON says the two spellings mean the same string.
    """
    outcome = batch(
        "TXN_ÜBER_ID\n",
        "governed-batch",
        "--dictionary",
        GOVERNED_BUNDLE,
    )

    assert outcome.exit_code == EXIT_OK, outcome.text
    assert outcome.stdout.isascii()
    assert batch_records(outcome)[0]["input"] == "TXN_ÜBER_ID"


def test_a_batch_overlay_is_layered_once_for_the_whole_run(
    batch: Callable[..., Invocation],
) -> None:
    """``--custom`` has to reach a batch, or a caller with house acronyms cannot use it."""
    outcome = batch(
        "KYC_REVIEW_DT\n",
        "governed-batch",
        "--dictionary",
        GOVERNED_BUNDLE,
        "--custom",
        '{"KYC": "Know Your Customer"}',
    )

    assert outcome.exit_code == EXIT_OK, outcome.text
    result = batch_records(outcome)[0]["result"]
    # REVIEW keeps its shape because the standard's allow-list approves it and
    # re-casing an approved token would be correcting the standard; the overlay
    # is the KYC half.
    assert result["phrase"] == "Know Your Customer REVIEW Date"
    assert result["is_fully_known"] is True


def test_governed_batch_reads_a_file_argument(
    run: Callable[..., Invocation], tmp_path: Path
) -> None:
    """The same command, with the corpus already on disk rather than in a pipe."""
    corpus = tmp_path / "columns.txt"
    corpus.write_text("TXN_ID\nAPPLNT_BRTH_DT\n", encoding="utf-8")

    outcome = run("governed-batch", str(corpus), "--dictionary", GOVERNED_BUNDLE)

    assert outcome.exit_code == EXIT_OK, outcome.text
    assert len(batch_records(outcome)) == 2


# ---------------------------------------------------------------------------
# A consumer that stops reading is success, not a crash
# ---------------------------------------------------------------------------
def test_a_consumer_that_closes_the_pipe_is_not_an_error(tmp_path: Path) -> None:
    """``acronymkit governed-batch ... | head -1`` exits 0 with no traceback.

    The whole point of a streaming command is that the reader sees the first
    answer before the last question is asked, so a reader that has seen enough
    and closed the pipe is the command working. Run out of process because that
    is the only place a real pipe exists: an in-process stub can imitate the
    exception but not the interpreter's own flush on the way out, which is what
    turned a handled condition into exit ``120``.

    Two platforms, one condition, two errors — POSIX raises ``BrokenPipeError``
    and Windows a plain ``OSError`` with ``EINVAL`` — so this asserts the outcome
    rather than the exception type.
    """
    corpus = tmp_path / "wide.txt"
    corpus.write_text("".join(f"TXN_ID_{index}\n" for index in range(20_000)), encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "acronymkit.cli",
            "governed-batch",
            str(corpus),
            "--dictionary",
            GOVERNED_BUNDLE,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(REPO_ROOT),
        env=dict(os.environ, PYTHONPATH=str(SRC), PYTHONDONTWRITEBYTECODE="1"),
    )
    assert process.stdout is not None and process.stderr is not None
    first = process.stdout.readline()
    process.stdout.close()
    complaints = process.stderr.read().decode("utf-8", "replace")
    process.stderr.close()

    assert process.wait(timeout=120) == EXIT_OK, complaints
    assert "Traceback" not in complaints
    assert json.loads(first)["line"] == 1


def test_a_broken_pipe_is_told_apart_from_any_other_os_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``main`` returns 0 for a closed consumer and re-raises everything else.

    The Windows half of :func:`~acronymkit.cli._is_closed_consumer` reads a bare
    ``EINVAL`` as a hang-up, which is a real loss of precision and is the reason
    the other direction is asserted here: an ``OSError`` that is not that
    condition must still reach the interpreter rather than be reported as a
    clean run.

    The redirect itself is stubbed out. It really does ``dup2`` over file
    descriptor 1, which is the right thing for a process that is exiting and the
    wrong thing to do to the harness capturing this test; the subprocess test
    above is where it runs for real.
    """
    import acronymkit.cli as cli_module

    monkeypatch.setattr(cli_module, "_abandon_stdout", lambda: None)

    def raise_it(exc: BaseException) -> Callable[..., Any]:
        def _raise(*_args: Any, **_kwargs: Any) -> Any:
            raise exc

        return _raise

    monkeypatch.setattr(cli_module, "cli", raise_it(BrokenPipeError()))
    assert cli_module.main(["version"]) == EXIT_OK

    if sys.platform == "win32":
        monkeypatch.setattr(cli_module, "cli", raise_it(OSError(errno.EINVAL, "Invalid argument")))
        assert cli_module.main(["version"]) == EXIT_OK

    monkeypatch.setattr(cli_module, "cli", raise_it(OSError(errno.EACCES, "Permission denied")))
    with pytest.raises(OSError, match="Permission denied"):
        cli_module.main(["version"])


# ---------------------------------------------------------------------------
# governed-audit: the first thing a new adopter runs
# ---------------------------------------------------------------------------
CORPUS = "CUST_ACCT_KYC_ID\nTRNCH_ID_TRNCH_AM\nCUSTOMER_ACCOUNT_ID\nTXN_APPLNT_ID\n"


def test_governed_audit_reports_coverage_and_the_backlog(
    batch: Callable[..., Invocation],
) -> None:
    """The ranked unknown-token table is why this command exists.

    It turns "our catalog is incomplete" into a finite list of rows to write, in
    the order that clears the most columns per row.
    """
    outcome = batch(CORPUS, "governed-audit", "--dictionary", GOVERNED_BUNDLE)

    assert outcome.exit_code == EXIT_OK, outcome.text
    assert "Governed naming audit" in outcome.stdout
    assert "identifiers      4 (4 distinct)" in outcome.stdout
    assert "TRNCH" in outcome.stdout
    assert "KYC" in outcome.stdout


def test_governed_audit_json_is_the_audit_payload(batch: Callable[..., Invocation]) -> None:
    """A report a person reads and a payload a program reads, from one pass."""
    outcome = batch(CORPUS, "governed-audit", "--dictionary", GOVERNED_BUNDLE, "--format", "json")

    assert outcome.exit_code == EXIT_OK, outcome.text
    payload = json.loads(outcome.stdout)
    assert payload["total"] == 4
    assert payload["distinct"] == 4
    assert [token["token"] for token in payload["unknown_tokens"]][:1] == ["TRNCH"]
    assert "suggestions" not in payload


def test_the_suggestions_separate_a_decision_from_an_edit(
    batch: Callable[..., Invocation],
) -> None:
    """Two kinds of backlog row, and only one of them needs anybody to decide anything.

    ``CUSTOMER`` is a word the catalog already governs, so the answer is an edit
    to the column name. ``TRNCH`` is a row somebody has to write, and the
    library proposes no wording for it.
    """
    outcome = batch(
        CORPUS,
        "governed-audit",
        "--dictionary",
        GOVERNED_BUNDLE,
        "--format",
        "json",
        "--suggest",
    )

    assert outcome.exit_code == EXIT_OK, outcome.text
    proposals = {
        item["token"]: item["proposed_abbreviation"]
        for item in json.loads(outcome.stdout)["suggestions"]
    }
    assert proposals["CUSTOMER"] == "CUST"
    assert proposals["TRNCH"] is None


def test_governed_audit_still_reports_when_a_line_cannot_be_read(
    batch: Callable[..., Invocation],
) -> None:
    """A corpus with one bad line is still a corpus worth reporting on.

    The report is printed, the unreadable lines are named on stderr, and the
    exit status says the corpus was not read whole — so nobody mistakes a
    partial audit for a complete one.
    """
    outcome = batch(
        'TXN_ID\n{"identifier": null}\n',
        "governed-audit",
        "--dictionary",
        GOVERNED_BUNDLE,
    )

    assert outcome.exit_code == EXIT_FAILURE
    assert "Governed naming audit" in outcome.stdout
    assert "identifiers      1 (1 distinct)" in outcome.stdout
    assert "line 2" in outcome.stderr


# ---------------------------------------------------------------------------
# --unknown: letting a stale catalog stop a pipeline
# ---------------------------------------------------------------------------
def test_unknown_reject_turns_a_missing_catalog_row_into_a_hard_error(
    run: Callable[..., Invocation],
) -> None:
    """The governed case ``--policy`` alone could not express.

    None of the four presets sets ``UnknownPolicy.REJECT``, so until this flag
    existed a caller who wanted an unrecognised token to stop their pipeline —
    which is the whole reason the policy value exists — had to drop out of the
    command line into the Python API. The error names the offending token,
    because "the catalog is out of date" is not actionable and "``DOB`` is not
    in it" is.

    Run through ``main`` rather than ``CliRunner``: the raise is what is being
    tested, and a runner holds it as ``result.exception`` instead of rendering
    it, so the message a caller would actually read never reaches either stream.
    """
    outcome = run(
        "expand-identifier",
        "TXN_DOB_DT",
        "--dictionary",
        GOVERNED_BUNDLE,
        "--unknown",
        "reject",
    )

    assert outcome.exit_code == EXIT_FAILURE
    assert "DOB" in outcome.stderr
    assert "Traceback" not in outcome.text


def test_the_same_name_passes_through_when_unknown_is_not_overridden(runner: Any) -> None:
    """The control for the test above: the flag is what changed the outcome.

    Without it the identifier is answered, with the unrecognised token Title
    Cased and flagged rather than raised on, so the two runs differ in one
    argument and nothing else.
    """
    result = runner.invoke(
        build_cli(),
        ["expand-identifier", "TXN_DOB_DT", "--dictionary", GOVERNED_BUNDLE, "--format", "json"],
    )

    assert result.exit_code == 0, runner_output(result)
    payload = json.loads(runner_output(result))
    assert payload["phrase"] == "Transaction Dob Date"
    assert payload["is_fully_known"] is False


def test_a_rejected_token_is_one_failed_record_and_not_a_failed_batch(
    batch: Callable[..., Invocation],
) -> None:
    """The ``LexiconError`` record the JSON contract documents, actually produced.

    ``docs/notes/governed-json-contract.md`` §7.2 specifies ``error_type`` for a
    token rejected while answering, and a specification no command can reach is
    a specification nobody can check. The record envelope still holds: the bad
    line reports itself, the next line is still answered, and the run exits
    non-zero because a record failed.
    """
    outcome = batch(
        "TXN_DOB_DT\nTXN_APPLNT_ID\n",
        "governed-batch",
        "--dictionary",
        GOVERNED_BUNDLE,
        "--unknown",
        "reject",
    )

    assert outcome.exit_code == EXIT_FAILURE
    records = batch_records(outcome)
    assert [record["ok"] for record in records] == [False, True]
    assert records[0]["error_type"] == "LexiconError"
    assert "DOB" in records[0]["error"]
    assert records[1]["result"]["phrase"] == "Transaction Applicant Identifier"
    assert json.loads(outcome.stderr.strip())["failed"] == 1


def test_check_name_reports_an_unknown_token_even_under_reject(runner: Any) -> None:
    """``--unknown`` reaches the expansion verbs and no others, and that is not a gap.

    A compliance check that raised on the token it was asked to report would
    have nothing left to say. The flag is accepted here rather than refused so
    that one policy can be named once for a whole pipeline, and this pins the
    consequence so nobody reads the acceptance as a promise to raise.
    """
    result = runner.invoke(
        build_cli(),
        [
            "check-name",
            "TXN_DOB_DT",
            "--dictionary",
            GOVERNED_BUNDLE,
            "--unknown",
            "reject",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == EXIT_FAILURE
    payload = json.loads(runner_output(result))
    assert payload["compliant"] is False
    assert "DOB" in {reason["token"] for reason in payload["reasons"]}


def test_governed_audit_refuses_reject_and_says_why(batch: Callable[..., Invocation]) -> None:
    """Listing the tokens a catalog is silent about is what an audit is for.

    Under ``REJECT`` the audit would stop at the first one, so a caller asking
    "how many gaps" would learn only "at least one". It is refused at the door
    with a message naming the setting to use instead, rather than allowed to
    raise from somewhere inside the corpus.
    """
    outcome = batch(
        "TXN_DOB_DT\n",
        "governed-audit",
        "--dictionary",
        GOVERNED_BUNDLE,
        "--unknown",
        "reject",
    )

    assert outcome.exit_code == EXIT_FAILURE
    assert "REJECT" in outcome.stderr
    assert "PASSTHROUGH_TITLECASE" in outcome.stderr


@pytest.mark.parametrize("preset", ["governed_default", "frequency_baseline", "strict_length"])
def test_omitting_unknown_leaves_the_preset_exactly_as_it_was(preset: str) -> None:
    """A flag nobody typed must change nothing, and the risk here is not hypothetical.

    ``neural_optin`` is the one preset whose ``unknown`` is not
    ``passthrough_titlecase``, so a ``--unknown`` defaulting to that value would
    have quietly undone the opt-in for every caller who never typed the flag.
    Asserted through the helper rather than a command because no command prints
    the policy it resolved.
    """
    from acronymkit.cli import _governed_policy
    from acronymkit.governed.policy import NamingPolicy

    assert _governed_policy(preset) == getattr(NamingPolicy, preset)()
    assert _governed_policy("neural_optin").unknown.value == "neural"
    assert _governed_policy("neural_optin", "reject").unknown.value == "reject"
    assert NamingPolicy.neural_optin().unknown.value == "neural"


def test_an_override_changes_the_unknown_field_and_no_other(runner: Any) -> None:
    """``--unknown`` overrides one field, so the named preset still describes the run.

    ``strict_length`` is the preset to check it against: its distinguishing
    field is not ``unknown``, so if the copy lost anything the length finding
    would stop being reported.
    """
    over_long = "CUST_ACCT_PRIMARY_OWNER_PARTY_VERIFICATION_STAT_CD"
    result = runner.invoke(
        build_cli(),
        [
            "check-name",
            over_long,
            "--dictionary",
            GOVERNED_BUNDLE,
            "--policy",
            "strict_length",
            "--unknown",
            "reject",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == EXIT_FAILURE
    codes = {reason["code"] for reason in json.loads(runner_output(result))["reasons"]}
    assert "exceeds_max_length" in codes


def test_unknown_rejects_a_value_that_is_not_one_of_the_two(runner: Any) -> None:
    """``neural`` is deliberately absent, and a typo must not be read as a preference.

    It behaves as passthrough in this release, so offering it here would be a
    third spelling of a flag that does nothing; ``--policy neural_optin`` is
    where the declaration of intent belongs.
    """
    result = runner.invoke(
        build_cli(),
        ["expand-token", "TXN", "--dictionary", GOVERNED_BUNDLE, "--unknown", "neural"],
    )

    assert result.exit_code == EXIT_USAGE
