import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from src.core.main import app
from src.core.models.rfq import RFQ, Quote, RFQStatus

@pytest.fixture
def mock_rfq_service_cls():
    with patch("src.core.api.routes.rfq.RFQService") as mock_cls:
        # Configure the instance returned by RFQService()
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance
        yield mock_cls

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_create_rfq_endpoint(client, mock_rfq_service_cls):
    rfq_data = {
        "project_name": "Test API Project",
        "capabilities": ["3D Printing"],
        "description": "Test"
    }

    mock_service = mock_rfq_service_cls.return_value
    created_rfq = RFQ(**rfq_data)
    mock_service.create_rfq.return_value = created_rfq

    response = client.post("/v1/api/rfq/", json=rfq_data)

    assert response.status_code == 200
    assert response.json()["project_name"] == "Test API Project"
    mock_service.create_rfq.assert_called_once()

def test_receive_quote_webhook_missing_signature(client, mock_rfq_service_cls):
    """Verify that request without signature is rejected"""
    quote_data = {
        "rfq_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "provider_id": "test-provider",
        "amount": 500.0,
        "items": []
    }

    response = client.post("/v1/api/rfq/webhooks/quotes", json=quote_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing webhook signature"

def test_receive_quote_webhook_valid(client, mock_rfq_service_cls):
    """Verify processing with mocked signature verification"""
    quote_data = {
        "rfq_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "provider_id": "test-provider",
        "amount": 500.0,
        "items": []
    }

    mock_service = mock_rfq_service_cls.return_value
    saved_quote = Quote(**quote_data)
    mock_service.create_quote.return_value = saved_quote

    # Mock verify_signature dependency to pass
    async def mock_verify_signature():
        pass

    from src.core.api.routes.rfq import verify_signature
    app.dependency_overrides[verify_signature] = mock_verify_signature

    response = client.post("/v1/api/rfq/webhooks/quotes", json=quote_data, headers={"x-ohm-signature": "valid"})

    app.dependency_overrides = {} # Cleanup

    assert response.status_code == 200
    assert response.json()["success"] is True
    mock_service.create_quote.assert_called_once()
