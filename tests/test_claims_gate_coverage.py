"""The claims gate's advertised coverage, checked against the gate.

Two user-facing documents describe what ``tools/check_claims.py`` catches. Both
said it fails the build on *any* untraceable performance figure "anywhere in the
docs or the source". That was false in both, and it stood from the commit that
created the sentence until somebody read the page cold -- no gate could see it,
because **a claim about a tool's behaviour carries no number for a ratchet to
check**.

This module is the narrow mechanical part of that class, and it is narrow on
purpose. It cannot verify that prose is true. It can verify two things that
together make the specific failure expensive:

1. **The blind spot is closed, and stays closed.** An uncited latency figure in
   microseconds now fails the gate, exactly as an uncited accuracy percentage in
   the same position always did. If somebody reverts the arming vocabulary, this
   test goes red and points at the seven documents that would then be overstating
   the gate. The assertion below used to run the other way -- it pinned the hole
   open so it could not quietly change -- and inverting it is the whole of this
   round's change to this module.
2. **The two copies of the sentence agree.** *One sentence written in two places
   and corrected in one* is the shape this repository has hit four times: the
   mypy floor rationale (twice, in two files), the ``socrata`` scan-glob note,
   and this. Where the same claim is duplicated, the duplication itself is
   checkable even when the claim is not.

3. **The widening is present in the shipped rules, not merely equivalent to
   them.** ``latency`` and ``duration`` are metric keywords and the three
   spelled-out sub-second units are units. Asserting the vocabulary directly is
   what stops the injection test above passing for some unrelated reason -- an
   exit code standing in for a specific claim is this repository's most repeated
   confound.

4. **The residue is pinned too.** Closing this closed two keywords and three
   units. It did not close the plurals ``latencies`` and ``durations``, a bare
   ``seconds``, a speedup ``x``, or a memory figure in ``KB`` -- each of those is
   injected below and each must still exit ``0``. **A closure reported as total
   would be the same defect one level up**, so the parts that are still open are
   a passing test rather than a sentence.

**What this does not do.** It does not check that the corrected wording is
accurate -- only that the two copies match and that the behaviour they describe
is still the behaviour. A third copy in a file nobody listed here is invisible to
it, and so is a rewording that keeps both copies consistent and both wrong.

**Why the widening was taken, having been measured and refused twice.** The
refusal rested on a real cost: it costs the deferred ratchet nothing, but it cost
seven shipped documents their accuracy -- ``docs/SOURCING.md`` was the seventh and
was missed on the first pass -- ``README.md``, ``docs/EVALUATION.md``,
``docs/DEFINITION-OF-DONE.md``, ``docs/POSITIONING.md``, ``docs/SECOND-READER.md``
and ``docs/DECISIONS.md`` all stated that an uncited latency in microseconds
passes, and three of them print a MEASURED mutation battery whose ``rc=0`` row
inverts. **Keeping a known blind spot open to preserve the descriptive accuracy
of the documents documenting it is circular debt**, and the thesis of this
library is refusing silent failures and deleting checks that cannot fail. All
six were corrected in the same commit that widened the rules, and the three
batteries were **re-run** rather than having their digits edited. See
``docs/GATES.md``, "The claims gate's hole, closed".

**The freeness was re-derived before it was taken, not inherited.** Across the
whole scanned set, not one line carrying ``latency`` or ``duration`` has a
free-standing prose number within the proximity window, and no prose number is
followed by a spelled-out sub-second unit -- so no number changed arming class
and neither ratchet moved. Which also means **the widened rule was permitted by
this tree and calibrated by nothing**: zero firings measure the documents, not
the rule. That is why the injections below exist.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_PATH = REPO_ROOT / "tools" / "check_claims.py"
README = REPO_ROOT / "README.md"
EVALUATION = REPO_ROOT / "docs" / "EVALUATION.md"

if not TOOL_PATH.is_file():  # pragma: no cover - CI job only
    pytest.skip(
        "tools/ is not part of an installed distribution; these tests belong to a checkout",
        allow_module_level=True,
    )


def _load_tool() -> ModuleType:
    """Import the claims gate by path; ``tools/`` is deliberately not a package."""
    spec = importlib.util.spec_from_file_location("_check_claims_for_coverage_test", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


#: The sentence fragment both documents must carry. Deliberately the *hedge*
#: rather than the whole sentence: the surrounding prose differs between the two
#: pages and should be allowed to, but the scope qualifier is the part that was
#: wrong and the part that must not silently revert to "any".
_COVERAGE_HEDGE = "that the gate can recognise"

#: The wording that was false in both files. Asserting its ABSENCE is what makes
#: a revert loud, and it is worth more than asserting the correction's presence:
#: somebody restoring the old sentence would otherwise only fail the positive
#: check, which is easy to read as a wording nit.
_RETIRED_OVERCLAIMS = (
    "a performance claim anywhere in the docs or the source cannot be traced",
    "any performance figure in the docs or the",
)


def _flowed(text: str) -> str:
    """Collapse whitespace, because markdown wraps and a wrap is not a change.

    Found by this test failing on its own first run: the corrected sentence in
    ``docs/EVALUATION.md`` had a line break inside the hedge, so a literal
    substring search reported the qualifier missing when it was present. A
    prose check that a reflow can break is a check that will be deleted the
    first time somebody reformats a paragraph.
    """
    return re.sub(r"\s+", " ", text)


@pytest.mark.parametrize("page", [README, EVALUATION], ids=["README.md", "docs/EVALUATION.md"])
def test_both_copies_of_the_coverage_sentence_carry_the_hedge(page: Path) -> None:
    """Neither page may claim the gate catches everything."""
    text = _flowed(page.read_text(encoding="utf-8"))
    assert _COVERAGE_HEDGE in text, (
        f"{page.name} describes the claims gate's coverage without the scope qualifier "
        f"{_COVERAGE_HEDGE!r}. The gate arms numbers by metric-keyword proximity or a "
        "trailing unit; it does not catch every performance figure, and saying it does "
        "was false in this file for months."
    )
    for retired in _RETIRED_OVERCLAIMS:
        assert retired not in text, (
            f"{page.name} has reverted to the retired overclaim {retired!r}. "
            "It is false: see the blind-spot test in this module."
        )


#: An invisible marker carried by every injection, so debris is identifiable.
#:
#: **This exists because the debris happened.** On 2026-08-25 this helper's
#: injected latency sentence was found sitting in the working tree's
#: ``README.md`` at line 716 -- left there by two runs of this module
#: interleaving, each restoring bytes it had read while the other's injection
#: was live. ``python tools/check_claims.py`` exited ``0`` and did not name the
#: file, because that sentence is exactly the one the gate cannot see: the front
#: page carried an invented performance figure and every gate in the repository
#: was green. It is the blind spot below observed in anger rather than by
#: injection, and it is the argument for closing it.
#:
#: The marker is not a ``<!--claim:...-->`` citation and the gate ignores it.
_PROBE_MARKER = "<!-- claims-gate-coverage probe; a leftover of this line is a bug -->"


def _readme_debris() -> int:
    """How many probe markers are sitting in README.md right now."""
    return README.read_text(encoding="utf-8").count(_PROBE_MARKER)


def _run_gate_with_injection(injected: str) -> Optional[int]:
    """Inject one sentence into README.md, run the gate, and always restore.

    Mutating the real file is deliberate rather than lazy: the gate resolves its
    scan globs against the repository root, so a copied tree would not be the
    thing under test. The ``finally`` restores the original bytes.

    Returns the gate's exit code, or ``None`` when the injected sentence was not
    still on disk at the moment the gate finished -- which means another process
    overwrote it and the exit code is about somebody else's tree.

    **Four guards, all of them added after a real leak.** The restore is a
    ``finally`` and that is not enough: nothing here is atomic, and when a second
    process is running the same module against the same checkout -- which is the
    normal state of this repository -- one restore writes back bytes captured
    while the other's injection was live. So this helper refuses to start when a
    marker is already present, verifies its own sentence survived the gate run,
    checks its marker is gone afterwards, and hands ``None`` to the caller rather
    than a number it cannot stand behind. **A measurement that cannot say whose
    tree it measured is not a measurement**, which is this round's most repeated
    finding and the reason for the third guard.
    """
    if _readme_debris():
        raise AssertionError(
            "README.md already carries a claims-gate probe marker. Either a previous run of "
            "this module died between injection and restore, or a second process is running "
            "it against this checkout right now. Both leave an invented performance figure "
            "on the front page that no gate here can see -- remove the marked line before "
            "re-running."
        )
    original = README.read_bytes()
    try:
        text = original.decode("utf-8")
        anchor = "## Documentation"
        assert text.count(anchor) == 1, "README anchor for injection is no longer unique"
        probe = f"{_PROBE_MARKER}\n{injected}\n\n{anchor}"
        README.write_bytes(text.replace(anchor, probe, 1).encode("utf-8"))
        completed = subprocess.run(
            [sys.executable, str(TOOL_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        still_there = injected in README.read_text(encoding="utf-8")
        return completed.returncode if still_there else None
    finally:
        README.write_bytes(original)
        if _readme_debris():  # pragma: no cover - only under a concurrent run
            raise AssertionError(
                "the restore did not remove this module's probe from README.md. The front "
                "page is carrying an uncited figure the claims gate cannot see; delete the "
                f"line marked {_PROBE_MARKER!r}."
            )


def _or_skip(code: Optional[int]) -> int:
    """The exit code, or a skip when another process owned README.md meanwhile."""
    if code is None:
        pytest.skip(
            "another process overwrote README.md while this injection was live, so the "
            "gate's exit code is about a tree this test did not build. Re-run on a quiet "
            "checkout."
        )
    return code


def test_no_probe_survived_an_earlier_run() -> None:
    """The front page carries no leftover injection.

    Cheap, and it is the check that was missing: the leak of 2026-08-25 was found
    by a widening measurement noticing an extra armed number, not by anything
    watching for it. A gate cannot see this sentence, so a test has to.

    **The wait is the whole difference between a leftover and an overlap.** A
    marker seen once may be another process's injection, live, about to be
    restored -- observed on this checkout within minutes of the guard being
    written. A marker still there seconds later is debris. One process on a
    runner never reaches the loop at all; it exists for a checkout several
    agents are working in, and it is bounded so a real leftover still fails.
    """
    deadline = time.monotonic() + 10.0
    while _readme_debris() and time.monotonic() < deadline:
        time.sleep(0.5)
    assert _readme_debris() == 0, (
        "README.md has carried a claims-gate probe for ten seconds, so it is a leftover "
        "rather than another process's live injection. It is an invented performance figure "
        "on the front page, and `python tools/check_claims.py` exits 0 with it there."
    )


def _require_an_unmutated_green_gate() -> None:
    """Skip when the gate is already red, because then an injection proves nothing.

    **This is the ``UNRESTORED`` verdict of ``tools/gates.py``, applied here.**
    Both tests below read the gate's whole-process exit code as a statement
    about one injected sentence, and that inference is only valid while the
    unmutated tree exits zero. On 2026-08-25 it was not: another workstream
    added a decision record, ``RECORD_FILE_PIN`` went stale, the gate exited
    ``1`` for a reason with nothing to do with latency, and
    the injection test then called ``test_the_measured_blind_spot_is_still_there``
    reported *"the claims gate now catches an uncited latency-in-microseconds
    figure"*. It did not, then. **It does now** -- the vocabulary was widened in
    a later round -- and that makes the confound sharper rather than moot: a
    right answer produced by a broken inference is still a broken inference, and
    the same skip would be needed to tell the two apart today. An
    exit code standing in for a specific claim is the same confound the
    ``gates.suite`` demonstration carries, and it is worth naming twice.

    A skip is the honest answer rather than a weak one: a demonstration against
    a gate that was already failing is not evidence, in either direction.
    """
    completed = subprocess.run(
        [sys.executable, str(TOOL_PATH)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        pytest.skip(
            "the claims gate exits "
            f"{completed.returncode} on the UNMUTATED tree, so an injected sentence cannot be "
            "attributed anything. Fix the standing failure first:\n"
            + "\n".join(
                line for line in (completed.stdout + completed.stderr).splitlines() if line.strip()
            )[-1200:]
        )


def test_the_positive_control_fails_the_build() -> None:
    """An armed, uncited figure must red the gate, or the test below proves nothing."""
    _require_an_unmutated_green_gate()
    code = _or_skip(
        _run_gate_with_injection("Governed expansion accuracy reached 99.94 % in this release.")
    )
    assert code == 1, (
        "an uncited accuracy percentage did not fail the claims gate. Either the gate "
        "regressed or the injection anchor stopped working -- until this passes, the "
        "blind-spot test below is not evidence of a blind spot."
    )


def test_the_closed_blind_spot_stays_closed() -> None:
    """An uncited latency in microseconds fails the build, and the docs say so.

    This assertion used to read ``== 0`` and to say that a red build here was a
    widening to be adopted. The widening was adopted; the row inverted; the six
    documents were corrected in the same commit. If this goes back to ``0``, the
    arming vocabulary was narrowed and those seven documents are now overstating
    the gate -- which is the failure this module exists to make expensive.
    """
    _require_an_unmutated_green_gate()
    code = _or_skip(
        _run_gate_with_injection(
            "Median latency for a governed expansion fell to 41 microseconds in this release."
        )
    )
    assert code == 1, (
        "the claims gate no longer catches an uncited latency-in-microseconds figure. "
        "That is a NARROWING and it re-opens the hole that was found live on the front "
        "page on 2026-08-25. Either restore 'latency' to _KEYWORDS and the spelled-out "
        "sub-second units to _UNIT_AFTER_NUMBER, or correct README.md, docs/EVALUATION.md, "
        "docs/DEFINITION-OF-DONE.md, docs/POSITIONING.md, docs/SECOND-READER.md and "
        "docs/DECISIONS.md, which all now state that this case is caught."
    )


#: What the gate still cannot see, one sentence each, all of them exiting ``0``.
#:
#: This is the residue of the closure, pinned rather than described. Closing the
#: latency asymmetry closed two keywords and three units; these are the classes
#: of performance claim that remain invisible, and a round that closes one of
#: them turns the matching row red and has to say so.
_UNCAUGHT_RESIDUE = (
    # The keyword rule matches whole words, so the plural misses.
    ("plural keyword", "Median latencies for governed expansion fell to 41.37 this quarter."),
    # Deliberately not armed: a bare `seconds` would arm dates and intervals.
    ("bare seconds", "A full governed sweep took 41.37 seconds in this release."),
    # `41.37x` is not free-standing, so no arming rule is ever consulted.
    ("speedup multiplier", "Governed expansion is 41.37x faster than the baseline."),
    # Memory and byte figures were considered for the unit rule and not taken.
    ("memory in KB", "Governed expansion holds 41.37 KB of resident state in this release."),
)


@pytest.mark.parametrize(
    "sentence", [text for _, text in _UNCAUGHT_RESIDUE], ids=[name for name, _ in _UNCAUGHT_RESIDUE]
)
def test_the_residue_the_closure_left_behind_is_still_uncaught(sentence: str) -> None:
    """The closure is partial, and each part still open is a passing test.

    **A closure reported as total would be the same defect one level up.** The
    module docstring lists these four; this runs them through the real gate so
    the list cannot drift from the behaviour. A red row here is good news and
    means the vocabulary got wider again -- update the docstring, ``docs/GATES.md``
    and the residue section of ``tools/check_claims.py`` in the same commit.
    """
    _require_an_unmutated_green_gate()
    code = _or_skip(_run_gate_with_injection(sentence))
    assert code == 0, (
        f"the claims gate now catches {sentence!r}. That is a WIDENING beyond the one this "
        "module records. Move this case out of _UNCAUGHT_RESIDUE and correct every document "
        "that publishes the residue list."
    )


def test_the_closure_has_a_named_cause_rather_than_being_folklore() -> None:
    """The arming rules must actually hold the terms, not merely happen to catch them.

    The injection above reads a whole-process exit code, which is the confound
    this repository has hit three times in one round. This asserts the mechanism
    directly, so a green injection for some unrelated reason cannot be read as
    the vocabulary being present.
    """
    tool = _load_tool()

    # The two arming rules are different KINDS of object, which this test got
    # wrong on its first run: `_KEYWORDS` is a tuple of substrings, but
    # `_UNIT_AFTER_NUMBER` is a compiled `re.Pattern` and iterating it raises
    # `TypeError`. Asserting the shape rather than duck-typing it means a future
    # change from pattern to sequence fails here loudly instead of silently
    # making the check vacuous.
    keywords = getattr(tool, "_KEYWORDS", ())
    unit_rule = getattr(tool, "_UNIT_AFTER_NUMBER", None)
    assert isinstance(keywords, tuple) and keywords, (
        "_KEYWORDS is not a non-empty tuple; this test would pass vacuously"
    )
    assert isinstance(unit_rule, re.Pattern), (
        "_UNIT_AFTER_NUMBER is no longer a compiled pattern; re-derive what the unit "
        "arming rule actually matches before trusting the assertions below"
    )

    lowered = {str(k).lower() for k in keywords}
    for keyword in _WIDENED_KEYWORDS:
        assert keyword in lowered, (
            f"{keyword!r} is not a metric keyword any more, so the closure the seven documents "
            "describe has been reverted. Re-derive the coverage sentences."
        )
    for unit in (" microseconds", " milliseconds", " nanoseconds", "microsecond", " microseconds."):
        assert unit_rule.match(unit) is not None, (
            f"the unit arming rule no longer matches {unit!r}; the documented cause of the "
            "closure is stale."
        )
    # And the residue has a named cause too: a whole-word keyword misses its own
    # plural, which is why `_UNCAUGHT_RESIDUE` leads with `latencies`.
    assert tool.keyword_positions("median latencies fell") == []
    assert unit_rule.match(" seconds") is None, (
        "a bare 'seconds' is now a unit. That arms dates and interval lengths; it was "
        "refused on purpose. Re-derive the residue list before accepting it."
    )


#: The narrow widening D-052 did not consider, measured rather than argued about
#: and now **shipped**. ``latency`` and ``duration`` as keywords; the three
#: spelled-out sub-second units as units. Deliberately NOT a bare ``seconds``:
#: every duration in this tree is sub-second, and a rule matching ``seconds``
#: would arm dates, counts of seconds in an interval, and the word wherever it
#: follows a number.
_WIDENED_KEYWORDS = ("latency", "duration")

#: The arming rules as they stood before the closure. Kept so that the freeness
#: of the widening can be **re-derived on every run against the live tree**
#: rather than inherited from the round that took it: if a later document writes
#: a latency figure that the old rules could not see, the widening stops being
#: free retroactively, the ledgers this repository ratchets shut are the ones
#: that would have moved, and the test below says so.
_PRE_WIDENING_UNIT_AFTER_NUMBER = re.compile(
    r"^[ \t]*(?:"
    r"%"
    r"|[µμumn]s\b"
    r"|[A-Za-z]*/(?:s|sec|second)s?\b"
    r")"
)


def _armings(tool: ModuleType, text: str, suffix: str) -> list:
    """Every claim-shaped number in one already-read file, with the rule that armed it.

    **This reads nothing.** It is handed the file's text, so both rule sets are
    evaluated against identical bytes and there is no window in which the tree
    can move between them. That matters more than it sounds: several agents edit
    this checkout at once, and the previous version of this measurement -- two
    full scans of the working tree, seconds apart -- reported a widening twice on
    2026-08-25 because somebody else saved a file in between. A comparison whose
    two halves read the disk separately is measuring the disk.

    It also measures ARMING rather than backing, which is the tighter statement:
    a rule that arms nothing new cannot move anything into any backing class.
    """
    raw_lines = text.splitlines()
    prose_lines = tool.prose_of(text, suffix).splitlines()
    citation_free = [tool._mask_spans(line, tool._CITATION_ANY) for line in prose_lines]
    found = []
    for number, raw in enumerate(raw_lines, start=1):
        prose = citation_free[number - 1] if number - 1 < len(citation_free) else ""
        if not prose.strip():
            continue
        keywords = tool.keyword_positions(raw)
        for offset, claim in tool.iter_claim_numbers(prose):
            found.append((number, claim, tool.arming_of(prose, offset, claim, keywords)))
    return found


def _newly_armed(tool: ModuleType, monkeypatch: pytest.MonkeyPatch, **widened: object) -> list:
    """Numbers on which the shipped rules and ``widened`` disagree.

    One read per file, two evaluations of the same bytes. Returns
    ``(path, line, number, shipped_arming, other_arming)`` for every
    disagreement. The direction is not baked in: pass the pre-widening rules to
    ask what the closure cost, or a deliberately over-wide rule to check that
    the comparison can detect anything at all.
    """
    shipped = {"_KEYWORDS": tool._KEYWORDS, "_UNIT_AFTER_NUMBER": tool._UNIT_AFTER_NUMBER}
    project = tool.Project.at(REPO_ROOT)
    differences: list = []
    for path in tool.scan_paths(project):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):  # pragma: no cover - defensive
            continue
        for name, value in shipped.items():
            monkeypatch.setattr(tool, name, value)
        before = _armings(tool, text, path.suffix)
        for name, value in widened.items():
            monkeypatch.setattr(tool, name, value)
        after = _armings(tool, text, path.suffix)
        for name, value in shipped.items():
            monkeypatch.setattr(tool, name, value)
        assert len(before) == len(after), "arming changed which numbers are claim-shaped"
        differences.extend(
            (path.name, line, number, was, now)
            for (line, number, was), (_, _, now) in zip(before, after)
            if was != now
        )
    return differences


def test_the_measured_price_of_the_closure_is_still_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shipped rules must arm nothing the pre-widening rules did not.

    D-052 refused a wide widening because arming on everything would relabel
    over a thousand numbers nobody had adjudicated. A NARROW one is a different
    object and it was measured: on this tree it arms nothing new at all, so it
    neither fails the build nor grows ``DEFERRED_BASELINE``, which the trajectory
    forbids from growing.

    **The direction of this comparison flipped when the widening shipped.** It
    used to ask what the un-taken widening would cost; it now asks whether the
    taken one is still costing zero, which is the same arithmetic and a live
    question rather than a historical one. If a document acquires a latency
    figure in prose, this goes red *and so does the gate*, and the failure here
    is the one that names the number.

    The measurement carries its own positive control below, because a comparison
    that cannot detect a difference reports zero for either reason.
    """
    tool = _load_tool()
    narrowed = tuple(k for k in tool._KEYWORDS if k not in _WIDENED_KEYWORDS)
    assert len(narrowed) == len(tool._KEYWORDS) - len(_WIDENED_KEYWORDS), (
        "_KEYWORDS no longer carries the widened vocabulary, so this comparison would "
        "measure nothing. See test_the_closure_has_a_named_cause_rather_than_being_folklore."
    )
    moved = _newly_armed(
        tool,
        monkeypatch,
        _KEYWORDS=narrowed,
        _UNIT_AFTER_NUMBER=_PRE_WIDENING_UNIT_AFTER_NUMBER,
    )
    assert moved == [], (
        f"the shipped rules arm {len(moved)} number(s) the pre-widening rules did not, "
        f"e.g. {moved[:3]}. The closure's price was zero on the tree it was taken against and "
        "the two ratchets are pinned shut. Cite the number that moved, or record the ratchet "
        "shift in LEDGER_TRAJECTORY with its by_citation/by_deletion/by_fencing/by_other split."
    )


def test_that_measurement_could_have_detected_a_difference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The positive control on the test above. Zero firings measures nothing.

    Arming on an ordinary English word must arm hundreds of numbers. If it does
    not, the comparison above is comparing two identical evaluations for a reason
    that has nothing to do with latency, and its zero means nothing.
    """
    tool = _load_tool()
    moved = _newly_armed(tool, monkeypatch, _KEYWORDS=(*tool._KEYWORDS, "the"))
    assert len(moved) > 100, (
        f"arming on the word 'the' armed only {len(moved)} number(s). The comparison in the "
        "test above cannot detect a widening, so its zero is not evidence of one costing "
        "nothing."
    )
