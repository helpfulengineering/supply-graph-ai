"""Celery tasks for OKH generation."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

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

    def on_progress(stage: str, fraction: float, message: Optional[str] = None) -> None:
        self.update_state(
            state="PROGRESS",
            meta={
                "stage": stage,
                "fraction": fraction,
                "message": message,
                "url": url,
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
    return payload
