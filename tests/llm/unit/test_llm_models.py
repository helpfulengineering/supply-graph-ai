import pytest
from src.core.api.models.llm.request import LLMRequest
from src.core.api.models.llm.response import LLMResponse

def test_llm_request_valid():
    """Test valid LLMRequest model with all fields."""
    data = {
        "prompt": "What is the capital of France?",
        "context": "Provide a concise answer.",
        "model": "llama-3.1-8b-instant",
        "max_tokens": 100,
        "temperature": 0.7,
        "top_p": 0.95,
        "stream": False
    }
    request = LLMRequest(**data)
    assert request.prompt == "What is the capital of France?"
    assert request.context == "Provide a concise answer."
    assert request.model == "llama-3.1-8b-instant"
    assert request.max_tokens == 100
    assert request.temperature == 0.7
    assert request.top_p == 0.95
    assert request.stream is False

def test_llm_request_no_context():
    """Test LLMRequest with no context, using defaults."""
    data = {"prompt": "Test prompt"}
    request = LLMRequest(**data)
    assert request.prompt == "Test prompt"
    assert request.context is None
    assert request.model == "llama-3.1-8b-instant"
    assert request.max_tokens == 512
    assert request.temperature == 0.7  
    assert request.top_p == 0.9  
    assert request.stream is False

def test_llm_request_invalid_prompt():
    """Test LLMRequest with empty prompt raises error."""
    with pytest.raises(ValueError, match="prompt"):
        LLMRequest(prompt="")

def test_llm_response_valid():
    """Test valid LLMResponse model."""
    data = {
        "response": "The capital is Paris.",
        "model": "llama-3.1-8b-instant",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    }
    response = LLMResponse(**data)
    assert response.response == "The capital is Paris."
    assert response.model == "llama-3.1-8b-instant"
    assert response.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}

def test_llm_response_no_usage():
    """Test LLMResponse with no usage data."""
    data = {"response": "Test response", "model": "llama-3.1-8b-instant"}
    response = LLMResponse(**data)
    assert response.response == "Test response"
    assert response.model == "llama-3.1-8b-instant"
    assert response.usage is None