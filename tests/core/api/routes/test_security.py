import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from src.core.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_webhook_security(client):
    """Verify that webhooks reject requests without signature."""
    quote_data = {
        "rfq_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "provider_id": "test-provider",
        "amount": 500.0,
        "items": []
    }

    # Missing signature header
    response = client.post("/v1/api/rfq/webhooks/quotes", json=quote_data)

    # Should be 401 Unauthorized or 422 Unprocessable Entity (if Header(...) requirement fails pydantic validation)
    # Since I used Header(...), FastApi/Pydantic validation might kick in first returning 422 for missing required header.
    # If header is present but None, it hits my check logic (401).
    # Let's check which one it returns.
    # Actually, verify_signature sets default? No, I changed it to Header(...).
    # So it should be 422.

    assert response.status_code in (401, 422)

    # Empty signature header
    response = client.post("/v1/api/rfq/webhooks/quotes", json=quote_data, headers={"x-ohm-signature": ""})
    assert response.status_code == 401
