"""Tests for the Tier 1 backend contract in :mod:`acronymkit.nlp`.

``conftest.pytest_collection_modifyitems`` stamps every test in this file with
the ``nlp`` marker. That marker is *not* a skip: almost everything here runs on
a bare install, because the interesting contract — tier policy, the alignment
and role-update machinery, and "an availability probe never raises" — is
exactly what has to hold when spaCy and NLTK are absent. Only the handful of
tests that need a real tagger carry :data:`conftest.requires_nlp`.

Two simulations appear below. Both install their fake into ``sys.modules`` with
``monkeypatch.setitem`` and run under ``isolated_backend_caches``, which swaps
the module-level pipeline/tagger caches for empty ones so a simulated failure is
never memoised into the real process state.
"""

from __future__ import annotations

import sys
import types
from typing import Any, NamedTuple, Optional, Sequence

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from acronymkit.config import Config
from acronymkit.enums import EngineTier, Language, StopWordCategory, TokenRole
from acronymkit.exceptions import TierUnavailableError
from acronymkit.models import Token
from acronymkit.nlp import (
    BackendUnavailable,
    HeuristicBackend,
    NlpBackend,
    NltkBackend,
    SpacyBackend,
    resolve_backend,
)
from acronymkit.nlp import heuristic as heuristic_module
from acronymkit.nlp import nltk_backend as nltk_module
from acronymkit.nlp import spacy_backend as spacy_module
from acronymkit.nlp.base import (
    CRITICAL_ROLES,
    NEURAL_NOT_IMPLEMENTED_WARNING,
    NLP_UNAVAILABLE_WARNING,
    PRESERVED_ROLES,
    Annotation,
    apply_annotation,
    role_for_pos,
)
from acronymkit.nlp.heuristic import DEFAULT_POS, MIN_STEM_LENGTH, SUFFIX_POS, guess_pos
from acronymkit.nlp.nltk_backend import NLTK_LANGUAGE_CODES, penn_to_universal
from acronymkit.nlp.spacy_backend import MODEL_BY_LANGUAGE
from acronymkit.tokenizer import Tokenizer
from conftest import HAS_NLP_BACKEND, requires_nlp

#: Names a Tier 1 backend may report.
TIER1_NAMES = ("spacy", "nltk")

#: Phrases exercising every tokenizer-assigned role at once.
ANNOTATION_CORPUS = [
    "Application Programming Interface",
    "The API 3 Gateway System",
    "Multi-Factor Authentication of the XML 2 Parser",
    "running organization darkness capable famous",
    "Self Contained Underwater Breathing Apparatus",
]


# ---------------------------------------------------------------------------
# tier policy
# ---------------------------------------------------------------------------
class Policy(NamedTuple):
    """What :func:`resolve_backend` must do for one (tier, strict) pair."""

    raises: bool
    tier1: bool = False
    warnings: tuple[str, ...] = ()


def expected_policy(tier: EngineTier, strict: bool) -> Policy:
    """Return the documented outcome for ``tier``/``strict`` in this environment.

    Written from the policy in the :func:`resolve_backend` docstring rather than
    from its implementation, and parameterised on
    :data:`conftest.HAS_NLP_BACKEND` so the same table is meaningful with and
    without an installed Tier 1 runtime.

    Args:
        tier: The requested execution tier.
        strict: Whether degradation is forbidden.

    Returns:
        The expected :class:`Policy`.
    """
    if tier is EngineTier.ZERO_DEPENDENCY:
        return Policy(raises=False)
    if tier is EngineTier.NEURAL:
        # Tier 2 does not exist in this release, so strict always refuses.
        if strict:
            return Policy(raises=True)
        if HAS_NLP_BACKEND:
            return Policy(False, True, (NEURAL_NOT_IMPLEMENTED_WARNING,))
        return Policy(False, False, (NEURAL_NOT_IMPLEMENTED_WARNING, NLP_UNAVAILABLE_WARNING))
    if HAS_NLP_BACKEND:
        return Policy(False, True, ())
    if tier is EngineTier.STATISTICAL_NLP:
        return Policy(raises=True)
    if tier is EngineTier.HYBRID_NLP:
        if strict:
            return Policy(raises=True)
        return Policy(False, False, (NLP_UNAVAILABLE_WARNING,))
    return Policy(False, False, ())  # AUTO degrades silently, strict or not


@pytest.mark.parametrize("strict", [False, True], ids=["lenient", "strict"])
@pytest.mark.parametrize("tier", list(EngineTier), ids=lambda tier: tier.value)
def test_resolve_backend_follows_the_tier_policy(tier: EngineTier, strict: bool) -> None:
    """Every tier resolves, or refuses, exactly as documented."""
    config = Config(engine_tier=tier, strict=strict)
    policy = expected_policy(tier, strict)

    if policy.raises:
        with pytest.raises(TierUnavailableError) as excinfo:
            resolve_backend(config)
        assert excinfo.value.tier is tier
        return

    backend, warnings = resolve_backend(config)
    assert isinstance(warnings, list)
    assert tuple(warnings) == policy.warnings
    if policy.tier1:
        assert backend.name in TIER1_NAMES
    else:
        assert backend.name == "heuristic"
    assert backend.is_available()


def test_zero_dependency_never_warns_and_never_probes() -> None:
    """Tier 0 is the contract-free path: heuristic backend, no warnings, ever."""
    for strict in (False, True):
        backend, warnings = resolve_backend(
            Config(engine_tier=EngineTier.ZERO_DEPENDENCY, strict=strict)
        )
        assert isinstance(backend, HeuristicBackend)
        assert warnings == []


@pytest.mark.parametrize("tier", list(EngineTier), ids=lambda tier: tier.value)
def test_resolve_backend_returns_a_protocol_conformant_backend(tier: EngineTier) -> None:
    """Whatever is resolved satisfies the structural :class:`NlpBackend` contract."""
    try:
        backend, _ = resolve_backend(Config(engine_tier=tier))
    except TierUnavailableError:
        pytest.skip(f"tier {tier.value} is unavailable here")
    assert isinstance(backend, NlpBackend)
    assert isinstance(backend.name, str) and backend.name


@pytest.mark.parametrize("language", list(Language), ids=lambda lang: lang.value)
def test_resolve_backend_honours_the_configured_language(language: Language) -> None:
    """The resolved Tier 0 backend carries the language it was asked for."""
    backend, _ = resolve_backend(Config(engine_tier=EngineTier.ZERO_DEPENDENCY, language=language))
    assert isinstance(backend, HeuristicBackend)
    assert backend.language is language


def test_neural_warning_is_emitted_even_when_a_backend_exists() -> None:
    """Requesting Tier 2 always says Tier 2 did not happen."""
    config = Config(engine_tier=EngineTier.NEURAL, strict=False)
    _, warnings = resolve_backend(config)
    assert NEURAL_NOT_IMPLEMENTED_WARNING in warnings


def test_strict_neural_always_refuses() -> None:
    """``strict`` forbids receiving a lower tier, and Tier 2 is never available."""
    with pytest.raises(TierUnavailableError) as excinfo:
        resolve_backend(Config(engine_tier=EngineTier.NEURAL, strict=True))
    assert "nlp" in str(excinfo.value)


# ---------------------------------------------------------------------------
# HeuristicBackend: availability and suffix rules
# ---------------------------------------------------------------------------
def test_heuristic_backend_is_always_available() -> None:
    """The zero-dependency backend has no failure mode to report."""
    assert HeuristicBackend().is_available() is True
    assert HeuristicBackend(language=Language.DE).is_available() is True
    assert HeuristicBackend.name == "heuristic"


SUFFIX_CASES = [
    # -- nouns -----------------------------------------------------------
    ("creation", "NOUN"),
    ("decision", "NOUN"),
    ("management", "NOUN"),
    ("darkness", "NOUN"),
    ("tolerance", "NOUN"),
    ("presence", "NOUN"),
    ("friendship", "NOUN"),
    ("ability", "NOUN"),
    ("activism", "NOUN"),
    ("artist", "NOUN"),
    ("writer", "NOUN"),
    ("actor", "NOUN"),
    # -- verbs -----------------------------------------------------------
    ("running", "VERB"),
    ("educate", "VERB"),
    ("simplify", "VERB"),
    ("normalise", "VERB"),
    ("organize", "VERB"),
    ("tested", "VERB"),
    # -- adjectives ------------------------------------------------------
    ("capable", "ADJ"),
    ("reversible", "ADJ"),
    ("useless", "ADJ"),
    ("famous", "ADJ"),
    ("active", "ADJ"),
    ("helpful", "ADJ"),
    ("musical", "ADJ"),
    ("atomic", "ADJ"),
    # -- adverb ----------------------------------------------------------
    ("quickly", "ADV"),
]


@pytest.mark.parametrize(("word", "expected"), SUFFIX_CASES)
def test_guess_pos_classifies_by_suffix(word: str, expected: str) -> None:
    """The documented suffix families map to their Universal POS tags."""
    assert guess_pos(word) == expected


@pytest.mark.parametrize(("word", "expected"), SUFFIX_CASES)
def test_guess_pos_ignores_case_and_punctuation(word: str, expected: str) -> None:
    """Non-alphabetic characters are dropped before the table is consulted."""
    assert guess_pos(word.upper()) == expected
    assert guess_pos(f"{word}!") == expected


@pytest.mark.parametrize("word", ["", "123", "-", "  "])
def test_guess_pos_reports_x_for_letterless_input(word: str) -> None:
    """A word with no letters carries no morphological signal at all."""
    assert guess_pos(word) == "X"


@pytest.mark.parametrize("word", ["cat", "system", "gateway", "or", "ed"])
def test_guess_pos_falls_back_to_the_default_tag(word: str) -> None:
    """Words matching no suffix (or too short to) are tagged as nouns."""
    assert guess_pos(word) == DEFAULT_POS


def longest_suffix_pos(word: str) -> str:
    """Reference implementation of the documented "longest suffix wins" rule.

    Args:
        word: Surface form to classify.

    Returns:
        The tag of the longest table suffix that matches with at least
        :data:`MIN_STEM_LENGTH` characters of stem in front of it; the default
        tag when nothing matches, or ``"X"`` when the word holds no letters.
    """
    cleaned = "".join(character for character in word.casefold() if character.isalpha())
    if not cleaned:
        return "X"
    matches = [
        suffix
        for suffix in SUFFIX_POS
        if cleaned.endswith(suffix) and len(cleaned) - len(suffix) >= MIN_STEM_LENGTH
    ]
    if not matches:
        return DEFAULT_POS
    return SUFFIX_POS[max(matches, key=len)]


def test_the_suffix_table_is_ordered_longest_first() -> None:
    """The scan order is what makes the longest match win; pin it directly."""
    order = list(heuristic_module._SUFFIXES_LONGEST_FIRST)
    assert sorted(order) == sorted(SUFFIX_POS)
    assert [len(suffix) for suffix in order] == sorted(
        (len(suffix) for suffix in order), reverse=True
    )


@pytest.mark.parametrize("suffix", sorted(SUFFIX_POS), ids=sorted(SUFFIX_POS))
def test_every_table_suffix_is_reachable(suffix: str) -> None:
    """A stem plus a suffix resolves to that suffix's tag, not a shorter one's."""
    assert guess_pos("qa" + suffix) == SUFFIX_POS[suffix]


@settings(max_examples=300, deadline=None)
@given(
    word=st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz-'0123456789"),
        min_size=0,
        max_size=14,
    )
)
def test_guess_pos_agrees_with_the_longest_match_reference(word: str) -> None:
    """For any input, ``guess_pos`` is the longest-suffix rule and nothing else."""
    assert guess_pos(word) == longest_suffix_pos(word)


# ---------------------------------------------------------------------------
# annotation invariants
# ---------------------------------------------------------------------------
def tokenize(phrase: str, config: Optional[Config] = None) -> list[Token]:
    """Tokenise ``phrase`` with the Tier 0 tokenizer (no annotation)."""
    return Tokenizer(config if config is not None else Config()).tokenize(phrase)


def assert_annotation_invariants(before: Sequence[Token], after: Sequence[Token]) -> None:
    """Assert the whole :class:`NlpBackend` annotation contract in one place.

    Args:
        before: Tokens as the tokenizer produced them.
        after: The backend's returned tokens.

    Raises:
        AssertionError: If any invariant documented on ``NlpBackend`` is broken.
    """
    assert len(after) == len(before)
    for original, annotated in zip(before, after):
        assert annotated is not original, "annotate() must return new Token objects"
        assert annotated.text == original.text
        assert annotated.normalized == original.normalized
        assert annotated.index == original.index
        assert annotated.start == original.start
        assert annotated.end == original.end
        assert annotated.letters == original.letters
        assert annotated.subtokens == original.subtokens
        assert annotated.is_eligible == original.is_eligible
        if original.role in PRESERVED_ROLES:
            assert annotated.role is original.role
        assert annotated.is_critical == (annotated.role in CRITICAL_ROLES and annotated.is_eligible)


@pytest.mark.parametrize("phrase", ANNOTATION_CORPUS)
def test_heuristic_annotate_preserves_every_invariant(phrase: str) -> None:
    """The heuristic backend fills ``pos`` and touches nothing else."""
    tokens = tokenize(phrase)
    annotated = HeuristicBackend().annotate(phrase, tokens)
    assert_annotation_invariants(tokens, annotated)
    for original, token in zip(tokens, annotated):
        assert token.role is original.role, "the heuristic never overrules the tokenizer"
        assert token.pos


@pytest.mark.parametrize("phrase", ANNOTATION_CORPUS)
def test_tokenizer_output_already_satisfies_the_criticality_rule(phrase: str) -> None:
    """``is_critical`` is a function of role and eligibility before annotation too."""
    for token in tokenize(phrase):
        assert token.is_critical == (token.role in CRITICAL_ROLES and token.is_eligible)


def test_heuristic_annotate_preserves_acronym_and_numeral_roles() -> None:
    """Tokenizer-owned roles survive annotation, with their own POS tags."""
    phrase = "The API 3 Gateway System"
    tokens = tokenize(phrase)
    by_text = {token.text: token for token in HeuristicBackend().annotate(phrase, tokens)}

    assert by_text["API"].role is TokenRole.ACRONYM
    assert by_text["API"].pos == "PROPN"
    assert by_text["API"].is_critical is True
    assert by_text["3"].role is TokenRole.NUMERAL
    assert by_text["3"].pos == "NUM"
    assert by_text["The"].role is TokenRole.FUNCTION
    assert by_text["The"].pos == "DET"
    assert by_text["The"].is_critical is False


def test_heuristic_annotate_returns_an_empty_list_for_no_tokens() -> None:
    """No tokens in, no tokens out — and definitely no exception."""
    assert HeuristicBackend().annotate("", []) == []


def test_heuristic_annotate_is_deterministic() -> None:
    """Annotating the same input twice yields equal tokens."""
    phrase = "Multi-Factor Authentication of the XML 2 Parser"
    tokens = tokenize(phrase)
    backend = HeuristicBackend()
    assert backend.annotate(phrase, tokens) == backend.annotate(phrase, tokens)


def test_heuristic_annotate_ignores_the_text_argument() -> None:
    """The heuristic is context-free, so the raw text cannot change its verdict."""
    phrase = "Portable Document Format"
    tokens = tokenize(phrase)
    backend = HeuristicBackend()
    assert backend.annotate(phrase, tokens) == backend.annotate("something else", tokens)


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        (StopWordCategory.ARTICLE, "DET"),
        (StopWordCategory.DETERMINER, "DET"),
        (StopWordCategory.PREPOSITION, "ADP"),
        (StopWordCategory.CONJUNCTION, "CCONJ"),
        (StopWordCategory.PRONOUN, "PRON"),
        (StopWordCategory.AUXILIARY, "AUX"),
        (StopWordCategory.PARTICLE, "PART"),
        (StopWordCategory.OTHER, "X"),
    ],
)
def test_stop_word_categories_map_to_universal_tags(
    category: StopWordCategory, expected: str
) -> None:
    """A categorised stop word is tagged from its class, not from its ending."""
    token = Token(
        text="w",
        normalized="w",
        index=0,
        start=0,
        end=1,
        role=TokenRole.FUNCTION,
        stop_word_category=category,
        is_eligible=False,
    )
    annotated = HeuristicBackend().annotate("w", [token])[0]
    assert annotated.pos == expected


# ---------------------------------------------------------------------------
# the shared role-update machinery every Tier 1 backend runs through
# ---------------------------------------------------------------------------
def make_token(**overrides: Any) -> Token:
    """Build a content token, overriding any field."""
    fields: dict[str, Any] = {
        "text": "Gateway",
        "normalized": "gateway",
        "index": 3,
        "start": 10,
        "end": 17,
        "role": TokenRole.CONTENT,
        "is_critical": True,
        "is_eligible": True,
        "letters": "GA",
    }
    fields.update(overrides)
    return Token(**fields)


@pytest.mark.parametrize("role", sorted(PRESERVED_ROLES, key=lambda item: item.value))
@pytest.mark.parametrize("pos", ["DET", "ADP", "NOUN", "VERB", "X"])
def test_tokenizer_owned_roles_survive_a_tier_one_tag(role: TokenRole, pos: str) -> None:
    """No POS tag may re-label an ACRONYM, NUMERAL or SYMBOL token."""
    token = make_token(role=role, is_critical=role in CRITICAL_ROLES)
    assert role_for_pos(token, pos) is role
    annotated = apply_annotation(token, Annotation(text=token.text, pos=pos), update_roles=True)
    assert annotated.role is role
    assert annotated.pos == pos


@pytest.mark.parametrize("pos", ["NOUN", "PROPN", "VERB", "ADJ", "NUM"])
def test_content_tags_promote_a_token_to_content(pos: str) -> None:
    """A content tag makes the token part of ``T_critical`` when it is eligible."""
    token = make_token(role=TokenRole.FUNCTION, is_critical=False)
    annotated = apply_annotation(token, Annotation(text=token.text, pos=pos), update_roles=True)
    assert annotated.role is TokenRole.CONTENT
    assert annotated.is_critical is True


@pytest.mark.parametrize("pos", ["DET", "ADP", "CCONJ", "SCONJ", "PRON", "AUX", "PART", "INTJ"])
def test_function_tags_demote_a_token_and_clear_criticality(pos: str) -> None:
    """A function tag removes the token from ``T_critical``."""
    token = make_token()
    annotated = apply_annotation(token, Annotation(text=token.text, pos=pos), update_roles=True)
    assert annotated.role is TokenRole.FUNCTION
    assert annotated.is_critical is False


def test_an_ineligible_token_never_becomes_critical() -> None:
    """Criticality is conjunctive: a content role is not enough on its own."""
    token = make_token(role=TokenRole.FUNCTION, is_critical=False, is_eligible=False)
    annotated = apply_annotation(token, Annotation(text=token.text, pos="NOUN"), update_roles=True)
    assert annotated.role is TokenRole.CONTENT
    assert annotated.is_critical is False


def test_unknown_tag_on_a_capitalised_token_counts_as_content() -> None:
    """``X`` plus an uppercase letter is a mis-tagged proper noun, not noise."""
    upper = make_token(text="Kubernetes", role=TokenRole.UNKNOWN, is_critical=False)
    lower = make_token(text="kubernetes", role=TokenRole.UNKNOWN, is_critical=False)
    assert role_for_pos(upper, "X") is TokenRole.CONTENT
    assert role_for_pos(lower, "X") is TokenRole.UNKNOWN


def test_apply_annotation_leaves_offsets_alone() -> None:
    """Even a role change may not move a token in the source text."""
    token = make_token()
    annotated = apply_annotation(
        token, Annotation(text="different", pos="ADP", lemma="lemma"), update_roles=True
    )
    assert (annotated.text, annotated.start, annotated.end, annotated.index) == (
        token.text,
        token.start,
        token.end,
        token.index,
    )
    assert annotated.lemma == "lemma"


def test_apply_annotation_without_an_annotation_is_the_identity() -> None:
    """A token the backend could not align to is returned untouched."""
    token = make_token()
    assert apply_annotation(token, None) is token


# ---------------------------------------------------------------------------
# availability probes never raise
# ---------------------------------------------------------------------------
@pytest.fixture
def isolated_backend_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Swap the module-level backend caches for empty ones, restored on teardown.

    Both backends memoise successes *and* failures process-wide, so a simulated
    failure must not be allowed to poison a later real probe (or another test
    module's ``requires_nlp`` run).
    """
    monkeypatch.setattr(spacy_module, "PIPELINE_CACHE", {})
    monkeypatch.setattr(spacy_module, "_FAILED_MODELS", set())
    monkeypatch.setattr(nltk_module, "_TAGGER_CACHE", {})
    monkeypatch.setattr(nltk_module, "_FAILED_TAGGERS", set())
    monkeypatch.setattr(nltk_module, "_LEMMATIZER_CACHE", {})
    monkeypatch.setattr(nltk_module, "_PROBED_LEMMATIZERS", set())


@pytest.mark.parametrize("backend_cls", [SpacyBackend, NltkBackend])
@pytest.mark.parametrize("language", list(Language), ids=lambda lang: lang.value)
def test_optional_backend_probes_return_a_bool(backend_cls: type, language: Language) -> None:
    """``is_available`` answers ``True``/``False`` for every language, never raising."""
    available = backend_cls(language=language).is_available()
    assert isinstance(available, bool)
    assert available is True or available is False


@pytest.mark.parametrize("backend_cls", [SpacyBackend, NltkBackend])
def test_optional_backend_probes_are_repeatable(backend_cls: type) -> None:
    """Probing twice cannot flip the answer; the verdict is cached, not resampled."""
    backend = backend_cls()
    assert backend.is_available() == backend.is_available()


def test_spacy_backend_maps_a_model_for_every_language() -> None:
    """Each supported language names the small pipeline it would load."""
    for language in Language:
        assert MODEL_BY_LANGUAGE[language]
        assert SpacyBackend(language=language).model_name == MODEL_BY_LANGUAGE[language]


def test_nltk_backend_is_unavailable_for_unsupported_languages() -> None:
    """NLTK's perceptron tagger is English-only here, and says so without raising."""
    for language in Language:
        backend = NltkBackend(language=language)
        if language in NLTK_LANGUAGE_CODES:
            continue
        assert backend.language_code is None
        assert backend.is_available() is False
        with pytest.raises(BackendUnavailable):
            backend.annotate("x", tokenize("Portable Document Format"))


@pytest.mark.usefixtures("isolated_backend_caches")
def test_spacy_probe_survives_a_missing_package(monkeypatch: pytest.MonkeyPatch) -> None:
    """``import spacy`` failing is reported as unavailable, not propagated."""
    monkeypatch.setitem(sys.modules, "spacy", None)
    assert SpacyBackend().is_available() is False


@pytest.mark.usefixtures("isolated_backend_caches")
def test_spacy_probe_survives_a_broken_installation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A spaCy that imports but explodes on load is still just "unavailable"."""

    def explode(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("simulated spaCy model/version mismatch")

    fake = types.ModuleType("spacy")
    fake.load = explode  # type: ignore[attr-defined]
    fake.blank = explode  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "spacy", fake)

    assert SpacyBackend().is_available() is False
    with pytest.raises(BackendUnavailable):
        SpacyBackend().annotate("Portable Document Format", tokenize("Portable Document Format"))


@pytest.mark.usefixtures("isolated_backend_caches")
def test_nltk_probe_survives_a_missing_package(monkeypatch: pytest.MonkeyPatch) -> None:
    """``from nltk import pos_tag`` failing reports unavailable rather than raising."""
    monkeypatch.setitem(sys.modules, "nltk", None)
    assert NltkBackend().is_available() is False


@pytest.mark.usefixtures("isolated_backend_caches")
def test_nltk_probe_survives_missing_corpus_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """An installed NLTK whose tagger data was never downloaded is unavailable.

    This is the failure mode the probe exists for: ``import nltk`` succeeds and
    ``LookupError`` only surfaces on the first real tagging call.
    """

    def missing_corpus(*args: Any, **kwargs: Any) -> Any:
        raise LookupError("Resource averaged_perceptron_tagger not found.")

    fake = types.ModuleType("nltk")
    fake.pos_tag = missing_corpus  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "nltk", fake)

    assert NltkBackend().is_available() is False


def test_backend_caches_were_restored() -> None:
    """Guards the simulations above: the real module globals are back in place."""
    assert isinstance(spacy_module.PIPELINE_CACHE, dict)
    assert isinstance(nltk_module._TAGGER_CACHE, dict)
    assert SpacyBackend().is_available() in (True, False)
    assert NltkBackend().is_available() in (True, False)


# ---------------------------------------------------------------------------
# Penn -> Universal mapping (pure, needs no NLTK)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("NN", "NOUN"),
        ("NNS", "NOUN"),
        ("NNP", "PROPN"),
        ("NNPS", "PROPN"),
        ("VB", "VERB"),
        ("VBG", "VERB"),
        ("MD", "AUX"),
        ("JJ", "ADJ"),
        ("RB", "ADV"),
        ("IN", "ADP"),
        ("DT", "DET"),
        ("CC", "CCONJ"),
        ("PRP", "PRON"),
        ("PRP$", "PRON"),
        ("TO", "PART"),
        ("CD", "NUM"),
        ("SYM", "SYM"),
        (".", "PUNCT"),
        ("FW", "X"),
        ("NNPX", "PROPN"),
        ("VBQQ", "VERB"),
        ("ZZZ", "X"),
    ],
)
def test_penn_to_universal(tag: str, expected: str) -> None:
    """Known tags map directly; unknown ones fall back longest-prefix, then ``X``."""
    assert penn_to_universal(tag) == expected
    assert penn_to_universal(tag.lower()) == expected


# ---------------------------------------------------------------------------
# real Tier 1 runtime
# ---------------------------------------------------------------------------
@requires_nlp
def test_auto_resolves_a_real_tier_one_backend() -> None:
    """With a runtime installed, ``AUTO`` picks it silently."""
    backend, warnings = resolve_backend(Config(engine_tier=EngineTier.AUTO))
    assert backend.name in TIER1_NAMES
    assert warnings == []
    assert backend.is_available() is True


@requires_nlp
@pytest.mark.parametrize("phrase", ANNOTATION_CORPUS)
def test_real_backend_annotation_preserves_every_invariant(phrase: str) -> None:
    """A real tagger obeys the same contract the heuristic does."""
    backend, _ = resolve_backend(Config(engine_tier=EngineTier.AUTO))
    tokens = tokenize(phrase)
    assert_annotation_invariants(tokens, backend.annotate(phrase, tokens))


@requires_nlp
def test_real_backend_annotation_is_deterministic() -> None:
    """The same phrase tagged twice by the same backend gives the same tokens."""
    phrase = "The Application Programming Interface returns a document"
    backend, _ = resolve_backend(Config(engine_tier=EngineTier.AUTO))
    tokens = tokenize(phrase)
    assert backend.annotate(phrase, tokens) == backend.annotate(phrase, tokens)


@requires_nlp
def test_real_backend_fills_pos_tags() -> None:
    """A Tier 1 backend must actually add information, not just copy tokens."""
    phrase = "The Application Programming Interface returns a document"
    backend, _ = resolve_backend(Config(engine_tier=EngineTier.AUTO))
    annotated = backend.annotate(phrase, tokenize(phrase))
    assert any(token.pos for token in annotated)
