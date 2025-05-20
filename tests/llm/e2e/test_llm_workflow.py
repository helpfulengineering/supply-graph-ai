import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# Register the e2e marker to avoid the warning
pytest.mark.e2e = pytest.mark.skipif(False, reason="E2E test marker")

@pytest.mark.e2e
def test_llm_workflow(client, mock_groq):
    """End-to-end test for LLM workflow"""
    # Setup mock response at the correct path in the mock structure
    mock_response = mock_groq.chat.completions.create.return_value
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = '{"result": "processed data"}'
    mock_response.model = "llama-3.1-8b-instant"
    mock_response.usage = MagicMock()
    mock_response.usage.dict.return_value = {"total_tokens": 20}
    
    # Call endpoint
    response = client.post(
        "/v1/llm/",
        json={"prompt": "Process this text", "context": "Return JSON"}
    )
    
    assert response.status_code == 200
    assert "result" in response.json()["response"]
