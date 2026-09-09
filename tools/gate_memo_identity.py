#!/usr/bin/env python3
"""Assert the governed memo changes no answer: forced on, forced off, byte for byte.

Operating rule 19: an optimisation is proven **behaviour-identical**, not
benchmarked-equal. A memo that changes one ``entry_id`` in ten million is
catastrophic for a governance instrument and completely invisible to a
benchmark, which reports a rate and never looks at a field. So this gate times
nothing. It runs a corpus once per memo configuration and compares the **full
JSON rendering of every result** against the configuration with every level
turned off -- which carries ``entry_id``, ``source``, ``confidence``,
``class_word``, ``beat``, ``kind``, ``is_known``, ``is_fully_known`` and
``unaccounted`` as well as the phrase everybody looks at.

Why the phrase alone would not do
---------------------------------
``phrase`` is a join of ``long`` over the tokens. Every other provenance field
could be wrong while the phrase is right: an entry id carried over from a
different catalog row, a confidence memoised under one policy and served under
another, a ``beat`` tuple shared between two tokens that beat different things.
Two of the four memo levels are keyed by **caller input** rather than by the
vocabulary (``passed`` and ``identifiers``), which is exactly the shape where a
collision between two spellings would be invisible in the phrase and fatal in
the audit trail. So the comparison is ``to_json()``.

What "forced off" means, and why it is a real code path
-------------------------------------------------------
:func:`acronymkit.catalog.dictionary._set_memo_levels` makes
:meth:`GovernedDictionary._memo` hand out
:class:`~acronymkit.catalog.dictionary._NullMap` for a level that is off. That
map stores nothing and misses on every read. The per-token code is byte-identical
between the arms: it still does one ``get`` and one write and cannot tell which
map it holds. That matters because a "memo off" arm implemented as a second code
path would compare two implementations rather than one implementation against its
own cache, and the defect this gate is for lives in the cache.

Three ways this gate is kept capable of failing
-----------------------------------------------
A comparison of two arms that did the same thing is green for the wrong reason,
and `docs/GATES.md` exists because this project keeps shipping checks that cannot
fail where they run. So:

1. **The arms are proved to have differed.** Memo occupancy is read after each
   arm. A run where the memo-on arm remembered nothing, or the memo-off arm
   remembered something, is refused -- otherwise a bug that disabled memoisation
   entirely would make every arm trivially identical and this gate would go green
   on a library that had stopped caching.
2. **Each level is proved to have been reached.** Every level is turned off *on
   its own* as well as with the others, and a level left empty by the all-on arm
   is refused: a corpus that never fills ``passed`` says nothing about ``passed``.
   The exception is stated rather than waived silently -- an **empty** catalog
   can never fill ``resolved`` or ``expanded``, because neither map records that
   a token is unknown, so those two are required on the arms whose catalog has
   rows and required run-wide rather than per corpus. That exemption is itself
   a finding: it is the configuration every published governed figure is taken
   in, and in it the two vocabulary-keyed levels are inert by construction.
3. **The clear branch is proved to have executed.** The caller-input levels are
   run against a corpus large enough to fill and empty them, and the gate refuses
   a run in which neither cleared. The clear is where a memo is likeliest to
   serve a stale answer, and a corpus smaller than the limit never reaches it.

Two properties a diff of expansions cannot see, checked separately
------------------------------------------------------------------
``--only levels`` compares outputs. Two things that would be wrong are not
outputs at all, and both are properties the ``passed`` level created:

* a passthrough remembered under a policy that returns must never be served to a
  policy that raises -- ``UnknownPolicy.REJECT`` has to keep raising after a
  ``PASSTHROUGH_TITLECASE`` call has warmed the memo; and
* a call-scoped ``custom=`` overlay must never be served an answer computed
  without it, at either level.

Both run as ``--only properties`` and both are also part of the default run.

R17: the work count
-------------------
Every arm prints identifiers processed, distinct identifiers, token occurrences,
per-level memo occupancy and whether each caller-input level cleared. A gate that
got green because it stopped doing work looks exactly like one that got green
because the work was correct.

The corpora, and the one this cannot see
-----------------------------------------
The committed fixture vocabulary and a corpus generated from it always run: both
ship in the sdist and exist in every environment. The two real corpora under
``data/governed_gold/`` run **when they are present**, which on this project is a
developer machine and nothing else -- ``data/`` is fetched and never committed,
and no CI job fetches it. The gate names which arms ran, and its exit status does
not depend on the optional corpora being there, because a gate that fails for a
missing optional input is a gate people delete. **That is a real hole and it is
stated rather than hidden: in CI this gate has never seen a real schema.**

Usage::

    python tools/gate_memo_identity.py
    python tools/gate_memo_identity.py --limit 20000     # a shorter pass
    python tools/gate_memo_identity.py --only properties

Only the standard library and ``acronymkit`` itself are imported.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from acronymkit.catalog import (  # noqa: E402
    GovernedDictionary,
    NamingPolicy,
    expand_identifier,
)
from acronymkit.catalog import dictionary as dictionary_module  # noqa: E402
from acronymkit.catalog.enums import UnknownPolicy  # noqa: E402
from acronymkit.catalog.tokenizer import split_identifier  # noqa: E402
from acronymkit.exceptions import LexiconError  # noqa: E402

#: Printed on every refusal, so a demonstration of this gate failing is
#: attributable to the assertion rather than to the run. `docs/GATES.md` records
#: the marker with the mutation that produced it.
FAILURE_MARKER = "MEMO CHANGED AN ANSWER"

#: Where the fixture vocabulary lives. The same five files `bench/run_governed.py`
#: builds from, so this gate and that runner talk about one catalog.
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "governed"

#: The optional real corpora, named rather than globbed for the reason
#: `bench/corpora.py` gives: a runner must not silently pick between two
#: snapshots of a live catalog.
GOVERNED_GOLD = REPO_ROOT / "data" / "governed_gold"
SNAPSHOTS = {
    "socrata": "socrata_80pages_v2.json",
    "sec_xbrl": "sec_xbrl_2025q1.json",
}

#: Identifiers in the generated corpus. Larger than `_IDENTIFIER_MEMO_LIMIT` and
#: than `_MEMO_LIMIT` by enough that both caller-input levels fill and clear
#: several times; see the third bullet in the module docstring.
GENERATED_IDENTIFIERS = 30_000

#: The four levels, and the field of `_Memo` each one names.
LEVELS = ("resolved", "expanded", "passed", "identifiers")


def build_fixture_dictionary() -> GovernedDictionary:
    """Assemble the Northwind Data Standards fixture vocabulary.

    Returns:
        The fixture vocabulary.
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


def generated_corpus(count: int, *, seed: int = 0) -> Tuple[str, ...]:
    """Identifiers built from the fixture pool, with deliberate repetition.

    Three properties this corpus has to have, and none is accidental.

    It must contain tokens the fixture catalog answers for **and** tokens it does
    not, so ``expanded`` and ``passed`` both fill; and it must repeat identifiers,
    so ``identifiers`` fills. A corpus of distinct names would leave two of the
    four levels empty and the gate would pass without having tested them, which
    the occupancy check refuses.

    **And it must contain names that differ only in case.** That third property
    was added because the gate was measured without it and found blind: a probe
    that made the identifier memo read its key case-folded -- a one-word
    collision that would serve one caller another caller's ``identifier`` field
    -- fired on neither real corpus, because neither Socrata nor SEC XBRL happens
    to carry two names differing only in case. Both real corpora are still run,
    and the class they cannot reach is covered here.

    Args:
        count: How many identifiers to produce.
        seed: The generator seed. The corpus is a pure function of it.

    Returns:
        ``count`` identifiers, in occurrence order, not deduplicated.
    """
    text = (FIXTURES / "corpus_sample.txt").read_text(encoding="utf-8")
    names = [line.strip() for line in text.splitlines() if line.strip()]
    pool = [token for name in names for token in split_identifier(name)]
    rng = random.Random(seed)
    # Tokens no fixture catalog row can answer for, so `passed` fills too.
    strangers = [f"ZQ{index:04d}" for index in range(600)]
    distinct: List[str] = []
    while len(distinct) < max(1, count // 2):
        parts = [rng.choice(pool) for _ in range(rng.randint(1, 4))]
        if rng.random() < 0.5:
            parts.insert(rng.randrange(len(parts) + 1), rng.choice(strangers))
        distinct.append("_".join(parts))
    # The case-variant population: same characters, different spelling, which is
    # what a memo keyed on a folded key would collapse.
    distinct.extend(name.lower() for name in distinct[: max(1, len(distinct) // 10)])
    return tuple(rng.choice(distinct) for _ in range(count))


def read_snapshot(name: str) -> Optional[Tuple[str, ...]]:
    """Read one governed-gold cache file, or return ``None`` when it is absent.

    Args:
        name: ``"socrata"`` or ``"sec_xbrl"``.

    Returns:
        The identifiers in cache order, not deduplicated, or ``None``.
    """
    source = GOVERNED_GOLD / SNAPSHOTS[name]
    if not source.is_file():
        return None
    envelope = json.loads(source.read_text(encoding="utf-8"))
    payload = envelope.get("payload")
    if not isinstance(payload, list):
        return None
    return tuple(
        str(row[0]) for row in payload if isinstance(row, list) and row and str(row[0]).strip()
    )


def occupancy(catalog: GovernedDictionary, policy: NamingPolicy) -> Dict[str, int]:
    """Return how many answers each level of one dictionary's memo holds.

    Args:
        catalog: The dictionary the arm ran against.
        policy: The policy the arm ran under.

    Returns:
        Level name to entry count.
    """
    memo = catalog._memo(policy)
    return {level: len(getattr(memo, level)) for level in LEVELS}


def run_arm(
    identifiers: Sequence[str],
    factory: Callable[[], GovernedDictionary],
    policy: NamingPolicy,
    levels: Dict[str, bool],
) -> Tuple[List[str], Dict[str, int], Dict[str, int]]:
    """Expand a corpus under one memo configuration.

    The dictionary is built **after** the levels are set, because
    :func:`~acronymkit.catalog.dictionary._set_memo_levels` is documented as not
    retroactively emptying a memo that already exists.

    Args:
        identifiers: The corpus, in occurrence order.
        factory: Builds a fresh vocabulary.
        policy: The policy to expand under.
        levels: Which levels to turn on.

    Returns:
        The ``to_json()`` of every result, the memo occupancy after the pass, and
        how many times each caller-input level cleared.
    """
    restore = dictionary_module._set_memo_levels(**levels)
    try:
        catalog = factory()
        clears = {"passed": 0, "identifiers": 0}
        watched = {
            "passed": (dictionary_module._MEMO_LIMIT, "passed"),
            "identifiers": (dictionary_module._IDENTIFIER_MEMO_LIMIT, "identifiers"),
        }
        rendered: List[str] = []
        previous = dict.fromkeys(watched, 0)
        for identifier in identifiers:
            rendered.append(expand_identifier(identifier, catalog, policy).to_json())
            memo = catalog._memo(policy)
            for name, (_limit, field) in watched.items():
                size = len(getattr(memo, field))
                if size < previous[name]:
                    clears[name] += 1
                previous[name] = size
        return rendered, occupancy(catalog, policy), clears
    finally:
        dictionary_module._set_memo_levels(**restore)


def compare_corpus(
    label: str,
    identifiers: Sequence[str],
    factory: Callable[[], GovernedDictionary],
    reached: Dict[str, int],
) -> Tuple[List[str], List[str]]:
    """Run every memo configuration over one corpus and diff them.

    Args:
        label: The corpus name, for the report.
        identifiers: The corpus, in occurrence order.
        factory: Builds a fresh vocabulary.
        reached: Accumulator, level name to the largest occupancy any corpus in
            this run reached. Read by :func:`main` for the run-wide check.

    Returns:
        ``(problems, report lines)``.
    """
    problems: List[str] = []
    report: List[str] = []
    policy = NamingPolicy.governed_default()
    tokens = sum(len(split_identifier(name)) for name in identifiers)
    report.append(
        f"  {label}: {len(identifiers):,} identifiers, "
        f"{len(set(identifiers)):,} distinct, {tokens:,} token occurrences"
    )

    off = dict.fromkeys(LEVELS, False)
    reference, reference_occupancy, _ = run_arm(identifiers, factory, policy, off)
    if any(reference_occupancy.values()):
        problems.append(
            f"{FAILURE_MARKER}: the memo-off arm on {label} remembered "
            f"{reference_occupancy}, so the two arms are not what they claim to be "
            "and this comparison proves nothing."
        )

    on = dict.fromkeys(LEVELS, True)
    arms: List[Tuple[str, Dict[str, bool]]] = [("all levels on", on)]
    for level in LEVELS:
        arms.append((f"only {level} off", {**on, level: False}))

    for name, levels in arms:
        rendered, filled, clears = run_arm(identifiers, factory, policy, levels)
        mismatches = sum(1 for a, b in zip(reference, rendered) if a != b)
        first = next(
            (index for index, (a, b) in enumerate(zip(reference, rendered)) if a != b),
            None,
        )
        report.append(
            f"    {name:<22} occupancy {filled}  clears {clears}  "
            f"mismatches {mismatches:,} of {len(rendered):,}"
        )
        if mismatches:
            assert first is not None
            problems.append(
                f"{FAILURE_MARKER}: on {label}, '{name}' disagreed with the memo-off arm "
                f"on {mismatches:,} of {len(rendered):,} identifiers. First at index "
                f"{first} ({identifiers[first]!r}):\n"
                f"      memo off: {reference[first]}\n"
                f"      {name}: {rendered[first]}"
            )
        if levels is on:
            for level, size in filled.items():
                reached[level] = max(reached[level], size)
            # An empty catalog answers for nothing, so `resolved` and `expanded`
            # cannot fill there and their emptiness is a derivation rather than a
            # defect. `passed` and `identifiers` are keyed by caller input and
            # must fill on every corpus.
            required = LEVELS if len(factory()) else ("passed", "identifiers")
            empty = [level for level in required if filled[level] == 0]
            if empty:
                problems.append(
                    f"{FAILURE_MARKER}: on {label} the all-on arm left {empty} empty, so "
                    "this corpus never exercised those level(s) and the green above is "
                    "about a memo that did not run."
                )
            if not any(clears.values()):
                problems.append(
                    f"{FAILURE_MARKER}: on {label} neither caller-input level filled and "
                    "cleared, so the branch where a memo is likeliest to serve a stale "
                    "answer was never taken. Raise --limit or the corpus size."
                )
    return problems, report


def check_properties() -> Tuple[List[str], List[str]]:
    """Two correctness properties a diff of expansions cannot see.

    Returns:
        ``(problems, report lines)``.
    """
    problems: List[str] = []
    report: List[str] = []

    # 1. A passthrough remembered under a policy that returns must not be served
    #    to a policy that raises. `unknown` is a NamingPolicy field, so the two
    #    policies have separate memos; this asserts that rather than trusting it.
    catalog = GovernedDictionary.from_mapping({"TXN": "Transaction"})
    lenient = NamingPolicy.governed_default()
    strict = NamingPolicy(unknown=UnknownPolicy.REJECT)
    expand_identifier("TXN_KYC", catalog, lenient)
    try:
        expand_identifier("TXN_KYC", catalog, strict)
    except LexiconError:
        report.append("  REJECT still raises after a PASSTHROUGH_TITLECASE call warmed the memo")
    else:
        problems.append(
            f"{FAILURE_MARKER}: a passthrough memoised under PASSTHROUGH_TITLECASE was "
            "served to an UnknownPolicy.REJECT call, which was supposed to raise. The "
            "per-policy split is not holding."
        )

    # 2. A call-scoped overlay must not be served an answer computed without it,
    #    at either level. `with_custom` builds a new instance with empty memos;
    #    this asserts the consequence rather than the mechanism.
    warm = expand_identifier("TXN_KYC", catalog, lenient)
    overlaid = expand_identifier("TXN_KYC", catalog, lenient, custom={"KYC": "Know Your Customer"})
    if warm.phrase == overlaid.phrase or not overlaid.is_fully_known:
        problems.append(
            f"{FAILURE_MARKER}: a custom= overlay was served the answer computed without "
            f"it ({warm.phrase!r} vs {overlaid.phrase!r}). An identifier memo keyed only "
            "by the identifier would do exactly this."
        )
    else:
        report.append(
            f"  custom= is not served the pre-overlay answer ({warm.phrase!r} -> "
            f"{overlaid.phrase!r})"
        )

    # 3. The overlay's answer must not leak back to the un-overlaid dictionary.
    after = expand_identifier("TXN_KYC", catalog, lenient)
    if after.to_json() != warm.to_json():
        problems.append(
            f"{FAILURE_MARKER}: an overlaid call changed what the base dictionary answers "
            f"afterwards ({warm.phrase!r} -> {after.phrase!r})."
        )
    else:
        report.append("  the overlay does not write back into the base dictionary's memo")
    return problems, report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="cap each corpus at this many identifiers (0 = the whole corpus)",
    )
    parser.add_argument(
        "--only",
        choices=("all", "levels", "properties"),
        default="all",
        help="restrict the run",
    )
    args = parser.parse_args(argv)

    problems: List[str] = []
    report: List[str] = []

    if args.only in ("all", "properties"):
        found, lines = check_properties()
        problems += found
        report += lines

    if args.only in ("all", "levels"):
        corpora: List[Tuple[str, Sequence[str], Callable[[], GovernedDictionary]]] = [
            (
                "generated/fixture",
                generated_corpus(GENERATED_IDENTIFIERS),
                build_fixture_dictionary,
            ),
        ]
        for name in sorted(SNAPSHOTS):
            real = read_snapshot(name)
            if real is None:
                report.append(f"  {name}: absent, skipped (data/ is fetched, never committed)")
                continue
            corpora.append((f"{name}/empty", real, lambda: GovernedDictionary({})))
            corpora.append((f"{name}/fixture", real, build_fixture_dictionary))
        reached = dict.fromkeys(LEVELS, 0)
        for label, identifiers, factory in corpora:
            capped = identifiers[: args.limit] if args.limit else identifiers
            found, lines = compare_corpus(label, capped, factory, reached)
            problems += found
            report += lines
        report.append(f"  levels reached across the whole run: {reached}")
        never = [level for level, size in reached.items() if size == 0]
        if never:
            problems.append(
                f"{FAILURE_MARKER}: {never} were empty on every corpus in this run, so "
                "nothing here says anything about them. Add a corpus that reaches them "
                "rather than reading the green above as covering them."
            )

    for line in report:
        print(line)
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    print("every memo level is byte-identical to no memo at all, provenance included")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
