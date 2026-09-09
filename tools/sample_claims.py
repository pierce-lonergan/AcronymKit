#!/usr/bin/env python3
"""Draw a churn-weighted stratified sample of this project's unbacked claims.

WHAT THIS REPLACES, AND WHY THE OLD NUMBER DOES NOT COME WITH IT
================================================================
R15 -- the sampled-verification round -- has run five times. Every workstream
submits twelve non-load-bearing checkable sentences, a sampler draws twenty-four
of them under a published seed, and each is re-checked against running code
rather than against the document that states it. The five rounds returned
``5, 5, 6, 2, 2`` not true out of twenty-four each: **20 of 120 = 16.67 %,
Wilson 95 % [11.06, 24.35]**.

**That series is CLOSED, and this module is not a continuation of it.** Round
five measured the instrument rather than the project and the measurement is why:
a fifth point moved the interval's half-width by ``1.11`` points while moving
the estimate by ``2.08``, and reaching a half-width of three points needs about
``600`` draws -- twenty-five rounds of twenty-four in total, twenty more than
have been run. Pooling further draws of twenty-four is not a route to a usable
number.

THE PART THAT MUST NOT BE PAPERED OVER
--------------------------------------
The successor below draws from a **different population**, so the five-round
figure cannot be carried across the change and this module refuses to print a
pooled rate that spans it.

===================  ==========================================================
old frame            twenty-four sentences drawn uniformly from the pool every
                     workstream *submitted about its own round*: 12 per
                     workstream, 36 in a three-workstream round.
this frame           claim-shaped numbers **in the repository's scanned
                     documents** that no arming rule backs, partitioned by how
                     recently their file was touched, and drawn with a
                     deliberately unequal allocation across those strata.
===================  ==========================================================

Different unit (a submitted sentence against a number in a file), different
population (this round's self-report against the whole scanned tree), different
inclusion probabilities (uniform against stratified). A series silently
redefined mid-flight is the worst outcome available here, so the new series
**starts at n = 0** and says so on every run.

WHAT THE DISCONTINUITY BUYS, AND WHAT IT COSTS -- STATED BEFORE ANY DRAW
------------------------------------------------------------------------
The maintainer's argument for churn weighting is that re-measuring cold
invariant text is wasted attention: a paragraph nobody has edited in four months
was already checked, and the claims most likely to be wrong are the ones written
last week. That argument is about **relevance**, and it is a good one.

It is **not** an argument about precision, and this module will not let it be
read as one. Stratified sampling beats simple random sampling only when the
strata differ in the quantity being measured. If churned and cold text carry the
same not-true rate, an unequal allocation makes the **repository-wide** estimate
*less* precise per draw than a uniform one, because the design-weighted
estimator pays a variance penalty for over-sampling a small stratum.
:func:`design_effect` computes that penalty from the live stratum sizes; it is
printed on every draw, whether or not it flatters the design.

So the honest summary of the change is: **the repository-wide question gets
harder to answer and the "is the work just done described correctly" question
becomes answerable at all.** The second is the question a round actually needs.

WHAT WOULD MAKE THE DISCONTINUITY WORTH IT (pre-registered)
-----------------------------------------------------------
1. The ``round`` stratum's rate must separate from the ``cold`` stratum's by
   more than either interval's half-width, in at least two rounds. If the two
   strata measure the same rate, churn weighting has bought relevance and
   nothing else, and this module's own design-effect line is the argument
   against it.
2. The design-weighted repository estimate must remain computable. A frame that
   can only answer the narrow question has *removed* a measurement rather than
   replaced it, which is why the ``cold`` stratum keeps a non-zero allocation
   instead of being dropped.
3. Five rounds of this must reach a narrower interval **on the round stratum**
   than five rounds of the old frame reached on its own quantity. If they do
   not, the change was a rename.

Nothing here is imported by the library and nothing here touches the network.

Usage::

    python tools/sample_claims.py --frame            # strata and their sizes
    python tools/sample_claims.py --draw --seed 20260909
    python tools/sample_claims.py --estimate GRADED.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The strata, most-churned first. Ordered, because the allocation below is
#: positional and a reordered tuple would silently re-aim the whole draw.
STRATA: Tuple[str, ...] = ("round", "recent", "cold")

#: How many of a sample of :data:`DEFAULT_SIZE` each stratum gets.
#:
#: **THE COLD STRATUM IS NOT ZERO, AND THAT IS THE DESIGN.** Dropping it would
#: make the repository-wide rate permanently unmeasurable -- the frame would
#: answer only the narrow question and would have removed a measurement rather
#: than replaced one. Four draws a round is not much; it is the difference
#: between a quantity with a wide interval and a quantity with none.
DEFAULT_ALLOCATION: Dict[str, int] = {"round": 12, "recent": 8, "cold": 4}

#: The per-round draw. Twenty-four, the same as the old frame -- deliberately,
#: because it holds the GRADER'S EFFORT fixed across the discontinuity. The
#: statistic changes; the cost of a round does not, so a later comparison of
#: what the two frames bought per unit of attention is possible.
DEFAULT_SIZE = 24

#: How many commits back ``recent`` reaches. A round is roughly one commit here,
#: so twenty is about the last twenty rounds -- long enough to catch a claim
#: written two rounds ago and re-quoted since, short enough that a file nobody
#: has touched this quarter falls to ``cold``.
DEFAULT_RECENT_COMMITS = 20

#: Verdicts a grader may return. ``UNCHECKABLE`` is IN the denominator and NOT
#: in the numerator, which is the convention D-115 graded round five under: a
#: claim nobody can check is not a claim shown to be true, and excluding it
#: would let a round improve its rate by making claims harder to check.
VERDICTS: Tuple[str, ...] = ("TRUE", "FALSE", "MISLEADING", "UNCHECKABLE")

#: A bare four-digit integer in this range is a **date**, not a claim, and is
#: excluded from the frame.
#:
#: **ADDED AFTER THE FIRST EXPLORATORY DRAW AND BEFORE THE FIRST GRADED ONE,
#: WHICH IS THE ONLY MOMENT IT IS FREE.** ``check_claims``' own docstring says
#: the residue is "mostly years, defaults and rank cutoffs"; the first draw
#: under seed 20260909 put two of them in front of a grader and made the point
#: concretely. Because the successor series stands at ``n = 0``, refining the
#: frame costs nothing today and would cost the whole series after round one --
#: so it is done now and recorded here rather than deferred into a footnote.
#:
#: It is deliberately narrow, and it applies to the **unarmed** residue only.
#: ``628`` of the frame's numbers are one- or two-digit integers and many of
#: those ARE claims ("14 records", "31 came out of"), so no blanket
#: small-integer rule is applied. Measured effect of this one: the frame falls
#: from ``2182`` to ``2054``, so ``128`` numbers leave. ``130`` numbers in the
#: tree are year-shaped and ``2`` of them are on the DEFERRED ledger -- armed by
#: a metric keyword or a unit, so they are measurements that happen to look like
#: years, and dropping those would hide a real debt.
YEAR_LIKE = re.compile(r"^(?:19|20|21)\d{2}$")

#: Which verdicts count as **not true**. Fixed here, before any draw, because
#: D-115 records that round four's boundary rule is not on disk anywhere and
#: "graded under the rule somebody else wrote" turned out to mean "graded under
#: this grader's reading of a paragraph".
NOT_TRUE: Tuple[str, ...] = ("FALSE", "MISLEADING")

#: The closed series, recorded here so that a future round comparing against it
#: is comparing against a number with a name on it rather than a memory.
#:
#: ``wilson_pct`` is TRANSCRIBED from D-115 rather than computed, deliberately:
#: ``tests/test_sample_claims.py`` recomputes it from ``per_round`` with
#: :func:`wilson` and requires the two to agree to two decimals. A constant
#: derived from the function it is checked against would check nothing.
CLOSED_SERIES: Dict[str, Any] = {
    "rounds": 5,
    "draws": 120,
    "not_true": 20,
    "rate_pct": 100.0 * 20 / 120,
    "wilson_pct": (11.06, 24.35),
    "per_round": (5, 5, 6, 2, 2),
    "frame": "uniform draw from workstream-submitted claims_for_sampling sentences",
}


class SamplerError(Exception):
    """The frame could not be built."""


def _load_check_claims() -> object:
    """Import ``tools/check_claims.py`` by path.

    ``tools/`` is a directory of scripts and must not become a package; the same
    mechanism ``tests/test_gate_manifest.py`` uses. The population this module
    samples is *exactly* the residue that tool already computes, and
    re-implementing the scanner would create a second definition of "a claim"
    for the two to disagree about.
    """
    path = REPO_ROOT / "tools" / "check_claims.py"
    if not path.is_file():  # pragma: no cover - source checkouts only
        raise SamplerError(f"{path} is not here; this tool belongs to a checkout")
    spec = importlib.util.spec_from_file_location("_check_claims_for_sampling", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise SamplerError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git(args: Sequence[str], root: Path) -> List[str]:
    """Run git and return its stdout lines, or ``[]`` if git cannot answer.

    A missing git, a missing ref and a tarball checkout all land here and all
    mean the same thing: **churn is unknown**. The caller turns that into an
    all-``cold`` frame and says so, rather than guessing, because a frame that
    silently reports every file as untouched would draw a uniform sample while
    printing a stratified header.
    """
    try:
        finished = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:  # pragma: no cover - git absent
        return []
    if finished.returncode != 0:
        return []
    return [line.strip() for line in finished.stdout.splitlines() if line.strip()]


def churn(
    root: Path = REPO_ROOT,
    base: Optional[str] = None,
    recent_commits: int = DEFAULT_RECENT_COMMITS,
) -> Tuple[frozenset, frozenset, bool]:
    """Which files this round touched, and which the recent past did.

    Args:
        root: The checkout.
        base: The ref the current round started from. ``None`` means "the
            working tree against HEAD", which is the state a sampler is
            **actually** in when it runs at the end of a round: the work exists
            and is not committed yet.
        recent_commits: How far back ``recent`` reaches.

    Returns:
        ``(round_files, recent_files, known)``. ``known`` is ``False`` when git
        could not answer at all, and every caller must degrade loudly rather
        than treat that as "nothing changed".
    """
    if base is None:
        touched = set(_git(["diff", "--name-only", "HEAD"], root))
        touched.update(_git(["ls-files", "--others", "--exclude-standard"], root))
    else:
        touched = set(_git(["diff", "--name-only", f"{base}..HEAD"], root))
    history = set(
        _git(
            ["log", f"-n{recent_commits}", "--name-only", "--pretty=format:"],
            root,
        )
    )
    known = bool(touched or history)
    return frozenset(touched), frozenset(history) - frozenset(touched), known


@dataclass(frozen=True)
class FrameItem:
    """One claim in the frame: where it is, what it says, and which stratum."""

    identifier: str
    relative_path: str
    line_number: int
    number: str
    stratum: str
    line: str

    @property
    def sentence(self) -> str:
        """The line, trimmed to something a grader can read in a table."""
        text = " ".join(self.line.split())
        return text if len(text) <= 160 else text[:157] + "..."


@dataclass(frozen=True)
class Frame:
    """The whole population, partitioned."""

    items: Tuple[FrameItem, ...]
    churn_known: bool
    base: Optional[str]

    def sizes(self) -> Dict[str, int]:
        """``N_h`` for every stratum, zeroes included."""
        tally = dict.fromkeys(STRATA, 0)
        for item in self.items:
            tally[item.stratum] = tally.get(item.stratum, 0) + 1
        return tally

    @property
    def total(self) -> int:
        """``N``."""
        return len(self.items)


def build_frame(
    root: Path = REPO_ROOT,
    base: Optional[str] = None,
    recent_commits: int = DEFAULT_RECENT_COMMITS,
) -> Frame:
    """Every unbacked claim-shaped number in the scan set, put in a stratum.

    The population is ``check_claims``' own residue -- ``deferred`` and
    ``unexamined`` -- and nothing else. Those are exactly the numbers no gate
    has verified, which is the only population a sampler adds anything to: a
    number the claims gate backs is already checked by a machine on every push,
    and spending a grader's attention on it measures the grader.
    """
    check_claims = _load_check_claims()
    project = check_claims.Project.at(root)  # type: ignore[attr-defined]
    index = check_claims.build_index(  # type: ignore[attr-defined]
        check_claims.load_results(project)  # type: ignore[attr-defined]
    )
    allowlist = check_claims.load_allowlist(project)  # type: ignore[attr-defined]
    claims = check_claims.collect_claims(project, index, allowlist)  # type: ignore[attr-defined]
    round_files, recent_files, known = churn(root, base, recent_commits)

    items: List[FrameItem] = []
    for claim in claims:
        if claim.backing not in ("deferred", "unexamined"):
            continue
        if claim.backing == "unexamined" and YEAR_LIKE.match(claim.text):
            # A DATE IS NOT A CLAIM. Only the unarmed residue is filtered: a
            # number on the DEFERRED ledger was armed by a metric keyword or a
            # unit, so a four-digit figure there is a measurement that happens
            # to look like a year and dropping it would hide a real debt.
            continue
        relative = claim.path.resolve().relative_to(root.resolve()).as_posix()
        if not known:
            stratum = "cold"
        elif relative in round_files:
            stratum = "round"
        elif relative in recent_files:
            stratum = "recent"
        else:
            stratum = "cold"
        items.append(
            FrameItem(
                identifier=f"{relative}:{claim.line_number}:{claim.text}",
                relative_path=relative,
                line_number=claim.line_number,
                number=claim.text,
                stratum=stratum,
                line=claim.line,
            )
        )
    items.sort(key=lambda item: item.identifier)
    return Frame(items=tuple(items), churn_known=known, base=base)


def allocate(frame: Frame, size: int, allocation: Dict[str, int]) -> Dict[str, int]:
    """How many to draw from each stratum, given how many are there.

    A stratum smaller than its allocation gives what it has and the remainder
    goes to the others in :data:`STRATA` order. **The reallocation is reported,
    not silent**: a round with no churn draws its whole sample from cold text
    and the resulting estimate is a repository-wide one wearing a round-stratum
    label, which is the exact confusion this module exists to prevent.
    """
    planned = {name: min(allocation.get(name, 0), 0) for name in STRATA}
    sizes = frame.sizes()
    remaining = size
    for name in STRATA:
        want = min(allocation.get(name, 0), sizes[name], remaining)
        planned[name] = want
        remaining -= want
    for name in STRATA:
        if remaining <= 0:
            break
        extra = min(sizes[name] - planned[name], remaining)
        planned[name] += extra
        remaining -= extra
    return planned


def draw(frame: Frame, seed: int, size: int = DEFAULT_SIZE, **kwargs: object) -> List[FrameItem]:
    """The sample, reproducible from ``seed`` alone.

    ``random.Random(seed)`` and a sorted frame: the same commit and the same
    seed give the same twenty-four rows on any machine, which is what makes a
    second grader on the same sample possible. That is condition four of
    ``docs/CLAIMS-LEDGER.md``'s four, unmet for five rounds running, and it is
    unmeetable without exactly this property.
    """
    allocation = kwargs.get("allocation") or DEFAULT_ALLOCATION
    assert isinstance(allocation, dict)
    planned = allocate(frame, size, allocation)
    rng = random.Random(seed)
    chosen: List[FrameItem] = []
    for name in STRATA:
        pool = [item for item in frame.items if item.stratum == name]
        chosen.extend(rng.sample(pool, planned[name]) if planned[name] else [])
    return chosen


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> Tuple[float, float]:
    """The Wilson score interval, as percentages.

    Wilson rather than normal-approximation, for the reason every small-sample
    rate on this project uses it: at ``2 of 24`` the normal interval includes
    negative rates, and a lower bound below zero is a sentence that cannot be
    published.
    """
    if trials <= 0:
        return (0.0, 100.0)
    proportion = successes / trials
    denominator = 1 + z * z / trials
    centre = (proportion + z * z / (2 * trials)) / denominator
    half = (z / denominator) * math.sqrt(
        proportion * (1 - proportion) / trials + z * z / (4 * trials * trials)
    )
    return (100 * max(0.0, centre - half), 100 * min(1.0, centre + half))


def design_effect(frame: Frame, allocation: Dict[str, int], size: int = DEFAULT_SIZE) -> float:
    """How much precision the unequal allocation costs, at equal rates.

    The ratio of the design-weighted estimator's variance to the variance a
    simple random sample of the same size would have, computed **under the null
    that every stratum carries the same rate** -- which is the assumption that
    makes the number a property of the DESIGN rather than of any measurement:

        ``Deff = n * sum_h (W_h^2 / n_h)``   with ``W_h = N_h / N``

    Above ``1`` the churn-weighted draw is *less* precise about the repository
    than a uniform draw of the same size. That is the price of the change and
    it is printed whether or not it flatters the design. It says nothing about
    the round-stratum question, which a uniform draw of this size cannot answer
    at all.
    """
    planned = allocate(frame, size, allocation)
    total = frame.total
    drawn = sum(planned.values())
    if total <= 0 or drawn <= 0:
        return float("nan")
    sizes = frame.sizes()
    accumulated = 0.0
    for name in STRATA:
        if planned[name] <= 0:
            continue
        weight = sizes[name] / total
        accumulated += weight * weight / planned[name]
    return drawn * accumulated


def stratified_estimate(
    frame: Frame,
    graded: Dict[str, str],
    sample: Sequence[FrameItem],
) -> Dict[str, Any]:
    """Per-stratum rates and the design-weighted repository-wide rate.

    The pooled figure is ``sum_h W_h p_h``, **not** the raw count over the
    sample. Reporting the raw count would be the frame's central trap: with
    twelve of twenty-four drawn from a stratum that may hold two per cent of the
    population, the unweighted rate is an estimate of the churned text's rate
    wearing the whole repository's name.
    """
    sizes = frame.sizes()
    total = frame.total
    per_stratum: Dict[str, Dict[str, Any]] = {}
    weighted = 0.0
    variance = 0.0
    for name in STRATA:
        drawn = [item for item in sample if item.stratum == name]
        verdicts = [graded[item.identifier] for item in drawn if item.identifier in graded]
        if not verdicts:
            continue
        bad = sum(1 for verdict in verdicts if verdict in NOT_TRUE)
        proportion = bad / len(verdicts)
        weight = sizes[name] / total if total else 0.0
        weighted += weight * proportion
        variance += weight * weight * proportion * (1 - proportion) / len(verdicts)
        per_stratum[name] = {
            "N": sizes[name],
            "n": len(verdicts),
            "not_true": bad,
            "rate_pct": 100 * proportion,
            "wilson_pct": wilson(bad, len(verdicts)),
        }
    half = 1.959963984540054 * math.sqrt(variance) if variance > 0 else 0.0
    return {
        "per_stratum": per_stratum,
        "repository_rate_pct": 100 * weighted,
        "repository_half_width_pct": 100 * half,
        "graded": sum(int(item["n"]) for item in per_stratum.values()),
    }


def _render_frame(frame: Frame, allocation: Dict[str, int], size: int) -> str:
    lines: List[str] = []
    sizes = frame.sizes()
    planned = allocate(frame, size, allocation)
    lines.append(f"frame: {frame.total} unbacked claim-shaped number(s) in the scan set")
    if not frame.churn_known:
        lines.append(
            "  CHURN UNKNOWN -- git could not answer, so every file is `cold` and this draw is "
            "a uniform one with a stratified header. Do not report it as churn-weighted."
        )
    for name in STRATA:
        share = 100 * sizes[name] / frame.total if frame.total else 0.0
        lines.append(
            f"  {name:<8} N {sizes[name]:>5}  ({share:5.1f} % of the frame)  draw {planned[name]}"
        )
    lines.append(f"  design effect at equal rates: {design_effect(frame, allocation, size):.2f}")
    lines.append(
        "    above 1.00 means this allocation is LESS precise about the repository than a "
        "uniform draw of the same size. It buys the round-stratum question instead."
    )
    lines.append(
        f"  the closed series: {CLOSED_SERIES['not_true']} of {CLOSED_SERIES['draws']} = "
        f"{CLOSED_SERIES['rate_pct']:.2f} % over {CLOSED_SERIES['rounds']} rounds, Wilson "
        f"{CLOSED_SERIES['wilson_pct'][0]:.2f}-{CLOSED_SERIES['wilson_pct'][1]:.2f}. "
        "IT DOES NOT CARRY ACROSS. This frame starts at n = 0."
    )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command line entry point."""
    parser = argparse.ArgumentParser(
        prog="sample_claims.py",
        description=(
            "Draw a churn-weighted stratified sample of the claim-shaped numbers no gate "
            "backs. Successor to the fixed R15 pooling frame, which is closed."
        ),
    )
    parser.add_argument("--frame", action="store_true", help="print the strata and their sizes")
    parser.add_argument("--draw", action="store_true", help="draw a sample")
    parser.add_argument("--estimate", metavar="FILE", help="a JSON map of identifier -> verdict")
    parser.add_argument("--seed", type=int, default=None, help="the published seed")
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--base", default=None, help="the ref this round started from")
    parser.add_argument("--recent-commits", type=int, default=DEFAULT_RECENT_COMMITS)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--root", default=str(REPO_ROOT), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    root = Path(args.root)
    frame = build_frame(root, args.base, args.recent_commits)

    if args.estimate:
        graded = json.loads(Path(args.estimate).read_text(encoding="utf-8"))
        unknown = sorted(str(v) for v in graded.values() if v not in VERDICTS)
        if unknown:
            print(f"verdict(s) {unknown} are not in {list(VERDICTS)}")
            return 1
        if args.seed is None:
            print("--estimate needs the --seed the sample was drawn under")
            return 1
        sample = draw(frame, args.seed, args.size)
        result = stratified_estimate(frame, graded, sample)
        print(json.dumps(result, indent=2, default=list) if args.json else _render_estimate(result))
        return 0

    if args.draw:
        if args.seed is None:
            print("--draw needs a --seed, and the seed is published with the sample")
            return 1
        sample = draw(frame, args.seed, args.size)
        if args.json:
            print(
                json.dumps(
                    [
                        {
                            "id": item.identifier,
                            "stratum": item.stratum,
                            "path": item.relative_path,
                            "line": item.line_number,
                            "number": item.number,
                            "sentence": item.sentence,
                        }
                        for item in sample
                    ],
                    indent=2,
                )
            )
        else:
            print(_render_frame(frame, DEFAULT_ALLOCATION, args.size))
            print(f"\nsample of {len(sample)} under seed {args.seed}:")
            for item in sample:
                print(f"  [{item.stratum:<6}] {item.identifier}")
                print(f"           {item.sentence}")
        return 0

    print(_render_frame(frame, DEFAULT_ALLOCATION, args.size))
    return 0


def _render_estimate(result: Dict[str, Any]) -> str:
    lines = ["stratified estimate. A grading pass, not a benchmark measurement."]
    per_stratum = result["per_stratum"]
    assert isinstance(per_stratum, dict)
    for name in STRATA:
        row = per_stratum.get(name)
        if row is None:
            continue
        low, high = row["wilson_pct"]
        lines.append(
            f"  {name:<8} {row['not_true']:>2} of {row['n']:>2} not true = "
            f"{float(row['rate_pct']):6.2f} %  Wilson [{low:5.2f}, {high:5.2f}]  "
            f"N {row['N']}"
        )
    lines.append(
        f"  repository-wide, DESIGN-WEIGHTED: {float(result['repository_rate_pct']):.2f} % "
        f"+/- {float(result['repository_half_width_pct']):.2f} (normal approximation to a "
        "stratified estimator; Wilson has no closed form here)"
    )
    lines.append(
        "  NOT comparable with the closed 16.67 % over 120 draws: different population, "
        "different unit, different inclusion probabilities."
    )
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
