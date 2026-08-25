#!/usr/bin/env python3
"""Build the bundled lexicons from fetched third-party sources.

Replaces the v0.1.0 lexicons, which were model-authored and therefore
indefensible: a library whose ``Lambda(A)`` term rests on a word list an LLM
invented cannot claim a dictionary hit means anything.

Sources
-------
``en``
    SCOWL (Spell Checker Oriented Word Lists), size cut ``<= 60``. Permissively
    licensed, so the derived list is vendored into the wheel.

``fr`` / ``es`` / ``de``
    Hunspell dictionaries, which are copyleft — see ``data/LICENSES.md`` for the
    per-language reasoning. These are **never vendored**. This script can still
    convert them, but only to a path you choose outside the package, for use via
    ``Config(lexicon_path=...)``.

The vendoring rule is enforced here rather than remembered: :func:`_vendor_guard`
consults ``tools.fetch_data.ASSETS`` and refuses to write into the package
resource directory for any asset whose licence does not permit redistribution.

Usage
-----
::

    python tools/build_lexicons.py --language en                  # vendored
    python tools/build_lexicons.py --language fr --output ~/fr.txt  # local only
    python tools/build_lexicons.py --validate-syllables            # CMUdict check
"""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
import unicodedata
from pathlib import Path
from typing import Iterable, Iterator, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RESOURCE_DIR = REPO_ROOT / "src" / "acronymkit" / "resources"

sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_data import BY_KEY  # noqa: E402

#: SCOWL size cut. SCOWL grades entries 10 (most common) to 95 (obscure);
#: 60 is the largest cut the project describes as reasonable for a general
#: speller. The choice matters because ``Lambda(A)`` is a *claim* that a
#: generated acronym is a real word, and a false positive there is worse than a
#: false negative: at 80+ the list starts admitting strings no reader would
#: recognise as words, which would make the dictionary-backronym strategy
#: confidently propose nonsense.
SCOWL_MAX_SIZE = 60

#: SCOWL categories to include. Proper names, abbreviations, contractions and
#: all-caps entries are excluded on purpose: "NASA" must not count as a
#: dictionary word, or every initialism would trivially satisfy ``Lambda(A)``.
SCOWL_CATEGORIES = ("english-words", "american-words")

#: Bounds on a vendored lexicon entry.
MIN_WORD_LENGTH = 2
MAX_WORD_LENGTH = 16

_ALPHA_ONLY = re.compile(r"^[^\W\d_]+$")


def _vendor_guard(asset_key: str, destination: Path) -> None:
    """Refuse to write a non-redistributable asset into the package.

    Args:
        asset_key: Key into the :mod:`tools.fetch_data` registry.
        destination: Where the derived file would be written.

    Raises:
        SystemExit: If ``destination`` is inside the packaged resource
            directory and the source asset is not licensed for redistribution.
    """
    asset = BY_KEY[asset_key]
    try:
        destination.resolve().relative_to(RESOURCE_DIR.resolve())
    except ValueError:
        return  # outside the package: the user's own machine, their choice
    if not asset.vendorable:
        raise SystemExit(
            f"refusing to vendor '{asset_key}' into the wheel.\n"
            f"  licence: {asset.licence}\n"
            f"  {asset.vendor_note}\n"
            f"Write it somewhere outside {RESOURCE_DIR} and point "
            f"Config(lexicon_path=...) at it instead."
        )


def _normalise(word: str) -> Optional[str]:
    """Fold one raw source entry into a lexicon entry, or reject it.

    Args:
        word: Raw line from a source word list.

    Returns:
        The lowercase entry, or ``None`` if it is unusable (wrong length,
        contains digits, punctuation, whitespace or an apostrophe).
    """
    entry = unicodedata.normalize("NFC", word.strip()).lower()
    if not (MIN_WORD_LENGTH <= len(entry) <= MAX_WORD_LENGTH):
        return None
    if not _ALPHA_ONLY.match(entry):
        return None
    return entry


def read_scowl(archive: Path, *, max_size: int = SCOWL_MAX_SIZE) -> set[str]:
    """Extract the English word list from a SCOWL release tarball.

    Non-ASCII entries are dropped. SCOWL carries around 157 accented loanwords
    at this size cut (``abbé``, ``appliqué``, ``attaché``, ``blasé``), and they
    are genuine English — but they cannot help here and do measurably hurt.
    They cannot help because a generated acronym takes token initials and
    uppercases them, so an accented character reaches an English acronym only if
    an English token *starts* with one, which effectively never happens. They
    hurt because every distinct character widens the n-gram alphabet: keeping
    them takes it from 26 letters to 39 and spreads the smoothing mass over 13
    symbols that never appear in a candidate.

    Args:
        archive: Path to ``scowl-<version>.tar.gz``.
        max_size: Highest SCOWL size cut to include.

    Returns:
        The normalised, de-duplicated, ASCII-only word set.
    """
    words: set[str] = set()
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if "/final/" not in member.name:
                continue
            stem, _, size = member.name.rpartition(".")
            if not size.isdigit() or int(size) > max_size:
                continue
            if not stem.endswith(SCOWL_CATEGORIES):
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            # SCOWL final/ files are ISO-8859-1.
            for line in handle.read().decode("latin-1").splitlines():
                entry = _normalise(line)
                if entry is not None and entry.isascii():
                    words.add(entry)
    return words


def read_hunspell(dic_path: Path) -> set[str]:
    """Extract surface forms from a Hunspell ``.dic`` file.

    Only the stems are taken; affix flags after ``/`` are discarded rather than
    expanded, since expanding them correctly needs the ``.aff`` rules and a
    Hunspell implementation. The result is therefore a solid but not exhaustive
    lexicon — which is the honest trade for a fetch-only asset.

    Args:
        dic_path: Path to the ``.dic`` file.

    Returns:
        The normalised, de-duplicated word set.
    """
    words: set[str] = set()
    text = dic_path.read_bytes().decode("utf-8", "replace")
    for index, line in enumerate(text.splitlines()):
        if index == 0 and line.strip().isdigit():
            continue  # the entry-count header
        stem = line.split("/", 1)[0].split("\t", 1)[0]
        entry = _normalise(stem)
        if entry is not None:
            words.add(entry)
    return words


def write_lexicon(words: Iterable[str], destination: Path, *, header: Sequence[str]) -> int:
    """Write a sorted, de-duplicated lexicon file.

    Args:
        words: Entries to write.
        destination: Output path.
        header: Comment lines (without the leading ``#``) placed at the top;
            this is where third-party attribution lives.

    Returns:
        The number of entries written.
    """
    ordered = sorted(set(words))
    destination.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {line}".rstrip() for line in header]
    lines.append(f"# entries: {len(ordered)}")
    lines.append("")
    lines.extend(ordered)
    # ``Path.write_text`` grew ``newline`` in 3.10; ``requires-python`` is ``>=3.9``.
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return len(ordered)


def build_english(destination: Path) -> int:
    """Build the vendored English lexicon from SCOWL."""
    asset = BY_KEY["scowl"]
    _vendor_guard("scowl", destination)
    archive = DATA_DIR / asset.filename
    if not archive.exists():
        raise SystemExit(f"missing {archive}. Run: python tools/fetch_data.py scowl")
    words = read_scowl(archive)
    count = write_lexicon(
        words,
        destination,
        header=[
            "acronymkit bundled lexicon -- English",
            "",
            f"Derived from SCOWL (Spell Checker Oriented Word Lists), size cut <= {SCOWL_MAX_SIZE},",
            f"categories {', '.join(SCOWL_CATEGORIES)}. Proper names, abbreviations,",
            "contractions and all-caps entries are excluded so that an initialism",
            "cannot satisfy Lambda(A) merely by being a known acronym.",
            "",
            asset.attribution,
            "",
            "  Permission to use, copy, modify, distribute and sell these word lists,",
            "  the associated scripts, the output created from the scripts, and its",
            "  documentation for any purpose is hereby granted without fee, provided",
            "  that the above copyright notice appears in all copies and that both",
            "  that copyright notice and this permission notice appear in supporting",
            "  documentation. Kevin Atkinson makes no representations about the",
            '  suitability of this array for any purpose. It is provided "as is"',
            "  without express or implied warranty.",
            "",
            f"Source:  {asset.url}",
            f"SHA-256: {asset.sha256}",
            "",
            "Regenerate with: python tools/build_lexicons.py --language en",
        ],
    )
    return count


def build_hunspell_language(language: str, destination: Path) -> int:
    """Build a non-English lexicon from a fetched Hunspell dictionary."""
    key = f"hunspell-{language}"
    if key not in BY_KEY:
        raise SystemExit(f"no registered Hunspell asset for language {language!r}")
    asset = BY_KEY[key]
    _vendor_guard(key, destination)
    dic = DATA_DIR / asset.filename
    if not dic.exists():
        raise SystemExit(f"missing {dic}. Run: python tools/fetch_data.py {key}")
    words = read_hunspell(dic)
    return write_lexicon(
        words,
        destination,
        header=[
            f"acronymkit lexicon -- {language}",
            "",
            "NOT redistributable inside the acronymkit wheel.",
            f"Licence: {asset.licence}",
            asset.vendor_note,
            "",
            asset.attribution,
            f"Source:  {asset.url}",
            f"SHA-256: {asset.sha256}",
            "",
            "Use with: Config(lexicon_path=Path(<this file>))",
        ],
    )


# ---------------------------------------------------------------------------
# CMUdict validation
# ---------------------------------------------------------------------------
_STRESS_DIGIT = re.compile(r"\d")


def iter_cmudict(path: Path) -> Iterator[tuple[str, int]]:
    """Yield ``(word, syllable_count)`` from a CMUdict ``.dict`` file.

    A syllable nucleus is a vowel phoneme, and CMUdict marks exactly those with
    a trailing stress digit, so counting stress-marked phonemes counts syllables.

    Args:
        path: Path to ``cmudict.dict``.

    Yields:
        Lowercase word and its syllable count. Alternate pronunciations
        (``word(2)``) and entries with non-alphabetic characters are skipped.
    """
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        word, _, phonemes = line.partition(" ")
        if "(" in word or not _ALPHA_ONLY.match(word):
            continue
        syllables = sum(1 for token in phonemes.split() if _STRESS_DIGIT.search(token))
        if syllables:
            yield word.lower(), syllables


def validate_syllables(sample_limit: Optional[int] = None) -> dict[str, float]:
    """Measure the syllable heuristic against CMUdict ground truth.

    ``phonetics.syllable_count`` is a vowel-group heuristic. CMUdict gives real
    pronunciations for ~134k words, which turns "seems about right" into a
    number.

    Args:
        sample_limit: Optionally cap the number of words scored.

    Returns:
        Metrics: ``total``, ``exact`` accuracy, ``within_one`` accuracy, and
        ``mean_absolute_error``.
    """
    from acronymkit.phonetics import syllable_count

    path = DATA_DIR / BY_KEY["cmudict"].filename
    if not path.exists():
        raise SystemExit(f"missing {path}. Run: python tools/fetch_data.py cmudict")

    total = exact = within_one = 0
    absolute_error = 0
    for word, truth in iter_cmudict(path):
        if sample_limit is not None and total >= sample_limit:
            break
        predicted = syllable_count(word)
        total += 1
        delta = abs(predicted - truth)
        absolute_error += delta
        exact += delta == 0
        within_one += delta <= 1
    if not total:
        raise SystemExit("no CMUdict entries scored")
    return {
        "total": float(total),
        "exact": exact / total,
        "within_one": within_one / total,
        "mean_absolute_error": absolute_error / total,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--language", choices=("en", "fr", "es", "de"))
    parser.add_argument(
        "--output",
        type=Path,
        help="destination path; defaults to the packaged resource for --language en",
    )
    parser.add_argument(
        "--validate-syllables",
        action="store_true",
        help="score phonetics.syllable_count against CMUdict and print the metrics",
    )
    args = parser.parse_args(argv)

    if args.validate_syllables:
        metrics = validate_syllables()
        print(f"CMUdict words scored : {int(metrics['total']):,}")
        print(f"exact syllable match : {metrics['exact']:.4f}")
        print(f"within one syllable  : {metrics['within_one']:.4f}")
        print(f"mean absolute error  : {metrics['mean_absolute_error']:.4f}")
        return 0

    if not args.language:
        parser.print_help()
        return 2

    if args.language == "en":
        destination = args.output or (RESOURCE_DIR / "lexicon_en.txt")
        count = build_english(destination)
    else:
        if args.output is None:
            raise SystemExit(
                f"--output is required for {args.language}: the Hunspell sources are "
                "copyleft and must not be written into the package. See data/LICENSES.md."
            )
        count = build_hunspell_language(args.language, args.output)

    print(f"wrote {count:,} entries to {destination if args.language == 'en' else args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
