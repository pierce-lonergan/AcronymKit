"""Tests for :mod:`acronymkit.extractor` -- the Schwartz & Hearst implementation.

The algorithm trades recall for precision, so most of what is pinned here is a
*refusal* to fire: enumerations, cross-references, prose parentheticals and
long forms that would have to cross a sentence boundary must all yield nothing.
The one invariant that holds unconditionally -- and is therefore asserted on
every single case, plus on hypothesis-generated documents -- is that the source
text sliced by a reported span equals the reported form.
"""

from __future__ import annotations

import time
from typing import Optional

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from acronymkit.config import Config
from acronymkit.extractor import (
    AbbreviationExtractor,
    find_best_long_form,
    is_valid_long_form,
    is_valid_short_form,
)
from acronymkit.models import AcronymPair
from conftest import EXTRACTION_CASES, timing_budget

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def extractor() -> AbbreviationExtractor:
    """A stock extractor under the default configuration."""
    return AbbreviationExtractor(Config())


def assert_spans_exact(text: str, pairs: list[AcronymPair]) -> None:
    """Assert the defining span invariant for every pair.

    ``text[span] == form`` must hold for both the short and the long form; a
    reported offset that does not slice back to the reported string would make
    every downstream highlighter and redactor wrong.
    """
    for pair in pairs:
        short_start, short_end = pair.short_form_span
        long_start, long_end = pair.long_form_span
        assert text[short_start:short_end] == pair.short_form
        assert text[long_start:long_end] == pair.long_form
        assert 0 <= short_start < short_end <= len(text)
        assert 0 <= long_start < long_end <= len(text)


def pair_tuples(pairs: list[AcronymPair]) -> list[tuple[str, str]]:
    """Reduce pairs to the ``(short_form, long_form)`` tuples used in tables."""
    return [(pair.short_form, pair.long_form) for pair in pairs]


# ---------------------------------------------------------------------------
# The extraction corpus
# ---------------------------------------------------------------------------

#: ``(id, document, expected [(short, long), ...])``. Every entry is a
#: behavioural claim about the algorithm, not an observation of its output.
_EXTRA_EXTRACTION_CASES: list[tuple[str, str, list[tuple[str, str]]]] = [
    # -- canonical Long Form (Short Form) ---------------------------------
    (
        "canonical-who",
        "The World Health Organization (WHO) responded.",
        [("WHO", "World Health Organization")],
    ),
    (
        "canonical-dna",
        "Deoxyribonucleic acid (DNA) was sequenced.",
        [("DNA", "Deoxyribonucleic acid")],
    ),
    (
        "canonical-tnf",
        "Genes such as tumour necrosis factor (TNF) alpha.",
        [("TNF", "tumour necrosis factor")],
    ),
    (
        "canonical-lowercase-long-form",
        "This is a randomised controlled trial (RCT) of the drug.",
        [("RCT", "randomised controlled trial")],
    ),
    # -- inverted Short Form (Long Form) -----------------------------------
    (
        "inverted-cns",
        "The CNS (central nervous system) is complex.",
        [("CNS", "central nervous system")],
    ),
    (
        "inverted-lstm",
        "We trained an LSTM (long short term memory) network.",
        [("LSTM", "long short term memory")],
    ),
    # A capitalised expansion is the common real-world shape of the inverted
    # arrangement, and its first word ("World", "National", "Magnetic") looks
    # superficially like a bracketed short form. It must not be taken as one.
    (
        "inverted-capitalised-who",
        "The WHO (World Health Organization) is a body.",
        [("WHO", "World Health Organization")],
    ),
    (
        "inverted-capitalised-nasa",
        "NASA (National Aeronautics and Space Administration) launched it.",
        [("NASA", "National Aeronautics and Space Administration")],
    ),
    (
        "inverted-capitalised-mri",
        "We used MRI (Magnetic Resonance Imaging) scans.",
        [("MRI", "Magnetic Resonance Imaging")],
    ),
    (
        "inverted-capitalised-cns",
        "The CNS (Central Nervous System) is complex.",
        [("CNS", "Central Nervous System")],
    ),
    (
        "inverted-two-word-expansion",
        "The BD (Big Data) approach.",
        [("BD", "Big Data")],
    ),
    # -- several definitions in one document -------------------------------
    (
        "multiple-who-un",
        "The World Health Organization (WHO) and the United Nations (UN) met.",
        [("WHO", "World Health Organization"), ("UN", "United Nations")],
    ),
    (
        "multiple-sentences",
        "Central Nervous System (CNS). Multiple Sclerosis (MS) too.",
        [("CNS", "Central Nervous System"), ("MS", "Multiple Sclerosis")],
    ),
    (
        "multiple-mixed-brackets",
        "The central nervous system [CNS] and the peripheral nervous system {PNS} differ.",
        [("CNS", "central nervous system"), ("PNS", "peripheral nervous system")],
    ),
    # -- one definition, many later bare uses ------------------------------
    (
        "define-once-use-thrice",
        "The application programming interface (API) is stable. "
        "The API is documented. Use the API.",
        [("API", "application programming interface")],
    ),
    (
        "redefinition-at-a-second-offset",
        "The central nervous system (CNS) and the central nervous system (CNS) agree.",
        [
            ("CNS", "central nervous system"),
            ("CNS", "central nervous system"),
        ],
    ),
    # -- nested brackets ----------------------------------------------------
    (
        "nested-trailing-gloss",
        "The magnetic resonance imaging (MRI (fast)) scan.",
        [("MRI", "magnetic resonance imaging")],
    ),
    (
        "nested-inner-qualifier",
        "A study of the central nervous system (CNS (human)) was done.",
        [("CNS", "central nervous system")],
    ),
    (
        "nested-doubled",
        "The central nervous system ((CNS)) matters.",
        [("CNS", "central nervous system")],
    ),
    # -- unbalanced brackets ------------------------------------------------
    ("unbalanced-open", "The central nervous system (CNS was measured.", []),
    ("unbalanced-close", "The central nervous system CNS) was measured.", []),
    ("unbalanced-mixed", "The central nervous system (CNS] was measured.", []),
    ("unbalanced-runs", "((((((((((((((()))))))))))))))", []),
    # -- square and curly brackets -----------------------------------------
    (
        "square-brackets",
        "The central nervous system [CNS] was measured.",
        [("CNS", "central nervous system")],
    ),
    (
        "curly-brackets",
        "The central nervous system {CNS} was measured.",
        [("CNS", "central nervous system")],
    ),
    # -- cross references ---------------------------------------------------
    ("see-figure-3", "the result (see Figure 3) was clear", []),
    ("see-above", "The result (see above) was clear.", []),
    ("see-table-2", "See the appendix (Table 2) for details.", []),
    # -- enumerations -------------------------------------------------------
    ("enumeration", "(1) first item (2) second item", []),
    ("enumeration-lettered", "Consider (a) the first case (b) the second case.", []),
    # -- S&H 'first word' rule ---------------------------------------------
    (
        "first-word-rule-rct",
        "Randomised controlled trial (RCT; n=42) results.",
        [("RCT", "Randomised controlled trial")],
    ),
    (
        "first-word-rule-cns",
        "The central nervous system (CNS, n=12) was imaged.",
        [("CNS", "central nervous system")],
    ),
    # -- hyphenated long forms ---------------------------------------------
    (
        "hyphenated-nhl",
        "non-Hodgkin lymphoma (NHL) is common.",
        [("NHL", "non-Hodgkin lymphoma")],
    ),
    (
        "hyphenated-mfa",
        "Multi-Factor Authentication (MFA) is required.",
        [("MFA", "Multi-Factor Authentication")],
    ),
    (
        "hyphenated-short-form",
        "Interleukin 6 (IL-6) rose.",
        [("IL-6", "Interleukin 6")],
    ),
    # -- long form would have to cross a sentence boundary -----------------
    ("crosses-sentence-nasa", "We ended the sentence. Administration (NASA) followed.", []),
    (
        "crosses-sentence-split-name",
        "The National Aeronautics and Space. Administration (NASA) launched.",
        [],
    ),
    ("crosses-paragraph", "The central nervous system\n\n(CNS) after a blank line.", []),
    (
        "crosses-paragraph-crlf",
        "The central nervous system\r\n\r\n(CNS) after a blank line.",
        [],
    ),
    ("crosses-paragraph-cr", "The central nervous system\r\r(CNS) after a blank line.", []),
    # A *single* newline is a line wrap, not a paragraph break, whatever the
    # convention -- a CRLF document must not lose every wrapped definition.
    (
        "wrapped-long-form-lf",
        "The World Health\nOrganization (WHO) responded.",
        [("WHO", "World Health\nOrganization")],
    ),
    (
        "wrapped-long-form-crlf",
        "The World Health\r\nOrganization (WHO) responded.",
        [("WHO", "World Health\r\nOrganization")],
    ),
    (
        "wrapped-long-form-cr",
        "The World Health\rOrganization (WHO) responded.",
        [("WHO", "World Health\rOrganization")],
    ),
    (
        "abbreviation-is-not-a-sentence-end",
        "e.g. the central nervous system (CNS) matters.",
        [("CNS", "central nervous system")],
    ),
    (
        "title-is-not-a-sentence-end",
        "Dr. Smith studied the central nervous system (CNS) closely.",
        [("CNS", "central nervous system")],
    ),
    # -- prose parentheticals ----------------------------------------------
    ("prose-relative-clause", "The device (which was new) failed.", []),
    ("prose-namely", "Only one thing (namely this) matters.", []),
    ("prose-lowercase-short-form", "The central nervous system (cns) was measured.", []),
    # -- post-filters -------------------------------------------------------
    ("long-form-restates-short-form", "The Acme Corporation (Acme) filed.", []),
    ("short-form-below-min-length", "Word (A) here.", []),
    ("empty-brackets", "The system () failed.", []),
    ("nothing-precedes-the-bracket", "(NASA) launched.", []),
    ("no-brackets-at-all", "No parentheses here at all.", []),
    # -- delimiters that clip the window without killing the match ---------
    (
        "colon-delimiter",
        "Note: the central nervous system (CNS) matters.",
        [("CNS", "central nervous system")],
    ),
    (
        "semicolon-delimiter",
        "First clause; central nervous system (CNS) matters.",
        [("CNS", "central nervous system")],
    ),
    # -- unicode long forms -------------------------------------------------
    (
        "unicode-french",
        "Organisation Mondiale de la Santé (OMS) a répondu.",
        [("OMS", "Organisation Mondiale de la Santé")],
    ),
    (
        "unicode-german",
        "Bundesministerium für Bildung und Forschung (BMBF) ist zuständig.",
        [("BMBF", "Bundesministerium für Bildung und Forschung")],
    ),
    (
        "unicode-spanish",
        "El Instituto Nacional de Estadística (INE) publicó datos.",
        [("INE", "Instituto Nacional de Estadística")],
    ),
    (
        "unicode-astral-plane-noise",
        "Text with an emoji \U0001f600 and the central nervous system (CNS) here.",
        [("CNS", "central nervous system")],
    ),
    # U+0130 lowercases to two code points; it is still a letter, on both sides.
    (
        "unicode-turkish-dotted-i",
        "İstanbul Teknik Üniversitesi (İTÜ) kuruldu.",
        [("İTÜ", "İstanbul Teknik Üniversitesi")],
    ),
    (
        "unicode-turkish-dotted-i-inverted",
        "The İTÜ (İstanbul Teknik Üniversitesi) kuruldu.",
        [("İTÜ", "İstanbul Teknik Üniversitesi")],
    ),
    # -- blank input --------------------------------------------------------
    ("empty-string", "", []),
    ("whitespace-only", "   \n\t ", []),
]

ALL_EXTRACTION_CASES = [
    *(
        pytest.param(text, expected, id=f"conftest-{index}")
        for index, (text, expected) in enumerate(EXTRACTION_CASES)
    ),
    *(pytest.param(text, expected, id=name) for name, text, expected in _EXTRA_EXTRACTION_CASES),
]

#: Every document in the corpus, for invariants that do not care about outcome.
ALL_DOCUMENTS = [text for text, _ in EXTRACTION_CASES] + [
    text for _, text, _ in _EXTRA_EXTRACTION_CASES
]


# ---------------------------------------------------------------------------
# Corpus-driven extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("text", "expected"), ALL_EXTRACTION_CASES)
def test_extraction_corpus(
    extractor: AbbreviationExtractor, text: str, expected: list[tuple[str, str]]
) -> None:
    """Each document yields exactly the expected pairs, with exact spans."""
    pairs = extractor.extract(text)
    assert pair_tuples(pairs) == expected
    assert_spans_exact(text, pairs)


@pytest.mark.parametrize("text", ALL_DOCUMENTS)
def test_span_invariant_holds_for_every_document(
    extractor: AbbreviationExtractor, text: str
) -> None:
    """The span invariant is unconditional, whatever the document contains."""
    assert_spans_exact(text, extractor.extract(text))


@pytest.mark.parametrize("text", ALL_DOCUMENTS)
def test_extraction_is_deterministic(extractor: AbbreviationExtractor, text: str) -> None:
    """Repeated extraction of the same document returns identical pairs."""
    first = extractor.extract(text)
    second = extractor.extract(text)
    assert [pair.model_dump() for pair in first] == [pair.model_dump() for pair in second]


@pytest.mark.parametrize("text", ALL_DOCUMENTS)
def test_results_are_in_document_order(extractor: AbbreviationExtractor, text: str) -> None:
    """Pairs come back in the order the definitions appear in the source."""
    anchors = [
        min(pair.short_form_span[0], pair.long_form_span[0]) for pair in extractor.extract(text)
    ]
    assert anchors == sorted(anchors)


@pytest.mark.parametrize("text", ALL_DOCUMENTS)
def test_results_are_deduplicated(extractor: AbbreviationExtractor, text: str) -> None:
    """No two returned pairs share (short form, long form, both spans)."""
    keys = [
        (pair.short_form, pair.long_form, pair.short_form_span, pair.long_form_span)
        for pair in extractor.extract(text)
    ]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize(
    ("text", "pattern"),
    [
        ("The World Health Organization (WHO) responded.", "long(short)"),
        ("The central nervous system [CNS] was measured.", "long(short)"),
        ("MRI (magnetic resonance imaging) confirmed it.", "short(long)"),
        ("The CNS (central nervous system) is complex.", "short(long)"),
    ],
)
def test_pattern_records_the_arrangement(
    extractor: AbbreviationExtractor, text: str, pattern: str
) -> None:
    """``pattern`` distinguishes the canonical from the inverted arrangement."""
    pairs = extractor.extract(text)
    assert [pair.pattern for pair in pairs] == [pattern]


# ---------------------------------------------------------------------------
# The inverted arrangement with a capitalised expansion
# ---------------------------------------------------------------------------
#
# "(World Health Organization)" opens with a token that passes every short-form
# rule, so the region can be read as a bracketed short form and matched forward.
# That reading fails, and committing to it loses the definition: the canonical
# branch must be an attempt, not a commitment, and the first-word rule must
# refuse a plainly multi-word Title Case phrase.

_CAPITALISED_INVERTED_CASES = [
    ("The WHO (World Health Organization) is a body.", "WHO", "World Health Organization"),
    (
        "NASA (National Aeronautics and Space Administration) launched it.",
        "NASA",
        "National Aeronautics and Space Administration",
    ),
    ("We used MRI (Magnetic Resonance Imaging) scans.", "MRI", "Magnetic Resonance Imaging"),
    ("The CNS (Central Nervous System) is complex.", "CNS", "Central Nervous System"),
    (
        "We trained an LSTM (Long Short Term Memory) network.",
        "LSTM",
        "Long Short Term Memory",
    ),
    (
        "The API (Application Programming Interface) is stable.",
        "API",
        "Application Programming Interface",
    ),
    ("A DNA (Deoxyribonucleic Acid) strand.", "DNA", "Deoxyribonucleic Acid"),
    ("The BD (Big Data) approach.", "BD", "Big Data"),
]


@pytest.mark.parametrize(
    ("text", "short_form", "long_form"),
    _CAPITALISED_INVERTED_CASES,
    ids=["who", "nasa", "mri", "cns", "lstm", "api", "dna", "big-data"],
)
def test_inverted_arrangement_fires_for_a_capitalised_expansion(
    extractor: AbbreviationExtractor, text: str, short_form: str, long_form: str
) -> None:
    """``Short Form (Long Form)`` works when the expansion is Title Case."""
    pairs = extractor.extract(text)
    assert pair_tuples(pairs) == [(short_form, long_form)]
    assert [pair.pattern for pair in pairs] == ["short(long)"]
    assert_spans_exact(text, pairs)


def test_the_first_word_of_a_title_case_phrase_is_not_a_short_form(
    extractor: AbbreviationExtractor,
) -> None:
    """ "World" is a word in the expansion, not the abbreviation being defined."""
    pairs = extractor.extract("The WHO (World Health Organization) is a body.")
    assert [pair.short_form for pair in pairs] == ["WHO"]
    assert [pair.long_form for pair in pairs] == ["World Health Organization"]


@pytest.mark.parametrize(
    "text",
    [
        "the result (see Figure 3) was clear",
        "The result (see above) was clear.",
        "See the appendix (Table 2) for details.",
        "(1) first item (2) second item",
        "Consider (a) the first case (b) the second case.",
        "The device (which was new) failed.",
        "Only one thing (namely this) matters.",
        "The Acme Corporation (Acme) filed.",
        "(NASA) launched.",
        "The central nervous system (cns) was measured.",
        "We ended the sentence. Administration (NASA) followed.",
        "The central nervous system\n\n(CNS) after a blank line.",
    ],
    ids=[
        "see-figure",
        "see-above",
        "table-2",
        "enumeration",
        "enumeration-lettered",
        "relative-clause",
        "namely",
        "restatement",
        "nothing-precedes",
        "lowercase-short-form",
        "crosses-sentence",
        "crosses-paragraph",
    ],
)
def test_falling_back_to_the_inverted_branch_does_not_match_prose(
    extractor: AbbreviationExtractor, text: str
) -> None:
    """Trying the inverted branch second must not cost any precision."""
    assert extractor.extract(text) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Randomised controlled trial (RCT; n=42) results.",
            ("RCT", "Randomised controlled trial"),
        ),
        ("The central nervous system (CNS, n=12) was imaged.", ("CNS", "central nervous system")),
        (
            "The magnetic resonance imaging (MRI (fast)) scan.",
            ("MRI", "magnetic resonance imaging"),
        ),
    ],
    ids=["rct-semicolon", "cns-comma", "nested-gloss"],
)
def test_the_first_word_rule_still_fires_for_a_real_abbreviation(
    extractor: AbbreviationExtractor, text: str, expected: tuple[str, str]
) -> None:
    """An all-caps first word followed by a gloss keeps the canonical reading."""
    pairs = extractor.extract(text)
    assert pair_tuples(pairs) == [expected]
    assert [pair.pattern for pair in pairs] == ["long(short)"]


@pytest.mark.parametrize(
    ("text", "confidence"),
    [
        # Every short-form character sits on a long-form word initial.
        ("The World Health Organization (WHO) responded.", 1.0),
        # B,M,B,F vs initials B,f,B,u,F: 'M' places nowhere -> 3/4 aligned,
        # so 0.6 + 0.4 * 0.75 == 0.9.
        ("Bundesministerium für Bildung und Forschung (BMBF) ist da.", 0.9),
        # D,N,A vs initials D,a: 'N' places nowhere -> 2/3 aligned,
        # so 0.6 + 0.4 * 2/3 == 0.86666... -> rounded to 4 dp.
        ("Deoxyribonucleic acid (DNA) was sequenced.", 0.8667),
    ],
)
def test_confidence_is_the_initial_alignment_fraction(
    extractor: AbbreviationExtractor, text: str, confidence: float
) -> None:
    """Confidence is a stated linear function of the initial-match fraction."""
    pairs = extractor.extract(text)
    assert len(pairs) == 1
    assert pairs[0].confidence == pytest.approx(confidence)


@pytest.mark.parametrize("text", ALL_DOCUMENTS)
def test_confidence_stays_within_the_documented_band(
    extractor: AbbreviationExtractor, text: str
) -> None:
    """Confidence never leaves ``[0.6, 1.0]``."""
    for pair in extractor.extract(text):
        assert 0.6 <= pair.confidence <= 1.0


# ---------------------------------------------------------------------------
# Line endings
# ---------------------------------------------------------------------------
#
# The window scan stops at a *blank line*. Testing the character before a "\n"
# for membership in "\n\r" gets that wrong on every Windows document, because
# the "\r" of an ordinary CRLF matches: each definition whose long form wraps a
# line is then silently lost. What follows pins both halves of the rule --
# a blank line stops the window, a lone newline does not -- in all three
# conventions, and against mixtures of them.

#: ``(document template, expected long form template)``; ``<NL>`` is the wrap.
_WRAPPED_DEFINITIONS = [
    (
        "The World Health<NL>Organization (WHO) responded.",
        "WHO",
        "World Health<NL>Organization",
    ),
    (
        "We used a support vector<NL>machine (SVM) classifier.",
        "SVM",
        "support vector<NL>machine",
    ),
    (
        "The central nervous<NL>system [CNS] was measured.",
        "CNS",
        "central nervous<NL>system",
    ),
    (
        "Deoxyribonucleic<NL>acid (DNA) was sequenced.",
        "DNA",
        "Deoxyribonucleic<NL>acid",
    ),
    # The inverted arrangement wraps too: here the *bracketed* text is split.
    (
        "The MRI (Magnetic Resonance<NL>Imaging) scan.",
        "MRI",
        "Magnetic Resonance<NL>Imaging",
    ),
]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"], ids=["lf", "crlf", "cr"])
@pytest.mark.parametrize(
    ("template", "short_form", "long_form_template"),
    _WRAPPED_DEFINITIONS,
    ids=["who", "svm", "cns-square", "dna", "mri-inverted"],
)
def test_a_single_newline_is_a_line_wrap_not_a_paragraph_break(
    extractor: AbbreviationExtractor,
    newline: str,
    template: str,
    short_form: str,
    long_form_template: str,
) -> None:
    """A definition that wraps a line survives in LF, CRLF and CR documents."""
    text = template.replace("<NL>", newline)
    pairs = extractor.extract(text)
    assert pair_tuples(pairs) == [(short_form, long_form_template.replace("<NL>", newline))]
    assert_spans_exact(text, pairs)


@pytest.mark.parametrize(
    "blank_line",
    ["\n\n", "\r\n\r\n", "\r\r", "\n\r\n", "\r\n\n", "\r\r\n"],
    ids=["lf-lf", "crlf-crlf", "cr-cr", "lf-crlf", "crlf-lf", "cr-crlf"],
)
def test_a_blank_line_in_any_convention_stops_the_window(
    extractor: AbbreviationExtractor, blank_line: str
) -> None:
    """Two line terminators in a row remain a hard boundary, however written."""
    text = f"The central nervous system{blank_line}(CNS) after a blank line."
    assert extractor.extract(text) == []


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"], ids=["lf", "crlf", "cr"])
def test_line_endings_do_not_change_the_recovered_words(
    extractor: AbbreviationExtractor, newline: str
) -> None:
    """Re-wrapping a document changes its bytes, never its extracted words."""
    text = f"The World Health{newline}Organization (WHO) responded."
    pairs = extractor.extract(text)
    assert len(pairs) == 1
    assert pairs[0].long_form.split() == ["World", "Health", "Organization"]
    # The span still indexes the *original* string, newline and all.
    assert text[slice(*pairs[0].long_form_span)] == pairs[0].long_form
    assert newline in pairs[0].long_form


# ---------------------------------------------------------------------------
# Blank input
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["", " ", "\t", "\n\n", "   \n\t \r ", "\u00a0"])
def test_blank_input_returns_an_empty_list(extractor: AbbreviationExtractor, text: str) -> None:
    """Empty and whitespace-only documents yield ``[]`` rather than raising."""
    assert extractor.extract(text) == []


# ---------------------------------------------------------------------------
# Sentence capture
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Intro text. The central nervous system (CNS) matters. Outro.",
        "MRI (magnetic resonance imaging) confirmed it. Next sentence here.",
        "The World Health Organization (WHO) met. The United Nations (UN) met.",
        "Dr. Smith studied the central nervous system (CNS) closely. He left.",
    ],
)
def test_capture_sentences_populates_a_sentence_containing_the_short_form(
    text: str,
) -> None:
    """``extraction_capture_sentences`` attaches the enclosing sentence."""
    pairs = AbbreviationExtractor(Config(extraction_capture_sentences=True)).extract(text)
    assert pairs
    for pair in pairs:
        assert pair.sentence is not None
        assert pair.short_form in pair.sentence
        assert pair.long_form in pair.sentence
        assert pair.sentence in text


def test_sentence_is_not_captured_by_default(extractor: AbbreviationExtractor) -> None:
    """The field stays ``None`` unless capture is explicitly requested."""
    text = "Intro text. The central nervous system (CNS) matters. Outro."
    pairs = extractor.extract(text)
    assert pairs
    assert all(pair.sentence is None for pair in pairs)


def test_capture_sentences_does_not_disturb_the_spans() -> None:
    """Attaching sentences copies the pair without moving its offsets."""
    text = "Intro. The central nervous system (CNS) matters. Outro."
    plain = AbbreviationExtractor(Config()).extract(text)
    captured = AbbreviationExtractor(Config(extraction_capture_sentences=True)).extract(text)
    assert [p.short_form_span for p in plain] == [p.short_form_span for p in captured]
    assert [p.long_form_span for p in plain] == [p.long_form_span for p in captured]
    assert_spans_exact(text, captured)


# ---------------------------------------------------------------------------
# Configured short-form length bounds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("min_length", "max_length", "found"),
    [
        (2, 10, True),
        (3, 10, True),
        (4, 10, False),  # "CNS" is shorter than the configured minimum
        (2, 3, True),
        (2, 2, False),  # "CNS" is longer than the configured maximum
    ],
)
def test_extraction_short_form_length_bounds(min_length: int, max_length: int, found: bool) -> None:
    """``extraction_{min,max}_short_form_length`` gate the parenthetical."""
    config = Config(
        extraction_min_short_form_length=min_length,
        extraction_max_short_form_length=max_length,
    )
    pairs = AbbreviationExtractor(config).extract("The central nervous system (CNS) matters.")
    assert bool(pairs) is found
    if found:
        assert pairs[0].short_form == "CNS"


def test_extraction_max_length_rejects_an_over_long_short_form() -> None:
    """A four-character short form disappears once the ceiling drops to three."""
    text = "Bundesministerium fuer Bildung und Forschung (BMBF) ist da."
    assert AbbreviationExtractor(Config(extraction_max_short_form_length=4)).extract(text)
    assert not AbbreviationExtractor(Config(extraction_max_short_form_length=3)).extract(text)


# ---------------------------------------------------------------------------
# find_best_long_form as a pure function
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("short_form", "window", "expected"),
    [
        (
            "NASA",
            "The National Aeronautics and Space Administration",
            "National Aeronautics and Space Administration",
        ),
        ("SVM", "We used a support vector machine", "support vector machine"),
        ("MRI", "magnetic resonance imaging", "magnetic resonance imaging"),
        ("HMM", "hidden markov model", "hidden markov model"),
        ("CAT", "the cat", "cat"),
        ("CS", "computer science", "computer science"),
        # Case folding is symmetric: the short form's case is irrelevant.
        (
            "nasa",
            "The National Aeronautics and Space Administration",
            "National Aeronautics and Space Administration",
        ),
        # Non-alphanumeric short-form characters are skipped, not matched.
        (
            "N.A.S.A.",
            "The National Aeronautics and Space Administration",
            "National Aeronautics and Space Administration",
        ),
        # The remaining characters may sit inside a word; only the first is
        # constrained to a boundary.
        ("CAT", "concatenate", "concatenate"),
        ("PT", "prompt", "prompt"),
    ],
)
def test_find_best_long_form_matches(short_form: str, window: str, expected: str) -> None:
    """The right-to-left matcher recovers the expected expansion."""
    assert find_best_long_form(short_form, window) == expected


@pytest.mark.parametrize(
    ("short_form", "window"),
    [
        ("XYZ", "the quick brown fox"),  # 'z' is absent
        ("ABC", "alphabet"),  # 'c' is absent
        ("CS", "physics"),  # 'c' precedes no 's'
        ("", "the quick brown fox"),  # no short form
        ("ABC", ""),  # no window
        ("", ""),
    ],
)
def test_find_best_long_form_returns_none_on_failure(short_form: str, window: str) -> None:
    """Running the window cursor off the left edge is a failure, not a guess."""
    assert find_best_long_form(short_form, window) is None


@pytest.mark.parametrize(
    ("short_form", "no_boundary", "with_boundary"),
    [
        ("AT", "cat", "a cat"),
        ("XT", "extent", "x extent"),
        ("NS", "bones", "n bones"),
    ],
)
def test_first_character_must_land_on_a_word_boundary(
    short_form: str, no_boundary: str, with_boundary: str
) -> None:
    """The precision of S&H comes from constraining the *first* character.

    Both windows contain the short form's characters in the right order; only
    the one where the leading character begins a word may match.
    """
    assert find_best_long_form(short_form, no_boundary) is None
    matched = find_best_long_form(short_form, with_boundary)
    assert matched is not None
    assert matched[0].lower() == short_form[0].lower()


@pytest.mark.parametrize(
    ("short_form", "window"),
    [
        ("NASA", "The National Aeronautics and Space Administration"),
        ("CNS", "the central nervous system"),
        ("CAT", "concatenate"),
        ("XYZ", "the quick brown fox"),
        ("AT", "cat"),
    ],
)
def test_find_best_long_form_returns_a_suffix_of_the_window(short_form: str, window: str) -> None:
    """A successful match is always a suffix of the window it was found in."""
    matched = find_best_long_form(short_form, window)
    if matched is not None:
        assert window.endswith(matched)


# ---------------------------------------------------------------------------
# Characters whose lowercase is not one code point
# ---------------------------------------------------------------------------
#
# U+0130 LATIN CAPITAL LETTER I WITH DOT ABOVE lowercases to "i" + U+0307, a
# two-code-point string whose ``.isalnum()`` is False. Deciding "is this a
# letter?" on the *folded* text therefore drops a real letter -- and when the
# dropped letter is the first one, the word-boundary constraint that gives the
# algorithm its precision is never applied at all.


def test_dotted_capital_i_is_matched_rather_than_skipped() -> None:
    """U+0130 aligns like any other letter."""
    window = "İstanbul Teknik Üniversitesi"
    assert find_best_long_form("İTÜ", window) == window


def test_dotted_capital_i_matches_its_ascii_counterpart() -> None:
    """The fold is stable on both sides: "I" and "İ" compare equal."""
    window = "İstanbul Technical University"
    assert find_best_long_form("ITU", window) == window


def test_a_skipped_first_letter_does_not_forfeit_the_boundary_constraint() -> None:
    """Treating U+0130 as punctuation would promote "X" to the constrained slot.

    "The Xylophone Society" holds no "i"/"İ" at a word boundary, so there is no
    alignment at all; a matcher that silently dropped the "İ" would answer
    "Xylophone Society" instead.
    """
    assert find_best_long_form("İX", "The Xylophone Society") is None


def test_a_dotted_capital_i_definition_is_extracted_end_to_end(
    extractor: AbbreviationExtractor,
) -> None:
    """The defect is visible through the public API too, in both arrangements."""
    canonical = "İstanbul Teknik Üniversitesi (İTÜ) kuruldu."
    inverted = "The İTÜ (İstanbul Teknik Üniversitesi) kuruldu."
    assert pair_tuples(extractor.extract(canonical)) == [("İTÜ", "İstanbul Teknik Üniversitesi")]
    assert pair_tuples(extractor.extract(inverted)) == [("İTÜ", "İstanbul Teknik Üniversitesi")]
    assert_spans_exact(canonical, extractor.extract(canonical))
    assert_spans_exact(inverted, extractor.extract(inverted))


# ---------------------------------------------------------------------------
# is_valid_short_form
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("candidate", "valid"),
    [
        ("CNS", True),
        ("Ab", True),  # at least one uppercase letter is enough
        ("AB", True),
        ("1A", True),  # may start with a digit
        ("A B", True),  # two words are permitted
        (" CNS ", True),  # surrounding whitespace is ignored
        ("CNS.", True),  # trailing punctuation is tolerated
        ("AB", True),
        ("ABCDEFGHIJ", True),  # exactly the default maximum
        ("cns", False),  # no uppercase letter
        ("A", False),  # below the default minimum
        ("", False),
        ("   ", False),
        ("12", False),  # no letter at all
        ("ABCDEFGHIJK", False),  # one over the default maximum
        ("A B C", False),  # three words
        ("-AB", False),  # must start with an alphanumeric
        ("(AB", False),
        ("n=42", False),  # no uppercase, and not all-caps
    ],
)
def test_is_valid_short_form_defaults(candidate: str, valid: bool) -> None:
    """The default admissibility rules, boundary by boundary."""
    assert is_valid_short_form(candidate) is valid


@pytest.mark.parametrize(
    ("candidate", "min_length", "max_length", "valid"),
    [
        ("AB", 2, 10, True),
        ("AB", 3, 10, False),  # exactly one below the floor
        ("ABC", 3, 10, True),  # exactly on the floor
        ("ABCD", 2, 4, True),  # exactly on the ceiling
        ("ABCDE", 2, 4, False),  # exactly one over the ceiling
        ("ABCDE", 5, 5, True),  # a degenerate but legal window
        ("ABCD", 5, 5, False),
    ],
)
def test_is_valid_short_form_length_bounds(
    candidate: str, min_length: int, max_length: int, valid: bool
) -> None:
    """``min_length``/``max_length`` are inclusive on both ends."""
    assert is_valid_short_form(candidate, min_length=min_length, max_length=max_length) is valid


# ---------------------------------------------------------------------------
# is_valid_long_form
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("short_form", "long_form", "valid"),
    [
        ("CNS", "central nervous system", True),
        ("AB", "abc", True),
        ("CNS", "CNS", False),  # identical, so not longer
        ("AB", "ab", False),  # same length
        ("AB", "a", False),  # shorter
        ("CNS", "the CNS system", False),  # restatement, not a definition
        ("ABC", "a b c d e f g h i", False),  # more than len(short) + 5 words
        ("ABC", "a b c d e f g h", True),  # exactly len(short) + 5 words
        # Hyphens are word separators too, so eight hyphenated components
        # exceed the ``len("AB") + 5 == 7`` word budget while seven do not.
        ("AB", "a-b-c-d-e-f-g", True),
        ("AB", "a-b-c-d-e-f-g-h", False),
        ("CNS", "", False),
        ("", "central nervous system", False),
        # Alphanumeric budget: the expansion must hold at least as many
        # alphanumeric characters as the short form does.
        ("ABCD", ".....abc", False),
    ],
)
def test_is_valid_long_form(short_form: str, long_form: str, valid: bool) -> None:
    """The post-filters that keep restatements and stubs out of the output."""
    assert is_valid_long_form(short_form, long_form) is valid


def test_long_form_containing_the_short_form_is_rejected_case_sensitively(
    extractor: AbbreviationExtractor,
) -> None:
    """A parenthetical that merely repeats a word of the long form is dropped."""
    assert extractor.extract("The Acme Corporation (Acme) filed.") == []


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------

_LOWER = "abcdefghijklmnopqrstuvwxyz"
_LEAD_INS = ["", "The ", "We used the ", "In this study the ", "Results from the "]
_TAIL_OUTS = ["", ".", " was measured.", " followed the protocol.", "; see below."]


@st.composite
def _definition_documents(draw: st.DrawFn) -> tuple[str, str]:
    """Build a document that genuinely defines an abbreviation.

    Returns:
        ``(document, short_form)`` where ``document`` places a lowercase long
        form immediately before its parenthesised uppercase initialism.
    """
    words = draw(st.lists(st.text(alphabet=_LOWER, min_size=3, max_size=9), min_size=2, max_size=5))
    long_form = " ".join(words)
    short_form = "".join(word[0] for word in words).upper()
    lead = draw(st.sampled_from(_LEAD_INS))
    tail = draw(st.sampled_from(_TAIL_OUTS))
    return f"{lead}{long_form} ({short_form}){tail}", short_form


@given(_definition_documents())
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_generated_definitions_are_recovered_with_exact_spans(
    document_and_short: tuple[str, str],
) -> None:
    """Templated definitions always resolve, and their spans always slice back."""
    document, short_form = document_and_short
    pairs = AbbreviationExtractor(Config()).extract(document)
    assert_spans_exact(document, pairs)
    assert [pair.short_form for pair in pairs] == [short_form]
    long_form = pairs[0].long_form
    assert document.endswith(long_form, 0, pairs[0].long_form_span[1])
    assert long_form.endswith(pairs[0].long_form.split()[-1])


_FUZZ_ALPHABET = "AB abcde()[]{};:.,-\n=1"


@given(st.text(alphabet=_FUZZ_ALPHABET, max_size=140))
@settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_span_invariant_survives_arbitrary_bracket_soup(document: str) -> None:
    """Whatever comes back from arbitrary input, the spans slice back exactly."""
    assert_spans_exact(document, AbbreviationExtractor(Config()).extract(document))


@given(st.text(alphabet=_FUZZ_ALPHABET, max_size=140))
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_extraction_of_arbitrary_input_is_deterministic(document: str) -> None:
    """Two extractions of the same arbitrary document agree exactly."""
    extractor = AbbreviationExtractor(Config())
    first = [pair.model_dump() for pair in extractor.extract(document)]
    second = [pair.model_dump() for pair in extractor.extract(document)]
    assert first == second


@given(
    st.text(alphabet="ABC", min_size=1, max_size=5),
    st.text(alphabet=_LOWER + " ", max_size=40),
)
@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_find_best_long_form_is_always_a_suffix(short_form: str, window: str) -> None:
    """The matcher can only ever return a suffix of the window it searched."""
    matched: Optional[str] = find_best_long_form(short_form, window)
    if matched is not None:
        assert window.endswith(matched)
        assert len(matched) <= len(window)


# ---------------------------------------------------------------------------
# Pathological input
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.parametrize(
    "document",
    [
        "(" * 20_000,
        ")" * 20_000,
        "()" * 10_000,
        "(" * 5_000 + ")" * 5_000,
        "([{" * 5_000 + "}])" * 5_000,
        ("(" + "A" * 200 + ")") * 500,
        "word (ABC) " * 2_000,
    ],
    ids=[
        "opens-only",
        "closes-only",
        "alternating",
        "deeply-nested",
        "mixed-nested",
        "huge-parentheticals",
        "many-definitions",
    ],
)
def test_pathological_bracket_input_completes_quickly(document: str) -> None:
    """Degenerate bracket runs must not blow up into super-linear time."""
    extractor = AbbreviationExtractor(Config())
    started = time.perf_counter()
    pairs = extractor.extract(document)
    elapsed = time.perf_counter() - started
    assert elapsed < timing_budget(5.0)
    assert_spans_exact(document, pairs)


# ---------------------------------------------------------------------------
# Cost per bracket region
# ---------------------------------------------------------------------------
#
# The bracket scanner reports one region per nesting level, so a document with
# N nested regions is examined N times. Everything done per region -- trimming
# to the trailing words, matching, and the post-filters -- must therefore be
# bounded by the short-form window budget rather than by the size of the region,
# or the whole extraction becomes quadratic in document length.


def _nested_region_document(regions: int) -> str:
    """Build ``regions`` nested bracket regions of nine characters each.

    Every region is preceded by a valid short form and opens with a lowercase
    word, so each one reaches the inverted branch; and every region's content
    ends inside the same unbounded run of closing brackets, which is a single
    "word" as wide as the document.
    """
    return "XY (foo " * regions + ")" * regions


def _extraction_seconds(document: str, repeats: int = 3) -> float:
    """Fastest of ``repeats`` extractions, to damp scheduler noise."""
    extractor = AbbreviationExtractor(Config())
    best = float("inf")
    for _ in range(repeats):
        started = time.perf_counter()
        extractor.extract(document)
        best = min(best, time.perf_counter() - started)
    return best


@pytest.mark.slow
def test_nested_regions_stay_sub_quadratic_across_a_doubling() -> None:
    """Doubling the document must not quadruple the time.

    Linear work doubles, quadratic work quadruples; the threshold sits between
    the two so noise cannot decide the outcome.
    """
    small = _extraction_seconds(_nested_region_document(4_000))
    large = _extraction_seconds(_nested_region_document(8_000))
    assert large < 3.0 * max(small, 0.01)


@pytest.mark.slow
def test_a_200kb_nested_document_does_not_hang() -> None:
    """A 200 KB nest of regions is linear work, not a hang.

    The ceiling is scaled by :func:`conftest.machine_factor` rather than fixed
    at two seconds: the original constant was a claim about the development
    machine's CPU and duly failed on slower shared runners while the code was
    behaving correctly. The *shape* of the cost is asserted by
    :func:`test_nested_regions_stay_sub_quadratic_across_a_doubling`, which is
    machine-independent; this test only catches a genuine pathology.
    """
    document = _nested_region_document(22_000)
    assert len(document) > 190_000
    extractor = AbbreviationExtractor(Config())
    started = time.perf_counter()
    pairs = extractor.extract(document)
    elapsed = time.perf_counter() - started
    assert elapsed < timing_budget(2.0)
    assert_spans_exact(document, pairs)


@pytest.mark.slow
def test_an_enormous_parenthetical_is_matched_from_its_tail_only() -> None:
    """Only the trailing words of a bracketed long form are ever examined.

    The definition sits at the very end of a 100 KB parenthetical: it must still
    be found, and finding it must not cost a pass over the whole region.
    """
    document = "CNS (" + "filler " * 15_000 + "central nervous system) matters."
    assert len(document) > 100_000
    extractor = AbbreviationExtractor(Config())
    started = time.perf_counter()
    pairs = extractor.extract(document)
    elapsed = time.perf_counter() - started
    assert elapsed < 2.0
    assert pair_tuples(pairs) == [("CNS", "central nervous system")]
    assert_spans_exact(document, pairs)
