"""
Response models for Rules API endpoints.

These models define the response structures for rules management operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..base import APIStatus, SuccessResponse


class RuleResponse(SuccessResponse):
    """Response containing a single rule"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Rule retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {
                    "id": "cnc_machining_rule",
                    "type": "capability_match",
                    "capability": "cnc machining",
                    "satisfies_requirements": ["milling", "machining"],
                    "confidence": 0.95,
                    "domain": "manufacturing",
                },
            }
        }
    )

    data: Dict[str, Any] = Field(..., description="Rule data")


class RuleListResponse(SuccessResponse):
    """Response containing a list of rules"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Rules retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {
                    "rules": [
                        {
                            "id": "rule1",
                            "capability": "cnc machining",
                            "domain": "manufacturing",
                        }
                    ],
                    "total": 42,
                    "domains": ["manufacturing", "cooking"],
                },
            }
        }
    )

    data: Dict[str, Any] = Field(..., description="Rules data with metadata")


class RuleImportResponse(SuccessResponse):
    """Response from rule import operation"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Rules imported successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {
                    "imported_rules": 10,
                    "updated_rules": 2,
                    "errors": [],
                    "dry_run": False,
                },
            }
        }
    )

    data: Dict[str, Any] = Field(..., description="Import results")


class RuleExportResponse(SuccessResponse):
    """Response from rule export operation"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Rules exported successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {
                    "content": "domain: manufacturing\n...",
                    "format": "yaml",
                    "domain": "manufacturing",
                    "rule_count": 15,
                },
            }
        }
    )

    data: Dict[str, Any] = Field(..., description="Export data")


class RuleValidateResponse(SuccessResponse):
    """Response from rule validation"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Validation completed",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {"valid": True, "errors": [], "warnings": []},
            }
        }
    )

    data: Dict[str, Any] = Field(..., description="Validation results")


class RuleCompareResponse(SuccessResponse):
    """Response from rule comparison (dry-run)"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Comparison completed",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {
                    "changes": {
                        "added": ["new_rule_1", "new_rule_2"],
                        "updated": ["existing_rule_1"],
                        "deleted": [],
                    },
                    "summary": {
                        "total_added": 2,
                        "total_updated": 1,
                        "total_deleted": 0,
                    },
                },
            }
        }
    )

    data: Dict[str, Any] = Field(..., description="Comparison results")
