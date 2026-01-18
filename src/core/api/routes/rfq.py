import logging
import hashlib
import hmac
import json
from uuid import UUID
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel

from src.core.api.decorators import api_endpoint
from src.core.models.rfq import RFQ, Quote, RFQStatus
from src.core.services.rfq_service import RFQService
from src.core.integration.manager import IntegrationManager
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["rfq"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"},
    },
)


async def get_rfq_service() -> RFQService:
    service = RFQService()
    await service.initialize()
    return service


async def get_integration_manager() -> IntegrationManager:
    manager = IntegrationManager.get_instance()
    if not manager._initialized:
        await manager.initialize()
    return manager


@router.post(
    "/",
    summary="Create a new RFQ",
    description="Create a new Request for Quote and broadcast it to connected supply chain providers.",
    response_model=Dict[str, Any]
)
@api_endpoint()
async def create_rfq(
    rfq: RFQ,
    service: RFQService = Depends(get_rfq_service)
):
    try:
        created_rfq = await service.create_rfq(rfq)
        return created_rfq.to_dict()
    except Exception as e:
        logger.error(f"Error creating RFQ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create RFQ: {str(e)}"
        )


@router.get(
    "/{rfq_id}",
    summary="Get RFQ details",
    description="Retrieve details of an existing RFQ.",
    response_model=Dict[str, Any]
)
@api_endpoint()
async def get_rfq(
    rfq_id: UUID,
    service: RFQService = Depends(get_rfq_service)
):
    rfq = await service.get_rfq(rfq_id)
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ with ID {rfq_id} not found"
        )
    return rfq.to_dict()


@router.get(
    "/{rfq_id}/quotes",
    summary="Get quotes for an RFQ",
    description="Retrieve all quotes received for a specific RFQ.",
    response_model=list
)
@api_endpoint()
async def list_quotes(
    rfq_id: UUID,
    service: RFQService = Depends(get_rfq_service)
):
    quotes = await service.get_quotes_for_rfq(rfq_id)
    return [quote.to_dict() for quote in quotes]


# Webhook Verification Dependency
async def verify_signature(request: Request, x_ohm_signature: Optional[str] = Header(None)):
    """
    Verify HMAC signature of incoming webhooks.
    Enforces that a valid signature is present.
    """
    if not x_ohm_signature:
         raise HTTPException(
             status_code=status.HTTP_401_UNAUTHORIZED,
             detail="Missing webhook signature"
         )

    body = await request.body()

    manager = IntegrationManager.get_instance()
    if not manager._initialized:
        await manager.initialize()

    # Iterate over supply chain providers to find a matching signature
    valid = False
    for provider in manager.providers.values():
        if getattr(provider, "webhook_secret", None):
             # Re-compute signature
             secret_bytes = provider.webhook_secret.encode('utf-8')
             computed = hmac.new(secret_bytes, body, hashlib.sha256).hexdigest()
             if hmac.compare_digest(computed, x_ohm_signature):
                 valid = True
                 break

    if not valid:
         raise HTTPException(
             status_code=status.HTTP_401_UNAUTHORIZED,
             detail="Invalid webhook signature"
         )


@router.post(
    "/webhooks/quotes",
    summary="Receive new Quote (Webhook)",
    description="Endpoint for external providers to push new quotes. Requires X-OHM-Signature header.",
    response_model=Dict[str, Any]
)
async def receive_quote(
    quote: Quote,
    request: Request,
    service: RFQService = Depends(get_rfq_service),
    _ = Depends(verify_signature)
):
    try:
        saved_quote = await service.create_quote(quote)
        return {"success": True, "quote_id": str(saved_quote.id)}
    except Exception as e:
        logger.error(f"Error processing quote webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class StatusUpdate(BaseModel):
    rfq_id: UUID
    new_status: str
    metadata: Dict[str, Any] = {}


@router.post(
    "/webhooks/status",
    summary="Receive RFQ Status Update (Webhook)",
    description="Endpoint for external providers to update RFQ status. Requires X-OHM-Signature header.",
    response_model=Dict[str, Any]
)
async def update_status(
    update: StatusUpdate,
    request: Request,
    service: RFQService = Depends(get_rfq_service),
    _ = Depends(verify_signature)
):
    try:
        # Validate status enum
        try:
            status_enum = RFQStatus(update.new_status)
        except ValueError:
             raise HTTPException(status_code=400, detail=f"Invalid status: {update.new_status}")

        result = await service.update_rfq_status(update.rfq_id, status_enum)
        if not result:
             raise HTTPException(status_code=404, detail="RFQ not found")

        return {"success": True, "rfq_id": str(update.rfq_id), "status": update.new_status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing status webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
