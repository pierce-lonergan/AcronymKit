"""Compatibility path for :mod:`acronymkit.catalog.models`.

This module object **is** :mod:`acronymkit.catalog.models`. It does not import
its names, it replaces itself: ``sys.modules[__name__] = _module`` at the bottom
hands the real module back to the import system, which stores whatever is under
this name after execution. So ``acronymkit.governed.models is
acronymkit.catalog.models`` is ``True``, every private helper is reachable
through both paths, and there is exactly one class object per class rather than
two that compare equal.

Re-exporting with ``from ... import *`` would have been shorter and would have
been a different promise: it copies the names in ``__all__`` and drops
everything else, so a caller reaching a private helper through the old path --
which is the kind of caller a compatibility shim exists for -- would get an
``AttributeError`` that reads like the module is broken.

See :mod:`acronymkit.governed` for how long this path is kept.
"""

from __future__ import annotations

import sys

from ..catalog import models as _module

sys.modules[__name__] = _module
