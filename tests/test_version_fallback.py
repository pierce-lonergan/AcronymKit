"""The version fallback, driven with the distribution metadata removed.

``tests/test_engine.py`` asserts ``metadata.library_version ==
acronymkit.__version__``. That assertion was satisfied by two constants that did
**not** agree -- ``acronymkit/__init__.py`` held ``"0.3.0"`` and
``acronymkit/engine.py`` held ``"0.1.0"`` -- because in every checkout and every
CI cell the package is installed, the ``importlib.metadata`` path wins, and
neither constant is read.

**A check that cannot fail where it runs is this repository's signature defect**,
and this one was sitting inside the release procedure that denies the constants
exist: ``docs/RELEASE_CHECKLIST.md`` section 4 says ``pyproject.toml`` is "the
only place the version is written ... so there is no second constant to bump and
no risk of the two drifting". There were two, and they had already drifted from
each other before ``0.4.0``.

This module is the environment those constants are for. It removes the metadata
and asserts what the library then reports, so the agreement is measured rather
than assumed.

**What it does not do.** It does not check that ``FALLBACK_VERSION`` equals
``pyproject.toml``'s version -- that is the next test in this file, and it is a
separate claim: one is "the two code paths agree with each other", the other is
"they agree with the release". The first can hold while the second fails, which
is precisely the state this file was written to end.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import sys
from pathlib import Path
from typing import Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"

_NO_PARSER = sys.version_info < (3, 11) and importlib.util.find_spec("tomli") is None


def _declared_version() -> str:
    """``pyproject.toml``'s ``[project] version``, parsed rather than grepped."""
    if sys.version_info >= (3, 11):
        import tomllib
    else:  # pragma: no cover - 3.9/3.10 matrix cells only
        import tomli as tomllib  # type: ignore[no-redef]

    with PYPROJECT.open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


@pytest.fixture()
def metadata_absent(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Make ``importlib.metadata.version`` behave as it does un-installed.

    Patching the function rather than uninstalling the package is deliberate:
    the alternative is a subprocess in a scratch tree, which is what the
    ``build`` CI job already does to the whole distribution. What is under test
    here is one branch, and the branch is selected by this exception.
    """

    def _raise(name: str) -> str:
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", _raise)
    yield


def test_the_two_fallback_paths_report_the_same_version(
    metadata_absent: None,
) -> None:
    """``__version__`` and ``library_version`` must agree with no metadata.

    This is the assertion ``tests/test_engine.py`` believed it was making.
    Before the shared constant, it would have compared ``"0.3.0"`` against
    ``"0.1.0"`` -- and it never ran, because the metadata path always won.
    """
    import acronymkit
    from acronymkit import engine
    from acronymkit.core.version import FALLBACK_VERSION

    reported = acronymkit._resolve_version()  # type: ignore[attr-defined]
    engine_reported = engine._library_version()  # type: ignore[attr-defined]

    assert reported == FALLBACK_VERSION, (
        f"acronymkit reports {reported!r} with no distribution metadata, against "
        f"FALLBACK_VERSION {FALLBACK_VERSION!r}"
    )

    # `engine._library_version` BORROWS `__version__` rather than querying the
    # metadata a second time, so with the metadata gone it returns whatever the
    # package resolved -- which is why the two constants disagreeing was a
    # fallback-of-a-fallback rather than a live wrong answer. Both halves are
    # asserted anyway: the borrowed value, and engine's own constant, because
    # the constant is what fires on a partial import and nothing else reaches it.
    assert engine_reported == reported, (
        f"engine reports {engine_reported!r} and the package {reported!r}; "
        f"engine borrows __version__, so a difference means the borrow broke"
    )
    assert engine._FALLBACK_VERSION == FALLBACK_VERSION, (  # type: ignore[attr-defined]
        "engine's own fallback, which fires only on a partial import, no longer "
        "matches the shared constant -- the exact drift this file exists for"
    )


@pytest.mark.skipif(_NO_PARSER, reason="tomllib is 3.11+; tomli not installed")
@pytest.mark.skipif(not PYPROJECT.is_file(), reason="not a source checkout")
def test_the_fallback_agrees_with_the_version_being_released() -> None:
    """The fallback must equal ``pyproject.toml``, or a release drifts from it.

    A separate claim from the one above, and the one that actually goes stale:
    the two code paths can agree with each other perfectly while both disagree
    with the version on the tin. That is the state ``0.4.0`` was prepared in --
    ``pyproject.toml`` said ``0.4.0`` and the two constants said ``0.3.0`` and
    ``0.1.0``.

    It fails on the release commit that forgets the bump, which is the only
    moment it can be useful.
    """
    from acronymkit.core.version import FALLBACK_VERSION

    declared = _declared_version()
    assert declared == FALLBACK_VERSION, (
        f"acronymkit.core.version.FALLBACK_VERSION is {FALLBACK_VERSION!r} and "
        f"pyproject.toml declares {declared!r}. Bump them together: the fallback is "
        f"what an un-installed checkout reports as its own version."
    )


def test_the_constant_lives_in_exactly_one_place() -> None:
    """No module may carry its own version literal again.

    The defect was two constants, not two wrong values, so the guard is on the
    shape. A grep would miss a literal spelled differently; this reads the
    source of the two modules that used to hold one and requires the shared
    name.
    """
    for relative in ("src/acronymkit/__init__.py", "src/acronymkit/engine.py"):
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "FALLBACK_VERSION" in source, f"{relative} no longer references the constant"
        assert '_FALLBACK_VERSION = "' not in source, (
            f"{relative} has reintroduced its own version literal. There is one "
            f"constant, in acronymkit.core.version, and two of these drifted apart "
            f"before anybody noticed because the metadata path always wins."
        )
