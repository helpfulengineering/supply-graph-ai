import hmac
import hashlib
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime

from src.core.models.rfq import Bid, BidStatus, Quote, QuoteStatus, QuoteItem
from src.core.utils.logging import get_logger
from .config import PluginSettings

logger = get_logger(__name__)

class WeFlourishRFQService:
    _instance = None

    def __init__(self, settings: PluginSettings):
        self.settings = settings
        # In a real app, these would be backed by a database
        self._bids: Dict[str, Bid] = {}

    @classmethod
    def get_instance(cls, settings: Optional[PluginSettings] = None) -> "WeFlourishRFQService":
        if cls._instance is None:
            if settings is None:
                raise ValueError("Settings required for service initialization")
            cls._instance = cls(settings)
        return cls._instance

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify the HMAC-SHA256 signature from WeFlourish."""
        if not self.settings.OHM_WEBHOOK_SECRET:
            logger.warning("OHM_WEBHOOK_SECRET not configured, skipping signature verification")
            return True

        expected_signature = hmac.new(
            self.settings.OHM_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    async def create_bid_on_weflourish(self, bid: Bid) -> bool:
        """Push a bid to WeFlourish."""
        url = f"{self.settings.WEFLOURISH_API_URL}/ohm/bids"
        headers = {
            "x-api-key": self.settings.WEFLOURISH_API_KEY,
            "Content-Type": "application/json"
        }

        payload = bid.to_dict()
        # Ensure callback URL is included
        payload["callback_url"] = self.settings.OHM_CALLBACK_URL_BASE

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                bid.external_id = data.get("id")
                self._bids[bid.ohm_id] = bid
                logger.info(f"Successfully created bid {bid.ohm_id} on WeFlourish (WF ID: {bid.external_id})")
                return True
            except httpx.HTTPError as e:
                logger.error(f"Failed to create bid on WeFlourish: {e}")
                return False

    async def handle_webhook(self, payload: Dict[str, Any]):
        """Handle incoming webhooks from WeFlourish."""
        event = payload.get("event")
        ohm_request_id = payload.get("ohm_request_id")

        if not ohm_request_id:
            logger.error("Webhook payload missing ohm_request_id")
            return

        if event == "quote.created":
            await self._handle_quote_created(ohm_request_id, payload.get("quote"))
        elif event == "quote.accepted":
            await self._handle_quote_accepted(ohm_request_id, payload.get("quote_id"))
        elif event == "bid.status_changed":
            await self._handle_status_changed(ohm_request_id, payload.get("new_status"))
        else:
            logger.warning(f"Unhandled webhook event: {event}")

    async def _handle_quote_created(self, ohm_id: str, quote_data: Dict[str, Any]):
        bid = self._bids.get(ohm_id)
        if not bid:
            logger.error(f"Received quote for unknown bid: {ohm_id}")
            return

        items = [
            QuoteItem(
                bid_item_id=item.get("bidItemId"),
                description=item.get("description"),
                cost=item.get("cost"),
                ohm_resource_id=item.get("ohm_resource_id")
            )
            for item in quote_data.get("items", [])
        ]

        quote = Quote(
            id=quote_data.get("id"),
            amount=quote_data.get("amount"),
            contractor=quote_data.get("contractor"),
            items=items
        )

        bid.quotes.append(quote)
        bid.updated_at = datetime.utcnow()
        logger.info(f"Added new quote {quote.id} to bid {ohm_id}")

    async def _handle_quote_accepted(self, ohm_id: str, quote_id: str):
        bid = self._bids.get(ohm_id)
        if not bid:
            return

        for quote in bid.quotes:
            if quote.id == quote_id:
                quote.status = QuoteStatus.ACCEPTED
                logger.info(f"Quote {quote_id} accepted for bid {ohm_id}")
                break

    async def _handle_status_changed(self, ohm_id: str, new_status: str):
        bid = self._bids.get(ohm_id)
        if not bid:
            return

        try:
            bid.status = BidStatus(new_status)
            bid.updated_at = datetime.utcnow()
            logger.info(f"Bid {ohm_id} status changed to {new_status}")
        except ValueError:
            logger.warning(f"Invalid status received: {new_status}")

    def get_bid(self, ohm_id: str) -> Optional[Bid]:
        return self._bids.get(ohm_id)
