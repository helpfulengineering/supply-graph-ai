from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class TokenUsage(BaseModel):
    """Token usage information"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class LLMResponse(BaseModel):
    """Response model for the LLM endpoint"""
    response: str = Field(..., description="The generated text from the LLM")
    usage: TokenUsage = Field(..., description="Token usage statistics")
    model: str = Field(..., description="Model used for generation")
    finish_reason: Optional[str] = Field(None, description="Reason for completion")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")

class PromptInfo(BaseModel):
    """Information about an available prompt template"""
    name: str = Field(..., description="Name of the prompt template")
    description: Optional[str] = Field(None, description="Brief description of the prompt")
    required_variables: List[str] = Field(default_factory=list, description="Required template variables")
    
class PromptListResponse(BaseModel):
    """Response with available prompt templates"""
    prompts: List[PromptInfo] = Field(..., description="Available prompt templates")
    
class ContextInfo(BaseModel):
    """Information about an available context"""
    name: str = Field(..., description="Name of the context")
    description: Optional[str] = Field(None, description="Brief description of the context")
    
class ContextListResponse(BaseModel):
    """Response with available contexts"""
    contexts: List[ContextInfo] = Field(..., description="Available contexts")