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

1. **The blind spot still exists.** An uncited latency figure in microseconds
   passes the gate; an uncited accuracy percentage in the same position fails it.
   If somebody widens the arming rules so the latency case starts failing, this
   test goes red and points at the sentences that would then be understating the
   gate. A blind spot that is *measured* is a different object from one that is
   merely present.
2. **The two copies of the sentence agree.** *One sentence written in two places
   and corrected in one* is the shape this repository has hit four times: the
   mypy floor rationale (twice, in two files), the ``socrata`` scan-glob note,
   and this. Where the same claim is duplicated, the duplication itself is
   checkable even when the claim is not.

**What this does not do.** It does not check that the corrected wording is
accurate -- only that the two copies match and that the behaviour they describe
is still the behaviour. A third copy in a file nobody listed here is invisible to
it, and so is a rewording that keeps both copies consistent and both wrong.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

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


def _run_gate_with_injection(injected: str) -> int:
    """Inject one sentence into README.md, run the gate, and always restore.

    Mutating the real file is deliberate rather than lazy: the gate resolves its
    scan globs against the repository root, so a copied tree would not be the
    thing under test. The ``finally`` restores the original bytes.
    """
    original = README.read_bytes()
    try:
        text = original.decode("utf-8")
        anchor = "## Documentation"
        assert text.count(anchor) == 1, "README anchor for injection is no longer unique"
        README.write_bytes(text.replace(anchor, f"{injected}\n\n{anchor}", 1).encode("utf-8"))
        completed = subprocess.run(
            [sys.executable, str(TOOL_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return completed.returncode
    finally:
        README.write_bytes(original)


def test_the_positive_control_fails_the_build() -> None:
    """An armed, uncited figure must red the gate, or the test below proves nothing."""
    code = _run_gate_with_injection("Governed expansion accuracy reached 99.94 % in this release.")
    assert code == 1, (
        "an uncited accuracy percentage did not fail the claims gate. Either the gate "
        "regressed or the injection anchor stopped working -- until this passes, the "
        "blind-spot test below is not evidence of a blind spot."
    )


def test_the_measured_blind_spot_is_still_there() -> None:
    """An uncited latency in microseconds passes, and the docs say so.

    If this starts failing, the gate got wider and that is good news -- but the
    two sentences checked above are then understating it, and they must be
    corrected in the same commit that widens the rules.
    """
    code = _run_gate_with_injection(
        "Median latency for a governed expansion fell to 41 microseconds in this release."
    )
    assert code == 0, (
        "the claims gate now catches an uncited latency-in-microseconds figure. That is a "
        "WIDENING, not a regression. Update the coverage sentences in README.md and "
        "docs/EVALUATION.md, which currently tell readers this case is not caught, and "
        "then change this test to match the new coverage."
    )


def test_the_blind_spot_has_a_named_cause_rather_than_being_folklore() -> None:
    """The arming rules must actually lack the terms, not merely happen to miss them."""
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
        "arming rule actually matches before trusting the assertion below"
    )

    lowered = {str(k).lower() for k in keywords}
    assert "latency" not in lowered, (
        "'latency' is now a metric keyword, so the blind spot above has a different cause "
        "than the docs state. Re-derive the coverage sentences."
    )
    assert unit_rule.match(" microseconds") is None, (
        "spelled-out 'microseconds' is now matched by the unit arming rule; the documented "
        "cause of the blind spot is stale."
    )
