#!/usr/bin/env python3
"""Validate every bundled data resource against its frozen on-disk format.

``acronymkit`` ships three families of resource file, and every consumer in the
package assumes they are well-formed. This script is the gate that keeps that
assumption true; CI runs it on every push.

Checked invariants
------------------
``stopwords_<lang>.json``
    Object with ``language`` (matching the file name), an optional
    ``description`` and ``categories``. ``categories`` holds *exactly* the eight
    :class:`~acronymkit.enums.StopWordCategory` keys; every entry is lowercase,
    non-empty and untrimmed-whitespace-free; each list is sorted ascending and
    duplicate-free; and no word appears in two categories.

``lexicon_<lang>.txt``
    UTF-8, one lowercase word per line, strictly ascending (which also proves
    uniqueness), no blank lines, letters only for that language (accents for
    fr/es/de, ``ß`` for de), each word within the configured length bounds. A
    leading ``#`` comment block is allowed; comments after the first word are
    not.

``ngram_<lang>.json``
    Object carrying ``language`` (matching the file name), ``order`` ``2``,
    ``alphabet`` (sorted, unique), ``boundary_start``/``boundary_end`` (distinct
    single characters outside the alphabet), a finite non-positive
    ``backoff_log_prob``, a non-negative ``vocabulary_size`` and ``transitions``
    whose contexts lie in ``alphabet + boundary_start``, whose successors lie in
    ``alphabet + boundary_end``, and whose every value is a finite number
    ``<= 0`` (a natural-log probability).

Usage::

    python tools/validate_resources.py
    python tools/validate_resources.py --language en --require

A resource that is simply absent is reported as ``missing (skipped)`` and does
not fail the run, so the script is useful while the resource set is still being
filled in; ``--require`` turns every absence into a violation. Every offending
file is reported -- the script never stops at the first problem.

Only the standard library and ``acronymkit`` itself are imported.

Exit codes:
    ``0`` all present resources are valid, ``1`` at least one violation,
    ``2`` usage error.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

#: ``<repo>/tools`` -- this script's own directory.
TOOLS_DIR = Path(__file__).resolve().parent

#: Repository root, located relative to ``__file__``.
REPO_ROOT = TOOLS_DIR.parent

#: Source root inserted on ``sys.path`` to import ``acronymkit`` uninstalled.
SRC_DIR = REPO_ROOT / "src"

if SRC_DIR.is_dir() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from acronymkit.enums import Language, StopWordCategory  # noqa: E402

#: Directory holding the bundled resources.
DEFAULT_RESOURCE_DIR = SRC_DIR / "acronymkit" / "resources"

#: Top-level keys permitted in a stop-word document (``description`` optional).
STOPWORD_KEYS = frozenset({"language", "description", "categories"})

#: ``(kind, language)`` pairs that are absent on purpose, so ``--require`` does
#: not report them as gaps.
#:
#: Only English ships a lexicon and an n-gram model. The French, Spanish and
#: German word lists would have to be derived from Hunspell dictionaries, and
#: those are copyleft: German's only permissive arm is the OASIS licence, which
#: grants distribution solely alongside ODF applications, and the French and
#: Spanish MPL arms would make the wheel MIT-plus-MPL. See ``data/LICENSES.md``.
#:
#: Shipping model-authored substitutes was the v0.1.0 answer and is precisely
#: what this release removed: an invented word list makes every ``Lambda(A)``
#: claim unverifiable. The engine now degrades honestly instead, and says so in
#: ``EngineMetadata.warnings``.
#:
#: Users who want real coverage run::
#:
#:     python tools/fetch_data.py hunspell-fr
#:     python tools/build_lexicons.py --language fr --output ~/fr.txt
#:     Config(language=Language.FR, lexicon_path=Path("~/fr.txt"))
DELIBERATELY_ABSENT = frozenset(
    (kind, language) for kind in ("lexicon", "ngram") for language in ("fr", "es", "de")
)

#: Top-level keys required in an n-gram document.
NGRAM_REQUIRED_KEYS = (
    "language",
    "order",
    "alphabet",
    "boundary_start",
    "boundary_end",
    "backoff_log_prob",
    "vocabulary_size",
    "transitions",
)

#: N-gram order the package implements.
EXPECTED_ORDER = 2

#: Shortest / longest word accepted in a lexicon.
MIN_WORD_LENGTH = 1
MAX_WORD_LENGTH = 45

#: Violations printed per file before the remainder is summarised.
MAX_REPORTED = 10

#: Byte-order mark rejected at the head of any resource file.
_BOM = "\ufeff"

_BASE_LETTERS = frozenset("abcdefghijklmnopqrstuvwxyz")

#: Letters accepted in each language's lexicon.
LANGUAGE_LETTERS: dict[str, frozenset[str]] = {
    Language.EN.value: _BASE_LETTERS,
    Language.FR.value: _BASE_LETTERS | frozenset("àâæçéèêëîïôœùûüÿ"),
    Language.ES.value: _BASE_LETTERS | frozenset("áéíñóúü"),
    Language.DE.value: _BASE_LETTERS | frozenset("äöüß"),
}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _is_number(value: Any) -> bool:
    """Return whether ``value`` is a real (non-boolean) JSON number."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _read_bytes(path: Path) -> bytes:
    """Return the (decompressed) bytes of ``path``.

    Args:
        path: File to read; ``.gz`` is transparently decompressed.

    Returns:
        The raw contents.

    Raises:
        OSError: If the file cannot be read or is invalid gzip data.
    """
    raw = path.read_bytes()
    if path.name.endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw


def _load_json(path: Path) -> tuple[Optional[Any], list[str]]:
    """Parse a JSON resource.

    Args:
        path: File to read.

    Returns:
        ``(payload, violations)``; ``payload`` is ``None`` when parsing failed.
    """
    try:
        text = _read_bytes(path).decode("utf-8")
    except (OSError, EOFError) as exc:
        return None, [f"unreadable: {exc}"]
    except UnicodeDecodeError as exc:
        return None, [f"not valid UTF-8: {exc}"]
    if text.startswith(_BOM):
        return None, ["starts with a byte-order mark"]
    try:
        return json.loads(text), []
    except ValueError as exc:
        return None, [f"not valid JSON: {exc}"]


def _out_of_order(values: Sequence[str]) -> list[str]:
    """Return violations describing the first few ordering/duplicate breaks.

    Args:
        values: The sequence that must be strictly ascending.

    Returns:
        Violation strings; empty when the sequence is sorted and unique.
    """
    problems: list[str] = []
    for index in range(1, len(values)):
        previous, current = values[index - 1], values[index]
        if current == previous:
            problems.append(f"duplicate entry {current!r} (line/index {index + 1})")
        elif current < previous:
            problems.append(
                f"out of order: {current!r} follows {previous!r} (line/index {index + 1})"
            )
    return problems


# ---------------------------------------------------------------------------
# per-family validators
# ---------------------------------------------------------------------------
def validate_stopwords(path: Path, language: str) -> tuple[str, list[str]]:
    """Validate a categorised stop-word document.

    Args:
        path: File to validate.
        language: Language code taken from the file name.

    Returns:
        ``(summary, violations)``.
    """
    payload, violations = _load_json(path)
    if payload is None:
        return "unparseable", violations
    if not isinstance(payload, dict):
        return "unparseable", [f"top level is a {type(payload).__name__}, expected an object"]

    unexpected = sorted(set(payload) - STOPWORD_KEYS)
    if unexpected:
        violations.append(f"unexpected top-level key(s): {', '.join(unexpected)}")
    if "language" not in payload:
        violations.append("missing top-level key 'language'")
    elif payload["language"] != language:
        violations.append(
            f"declares language {payload['language']!r} but the file name says {language!r}"
        )

    categories = payload.get("categories")
    if not isinstance(categories, dict):
        violations.append("missing or non-object 'categories'")
        return "invalid", violations

    expected = {member.value for member in StopWordCategory}
    missing = sorted(expected - set(categories))
    extra = sorted(set(categories) - expected)
    if missing:
        violations.append(f"missing categor(y/ies): {', '.join(missing)}")
    if extra:
        violations.append(f"unknown categor(y/ies): {', '.join(extra)}")

    seen: dict[str, str] = {}
    total = 0
    for name in sorted(set(categories) & expected):
        entries = categories[name]
        if not isinstance(entries, list):
            violations.append(f"category {name!r} is a {type(entries).__name__}, expected a list")
            continue
        words: list[str] = []
        for entry in entries:
            if not isinstance(entry, str):
                violations.append(f"category {name!r} holds a non-string entry {entry!r}")
                continue
            if not entry:
                violations.append(f"category {name!r} holds an empty entry")
                continue
            if entry != entry.strip():
                violations.append(f"category {name!r}: {entry!r} has surrounding whitespace")
            if entry != entry.lower():
                violations.append(f"category {name!r}: {entry!r} is not lowercase")
            words.append(entry)
        total += len(words)
        violations.extend(f"category {name!r}: {problem}" for problem in _out_of_order(words))
        for word in words:
            owner = seen.get(word)
            if owner is not None and owner != name:
                violations.append(f"{word!r} appears in both {owner!r} and {name!r}")
            else:
                seen[word] = name

    return f"{len(expected & set(categories))} categories, {total} words", violations


def validate_lexicon(path: Path, language: str) -> tuple[str, list[str]]:
    """Validate a plain-text lexicon.

    Args:
        path: File to validate.
        language: Language code taken from the file name.

    Returns:
        ``(summary, violations)``.
    """
    try:
        raw = _read_bytes(path)
    except (OSError, EOFError) as exc:
        return "unreadable", [f"unreadable: {exc}"]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return "unreadable", [f"not valid UTF-8: {exc}"]

    violations: list[str] = []
    if text.startswith(_BOM):
        violations.append("starts with a byte-order mark")
        text = text[1:]

    allowed = LANGUAGE_LETTERS.get(language, _BASE_LETTERS)
    words: list[str] = []
    body_started = False
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            if body_started:
                violations.append(f"line {number}: comment after the first word")
            continue
        if not stripped:
            if body_started:
                violations.append(f"line {number}: blank line inside the word list")
            continue
        body_started = True
        if line != stripped:
            violations.append(f"line {number}: {line!r} has surrounding whitespace")
        if stripped != stripped.lower():
            violations.append(f"line {number}: {stripped!r} is not lowercase")
        if not (MIN_WORD_LENGTH <= len(stripped) <= MAX_WORD_LENGTH):
            violations.append(
                f"line {number}: {stripped!r} length {len(stripped)} is outside "
                f"[{MIN_WORD_LENGTH}, {MAX_WORD_LENGTH}]"
            )
        illegal = sorted({char for char in stripped if char not in allowed})
        if illegal:
            violations.append(
                f"line {number}: {stripped!r} contains character(s) not allowed for "
                f"{language!r}: {''.join(illegal)!r}"
            )
        words.append(stripped)

    violations.extend(_out_of_order(words))
    if not words:
        violations.append("contains no words")
    return f"{len(words)} words", violations


def validate_ngram(path: Path, language: str) -> tuple[str, list[str]]:
    """Validate a generated character n-gram model.

    Args:
        path: File to validate.
        language: Language code taken from the file name.

    Returns:
        ``(summary, violations)``.
    """
    payload, violations = _load_json(path)
    if payload is None:
        return "unparseable", violations
    if not isinstance(payload, dict):
        return "unparseable", [f"top level is a {type(payload).__name__}, expected an object"]

    for key in NGRAM_REQUIRED_KEYS:
        if key not in payload:
            violations.append(f"missing required key {key!r}")

    if payload.get("language") not in (None, language):
        violations.append(
            f"declares language {payload.get('language')!r} but the file name says {language!r}"
        )
    if "order" in payload and payload["order"] != EXPECTED_ORDER:
        violations.append(f"order is {payload['order']!r}, expected {EXPECTED_ORDER}")

    alphabet = payload.get("alphabet", "")
    if not isinstance(alphabet, str) or not alphabet:
        violations.append("'alphabet' must be a non-empty string")
        alphabet = ""
    else:
        if len(set(alphabet)) != len(alphabet):
            violations.append("'alphabet' contains duplicate characters")
        if list(alphabet) != sorted(alphabet):
            violations.append("'alphabet' is not sorted ascending")

    start = payload.get("boundary_start", "^")
    end = payload.get("boundary_end", "$")
    for name, symbol in (("boundary_start", start), ("boundary_end", end)):
        if not isinstance(symbol, str) or len(symbol) != 1:
            violations.append(f"{name!r} must be a single character, got {symbol!r}")
        elif symbol in alphabet:
            violations.append(f"{name!r} ({symbol!r}) also appears in the alphabet")
    if start == end:
        violations.append("'boundary_start' and 'boundary_end' must differ")

    backoff = payload.get("backoff_log_prob")
    if not _is_number(backoff) or not math.isfinite(float(backoff)):
        violations.append(f"'backoff_log_prob' must be a finite number, got {backoff!r}")
    elif float(backoff) > 0.0:
        violations.append(f"'backoff_log_prob' must be <= 0, got {backoff!r}")

    size = payload.get("vocabulary_size", 0)
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        violations.append(f"'vocabulary_size' must be a non-negative integer, got {size!r}")

    transitions = payload.get("transitions")
    if not isinstance(transitions, dict):
        violations.append("'transitions' must be an object")
        return "invalid", violations

    valid_contexts = set(alphabet) | ({start} if isinstance(start, str) else set())
    valid_successors = set(alphabet) | ({end} if isinstance(end, str) else set())
    unknown_contexts: set[str] = set()
    unknown_successors: set[str] = set()
    positive = 0
    non_numeric = 0
    count = 0
    for prev, row in transitions.items():
        if prev not in valid_contexts:
            unknown_contexts.add(prev)
        if not isinstance(row, dict):
            violations.append(f"transition row {prev!r} is a {type(row).__name__}, expected object")
            continue
        for nxt, value in row.items():
            count += 1
            if nxt not in valid_successors:
                unknown_successors.add(nxt)
            if not _is_number(value) or not math.isfinite(float(value)):
                non_numeric += 1
            elif float(value) > 0.0:
                positive += 1
    if unknown_contexts:
        violations.append(
            "transition context(s) outside alphabet + boundary_start: "
            + ", ".join(repr(c) for c in sorted(unknown_contexts)[:10])
        )
    if unknown_successors:
        violations.append(
            "transition successor(s) outside alphabet + boundary_end: "
            + ", ".join(repr(c) for c in sorted(unknown_successors)[:10])
        )
    if non_numeric:
        violations.append(f"{non_numeric} transition value(s) are not finite numbers")
    if positive:
        violations.append(f"{positive} transition value(s) are > 0 (must be log-probabilities)")
    if not count:
        violations.append("'transitions' is empty")

    return f"{len(alphabet)} letters, {count} transitions", violations


#: ``kind -> (file-name template, validator)``.
VALIDATORS = {
    "stopwords": ("stopwords_{lang}.json", validate_stopwords),
    "lexicon": ("lexicon_{lang}.txt", validate_lexicon),
    "ngram": ("ngram_{lang}.json", validate_ngram),
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="validate_resources.py",
        description="Validate the bundled acronymkit resource files.",
    )
    parser.add_argument(
        "-l",
        "--language",
        action="append",
        dest="languages",
        metavar="LANG",
        choices=[member.value for member in Language],
        help="Language to validate; repeatable. Defaults to every known language.",
    )
    parser.add_argument(
        "--resources-dir",
        type=Path,
        default=DEFAULT_RESOURCE_DIR,
        metavar="DIR",
        help="Directory holding the resource files.",
    )
    parser.add_argument(
        "--require",
        action="store_true",
        help="Treat a missing resource file as a violation instead of skipping it.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point.

    Args:
        argv: Argument vector excluding the program name; defaults to
            :data:`sys.argv`.

    Returns:
        ``0`` when every present (or required) resource is valid, else ``1``.
    """
    args = build_parser().parse_args(argv)
    resources_dir = Path(args.resources_dir)
    languages = list(dict.fromkeys(args.languages or [m.value for m in Language]))

    print(f"validating resources in {resources_dir}")
    failures: list[tuple[str, list[str]]] = []
    missing = 0
    checked = 0
    #: Every legal resource file name, independent of the selected languages,
    #: so that ``--language`` never makes a valid file look like a stray.
    expected_names = {
        template.format(lang=member.value) + suffix
        for template, _ in VALIDATORS.values()
        for member in Language
        for suffix in ("", ".gz")
    }
    expected_names.add("__init__.py")

    for kind in sorted(VALIDATORS):
        template, validator = VALIDATORS[kind]
        for language in languages:
            name = template.format(lang=language)
            path = resources_dir / name
            if not path.is_file():
                gzipped = resources_dir / (name + ".gz")
                if gzipped.is_file():
                    path = gzipped
                    name = gzipped.name
                elif (kind, language) in DELIBERATELY_ABSENT:
                    # Not a gap: see DELIBERATELY_ABSENT. --require must not
                    # demand a file the project has decided it cannot ship.
                    print(f"  n/a   {name:<24} not bundled by design")
                    continue
                elif args.require:
                    print(f"  FAIL  {name:<24} missing (required)")
                    failures.append((name, ["file is missing and --require was given"]))
                    missing += 1
                    continue
                else:
                    print(f"  SKIP  {name:<24} missing (skipped)")
                    missing += 1
                    continue
            checked += 1
            summary, violations = validator(path, language)
            status = "OK  " if not violations else "FAIL"
            print(f"  {status}  {name:<24} {summary}")
            if violations:
                failures.append((name, violations))

    if resources_dir.is_dir():
        strays = sorted(
            entry.name
            for entry in resources_dir.iterdir()
            if entry.is_file()
            and entry.name not in expected_names
            and entry.suffix in {".json", ".txt", ".gz"}
        )
        for stray in strays:
            print(f"  NOTE  {stray:<24} not a recognised resource name")

    print(f"\n{checked} file(s) validated, {missing} missing, {len(failures)} with violations")
    if not failures:
        return 0

    print("\nviolations:", file=sys.stderr)
    for name, violations in failures:
        print(f"  {name}:", file=sys.stderr)
        for violation in violations[:MAX_REPORTED]:
            print(f"    - {violation}", file=sys.stderr)
        if len(violations) > MAX_REPORTED:
            print(f"    - ... {len(violations) - MAX_REPORTED} more", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
