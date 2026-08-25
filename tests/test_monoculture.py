"""Tests for ``bench/run_monoculture.py``.

Two of these are unusual and are the reason the file exists.

**The independence tests are the deliverable, not a check on it.** The claim
``shapecue`` makes is that it is not a Schwartz & Hearst descendant, and a claim
about lineage is worth nothing asserted. So it is stated as two falsifiable
properties and tested as such: the proposer accepts a pair whose short form
shares **no character** with its long form (so it cannot be running the 2003
validator), and it proposes **nothing** on the canonical parenthetical
arrangement with no cue in it (so it cannot be running the 2003 candidate
generator). Either test failing means the independence claim is false, which is
what a test of a claim should mean.

**The reachability test is an air-gap guard.** This module is a measuring
instrument, and the corpus-construction rule (R10) is that a measuring
instrument may not become a shipped code path. Nothing under ``src/acronymkit``
may name it.

Every assertion here was mutation-checked in place rather than assumed to be
capable of failing (R11): each was run once against a deliberately broken
implementation and observed red before being left green.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "bench" / "run_monoculture.py"

# A GUARD, NOT A LINE IN `EXPECTED_NON_PASSING`. The sdist ships `bench/` as a
# package directory (because `bench/results.json` and `bench/splits.toml` ship)
# and deliberately ships none of its modules, so the import below raises
# `ImportError` there and this file would fail to COLLECT. `pytest.mark.skipif`
# cannot help: marks are consulted at collection and a module body runs at
# import, so the exception has already happened -- the lesson of D-058's fifth
# historical breakage. The condition named is exactly the one that differs, so
# any other error in this file still reaches the job.
if not RUNNER.is_file():  # pragma: no cover - installed/sdist runs only
    pytest.skip(
        "bench/run_monoculture.py is not part of an installed distribution",
        allow_module_level=True,
    )

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bench import run_monoculture as mono  # noqa: E402


# ---------------------------------------------------------------------------
# The Schwartz & Hearst validator, transcribed
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("short_form", "long_form", "expected"),
    [
        ("WHO", "World Health Organization", True),
        ("HMG-CoA", "3-hydroxy-3-methylglutaryl coenzyme A", True),
        ("CNS", "central nervous system", True),
        # The first character must land on a word-initial character. "system"
        # holds an "s", but not at the start of a word after "central nervous",
        # so a short form beginning with the wrong letter is refused.
        ("QQQ", "World Health Organization", False),
        ("XYZ", "central nervous system", False),
        # Right-to-left and greedy: every character must appear, in order.
        # `WOH` is NOT here, and the omission is the point -- it aligns
        # (`W`orld ... `O`... `H`ealth is not the reading; the walk runs right to
        # left and finds `h` in "Healt`h`", `o` in "W`o`rld", `W` word-initial),
        # so an intuition about which permutations are refused is not a substitute
        # for running the walk. `OWH` really is refused: after `h` and `w` the
        # first character has no `o` left of the `W`.
        ("OWH", "World Health Organization", False),
        ("", "central nervous system", False),
        ("---", "central nervous system", False),
        ("CNS", "", False),
    ],
)
def test_sh_alignable_matches_the_paper(short_form: str, long_form: str, expected: bool) -> None:
    """The predicate every system in the family inherits, on decided cases."""
    assert mono.sh_alignable(short_form, long_form) is expected


def test_sh_alignable_requires_a_word_initial_anchor() -> None:
    """The first short-form character may not land mid-word.

    This is the clause that separates the 2003 algorithm from a plain
    subsequence test, and dropping it is the most likely way a re-implementation
    goes subtly wrong. ``"ns"`` is a subsequence of ``"central nervous system"``
    twice over, and only the word-initial reading is the paper's.
    """
    assert mono.sh_alignable("ns", "central nervous system") is True
    assert mono.sh_alignable("rs", "central nervous system") is False


# ---------------------------------------------------------------------------
# The independence claim, as two falsifiable properties
# ---------------------------------------------------------------------------
def test_shapecue_accepts_a_pair_with_no_shared_character() -> None:
    """It cannot be running the S&H validator, because the validator refuses this.

    ``QQQ`` shares no character with ``Bureau of Weights``. Every implementation
    in the family must refuse the pair; ``shapecue`` proposes it. This is the
    whole independence argument on the validator axis, and it is one assertion.
    """
    _, edges = mono.propose_shapecue(mono.DISJOINT_CASE)
    proposed = [
        (mono.DISJOINT_CASE[s[0] : s[1]], mono.DISJOINT_CASE[lf[0] : lf[1]]) for s, lf, _ in edges
    ]
    assert ("QQQ", "Bureau of Weights") in proposed
    assert mono.sh_alignable("QQQ", "Bureau of Weights") is False


def test_shapecue_proposes_nothing_on_a_bare_parenthetical() -> None:
    """It cannot be running the S&H candidate generator, which lives on this case."""
    _, edges = mono.propose_shapecue(mono.PARENTHETICAL_CASE)
    assert edges == []
    assert mono.sh_alignable("WHO", "World Health Organization") is True


def test_shapecue_ignores_the_short_form_entirely_when_pairing() -> None:
    """Swapping the abbreviation for an unrelated string changes no long form.

    A character-alignment validator's output depends on the short form's
    characters by definition. This one's does not, so the long form it returns is
    invariant under any shape-preserving substitution of the short form.
    """
    # Asserted per replacement rather than over the union. `BOW` happens to
    # align into "Bureau of Weights", so a union assertion would survive a
    # proposer that had quietly started checking the alignment and dropped the
    # other three -- which is exactly the mutation this test exists to catch.
    for replacement in ("QQQ", "ZZZ", "BOW", "XKCD"):
        text = f"The Bureau of Weights, hereinafter {replacement}, met in June."
        _, edges = mono.propose_shapecue(text)
        assert [text[lf[0] : lf[1]] for _, lf, _ in edges] == ["Bureau of Weights"], replacement


def test_shapecue_reads_no_bracket() -> None:
    """Adding or removing brackets around a cue's long form changes nothing.

    Schwartz & Hearst's candidate generator is a bracket scanner, so a proposer
    whose output is invariant to bracketing is not running it.
    """
    _, plain = mono.propose_shapecue("The Global Environment Facility, hereinafter GEF, met.")
    _, bracketed = mono.propose_shapecue("The (Global Environment Facility) met.")
    assert len(plain) == 1
    assert bracketed == []


def test_roster_reads_the_three_legend_separators() -> None:
    """The class the measurement found: figure legends and table footnotes."""
    equals = "EPI = Echo planar imaging."
    colons = "BMI: body mass index; CE: cholesteryl ester; ELF: epithelial lining fluid."
    _, from_equals = mono.propose_shapecue(equals)
    _, from_colons = mono.propose_shapecue(colons)
    assert [equals[lf[0] : lf[1]] for _, lf, _ in from_equals] == ["Echo planar imaging"]
    assert [colons[lf[0] : lf[1]] for _, lf, _ in from_colons] == [
        "body mass index",
        "cholesteryl ester",
        "epithelial lining fluid",
    ]


def test_roster_quorum_refuses_a_lone_comma() -> None:
    """One comma is a sentence. The quorum is what stops prose being read as a roster."""
    # The lone entry is placed at a real roster anchor -- straight after a colon
    # -- so the *only* thing refusing it is the quorum. Written any other way the
    # test passes for the wrong reason: the pattern would not have matched at
    # all, and lowering the quorum to one would leave it green.
    _, lone = mono.propose_shapecue("The assay ran; PCR, the samples were frozen and stored.")
    assert lone == []
    _, several = mono.propose_shapecue("Hh, hedgehog; NRF2, nuclear factor; GO, Gene Ontology.")
    assert len(several) >= 2


def test_roster_quorum_counts_entries_the_shape_filter_refuses() -> None:
    """Whether a region is a roster is evidence about the region, not about its rows.

    ``Ct`` and ``Unk`` fail :func:`is_shape_short_form` and are still roster
    entries. If the quorum only counted emitted rows, a legend whose other rows
    are lower case would drop below it and the one good row would be lost.
    """
    text = "Abbreviations: Ct, cycle threshold; Unk, unknown; N1, nucleocapsid gene region 1"
    _, edges = mono.propose_shapecue(text)
    assert [text[short[0] : short[1]] for short, _, _ in edges] == ["N1"]


# ---------------------------------------------------------------------------
# The measuring apparatus
# ---------------------------------------------------------------------------
def test_bracket_adjacent_reads_both_arrangements() -> None:
    """``long form (SF)`` and ``SF (long form)`` both count; bare prose does not."""
    inside = "the central nervous system (CNS) was"
    ahead = "CNS (central nervous system) was"
    bare = "the central nervous system was"
    assert mono.bracket_adjacent(inside, (inside.index("CNS"), inside.index("CNS") + 3)) is True
    assert mono.bracket_adjacent(ahead, (0, 3)) is True
    assert mono.bracket_adjacent(bare, (4, 26)) is False


def test_matched_gold_is_one_to_one() -> None:
    """One sprawling prediction may not claim two gold spans under ``overlap``."""
    gold = [(0, 5), (10, 15)]
    assert mono.matched_gold(gold, [(0, 20)], "overlap") == {0}
    assert mono.matched_gold(gold, [(0, 20), (11, 12)], "overlap") == {0, 1}
    assert mono.matched_gold(gold, [(0, 20)], "exact") == set()


def test_overlap_record_computes_share_and_union_gain() -> None:
    """The R13 arithmetic, on a case whose answers can be read off by hand."""
    record = mono.overlap_record(
        {"a": {1, 2, 3}, "b": {2, 3}, "shapecue": {4}},
        "widget",
        {"corpus": "toy"},
    )
    assert record["union_total"] == 4
    assert record["n_a"] == 3
    assert record["share_pct_a"] == 75.0
    assert record["unique_a"] == 1
    assert record["union_gain_pct_a"] == 25.0
    # `b` is entirely inside `a`, so removing it loses the union nothing.
    assert record["unique_b"] == 0
    assert record["union_gain_pct_b"] == 0.0
    assert record["overlap_a__b"] == 2
    assert record["jaccard_a__b"] == round(100 * 2 / 3, 2)
    assert record["sh_family"] == ["a", "b"]
    assert record["sh_family_share_pct"] == 75.0
    assert record["independent_gain_pct"] == 25.0


def test_score_spans_counts_false_positives_and_negatives() -> None:
    """Coverage is reported beside independence, so its arithmetic is checked too."""
    passage = mono.Passage("u", "abcdefghij", gold_short=[(0, 2), (4, 6)])
    proposal = mono.Proposals()
    proposal.short_spans = {"u": [(0, 2), (8, 10)]}
    proposal.long_spans = {"u": []}
    scores = mono.score_spans([passage], proposal, "short_form", "exact")
    assert scores["short_form.exact_true_positives"] == 1
    assert scores["short_form.exact_false_positives"] == 1
    assert scores["short_form.exact_false_negatives"] == 1
    assert scores["short_form.exact_precision"] == 50.0
    assert scores["short_form.exact_recall"] == 50.0


def test_sh_family_excludes_exactly_the_independent_proposers() -> None:
    """The partition the whole report rests on, so it is asserted rather than read."""
    names = ["acronymkit/general", "pyab3p", "allcaps", "shapecue"]
    assert mono.sh_family(names) == ["acronymkit/general", "pyab3p"]
    assert set(mono.INDEPENDENT_PROPOSERS) == {"allcaps", "shapecue"}


# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------
def test_every_corpus_key_names_a_corpus_the_manifest_declares() -> None:
    """A runner may not open a corpus ``bench/splits.toml`` has never heard of.

    The readers this module calls already consult the manifest, so this asserts
    the mapping in :data:`bench.run_monoculture.CORPORA` rather than the read --
    a typo in the ``corpus`` field would put a wrong name into every record the
    runner writes and no reader would notice, because the reader is chosen by
    the key and the label is written from the table.
    """
    manifest = (REPO_ROOT / "bench" / "splits.toml").read_text(encoding="utf-8")
    declared = set(re.findall(r"^\[corpora\.([A-Za-z0-9_]+)\]", manifest, re.MULTILINE))
    assert declared, "no [corpora.*] tables found; the manifest moved or the regex is wrong"
    for key, entry in mono.CORPORA.items():
        name = str(entry["corpus"])
        base = "plod" if name.startswith("plod_cw") else name
        assert base in declared, f"{key} names corpus {name!r}, which the manifest does not declare"


def test_only_one_corpus_is_marked_as_having_pooled_gold() -> None:
    """The control has to be labelled, or the contrast it provides is invisible."""
    pooled = [key for key, entry in mono.CORPORA.items() if entry["pooled_gold"]]
    assert pooled == ["med1250"]


def test_no_shipped_module_can_reach_the_measuring_instrument() -> None:
    """R10's air gap: a bench instrument may not become a library code path.

    ``bench/run_monoculture.py`` shells out to a foreign interpreter, reads
    corpora from ``data/`` and exists to construct measurements. None of that
    may be reachable from an installed ``acronymkit``. Checked by name over the
    whole shipped package rather than by importing anything, because an import
    that succeeds proves less than a grep that finds nothing.
    """
    forbidden = ("run_monoculture", "shapecue", "sh_alignable", "propose_shapecue")
    offenders = []
    for module in sorted((REPO_ROOT / "src" / "acronymkit").rglob("*.py")):
        body = module.read_text(encoding="utf-8")
        for name in forbidden:
            if name in body:
                offenders.append(f"{module.relative_to(REPO_ROOT)} names {name!r}")
    assert offenders == []


def test_the_runner_imports_nothing_but_the_standard_library_at_module_level() -> None:
    """It has to load under a foreign interpreter that has never heard of acronymkit.

    ``--external-worker`` runs this same file under whichever Python has
    ``pyab3p`` and ``scispacy``. A top-level ``from bench import corpora`` or
    ``from acronymkit import ...`` would make that mode fail on import, and it
    would fail *only* on the machine that has the baselines installed -- which is
    the class of defect D-058 is about.
    """
    source = RUNNER.read_text(encoding="utf-8")
    body = source.split('"""', 2)[-1]
    top_level = re.findall(r"^(?:from|import)\s+([A-Za-z_][A-Za-z0-9_.]*)", body, re.MULTILINE)
    allowed = {
        "__future__",
        "argparse",
        "json",
        "os",
        "re",
        "subprocess",
        "sys",
        "tempfile",
        "time",
        "pathlib",
        "typing",
    }
    assert set(top_level) <= allowed, f"non-stdlib top-level import: {set(top_level) - allowed}"
