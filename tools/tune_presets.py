#!/usr/bin/env python3
"""Grid-search the ``S(A, T)`` coefficients against a canonical corpus.

The preset weight vectors in :data:`acronymkit.config.STRATEGY_WEIGHTS` are not
hand-picked. They are the result of this sweep, and this script exists so the
claim is falsifiable: anyone can re-run it and get the same region.

What it measures
----------------
A corpus of textbook initialisms whose expansion every reader already knows.
The default configuration must return the conventional acronym as the *primary*
result for all of them. That is a weak requirement — it says nothing about
exotic phrases — but it is a requirement the naive objective fails, which makes
it a useful floor.

Why the region matters more than the point
------------------------------------------
A single winning vector proves nothing: with enough knobs, something always
fits. What matters is whether the winners form a broad plateau or an isolated
spike. A plateau means the defaults are robust to the corpus; a spike means they
are overfitted to it. The script reports the plateau extent for exactly this
reason.

This history is worth keeping: the v0.1.0 weights scored 16/16 against a
model-authored word list and only 13/16 once the real SCOWL lexicon replaced it,
because a larger dictionary makes ``Lambda(A)`` fire far more often. Tuning
against invented data produced invented confidence.

Usage
-----
::

    python tools/tune_presets.py                     # sweep and report
    python tools/tune_presets.py --check             # verify shipped presets
    python tools/tune_presets.py --strategy balanced_pronounceable
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from acronymkit import AcronymEngine, Config  # noqa: E402
from acronymkit.config import STRATEGY_WEIGHTS, ScoringWeights  # noqa: E402
from acronymkit.enums import ScoringStrategy  # noqa: E402

#: Phrase -> the acronym a competent human would produce. Kept identical to
#: ``tests/conftest.CANONICAL_ACRONYMS`` so the test suite pins what this tunes.
CANONICAL: tuple[tuple[str, str], ...] = (
    ("Application Programming Interface", "API"),
    ("Portable Document Format", "PDF"),
    ("National Aeronautics and Space Administration", "NASA"),
    ("Hyper Text Markup Language", "HTML"),
    ("Random Access Memory", "RAM"),
    ("Central Processing Unit", "CPU"),
    ("Graphics Processing Unit", "GPU"),
    ("Self Contained Underwater Breathing Apparatus", "SCUBA"),
    ("Light Amplification by Stimulated Emission of Radiation", "LASER"),
    ("Structured Query Language", "SQL"),
    ("Customer Relationship Management", "CRM"),
    ("Quality Assurance", "QA"),
    ("Transmission Control Protocol", "TCP"),
    ("Simple Object Access Protocol", "SOAP"),
    ("Basic Input Output System", "BIOS"),
    ("Read Only Memory", "ROM"),
)

#: Swept axes. ``alpha`` is fixed at 1.0: the objective is scale-invariant up to
#: a common factor, so only the ratios matter and one axis can be pinned.
BETA_VALUES = (0.25, 0.5, 1.0, 2.0)
GAMMA_VALUES = (6.0, 10.0, 14.0, 20.0)
DELTA_VALUES = (10.0, 15.0, 20.0, 26.0)
LENGTH_PENALTY_VALUES = (4.0, 6.0, 8.0, 10.0)
PREFERRED_LENGTH_VALUES = (1, 2, 3)


def score_vector(weights: ScoringWeights) -> tuple[int, list[tuple[str, str, str]]]:
    """Count canonical hits for one weight vector.

    Args:
        weights: Coefficients to evaluate.

    Returns:
        ``(hits, failures)`` where each failure is
        ``(phrase, expected, actual)``.
    """
    engine = AcronymEngine(Config(scoring_strategy=ScoringStrategy.CUSTOM, scoring_weights=weights))
    failures: list[tuple[str, str, str]] = []
    for phrase, expected in CANONICAL:
        try:
            actual = engine.generate(phrase).primary_acronym
        except Exception as exc:
            actual = f"<{type(exc).__name__}>"
        if actual != expected:
            failures.append((phrase, expected, actual))
    return len(CANONICAL) - len(failures), failures


def sweep() -> list[tuple[int, ScoringWeights]]:
    """Evaluate the full grid.

    Returns:
        ``(hits, weights)`` for every vector, unsorted.
    """
    results: list[tuple[int, ScoringWeights]] = []
    grid = itertools.product(
        BETA_VALUES,
        GAMMA_VALUES,
        DELTA_VALUES,
        LENGTH_PENALTY_VALUES,
        PREFERRED_LENGTH_VALUES,
    )
    for beta, gamma, delta, length_penalty, preferred in grid:
        weights = ScoringWeights(
            alpha=1.0,
            beta=beta,
            gamma=gamma,
            delta=delta,
            length_penalty=length_penalty,
            preferred_length=preferred,
        )
        hits, _ = score_vector(weights)
        results.append((hits, weights))
    return results


def _report(results: list[tuple[int, ScoringWeights]]) -> Optional[ScoringWeights]:
    """Print the plateau summary and return the recommended vector."""
    best = max(hits for hits, _ in results)
    winners = [w for hits, w in results if hits == best]
    print(f"grid: {len(results)} vectors over {len(CANONICAL)} canonical cases")
    print(
        f"best: {best}/{len(CANONICAL)}   plateau: {len(winners)}/{len(results)} vectors reach it"
    )
    if best < len(CANONICAL):
        print("\nWARNING: no vector satisfies the whole corpus. Either the corpus")
        print("grew a genuinely ambiguous case, or the objective needs a new term.")
    print("\nplateau extent:")
    for label, values in (
        ("beta", sorted({w.beta for w in winners})),
        ("gamma", sorted({w.gamma for w in winners})),
        ("delta", sorted({w.delta for w in winners})),
        ("length_penalty", sorted({w.length_penalty for w in winners})),
        ("preferred_length", sorted({w.preferred_length for w in winners})),
    ):
        print(f"  {label:17} {values}")
    if not winners:
        return None
    # Prefer the plateau centroid: the vector closest to the median of each axis
    # is the least likely to sit on an edge that a corpus change would push off.
    medians = [
        sorted(w.beta for w in winners)[len(winners) // 2],
        sorted(w.gamma for w in winners)[len(winners) // 2],
        sorted(w.delta for w in winners)[len(winners) // 2],
        sorted(w.length_penalty for w in winners)[len(winners) // 2],
        sorted(w.preferred_length for w in winners)[len(winners) // 2],
    ]

    def distance(w: ScoringWeights) -> tuple[float, ...]:
        return (
            abs(w.beta - medians[0]),
            abs(w.gamma - medians[1]),
            abs(w.delta - medians[2]),
            abs(w.length_penalty - medians[3]),
            abs(w.preferred_length - medians[4]),
        )

    pick = sorted(winners, key=distance)[0]
    print(
        f"\nrecommended (plateau centroid): alpha=1.0 beta={pick.beta} gamma={pick.gamma} "
        f"delta={pick.delta} length_penalty={pick.length_penalty} "
        f"preferred_length={pick.preferred_length}"
    )
    return pick


def _mean_pronounceability(strategy: ScoringStrategy) -> float:
    """Mean pronounceability of the primary result across the canonical corpus."""
    engine = AcronymEngine(Config(scoring_strategy=strategy))
    scores = [engine.generate(phrase).primary.pronounceability_score for phrase, _ in CANONICAL]
    return sum(scores) / len(scores)


def check_shipped() -> int:
    """Verify the shipped presets still behave as documented.

    Two different requirements, because the presets have two different jobs:

    * ``STRICT_INITIALISM`` — the default — **must** reproduce the whole
      canonical corpus. This is the contract every user relies on when they call
      ``generate()`` without configuring anything.
    * ``BALANCED_PRONOUNCEABLE`` **must not** be required to. Against the real
      SCOWL lexicon no vector both weights dictionary hits meaningfully and
      returns every textbook initialism, so demanding both is asking the preset
      not to do its job. What is checked instead is that it actually *trades*:
      its mean pronounceability must exceed the strict preset's. A "balanced"
      preset that behaved identically to strict would be dead weight.

    Returns:
        Process exit code: non-zero if either contract is broken.
    """
    exit_code = 0

    hits, failures = score_vector(STRATEGY_WEIGHTS[ScoringStrategy.STRICT_INITIALISM])
    status = "ok" if hits == len(CANONICAL) else "FAIL"
    print(f"  {status:4} strict_initialism (default)   {hits}/{len(CANONICAL)} canonical")
    for phrase, expected, actual in failures:
        print(f"         expected {expected:6} got {actual:8} <- {phrase}")
    if hits != len(CANONICAL):
        exit_code = 1

    strict_pron = _mean_pronounceability(ScoringStrategy.STRICT_INITIALISM)
    balanced_pron = _mean_pronounceability(ScoringStrategy.BALANCED_PRONOUNCEABLE)
    _, balanced_failures = score_vector(STRATEGY_WEIGHTS[ScoringStrategy.BALANCED_PRONOUNCEABLE])
    trades = balanced_pron > strict_pron
    status = "ok" if trades else "FAIL"
    print(
        f"  {status:4} balanced_pronounceable        "
        f"pronounceability {balanced_pron:.3f} vs strict {strict_pron:.3f}"
    )
    print(
        f"         deviates from the corpus on {len(balanced_failures)} case(s) "
        f"by design: {', '.join(f'{e}->{a}' for _, e, a in balanced_failures) or 'none'}"
    )
    if not trades:
        print("         a balanced preset that does not trade is redundant with strict")
        exit_code = 1

    return exit_code


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the shipped presets against the corpus and exit non-zero on regression",
    )
    args = parser.parse_args(argv)

    if args.check:
        return check_shipped()

    _report(sweep())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
