#!/usr/bin/env python3
"""Measure the backronym subsystem — and say plainly what cannot be measured.

Four of the five subsystems `docs/ARCHITECTURE.md` dispatches to carry an
accuracy number. `BackronymGenerator` carries none, and
`docs/DEFINITION-OF-DONE.md` criterion 2 has been open on exactly that. This
runner closes the measurable half of it and refuses the other half out loud.

What a backronym number could be, and why one of them is not available
----------------------------------------------------------------------
Forward generation has a gold standard: a corpus of real (short form, long
form) pairs records what a human chose, so "did the system return it" is a
question a corpus answers. Backronym synthesis has no such thing. It is handed
a target word and asked to invent a phrase, and **no annotator has ever been
asked to judge whether an invented phrase is a good one**. There is no
published backronym gold, this project has not built one, and building one
would mean inventing the standard the system is then scored against.

So the candidate metrics split cleanly into two kinds, and keeping them apart
is the whole point of this file:

**PROPERTIES — checkable, and checked here.** They have a definite answer that
a verifier independent of the generator can compute from the input alone:

* *Constraint satisfaction.* Does every returned alignment actually satisfy the
  alignment constraint — letters in non-decreasing token order, strictly
  increasing offsets inside a shared token, every letter genuinely present at
  the offset claimed, every donated word an eligible token, the reported
  ``coverage`` equal to the arithmetic it claims to be? Re-derived here from
  the raw pair by :func:`constraint_violations`, which shares no code with the
  search.
* *Feasibility.* For what share of real pairs does the constraint admit a
  complete alignment **at all**? This is a fact about the corpus and the
  tokeniser, computed with no reference to any weight, and it is the ceiling
  that bounds everything the aligner can do.
* *Coverage.* What share of target letters were mapped, and what share could
  have been — printed in the same row, because a coverage figure without its
  ceiling is unreadable.
* *Vocabulary coverage.* For what share of real short forms can synthesis
  produce a complete expansion out of the shipped lexicon?

**QUALITY — not measured here, and not measurable without a judge.** Is the
phrase meaningful? Is it apt for the domain? Would a person prefer
``"timed artificial insemination"`` to ``"timed artificial artificial"``? Every
one of those needs a human (or a model standing in for one), and this project
has neither. Nothing below is a quality number and nothing below should be
quoted as one.

The tautology this file is written to avoid
-------------------------------------------
**A measurement that scores a generator against its own objective is a
tautology.** The aligner maximises ``S(A, T)``, and ``S`` already contains the
unmapped penalty — so "did it map the letters" is partly a restatement of what
it was told to do. Two devices keep the numbers honest:

1. **The oracle is independent.** Feasibility, the letter ceiling and
   underdetermination come from a two-pointer subsequence test over the
   concatenated eligible-token character stream. The alignment constraint
   (``t`` non-decreasing; ``o`` strictly increasing within a shared ``t``) is
   *exactly* strict increase in the lexicographic ``(t, o)`` order, so
   "a complete alignment exists" is "the target letters are a subsequence of
   that stream" — decided in one pass, with no weights, no search and no
   library code.

2. **Coverage is not the objective, and the shortfall is decomposed rather
   than reported as failure.** Leaving a letter unmapped costs
   ``unmapped_penalty``; stepping over a critical token costs ``delta``, which
   ships four times larger. So the objective sometimes *prefers* an incomplete
   alignment, and it is right to. ``bispectral index`` / ``BIS`` is the case:
   the oracle's complete reading takes ``b``, ``i``, ``s`` from inside
   ``bispectral`` and abandons ``index`` — and the aligner instead spends the
   ``S`` on covering both words and leaves one letter out. Every
   feasible-but-incomplete pair is therefore re-scored: the oracle's complete
   path is built with the library's own :func:`~acronymkit.scoring.Scorer` and
   compared to what was returned. A pair where the returned answer scores at
   least as high is ``objective_preferred``; one where the complete path scores
   strictly higher and was not found is ``search_shortfall`` — a real defect,
   because the search failed to reach a state it should have. That check runs
   on the library's own objective, so passing it says **the search works**, not
   that the answer is good. One caveat if it ever fires: the aligner considers
   at most ``_MAX_OFFSETS_PER_TOKEN`` occurrences of a letter inside one token
   and the oracle considers all of them, so a shortfall could be that
   documented bound rather than a search bug, and must be attributed before it
   is reported as one.

The oracle is also checked against the library rather than trusted. If the
oracle calls a pair infeasible and ``align`` returns a complete alignment for
it, one of the two is wrong and every row in the table is worthless;
``oracle_contradictions_n`` counts that case rather than skipping past it.

Where the inputs come from, and what they are not
-------------------------------------------------
Two corpora supply the **input distribution and nothing else**. Neither
supplies a gold answer for this task, because neither annotator was ever asked
one:

* **MED1250** — annotators marked abbreviation *definitions* in MEDLINE
  abstracts. The pairs are real; the alignment of letters onto words inside a
  pair was never annotated.
* **SDU@AAAI-21 AD ``diction.json``** — the shared task's inventory of legal
  expansions per acronym. Again real pairs, again no alignment.

Both are declared ``role = "tuning"`` and ``contaminated = true`` in
``bench/splits.toml`` and every figure here is labelled accordingly. That label
is weaker than usual for a reason worth stating rather than hiding: **these are
properties, not fitted decisions**, so there is no held-out split that would
make them more trustworthy — nothing here was tuned on anything. What the
label still buys is a reader who does not mistake the input distribution for a
blind one.

No held-out budget is spent. SDU-21 AD ``test.json``, SDU-22 legal
``train.json`` and SDU-22 scientific ``train.json`` are untouched; ``diction.json``
is the candidate inventory, not a split.

The trap next door
------------------
``bench/results.json`` already holds ``generation.med1250.dictionary_backronym``
and it is **not** a backronym measurement. It is forward generation —
long form in, acronym out, ranked against the human's choice — run under a
preset that happens to be named ``DICTIONARY_BACKRONYM``. Nothing in it calls
``align`` or ``synthesize``. It must never be quoted as this subsystem's number.

Usage::

    python bench/run_backronym.py                   # both arms, both corpora
    python bench/run_backronym.py --save            # record into bench/results.json
    python bench/run_backronym.py --examples        # show underdetermined readings
    python bench/run_backronym.py --corpus med1250  # one corpus
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit.backronym import BackronymGenerator  # noqa: E402
from acronymkit.config import Config  # noqa: E402
from acronymkit.models import BackronymCandidate, Token  # noqa: E402
from acronymkit.scoring import Scorer, build_mappings  # noqa: E402
from acronymkit.tokenizer import Tokenizer  # noqa: E402
from bench import corpora  # noqa: E402

#: One position in the character stream: ``(token index, offset, lowered char)``.
StreamPosition = Tuple[int, int, str]

#: A ``(short form, long form)`` pair, as the corpora supply it.
Pair = Tuple[str, str]

#: Input sources, keyed by the ``bench/splits.toml`` corpus name they draw from.
#: The key is the manifest name and not a reader name, because the run id is
#: built from it and a run id naming a corpus the manifest cannot resolve is a
#: figure exempt from the split rule by spelling.
SOURCES = ("med1250", "sdu21_ad")

#: How each source describes itself in the report. The distinction between a
#: corpus and the *file within it* that supplies these inputs is load-bearing:
#: ``sdu21_ad`` is a disambiguation corpus whose ``diction.json`` is a candidate
#: inventory, and reading its dev split instead would be a different measurement.
SOURCE_DESCRIPTION = {
    "med1250": "MED1250 gold definition pairs (Ab3P annotation)",
    "sdu21_ad": "SDU@AAAI-21 AD diction.json (acronym -> legal expansions)",
}

#: Subsets every arm is decomposed over. ``with_digit`` exists because a target
#: letter that is a digit is the single largest failure mode in both arms and
#: pooling it into ``all`` hides that behind an average -- operating rule 5.
SUBSETS = ("all", "alphabetic", "with_digit")

#: Alternatives requested from ``synthesize`` when counting how many distinct
#: expansions a target admits. Sized off nothing in particular: it is a
#: descriptive count, not a threshold anything depends on.
SYNTHESIS_ALTERNATIVES = 25

#: Alignments per pair pushed through the constraint verifier. The verifier is a
#: guard rather than a metric, so it is run over more than the top candidate:
#: a violation in a ranked-fifth alternative is still a violation, and the top
#: candidate is the one place a bug is least likely to hide.
VERIFY_DEPTH = 5

#: Why a pair admits no complete alignment, in **committed precedence order**.
#: Every infeasible pair is attributed to exactly one, first match wins, so the
#: counts partition rather than overlap:
#:
#: ``token_ineligible``
#:     A complete alignment exists over *all* tokens and does not exist over the
#:     eligible ones. The stop-word and minimum-length filters removed the
#:     donor. ``vitD <- "vitamin D"`` is the shape: ``D`` is a one-character
#:     token and one-character tokens are not eligible to donate.
#: ``digit_absent``
#:     Some digit of the target occurs nowhere in the phrase at all --
#:     ``T3 <- "triiodothyronine"``. Ranked above ``character_absent`` because
#:     it is the largest and most distinctive class, and a target character that
#:     is a digit is a different problem from a letter that is missing.
#: ``character_absent``
#:     Some non-digit character occurs nowhere in the phrase --
#:     ``DPH <- "phenytoin"``. Nothing about tokenisation or search can reach it.
#: ``out_of_order``
#:     Every character occurs, but not in the order the target needs --
#:     ``"FasL ICD" <- "intracellular FasL domain"``.
INFEASIBILITY_CAUSES = ("token_ineligible", "digit_absent", "character_absent", "out_of_order")


# ---------------------------------------------------------------------------
# the independent oracle
# ---------------------------------------------------------------------------
def canonical_letters(target: str) -> str:
    """Uppercase alphanumerics of ``target``, matching the library's canonical form.

    Duplicated deliberately rather than imported from
    ``acronymkit.backronym._target_letters``: the oracle must not share code
    with the thing it adjudicates, and a private helper is not a contract.
    ``tests/test_backronym.py`` asserts the two agree, so the duplication is
    checked rather than hoped for.

    Args:
        target: Raw target word.

    Returns:
        The canonical letter sequence.
    """
    return "".join(character for character in target.upper() if character.isalnum())


def character_stream(tokens: Sequence[Token]) -> List[StreamPosition]:
    """Every character an alignment may legally land on, in constraint order.

    The alignment constraint is: token indices non-decreasing, and offsets
    strictly increasing whenever two consecutive letters share a token. That is
    exactly strict increase in the lexicographic ``(token index, offset)``
    order, which is the order this list is in. So "a complete alignment exists"
    reduces to "the letters are a subsequence of this stream", and every oracle
    below is a two-pointer walk.

    Args:
        tokens: The full token sequence for the source phrase.

    Returns:
        ``(token index, offset, lowered character)`` for every character of
        every *eligible* token. Ineligible tokens (stop words, over-short
        words) donate nothing, exactly as the aligner treats them.
    """
    return [
        (position, offset, character.lower())
        for position, token in enumerate(tokens)
        if token.is_eligible
        for offset, character in enumerate(token.text)
    ]


def earliest_fit(letters: str, stream: Sequence[StreamPosition]) -> Optional[List[Tuple[int, int]]]:
    """The componentwise-earliest complete alignment, or ``None`` if none exists.

    Greedy earliest-fit is optimal for monotone subsequence matching: taking
    the first legal position for each letter never rules out a continuation
    that a later position would have allowed. So this both *decides*
    feasibility and returns the minimum feasible position for every letter.

    Args:
        letters: Canonical target letters.
        stream: Output of :func:`character_stream`.

    Returns:
        One ``(token index, offset)`` per letter, or ``None`` when the letters
        are not a subsequence of the stream.
    """
    chosen: List[Tuple[int, int]] = []
    cursor = 0
    for letter in letters:
        wanted = letter.lower()
        while cursor < len(stream) and stream[cursor][2] != wanted:
            cursor += 1
        if cursor == len(stream):
            return None
        chosen.append((stream[cursor][0], stream[cursor][1]))
        cursor += 1
    return chosen


def latest_fit(letters: str, stream: Sequence[StreamPosition]) -> Optional[List[Tuple[int, int]]]:
    """The componentwise-latest complete alignment, or ``None`` if none exists.

    The mirror of :func:`earliest_fit`, and the second half of the uniqueness
    test: since the two are the componentwise minimum and maximum over all
    feasible complete alignments, they agree on a letter exactly when every
    feasible alignment agrees on it.

    Args:
        letters: Canonical target letters.
        stream: Output of :func:`character_stream`.

    Returns:
        One ``(token index, offset)`` per letter, or ``None`` when infeasible.
    """
    chosen: List[Tuple[int, int]] = []
    cursor = len(stream) - 1
    for letter in reversed(letters):
        wanted = letter.lower()
        while cursor >= 0 and stream[cursor][2] != wanted:
            cursor -= 1
        if cursor < 0:
            return None
        chosen.append((stream[cursor][0], stream[cursor][1]))
        cursor -= 1
    return chosen[::-1]


def infeasibility_cause(letters: str, tokens: Sequence[Token]) -> str:
    """Why no complete alignment exists, under :data:`INFEASIBILITY_CAUSES` precedence.

    Called only for pairs :func:`earliest_fit` has already rejected over the
    eligible stream. The attribution is a decomposition of a ceiling, and a
    ceiling reported without one is a number nobody can act on.

    Args:
        letters: Canonical target letters.
        tokens: The full token sequence for the source phrase.

    Returns:
        One member of :data:`INFEASIBILITY_CAUSES`.
    """
    unfiltered = [
        (position, offset, character.lower())
        for position, token in enumerate(tokens)
        for offset, character in enumerate(token.text)
    ]
    if earliest_fit(letters, unfiltered) is not None:
        return "token_ineligible"
    present = {position[2] for position in unfiltered}
    missing = [letter for letter in letters if letter.lower() not in present]
    if any(letter.isdigit() for letter in missing):
        return "digit_absent"
    if missing:
        return "character_absent"
    return "out_of_order"


def longest_embeddable(letters: str, stream: Sequence[StreamPosition]) -> int:
    """How many target letters could be mapped at best, in order.

    The ceiling for :attr:`~acronymkit.models.BackronymCandidate.coverage` when
    a complete alignment does not exist. It is the length of the longest
    subsequence of ``letters`` that is itself a subsequence of the stream --
    an ordinary LCS, since a common subsequence of the two is exactly that.

    Args:
        letters: Canonical target letters.
        stream: Output of :func:`character_stream`.

    Returns:
        The bound, between ``0`` and ``len(letters)``.
    """
    previous = [0] * (len(stream) + 1)
    for letter in letters:
        wanted = letter.lower()
        current = [0] * (len(stream) + 1)
        for column, position in enumerate(stream, start=1):
            carried = previous[column - 1] + 1 if position[2] == wanted else 0
            current[column] = max(current[column - 1], previous[column], carried)
        previous = current
    return previous[-1]


def constraint_violations(
    letters: str, tokens: Sequence[Token], candidate: BackronymCandidate
) -> List[str]:
    """Re-derive the alignment constraint from the raw pair and report breaks.

    This is the "does every word start with the required letter, in order"
    check, stated exactly and widened to everything the payload asserts. It
    reads the candidate and the tokens and calls nothing in the search, so a
    bug in the search cannot make it agree.

    A non-empty result on real input would be a defect report. An empty one is
    a **guard passing**, not evidence of quality -- see the module docstring.

    Args:
        letters: Canonical target letters the candidate claims to spell.
        tokens: The token sequence the candidate was aligned against.
        candidate: One returned alignment.

    Returns:
        Human-readable violations, empty when the candidate is well formed.
    """
    broken: List[str] = []
    if candidate.target_word != letters:
        broken.append(f"target_word {candidate.target_word!r} != {letters!r}")
    if len(candidate.mappings) != len(letters):
        broken.append(f"{len(candidate.mappings)} mappings for {len(letters)} letters")
        return broken
    if len(candidate.expansion) != len(letters):
        broken.append(f"{len(candidate.expansion)} expansion slots for {len(letters)} letters")
        return broken

    previous: Optional[Tuple[int, int]] = None
    mapped = 0
    for position, mapping in enumerate(candidate.mappings):
        letter = letters[position]
        if mapping.character != letter:
            broken.append(f"letter {position}: mapping says {mapping.character!r}, not {letter!r}")
        if mapping.token_index is None:
            if candidate.expansion[position] != "":
                broken.append(f"letter {position}: unmapped but donates a word")
            if letter not in candidate.unmapped_letters:
                broken.append(f"letter {position}: unmapped but not recorded")
            previous = None
            continue

        mapped += 1
        if not 0 <= mapping.token_index < len(tokens):
            broken.append(f"letter {position}: token index {mapping.token_index} out of range")
            previous = None
            continue
        token = tokens[mapping.token_index]
        offset = mapping.char_offset
        if not token.is_eligible:
            broken.append(f"letter {position}: donated by ineligible token {token.text!r}")
        if offset is None or not 0 <= offset < len(token.text):
            broken.append(f"letter {position}: offset {offset} outside {token.text!r}")
        elif token.text[offset].lower() != letter.lower():
            broken.append(f"letter {position}: {letter!r} not at offset {offset} of {token.text!r}")
        if candidate.expansion[position] != token.text:
            broken.append(
                f"letter {position}: expansion says {candidate.expansion[position]!r}, "
                f"token is {token.text!r}"
            )
        if previous is not None and offset is not None:
            previous_token, previous_offset = previous
            if mapping.token_index < previous_token:
                broken.append(f"letter {position}: token order went backwards")
            elif mapping.token_index == previous_token and offset <= previous_offset:
                broken.append(f"letter {position}: offset did not increase inside one token")
        previous = (mapping.token_index, offset) if offset is not None else None

    expected = mapped / len(letters) if letters else 0.0
    if abs(candidate.coverage - expected) > 1e-9:
        broken.append(f"coverage {candidate.coverage} != {mapped}/{len(letters)}")
    return broken


# ---------------------------------------------------------------------------
# tallies
# ---------------------------------------------------------------------------
def _percentage(numerator: int, denominator: int) -> float:
    """``numerator / denominator`` as a percentage, or ``0.0`` on an empty denominator.

    A zero denominator is reported as ``0.0`` and never hidden: every entry
    written to ``bench/results.json`` carries the denominator beside the
    percentage, so a rate over nothing is visible as one rather than read as a
    measurement.
    """
    return round(numerator / denominator * 100, 2) if denominator else 0.0


@dataclass
class AlignmentTally:
    """Counters for one subset of one alignment arm."""

    pairs: int = 0
    verified: int = 0
    violating: int = 0
    feasible: int = 0
    complete: int = 0
    incomplete_feasible: int = 0
    objective_preferred: int = 0
    search_shortfall: int = 0
    underdetermined: int = 0
    oracle_contradictions: int = 0
    letters: int = 0
    letters_mapped: int = 0
    letters_reachable: int = 0
    causes: Counter = field(default_factory=Counter)

    def entry(self) -> Dict[str, object]:
        """The ``bench/results.json`` record for this subset.

        Every rate is written beside the count it was taken over, so a row
        whose denominator is zero -- ``with_digit`` on a corpus holding no
        digit targets -- reads as an empty row rather than as a score of zero.
        """
        return {
            "pairs": self.pairs,
            "alignments_verified": self.verified,
            "constraint_violations": self.violating,
            "validity_pct": _percentage(self.verified - self.violating, self.verified),
            "feasible_n": self.feasible,
            "feasible_pct": _percentage(self.feasible, self.pairs),
            "complete_n": self.complete,
            "complete_pct": _percentage(self.complete, self.pairs),
            "complete_of_feasible_pct": _percentage(self.complete, self.feasible),
            "incomplete_feasible_n": self.incomplete_feasible,
            "objective_preferred_n": self.objective_preferred,
            "search_shortfall_n": self.search_shortfall,
            "underdetermined_n": self.underdetermined,
            "underdetermined_pct": _percentage(self.underdetermined, self.feasible),
            "oracle_contradictions_n": self.oracle_contradictions,
            "letters": self.letters,
            "letter_coverage_pct": _percentage(self.letters_mapped, self.letters),
            "letter_ceiling_pct": _percentage(self.letters_reachable, self.letters),
            "infeasible_by_cause": {
                cause: self.causes.get(cause, 0) for cause in INFEASIBILITY_CAUSES
            },
        }


@dataclass
class SynthesisTally:
    """Counters for one subset of one synthesis arm."""

    targets: int = 0
    produced: int = 0
    complete: int = 0
    letters: int = 0
    letters_served: int = 0
    words: int = 0
    word_characters: int = 0
    wrong_initial: int = 0
    alternatives: int = 0
    duplicate_alternatives: int = 0

    def entry(self) -> Dict[str, object]:
        """The ``bench/results.json`` record for this subset.

        There is deliberately no mean-alternatives figure. ``synthesize``
        round-robins over per-letter lists whose length is the lexicon's, so
        every real target returns exactly ``limit`` alternatives and the mean
        measures the cap rather than the generator.

        ``word_length_mean`` is here because it is the one number that
        *describes* what the ranking key does without pretending to judge it:
        the key prefers 3-12 characters and then shorter before longer, so it
        settles on the alphabetically-first three-letter word for every letter.
        """
        return {
            "targets": self.targets,
            "produced_pct": _percentage(self.produced, self.targets),
            "complete_n": self.complete,
            "complete_pct": _percentage(self.complete, self.targets),
            "letters": self.letters,
            "letter_coverage_pct": _percentage(self.letters_served, self.letters),
            "words_checked": self.words,
            "wrong_initial_n": self.wrong_initial,
            "initial_constraint_pct": _percentage(self.words - self.wrong_initial, self.words),
            "word_length_mean": (
                round(self.word_characters / self.words, 2) if self.words else 0.0
            ),
            "alternatives_total": self.alternatives,
            "duplicate_alternatives_n": self.duplicate_alternatives,
            "distinct_alternatives_pct": _percentage(
                self.alternatives - self.duplicate_alternatives, self.alternatives
            ),
        }


def _subsets_for(letters: str) -> Tuple[str, ...]:
    """Which subsets a target belongs to: always ``all``, plus one of the other two."""
    return ("all", "with_digit" if any(c.isdigit() for c in letters) else "alphabetic")


# ---------------------------------------------------------------------------
# the arms
# ---------------------------------------------------------------------------
@dataclass
class AlignmentReport:
    """One corpus's alignment arm, decomposed."""

    corpus: str
    split_role: str
    source: str
    tallies: Dict[str, AlignmentTally]
    elapsed_seconds: float = 0.0
    violations: List[str] = field(default_factory=list)
    shortfalls: List[str] = field(default_factory=list)
    underdetermined_examples: List[Tuple[str, str, str, str]] = field(default_factory=list)

    def entry(self) -> Dict[str, object]:
        """The full ``bench/results.json`` record, subsets nested by name."""
        record: Dict[str, object] = {
            "corpus": self.corpus,
            "split_role": self.split_role,
            "input_source": self.source,
            "gold_supplies": "inputs only; no annotator judged an alignment",
            "elapsed_seconds": round(self.elapsed_seconds, 4),
        }
        for name in SUBSETS:
            record[name] = self.tallies[name].entry()
        return record


def measure_alignment(
    pairs: Sequence[Pair],
    *,
    corpus: str,
    source: str,
    config: Config,
    examples: int = 0,
) -> AlignmentReport:
    """Run the alignment arm over real ``(short form, long form)`` pairs.

    Args:
        pairs: The inputs. Nothing about them is treated as a gold answer.
        corpus: ``bench/splits.toml`` corpus name, used for the run id.
        source: Human-readable description of which file supplied the pairs.
        config: Engine configuration; supplies the tokeniser and the weights.
        examples: How many underdetermined readings to retain for ``--examples``.

    Returns:
        The decomposed report.
    """
    tokenizer = Tokenizer(config)
    scorer = Scorer(config)
    generator = BackronymGenerator(config, scorer)
    tallies = {name: AlignmentTally() for name in SUBSETS}
    report = AlignmentReport(
        corpus=corpus,
        split_role=corpora.label_for(corpus),
        source=source,
        tallies=tallies,
    )

    started = time.perf_counter()
    for short_form, long_form in pairs:
        letters = canonical_letters(short_form)
        if not letters:
            continue
        buckets = [tallies[name] for name in _subsets_for(letters)]
        tokens = tokenizer.tokenize(long_form)
        stream = character_stream(tokens)
        candidates = generator.align(short_form, tokens, limit=VERIFY_DEPTH)
        top = candidates[0] if candidates else None

        for bucket in buckets:
            bucket.pairs += 1
            bucket.letters += len(letters)
        for candidate in candidates:
            broken = constraint_violations(letters, tokens, candidate)
            for bucket in buckets:
                bucket.verified += 1
                bucket.violating += 1 if broken else 0
            if broken and len(report.violations) < 20:
                report.violations.append(f"{short_form!r} <- {long_form!r}: {'; '.join(broken)}")

        mapped = sum(1 for mapping in top.mappings if mapping.token_index is not None) if top else 0
        for bucket in buckets:
            bucket.letters_mapped += mapped

        earliest = earliest_fit(letters, stream)
        if earliest is None:
            reachable = longest_embeddable(letters, stream)
            cause = infeasibility_cause(letters, tokens)
            for bucket in buckets:
                bucket.letters_reachable += reachable
                bucket.causes[cause] += 1
                # The oracle says no complete alignment exists. If the library
                # returned one anyway, one of the two is wrong and the whole
                # table is worthless -- so it is counted rather than skipped.
                if top is not None and top.coverage == 1.0:
                    bucket.oracle_contradictions += 1
            if top is not None and top.coverage == 1.0 and len(report.violations) < 20:
                report.violations.append(
                    f"{short_form!r} <- {long_form!r}: oracle says infeasible, "
                    f"align returned a complete alignment"
                )
            continue

        latest = latest_fit(letters, stream)
        assert latest is not None  # feasible one way is feasible the other
        for bucket in buckets:
            bucket.feasible += 1
            bucket.letters_reachable += len(letters)

        # Compared on the WORDS read out, not on the token indices used: two
        # alignments that name the same words are the same answer to a caller.
        # That makes ``underdetermined`` a lower bound -- a pair whose two
        # extremes name the same words but whose middle does not is counted as
        # determined -- and the conservative direction is the right one for a
        # figure whose whole point is "here is what a judge would have to
        # settle".
        earliest_words = tuple(tokens[position].text for position, _ in earliest)
        latest_words = tuple(tokens[position].text for position, _ in latest)
        if earliest_words != latest_words:
            for bucket in buckets:
                bucket.underdetermined += 1
            if len(report.underdetermined_examples) < examples:
                report.underdetermined_examples.append(
                    (short_form, long_form, " ".join(earliest_words), " ".join(latest_words))
                )

        if top is not None and top.coverage == 1.0:
            for bucket in buckets:
                bucket.complete += 1
            continue

        # Feasible but incomplete: separate the objective's trade from a search
        # failure by scoring the oracle's complete path with the library's own
        # scorer. See the module docstring -- this is a search guard, and it
        # runs on the objective the search is given, so it cannot flatter the
        # answer's quality.
        assignments = [
            (position, token_index, offset)
            for position, (token_index, offset) in enumerate(earliest)
        ]
        mappings = build_mappings(letters, assignments, tokens, config.weights)
        complete_score = scorer.score(
            letters, tokens, mappings, {token_index for token_index, _ in earliest}
        ).total
        returned = top.score if top is not None else float("-inf")
        preferred = returned + 1e-9 >= complete_score
        for bucket in buckets:
            bucket.incomplete_feasible += 1
            if preferred:
                bucket.objective_preferred += 1
            else:
                bucket.search_shortfall += 1
        if not preferred and len(report.shortfalls) < 20:
            report.shortfalls.append(
                f"{short_form!r} <- {long_form!r}: returned {returned:.3f}, "
                f"complete path scores {complete_score:.3f}"
            )

    report.elapsed_seconds = time.perf_counter() - started
    return report


@dataclass
class SynthesisReport:
    """One corpus's synthesis arm, decomposed."""

    corpus: str
    split_role: str
    source: str
    tallies: Dict[str, SynthesisTally]
    unservable: Counter
    elapsed_seconds: float = 0.0
    examples: List[Tuple[str, str]] = field(default_factory=list)

    def entry(self) -> Dict[str, object]:
        """The full ``bench/results.json`` record, subsets nested by name."""
        record: Dict[str, object] = {
            "corpus": self.corpus,
            "split_role": self.split_role,
            "input_source": self.source,
            "gold_supplies": "target words only; no annotator judged a synthesis",
            "elapsed_seconds": round(self.elapsed_seconds, 4),
            "unservable_letters": dict(sorted(self.unservable.items())),
        }
        for name in SUBSETS:
            record[name] = self.tallies[name].entry()
        return record


def measure_synthesis(
    targets: Sequence[str],
    *,
    corpus: str,
    source: str,
    config: Config,
    examples: int = 0,
    vocabulary: Optional[Sequence[str]] = None,
) -> SynthesisReport:
    """Run the synthesis arm over real short forms and a word list.

    The only figure here that is not near-vacuous is coverage: whether the
    vocabulary can serve every letter of a real short form. ``initial_constraint_pct``
    is checked and reported because an unchecked guard is not a guard, and it is
    labelled in the report as what it is -- a property the construction makes
    true, whose value is that it would fire if the construction broke.

    Args:
        targets: Distinct short forms. Duplicates are removed by the caller so
            a frequent acronym does not weight the coverage figure.
        corpus: ``bench/splits.toml`` corpus name, used for the run id.
        source: Human-readable description of which file supplied the targets.
        config: Engine configuration; supplies the language and the lexicon.
        examples: How many synthesised expansions to retain for ``--examples``.
        vocabulary: Words to draw from. ``None`` -- what the CLI passes -- means
            the shipped lexicon for ``config.language``, which is what makes the
            coverage figure a statement about this package. The parameter exists
            because the figure is a property of *a* word list crossed with the
            target distribution, and a caller who cannot say which word list is
            quoting an unattributed number.

    Returns:
        The decomposed report.
    """
    generator = BackronymGenerator(config, Scorer(config))
    tallies = {name: SynthesisTally() for name in SUBSETS}
    report = SynthesisReport(
        corpus=corpus,
        split_role=corpora.label_for(corpus),
        source=source,
        tallies=tallies,
        unservable=Counter(),
    )

    started = time.perf_counter()
    for target in targets:
        letters = canonical_letters(target)
        if not letters:
            continue
        buckets = [tallies[name] for name in _subsets_for(letters)]
        for bucket in buckets:
            bucket.targets += 1
            bucket.letters += len(letters)

        candidates = generator.synthesize(
            target, vocabulary=vocabulary, limit=SYNTHESIS_ALTERNATIVES
        )
        if not candidates:
            continue
        best = candidates[0]
        served = len(letters) - len(best.unmapped_letters)
        seen = {candidate.expansion_text for candidate in candidates}
        for bucket in buckets:
            bucket.produced += 1
            bucket.letters_served += served
            bucket.alternatives += len(candidates)
            bucket.duplicate_alternatives += len(candidates) - len(seen)
            if not best.unmapped_letters:
                bucket.complete += 1
        for letter in best.unmapped_letters:
            report.unservable[letter] += 1
        for position, word in enumerate(best.expansion):
            if not word:
                continue
            for bucket in buckets:
                bucket.words += 1
                bucket.word_characters += len(word)
            if word[:1].lower() != letters[position].lower():
                for bucket in buckets:
                    bucket.wrong_initial += 1
        if len(report.examples) < examples:
            report.examples.append((target, best.expansion_text))

    report.elapsed_seconds = time.perf_counter() - started
    return report


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------
def load_pairs(corpus: str) -> List[Pair]:
    """Real ``(short form, long form)`` pairs from one declared corpus.

    Loading goes through ``bench.corpora``, so a corpus ``bench/splits.toml``
    does not declare fails here rather than producing a figure that is exempt
    from the split rule because nobody wrote the rule down for it.

    Args:
        corpus: A key of :data:`SOURCES`.

    Returns:
        The pairs, in corpus order.

    Raises:
        SystemExit: If ``corpus`` is not a known source.
    """
    if corpus == "med1250":
        return [
            (pair.short_form, pair.long_form)
            for document in corpora.load("med1250")
            for pair in document.pairs
        ]
    if corpus == "sdu21_ad":
        corpora.declaration("sdu21_ad")
        return [
            (acronym, expansion)
            for acronym, expansions in corpora.read_sdu21_ad_diction().items()
            for expansion in expansions
        ]
    raise SystemExit(f"unknown source {corpus!r}; expected one of {', '.join(SOURCES)}")


def distinct_targets(pairs: Sequence[Pair]) -> List[str]:
    """The distinct short forms of ``pairs``, sorted.

    Distinct rather than per-occurrence: synthesis takes a target word and
    nothing else, so scoring a frequent acronym once per definition would
    weight the coverage figure by how often a corpus happens to repeat it.
    """
    return sorted({short_form for short_form, _ in pairs})


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def environment() -> str:
    """One-line description of the machine, for the results table."""
    return f"Python {platform.python_version()} on {platform.system()} {platform.machine()}"


def save_results(entries: Dict[str, object]) -> Path:
    """Merge ``entries`` into ``bench/results.json``, the one file claims may cite.

    Args:
        entries: ``{run_id: {...measurements...}}``.

    Returns:
        Path to the results file.
    """
    path = REPO_ROOT / "bench" / "results.json"
    document = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"runs": {}}
    document.setdefault("runs", {}).update(entries)
    document["environment"] = environment()
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _worst(reports: Sequence[AlignmentReport], metric: str) -> Tuple[str, float]:
    """The lowest non-empty ``metric`` across every row of every alignment report."""
    rows = [
        (f"{report.corpus}/{name}", float(report.tallies[name].entry()[metric]))  # type: ignore[arg-type]
        for report in reports
        for name in SUBSETS
        if report.tallies[name].pairs
    ]
    return min(rows, key=lambda row: row[1]) if rows else ("none", 0.0)


def render_alignment(reports: Sequence[AlignmentReport]) -> str:
    """The alignment table, worst row included rather than appended."""
    header = (
        f"{'corpus / subset':<26} {'pairs':>7} {'feasible%':>10} {'complete%':>10} "
        f"{'of feas%':>9} {'letters%':>9} {'ceiling%':>9} {'undet%':>8}"
    )
    lines = [header, "-" * len(header)]
    for report in reports:
        for name in SUBSETS:
            tally = report.tallies[name]
            if not tally.pairs:
                lines.append(
                    f"{report.corpus + ' / ' + name:<26} {'0':>7}   (no rows in this subset)"
                )
                continue
            row = tally.entry()
            lines.append(
                f"{report.corpus + ' / ' + name:<26} {tally.pairs:>7,} "
                f"{row['feasible_pct']:>10.2f} {row['complete_pct']:>10.2f} "
                f"{row['complete_of_feasible_pct']:>9.2f} {row['letter_coverage_pct']:>9.2f} "
                f"{row['letter_ceiling_pct']:>9.2f} {row['underdetermined_pct']:>8.2f}"
            )
    name, value = _worst(reports, "complete_pct")
    lines += ["", f"worst complete% row: {name} at {value:.2f}"]
    lines += ["", "WHY THE CEILING IS WHERE IT IS -- one cause per pair, committed precedence"]
    causes_header = f"  {'corpus':<12} " + " ".join(
        f"{cause:>18}" for cause in INFEASIBILITY_CAUSES
    )
    lines += [causes_header, "  " + "-" * (len(causes_header) - 2)]
    for report in reports:
        tally = report.tallies["all"]
        counts = " ".join(f"{tally.causes.get(cause, 0):>18,}" for cause in INFEASIBILITY_CAUSES)
        lines.append(f"  {report.corpus:<12} {counts}")
    return "\n".join(lines)


def render_guards(reports: Sequence[AlignmentReport]) -> str:
    """The two guard results, with their firing counts.

    A guard reported without the number of times it could have fired is the
    defect ``docs/DECISIONS.md`` D-046 records: a criterion evaluated where the
    mechanism never fires tests the gate, not the thing.
    """
    lines = [
        "GUARDS (properties, not quality; a passing guard is not evidence of a good backronym)",
        "-" * 88,
    ]
    for report in reports:
        tally = report.tallies["all"]
        row = tally.entry()
        lines.append(
            f"  {report.corpus:<12} constraint satisfaction {row['validity_pct']:>7.2f} %  "
            f"over {tally.verified:,} alignments, {tally.violating} violating"
        )
        lines.append(
            f"  {'':<12} oracle agreement        "
            f"{_percentage(tally.pairs - tally.oracle_contradictions, tally.pairs):>7.2f} %  "
            f"over {tally.pairs:,} pairs, {tally.oracle_contradictions} contradicting"
        )
        if tally.incomplete_feasible:
            rate = _percentage(tally.objective_preferred, tally.incomplete_feasible)
            lines.append(
                f"  {'':<12} search optimality       {rate:>7.2f} %  "
                f"over {tally.incomplete_feasible} feasible-but-incomplete pairs "
                f"({tally.search_shortfall} shortfall)"
            )
        else:
            lines.append(
                f"  {'':<12} search optimality           n/a    "
                "FIRED ZERO TIMES on this corpus and adjudicates nothing here"
            )
    return "\n".join(lines)


def render_synthesis(reports: Sequence[SynthesisReport]) -> str:
    """The synthesis table, worst row included."""
    header = (
        f"{'corpus / subset':<26} {'targets':>9} {'produced%':>10} {'complete%':>10} "
        f"{'letters%':>9} {'distinct%':>10} {'word len':>9}"
    )
    lines = [header, "-" * len(header)]
    worst: Optional[Tuple[str, float]] = None
    for report in reports:
        for name in SUBSETS:
            tally = report.tallies[name]
            label = f"{report.corpus} / {name}"
            if not tally.targets:
                lines.append(f"{label:<26} {'0':>9}   (no rows in this subset)")
                continue
            row = tally.entry()
            lines.append(
                f"{label:<26} {tally.targets:>9,} {row['produced_pct']:>10.2f} "
                f"{row['complete_pct']:>10.2f} {row['letter_coverage_pct']:>9.2f} "
                f"{row['distinct_alternatives_pct']:>10.2f} {row['word_length_mean']:>9.2f}"
            )
            value = float(row["complete_pct"])  # type: ignore[arg-type]
            if worst is None or value < worst[1]:
                worst = (label, value)
    if worst is not None:
        lines += ["", f"worst complete% row: {worst[0]} at {worst[1]:.2f}"]
    for report in reports:
        if report.unservable:
            served = ", ".join(
                f"{letter!r}x{count}" for letter, count in sorted(report.unservable.items())
            )
            lines.append(f"  {report.corpus}: letters the lexicon cannot serve -> {served}")
        else:
            lines.append(f"  {report.corpus}: every letter of every target was served")
    lines += [
        "",
        "COVERAGE IS NOT QUALITY, and the alphabetic row is where that is easiest to see.",
        "Every letter served, every word a real dictionary word, every initial correct -- and",
        "the ranking key settles on the alphabetically-first short word each time. Run with",
        "--examples: 'ABC' comes back as 'aah baa cab'. No property below distinguishes that",
        "from a good backronym, and nothing here should be read as claiming otherwise.",
    ]
    return "\n".join(lines)


def render_preamble(config: Config) -> str:
    """What the numbers below are, stated before they are shown."""
    return "\n".join(
        [
            "BACKRONYM SUBSYSTEM -- properties and coverage, NOT accuracy",
            "=" * 88,
            f"environment : {environment()}",
            f"preset      : {config.scoring_strategy.value}",
            "",
            "No corpus in this project holds a gold backronym. Both inputs below supply real",
            "(short form, long form) pairs; NEITHER annotator was asked to judge an alignment or",
            "an invented phrase. So nothing here is an accuracy figure, and semantic coherence --",
            "is this a GOOD backronym -- is not measured, because measuring it needs a judge this",
            "project does not have. See docs/EVALUATION.md.",
            "",
            "generation.med1250.dictionary_backronym in bench/results.json is FORWARD GENERATION",
            "under a backronym-flavoured preset. It is not this subsystem's number.",
        ]
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--corpus",
        action="append",
        choices=SOURCES,
        help="repeatable; defaults to every source",
    )
    parser.add_argument("--examples", action="store_true", help="show sample readings")
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    args = parser.parse_args(argv)

    config = Config()
    sources = args.corpus or list(SOURCES)
    keep = 6 if args.examples else 0

    alignment: List[AlignmentReport] = []
    synthesis: List[SynthesisReport] = []
    for corpus in sources:
        pairs = load_pairs(corpus)
        description = SOURCE_DESCRIPTION[corpus]
        alignment.append(
            measure_alignment(
                pairs, corpus=corpus, source=description, config=config, examples=keep
            )
        )
        synthesis.append(
            measure_synthesis(
                distinct_targets(pairs),
                corpus=corpus,
                source=description,
                config=config,
                examples=keep,
            )
        )

    print(render_preamble(config))
    for report in alignment:
        print(f"\ninput: {report.corpus} -- {report.source} [{report.split_role}]")
    print("\nALIGNMENT (align): a fixed target onto a real expansion")
    print(render_alignment(alignment))
    print()
    print(render_guards(alignment))
    print("\nSYNTHESIS (synthesize): a target with no source phrase, from the shipped lexicon")
    print(render_synthesis(synthesis))

    for report in alignment:
        for line in report.violations:
            print(f"\nCONSTRAINT VIOLATION [{report.corpus}] {line}")
        for line in report.shortfalls:
            print(f"\nSEARCH SHORTFALL [{report.corpus}] {line}")

    if args.examples:
        print(
            "\nUNDERDETERMINED READINGS -- the constraint admits both, and choosing needs a judge"
        )
        print("-" * 88)
        for report in alignment:
            for short_form, long_form, first, second in report.underdetermined_examples:
                print(f"  [{report.corpus}] {short_form!r} <- {long_form!r}")
                print(f"      earliest reading: {first}")
                print(f"      latest reading  : {second}")
        print("\nSYNTHESISED EXPANSIONS -- unjudged, and shown so the reader can judge them")
        print("-" * 88)
        for report in synthesis:
            for target, text in report.examples:
                print(f"  [{report.corpus}] {target!r} -> {text!r}")

    if args.save:
        entries: Dict[str, object] = {}
        for report in alignment:
            entries[f"backronym.{report.corpus}.alignment"] = report.entry()
        for report in synthesis:
            entries[f"backronym.{report.corpus}.synthesis"] = report.entry()
        path = save_results(entries)
        print(f"\nsaved {len(entries)} run(s) to {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
