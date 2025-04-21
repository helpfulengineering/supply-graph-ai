from pydantic import BaseModel, Field
from typing import Dict, Any, List
from uuid import UUID, uuid4

class ProcessNode(BaseModel):
    id: UUID
    name: str
    inputs: List[str]
    outputs: List[str]
    requirements: Dict[str, Any]
    capabilities: Dict[str, Any]

class Workflow(BaseModel):
    id: UUID
    name: str
    nodes: Dict[str, ProcessNode]
    edges: List[Dict[str, UUID]]

class SupplyTreeResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    domain: str
    workflows: Dict[str, Workflow]
    confidence: float
    validation_status: bool
    metadata: Dict[str, Any] = {}