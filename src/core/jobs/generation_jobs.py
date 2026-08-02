"""Enqueue and inspect OKH generate-from-url Celery jobs."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from celery.result import AsyncResult

from src.config.schema import get_settings
from src.core.jobs.celery_app import celery_app
from src.core.jobs.tasks import generate_from_url_task


def jobs_available() -> bool:
    settings = get_settings()
    return bool(settings.jobs_enabled and settings.job_broker_url)


def count_inflight_jobs() -> Dict[str, int]:
    """Return active + reserved (+ scheduled) task counts across workers."""
    inspector = celery_app.control.inspect(timeout=1.0)
    active = reserved = scheduled = 0
    try:
        for mapping in (inspector.active() or {}).values():
            active += len(mapping or [])
        for mapping in (inspector.reserved() or {}).values():
            reserved += len(mapping or [])
        for mapping in (inspector.scheduled() or {}).values():
            scheduled += len(mapping or [])
    except Exception:
        # Broker unreachable — treat as unknown (0) so submit can still proceed
        # or fail elsewhere; callers use settings caps only when inspect works.
        return {"active": 0, "queued": 0, "total": 0}
    queued = reserved + scheduled
    return {"active": active, "queued": queued, "total": active + queued}


def enforce_job_capacity(additional: int = 1) -> None:
    """Raise ValueError if concurrent/queued caps would be exceeded."""
    settings = get_settings()
    counts = count_inflight_jobs()
    if counts["active"] + additional > settings.generate_from_url_max_concurrent:
        raise ValueError(
            f"Too many concurrent generation jobs "
            f"({counts['active']} active; max "
            f"{settings.generate_from_url_max_concurrent})"
        )
    if counts["queued"] + additional > settings.generate_from_url_max_queued:
        raise ValueError(
            f"Too many queued generation jobs "
            f"({counts['queued']} queued; max "
            f"{settings.generate_from_url_max_queued})"
        )


def enqueue_generate_jobs(
    urls: List[str],
    *,
    skip_review: bool = True,
    verbose: bool = False,
    clone: bool = True,
    save_clone: Optional[str] = None,
    no_llm: bool = False,
) -> Dict[str, Any]:
    """Create one Celery job per URL. Returns batch_id and job descriptors."""
    if not urls:
        raise ValueError("At least one URL is required")
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_urls: List[str] = []
    for url in urls:
        url = url.strip()
        if not url or url in seen:
            continue
        seen.add(url)
        unique_urls.append(url)
    if not unique_urls:
        raise ValueError("At least one URL is required")

    enforce_job_capacity(additional=len(unique_urls))

    batch_id = str(uuid.uuid4())
    jobs: List[Dict[str, str]] = []
    for url in unique_urls:
        async_result = generate_from_url_task.delay(
            url=url,
            skip_review=skip_review,
            verbose=verbose,
            clone=clone,
            save_clone=save_clone,
            no_llm=no_llm,
        )
        jobs.append({"job_id": async_result.id, "url": url})
    return {"batch_id": batch_id, "jobs": jobs}


def get_job_status(job_id: str) -> Dict[str, Any]:
    """Map a Celery AsyncResult into the public job status payload."""
    result = AsyncResult(job_id, app=celery_app)
    state = result.state or "PENDING"
    meta = result.info if isinstance(result.info, dict) else {}
    payload: Dict[str, Any] = {
        "job_id": job_id,
        "state": state,
        "stage": meta.get("stage"),
        "fraction": meta.get("fraction"),
        "message": meta.get("message"),
        "url": meta.get("url"),
        "error": None,
        "manifest": None,
        "quality_report": None,
    }
    if state == "SUCCESS" and isinstance(result.result, dict):
        payload["url"] = result.result.get("url") or payload["url"]
        payload["message"] = result.result.get("message") or payload["message"]
        payload["manifest"] = result.result.get("manifest")
        payload["quality_report"] = result.result.get("quality_report")
        payload["fraction"] = 1.0
    elif state == "FAILURE":
        payload["error"] = str(result.result) if result.result else "Job failed"
    return payload
