"""Does deferring provenance buy anything? Two censuses that answer it in counts.

Mandate III ranked *lazy provenance* first: carry compact integer spans through
the intermediate passes and materialise the public record only when a caller
reads ``.provenance``. D-086 measured the premise underneath it by walking this
repository's syntax tree and found ``0`` of ``3`` in-library ``expand_identifier``
call sites phrase-only. D-100 then took the other half of the bet -- the record
was made cheaper rather than deferred -- and named the floor it stopped at:
allocating the object and filling its ``__dict__``.

This runner asks the two questions those records leave open, and it asks both in
**machine-independent counts** rather than in nanoseconds (R18, and D-013 is the
record of this project making that mistake once).

**The read census.** D-086 counted call *sites*. This counts *executions*: it
installs a spy on :class:`~acronymkit.catalog.models.IdentifierExpansion` and
records, per record, which attribute names were actually read, over five consumer
shapes that all exist in this repository. A site is a place a read could happen;
an execution is one that did.

**The deferral census.** It then builds the design the brief describes -- a flat
tuple of ``(start, end, answer_slot, flags)`` integers per identifier, a compact
answer tuple per distinct token, and a deferred record that materialises
:class:`~acronymkit.catalog.models.TokenExpansion` objects only when ``.tokens``
is read -- and counts every object each route allocates on each of those five
shapes. Byte-identity of the materialised records against the shipped ones is
checked over every field of every record, with a control probe that must fire.

WHAT THIS RUNNER IS NOT
-----------------------
It is **not** a re-implementation of ``expand_identifier``. Every token is
resolved by the shipped :func:`acronymkit.catalog.expansion._expand`, split by the
shipped tokenizer, rejoined by the shipped digit pass and remembered through the
shipped :func:`acronymkit.catalog.dictionary._remember` with the shipped bound.
What differs between the two routes is what the intermediate pass *carries* and
when the record is *built* -- which is the whole of the question. A driver that
re-walked the expansion path would be measuring a copy and calling the difference
a finding, which is the objection ``bench/run_governed_perf.py`` already records
against exactly that shortcut.

It also does not touch ``src/acronymkit``. The deferred route lives here, in the
bench tree, because it was measured and rejected; committing the instrument is
what lets a later round re-derive the rejection instead of re-litigating it.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from acronymkit.catalog import GovernedDictionary  # noqa: E402
from acronymkit.catalog import audit as audit_module  # noqa: E402
from acronymkit.catalog import dictionary as dictionary_module  # noqa: E402
from acronymkit.catalog import expansion as expansion_module  # noqa: E402
from acronymkit.catalog.models import (  # noqa: E402
    IdentifierExpansion,
    TokenExpansion,
    _new_identifier_expansion,
    _new_token_expansion,
)
from acronymkit.catalog.policy import NamingPolicy  # noqa: E402
from bench.run_governed_perf import (  # noqa: E402
    FIXTURE_SCHEMA_IDENTIFIERS,
    build_fixture_dictionary,
    environment,
    fixture_schema_corpus,
    machine_note,
    read_snapshot,
)

#: Attribute names whose read a deferred design would have to service by
#: materialising the token records. ``__dict__`` is in the set because
#: ``to_dict``, ``to_json`` and ``model_dump`` all read the instance dict
#: directly rather than going through attribute access, so a spy on
#: ``__getattribute__`` sees the dict read and never sees ``tokens``.
FORCING_READS = frozenset(
    {"tokens", "unknown_tokens", "__dict__", "__repr__", "__eq__", "__str__", "__hash__"}
)

#: The five consumer shapes, each of which exists in this repository. The label
#: is the run-id suffix; the note is what reads that way and is printed beside
#: the figure so a reader is not asked to take the population on trust.
ARM_NOTES = {
    "phrase_only": "bench/run_governed_gold.py -- the shape every published governed figure is "
    "taken with",
    "gate_only": "a pipeline gating on is_fully_known and nothing else; no site in this "
    "repository does this, and it is the most favourable shape the bet has",
    "audit": "acronymkit.catalog.audit._observe -- the library's own consumer",
    "to_json": "bench/run_catalog_gap.py and tools/gate_memo_identity.py -- the wire shape",
    "to_dict": "acronymkit expand --format json -- the CLI shape",
}

#: Consumer shapes, in report order.
ARM_ORDER = ("phrase_only", "gate_only", "audit", "to_json", "to_dict")

#: The deferral census runs one arm the read census cannot: the STRONGEST
#: form of the bet, in which materialised records are shared across every
#: occurrence of a token the way the shipped token memo shares them. Without
#: it the comparison would be against a deferred design nobody would build,
#: and the objection would be right.
DEFERRAL_ARMS = (*ARM_ORDER, "to_json_shared")

#: Identifiers in the fixture arm, taken from the perf runner so the two agree.
FIXTURE_IDENTIFIERS = FIXTURE_SCHEMA_IDENTIFIERS


# ---------------------------------------------------------------------------
# the read census
# ---------------------------------------------------------------------------


class _ReadLedger:
    """Which attribute names were read, per :class:`IdentifierExpansion`."""

    def __init__(self) -> None:
        """Start empty."""
        #: Strong references to every record built while the ledger was live, so
        #: that ``id()`` cannot be reused underneath the mask table.
        self.records: List[IdentifierExpansion] = []
        #: ``id(record) -> the attribute names read on it``.
        self.masks: Dict[int, Set[str]] = {}

    def tally(self) -> Dict[str, Any]:
        """Reduce the masks to the counts this runner saves.

        Returns:
            Record and per-field counts, plus the forcing share.
        """
        masks = list(self.masks.values())
        total = len(masks)
        forcing = sum(1 for mask in masks if mask & FORCING_READS)
        return {
            "records": total,
            "forcing": forcing,
            "forcing_pct": round(100.0 * forcing / total, 4) if total else 0.0,
            "never_read": sum(1 for mask in masks if not mask),
            "read_tokens": sum(1 for mask in masks if "tokens" in mask),
            "read_dict": sum(1 for mask in masks if "__dict__" in mask),
            "read_phrase": sum(1 for mask in masks if "phrase" in mask),
            "read_is_fully_known": sum(1 for mask in masks if "is_fully_known" in mask),
            "read_class_word": sum(1 for mask in masks if "class_word" in mask),
            "read_unaccounted": sum(1 for mask in masks if "unaccounted" in mask),
        }


@contextlib.contextmanager
def read_ledger() -> Iterator[_ReadLedger]:
    """Spy on every attribute read of every identifier record built inside.

    The spy is installed on the class rather than on an instance, and the
    construction hook is installed on
    :mod:`acronymkit.catalog.expansion`'s module global rather than on
    :mod:`acronymkit.catalog.models`, because that is the name the hot path
    resolves. A record served from the identifier memo is **not** re-registered:
    it was counted when it was built, and its reads accumulate across every call
    that is served it, which is the population the question is about.

    Yields:
        The ledger, live for the duration.

    Raises:
        RuntimeError: If the class carried its own ``__getattribute__`` before
            the spy went in. Restoring by deletion would then remove somebody
            else's override, and silently leaving the spy behind would make every
            later measurement in the process wrong.
    """
    if "__getattribute__" in vars(IdentifierExpansion):
        raise RuntimeError("IdentifierExpansion already defines __getattribute__; refusing to spy")
    ledger = _ReadLedger()
    base = IdentifierExpansion.__getattribute__
    real_new = expansion_module._new_identifier_expansion
    masks = ledger.masks

    def spy(self: IdentifierExpansion, name: str) -> Any:
        mask = masks.get(id(self))
        if mask is not None:
            mask.add(name)
        return base(self, name)

    def counted(*args: Any) -> IdentifierExpansion:
        record = real_new(*args)
        ledger.records.append(record)
        masks[id(record)] = set()
        return record

    IdentifierExpansion.__getattribute__ = spy  # type: ignore[method-assign, assignment]
    expansion_module._new_identifier_expansion = counted  # type: ignore[assignment]
    try:
        yield ledger
    finally:
        del IdentifierExpansion.__getattribute__
        expansion_module._new_identifier_expansion = real_new


def _arm_phrase(records: Sequence[IdentifierExpansion]) -> int:
    """Read ``.phrase`` and nothing else.

    Args:
        records: The results of one corpus pass.

    Returns:
        How many phrases were non-empty. The return value is not the
        measurement; it exists so that the read is a use rather than a
        statement a linter is entitled to call dead.
    """
    return sum(1 for record in records if record.phrase)


def _arm_gate(records: Sequence[IdentifierExpansion]) -> int:
    """Read ``.is_fully_known`` and nothing else.

    Args:
        records: The results of one corpus pass.

    Returns:
        How many identifiers were fully known.
    """
    return sum(1 for record in records if record.is_fully_known)


def _arm_to_json(records: Sequence[IdentifierExpansion]) -> int:
    """Render each record to JSON, the way the wire consumers do.

    Args:
        records: The results of one corpus pass.

    Returns:
        How many renderings were non-empty.
    """
    return sum(1 for record in records if record.to_json())


def _arm_to_dict(records: Sequence[IdentifierExpansion]) -> int:
    """Render each record to a dict, the way ``acronymkit expand`` does.

    Args:
        records: The results of one corpus pass.

    Returns:
        How many renderings were non-empty.
    """
    return sum(1 for record in records if record.to_dict())


#: Arms that consume an already-computed record. The ``audit`` arm is not here
#: because it is a whole consumer rather than a field read; it gets its own path.
RECORD_ARMS: Dict[str, Callable[[Sequence[IdentifierExpansion]], int]] = {
    "phrase_only": _arm_phrase,
    "gate_only": _arm_gate,
    "to_json": _arm_to_json,
    "to_dict": _arm_to_dict,
}


def read_census(
    identifiers: Sequence[str],
    catalog_factory: Callable[[], GovernedDictionary],
) -> Dict[str, Any]:
    """Count, per consumer shape, which record fields are read at run time.

    Args:
        identifiers: The corpus, in cache order.
        catalog_factory: Builds a fresh vocabulary per arm, so no arm inherits
            another's memo.

    Returns:
        One sub-entry per arm plus the corpus size.
    """
    figures: Dict[str, Any] = {"identifiers": len(identifiers)}
    for arm in ARM_ORDER:
        catalog = catalog_factory()
        policy = NamingPolicy.governed_default()
        with read_ledger() as ledger:
            if arm == "audit":
                trip = audit_module._trip_policy(policy)
                refusals = 0
                for name in identifiers:
                    try:
                        audit_module._observe(name, catalog, policy, trip)
                    except Exception:  # counted below, not swallowed silently
                        refusals += 1
                figures["audit_refusals"] = refusals
                figures["audit_refusal_pct"] = round(
                    100.0 * refusals / len(identifiers), 4 if identifiers else 0
                )
            else:
                records = [
                    expansion_module.expand_identifier(name, catalog, policy)
                    for name in identifiers
                ]
                RECORD_ARMS[arm](records)
            tally = ledger.tally()
        figures[arm] = tally
    return figures


# ---------------------------------------------------------------------------
# the deferred route: integer spans in, records out only when somebody looks
# ---------------------------------------------------------------------------

#: How many integers one token contributes to the flat intermediate array:
#: ``start``, ``end``, ``answer_slot``, ``flags``.
IR_STRIDE = 4

#: The one bit ``flags`` carries today. It is redundant with the answer tuple and
#: it is here because the brief's shape says ``flags``: carrying it is what makes
#: the "compact integers are free" premise measurable rather than assumed.
FLAG_IS_KNOWN = 1

#: CPython caches small integers; above this an ``int`` in the array is a heap
#: object like any other. Counted rather than waved at.
SMALL_INT_CEILING = 256

#: The keys of the deferred ledger that are object allocations. Memo hits are
#: not allocations, the integers in the array are counted separately because
#: CPython caches the small ones, and a tokenizer pass is work rather than an
#: object. ``lazy_slices`` IS here: the tokenizer already built that string once
#: and the deferred route throws it away and rebuilds it at materialisation.
LAZY_ALLOCATION_KEYS = (
    "lazy_answer_tuples",
    "lazy_ir_tuples",
    "lazy_deferred_records",
    "lazy_materialised_token_records",
    "lazy_materialised_tuples",
    "lazy_materialised_identifier_records",
    "lazy_slices",
    "lazy_synthesised_tables",
)

#: Ledger keys that are counts of work rather than allocations. Kept apart
#: from :data:`LAZY_ALLOCATION_KEYS` so that adding a diagnostic count can
#: never quietly move the total the comparison is made on.
LAZY_DIAGNOSTIC_KEYS = (
    "lazy_identifier_memo_hits",
    "lazy_ir_integers",
    "lazy_ir_large_integers",
    "lazy_materialisation_shared_hits",
    "lazy_records_read",
    "lazy_token_memo_hits",
    "lazy_tokenizer_passes",
    "lazy_tokens_not_a_slice",
)


class _Deferred:
    """An identifier expanded into integer spans, with the records not yet built.

    Everything a caller can read without touching provenance -- ``phrase``,
    ``is_fully_known``, ``class_word``, ``unaccounted`` -- is computed eagerly,
    because each is a function of *every* token's resolution and there is no
    design in which they are not. What is deferred is the construction of the
    :class:`TokenExpansion` objects, which is the only part of the record a lazy
    design can actually postpone.
    """

    __slots__ = (
        "_answers",
        "_counts",
        "_shared",
        "_spans",
        "_synthesised",
        "_tokens",
        "class_word",
        "identifier",
        "is_fully_known",
        "phrase",
        "unaccounted",
    )

    def __init__(
        self,
        identifier: str,
        phrase: str,
        class_word: Optional[str],
        is_fully_known: bool,
        unaccounted: Tuple[str, ...],
        spans: Tuple[int, ...],
        answers: List[Tuple[Any, ...]],
        synthesised: List[str],
        shared: Optional[Dict[Tuple[int, str], TokenExpansion]],
        counts: Dict[str, int],
    ) -> None:
        """Hold the eager fields and the integer array the rest is built from.

        Args:
            identifier: The identifier exactly as supplied.
            phrase: The long forms joined.
            class_word: Read from the trailing token, or ``None``.
            is_fully_known: Every token known and nothing unaccounted for.
            unaccounted: The unaccounted characters.
            spans: ``(start, end, answer_slot, flags)`` per token, flattened.
                A ``start`` below zero encodes ``-1 - index`` into
                ``synthesised``, for a token that is not a substring of the
                identifier at all.
            answers: The per-distinct-token compact answers this call's spans
                index into. Shared with every other call in the pass.
            synthesised: Token texts no pair of offsets can address. See
                :func:`expand_deferred` for the rule that puts one here.
            shared: A materialisation cache keyed by ``(answer_slot, raw)``,
                or ``None`` for the plain deferred route. Supplying one is
                what makes the deferred route share provenance records
                between occurrences the way the shipped token memo does.
            counts: The pass's work-count ledger.
        """
        self.identifier = identifier
        self.phrase = phrase
        self.class_word = class_word
        self.is_fully_known = is_fully_known
        self.unaccounted = unaccounted
        self._spans = spans
        self._answers = answers
        self._synthesised = synthesised
        self._shared = shared
        self._counts = counts
        self._tokens: Optional[Tuple[TokenExpansion, ...]] = None

    @property
    def tokens(self) -> Tuple[TokenExpansion, ...]:
        """Materialise the provenance records, once, on first read.

        Returns:
            One :class:`TokenExpansion` per token, in identifier order.
        """
        built = self._tokens
        if built is not None:
            return built
        spans = self._spans
        answers = self._answers
        text = self.identifier
        counts = self._counts
        records = []
        for offset in range(0, len(spans), IR_STRIDE):
            start = spans[offset]
            answer = answers[spans[offset + 2]]
            slot = spans[offset + 2]
            if start < 0:
                raw = self._synthesised[-1 - start]
            else:
                counts["lazy_slices"] += 1
                raw = text[start : spans[offset + 1]]
            shared = self._shared
            if shared is not None:
                cached = shared.get((slot, raw))
                if cached is not None:
                    counts["lazy_materialisation_shared_hits"] += 1
                    records.append(cached)
                    continue
            counts["lazy_materialised_token_records"] += 1
            fresh = _materialise(raw, answer)
            if shared is not None:
                shared[(slot, raw)] = fresh
            records.append(fresh)
        counts["lazy_materialised_tuples"] += 1
        built = tuple(records)
        self._tokens = built
        return built

    def as_record(self) -> IdentifierExpansion:
        """Build the public record this stands in for, provenance included.

        Returns:
            The :class:`IdentifierExpansion` a non-deferred call would have
            returned.
        """
        self._counts["lazy_materialised_identifier_records"] += 1
        return _new_identifier_expansion(
            self.identifier,
            self.phrase,
            self.tokens,
            self.class_word,
            self.is_fully_known,
            self.unaccounted,
        )


def _compact(record: TokenExpansion) -> Tuple[Any, ...]:
    """Reduce a resolved token record to the tuple the deferred route carries.

    Args:
        record: What the shipped resolver returned.

    Returns:
        The eight field values, in the order
        :func:`~acronymkit.catalog.models._new_token_expansion` takes them after
        ``raw`` -- which is the field the integer span reconstructs.
    """
    return (
        record.long,
        record.is_known,
        record.source,
        record.entry_id,
        record.confidence,
        record.class_word,
        record.beat,
        record.kind,
    )


def _materialise(raw: str, answer: Tuple[Any, ...]) -> TokenExpansion:
    """Build one provenance record from a span slice and a compact answer.

    Args:
        raw: ``identifier[start:end]``.
        answer: What :func:`_compact` produced.

    Returns:
        The record, through the shipped builder, so the two routes cannot differ
        by construction machinery.
    """
    return _new_token_expansion(
        raw,
        answer[0],
        answer[1],
        answer[2],
        answer[3],
        answer[4],
        answer[5],
        answer[6],
        answer[7],
    )


def expand_deferred(
    identifier: str,
    catalog: GovernedDictionary,
    policy: NamingPolicy,
    answers: List[Tuple[Any, ...]],
    slots: Dict[str, int],
    memo: Dict[str, _Deferred],
    counts: Dict[str, int],
    shared: Optional[Dict[Tuple[int, str], TokenExpansion]] = None,
) -> _Deferred:
    """The deferred route: integer spans through, records only on demand.

    Args:
        identifier: The identifier to expand.
        catalog: The vocabulary.
        policy: The resolved policy.
        answers: The pass's compact answer table.
        slots: Token text to its index in ``answers``; the deferred route's
            token memo, bounded and cleared exactly as the shipped one is.
        memo: The deferred route's identifier memo, bounded the same way.
        counts: The pass's work-count ledger.
        shared: The materialisation cache, or ``None``. See
            :class:`_Deferred`.

    Returns:
        The deferred expansion.
    """
    remembered = memo.get(identifier)
    if remembered is not None:
        counts["lazy_identifier_memo_hits"] += 1
        return remembered
    parts = expansion_module.split_identifier_parts(identifier)
    counts["lazy_tokenizer_passes"] += 1
    tokens = expansion_module._rejoin_digit_tokens(parts.tokens, catalog, policy)

    spans: List[int] = []
    synthesised: List[str] = []
    cursor = 0
    known = True
    longs: List[str] = []
    last_class_word: Optional[str] = None
    for token in tokens:
        start = identifier.find(token, cursor)
        if start < 0:
            # THE ZERO-COPY PREMISE FAILING, COUNTED RATHER THAN ASSUMED AWAY.
            # `_rejoin_digit_tokens` puts `1_MM` back together as the token
            # `1MM`, which is not a substring of the identifier -- the separator
            # is still sitting between the two halves. `raw` is a SYNTHESISED
            # string for such a token, no pair of offsets can address it, and
            # the deferred route has to carry the text after all. Zero on an
            # empty catalog, because the rejoin fires only where a catalog
            # vouches for the joined token -- which is every published
            # governed arm, and is why a span IR would have passed R19 here
            # and broken on the first real catalog.
            counts["lazy_tokens_not_a_slice"] += 1
            synthesised.append(token)
            start, end = -len(synthesised), 0
        else:
            end = start + len(token)
            cursor = end
        slot = slots.get(token)
        if slot is None:
            record = expansion_module._expand(token, catalog, policy)
            answers.append(_compact(record))
            counts["lazy_answer_tuples"] += 1
            slot = len(answers) - 1
            if len(slots) >= dictionary_module._MEMO_LIMIT:
                slots.clear()
            slots[token] = slot
        else:
            counts["lazy_token_memo_hits"] += 1
        answer = answers[slot]
        spans.append(start)
        spans.append(end)
        spans.append(slot)
        spans.append(FLAG_IS_KNOWN if answer[1] else 0)
        if answer[0]:
            longs.append(answer[0])
        known = known and bool(answer[1])
        last_class_word = answer[5]

    counts["lazy_ir_tuples"] += 1
    if synthesised:
        counts["lazy_synthesised_tables"] += 1
    counts["lazy_ir_integers"] += len(spans)
    counts["lazy_ir_large_integers"] += sum(1 for value in spans if value > SMALL_INT_CEILING)
    counts["lazy_deferred_records"] += 1
    deferred = _Deferred(
        identifier,
        " ".join(longs),
        last_class_word if tokens else None,
        not parts.unaccounted and known,
        parts.unaccounted,
        tuple(spans),
        answers,
        synthesised,
        shared,
        counts,
    )
    if len(memo) >= dictionary_module._IDENTIFIER_MEMO_LIMIT:
        memo.clear()
    memo[identifier] = deferred
    return deferred


def _new_counts() -> Dict[str, int]:
    """A zeroed ledger, so every key exists whether or not the pass hit it.

    Returns:
        The ledger.
    """
    return {
        "lazy_answer_tuples": 0,
        "lazy_deferred_records": 0,
        "lazy_identifier_memo_hits": 0,
        "lazy_ir_integers": 0,
        "lazy_ir_large_integers": 0,
        "lazy_ir_tuples": 0,
        "lazy_materialised_identifier_records": 0,
        "lazy_materialised_token_records": 0,
        "lazy_materialisation_shared_hits": 0,
        "lazy_materialised_tuples": 0,
        "lazy_records_read": 0,
        "lazy_slices": 0,
        "lazy_synthesised_tables": 0,
        "lazy_tokens_not_a_slice": 0,
        "lazy_token_memo_hits": 0,
        "lazy_tokenizer_passes": 0,
    }


@contextlib.contextmanager
def eager_counts() -> Iterator[Dict[str, int]]:
    """Count what the shipped route allocates, without changing what it does.

    Yields:
        The ledger, filled as the shipped builders are called.
    """
    counts = {
        "eager_identifier_records": 0,
        "eager_token_records": 0,
        "eager_token_tuples": 0,
    }
    real_identifier = expansion_module._new_identifier_expansion
    real_token = expansion_module._new_token_expansion

    def counted_identifier(*args: Any) -> IdentifierExpansion:
        counts["eager_identifier_records"] += 1
        # The shipped path hands the builder a tuple it has just built by
        # comprehension; one per constructed record, counted here because there
        # is no other site that sees it.
        counts["eager_token_tuples"] += 1
        return real_identifier(*args)

    def counted_token(*args: Any) -> TokenExpansion:
        counts["eager_token_records"] += 1
        return real_token(*args)

    expansion_module._new_identifier_expansion = counted_identifier  # type: ignore[assignment]
    expansion_module._new_token_expansion = counted_token  # type: ignore[assignment]
    try:
        yield counts
    finally:
        expansion_module._new_identifier_expansion = real_identifier
        expansion_module._new_token_expansion = real_token


@contextlib.contextmanager
def shipped_memos_off() -> Iterator[None]:
    """Silence the shipped memos so the deferred route's own can stand in.

    The deferred route memoises compact answers where the shipped route
    memoises records, with the same key, the same bound and the same
    clear-when-full rule. Leaving the shipped memos live underneath would make
    the comparison one memo against two.

    Yields:
        Nothing. The levels are restored on the way out, exceptions included.
    """
    restore = dictionary_module._set_memo_levels(
        resolved=False, expanded=False, passed=False, identifiers=False
    )
    try:
        yield
    finally:
        dictionary_module._set_memo_levels(**restore)


def deferral_census(
    identifiers: Sequence[str],
    catalog_factory: Callable[[], GovernedDictionary],
) -> Dict[str, Any]:
    """Count what each route allocates, per consumer shape, and check identity.

    Args:
        identifiers: The corpus, in cache order.
        catalog_factory: Builds a fresh vocabulary per pass.

    Returns:
        Per-arm object counts for both routes, the identity verdict and the
        control-probe verdict.
    """
    figures: Dict[str, Any] = {"identifiers": len(identifiers)}
    policy = NamingPolicy.governed_default()

    for arm in DEFERRAL_ARMS:
        consumer = "to_json" if arm == "to_json_shared" else arm
        catalog = catalog_factory()
        with eager_counts() as eager:
            if consumer == "audit":
                trip = audit_module._trip_policy(policy)
                for name in identifiers:
                    with contextlib.suppress(Exception):
                        audit_module._observe(name, catalog, policy, trip)
            else:
                eager_records = [
                    expansion_module.expand_identifier(name, catalog, policy)
                    for name in identifiers
                ]
                RECORD_ARMS[consumer](eager_records)
        eager_total = sum(eager.values())

        counts = _new_counts()
        with shipped_memos_off():
            catalog = catalog_factory()
            answers: List[Tuple[Any, ...]] = []
            slots: Dict[str, int] = {}
            memo: Dict[str, _Deferred] = {}
            shared: Optional[Dict[Tuple[int, str], TokenExpansion]] = (
                {} if arm == "to_json_shared" else None
            )
            produced = [
                expand_deferred(name, catalog, policy, answers, slots, memo, counts, shared)
                for name in identifiers
            ]
            if consumer == "phrase_only":
                read = sum(1 for deferred in produced if deferred.phrase)
            elif consumer == "gate_only":
                read = sum(1 for deferred in produced if deferred.is_fully_known)
            elif consumer == "audit":
                read = sum(1 for deferred in produced if deferred.tokens)
            else:
                read = sum(1 for deferred in produced if deferred.as_record().to_json())
            counts["lazy_records_read"] = read
        lazy_total = sum(counts[key] for key in LAZY_ALLOCATION_KEYS)

        figures[arm] = {
            **eager,
            **counts,
            "eager_objects": eager_total,
            "lazy_objects": lazy_total,
            "lazy_minus_eager": lazy_total - eager_total,
            "lazy_over_eager": round(lazy_total / eager_total, 4) if eager_total else 0.0,
        }

    # The population every provenance ranking rests on, re-derived here rather
    # than quoted. D-086 measured 3.728 records per identifier and ranked lazy
    # provenance first on it; D-100 and D-101 then moved it and nothing in this
    # repository recomputes it, so the figure a later round would re-open the
    # bet on is whatever the last decision record happened to say.
    settled = figures["to_json"]
    records = settled["eager_identifier_records"] + settled["eager_token_records"]
    figures["provenance_records_constructed"] = records
    figures["provenance_records_per_identifier"] = (
        round(records / len(identifiers), 4) if identifiers else 0.0
    )
    figures["token_memo_hit_pct"] = (
        round(
            100.0
            * settled["lazy_token_memo_hits"]
            / (settled["lazy_token_memo_hits"] + settled["lazy_answer_tuples"]),
            4,
        )
        if settled["lazy_answer_tuples"] or settled["lazy_token_memo_hits"]
        else 0.0
    )
    figures["identifier_memo_hit_pct"] = (
        round(100.0 * settled["lazy_identifier_memo_hits"] / len(identifiers), 4)
        if identifiers
        else 0.0
    )
    figures["deferrable_records"] = settled["eager_token_records"]
    figures["deferrable_records_pct"] = round(100.0 * settled["eager_token_records"] / records, 4)
    figures.update(identity_arm(identifiers, catalog_factory, policy))
    figures.update(unarmed_note(identifiers[:NOTE_IDENTIFIERS], catalog_factory, policy))
    return figures


#: How many identifiers the unarmed note runs over. Capped, because it runs
#: under ``tracemalloc``, which is expensive and which nothing here gates on.
NOTE_IDENTIFIERS = 20_000


def unarmed_note(
    identifiers: Sequence[str],
    catalog_factory: Callable[[], GovernedDictionary],
    policy: NamingPolicy,
) -> Dict[str, Any]:
    """Wall-clock and peak traced allocation for both routes. **Never armed.**

    R18: nanoseconds and bytes are properties of the runner, not of the code,
    and D-013 is the record of this project ratcheting on one once. These
    figures are saved so a reader gets the wall-clock story beside the counts,
    the machine and the interpreter are named on the same entry, and nothing in
    this repository compares them against a threshold.

    The memory figure is **peak traced Python allocation**, from
    :mod:`tracemalloc`, and it is not resident set size. It counts blocks the
    allocator handed to Python objects while the pass ran; RSS also holds the
    interpreter, the corpus, the arenas the allocator has not returned and every
    page the operating system decided to keep. The two move together and they are
    not the same number, which is why this one is named for what it is.

    Args:
        identifiers: The (capped) corpus.
        catalog_factory: Builds a fresh vocabulary per route.
        policy: The resolved policy.

    Returns:
        Wall-clock nanoseconds and peak traced bytes for each route, with the
        identifier count they were taken over.
    """
    figures: Dict[str, Any] = {"note_identifiers": len(identifiers)}

    tracemalloc.start()
    catalog = catalog_factory()
    started = time.perf_counter_ns()
    for name in identifiers:
        expansion_module.expand_identifier(name, catalog, policy).to_json()
    figures["note_eager_ns"] = time.perf_counter_ns() - started
    figures["note_eager_peak_bytes"] = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    with shipped_memos_off():
        tracemalloc.start()
        catalog = catalog_factory()
        counts = _new_counts()
        answers: List[Tuple[Any, ...]] = []
        slots: Dict[str, int] = {}
        memo: Dict[str, _Deferred] = {}
        started = time.perf_counter_ns()
        for name in identifiers:
            expand_deferred(
                name, catalog, policy, answers, slots, memo, counts
            ).as_record().to_json()
        figures["note_lazy_ns"] = time.perf_counter_ns() - started
        figures["note_lazy_peak_bytes"] = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()

    return figures


def identity_arm(
    identifiers: Sequence[str],
    catalog_factory: Callable[[], GovernedDictionary],
    policy: NamingPolicy,
) -> Dict[str, Any]:
    """R19 over the deferred route: every field of every record, both renderings.

    Args:
        identifiers: The corpus.
        catalog_factory: Builds a fresh vocabulary per route.
        policy: The resolved policy.

    Returns:
        The comparison counts, the two identity verdicts and the control probe.
    """
    catalog = catalog_factory()
    shipped = [
        expansion_module.expand_identifier(name, catalog, policy).to_json() for name in identifiers
    ]
    shipped_reprs = []
    catalog = catalog_factory()
    for name in identifiers:
        shipped_reprs.append(repr(expansion_module.expand_identifier(name, catalog, policy)))

    with shipped_memos_off():
        catalog = catalog_factory()
        counts = _new_counts()
        answers: List[Tuple[Any, ...]] = []
        slots: Dict[str, int] = {}
        memo: Dict[str, _Deferred] = {}
        rendered = []
        reprs = []
        for name in identifiers:
            record = expand_deferred(
                name, catalog, policy, answers, slots, memo, counts
            ).as_record()
            rendered.append(record.to_json())
            reprs.append(repr(record))

    json_mismatches = sum(1 for left, right in zip(shipped, rendered) if left != right)
    repr_mismatches = sum(1 for left, right in zip(shipped_reprs, reprs) if left != right)

    # The control: one record's entry_id moved, on one token, over the whole
    # corpus. A comparison that cannot see that is reporting nothing, and this
    # is the failure the whole R19 rule is about.
    probe_fired = False
    if rendered:
        index = len(rendered) // 2
        with shipped_memos_off():
            catalog = catalog_factory()
            probe_answers: List[Tuple[Any, ...]] = []
            probe_slots: Dict[str, int] = {}
            probe_memo: Dict[str, _Deferred] = {}
            probe_counts = _new_counts()
            deferred = expand_deferred(
                identifiers[index],
                catalog,
                policy,
                probe_answers,
                probe_slots,
                probe_memo,
                probe_counts,
            )
            tokens = deferred.tokens
            if tokens:
                moved = _new_token_expansion(
                    tokens[0].raw,
                    tokens[0].long,
                    tokens[0].is_known,
                    tokens[0].source,
                    "probe:moved",
                    tokens[0].confidence,
                    tokens[0].class_word,
                    tokens[0].beat,
                    tokens[0].kind,
                )
                perturbed = _new_identifier_expansion(
                    deferred.identifier,
                    deferred.phrase,
                    (moved, *tokens[1:]),
                    deferred.class_word,
                    deferred.is_fully_known,
                    deferred.unaccounted,
                )
                probe_fired = perturbed.to_json() != shipped[index]
            else:
                probe_fired = False

    return {
        "identity_records": len(rendered),
        "identity_json_mismatches": json_mismatches,
        "identity_repr_mismatches": repr_mismatches,
        "json_identical": json_mismatches == 0,
        "repr_identical": repr_mismatches == 0,
        "control_probe_fired": probe_fired,
        "identity_tokens_not_a_slice": counts["lazy_tokens_not_a_slice"],
    }


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------


def render_reads(run_id: str, entry: Dict[str, Any]) -> List[str]:
    """Format one read census for the console.

    Args:
        run_id: The saved run id.
        entry: What :func:`read_census` returned.

    Returns:
        The lines.
    """
    lines = [
        run_id,
        f"  {int(entry['identifiers']):,} identifiers. A FORCING read is one a deferred design"
        " would have to service by building the token records.",
        f"  {'arm':<12} {'records':>9} {'forcing':>9} {'%':>7} {'.tokens':>9} {'__dict__':>9}"
        f" {'never read':>11}",
    ]
    for arm in ARM_ORDER:
        figures = entry[arm]
        lines.append(
            f"  {arm:<12} {figures['records']:>9,} {figures['forcing']:>9,}"
            f" {figures['forcing_pct']:>7.2f} {figures['read_tokens']:>9,}"
            f" {figures['read_dict']:>9,} {figures['never_read']:>11,}"
        )
    for arm in ARM_ORDER:
        lines.append(f"  {arm:<12} {ARM_NOTES[arm]}")
    if "audit_refusals" in entry:
        lines.append(
            f"  the audit arm REFUSED {int(entry['audit_refusals']):,} identifiers"
            f" ({entry['audit_refusal_pct']} %) -- normalize will not delete an unreadable"
            " character, and the library's own consumer calls it"
        )
    return lines


def render_deferral(run_id: str, entry: Dict[str, Any]) -> List[str]:
    """Format one deferral census for the console.

    Args:
        run_id: The saved run id.
        entry: What :func:`deferral_census` returned.

    Returns:
        The lines.
    """
    lines = [
        run_id,
        f"  objects allocated per corpus pass, {int(entry['identifiers']):,} identifiers."
        " Counts, not nanoseconds (R18).",
        f"  {'arm':<16} {'eager':>11} {'lazy':>11} {'lazy-eager':>11} {'x':>7}",
    ]
    for arm in DEFERRAL_ARMS:
        figures = entry[arm]
        lines.append(
            f"  {arm:<16} {figures['eager_objects']:>11,} {figures['lazy_objects']:>11,}"
            f" {figures['lazy_minus_eager']:>+11,} {figures['lazy_over_eager']:>7.3f}"
        )
    lines.append(
        f"  R19 over {int(entry['identity_records']):,} records:"
        f" json_identical={entry['json_identical']}"
        f" repr_identical={entry['repr_identical']}"
        f" control_probe_fired={entry['control_probe_fired']}"
        f" json_mismatches={int(entry['identity_json_mismatches']):,}"
        f" repr_mismatches={int(entry['identity_repr_mismatches']):,}"
    )
    lines.append(
        "  UNARMED NOTE (R18): wall-clock and peak traced Python allocation, over "
        f"{int(entry['note_identifiers']):,} identifiers on the to_json arm. Nothing gates on "
        "either. This is not RSS."
    )
    lines.append(f"    machine {entry['machine']}")
    lines.append(
        f"    eager {entry['note_eager_ns'] / 1e6:>9.1f} ms  peak traced "
        f"{entry['note_eager_peak_bytes'] / 1e6:>8.2f} MB"
    )
    lines.append(
        f"    lazy  {entry['note_lazy_ns'] / 1e6:>9.1f} ms  peak traced "
        f"{entry['note_lazy_peak_bytes'] / 1e6:>8.2f} MB"
    )
    lines.append(
        f"  the integer array is not free: {int(entry['to_json']['lazy_ir_integers']):,}"
        f" integers carried, {int(entry['to_json']['lazy_ir_large_integers']):,} of them above"
        f" the small-int cache, {int(entry['to_json']['lazy_tokens_not_a_slice']):,} tokens that"
        " are not substrings of their own identifier and had to be carried as text"
    )
    return lines


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point.

    Args:
        argv: Arguments, or ``None`` for ``sys.argv``.

    Returns:
        ``0`` unless R19 failed on an arm that ran.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true", help="record into bench/results.json")
    parser.add_argument(
        "--only",
        choices=("all", "reads", "deferral"),
        default="all",
        help=(
            "'reads' is the runtime read-rate census -- which record fields five real consumer "
            "shapes actually touch; 'deferral' builds the integer-span route and counts what "
            "each route allocates, with R19 over every field of every record."
        ),
    )
    parser.add_argument(
        "--corpus",
        action="append",
        choices=("socrata", "sec_xbrl", "fixture_schema"),
        help="restrict to one corpus; repeatable (default: all three)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="cap each corpus at this many identifiers (0 = the whole corpus)",
    )
    args = parser.parse_args(argv)

    wanted = tuple(args.corpus or ("socrata", "sec_xbrl", "fixture_schema"))
    arms: List[Tuple[str, str, Sequence[str], Callable[[], GovernedDictionary], str]] = []
    if "socrata" in wanted:
        socrata, socrata_source, _ = read_snapshot("socrata")
        arms.append(("socrata", "empty", socrata, lambda: GovernedDictionary({}), socrata_source))
    if "sec_xbrl" in wanted:
        sec_xbrl, sec_source, _ = read_snapshot("sec_xbrl")
        arms.append(("sec_xbrl", "empty", sec_xbrl, lambda: GovernedDictionary({}), sec_source))
    if "fixture_schema" in wanted:
        arms.append(
            (
                "fixture_schema",
                "fixture",
                fixture_schema_corpus(FIXTURE_IDENTIFIERS),
                build_fixture_dictionary,
                "bench fixture pool, seed 0",
            )
        )

    entries: Dict[str, Dict[str, Any]] = {}
    failed: List[str] = []
    for corpus_name, catalog_label, corpus, factory, source in arms:
        population: Sequence[str] = corpus[: args.limit] if args.limit else corpus
        stamp = {
            "corpus": corpus_name,
            "catalog": catalog_label,
            "source": source,
            "environment": environment(),
            "machine": machine_note(),
        }
        if args.only in ("all", "reads"):
            run_id = f"governed_perf.{corpus_name}.{catalog_label}.reads"
            entry = {**read_census(population, factory), **stamp}
            entries[run_id] = entry
            print("\n".join(render_reads(run_id, entry)))
            print()
        if args.only in ("all", "deferral"):
            run_id = f"governed_perf.{corpus_name}.{catalog_label}.deferral"
            entry = {**deferral_census(population, factory), **stamp}
            entries[run_id] = entry
            print("\n".join(render_deferral(run_id, entry)))
            print()
            if not (
                entry["json_identical"] and entry["repr_identical"] and entry["control_probe_fired"]
            ):
                failed.append(run_id)

    if failed:
        print(f"R19 FAILED on {', '.join(failed)}")
        return 1
    if args.save:
        from run_extraction import save_results

        print(f"saved {len(entries)} run(s) to {save_results(entries).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
