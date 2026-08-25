"""Tests for ``tools/build_gold_corpus.py`` and its reader in ``bench/corpora.py``.

This pipeline builds the corpus that would close ``headline_capable("extraction")``,
and the thing most worth testing about it is not that it extracts well. It is that
it **refuses to overclaim**. The artifact it writes is adjudicated by one person,
that person is the author of one of the systems pooled into it, and every incentive
in the situation points at quietly filing it as ``held_out`` and quoting a number
off it. So the refusals are pinned first and hardest:

* an envelope may not claim ``is_gold_standard`` while carrying fewer than two
  adjudicators -- and the check is at *read* time, not only at write time, because
  the field is written by a tool in this repository and a later tool can be told
  to write it differently;
* a verdict with no adjudicator is refused, because an unattributed verdict is
  exactly what later gets read as though a second annotator produced it;
* the worklist carries no proposed verdict, so adjudication cannot decay into
  review of the extractor's own output; and
* ``ReferenceSet.require_headline_eligible`` raises, and its message names the
  two unmet conditions rather than stating a verdict.

Second, the three defects the **pilot** found, as regressions. Each one reached a
worklist or a population count before it was caught, and each is the argument for
piloting rather than adjudicating at scale:

* the legend row ``CPI-U--Consumer Price Index for All Urban Consumers`` split at
  the space rather than at the double hyphen;
* the legend ran past its own table into the next section heading; and
* ``(``NAECA'')`` landed in the *unproposed* stratum for a document where
  ``acronymkit`` had proposed ``NAECA``, which would have re-weighted into a
  false-negative rate for definitions the systems did in fact find.

Third, the pin. ``tools/fetch_data.py`` pins by the digest of the fetched bytes and
that is wrong for this substrate: both hosts rewrite e-mail addresses into a
per-response token, so the same document differs in bytes. The property the pin
rests on -- two bodies differing only in that token hash identically -- is asserted
here rather than trusted.

Nothing in this file touches the network. The two live behaviours that cannot be
tested offline are named in ``TestWhatIsNotTestedHere`` rather than left as an
absence.
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_PATH = REPO_ROOT / "tools" / "build_gold_corpus.py"
SPLITS_PATH = REPO_ROOT / "tools" / "splits.py"


def _load(path: Path, name: str) -> ModuleType:
    """Import a ``tools/`` script by path.

    ``tools/`` is a directory of scripts and must not become a package: making it
    importable for the benefit of a test would be the test changing the shape of
    the thing it tests. ``tests/test_check_claims.py`` records the same reasoning.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# A GUARD, NOT A LINE IN `EXPECTED_NON_PASSING`. `tools/` ships in the sdist and
# is no part of an installed distribution, so under the installed-suite CI job
# the two loads below raise `FileNotFoundError` and this file fails to COLLECT.
# The obvious spelling -- `pytest.mark.skipif` -- cannot help: marks run at
# collection and the module body runs at import, so the exception has already
# happened. That is the lesson of the fifth historical breakage and it is why
# this is a module-level skip placed BEFORE the loads rather than a decorator
# after them.
#
# The alternative was adding this file to `EXPECTED_NON_PASSING` in
# `.github/workflows/ci.yml`, beside the two files that do exactly this. That
# list's own comment argues against it: an entry is keyed on the FILE, so while
# a name sits there the job cannot see any second defect in it -- measured, by
# reintroducing a real breakage into a listed file and getting a run identical
# to a clean one. The list is something to shrink.
if not TOOL_PATH.is_file() or not SPLITS_PATH.is_file():  # pragma: no cover - CI job only
    pytest.skip(
        "tools/ is not part of an installed distribution; these tests belong to a checkout",
        allow_module_level=True,
    )

builder = _load(TOOL_PATH, "_build_gold_corpus_under_test")
splits = _load(SPLITS_PATH, "_splits_for_gold_corpus_test")

# `bench/corpora.py` IS GUARDED SEPARATELY FROM `tools/`, BECAUSE THE SDIST SHIPS
# ONE AND NOT THE OTHER. The extracted-tree run in the `build` job has `tools/`
# -- that run is where these tool tests are meant to execute -- but the sdist
# deliberately does not ship `bench/*.py`, so the import below fails there with
# `cannot import name 'corpora' from 'bench'`: the package directory exists,
# because `bench/results.json` ships, and the module does not.
#
# Skipping the whole module on that condition would be wrong. It would silently
# drop the tool tests from the one run that exists to exercise them. So only the
# reader tests stand down, via `needs_corpora` below.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CORPORA_SOURCE = REPO_ROOT / "bench" / "corpora.py"
if CORPORA_SOURCE.is_file():
    from bench import corpora
else:  # pragma: no cover - sdist run only
    corpora = None  # type: ignore[assignment]

#: For the tests that exercise the reader rather than the builder.
needs_corpora = pytest.mark.skipif(
    corpora is None, reason="bench/corpora.py is not shipped in the sdist"
)

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
#: A Federal Register body as the primary host serves it: an HTML shell, a single
#: ``<pre>``, hyperlinks inserted into the plain text, and a CDN-obfuscated e-mail
#: address. ``{token}`` is where the per-response cipher goes.
BODY_TEMPLATE = """<html>
<head><title>Federal Register</title></head>
<body><pre>
[Federal Register Volume 89, Number 41]
DEPARTMENT OF HOMELAND SECURITY
Coast Guard

FOR FURTHER INFORMATION CONTACT: email <a href="/cdn-cgi/l/email-protection#{token}"><span class="__cf_email__" data-cfemail="{token}">[email&#160;protected]</span></a>.

SUPPLEMENTARY INFORMATION:

I. Table of Abbreviations

CFR Code of Federal Regulations
CPI-U--Consumer Price Index for All Urban Consumers
IMMACT 90--Immigration Act of 1990
LWD Low Water Datum based on IGLD85

II. Background Information and Regulatory History

    The Coast Guard published a notice of proposed rulemaking (NPRM) about
the Low Water Datum (LWD) at <a href="http://www.gpo.gov">www.gpo.gov</a>.
The National Appliance Energy Conservation Act of 1987 (``NAECA'') applies.
See 88 FR 29591 (May 8, 2023).
</pre></body>
</html>
"""


def body(token: str = "a1b2c3") -> bytes:
    """One fetched body, with a chosen obfuscation token."""
    return BODY_TEMPLATE.format(token=token).encode("utf-8")


@pytest.fixture()
def text() -> str:
    """The normalised text of the fixture document."""
    return builder.normalise_body(body())


def worklist_rows(path: Path) -> list:
    """Every JSON record in a worklist or adjudication file."""
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


# ---------------------------------------------------------------------------
# the pin
# ---------------------------------------------------------------------------
class TestThePin:
    """The corpus's identity is the text, and the reason is measured."""

    def test_the_shell_is_removed_and_the_document_survives(self, text: str) -> None:
        """``<pre>`` unwrapped, tags dropped, entities resolved, links kept as text."""
        assert "<pre>" not in text and "<html>" not in text
        assert "www.gpo.gov" in text
        assert "Table of Abbreviations" in text
        assert "&#160;" not in text

    def test_an_obfuscated_address_becomes_a_constant(self, text: str) -> None:
        """A visible placeholder, not the cipher and not the real address."""
        assert builder._EMAIL_PLACEHOLDER in text
        assert "cdn-cgi" not in text
        assert "__cf_email__" not in text

    def test_two_hosts_disagreeing_only_on_the_token_hash_identically(self) -> None:
        """The whole reason the digest is over text and not over bytes.

        Measured live during this workstream: the primary host and the Government
        Publishing Office mirror serve byte-different bodies for the same document
        because the CDN cipher is per-response. A byte pin would fire the loud
        checksum failure ``tools/fetch_data.py`` reserves for a corpus that really
        changed, on every second fetch.
        """
        first, second = body("deadbeef"), body("0123456789abcdef")
        assert first != second
        assert builder.text_digest(builder.normalise_body(first)) == builder.text_digest(
            builder.normalise_body(second)
        )

    def test_line_endings_are_normalised(self) -> None:
        """CRLF and CR must not change a document's identity."""
        crlf = BODY_TEMPLATE.format(token="x").replace("\n", "\r\n").encode("utf-8")
        assert builder.normalise_body(crlf) == builder.normalise_body(body("x"))

    def test_the_pin_table_is_well_formed(self) -> None:
        """Every pinned document carries a real digest and a real length."""
        assert builder.PINNED_DOCUMENTS, "the population is empty; nothing is pinned"
        numbers = [pin.document_number for pin in builder.PINNED_DOCUMENTS]
        assert len(numbers) == len(set(numbers)), "a document is pinned twice"
        assert len(numbers) == builder.SELECTION.size
        for pin in builder.PINNED_DOCUMENTS:
            assert len(pin.text_sha256) == 64, pin.document_number
            assert set(pin.text_sha256) <= set("0123456789abcdef"), pin.document_number
            assert pin.text_length > 0, pin.document_number
            datetime.date.fromisoformat(pin.publication_date)

    def test_the_two_body_urls_are_built_from_the_pin(self) -> None:
        """Re-fetching a pinned document needs no second API round trip."""
        pin = builder.PINNED_DOCUMENTS[0]
        primary = builder.body_url(pin.document_number, pin.publication_date)
        mirror = builder.mirror_url(pin.document_number, pin.publication_date)
        assert pin.document_number in primary and pin.document_number in mirror
        assert primary.startswith("https://") and mirror.startswith("https://")
        assert primary != mirror, "the mirror must be a different host to be a check"


class TestSelection:
    """The draw is a fact about the set of documents, not about pagination."""

    def test_the_draw_is_seeded_and_reproducible(self) -> None:
        rows = [{"document_number": f"2024-{index:05d}"} for index in range(200)]
        first = builder.draw(rows, builder.SELECTION)
        second = builder.draw(list(reversed(rows)), builder.SELECTION)
        assert [row["document_number"] for row in first] == [
            row["document_number"] for row in second
        ], "the draw depends on the order the API happened to return"

    def test_a_shrunken_population_is_refused_rather_than_accommodated(self) -> None:
        """Do not shrink the draw to fit; that is a different corpus wearing the same name."""
        rows = [{"document_number": f"2024-{index:05d}"} for index in range(3)]
        with pytest.raises(SystemExit, match="fewer than the pinned draw size"):
            builder.draw(rows, builder.SELECTION)


# ---------------------------------------------------------------------------
# the agency's legend, and the two defects the pilot found in it
# ---------------------------------------------------------------------------
class TestTheLegend:
    """The closest thing here to an arbiter that is not the system's author."""

    def test_both_attested_row_syntaxes_parse(self, text: str) -> None:
        entries = builder.legend_entries(text)
        assert entries["CFR"] == "Code of Federal Regulations"
        assert entries["LWD"] == "Low Water Datum based on IGLD85"

    def test_a_dashed_row_splits_at_the_dash_and_not_at_a_space(self, text: str) -> None:
        """Pilot regression.

        A single pattern with ``(?:--|[ \\t]+)`` reads ``CPI-U--Consumer Price
        Index ...`` as ``CPI-U--Consumer`` defined as ``Price Index ...``, because
        a short-form class that admits ``-`` swallows the dash run. The dashed form
        is tried first for exactly this reason.
        """
        entries = builder.legend_entries(text)
        assert entries["CPI-U"] == "Consumer Price Index for All Urban Consumers"
        assert not any(key.startswith("CPI-U--") for key in entries)

    def test_a_dashed_short_form_may_contain_a_space(self, text: str) -> None:
        """``IMMACT 90--Immigration Act of 1990``. Pilot regression."""
        assert builder.legend_entries(text)["IMMACT 90"] == "Immigration Act of 1990"

    def test_the_legend_stops_at_the_next_section_heading(self, text: str) -> None:
        """Pilot regression.

        In the Coast Guard house style the next heading sits directly under the
        last legend row with no blank line, so a parser that stops only on blank
        lines reports ``II.`` defined as ``Background Information and Regulatory
        History`` -- and then keeps going into prose.
        """
        entries = builder.legend_entries(text)
        assert "II." not in entries
        assert not any(key in ("The", "On") for key in entries)

    def test_a_row_offset_points_at_the_row(self, text: str) -> None:
        """Pilot regression: evidence that does not contain the thing being judged.

        Anchoring on ``text.find(short_form)`` put the adjudicator's window at the
        first mention of ``CFR`` in the document, which is a page header. Evidence
        that looks like evidence and is not is worse than none.
        """
        rows = builder.legend_rows(text)
        assert rows
        for short, long_form, offset in rows:
            window = text[offset : offset + len(short) + len(long_form) + 4]
            assert short in window, (short, window)

    def test_a_document_with_no_legend_yields_nothing(self) -> None:
        assert builder.legend_entries("There is no table of anything here.\n") == {}


# ---------------------------------------------------------------------------
# pooling
# ---------------------------------------------------------------------------
class TestPooling:
    """Three proposers, and an honest account of what the second and third buy."""

    @pytest.fixture()
    def pool(self, tmp_path: Path, text: str) -> object:
        return builder.build_pool(
            {"doc-1": text},
            external_system=builder.EXTERNAL_SYSTEMS[0],
            interpreter=None,
            scratch=tmp_path,
        )

    def test_a_missing_external_proposer_is_recorded_not_tolerated(self, pool: object) -> None:
        """A two-proposer pool is a different recipe and must say so."""
        assert "NOT RUN" in pool.recipe["external"]
        assert pool.recipe["acronymkit_high_recall"]
        assert pool.recipe["all_caps"]

    def test_the_recipe_records_the_exact_configuration(self, pool: object) -> None:
        """ "We turned the knobs up" is not a reproducible recipe."""
        recipe = pool.recipe["acronymkit_high_recall"]
        assert "extraction_require_uppercase=False" in recipe
        assert "legend_syntax off" in recipe

    def test_every_stratum_is_counted_and_the_counts_are_the_candidates(self, pool: object) -> None:
        """Populations must be exact: an estimate without its denominator is noise."""
        assert set(pool.population) == set(builder.STRATA)
        assert sum(pool.population.values()) == len(pool.candidates)

    def test_a_definition_is_proposed_and_lands_in_a_proposed_stratum(self, pool: object) -> None:
        proposed = {
            (candidate.short_form, candidate.long_form)
            for candidate in pool.candidates
            if candidate.stratum.startswith("proposed")
        }
        assert ("NPRM", "notice of proposed rulemaking") in proposed

    def test_a_quoted_short_form_a_proposer_found_is_not_called_unproposed(
        self, pool: object
    ) -> None:
        """Pilot regression, and the one that would have biased the headline estimate.

        ``(``NAECA'')`` is the Federal Register's quoting of a short form that
        ``acronymkit`` proposes. Comparing raw inner text against proposed surfaces
        put it in the *unproposed* stratum, where it adjudicates as a definition and
        re-weights by that stratum's population into a false-negative rate for
        definitions the systems did in fact find.
        """
        unproposed = {
            candidate.short_form
            for candidate in pool.candidates
            if candidate.stratum == "unproposed_parenthetical"
        }
        assert not any("NAECA" in surface for surface in unproposed), sorted(unproposed)

    def test_the_all_caps_proposer_contributes_vertices_not_edges(self, pool: object) -> None:
        """It proposes short forms with no long form, and that is its whole job."""
        unpaired = [
            candidate for candidate in pool.candidates if candidate.stratum == "unpaired_short_form"
        ]
        assert unpaired
        assert all(candidate.long_form is None for candidate in unpaired)
        assert all(candidate.proposers == ("all_caps",) for candidate in unpaired)

    def test_unproposed_candidates_name_no_proposer(self, pool: object) -> None:
        """Empty ``proposers`` is what ``unproposed`` means; it is not a default."""
        for candidate in pool.candidates:
            if candidate.stratum.startswith("unproposed"):
                assert candidate.proposers == (), candidate

    def test_legend_support_is_evidence_and_travels_with_the_candidate(self, pool: object) -> None:
        supported = [c for c in pool.candidates if c.legend_support]
        assert supported, "the fixture carries a legend; nothing picked it up"

    def test_every_candidate_carries_a_readable_evidence_window(self, pool: object) -> None:
        for candidate in pool.candidates:
            assert candidate.evidence.strip(), candidate
            assert "\n" not in candidate.evidence


class TestTheDefiningOccurrenceIsNotAGoldDerivation:
    """Choosing a window to read is not choosing which occurrence is the definition."""

    def test_it_prefers_an_occurrence_the_short_form_follows(self) -> None:
        """And skips one it does not, which is the masthead case.

        The window that decides this is deliberately tight. At the first draft's
        160 characters a Federal Register masthead qualified -- the agency name and
        a docket number containing its initials sit close together and define
        nothing -- and three pilot items were adjudicated against a page header.
        """
        header = "Low Water Datum appears in the running head. " + "filler word " * 8
        text = header + "Later: Low Water Datum (LWD) is defined here."
        index = builder._defining_occurrence(text, "LWD", "Low Water Datum")
        assert text[index:].startswith("Low Water Datum (LWD)")

    def test_it_falls_back_rather_than_failing(self) -> None:
        assert builder._defining_occurrence("nothing here", "XX", "ex ex") == 0


# ---------------------------------------------------------------------------
# the worklist
# ---------------------------------------------------------------------------
class TestTheWorklist:
    """What an adjudicator is shown, and what they are deliberately not shown."""

    @pytest.fixture()
    def drawn(self, tmp_path: Path, text: str) -> tuple:
        pool = builder.build_pool(
            {"doc-1": text},
            external_system=builder.EXTERNAL_SYSTEMS[0],
            interpreter=None,
            scratch=tmp_path,
        )
        allocation = dict.fromkeys(builder.STRATA, 3)
        items = builder.draw_worklist(pool, seed=7, allocation=allocation)
        path = builder.write_worklist(tmp_path / "worklist.jsonl", pool, items, seed=7)
        return pool, items, path

    def test_no_item_carries_a_proposed_verdict(self, drawn: tuple) -> None:
        """The load-bearing refusal.

        Pre-filling a verdict turns adjudication into review of the extractor's own
        output, which is the failure this whole pipeline is arranged against.
        """
        rows = worklist_rows(drawn[2])
        items = [row for row in rows if row["record"] == "item"]
        assert items
        for row in items:
            assert row["verdict"] is None
            assert row["hard_case"] is None
            assert row["adjudicated_long_form"] is None

    def test_the_header_carries_the_provenance_and_the_warning(self, drawn: tuple) -> None:
        header = worklist_rows(drawn[2])[0]
        assert header["record"] == "header"
        assert header["licence_read_on"] and header["licence_url"]
        assert header["population"] and header["recipe"]
        assert "not a gold standard" in header["warning"]
        assert "single-annotator reference set" in header["warning"]
        assert "one more domain" in header["domain"].lower()

    def test_sampling_is_within_stratum_and_never_across_it(self, drawn: tuple) -> None:
        """Sampling the union would drown every stratum in parentheticals."""
        pool, items, _ = drawn
        for stratum in builder.STRATA:
            available = pool.population.get(stratum, 0)
            taken = sum(1 for item in items if item.stratum == stratum)
            assert taken == min(3, available), stratum

    def test_the_draw_is_reproducible_under_its_seed(self, drawn: tuple) -> None:
        pool, items, _ = drawn
        again = builder.draw_worklist(pool, seed=7, allocation=dict.fromkeys(builder.STRATA, 3))
        assert [item.key() for item in again] == [item.key() for item in items]


# ---------------------------------------------------------------------------
# reading adjudications back
# ---------------------------------------------------------------------------
def _session(rows: list, **header: object) -> object:
    """Build an :class:`AdjudicationSession` from raw rows, via the real loader."""
    return rows


class TestReadingAdjudications:
    """Every refusal here is about attribution, not about format."""

    def _write(self, tmp_path: Path, items: list, **header: object) -> Path:
        head = {
            "record": "header",
            "population": dict.fromkeys(builder.STRATA, 100),
        }
        head.update(header)
        path = tmp_path / "adjudications.jsonl"
        rows = [head] + [dict(item, record="item") for item in items]
        builder._write_lf(path, "\n".join(json.dumps(row) for row in rows) + "\n")
        return path

    def _item(self, **overrides: object) -> dict:
        item = {
            "document": "doc-1",
            "short_form": "NPRM",
            "long_form": "notice of proposed rulemaking",
            "stratum": "proposed_by_several",
            "proposers": ["acronymkit_high_recall", "external"],
            "evidence": "a window",
            "offset": 0,
            "legend_support": False,
            "verdict": "definition",
            "hard_case": "clear",
            "adjudicated_long_form": "notice of proposed rulemaking",
            "note": "",
            "adjudicator": "someone",
        }
        item.update(overrides)
        return item

    def test_a_verdict_with_no_adjudicator_is_refused(self, tmp_path: Path) -> None:
        """An unattributed verdict is what later reads as a second annotator's."""
        path = self._write(tmp_path, [self._item(adjudicator="")])
        with pytest.raises(SystemExit, match="no adjudicator"):
            builder.load_adjudications(path)

    def test_a_verdict_outside_the_vocabulary_is_refused(self, tmp_path: Path) -> None:
        path = self._write(tmp_path, [self._item(verdict="probably")])
        with pytest.raises(SystemExit, match="is not one of"):
            builder.load_adjudications(path)

    def test_an_undecided_item_is_counted_and_not_guessed(self, tmp_path: Path) -> None:
        path = self._write(tmp_path, [self._item(verdict=None), self._item()])
        session = builder.load_adjudications(path)
        assert session.undecided == 1
        assert len(session.decided) == 1

    def test_an_unknown_hard_case_is_reported_rather_than_refused(self, tmp_path: Path) -> None:
        """A new category is a finding about the substrate, not a malformed file.

        The pilot added seven of them; refusing the first would have meant
        adjudicating the substrate with a vocabulary written before anyone read it.
        """
        path = self._write(tmp_path, [self._item(hard_case="something_new")])
        session = builder.load_adjudications(path)
        assert session.unknown_categories == ["something_new"]
        assert builder.pilot_report(session)["unknown_categories"] == ["something_new"]


class TestThePilotReport:
    """What the pilot measures, and what it refuses to let a reader conclude."""

    def _session(self, tmp_path: Path, items: list, **header: object) -> object:
        helper = TestReadingAdjudications()
        return builder.load_adjudications(helper._write(tmp_path, items, **header))

    def _item(self, **overrides: object) -> dict:
        return TestReadingAdjudications()._item(**overrides)

    def test_one_adjudicator_is_a_reference_set_and_never_a_gold_standard(
        self, tmp_path: Path
    ) -> None:
        session = self._session(tmp_path, [self._item()])
        report = builder.pilot_report(session)
        assert report["adjudicator_count"] == 1
        assert report["is_gold_standard"] is False
        assert report["artifact_kind"] == "single-annotator reference set"

    def test_the_rate_ships_with_the_caveat_that_makes_it_readable(self, tmp_path: Path) -> None:
        """A rate produced by one interested reader is not an annotation costing."""
        session = self._session(tmp_path, [self._item()])
        assert "upper bound on speed" in builder.pilot_report(session)["rate_caveat"]

    def test_contested_is_narrower_than_not_clear(self, tmp_path: Path) -> None:
        """The distinction the first version of this report got wrong.

        Counting every non-``clear`` item as hard put ``not_an_abbreviation`` -- a
        subsection marker like ``(b)``, decidable at a glance -- in the same column
        as ``boundary``, where two careful people genuinely disagree. It made the
        cheapest stratum look like the most expensive one.
        """
        items = [
            self._item(hard_case="not_an_abbreviation", verdict="not_a_definition"),
            self._item(hard_case="boundary"),
            self._item(hard_case="clear"),
        ]
        stratum = builder.pilot_report(self._session(tmp_path, items))["by_stratum"]
        row = stratum["proposed_by_several"]
        assert row["not_clear"] == 2
        assert row["contested"] == 1

    def test_an_undecidable_item_counts_as_contested_whatever_its_category(
        self, tmp_path: Path
    ) -> None:
        items = [self._item(verdict="undecidable", hard_case="clear")]
        report = builder.pilot_report(self._session(tmp_path, items))
        assert report["undecidable"] == 1
        assert report["contested"] == 1

    def test_every_stratum_reports_its_population_beside_its_sample(self, tmp_path: Path) -> None:
        report = builder.pilot_report(self._session(tmp_path, [self._item()]))
        row = report["by_stratum"]["proposed_by_several"]
        assert row["population"] == 100 and row["sampled"] == 1

    def test_a_stratum_with_no_definitions_does_not_report_a_false_negative_rate_of_zero(
        self, tmp_path: Path
    ) -> None:
        """The single most important line in the report.

        A few dozen items drawn from a population of thousands cannot distinguish
        "no missed definitions" from "several hundred", and the whole case for
        enlarging the unproposed sample is the width of that gap. A point estimate
        of zero printed alone would read as a clean bill of health.
        """
        items = [
            self._item(
                stratum="unproposed_parenthetical",
                verdict="not_a_definition",
                hard_case="not_an_abbreviation",
            )
            for _ in range(10)
        ]
        row = builder.pilot_report(self._session(tmp_path, items))["by_stratum"][
            "unproposed_parenthetical"
        ]
        assert row["definitions_found"] == 0
        assert row["definitions_per_stratum_point"] == 0
        assert row["definitions_per_stratum_upper95"] > 0

    @pytest.mark.parametrize(
        ("found", "sampled"),
        [(0, 1), (0, 30), (0, 3000), (1, 30), (30, 30)],
    )
    def test_the_upper_bound_is_a_proportion_and_never_below_the_estimate(
        self, found: int, sampled: int
    ) -> None:
        upper = builder._rule_of_three_upper(found, sampled)
        assert 0.0 <= upper <= 1.0
        assert upper >= found / sampled


# ---------------------------------------------------------------------------
# freezing
# ---------------------------------------------------------------------------
class TestFreezing:
    """The artifact may not claim more than its adjudicator count supports."""

    @pytest.fixture()
    def frozen(self, tmp_path: Path) -> dict:
        helper = TestReadingAdjudications()
        path = helper._write(
            tmp_path,
            [
                helper._item(),
                helper._item(
                    short_form="LWD",
                    long_form="Low Water Datum",
                    verdict="wrong_long_form",
                    adjudicated_long_form="Low Water Datum based on IGLD85",
                    hard_case="boundary",
                ),
                helper._item(
                    short_form="(b)",
                    long_form=None,
                    verdict="not_a_definition",
                    adjudicated_long_form=None,
                    hard_case="not_an_abbreviation",
                ),
            ],
        )
        session = builder.load_adjudications(path)
        pool = builder.Pool(population=dict.fromkeys(builder.STRATA, 100), recipe={"x": "y"})
        out = builder.freeze(
            session, pool, path=tmp_path / "reference_set.json", frozen_on="2026-08-24"
        )
        return json.loads(out.read_text(encoding="utf-8"))

    def test_it_labels_itself_a_reference_set_and_refuses_the_word_gold(self, frozen: dict) -> None:
        assert frozen["artifact_kind"] == "single-annotator reference set"
        assert frozen["is_gold_standard"] is False
        assert frozen["headline_eligible"] is False
        assert "gold standard" not in frozen["artifact_kind"]

    def test_it_asks_for_a_role_that_can_never_back_a_headline(self, frozen: dict) -> None:
        """The artifact asked for a role by name; the vocabulary now has it.

        This assertion used to be ``requested_role not in splits.ROLES`` -- the
        artifact naming a role the manifest could not express, which was the true
        and useful statement for exactly one round. Inverting it rather than
        deleting it keeps the binding: the envelope's ``requested_role`` and the
        manifest's vocabulary are still checked against each other, and the
        property that made the role worth adding is checked beside it.

        ``held_out`` would make a self-adjudicated set headline-eligible;
        ``tuning`` would assert a fitting that never happened. Neither is
        reachable from here now, because the requested role is in
        ``NEVER_HEADLINE_ROLES``.
        """
        assert frozen["requested_role"] == builder.REQUESTED_ROLE
        assert frozen["requested_role"] in splits.ROLES
        assert frozen["requested_role"] in splits.NEVER_HEADLINE_ROLES
        assert "held_out" in frozen["role_note"]

    def test_the_freeze_date_travels_with_the_corpus(self, frozen: dict) -> None:
        """A freeze later than the tuning it adjudicates is not a freeze."""
        assert frozen["frozen_on"] == "2026-08-24"

    def test_the_domain_and_the_licence_reading_travel_with_it(self, frozen: dict) -> None:
        assert "one more domain" in frozen["domain"].lower()
        assert frozen["licence_read_on"] and frozen["licence_url"]
        assert frozen["vendorable"] is False

    def test_only_definitions_reach_the_payload(self, frozen: dict) -> None:
        pairs = [pair for rows in frozen["payload"].values() for pair in rows]
        assert ["NPRM", "notice of proposed rulemaking"] in pairs
        assert ["LWD", "Low Water Datum based on IGLD85"] in pairs
        assert not any(pair[0] == "(b)" for pair in pairs)

    def test_a_sampled_document_is_not_marked_exhaustively_annotated(self, frozen: dict) -> None:
        """The flag a pilot cannot earn, and the one most easily assumed.

        The pool in this fixture holds no candidates, so no document can have had
        all of its candidates adjudicated. That is the pilot's situation exactly:
        a worklist is a sample of the pool, so no document is complete and the
        artifact must not present itself as scorable.
        """
        assert frozen["exhaustively_annotated_documents"] == []
        assert frozen["scorable"] is False
        assert "recall is undefined" in frozen["scorable_note"]

    def test_a_document_whose_every_candidate_was_adjudicated_is_marked_exhaustive(
        self, tmp_path: Path
    ) -> None:
        """And the flag is computed from the pool, not asserted by the caller."""
        helper = TestReadingAdjudications()
        path = helper._write(tmp_path, [helper._item()])
        session = builder.load_adjudications(path)
        pool = builder.Pool(
            candidates=[
                builder.Candidate(
                    document="doc-1",
                    short_form="NPRM",
                    long_form="notice of proposed rulemaking",
                    stratum="proposed_by_several",
                )
            ],
            population=dict.fromkeys(builder.STRATA, 1),
        )
        out = builder.freeze(session, pool, path=tmp_path / "reference_set.json")
        envelope = json.loads(out.read_text(encoding="utf-8"))
        assert envelope["exhaustively_annotated_documents"] == ["doc-1"]
        assert envelope["scorable"] is True

    def test_an_empty_session_produces_no_artifact(self, tmp_path: Path) -> None:
        session = builder.AdjudicationSession()
        pool = builder.Pool()
        with pytest.raises(SystemExit, match="nothing adjudicated"):
            builder.freeze(session, pool, path=tmp_path / "out.json")


# ---------------------------------------------------------------------------
# the reader in bench/corpora.py
# ---------------------------------------------------------------------------
@needs_corpora
class TestTheReader:
    """Standing, not shape. Nothing here would crash; that is the danger."""

    @pytest.fixture()
    def envelope(self) -> dict:
        return {
            "artifact_kind": "single-annotator reference set",
            "is_gold_standard": False,
            "adjudicators": ["someone (author of acronymkit)"],
            "frozen_on": "2026-08-24",
            "domain": "one more domain, not general text",
            "licence": "Public domain (17 U.S.C. 105)",
            "payload": {"doc-1": [["NPRM", "notice of proposed rulemaking"]]},
        }

    def test_it_parses_into_documents_a_pair_scorer_could_read(self, envelope: dict) -> None:
        reference = corpora.parse_reference_set("fr", "x.json", envelope)
        assert len(reference.documents) == 1
        assert reference.documents[0].pairs[0].short_form == "NPRM"

    def test_the_label_names_the_standing_the_adjudicator_count_and_the_domain(
        self, envelope: dict
    ) -> None:
        label = corpora.parse_reference_set("fr", "x.json", envelope).label()
        assert "single-annotator reference set" in label
        assert "1 adjudicator" in label
        assert "Federal Register" in label

    def test_it_refuses_to_back_a_headline_and_says_what_would_change_that(
        self, envelope: dict
    ) -> None:
        reference = corpora.parse_reference_set("fr", "x.json", envelope)
        with pytest.raises(SystemExit) as caught:
            reference.require_headline_eligible()
        message = str(caught.value)
        assert "second, independent adjudicator" in message
        assert "agreement computed and published" in message

    def test_an_envelope_claiming_gold_with_one_adjudicator_is_refused_at_read_time(
        self, envelope: dict
    ) -> None:
        """The check that matters: the field is written by a tool in this repository.

        ``freeze`` writes ``is_gold_standard`` honestly today. A later tool can be
        told to write it differently, and the reader is the last place the claim and
        the evidence can be compared before a number exists.
        """
        envelope["is_gold_standard"] = True
        with pytest.raises(SystemExit, match="claim and the evidence"):
            corpora.parse_reference_set("fr", "x.json", envelope)

    def test_an_envelope_with_no_adjudicator_is_refused(self, envelope: dict) -> None:
        envelope["adjudicators"] = []
        with pytest.raises(SystemExit, match="records no adjudicator"):
            corpora.parse_reference_set("fr", "x.json", envelope)

    def test_a_file_that_is_not_a_freeze_envelope_is_refused(self) -> None:
        with pytest.raises(SystemExit, match="freeze envelope"):
            corpora.parse_reference_set("fr", "x.json", {"payload": []})

    def test_a_pilot_produces_nothing_scorable_and_the_refusal_says_why(
        self, envelope: dict
    ) -> None:
        """The guard against the quietest failure available here.

        A frozen pilot looks exactly like a complete pair corpus: same envelope,
        same payload shape, real pairs inside. It is a *sample*, so against it
        recall is undefined -- the denominator is unknown -- and precision is
        understated, because a correct pair that was never sampled scores as a
        false positive. Nothing about the file reveals that, which is why the
        artifact carries the flag and the reader enforces it.
        """
        reference = corpora.parse_reference_set("fr", "x.json", envelope)
        assert reference.exhaustive == ()
        with pytest.raises(SystemExit) as caught:
            reference.documents_for_scoring()
        assert "no exhaustively annotated document" in str(caught.value)

    def test_a_document_with_no_text_is_refused_rather_than_scored_as_a_miss(
        self, envelope: dict
    ) -> None:
        """``extraction`` gold is a passage plus the pairs annotated in it.

        An empty passage hands every extractor an empty string, which yields no
        predictions and scores as total recall failure -- a plausible number, not
        an error. ``read_plod_cw_text`` documents the same trap for its own
        corpus, which is where the shape of this guard comes from.
        """
        envelope["exhaustively_annotated_documents"] = ["doc-1"]
        reference = corpora.parse_reference_set("fr", "x.json", envelope)
        with pytest.raises(SystemExit, match="carry no text"):
            reference.documents_for_scoring()

    def test_a_document_with_text_and_an_exhaustive_annotation_is_returned(
        self, envelope: dict
    ) -> None:
        envelope["exhaustively_annotated_documents"] = ["doc-1"]
        reference = corpora.parse_reference_set(
            "fr", "x.json", envelope, bodies={"doc-1": "a passage (NPRM) in it"}
        )
        usable = reference.documents_for_scoring()
        assert [document.uid for document in usable] == ["doc-1"]
        assert usable[0].text

    def test_a_cached_body_that_drifted_under_its_pin_is_dropped(
        self, tmp_path: Path, envelope: dict
    ) -> None:
        """A corpus scored against drifted text produces a number with no recorded cause."""
        envelope["documents"] = [
            {"document_number": "doc-1", "text_sha256": "0" * 64},
            {"document_number": "doc-2", "text_sha256": ""},
        ]
        bodies = tmp_path / "bodies"
        bodies.mkdir()
        (bodies / "doc-1.txt").write_text("drifted", encoding="utf-8")
        (bodies / "doc-2.txt").write_text("unpinned but present", encoding="utf-8")
        found = corpora._reference_bodies(envelope, bodies)
        assert "doc-1" not in found
        assert found["doc-2"] == "unpinned but present"

    def test_the_provenance_survives_the_parse(self, envelope: dict) -> None:
        """A consumer must never have to re-open the artifact to say where it came from."""
        envelope["population"] = {"unproposed_parenthetical": 3503}
        reference = corpora.parse_reference_set("fr", "x.json", envelope)
        assert reference.provenance["population"]["unproposed_parenthetical"] == 3503
        assert "adjudicators" not in reference.provenance

    def test_it_is_not_iterable_as_documents(self, envelope: dict) -> None:
        """Same guard ``SegmentationCorpus`` carries: the idiom must fail, not half-work."""
        reference = corpora.parse_reference_set("fr", "x.json", envelope)
        with pytest.raises(TypeError):
            list(iter(reference))  # type: ignore[call-overload]


@needs_corpora
class TestTheRegistration:
    """The corpus is declared now, at a role that can never back a headline.

    This class replaces ``TestTheRegistryGap``, which pinned the *absence* of the
    entry. The gap is closed the way D-056 said it had to be: a new role, not a
    wrong one, and the exemption deleted in the same commit as the table.
    """

    def test_the_role_the_artifact_asked_for_exists_now(self) -> None:
        """``builder.REQUESTED_ROLE`` was a string no vocabulary contained.

        The artifact has been writing ``requested_role`` into its own envelope
        since it was first frozen, and ``tools/splits.py`` had no such role. The
        two are bound here rather than left to agree by memory.
        """
        assert set(splits.ROLES) >= {"tuning", "held_out", builder.REQUESTED_ROLE}
        assert builder.REQUESTED_ROLE in splits.NEVER_HEADLINE_ROLES
        assert builder.REQUESTED_ROLE == corpora.FEDERAL_REGISTER_ROLE

    def test_the_manifest_declares_it_at_exactly_that_role(self) -> None:
        manifest = splits.load(REPO_ROOT / "bench" / "splits.toml")
        corpus = manifest.corpus(corpora.FEDERAL_REGISTER_CORPUS)
        assert corpus.role == builder.REQUESTED_ROLE
        assert corpus.may_back_a_headline is False
        for task in splits.TASKS:
            assert corpora.FEDERAL_REGISTER_CORPUS not in {
                entry.name for entry in manifest.headline_capable(task)
            }, task

    def test_it_is_still_in_no_registry_and_no_declaration_map(self) -> None:
        """Declared is not the same as registered, and it must not become so by drift.

        ``READERS`` promises ``GoldDocument`` lists and this reader returns a
        ``ReferenceSet``; ``DECLARED_AS`` maps *reader* names to *manifest*
        names, and this reader is called by its manifest name directly. Adding it
        to either would hand a pair scorer a corpus that refuses to be scored,
        one call further in than the refusal.
        """
        name = corpora.FEDERAL_REGISTER_CORPUS
        assert name not in corpora.DECLARED_AS
        assert name not in corpora.DECLARED_AS.values()
        for registry in (
            corpora.READERS,
            corpora.DISAMBIGUATION_READERS,
            corpora.SPAN_READERS,
            corpora.CHAR_SPAN_READERS,
            corpora.SEGMENTATION_READERS,
        ):
            assert name not in registry

    def test_the_reader_no_longer_dies_on_the_declaration(self) -> None:
        """The refusal that was the point of the last round, gone for the right reason.

        Asserted as "not *this* failure" rather than as a successful load,
        because the artifact lives under the git-ignored ``data/`` and no CI
        runner has it. Both outcomes are acceptable and only one message is not:
        a runner with the corpus gets a ``ReferenceSet``, a runner without it
        gets the fetch instruction, and neither may be the manifest saying the
        corpus is undeclared.
        """
        try:
            reference = corpora.read_federal_register_reference()
        except SystemExit as exit_:
            message = str(exit_)
            assert "does not declare" not in message, message
            assert "is declared role=" not in message, message
            assert message.startswith("missing "), message
            return
        assert reference.name == corpora.FEDERAL_REGISTER_CORPUS
        assert reference.adjudicator_count == 1

    def test_the_reader_refuses_a_corpus_re_filed_under_another_role(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The one-word edit, driven through the reader rather than beside it.

        ``declaration()`` establishes only that the manifest says *something*
        about this corpus. The danger is that it says ``held_out``, which would
        make a self-adjudicated set the eligible source for the project's
        flagship claim. So the reader asserts the role before it opens the file.

        **This test exists because its first draft did not test that.** The draft
        called ``Corpus.require_role`` directly, which exercises
        ``tools/splits.py`` and not the wiring in ``read_federal_register_reference``:
        deleting the reader's role check left the whole suite green. It now
        re-files the real manifest, injects the resulting declaration, and calls
        the reader -- so removing that branch is red.

        The corpus is built by the *reader's own* loader module rather than by
        this file's copy, because ``tools/splits.py`` is imported by path in two
        places and the ``SplitsError`` the reader catches is the other module's.
        """
        module = corpora._splits_module()
        assert module is not None
        source = (REPO_ROOT / "bench" / "splits.toml").read_text(encoding="utf-8")
        re_filed = source.replace('role = "single_annotator_reference"', 'role = "held_out"', 1)
        assert re_filed != source, "the re-filing did not take; this test proves nothing"
        path = tmp_path / "splits.toml"
        path.write_text(re_filed, encoding="utf-8")
        corpus = module.load(path).corpus(corpora.FEDERAL_REGISTER_CORPUS)
        assert corpus.role == "held_out", "the mutation did not take; this test proves nothing"

        monkeypatch.setattr(corpora, "declaration", lambda name: corpus)
        with pytest.raises(SystemExit, match="the only role this reader will open it at"):
            corpora.read_federal_register_reference()

    def test_the_exemption_map_is_empty_and_its_tripwire_still_fires(self) -> None:
        """The exemption is deleted, and the check that reads it is not now vacuous.

        The old test looped over ``UNREGISTERED_READERS`` asserting each name was
        undeclared. With the map empty that loop runs **zero times** and passes
        unconditionally -- a green measuring nothing, which is D-051's vacuous
        criterion and D-056's ``all()`` over an empty pool arriving a third time.

        So the check is a function, and it is exercised twice: once against the
        real (empty) map, where it must find nothing, and once against a
        synthetic map that excuses a corpus the manifest really declares, where
        it must find it. The second call is what gives this test a firing count
        above zero.
        """
        manifest = splits.load(REPO_ROOT / "bench" / "splits.toml")
        assert corpora.UNREGISTERED_READERS == {}
        assert corpora.stale_exemptions(corpora.UNREGISTERED_READERS, manifest.names) == []

        synthetic = {
            corpora.FEDERAL_REGISTER_CORPUS: "held back because ROLES cannot say what it is"
        }
        assert corpora.stale_exemptions(synthetic, manifest.names) == [
            corpora.FEDERAL_REGISTER_CORPUS
        ], "the tripwire does not fire on an exemption that excuses a declared corpus"

    def test_declaring_it_did_not_make_it_scorable(self) -> None:
        """A corpus in the governance file is one ``--save`` from a table; this one is not.

        Both refusals are on the artifact rather than on the manifest, so
        registration could not have relaxed either. Driven through
        ``parse_reference_set`` so it holds on a runner with no ``data/``.
        """
        envelope = {
            "artifact_kind": "single-annotator reference set",
            "adjudicators": ["one person"],
            "payload": {"doc-1": [["NPRM", "notice of proposed rulemaking"]]},
            "exhaustively_annotated_documents": [],
        }
        reference = corpora.parse_reference_set(corpora.FEDERAL_REGISTER_CORPUS, "x.json", envelope)
        with pytest.raises(SystemExit, match="no exhaustively annotated document"):
            reference.documents_for_scoring()
        with pytest.raises(SystemExit, match="may not back a headline number"):
            reference.require_headline_eligible()

    def test_the_manifest_entry_carries_the_two_facts_the_role_requires(self) -> None:
        """Who decided, and how the candidates they decided on were proposed.

        They were inside the frozen envelope in a git-ignored directory, which is
        somewhere the governance file cannot see. The role's whole content is
        that they are now in the file that governs what may be measured.
        """
        manifest = splits.load(REPO_ROOT / "bench" / "splits.toml")
        corpus = manifest.corpus(corpora.FEDERAL_REGISTER_CORPUS)
        assert corpus.adjudicator_count == 1
        assert corpus.pooling_recipe.strip()
        assert builder.EXTERNAL_SYSTEMS[0] in corpus.pooling_recipe, (
            "the recipe must name the external proposer the tool actually drives"
        )


# ---------------------------------------------------------------------------
# the substrate registration
# ---------------------------------------------------------------------------
class TestTheSubstrateRegistration:
    """Operating rule 4, applied to an entry that was written after the rule."""

    @pytest.fixture()
    def fetch_data(self) -> ModuleType:
        return _load(REPO_ROOT / "tools" / "fetch_data.py", "_fetch_data_for_gold_corpus_test")

    def test_the_substrate_is_registered(self, fetch_data: ModuleType) -> None:
        keys = {substrate.key for substrate in fetch_data.SUBSTRATES}
        assert "federal-register" in keys

    def test_its_licence_came_from_terms_and_carries_a_read_date(
        self, fetch_data: ModuleType
    ) -> None:
        """Both halves of R4. The registry used to enforce only the first."""
        for substrate in fetch_data.SUBSTRATES:
            assert splits._licence_url_problem(substrate.licence_url) is None, substrate.key
            read_on = datetime.date.fromisoformat(substrate.licence_read_on)
            assert read_on <= datetime.date.today(), substrate.key

    def test_the_licence_evidence_is_pinned_like_any_other_licence_file(
        self, fetch_data: ModuleType
    ) -> None:
        asset = fetch_data.BY_KEY["federal-register-terms"]
        assert len(asset.sha256) == 64
        assert asset.licence_read_on == "2026-08-24"
        assert splits._licence_url_problem(asset.licence_url) is None

    def test_the_domain_is_stated_where_it_travels(self, fetch_data: ModuleType) -> None:
        """This repository has twice had to correct a corpus described by its own name."""
        substrate = next(s for s in fetch_data.SUBSTRATES if s.key == "federal-register")
        assert "ONE MORE DOMAIN" in substrate.domain_note
        assert "general text" in substrate.domain_note

    def test_the_captcha_finding_is_recorded_rather_than_worked_around(
        self, fetch_data: ModuleType
    ) -> None:
        substrate = next(s for s in fetch_data.SUBSTRATES if s.key == "federal-register")
        assert "CAPTCHA" in substrate.access_note
        assert "Do not defeat the CAPTCHA." in substrate.access_note

    def test_the_pin_note_explains_why_it_is_not_a_digest_of_the_bytes(
        self, fetch_data: ModuleType
    ) -> None:
        substrate = next(s for s in fetch_data.SUBSTRATES if s.key == "federal-register")
        assert "NORMALISED TEXT" in substrate.pin_note
        assert "PINNED_DOCUMENTS" in substrate.pin_note

    def test_the_fetched_text_may_not_ship(self, fetch_data: ModuleType) -> None:
        substrate = next(s for s in fetch_data.SUBSTRATES if s.key == "federal-register")
        assert substrate.vendorable is False


# ---------------------------------------------------------------------------
# what is deliberately not covered
# ---------------------------------------------------------------------------
class TestWhatIsNotTestedHere:
    """Named rather than left as an absence, because an absence looks like coverage."""

    def test_nothing_in_this_module_reaches_the_network(self) -> None:
        """The suite runs under an air-gap guard; this states the intent as well.

        Three behaviours are therefore unexercised and must be re-checked by hand
        when the substrate is next touched:

        * ``discover`` paging the API,
        * ``fetch --mirror-check`` agreeing with the Government Publishing Office,
        * ``select`` reporting drift when the population moves.

        The first two were verified live during this workstream, on every pinned
        document. The third has never fired, because the population has not moved
        yet -- which means the drift branch is written and unproven.
        """
        assert builder.FEDERAL_REGISTER_API.startswith("https://")
        assert builder.GOVINFO_MIRROR.startswith("https://")

    def test_the_external_proposer_is_not_exercised(self) -> None:
        """It needs an interpreter this suite cannot assume, so the pool runs without it.

        The consequence is that the *marginal contribution* of the third proposer
        -- the number that decides whether pooling three parenthesis scanners is
        worth the cost -- is measured only by running the tool, never by a test.
        """
        assert "pyab3p" in builder.EXTERNAL_SYSTEMS
        assert builder.EXTERNAL_SYSTEMS[0] == "pyab3p"
