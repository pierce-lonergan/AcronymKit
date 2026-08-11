"""The facade: bind a vocabulary and a policy once, then call the verbs.

The five governed verbs share one shape — ``verb(subject, dictionary,
policy=None, *, custom=None)`` — and that shape is right for the functions and
wrong for the caller. A schema-governance pipeline holds one vocabulary and one
policy for its whole run, and repeating both at every call site is three
arguments of ceremony per line, in exchange for a flexibility nobody uses. Worse,
it is three arguments that can drift: one call site left on the default policy
while the rest moved to a strict one is a bug that no type checker sees and no
test finds unless somebody thought to write it.

:class:`GovernedNamer` is what a caller should reach for first. It binds the
vocabulary, the policy and any overlay once, and exposes the same five verbs with
the subject as their only argument.

The same task, before and after
-------------------------------
Before — five files merged by hand, then three arguments carried to every call::

    allow = json.loads(Path("std/allowlist.json").read_text(encoding="utf-8"))
    words = json.loads(Path("std/class_words.json").read_text(encoding="utf-8"))
    with Path("std/term_glossary.csv").open(encoding="utf-8", newline="") as handle:
        terms = {row["logical_name"]: row["term_id"] for row in csv.DictReader(handle)}
    nds = GovernedDictionary.from_json(
        "std/dictionary.json",
        approved_abbreviations=allow["approved_abbreviations"],
        common_keywords=allow["common_keywords"],
        short_full_words=allow["short_full_words"],
        class_words=words["abbreviations"],
        term_index=terms,
    )
    policy, house = NamingPolicy.strict_length(), {"KYC": "Know Your Customer"}

    expand_identifier("TXN_APPLNT_ID", nds, policy, custom=house)
    is_compliant("TXN_APPLNT_ID", nds, policy, custom=house)
    normalize("custmr_acct_num", nds, policy, custom=house)

After::

    namer = GovernedNamer.from_bundle(
        "std", NamingPolicy.strict_length(), custom={"KYC": "Know Your Customer"}
    )

    namer.expand_identifier("TXN_APPLNT_ID")
    namer.is_compliant("TXN_APPLNT_ID")
    namer.normalize("custmr_acct_num")

Two things changed besides the line count. The pin sheet is merged in the second
version and was not in the first, because merging it is work the hand-written
version forgot to do — see :func:`~acronymkit.governed.loaders.load_bundle`. And
the policy is named once, so there is one place to read it from and no way for
two call sites to disagree about which rules a run used.

What it does not change
-----------------------
Nothing about the answers. Every method here forwards to the free function of
the same name, with the bound arguments filled in, and returns exactly what that
function returns. The precedence chain, the refusal to guess and the audit trail
are all where they were; this module holds no naming logic at all, on purpose,
so that there is no second place for a governed decision to be made.

Immutable and shareable
-----------------------
An instance is built once, never written to afterwards, and reads no clock, so
one namer can be a module-level constant shared by every thread of a service. It
holds no cache of its own; the dictionary it binds does memoise what it has
resolved, and :class:`~acronymkit.governed.dictionary.GovernedDictionary`
documents why that is safe to share.
:meth:`GovernedNamer.with_custom` and :meth:`GovernedNamer.with_policy` return
new namers and leave the receiver alone, which is what makes a per-project
overlay a value to pass around rather than a mutation to sequence correctly.

Worked examples use the fictional **Northwind Data Standards** catalog (``NDS``).
Nothing here describes a real organisation's standard.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Optional, Union

from ..exceptions import ConfigurationError

# The methods below carry the same names as the free functions they forward to,
# which reads well at the call site and would read ambiguously in the bodies.
# Aliasing settles it: a name with a leading underscore in a method body is the
# module-level function and cannot be the method.
from .compliance import is_compliant as _is_compliant
from .compliance import normalize as _normalize
from .dictionary import GovernedDictionary
from .expansion import expand_identifier as _expand_identifier
from .expansion import expand_token as _expand_token
from .loaders import DEFAULT_ENCODING, DEFAULT_TERM_COLUMNS, load_bundle, load_csv
from .loaders import load_long_to_short_csv as _load_long_to_short_csv
from .models import (
    ComplianceResult,
    GovernedEntry,
    IdentifierExpansion,
    PhysicalName,
    TokenExpansion,
)
from .naming import to_physical_name as _to_physical_name
from .policy import NamingPolicy

__all__ = ["GovernedNamer"]

#: Anything :func:`os.fspath` accepts, matching the loaders this class mirrors.
_PathLike = Union[str, "os.PathLike[str]"]

#: What :meth:`GovernedNamer.from_json` accepts, matching
#: :meth:`GovernedDictionary.from_json`: a path, or an already-parsed document.
_JsonSource = Union[str, "os.PathLike[str]", Mapping[str, Any], Sequence[Any]]


class GovernedNamer:
    """A governed vocabulary and policy, bound together, with the verbs on top.

    The entry point for an integration. Build one per standard — or one per
    standard and policy pair — hold it for the life of the process, and call the
    verbs with only their subject.

    Immutable after construction and safe to share across threads: the policy is
    a frozen model, nothing here writes to an instance after ``__init__``, and
    the dictionary's own memo is written under the conditions
    :class:`~acronymkit.governed.dictionary.GovernedDictionary` sets out.

    Example:
        >>> from acronymkit.governed import GovernedDictionary
        >>> from acronymkit.governed.namer import GovernedNamer
        >>> nds = GovernedNamer(
        ...     GovernedDictionary.from_mapping({"TXN": "Transaction", "ID": "Identifier"})
        ... )
        >>> nds.expand_identifier("TXN_ID").phrase
        'Transaction Identifier'
        >>> nds.expand_token("KYC").is_known
        False
        >>> nds.with_custom({"KYC": "Know Your Customer"}).expand_token("KYC").long
        'Know Your Customer'
    """

    __slots__ = ("_dictionary", "_policy")

    def __init__(
        self,
        dictionary: GovernedDictionary,
        policy: Optional[NamingPolicy] = None,
        *,
        custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
    ) -> None:
        """Bind a vocabulary, a policy and an overlay.

        The overlay is layered into the dictionary **once**, here, rather than
        on every call. That is the same operation
        :func:`~acronymkit.governed.expansion.expand_token` performs per call
        when it is handed ``custom=``, and doing it once is both the cheaper
        arrangement and the one that cannot be forgotten at a call site.

        Args:
            dictionary: The governed vocabulary. Required, and the reason is the
                subsystem's: a governed verb with no governed vocabulary is a
                contradiction, and the coherent reading of "no vocabulary" —
                expand nothing, pass everything through — is spelled
                ``GovernedDictionary()``.
            policy: The rules to apply to every call. ``None`` means
                :meth:`~acronymkit.governed.policy.NamingPolicy.governed_default`,
                and is resolved here rather than per call, so
                :attr:`policy` always names the rules that are actually in
                force.
            custom: A caller overlay layered onto ``dictionary``. The dictionary
                passed in is not modified.

        Raises:
            ConfigurationError: If ``dictionary`` is ``None``. Raised at
                construction rather than at the first call, because a namer with
                no vocabulary is unusable and the stack trace is worth more
                where the mistake was made.
        """
        if dictionary is None:
            raise ConfigurationError(
                "GovernedNamer() requires a governed vocabulary, and dictionary=None is not one. "
                "Pass a GovernedDictionary. If you want every token to pass through "
                "untouched, pass an empty GovernedDictionary() and say so explicitly."
            )
        self._dictionary: GovernedDictionary = (
            dictionary.with_custom(custom) if custom else dictionary
        )
        self._policy: NamingPolicy = (
            policy if policy is not None else NamingPolicy.governed_default()
        )

    # -- construction ------------------------------------------------------
    @classmethod
    def from_bundle(
        cls,
        path: _PathLike,
        policy: Optional[NamingPolicy] = None,
        *,
        custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
        term_columns: tuple[str, str] = DEFAULT_TERM_COLUMNS,
        encoding: str = DEFAULT_ENCODING,
    ) -> GovernedNamer:
        """Build a namer from a bundle directory or single bundle object.

        The shortest path from a standard on disk to a working namer, and the
        one to reach for first. The bundle layout, the file names it accepts and
        how the pin sheet is merged are all
        :func:`~acronymkit.governed.loaders.load_bundle`'s and are documented
        there.

        Args:
            path: A directory holding the standard's files, or one JSON object.
            policy: As :meth:`__init__`.
            custom: As :meth:`__init__`.
            term_columns: As :func:`~acronymkit.governed.loaders.load_bundle`.
            encoding: As :func:`~acronymkit.governed.loaders.load_bundle`.

        Returns:
            The namer.

        Raises:
            LexiconError: As :func:`~acronymkit.governed.loaders.load_bundle`.
        """
        return cls(
            load_bundle(path, custom=custom, term_columns=term_columns, encoding=encoding),
            policy,
        )

    @classmethod
    def from_csv(
        cls,
        path: _PathLike,
        policy: Optional[NamingPolicy] = None,
        *,
        token_column: str,
        canonical_column: str,
        encoding: str = DEFAULT_ENCODING,
        delimiter: str = ",",
        custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
        approved_abbreviations: Iterable[str] = (),
        common_keywords: Iterable[str] = (),
        short_full_words: Iterable[str] = (),
        class_words: Optional[Mapping[str, str]] = None,
        term_index: Optional[Mapping[str, str]] = None,
    ) -> GovernedNamer:
        """Build a namer from a short → long CSV catalog.

        Every argument but ``policy`` is :func:`~acronymkit.governed.loaders.load_csv`'s
        and means exactly what it means there, including the two column names
        having no defaults.

        Args:
            path: The CSV file.
            policy: As :meth:`__init__`.
            token_column: As :func:`~acronymkit.governed.loaders.load_csv`.
            canonical_column: As :func:`~acronymkit.governed.loaders.load_csv`.
            encoding: As :func:`~acronymkit.governed.loaders.load_csv`.
            delimiter: As :func:`~acronymkit.governed.loaders.load_csv`.
            custom: As :meth:`__init__`.
            approved_abbreviations: As :meth:`GovernedDictionary.__init__`.
            common_keywords: As :meth:`GovernedDictionary.__init__`.
            short_full_words: As :meth:`GovernedDictionary.__init__`.
            class_words: As :meth:`GovernedDictionary.__init__`.
            term_index: As :meth:`GovernedDictionary.__init__`.

        Returns:
            The namer.

        Raises:
            LexiconError: As :func:`~acronymkit.governed.loaders.load_csv`.
        """
        return cls(
            load_csv(
                path,
                token_column=token_column,
                canonical_column=canonical_column,
                encoding=encoding,
                delimiter=delimiter,
                custom=custom,
                approved_abbreviations=approved_abbreviations,
                common_keywords=common_keywords,
                short_full_words=short_full_words,
                class_words=class_words,
                term_index=term_index,
            ),
            policy,
        )

    @classmethod
    def from_long_to_short_csv(
        cls,
        path: _PathLike,
        policy: Optional[NamingPolicy] = None,
        *,
        long_column: str,
        short_column: str,
        encoding: str = DEFAULT_ENCODING,
        delimiter: str = ",",
        custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
        approved_abbreviations: Iterable[str] = (),
        common_keywords: Iterable[str] = (),
        short_full_words: Iterable[str] = (),
        class_words: Optional[Mapping[str, str]] = None,
        term_index: Optional[Mapping[str, str]] = None,
    ) -> GovernedNamer:
        """Build a namer from a long → short CSV catalog, inverted.

        The direction a governed catalog is actually stored in. Every argument
        but ``policy`` is
        :func:`~acronymkit.governed.loaders.load_long_to_short_csv`'s, including
        what the inversion does to a collision and how it records it.

        Args:
            path: The CSV file.
            policy: As :meth:`__init__`.
            long_column: As :func:`~acronymkit.governed.loaders.load_long_to_short_csv`.
            short_column: As :func:`~acronymkit.governed.loaders.load_long_to_short_csv`.
            encoding: As :func:`~acronymkit.governed.loaders.load_long_to_short_csv`.
            delimiter: As :func:`~acronymkit.governed.loaders.load_long_to_short_csv`.
            custom: As :meth:`__init__`.
            approved_abbreviations: As :meth:`GovernedDictionary.__init__`.
            common_keywords: As :meth:`GovernedDictionary.__init__`.
            short_full_words: As :meth:`GovernedDictionary.__init__`.
            class_words: As :meth:`GovernedDictionary.__init__`.
            term_index: As :meth:`GovernedDictionary.__init__`.

        Returns:
            The namer.

        Raises:
            LexiconError: As :func:`~acronymkit.governed.loaders.load_long_to_short_csv`.
        """
        return cls(
            _load_long_to_short_csv(
                path,
                long_column=long_column,
                short_column=short_column,
                encoding=encoding,
                delimiter=delimiter,
                custom=custom,
                approved_abbreviations=approved_abbreviations,
                common_keywords=common_keywords,
                short_full_words=short_full_words,
                class_words=class_words,
                term_index=term_index,
            ),
            policy,
        )

    @classmethod
    def from_json(
        cls,
        path_or_obj: _JsonSource,
        policy: Optional[NamingPolicy] = None,
        *,
        custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
        approved_abbreviations: Iterable[str] = (),
        common_keywords: Iterable[str] = (),
        short_full_words: Iterable[str] = (),
        class_words: Optional[Mapping[str, str]] = None,
        term_index: Optional[Mapping[str, str]] = None,
    ) -> GovernedNamer:
        """Build a namer from a JSON catalog file or a parsed document.

        Mirrors :meth:`GovernedDictionary.from_json`, including that a
        :class:`str` argument is a **path** and never JSON text. This reads the
        catalog and nothing else; for a whole standard use :meth:`from_bundle`.

        Args:
            path_or_obj: As :meth:`GovernedDictionary.from_json`.
            policy: As :meth:`__init__`.
            custom: As :meth:`__init__`.
            approved_abbreviations: As :meth:`GovernedDictionary.__init__`.
            common_keywords: As :meth:`GovernedDictionary.__init__`.
            short_full_words: As :meth:`GovernedDictionary.__init__`.
            class_words: As :meth:`GovernedDictionary.__init__`.
            term_index: As :meth:`GovernedDictionary.__init__`.

        Returns:
            The namer.

        Raises:
            LexiconError: As :meth:`GovernedDictionary.from_json`.
        """
        return cls(
            GovernedDictionary.from_json(
                path_or_obj,
                custom=custom,
                approved_abbreviations=approved_abbreviations,
                common_keywords=common_keywords,
                short_full_words=short_full_words,
                class_words=class_words,
                term_index=term_index,
            ),
            policy,
        )

    @classmethod
    def from_mapping(
        cls,
        short_to_long: Mapping[str, str],
        policy: Optional[NamingPolicy] = None,
        *,
        custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
        approved_abbreviations: Iterable[str] = (),
        common_keywords: Iterable[str] = (),
        short_full_words: Iterable[str] = (),
        class_words: Optional[Mapping[str, str]] = None,
        term_index: Optional[Mapping[str, str]] = None,
    ) -> GovernedNamer:
        """Build a namer from a plain ``{token: long form}`` mapping.

        The smallest useful namer, and the shape to reach for when trying the
        library out. A mapping cannot express a collision, so nothing built this
        way is ever settled by score — see
        :meth:`GovernedDictionary.from_mapping`.

        Args:
            short_to_long: As :meth:`GovernedDictionary.from_mapping`.
            policy: As :meth:`__init__`.
            custom: As :meth:`__init__`.
            approved_abbreviations: As :meth:`GovernedDictionary.__init__`.
            common_keywords: As :meth:`GovernedDictionary.__init__`.
            short_full_words: As :meth:`GovernedDictionary.__init__`.
            class_words: As :meth:`GovernedDictionary.__init__`.
            term_index: As :meth:`GovernedDictionary.__init__`.

        Returns:
            The namer.
        """
        return cls(
            GovernedDictionary.from_mapping(
                short_to_long,
                custom=custom,
                approved_abbreviations=approved_abbreviations,
                common_keywords=common_keywords,
                short_full_words=short_full_words,
                class_words=class_words,
                term_index=term_index,
            ),
            policy,
        )

    # -- layering ----------------------------------------------------------
    def with_custom(
        self, custom: Optional[Mapping[str, Union[str, GovernedEntry]]]
    ) -> GovernedNamer:
        """Return a new namer with ``custom`` layered on top of this one's overlay.

        Layers compose and the last one wins, exactly as
        :meth:`GovernedDictionary.with_custom` describes: a house layer stays in
        force on every token a project layer is silent about. The receiver is
        unchanged, so a shared module-level namer can be specialised per project
        without any sequencing worry.

        Args:
            custom: The overlay to layer. ``None`` and an empty mapping both
                yield an equivalent namer rather than the receiver itself.

        Returns:
            A new :class:`GovernedNamer` with the same policy.
        """
        return type(self)(self._dictionary.with_custom(custom), self._policy)

    def with_policy(self, policy: Optional[NamingPolicy]) -> GovernedNamer:
        """Return a new namer that applies ``policy`` to the same vocabulary.

        The cheap way to run one standard under two sets of rules — a strict
        check for new schemas beside the default for existing ones — without
        rebuilding the vocabulary, which is the expensive half.

        Args:
            policy: The rules to apply. ``None`` restores
                :meth:`~acronymkit.governed.policy.NamingPolicy.governed_default`.

        Returns:
            A new :class:`GovernedNamer` sharing this one's dictionary. The
            receiver is unchanged.
        """
        return type(self)(self._dictionary, policy)

    # -- the verbs ---------------------------------------------------------
    def expand_token(self, token: Optional[str]) -> TokenExpansion:
        """Expand one token. See :func:`~acronymkit.governed.expansion.expand_token`.

        Args:
            token: The token, matched case-insensitively. Blank input returns an
                expansion whose ``long`` is ``""`` rather than raising, so a
                blank cell does not stop a batch.

        Returns:
            The expansion, with its provenance.

        Raises:
            LexiconError: If the token is unknown and the bound policy's
                ``unknown`` is ``UnknownPolicy.REJECT``.
        """
        return _expand_token(token, self._dictionary, self._policy)

    def expand_identifier(self, identifier: Optional[str]) -> IdentifierExpansion:
        """Expand a whole identifier. See :func:`~acronymkit.governed.expansion.expand_identifier`.

        Args:
            identifier: The physical name, split on the conventions physical
                names are written in.

        Returns:
            The expansion: the phrase, one record per token, the trailing class
            word and ``is_fully_known``.

        Raises:
            LexiconError: If a token is unknown and the bound policy's
                ``unknown`` is ``UnknownPolicy.REJECT``.
        """
        return _expand_identifier(identifier, self._dictionary, self._policy)

    def to_physical_name(self, logical: str) -> PhysicalName:
        """Render a logical name. See :func:`~acronymkit.governed.naming.to_physical_name`.

        Args:
            logical: The logical name, in words.

        Returns:
            The governed physical name in ``UPPER_SNAKE``, word by word, with
            the catalog row behind each token.
        """
        return _to_physical_name(logical, self._dictionary, self._policy)

    def is_compliant(self, name: str) -> ComplianceResult:
        """Check a physical name. See :func:`~acronymkit.governed.compliance.is_compliant`.

        Args:
            name: The physical name somebody else wrote.

        Returns:
            The result: never a bare boolean, always one finding per token plus
            the whole-name findings, each carrying the smallest edit that clears
            it.
        """
        return _is_compliant(name, self._dictionary, self._policy)

    def normalize(self, name: str) -> str:
        """Correct a physical name. See :func:`~acronymkit.governed.compliance.normalize`.

        Args:
            name: The physical name to correct.

        Returns:
            The name with the corrections the vocabulary justifies applied. It
            is not a promise of compliance — run :meth:`is_compliant` on the
            result to see what is left.
        """
        return _normalize(name, self._dictionary, self._policy)

    # -- batches -----------------------------------------------------------
    def expand_many(self, identifiers: Iterable[Optional[str]]) -> tuple[IdentifierExpansion, ...]:
        """Expand many identifiers, in order.

        A schema pipeline's unit of work is a table's worth of columns, not one
        column, and a method that takes the batch is the shape that call site
        wants — particularly across a process boundary, where the cost that
        matters is the number of round trips rather than the work inside them.

        **This is the loop, and it says so.** It is not faster per identifier
        than calling :meth:`expand_identifier` in a comprehension; the only
        difference either way is the one policy object this class already bound
        at construction, and on the fixture corpus that difference sits at the
        edge of run-to-run variance. The method earns its place by being the
        right call shape and by fixing the contract below, not by being quick.

        Two properties are the contract, and they are what a future parallel or
        cached implementation would have to keep to be a drop-in:

        * **Positional correspondence.** Result *i* is the answer for input *i*,
          always. A caller aligns the results back onto their own rows by
          position, so no implementation may filter, reorder or deduplicate the
          output.
        * **Per-item independence.** Nothing is carried from one item to the
          next. The dictionary is immutable, the policy is frozen and the verbs
          read no state, so items may be evaluated in any order or in parallel
          without changing a single answer.

        Nothing is memoised. A memo keyed on the identifier was prototyped and
        measured, and it is not here. On the fixture corpus, whose identifiers
        are all distinct, it changed nothing outside run-to-run variance while
        holding every result in memory for the length of the call. What it does
        buy is proportional to how often the input repeats — which is a property
        of the caller's schema, not of this library, and nobody here has
        measured a real one. A caller who knows their schema repeats can wrap
        :meth:`expand_identifier` in :func:`functools.lru_cache` and get it
        without this library assuming it on their behalf.

        Args:
            identifiers: The physical names, in the order the results are wanted
                in. Any iterable; it is consumed once.

        Returns:
            One :class:`~acronymkit.governed.models.IdentifierExpansion` per
            input, in input order. A tuple, because the result of a governed
            call should not be something a caller can edit in place.

        Raises:
            LexiconError: If a token is unknown and the bound policy's
                ``unknown`` is ``UnknownPolicy.REJECT``. The batch stops there;
                a partial result is not returned, because a tuple that is
                shorter than its input breaks the positional correspondence
                every caller relies on.
        """
        catalog, policy = self._dictionary, self._policy
        return tuple(_expand_identifier(item, catalog, policy) for item in identifiers)

    def check_many(self, names: Iterable[str]) -> tuple[ComplianceResult, ...]:
        """Check many physical names, in order.

        The compliance half of :meth:`expand_many`, with the same two contract
        properties — positional correspondence and per-item independence — and
        the same absence of any cache. A schema sweep is what this is for: run
        it over a table's columns and filter the results on ``compliant``.

        Args:
            names: The physical names, in the order the results are wanted in.
                Any iterable; it is consumed once.

        Returns:
            One :class:`~acronymkit.governed.models.ComplianceResult` per input,
            in input order.
        """
        catalog, policy = self._dictionary, self._policy
        return tuple(_is_compliant(item, catalog, policy) for item in names)

    # -- properties --------------------------------------------------------
    @property
    def dictionary(self) -> GovernedDictionary:
        """The bound vocabulary, with any construction-time overlay layered in."""
        return self._dictionary

    @property
    def policy(self) -> NamingPolicy:
        """The bound policy. Never ``None``: a ``None`` argument was resolved to the default."""
        return self._policy

    # -- dunder ------------------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover - display helper
        return (
            f"GovernedNamer(dictionary={self._dictionary!r}, "
            f"mode={self._policy.mode.value}, unknown={self._policy.unknown.value})"
        )
