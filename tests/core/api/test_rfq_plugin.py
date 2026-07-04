import pytest
import hmac
import hashlib
import json
from fastapi.testclient import TestClient
from src.core.main import app
from src.plugins.weflourish_ohm.service import WeFlourishRFQService
from src.plugins.manager import PluginManager

@pytest.fixture(scope="module")
def setup_plugin():
    from src.config import settings
    # Set active plugins for the app
    settings.ACTIVE_PLUGINS = ["weflourish_ohm"]
    # Re-initialize plugin manager
    PluginManager.reset_instance()
    pm = PluginManager.get_instance()
    pm.reload_config()
    pm.discover_and_load()

    from src.core.main import api_v1
    pm.register_all_routes(api_v1)

    return pm

@pytest.fixture
def client(setup_plugin):
    # This will use the app which has PluginManager.register_all_routes(api_v1) in its flow
    return TestClient(app)

@pytest.fixture
def webhook_secret(setup_plugin):
    plugin = setup_plugin.get_plugin("weflourish_ohm")
    old_secret = plugin.settings.OHM_WEBHOOK_SECRET
    plugin.settings.OHM_WEBHOOK_SECRET = "test_secret"
    yield "test_secret"
    plugin.settings.OHM_WEBHOOK_SECRET = old_secret

def test_webhook_signature_verification(client, webhook_secret):
    payload = {
        "event": "quote.created",
        "ohm_request_id": "req-123",
        "quote": {
            "id": "q-1",
            "amount": 100,
            "contractor": "Test",
            "items": []
        }
    }
    # Add a mock bid to the service so it's found
    from src.plugins.weflourish_ohm.service import WeFlourishRFQService
    from src.core.models.rfq import Bid
    service = WeFlourishRFQService.get_instance()
    service._bids["req-123"] = Bid(ohm_id="req-123", project_name="Test", description="Test")

    body = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    headers = {"x-weflourish-signature": signature, "Content-Type": "application/json"}

    response = client.post("/v1/api/rfq/webhooks/weflourish", content=body, headers=headers)
    if response.status_code != 200:
        print(f"Error response: {response.json()}")
    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}

def test_webhook_invalid_signature(client, webhook_secret):
    payload = {"event": "quote.created", "ohm_request_id": "req-123"}
    headers = {"x-weflourish-signature": "invalid_sig"}

    response = client.post("/v1/api/rfq/webhooks/weflourish", json=payload, headers=headers)
    assert response.status_code == 401

def test_create_bid_endpoint(client, monkeypatch):
    async def mock_create_bid_on_weflourish(self, bid):
        bid.external_id = "wf-123"
        return True

    monkeypatch.setattr(WeFlourishRFQService, "create_bid_on_weflourish", mock_create_bid_on_weflourish)

    # Wrap payload in 'request' field if that's what FastAPI expects for the model?
    # No, FastAPI expects the body to be the model.
    # Wait, the error said: {'detail': [{'type': 'missing', 'loc': ['body', 'request'], 'msg': 'Field required', 'input': None}]}
    # This happens when you have 'def create_bid(request: BidCreateRequest)' in the route.
    # FastAPI thinks 'request' is a field in the body.

    payload = {
        "ohm_id": "req-123",
        "project_name": "Test Project",
        "description": "Test Description",
        "required_capabilities": ["cnc"]
    }

    response = client.post("/v1/api/rfq/bids", json={"bid_request": payload})
    if response.status_code != 201:
        print(f"Error response (create_bid): {response.json()}")
    assert response.status_code == 201
    assert response.json()["weflourish_id"] == "wf-123"
