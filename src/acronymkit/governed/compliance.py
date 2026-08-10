"""The verifier: does this physical name conform to the governed standard?

:func:`is_compliant` checks a name somebody else wrote and returns a verdict per
token — which rule accepted it, or which rule rejected it and what to write
instead. :func:`normalize` applies the corrections that check can justify, in
one pass, and is idempotent.

Neither invents anything. A token the vocabulary does not cover is reported as
not approved, with no suggested replacement, because the only replacements this
module will propose are ones the catalog already names.

Why the verdict is never a bare boolean
---------------------------------------
``False`` is not actionable. A name fails because of *something*, and the
something is almost always one token out of six. So every finding names the
token it is about, carries a machine-readable
:class:`~acronymkit.governed.enums.ComplianceReasonCode`, a sentence for a
person, and — when the vocabulary supplies one — the concrete thing to write
instead. Passing tokens get findings too, so a review can see *why* a name was
accepted rather than only that it was.

Whole-name findings (casing, a missing trailing class word, length, an empty
name) carry ``token=None``. They are emitted only on failure: the five codes
that name a defect would read as their own opposite attached to a ``PASS``
verdict, and "this name is not NOT_UPPER_SNAKE" is not a sentence worth putting
in an audit trail.

Each ``fix`` is the smallest edit that clears *its own* finding and nothing
else, so a caller can apply one without silently accepting another. The casing
fix re-cases and does not touch the tokens; the class-word fix appends and does
not re-case. ``EXCEEDS_MAX_LENGTH`` is the exception, because there is no
minimal edit that clears it — nothing here shortens a name — so what it offers
instead is the governed rewrite, and only when that rewrite happens to fit.

The false positive this exists to avoid
----------------------------------------
The naive rule for "is this token an unapproved abbreviation" is *two to five
capital letters*, and it is wrong on ``FRAUD``, ``STATE``, ``PHONE``, ``MODEL``,
``OWNER``, ``PARTY``, ``RISK``, ``BATCH``, ``LEVEL`` and every other short
English word a schema uses — all of which are whole words, none of which is an
abbreviation, and all of which a governed standard permits. That is why the
allow-lists are consulted **before** any correction is proposed, and why
``SHORT_FULL_WORD`` and ``COMMON_KEYWORD`` are reason codes of their own: a
reviewer reading "``FRAUD``: short full word, accepted" learns something, and a
reviewer reading "``FRAUD``: unapproved abbreviation, did you mean ``FRD``?"
learns something false.

The order the rules are consulted in
------------------------------------
Highest first, matching the resolution order the rest of the package uses::

    1. the caller's overlay          -> CUSTOM_ABBREV
    2. approved_abbreviations        -> APPROVED_ABBREV
    3. common_keywords               -> COMMON_KEYWORD
    4. short_full_words              -> SHORT_FULL_WORD
    5. the catalog entry's own kind  -> PROPER_NOUN_ACRONYM / SHORT_FULL_WORD /
                                        APPROVED_ABBREV
    6. nothing                       -> UNAPPROVED_ABBREV, and a fix when the
                                        catalog names one

Rules 2 to 4 are in that order because a token may sit in more than one list and
something has to decide; putting the abbreviation list first means a token
approved *as an abbreviation* is reported as one. Rule 5 comes after the lists
so that a proper-noun acronym the catalog carries but no list mentions —
``ZIP``, ``ABA``, ``ATM`` — reports ``PROPER_NOUN_ACRONYM`` rather than the
blander approved-abbreviation code, which is a distinction a review turns on.
Rule 5 also accepts a class-word entry: a standard that requires every name to
end in ``DT`` and then flags ``DT`` as unapproved is arguing with itself.

Tokens that hold no letters — the ``1`` and ``2`` of ``ADDR_LINE_1_TXT`` — get
no finding at all. They are ordinals and version markers, not abbreviations, so
the abbreviation rules have nothing to say about them, and there is no reason
code that describes one honestly. Reported as a gap rather than forced into
``SHORT_FULL_WORD``.

Idempotence
-----------
``normalize(normalize(x)) == normalize(x)`` for every ``x``, and it holds by
construction rather than by testing: a rewrite is proposed **only when its
target is approved**, so the second pass finds an approved token, has nothing to
propose, and returns it unchanged. When the catalog offers nothing approved the
token is left exactly as it was, which is also a fixed point. Both branches
terminate after one step, so no cycle of "unapproved token A rewrites to
unapproved token B rewrites to A" can exist.

``normalize`` and ``is_compliant`` share one decision ladder — ``normalize``
applies precisely the ``fix`` that ``is_compliant`` reports — so the check and
the correction cannot drift apart into two different opinions about the same
name.

What ``normalize`` does not do
------------------------------
It does not append a missing class word. The contract marks
``append_class_word_when_missing`` as affecting ``to_physical_name`` only, and a
verifier that quietly extended a name it was asked to check would be editing the
caller's schema. So ``normalize`` is not a promise of compliance: it fixes
casing and rewrites unapproved abbreviations to their approved forms, and a name
that is still missing its class word afterwards is still reported as such.

**It never shortens a name.** Under
:meth:`~acronymkit.governed.policy.NamingPolicy.strict_length` an over-long name
is reported with ``EXCEEDS_MAX_LENGTH`` and returned whole. The suggested fix,
where there is one, is the governed rewrite — which is sometimes shorter because
``CUSTMR`` becomes ``CUST`` — and never a name with a token dropped out of it.
No code path here removes a token to make a name fit.

Worked examples use the fictional **Northwind Data Standards** (``NDS``) catalog
with synthetic ids. Nothing here describes a real organisation's standard.
"""

from __future__ import annotations

from typing import Mapping, Optional, Union

from ..exceptions import ConfigurationError
from .dictionary import GovernedDictionary
from .enums import ComplianceReasonCode, EntryKind, ExpansionSource, Verdict
from .expansion import _rejoin_digit_tokens
from .models import ComplianceReason, ComplianceResult, GovernedEntry
from .naming import DEFAULT_CLASS_WORD
from .policy import NamingPolicy
from .tokenizer import split_identifier

__all__ = ["is_compliant", "normalize"]


#: Entry kinds that approve a token on the strength of the catalog row alone,
#: with the reason code each one reports. A ``keep_as_abbrev`` entry of any other
#: kind is handled separately: the flag, not the kind, is what says "this token
#: IS the governed physical form".
_KIND_CODES = {
    EntryKind.PROPER_NOUN_ACRONYM: ComplianceReasonCode.PROPER_NOUN_ACRONYM,
    EntryKind.SHORT_FULL_WORD: ComplianceReasonCode.SHORT_FULL_WORD,
    EntryKind.CLASS_WORD_ABBREV: ComplianceReasonCode.APPROVED_ABBREV,
}


def _is_upper_snake(name: str) -> bool:
    """Whether ``name`` is written in ``UPPER_SNAKE`` form.

    Underscore-separated runs of upper-case letters and digits, with no empty
    run — which rules out a leading underscore, a trailing one and a doubled one
    in the middle, each of which produces a different name after splitting than
    the one that was written.

    Letters with no case of their own are accepted rather than rejected. A CJK
    or Hebrew character cannot be "upper case", and refusing a name for
    containing one would be enforcing an alphabet rather than a convention.

    Args:
        name: The physical name as supplied.

    Returns:
        ``True`` when the name is already in the governed form.
    """
    if not name:
        return False
    parts = name.split("_")
    if any(not part for part in parts):
        return False
    return all(
        character.isdigit() or (character.isalpha() and not character.islower())
        for part in parts
        for character in part
    )


def _allow_list_code(
    dictionary: GovernedDictionary, token: str
) -> Optional[tuple[ComplianceReasonCode, str]]:
    """Which allow-list holds ``token``, and what that justifies.

    The three lists are read directly rather than through the shared
    ``is_approved`` predicate, because ``is_approved`` answers *whether* a token
    is approved and the reason codes need to know *which list said so*. That
    distinction is the whole value of ``COMMON_KEYWORD`` and
    ``SHORT_FULL_WORD``: "``FRAUD`` is a word" and "``FRAUD`` is an approved
    abbreviation" are different statements, and only one of them is true.

    The order below decides for a token that sits in more than one list, and it
    is the order a naming standard states its own rules in: approved
    abbreviations, then permitted vocabulary, then words that need no approval
    because they are words. A token in two lists is reported by the first, which
    is a decision worth being able to point at rather than an accident of set
    iteration.

    Args:
        dictionary: The vocabulary to consult.
        token: The token, upper-cased.

    Returns:
        The reason code and the list's name for the message, or ``None`` when no
        list holds the token.
    """
    if token in dictionary.approved_abbreviations:
        return ComplianceReasonCode.APPROVED_ABBREV, "an approved abbreviation"
    if token in dictionary.common_keywords:
        return ComplianceReasonCode.COMMON_KEYWORD, "a common keyword"
    if token in dictionary.short_full_words:
        return ComplianceReasonCode.SHORT_FULL_WORD, "a genuine short word, not an abbreviation"
    return None


def _approved_form(
    dictionary: GovernedDictionary,
    entry: Optional[GovernedEntry],
    token: str,
) -> Optional[str]:
    """The approved token to write instead of ``token``, when the catalog names one.

    Found by going through the long form: the entry says what the token means,
    and the reverse index says which token the standard approves for that
    meaning. ``CUSTMR`` means "Customer", "Customer" abbreviates to ``CUST``, so
    the fix is ``CUST``.

    A replacement is proposed **only when it is itself approved**. That is the
    condition that makes :func:`normalize` idempotent — the second pass sees an
    approved token and proposes nothing — and it is also the honest rule: an
    unapproved token rewritten to another unapproved token has not been fixed.

    Args:
        dictionary: The vocabulary to consult.
        entry: The catalog entry for ``token``, or ``None`` when there is none.
        token: The token, upper-cased.

    Returns:
        The approved token, or ``None`` when the catalog does not name one —
        which is every case where the token is simply unknown. Suggesting a
        replacement the catalog cannot justify would be guessing.
    """
    if entry is None:
        return None
    target = dictionary.abbreviate(entry.canonical)
    if target is None or target.token == token:
        return None
    return target.token if dictionary.is_approved(target.token) else None


def _token_finding(
    dictionary: GovernedDictionary,
    policy: NamingPolicy,
    token: str,
) -> ComplianceReason:
    """Judge one token against the vocabulary.

    The ladder in the module docstring, in order. Every branch produces a
    finding; the ``fix`` on the failing one is what :func:`normalize` applies,
    which is what keeps the check and the correction in agreement.

    Args:
        dictionary: The vocabulary, with any call-time overlay applied.
        policy: The active policy, passed to ``resolve`` so that a demoted
            overlay is not reported as an approval.
        token: One token of the name, exactly as it was written.

    Returns:
        One finding for this token.
    """
    upper = token.upper()
    entry = dictionary.resolve(upper, policy)

    if entry is not None and entry.source is ExpansionSource.CUSTOM:
        return ComplianceReason(
            token=token,
            verdict=Verdict.PASS,
            code=ComplianceReasonCode.CUSTOM_ABBREV,
            detail=f"{upper} is approved by the caller's overlay, not by the catalog.",
        )

    listed = _allow_list_code(dictionary, upper)
    if listed is not None:
        code, description = listed
        return ComplianceReason(
            token=token,
            verdict=Verdict.PASS,
            code=code,
            detail=f"{upper} is {description}.",
        )

    if entry is not None:
        kind_code = _KIND_CODES.get(entry.kind)
        if kind_code is not None:
            return ComplianceReason(
                token=token,
                verdict=Verdict.PASS,
                code=kind_code,
                detail=f"{upper} is a {entry.kind.value.replace('_', ' ')} in the catalog.",
            )
        if entry.keep_as_abbrev:
            return ComplianceReason(
                token=token,
                verdict=Verdict.PASS,
                code=ComplianceReasonCode.APPROVED_ABBREV,
                detail=f"{upper} is the governed physical form of {entry.canonical!r}.",
            )

    if dictionary.is_approved(upper):
        return ComplianceReason(
            token=token,
            verdict=Verdict.PASS,
            code=ComplianceReasonCode.APPROVED_ABBREV,
            detail=f"{upper} is approved by the vocabulary.",
        )

    fix = _approved_form(dictionary, entry, upper)
    if fix is not None:
        detail = f"{upper} is not an approved abbreviation; the approved form is {fix}."
    elif entry is not None:
        detail = (
            f"{upper} is not an approved abbreviation, and the catalog names no "
            f"approved form for {entry.canonical!r}."
        )
    else:
        detail = f"{upper} is not in the governed vocabulary, so nothing approves it."
    return ComplianceReason(
        token=token,
        verdict=Verdict.FAIL,
        code=ComplianceReasonCode.UNAPPROVED_ABBREV,
        detail=detail,
        fix=fix,
    )


def _judge(
    dictionary: GovernedDictionary,
    policy: NamingPolicy,
    tokens: tuple[str, ...],
) -> tuple[tuple[ComplianceReason, ...], str]:
    """Judge every token once, and build the corrected name from the same verdicts.

    The single place the two verbs share. :func:`is_compliant` reports the
    findings and :func:`normalize` returns the name, and because the name is
    assembled out of the findings' own ``fix`` values the check and the
    correction cannot come to different conclusions about a token.

    A token holding no letters is passed through untouched and produces no
    finding; see the module docstring.

    Args:
        dictionary: The vocabulary, with any call-time overlay applied.
        policy: The active policy.
        tokens: The name's tokens, in order.

    Returns:
        The per-token findings, in token order, and the corrected name.
    """
    findings: list[ComplianceReason] = []
    corrected: list[str] = []
    for token in tokens:
        if not any(character.isalpha() for character in token):
            corrected.append(token)
            continue
        finding = _token_finding(dictionary, policy, token)
        findings.append(finding)
        corrected.append(finding.fix or token.upper())
    return tuple(findings), "_".join(corrected)


def _trailing_class_word(dictionary: GovernedDictionary, tokens: tuple[str, ...]) -> Optional[str]:
    """The class word the name ends in, or ``None``.

    Position is the whole rule: a class word anywhere but the end is an ordinary
    word, so only the trailing token is inspected. ``class_word_for`` already
    accepts both spellings a standard permits — the abbreviation (``..._DT``) and
    the word written out (``..._DATE``) — so this adds only one thing: a name
    ending in a class word's long form is still recognised when the dictionary
    was built from entries alone, with no class-word map to look the long form up
    in. The entry behind the word knows which class word it designates.

    Args:
        dictionary: The vocabulary, with any call-time overlay applied.
        tokens: The name's tokens, in order.

    Returns:
        The class word's long form, as the vocabulary states it, or ``None``.
    """
    if not tokens:
        return None
    token = tokens[-1]
    direct = dictionary.class_word_for(token)
    if direct is not None:
        return direct
    entry = dictionary.abbreviate(token)
    return entry.class_word if entry is not None else None


def _prepare(
    name: str,
    dictionary: GovernedDictionary,
    policy: Optional[NamingPolicy],
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]],
    verb: str,
) -> tuple[NamingPolicy, GovernedDictionary, tuple[str, ...]]:
    """Shared entry work for both verbs: validate, default, layer, tokenise.

    Args:
        name: The physical name as supplied.
        dictionary: The governed vocabulary.
        policy: The caller's policy, or ``None``.
        custom: The call-time overlay, or ``None``.
        verb: The public function's name, for the error message.

    Returns:
        The active policy, the dictionary with the overlay layered on, and the
        name's tokens with digit-leading catalog forms rejoined.

    Raises:
        ConfigurationError: If ``dictionary`` is ``None``.
    """
    if dictionary is None:
        raise ConfigurationError(
            f"{verb} requires a governed vocabulary, and dictionary was None. Pass a "
            "GovernedDictionary; an empty GovernedDictionary() is the supported way to "
            "check a name against a vocabulary that governs nothing."
        )
    active = NamingPolicy.governed_default() if policy is None else policy
    layered = dictionary.with_custom(custom) if custom else dictionary
    return active, layered, _rejoin_digit_tokens(split_identifier(name), layered, active)


def is_compliant(
    name: str,
    dictionary: GovernedDictionary,
    policy: Optional[NamingPolicy] = None,
    *,
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
) -> ComplianceResult:
    """Check a physical name against the governed standard, token by token.

    Produces one finding per token — passing findings included — followed by the
    whole-name findings that failed. See the module docstring for the order the
    rules are consulted in and for why the allow-lists come before any proposed
    correction.

    Args:
        name: The physical name to check, as somebody wrote it. Any casing is
            accepted; a name that is not ``UPPER_SNAKE`` is reported as such
            rather than rejected out of hand.
        dictionary: The governed vocabulary. Required.
        policy: ``None`` means
            :meth:`~acronymkit.governed.policy.NamingPolicy.governed_default`.
            ``require_trailing_class_word`` and ``enforce_name_length`` decide
            whether those two whole-name findings are produced at all;
            ``allow_override`` decides whether a contradicting overlay counts as
            an approval.
        custom: A caller-supplied overlay layered for this call only.

    Returns:
        A :class:`~acronymkit.governed.models.ComplianceResult`. ``compliant`` is
        ``True`` when no finding carries a ``FAIL`` verdict.

    Raises:
        ConfigurationError: If ``dictionary`` is ``None``.

    Example:
        >>> from acronymkit.governed import GovernedDictionary, is_compliant
        >>> catalog = GovernedDictionary.from_mapping(
        ...     {"TXN": "Transaction", "ID": "Identifier"},
        ...     approved_abbreviations=["TXN", "ID"],
        ...     class_words={"ID": "Identifier"},
        ... )
        >>> is_compliant("TXN_ID", catalog).compliant
        True
        >>> result = is_compliant("txn xyz", catalog)
        >>> [reason.code.value for reason in result.failures]
        ['unapproved_abbrev', 'not_upper_snake', 'missing_class_word']
        >>> result.ends_in_class_word
        False
    """
    active, layered, tokens = _prepare(name, dictionary, policy, custom, "is_compliant")

    if not tokens:
        return ComplianceResult(
            name=name,
            compliant=False,
            reasons=(
                ComplianceReason(
                    token=None,
                    verdict=Verdict.FAIL,
                    code=ComplianceReasonCode.EMPTY_NAME,
                    detail="There is no name to check: it is empty, or holds only separators.",
                ),
            ),
            ends_in_class_word=False,
            class_word=None,
        )

    judged, rewritten = _judge(layered, active, tokens)
    findings = list(judged)

    if not _is_upper_snake(name):
        findings.append(
            ComplianceReason(
                token=None,
                verdict=Verdict.FAIL,
                code=ComplianceReasonCode.NOT_UPPER_SNAKE,
                detail="A governed physical name is written in UPPER_SNAKE form.",
                fix="_".join(token.upper() for token in tokens),
            )
        )

    class_word = _trailing_class_word(layered, tokens)
    if active.require_trailing_class_word and class_word is None:
        suggestion = (
            f"{'_'.join(token.upper() for token in tokens)}_{DEFAULT_CLASS_WORD}"
            if layered.class_word_for(DEFAULT_CLASS_WORD) is not None
            else None
        )
        findings.append(
            ComplianceReason(
                token=None,
                verdict=Verdict.FAIL,
                code=ComplianceReasonCode.MISSING_CLASS_WORD,
                detail=(
                    f"The name ends in {tokens[-1].upper()!r}, which the vocabulary does "
                    "not designate as a class word, so the name does not say what kind of "
                    "value the column holds."
                ),
                fix=suggestion,
            )
        )

    if active.enforce_name_length and len(name) > active.max_name_length:
        over = len(name) - active.max_name_length
        findings.append(
            ComplianceReason(
                token=None,
                verdict=Verdict.FAIL,
                code=ComplianceReasonCode.EXCEEDS_MAX_LENGTH,
                detail=(
                    f"The name is {len(name)} characters, {over} over the "
                    f"{active.max_name_length}-character limit. Nothing here shortens a "
                    "name; shorten the logical name and render it again."
                ),
                fix=(
                    rewritten
                    if rewritten != name and len(rewritten) <= active.max_name_length
                    else None
                ),
            )
        )

    return ComplianceResult(
        name=name,
        compliant=not any(finding.verdict is Verdict.FAIL for finding in findings),
        reasons=tuple(findings),
        ends_in_class_word=class_word is not None,
        class_word=class_word,
    )


def normalize(
    name: str,
    dictionary: GovernedDictionary,
    policy: Optional[NamingPolicy] = None,
    *,
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
) -> str:
    """Apply the corrections the vocabulary justifies, in one pass.

    Casing is normalised to ``UPPER_SNAKE`` and every unapproved abbreviation
    the catalog names an approved form for is rewritten to it — ``CUSTMR`` to
    ``CUST``, ``ACCNT`` to ``ACCT``. Everything else is left exactly as it
    stands, including tokens the vocabulary has never heard of: an unknown token
    rewritten to a guess is worse than an unknown token reported as unknown.

    Idempotent: ``normalize(normalize(x)) == normalize(x)``. See the module
    docstring for why that holds by construction rather than by testing.

    This is **not** a promise of compliance. It does not append a missing class
    word — the contract assigns that to ``to_physical_name`` — and it never
    shortens a name to fit a length limit. Run :func:`is_compliant` on the
    result to see what is left.

    Args:
        name: The physical name to correct, as somebody wrote it.
        dictionary: The governed vocabulary. Required.
        policy: ``None`` means
            :meth:`~acronymkit.governed.policy.NamingPolicy.governed_default`.
        custom: A caller-supplied overlay layered for this call only.

    Returns:
        The corrected name, rebuilt from its tokens — so a name written without
        separators gains them (``ADDRESS2LINE1`` becomes ``ADDRESS_2_LINE_1``),
        which is the same boundary judgement every other verb in this package
        makes about it. An empty or separator-only name yields ``""``, because a
        blank cell in a schema export should not stop a batch.

    Raises:
        ConfigurationError: If ``dictionary`` is ``None``.

    Example:
        >>> from acronymkit.governed import GovernedDictionary, normalize
        >>> catalog = GovernedDictionary.from_mapping(
        ...     {"TXN": "Transaction", "NBR": "Number", "NUM": "Number"},
        ...     approved_abbreviations=["TXN", "NBR"],
        ... )
        >>> normalize("txnNum", catalog)
        'TXN_NBR'
        >>> normalize(normalize("txnNum", catalog), catalog)
        'TXN_NBR'
    """
    active, layered, tokens = _prepare(name, dictionary, policy, custom, "normalize")
    return _judge(layered, active, tokens)[1]
