"""Command-line front end for :mod:`acronymkit`.

The console script declared in ``pyproject.toml`` (``acronymkit =
acronymkit.cli:main``) resolves here. The commands fall into two groups,
matching the two capabilities the library offers.

*Acronyms*: generate them, extract the ones a document defines, score and
inspect them::

    acronymkit generate  "Application Programming Interface"
    acronymkit backronym "Next Generation High Performance Storage" NEXUS
    acronymkit synthesize RAM
    acronymkit extract    paper.txt        # or '-' / a pipe for stdin
    acronymkit score      PDF "Portable Document Format"
    acronymkit tokens     "Multi-Factor Authentication"
    acronymkit schema
    acronymkit version
    acronymkit doctor

*Governed naming* (:mod:`acronymkit.governed`): expand a database identifier
against a vocabulary somebody has already written down, render the reverse
direction, and check a name against the standard::

    acronymkit expand-token      TXN                    --dictionary nds.json
    acronymkit expand-identifier APPLNT_BRTH_DT         --dictionary nds.json
    acronymkit physical-name     "Applicant Birth Date" --dictionary nds.json
    acronymkit normalize-name    APPLNT_BRTH_DT         --dictionary nds.json
    acronymkit check-name        APPLNT_BRTH_DT         --dictionary nds.json
    acronymkit governed-batch    --dictionary std/ --op expand  < columns.txt
    acronymkit governed-audit    --dictionary std/              < columns.txt

Every governed command takes ``--dictionary`` (required — a governed verb with
no governed vocabulary is a contradiction), ``--dictionary-format``,
``--columns``, ``--delimiter``, ``--policy``, ``--custom`` and the shared
``--format``/``--indent`` pair. They take none of the engine configuration
options, because none of them runs the engine: nothing in the governed
subsystem tokenises for pronounceability, scores a candidate or consults a
language resource, so offering ``--strategy`` there would advertise a knob
attached to nothing.

One process for a whole schema
------------------------------
The consumer this subsystem was built for is a schema-governance pipeline
written in another language, which reaches this library across a process
boundary with tens of thousands of column names. One invocation per column is
not a slow design, it is an unusable one: the work per name is microseconds and
an interpreter start-up is tens of milliseconds, so the overhead would be
several orders of magnitude larger than the answer. ``governed-batch`` is the
shape that fixes it — one invocation, one vocabulary build, and a JSON record
per line of standard input written straight back out.

Three properties make it usable as a co-process rather than only as a script:

* **It streams.** Records are read, answered and written one at a time and
  nothing accumulates, so memory is flat in the size of the corpus and a caller
  reading the pipe sees the first answer before the last question is asked.
* **Every record carries its input.** A caller correlates on the echoed
  ``input`` (and on ``id``, if their record supplied one) rather than on
  position, which is what lets them read the stream out of order or in parallel.
* **A bad record is a record, not an exit.** One malformed line reports its own
  failure and the run continues, because losing forty-nine thousand answers to
  one unparseable line is a worse outcome than any error message. The exit
  status still reports that something failed, so the command remains usable as
  a gate.

``governed-audit`` is the other half, and the first thing to run against a real
schema: it reduces the same corpus to one report — coverage, the ranked list of
tokens the catalog does not cover, compliance findings by reason code, and the
round trips that are neither stable nor a governed correction.

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

    ``check-name`` also exits ``1`` when the name it was given is not
    compliant. That is a finding, not a malfunction — the command ran and
    printed its verdict — and the status is what makes it usable as a step in
    somebody else's CI, where a report nobody can branch on is a log line.
    ``doctor --offline`` already sets the precedent.

    ``governed-batch`` exits ``1`` when any record failed, and
    ``governed-audit`` when any input line could not be read. Neither treats a
    *finding* that way: a name that does not comply is an answer the command was
    asked for, and a batch that exited non-zero because the schema it was handed
    is imperfect would be a gate on the wrong thing.
``2``
    Usage error — an unknown flag, a bad enum value, an unreadable
    ``--config``, ``--dictionary`` or ``--custom`` file, an inconsistent
    configuration, or the absence of ``click`` itself.

:func:`main` is total with respect to user error: it converts every expected
failure into one of those codes and never propagates an exception to the
interpreter.
"""

from __future__ import annotations

import errno
import json
import os
import sys
from contextlib import suppress
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterator,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from pydantic import ValidationError

from .config import Config
from .engine import AcronymEngine
from .enums import EngineTier, Language, ScoringStrategy
from .exceptions import AcronymKitError, LexiconError
from .models import (
    AcronymCandidate,
    AcronymResult,
    BackronymResult,
    ExtractionResult,
    ScoreBreakdown,
    Token,
)

if TYPE_CHECKING:
    # Governed naming is imported inside the callbacks that need it, the same
    # way ``doctor``, ``schema`` and ``version`` import theirs: a governed
    # command needs seven more Pydantic models, and ``acronymkit generate``
    # should not build their core schemas to find out it does not want them.
    # These are the annotations only.
    from .governed.audit import CatalogSuggestion
    from .governed.dictionary import GovernedDictionary
    from .governed.models import (
        ComplianceResult,
        GovernedEntry,
        IdentifierExpansion,
        PhysicalName,
        TokenExpansion,
    )
    from .governed.namer import GovernedNamer
    from .governed.policy import NamingPolicy

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

#: Values accepted by ``--policy``, each the name of a
#: :class:`~acronymkit.governed.policy.NamingPolicy` classmethod. Spelling them
#: as the constructor names rather than inventing CLI-flavoured aliases means
#: ``--policy frequency_baseline`` and ``NamingPolicy.frequency_baseline()``
#: cannot come to mean different things, and the list is resolved by
#: :func:`getattr` so there is one list rather than two.
_POLICY_PRESETS = (
    "governed_default",
    "frequency_baseline",
    "neural_optin",
    "strict_length",
)

#: Values accepted by ``--unknown``, each the value of a
#: :class:`~acronymkit.governed.enums.UnknownPolicy` member. Two of the three
#: members, and the omission is deliberate: ``neural`` behaves as passthrough in
#: this release, so offering it here would be a third spelling of a flag that
#: does nothing, and the preset that declares the opt-in — ``neural_optin`` —
#: already reaches it for a caller who wants the declaration on the record.
_UNKNOWN_OVERRIDES = ("passthrough_titlecase", "reject")

#: Values accepted by ``--dictionary-format``; see :func:`_governed_dictionary`
#: for what each one reads.
_DICTIONARY_LAYOUTS = (
    "auto",
    "bundle",
    "catalog",
    "short_to_long",
    "long_to_short",
    "csv",
    "long_to_short_csv",
)

#: The two layouts that read a CSV, mapped to what their ``--columns`` pair
#: names. The roles differ per layout because the *direction* differs, and the
#: message a caller who forgot the flag gets has to name the direction they
#: chose rather than "two columns".
_CSV_LAYOUTS: dict[str, tuple[str, str]] = {
    "csv": ("token", "long form"),
    "long_to_short_csv": ("long form", "token"),
}

#: How many column names ``--columns`` carries.
_COLUMN_COUNT = 2

#: Per-record operations ``governed-batch`` can apply, in the order the help
#: lists them. Each is one of the governed verbs, except ``audit``, which is the
#: audit module's per-identifier record.
_BATCH_OPS = ("expand", "physical", "check", "normalize", "audit")

#: Separators that make one batch record as small as it can be while staying
#: readable when a person pipes the stream through ``head``.
_JSONL_SEPARATORS = (",", ":")

#: Keys a ``--dictionary`` object may carry beside its entries, each named
#: exactly for the :class:`~acronymkit.governed.dictionary.GovernedDictionary`
#: keyword argument it supplies. A governed standard normally keeps these in
#: files of their own; the CLI has one flag for the vocabulary, so it reads
#: them from the one file and does nothing when they are absent.
_VOCABULARY_KEYS = (
    "approved_abbreviations",
    "common_keywords",
    "short_full_words",
    "class_words",
    "term_index",
)

#: Prefix marking a key as metadata rather than data, in every JSON file this
#: CLI reads. The governed fixtures use it for the ``_meta`` block a catalog
#: records itself in, and a token can never begin with it.
_METADATA_PREFIX = "_"

#: Hanging indent for the continuation lines of a compliance finding, sized to
#: put them under the token rather than under the verdict tag.
_FINDING_INDENT = " " * len("  [PASS] ")

#: Width of the example column in a suggestions table. The same value
#: ``render_audit`` uses for its own example columns, so the two tables a
#: ``governed-audit --suggest`` run prints line up with each other.
_EXAMPLE_WIDTH = 44

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


def _is_closed_consumer(exc: OSError) -> bool:
    """Whether an :class:`OSError` is "the process reading my output went away".

    ``acronymkit governed-batch ... | head -1`` is a normal thing to type, and it
    closes the pipe after one line. What reaches this library then depends on the
    platform, which is the whole reason this predicate exists rather than a bare
    ``except BrokenPipeError``:

    * POSIX raises :class:`BrokenPipeError`, whose ``errno`` is ``EPIPE``;
    * Windows has no ``SIGPIPE`` and no ``EPIPE`` on this path. The C runtime
      fails the write with ``EINVAL`` and CPython raises a plain
      :class:`OSError`, so a Windows consumer hanging up is indistinguishable at
      this level from any other invalid argument.

    That ambiguity is the honest limit of this function, and it is accepted in
    one direction only: on Windows an ``EINVAL`` escaping a command is read as a
    closed consumer, which means a genuine ``EINVAL`` from somewhere else would
    exit ``0`` instead of printing a traceback. Every other ``OSError``
    propagates untouched.

    Args:
        exc: The error that escaped the command.

    Returns:
        ``True`` when the downstream reader is gone.
    """
    if isinstance(exc, BrokenPipeError):
        return True
    return sys.platform == "win32" and exc.errno == errno.EINVAL


def _abandon_stdout() -> None:
    """Point standard output at the null device, discarding what is buffered.

    Returning ``EXIT_OK`` after a closed pipe is not enough on its own: the
    interpreter flushes ``sys.stdout`` on the way out, that flush fails against
    the same closed pipe, and Python prints "Exception ignored on flushing
    sys.stdout" and exits ``120`` — so the process reports a crash after the code
    decided it had not crashed. Re-pointing the file descriptor is the documented
    remedy and is what makes the exit status mean what it says.

    Silent on failure by design. ``sys.stdout`` may be a stream a test harness
    substituted, with no file descriptor to redirect; there is then nothing to
    detach and nothing that can fail at shutdown either.
    """
    with suppress(AttributeError, OSError, ValueError):
        descriptor = sys.stdout.fileno()
        null = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(null, descriptor)
        finally:
            os.close(null)


# ---------------------------------------------------------------------------
# governed vocabulary assembly
# ---------------------------------------------------------------------------
def _read_json_document(click: Any, flag: str, path: str) -> Any:
    """Load any JSON document from a file named by a command-line flag.

    Separate from :func:`_read_config_file`, which is specific to ``--config``
    and insists on an object: a governed catalog is legitimately either an
    object or a bare array, so the shape check belongs to whoever knows what
    was asked for.

    Args:
        click: The imported ``click`` module.
        flag: The flag the path came from, for the error message. A user who
            passed three file-valued flags needs to be told which one failed.
        path: Filesystem path to a UTF-8 JSON file.

    Returns:
        The decoded document: any JSON value.

    Raises:
        click.UsageError: If the file cannot be read, is not UTF-8, or is not
            valid JSON.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise click.UsageError(f"{flag} file '{path}' is not valid UTF-8: {exc}") from exc
    except OSError as exc:
        raise click.UsageError(f"could not read {flag} file '{path}': {exc}") from exc
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise click.UsageError(f"{flag} file '{path}' is not valid JSON: {exc}") from exc


def _read_json_argument(click: Any, flag: str, value: str) -> Any:
    """Decode a flag whose value is either inline JSON or a path to JSON.

    The rule is the first non-blank character: ``{`` or ``[`` means the value
    *is* the document, anything else means it names a file holding one. That is
    decidable rather than heuristic — no filesystem path begins with a brace,
    and no JSON object or array begins with anything else — so the two cases
    can never be confused for each other, and a caller never has to say which
    one they meant.

    Args:
        click: The imported ``click`` module.
        flag: The flag the value came from, for the error message.
        value: Inline JSON, or a path.

    Returns:
        The decoded document.

    Raises:
        click.UsageError: If inline JSON does not parse, or the named file
            cannot be read or does not parse.
    """
    text = value.strip()
    if text.startswith(("{", "[")):
        try:
            return json.loads(text)
        except ValueError as exc:
            raise click.UsageError(f"inline {flag} JSON is not valid: {exc}") from exc
    return _read_json_document(click, flag, value)


def _is_catalog_document(document: Any) -> bool:
    """Report whether a ``--dictionary`` document holds catalog rows.

    Args:
        document: The decoded ``--dictionary`` file.

    Returns:
        ``True`` for a bare array of rows, or for an object carrying them under
        ``"entries"`` — the two layouts
        :meth:`~acronymkit.governed.dictionary.GovernedDictionary.from_json`
        accepts. Anything else is treated as a plain token mapping.
    """
    if isinstance(document, list):
        return True
    return isinstance(document, dict) and isinstance(document.get("entries"), list)


def _vocabulary_arguments(document: Any) -> dict[str, Any]:
    """Collect the allow-lists, class words and glossary a catalog file carries.

    Args:
        document: The decoded ``--dictionary`` file.

    Returns:
        The subset of :data:`_VOCABULARY_KEYS` present and non-empty, ready to
        pass to the loader as keyword arguments. Empty for a bare array, and
        empty for an object that carries none of them — which is the ordinary
        case, and costs only the reason codes that distinguish one allow-list
        from another.
    """
    if not isinstance(document, dict):
        return {}
    return {key: document[key] for key in _VOCABULARY_KEYS if document.get(key)}


def _string_mapping(click: Any, flag: str, document: Any) -> dict[str, str]:
    """Read a JSON object of string-to-string pairs, skipping metadata keys.

    Args:
        click: The imported ``click`` module.
        flag: The flag the document came from, for the error message.
        document: The decoded document.

    Returns:
        The pairs, with :data:`_METADATA_PREFIX` keys dropped.

    Raises:
        click.UsageError: If the document is not an object, or any value is not
            a string. Reported rather than skipped: a mapping whose values are
            objects is far more likely to be a catalog passed with the wrong
            ``--dictionary-format`` than a file the caller wanted half of.
    """
    if not isinstance(document, dict):
        raise click.UsageError(
            f"{flag} must hold a JSON object mapping strings to strings, "
            f"got {type(document).__name__}"
        )
    pairs: dict[str, str] = {}
    for key, value in document.items():
        if key.startswith(_METADATA_PREFIX):
            continue
        if not isinstance(value, str):
            raise click.UsageError(
                f"{flag} entry '{key}' must be a string, got {type(value).__name__}"
            )
        pairs[key] = value
    return pairs


def _resolve_layout(click: Any, layout: str, source: Path) -> str:
    """Settle ``--dictionary-format auto`` as far as the path alone can settle it.

    Two of the five readers can be chosen from the path, and one of them must
    not be chosen at all:

    * a **directory** is always a bundle, because nothing else is a directory;
    * a **CSV** cannot be settled here, and the caller is told so rather than
      guessed at. A two-column CSV is a valid vocabulary read either way round,
      meaning different things, which is the same reason ``auto`` never picks
      ``long_to_short`` for a JSON mapping.

    Anything else is a JSON file, and which JSON layout it holds is decidable
    from the document rather than from its name, so it is left for
    :func:`_governed_dictionary` to settle after the read.

    Args:
        click: The imported ``click`` module.
        layout: The requested ``--dictionary-format``.
        source: The ``--dictionary`` path.

    Returns:
        The layout, still ``"auto"`` when only the document can decide.

    Raises:
        click.UsageError: If a CSV was passed with no direction declared, or if
            a directory was passed with a layout that reads a file.
    """
    if layout != "auto":
        if source.is_dir() and layout != "bundle":
            raise click.UsageError(
                f"--dictionary '{source!s}' is a directory, which is always a bundle, but "
                f"--dictionary-format says '{layout}'. Drop the flag, or pass "
                f"--dictionary-format bundle."
            )
        return layout
    if source.is_dir():
        return "bundle"
    if source.suffix.lower() == ".csv":
        raise click.UsageError(
            f"--dictionary '{source!s}' is a CSV, and which way round it reads cannot be "
            "decided by looking at it: the same two columns are a valid vocabulary read "
            "either way and mean different things. Pass --dictionary-format csv for "
            "token,long form, or long_to_short_csv for long form,token, with "
            "--columns naming the two headers."
        )
    return "auto"


def _dictionary_columns(click: Any, value: Optional[str], layout: str) -> tuple[str, str]:
    """Read the ``--columns`` pair a CSV layout needs, and refuse the rest.

    The loaders take the column names with **no defaults** on purpose — there is
    no conventional header for "the long form", and picking one would be this
    tool guessing about a file it has never seen — so the flag is required
    exactly when a CSV is being read and rejected when it is not, rather than
    quietly ignored.

    Args:
        click: The imported ``click`` module.
        value: The raw ``--columns`` value, ``"key,value"``.
        layout: The already-resolved layout.

    Returns:
        The two column names, stripped. Empty strings when the layout reads no
        CSV, which is the case in which they are never looked at.

    Raises:
        click.UsageError: If the flag is missing for a CSV layout, present for
            any other, or does not hold exactly two non-blank names.
    """
    roles = _CSV_LAYOUTS.get(layout)
    if roles is None:
        if value:
            raise click.UsageError(
                f"--columns names the two columns of a CSV catalog, and "
                f"--dictionary-format '{layout}' does not read one. Drop --columns, or pass "
                f"--dictionary-format csv or long_to_short_csv."
            )
        return ("", "")
    if not value:
        raise click.UsageError(
            f"--dictionary-format {layout} needs --columns '<{roles[0]}>,<{roles[1]}>' naming "
            f"the two headers of your file. There is no conventional name for either, so this "
            f"tool will not guess one."
        )
    names = [name.strip() for name in value.split(",")]
    if len(names) != _COLUMN_COUNT or not all(names):
        raise click.UsageError(
            f"--columns takes exactly two non-blank column names separated by a comma, as in "
            f"'--columns \"{roles[0]},{roles[1]}\"', not {value!r}. A header that itself "
            f"contains a comma cannot be named this way; use the Python loaders for that file."
        )
    return (names[0], names[1])


def _governed_dictionary(click: Any, options: dict[str, Any]) -> GovernedDictionary:
    """Load the governed vocabulary a command runs against.

    ``--dictionary-format`` chooses the reader:

    ``bundle``
        A directory holding a whole standard — catalog, allow-lists, class
        words, pin sheet and term glossary — or one JSON object carrying the
        same sections. See
        :func:`~acronymkit.governed.loaders.load_bundle` for the file names it
        accepts and how the pin sheet is merged.
    ``catalog``
        Full :class:`~acronymkit.governed.models.GovernedEntry` rows, as a bare
        array or under an ``"entries"`` key. Keys listed in
        :data:`_VOCABULARY_KEYS` are read from the same object when present.
    ``short_to_long``
        ``{"TXN": "Transaction"}`` — the smallest useful vocabulary, and the
        one to reach for when trying a command out.
    ``long_to_short``
        ``{"Transaction": "TXN"}`` — the direction a real catalog is stored in,
        and the reason this flag exists at all. Inverting it produces the
        collisions ``canonical_form_score`` then settles, so it cannot be
        detected by inspection: the same file is a valid vocabulary read either
        way round, meaning different things. It has to be declared.
    ``csv`` / ``long_to_short_csv``
        The same two directions, read from a spreadsheet export with
        ``--columns`` naming the two headers and ``--delimiter`` its separator.
        This is the shape a governance function's standard actually arrives in.
    ``auto`` (the default)
        ``bundle`` for a directory; ``catalog`` when the document is one of the
        two catalog layouts; ``short_to_long`` otherwise. Never
        ``long_to_short``, and never a CSV layout, for the reason above.

    Args:
        click: The imported ``click`` module.
        options: The command callback's keyword arguments.

    Returns:
        The indexed vocabulary, with no overlay layered — ``--custom`` is
        passed to the verb instead, so that it is a call-time overlay and
        ``--policy`` can still refuse it.

    Raises:
        click.UsageError: If the file is unreadable, is not JSON, does not hold
            the declared layout, or holds a malformed row.
    """
    from .governed.dictionary import GovernedDictionary

    path = str(options["dictionary_path"])
    source = Path(path)
    layout = _resolve_layout(click, str(options.get("dictionary_format") or "auto"), source)
    columns = _dictionary_columns(click, options.get("columns"), layout)
    delimiter = str(options.get("delimiter") or ",")
    if layout in _CSV_LAYOUTS or layout == "bundle":
        return _load_governed_file(click, path, layout, columns, delimiter)

    document = _read_json_document(click, "--dictionary", path)
    if layout == "auto":
        layout = "catalog" if _is_catalog_document(document) else "short_to_long"
    try:
        if layout == "catalog":
            return GovernedDictionary.from_json(document, **_vocabulary_arguments(document))
        mapping = _string_mapping(click, "--dictionary", document)
        if layout == "short_to_long":
            return GovernedDictionary.from_mapping(mapping)
        return GovernedDictionary.from_long_to_short(mapping)
    except LexiconError as exc:
        raise click.UsageError(f"--dictionary file '{path}': {exc}") from exc


def _load_governed_file(
    click: Any, path: str, layout: str, columns: tuple[str, str], delimiter: str
) -> GovernedDictionary:
    """Run one of the loaders that reads its own file, rather than a JSON document.

    Separate from :func:`_governed_dictionary` because these three readers open
    the path themselves — a bundle is a directory of files and a CSV is not JSON
    — so the "decode the document, then decide" shape the JSON layouts share
    does not apply to them.

    Args:
        click: The imported ``click`` module.
        path: The ``--dictionary`` path.
        layout: ``"bundle"``, ``"csv"`` or ``"long_to_short_csv"``.
        columns: The ``--columns`` pair, unused by ``bundle``.
        delimiter: The CSV field separator, unused by ``bundle``.

    Returns:
        The indexed vocabulary.

    Raises:
        click.UsageError: Carrying whatever the loader refused, which already
            names the file and the column.
    """
    from .governed.loaders import load_bundle, load_csv, load_long_to_short_csv

    try:
        if layout == "bundle":
            return load_bundle(path)
        if layout == "csv":
            return load_csv(
                path,
                token_column=columns[0],
                canonical_column=columns[1],
                delimiter=delimiter,
            )
        return load_long_to_short_csv(
            path,
            long_column=columns[0],
            short_column=columns[1],
            delimiter=delimiter,
        )
    except LexiconError as exc:
        raise click.UsageError(f"--dictionary '{path}': {exc}") from exc


def _governed_overlay(
    click: Any, value: Optional[str]
) -> Optional[Mapping[str, Union[str, GovernedEntry]]]:
    """Decode ``--custom`` into an overlay the governed verbs accept.

    Two value shapes, matching what the library takes: a bare string is the
    long form and nothing more, and an object is a whole
    :class:`~acronymkit.governed.models.GovernedEntry`, so an overlay can carry
    its own provenance handle, confidence and kind rather than borrowing the
    catalog's.

    An entry object may leave out ``token`` and ``source``, which are otherwise
    required fields. Both are filled in here — ``token`` from the mapping key,
    ``source`` as ``custom`` — because
    :class:`~acronymkit.governed.dictionary.GovernedDictionary` rewrites both to
    exactly those values on the way in whatever the caller wrote. Demanding
    that a caller type a field whose value is discarded teaches them that the
    field means something, and it does not. Nothing else is defaulted: the
    entry still has to say what it means (``canonical``) and what kind of record
    it is (``kind``), and inventing either would be this CLI making up a
    provenance.

    Args:
        click: The imported ``click`` module.
        value: The raw ``--custom`` value: inline JSON or a path. ``None`` or
            empty when the flag was not given.

    Returns:
        The overlay, or ``None`` when there is nothing to layer.

    Raises:
        click.UsageError: If the value does not decode, is not an object, or
            holds a value that is neither a string nor a usable entry.
    """
    if not value:
        return None
    from .governed.models import GovernedEntry

    document = _read_json_argument(click, "--custom", value)
    if not isinstance(document, dict):
        raise click.UsageError(
            f"--custom must hold a JSON object of token to long form or entry, "
            f"got {type(document).__name__}"
        )
    overlay: dict[str, Union[str, GovernedEntry]] = {}
    for token, supplied in document.items():
        if token.startswith(_METADATA_PREFIX):
            continue
        if isinstance(supplied, str):
            overlay[token] = supplied
        elif isinstance(supplied, dict):
            fields = {"token": token, "source": "custom", **supplied}
            try:
                overlay[token] = GovernedEntry(**fields)
            except ValidationError as exc:
                raise click.UsageError(
                    f"--custom entry '{token}' is not a valid governed entry: "
                    f"{_format_validation_error(exc)}"
                ) from exc
        else:
            raise click.UsageError(
                f"--custom entry '{token}' must be a string or an object, "
                f"got {type(supplied).__name__}"
            )
    return overlay


def _governed_policy(name: str, unknown: Optional[str] = None) -> NamingPolicy:
    """Return the named :class:`~acronymkit.governed.policy.NamingPolicy` preset.

    ``unknown`` is the one field of the preset a command line may change, and it
    is a field rather than a fifth preset because "reject unknown tokens" is
    orthogonal to every other choice the four presets express: a caller who
    wants a stale catalog to stop their pipeline wants it under whichever
    preset they were already running.

    ``None`` means the preset's own value stands. That matters more than a
    default usually does — ``neural_optin`` is the only preset that sets
    ``unknown`` to anything else, and a flag defaulting to
    ``passthrough_titlecase`` would silently undo the opt-in for every caller
    who never typed the flag.

    Args:
        name: One of :data:`_POLICY_PRESETS`, which are the classmethod names
            themselves. ``click.Choice`` has already rejected anything else, so
            the lookup cannot miss.
        unknown: One of :data:`_UNKNOWN_OVERRIDES`, or ``None`` to leave the
            preset alone.

    Returns:
        The policy the preset constructs, or a copy of it carrying the
        requested ``unknown`` handling. The presets are memoised and frozen, so
        the copy is what keeps an override from reaching the next caller.
    """
    from .governed.enums import UnknownPolicy
    from .governed.policy import NamingPolicy

    constructor: Callable[[], NamingPolicy] = getattr(NamingPolicy, name)
    policy = constructor()
    if unknown is None:
        return policy
    return policy.model_copy(update={"unknown": UnknownPolicy(unknown)})


def _governed_context(
    click: Any, options: dict[str, Any]
) -> tuple[GovernedDictionary, NamingPolicy, Optional[Mapping[str, Union[str, GovernedEntry]]]]:
    """Assemble the three arguments every governed verb takes.

    Args:
        click: The imported ``click`` module.
        options: The command callback's keyword arguments.

    Returns:
        ``(dictionary, policy, custom)``, in the order the verbs take them.

    Raises:
        click.UsageError: If ``--dictionary`` or ``--custom`` is unusable.
    """
    unknown = options.get("unknown")
    return (
        _governed_dictionary(click, options),
        _governed_policy(str(options["policy_name"]), None if unknown is None else str(unknown)),
        _governed_overlay(click, options.get("custom")),
    )


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


def _labelled(pairs: Sequence[tuple[str, str]]) -> list[str]:
    """Lay out ``label: value`` lines with the values in one column.

    The single-record counterpart to :func:`_table`, used where a command
    reports one thing rather than a list of them.

    Args:
        pairs: ``(label, value)`` in display order. Labels are written without
            their colon.

    Returns:
        One line per pair, trailing whitespace stripped.
    """
    width = max((len(label) for label, _ in pairs), default=0)
    return [f"{label + ':':<{width + 1}} {value}".rstrip() for label, value in pairs]


def _optional(value: Optional[str]) -> str:
    """Render an optional string, showing an absent one as ``'-'``."""
    return value if value else "-"


def _clip(text: str, width: int) -> str:
    """Shorten ``text`` to ``width`` characters, marking that it was shortened.

    Args:
        text: The text to fit.
        width: The column width, at least four.

    Returns:
        The text, or its head followed by an ellipsis.
    """
    return text if len(text) <= width else text[: width - 3] + "..."


def _render_token_expansion(expansion: TokenExpansion) -> list[str]:
    """Render one token's governed expansion, provenance included.

    Every field the DTO carries is shown, including the ones that are usually
    empty. A governed answer is only worth having if the reader can see what
    produced it, and a field that disappears when it is empty makes "there was
    nothing to beat" indistinguishable from "the renderer dropped it".

    Args:
        expansion: The verb's result.

    Returns:
        The lines to print.
    """
    return _labelled(
        [
            ("Token", expansion.raw),
            ("Expansion", expansion.long or "-"),
            ("Known", _yes_no(expansion.is_known)),
            ("Source", expansion.source.value),
            ("Kind", expansion.kind.value if expansion.kind else "-"),
            ("Entry", _optional(expansion.entry_id)),
            ("Confidence", f"{expansion.confidence:.2f}"),
            ("Class word", _optional(expansion.class_word)),
            ("Beat", ", ".join(expansion.beat) or "-"),
        ]
    )


def _render_identifier_expansion(expansion: IdentifierExpansion) -> list[str]:
    """Render a whole identifier's expansion as a header plus a token table.

    Args:
        expansion: The verb's result.

    ``Unaccounted`` is printed even when it is empty, and it is what makes
    ``Fully known: no`` legible on an identifier whose tokens all resolved: a
    character the splitter could not account for is the other half of that flag,
    and a reader who cannot see it has been told a name failed without being
    told what failed.

    Returns:
        The lines to print. An identifier that tokenises to nothing gets the
        header and an explanatory line, not an empty table.
    """
    lines = _labelled(
        [
            ("Identifier", expansion.identifier),
            ("Phrase", expansion.phrase or "-"),
            ("Class word", _optional(expansion.class_word)),
            ("Fully known", _yes_no(expansion.is_fully_known)),
            ("Unaccounted", " ".join(expansion.unaccounted) or "-"),
        ]
    )
    if not expansion.tokens:
        return [*lines, "", "No tokens."]
    rows = [
        [
            token.raw,
            token.long or "-",
            _yes_no(token.is_known),
            token.source.value,
            f"{token.confidence:.2f}",
            _optional(token.entry_id),
            ", ".join(token.beat) or "-",
        ]
        for token in expansion.tokens
    ]
    lines.append("")
    lines.extend(
        _table(["TOKEN", "EXPANSION", "KNOWN", "SOURCE", "CONF", "ENTRY", "BEAT"], rows, (4,))
    )
    return lines


def _render_physical_name(name: PhysicalName) -> list[str]:
    """Render a governed physical name and the word-by-word trail behind it.

    ``Truncated`` is printed even though it is always ``no``. The invariant is
    that no policy shortens a name, and an invariant a reader can see asserted
    in the output is worth more than one they have to take on trust.

    Args:
        name: The verb's result.

    Returns:
        The lines to print.
    """
    lines = _labelled(
        [
            ("Logical", name.logical),
            ("Physical", name.physical or "-"),
            ("Term id", _optional(name.term_id)),
            ("Confidence", f"{name.confidence:.2f}"),
            ("Truncated", _yes_no(name.truncated)),
        ]
    )
    if not name.tokens:
        return [*lines, "", "No words."]
    rows = [
        [token.word, token.abbrev, token.source.value, _optional(token.entry_id)]
        for token in name.tokens
    ]
    lines.append("")
    lines.extend(_table(["WORD", "ABBREV", "SOURCE", "ENTRY"], rows, ()))
    return lines


def _render_compliance(result: ComplianceResult) -> list[str]:
    """Render a compliance verdict and every finding that produced it.

    Findings are laid out one block each rather than as table rows because the
    detail sentence and the suggested fix are prose of unbounded length, and a
    column wide enough for the longest of them would push the token out of
    sight on the rows where nothing is wrong.

    Args:
        result: The verb's result.

    Returns:
        The lines to print.
    """
    lines = _labelled(
        [
            ("Name", result.name),
            ("Compliant", _yes_no(result.compliant)),
            ("Ends in class word", _yes_no(result.ends_in_class_word)),
            ("Class word", _optional(result.class_word)),
        ]
    )
    if not result.reasons:
        return [*lines, "", "No findings."]
    lines.extend(["", "Findings:"])
    for reason in result.reasons:
        subject = reason.token if reason.token is not None else "<name>"
        lines.append(f"  [{reason.verdict.value.upper()}] {subject}: {reason.code.value}")
        lines.append(f"{_FINDING_INDENT}{reason.detail}")
        if reason.fix:
            lines.append(f"{_FINDING_INDENT}fix: {reason.fix}")
    return lines


def _render_suggestions(suggestions: Sequence[CatalogSuggestion]) -> list[str]:
    """Render the catalog backlog an audit produced as a work list.

    Most rows carry no proposed wording, and that is the honest outcome rather
    than a rendering failure: a suggestion is a request for a decision from
    whoever owns the catalog, and this library fills the wording in only where
    the catalog itself already supplies it. So the two proposal columns are
    printed only when some row has something to put in them, on the same
    reasoning ``render_audit`` uses for its own optional column — a column of
    dashes reads as a column that failed to fill rather than as one that had
    nothing to say.

    Args:
        suggestions: The ranked suggestions.

    Returns:
        The lines to print, headed by a count.
    """
    if not suggestions:
        return ["Catalog suggestions", "  none: the vocabulary covered every token in the corpus"]
    proposed = any(item.proposed_abbreviation for item in suggestions)
    headers = ["OCC", "IDS", "TOKEN"]
    if proposed:
        headers.extend(["WRITE", "MEANING"])
    headers.append("EXAMPLE")
    rows = [
        [
            str(item.occurrences),
            str(item.identifier_count),
            item.token,
            *(
                [_optional(item.proposed_abbreviation), _optional(item.proposed_long_form)]
                if proposed
                else []
            ),
            _clip(item.examples[0] if item.examples else "-", _EXAMPLE_WIDTH),
        ]
        for item in suggestions
    ]
    lines = [f"Catalog suggestions ({len(suggestions)})", ""]
    lines.extend(_table(headers, rows, (0, 1)))
    if proposed:
        lines.extend(
            [
                "",
                "A row with a WRITE column needs no decision, only an edit: the catalog "
                "already governs that word.",
            ]
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
# streaming batch mode
# ---------------------------------------------------------------------------
def _governed_namer(click: Any, options: dict[str, Any]) -> GovernedNamer:
    """Bind the vocabulary, policy and overlay once for a whole run.

    The per-name commands pass the three arguments to the verb on every call,
    which is right for one call. A batch makes tens of thousands, and repeating
    the overlay layering per name would be the same work done per record instead
    of per process — so the batch commands use the facade, which layers it once
    and holds it.

    Args:
        click: The imported ``click`` module.
        options: The command callback's keyword arguments.

    Returns:
        A :class:`~acronymkit.governed.namer.GovernedNamer` over the requested
        vocabulary and policy.

    Raises:
        click.UsageError: If ``--dictionary`` or ``--custom`` is unusable.
    """
    from .governed.namer import GovernedNamer

    dictionary, policy, custom = _governed_context(click, options)
    return GovernedNamer(dictionary, policy, custom=custom)


def _batch_stream(click: Any, source: Optional[str]) -> tuple[Any, bool]:
    """Open the record stream, without reading any of it.

    Decoding is pinned to UTF-8 with undecodable bytes replaced rather than
    raising, on both paths and deliberately. A batch is fed by another process
    on the far side of a pipe, where the encoding is whatever that process
    writes and the console code page is irrelevant; and a single bad byte in the
    middle of a fifty-thousand-line export must cost the record it is in, not
    the run. The replacement character reaches the output on that record's
    ``input``, so the damage is visible rather than silent.

    Args:
        click: The imported ``click`` module.
        source: A path, ``"-"`` for standard input, or ``None`` to use standard
            input when it is not a terminal.

    Returns:
        ``(stream, close_it)`` — the second is ``True`` only for a file this
        function opened, because closing the caller's standard input would be a
        surprise.

    Raises:
        click.UsageError: If no source was given and standard input is a
            terminal, or the named file cannot be opened.
    """
    if source is None:
        if _stdin_is_tty():
            raise click.UsageError(
                "no FILE given and stdin is a terminal; pass a path, pass '-', "
                "or pipe the records in"
            )
        source = "-"
    if source == "-":
        stream = sys.stdin
        if stream is None:  # pragma: no cover - detached interpreter
            raise click.UsageError("stdin is not available to read from")
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            # A stream a test harness or an embedding process substituted may
            # refuse; the run is still correct, it just decodes the way that
            # stream was already set up to.
            with suppress(AttributeError, ValueError, OSError):
                reconfigure(encoding="utf-8", errors="replace")
        return stream, False
    try:
        return Path(source).open(encoding="utf-8-sig", errors="replace"), True
    except OSError as exc:
        raise click.UsageError(f"could not read '{source}': {exc}") from exc


def _batch_subject(text: str) -> tuple[Optional[str], Any, Optional[str]]:
    """Read one input line as a subject, and a correlation key if it carried one.

    Two line shapes are accepted and the rule between them is decidable rather
    than heuristic: a line whose first non-blank character is ``{`` is a JSON
    object, and anything else is the subject itself. No physical name begins
    with a brace, so the two cannot be confused, and a caller with nothing but a
    column list never has to learn the JSON form at all.

    The object form exists for one reason — a caller who needs their own key
    echoed back. ``id`` is round-tripped untouched onto the answer, so a Java
    pipeline holding a row id can join the stream back onto its rows without
    trusting the order it read them in.

    Args:
        text: The line, already stripped of surrounding whitespace and known
            to be non-blank.

    Returns:
        ``(subject, id, problem)``. Exactly one of ``subject`` and ``problem``
        is ``None``.
    """
    if not text.startswith("{"):
        return text, None, None
    try:
        payload = json.loads(text)
    except ValueError as exc:
        return None, None, f"line is not valid JSON: {exc}"
    if not isinstance(payload, dict):
        return (
            None,
            None,
            f"a JSON record must be an object carrying 'identifier', got {type(payload).__name__}",
        )
    identity = payload.get("id")
    if identity is not None and not isinstance(identity, (str, int, float, bool)):
        return (
            None,
            None,
            f"'id' is echoed back onto the answer, so it must be a string, a number or a "
            f"boolean, not {type(identity).__name__}",
        )
    subject = payload.get("identifier")
    if not isinstance(subject, str):
        found = "absent" if "identifier" not in payload else type(subject).__name__
        return (
            None,
            identity,
            f"a JSON record must carry a string 'identifier'; it is {found}. A line that is "
            f"not a JSON object is read as the identifier itself.",
        )
    return subject, identity, None


def _batch_operation(op: str, namer: GovernedNamer) -> Callable[[str], dict[str, Any]]:
    """Return the function one batch record's ``result`` comes from.

    Resolved once per run rather than per record, so the import and the branch
    are paid for by the process rather than by the corpus.

    ``audit`` is the one entry that is not a verb: it runs
    :func:`~acronymkit.governed.audit.audit_identifiers` over the single name
    and returns the per-identifier record, which is the shape a governance
    pipeline writes into its findings table — known, compliant, which tokens
    are missing, which reason codes fired, and what the governed form would be.
    It costs four verb calls and a small pile of model construction per record,
    where ``expand`` costs one, and it is opt-in for that reason.

    Args:
        op: One of :data:`_BATCH_OPS`; ``click.Choice`` has already rejected
            anything else.
        namer: The bound vocabulary and policy.

    Returns:
        A callable taking the record's subject and returning its JSON payload.
    """
    if op == "expand":
        return lambda subject: namer.expand_identifier(subject).to_dict()
    if op == "physical":
        return lambda subject: namer.to_physical_name(subject).to_dict()
    if op == "check":
        return lambda subject: namer.is_compliant(subject).to_dict()
    if op == "normalize":
        return lambda subject: {"name": subject, "normalized": namer.normalize(subject)}

    from .governed.audit import IdentifierAudit, audit_identifiers

    def audit_one(subject: str) -> dict[str, Any]:
        """Audit one name, filling in the record the audit keeps only when notable."""
        audit = audit_identifiers((subject,), namer.dictionary, namer.policy, max_examples=0)
        if audit.details:
            return audit.details[0].to_dict()
        # An identifier the audit had nothing to say about keeps no detail
        # record, and a batch owes an answer for every line. The two flags are
        # read off the audit's own counts rather than assumed, so this branch
        # cannot come to disagree with the module that produced them.
        return IdentifierAudit(
            identifier=subject,
            occurrences=1,
            is_fully_known=bool(audit.fully_known),
            compliant=bool(audit.compliant),
        ).to_dict()

    return audit_one


def _run_batch(
    op: str, namer: GovernedNamer, stream: Any, flush_every: int
) -> tuple[int, int, int, bool]:
    """Read the stream, answer each record, write each answer, keep nothing.

    The loop holds one record at a time. Nothing accumulates — not the inputs,
    not the answers, not a cache keyed on the identifier — so memory is flat in
    the size of the corpus and a fifty-thousand-column schema costs what a
    hundred-column one does.

    Every exception a record raises is caught and reported *on that record*.
    That includes the ones this library does not expect: a
    :class:`~acronymkit.exceptions.LexiconError` from a policy that rejects
    unknown tokens is a documented outcome, and anything else is a bug — but the
    right response to a bug on record 812 is still to answer the other 49,999
    and put the type on the record, rather than to lose the run. The exit status
    reports that something failed; ``error_type`` says what.

    Args:
        op: The operation name.
        namer: The bound vocabulary and policy.
        stream: An iterable of lines.
        flush_every: Flush standard output after this many records; ``0`` leaves
            flushing to the interpreter's buffer, which is faster and is wrong
            for a caller reading the pipe as it goes.

    Returns:
        ``(records, failed, skipped)`` — records written, of those how many
        carry an error, and blank lines passed over.
    """
    apply = _batch_operation(op, namer)
    out = sys.stdout
    records = failed = skipped = 0
    for number, line in enumerate(stream, start=1):
        text = line.strip()
        if not text:
            skipped += 1
            continue
        subject, identity, problem = _batch_subject(text)
        record: dict[str, Any] = {"line": number}
        if identity is not None:
            record["id"] = identity
        record["input"] = text if subject is None else subject
        if problem is not None or subject is None:
            record["ok"] = False
            record["error"] = problem or "the line could not be read"
            record["error_type"] = "InputError"
            failed += 1
        else:
            try:
                result = apply(subject)
            except Exception as exc:  # one bad record must not end the run
                record["ok"] = False
                record["error"] = str(exc) or type(exc).__name__
                record["error_type"] = type(exc).__name__
                failed += 1
            else:
                record["ok"] = True
                record["result"] = result
        records += 1
        try:
            out.write(json.dumps(record, ensure_ascii=True, separators=_JSONL_SEPARATORS))
            out.write("\n")
            if flush_every and records % flush_every == 0:
                out.flush()
        except OSError as exc:
            # The consumer stopped reading -- ``| head -1`` on a streaming
            # command. Handled *here* rather than by letting it reach
            # :func:`main`, because ``click`` intercepts ``EPIPE`` inside its
            # own ``main()`` and turns it into ``sys.exit(1)`` before our
            # handler can run: the process would report a failure for the most
            # ordinary way there is to use this command.
            #
            # Windows raises ``EINVAL`` rather than ``EPIPE`` for the same
            # event, so click's check does not match it there and the exception
            # did reach our handler. That is precisely why this was invisible
            # on the machine it was written on and failed on every POSIX cell
            # in CI: the platform difference hid the design mistake.
            if not _is_closed_consumer(exc):
                raise
            _abandon_stdout()
            return records, failed, skipped, True
    try:
        out.flush()
    except OSError as exc:
        if not _is_closed_consumer(exc):
            raise
        _abandon_stdout()
        return records, failed, skipped, True
    return records, failed, skipped, False


def _batch_identifiers(stream: Any, problems: list[str]) -> Iterator[str]:
    """Yield the subject of every readable line, recording the ones that are not.

    The reading half of :func:`_run_batch` without the answering half, for
    ``governed-audit``, which consumes a corpus rather than answering it record
    by record. A generator rather than a list, because
    :func:`~acronymkit.governed.audit.audit_identifiers` consumes its argument
    exactly once and a schema export should not be held in memory to be counted.

    Args:
        stream: An iterable of lines.
        problems: Collects one message per unreadable line, in file order. The
            audit is over the lines that could be read, and the caller reports
            how many could not.

    Yields:
        One subject per readable non-blank line.
    """
    for number, line in enumerate(stream, start=1):
        text = line.strip()
        if not text:
            continue
        subject, _, problem = _batch_subject(text)
        if subject is None:
            problems.append(f"line {number}: {problem}")
            continue
        yield subject


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


def _vocabulary_options(click: Any) -> Callable[[_Decorator], _Decorator]:
    """Build the decorator naming the vocabulary a governed command runs against.

    ``--dictionary`` is required rather than defaulted, and there is no bundled
    vocabulary to fall back on. A governed verb answers "what does the standard
    say", and a standard the caller did not supply is one this library would be
    making up — which is the single thing the subsystem exists not to do. It
    accepts a directory as well as a file, because a standard is five files and
    a flag that took only one of them would send every caller back to writing
    the merge script :func:`~acronymkit.governed.loaders.load_bundle` exists to
    delete.

    ``--policy`` names one of the four presets rather than exposing the nine
    fields behind them, because a named policy is auditable and a loose bag of
    booleans is not: "this job runs under ``governed_default``" is a reviewable
    sentence, and ``--allow-override/--no-allow-override --mode most_common``
    scattered across a crontab is not. Callers who need a field combination the
    presets do not cover have the Python API.

    ``--unknown`` is the one exception, and it is one because no preset sets
    ``UnknownPolicy.REJECT`` and refusing an unrecognised token is exactly the
    governed use case: a pipeline whose catalog has gone stale should stop
    rather than carry on under a name nobody approved. It overrides the
    resolved policy's ``unknown`` field and changes nothing else, so the
    reviewable sentence survives — "``governed_default``, rejecting unknown
    tokens" still names what ran. Omitted, the preset's own value stands.

    What it reaches is worth stating, because it is not every command.
    ``expand-token``, ``expand-identifier`` and ``governed-batch`` under
    ``--op expand`` raise on the first unrecognised token; ``check-name``,
    ``normalize-name`` and ``physical-name`` do not consult the field at all,
    because reporting an unapproved token *is* their answer. ``governed-audit``
    refuses the combination outright, with a message saying so: listing the
    tokens a catalog is silent about is what an audit is for, and a policy that
    stops at the first one answers a question nobody asked.

    Separate from :func:`_governed_options` because the batch commands take
    these seven options and not the ``--format``/``--indent`` pair: their output
    format is one JSON object per line and is not a choice.

    Args:
        click: The imported ``click`` module.

    Returns:
        A decorator applying the seven vocabulary options to a command callback.
    """
    options = [
        click.option(
            "--dictionary",
            "dictionary_path",
            required=True,
            type=click.Path(exists=True, dir_okay=True, readable=True),
            help="The governed vocabulary: a bundle directory, a JSON catalog, or a CSV. Required.",
        ),
        click.option(
            "--dictionary-format",
            "dictionary_format",
            type=click.Choice(_DICTIONARY_LAYOUTS),
            default="auto",
            show_default=True,
            help="How to read --dictionary: a whole bundle, full catalog rows, a token->long "
            "form mapping, a long form->token mapping to invert, or either direction as a CSV. "
            "'auto' takes a directory as a bundle and never guesses a direction.",
        ),
        click.option(
            "--columns",
            "columns",
            default=None,
            help="The two CSV headers, 'key,value', in the direction --dictionary-format "
            "names. Required for csv and long_to_short_csv, rejected otherwise.",
        ),
        click.option(
            "--delimiter",
            "delimiter",
            default=",",
            show_default=True,
            help="Field separator for a CSV --dictionary.",
        ),
        click.option(
            "--custom",
            "custom",
            default=None,
            help="Caller-supplied acronyms layered above the catalog, as inline JSON "
            '(\'{"XYZ": "Exchange"}\') or a path to a JSON file. Values may be a long form '
            "or a whole governed entry.",
        ),
        click.option(
            "--policy",
            "policy_name",
            type=click.Choice(_POLICY_PRESETS),
            default="governed_default",
            show_default=True,
            help="Named NamingPolicy preset to resolve under.",
        ),
        click.option(
            "--unknown",
            "unknown",
            type=click.Choice(_UNKNOWN_OVERRIDES),
            default=None,
            help="Override how the chosen --policy handles a token the vocabulary does not "
            "contain: pass it through Title Cased and marked unknown, or reject it as a "
            "LexiconError. Omitted, the preset decides.",
        ),
    ]

    def decorate(func: _Decorator) -> _Decorator:
        for option in reversed(options):
            func = option(func)
        return func

    return decorate


def _governed_options(click: Any) -> Callable[[_Decorator], _Decorator]:
    """Build the decorator carrying the options every per-name governed command takes.

    Args:
        click: The imported ``click`` module.

    Returns:
        A decorator applying the vocabulary options, then ``--format`` and
        ``--indent``, to a command callback.
    """
    vocabulary = _vocabulary_options(click)
    output = _output_options(click)

    def decorate(func: _Decorator) -> _Decorator:
        return vocabulary(output(func))

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
    governed_options = _governed_options(click)
    vocabulary_options = _vocabulary_options(click)

    @click.group(
        context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 100},
        help="Generate, extract and disambiguate acronyms, and expand identifiers "
        "against a governed vocabulary.",
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

    @group.command(
        "expand-token",
        help="Expand one governed TOKEN against the vocabulary in --dictionary.",
    )
    @click.argument("token")
    @governed_options
    def expand_token_command(token: str, **options: Any) -> None:
        """Expand a single token, with the provenance of the answer.

        Args:
            token: The short form to expand, matched case-insensitively.
            **options: The shared governed and output options.

        Raises:
            click.UsageError: If ``--dictionary`` or ``--custom`` is unusable.
            LexiconError: If the policy is ``UnknownPolicy.REJECT`` and the
                vocabulary does not contain the token.
        """
        from .governed.expansion import expand_token

        dictionary, policy, custom = _governed_context(click, options)
        expansion = expand_token(token, dictionary, policy, custom=custom)
        if options["output_format"] == "json":
            _emit_json(click, expansion.to_dict(), options["indent"])
        else:
            _emit(click, _render_token_expansion(expansion))

    @group.command(
        "expand-identifier",
        help="Expand a whole IDENTIFIER (TXN_APPLNT_ID) token by token.",
    )
    @click.argument("identifier")
    @governed_options
    def expand_identifier_command(identifier: str, **options: Any) -> None:
        """Expand an identifier into a readable phrase, token by token.

        Args:
            identifier: The column or field name to expand.
            **options: The shared governed and output options.

        Raises:
            click.UsageError: If ``--dictionary`` or ``--custom`` is unusable.
            LexiconError: If the policy is ``UnknownPolicy.REJECT`` and any
                token is not in the vocabulary.
        """
        from .governed.expansion import expand_identifier

        dictionary, policy, custom = _governed_context(click, options)
        expansion = expand_identifier(identifier, dictionary, policy, custom=custom)
        if options["output_format"] == "json":
            _emit_json(click, expansion.to_dict(), options["indent"])
        else:
            _emit(click, _render_identifier_expansion(expansion))

    @group.command(
        "physical-name",
        help="Render LOGICAL ('Applicant Birth Date') as the governed physical name.",
    )
    @click.argument("logical")
    @governed_options
    def physical_name_command(logical: str, **options: Any) -> None:
        """The reverse direction: logical name in, governed physical name out.

        Args:
            logical: The logical name to abbreviate.
            **options: The shared governed and output options.

        Raises:
            click.UsageError: If ``--dictionary`` or ``--custom`` is unusable.
        """
        from .governed.naming import to_physical_name

        dictionary, policy, custom = _governed_context(click, options)
        rendered = to_physical_name(logical, dictionary, policy, custom=custom)
        if options["output_format"] == "json":
            _emit_json(click, rendered.to_dict(), options["indent"])
        else:
            _emit(click, _render_physical_name(rendered))

    @group.command(
        "normalize-name",
        help="Rewrite NAME into the governed form, applying only corrections the catalog names.",
    )
    @click.argument("name")
    @governed_options
    def normalize_name_command(name: str, **options: Any) -> None:
        """Print the governed rewrite of a physical name.

        The text form prints the rewritten name alone, with no label, because
        the name is the whole answer and this is the command that ends up on
        the left of a pipe. Everything else about the rewrite — which token
        changed and why — is what ``check-name`` reports.

        Passing this is not the same as being compliant: ``normalize`` applies
        the corrections the catalog can justify, and appends no class word,
        because appending one is documented as ``to_physical_name`` behaviour.

        Args:
            name: The physical name to rewrite.
            **options: The shared governed and output options.

        Raises:
            click.UsageError: If ``--dictionary`` or ``--custom`` is unusable.
        """
        from .governed.compliance import normalize

        dictionary, policy, custom = _governed_context(click, options)
        normalized = normalize(name, dictionary, policy, custom=custom)
        if options["output_format"] == "json":
            _emit_json(click, {"name": name, "normalized": normalized}, options["indent"])
        else:
            _emit(click, [normalized])

    @group.command(
        "check-name",
        help="Check NAME against the governed standard; exit 1 when it does not conform.",
    )
    @click.argument("name")
    @governed_options
    def check_name_command(name: str, **options: Any) -> None:
        """Report a per-token compliance verdict, and set the exit status from it.

        Built to be a step in somebody else's pipeline, which is why the status
        carries the verdict: a non-compliant name exits :data:`EXIT_FAILURE`
        after printing every finding, so a schema review can run this over a
        list of column names and fail the build on the ones that do not
        conform. ``doctor --offline`` works the same way.

        Args:
            name: The physical name to check.
            **options: The shared governed and output options.

        Raises:
            click.UsageError: If ``--dictionary`` or ``--custom`` is unusable.
            SystemExit: With :data:`EXIT_FAILURE` when the name is not
                compliant. The output is printed first.
        """
        from .governed.compliance import is_compliant

        dictionary, policy, custom = _governed_context(click, options)
        result = is_compliant(name, dictionary, policy, custom=custom)
        if options["output_format"] == "json":
            _emit_json(click, result.to_dict(), options["indent"])
        else:
            _emit(click, _render_compliance(result))
        if not result.compliant:
            raise SystemExit(EXIT_FAILURE)

    @group.command(
        "governed-batch",
        help="Answer a whole schema in one process: JSON records in on stdin, "
        "one JSON object per line out.",
    )
    @click.argument(
        "file",
        required=False,
        default=None,
        type=click.Path(exists=True, dir_okay=False, readable=True, allow_dash=True),
    )
    @click.option(
        "--op",
        "op",
        type=click.Choice(_BATCH_OPS),
        default="expand",
        show_default=True,
        help="What to do with each record: expand an identifier, render a logical name as a "
        "physical one, check a name, correct a name, or return its audit record.",
    )
    @click.option(
        "--flush-every",
        "flush_every",
        type=click.IntRange(min=0),
        default=1,
        show_default=True,
        help="Flush stdout after this many records; 0 buffers, which is faster and wrong for "
        "a caller reading the pipe as it goes.",
    )
    @vocabulary_options
    def governed_batch_command(
        file: Optional[str], op: str, flush_every: int, **options: Any
    ) -> None:
        """Stream one governed answer per input record.

        This is the command the whole subsystem is adoptable through. A pipeline
        in another language holds a schema, not a column, and the cost that
        decides whether this library is usable from it is the number of process
        starts rather than the work inside them: the answer for one name takes
        microseconds and an interpreter takes tens of milliseconds, so a run
        that pays the start-up once per schema is three or four orders of
        magnitude away from one that pays it per column.

        Input is one record per line, in either of two shapes — a bare
        identifier, or a JSON object carrying ``identifier`` and optionally an
        ``id`` to be echoed back. Output is one JSON object per line, carrying
        the line number, the input, ``ok``, and either ``result`` or ``error``
        and ``error_type``. Blank lines are passed over and counted rather than
        answered.

        The exit status reports records that *failed*, not names that did not
        comply: a non-compliant name is the answer ``--op check`` was asked for,
        and it arrives as ``"ok": true`` with ``compliant`` false inside the
        result. The one-line summary on standard error is there so a caller can
        confirm it received every record it sent.

        Args:
            file: Path to the record stream, ``"-"`` for standard input, or
                ``None`` to use standard input when it is not a terminal.
            op: The per-record operation.
            flush_every: Output flush interval, in records.
            **options: The shared vocabulary options.

        Raises:
            click.UsageError: If ``--dictionary`` or ``--custom`` is unusable, or
                there is no readable record stream.
            SystemExit: With :data:`EXIT_FAILURE` when any record failed. Every
                record is written first.
        """
        namer = _governed_namer(click, options)
        stream, close_it = _batch_stream(click, file)
        try:
            records, failed, skipped, consumer_gone = _run_batch(op, namer, stream, flush_every)
        finally:
            if close_it:
                stream.close()
        if consumer_gone:
            # Nothing is reading stdout, and the answer was delivered as far as
            # anyone wanted it. There is nobody left to read a summary, and a
            # non-zero exit would call an ordinary `| head` a failure.
            return
        print(
            json.dumps(
                {
                    "op": op,
                    "records": records,
                    "failed": failed,
                    "skipped": skipped,
                },
                separators=_JSONL_SEPARATORS,
            ),
            file=sys.stderr,
        )
        if failed:
            raise SystemExit(EXIT_FAILURE)

    @group.command(
        "governed-audit",
        help="Report what a governed vocabulary does to a whole corpus of names, read from "
        "FILE or stdin.",
    )
    @click.argument(
        "file",
        required=False,
        default=None,
        type=click.Path(exists=True, dir_okay=False, readable=True, allow_dash=True),
    )
    @click.option(
        "--limit",
        "limit",
        type=click.IntRange(min=0),
        default=20,
        show_default=True,
        help="Rows of each ranked table to show; 0 shows every row.",
    )
    @click.option(
        "--suggest",
        "suggest",
        is_flag=True,
        help="Also list the catalog rows the corpus says are missing, ranked.",
    )
    @click.option(
        "--details",
        "details",
        is_flag=True,
        help="Keep the per-identifier records. JSON output only, and large: one record per "
        "distinct name the audit has something to say about.",
    )
    @governed_options
    def governed_audit_command(
        file: Optional[str], limit: int, suggest: bool, details: bool, **options: Any
    ) -> None:
        """Reduce a corpus of physical names to one report.

        The first thing to run against a real schema, and the reason is the
        ranked unknown-token table: it turns "our catalog is incomplete" into a
        finite list of rows to write, in the order that clears the most columns
        per row. Everything else on the report — coverage, compliance findings
        by reason code, the round trips that are neither stable nor a governed
        correction — is a count of something one of the verbs already said.

        The corpus is streamed rather than read into memory, so a schema export
        of any size is a legitimate argument. What the audit itself holds is one
        small record per *distinct* name, which is what de-duplicating a
        warehouse's repeated column names requires.

        Args:
            file: Path to the corpus, ``"-"`` for standard input, or ``None`` to
                use standard input when it is not a terminal.
            limit: Ranked-table row cap; ``0`` means every row.
            suggest: Append the catalog backlog as a work list.
            details: Retain the per-identifier records in the JSON payload.
            **options: The shared vocabulary and output options.

        Raises:
            click.UsageError: If ``--dictionary`` or ``--custom`` is unusable, or
                there is no readable corpus.
            SystemExit: With :data:`EXIT_FAILURE` when an input line could not be
                read. The report is printed first, because a corpus with one bad
                line is still a corpus worth reporting on.
        """
        from .governed.audit import audit_identifiers, render_audit, suggest_catalog_additions

        dictionary, policy, custom = _governed_context(click, options)
        stream, close_it = _batch_stream(click, file)
        problems: list[str] = []
        try:
            audit = audit_identifiers(
                _batch_identifiers(stream, problems),
                dictionary,
                policy,
                custom=custom,
                keep_details=details,
            )
        finally:
            if close_it:
                stream.close()
        rows = None if limit == 0 else limit
        suggestions = suggest_catalog_additions(audit, limit=rows) if suggest else ()
        if options["output_format"] == "json":
            payload = audit.to_dict()
            if suggest:
                payload["suggestions"] = [item.to_dict() for item in suggestions]
            _emit_json(click, payload, options["indent"])
        else:
            lines = [render_audit(audit, limit=rows)]
            if suggest:
                lines.extend(["", *_render_suggestions(suggestions)])
            _emit(click, lines)
        if problems:
            print(
                f"{len(problems)} input line(s) could not be read and are not in the audit:",
                file=sys.stderr,
            )
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            raise SystemExit(EXIT_FAILURE)

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

    A consumer that stops reading — ``| head -1`` on a streaming command — is
    success, not failure: the answer was delivered as far as anyone wanted it.
    See :func:`_is_closed_consumer` for why recognising that needs more than
    ``except BrokenPipeError`` and :func:`_abandon_stdout` for why returning a
    code is not enough on its own.

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
    except OSError as exc:
        if not _is_closed_consumer(exc):
            raise
        _abandon_stdout()
        return EXIT_OK
    except SystemExit as exc:  # pragma: no cover - click's own exit paths
        code = exc.code
        return EXIT_OK if code is None else int(code)

    return EXIT_OK if not isinstance(outcome, int) else outcome


if __name__ == "__main__":  # pragma: no cover - module execution shim
    sys.exit(main())
