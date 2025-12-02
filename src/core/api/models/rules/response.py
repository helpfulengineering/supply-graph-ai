"""
Response models for Rules API endpoints.

These models define the response structures for rules management operations.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from ..base import SuccessResponse, APIStatus


class RuleResponse(SuccessResponse):
    """Response containing a single rule"""
    data: Dict[str, Any] = Field(..., description="Rule data")
    
    class Config:
        json_schema_extra = {
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
                    "domain": "manufacturing"
                }
            }
        }


class RuleListResponse(SuccessResponse):
    """Response containing a list of rules"""
    data: Dict[str, Any] = Field(..., description="Rules data with metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Rules retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {
                    "rules": [
                        {
                            "id": "rule1",
                            "capability": "cnc machining",
                            "domain": "manufacturing"
                        }
                    ],
                    "total": 42,
                    "domains": ["manufacturing", "cooking"]
                }
            }
        }


class RuleImportResponse(SuccessResponse):
    """Response from rule import operation"""
    data: Dict[str, Any] = Field(..., description="Import results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Rules imported successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {
                    "imported_rules": 10,
                    "updated_rules": 2,
                    "errors": [],
                    "dry_run": False
                }
            }
        }


class RuleExportResponse(SuccessResponse):
    """Response from rule export operation"""
    data: Dict[str, Any] = Field(..., description="Export data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Rules exported successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {
                    "content": "domain: manufacturing\n...",
                    "format": "yaml",
                    "domain": "manufacturing",
                    "rule_count": 15
                }
            }
        }


class RuleValidateResponse(SuccessResponse):
    """Response from rule validation"""
    data: Dict[str, Any] = Field(..., description="Validation results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Validation completed",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {
                    "valid": True,
                    "errors": [],
                    "warnings": []
                }
            }
        }


class RuleCompareResponse(SuccessResponse):
    """Response from rule comparison (dry-run)"""
    data: Dict[str, Any] = Field(..., description="Comparison results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Comparison completed",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {
                    "changes": {
                        "added": ["new_rule_1", "new_rule_2"],
                        "updated": ["existing_rule_1"],
                        "deleted": []
                    },
                    "summary": {
                        "total_added": 2,
                        "total_updated": 1,
                        "total_deleted": 0
                    }
                }
            }
        }

