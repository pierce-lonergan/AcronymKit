"""Command-line front end for :mod:`acronymkit`.

The console script declared in ``pyproject.toml`` (``acronymkit =
acronymkit.cli:main``) resolves here. Eight commands cover the whole public
surface::

    acronymkit generate  "Application Programming Interface"
    acronymkit backronym "Next Generation High Performance Storage" NEXUS
    acronymkit synthesize RAM
    acronymkit extract    paper.txt        # or '-' / a pipe for stdin
    acronymkit score      PDF "Portable Document Format"
    acronymkit tokens     "Multi-Factor Authentication"
    acronymkit schema
    acronymkit version

Optional dependency
-------------------
``click`` is an *optional* extra (``pip install 'acronymkit[cli]'``), so this
module must stay importable on an installation that does not have it: nothing
here imports ``click`` at module scope. Every entry point routes through
:func:`_require_click`, which raises :class:`_CliDependencyError` with an
actionable message; :func:`main` turns that into exit status ``2`` rather than
an :exc:`ImportError` traceback. That is also why the command group is built
inside :func:`build_cli` rather than written with module-level decorators — the
usual click idiom would execute ``click.group()`` at import time.

Configuration
-------------
Every analysis command accepts the same configuration options. Values come from
three layers, later layers winning:

1. :class:`~acronymkit.config.Config` defaults;
2. ``--config FILE``, a JSON object of ``Config`` field names;
3. explicit command-line flags.

Because an unset flag must be distinguishable from a flag set to a falsey
value, every configuration option defaults to ``None`` and only non-``None``
values are merged — including the ``--include-articles/--no-include-articles``
pair, which stays ``None`` until one of the two forms is given.

Exit status
-----------
``0``
    The command produced its output.
``1``
    The engine refused the input: a blank phrase
    (:class:`~acronymkit.exceptions.EmptyPhraseError`), no candidate surviving
    the constraints (:class:`~acronymkit.exceptions.NoCandidateError`), or any
    other :class:`~acronymkit.exceptions.AcronymKitError` such as an
    unavailable tier or a missing resource. The message goes to stderr; no
    traceback is printed.
``2``
    Usage error — an unknown flag, a bad enum value, an unreadable
    ``--config`` file, an inconsistent configuration, or the absence of
    ``click`` itself.

:func:`main` is total with respect to user error: it converts every expected
failure into one of those codes and never propagates an exception to the
interpreter.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, Optional, Sequence, TypeVar

from pydantic import ValidationError

from .config import Config
from .engine import AcronymEngine
from .enums import EngineTier, Language, ScoringStrategy
from .exceptions import AcronymKitError
from .models import (
    AcronymCandidate,
    AcronymResult,
    BackronymResult,
    ExtractionResult,
    ScoreBreakdown,
    Token,
)

__all__ = ["cli", "main"]


#: Program name shown in usage lines, independent of ``sys.argv[0]``.
PROG_NAME = "acronymkit"

#: Success.
EXIT_OK = 0

#: The engine declined the input (empty phrase, no candidate, bad tier).
EXIT_FAILURE = 1

#: Usage error, or a missing optional dependency.
EXIT_USAGE = 2

#: Shown when ``click`` is not importable.
_CLICK_MISSING = (
    "This command needs the CLI extra: pip install acronymkit[cli]\n"
    "(quote the extra for zsh/fish: pip install 'acronymkit[cli]')"
)

#: Output formats accepted by ``--format``.
_FORMATS = ("text", "json")

#: Default ``--indent`` for JSON output; ``0`` selects the compact form.
_DEFAULT_INDENT = 2

#: Enum-valued options: flag name -> (enum class, ``Config`` field).
_ENUM_OPTIONS: dict[str, tuple[Any, str]] = {
    "tier": (EngineTier, "engine_tier"),
    "strategy": (ScoringStrategy, "scoring_strategy"),
    "language": (Language, "language"),
}

#: Plain-valued options: flag name -> ``Config`` field.
_SCALAR_OPTIONS: dict[str, str] = {
    "min_length": "min_acronym_length",
    "max_length": "max_acronym_length",
    "top": "max_candidates",
    "include_articles": "include_articles",
}

_Decorator = TypeVar("_Decorator", bound=Callable[..., Any])

#: Memoised command group; see :func:`build_cli`.
_GROUP: Optional[Any] = None


class _CliDependencyError(AcronymKitError):
    """Raised when the optional ``click`` dependency is not importable.

    Private because it exists only to carry the install hint from
    :func:`_require_click` up to :func:`main`, which renders it as exit status
    :data:`EXIT_USAGE`.
    """


def _require_click() -> Any:
    """Import and return the :mod:`click` module.

    Returns:
        The imported ``click`` module.

    Raises:
        _CliDependencyError: If ``click`` is not installed, carrying the
            ``pip install`` hint as its message.
    """
    try:
        import click
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise _CliDependencyError(_CLICK_MISSING) from exc
    return click


def _choices(enum_cls: Any) -> list[str]:
    """Return an enum's string values in declaration order.

    Args:
        enum_cls: One of the :mod:`acronymkit.enums` string enums.

    Returns:
        The ``value`` of every member, suitable for :class:`click.Choice`.
    """
    return [member.value for member in enum_cls]


# ---------------------------------------------------------------------------
# configuration assembly
# ---------------------------------------------------------------------------
def _read_config_file(click: Any, path: str) -> dict[str, Any]:
    """Load a ``--config`` JSON file into a plain dictionary.

    Args:
        click: The imported ``click`` module.
        path: Filesystem path to a JSON object of ``Config`` field names.

    Returns:
        The decoded mapping.

    Raises:
        click.UsageError: If the file is unreadable, is not valid JSON, or does
            not hold a JSON object.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise click.UsageError(f"could not read --config file '{path}': {exc}") from exc
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise click.UsageError(f"--config file '{path}' is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise click.UsageError(
            f"--config file '{path}' must contain a JSON object of Config fields, "
            f"got {type(payload).__name__}"
        )
    return dict(payload)


def _format_validation_error(exc: ValidationError) -> str:
    """Condense a Pydantic validation failure into one CLI-sized line.

    Pydantic's own rendering spans several lines per error and carries an
    upstream documentation URL, which is noise at a terminal. Each error is
    reduced to ``field: message``, with whole-model errors (the ones raised by
    ``Config``'s cross-field validator, whose location is empty) labelled
    ``config``.

    Args:
        exc: The failure raised while constructing :class:`Config`.

    Returns:
        The errors joined by ``"; "``.
    """
    parts: list[str] = []
    for error in exc.errors():
        location = ".".join(str(item) for item in error.get("loc", ())) or "config"
        message = str(error.get("msg", "")).removeprefix("Value error, ")
        parts.append(f"{location}: {message}")
    return "; ".join(parts) or str(exc)


def _build_config(click: Any, options: dict[str, Any]) -> Config:
    """Merge the configuration layers into one validated :class:`Config`.

    ``--config`` supplies the base and explicit flags override it, so a shared
    profile can be checked in and tweaked per invocation.

    Args:
        click: The imported ``click`` module.
        options: The command callback's keyword arguments.

    Returns:
        The validated configuration.

    Raises:
        click.UsageError: If the ``--config`` file is unusable or the merged
            field set is rejected by ``Config`` (unknown field, out-of-range
            value, ``min_length`` above ``max_length``).
    """
    payload: dict[str, Any] = {}
    config_path = options.get("config_path")
    if config_path:
        payload.update(_read_config_file(click, str(config_path)))
    for flag, (enum_cls, field) in _ENUM_OPTIONS.items():
        value = options.get(flag)
        if value is not None:
            payload[field] = enum_cls.coerce(value)
    for flag, field in _SCALAR_OPTIONS.items():
        value = options.get(flag)
        if value is not None:
            payload[field] = value
    try:
        return Config(**payload)
    except ValidationError as exc:
        raise click.UsageError(f"invalid configuration: {_format_validation_error(exc)}") from exc
    except (ValueError, TypeError) as exc:
        raise click.UsageError(f"invalid configuration: {exc}") from exc


def _make_engine(click: Any, options: dict[str, Any]) -> AcronymEngine:
    """Build the engine a command should run against.

    Args:
        click: The imported ``click`` module.
        options: The command callback's keyword arguments.

    Returns:
        An engine configured from the merged option layers.

    Raises:
        click.UsageError: If the configuration is invalid.
        TierUnavailableError: If the requested tier has no installed runtime and
            may not degrade.
    """
    return AcronymEngine(_build_config(click, options))


def _read_input(click: Any, source: Optional[str]) -> str:
    """Read the document a command should operate on.

    Args:
        click: The imported ``click`` module.
        source: A filesystem path, ``"-"`` for standard input, or ``None`` to
            use standard input when it is not a terminal.

    Returns:
        The decoded text.

    Raises:
        click.UsageError: If no source was given and standard input is a
            terminal, or if the named file cannot be read as UTF-8.
    """
    if source is None:
        if _stdin_is_tty():
            raise click.UsageError(
                "no FILE given and stdin is a terminal; pass a path, pass '-', or pipe the text in"
            )
        source = "-"
    if source == "-":
        if sys.stdin is None:  # pragma: no cover - detached interpreter
            raise click.UsageError("stdin is not available to read from")
        return sys.stdin.read()
    try:
        return Path(source).read_text(encoding="utf-8")
    except OSError as exc:
        raise click.UsageError(f"could not read '{source}': {exc}") from exc
    except UnicodeDecodeError as exc:
        raise click.UsageError(f"'{source}' is not valid UTF-8 text: {exc}") from exc


def _stdin_is_tty() -> bool:
    """Report whether standard input is an interactive terminal.

    Returns:
        ``True`` when stdin is a TTY, ``False`` when it is a pipe, a file, or
        unavailable (a closed or detached stream cannot be interactive).
    """
    stream = sys.stdin
    if stream is None:
        return False
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):  # pragma: no cover - closed stream
        return False


# ---------------------------------------------------------------------------
# rendering helpers
# ---------------------------------------------------------------------------
def _yes_no(flag: bool) -> str:
    """Render a boolean as ``'yes'`` / ``'no'``."""
    return "yes" if flag else "no"


def _table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    right_aligned: Sequence[int] = (),
) -> list[str]:
    """Lay out rows as a fixed-width table.

    Column widths come from the widest cell, so the output aligns without
    depending on terminal width or on any drawing characters.

    Args:
        headers: Column headings.
        rows: Cell text, one sequence per row, each the length of ``headers``.
        right_aligned: Indices of columns to right-align (numeric columns).

    Returns:
        The heading line, a dashed rule, and one line per row, each with
        trailing whitespace stripped.
    """
    widths = [len(header) for header in headers]
    for row in rows:
        for column, cell in enumerate(row):
            widths[column] = max(widths[column], len(cell))
    right = set(right_aligned)

    def lay_out(cells: Sequence[str]) -> str:
        parts = [
            cell.rjust(widths[column]) if column in right else cell.ljust(widths[column])
            for column, cell in enumerate(cells)
        ]
        return "  ".join(parts).rstrip()

    lines = [lay_out(headers), lay_out(["-" * width for width in widths])]
    lines.extend(lay_out(row) for row in rows)
    return lines


def _breakdown_lines(breakdown: ScoreBreakdown, label: str) -> list[str]:
    """Render a :class:`~acronymkit.models.ScoreBreakdown` as an audit block.

    Each term is shown with its coefficient and its signed contribution, so the
    numbers on screen add up to the reported total, followed by the one-line
    arithmetic trace from
    :meth:`~acronymkit.models.ScoreBreakdown.explain`.

    Args:
        breakdown: The decomposition to render.
        label: The acronym the breakdown belongs to.

    Returns:
        The block's lines, starting with a heading.
    """
    terms = (
        ("positional", breakdown.positional, breakdown.alpha, 1.0),
        ("phonotactic", breakdown.phonotactic, breakdown.beta, 1.0),
        ("lexical", breakdown.lexical, breakdown.gamma, 1.0),
        ("information_loss", breakdown.information_loss, breakdown.delta, -1.0),
    )
    rows = [
        [name, f"{value:.3f}", f"{coefficient:g}", f"{sign * value * coefficient:.3f}"]
        for name, value, coefficient, sign in terms
    ]
    rows.append(["total", "", "", f"{breakdown.total:.3f}"])
    lines = [f"Score breakdown for {label}:"]
    lines.extend(
        "  " + line for line in _table(["TERM", "VALUE", "COEFF", "CONTRIBUTION"], rows, (1, 2, 3))
    )
    lines.append(f"  {breakdown.explain()}")
    return lines


def _candidate_rows(candidates: Sequence[AcronymCandidate]) -> list[list[str]]:
    """Build the ``generate`` table body.

    Args:
        candidates: The ranked candidates, best first.

    Returns:
        One row of ``rank / acronym / score / pronounceability / dictionary``
        per candidate.
    """
    return [
        [
            str(rank),
            candidate.acronym,
            f"{candidate.score:.3f}",
            f"{candidate.pronounceability_score:.2f}",
            _yes_no(candidate.is_dictionary_word),
        ]
        for rank, candidate in enumerate(candidates, start=1)
    ]


def _render_generate(result: AcronymResult) -> list[str]:
    """Render a generation result as aligned text.

    Args:
        result: The engine's :class:`~acronymkit.models.AcronymResult`.

    Returns:
        The lines to print: a header, the ranked candidate table, and the
        primary candidate's score breakdown when one was attached.
    """
    lines = [
        f"Phrase:  {result.source_phrase}",
        f"Primary: {result.primary_acronym}  (score {result.score:.3f})",
        "",
    ]
    lines.extend(
        _table(
            ["RANK", "ACRONYM", "SCORE", "PRONOUNCE", "DICT"],
            _candidate_rows(result.alternatives),
            (0, 2, 3),
        )
    )
    primary = result.primary
    if primary is not None and primary.breakdown is not None:
        lines.append("")
        lines.extend(_breakdown_lines(primary.breakdown, primary.acronym))
    notes = [f"warning: {warning}" for warning in result.metadata.warnings]
    if result.metadata.truncated:
        notes.insert(0, "note: the search hit a budget and was truncated.")
    if notes:
        lines.append("")
        lines.extend(notes)
    return lines


def _render_backronym(result: BackronymResult) -> list[str]:
    """Render a backronym result as aligned text.

    Args:
        result: The engine's :class:`~acronymkit.models.BackronymResult`. Works
            for both the aligned and the synthesised flavour; the source-phrase
            line is omitted when there is no phrase.

    Returns:
        The lines to print.
    """
    lines: list[str] = []
    if result.source_phrase:
        lines.append(f"Phrase:  {result.source_phrase}")
    lines.append(f"Target:  {result.target_word}")
    if not result.candidates:
        lines.append("")
        lines.append("No expansion could be built for this target word.")
        return lines
    lines.append(f"Primary: {result.primary_expansion}  (score {result.score:.3f})")
    lines.append("")
    rows = [
        [
            str(rank),
            candidate.expansion_text or "(empty)",
            f"{candidate.score:.3f}",
            f"{candidate.coverage * 100:.0f}%",
            "".join(candidate.unmapped_letters) or "-",
        ]
        for rank, candidate in enumerate(result.candidates, start=1)
    ]
    lines.extend(_table(["RANK", "EXPANSION", "SCORE", "COVERAGE", "UNMAPPED"], rows, (0, 2, 3)))
    return lines


def _render_extraction(result: ExtractionResult) -> list[str]:
    """Render extracted definition pairs as aligned text.

    Args:
        result: The engine's :class:`~acronymkit.models.ExtractionResult`.

    Returns:
        The lines to print, or a single explanatory line when the document
        defines nothing.
    """
    if not result.pairs:
        return ["No abbreviation definitions found."]
    rows = [
        [
            pair.short_form,
            pair.long_form,
            f"{pair.confidence:.2f}",
            pair.pattern,
            f"{pair.short_form_span[0]}:{pair.short_form_span[1]}",
            f"{pair.long_form_span[0]}:{pair.long_form_span[1]}",
        ]
        for pair in result.pairs
    ]
    header = f"{len(result.pairs)} definition(s) found."
    lines = [header, ""]
    lines.extend(
        _table(
            ["SHORT", "LONG", "CONF", "PATTERN", "SHORT SPAN", "LONG SPAN"],
            rows,
            (2,),
        )
    )
    return lines


def _render_score(
    acronym: str, phrase: str, candidate: AcronymCandidate, tokens: Sequence[Token]
) -> list[str]:
    """Render a scored acronym, its letter alignment and its breakdown.

    Args:
        acronym: The acronym as the user typed it.
        phrase: The phrase it was scored against.
        candidate: The engine's scored candidate.
        tokens: The phrase's tokens, used to name the aligned token per letter.

    Returns:
        The lines to print.
    """
    normalised = "" if candidate.acronym == acronym else f"  (normalised from '{acronym}')"
    lines = [
        f"Acronym: {candidate.acronym}{normalised}",
        f"Phrase:  {phrase}",
        f"Score:   {candidate.score:.3f}",
        f"Dictionary word:  {_yes_no(candidate.is_dictionary_word)}",
        f"Pronounceability: {candidate.pronounceability_score:.2f}",
        "",
    ]
    rows = []
    for mapping in candidate.mappings:
        index = mapping.token_index
        if index is not None and 0 <= index < len(tokens):
            token_cell = f"{index}:{tokens[index].text}"
        else:
            token_cell = "-"
        rows.append(
            [
                str(mapping.position),
                mapping.character,
                token_cell,
                "-" if mapping.char_offset is None else str(mapping.char_offset),
                mapping.kind.value,
                f"{mapping.weight:.1f}",
            ]
        )
    lines.extend(_table(["POS", "CHAR", "TOKEN", "OFFSET", "KIND", "OMEGA"], rows, (0, 3, 5)))
    if candidate.breakdown is not None:
        lines.append("")
        lines.extend(_breakdown_lines(candidate.breakdown, candidate.acronym))
    return lines


def _render_tokens(phrase: str, tokens: Sequence[Token]) -> list[str]:
    """Render the token stream, one line per token.

    Args:
        phrase: The analysed phrase.
        tokens: The engine's analysed tokens.

    Returns:
        The lines to print: a header and a table carrying each token's role,
        eligibility and donated letters.
    """
    if not tokens:
        return [f"Phrase: {phrase}", "", "No tokens."]
    rows = [
        [
            str(token.index),
            token.text,
            token.role.value,
            token.pos or "-",
            token.stop_word_category.value if token.stop_word_category else "-",
            _yes_no(token.is_eligible),
            _yes_no(token.is_critical),
            token.letters or "-",
            f"{token.start}:{token.end}",
        ]
        for token in tokens
    ]
    eligible = sum(1 for token in tokens if token.is_eligible)
    lines = [
        f"Phrase: {phrase}",
        f"{len(tokens)} token(s), {eligible} eligible to donate letters.",
        "",
    ]
    lines.extend(
        _table(
            ["#", "TEXT", "ROLE", "POS", "STOPWORD", "ELIGIBLE", "CRITICAL", "LETTERS", "SPAN"],
            rows,
            (0,),
        )
    )
    return lines


def _emit(click: Any, lines: Sequence[str]) -> None:
    """Write rendered text lines to standard output.

    Args:
        click: The imported ``click`` module.
        lines: The lines to print, without trailing newlines.
    """
    click.echo("\n".join(lines))


def _emit_json(click: Any, payload: Any, indent: int) -> None:
    """Write a JSON payload to standard output.

    Args:
        click: The imported ``click`` module.
        payload: Any JSON-encodable object.
        indent: Indentation width; ``0`` selects the compact single-line form.
    """
    click.echo(json.dumps(payload, indent=indent or None, ensure_ascii=False))


# ---------------------------------------------------------------------------
# command group
# ---------------------------------------------------------------------------
def _output_options(click: Any) -> Callable[[_Decorator], _Decorator]:
    """Build the decorator carrying ``--format`` and ``--indent``.

    Args:
        click: The imported ``click`` module.

    Returns:
        A decorator that applies both options to a command callback.
    """
    options = [
        click.option(
            "--format",
            "output_format",
            type=click.Choice(_FORMATS),
            default="text",
            show_default=True,
            help="Render aligned text or a machine-readable JSON payload.",
        ),
        click.option(
            "--indent",
            type=click.IntRange(min=0),
            default=_DEFAULT_INDENT,
            show_default=True,
            help="JSON indentation width; 0 emits compact single-line JSON.",
        ),
    ]

    def decorate(func: _Decorator) -> _Decorator:
        for option in reversed(options):
            func = option(func)
        return func

    return decorate


def _config_options(click: Any) -> Callable[[_Decorator], _Decorator]:
    """Build the decorator carrying every engine-configuration option.

    Each option defaults to ``None`` so that an unset flag can be told apart
    from one that was set to a default-looking value; only non-``None`` values
    reach :class:`~acronymkit.config.Config`.

    Args:
        click: The imported ``click`` module.

    Returns:
        A decorator that applies the shared configuration options, followed by
        ``--format`` and ``--indent``, to a command callback.
    """
    options = [
        click.option(
            "--tier",
            type=click.Choice(_choices(EngineTier)),
            default=None,
            help="Execution tier to request [default: zero_dependency].",
        ),
        click.option(
            "--strategy",
            type=click.Choice(_choices(ScoringStrategy)),
            default=None,
            help="Scoring weight preset [default: balanced_pronounceable].",
        ),
        click.option(
            "--language",
            type=click.Choice(_choices(Language)),
            default=None,
            help="Language of the bundled stop-word, lexicon and n-gram resources [default: en].",
        ),
        click.option(
            "--min-length",
            type=click.IntRange(min=1),
            default=None,
            help="Shortest acceptable acronym [default: 2].",
        ),
        click.option(
            "--max-length",
            type=click.IntRange(min=1),
            default=None,
            help="Longest acceptable acronym [default: 6].",
        ),
        click.option(
            "--top",
            type=click.IntRange(min=1),
            default=None,
            help="Number of candidates to keep and display [default: 25].",
        ),
        click.option(
            "--include-articles/--no-include-articles",
            "include_articles",
            default=None,
            help="Let articles ('a', 'an', 'the') donate letters [default: off].",
        ),
        click.option(
            "--config",
            "config_path",
            type=click.Path(exists=True, dir_okay=False, readable=True),
            default=None,
            help="JSON file of Config fields; explicit flags above override it.",
        ),
    ]
    output = _output_options(click)

    def decorate(func: _Decorator) -> _Decorator:
        func = output(func)
        for option in reversed(options):
            func = option(func)
        return func

    return decorate


def build_cli() -> Any:
    """Construct (once) and return the ``click`` command group.

    The group is built lazily rather than declared with module-level decorators
    so that importing this module never requires ``click``. The result is
    memoised because building it allocates every command and option object.

    Returns:
        The ``click.Group`` implementing the ``acronymkit`` console script.

    Raises:
        _CliDependencyError: If ``click`` is not installed.
    """
    global _GROUP
    if _GROUP is not None:
        return _GROUP

    click = _require_click()
    config_options = _config_options(click)
    output_options = _output_options(click)

    @click.group(
        context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 100},
        help="Generate, extract and disambiguate acronyms.",
    )
    def group() -> None:
        """Root command group. Help text is supplied via ``help=``."""

    @group.command(
        "generate",
        help="Rank acronyms for PHRASE, best first.",
    )
    @click.argument("phrase")
    @config_options
    def generate_command(phrase: str, **options: Any) -> None:
        """Forward generation: phrase in, ranked acronyms out.

        Args:
            phrase: The text to abbreviate.
            **options: The shared configuration and output options.

        Raises:
            EmptyPhraseError: If the phrase holds no eligible token.
            NoCandidateError: If no candidate satisfied the constraints.
        """
        engine = _make_engine(click, options)
        result = engine.generate(phrase)
        if options["output_format"] == "json":
            _emit_json(click, result.to_dict(), options["indent"])
        else:
            _emit(click, _render_generate(result))

    @group.command(
        "backronym",
        help="Fit TARGET onto the words of PHRASE.",
    )
    @click.argument("phrase")
    @click.argument("target")
    @config_options
    def backronym_command(phrase: str, target: str, **options: Any) -> None:
        """Align a target word onto an existing phrase.

        Args:
            phrase: The phrase supplying the expansion words.
            target: The word the expansion must spell out.
            **options: The shared configuration and output options.

        Raises:
            EmptyPhraseError: If the phrase produces no tokens.
        """
        engine = _make_engine(click, options)
        result = engine.generate_backronym(phrase, target)
        if options["output_format"] == "json":
            _emit_json(click, result.to_dict(), options["indent"])
        else:
            _emit(click, _render_backronym(result))

    @group.command(
        "synthesize",
        help="Invent an expansion for TARGET from the language lexicon.",
    )
    @click.argument("target")
    @config_options
    def synthesize_command(target: str, **options: Any) -> None:
        """Backronym synthesis with no source phrase.

        Args:
            target: The word the expansion must spell out.
            **options: The shared configuration and output options.
        """
        engine = _make_engine(click, options)
        result = engine.synthesize_backronym(target)
        if options["output_format"] == "json":
            _emit_json(click, result.to_dict(), options["indent"])
        else:
            _emit(click, _render_backronym(result))

    @group.command(
        "extract",
        help="Extract 'Long Form (SF)' definitions from FILE, or from stdin when FILE is '-' "
        "or omitted.",
    )
    @click.argument(
        "file",
        required=False,
        default=None,
        type=click.Path(exists=True, dir_okay=False, readable=True, allow_dash=True),
    )
    @config_options
    def extract_command(file: Optional[str], **options: Any) -> None:
        """Schwartz & Hearst extraction over a document.

        Args:
            file: Path to the document, ``"-"`` for standard input, or ``None``
                to read standard input when it is not a terminal.
            **options: The shared configuration and output options.
        """
        engine = _make_engine(click, options)
        text = _read_input(click, file)
        result = engine.extract(text)
        if options["output_format"] == "json":
            _emit_json(click, result.to_dict(), options["indent"])
        else:
            _emit(click, _render_extraction(result))

    @group.command(
        "score",
        help="Score ACRONYM against PHRASE and show the alignment.",
    )
    @click.argument("acronym")
    @click.argument("phrase")
    @config_options
    def score_command(acronym: str, phrase: str, **options: Any) -> None:
        """Score an acronym the caller already has.

        Args:
            acronym: The acronym to evaluate; case and punctuation are ignored.
            phrase: The phrase it is meant to abbreviate.
            **options: The shared configuration and output options.

        Raises:
            EmptyPhraseError: If the phrase produces no tokens.
            NoCandidateError: If the acronym holds no alphanumeric character.
        """
        engine = _make_engine(click, options)
        candidate = engine.score(acronym, phrase)
        if options["output_format"] == "json":
            _emit_json(click, candidate.to_dict(), options["indent"])
        else:
            _emit(click, _render_score(acronym, phrase, candidate, engine.tokenize(phrase)))

    @group.command(
        "tokens",
        help="Show how PHRASE tokenises, and which tokens may donate letters.",
    )
    @click.argument("phrase")
    @config_options
    def tokens_command(phrase: str, **options: Any) -> None:
        """Expose the analysed token stream.

        Args:
            phrase: The text to analyse.
            **options: The shared configuration and output options.
        """
        engine = _make_engine(click, options)
        tokens = engine.tokenize(phrase)
        if options["output_format"] == "json":
            _emit_json(click, [token.to_dict() for token in tokens], options["indent"])
        else:
            _emit(click, _render_tokens(phrase, tokens))

    @group.command(
        "schema",
        help="Print the AcronymEngineResult JSON Schema that 'generate --format json' conforms to.",
    )
    @output_options
    def schema_command(**options: Any) -> None:
        """Print the interchange schema.

        The document is JSON in both output formats; ``--format`` only chooses
        whether it is indented for reading or compacted.

        Args:
            **options: The shared output options.

        Raises:
            ResourceNotFoundError: If the schema is in neither the checkout nor
                the bundled resources.
        """
        from .serialization import load_schema

        indent = options["indent"] if options["output_format"] == "json" else _DEFAULT_INDENT
        _emit_json(click, load_schema(), indent)

    @group.command("version", help="Print the installed acronymkit version.")
    @output_options
    def version_command(**options: Any) -> None:
        """Report the library version.

        Args:
            **options: The shared output options.
        """
        from . import __version__

        if options["output_format"] == "json":
            _emit_json(click, {"name": PROG_NAME, "version": __version__}, options["indent"])
        else:
            _emit(click, [f"{PROG_NAME} {__version__}"])

    @group.command(
        "doctor",
        help="Report what this installation can do, and exit non-zero if it cannot.",
    )
    @click.option(
        "--offline",
        is_flag=True,
        help="Require an air-gap-ready installation; exit non-zero if anything would need the network.",
    )
    @output_options
    def doctor_command(offline: bool, **options: Any) -> None:
        """Print the capability report and set an exit status from it.

        Built for a container start-up probe and for an enterprise's own CI,
        which is why the exit status matters more than the text: a report
        nobody can assert on is a README with extra steps.

        With ``--offline``, the command is a gate rather than a description.
        It fails when this process could be made to reach the network by
        something other than ``acronymkit`` — today that means installed
        ``pydantic`` entry-point plugins, which ``pydantic`` imports while
        building any model. See :func:`acronymkit.config._enforce_offline`.

        Args:
            offline: Treat network-capable findings as failures.
            **options: The shared output options.
        """
        from .diagnostics import capabilities, format_report

        report = capabilities()
        problems: list[str] = []
        if offline:
            plugins = report["network"]["third_party_import_hooks"]["pydantic_entry_point_plugins"]
            if plugins:
                problems.append(
                    f"third-party pydantic plugins are installed and will be imported "
                    f"while building a Config: {', '.join(plugins)}. "
                    f"Set PYDANTIC_DISABLE_PLUGINS=1 or uninstall them."
                )
        report["problems"] = problems
        report["ok"] = not problems

        if options["output_format"] == "json":
            _emit_json(click, report, options["indent"])
        else:
            lines = [format_report(report)]
            if problems:
                lines += ["", "PROBLEMS"] + [f"  - {problem}" for problem in problems]
            elif offline:
                lines += ["", "offline check: OK"]
            _emit(click, lines)
        if problems:
            raise SystemExit(1)

    _GROUP = group
    return group


def cli(
    args: Optional[Sequence[str]] = None,
    *,
    standalone_mode: bool = True,
    **extra: Any,
) -> Any:
    """Invoke the ``click`` command group directly.

    This is the raw click entry point, for callers that want click's own
    behaviour. Most callers — including the console script — want :func:`main`,
    which wraps this one and returns an exit code instead of raising.

    Args:
        args: Argument vector excluding the program name. ``None`` uses
            ``sys.argv[1:]``.
        standalone_mode: Click's own flag. ``True`` (the default) makes click
            print errors and terminate the process; ``False`` makes it return
            or raise so a caller can decide.
        **extra: Forwarded to the click :class:`click.Context`.

    Returns:
        Whatever click's ``Group.main`` returns: ``None`` in standalone mode,
        the callback result or an exit code otherwise.

    Raises:
        _CliDependencyError: If ``click`` is not installed.
        SystemExit: In standalone mode, always.
    """
    group = build_cli()
    return group.main(
        args=args,
        prog_name=PROG_NAME,
        standalone_mode=standalone_mode,
        **extra,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the command line and return a process exit code.

    The console-script entry point. Every anticipated failure — a missing
    ``click``, a usage mistake, an engine refusal — is turned into a message on
    stderr and one of :data:`EXIT_OK`, :data:`EXIT_FAILURE` or
    :data:`EXIT_USAGE`. Nothing a user can type produces a traceback.

    Args:
        argv: Argument vector excluding the program name. ``None`` uses
            ``sys.argv[1:]``.

    Returns:
        ``0`` on success, ``1`` when the engine declined the input, ``2`` for a
        usage error or a missing optional dependency.

    Example:
        >>> main(["version"])
        acronymkit 0.1.0
        0
    """
    try:
        click = _require_click()
    except _CliDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE

    try:
        outcome = cli(
            args=None if argv is None else list(argv),
            standalone_mode=False,
        )
    except click.ClickException as exc:
        exc.show()
        return int(exc.exit_code)
    except click.exceptions.Abort:
        print("aborted", file=sys.stderr)
        return EXIT_FAILURE
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        print("aborted", file=sys.stderr)
        return EXIT_FAILURE
    except AcronymKitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    except BrokenPipeError:  # pragma: no cover - depends on the consumer
        return EXIT_OK
    except SystemExit as exc:  # pragma: no cover - click's own exit paths
        code = exc.code
        return EXIT_OK if code is None else int(code)

    return EXIT_OK if not isinstance(outcome, int) else outcome


if __name__ == "__main__":  # pragma: no cover - module execution shim
    sys.exit(main())
