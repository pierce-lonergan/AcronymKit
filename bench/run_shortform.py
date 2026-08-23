#!/usr/bin/env python3
"""Where the extraction gap to ``pyab3p`` actually lives, and what closes it.

Seven experiments have tried to close the 5-point MED1250 gap by changing how a
*long form* is chosen. This runner measures the other half of the problem --
which *short form* is admitted in the first place -- and re-derives the
selection-ceiling statistic that D-012 used to close the long-form line of
attack.

Four measurements, each independently selectable:

``--attribute``
    Every acronymkit miss on MED1250, attributed with the extractor's own
    machinery rather than a regex approximation of it: selection, matching, or
    one of three distinct short-form-admission failures. The same table reports
    how many of each ``pyab3p`` recovers, which is what turns "it is better"
    into a statement about where.

``--ceiling``
    D-012's tie statistic, conditioned on the brackets the greedy rule gets
    *wrong*. D-012 computes it over every bracket whose gold span is reachable,
    which is dominated by the ~78 % already correct. It also scores a candidate
    with ``best_match``, which rescans every start inside the suffix it is
    handed and therefore rates the suffix rather than the span; this uses
    ``match(..., start=0)`` so a longer span is a genuinely different claim.

``--variants``
    Two short-form-span defects, measured alone and together, on the frozen
    dev/test halves and on the whole corpus, across all three extraction
    profiles. Both are bugs rather than knobs: ``_trim_span`` strips a balanced
    closing bracket off ``FEV(1)``, and ``_short_form_in`` never offers a
    two-word short form when the first word alone is admissible.

``--relaxations``
    A rejected relaxation, recorded because it loses: treating a digit in the
    short form as optional when nothing else aligns.

``--gates DIR``
    What Ab3P's own data tables are worth as admission gates, and whether a
    unigram frequency signal can decide a span boundary at all, pointed at a
    directory holding ``Lf1chSf`` and ``SingTermFreq.dat`` (the ``word_data``
    directory inside the ``pyab3p`` wheel, or a fetch of the same pinned
    commit). Fetch-only, benchmark use, never vendored.

Every MED1250 number here is a **tuning-split** number: ``bench/splits.toml``
records the corpus as contaminated and there is still no held-out pair corpus.

Usage::

    python bench/run_shortform.py --ceiling --variants --save
    python bench/run_shortform.py --attribute --interpreter C:/akbench/Scripts/python.exe
    python bench/run_shortform.py --gates C:/akbench/Lib/site-packages/word_data
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Callable, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

import acronymkit.extractor as extractor_module  # noqa: E402
from acronymkit._pseudo_precision import (  # noqa: E402
    estimate_precisions,
    harvest_candidates,
    short_form_group,
)
from acronymkit._strategies import STRATEGIES, match, split_long_form  # noqa: E402
from acronymkit.config import Config  # noqa: E402
from acronymkit.extractor import (  # noqa: E402
    AbbreviationExtractor,
    find_best_long_form,
    is_valid_long_form,
    is_valid_short_form,
)
from bench import corpora, scoring  # noqa: E402
from bench.run_cascade import split_corpus  # noqa: E402
from bench.run_extraction import (  # noqa: E402
    dedupe_per_document,
    predict_acronymkit,
    predict_external,
    save_results,
)

#: Bracket regex used only by the ceiling measurement, where it must match the
#: one ``bench/run_rerank.py`` and ``bench/run_oracle.py`` use so the numbers
#: are comparable to theirs. The attribution measurement deliberately uses the
#: extractor's own balanced-region scanner instead.
_PAREN = re.compile(r"\(([^()]{1,30})\)")

#: Window width in words, matching run_oracle.py and run_rerank.py exactly.
_WINDOW = 14

#: Extraction profiles, spelled out rather than imported, so this runner records
#: the settings it measured rather than whatever the enum means later.
_PROFILES: dict[str, dict[str, object]] = {
    "high_precision": {
        "extraction_min_short_form_length": 2,
        "extraction_max_short_form_length": 10,
        "extraction_require_uppercase": True,
    },
    "general": {
        "extraction_min_short_form_length": 2,
        "extraction_max_short_form_length": 14,
        "extraction_require_uppercase": True,
    },
    "biomedical": {
        "extraction_min_short_form_length": 1,
        "extraction_max_short_form_length": 14,
        "extraction_require_uppercase": False,
    },
}

_OPENERS = {"(": ")", "[": "]", "{": "}"}
_CLOSERS = {closer: opener for opener, closer in _OPENERS.items()}


# ---------------------------------------------------------------------------
# the two candidate short-form-span fixes, as patches rather than edits
# ---------------------------------------------------------------------------
_ORIGINAL_TRIM = extractor_module._trim_span
_ORIGINAL_PAIR_FOR_REGION = AbbreviationExtractor._pair_for_region


def _unmatched_openers(text: str) -> list[str]:
    """Opening brackets in ``text`` that nothing closes."""
    stack: list[str] = []
    for character in text:
        if character in _OPENERS:
            stack.append(character)
        elif character in _CLOSERS and stack and _OPENERS[stack[-1]] == character:
            stack.pop()
    return stack


def trim_span_balanced(
    text: str, start: int, end: int, *, limit: int = extractor_module._MAX_TRIM
) -> tuple[int, int]:
    """``_trim_span`` that refuses to leave a bracket open.

    ``_trim_span`` strips trailing non-alphanumerics unconditionally, so the
    bracketed region ``FEV(1)`` yields the short form ``FEV(1`` -- an unmatched
    opener that can never equal any annotation. The right edge is put back
    exactly far enough to close what the trim opened.
    """
    trimmed_start, trimmed_end = _ORIGINAL_TRIM(text, start, end, limit=limit)
    stack = _unmatched_openers(text[trimmed_start:trimmed_end])
    if not stack:
        return trimmed_start, trimmed_end
    cursor = trimmed_end
    while stack and cursor < end and text[cursor] in _CLOSERS:
        if _OPENERS[stack[-1]] != text[cursor]:
            break
        stack.pop()
        cursor += 1
    return (trimmed_start, cursor) if not stack else (trimmed_start, trimmed_end)


def pair_for_region_two_word(
    self: AbbreviationExtractor, text: str, open_index: int, close_index: int
):
    """``_pair_for_region`` that also offers the whole two-word bracketed text.

    ``is_valid_short_form`` admits up to two words, but ``_short_form_in`` takes
    the first word whenever it alone is admissible, so ``MEF cells``,
    ``TNF alpha``, ``PAR 2`` and ``MV CBCT`` are never candidates. The two-word
    reading is preferred when it aligns, which on MED1250 raises precision as
    well as recall -- a two-word short form that aligns is evidence the
    first-word reading was the wrong parse.
    """
    first = _ORIGINAL_PAIR_FOR_REGION(self, text, open_index, close_index)
    content_start, content_end = open_index + 1, close_index
    if content_start >= content_end:
        return first
    start, end = extractor_module._trim_span(text, content_start, content_end)
    if start >= end:
        return first
    candidate = text[start:end]
    config = self.config
    if len(candidate.split()) != 2:
        return first
    if len(candidate) > config.extraction_max_short_form_length:
        return first
    if not is_valid_short_form(
        candidate,
        min_length=config.extraction_min_short_form_length,
        max_length=config.extraction_max_short_form_length,
        require_uppercase=config.extraction_require_uppercase,
    ):
        return first
    window = self._long_form_window(text, open_index, len(candidate))
    if window is None:
        return first
    pair = self._build_pair(text, candidate, (start, end), window, "long(short)")
    return pair if pair is not None else first


def _install(*, balanced_trim: bool, two_word: bool) -> None:
    """Patch the two candidate fixes in or out, in place."""
    extractor_module._trim_span = trim_span_balanced if balanced_trim else _ORIGINAL_TRIM
    AbbreviationExtractor._pair_for_region = (
        pair_for_region_two_word if two_word else _ORIGINAL_PAIR_FOR_REGION
    )


# ---------------------------------------------------------------------------
# 1. attribution
# ---------------------------------------------------------------------------
#: Causes, most specific first. A miss is attributed to the first that applies.
_CAUSES = (
    "selection: right short form, wrong long-form span",
    "matching: short form offered, no valid long form",
    "admission: short form lost to unbalanced bracket trimming",
    "admission: short form lost to the first-word rule",
    "admission: short form never offered at all",
)


def _slug(text: str) -> str:
    """A results.json-safe key fragment."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _offered_short_forms(
    extractor: AbbreviationExtractor, text: str, trim: Callable
) -> tuple[set[str], set[str]]:
    """What ``_short_form_in`` offers under ``trim``, and the two-word reading.

    Args:
        extractor: A configured extractor, read for its gates only.
        text: The document.
        trim: The ``_trim_span`` implementation to install for the scan.

    Returns:
        ``(offered, whole_region)`` -- case-folded short forms the extractor
        actually proposes, and the admissible whole trimmed bracketed texts the
        first-word rule suppresses.
    """
    previous = extractor_module._trim_span
    extractor_module._trim_span = trim
    try:
        offered: set[str] = set()
        whole: set[str] = set()
        config = extractor.config
        for open_index, close_index in extractor_module._bracket_regions(text):
            if open_index + 1 >= close_index:
                continue
            found = extractor._short_form_in(text, open_index + 1, close_index)
            if found:
                offered.add(scoring.normalise_exact(found[0]))
            preceding = extractor._preceding_token(text, open_index)
            if preceding:
                offered.add(scoring.normalise_exact(preceding[0]))
            start, end = trim(text, open_index + 1, close_index)
            candidate = text[start:end]
            if (
                start < end
                and len(candidate) <= config.extraction_max_short_form_length
                and is_valid_short_form(
                    candidate,
                    min_length=config.extraction_min_short_form_length,
                    max_length=config.extraction_max_short_form_length,
                    require_uppercase=config.extraction_require_uppercase,
                )
            ):
                whole.add(scoring.normalise_exact(candidate))
    finally:
        extractor_module._trim_span = previous
    return offered, whole


def attribute(documents: Sequence, interpreter: str) -> dict:
    """Attribute every miss to one cause, and count pyab3p's recoveries."""
    _install(balanced_trim=False, two_word=False)
    ours = dedupe_per_document(predict_acronymkit(documents))
    rival, _, _ = predict_external("pyab3p", documents, interpreter, "med1250", None)
    rival = dedupe_per_document(rival)
    extractor = AbbreviationExtractor(Config())

    def keys(pairs):
        return {(scoring.normalise_exact(s), scoring.normalise_relaxed(lf)) for s, lf in pairs}

    counts: Counter = Counter()
    recovered: Counter = Counter()
    for document in documents:
        gold = {
            (scoring.normalise_exact(p.short_form), scoring.normalise_relaxed(p.long_form))
            for p in document.pairs
        }
        mine = keys(ours.get(document.uid, []))
        theirs = keys(rival.get(document.uid, []))
        my_short_forms = {key[0] for key in mine}
        offered, _ = _offered_short_forms(extractor, document.text, _ORIGINAL_TRIM)
        balanced_offered, balanced_whole = _offered_short_forms(
            extractor, document.text, trim_span_balanced
        )
        for pair in gold - mine:
            short_form = pair[0]
            if short_form in my_short_forms:
                cause = _CAUSES[0]
            elif short_form in offered:
                cause = _CAUSES[1]
            elif short_form in balanced_offered:
                cause = _CAUSES[2]
            elif short_form in balanced_whole:
                cause = _CAUSES[3]
            else:
                cause = _CAUSES[4]
            counts[cause] += 1
            if pair in theirs:
                recovered[cause] += 1

    total = sum(counts.values())
    print(f"acronymkit misses on MED1250 : {total}")
    print(f"of which pyab3p recovers     : {sum(recovered.values())}\n")
    print(f"{'cause':<58} {'n':>5} {'share':>7} {'pyab3p':>7}")
    print("-" * 80)
    for cause in _CAUSES:
        print(
            f"{cause:<58} {counts[cause]:>5} {counts[cause] / total * 100:>6.1f}% "
            f"{recovered[cause]:>7}"
        )
    return {
        "corpus": "med1250",
        "split": "all (tuning)",
        "total_misses": total,
        "pyab3p_recovers": sum(recovered.values()),
        **{"n_" + _slug(cause): counts[cause] for cause in _CAUSES},
        **{"pyab3p_" + _slug(cause): recovered[cause] for cause in _CAUSES},
    }


# ---------------------------------------------------------------------------
# 2. selection ceiling
# ---------------------------------------------------------------------------
def _score_span(short_form: str, words: Sequence[str], table) -> float:
    """Reliability of the best strategy that explains *this span*.

    ``bench/run_rerank.py`` calls ``best_match``, which rescans every start
    inside the suffix it is handed, so its score is non-decreasing in span
    length and is always maximised by the full window. ``match(..., start=0)``
    requires the alignment to cover the span.
    """
    group = short_form_group(short_form)
    best = 0.0
    for strategy in STRATEGIES:
        precision = table.precision(group, strategy.name)
        if precision <= best:
            continue
        if match(short_form, words, strategy, 0) is not None:
            best = precision
    return best


_CEILING_KEYS = (
    "brackets with a gold pair",
    "greedy correct",
    "greedy wrong",
    "wrong, gold not a start boundary",
    "wrong, gold reachable",
    "wrong, gold explained by no strategy",
    "wrong, gold uniquely top-scoring",
    "wrong, gold tied with the top",
    "wrong, gold below the top",
)


def _oracle_substitution(documents: Sequence, fixes: dict) -> tuple[float, float, float]:
    """Score the greedy predictions with every addressable span replaced by gold.

    This is what a *perfect* per-candidate selector would score over the space a
    re-ranker can actually select from, and it is therefore the ceiling on the
    whole per-candidate-evidence line of attack -- measured, not assumed.
    """
    predictions = {
        uid: list(pairs)
        for uid, pairs in dedupe_per_document(predict_acronymkit(documents)).items()
    }
    for uid, items in fixes.items():
        kept = [
            (short, long_form)
            for short, long_form in predictions.get(uid, [])
            if not any(
                scoring.normalise_exact(short) == scoring.normalise_exact(short_form)
                and greedy is not None
                and scoring.normalise_relaxed(long_form) == scoring.normalise_relaxed(greedy)
                for short_form, greedy, _ in items
            )
        ]
        kept.extend((short_form, gold_span) for short_form, _, gold_span in items)
        predictions[uid] = kept
    score = scoring.evaluate(
        documents,
        dedupe_per_document(predictions),
        corpus="med1250",
        system="oracle_per_candidate",
    ).scores["exact"]
    return score.precision * 100, score.recall * 100, score.f1 * 100


def ceiling(documents: Sequence, table) -> dict:
    """The tie statistic, conditioned on the brackets the greedy rule gets wrong."""
    counts: Counter = Counter()
    fixes: dict = {}
    for document in documents:
        text = document.text
        gold: dict[str, set[str]] = {}
        for pair in document.pairs:
            gold.setdefault(scoring.normalise_exact(pair.short_form), set()).add(
                scoring.normalise_relaxed(pair.long_form)
            )
        for bracket in _PAREN.finditer(text):
            short_form = bracket.group(1).strip()
            if not is_valid_short_form(short_form, min_length=2, max_length=10):
                continue
            short_key = scoring.normalise_exact(short_form)
            if short_key not in gold:
                continue
            window = text[: bracket.start()]
            words = split_long_form(window)[-_WINDOW:]
            if not words:
                continue
            folded = [word.casefold() for word, _, _ in words]
            spans: list[str] = []
            scores: list[float] = []
            for index in reversed(range(len(words))):
                span = text[words[index][1] : bracket.start()].strip().rstrip(",;:( ").strip()
                if not span:
                    continue
                spans.append(span)
                scores.append(_score_span(short_form.casefold(), folded[index:], table))
            if not spans:
                continue
            counts["brackets with a gold pair"] += 1
            greedy = find_best_long_form(short_form, window)
            if greedy is not None and not is_valid_long_form(short_form, greedy):
                greedy = None
            if greedy is not None and scoring.normalise_relaxed(greedy) in gold[short_key]:
                counts["greedy correct"] += 1
                continue
            counts["greedy wrong"] += 1
            reachable = [
                index
                for index, span in enumerate(spans)
                if scoring.normalise_relaxed(span) in gold[short_key]
            ]
            if not reachable:
                counts["wrong, gold not a start boundary"] += 1
                continue
            counts["wrong, gold reachable"] += 1
            top = max(scores)
            value = scores[reachable[0]]
            at_top = sum(1 for candidate in scores if abs(candidate - top) < 1e-12)
            if value <= 0.0:
                counts["wrong, gold explained by no strategy"] += 1
            elif abs(value - top) < 1e-12 and at_top == 1:
                counts["wrong, gold uniquely top-scoring"] += 1
            elif abs(value - top) < 1e-12:
                counts["wrong, gold tied with the top"] += 1
            else:
                counts["wrong, gold below the top"] += 1
            if value > 0.0:
                fixes.setdefault(document.uid, []).append((short_form, greedy, spans[reachable[0]]))

    wrong = counts["greedy wrong"]
    addressable = (
        counts["wrong, gold uniquely top-scoring"]
        + counts["wrong, gold tied with the top"]
        + counts["wrong, gold below the top"]
    )
    gold_pairs = sum(len(document.pairs) for document in documents)
    print(f"\n{'quantity':<40} {'n':>6} {'share of wrong':>16}")
    print("-" * 64)
    for key in _CEILING_KEYS:
        # The share is of the brackets the greedy rule gets wrong, so it is
        # meaningless for the three totals above that line.
        share = f"{counts[key] / wrong * 100:14.1f}%" if wrong and key.startswith("wrong") else ""
        print(f"{key:<40} {counts[key]:>6} {share:>16}")
    print(
        f"\naddressable by ANY per-candidate score : {addressable} pairs "
        f"({addressable / gold_pairs * 100:.2f} recall points of {gold_pairs} gold)"
    )
    print(f"already unique under the per-rule score: {counts['wrong, gold uniquely top-scoring']}")
    precision, recall, f1 = _oracle_substitution(documents, fixes)
    print(
        f"perfect per-candidate selector over that space: P {precision:.2f} "
        f"R {recall:.2f} F1 {f1:.2f}"
    )
    return {
        "corpus": "med1250",
        "split": "all (tuning)",
        "gold_pairs": gold_pairs,
        **{_slug(key): counts[key] for key in _CEILING_KEYS},
        "addressable_by_per_candidate_score": addressable,
        "addressable_recall_points": round(addressable / gold_pairs * 100, 2),
        "already_unique_under_per_rule_score": counts["wrong, gold uniquely top-scoring"],
        "oracle_selector_exact_precision": round(precision, 2),
        "oracle_selector_exact_recall": round(recall, 2),
        "oracle_selector_exact_f1": round(f1, 2),
    }


# ---------------------------------------------------------------------------
# 3. variants
# ---------------------------------------------------------------------------
_VARIANTS = (
    ("baseline", False, False),
    ("balanced_trim", True, False),
    ("two_word", False, True),
    ("both", True, True),
)


def variants(documents: Sequence) -> dict:
    """Score the two short-form-span fixes across profiles and splits."""
    dev, test = split_corpus(documents)
    splits = (("dev", dev), ("test", test), ("all", documents))
    recorded: dict = {}
    print(f"\n{'profile':<16} {'variant':<14} {'split':<5} {'P %':>7} {'R %':>7} {'F1 %':>7}")
    print("-" * 62)
    for profile, settings in _PROFILES.items():
        for name, balanced, two_word in _VARIANTS:
            _install(balanced_trim=balanced, two_word=two_word)
            for split_name, subset in splits:
                evaluation = scoring.evaluate(
                    subset,
                    dedupe_per_document(predict_acronymkit(subset, **settings)),
                    corpus="med1250",
                    system=f"{profile}/{name}",
                )
                score = evaluation.scores["exact"]
                print(
                    f"{profile:<16} {name:<14} {split_name:<5} {score.precision * 100:7.2f} "
                    f"{score.recall * 100:7.2f} {score.f1 * 100:7.2f}"
                )
                recorded[f"shortform.med1250_{split_name}.{profile}.{name}"] = {
                    "corpus": "med1250",
                    "split": f"{split_name} (tuning)",
                    "split_seed": 20260809,
                    "profile": profile,
                    "variant": name,
                    "balanced_trim": balanced,
                    "two_word_short_form": two_word,
                    "exact_precision": round(score.precision * 100, 2),
                    "exact_recall": round(score.recall * 100, 2),
                    "exact_f1": round(score.f1 * 100, 2),
                    "exact_true_positives": score.true_positives,
                    "exact_false_positives": score.false_positives,
                    "exact_false_negatives": score.false_negatives,
                }
    _install(balanced_trim=False, two_word=False)
    return recorded


# ---------------------------------------------------------------------------
# 4. admission gates
# ---------------------------------------------------------------------------
def frequency_separation(documents: Sequence, counts: dict[str, int]) -> dict:
    """Can a unigram frequency signal decide "extend the span left" at all?

    Both the greedy span and the gold span end at the bracket, so the only thing
    in dispute is the leading words. Any score that is a function of word
    frequencies therefore decides "extend" or "stop", and the decision turns on
    the word immediately to the left. This sweeps every threshold on that word's
    frequency and reports the best net move -- one true extension gained minus
    one correct answer destroyed.
    """
    extend: list[int] = []
    hold: list[int] = []
    for document in documents:
        text = document.text
        gold: dict[str, set[str]] = {}
        for pair in document.pairs:
            gold.setdefault(scoring.normalise_exact(pair.short_form), set()).add(
                scoring.normalise_relaxed(pair.long_form)
            )
        for bracket in _PAREN.finditer(text):
            short_form = bracket.group(1).strip()
            if not is_valid_short_form(short_form, min_length=2, max_length=10):
                continue
            short_key = scoring.normalise_exact(short_form)
            if short_key not in gold:
                continue
            window = text[: bracket.start()]
            words = split_long_form(window)[-_WINDOW:]
            if not words:
                continue
            greedy = find_best_long_form(short_form, window)
            if greedy is None or not is_valid_long_form(short_form, greedy):
                continue
            greedy_key = scoring.normalise_relaxed(greedy)
            indexed = []
            for index in reversed(range(len(words))):
                span = text[words[index][1] : bracket.start()].strip().rstrip(",;:( ").strip()
                if span:
                    indexed.append((index, span))
            greedy_index = next(
                (i for i, span in indexed if scoring.normalise_relaxed(span) == greedy_key), None
            )
            if greedy_index is None:
                continue
            left = [i for i, _ in indexed if i < greedy_index]
            if not left:
                continue
            frequency = counts.get(words[max(left)][0].casefold(), 0)
            gold_index = next(
                (i for i, span in indexed if scoring.normalise_relaxed(span) in gold[short_key]),
                None,
            )
            if greedy_key in gold[short_key]:
                hold.append(frequency)
            elif gold_index is not None and gold_index < greedy_index:
                extend.append(frequency)

    best: dict[str, tuple[int, object]] = {
        "higher_extends": (0, None),
        "lower_extends": (0, None),
    }
    for threshold in sorted(set(extend) | set(hold)):
        for label in ("higher_extends", "lower_extends"):
            above = label == "higher_extends"
            gained = sum(1 for value in extend if (value >= threshold) == above)
            destroyed = sum(1 for value in hold if (value >= threshold) == above)
            if gained - destroyed > best[label][0]:
                best[label] = (gained - destroyed, (threshold, gained, destroyed))
    print(
        f"\nunigram frequency separation: {len(extend)} brackets must extend, {len(hold)} must not"
    )
    for label, (net, detail) in best.items():
        print(f"   best threshold, {label:<15}: net {net:+d}  {detail}")
    return {
        "corpus": "med1250",
        "split": "all (tuning)",
        "source": "Ab3P SingTermFreq.dat (unigram; no multi-word keys)",
        "must_extend": len(extend),
        "must_not_extend": len(hold),
        "best_net_gain_higher_extends": best["higher_extends"][0],
        "best_net_gain_lower_extends": best["lower_extends"][0],
    }


def _load_word_data(directory: Path) -> tuple[set[str], set[str], dict[str, int]]:
    """Ab3P's one-character vocabulary, and what SingTermFreq.dat compiles to.

    ``make_wordCountHash.C`` keeps rows with ``len >= 3`` and ``freq >= 100``,
    and the only consumer -- ``AbbrStra::is_subword`` -- tests
    ``wrdset.count(word) == 0``. The 31 MB of counts is therefore a vocabulary
    at the point of use, and this reproduces that reduction exactly.
    """
    with open(directory / "Lf1chSf", encoding="utf-8") as handle:
        lf1chsf = {line.strip() for line in handle if line.strip()}
    vocabulary: set[str] = set()
    counts: dict[str, int] = {}
    with open(directory / "SingTermFreq.dat", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            separator = line.rfind("|")
            if separator < 0:
                continue
            word = line[:separator]
            try:
                count = int(line[separator + 1 :])
            except ValueError:
                continue
            counts[word] = count
            if len(word) >= 3 and count >= 100:
                vocabulary.add(word)
    return lf1chsf, vocabulary, counts


def _shape(short_form: str) -> str:
    """Which admission gate a short form needs, if any."""
    short_form = short_form.strip()
    if len(short_form) == 1:
        return "one_character"
    if not any(character.isupper() for character in short_form):
        return "no_uppercase"
    if len(short_form) > 10:
        return "over_ten_characters"
    return "default_gate"


def gates(documents: Sequence, directory: Path) -> dict:
    """Precision by short-form shape once the gates open, and what a vocabulary buys."""
    lf1chsf, vocabulary, counts = _load_word_data(directory)
    print(
        f"\nLf1chSf: {len(lf1chsf)} words; SingTermFreq.dat holds {len(counts)} unigram rows "
        f"and reduces to {len(vocabulary)} words at length>=3, freq>=100"
    )
    _install(balanced_trim=True, two_word=True)
    predictions = dedupe_per_document(predict_acronymkit(documents, **_PROFILES["biomedical"]))
    _install(balanced_trim=False, two_word=False)

    rows = []
    for document in documents:
        gold = {
            (scoring.normalise_exact(p.short_form), scoring.normalise_relaxed(p.long_form))
            for p in document.pairs
        }
        for short_form, long_form in predictions.get(document.uid, []):
            words = [w for w in long_form.replace("-", " ").replace("/", " ").split() if w]
            head = words[-1].strip(".,;:()[]").casefold() if words else ""
            rows.append(
                {
                    "shape": _shape(short_form),
                    "correct": (
                        scoring.normalise_exact(short_form),
                        scoring.normalise_relaxed(long_form),
                    )
                    in gold,
                    "head_in_lf1chsf": head in lf1chsf,
                    "content_in_vocabulary": all(
                        word.strip(".,;:()[]").casefold() in vocabulary
                        for word in words
                        if len(word.strip(".,;:()[]")) >= 3
                    ),
                }
            )

    recorded: dict = {}
    print(f"\n{'short-form shape':<22} {'TP':>5} {'FP':>5} {'precision %':>12}")
    print("-" * 48)
    for name in ("default_gate", "one_character", "no_uppercase", "over_ten_characters"):
        subset = [row for row in rows if row["shape"] == name]
        if not subset:
            continue
        true_positives = sum(1 for row in subset if row["correct"])
        false_positives = len(subset) - true_positives
        print(
            f"{name:<22} {true_positives:>5} {false_positives:>5} "
            f"{true_positives / len(subset) * 100:11.1f}%"
        )
        entry = {
            "corpus": "med1250",
            "split": "all (tuning)",
            "profile": "biomedical",
            "with_short_form_span_fixes": True,
            "shape": name,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "precision": round(true_positives / len(subset) * 100, 2),
        }
        for gate, field in (
            ("lf1chsf_head", "head_in_lf1chsf"),
            ("singtermfreq_content", "content_in_vocabulary"),
        ):
            kept = [row for row in subset if row[field]]
            kept_true = sum(1 for row in kept if row["correct"])
            entry[f"gate_{gate}_true_positives"] = kept_true
            entry[f"gate_{gate}_false_positives"] = len(kept) - kept_true
            entry[f"gate_{gate}_precision"] = round(kept_true / len(kept) * 100, 2) if kept else 0.0
            print(
                f"    gate {gate:<22} keeps {kept_true:>4}/{true_positives:<4} TP and "
                f"{len(kept) - kept_true:>4}/{false_positives:<4} FP -> "
                f"{entry[f'gate_{gate}_precision']:.1f}%"
            )
        recorded[f"admission.med1250.{name}"] = entry
    recorded["analysis.med1250.unigram_frequency_separation"] = frequency_separation(
        documents, counts
    )
    return recorded


# ---------------------------------------------------------------------------
# 5. rejected relaxation: optional digits
# ---------------------------------------------------------------------------
def relaxations(documents: Sequence) -> dict:
    """Treat a digit in the short form as optional when nothing else aligns.

    Schwartz & Hearst require every alphanumeric short-form character to align,
    and MED1250 annotates definitions where a digit has no counterpart at all
    (``N2O`` -> "nitrous oxide", ``2D`` -> "two-dimensional"), so the digit alone
    blocks the match. Recorded because it loses: the relaxation is a strict
    fallback and cannot break a correct pair, yet the pairs it newly admits are
    wrong often enough to cost more precision than the recall is worth.
    """
    original = extractor_module.find_best_long_form

    def make(mode: str):
        def relaxed(short_form: str, window: str):
            found = original(short_form, window)
            if found is not None:
                return found
            if mode == "drop_all_digits":
                stripped = "".join(c for c in short_form if not c.isdigit())
            else:
                stripped = re.sub(r"\d+$", "", short_form)
            if stripped == short_form or not any(c.isalnum() for c in stripped):
                return None
            return original(stripped, window)

        return relaxed

    dev, test = split_corpus(documents)
    recorded: dict = {}
    print(f"\n{'relaxation':<22} {'split':<5} {'P %':>7} {'R %':>7} {'F1 %':>7}")
    print("-" * 52)
    try:
        for name in ("baseline", "drop_trailing_digits", "drop_all_digits"):
            extractor_module.find_best_long_form = original if name == "baseline" else make(name)
            for split_name, subset in (("dev", dev), ("test", test), ("all", documents)):
                evaluation = scoring.evaluate(
                    subset,
                    dedupe_per_document(predict_acronymkit(subset)),
                    corpus="med1250",
                    system=name,
                )
                score = evaluation.scores["exact"]
                print(
                    f"{name:<22} {split_name:<5} {score.precision * 100:7.2f} "
                    f"{score.recall * 100:7.2f} {score.f1 * 100:7.2f}"
                )
                recorded[f"relaxation.med1250_{split_name}.{name}"] = {
                    "corpus": "med1250",
                    "split": f"{split_name} (tuning)",
                    "split_seed": 20260809,
                    "rule": name,
                    "shipped": False,
                    "exact_precision": round(score.precision * 100, 2),
                    "exact_recall": round(score.recall * 100, 2),
                    "exact_f1": round(score.f1 * 100, 2),
                }
    finally:
        extractor_module.find_best_long_form = original
    return recorded


# ---------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--attribute", action="store_true")
    parser.add_argument("--ceiling", action="store_true")
    parser.add_argument("--variants", action="store_true")
    parser.add_argument("--relaxations", action="store_true")
    parser.add_argument("--gates", type=Path, help="directory holding Lf1chSf and SingTermFreq.dat")
    parser.add_argument(
        "--interpreter",
        default=sys.executable,
        help="Python that has pyab3p installed; needed by --attribute",
    )
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    if not (args.attribute or args.ceiling or args.variants or args.relaxations or args.gates):
        parser.error(
            "choose at least one of --attribute, --ceiling, --variants, --relaxations, --gates"
        )

    documents = corpora.load("med1250")
    recorded: dict = {}

    if args.attribute:
        recorded["analysis.med1250.miss_attribution"] = attribute(documents, args.interpreter)
    if args.ceiling:
        dev, _ = split_corpus(documents)
        table = estimate_precisions(
            harvest_candidates(document.text for document in dev), chance_trials=3
        )
        recorded["analysis.med1250.selection_ceiling"] = ceiling(documents, table)
    if args.variants:
        recorded.update(variants(documents))
    if args.relaxations:
        recorded.update(relaxations(documents))
    if args.gates:
        recorded.update(gates(documents, args.gates))

    if args.save:
        path = save_results(recorded)
        print(f"\nsaved {len(recorded)} run(s) to {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
