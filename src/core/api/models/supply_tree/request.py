from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from uuid import UUID

class WorkflowNodeRequest(BaseModel):
    """Request model for a workflow node"""
    # Required fields first
    name: str
    
    # Optional fields after
    id: Optional[UUID] = None
    okh_refs: List[str] = Field(default_factory=list)
    okw_refs: List[str] = Field(default_factory=list)
    input_requirements: Dict[str, Any] = Field(default_factory=dict)
    output_specifications: Dict[str, Any] = Field(default_factory=dict)
    estimated_time: Optional[str] = None
    assigned_facility: Optional[str] = None
    assigned_equipment: Optional[str] = None
    materials: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkflowRequest(BaseModel):
    """Request model for a workflow"""
    # Required fields first
    name: str
    
    # Optional fields after
    id: Optional[UUID] = None
    nodes: Dict[str, WorkflowNodeRequest] = Field(default_factory=dict)
    edges: List[Dict[str, str]] = Field(default_factory=list)

class WorkflowConnectionRequest(BaseModel):
    """Request model for a workflow connection"""
    # Required fields first
    source_workflow: str
    source_node: str
    target_workflow: str
    target_node: str
    connection_type: str
    
    # Optional fields after
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SupplyTreeOptimizeRequest(BaseModel):
    """Request model for optimizing a supply tree"""
    # Required fields only
    criteria: Dict[str, Any]

class SupplyTreeCreateRequest(BaseModel):
    """Request model for creating a supply tree"""
    # Optional fields (none are strictly required for initial creation)
    workflows: Dict[str, WorkflowRequest] = Field(default_factory=dict)
    connections: List[WorkflowConnectionRequest] = Field(default_factory=list)
    okh_reference: Optional[str] = None
    required_quantity: int = 1
    deadline: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SupplyTreeValidateRequest(BaseModel):
    """Request model for validating a supply tree"""
    # Optional fields
    okh_reference: Optional[str] = None
    okw_references: Optional[List[str]] = None