"""The extraction differential, pinned — including its capacity to go red.

``bench/run_scorer_differential.py`` publishes an agreement figure, and an
agreement figure is the single most dangerous kind of number a project can
publish: it is at its most reassuring exactly when the instrument is broken,
because a comparison that cannot separate anything reports perfect agreement.
So the tests that matter here are not the ones asserting the two scorers agree.
They are the ones asserting that they **stop** agreeing when either side is
perturbed.

What this file pins, and why each item is here
----------------------------------------------
* **The second scorer disagrees when the first one is changed.** Three
  mutations of ``bench/scoring.py``, one documented step of the convention each,
  plus one of the second scorer so the differential is shown symmetric. All four
  asserted red. Without them, ``verdicts_agreeing_on_counts ==
  verdicts_compared`` is a sentence about nothing.
* **And the fixture those mutations run on is required to be discriminating.**
  It must contain a true positive, a false positive and a false negative before
  any agreement over it is read. The first draft of it did not discriminate for
  the case-folding mutation, which passed while measuring nothing; that is why
  each record now carries a comment naming the decision it defends.
* **A no-op cannot enter the reader-mutation table.** Every expression in
  ``TEXT_MUTATIONS`` must change a sample string, or it would be counted as a
  mutation the comparison failed to catch.
* **The second scorer shares no code with the first.** Asserted by import
  inspection rather than by the module docstring's word, because "written
  independently" is precisely the claim a reader cannot check.
* **The reference-output parser reproduces this harness's document keys.**
  ``identify_abbr`` echoes its input, so the keys are derived from the same
  bare-PubMed-ID rule ``bench.corpora.read_med1250`` uses. If the two ever
  diverge the arm compares two different corpora and reports agreement on
  neither.
* **The SHA-256 pin is a pin.** A reference output nothing verifies is a
  reference that can be edited under the check that reads it.
* **A drifted record boundary is loud rather than silent.**
  ``scoring.evaluate`` ignores a prediction key it does not recognise, so a
  parser whose record rule drifted would score a subset and publish a plausible
  number. ``reference_records_match_reader`` is asserted capable of being false.
* **The vacuous half of the agreement is counted.** ``documents_vacuous`` plus
  ``documents_discriminating`` must exhaust the corpus, so a reader cannot take
  ``1252 of 1252`` for a discrimination that happened 1,252 times.
* **The runner is not reachable from the library** (R10).

Nothing here touches the network and nothing here needs ``data/``. Every
fixture is a literal.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "bench" / "run_scorer_differential.py"

# A GUARD, NOT A LINE IN ``EXPECTED_NON_PASSING``. The sdist ships ``bench/`` as
# a package directory and deliberately ships none of its modules, so the import
# below raises ``ImportError`` there and this file would fail to COLLECT. The
# condition named is exactly the one that differs, so any other error in this
# file still reaches the job. Same mechanism as ``tests/test_monoculture.py``.
if not RUNNER.is_file():  # pragma: no cover - installed/sdist runs only
    pytest.skip(
        "bench/run_scorer_differential.py is not part of an installed distribution",
        allow_module_level=True,
    )

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bench import corpora, scoring  # noqa: E402
from bench import run_scorer_differential as differential  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures: a four-record corpus with one of every awkward shape
# ---------------------------------------------------------------------------
def _document(uid: str, text: str, pairs: List[Tuple[str, str]]) -> corpora.GoldDocument:
    """One gold document from literals."""
    return corpora.GoldDocument(
        uid=uid,
        identifier=uid.split(":")[-1],
        text=text,
        pairs=tuple(corpora.GoldPair(short, long_form) for short, long_form in pairs),
    )


#: Each record exercises exactly one decision the convention has to make, and
#: the set is chosen so that **every** mutation below is discriminating on it.
#: The first two drafts of this fixture were not: dropping case folding changed
#: no verdict because no record differed in case, and the mutation test passed
#: while measuring nothing. That is the failure this file is about, committed
#: by the file itself, so the records are annotated with what each one defends.
DOCUMENTS = [
    # plain agreement -- the true positive every count needs
    _document("0000:1", "multiple sclerosis (MS) again", [("MS", "multiple sclerosis")]),
    # case: exact matching must fold, or this is a miss
    _document("0001:2", "Deoxyribonucleic Acid (DNA)", [("DNA", "Deoxyribonucleic Acid")]),
    # whitespace: exact matching must collapse runs
    _document("0002:3", "polymerase chain reaction (PCR)", [("PCR", "polymerase chain reaction")]),
    # leading determiner: relaxed matching must drop it, exact must not
    _document("0003:4", "the central nervous system (CNS)", [("CNS", "central nervous system")]),
    # edge punctuation: relaxed matching must trim it, exact must not
    _document("0004:5", "electrocardiogram (ECG),", [("ECG", "electrocardiogram")]),
    # a short form the annotator wrapped: relaxed does NOT reach it, by design
    _document("0005:6", "sulfhydryl compounds (-SH)", [("-SH", "sulfhydryl compounds")]),
    # the same pair defined twice: the record that makes the gold unreachable
    _document(
        "0006:7",
        "creatine kinase (CK) ... creatine kinase (CK)",
        [("CK", "creatine kinase"), ("CK", "creatine kinase")],
    ),
    # a pair no system found: the false negative
    _document("0007:8", "positron emission tomography (PET)", [("PET", "positron emission")]),
]

PREDICTIONS: Dict[str, List[Tuple[str, str]]] = {
    "0000:1": [("MS", "multiple sclerosis")],
    "0001:2": [("DNA", "deoxyribonucleic acid")],
    "0002:3": [("PCR", "polymerase  chain   reaction")],
    "0003:4": [("CNS", "the central nervous system")],
    "0004:5": [("ECG", "electrocardiogram,")],
    "0005:6": [("SH", "sulfhydryl compounds")],
    "0006:7": [("CK", "creatine kinase")],
    "0007:8": [("PET", "photon emission tomography")],
}


def _shipped(relaxed: bool) -> Tuple[int, int, int]:
    """``bench/scoring.py``'s verdict on the fixture."""
    evaluation = scoring.evaluate(DOCUMENTS, PREDICTIONS, corpus="fixture", system="fixture")
    score = evaluation.scores["relaxed" if relaxed else "exact"]
    return score.true_positives, score.false_positives, score.false_negatives


def _independent(relaxed: bool, **kwargs: object) -> Tuple[int, int, int]:
    """The second scorer's verdict on the same fixture."""
    return differential.independent_counts(
        DOCUMENTS,
        PREDICTIONS,
        relaxed=relaxed,
        **kwargs,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# the agreement, and then the mutations that break it
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("relaxed", [False, True])
def test_the_two_scorers_agree_on_the_fixture(relaxed: bool) -> None:
    """The differential's positive result, on a corpus small enough to read."""
    assert _independent(relaxed) == _shipped(relaxed)


@pytest.mark.parametrize("relaxed", [False, True])
def test_the_fixture_is_not_a_degenerate_agreement(relaxed: bool) -> None:
    """Both scorers must actually produce non-zero counts of all three kinds.

    An agreement over ``(0, 0, 0)`` is the failure this whole file exists to
    prevent, so the fixture is required to contain a true positive, a false
    positive and a false negative before any agreement over it is read.
    """
    assert all(count > 0 for count in _shipped(relaxed))


@pytest.mark.parametrize(
    ("attribute", "replacement", "reason"),
    [
        ("normalise_exact", str.strip, "case folding dropped from the exact convention"),
        ("normalise_relaxed", str.strip, "the whole relaxed convention dropped"),
        (
            "normalise_relaxed",
            lambda value: " ".join(value.split()).casefold(),
            "the relaxed convention weakened to the exact one",
        ),
    ],
)
def test_a_perturbed_first_scorer_is_detected(
    monkeypatch: pytest.MonkeyPatch, attribute: str, replacement: object, reason: str
) -> None:
    """Break one documented step of ``bench/scoring.py`` and the agreement must go.

    This is the R11 obligation discharged where the check runs: an agreement
    figure is evidence only once the comparison has been observed failing. Each
    row names the step it removes.
    """
    baseline = {relaxed: _shipped(relaxed) for relaxed in (False, True)}
    monkeypatch.setattr(scoring, attribute, replacement)
    disagreements = [
        relaxed
        for relaxed in (False, True)
        if _shipped(relaxed) != baseline[relaxed] and _independent(relaxed) == baseline[relaxed]
    ]
    assert disagreements, f"mutation not detected: {reason}"


def test_a_perturbed_second_scorer_is_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    """And the differential is symmetric: breaking the second side is caught too."""
    monkeypatch.setattr(differential, "_trim_edges", lambda text: text)
    assert _independent(True) != _shipped(True)


def test_the_second_scorer_shares_no_code_with_the_first() -> None:
    """The independence claim, checked rather than asserted in a docstring.

    ``bench/scoring``'s normalisers are the thing a lazy reimplementation would
    reuse, so the check is that this module's source never names them.
    """
    source = inspect.getsource(differential)
    body = source.split('"""', 2)[-1]
    for helper in ("normalise_exact", "normalise_relaxed", "_LEADING_NOISE", "_EDGE_PUNCT"):
        assert f"scoring.{helper}" not in body


# ---------------------------------------------------------------------------
# the convention's edges, where two readings of the same sentence diverge
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("the system", "system"),
        ("The System", "System"),
        ("the", "the"),  # a determiner with nothing after it is not a determiner
        ("thesis work", "thesis work"),
        ("a", "a"),
    ],
)
def test_only_a_determiner_followed_by_a_word_is_dropped(value: str, expected: str) -> None:
    """``_LEADING_NOISE`` requires ``\\s+``; so must the reimplementation."""
    assert differential._drop_determiner(value) == expected


def test_the_relaxed_convention_does_not_reach_the_short_form_by_default() -> None:
    """The shipped scorer's undocumented choice, pinned so a change is visible.

    ``bench/scoring.py`` documents the relaxed convention over the *long* form
    and applies the exact convention to the short form under both. The fixture's
    third record is the class that costs: gold ``-SH``, predicted ``SH``.
    """
    default = differential.independent_key(("-SH", "sulfhydryl compounds"), relaxed=True)
    reaching = differential.independent_key(
        ("-SH", "sulfhydryl compounds"), relaxed=True, relaxed_short_form=True
    )
    assert default != reaching
    assert default.split("\x00")[0] == "-sh"
    assert reaching.split("\x00")[0] == "sh"


# ---------------------------------------------------------------------------
# the reference output
# ---------------------------------------------------------------------------
#: One ``identify_abbr`` record verbatim in shape: the echoed input lines, then
#: two-space-indented ``sf|lf|precision`` lines under the line they were found
#: in. The second record has no abbreviation at all, which is the vacuous
#: majority of the real file.
REFERENCE_FIXTURE = "\n".join(
    [
        "12018411",
        "Comparison of two timed artificial insemination (TAI) protocols.",
        "  TAI|timed artificial insemination|0.999808",
        "Two estrus-synchronization programs were compared.",
        "",
        "3533522",
        "Characterization of rabbit uterine estrogen receptor proteins.",
        "Two estrogen binding proteins were purified.",
        "",
    ]
)


def test_reference_output_keys_match_this_harness(tmp_path: Path) -> None:
    """Record keys are ``position:identifier``, the way ``read_med1250`` builds them."""
    path = tmp_path / "identify_abbr-out"
    path.write_text(REFERENCE_FIXTURE, encoding="utf-8")
    parsed = differential.read_reference_output(path)
    assert list(parsed) == ["0000:12018411", "0001:3533522"]
    assert parsed["0000:12018411"] == [("TAI", "timed artificial insemination")]
    assert parsed["0001:3533522"] == []


def test_reference_output_ignores_unindented_pipe_lines(tmp_path: Path) -> None:
    """A pipe in the abstract is not a prediction.

    ``identify_abbr`` indents every abbreviation by exactly two spaces and
    echoes the input unindented. Dropping that requirement would harvest text
    as predictions, which is a failure that inflates agreement rather than
    breaking it.
    """
    path = tmp_path / "identify_abbr-out"
    path.write_text("99\nA sentence with a | in it.\n  SF|long form|0.9\n\n", encoding="utf-8")
    assert differential.read_reference_output(path) == {"0000:99": [("SF", "long form")]}


def test_a_drifted_record_boundary_is_visible_rather_than_silent() -> None:
    """The alignment field must go false when the keys stop matching.

    ``scoring.evaluate`` looks predictions up by uid and ignores a key it does
    not recognise, so a parser whose record rule drifted from the reader's would
    score a subset and report a plausible number. This is the field that catches
    that, and it is asserted capable of being false.
    """
    aligned = {document.uid: [] for document in DOCUMENTS}
    entry = differential.reference_output_arm(DOCUMENTS, aligned, interpreter=None)
    assert entry["reference_records_match_reader"] is True

    drifted = {f"9{uid[1:]}": pairs for uid, pairs in aligned.items()}
    entry = differential.reference_output_arm(DOCUMENTS, drifted, interpreter=None)
    assert entry["reference_records_match_reader"] is False


def test_a_missing_reference_output_says_how_to_get_one(tmp_path: Path) -> None:
    """The error names the command, because a runner that just raises is a puzzle."""
    with pytest.raises(SystemExit) as caught:
        differential.read_reference_output(tmp_path / "absent")
    assert "--fetch" in str(caught.value)


def test_the_sha256_pin_rejects_a_substituted_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The pin is a pin: a wrong payload must not be written to the cache."""

    class _Response:
        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self) -> bytes:
            return b"not the reference output"

    target = tmp_path / "identify_abbr-out"
    monkeypatch.setattr(differential, "REFERENCE_PATH", target)
    monkeypatch.setattr(differential.urllib.request, "urlopen", lambda *a, **k: _Response())
    with pytest.raises(SystemExit) as caught:
        differential.fetch_reference_output(refresh=True)
    assert differential.REFERENCE_SHA256 in str(caught.value)
    assert not target.exists()


# ---------------------------------------------------------------------------
# accounting
# ---------------------------------------------------------------------------
def test_the_vacuous_half_of_the_agreement_is_counted() -> None:
    """``discriminating + vacuous`` must exhaust the corpus.

    ``1252 of 1252 documents agree`` is a phrasing tighter than the measurement
    unless the count of records where both sides propose nothing sits beside
    it. This asserts the runner cannot publish the first without the second.
    """
    reference = {"0000:1": [("MS", "multiple sclerosis")], "0001:2": [], "0002:3": []}
    entry = differential.reference_output_arm(DOCUMENTS[:3], reference, interpreter=None)
    assert entry["documents_discriminating"] == 1
    assert entry["documents_vacuous"] == 2
    assert (
        int(entry["documents_discriminating"])  # type: ignore[call-overload]
        + int(entry["documents_vacuous"])  # type: ignore[call-overload]
        == entry["documents"]
    )
    assert entry["harness_comparison"] == "not run"


def test_synthetic_prediction_sets_are_labelled_not_hidden() -> None:
    """The controls count into the total and are named, so a reader can subtract."""
    systems = {name: dict(PREDICTIONS) for name in ("acronymkit", "empty", "gold_as_prediction")}
    entry = differential.scorer_agreement_arm(DOCUMENTS, systems)
    assert entry["verdicts_compared"] == 6
    assert entry["verdicts_from_extractors"] == 2
    assert set(entry["synthetic_prediction_sets"]) == {"empty", "gold_as_prediction"}  # type: ignore[arg-type]


def test_the_harness_ceiling_arm_finds_the_unreachable_gold() -> None:
    """One fixture record defines the same pair twice; one copy is unreachable."""
    from bench.run_extraction import dedupe_per_document

    gold_as_prediction = dedupe_per_document(
        {
            document.uid: [(pair.short_form, pair.long_form) for pair in document.pairs]
            for document in DOCUMENTS
        }
    )
    entry = differential.harness_ceiling_arm(DOCUMENTS, {"gold_as_prediction": gold_as_prediction})
    assert entry["gold_pairs"] == sum(len(document.pairs) for document in DOCUMENTS)
    assert entry["unreachable_pairs"] == 1
    assert entry["documents_affected"] == 1
    assert entry["max_precision_pct"] == 100.0
    assert entry["max_recall_pct"] < 100.0


# ---------------------------------------------------------------------------
# the mutation arm, which is the evidence that arm 1 can fail
# ---------------------------------------------------------------------------
SAMPLE = "Comparison of two timed artificial insemination (TAI) protocols."


@pytest.mark.parametrize("name", sorted(differential.TEXT_MUTATIONS))
def test_every_mutation_actually_mutates(name: str) -> None:
    """A no-op in the mutation table would report a detection it did not make.

    The table is Python expressions over ``text``, embedded verbatim in the
    child program. An expression that returns its input unchanged would produce
    ``0 documents differ`` -- which is what the *control* row means -- and be
    counted as a mutation the comparison failed to catch, or, worse, be read as
    the comparison being insensitive. So each one is required here to change a
    string that has all the features the corpus has.
    """
    mutated = eval(differential.TEXT_MUTATIONS[name], {"text": SAMPLE})
    assert isinstance(mutated, str)
    assert mutated != SAMPLE


@pytest.mark.parametrize("name", sorted(differential.TEXT_MUTATIONS))
def test_the_child_program_compiles_for_every_mutation(name: str) -> None:
    """The expression is embedded by string formatting; a bad one is a syntax error.

    Caught here rather than by a subprocess that returns a non-zero exit and an
    unattributable stderr in the middle of a benchmark run.
    """
    source = differential._CHILD_PROGRAM.format(
        repo=str(REPO_ROOT), expression=differential.TEXT_MUTATIONS[name]
    )
    compile(source, "<child>", "exec")


def test_the_mutation_arm_counts_a_missed_mutation_as_missed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutation that changes nothing must not be counted as detected.

    The arm's own failure mode: ``mutations_detected`` is the number that says
    the comparison works, so a bug that counted every row would make the
    instrument self-certifying.
    """
    reference = {"0000:1": [("MS", "multiple sclerosis")], "0001:2": []}

    def _fake(interpreter: str, *, mutation: object = None) -> object:
        return reference if mutation in (None, "casefold") else {"0000:1": [], "0001:2": []}

    monkeypatch.setattr(differential, "predict_pyab3p_out_of_process", _fake)
    monkeypatch.setattr(differential, "_interpreter_version", lambda _: "3.12.0")
    entry = differential.reference_mutation_arm("python", reference)
    differing = entry["documents_differing"]
    assert isinstance(differing, dict)
    assert differing["control"] == 0
    assert differing["casefold"] == 0
    assert entry["mutations_detected"] == entry["mutations_run"] - 1


# ---------------------------------------------------------------------------
# R10: a measuring instrument may not become a shipped code path
# ---------------------------------------------------------------------------
def test_the_library_cannot_reach_this_runner() -> None:
    """Nothing under ``src/acronymkit`` may name this module."""
    for path in (REPO_ROOT / "src" / "acronymkit").rglob("*.py"):
        assert "run_scorer_differential" not in path.read_text(encoding="utf-8")
