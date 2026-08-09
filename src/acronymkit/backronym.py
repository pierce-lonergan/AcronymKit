"""Backronym construction: fitting a fixed target word onto real words.

Where :mod:`acronymkit.generator` searches for the best *acronym* of a phrase,
this module solves the inverse problem: the string is given and the words are
what must be found. Two independent capabilities implement the two shapes that
problem takes in practice.

Alignment (``align``)
---------------------
The ACRONYM-style positional alignment (Cook, 2019). Given a target word and a
source phrase, every letter of the target is mapped onto a source token in
*non-decreasing* token order, where the letter occurs somewhere inside that
token's surface form::

    NEXUS  <-  Network Exchange Unified Security
    N -> "Network"  offset 0   INITIAL     omega = 10
    E -> "Exchange" offset 0   INITIAL     omega = 10
    X -> "Exchange" offset 1   CONTIGUOUS  omega = 2
    U -> "Unified"  offset 0   INITIAL     omega = 10
    S -> "Security" offset 0   INITIAL     omega = 10

Consecutive letters may share a token provided their character offsets
*strictly increase*, which is what makes sub-word matches -- and therefore
:class:`~acronymkit.enums.MappingKind.CONTIGUOUS` -- reachable. A letter that
lands on offset ``0`` is ``INITIAL``; one that lands exactly one character
after the immediately preceding letter *of the same token* is ``CONTIGUOUS``;
anything else mapped is ``INTERNAL``. The default 10/3/2 schedule is what makes
the search prefer word initials without any special casing, and the shipped
``unmapped_penalty`` of ``4`` is what makes an internal match beat leaving the
letter out.

The state is ``(letter_index, token_index, char_offset)``. The offset dimension
is bounded by :data:`_MAX_OFFSETS_PER_TOKEN`: at most that many occurrences of
a letter inside one token are ever considered, so the tabulation stays
``O(len(target) * len(tokens))`` and a long phrase still costs about the same
as a short one per result. A suffix-optimum table -- the best score obtainable
for ``letters[i:]`` using tokens ``j`` onward, with the offset constraints
*relaxed away* -- is tabulated once by :meth:`BackronymGenerator._suffix_optima`
and used as an admissible and consistent bound for best-first backtracking, so
complete alignments pop in descending score order. No alignment is enumerated
in full unless it is about to be collected.

Only tokens with ``is_eligible`` set are candidates, so the configured
stop-word policy applies to backronyms exactly as it does to forward
generation.

Objective
---------
``Phi(A)``, ``Lambda(A)`` and the length penalty are *constants* here -- the
acronym is the fixed target -- so up to an additive constant the full
``S(A, T)`` is exactly

    ``alpha * (SUM_i omega - unmapped_penalty * #unmapped)  -  delta * Psi(T, A)``

and both halves decompose over the path: ``Psi`` grows by one for every
critical token the cursor steps over without using. The search therefore
maximises the *whole* objective rather than the positional term alone. This
matters: matching a letter inside a token rather than leaving it out is worth
``3 - (-4) = 7`` positionally, but ``7 + delta = 22`` once the token it rescues
is counted (``delta`` ships at ``15``). A search that saw only the positional
term would trade token coverage away for word initials that never repay it.

Because the bound relaxes the offset constraints it is optimistic rather than
exact, so ranking is confirmed rather than assumed: :meth:`align` expands a
*pool* of ``max(limit, config.max_candidates) * 4`` distinct expansions (floor
:data:`_POOL_FLOOR`), re-ranks that pool by the full
:meth:`~acronymkit.scoring.Scorer.score`, and only then truncates to ``limit``.
The pool is sized off ``max_candidates`` rather than ``limit`` so that
``limit=1`` -- what :meth:`~acronymkit.engine.AcronymEngine.score` asks for --
gets exactly the same re-ranking as ``limit=25``.
``BackronymCandidate.score`` is always the complete ``S(A, T)``.

Repeated words
--------------
A phrase such as ``"signal signal signal ..."`` admits astronomically many
structurally distinct alignments that all *read* the same. Two eligible tokens
with the same surface form and the same ``is_critical`` flag are
interchangeable, and the earliest of them dominates every later copy (same
weights, same ``Psi``, strictly more continuations), so only the earliest is
ever expanded. That collapses the duplicates before they are enumerated
instead of discarding them afterwards. A stall guard
(:data:`_MAX_STALLED_POPS` consecutive completions that add no new expansion
text) backs it up for any duplication the structural key cannot see.

Synthesis (``synthesize``)
--------------------------
No source phrase at all: each target letter draws its own word from a
vocabulary (a caller-supplied iterable, or the language lexicon). Per-letter
lists are ranked deterministically -- words of 3 to 12 characters first, then
shorter before longer, then alphabetically -- and alternatives are produced by
*round-robin* over those lists, advancing every position at once so that
successive suggestions differ throughout rather than only in the final slot.

Determinism and safety
----------------------
Both entry points are pure: no clock, no randomness, no set-iteration-order
dependence. Ties are broken on the earlier ``(token index, char offset)`` pair
(alignment) or on the ranking key (synthesis), so repeated calls return
identical lists. Neither method raises: an empty target, an empty token
sequence, a letter that occurs nowhere and an empty vocabulary all degrade to
an empty list or to recorded ``unmapped_letters``.

The module is standard library plus ``pydantic`` and therefore usable on the
Tier 0 (zero-dependency) path.
"""

from __future__ import annotations

import heapq
import itertools
from typing import Iterable, Optional, Sequence

from .config import Config, ScoringWeights
from .enums import TokenRole
from .lexicon import Lexicon
from .models import BackronymCandidate, Token
from .scoring import Scorer, build_mappings

__all__ = ["BackronymGenerator"]


#: One step of an alignment path: ``(token position, character offset)`` for a
#: mapped letter, or ``None`` for an unmapped one.
_Step = Optional[tuple[int, int]]

#: Deterministic tie-break key: one ``(token position, char offset)`` pair per
#: letter decided so far, unmapped letters carrying a sentinel position.
_Key = tuple[tuple[int, int], ...]

#: One entry of the best-first frontier::
#:
#:     (negated bound, negated letter index, tie-break key, insertion order,
#:      letter index, cursor token slot, minimum offset within that slot,
#:      whether the previous letter mapped into that slot, score so far, path)
#:
#: The negated letter index is a tie-break, not part of the objective: equal
#: bounds are extremely common (every token that offers the same ``omega``
#: ties), and without it the frontier widens a whole level before descending,
#: which on a phrase where every token matches every letter exhausts
#: ``max_search_nodes`` before a single complete alignment is reached. Deeper
#: first also puts a completed alignment ahead of any partial state sharing its
#: bound -- which is exactly right, since no completion reachable from that
#: partial state can beat the bound they tie on.
_Entry = tuple[float, int, _Key, int, int, int, int, bool, float, tuple[_Step, ...]]

#: Sentinel used by the suffix-optimum table for "no completion exists".
_NEG_INF = float("-inf")

#: Decimal places retained when comparing search priorities. Quantising makes
#: alignments that differ only by floating-point noise compare equal, so the
#: explicit token-index tie-break -- not accumulated rounding error -- decides
#: their order.
_PRIORITY_PRECISION = 9

#: How many occurrences of one letter inside a single token the alignment will
#: consider. Sub-word matching makes the search state three-dimensional --
#: ``(letter, token, offset)`` -- and this is the bound on the third dimension.
#: Four covers every realistic word (only pathological repetition such as the
#: four ``s`` of "mississippi" gets close); later occurrences are dropped, which
#: can only cost an alternative, never correctness of the ones returned.
_MAX_OFFSETS_PER_TOKEN = 4

#: Pool policy for :meth:`BackronymGenerator.align`. The k-best pool expanded
#: before the full-objective re-rank is
#: ``max(_POOL_FLOOR, max(limit, config.max_candidates) * _POOL_MULTIPLIER)``
#: distinct expansions, of which only ``limit`` survive. Sizing off
#: ``max_candidates`` rather than ``limit`` keeps ``limit=1`` -- the public
#: ``score`` path -- as well re-ranked as a full request.
_POOL_MULTIPLIER = 4
_POOL_FLOOR = 32

#: Stall guard: give up once this many consecutive completed alignments have
#: all collapsed onto an expansion text already collected. Structural dedup
#: (see the module docstring) normally prevents that, so this only bounds the
#: damage from duplication the structural key cannot see. Completions pop
#: best-first, so a stall can only ever cost trailing alternatives.
_MAX_STALLED_POPS = 512

#: Word lengths preferred by :meth:`BackronymGenerator.synthesize`. Words in
#: this band rank ahead of everything else; two-letter fragments and
#: sesquipedalian outliers are demoted rather than discarded.
_PREFERRED_MIN_LENGTH = 3
_PREFERRED_MAX_LENGTH = 12


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _target_letters(target_word: str) -> str:
    """Return the canonical letter sequence of a target word.

    The target is uppercased and reduced to alphanumeric characters, so
    ``"Wi-Fi"`` becomes ``"WIFI"`` and ``"p.d.f."`` becomes ``"PDF"``. That
    string is the acronym ``A`` handed to the scorer, and it is what
    :attr:`~acronymkit.models.BackronymCandidate.target_word` reports.

    Args:
        target_word: Raw target as supplied by the caller.

    Returns:
        The uppercased alphanumeric form; ``""`` when nothing survives.
    """
    return "".join(char for char in target_word.upper() if char.isalnum())


def _letter_offsets(text: str, letter: str) -> tuple[int, ...]:
    """Return the offsets in ``text`` holding ``letter``, earliest first.

    The comparison is case-insensitive but never rewrites ``text``, so every
    returned offset indexes the token's surface form exactly -- which matters
    for scripts where case mapping changes length (``"ß"`` uppercases to
    ``"SS"``).

    Every occurrence matters now that consecutive letters may share a token:
    offset ``0`` is the sole way to earn ``INITIAL``, and a later offset can
    earn ``CONTIGUOUS`` or ``INTERNAL`` depending on where the *previous*
    letter landed. At most :data:`_MAX_OFFSETS_PER_TOKEN` offsets are reported,
    which bounds the offset dimension of the search state.

    Args:
        text: Token surface form to search.
        letter: Single character being placed.

    Returns:
        The zero-based offsets in increasing order; empty when the letter does
        not occur.
    """
    lowered = letter.lower()
    found: list[int] = []
    for offset, char in enumerate(text):
        if char == letter or char.lower() == lowered:
            found.append(offset)
            if len(found) == _MAX_OFFSETS_PER_TOKEN:
                break
    return tuple(found)


def _priority(value: float) -> float:
    """Quantise a search priority so near-equal scores tie deterministically."""
    return round(value, _PRIORITY_PRECISION)


def _render(path: Sequence[_Step], tokens: Sequence[Token]) -> str:
    """Render an alignment path as its expansion text.

    Each *token* contributes its surface form once, however many letters it
    donated: token positions are non-decreasing, so every repeat is adjacent
    and a change of position is exactly a word boundary. Unmapped letters
    contribute nothing.

    This is the distinctness signature :meth:`BackronymGenerator.align` dedupes
    on, and it is deliberately cheap -- it runs on every completed alignment
    the search pops, whereas the full candidate is only built for the ones that
    survive.

    Args:
        path: One step per letter -- ``(token position, char offset)`` or
            ``None`` for an unmapped letter.
        tokens: The full token sequence the positions index into.

    Returns:
        The expansion text; ``""`` when nothing was mapped.
    """
    words: list[str] = []
    previous: Optional[int] = None
    for step in path:
        if step is None:
            continue
        position = step[0]
        if position != previous:
            words.append(tokens[position].text)
            previous = position
    return " ".join(words)


def _word_rank_key(word: str) -> tuple[int, int, str]:
    """Return the deterministic ranking key for a synthesis vocabulary word.

    Ordering is ``(outside the preferred length band, length, alphabetical)``:
    words of :data:`_PREFERRED_MIN_LENGTH` to :data:`_PREFERRED_MAX_LENGTH`
    characters come first, shorter before longer inside each group, ties broken
    lexicographically.

    Args:
        word: Candidate word.

    Returns:
        A total-order sort key.
    """
    length = len(word)
    preferred = _PREFERRED_MIN_LENGTH <= length <= _PREFERRED_MAX_LENGTH
    return (0 if preferred else 1, length, word)


def _rank_words(words: Iterable[str]) -> tuple[str, ...]:
    """Deduplicate and rank a bag of vocabulary words.

    Entries are stripped; blanks and non-strings are dropped. Words that differ
    only by case collapse to their lexicographically smallest surface form, so
    the result does not depend on the iteration order of the input.

    Args:
        words: Candidate words, in any order.

    Returns:
        The ranked, deduplicated words, best first.
    """
    unique: dict[str, str] = {}
    for raw in words:
        if not isinstance(raw, str):
            continue
        word = raw.strip()
        if not word:
            continue
        key = word.casefold()
        current = unique.get(key)
        if current is None or word < current:
            unique[key] = word
    return tuple(sorted(unique.values(), key=_word_rank_key))


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class BackronymGenerator:
    """Fit a fixed target word onto source tokens or onto dictionary words.

    The generator is immutable and side-effect free; construct one per engine
    and share it across threads.

    Example:
        >>> from acronymkit.config import Config
        >>> from acronymkit.scoring import Scorer
        >>> from acronymkit.tokenizer import Tokenizer
        >>> config = Config()
        >>> generator = BackronymGenerator(config, Scorer(config))
        >>> tokens = Tokenizer(config).tokenize("Portable Document Format")
        >>> best = generator.align("PDF", tokens)[0]
        >>> best.expansion_text
        'Portable Document Format'
        >>> best.coverage
        1.0

    Args:
        config: Engine configuration. Supplies the effective weights, the
            candidate ceiling (``max_candidates``), the search budget
            (``max_search_nodes``), the breakdown switch and the language used
            when a synthesis vocabulary has to be loaded.
        scorer: The shared scorer. Every returned ``score`` is its verdict, so
            backronyms are ranked on exactly the same objective as forward
            candidates.
        lexicon: Default vocabulary for :meth:`synthesize`. When ``None`` the
            scorer's own lexicon is adopted if it has one; failing that,
            :meth:`~acronymkit.lexicon.Lexicon.load` is consulted lazily on
            first use.
    """

    __slots__ = ("_config", "_lexicon", "_scorer", "_weights")

    def __init__(
        self,
        config: Config,
        scorer: Scorer,
        lexicon: Optional[Lexicon] = None,
    ) -> None:
        self._config = config
        self._scorer = scorer
        self._weights: ScoringWeights = config.weights
        self._lexicon = lexicon if lexicon is not None else scorer.lexicon

    # -- properties --------------------------------------------------------
    @property
    def config(self) -> Config:
        """The configuration this generator was built from."""
        return self._config

    @property
    def scorer(self) -> Scorer:
        """The scorer evaluating every candidate."""
        return self._scorer

    @property
    def lexicon(self) -> Optional[Lexicon]:
        """The default synthesis vocabulary, or ``None`` if none was bound."""
        return self._lexicon

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return (
            f"BackronymGenerator(language={self._config.language.value!r}, "
            f"lexicon={self._lexicon is not None})"
        )

    # -- alignment ---------------------------------------------------------
    def align(
        self,
        target_word: str,
        tokens: Sequence[Token],
        *,
        limit: Optional[int] = None,
    ) -> list[BackronymCandidate]:
        """Align a target word onto a source phrase.

        Each letter of ``target_word`` (uppercased, alphanumeric only) is
        assigned to an eligible token in *non-decreasing* token order, such
        that the letter occurs somewhere in that token's surface form. Two
        consecutive letters may share a token as long as their character
        offsets strictly increase, which is how a sub-word match such as
        ``E``/``X`` out of ``"Exchange"`` -- ``INITIAL`` then ``CONTIGUOUS`` --
        arises. A letter with no legal token is left ``UNMAPPED``: it is
        recorded in
        :attr:`~acronymkit.models.BackronymCandidate.unmapped_letters`,
        contributes an empty string to the expansion, and costs
        ``weights.unmapped_penalty``.

        Search proceeds best-first over ``(letter, token, offset)`` states,
        bounded by a suffix-optimum table that relaxes the offset constraints
        away. Both halves of the objective that vary with the alignment are
        accumulated along the path -- the positional term *and*
        ``delta * Psi(T, A)``, which grows by one for every critical token the
        cursor steps over -- so the search maximises the real objective rather
        than the positional term alone.

        Because that bound is optimistic rather than exact, the ranking is
        confirmed rather than assumed: a pool of
        ``max(limit, config.max_candidates) * 4`` distinct expansions (floor
        :data:`_POOL_FLOOR`) is expanded, re-ranked by the full ``S(A, T)``
        from the :class:`~acronymkit.scoring.Scorer`, and only then truncated
        to ``limit``. ``align(..., limit=1)`` therefore returns the same
        candidate as ``align(...)[0]``.

        Results are distinct by expansion *text*: two alignments that read the
        same once unmapped slots collapse, or once repeated letters from one
        token collapse, are reported once, keeping the better-scoring one.

        The search stops early once the pool is full, ``config.max_search_nodes``
        states have been expanded, or :data:`_MAX_STALLED_POPS` consecutive
        completions have failed to produce a new expansion text.

        Args:
            target_word: Word the expansion must spell out.
            tokens: Source phrase, typically from
                :meth:`~acronymkit.tokenizer.Tokenizer.tokenize`. Tokens with
                ``is_eligible`` unset (stop words, over-short words) are never
                assigned a letter.
            limit: Maximum candidates to return; defaults to
                ``config.max_candidates``. Values below one yield ``[]``.

        Returns:
            Candidates best first, the first being the full-objective best.
            Empty when the target has no alphanumeric characters or ``limit``
            is not positive; otherwise never empty -- a target that matches
            nothing still returns the all-unmapped alignment with
            ``coverage == 0.0``.

        Example:
            >>> from acronymkit.config import Config
            >>> from acronymkit.scoring import Scorer
            >>> from acronymkit.tokenizer import Tokenizer
            >>> config = Config()
            >>> generator = BackronymGenerator(config, Scorer(config))
            >>> tokens = Tokenizer(config).tokenize("Application Programming Interface")
            >>> top = generator.align("API", tokens)[0]
            >>> [m.kind.value for m in top.mappings]
            ['initial', 'initial', 'initial']
            >>> generator.align("ZZZ", tokens)[0].unmapped_letters
            ['Z', 'Z', 'Z']
            >>> nexus = Tokenizer(config).tokenize("Network Exchange Unified Security")
            >>> generator.align("NEXUS", nexus)[0].expansion_text
            'Network Exchange Unified Security'
        """
        letters = _target_letters(target_word)
        wanted = self._config.max_candidates if limit is None else limit
        if not letters or wanted <= 0:
            return []

        weights = self._weights
        alpha = float(weights.alpha)
        delta = float(weights.delta)
        penalty = alpha * float(weights.unmapped_penalty)
        initial_gain = alpha * float(weights.initial_weight)
        internal_gain = alpha * float(weights.internal_weight)
        contiguous_gain = alpha * float(weights.contiguous_weight)

        token_list = list(tokens)
        positions = [position for position, token in enumerate(token_list) if token.is_eligible]
        usable = [token_list[p] for p in positions]
        letter_count = len(letters)
        usable_count = len(usable)
        # criticals[j] counts the critical tokens among usable slots [0, j), so
        # stepping the cursor from a to b drops criticals[b] - criticals[a] of
        # them -- exactly the increment to Psi(T, A).
        criticals = [0] * (usable_count + 1)
        for slot, token in enumerate(usable):
            criticals[slot + 1] = criticals[slot] + (1 if token.is_critical else 0)
        # Interchangeability class for the structural dedup: same surface form
        # and same criticality means identical weights, identical Psi and
        # identical rendering, so only the earliest copy is ever expanded.
        classes = [(token.text, token.is_critical) for token in usable]

        offsets, gains = self._match_table(letters, usable)
        fresh, held = self._suffix_optima(gains, criticals, penalty, delta)

        # Sorts after every real token position, so an equally scoring mapped
        # letter always outranks an unmapped one on the tie-break.
        sentinel = (len(token_list) + 1, 0)
        budget = max(1, self._config.max_search_nodes)
        pool = max(_POOL_FLOOR, max(wanted, self._config.max_candidates) * _POOL_MULTIPLIER)

        counter = itertools.count()
        heap: list[_Entry] = [(-_priority(fresh[0]), 0, (), next(counter), 0, 0, 0, False, 0.0, ())]

        def push(
            index: int,
            slot: int,
            floor: int,
            chained: bool,
            score: float,
            path: tuple[_Step, ...],
            key: _Key,
        ) -> None:
            """Queue one successor state under its admissible bound."""
            bound = score + (held[index][slot] if floor else fresh[index])
            heapq.heappush(
                heap,
                (
                    -_priority(bound),
                    -index,
                    key,
                    next(counter),
                    index,
                    slot,
                    floor,
                    chained,
                    score,
                    path,
                ),
            )

        found: list[tuple[BackronymCandidate, _Key]] = []
        seen: set[str] = set()
        expanded = 0
        stalled = 0

        while heap and len(found) < pool and expanded < budget:
            (
                _bound,
                _depth,
                key,
                _order,
                index,
                slot,
                floor,
                chained,
                accumulated,
                path,
            ) = heapq.heappop(heap)
            expanded += 1
            if index == letter_count:
                # Alignments are distinct by construction, but two of them can
                # *read* the same once unmapped slots collapse (letter i taking
                # token t, versus letter i+1 taking it internally) or once a
                # repeated letter shifts within one token. Keep only the first
                # -- best-first order means that is the better one -- and pay
                # for scoring a candidate only once it has earned its place.
                signature = _render(path, token_list)
                if signature in seen:
                    stalled += 1
                    if stalled >= _MAX_STALLED_POPS:
                        break
                    continue
                stalled = 0
                seen.add(signature)
                found.append((self._alignment_candidate(letters, path, token_list), key))
                continue

            offset_row = offsets[index]
            # First slot whose fate is still undecided: the cursor token itself
            # unless a previous letter already claimed it.
            start = slot + 1 if floor else slot

            push(
                index + 1,
                slot,
                floor,
                False,
                accumulated - penalty,
                (*path, None),
                (*key, sentinel),
            )

            # Stay inside the cursor token, at a strictly later offset.
            if slot < usable_count:
                for offset in offset_row[slot]:
                    if offset < floor:
                        continue
                    if offset == 0:
                        gain = initial_gain
                    elif chained and offset == floor:
                        gain = contiguous_gain
                    else:
                        gain = internal_gain
                    step = (positions[slot], offset)
                    push(
                        index + 1,
                        slot,
                        offset + 1,
                        True,
                        accumulated + gain,
                        (*path, step),
                        (*key, step),
                    )

            # Advance to a later token, skipping interchangeable duplicates.
            expanded_classes = {classes[slot]} if slot < usable_count and not floor else set()
            for later in range(slot + 1, usable_count):
                marker = classes[later]
                if marker in expanded_classes:
                    continue
                expanded_classes.add(marker)
                skipped = delta * (criticals[later] - criticals[start])
                for offset in offset_row[later]:
                    gain = initial_gain if offset == 0 else internal_gain
                    step = (positions[later], offset)
                    push(
                        index + 1,
                        later,
                        offset + 1,
                        True,
                        accumulated + gain - skipped,
                        (*path, step),
                        (*key, step),
                    )

        found.sort(key=lambda item: (-item[0].score, -item[0].coverage, item[1]))
        return [candidate for candidate, _key in found[:wanted]]

    # -- synthesis ---------------------------------------------------------
    def synthesize(
        self,
        target_word: str,
        *,
        vocabulary: Optional[Iterable[str]] = None,
        limit: Optional[int] = None,
    ) -> list[BackronymCandidate]:
        """Invent an expansion for a target word with no source phrase.

        Every letter of ``target_word`` draws its own word from ``vocabulary``:
        the words starting with that letter are ranked by
        :func:`_word_rank_key` (3-12 characters first, then shorter, then
        alphabetical) and alternatives are emitted by round-robin over those
        per-letter lists. Because all positions advance together, the second
        suggestion differs from the first in *every* slot rather than only in
        the last.

        A letter with no matching word is not fatal: that position yields an
        empty string and the letter is recorded in
        :attr:`~acronymkit.models.BackronymCandidate.unmapped_letters` -- which
        matters for letters such as ``X`` that most word lists barely cover.

        Every emitted word is scored as an ``INITIAL`` match against a
        synthetic token sequence, so ``score`` is the same ``S(A, T)`` the rest
        of the library reports. Those scores are equal across the returned
        alternatives by construction (the acronym, the mapping kinds and the
        information loss are all identical), so the round-robin rank order is
        preserved.

        Args:
            target_word: Word the expansion must spell out.
            vocabulary: Words to draw from. Defaults to the bound lexicon, or
                to :meth:`~acronymkit.lexicon.Lexicon.load` for
                ``config.language`` when the generator has none. The iterable
                is consumed exactly once.
            limit: Maximum candidates to return; defaults to
                ``config.max_candidates``. Values below one yield ``[]``.

        Returns:
            Distinct expansions, best first. Empty -- never an exception --
            when the target has no alphanumeric characters, ``limit`` is not
            positive, or the vocabulary supplies no word for any letter.

        Example:
            >>> from acronymkit.config import Config
            >>> from acronymkit.scoring import Scorer
            >>> config = Config()
            >>> generator = BackronymGenerator(config, Scorer(config))
            >>> words = ["rapid", "reliable", "adaptive", "agile", "modular", "modern"]
            >>> [c.expansion_text for c in generator.synthesize("RAM", vocabulary=words)]
            ['rapid agile modern', 'reliable adaptive modular']
            >>> generator.synthesize("RAM", vocabulary=[])
            []
        """
        letters = _target_letters(target_word)
        wanted = self._config.max_candidates if limit is None else limit
        if not letters or wanted <= 0:
            return []

        ranked = self._ranked_vocabulary(letters, vocabulary)
        rounds = max((len(bucket) for bucket in ranked), default=0)
        if rounds == 0:
            return []

        results: list[BackronymCandidate] = []
        seen: set[tuple[str, ...]] = set()
        for turn in range(rounds):
            words = tuple(bucket[turn % len(bucket)] if bucket else "" for bucket in ranked)
            if words in seen:
                continue
            seen.add(words)
            results.append(self._synthesized_candidate(letters, words))
            if len(results) >= wanted:
                break

        # Stable: scores tie by construction, so round-robin rank order stands.
        results.sort(key=lambda candidate: -candidate.score)
        return results

    # -- internals ---------------------------------------------------------
    def _match_table(
        self, letters: str, usable: Sequence[Token]
    ) -> tuple[list[list[tuple[int, ...]]], list[list[Optional[float]]]]:
        """Tabulate where each target letter may land and what that is worth.

        Args:
            letters: Canonical target letters.
            usable: The eligible tokens, in phrase order.

        Returns:
            ``(offsets, gains)``, both indexed ``[letter][usable token]``.
            ``offsets`` holds every offset the letter occupies inside that
            token, capped at :data:`_MAX_OFFSETS_PER_TOKEN` and empty when the
            letter does not occur. ``gains`` holds the *best* ``alpha * omega``
            reachable there -- which is what the suffix-optimum table needs,
            since the actual kind depends on where the previous letter landed
            -- or ``None`` when the letter does not occur.
        """
        alpha = float(self._weights.alpha)
        initial_weight = alpha * float(self._weights.initial_weight)
        internal_weight = alpha * float(self._weights.internal_weight)
        contiguous_weight = alpha * float(self._weights.contiguous_weight)
        # Weights are not constrained to the 10/3/2 ordering, so take the max
        # rather than assuming INITIAL wins: the bound must never understate.
        continued_weight = max(internal_weight, contiguous_weight)
        offsets: list[list[tuple[int, ...]]] = []
        gains: list[list[Optional[float]]] = []
        for letter in letters:
            offset_row: list[tuple[int, ...]] = []
            gain_row: list[Optional[float]] = []
            for token in usable:
                found = _letter_offsets(token.text, letter)
                offset_row.append(found)
                if not found:
                    gain_row.append(None)
                elif found[0] != 0:
                    gain_row.append(continued_weight)
                elif len(found) > 1:
                    gain_row.append(max(initial_weight, continued_weight))
                else:
                    gain_row.append(initial_weight)
            offsets.append(offset_row)
            gains.append(gain_row)
        return offsets, gains

    def _suffix_optima(
        self,
        gains: Sequence[Sequence[Optional[float]]],
        criticals: Sequence[int],
        penalty: float,
        delta: float,
    ) -> tuple[list[float], list[list[float]]]:
        """Tabulate an optimistic score for every alignment suffix.

        Two tables are returned, matching the two shapes a search state takes.
        ``fresh[i]`` bounds letters ``i`` onward when no token has been claimed
        yet; ``held[i][t]`` bounds them when token ``t`` is the cursor -- it is
        already covered, so it costs no ``Psi`` and may still donate a further
        letter at a later offset::

            held[i][t] = max(
                held[i + 1][t] - unmapped_penalty,               # letter i out
                max_omega(i, t) + held[i + 1][t],                # stay on t
                max over u > t:                                  # advance to u
                    max_omega(i, u)
                    - delta * criticals(t + 1, u)
                    + held[i + 1][u],
            )
            fresh[i] = max(
                fresh[i + 1] - unmapped_penalty,
                max over t: max_omega(i, t) - delta * criticals(0, t)
                            + held[i + 1][t],
            )

        with base rows charging ``delta`` for every critical token still
        undecided, so the bound already contains the whole of ``Psi(T, A)``.
        That matters as much as admissibility: a bound that omitted a cost the
        path keeps accruing would decay with depth, and best-first search would
        widen a whole level at a time instead of descending.

        Two relaxations remain, both one-sided and both concerning offsets --
        the dimension the tables do not carry. ``max_omega`` assumes the best
        of the ``INITIAL``/``CONTIGUOUS``/``INTERNAL`` weights is reachable,
        and staying on ``t`` ignores the strictly-increasing offset rule. The
        tables therefore never *understate*, and since every entry dominates
        every real transition out of the state it indexes, the bound is
        consistent as well as admissible -- which is what lets :meth:`align`
        pop complete alignments in descending score order.

        The inner maxima are accumulated right-to-left through a suffix-maximum
        pass, so the whole tabulation costs ``O(len(letters) * len(tokens))``.

        Args:
            gains: ``[letter][token]`` best weights from :meth:`_match_table`,
                already scaled by ``alpha``.
            criticals: Prefix counts of critical tokens; ``criticals[j]`` is the
                number among usable slots ``[0, j)``.
            penalty: ``alpha * weights.unmapped_penalty``.
            delta: The information-loss coefficient.

        Returns:
            ``(fresh, held)``: a ``len(letters) + 1`` vector and a
            ``(len(letters) + 1) x len(tokens)`` table, both with the
            all-undecided base row at index ``len(letters)``.
        """
        letter_count = len(gains)
        usable_count = len(gains[0]) if letter_count else 0
        total = criticals[usable_count]

        fresh = [0.0] * (letter_count + 1)
        held = [[0.0] * usable_count for _ in range(letter_count + 1)]
        fresh[letter_count] = -delta * total
        base = held[letter_count]
        for slot in range(usable_count):
            base[slot] = -delta * (total - criticals[slot + 1])

        for index in range(letter_count - 1, -1, -1):
            gain_row = gains[index]
            following = held[index + 1]
            # advance[t] = max over u >= t of (omega(u) - delta * criticals[u]
            # + held[i + 1][u]); adding delta * criticals[t] recovers the real
            # skip charge for a jump that starts at t.
            advance = [_NEG_INF] * (usable_count + 1)
            running = _NEG_INF
            for slot in range(usable_count - 1, -1, -1):
                gain = gain_row[slot]
                if gain is not None:
                    value = gain - delta * criticals[slot] + following[slot]
                    if value > running:
                        running = value
                advance[slot] = running

            row = held[index]
            for slot in range(usable_count):
                option = following[slot] - penalty
                gain = gain_row[slot]
                if gain is not None:
                    stay = gain + following[slot]
                    if stay > option:
                        option = stay
                jump = advance[slot + 1]
                if jump > _NEG_INF:
                    jump += delta * criticals[slot + 1]
                    if jump > option:
                        option = jump
                row[slot] = option

            option = fresh[index + 1] - penalty
            opening = advance[0]
            if opening > option:
                option = opening
            fresh[index] = option
        return fresh, held

    def _alignment_candidate(
        self, letters: str, path: Sequence[_Step], tokens: Sequence[Token]
    ) -> BackronymCandidate:
        """Package one completed alignment path as a scored candidate.

        ``expansion`` keeps one entry per target letter, so a token that
        donates two letters appears twice there. ``expansion_text`` is the
        *reading* of the alignment and therefore names each token once: since
        token positions are non-decreasing, every repeat is adjacent and
        collapsing on a change of token position renders the phrase in order.

        Args:
            letters: Canonical target letters; also the acronym ``A``.
            path: One step per letter -- ``(token position, char offset)`` or
                ``None`` for an unmapped letter.
            tokens: The full token sequence the positions index into.

        Returns:
            The scored candidate, with ``breakdown`` attached only when
            ``config.include_breakdown`` is set.
        """
        assignments: list[tuple[int, Optional[int], Optional[int]]] = []
        expansion: list[str] = []
        unmapped: list[str] = []
        covered: set[int] = set()
        for position, step in enumerate(path):
            if step is None:
                assignments.append((position, None, None))
                expansion.append("")
                unmapped.append(letters[position])
                continue
            token_position, offset = step
            assignments.append((position, token_position, offset))
            expansion.append(tokens[token_position].text)
            # `covered` is keyed by Token.index because that is what
            # Scorer.information_loss compares against, while the assignment
            # carries the sequence position that build_mappings bounds-checks.
            covered.add(tokens[token_position].index)

        mappings = build_mappings(letters, assignments, tokens, self._weights)
        breakdown = self._scorer.score(letters, tokens, mappings, covered)
        mapped = len(letters) - len(unmapped)
        return BackronymCandidate(
            target_word=letters,
            expansion=expansion,
            expansion_text=_render(path, tokens),
            score=breakdown.total,
            coverage=mapped / len(letters),
            mappings=mappings,
            unmapped_letters=unmapped,
            breakdown=breakdown if self._config.include_breakdown else None,
        )

    def _ranked_vocabulary(
        self, letters: str, vocabulary: Optional[Iterable[str]]
    ) -> list[tuple[str, ...]]:
        """Build the ranked word list backing each target letter.

        Args:
            letters: Canonical target letters.
            vocabulary: Caller-supplied words, or ``None`` to fall back to the
                bound lexicon (loading one for ``config.language`` if the
                generator has none).

        Returns:
            One ranked tuple per letter, positionally aligned with ``letters``.
            A letter no word starts with yields an empty tuple.
        """
        required = set(letters)
        buckets: dict[str, tuple[str, ...]] = {}
        if vocabulary is None:
            lexicon = self._lexicon
            if lexicon is None:
                lexicon = Lexicon.load(self._config.language, path=self._config.lexicon_path)
            for letter in sorted(required):
                buckets[letter] = _rank_words(lexicon.starting_with(letter.lower()))
        else:
            collected: dict[str, list[str]] = {letter: [] for letter in sorted(required)}
            for raw in vocabulary:
                if not isinstance(raw, str):
                    continue
                word = raw.strip()
                if not word:
                    continue
                head = word[0].upper()
                if head in collected:
                    collected[head].append(word)
            buckets = {letter: _rank_words(words) for letter, words in collected.items()}
        return [buckets.get(letter, ()) for letter in letters]

    def _synthesized_candidate(self, letters: str, words: Sequence[str]) -> BackronymCandidate:
        """Score one synthesised expansion against synthetic source tokens.

        A :class:`~acronymkit.models.Token` is fabricated for every non-empty
        word so the alignment can be expressed in the same vocabulary as
        :meth:`align`: each word is a critical content token whose initial the
        target letter occupies, giving an ``INITIAL`` mapping and zero
        information loss. Token offsets index
        :attr:`~acronymkit.models.BackronymCandidate.expansion_text`.

        Args:
            letters: Canonical target letters.
            words: One word per letter, positionally aligned; ``""`` marks a
                letter the vocabulary could not serve.

        Returns:
            The scored candidate.
        """
        tokens: list[Token] = []
        assignments: list[tuple[int, Optional[int], Optional[int]]] = []
        expansion: list[str] = []
        unmapped: list[str] = []
        cursor = 0
        for position, word in enumerate(words):
            if not word:
                assignments.append((position, None, None))
                expansion.append("")
                unmapped.append(letters[position])
                continue
            index = len(tokens)
            tokens.append(
                Token(
                    text=word,
                    normalized=word.casefold(),
                    index=index,
                    start=cursor,
                    end=cursor + len(word),
                    role=TokenRole.CONTENT,
                    is_critical=True,
                    is_eligible=True,
                    letters=word[:1].upper(),
                )
            )
            cursor += len(word) + 1
            assignments.append((position, index, 0))
            expansion.append(word)

        mappings = build_mappings(letters, assignments, tokens, self._weights)
        covered = {token.index for token in tokens}
        breakdown = self._scorer.score(letters, tokens, mappings, covered)
        mapped = len(letters) - len(unmapped)
        return BackronymCandidate(
            target_word=letters,
            expansion=expansion,
            expansion_text=" ".join(word for word in expansion if word),
            score=breakdown.total,
            coverage=mapped / len(letters),
            mappings=mappings,
            unmapped_letters=unmapped,
            breakdown=breakdown if self._config.include_breakdown else None,
        )
