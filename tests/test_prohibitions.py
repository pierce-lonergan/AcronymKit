"""Tests for ``tools/prohibitions.py``.

The module states a denominator and draws a seeded sample from it. Both of
those are only worth anything if they are **reproducible** and if the
extraction rules do what their docstrings say, so that is what is tested here:

* the free-standing-number rule keeps figures and drops identifiers and dates,
  which is the difference between a claim frame and a token count;
* the draw is a pure function of ``(seed, stratum, frame)``;
* the prose span is exactly the complement of the evidence span inside the same
  records, so switching modes cannot silently double-count or drop lines;
* ``--check`` passes on this tree **and fails when the enumeration is broken**.
  The last one matters most. A self-consistency check nobody has seen fail is
  a check nobody has evidence works, which is R11 applied to a tool rather than
  to a CI gate.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "_prohibitions_under_test", REPO_ROOT / "tools" / "prohibitions.py"
)
assert _SPEC is not None and _SPEC.loader is not None
prohibitions = importlib.util.module_from_spec(_SPEC)
sys.modules["_prohibitions_under_test"] = prohibitions
_SPEC.loader.exec_module(prohibitions)


AUDIT_FIXTURE = """\
# Audit

### Five proposals that should not be built

| Proposal | Why not |
|---|---|
| Mirror the world | Coverage is `4.72 %` and the table is far too large |
| Vendor a catalogue | Covers `1.124 %` of real token occurrences |

---

## 1. How to make this better

### Do not do these

**Do not take the lever.** D-012 identified it; the audit bounded it.

```
run
  ceiling   85.44    against a baseline of 83.85
```

**Do not relax digits.** Measured on 2026-08-23; loses on MED1250 at 0.3.0.

---

## 4. Extending

### D. What should stay closed

**The cascade.** 30 rules and a fitted table.

**Adding a language.** Closed at four independent points.
"""

DECISIONS_FIXTURE = """\
# Decisions

## D-900 — A thing that was rejected

**Status:** rejected · **Evidence:** somewhere

Prose that mentions 77 in passing.

```
fenced
  measured   12.50
```

More prose mentioning 88.

---

## D-901 — A thing that shipped

**Status:** shipped · **Evidence:** elsewhere

Prose mentioning 99.
"""


def _tree(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "AUDIT-2026-08.md").write_text(AUDIT_FIXTURE, encoding="utf-8")
    (docs / "DECISIONS.md").write_text(DECISIONS_FIXTURE, encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Covers `1.124 %` of tokens", ["1.124"]),
        ("out of 1,221 gold", ["1,221"]),
        ("D-012 identified it", []),
        ("MED1250 is a tuning split", []),
        ("verified live, 2026-08-23", []),
        ("acronymkit-0.3.0-py3-none-any.whl", []),
        ("ceiling 85.44 against a baseline of 83.85", ["85.44", "83.85"]),
        # THE RULE'S KNOWN GAP, PINNED RATHER THAN HIDDEN. ``@`` and ``+`` are
        # not in the excluded-neighbour set, so ``R@25`` and ``U+2081`` are
        # admitted as figures even though both are identifiers.
        # ``tools/check_claims.py`` drops them; this module does not, and the
        # audit that used this frame says so rather than quietly tightening the
        # rule after seeing which claims it drew.
        ("R@25 is not a claim", ["25"]),
        ("U+2081 SUBSCRIPT ONE", ["2081"]),
    ],
)
def test_the_number_rule_keeps_figures_and_drops_identifiers(text: str, expected: list) -> None:
    assert [figure for _column, figure in prohibitions.free_standing_numbers(text)] == expected


def test_the_audit_rule_finds_every_shape_of_do_not(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    found, _claims = prohibitions.build_frame(root)
    labels = [p.label for p in found if p.stratum == "A"]
    assert len(labels) == 6, labels
    assert "Mirror the world" in labels
    assert "The cascade." in labels
    assert any(label.startswith("Do not take the lever") for label in labels)


def test_a_do_not_span_reaches_its_fenced_block(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _found, claims = prohibitions.build_frame(root)
    lever = [c.figure for c in claims if c.pid == "A03"]
    assert "85.44" in lever and "83.85" in lever


def test_the_closure_markers_select_only_closed_records(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    found, _claims = prohibitions.build_frame(root)
    assert [p.pid for p in found if p.stratum == "B"] == ["D-900"]


def test_the_evidence_span_reads_the_fence_and_not_the_prose(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _found, claims = prohibitions.build_frame(root, span_mode="evidence")
    figures = {c.figure for c in claims if c.pid == "D-900"}
    assert "12.50" in figures
    assert "77" not in figures and "88" not in figures


def test_the_prose_span_is_exactly_the_complement_of_the_evidence_span(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _f, evidence = prohibitions.build_frame(root, span_mode="evidence")
    _g, prose = prohibitions.build_frame(root, span_mode="prose")
    _h, everything = prohibitions.build_frame(root, span_mode="all")

    def key(claims: Any) -> list:
        return sorted((c.pid, c.line, c.figure) for c in claims if c.stratum in {"B", "P", "F"})

    assert not set(key(evidence)) & set(key(prose))
    assert sorted(key(evidence) + key(prose)) == key(everything)


def test_the_draw_is_a_pure_function_of_seed_and_frame() -> None:
    _found, claims = prohibitions.build_frame()
    first = prohibitions.draw(claims, 20260825, {"A": 5, "B": 5})
    second = prohibitions.draw(claims, 20260825, {"A": 5, "B": 5})
    assert [c.cid for c in first] == [c.cid for c in second]


def test_a_different_seed_draws_a_different_sample() -> None:
    _found, claims = prohibitions.build_frame()
    a = [c.cid for c in prohibitions.draw(claims, 20260825, {"B": 12})]
    b = [c.cid for c in prohibitions.draw(claims, 1, {"B": 12})]
    assert a != b


def test_a_draw_larger_than_the_stratum_is_a_census_rather_than_an_error() -> None:
    _found, claims = prohibitions.build_frame()
    pool = sum(1 for c in claims if c.stratum == "A")
    drawn = prohibitions.draw(claims, 20260825, {"A": pool + 500})
    assert len(drawn) == pool


def test_the_hand_edits_to_the_population_are_disjoint() -> None:
    added = set(prohibitions.MANUAL_STRATUM_B)
    removed = set(prohibitions.MANUAL_STRATUM_B_EXCLUSIONS)
    assert not (added & removed)
    assert all(reason.strip() for reason in prohibitions.MANUAL_STRATUM_B.values())
    assert all(reason.strip() for reason in prohibitions.MANUAL_STRATUM_B_EXCLUSIONS.values())


def test_check_passes_on_this_tree(capsys: Any) -> None:
    assert prohibitions.main(["--check"]) == 0
    assert "prohibitions OK" in capsys.readouterr().out


def test_check_fails_when_a_hand_added_record_is_not_in_the_document(
    monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    """The mutation that shows ``--check`` can go red where it runs.

    Without this, ``--check`` returning ``0`` is a fact about nothing.
    """
    monkeypatch.setitem(prohibitions.MANUAL_STRATUM_B, "D-9999", "a record that does not exist")
    assert prohibitions.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "D-9999" in out and "FAILED" in out


def test_check_fails_when_the_audit_markers_stop_matching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    root = _tree(tmp_path)
    monkeypatch.setattr(prohibitions, "_DO_NOT", prohibitions.re.compile(r"\*\*Never ever "))
    monkeypatch.setattr(prohibitions, "_TABLE_SECTION", "### nothing matches this")
    monkeypatch.setattr(prohibitions, "_CLOSED_SECTION", "### nor this")
    assert prohibitions.main(["--check", "--root", str(root)]) == 1
    assert "stratum A is empty" in capsys.readouterr().out


def test_the_listing_prints_a_population_size(capsys: Any) -> None:
    assert prohibitions.main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "population:" in out
    assert "census, never sampled" in out
