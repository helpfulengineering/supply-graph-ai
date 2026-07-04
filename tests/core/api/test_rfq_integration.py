import pytest
import hmac
import hashlib
import json
from fastapi.testclient import TestClient
from src.core.main import app
from src.core.services.rfq_service import RFQService
from src.config import settings

client = TestClient(app)

@pytest.fixture
def rfq_service():
    return RFQService()

@pytest.fixture
def webhook_secret():
    old_secret = settings.OHM_WEBHOOK_SECRET
    settings.OHM_WEBHOOK_SECRET = "test_secret"
    yield "test_secret"
    settings.OHM_WEBHOOK_SECRET = old_secret

def test_webhook_signature_verification(webhook_secret):
    payload = {"event": "quote.created", "ohm_request_id": "req-123"}
    # Use compact separators to match common JSON serialization
    body = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    headers = {"x-weflourish-signature": signature}

    # We need to ensure the service instance used by the route is the one we want to check,
    # but since it's a singleton-like, it should work.
    response = client.post("/v1/api/rfq/webhooks/weflourish", content=body, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}

def test_webhook_invalid_signature(webhook_secret):
    payload = {"event": "quote.created", "ohm_request_id": "req-123"}
    headers = {"x-weflourish-signature": "invalid_sig"}

    response = client.post("/v1/api/rfq/webhooks/weflourish", json=payload, headers=headers)
    assert response.status_code == 401

def test_create_bid_endpoint(monkeypatch):
    async def mock_create_bid_on_weflourish(self, bid):
        bid.weflourish_id = "wf-123"
        return True

    monkeypatch.setattr(RFQService, "create_bid_on_weflourish", mock_create_bid_on_weflourish)

    payload = {
        "ohm_id": "req-123",
        "project_name": "Test Project",
        "description": "Test Description",
        "required_capabilities": ["cnc"]
    }

    response = client.post("/v1/api/rfq/bids", json=payload)
    assert response.status_code == 201
    assert response.json()["weflourish_id"] == "wf-123"
