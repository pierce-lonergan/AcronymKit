#!/usr/bin/env python3
"""Train and commit the bundled character n-gram models.

The phonotactic term ``Phi(A)`` of the scoring function is backed by a
character bigram model per language, shipped inside the package as
``src/acronymkit/resources/ngram_<lang>.json``. That file is *generated*, not
hand-written: this script reads ``lexicon_<lang>.txt``, fits
:class:`acronymkit.phonetics.CharNGramModel` with add-k smoothing and writes the
JSON in a diff-friendly canonical form (sorted keys, ``indent=1``, every float
rounded to six decimal places).

Usage::

    python tools/build_ngram_model.py                     # every language with a lexicon
    python tools/build_ngram_model.py --language en --language fr
    python tools/build_ngram_model.py --smoothing 0.25
    python tools/build_ngram_model.py --check             # CI drift gate

``--check`` re-trains from the current lexicons and compares the result against
the committed file, exiting ``1`` and describing the differences if they have
drifted apart. Languages without a lexicon are skipped with a notice rather than
treated as an error, so the script is usable long before every lexicon lands.

Only the standard library and ``acronymkit`` itself are imported; the package is
made importable from a plain source checkout by putting ``<repo>/src`` on
``sys.path``, so no editable install is required.

Exit codes:
    ``0`` success, ``1`` drift detected or a lexicon/output error, ``2`` usage.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

#: ``<repo>/tools`` -- this script's own directory.
TOOLS_DIR = Path(__file__).resolve().parent

#: Repository root, located relative to ``__file__`` so the script is runnable
#: from any working directory.
REPO_ROOT = TOOLS_DIR.parent

#: Source root inserted on ``sys.path`` to import ``acronymkit`` uninstalled.
SRC_DIR = REPO_ROOT / "src"

if SRC_DIR.is_dir() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from acronymkit.enums import Language  # noqa: E402
from acronymkit.phonetics import CharNGramModel  # noqa: E402

#: Directory holding both the lexicons and the generated models.
DEFAULT_RESOURCE_DIR = SRC_DIR / "acronymkit" / "resources"

#: Decimal places kept for every float written to the model files.
ROUND_DIGITS = 6

#: Default Lidstone ``k``.
DEFAULT_SMOOTHING = 0.5

#: Maximum number of individual differences printed per language in ``--check``.
MAX_DIFF_LINES = 12


# ---------------------------------------------------------------------------
# lexicon input
# ---------------------------------------------------------------------------
def lexicon_path(language: str, resource_dir: Path) -> Optional[Path]:
    """Return the lexicon file for ``language``, or ``None`` when absent.

    Args:
        language: Lowercase language code, e.g. ``"en"``.
        resource_dir: Directory searched for ``lexicon_<lang>.txt[.gz]``.

    Returns:
        The first existing candidate path, else ``None``.
    """
    for name in (f"lexicon_{language}.txt", f"lexicon_{language}.txt.gz"):
        candidate = resource_dir / name
        if candidate.is_file():
            return candidate
    return None


def read_lexicon(path: Path) -> list[str]:
    """Read the words of a lexicon file.

    Blank lines and ``#`` comment lines (the format's optional leading comment
    block) are skipped; every other line is stripped of surrounding whitespace.

    Args:
        path: File to read; a ``.gz`` suffix is transparently decompressed.

    Returns:
        The words, in file order.

    Raises:
        OSError: If the file cannot be read.
        UnicodeDecodeError: If the file is not valid UTF-8.
    """
    raw = path.read_bytes()
    if path.name.endswith(".gz"):
        raw = gzip.decompress(raw)
    words: list[str] = []
    for line in raw.decode("utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        words.append(stripped)
    return words


def discover_languages(resource_dir: Path) -> list[str]:
    """Return the language codes that currently have a lexicon.

    Args:
        resource_dir: Directory to scan.

    Returns:
        Sorted, lowercase language codes drawn from :class:`Language`, limited
        to those with a readable lexicon file.
    """
    return [
        member.value for member in Language if lexicon_path(member.value, resource_dir) is not None
    ]


# ---------------------------------------------------------------------------
# canonical rendering
# ---------------------------------------------------------------------------
def round_payload(payload: Any, digits: int = ROUND_DIGITS) -> Any:
    """Recursively round every float in ``payload``.

    Negative zero is normalised to ``0.0`` so the rendering is stable across
    platforms.

    Args:
        payload: A JSON-compatible structure.
        digits: Decimal places to keep.

    Returns:
        A new structure with the same shape and rounded floats.
    """
    if isinstance(payload, bool):
        return payload
    if isinstance(payload, float):
        rounded = round(payload, digits)
        return 0.0 if rounded == 0 else rounded
    if isinstance(payload, dict):
        return {key: round_payload(value, digits) for key, value in payload.items()}
    if isinstance(payload, list):
        return [round_payload(value, digits) for value in payload]
    return payload


def render(payload: dict[str, Any]) -> str:
    """Serialise a model payload in the committed canonical form.

    Args:
        payload: The (already rounded) model dictionary.

    Returns:
        JSON text with sorted keys, one-space indentation, non-ASCII characters
        left intact for readable diffs, and a trailing newline.
    """
    return json.dumps(payload, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def build_payload(language: str, words: Sequence[str], smoothing: float) -> dict[str, Any]:
    """Train a model and return its rounded, JSON-ready payload.

    Args:
        language: Language code recorded on the model.
        words: Training words.
        smoothing: Lidstone ``k`` handed to
            :meth:`acronymkit.phonetics.CharNGramModel.train`.

    Returns:
        The payload as it should appear on disk.

    Raises:
        ValueError: If ``language`` is unknown or ``smoothing`` is not positive.
    """
    model = CharNGramModel.train(words, language=Language.coerce(language), smoothing=smoothing)
    return round_payload(model.to_dict())


# ---------------------------------------------------------------------------
# drift reporting
# ---------------------------------------------------------------------------
def describe_diff(committed: Any, rebuilt: dict[str, Any]) -> list[str]:
    """Describe how a committed model differs from a freshly trained one.

    Args:
        committed: The parsed committed payload (any JSON value).
        rebuilt: The freshly trained payload.

    Returns:
        Human-readable difference lines; empty when the payloads agree.
    """
    if not isinstance(committed, dict):
        return [f"committed file is a {type(committed).__name__}, expected an object"]

    lines: list[str] = []
    for key in sorted((set(committed) | set(rebuilt)) - {"transitions"}):
        old = committed.get(key, "<missing>")
        new = rebuilt.get(key, "<missing>")
        if old != new:
            lines.append(f"{key}: {old!r} -> {new!r}")

    old_transitions = committed.get("transitions")
    new_transitions = rebuilt.get("transitions", {})
    if not isinstance(old_transitions, dict):
        lines.append("transitions: committed value is not an object")
        return lines

    old_pairs = {
        (prev, nxt): value
        for prev, row in old_transitions.items()
        if isinstance(row, dict)
        for nxt, value in row.items()
    }
    new_pairs = {
        (prev, nxt): value for prev, row in new_transitions.items() for nxt, value in row.items()
    }
    added = sorted(set(new_pairs) - set(old_pairs))
    removed = sorted(set(old_pairs) - set(new_pairs))
    changed = sorted(
        key for key in set(old_pairs) & set(new_pairs) if old_pairs[key] != new_pairs[key]
    )
    if added:
        sample = ", ".join(f"{p}->{n}" for p, n in added[:5])
        lines.append(f"transitions: {len(added)} added ({sample})")
    if removed:
        sample = ", ".join(f"{p}->{n}" for p, n in removed[:5])
        lines.append(f"transitions: {len(removed)} removed ({sample})")
    if changed:
        lines.append(f"transitions: {len(changed)} changed")
        for prev, nxt in changed[:5]:
            lines.append(
                f"  {prev}->{nxt}: {old_pairs[(prev, nxt)]!r} -> {new_pairs[(prev, nxt)]!r}"
            )
    return lines


# ---------------------------------------------------------------------------
# per-language driver
# ---------------------------------------------------------------------------
def process_language(
    language: str,
    *,
    lexicon_dir: Path,
    output_dir: Path,
    smoothing: float,
    check: bool,
) -> tuple[bool, list[str]]:
    """Build (or verify) the model for one language.

    Args:
        language: Language code.
        lexicon_dir: Directory holding ``lexicon_<lang>.txt``.
        output_dir: Directory holding/receiving ``ngram_<lang>.json``.
        smoothing: Lidstone ``k``.
        check: When ``True`` nothing is written; the committed file is compared
            against a fresh training run instead.

    Returns:
        ``(ok, messages)`` -- ``ok`` is ``False`` on a hard failure or on drift.
    """
    messages: list[str] = []
    source = lexicon_path(language, lexicon_dir)
    if source is None:
        messages.append(f"{language}: no lexicon_{language}.txt - skipped")
        return True, messages

    try:
        words = read_lexicon(source)
    except (OSError, UnicodeDecodeError, EOFError) as exc:
        messages.append(f"{language}: lexicon unreadable ({exc})")
        return False, messages
    if not words:
        messages.append(f"{language}: lexicon {source.name} is empty - skipped")
        return True, messages

    payload = build_payload(language, words, smoothing)
    text = render(payload)
    target = output_dir / f"ngram_{language}.json"
    transition_count = sum(len(row) for row in payload["transitions"].values())

    if check:
        if not target.is_file():
            messages.append(f"{language}: {target.name} is missing (run without --check)")
            return False, messages
        try:
            current = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            messages.append(f"{language}: {target.name} unreadable ({exc})")
            return False, messages
        if current == text:
            messages.append(f"{language}: {target.name} up to date")
            return True, messages
        messages.append(f"{language}: {target.name} DRIFT")
        try:
            committed = json.loads(current)
        except ValueError as exc:
            messages.append(f"  committed file is not valid JSON: {exc}")
            return False, messages
        differences = describe_diff(committed, payload)
        if not differences:
            differences = ["content is equivalent but the formatting differs"]
        for line in differences[:MAX_DIFF_LINES]:
            messages.append(f"  {line}")
        if len(differences) > MAX_DIFF_LINES:
            messages.append(f"  ... {len(differences) - MAX_DIFF_LINES} more difference(s)")
        return False, messages

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except OSError as exc:
        messages.append(f"{language}: could not write {target.name} ({exc})")
        return False, messages
    messages.append(
        f"{language}: wrote {target.name} "
        f"({payload['vocabulary_size']} words, {len(payload['alphabet'])} letters, "
        f"{transition_count} transitions)"
    )
    return True, messages


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="build_ngram_model.py",
        description="Train the bundled acronymkit character n-gram models.",
    )
    parser.add_argument(
        "-l",
        "--language",
        action="append",
        dest="languages",
        metavar="LANG",
        choices=[member.value for member in Language],
        help=(
            "Language to build; repeatable. Defaults to every language that "
            "currently has a lexicon."
        ),
    )
    parser.add_argument(
        "--smoothing",
        type=float,
        default=DEFAULT_SMOOTHING,
        metavar="K",
        help=f"Lidstone add-k smoothing constant (default: {DEFAULT_SMOOTHING}).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if a committed model differs from a fresh build.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RESOURCE_DIR,
        metavar="DIR",
        help="Directory holding the generated ngram_<lang>.json files.",
    )
    parser.add_argument(
        "--lexicon-dir",
        type=Path,
        default=DEFAULT_RESOURCE_DIR,
        metavar="DIR",
        help="Directory holding the lexicon_<lang>.txt inputs.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point.

    Args:
        argv: Argument vector excluding the program name; defaults to
            :data:`sys.argv`.

    Returns:
        ``0`` on success, ``1`` on drift or an I/O failure.
    """
    args = build_parser().parse_args(argv)
    if not (args.smoothing > 0.0):
        print("error: --smoothing must be greater than 0", file=sys.stderr)
        return 2

    lexicon_dir = Path(args.lexicon_dir)
    output_dir = Path(args.output_dir)
    languages = list(dict.fromkeys(args.languages or discover_languages(lexicon_dir)))
    if not languages:
        print(f"no lexicon_<lang>.txt found in {lexicon_dir}; nothing to build")
        return 0

    ok = True
    for language in languages:
        succeeded, messages = process_language(
            language,
            lexicon_dir=lexicon_dir,
            output_dir=output_dir,
            smoothing=args.smoothing,
            check=args.check,
        )
        ok = ok and succeeded
        for line in messages:
            print(line)

    if not ok:
        if args.check:
            print(
                "\nModels are out of date. Re-run: python tools/build_ngram_model.py",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
