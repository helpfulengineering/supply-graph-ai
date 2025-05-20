from fastapi import APIRouter, HTTPException, status, Body
from typing import Dict, Any, List, Optional

from ..models.llm.request import LLMRequest
from ..models.llm.response import LLMResponse, PromptListResponse, ContextListResponse
from ..models.llm.response import PromptInfo, ContextInfo, TokenUsage

from src.core.services.llm_provider import LLMProvider
from src.core.services.directory_manager import DirectoryManager

# Create router with prefix and tags
router = APIRouter(prefix="/v1", tags=["llm"])

# Initialize services
llm_provider = LLMProvider()
directory_manager = DirectoryManager()

@router.get("/llm/prompts", response_model=PromptListResponse)
async def list_prompts():
    """List all available prompt templates"""
    prompt_list = directory_manager.list_prompts()
    prompts = [
        PromptInfo(
            name=p["name"],
            description=p["description"],
            required_variables=p["required_variables"]
        ) for p in prompt_list
    ]
    return PromptListResponse(prompts=prompts)

@router.get("/llm/contexts", response_model=ContextListResponse)
async def list_contexts():
    """List all available contexts"""
    context_list = directory_manager.list_contexts()
    contexts = [
        ContextInfo(
            name=c["name"],
            description=c["description"]
        ) for c in context_list
    ]
    return ContextListResponse(contexts=contexts)

@router.get("/llm/models", response_model=List[Dict[str, str]])
async def list_available_models():
    """List all available LLM models that can be used"""
    return llm_provider.get_available_models()

@router.post("/llm", response_model=LLMResponse)
async def process_llm_request(request: LLMRequest):
    """Process a request with the LLM"""
    try:
        result = await llm_provider.generate(
            prompt=request.prompt,
            prompt_template=request.prompt_template,
            context_name=request.context_name,
            template_variables=request.template_variables,
            system_message=request.system_message,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop_sequences=request.stop_sequences
        )
        
        return LLMResponse(
            response=result["response"],
            usage=TokenUsage(
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=result["usage"]["completion_tokens"],
                total_tokens=result["usage"]["total_tokens"]
            ),
            model=result["model"],
            finish_reason=result["finish_reason"],
            processing_time_ms=result["processing_time_ms"]
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM processing error: {str(e)}"
        )