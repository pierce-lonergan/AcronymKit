"""Compatibility path for :mod:`acronymkit.nlp.tokenizer` -- prose tokenisation: the chunker the whole prose half is built on.

The definitions moved when the package was split at the **lexer contract seam**.
**This is one half of the contract collision the package was split over.** It
and :mod:`acronymkit.catalog.tokenizer` are both called `tokenizer`, both take
a string, and destroy each other's input: this one treats `_`, `:` and `/` as
separators to be discarded and NFKC-normalises what is left, while the
identifier tokenizer treats them as semantic and may not lose a character.
Neither is a setting on the other.

**This module object IS :mod:`acronymkit.nlp.tokenizer`.** It does not re-export
its names, it replaces itself: ``sys.modules[__name__] = _module`` hands the
real module back to the import system, which stores whatever is under this name
after execution. So ``acronymkit.tokenizer is acronymkit.nlp.tokenizer`` is ``True``,
every private helper is reachable through both paths, and there is exactly one
class object per class rather than two that compare equal. ``from ... import *``
would have been shorter and would have dropped every private name -- which is
precisely what a caller who reaches for one through the old path would notice.

``acronymkit.tokenizer`` is a public import path that ``README.md``, ``docs/`` and
``docs/DECISIONS.md`` name, and the last of those is a file this workstream may
not edit. **How long it is kept: through the whole of the ``0.x`` line**, with
removal requiring a major version and a ``DeprecationWarning`` announced at
least one minor release ahead. See ``CHANGELOG.md``.
"""

from __future__ import annotations

import sys

from .nlp import tokenizer as _module

sys.modules[__name__] = _module
