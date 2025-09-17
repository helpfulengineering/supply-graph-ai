from fastapi import APIRouter, HTTPException, Query, Path, status, Depends
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
    SuccessResponse
)
from ...services.storage_service import StorageService
from ...models.okw import ManufacturingFacility
from ...utils.logging import get_logger

# Set up logging
logger = get_logger(__name__)

# Create router with prefix and tags
router = APIRouter(tags=["okw"])

async def get_storage_service() -> StorageService:
    return await StorageService.get_instance()

@router.post("/create", response_model=OKWResponse, status_code=status.HTTP_201_CREATED)
async def create_okw(request: OKWCreateRequest):
    """Create a new OKW facility"""
    # Placeholder implementation
    return OKWResponse(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        name=request.name,
        location=request.location,
        facility_status=request.facility_status,
        access_type=request.access_type
    )

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
async def get_okw(id: UUID = Path(..., title="The ID of the OKW facility")):
    """Get an OKW facility by ID"""
    # Placeholder implementation - return 404 for now
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"OKW facility with ID {id} not found"
    )

@router.get("", response_model=OKWListResponse)
async def list_okw(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    filter: Optional[str] = Query(None, description="Filter criteria"),
    storage_service: StorageService = Depends(get_storage_service)
):
    """List OKW facilities from storage"""
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

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_facilities = facilities[start_idx:end_idx]
        
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
            total=len(facilities),
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing OKW facilities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing OKW facilities: {str(e)}")

@router.put("/{id}", response_model=OKWResponse)
async def update_okw(
    request: OKWUpdateRequest,
    id: UUID = Path(..., title="The ID of the OKW facility")
):
    """Update an OKW facility"""
    # Placeholder implementation - return 404 for now
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"OKW facility with ID {id} not found"
    )

@router.delete("/{id}", response_model=SuccessResponse)
async def delete_okw(
    id: UUID = Path(..., title="The ID of the OKW facility")
):
    """Delete an OKW facility"""
    # Placeholder implementation
    return SuccessResponse(
        success=True,
        message=f"OKW facility with ID {id} deleted successfully"
    )

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