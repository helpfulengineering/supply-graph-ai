from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from uuid import UUID
from typing import Optional
import json
import yaml

from ..models.match.request import (
    MatchRequest,
    ValidateMatchRequest
)
from ..models.match.response import (
    MatchResponse,
    ValidationResult
)
from ...services.matching_service import MatchingService
from ...services.storage_service import StorageService
from ...services.okh_service import OKHService
from ...services.domain_service import DomainDetector
from ...registry.domain_registry import DomainRegistry
from ...models.okh import OKHManifest
from ...utils.logging import get_logger

router = APIRouter(tags=["match"])

logger = get_logger(__name__)

async def get_matching_service() -> MatchingService:
    return await MatchingService.get_instance()

async def get_storage_service() -> StorageService:
    return await StorageService.get_instance()

async def get_okh_service() -> OKHService:
    return await OKHService.get_instance()

@router.post("", response_model=MatchResponse)
async def match_requirements_to_capabilities(
    request: MatchRequest,
    matching_service: MatchingService = Depends(get_matching_service),
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(get_okh_service)
):
    try:
        # 1. Get the OKH manifest from the request
        okh_manifest = None
        
        if request.okh_manifest is not None:
            # Use provided manifest
            okh_manifest = request.okh_manifest
            logger.info("Using provided OKH manifest")
            
        elif request.okh_id is not None:
            # Load manifest from storage by ID
            okh_manifest = await okh_service.get(request.okh_id)
            if okh_manifest is None:
                raise HTTPException(status_code=404, detail=f"OKH manifest with ID {request.okh_id} not found")
            logger.info(f"Loaded OKH manifest from storage: {request.okh_id}")
            
        elif request.okh_url is not None:
            # Fetch manifest from remote URL
            try:
                okh_manifest = await okh_service.fetch_from_url(request.okh_url)
                logger.info(f"Fetched OKH manifest from URL: {request.okh_url}")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Failed to fetch OKH manifest from URL: {str(e)}")
        
        if okh_manifest is None:
            raise HTTPException(status_code=400, detail="No valid OKH manifest provided")
        
        # 2. Validate the OKH manifest
        try:
            okh_manifest.validate()
            logger.debug("OKH manifest validation successful")
        except ValueError as e:
            logger.error(f"OKH manifest validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid OKH manifest: {str(e)}")

        # 3. (Optional) Store the OKH manifest for audit/history
        try:
            okh_handler = storage_service.get_domain_handler("okh")
            await okh_handler.save(okh_manifest)
        except Exception as e:
            logger.warning(f"Failed to store OKH manifest: {e}")

        # 4. Load OKW facilities from storage
        okw_handler = storage_service.get_domain_handler("okw")
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
                        import yaml
                        okw_data = yaml.safe_load(content)
                    elif obj["key"].endswith('.json'):
                        okw_data = json.loads(content)
                    else:
                        logger.warning(f"Skipping unsupported file format: {obj['key']}")
                        continue
                    
                    # Create ManufacturingFacility object
                    from ...models.okw import ManufacturingFacility
                    facility = ManufacturingFacility.from_dict(okw_data)
                    
                    # Apply filters if provided
                    if request.okw_filters:
                        if not _matches_filters(facility, request.okw_filters):
                            continue
                    
                    facilities.append(facility)
                    logger.debug(f"Loaded OKW facility from {obj['key']}: {facility.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to load OKW facility from {obj['key']}: {e}")
                    continue
            
            logger.info(f"Loaded {len(facilities)} OKW facilities from storage.")
        except Exception as e:
            logger.error(f"Failed to list/load OKW facilities: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load OKW facilities: {str(e)}")

        # 5. Run the matching logic (pass the in-memory OKH manifest and loaded OKW facilities)
        try:
            solutions = await matching_service.find_matches_with_manifest(
                okh_manifest=okh_manifest,
                facilities=facilities,
                optimization_criteria=request.optimization_criteria
            )
        except Exception as e:
            logger.error(f"Error during matching: {e}")
            raise HTTPException(status_code=500, detail=f"Error during matching: {str(e)}")

        # 5. Return the results
        if not solutions:
            return MatchResponse(
                solutions=[],
                metadata={
                    "message": "No matching facilities found",
                    "optimization_criteria": request.optimization_criteria
                }
            )
        # Convert solutions to a serializable format
        serialized_solutions = []
        for solution in solutions:
            # Get name and description from metadata or use defaults
            name = solution.tree.metadata.get('okh_title', f'Supply Tree {str(solution.tree.id)[:8]}')
            description = solution.tree.metadata.get('description', f'Manufacturing solution for {solution.tree.metadata.get("okh_title", "hardware project")}')
            
            # Calculate node and edge counts from workflows
            total_nodes = sum(len(workflow.graph.nodes) for workflow in solution.tree.workflows.values())
            total_edges = sum(len(workflow.graph.edges) for workflow in solution.tree.workflows.values())
            
            serialized_solutions.append({
                "tree": {
                    "id": str(solution.tree.id),
                    "name": name,
                    "description": description,
                    "node_count": total_nodes,
                    "edge_count": total_edges
                },
                "score": solution.score,
                "metrics": solution.metrics
            })
        
        return MatchResponse(
            solutions=serialized_solutions,
            metadata={
                "solution_count": len(solutions),
                "facility_count": sum(s.metrics["facility_count"] for s in solutions),
                "optimization_criteria": request.optimization_criteria
            }
        )
    except Exception as e:
        logger.error(f"Error finding matches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error finding matches: {str(e)}")

@router.post("/validate", response_model=ValidationResult)
async def validate_match(
    request: ValidateMatchRequest,
    matching_service: MatchingService = Depends(get_matching_service)
):
    try:
        logger.info(
            "Validating supply tree",
            extra={
                "okh_id": str(request.okh_id),
                "supply_tree_id": str(request.supply_tree_id)
            }
        )
        # TODO: Implement validation using matching service
        # For now, return a placeholder response
        logger.debug("Using placeholder validation response")
        return ValidationResult(
            valid=True,
            confidence=0.8,
            metadata={
                "okh_id": str(request.okh_id),
                "supply_tree_id": str(request.supply_tree_id),
                "validation_criteria": request.validation_criteria
            }
        )
    except Exception as e:
        logger.error(
            "Error validating match",
            extra={
                "okh_id": str(request.okh_id),
                "supply_tree_id": str(request.supply_tree_id),
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error validating match: {str(e)}"
        )

def _matches_filters(facility, filters: dict) -> bool:
    """Check if a facility matches the provided filters"""
    try:
        # Location filter
        if "location" in filters:
            location_filter = filters["location"]
            if "country" in location_filter:
                if facility.location.get("country", "").lower() != location_filter["country"].lower():
                    return False
            if "city" in location_filter:
                if facility.location.get("city", "").lower() != location_filter["city"].lower():
                    return False
        
        # Capability filter
        if "capabilities" in filters:
            required_capabilities = filters["capabilities"]
            facility_capabilities = [cap.get("name", "").lower() for cap in facility.equipment]
            for required_cap in required_capabilities:
                if required_cap.lower() not in facility_capabilities:
                    return False
        
        # Access type filter
        if "access_type" in filters:
            if facility.access_type.lower() != filters["access_type"].lower():
                return False
        
        # Facility status filter
        if "facility_status" in filters:
            if facility.facility_status.lower() != filters["facility_status"].lower():
                return False
        
        return True
    except Exception as e:
        logger.warning(f"Error applying filters to facility {facility.name}: {e}")
        return True  # Default to including the facility if filter fails

@router.post("/upload", response_model=MatchResponse)
async def match_requirements_from_file(
    okh_file: UploadFile = File(..., description="OKH file (YAML or JSON)"),
    access_type: Optional[str] = Form(None, description="Filter by access type"),
    facility_status: Optional[str] = Form(None, description="Filter by facility status"),
    location: Optional[str] = Form(None, description="Filter by location"),
    capabilities: Optional[str] = Form(None, description="Comma-separated list of required capabilities"),
    materials: Optional[str] = Form(None, description="Comma-separated list of required materials"),
    matching_service: MatchingService = Depends(get_matching_service),
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Match requirements to capabilities using an uploaded OKH file.
    
    This endpoint accepts a file upload (YAML or JSON) containing an OKH manifest
    and returns matching supply trees based on the requirements in the file.
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
            okh_manifest = OKHManifest.from_dict(okh_data)
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid OKH manifest: {str(e)}"
            )
        
        # Build OKW filters from form data
        okw_filters = {}
        if access_type:
            okw_filters["access_type"] = access_type
        if facility_status:
            okw_filters["facility_status"] = facility_status
        if location:
            okw_filters["location"] = location
        if capabilities:
            okw_filters["capabilities"] = [cap.strip() for cap in capabilities.split(',')]
        if materials:
            okw_filters["materials"] = [mat.strip() for mat in materials.split(',')]
        
        # Store the OKH manifest
        okh_handler = storage_service.get_domain_handler("okh")
        await okh_handler.save(okh_manifest)
        
        # Load OKW facilities from storage
        okw_facilities = []
        async for obj in storage_service.manager.list_objects():
            try:
                data = await storage_service.manager.get_object(obj["key"])
                content = data.decode('utf-8')
                
                if obj["key"].endswith(('.yaml', '.yml')):
                    okw_data = yaml.safe_load(content)
                elif obj["key"].endswith('.json'):
                    okw_data = json.loads(content)
                else:
                    continue
                
                from ...models.okw import ManufacturingFacility
                facility = ManufacturingFacility.from_dict(okw_data)
                
                # Apply filters
                if _matches_filters(facility, okw_filters):
                    okw_facilities.append(facility)
                    
            except Exception as e:
                logger.warning(f"Failed to load OKW facility from {obj['key']}: {e}")
                continue
        
        # Find matches
        solutions = await matching_service.find_matches_with_manifest(
            okh_manifest, okw_facilities
        )
        
        # Serialize results
        results = []
        for solution in solutions:
            # Calculate actual node and edge counts from workflows
            total_nodes = sum(len(workflow.graph.nodes) for workflow in solution.tree.workflows.values())
            total_edges = sum(len(workflow.graph.edges) for workflow in solution.tree.workflows.values())
            
            results.append({
                "tree": {
                    "id": str(solution.tree.id),
                    "name": solution.tree.metadata.get("name", "Unnamed Supply Tree"),
                    "description": solution.tree.metadata.get("description", "No description available"),
                    "node_count": total_nodes,
                    "edge_count": total_edges,
                    "workflow_count": len(solution.tree.workflows),
                    "metadata": solution.tree.metadata
                },
                "score": solution.score,
                "metrics": solution.metrics
            })
        
        return MatchResponse(
            solutions=results,
            metadata={
                "solution_count": len(results),
                "facility_count": len(okw_facilities),
                "optimization_criteria": {}
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in file upload matching: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/domains")
async def list_domains():
    """List all available domains with their metadata"""
    try:
        domains = DomainRegistry.list_domains()
        metadata = DomainRegistry.get_all_metadata()
        
        result = []
        for domain_name in domains:
            domain_metadata = metadata[domain_name]
            result.append({
                "name": domain_name,
                "display_name": domain_metadata.display_name,
                "description": domain_metadata.description,
                "version": domain_metadata.version,
                "status": domain_metadata.status.value,
                "supported_input_types": list(domain_metadata.supported_input_types),
                "supported_output_types": list(domain_metadata.supported_output_types),
                "documentation_url": domain_metadata.documentation_url,
                "maintainer": domain_metadata.maintainer
            })
        
        return {
            "domains": result,
            "total_count": len(result)
        }
    except Exception as e:
        logger.error(f"Error listing domains: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing domains: {str(e)}")

@router.get("/domains/{domain_name}")
async def get_domain_info(domain_name: str):
    """Get detailed information about a specific domain"""
    try:
        if domain_name not in DomainRegistry.list_domains():
            raise HTTPException(status_code=404, detail=f"Domain '{domain_name}' not found")
        
        metadata = DomainRegistry.get_domain_metadata(domain_name)
        supported_types = DomainRegistry.get_supported_types(domain_name)
        
        return {
            "name": domain_name,
            "display_name": metadata.display_name,
            "description": metadata.description,
            "version": metadata.version,
            "status": metadata.status.value,
            "supported_input_types": list(metadata.supported_input_types),
            "supported_output_types": list(metadata.supported_output_types),
            "documentation_url": metadata.documentation_url,
            "maintainer": metadata.maintainer,
            "type_mappings": supported_types
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting domain info for {domain_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting domain info: {str(e)}")

@router.get("/domains/{domain_name}/health")
async def get_domain_health(domain_name: str):
    """Get health status for a specific domain"""
    try:
        if domain_name not in DomainRegistry.list_domains():
            raise HTTPException(status_code=404, detail=f"Domain '{domain_name}' not found")
        
        # Get domain services
        domain_services = DomainRegistry.get_domain_services(domain_name)
        
        # Basic health check
        health_status = {
            "domain": domain_name,
            "status": "healthy",
            "components": {
                "extractor": {
                    "type": type(domain_services.extractor).__name__,
                    "status": "available"
                },
                "matcher": {
                    "type": type(domain_services.matcher).__name__,
                    "status": "available"
                },
                "validator": {
                    "type": type(domain_services.validator).__name__,
                    "status": "available"
                }
            }
        }
        
        if domain_services.orchestrator:
            health_status["components"]["orchestrator"] = {
                "type": type(domain_services.orchestrator).__name__,
                "status": "available"
            }
        
        return health_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting domain health for {domain_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting domain health: {str(e)}")

@router.post("/detect-domain")
async def detect_domain_from_input(
    requirements_data: dict,
    capabilities_data: dict
):
    """Detect the appropriate domain from input data"""
    try:
        # Create mock objects with the provided data
        class MockRequirements:
            def __init__(self, data):
                self.content = data
                self.domain = data.get('domain')
                self.type = data.get('type')
        
        class MockCapabilities:
            def __init__(self, data):
                self.content = data
                self.domain = data.get('domain')
                self.type = data.get('type')
        
        requirements = MockRequirements(requirements_data)
        capabilities = MockCapabilities(capabilities_data)
        
        # Detect domain
        detection_result = DomainDetector.detect_domain(requirements, capabilities)
        
        return {
            "detected_domain": detection_result.domain,
            "confidence": detection_result.confidence,
            "method": detection_result.method,
            "alternative_domains": detection_result.alternative_domains,
            "is_confident": detection_result.is_confident()
        }
    except Exception as e:
        logger.error(f"Error detecting domain: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error detecting domain: {str(e)}")