import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

def test_llm_endpoint_non_streaming(client, mock_groq):
    """Test non-streaming LLM endpoint"""
    # Setup mock response at the correct place in the mock structure
    mock_response = mock_groq.chat.completions.create.return_value
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = "Test response"
    mock_response.model = "llama-3.1-8b-instant"
    mock_response.usage = MagicMock()
    mock_response.usage.dict.return_value = {"total_tokens": 10}
    
    # Make request to endpoint
    response = client.post(
        "/v1/llm/",
        json={"prompt": "Test prompt"}
    )
    
    assert response.status_code == 200
    assert response.json()["response"] == "Test response"

# Similar updates for other failing tests...