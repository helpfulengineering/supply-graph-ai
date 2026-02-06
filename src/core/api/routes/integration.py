from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from ...integration.manager import IntegrationManager
from ...integration.models.base import ProviderStatus, IntegrationCategory
from ..decorators import api_endpoint

router = APIRouter(
    tags=["integration"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"},
    },
)

async def get_integration_manager() -> IntegrationManager:
    manager = IntegrationManager.get_instance()
    if not manager._initialized:
        await manager.initialize()
    return manager

@router.get(
    "/providers",
    summary="List all integration providers",
    description="List all configured and registered external integration providers."
)
@api_endpoint()
async def list_providers(
    manager: IntegrationManager = Depends(get_integration_manager)
):
    providers_info = []
    for name, provider in manager.providers.items():
        providers_info.append({
            "name": name,
            "type": provider.provider_type,
            "category": provider.category,
            "connected": provider.is_connected,
            "status": provider.get_status()
        })
    return providers_info

@router.get(
    "/status",
    summary="Get status of all integration providers",
    description="Check health and connection status of all providers."
)
@api_endpoint()
async def get_providers_status(
    manager: IntegrationManager = Depends(get_integration_manager)
):
    status_report = {}
    for name, provider in manager.providers.items():
        is_healthy = await provider.check_health()
        status_report[name] = {
            "status": "healthy" if is_healthy else "unhealthy",
            "connected": provider.is_connected,
            "category": provider.category
        }
    return status_report
