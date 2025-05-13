from fastapi import APIRouter, HTTPException, Query, Path, Depends, status
from typing import Optional
from uuid import UUID
import logging

from ..models.okh.request import (
    OKHCreateRequest, 
    OKHUpdateRequest, 
    OKHValidateRequest,
    OKHExtractRequest
)
from ..models.okh.response import (
    OKHResponse, 
    OKHValidationResponse, 
    OKHExtractResponse,
    OKHListResponse,
    SuccessResponse
)
from ...services.okh_service import OKHService

# Set up logging
logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(tags=["okh"])

# Dependency to get OKH service
async def get_okh_service():
    # In a real implementation, this would use dependency injection
    # or configuration to create the service
    return OKHService()

@router.post("/create", response_model=OKHResponse, status_code=status.HTTP_201_CREATED)
async def create_okh(
    request: OKHCreateRequest,
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Create a new OKH manifest
    
    Creates a new OpenKnowHow manifest with the provided data.
    The manifest describes a piece of open source hardware.
    """
    try:
        # Call service to create OKH manifest
        result = await okh_service.create(request.dict())
        return result
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error creating OKH manifest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the OKH manifest"
        )

@router.get("/{id}", response_model=OKHResponse)
async def get_okh(
    id: UUID = Path(..., title="The ID of the OKH manifest"),
    component: Optional[str] = Query(None, description="Specific component to retrieve"),
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Get an OKH manifest by ID
    
    Retrieves a specific OpenKnowHow manifest by its unique identifier.
    Optionally retrieves only a specific component of the manifest.
    """
    try:
        # Call service to get OKH manifest
        result = await okh_service.get(id, component)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKH manifest with ID {id} not found"
            )
        return result
    except ValueError as e:
        # Handle invalid parameters
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error retrieving OKH manifest {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the OKH manifest"
        )

@router.get("", response_model=OKHListResponse)
async def list_okh(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    filter: Optional[str] = Query(None, description="Filter criteria (e.g., 'title=contains:Hardware')"),
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    List OKH manifests
    
    Returns a paginated list of OpenKnowHow manifests.
    Optionally filtered by the provided criteria.
    """
    try:
        # Parse filter parameter if provided
        filter_params = {}
        if filter:
            # Simple parsing for filter format: field=operator:value
            # For example: title=contains:Hardware
            parts = filter.split('=', 1)
            if len(parts) == 2:
                field, op_value = parts
                op_parts = op_value.split(':', 1)
                if len(op_parts) == 2:
                    op, value = op_parts
                    filter_params = {
                        "field": field,
                        "operator": op,
                        "value": value
                    }
        
        # Call service to list OKH manifests
        results, total = await okh_service.list(page, page_size, filter_params)
        
        return OKHListResponse(
            results=results,
            total=total,
            page=page,
            page_size=page_size
        )
    except ValueError as e:
        # Handle invalid parameters
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error listing OKH manifests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing OKH manifests"
        )

@router.put("/{id}", response_model=OKHResponse)
async def update_okh(
    request: OKHUpdateRequest,
    id: UUID = Path(..., title="The ID of the OKH manifest"),
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Update an OKH manifest
    
    Updates an existing OpenKnowHow manifest with the provided data.
    """
    try:
        # Check if manifest exists
        existing = await okh_service.get(id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKH manifest with ID {id} not found"
            )
        
        # Call service to update OKH manifest
        result = await okh_service.update(id, request.dict())
        return result
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error updating OKH manifest {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the OKH manifest"
        )

@router.delete("/{id}", response_model=SuccessResponse)
async def delete_okh(
    id: UUID = Path(..., title="The ID of the OKH manifest"),
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Delete an OKH manifest
    
    Deletes an OpenKnowHow manifest by its unique identifier.
    """
    try:
        # Check if manifest exists
        existing = await okh_service.get(id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKH manifest with ID {id} not found"
            )
        
        # Call service to delete OKH manifest
        success = await okh_service.delete(id)
        
        return SuccessResponse(
            success=success,
            message=f"OKH manifest with ID {id} deleted successfully"
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error deleting OKH manifest {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the OKH manifest"
        )

@router.post("/validate", response_model=OKHValidationResponse)
async def validate_okh(
    request: OKHValidateRequest,
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Validate an OKH object
    
    Validates an OpenKnowHow object against the schema and returns
    normalized content with validation information.
    """
    try:
        # Call service to validate OKH manifest
        result = await okh_service.validate(
            request.content, 
            request.validation_context
        )
        
        return result
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error validating OKH manifest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while validating the OKH manifest"
        )

@router.post("/extract", response_model=OKHExtractResponse)
async def extract_requirements(
    request: OKHExtractRequest,
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Extract requirements from an OKH object
    
    Extracts process requirements from an OpenKnowHow object for matching.
    """
    try:
        # Call service to extract requirements
        requirements = await okh_service.extract_requirements(request.content)
        
        return OKHExtractResponse(requirements=requirements)
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error extracting requirements: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while extracting requirements"
        )