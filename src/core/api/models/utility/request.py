from pydantic import BaseModel
from typing import Optional

class DomainFilterRequest(BaseModel):
    """Request model for filtering domains"""
    # Optional fields
    name: Optional[str] = None
    active_only: bool = True

class ContextFilterRequest(BaseModel):
    """Request model for filtering contexts within a domain"""
    # Optional fields
    name: Optional[str] = None
    include_deprecated: bool = False
    with_details: bool = False