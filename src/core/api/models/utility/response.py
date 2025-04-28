from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class Domain(BaseModel):
    """Model for domain information"""
    # Required fields only
    id: str
    name: str
    description: str

class DomainsResponse(BaseModel):
    """Response model for available domains"""
    # Required fields only
    domains: List[Domain]

class Context(BaseModel):
    """Model for validation context information"""
    # Required fields only
    id: str
    name: str
    description: str

class ContextsResponse(BaseModel):
    """Response model for validation contexts"""
    # Required fields only
    contexts: List[Context]

class ErrorResponse(BaseModel):
    """Response model for API errors"""
    # Required fields first
    error: Dict[str, Any]  # Contains code, message, details