"""Per-cluster limiter (S51) and the 429 Retry-After handling it feeds."""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest

from ts_admin.ts_client import retry, throttle
from ts_admin.ts_client.exceptions import TSRateLimitError
from ts_admin.ts_client.throttle import ClusterLimiter


async def _hold(limiter, lane, gauge, release):
    async with limiter.slot(lane):
        gauge["n"] += 1
        gauge["peak"] = max(gauge["peak"], gauge["n"])
        await release.wait()
        gauge["n"] -= 1


async def _settle():
    for _ in range(5):
        await asyncio.sleep(0)


async def test_background_capped_at_max_minus_reserve():
    limiter, gauge, release = ClusterLimiter(6, 2), {"n": 0, "peak": 0}, asyncio.Event()
    tasks = [asyncio.create_task(_hold(limiter, "background", gauge, release)) for _ in range(10)]
    await _settle()
    assert gauge["n"] == 4
    release.set()
    await asyncio.gather(*tasks)
    assert gauge["peak"] == 4


async def test_reserve_admits_interactive_while_background_saturated():
    limiter, gauge, release = ClusterLimiter(6, 2), {"n": 0, "peak": 0}, asyncio.Event()
    bg = [asyncio.create_task(_hold(limiter, "background", gauge, release)) for _ in range(10)]
    await _settle()
    ui = [asyncio.create_task(_hold(limiter, "interactive", gauge, release)) for _ in range(3)]
    await _settle()
    assert gauge["n"] == 6  # 4 background + 2 interactive; the 3rd interactive waits
    release.set()
    await asyncio.gather(*bg, *ui)
    assert gauge["peak"] == 6  # global cap


async def test_pause_blocks_all_lanes():
    limiter = ClusterLimiter(6, 2)
    for lane in ("interactive", "background"):
        limiter.pause(0.15)
        limiter.pause(0.01)  # never shortens
        start = time.monotonic()
        async with limiter.slot(lane):
            pass
        assert time.monotonic() - start >= 0.1


async def test_slot_released_on_exception():
    limiter = ClusterLimiter(2, 1)
    for lane in ("background", "interactive"):
        for _ in range(3):
            with pytest.raises(RuntimeError):
                async with limiter.slot(lane):
                    raise RuntimeError("boom")
    async with limiter.slot("background"):
        pass


def test_registry_is_per_loop_and_url():
    throttle._reset_for_tests()

    async def get(url):
        return throttle.limiter_for(url), throttle.limiter_for(url)

    a1, a2 = asyncio.run(get("https://a"))
    assert a1 is a2
    b, _ = asyncio.run(get("https://a"))  # fresh loop -> fresh limiter
    assert b is not a1

    async def two():
        return throttle.limiter_for("https://a") is throttle.limiter_for("https://b")

    assert asyncio.run(two()) is False


def test_lane_context_manager_resets():
    assert throttle.current_lane.get() == "interactive"
    with throttle.lane("background"):
        assert throttle.current_lane.get() == "background"
    assert throttle.current_lane.get() == "interactive"


async def test_background_decorator_sets_lane():
    @throttle.background
    async def job():
        return throttle.current_lane.get()

    assert await job() == "background"
    assert throttle.current_lane.get() == "interactive"


# ── Retry-After / 429 ──────────────────────────────────────────────────────


def test_parse_retry_after_variants():
    assert retry.parse_retry_after("7") == 7
    assert retry.parse_retry_after("9999") == retry.MAX_RETRY_AFTER_SECONDS
    future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=30), usegmt=True)
    assert 25 <= retry.parse_retry_after(future) <= 31
    past = format_datetime(datetime.now(timezone.utc) - timedelta(seconds=30), usegmt=True)
    assert retry.parse_retry_after(past) is None
    for bad in (None, "", "garbage", "Not, 99 Foo 0000 99:99:99 GMT"):
        assert retry.parse_retry_after(bad) is None


def _429(retry_after):
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    request = httpx.Request("GET", "https://x/y")
    return httpx.HTTPStatusError("429", request=request, response=httpx.Response(429, headers=headers, request=request))


@pytest.mark.parametrize("header", ["1", "garbage", None])
async def test_429_pauses_cluster_and_retries(monkeypatch, header):
    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)

    monkeypatch.setattr(retry.asyncio, "sleep", fake_sleep)
    paused: list[float] = []
    calls = {"n": 0}

    async def op():
        calls["n"] += 1
        if calls["n"] == 1:
            raise _429(header)
        return "ok"

    assert await retry.with_retry(op, on_rate_limit=paused.append) == "ok"
    assert len(paused) == 1 and paused[0] == sleeps[0]
    assert 1.0 <= paused[0] <= retry.MAX_RETRY_AFTER_SECONDS + 1


async def test_429_exhausted_raises_rate_limit_error(monkeypatch):
    async def fake_sleep(_s):
        return None

    monkeypatch.setattr(retry.asyncio, "sleep", fake_sleep)

    async def op():
        raise _429("3")

    with pytest.raises(TSRateLimitError):
        await retry.with_retry(op)
