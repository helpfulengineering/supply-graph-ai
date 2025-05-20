from pydantic import BaseModel
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
    