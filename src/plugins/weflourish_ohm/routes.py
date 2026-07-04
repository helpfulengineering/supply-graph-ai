from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from src.core.utils.logging import get_logger
from .service import WeFlourishRFQService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/rfq", tags=["weflourish"])

class BidCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ohm_id: str
    project_name: str
    description: str
    project_link: Optional[str] = None
    required_capabilities: List[str] = []
    metadata: Dict[str, Any] = {}

@router.post("/webhooks/weflourish", status_code=status.HTTP_200_OK)
async def weflourish_webhook(
    request: Request,
    x_weflourish_signature: str = Header(None),
    rfq_service: WeFlourishRFQService = Depends(WeFlourishRFQService.get_instance),
):
    """
    Inbound webhook receiver for WeFlourish commercial lifecycle events.
    Verifies x_weflourish_signature using HMAC-SHA256.
    """
    body = await request.body()

    if not x_weflourish_signature:
        logger.warning("Missing x-weflourish-signature header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature",
        )

    if not rfq_service.verify_signature(body, x_weflourish_signature):
        logger.error("Invalid x-weflourish-signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    payload = await request.json()
    logger.info(f"Received WeFlourish webhook: {payload.get('event')}")

    await rfq_service.handle_webhook(payload)

    return {"status": "accepted"}

from fastapi import Body

@router.post("/bids", status_code=status.HTTP_201_CREATED)
async def create_bid(
    bid_request: BidCreateRequest = Body(...),
    rfq_service: WeFlourishRFQService = Depends(WeFlourishRFQService.get_instance),
):
    """
    Push a new bid (project requirement) to WeFlourish.
    """
    from src.core.models.rfq import Bid

    bid = Bid(
        ohm_id=bid_request.ohm_id,
        project_name=bid_request.project_name,
        description=bid_request.description,
        project_link=bid_request.project_link,
        required_capabilities=bid_request.required_capabilities,
        metadata=bid_request.metadata,
    )

    success = await rfq_service.create_bid_on_weflourish(bid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to push bid to WeFlourish",
        )

    return {
        "status": "success",
        "weflourish_id": bid.external_id,
        "ohm_id": bid.ohm_id
    }
