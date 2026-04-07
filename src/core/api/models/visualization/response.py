"""Response models for visualization artifacts."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..base import SuccessResponse


class VisualizationSection(BaseModel):
    """Generic visualization section for additive contract evolution."""

    model_config = ConfigDict(extra="allow")


class VisualizationBundleData(BaseModel):
    """Top-level visualization payload."""

    schema_version: str = Field(..., description="Visualization contract version.")
    source_type: str = Field(..., description="Source domain of this bundle.")
    generated_at: str = Field(..., description="ISO8601 generation timestamp.")
    matching: Optional[Dict[str, Any]] = None
    supply_tree: Optional[Dict[str, Any]] = None
    network: Optional[Dict[str, Any]] = None
    dashboard: Optional[Dict[str, Any]] = None
    artifacts: Dict[str, Any] = Field(default_factory=dict)


class VisualizationBundleResponse(SuccessResponse):
    """Standard success envelope for visualization payloads."""

    data: VisualizationBundleData
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Visualization bundle created successfully",
                "timestamp": "2026-04-07T00:00:00Z",
                "request_id": "req_123",
                "data": {
                    "schema_version": "3.2.0",
                    "source_type": "supply_tree_solution",
                    "generated_at": "2026-04-07T00:00:00Z",
                    "matching": {"overview": {"total_solutions": 4}},
                    "supply_tree": {"nodes": [], "edges": []},
                    "network": {"facility_distribution": []},
                    "dashboard": {"kpis": {}},
                    "artifacts": {
                        "graphml_endpoint": "/v1/api/supply-tree/solution/{id}/export?format=graphml"
                    },
                },
                "metadata": {"contract_family": "visualization"},
            }
        }
    )
