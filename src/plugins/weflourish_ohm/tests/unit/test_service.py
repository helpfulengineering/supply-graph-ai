import pytest
import hmac
import hashlib
import json
from unittest.mock import AsyncMock, patch
from src.plugins.weflourish_ohm.service import WeFlourishRFQService
from src.plugins.weflourish_ohm.config import PluginSettings
from src.core.models.rfq import Bid, BidStatus, QuoteStatus

@pytest.fixture
def settings():
    return PluginSettings(
        WEFLOURISH_API_KEY="test_key",
        OHM_WEBHOOK_SECRET="test_secret",
        WEFLOURISH_API_URL="https://api.test.com"
    )

@pytest.fixture
def service(settings):
    # Reset singleton-like behavior for testing if necessary,
    # but here we just instantiate it directly for unit testing.
    return WeFlourishRFQService(settings)

def test_verify_signature_valid(service, settings):
    payload = b'{"foo": "bar"}'
    signature = hmac.new(
        settings.OHM_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    assert service.verify_signature(payload, signature) is True

def test_verify_signature_invalid(service):
    payload = b'{"foo": "bar"}'
    assert service.verify_signature(payload, "wrong_sig") is False

@pytest.mark.anyio
async def test_create_bid_on_weflourish(service):
    bid = Bid(ohm_id="req-1", project_name="P1", description="D1")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json = MagicMock(return_value={"id": "wf-123"})
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        success = await service.create_bid_on_weflourish(bid)

        assert success is True
        assert bid.external_id == "wf-123"
        assert service.get_bid("req-1") is bid

@pytest.mark.anyio
async def test_handle_webhook_quote_created(service):
    bid = Bid(ohm_id="req-1", project_name="P1", description="D1")
    service._bids["req-1"] = bid

    payload = {
        "event": "quote.created",
        "ohm_request_id": "req-1",
        "quote": {
            "id": "q-1",
            "amount": 500,
            "contractor": "Acme",
            "items": [
                {"bidItemId": "i1", "description": "D1", "cost": 500}
            ]
        }
    }

    await service.handle_webhook(payload)

    assert len(bid.quotes) == 1
    assert bid.quotes[0].id == "q-1"
    assert bid.quotes[0].amount == 500

@pytest.mark.anyio
async def test_handle_webhook_status_changed(service):
    bid = Bid(ohm_id="req-1", project_name="P1", description="D1", status=BidStatus.OPEN)
    service._bids["req-1"] = bid

    payload = {
        "event": "bid.status_changed",
        "ohm_request_id": "req-1",
        "new_status": "completed"
    }

    await service.handle_webhook(payload)
    assert bid.status == BidStatus.COMPLETED

from unittest.mock import MagicMock
