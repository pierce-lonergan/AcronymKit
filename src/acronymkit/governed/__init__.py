"""Governed naming: deterministic expansion of an identifier against a catalog.

Given a bare database column token — ``TXN_ID``, ``APPLNT_VERIF_DT`` — and a
governed vocabulary, return "Transaction Identifier", every time, with a record
of which catalog entry produced each word. And back the other way: turn a
logical name into the governed physical name, and check whether a name someone
else wrote conforms. One package owns *expand* ⇄ *canonicalise* ⇄ *verify* over
one vocabulary, so the three directions cannot disagree with each other.

This is not disambiguation, and the difference is the point
-----------------------------------------------------------
A disambiguator answers "which of these expansions does this *sentence* mean?"
and needs the sentence. A column name is not a sentence. There is no
surrounding prose, no document, no corpus — there is one token, and the answer
has to come from somewhere else.

In a governed setting it already has. Someone wrote the standard down. The
catalog *is* the ground truth, so reproducing what it says is not a weaker
substitute for a model, it is the only defensible answer: a model that mostly
agreed with the standard would still disagree with it sometimes, nobody could
say in advance when, and every disagreement would be the library overruling a
decision a data-governance function already made and signed off. So this
subsystem does not infer, learn or approximate. Where the catalog is silent it
says so and stops.

Three properties, and every design choice here serves them
----------------------------------------------------------
**The dictionary is the ground truth.** Nothing is guessed. An unknown token is
reported as unknown, with ``is_known=False`` and zero confidence, never
approximated into something that looks like an answer. The statistical tier
exists behind an explicit opt-in
(:meth:`~acronymkit.governed.policy.NamingPolicy.neural_optin`) and may only
ever speak for tokens the catalog is silent about.

**Context-free.** The input is one token or one identifier. No sentence, no
document, no corpus, and therefore no way for surrounding text to change what a
token resolves to. The same token under the same vocabulary and policy resolves
the same way in every row of a million-row table.

**Auditable.** Every expanded token carries where its answer came from
(:class:`~acronymkit.governed.enums.ExpansionSource`), which catalog row
produced it (``entry_id``), how far the catalog stands behind it
(``confidence``) and what it was chosen over (``beat``). A reviewer can tell a
decision from a coincidence without re-running anything.

Resolution precedence
---------------------
One order, highest first, applied to every token::

    1. custom overlay      -> ExpansionSource.CUSTOM
    2. entry pin           -> PINNED
    3. entry canonical     -> APPROVED if keep_as_abbrev, else GOVERNED
    4. allow-list only     -> APPROVED, and the expansion is the token itself
    5. collision, no pin   -> SCORED, settled by canonical_form_score
    6. nothing matched     -> PASSTHROUGH, Title Case, is_known False

What is *not* claimed
---------------------
That a governed hit resolves from the dictionary under every policy is an
**invariant, true by construction**, not a measurement. A lookup table returns
what is in the lookup table; putting a percentage next to that would be
dressing a tautology up as a result. It is tested as an invariant and no figure
is attached to it anywhere.
:meth:`~acronymkit.governed.policy.NamingPolicy.frequency_baseline` is likewise
a contrast arm on fixture tokens chosen to make two rules disagree — it is not a
benchmark and nothing measured on it transfers to a corpus.

Import policy
-------------
Same two promises as the parent package. Nothing here imports anything outside
the standard library and ``pydantic``, so a Tier 0 image stays Tier 0. And
``import acronymkit.governed`` binds no submodule: every name below is resolved
on first attribute access through the module-level ``__getattr__`` of
:pep:`562` and then cached in the module globals, so a caller that only wants
:class:`~acronymkit.governed.enums.EntryKind` never pays for the Pydantic
schemas behind :class:`~acronymkit.governed.dictionary.GovernedDictionary`.

Worked examples throughout this package use a fictional catalog, **Northwind
Data Standards** (``NDS``), with synthetic entry ids (``NDS-<TOKEN>``) and term
ids (``TRM-<6 digits>``). Nothing here describes a real organisation's standard.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # The real imports, for type checkers only. mypy, IDEs and :pep:`561`
    # consumers resolve these; an actual attribute access resolves the
    # ``_EXPORT_SOURCES`` table below. The two lists describe one surface and
    # can drift silently, so they are written next to each other deliberately.
    from .audit import (
        CatalogSuggestion,
        CorpusAudit,
        FindingTally,
        IdentifierAudit,
        RoundTripBreak,
        UnknownToken,
        audit_identifiers,
        render_audit,
        suggest_catalog_additions,
    )
    from .compliance import is_compliant, normalize
    from .dictionary import GovernedDictionary
    from .enums import (
        ComplianceReasonCode,
        EntryKind,
        ExpansionSource,
        ResolutionMode,
        UnknownPolicy,
        Verdict,
    )
    from .expansion import expand_identifier, expand_token
    from .loaders import (
        BUNDLE_FILES,
        load_bundle,
        load_csv,
        load_long_to_short_csv,
        load_term_index_csv,
    )
    from .models import (
        ComplianceReason,
        ComplianceResult,
        GovernedEntry,
        IdentifierExpansion,
        PhysicalName,
        PhysicalToken,
        TokenExpansion,
    )
    from .namer import GovernedNamer
    from .naming import to_physical_name
    from .policy import NamingPolicy
    from .scoring import canonical_form_score, score_breakdown
    from .tokenizer import (
        ACCOUNTED_SEPARATORS,
        IdentifierParts,
        split_identifier,
        split_identifier_parts,
        strip_qualifier,
    )

#: Public name -> the submodule that defines it. This is the whole lazy import
#: table; every entry is also in :data:`__all__`, and the reverse holds.
_EXPORT_SOURCES = {
    "CatalogSuggestion": "audit",
    "CorpusAudit": "audit",
    "FindingTally": "audit",
    "IdentifierAudit": "audit",
    "RoundTripBreak": "audit",
    "UnknownToken": "audit",
    "audit_identifiers": "audit",
    "render_audit": "audit",
    "suggest_catalog_additions": "audit",
    "is_compliant": "compliance",
    "normalize": "compliance",
    "GovernedDictionary": "dictionary",
    "ComplianceReasonCode": "enums",
    "EntryKind": "enums",
    "ExpansionSource": "enums",
    "ResolutionMode": "enums",
    "UnknownPolicy": "enums",
    "Verdict": "enums",
    "expand_identifier": "expansion",
    "expand_token": "expansion",
    "BUNDLE_FILES": "loaders",
    "load_bundle": "loaders",
    "load_csv": "loaders",
    "load_long_to_short_csv": "loaders",
    "load_term_index_csv": "loaders",
    "ComplianceReason": "models",
    "ComplianceResult": "models",
    "GovernedEntry": "models",
    "IdentifierExpansion": "models",
    "PhysicalName": "models",
    "PhysicalToken": "models",
    "TokenExpansion": "models",
    "GovernedNamer": "namer",
    "to_physical_name": "naming",
    "NamingPolicy": "policy",
    "canonical_form_score": "scoring",
    "score_breakdown": "scoring",
    "ACCOUNTED_SEPARATORS": "tokenizer",
    "IdentifierParts": "tokenizer",
    "split_identifier": "tokenizer",
    "split_identifier_parts": "tokenizer",
    "strip_qualifier": "tokenizer",
}

#: Submodules reachable as attributes of this package, so that
#: ``import acronymkit.governed; acronymkit.governed.tokenizer`` works without
#: the package having imported any of them up front.
_SUBMODULES = frozenset(
    {
        "audit",
        "compliance",
        "dictionary",
        "enums",
        "expansion",
        "loaders",
        "models",
        "namer",
        "naming",
        "policy",
        "scoring",
        "tokenizer",
    }
)

__all__ = [
    "ACCOUNTED_SEPARATORS",
    "BUNDLE_FILES",
    "CatalogSuggestion",
    "ComplianceReason",
    "ComplianceReasonCode",
    "ComplianceResult",
    "CorpusAudit",
    "EntryKind",
    "ExpansionSource",
    "FindingTally",
    "GovernedDictionary",
    "GovernedEntry",
    "GovernedNamer",
    "IdentifierAudit",
    "IdentifierExpansion",
    "IdentifierParts",
    "NamingPolicy",
    "PhysicalName",
    "PhysicalToken",
    "ResolutionMode",
    "RoundTripBreak",
    "TokenExpansion",
    "UnknownPolicy",
    "UnknownToken",
    "Verdict",
    "audit_identifiers",
    "canonical_form_score",
    "expand_identifier",
    "expand_token",
    "is_compliant",
    "load_bundle",
    "load_csv",
    "load_long_to_short_csv",
    "load_term_index_csv",
    "normalize",
    "render_audit",
    "score_breakdown",
    "split_identifier",
    "split_identifier_parts",
    "strip_qualifier",
    "suggest_catalog_additions",
    "to_physical_name",
]


def __getattr__(name: str) -> Any:
    """Resolve a public name, or a submodule, on first access (:pep:`562`).

    The resolved object is written into the module globals, so this runs at most
    once per name and every subsequent access is an ordinary attribute lookup.

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
