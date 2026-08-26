"""Tests for ``bench/run_genre.py``.

Three of these are the deliverable rather than a check on it.

**The gold's independence from Schwartz & Hearst is a claim about construction,
and a claim about construction is worth nothing asserted.** ``run_genre``'s gold
comes from each article's own ``<def-list>`` and is admitted by
:func:`bench.run_genre.roster_pair_admissible`, which compares no character of
the term against the definition. That is stated as a falsifiable property and
tested as one: a roster row whose term shares **no character** with its own
definition is admitted, and ``sh_alignable`` refuses the same row. If the first
assertion ever fails, the gold has acquired the blind spot it exists to measure.

**The arbiter must be outside both measured halves.** The roster lives in
``<back>``; the halves are ``<abstract>`` and ``<body>``. A test drives a
document whose ``<back>`` holds a sentence that appears nowhere else and asserts
that neither half contains it.

**The interval must be paired.** :func:`bench.run_genre.cluster_bootstrap` is
given two halves that agree article for article; a paired resample can only ever
produce a difference of zero, and an implementation that resampled the two
halves independently would produce a wide interval. The test asserts the
interval is exactly zero-wide, which is the one arrangement that separates the
two implementations.

Every assertion here was mutation-checked in place rather than assumed capable
of failing (R11): each was run once against a deliberately broken implementation
and observed red before being left green.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "bench" / "run_genre.py"

# A GUARD, NOT A LINE IN `EXPECTED_NON_PASSING`, for the reason
# tests/test_monoculture.py gives at the same place: the sdist ships `bench/` as
# a package directory and deliberately ships none of its modules, so the import
# below raises `ImportError` there and this file would fail to COLLECT. A
# `skipif` mark is consulted at collection and a module body runs at import, so
# the mark is too late. The condition named is exactly the one that differs, so
# any other error in this file still reaches the job.
if not RUNNER.is_file():  # pragma: no cover - installed/sdist runs only
    pytest.skip(
        "bench/run_genre.py is not part of an installed distribution",
        allow_module_level=True,
    )

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bench import run_genre as genre  # noqa: E402
from bench import run_monoculture as mono  # noqa: E402

#: A JATS document with one of everything this runner has to get right: a
#: sub-article that must not be read, a citation whose brackets must not survive,
#: a figure caption and a table footnote inside the body, a roster in `<back>`
#: that must not appear in either half, and a `<def-list>` inside the body that
#: must be counted and not believed.
FIXTURE = """<?xml version="1.0"?>
<article xmlns:ali="http://www.niso.org/schemas/ali/1.0/">
  <front>
    <article-meta>
      <permissions>
        <license><ali:license_ref>https://creativecommons.org/licenses/by/4.0/</ali:license_ref></license>
      </permissions>
      <abstract>
        <p>We measured magnetic resonance imaging (MRI) in every subject.</p>
      </abstract>
    </article-meta>
  </front>
  <body>
    <sec>
      <title>Introduction</title>
      <p>Earlier work showed this [<xref ref-type="bibr">12</xref>].</p>
      <p>The Bureau of Weights, hereinafter QQQ, supplied the standard.</p>
    </sec>
    <fig><caption><p>EPI = Echo planar imaging.</p></caption></fig>
    <table-wrap>
      <table><tbody><tr><td>alpha</td><td>beta</td></tr></tbody></table>
      <table-wrap-foot><p>BMI: body mass index; CE: cholesteryl ester</p></table-wrap-foot>
    </table-wrap>
    <def-list><def-item><term>ZZZ</term><def>a roster inside the body</def></def-item></def-list>
  </body>
  <back>
    <glossary>
      <title>Abbreviations</title>
      <def-list>
        <def-item><term>MRI</term><def>Magnetic resonance imaging</def></def-item>
        <def-item><term>QQQ</term><def>Bureau of Weights</def></def-item>
        <def-item><term>CT</term><def>Computed tomography</def></def-item>
      </def-list>
    </glossary>
    <ack><p>Sequestered acknowledgement sentence.</p></ack>
  </back>
  <sub-article>
    <body><p>A peer review report mentioning positron emission tomography (PET).</p></body>
  </sub-article>
</article>
"""


def _fixture_article() -> genre.Article:
    """The fixture, parsed."""
    article = genre.parse_article(1, FIXTURE.encode("utf-8"), "CC BY")
    assert article is not None
    return article


# ---------------------------------------------------------------------------
# The gold's independence from the Schwartz & Hearst alignment
# ---------------------------------------------------------------------------
def test_roster_admits_a_pair_sharing_no_character_with_its_own_term() -> None:
    """The property the whole gold rests on, stated so it can fail.

    ``QQQ`` shares no character with ``Bureau of Weights``. The Schwartz &
    Hearst validator refuses it. This gold admits it, because it never looks.
    """
    assert genre.roster_pair_admissible("QQQ", "Bureau of Weights") is True
    assert mono.sh_alignable("QQQ", "Bureau of Weights") is False


def test_roster_admission_is_a_property_of_each_string_separately() -> None:
    """Reordering or rewriting the definition never changes the term's verdict."""
    for definition in ("Bureau of Weights", "Weights of Bureau", "quantum quark quench"):
        assert genre.roster_pair_admissible("QQQ", definition) is True


@pytest.mark.parametrize(
    ("term", "definition"),
    [
        ("a", "too short a term"),
        ("magnetic resonance", "a term with whitespace is a phrase"),
        ("1234", "a term with no letter"),
        ("mri", "a term with no upper case"),
        ("MRI", "no"),
        ("MRI", "x" * 200),
        ("MRI", "12345"),
        ("MRI", "mri"),
    ],
)
def test_roster_refuses_rows_that_are_not_abbreviation_entries(term: str, definition: str) -> None:
    """Each refusal is one condition, and none of them reads both strings at once."""
    assert genre.roster_pair_admissible(term, definition) is False


# ---------------------------------------------------------------------------
# The arbiter is outside both halves
# ---------------------------------------------------------------------------
def test_the_roster_is_read_from_back_and_appears_in_neither_half() -> None:
    """``<back>`` is the arbiter, so it must not be part of what is measured."""
    article = _fixture_article()
    assert ("MRI", "Magnetic resonance imaging") in article.roster
    assert ("QQQ", "Bureau of Weights") in article.roster
    assert "Magnetic resonance imaging" not in article.body
    assert "Sequestered acknowledgement sentence" not in article.abstract
    assert "Sequestered acknowledgement sentence" not in article.body


def test_a_def_list_inside_the_body_is_counted_and_not_believed() -> None:
    """A roster in the body would put the arbiter inside the measured text."""
    article = _fixture_article()
    assert article.roster_in_body == 1
    assert all(short != "ZZZ" for short, _ in article.roster)


def test_a_sub_article_contributes_to_neither_half() -> None:
    """Peer review reports are deposited as ``<sub-article>`` and are not the article."""
    article = _fixture_article()
    assert "positron emission tomography" not in article.body
    assert "positron emission tomography" not in article.abstract


def test_the_body_half_keeps_figure_captions_and_table_footnotes() -> None:
    """The class under test lives there, so dropping them would answer the question."""
    article = _fixture_article()
    assert "EPI = Echo planar imaging" in article.body
    assert "BMI: body mass index" in article.body


# ---------------------------------------------------------------------------
# The citation sweep, which rewrites the characters the measurement is about
# ---------------------------------------------------------------------------
def test_citation_brackets_are_removed_and_the_removal_is_counted() -> None:
    """A body cites and an abstract does not, so a surviving ``[12]`` is a thumb on the scale."""
    article = _fixture_article()
    assert "[12]" not in article.body
    assert "[]" not in article.body
    assert "Earlier work showed this" in article.body
    assert article.empty_brackets_removed["body"] >= 1


def test_render_reports_its_own_firing_count() -> None:
    """R12: a cleaner that acts silently cannot be weighed."""
    import xml.etree.ElementTree as ET

    element = ET.fromstring("<p>one [<xref>1</xref>] two [<xref>2</xref>] three</p>")
    text, removed = genre.render(element)
    assert removed == 2
    assert "one" in text and "three" in text


# ---------------------------------------------------------------------------
# The three halves
# ---------------------------------------------------------------------------
def test_body_matched_is_a_contiguous_body_window_of_the_abstract_s_length() -> None:
    """The length control has to be a real slice of the real body, or it controls nothing."""
    import random

    article = _fixture_article()
    window = article.half("body_matched", random.Random(0))
    assert window in article.body
    assert len(window) == min(len(article.abstract), len(article.body))


def test_an_unknown_half_is_refused() -> None:
    import random

    with pytest.raises(ValueError):
        _fixture_article().half("references", random.Random(0))


def test_a_declared_pair_is_gold_only_about_the_half_that_spells_it_out() -> None:
    """``CT`` is declared and never written out, so it is gold about neither half."""
    article = _fixture_article()
    abstract = genre.passages_for([article], "abstract")[0]
    body = genre.passages_for([article], "body")[0]
    assert ("MRI", "Magnetic resonance imaging") in abstract.gold_pairs
    assert ("QQQ", "Bureau of Weights") in body.gold_pairs
    assert all(short != "CT" for short, _ in abstract.gold_pairs + body.gold_pairs)


def test_the_case_fold_is_a_transcription_that_has_not_drifted() -> None:
    """Where case already agrees, the folded locator must be ``run_monoculture``'s.

    The alternative to a transcription is an import of a private name; the
    alternative to this test is a transcription that quietly stops agreeing.
    """
    text = "We used magnetic resonance imaging (MRI) throughout the study."
    assert genre.locate_pair_folded(text, "MRI", "magnetic resonance imaging") == mono.locate_pair(
        text, "MRI", "magnetic resonance imaging"
    )
    assert genre._occurrences(text, "MRI", fold=False) == [(36, 39)]


def test_the_case_fold_recovers_a_roster_definition_the_body_writes_in_lower_case() -> None:
    """The reason the fold exists, as a case rather than as a paragraph.

    An author's glossary is typed in sentence case and the body writes the same
    phrase mid-sentence in lower case. A case-sensitive search drops the pair,
    and it drops more of them in one half than the other -- a genre-correlated
    artefact inside the contrast under test.
    """
    text = "We used magnetic resonance imaging (MRI) throughout."
    assert mono.locate_pair(text, "MRI", "Magnetic resonance imaging") is None
    assert genre.locate_pair_folded(text, "MRI", "Magnetic resonance imaging") is not None


def test_the_short_form_half_of_a_pair_is_not_folded() -> None:
    """Folding it too would let ``CT`` match inside ``fact``, on a substring search."""
    text = "The fact is that computed tomography was unavailable."
    assert genre.locate_pair_folded(text, "CT", "computed tomography") is None


def test_gold_spans_line_up_with_the_pairs_they_came_from() -> None:
    """One located pair, one short span, one long span, in the same order.

    The long-form span carries **the text's** casing and not the roster's, which
    is the point of the fold and is what every downstream bracket-adjacency and
    span-overlap measurement needs: a span has to index the half it was found
    in, or ``bracket_adjacent`` would be reading the wrong characters.
    """
    passage = genre.passages_for([_fixture_article()], "abstract")[0]
    assert passage.gold_pairs
    assert len(passage.gold_pairs) == len(passage.gold_short) == len(passage.gold_long)
    for (short, long_form), short_span, long_span in zip(
        passage.gold_pairs, passage.gold_short, passage.gold_long
    ):
        assert passage.surface(short_span) == short
        assert passage.surface(long_span).casefold() == long_form.casefold()
        assert passage.text[long_span[0] : long_span[1]] == passage.surface(long_span)


def test_an_article_with_no_body_is_not_a_same_article_contrast() -> None:
    document = (
        "<article><front><article-meta><abstract><p>Only an abstract.</p>"
        "</abstract></article-meta></front></article>"
    )
    assert genre.parse_article(1, document.encode("utf-8"), "CC BY") is None


# ---------------------------------------------------------------------------
# The interval
# ---------------------------------------------------------------------------
def test_the_bootstrap_is_paired_over_articles() -> None:
    """The one arrangement that separates a paired resample from an unpaired one.

    Both halves agree article for article, so every paired replicate has a
    difference of exactly zero. An implementation that drew its two resamples
    independently would sometimes pick the all-ones article for one half and the
    all-zeros article for the other, and would report a wide interval.
    """
    rows = [(1.0, 1.0), (0.0, 1.0)] * 20
    record = genre.cluster_bootstrap(rows, list(rows), replicates=200)
    assert record["difference_pct"] == 0.0
    assert record["difference_ci_low_pct"] == 0.0
    assert record["difference_ci_high_pct"] == 0.0
    assert record["ci_excludes_zero"] is False


def test_the_bootstrap_finds_a_real_difference() -> None:
    left = [(1.0, 1.0)] * 40
    right = [(0.0, 1.0)] * 40
    record = genre.cluster_bootstrap(left, right, replicates=200)
    assert record["difference_pct"] == 100.0
    assert record["ci_excludes_zero"] is True


def test_the_bootstrap_reports_how_many_articles_carry_evidence() -> None:
    """R12 again: an interval over a denominator of nothing is not a null result."""
    left = [(0.0, 0.0)] * 5 + [(1.0, 2.0)] * 5
    record = genre.cluster_bootstrap(left, [(1.0, 4.0)] * 10, replicates=100)
    assert record["articles"] == 10
    assert record["articles_with_evidence_left"] == 5
    assert record["articles_with_evidence_right"] == 10


def test_the_bootstrap_refuses_unpaired_input() -> None:
    with pytest.raises(ValueError):
        genre.cluster_bootstrap([(1.0, 1.0)], [(1.0, 1.0), (0.0, 1.0)])


def test_the_verdict_reads_both_headline_comparisons() -> None:
    """A verdict that could be read either way is not a verdict."""
    genre_shaped = {
        "abstract_minus_body.bracket_adjacency_of_located_gold_long_forms": {
            "difference_pct": 20.0,
            "ci_excludes_zero": True,
        },
        "abstract_minus_body.independent_gain_on_proposal_edges": {
            "difference_pct": -20.0,
            "ci_excludes_zero": True,
        },
    }
    assert genre.verdict(genre_shaped) == "genre"
    flat = {
        "abstract_minus_body.bracket_adjacency_of_located_gold_long_forms": {
            "difference_pct": 1.0,
            "ci_excludes_zero": False,
        },
        "abstract_minus_body.independent_gain_on_proposal_edges": {
            "difference_pct": -1.0,
            "ci_excludes_zero": False,
        },
    }
    assert genre.verdict(flat) == "provenance-back-in-play"
    half = dict(genre_shaped)
    half["abstract_minus_body.bracket_adjacency_of_located_gold_long_forms"] = {
        "difference_pct": 5.0,
        "ci_excludes_zero": False,
    }
    assert genre.verdict(half) == "split"


# ---------------------------------------------------------------------------
# The licence filter, and the draw it was measured on
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("meta", "expected"),
    [
        (None, "(no such article version)"),
        ({"is_pmc_openaccess": False, "license_code": "CC BY"}, "(not in the open-access subset)"),
        ({"is_pmc_openaccess": True, "is_retracted": True, "license_code": "CC BY"}, "(retracted)"),
        (
            {"is_pmc_openaccess": True, "is_historical_ocr": True, "license_code": "CC0"},
            "(historical OCR)",
        ),
        ({"is_pmc_openaccess": True}, "(no licence code)"),
        ({"is_pmc_openaccess": True, "license_code": "CC BY-ND"}, "CC BY-ND"),
        ({"is_pmc_openaccess": True, "license_code": "CC BY"}, "CC BY"),
    ],
)
def test_licence_verdict_buckets_every_probe(meta: object, expected: str) -> None:
    assert genre.licence_verdict(meta) == expected  # type: ignore[arg-type]


def test_only_two_licence_codes_are_admitted() -> None:
    """ND, NC, SA and text-mining-only grants are all refused, one by one."""
    for code in ("CC BY-NC", "CC BY-NC-ND", "CC BY-NC-SA", "CC BY-ND", "TDM"):
        assert code not in genre.PERMISSIVE_LICENCE_CODES
    assert set(genre.PERMISSIVE_LICENCE_CODES) == {"CC BY", "CC0"}


def test_the_recorded_licence_census_adds_up_to_its_own_probe_count() -> None:
    """A hand-transcribed constant with no internal check is a typo waiting to be quoted."""
    assert sum(genre.DRAW_CENSUS.values()) == genre.DRAW_PROBES


def test_the_recorded_census_contains_at_least_one_non_permissive_licence() -> None:
    """The finding is that filtering is required; if it ever were not, this fails."""
    non_permissive = {
        label: count
        for label, count in genre.DRAW_CENSUS.items()
        if not label.startswith("(") and label not in genre.PERMISSIVE_LICENCE_CODES
    }
    assert non_permissive
    assert "CC BY-ND" in non_permissive


# ---------------------------------------------------------------------------
# The pins
# ---------------------------------------------------------------------------
def test_the_draw_is_pinned_and_free_of_repeats() -> None:
    ids = genre.pinned_pmcids()
    assert len(ids) == 2000
    assert len(set(ids)) == len(ids)
    assert all(genre.DRAW_ID_LOW <= pmcid < genre.DRAW_ID_HIGH for pmcid in ids)


def test_the_manifest_digest_is_pinned() -> None:
    assert re.fullmatch(r"[0-9a-f]{64}", genre.PINNED_MANIFEST_SHA256)


def test_the_manifest_rendering_is_sorted_and_canonical() -> None:
    """The digest is over this exact rendering, so its shape is part of the pin."""
    body = genre.manifest_text({7: "b" * 64, 3: "a" * 64})
    assert body == f"PMC3\t{'a' * 64}\nPMC7\t{'b' * 64}\n"


def test_only_version_one_is_ever_fetched() -> None:
    """A later version must not silently replace a pinned article."""
    assert genre.xml_url(123).endswith("/PMC123.1/PMC123.1.xml")
    assert genre.metadata_url(123).endswith("/PMC123.1/PMC123.1.json")


# ---------------------------------------------------------------------------
# The manifest declaration, and the ceiling the role puts on this corpus
# ---------------------------------------------------------------------------
def test_the_corpus_is_declared_and_can_never_back_a_headline() -> None:
    import tools.splits as splits

    manifest = splits.load()
    corpus = manifest.corpora["pmc_oa_same_article_genre"]
    assert corpus.role == "single_annotator_reference"
    assert corpus.task == "extraction"
    assert corpus.may_back_a_headline is False
    assert corpus.name not in [c.name for c in manifest.headline_capable("extraction")]


def test_the_runner_and_the_manifest_agree_on_the_corpus_name() -> None:
    """A runner writing records under a name nothing declares is an undeclared corpus."""
    import tools.splits as splits

    assert "pmc_oa_same_article_genre" in splits.load().corpora


# ---------------------------------------------------------------------------
# The measuring instrument may not become a shipped code path (R10)
# ---------------------------------------------------------------------------
def test_no_shipped_module_can_reach_the_measuring_instrument() -> None:
    for path in (REPO_ROOT / "src" / "acronymkit").rglob("*.py"):
        assert "run_genre" not in path.read_text(encoding="utf-8"), path


def test_the_runner_adds_no_proposer_of_its_own() -> None:
    """The pool is exactly ``bench/run_monoculture.py``'s, which is the point.

    A new Schwartz & Hearst descendant would change the pool the contrast is
    measured against, and Mandate II forbids one outright.
    """
    source = RUNNER.read_text(encoding="utf-8")
    assert "def propose_" not in source
    assert "def sh_alignable" not in source
    for name in mono.EXTERNAL_SH_SYSTEMS:
        assert f"import {name}" not in source
