from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from uuid import UUID
from enum import Enum

class ProcessStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

class WorkflowNodeResponse(BaseModel):
    """Response model for a workflow node"""
    # Required fields first
    id: UUID
    name: str
    process_status: ProcessStatus = ProcessStatus.PENDING
    confidence_score: float = 1.0
    substitution_used: bool = False
    
    # Optional fields after
    okh_refs: List[str] = []
    okw_refs: List[str] = []
    input_requirements: Dict[str, Any] = {}
    output_specifications: Dict[str, Any] = {}
    estimated_time: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    assigned_facility: Optional[str] = None
    assigned_equipment: Optional[str] = None
    materials: List[str] = []
    metadata: Dict[str, Any] = {}

class WorkflowResponse(BaseModel):
    """Response model for a workflow"""
    # Required fields first
    id: UUID
    name: str
    nodes: Dict[str, WorkflowNodeResponse]
    edges: List[Dict[str, str]]
    entry_points: List[str]
    exit_points: List[str]

class WorkflowConnectionResponse(BaseModel):
    """Response model for a workflow connection"""
    # Required fields first
    source_workflow: str
    source_node: str
    target_workflow: str
    target_node: str
    connection_type: str
    
    # Optional fields after
    metadata: Dict[str, Any] = {}

class ResourceSnapshotResponse(BaseModel):
    """Response model for a resource snapshot"""
    # Required fields first
    uri: str
    content: Dict[str, Any]
    timestamp: str
    
    # Optional fields after
    version: Optional[str] = None

class SupplyTreeResponse(BaseModel):
    """Response model for a supply tree"""
    # Required fields first
    id: UUID
    workflows: Dict[str, WorkflowResponse]
    creation_time: str
    confidence: float = 0.0
    required_quantity: int = 1
    
    # Optional fields after
    connections: List[WorkflowConnectionResponse] = []
    snapshots: Dict[str, ResourceSnapshotResponse] = {}
    okh_reference: Optional[str] = None
    deadline: Optional[str] = None
    metadata: Dict[str, Any] = {}

class OptimizationMetrics(BaseModel):
    """Response model for optimization metrics"""
    # All optional fields
    cost: Optional[float] = None
    time: Optional[str] = None
    quality_score: Optional[float] = None

class SupplyTreeOptimizationResponse(SupplyTreeResponse):
    """Response model for optimized supply tree"""
    # Additional required field in this subclass
    optimization_metrics: OptimizationMetrics

class ValidationIssue(BaseModel):
    """Model for validation issues"""
    # Required fields first
    type: str  # "error", "warning", "info"
    message: str
    
    # Optional fields after
    path: Optional[str] = None
    component: Optional[str] = None

class ValidationResult(BaseModel):
    """Response model for validation results"""
    # Required fields first
    valid: bool
    confidence: float
    
    # Optional fields after
    issues: List[Dict[str, Any]] = []

class SupplyTreeListResponse(BaseModel):
    """Response model for listing supply trees"""
    # Required fields first
    results: List[SupplyTreeResponse]
    total: int
    page: int
    page_size: int

class SuccessResponse(BaseModel):
    """Response model for successful operations"""
    # Required fields only
    success: bool
    message: str