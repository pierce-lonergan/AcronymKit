#!/usr/bin/env python3
"""The catalog-gap report on real schema corpora, plus the controls it needs to be read.

:func:`acronymkit.governed.gap.catalog_gap` claims something exact: that a
label carrying a character its identifier does not is unreachable by **any**
catalog-free method, and that the tokens responsible are a finite ranked list.
This runner points that at two real identifier/label populations and publishes
the shape, with four controls beside it, because the census on its own is
readable in a way that flatters it.

The arms
--------
``catalog_gap.socrata.census``
    The report as it ships, on the real Socrata portal population. Every filter
    off.

``catalog_gap.socrata.letters_min2``
    The same population with the two mechanical filters on
    (``min_token_length=2``, ``require_letter=True``). **This is the control the
    census needs**, because the census's ranked head is dominated by
    single-character fragments of machine-generated identifiers and the filtered
    arm prices what removing them costs: a cleaner head, and a much larger share
    of unreachable columns with no work item attached to them at all.

``catalog_gap.sec_xbrl.census``
    The contrast arm. SEC XBRL tags are largely produced from their labels by
    the LC3 convention -- the label with its spaces removed -- so a much larger
    share of pairs shares a character stream than on a portal catalog, and the
    report should find a correspondingly smaller gap. **It is a contrast and not
    a negative control, and the difference is worth stating because the first
    draft of this docstring got it wrong.** "Almost no gap" is what LC3 predicts
    and it is not what the run says: ``reachable_columns`` over
    ``labelled_columns`` is what the two corpora differ on, and the residue here
    is large enough that anyone reading this arm as a zero baseline would be
    reading the adjective rather than the number.

``catalog_gap.socrata.word_list_control``
    The **rejected** design, kept rather than deleted. Deciding from the token
    alone whether it is a word, against the English word list this package
    ships, is the obvious way to avoid asking a caller for labels. It is wrong
    about most of the tokens it flags, and the entry carries the rate and the
    verdict so that the next person to have the idea meets the measurement
    rather than the idea.

``catalog_gap.socrata.label_word_rule``
    Unicode-aware label words against the ASCII-only rule ``tools/byoc_eval.py``
    scores with. The ASCII rule splits ``Número`` into ``n`` and ``mero`` and
    then finds both tokens present, so it reports columns as fully attributed
    that are not. The distance between the two rules is saved rather than
    asserted.

``catalog_gap.socrata.byoc_agreement``
    The composition claim, checked rather than stated: over one CSV,
    ``catalog_gap``'s ``columns`` and ``unreachable_columns`` must equal
    ``tools/byoc_eval.py``'s ``pairs_scored`` and ``pairs_where_label_expands``.
    Both figures are recomputed here from that module's own ``stream_key`` and
    its own de-duplication rule, so the agreement is a comparison of two
    implementations rather than a restatement of one.

``catalog_gap.socrata.identity``
    R19. The gap report is additive -- it calls the shipped verbs and changes
    none of them -- and "additive" is a claim about bytes, not a feeling. This
    arm hashes ``expand_identifier(...).to_json()`` over every one of the
    corpus's identifiers, so the same command run on a tree with the module
    removed produces the same hash or the claim is false. What it cannot do is
    prove the *absence* of a change it was not pointed at: it covers
    ``expand_identifier`` over one corpus under one catalog, which is where a
    provenance regression would land, and not every verb in the subsystem.

R17: a performance number without a work count is a null result
---------------------------------------------------------------
Every arm saves the counts the report itself carries -- tokenizer passes, label
word-sets built, catalog lookups performed, token occurrences, greedy
set-difference evaluations -- beside its figures. The zero on
``catalog_lookups`` is the load-bearing one: it is what "this report needs no
catalog" means in work rather than in prose, and a later change that quietly
started consulting one would show up there before it showed up anywhere else.

R18: counts are gated, wall-clock is a note
-------------------------------------------
Every count here is a property of the code and is identical on two machines. The
elapsed seconds are a property of this runner, are saved under ``elapsed_note``
with the machine named, and are not for citing.

Usage::

    python bench/run_catalog_gap.py                  # report, record nothing
    python bench/run_catalog_gap.py --save           # record into bench/results.json
    python bench/run_catalog_gap.py --only census    # the two census arms alone
    python bench/run_catalog_gap.py --limit 20000    # a short pass, for a smoke test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit.governed import GovernedDictionary, expand_identifier  # noqa: E402
from acronymkit.governed.gap import catalog_gap, label_words, stream_key  # noqa: E402
from acronymkit.governed.tokenizer import split_identifier  # noqa: E402
from acronymkit.lexicon import Lexicon  # noqa: E402

#: The governed-gold cache the two real corpora are read out of.
GOVERNED_GOLD_CACHE = REPO_ROOT / "data" / "governed_gold"

#: Which cache file each corpus is read from. Named rather than globbed, for the
#: reason ``bench/corpora.py`` refuses to choose between two snapshots of a live
#: catalog: two files are two populations, not two copies.
SNAPSHOTS = {
    "socrata": "socrata_80pages_v2.json",
    "sec_xbrl": "sec_xbrl_2025q1.json",
}

#: ``tools/byoc_eval.py``'s label-word rule, reproduced here so the two can be
#: scored against each other. ASCII-only on purpose: that is what it is.
_ASCII_RUN = re.compile(r"[^0-9a-z]+")

#: Ranked rows every arm computes, and the budget the greedy control is given.
HEAD = 20


def environment() -> str:
    """One-line description of the machine, for the results table."""
    return f"Python {platform.python_version()} on {platform.system()} {platform.machine()}"


def machine_note() -> str:
    """The machine named, for the unarmed wall-clock note R18 requires."""
    processor = platform.processor() or platform.machine()
    return f"{environment()}; {processor}"


def read_schema(name: str, limit: int = 0) -> tuple[list[tuple[str, str]], str, str]:
    """Read one identifier/label population out of the governed-gold cache.

    Rows are returned **as they occur** and are not de-duplicated here:
    de-duplication is the report's own documented rule and doing it twice, in two
    places, is how the two stop agreeing.

    Args:
        name: ``"socrata"`` or ``"sec_xbrl"``.
        limit: Cap on rows read; ``0`` reads the whole cache.

    Returns:
        The rows, the cache file name, and the fetch date.

    Raises:
        SystemExit: If the corpus is unknown or the cache file is absent.
    """
    if name not in SNAPSHOTS:
        raise SystemExit(f"unknown corpus {name!r}; known: {sorted(SNAPSHOTS)}")
    source = GOVERNED_GOLD_CACHE / SNAPSHOTS[name]
    if not source.is_file():
        raise SystemExit(f"missing {source}\nRun: python bench/run_governed_gold.py --only {name}")
    envelope = json.loads(source.read_text(encoding="utf-8"))
    payload = envelope.get("payload")
    if not isinstance(payload, list):
        raise SystemExit(f"{source} is not a run_governed_gold cache envelope")
    rows = [
        (str(row[0]), str(row[1]))
        for row in payload
        if isinstance(row, list) and len(row) >= 2 and str(row[0]).strip()
    ]
    if limit:
        rows = rows[:limit]
    return rows, source.name, str(envelope.get("fetched_on") or "unknown")


def census(
    corpus: str,
    rows: Sequence[tuple[str, str]],
    source: str,
    fetched_on: str,
    *,
    min_token_length: int = 1,
    require_letter: bool = False,
) -> dict[str, Any]:
    """Run the shipped report over one population and render it as a results entry.

    Args:
        corpus: The corpus name, saved on the entry.
        rows: ``(identifier, label)`` rows in cache order.
        source: The cache file read.
        fetched_on: The fetch date carried through from the envelope.
        min_token_length: Passed to :func:`~acronymkit.governed.gap.catalog_gap`.
        require_letter: Passed to :func:`~acronymkit.governed.gap.catalog_gap`.

    Returns:
        The entry, with the report's own work counts on it.
    """
    started = time.perf_counter()
    gap = catalog_gap(
        rows,
        head=HEAD,
        min_token_length=min_token_length,
        require_letter=require_letter,
    )
    elapsed = time.perf_counter() - started
    entry = gap.to_dict()
    entry.pop("head", None)
    entry.update(
        {
            "corpus": corpus,
            "source": source,
            "fetched_on": fetched_on,
            "rows_read": len(rows),
            "head_size": len(gap.head),
            "head_tokens": [row.token for row in gap.head],
            "head_columns_each": [row.columns for row in gap.head],
            "unattributed_pct": gap.unattributed_pct,
            "work_list_tokens": gap.work_list_tokens,
            "elapsed_note": f"{elapsed:.2f} s on {machine_note()}; NOT a gated figure",
        }
    )
    return entry


def word_list_control(rows: Sequence[tuple[str, str]]) -> dict[str, Any]:
    """Score the label-free classifier this module rejected, and say why.

    The classifier: a token is unreachable if it is not a word in the bundled
    English lexicon. The ground truth available without a glossary is weak but it
    is one-sided and that is enough to refute the classifier: if the token
    appears **verbatim as a whole word** in a label of a column it occurs in,
    then it was reachable, and calling it unreachable was wrong. Nothing here
    can show the classifier is *right* about the rest, which is stated rather
    than glossed: the arm refutes and does not confirm.

    Args:
        rows: ``(identifier, label)`` rows in cache order.

    Returns:
        The entry, carrying the false-positive rate and the verdict.
    """
    lexicon = Lexicon.load()
    seen: set[str] = set()
    tokens: set[str] = set()
    appears: set[str] = set()
    lookups = 0
    for identifier, label in rows:
        identifier = identifier.strip()
        if not identifier or identifier.casefold() in seen:
            continue
        seen.add(identifier.casefold())
        words = label_words(label)
        for token in split_identifier(identifier):
            folded = token.casefold()
            tokens.add(folded)
            if folded in words:
                appears.add(folded)
    letterful = {token for token in tokens if any(char.isalpha() for char in token)}
    called: set[str] = set()
    for token in letterful:
        lookups += 1
        if not lexicon.contains(token):
            called.add(token)
    false_positives = called & appears
    examples = sorted(false_positives)
    return {
        "corpus": "socrata",
        "verdict": "REJECTED",
        "columns": len(seen),
        "distinct_tokens": len(tokens),
        "letter_bearing_tokens": len(letterful),
        "lexicon_lookups": lookups,
        "called_unreachable": len(called),
        "false_positives": len(false_positives),
        "false_positive_pct": round(100.0 * len(false_positives) / len(called), 2)
        if called
        else 0.0,
        "false_positive_examples": examples[:12],
        "ground_truth": (
            "the token appears verbatim as a whole label word somewhere it occurs, so it was "
            "reachable. One-sided: this arm can refute the classifier and cannot confirm it."
        ),
        "why_rejected": (
            "the causes are structural rather than tunable -- other languages, ordinals, domain "
            "vocabulary and concatenations -- so no English word list stops being wrong about "
            "them. acronymkit.governed.gap therefore imports no lexicon and requires labels."
        ),
    }


def label_word_rule(rows: Sequence[tuple[str, str]]) -> dict[str, Any]:
    """Score the Unicode label-word rule against ``tools/byoc_eval.py``'s ASCII one.

    Both rules are run over the same de-duplicated population in one pass, so the
    difference is the rule and nothing else.

    Args:
        rows: ``(identifier, label)`` rows in cache order.

    Returns:
        The entry, with the two attribution counts and the distance between them.
    """
    seen: set[str] = set()
    unreachable = 0
    unicode_unattributed = 0
    ascii_unattributed = 0
    unicode_tokens: set[str] = set()
    ascii_tokens: set[str] = set()
    for identifier, label in rows:
        identifier, label = identifier.strip(), label.strip()
        if not identifier or not label or identifier.casefold() in seen:
            continue
        seen.add(identifier.casefold())
        if stream_key(identifier) == stream_key(label):
            continue
        unreachable += 1
        folded = [token.casefold() for token in split_identifier(identifier)]
        unicode_words = label_words(label)
        ascii_words = {word for word in _ASCII_RUN.split(label.casefold()) if word}
        unicode_missing = [token for token in folded if token not in unicode_words]
        ascii_missing = [token for token in folded if token not in ascii_words]
        if unicode_missing:
            unicode_tokens.update(unicode_missing)
        else:
            unicode_unattributed += 1
        if ascii_missing:
            ascii_tokens.update(ascii_missing)
        else:
            ascii_unattributed += 1
    unicode_pct = round(100.0 * unicode_unattributed / unreachable, 2) if unreachable else 0.0
    ascii_pct = round(100.0 * ascii_unattributed / unreachable, 2) if unreachable else 0.0
    return {
        "corpus": "socrata",
        "columns": len(seen),
        "unreachable_columns": unreachable,
        "unicode_unattributed_columns": unicode_unattributed,
        "unicode_unattributed_pct": unicode_pct,
        "unicode_unreachable_tokens": len(unicode_tokens),
        "ascii_unattributed_columns": ascii_unattributed,
        "ascii_unattributed_pct": ascii_pct,
        "ascii_unreachable_tokens": len(ascii_tokens),
        "rule_difference_points": round(ascii_pct - unicode_pct, 2),
        "shipped_rule": "unicode",
        "note": (
            "the ASCII rule splits an accented label word into fragments and then finds the "
            "identifier's fragments present, so it attributes fewer columns to a token and "
            "reports more of them as 'the label says more than the identifier'."
        ),
    }


def byoc_agreement(rows: Sequence[tuple[str, str]]) -> dict[str, Any]:
    """Check the composition claim against ``tools/byoc_eval.py``'s own functions.

    ``catalog_gap`` says it puts the same numbers under the same population as
    the bring-your-own-catalog kit. That is a claim about two implementations and
    it is checked by running both, not by reading both.

    Args:
        rows: ``(identifier, label)`` rows in cache order.

    Returns:
        The entry, with both sides and whether they agree.

    Raises:
        SystemExit: If ``tools/byoc_eval.py`` cannot be imported.
    """
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    try:
        import byoc_eval
    except ImportError as exc:  # pragma: no cover - the kit is committed
        raise SystemExit(f"cannot import tools/byoc_eval.py: {exc}") from exc

    seen: set[str] = set()
    byoc_scored = 0
    byoc_expands = 0
    for identifier, label in rows:
        identifier, label = identifier.strip(), label.strip()
        if not identifier or not label or identifier.casefold() in seen:
            continue
        seen.add(identifier.casefold())
        byoc_scored += 1
        if byoc_eval.stream_key(identifier) != byoc_eval.stream_key(label):
            byoc_expands += 1
    gap = catalog_gap(rows, head=0)
    return {
        "corpus": "socrata",
        "gap_columns": gap.labelled_columns,
        "byoc_pairs_scored": byoc_scored,
        "columns_agree": gap.labelled_columns == byoc_scored,
        "gap_unreachable_columns": gap.unreachable_columns,
        "byoc_pairs_where_label_expands": byoc_expands,
        "unreachable_agrees": gap.unreachable_columns == byoc_expands,
        "note": (
            "byoc_eval rejects a row with an empty label; catalog_gap admits it, counts it as "
            "unlabelled and does not classify it. The comparison is therefore against "
            "labelled_columns, and the two stream_key implementations are compared directly."
        ),
    }


def _digest(identifiers: Sequence[str], catalog: GovernedDictionary) -> str:
    """SHA-256 over ``to_json()`` of every expansion, newline separated, in order."""
    digest = hashlib.sha256()
    for identifier in identifiers:
        digest.update(expand_identifier(identifier, catalog).to_json().encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def identity(rows: Sequence[tuple[str, str]]) -> dict[str, Any]:
    """R19: hash the shipped expansion's whole output over the corpus, with a positive control.

    The catalog-gap report adds a module and changes no verb. That is a claim
    about bytes: ``sha256_empty_catalog``, taken over ``to_json()`` of every
    record including its provenance, is the same on a tree without the module and
    on a tree with it, or the claim is false.

    **A digest that could not detect a small change would be a green that means
    nothing**, so the arm carries its own positive control rather than asserting
    sensitivity. ``sentinel_token`` is the alphabetically first token of more than
    six letters that occurs in **exactly one** identifier in the whole corpus; a
    catalog holding that one row changes one ``long``, one ``entry_id``, one
    ``source`` and one ``confidence``, in one record out of
    ``records``. ``digests_differ`` is what that does to the hash.

    Args:
        rows: ``(identifier, label)`` rows in cache order.

    Returns:
        The entry, with both digests, the sentinel and whether they differ.
    """
    identifiers = [identifier for identifier, _label in rows]
    occurrences: dict[str, int] = {}
    for identifier in identifiers:
        for token in set(split_identifier(identifier)):
            key = token.upper()
            occurrences[key] = occurrences.get(key, 0) + 1
    singletons = sorted(
        token
        for token, count in occurrences.items()
        if count == 1 and token.isalpha() and len(token) > 6
    )
    sentinel = singletons[0] if singletons else ""
    base = _digest(identifiers, GovernedDictionary({}))
    control = (
        _digest(identifiers, GovernedDictionary.from_mapping({sentinel: "Sentinel Word"}))
        if sentinel
        else base
    )
    return {
        "corpus": "socrata",
        "records": len(identifiers),
        "sha256_empty_catalog": base,
        "sentinel_token": sentinel,
        "sentinel_identifiers": 1 if sentinel else 0,
        "sha256_one_entry_catalog": control,
        "digests_differ": base != control,
        "what_is_hashed": (
            "expand_identifier(identifier, GovernedDictionary({})).to_json() for every "
            "identifier in cache order, newline separated -- phrase, every token record, "
            "entry_id, source, confidence, beat, class_word, is_fully_known and unaccounted."
        ),
    }


def render(run_id: str, entry: dict[str, Any]) -> list[str]:
    """Render one entry as the lines this runner prints."""
    lines = [run_id]
    for key, value in entry.items():
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value[:12]) + ("…" if len(value) > 12 else "")
        text = f"{value:,}" if isinstance(value, int) and not isinstance(value, bool) else value
        lines.append(f"  {key:<34} {text}")
    return lines


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the arms and optionally record them.

    Args:
        argv: Command-line arguments, or ``None`` for ``sys.argv[1:]``.

    Returns:
        Process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--only",
        choices=("all", "census", "controls", "identity"),
        default="all",
        help="which arms to run",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="cap each corpus at this many rows (0 = the whole corpus)",
    )
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    args = parser.parse_args(argv)

    entries: dict[str, dict[str, Any]] = {}
    socrata, socrata_source, socrata_fetched = read_schema("socrata", args.limit)

    if args.only in ("all", "census"):
        entries["catalog_gap.socrata.census"] = census(
            "socrata", socrata, socrata_source, socrata_fetched
        )
        entries["catalog_gap.socrata.letters_min2"] = census(
            "socrata",
            socrata,
            socrata_source,
            socrata_fetched,
            min_token_length=2,
            require_letter=True,
        )
        sec, sec_source, sec_fetched = read_schema("sec_xbrl", args.limit)
        entries["catalog_gap.sec_xbrl.census"] = census("sec_xbrl", sec, sec_source, sec_fetched)

    if args.only in ("all", "controls"):
        entries["catalog_gap.socrata.word_list_control"] = word_list_control(socrata)
        entries["catalog_gap.socrata.label_word_rule"] = label_word_rule(socrata)
        entries["catalog_gap.socrata.byoc_agreement"] = byoc_agreement(socrata)

    if args.only in ("all", "identity"):
        entries["catalog_gap.socrata.identity"] = identity(socrata)

    for run_id, entry in entries.items():
        print("\n".join(render(run_id, entry)))
        print()

    if args.save:
        from run_extraction import save_results

        print(f"saved {len(entries)} run(s) to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
