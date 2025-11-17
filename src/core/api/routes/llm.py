"""
LLM API routes for the Open Matching Engine.

This module provides API endpoints for LLM service monitoring and discovery.
"""

from fastapi import APIRouter, Depends, Request, status, HTTPException
from typing import Dict, Any, List
from datetime import datetime

from ..decorators import api_endpoint
from ..error_handlers import create_error_response, create_success_response
from ..models.llm.response import LLMHealthResponse, LLMProvidersResponse, ProviderStatus
from ...llm.service import LLMService
from ...llm.providers.base import LLMProviderType
from ...utils.logging import get_logger

# Set up logging
logger = get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/api/llm",
    tags=["llm"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal Server Error"}
    }
)


async def get_llm_service() -> LLMService:
    """Get LLM service instance."""
    return await LLMService.get_instance()


@router.get(
    "/health",
    summary="LLM Service Health Check",
    description="""
    Check LLM service health and provider status.
    
    Returns information about:
    - Overall LLM service status
    - Status of each configured provider
    - Service metrics (requests, costs, etc.)
    """
)
@api_endpoint(
    success_message="LLM service health check completed",
    include_metrics=False  # Don't track metrics for health check
)
async def get_llm_health(
    http_request: Request = None,
    llm_service: LLMService = Depends(get_llm_service)
) -> LLMHealthResponse:
    """
    Get LLM service health and provider status.
    
    Args:
        http_request: HTTP request object for tracking
        llm_service: LLM service dependency
        
    Returns:
        LLMHealthResponse with health information
    """
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
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
                    error=status_info.get("error")
                )
            except Exception as e:
                logger.warning(f"Error getting status for provider {provider_type}: {e}")
                providers_status[provider_type.value] = ProviderStatus(
                    name=provider_type.value,
                    type=provider_type.value,
                    status="error",
                    error=str(e)
                )
        
        # Determine overall status
        overall_status = "healthy"
        if not providers_status:
            overall_status = "unavailable"
        elif any(p.status not in ["healthy", "active"] for p in providers_status.values()):
            overall_status = "degraded"
        
        # Prepare metrics dict
        metrics_dict = {
            "total_requests": metrics.get("total_requests", 0),
            "total_cost": metrics.get("total_cost", 0.0),
            "average_cost_per_request": metrics.get("average_cost_per_request", 0.0),
            "active_provider": metrics.get("active_provider"),
            "available_providers": metrics.get("available_providers", [])
        }
        
        logger.info(
            f"LLM health check completed: {overall_status}",
            extra={
                "request_id": request_id,
                "status": overall_status,
                "providers_count": len(providers_status)
            }
        )
        
        return LLMHealthResponse(
            status="success",
            message="LLM service health check completed",
            timestamp=datetime.now(),
            request_id=request_id,
            health_status=overall_status,
            providers=providers_status,
            metrics=metrics_dict
        )
        
    except Exception as e:
        logger.error(
            f"Error checking LLM health: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please check LLM service configuration and try again"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
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
    """
)
@api_endpoint(
    success_message="Providers retrieved successfully",
    include_metrics=False  # Don't track metrics for provider list
)
async def get_llm_providers(
    http_request: Request = None,
    llm_service: LLMService = Depends(get_llm_service)
) -> LLMProvidersResponse:
    """
    Get list of available LLM providers.
    
    Args:
        http_request: HTTP request object for tracking
        llm_service: LLM service dependency
        
    Returns:
        LLMProvidersResponse with provider information
    """
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Get available providers
        available_providers = await llm_service.get_available_providers()
        
        # Get provider status for each
        providers_list: List[ProviderStatus] = []
        for provider_type in available_providers:
            try:
                status_info = await llm_service.get_provider_status(provider_type)
                providers_list.append(ProviderStatus(
                    name=provider_type.value,
                    type=provider_type.value,
                    status=status_info.get("status", "unknown"),
                    model=status_info.get("model"),
                    is_connected=status_info.get("is_connected"),
                    available_models=status_info.get("available_models"),
                    error=status_info.get("error")
                ))
            except Exception as e:
                logger.warning(f"Error getting status for provider {provider_type}: {e}")
                providers_list.append(ProviderStatus(
                    name=provider_type.value,
                    type=provider_type.value,
                    status="error",
                    error=str(e)
                ))
        
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
                "default_provider": default_provider
            }
        )
        
        return LLMProvidersResponse(
            status="success",
            message="Providers retrieved successfully",
            timestamp=datetime.now(),
            request_id=request_id,
            providers=providers_list,
            default_provider=default_provider,
            available_providers=available_provider_names
        )
        
    except Exception as e:
        logger.error(
            f"Error retrieving providers: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please check LLM service configuration and try again"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )

