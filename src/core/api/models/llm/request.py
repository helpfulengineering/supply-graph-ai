from pydantic import BaseModel, Field, field_validator
from typing import Optional

class LLMRequest(BaseModel):
    """ Request model for LLM API. """
    prompt: str
    context: Optional[str] = None
    model: Optional[str] = 'llama-3.1-8b-instant'
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    stream: Optional[bool] = False
    
    @field_validator('prompt')
    @classmethod  # This is now required in V2
    def prompt_must_not_be_empty(cls, v):
        if not v or v.strip() == '':
            raise ValueError('prompt cannot be empty')
        return v
