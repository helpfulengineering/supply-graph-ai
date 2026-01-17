import logging
import httpx
import json
import hashlib
import hmac
from typing import Dict, Any

from .base import BaseIntegrationProvider
from ..models.base import IntegrationCategory, IntegrationRequest, IntegrationResponse, ProviderStatus

logger = logging.getLogger(__name__)

class GenericSupplyChainProvider(BaseIntegrationProvider):
    """
    Generic provider for Supply Chain integrations (RFQ/Quote).
    Can be configured for WeFlourish or other RFQ systems.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.category = IntegrationCategory.SUPPLY_CHAIN
        self.api_url = config.get("api_url")
        self.api_key = config.get("api_key")
        self.webhook_secret = config.get("webhook_secret")

        if not self.api_url:
            logger.warning(f"Provider {self.__class__.__name__} initialized without api_url")

    async def connect(self) -> None:
        """Verify connection to the provider."""
        # Simple health check if an endpoint is provided
        if self.api_url:
            self._is_connected = True
        else:
            self._is_connected = False

    async def disconnect(self) -> None:
        """Disconnect (no-op for HTTP)."""
        self._is_connected = False

    async def check_health(self) -> bool:
        """Check health of the provider."""
        # Could implement a ping to api_url if supported
        return self._is_connected

    async def execute(self, request: IntegrationRequest) -> IntegrationResponse:
        """
        Execute a request against the supply chain provider.

        Supported actions:
        - send_rfq: Send a Bid/RFQ to the provider.
        """
        if request.action == "send_rfq":
            return await self._send_rfq(request.payload)

        return IntegrationResponse(
            success=False,
            data=None,
            error=f"Unsupported action: {request.action}"
        )

    async def _send_rfq(self, rfq_data: Dict[str, Any]) -> IntegrationResponse:
        """
        Send RFQ to the provider's API.
        This method maps the generic RFQ to the specific format if needed,
        or sends it as-is (generic).
        """
        if not self.api_url:
            return IntegrationResponse(
                success=False,
                data=None,
                error="Provider api_url not configured"
            )

        # Payload Construction
        # We construct a standard payload that aligns with the proposed OHM supply chain contract.
        # This standard format is designed to be compatible with reference implementations like WeFlourish.
        payload = {
            "ohm_id": rfq_data.get("id"),
            "project_name": rfq_data.get("project_name"),
            "description": rfq_data.get("description"),
            "required_capabilities": rfq_data.get("capabilities"),
            "metadata": rfq_data.get("metadata", {}),
            "callback_url": rfq_data.get("callback_url")
        }

        # Headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OHM/1.0"
        }

        if self.api_key:
            headers["x-api-key"] = self.api_key

        # Signing (HMAC)
        if self.webhook_secret:
            signature = self._sign_payload(payload)
            headers["x-ohm-signature"] = signature

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use the configured api_url directly.
                # Configuration should provide the full endpoint URL.
                url = self.api_url

                logger.info(f"Sending RFQ to {url}")
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code in (200, 201):
                    return IntegrationResponse(
                        success=True,
                        data=response.json() if response.content else {},
                        metadata={"status_code": response.status_code}
                    )
                else:
                    return IntegrationResponse(
                        success=False,
                        data=response.text,
                        error=f"HTTP Error: {response.status_code}",
                        metadata={"status_code": response.status_code}
                    )

        except Exception as e:
            logger.error(f"Failed to send RFQ: {e}")
            return IntegrationResponse(
                success=False,
                data=None,
                error=str(e)
            )

    def _sign_payload(self, payload: Dict[str, Any]) -> str:
        """Sign payload with HMAC-SHA256."""
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        secret_bytes = self.webhook_secret.encode('utf-8')
        payload_bytes = payload_str.encode('utf-8')
        return hmac.new(secret_bytes, payload_bytes, hashlib.sha256).hexdigest()
