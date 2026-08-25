#!/usr/bin/env python3
"""Build the bundled pseudo-precision reliability table.

Why this ships at all
---------------------
``acronymkit._pseudo_precision`` estimates how often each matching strategy
fires *for a reason*, from raw text and no annotation. That is the property
worth having: a user on legal, financial or internal documentation can calibrate
on their own corpus where no gold standard exists. But it costs them a corpus,
and until now there was no other way to get a number at all. An offline user
with no corpus and no network had an estimator and nothing to put in it.

So a table derived once, by a maintainer, ships as the starting point. It is a
**prior, not a calibration**: see the caveat in
:func:`acronymkit._pseudo_precision.bundled_table`.

Where the text comes from, and why that is the licence question
--------------------------------------------------------------
The estimator reads raw text, so the table inherits whatever the text's licence
imposes. This project has three corpora on disk and only one of them can be
used:

``med1250``
    Public domain (United States Government Work). Usable.
``sdu21-ad-*``
    CC BY-NC-SA 4.0 — non-commercial *and* share-alike. Barred.
``plod-cw-*``
    CC BY-SA 4.0 — share-alike, and section 3(b) reaches Adapted Material, so
    the derived table would inherit BY-SA. Barred, as that asset's note in
    ``data/LICENSES.md`` already records.

MED1250 is therefore the source, and :func:`_derive_guard` checks that against
``tools.fetch_data.ASSETS`` rather than trusting this paragraph.

Two independent arguments make the result shippable, and both are worth stating
because either alone would be thinner than it looks. The first is the licence:
the NLM notice places no restriction on use or reproduction. The second is that
the derived table contains **no text from the corpus** — every key is one of our
own short-form group labels or one of our own strategy names, and every value is
a count or a float. There is nothing in it to have a licence.

Which half, and why it matters
------------------------------
The **development half only**, under ``bench/run_cascade.py``'s frozen split
seed, imported from there rather than repeated here. Deriving from the whole
corpus would be easier and would quietly poison every MED1250 number this
project publishes: no held-out figure can describe a table that has seen the
held-out half. Deriving from the dev half means the shipped table *is* the table
D-010's threshold sweep was measured on.

Usage
-----
::

    python tools/build_reliability_table.py                 # write the resource
    python tools/build_reliability_table.py --check         # verify it is current
    python tools/build_reliability_table.py --cross-check    # against Ab3P's table

``--check`` is the one that matters in review: it rebuilds from source and
compares byte for byte, so a resource edited by hand fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RESOURCE_DIR = REPO_ROOT / "src" / "acronymkit" / "resources"

sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_data import BY_KEY  # noqa: E402

#: Registry key of the corpus the table is derived from.
SOURCE_ASSET = "med1250"

#: Registry key of the published table used only by ``--cross-check``.
REFERENCE_ASSET = "ab3p-prec"

#: Name of the resource written into the package.
RESOURCE_NAME = "pseudo_precision_en.json"

#: Decimal places kept for each estimate. Ab3P publishes six and the extra
#: digits of a Python float carry no information here -- they are noise from a
#: division, and writing them would make the file's bytes depend on the last bit
#: of a floating-point result rather than on the measurement.
PRECISION_DIGITS = 6

#: Mismatched windows paired with each short form when measuring the chance
#: rate. Matches ``bench/run_cascade.py``'s default, so the shipped table is the
#: table whose calibration that runner reports.
CHANCE_TRIALS = 3


def _derive_guard(asset_key: str, destination: Path) -> None:
    """Refuse to derive a packaged resource from a licence-tainted asset.

    The mirror of ``tools/build_lexicons.py``'s ``_vendor_guard``, for the other
    question: that one asks whether an asset's *bytes* may ship, this one asks
    whether something computed from them may. A share-alike corpus answers no to
    the second even when it answers yes to the first, which is the trap this
    function exists to make mechanical.

    Args:
        asset_key: Key into the :mod:`tools.fetch_data` registry.
        destination: Where the derived resource would be written.

    Raises:
        SystemExit: If ``destination`` is inside the packaged resource directory
            and the source asset's licence does not permit shipping a derived
            work.
    """
    asset = BY_KEY[asset_key]
    try:
        destination.resolve().relative_to(RESOURCE_DIR.resolve())
    except ValueError:
        return  # outside the package: the user's own machine, their choice
    if not asset.derivable:
        raise SystemExit(
            f"refusing to derive a packaged resource from '{asset_key}'.\n"
            f"  licence: {asset.licence}\n"
            f"  {asset.vendor_note}\n"
            "A statistics table computed from a share-alike or non-commercial "
            "corpus is Adapted Material and inherits its terms. Write it "
            f"somewhere outside {RESOURCE_DIR} instead."
        )


def _source_documents() -> tuple[list, int]:
    """Load the MED1250 development half using the benchmark's frozen split.

    Imported from ``bench`` rather than reimplemented: a second copy of the
    split would drift, and if it drifted the shipped table would stop being the
    one ``bench/run_cascade.py`` reports held-out numbers for.

    Returns:
        ``(development documents, split seed)``.
    """
    from bench import corpora
    from bench.run_cascade import SPLIT_SEED, split_corpus

    source = DATA_DIR / BY_KEY[SOURCE_ASSET].filename
    if not source.exists():
        raise SystemExit(f"missing {source}. Run: python tools/fetch_data.py {SOURCE_ASSET}")
    development, _test = split_corpus(corpora.load("med1250"))
    return development, SPLIT_SEED


def build(*, chance_trials: int = CHANCE_TRIALS) -> dict[str, Any]:
    """Derive the table and wrap it with its provenance.

    Args:
        chance_trials: Mismatched windows paired with each short form when
            measuring the chance firing rate.

    Returns:
        The JSON-ready document: a ``provenance`` block followed by exactly the
        keys :meth:`acronymkit._pseudo_precision.PrecisionTable.from_dict`
        reads.
    """
    from acronymkit._pseudo_precision import estimate_precisions, harvest_candidates

    asset = BY_KEY[SOURCE_ASSET]
    development, split_seed = _source_documents()
    candidates = harvest_candidates(document.text for document in development)
    table = estimate_precisions(candidates, chance_trials=chance_trials)
    payload = table.to_dict()

    values = {
        group: {
            name: round(value, PRECISION_DIGITS) for name, value in sorted(per_strategy.items())
        }
        for group, per_strategy in sorted(payload["values"].items())
    }
    support = {
        group: dict(sorted(per_strategy.items()))
        for group, per_strategy in sorted(payload["support"].items())
    }

    provenance = {
        "_comment": (
            "JSON has no comment syntax, so the header this file would otherwise "
            "carry is data. Generated by tools/build_reliability_table.py; do not "
            "edit by hand, and run that script with --check to prove it is current."
        ),
        "source_asset": asset.key,
        "source_url": asset.url,
        "source_sha256": asset.sha256,
        "source_licence": asset.licence,
        "source_licence_url": asset.licence_url,
        "attribution": asset.attribution,
        "derived_from": (
            "The development half of MED1250 under bench/run_cascade.py's frozen "
            "split seed. Raw text only: the estimator reads no annotation, and the "
            "gold pairs in the corpus file are never opened."
        ),
        "domain": "English biomedical abstracts (MEDLINE records)",
        "caveat": (
            "A prior, not a calibration. These estimates describe how the matching "
            "strategies behave on MEDLINE abstracts; on legal, financial or "
            "internal-documentation text they are a starting point of unmeasured "
            "accuracy. Derive your own with estimate_precisions() if you have text."
        ),
        "contains_source_text": False,
        "split_seed": split_seed,
        "development_documents": len(development),
        "chance_trials": chance_trials,
        "estimate_decimals": PRECISION_DIGITS,
        "generator": "tools/build_reliability_table.py",
    }

    return {
        "provenance": provenance,
        "seed": payload["seed"],
        "candidates": payload["candidates"],
        "values": values,
        "support": support,
    }


def render(document: dict[str, Any]) -> str:
    """Serialise the document exactly as the resource is written.

    ``sort_keys`` is off so ``provenance`` stays at the top of the file, where a
    header comment would be in any format that had them.

    Args:
        document: Output of :func:`build`.

    Returns:
        The file's contents, newline-terminated.
    """
    return json.dumps(document, indent=1, sort_keys=False) + "\n"


def write(destination: Path) -> Path:
    """Build and write the resource.

    Args:
        destination: Output path.

    Returns:
        The path written.
    """
    _derive_guard(SOURCE_ASSET, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # ``Path.write_text`` grew ``newline`` in 3.10; ``requires-python`` is ``>=3.9``.
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(render(build()))
    return destination


def check(destination: Path) -> int:
    """Rebuild from source and compare with what is on disk.

    Args:
        destination: The resource to verify.

    Returns:
        Process exit code: ``0`` when the file is exactly what the source
        produces today.
    """
    if not destination.is_file():
        print(f"MISSING {destination}", file=sys.stderr)
        return 1
    expected = render(build())
    actual = destination.read_text(encoding="utf-8")
    if expected == actual:
        print(f"ok  {destination.name} matches a fresh build ({len(actual):,} B)")
        return 0
    print(
        f"STALE {destination.name}: on disk {len(actual):,} B, fresh build "
        f"{len(expected):,} B. Regenerate with "
        "`python tools/build_reliability_table.py`.",
        file=sys.stderr,
    )
    return 1


def _read_reference() -> dict[str, dict[str, float]]:
    """Read Ab3P's published table, grouped the way ours is.

    Their rows are ``<class> <length> <strategy> <estimate>`` with classes
    ``Al``/``Num``/``Spec``, which map onto our ``al``/``num``/``spec`` group
    prefixes.

    Returns:
        ``{group: {ab3p strategy name: estimate}}``.

    Raises:
        SystemExit: If the asset has not been fetched.
    """
    path = DATA_DIR / BY_KEY[REFERENCE_ASSET].filename
    if not path.exists():
        raise SystemExit(f"missing {path}. Run: python tools/fetch_data.py {REFERENCE_ASSET}")
    grouped: dict[str, dict[str, float]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != 4:
            continue
        kind, length, name, estimate = fields
        grouped.setdefault(f"{kind.lower()}:{length}", {})[name] = float(estimate)
    return grouped


def cross_check() -> int:
    """Compare our derived ordering against Ab3P's published one.

    What can honestly be compared is the **range** per bucket, not rule against
    rule. Ab3P's seventeen named rules and our parameterised family are not the
    same set, so a number-to-number comparison at the loose end measures a
    difference in rule definitions as much as anything else — the correction in
    D-010 says exactly this, and repeating the error here would be worse than
    not checking at all.

    What the range comparison does test is real: whether a table derived from
    unlabelled text puts its strictest rules where a labelled estimate puts
    theirs, and whether both fall the same way as short forms get shorter.

    Returns:
        Process exit code; always ``0``. This reports, it does not gate.
    """
    ours = build()["values"]
    theirs = _read_reference()
    print("Range per bucket. Rule sets differ, so only the spread is comparable.\n")
    print(
        f"{'group':<8} {'ours max':>9} {'ours min':>9} {'Ab3P max':>9} {'Ab3P min':>9}  n(ours)/n(Ab3P)"
    )
    print("-" * 72)
    for group in sorted(set(ours) | set(theirs)):
        mine = ours.get(group, {})
        yours = theirs.get(group, {})
        if not mine or not yours:
            print(
                f"{group:<8} {'-' if not mine else 'present':>9} "
                f"{'':>9} {'-' if not yours else 'present':>9} {'':>9}  "
                f"{len(mine)}/{len(yours)}"
            )
            continue
        print(
            f"{group:<8} {max(mine.values()):9.4f} {min(mine.values()):9.4f} "
            f"{max(yours.values()):9.4f} {min(yours.values()):9.4f}  "
            f"{len(mine)}/{len(yours)}"
        )
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point.

    Args:
        argv: Argument vector; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="destination path; defaults to the packaged resource",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild and compare with the file on disk instead of writing",
    )
    parser.add_argument(
        "--cross-check",
        action="store_true",
        help="compare the derived ordering against Ab3P's published table",
    )
    args = parser.parse_args(argv)

    destination = args.output or (RESOURCE_DIR / RESOURCE_NAME)

    if args.cross_check:
        return cross_check()
    if args.check:
        return check(destination)

    written = write(destination)
    size = written.stat().st_size
    print(f"wrote {written} ({size:,} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
