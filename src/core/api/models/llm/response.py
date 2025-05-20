from pydantic import BaseModel
from typing import Optional

class LLMResponse(BaseModel):
    """ Response model for LLM API. """
    
    response: str
    model: str
    usage: Optional[dict] = None