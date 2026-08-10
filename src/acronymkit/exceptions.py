"""Exception hierarchy for ``acronymkit``.

Every exception raised by the library derives from :class:`AcronymKitError`, so
integrators can install a single ``except`` clause at a service boundary.
"""

from __future__ import annotations

from typing import Optional, Sequence

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


class AcronymKitError(Exception):
    """Base class for all errors raised by ``acronymkit``."""


class ConfigurationError(AcronymKitError, ValueError):
    """Raised when a :class:`~acronymkit.config.Config` is internally inconsistent."""


class OfflineError(ConfigurationError):
    """Raised when strict offline mode cannot be honoured.

    Strict offline mode is a promise that this process will not reach the
    network. ``acronymkit`` itself keeps that promise unconditionally — it
    contains no network code on any path — so this exception is never about
    something the library was about to do. It is about something the library
    can *see* and cannot prevent: a configuration that would require a
    capability offline mode forbids, or third-party code that another package
    has arranged to have imported.

    It derives from :class:`ConfigurationError`, and therefore from
    :class:`ValueError`, because it is raised where a configuration is
    rejected: at :class:`~acronymkit.config.Config` construction, not part-way
    through an inference. Discovering at 2 a.m. that a container cannot do
    what it was asked is the failure this exists to move to start-up.

    Args:
        reason: What cannot be honoured, in one sentence.
        remedy: The concrete thing to do about it, if there is one.
    """

    def __init__(self, reason: str, remedy: Optional[str] = None) -> None:
        self.reason = reason
        self.remedy = remedy
        message = f"Strict offline mode cannot be honoured: {reason}"
        if remedy:
            message = f"{message} {remedy}"
        super().__init__(message)


class TierUnavailableError(AcronymKitError, RuntimeError):
    """Raised when a requested :class:`~acronymkit.enums.EngineTier` cannot be built.

    Only raised for tiers that do not permit silent degradation
    (``STATISTICAL_NLP`` and ``NEURAL``), or when ``Config.strict`` is set.

    Args:
        tier: The tier that could not be constructed.
        missing: Distribution names that would satisfy the requirement.
        extra: The ``pip install 'acronymkit[...]'`` extra to suggest.
    """

    def __init__(
        self,
        tier: object,
        missing: Sequence[str] = (),
        extra: Optional[str] = None,
    ) -> None:
        self.tier = tier
        self.missing = tuple(missing)
        self.extra = extra
        hint = ""
        if extra:
            hint = f" Install it with: pip install 'acronymkit[{extra}]'"
        elif missing:
            hint = f" Install one of: {', '.join(missing)}"
        super().__init__(f"Engine tier {tier} is unavailable.{hint}")


class ResourceNotFoundError(AcronymKitError, FileNotFoundError):
    """Raised when a bundled or user-supplied data resource cannot be loaded."""


class LexiconError(AcronymKitError):
    """Raised when a dictionary/lexicon source is unreadable or malformed."""


class TokenizationError(AcronymKitError):
    """Raised when input text cannot be tokenised into usable units."""


class EmptyPhraseError(TokenizationError, ValueError):
    """Raised when the input phrase contains no acronym-eligible tokens.

    This is distinct from :class:`NoCandidateError`: the phrase itself was
    empty, whitespace-only, or reduced to nothing by the active filters.
    """


class GenerationError(AcronymKitError):
    """Base class for failures during forward generation or backronym search."""


class NoCandidateError(GenerationError):
    """Raised when no candidate satisfies the active generation constraints.

    Typically caused by over-constrained configuration, e.g. a
    ``min_acronym_length`` larger than the number of eligible tokens, or
    ``require_dictionary_word=True`` with no dictionary hit in the search space.
    """
