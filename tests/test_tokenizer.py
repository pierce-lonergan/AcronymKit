"""Behavioural tests for :mod:`acronymkit.tokenizer`.

The tokenizer is the contract every downstream subsystem depends on, so this
module pins the guarantees rather than the implementation:

* offsets round-trip exactly into the *original* string;
* the emitted sequence is ordered, gapless in ``index`` and non-overlapping;
* ``letters`` is the only donation channel and obeys the configured policies;
* ``is_critical`` is exactly ``role in (CONTENT, ACRONYM) and is_eligible`` --
  the definition of ``T_critical`` used by the information-loss term ``Psi``.

Non-ASCII data is written with escape sequences so the file stays pure ASCII and
survives any source encoding.
"""

from __future__ import annotations

import doctest
from typing import Optional

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from acronymkit import tokenizer as tokenizer_module
from acronymkit.config import Config
from acronymkit.enums import HyphenPolicy, NumeralPolicy, StopWordCategory, TokenRole
from acronymkit.exceptions import TokenizationError
from acronymkit.models import Token
from acronymkit.tokenizer import (
    Tokenizer,
    is_roman_numeral,
    normalize,
    spell_number,
    split_camel_case,
    strip_accents,
)
from conftest import CANONICAL_ACRONYMS

# --------------------------------------------------------------------------
# Shared fixtures / constants
# --------------------------------------------------------------------------

#: Module-level so hypothesis-driven tests never depend on a function-scoped
#: fixture (which hypothesis rightly flags as a health-check failure).
DEFAULT_TOKENIZER = Tokenizer(Config())

HYPHEN = "-"
EN_DASH = "\u2013"
EM_DASH = "\u2014"
NON_BREAKING_HYPHEN = "\u2011"
RIGHT_SINGLE_QUOTE = "\u2019"

#: "Systeme d'Information" with the correct grave accent.
FRENCH_PHRASE = "Syst\u00e8me d'Information"
#: "Gross Datenverarbeitung" with the correct sharp s.
GERMAN_PHRASE = "Gro\u00df Datenverarbeitung"
#: "Ellinika Grammata" in Greek script.
GREEK_PHRASE = "\u0395\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac \u0393\u03c1\u03ac\u03bc\u03bc\u03b1\u03c4\u03b1"
#: Han, katakana and hangul runs.
CJK_PHRASE = "\u4e2d\u6587 \u30c6\u30b9\u30c8 \ud55c\uad6d\uc5b4"

#: Deliberately awkward inputs used by the explicit offset checks.
OFFSET_CORPUS = [
    "",
    " ",
    "API",
    "Multi-Factor Authentication",
    "Multi" + EN_DASH + "Factor",
    "Multi" + EM_DASH + "Factor",
    "input/output",
    "XMLHttpRequest iOS parseJSON getHTTPResponse",
    "3D 1st 3.5 Web 2.0",
    "The Art of War",
    FRENCH_PHRASE,
    GERMAN_PHRASE,
    GREEK_PHRASE,
    CJK_PHRASE,
    "don't l'International",
    "  leading and trailing  ",
    "Hello, world! (yes) -- ok.",
    "e.g. see Fig. 3; cf. Dr. Smith.",
    "line one\nline two\ttabbed",
    "\u00c9cole Nationale Sup\u00e9rieure",
    "emoji \U0001f600 between words",
]

#: A tiny alphabet packed with the characters that drive the interesting
#: branches: connectors, apostrophes, elision clitics, digits, CJK, accents.
_INTERESTING_CHARS = "".join(
    sorted(
        set(
            "aAbZ19 \t\n"
            + HYPHEN
            + EN_DASH
            + EM_DASH
            + NON_BREAKING_HYPHEN
            + "/'"
            + RIGHT_SINGLE_QUOTE
            + ".,!?()"
            + "ldqu"
            + "\u00e9\u00df\u00e7"
            + "\u4e2d\u30c6\ud55c"
            + "\u0395\u03bb"
        )
    )
)

TEXT_STRATEGY = st.one_of(
    st.text(max_size=120),
    st.text(alphabet=_INTERESTING_CHARS, max_size=80),
    st.sampled_from(OFFSET_CORPUS),
)


def _tokenizer(**overrides: object) -> Tokenizer:
    """Return a tokenizer built from ``Config(**overrides)``."""
    return Tokenizer(Config(**overrides))


def _letters(tokens: list[Token]) -> list[str]:
    return [token.letters for token in tokens]


def _texts(tokens: list[Token]) -> list[str]:
    return [token.text for token in tokens]


# --------------------------------------------------------------------------
# Invariant 1: offsets
# --------------------------------------------------------------------------
@settings(max_examples=300, deadline=None)
@given(TEXT_STRATEGY)
def test_offsets_round_trip_for_any_text(text: str) -> None:
    """``text[t.start:t.end] == t.text`` is the load-bearing offset guarantee."""
    for token in DEFAULT_TOKENIZER.tokenize(text):
        assert text[token.start : token.end] == token.text


@pytest.mark.parametrize("text", OFFSET_CORPUS)
def test_offsets_round_trip_explicit_cases(text: str) -> None:
    tokens = DEFAULT_TOKENIZER.tokenize(text)
    assert all(text[t.start : t.end] == t.text for t in tokens)


@settings(max_examples=300, deadline=None)
@given(TEXT_STRATEGY)
def test_token_sequence_is_ordered_and_non_overlapping(text: str) -> None:
    """Indices are ``0..n-1``; starts strictly increase; spans never overlap."""
    tokens = DEFAULT_TOKENIZER.tokenize(text)
    assert [t.index for t in tokens] == list(range(len(tokens)))
    starts = [t.start for t in tokens]
    assert starts == sorted(starts)
    assert len(set(starts)) == len(starts)
    previous_end = 0
    for token in tokens:
        assert token.end > token.start
        assert token.start >= previous_end
        previous_end = token.end
    assert previous_end <= len(text)


@settings(max_examples=200, deadline=None)
@given(TEXT_STRATEGY)
def test_tokenization_is_deterministic(text: str) -> None:
    """Two runs over the same input produce identical token records."""
    assert DEFAULT_TOKENIZER.tokenize(text) == DEFAULT_TOKENIZER.tokenize(text)


@settings(max_examples=200, deadline=None)
@given(TEXT_STRATEGY)
def test_normalized_field_matches_normalize(text: str) -> None:
    for token in DEFAULT_TOKENIZER.tokenize(text):
        assert token.normalized == normalize(token.text)


@settings(max_examples=200, deadline=None)
@given(TEXT_STRATEGY)
def test_letters_are_uppercase_and_within_budget(text: str) -> None:
    """``letters`` is an uppercased budget; CONTENT tokens respect the limit."""
    config = Config()
    for token in DEFAULT_TOKENIZER.tokenize(text):
        assert token.letters == token.letters.upper()
        if token.role is TokenRole.CONTENT:
            assert len(token.letters) <= config.max_letters_per_token


# --------------------------------------------------------------------------
# Invariant 2: is_critical is exactly the T_critical predicate
# --------------------------------------------------------------------------
@settings(max_examples=300, deadline=None)
@given(TEXT_STRATEGY)
def test_is_critical_is_content_or_acronym_and_eligible(text: str) -> None:
    for token in DEFAULT_TOKENIZER.tokenize(text):
        expected = token.role in (TokenRole.CONTENT, TokenRole.ACRONYM) and token.is_eligible
        assert token.is_critical is expected


@pytest.mark.parametrize(
    "config_kwargs",
    [
        {},
        {"include_articles": True, "include_prepositions": True},
        {"min_word_length": 5},
        {"numeral_policy": NumeralPolicy.SKIP},
        {"preserve_existing_acronyms": False},
        {"hyphen_policy": HyphenPolicy.MERGE},
    ],
)
def test_is_critical_predicate_holds_under_every_policy(config_kwargs: dict) -> None:
    source = "The API 3.5 Multi-Factor of War don't a"
    for token in _tokenizer(**config_kwargs).tokenize(source):
        expected = token.role in (TokenRole.CONTENT, TokenRole.ACRONYM) and token.is_eligible
        assert token.is_critical is expected


def test_numeral_tokens_are_never_critical() -> None:
    tokens = DEFAULT_TOKENIZER.tokenize("Web 2.0 and 3 things")
    numerals = [t for t in tokens if t.role is TokenRole.NUMERAL]
    assert numerals, "expected the numeric tokens to be recognised"
    assert all(not t.is_critical for t in numerals)


# --------------------------------------------------------------------------
# Hyphen policies
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "separator", [HYPHEN, EN_DASH, EM_DASH], ids=["hyphen", "en-dash", "em-dash"]
)
@pytest.mark.parametrize(
    ("policy", "expected_letters"),
    [
        (HyphenPolicy.SPLIT, "MF"),
        (HyphenPolicy.MERGE, "MU"),
        (HyphenPolicy.FIRST_ONLY, "M"),
    ],
)
def test_hyphen_policy_on_multi_factor_authentication(
    separator: str, policy: HyphenPolicy, expected_letters: str
) -> None:
    source = f"Multi{separator}Factor Authentication"
    tokens = _tokenizer(hyphen_policy=policy).tokenize(source)

    assert _texts(tokens) == [f"Multi{separator}Factor", "Authentication"]
    assert tokens[0].subtokens == ["Multi", "Factor"]
    assert tokens[0].letters == expected_letters
    assert tokens[1].letters == "AU"
    assert tokens[1].subtokens == []
    assert all(source[t.start : t.end] == t.text for t in tokens)


@pytest.mark.parametrize(
    ("policy", "expected_letters"),
    [
        (HyphenPolicy.SPLIT, "IO"),
        (HyphenPolicy.MERGE, "IN"),
        (HyphenPolicy.FIRST_ONLY, "I"),
    ],
)
def test_hyphen_policy_on_solidus_compound(policy: HyphenPolicy, expected_letters: str) -> None:
    tokens = _tokenizer(hyphen_policy=policy).tokenize("input/output")

    assert len(tokens) == 1
    assert tokens[0].text == "input/output"
    assert tokens[0].subtokens == ["input", "output"]
    assert tokens[0].letters == expected_letters


def test_split_policy_is_capped_by_max_letters_per_token() -> None:
    source = "Multi-Factor-Auth-Zone"
    two = _tokenizer(hyphen_policy=HyphenPolicy.SPLIT).tokenize(source)
    three = _tokenizer(hyphen_policy=HyphenPolicy.SPLIT, max_letters_per_token=3).tokenize(source)

    assert two[0].subtokens == ["Multi", "Factor", "Auth", "Zone"]
    assert two[0].letters == "MF"
    assert three[0].letters == "MFA"


def test_single_letter_budget_collapses_split_policy() -> None:
    tokens = _tokenizer(hyphen_policy=HyphenPolicy.SPLIT, allow_multi_letter_tokens=False).tokenize(
        "Multi-Factor"
    )

    assert tokens[0].letters == "M"
    assert tokens[0].subtokens == ["Multi", "Factor"]


# --------------------------------------------------------------------------
# camelCase / PascalCase
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("word", "components"),
    [
        ("XMLHttpRequest", ["XML", "Http", "Request"]),
        ("iOS", ["i", "OS"]),
        ("parseJSON", ["parse", "JSON"]),
        ("getHTTPResponse", ["get", "HTTP", "Response"]),
        ("multi", ["multi"]),
        ("ABC", ["ABC"]),
        ("Ab", ["Ab"]),
        ("aB", ["a", "B"]),
        ("HTML5", ["HTML", "5"]),
        ("v2Model", ["v", "2", "Model"]),
        ("don't", ["don't"]),
        ("O'Brien", ["O'Brien"]),
        ("", []),
    ],
)
def test_split_camel_case(word: str, components: list) -> None:
    assert split_camel_case(word) == components


@settings(max_examples=200, deadline=None)
@given(st.text(alphabet=_INTERESTING_CHARS, max_size=40))
def test_split_camel_case_is_a_partition(word: str) -> None:
    """Components concatenate back to the input and are never empty."""
    components = split_camel_case(word)
    assert "".join(components) == word
    assert all(components)


@pytest.mark.parametrize(
    ("source", "subtokens", "letters"),
    [
        ("XMLHttpRequest", ["XML", "Http", "Request"], "XH"),
        ("iOS", ["i", "OS"], "IO"),
        ("parseJSON", ["parse", "JSON"], "PJ"),
        ("getHTTPResponse", ["get", "HTTP", "Response"], "GH"),
    ],
)
def test_camel_case_tokens_expose_components(source: str, subtokens: list, letters: str) -> None:
    tokens = DEFAULT_TOKENIZER.tokenize(source)

    assert len(tokens) == 1
    assert tokens[0].text == source
    assert tokens[0].subtokens == subtokens
    assert tokens[0].letters == letters
    assert tokens[0].role is TokenRole.CONTENT


# --------------------------------------------------------------------------
# Numerals
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        (NumeralPolicy.DIGIT, [("1st", "1"), ("3.5", "35"), ("2.0", "20"), ("3", "3")]),
        (NumeralPolicy.WORD, [("1st", "F"), ("3.5", "35"), ("2.0", "20"), ("3", "T")]),
        (NumeralPolicy.SKIP, [("1st", ""), ("3.5", ""), ("2.0", ""), ("3", "")]),
    ],
)
def test_numeral_policies(policy: NumeralPolicy, expected: list) -> None:
    tokens = _tokenizer(numeral_policy=policy).tokenize("1st 3.5 Web 2.0 3")
    numerals = [t for t in tokens if t.role is TokenRole.NUMERAL]

    assert [(t.text, t.letters) for t in numerals] == expected


@pytest.mark.parametrize("policy", list(NumeralPolicy))
def test_decimal_numbers_stay_one_token(policy: NumeralPolicy) -> None:
    tokens = _tokenizer(numeral_policy=policy).tokenize("Web 2.0")

    assert _texts(tokens) == ["Web", "2.0"]
    assert tokens[1].role is TokenRole.NUMERAL


def test_numeral_skip_marks_tokens_ineligible() -> None:
    tokens = _tokenizer(numeral_policy=NumeralPolicy.SKIP).tokenize("Version 3 Release")
    numeral = next(t for t in tokens if t.role is TokenRole.NUMERAL)

    assert numeral.letters == ""
    assert numeral.is_eligible is False
    assert numeral.is_critical is False


def test_numerals_are_exempt_from_min_word_length() -> None:
    tokens = _tokenizer(min_word_length=5, numeral_policy=NumeralPolicy.DIGIT).tokenize("3 x")
    numeral = next(t for t in tokens if t.role is TokenRole.NUMERAL)
    short_word = next(t for t in tokens if t.role is TokenRole.CONTENT)

    assert numeral.is_eligible is True
    assert short_word.is_eligible is False


def test_3d_is_preserved_as_an_uppercase_unit_not_a_numeral() -> None:
    """``3D`` has no lowercase letter, so the acronym rule claims it first.

    This is the documented precedence in ``_build_token``: the numeral branch
    only fires for a *purely* numeric surface form.
    """
    kept = DEFAULT_TOKENIZER.tokenize("3D")[0]
    assert kept.role is TokenRole.ACRONYM
    assert kept.letters == "3D"
    assert kept.subtokens == ["3", "D"]

    plain = _tokenizer(preserve_existing_acronyms=False).tokenize("3D")[0]
    assert plain.role is TokenRole.CONTENT
    assert plain.letters == "D"


@pytest.mark.parametrize(
    ("policy", "expected"),
    [(NumeralPolicy.DIGIT, ["3", "DI"]), (NumeralPolicy.WORD, ["T", "DI"])],
)
def test_three_dimensional_matches_the_enum_docstring(
    policy: NumeralPolicy, expected: list
) -> None:
    tokens = _tokenizer(numeral_policy=policy).tokenize("3 Dimensional")
    assert _letters(tokens) == expected


# --------------------------------------------------------------------------
# preserve_existing_acronyms
# --------------------------------------------------------------------------
def test_existing_acronym_is_preserved_verbatim() -> None:
    tokens = DEFAULT_TOKENIZER.tokenize("API XML")

    assert [t.role for t in tokens] == [TokenRole.ACRONYM, TokenRole.ACRONYM]
    assert _letters(tokens) == ["API", "XML"]
    assert all(t.is_critical for t in tokens)


def test_single_uppercase_letter_is_not_an_acronym() -> None:
    lone = DEFAULT_TOKENIZER.tokenize("A")[0]

    assert lone.role is not TokenRole.ACRONYM
    assert lone.letters == "A"


def test_disabling_preservation_demotes_acronyms_to_content() -> None:
    tokens = _tokenizer(preserve_existing_acronyms=False).tokenize("API XML")

    assert [t.role for t in tokens] == [TokenRole.CONTENT, TokenRole.CONTENT]
    assert _letters(tokens) == ["AP", "XM"]


def test_acronyms_are_exempt_from_min_word_length() -> None:
    tokens = _tokenizer(min_word_length=5).tokenize("AI xy")

    assert tokens[0].role is TokenRole.ACRONYM
    assert tokens[0].is_eligible is True
    assert tokens[0].is_critical is True
    assert tokens[1].is_eligible is False


def test_hyphenated_acronym_keeps_alphanumerics_only() -> None:
    token = DEFAULT_TOKENIZER.tokenize("COVID-19")[0]

    assert token.role is TokenRole.ACRONYM
    assert token.letters == "COVID19"
    assert token.subtokens == ["COVID", "19"]


# --------------------------------------------------------------------------
# Stop words
# --------------------------------------------------------------------------
def test_articles_and_prepositions_are_suppressed_by_default() -> None:
    tokens = DEFAULT_TOKENIZER.tokenize("The Art of War")

    assert _texts(tokens) == ["The", "Art", "of", "War"]
    assert [t.role for t in tokens] == [
        TokenRole.FUNCTION,
        TokenRole.CONTENT,
        TokenRole.FUNCTION,
        TokenRole.CONTENT,
    ]
    assert [t.stop_word_category for t in tokens] == [
        StopWordCategory.ARTICLE,
        None,
        StopWordCategory.PREPOSITION,
        None,
    ]
    assert [t.is_eligible for t in tokens] == [False, True, False, True]
    assert "".join(t.letters[:1] for t in tokens if t.is_eligible) == "AW"


def test_including_articles_and_prepositions_makes_them_eligible() -> None:
    tokens = _tokenizer(include_articles=True, include_prepositions=True).tokenize("The Art of War")

    assert [t.is_eligible for t in tokens] == [True, True, True, True]
    assert "".join(t.letters[:1] for t in tokens if t.is_eligible) == "TAOW"
    # Role stays FUNCTION, so an included article is still outside T_critical.
    assert [t.is_critical for t in tokens] == [False, True, False, True]


@pytest.mark.parametrize(
    ("word", "flag", "category"),
    [
        ("the", "include_articles", StopWordCategory.ARTICLE),
        ("of", "include_prepositions", StopWordCategory.PREPOSITION),
        ("and", "include_conjunctions", StopWordCategory.CONJUNCTION),
        ("it", "include_pronouns", StopWordCategory.PRONOUN),
        ("is", "include_auxiliaries", StopWordCategory.AUXILIARY),
    ],
)
def test_each_include_flag_gates_exactly_its_category(
    word: str, flag: str, category: StopWordCategory
) -> None:
    excluded = _tokenizer(**{flag: False}).tokenize(word)[0]
    included = _tokenizer(**{flag: True}).tokenize(word)[0]

    assert excluded.stop_word_category is category
    assert included.stop_word_category is category
    assert excluded.role is TokenRole.FUNCTION
    assert excluded.is_eligible is False
    assert included.is_eligible is True


@pytest.mark.parametrize("category", [StopWordCategory.DETERMINER, StopWordCategory.PARTICLE])
def test_determiners_and_particles_are_always_suppressed(
    category: StopWordCategory,
) -> None:
    word = {"determiner": "this", "particle": "not"}[category.value]
    token = _tokenizer(
        include_articles=True,
        include_prepositions=True,
        include_conjunctions=True,
        include_pronouns=True,
        include_auxiliaries=True,
    ).tokenize(word)[0]

    assert token.stop_word_category is category
    assert token.is_eligible is False


def test_custom_keep_word_overrides_the_bundled_stop_list() -> None:
    token = _tokenizer(custom_keep_words=frozenset({"the"})).tokenize("The Art")[0]

    assert token.stop_word_category is None
    assert token.role is TokenRole.CONTENT
    assert token.is_eligible is True


def test_custom_stop_word_suppresses_a_content_word() -> None:
    token = _tokenizer(custom_stop_words=frozenset({"art"})).tokenize("The Art")[1]

    assert token.stop_word_category is StopWordCategory.OTHER
    assert token.role is TokenRole.FUNCTION
    assert token.is_eligible is False


@pytest.mark.parametrize(("phrase", "expected"), CANONICAL_ACRONYMS)
def test_eligible_initials_reproduce_the_canonical_initialism(phrase: str, expected: str) -> None:
    """Stop-word filtering alone must recover the textbook acronym."""
    tokens = DEFAULT_TOKENIZER.tokenize(phrase)
    assert "".join(t.letters[:1] for t in tokens if t.is_eligible) == expected
    assert "".join(t.letters[:1] for t in tokens if t.is_critical) == expected


# --------------------------------------------------------------------------
# min_word_length
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("min_length", "eligibility"),
    [
        (1, [True, True, True]),
        (2, [False, True, True]),
        (3, [False, False, True]),
        (4, [False, False, False]),
    ],
)
def test_min_word_length_gates_short_content_words(min_length: int, eligibility: list) -> None:
    tokens = _tokenizer(min_word_length=min_length).tokenize("x yz abc")

    assert _texts(tokens) == ["x", "yz", "abc"]
    assert [t.is_eligible for t in tokens] == eligibility
    assert [t.is_critical for t in tokens] == eligibility


def test_min_word_length_exempts_acronyms_and_numerals() -> None:
    tokens = _tokenizer(min_word_length=6).tokenize("AI 42 word")

    assert tokens[0].role is TokenRole.ACRONYM
    assert tokens[0].is_eligible is True
    assert tokens[1].role is TokenRole.NUMERAL
    assert tokens[1].is_eligible is True
    assert tokens[2].role is TokenRole.CONTENT
    assert tokens[2].is_eligible is False


# --------------------------------------------------------------------------
# Unicode
# --------------------------------------------------------------------------
def test_french_accented_phrase() -> None:
    tokens = DEFAULT_TOKENIZER.tokenize(FRENCH_PHRASE)

    assert _texts(tokens) == ["Syst\u00e8me", "d", "Information"]
    assert tokens[0].letters == "SY"
    assert tokens[0].normalized == "syst\u00e8me"
    assert tokens[2].letters == "IN"
    assert all(FRENCH_PHRASE[t.start : t.end] == t.text for t in tokens)


def test_german_sharp_s_phrase() -> None:
    tokens = DEFAULT_TOKENIZER.tokenize(GERMAN_PHRASE)

    assert _texts(tokens) == ["Gro\u00df", "Datenverarbeitung"]
    assert _letters(tokens) == ["GR", "DA"]
    assert tokens[0].normalized == "gross"
    assert all(t.is_critical for t in tokens)


def test_greek_script_tokenises_like_latin() -> None:
    tokens = DEFAULT_TOKENIZER.tokenize(GREEK_PHRASE)

    assert len(tokens) == 2
    assert _letters(tokens) == ["\u0395\u039b", "\u0393\u03a1"]
    assert all(t.role is TokenRole.CONTENT for t in tokens)
    assert all(GREEK_PHRASE[t.start : t.end] == t.text for t in tokens)


def test_cjk_runs_donate_only_their_first_character() -> None:
    tokens = DEFAULT_TOKENIZER.tokenize(CJK_PHRASE)

    assert _texts(tokens) == ["\u4e2d\u6587", "\u30c6\u30b9\u30c8", "\ud55c\uad6d\uc5b4"]
    assert _letters(tokens) == ["\u4e2d", "\u30c6", "\ud55c"]
    assert all(len(t.letters) == 1 for t in tokens)


def test_full_width_latin_normalises_but_offsets_stay_on_the_original() -> None:
    source = "\uff21\uff22\uff23"  # fullwidth ABC
    token = DEFAULT_TOKENIZER.tokenize(source)[0]

    assert token.text == source
    assert token.normalized == "abc"
    assert source[token.start : token.end] == token.text


# --------------------------------------------------------------------------
# Apostrophes and elision
# --------------------------------------------------------------------------
def test_english_contraction_is_a_single_token() -> None:
    tokens = DEFAULT_TOKENIZER.tokenize("don't")

    assert _texts(tokens) == ["don't"]


@pytest.mark.parametrize("apostrophe", ["'", RIGHT_SINGLE_QUOTE])
def test_french_elision_splits_the_clitic(apostrophe: str) -> None:
    source = f"l{apostrophe}International"
    tokens = DEFAULT_TOKENIZER.tokenize(source)

    assert _texts(tokens) == ["l", "International"]
    assert tokens[1].letters == "IN"
    assert all(source[t.start : t.end] == t.text for t in tokens)
    # The apostrophe itself is not part of either token.
    assert tokens[0].end == tokens[1].start - 1


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("O'Brien", ["O'Brien"]),
        ("qu'il", ["qu", "il"]),
        ("d'accord", ["d", "accord"]),
        ("can't won't", ["can't", "won't"]),
    ],
)
def test_apostrophe_handling(source: str, expected: list) -> None:
    assert _texts(DEFAULT_TOKENIZER.tokenize(source)) == expected


# --------------------------------------------------------------------------
# Degenerate input
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    ["", " ", "   ", "\t", "\n", "\r\n\t ", "!!!", "... --- ...", "@#$%^&*", "()[]{}", "\u2014"],
)
def test_empty_whitespace_and_punctuation_yield_no_tokens(text: str) -> None:
    assert DEFAULT_TOKENIZER.tokenize(text) == []


def test_punctuation_between_words_is_dropped_without_shifting_offsets() -> None:
    source = "Hello, world! (yes) -- ok."
    tokens = DEFAULT_TOKENIZER.tokenize(source)

    assert _texts(tokens) == ["Hello", "world", "yes", "ok"]
    assert [(t.start, t.end) for t in tokens] == [(0, 5), (7, 12), (15, 18), (23, 25)]


@pytest.mark.parametrize("value", [None, 42, b"bytes", ["a"]])
def test_tokenize_rejects_non_string_input(value: object) -> None:
    with pytest.raises(TokenizationError):
        DEFAULT_TOKENIZER.tokenize(value)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# split_sentences
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("See e.g. the manual. It works.", ["See e.g. the manual.", "It works."]),
        ("That is i.e. the point. Next.", ["That is i.e. the point.", "Next."]),
        ("Dr. Smith works at NASA. He left.", ["Dr. Smith works at NASA.", "He left."]),
        ("See Fig. 3 for detail. Done.", ["See Fig. 3 for detail.", "Done."]),
        ("Cats vs. dogs is a debate. Yes.", ["Cats vs. dogs is a debate.", "Yes."]),
        (
            "Reported by Jones et al. in 1999. Later confirmed.",
            ["Reported by Jones et al. in 1999.", "Later confirmed."],
        ),
        ("See No. 5 below. Fine.", ["See No. 5 below.", "Fine."]),
        ("J. R. Smith wrote it. He did.", ["J. R. Smith wrote it.", "He did."]),
        ("cf. the appendix. Ok.", ["cf. the appendix.", "Ok."]),
        ("approx. 30 units. Ok.", ["approx. 30 units.", "Ok."]),
    ],
)
def test_split_sentences_ignores_common_abbreviations(text: str, expected: list) -> None:
    spans = DEFAULT_TOKENIZER.split_sentences(text)
    assert [text[s:e] for s, e in spans] == expected


@pytest.mark.parametrize(
    ("text", "count"),
    [
        ("One sentence only", 1),
        ("First. Second. Third.", 3),
        ("Really? Yes! Truly.", 3),
        ("Trailing whitespace.   ", 1),
        ("No terminator at all", 1),
    ],
)
def test_split_sentences_counts(text: str, count: int) -> None:
    assert len(DEFAULT_TOKENIZER.split_sentences(text)) == count


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
def test_split_sentences_on_blank_input(text: str) -> None:
    assert DEFAULT_TOKENIZER.split_sentences(text) == []


@settings(max_examples=200, deadline=None)
@given(TEXT_STRATEGY)
def test_split_sentences_spans_are_ordered_trimmed_and_in_range(text: str) -> None:
    spans = DEFAULT_TOKENIZER.split_sentences(text)
    previous_end = 0
    for start, end in spans:
        assert 0 <= start < end <= len(text)
        assert start >= previous_end
        assert not text[start].isspace()
        assert not text[end - 1].isspace()
        previous_end = end


@settings(max_examples=150, deadline=None)
@given(TEXT_STRATEGY)
def test_every_token_lives_inside_some_sentence_span(text: str) -> None:
    """Sentence spans cover every emitted token (they partition the content)."""
    spans = DEFAULT_TOKENIZER.split_sentences(text)
    for token in DEFAULT_TOKENIZER.tokenize(text):
        assert any(start <= token.start and token.end <= end for start, end in spans)


# --------------------------------------------------------------------------
# Module-level helpers
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Caf\u00e9 NA\u00cfVE", "caf\u00e9 na\u00efve"),
        ("\uff21\uff22\uff23", "abc"),
        ("Gro\u00df", "gross"),
        ("", ""),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("r\u00e9sum\u00e9", "resume"),
        ("\u00dcber", "Uber"),
        ("na\u00efve", "naive"),
        ("ascii", "ascii"),
    ],
)
def test_strip_accents(raw: str, expected: str) -> None:
    assert strip_accents(raw) == expected


@settings(max_examples=200, deadline=None)
@given(st.text(alphabet="abcXYZ ", max_size=30))
def test_strip_accents_is_identity_on_ascii(text: str) -> None:
    assert strip_accents(text) == text


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("XIV", True),
        ("mcmxc", True),
        ("MMMCMXCIX", True),
        ("VI", True),
        ("IIII", False),
        ("IC", False),
        ("ABC", False),
        ("", False),
    ],
)
def test_is_roman_numeral(word: str, expected: bool) -> None:
    assert is_roman_numeral(word) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", "zero"),
        ("3", "three"),
        ("1st", "first"),
        ("21st", "twenty-first"),
        ("12th", "twelfth"),
        ("100", "one hundred"),
        ("999", "nine hundred ninety-nine"),
        ("1000", None),
        ("3.5", None),
        ("abc", None),
        ("", None),
    ],
)
def test_spell_number(value: str, expected: Optional[str]) -> None:
    assert spell_number(value) == expected


@settings(max_examples=200, deadline=None)
@given(st.integers(min_value=0, max_value=999))
def test_spell_number_covers_every_supported_cardinal(number: int) -> None:
    spelled = spell_number(str(number))
    assert spelled is not None
    assert spelled == spelled.lower()
    assert spelled[0].isalpha()


# --------------------------------------------------------------------------
# Doctests
# --------------------------------------------------------------------------
def test_tokenizer_module_doctests_pass() -> None:
    """The examples in ``Tokenizer.tokenize`` (and friends) must be executable."""
    results = doctest.testmod(tokenizer_module, verbose=False, report=False)

    assert results.attempted > 0
    assert results.failed == 0
