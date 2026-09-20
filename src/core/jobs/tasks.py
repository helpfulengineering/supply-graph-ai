"""Celery tasks: OKH generation.

There used to be a storage-migration task here. It never worked (it built a
fresh, unconfigured StorageService per task, so it stopped with "There is no
current storage to migrate from"), carried the destination's credentials through
the broker as cleartext JSON, and nothing called it; it was retired in #543. No
task in this package reads or writes the object store.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.generation.progress import ProgressCallback
from src.core.jobs.celery_app import celery_app


def reset_loop_bound_singletons() -> None:
    """Drop process-wide services so the next task rebuilds them on its own loop.

    Every task body calls ``asyncio.run``, which creates an event loop and
    closes it on return. The services are process-wide singletons that outlive
    that loop, and the clients they hold — aiohttp sessions and connectors
    underneath the Azure SDK — are bound to the loop that created them. Reused
    on the next task, every call against them raises.

    ``OKHService._initialize_dependencies`` only configures storage when it is
    not already configured, so the second task inherits a service that claims to
    be ready and cannot read anything. The read that failed was the LLM
    credential lookup, and ``_stored_key`` swallows its exception at DEBUG — so
    the node reported "no provider is configured" while holding a valid,
    readable key.

    The signature in production was exact: the first generation after a worker
    start used the LLM, and every generation after it did not.

    ``_initialization_locks`` is cleared alongside them, defensively rather than
    out of necessity: measured on Python 3.12, an uncontended ``asyncio.Lock`` binds
    lazily on first await and is reused across loops without error. It is
    dropped because a lock whose waiter queue referenced a dead loop would be a
    much harder failure, and the locks guard construction that is being redone
    anyway.

    Safe because a prefork worker runs one task at a time per child process. A
    threaded or gevent pool would need a different approach — there, concurrent
    tasks share the process and one clearing the registry would pull services
    out from under another.
    """
    from src.core.services.base import BaseService
    from src.core.services.storage_service import StorageService

    BaseService._instances.clear()
    BaseService._initialization_locks.clear()
    StorageService._instance = None


async def _run_generate_from_url(
    *,
    url: str,
    skip_review: bool = False,
    verbose: bool = False,
    clone: bool = True,
    save_clone: Optional[str] = None,
    no_llm: bool = False,
    progress: Optional[ProgressCallback] = None,
) -> Dict[str, Any]:
    """Call OKHService.generate_from_url (async) from a worker process."""
    from src.core.services.okh_service import OKHService

    service = await OKHService.get_instance()
    return await service.generate_from_url(
        url=url,
        skip_review=skip_review,
        verbose=verbose,
        clone=clone,
        save_clone=save_clone,
        no_llm=no_llm,
        progress=progress,
    )


@celery_app.task(bind=True, name="ohm.generate_from_url")
def generate_from_url_task(
    self,
    url: str,
    *,
    skip_review: bool = False,
    verbose: bool = False,
    clone: bool = True,
    save_clone: Optional[str] = None,
    no_llm: bool = False,
) -> Dict[str, Any]:
    """Generate an OKH manifest from a repository URL (runs in the worker)."""

    # Republished whole on every update, not appended to remotely.
    #
    # `update_state` OVERWRITES meta, so a client polling the latest event
    # samples the timeline rather than receiving it: a stage shorter than the
    # poll interval is never observed. Publishing the cumulative list makes a
    # poll at any interval see everything so far, with no second store to keep,
    # expire and secure. Nine stages make that cheap; it would not suit a
    # high-frequency feed.
    events: List[Dict[str, Any]] = []

    def on_progress(stage: str, fraction: float, message: Optional[str] = None) -> None:
        events.append(
            {
                "seq": len(events),
                "stage": stage,
                "fraction": fraction,
                "message": message,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.update_state(
            state="PROGRESS",
            meta={
                "stage": stage,
                "fraction": fraction,
                "message": message,
                "url": url,
                "events": events,
            },
        )

    reset_loop_bound_singletons()
    result = asyncio.run(
        _run_generate_from_url(
            url=url,
            skip_review=skip_review,
            verbose=verbose,
            clone=clone,
            save_clone=save_clone,
            no_llm=no_llm,
            progress=on_progress,
        )
    )
    payload = dict(result)
    payload["url"] = url
    payload["job_id"] = self.request.id
    # Celery replaces meta with the return value on success, so the log has to
    # travel in the result or the record dies exactly when the run completes —
    # which is when it becomes worth reading.
    payload["events"] = events
    return payload
