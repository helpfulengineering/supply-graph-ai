"""The MoM cache must not turn an unreachable MoM into a gateway timeout.

A failed refresh leaves the cache empty, so ``is_fresh()`` stays False and every
later request used to re-attempt the fetch. Those attempts serialize on the
cache lock, so callers queued behind each other: with a 30s fetch ceiling the
fifth caller waited past nginx's 120s ``proxy_read_timeout`` and the browser saw
a 504 on a match that had nothing to do with MoM being down.

These tests pin the two guards that bound that wait.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from src.core.services.mom_bridge import (
    MOM_FETCH_TIMEOUT_SECONDS,
    MoMSpacesCache,
)

SPACES = [{"space": "urn:a", "name": "A"}]


def patch_fetch(*, result=None, error=None, delay=0.0):
    calls = {"n": 0}

    async def fake_fetch(*_a, **_kw):
        calls["n"] += 1
        if delay:
            await asyncio.sleep(delay)
        if error:
            raise error
        return list(result or [])

    return (
        patch(
            "src.core.services.mom_bridge.fetch_all_mom_spaces", side_effect=fake_fetch
        ),
        calls,
    )


@pytest.mark.asyncio
class TestFailureCooldown:
    async def test_a_failure_suppresses_further_fetches(self):
        """One caller pays the timeout; the rest return immediately."""
        patcher, calls = patch_fetch(error=RuntimeError("MoM down"))
        cache = MoMSpacesCache(failure_cooldown_seconds=60.0)
        with patcher:
            for _ in range(5):
                spaces, available = await cache.get()

        assert calls["n"] == 1, "every request re-attempted the failed fetch"
        assert spaces == []
        assert available is False

    async def test_the_cooldown_expires(self):
        patcher, calls = patch_fetch(error=RuntimeError("MoM down"))
        cache = MoMSpacesCache(failure_cooldown_seconds=0.0)
        with patcher:
            await cache.get()
            await cache.get()

        assert calls["n"] == 2, "a zero cooldown must not suppress the retry"

    async def test_force_refresh_bypasses_the_cooldown(self):
        """An explicit refresh is a deliberate act, not incidental traffic."""
        patcher, calls = patch_fetch(error=RuntimeError("MoM down"))
        cache = MoMSpacesCache(failure_cooldown_seconds=60.0)
        with patcher:
            await cache.get()
            await cache.get(force_refresh=True)

        assert calls["n"] == 2

    async def test_recovery_clears_the_failure_state(self):
        cache = MoMSpacesCache(failure_cooldown_seconds=0.0)
        failing, _ = patch_fetch(error=RuntimeError("MoM down"))
        with failing:
            await cache.get()
        assert cache.in_failure_cooldown() is False  # cooldown 0

        ok, _ = patch_fetch(result=SPACES)
        with ok:
            spaces, available = await cache.get()

        assert spaces == SPACES
        assert available is True
        assert cache.in_failure_cooldown() is False

    async def test_stale_data_is_still_served_after_a_failure(self):
        """Degrading to stale is the point; the cooldown must not lose it."""
        cache = MoMSpacesCache(ttl_seconds=0.0, failure_cooldown_seconds=60.0)
        ok, _ = patch_fetch(result=SPACES)
        with ok:
            await cache.get()

        failing, _ = patch_fetch(error=RuntimeError("MoM down"))
        with failing:
            spaces, available = await cache.get()

        assert spaces == SPACES
        assert available is True


@pytest.mark.asyncio
class TestNoQueueingBehindARefresh:
    async def test_holders_of_stale_data_do_not_wait_for_an_in_flight_refresh(self):
        """The queueing that produced the 504, in miniature."""
        cache = MoMSpacesCache(ttl_seconds=0.0)
        ok, _ = patch_fetch(result=SPACES)
        with ok:
            await cache.get()  # seed, now stale

        slow, calls = patch_fetch(result=SPACES, delay=0.3)
        with slow:
            refresher = asyncio.create_task(cache.get())
            await asyncio.sleep(0.05)  # let it take the lock

            waiter = await asyncio.wait_for(cache.get(), timeout=0.1)
            await refresher

        assert waiter == (SPACES, True)
        assert calls["n"] == 1, "the second caller triggered its own fetch"

    async def test_a_cold_cache_still_waits_for_data(self):
        """With nothing to serve, waiting is correct — there is no stale copy."""
        cache = MoMSpacesCache()
        slow, calls = patch_fetch(result=SPACES, delay=0.05)
        with slow:
            first, second = await asyncio.gather(cache.get(), cache.get())

        assert first == (SPACES, True)
        assert second == (SPACES, True)
        assert calls["n"] == 1, "the lock must still collapse a thundering herd"


def test_the_fetch_timeout_is_bounded():
    """~2s in production for 3,193 spaces; 30s let callers cross the gateway."""
    assert MOM_FETCH_TIMEOUT_SECONDS <= 15.0
