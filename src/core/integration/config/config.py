from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class IntegrationConfig(BaseModel):
    """Configuration for IntegrationManager."""
    providers: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    defaults: Dict[str, str] = Field(default_factory=dict)
