"""Storage configuration, changeable while the instance is running (#377).

Storage was the last setting with no runtime path: provider and credentials
were read from the environment at container start and could not be changed
without a redeploy. That is the gap that makes a hands-off installer
impossible, because installation and configuration are separate — anything
needing configuration has to be reachable once the instance is already up.

Both endpoints require ``require_admin_strict``: admin that the
``ENVIRONMENT != production`` write-auth relaxation cannot bypass, the same
treatment LLM provider credentials get. An endpoint that can repoint an
instance's storage is not something to leave open in a development deployment.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ...models.auth import AuthenticatedUser
from ...services.storage_config_store import StorageConfigStoreError
from ...services.storage_reconfigure import (
    MODE_ABANDON,
    MODE_ABANDON_AND_WIPE,
    MODE_MIGRATE,
    StorageReconfigureError,
    build_candidate,
    current_config,
    reconfigure_storage,
    switch_and_wipe,
)
from ...services.storage_service import StorageService
from ..dependencies import require_admin_strict
from ..models.storage.config import (
    MigrationEvent,
    MigrationJobData,
    MigrationJobResponse,
    MigrationStatusData,
    MigrationStatusResponse,
    StorageConfigData,
    StorageConfigResponse,
    StorageConfigureData,
    StorageConfigureRequest,
    StorageConfigureResponse,
    StorageConfigView,
    StorageFingerprint,
)

router = APIRouter()


async def get_storage_service() -> StorageService:
    return await StorageService.get_instance()


@router.get(
    "/config",
    response_model=StorageConfigResponse,
    summary="Read the current storage configuration",
)
async def read_storage_config(
    _admin: AuthenticatedUser = Depends(require_admin_strict),
    service: StorageService = Depends(get_storage_service),
) -> StorageConfigResponse:
    """Report the configuration and what the app is actually connected to.

    The two can disagree — the configuration is what was asked for, the
    fingerprint is what answered — which is the first thing worth knowing when
    storage is misbehaving. No credential value is returned, only which names
    are set.
    """
    view = await current_config(service)
    fingerprint = await service.get_config_fingerprint()

    return StorageConfigResponse(
        status="success",
        message="Storage configuration retrieved",
        timestamp=datetime.now(),
        data=StorageConfigView(
            config=StorageConfigData(**view.to_dict()),
            fingerprint=StorageFingerprint(**fingerprint),
        ),
    )


@router.post(
    "/config",
    response_model=StorageConfigureResponse,
    summary="Switch to a different storage backend",
)
async def configure_storage(
    payload: StorageConfigureRequest,
    _admin: AuthenticatedUser = Depends(require_admin_strict),
    service: StorageService = Depends(get_storage_service),
):
    """Validate the new backend, then commit to it.

    Existing data stays where it is; this changes which backend the instance
    reads and writes. A rejected configuration leaves the instance serving
    exactly as it was — the candidate is proved with a real write/read round
    trip before anything is persisted or swapped.

    ``mode`` decides what happens to the data already in storage. ``migrate``
    returns a job rather than a result: a copy of a populated backend runs far
    longer than an ingress timeout allows, and a caller that cannot observe it
    cannot tell a slow copy from a stalled one.
    """
    # None means abandon — see the field's note on why it is not defaulted.
    mode = payload.mode or MODE_ABANDON

    if mode == MODE_MIGRATE:
        return await _start_migration(payload)

    try:
        candidate = build_candidate(
            provider=payload.provider,
            bucket=payload.bucket,
            region=payload.region,
            endpoint_url=payload.endpoint_url,
            credentials=payload.credentials,
        )

        if mode == MODE_ABANDON_AND_WIPE:
            if not payload.wipe_confirm:
                raise StorageReconfigureError(
                    "abandon_and_wipe requires wipe_confirm naming the exact "
                    "bucket to erase. Nothing was changed."
                )
            result = await switch_and_wipe(
                service,
                candidate,
                wipe_confirm=payload.wipe_confirm,
                dry_run=bool(payload.dry_run),
            )
        else:
            result = await reconfigure_storage(
                service,
                provider=candidate.provider,
                bucket=candidate.bucket_name,
                region=candidate.region,
                endpoint_url=candidate.endpoint_url,
                credentials=candidate.credentials,
            )
    except StorageReconfigureError as exc:
        # 400: the caller gave a configuration that does not work. The
        # instance is untouched, which the message says so an operator is not
        # left wondering whether they have just broken their node.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{exc} The instance is still serving from its previous "
                "configuration."
            ),
        ) from exc
    except StorageConfigStoreError as exc:
        # The backend worked; persisting it did not. Distinct from the above
        # because the fix is different — an unwritable volume or missing
        # encryption material, not a bad credential.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return StorageConfigureResponse(
        status="success",
        message=f"Storage reconfigured to {result['provider']}",
        timestamp=datetime.now(),
        data=StorageConfigureData(**result),
    )


async def _start_migration(
    payload: StorageConfigureRequest,
) -> MigrationJobResponse:
    """Enqueue a migration and hand back somewhere to watch it.

    Validation of the request shape happens here, synchronously, so a caller
    with a misspelled credential learns immediately rather than from a job that
    fails a minute later. Whether the *destination* works is the job's first
    step — proving it needs a network round trip that does not belong in a
    request handler.
    """
    from ...jobs import generation_jobs
    from ...jobs.tasks import migrate_storage_task

    try:
        build_candidate(
            provider=payload.provider,
            bucket=payload.bucket,
            region=payload.region,
            endpoint_url=payload.endpoint_url,
            credentials=payload.credentials,
        )
    except StorageReconfigureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    if not generation_jobs.jobs_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Migration runs as a background job, and jobs are not enabled "
                "on this instance. Set JOBS_ENABLED=true with a broker "
                "configured, or switch with mode=abandon and move the data "
                "yourself. Nothing was changed."
            ),
        )

    task = migrate_storage_task.delay(
        payload.provider,
        payload.bucket,
        region=payload.region,
        endpoint_url=payload.endpoint_url,
        credentials=payload.credentials,
    )

    return MigrationJobResponse(
        status="success",
        message="Migration started. The instance keeps serving from its "
        "current storage until the copy verifies.",
        timestamp=datetime.now(),
        data=MigrationJobData(
            job_id=task.id,
            state="PENDING",
            events_url=f"/v1/api/storage/migration/{task.id}",
        ),
    )


@router.get(
    "/migration/{job_id}",
    response_model=MigrationStatusResponse,
    summary="Progress of a running storage migration",
)
async def migration_status(
    job_id: str,
    since: int = 0,
    _admin: AuthenticatedUser = Depends(require_admin_strict),
) -> MigrationStatusResponse:
    """Cumulative progress of a migration job.

    ``since`` is an offset, not a timestamp: pass back ``next_cursor`` and only
    new events arrive. The whole log is republished on every update, so a
    caller polling at any interval sees every stage rather than sampling the
    timeline.
    """
    from ...jobs import generation_jobs

    if not generation_jobs.jobs_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background jobs are not enabled on this instance.",
        )

    payload = generation_jobs.get_job_events(job_id, since=since)
    result = payload.get("result")

    return MigrationStatusResponse(
        status="success",
        message=f"Migration {payload['state'].lower()}",
        timestamp=datetime.now(),
        data=MigrationStatusData(
            job_id=payload["job_id"],
            state=payload["state"],
            events=[MigrationEvent(**e) for e in payload["events"]],
            next_cursor=payload["next_cursor"],
            result=result if isinstance(result, dict) else None,
        ),
    )
