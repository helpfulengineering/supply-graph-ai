"""
Rules Management API Routes

This module provides API endpoints for managing capability rules.
All endpoints are under /api/match/rules to align with the matching domain.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Path, Query, Request
from typing import Optional
import yaml
import json

# Import standardized components
from ..models.base import SuccessResponse
from ..decorators import (
    api_endpoint,
    track_performance
)
from ..error_handlers import create_success_response

# Import rules models
from ..models.rules.request import (
    RuleCreateRequest,
    RuleUpdateRequest,
    RuleImportRequest,
    RuleValidateRequest,
    RuleCompareRequest
)
from ..models.rules.response import (
    RuleResponse,
    RuleListResponse,
    RuleImportResponse,
    RuleExportResponse,
    RuleValidateResponse,
    RuleCompareResponse
)

# Import services
from ...matching.rules_service import RulesService
from ...matching.import_export_service import ImportExportService
from ...matching.validation import ValidationService
from ...matching.capability_rules import CapabilityRuleManager

from ...utils.logging import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/api/match/rules",
    tags=["rules"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)


# Service dependencies
_rule_manager: Optional[CapabilityRuleManager] = None
_rules_service: Optional[RulesService] = None
_import_export_service: Optional[ImportExportService] = None


async def get_rule_manager() -> CapabilityRuleManager:
    """Get rule manager instance"""
    global _rule_manager
    if _rule_manager is None:
        _rule_manager = CapabilityRuleManager()
        await _rule_manager.initialize()
    return _rule_manager


async def get_rules_service() -> RulesService:
    """Get rules service instance"""
    global _rules_service
    if _rules_service is None:
        rule_manager = await get_rule_manager()
        validation_service = ValidationService()
        _rules_service = RulesService(rule_manager, validation_service)
        await _rules_service.initialize()
    return _rules_service


async def get_import_export_service() -> ImportExportService:
    """Get import/export service instance"""
    global _import_export_service
    if _import_export_service is None:
        rule_manager = await get_rule_manager()
        validation_service = ValidationService()
        rules_service = RulesService(rule_manager, validation_service)
        await rules_service.initialize()
        _import_export_service = ImportExportService(validation_service, rules_service)
    return _import_export_service


# Endpoints

@router.get("/", response_model=RuleListResponse, summary="List all rules")
@api_endpoint(success_message="Rules retrieved successfully")
@track_performance("rules_list")
async def list_rules(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    include_metadata: bool = Query(False, description="Include metadata"),
    service: RulesService = Depends(get_rules_service)
):
    """List all rules, optionally filtered by domain or tag"""
    try:
        result = await service.list_rules(
            domain=domain,
            tag=tag,
            include_metadata=include_metadata
        )
        return create_success_response(
            message="Rules retrieved successfully",
            data=result
        )
    except Exception as e:
        logger.exception("Error listing rules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list rules: {str(e)}"
        )


@router.get("/{domain}/{rule_id}", response_model=RuleResponse, summary="Get a specific rule")
@api_endpoint(success_message="Rule retrieved successfully")
@track_performance("rules_get")
async def get_rule(
    domain: str = Path(..., description="Domain name"),
    rule_id: str = Path(..., description="Rule ID"),
    include_metadata: bool = Query(False, description="Include metadata"),
    service: RulesService = Depends(get_rules_service)
):
    """Get a specific rule by domain and ID"""
    try:
        rule = await service.get_rule(domain, rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{rule_id}' not found in domain '{domain}'"
            )
        
        rule_dict = rule.to_dict(include_metadata=include_metadata)
        return create_success_response(
            message="Rule retrieved successfully",
            data=rule_dict
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting rule")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rule: {str(e)}"
        )


@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED, summary="Create a new rule")
@api_endpoint(success_message="Rule created successfully")
@track_performance("rules_create")
async def create_rule(
    request: RuleCreateRequest,
    http_request: Request,
    service: RulesService = Depends(get_rules_service)
):
    """Create a new rule"""
    try:
        rule = await service.create_rule(request.rule_data)
        rule_dict = rule.to_dict(include_metadata=False)
        response = create_success_response(
            message="Rule created successfully",
            data=rule_dict
        )
        # Set status code for 201 Created
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=response.model_dump(mode='json'),
            status_code=status.HTTP_201_CREATED
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Error creating rule")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create rule: {str(e)}"
        )


@router.put("/{domain}/{rule_id}", response_model=RuleResponse, summary="Update an existing rule")
@api_endpoint(success_message="Rule updated successfully")
@track_performance("rules_update")
async def update_rule(
    domain: str = Path(..., description="Domain name"),
    rule_id: str = Path(..., description="Rule ID"),
    request: RuleUpdateRequest = ...,
    http_request: Request = None,
    service: RulesService = Depends(get_rules_service)
):
    """Update an existing rule"""
    try:
        # Ensure rule_id and domain match path parameters
        request.rule_data["id"] = rule_id
        request.rule_data["domain"] = domain
        
        rule = await service.update_rule(domain, rule_id, request.rule_data)
        rule_dict = rule.to_dict(include_metadata=False)
        return create_success_response(
            message="Rule updated successfully",
            data=rule_dict
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Error updating rule")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update rule: {str(e)}"
        )


@router.delete("/{domain}/{rule_id}", response_model=SuccessResponse, summary="Delete a rule")
@api_endpoint(success_message="Rule deleted successfully")
@track_performance("rules_delete")
async def delete_rule(
    domain: str = Path(..., description="Domain name"),
    rule_id: str = Path(..., description="Rule ID"),
    confirm: bool = Query(False, description="Confirmation flag"),
    service: RulesService = Depends(get_rules_service)
):
    """Delete a rule"""
    try:
        if not confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation required. Set 'confirm=true' to delete."
            )
        
        result = await service.delete_rule(domain, rule_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{rule_id}' not found in domain '{domain}'"
            )
        
        return create_success_response(
            message="Rule deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting rule")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete rule: {str(e)}"
        )


@router.post("/import", response_model=RuleImportResponse, summary="Import rules from file")
@api_endpoint(success_message="Rules imported successfully")
@track_performance("rules_import")
async def import_rules(
    request: RuleImportRequest,
    http_request: Request = None,
    service: ImportExportService = Depends(get_import_export_service)
):
    """Import rules from YAML or JSON file content"""
    try:
        result = await service.import_rules(
            file_content=request.file_content,
            file_format=request.file_format,
            domain=request.domain,
            partial_update=request.partial_update,
            dry_run=request.dry_run
        )
        
        message = "Rules imported successfully" if not result.get("dry_run") else "Rules comparison completed"
        return create_success_response(
            message=message,
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Error importing rules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import rules: {str(e)}"
        )


@router.post("/export", response_model=RuleExportResponse, summary="Export rules to file")
@api_endpoint(success_message="Rules exported successfully")
@track_performance("rules_export")
async def export_rules(
    domain: Optional[str] = Query(None, description="Export specific domain"),
    format: str = Query("yaml", description="Export format: 'yaml' or 'json'"),
    include_metadata: bool = Query(False, description="Include metadata"),
    service: ImportExportService = Depends(get_import_export_service)
):
    """Export rules to YAML or JSON format"""
    try:
        content, metadata = await service.export_rules(
            domain=domain,
            format=format,
            include_metadata=include_metadata
        )
        
        result = {
            "content": content,
            **metadata
        }
        
        return create_success_response(
            message="Rules exported successfully",
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Error exporting rules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export rules: {str(e)}"
        )


@router.post("/validate", response_model=RuleValidateResponse, summary="Validate rule file")
@api_endpoint(success_message="Validation completed")
@track_performance("rules_validate")
async def validate_rules(
    request: RuleValidateRequest,
    http_request: Request = None,
    service: ImportExportService = Depends(get_import_export_service)
):
    """Validate rule file content without importing"""
    try:
        # Parse file to get rule set data
        if request.file_format.lower() == 'yaml':
            data = yaml.safe_load(request.file_content)
        elif request.file_format.lower() == 'json':
            data = json.loads(request.file_content)
        else:
            raise ValueError(f"Unsupported file format: {request.file_format}")
        
        # Handle multi-domain format
        if "domains" in data:
            # Validate all domains
            validation_service = ValidationService()
            all_results = {}
            for dom, domain_data in data["domains"].items():
                result = await validation_service.validate_rule_set(domain_data)
                all_results[dom] = result
            
            # Aggregate results
            all_valid = all(r["valid"] for r in all_results.values())
            all_errors = []
            all_warnings = []
            for dom, result in all_results.items():
                all_errors.extend([f"{dom}: {e}" for e in result["errors"]])
                all_warnings.extend([f"{dom}: {w}" for w in result["warnings"]])
            
            result = {
                "valid": all_valid,
                "errors": all_errors,
                "warnings": all_warnings
            }
        else:
            # Single domain format
            validation_service = ValidationService()
            result = await validation_service.validate_rule_set(data)
        
        return create_success_response(
            message="Validation completed",
            data=result
        )
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(e)}"
        )
    except Exception as e:
        logger.exception("Error validating rules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate rules: {str(e)}"
        )


@router.post("/compare", response_model=RuleCompareResponse, summary="Compare rules file with current rules")
@api_endpoint(success_message="Comparison completed")
@track_performance("rules_compare")
async def compare_rules(
    request: RuleCompareRequest,
    http_request: Request = None,
    service: ImportExportService = Depends(get_import_export_service)
):
    """Compare rules file with current rules (dry-run)"""
    try:
        result = await service.compare_rules(
            file_content=request.file_content,
            file_format=request.file_format,
            domain=request.domain
        )
        
        return create_success_response(
            message="Comparison completed",
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Error comparing rules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare rules: {str(e)}"
        )


@router.post("/reset", response_model=SuccessResponse, summary="Reset all rules")
@api_endpoint(success_message="Rules reset successfully")
@track_performance("rules_reset")
async def reset_rules(
    confirm: bool = Query(False, description="Confirmation flag"),
    service: RulesService = Depends(get_rules_service)
):
    """Reset all rules (clear all rule sets)"""
    try:
        if not confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation required. Set 'confirm=true' to reset all rules."
            )
        
        await service.reset_rules()
        return create_success_response(
            message="Rules reset successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error resetting rules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset rules: {str(e)}"
        )

