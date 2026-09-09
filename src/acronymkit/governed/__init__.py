"""Compatibility path. The subsystem now lives in :mod:`acronymkit.catalog`.

Why the path did not simply move
--------------------------------
``acronymkit.governed`` is a **public import path with a documented API**. It is
named in ``README.md``, in ``docs/GOVERNED_NAMING.md``, in
``docs/QUICKSTART_GOVERNED.md``, in the CLI's own help, and in
``docs/DECISIONS.md`` -- a file the recorder owns and nobody else may edit, which
means a break here would leave the project's own decision record citing an
import path that no longer exists. Moving it outright would break every caller
and falsify a document this workstream is forbidden to correct. So the path
stays and the definitions moved.

Why the definitions moved
-------------------------
The package was split at the **lexer contract seam**. This half operates on
rigid identifier boundaries, treats ``#``, ``%``, ``_``, ``:`` and ``/`` as
semantic tokens, and enforces physical column constraints; the prose half
(:mod:`acronymkit.nlp`) treats punctuation as a clause boundary and leans on
whitespace. Each tokenizer destroys the other's input -- measured as character
loss on ``14.6560`` % of distinct Socrata captions and ``36.0072`` % of distinct
SEC XBRL labels. That is a package boundary rather than a setting, and
``catalog`` is what the boundary is named after: the thing this half is *about*
is a vocabulary somebody else governs.

What ``governed`` meant is not lost. It is the **posture** -- refuse rather than
guess -- and it is still the name of every type here
(:class:`~acronymkit.catalog.dictionary.GovernedDictionary`,
:class:`~acronymkit.catalog.models.GovernedEntry`,
:class:`~acronymkit.catalog.namer.GovernedNamer`), of the documentation page,
and of every ``governed_*`` run id in ``bench/results.json``. **No run id moved**,
because a run id is the identity of a measurement and renaming one silently
re-points every citation of it.

What this shim guarantees, mechanically
---------------------------------------
Three things, each checked by ``tests/test_architecture_boundaries.py`` rather
than asserted here:

1. **Every public name resolves.** ``acronymkit.governed.__all__`` is
   ``acronymkit.catalog.__all__``, element for element.
2. **They are the same objects, not copies.** ``acronymkit.governed.expand_identifier
   is acronymkit.catalog.expand_identifier``. Identity and not equality: a shim
   that rebound names to fresh classes would satisfy every ``==`` in the suite
   and fail the first time somebody wrote ``except`` or ``isinstance`` across
   the two paths.
3. **Every submodule resolves, and is the same module object.**
   ``import acronymkit.governed.tokenizer`` works, and
   ``acronymkit.governed.tokenizer is acronymkit.catalog.tokenizer``. The
   thirteen files beside this one exist for that: each replaces itself in
   ``sys.modules``, so there is one module object per submodule rather than two
   holding equal-looking copies of the same classes.

What it does **not** do: emit a ``DeprecationWarning``. Deliberately. Nothing in
this package imports through this path any more -- every module in ``src``,
``tests``, ``bench`` and ``tools`` was moved to ``acronymkit.catalog`` in the
same change -- so the only emitter would be an external caller, who cannot act
on it until the deprecation cycle below actually opens.

How long this path is kept
--------------------------
**Through the whole of the ``0.x`` line.** Removal requires a major version, and
a ``DeprecationWarning`` announced in a minor release at least one release
ahead of it. That is written down in ``CHANGELOG.md`` under the entry that
introduced the split, and it is a commitment rather than an intention: a
compatibility shim with no stated end date is a second public API somebody has
to maintain forever without ever having decided to.

Import cost
-----------
Unchanged, and it has to be. ``import acronymkit.governed`` binds no submodule:
every name resolves on first attribute access through :pep:`562`, exactly as it
did before the move, so a caller who only wants
:class:`~acronymkit.catalog.enums.EntryKind` still never pays for the Pydantic
schemas behind :class:`~acronymkit.catalog.dictionary.GovernedDictionary`.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

#: Submodules reachable through this path. Each has a one-line file beside this
#: one that replaces itself with the ``acronymkit.catalog`` module of the same
#: name, so that ``import acronymkit.governed.tokenizer`` and
#: ``from acronymkit.governed.tokenizer import split_identifier`` both work and
#: both reach the same module object as the ``catalog`` path does.
_SUBMODULES = frozenset(
    {
        "audit",
        "compliance",
        "dictionary",
        "enums",
        "expansion",
        "gap",
        "loaders",
        "models",
        "namer",
        "naming",
        "policy",
        "scoring",
        "tokenizer",
    }
)


def __getattr__(name: str) -> Any:
    """Resolve any public name, or any submodule, from :mod:`acronymkit.catalog`.

    Delegating to ``catalog``'s own :pep:`562` ``__getattr__`` rather than
    holding a second copy of its export table is the point: two tables drift,
    and a shim that has stopped re-exporting one name is the failure this whole
    arrangement exists to prevent.

    Args:
        name: The attribute being looked up.

    Returns:
        The object ``acronymkit.catalog`` resolves under that name, or the
        submodule.

    Raises:
        AttributeError: If ``acronymkit.catalog`` has no such attribute. The
            message names *this* module, so a caller on the old path gets the
            error they would have got before the move rather than one pointing
            at a package they did not import.
    """
    if name in _SUBMODULES:
        value: Any = import_module(f".{name}", __name__)
    else:
        catalog = import_module("acronymkit.catalog")
        try:
            value = getattr(catalog, name)
        except AttributeError:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return the same attribute surface :mod:`acronymkit.catalog` offers."""
    catalog = import_module("acronymkit.catalog")
    return sorted(set(globals()) | set(dir(catalog)) | _SUBMODULES)
