"""Compatibility path. The hierarchy now lives in :mod:`acronymkit.core.exceptions`.

``acronymkit.exceptions`` is a **public import path with a documented API**:
``docs/`` names it, the ``README`` names it, and every integrator who installed
the single ``except acronymkit.exceptions.AcronymKitError`` clause the module
docstring recommends imports it by this name. It therefore does not move; the
*definitions* moved to :mod:`acronymkit.core.exceptions` when the package was
split at the lexer contract seam, and this module re-exports them.

**These are the same objects, not copies.** ``acronymkit.exceptions.TokenizationError
is acronymkit.core.exceptions.TokenizationError`` is ``True``, so an ``except``
clause written against either path catches an exception raised through the
other. A shim that rebound names to fresh classes would be worse than a break,
because it would fail silently at the one moment an integrator needs it.

What *did* change: ``__module__`` on every class here is now
``acronymkit.core.exceptions``, so an uncaught traceback prints
``acronymkit.core.exceptions.ConfigurationError`` where it used to print
``acronymkit.exceptions.ConfigurationError``. Nothing in this package matches on
that string, and it is stated here rather than discovered in a log.

**How long this path is kept:** through the whole of the ``0.x`` line, and
removal requires a major version and a deprecation cycle announced one minor
release ahead. No ``DeprecationWarning`` is emitted today, deliberately: this
package's own modules would be the loudest emitters of it and a warning nobody
can act on is noise. See ``CHANGELOG.md`` and ``docs/ARCHITECTURE.md``.
"""

from __future__ import annotations

from .core.exceptions import (
    AcronymKitError,
    ConfigurationError,
    EmptyPhraseError,
    GenerationError,
    LexiconError,
    NoCandidateError,
    OfflineError,
    ResourceNotFoundError,
    TierUnavailableError,
    TokenizationError,
)

__all__ = [
    "AcronymKitError",
    "ConfigurationError",
    "EmptyPhraseError",
    "GenerationError",
    "LexiconError",
    "NoCandidateError",
    "OfflineError",
    "ResourceNotFoundError",
    "TierUnavailableError",
    "TokenizationError",
]
