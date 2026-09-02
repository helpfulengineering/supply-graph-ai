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


def test_the_reset_clears_loop_bound_initialization_locks():
    """asyncio.Lock binds to a loop too, so a stale one deadlocks or errors."""

    async def seed() -> None:
        BaseService._initialization_locks["Seeded"] = asyncio.Lock()

    asyncio.run(seed())
    assert BaseService._initialization_locks

    reset_loop_bound_singletons()

    assert BaseService._initialization_locks == {}
    assert BaseService._instances == {}
    assert StorageService._instance is None
