"""Per-candidate corpus statistics, derived from unlabelled text.

Why this module exists
----------------------
Two selection experiments in this project consumed a *per-strategy* signal to
make a *per-span* decision, and both failed for the same structural reason: the
competing spans in the cases we get wrong are explained by the *same* matching
rule, so no per-rule number can separate them (see ``docs/DECISIONS.md`` D-010
and D-012). ``"International Index of Erectile Function"`` and
``"Index of Erectile Function"`` are both plain word-initial alignments.

What separates them is not the rule. It is whether the language actually puts
those words together. That is a property of the *span*, so it is measurable per
candidate, and it is measurable from raw text with no annotation at all — which
is the same property that makes :mod:`acronymkit._pseudo_precision` usable on a
domain with no gold standard.

Ab3P's answer to the same problem is ``SingTermFreq.dat``: 31 MB of shipped
term-frequency data. Deriving the equivalent here rather than vendoring theirs
is deliberate. It works on any domain, it is ours, and :meth:`TermStatistics.prune`
makes its size a choice rather than a constant.

The three statistics
--------------------
**Document frequency.** How many documents a word occurs in. Function words
occur nearly everywhere; the words that name a thing do not. Exposed directly
and as :meth:`TermStatistics.specificity`, an inverse-document-frequency
rescaled to ``[0, 1]``.

**Adjacent-word association.** Normalised pointwise mutual information (Bouma,
2009) over adjacent token pairs, so the value is bounded in ``[-1, 1]`` and
therefore comparable between pairs of very different frequency. Raw PMI is not:
it is maximised by pairs that occur once each and only together, which is
exactly the noise a small corpus is full of.

Two count floors guard that further. A pair observed fewer than ``min_count``
times scores ``0.0`` — no evidence, not evidence of no association — and what
survives is multiplied by the Pantel & Lin (2002) discount
``c/(c + k) · m/(m + k)``, monotone in the pair count ``c`` and in the rarer
constituent's count ``m``. A pair seen twice is therefore below the floor
outright at the default setting, and a pair just above it is held well under the
ceiling a pair seen two hundred times can reach.

**A boundary statistic: left-branching entropy.** Every candidate span ends at
the same place — the opening bracket — so the only free choice is the *left*
edge, and the boundary statistic has to be about left edges specifically.

The obvious candidate, *how often a word begins a candidate span versus occurring
inside one*, cannot be derived here, and it is worth writing down why: the
candidate space is every suffix of the window, so each occurrence of a word
begins exactly one candidate and sits inside every longer one. The ratio is a
function of position in the window and nothing else. It carries no information
about the word.

The derivable analogue is Harris's (1955) variation criterion, used for
unsupervised segmentation by Jin & Tanaka-Ishii (2006): count the *distinct*
words observed immediately to a word's left in running text. A word that follows
many different words is one the language permits a cut in front of; a word that
almost always follows the same word is bound to it and cutting there splits a
unit. Entropy rather than raw variety, so that one dominant predecessor is not
disguised by a long tail of rare ones, and normalised by the log of the
observation count so the value is bounded and does not simply reward frequency.

Note that this statistic alone cannot pick a span: ``"the"`` and ``"and"`` follow
a great many different words and score high. It has to be read together with
specificity, which is exactly why both are here.

Tier 0 pure: standard library only.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from acronymkit._strategies import split_long_form

__all__ = [
    "TermStatistics",
    "build_statistics",
    "segment",
    "tokenise",
]

#: Punctuation that ends a clause. Adjacency is not counted across one, because
#: a bigram spanning a full stop describes the corpus's sentence order rather
#: than any property of the two words. Commas are deliberately *not* here: a
#: long form may legitimately contain one (``2,6-diaminopurine``).
_CLAUSE_BREAK = re.compile(r"[.;:!?()\[\]{}…]+")


def segment(text: str) -> List[str]:
    """Split ``text`` at clause punctuation.

    Args:
        text: Raw document text.

    Returns:
        The clause-level pieces, in order. Empty pieces are dropped.
    """
    return [piece for piece in _CLAUSE_BREAK.split(text) if piece.strip()]


def tokenise(text: str) -> List[str]:
    """Case-fold ``text`` into the same tokens the candidate spans are built from.

    :func:`acronymkit._strategies.split_long_form` is reused rather than a local
    regular expression, because a statistic computed over different units than
    the spans it scores is measuring something else.

    Args:
        text: A clause, or any text.

    Returns:
        Case-folded alphanumeric tokens, in order.
    """
    return [word.casefold() for word, _start, _end in split_long_form(text)]


@dataclass
class TermStatistics:
    """Counts over an unlabelled corpus, plus the measures derived from them.

    Attributes:
        documents: Number of documents the counts were built from.
        tokens: Total token occurrences.
        pairs: Total adjacent token pairs.
        unigram: ``{word: occurrences}``.
        bigram: ``{left: {right: occurrences}}`` for adjacent pairs.
        document_frequency: ``{word: documents containing it}``.
        left_entropy: ``{word: entropy of its left-neighbour distribution}``,
            in nats and un-normalised; :meth:`left_boundary` rescales it.
        left_observations: ``{word: occurrences that had a left neighbour}``.
        min_count: Pair-count floor. Below it :meth:`association` reports no
            evidence, and the surviving discount uses it as ``k``.
    """

    documents: int = 0
    tokens: int = 0
    pairs: int = 0
    unigram: Dict[str, int] = field(default_factory=dict)
    bigram: Dict[str, Dict[str, int]] = field(default_factory=dict)
    document_frequency: Dict[str, int] = field(default_factory=dict)
    left_entropy: Dict[str, float] = field(default_factory=dict)
    left_observations: Dict[str, int] = field(default_factory=dict)
    min_count: int = 3

    # -- primitive lookups -------------------------------------------------
    def frequency(self, word: str) -> int:
        """Occurrences of ``word`` in the corpus."""
        return self.unigram.get(word, 0)

    def documents_containing(self, word: str) -> int:
        """Number of documents ``word`` occurs in."""
        return self.document_frequency.get(word, 0)

    def pair_count(self, left: str, right: str) -> int:
        """Occurrences of ``left`` immediately followed by ``right``."""
        return self.bigram.get(left, {}).get(right, 0)

    # -- derived measures --------------------------------------------------
    def specificity(self, word: str) -> float:
        """Inverse document frequency of ``word``, rescaled to ``[0, 1]``.

        ``1.0`` means the word was never seen and is treated as maximally
        specific — which is the right default here, because an unseen word in a
        biomedical abstract is far more often a technical term than a function
        word. ``0.0`` means it occurs in every document.

        Args:
            word: Case-folded token.

        Returns:
            A value in ``[0, 1]``.
        """
        if self.documents <= 1:
            return 1.0
        seen = self.document_frequency.get(word, 0)
        return min(1.0, math.log(self.documents / (1 + seen)) / math.log(self.documents))

    def association(self, left: str, right: str) -> float:
        """Discounted normalised PMI of the adjacent pair ``(left, right)``.

        Args:
            left: Case-folded first token.
            right: Case-folded second token.

        Returns:
            A value in ``[-1, 1]``. ``0.0`` when the pair was observed fewer
            than :attr:`min_count` times, which reports *absence of evidence*
            rather than evidence of independence.
        """
        joint = self.pair_count(left, right)
        if joint < self.min_count or not self.pairs or not self.tokens:
            return 0.0
        left_count = self.unigram.get(left, 0)
        right_count = self.unigram.get(right, 0)
        if not left_count or not right_count:
            return 0.0

        joint_probability = joint / self.pairs
        expected = (left_count / self.tokens) * (right_count / self.tokens)
        if expected <= 0.0:
            return 0.0
        normalised = math.log(joint_probability / expected) / -math.log(joint_probability)

        floor = float(self.min_count)
        rarer = float(min(left_count, right_count))
        discount = (joint / (joint + floor)) * (rarer / (rarer + floor))
        return max(-1.0, min(1.0, normalised)) * discount

    def left_boundary(self, word: str, default: float = 0.5) -> float:
        """How freely the language allows a cut immediately before ``word``.

        Left-branching entropy normalised by the log of the number of
        observations, so the result is bounded and a word seen twice with two
        different predecessors does not outrank a word seen two hundred times
        with fifty.

        Args:
            word: Case-folded token.
            default: Returned when the word has fewer than :attr:`min_count`
                observed left contexts. Neutral by design — an unseen word is
                not evidence either way.

        Returns:
            A value in ``[0, 1]``, or ``default``.
        """
        observations = self.left_observations.get(word, 0)
        if observations < self.min_count:
            return default
        ceiling = math.log(observations)
        if ceiling <= 0.0:
            return default
        return max(0.0, min(1.0, self.left_entropy.get(word, 0.0) / ceiling))

    # -- span-level measures -----------------------------------------------
    def cohesion(self, words: Sequence[str]) -> float:
        """Mean adjacent association inside a span.

        A term hangs together: every neighbouring pair inside it is a pair the
        corpus has seen. A span that has swallowed surrounding prose contains
        junctions the corpus has not, and this is what registers that.

        Args:
            words: Case-folded tokens of the span, in order.

        Returns:
            The mean of :meth:`association` over adjacent pairs; ``0.0`` for a
            span of fewer than two words.
        """
        if len(words) < 2:
            return 0.0
        total = sum(self.association(words[i], words[i + 1]) for i in range(len(words) - 1))
        return total / (len(words) - 1)

    def edge_contrast(self, previous: Optional[str], words: Sequence[str]) -> float:
        """How much better the span's left edge is than the cut that made it.

        The quantity that actually distinguishes two spans the same matching
        rule explains: the bond *inside* the left edge minus the bond *across*
        it. Cutting between ``"the"`` and ``"International"`` breaks nothing and
        keeps ``"International Index"`` intact, so the contrast is high; cutting
        between ``"International"`` and ``"Index"`` splits a collocation, so it
        is negative.

        Args:
            previous: The token immediately before the span, or ``None`` when
                the span starts at the beginning of the available context.
            words: Case-folded tokens of the span, in order.

        Returns:
            ``association(words[0], words[1]) - association(previous, words[0])``.
        """
        if not words:
            return 0.0
        inside = self.association(words[0], words[1]) if len(words) > 1 else 0.0
        across = self.association(previous, words[0]) if previous is not None else 0.0
        return inside - across

    # -- size ---------------------------------------------------------------
    def prune(self, min_frequency: int = 2, min_pair_count: int = 2) -> TermStatistics:
        """Drop rare entries, returning a smaller table.

        The lever that makes the size of this resource a decision rather than a
        constant. Totals are left at their pre-pruning values so that the
        probabilities :meth:`association` computes stay normalised against the
        corpus that was actually observed.

        Args:
            min_frequency: Keep words seen at least this many times.
            min_pair_count: Keep pairs seen at least this many times.

        Returns:
            A new :class:`TermStatistics`; the receiver is unchanged.
        """
        unigram = {word: count for word, count in self.unigram.items() if count >= min_frequency}
        bigram: Dict[str, Dict[str, int]] = {}
        for left, rights in self.bigram.items():
            if left not in unigram:
                continue
            kept = {
                right: count
                for right, count in rights.items()
                if count >= min_pair_count and right in unigram
            }
            if kept:
                bigram[left] = kept
        return TermStatistics(
            documents=self.documents,
            tokens=self.tokens,
            pairs=self.pairs,
            unigram=unigram,
            bigram=bigram,
            document_frequency={
                word: count for word, count in self.document_frequency.items() if word in unigram
            },
            left_entropy={
                word: value for word, value in self.left_entropy.items() if word in unigram
            },
            left_observations={
                word: count for word, count in self.left_observations.items() if word in unigram
            },
            min_count=self.min_count,
        )

    def size(self) -> Tuple[int, int]:
        """``(distinct words, distinct adjacent pairs)`` currently stored."""
        return len(self.unigram), sum(len(rights) for rights in self.bigram.values())


def build_statistics(texts: Iterable[str], *, min_count: int = 3) -> TermStatistics:
    """Count a corpus. No labels are read and none are needed.

    Args:
        texts: Raw documents. Only their text is used.
        min_count: Evidence floor carried onto the returned table.

    Returns:
        The populated :class:`TermStatistics`.
    """
    unigram: Dict[str, int] = defaultdict(int)
    bigram: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    left_context: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    document_frequency: Dict[str, int] = defaultdict(int)
    documents = 0
    tokens = 0
    pairs = 0

    for text in texts:
        documents += 1
        seen: set = set()
        for clause in segment(text):
            words = tokenise(clause)
            tokens += len(words)
            for index, word in enumerate(words):
                unigram[word] += 1
                seen.add(word)
                if index:
                    previous = words[index - 1]
                    bigram[previous][word] += 1
                    left_context[word][previous] += 1
                    pairs += 1
        for word in seen:
            document_frequency[word] += 1

    left_entropy: Dict[str, float] = {}
    left_observations: Dict[str, int] = {}
    for word, predecessors in left_context.items():
        total = sum(predecessors.values())
        left_observations[word] = total
        entropy = 0.0
        for count in predecessors.values():
            probability = count / total
            entropy -= probability * math.log(probability)
        left_entropy[word] = entropy

    return TermStatistics(
        documents=documents,
        tokens=tokens,
        pairs=pairs,
        unigram=dict(unigram),
        bigram={left: dict(rights) for left, rights in bigram.items()},
        document_frequency=dict(document_frequency),
        left_entropy=left_entropy,
        left_observations=left_observations,
        min_count=min_count,
    )
