"""The catalog-gap report: which of a schema's tokens no catalog-free method can reach.

:mod:`~acronymkit.catalog.audit` answers *what does this vocabulary do to my
schema*, and to answer it at all it needs a vocabulary. This module answers the
question that comes **before** a vocabulary exists, and needs none::

    Your schema has 69,682 columns and 24,536 distinct tokens. 19,673 of those
    never make a label unreachable. 4,863 do, at least once -- and no
    catalog-free method will ever reach those, however good it gets. Here they
    are, ranked by how many columns each one costs you.

Those are the measured figures for one real corpus, saved under
``catalog_gap.socrata.census`` and read out in ``docs/GOVERNED_NAMING.md``. They
are printed here rather than invented ones so that a docstring example and the
gated run cannot drift into disagreeing.

The derivation, which is the whole reason this is exact rather than probabilistic
---------------------------------------------------------------------------------
With no catalog, :func:`~acronymkit.catalog.expansion.expand_token` falls
through to ``PASSTHROUGH``: the answer for token ``T`` is ``Title(T)``, and it
is the only answer available. Generalise off this library and the statement gets
stronger rather than weaker: **a catalog-free method emits, for an identifier,
exactly the characters that identifier carries** -- it may re-cut them and
re-case them, and it may not invent one. So if the human wording of a column
carries a character the identifier does not, no catalog-free method reaches that
wording. Not this library's. Not a better one. Not one nobody has written yet.

That is a derivation about what a method *can emit*, not a measurement of how
often one is right, and it does not soften with a bigger model. It is the same
argument ``docs/POSITIONING.md`` makes when it calls the empty catalog's ``0``
of ``486`` on abbreviated token positions "a derivation and not a result".

Two statements come out of it and they are not equally strong
-------------------------------------------------------------
**The column-level statement is exact and assumes nothing.** Compare the
identifier's alphanumeric character stream, case-folded, with the label's. If
they differ, the label is unreachable: :attr:`CatalogGap.unreachable_columns`
counts a property of two strings and there is no judgement anywhere in it. The
key is :func:`stream_key`, and it is byte-for-byte the rule ``tools/byoc_eval.py``
calls ``stream_key`` and reports as ``pairs_where_label_expands`` -- deliberately,
so the two tools put the same number under the same population and a caller can
run both over one CSV.

**The token-level attribution is a necessary condition, and it is the softer
half.** A token that is not a whole word of the label is *individually
sufficient* to make that label unreachable -- exact, because the catalog-free
phrase is the title-cased tokens joined, so a token matching no label word
cannot be one of the label's words. What is not exact is the converse: a label
can be unreachable with every token present, because the label simply says more
than the identifier does (``LEGAL_DESC`` -> *Property Legal Description*). Those
columns carry no work item at all. They are counted on
:attr:`CatalogGap.unattributed_columns` rather than dropped, because a reader who
takes the ranked table for the whole of the gap is reading past a quarter of it.

What was tried, measured and thrown away: the label-free classifier
-------------------------------------------------------------------
The obvious way to avoid asking the caller for labels is to decide, from the
token alone, whether it is a word -- ``CUSTOMER`` is, ``CUSTMR`` is not -- using
the English word list this package already ships. It was scored against the
whole Socrata identifier/caption population before a line of this module was
written. **It is wrong about most of the tokens it flags**: the false-positive
rate is ``catalog_gap.socrata.word_list_control.false_positive_pct``, and the
causes are structural rather than tunable -- other languages (``FECHA``,
``NOMBRE``, ``DE``), ordinals (``1ST``, ``25TH``), domain vocabulary and
concatenations. An English word list will not stop being wrong about those.

So **there is no word list in this module**, nothing here imports
:mod:`acronymkit.lexicon`, and a column with no label is reported as unlabelled
rather than guessed at. The rejected arm is saved rather than deleted, because a
later reader will have the same idea.

The ranking is by column count, and that is an assumption about the reader
--------------------------------------------------------------------------
The table is ordered by how many distinct columns each token makes unreachable,
because clearing the row that touches the most columns is the cheapest first
move **if** what a governance function wants is coverage per row written.
**This project has never had a governance function to ask** -- ``docs/SOURCING.md``
section 0 measures that there is no inbound adopter at all -- so that is a guess
about users, not a finding about them.

Rather than hedge it in prose, the report computes what a greedy set cover of the
same budget would have reached on the caller's own data and prints both;
:attr:`CatalogGap.ranking_cost_points` is the gap between them. If the ranking is
the wrong one for them, that number says so on their schema instead of leaving
them to find out.

What this costs
---------------
One tokenizer pass and, for a labelled column whose stream differs, one label
word-set per **distinct** identifier -- not per occurrence, and none at all for
the column-level count. One catalog lookup per **distinct** unreachable token,
and **zero** when no catalog is supplied, which is what "needs no catalog" means
in work rather than in prose. Every one of those counts rides on the returned
record (:attr:`CatalogGap.tokenizer_passes`, :attr:`CatalogGap.label_word_sets`,
:attr:`CatalogGap.catalog_lookups`, :attr:`CatalogGap.greedy_set_operations`),
because a throughput figure with no work count cannot distinguish code that got
faster from code that stopped doing the work.

Worked examples use the fictional **Northwind Data Standards** (``NDS``)
catalog. Nothing here describes a real organisation's schema or standard.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Optional, Union

from ..core.exceptions import ConfigurationError
from .dictionary import GovernedDictionary
from .expansion import expand_token
from .models import GovernedEntry, _freeze_sequences, _FrozenModel
from .policy import NamingPolicy
from .tokenizer import split_identifier_parts

__all__ = [
    "CatalogGap",
    "GapToken",
    "catalog_gap",
    "label_words",
    "render_gap",
    "stream_key",
]


def stream_key(text: str) -> str:
    """The case-folded alphanumeric character stream of ``text``.

    Two strings sharing this key differ only in where the words were cut and how
    they were cased -- both of which a catalog-free method is free to change. Two
    that do not share it differ in the characters themselves, which is exactly
    what a catalog-free method cannot invent.

    ``casefold`` is applied to the whole string **before** the alphanumeric
    filter, not after, because ``tools/byoc_eval.py`` does it in that order and
    the two must agree on the population or the composition this module is for
    stops being checkable. The order is observable: ``"İ".casefold()`` is
    ``"i"`` followed by a combining dot, and the dot is not alphanumeric, so
    folding first drops it and filtering first keeps it.

    Args:
        text: An identifier or a label.

    Returns:
        The characters, case-folded and concatenated.

    Example:
        >>> stream_key("TXN_APPLNT_ID")
        'txnapplntid'
        >>> stream_key("Transaction Applicant Identifier") == stream_key("TXN_APPLNT_ID")
        False
        >>> stream_key("txn applnt id") == stream_key("TXN_APPLNT_ID")
        True
    """
    return "".join(character for character in text.casefold() if character.isalnum())


def label_words(label: Optional[str]) -> frozenset[str]:
    """The case-folded whole words of ``label``, as maximal alphanumeric runs.

    The one place this module decides what *the token appears in the label*
    means, so the decision lives in a named function rather than scattered
    through a loop.

    Runs are **Unicode-aware and not accent-folded**, and that is the choice that
    keeps the derivation honest rather than a stylistic one. ``Número`` carries a
    character ``n_mero`` does not, so a catalog-free method genuinely cannot
    produce it; an ASCII-only rule splits the label into ``n`` and ``mero``,
    finds both tokens present, and reports a column as fully attributed that is
    not. ``tools/byoc_eval.py`` uses the ASCII rule for its own scoring and the
    two are scored against each other at ``catalog_gap.socrata.label_word_rule``.
    The leniency is invisible in the output and it is not small.

    Args:
        label: The human wording of the column, or ``None``.

    Returns:
        The distinct case-folded words. Empty for ``None``, for the empty string,
        and for a label holding no alphanumeric character at all.

    Example:
        >>> sorted(label_words("Transaction Identifier"))
        ['identifier', 'transaction']
        >>> sorted(label_words("E-mail (work)"))
        ['e', 'mail', 'work']
        >>> sorted(label_words("Número"))
        ['número']
        >>> label_words(None)
        frozenset()
    """
    if not label:
        return frozenset()
    words: list[str] = []
    current: list[str] = []
    for character in label:
        if character.isalnum():
            current.append(character)
        elif current:
            words.append("".join(current).casefold())
            current = []
    if current:
        words.append("".join(current).casefold())
    return frozenset(words)


# --------------------------------------------------------------------------
# The payload
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class GapToken(_FrozenModel):
    """One token that makes at least one label unreachable, and what it costs.

    A row of the work list. Ranked by :attr:`columns`, so the tuple of these on
    a :class:`CatalogGap` reads top to bottom as the order to write catalog rows
    in -- under the assumption named in the module docstring, and priced by
    :attr:`CatalogGap.ranking_cost_points`.

    This is deliberately **not**
    :class:`~acronymkit.catalog.audit.UnknownToken`. That class ranks what a
    vocabulary does not cover and needs the vocabulary to say so; this one ranks
    what no vocabulary-free method could cover and is computed without one.
    """

    #: The token as the identifier wrote it, case-folded. Lookup everywhere in
    #: this module is case-insensitive, so a schema that writes both ``custmr``
    #: and ``CUSTMR`` contributes to one row here rather than two.
    token: str

    #: How many **distinct** columns this token makes unreachable. The ranking
    #: key, and the number to quote as "how many columns this row would clear".
    columns: int

    #: How many times the token appears anywhere in the schema, counting every
    #: appearance in every column including the reachable ones. Reported beside
    #: :attr:`columns` because the two say different things, and because a token
    #: frequent overall but rarely breaking anything is a different object from
    #: one that breaks every column it touches.
    occurrences: int

    #: Columns the token was seen breaking, in input order, capped by the
    #: report's ``max_examples``. Enough to go and look at, and deliberately not
    #: the full list: on a real schema the full list is most of the schema.
    examples: tuple[str, ...] = ()

    #: The label of the first example, so a reviewer can see what the column was
    #: supposed to say without joining two tables by hand.
    example_label: str = ""

    def __post_init__(self) -> None:
        """Normalise the example list to a tuple.

        Raises:
            GovernedValidationError: If ``examples`` is not a sequence.
        """
        _freeze_sequences(self, "examples")

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.token} in {self.columns} column(s)"


@dataclass(frozen=True)
class CatalogGap(_FrozenModel):
    """What a schema's own labels prove no catalog-free method can reach.

    Every field is a count of a property of two strings, or a work count. There
    is no accuracy figure here and there is not going to be one: this report says
    what is *impossible* without a catalog, which is a stronger and much smaller
    claim than saying what is likely with one.
    """

    #: Rows offered, before anything was rejected. The denominator for the three
    #: rejection counts below, and the only figure here that is a property of the
    #: caller's file rather than of their schema.
    rows_offered: int

    #: Rows with no identifier at all. Rejected, counted, never guessed at.
    rows_without_identifier: int

    #: Rows whose identifier was already seen, case-folded. Rejected on the same
    #: rule ``tools/byoc_eval.py`` applies -- first occurrence wins -- so that the
    #: two tools report the same column count over one CSV.
    rows_duplicated: int

    #: Distinct columns admitted: the schema, as this report understands it.
    columns: int

    #: Columns carrying a human label. The classification below applies to these
    #: and to no others.
    labelled_columns: int

    #: Columns carrying no label. **Not classified and not guessed at**, for the
    #: reason the module docstring gives at length. A report where this is most
    #: of :attr:`columns` has measured very little and says so here.
    unlabelled_columns: int

    #: Labelled columns whose label shares the identifier's character stream.
    #: A catalog-free method could reach these -- where to cut and how to case
    #: are all that remain. This is *reachable*, not *correct*: whether the
    #: shipped splitter actually cuts them right is a different question, and it
    #: is the one ``governed_gold.socrata.*`` measures.
    reachable_columns: int

    #: Labelled columns whose label carries a character the identifier does not.
    #: **No catalog-free method reaches these.** The exact half of the report.
    unreachable_columns: int

    #: Unreachable columns where at least one token is missing from the label, so
    #: the impossibility is attributable to a token and lands on the work list.
    attributed_columns: int

    #: Unreachable columns where every token *is* a label word, so the label says
    #: more than the identifier does and no catalog row would fix it. These carry
    #: no work item. A reader who takes the ranked table for the whole gap is
    #: reading past exactly this number.
    unattributed_columns: int

    #: Columns holding a character the tokenizer could not account for. Reported
    #: because it is a second, independent reason a round trip cannot reproduce
    #: the input, and because ``is_fully_known`` already refuses on it.
    columns_with_unaccounted: int

    #: Distinct tokens across every admitted column, labelled or not.
    distinct_tokens: int

    #: Distinct tokens appearing in at least one labelled column -- the only ones
    #: this report can classify. :attr:`distinct_tokens` minus this is the
    #: unclassifiable remainder, and it is zero when every column has a label.
    classified_tokens: int

    #: Classified tokens that never made a label unreachable. **Read this as "not
    #: proven impossible", never as "resolved"**: it means no column offered a
    #: proof against this token, not that a catalog-free method gets it right.
    reachable_tokens: int

    #: Classified tokens that made at least one label unreachable. The work list,
    #: before the catalog is consulted.
    unreachable_tokens: int

    #: Unreachable tokens the supplied catalog already answers. ``0`` when no
    #: catalog was supplied. :attr:`unreachable_tokens` minus this is what is
    #: actually left to write.
    catalog_covered_tokens: int

    #: Distinct columns made unreachable by at least one token still on the work
    #: list. The denominator of :attr:`head_coverage_pct`.
    work_list_columns: int

    #: The ranked head: the tokens that buy the most columns, longest first.
    head: tuple[GapToken, ...] = ()

    #: Distinct columns the head covers between them -- a union, not a sum, so
    #: two tokens in one column count once.
    head_columns: int = 0

    #: The head's share of :attr:`work_list_columns`, as a percentage. This is
    #: the "the twenty at the top buy this much" figure.
    head_coverage_pct: float = 0.0

    #: How many single-character tokens are in the head. **Read this before
    #: reading the ranking.** A one-character token is not a vocabulary item, and
    #: a head full of them means the concentration is machine-generated
    #: identifier debris rather than an abbreviation the caller could govern.
    head_single_character: int = 0

    #: How many head tokens carry no letter at all -- ordinals and hash
    #: fragments. Same warning as above, on the other axis.
    head_without_letter: int = 0

    #: Distinct columns a greedy set cover of the same budget would have reached.
    #: The control on the ranking, not a recommendation: a greedy cover is not
    #: stable under small changes to the schema and a work list that reorders
    #: every quarter is not a work list.
    greedy_columns: int = 0

    #: The greedy cover's share of :attr:`work_list_columns`, as a percentage.
    greedy_coverage_pct: float = 0.0

    #: :attr:`greedy_coverage_pct` minus :attr:`head_coverage_pct`, in points.
    #: What ranking by column count costs on this schema, against a budget of the
    #: same size. Small means the assumption is cheap here; large means the
    #: caller should be reading a cover rather than a ranking.
    ranking_cost_points: float = 0.0

    #: Minimum token length admitted to the work list; ``1`` admits everything.
    min_token_length: int = 1

    #: Whether a token had to carry a letter to reach the work list.
    require_letter: bool = False

    #: Tokenizer passes performed: one per admitted column, none per occurrence.
    tokenizer_passes: int = 0

    #: Label word-sets built: one per labelled column whose stream differs from
    #: its identifier's, and none for the reachable majority.
    label_word_sets: int = 0

    #: Catalog lookups performed: one per distinct unreachable token, and **zero**
    #: when no catalog was supplied.
    catalog_lookups: int = 0

    #: Token occurrences seen, counting every appearance. Beside
    #: :attr:`distinct_tokens` this is the repetition the per-distinct costs
    #: above are amortised over.
    token_occurrences: int = 0

    #: Set-difference evaluations the greedy control performed. It is the most
    #: expensive thing in this module and the only one that is not linear, so its
    #: cost is reported rather than hidden.
    greedy_set_operations: int = 0

    def __post_init__(self) -> None:
        """Normalise the head to a tuple.

        Raises:
            GovernedValidationError: If ``head`` is not a sequence.
        """
        _freeze_sequences(self, "head")

    @property
    def work_list_tokens(self) -> int:
        """Unreachable tokens the catalog does not already answer."""
        return self.unreachable_tokens - self.catalog_covered_tokens

    @property
    def unattributed_pct(self) -> float:
        """:attr:`unattributed_columns` as a share of :attr:`unreachable_columns`."""
        if not self.unreachable_columns:
            return 0.0
        return round(100.0 * self.unattributed_columns / self.unreachable_columns, 2)

    def __str__(self) -> str:  # pragma: no cover - display helper
        return (
            f"{self.columns} column(s), {self.unreachable_columns} unreachable, "
            f"{self.work_list_tokens} token(s) to write"
        )


# --------------------------------------------------------------------------
# the pass
# --------------------------------------------------------------------------
@dataclass
class _Work:
    """Mutable accumulator for one token, kept only while the pass runs."""

    columns: set[str] = field(default_factory=set)
    examples: list[str] = field(default_factory=list)
    example_label: str = ""


def _admissible(token: str, min_length: int, require_letter: bool) -> bool:
    """Whether ``token`` may reach the work list under the two filters.

    Both filters are mechanical properties of the string, which is the only kind
    this module is willing to apply: "is this token a real abbreviation" is a
    judgement and the label-free classifier that tried to make it is the arm the
    module docstring records as rejected.

    Args:
        token: The surface token.
        min_length: Shortest admissible length; ``1`` admits everything.
        require_letter: Whether the token must carry at least one letter.

    Returns:
        ``True`` if the token may be ranked.
    """
    if len(token) < min_length:
        return False
    return not require_letter or any(character.isalpha() for character in token)


def _greedy_cover(work: Mapping[str, set[str]], budget: int) -> tuple[int, int]:
    """Greedily cover as many columns as ``budget`` tokens can, and count the cost.

    The control on the frequency ranking. Deliberately recomputed from the same
    sets the ranking used rather than approximated, because the whole point of
    the comparison is that it is the same population.

    Args:
        work: Token -> the columns it makes unreachable.
        budget: How many tokens the cover may choose.

    Returns:
        ``(columns covered, set-difference evaluations performed)``.
    """
    remaining = dict(work)
    covered: set[str] = set()
    operations = 0
    for _ in range(max(budget, 0)):
        best: Optional[str] = None
        best_gain = 0
        # Sorted, and the comparison is strict, so a tie keeps the
        # lexicographically first token and two runs over one schema choose the
        # same cover. A dictionary's insertion order would make this control's
        # verdict depend on the order the caller's CSV happened to arrive in.
        for token in sorted(remaining):
            operations += 1
            gain = len(remaining[token] - covered)
            if gain > best_gain:
                best_gain = gain
                best = token
        if best is None:
            break
        covered |= remaining.pop(best)
    return len(covered), operations


def _require(dictionary: Optional[GovernedDictionary]) -> None:
    """Refuse a dictionary of the wrong type, and accept ``None``.

    ``None`` is the supported way to say *I have no catalog yet*, which is the
    case this whole module exists for -- unlike
    :func:`~acronymkit.catalog.expansion.expand_identifier`, where a governed
    verb with no vocabulary is a contradiction and ``None`` is refused.

    Args:
        dictionary: The catalog, or ``None``.

    Raises:
        ConfigurationError: If it is neither.
    """
    if dictionary is None or isinstance(dictionary, GovernedDictionary):
        return
    raise ConfigurationError(
        "catalog_gap(dictionary=...) takes a GovernedDictionary or None "
        f"(None means 'no catalog', which is the case this report is for); got "
        f"{type(dictionary).__name__}"
    )


def catalog_gap(
    rows: Iterable[tuple[str, str]],
    dictionary: Optional[GovernedDictionary] = None,
    policy: Optional[NamingPolicy] = None,
    *,
    custom: Optional[Mapping[str, Union[str, GovernedEntry]]] = None,
    head: int = 20,
    min_token_length: int = 1,
    require_letter: bool = False,
    max_examples: int = 3,
) -> CatalogGap:
    """Report which of a schema's tokens no catalog-free method can ever reach.

    One streaming pass over ``(identifier, label)`` rows. Identifiers are
    de-duplicated case-insensitively with the first occurrence winning, which is
    the rule ``tools/byoc_eval.py`` applies, so one CSV run through both tools
    reports one column count.

    Args:
        rows: ``(identifier, label)`` pairs. A row whose label is empty is
            admitted, counted as unlabelled and **not classified**; a row whose
            identifier is empty is rejected and counted.
        dictionary: The caller's catalog, or ``None`` for the case this report is
            built for. Supplying one adds exactly one thing: unreachable tokens
            the catalog already answers are marked and kept off the work list.
        policy: The naming policy for those lookups. Ignored when no catalog is
            supplied, because no lookup happens.
        custom: A per-call overlay, passed straight through to
            :func:`~acronymkit.catalog.expansion.expand_token`.
        head: How many ranked rows to return, and the budget the greedy control
            is given. ``0`` returns no rows and still returns every count.
        min_token_length: Shortest token admitted to the work list.
        require_letter: Whether a token must carry a letter to be ranked. Both
            filters are off by default: a report that silently dropped part of
            its input would be the failure this subsystem exists to refuse.
        max_examples: Example columns retained per ranked token.

    Returns:
        The report.

    Raises:
        ConfigurationError: If ``dictionary`` is neither a
            :class:`~acronymkit.catalog.dictionary.GovernedDictionary` nor
            ``None``, or if ``head``, ``min_token_length`` or ``max_examples`` is
            negative.

    Example:
        >>> gap = catalog_gap(
        ...     [
        ...         ("TXN_APPLNT_ID", "Transaction Applicant Identifier"),
        ...         ("CUSTOMER_NAME", "Customer Name"),
        ...     ]
        ... )
        >>> gap.columns, gap.reachable_columns, gap.unreachable_columns
        (2, 1, 1)
        >>> [(row.token, row.columns) for row in gap.head]
        [('applnt', 1), ('id', 1), ('txn', 1)]
        >>> gap.catalog_lookups
        0
    """
    _require(dictionary)
    if head < 0 or min_token_length < 0 or max_examples < 0:
        raise ConfigurationError(
            "catalog_gap() takes non-negative head, min_token_length and max_examples; got "
            f"head={head}, min_token_length={min_token_length}, max_examples={max_examples}"
        )

    seen: set[str] = set()
    work: dict[str, _Work] = {}
    occurrences: dict[str, int] = {}
    classified: set[str] = set()
    rows_offered = rows_without_identifier = rows_duplicated = 0
    labelled = unlabelled = reachable = unreachable = 0
    attributed = unattributed = unaccounted_columns = 0
    tokenizer_passes = label_word_sets = token_occurrences = 0

    for row in rows:
        rows_offered += 1
        identifier, label = row[0], row[1]
        identifier = (identifier or "").strip()
        label = (label or "").strip()
        if not identifier:
            rows_without_identifier += 1
            continue
        key = identifier.casefold()
        if key in seen:
            rows_duplicated += 1
            continue
        seen.add(key)

        parts = split_identifier_parts(identifier)
        tokenizer_passes += 1
        if parts.unaccounted:
            unaccounted_columns += 1
        folded = [token.casefold() for token in parts.tokens]
        for token in folded:
            occurrences[token] = occurrences.get(token, 0) + 1
            token_occurrences += 1

        if not label:
            unlabelled += 1
            continue
        labelled += 1
        classified.update(folded)
        if stream_key(identifier) == stream_key(label):
            reachable += 1
            continue

        unreachable += 1
        words = label_words(label)
        label_word_sets += 1
        missing = [
            token
            for token in folded
            if token not in words and _admissible(token, min_token_length, require_letter)
        ]
        if not missing:
            unattributed += 1
            continue
        attributed += 1
        for token in missing:
            item = work.get(token)
            if item is None:
                item = work[token] = _Work(example_label=label)
            item.columns.add(key)
            if len(item.examples) < max_examples:
                item.examples.append(identifier)

    covered: set[str] = set()
    catalog_lookups = 0
    if dictionary is not None:
        for token in work:
            catalog_lookups += 1
            if expand_token(token, dictionary, policy, custom=custom).is_known:
                covered.add(token)

    live = {token: item.columns for token, item in work.items() if token not in covered}
    work_list_columns = len(set().union(*live.values())) if live else 0
    ranked = sorted(live, key=lambda token: (-len(live[token]), token))[:head]
    head_columns = len(set().union(*(live[token] for token in ranked))) if ranked else 0
    greedy_columns, greedy_operations = _greedy_cover(live, head)

    rows_out = tuple(
        GapToken(
            token=token,
            columns=len(work[token].columns),
            occurrences=occurrences.get(token, 0),
            examples=tuple(work[token].examples),
            example_label=work[token].example_label,
        )
        for token in ranked
    )
    return CatalogGap(
        rows_offered=rows_offered,
        rows_without_identifier=rows_without_identifier,
        rows_duplicated=rows_duplicated,
        columns=len(seen),
        labelled_columns=labelled,
        unlabelled_columns=unlabelled,
        reachable_columns=reachable,
        unreachable_columns=unreachable,
        attributed_columns=attributed,
        unattributed_columns=unattributed,
        columns_with_unaccounted=unaccounted_columns,
        distinct_tokens=len(occurrences),
        classified_tokens=len(classified),
        reachable_tokens=len(classified) - len(work),
        unreachable_tokens=len(work),
        catalog_covered_tokens=len(covered),
        work_list_columns=work_list_columns,
        head=rows_out,
        head_columns=head_columns,
        head_coverage_pct=_pct(head_columns, work_list_columns),
        head_single_character=sum(1 for token in ranked if len(token) == 1),
        head_without_letter=sum(
            1 for token in ranked if not any(character.isalpha() for character in token)
        ),
        greedy_columns=greedy_columns,
        greedy_coverage_pct=_pct(greedy_columns, work_list_columns),
        ranking_cost_points=round(
            _pct(greedy_columns, work_list_columns) - _pct(head_columns, work_list_columns), 2
        ),
        min_token_length=min_token_length,
        require_letter=require_letter,
        tokenizer_passes=tokenizer_passes,
        label_word_sets=label_word_sets,
        catalog_lookups=catalog_lookups,
        token_occurrences=token_occurrences,
        greedy_set_operations=greedy_operations,
    )


def _pct(part: int, whole: int) -> float:
    """``part`` as a percentage of ``whole``, or ``0.0`` when ``whole`` is zero."""
    return round(100.0 * part / whole, 2) if whole else 0.0


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
#: How wide an example column may be before it is clipped. Physical names in a
#: real schema run long and one of them is not worth wrapping a table around.
_EXAMPLE_WIDTH = 44


def _clip(text: str, width: int) -> str:
    """Shorten ``text`` to ``width`` characters with a trailing ellipsis."""
    return text if len(text) <= width else text[: max(width - 1, 0)] + "…"


def _pairs(rows: tuple[tuple[str, str], ...]) -> list[str]:
    """Render label/value pairs with the labels right-padded to one width."""
    width = max((len(label) for label, _value in rows), default=0)
    return [f"  {label.ljust(width)}  {value}" for label, value in rows]


def _table(headers: tuple[str, ...], body: list[list[str]], right: tuple[int, ...]) -> list[str]:
    """Render a fixed-width table, right-aligning the named column indices."""
    widths = [len(header) for header in headers]
    for line in body:
        for index, cell in enumerate(line):
            widths[index] = max(widths[index], len(cell))

    def render(cells: list[str]) -> str:
        parts = [
            cell.rjust(widths[index]) if index in right else cell.ljust(widths[index])
            for index, cell in enumerate(cells)
        ]
        return "  " + "  ".join(parts).rstrip()

    lines = [render(list(headers)), "  " + "  ".join("-" * width for width in widths)]
    lines.extend(render(line) for line in body)
    return lines


def render_gap(gap: CatalogGap, *, limit: Optional[int] = 20) -> str:
    """Render a :class:`CatalogGap` for a person to read.

    Args:
        gap: The report.
        limit: Rows of the ranked table to show; ``None`` shows every row the
            report holds.

    Returns:
        The report as text, without a trailing newline.
    """
    rows = gap.head if limit is None else gap.head[:limit]
    lines = ["catalog gap -- what no catalog-free method can reach", ""]
    lines.extend(
        _pairs(
            (
                ("columns", f"{gap.columns:,} ({gap.labelled_columns:,} labelled)"),
                (
                    "reachable",
                    f"{gap.reachable_columns:,} "
                    f"({_pct(gap.reachable_columns, gap.labelled_columns)} % of labelled)",
                ),
                (
                    "UNREACHABLE",
                    f"{gap.unreachable_columns:,} "
                    f"({_pct(gap.unreachable_columns, gap.labelled_columns)} % of labelled)",
                ),
                (
                    "  attributed",
                    f"{gap.attributed_columns:,} -- a token to write is named below",
                ),
                (
                    "  unattributed",
                    f"{gap.unattributed_columns:,} ({gap.unattributed_pct} % of unreachable) "
                    "-- the label says more than the identifier; no catalog row fixes these",
                ),
                ("distinct tokens", f"{gap.distinct_tokens:,}"),
                (
                    "  never break a label",
                    f"{gap.reachable_tokens:,} -- not proven impossible, which is weaker "
                    "than resolved",
                ),
                ("  break at least one", f"{gap.unreachable_tokens:,}"),
                (
                    "  already in catalog",
                    f"{gap.catalog_covered_tokens:,}"
                    + ("" if gap.catalog_lookups else " (no catalog supplied)"),
                ),
                ("  LEFT TO WRITE", f"{gap.work_list_tokens:,}"),
            )
        )
    )
    if gap.unlabelled_columns:
        lines.append(
            f"  {gap.unlabelled_columns:,} column(s) carry no label and are NOT classified. "
            "Nothing here is guessed from an identifier alone."
        )
    lines.extend(["", f"the work list, ranked by columns cleared (top {len(rows)})", ""])
    if not rows:
        lines.append("  nothing to write: no label in this schema is unreachable")
    else:
        body = [
            [
                row.token,
                f"{row.columns:,}",
                f"{row.occurrences:,}",
                _clip(row.examples[0] if row.examples else "", _EXAMPLE_WIDTH),
                _clip(row.example_label, _EXAMPLE_WIDTH),
            ]
            for row in rows
        ]
        lines.extend(_table(("token", "columns", "seen", "example", "its label"), body, (1, 2)))
        lines.extend(
            [
                "",
                f"  these {len(rows)} cover {gap.head_columns:,} of {gap.work_list_columns:,} "
                f"unreachable columns ({gap.head_coverage_pct} %)",
                f"  a greedy cover of the same size reaches {gap.greedy_coverage_pct} %, so "
                f"ranking by column count costs {gap.ranking_cost_points} point(s) here",
            ]
        )
        if gap.head_single_character or gap.head_without_letter:
            lines.append(
                f"  READ THIS FIRST: {gap.head_single_character} of the {len(rows)} rows above "
                f"are single characters and {gap.head_without_letter} carry no letter at all. "
                "Those are not vocabulary items; they are fragments of machine-generated "
                "names, and no catalog row would fix them. Re-run with "
                "min_token_length=2, require_letter=True to see the head without them."
            )
    return "\n".join(lines)
