"""Tests for ``bench/run_one_sense.py``.

Five of these are the deliverable rather than a check on it.

**The transcription must not drift.** ``term_shaped`` is the term half of
``bench.run_genre.roster_pair_admissible``, reused deliberately because that
rule was written by another workstream for another question *before* this one
was asked -- which is what stops it being a filter chosen after looking at the
output. A test drives both over one battery and asserts they agree, so a drift
in either turns the suite red rather than quietly re-defining the population.

**The occurrence rule must be the bounded one.** ``bench/run_monoculture.py``'s
``_occurrences`` is a bare substring search and finds ``CT`` inside ``fact``.
Every occurrence figure in this runner would be inflated by that. The test
asserts the two disagree on exactly that string, so a future edit that reaches
for the shared helper is caught.

**A case-folded key manufactures ambiguity.** ``ms``/``MS`` and ``N``/``n`` are
two short forms in biology's own case convention, not one short form with two
senses. A test builds that document and asserts the violation appears under the
folded key and not under the case-sensitive one -- which is the round's finding
expressed as a failing condition rather than a sentence.

**The nested-abbreviation pass must not import the ambiguity it is measuring.**
``expand_nested`` substitutes only short forms the document defines exactly
once. A test gives it a document where the nested short form is itself ambiguous
and asserts nothing is substituted.

**A2's arithmetic must be checkable by hand.** ``a2_record`` is driven over a
hand-built document whose licensed occurrences, floor, ceiling and
out-of-sentence count are all countable by eye, and every one is asserted.

Every assertion here was mutation-checked in place rather than assumed capable
of failing (R11): each was run once against a deliberately broken implementation
and observed red before being left green.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "bench" / "run_one_sense.py"

# A GUARD, NOT A LINE IN `EXPECTED_NON_PASSING`, for the reason
# tests/test_genre.py gives at the same place: the sdist ships `bench/` as a
# package directory and deliberately ships none of its modules, so the import
# below raises `ImportError` there and this file would fail to COLLECT. A
# `skipif` mark is consulted at collection and a module body runs at import, so
# the mark is too late.
if not RUNNER.is_file():  # pragma: no cover - installed/sdist runs only
    pytest.skip(
        "bench/run_one_sense.py is not part of an installed distribution",
        allow_module_level=True,
    )

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bench import run_genre as genre  # noqa: E402
from bench import run_monoculture as mono  # noqa: E402
from bench import run_one_sense as ons  # noqa: E402

#: A JATS document whose roster collides three ways: once on case alone
#: (``ms``/``MS``, a millisecond against multiple sclerosis), once on case alone
#: with a scope refinement (``N``/``n``), and once for real (``MHB`` twice, a
#: hyphenation variant). The first two are the shape that separates a
#: case-folded key from a case-sensitive one; the third survives both.
COLLIDING = """<?xml version="1.0"?>
<article>
  <front><article-meta><abstract>
    <p>Response times were recorded in ms and multiple sclerosis (MS) was excluded.</p>
  </abstract></article-meta></front>
  <body><sec><p>Cultures were grown in Mueller-Hinton broth (MHB) overnight.</p></sec></body>
  <back><glossary><def-list>
    <def-item><term>ms</term><def>millisecond</def></def-item>
    <def-item><term>MS</term><def>Multiple Sclerosis</def></def-item>
    <def-item><term>N</term><def>Number of patients</def></def-item>
    <def-item><term>n</term><def>Number of patients in a subgroup</def></def-item>
    <def-item><term>MHB</term><def>Mueller hinton broth</def></def-item>
    <def-item><term>MHB</term><def>Mueller-Hinton broth</def></def-item>
  </def-list></glossary></back>
</article>
"""


def _colliding_article() -> genre.Article:
    """The fixture, parsed through ``run_genre``'s own reader."""
    article = genre.parse_article(999, COLLIDING.encode("utf-8"), "CC BY")
    assert article is not None
    return article


# ---------------------------------------------------------------------------
# The transcription pin
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "term",
    [
        "MRI",
        "CT",
        "i.e",
        "e.g",
        "p",
        "A",
        "set",
        "site",
        "Fig",
        "ms",
        "MS",
        "HD-sEMG",
        "95",
        "a term with whitespace",
        "ABCDEFGHIJKLMNOPQ",
        "",
    ],
)
def test_term_shaped_agrees_with_the_roster_rule_it_transcribes(term: str) -> None:
    """The filter is somebody else's rule, and this is what keeps it so.

    ``roster_pair_admissible`` takes a definition too, so a definition that
    passes every condition on its own half is supplied. Any disagreement means
    the population this runner reports on has silently stopped being the
    population that rule admits.
    """
    definition = "an expansion long enough to pass every condition on its own half"
    assert ons.term_shaped(term) is genre.roster_pair_admissible(term, definition)


def test_term_shaped_refuses_the_discourse_markers_the_extractor_keys() -> None:
    """The four keys that would otherwise dominate the `distinct` class."""
    for marker in ("i.e", "e.g", "p", "d"):
        assert ons.term_shaped(marker) is False


# ---------------------------------------------------------------------------
# The occurrence rule
# ---------------------------------------------------------------------------
def test_bounded_occurrences_refuses_the_substring_the_shared_helper_accepts() -> None:
    """``CT`` inside ``PCT`` is the whole reason this runner has its own counter.

    The shared helper is case-sensitive, so ``fact`` does not fool it and a
    lowercase example would prove nothing. ``PCT`` does, and a real roster
    carries both ``CT`` and ``PCT`` often enough that this is not a contrived
    string.
    """
    text = "The PCT value rose while the CT scan and a second CT scan were unremarkable."
    assert len(mono._occurrences(text, "CT")) == 3
    assert len(ons.bounded_occurrences(text, "CT")) == 2


def test_bounded_occurrences_handles_a_short_form_carrying_punctuation() -> None:
    """``HD-sEMG`` and ``95% CI`` are real roster terms and must not blow up a regex."""
    text = "HD-sEMG traces and the 95% CI were reported; HD-sEMG again."
    assert len(ons.bounded_occurrences(text, "HD-sEMG")) == 2
    assert len(ons.bounded_occurrences(text, "95% CI")) == 1


# ---------------------------------------------------------------------------
# The surface-variant ladder
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("expansions", "expected"),
    [
        (["Mueller hinton broth", "Mueller-Hinton broth"], "surface"),
        (["deep learning", "deep-learning"], "surface"),
        (["Non-metric multidimensional scaling", "nonmetric multidimensional scaling"], "surface"),
        (["Region of Convergence", "Regions of Convergence"], "surface"),
        (["density of state", "density of states"], "surface"),
        (
            ["water vapor transmission rate", "water vapor transmission rate permeability"],
            "refinement",
        ),
        (["Number of patients", "Number of patients in a subgroup"], "refinement"),
        (["standard deviation", "swelling degree"], "distinct"),
        (["IFN-stimulated response element", "internal ribosome entry site"], "distinct"),
        (["Federal Licensing Exam", "Federal Licensing Examination"], "distinct"),
    ],
)
def test_the_ladder_puts_each_shape_in_the_class_it_belongs_to(
    expansions: list, expected: str
) -> None:
    """The three classes, one example each way, including the ones it must NOT fold.

    ``Exam``/``Examination`` is in the list on purpose: it is one concept and
    the ladder calls it ``distinct``, because a stemmer aggressive enough to
    fold it would also fold ``microscope`` into ``microscopy``. The class is
    named ``distinct`` rather than ``genuine`` for exactly this reason.
    """
    assert ons.classify_group(expansions, {}) == expected


def test_the_ladder_is_indifferent_to_the_order_it_is_given() -> None:
    """A class that depended on first-seen order would be a bug nobody could see."""
    forms = ["Chromatin Immunoprecipitation", "Chromatin immuno-precipitation"]
    assert ons.classify_group(forms, {}) == ons.classify_group(list(reversed(forms)), {})


def test_nested_expansion_folds_a_nested_abbreviation_and_only_an_unambiguous_one() -> None:
    """One pass, and never through a short form the document itself collides.

    Substituting an ambiguous nested short form would import the very ambiguity
    under test into the classifier that is supposed to measure it.
    """
    unambiguous = {"CT": "computed tomography"}
    assert ons.classify_group(["cone-beam CT", "cone-beam computed tomography"], unambiguous) == (
        "surface"
    )
    assert ons.classify_group(["cone-beam CT", "cone-beam computed tomography"], {}) == "distinct"
    assert ons.expand_nested("cone-beam CT", {}) == "cone-beam CT"


# ---------------------------------------------------------------------------
# The keying, which is a finding
# ---------------------------------------------------------------------------
def test_a_case_folded_key_manufactures_a_violation_the_document_does_not_carry() -> None:
    """``ms``/``MS`` and ``N``/``n`` are two short forms, not one with two senses.

    The raw roster of the fixture carries three collisions under a folded key
    and one under a case-sensitive key. The two that disappear are the two that
    biology's own case convention distinguishes.
    """
    pairs = ons.raw_roster(999) or [
        ("ms", "millisecond"),
        ("MS", "Multiple Sclerosis"),
        ("N", "Number of patients"),
        ("n", "Number of patients in a subgroup"),
        ("MHB", "Mueller hinton broth"),
        ("MHB", "Mueller-Hinton broth"),
    ]
    folded = ons.group_pairs(pairs, fold_key=True)
    exact = ons.group_pairs(pairs, fold_key=False)
    assert sum(1 for forms in folded.values() if len(forms) > 1) == 3
    assert sum(1 for forms in exact.values() if len(forms) > 1) == 1


def test_the_roster_admission_rule_suppresses_two_of_the_three_folded_collisions() -> None:
    """The rule this runner reuses was built to measure something else.

    ``ms`` and ``n`` carry no capital, so ``roster_pair_admissible`` refuses
    them, and with them go the millisecond/multiple-sclerosis collision and the
    subgroup refinement. Measuring the rule through itself would have missed
    this entirely, which is why :func:`bench.run_one_sense.raw_roster` exists.
    """
    article = _colliding_article()
    raw = [
        ("ms", "millisecond"),
        ("MS", "Multiple Sclerosis"),
        ("N", "Number of patients"),
        ("n", "Number of patients in a subgroup"),
        ("MHB", "Mueller hinton broth"),
        ("MHB", "Mueller-Hinton broth"),
    ]
    admitted_folded = ons.group_pairs(article.roster, fold_key=True)
    raw_folded = ons.group_pairs(raw, fold_key=True)
    assert sum(1 for forms in raw_folded.values() if len(forms) > 1) == 3
    assert sum(1 for forms in admitted_folded.values() if len(forms) > 1) == 1


def test_the_roster_record_counts_the_fixture_the_way_the_grouping_does() -> None:
    """The record is the grouping plus arithmetic, and the arithmetic is checked."""
    article = _colliding_article()
    record = ons.roster_record([article], fold_key=False, admitted=True, context={})
    assert record["articles_with_a_roster"] == 1
    assert record["groups_with_two_or_more_expansions"] == 1
    assert record["class_surface"] == 1
    assert record["class_distinct"] == 0
    assert record["violations"][0]["short_form"] == "MHB"


# ---------------------------------------------------------------------------
# Sentence spans
# ---------------------------------------------------------------------------
def test_enclosing_sentence_finds_the_containing_span_and_refuses_a_gap() -> None:
    """Binary search over ordered spans, including an offset that falls between two."""
    spans = [(0, 10), (12, 20), (25, 30)]
    assert ons.enclosing_sentence(spans, 0) == (0, 10)
    assert ons.enclosing_sentence(spans, 9) == (0, 10)
    assert ons.enclosing_sentence(spans, 11) is None
    assert ons.enclosing_sentence(spans, 19) == (12, 20)
    assert ons.enclosing_sentence(spans, 24) is None
    assert ons.enclosing_sentence(spans, 40) is None
    assert ons.enclosing_sentence([], 3) is None


def test_turning_sentence_capture_on_changes_no_pair() -> None:
    """The substitution's other half: the coverage figure must be about the shipped pairs.

    ``resolver_groups`` runs the engine WITHOUT capture and takes sentences from
    a cached table instead. That is only legitimate if capture would not have
    changed which pairs exist, so the equality is asserted rather than assumed.
    """
    from acronymkit import AcronymEngine, Config
    from acronymkit.enums import ExtractionProfile

    text = (
        "We measured the standard deviation (SD) of the sample. Later the SD was large. "
        "The swelling degree (SD) was also measured. Magnetic resonance imaging (MRI) followed."
    )
    config = Config.for_profile(ExtractionProfile.BIOMEDICAL)
    plain = [(p.short_form, p.long_form) for p in AcronymEngine(config).extract_definitions(text)]
    capturing = AcronymEngine(config.model_copy(update={"extraction_capture_sentences": True}))
    with_capture = [(p.short_form, p.long_form) for p in capturing.extract_definitions(text)]
    assert plain == with_capture
    assert ("SD", "standard deviation") in plain
    assert ("SD", "swelling degree") in plain


# ---------------------------------------------------------------------------
# A2's arithmetic, countable by eye
# ---------------------------------------------------------------------------
#: The sentences of the hand-built document, in order. Spans are derived from
#: their lengths rather than written down, so the arithmetic below cannot drift
#: when a word is edited.
_SENTENCES = (
    "Earlier work used SD widely. ",
    "The standard deviation (SD) was small. ",
    "Later the SD rose. ",
    "The swelling degree (SD) was measured. ",
    "That SD differed. ",
    "Magnetic resonance imaging (MRI) followed. ",
    "The MRI was clear.",
)


def _hand_built_document() -> ons.DocumentGroups:
    """One document with one ambiguous short form and one unambiguous one.

    ``SD`` is defined twice -- ``standard deviation`` at the first site and
    ``swelling degree`` at the second -- and occurs **five** times, one of them
    in the opening sentence **before** either definition. That first occurrence
    is the one that separates *license every occurrence* from *license every
    occurrence at or after the first definition*, and a fixture without it lets
    the two models agree. ``MRI`` is defined once and occurs twice.
    """
    text = "".join(_SENTENCES)
    spans = []
    cursor = 0
    for sentence in _SENTENCES:
        spans.append((cursor, cursor + len(sentence)))
        cursor += len(sentence)
    first_sd = text.index("(SD)") + 1
    second_sd = text.index("(SD)", first_sd + 1) + 1
    groups = {
        "SD": [
            ons.Definition("SD", "standard deviation", first_sd, spans[1]),
            ons.Definition("SD", "swelling degree", second_sd, spans[3]),
        ],
        "MRI": [
            ons.Definition("MRI", "Magnetic resonance imaging", text.index("(MRI)") + 1, spans[5]),
        ],
    }
    return ons.DocumentGroups(1, text, groups)


def test_a2_licenses_nothing_before_the_first_definition() -> None:
    """The opening ``SD`` is in the document and is not licensed, and that is the model.

    Seven whole-token occurrences exist; six are at or after a definition of
    their own short form. A model that licensed all seven would be licensing an
    occurrence no definition had yet been seen for, which is not what A2 claims.
    """
    document = _hand_built_document()
    every = len(ons.bounded_occurrences(document.text, "SD")) + len(
        ons.bounded_occurrences(document.text, "MRI")
    )
    record = ons.a2_record([document], "biomedical", {})
    assert every == 7
    assert record["licensed_occurrences"] == 6


def test_a_short_form_the_document_collides_is_not_offered_as_a_nested_expansion() -> None:
    """``unambiguous()`` is the filter that stops the ladder importing the ambiguity.

    Without it, ``expand_nested`` would rewrite a long form containing ``SD``
    using one of ``SD``'s two competing expansions -- resolving an ambiguity by
    picking a side, inside the classifier that exists to count ambiguities.
    """
    document = _hand_built_document()
    unambiguous = document.unambiguous()
    assert "SD" not in unambiguous
    assert unambiguous["MRI"] == "Magnetic resonance imaging"


def test_a2_prices_both_sides_of_the_trade_on_a_document_countable_by_eye() -> None:
    """Licensed occurrences, the coverage A2 buys, and the two error bounds.

    ``SD`` occurs four times, all at or after its first definition; ``MRI``
    twice. Six licensed occurrences. Three of them sit inside a definition
    sentence -- the two definition sites for ``SD`` and the one for ``MRI`` --
    so three are new coverage. ``SD`` is ``distinct``: its floor is the one
    definition site A2 did not commit to, and its ceiling is three of its four.
    """
    record = ons.a2_record([_hand_built_document()], "biomedical", {})
    assert record["licensed_occurrences"] == 6
    assert record["licensed_occurrences_inside_a_definition_sentence"] == 3
    assert record["licensed_occurrences_outside_every_definition_sentence"] == 3
    assert record["groups_unambiguous"] == 1
    assert record["groups_distinct"] == 1
    assert record["licensed_occurrences_distinct"] == 4
    assert record["wrong_floor_distinct"] == 1
    assert record["wrong_ceiling_distinct"] == 3
    assert ("wrong_floor_unambiguous" in record) is False


def test_a2_attributes_no_error_at_all_to_an_unambiguous_group() -> None:
    """The class that carries most of the corpus must contribute nothing to either bound.

    A2 introduces no error where the document defines a short form once. If this
    ever fails, the error bounds are counting the extractor's own mistakes as
    A2's, which is the one confusion that would make the whole record unreadable.
    """
    record = ons.a2_record([_hand_built_document()], "biomedical", {})
    correctness_floor = record["wrong_floor_distinct"] + record["wrong_floor_refinement"]
    assert record["licensed_occurrences_unambiguous"] == 2
    assert correctness_floor == 1
    assert record["wrong_floor_surface"] == 0


# ---------------------------------------------------------------------------
# The adjudication table
# ---------------------------------------------------------------------------
def test_every_hand_label_uses_the_closed_vocabulary() -> None:
    """A typo in a label would silently vanish from every reported count."""
    assert set(ons.AUDIT_LABELS.values()) <= set(ons.AUDIT_LABEL_VOCABULARY)


def test_the_audit_draw_is_seeded_and_stable() -> None:
    """Two draws over the same frame are the same draw, and the frame is sorted first."""
    frame = [(index, f"S{index}") for index in range(500)]
    first = ons.audit_sample(frame, 120, 0)
    second = ons.audit_sample(list(reversed(frame)), 120, 0)
    assert first == second
    assert len(first) == 120


def test_the_three_class_draws_do_not_share_a_shuffle() -> None:
    """A shared shuffle would draw the same positions from three different frames.

    Sampling ``surface``, ``refinement`` and ``distinct`` at the same seed would
    make the three samples correlated in a way nobody could reason about, so
    each class carries a salt. The salts are distinct and the draws differ.
    """
    frame = [(index, f"S{index}") for index in range(500)]
    salts = ons.AUDIT_CLASS_SALT
    assert len(set(salts.values())) == len(salts)
    draws = [tuple(ons.audit_sample(frame, 40, salt)) for salt in salts.values()]
    assert len(set(draws)) == len(draws)


def test_every_class_the_ladder_can_emit_has_a_sample_size_and_a_salt() -> None:
    """A class with no sample is a class nobody adjudicated, and it must not be silent."""
    emitted = {"surface", "refinement", "distinct"}
    assert set(ons.AUDIT_SAMPLE_SIZES) == emitted
    assert set(ons.AUDIT_CLASS_SALT) == emitted


# ---------------------------------------------------------------------------
# The interval, pinned against published values
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("successes", "trials", "low", "high"),
    [
        (2, 10, 2.52, 55.61),
        (0, 10, 0.00, 30.85),
        (10, 10, 69.15, 100.00),
        (1, 40, 0.06, 13.16),
        (0, 40, 0.00, 8.81),
    ],
)
def test_the_exact_binomial_interval_reproduces_published_values(
    successes: int, trials: int, low: float, high: float
) -> None:
    """A hand-rolled Clopper-Pearson has to be checked against somebody else's arithmetic.

    This package carries no numerical dependency, so the interval is bisection
    on a binomial tail written out in the runner. The five rows are the standard
    worked examples, including both degenerate ends, and they are the only thing
    standing between a published interval and a plausible-looking one.
    """
    computed_low, computed_high = ons.clopper_pearson(successes, trials)
    assert round(100 * computed_low, 2) == pytest.approx(low, abs=0.01)
    assert round(100 * computed_high, 2) == pytest.approx(high, abs=0.01)


def test_the_interval_is_defined_for_an_empty_draw() -> None:
    """A class whose frame is empty must not divide by it."""
    assert ons.clopper_pearson(0, 0) == (0.0, 0.0)
