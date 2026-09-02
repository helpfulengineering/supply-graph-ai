"""A Celery task must not inherit services bound to a closed event loop.

The production failure this pins: the first generation after a worker start
used the LLM, and every generation after it reported "no provider is
configured" while a valid, readable credential sat in storage.

Each task body calls ``asyncio.run``, which closes its loop on return. The
services are process-wide singletons that outlive it, holding clients bound to
that dead loop. ``OKHService._initialize_dependencies`` skips ``configure()``
when storage is already configured, so task two inherits a service that reports
itself ready and can read nothing — and the read that failed was the credential
lookup, whose exception is swallowed at DEBUG.
"""

from __future__ import annotations

import asyncio

import pytest

from src.core.jobs.tasks import reset_loop_bound_singletons
from src.core.services.base import BaseService
from src.core.services.storage_service import StorageService


def _one_task(reset: bool) -> StorageService:
    """Run one task body the way Celery does, returning the service it used.

    Returns the object rather than ``id()``: a freed instance's id can be
    handed to the next allocation, which would make "these differ" pass for
    the wrong reason. Callers hold both, so neither can be collected.
    """
    if reset:
        reset_loop_bound_singletons()

    async def body() -> StorageService:
        return await StorageService.get_instance()

    return asyncio.run(body())


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_loop_bound_singletons()
    yield
    reset_loop_bound_singletons()


def test_sequential_tasks_get_a_service_built_on_their_own_loop():
    first = _one_task(reset=True)
    second = _one_task(reset=True)

    assert first is not second, (
        "the second task reused the first task's StorageService, whose client "
        "is bound to an event loop that asyncio.run has already closed"
    )


def test_without_the_reset_the_second_task_inherits_the_first_service():
    """The bug itself, pinned so the fix cannot be quietly removed."""
    first = _one_task(reset=False)
    second = _one_task(reset=False)

    assert first is second


def test_the_reset_clears_the_initialization_locks():
    """Cleared defensively, not out of necessity.

    Measured on 3.12: an uncontended ``asyncio.Lock`` binds lazily on first
    await and survives reuse on a new loop. They are dropped because a lock
    whose waiter queue referenced a dead loop is a far harder failure, and they
    guard construction that is being redone anyway.
    """

    async def seed() -> None:
        BaseService._initialization_locks["Seeded"] = asyncio.Lock()

    asyncio.run(seed())
    assert BaseService._initialization_locks

    reset_loop_bound_singletons()

    assert BaseService._initialization_locks == {}
    assert BaseService._instances == {}
    assert StorageService._instance is None


# --- The mechanism itself, measured rather than asserted ---------------------


def test_a_client_created_on_a_closed_loop_is_unusable():
    """The premise of this whole fix, demonstrated with a real client.

    Everything above tests object identity, which would pass even if the
    identity did not matter. This is why it matters: aiohttp is what the Azure
    SDK uses underneath, and ``_stored_key`` swallows exactly this exception.
    """
    import aiohttp

    holder = {}

    async def create() -> None:
        holder["session"] = aiohttp.ClientSession()

    asyncio.run(create())  # loop created, then closed

    async def use() -> str:
        try:
            await holder["session"].get(
                "http://127.0.0.1:9/", timeout=aiohttp.ClientTimeout(total=1)
            )
            return "no error"
        except RuntimeError as exc:
            return str(exc)
        except Exception as exc:  # noqa: BLE001 — any other failure is a miss
            return f"unexpected {type(exc).__name__}"

    assert asyncio.run(use()) == "Event loop is closed"
