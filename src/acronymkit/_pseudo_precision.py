"""Estimate how reliable each matching strategy is, without a gold standard.

The idea, from Sohn et al. (2008)
---------------------------------
A loose matching rule will happily align a short form to text that does not
define it. So take the rate at which a rule fires **by chance** — measured by
pairing short forms with windows that cannot be their definitions — and subtract
it from the rate at which it fires on real text. What remains is the rate at
which the rule fires for a reason.

For strategy ``A`` and short form ``s``:

.. math::

    \\mathrm{prec}_A(s) = \\frac{n_{SL}(s, A) - \\lambda_A(s)\\, n_S(s)}{n_{SL}(s, A)}

where ``n_S(s)`` counts candidate pairs carrying ``s``, ``n_SL(s, A)`` counts
those where ``A`` matched, and ``λ_A(s)`` is the chance firing rate. Aggregated
over short forms, weighted by how often the strategy fired:

.. math::

    \\mathrm{prec}_A = \\frac{\\sum_s \\mathrm{prec}_A(s)\\, n_{SL}(s, A)}
                            {\\sum_s n_{SL}(s, A)}

Why this is worth having
------------------------
It needs **no annotation whatsoever**. Reliability is estimated from raw text, so
a user can re-derive it on their own domain — legal, financial, internal
documentation — where no gold standard exists and never will. Nothing else in
this library can be tuned that way.

It is also the natural source of a per-pair confidence: the precision of the
strategy that produced a pair *is* an estimate of how likely that pair is right,
which is what makes abstention possible.

Estimating λ
------------
``λ_A(s)`` is measured by pairing ``s`` with long-form windows harvested from
*other* documents. Those windows do not define ``s``, so every match a strategy
makes on them is a false positive by construction. Randomisation is seeded and
recorded, so an estimate is reproducible.

Tier 0 pure: standard library only.
"""

from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

from ._strategies import STRATEGIES, Strategy, best_match, split_long_form

__all__ = [
    "Candidate",
    "PrecisionTable",
    "estimate_precisions",
    "harvest_candidates",
    "short_form_group",
]

#: A parenthetical short form, plus the text preceding it.
_PAREN = re.compile(r"\(([^()]{1,30})\)")

#: Words of preceding context retained as the candidate long-form window,
#: matching the reference algorithm's budget.
_WINDOW_WORDS = 12


@dataclass(frozen=True)
class Candidate:
    """One potential short-form/long-form pair harvested from raw text.

    No claim is made that it *is* a definition — that is the point. The
    estimator works over unlabelled candidates.
    """

    short_form: str
    window: tuple[str, ...]


def short_form_group(short_form: str) -> str:
    """Bucket a short form by length and character content.

    Reliability is not uniform: a three-letter all-alphabetic short form is a
    far safer match than a two-character one containing punctuation. Ab3P splits
    on exactly these axes and so do we — lengths 1-5 with 6+ folded into 5, and
    three content classes.

    Args:
        short_form: The abbreviation.

    Returns:
        A key such as ``"al:3"``, ``"num:2"`` or ``"spec:4"``.
    """
    length = min(max(len(short_form), 1), 5)
    if any(not character.isalnum() for character in short_form):
        kind = "spec"
    elif any(character.isdigit() for character in short_form):
        kind = "num"
    else:
        kind = "al"
    return f"{kind}:{length}"


def harvest_candidates(texts: Iterable[str]) -> list[Candidate]:
    """Extract unlabelled ``(short form, preceding window)`` pairs from raw text.

    Deliberately permissive — the point is to observe how often each strategy
    fires across everything bracket-shaped, including the many parentheticals
    that are not definitions at all. Filtering here would bias the chance rate.

    Args:
        texts: Raw documents.

    Returns:
        Every candidate found, in document order.
    """
    candidates: list[Candidate] = []
    for text in texts:
        for found in _PAREN.finditer(text):
            short_form = found.group(1).strip()
            if not short_form or not any(c.isalnum() for c in short_form):
                continue
            preceding = text[: found.start()]
            words = [word.casefold() for word, _, _ in split_long_form(preceding)]
            if not words:
                continue
            candidates.append(Candidate(short_form.casefold(), tuple(words[-_WINDOW_WORDS:])))
    return candidates


@dataclass
class PrecisionTable:
    """Estimated precision per ``(short-form group, strategy)``.

    Attributes:
        values: ``{group: {strategy name: precision}}``.
        support: ``{group: {strategy name: times the strategy fired}}``.
        seed: Randomisation seed used for the chance estimate.
        candidates: How many unlabelled candidates the estimate was built from.
    """

    values: dict[str, dict[str, float]]
    support: dict[str, dict[str, int]]
    seed: int = 0
    candidates: int = 0

    def precision(self, group: str, strategy: str) -> float:
        """Estimated precision, or ``0.0`` when the pair was never observed."""
        return self.values.get(group, {}).get(strategy, 0.0)

    def ordered(self, group: str, minimum_support: int = 5) -> list[str]:
        """Strategy names for ``group``, most reliable first.

        Args:
            group: Short-form group key.
            minimum_support: Strategies that fired fewer times than this are
                dropped — an estimate from three observations is noise, and
                admitting it would let a rule with no evidence outrank one with
                plenty.

        Returns:
            Strategy names in descending estimated precision, ties broken by
            structural strictness so the order is deterministic.
        """
        strictness = {s.name: s.strictness for s in STRATEGIES}
        eligible = [
            name
            for name, value in self.values.get(group, {}).items()
            if self.support.get(group, {}).get(name, 0) >= minimum_support and value > 0.0
        ]
        return sorted(eligible, key=lambda n: (-self.values[group][n], strictness[n], n))

    def to_dict(self) -> dict:
        """JSON-ready representation."""
        return {
            "seed": self.seed,
            "candidates": self.candidates,
            "values": self.values,
            "support": self.support,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> PrecisionTable:
        """Rebuild from :meth:`to_dict` output."""
        return cls(
            values=payload["values"],
            support=payload["support"],
            seed=payload.get("seed", 0),
            candidates=payload.get("candidates", 0),
        )

    def save(self, path: Path) -> Path:
        """Write the table as JSON."""
        path.write_text(
            json.dumps(self.to_dict(), indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        return path

    @classmethod
    def load(cls, path: Path) -> PrecisionTable:
        """Read a table written by :meth:`save`."""
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


def estimate_precisions(
    candidates: Sequence[Candidate],
    *,
    strategies: Sequence[Strategy] = STRATEGIES,
    chance_trials: int = 3,
    seed: int = 20260809,
    minimum_support: int = 5,
) -> PrecisionTable:
    """Estimate each strategy's precision without any labelled data.

    Args:
        candidates: Unlabelled candidates from :func:`harvest_candidates`.
        strategies: Rules to evaluate.
        chance_trials: Mismatched windows paired with each short form when
            measuring the chance rate. More trials tighten ``λ`` at linear cost.
        seed: Randomisation seed, recorded on the returned table.
        minimum_support: Groups with fewer observations than this are still
            recorded but will be filtered by :meth:`PrecisionTable.ordered`.

    Returns:
        The populated :class:`PrecisionTable`.
    """
    rng = random.Random(seed)
    windows = [candidate.window for candidate in candidates]

    observed: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    totals: dict[str, int] = defaultdict(int)
    chance_hits: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    chance_totals: dict[str, int] = defaultdict(int)

    for index, candidate in enumerate(candidates):
        group = short_form_group(candidate.short_form)
        totals[group] += 1
        for strategy in strategies:
            if best_match(candidate.short_form, candidate.window, strategy) is not None:
                observed[group][strategy.name] += 1

        # Chance: the same short form against windows that cannot define it.
        for _ in range(chance_trials):
            other = rng.randrange(len(windows))
            if other == index:
                continue
            chance_totals[group] += 1
            for strategy in strategies:
                if best_match(candidate.short_form, windows[other], strategy) is not None:
                    chance_hits[group][strategy.name] += 1

    values: dict[str, dict[str, float]] = {}
    support: dict[str, dict[str, int]] = {}
    for group, per_strategy in observed.items():
        values[group] = {}
        support[group] = {}
        for name, fired in per_strategy.items():
            trials = chance_totals.get(group, 0)
            rate = (chance_hits[group][name] / trials) if trials else 0.0
            expected_by_chance = rate * totals[group]
            precision = (fired - expected_by_chance) / fired if fired else 0.0
            values[group][name] = max(0.0, min(1.0, precision))
            support[group][name] = fired

    return PrecisionTable(values=values, support=support, seed=seed, candidates=len(candidates))


def best_alignment(
    short_form: str,
    words: Sequence[str],
    table: PrecisionTable,
    *,
    strategies: Sequence[Strategy] = STRATEGIES,
    minimum_precision: float = 0.0,
) -> Optional[tuple[Strategy, tuple[tuple[int, int], ...], float]]:
    """Apply strategies in descending reliability and take the first that fits.

    This is the cascade: because the order is by estimated precision, the first
    success is the most reliable available explanation of the short form, and its
    precision doubles as the pair's confidence.

    Args:
        short_form: Case-folded short form.
        words: Case-folded long-form words.
        table: Estimated precisions.
        strategies: Rules available.
        minimum_precision: Refuse to match below this confidence — the
            abstention threshold.

    Returns:
        ``(strategy, positions, confidence)``, or ``None`` if nothing matched
        above the threshold.
    """
    group = short_form_group(short_form)
    by_name = {strategy.name: strategy for strategy in strategies}
    for name in table.ordered(group):
        confidence = table.precision(group, name)
        if confidence < minimum_precision:
            break  # the list is descending; nothing later can qualify
        strategy = by_name.get(name)
        if strategy is None:
            continue
        positions = best_match(short_form, words, strategy)
        if positions is not None:
            return strategy, positions, confidence
    return None
