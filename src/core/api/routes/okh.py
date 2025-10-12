from fastapi import APIRouter, HTTPException, Query, Path, Depends, status, UploadFile, File, Form
from typing import Optional
from uuid import UUID
import logging
import json
import yaml

from ..models.okh.request import (
    OKHCreateRequest, 
    OKHUpdateRequest, 
    OKHValidateRequest,
    OKHExtractRequest,
    OKHUploadRequest
)
from ..models.okh.response import (
    OKHResponse, 
    OKHValidationResponse, 
    OKHExtractResponse,
    OKHListResponse,
    SuccessResponse,
    OKHUploadResponse
)
from ...services.okh_service import OKHService
from ...services.storage_service import StorageService
from src.config import settings

# Set up logging
logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(tags=["okh"])

# Dependency to get OKH service
async def get_okh_service():
    return await OKHService.get_instance()

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
        result = await okh_service.create(request.model_dump())
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
        result = await okh_service.get(id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKH manifest with ID {id} not found"
            )
        
        # Convert OKHManifest to OKHResponse
        manifest_dict = result.to_dict()
        return OKHResponse(**manifest_dict)
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
        manifests, total = await okh_service.list(page, page_size, filter_params)
        
        # Convert OKHManifest objects to OKHResponse objects
        results = []
        for manifest in manifests:
            # Convert OKHManifest to dict, then to OKHResponse
            manifest_dict = manifest.to_dict()
            results.append(OKHResponse(**manifest_dict))
        
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
        result = await okh_service.update(id, request.model_dump())
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

@router.post("/upload", response_model=OKHUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_okh_file(
    okh_file: UploadFile = File(..., description="OKH file (YAML or JSON)"),
    description: Optional[str] = Form(None, description="Optional description for the uploaded OKH"),
    tags: Optional[str] = Form(None, description="Comma-separated list of tags"),
    validation_context: Optional[str] = Form(None, description="Validation context (e.g., 'manufacturing', 'hobby')"),
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Upload an OKH file
    
    Accepts a file upload (YAML or JSON) containing an OKH manifest,
    validates it, and stores it for use in matching operations.
    """
    try:
        # Validate file type
        if not okh_file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        file_extension = okh_file.filename.lower().split('.')[-1]
        if file_extension not in ['yaml', 'yml', 'json']:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Please upload a YAML (.yaml, .yml) or JSON (.json) file"
            )
        
        # Read and parse the file content
        content = await okh_file.read()
        content_str = content.decode('utf-8')
        
        try:
            if file_extension == 'json':
                okh_data = json.loads(content_str)
            else:  # yaml or yml
                okh_data = yaml.safe_load(content_str)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file format: {str(e)}"
            )
        
        # Convert to OKHManifest
        try:
            from ...models.okh import OKHManifest
            okh_manifest = OKHManifest.from_dict(okh_data)
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid OKH manifest: {str(e)}"
            )
        
        # Validate the manifest
        try:
            okh_manifest.validate()
        except ValueError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"OKH validation failed: {str(e)}"
            )
        
        # Store the OKH manifest
        try:
            result = await okh_service.create(okh_manifest.to_dict())
        except Exception as e:
            logger.error(f"Error storing OKH manifest: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error storing OKH manifest: {str(e)}"
            )
        
        # Convert result to OKHResponse format
        result_dict = result.to_dict()
        okh_response = OKHResponse(**result_dict)
        
        return OKHUploadResponse(
            success=True,
            message=f"OKH file '{okh_file.filename}' uploaded and stored successfully",
            okh=okh_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading OKH file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )