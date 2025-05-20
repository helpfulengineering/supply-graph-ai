import pytest
from fastapi.testclient import TestClient
from src.core.main import app
from unittest.mock import MagicMock, patch

@pytest.fixture
def client():
    """Fixture for FastAPI test client."""
    return TestClient(app)

@pytest.fixture
def mock_groq():
    """Fixture to mock Groq client."""
    # Create a mock with the properly configured return value
    mock_client = MagicMock()
    
    # Configure the mock to work with async code
    mock_create = MagicMock()
    # Make the mock.return_value property directly accessible (not awaitable)
    mock_client.chat.completions.create.return_value = mock_create
    
    # Patch the client in the LLM route module
    with patch("src.core.api.routes.llm.client", mock_client):
        yield mock_client