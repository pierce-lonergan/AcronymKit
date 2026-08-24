"""Contextual disambiguation of standalone acronyms -- the Tier 0/1 seam.

Purpose
-------
Given a bare short form (``"MS"``) and the sentence or paragraph it occurred in,
decide which expansion the author meant. :class:`LexicalDisambiguator` answers
that question with nothing but the standard library, ``pydantic`` and the other
``acronymkit`` modules: no embeddings, no model download, no network.

Why the signature matters
-------------------------
This module also *defines the contract* that the Phase 3 neural backend will
implement. A transformer/ONNX disambiguator selected by
:attr:`~acronymkit.enums.EngineTier.NEURAL` is expected to expose the very same
``disambiguate(acronym: str, context: str) -> DisambiguationResult`` method,
consume the same :class:`ExpansionDictionary`, and emit
:class:`~acronymkit.models.DisambiguationCandidate` records whose ``source`` is
``"neural"`` instead of ``"dictionary"``. Callers therefore never learn which
tier answered them, and swapping the backend is a construction-time decision
rather than an API change. Because Phase 3 is not implemented yet, requesting
:attr:`~acronymkit.enums.EngineTier.NEURAL` degrades to this lexical backend
with a warning, or raises
:class:`~acronymkit.exceptions.TierUnavailableError` when ``Config.strict`` is
set -- exactly the behaviour documented on the enum member itself.

Resolution strategy
-------------------
1. **Inline definition (authoritative).** The document is asked first: the
   Schwartz & Hearst extractor runs over ``context`` and, if it finds a
   parenthetical definition of this very acronym, that expansion is returned
   with ``score = 1.0`` and ``source = "inline"``. A document that defines its
   own abbreviation outranks any external dictionary, so ``1.0`` is *reserved*
   for this case and dictionary evidence is capped strictly below it
   (:data:`MAX_DICTIONARY_SCORE`).
2. **Dictionary scoring.** Every candidate expansion registered for the acronym
   is scored by the bounded blend documented on
   :meth:`LexicalDisambiguator.disambiguate` and in
   :data:`WEIGHT_OVERLAP` / :data:`WEIGHT_INITIALS` / :data:`WEIGHT_REGISTER`.

Saying "I don't know"
---------------------
:attr:`~acronymkit.models.DisambiguationResult.margin` -- the score gap between
the first and second candidate -- is reported on every result, and
:class:`LexicalDisambiguator` will refuse to answer below a margin the caller
names (``min_margin``). Four things about that are worth stating before anyone
builds on it, because the shape of this feature is easy to overstate.

**It is a dictionary-path instrument.** A margin needs two candidates. On the
engine's default path the candidate set is whatever the passage itself defined,
which is almost never more than one expansion, so ``margin`` is almost always
``None`` and the gate almost never fires. Supplying a dictionary is what makes
either of them mean anything. The measurement is
``disambiguation.sdu21.diagnosis.default_path`` in ``bench/results.json``.

**The gate is off by default, and stays off.** Turning it on would change
``primary_expansion`` from "always populated when candidates exist" to
"sometimes ``None``" for every existing caller, and it would do so to buy a
trade rather than an improvement: gating raises accuracy *among the questions
still answered* while lowering the number answered, which is a different
quantity from being right more often. The full coverage/accuracy curve, split
by candidate-set size and by whether the gold expansion's words are in the
sentence at all, is published under ``disambiguation.sdu21.abstention_curve``.
Every threshold in it comes from a split ``bench/splits.toml`` declares
``role = "tuning"``, so no value in it is a default this library may adopt --
it is a curve for a caller to choose a point on, against their own data.

**A margin is not a probability.** It is a difference of two unnormalised
blends, so it does not sum to anything and does not mean the same thing on a
two-way choice as on a fifteen-way one. The published curve is decomposed by
candidate-set size for exactly that reason, and the decomposition matters: at
the gate the run picks as its reference, the candidate-set sizes where the gate
still loses to a trivial frequency baseline account for about a third of the
split, and a pooled row would hide that.

**Read the baseline column before adopting a threshold.** The same run scores
the shared task's own most-frequent-expansion baseline on the very same
answered subset. Below the reference gate that baseline is *more* accurate
there, which means the gate was selecting easy questions rather than producing
good answers. This is the number that decides whether abstention is worth
anything to a caller who could instead supply expansion counts, and it is
reported beside every row rather than left for someone to think of.

Determinism
-----------
No randomness, no clock-dependent behaviour and no set-iteration order reaches
the output: candidates are sorted by ``(-score, expansion)``, evidence terms are
sorted and capped, and every score is rounded to
:data:`SCORE_PRECISION` decimal places so results are byte-stable across runs
and platforms.

Import policy
-------------
:class:`~acronymkit.tokenizer.Tokenizer` and
:class:`~acronymkit.extractor.AbbreviationExtractor` are imported at module
level. That is safe here because neither module imports this one -- the
dependency graph ``disambiguation -> {tokenizer, extractor} -> {config, enums,
models, stopwords}`` is acyclic -- and neither import performs I/O: resource
files are read when a :class:`~acronymkit.tokenizer.Tokenizer` is *constructed*,
which this module defers until the first call that actually needs one.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Optional, Sequence

from .config import Config, ScoringWeights
from .enums import EngineTier
from .exceptions import (
    ConfigurationError,
    LexiconError,
    ResourceNotFoundError,
    TierUnavailableError,
)
from .extractor import AbbreviationExtractor
from .models import (
    AcronymPair,
    DisambiguationCandidate,
    DisambiguationResult,
    EngineMetadata,
    Token,
)
from .tokenizer import Tokenizer

__all__ = ["ExpansionDictionary", "LexicalDisambiguator"]


# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

#: Weight of the context/expansion content-word overlap term. The dominant
#: signal: it is the only term that looks at what the surrounding text is
#: actually about.
WEIGHT_OVERLAP = 0.55

#: Weight of the initial-letter agreement term -- how well the acronym can be
#: *derived* from the expansion under the library's own omega schedule.
WEIGHT_INITIALS = 0.30

#: Weight of the orthographic register agreement term (proper-noun expansion in
#: a proper-noun context, or common-noun expansion in a common-noun context).
WEIGHT_REGISTER = 0.15

#: Similarity awarded when two words share a morphological stem
#: (``"spectrometry"`` / ``"spectrum"``). Below an exact match, well above any
#: sub-word resonance.
STEM_SIMILARITY = 0.75

#: Sub-word (character-bigram Dice) similarity is scaled by this factor so that
#: it can only ever break ties between candidates that agree on the stronger
#: signals; it can never outrank a stem or exact match.
SUBWORD_SCALE = 0.5

#: Shortest shared prefix that may count as a stem, in characters.
MIN_STEM_PREFIX = 4

#: A shared prefix must also cover this fraction of the shorter word, which
#: keeps ``"compound"`` / ``"computer"`` from looking related.
STEM_PREFIX_RATIO = 0.6

#: Similarity a context term must reach before it is reported as evidence.
EVIDENCE_MIN_SIMILARITY = 0.1

#: Upper bound on the number of evidence terms attached to one candidate.
MAX_EVIDENCE = 8

#: Score of an expansion defined inline by the document itself.
INLINE_SCORE = 1.0

#: Ceiling for dictionary-sourced scores. Strictly below :data:`INLINE_SCORE`,
#: so an inline definition always sorts first under the ``(-score, expansion)``
#: ordering without needing a special case in the sort key.
MAX_DICTIONARY_SCORE = 0.99

#: Decimal places every reported score is rounded to.
SCORE_PRECISION = 6

#: ``source`` values used by this backend. Phase 3 adds ``"neural"``.
SOURCE_INLINE = "inline"
SOURCE_DICTIONARY = "dictionary"

#: Warning emitted when EngineTier.NEURAL is requested without Config.strict.
_NEURAL_WARNING = (
    "EngineTier.NEURAL is reserved for the Phase 3 transformer backend and is "
    "not implemented yet; disambiguation degraded to the lexical backend."
)

#: Distributions that would satisfy the Phase 3 tier, for the strict-mode error.
_NEURAL_REQUIREMENTS = ("onnxruntime", "transformers")


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------


def _short_form_key(text: str) -> str:
    """Return the canonical index key for a short form.

    Uppercases and discards every non-alphanumeric character, so ``"N.A.S.A."``,
    ``"nasa"`` and ``"NASA"`` all address the same bucket.

    Args:
        text: Raw short form.

    Returns:
        The normalised key; ``""`` when ``text`` holds nothing alphanumeric.
    """
    return "".join(char for char in text if char.isalnum()).upper()


def _expansion_key(text: str) -> str:
    """Return the de-duplication key for an expansion string.

    Whitespace runs are collapsed and case is folded, so ``"Blood  pressure"``
    and ``"blood pressure"`` are recognised as the same expansion while the
    first-seen surface form is what gets stored.

    Args:
        text: Raw expansion string.

    Returns:
        The comparison key.
    """
    return " ".join(text.split()).casefold()


def _word_key(text: str) -> str:
    """Return the comparison form of a single word: alphanumerics, case-folded."""
    return "".join(char for char in text if char.isalnum()).casefold()


def _bigrams(word: str) -> frozenset[str]:
    """Return the set of character bigrams of ``word`` (empty below 2 characters)."""
    if len(word) < 2:
        return frozenset()
    return frozenset(word[index : index + 2] for index in range(len(word) - 1))


def _common_prefix_length(left: str, right: str) -> int:
    """Return the number of leading characters ``left`` and ``right`` share."""
    limit = min(len(left), len(right))
    index = 0
    while index < limit and left[index] == right[index]:
        index += 1
    return index


def _shares_stem(left: str, right: str) -> bool:
    """Report whether two words plausibly share a morphological stem.

    A shared prefix qualifies when it is at least :data:`MIN_STEM_PREFIX`
    characters long *and* covers at least :data:`STEM_PREFIX_RATIO` of the
    shorter word. That accepts ``"spectrometry"`` / ``"spectrum"`` and
    ``"lesion"`` / ``"lesions"`` while rejecting ``"compound"`` / ``"computer"``.

    Args:
        left: First word (comparison form).
        right: Second word (comparison form).

    Returns:
        ``True`` when the two words are treated as morphologically related.
    """
    shortest = min(len(left), len(right))
    if shortest < MIN_STEM_PREFIX:
        return False
    prefix = _common_prefix_length(left, right)
    return prefix >= MIN_STEM_PREFIX and prefix >= STEM_PREFIX_RATIO * shortest


def _word_similarity(expansion_word: str, context_word: str) -> float:
    """Return the graded similarity of two content words, in ``[0, 1]``.

    Three tiers, in decreasing strength:

    * ``1.0`` -- the words are identical;
    * :data:`STEM_SIMILARITY` -- they share a morphological stem
      (see :func:`_shares_stem`);
    * :data:`SUBWORD_SCALE` times the character-bigram Dice coefficient --
      a deliberately weak orthographic resonance that only ever breaks ties.

    Args:
        expansion_word: Content word taken from a candidate expansion.
        context_word: Content word taken from the surrounding context.

    Returns:
        The similarity in ``[0, 1]``.
    """
    if not expansion_word or not context_word:
        return 0.0
    if expansion_word == context_word:
        return 1.0
    if _shares_stem(expansion_word, context_word):
        return STEM_SIMILARITY
    left = _bigrams(expansion_word)
    right = _bigrams(context_word)
    if not left or not right:
        return 0.0
    shared = len(left & right)
    if not shared:
        return 0.0
    return SUBWORD_SCALE * (2.0 * shared / (len(left) + len(right)))


def _derivability(acronym_key: str, words: Sequence[str], weights: ScoringWeights) -> float:
    """Return how well ``acronym_key`` can be derived from ``words``, in ``[0, 1]``.

    A left-to-right alignment of the acronym characters onto the expansion's
    content words, credited with the library's own ``omega`` schedule
    (:class:`~acronymkit.config.ScoringWeights`): a character landing on a word
    *initial* earns ``initial_weight``, one continuing the previously matched
    word earns ``contiguous_weight`` when it is the immediately following
    character and ``internal_weight`` otherwise, and an unplaceable character
    earns nothing. Word initials are preferred whenever both are possible, and
    intervening words may be skipped (so ``"MS"`` still reads cleanly off
    ``"master of science"``).

    The total is normalised by ``len(acronym_key) * initial_weight``, i.e. by a
    perfect initialism, so ``"multiple sclerosis"`` scores ``1.0`` for ``"MS"``
    while ``"Microsoft"`` -- initial ``M`` plus an internal ``s`` -- scores
    ``(10 + 3) / 20 = 0.65`` under the default schedule.

    Args:
        acronym_key: Normalised acronym (see :func:`_short_form_key`).
        words: The expansion's content words, in order, in comparison form.
        weights: The active :class:`~acronymkit.config.ScoringWeights`.

    Returns:
        The normalised derivability in ``[0, 1]``; ``0.0`` when either input is
        empty.
    """
    initial_weight = float(weights.initial_weight)
    internal_weight = float(weights.internal_weight)
    contiguous_weight = float(weights.contiguous_weight)
    if not acronym_key or not words or initial_weight <= 0.0:
        return 0.0

    letters = acronym_key.casefold()
    total = 0.0
    active_word = -1  # word currently donating characters
    next_offset = 0  # offset just past the last matched character
    word_cursor = 0  # first word whose initial may still be used

    for letter in letters:
        internal_gain = 0.0
        internal_offset = -1
        if 0 <= active_word < len(words):
            position = words[active_word].find(letter, next_offset)
            if position >= 0:
                internal_offset = position
                internal_gain = contiguous_weight if position == next_offset else internal_weight
        initial_index = -1
        for index in range(word_cursor, len(words)):
            if words[index][:1] == letter:
                initial_index = index
                break

        if initial_index >= 0 and initial_weight >= internal_gain:
            total += initial_weight
            active_word = initial_index
            next_offset = 1
            word_cursor = initial_index + 1
        elif internal_offset >= 0:
            total += internal_gain
            next_offset = internal_offset + 1

    return max(0.0, min(1.0, total / (len(letters) * initial_weight)))


# ---------------------------------------------------------------------------
# Expansion dictionary
# ---------------------------------------------------------------------------


class ExpansionDictionary:
    """An index from a normalised short form to its candidate expansions.

    Keys are normalised by :func:`_short_form_key` (uppercased, non-alphanumeric
    characters removed) so ``"N.A.S.A."`` and ``"nasa"`` resolve to the same
    entry. Values keep the caller's original strings verbatim, de-duplicated
    case- and whitespace-insensitively, in insertion order -- the order a
    document introduced them is itself weak evidence, and preserving it keeps
    results reproducible.

    The dictionary is a plain mutable container: :meth:`add` mutates in place
    while :meth:`merge` is purely functional.

    Example:
        >>> index = ExpansionDictionary({"MS": ["multiple sclerosis", "Microsoft"]})
        >>> index.candidates("m.s.")
        ('multiple sclerosis', 'Microsoft')
        >>> len(index)
        1
    """

    __slots__ = ("_entries",)

    def __init__(self, mapping: Optional[Mapping[str, Sequence[str]]] = None) -> None:
        """Build an index.

        Args:
            mapping: Optional ``{short_form: [expansion, ...]}`` seed. A bare
                string value is accepted as a single expansion.

        Raises:
            LexiconError: If a value is neither a string nor a sequence of
                strings.
        """
        self._entries: dict[str, list[str]] = {}
        if mapping:
            for short_form, expansions in mapping.items():
                for expansion in _coerce_expansions(short_form, expansions):
                    self.add(short_form, expansion)

    # -- construction ------------------------------------------------------
    @classmethod
    def from_pairs(cls, pairs: Iterable[AcronymPair]) -> ExpansionDictionary:
        """Build an index from extractor output.

        This is how a document teaches the disambiguator its own local
        vocabulary: run :class:`~acronymkit.extractor.AbbreviationExtractor`
        over the corpus, feed the pairs in here, and every abbreviation the
        corpus defined becomes a candidate everywhere else it is used.

        Args:
            pairs: :class:`~acronymkit.models.AcronymPair` records, in document
                order.

        Returns:
            A new dictionary; document order is preserved per short form.
        """
        index = cls()
        for pair in pairs:
            index.add(pair.short_form, pair.long_form)
        return index

    @classmethod
    def from_json(cls, path: Path) -> ExpansionDictionary:
        """Load an index from a JSON file.

        The document must be a single object mapping short forms to expansions::

            {"NASA": ["National Aeronautics and Space Administration"],
             "MS": ["multiple sclerosis", "Microsoft"]}

        A bare string value is accepted as a one-element list.

        Args:
            path: Path to the JSON document.

        Returns:
            The loaded dictionary.

        Raises:
            ResourceNotFoundError: If ``path`` does not exist or cannot be read.
            LexiconError: If the document is not valid JSON, is not an object,
                or holds a value that is not a string or a sequence of strings.
        """
        source = Path(path)
        try:
            raw = source.read_text(encoding="utf-8")
        except OSError as exc:
            raise ResourceNotFoundError(
                f"Expansion dictionary {str(source)!r} could not be read: {exc}"
            ) from exc
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise LexiconError(
                f"Expansion dictionary {str(source)!r} is not valid JSON: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise LexiconError(
                f"Expansion dictionary {str(source)!r} must contain a JSON object "
                f"mapping short forms to expansions, got {type(payload).__name__}"
            )
        index = cls()
        for short_form, expansions in payload.items():
            if not isinstance(short_form, str):  # pragma: no cover - JSON keys are str
                raise LexiconError(
                    f"Expansion dictionary {str(source)!r} has a non-string key {short_form!r}"
                )
            for expansion in _coerce_expansions(short_form, expansions, source=str(source)):
                index.add(short_form, expansion)
        return index

    # -- mutation ----------------------------------------------------------
    def add(self, short_form: str, expansion: str) -> None:
        """Register one expansion for one short form.

        Blank short forms and blank expansions are ignored, and an expansion
        already present for this short form (compared case- and
        whitespace-insensitively) is not stored twice.

        Args:
            short_form: The abbreviation; normalised into the index key.
            expansion: The expansion string, stored verbatim.
        """
        key = _short_form_key(short_form)
        if not key or not expansion or not expansion.strip():
            return
        bucket = self._entries.setdefault(key, [])
        candidate = _expansion_key(expansion)
        if any(_expansion_key(existing) == candidate for existing in bucket):
            return
        bucket.append(expansion)

    # -- queries -----------------------------------------------------------
    def candidates(self, short_form: str) -> tuple[str, ...]:
        """Return the registered expansions of ``short_form`` in insertion order.

        Args:
            short_form: The abbreviation, in any case or punctuation style.

        Returns:
            The expansions verbatim; an empty tuple when the short form is
            unknown.
        """
        return tuple(self._entries.get(_short_form_key(short_form), ()))

    def merge(self, other: ExpansionDictionary) -> ExpansionDictionary:
        """Return a new dictionary holding the entries of both operands.

        Neither operand is mutated. ``self``'s expansions come first for every
        short form, then ``other``'s, with duplicates dropped.

        Args:
            other: The dictionary to merge in.

        Returns:
            A new :class:`ExpansionDictionary`.

        Raises:
            TypeError: If ``other`` is not an :class:`ExpansionDictionary`.
        """
        if not isinstance(other, ExpansionDictionary):
            raise TypeError(f"merge() expects an ExpansionDictionary, got {type(other).__name__}")
        merged = ExpansionDictionary()
        for source in (self, other):
            for key, expansions in source._entries.items():
                for expansion in expansions:
                    merged.add(key, expansion)
        return merged

    def to_dict(self) -> dict[str, list[str]]:
        """Return a plain ``{normalised_short_form: [expansion, ...]}`` copy."""
        return {key: list(values) for key, values in self._entries.items()}

    def items(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """Return ``(short_form, expansions)`` pairs in insertion order."""
        return tuple((key, tuple(values)) for key, values in self._entries.items())

    def __len__(self) -> int:
        """Return the number of distinct short forms indexed."""
        return len(self._entries)

    def __contains__(self, key: object) -> bool:
        """Report whether a short form (in any case/punctuation) is indexed."""
        if not isinstance(key, str):
            return False
        return _short_form_key(key) in self._entries

    def __iter__(self) -> Iterator[str]:
        """Iterate the normalised short forms in insertion order."""
        return iter(self._entries)

    def __repr__(self) -> str:  # pragma: no cover - display helper
        total = sum(len(values) for values in self._entries.values())
        return f"ExpansionDictionary({len(self._entries)} short forms, {total} expansions)"


def _coerce_expansions(
    short_form: object, expansions: object, *, source: Optional[str] = None
) -> tuple[str, ...]:
    """Normalise a raw dictionary value into a tuple of expansion strings.

    Args:
        short_form: The key the value belongs to, for error messages.
        expansions: A string, or any non-string iterable of strings.
        source: Optional resource name, included in error messages.

    Returns:
        The expansions, in order.

    Raises:
        LexiconError: If the value is neither a string nor a sequence of
            strings.
    """
    where = f" in {source!r}" if source else ""
    if isinstance(expansions, str):
        return (expansions,)
    if isinstance(expansions, (list, tuple)):
        for item in expansions:
            if not isinstance(item, str):
                raise LexiconError(
                    f"Expansions for {short_form!r}{where} must all be strings; "
                    f"got {type(item).__name__}"
                )
        return tuple(expansions)
    raise LexiconError(
        f"Expansions for {short_form!r}{where} must be a string or a list of "
        f"strings, got {type(expansions).__name__}"
    )


def _below_gate(result: DisambiguationResult, min_margin: float) -> bool:
    """Whether ``result`` fails the abstention gate at ``min_margin``.

    Reads the *published*
    :attr:`~acronymkit.models.DisambiguationResult.margin` rather than
    recomputing the subtraction, so the field a caller inspects and the field
    the gate acts on cannot drift apart.

    Two cases are exempt, and both are exemptions from a *comparison that has no
    content*, not softenings of the policy:

    * **Fewer than two candidates.** No margin was computed because no rival
      existed. Gating here would refuse most of the engine's default path, where
      one inline definition is the usual outcome.
    * **The top two come from different sources.** Today that means an inline
      definition sitting above dictionary candidates, and the gap between them
      is bounded by ``INLINE_SCORE - MAX_DICTIONARY_SCORE`` -- a cap this module
      chose so an inline definition always sorts first, not a measurement of how
      much better it is. A dictionary candidate that scores at the cap, which is
      what an expansion whose every word is in the sentence does, would drive
      that gap to its floor and make any gate above it refuse the document's own
      definition of its own abbreviation. The exemption can only ever turn a
      refusal into an answer, never the reverse, because it is skipped exactly
      when the winner outranks the runner-up by construction.

      **This rests on there being exactly two sources.** With
      :data:`SOURCE_INLINE` capped above :data:`SOURCE_DICTIONARY`, "the top two
      differ in source" implies "the winner is an inline definition". The Phase
      3 ``"neural"`` source has no such ordering against either, so when it
      lands this exemption must be re-derived rather than inherited: a
      neural/dictionary pair one point apart is a close call, not an artifact.

    Args:
        result: The result to test.
        min_margin: The gate, already validated.

    Returns:
        ``True`` when the answer should be withheld.
    """
    margin = result.margin
    if margin is None:
        return False
    if result.candidates[0].source != result.candidates[1].source:
        return False
    return margin < min_margin


def _validated_min_margin(value: Optional[float]) -> Optional[float]:
    """Return ``value`` as a usable abstention gate, or raise.

    Args:
        value: The caller's ``min_margin``.

    Returns:
        ``None`` for "no gate", otherwise the threshold as a ``float``.

    Raises:
        ConfigurationError: If ``value`` is not a real number in ``[0, 1]``.
            ``bool`` is refused too: ``min_margin=True`` would otherwise mean
            "abstain unless the margin is a full point", which is not what
            anybody writing it meant.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(
            f"min_margin must be a number in [0.0, {INLINE_SCORE}] or None, not {value!r}"
        )
    numeric = float(value)
    if not 0.0 <= numeric <= INLINE_SCORE:
        raise ConfigurationError(
            f"min_margin={numeric!r} is outside [0.0, {INLINE_SCORE}]; a score gap cannot "
            "exceed the inline-definition score, so this gate would abstain on every input"
        )
    return numeric


# ---------------------------------------------------------------------------
# Lexical disambiguator
# ---------------------------------------------------------------------------


class LexicalDisambiguator:
    """Tier 0/1 disambiguation seam.

    Resolves a standalone acronym against its context using inline definitions
    and lexical evidence only. The Tier 2 neural backend planned for Phase 3
    will implement the same :meth:`disambiguate` signature and be selected by
    :attr:`~acronymkit.enums.EngineTier.NEURAL`; until it exists, requesting
    that tier degrades here (with a warning) or raises under ``Config.strict``.

    Instances are cheap to build -- the tokenizer and extractor are constructed
    on first use -- and hold no per-call state, so one may be shared across
    threads.

    Example:
        >>> from acronymkit.config import Config
        >>> index = ExpansionDictionary({"BP": ["blood pressure"]})
        >>> engine = LexicalDisambiguator(Config(), index)
        >>> result = engine.disambiguate("BP", "Blood pressure (BP) was elevated.")
        >>> result.primary_expansion
        'Blood pressure'
        >>> result.candidates[0].source
        'inline'
    """

    __slots__ = ("_config", "_dictionary", "_extractor", "_min_margin", "_tokenizer", "_warnings")

    def __init__(
        self,
        config: Config,
        dictionary: Optional[ExpansionDictionary] = None,
        tokenizer: Optional[Tokenizer] = None,
        *,
        min_margin: Optional[float] = None,
    ) -> None:
        """Build a disambiguator.

        Args:
            config: Engine configuration. ``language`` selects the stop-word
                resource used to build both word bags, ``weights`` supplies the
                omega schedule behind the initial-letter term, and
                ``engine_tier``/``strict`` govern the Phase 3 degradation.
            dictionary: Expansion index. An empty one is used when omitted, in
                which case only inline definitions can resolve.
            tokenizer: Pre-built tokenizer to reuse. One is constructed lazily
                from ``config`` when omitted.
            min_margin: Abstention gate. ``None``, the default, disables it
                entirely and is why this parameter breaks nothing. Given a
                number in ``[0.0, 1.0]``, an answer is returned only when
                :attr:`~acronymkit.models.DisambiguationResult.margin` is at
                least that large; otherwise ``primary_expansion`` comes back
                ``None`` with ``abstained`` set and the ranked ``candidates``
                still attached, so the caller can see what was refused. The
                comparison is ``margin >= min_margin``, which makes the
                parameter the same quantity as the ``gate_*`` rows of
                ``disambiguation.sdu21.abstention_curve``. Two candidate sets
                are never refused and :func:`_below_gate` says why: one with no
                second candidate, and one whose top two come from different
                sources, where the gap is fixed by
                ``INLINE_SCORE - MAX_DICTIONARY_SCORE`` rather than measured.

        Raises:
            TierUnavailableError: If ``config.engine_tier`` is
                :attr:`~acronymkit.enums.EngineTier.NEURAL` and ``config.strict``
                is set: the Phase 3 backend does not exist yet, and strict mode
                forbids silent degradation.
            ConfigurationError: If ``min_margin`` is not ``None`` and is not a
                real number in ``[0.0, 1.0]``. A margin cannot exceed
                :data:`INLINE_SCORE`, so a threshold above it would abstain on
                everything for ever, and silently doing that is the failure this
                refusal exists to prevent.

        Note:
            **Why the gate is opt-in and not on by default.** Defaulting it on
            would break every caller that treats ``primary_expansion`` as
            populated whenever ``candidates`` is non-empty, and it would pick a
            threshold on their behalf out of a curve measured on one tuning
            split of one corpus in one domain. There is no threshold this
            library can defend as *theirs*: the curve is a coverage/accuracy
            trade, and where a caller wants to sit on it is a property of what
            they do with a refusal, which the library cannot see. So the library
            reports the margin, publishes the curve, and leaves the choice
            where the information is.
        """
        self._config = config
        self._dictionary = dictionary if dictionary is not None else ExpansionDictionary()
        self._tokenizer = tokenizer
        self._extractor: Optional[AbbreviationExtractor] = None
        self._min_margin = _validated_min_margin(min_margin)
        self._warnings: tuple[str, ...] = ()
        if config.engine_tier is EngineTier.NEURAL:
            if config.strict:
                raise TierUnavailableError(EngineTier.NEURAL, _NEURAL_REQUIREMENTS, "transformers")
            self._warnings = (_NEURAL_WARNING,)

    # -- properties --------------------------------------------------------
    @property
    def config(self) -> Config:
        """The configuration this disambiguator was built from."""
        return self._config

    @property
    def dictionary(self) -> ExpansionDictionary:
        """The expansion index consulted for dictionary-sourced candidates."""
        return self._dictionary

    @property
    def min_margin(self) -> Optional[float]:
        """The abstention gate this disambiguator was built with, or ``None``."""
        return self._min_margin

    @property
    def tokenizer(self) -> Tokenizer:
        """The tokenizer, constructed on first access."""
        if self._tokenizer is None:
            self._tokenizer = Tokenizer(self._config)
        return self._tokenizer

    @property
    def extractor(self) -> AbbreviationExtractor:
        """The inline-definition extractor, constructed on first access."""
        if self._extractor is None:
            self._extractor = AbbreviationExtractor(self._config, self.tokenizer)
        return self._extractor

    # -- public API --------------------------------------------------------
    def disambiguate(self, acronym: str, context: str) -> DisambiguationResult:
        """Resolve ``acronym`` to its most likely expansion given ``context``.

        Resolution proceeds in two stages.

        **1. Inline definition.** The Schwartz & Hearst extractor runs over
        ``context``. Any parenthetical definition of this acronym scores
        :data:`INLINE_SCORE` (``1.0``) with ``source = "inline"`` and wins
        outright: dictionary scores are capped at :data:`MAX_DICTIONARY_SCORE`,
        so no external candidate can tie with the document's own definition.

        **2. Dictionary scoring.** Every registered expansion is scored by the
        bounded blend::

            score = 0.55 * overlap + 0.30 * initials + 0.15 * register

        each term lying in ``[0, 1]``, so the blend does too:

        ``overlap`` (:data:`WEIGHT_OVERLAP`)
            Content-word agreement between the context bag and the expansion
            bag. Both bags are produced by the configured
            :class:`~acronymkit.tokenizer.Tokenizer`, so stop words are excluded
            from both, comparison is case-folded, and the acronym itself is
            removed from the context bag. The term is the *mean* over the
            expansion's words of that word's best similarity against any
            context word (:func:`_word_similarity`: ``1.0`` exact,
            :data:`STEM_SIMILARITY` for a shared stem, and a
            :data:`SUBWORD_SCALE`-damped character-bigram Dice otherwise).
            Averaging over the expansion's own length is what bounds it at
            ``1.0`` regardless of how long the context is.
        ``initials`` (:data:`WEIGHT_INITIALS`)
            Does the expansion's content-word initial sequence actually spell
            the acronym? Scored by :func:`_derivability`, which credits word
            initials with ``ScoringWeights.initial_weight`` and characters found
            inside a word with the internal/contiguous weights, normalised by a
            perfect initialism. A true initialism scores ``1.0``; a compound
            such as ``"Microsoft"`` for ``"MS"`` scores ``0.65`` under the
            default 10/3/2 schedule rather than being rejected outright.
        ``register`` (:data:`WEIGHT_REGISTER`)
            Orthographic agreement: ``1.0`` when a capitalised (proper-noun)
            expansion meets a context that itself uses proper nouns -- a
            non-sentence-initial title-case word that is neither the acronym nor
            another all-caps abbreviation -- or when a lower-case expansion
            meets a context without them; ``0.0`` on a mismatch. This term only
            discriminates when the dictionary itself distinguishes proper nouns
            by capitalisation, and it is deliberately the smallest weight.

        Candidates are sorted by ``(-score, expansion)``, so ties are
        alphabetical and reproducible, and each carries up to
        :data:`MAX_EVIDENCE` sorted context terms that drove its overlap.

        **3. Abstention, when asked for.** The gap between the first and second
        candidate is reported as
        :attr:`~acronymkit.models.DisambiguationResult.margin`, always, at no
        cost and with no policy attached. If this disambiguator was built with
        ``min_margin``, a result whose margin falls below it comes back with
        ``primary_expansion = None``, ``abstained = True`` and its ranked
        ``candidates`` intact. A result with fewer than two candidates has no
        margin and is never gated, and neither is one whose top two candidates
        come from different sources -- an inline definition beaten down to a
        ``0.01`` gap by a dictionary candidate at the cap is an artifact of the
        cap, not a close call. :func:`_below_gate` states both exemptions.

        Args:
            acronym: The short form to resolve, in any case or punctuation
                style.
            context: Surrounding text. May be empty.

        Returns:
            A :class:`~acronymkit.models.DisambiguationResult` whose
            ``primary_expansion`` is the highest-scoring expansion; ``None``
            when neither an inline definition nor a dictionary entry exists, and
            ``None`` with ``abstained`` set when ``min_margin`` declined the
            top candidate. The result always carries valid metadata.

        Example:
            One gate, two outcomes. A sentence with nothing to go on is refused
            with its candidates still visible; a sentence that defines the
            abbreviation itself is answered.

            >>> from acronymkit.config import Config
            >>> index = ExpansionDictionary(
            ...     {"BP": ["blood pressure", "boiling point", "British Petroleum"]}
            ... )
            >>> picky = LexicalDisambiguator(Config(), index, min_margin=0.10)
            >>> refused = picky.disambiguate("BP", "The reading was taken twice.")
            >>> refused.primary_expansion is None, refused.abstained
            (True, True)
            >>> [candidate.expansion for candidate in refused.candidates]
            ['boiling point', 'blood pressure', 'British Petroleum']
            >>> answered = picky.disambiguate("BP", "Blood pressure (BP) was elevated.")
            >>> answered.primary_expansion, answered.abstained
            ('Blood pressure', False)
        """
        started = time.perf_counter()
        acronym_key = _short_form_key(acronym)
        tokens = self.tokenizer.tokenize(context) if context and context.strip() else []

        candidates: list[DisambiguationCandidate] = []
        if acronym_key:
            context_terms = self._context_terms(tokens, acronym_key)
            seen: set[str] = set()
            for expansion, evidence in self._inline_expansions(acronym_key, context):
                key = _expansion_key(expansion)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    DisambiguationCandidate(
                        expansion=expansion,
                        score=INLINE_SCORE,
                        source=SOURCE_INLINE,
                        evidence=evidence,
                    )
                )
            context_is_proper = self._context_is_proper(context, tokens, acronym_key)
            for expansion in self._dictionary.candidates(acronym_key):
                key = _expansion_key(expansion)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    self._score_expansion(acronym_key, expansion, context_terms, context_is_proper)
                )

        candidates.sort(key=lambda candidate: (-candidate.score, candidate.expansion))
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        result = DisambiguationResult(
            acronym=acronym,
            context=context,
            primary_expansion=candidates[0].expansion if candidates else None,
            candidates=candidates,
            metadata=self._metadata(len(tokens), len(candidates), elapsed_ms),
        )
        if self._min_margin is not None and _below_gate(result, self._min_margin):
            return result.model_copy(update={"primary_expansion": None})
        return result

    # -- inline path -------------------------------------------------------
    def _inline_expansions(self, acronym_key: str, context: str) -> list[tuple[str, list[str]]]:
        """Return the document's own definitions of ``acronym_key``.

        Args:
            acronym_key: Normalised acronym.
            context: The text to scan.

        Returns:
            ``(expansion, evidence)`` pairs in document order, where evidence is
            the sorted content-word bag of the long form.
        """
        if not context or not context.strip():
            return []
        found: list[tuple[str, list[str]]] = []
        for pair in self.extractor.extract(context):
            if _short_form_key(pair.short_form) != acronym_key:
                continue
            evidence = sorted(set(self._content_words(pair.long_form)))
            found.append((pair.long_form, evidence[:MAX_EVIDENCE]))
        return found

    # -- dictionary path ---------------------------------------------------
    def _score_expansion(
        self,
        acronym_key: str,
        expansion: str,
        context_terms: Sequence[str],
        context_is_proper: bool,
    ) -> DisambiguationCandidate:
        """Score one dictionary expansion against the context.

        Args:
            acronym_key: Normalised acronym.
            expansion: The candidate expansion, verbatim.
            context_terms: Content-word bag of the context.
            context_is_proper: Whether the context uses proper nouns.

        Returns:
            The scored candidate, ``source = "dictionary"``.
        """
        words = self._content_words(expansion)
        overlap, evidence = _overlap_and_evidence(words, context_terms)
        initials = _derivability(acronym_key, words, self._config.weights)
        expansion_is_proper = any(char.isupper() for char in expansion)
        register = 1.0 if expansion_is_proper == context_is_proper else 0.0
        blend = WEIGHT_OVERLAP * overlap + WEIGHT_INITIALS * initials + WEIGHT_REGISTER * register
        score = round(min(MAX_DICTIONARY_SCORE, max(0.0, blend)), SCORE_PRECISION)
        return DisambiguationCandidate(
            expansion=expansion,
            score=score,
            source=SOURCE_DICTIONARY,
            evidence=evidence,
        )

    # -- bag construction --------------------------------------------------
    def _content_words(self, text: str) -> list[str]:
        """Return the content-word bag of ``text``, in order.

        Stop words are excluded by the configured tokenizer (a token counts when
        :attr:`~acronymkit.models.Token.is_critical` holds, i.e. it is a content
        or acronym token that the active configuration lets donate letters).
        When a fragment consists purely of function words the filter is relaxed
        to every token, so an expansion never yields an empty bag while it still
        has words.

        Args:
            text: A context, expansion or long form.

        Returns:
            The lower-cased, punctuation-free words.
        """
        if not text or not text.strip():
            return []
        tokens = self.tokenizer.tokenize(text)
        words = [_word_key(token.normalized) for token in tokens if token.is_critical]
        words = [word for word in words if word]
        if not words:
            words = [_word_key(token.normalized) for token in tokens]
            words = [word for word in words if word]
        return words

    @staticmethod
    def _context_terms(tokens: Sequence[Token], acronym_key: str) -> tuple[str, ...]:
        """Return the context's content-word bag with the acronym removed.

        Args:
            tokens: Tokens produced from the context.
            acronym_key: Normalised acronym, excluded from the bag because the
                occurrence being resolved is not evidence for anything.

        Returns:
            The de-duplicated words, in first-occurrence order.
        """
        terms: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            if not token.is_critical:
                continue
            word = _word_key(token.normalized)
            if not word or word.upper() == acronym_key or word in seen:
                continue
            seen.add(word)
            terms.append(word)
        return tuple(terms)

    def _context_is_proper(self, context: str, tokens: Sequence[Token], acronym_key: str) -> bool:
        """Report whether the context uses proper nouns.

        A context qualifies when it holds at least one content token that begins
        with an upper-case letter, is not entirely upper-case (that would be
        another abbreviation rather than a proper noun), is not the acronym being
        resolved, and does not merely start a sentence.

        Args:
            context: The raw context text.
            tokens: Tokens produced from it.
            acronym_key: Normalised acronym.

        Returns:
            ``True`` when a proper noun is present.
        """
        if not tokens:
            return False
        starts = {start for start, _ in self.tokenizer.split_sentences(context)}
        for token in tokens:
            if not token.is_critical:
                continue
            surface = token.text
            if not surface[:1].isupper() or surface.isupper():
                continue
            if _short_form_key(surface) == acronym_key:
                continue
            if token.start in starts:
                continue
            return True
        return False

    # -- metadata ----------------------------------------------------------
    def _metadata(
        self, tokens_processed: int, candidates_evaluated: int, elapsed_ms: float
    ) -> EngineMetadata:
        """Build the observability envelope for one call.

        Args:
            tokens_processed: Number of context tokens analysed.
            candidates_evaluated: Number of scored candidates.
            elapsed_ms: Wall-clock duration of the call.

        Returns:
            The populated :class:`~acronymkit.models.EngineMetadata`.
        """
        requested = self._config.engine_tier
        effective = EngineTier.ZERO_DEPENDENCY if requested is EngineTier.NEURAL else requested
        return EngineMetadata(
            engine_tier=effective,
            execution_time_ms=max(0.0, elapsed_ms),
            tokens_processed=tokens_processed,
            candidates_evaluated=candidates_evaluated,
            language=self._config.language,
            requested_tier=requested,
            warnings=list(self._warnings),
        )

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return (
            f"LexicalDisambiguator(language={self._config.language.value!r}, "
            f"short_forms={len(self._dictionary)})"
        )


def _overlap_and_evidence(
    expansion_words: Sequence[str], context_terms: Sequence[str]
) -> tuple[float, list[str]]:
    """Return the overlap term and the context terms that produced it.

    For every expansion word the best-matching context term is located with
    :func:`_word_similarity`; the term is the mean of those best similarities,
    which bounds it at ``1.0``. A context term is reported as evidence when it
    was some expansion word's best match at a similarity of at least
    :data:`EVIDENCE_MIN_SIMILARITY`.

    Args:
        expansion_words: The expansion's content words.
        context_terms: The context's content-word bag.

    Returns:
        ``(overlap, evidence)`` where ``overlap`` is in ``[0, 1]`` and
        ``evidence`` is sorted and capped at :data:`MAX_EVIDENCE` entries.
    """
    if not expansion_words or not context_terms:
        return 0.0, []
    total = 0.0
    evidence: set[str] = set()
    for word in expansion_words:
        best_score = 0.0
        best_term = ""
        for term in context_terms:
            similarity = _word_similarity(word, term)
            if similarity > best_score:
                best_score = similarity
                best_term = term
        total += best_score
        if best_term and best_score >= EVIDENCE_MIN_SIMILARITY:
            evidence.add(best_term)
    overlap = max(0.0, min(1.0, total / len(expansion_words)))
    return overlap, sorted(evidence)[:MAX_EVIDENCE]
