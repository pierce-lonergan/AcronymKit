#!/usr/bin/env python3
"""Bring-your-own-catalog evaluation: run it on your schema, send back only numbers.

Why this file exists
--------------------
``docs/POSITIONING.md`` commits this library to being a governance instrument,
and names as the first cost of that commitment: *it requires a real proprietary
glossary, and this project does not have one.* Every published governed figure
is taken with ``GovernedDictionary({})`` -- an **empty** catalog -- so those
figures measure where an identifier is *cut* and say nothing about what a
governed vocabulary is worth. The one experiment that did build a catalog
inferred it from the very labels used as gold, and it found the catalog no
better than the empty one. That is reversal one, and it is open.

Closing it needs a real glossary measured against the schema it governs. The
obstacle has never been the measurement; it is that a data-standards glossary is
the kind of asset an organisation will not email to a stranger. **So the
measurement comes to the data.** This file is one script, standard library plus
``acronymkit``, no network, no telemetry, no writes outside the paths you name.
You run it inside your own network and send back a JSON file that contains
counts and percentages and nothing else -- a property this module enforces
rather than promises (see :func:`redaction_problems`).

What it measures
----------------
Two arms over the same identifiers, differing in exactly one thing:

``empty``
    ``expand_identifier(identifier, GovernedDictionary({}))``. The shipped code
    path with no vocabulary at all. This is the arm every published figure in
    this project is taken on.

``catalog``
    ``expand_identifier(identifier, <your catalog>)``. Same code path, same
    identifiers, your vocabulary loaded.

Scored against the human label your schema already carries. The question is
whether the second arm beats the first, and by how much.

The firing count comes first, and it can make the run worthless
---------------------------------------------------------------
Before any comparison this module counts ``catalog_fired_pairs``: identifiers
where the two arms produced different phrases. If that is zero, the two arms are
the same arm, every difference is exactly zero by construction, and the run
**measured nothing** -- which is what the report says, in those words, and it is
the first thing printed. A catalog that never fires is not evidence that
catalogs do not help; it is evidence that this schema and this catalog do not
overlap, and the fix is a bigger overlap rather than a stronger conclusion.

The circularity check, which is why the last attempt at this was thrown away
---------------------------------------------------------------------------
The August 2026 audit built catalogs by reading them off the display labels it
then scored against. A catalog derived from the gold cannot lose, and a catalog
derived from the gold that *still* does not win says nothing at all. There is no
way for a script to verify how a glossary was authored, so this one measures the
observable proxy: ``leakage.entries_present_in_gold_pct``, the share of your
catalog's expansions that appear verbatim as a word run inside the labels being
scored. A glossary written years before this schema will score low. A glossary
reverse-engineered from these labels will score high. Read the headline in the
light of that number, and if it is high, say so beside the result.

The statistics, and the size of ask they imply
----------------------------------------------
The two arms are paired -- same identifiers, same code -- so the comparison is
McNemar's, over the **discordant** pairs only: the ones where exactly one arm was
right. Pairs both arms get right and pairs both arms get wrong carry no
information about which arm is better, and a percentage-point gap quoted without
the discordant count is unreadable.

``--power`` prints the discordant counts that make a result decidable. Two
columns, because the exact binomial test's power is not monotone in ``n``: the
smallest ``n`` at which power first reaches ``0.80``, and the ``n`` from which it
stays there. :data:`MIN_DISCORDANT_PAIRS` is the second column at an effect of
``0.70`` -- the catalog winning seven of every ten pairs the two arms disagree
on -- because a criterion set at a sample size the test dips back below is not a
criterion.

**The row count that yields those discordant pairs is not stated here, and that
is deliberate.** It depends on how abbreviated your schema is and on how much of
it your catalog covers, and this project has no measurement of either for any
real schema -- which is the whole reason this file exists. So the acceptance
criterion is on discordant pairs, the kit reports the count it got, and a run
that falls short says so instead of a run that guesses.

What leaves your network
------------------------
The file ``--out`` names, and nothing else. Its strings are declared **by
position**: every path that may hold one is listed in
:data:`_ALLOWED_STRING_PATHS` with the shape it may take, every dictionary key
is listed in :data:`_ALLOWED_REPORT_KEYS`, and :func:`redaction_problems`
refuses to let ``main`` write a report carrying anything else. So a schema name,
a column name, a catalog term or a label cannot reach the output even through a
code path nobody thought about -- which is stronger than the first draft, whose
"looks like a version string" pattern admitted underscores and would have passed
``PATIENT_MRN_HASHED`` straight through. Run
``--self-test`` first: it drives both arms over a synthetic fixture that ships in
this file, and it includes the negative control -- a fixture where the catalog
must *not* help -- because a kit that only ever reports "the catalog helped"
would prove nothing when it reported it about yours.

Usage::

    python byoc_eval.py --self-test
    python byoc_eval.py --power
    python byoc_eval.py --template ./example
    python byoc_eval.py --schema schema.csv --catalog glossary.csv --out report.json

Input formats, both CSV with a header row::

    schema.csv     identifier,label
                   TXN_ID,Transaction Identifier
    glossary.csv   token,expansion
                   TXN,Transaction

Column names are configurable (``--identifier-column`` and friends) because no
two organisations name these the same way. Nothing else about the input is
configurable, on purpose: an evaluation with tuning knobs is an evaluation
somebody can tune until it agrees with them.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _datetime
import hashlib
import json
import math
import platform
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:  # installed, or already importable
    from acronymkit.governed import GovernedDictionary, expand_identifier
except ImportError:  # pragma: no cover - exercised only from a source checkout
    _SRC = Path(__file__).resolve().parent.parent / "src"
    if _SRC.is_dir():
        sys.path.insert(0, str(_SRC))
    from acronymkit.governed import GovernedDictionary, expand_identifier

#: Bumped whenever the report's shape or any metric's definition changes, so two
#: reports from two organisations can be told apart without asking either of
#: them when they ran it. It is not the library's version; both are recorded.
KIT_VERSION = "1"

#: Discordant pairs required before a difference between the arms is decidable.
#: Derived, not chosen: ``--power`` recomputes it. It is the count from which the
#: two-sided exact binomial test holds power ``0.80`` at ``alpha = 0.05`` against
#: an effect of ``0.70``, and it is the *stable* column rather than the first
#: crossing, because power is not monotone in ``n`` for an exact test.
MIN_DISCORDANT_PAIRS = 54

#: The effect and the level :data:`MIN_DISCORDANT_PAIRS` is derived at.
POWER_EFFECT = 0.70
POWER_ALPHA = 0.05
POWER_TARGET = 0.80

#: Verdict strings. A closed set, because the verdict is written into the report
#: and the report may not carry a string this module did not author.
VERDICT_NO_CATALOG = "no-catalog-supplied"
VERDICT_NOTHING_MEASURED = "catalog-never-fired-nothing-measured"
VERDICT_UNDERPOWERED = "catalog-fired-too-few-discordant-pairs-to-decide"
VERDICT_NO_DIFFERENCE = "catalog-fired-no-detectable-difference"
VERDICT_CATALOG_BETTER = "catalog-fired-catalog-better"
VERDICT_EMPTY_BETTER = "catalog-fired-empty-better"

#: The sentence operating rule 12 requires when the thing under test never ran.
#: Quoted verbatim rather than paraphrased, because a paraphrase of it is what a
#: null result normally arrives wearing.
NOTHING_MEASURED_SENTENCE = (
    "The catalog fired on zero identifiers, so this run measured nothing about "
    "the catalog. Every difference below is zero by construction."
)

_ALPHANUMERIC_RUN = re.compile(r"[^0-9a-z]+")
_SHA256 = re.compile(r"^(?:[0-9a-f]{64})?$")
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

#: The rejection reasons :meth:`SchemaRows.reject` may write. They become
#: dictionary **keys** in the report, so they are declared here rather than
#: trusted for being module-authored.
_REJECTION_REASONS = frozenset({"empty_identifier", "empty_label", "duplicate_identifier"})

#: Every dictionary key the report may carry, enumerated rather than pattern
#: matched.
#:
#: THE FIRST DRAFT OF THIS GUARD WAS A PATTERN AND IT DID NOT WORK. It admitted
#: any string of ``[0-9A-Za-z._+-]`` as "a version token", and the character
#: class contains ``_`` -- so ``PATIENT_MRN_HASHED`` passed redaction. The test
#: that found it is ``tests/test_byoc_eval.py``'s leaked-value case, which is
#: exactly what a mutation test is for. A pattern loose enough to admit every
#: real version string is loose enough to admit most column names, so the shape
#: had to change: strings are allowed **by report path**, keys **by name**, and
#: anything undeclared is a problem.
_ALLOWED_REPORT_KEYS = frozenset(
    {
        # top level
        "arms",
        "firing",
        "inputs",
        "kit",
        "leakage",
        "paired",
        "population",
        "verdict",
        # arms: subset, then arm
        "all",
        "expanding",
        "fired",
        "empty",
        "catalog",
        # one arm's tally
        "pairs",
        "exact_pct",
        "fully_known_pct",
        "word_precision_pct",
        "word_recall_pct",
        "word_f1_pct",
        # firing
        "catalog_entries_loaded",
        "catalog_fired_pairs",
        "catalog_fired_pct",
        "catalog_entries_that_fired",
        "catalog_entries_that_fired_pct",
        "nothing_measured",
        "note",
        # population
        "pairs_scored",
        "pairs_where_label_expands",
        "pairs_where_label_expands_pct",
        "unknown_token_types_empty_arm",
        "unknown_token_types_catalog_arm",
        # paired test
        "both_correct",
        "neither_correct",
        "catalog_only_correct",
        "empty_only_correct",
        "discordant_pairs",
        "discordant_pairs_required",
        "decidable",
        "mcnemar_exact_p",
        "exact_pct_delta",
        # circularity check
        "entries",
        "entries_present_in_gold",
        "entries_present_in_gold_pct",
        # provenance
        "name",
        "kit_version",
        "acronymkit_version",
        "python",
        "generated_utc",
        "schema_sha256",
        "schema_rows_read",
        "schema_rows_scored",
        "schema_rows_rejected",
        "catalog_sha256",
    }
)

#: The report path under which dynamic keys are permitted, and nowhere else.
_REJECTION_PATH = "report.inputs.schema_rows_rejected"

#: Every path in the report that may hold a string, with what that string may
#: be. A string at any other path is a leak; a string at one of these that does
#: not match is a leak too.
_ALLOWED_STRING_PATHS: Dict[str, re.Pattern[str]] = {
    "report.kit.name": re.compile(r"^acronymkit byoc_eval$"),
    "report.kit.kit_version": re.compile(r"^\d{1,3}$"),
    # An installed version, or the empty string when the library will not say.
    "report.kit.acronymkit_version": re.compile(r"^(?:\d+(?:\.\d+){0,3}(?:[a-z]{1,3}\d{1,3})?)?$"),
    "report.kit.python": re.compile(r"^\d+\.\d+\.\d+$"),
    "report.kit.generated_utc": _TIMESTAMP,
    "report.inputs.schema_sha256": _SHA256,
    "report.inputs.catalog_sha256": _SHA256,
    "report.verdict": re.compile(
        "^(?:{alternatives})$".format(
            alternatives="|".join(
                re.escape(verdict)
                for verdict in (
                    VERDICT_NO_CATALOG,
                    VERDICT_NOTHING_MEASURED,
                    VERDICT_UNDERPOWERED,
                    VERDICT_NO_DIFFERENCE,
                    VERDICT_CATALOG_BETTER,
                    VERDICT_EMPTY_BETTER,
                )
            )
        )
    ),
    "report.firing.note": re.compile(f"^{re.escape(NOTHING_MEASURED_SENTENCE)}$"),
}


# ---------------------------------------------------------------------------
# normalisation and the two metrics
# ---------------------------------------------------------------------------
def words(text: str) -> List[str]:
    """The comparison words of ``text``: case-folded, punctuation as separator.

    ``"Transaction Identifier"``, ``"transaction  identifier"`` and
    ``"Transaction-Identifier"`` all give ``["transaction", "identifier"]``.
    Typography is not the subject of this measurement and scoring it as an error
    would put a house style guide in the numerator.

    Args:
        text: A label or a produced phrase.

    Returns:
        The words, in order.
    """
    return [word for word in _ALPHANUMERIC_RUN.split(text.casefold()) if word]


def phrase_key(text: str) -> str:
    """The whole-phrase comparison key: :func:`words`, space-joined."""
    return " ".join(words(text))


def stream_key(text: str) -> str:
    """The alphanumeric character stream of ``text``, case-folded.

    Two strings sharing this key differ only in where the words were cut. Two
    that do not share it differ in the characters themselves -- which is what
    "the label expands the identifier" means, and it is the only population a
    catalog can possibly help on.
    """
    return "".join(character for character in text.casefold() if character.isalnum())


@dataclass
class Tally:
    """Counters for one arm over one subset.

    Attributes:
        pairs: Scored pairs.
        exact: Pairs whose phrase key equals the label's.
        fully_known: Pairs where every token resolved from the catalog.
        hits: Predicted words that are label words, counted as a multiset.
        predicted: Predicted words.
        gold: Label words.
    """

    pairs: int = 0
    exact: int = 0
    fully_known: int = 0
    hits: int = 0
    predicted: int = 0
    gold: int = 0

    def add(self, *, exact: bool, fully_known: bool, hits: int, predicted: int, gold: int) -> None:
        """Fold one scored pair in."""
        self.pairs += 1
        self.exact += int(exact)
        self.fully_known += int(fully_known)
        self.hits += hits
        self.predicted += predicted
        self.gold += gold

    def as_dict(self) -> Dict[str, Optional[float]]:
        """The published shape of this arm on this subset.

        An undefined ratio is ``null`` and never ``0.0``. A subset with no pairs
        in it has no accuracy, and storing zero there would read as "got
        everything wrong" while meaning "was never asked".

        The converse is guarded too, and it bit the first draft: an arm that
        predicted words and hit none of them has ``precision == recall == 0``,
        which is a real ``0.0`` F1 and not an undefined one. Dividing by
        ``precision + recall`` without that branch stored ``null`` there and the
        empty arm of the shipped self-test fixture printed it.
        """
        precision = self.hits / self.predicted if self.predicted else None
        recall = self.hits / self.gold if self.gold else None
        f1: Optional[float] = None
        if precision is not None and recall is not None:
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return {
            "pairs": self.pairs,
            "exact_pct": _pct(self.exact, self.pairs),
            "fully_known_pct": _pct(self.fully_known, self.pairs),
            "word_precision_pct": None if precision is None else round(precision * 100, 2),
            "word_recall_pct": None if recall is None else round(recall * 100, 2),
            "word_f1_pct": None if f1 is None else round(f1 * 100, 2),
        }


def _pct(part: int, whole: int) -> Optional[float]:
    """``part`` as a percentage of ``whole``, or ``None`` when undefined."""
    return round(part / whole * 100, 2) if whole else None


def score_pair(phrase: str, label: str) -> Tuple[bool, int, int, int]:
    """Score one produced phrase against one label.

    Args:
        phrase: What ``expand_identifier`` produced.
        label: The human label the schema carries.

    Returns:
        ``(exact, hits, predicted, gold)`` -- whole-phrase agreement and the
        word-multiset overlap behind the per-word figures.
    """
    predicted_words = Counter(words(phrase))
    gold_words = Counter(words(label))
    hits = sum((predicted_words & gold_words).values())
    return (
        phrase_key(phrase) == phrase_key(label),
        hits,
        sum(predicted_words.values()),
        sum(gold_words.values()),
    )


# ---------------------------------------------------------------------------
# the paired test
# ---------------------------------------------------------------------------
def exact_binomial_two_sided(successes: int, trials: int) -> Optional[float]:
    """Two-sided exact binomial p-value against ``p = 0.5``.

    This is McNemar's test in its exact form, which is the right one here
    because a real schema can easily produce a discordant count in the dozens
    and the chi-square approximation is not trustworthy there.

    Args:
        successes: Discordant pairs the catalog arm won.
        trials: Discordant pairs.

    Returns:
        The p-value, or ``None`` when there are no discordant pairs -- which is
        not a p-value of 1, it is the absence of a test.
    """
    if trials <= 0:
        return None
    tail = min(successes, trials - successes)
    mass = sum(math.comb(trials, index) for index in range(tail + 1))
    return min(1.0, 2.0 * mass / (2.0**trials))


def power_of(trials: int, effect: float, alpha: float = POWER_ALPHA) -> float:
    """Power of the two-sided exact binomial test at ``trials`` discordant pairs.

    Args:
        trials: Discordant pairs.
        effect: The true probability that the catalog arm wins a discordant pair.
        alpha: The level.

    Returns:
        The probability of rejecting, between 0 and 1.
    """
    total = 0.0
    for successes in range(trials + 1):
        p_value = exact_binomial_two_sided(successes, trials)
        if p_value is not None and p_value <= alpha:
            total += (
                math.comb(trials, successes)
                * effect**successes
                * (1 - effect) ** (trials - successes)
            )
    return total


def power_table(
    effects: Sequence[float] = (0.60, 0.65, 0.70, 0.75, 0.80),
    target: float = POWER_TARGET,
    alpha: float = POWER_ALPHA,
    ceiling: int = 400,
    stable_window: int = 60,
) -> List[Dict[str, Optional[float]]]:
    """Discordant counts at which the paired test becomes decidable.

    Two columns rather than one. The exact test's power is **not monotone** in
    ``n`` -- adding a discordant pair can move the rejection region and lose
    power -- so the first crossing is not a level anybody can rely on. The second
    column is the count from which power holds for ``stable_window`` consecutive
    values, and it is the one :data:`MIN_DISCORDANT_PAIRS` is taken from.

    Args:
        effects: True win-probabilities on a discordant pair to report.
        target: The power to reach.
        alpha: The level.
        ceiling: Largest ``n`` searched. A row that does not reach ``target``
            below it reports ``null`` rather than the ceiling.
        stable_window: Consecutive values that must hold ``target``.

    Returns:
        One row per effect.
    """
    rows: List[Dict[str, Optional[float]]] = []
    for effect in effects:
        powers = {trials: power_of(trials, effect, alpha) for trials in range(2, ceiling + 1)}
        first: Optional[int] = None
        stable: Optional[int] = None
        for trials in range(2, ceiling + 1):
            if first is None and powers[trials] >= target:
                first = trials
            window = range(trials, min(trials + stable_window, ceiling + 1))
            if stable is None and all(powers[value] >= target for value in window):
                stable = trials
        rows.append(
            {
                "effect": effect,
                "first_n_at_target": first,
                "stable_n_at_target": stable,
                "power_at_stable_n": round(powers[stable], 4) if stable is not None else None,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# input
# ---------------------------------------------------------------------------
@dataclass
class SchemaRows:
    """Admitted ``(identifier, label)`` pairs and the counts behind them.

    Attributes:
        pairs: The rows that will be scored, deduplicated on identifier.
        rows_read: Data rows read from the file.
        rejected: Counts by reason. Reasons only; no row content.
    """

    pairs: List[Tuple[str, str]] = field(default_factory=list)
    rows_read: int = 0
    rejected: Dict[str, int] = field(default_factory=dict)

    def reject(self, reason: str) -> None:
        """Count one rejected row."""
        self.rejected[reason] = self.rejected.get(reason, 0) + 1


def read_schema(
    path: Path,
    *,
    identifier_column: str,
    label_column: str,
    encoding: str = "utf-8-sig",
    delimiter: str = ",",
) -> SchemaRows:
    """Read the schema file.

    Args:
        path: The CSV.
        identifier_column: Header of the machine-name column.
        label_column: Header of the human-label column.
        encoding: File encoding.
        delimiter: Field delimiter.

    Returns:
        The admitted pairs and the rejection counts.

    Raises:
        KeyError: When a named column is not in the header.
    """
    rows = SchemaRows()
    seen: set = set()
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        _require_columns(reader.fieldnames, (identifier_column, label_column), path)
        for row in reader:
            rows.rows_read += 1
            identifier = (row.get(identifier_column) or "").strip()
            label = (row.get(label_column) or "").strip()
            if not identifier:
                rows.reject("empty_identifier")
                continue
            if not label:
                rows.reject("empty_label")
                continue
            key = identifier.casefold()
            if key in seen:
                rows.reject("duplicate_identifier")
                continue
            seen.add(key)
            rows.pairs.append((identifier, label))
    return rows


def read_catalog(
    path: Path,
    *,
    token_column: str,
    expansion_column: str,
    encoding: str = "utf-8-sig",
    delimiter: str = ",",
) -> Dict[str, str]:
    """Read the glossary file into a ``token -> expansion`` mapping.

    Later rows win over earlier ones for the same token, and the count of
    overridden tokens is not reported: it is a property of the caller's file, it
    would need the token to be meaningful, and the token may not leave.

    Args:
        path: The CSV.
        token_column: Header of the short-form column.
        expansion_column: Header of the long-form column.
        encoding: File encoding.
        delimiter: Field delimiter.

    Returns:
        The mapping ``GovernedDictionary.from_mapping`` will be built from.

    Raises:
        KeyError: When a named column is not in the header.
    """
    mapping: Dict[str, str] = {}
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        _require_columns(reader.fieldnames, (token_column, expansion_column), path)
        for row in reader:
            token = (row.get(token_column) or "").strip()
            expansion = (row.get(expansion_column) or "").strip()
            if token and expansion:
                mapping[token] = expansion
    return mapping


def _require_columns(
    fieldnames: Optional[Sequence[str]], required: Iterable[str], path: Path
) -> None:
    """Fail with the header the file actually has, before anything is scored."""
    present = list(fieldnames or ())
    missing = [name for name in required if name not in present]
    if missing:
        raise KeyError(
            f"{path}: header has {present!r}; missing {missing!r}. "
            "Pass --identifier-column / --label-column / --token-column / "
            "--expansion-column to name your own."
        )


def digest(path: Path) -> str:
    """SHA-256 of the file, so two reports can be told apart by their input."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------
@dataclass
class Outcome:
    """One identifier, scored under both arms.

    Attributes:
        expands: The label's character stream differs from the identifier's, so
            the label spells something out that the identifier abbreviates.
        fired: The catalog arm produced a different phrase from the empty arm.
        empty_exact: The empty arm matched the label.
        catalog_exact: The catalog arm matched the label.
    """

    expands: bool
    fired: bool
    empty_exact: bool
    catalog_exact: bool


def evaluate(
    pairs: Sequence[Tuple[str, str]], catalog_mapping: Mapping[str, str]
) -> Dict[str, Any]:
    """Score both arms and build the whole report body.

    Args:
        pairs: Admitted ``(identifier, label)`` rows.
        catalog_mapping: The caller's glossary. May be empty, in which case the
            two arms are identical and the report says so.

    Returns:
        Everything except the ``kit`` and ``inputs`` blocks.
    """
    empty_catalog = GovernedDictionary({})
    loaded_catalog = (
        GovernedDictionary.from_mapping(dict(catalog_mapping)) if catalog_mapping else empty_catalog
    )

    subsets = ("all", "expanding", "fired")
    tallies: Dict[str, Dict[str, Tally]] = {
        subset: {"empty": Tally(), "catalog": Tally()} for subset in subsets
    }
    outcomes: List[Outcome] = []
    fired_entries: set = set()
    unknown_types_empty: set = set()
    unknown_types_catalog: set = set()

    for identifier, label in pairs:
        empty_expansion = expand_identifier(identifier, empty_catalog)
        catalog_expansion = expand_identifier(identifier, loaded_catalog)

        empty_exact, empty_hits, empty_predicted, gold_words = score_pair(
            empty_expansion.phrase, label
        )
        catalog_exact, catalog_hits, catalog_predicted, _ = score_pair(
            catalog_expansion.phrase, label
        )

        fired = phrase_key(empty_expansion.phrase) != phrase_key(catalog_expansion.phrase)
        expands = stream_key(identifier) != stream_key(label)
        if fired:
            for token in catalog_expansion.tokens:
                if token.is_known:
                    fired_entries.add(token.raw.casefold())
        for token in empty_expansion.tokens:
            if not token.is_known:
                unknown_types_empty.add(token.raw.casefold())
        for token in catalog_expansion.tokens:
            if not token.is_known:
                unknown_types_catalog.add(token.raw.casefold())

        applicable = ["all"] + (["expanding"] if expands else []) + (["fired"] if fired else [])
        for subset in applicable:
            tallies[subset]["empty"].add(
                exact=empty_exact,
                fully_known=empty_expansion.is_fully_known,
                hits=empty_hits,
                predicted=empty_predicted,
                gold=gold_words,
            )
            tallies[subset]["catalog"].add(
                exact=catalog_exact,
                fully_known=catalog_expansion.is_fully_known,
                hits=catalog_hits,
                predicted=catalog_predicted,
                gold=gold_words,
            )
        outcomes.append(
            Outcome(
                expands=expands,
                fired=fired,
                empty_exact=empty_exact,
                catalog_exact=catalog_exact,
            )
        )

    fired_pairs = sum(1 for outcome in outcomes if outcome.fired)
    catalog_only = sum(
        1 for outcome in outcomes if outcome.catalog_exact and not outcome.empty_exact
    )
    empty_only = sum(1 for outcome in outcomes if outcome.empty_exact and not outcome.catalog_exact)
    discordant = catalog_only + empty_only

    firing: Dict[str, Any] = {
        "catalog_entries_loaded": len(catalog_mapping),
        "catalog_fired_pairs": fired_pairs,
        "catalog_fired_pct": _pct(fired_pairs, len(outcomes)),
        "catalog_entries_that_fired": len(fired_entries),
        "catalog_entries_that_fired_pct": _pct(len(fired_entries), len(catalog_mapping)),
        "nothing_measured": fired_pairs == 0,
    }
    if fired_pairs == 0:
        firing["note"] = NOTHING_MEASURED_SENTENCE

    empty_exact_pct = tallies["all"]["empty"].as_dict()["exact_pct"]
    catalog_exact_pct = tallies["all"]["catalog"].as_dict()["exact_pct"]
    delta: Optional[float] = None
    if empty_exact_pct is not None and catalog_exact_pct is not None:
        delta = round(catalog_exact_pct - empty_exact_pct, 2)

    paired = {
        "both_correct": sum(
            1 for outcome in outcomes if outcome.empty_exact and outcome.catalog_exact
        ),
        "neither_correct": sum(
            1 for outcome in outcomes if not outcome.empty_exact and not outcome.catalog_exact
        ),
        "catalog_only_correct": catalog_only,
        "empty_only_correct": empty_only,
        "discordant_pairs": discordant,
        "discordant_pairs_required": MIN_DISCORDANT_PAIRS,
        "decidable": discordant >= MIN_DISCORDANT_PAIRS,
        "mcnemar_exact_p": _round_p(exact_binomial_two_sided(catalog_only, discordant)),
        "exact_pct_delta": delta,
    }

    return {
        "firing": firing,
        "population": {
            "pairs_scored": len(outcomes),
            "pairs_where_label_expands": sum(1 for outcome in outcomes if outcome.expands),
            "pairs_where_label_expands_pct": _pct(
                sum(1 for outcome in outcomes if outcome.expands), len(outcomes)
            ),
            "unknown_token_types_empty_arm": len(unknown_types_empty),
            "unknown_token_types_catalog_arm": len(unknown_types_catalog),
        },
        "arms": {
            subset: {
                "empty": tallies[subset]["empty"].as_dict(),
                "catalog": tallies[subset]["catalog"].as_dict(),
            }
            for subset in subsets
        },
        "paired": paired,
        "verdict": verdict_for(bool(catalog_mapping), fired_pairs, discordant, catalog_only),
    }


def _round_p(value: Optional[float]) -> Optional[float]:
    """Round a p-value for publication, without rounding a small one to zero."""
    if value is None:
        return None
    return round(value, 6) if value >= 1e-6 else float(f"{value:.2e}")


def verdict_for(has_catalog: bool, fired_pairs: int, discordant: int, catalog_only: int) -> str:
    """The one-token summary, from the closed set of verdict constants.

    Ordered so that the cheapest disqualification is reported first: no catalog
    beats no firing beats too few discordant pairs beats a real result. A run
    that never fired must not be reported as "no detectable difference", because
    those are opposite findings that look identical in a table.
    """
    if not has_catalog:
        return VERDICT_NO_CATALOG
    if fired_pairs == 0:
        return VERDICT_NOTHING_MEASURED
    if discordant < MIN_DISCORDANT_PAIRS:
        return VERDICT_UNDERPOWERED
    p_value = exact_binomial_two_sided(catalog_only, discordant)
    if p_value is None or p_value > POWER_ALPHA:
        return VERDICT_NO_DIFFERENCE
    return VERDICT_CATALOG_BETTER if catalog_only * 2 > discordant else VERDICT_EMPTY_BETTER


def leakage(catalog_mapping: Mapping[str, str], pairs: Sequence[Tuple[str, str]]) -> Dict[str, Any]:
    """How much of the catalog is readable off the labels it is scored against.

    A glossary reverse-engineered from these labels cannot lose on them, so a
    win it produces is not evidence. There is no way to check authorship from
    here; what is checkable is whether each expansion appears verbatim as a word
    run inside some label being scored, and that is what this counts.

    Args:
        catalog_mapping: The caller's glossary.
        pairs: The scored rows.

    Returns:
        Counts and the share, or an empty-catalog shape.
    """
    label_runs: set = set()
    for _identifier, label in pairs:
        label_words = words(label)
        for start in range(len(label_words)):
            for end in range(start + 1, len(label_words) + 1):
                label_runs.add(" ".join(label_words[start:end]))
    present = sum(
        1 for expansion in catalog_mapping.values() if phrase_key(expansion) in label_runs
    )
    return {
        "entries": len(catalog_mapping),
        "entries_present_in_gold": present,
        "entries_present_in_gold_pct": _pct(present, len(catalog_mapping)),
    }


def build_report(
    pairs: Sequence[Tuple[str, str]],
    catalog_mapping: Mapping[str, str],
    *,
    rows: Optional[SchemaRows] = None,
    schema_digest: str = "",
    catalog_digest: str = "",
) -> Dict[str, Any]:
    """Assemble the whole report, including the blocks that identify the run."""
    body = evaluate(pairs, catalog_mapping)
    body["leakage"] = leakage(catalog_mapping, pairs)
    body["kit"] = {
        "name": "acronymkit byoc_eval",
        "kit_version": KIT_VERSION,
        "acronymkit_version": _acronymkit_version(),
        "python": platform.python_version(),
        "generated_utc": _datetime.datetime.now(_datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    body["inputs"] = {
        "schema_sha256": schema_digest,
        "schema_rows_read": rows.rows_read if rows is not None else len(pairs),
        "schema_rows_scored": len(pairs),
        "schema_rows_rejected": dict(sorted(rows.rejected.items())) if rows is not None else {},
        "catalog_sha256": catalog_digest,
    }
    return body


def _acronymkit_version() -> str:
    """The installed library's version, or an empty string if it will not say."""
    try:
        import acronymkit

        return str(getattr(acronymkit, "__version__", ""))
    except Exception:  # pragma: no cover - a library that will not import got us here
        return ""


# ---------------------------------------------------------------------------
# the guard that lets somebody send this file
# ---------------------------------------------------------------------------
def redaction_problems(report: Mapping[str, Any]) -> List[str]:
    """Every string in ``report`` that this module did not author.

    This is the property that turns "send us your glossary" into "run this and
    send two numbers", so it is checked rather than asserted. It is an
    allow-list and not a scan for known-bad content, and it is declared **by
    position**: a string is permitted only at a path in
    :data:`_ALLOWED_STRING_PATHS` and only when it matches that path's pattern;
    a dictionary key is permitted only when it is in
    :data:`_ALLOWED_REPORT_KEYS`. A string anywhere else is a problem whether or
    not anybody has thought about what it might contain.

    One place takes dynamic keys, named explicitly: ``schema_rows_rejected`` is
    keyed by rejection reason, and those must come from
    :data:`_REJECTION_REASONS`.

    The cost of this shape is that a new field is a red test until it is
    declared here, which is the intended cost. The alternative was a pattern,
    and the pattern that shipped in the first draft admitted ``_`` and therefore
    admitted most column names -- see :data:`_ALLOWED_REPORT_KEYS`.

    Args:
        report: The report about to be written.

    Returns:
        ``"<path>: <value>"`` for each problem, empty when the report is clean.
    """
    problems: List[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, str):
            pattern = _ALLOWED_STRING_PATHS.get(path)
            if pattern is None:
                problems.append(f"{path}: string at an undeclared path: {node!r}")
            elif not pattern.match(node):
                problems.append(f"{path}: string does not match its declared shape: {node!r}")
        elif isinstance(node, Mapping):
            dynamic = path == _REJECTION_PATH
            permitted = _REJECTION_REASONS if dynamic else _ALLOWED_REPORT_KEYS
            for key, value in node.items():
                if not isinstance(key, str) or key not in permitted:
                    problems.append(f"{path} key: {key!r}")
                walk(value, f"{path}.{key}")
        elif isinstance(node, (list, tuple)):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(report, "report")
    return problems


# ---------------------------------------------------------------------------
# the fixtures, and the negative control
# ---------------------------------------------------------------------------
#: A schema whose labels spell out abbreviations a glossary knows. The catalog
#: must win here, and if it does not, this kit is broken rather than the
#: catalog.
POSITIVE_SCHEMA: Tuple[Tuple[str, str], ...] = (
    ("TXN_ID", "Transaction Identifier"),
    ("TXN_AMT", "Transaction Amount"),
    ("ACCT_BAL", "Account Balance"),
    ("ACCT_NBR", "Account Number"),
    ("CUST_NM", "Customer Name"),
    ("CUST_ADDR", "Customer Address"),
    ("APPLNT_VERIF_DT", "Applicant Verification Date"),
    ("PYMT_STAT_CD", "Payment Status Code"),
)

POSITIVE_CATALOG: Dict[str, str] = {
    "TXN": "Transaction",
    "ID": "Identifier",
    "AMT": "Amount",
    "ACCT": "Account",
    "BAL": "Balance",
    "NBR": "Number",
    "CUST": "Customer",
    "NM": "Name",
    "ADDR": "Address",
    "APPLNT": "Applicant",
    "VERIF": "Verification",
    "DT": "Date",
    "PYMT": "Payment",
    "STAT": "Status",
    "CD": "Code",
}

#: A schema already spelled out, which is the shape the August 2026 audit found
#: real Socrata schemas mostly have. The same catalog must change nothing here.
#: This is the control: a kit that reported a win on this fixture would report
#: a win on anything.
NEGATIVE_SCHEMA: Tuple[Tuple[str, str], ...] = (
    ("customer_name", "Customer Name"),
    ("account_balance", "Account Balance"),
    ("payment_status", "Payment Status"),
    ("verification_date", "Verification Date"),
)

#: A glossary whose expansions appear nowhere in :data:`POSITIVE_SCHEMA`'s
#: labels. The circularity check must read zero on it -- otherwise the check is
#: a constant and the ``100`` it reads on :data:`POSITIVE_CATALOG` means nothing.
#: :data:`POSITIVE_CATALOG` *is* a catalog read off its own labels, which is why
#: it is the right positive control for this and the wrong shape for a real ask.
LEAKAGE_CONTROL_CATALOG: Dict[str, str] = {
    "QSW": "Quarterly Settlement Window",
    "RRB": "Reinsurance Recoverable Balance",
}


def self_test() -> Tuple[bool, List[str]]:
    """Drive both fixtures and check the kit can tell them apart.

    Four assertions, and the last two are the ones worth having:

    1. On the positive fixture the catalog fires.
    2. On the positive fixture the catalog arm beats the empty arm.
    3. On the **negative** fixture the catalog does not fire at all, and the
       report says the run measured nothing rather than saying no difference.
    4. The report passes :func:`redaction_problems`.

    Returns:
        ``(ok, lines)`` -- the verdict and what to print.
    """
    lines: List[str] = []
    ok = True

    positive = build_report(POSITIVE_SCHEMA, POSITIVE_CATALOG)
    negative = build_report(NEGATIVE_SCHEMA, POSITIVE_CATALOG)

    checks: List[Tuple[str, bool, str]] = [
        (
            "positive fixture: the catalog fires",
            positive["firing"]["catalog_fired_pairs"] == len(POSITIVE_SCHEMA),
            "fired on {n} of {d}".format(
                n=positive["firing"]["catalog_fired_pairs"], d=len(POSITIVE_SCHEMA)
            ),
        ),
        (
            "positive fixture: the catalog arm wins",
            (positive["paired"]["catalog_only_correct"] > 0)
            and (positive["paired"]["empty_only_correct"] == 0),
            "catalog-only {a}, empty-only {b}".format(
                a=positive["paired"]["catalog_only_correct"],
                b=positive["paired"]["empty_only_correct"],
            ),
        ),
        (
            "negative control: the catalog does not fire",
            negative["firing"]["catalog_fired_pairs"] == 0,
            "fired on {n}".format(n=negative["firing"]["catalog_fired_pairs"]),
        ),
        (
            "negative control: the verdict says nothing was measured",
            negative["verdict"] == VERDICT_NOTHING_MEASURED,
            str(negative["verdict"]),
        ),
        (
            "circularity check fires on a catalog read off the labels",
            positive["leakage"]["entries_present_in_gold_pct"] == 100.0,
            "{p} % of entries found verbatim in the labels".format(
                p=positive["leakage"]["entries_present_in_gold_pct"]
            ),
        ),
        (
            "circularity check stays quiet on a catalog that is not",
            leakage(LEAKAGE_CONTROL_CATALOG, POSITIVE_SCHEMA)["entries_present_in_gold_pct"] == 0.0,
            "{p} %".format(
                p=leakage(LEAKAGE_CONTROL_CATALOG, POSITIVE_SCHEMA)["entries_present_in_gold_pct"]
            ),
        ),
        (
            "the report carries no string from the input",
            not redaction_problems(positive) and not redaction_problems(negative),
            "; ".join(redaction_problems(positive) + redaction_problems(negative)) or "clean",
        ),
    ]
    for name, passed, detail in checks:
        ok = ok and passed
        lines.append(
            "  {mark}  {name}  --  {detail}".format(
                mark="ok " if passed else "FAIL", name=name, detail=detail
            )
        )

    lines.append("")
    lines.append(
        "  positive fixture exact: empty {e} %, catalog {c} %".format(
            e=positive["arms"]["all"]["empty"]["exact_pct"],
            c=positive["arms"]["all"]["catalog"]["exact_pct"],
        )
    )
    lines.append(
        "  negative control exact: empty {e} %, catalog {c} %".format(
            e=negative["arms"]["all"]["empty"]["exact_pct"],
            c=negative["arms"]["all"]["catalog"]["exact_pct"],
        )
    )
    return ok, lines


TEMPLATE_SCHEMA_CSV = "identifier,label\n" + "".join(
    f"{identifier},{label}\n" for identifier, label in POSITIVE_SCHEMA
)

TEMPLATE_CATALOG_CSV = "token,expansion\n" + "".join(
    f"{token},{expansion}\n" for token, expansion in POSITIVE_CATALOG.items()
)


# ---------------------------------------------------------------------------
# command line
# ---------------------------------------------------------------------------
def render(report: Mapping[str, Any]) -> str:
    """The human summary printed to the terminal, firing count first."""
    firing = report["firing"]
    paired = report["paired"]
    arms = report["arms"]
    lines = [
        "acronymkit bring-your-own-catalog evaluation",
        "  kit {kit}, acronymkit {lib}".format(
            kit=report["kit"]["kit_version"], lib=report["kit"]["acronymkit_version"] or "unknown"
        ),
        "",
        "FIRING COUNT FIRST",
        "  catalog entries loaded        {n}".format(n=firing["catalog_entries_loaded"]),
        "  identifiers the catalog moved {n} ({p} %)".format(
            n=firing["catalog_fired_pairs"], p=firing["catalog_fired_pct"]
        ),
        "  catalog entries that fired    {n}".format(n=firing["catalog_entries_that_fired"]),
    ]
    if firing["nothing_measured"]:
        lines += ["", "  " + NOTHING_MEASURED_SENTENCE]
    lines += [
        "",
        "THE TWO NUMBERS",
        "  exact match, empty catalog    {v} %".format(v=arms["all"]["empty"]["exact_pct"]),
        "  exact match, your catalog     {v} %".format(v=arms["all"]["catalog"]["exact_pct"]),
        "  difference                    {v} points".format(v=paired["exact_pct_delta"]),
        "",
        "THE PAIRED TEST",
        "  your catalog right, empty wrong   {n}".format(n=paired["catalog_only_correct"]),
        "  empty right, your catalog wrong   {n}".format(n=paired["empty_only_correct"]),
        "  discordant pairs                  {n} (need {r} to decide)".format(
            n=paired["discordant_pairs"], r=paired["discordant_pairs_required"]
        ),
        "  McNemar exact p                   {p}".format(p=paired["mcnemar_exact_p"]),
        "",
        "CIRCULARITY CHECK",
        "  catalog expansions found verbatim in the labels  {n} of {d} ({p} %)".format(
            n=report["leakage"]["entries_present_in_gold"],
            d=report["leakage"]["entries"],
            p=report["leakage"]["entries_present_in_gold_pct"],
        ),
        "",
        "VERDICT  {v}".format(v=report["verdict"]),
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """The command line."""
    parser = argparse.ArgumentParser(
        prog="byoc_eval",
        description=(
            "Score acronymkit's governed expander on your schema, with and without "
            "your glossary. Nothing leaves this machine except the file --out names, "
            "and that file carries counts only."
        ),
    )
    parser.add_argument("--schema", type=Path, help="CSV of identifier,label")
    parser.add_argument("--catalog", type=Path, help="CSV of token,expansion")
    parser.add_argument("--out", type=Path, help="write the JSON report here")
    parser.add_argument("--identifier-column", default="identifier")
    parser.add_argument("--label-column", default="label")
    parser.add_argument("--token-column", default="token")
    parser.add_argument("--expansion-column", default="expansion")
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--delimiter", default=",")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the built-in fixtures, including the negative control, and exit",
    )
    parser.add_argument(
        "--power",
        action="store_true",
        help="print the discordant-pair counts that make a result decidable, and exit",
    )
    parser.add_argument(
        "--template",
        type=Path,
        help="write example schema.csv and catalog.csv into this directory, and exit",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point.

    Returns:
        ``0`` on a completed run, ``1`` on a failed self-test, a bad input or a
        report that did not pass redaction. A run whose verdict is
        "nothing measured" still returns ``0``: it completed, and the finding is
        the finding.
    """
    arguments = build_parser().parse_args(argv)

    if arguments.self_test:
        ok, lines = self_test()
        print("self-test")
        print("\n".join(lines))
        print("\n{v}".format(v="SELF-TEST PASSED" if ok else "SELF-TEST FAILED"))
        return 0 if ok else 1

    if arguments.power:
        print(
            f"two-sided exact binomial (McNemar), alpha {POWER_ALPHA}, target power {POWER_TARGET}"
        )
        print("  effect   first n at target   stable n at target   power at stable n")
        for row in power_table():
            print(
                "  {e:<8} {f:<19} {s:<20} {p}".format(
                    e=row["effect"],
                    f=row["first_n_at_target"],
                    s=row["stable_n_at_target"],
                    p=row["power_at_stable_n"],
                )
            )
        print(
            f"\nMIN_DISCORDANT_PAIRS = {MIN_DISCORDANT_PAIRS}, the stable column at effect {POWER_EFFECT}"
        )
        return 0

    if arguments.template is not None:
        arguments.template.mkdir(parents=True, exist_ok=True)
        (arguments.template / "schema.csv").write_text(TEMPLATE_SCHEMA_CSV, encoding="utf-8")
        (arguments.template / "catalog.csv").write_text(TEMPLATE_CATALOG_CSV, encoding="utf-8")
        print(f"wrote {arguments.template}/schema.csv and {arguments.template}/catalog.csv")
        return 0

    if arguments.schema is None:
        build_parser().print_help()
        return 1

    try:
        rows = read_schema(
            arguments.schema,
            identifier_column=arguments.identifier_column,
            label_column=arguments.label_column,
            encoding=arguments.encoding,
            delimiter=arguments.delimiter,
        )
        catalog_mapping: Dict[str, str] = {}
        catalog_digest = ""
        if arguments.catalog is not None:
            catalog_mapping = read_catalog(
                arguments.catalog,
                token_column=arguments.token_column,
                expansion_column=arguments.expansion_column,
                encoding=arguments.encoding,
                delimiter=arguments.delimiter,
            )
            catalog_digest = digest(arguments.catalog)
    except (OSError, KeyError, UnicodeDecodeError) as error:
        print(f"input error: {error}", file=sys.stderr)
        return 1

    if not rows.pairs:
        print(f"input error: no scorable rows in {arguments.schema}", file=sys.stderr)
        return 1

    report = build_report(
        rows.pairs,
        catalog_mapping,
        rows=rows,
        schema_digest=digest(arguments.schema),
        catalog_digest=catalog_digest,
    )

    problems = redaction_problems(report)
    if problems:  # pragma: no cover - a leak is a defect in this module
        print("REPORT NOT WRITTEN -- it carries input text:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    print(render(report))
    if arguments.out is not None:
        arguments.out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nwrote {arguments.out} -- read it before you send it")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
