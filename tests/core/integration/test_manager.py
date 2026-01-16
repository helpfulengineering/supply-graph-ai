import pytest
import pytest_asyncio
import asyncio
from unittest.mock import MagicMock, patch
from src.core.integration.manager import IntegrationManager
from src.core.integration.models.base import IntegrationCategory, IntegrationRequest, IntegrationResponse
from src.core.integration.providers.base import BaseIntegrationProvider

# Mock Provider
class MockProvider(BaseIntegrationProvider):
    def __init__(self, config):
        super().__init__(config)
        self.category = IntegrationCategory.VCS_PLATFORM
        self.provider_type = "mock"

    async def connect(self):
        self._is_connected = True

    async def disconnect(self):
        self._is_connected = False

    async def check_health(self):
        return self._is_connected

    async def execute(self, request):
        if request.action == "fail":
            return IntegrationResponse(success=False, data=None, error="Failed intentionally")
        return IntegrationResponse(success=True, data={"result": "success"})

@pytest_asyncio.fixture
async def integration_manager():
    # Reset singleton
    IntegrationManager._instance = None
    IntegrationManager._initialized = False
    manager = IntegrationManager.get_instance()

    # Register mock provider
    manager.register_provider_class("mock", MockProvider)

    # Initialize with mocked config
    with patch("builtins.open", MagicMock()) as mock_open:
        with patch("json.load") as mock_json:
            mock_json.return_value = {
                "providers": {
                    "mock_instance": {
                        "provider_type": "mock",
                        "some_key": "some_value"
                    }
                }
            }
            with patch("os.path.exists", return_value=True):
                 await manager.initialize()

    return manager

@pytest.mark.asyncio
async def test_manager_initialization(integration_manager):
    assert integration_manager._initialized
    assert "mock_instance" in integration_manager.providers
    assert isinstance(integration_manager.providers["mock_instance"], MockProvider)

@pytest.mark.asyncio
async def test_execute_request(integration_manager):
    request = IntegrationRequest(provider_type="mock", action="test")
    response = await integration_manager.execute_request("mock_instance", request)
    assert response.success
    assert response.data["result"] == "success"

@pytest.mark.asyncio
async def test_execute_request_failure(integration_manager):
    request = IntegrationRequest(provider_type="mock", action="fail")
    response = await integration_manager.execute_request("mock_instance", request)
    assert not response.success
    assert response.error == "Failed intentionally"

@pytest.mark.asyncio
async def test_get_providers_by_category(integration_manager):
    providers = await integration_manager.get_providers_by_category(IntegrationCategory.VCS_PLATFORM)
    assert len(providers) == 1
    assert providers[0].provider_type == "mock"
