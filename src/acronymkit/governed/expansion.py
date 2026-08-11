"""The forward direction: a bare token, or a whole identifier, into words.

:func:`expand_token` and :func:`expand_identifier` are what the subsystem is
for. Given ``TXN_APPLNT_ID`` and a governed vocabulary they return "Transaction
Applicant Identifier", the same way every time, with a record of which catalog
row produced each word and what that word was chosen over.

Neither function has a sentence to lean on. That is the premise, not a
limitation: a column name is not prose, there is no surrounding text to
disambiguate against, and the answer therefore has to come from the catalog or
not at all. Both functions are pure lookups over
:class:`~acronymkit.governed.dictionary.GovernedDictionary` with an audit record
wrapped around them, and the only judgement anywhere in the path is
:func:`~acronymkit.governed.tokenizer.split_identifier` deciding where one token
ends and the next begins.

The unknown-token contract
--------------------------
A token the vocabulary does not contain comes back **Title Cased**, with
``is_known=False``, ``confidence=0.0`` and ``source=ExpansionSource.PASSTHROUGH``.
It is not approximated, not stemmed towards something that looks close, and not
handed to a model.

This is the design thesis, so it is worth stating rather than implying: **the
library is willing to say it does not know.** An unknown token reported as
unknown is recoverable — a pipeline filters on ``is_known``, routes the misses
to whoever owns the catalog, and the fix is a new row. An unknown token quietly
approximated is not recoverable, because nothing downstream can tell it from an
answer. The Title Cased form exists so the phrase stays readable for a person,
and the three other fields exist so no program mistakes it for an answer.

The other half of not guessing: nothing is lost
-----------------------------------------------
"I do not know this token" is one honest answer and "there was something in this
name I could not read" is another, and the second is the one a splitter is in a
position to get wrong quietly. Every character of an identifier is either inside
a token, or one of the separators
:mod:`~acronymkit.governed.tokenizer` accounts for, or reported on
:attr:`~acronymkit.governed.models.IdentifierExpansion.unaccounted`; and
``is_fully_known`` is ``True`` only when the catalog answered for every token and
that third list is empty. A confident, complete-looking phrase produced by
discarding part of the input would be exactly the failure the passthrough
contract above exists to prevent, arriving through a different door.

:func:`expand_token` has nothing to account for. It looks its argument up whole,
so a character it cannot read stays in the lookup key and the token resolves or
does not; there is no splitting for anything to fall out of.

``UnknownPolicy.REJECT`` turns the same situation into a raised
:class:`~acronymkit.exceptions.LexiconError`, for pipelines where an
unrecognised token means the catalog is out of date and processing should stop.
``UnknownPolicy.NEURAL`` is accepted and, in this release, behaves as
passthrough: this package contains no statistical tier and importing one would
break the Tier 0 promise the distribution makes. The opt-in is a declaration of
intent that nothing yet acts on, and
``NamingPolicy.governed_hit_is_final`` means it could never change a *known*
token's answer in any case.

Why ``dictionary`` may not be ``None``
--------------------------------------
A governed verb with no governed vocabulary is a contradiction, so passing
``None`` raises :class:`~acronymkit.exceptions.ConfigurationError` naming the
problem. The reading of "no dictionary" that *is* coherent — expand nothing,
pass everything through — is spelled ``GovernedDictionary()``, and it does
exactly that. Making the empty case explicit costs one call and removes the
failure where a vocabulary that failed to load silently degrades a whole schema
to Title Case.

Vocabulary note: worked examples use the fictional **Northwind Data Standards**
catalog (``NDS``) and generic industry tokens (``TXN``, ``APPLNT``, ``DT``).
Nothing here describes a real organisation's schema.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Optional, Union

from ..exceptions import ConfigurationError, LexiconError
from .dictionary import GovernedDictionary, _remember
from .enums import EntryKind, ExpansionSource, UnknownPolicy
from .models import GovernedEntry, IdentifierExpansion, TokenExpansion
from .policy import NamingPolicy
from .tokenizer import split_identifier_parts

__all__ = ["expand_identifier", "expand_token"]


#: The policy applied when the caller names none. Built once rather than per
#: call, which is worth stating because it looks like a micro-optimisation and is
#: not one: a :class:`~acronymkit.governed.policy.NamingPolicy` is frozen, so one
#: shared instance and a fresh equal instance are the same policy in every way a
#: caller can observe, and the difference between them is two costs that a
#: single-token call cannot amortise. Constructing one validates nine fields, and
#: the dictionary's memo is kept per policy and matched by value, so a caller who
#: passes ``policy=None`` was paying for a new object and then paying again to
#: discover it equalled the last one. Together that is most of the cost of
#: expanding one already-known token.
#:
#: :mod:`acronymkit.governed.compliance` and :mod:`acronymkit.governed.naming`
#: still build their own default per call; the same constant would do the same
#: thing for them.
_DEFAULT_POLICY = NamingPolicy.governed_default()


def _title_case(token: str) -> str:
    """Capitalise the first character of ``token`` and lower the rest.

    Spelled out here rather than reached for from
    :class:`~acronymkit.enums.CaseStyle`, which applies the same rule, because
    how an unknown token is rendered is part of *this* subsystem's published
    contract. If the generation-side casing rule ever changes, a governed
    passthrough must not change with it.

    ``str.title`` is deliberately not used: it re-capitalises after every
    non-letter, so a token that survived the splitter with a digit in it would
    come back as ``Address2Line`` rather than ``Address2line``.

    Args:
        token: A surface token, already non-empty.

    Returns:
        The Title Cased form.
    """
    return token[:1].upper() + token[1:].lower()


def _require_dictionary(dictionary: Optional[GovernedDictionary], verb: str) -> GovernedDictionary:
    """Reject a governed call that was given no governed vocabulary.

    Args:
        dictionary: The caller's vocabulary, possibly ``None``.
        verb: The public function's name, so the message names the call site.

    Returns:
        The vocabulary, unchanged.

    Raises:
        ConfigurationError: If ``dictionary`` is ``None``. It is a
            :class:`ValueError` as well as an
            :class:`~acronymkit.exceptions.AcronymKitError`, so it is catchable
            either way.
    """
    if dictionary is None:
        raise ConfigurationError(
            f"{verb}() requires a governed vocabulary, and dictionary=None is not one. "
            "Pass a GovernedDictionary. If you want every token to pass through "
            "untouched, pass an empty GovernedDictionary() and say so explicitly."
        )
    return dictionary


def _prepare(
    dictionary: Optional[GovernedDictionary],
    policy: Optional[NamingPolicy],
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]],
    verb: str,
) -> tuple[GovernedDictionary, NamingPolicy]:
    """Resolve the three arguments every governed verb shares.

    ``custom`` is layered for this call only: the caller's dictionary is never
    modified, and the layered copy is discarded when the call returns. Layering
    is cheap by design — see
    :meth:`~acronymkit.governed.dictionary.GovernedDictionary.with_custom` — so
    a per-call overlay is affordable inside a loop over a schema.

    Args:
        dictionary: The caller's vocabulary.
        policy: The caller's policy, or ``None`` for the default.
        custom: A call-scoped overlay, or ``None``.
        verb: The public function's name, for the error message.

    Returns:
        The vocabulary to use and the policy to apply.

    Raises:
        ConfigurationError: If ``dictionary`` is ``None``.
    """
    catalog = _require_dictionary(dictionary, verb)
    if custom:
        catalog = catalog.with_custom(custom)
    return catalog, policy if policy is not None else _DEFAULT_POLICY


def _empty_expansion(raw: str) -> TokenExpansion:
    """Return the expansion of nothing.

    The expansion of an empty token is an empty string, reported as unknown with
    zero confidence. Returning it rather than raising is what keeps a batch over
    a schema export from stopping on a blank cell, and it is why
    :attr:`~acronymkit.governed.models.TokenExpansion.long` is documented as
    ``""`` for empty input.

    ``UnknownPolicy.REJECT`` is not consulted. That policy is about a token the
    catalog does not recognise; absent input is not a token at all, and a
    vocabulary cannot be out of date with respect to a blank.

    Args:
        raw: The input as supplied, so the caller can align the result back onto
            its own row. ``None`` is recorded as ``""``.

    Returns:
        The empty expansion.
    """
    return TokenExpansion(
        raw=raw,
        long="",
        is_known=False,
        source=ExpansionSource.PASSTHROUGH,
        entry_id=None,
        confidence=0.0,
        class_word=None,
        beat=(),
        kind=None,
    )


def _expand(token: str, dictionary: GovernedDictionary, policy: NamingPolicy) -> TokenExpansion:
    """Expand one already-non-empty token against a prepared vocabulary.

    The shared body of both public verbs. It is separate so that
    :func:`expand_identifier` layers an overlay and resolves a policy once for
    the whole identifier rather than once per token.

    The answer is a pure function of ``(token, dictionary, policy)``, and a
    schema asks the same question thousands of times — ``ID``, ``DT`` and ``CD``
    between them account for a sixth of the fixture corpus's tokens — so it is
    remembered on the dictionary, which is the object whose lifetime the answer
    is valid for. See the
    :mod:`~acronymkit.governed.dictionary` module docstring for what makes that
    safe; the two conditions this end has to meet are:

    * the key is the **surface** token, not the lookup key, because ``raw``
      reports the spelling that was given — ``txn`` and ``TXN`` resolve alike and
      do not expand alike; and
    * a **passthrough is not remembered**. It is not an answer the vocabulary
      gave, so caching it would key the memo by the caller's names rather than by
      the catalog (see :class:`~acronymkit.governed.dictionary._Memo`), and it
      would put a policy-dependent raise behind a lookup: ``UnknownPolicy.REJECT``
      raises here rather than returning, and the one thing a cache must never do
      is answer a question that was supposed to stop the pipeline.

    Two callers can now hold the same :class:`TokenExpansion` object rather than
    two equal ones. The models are frozen, so the only way to tell is ``is``.

    Args:
        token: A surface token as it appeared in the input.
        dictionary: The vocabulary, with any call-scoped overlay already layered.
        policy: The resolved policy.

    Returns:
        The expansion, known or passed through.

    Raises:
        LexiconError: If the token is unknown and ``policy.unknown`` is
            ``UnknownPolicy.REJECT``.
    """
    memo = dictionary._memo(policy).expanded
    remembered = memo.get(token)
    if remembered is not None:
        return remembered
    entry = dictionary.resolve(token, policy)
    if entry is None:
        return _passthrough(token, dictionary, policy)
    winner = entry.canonical
    return _remember(
        memo,
        token,
        TokenExpansion(
            raw=token,
            long=winner,
            is_known=True,
            source=entry.source,
            entry_id=entry.entry_id,
            confidence=entry.confidence,
            class_word=entry.class_word or dictionary.class_word_for(token),
            beat=tuple(candidate for candidate in entry.candidates if candidate != winner),
            kind=entry.kind,
        ),
    )


def _passthrough(
    token: str, dictionary: GovernedDictionary, policy: NamingPolicy
) -> TokenExpansion:
    """Report a token the vocabulary does not contain.

    ``beat`` is empty, because nothing was chosen over anything: a passthrough
    is the absence of a decision, not a decision that went a particular way.
    ``confidence`` is zero for the same reason — it is not low confidence in an
    answer, it is the absence of one. A class word is still reported when the
    class-word map names the token, since "what kind of value does this column
    hold" and "what does this token expand to" are separate questions and the
    map can answer the first without the catalog answering the second.

    Args:
        token: The unknown token.
        dictionary: The vocabulary, consulted only for the class-word map.
        policy: The resolved policy; ``unknown`` is read here.

    Returns:
        The passthrough expansion.

    Raises:
        LexiconError: If ``policy.unknown`` is ``UnknownPolicy.REJECT``. No
            exception in this library's hierarchy names "the governed
            vocabulary is missing a token", so the vocabulary error is used and
            the message says which token was missing.
    """
    if policy.unknown is UnknownPolicy.REJECT:
        raise LexiconError(
            f"Token {token!r} is not in the governed vocabulary and "
            "NamingPolicy.unknown is REJECT. Add a catalog row or an allow-list entry "
            "for it, supply it through custom=, or use a policy whose unknown handling "
            "is PASSTHROUGH_TITLECASE."
        )
    return TokenExpansion(
        raw=token,
        long=_title_case(token),
        is_known=False,
        source=ExpansionSource.PASSTHROUGH,
        entry_id=None,
        confidence=0.0,
        class_word=dictionary.class_word_for(token),
        beat=(),
        kind=EntryKind.PASSTHROUGH,
    )


def _rejoin_digit_tokens(
    tokens: tuple[str, ...], dictionary: GovernedDictionary, policy: NamingPolicy
) -> tuple[str, ...]:
    """Second pass: put back a digit-leading token the catalog vouches for.

    :func:`~acronymkit.governed.tokenizer.split_identifier` splits at every
    letter/digit boundary, so ``1MM`` arrives here as ``('1', 'MM')`` — and
    there is nothing in the string ``1MM`` that says it should not, since it has
    exactly the shape of ``7Code``, which must split. Some catalogs do carry a
    digit-leading token (``1MM`` for a one-million unit, ``2FA``, ``3DS``), and
    the only thing that can tell the two apart is a governed vocabulary.

    Hence the two passes. The tokenizer runs first and knows nothing but
    orthography; this pass runs second, knows the catalog, and repairs exactly
    the case the catalog vouches for. A digit token is joined to the token after
    it, the joined form is tried as a lookup, and both are consumed only when it
    resolves. Everything else falls through untouched — ``address2line1`` stays
    four tokens because no catalog carries ``2line``.

    Putting the rule in the tokenizer instead would make its output a function
    of somebody's vocabulary rather than of its input: the same identifier would
    split one way against a catalog holding ``1MM`` and another way against one
    that does not, and a fixture recording the split would be a fixture of a
    dictionary.

    One consequence is worth stating plainly. The tokenizer's output does not
    record whether a separator stood between two tokens, so ``TXN_1_MM`` and
    ``TXN_1MM`` are the same sequence by the time this runs and both yield
    ``1MM``. That is defensible — the catalog vouches for the joined token
    either way — but it means the join is over the token sequence, not over the
    original spelling.

    Args:
        tokens: The tokenizer's output, in order.
        dictionary: The vocabulary, with any call-scoped overlay layered.
        policy: The resolved policy, so the join sees the same vocabulary the
            expansion will.

    Returns:
        The tokens with any vouched-for digit-leading form restored.
    """
    merged: list[str] = []
    index = 0
    total = len(tokens)
    while index < total:
        current = tokens[index]
        if current.isdigit() and index + 1 < total:
            joined = current + tokens[index + 1]
            if dictionary.resolve(joined, policy) is not None:
                merged.append(joined)
                index += 2
                continue
        merged.append(current)
        index += 1
    return tuple(merged)


def expand_token(
    token: Optional[str],
    dictionary: Optional[GovernedDictionary],
    policy: Optional[NamingPolicy] = None,
    *,
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
) -> TokenExpansion:
    """Expand one governed token into its long form, with provenance.

    The token is looked up whole — no splitting, no stripping of separators. Use
    :func:`expand_identifier` for anything that might be more than one token.

    A token the vocabulary contains comes back with ``is_known=True``, the
    catalog's confidence, the row's ``entry_id``, the rule that decided it in
    ``source``, and the candidate long forms it beat in ``beat``. A token the
    vocabulary does not contain comes back Title Cased with ``is_known=False``,
    ``confidence=0.0`` and ``source=PASSTHROUGH`` — the library declining to
    guess, which is a feature and is described at length in the module
    docstring.

    Args:
        token: The token, matched case-insensitively. ``None``, ``""`` and
            whitespace return an expansion whose ``long`` is ``""``; this never
            raises, so a blank cell does not stop a batch.
        dictionary: The governed vocabulary. Required — see the module
            docstring for why ``None`` is refused and what to pass instead.
        policy: The rules to apply. ``None`` means
            :meth:`~acronymkit.governed.policy.NamingPolicy.governed_default`.
        custom: A caller-supplied overlay layered for this call only, on top of
            any overlay the dictionary already carries. ``{"XYZ": "Exchange"}``
            or ``{"XYZ": GovernedEntry(...)}``. It outranks the catalog, subject
            to ``policy.allow_override``.

    Returns:
        The expansion, always. The only failures are a missing dictionary and an
        explicit ``REJECT`` policy.

    Raises:
        ConfigurationError: If ``dictionary`` is ``None``.
        LexiconError: If the token is unknown and ``policy.unknown`` is
            ``UnknownPolicy.REJECT``.

    Example:
        >>> from acronymkit.governed import GovernedDictionary, expand_token
        >>> catalog = GovernedDictionary.from_mapping({"TXN": "Transaction"})
        >>> expand_token("txn", catalog).long
        'Transaction'
        >>> unknown = expand_token("KYC", catalog)
        >>> unknown.long, unknown.is_known, unknown.confidence
        ('Kyc', False, 0.0)
        >>> expand_token("KYC", catalog, custom={"KYC": "Know Your Customer"}).long
        'Know Your Customer'
    """
    catalog, active = _prepare(dictionary, policy, custom, "expand_token")
    text = token.strip() if token else ""
    if not text:
        return _empty_expansion(token or "")
    return _expand(text, catalog, active)


def expand_identifier(
    identifier: Optional[str],
    dictionary: Optional[GovernedDictionary],
    policy: Optional[NamingPolicy] = None,
    *,
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
) -> IdentifierExpansion:
    """Expand a whole physical identifier, token by token, with provenance.

    ``TXN_APPLNT_ID`` becomes the phrase "Transaction Applicant Identifier",
    three :class:`~acronymkit.governed.models.TokenExpansion` records each
    carrying its own audit trail, and the class word read off the trailing
    token.

    Five things about the shape of the answer are worth knowing before relying
    on it.

    **The class word comes from the trailing token and nowhere else.** Position
    is the whole rule: a class word anywhere but the end is an ordinary word, so
    ``APPLNT_VERIF_DT`` names a date and ``DT_APPLNT_VERIF`` does not. Each
    token still reports the class word *it* designates, so the per-token records
    are not lying about ``DT``; it is the identifier-level field that reads only
    the last one.

    **Every token is a token, including an ordinal.** ``ADDR_LINE_1`` splits to
    three, and unless the vocabulary has a row or an allow-list entry for ``1``,
    that token passes through and ``is_fully_known`` is ``False``. That is the
    honest report — the catalog has nothing to say about ``1`` — and the fix is
    to say something about it, through an allow-list or ``custom=``.

    **A digit-leading catalog token is repaired in a second pass.** ``1MM``
    splits to ``('1', 'MM')`` and is put back only because the catalog carries
    it; see :func:`_rejoin_digit_tokens` for why that belongs here rather than
    in the tokenizer.

    **Nothing in the name is discarded in silence.** A character that is neither
    a letter, a digit, nor one of the separators the tokenizer accounts for —
    an emoji, a currency sign, a stray control character — is listed on
    ``unaccounted`` and makes ``is_fully_known`` ``False``. It is reported rather
    than turned into a token because it is not a word and no catalog row could
    ever answer for it; the fix is to the name, not to the vocabulary.

    **A qualified name keeps its qualifier.** ``.`` is an ordinary separator, so
    ``db.schema.TXN_ID`` expands to a phrase beginning "Db Schema". Pass
    :func:`~acronymkit.governed.tokenizer.strip_qualifier` yourself when the
    input really is a qualified path and the leaf is what you want; this
    function will not decide that for you, because ``nds.risk-model`` is one
    name with a dot in it and nothing in either string says which is which.

    Args:
        identifier: A physical name — a column, table or attribute identifier.
            ``None``, ``""`` and separator-only input all return an empty
            result rather than raising.
        dictionary: The governed vocabulary. Required — see the module
            docstring for why ``None`` is refused and what to pass instead.
        policy: The rules to apply. ``None`` means
            :meth:`~acronymkit.governed.policy.NamingPolicy.governed_default`.
        custom: A caller-supplied overlay layered for this call only. Layered
            once for the whole identifier, not once per token.

    Returns:
        The expansion. ``tokens`` is empty and ``phrase`` is ``""`` when the
        identifier holds no letters or digits; ``is_fully_known`` is ``True``
        for that case, vacuously, since there is no token that failed to
        resolve and nothing went unaccounted for — the empty ``tokens`` tuple is
        what says nothing was expanded. An identifier made only of characters
        the tokenizer cannot read is *not* that case: it tokenises to nothing
        and reports every one of them on ``unaccounted``, so ``is_fully_known``
        is ``False``.

    Raises:
        ConfigurationError: If ``dictionary`` is ``None``.
        LexiconError: If any token is unknown and ``policy.unknown`` is
            ``UnknownPolicy.REJECT``. The first such token stops the call.

    Example:
        >>> from acronymkit.governed import GovernedDictionary, expand_identifier
        >>> catalog = GovernedDictionary.from_mapping(
        ...     {"TXN": "Transaction", "APPLNT": "Applicant", "ID": "Identifier"},
        ...     class_words={"ID": "Identifier"},
        ... )
        >>> result = expand_identifier("TXN_APPLNT_ID", catalog)
        >>> result.phrase
        'Transaction Applicant Identifier'
        >>> result.class_word, result.is_fully_known
        ('Identifier', True)
        >>> partial = expand_identifier("TXN_KYC_ID", catalog)
        >>> partial.phrase, partial.is_fully_known
        ('Transaction Kyc Identifier', False)
        >>> [token.raw for token in partial.unknown_tokens]
        ['KYC']
        >>> lossy = expand_identifier("TXN_\\U0001F600_ID", catalog)
        >>> lossy.phrase, lossy.is_fully_known, lossy.unaccounted == ("\\U0001F600",)
        ('Transaction Identifier', False, True)
    """
    catalog, active = _prepare(dictionary, policy, custom, "expand_identifier")
    text = identifier or ""
    parts = split_identifier_parts(text)
    tokens = _rejoin_digit_tokens(parts.tokens, catalog, active)
    expansions = tuple(_expand(token, catalog, active) for token in tokens)
    return IdentifierExpansion(
        identifier=text,
        phrase=" ".join(expansion.long for expansion in expansions if expansion.long),
        tokens=expansions,
        class_word=expansions[-1].class_word if expansions else None,
        is_fully_known=not parts.unaccounted
        and all(expansion.is_known for expansion in expansions),
        unaccounted=parts.unaccounted,
    )
