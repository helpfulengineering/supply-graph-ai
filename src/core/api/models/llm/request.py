from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class LLMRequest(BaseModel):
    """Request model for the LLM endpoint"""
    prompt: str = Field(..., description="The prompt to send to the LLM")
    prompt_template: Optional[str] = Field(None, description="Name of a prompt template to use")
    context_name: Optional[str] = Field(None, description="Name of the context to apply")
    template_variables: Dict[str, Any] = Field(default_factory=dict, description="Variables to fill in prompt template")
    system_message: Optional[str] = Field(None, description="Optional system message to guide the LLM")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Temperature parameter (0-1)")
    max_tokens: int = Field(1000, gt=0, description="Maximum tokens to generate")
    stop_sequences: Optional[List[str]] = Field(None, description="Sequences that will stop generation")