import pytest
import json
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.services.rfq_service import RFQService
from src.core.models.rfq import RFQ, Quote, RFQStatus
from src.core.integration.models.base import IntegrationCategory, IntegrationResponse

@pytest.fixture
def mock_storage_instance():
    instance = AsyncMock()
    instance.manager = AsyncMock()
    # Configure manager.put_object to be awaitable
    instance.manager.put_object = AsyncMock(return_value=True)
    return instance

@pytest.fixture
def mock_integration_instance():
    instance = AsyncMock()
    instance._initialized = True
    return instance

@pytest.fixture
def rfq_service(mock_storage_instance, mock_integration_instance):
    with patch("src.core.services.storage_service.StorageService.get_instance", new_callable=AsyncMock) as mock_storage_cls:
        with patch("src.core.integration.manager.IntegrationManager.get_instance") as mock_integration_cls:
            mock_storage_cls.return_value = mock_storage_instance
            mock_integration_cls.return_value = mock_integration_instance

            service = RFQService()
            yield service

@pytest.mark.asyncio
async def test_create_rfq(rfq_service, mock_integration_instance, mock_storage_instance):
    rfq = RFQ(project_name="Test Project", capabilities=["CNC"])

    # Mock integration providers
    mock_provider = AsyncMock()
    mock_provider.execute.return_value = IntegrationResponse(success=True, data={})

    # Configure the mock instance that will be returned by get_instance
    mock_integration_instance.get_providers_by_category.return_value = [mock_provider]

    result = await rfq_service.create_rfq(rfq)

    assert result.status == RFQStatus.OPEN
    mock_storage_instance.manager.put_object.assert_called()
    mock_provider.execute.assert_called_once()

@pytest.mark.asyncio
async def test_create_quote(rfq_service, mock_storage_instance):
    quote = Quote(rfq_id=uuid4(), provider_id="prov1", amount=100.0)

    result = await rfq_service.create_quote(quote)

    assert result.amount == 100.0
    mock_storage_instance.manager.put_object.assert_called()

@pytest.mark.asyncio
async def test_update_rfq_status(rfq_service, mock_storage_instance):
    rfq_id = uuid4()
    rfq = RFQ(id=rfq_id, project_name="Test", status=RFQStatus.OPEN)

    with patch("src.core.services.rfq_service.SmartFileDiscovery") as MockDiscovery:
        mock_discovery_instance = MockDiscovery.return_value
        mock_discovery_instance.discover_files = AsyncMock(return_value=[
            MagicMock(key=f"rfq/requests/{rfq_id}-rfq.json")
        ])

        # storage.manager.get_object is async
        mock_storage_instance.manager.get_object.return_value = json.dumps(rfq.to_dict()).encode("utf-8")

        success = await rfq_service.update_rfq_status(rfq_id, RFQStatus.FILLED)

        assert success is True
        args, _ = mock_storage_instance.manager.put_object.call_args
        saved_data = json.loads(args[1].decode("utf-8"))
        assert saved_data["status"] == "filled"
