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

Two ways to get a table
-----------------------
:func:`estimate_precisions` derives one from **your** text. That is the route
this module exists for and the only one that yields a calibration for your
domain.

:func:`bundled_table` loads one derived once by a maintainer and shipped with
the package, so that an installation with no corpus and no network still has
somewhere to start. It is a **prior**, not a calibration — the distinction is
spelled out on that function and it is not a formality.

Tier 0 pure: standard library only.
"""

from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from ._strategies import STRATEGIES, Strategy, best_match, split_long_form
from .resources import read_json_resource

__all__ = [
    "BUNDLED_TABLE_RESOURCE",
    "Candidate",
    "PrecisionTable",
    "best_alignment",
    "bundled_table",
    "bundled_table_provenance",
    "estimate_precisions",
    "harvest_candidates",
    "short_form_group",
]

#: The shipped table, built by ``tools/build_reliability_table.py``. Named here
#: rather than inlined so that a caller auditing an installation can check the
#: same file :func:`acronymkit.capabilities` reports a digest for.
BUNDLED_TABLE_RESOURCE = "pseudo_precision_en.json"

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
            structural strictness so the order is deterministic. A name this
            build does not define is still returned — :func:`best_alignment`
            skips it — but sorts last among its ties rather than raising. That
            mattered less when every table was built in the same process that
            consumed it; a table now arrives from a file, possibly written by an
            older build, and a strategy renamed since then must not turn a
            lookup into a ``KeyError``.
        """
        strictness = {s.name: s.strictness for s in STRATEGIES}
        unknown = (len(strictness),) * 4
        eligible = [
            name
            for name, value in self.values.get(group, {}).items()
            if self.support.get(group, {}).get(name, 0) >= minimum_support and value > 0.0
        ]
        return sorted(
            eligible,
            key=lambda n: (-self.values[group][n], strictness.get(n, unknown), n),
        )

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


def bundled_table() -> PrecisionTable:
    """Load the reliability table shipped inside the package.

    This is the zero-argument, zero-corpus, zero-network route to a usable
    table. Nothing is downloaded and nothing is fitted at import time; the file
    is a bundled resource and reading it is the whole operation.

    What it is a table *of*, stated plainly because the alternative is a user
    trusting a number that does not describe their text:

    * It was derived from the development half of MED1250 — MEDLINE abstracts —
      with the estimator in this module, reading raw text and no annotation.
    * It is therefore a **prior on English biomedical prose**. On a contract, a
      filing or an internal wiki the strategies may fire at quite different
      rates, and how different has not been measured. Treat the confidences as
      an ordering you inherited rather than as probabilities you verified.
    * :func:`estimate_precisions` remains the route that yields a calibration.
      If you have a corpus, use it: that path is why this module exists, and a
      table built from your own text is strictly better evidence about your own
      text than this one can be.

    The provenance travels with the data — see :func:`bundled_table_provenance`
    — so the source corpus, its licence and the split seed are inspectable at
    run time rather than only in the repository.

    Returns:
        A freshly constructed :class:`PrecisionTable`. Not shared or cached:
        the table is mutable, so handing out one instance would let one caller's
        edits reach another's.

    Raises:
        ResourceNotFoundError: If the resource is missing from the installation
            or is not the document this function expects.

    Example:
        >>> table = bundled_table()
        >>> table.precision("al:3", "anchInit_placeInit_skipNone") > 0.9
        True
    """
    return PrecisionTable.from_dict(_bundled_document())


def bundled_table_provenance() -> dict[str, Any]:
    """Describe where :func:`bundled_table` came from.

    Carried as data because the resource is JSON and JSON has no comment
    syntax: every other bundled resource states its source in a header comment,
    and this one would too if the format allowed. Keys include the source
    asset's URL, SHA-256 and licence, the corpus half and split seed it was
    derived from, and the caveat repeated on :func:`bundled_table`.

    Returns:
        A fresh, mutable mapping. Empty only if a future resource drops the
        block, which callers should treat as "unknown", not as "none".

    Example:
        >>> bundled_table_provenance()["source_licence"]
        'Public domain (United States Government Work)'
    """
    provenance = _bundled_document().get("provenance", {})
    return provenance if isinstance(provenance, dict) else {}


def _bundled_document() -> dict[str, Any]:
    """Read and shape-check the bundled resource.

    Returns:
        The decoded document.

    Raises:
        ResourceNotFoundError: If the document is not an object carrying the
            ``values`` and ``support`` mappings the table is built from. A
            wrong-shaped resource is indistinguishable from a missing one as far
            as a caller can act on it, so it is reported the same way.
    """
    from .exceptions import ResourceNotFoundError

    document = read_json_resource(BUNDLED_TABLE_RESOURCE)
    if not isinstance(document, dict) or not isinstance(document.get("values"), dict):
        raise ResourceNotFoundError(
            f"Bundled resource {BUNDLED_TABLE_RESOURCE!r} is not a pseudo-precision "
            "table: expected an object with 'values' and 'support' mappings"
        )
    if not isinstance(document.get("support"), dict):
        raise ResourceNotFoundError(
            f"Bundled resource {BUNDLED_TABLE_RESOURCE!r} is missing its 'support' counts"
        )
    return document


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
    table: Optional[PrecisionTable] = None,
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
        table: Estimated precisions. Omit it to fall back on
            :func:`bundled_table`, which makes the cascade usable with no
            corpus — at the cost of an ordering derived from someone else's
            domain. Pass a table from :func:`estimate_precisions` whenever you
            have text of your own.
        strategies: Rules available.
        minimum_precision: Refuse to match below this confidence — the
            abstention threshold.

    Returns:
        ``(strategy, positions, confidence)``, or ``None`` if nothing matched
        above the threshold.
    """
    if table is None:
        table = bundled_table()
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
