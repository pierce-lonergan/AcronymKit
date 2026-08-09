"""Forward acronym generation — the beam search behind ``AcronymEngine.generate``.

The generator turns a tokenised phrase into a ranked list of
:class:`~acronymkit.models.AcronymCandidate` records. It owns the *search*;
:class:`~acronymkit.scoring.Scorer` owns the *arithmetic*. Nothing in this
module re-implements ``S(A, T)``.

Search space
------------
The search runs strictly left-to-right over the **eligible** tokens (those with
``Token.is_eligible`` and a non-empty ``Token.letters``). A partial state is the
pair ``(chars, takes)``:

``chars``
    The acronym prefix accumulated so far.
``takes``
    An ordered tuple of ``(token_index, letters_taken)`` pairs recording which
    token donated how many leading characters. Everything else — the ``covered``
    token set, the positional term, the per-character
    :class:`~acronymkit.models.LetterMapping` list — is derived from it, so a
    state is cheap to copy and trivially hashable.

At each token the successor branches are:

* **skip** — only when :attr:`~acronymkit.config.Config.allow_token_skipping`;
* **take ``k``** for ``k`` in ``1 .. max_letters_per_token``, contributing
  ``token.letters[:k]``;
* for :attr:`~acronymkit.enums.TokenRole.ACRONYM` tokens, a **single atomic
  branch** contributing the whole ``token.letters`` string. An acronym that the
  tokenizer already recognised ("API", "XML") is reused verbatim and is never
  split, so ``"API"`` can never degrade into ``"AP"`` or ``"A"``.

Partial states longer than
:attr:`~acronymkit.config.Config.max_acronym_length` are never generated.
Whether the frontier is *also* cut back after each token round depends on how
large the space is, and the generator decides that before the first round.

**Exhaustive mode.** Multiplying out the per-token branching factors
(``len(pieces)``, plus one when skipping is allowed) gives an exact upper bound
on the number of successors an unpruned search would enumerate. When that bound
fits inside :attr:`~acronymkit.config.Config.max_search_nodes` the search runs
with **no beam cut at all**, and the returned ranking is therefore the exact
optimum over the whole space. Almost every real phrase lands here: at the
shipped defaults a token of two or more letters branches three ways, so seven
tokens enumerate at most ``3 + 9 + ... + 3**7 = 3279`` successors against a
budget of ``50_000``, and nine tokens — the largest that still fits — at most
``29_523``.

Exhaustive mode is exact, not free: it is the caller's node budget being spent
as declared, and the states it keeps all have to be scored. Up to about six
eligible tokens it costs no more than the beam it replaces (six tokens: ~740
successors, a few milliseconds); at the nine-token ceiling it is roughly an
order of magnitude slower than a 250-wide beam would have been, and a config
that raises ``max_acronym_length`` or ``max_letters_per_token`` reaches that
ceiling with fewer tokens. Lowering
:attr:`~acronymkit.config.Config.max_search_nodes` below the bound is the dial
that buys the latency back, at the cost of the exactness guarantee.

**Beam mode.** Otherwise the frontier is cut back to
:attr:`~acronymkit.config.Config.search_beam_width` states after every round.
A cut can discard the eventual optimum, so any round that actually drops a state
sets ``truncated=True`` (see *Budgets and truncation* below).

The beam ranking key
--------------------
When a cut is unavoidable the key must not be the positional term alone. Under
:attr:`~acronymkit.enums.ScoringStrategy.DICTIONARY_BACKRONYM` (``gamma=60.0``)
a four-character prefix that is still on its way to a dictionary word is worth
far more than a six-character full-coverage prefix that is not, yet the
positional term ranks the short prefix last and prunes it away. States are
therefore ranked by an *optimistic bound* on the best total any completion of
the state could still reach::

    bound = alpha * (positional_so_far + best_positional_still_reachable)
          - length_penalty * max(0, len(chars) - preferred_length)
          - delta * critical_tokens_already_skipped
          + gamma * (1 if some lexicon word still starts with chars else 0)

Every term equals, or over-states, its final value, so the bound never
under-states what a state can become:

* ``positional_so_far`` is *exact*. A run of characters taken from one token is
  always classified ``INITIAL`` followed by ``CONTIGUOUS`` (see
  :func:`~acronymkit.scoring.build_mappings`), so the sum of ``omega`` collapses
  to ``takes * initial_weight + (len(chars) - takes) * contiguous_weight`` —
  the value :meth:`~acronymkit.scoring.Scorer.positional_term` will later
  compute, obtained without constructing a single Pydantic model.
* ``best_positional_still_reachable`` maximises over every legal way to spend the
  remaining ``max_acronym_length - len(chars)`` characters on the tokens not yet
  visited: at most one ``INITIAL`` per remaining token, every further character
  ``CONTIGUOUS``, and at least one ``INITIAL`` before any ``CONTIGUOUS`` because
  the search never returns to a token it has passed. It is maximised *jointly*
  with the length penalty those same characters would incur, which keeps the
  bound tight instead of merely valid.
* ``Psi`` is charged only for the critical tokens the state has already passed
  over, which is known exactly; future skips are optimistically assumed away.
* ``Lambda`` is bounded by ``gamma`` exactly when some lexicon entry still has
  ``chars`` as a prefix — one :func:`bisect.bisect_left` into the lexicon's
  first-letter bucket, memoised for the duration of a single search. A state
  that can still become a word therefore can never be ranked below one that
  cannot on the lexical term.
* ``Phi`` is a mean bigram log-likelihood and so is never positive; with
  ``beta >= 0`` the term ``beta * Phi <= 0`` and the bound simply omits it.

Admissibility is a property of the *bound*, not a promise that a beam search is
exact: when more than ``search_beam_width`` states share a frontier, a state
whose bound is unachievable can still displace the eventual optimum. What the
bound guarantees is that a state is never cut in favour of one that provably
cannot beat it — in particular a live dictionary prefix is never cut in favour
of a dead one of equal positional value. Exactness comes from exhaustive mode,
which covers every space that fits the node budget.

The plain-initialism safety net
-------------------------------
A beam cut is a *heuristic*: a short, conventional initialism can legitimately
be pruned out of a wide frontier. That is unacceptable for the one candidate
every user expects to see. Before scoring, therefore, the generator
**unconditionally injects** the plain initialism — the first letter of every
eligible token (the whole string for an ``ACRONYM`` token), truncated to
``max_acronym_length`` — into the candidate pool, whether or not the search
happened to reach it.

The injection is deliberately a *safety net for presence*, not a ranking
override: the initialism is scored by the same :class:`~acronymkit.scoring.Scorer`
as every other candidate and takes its place in the same ``(-score, length,
acronym)`` ordering. It is also subject to the same final filters, so
``require_dictionary_word=True`` still rejects it rather than smuggling a
non-word past the constraint. The one further concession is the last slot of the
returned list: on a long phrase the initialism can be outscored by more than
``max_candidates`` rivals, so top-N truncation gives the final slot back to it
(see :meth:`ForwardGenerator._limit`) — which, because it ranked below
everything retained, leaves the list correctly ordered.

That concession needs two slots to be honest, so the guarantee is stated with
its bound in place: **the plain initialism is always scored, and it is always
returned when ``max_candidates >= 2``.** With ``max_candidates == 1`` the single
slot belongs to the top-ranked candidate. Handing that slot to a strictly
lower-scoring initialism would change :attr:`AcronymResult.primary_acronym
<acronymkit.models.AcronymResult.primary_acronym>` from "the best acronym found"
into "the plain initialism", which is a ranking override rather than a safety
net — and the initialism remains one slot away for any caller that wants it.

Note that "present" is all the safety net promises. Ranking is decided purely by
``S(A, T)``, and the shipped ``BALANCED_PRONOUNCEABLE`` weights (``alpha=1.0``,
``beta=1.0``, ``gamma=12.0``, ``delta=15.0``, ``length_penalty=6.0``,
``preferred_length=2``, with ``omega`` on the ``10 / 3 / 2`` schedule) make a
dictionary hit too cheap to pay for dropping a token. Trading one covered
critical token for a real word one character shorter gains ``gamma = 12`` and
saves one character of length penalty (``6``) against a loss of ``delta = 15``
plus the forfeited ``initial_weight = 10``: ``12 + 6 - 15 - 10 = -7``. Spending
the freed character on a second letter from a token already used claws back only
``contiguous_weight = 2`` and forfeits the ``6``, which is worse. The literal
initialism
therefore outranks the word-shaped rival by default, which is why
``tests/test_scoring_presets.py`` can pin the whole canonical corpus as primary
results. Under ``DICTIONARY_BACKRONYM`` (``gamma=60.0``, ``delta=22.0``,
``length_penalty=3.0``) the same trade is worth ``60 + 3 - 22 - 10 = +31`` and
the word wins instead — that strategy, not a tweak here, is how a caller asks
for backronyms. Callers who want the classic first-letter initialism and nothing
else should generate one letter per token (``Config.fast()``, or any config with
``allow_multi_letter_tokens=False``), which removes the multi-letter branches
from the search space entirely.

Budgets and truncation
----------------------
:attr:`~acronymkit.config.Config.max_search_nodes` caps the number of enumerated
successor states and :attr:`~acronymkit.config.Config.search_time_budget_ms`
caps wall-clock time (measured with :func:`time.perf_counter`). Both are checked
at the top of every token round and, for the node cap, before each state is
expanded — so the search overruns a budget by at most the remainder of one
expansion round. When either binds, expansion stops, the states reached so far
are scored, and ``truncated=True`` is returned.

``truncated`` also reports a beam cut, matching
:attr:`~acronymkit.models.GenerationMetadata.truncated` ("the candidate search
hit a beam or time budget"). A cut is exactly the event that can cost the caller
the optimum, so silence about it would leave the one loss the caller might care
about undetectable. Exhaustive mode keeps the flag quiet for the small phrases
that dominate real use: there is nothing to cut, so nothing is reported.

Determinism
-----------
No randomness, no clock-dependent output, no reliance on hash order. Every
frontier cut, every de-duplication collision and the final ranking are resolved
by explicit total orders, so the same input yields byte-identical output across
runs, interpreters and ``PYTHONHASHSEED`` values.
"""

from __future__ import annotations

import bisect
import time
from typing import AbstractSet, Callable, Optional, Sequence

from .config import Config
from .enums import TokenRole
from .exceptions import NoCandidateError
from .models import AcronymCandidate, Token
from .phonetics import has_vowel
from .scoring import Scorer, build_mappings

__all__ = ["ForwardGenerator"]

#: One ``(token_index, letters_taken)`` donation record.
_Take = tuple[int, int]

#: A partial (or complete) search state: the accumulated characters plus the
#: ordered donation records that produced them.
_State = tuple[str, tuple[_Take, ...]]

#: De-duplication key for the frontier: the accumulated string plus the ordered
#: indices of the donating tokens. Two states sharing this key necessarily share
#: their positional term and their ``covered`` set, so collapsing them is exact
#: rather than lossy.
_StateKey = tuple[str, tuple[int, ...]]

#: Value of ``Lambda(A)`` that counts as a dictionary hit.
_LEXICAL_HIT = 1.0

#: Predicate answering "could this prefix still grow into a lexicon word?".
_PrefixProbe = Callable[[str], bool]

#: Milliseconds per second, for converting ``search_time_budget_ms``.
_MS_PER_SECOND = 1000.0


class ForwardGenerator:
    """Beam-search generator for forward (phrase -> acronym) generation.

    The generator holds no mutable state: it is safe to build one per engine and
    share it across threads. All configuration is read from the
    :class:`~acronymkit.config.Config` supplied at construction, and all
    arithmetic is delegated to the injected :class:`~acronymkit.scoring.Scorer`.

    Example:
        >>> from acronymkit.config import Config
        >>> from acronymkit.scoring import Scorer
        >>> from acronymkit.tokenizer import Tokenizer
        >>> config = Config()
        >>> generator = ForwardGenerator(config, Scorer(config))
        >>> tokens = Tokenizer(config).tokenize("Portable Document Format")
        >>> candidates, evaluated, truncated = generator.generate(tokens)
        >>> "PDF" in [candidate.acronym for candidate in candidates]
        True
        >>> truncated
        False

    Args:
        config: Engine configuration governing the search shape, the budgets and
            the final filters.
        scorer: Scorer supplying ``S(A, T)``, the effective
            :class:`~acronymkit.config.ScoringWeights` and the lexicon /
            n-gram collaborators.
    """

    __slots__ = ("_config", "_scorer")

    def __init__(self, config: Config, scorer: Scorer) -> None:
        self._config = config
        self._scorer = scorer

    # -- properties --------------------------------------------------------
    @property
    def config(self) -> Config:
        """The configuration this generator was built from."""
        return self._config

    @property
    def scorer(self) -> Scorer:
        """The scorer used to rank candidates."""
        return self._scorer

    def __repr__(self) -> str:  # pragma: no cover - display helper
        return (
            f"ForwardGenerator(beam={self._config.search_beam_width}, "
            f"max_nodes={self._config.max_search_nodes}, "
            f"max_length={self._config.max_acronym_length})"
        )

    # -- public API --------------------------------------------------------
    def generate(self, tokens: Sequence[Token]) -> tuple[list[AcronymCandidate], int, bool]:
        """Search for acronym candidates over ``tokens``.

        The returned list is ordered best-first by ``(-score, len(acronym),
        acronym)`` and truncated to
        :attr:`~acronymkit.config.Config.max_candidates`. Every acronym string
        appears at most once; when several alignments produce the same string the
        highest-scoring one is kept, breaking ties on more ``INITIAL`` mappings
        and then on fewer skipped critical tokens.

        The plain initialism is injected into the candidate pool before scoring
        (see the module docstring), so no amount of searching can lose it: it is
        always scored, and it is returned whenever it satisfies the active
        filters and ``max_candidates >= 2``. At ``max_candidates == 1`` the
        single slot belongs to the top-ranked candidate, which need not be the
        initialism. Its *rank*, in any case, is decided by ``S(A, T)`` like
        everyone else's.

        Args:
            tokens: The complete token sequence for the phrase, as produced by
                :meth:`~acronymkit.tokenizer.Tokenizer.tokenize`. Indices in the
                returned mappings refer to :attr:`~acronymkit.models.Token.index`
                values, so the *full* sequence must be passed, not a filtered
                subset.

        Returns:
            A ``(candidates, candidates_evaluated, truncated)`` triple.
            ``candidates_evaluated`` counts the partial states enumerated during
            the search (the quantity capped by
            :attr:`~acronymkit.config.Config.max_search_nodes`) and ``truncated``
            reports whether a node budget, a time budget or a beam cut cost the
            search states it never scored. It stays ``False`` for any phrase
            whose whole search space fits the node budget, which is the common
            case.

        Raises:
            NoCandidateError: If ``tokens`` is empty, contains no token able to
                donate characters, or if every state was rejected by the length,
                vowel or dictionary filters. The engine converts blank input into
                :class:`~acronymkit.exceptions.EmptyPhraseError` before calling
                here; the empty-sequence check is a defensive backstop.
        """
        if not tokens:
            raise NoCandidateError("cannot generate an acronym from an empty token sequence")

        eligible = [token for token in tokens if token.is_eligible and token.letters]
        if not eligible:
            raise NoCandidateError(
                "no eligible tokens: every token was filtered out by the active "
                "stop-word, minimum-word-length or numeral policy"
            )

        states, evaluated, truncated = self._search(eligible)

        pool: list[_State] = list(states)
        initialism = self._plain_initialism(eligible)
        if initialism is not None:
            pool.append(initialism)

        ranked = self._finalise(pool, tokens)
        if not ranked:
            raise NoCandidateError(self._failure_reason(eligible))
        return self._limit(ranked, initialism), evaluated, truncated

    def _limit(
        self, ranked: list[AcronymCandidate], initialism: Optional[_State]
    ) -> list[AcronymCandidate]:
        """Cut ``ranked`` to ``max_candidates``, reserving a slot for the initialism.

        Searching cannot lose the plain initialism, but ordinary top-N truncation
        still can: on a long phrase, ``max_candidates`` higher-scoring acronyms
        may sit above it. The final slot is therefore given back to it when it
        would otherwise be cut. Because the initialism ranked below every
        candidate that is kept, placing it last leaves the list correctly ordered
        by ``(-score, len(acronym), acronym)``.

        The reservation needs a list of at least two, and at
        ``max_candidates == 1`` it is deliberately *not* made: the only slot
        available holds the top-ranked candidate, and the swap would only ever
        fire to replace it with something that scored strictly lower. That would
        turn :attr:`~acronymkit.models.AcronymResult.primary_acronym` into the
        plain initialism for every latency-sensitive caller — a ranking override,
        which the safety net explicitly is not. The initialism is one slot away
        for anyone who wants it; see the module docstring for the guarantee as
        stated.

        Args:
            ranked: The complete candidate list, already sorted best-first.
            initialism: The injected plain-initialism state, or ``None``.

        Returns:
            At most ``max_candidates`` candidates, still in ranked order.
        """
        limit = self._config.max_candidates
        result = ranked[:limit]
        if initialism is None or limit <= 1 or len(ranked) <= limit:
            return result
        cased = self._config.case_style.apply(initialism[0])
        if any(candidate.acronym == cased for candidate in result):
            return result
        for candidate in ranked[limit:]:
            if candidate.acronym == cased:
                return [*result[: limit - 1], candidate]
        return result

    # -- search ------------------------------------------------------------
    def _search(self, eligible: Sequence[Token]) -> tuple[list[_State], int, bool]:
        """Run the left-to-right search over ``eligible``.

        The search is *exhaustive* — no beam cut whatsoever — whenever the whole
        space demonstrably fits inside
        :attr:`~acronymkit.config.Config.max_search_nodes`, and a beam search
        ranked by :meth:`_beam_bound` otherwise. See the module docstring for
        both regimes.

        Args:
            eligible: Tokens permitted to donate characters, in phrase order.

        Returns:
            A ``(states, evaluated, truncated)`` triple where ``states`` is the
            surviving frontier, ``evaluated`` is the number of successor states
            enumerated and ``truncated`` reports whether a budget or a beam cut
            cost the search states it never scored.
        """
        config = self._config
        max_length = config.max_acronym_length
        max_nodes = config.max_search_nodes
        allow_skip = config.allow_token_skipping
        branches = self._branches(eligible)
        deadline = self._deadline(config.search_time_budget_ms)

        # Exhaustive whenever the entire space fits the node budget the caller
        # declared: a cut inside a budget nobody exceeded can only lose the
        # optimum. See the module docstring for what that costs.
        beam_width: Optional[int] = (
            None if self._fits_exhaustively(branches) else config.search_beam_width
        )
        critical = frozenset(token.index for token in eligible if token.is_critical)
        probe = self._word_prefix_probe()
        remaining = len(eligible)

        frontier: list[_State] = [("", ())]
        evaluated = 0
        truncated = False
        passed_critical = 0

        for token, pieces in zip(eligible, branches):
            if evaluated >= max_nodes or self._expired(deadline):
                truncated = True
                break
            remaining -= 1
            if token.is_critical:
                # Every state leaving this round has either covered ``token`` or
                # skipped it for good, so its contribution to Psi is now known.
                passed_critical += 1

            successors: dict[_StateKey, _State] = {}
            exhausted = False
            for position, (chars, takes) in enumerate(frontier):
                if evaluated >= max_nodes:
                    # Carry the unexpanded tail forward unchanged rather than
                    # discarding it: those states are already valid acronyms.
                    truncated = True
                    exhausted = True
                    for carried in frontier[position:]:
                        self._offer(successors, carried)
                    break
                if allow_skip:
                    evaluated += 1
                    self._offer(successors, (chars, takes))
                room = max_length - len(chars)
                for piece in pieces:
                    if len(piece) > room:
                        # ``pieces`` is ordered by increasing length.
                        break
                    evaluated += 1
                    self._offer(
                        successors,
                        (chars + piece, (*takes, (token.index, len(piece)))),
                    )

            if not successors:
                # Every branch overflowed ``max_acronym_length`` and skipping is
                # disabled: the search cannot continue.
                frontier = []
                break
            frontier = list(successors.values())
            if beam_width is not None and len(frontier) > beam_width:
                frontier = self._prune(
                    frontier,
                    beam_width,
                    self._completion_table(remaining),
                    passed_critical,
                    critical,
                    probe,
                )
                # A cut is the one event that can silently cost the caller the
                # optimum, so it is reported rather than swallowed.
                truncated = True
            if exhausted:
                break

        return frontier, evaluated, truncated

    def _fits_exhaustively(self, branches: Sequence[tuple[str, ...]]) -> bool:
        """Return whether the *whole* search space fits the node budget.

        Round ``i`` expands at most ``prod(factors[:i])`` states into
        ``factors[i]`` successors each, where ``factors[i]`` is the number of
        branches of token ``i`` plus one for the skip branch. Summing those
        products bounds the successors an unpruned search would enumerate — the
        exact quantity :attr:`~acronymkit.config.Config.max_search_nodes` caps.
        The bound ignores both de-duplication and the ``max_acronym_length``
        cut-off, so it over-states the real count and never claims a space fits
        when it does not.

        Args:
            branches: Per-token letter pieces, as built by :meth:`_branches`.

        Returns:
            ``True`` when the search may run without any beam cut. The running
            total is compared against the budget every round, so the products
            are abandoned long before they can grow large.
        """
        budget = self._config.max_search_nodes
        skip = 1 if self._config.allow_token_skipping else 0
        reachable = 1
        total = 0
        for pieces in branches:
            factor = len(pieces) + skip
            total += reachable * factor
            if total > budget:
                return False
            reachable *= factor
        return True

    def _word_prefix_probe(self) -> Optional[_PrefixProbe]:
        """Return a "could still become a dictionary word" test, or ``None``.

        The lexicon is duck-typed (see :class:`~acronymkit.scoring.Scorer`), so
        the probe is offered only when the object exposes ``starting_with`` and
        ``gamma`` is non-zero; otherwise the lexical term is a constant across
        the frontier and bounding it would change no ranking.

        Returns:
            A memoised predicate mapping an accumulated prefix to whether any
            lexicon entry begins with it, or ``None`` when no useful probe
            exists. ``starting_with`` is called with a *single* character, which
            the lexicon answers from an index in O(1); the prefix is then located
            inside that sorted bucket with :func:`bisect.bisect_left`, so no
            result tuple is ever materialised. The cache lives for one search
            only, keeping the generator itself stateless and thread-safe.
        """
        lexicon = self._scorer.lexicon
        if lexicon is None or not float(self._scorer.weights.gamma):
            return None
        starting_with = getattr(lexicon, "starting_with", None)
        if starting_with is None:
            return None
        cache: dict[str, bool] = {}

        def probe(chars: str) -> bool:
            key = chars.casefold()
            cached = cache.get(key)
            if cached is None:
                bucket: Sequence[str] = starting_with(key[:1])
                position = bisect.bisect_left(bucket, key)
                cached = position < len(bucket) and bucket[position].startswith(key)
                cache[key] = cached
            return cached

        return probe

    def _completion_table(self, remaining: int) -> list[float]:
        """Tabulate the best net gain still reachable, by current prefix length.

        Entry ``length`` is the maximum, over every number of characters the
        state could still add, of the positional term those characters would
        contribute *minus* the extra length penalty they would incur. Both are
        linear in the number added, so maximising them jointly is what keeps the
        bound tight rather than merely valid.

        The positional part assumes the most generous legal arrangement: at most
        one ``INITIAL`` per remaining token and every further character
        ``CONTIGUOUS``, with at least one ``INITIAL`` before any ``CONTIGUOUS``
        because the search never returns to a token it has passed. Both extremes
        of that linear trade-off are evaluated, so the table is an upper bound
        even for configurations where ``contiguous_weight`` exceeds
        ``initial_weight``. The per-token letter cap is deliberately ignored:
        respecting it could only lower the bound, and an ``ACRONYM`` token is
        allowed to exceed it anyway.

        Args:
            remaining: Number of tokens the search has not yet visited.

        Returns:
            A list of length ``max_acronym_length + 1``, indexed by the number of
            characters accumulated so far. Every entry is ``>= 0.0``, since
            adding nothing is always allowed.
        """
        weights = self._scorer.weights
        max_length = self._config.max_acronym_length
        alpha = float(weights.alpha)
        initial = alpha * float(weights.initial_weight)
        contiguous = alpha * float(weights.contiguous_weight)
        penalty = float(weights.length_penalty)
        preferred = int(weights.preferred_length)

        table: list[float] = []
        for length in range(max_length + 1):
            best = 0.0
            charged = max(0, length - preferred)
            if remaining > 0:
                for added in range(1, max_length - length + 1):
                    initials = min(added, remaining)
                    gain = max(
                        initial + (added - 1) * contiguous,
                        initials * initial + (added - initials) * contiguous,
                    )
                    gain -= penalty * (max(0, length + added - preferred) - charged)
                    best = max(best, gain)
            table.append(best)
        return table

    def _branches(self, eligible: Sequence[Token]) -> list[tuple[str, ...]]:
        """Pre-compute the letter pieces each eligible token may donate.

        Args:
            eligible: Tokens permitted to donate characters, in phrase order.

        Returns:
            One tuple per token, ordered by increasing piece length. An
            ``ACRONYM``-role token yields exactly one piece — its whole
            ``letters`` string — because an existing acronym is atomic.
        """
        config = self._config
        limit = config.max_letters_per_token if config.allow_multi_letter_tokens else 1
        limit = max(1, limit)
        branches: list[tuple[str, ...]] = []
        for token in eligible:
            letters = token.letters
            if token.role is TokenRole.ACRONYM:
                branches.append((letters,))
                continue
            cap = min(limit, len(letters))
            branches.append(tuple(letters[:count] for count in range(1, cap + 1)))
        return branches

    def _plain_initialism(self, eligible: Sequence[Token]) -> Optional[_State]:
        """Build the plain initialism state injected as a safety net.

        One character is taken from every eligible token — the whole ``letters``
        string for an ``ACRONYM``-role token — and the result is capped at
        ``max_acronym_length``.

        An ``ACRONYM``-role token is **atomic**: it contributes all of its
        characters or none of them. When its full width does not fit in the
        remaining room the token is skipped rather than clipped, so an existing
        ``"API"`` can never degrade into ``"AP"`` or ``"A"``. This matches the
        beam search, which offers such a token as a single indivisible branch.
        Ordinary tokens contribute a single initial, so they are unaffected.

        Args:
            eligible: Tokens permitted to donate characters, in phrase order.

        Returns:
            The corresponding state, or ``None`` when no token could contribute
            a character.
        """
        max_length = self._config.max_acronym_length
        chars = ""
        takes: list[_Take] = []
        for token in eligible:
            atomic = token.role is TokenRole.ACRONYM
            piece = token.letters if atomic else token.letters[:1]
            if not piece:
                continue
            room = max_length - len(chars)
            if room <= 0:
                break
            if len(piece) > room:
                # An atomic acronym that does not fit is dropped whole; a
                # single-character take can never reach here (room >= 1).
                continue
            chars += piece
            takes.append((token.index, len(piece)))
        if not chars:
            return None
        return (chars, tuple(takes))

    # -- frontier bookkeeping ---------------------------------------------
    @staticmethod
    def _offer(successors: dict[_StateKey, _State], state: _State) -> None:
        """Insert ``state`` into ``successors``, collapsing exact duplicates.

        States sharing a :data:`_StateKey` have identical characters, identical
        ``covered`` sets and therefore an identical positional term; only the
        internal split of the characters across tokens can differ. The
        lexicographically smallest ``takes`` tuple is retained so the choice is
        deterministic.

        Args:
            successors: Accumulator for the next frontier, keyed by
                :data:`_StateKey`.
            state: The candidate successor state.
        """
        key: _StateKey = (state[0], tuple(index for index, _ in state[1]))
        current = successors.get(key)
        if current is None or state[1] < current[1]:
            successors[key] = state

    def _prune(
        self,
        states: list[_State],
        beam_width: int,
        completion: Sequence[float],
        passed_critical: int,
        critical: AbstractSet[int],
        probe: Optional[_PrefixProbe],
    ) -> list[_State]:
        """Cut ``states`` back to the ``beam_width`` best partial states.

        Called only when a cut is actually needed; :meth:`_search` skips it
        entirely in exhaustive mode and whenever the frontier already fits.

        Args:
            states: The freshly generated frontier.
            beam_width: Maximum number of states to retain.
            completion: Table from :meth:`_completion_table` for this round.
            passed_critical: Critical tokens the round has finished deciding.
            critical: Indices of the critical eligible tokens.
            probe: Dictionary-prefix predicate, or ``None``.

        Returns:
            The retained states, ranked by descending :meth:`_beam_bound` with a
            total tie-break on ``(length, characters, takes)`` so the cut is
            deterministic.
        """
        states.sort(
            key=lambda state: (
                -self._beam_bound(state, completion, passed_critical, critical, probe),
                len(state[0]),
                state[0],
                state[1],
            )
        )
        return states[:beam_width]

    def _beam_bound(
        self,
        state: _State,
        completion: Sequence[float],
        passed_critical: int,
        critical: AbstractSet[int],
        probe: Optional[_PrefixProbe],
    ) -> float:
        """Return an optimistic bound on the best total ``state`` can still reach.

        The bound is admissible: it equals or exceeds the score of every
        completion of ``state``, so the beam never cuts a state in favour of one
        that provably cannot beat it. See the module docstring for the term-by-
        term derivation; in short the positional and information-loss parts that
        are already settled are charged exactly, the length penalty is charged
        on the characters accumulated so far (it can only grow), the reachable
        remainder comes from ``completion``, ``Lambda`` is credited whenever a
        lexicon word can still start with the prefix, and ``beta * Phi`` is
        omitted because a mean bigram log-likelihood is never positive.

        Args:
            state: The partial state to rank.
            completion: Table from :meth:`_completion_table` for this round.
            passed_critical: Critical tokens the round has finished deciding.
            critical: Indices of the critical eligible tokens.
            probe: Dictionary-prefix predicate, or ``None``. ``None`` credits
                ``gamma`` to every state, which is a constant and therefore
                ranks nothing.

        Returns:
            The bound, in the same units as
            :attr:`~acronymkit.models.ScoreBreakdown.total`.
        """
        chars, takes = state
        weights = self._scorer.weights
        length = len(chars)
        value = float(weights.alpha) * self._positional(length, len(takes))
        value -= float(weights.length_penalty) * max(0, length - int(weights.preferred_length))
        value += completion[length]
        dropped = passed_critical - sum(1 for index, _ in takes if index in critical)
        value -= float(weights.delta) * dropped
        gamma = float(weights.gamma)
        if gamma and (probe is None or probe(chars)):
            value += gamma
        return value

    def _positional(self, length: int, takes: int) -> float:
        """Return the exact positional term of a state.

        Characters drawn from one token are classified ``INITIAL`` for the first
        and ``CONTIGUOUS`` for each subsequent one, so the sum of ``omega``
        collapses to a closed form that needs no
        :class:`~acronymkit.models.LetterMapping` objects.

        Args:
            length: Number of characters accumulated so far.
            takes: Number of tokens that donated characters.

        Returns:
            ``takes * initial_weight + (length - takes) * contiguous_weight``.
        """
        weights = self._scorer.weights
        return takes * float(weights.initial_weight) + (length - takes) * float(
            weights.contiguous_weight
        )

    # -- budgets -----------------------------------------------------------
    @staticmethod
    def _deadline(budget_ms: Optional[float]) -> Optional[float]:
        """Return the :func:`time.perf_counter` instant the search must stop at.

        Args:
            budget_ms: Wall-clock budget in milliseconds, or ``None``.

        Returns:
            The absolute deadline, or ``None`` when the search is unbounded.
        """
        if budget_ms is None:
            return None
        return time.perf_counter() + budget_ms / _MS_PER_SECOND

    @staticmethod
    def _expired(deadline: Optional[float]) -> bool:
        """Return whether ``deadline`` has passed.

        Args:
            deadline: Absolute :func:`time.perf_counter` deadline, or ``None``.

        Returns:
            ``True`` when a deadline exists and has been reached.
        """
        return deadline is not None and time.perf_counter() >= deadline

    # -- finalisation ------------------------------------------------------
    def _finalise(
        self, states: Sequence[_State], tokens: Sequence[Token]
    ) -> list[AcronymCandidate]:
        """Filter, de-duplicate, score and rank the search output.

        Args:
            states: Every state to consider, including the injected initialism.
            tokens: The complete token sequence, for ``Psi(T, A)`` and mapping
                bounds checks.

        Returns:
            Scored candidates ordered by ``(-score, len(acronym), acronym)``.
            The list is empty when every state was rejected by a filter.
        """
        config = self._config
        scorer = self._scorer
        weights = scorer.weights
        alpha = float(weights.alpha)
        delta = float(weights.delta)
        critical = {token.index for token in tokens if token.is_critical}
        minimum = config.min_acronym_length
        maximum = config.max_acronym_length
        case_style = config.case_style

        # cased acronym -> (selection key, winning takes, covered indices)
        best: dict[str, tuple[tuple[float, int, float], tuple[_Take, ...], set[int]]] = {}
        for chars, takes in states:
            if not minimum <= len(chars) <= maximum:
                continue
            cased = case_style.apply(chars)
            if config.require_vowel and not has_vowel(cased):
                continue
            if config.require_dictionary_word and scorer.lexical_term(cased) < _LEXICAL_HIT:
                continue
            covered = {index for index, _ in takes}
            loss = float(len(critical - covered))
            # Candidates sharing ``cased`` share Phi(A) and Lambda(A), so the
            # positional and information-loss terms alone decide which alignment
            # scores highest. Ties fall back to more INITIAL mappings (one per
            # donating token), then to fewer skipped critical tokens.
            key = (
                alpha * self._positional(len(chars), len(takes)) - delta * loss,
                len(takes),
                -loss,
            )
            current = best.get(cased)
            if current is None or key > current[0] or (key == current[0] and takes < current[1]):
                best[cased] = (key, takes, covered)

        candidates: list[AcronymCandidate] = []
        for cased, (_, takes, covered) in best.items():
            mappings = build_mappings(cased, self._assignments(takes), tokens, weights)
            candidates.append(scorer.build_candidate(cased, tokens, mappings, covered))
        candidates.sort(key=lambda item: (-item.score, len(item.acronym), item.acronym))
        return candidates

    @staticmethod
    def _assignments(takes: Sequence[_Take]) -> list[tuple[int, Optional[int], Optional[int]]]:
        """Expand donation records into per-character assignment triples.

        Args:
            takes: Ordered ``(token_index, letters_taken)`` records.

        Returns:
            ``(position, token_index, char_offset)`` triples in acronym order,
            ready for :func:`~acronymkit.scoring.build_mappings`. Offsets index
            into :attr:`~acronymkit.models.Token.letters`, so offset ``0`` is the
            token initial and every further offset continues the run.
        """
        assignments: list[tuple[int, Optional[int], Optional[int]]] = []
        position = 0
        for token_index, count in takes:
            for offset in range(count):
                assignments.append((position, token_index, offset))
                position += 1
        return assignments

    def _failure_reason(self, eligible: Sequence[Token]) -> str:
        """Compose an actionable message for an empty candidate pool.

        Args:
            eligible: Tokens that were permitted to donate characters.

        Returns:
            A human-readable explanation naming the constraints most likely to
            be responsible.
        """
        config = self._config
        reasons = [
            f"no acronym of length {config.min_acronym_length}-"
            f"{config.max_acronym_length} could be built from "
            f"{len(eligible)} eligible token(s)"
        ]
        if config.require_dictionary_word:
            reasons.append("require_dictionary_word=True left no dictionary hit")
        if config.require_vowel:
            reasons.append("require_vowel=True rejected every vowel-free candidate")
        if not config.allow_token_skipping:
            reasons.append("allow_token_skipping=False forbids dropping any token")
        return "; ".join(reasons)
