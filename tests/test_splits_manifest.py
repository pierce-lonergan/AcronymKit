"""``bench/splits.toml`` must parse, because a rule nothing reads is a habit.

The project's second operating rule is that train/test separation is declared
before any knob is touched, and ``bench/splits.toml`` is where that declaration
lives. It was not valid TOML: a ``status`` key was written twice inside
``[corpora.plod]`` while adding a correction block, and nothing noticed for
months because nothing in the repository ever loaded the file. Eleven places
cite it in prose; zero parse it.

That is the failure worth guarding against, and it is not really about TOML. A
governance artifact that no tool reads degrades into a document people believe
is enforced. This test makes the file load, and checks the fields the rule
actually depends on, so a corpus cannot be registered without saying what it is
for and what its licence permits.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SPLITS = REPO_ROOT / "bench" / "splits.toml"

#: Every corpus must declare these. ``role`` is what the headline rule keys on;
#: ``licence`` is what decides whether a corpus may be shipped or only measured
#: against, a distinction this project has already got wrong twice.
_REQUIRED = ("role", "task", "licence")

#: The only roles the policy recognises. A typo here would silently exempt a
#: corpus from the headline rule.
_ROLES = {"tuning", "held_out"}


def _load() -> dict:
    """Parse the manifest, or fail with the reason."""
    if sys.version_info >= (3, 11):
        import tomllib
    else:  # pragma: no cover - 3.9/3.10 path
        tomllib = pytest.importorskip("tomli", reason="tomllib is 3.11+; tomli not installed")
    with SPLITS.open("rb") as handle:
        return tomllib.load(handle)


@pytest.mark.skipif(not SPLITS.is_file(), reason="not a source checkout")
def test_the_splits_manifest_parses() -> None:
    """The file the train/test rule rests on must be machine-readable."""
    document = _load()

    assert document.get("corpora"), "no corpora declared; the manifest guards nothing"


@pytest.mark.skipif(not SPLITS.is_file(), reason="not a source checkout")
def test_every_corpus_declares_role_task_and_licence() -> None:
    """A corpus with no declared role is exempt from the rule by accident.

    Licence is required for the same reason: this project has twice recorded a
    corpus as more permissive than it is, and both times the correction came
    from a person reading the terms rather than from anything automatic.
    """
    corpora = _load()["corpora"]

    missing = {
        name: [field for field in _REQUIRED if not spec.get(field)]
        for name, spec in corpora.items()
        if any(not spec.get(field) for field in _REQUIRED)
    }
    assert not missing, f"corpora missing required declarations: {missing}"

    bad_roles = {name: spec["role"] for name, spec in corpora.items() if spec["role"] not in _ROLES}
    assert not bad_roles, f"unrecognised roles (expected {sorted(_ROLES)}): {bad_roles}"
