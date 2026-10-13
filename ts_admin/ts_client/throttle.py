"""Per-cluster ThoughtSpot API limiter.

One ``ClusterLimiter`` per (event loop, base_url). Every HTTP attempt holds a
global slot; the background lane additionally holds one of ``max - reserve``
background slots, so a sync can never starve UI clicks of the reserved slots.
A 429 pauses the whole cluster (all lanes) until ``pause_until``.
"""

import asyncio
import functools
import time
import weakref
from collections.abc import Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any, TypeVar

MAX_CONCURRENT = 6
INTERACTIVE_RESERVE = 2

INTERACTIVE = "interactive"
BACKGROUND = "background"

current_lane: ContextVar[str] = ContextVar("ts_api_lane", default=INTERACTIVE)

R = TypeVar("R")


class ClusterLimiter:
    def __init__(self, max_concurrent: int = MAX_CONCURRENT, interactive_reserve: int = INTERACTIVE_RESERVE) -> None:
        self._global = asyncio.Semaphore(max_concurrent)
        self._background = asyncio.Semaphore(max_concurrent - interactive_reserve)
        self.pause_until = 0.0  # time.monotonic() deadline

    def pause(self, seconds: float) -> None:
        self.pause_until = max(self.pause_until, time.monotonic() + seconds)

    @asynccontextmanager
    async def slot(self, lane: str = INTERACTIVE):
        sems = (self._background, self._global) if lane == BACKGROUND else (self._global,)
        while True:
            while (remaining := self.pause_until - time.monotonic()) > 0:
                await asyncio.sleep(remaining)
            for sem in sems:
                await sem.acquire()
            # A 429 may have landed while we queued; waiters must not fire into it.
            if self.pause_until <= time.monotonic():
                break
            for sem in reversed(sems):
                sem.release()
        try:
            yield
        finally:
            for sem in reversed(sems):
                sem.release()


_registry: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[str, ClusterLimiter]]" = (
    weakref.WeakKeyDictionary()
)


def limiter_for(base_url: str) -> ClusterLimiter:
    # Keyed by loop: asyncio semaphores bind to one loop, and tests use fresh loops
    # (weak, so closed loops don't leak).
    return _registry.setdefault(asyncio.get_running_loop(), {}).setdefault(base_url, ClusterLimiter())


def _reset_for_tests() -> None:
    _registry.clear()


@contextmanager
def lane(name: str) -> Iterator[None]:
    token = current_lane.set(name)
    try:
        yield
    finally:
        current_lane.reset(token)


def background(fn: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
    """Decorator: run an async job target in the background lane."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> R:
        with lane(BACKGROUND):
            return await fn(*args, **kwargs)

    return wrapper
