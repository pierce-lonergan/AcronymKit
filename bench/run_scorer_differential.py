#!/usr/bin/env python3
"""Check the extraction harness against something that is not the extraction harness.

Why this file exists
--------------------
``docs/EVALUATION.md`` used to argue that the extraction reader and scorer were
correct because ``pyab3p``'s score here landed within half a point of Ab3P's
published figures. That sentence cited numbers matching neither
``bench/results.json`` nor the table five lines above it, appealed to a paper
nobody in this repository has read, and was **withdrawn** rather than restated
(D-060). The withdrawal left a hole: every row in the extraction table is
produced by this harness, which is what makes the rows comparable to each other
and exactly why no arrangement of them can adjudicate the harness.

The honest substitute is a **differential**: run something that is not this
harness over the same corpus and require agreement to the digit.

What was looked for, and what was actually found
------------------------------------------------
The brief for this file assumed a reference **scorer** — "MED1250 ships with
Ab3P's own evaluation conventions". It does not. Counted rather than asserted,
and every count below is saved as a field of
``differential.med1250.reference_output`` so that a later reader can re-derive
it instead of taking this paragraph's word:

* ``pyab3p`` 0.1.1's wheel contains one compiled extension and a ``word_data``
  directory. Its public surface is two names, ``Ab3p`` and ``AbbrOut``, and
  ``Ab3p`` has one method, ``get_abbrs``. **Zero** evaluation entry points.
* Ab3P upstream at the commit ``tools/fetch_data.py`` already pins ships a
  ``Makefile`` with seven named targets carrying a recipe. Its ``test`` target
  is ``./identify_abbr MED1250_unlabeled | diff identify_abbr-out -`` — a
  *reproduction* check against a stored output file. **Zero** targets compute a
  precision, a recall or an F-score, and no scoring program is distributed.
* Two shared-task scorers are already in this tree and **neither can express
  the task**. ``data/sdu21_ad_scorer.py`` aligns one gold label per instance by
  id, which is classification, not set-valued extraction.
  ``data/sdu22_ae_scorer.py`` scores token-index spans and never pairs a short
  form with a long form — and MED1250's gold carries no offsets anywhere in the
  file (D-048), so there is nothing to hand it. Not near misses: the wrong
  shape, twice.

**So the scorer half of the vacancy cannot be closed by a differential, and
this file does not claim to close it.** What Ab3P *does* ship is
``identify_abbr-out``: 1.6 MB of the reference implementation's own output over
MED1250, produced by the NLM, checked in in 2016, and never read by this
repository. That is a **prediction** reference, and it adjudicates the half of
the harness the scorer sits behind — the reader, the record segmentation and
the system adapter.

The five arms
-------------
``differential.med1250.reference_output``
    NLM's canonical Ab3P output against ``pyab3p`` driven through this
    repository's reader, pair for pair; and the canonical predictions scored by
    ``bench/scoring.py`` against the gated ``extraction.med1250.pyab3p`` row.
    The first needs ``--interpreter``; the second is offline and is the one
    that reproduces a published figure.

``differential.med1250.scorer_agreement``
    ``bench/scoring.py`` against :func:`independent_counts`, a second scorer in
    this file written from the *documented* convention with a different
    implementation of every step. Same shape as
    ``governed_catalog.socrata.scorer_agreement``, and **weaker than it**: that
    one compared two scorers written by two workstreams in two files for two
    questions. This one compares a scorer against a reimplementation written in
    the same round by the same author for the purpose of agreeing, so
    common-author error is precisely what it cannot detect.

``differential.med1250.harness_ceiling``
    The gold fed back as a prediction set. It does not score 100.

``differential.med1250.specification``
    The decisions ``bench/scoring.py`` makes that its own documentation does
    not state, each with the number of points it is worth.

``differential.med1250.reference_output_mutations``
    The first arm, shown failing. Five perturbations of the text this harness
    hands the extractor, each compared against the untouched reference output.
    Needs ``--interpreter``.

Usage::

    python bench/run_scorer_differential.py --fetch          # 1.6 MB, once
    python bench/run_scorer_differential.py
    python bench/run_scorer_differential.py --save
    python bench/run_scorer_differential.py --interpreter /path/to/python3.12
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import platform
import re
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from bench import corpora, scoring  # noqa: E402
from bench.run_extraction import dedupe_per_document, predict_acronymkit  # noqa: E402

Pair = Tuple[str, str]
Predictions = Dict[str, List[Pair]]

#: The Ab3P commit ``tools/fetch_data.py`` already pins for ``MED1250_labeled``.
#: The reference output is fetched from the same tree, so the predictions and
#: the gold cannot drift apart.
AB3P_COMMIT = "41130cddfcba1449ba612905d4a51274f8f565a8"
REFERENCE_URL = f"https://raw.githubusercontent.com/ncbi-nlp/Ab3P/{AB3P_COMMIT}/identify_abbr-out"
REFERENCE_PATH = corpora.DATA_DIR / "ab3p_reference" / "identify_abbr-out"

#: SHA-256 of ``identify_abbr-out`` at that commit, taken on 2026-08-25. The
#: pin is the point: an unpinned reference output is a reference that can be
#: edited under the check that reads it.
REFERENCE_SHA256 = "c4b85fa6e30658a430a4910fa8038a6dec59c2072d58dd60d9b1ddbe6c365dbd"

#: The gated row this file's reference arm must reproduce.
GATED_PYAB3P_RUN_ID = "extraction.med1250.pyab3p"

#: Recorded in the entry, because a fetched artefact whose terms live only in
#: another tool's constants is an artefact whose terms nobody can find from the
#: number that used it. Same file, same commit, same terms as
#: ``MED1250_labeled``, which ``tools/fetch_data.py`` already fetches under
#: them. **Fetch-only, on the same precedent as the corpus**: it is not
#: vendored into the wheel and not committed to this repository.
REFERENCE_LICENCE = {
    "licence": "Public domain (United States Government Work)",
    "licence_url": f"https://raw.githubusercontent.com/ncbi-nlp/Ab3P/{AB3P_COMMIT}/README.md",
    "attribution": (
        "Sohn S, Comeau DC, Kim W, Wilbur WJ. Abbreviation definition identification "
        "based on automatic precision estimates. BMC Bioinformatics. 2008;9:402. "
        "National Library of Medicine."
    ),
    "vendored": False,
}

#: Counted facts about the reference-scorer search, saved rather than asserted.
#: Each is re-derivable from the artefact named beside it in the module
#: docstring; none is a judgement.
SEARCH_COUNTS: Dict[str, int] = {
    "pyab3p_public_names": 2,
    "pyab3p_public_methods_on_ab3p": 1,
    "pyab3p_scoring_entry_points": 0,
    "ab3p_makefile_recipe_targets": 7,
    "ab3p_makefile_scoring_targets": 0,
    "shared_task_scorers_in_tree": 2,
    "shared_task_scorers_expressing_pair_extraction": 0,
}

#: Prediction sets that are not an extractor. ``gold_as_prediction`` measures
#: the harness's ceiling and ``empty`` is the null control; both agree between
#: any two scorers trivially, so they are named here rather than counted into
#: the agreement figure without a label.
SYNTHETIC_PREDICTION_SETS = frozenset({"empty", "gold_as_prediction"})

#: A bare PubMed ID delimits a record in ``MED1250_labeled``. ``identify_abbr``
#: echoes every input line before the abbreviations it found in that line, so
#: the same rule delimits records in its output — and the two files are the
#: labelled and unlabelled halves of one corpus, so the rule has to be the same
#: one ``bench/corpora.read_med1250`` uses or the alignment means nothing.
_PUBMED_ID = re.compile(r"^\d{1,9}\s*$")


# ---------------------------------------------------------------------------
# the reference output
# ---------------------------------------------------------------------------
def fetch_reference_output(*, refresh: bool = False) -> Path:
    """Download ``identify_abbr-out`` from the pinned Ab3P commit and verify it.

    ``bench/run_governed_gold.py`` and ``bench/run_genre.py`` already fetch
    their own corpora rather than going through ``tools/fetch_data.py``; this
    follows them.

    Args:
        refresh: Re-download even if the cache is present.

    Returns:
        Path to the cached file.

    Raises:
        SystemExit: If the download does not match :data:`REFERENCE_SHA256`.
    """
    if REFERENCE_PATH.is_file() and not refresh:
        return REFERENCE_PATH
    REFERENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(REFERENCE_URL, timeout=120) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != REFERENCE_SHA256:
        raise SystemExit(
            f"{REFERENCE_URL}\n  expected sha256 {REFERENCE_SHA256}\n  got      sha256 {digest}"
        )
    REFERENCE_PATH.write_bytes(payload)
    return REFERENCE_PATH


def read_reference_output(path: Optional[Path] = None) -> Predictions:
    """Parse the NLM's own Ab3P output into this harness's document keys.

    ``identify_abbr`` prints each input line, then one indented
    ``sf|lf|precision`` line per abbreviation found in it. Records are keyed the
    way :func:`bench.corpora.read_med1250` keys them — ``position:pubmed_id`` —
    because two PubMed IDs occur twice in this corpus and the identifier alone
    is not unique.

    Args:
        path: Override the cached location.

    Returns:
        ``{document uid: [(short, long), ...]}``, in file order.

    Raises:
        SystemExit: If the reference output has not been fetched.
    """
    source = path or REFERENCE_PATH
    if not source.is_file():
        raise SystemExit(f"missing {source}\nRun: python bench/run_scorer_differential.py --fetch")
    records: List[List[str]] = []
    for line in source.read_text(encoding="utf-8", errors="replace").split("\n"):
        if _PUBMED_ID.match(line):
            records.append([line.strip()])
        elif records:
            records[-1].append(line)
    predictions: Predictions = {}
    for position, lines in enumerate(records):
        pairs: List[Pair] = []
        for line in lines[1:]:
            if line.startswith("  ") and "|" in line:
                fields = line.strip().split("|")
                if len(fields) >= 2 and fields[0] and fields[1]:
                    pairs.append((fields[0], fields[1]))
        predictions[f"{position:04d}:{lines[0]}"] = pairs
    return predictions


# ---------------------------------------------------------------------------
# the second scorer
# ---------------------------------------------------------------------------
#: Determiners the relaxed convention drops. Same closed list ``bench/scoring``
#: uses; it is part of the convention rather than of the implementation.
_DETERMINERS = frozenset({"the", "a", "an", "its", "their", "our", "this", "these", "those"})

#: Characters the relaxed convention trims from either end. Written as a set of
#: literals rather than a regular-expression class, because a second scorer that
#: reuses the first one's regex is not a second scorer. The two dashes are
#: escapes for the same reason ``bench/scoring.py`` writes them that way: a
#: reader cannot tell a stray en dash from an intended one.
_EN_DASH = "\u2013"
_EM_DASH = "\u2014"
_EDGE_CHARACTERS = frozenset(" \t\n\r-" + _EN_DASH + _EM_DASH + ",;:.'" + '"' + "()[]")


def _collapse(text: str) -> str:
    """Whitespace-collapse by splitting and rejoining, not by substitution."""
    return " ".join(text.split())


def _trim_edges(text: str) -> str:
    """Walk in from both ends while the character is trimmable."""
    start, end = 0, len(text)
    while start < end and text[start] in _EDGE_CHARACTERS:
        start += 1
    while end > start and text[end - 1] in _EDGE_CHARACTERS:
        end -= 1
    return text[start:end]


def _drop_determiner(text: str) -> str:
    """Drop one leading determiner, and only when a word follows it."""
    head, separator, rest = text.partition(" ")
    return rest if separator and head.lower() in _DETERMINERS else text


def independent_key(pair: Pair, *, relaxed: bool, relaxed_short_form: bool = False) -> str:
    """Build a comparison key from the documented convention.

    Written from ``bench/scoring``'s stated convention — *"whitespace
    normalisation and case folding"* for exact, *"up to leading determiners and
    surrounding punctuation"* for relaxed — rather than from its code. Every
    step is implemented differently: character walks instead of regular
    expressions, ``partition`` instead of an anchored alternation.

    Args:
        pair: ``(short form, long form)``.
        relaxed: Apply the relaxed convention to the long form.
        relaxed_short_form: Also apply it to the short form. **Off by default,
            because that is what the shipped scorer does** — the documentation
            speaks only of the long form. It is a parameter rather than a
            constant because the choice is worth points and nothing said so.

    Returns:
        The key, with a NUL separating the two halves.
    """
    short, long_form = pair

    def render(value: str, apply_relaxed: bool) -> str:
        text = _collapse(value)
        if apply_relaxed:
            text = _trim_edges(_drop_determiner(_trim_edges(text)))
        return text.casefold()

    return f"{render(short, relaxed and relaxed_short_form)}\x00{render(long_form, relaxed)}"


def independent_counts(
    documents: Sequence[corpora.GoldDocument],
    predictions: Predictions,
    *,
    relaxed: bool,
    pooled: bool = True,
    relaxed_short_form: bool = False,
) -> Tuple[int, int, int]:
    """Multiset TP/FP/FN by ``Counter`` intersection rather than list removal.

    ``bench/scoring._count`` walks the predictions and removes from a mutable
    copy of the gold. This takes the multiset intersection instead. The two are
    the same statement about multisets and share no code.

    Args:
        documents: Gold documents.
        predictions: Predicted pairs per document uid.
        relaxed: Matching convention.
        pooled: Match over the whole corpus at once, which is what the shipped
            scorer does. ``False`` matches within each document — the reading
            the documentation invites, and the difference is measured rather
            than assumed to be zero.
        relaxed_short_form: See :func:`independent_key`.

    Returns:
        ``(true_positives, false_positives, false_negatives)``.
    """
    gold_all: collections.Counter = collections.Counter()
    predicted_all: collections.Counter = collections.Counter()
    true_positives = false_positives = false_negatives = 0
    for document in documents:
        gold = collections.Counter(
            independent_key(
                (pair.short_form, pair.long_form),
                relaxed=relaxed,
                relaxed_short_form=relaxed_short_form,
            )
            for pair in document.pairs
        )
        predicted = collections.Counter(
            independent_key(pair, relaxed=relaxed, relaxed_short_form=relaxed_short_form)
            for pair in predictions.get(document.uid, [])
        )
        if pooled:
            gold_all += gold
            predicted_all += predicted
            continue
        hits = sum((gold & predicted).values())
        true_positives += hits
        false_positives += sum(predicted.values()) - hits
        false_negatives += sum(gold.values()) - hits
    if pooled:
        hits = sum((gold_all & predicted_all).values())
        true_positives = hits
        false_positives = sum(predicted_all.values()) - hits
        false_negatives = sum(gold_all.values()) - hits
    return true_positives, false_positives, false_negatives


def rates(true_positives: int, false_positives: int, false_negatives: int) -> Tuple[float, ...]:
    """Precision, recall and F1 as percentages rounded to two places."""
    predicted = true_positives + false_positives
    actual = true_positives + false_negatives
    precision = true_positives / predicted if predicted else 0.0
    recall = true_positives / actual if actual else 0.0
    total = precision + recall
    f1 = 2 * precision * recall / total if total else 0.0
    return round(precision * 100, 2), round(recall * 100, 2), round(f1 * 100, 2)


# ---------------------------------------------------------------------------
# prediction sets
# ---------------------------------------------------------------------------
def prediction_sets(
    documents: Sequence[corpora.GoldDocument], reference: Predictions
) -> Dict[str, Predictions]:
    """Every prediction set available without a second interpreter.

    A differential over one prediction set measures one path through the
    scorer. Which sets are present is recorded with the result, because a
    scorer agreement taken over one system is a different claim from the same
    figure taken over five.

    Args:
        documents: Gold documents.
        reference: The NLM reference output, already parsed.

    Returns:
        ``{system name: predictions}``, deduplicated exactly as
        ``bench/run_extraction.py`` deduplicates before scoring.
    """
    raw: Dict[str, Predictions] = {
        "acronymkit": predict_acronymkit(documents),
        "ab3p_reference_output": reference,
        "gold_as_prediction": {
            document.uid: [(pair.short_form, pair.long_form) for pair in document.pairs]
            for document in documents
        },
        "empty": {document.uid: [] for document in documents},
    }
    optional: Dict[str, Callable[[], Predictions]] = {
        "abbreviations": lambda: _predict_abbreviations(documents),
        "abbreviation_extractor": lambda: _predict_abbreviation_extractor(documents),
    }
    for name, build in optional.items():
        try:
            raw[name] = build()
        except ImportError:
            continue
    return {name: dedupe_per_document(pairs) for name, pairs in raw.items()}


def _predict_abbreviations(documents: Sequence[corpora.GoldDocument]) -> Predictions:
    """The other pure-Python Schwartz & Hearst implementation, if installed."""
    from abbreviations import schwartz_hearst

    return {
        document.uid: list(
            schwartz_hearst.extract_abbreviation_definition_pairs(doc_text=document.text).items()
        )
        for document in documents
    }


def _predict_abbreviation_extractor(documents: Sequence[corpora.GoldDocument]) -> Predictions:
    """The Rust implementation, if installed."""
    import abbreviation_extractor

    return {
        document.uid: [
            (item.abbreviation, item.definition)
            for item in abbreviation_extractor.extract_abbreviation_definition_pairs(document.text)
        ]
        for document in documents
    }


def _interpreter_version(interpreter: str) -> str:
    """Ask an interpreter what it is, so the result records a version not a path."""
    completed = subprocess.run(
        [interpreter, "-c", "import platform; print(platform.python_version())"],
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() or "unknown"


#: Perturbations of the text this harness hands the extractor, as Python
#: expressions over a name ``text``. They are expressions rather than functions
#: because the child process below embeds them **verbatim**: there is one
#: definition of each mutation, in this table, and no second copy that can
#: drift from it.
#:
#: Crude on purpose. The job is not to model a plausible reader bug, it is to
#: establish that the reference comparison is sensitive to its input at all.
TEXT_MUTATIONS: Dict[str, str] = {
    "casefold": "text.casefold()",
    "first_half": "text[: len(text) // 2]",
    "brackets_removed": 'text.replace("(", " ").replace(")", " ")',
    "words_reversed": '" ".join(reversed(text.split()))',
    "spaces_removed": 'text.replace(" ", "")',
}

#: The program the foreign interpreter runs. It imports ``bench.corpora``
#: (stdlib-only) and ``pyab3p`` and nothing else, so it loads under an
#: interpreter that has never heard of ``acronymkit`` -- the same constraint
#: ``bench/external.py`` is written under, met without editing that file.
_CHILD_PROGRAM = """
import json, sys
sys.path.insert(0, {repo!r})
from bench import corpora
import pyab3p
engine = pyab3p.Ab3p()
out = {{}}
for document in corpora.load("med1250"):
    text = document.text
    text = {expression}
    out[document.uid] = [(a.short_form, a.long_form) for a in engine.get_abbrs(text)]
print(json.dumps(out))
"""


def predict_pyab3p_out_of_process(
    interpreter: str, *, mutation: Optional[str] = None
) -> Predictions:
    """Drive ``pyab3p`` under an interpreter that has it.

    The unmutated path goes through ``bench/external.py``, which is the route
    every other runner uses and the one whose output is comparable with theirs.
    The mutated path runs :data:`_CHILD_PROGRAM` instead, because a mutation
    switch does not belong in a shared adapter that four other runners call.

    Args:
        interpreter: A CPython 3.12 or earlier with ``pyab3p`` installed.
        mutation: A key of :data:`TEXT_MUTATIONS`, applied to every document's
            text before the extractor sees it. ``None`` is the control.

    Returns:
        Raw predictions, not deduplicated.

    Raises:
        SystemExit: If the subprocess fails.
    """
    if mutation is None:
        command = [
            interpreter,
            str(REPO_ROOT / "bench" / "external.py"),
            "--system",
            "pyab3p",
            "--corpus",
            "med1250",
        ]
    else:
        command = [
            interpreter,
            "-c",
            _CHILD_PROGRAM.format(repo=str(REPO_ROOT), expression=TEXT_MUTATIONS[mutation]),
        ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise SystemExit(f"pyab3p failed under {interpreter}:\n{completed.stderr[-2000:]}")
    payload = json.loads(completed.stdout)
    predictions = payload["predictions"] if mutation is None else payload
    return {uid: [(pair[0], pair[1]) for pair in pairs] for uid, pairs in predictions.items()}


def reference_mutation_arm(interpreter: str, reference: Predictions) -> Dict[str, object]:
    """Show the reference comparison failing, in the environment where it runs.

    An agreement of ``1,053 of 1,053`` is evidence only once the comparison has
    been observed separating something. Each mutation perturbs the *text this
    harness hands the extractor* and nothing else — the reference output is
    untouched — so a mutation that leaves the verdict unchanged would mean the
    comparison is insensitive to the input, which is the failure mode an
    agreement figure hides.

    The mutations are deliberately crude and deliberately **committed**: the
    first version of this evidence was a fenced block of numbers produced in a
    scratch directory, which is a figure no gate can read (R16's shape applied
    to a code block rather than to an image).

    Args:
        interpreter: Python with ``pyab3p``.
        reference: The NLM reference output, parsed.

    Returns:
        The arm's entry: one field per mutation, holding documents differing.
    """
    discriminating = sum(1 for pairs in reference.values() if pairs)
    results: Dict[str, int] = {}
    for name in ("control", *sorted(TEXT_MUTATIONS)):
        got = predict_pyab3p_out_of_process(
            interpreter, mutation=None if name == "control" else name
        )
        keys = set(reference) | set(got)
        results[name] = sum(1 for key in keys if reference.get(key, []) != got.get(key, []))
    return {
        "corpus": "med1250",
        "arm": "reference_output_mutations",
        "system": "pyab3p under a mutated reader, against the NLM reference output",
        "harness_interpreter_version": _interpreter_version(interpreter),
        "documents": len(reference),
        "documents_discriminating": discriminating,
        "mutations_run": len(TEXT_MUTATIONS),
        "mutations_detected": sum(
            1 for name, count in results.items() if name != "control" and count
        ),
        "documents_differing": results,
    }


# ---------------------------------------------------------------------------
# arms
# ---------------------------------------------------------------------------
def reference_output_arm(
    documents: Sequence[corpora.GoldDocument],
    reference: Predictions,
    *,
    interpreter: Optional[str],
) -> Dict[str, object]:
    """NLM's own Ab3P predictions, against this harness two ways.

    Two comparisons, and only the first needs a foreign interpreter:

    1. **Prediction-level.** The reference output against ``pyab3p`` driven
       through ``bench/corpora.read_med1250``. NLM ran the C++ program over
       ``MED1250_unlabeled`` one line at a time; this harness hands the binding
       one string per record, assembled from the *labelled* file. Nothing
       guarantees those agree.
    2. **Figure-level.** The reference predictions scored by ``bench/scoring``
       against the gated ``extraction.med1250.pyab3p`` row. Offline.

    ``documents_discriminating`` is the count that matters and it is far below
    ``documents``: a record where both sides propose nothing agrees vacuously.

    Args:
        documents: Gold documents.
        reference: Parsed reference output.
        interpreter: Python with ``pyab3p``; ``None`` skips comparison 1.

    Returns:
        The arm's entry.
    """
    deduped = dedupe_per_document(reference)
    evaluation = scoring.evaluate(
        documents, deduped, corpus="med1250", system="ab3p_reference_output"
    )
    gated = _gated_run(GATED_PYAB3P_RUN_ID)
    figures = {
        f"{convention}_{metric}": round(getattr(evaluation.scores[convention], metric) * 100, 2)
        for convention in ("exact", "relaxed")
        for metric in ("precision", "recall", "f1")
    }
    reproduces = all(gated.get(name) == value for name, value in figures.items()) if gated else None

    entry: Dict[str, object] = {
        "corpus": "med1250",
        "arm": "reference_output",
        "source": REFERENCE_URL,
        "sha256": REFERENCE_SHA256,
        "ab3p_commit": AB3P_COMMIT,
        "documents": len(documents),
        # The alignment, saved rather than assumed. `scoring.evaluate` looks
        # predictions up by uid and silently ignores a key it does not know, so
        # a parser whose record boundaries drifted from the reader's would
        # produce a plausible score over a subset and say nothing. This is the
        # field that would go false first.
        "reference_records": len(reference),
        "reference_records_match_reader": set(reference)
        == {document.uid for document in documents},
        "reference_pairs_raw": sum(len(pairs) for pairs in reference.values()),
        "reference_pairs_scored": sum(len(pairs) for pairs in deduped.values()),
        "documents_discriminating": sum(1 for pairs in reference.values() if pairs),
        "documents_vacuous": sum(1 for pairs in reference.values() if not pairs),
        "gated_run_id": GATED_PYAB3P_RUN_ID,
        "reproduces_gated_row": reproduces,
        **figures,
        **SEARCH_COUNTS,
        **REFERENCE_LICENCE,
    }

    if interpreter is None:
        entry["harness_comparison"] = "not run"
        return entry

    harness = predict_pyab3p_out_of_process(interpreter)
    keys = set(reference) | set(harness)
    agreeing = sum(1 for key in keys if reference.get(key, []) == harness.get(key, []))
    reference_pairs = collections.Counter(
        (key, pair) for key, pairs in reference.items() for pair in pairs
    )
    harness_pairs = collections.Counter(
        (key, pair) for key, pairs in harness.items() for pair in pairs
    )
    shared = sum((reference_pairs & harness_pairs).values())
    entry.update(
        {
            "harness_comparison": "run",
            # The VERSION, not the path. A path is a property of one filesystem
            # and it carries a home directory into a committed file; the version
            # is the fact a later reader needs. R18's distinction, applied to a
            # field rather than to a timing.
            "harness_interpreter_version": _interpreter_version(interpreter),
            "documents_compared": len(keys),
            "documents_agreeing": agreeing,
            "documents_disagreeing": len(keys) - agreeing,
            "harness_pairs_raw": sum(harness_pairs.values()),
            "pairs_agreeing": shared,
            "pairs_only_in_reference": sum(reference_pairs.values()) - shared,
            "pairs_only_in_harness": sum(harness_pairs.values()) - shared,
        }
    )
    return entry


def scorer_agreement_arm(
    documents: Sequence[corpora.GoldDocument], systems: Dict[str, Predictions]
) -> Dict[str, object]:
    """``bench/scoring.py`` against :func:`independent_counts`, verdict by verdict.

    One verdict is one ``(system, convention)`` cell: the ``(TP, FP, FN)``
    triple and the three rates. Agreement is required on the integers, not on
    the rounded percentages — two scorers can round to the same two places from
    different counts, and a figure agreement over a count disagreement is the
    failure mode this arm exists to catch.

    Args:
        documents: Gold documents.
        systems: ``{name: deduplicated predictions}``.

    Returns:
        The arm's entry.
    """
    disagreements: List[str] = []
    counts_agreeing = figures_agreeing = verdicts = 0
    extractor_verdicts = 0
    pairs_scored = 0
    for name in sorted(systems):
        if name not in SYNTHETIC_PREDICTION_SETS:
            extractor_verdicts += 2
        predictions = systems[name]
        pairs_scored += sum(len(pairs) for pairs in predictions.values())
        evaluation = scoring.evaluate(documents, predictions, corpus="med1250", system=name)
        for convention in ("exact", "relaxed"):
            verdicts += 1
            shipped = evaluation.scores[convention]
            mine = independent_counts(documents, predictions, relaxed=convention == "relaxed")
            theirs = (
                shipped.true_positives,
                shipped.false_positives,
                shipped.false_negatives,
            )
            if mine == theirs:
                counts_agreeing += 1
            else:
                disagreements.append(f"{name}/{convention}: shipped {theirs} independent {mine}")
            shipped_rates = (
                round(shipped.precision * 100, 2),
                round(shipped.recall * 100, 2),
                round(shipped.f1 * 100, 2),
            )
            if shipped_rates == rates(*mine):
                figures_agreeing += 1
    return {
        "corpus": "med1250",
        "arm": "scorer_agreement",
        "system": "bench.scoring._count against run_scorer_differential.independent_counts",
        "shares_code_with_scorer_under_test": False,
        "written_by_a_second_author": False,
        "systems": sorted(systems),
        "prediction_sets": len(systems),
        "synthetic_prediction_sets": sorted(SYNTHETIC_PREDICTION_SETS),
        # The work count, without which the agreement is a number with no
        # denominator (R17). Both scorers visit every document once per verdict,
        # so this is `documents x verdicts` and is derived from the verdict count
        # rather than from the system count, which cannot drift from it.
        "document_scorings_per_scorer": len(documents) * verdicts,
        "pairs_scored": pairs_scored,
        "verdicts_compared": verdicts,
        "verdicts_from_extractors": extractor_verdicts,
        "verdicts_agreeing_on_counts": counts_agreeing,
        "verdicts_agreeing_on_figures": figures_agreeing,
        "verdicts_disagreeing": verdicts - counts_agreeing,
        "disagreements": disagreements,
    }


def harness_ceiling_arm(
    documents: Sequence[corpora.GoldDocument], systems: Dict[str, Predictions]
) -> Dict[str, object]:
    """What this harness scores when handed the gold as a prediction set.

    Not 100. ``bench/run_extraction.dedupe_per_document`` collapses repeated
    pairs inside a document and the gold is not deduplicated, so a record that
    genuinely defines the same pair twice has its second copy in the recall
    denominator and unreachable by any system. The runner documents the
    mechanism as *"a handful"*; this is the number.

    Args:
        documents: Gold documents.
        systems: Must contain ``gold_as_prediction``.

    Returns:
        The arm's entry.
    """
    gold_pairs = sum(len(document.pairs) for document in documents)
    reachable = sum(len(pairs) for pairs in systems["gold_as_prediction"].values())
    evaluation = scoring.evaluate(
        documents, systems["gold_as_prediction"], corpus="med1250", system="gold_as_prediction"
    )
    exact = evaluation.scores["exact"]
    affected = sum(
        1
        for document in documents
        if len(document.pairs) != len(systems["gold_as_prediction"][document.uid])
    )
    return {
        "corpus": "med1250",
        "arm": "harness_ceiling",
        "system": "gold_as_prediction",
        "gold_pairs": gold_pairs,
        "reachable_pairs": reachable,
        "unreachable_pairs": gold_pairs - reachable,
        "documents_affected": affected,
        "max_precision_pct": round(exact.precision * 100, 2),
        "max_recall_pct": round(exact.recall * 100, 2),
        "max_f1_pct": round(exact.f1 * 100, 2),
    }


def specification_arm(
    documents: Sequence[corpora.GoldDocument], systems: Dict[str, Predictions]
) -> Dict[str, object]:
    """The scorer's undocumented decisions, each priced.

    ``bench/scoring.py`` documents two matching conventions and a multiset. It
    does not document that matching is **pooled over the whole corpus**, so a
    prediction in one record can consume a gold pair from another; nor that the
    relaxed convention applies to the **long form only**, so a short form the
    annotator wrapped in punctuation is a miss under both conventions.

    Neither is a defect. Both are choices, and a choice nobody wrote down is
    indistinguishable from an accident until somebody measures it.

    Args:
        documents: Gold documents.
        systems: ``{name: deduplicated predictions}``.

    Returns:
        The arm's entry, with a per-system delta for each axis.
    """
    pooling: Dict[str, float] = {}
    short_form: Dict[str, float] = {}
    reclassified: Dict[str, int] = {}
    for name in sorted(systems):
        predictions = systems[name]
        for convention in ("exact", "relaxed"):
            relaxed = convention == "relaxed"
            base = rates(*independent_counts(documents, predictions, relaxed=relaxed))
            split = rates(
                *independent_counts(documents, predictions, relaxed=relaxed, pooled=False)
            )
            pooling[f"{name}/{convention}"] = round(base[2] - split[2], 2)
        base = rates(*independent_counts(documents, predictions, relaxed=True))
        both = independent_counts(documents, predictions, relaxed=True, relaxed_short_form=True)
        short_form[name] = round(rates(*both)[2] - base[2], 2)
        reclassified[name] = both[0] - independent_counts(documents, predictions, relaxed=True)[0]
    return {
        "corpus": "med1250",
        "arm": "specification",
        "axis_pooling_f1_delta_by_cell": pooling,
        "axis_pooling_max_abs_f1_delta": max(abs(value) for value in pooling.values()),
        "axis_relaxed_short_form_f1_delta_by_system": short_form,
        "axis_relaxed_short_form_max_f1_delta": max(short_form.values()),
        "axis_relaxed_short_form_pairs_reclassified": reclassified,
    }


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def _gated_run(run_id: str) -> Dict[str, object]:
    """Read one run out of ``bench/results.json``, or ``{}`` if it is absent."""
    path = REPO_ROOT / "bench" / "results.json"
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    run = document.get("runs", {}).get(run_id, {})
    return run if isinstance(run, dict) else {}


def environment() -> str:
    """One-line description of the machine, for the results file."""
    return f"Python {platform.python_version()} on {platform.system()} {platform.machine()}"


def save_results(entries: Mapping[str, object]) -> Path:
    """Merge ``entries`` into ``bench/results.json``. Runners are the only writers."""
    path = REPO_ROOT / "bench" / "results.json"
    document = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"runs": {}}
    runs = document.setdefault("runs", {})
    runs.update(entries)
    document["environment"] = environment()
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def render(entries: Dict[str, Dict[str, object]]) -> str:
    """Human-readable report."""
    reference = entries["differential.med1250.reference_output"]
    agreement = entries["differential.med1250.scorer_agreement"]
    ceiling = entries["differential.med1250.harness_ceiling"]
    specification = entries["differential.med1250.specification"]
    lines = [
        "REFERENCE SCORER SEARCH -- what exists, counted",
        f"  pyab3p public names                        {SEARCH_COUNTS['pyab3p_public_names']}",
        f"  pyab3p scoring entry points                {SEARCH_COUNTS['pyab3p_scoring_entry_points']}",
        f"  Ab3P Makefile recipe targets               {SEARCH_COUNTS['ab3p_makefile_recipe_targets']}",
        f"  ... of which compute P/R/F                 {SEARCH_COUNTS['ab3p_makefile_scoring_targets']}",
        "  verdict: no reference SCORER exists; a reference PREDICTION SET does",
        "",
        "ARM 1 -- NLM's own Ab3P output, scored by this harness",
        f"  documents                                  {reference['documents']}",
        f"  of which discriminating                    {reference['documents_discriminating']}",
        f"  of which vacuous (both sides empty)        {reference['documents_vacuous']}",
        f"  reference pairs scored                     {reference['reference_pairs_scored']}",
        f"  exact P/R/F1                               {reference['exact_precision']} / "
        f"{reference['exact_recall']} / {reference['exact_f1']}",
        f"  reproduces {GATED_PYAB3P_RUN_ID}   {reference['reproduces_gated_row']}",
        f"  prediction-level comparison                {reference['harness_comparison']}",
    ]
    if reference.get("harness_comparison") == "run":
        lines += [
            f"    documents agreeing                       "
            f"{reference['documents_agreeing']} of {reference['documents_compared']}",
            f"    pairs agreeing                           "
            f"{reference['pairs_agreeing']} of {reference['reference_pairs_raw']}",
        ]
    lines += [
        "",
        "ARM 2 -- scorer against an independently written scorer",
        f"  prediction sets                            {agreement['prediction_sets']}",
        f"  pairs scored                               {agreement['pairs_scored']}",
        f"  verdicts agreeing on counts                "
        f"{agreement['verdicts_agreeing_on_counts']} of {agreement['verdicts_compared']}",
        f"  verdicts agreeing on figures               "
        f"{agreement['verdicts_agreeing_on_figures']} of {agreement['verdicts_compared']}",
    ]
    problems = agreement["disagreements"]
    if isinstance(problems, list):
        lines += [f"    {problem}" for problem in problems]
    lines += [
        "",
        "ARM 3 -- the ceiling: the gold fed back as a prediction set",
        f"  gold pairs                                 {ceiling['gold_pairs']}",
        f"  unreachable by any system                  {ceiling['unreachable_pairs']} "
        f"in {ceiling['documents_affected']} documents",
        f"  max P/R/F1                                 {ceiling['max_precision_pct']} / "
        f"{ceiling['max_recall_pct']} / {ceiling['max_f1_pct']}",
        "",
        "ARM 4 -- the scorer's undocumented decisions, priced",
        f"  pooled vs per-document, max |dF1|          "
        f"{specification['axis_pooling_max_abs_f1_delta']}",
        f"  relaxed short form, max dF1                "
        f"{specification['axis_relaxed_short_form_max_f1_delta']}",
        f"  pairs reclassified by it                   "
        f"{specification['axis_relaxed_short_form_pairs_reclassified']}",
    ]
    mutations = entries.get("differential.med1250.reference_output_mutations")
    if mutations is not None:
        differing = mutations["documents_differing"]
        lines += [
            "",
            "ARM 5 -- arm 1's comparison, shown failing",
            f"  discriminating documents                   {mutations['documents_discriminating']}",
            f"  mutations detected                         "
            f"{mutations['mutations_detected']} of {mutations['mutations_run']}",
        ]
        if isinstance(differing, dict):
            lines += [
                f"    {name:<38} {count:>5} documents differ" for name, count in differing.items()
            ]
    lines += [
        "",
        f"environment : {environment()}",
    ]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fetch", action="store_true", help="download the Ab3P reference output")
    parser.add_argument("--refresh", action="store_true", help="re-download it")
    parser.add_argument(
        "--interpreter",
        help="Python with pyab3p installed; enables the prediction-level comparison",
    )
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    args = parser.parse_args(argv)

    if args.fetch or args.refresh:
        path = fetch_reference_output(refresh=args.refresh)
        print(f"reference output at {path.relative_to(REPO_ROOT)} (sha256 verified)")
        if not args.save:
            return 0

    documents = corpora.load("med1250")
    reference = read_reference_output()
    systems = prediction_sets(documents, reference)

    entries: Dict[str, Dict[str, object]] = {
        "differential.med1250.reference_output": reference_output_arm(
            documents, reference, interpreter=args.interpreter
        ),
        "differential.med1250.scorer_agreement": scorer_agreement_arm(documents, systems),
        "differential.med1250.harness_ceiling": harness_ceiling_arm(documents, systems),
        "differential.med1250.specification": specification_arm(documents, systems),
    }
    if args.interpreter:
        entries["differential.med1250.reference_output_mutations"] = reference_mutation_arm(
            args.interpreter, reference
        )
    for entry in entries.values():
        entry["measured_on"] = str(date.today())
    print(render(entries))
    if args.save:
        print(f"\nsaved {len(entries)} run(s) to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
