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
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from acronymkit.config import Config
from acronymkit.extractor import (
    AbbreviationExtractor,
    _trim_span,
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
    # -- a bracketed short form keeps its own closing bracket ---------------
    # ``_trim_span`` used to strip the trailing ``)`` unconditionally, so these
    # documents yielded ``FEV(1`` and ``NDS(2`` -- unmatched openers that equal
    # no annotation under any convention. The long form was unaffected either
    # way, because the matcher skips non-alphanumeric short-form characters, so
    # the defect cost a pair outright rather than mis-scoring one.
    (
        "balanced-trim-subscripted-short-form",
        "Forced expiratory volume in 1 second (FEV(1)) fell.",
        [("FEV(1)", "Forced expiratory volume in 1 second")],
    ),
    (
        "balanced-trim-with-trailing-gloss",
        "Forced expiratory volume in 1 second (FEV(1); n=42) fell.",
        [("FEV(1)", "Forced expiratory volume in 1 second")],
    ),
    (
        "balanced-trim-inside-a-square-region",
        "The report [Northwind Data Standards 2 (NDS(2))] took effect.",
        [("NDS(2)", "Northwind Data Standards 2")],
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
# _trim_span: the balanced-bracket restoration
# ---------------------------------------------------------------------------
# The trim strips trailing non-alphanumerics, then puts back exactly as much as
# it takes to close what it opened. Three properties matter and each is pinned
# below: it never reaches past the span it was given, it restores
# all-or-nothing, and it costs O(1) whatever it is handed.


@pytest.mark.parametrize(
    ("text", "start", "end", "expected"),
    [
        # The case the restoration exists for.
        ("FEV(1)", 0, 6, "FEV(1)"),
        ("a FEV(1) b", 2, 8, "FEV(1)"),
        # Nested, and both levels are restored.
        ("A((b))", 0, 6, "A((b))"),
        # A closing bracket that closes nothing is still stripped: the trim is
        # not "keep every bracket", it is "leave nothing open".
        ("A(b)c)", 0, 6, "A(b)c"),
        # Bracket kinds must agree before anything is restored.
        ("A(b]", 0, 4, "A(b"),
        # Nothing to restore, so nothing changes.
        ("...abc...", 0, 9, "abc"),
        ("RCT; n=42", 0, 9, "RCT; n=42"),
        ("((((((x))))))", 0, 13, "x"),
        ("(", 0, 1, ""),
    ],
)
def test_trim_span_leaves_no_bracket_open(text: str, start: int, end: int, expected: str) -> None:
    """The trimmed span is balanced, and is a slice of what was handed in."""
    trimmed_start, trimmed_end = _trim_span(text, start, end)
    assert text[trimmed_start:trimmed_end] == expected
    assert start <= trimmed_start <= trimmed_end <= end


def test_trim_span_restores_all_or_nothing() -> None:
    """A span that cannot be fully closed is left exactly as the plain trim made it.

    ``A((b)`` holds two openers and one closer, so closing it completely would
    need a character the text does not have. Restoring the one available closer
    would produce ``A((b)`` -- still unbalanced, and now a third string that is
    neither what the text says nor what the trim decided.
    """
    start, end = _trim_span("A((b)", 0, 5)
    assert "A((b)"[start:end] == "A((b"


@given(
    text=st.text(alphabet="ab()[]{}.,;: 12", max_size=40),
    lower=st.integers(min_value=0, max_value=40),
    span=st.integers(min_value=0, max_value=40),
)
@settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_trim_span_never_reaches_outside_its_input(text: str, lower: int, span: int) -> None:
    """The restoration may only give back characters this call removed.

    Widening a span is the one thing a *trim* is not supposed to do, and the
    span invariant every caller relies on -- ``text[span] == form`` -- stops
    holding the moment an offset escapes the region it was computed for.
    """
    start = min(lower, len(text))
    end = min(start + span, len(text))
    trimmed_start, trimmed_end = _trim_span(text, start, end)
    assert start <= trimmed_start <= trimmed_end <= end


# ---------------------------------------------------------------------------
# A long form may still begin with a function word
# ---------------------------------------------------------------------------
# Rejecting those was built and measured, and it lost. It is free on MED1250 --
# three predictions removed, none of them correct -- and asked again on two
# other corpora it deletes eleven predictions carrying a correct short-form
# span and three carrying a correct long-form span, because this library emits
# *pairs* and refusing a long form takes the short form standing beside it.
#
#   bench/results.json:
#     shortform.med1250_all.function_word_exposure
#     shortform.sdu22_ae_legal_dev.function_word_exposure
#     shortform.sdu22_ae_scientific_dev.function_word_exposure
#     shortform.plod_all.tight.high_precision.{baseline,function_word}
#   Reproduce with: python bench/run_shortform.py --variants --spans
#
# The tests below pin the behaviour that was kept, so the rule cannot be
# re-added without a failing test and a fresh measurement. Note what the rule
# would *not* have done: ``OMB`` should expand to ``Office of Management and
# Budget``, and rejecting ``of Management and Budget`` does not recover it --
# the correct span starts to the *left* of ``of``, and choosing a different
# long-form starting boundary is what D-008 built, measured and reverted.


@pytest.mark.parametrize(
    ("short_form", "long_form"),
    [
        ("OMB", "of Management and Budget"),
        ("ORM", "of Records Management"),
        ("TIA", "the Indonesian Armed Forces"),
        ("AA", "an adverb"),
    ],
)
def test_a_long_form_beginning_with_a_function_word_is_still_valid(
    short_form: str, long_form: str
) -> None:
    """``is_valid_long_form`` has no opinion about the first word's word class."""
    assert is_valid_long_form(short_form, long_form) is True


def test_a_truncated_institutional_long_form_is_still_reported(
    extractor: AbbreviationExtractor,
) -> None:
    """The defect is real and the output is deliberately unchanged.

    The pair is wrong -- the expansion should start at ``Office`` -- and it is
    reported anyway, because the only rule that removes it also removes a
    correct short-form span, and because removing it recovers nothing.
    """
    text = "The Northwind Office of Records Management (ORM) replied."
    assert pair_tuples(extractor.extract(text)) == [("ORM", "of Records Management")]


def test_the_same_shape_without_a_leading_preposition_is_correct(
    extractor: AbbreviationExtractor,
) -> None:
    """The control: nothing about institutional prose is broken in general."""
    text = "Northwind Data Standards (NDS) apply from January."
    assert pair_tuples(extractor.extract(text)) == [("NDS", "Northwind Data Standards")]


# ---------------------------------------------------------------------------
# The SF = LF legend arrangement, behind a default-off flag
# ---------------------------------------------------------------------------
# An abbreviation legend -- "GEF = Global Environment Facility" -- is a
# definition that no bracket introduces, so the whole S&H machinery walks past
# it. It is the largest single miss class on the newest corpus this repository
# reads, and it is also the surface of every equation and assignment, which is
# why it ships off.
#
#   bench/results.json:
#     shortform.med1250_{dev,test,all}.{high_precision,general,biomedical}.legend
#       -- bit-identical to .balanced_trim on every field, which is what shipped
#     shortform.med1250_all.legend_exposure{,_biomedical}
#       -- every separator in the corpus, gate by gate, and none survives
#     shortform.plod_{dev,test,all}.{tight,spaced}.high_precision.legend
#     shortform.sdu22_ae_{legal,scientific}_dev.high_precision.legend
#     shortform.{plod_*,sdu22_ae_*}.legend_exposure
#   Reproduce with: python bench/run_shortform.py --variants --spans --legend
#
# What the tests below pin is the *refusals*, in the same proportion the corpus
# does: three legends that must be read, and eleven surfaces that must not be.

#: ``(text, [(short, long), ...])`` -- legends that must be read.
_LEGEND_CASES = [
    (
        "Abbreviations: GEF = Global Environment Facility",
        [("GEF", "Global Environment Facility")],
    ),
    (
        "AOS = administrative and operational services; STS = support for technical services",
        [
            ("AOS", "administrative and operational services"),
            ("STS", "support for technical services"),
        ],
    ),
    (
        "TRAC = target for resource assignment from the core.",
        [("TRAC", "target for resource assignment from the core")],
    ),
    (
        "Here EPI = Echo planar imaging and NAA = N-acetyl-aspartate.",
        [("EPI", "Echo planar imaging"), ("NAA", "N-acetyl-aspartate")],
    ),
]

#: Surfaces that share the ``X = Y`` shape and are not definitions. Every one is
#: taken from a real corpus: the first eight from MED1250 abstracts, which carry
#: 401 separators and no legend at all, the last three from the SDU-22 miss dump
#: the audit published. A legend rule that fires on any of these is the
#: precision regression the whole arrangement is gated against.
_NOT_A_LEGEND = [
    "Cows (n = 523) assigned to treatment 1 were inseminated at 72 h.",
    "A P value of < or = 0.05 was considered significant.",
    "The timing was well correlated (r = 0.78) with peak ejection velocity.",
    "Two estrogen binding proteins (Mr = 50,000 and 65,000) were purified.",
    "The enzyme has a high affinity (Km Ca2+ = 0.5 microM) and is dependent.",
    "A risk factor for stroke in our cohort was reported, OR = 6.9, in men.",
    "Response rate = 90% among 710 worksites in the same communities.",
    "They are related by the equations Y1 = 1.074 X1 - 9.828 and Y2 = 1.22 X2.",
    "Tsat=Tamb [kPa] at the inlet of the compressor.",
    "where wC = carbon mass fraction of the fuel",
    "with xH2Oexhdry the water content of the exhaust",
]

#: Operator spellings that merely contain an ``=``.
_OPERATOR_SURFACES = [
    "The guard holds while ABC == DEF holds for the whole run.",
    "The bound is ABC <= DEF for every admissible input.",
    "It holds when ABC >= DEF over the sampled interval.",
    "The check fails if ABC != DEF at any point.",
    "Then ABC += DEF accumulates over the loop.",
    "In that dialect ABC := DEF binds the name.",
]


@pytest.fixture(scope="module")
def legend_extractor() -> AbbreviationExtractor:
    """An extractor with the legend arrangement asked for explicitly."""
    return AbbreviationExtractor(Config(), legend_syntax=True)


def legend_pairs(pairs: list[AcronymPair]) -> list[AcronymPair]:
    """Only the pairs the legend arrangement produced."""
    return [pair for pair in pairs if pair.pattern == "short=long"]


def bracketed_pairs(pairs: list[AcronymPair]) -> list[AcronymPair]:
    """Everything except what the legend arrangement produced."""
    return [pair for pair in pairs if pair.pattern != "short=long"]


@pytest.mark.parametrize(("text", "expected"), _LEGEND_CASES)
def test_a_legend_is_invisible_by_default(
    extractor: AbbreviationExtractor, text: str, expected: list[tuple[str, str]]
) -> None:
    """The shipped default reads brackets and nothing else.

    ``expected`` is unused on purpose: the point is that a document which the
    flagged extractor reads as a legend yields nothing at all without the flag.
    """
    assert extractor.extract(text) == []
    assert expected  # the same document is non-empty under the flag, below


@pytest.mark.parametrize(("text", "expected"), _LEGEND_CASES)
def test_a_legend_is_read_when_the_flag_is_set(
    legend_extractor: AbbreviationExtractor, text: str, expected: list[tuple[str, str]]
) -> None:
    """``SF = LF`` yields the pair, with exact spans and its own pattern."""
    pairs = legend_extractor.extract(text)
    assert pair_tuples(pairs) == expected
    assert [pair.pattern for pair in pairs] == ["short=long"] * len(expected)
    assert_spans_exact(text, pairs)


@pytest.mark.parametrize("text", _NOT_A_LEGEND + _OPERATOR_SURFACES)
def test_an_equation_is_not_a_legend(legend_extractor: AbbreviationExtractor, text: str) -> None:
    """The gate holds on the surfaces that share the shape.

    These are the reason the arrangement is flagged rather than shipped on, and
    they are asserted with the flag *on*: a rule that only holds while it is
    switched off is not a rule.
    """
    assert legend_pairs(legend_extractor.extract(text)) == []


def test_a_legend_entry_stops_before_the_next_one(
    legend_extractor: AbbreviationExtractor,
) -> None:
    """A second separator bounds the first entry's expansion.

    Without that stop, ``AOS`` reaches across the ``;`` and swallows ``STS``'s
    short form into its own long form -- and the alignment would accept it,
    because ``S`` matches ``STS``.
    """
    text = "AOS = administrative and operational services; STS = support for technical services"
    pairs = legend_extractor.extract(text)
    assert pair_tuples(pairs) == [
        ("AOS", "administrative and operational services"),
        ("STS", "support for technical services"),
    ]
    assert_spans_exact(text, pairs)


@pytest.mark.parametrize("separator", ["\n", "\r\n", "\r"])
def test_a_legend_does_not_cross_a_line_break(
    legend_extractor: AbbreviationExtractor, separator: str
) -> None:
    """A legend entry is a line; the expansion may not come from the next one."""
    text = f"GEF ={separator}Global Environment Facility"
    assert legend_pairs(legend_extractor.extract(text)) == []


def test_a_single_word_truncation_is_not_admitted(
    legend_extractor: AbbreviationExtractor,
) -> None:
    """``INT = interrupted`` is a real gold legend and is deliberately missed.

    The gate demands that every short-form character start a word, and a
    truncation of one word starts one word. Loosening it to the inside-a-word
    alignment ``find_best_long_form`` performs is exactly the reading under
    which ``Tsat=Tamb`` becomes a definition, so the miss is the price of the
    refusals above and is pinned here so that it is a decision rather than a
    surprise.
    """
    assert legend_pairs(legend_extractor.extract("INT = interrupted")) == []


def test_a_legend_whose_expansion_is_no_longer_than_the_short_form_is_refused(
    legend_extractor: AbbreviationExtractor,
) -> None:
    """``is_valid_long_form`` still applies, unchanged, to this arrangement."""
    assert legend_pairs(legend_extractor.extract("IS = is")) == []


def test_legend_pairs_are_interleaved_in_document_order(
    legend_extractor: AbbreviationExtractor,
) -> None:
    """A legend after a bracketed definition comes second, and vice versa."""
    text = (
        "The World Health Organization (WHO) reported. Also EPI = Echo planar imaging. "
        "The central nervous system (CNS) was imaged."
    )
    pairs = legend_extractor.extract(text)
    assert pair_tuples(pairs) == [
        ("WHO", "World Health Organization"),
        ("EPI", "Echo planar imaging"),
        ("CNS", "central nervous system"),
    ]
    anchors = [min(pair.short_form_span[0], pair.long_form_span[0]) for pair in pairs]
    assert anchors == sorted(anchors)
    assert_spans_exact(text, pairs)


@pytest.mark.parametrize("text", ALL_DOCUMENTS + [text for text, _ in _LEGEND_CASES])
def test_the_flag_only_ever_adds_pairs(
    extractor: AbbreviationExtractor, legend_extractor: AbbreviationExtractor, text: str
) -> None:
    """Turning the flag on adds candidates and re-ranks none.

    This is the load-bearing claim of the whole arrangement: it operates where
    D-012's pseudo-precision diagnosis does not bite, because it never competes
    with a bracketed reading. Strip the legend pairs back out and what is left
    must be, pair for pair and span for span, what the shipped default returns.
    """
    without = [pair.model_dump() for pair in extractor.extract(text)]
    with_flag = [pair.model_dump() for pair in bracketed_pairs(legend_extractor.extract(text))]
    assert with_flag == without


def test_the_flag_is_reported() -> None:
    """A caller can ask an extractor which arrangements it reads."""
    assert AbbreviationExtractor(Config()).legend_syntax is False
    assert AbbreviationExtractor(Config(), legend_syntax=True).legend_syntax is True


def test_the_engine_reaches_the_flag_by_injecting_an_extractor() -> None:
    """The documented opt-in route, end to end.

    The flag is a constructor argument rather than a ``Config`` field because it
    changes *which surfaces are scanned* rather than tuning the existing scan;
    the engine already accepts a collaborator, so that is the seam it uses.
    """
    from acronymkit import AcronymEngine

    config = Config()
    text = "Abbreviations: GEF = Global Environment Facility"
    assert AcronymEngine(config).extract_definitions(text) == []
    engine = AcronymEngine(config, extractor=AbbreviationExtractor(config, legend_syntax=True))
    assert [(pair.short_form, pair.long_form) for pair in engine.extract_definitions(text)] == [
        ("GEF", "Global Environment Facility")
    ]


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
    # Exclude the one input shape for which the templated definition provably
    # does NOT resolve, so that the property below is true rather than usually
    # true. Hypothesis found it as `("aaa aaa aaa (AAA)", "AAA")`.
    #
    # Schwartz & Hearst matches right to left and stops at the first alignment
    # whose leading character sits on a word boundary, so it returns the
    # *shortest* qualifying suffix -- here the final "aaa" rather than the whole
    # phrase. `is_valid_long_form` then rejects it for not being longer than the
    # abbreviation, and because the scan does not backtrack to a longer
    # alignment the pair is dropped outright.
    #
    # The exclusion is exact, not a guess. Any candidate spanning two or more
    # words contains a space in addition to the short form's letters, so it is
    # always longer than the short form and always survives the length filter.
    # Only a single-word candidate can be too short, and a single word carrying
    # the short form's letters in order is too short exactly when it *is* the
    # short form. So the drop happens if and only if the final word upper-cases
    # to the short form -- confirmed against 4,000 random three-letter-alphabet
    # documents, chosen to maximise collisions, with zero counterexamples.
    #
    # `test_a_long_form_whose_final_word_is_the_abbreviation_is_dropped` pins
    # the excluded behaviour, so this narrows the generator without hiding what
    # it stopped covering.
    assume(words[-1].upper() != short_form)
    lead = draw(st.sampled_from(_LEAD_INS))
    tail = draw(st.sampled_from(_TAIL_OUTS))
    return f"{lead}{long_form} ({short_form}){tail}", short_form


def test_a_long_form_whose_final_word_is_the_abbreviation_is_dropped() -> None:
    """The one shape ``_definition_documents`` excludes, pinned rather than hidden.

    "aaa aaa aaa (AAA)" is a legitimate definition that this extractor does not
    recover, and the reason is structural rather than a slip. Schwartz & Hearst
    scans right to left and stops at the first alignment beginning on a word
    boundary, so it proposes the final "aaa"; that candidate is not longer than
    "AAA", :func:`is_valid_long_form` rejects it, and nothing backtracks to the
    longer alignment that would have worked.

    Returning nothing is the better of the two available answers -- the
    alternative the greedy rule can reach is the truncated "aaa", and this
    project has measured repeatedly (D-011, D-012) that the rule's willingness
    to discard rather than over-extend is where its precision comes from.
    Fixing it means adding backtracking to the matcher, which is a change to
    the selection rule and would have to be measured against MED1250 before it
    could ship.

    This test exists so that a future change to any of that fails loudly here
    instead of quietly widening what the property test covers.
    """
    extractor = AbbreviationExtractor(Config())

    assert extractor.extract("aaa aaa aaa (AAA)") == []
    assert extractor.extract("aa aa (AA)") == []

    # One letter different in the final word and the same document resolves,
    # which is what makes this a boundary rather than a general failure.
    recovered = extractor.extract("aaa aaa aab (AAA)")
    assert [pair.short_form for pair in recovered] == ["AAA"]


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


@given(st.text(alphabet=_FUZZ_ALPHABET, max_size=140))
@settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_span_invariant_survives_bracket_soup_with_the_legend_flag(document: str) -> None:
    """The span invariant is unconditional under the flag too.

    ``_FUZZ_ALPHABET`` already carries ``=`` alongside the brackets, so this
    exercises separators nested inside, adjacent to and straddling bracket
    regions -- which is where a second scanner over the same text can most
    easily report an offset that does not slice back.
    """
    pairs = AbbreviationExtractor(Config(), legend_syntax=True).extract(document)
    assert_spans_exact(document, pairs)
    anchors = [min(pair.short_form_span[0], pair.long_form_span[0]) for pair in pairs]
    assert anchors == sorted(anchors)


@given(st.text(alphabet=_FUZZ_ALPHABET, max_size=140))
@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_the_flag_adds_pairs_to_arbitrary_input_and_removes_none(document: str) -> None:
    """The additive property, asserted against generated input rather than a list."""
    without = [pair.model_dump() for pair in AbbreviationExtractor(Config()).extract(document)]
    flagged = AbbreviationExtractor(Config(), legend_syntax=True).extract(document)
    assert [pair.model_dump() for pair in bracketed_pairs(flagged)] == without


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


def _extraction_seconds(document: str, repeats: int = 3, *, legend_syntax: bool = False) -> float:
    """Fastest of ``repeats`` extractions, to damp scheduler noise."""
    extractor = AbbreviationExtractor(Config(), legend_syntax=legend_syntax)
    best = float("inf")
    for _ in range(repeats):
        started = time.perf_counter()
        extractor.extract(document)
        best = min(best, time.perf_counter() - started)
    return best


def _separator_document(entries: int) -> str:
    """A document that is nothing but ``=`` in the shapes that must be refused.

    Each entry reaches the last gate before failing it, which is the expensive
    path: the left token is an admissible short form, a window follows, and
    every candidate prefix in that window is built and rejected.
    """
    return "Xy = 0.05 and Ab = 12,000 or Cd = -3 " * entries


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
def test_the_legend_scan_stays_sub_quadratic_across_a_doubling() -> None:
    """The same shape assertion for the separator scan, which is a second pass.

    A document dense in ``=`` is the pathological input for this arrangement:
    every separator builds a window and a run of candidate prefixes. Both are
    bounded by the same word and character budgets the backwards scan uses, so
    the cost is linear in the number of separators -- and the doubling is what
    says so rather than the docstring.
    """
    small = _extraction_seconds(_separator_document(4_000), legend_syntax=True)
    large = _extraction_seconds(_separator_document(8_000), legend_syntax=True)
    assert large < 3.0 * max(small, 0.01)
    assert (
        AbbreviationExtractor(Config(), legend_syntax=True).extract(_separator_document(50)) == []
    )


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
