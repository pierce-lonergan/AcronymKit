"""Compatibility path for :mod:`acronymkit.nlp.extractor` -- candidate extraction, parenthetical matching and the backwards long-form scan.

The definitions moved when the package was split at the **lexer contract seam**.
It is the prose half's tokenizer contract end to end: it treats punctuation as
a clause boundary, leans on whitespace, and pulls definitions out of running
morphology. Run it over a schema identifier and the characters it discards are
the ones the identifier was carrying meaning in.

**This module object IS :mod:`acronymkit.nlp.extractor`.** It does not re-export
its names, it replaces itself: ``sys.modules[__name__] = _module`` hands the
real module back to the import system, which stores whatever is under this name
after execution. So ``acronymkit.extractor is acronymkit.nlp.extractor`` is ``True``,
every private helper is reachable through both paths, and there is exactly one
class object per class rather than two that compare equal. ``from ... import *``
would have been shorter and would have dropped every private name -- which is
precisely what a caller who reaches for one through the old path would notice.

``acronymkit.extractor`` is a public import path that ``README.md``, ``docs/`` and
``docs/DECISIONS.md`` name, and the last of those is a file this workstream may
not edit. **How long it is kept: through the whole of the ``0.x`` line**, with
removal requiring a major version and a ``DeprecationWarning`` announced at
least one minor release ahead. See ``CHANGELOG.md``.
"""

from __future__ import annotations

import sys

from .nlp import extractor as _module

sys.modules[__name__] = _module
