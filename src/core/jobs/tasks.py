"""Celery tasks: OKH generation, and storage migration (#381)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.generation.progress import ProgressCallback
from src.core.jobs.celery_app import celery_app


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


async def _run_storage_migration(
    *,
    provider: str,
    bucket: str,
    region: Optional[str],
    endpoint_url: Optional[str],
    credentials: Dict[str, str],
    progress: Optional[Any] = None,
) -> Dict[str, Any]:
    """Copy to the new backend, verify, then switch — in a worker process."""
    from src.core.services.storage_reconfigure import (
        build_candidate,
        migrate_and_switch,
    )
    from src.core.services.storage_service import StorageService

    service = await StorageService.get_instance()
    candidate = build_candidate(
        provider=provider,
        bucket=bucket,
        region=region,
        endpoint_url=endpoint_url,
        credentials=credentials,
    )
    return await migrate_and_switch(service, candidate, progress=progress)


@celery_app.task(bind=True, name="ohm.migrate_storage")
def migrate_storage_task(
    self,
    provider: str,
    bucket: str,
    *,
    region: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    credentials: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Migrate storage to a new backend (runs in the worker).

    A migration on a populated backend takes far longer than an ingress
    timeout allows, and a caller that cannot observe it cannot tell a slow copy
    from a stalled one. So it runs here and publishes the same cumulative event
    log the generation timeline uses — the substrate from #375, rather than a
    second progress mechanism that would need its own store, expiry and
    security.
    """
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
                "bucket": bucket,
                "events": events,
            },
        )

    result = asyncio.run(
        _run_storage_migration(
            provider=provider,
            bucket=bucket,
            region=region,
            endpoint_url=endpoint_url,
            credentials=credentials or {},
            progress=on_progress,
        )
    )
    payload = dict(result)
    payload["job_id"] = self.request.id
    # Celery replaces meta with the return value on success, so the log has to
    # travel in the result or it dies exactly when the run completes.
    payload["events"] = events
    return payload
