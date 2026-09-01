"""
LLM API routes for the Open Hardware Manager.

This module provides API endpoints for LLM service monitoring, discovery,
and admin-managed provider credentials.
"""

from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from src.config.llm_config import CredentialManager, LLMProvider

from ...llm.credentials import (
    apply_stored_credential,
    ensure_stored_credentials_loaded,
)
from ...llm.service import LLMService
from ...models.auth import AuthenticatedUser
from ...services.storage_service import StorageService
from ...storage.llm_credential_store import (
    CredentialUnreadableError,
    LLMCredentialStore,
)
from ...utils.logging import get_logger
from ..constants.openapi import RESPONSES_400_401_500
from ..decorators import api_endpoint
from ..dependencies import require_admin_strict
from ..error_handlers import create_error_response
from ..models.base import SuccessResponse
from ..models.llm.request import LLMCredentialUpsert
from ..models.llm.response import (
    LLMCredentialListResponse,
    LLMCredentialStatus,
    LLMHealthResponse,
    LLMProvidersResponse,
    ProviderStatus,
)

# Set up logging
logger = get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/api/llm",
    tags=["llm"],
    responses=RESPONSES_400_401_500,
)


async def get_llm_service() -> LLMService:
    """Get LLM service instance, loading stored credentials if it has none.

    Startup loads them, but that attempt can fail — `add_provider` ends in a
    network call, and a worker starting before egress is ready gets nothing and
    never retries. Doing it here as well means the recovery happens when
    something actually needs an LLM, rather than requiring a restart or a
    re-save. It is a flag check once the load has succeeded.
    """
    service = await LLMService.get_instance()
    try:
        await ensure_stored_credentials_loaded(
            service, await get_llm_credential_store()
        )
    except Exception as e:  # noqa: BLE001 — an LLM is optional
        logger.warning("Could not load stored LLM credentials on demand: %s", e)
    return service


async def get_llm_credential_store() -> LLMCredentialStore:
    """Credential store backed by the process StorageService + CredentialManager."""
    storage = await StorageService.get_instance()
    return LLMCredentialStore(storage, CredentialManager())


def _parse_provider(name: str) -> LLMProvider:
    try:
        return LLMProvider(name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown LLM provider: {name}",
        ) from exc


@router.get(
    "/health",
    summary="LLM Service Health Check",
    description="""
    Check LLM service health and provider status.
    
    Returns information about:
    - Overall LLM service status
    - Status of each configured provider
    - Service metrics (requests, costs, etc.)
    """,
)
@api_endpoint(
    success_message="LLM service health check completed",
    include_metrics=False,  # Don't track metrics for health check
)
async def get_llm_health(
    http_request: Request = None,
    llm_service: LLMService = Depends(get_llm_service),
) -> LLMHealthResponse:
    """
    Get LLM service health and provider status.

    Args:
        http_request: HTTP request object for tracking
        llm_service: LLM service dependency

    Returns:
        LLMHealthResponse with health information
    """
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Get service metrics
        metrics = await llm_service.get_service_metrics()

        # Get provider status for all providers
        providers_status: Dict[str, ProviderStatus] = {}
        available_providers = await llm_service.get_available_providers()

        for provider_type in available_providers:
            try:
                status_info = await llm_service.get_provider_status(provider_type)
                providers_status[provider_type.value] = ProviderStatus(
                    name=provider_type.value,
                    type=provider_type.value,
                    status=status_info.get("status", "unknown"),
                    model=status_info.get("model"),
                    is_connected=status_info.get("is_connected"),
                    available_models=status_info.get("available_models"),
                    error=status_info.get("error"),
                )
            except Exception as e:
                logger.warning(
                    f"Error getting status for provider {provider_type}: {e}"
                )
                providers_status[provider_type.value] = ProviderStatus(
                    name=provider_type.value,
                    type=provider_type.value,
                    status="error",
                    error=str(e),
                )

        # Determine overall status
        overall_status = "healthy"
        if not providers_status:
            overall_status = "unavailable"
        elif any(
            p.status not in ["healthy", "active"] for p in providers_status.values()
        ):
            overall_status = "degraded"

        # Prepare metrics dict
        metrics_dict = {
            "total_requests": metrics.get("total_requests", 0),
            "total_cost": metrics.get("total_cost", 0.0),
            "average_cost_per_request": metrics.get("average_cost_per_request", 0.0),
            "active_provider": metrics.get("active_provider"),
            "available_providers": metrics.get("available_providers", []),
        }

        logger.info(
            f"LLM health check completed: {overall_status}",
            extra={
                "request_id": request_id,
                "status": overall_status,
                "providers_count": len(providers_status),
            },
        )

        return LLMHealthResponse(
            status="success",
            message="LLM service health check completed",
            timestamp=datetime.now(),
            request_id=request_id,
            health_status=overall_status,
            providers=providers_status,
            metrics=metrics_dict,
        )

    except Exception as e:
        logger.error(
            f"Error checking LLM health: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please check LLM service configuration and try again",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/providers",
    summary="List LLM Providers",
    description="""
    List all configured LLM providers and their status.
    
    Returns information about:
    - Available providers
    - Provider status and configuration
    - Default provider
    """,
)
@api_endpoint(
    success_message="Providers retrieved successfully",
    include_metrics=False,  # Don't track metrics for provider list
)
async def get_llm_providers(
    http_request: Request = None,
    llm_service: LLMService = Depends(get_llm_service),
) -> LLMProvidersResponse:
    """
    Get list of available LLM providers.

    Args:
        http_request: HTTP request object for tracking
        llm_service: LLM service dependency

    Returns:
        LLMProvidersResponse with provider information
    """
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Get available providers
        available_providers = await llm_service.get_available_providers()

        # Get provider status for each
        providers_list: List[ProviderStatus] = []
        for provider_type in available_providers:
            try:
                status_info = await llm_service.get_provider_status(provider_type)
                providers_list.append(
                    ProviderStatus(
                        name=provider_type.value,
                        type=provider_type.value,
                        status=status_info.get("status", "unknown"),
                        model=status_info.get("model"),
                        is_connected=status_info.get("is_connected"),
                        available_models=status_info.get("available_models"),
                        error=status_info.get("error"),
                    )
                )
            except Exception as e:
                logger.warning(
                    f"Error getting status for provider {provider_type}: {e}"
                )
                providers_list.append(
                    ProviderStatus(
                        name=provider_type.value,
                        type=provider_type.value,
                        status="error",
                        error=str(e),
                    )
                )

        # Get default provider
        metrics = await llm_service.get_service_metrics()
        default_provider = metrics.get("active_provider")

        # Get available provider names
        available_provider_names = [p.value for p in available_providers]

        logger.info(
            f"Providers retrieved: {len(providers_list)} providers",
            extra={
                "request_id": request_id,
                "providers_count": len(providers_list),
                "default_provider": default_provider,
            },
        )

        return LLMProvidersResponse(
            status="success",
            message="Providers retrieved successfully",
            timestamp=datetime.now(),
            request_id=request_id,
            providers=providers_list,
            default_provider=default_provider,
            available_providers=available_provider_names,
        )

    except Exception as e:
        logger.error(
            f"Error retrieving providers: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please check LLM service configuration and try again",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/credentials",
    response_model=LLMCredentialListResponse,
    summary="List stored LLM credentials",
)
async def list_llm_credentials(
    _admin: AuthenticatedUser = Depends(require_admin_strict),
    store: LLMCredentialStore = Depends(get_llm_credential_store),
) -> LLMCredentialListResponse:
    """Return masked status for all stored provider credentials."""
    statuses = await store.list_status()
    return LLMCredentialListResponse(
        status="success",
        message="Credentials retrieved",
        timestamp=datetime.now(),
        credentials=[LLMCredentialStatus(**s) for s in statuses],
    )


@router.put(
    "/credentials/{provider}",
    response_model=LLMCredentialStatus,
    summary="Set or rotate an LLM provider credential",
)
async def upsert_llm_credential(
    payload: LLMCredentialUpsert,
    provider: str = Path(..., description="Provider name, e.g. anthropic"),
    _admin: AuthenticatedUser = Depends(require_admin_strict),
    store: LLMCredentialStore = Depends(get_llm_credential_store),
    llm_service: LLMService = Depends(get_llm_service),
) -> LLMCredentialStatus:
    """Encrypt and persist a provider API key; optionally hot-swap into the service."""
    provider_enum = _parse_provider(provider)
    try:
        await store.save(provider_enum, payload.api_key, model=payload.model)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e

    if payload.activate:
        applied = await apply_stored_credential(
            llm_service, store, provider_enum, model=payload.model
        )
        if not applied:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Credential stored but failed to activate in LLM service",
            )
        # Record the choice as well as applying it. Hot-swapping alone lasted
        # only as long as this process: another worker, or this one after a
        # restart, had no idea which provider had been chosen.
        await store.set_active(provider_enum)

    statuses = await store.list_status()
    for status_row in statuses:
        if status_row["provider"] == provider_enum.value:
            return LLMCredentialStatus(**status_row)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Credential stored but status could not be read back",
    )


@router.put(
    "/active/{provider}",
    response_model=LLMCredentialStatus,
    summary="Choose which stored provider the node uses",
)
async def set_active_llm_provider(
    provider: str = Path(..., description="Provider name, e.g. anthropic"),
    _admin: AuthenticatedUser = Depends(require_admin_strict),
    store: LLMCredentialStore = Depends(get_llm_credential_store),
    llm_service: LLMService = Depends(get_llm_service),
) -> LLMCredentialStatus:
    """Make a stored provider the active one, without re-entering its key.

    The choice is recorded in the store as well as applied here, so it survives
    a restart and is the same answer in every worker. Activation used to be
    process-local: which provider a node used depended on which worker had last
    handled a save.
    """
    provider_enum = _parse_provider(provider)

    applied = await apply_stored_credential(llm_service, store, provider_enum)
    if not applied:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No stored credential for {provider_enum.value}. Save one "
                "before making it active."
            ),
        )

    await store.set_active(provider_enum)

    for status_row in await store.list_status():
        if status_row["provider"] == provider_enum.value:
            return LLMCredentialStatus(**status_row)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Provider activated but status could not be read back",
    )


@router.delete(
    "/credentials/{provider}",
    response_model=SuccessResponse,
    summary="Delete a stored LLM provider credential",
)
async def delete_llm_credential(
    provider: str = Path(..., description="Provider name, e.g. anthropic"),
    _admin: AuthenticatedUser = Depends(require_admin_strict),
    store: LLMCredentialStore = Depends(get_llm_credential_store),
    llm_service: LLMService = Depends(get_llm_service),
) -> SuccessResponse:
    """Remove a stored credential and disconnect it from the running service."""
    from ...llm.providers.base import LLMProviderType

    provider_enum = _parse_provider(provider)
    deleted = await store.delete(provider_enum)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stored credential for provider {provider}",
        )
    try:
        await llm_service.remove_provider(LLMProviderType(provider_enum.value))
    except Exception:
        logger.debug("Provider %s was not active in LLM service", provider)
    return SuccessResponse(success=True, message=f"Credential for {provider} deleted")


@router.post(
    "/credentials/{provider}/test",
    response_model=SuccessResponse,
    summary="Test a stored LLM provider credential",
)
async def test_llm_credential(
    provider: str = Path(..., description="Provider name, e.g. anthropic"),
    _admin: AuthenticatedUser = Depends(require_admin_strict),
    store: LLMCredentialStore = Depends(get_llm_credential_store),
    llm_service: LLMService = Depends(get_llm_service),
) -> SuccessResponse:
    """Run health_check against the provider using the stored credential."""
    from ...llm.providers.base import LLMProviderType

    provider_enum = _parse_provider(provider)
    try:
        stored = await store.load(provider_enum)
    except CredentialUnreadableError as exc:
        # 409, not 500: the request is well-formed and the credential is
        # there. The node's encryption material changed under it, and only
        # re-saving the key fixes that — so say so instead of raising.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stored credential for provider {provider}",
        )

    provider_type = LLMProviderType(provider_enum.value)
    await apply_stored_credential(llm_service, store, provider_enum, set_active=False)
    provider_instance = llm_service._providers.get(provider_type)
    if provider_instance is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not initialize provider for health check",
        )
    healthy = await provider_instance.health_check()
    if not healthy:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider {provider} health check failed",
        )
    return SuccessResponse(
        success=True, message=f"Provider {provider} health check passed"
    )
