"""Fan-out helpers behind the engine's batch and async APIs.

Both entry points map one callable over a sequence of inputs and return a
single :class:`~acronymkit.models.BatchResult`. They share three guarantees
that a bare ``ThreadPoolExecutor.map`` or ``asyncio.gather`` does not give:

**Submission order is preserved.**
    ``results[i]`` always corresponds to ``items[i]``, whatever order the work
    actually completed in. Slots are pre-allocated and written by index rather
    than appended.

**One failure never aborts the batch.**
    Every item is executed inside its own ``try``/``except Exception``. A raised
    exception is recorded as ``errors[i]`` and leaves ``results[i] is None``;
    the remaining items run regardless. ``BaseException`` (``KeyboardInterrupt``,
    ``SystemExit``, ``asyncio.CancelledError``) is deliberately *not* caught, so
    interpreter-level shutdown signals still propagate.

**The envelope is deterministic.**
    ``errors`` is rebuilt in ascending index order before it is returned, so two
    runs that fail on the same items produce byte-identical JSON even though the
    failures were observed in a race-dependent order.

The work itself is synchronous and CPU-bound, so :func:`arun_batch` offloads it
to :func:`asyncio.to_thread` rather than pretending it is awaitable, and bounds
the number of in-flight items with an :class:`asyncio.Semaphore`. That keeps a
ten-thousand-phrase batch from spawning ten thousand worker threads while the
event loop stays free to serve other coroutines.

The module is standard library plus ``pydantic`` and the frozen
``acronymkit`` core, so it is importable on the Tier 0 path.

Import cost
-----------
:mod:`asyncio` and :mod:`concurrent.futures` are imported *inside* the two
functions that need them rather than at module scope. ``asyncio`` in particular
is one of the heaviest imports in the standard library — measured at roughly the
cost of importing the rest of this package — and neither a synchronous
``generate`` nor the ``acronymkit`` CLI should pay for machinery it never
touches. After the first call the deferred import is a :data:`sys.modules`
lookup, which is far below the cost of the work being fanned out.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Callable, Iterable, Optional

from .exceptions import ConfigurationError
from .models import AcronymResult, BatchResult

if TYPE_CHECKING:  # pragma: no cover - typing only; see "Import cost" above
    from concurrent.futures import Future

__all__ = ["arun_batch", "run_batch"]


#: Upper bound on worker threads chosen automatically, mirroring the ceiling
#: :class:`~concurrent.futures.ThreadPoolExecutor` applies to its own default.
DEFAULT_MAX_WORKERS = 32

#: Extra threads over the CPU count when sizing the pool automatically. The
#: work is CPU-bound but releases the GIL around resource I/O on first use, so a
#: small amount of oversubscription keeps the pool busy.
_WORKER_HEADROOM = 4

#: Milliseconds per second, for ``total_execution_time_ms``.
_MS_PER_SECOND = 1000.0


def _describe(exc: Exception) -> str:
    """Render an exception as the string stored in ``BatchResult.errors``.

    Args:
        exc: The exception raised while processing one item.

    Returns:
        ``"TypeName: message"``, or just ``"TypeName"`` when the exception
        carries no message. The type name is always included because several
        library errors (notably
        :class:`~acronymkit.exceptions.EmptyPhraseError`) are distinguished by
        type rather than by wording.
    """
    message = str(exc).strip()
    name = type(exc).__name__
    return f"{name}: {message}" if message else name


def _resolve_workers(requested: Optional[int], count: int) -> int:
    """Return the thread-pool size to use for ``count`` items.

    Args:
        requested: Caller-supplied worker count, or ``None`` for automatic
            sizing.
        count: Number of items in the batch; the pool is never larger than this.

    Returns:
        A worker count of at least ``1``.

    Raises:
        ConfigurationError: If ``requested`` is not a positive integer.
    """
    if requested is None:
        automatic = (os.cpu_count() or 1) + _WORKER_HEADROOM
        return max(1, min(DEFAULT_MAX_WORKERS, automatic, count))
    if requested < 1:
        raise ConfigurationError(f"max_workers must be >= 1, got {requested}")
    return max(1, min(requested, count))


def _resolve_concurrency(requested: Optional[int], count: int) -> int:
    """Return the number of items :func:`arun_batch` may have in flight.

    Args:
        requested: Caller-supplied bound, or ``None`` for automatic sizing.
        count: Number of items in the batch.

    Returns:
        A concurrency limit of at least ``1``.

    Raises:
        ConfigurationError: If ``requested`` is not a positive integer.
    """
    if requested is None:
        return _resolve_workers(None, count)
    if requested < 1:
        raise ConfigurationError(f"concurrency must be >= 1, got {requested}")
    return max(1, min(requested, count))


def _envelope(
    results: list[Optional[AcronymResult]],
    errors: dict[int, str],
    started: float,
) -> BatchResult:
    """Package the collected outcomes as a :class:`BatchResult`.

    Args:
        results: Positional slots, already aligned with the submitted items.
        errors: Index-keyed failure messages, in whatever order they occurred.
        started: :func:`time.perf_counter` reading taken before the fan-out.

    Returns:
        The batch envelope, with ``errors`` re-keyed in ascending index order so
        the payload is byte-stable across runs.
    """
    elapsed_ms = (time.perf_counter() - started) * _MS_PER_SECOND
    return BatchResult(
        results=results,
        errors={index: errors[index] for index in sorted(errors)},
        total_execution_time_ms=max(0.0, elapsed_ms),
    )


def run_batch(
    func: Callable[[str], AcronymResult],
    items: Iterable[str],
    *,
    max_workers: Optional[int] = None,
) -> BatchResult:
    """Map ``func`` over ``items`` on a thread pool, collecting per-item errors.

    A single worker is used when the batch holds one item (or ``max_workers``
    is ``1``), which avoids paying for a pool on the common one-shot call.

    Args:
        func: Callable applied to each item, typically
            :meth:`~acronymkit.engine.AcronymEngine.generate`. It must be safe
            to call concurrently from several threads.
        items: The inputs, consumed once and materialised in order.
        max_workers: Thread-pool size. ``None`` picks
            ``min(32, cpu_count + 4, len(items))``.

    Returns:
        A :class:`~acronymkit.models.BatchResult` whose ``results`` list is
        positionally aligned with ``items``: a failed item leaves ``None`` in
        its slot and its message in ``errors`` under the same index.

    Raises:
        ConfigurationError: If ``max_workers`` is given and is below ``1``.

    Example:
        >>> from acronymkit import AcronymEngine
        >>> engine = AcronymEngine()
        >>> batch = run_batch(engine.generate, ["Portable Document Format", "   "])
        >>> batch.results[0].primary_acronym
        'PDF'
        >>> batch.results[1] is None
        True
        >>> sorted(batch.errors)
        [1]
    """
    entries = list(items)
    started = time.perf_counter()
    results: list[Optional[AcronymResult]] = [None] * len(entries)
    errors: dict[int, str] = {}
    if not entries:
        return _envelope(results, errors, started)

    workers = _resolve_workers(max_workers, len(entries))
    if workers == 1:
        for index, item in enumerate(entries):
            try:
                results[index] = func(item)
            except Exception as exc:
                errors[index] = _describe(exc)
        return _envelope(results, errors, started)

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures: list[Future[AcronymResult]] = [pool.submit(func, item) for item in entries]
        for index, future in enumerate(futures):
            try:
                results[index] = future.result()
            except Exception as exc:
                errors[index] = _describe(exc)
    return _envelope(results, errors, started)


async def arun_batch(
    func: Callable[[str], AcronymResult],
    items: Iterable[str],
    *,
    concurrency: Optional[int] = None,
) -> BatchResult:
    """Await ``func`` over ``items`` on worker threads, collecting per-item errors.

    Each item is executed with :func:`asyncio.to_thread` while an
    :class:`asyncio.Semaphore` caps how many run at once, so the event loop is
    never blocked and the thread count stays bounded no matter how long the
    batch is.

    Args:
        func: Callable applied to each item; must be thread-safe.
        items: The inputs, consumed once and materialised in order.
        concurrency: Maximum items in flight. ``None`` picks
            ``min(32, cpu_count + 4, len(items))``.

    Returns:
        A :class:`~acronymkit.models.BatchResult` positionally aligned with
        ``items``, exactly as :func:`run_batch` returns.

    Raises:
        ConfigurationError: If ``concurrency`` is given and is below ``1``.

    Example:
        >>> import asyncio
        >>> from acronymkit import AcronymEngine
        >>> engine = AcronymEngine()
        >>> phrases = ["Application Programming Interface"]
        >>> asyncio.run(arun_batch(engine.generate, phrases)).results[0].primary_acronym
        'API'
    """
    import asyncio

    entries = list(items)
    started = time.perf_counter()
    results: list[Optional[AcronymResult]] = [None] * len(entries)
    errors: dict[int, str] = {}
    if not entries:
        return _envelope(results, errors, started)

    semaphore = asyncio.Semaphore(_resolve_concurrency(concurrency, len(entries)))

    async def _run(index: int, item: str) -> None:
        """Execute one item off-loop, recording its result or its failure."""
        async with semaphore:
            try:
                results[index] = await asyncio.to_thread(func, item)
            except Exception as exc:
                errors[index] = _describe(exc)

    await asyncio.gather(*(_run(index, item) for index, item in enumerate(entries)))
    return _envelope(results, errors, started)
