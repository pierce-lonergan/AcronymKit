#!/usr/bin/env python3
"""Tier 0 imports, generates and extracts with no optional dependency present.

Why this is a script and not a heredoc
--------------------------------------
It was a ``python - <<'PY'`` block inside ``.github/workflows/ci.yml``'s
``zero-dependency`` job. ``.github/gates.toml`` recorded the consequence:
``kind = "inline"``, *"the mutation is obvious and cheap once the probe is a
script -- an eager `import click` in `src/acronymkit/__init__.py` -- and it
cannot be run against the gate as it stands without copying the gate."* This is
that script; the mutation is registered and runs against **this** file.

What it asserts
---------------
Two things, and they fail differently depending on what the environment holds:

1. **Tier 0 runs at all.** ``AcronymEngine(Config(engine_tier=ZERO_DEPENDENCY))``
   generates ``PDF`` from *Portable Document Format* and extracts ``NASA`` from
   a parenthetical.
2. **Nothing optional got into ``sys.modules``.** ``spacy``, ``nltk``, ``click``,
   ``onnxruntime``, ``transformers`` and ``numpy`` are the packages a Tier 0
   install does not have; any of them present after the import means the base
   install has acquired a dependency it does not declare.

**The two halves catch the same defect in different environments, and that is
worth stating because it decides what the mutation demonstrates.** The
registered mutation adds an eager ``import click`` at module scope. On the
runner this gate runs on, no extras are installed, so that import *raises* and
assertion 1 fires. On a developer machine, ``click`` is usually installed, the
import succeeds, and assertion 2 fires. Same defect, same gate, two mechanisms
-- so this file routes both through one marker rather than letting the verdict
depend on which machine ran it.

Usage::

    python tools/gate_tier_zero.py

Imports nothing but the standard library and ``acronymkit`` itself -- and the
``acronymkit`` import is inside the guarded block, because a gate that dies at
module scope prints a traceback instead of a verdict.

Exit codes:
    ``0`` Tier 0 is pure and works, ``1`` it is not.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence

#: Top-level package names a Tier 0 install must not have pulled in. Kept as the
#: first component of a dotted name: ``numpy.core`` leaking is ``numpy``
#: leaking.
OPTIONAL_PACKAGES = frozenset({"spacy", "nltk", "click", "onnxruntime", "transformers", "numpy"})

#: Printed on every failure, and required by the registered mutation's
#: ``expect_failure_matching``. See ``tools/gate_schema_copies.py`` for why a
#: non-zero exit is not on its own an attributable verdict.
FAILURE_MARKER = "TIER 0 PURITY FAILED"


def check() -> List[str]:
    """Every Tier 0 problem, as a list of sentences. Empty means pure."""
    problems: List[str] = []
    try:
        from acronymkit import AcronymEngine, Config
        from acronymkit.enums import EngineTier
    except Exception as error:  # ImportError, and anything a module body raises
        return [
            f"{FAILURE_MARKER}: importing acronymkit raised "
            f"{type(error).__name__}: {error}. With no extras installed the base "
            "package must import on its own; something at module scope now needs "
            "an optional dependency."
        ]

    try:
        engine = AcronymEngine(Config(engine_tier=EngineTier.ZERO_DEPENDENCY))
        result = engine.generate("Portable Document Format")
        print(result.primary_acronym, result.score)
        if result.primary_acronym != "PDF":
            problems.append(
                f"{FAILURE_MARKER}: Tier 0 generated {result.primary_acronym!r} for "
                "'Portable Document Format', expected 'PDF'."
            )
        pairs = engine.extract_definitions(
            "The National Aeronautics and Space Administration (NASA) launched it."
        )
        if not pairs or pairs[0].short_form != "NASA":
            problems.append(
                f"{FAILURE_MARKER}: Tier 0 extraction returned {pairs!r}, expected a first "
                "pair whose short form is 'NASA'."
            )
    except Exception as error:
        problems.append(
            f"{FAILURE_MARKER}: Tier 0 raised {type(error).__name__}: {error} while "
            "generating or extracting with no extras installed."
        )

    leaked = sorted(m for m in sys.modules if m.split(".")[0] in OPTIONAL_PACKAGES)
    if leaked:
        problems.append(
            f"{FAILURE_MARKER}: Tier 0 pulled in optional dependencies: {leaked}. "
            "The base install must not import any of "
            f"{sorted(OPTIONAL_PACKAGES)} at module scope."
        )
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)

    problems = check()
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    print("Tier 0 purity OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
