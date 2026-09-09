"""The leaf: what both halves of this package may depend on, and nothing else.

Why this package exists
-----------------------
``acronymkit`` contains two tokenizers whose contracts collide, and the
collision is measured rather than asserted. Prose tokenisation treats
punctuation as a clause boundary, leans on whitespace, pulls parentheticals out
of running morphology and tolerates non-ASCII. Identifier tokenisation operates
on rigid boundaries, treats ``#``, ``%``, ``_``, ``:`` and ``/`` as *semantic*
tokens, and enforces physical column constraints. Run either one over the
other's input and characters are destroyed: ``14.6560`` % of distinct Socrata
captions and ``36.0072`` % of distinct SEC XBRL labels lose characters that way
(``docs/DECISIONS.md``, the B1 finding). A tokenizer whose input the sibling
tokenizer damages is not a setting; it is a package boundary, and this is the
one package that sits below both of them.

**Both figures are quoted from a fenced block and neither is gated.** They live
in ``docs/DECISIONS.md`` and ``docs/GOVERNED_NAMING.md`` inside fenced code
blocks, which ``tools/check_claims.py`` cannot read -- D-112 records that as the
largest structural hole in that gate's coverage -- and no run id in
``bench/results.json`` backs either. They are the measurement this split rests
on, so they are repeated here; saying where they come from and what does not
check them is the difference between quoting a measurement and laundering one.

So :mod:`acronymkit.core` is what is left when everything lexical is removed:

* **no regular expressions** -- not compiled, not inline, not imported;
* **no lexical assets** -- no stop-word list, no lexicon, no n-gram model, no
  file under ``resources/``;
* **no string normalisation** -- no NFKC, no case-folding, no accent handling.

What is here instead is arithmetic and vocabulary that neither half can damage:

* :mod:`~acronymkit.core.exceptions` -- the exception hierarchy every module in
  this package raises from, including :class:`~acronymkit.core.exceptions.TokenizationError`,
  which both tokenizers raise and neither owns.
* :mod:`~acronymkit.core.conformal` -- nonconformity scoring and split-conformal
  risk arithmetic. Sorting, an order statistic and a comparison; the objects it
  scores are duck-typed, so the module reads ``.candidates`` and ``.score``
  without importing the class that supplies them.
* :mod:`~acronymkit.core.spans` -- immutable half-open character coordinates,
  the one vocabulary the two halves genuinely share.

The leaf rule, and how it is enforced
-------------------------------------
**This package imports from neither sibling.** Not from
:mod:`acronymkit.catalog`, not from :mod:`acronymkit.nlp`, and not under
``typing.TYPE_CHECKING`` either -- a deferred import is still an edge in the
dependency graph, and a type annotation is exactly how a leaf stops being one
without anybody noticing.

That is checked rather than promised: ``tests/test_architecture_boundaries.py``
walks the **abstract syntax tree** of every module in this package and rejects
the edge wherever it appears -- ``from acronymkit.nlp import x``,
``import acronymkit.catalog as c``, a deferred import inside a function body, a
``TYPE_CHECKING`` block, and ``importlib.import_module`` on a literal. A grep
over ``from acronymkit.nlp`` sees the first of those five and misses four.

What is *not* forbidden here is an import from the modules that are in neither
half -- and at the time of writing there is exactly one such edge and it is
deferred: :mod:`~acronymkit.core.conformal` names
:class:`~acronymkit.models.DisambiguationResult` under ``TYPE_CHECKING`` for its
annotations, and reads that object entirely through duck-typed attribute access
at run time. So ``import acronymkit.core`` binds no sibling and no DTO layer.
The boundary test states that exemption explicitly rather than leaving it to be
inferred from a passing run.

Import cost
-----------
Same promise as the parent package, one level down: ``import acronymkit.core``
binds no submodule. Every name in :data:`__all__` resolves on first attribute
access through the module-level ``__getattr__`` of :pep:`562` and is then cached
in the module globals.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

#: Public name -> the submodule that defines it. The lazy ``__getattr__``
#: below is driven by this table; every entry is also in :data:`__all__`, and
#: the reverse holds.
_EXPORT_SOURCES = {
    "ASSUMPTION": "conformal",
    "ConformalDecision": "conformal",
    "ConformalGate": "conformal",
    "GroupCalibration": "conformal",
    "arity_group": "conformal",
    "group_counts": "conformal",
    "nonconformity": "conformal",
    "smallest_calibration_size": "conformal",
    "AcronymKitError": "exceptions",
    "ConfigurationError": "exceptions",
    "EmptyPhraseError": "exceptions",
    "GenerationError": "exceptions",
    "LexiconError": "exceptions",
    "NoCandidateError": "exceptions",
    "OfflineError": "exceptions",
    "ResourceNotFoundError": "exceptions",
    "TierUnavailableError": "exceptions",
    "TokenizationError": "exceptions",
    "Span": "spans",
}

#: Submodules reachable as attributes of this package, so that
#: ``import acronymkit.core; acronymkit.core.spans`` works without the package
#: having imported any of them up front.
_SUBMODULES = frozenset({"conformal", "exceptions", "spans"})

__all__ = [
    "ASSUMPTION",
    "AcronymKitError",
    "ConfigurationError",
    "ConformalDecision",
    "ConformalGate",
    "EmptyPhraseError",
    "GenerationError",
    "GroupCalibration",
    "LexiconError",
    "NoCandidateError",
    "OfflineError",
    "ResourceNotFoundError",
    "Span",
    "TierUnavailableError",
    "TokenizationError",
    "arity_group",
    "group_counts",
    "nonconformity",
    "smallest_calibration_size",
]


def __getattr__(name: str) -> Any:
    """Resolve a public name, or a submodule, on first access (:pep:`562`).

    Args:
        name: The attribute being looked up.

    Returns:
        The exported object, or the submodule.

    Raises:
        AttributeError: If ``name`` is neither an export nor a submodule. The
            message matches CPython's own, so nothing that inspects the package
            can tell a lazy miss from an ordinary one.
    """
    if name in _EXPORT_SOURCES:
        value: Any = getattr(import_module(f".{_EXPORT_SOURCES[name]}", __name__), name)
    elif name in _SUBMODULES:
        value = import_module(f".{name}", __name__)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return the full attribute surface, resolved or not, for ``dir()``."""
    return sorted(set(globals()) | set(__all__) | _SUBMODULES)
