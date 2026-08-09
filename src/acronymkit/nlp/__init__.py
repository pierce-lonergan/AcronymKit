"""Tier 1 linguistic annotation backends.

The engine resolves exactly one backend at construction time via
:func:`resolve_backend`, which turns a
:class:`~acronymkit.enums.EngineTier` request into a concrete annotator plus
the warnings that describe any degradation:

* :class:`HeuristicBackend` — pure stdlib, always available, fills ``pos`` from
  a suffix table and the categorised stop-word registry.
* :class:`SpacyBackend` — small spaCy pipeline; offset-exact alignment.
* :class:`NltkBackend` — NLTK's averaged perceptron tagger, Penn tags mapped to
  Universal POS.

Importing this package pulls in no optional dependency: spaCy and NLTK are
imported inside functions, and the backend modules are safe to import on a
machine that has neither.
"""

from __future__ import annotations

from .base import BackendUnavailable, NlpBackend, resolve_backend
from .heuristic import HeuristicBackend
from .nltk_backend import NltkBackend
from .spacy_backend import SpacyBackend

__all__ = [
    "BackendUnavailable",
    "HeuristicBackend",
    "NlpBackend",
    "NltkBackend",
    "SpacyBackend",
    "resolve_backend",
]
