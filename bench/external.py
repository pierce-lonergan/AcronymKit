#!/usr/bin/env python3
"""Run a competing extractor and emit predictions as JSON.

Executed by a *foreign* interpreter, not the project's. Two of the baselines
cannot run in the same process as the benchmark:

* ``pyab3p`` publishes wheels only up to CPython 3.12;
* ``scispacy`` declares ``requires-python <3.13``.

Rather than pin the whole project to an older interpreter, the harness shells
out to whichever interpreter has the baseline installed and reads JSON back.
That also isolates each baseline's dependency tree, so a heavy competitor cannot
perturb the measurement of a light one.

This module imports only the standard library plus ``bench.corpora`` (itself
stdlib-only), so it loads cleanly under an interpreter that has never heard of
``acronymkit``.

Usage::

    <other-python> bench/external.py --system pyab3p --corpus med1250
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import corpora


def predict_abbreviations(texts: Sequence[str]) -> list[list[tuple[str, str]]]:
    """``abbreviations`` — a pure-Python Schwartz & Hearst implementation."""
    from abbreviations import schwartz_hearst

    results = []
    for text in texts:
        pairs = schwartz_hearst.extract_abbreviation_definition_pairs(doc_text=text)
        results.append([(short, long_form) for short, long_form in pairs.items()])
    return results


def predict_abbreviation_extractor(texts: Sequence[str]) -> list[list[tuple[str, str]]]:
    """``abbreviation-extractor`` — Rust implementation with Python bindings."""
    import abbreviation_extractor as extractor

    results = []
    for text in texts:
        found = extractor.extract_abbreviation_definition_pairs(text)
        results.append([(item.abbreviation, item.definition) for item in found])
    return results


def predict_pyab3p(texts: Sequence[str]) -> list[list[tuple[str, str]]]:
    """``pyab3p`` — bindings around the original NLM Ab3P C++ implementation.

    Ab3P was developed by the NLM against this very corpus, so its numbers here
    carry a home-advantage that a like-for-like reading should acknowledge.
    """
    import pyab3p

    engine = pyab3p.Ab3p()
    results = []
    for text in texts:
        results.append([(item.short_form, item.long_form) for item in engine.get_abbrs(text)])
    return results


def predict_scispacy(texts: Sequence[str]) -> list[list[tuple[str, str]]]:
    """``scispacy`` — the de facto Python baseline, behind a spaCy pipeline."""
    import spacy
    from scispacy.abbreviation import AbbreviationDetector  # noqa: F401

    try:
        nlp = spacy.load("en_core_sci_sm", disable=["ner", "lemmatizer", "tagger"])
    except OSError:
        nlp = spacy.blank("en")
    if "abbreviation_detector" not in nlp.pipe_names:
        nlp.add_pipe("abbreviation_detector")

    results = []
    for doc in nlp.pipe(texts, batch_size=64):
        results.append([(str(a), str(a._.long_form)) for a in doc._.abbreviations])
    return results


PREDICTORS = {
    "abbreviations": predict_abbreviations,
    "abbreviation_extractor": predict_abbreviation_extractor,
    "pyab3p": predict_pyab3p,
    "scispacy": predict_scispacy,
}


def _import_seconds(system: str) -> float:
    """Cost of importing this baseline in a cold process, in seconds."""
    modules = {
        "abbreviations": "abbreviations.schwartz_hearst",
        "abbreviation_extractor": "abbreviation_extractor",
        "pyab3p": "pyab3p",
        "scispacy": "scispacy.abbreviation",
    }
    started = time.perf_counter()
    __import__(modules[system])
    return time.perf_counter() - started


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Emit ``{uid: [[short, long], ...]}`` plus timings, as JSON on stdout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", required=True, choices=sorted(PREDICTORS))
    parser.add_argument("--corpus", default="med1250")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)

    documents = corpora.load(args.corpus)
    if args.limit:
        documents = documents[: args.limit]

    import_seconds = _import_seconds(args.system)
    texts = [document.text for document in documents]

    started = time.perf_counter()
    predicted = PREDICTORS[args.system](texts)
    elapsed = time.perf_counter() - started

    payload = {
        "system": args.system,
        "interpreter": sys.version.split()[0],
        "elapsed_seconds": elapsed,
        "import_seconds": import_seconds,
        "predictions": {
            document.uid: [list(pair) for pair in pairs]
            for document, pairs in zip(documents, predicted)
        },
    }
    json.dump(payload, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
