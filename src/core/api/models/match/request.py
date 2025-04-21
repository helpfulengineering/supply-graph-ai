from pydantic import BaseModel
from typing import Dict, Any, Optional

class RequirementsInput(BaseModel):
    content: Dict[str, Any]
    domain: Optional[str] = None
    type: str  # "okh" or "recipe"

class CapabilitiesInput(BaseModel):
    content: Dict[str, Any]
    domain: Optional[str] = None
    type: str  # "okw" or "kitchen"