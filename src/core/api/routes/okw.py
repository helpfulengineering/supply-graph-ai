from fastapi import APIRouter, HTTPException, Query, Path, status, Depends, UploadFile, File, Form
from typing import Optional, List
from uuid import UUID
import logging
import json
import yaml

from ..models.okw.request import (
    OKWCreateRequest, 
    OKWUpdateRequest, 
    OKWValidateRequest,
    OKWExtractRequest
)
from ..models.okw.response import (
    OKWResponse, 
    OKWValidationResponse, 
    OKWExtractResponse,
    OKWListResponse,
    SuccessResponse,
    OKWUploadResponse
)
from ...services.storage_service import StorageService
from ...services.okw_service import OKWService
from ...models.okw import ManufacturingFacility
from ...utils.logging import get_logger

# Set up logging
logger = get_logger(__name__)

# Create router with prefix and tags
router = APIRouter(tags=["okw"])

async def get_storage_service() -> StorageService:
    return await StorageService.get_instance()

# Dependency to get OKW service
async def get_okw_service():
    return await OKWService.get_instance()

@router.post("/create", response_model=OKWResponse, status_code=status.HTTP_201_CREATED)
async def create_okw(
    request: OKWCreateRequest,
    okw_service: OKWService = Depends(get_okw_service)
):
    """Create a new OKW facility"""
    try:
        # Convert request to facility data
        facility_data = request.dict()
        
        # Create facility using service
        facility = await okw_service.create(facility_data)
        
        # Convert to response format
        location_dict = facility.location.to_dict() if hasattr(facility.location, 'to_dict') else {
            "address": facility.location.address.to_dict() if hasattr(facility.location.address, 'to_dict') else {
                "street": getattr(facility.location.address, 'street', ''),
                "city": getattr(facility.location.address, 'city', ''),
                "region": getattr(facility.location.address, 'region', ''),
                "postal_code": getattr(facility.location.address, 'postal_code', ''),
                "country": getattr(facility.location.address, 'country', '')
            },
            "coordinates": {
                "latitude": getattr(facility.location, 'latitude', None),
                "longitude": getattr(facility.location, 'longitude', None)
            }
        }
        
        return {
            "id": str(facility.id),
            "name": facility.name,
            "location": location_dict,
            "facility_status": facility.facility_status,
            "access_type": facility.access_type,
            "manufacturing_processes": facility.manufacturing_processes,
            "equipment": [eq.to_dict() for eq in facility.equipment] if facility.equipment else [],
            "typical_materials": [mat.to_dict() for mat in facility.typical_materials] if facility.typical_materials else []
        }
        
    except Exception as e:
        logger.error(f"Error creating OKW facility: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating OKW facility: {str(e)}")

@router.get("/search", response_model=OKWListResponse)
async def search_okw(
    location: Optional[str] = Query(None, description="Geographic location to search near"),
    capabilities: Optional[List[str]] = Query(None, description="Required capabilities"),
    materials: Optional[List[str]] = Query(None, description="Required materials"),
    access_type: Optional[str] = Query(None, description="Access type filter"),
    facility_status: Optional[str] = Query(None, description="Facility status filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Search for facilities by criteria"""
    try:
        # Load OKW facilities from storage (same logic as matching route)
        facilities = []
        try:
            # Get all objects from storage (these are the actual OKW files)
            objects = []
            async for obj in storage_service.manager.list_objects():
                objects.append(obj)
            
            logger.info(f"Found {len(objects)} objects in storage")
            
            # Load and parse each OKW file
            for obj in objects:
                try:
                    # Read the file content
                    data = await storage_service.manager.get_object(obj["key"])
                    content = data.decode('utf-8')
                    
                    # Parse based on file extension
                    if obj["key"].endswith(('.yaml', '.yml')):
                        okw_data = yaml.safe_load(content)
                    elif obj["key"].endswith('.json'):
                        okw_data = json.loads(content)
                    else:
                        logger.warning(f"Skipping unsupported file format: {obj['key']}")
                        continue
                    
                    # Create ManufacturingFacility object
                    facility = ManufacturingFacility.from_dict(okw_data)
                    facilities.append(facility)
                    logger.debug(f"Loaded OKW facility from {obj['key']}: {facility.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to load OKW facility from {obj['key']}: {e}")
                    continue
            
            logger.info(f"Loaded {len(facilities)} OKW facilities from storage.")
        except Exception as e:
            logger.error(f"Failed to list/load OKW facilities: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load OKW facilities: {str(e)}")

        # Apply search filters
        filtered_facilities = []
        logger.info(f"Applying filters: access_type='{access_type}', facility_status='{facility_status}', location='{location}'")
        
        for facility in facilities:
            logger.debug(f"Checking facility: {facility.name} (access_type: {facility.access_type})")
            
            # Location filter
            if location and location.lower() not in str(facility.location).lower():
                logger.debug(f"  Filtered out by location: {facility.name}")
                continue
            
            # Capabilities filter
            if capabilities:
                facility_capabilities = [cap.get("name", "").lower() for cap in facility.equipment]
                if not any(cap.lower() in facility_capabilities for cap in capabilities):
                    logger.debug(f"  Filtered out by capabilities: {facility.name}")
                    continue
            
            # Materials filter
            if materials:
                facility_materials = [mat.lower() for mat in facility.typical_materials]
                if not any(mat.lower() in facility_materials for mat in materials):
                    logger.debug(f"  Filtered out by materials: {facility.name}")
                    continue
            
            # Access type filter
            if access_type:
                facility_access_type = facility.access_type.value.lower()
                filter_access_type = access_type.lower()
                logger.debug(f"  Comparing access_type: '{facility_access_type}' vs '{filter_access_type}'")
                if facility_access_type != filter_access_type:
                    logger.debug(f"  Filtered out by access_type: {facility.name}")
                    continue
            
            # Facility status filter
            if facility_status and facility.facility_status.value.lower() != facility_status.lower():
                logger.debug(f"  Filtered out by facility_status: {facility.name}")
                continue
            
            logger.debug(f"  Facility passed all filters: {facility.name}")
            filtered_facilities.append(facility)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_facilities = filtered_facilities[start_idx:end_idx]
        
        # Convert to response format
        results = []
        for facility in paginated_facilities:
            # Convert Location object to dict for serialization
            location_dict = facility.location.to_dict() if hasattr(facility.location, 'to_dict') else {
                "address": facility.location.address.to_dict() if hasattr(facility.location.address, 'to_dict') else {
                    "street": getattr(facility.location.address, 'street', ''),
                    "city": getattr(facility.location.address, 'city', ''),
                    "region": getattr(facility.location.address, 'region', ''),
                    "postal_code": getattr(facility.location.address, 'postal_code', ''),
                    "country": getattr(facility.location.address, 'country', '')
                },
                "coordinates": {
                    "latitude": getattr(facility.location, 'latitude', None),
                    "longitude": getattr(facility.location, 'longitude', None)
                }
            }
            
            results.append({
                "id": str(facility.id),
                "name": facility.name,
                "location": location_dict,
                "facility_status": facility.facility_status,
                "access_type": facility.access_type,
                "manufacturing_processes": facility.manufacturing_processes,
                "equipment": facility.equipment,
                "typical_materials": facility.typical_materials
            })
        
        return OKWListResponse(
            results=results,
            total=len(filtered_facilities),
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error searching OKW facilities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching OKW facilities: {str(e)}")

@router.get("/{id}", response_model=OKWResponse)
async def get_okw(
    id: UUID = Path(..., title="The ID of the OKW facility"),
    okw_service: OKWService = Depends(get_okw_service)
):
    """Get an OKW facility by ID"""
    try:
        facility = await okw_service.get(id)
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKW facility with ID {id} not found"
            )
        
        # Convert to response format
        location_dict = facility.location.to_dict() if hasattr(facility.location, 'to_dict') else {
            "address": facility.location.address.to_dict() if hasattr(facility.location.address, 'to_dict') else {
                "street": getattr(facility.location.address, 'street', ''),
                "city": getattr(facility.location.address, 'city', ''),
                "region": getattr(facility.location.address, 'region', ''),
                "postal_code": getattr(facility.location.address, 'postal_code', ''),
                "country": getattr(facility.location.address, 'country', '')
            },
            "coordinates": {
                "latitude": getattr(facility.location, 'latitude', None),
                "longitude": getattr(facility.location, 'longitude', None)
            }
        }
        
        return {
            "id": str(facility.id),
            "name": facility.name,
            "location": location_dict,
            "facility_status": facility.facility_status,
            "access_type": facility.access_type,
            "manufacturing_processes": facility.manufacturing_processes,
            "equipment": [eq.to_dict() for eq in facility.equipment] if facility.equipment else [],
            "typical_materials": [mat.to_dict() for mat in facility.typical_materials] if facility.typical_materials else []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting OKW facility {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting OKW facility: {str(e)}")

@router.get("", response_model=OKWListResponse)
async def list_okw(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    filter: Optional[str] = Query(None, description="Filter criteria"),
    okw_service: OKWService = Depends(get_okw_service)
):
    """List OKW facilities from storage"""
    try:
        # Call service to list OKW facilities
        facilities, total = await okw_service.list(page, page_size, None)
        
        # Convert ManufacturingFacility objects to response format
        results = []
        for facility in facilities:
            # Convert Location object to dict for serialization
            location_dict = facility.location.to_dict() if hasattr(facility.location, 'to_dict') else {
                "address": facility.location.address.to_dict() if hasattr(facility.location.address, 'to_dict') else {
                    "street": getattr(facility.location.address, 'street', ''),
                    "city": getattr(facility.location.address, 'city', ''),
                    "region": getattr(facility.location.address, 'region', ''),
                    "postal_code": getattr(facility.location.address, 'postal_code', ''),
                    "country": getattr(facility.location.address, 'country', '')
                },
                "coordinates": {
                    "latitude": getattr(facility.location, 'latitude', None),
                    "longitude": getattr(facility.location, 'longitude', None)
                }
            }
            
            results.append({
                "id": str(facility.id),
                "name": facility.name,
                "location": location_dict,
                "facility_status": facility.facility_status,
                "access_type": facility.access_type,
                "manufacturing_processes": facility.manufacturing_processes,
                "equipment": facility.equipment,
                "typical_materials": facility.typical_materials
            })
        
        return OKWListResponse(
            results=results,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing OKW facilities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing OKW facilities: {str(e)}")

@router.put("/{id}", response_model=OKWResponse)
async def update_okw(
    request: OKWUpdateRequest,
    id: UUID = Path(..., title="The ID of the OKW facility"),
    okw_service: OKWService = Depends(get_okw_service)
):
    """Update an OKW facility"""
    try:
        # Check if facility exists
        existing_facility = await okw_service.get(id)
        if not existing_facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKW facility with ID {id} not found"
            )
        
        # Convert request to facility data
        facility_data = request.dict()
        facility_data["id"] = str(id)  # Ensure ID is preserved
        
        # Update facility using service
        facility = await okw_service.update(id, facility_data)
        
        # Convert to response format
        location_dict = facility.location.to_dict() if hasattr(facility.location, 'to_dict') else {
            "address": facility.location.address.to_dict() if hasattr(facility.location.address, 'to_dict') else {
                "street": getattr(facility.location.address, 'street', ''),
                "city": getattr(facility.location.address, 'city', ''),
                "region": getattr(facility.location.address, 'region', ''),
                "postal_code": getattr(facility.location.address, 'postal_code', ''),
                "country": getattr(facility.location.address, 'country', '')
            },
            "coordinates": {
                "latitude": getattr(facility.location, 'latitude', None),
                "longitude": getattr(facility.location, 'longitude', None)
            }
        }
        
        return {
            "id": str(facility.id),
            "name": facility.name,
            "location": location_dict,
            "facility_status": facility.facility_status,
            "access_type": facility.access_type,
            "manufacturing_processes": facility.manufacturing_processes,
            "equipment": [eq.to_dict() for eq in facility.equipment] if facility.equipment else [],
            "typical_materials": [mat.to_dict() for mat in facility.typical_materials] if facility.typical_materials else []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating OKW facility {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating OKW facility: {str(e)}")

@router.delete("/{id}", response_model=SuccessResponse)
async def delete_okw(
    id: UUID = Path(..., title="The ID of the OKW facility"),
    okw_service: OKWService = Depends(get_okw_service)
):
    """Delete an OKW facility"""
    try:
        # Check if facility exists
        existing_facility = await okw_service.get(id)
        if not existing_facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKW facility with ID {id} not found"
            )
        
        # Delete facility using service
        success = await okw_service.delete(id)
        
        if success:
            return SuccessResponse(
                success=True,
                message=f"OKW facility with ID {id} deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete OKW facility with ID {id}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting OKW facility {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting OKW facility: {str(e)}")

@router.post("/validate", response_model=OKWValidationResponse)
async def validate_okw(request: OKWValidateRequest):
    """Validate an OKW object"""
    # Placeholder implementation
    return OKWValidationResponse(
        valid=True,
        normalized_content=request.content
    )

@router.post("/extract", response_model=OKWExtractResponse)
async def extract_capabilities(request: OKWExtractRequest):
    """Extract capabilities from an OKW object"""
    # Placeholder implementation
    return OKWExtractResponse(
        capabilities=[]  # Return empty list for now
    )

@router.post("/upload", response_model=OKWUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_okw_file(
    okw_file: UploadFile = File(..., description="OKW file (YAML or JSON)"),
    description: Optional[str] = Form(None, description="Optional description for the uploaded OKW"),
    tags: Optional[str] = Form(None, description="Comma-separated list of tags"),
    validation_context: Optional[str] = Form(None, description="Validation context (e.g., 'manufacturing', 'hobby')"),
    okw_service: OKWService = Depends(get_okw_service)
):
    """
    Upload an OKW file
    
    Accepts a file upload (YAML or JSON) containing an OKW facility,
    validates it, and stores it for use in matching operations.
    """
    try:
        # Validate file type
        if not okw_file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        file_extension = okw_file.filename.lower().split('.')[-1]
        if file_extension not in ['yaml', 'yml', 'json']:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Please upload a YAML (.yaml, .yml) or JSON (.json) file"
            )
        
        # Read and parse the file content
        content = await okw_file.read()
        content_str = content.decode('utf-8')
        
        try:
            if file_extension == 'json':
                okw_data = json.loads(content_str)
            else:  # yaml or yml
                okw_data = yaml.safe_load(content_str)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file format: {str(e)}"
            )
        
        # Convert to ManufacturingFacility
        try:
            okw_facility = ManufacturingFacility.from_dict(okw_data)
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid OKW facility: {str(e)}"
            )
        
        # Store the OKW facility
        try:
            result = await okw_service.create(okw_facility.to_dict())
        except Exception as e:
            logger.error(f"Error storing OKW facility: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error storing OKW facility: {str(e)}"
            )
        
        # Convert result to OKWResponse format
        result_dict = result.to_dict()
        okw_response = OKWResponse(**result_dict)
        
        return OKWUploadResponse(
            success=True,
            message=f"OKW file '{okw_file.filename}' uploaded and stored successfully",
            okw=okw_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading OKW file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )