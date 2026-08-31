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
    StorageReconfigureError,
    current_config,
    reconfigure_storage,
)
from ...services.storage_service import StorageService
from ..dependencies import require_admin_strict
from ..models.storage.config import (
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
) -> StorageConfigureResponse:
    """Validate the new backend, then commit to it.

    Existing data stays where it is; this changes which backend the instance
    reads and writes. A rejected configuration leaves the instance serving
    exactly as it was — the candidate is proved with a real write/read round
    trip before anything is persisted or swapped.
    """
    try:
        result = await reconfigure_storage(
            service,
            provider=payload.provider,
            bucket=payload.bucket,
            region=payload.region,
            endpoint_url=payload.endpoint_url,
            credentials=payload.credentials,
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
