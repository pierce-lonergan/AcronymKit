"""Tests for the batch and async fan-out APIs.

:mod:`acronymkit.batch` makes three promises that a bare
``ThreadPoolExecutor.map`` does not: submission order is preserved, one failure
never aborts the batch, and the envelope is deterministic. Those three, plus the
equivalence of the synchronous, threaded and asyncio paths, are what this module
pins.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Callable, Optional

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from acronymkit import AcronymEngine
from acronymkit.batch import arun_batch, run_batch
from acronymkit.exceptions import ConfigurationError, EmptyPhraseError
from acronymkit.models import AcronymResult, BatchResult
from conftest import CANONICAL_ACRONYMS

PHRASES = [phrase for phrase, _ in CANONICAL_ACRONYMS]
EXPECTED = [acronym for _, acronym in CANONICAL_ACRONYMS]

#: Inputs the engine must reject, interleaved with good ones by the tests below.
BAD_PHRASES = ["", "   ", "\t\n ", "the of and"]


def _stable(result: AcronymResult) -> dict:
    """Return a result payload with the wall-clock reading neutralised.

    ``execution_time_ms`` is the only field that legitimately differs between
    two runs of the same input, so it is zeroed before results are compared.
    """
    payload = result.to_dict()
    payload["metadata"]["execution_time_ms"] = 0.0
    return payload


class _ConcurrencyProbe:
    """Wrap a callable and record the peak number of simultaneous calls."""

    def __init__(self, inner: Callable[[str], AcronymResult], hold: float = 0.01) -> None:
        self._inner = inner
        self._hold = hold
        self._lock = threading.Lock()
        self.active = 0
        self.peak = 0
        self.calls = 0

    def __call__(self, phrase: str) -> AcronymResult:
        with self._lock:
            self.active += 1
            self.calls += 1
            self.peak = max(self.peak, self.active)
        try:
            time.sleep(self._hold)  # widen the window so overlap is observable
            return self._inner(phrase)
        finally:
            with self._lock:
                self.active -= 1


# ---------------------------------------------------------------------------
# Order preservation
# ---------------------------------------------------------------------------
def test_batch_generate_preserves_submission_order(engine: AcronymEngine) -> None:
    """``results[i]`` corresponds to ``phrases[i]`` whatever order work finished."""
    batch = engine.batch_generate(PHRASES)
    assert len(batch.results) == len(PHRASES)
    assert [result.primary_acronym for result in batch.results] == EXPECTED
    assert [result.source_phrase for result in batch.results] == PHRASES


def test_order_is_preserved_with_failures_interleaved(engine: AcronymEngine) -> None:
    """Failed slots hold their position rather than compacting the list."""
    phrases = ["Portable Document Format", "", "Random Access Memory", "   "]
    batch = engine.batch_generate(phrases)
    assert [result.primary_acronym if result is not None else None for result in batch.results] == [
        "PDF",
        None,
        "RAM",
        None,
    ]


@settings(max_examples=20, deadline=None)
@given(indices=st.lists(st.integers(min_value=0, max_value=len(PHRASES) - 1), max_size=6))
def test_order_is_preserved_for_any_submission(engine: AcronymEngine, indices: list[int]) -> None:
    """Property: every slot holds the acronym of the phrase submitted there."""
    phrases = [PHRASES[index] for index in indices]
    batch = engine.batch_generate(phrases, max_workers=2)
    assert [result.primary_acronym for result in batch.results] == [
        EXPECTED[index] for index in indices
    ]


# ---------------------------------------------------------------------------
# Failure isolation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad", BAD_PHRASES, ids=repr)
def test_a_failing_item_yields_none_and_records_its_error(engine: AcronymEngine, bad: str) -> None:
    """The failure is confined to its own index and carries a typed message."""
    phrases = ["Portable Document Format", bad, "Random Access Memory"]
    batch = engine.batch_generate(phrases)

    assert batch.results[1] is None
    assert set(batch.errors) == {1}
    assert batch.errors[1].startswith("EmptyPhraseError:")
    # The rest of the batch ran regardless.
    assert batch.results[0] is not None
    assert batch.results[2] is not None
    assert batch.results[0].primary_acronym == "PDF"
    assert batch.results[2].primary_acronym == "RAM"


def test_many_failures_do_not_abort_the_batch(engine: AcronymEngine) -> None:
    """Every good phrase still produces a result no matter how many failed."""
    phrases: list[str] = []
    good_positions: list[int] = []
    for index, phrase in enumerate(PHRASES[:8]):
        good_positions.append(len(phrases))
        phrases.append(phrase)
        phrases.append(BAD_PHRASES[index % len(BAD_PHRASES)])

    batch = engine.batch_generate(phrases)

    assert batch.failure_count == 8
    assert len(batch.succeeded) == 8
    assert [batch.results[position].primary_acronym for position in good_positions] == (
        EXPECTED[:8]
    )


def test_error_indices_are_returned_in_ascending_order(engine: AcronymEngine) -> None:
    """The envelope is byte-stable: errors are re-keyed low to high."""
    phrases = ["", "Portable Document Format", "  ", "", "Random Access Memory", ""]
    batch = engine.batch_generate(phrases)
    assert list(batch.errors) == sorted(batch.errors)
    assert list(batch.errors) == [0, 2, 3, 5]


def test_error_message_names_the_exception_type(engine: AcronymEngine) -> None:
    """Errors distinguished by type, not wording, stay distinguishable."""
    batch = engine.batch_generate(["the of and"])
    assert batch.results[0] is None
    assert batch.errors[0].startswith("EmptyPhraseError: ")
    assert "no acronym-eligible tokens" in batch.errors[0]


def test_an_exception_with_no_message_still_records_its_type() -> None:
    """``_describe`` falls back to the bare type name."""

    def explode(phrase: str) -> AcronymResult:
        raise RuntimeError

    batch = run_batch(explode, ["anything"], max_workers=1)
    assert batch.results == [None]
    assert batch.errors == {0: "RuntimeError"}


def test_base_exceptions_are_not_swallowed() -> None:
    """Interpreter-level signals propagate instead of becoming batch errors."""

    def interrupt(phrase: str) -> AcronymResult:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_batch(interrupt, ["anything"], max_workers=1)


# ---------------------------------------------------------------------------
# succeeded / failure_count
# ---------------------------------------------------------------------------
def test_succeeded_and_failure_count(engine: AcronymEngine) -> None:
    """The two convenience properties agree with ``results`` and ``errors``."""
    phrases = ["Portable Document Format", "", "Quality Assurance", "   "]
    batch = engine.batch_generate(phrases)

    assert batch.failure_count == 2
    assert batch.failure_count == len(batch.errors)
    assert [result.primary_acronym for result in batch.succeeded] == ["PDF", "QA"]
    assert len(batch.succeeded) + batch.failure_count == len(batch.results)
    assert all(result is not None for result in batch.succeeded)


def test_a_fully_successful_batch_reports_no_failures(engine: AcronymEngine) -> None:
    """No errors means ``succeeded`` is the whole list."""
    batch = engine.batch_generate(PHRASES[:5])
    assert batch.failure_count == 0
    assert batch.errors == {}
    assert batch.succeeded == batch.results


def test_a_fully_failing_batch_reports_no_successes(engine: AcronymEngine) -> None:
    """Every slot may fail without anything blowing up."""
    batch = engine.batch_generate(BAD_PHRASES)
    assert batch.succeeded == []
    assert batch.failure_count == len(BAD_PHRASES)
    assert all(result is None for result in batch.results)


# ---------------------------------------------------------------------------
# Equivalence with the sequential path
# ---------------------------------------------------------------------------
def test_batch_results_match_sequential_results(engine: AcronymEngine) -> None:
    """Fanning out changes throughput, never answers."""
    sequential = [_stable(engine.generate(phrase)) for phrase in PHRASES]
    batch = engine.batch_generate(PHRASES)
    assert [_stable(result) for result in batch.results] == sequential


@pytest.mark.parametrize("max_workers", [1, 2, 4, 8], ids=lambda n: f"workers={n}")
def test_results_are_independent_of_the_worker_count(
    engine: AcronymEngine, max_workers: int
) -> None:
    """Pool size is a performance knob with no semantic effect."""
    reference = [_stable(engine.generate(phrase)) for phrase in PHRASES[:8]]
    batch = engine.batch_generate(PHRASES[:8], max_workers=max_workers)
    assert [_stable(result) for result in batch.results] == reference


def test_batch_reports_a_non_negative_total_time(engine: AcronymEngine) -> None:
    """The envelope times the whole fan-out."""
    batch = engine.batch_generate(PHRASES[:4])
    assert batch.total_execution_time_ms >= 0.0


# ---------------------------------------------------------------------------
# Concurrency limits
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("max_workers", [1, 2, 3], ids=lambda n: f"workers={n}")
def test_run_batch_never_exceeds_the_requested_worker_count(
    engine: AcronymEngine, max_workers: int
) -> None:
    """No more than ``max_workers`` items are ever in flight at once."""
    probe = _ConcurrencyProbe(engine.generate)
    batch = run_batch(probe, PHRASES[:8], max_workers=max_workers)

    assert probe.calls == 8
    assert probe.peak <= max_workers
    assert probe.active == 0
    assert [result.primary_acronym for result in batch.results] == EXPECTED[:8]


def test_a_single_worker_runs_strictly_sequentially(engine: AcronymEngine) -> None:
    """``max_workers=1`` takes the no-pool path and never overlaps."""
    probe = _ConcurrencyProbe(engine.generate, hold=0.0)
    run_batch(probe, PHRASES[:4], max_workers=1)
    assert probe.peak == 1


def test_the_pool_really_does_run_items_in_parallel(engine: AcronymEngine) -> None:
    """The bound is an upper limit on real concurrency, not on a serial loop.

    Four items are submitted to four workers and each rendezvouses on a
    four-party barrier: the batch can only complete if all four ran at once, so
    a silently sequential implementation deadlocks the barrier and fails.
    """
    barrier = threading.Barrier(4)

    def rendezvous(phrase: str) -> AcronymResult:
        barrier.wait(timeout=10)
        return engine.generate(phrase)

    batch = run_batch(rendezvous, PHRASES[:4], max_workers=4)
    assert [result.primary_acronym for result in batch.results] == EXPECTED[:4]
    assert batch.failure_count == 0


def test_the_pool_is_never_larger_than_the_batch(engine: AcronymEngine) -> None:
    """Asking for more workers than items does not over-provision."""
    probe = _ConcurrencyProbe(engine.generate)
    run_batch(probe, PHRASES[:2], max_workers=64)
    assert probe.peak <= 2


@pytest.mark.parametrize("max_workers", [0, -1, -100], ids=repr)
def test_non_positive_worker_counts_are_rejected(engine: AcronymEngine, max_workers: int) -> None:
    """A nonsensical pool size is a configuration error, not a silent clamp."""
    with pytest.raises(ConfigurationError):
        engine.batch_generate(PHRASES[:2], max_workers=max_workers)


@pytest.mark.parametrize("concurrency", [0, -1], ids=repr)
async def test_non_positive_concurrency_is_rejected(
    engine: AcronymEngine, concurrency: int
) -> None:
    """The async path validates its bound the same way."""
    with pytest.raises(ConfigurationError):
        await engine.abatch_generate(PHRASES[:2], concurrency=concurrency)


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------
def test_empty_batch_is_handled(engine: AcronymEngine) -> None:
    """An empty submission produces an empty, well-formed envelope."""
    batch = engine.batch_generate([])
    assert isinstance(batch, BatchResult)
    assert batch.results == []
    assert batch.errors == {}
    assert batch.succeeded == []
    assert batch.failure_count == 0
    assert batch.total_execution_time_ms >= 0.0


def test_empty_batch_never_starts_a_pool() -> None:
    """No work means the callable is not invoked at all."""
    calls: list[str] = []

    def record(phrase: str) -> AcronymResult:  # pragma: no cover - never called
        calls.append(phrase)
        raise AssertionError("run_batch called func for an empty batch")

    assert run_batch(record, []).results == []
    assert calls == []


async def test_empty_async_batch_is_handled(engine: AcronymEngine) -> None:
    """The asyncio path agrees with the threaded one on the empty case."""
    batch = await engine.abatch_generate([])
    assert batch.results == []
    assert batch.errors == {}
    assert batch.failure_count == 0


def test_empty_batch_accepts_any_worker_count(engine: AcronymEngine) -> None:
    """Sizing logic must not divide by, or clamp to, zero items."""
    assert engine.batch_generate([], max_workers=4).results == []


# ---------------------------------------------------------------------------
# asyncio equivalence
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("phrase", "expected"), CANONICAL_ACRONYMS, ids=[phrase for phrase, _ in CANONICAL_ACRONYMS]
)
async def test_agenerate_matches_generate(
    engine: AcronymEngine, phrase: str, expected: str
) -> None:
    """``agenerate`` is ``generate`` on a worker thread — same answer."""
    synchronous = engine.generate(phrase)
    asynchronous = await engine.agenerate(phrase)
    assert asynchronous.primary_acronym == expected
    assert _stable(asynchronous) == _stable(synchronous)


async def test_agenerate_propagates_failures(engine: AcronymEngine) -> None:
    """A bad phrase raises through the await rather than returning ``None``."""
    with pytest.raises(EmptyPhraseError):
        await engine.agenerate("   ")


async def test_abatch_generate_matches_batch_generate(engine: AcronymEngine) -> None:
    """The asyncio fan-out returns exactly what the threaded one returns."""
    phrases = [*PHRASES[:8], "", "the of and"]
    threaded = engine.batch_generate(phrases)
    awaited = await engine.abatch_generate(phrases)

    assert [_stable(result) if result is not None else None for result in awaited.results] == [
        _stable(result) if result is not None else None for result in threaded.results
    ]
    assert awaited.errors == threaded.errors
    assert awaited.failure_count == threaded.failure_count


async def test_abatch_generate_preserves_order_and_isolates_failures(
    engine: AcronymEngine,
) -> None:
    """The three batch guarantees hold on the asyncio path too."""
    phrases = ["Portable Document Format", "", "Random Access Memory"]
    batch = await engine.abatch_generate(phrases)
    assert [result.primary_acronym if result is not None else None for result in batch.results] == [
        "PDF",
        None,
        "RAM",
    ]
    assert list(batch.errors) == [1]


@pytest.mark.parametrize("concurrency", [1, 2, 3], ids=lambda n: f"concurrency={n}")
async def test_arun_batch_respects_its_concurrency_bound(
    engine: AcronymEngine, concurrency: int
) -> None:
    """The semaphore caps items in flight, however many were submitted."""
    probe = _ConcurrencyProbe(engine.generate)
    batch = await arun_batch(probe, PHRASES[:8], concurrency=concurrency)

    assert probe.calls == 8
    assert probe.peak <= concurrency
    assert probe.active == 0
    assert [result.primary_acronym for result in batch.results] == EXPECTED[:8]


async def test_arun_batch_really_does_run_items_in_parallel(
    engine: AcronymEngine,
) -> None:
    """The semaphore bounds concurrency without serialising it.

    As in the threaded case, a four-party barrier makes genuine parallelism a
    precondition for the batch completing at all.
    """
    barrier = threading.Barrier(4)

    def rendezvous(phrase: str) -> AcronymResult:
        barrier.wait(timeout=10)
        return engine.generate(phrase)

    batch = await arun_batch(rendezvous, PHRASES[:4], concurrency=4)
    assert [result.primary_acronym for result in batch.results] == EXPECTED[:4]
    assert batch.failure_count == 0


async def test_abatch_generate_does_not_block_the_event_loop(
    engine: AcronymEngine,
) -> None:
    """Other coroutines keep running while the batch is in flight."""
    ticks = 0

    async def heartbeat() -> None:
        nonlocal ticks
        for _ in range(20):
            await asyncio.sleep(0.001)
            ticks += 1

    beat = asyncio.ensure_future(heartbeat())
    batch = await engine.abatch_generate(PHRASES, concurrency=4)
    await beat

    assert len(batch.succeeded) == len(PHRASES)
    assert ticks == 20


# ---------------------------------------------------------------------------
# run_batch as a standalone helper
# ---------------------------------------------------------------------------
def test_run_batch_consumes_an_arbitrary_iterable(engine: AcronymEngine) -> None:
    """Inputs are materialised once, so a generator is a valid argument."""
    batch = run_batch(engine.generate, (phrase for phrase in PHRASES[:3]))
    assert [result.primary_acronym for result in batch.results] == EXPECTED[:3]


def test_run_batch_and_arun_batch_agree(engine: AcronymEngine) -> None:
    """The two helpers are interchangeable from the caller's point of view."""
    phrases = [*PHRASES[:6], ""]
    threaded = run_batch(engine.generate, phrases)
    awaited = asyncio.run(arun_batch(engine.generate, phrases))

    def _norm(batch: BatchResult) -> list[Optional[dict]]:
        return [_stable(result) if result is not None else None for result in batch.results]

    assert _norm(threaded) == _norm(awaited)
    assert threaded.errors == awaited.errors


def test_run_batch_accepts_any_callable(engine: AcronymEngine) -> None:
    """The helper is generic over the mapped function, not tied to ``generate``."""
    reference = engine.generate("Portable Document Format")

    def constant(phrase: str) -> Any:
        return reference

    batch = run_batch(constant, ["a", "b", "c"], max_workers=2)
    assert [result.primary_acronym for result in batch.results] == ["PDF"] * 3
