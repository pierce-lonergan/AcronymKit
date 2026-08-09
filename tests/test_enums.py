"""Behavioural tests for :mod:`acronymkit.enums`.

The enums are the wire format: every member's ``value`` appears verbatim in JSON
payloads governed by ``schemas/acronym-engine-result.schema.json`` and is
accepted as a plain string by :class:`~acronymkit.config.Config`. These tests
pin the values, the ``coerce()`` contract and the small amount of behaviour the
members carry.
"""

from __future__ import annotations

from typing import Optional

import pytest
from hypothesis import given
from hypothesis import strategies as st

from acronymkit.enums import (
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

# ---------------------------------------------------------------------------
# The frozen wire format
# ---------------------------------------------------------------------------
#: ``{enum class: {member name: wire value}}`` — exhaustive by construction, so
#: adding or renaming a member fails ``test_member_set_is_exhaustive``.
EXPECTED_VALUES = {
    EngineTier: {
        "ZERO_DEPENDENCY": "zero_dependency",
        "STATISTICAL_NLP": "statistical_nlp",
        "HYBRID_NLP": "hybrid_nlp",
        "NEURAL": "neural",
        "AUTO": "auto",
    },
    ScoringStrategy: {
        "STRICT_INITIALISM": "strict_initialism",
        "BALANCED_PRONOUNCEABLE": "balanced_pronounceable",
        "MAX_PRONOUNCEABLE": "max_pronounceable",
        "DICTIONARY_BACKRONYM": "dictionary_backronym",
        "CUSTOM": "custom",
    },
    TokenRole: {
        "CONTENT": "content",
        "FUNCTION": "function",
        "NUMERAL": "numeral",
        "SYMBOL": "symbol",
        "ACRONYM": "acronym",
        "UNKNOWN": "unknown",
    },
    StopWordCategory: {
        "ARTICLE": "article",
        "PREPOSITION": "preposition",
        "CONJUNCTION": "conjunction",
        "PRONOUN": "pronoun",
        "AUXILIARY": "auxiliary",
        "DETERMINER": "determiner",
        "PARTICLE": "particle",
        "OTHER": "other",
    },
    CaseStyle: {
        "UPPER": "upper",
        "LOWER": "lower",
        "TITLE": "title",
        "PRESERVE": "preserve",
    },
    MappingKind: {
        "INITIAL": "initial",
        "INTERNAL": "internal",
        "CONTIGUOUS": "contiguous",
        "UNMAPPED": "unmapped",
    },
    Language: {"EN": "en", "FR": "fr", "ES": "es", "DE": "de"},
    HyphenPolicy: {"SPLIT": "split", "MERGE": "merge", "FIRST_ONLY": "first_only"},
    NumeralPolicy: {"DIGIT": "digit", "WORD": "word", "SKIP": "skip"},
}

ENUM_CLASSES = list(EXPECTED_VALUES)

#: Every member of every enum, for the exhaustive parametrisations below.
ALL_MEMBERS = [member for enum_cls in ENUM_CLASSES for member in enum_cls]


def _ident(member: object) -> str:
    """Readable test id: ``EngineTier.AUTO``."""
    return f"{type(member).__name__}.{getattr(member, 'name', member)}"


# ---------------------------------------------------------------------------
# Members are strings with the documented values
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("member", ALL_MEMBERS, ids=_ident)
def test_member_is_a_string_with_the_expected_value(member: object) -> None:
    """Every member is a ``str`` whose value is the documented wire token."""
    expected = EXPECTED_VALUES[type(member)][member.name]  # type: ignore[attr-defined]
    assert isinstance(member, str)
    assert member.value == expected  # type: ignore[attr-defined]
    assert member == expected
    assert str(member) == expected
    # A str-enum must interoperate with plain strings in every direction.
    assert f"{member}" == expected
    assert expected in {member}


@pytest.mark.parametrize("enum_cls", ENUM_CLASSES, ids=lambda cls: cls.__name__)
def test_member_set_is_exhaustive(enum_cls: type) -> None:
    """No member is added, removed or renamed without updating the contract."""
    assert {member.name: member.value for member in enum_cls} == EXPECTED_VALUES[enum_cls]


@pytest.mark.parametrize("enum_cls", ENUM_CLASSES, ids=lambda cls: cls.__name__)
def test_values_are_unique(enum_cls: type) -> None:
    """Distinct members never share a wire value."""
    values = [member.value for member in enum_cls]
    assert len(set(values)) == len(values)


# ---------------------------------------------------------------------------
# coerce()
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("member", ALL_MEMBERS, ids=_ident)
def test_coerce_accepts_the_member_itself(member: object) -> None:
    """Coercing a member is the identity, not a copy."""
    assert type(member).coerce(member) is member  # type: ignore[attr-defined]


@pytest.mark.parametrize("member", ALL_MEMBERS, ids=_ident)
def test_coerce_accepts_value_name_and_mixed_case(member: object) -> None:
    """Values, names and arbitrary casing all resolve to the same member."""
    enum_cls = type(member)
    forms = [
        member.value,  # type: ignore[attr-defined]
        member.value.upper(),  # type: ignore[attr-defined]
        member.name,  # type: ignore[attr-defined]
        member.name.lower(),  # type: ignore[attr-defined]
        member.name.title(),  # type: ignore[attr-defined]
        f"  {member.value}  ",  # type: ignore[attr-defined]
        member.value.replace("_", "-"),  # type: ignore[attr-defined]
        member.name.replace("_", "-"),  # type: ignore[attr-defined]
    ]
    for form in forms:
        assert enum_cls.coerce(form) is member, form  # type: ignore[attr-defined]


@pytest.mark.parametrize("enum_cls", ENUM_CLASSES, ids=lambda cls: cls.__name__)
@pytest.mark.parametrize("bad", ["", "definitely-not-a-member", "   ", "0"], ids=repr)
def test_coerce_rejects_unknown_strings_listing_valid_options(enum_cls: type, bad: str) -> None:
    """The error names the offending input and enumerates every valid value."""
    with pytest.raises(ValueError) as excinfo:
        enum_cls.coerce(bad)
    message = str(excinfo.value)
    assert enum_cls.__name__ in message
    assert repr(bad) in message
    for member in enum_cls:
        assert member.value in message


@pytest.mark.parametrize("enum_cls", ENUM_CLASSES, ids=lambda cls: cls.__name__)
@pytest.mark.parametrize("bad", [None, 3, 4.5, object(), ["auto"]], ids=repr)
def test_coerce_rejects_non_string_objects(enum_cls: type, bad: object) -> None:
    """Anything that is neither a member nor a string is a ``ValueError``."""
    with pytest.raises(ValueError):
        enum_cls.coerce(bad)


@pytest.mark.parametrize("enum_cls", ENUM_CLASSES, ids=lambda cls: cls.__name__)
def test_coerce_does_not_leak_across_enum_types(enum_cls: type) -> None:
    """A member of one enum is not silently accepted by another."""
    foreign = [
        member
        for member in ALL_MEMBERS
        if not isinstance(member, enum_cls)
        and member.value not in {m.value for m in enum_cls}
        and member.name.lower() not in {m.value for m in enum_cls}
    ]
    for member in foreign:
        with pytest.raises(ValueError):
            enum_cls.coerce(member)


@given(data=st.data())
def test_coerce_is_case_and_whitespace_insensitive(data: st.DataObject) -> None:
    """Property: any casing of a member's value, padded with spaces, coerces."""
    member = data.draw(st.sampled_from(ALL_MEMBERS))
    value = member.value
    flips = data.draw(st.lists(st.booleans(), min_size=len(value), max_size=len(value)))
    scrambled = "".join(char.upper() if flip else char.lower() for char, flip in zip(value, flips))
    lead = data.draw(st.text(alphabet=" \t\n", max_size=3))
    trail = data.draw(st.text(alphabet=" \t\n", max_size=3))
    assert type(member).coerce(lead + scrambled + trail) is member


# ---------------------------------------------------------------------------
# EngineTier
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("tier", "rank", "requires_nlp", "allows_degradation"),
    [
        (EngineTier.AUTO, -1, False, True),
        (EngineTier.ZERO_DEPENDENCY, 0, False, False),
        (EngineTier.STATISTICAL_NLP, 1, True, False),
        (EngineTier.HYBRID_NLP, 1, True, True),
        (EngineTier.NEURAL, 2, True, False),
    ],
    ids=lambda value: getattr(value, "name", value),
)
def test_engine_tier_properties(
    tier: EngineTier, rank: int, requires_nlp: bool, allows_degradation: bool
) -> None:
    """Rank orders the tiers; the two flags drive ``resolve_backend`` policy."""
    assert tier.rank == rank
    assert tier.requires_nlp is requires_nlp
    assert tier.allows_degradation is allows_degradation


def test_engine_tier_rank_orders_the_real_tiers() -> None:
    """Ranks are a total order on the concrete tiers, with AUTO below them all."""
    concrete = [
        EngineTier.ZERO_DEPENDENCY,
        EngineTier.STATISTICAL_NLP,
        EngineTier.NEURAL,
    ]
    assert [tier.rank for tier in concrete] == sorted(tier.rank for tier in concrete)
    assert EngineTier.AUTO.rank < min(tier.rank for tier in concrete)


def test_zero_dependency_is_the_only_tier_needing_nothing_and_promising_everything() -> None:
    """Tier 0 neither requires a runtime nor has anything to degrade to."""
    assert EngineTier.ZERO_DEPENDENCY.requires_nlp is False
    assert EngineTier.ZERO_DEPENDENCY.allows_degradation is False


# ---------------------------------------------------------------------------
# CaseStyle.apply
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("style", "value", "expected"),
    [
        (CaseStyle.UPPER, "aBcD", "ABCD"),
        (CaseStyle.LOWER, "aBcD", "abcd"),
        (CaseStyle.TITLE, "aBcD", "Abcd"),
        (CaseStyle.PRESERVE, "aBcD", "aBcD"),
        (CaseStyle.UPPER, "pdf", "PDF"),
        (CaseStyle.LOWER, "PDF", "pdf"),
        (CaseStyle.TITLE, "PDF", "Pdf"),
        (CaseStyle.PRESERVE, "PDF", "PDF"),
        (CaseStyle.TITLE, "x", "X"),
        (CaseStyle.TITLE, "3d", "3d"),
        (CaseStyle.UPPER, "", ""),
        (CaseStyle.LOWER, "", ""),
        (CaseStyle.TITLE, "", ""),
        (CaseStyle.PRESERVE, "", ""),
    ],
    ids=repr,
)
def test_case_style_apply(style: CaseStyle, value: str, expected: str) -> None:
    """Each style re-cases exactly as documented, including for empty input."""
    assert style.apply(value) == expected


@pytest.mark.parametrize("style", list(CaseStyle), ids=_ident)
def test_case_style_apply_preserves_length(style: CaseStyle) -> None:
    """Re-casing never adds or removes characters."""
    for value in ("", "a", "PDF", "Multi3Word", "ÉCOLE"):
        assert len(style.apply(value)) == len(value)


@pytest.mark.parametrize("style", list(CaseStyle), ids=_ident)
def test_case_style_apply_is_idempotent(style: CaseStyle) -> None:
    """Applying a style twice equals applying it once."""
    for value in ("", "aBcD", "PDF", "scuba"):
        once = style.apply(value)
        assert style.apply(once) == once


# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("en-GB", Language.EN),
        ("fr_FR", Language.FR),
        ("en", Language.EN),
        ("EN-us", Language.EN),
        ("de_AT", Language.DE),
        ("es-419", Language.ES),
        ("DE", Language.DE),
    ],
    ids=repr,
)
def test_language_from_tag(tag: str, expected: Language) -> None:
    """BCP-47-ish tags reduce to their primary subtag."""
    assert Language.from_tag(tag) is expected


@pytest.mark.parametrize("tag", ["", "zz-ZZ", "klingon"], ids=repr)
def test_language_from_tag_rejects_unsupported_primary_subtags(tag: str) -> None:
    """An unbundled language is an error, not a silent fallback to English."""
    with pytest.raises(ValueError):
        Language.from_tag(tag)


@pytest.mark.parametrize(
    ("language", "display"),
    [
        (Language.EN, "English"),
        (Language.FR, "French"),
        (Language.ES, "Spanish"),
        (Language.DE, "German"),
    ],
    ids=_ident,
)
def test_language_display_name(language: Language, display: str) -> None:
    """All four bundled languages have a human-readable name."""
    assert language.display_name == display


def test_every_language_has_a_display_name() -> None:
    """The display-name table stays in step with the member list."""
    names = {language.display_name for language in Language}
    assert len(names) == len(list(Language))


# ---------------------------------------------------------------------------
# coerce_optional
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, None), ("en", Language.EN), (Language.DE, Language.DE), ("FR", Language.FR)],
    ids=repr,
)
def test_coerce_optional(value: object, expected: Optional[Language]) -> None:
    """``None`` passes through; anything else is coerced normally."""
    from acronymkit.enums import coerce_optional

    assert coerce_optional(Language, value) is expected
