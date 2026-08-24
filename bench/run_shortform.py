#!/usr/bin/env python3
"""Where the extraction gap to ``pyab3p`` actually lives, and what closes it.

Seven experiments have tried to close the 5-point MED1250 gap by changing how a
*long form* is chosen. This runner measures the other half of the problem --
which *short form* is admitted in the first place -- and re-derives the
selection-ceiling statistic that D-012 used to close the long-form line of
attack.

Six measurements, each independently selectable:

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
    Three candidate fixes, measured alone (and the first two also together), on
    the frozen dev/test halves and on the whole corpus, across all three
    extraction profiles. Two are short-form-span bugs rather than knobs:
    ``_trim_span`` strips a balanced closing bracket off ``FEV(1)``, and
    ``_short_form_in`` never offers a two-word short form when the first word
    alone is admissible. The third is a long-form admission rule: reject a long
    form whose first word is a function word, because
    ``find_best_long_form`` returns a suffix starting at the word that supplied
    the short form's first character, so ``OMB -> of Management and Budget`` is
    a parse in which the ``O`` came from ``of``.

    ``both`` stays in the table on purpose. The two span fixes were first
    measured together, they look like one change, and R6 exists because they are
    not: one is free everywhere and one is a trade.

    A fifth row, ``legend``, is the library's own default-off
    ``legend_syntax`` flag: the ``SF = LF`` abbreviation legend, which no
    bracket introduces. Its comparator is ``balanced_trim`` rather than
    ``baseline``, because ``balanced_trim`` is what ships; every row records
    the comparator it must be read against.

``--spans``
    The same variants on the two corpora that annotate spans without pairing
    them -- PLOD-CW (dev and test) and SDU@AAAI-22 AE (legal and scientific
    dev) -- scored the way each corpus's own task is scored, short forms and
    long forms separately, with no derived pairing anywhere. MED1250 is a
    declared tuning split, so it cannot answer whether a fix generalises; this
    can, for PLOD.

    Every table prints the corpus's structure above its scores, because a
    neutral result only means something on a corpus capable of showing the
    phenomenon (R9.5) and a recall figure only means something beside its
    ceiling (R9.6). SDU-22 AE dev is registered ``tuning`` and contaminated --
    see ``bench/splits.toml`` -- so its rows are tuning rows.

``--legend``
    How far every ``=`` in a corpus gets through the legend gates, gate by
    gate, on MED1250 and on both SDU@AAAI-22 AE dev splits -- plus how many of
    each corpus's gold long forms begin immediately after a separator, which is
    whether the corpus can show the class at all. Read this before the
    ``legend`` row of ``--variants``: a null result on a corpus where the rule
    never fires is a fact about the corpus.

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
    python bench/run_shortform.py --variants --spans --save
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
from acronymkit._strategies import (  # noqa: E402
    SKIPPABLE,
    STRATEGIES,
    match,
    split_long_form,
)
from acronymkit.config import Config  # noqa: E402
from acronymkit.extractor import (  # noqa: E402
    AbbreviationExtractor,
    find_best_long_form,
    is_valid_long_form,
    is_valid_short_form,
)
from bench import corpora, run_spans, scoring  # noqa: E402
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
# the candidate fixes, as patches rather than edits
# ---------------------------------------------------------------------------
# THE "OFF" SIDE OF EACH SWITCH IS SPELLED OUT HERE RATHER THAN CAPTURED FROM
# THE LIBRARY, for the same reason ``_PROFILES`` above is: a variant table is a
# statement about a *delta*, and a delta measured against "whatever the library
# does today" stops being reproducible the moment one of these ships. Capture
# the installed implementation and the day ``balanced_trim`` lands in
# ``extractor.py`` this runner starts reporting ``baseline == balanced_trim ==
# 0.00`` difference and calls it a null result. So the pre-fix behaviour is
# frozen in this file and the runner installs one side or the other explicitly.
#
# ``_ORIGINAL_*`` is still captured, but only to restore the process to the
# shipped extractor when the runner is done with it.
_ORIGINAL_TRIM = extractor_module._trim_span
_ORIGINAL_PAIR_FOR_REGION = AbbreviationExtractor._pair_for_region
_ORIGINAL_IS_VALID_LONG_FORM = extractor_module.is_valid_long_form

# ``legend`` is the one switch whose two sides are NOT transcribed here, and the
# exception is principled rather than convenient. The three fixes above were
# candidate edits: each had an "off" side that existed only until it shipped,
# which is why freezing it in this file is what keeps the delta reproducible.
# ``legend_syntax`` is a permanent, public, default-off constructor argument --
# both sides of the switch are shipped code and stay shipped, so driving the
# real flag is what makes this row describe the library rather than a sketch of
# it. What is patched is only the *default*, so that the engines built deep
# inside ``predict_acronymkit`` and ``_engine_pairs`` pick it up.
_ORIGINAL_EXTRACTOR_INIT = AbbreviationExtractor.__init__


def _extractor_init_legend_on(
    self: AbbreviationExtractor, config, tokenizer=None, *, legend_syntax: bool = False
) -> None:
    """``AbbreviationExtractor.__init__`` with ``legend_syntax`` defaulted on."""
    _ORIGINAL_EXTRACTOR_INIT(self, config, tokenizer, legend_syntax=True)


def trim_span_unbalanced(
    text: str, start: int, end: int, *, limit: int = extractor_module._MAX_TRIM
) -> tuple[int, int]:
    """``_trim_span`` as it stood before the balanced-bracket fix.

    Transcribed rather than imported. This is the "off" side of the
    ``balanced_trim`` switch and it must keep meaning what it meant when the
    variant table was recorded, whatever ``acronymkit.extractor`` does later.
    """
    budget = limit
    while start < end and budget > 0 and not text[start].isalnum():
        start += 1
        budget -= 1
    budget = limit
    while end > start and budget > 0 and not text[end - 1].isalnum():
        end -= 1
        budget -= 1
    return start, end


#: How far back from the right edge the balance scan looks. Matches
#: ``acronymkit.extractor._MAX_BALANCE_SCAN``; spelled out here for the same
#: reason the pre-fix trim is.
_MAX_BALANCE_SCAN = 32


def _orphaned_openers(text: str, start: int, end: int) -> list[str]:
    """Opening brackets near the right edge of ``[start, end)`` that nothing closes.

    Right-to-left, bounded. An unbounded scan over the kept span would make
    ``_trim_span`` cost time proportional to the bracketed region it is handed,
    which on a whole-paragraph parenthetical is exactly the quadratic behaviour
    ``_MAX_TRIM`` exists to prevent.
    """
    pending: list[str] = []
    orphans: list[str] = []
    cursor = end
    budget = _MAX_BALANCE_SCAN
    while cursor > start and budget > 0:
        cursor -= 1
        budget -= 1
        character = text[cursor]
        if character in _CLOSERS:
            pending.append(character)
        elif character in _OPENERS:
            if pending and _OPENERS[character] == pending[-1]:
                pending.pop()
            else:
                orphans.append(character)
    return orphans


def trim_span_balanced(
    text: str, start: int, end: int, *, limit: int = extractor_module._MAX_TRIM
) -> tuple[int, int]:
    """``_trim_span`` that refuses to leave a bracket open.

    ``_trim_span`` strips trailing non-alphanumerics unconditionally, so the
    bracketed region ``FEV(1)`` yields the short form ``FEV(1`` -- an unmatched
    opener that can never equal any annotation. The right edge is put back
    exactly far enough to close what the trim opened, all-or-nothing.

    This is the "on" side of the switch, and it is the algorithm that shipped
    rather than a looser sketch of it -- otherwise the recorded delta would
    describe code nobody runs.
    """
    trimmed_start, trimmed_end = trim_span_unbalanced(text, start, end, limit=limit)
    if trimmed_end >= end or text[trimmed_end] not in _CLOSERS:
        return trimmed_start, trimmed_end
    orphans = _orphaned_openers(text, trimmed_start, trimmed_end)
    if not orphans:
        return trimmed_start, trimmed_end
    cursor = trimmed_end
    for opener in orphans:
        if cursor >= end or text[cursor] != _OPENERS[opener]:
            return trimmed_start, trimmed_end
        cursor += 1
    return trimmed_start, cursor


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


def long_form_valid_permissive(short_form: str, long_form: str) -> bool:
    """``is_valid_long_form`` as it stood before the function-word rule.

    The "off" side of the ``function_word`` switch, transcribed for the same
    reason :func:`trim_span_unbalanced` is.
    """
    short = short_form.strip()
    expansion = long_form.strip()
    if not short or not expansion:
        return False
    if len(expansion) <= len(short):
        return False
    if extractor_module._alnum_count(expansion) < extractor_module._alnum_count(short):
        return False
    if len(extractor_module._split_words(expansion)) > len(short) + 5:
        return False
    return not extractor_module._contains_standalone(expansion, short)


def leads_with_function_word(long_form: str) -> bool:
    """Does ``long_form``'s first word belong to :data:`SKIPPABLE`?

    ``find_best_long_form`` returns a suffix beginning at the word that supplied
    the short form's *first* character, so a long form that starts with ``of``
    is a parse in which the ``O`` of ``OMB`` was taken from ``of``. The set is
    ``acronymkit._strategies.SKIPPABLE`` -- the project's own list of words a
    coiner omits -- rather than one invented here, because a rejection set
    chosen after seeing the corpus is a tuned parameter wearing a rule's
    clothes.
    """
    words = long_form.split()
    return bool(words) and words[0].strip(".,;:").lower() in SKIPPABLE


def long_form_valid_strict(short_form: str, long_form: str) -> bool:
    """``is_valid_long_form`` plus the leading-function-word rejection (W6)."""
    if not long_form_valid_permissive(short_form, long_form):
        return False
    return not leads_with_function_word(long_form)


def _install(
    *,
    balanced_trim: bool,
    two_word: bool,
    function_word: bool = False,
    legend: bool = False,
) -> None:
    """Patch the candidate fixes in or out, in place.

    Both sides of the first three switches are this module's own functions, so a
    cell of the variant table means the same thing before and after any of them
    ships. ``legend`` drives the library's own flag; see the note above
    :func:`_extractor_init_legend_on` for why that one is different.
    """
    extractor_module._trim_span = trim_span_balanced if balanced_trim else trim_span_unbalanced
    AbbreviationExtractor._pair_for_region = (
        pair_for_region_two_word if two_word else _ORIGINAL_PAIR_FOR_REGION
    )
    extractor_module.is_valid_long_form = (
        long_form_valid_strict if function_word else long_form_valid_permissive
    )
    AbbreviationExtractor.__init__ = (  # type: ignore[method-assign]
        _extractor_init_legend_on if legend else _ORIGINAL_EXTRACTOR_INIT
    )


def _restore() -> None:
    """Put the shipped extractor back, so nothing downstream inherits a patch."""
    extractor_module._trim_span = _ORIGINAL_TRIM
    AbbreviationExtractor._pair_for_region = _ORIGINAL_PAIR_FOR_REGION
    extractor_module.is_valid_long_form = _ORIGINAL_IS_VALID_LONG_FORM
    AbbreviationExtractor.__init__ = _ORIGINAL_EXTRACTOR_INIT  # type: ignore[method-assign]


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
#: ``(name, balanced_trim, two_word, function_word, legend)``. ``both`` is kept
#: because it is the R6 counterexample this table exists to make visible: the
#: two short-form-span fixes were first measured together, they look like one
#: change, and they are not -- one is free everywhere and one is a trade.
#:
#: **READ EACH ROW AGAINST ITS OWN COMPARATOR, WHICH IS RECORDED IN THE ENTRY.**
#: The first four rows are deltas against ``baseline``, which is the extractor
#: as it stood before D-032. ``legend`` is a delta against ``balanced_trim``,
#: because ``balanced_trim`` is what ships today and a shipping decision has to
#: be one change away from what ships -- reading it against ``baseline`` would
#: bundle it with a fix that landed a session ago, which is the exact error R6
#: exists to prevent and which this table was built to make visible.
_VARIANTS = (
    ("baseline", False, False, False, False),
    ("balanced_trim", True, False, False, False),
    ("two_word", False, True, False, False),
    ("both", True, True, False, False),
    ("function_word", False, False, True, False),
    ("legend", True, False, False, True),
)

#: Which row each variant must be read against.
_COMPARATOR = {
    "baseline": None,
    "balanced_trim": "baseline",
    "two_word": "baseline",
    "both": "baseline",
    "function_word": "baseline",
    "legend": "balanced_trim",
}


def variants(documents: Sequence) -> dict:
    """Score the candidate fixes across profiles and splits, on MED1250 pairs."""
    dev, test = split_corpus(documents)
    splits = (("dev", dev), ("test", test), ("all", documents))
    recorded: dict = {}
    print(f"\n{'profile':<16} {'variant':<14} {'split':<5} {'P %':>7} {'R %':>7} {'F1 %':>7}")
    print("-" * 62)
    for profile, settings in _PROFILES.items():
        for name, balanced, two_word, function_word, legend in _VARIANTS:
            _install(
                balanced_trim=balanced,
                two_word=two_word,
                function_word=function_word,
                legend=legend,
            )
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
                    "comparator": _COMPARATOR[name],
                    "balanced_trim": balanced,
                    "two_word_short_form": two_word,
                    "reject_leading_function_word": function_word,
                    "legend_syntax": legend,
                    "exact_precision": round(score.precision * 100, 2),
                    "exact_recall": round(score.recall * 100, 2),
                    "exact_f1": round(score.f1 * 100, 2),
                    "exact_true_positives": score.true_positives,
                    "exact_false_positives": score.false_positives,
                    "exact_false_negatives": score.false_negatives,
                }
    _restore()
    recorded["shortform.med1250_all.function_word_exposure"] = function_word_exposure(documents)
    return recorded


def function_word_exposure(documents: Sequence) -> dict:
    """What the leading-function-word rule removes on MED1250, and what it caps.

    Two counts, and the second is the point. The rule deletes predictions whose
    long form begins with a function word; it also makes a whole class of gold
    long form permanently unreachable, and that cost is invisible today only
    because the extractor reaches none of them. Counting the gold side here --
    and asserting it in ``tests/test_extractor.py`` -- is what turns a future
    recall improvement into a measured cost rather than a silent one.

    The rule does **not** recover the right answer. ``OHCHR -> of the United
    Nations High Commissioner for Human Rights`` is wrong because the span
    should start at ``Office``, which is to the *left* of ``of``; reaching it
    means choosing a different long-form starting boundary, which is exactly
    what D-008 built, measured and reverted.
    """
    _restore()
    predictions = dedupe_per_document(predict_acronymkit(documents))
    predicted = 0
    predicted_leading = 0
    predicted_leading_correct = 0
    for document in documents:
        gold = {
            (scoring.normalise_exact(pair.short_form), scoring.normalise_relaxed(pair.long_form))
            for pair in document.pairs
        }
        for short_form, long_form in predictions.get(document.uid, []):
            predicted += 1
            if not leads_with_function_word(long_form):
                continue
            predicted_leading += 1
            key = (scoring.normalise_exact(short_form), scoring.normalise_relaxed(long_form))
            predicted_leading_correct += key in gold
    gold_pairs = sum(len(document.pairs) for document in documents)
    gold_leading = sum(
        leads_with_function_word(pair.long_form)
        for document in documents
        for pair in document.pairs
    )
    print(
        f"\nMED1250 leading-function-word exposure: {predicted_leading} of {predicted} "
        f"predictions ({predicted_leading_correct} of them correct); "
        f"{gold_leading} of {gold_pairs} gold long forms are capped by the rule"
    )
    return {
        "corpus": "med1250",
        "split": "all (tuning)",
        "rule": "reject a long form whose first word is in _strategies.SKIPPABLE",
        "function_words": sorted(SKIPPABLE),
        "predicted_pairs": predicted,
        "predicted_leading_function_word": predicted_leading,
        "predicted_leading_function_word_correct": predicted_leading_correct,
        "gold_pairs": gold_pairs,
        "gold_leading_function_word": gold_leading,
    }


# ---------------------------------------------------------------------------
# 3a. is the corpus even capable of showing the legend class?
# ---------------------------------------------------------------------------
#: The gates ``AbbreviationExtractor._legend_pair_at`` applies, in order.
_LEGEND_GATES = (
    "separators",
    "not an operator",
    "left token is a short form",
    "a window follows",
    "a prefix aligns",
)


def _text_and_gold_starts(document, style: str) -> tuple[str, list[int], int]:
    """``(text, gold long-form start offsets, gold long-form count)``.

    Three corpus shapes reach this runner and none of them agree on how a long
    form is located. A char-span corpus gives offsets into real text; PLOD gives
    token indices into a sentence that has to be detokenised first; a pair
    corpus gives no offsets at all, so the gold string is searched for. The
    third is weaker evidence than the first two and is labelled as such wherever
    the number is printed.
    """
    text = getattr(document, "text", None)
    if text is None:  # PLOD: token indices into a detokenised sentence
        text, offsets = document.render(style)
        starts = [
            offsets[start][0] for start, _ in document.long_form_spans if start < len(offsets)
        ]
        return text, starts, len(document.long_form_spans)
    spans = getattr(document, "long_form_spans", None)
    if spans is not None:
        return text, [start for start, _ in spans], len(spans)
    starts = []
    for pair in document.pairs:
        index = text.find(pair.long_form) if pair.long_form else -1
        if index >= 0:
            starts.append(index)
    return text, starts, len(document.pairs)


def legend_exposure(
    documents: Sequence, *, corpus: str, split: str, settings: dict, style: str = "tight"
) -> dict:
    """Count how far each ``=`` gets through the legend gates, corpus by corpus.

    R9.5, and it is the whole reason a MED1250 null result can be read at all.
    "Precision did not move on MED1250" is two very different statements
    depending on whether the rule fired there and was right, or never fired.
    This funnel says which, and it says it with the extractor's own private
    gates rather than a regex approximation of them, so it cannot drift from
    what the code does.

    The last column of the gold side is the corpus-capability figure: how many
    gold long forms begin immediately after a separator. A corpus with none of
    those cannot show the phenomenon in either direction, which is exactly the
    trap PLOD set for ``two_word`` in D-032.

    Args:
        documents: Any corpus whose documents carry ``.text``. Gold long-form
            spans are used when the documents have them; ``.pairs`` are used
            when they do not.
        corpus: Corpus name for the record.
        split: Split label, including its role.
        settings: Extraction profile overrides.

    Returns:
        One ``results.json`` record.
    """
    _restore()
    extractor = AbbreviationExtractor(Config(**settings), legend_syntax=True)  # type: ignore[arg-type]
    counts: Counter = Counter()
    emitted: list[tuple[str, str, str]] = []
    gold_after_separator = 0
    gold_spans = 0
    for document in documents:
        text, gold_starts, gold_here = _text_and_gold_starts(document, style)
        cursor = 0
        while True:
            index = text.find("=", cursor)
            if index < 0:
                break
            cursor = index + 1
            counts["separators"] += 1
            if index == 0 or index + 1 >= len(text):
                continue
            if (
                text[index - 1] in extractor_module._LEGEND_OPERATOR_CHARS
                or text[index + 1] in extractor_module._LEGEND_OPERATOR_CHARS
            ):
                continue
            counts["not an operator"] += 1
            preceding = extractor._preceding_token(text, index)
            if preceding is None:
                continue
            counts["left token is a short form"] += 1
            window = extractor._legend_window(text, index, len(preceding[0]))
            if window is None:
                continue
            counts["a window follows"] += 1
            pair = extractor._legend_long_form(
                text, preceding[0], (preceding[1], preceding[2]), window
            )
            if pair is None:
                continue
            counts["a prefix aligns"] += 1
            emitted.append((document.uid, pair.short_form, pair.long_form))
        gold_spans += gold_here
        for start in gold_starts:
            probe = start - 1
            while probe >= 0 and text[probe].isspace():
                probe -= 1
            gold_after_separator += probe >= 0 and text[probe] == "="

    print(f"\nlegend gates on {corpus} [{split}], profile settings {sorted(settings.items())}")
    print(f"{'gate':<30} {'n':>7} {'share of separators':>21}")
    print("-" * 60)
    total = counts["separators"]
    for gate in _LEGEND_GATES:
        share = f"{counts[gate] / total * 100:19.2f}%" if total else f"{'--':>20}"
        print(f"{gate:<30} {counts[gate]:>7} {share:>21}")
    if gold_spans:
        print(
            f"gold long forms starting immediately after a separator: "
            f"{gold_after_separator} of {gold_spans} "
            f"({gold_after_separator / gold_spans * 100:.2f}% -- the corpus capability)"
        )
    for uid, short_form, long_form in emitted[:20]:
        print(f"    [{uid}] {short_form!r} -> {long_form!r}")
    return {
        "corpus": corpus,
        "split": split,
        "profile_settings": {key: settings[key] for key in sorted(settings)},
        "detokenisation": style,
        **{"gate_" + _slug(gate): counts[gate] for gate in _LEGEND_GATES},
        "gold_long_form_spans": gold_spans,
        "gold_long_form_spans_after_a_separator": gold_after_separator,
        "gold_long_form_spans_after_a_separator_pct": (
            round(gold_after_separator / gold_spans * 100, 2) if gold_spans else 0.0
        ),
        "pairs_emitted": [
            {"sample": uid, "short_form": short_form, "long_form": long_form}
            for uid, short_form, long_form in emitted
        ],
    }


# ---------------------------------------------------------------------------
# 3b. the same fixes, on the two span-detection corpora
# ---------------------------------------------------------------------------
# MED1250 is a declared tuning split, so a variant table measured only there
# cannot say whether a fix generalises -- and R6 wants every component measured
# on at least two corpora before it ships. These are the two corpora that can be
# scored without inventing any part of the gold standard: both annotate spans
# and neither pairs them, so short forms and long forms are scored separately,
# exactly as each corpus's own scorer does. No pairing is derived anywhere.
#
# READ THE STRUCTURE TABLE BEFORE THE SCORE TABLE. A neutral result is only
# evidence of neutrality on a corpus capable of showing the phenomenon, and
# PLOD is not: it has no multi-token gold short form for ``two_word`` to get
# right and almost no bracketed one for ``balanced_trim`` to reach. The
# structure counts are printed above the scores so the two cannot be read apart.
_SPAN_LABELS = ("short_form", "long_form")
_SPAN_CONVENTIONS = ("exact", "overlap")


def _char_span_set(span: tuple[int, int]) -> frozenset:
    """One half-open character span as the set of offsets it covers."""
    return frozenset(range(span[0], span[1]))


def _engine_pairs(text: str, settings: dict) -> list:
    """Whatever the engine currently installed reports for ``text``."""
    from acronymkit import AcronymEngine

    return AcronymEngine(Config(**settings)).extract_definitions(text)  # type: ignore[arg-type]


def _engine_spans(text: str, settings: dict) -> dict[str, tuple[frozenset, ...]]:
    """Run the shipped engine over ``text`` and keep its own character offsets.

    No localiser: this corpus is real prose with real offsets, so the spans the
    extractor reports can be compared to the annotation directly. That is a
    privilege ``bench/run_spans.py`` deliberately denies itself on PLOD, where
    external baselines have to have their spans string-searched; here there is
    no external baseline in the table, so there is nothing to flatter.
    """
    shorts: list[frozenset] = []
    longs: list[frozenset] = []
    for pair in _engine_pairs(text, settings):
        shorts.append(_char_span_set(pair.short_form_span))
        longs.append(_char_span_set(pair.long_form_span))
    return {"short_form": run_spans._distinct(shorts), "long_form": run_spans._distinct(longs)}


def _tally(gold: dict, predicted: dict) -> dict[str, list[int]]:
    """``(true positives, false positives, false negatives)`` for one document.

    Matching is ``bench/run_spans.match`` rather than a second implementation of
    it, so ``exact`` and ``overlap`` mean here exactly what they mean on PLOD --
    including the one-to-one claim that stops a single sprawling prediction
    scoring against every gold span it touches.
    """
    counts: dict[str, list[int]] = {}
    for label in _SPAN_LABELS:
        for convention in _SPAN_CONVENTIONS:
            claimed = run_spans.match(gold[label], predicted[label], convention)
            counts[f"{label}.{convention}"] = [
                len(claimed),
                len(predicted[label]) - len(claimed),
                len(gold[label]) - len(claimed),
            ]
    return counts


def _score_char_spans(documents: Sequence, settings: dict) -> dict:
    """Score the engine's own character offsets against a char-span corpus."""
    totals = {f"{label}.{c}": [0, 0, 0] for label in _SPAN_LABELS for c in _SPAN_CONVENTIONS}
    for document in documents:
        gold = {
            "short_form": [_char_span_set(s) for s in document.short_form_spans],
            "long_form": [_char_span_set(s) for s in document.long_form_spans],
        }
        counts = _tally(gold, _engine_spans(document.text, settings))
        for key, values in counts.items():
            for index in range(3):
                totals[key][index] += values[index]
    return {
        key: run_spans.SpanScore(key.split(".")[0], key.split(".")[1], *values)
        for key, values in totals.items()
    }


def _score_token_spans(documents: Sequence, settings: dict, style: str) -> dict:
    """Score the engine's own offsets against PLOD, mapped into token space."""
    predictions, _ = run_spans.predict_acronymkit_native(documents, style, **settings)
    scores, _ = run_spans.score(documents, predictions)
    return scores


def plod_structure(documents: Sequence) -> dict:
    """Is PLOD structurally capable of showing either short-form-span defect?

    ``two_word`` can only change an answer where a gold short form spans more
    than one token; ``balanced_trim`` can only change one where a gold short
    form carries a bracket character. Both counts are near zero here, so a
    neutral PLOD row is a statement about this corpus's annotation and not about
    the fix. R9.5, and the reason it is printed in the same table as the score.
    """
    statistics = dict(run_spans.corpus_statistics(documents))
    multi_token = 0
    bracketed = 0
    for document in documents:
        for start, end in document.short_form_spans:
            multi_token += end - start > 1
            surface = " ".join(document.tokens[start:end])
            bracketed += any(character in surface for character in "()[]{}")
    total = statistics["short_form_spans"]
    statistics.update(
        {
            "gold_short_form_spans_multi_token": multi_token,
            "gold_short_form_spans_multi_token_pct": round(100 * multi_token / max(total, 1), 2),
            "gold_short_form_spans_with_bracket": bracketed,
            "gold_short_form_spans_with_bracket_pct": round(100 * bracketed / max(total, 1), 2),
        }
    )
    return statistics


def sdu22_structure(documents: Sequence) -> dict:
    """The SDU-22 recall ceiling, recomputed, plus the same two capability counts."""
    statistics = dict(corpora.sdu22_ae_recall_ceiling(documents))
    multi_token = 0
    bracketed = 0
    for document in documents:
        for surface in document.short_forms():
            multi_token += len(surface.split()) > 1
            bracketed += any(character in surface for character in "()[]{}")
    total = statistics["gold_short_form_spans"]
    statistics.update(
        {
            "documents": len(documents),
            "gold_short_form_spans_multi_token": multi_token,
            "gold_short_form_spans_multi_token_pct": round(100 * multi_token / max(total, 1), 2),
            "gold_short_form_spans_with_bracket": bracketed,
            "gold_short_form_spans_with_bracket_pct": round(100 * bracketed / max(total, 1), 2),
        }
    )
    return statistics


def sdu22_function_word_exposure(documents: Sequence, domain: str, settings: dict) -> dict:
    """Every SDU-22 prediction the function-word rule would delete, and its fate.

    The MED1250 exposure count says the rule removes three wrong answers and no
    right ones. That is a statement about one tuning corpus in one domain, and
    it does not survive being asked again somewhere else. Here it is asked
    again, on institutional and on scientific prose, and the answer is
    different -- which is the whole reason R6 wants two corpora.

    The asymmetry is structural rather than incidental. acronymkit emits
    *pairs*, so a rule that rejects a long form deletes the short form standing
    beside it. On a corpus that scores short forms and long forms separately,
    every long-form false positive this removes costs a short-form true positive
    at the same time.
    """
    _restore()
    rows: list[dict] = []
    short_form_correct = 0
    long_form_correct = 0
    predicted = 0
    for document in documents:
        gold_short = set(document.short_form_spans)
        gold_long = set(document.long_form_spans)
        spans = _engine_spans(document.text, settings)
        predicted += len(spans["short_form"])
        for pair in _engine_pairs(document.text, settings):
            if not leads_with_function_word(pair.long_form):
                continue
            short_hit = pair.short_form_span in gold_short
            long_hit = pair.long_form_span in gold_long
            short_form_correct += short_hit
            long_form_correct += long_hit
            rows.append(
                {
                    "sample": document.uid,
                    "short_form": pair.short_form,
                    "long_form": pair.long_form,
                    "short_form_span_correct": short_hit,
                    "long_form_span_correct": long_hit,
                }
            )
    print(
        f"\nSDU-22 {domain} dev: {len(rows)} of {predicted} predictions lead with a function "
        f"word; {short_form_correct} carry a correct short-form span and "
        f"{long_form_correct} a correct long-form span -- all of which the rule deletes"
    )
    for row in rows:
        print(
            f"    [{row['sample']}] {row['short_form']!r} -> {row['long_form']!r}  "
            f"SF {'hit' if row['short_form_span_correct'] else 'miss'}, "
            f"LF {'hit' if row['long_form_span_correct'] else 'miss'}"
        )
    return {
        "corpus": f"sdu22_ae_{domain}",
        "split": "dev (tuning, contaminated)",
        "rule": "reject a long form whose first word is in _strategies.SKIPPABLE",
        "predicted_short_form_spans": predicted,
        "predicted_leading_function_word": len(rows),
        "predicted_leading_function_word_short_form_correct": short_form_correct,
        "predicted_leading_function_word_long_form_correct": long_form_correct,
        "cases": rows,
    }


def span_variants(profile: str = "high_precision") -> dict:
    """Score every variant on PLOD and SDU@AAAI-22 AE, decomposed by corpus.

    One profile, because the axis under test here is the fix rather than the
    admission gate, and ``high_precision`` is what ``Config()`` gives a caller
    who chooses nothing. The MED1250 table above sweeps all three.

    PLOD is scored on ``dev``, ``test`` **and** the pooled corpus, under both
    detokenisation styles, for a reason that decides one of these fixes: the
    two halves hold 263 and 270 gold short-form spans, so a delta of a fifth of
    a percentage point is one span and neither half can resolve it. The pooled
    split holds 2,869. Reporting only the halves would print "neutral" for an
    effect the corpus can in fact see, and reporting only the pooled split would
    hide whether it decomposes. Both styles, because
    ``bench/run_spans.py`` already established that choosing one puts an
    arbitrary decision inside a number -- and the two disagree here.

    Args:
        profile: Key into :data:`_PROFILES`.

    Returns:
        ``{run_id: record}`` for :func:`save_results`.
    """
    settings = _PROFILES[profile]
    styles = tuple(corpora.DETOKENISE_STYLES)
    recorded: dict = {}

    plod = {split: corpora.read_plod_cw(split=split) for split in ("dev", "test", "all")}
    sdu22 = {
        domain: corpora.read_sdu22_ae(domain=domain, split="dev")
        for domain in ("legal", "scientific")
    }

    print("\ncorpus structure -- read this before the scores below")
    print(
        f"{'corpus':<28} {'docs':>6} {'gold SF':>8} {'gold LF':>8} "
        f"{'multi-tok SF':>13} {'bracketed SF':>13} {'SF recall ceiling':>18}"
    )
    print("-" * 100)
    for split, documents in plod.items():
        statistics = plod_structure(documents)
        recorded[f"shortform.plod_{split}.corpus"] = {
            "corpus": f"plod_cw_{split}",
            "split": f"{split} (held_out, span detection)",
            **statistics,
        }
        print(
            f"{'plod_cw_' + split:<28} {statistics['documents']:>6} "
            f"{statistics['short_form_spans']:>8} {statistics['long_form_spans']:>8} "
            f"{statistics['gold_short_form_spans_multi_token_pct']:>12.2f}% "
            f"{statistics['gold_short_form_spans_with_bracket_pct']:>12.2f}% "
            f"{statistics['short_form_spans_bracket_adjacent_pct']:>17.2f}%"
        )
    for domain, documents in sdu22.items():
        statistics = sdu22_structure(documents)
        recorded[f"shortform.sdu22_ae_{domain}_dev.corpus"] = {
            "corpus": f"sdu22_ae_{domain}",
            "split": "dev (tuning, contaminated)",
            **statistics,
        }
        print(
            f"{'sdu22_ae_' + domain + '_dev':<28} {statistics['documents']:>6} "
            f"{statistics['gold_short_form_spans']:>8} "
            f"{statistics['gold_long_form_spans']:>8} "
            f"{statistics['gold_short_form_spans_multi_token_pct']:>12.2f}% "
            f"{statistics['gold_short_form_spans_with_bracket_pct']:>12.2f}% "
            f"{statistics['ceiling_pct']:>17.2f}%"
        )
    print(
        "\nSF recall ceiling: for PLOD, the share of gold short forms standing in one of the\n"
        "two parenthetical arrangements; for SDU-22, gold long forms / gold short forms.\n"
        "Neither is a bound -- see bench/splits.toml, shortform_recall_ceiling_basis -- and\n"
        "every point above the SDU-22 figure is bought in long-form precision."
    )

    header = (
        f"\n{'corpus / detokenisation':<30} {'variant':<14} {'label':<11} "
        f"{'exP':>6} {'exR':>6} {'exF1':>6} | {'ovP':>6} {'ovR':>6} {'ovF1':>6}"
    )
    print(header)
    print("-" * (len(header) - 1))
    for name, balanced, two_word, function_word, legend in _VARIANTS:
        _install(
            balanced_trim=balanced,
            two_word=two_word,
            function_word=function_word,
            legend=legend,
        )
        rows: list[tuple[str, str, dict, int, dict]] = []
        for split, documents in plod.items():
            for style in styles:
                rows.append(
                    (
                        f"plod_cw_{split}",
                        f"shortform.plod_{split}.{style}.{profile}.{name}",
                        _score_token_spans(documents, settings, style),
                        len(documents),
                        {
                            "split": f"{split} (held_out, span detection)",
                            "detokenisation": style,
                            "scorer": "PLOD token-index spans, per label",
                        },
                    )
                )
        for domain, documents in sdu22.items():
            rows.append(
                (
                    f"sdu22_ae_{domain}_dev",
                    f"shortform.sdu22_ae_{domain}_dev.{profile}.{name}",
                    _score_char_spans(documents, settings),
                    len(documents),
                    {
                        "split": "dev (tuning, contaminated)",
                        "scorer": "SDU-22 AE phrase-level char spans, per label",
                    },
                )
            )
        for corpus_name, run_id, scores, count, extra in rows:
            recorded[run_id] = run_spans.entry(
                scores,
                corpus=corpus_name,
                system="acronymkit",
                profile=profile,
                variant=name,
                comparator=_COMPARATOR[name],
                balanced_trim=balanced,
                two_word_short_form=two_word,
                reject_leading_function_word=function_word,
                legend_syntax=legend,
                span_source="native offsets",
                documents=count,
                **extra,
            )
            label_for_row = f"{corpus_name}/{extra.get('detokenisation', 'char')}"
            for index, label in enumerate(_SPAN_LABELS):
                exact = scores[f"{label}.exact"]
                overlap = scores[f"{label}.overlap"]
                print(
                    f"{label_for_row if index == 0 else '':<30} "
                    f"{name if index == 0 else '':<14} {label:<11} "
                    f"{exact.precision * 100:6.2f} {exact.recall * 100:6.2f} "
                    f"{exact.f1 * 100:6.2f} | "
                    f"{overlap.precision * 100:6.2f} {overlap.recall * 100:6.2f} "
                    f"{overlap.f1 * 100:6.2f}"
                )
    _restore()
    for domain, documents in sdu22.items():
        recorded[f"shortform.sdu22_ae_{domain}_dev.function_word_exposure"] = (
            sdu22_function_word_exposure(documents, domain, settings)
        )
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
    _restore()

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
    parser.add_argument(
        "--spans",
        action="store_true",
        help="score every variant on PLOD and SDU@AAAI-22 AE, decomposed by corpus",
    )
    parser.add_argument(
        "--legend",
        action="store_true",
        help="count how far every '=' gets through the legend gates, per corpus",
    )
    parser.add_argument("--relaxations", action="store_true")
    parser.add_argument("--gates", type=Path, help="directory holding Lf1chSf and SingTermFreq.dat")
    parser.add_argument(
        "--interpreter",
        default=sys.executable,
        help="Python that has pyab3p installed; needed by --attribute",
    )
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    med1250_wanted = (
        args.attribute
        or args.ceiling
        or args.variants
        or args.relaxations
        or args.legend
        or bool(args.gates)
    )
    if not (med1250_wanted or args.spans):
        parser.error(
            "choose at least one of --attribute, --ceiling, --variants, --spans, "
            "--legend, --relaxations, --gates"
        )

    recorded: dict = {}
    if args.spans:
        recorded.update(span_variants())
    if not med1250_wanted:
        if args.save:
            path = save_results(recorded)
            print(f"\nsaved {len(recorded)} run(s) to {path.relative_to(REPO_ROOT)}")
        return 0

    documents = corpora.load("med1250")

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
    if args.legend:
        recorded["shortform.med1250_all.legend_exposure"] = legend_exposure(
            documents,
            corpus="med1250",
            split="all (tuning)",
            settings=_PROFILES["high_precision"],
        )
        recorded["shortform.med1250_all.legend_exposure_biomedical"] = legend_exposure(
            documents,
            corpus="med1250",
            split="all (tuning)",
            settings=_PROFILES["biomedical"],
        )
        for domain in ("legal", "scientific"):
            recorded[f"shortform.sdu22_ae_{domain}_dev.legend_exposure"] = legend_exposure(
                corpora.read_sdu22_ae(domain=domain, split="dev"),
                corpus=f"sdu22_ae_{domain}",
                split="dev (tuning, contaminated)",
                settings=_PROFILES["high_precision"],
            )
        for split in ("dev", "test", "all"):
            recorded[f"shortform.plod_{split}.legend_exposure"] = legend_exposure(
                corpora.read_plod_cw(split=split),
                corpus=f"plod_cw_{split}",
                split=f"{split} (held_out, span detection)",
                settings=_PROFILES["high_precision"],
            )
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
