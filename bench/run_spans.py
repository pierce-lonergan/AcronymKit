#!/usr/bin/env python3
"""Score abbreviation and long-form *span detection* on PLOD-CW.

Why a second extraction harness exists
--------------------------------------
Every extraction number in this repository comes from MED1250: one corpus, one
domain, one annotation convention, and a tuning set at that. PLOD is the second
corpus. It is a different corpus, a different genre (article body text rather
than abstracts), a different annotation provenance (semi-automatic, from PLOS's
own abbreviation index) and — decisively — a different *task*.

It is **not** a different domain, and ``bench/splits.toml`` is wrong to file it
as the "non-biomedical counterweight". PLOD is drawn from PLOS journals and its
own dataset card calls it scientific-domain; the text is dominated by life
sciences. So nothing here speaks to how the extractor behaves on legal,
financial or general-web prose, and reading it that way would be the most
damaging available misreading of these numbers. See D-017.

PLOD labels abbreviation spans and long-form spans and never pairs them.
``bench/splits.toml`` already ruled that deriving pairs from adjacency would
make part of the gold standard ours, and a gold standard we partly invented
cannot adjudicate our own system. That conclusion stands, so this runner does
not derive anything. It scores PLOD's own task:

* **short-form span detection** — did we identify the abbreviation spans?
* **long-form span detection** — did we identify the expansion spans?

Two separate scores. No pairing, anywhere.

The three choices that decide what the numbers mean
--------------------------------------------------
**1. Detokenisation.** PLOD ships tokens; our extractor takes prose. Text is
reconstructed with per-token character offsets recorded, the extractor is run on
it, and its character spans are mapped back to token index sets so the
comparison happens in *token* space, where the annotation lives. Both joins that
``bench.corpora.detokenise`` offers are run and reported: ``tight`` welds
punctuation and hyphens back on, ``spaced`` puts one space between every pair of
tokens and invents nothing. Reporting one of them alone would put an arbitrary
choice inside a number.

**2. Two match conventions, always labelled.** ``exact`` requires the predicted
token index set to equal the gold one. ``overlap`` requires only a non-empty
intersection, matched one-to-one so a single sprawling prediction cannot claim
several gold spans. They differ a lot here, and quoting one unlabelled is how
comparisons become dishonest by accident.

**3. Everything goes through one localiser.** The external baselines return
``(short, long)`` strings and no offsets, so their spans have to be found in the
text. acronymkit *does* report offsets — and the headline rows still use the
localiser, because scoring our own row through a privileged path would flatter
it. The native-offset rows are recorded beside them under a ``.native`` run id
so the localiser's cost is visible rather than assumed.

Usage::

    python tools/fetch_data.py plod-cw-test plod-cw-dev plod-cw-train
    python bench/run_spans.py --save
    python bench/run_spans.py --save --split all
    python bench/run_spans.py --save --system pyab3p --system scispacy \\
        --system abbreviations --system abbreviation_extractor \\
        --interpreter C:/akbench/Scripts/python.exe
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from bench import corpora  # noqa: E402
from bench.run_extraction import (  # noqa: E402
    EXTERNAL_SYSTEMS,
    dedupe_per_document,
    predict_acronymkit,
    predict_external,
    save_results,
)

Pair = tuple[str, str]
CharSpan = tuple[int, int]

#: The label pair PLOD annotates, and the two conventions each is scored under.
LABELS = ("short_form", "long_form")
CONVENTIONS = ("exact", "overlap")

#: acronymkit rows, one per named operating point. Recorded as profile names
#: rather than raw settings so the table lines up with the MED1250 profile table
#: in docs/EVALUATION.md.
PROFILES = ("high_precision", "general", "biomedical")

#: Display name of the trivial baseline, referenced when it is excluded from a
#: cross-system union.
TRIVIAL_ROW = "all-caps token (trivial)"

#: Bracket tokens whose presence beside a gold abbreviation makes that
#: abbreviation *reachable* by a parenthetical definition algorithm at all.
_BRACKETS_OPEN = frozenset({"(", "["})
_BRACKETS_CLOSE = frozenset({")", "]"})

_WHITESPACE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# predictions
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SpanPrediction:
    """One document's predicted spans, as token index sets.

    Attributes:
        short_forms: Predicted abbreviation spans.
        long_forms: Predicted long-form spans.
    """

    short_forms: tuple[frozenset, ...] = ()
    long_forms: tuple[frozenset, ...] = ()

    def of(self, label: str) -> tuple[frozenset, ...]:
        """The spans for ``"short_form"`` or ``"long_form"``."""
        return self.short_forms if label == "short_form" else self.long_forms


def char_span_to_tokens(span: CharSpan, offsets: Sequence[CharSpan]) -> frozenset:
    """Map a half-open character span onto the token indices it touches.

    Any overlap counts. A predicted long form that swallows the ``"1,4 -"`` in
    front of ``"dithiothreitol"`` therefore claims three tokens where the
    annotation has one — which is exactly the disagreement the ``exact`` and
    ``overlap`` conventions are there to separate.
    """
    start, end = span
    if end <= start:
        return frozenset()
    return frozenset(
        index
        for index, (token_start, token_end) in enumerate(offsets)
        if token_start < end and start < token_end
    )


def _occurrences(text: str, needle: str) -> list[CharSpan]:
    """Every place ``needle`` appears in ``text``, verbatim or whitespace-flexibly.

    The verbatim pass is tried first and is what nearly always fires: a
    Schwartz & Hearst implementation returns substrings of its input. The
    fallback exists for systems that normalise internal whitespace before
    returning, and a prediction that matches under neither is dropped and
    counted rather than guessed at.
    """
    if not needle:
        return []
    found: list[CharSpan] = []
    start = text.find(needle)
    while start != -1:
        found.append((start, start + len(needle)))
        start = text.find(needle, start + 1)
    if found:
        return found
    parts = [part for part in _WHITESPACE.split(needle.strip()) if part]
    if not parts:
        return []
    pattern = r"\s*".join(re.escape(part) for part in parts)
    return [(match.start(), match.end()) for match in re.finditer(pattern, text)]


def locate_pair(text: str, short: str, long_form: str) -> Optional[tuple[CharSpan, CharSpan]]:
    """Find the occurrence of each form that best explains them as one definition.

    A short form such as ``"S"`` occurs all over a sentence, so picking the
    first occurrence would attribute the prediction to the wrong token. The
    occurrences chosen are the pair with the smallest gap between them, which is
    what "definition" means positionally, with ties broken leftmost for
    determinism.

    Returns:
        ``(short_form_span, long_form_span)``, or ``None`` when either form
        cannot be found at all.
    """
    shorts = _occurrences(text, short)
    longs = _occurrences(text, long_form)
    if not shorts or not longs:
        return None
    ranked = [
        (max(0, max(s[0], lf[0]) - min(s[1], lf[1])), s[0], lf[0], s, lf)
        for s in shorts
        for lf in longs
    ]
    _, _, _, best_short, best_long = min(ranked)
    return best_short, best_long


def localise(
    predictions: dict[str, list[Pair]],
    documents: Sequence[corpora.SpanDocument],
    style: str,
) -> tuple[dict[str, SpanPrediction], int, int]:
    """Turn ``(short, long)`` strings into token index sets, uniformly for every system.

    Args:
        predictions: ``{uid: [(short, long), ...]}`` as the extraction harness
            already produces for acronymkit and for every external baseline.
        documents: The span corpus, for the text and token offsets.
        style: Detokenisation style; must match the one the system was run on.

    Returns:
        ``(spans, unlocated, total)`` — the per-document spans, and how many
        predicted pairs could not be found in the text out of how many were
        offered. A localiser that silently loses predictions would understate
        every external baseline, so the loss is counted and reported.
    """
    located: dict[str, SpanPrediction] = {}
    unlocated = 0
    total = 0
    for document in documents:
        text, offsets = document.render(style)
        shorts: list[frozenset] = []
        longs: list[frozenset] = []
        for short, long_form in predictions.get(document.uid, []):
            total += 1
            found = locate_pair(text, short, long_form)
            if found is None:
                unlocated += 1
                continue
            shorts.append(char_span_to_tokens(found[0], offsets))
            longs.append(char_span_to_tokens(found[1], offsets))
        located[document.uid] = SpanPrediction(_distinct(shorts), _distinct(longs))
    return located, unlocated, total


def _distinct(spans: Sequence[frozenset]) -> tuple[frozenset, ...]:
    """Drop empties and repeats, order preserved.

    Two different predicted pairs can land on the same tokens — most obviously
    when a document defines the same abbreviation twice. The gold standard has
    no repeated span, so counting a repeat as a second prediction would
    manufacture a false positive. Applied to every system alike.
    """
    seen: set = set()
    kept: list[frozenset] = []
    for span in spans:
        if span and span not in seen:
            seen.add(span)
            kept.append(span)
    return tuple(kept)


def predict_acronymkit_native(
    documents: Sequence[corpora.SpanDocument], style: str, **overrides: object
) -> tuple[dict[str, SpanPrediction], float]:
    """Run our extractor and keep the character offsets it reports itself.

    This is the control on :func:`localise`, not the headline: every other row
    has to have its spans found by string search, so ours does too. The gap
    between this row and the corresponding located row is the localiser's cost.
    """
    from acronymkit import AcronymEngine, Config

    engine = AcronymEngine(Config(**overrides))
    predictions: dict[str, SpanPrediction] = {}
    started = time.perf_counter()
    for document in documents:
        text, offsets = document.render(style)
        pairs = engine.extract_definitions(text)
        predictions[document.uid] = SpanPrediction(
            _distinct([char_span_to_tokens(pair.short_form_span, offsets) for pair in pairs]),
            _distinct([char_span_to_tokens(pair.long_form_span, offsets) for pair in pairs]),
        )
    return predictions, time.perf_counter() - started


def predict_all_caps(documents: Sequence[corpora.SpanDocument]) -> dict[str, SpanPrediction]:
    """The trivial baseline: every all-caps token of length 2+ is a short form.

    It exists to put a floor under the table. A span-detection F1 is not
    intuitively calibrated — is 40 good? — and a rule anyone could write in one
    line answers that. It predicts no long forms at all, by construction, so its
    long-form row is zero and is printed rather than hidden.

    It works in token space directly, which spares it the detokenisation the
    real systems pay for. That is an advantage, it is small, and it is stated.
    """
    predictions: dict[str, SpanPrediction] = {}
    for document in documents:
        shorts = [
            frozenset({index})
            for index, token in enumerate(document.tokens)
            if len(token) >= 2 and token == token.upper() and any(c.isalpha() for c in token)
        ]
        predictions[document.uid] = SpanPrediction(_distinct(shorts), ())
    return predictions


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SpanScore:
    """Precision, recall and F1 for one label under one match convention."""

    label: str
    convention: str
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def f1(self) -> float:
        precision, recall = self.precision, self.recall
        total = precision + recall
        return 2 * precision * recall / total if total else 0.0


def match(gold: Sequence[frozenset], predicted: Sequence[frozenset], convention: str) -> set:
    """Indices of the gold spans a system got, under one convention.

    ``exact`` consumes an identical token index set. ``overlap`` consumes the
    first unclaimed gold span sharing any token, matched **one-to-one**: without
    that, a single prediction spanning half the sentence would score against
    every gold span in it and overlap-recall would stop meaning anything.

    Greedy in corpus order rather than a maximum bipartite matching, which is
    equivalent here because gold spans within a document are disjoint by
    construction, and the predicted spans are de-duplicated before they arrive.
    """
    claimed: set = set()
    for prediction in predicted:
        for index, gold_span in enumerate(gold):
            if index in claimed:
                continue
            hit = prediction == gold_span if convention == "exact" else bool(prediction & gold_span)
            if hit:
                claimed.add(index)
                break
    return claimed


def score(
    documents: Sequence[corpora.SpanDocument], predictions: dict[str, SpanPrediction]
) -> tuple[dict[str, SpanScore], dict[str, set]]:
    """Score every label/convention combination over the corpus.

    Returns:
        ``(scores, matched)`` — scores keyed ``"<label>.<convention>"``, and the
        set of ``(uid, gold index)`` pairs each combination matched, which is
        what makes a cross-system union computable afterwards.
    """
    tallies = {f"{label}.{convention}": [0, 0, 0] for label in LABELS for convention in CONVENTIONS}
    matched: dict[str, set] = {key: set() for key in tallies}

    for document in documents:
        prediction = predictions.get(document.uid, SpanPrediction())
        gold_by_label = {
            "short_form": document.short_form_spans,
            "long_form": document.long_form_spans,
        }
        for label in LABELS:
            gold = [frozenset(range(start, end)) for start, end in gold_by_label[label]]
            predicted = prediction.of(label)
            for convention in CONVENTIONS:
                key = f"{label}.{convention}"
                claimed = match(gold, predicted, convention)
                tallies[key][0] += len(claimed)
                tallies[key][1] += len(predicted) - len(claimed)
                tallies[key][2] += len(gold) - len(claimed)
                matched[key].update((document.uid, index) for index in claimed)

    scores = {
        key: SpanScore(key.split(".")[0], key.split(".")[1], *counts)
        for key, counts in tallies.items()
    }
    return scores, matched


# ---------------------------------------------------------------------------
# corpus description
# ---------------------------------------------------------------------------
def corpus_statistics(documents: Sequence[corpora.SpanDocument]) -> dict:
    """Facts about PLOD that bound what any definition extractor can score.

    The important one is ``short_form_spans_bracket_adjacent``. PLOD tags every
    *mention* of an abbreviation, defined or not — ``SDS`` in "a discontinuous
    SDS gel", ``wk`` for "week", ``pY232`` four times in one sentence. A
    Schwartz & Hearst extractor only ever returns abbreviations standing in one
    of its two parenthetical arrangements, so that count is a hard ceiling on
    its recall here, imposed by the corpus's annotation convention rather than
    by the algorithm. Reading the recall column without it would be reading a
    number against the wrong denominator.

    Both arrangements count, and this is deliberately the *generous* reading:
    ``long form (SF)`` puts the abbreviation inside the brackets, and
    ``SF (long form)`` puts it immediately in front of one. Counting only the
    first would flatter every system in the table by shrinking the denominator
    it is measured against, so the looser figure is the one reported as the
    ceiling and the stricter one is recorded beside it.
    """
    tokens = 0
    short_spans = 0
    long_spans = 0
    inside = 0
    adjacent = 0
    interrupted = 0
    for document in documents:
        tokens += len(document.tokens)
        short_spans += len(document.short_form_spans)
        long_spans += len(document.long_form_spans)
        for start, end in document.short_form_spans:
            before = document.tokens[start - 1] if start else ""
            after = document.tokens[end] if end < len(document.tokens) else ""
            enclosed = before in _BRACKETS_OPEN or after in _BRACKETS_CLOSE
            inside += enclosed
            adjacent += enclosed or after in _BRACKETS_OPEN
        for start, _ in document.long_form_spans:
            # A long-form span the reader had to open on an I-LF tag with no
            # B-LF in front of it. PLOD sometimes tags an AC token in the middle
            # of a long form, cutting the annotation in two. Counted so the
            # gold's own noise is on the record rather than absorbed silently.
            if document.ner_tags[start].startswith("I-"):
                interrupted += 1
    return {
        "documents": len(documents),
        "tokens": tokens,
        "short_form_spans": short_spans,
        "long_form_spans": long_spans,
        "long_form_spans_opened_on_i_tag": interrupted,
        "short_form_spans_inside_brackets": inside,
        "short_form_spans_bracket_adjacent": adjacent,
        "short_form_spans_bracket_adjacent_pct": round(100 * adjacent / max(short_spans, 1), 2),
    }


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def render(rows: Sequence[tuple[str, dict[str, SpanScore]]]) -> str:
    """One table: every system, both labels, both conventions, nothing elided.

    Two lines per system rather than a compressed one, because the interesting
    disagreement on this corpus is between *precision and recall within a
    label*, and a table that shows only F1 hides it.
    """
    header = (
        f"{'system':<30} {'label':<11} "
        f"{'exP':>6} {'exR':>6} {'exF1':>6} | {'ovP':>6} {'ovR':>6} {'ovF1':>6}"
    )
    lines = [header, "-" * len(header)]
    for name, scores in rows:
        for index, label in enumerate(LABELS):
            exact = scores[f"{label}.exact"]
            overlap = scores[f"{label}.overlap"]
            lines.append(
                f"{name if index == 0 else '':<30} {label:<11} "
                f"{exact.precision * 100:6.2f} {exact.recall * 100:6.2f} "
                f"{exact.f1 * 100:6.2f} | "
                f"{overlap.precision * 100:6.2f} {overlap.recall * 100:6.2f} "
                f"{overlap.f1 * 100:6.2f}"
            )
    lines.append("")
    lines.append("ex = exact token-set match, ov = any-overlap match, matched one-to-one.")
    lines.append("Both conventions are printed because they differ and one alone would mislead.")
    return "\n".join(lines)


def union_recall(
    matched_by_system: dict[str, dict[str, set]],
    members: Sequence[str],
    gold_totals: dict[str, int],
    name: str,
    context: dict,
) -> dict:
    """Recall of the union over ``members`` — the ceiling those systems share.

    The idiom D-011 established for MED1250: a per-system recall says how good
    one system is, while the union says how much of the gold is reachable *at
    all* by anything in the table. On this corpus that distinction carries most
    of the finding, because the gap between the two is the corpus's annotation
    convention rather than any system's ability.
    """
    record: dict = {"system": f"oracle union ({name})", "members": sorted(members), **context}
    for label in LABELS:
        for convention in CONVENTIONS:
            key = f"{label}.{convention}"
            union: set = set()
            for member in members:
                union |= matched_by_system[member][key]
            record[f"{key}_recall"] = round(100 * len(union) / max(gold_totals[label], 1), 2)
            record[f"{key}_true_positives"] = len(union)
    return record


def entry(scores: dict[str, SpanScore], **extra: object) -> dict:
    """One ``bench/results.json`` record: every convention, no derived deltas."""
    record: dict = dict(extra)
    for key, value in scores.items():
        record[f"{key}_precision"] = round(value.precision * 100, 2)
        record[f"{key}_recall"] = round(value.recall * 100, 2)
        record[f"{key}_f1"] = round(value.f1 * 100, 2)
        record[f"{key}_true_positives"] = value.true_positives
        record[f"{key}_false_positives"] = value.false_positives
        record[f"{key}_false_negatives"] = value.false_negatives
    return record


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--split", default="test", choices=list(corpora.PLOD_CW_SPLITS))
    parser.add_argument(
        "--style",
        action="append",
        choices=list(corpora.DETOKENISE_STYLES),
        help="repeatable; defaults to both, because reporting one hides a choice",
    )
    parser.add_argument(
        "--system",
        action="append",
        choices=sorted(set(EXTERNAL_SYSTEMS)),
        help="external baseline to include; repeatable, needs --interpreter",
    )
    parser.add_argument("--interpreter", default=sys.executable)
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    args = parser.parse_args(argv)

    from acronymkit.config import EXTRACTION_PROFILES
    from acronymkit.enums import ExtractionProfile

    documents = corpora.read_plod_cw(split=args.split)
    styles = args.style or list(corpora.DETOKENISE_STYLES)
    externals = args.system or []

    stats = corpus_statistics(documents)
    print(
        f"PLOD-CW {args.split}: {stats['documents']:,} sentences, {stats['tokens']:,} tokens, "
        f"{stats['short_form_spans']:,} short-form spans, "
        f"{stats['long_form_spans']:,} long-form spans"
    )
    print(
        f"  of the short-form spans, {stats['short_form_spans_bracket_adjacent']:,} "
        f"({stats['short_form_spans_bracket_adjacent_pct']:.2f} %) stand in one of the two "
        "parenthetical arrangements -- the ceiling on recall for any "
        "definition-based algorithm"
    )
    print()

    recorded: dict = {
        f"spans.plod.{args.split}.corpus": {"corpus": f"plod_cw_{args.split}", **stats}
    }

    for style in styles:
        rows: list[tuple[str, dict[str, SpanScore]]] = []
        matched_by_system: dict[str, dict[str, set]] = {}
        suffix = "" if style == "tight" else f"_{style}"
        corpus_key = f"plod_cw_{args.split}{suffix}"
        text_documents = corpora.read_plod_cw_text(split=args.split, style=style)

        for profile in PROFILES:
            settings = EXTRACTION_PROFILES[ExtractionProfile.coerce(profile)]

            native, elapsed = predict_acronymkit_native(documents, style, **settings)
            native_scores, _ = score(documents, native)
            rows.append((f"acronymkit/{profile} (native spans)", native_scores))
            recorded[f"spans.plod.{args.split}.{style}.acronymkit.{profile}.native"] = entry(
                native_scores,
                corpus=corpus_key,
                system="acronymkit",
                profile=profile,
                span_source="native offsets",
                detokenisation=style,
                documents=len(documents),
                elapsed_seconds=round(elapsed, 4),
                docs_per_second=round(len(documents) / max(elapsed, 1e-9), 1),
            )

            started = time.perf_counter()
            strings = predict_acronymkit(text_documents, **settings)
            elapsed = time.perf_counter() - started
            spans, unlocated, total = localise(dedupe_per_document(strings), documents, style)
            located_scores, matched = score(documents, spans)
            rows.append((f"acronymkit/{profile}", located_scores))
            matched_by_system[f"acronymkit/{profile}"] = matched
            recorded[f"spans.plod.{args.split}.{style}.acronymkit.{profile}"] = entry(
                located_scores,
                corpus=corpus_key,
                system="acronymkit",
                profile=profile,
                span_source="string localiser",
                detokenisation=style,
                documents=len(documents),
                predicted_pairs=total,
                unlocated_pairs=unlocated,
                elapsed_seconds=round(elapsed, 4),
                docs_per_second=round(len(documents) / max(elapsed, 1e-9), 1),
            )

        for system in externals:
            strings, elapsed, _ = predict_external(
                system, text_documents, args.interpreter, corpus_key, None
            )
            spans, unlocated, total = localise(dedupe_per_document(strings), documents, style)
            external_scores, matched = score(documents, spans)
            rows.append((system, external_scores))
            matched_by_system[system] = matched
            recorded[f"spans.plod.{args.split}.{style}.{system}"] = entry(
                external_scores,
                corpus=corpus_key,
                system=system,
                span_source="string localiser",
                detokenisation=style,
                documents=len(documents),
                predicted_pairs=total,
                unlocated_pairs=unlocated,
                elapsed_seconds=round(elapsed, 4),
                docs_per_second=round(len(documents) / max(elapsed, 1e-9), 1),
            )

        trivial = predict_all_caps(documents)
        trivial_scores, matched = score(documents, trivial)
        rows.append((TRIVIAL_ROW, trivial_scores))
        matched_by_system[TRIVIAL_ROW] = matched
        recorded[f"spans.plod.{args.split}.{style}.allcaps"] = entry(
            trivial_scores,
            corpus=corpus_key,
            system="allcaps",
            span_source="token space, no detokenisation",
            detokenisation=style,
            documents=len(documents),
        )

        gold_totals = {
            "short_form": stats["short_form_spans"],
            "long_form": stats["long_form_spans"],
        }

        # Two unions, because they answer different questions. The first says
        # what the whole table reaches; the second excludes the trivial
        # all-caps rule, which is not a definition extractor and would otherwise
        # let a one-line heuristic flatter the ceiling every real system shares.
        context = {"corpus": corpus_key, "detokenisation": style}
        everything = union_recall(
            matched_by_system, list(matched_by_system), gold_totals, "all rows", context
        )
        definitional = union_recall(
            matched_by_system,
            [name for name in matched_by_system if name != TRIVIAL_ROW],
            gold_totals,
            "definition extractors",
            context,
        )
        recorded[f"spans.plod.{args.split}.{style}.oracle"] = everything
        recorded[f"spans.plod.{args.split}.{style}.oracle_definitional"] = definitional

        print(f"=== detokenisation: {style} ===")
        print(render(rows))
        for record in (definitional, everything):
            print(
                f"  {record['system']:<38} overlap recall: "
                f"short-form {record['short_form.overlap_recall']:6.2f} %, "
                f"long-form {record['long_form.overlap_recall']:6.2f} %"
            )
        print()

    if args.save:
        print(f"saved {len(recorded)} run(s) to {save_results(recorded).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
