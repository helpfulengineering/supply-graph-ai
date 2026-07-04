import pytest
import hmac
import hashlib
import json
from fastapi.testclient import TestClient
from src.core.main import app, api_v1
from src.plugins.manager import PluginManager
from src.plugins.weflourish_ohm.service import WeFlourishRFQService
from src.core.models.rfq import Bid

@pytest.fixture(scope="module")
def setup_integration():
    from src.config import settings
    original_plugins = settings.ACTIVE_PLUGINS
    settings.ACTIVE_PLUGINS = ["weflourish_ohm"]

    PluginManager.reset_instance()
    pm = PluginManager.get_instance()
    pm.reload_config()
    pm.discover_and_load()

    # We must ensure routes are registered on the app's api_v1
    pm.register_all_routes(api_v1)

    yield pm

    settings.ACTIVE_PLUGINS = original_plugins
    PluginManager.reset_instance()

@pytest.fixture
def client(setup_integration):
    return TestClient(app)

@pytest.fixture
def service(setup_integration):
    return WeFlourishRFQService.get_instance()

def test_webhook_full_flow(client, service, setup_integration):
    # 1. Create a bid locally (simulated)
    bid_id = "req-integration-1"
    bid = Bid(ohm_id=bid_id, project_name="Integration Test", description="Desc")
    service._bids[bid_id] = bid

    # 2. Receive a webhook for this bid
    payload = {
        "event": "quote.created",
        "ohm_request_id": bid_id,
        "quote": {
            "id": "q-999",
            "amount": 1234.56,
            "contractor": "Acme Corp",
            "items": []
        }
    }
    body = json.dumps(payload, separators=(",", ":")).encode()

    # Sign it
    plugin = setup_integration.get_plugin("weflourish_ohm")
    plugin.settings.OHM_WEBHOOK_SECRET = "integration_secret"

    signature = hmac.new(
        b"integration_secret",
        body,
        hashlib.sha256
    ).hexdigest()

    headers = {
        "x-weflourish-signature": signature,
        "Content-Type": "application/json"
    }

    response = client.post("/v1/api/rfq/webhooks/weflourish", content=body, headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}

    # 3. Verify service state
    updated_bid = service.get_bid(bid_id)
    assert len(updated_bid.quotes) == 1
    assert updated_bid.quotes[0].amount == 1234.56

def test_webhook_unauthorized(client):
    payload = {"event": "foo"}
    headers = {"x-weflourish-signature": "bad"}
    response = client.post("/v1/api/rfq/webhooks/weflourish", json=payload, headers=headers)
    assert response.status_code == 401

def test_create_bid_api(client, monkeypatch):
    # Mock outbound HTTP call
    async def mock_push(self, bid):
        bid.external_id = "wf-remote-id"
        return True

    monkeypatch.setattr(WeFlourishRFQService, "create_bid_on_weflourish", mock_push)

    payload = {
        "bid_request": {
            "ohm_id": "req-api-test",
            "project_name": "API Test",
            "description": "Testing the POST /bids endpoint"
        }
    }

    response = client.post("/v1/api/rfq/bids", json=payload)
    assert response.status_code == 201
    assert response.json()["weflourish_id"] == "wf-remote-id"
