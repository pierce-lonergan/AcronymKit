"""Compatibility path for :mod:`acronymkit.nlp.propagation` -- document-scope propagation of a committed short form (A2).

The definitions moved when the package was split at the **lexer contract seam**.
It reasons about occurrences in running text, which is a prose-half
commitment: `whole-token occurrence` is a statement about word boundaries in a
document, and a column identifier has none.

**This module object IS :mod:`acronymkit.nlp.propagation`.** It does not re-export
its names, it replaces itself: ``sys.modules[__name__] = _module`` hands the
real module back to the import system, which stores whatever is under this name
after execution. So ``acronymkit.propagation is acronymkit.nlp.propagation`` is ``True``,
every private helper is reachable through both paths, and there is exactly one
class object per class rather than two that compare equal. ``from ... import *``
would have been shorter and would have dropped every private name -- which is
precisely what a caller who reaches for one through the old path would notice.

``acronymkit.propagation`` is a public import path that ``README.md``, ``docs/`` and
``docs/DECISIONS.md`` name, and the last of those is a file this workstream may
not edit. **How long it is kept: through the whole of the ``0.x`` line**, with
removal requiring a major version and a ``DeprecationWarning`` announced at
least one minor release ahead. See ``CHANGELOG.md``.
"""

from __future__ import annotations

import sys

from .nlp import propagation as _module

sys.modules[__name__] = _module
