#!/usr/bin/env python3
"""Assert an extracted sdist carries the files this project's evidence rests on.

Why this is a script and not five ``test -f`` lines
---------------------------------------------------
``.github/workflows/ci.yml``'s ``build`` job ran five ``test -f`` lines and a
whole pytest run inside one step. The register splits those into two gates
because they have measurably different coverage of the five historical
breakages -- two of five against four of five -- and *"registering the step as
one gate would have published a single number true of neither."*

The ``test -f`` half is a list of names, and a list of names is the wrong shape;
that is written down beside ``gates.sdist_file_list`` and is still true. What
was *also* true, and worse, is that ``tools/gate_packaging_mutation.py`` kept a
second copy of the list so it could reproduce the step. **A harness that
re-implements the gate is testing its own copy.** The copy is gone: this file is
the list, ``ci.yml`` invokes it, and the harness imports :data:`REQUIRED`.

Each entry carries the reason it is here, and the reason is printed on failure
rather than being a comment somebody has to go and find. ``data/LICENSES.md`` is
the one to read twice: it is held by this list **and by nothing else in the
repository**, measured -- the extracted-tree suite passes with it gone, because
no test reads it, while two shipped documents cite it as evidence.

Usage::

    python tools/gate_sdist_files.py /tmp/sdist

Standard library only.

Exit codes:
    ``0`` every required path is present, ``1`` at least one is missing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

#: Path in the extracted sdist -> why its absence is a defect.
#:
#: Ordered, because the failure report reads better in the order the ``test -f``
#: lines were written. Adding a name here is cheap and is not the fix for this
#: gate's shape: it is a list, it will always be a list, and the thing that
#: catches what the list does not is the extracted-tree suite run beside it.
REQUIRED: Tuple[Tuple[str, str], ...] = (
    ("tests/conftest.py", "the artifact's own test suite cannot start without it"),
    (
        "schemas/acronym-engine-result.schema.json",
        "the documented interchange contract is absent from the artifact that claims it",
    ),
    (
        "bench/results.json",
        "the shipped docs make claims the shipped checker then cannot back",
    ),
    (
        "data/LICENSES.md",
        "README.md and SECURITY.md link to it as the evidence for the pinned-and-"
        "checksummed asset claim, so without it that link resolves to nothing for "
        "anyone holding a distribution. Nothing else in this repository notices its "
        "absence: the extracted-tree suite passes with it gone.",
    ),
    (
        "tests/airgap_socket_guard.py",
        "the point of shipping the air-gap proof is that an enterprise can re-run it "
        "in their own environment",
    ),
)

#: Printed on every failure. See ``tools/gate_schema_copies.py`` for why a
#: non-zero exit is not on its own an attributable verdict.
FAILURE_MARKER = "SDIST FILE LIST FAILED"


def missing(tree: Path) -> List[Tuple[str, str]]:
    """Every required path absent from ``tree``, with its reason."""
    return [(name, why) for name, why in REQUIRED if not (tree / name).is_file()]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tree", type=Path, help="root of the extracted sdist")
    args = parser.parse_args(argv)

    if not args.tree.is_dir():
        print(f"{FAILURE_MARKER}: {args.tree} is not a directory", file=sys.stderr)
        return 1
    absent = missing(args.tree)
    if absent:
        for name, why in absent:
            print(f"{FAILURE_MARKER}: {name} missing from sdist: {why}", file=sys.stderr)
        return 1
    print(f"{args.tree}: all {len(REQUIRED)} required paths present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
