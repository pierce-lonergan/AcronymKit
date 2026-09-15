"""The one version literal, for the case where distribution metadata is absent.

``pyproject.toml``'s ``[project] version`` is the version. ``__version__``
resolves from installed distribution metadata at runtime, so in every
environment this package is actually used in, nothing here is read.

**This module exists because that made two constants invisible.**
``docs/RELEASE_CHECKLIST.md`` section 4 states that ``pyproject.toml`` is "the
only place the version is written ... so there is no second constant to bump and
no risk of the two drifting". There were two more:
``acronymkit/__init__.py`` held ``"0.3.0"`` and ``acronymkit/engine.py`` held
``"0.1.0"``, and **they already disagreed with each other before 0.4.0 existed.**

``tests/test_engine.py`` asserts ``metadata.library_version ==
acronymkit.__version__``, which those two values violate — and it passes, in
every checkout and every CI cell, because both are installed and the metadata
path wins. A check that cannot fail where it runs is this repository's signature
defect and it was sitting inside the release procedure that denies the constant
exists.

So: one constant, read by both, and
``tests/test_version_fallback.py`` drives the path with the metadata removed so
the agreement is asserted rather than assumed.
"""

from __future__ import annotations

#: Reported as ``__version__`` and as ``library_version`` when
#: ``importlib.metadata`` cannot find the distribution — an un-installed source
#: checkout, and nothing else.
#:
#: Bump it with ``pyproject.toml``. The test named above fails if the two
#: disagree, which is the whole reason it is one name.
FALLBACK_VERSION = "0.4.0"

__all__ = ["FALLBACK_VERSION"]
