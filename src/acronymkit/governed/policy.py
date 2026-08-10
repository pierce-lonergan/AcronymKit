"""How a governed vocabulary is applied: :class:`NamingPolicy` and its presets.

The dictionary says what a token means. The policy says what to do with that —
whether a caller's overlay may beat the catalog, what happens to a token the
catalog has never seen, whether a name that is too long is a problem, and
whether a trailing class word is required. Splitting the two is what lets one
vocabulary be read under several house rules without copying it.

The presets are named rather than left as keyword arguments at each call site
because a named policy is auditable and a loose bag of booleans is not: "this
pipeline runs under ``governed_default``" is a reviewable sentence.
:meth:`NamingPolicy.frequency_baseline` is the odd one out — it exists to be
beaten, as the contrast arm against the governed answer.

The length invariant
--------------------
:attr:`NamingPolicy.enforce_name_length` may only ever cause a *flag*. No code
path in this package truncates a name or drops a token, under any policy, ever.
That is not a default that can be turned off; it is the guarantee the subsystem
is for. A pipeline that silently shortened ``TXN_APPLNT_VERIF_STAT_CD`` to fit a
platform limit would be inventing an identifier nobody governs, and it would do
it at the exact moment the caller most needs to be told. So the answer is always
the full name plus a finding, and :attr:`PhysicalName.truncated` exists solely
so that a test — and an auditor — can assert it stayed ``False``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from ..exceptions import ConfigurationError
from .enums import ResolutionMode, UnknownPolicy

__all__ = ["NamingPolicy"]


def _describe(exc: PydanticValidationError) -> str:
    """Render a Pydantic validation error as a compact, actionable message.

    A near-copy of ``acronymkit.config._describe_validation_error``, and
    deliberately not an import of it: importing :mod:`acronymkit.config` builds
    the :class:`~acronymkit.config.Config` core schema, which is the single
    largest import cost in this distribution and has nothing to do with governed
    naming. A few duplicated lines are the cheaper of the two mistakes.

    Args:
        exc: The error raised while validating a :class:`NamingPolicy`.

    Returns:
        One ``field: message`` clause per problem, joined with ``"; "``. A
        problem with no location is reported unqualified.
    """
    problems = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = error.get("msg", "invalid value")
        problems.append(f"{location}: {message}" if location else message)
    return "; ".join(problems) or str(exc)


class NamingPolicy(BaseModel):
    """Rules applied on top of a governed vocabulary.

    Frozen, so a policy resolved once at start-up is safe to share across
    threads and to hold on a long-lived service object.

    Example:
        >>> from acronymkit.governed import NamingPolicy
        >>> NamingPolicy.governed_default().governed_hit_is_final
        True
        >>> NamingPolicy.frequency_baseline().allow_override
        False
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: ResolutionMode = Field(
        default=ResolutionMode.GOVERNED,
        description="How a token with several candidate long forms is resolved. GOVERNED "
        "honours the catalog; MOST_COMMON is the contrast arm and ignores the pin.",
    )
    allow_override: bool = Field(
        default=True,
        description="Whether a caller-supplied pin or overlay entry may beat the catalog "
        "default. When False, an overlay that CONTRADICTS a governed entry is not applied and "
        "the result carries a note saying so — but an overlay for a token the catalog does not "
        "know is still applied, because overriding nothing is not an override.",
    )
    unknown: UnknownPolicy = Field(
        default=UnknownPolicy.PASSTHROUGH_TITLECASE,
        description="What to do with a token the vocabulary does not contain.",
    )
    neural_fallback: bool = Field(
        default=False,
        description="Whether the statistical tier may be consulted at all. Off by default: a "
        "governed pipeline that quietly starts guessing has lost the property it was chosen "
        "for, so reaching the guess must be an explicit act.",
    )
    governed_hit_is_final: bool = Field(
        default=True,
        description="A statistical answer may NEVER override a governed one. This is the "
        "line the neural opt-in does not cross: the tier can only ever speak for tokens the "
        "catalog is silent about. Turning it off is not supported by any preset.",
    )
    enforce_name_length: bool = Field(
        default=False,
        description="Whether a name longer than max_name_length is reported as a problem. It "
        "may only ever cause a FLAG. No code path truncates a name or drops a token, ever — "
        "not under this setting, not under any other. The result is the full name plus an "
        "EXCEEDS_MAX_LENGTH finding, and PhysicalName.truncated stays False so that the "
        "invariant can be asserted rather than trusted.",
    )
    max_name_length: int = Field(
        default=30,
        ge=1,
        description="Character ceiling checked when enforce_name_length is on. The default is "
        "a common platform limit for an identifier and is a starting point, not a standard.",
    )
    require_trailing_class_word: bool = Field(
        default=True,
        description="Whether a physical name must end in a class word to be compliant. On by "
        "default because that is what makes a name self-describing; off in the frequency "
        "baseline, which is not modelling a naming standard at all.",
    )
    append_class_word_when_missing: bool = Field(
        default=True,
        description="Whether to append the class word implied by the logical name when the "
        "rendered physical name lacks one. Affects to_physical_name only — a compliance check "
        "reports what it was given and never edits it.",
    )

    def __init__(self, **data: Any) -> None:
        """Validate and freeze a policy.

        Pydantic wraps a bad field value in its own ``ValidationError``, which is
        not an :class:`~acronymkit.exceptions.AcronymKitError`. That would break
        the contract documented in :mod:`acronymkit.exceptions` — a single
        ``except AcronymKitError`` at a service boundary catches everything this
        library raises — so the wrapper is unwrapped here and re-raised as
        :class:`~acronymkit.exceptions.ConfigurationError`, which is also a
        ``ValueError`` and therefore still catchable the conventional way.
        :class:`~acronymkit.config.Config` does the same thing for the same
        reason.

        Args:
            **data: Field values; see the class attributes.

        Raises:
            ConfigurationError: If any field is invalid.
        """
        try:
            super().__init__(**data)
        except PydanticValidationError as exc:
            raise ConfigurationError(_describe(exc)) from exc

    @classmethod
    def governed_default(cls) -> NamingPolicy:
        """The default policy: the catalog decides, and an unknown stays unknown.

        Overlays are honoured, collisions are settled by the catalog's pin, a
        governed hit is final, a trailing class word is required, and a token
        the vocabulary does not contain comes back Title Cased and marked
        unknown rather than guessed at.

        Returns:
            A policy with every field at its declared default.
        """
        return cls()

    @classmethod
    def frequency_baseline(cls) -> NamingPolicy:
        """The contrast arm: resolve a collision by "most common", ignoring the pin.

        Sets ``mode=MOST_COMMON``, ``allow_override=False`` and
        ``require_trailing_class_word=False``. "Most common" is implemented as
        *the first candidate in the entry's declared* ``candidates`` *order*,
        which the fixture data orders by corpus frequency — so the rule is
        deterministic and inspectable rather than a hidden count.

        This policy exists to be beaten. It is what makes "the governed answer
        differs from the popular answer" a claim a reader can check, on tokens
        chosen so the two rules disagree. It is a comparison on fixture data and
        it is not evidence about any corpus; nothing measured on it transfers to
        one.

        Returns:
            The contrast policy.
        """
        return cls(
            mode=ResolutionMode.MOST_COMMON,
            allow_override=False,
            require_trailing_class_word=False,
        )

    @classmethod
    def neural_optin(cls) -> NamingPolicy:
        """Allow the statistical tier, but only where the catalog is silent.

        Sets ``unknown=NEURAL`` and ``neural_fallback=True`` while keeping
        ``governed_hit_is_final=True``, which is the whole shape of the opt-in:
        a guess may fill a gap, and it may never overrule a governed answer. The
        combination is spelled out here rather than left to a caller because the
        two flags are easy to set and the third is easy to forget, and
        forgetting it is what turns a governed pipeline back into a guessing
        one.

        Returns:
            The opt-in policy.
        """
        return cls(
            unknown=UnknownPolicy.NEURAL,
            neural_fallback=True,
            governed_hit_is_final=True,
        )

    @classmethod
    def strict_length(cls) -> NamingPolicy:
        """Flag names longer than ``max_name_length``, and change nothing else.

        Sets ``enforce_name_length=True`` with ``max_name_length=30``. Read the
        verb: it flags. This preset cannot shorten a name, because no code path
        in this package can — see :attr:`enforce_name_length`.

        Returns:
            The length-checking policy.
        """
        return cls(enforce_name_length=True, max_name_length=30)
