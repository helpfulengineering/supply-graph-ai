import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from src.core.services.base import BaseService
from src.core.services.storage_service import StorageService
from src.core.storage.smart_discovery import SmartFileDiscovery
from src.core.models.rfq import RFQ, Quote, RFQStatus, QuoteStatus
from src.core.integration.manager import IntegrationManager
from src.core.integration.models.base import IntegrationCategory, IntegrationRequest

logger = logging.getLogger(__name__)


class RFQService(BaseService):
    """Service for managing RFQs and Quotes."""

    def __init__(self):
        super().__init__("RFQService")
        self.storage: Optional[StorageService] = None
        self.integration_manager: Optional[IntegrationManager] = None

    async def initialize(self) -> None:
        """Initialize service dependencies."""
        self.storage = await StorageService.get_instance()
        self.integration_manager = IntegrationManager.get_instance()
        if not self.integration_manager._initialized:
            await self.integration_manager.initialize()
        await self.ensure_initialized()

    async def create_rfq(self, rfq_data: RFQ) -> RFQ:
        """Create a new RFQ and broadcast it to supply chain providers."""
        await self.ensure_initialized()

        # 1. Save RFQ to storage
        rfq_json = json.dumps(rfq_data.to_dict(), indent=2, default=str)
        filename = f"rfq/requests/{rfq_data.id}-rfq.json"

        if self.storage and self.storage.manager:
            await self.storage.manager.put_object(filename, rfq_json.encode("utf-8"))
            logger.info(f"Saved RFQ {rfq_data.id} to {filename}")

        # 2. Broadcast to Supply Chain Providers
        providers = await self.integration_manager.get_providers_by_category(
            IntegrationCategory.SUPPLY_CHAIN
        )

        logger.info(f"Found {len(providers)} supply chain providers")

        request = IntegrationRequest(
            provider_type="supply_chain",  # Generic type, providers will handle specific logic
            action="send_rfq",
            payload=rfq_data.to_dict()
        )

        for provider in providers:
            try:
                # Assuming provider name is the key in the manager's dict,
                # but we have the provider instance here.
                # We need to find the name to use execute_request, or call execute directly.
                # Calling execute directly is safer since we have the instance.
                response = await provider.execute(request)
                if response.success:
                    logger.info(f"Successfully sent RFQ to provider")
                else:
                    logger.error(f"Failed to send RFQ to provider: {response.error}")
            except Exception as e:
                logger.error(f"Error sending RFQ to provider: {e}")

        # Update status to OPEN if it was DRAFT
        if rfq_data.status == RFQStatus.DRAFT:
            rfq_data.status = RFQStatus.OPEN
            # Re-save with new status
            rfq_json = json.dumps(rfq_data.to_dict(), indent=2, default=str)
            if self.storage and self.storage.manager:
                await self.storage.manager.put_object(filename, rfq_json.encode("utf-8"))

        return rfq_data

    async def get_rfq(self, rfq_id: UUID) -> Optional[RFQ]:
        """Retrieve an RFQ by ID."""
        await self.ensure_initialized()

        if not self.storage or not self.storage.manager:
            return None

        discovery = SmartFileDiscovery(self.storage.manager)
        files = await discovery.discover_files("rfq")

        for file_info in files:
            try:
                data = await self.storage.manager.get_object(file_info.key)
                rfq_dict = json.loads(data.decode("utf-8"))
                if rfq_dict.get("id") == str(rfq_id):
                    return RFQ(**rfq_dict)
            except Exception as e:
                logger.error(f"Error reading RFQ file {file_info.key}: {e}")
                continue

        return None

    async def create_quote(self, quote_data: Quote) -> Quote:
        """Save a new incoming quote."""
        await self.ensure_initialized()

        quote_json = json.dumps(quote_data.to_dict(), indent=2, default=str)
        filename = f"rfq/quotes/{quote_data.id}-quote.json"

        if self.storage and self.storage.manager:
            await self.storage.manager.put_object(filename, quote_json.encode("utf-8"))
            logger.info(f"Saved Quote {quote_data.id} to {filename}")

        return quote_data

    async def get_quotes_for_rfq(self, rfq_id: UUID) -> List[Quote]:
        """List all quotes for a specific RFQ."""
        await self.ensure_initialized()
        quotes = []

        if not self.storage or not self.storage.manager:
            return quotes

        discovery = SmartFileDiscovery(self.storage.manager)
        files = await discovery.discover_files("quote")

        for file_info in files:
            try:
                data = await self.storage.manager.get_object(file_info.key)
                quote_dict = json.loads(data.decode("utf-8"))
                if quote_dict.get("rfq_id") == str(rfq_id):
                    quotes.append(Quote(**quote_dict))
            except Exception as e:
                logger.error(f"Error reading Quote file {file_info.key}: {e}")
                continue

        return quotes

    async def update_rfq_status(self, rfq_id: UUID, new_status: RFQStatus) -> bool:
        """Update the status of an RFQ."""
        rfq = await self.get_rfq(rfq_id)
        if not rfq:
            return False

        rfq.status = new_status

        # Save updated RFQ
        rfq_json = json.dumps(rfq.to_dict(), indent=2, default=str)
        # We need to find the filename again or store it.
        # For now, let's assume standard naming convention or search again.
        # Ideally, get_rfq could return file path too, but let's stick to convention.
        filename = f"rfq/requests/{rfq.id}-rfq.json"

        if self.storage and self.storage.manager:
             # Check if file exists at standard location, if not, we might create a duplicate if it was moved.
             # But our discovery uses directory structure, so we should write back to the same place if we stick to convention.
            await self.storage.manager.put_object(filename, rfq_json.encode("utf-8"))
            return True

        return False
