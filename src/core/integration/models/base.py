from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class IntegrationCategory(str, Enum):
    """Categories of external integrations."""
    AI_MODEL = "ai_model"
    VCS_PLATFORM = "vcs_platform"
    STORAGE_BUCKET = "storage_bucket"
    ERP = "erp"

class IntegrationRequest(BaseModel):
    """Standardized request for an integration provider."""
    provider_type: str
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class IntegrationResponse(BaseModel):
    """Standardized response from an integration provider."""
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

class ProviderStatus(str, Enum):
    """Status of an integration provider."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"
