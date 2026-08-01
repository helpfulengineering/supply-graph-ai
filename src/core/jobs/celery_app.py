"""Celery application for OHM background jobs."""

from __future__ import annotations

from celery import Celery

from src.config.schema import get_settings

# Result records (and large manifests) expire so Redis does not grow unbounded.
DEFAULT_RESULT_EXPIRES_SECONDS = 24 * 60 * 60


def _broker_url() -> str:
    return get_settings().job_broker_url or "redis://localhost:6379/1"


def _result_backend() -> str:
    return get_settings().job_result_backend or _broker_url()


celery_app = Celery(
    "ohm",
    broker=_broker_url(),
    backend=_result_backend(),
    include=["src.core.jobs.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=DEFAULT_RESULT_EXPIRES_SECONDS,
    timezone="UTC",
    enable_utc=True,
    # Prefork isolates blocking spaCy work from the API process.
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
