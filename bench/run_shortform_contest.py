#!/usr/bin/env python3
"""Is the shipped extractor really sixteen points worse than a one-line rule?

The comparison this runner exists to settle
-------------------------------------------
``bench/results.json`` records, on PLOD-CW with every split pooled, short-form
exact F1 of ``52.56`` for ``acronymkit/high_precision`` and ``68.62`` for
``allcaps`` -- the one-line rule in ``bench/run_spans.py`` that calls every
all-caps token an abbreviation. D-049 quoted the pair and used it to constrain
how the W11 emission model may be pitched. Both figures are real, both are on
the only held-out corpus this project has for the label, and read side by side
they say the flagship extractor loses its own task to four lines of Python.

**They are not a like-for-like comparison, and this runner measures by how
much.** Two structural asymmetries sit underneath them, and each one handicaps
a different competitor:

* PLOD tags every *occurrence* of an abbreviation, defined or not.
  ``extract()`` emits a ``(short, long)`` **pair** and cannot emit a short form
  it has not paired -- ``long_form=None`` is a ``ValidationError`` and D-041
  closed the class. So every gold occurrence standing in no definitional
  arrangement is a false negative this library cannot ever convert, at any
  setting, without a change of emission model.
* ``predict_all_caps`` admits a single token of length 2+ that equals its own
  uppercase. Every gold short form outside that shape is a false negative *it*
  cannot ever convert.

So the two systems are handicapped on disjoint parts of the gold, and a single
F1 over the whole corpus reports the sum of two different disabilities.

The 2x2, and why the regions are these regions
----------------------------------------------
Four nested evaluation regions, one per cell of a two-factor design. Each is a
**predicate on a token span**, so it applies identically to a gold span and to a
predicted span -- which is what makes precision inside a region well defined
rather than a recall-only rescoring:

===========================  ============================================
region                       gold short-form spans it keeps
===========================  ============================================
``all``                      every one; reproduces the published rows
``caps``                     the ones ``predict_all_caps`` could admit
``definitional``             the ones standing beside a bracket
``definitional_caps``        both conditions; the strict contested region
===========================  ============================================

``definitional`` is ``bench.run_spans.corpus_statistics``'s
``short_form_spans_bracket_adjacent`` predicate, unchanged and re-derived here:
a bracket immediately before the span, or a closing or opening bracket
immediately after it. That function's own docstring already calls the count "a
hard ceiling on its recall here, imposed by the corpus's annotation convention
rather than by the algorithm", and deliberately takes the *generous* reading --
both parenthetical arrangements -- which enlarges the region with gold no
definition extractor reaches and therefore costs this library recall rather
than granting it.

**The region rules were fixed before any of these numbers were seen**, they are
properties of the corpus's own tokens rather than of any system's output, and
nothing here reads which individual span was missed or why. That distinction is
the one D-049 draws: PLOD may be scored and must not be diagnosed, because
reading a miss taxonomy is the act that turned MED1250 and both SDU-22 dev
splits into tuning sets. This runner has no error-listing mode for that reason.

The control that says the instrument is the same instrument
-----------------------------------------------------------
The ``all`` region must reproduce ``spans.plod.<split>.tight.*`` exactly, and
the ``definitional`` gold count must reproduce
``spans.plod.<split>.corpus.short_form_spans_bracket_adjacent``. Both are
checked against ``bench/results.json`` on every run, and ``--save`` refuses to
write anything if either disagrees.

The control that says what the metric cannot see
------------------------------------------------
``--pairing`` replays PLOD's own gold as a prediction twice: once paired
honestly, once with each document's long forms rotated against its short forms.
The two are scored, and they are the same row -- ``100.00`` on all four span
metrics either way -- because ``bench.run_spans.SpanPrediction`` has fields for
``short_forms`` and ``long_forms`` and **no slot for the edge between them**.
D-048 established this by permuting 1,376 of PLOD's gold long forms; this
re-derives it inside the runner that publishes the contested figures, with the
count of documents the rotation actually moved reported beside it, so a null
result arrives with its firing count attached.

The consequence is the one sentence this whole comparison turns on: **the span
scorer measures short-form detection, not extraction.** A win in the
``definitional`` column is evidence that this library puts the abbreviation
spans in the right places, and it is not evidence that it pairs them with the
right expansions. No corpus registered in ``bench/splits.toml`` can answer the
second question -- that is criterion 9, and it is open.

Usage::

    python tools/fetch_data.py plod-cw-test plod-cw-dev plod-cw-train
    python bench/run_shortform_contest.py
    python bench/run_shortform_contest.py --split all --split test --save
    python bench/run_shortform_contest.py --pairing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from bench import corpora  # noqa: E402
from bench.run_extraction import (  # noqa: E402
    dedupe_per_document,
    predict_acronymkit,
    save_results,
)
from bench.run_spans import (  # noqa: E402
    _BRACKETS_CLOSE,
    _BRACKETS_OPEN,
    CONVENTIONS,
    LABELS,
    PROFILES,
    SpanPrediction,
    localise,
    match,
    predict_acronymkit_native,
    predict_all_caps,
    score,
)

#: A predicate on ``(document, token index set)``.
Region = Callable[[corpora.SpanDocument, frozenset], bool]

#: Where the run ids this runner writes live in ``bench/results.json``.
PREFIX = "shortform_contest.plod"

#: The detokenisation this runner reports. ``docs/EVALUATION.md`` calls the
#: tight join primary and prices the other one; the contested figures are both
#: tight, so mixing joins into this table would put a second variable inside a
#: comparison that exists to isolate one.
STYLE = "tight"


# ---------------------------------------------------------------------------
# regions
# ---------------------------------------------------------------------------
def _bounds(span: frozenset) -> tuple[int, int]:
    """The half-open ``(start, end)`` of a contiguous token index set."""
    return min(span), max(span) + 1


def region_all(document: corpora.SpanDocument, span: frozenset) -> bool:
    """Every span. The control region, and the published one."""
    del document, span
    return True


def region_caps(document: corpora.SpanDocument, span: frozenset) -> bool:
    """The shape ``bench.run_spans.predict_all_caps`` admits.

    Transcribed from that function rather than approximated, because a region
    that differs from the baseline's own rule would let the baseline score
    false negatives inside a region defined as the place it cannot have any.
    """
    if len(span) != 1:
        return False
    token = document.tokens[min(span)]
    return len(token) >= 2 and token == token.upper() and any(c.isalpha() for c in token)


def region_definitional(document: corpora.SpanDocument, span: frozenset) -> bool:
    """Standing in one of the two parenthetical arrangements.

    The same predicate ``bench.run_spans.corpus_statistics`` counts as
    ``short_form_spans_bracket_adjacent``: an opening bracket immediately
    before, or either kind of bracket immediately after. Both arrangements
    count, which is the generous reading and the one that keeps gold no
    definition extractor can reach inside the denominator.
    """
    start, end = _bounds(span)
    before = document.tokens[start - 1] if start else ""
    after = document.tokens[end] if end < len(document.tokens) else ""
    return before in _BRACKETS_OPEN or after in _BRACKETS_CLOSE or after in _BRACKETS_OPEN


def region_definitional_caps(document: corpora.SpanDocument, span: frozenset) -> bool:
    """Both conditions: the region in which neither system is handicapped."""
    return region_definitional(document, span) and region_caps(document, span)


#: The 2x2, in the order the tables print it: no restriction, each factor
#: alone, then both.
REGIONS: tuple[tuple[str, Region], ...] = (
    ("all", region_all),
    ("caps", region_caps),
    ("definitional", region_definitional),
    ("definitional_caps", region_definitional_caps),
)


# ---------------------------------------------------------------------------
# scoring inside a region
# ---------------------------------------------------------------------------
def region_score(
    documents: Sequence[corpora.SpanDocument],
    predictions: dict,
    keep: Region,
    label: str = "short_form",
) -> dict:
    """Score one label inside one region, both match conventions.

    Gold spans failing ``keep`` are removed from the denominator; predicted
    spans failing ``keep`` are removed from the numerator's cost. Filtering
    both sides by the same predicate is what stops a region being a
    recall-only rescoring, where a system with an out-of-region false positive
    would keep the penalty and lose the chance to earn it back.

    Under ``exact`` this is exactly a restriction: a prediction equal to an
    in-region gold span is in-region by construction, so no gold becomes
    unmatchable. Under ``overlap`` it is not -- a prediction touching an
    in-region gold span can itself fail the predicate -- so the overlap columns
    are reported and are not the headline.
    """
    counts = {convention: [0, 0, 0] for convention in CONVENTIONS}
    gold_spans = 0
    predicted_spans = 0
    for document in documents:
        raw = document.short_form_spans if label == "short_form" else document.long_form_spans
        gold = [frozenset(range(start, end)) for start, end in raw]
        gold = [span for span in gold if keep(document, span)]
        predicted = [
            span
            for span in predictions.get(document.uid, SpanPrediction()).of(label)
            if keep(document, span)
        ]
        gold_spans += len(gold)
        predicted_spans += len(predicted)
        for convention in CONVENTIONS:
            claimed = match(gold, predicted, convention)
            counts[convention][0] += len(claimed)
            counts[convention][1] += len(predicted) - len(claimed)
            counts[convention][2] += len(gold) - len(claimed)

    record: dict = {"gold_spans": gold_spans, "predicted_spans": predicted_spans}
    for convention, (true_positives, false_positives, false_negatives) in counts.items():
        predicted_total = true_positives + false_positives
        gold_total = true_positives + false_negatives
        precision = true_positives / predicted_total if predicted_total else 0.0
        recall = true_positives / gold_total if gold_total else 0.0
        total = precision + recall
        f1 = 2 * precision * recall / total if total else 0.0
        record[f"{convention}_true_positives"] = true_positives
        record[f"{convention}_false_positives"] = false_positives
        record[f"{convention}_false_negatives"] = false_negatives
        record[f"{convention}_precision"] = round(precision * 100, 2)
        record[f"{convention}_recall"] = round(recall * 100, 2)
        record[f"{convention}_f1"] = round(f1 * 100, 2)
    return record


def contest_entry(
    documents: Sequence[corpora.SpanDocument], predictions: dict, /, **extra: object
) -> dict:
    """One ``bench/results.json`` record: every region, flattened under its name.

    The two data arguments are positional-only on purpose. ``extra`` carries
    the record's own ``corpus`` and ``documents`` fields, whose names this
    project fixed long before this runner existed, so either one as a keyword
    would otherwise collide with a parameter and raise at the call site.
    """
    record: dict = dict(extra)
    for name, keep in REGIONS:
        for key, value in region_score(documents, predictions, keep).items():
            record[f"{name}.{key}"] = value
    return record


# ---------------------------------------------------------------------------
# the pairing control
# ---------------------------------------------------------------------------
def replay_gold(
    documents: Sequence[corpora.SpanDocument], *, rotate: bool
) -> tuple[dict, int, int]:
    """PLOD's own gold, replayed as a prediction, optionally mis-paired.

    Pairs each document's short-form spans with its long-form spans in corpus
    order, then coarsens the pairs into the shape the span scorer consumes.
    With ``rotate`` the long forms are shifted by one before pairing, so a
    document with two or more of them is guaranteed to have every pair wrong.

    Returns:
        ``(predictions, documents_rotated, pairs_mispaired)`` -- the firing
        count for the null result this control produces, because a permutation
        that never permuted would prove nothing.
    """
    predictions: dict = {}
    rotated_documents = 0
    mispaired = 0
    for document in documents:
        shorts = [frozenset(range(start, end)) for start, end in document.short_form_spans]
        longs = [frozenset(range(start, end)) for start, end in document.long_form_spans]
        if rotate and len(longs) > 1:
            longs = longs[1:] + longs[:1]
            rotated_documents += 1
            mispaired += min(len(shorts), len(longs))
        predictions[document.uid] = SpanPrediction(tuple(shorts), tuple(longs))
    return predictions, rotated_documents, mispaired


# ---------------------------------------------------------------------------
# verification against the gated figures
# ---------------------------------------------------------------------------
def gated_runs() -> dict:
    """``bench/results.json``'s ``runs`` table, or an empty one."""
    path = REPO_ROOT / "bench" / "results.json"
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    runs = document.get("runs", {})
    return runs if isinstance(runs, dict) else {}


def verify(split: str, records: dict, runs: dict) -> list[str]:
    """Every way this runner's ``all`` region may disagree with the published rows.

    The whole decomposition is worthless if the unrestricted region does not
    reproduce the figures it decomposes, so the reproduction is a gate rather
    than a claim: ``--save`` refuses on any disagreement, and the messages name
    both sides.
    """
    problems: list[str] = []

    def compare(mine: str, theirs: str, field: str, region_field: str) -> None:
        record = records.get(mine)
        published = runs.get(theirs)
        if record is None or published is None or field not in published:
            problems.append(f"{theirs}.{field} is not in bench/results.json to compare against")
            return
        if record[region_field] != published[field]:
            problems.append(
                f"{mine}.{region_field} = {record[region_field]} but "
                f"{theirs}.{field} = {published[field]}"
            )

    base = f"{PREFIX}.{split}"
    published_base = f"spans.plod.{split}.{STYLE}"
    compare(
        f"{base}.regions",
        f"spans.plod.{split}.corpus",
        "short_form_spans",
        "all.gold_spans",
    )
    compare(
        f"{base}.regions",
        f"spans.plod.{split}.corpus",
        "short_form_spans_bracket_adjacent",
        "definitional.gold_spans",
    )
    for mine, theirs in (
        (f"{base}.allcaps", f"{published_base}.allcaps"),
        (
            f"{base}.acronymkit.high_precision",
            f"{published_base}.acronymkit.high_precision",
        ),
        (
            f"{base}.acronymkit.high_precision.native",
            f"{published_base}.acronymkit.high_precision.native",
        ),
    ):
        for metric in ("precision", "recall", "f1"):
            compare(mine, theirs, f"short_form.exact_{metric}", f"all.exact_{metric}")
    return problems


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def render(rows: Sequence[tuple[str, dict]]) -> str:
    """The 2x2 as one table, F1 per region with its denominator beside it."""
    header = f"{'system':<42} " + " ".join(f"{name:>19}" for name, _ in REGIONS)
    lines = [header, "-" * len(header)]
    denominators = " ".join(f"{rows[0][1][name + '.gold_spans']:>19,}" for name, _ in REGIONS)
    lines.append(f"{'gold short-form spans':<42} {denominators}")
    lines.append("-" * len(header))
    for name, record in rows:
        cells = " ".join(
            f"{record[f'{region}.exact_precision']:6.2f}/"
            f"{record[f'{region}.exact_recall']:6.2f}/"
            f"{record[f'{region}.exact_f1']:6.2f}"
            for region, _ in REGIONS
        )
        lines.append(f"{name:<42} {cells}")
    lines.append("")
    lines.append("cells are exact precision / recall / F1 on the short-form label.")
    lines.append(
        "`allcaps` scores 100.00 recall in the two caps regions BY CONSTRUCTION -- it emits "
        "every token they are defined by, so only its precision column is informative there."
    )
    return "\n".join(lines)


def render_lead(rows: Sequence[tuple[str, dict]], contenders: tuple[str, str]) -> str:
    """The contested pair alone, region by region, with the signed lead.

    The four-region table above carries every row and is the evidence; this is
    the one comparison the whole runner exists to settle, printed so that the
    direction of the result is read off the rows rather than reconstructed from
    them. A difference of two F1 values is arithmetic on the line above it and
    is deliberately not saved as a field: ``bench/results.json`` records no
    derived deltas, and a delta stored beside its operands is a third number
    that can go stale on its own.
    """
    lookup = dict(rows)
    left, right = contenders
    lines = [
        f"  {'region':<20} {'acronymkit':>10} {'allcaps':>9}   lead",
    ]
    for region, _ in REGIONS:
        ours = lookup[left][f"{region}.exact_f1"]
        theirs = lookup[right][f"{region}.exact_f1"]
        winner = "acronymkit" if ours >= theirs else "allcaps"
        lines.append(
            f"  {region:<20} {ours:>10.2f} {theirs:>9.2f}   {winner:<10} {abs(ours - theirs):+6.2f}"
        )
    return "\n".join(lines)


def _profile_rows(
    documents: Sequence[corpora.SpanDocument], split: str
) -> tuple[dict, list[tuple[str, dict]]]:
    """Every acronymkit row for one split: located for each profile, plus native."""
    from acronymkit.config import EXTRACTION_PROFILES
    from acronymkit.enums import ExtractionProfile

    text_documents = corpora.read_plod_cw_text(split=split, style=STYLE)
    records: dict = {}
    rows: list[tuple[str, dict]] = []
    for profile in PROFILES:
        settings = EXTRACTION_PROFILES[ExtractionProfile.coerce(profile)]
        strings = predict_acronymkit(text_documents, **settings)
        located, unlocated, total = localise(dedupe_per_document(strings), documents, STYLE)
        record = contest_entry(
            documents,
            located,
            corpus=f"plod_cw_{split}",
            system="acronymkit",
            profile=profile,
            span_source="string localiser",
            detokenisation=STYLE,
            documents=len(documents),
            predicted_pairs=total,
            unlocated_pairs=unlocated,
        )
        records[f"{PREFIX}.{split}.acronymkit.{profile}"] = record
        rows.append((f"acronymkit/{profile}", record))

        if profile == "high_precision":
            native, _ = predict_acronymkit_native(documents, STYLE, **settings)
            native_record = contest_entry(
                documents,
                native,
                corpus=f"plod_cw_{split}",
                system="acronymkit",
                profile=profile,
                span_source="native offsets",
                detokenisation=STYLE,
                documents=len(documents),
            )
            records[f"{PREFIX}.{split}.acronymkit.{profile}.native"] = native_record
            rows.append((f"acronymkit/{profile} (native spans)", native_record))
    return records, rows


def _pairing_control(documents: Sequence[corpora.SpanDocument], split: str) -> dict:
    """The gold-replay control, honest and rotated, as one record."""
    record: dict = {
        "corpus": f"plod_cw_{split}",
        "system": "gold replayed as a prediction",
        "documents": len(documents),
        "gold_long_form_spans": sum(len(d.long_form_spans) for d in documents),
    }
    for name, rotate in (("honest", False), ("rotated", True)):
        predictions, rotated_documents, mispaired = replay_gold(documents, rotate=rotate)
        scores, _ = score(documents, predictions)
        if rotate:
            record["documents_rotated"] = rotated_documents
            record["pairs_mispaired"] = mispaired
        for label in LABELS:
            for convention in CONVENTIONS:
                key = f"{label}.{convention}"
                record[f"{name}.{key}_f1"] = round(scores[key].f1 * 100, 2)
    return record


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--split",
        action="append",
        choices=list(corpora.PLOD_CW_SPLITS),
        help="repeatable; defaults to the pooled corpus and the test split",
    )
    parser.add_argument(
        "--pairing",
        action="store_true",
        help="also run the gold-replay control that shows the metric cannot see pairing",
    )
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    args = parser.parse_args(argv)

    splits = args.split or ["all", "test"]
    runs = gated_runs()
    recorded: dict = {}
    problems: list[str] = []

    for split in splits:
        documents = corpora.read_plod_cw(split=split)
        census: dict = {
            "corpus": f"plod_cw_{split}",
            "documents": len(documents),
            "tokens": sum(len(document.tokens) for document in documents),
        }
        total = sum(len(document.short_form_spans) for document in documents)
        for name, keep in REGIONS:
            kept = sum(
                1
                for document in documents
                for start, end in document.short_form_spans
                if keep(document, frozenset(range(start, end)))
            )
            census[f"{name}.gold_spans"] = kept
            census[f"{name}.gold_share_pct"] = round(100 * kept / max(total, 1), 2)
        recorded[f"{PREFIX}.{split}.regions"] = census

        records, rows = _profile_rows(documents, split)
        recorded.update(records)

        trivial = predict_all_caps(documents)
        trivial_record = contest_entry(
            documents,
            trivial,
            corpus=f"plod_cw_{split}",
            system="allcaps",
            span_source="token space, no detokenisation",
            detokenisation=STYLE,
            documents=len(documents),
        )
        recorded[f"{PREFIX}.{split}.allcaps"] = trivial_record
        rows.append(("allcaps (one-line rule)", trivial_record))

        if args.pairing:
            recorded[f"{PREFIX}.{split}.pairing_blind"] = _pairing_control(documents, split)

        print(
            f"PLOD-CW {split}: {census['documents']:,} sentences, "
            f"{census['tokens']:,} tokens, {total:,} gold short-form spans"
        )
        print()
        print(render(rows))
        print()
        print(
            render_lead(
                rows, ("acronymkit/high_precision (native spans)", "allcaps (one-line rule)")
            )
        )
        print()
        if args.pairing:
            control = recorded[f"{PREFIX}.{split}.pairing_blind"]
            print(
                "  gold replayed as a prediction, rotated on "
                f"{control['documents_rotated']:,} of {census['documents']:,} documents, "
                f"{control['pairs_mispaired']:,} pairs wrong:"
            )
            for label in LABELS:
                print(
                    f"    {label:<11} exact F1 honest {control[f'honest.{label}.exact_f1']:6.2f}"
                    f"   rotated {control[f'rotated.{label}.exact_f1']:6.2f}"
                )
            print("  the span scorer has no slot for the edge, so the rows are the same row.")
            print()

        found = verify(split, recorded, runs)
        problems += found
        status = "reproduces the published rows" if not found else "DISAGREES"
        print(f"  control: the `all` region {status} for spans.plod.{split}.{STYLE}.*")
        for problem in found:
            print(f"    {problem}")
        print()

    if problems:
        print(
            f"{len(problems)} disagreement(s) with bench/results.json. "
            "Not saving: a decomposition that does not reproduce what it decomposes "
            "is measuring something else."
        )
        return 1

    if args.save:
        print(f"saved {len(recorded)} run(s) to {save_results(recorded).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
