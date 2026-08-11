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

Why the policy is a dataclass and not a validated model
-------------------------------------------------------
A policy is a dict key. :meth:`~acronymkit.governed.dictionary.GovernedDictionary._memo`
keys its per-policy memos on the policy *by value*, so ``__eq__`` and ``__hash__``
have to mean "the same nine settings" and nothing else; a frozen dataclass gives
exactly that and gives it without a compiled extension in the import graph. See
:mod:`acronymkit.governed.models` for the rest of that argument, which is the
same argument.

The nine fields are checked by hand in :meth:`NamingPolicy.__init__` rather than
derived from the annotations. That is nine explicit lines, and it is what keeps
the refusals this module is judged on — an unknown field, a mode nobody
declared, a length ceiling below one — reported together and reported as
:class:`~acronymkit.exceptions.ConfigurationError`.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from functools import cache
from typing import Any, Mapping, Optional, Tuple

from ..exceptions import ConfigurationError
from .enums import ResolutionMode, UnknownPolicy
from .models import _describe_problems, _flag, _member

__all__ = ["NamingPolicy"]


def _bounded_int(value: Any, name: str, minimum: int, problems: list[Tuple[str, str]]) -> Any:
    """Read an integer field and hold it at or above ``minimum``.

    The accepted spellings are the ones the subsystem has always taken: an
    ``int``, a ``bool`` (which is an ``int`` in Python and was accepted before),
    a ``float`` that is whole, and a string of digits. A policy crosses the wire
    as JSON and arrives from a CLI flag as text, so refusing ``"30"`` would
    break a caller for no gain.

    Args:
        value: Whatever the caller supplied.
        name: The field name, for the message.
        minimum: The inclusive lower bound.
        problems: Collected problems, appended to in place.

    Returns:
        The value as an ``int``, or unchanged when it is not readable as one.
    """
    if isinstance(value, bool):
        number = int(value)
    elif isinstance(value, int):
        number = value
    elif isinstance(value, float) and value.is_integer():
        number = int(value)
    elif isinstance(value, str):
        try:
            number = int(value)
        except ValueError:
            problems.append(
                (name, "Input should be a valid integer, unable to parse string as an integer")
            )
            return value
    else:
        problems.append((name, "Input should be a valid integer"))
        return value
    if number < minimum:
        problems.append((name, f"Input should be greater than or equal to {minimum}"))
    return number


@dataclass(frozen=True)
class NamingPolicy:
    """Rules applied on top of a governed vocabulary.

    Frozen, so a policy resolved once at start-up is safe to share across
    threads and to hold on a long-lived service object. Hashable by value, which
    is what lets the resolver keep one memo per distinct set of settings.

    Example:
        >>> from acronymkit.governed import NamingPolicy
        >>> NamingPolicy.governed_default().governed_hit_is_final
        True
        >>> NamingPolicy.frequency_baseline().allow_override
        False
    """

    #: How a token with several candidate long forms is resolved. GOVERNED
    #: honours the catalog; MOST_COMMON is the contrast arm and ignores the pin.
    mode: ResolutionMode = ResolutionMode.GOVERNED

    #: Whether a caller-supplied pin or overlay entry may beat the catalog
    #: default. When False, an overlay that CONTRADICTS a governed entry is not
    #: applied and the result carries a note saying so — but an overlay for a
    #: token the catalog does not know is still applied, because overriding
    #: nothing is not an override.
    allow_override: bool = True

    #: What to do with a token the vocabulary does not contain.
    unknown: UnknownPolicy = UnknownPolicy.PASSTHROUGH_TITLECASE

    #: Whether the statistical tier may be consulted at all. Off by default: a
    #: governed pipeline that quietly starts guessing has lost the property it
    #: was chosen for, so reaching the guess must be an explicit act.
    neural_fallback: bool = False

    #: A statistical answer may NEVER override a governed one. This is the line
    #: the neural opt-in does not cross: the tier can only ever speak for tokens
    #: the catalog is silent about. Turning it off is not supported by any
    #: preset.
    governed_hit_is_final: bool = True

    #: Whether a name longer than max_name_length is reported as a problem. It
    #: may only ever cause a FLAG. No code path truncates a name or drops a
    #: token, ever — not under this setting, not under any other. The result is
    #: the full name plus an EXCEEDS_MAX_LENGTH finding, and
    #: PhysicalName.truncated stays False so that the invariant can be asserted
    #: rather than trusted.
    enforce_name_length: bool = False

    #: Character ceiling checked when enforce_name_length is on. The default is
    #: a common platform limit for an identifier and is a starting point, not a
    #: standard.
    max_name_length: int = 30

    #: Whether a physical name must end in a class word to be compliant. On by
    #: default because that is what makes a name self-describing; off in the
    #: frequency baseline, which is not modelling a naming standard at all.
    require_trailing_class_word: bool = True

    #: Whether to append the class word implied by the logical name when the
    #: rendered physical name lacks one. Affects to_physical_name only — a
    #: compliance check reports what it was given and never edits it.
    append_class_word_when_missing: bool = True

    def __init__(self, **data: Any) -> None:
        """Validate and freeze a policy.

        Every problem is reported together, as ``field: message`` clauses joined
        with ``"; "``, and the whole thing is raised as
        :class:`~acronymkit.exceptions.ConfigurationError` — which is also a
        :class:`ValueError`, so it stays catchable the conventional way, and is
        an :class:`~acronymkit.exceptions.AcronymKitError`, so the single
        ``except`` clause :mod:`acronymkit.exceptions` promises at a service
        boundary still catches it. :class:`~acronymkit.config.Config` presents
        the same face for the same reason.

        Args:
            **data: Field values; see the class attributes. A keyword this
                policy does not declare is refused rather than ignored: a
                misspelled setting that is silently dropped is a pipeline
                running under rules nobody chose.

        Raises:
            ConfigurationError: If any field is invalid or unknown.
        """
        problems: list[Tuple[str, str]] = []
        unknown = [
            (name, "Extra inputs are not permitted") for name in data if name not in _DEFAULTS
        ]
        values = {**_DEFAULTS, **data}

        set_field = object.__setattr__
        set_field(self, "mode", _member(values["mode"], ResolutionMode, "mode", problems))
        set_field(
            self, "allow_override", _flag(values["allow_override"], "allow_override", problems)
        )
        set_field(self, "unknown", _member(values["unknown"], UnknownPolicy, "unknown", problems))
        set_field(
            self, "neural_fallback", _flag(values["neural_fallback"], "neural_fallback", problems)
        )
        set_field(
            self,
            "governed_hit_is_final",
            _flag(values["governed_hit_is_final"], "governed_hit_is_final", problems),
        )
        set_field(
            self,
            "enforce_name_length",
            _flag(values["enforce_name_length"], "enforce_name_length", problems),
        )
        set_field(
            self,
            "max_name_length",
            _bounded_int(values["max_name_length"], "max_name_length", 1, problems),
        )
        set_field(
            self,
            "require_trailing_class_word",
            _flag(values["require_trailing_class_word"], "require_trailing_class_word", problems),
        )
        set_field(
            self,
            "append_class_word_when_missing",
            _flag(
                values["append_class_word_when_missing"],
                "append_class_word_when_missing",
                problems,
            ),
        )

        problems.extend(unknown)
        if problems:
            raise ConfigurationError(_describe_problems(problems))

    def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
        """Return the nine settings as a ``dict``, in declaration order.

        Kept from the Pydantic era because a policy is written to and read from
        JSON — ``tests/fixtures/governed/policies.json`` stores all four presets
        in exactly this shape.

        Args:
            mode: ``"json"`` renders the two enum fields as their string values,
                which is what crosses a wire; anything else returns the members.

        Returns:
            One key per field, in declaration order.
        """
        values = {name: getattr(self, name) for name in _FIELD_NAMES}
        if mode == "json":
            return {
                name: value.value if isinstance(value, (ResolutionMode, UnknownPolicy)) else value
                for name, value in values.items()
            }
        return values

    def model_copy(
        self,
        *,
        update: Optional[Mapping[str, Any]] = None,
        deep: bool = False,
    ) -> NamingPolicy:
        """Return a policy with ``update`` applied, without re-validating.

        The same semantics as
        :meth:`acronymkit.governed.models._FrozenModel.model_copy`, and the same
        semantics this method had while it was pydantic's: the values in
        ``update`` are written as given. It is deliberately not a second
        validation point, because it is the documented way to derive a variant
        from a preset and a caller who has just been handed one should not have
        the rules for building one change underneath them. Build with
        :class:`NamingPolicy` itself to have the settings checked.

        Args:
            update: Settings to replace, or ``None`` for a plain copy.
            deep: Accepted so the signature does not narrow. Every field is an
                immutable scalar, so it can make no difference.

        Returns:
            A new policy. The receiver is unchanged.
        """
        del deep
        values = dict(self.__dict__)
        if update:
            values.update(update)
        clone = object.__new__(type(self))
        clone.__dict__.update(values)
        return clone

    @classmethod
    @cache
    def governed_default(cls) -> NamingPolicy:
        """The default policy: the catalog decides, and an unknown stays unknown.

        Overlays are honoured, collisions are settled by the catalog's pin, a
        governed hit is final, a trailing class word is required, and a token
        the vocabulary does not contain comes back Title Cased and marked
        unknown rather than guessed at.

        **Memoised, and the four presets share the reason.** Each one names a
        fixed set of field values, so every call was building an object equal to
        the last. That is not free: this is the default a caller gets whenever
        they omit ``policy=``, so it ran once per verb call, and the resolver
        then keys its caches on the policy *by value* — meaning the cost was
        paid twice, once to construct and once to discover the construction had
        been unnecessary. Returning one shared instance is safe because the
        record is frozen: two callers cannot tell they hold the same object
        except by ``is``, and nothing may mutate it. Callers who want a variant
        still get a fresh object from ``model_copy(update=...)``.

        Returns:
            A policy with every field at its declared default. The same
            instance on every call.
        """
        return cls()

    @classmethod
    @cache
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
    @cache
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
    @cache
    def strict_length(cls) -> NamingPolicy:
        """Flag names longer than ``max_name_length``, and change nothing else.

        Sets ``enforce_name_length=True`` with ``max_name_length=30``. Read the
        verb: it flags. This preset cannot shorten a name, because no code path
        in this package can — see :attr:`enforce_name_length`.

        Returns:
            The length-checking policy.
        """
        return cls(enforce_name_length=True, max_name_length=30)


#: Every field's declared default, keyed by name in declaration order — which is
#: also the emitted key order, and is what the wire contract fixes.
#:
#: Read off the class rather than written out a second time.
#: :meth:`NamingPolicy.__init__` takes ``**data``, because that is what lets an
#: unknown keyword be refused *by name* rather than as a bare ``TypeError``, and
#: the price of that is that the defaults are applied here instead of by a
#: generated signature.
_DEFAULTS: dict[str, Any] = {field.name: field.default for field in fields(NamingPolicy)}

#: Field names in declaration order.
_FIELD_NAMES: tuple[str, ...] = tuple(_DEFAULTS)
