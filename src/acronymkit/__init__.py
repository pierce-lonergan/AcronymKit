"""acronymkit — bi-directional, multi-tiered acronym engine.

One library for the three things production systems do with acronyms:
*generate* them from a phrase, *extract* the ones a document already defines,
and *disambiguate* the ones it does not. Ranking is a single explicit objective
function, ``S(A, T) = alpha * SUM omega + beta * Phi(A) + gamma * Lambda(A)
- delta * Psi(T, A)``, and every result carries the term-by-term breakdown that
produced it.

Example:
    >>> from acronymkit import AcronymEngine, Config
    >>> engine = AcronymEngine(Config(max_candidates=5))
    >>> engine.generate("Portable Document Format").primary_acronym
    'PDF'
    >>> engine.generate_backronym(
    ...     phrase="Next Generation High Performance Storage System",
    ...     target_word="NEXUS",
    ... ).target_word
    'NEXUS'
    >>> pair = engine.extract_definitions(
    ...     "The World Health Organization (WHO) issued guidance."
    ... )[0]
    >>> (pair.short_form, pair.long_form)
    ('WHO', 'World Health Organization')

Governed naming
---------------
:mod:`acronymkit.governed` is a separate capability with its own entry points,
re-exported here for reach. It answers the schema-governance question rather
than the linguistic one: given a bare column token and a vocabulary somebody
has already written down, say what the token means, deterministically, and
record which catalog row said so.

    >>> from acronymkit import GovernedDictionary, expand_identifier
    >>> catalog = GovernedDictionary.from_mapping(
    ...     {"TXN": "Transaction", "ID": "Identifier"}
    ... )
    >>> expand_identifier("TXN_ID", catalog).phrase
    'Transaction Identifier'

``normalize_name`` is :func:`acronymkit.governed.compliance.normalize` under a
qualified name, and the rename is not cosmetic: this package already has a
:func:`acronymkit.tokenizer.normalize`, which NFKC-composes and case-folds
arbitrary text. Read inside its own module the bare verb is unambiguous; read
at the top of the package it would be one of two unrelated normalisations with
no way to tell which. The defining module keeps the short name; the export says
what it normalises. See :data:`_EXPORT_ALIASES`.

Import policy
-------------
Two separate promises, and they are worth keeping apart.

**Purity.** Importing anything in this package pulls in the standard library
and ``pydantic`` and nothing else. spaCy, NLTK, ONNX Runtime, transformers and
``click`` are optional extras imported lazily, inside the functions that need
them, so Tier 0 stays Tier 0 on a bare production image. CI asserts it.

**Cost.** ``import acronymkit`` binds no submodule at all. Every name in
:data:`__all__` is resolved on first attribute access through the module-level
``__getattr__`` of :pep:`562` and then cached in the module globals, so the
second access is an ordinary dictionary hit.

That matters because the DTO layer is Pydantic, and building the core schema
for :class:`~acronymkit.config.Config` alone dominates this package's import
cost. A caller that imports the package for :data:`__version__`, for a type
name under ``typing.TYPE_CHECKING``, or because something else in the process
depends on it should not pay for a schema it never validates against.

**This defers the cost; it does not remove it.** A caller that names
``AcronymEngine`` pays for the DTO layer at that moment instead of at
``import``, and the total to a first result is the same. ``bench/run_micro.py``
therefore records three figures — the bare import, the import of the engine,
and time to first generated result — so that the cheap one cannot be quoted on
its own as a saving that is not there.

:data:`__version__` is deferred on the same principle: reading it costs an
``importlib.metadata`` lookup, which parses distribution metadata with the
``email`` package and is the second-largest thing this package used to import.

Nothing about the public surface changes::

    from acronymkit import AcronymEngine, Config   # works, as before
    import acronymkit
    acronymkit.AcronymEngine                       # works, as before
    from acronymkit import *                       # binds exactly __all__

Static analysis is unaffected: the ``TYPE_CHECKING`` block below holds the real
imports, so mypy, IDEs and :pep:`561` consumers see ordinary re-exports.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # The real imports, for type checkers only. These are what mypy, IDEs and
    # downstream ``py.typed`` consumers resolve; the runtime path is the
    # ``__getattr__`` below. Three lists now describe one surface — this block,
    # ``_EXPORT_SOURCES`` and ``__all__`` — and drift between them is invisible
    # to both mypy and the interpreter, so ``tests/test_package.py`` reads this
    # block with ``ast`` and asserts all three agree.
    from .config import STRATEGY_WEIGHTS, Config, ScoringWeights
    from .diagnostics import capabilities, format_report
    from .disambiguation import ExpansionDictionary
    from .engine import AcronymEngine
    from .enums import (
        CaseStyle,
        EngineTier,
        HyphenPolicy,
        Language,
        MappingKind,
        NumeralPolicy,
        ScoringStrategy,
        StopWordCategory,
        TokenRole,
    )
    from .exceptions import (
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
    from .governed.compliance import is_compliant
    from .governed.compliance import normalize as normalize_name
    from .governed.dictionary import GovernedDictionary
    from .governed.expansion import expand_identifier, expand_token
    from .governed.models import GovernedEntry
    from .governed.naming import to_physical_name
    from .governed.policy import NamingPolicy
    from .models import (
        AcronymCandidate,
        AcronymPair,
        AcronymResult,
        BackronymCandidate,
        BackronymResult,
        BatchResult,
        DisambiguationCandidate,
        DisambiguationResult,
        EngineMetadata,
        ExtractionResult,
        LetterMapping,
        ScoreBreakdown,
        Token,
    )

    #: Installed distribution version; the single source of truth for
    #: ``EngineMetadata.library_version``. Resolved on first access, because
    #: ``importlib.metadata`` parses distribution metadata with the ``email``
    #: package and is not free.
    __version__: str

#: Version reported when the distribution metadata is unavailable, which is the
#: case in an un-installed source checkout.
_FALLBACK_VERSION = "0.3.0"

#: Public name -> the submodule it is resolved from. This is the whole lazy
#: import table; every entry is also in :data:`__all__`, and the reverse holds
#: except for ``__version__``, which is computed rather than imported. The
#: values mirror the module paths in the ``TYPE_CHECKING`` block above one for
#: one, which is what ``tests/test_package.py`` compares them against.
_EXPORT_SOURCES = {
    "STRATEGY_WEIGHTS": "config",
    "capabilities": "diagnostics",
    "format_report": "diagnostics",
    "Config": "config",
    "ScoringWeights": "config",
    "ExpansionDictionary": "disambiguation",
    "AcronymEngine": "engine",
    "CaseStyle": "enums",
    "EngineTier": "enums",
    "HyphenPolicy": "enums",
    "Language": "enums",
    "MappingKind": "enums",
    "NumeralPolicy": "enums",
    "ScoringStrategy": "enums",
    "StopWordCategory": "enums",
    "TokenRole": "enums",
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
    "AcronymCandidate": "models",
    "AcronymPair": "models",
    "AcronymResult": "models",
    "BackronymCandidate": "models",
    "BackronymResult": "models",
    "BatchResult": "models",
    "DisambiguationCandidate": "models",
    "DisambiguationResult": "models",
    "EngineMetadata": "models",
    "ExtractionResult": "models",
    "LetterMapping": "models",
    "ScoreBreakdown": "models",
    "Token": "models",
    "is_compliant": "governed.compliance",
    "normalize_name": "governed.compliance",
    "GovernedDictionary": "governed.dictionary",
    "expand_identifier": "governed.expansion",
    "expand_token": "governed.expansion",
    "GovernedEntry": "governed.models",
    "to_physical_name": "governed.naming",
    "NamingPolicy": "governed.policy",
}

#: Public name -> the name its own module gives it, for the exports whose two
#: spellings differ. Only ``normalize_name`` needs an entry, and the table
#: exists rather than the alias being hard-coded because
#: :data:`_EXPORT_SOURCES` resolves by identical name and silently returning
#: the wrong object is the failure mode a special case here would invite.
#:
#: Renaming on re-export is worth doing sparingly and worth doing here:
#: ``acronymkit.tokenizer.normalize`` already exists and does something else
#: entirely. Exporting the compliance verb as ``normalize`` would mean
#: ``from acronymkit import normalize`` and ``from acronymkit.tokenizer import
#: normalize`` silently shadowing each other in one module, and a reader of
#: either call site having no way to tell which was meant. The defining module
#: keeps the short name; the package exports the qualified one.
_EXPORT_ALIASES = {
    "normalize_name": "normalize",
}

#: Submodules a bare ``import acronymkit`` used to bind as a side effect of the
#: eager re-exports. They stay reachable as attributes so that
#: ``import acronymkit; acronymkit.tokenizer`` keeps working, but they are now
#: imported on demand. ``cli`` and ``serialization`` are deliberately absent
#: because they were never bound this way either: the point is to reproduce the
#: previous attribute surface exactly, not to widen it.
#:
#: ``governed`` is the one entry with no previous surface to reproduce. It is
#: listed because it is a sub-package whose own names are a superset of the
#: eight re-exported here — a caller reaching for ``EntryKind`` or
#: ``canonical_form_score`` has to get at it somehow, and
#: ``acronymkit.governed`` raising ``AttributeError`` after ``import
#: acronymkit`` while ``import acronymkit.governed`` worked would be a
#: distinction nobody can predict from the outside.
_SUBMODULES = frozenset(
    {
        "backronym",
        "batch",
        "config",
        "diagnostics",
        "disambiguation",
        "engine",
        "enums",
        "exceptions",
        "extractor",
        "generator",
        "governed",
        "lexicon",
        "models",
        "nlp",
        "phonetics",
        "resources",
        "scoring",
        "stopwords",
        "tokenizer",
    }
)

__all__ = [
    "STRATEGY_WEIGHTS",
    "AcronymCandidate",
    "AcronymEngine",
    "AcronymKitError",
    "AcronymPair",
    "AcronymResult",
    "BackronymCandidate",
    "BackronymResult",
    "BatchResult",
    "CaseStyle",
    "Config",
    "ConfigurationError",
    "DisambiguationCandidate",
    "DisambiguationResult",
    "EmptyPhraseError",
    "EngineMetadata",
    "EngineTier",
    "ExpansionDictionary",
    "ExtractionResult",
    "GenerationError",
    "GovernedDictionary",
    "GovernedEntry",
    "HyphenPolicy",
    "Language",
    "LetterMapping",
    "LexiconError",
    "MappingKind",
    "NamingPolicy",
    "NoCandidateError",
    "NumeralPolicy",
    "OfflineError",
    "ResourceNotFoundError",
    "ScoreBreakdown",
    "ScoringStrategy",
    "ScoringWeights",
    "StopWordCategory",
    "TierUnavailableError",
    "Token",
    "TokenRole",
    "TokenizationError",
    "__version__",
    "capabilities",
    "expand_identifier",
    "expand_token",
    "format_report",
    "is_compliant",
    "normalize_name",
    "to_physical_name",
]


def _resolve_version() -> str:
    """Return the installed distribution version.

    Returns:
        The version recorded in the distribution metadata, or
        :data:`_FALLBACK_VERSION` in an un-installed source checkout.
    """
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as distribution_version

    try:
        return distribution_version("acronymkit")
    except PackageNotFoundError:  # pragma: no cover - un-installed source checkout
        return _FALLBACK_VERSION


def __getattr__(name: str) -> Any:
    """Resolve a public name, or a submodule, on first access (:pep:`562`).

    The resolved object is written into the module globals, so this runs at
    most once per name and every subsequent access is a normal attribute
    lookup with no function call at all.

    Args:
        name: The attribute being looked up. An export renamed on the way out
            (see :data:`_EXPORT_ALIASES`) is fetched from its module under the
            name that module gives it.

    Returns:
        The exported object, or the submodule.

    Raises:
        AttributeError: If ``name`` is neither an export nor a submodule. The
            message matches CPython's own, so nothing that inspects the package
            can tell a lazy miss from an ordinary one.
    """
    if name == "__version__":
        value: Any = _resolve_version()
    elif name in _EXPORT_SOURCES:
        module = import_module(f".{_EXPORT_SOURCES[name]}", __name__)
        value = getattr(module, _EXPORT_ALIASES.get(name, name))
    elif name in _SUBMODULES:
        value = import_module(f".{name}", __name__)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return the full attribute surface, resolved or not, for ``dir()``."""
    return sorted(set(globals()) | set(__all__) | _SUBMODULES)
