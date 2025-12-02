"""
Request models for Rules API endpoints.

These models define the request structures for rules management operations.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from ..base import BaseAPIRequest


class RuleListRequest(BaseAPIRequest):
    """Request for listing rules"""

    domain: Optional[str] = Field(None, description="Filter by domain")
    tag: Optional[str] = Field(None, description="Filter by tag")
    include_metadata: bool = Field(False, description="Include metadata in response")


class RuleGetRequest(BaseAPIRequest):
    """Request for getting a specific rule"""

    include_metadata: bool = Field(False, description="Include metadata in response")


class RuleCreateRequest(BaseAPIRequest):
    """Request for creating a new rule"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rule_data": {
                    "id": "cnc_machining_rule",
                    "type": "capability_match",
                    "capability": "cnc machining",
                    "satisfies_requirements": ["milling", "machining"],
                    "confidence": 0.95,
                    "domain": "manufacturing",
                    "description": "CNC machining can satisfy milling and machining requirements",
                }
            }
        }
    )

    rule_data: Dict[str, Any] = Field(..., description="Rule data dictionary")


class RuleUpdateRequest(BaseAPIRequest):
    """Request for updating an existing rule"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rule_data": {
                    "id": "cnc_machining_rule",
                    "type": "capability_match",
                    "capability": "cnc machining",
                    "satisfies_requirements": ["milling", "machining", "turning"],
                    "confidence": 0.98,
                    "domain": "manufacturing",
                }
            }
        }
    )

    rule_data: Dict[str, Any] = Field(..., description="Updated rule data dictionary")


class RuleDeleteRequest(BaseAPIRequest):
    """Request for deleting a rule"""

    confirm: bool = Field(False, description="Confirmation flag")


class RuleImportRequest(BaseAPIRequest):
    """Request for importing rules from file or reloading from filesystem"""

    file_content: Optional[str] = Field(
        None, description="File content to import (omit to reload from filesystem)"
    )
    file_format: Optional[str] = Field(
        None,
        description="File format: 'yaml' or 'json' (required if file_content provided)",
    )
    domain: Optional[str] = Field(
        None, description="Target domain (if importing/reloading single domain)"
    )
    partial_update: bool = Field(
        True,
        description="Allow partial updates (merge vs replace, only for file import)",
    )
    dry_run: bool = Field(
        False,
        description="Validate and compare without applying changes (only for file import)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_content": "domain: manufacturing\nversion: 1.0.0\nrules:\n  ...",
                "file_format": "yaml",
                "partial_update": True,
                "dry_run": False,
            }
        }
    )


class RuleExportRequest(BaseAPIRequest):
    """Request for exporting rules"""

    domain: Optional[str] = Field(
        None, description="Export specific domain (all if not specified)"
    )
    format: str = Field("yaml", description="Export format: 'yaml' or 'json'")
    include_metadata: bool = Field(False, description="Include metadata in export")


class RuleValidateRequest(BaseAPIRequest):
    """Request for validating rule file content"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_content": "domain: manufacturing\nversion: 1.0.0\nrules:\n  ...",
                "file_format": "yaml",
            }
        }
    )

    file_content: str = Field(..., description="File content to validate")
    file_format: str = Field(..., description="File format: 'yaml' or 'json'")


class RuleCompareRequest(BaseAPIRequest):
    """Request for comparing rules file with current rules"""

    file_content: str = Field(..., description="File content to compare")
    file_format: str = Field(..., description="File format: 'yaml' or 'json'")
    domain: Optional[str] = Field(None, description="Compare specific domain")


class RuleResetRequest(BaseAPIRequest):
    """Request for resetting all rules"""

    confirm: bool = Field(False, description="Confirmation flag")
