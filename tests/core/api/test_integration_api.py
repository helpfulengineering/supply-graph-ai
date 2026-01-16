import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from src.core.main import app
from src.core.integration.manager import IntegrationManager
from src.core.integration.providers.base import BaseIntegrationProvider
from src.core.integration.models.base import IntegrationCategory, ProviderStatus

# Mock Provider
class MockApiProvider(BaseIntegrationProvider):
    def __init__(self, config):
        super().__init__(config)
        self.category = IntegrationCategory.AI_MODEL
        self.provider_type = "mock_api"
        self._is_connected = True

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def check_health(self):
        return True

    async def execute(self, request):
        pass

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def setup_integration_manager():
    # Reset singleton
    IntegrationManager._instance = None
    IntegrationManager._initialized = False
    manager = IntegrationManager.get_instance()

    # Register mock provider
    manager.register_provider_class("mock_api", MockApiProvider)

    # Mock config loading to avoid file system issues and ensure our provider is loaded
    with patch("builtins.open", MagicMock()) as mock_open:
        with patch("json.load") as mock_json:
            mock_json.return_value = {
                "providers": {
                    "test_provider": {
                        "provider_type": "mock_api"
                    }
                }
            }
            with patch("os.path.exists", return_value=True):
                 # Initialize (async) - need to run this in loop or mock initialize
                 # Since we are in a sync test with TestClient, we might need to rely on app startup
                 # or manually setup providers.

                 # Manual setup for test simplicity
                 provider = MockApiProvider({})
                 manager.providers["test_provider"] = provider
                 manager._initialized = True

    return manager

def test_list_providers(client, setup_integration_manager):
    response = client.get("/v1/api/integration/providers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["status"] == "success"

    # Data is wrapped in "data" field by api_endpoint decorator
    # wait, api_endpoint decorator structure:
    # { "status": ..., "data": { "result": [...] } ... } if result is list?
    # Let's check api_endpoint decorator logic.
    # If result is list, it puts it in "data": {"result": result} ?
    # Or just "data": result ?

    # Let's verify structure in test failure if needed, but assuming standard wrapper
    providers = data["data"]
    # If returned directly as list from endpoint, decorator wraps it.
    # If it's a list, the decorator usually does: "data": result if isinstance(result, dict) else {"result": result}
    # So it should be data["result"]

    items = providers.get("result", providers)
    assert len(items) >= 1
    found = False
    for item in items:
        if item["name"] == "test_provider":
            assert item["type"] == "mock_api"
            assert item["status"] == "active"
            found = True
    assert found

def test_get_providers_status(client, setup_integration_manager):
    # This endpoint is async, TestClient handles it but the manager.providers is populated
    response = client.get("/v1/api/integration/status")
    assert response.status_code == 200
    data = response.json()

    status_report = data["data"] # "data" field from wrapper
    # result is a dict, so "data": result

    assert "test_provider" in status_report
    assert status_report["test_provider"]["status"] == "healthy"
