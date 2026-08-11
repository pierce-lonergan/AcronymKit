#!/usr/bin/env python3
"""Governed-naming benchmarks: build cost, per-call latency, corpus throughput.

The governed subsystem is called across a process boundary by a schema-governance
pipeline that walks tens of thousands of database column names, so what matters
is the cost of one call and the cost of a corpus — not the cost of a warm loop
over one string. These are the numbers ``docs/`` and ``README.md`` may cite about
that subsystem, so they are recorded into ``bench/results.json`` and nowhere
else.

Two corpora, and they are not comparable to each other
------------------------------------------------------
Real schemas repeat tokens enormously: every table has an id, a date and a code
column, and the fixture corpus resolves 640 token occurrences out of 117 distinct
tokens. Anything memoised per token therefore looks very good on a real corpus
and does nothing at all on a corpus of one-off tokens. Publishing only the first
would be a flattering measurement, so both are run and both are recorded:

``schema``
    Identifiers assembled from the fixture corpus's own token pool, sampled with
    replacement so the token-frequency distribution is the fixture's. Every
    *name* is distinct — a schema does not contain the same column twice — while
    the tokens repeat the way a governed vocabulary makes them repeat. Measured
    in steady state: one full warm-up pass, then a timed pass.

``novel``
    Identifiers whose every token is unique across the whole corpus and appears
    in no catalog row. Nothing can be reused between names, so this is the floor
    a per-token cache can offer and the ceiling on what its bookkeeping costs.
    The timed names are never seen during warm-up.

The two arms answer different questions and their numbers must not be read
against each other: a ``novel`` token is unknown to the catalog and takes the
passthrough path, which is a different amount of work from resolving a governed
row. Compare each arm against itself across a change; that is the comparison the
arms are built for.

**Every measurement gets a freshly built vocabulary.** A ``GovernedDictionary``
remembers what it has been asked, so a corpus benchmarked second on the same
object is not being asked the same question as the one benchmarked first — the
first draft of this runner shared one dictionary and reported a ``novel`` arm
that was partly served from the previous arm's answers, which is exactly the
flattering measurement the two arms exist to prevent. Building costs half a
millisecond and removes the whole class of problem.

What the latency figures include
--------------------------------
Each sample is one call, timed with :func:`time.perf_counter` around it, so a
sample carries roughly 0.1 us of timer overhead. That is under a percent of the
identifier-level calls and a few percent of ``expand_token``; it is present in
every run alike, and the throughput figures — one timer around a whole pass —
carry none of it and are the ones to quote for a pipeline.

Usage::

    python bench/run_governed.py                  # report, record nothing
    python bench/run_governed.py --save           # record into bench/results.json
    python bench/run_governed.py --only latency   # skip the throughput passes
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import string
import sys
import time
from pathlib import Path
from typing import Callable, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit.governed import (  # noqa: E402
    GovernedDictionary,
    expand_identifier,
    expand_token,
    is_compliant,
    to_physical_name,
)
from acronymkit.governed.tokenizer import split_identifier  # noqa: E402

#: The fixture catalog and corpus. Synthetic throughout — see the corpus README.
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "governed"

#: Identifiers per timed pass. Large enough that the median is stable and small
#: enough that a full run stays under a minute.
IDENTIFIERS = 2_000

#: Token-level samples, for the ``expand_token`` figures.
TOKENS = 20_000

#: Dictionary builds behind the build-cost median.
BUILD_REPEATS = 50

#: Columns in the schema this project's own throughput sentence talks about.
PROJECTED_COLUMNS = 50_000

#: The identifier the per-call figures were first quoted on: 17 tokens, 88
#: characters, every token governed. Pinned so that a single-name figure stays
#: comparable across releases even if the fixture corpus grows.
REFERENCE_IDENTIFIER = (
    "CUST_ACCT_PRIMARY_OWNER_PARTY_ID_VERIFICATION_STS_CD_SRC_SYSTEM_NM_LAST_CHG_TS_BATCH_NBR"
)


def build_dictionary() -> GovernedDictionary:
    """Assemble the fixture vocabulary the way a caller assembles a real one.

    The five fixture files are the five files a naming standard is kept in — the
    catalog, the allow-lists, the class words and the glossary — so the build
    measured here is the build a service performs at start-up.

    Returns:
        The Northwind Data Standards fixture vocabulary.
    """
    allow_list = json.loads((FIXTURES / "allowlist.json").read_text(encoding="utf-8"))
    class_words = json.loads((FIXTURES / "class_words.json").read_text(encoding="utf-8"))
    with (FIXTURES / "term_glossary.csv").open(encoding="utf-8", newline="") as handle:
        glossary = {row["logical_name"]: row["term_id"] for row in csv.DictReader(handle)}
    return GovernedDictionary.from_json(
        FIXTURES / "dictionary.json",
        approved_abbreviations=allow_list["approved_abbreviations"],
        common_keywords=allow_list["common_keywords"],
        short_full_words=allow_list["short_full_words"],
        class_words=class_words["abbreviations"],
        term_index=glossary,
    )


def fixture_corpus() -> tuple[str, ...]:
    """The 40 synthetic UPPER_SNAKE identifiers the fixtures ship."""
    text = (FIXTURES / "corpus_sample.txt").read_text(encoding="utf-8")
    return tuple(line.strip() for line in text.splitlines() if line.strip())


def schema_corpus(count: int, *, seed: int = 0) -> tuple[str, ...]:
    """Distinct identifiers with the fixture corpus's token-frequency profile.

    Tokens are drawn from the fixture pool *with replacement*, so a token that
    appears in a tenth of the fixture names appears in about a tenth of these;
    name lengths are drawn from the fixture's own length distribution. Seeded, so
    two runs benchmark the same corpus.

    Args:
        count: How many identifiers to produce.
        seed: The generator seed.

    Returns:
        ``count`` distinct identifiers.
    """
    names = fixture_corpus()
    splits = [split_identifier(name) for name in names]
    pool = [token for tokens in splits for token in tokens]
    lengths = [len(tokens) for tokens in splits]
    rng = random.Random(seed)

    corpus: list[str] = []
    seen: set[str] = set()
    while len(corpus) < count:
        candidate = "_".join(rng.choice(pool) for _ in range(rng.choice(lengths)))
        if candidate in seen:
            continue
        seen.add(candidate)
        corpus.append(candidate)
    return tuple(corpus)


def novel_corpus(
    count: int, dictionary: GovernedDictionary, *, tokens_per_name: int = 18
) -> tuple[str, ...]:
    """Identifiers whose every token is new, and is in no catalog row.

    Tokens are a fixed-width base-26 counter behind a ``Q`` prefix, which keeps
    them the shape of an UPPER_SNAKE column name — the tokenizer must do the same
    work on them as on a real one — while guaranteeing that no token recurs and
    that none collides with the vocabulary. The collision guard is asserted
    rather than assumed, because a corpus that quietly shared a token with the
    catalog would turn the cache's worst case into an average one.

    The counter restarts at every call, so two corpora built here hold the *same*
    tokens. That is deliberate and is safe only because each measurement is given
    a dictionary that has never seen any of them; it is the reason
    :func:`fresh_dictionary` exists.

    Args:
        count: How many identifiers to produce.
        dictionary: The vocabulary the tokens must be absent from.
        tokens_per_name: Tokens per identifier; the fixture median is 18.

    Returns:
        ``count`` identifiers, sharing no token with each other or the catalog.

    Raises:
        AssertionError: If a generated token turns out to be in the vocabulary.
    """
    letters = string.ascii_uppercase
    corpus: list[str] = []
    index = 0
    for _ in range(count):
        tokens: list[str] = []
        for _ in range(tokens_per_name):
            digits = []
            value = index
            for _ in range(4):
                digits.append(letters[value % 26])
                value //= 26
            token = "Q" + "".join(reversed(digits))
            assert token not in dictionary, f"{token} collides with the fixture catalog"
            tokens.append(token)
            index += 1
        corpus.append("_".join(tokens))
    return tuple(corpus)


#: A verb bound to a vocabulary: what :func:`latency` and :func:`throughput`
#: time. The vocabulary is supplied by the caller so that each measurement can be
#: handed a fresh one; see the module docstring.
Verb = Callable[[GovernedDictionary], Callable[[str], object]]


def fresh_dictionary() -> GovernedDictionary:
    """A vocabulary that has answered nothing yet.

    Equal in content to every other one this module builds and equal to none of
    them in what it remembers, which is the property a measurement needs.

    Returns:
        A new, unused fixture vocabulary.
    """
    return build_dictionary()


def latency(verb: Verb, timed: Sequence[str], warm: Sequence[str]) -> dict[str, float]:
    """Per-call microseconds over a sequence of inputs, on an unused vocabulary.

    Args:
        verb: Builds the one-argument call from the vocabulary it is given.
        timed: The inputs to time, one sample each.
        warm: Inputs run first and discarded, so the figures describe a warm
            interpreter — and, for the ``schema`` arm, a warm cache. Must share
            nothing with ``timed`` when the point of the arm is a cold cache.

    Returns:
        ``min``, ``median``, ``p95`` and the sample count. Dispersion is included
        because a single figure with no spread is not a measurement.
    """
    call = verb(fresh_dictionary())
    for item in warm:
        call(item)

    samples = []
    for item in timed:
        started = time.perf_counter()
        call(item)
        samples.append((time.perf_counter() - started) * 1e6)
    samples.sort()
    return {
        "min": round(samples[0], 2),
        "median": round(statistics.median(samples), 2),
        "p95": round(samples[int(len(samples) * 0.95)], 2),
        "iterations": len(samples),
    }


def throughput(verb: Verb, timed: Sequence[str], warm: Sequence[str]) -> dict[str, float]:
    """Identifiers per second over one pass, with a single timer around it.

    Args:
        verb: Builds the one-argument call from the vocabulary it is given.
        timed: The corpus to time.
        warm: The corpus to run first and discard.

    Returns:
        The rate, the elapsed seconds and the projection onto a
        :data:`PROJECTED_COLUMNS`-column schema.
    """
    call = verb(fresh_dictionary())
    for item in warm:
        call(item)
    started = time.perf_counter()
    for item in timed:
        call(item)
    elapsed = time.perf_counter() - started
    rate = len(timed) / elapsed
    return {
        "identifiers_per_second": round(rate),
        "elapsed_seconds": round(elapsed, 3),
        "identifiers": len(timed),
        "projected_seconds": round(PROJECTED_COLUMNS / rate, 2),
    }


def build_milliseconds(repeats: int = BUILD_REPEATS) -> dict[str, float]:
    """Cost of assembling the fixture vocabulary, in milliseconds.

    The five fixture files are read once and parsed once, outside the timer, so
    what is measured is indexing rather than disk.

    Args:
        repeats: Builds behind the median.

    Returns:
        ``min``, ``median`` and ``p95`` milliseconds, plus the row count.
    """
    prepared = build_dictionary()  # warm the JSON parse and the pydantic schemas
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        build_dictionary()
        samples.append((time.perf_counter() - started) * 1000)
    samples.sort()
    return {
        "min": round(samples[0], 3),
        "median": round(statistics.median(samples), 3),
        "p95": round(samples[int(len(samples) * 0.95)], 3),
        "entries": len(prepared),
        "iterations": repeats,
    }


def token_stream(corpus: Sequence[str], count: int) -> tuple[str, ...]:
    """Flatten a corpus into ``count`` tokens, cycling if it is short."""
    tokens = [token for name in corpus for token in split_identifier(name)]
    if not tokens:
        return ()
    return tuple(tokens[index % len(tokens)] for index in range(count))


def _row(label: str, measured: dict[str, float]) -> str:
    """Render one latency row for the console."""
    return (
        f"{label:<34}{measured['median']:9.2f} us median "
        f"(min {measured['min']:.2f}, p95 {measured['p95']:.2f})"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument(
        "--only",
        choices=("all", "build", "latency", "throughput"),
        default="all",
        help=(
            "restrict the run to one section. A change to the build path cannot move a "
            "per-call figure, and re-recording one it did not move republishes run-to-run "
            "noise as a result -- which is the size of difference this project reverts "
            "changes for."
        ),
    )
    parser.add_argument(
        "--identifiers",
        type=int,
        default=IDENTIFIERS,
        help=f"identifiers per timed pass (default {IDENTIFIERS})",
    )
    args = parser.parse_args(argv)

    entries: dict[str, dict] = {}
    dictionary = build_dictionary()

    if args.only in ("all", "build"):
        built = build_milliseconds()
        print(f"{'dictionary build':<34}{built['median']:9.3f} ms median ({built['entries']} rows)")
        entries["governed.build"] = built

    schema = schema_corpus(args.identifiers)
    # The novel arm needs names for warm-up that are never timed: nothing may be
    # reused between the two halves, or the timed pass would be measuring hits.
    warm_count = min(200, args.identifiers)
    novel = novel_corpus(args.identifiers + warm_count, dictionary)
    novel_warm, novel_timed = novel[:warm_count], novel[warm_count:]

    schema_tokens = token_stream(schema, TOKENS)
    novel_tokens = token_stream(novel_corpus(TOKENS // 18 + 2, dictionary), TOKENS)
    novel_token_warm = token_stream(schema, 2_000)

    if args.only in ("all", "latency", "throughput"):
        # Built on a throwaway vocabulary: expanding a name teaches the
        # dictionary that name's tokens, and the corpora built here are inputs to
        # measurements that must start from a vocabulary taught nothing.
        scratch = fresh_dictionary()
        phrases = tuple(expand_identifier(name, scratch).phrase for name in schema)
        novel_phrases = tuple(expand_identifier(name, scratch).phrase for name in novel_timed)

    if args.only in ("all", "latency"):
        measured = {
            "governed.split_identifier": latency(
                lambda _: split_identifier, schema, schema[: len(schema) // 4]
            ),
            "governed.expand_token": latency(
                lambda catalog: lambda token: expand_token(token, catalog),
                schema_tokens,
                schema_tokens[:2_000],
            ),
            "governed.expand_token_novel": latency(
                lambda catalog: lambda token: expand_token(token, catalog),
                novel_tokens,
                novel_token_warm,
            ),
            "governed.expand_identifier": latency(
                lambda catalog: lambda name: expand_identifier(name, catalog), schema, schema
            ),
            "governed.expand_identifier_novel": latency(
                lambda catalog: lambda name: expand_identifier(name, catalog),
                novel_timed,
                novel_warm,
            ),
            "governed.is_compliant": latency(
                lambda catalog: lambda name: is_compliant(name, catalog), schema, schema
            ),
            "governed.is_compliant_novel": latency(
                lambda catalog: lambda name: is_compliant(name, catalog), novel_timed, novel_warm
            ),
            "governed.to_physical_name": latency(
                lambda catalog: lambda phrase: to_physical_name(phrase, catalog), phrases, phrases
            ),
            "governed.to_physical_name_novel": latency(
                lambda catalog: lambda phrase: to_physical_name(phrase, catalog),
                novel_phrases[warm_count:],
                novel_phrases[:warm_count],
            ),
            "governed.reference_identifier": latency(
                lambda catalog: lambda name: expand_identifier(name, catalog),
                (REFERENCE_IDENTIFIER,) * 1_000,
                (REFERENCE_IDENTIFIER,) * 200,
            ),
        }
        for run_id, figures in measured.items():
            print(_row(run_id.replace("governed.", ""), figures))
            corpus = "novel" if run_id.endswith("_novel") else "schema"
            entries[run_id] = {**figures, "corpus": corpus}

    if args.only in ("all", "throughput"):

        def expand(catalog: GovernedDictionary) -> Callable[[str], object]:
            return lambda item: expand_identifier(item, catalog)

        hot = throughput(expand, schema, schema)
        cold = throughput(expand, novel_timed, novel_warm)
        print(
            f"{'throughput, schema':<34}{hot['identifiers_per_second']:9,} identifiers/s "
            f"({PROJECTED_COLUMNS:,} columns in {hot['projected_seconds']} s)"
        )
        print(
            f"{'throughput, novel':<34}{cold['identifiers_per_second']:9,} identifiers/s "
            f"({PROJECTED_COLUMNS:,} columns in {cold['projected_seconds']} s)"
        )
        entries["governed.throughput"] = {**hot, "corpus": "schema"}
        entries["governed.throughput_novel"] = {**cold, "corpus": "novel"}

    if args.save:
        from run_extraction import save_results

        print(f"saved {len(entries)} run(s) to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
