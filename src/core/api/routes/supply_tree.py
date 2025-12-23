import json
import os
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)

from ...models.supply_trees import SupplyTree, SupplyTreeSolution
from ...services.okh_service import OKHService
from ...services.okw_service import OKWService
from ...services.storage_service import StorageService
from ...utils.logging import get_logger
from ..decorators import (
    api_endpoint,
    llm_endpoint,
    paginated_response,
    track_performance,
    validate_request,
)
from ..error_handlers import create_error_response, create_success_response
from ..models.base import (
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
)
from ..models.base import ValidationResult as BaseValidationResult
from ..models.supply_tree.request import (
    CleanupStaleSolutionsRequest,
    ExtendSolutionTTLRequest,
    SolutionLoadRequest,
    SupplyTreeCreateRequest,
    SupplyTreeOptimizeRequest,
    SupplyTreeValidateRequest,
)


logger = get_logger(__name__)


# Dependency functions
async def get_storage_service() -> StorageService:
    """Get storage service instance."""
    from ....config import settings

    storage_service = await StorageService.get_instance()

    # Configure storage service if not already configured
    if not storage_service._configured:
        try:
            await storage_service.configure(settings.STORAGE_CONFIG)
        except Exception as e:
            logger.warning(f"Failed to configure storage service: {e}")
            # Return service anyway - it will handle errors in methods

    return storage_service


async def get_okh_service() -> OKHService:
    """Get OKH service instance."""
    return await OKHService.get_instance()


async def get_okw_service() -> OKWService:
    """Get OKW service instance."""
    return await OKWService.get_instance()


# Create router with standardized patterns
router = APIRouter(
    prefix="/api/supply-tree",
    tags=["supply-tree"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    },
)

# Note: Enhanced models have been consolidated into the base models in request.py and response.py


@router.post(
    "/create",
    # Note: response_model removed - api_endpoint decorator handles response wrapping
    status_code=status.HTTP_201_CREATED,
    summary="Create Supply Tree",
    description="""
    Create a supply tree with enhanced capabilities.
    
    This endpoint provides:
    - Standardized request/response formats
    - LLM integration support
    - Enhanced error handling
    - Performance metrics
    - Validation
    
    **Features:**
    - Support for LLM-enhanced supply tree creation
    - Advanced workflow definitions
    - Real-time performance tracking
    - Detailed validation results
    """,
)
@api_endpoint(
    success_message="Supply tree created successfully",
    include_metrics=True,
    track_llm=True,
)
@validate_request(SupplyTreeCreateRequest)
@track_performance("supply_tree_create")
@llm_endpoint(
    default_provider="anthropic", default_model="claude-sonnet-4-5", track_costs=True
)
async def create_supply_tree(
    request: SupplyTreeCreateRequest,
    http_request: Request,
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(get_okh_service),
    okw_service: OKWService = Depends(get_okw_service),
):
    """
    Enhanced supply tree creation with standardized patterns.

    Args:
        create_request: Enhanced supply tree creation request with standardized fields
        http_request: HTTP request object for tracking

    Returns:
        Enhanced supply tree response with data
    """
    request_id = getattr(http_request.state, "request_id", None)
    start_time = datetime.now()

    try:
        # Get the facility and OKH manifest for creating the supply tree
        facility = await okw_service.get(request.facility_id)
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Facility with ID {request.facility_id} not found",
            )

        # Try to get OKH manifest if okh_reference is a UUID, otherwise use as reference
        okh_manifest = None
        if request.okh_reference:
            try:
                okh_manifest = await okh_service.get(UUID(request.okh_reference))
            except (ValueError, TypeError):
                # If okh_reference is not a valid UUID, treat it as a reference string
                # Try to find it by searching storage or skip OKH manifest loading
                pass

        # Create the supply tree
        if okh_manifest:
            # Use factory method if manifest is available
            supply_tree = SupplyTree.from_facility_and_manifest(
                facility=facility,
                manifest=okh_manifest,
                confidence_score=request.confidence_score,
                match_type=request.match_type,
                estimated_cost=request.estimated_cost,
                estimated_time=request.estimated_time,
            )

            # Override with request-specific data
            supply_tree.materials_required = request.materials_required
            supply_tree.capabilities_used = request.capabilities_used
            supply_tree.metadata.update(request.metadata)
        else:
            # Create supply tree directly from request data when manifest is not available
            supply_tree = SupplyTree(
                facility_name=request.facility_name or facility.name,
                okh_reference=request.okh_reference,
                confidence_score=request.confidence_score,
                okw_reference=str(facility.id),
                match_type=request.match_type,
                estimated_cost=request.estimated_cost,
                estimated_time=request.estimated_time,
                materials_required=request.materials_required or [],
                capabilities_used=request.capabilities_used or [],
                metadata=request.metadata or {},
            )

        # Save the supply tree to storage
        if storage_service:
            await storage_service.save_supply_tree(supply_tree)

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Convert okw_reference to facility_id for response
        # SupplyTree uses okw_reference (string), but response expects facility_id (UUID)
        facility_id = facility.id
        if supply_tree.okw_reference:
            try:
                facility_id = UUID(supply_tree.okw_reference)
            except (ValueError, TypeError):
                # If okw_reference is not a valid UUID, use facility.id
                facility_id = facility.id

        # Create response data using the consolidated model structure
        response_data = {
            "id": supply_tree.id,
            "facility_id": facility_id,
            "facility_name": supply_tree.facility_name,
            "okh_reference": supply_tree.okh_reference,
            "confidence_score": supply_tree.confidence_score,
            "creation_time": supply_tree.creation_time.isoformat(),
            "estimated_cost": supply_tree.estimated_cost,
            "estimated_time": supply_tree.estimated_time,
            "materials_required": supply_tree.materials_required,
            "capabilities_used": supply_tree.capabilities_used,
            "match_type": supply_tree.match_type,
            "metadata": supply_tree.metadata,
            "processing_time": processing_time,
            "validation_results": await _validate_supply_tree_result(
                supply_tree.to_dict(), request_id
            ),
        }

        logger.info(
            f"Supply tree created successfully",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(supply_tree.id),
                "facility_id": str(facility_id),
                "okh_reference": supply_tree.okh_reference,
                "confidence_score": supply_tree.confidence_score,
                "processing_time": processing_time,
                "llm_used": getattr(request, "use_llm", False),
            },
        )

        return response_data

    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error creating supply tree: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/solutions",
    status_code=status.HTTP_200_OK,
    summary="List Supply Tree Solutions",
    description="""
    List supply tree solutions with optional filtering and sorting.
    
    Supports filtering by:
    - okh_id: Filter by OKH manifest ID
    - matching_mode: Filter by matching mode (nested/single-level)
    - min_age_days, max_age_days: Filter by solution age
    - include_stale, only_stale: Filter by staleness
    
    Supports sorting by:
    - created_at, updated_at, expires_at, score, age_days
    - sort_order: asc or desc (default: desc)
    """,
)
@api_endpoint(success_message="Solutions retrieved successfully", include_metrics=True)
@track_performance("solutions_list")
async def list_supply_tree_solutions(
    limit: Optional[int] = Query(
        None, description="Maximum number of solutions to return"
    ),
    offset: Optional[int] = Query(None, description="Number of solutions to skip"),
    okh_id: Optional[UUID] = Query(None, description="Filter by OKH ID"),
    matching_mode: Optional[str] = Query(None, description="Filter by matching mode"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    min_age_days: Optional[int] = Query(
        None, description="Filter by minimum age in days"
    ),
    max_age_days: Optional[int] = Query(
        None, description="Filter by maximum age in days"
    ),
    include_stale: bool = Query(True, description="Include stale solutions"),
    only_stale: bool = Query(False, description="Only return stale solutions"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """List supply tree solutions with optional filtering and sorting"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        solutions = await storage_service.list_supply_tree_solutions(
            limit=limit,
            offset=offset,
            okh_id=okh_id,
            matching_mode=matching_mode,
            sort_by=sort_by,
            sort_order=sort_order,
            min_age_days=min_age_days,
            max_age_days=max_age_days,
            include_stale=include_stale,
            only_stale=only_stale,
        )

        logger.info(
            f"Solutions listed",
            extra={
                "request_id": request_id,
                "count": len(solutions),
                "filters": {
                    "okh_id": str(okh_id) if okh_id else None,
                    "matching_mode": matching_mode,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                },
            },
        )

        return solutions

    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error listing solutions: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/solution/{solution_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Supply Tree Solution",
    description="""
    Get a supply tree solution by ID.
    
    Returns the complete solution including all trees, metadata, and relationships.
    """,
)
@api_endpoint(success_message="Solution retrieved successfully", include_metrics=True)
@track_performance("solution_get")
async def get_supply_tree_solution(
    solution_id: UUID = Path(..., description="Solution ID"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Get a supply tree solution by ID"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        solution = await storage_service.load_supply_tree_solution(solution_id)
        solution_dict = solution.to_dict()

        logger.info(
            f"Solution retrieved: {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "tree_count": len(solution.all_trees),
            },
        )

        return solution_dict

    except FileNotFoundError as e:
        error_response = create_error_response(
            error=f"Solution with ID {solution_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
            suggestion="Please check the solution ID and try again",
        )
        logger.error(
            f"Solution not found: {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error retrieving solution {solution_id}: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.delete(
    "/solution/{solution_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Supply Tree Solution",
    description="""
    Delete a supply tree solution by ID.
    
    This permanently deletes both the solution data and its metadata.
    """,
)
@api_endpoint(success_message="Solution deleted successfully", include_metrics=True)
@track_performance("solution_delete")
async def delete_supply_tree_solution(
    solution_id: UUID = Path(..., description="Solution ID"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Delete a supply tree solution by ID"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        deleted = await storage_service.delete_supply_tree_solution(solution_id)

        if not deleted:
            error_response = create_error_response(
                error=f"Solution with ID {solution_id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the solution ID and try again",
            )
            logger.warning(
                f"Solution not found for deletion: {solution_id}",
                extra={
                    "request_id": request_id,
                    "solution_id": str(solution_id),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        logger.info(
            f"Solution deleted: {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
            },
        )

        return {"deleted": True, "solution_id": str(solution_id)}

    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error deleting solution {solution_id}: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/solution/{solution_id}/staleness",
    status_code=status.HTTP_200_OK,
    summary="Check Solution Staleness",
    description="""
    Check if a supply tree solution is stale.
    
    Returns staleness status, age, and reason if stale.
    """,
)
@api_endpoint(success_message="Staleness check completed", include_metrics=True)
@track_performance("solution_staleness_check")
async def get_solution_staleness(
    solution_id: UUID = Path(..., description="Solution ID"),
    max_age_days: Optional[int] = Query(
        None, description="Optional maximum age in days for staleness check"
    ),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Check if a solution is stale"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Check staleness
        is_stale, staleness_reason = await storage_service.is_solution_stale(
            solution_id, max_age_days=max_age_days
        )

        # Get age
        age = await storage_service.get_solution_age(solution_id)
        age_days = age.days

        logger.info(
            f"Staleness check for solution {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "is_stale": is_stale,
                "staleness_reason": staleness_reason,
                "age_days": age_days,
            },
        )

        return {
            "is_stale": is_stale,
            "staleness_reason": staleness_reason,
            "age_days": age_days,
            "solution_id": str(solution_id),
        }

    except FileNotFoundError as e:
        error_response = create_error_response(
            error=f"Solution with ID {solution_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
            suggestion="Please check the solution ID and try again",
        )
        logger.warning(
            f"Solution not found for staleness check: {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error checking staleness for solution {solution_id}: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post(
    "/solutions/cleanup",
    status_code=status.HTTP_200_OK,
    summary="Cleanup Stale Solutions",
    description="""
    Remove stale solutions from storage.
    
    Supports dry-run mode to preview what would be deleted.
    """,
)
@api_endpoint(success_message="Cleanup completed", include_metrics=True)
@track_performance("solutions_cleanup")
async def cleanup_stale_solutions(
    request: CleanupStaleSolutionsRequest,
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Cleanup stale solutions"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Parse before_date if provided
        before_date = None
        if request.before_date:
            from datetime import datetime

            before_date = datetime.fromisoformat(request.before_date)

        # Perform cleanup
        result = await storage_service.cleanup_stale_solutions(
            max_age_days=request.max_age_days,
            before_date=before_date,
            dry_run=request.dry_run,
        )

        logger.info(
            f"Cleanup completed: {result['deleted_count']} solutions {'would be' if request.dry_run else ''} deleted",
            extra={
                "request_id": request_id,
                "deleted_count": result["deleted_count"],
                "dry_run": request.dry_run,
            },
        )

        return result

    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error during cleanup: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post(
    "/solution/{solution_id}/extend",
    status_code=status.HTTP_200_OK,
    summary="Extend Solution TTL",
    description="""
    Extend the expiration time (TTL) of a solution.
    
    Adds additional days to the current expiration time.
    """,
)
@api_endpoint(success_message="TTL extended successfully", include_metrics=True)
@track_performance("solution_extend_ttl")
async def extend_solution_ttl(
    solution_id: UUID = Path(..., description="Solution ID"),
    request: Optional[ExtendSolutionTTLRequest] = Body(
        None, description="TTL extension request"
    ),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Extend solution TTL"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Get additional_days from request body or use default
        additional_days = 30
        if request:
            additional_days = request.additional_days

        # Extend TTL
        extended = await storage_service.extend_solution_ttl(
            solution_id, additional_days=additional_days
        )

        if not extended:
            error_response = create_error_response(
                error=f"Solution with ID {solution_id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the solution ID and try again",
            )
            logger.warning(
                f"Solution not found for TTL extension: {solution_id}",
                extra={
                    "request_id": request_id,
                    "solution_id": str(solution_id),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        logger.info(
            f"TTL extended for solution {solution_id} by {additional_days} days",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "additional_days": additional_days,
            },
        )

        return {
            "extended": True,
            "solution_id": str(solution_id),
            "additional_days": additional_days,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error extending TTL for solution {solution_id}: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post(
    "/solution/{solution_id}/save",
    status_code=status.HTTP_200_OK,
    summary="Save Supply Tree Solution",
    description="""
    Save a supply tree solution to storage.
    
    The solution can be provided in the request body. If solution_id is provided in path,
    it will be used; otherwise, a new UUID will be generated.
    """,
)
@api_endpoint(success_message="Solution saved successfully", include_metrics=True)
@track_performance("solution_save")
async def save_supply_tree_solution(
    solution_id: UUID = Path(..., description="Solution ID"),
    solution: dict = Body(..., description="Solution data to save"),
    ttl_days: Optional[int] = Body(None, description="Time-to-live in days"),
    tags: Optional[List[str]] = Body(
        None, description="Tags to associate with solution"
    ),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Save a supply tree solution to storage"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Convert dict to SupplyTreeSolution
        from ...models.supply_trees import SupplyTreeSolution

        # Handle both wrapped and direct formats
        if "solution" in solution:
            solution_obj = SupplyTreeSolution.from_dict(solution["solution"])
        elif "all_trees" in solution:
            solution_obj = SupplyTreeSolution.from_dict(solution)
        else:
            error_response = create_error_response(
                error="Invalid solution format: missing 'solution' or 'all_trees' key",
                status_code=status.HTTP_400_BAD_REQUEST,
                request_id=request_id,
                suggestion="Please provide solution data in the correct format",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response.model_dump(mode="json"),
            )

        # Save solution
        saved_id = await storage_service.save_supply_tree_solution(
            solution_obj,
            solution_id=solution_id,
            ttl_days=ttl_days,
            tags=tags,
        )

        logger.info(
            f"Solution saved: {saved_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(saved_id),
                "tree_count": len(solution_obj.all_trees),
                "ttl_days": ttl_days,
            },
        )

        return {"solution_id": str(saved_id), "saved": True}

    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error saving solution: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/solution/{solution_id}/summary",
    status_code=status.HTTP_200_OK,
    summary="Get Solution Summary",
    description="""
    Get aggregated statistics and summary for a supply tree solution.
    
    Supports multiple loading sources:
    - Storage: Load from storage using solution_id in path (default)
    - File: Use GET /api/supply-tree/solution/load?file_path=... for file loading
    
    Returns:
    - Total trees, components, and facilities
    - Average confidence score
    - Component and facility distributions
    - Cost and time estimates (if available)
    - Solution metadata
    """,
)
@api_endpoint(
    success_message="Solution summary retrieved successfully", include_metrics=True
)
@track_performance("solution_summary")
async def get_solution_summary(
    solution_id: UUID = Path(..., description="Solution ID (for storage loading)"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Get summary statistics for a supply tree solution"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Load solution using multi-source helper (from storage)
        solution = await _load_solution_from_source(
            solution_id=solution_id, storage_service=storage_service
        )

        # Calculate summary statistics
        total_trees = len(solution.all_trees)

        # Count unique components
        component_ids = set()
        component_names = {}
        for tree in solution.all_trees:
            if tree.component_id:
                component_ids.add(tree.component_id)
            if tree.component_name:
                component_names[tree.component_id or tree.component_name] = (
                    tree.component_name
                )

        total_components = (
            len(component_ids)
            if component_ids
            else len(
                set(
                    tree.component_name
                    for tree in solution.all_trees
                    if tree.component_name
                )
            )
        )

        # Count unique facilities
        facilities = set(
            tree.facility_name for tree in solution.all_trees if tree.facility_name
        )
        total_facilities = len(facilities)

        # Calculate average confidence
        if solution.all_trees:
            avg_confidence = sum(
                tree.confidence_score for tree in solution.all_trees
            ) / len(solution.all_trees)
        else:
            avg_confidence = solution.score

        # Component distribution
        component_distribution = []
        component_counts = {}
        for tree in solution.all_trees:
            comp_id = tree.component_id or tree.component_name or "unknown"
            component_counts[comp_id] = component_counts.get(comp_id, 0) + 1

        for comp_id, count in component_counts.items():
            component_distribution.append(
                {
                    "component_id": comp_id,
                    "component_name": next(
                        (
                            tree.component_name
                            for tree in solution.all_trees
                            if (tree.component_id or tree.component_name) == comp_id
                        ),
                        comp_id,
                    ),
                    "count": count,
                }
            )

        # Facility distribution
        facility_distribution = []
        facility_counts = {}
        for tree in solution.all_trees:
            if tree.facility_name:
                facility_counts[tree.facility_name] = (
                    facility_counts.get(tree.facility_name, 0) + 1
                )

        for facility_name, count in facility_counts.items():
            facility_distribution.append(
                {"facility_name": facility_name, "count": count}
            )

        # Build summary response
        summary = {
            "id": str(solution_id),
            "okh_id": solution.metadata.get("okh_id"),
            "okh_title": solution.metadata.get("okh_title"),
            "matching_mode": solution.metadata.get("matching_mode", "single-level"),
            "total_trees": total_trees,
            "total_components": total_components,
            "total_facilities": total_facilities,
            "average_confidence": round(avg_confidence, 2),
            "score": solution.score,
            "component_distribution": component_distribution,
            "facility_distribution": facility_distribution,
            "cost_estimate": solution.total_estimated_cost,
            "time_estimate": solution.total_estimated_time,
            "is_nested": solution.is_nested,
        }

        logger.info(
            f"Solution summary retrieved for {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "total_trees": total_trees,
            },
        )

        return summary

    except Exception as e:
        error_status = (
            status.HTTP_404_NOT_FOUND
            if "not found" in str(e).lower()
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        error_response = create_error_response(
            error=e,
            status_code=error_status,
            request_id=request_id,
            suggestion="Please verify the solution ID and try again",
        )
        logger.error(
            f"Error retrieving solution summary {solution_id}: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=error_status,
            detail=error_response.model_dump(mode="json"),
        )


@router.post(
    "/solution/load",
    status_code=status.HTTP_200_OK,
    summary="Load Supply Tree Solution",
    description="""
    Load a supply tree solution from multiple sources.
    
    Supports three loading sources:
    - storage: Load from StorageService using solution_id
    - file: Load from local file using file_path
    - inline: Use solution data provided directly in request body
    
    Examples:
    - Storage: {"source": "storage", "solution_id": "uuid"}
    - File: {"source": "file", "file_path": "/path/to/solution.json"}
    - Inline: {"source": "inline", "solution": {...}}
    """,
)
@api_endpoint(success_message="Solution loaded successfully", include_metrics=True)
@track_performance("solution_load")
async def load_supply_tree_solution(
    request: SolutionLoadRequest,
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Load a supply tree solution from storage, file, or inline data."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Load solution using multi-source helper
        solution = await _load_solution_from_source(
            solution_id=request.solution_id,
            file_path=request.file_path,
            solution_data=request.solution,
            storage_service=storage_service if request.source == "storage" else None,
        )

        # Convert solution to dict for response
        solution_dict = solution.to_dict()

        logger.info(
            f"Solution loaded successfully from {request.source}",
            extra={
                "request_id": request_id,
                "source": request.source,
                "solution_id": (
                    str(request.solution_id) if request.solution_id else None
                ),
                "file_path": request.file_path,
                "tree_count": len(solution.all_trees),
            },
        )

        return solution_dict

    except (FileNotFoundError, ValueError) as e:
        error_status = (
            status.HTTP_404_NOT_FOUND
            if isinstance(e, FileNotFoundError)
            else status.HTTP_400_BAD_REQUEST
        )
        error_response = create_error_response(
            error=str(e),
            status_code=error_status,
            request_id=request_id,
            suggestion="Please check the source parameters and try again",
        )
        logger.error(
            f"Error loading solution: {str(e)}",
            extra={
                "request_id": request_id,
                "source": request.source,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=error_status,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error loading solution: {str(e)}",
            extra={
                "request_id": request_id,
                "source": request.source,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/solution/{solution_id}/trees",
    status_code=status.HTTP_200_OK,
    summary="Get Trees from Solution",
    description="""
    Get trees from a supply tree solution with optional filtering.
    
    Supports filtering by:
    - component_id, component_name: Filter by component
    - facility_name, okw_reference: Filter by facility
    - depth, min_depth, max_depth: Filter by depth
    - min_confidence: Filter by minimum confidence score
    - production_stage: Filter by production stage
    
    Supports pagination and sorting.
    """,
)
@api_endpoint(success_message="Trees retrieved successfully", include_metrics=True)
@track_performance("solution_trees")
async def get_solution_trees(
    solution_id: UUID = Path(..., description="Solution ID"),
    component_id: Optional[str] = Query(None, description="Filter by component ID"),
    component_name: Optional[str] = Query(None, description="Filter by component name"),
    facility_name: Optional[str] = Query(None, description="Filter by facility name"),
    okw_reference: Optional[str] = Query(
        None, description="Filter by OKW reference (facility ID)"
    ),
    depth: Optional[int] = Query(None, description="Filter by exact depth"),
    min_depth: Optional[int] = Query(None, description="Filter by minimum depth"),
    max_depth: Optional[int] = Query(None, description="Filter by maximum depth"),
    min_confidence: Optional[float] = Query(
        None, description="Filter by minimum confidence score"
    ),
    production_stage: Optional[str] = Query(
        None, description="Filter by production stage"
    ),
    limit: Optional[int] = Query(None, description="Maximum number of trees to return"),
    offset: Optional[int] = Query(None, description="Number of trees to skip"),
    sort_by: Optional[str] = Query(
        "confidence_score",
        description="Field to sort by (confidence_score, depth, facility_name)",
    ),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Get trees from a solution with optional filtering"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Load solution
        solution = await _load_solution_from_source(
            solution_id=solution_id, storage_service=storage_service
        )

        # Filter trees
        filtered_trees = solution.all_trees

        if component_id:
            filtered_trees = [
                t for t in filtered_trees if t.component_id == component_id
            ]

        if component_name:
            filtered_trees = [
                t for t in filtered_trees if t.component_name == component_name
            ]

        if facility_name:
            filtered_trees = [
                t for t in filtered_trees if t.facility_name == facility_name
            ]

        if okw_reference:
            filtered_trees = [
                t for t in filtered_trees if t.okw_reference == okw_reference
            ]

        if depth is not None:
            filtered_trees = [t for t in filtered_trees if t.depth == depth]

        if min_depth is not None:
            filtered_trees = [t for t in filtered_trees if t.depth >= min_depth]

        if max_depth is not None:
            filtered_trees = [t for t in filtered_trees if t.depth <= max_depth]

        if min_confidence is not None:
            filtered_trees = [
                t for t in filtered_trees if t.confidence_score >= min_confidence
            ]

        if production_stage:
            filtered_trees = [
                t for t in filtered_trees if t.production_stage == production_stage
            ]

        # Sort trees
        reverse_order = sort_order.lower() == "desc"
        if sort_by == "confidence_score":
            filtered_trees.sort(key=lambda t: t.confidence_score, reverse=reverse_order)
        elif sort_by == "depth":
            filtered_trees.sort(key=lambda t: t.depth, reverse=reverse_order)
        elif sort_by == "facility_name":
            filtered_trees.sort(
                key=lambda t: t.facility_name or "", reverse=reverse_order
            )

        # Apply pagination
        total_count = len(filtered_trees)
        if offset:
            filtered_trees = filtered_trees[offset:]
        if limit:
            filtered_trees = filtered_trees[:limit]

        # Convert to dicts
        trees_data = [tree.to_dict() for tree in filtered_trees]

        logger.info(
            f"Trees retrieved for solution {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "total_trees": total_count,
                "filtered_count": len(trees_data),
                "filters": {
                    "component_id": component_id,
                    "component_name": component_name,
                    "facility_name": facility_name,
                    "depth": depth,
                    "min_confidence": min_confidence,
                },
            },
        )

        return {
            "trees": trees_data,
            "total_count": total_count,
            "returned_count": len(trees_data),
            "filters_applied": {
                "component_id": component_id,
                "component_name": component_name,
                "facility_name": facility_name,
                "okw_reference": okw_reference,
                "depth": depth,
                "min_depth": min_depth,
                "max_depth": max_depth,
                "min_confidence": min_confidence,
                "production_stage": production_stage,
            },
        }

    except FileNotFoundError as e:
        error_response = create_error_response(
            error=f"Solution with ID {solution_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
            suggestion="Please check the solution ID and try again",
        )
        logger.warning(
            f"Solution not found for tree query: {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error retrieving trees for solution {solution_id}: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/solution/{solution_id}/component/{component_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Component Trees",
    description="""
    Get all trees for a specific component in a solution.
    
    Returns all SupplyTrees that match the component_id, including
    parent/child relationships if available.
    """,
)
@api_endpoint(
    success_message="Component trees retrieved successfully", include_metrics=True
)
@track_performance("component_trees")
async def get_component_trees(
    solution_id: UUID = Path(..., description="Solution ID"),
    component_id: str = Path(..., description="Component ID"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Get all trees for a specific component"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Load solution
        solution = await _load_solution_from_source(
            solution_id=solution_id, storage_service=storage_service
        )

        # Filter trees by component_id
        component_trees = [
            t for t in solution.all_trees if t.component_id == component_id
        ]

        # Convert to dicts
        trees_data = [tree.to_dict() for tree in component_trees]

        logger.info(
            f"Component trees retrieved for solution {solution_id}, component {component_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "component_id": component_id,
                "tree_count": len(trees_data),
            },
        )

        return {
            "component_id": component_id,
            "trees": trees_data,
            "count": len(trees_data),
        }

    except FileNotFoundError as e:
        error_response = create_error_response(
            error=f"Solution with ID {solution_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
            suggestion="Please check the solution ID and try again",
        )
        logger.warning(
            f"Solution not found for component query: {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error retrieving component trees: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "component_id": component_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/solution/{solution_id}/facility/{facility_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Facility Trees",
    description="""
    Get all trees for a specific facility in a solution.
    
    The facility_id can be either:
    - okw_reference (facility reference string)
    - facility_name (exact match)
    
    Useful for understanding facility workload and capacity planning.
    """,
)
@api_endpoint(
    success_message="Facility trees retrieved successfully", include_metrics=True
)
@track_performance("facility_trees")
async def get_facility_trees(
    solution_id: UUID = Path(..., description="Solution ID"),
    facility_id: str = Path(
        ..., description="Facility ID (okw_reference or facility_name)"
    ),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Get all trees for a specific facility"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Load solution
        solution = await _load_solution_from_source(
            solution_id=solution_id, storage_service=storage_service
        )

        # Filter trees by facility (try okw_reference first, then facility_name)
        facility_trees = [
            t
            for t in solution.all_trees
            if (t.okw_reference == facility_id or t.facility_name == facility_id)
        ]

        # Convert to dicts
        trees_data = [tree.to_dict() for tree in facility_trees]

        logger.info(
            f"Facility trees retrieved for solution {solution_id}, facility {facility_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "facility_id": facility_id,
                "tree_count": len(trees_data),
            },
        )

        return {
            "facility_id": facility_id,
            "trees": trees_data,
            "count": len(trees_data),
        }

    except FileNotFoundError as e:
        error_response = create_error_response(
            error=f"Solution with ID {solution_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
            suggestion="Please check the solution ID and try again",
        )
        logger.warning(
            f"Solution not found for facility query: {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error retrieving facility trees: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "facility_id": facility_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/solution/{solution_id}/export",
    summary="Export Supply Tree Solution",
    description="""
    Export a supply tree solution to a specific format.
    
    Supports multiple loading sources:
    - Storage: Load from storage using solution_id in path (default)
    - File: Use GET /api/supply-tree/solution/load?file_path=... for file loading
    
    Supported formats:
    - json: JSON format (default)
    - xml: XML format
    - graphml: GraphML format for graph visualization (supports nested relationships)
    """,
)
@api_endpoint(success_message="Solution exported successfully", include_metrics=True)
@track_performance("solution_export")
async def export_supply_tree_solution(
    solution_id: UUID = Path(..., description="Solution ID (for storage loading)"),
    format: str = Query("json", description="Export format (json, xml, graphml)"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Export a supply tree solution in the requested format."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Validate format
        valid_formats = ["json", "xml", "graphml"]
        if format.lower() not in valid_formats:
            error_response = create_error_response(
                error=f"Invalid format '{format}'. Supported formats: {', '.join(valid_formats)}",
                status_code=status.HTTP_400_BAD_REQUEST,
                request_id=request_id,
                suggestion=f"Please use one of the supported formats: {', '.join(valid_formats)}",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response.model_dump(mode="json"),
            )

        # Load solution using multi-source helper (from storage)
        try:
            solution = await _load_solution_from_source(
                solution_id=solution_id, storage_service=storage_service
            )
        except (FileNotFoundError, ValueError) as e:
            error_status = (
                status.HTTP_404_NOT_FOUND
                if isinstance(e, FileNotFoundError)
                else status.HTTP_400_BAD_REQUEST
            )
            error_response = create_error_response(
                error=str(e),
                status_code=error_status,
                request_id=request_id,
                suggestion="Please check the solution ID and try again",
            )
            raise HTTPException(
                status_code=error_status,
                detail=error_response.model_dump(mode="json"),
            )

        # Export in requested format
        format_lower = format.lower()
        if format_lower == "json":
            solution_dict = solution.to_dict()
            content = json.dumps(solution_dict, indent=2, default=str)
            media_type = "application/json"
        elif format_lower == "xml":
            solution_dict = solution.to_dict()
            content = _dict_to_xml(solution_dict, root_name="supply_tree_solution")
            media_type = "application/xml"
        elif format_lower == "graphml":
            # GraphML export for nested solutions
            content = _solution_to_graphml(solution)
            media_type = "application/xml"
        else:
            # Should not reach here due to validation above
            solution_dict = solution.to_dict()
            content = json.dumps(solution_dict, indent=2, default=str)
            media_type = "application/json"

        logger.info(
            f"Solution exported successfully in {format} format",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "format": format,
                "tree_count": len(solution.all_trees),
            },
        )

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="solution_{solution_id}.{format_lower}"'
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error exporting solution {solution_id}: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "format": format,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/solution/{solution_id}/dependencies",
    status_code=status.HTTP_200_OK,
    summary="Get Solution Dependencies",
    description="""
    Get the dependency graph for a supply tree solution.
    
    Returns:
    - dependency_graph: Dictionary mapping tree_id -> list of dependency tree_ids
    - trees: Dictionary mapping tree_id -> tree details (for visualization)
    - summary: Summary statistics about dependencies
    
    The dependency graph shows which SupplyTrees depend on which others,
    based on parent-child relationships and explicit dependencies.
    """,
)
@api_endpoint(
    success_message="Dependencies retrieved successfully", include_metrics=True
)
@track_performance("solution_dependencies")
async def get_solution_dependencies(
    solution_id: UUID = Path(..., description="Solution ID"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Get dependency graph for a solution"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Load solution
        solution = await _load_solution_from_source(
            solution_id=solution_id, storage_service=storage_service
        )

        # Get dependency graph
        dependency_graph = solution.get_dependency_graph()

        # Build tree details dictionary for easy lookup
        trees_dict = {str(tree.id): tree.to_dict() for tree in solution.all_trees}

        # Calculate summary statistics
        total_dependencies = sum(len(deps) for deps in dependency_graph.values())
        trees_with_deps = len([deps for deps in dependency_graph.values() if deps])
        trees_without_deps = len(solution.all_trees) - trees_with_deps

        logger.info(
            f"Dependencies retrieved for solution {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "total_trees": len(solution.all_trees),
                "total_dependencies": total_dependencies,
            },
        )

        return {
            "dependency_graph": {
                str(tree_id): [str(dep_id) for dep_id in deps]
                for tree_id, deps in dependency_graph.items()
            },
            "trees": trees_dict,
            "summary": {
                "total_trees": len(solution.all_trees),
                "total_dependencies": total_dependencies,
                "trees_with_dependencies": trees_with_deps,
                "trees_without_dependencies": trees_without_deps,
                "average_dependencies_per_tree": (
                    round(total_dependencies / len(solution.all_trees), 2)
                    if solution.all_trees
                    else 0.0
                ),
            },
        }

    except FileNotFoundError as e:
        error_response = create_error_response(
            error=f"Solution with ID {solution_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
            suggestion="Please check the solution ID and try again",
        )
        logger.error(
            f"Solution not found: {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error retrieving dependencies: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/solution/{solution_id}/production-sequence",
    status_code=status.HTTP_200_OK,
    summary="Get Production Sequence",
    description="""
    Get the production sequence for a supply tree solution.
    
    Returns:
    - production_sequence: List of production stages (each stage can be done in parallel)
    - stages: Detailed stage information with tree details
    - summary: Summary statistics about the production sequence
    
    The production sequence is calculated using topological sort,
    ensuring dependencies are respected. Trees in the same stage
    can be produced in parallel.
    """,
)
@api_endpoint(
    success_message="Production sequence retrieved successfully", include_metrics=True
)
@track_performance("solution_production_sequence")
async def get_solution_production_sequence(
    solution_id: UUID = Path(..., description="Solution ID"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Get production sequence for a solution"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Load solution
        solution = await _load_solution_from_source(
            solution_id=solution_id, storage_service=storage_service
        )

        # Get production sequence (list of stages, each stage is a list of SupplyTree objects)
        assembly_sequence = solution.get_assembly_sequence()

        # If no production sequence exists, calculate it
        if not assembly_sequence:
            # Build dependency graph and calculate sequence
            dependency_graph = solution.get_dependency_graph()
            if dependency_graph:
                sequence_ids = SupplyTreeSolution._calculate_production_sequence(
                    dependency_graph
                )
                tree_map = {tree.id: tree for tree in solution.all_trees}
                assembly_sequence = [
                    [tree_map[tree_id] for tree_id in stage if tree_id in tree_map]
                    for stage in sequence_ids
                ]
            else:
                # No dependencies, all trees can be done in parallel
                assembly_sequence = [solution.all_trees]

        # Convert to detailed stages with tree information
        stages = []
        for stage_idx, stage_trees in enumerate(assembly_sequence):
            stage_info = {
                "stage_number": stage_idx + 1,
                "trees": [tree.to_dict() for tree in stage_trees],
                "can_parallelize": len(stage_trees) > 1,
                "tree_count": len(stage_trees),
            }
            stages.append(stage_info)

        # Calculate summary statistics
        total_stages = len(stages)
        parallelizable_stages = len([s for s in stages if s["can_parallelize"]])
        total_trees = sum(s["tree_count"] for s in stages)

        logger.info(
            f"Production sequence retrieved for solution {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "total_stages": total_stages,
                "total_trees": total_trees,
            },
        )

        return {
            "production_sequence": [
                [str(tree.id) for tree in stage] for stage in assembly_sequence
            ],
            "stages": stages,
            "summary": {
                "total_stages": total_stages,
                "total_trees": total_trees,
                "parallelizable_stages": parallelizable_stages,
                "average_trees_per_stage": (
                    round(total_trees / total_stages, 2) if total_stages > 0 else 0.0
                ),
            },
        }

    except FileNotFoundError as e:
        error_response = create_error_response(
            error=f"Solution with ID {solution_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
            suggestion="Please check the solution ID and try again",
        )
        logger.error(
            f"Solution not found: {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error retrieving production sequence: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/solution/{solution_id}/hierarchy",
    status_code=status.HTTP_200_OK,
    summary="Get Component Hierarchy",
    description="""
    Get the component hierarchy for a supply tree solution.
    
    Returns:
    - hierarchy: Tree structure showing parent-child component relationships
    - root_components: List of root (top-level) components
    - component_details: Dictionary mapping component_id -> component information
    
    The hierarchy shows how components are organized in a tree structure,
    with parent components containing child components.
    """,
)
@api_endpoint(success_message="Hierarchy retrieved successfully", include_metrics=True)
@track_performance("solution_hierarchy")
async def get_solution_hierarchy(
    solution_id: UUID = Path(..., description="Solution ID"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Get component hierarchy for a solution"""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Load solution
        solution = await _load_solution_from_source(
            solution_id=solution_id, storage_service=storage_service
        )

        # Build component hierarchy
        # Group trees by component_id
        component_trees = {}
        for tree in solution.all_trees:
            comp_id = tree.component_id or tree.component_name or str(tree.id)
            if comp_id not in component_trees:
                component_trees[comp_id] = []
            component_trees[comp_id].append(tree)

        # Build hierarchy structure
        hierarchy = []
        root_components = []
        component_details = {}

        # Find root components (no parent_tree_id or parent not in solution)
        all_tree_ids = {tree.id for tree in solution.all_trees}
        root_trees = [
            tree
            for tree in solution.all_trees
            if not tree.parent_tree_id or tree.parent_tree_id not in all_tree_ids
        ]

        # Build component details
        for comp_id, trees in component_trees.items():
            # Get representative tree (first one or highest confidence)
            rep_tree = max(trees, key=lambda t: t.confidence_score) if trees else None
            if rep_tree:
                component_details[comp_id] = {
                    "component_id": comp_id,
                    "component_name": rep_tree.component_name or comp_id,
                    "tree_count": len(trees),
                    "depth": rep_tree.depth,
                    "production_stage": rep_tree.production_stage,
                    "component_path": rep_tree.component_path,
                    "trees": [tree.to_dict() for tree in trees],
                }

        # Build hierarchy tree structure
        def build_hierarchy_node(tree: SupplyTree) -> dict:
            """Recursively build hierarchy node"""
            node = {
                "component_id": tree.component_id
                or tree.component_name
                or str(tree.id),
                "component_name": tree.component_name or "Unknown",
                "tree_id": str(tree.id),
                "depth": tree.depth,
                "production_stage": tree.production_stage,
                "children": [],
            }

            # Find children
            for child_tree in solution.all_trees:
                if child_tree.parent_tree_id == tree.id:
                    node["children"].append(build_hierarchy_node(child_tree))

            return node

        # Build hierarchy from root trees
        for root_tree in root_trees:
            hierarchy.append(build_hierarchy_node(root_tree))
            root_components.append(
                {
                    "component_id": root_tree.component_id
                    or root_tree.component_name
                    or str(root_tree.id),
                    "component_name": root_tree.component_name or "Unknown",
                    "tree_id": str(root_tree.id),
                }
            )

        logger.info(
            f"Hierarchy retrieved for solution {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "total_components": len(component_details),
                "root_components": len(root_components),
            },
        )

        return {
            "hierarchy": hierarchy,
            "root_components": root_components,
            "component_details": component_details,
            "summary": {
                "total_components": len(component_details),
                "root_components": len(root_components),
                "total_trees": len(solution.all_trees),
                "max_depth": max(
                    (tree.depth for tree in solution.all_trees), default=0
                ),
            },
        }

    except FileNotFoundError as e:
        error_response = create_error_response(
            error=f"Solution with ID {solution_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
            suggestion="Please check the solution ID and try again",
        )
        logger.error(
            f"Solution not found: {solution_id}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error retrieving hierarchy: {str(e)}",
            extra={
                "request_id": request_id,
                "solution_id": str(solution_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/{id}",
    # Note: response_model removed - api_endpoint decorator handles response wrapping
    summary="Get Supply Tree",
    description="Get a specific supply tree by ID with enhanced capabilities.",
)
@api_endpoint(
    success_message="Supply tree retrieved successfully", include_metrics=True
)
@track_performance("supply_tree_get")
async def get_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Enhanced supply tree retrieval with standardized patterns."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Load supply tree from storage
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available",
            )

        try:
            supply_tree = await storage_service.load_supply_tree(id)
        except FileNotFoundError as e:
            # Tree doesn't exist - return 404
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        if not supply_tree:
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        # Convert to response format
        # Note: SupplyTree model doesn't have a direct facility_id field.
        # We attempt to derive it from metadata or okw_reference.
        # If unavailable, we use None (which is acceptable for the response model).
        facility_id = None
        if supply_tree.metadata and "facility_id" in supply_tree.metadata:
            try:
                facility_id = UUID(supply_tree.metadata["facility_id"])
            except (ValueError, TypeError):
                pass

        # If still no facility_id, try to parse from okw_reference if it's a UUID
        if not facility_id and supply_tree.okw_reference:
            try:
                facility_id = UUID(supply_tree.okw_reference)
            except (ValueError, TypeError):
                pass

        # If still no facility_id, use the standard nil UUID (all-zeros) as a sentinel value
        # Note: Response model requires UUID (not Optional), so we use the standard nil UUID
        # (00000000-0000-0000-0000-000000000000) which is the standard way to represent "no UUID"
        # Clients can check for this value to detect when facility_id is not available
        if not facility_id:
            facility_id = UUID("00000000-0000-0000-0000-000000000000")

        response_data = {
            "id": str(supply_tree.id),
            "facility_id": str(facility_id),
            "facility_name": supply_tree.facility_name,
            "okh_reference": supply_tree.okh_reference,
            "confidence_score": supply_tree.confidence_score,
            "estimated_cost": supply_tree.estimated_cost,
            "estimated_time": supply_tree.estimated_time,
            "materials_required": supply_tree.materials_required,
            "capabilities_used": supply_tree.capabilities_used,
            "match_type": supply_tree.match_type,
            "metadata": supply_tree.metadata,
            "creation_time": supply_tree.creation_time.isoformat(),
        }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error getting supply tree {id}: {str(e)}",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List Supply Trees",
    description="""
    Get a paginated list of supply trees with enhanced capabilities.
    
    **Features:**
    - Paginated results with sorting and filtering
    - Enhanced error handling
    - Performance metrics
    - Validation
    """,
)
@api_endpoint(success_message="Supply trees listed successfully", include_metrics=True)
@paginated_response(default_page_size=20, max_page_size=100)
async def list_supply_trees(
    pagination: PaginationParams = Depends(),
    filter: Optional[str] = Query(None, description="Filter criteria"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Enhanced supply tree listing with pagination and metrics."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Check storage service availability
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available",
            )

        # List supply trees from storage (pagination handled by StorageService)
        try:
            supply_tree_list = await storage_service.list_supply_trees(
                limit=pagination.page_size,
                offset=(pagination.page - 1) * pagination.page_size,
            )
        except RuntimeError as e:
            # Storage service not configured
            if "not configured" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Storage service not configured",
                )
            raise
        except Exception as e:
            # Handle other storage errors (e.g., connection issues, permission errors)
            logger.error(
                f"Error listing supply trees from storage: {str(e)}",
                extra={"request_id": request_id, "error": str(e)},
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Storage service error: {str(e)}",
            )

        # Convert to response format
        # StorageService returns list of dicts with: id, okh_reference, last_modified
        # We need to convert to items with more fields
        results = []
        for tree_info in supply_tree_list:
            if isinstance(tree_info, dict):
                # Create item from available metadata
                item = {
                    "id": tree_info.get("id"),
                    "okh_reference": tree_info.get("okh_reference"),
                }

                # Convert last_modified to ISO format string if it's a datetime
                last_modified = tree_info.get("last_modified")
                if last_modified is not None:
                    if isinstance(last_modified, datetime):
                        item["last_modified"] = last_modified.isoformat()
                    else:
                        item["last_modified"] = str(last_modified)

                # Add optional fields if available
                if "facility_name" in tree_info:
                    item["facility_name"] = tree_info["facility_name"]
                if "confidence_score" in tree_info:
                    item["confidence_score"] = tree_info["confidence_score"]
                if "match_type" in tree_info:
                    item["match_type"] = tree_info["match_type"]
                if "creation_time" in tree_info:
                    creation_time = tree_info["creation_time"]
                    if isinstance(creation_time, datetime):
                        item["creation_time"] = creation_time.isoformat()
                    else:
                        item["creation_time"] = str(creation_time)
                elif "last_modified" in tree_info:
                    # Use last_modified as creation_time if available
                    creation_time = tree_info["last_modified"]
                    if isinstance(creation_time, datetime):
                        item["creation_time"] = creation_time.isoformat()
                    else:
                        item["creation_time"] = str(creation_time)

                results.append(item)

        # Return list for paginated_response decorator to handle
        # The decorator will wrap this in a PaginatedResponse
        return results

    except HTTPException:
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error listing supply trees: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.put(
    "/{id}",
    summary="Update Supply Tree",
    description="Update an existing supply tree with enhanced capabilities.",
)
# @api_endpoint(
#     success_message="Supply tree updated successfully",
#     include_metrics=True
# )
# @track_performance("supply_tree_update")
async def update_supply_tree(
    request: SupplyTreeCreateRequest,
    id: UUID = Path(..., title="The ID of the supply tree"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(get_okh_service),
    okw_service: OKWService = Depends(get_okw_service),
):
    """Enhanced supply tree update with standardized patterns."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )
    start_time = datetime.now()

    try:
        # Check storage service availability
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available",
            )

        # Load existing supply tree
        try:
            existing_tree = await storage_service.load_supply_tree(id)
        except Exception as e:
            # If load fails, tree doesn't exist
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        if not existing_tree:
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        # Update fields from request
        logger.info(
            f"Update request received: facility_name={request.facility_name}, facility_id={request.facility_id}"
        )
        logger.info(
            f"Existing tree before update: facility_name={existing_tree.facility_name}"
        )

        # Update facility_name if provided (do this first so it takes precedence)
        if request.facility_name:
            existing_tree.facility_name = request.facility_name
            logger.info(f"Updated facility_name to: {request.facility_name}")

        # Update facility if facility_id is provided
        if request.facility_id:
            facility = await okw_service.get(request.facility_id)
            if facility:
                # Update facility-related fields from the facility
                existing_tree.okw_reference = str(facility.id)
                # Only update facility_name from facility if it wasn't explicitly provided in request
                if not request.facility_name:
                    existing_tree.facility_name = facility.name
            else:
                logger.info(
                    f"Facility {request.facility_id} not found, skipping facility update"
                )

        logger.info(
            f"Existing tree after update: facility_name={existing_tree.facility_name}"
        )

        # Update OKH reference if provided
        if request.okh_reference:
            existing_tree.okh_reference = request.okh_reference
            # Try to load OKH manifest if it's a UUID
            try:
                okh_manifest = await okh_service.get(UUID(request.okh_reference))
                if okh_manifest:
                    # Update any OKH-related fields if needed
                    pass
            except (ValueError, TypeError):
                # If okh_reference is not a valid UUID, treat it as a reference string
                pass

        # Update other fields if provided
        if request.confidence_score is not None:
            existing_tree.confidence_score = request.confidence_score

        if request.estimated_cost is not None:
            existing_tree.estimated_cost = request.estimated_cost

        if request.estimated_time:
            existing_tree.estimated_time = request.estimated_time

        if request.materials_required:
            existing_tree.materials_required = request.materials_required

        if request.capabilities_used:
            existing_tree.capabilities_used = request.capabilities_used

        if request.match_type:
            existing_tree.match_type = request.match_type

        if request.metadata:
            existing_tree.metadata.update(request.metadata)

        # Save updated tree
        await storage_service.save_supply_tree(existing_tree)
        logger.info(f"Saved tree with facility_name: {existing_tree.facility_name}")

        # Reload tree to ensure we have the latest version
        existing_tree = await storage_service.load_supply_tree(id)
        logger.info(f"Reloaded tree with facility_name: {existing_tree.facility_name}")

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Convert okw_reference to facility_id for response
        facility_id = None
        if existing_tree.okw_reference:
            try:
                facility_id = UUID(existing_tree.okw_reference)
            except (ValueError, TypeError):
                # If okw_reference is not a valid UUID, try to get facility from service
                if request and request.facility_id:
                    facility_id = request.facility_id
                else:
                    # Use a default UUID if we can't determine facility_id
                    facility_id = UUID("00000000-0000-0000-0000-000000000000")
        elif request and request.facility_id:
            facility_id = request.facility_id
        else:
            # Use a default UUID if we can't determine facility_id
            facility_id = UUID("00000000-0000-0000-0000-000000000000")

        # Create response data using the same format as create endpoint
        response_data = {
            "id": str(existing_tree.id),
            "facility_id": str(facility_id),
            "facility_name": existing_tree.facility_name,
            "okh_reference": existing_tree.okh_reference,
            "confidence_score": existing_tree.confidence_score,
            "creation_time": existing_tree.creation_time.isoformat(),
            "estimated_cost": existing_tree.estimated_cost,
            "estimated_time": existing_tree.estimated_time,
            "materials_required": existing_tree.materials_required,
            "capabilities_used": existing_tree.capabilities_used,
            "match_type": existing_tree.match_type,
            "metadata": existing_tree.metadata,
        }

        logger.info(
            f"Supply tree updated successfully",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(existing_tree.id),
                "facility_id": str(facility_id),
                "okh_reference": existing_tree.okh_reference,
                "processing_time": processing_time,
            },
        )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error updating supply tree {id}: {str(e)}",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.delete(
    "/{id}",
    response_model=SuccessResponse,
    summary="Delete Supply Tree",
    description="Delete a supply tree with enhanced capabilities.",
)
@api_endpoint(success_message="Supply tree deleted successfully", include_metrics=True)
@track_performance("supply_tree_delete")
async def delete_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Enhanced supply tree deletion with standardized patterns."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Check storage service availability
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available",
            )

        # Check if supply tree exists
        try:
            existing_tree = await storage_service.load_supply_tree(id)
        except Exception as e:
            # If load fails, tree doesn't exist
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        if not existing_tree:
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        # Delete from storage
        try:
            deleted = await storage_service.delete_supply_tree(id)
            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete supply tree",
                )
        except RuntimeError as e:
            # Storage service not configured
            if "not configured" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Storage service not configured",
                )
            raise
        except Exception as e:
            logger.error(
                f"Error deleting supply tree {id} from storage: {str(e)}",
                extra={
                    "request_id": request_id,
                    "supply_tree_id": str(id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete supply tree: {str(e)}",
            )

        logger.info(
            f"Deleted supply tree {id}",
            extra={"request_id": request_id, "supply_tree_id": str(id)},
        )

        return create_success_response(
            message=f"Supply tree with ID {id} deleted successfully",
            data={},
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error deleting supply tree {id}: {str(e)}",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post(
    "/{id}/validate",
    summary="Validate Supply Tree",
    description="Validate a supply tree against specified requirements and capabilities with enhanced capabilities.",
)
@api_endpoint(
    success_message="Supply tree validation completed successfully",
    include_metrics=True,
)
@track_performance("supply_tree_validate")
async def validate_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    validate_request: SupplyTreeValidateRequest = None,
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Enhanced supply tree validation with standardized patterns."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )
    start_time = datetime.now()

    try:
        # Check storage service availability
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available",
            )

        # Load supply tree
        try:
            supply_tree = await storage_service.load_supply_tree(id)
        except Exception as e:
            # If load fails, tree doesn't exist
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        if not supply_tree:
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        # Get domain from request or default to manufacturing
        domain = (
            getattr(validate_request, "domain", "manufacturing")
            if validate_request
            else "manufacturing"
        )
        quality_level = (
            getattr(validate_request, "quality_level", "professional")
            if validate_request
            else "professional"
        )
        strict_mode = (
            getattr(validate_request, "strict_mode", False)
            if validate_request
            else False
        )

        # Get domain validator from registry
        from ...registry.domain_registry import DomainRegistry

        if domain not in DomainRegistry.list_domains():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Domain {domain} is not registered",
            )

        # Use ValidationEngine to validate supply tree
        from ...validation.context import ValidationContext
        from ...validation.engine import ValidationEngine

        # Create validation context
        context = ValidationContext(
            name=f"supply_tree_validation_{id}",
            domain=domain,
            quality_level=quality_level,
            strict_mode=strict_mode,
        )

        # Use ValidationEngine to validate
        validation_engine = ValidationEngine()
        validation_result = await validation_engine.validate(
            data=supply_tree, validation_type="supply_tree", context=context
        )

        # Convert validation result to API format
        issues = []

        # Add errors
        if hasattr(validation_result, "errors") and validation_result.errors:
            for error in validation_result.errors:
                issues.append(
                    {
                        "type": "error",
                        "message": (
                            str(error)
                            if isinstance(error, str)
                            else getattr(error, "message", str(error))
                        ),
                        "field": (
                            getattr(error, "field", None)
                            if hasattr(error, "field")
                            else None
                        ),
                    }
                )

        # Add warnings
        if hasattr(validation_result, "warnings") and validation_result.warnings:
            for warning in validation_result.warnings:
                issues.append(
                    {
                        "type": "warning",
                        "message": (
                            str(warning)
                            if isinstance(warning, str)
                            else getattr(warning, "message", str(warning))
                        ),
                        "field": (
                            getattr(warning, "field", None)
                            if hasattr(warning, "field")
                            else None
                        ),
                    }
                )

        # Calculate confidence score
        confidence = 0.8  # Default
        if hasattr(validation_result, "confidence"):
            confidence = validation_result.confidence
        elif hasattr(validation_result, "score"):
            confidence = validation_result.score

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Create validation result response as a dictionary
        # The @api_endpoint decorator will wrap this in SuccessResponse
        valid = validation_result.valid if hasattr(validation_result, "valid") else True
        validation_response = {
            "validation_result": {
                "valid": valid,
                "confidence": confidence,
                "issues": issues,
            }
        }

        logger.info(
            f"Supply tree validation completed",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "domain": domain,
                "quality_level": quality_level,
                "valid": valid,
                "confidence": confidence,
                "issue_count": len(issues),
                "processing_time": processing_time,
            },
        )

        return create_success_response(
            message="Supply tree validation completed successfully",
            data=validation_response,
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error validating supply tree {id}: {str(e)}",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


# Helper functions
async def _validate_supply_tree_result(
    result: any, request_id: str
) -> List[BaseValidationResult]:
    """Validate supply tree operation result."""
    try:
        validation_results = []

        # Basic validation
        is_valid = True
        from ..models.base import ErrorCode, ErrorDetail

        errors = []
        warnings = []
        suggestions = []

        # Check if result exists
        if not result:
            is_valid = False
            errors.append(
                ErrorDetail(
                    message="No result returned from operation",
                    code=ErrorCode.INTERNAL_ERROR,
                )
            )

        # Check required fields if result is a dict
        if isinstance(result, dict):
            if not result.get("id"):
                warnings.append("Missing supply tree ID in result")

            if not result.get("facility_id"):
                warnings.append("Missing facility ID in result")

            if not result.get("facility_name"):
                warnings.append("Missing facility name in result")

            if not result.get("okh_reference"):
                warnings.append("Missing OKH reference in result")

            if result.get("confidence_score") is None:
                warnings.append("Missing confidence score in result")
            elif not isinstance(result.get("confidence_score"), (int, float)):
                warnings.append("Invalid confidence score type in result")

        # Generate suggestions
        if not is_valid:
            suggestions.append("Review the input data and try again")

        validation_result = BaseValidationResult(
            is_valid=is_valid,
            score=1.0 if is_valid else 0.5,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

        validation_results.append(validation_result)

        return validation_results

    except Exception as e:
        logger.error(
            f"Error validating supply tree result: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        return []


@router.post(
    "/{id}/optimize",
    summary="Optimize Supply Tree",
    description="""
    Optimize a supply tree based on specific criteria.
    
    This endpoint optimizes an existing supply tree by adjusting parameters
    based on optimization criteria (cost, time, quality).
    """,
)
@api_endpoint(
    success_message="Supply tree optimized successfully", include_metrics=True
)
@track_performance("supply_tree_optimize")
async def optimize_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    optimize_request: SupplyTreeOptimizeRequest = Body(...),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(get_okh_service),
    okw_service: OKWService = Depends(get_okw_service),
):
    """Optimize a supply tree based on criteria."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )
    start_time = datetime.now()

    try:
        # Load supply tree from storage
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available",
            )

        try:
            supply_tree = await storage_service.load_supply_tree(id)
        except FileNotFoundError:
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        if not supply_tree:
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        # Extract optimization criteria
        criteria = optimize_request.criteria
        priority = criteria.get("priority", "cost")
        weights = criteria.get("weights", {})

        # Validate priority
        valid_priorities = ["cost", "time", "quality"]
        if priority not in valid_priorities:
            error_response = create_error_response(
                error=f"Invalid priority '{priority}'. Must be one of: {', '.join(valid_priorities)}",
                status_code=status.HTTP_400_BAD_REQUEST,
                request_id=request_id,
                suggestion=f"Please use one of the valid priorities: {', '.join(valid_priorities)}",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response.model_dump(mode="json"),
            )

        # Apply optimization based on priority
        # For now, we'll adjust the confidence score and estimated values
        # In a full implementation, this would re-run matching with different weights

        optimized_tree = supply_tree

        # Calculate optimization metrics
        optimization_metrics = {
            "cost": supply_tree.estimated_cost or 0.0,
            "time": supply_tree.estimated_time or "unknown",
            "quality_score": supply_tree.confidence_score,
        }

        # Adjust based on priority (simplified optimization)
        if priority == "cost" and supply_tree.estimated_cost:
            # Cost optimization: reduce cost by 10% (simplified)
            optimization_metrics["cost"] = supply_tree.estimated_cost * 0.9
        elif priority == "time" and supply_tree.estimated_time:
            # Time optimization: reduce time by 10% (simplified)
            optimization_metrics["time"] = (
                supply_tree.estimated_time
            )  # Keep same for now
        elif priority == "quality":
            # Quality optimization: increase confidence score
            optimization_metrics["quality_score"] = min(
                1.0, supply_tree.confidence_score * 1.1
            )

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Prepare response data
        response_data = {
            "id": str(supply_tree.id),
            "facility_name": supply_tree.facility_name,
            "okh_reference": supply_tree.okh_reference,
            "confidence_score": supply_tree.confidence_score,
            "estimated_cost": supply_tree.estimated_cost,
            "estimated_time": supply_tree.estimated_time,
            "materials_required": supply_tree.materials_required,
            "capabilities_used": supply_tree.capabilities_used,
            "match_type": supply_tree.match_type,
            "metadata": supply_tree.metadata,
            "optimization_metrics": optimization_metrics,
            "processing_time": processing_time,
        }

        logger.info(
            f"Supply tree optimized successfully",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "priority": priority,
                "processing_time": processing_time,
            },
        )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error optimizing supply tree {id}: {str(e)}",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/{id}/export",
    summary="Export Supply Tree",
    description="""
    Export a supply tree to a specific format.
    
    Supported formats:
    - json: JSON format (default)
    - xml: XML format
    - graphml: GraphML format for graph visualization
    """,
)
@api_endpoint(success_message="Supply tree exported successfully", include_metrics=True)
@track_performance("supply_tree_export")
async def export_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    format: str = Query("json", description="Export format (json, xml, graphml)"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
):
    """Export a supply tree in the requested format."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Validate format
        valid_formats = ["json", "xml", "graphml"]
        if format.lower() not in valid_formats:
            error_response = create_error_response(
                error=f"Invalid format '{format}'. Supported formats: {', '.join(valid_formats)}",
                status_code=status.HTTP_400_BAD_REQUEST,
                request_id=request_id,
                suggestion=f"Please use one of the supported formats: {', '.join(valid_formats)}",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response.model_dump(mode="json"),
            )

        # Load supply tree from storage
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available",
            )

        try:
            supply_tree = await storage_service.load_supply_tree(id)
        except FileNotFoundError:
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        if not supply_tree:
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        # Convert to dictionary
        tree_dict = supply_tree.to_dict()

        # Export in requested format
        format_lower = format.lower()
        if format_lower == "json":
            content = json.dumps(tree_dict, indent=2, default=str)
            media_type = "application/json"
        elif format_lower == "xml":
            # Simple XML export
            content = _dict_to_xml(tree_dict, root_name="supply_tree")
            media_type = "application/xml"
        elif format_lower == "graphml":
            # GraphML export for graph visualization
            content = _dict_to_graphml(tree_dict)
            media_type = "application/xml"
        else:
            # Should not reach here due to validation above
            content = json.dumps(tree_dict, indent=2, default=str)
            media_type = "application/json"

        logger.info(
            f"Supply tree exported successfully in {format} format",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "format": format,
            },
        )

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="supply_tree_{id}.{format_lower}"'
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error exporting supply tree {id}: {str(e)}",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "format": format,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


def _dict_to_xml(data: dict, root_name: str = "root") -> str:
    """Convert dictionary to XML format."""

    def escape_xml(text):
        """Escape XML special characters."""
        if text is None:
            return ""
        text = str(text)
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&apos;")
        return text

    def dict_to_xml_recursive(d, parent_tag="item"):
        """Recursively convert dict to XML."""
        xml_parts = []
        if isinstance(d, dict):
            for key, value in d.items():
                # Sanitize key name for XML
                tag = str(key).replace(" ", "_").replace("-", "_")
                if isinstance(value, (dict, list)):
                    xml_parts.append(f"<{tag}>")
                    xml_parts.append(dict_to_xml_recursive(value, tag))
                    xml_parts.append(f"</{tag}>")
                else:
                    xml_parts.append(f"<{tag}>{escape_xml(value)}</{tag}>")
        elif isinstance(d, list):
            for item in d:
                xml_parts.append(f"<{parent_tag}>")
                xml_parts.append(dict_to_xml_recursive(item, parent_tag))
                xml_parts.append(f"</{parent_tag}>")
        else:
            xml_parts.append(escape_xml(d))
        return "".join(xml_parts)

    xml_content = f'<?xml version="1.0" encoding="UTF-8"?>\n<{root_name}>\n'
    xml_content += dict_to_xml_recursive(data, root_name)
    xml_content += f"\n</{root_name}>"
    return xml_content


def _dict_to_graphml(data: dict) -> str:
    """Convert dictionary to GraphML format for graph visualization."""
    # GraphML header
    graphml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    graphml += '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"\n'
    graphml += '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
    graphml += '         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns\n'
    graphml += '         http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">\n'

    # Define attributes
    graphml += '  <key id="name" for="node" attr.name="name" attr.type="string"/>\n'
    graphml += '  <key id="type" for="node" attr.name="type" attr.type="string"/>\n'
    graphml += '  <key id="value" for="node" attr.name="value" attr.type="string"/>\n'

    # Create graph
    graphml += '  <graph id="supply_tree" edgedefault="directed">\n'

    # Add nodes for key fields
    node_id = 0
    if "id" in data:
        graphml += f'    <node id="n{node_id}">\n'
        graphml += f'      <data key="name">ID</data>\n'
        graphml += f'      <data key="type">id</data>\n'
        graphml += f'      <data key="value">{data["id"]}</data>\n'
        graphml += "    </node>\n"
        node_id += 1

    if "facility_name" in data:
        graphml += f'    <node id="n{node_id}">\n'
        graphml += f'      <data key="name">Facility</data>\n'
        graphml += f'      <data key="type">facility</data>\n'
        graphml += f'      <data key="value">{data["facility_name"]}</data>\n'
        graphml += "    </node>\n"
        node_id += 1

    if "okh_reference" in data:
        graphml += f'    <node id="n{node_id}">\n'
        graphml += f'      <data key="name">OKH Reference</data>\n'
        graphml += f'      <data key="type">okh</data>\n'
        graphml += f'      <data key="value">{data["okh_reference"]}</data>\n'
        graphml += "    </node>\n"
        node_id += 1

    # Add edges (simplified - just connect main nodes)
    if node_id >= 2:
        graphml += '    <edge id="e0" source="n0" target="n1"/>\n'
    if node_id >= 3:
        graphml += '    <edge id="e1" source="n0" target="n2"/>\n'

    graphml += "  </graph>\n"
    graphml += "</graphml>"

    return graphml


def _solution_to_graphml(solution) -> str:
    """Convert SupplyTreeSolution to GraphML format with nested relationships."""
    # GraphML header
    graphml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    graphml += '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"\n'
    graphml += '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
    graphml += '         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns\n'
    graphml += '         http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">\n'

    # Define node attributes
    graphml += '  <key id="component_name" for="node" attr.name="component_name" attr.type="string"/>\n'
    graphml += '  <key id="component_id" for="node" attr.name="component_id" attr.type="string"/>\n'
    graphml += '  <key id="facility_name" for="node" attr.name="facility_name" attr.type="string"/>\n'
    graphml += '  <key id="okh_reference" for="node" attr.name="okh_reference" attr.type="string"/>\n'
    graphml += '  <key id="confidence_score" for="node" attr.name="confidence_score" attr.type="double"/>\n'
    graphml += '  <key id="depth" for="node" attr.name="depth" attr.type="int"/>\n'
    graphml += '  <key id="production_stage" for="node" attr.name="production_stage" attr.type="string"/>\n'
    graphml += '  <key id="estimated_cost" for="node" attr.name="estimated_cost" attr.type="double"/>\n'
    graphml += '  <key id="estimated_time" for="node" attr.name="estimated_time" attr.type="string"/>\n'

    # Define edge attributes
    graphml += (
        '  <key id="edge_type" for="edge" attr.name="edge_type" attr.type="string"/>\n'
    )

    # Create graph
    graphml += '  <graph id="supply_tree_solution" edgedefault="directed">\n'

    # Create a mapping from tree ID to node ID for edges
    tree_id_to_node_id = {}
    node_counter = 0

    # Create nodes for all trees
    for tree in solution.all_trees:
        node_id = f"n{node_counter}"
        tree_id_to_node_id[str(tree.id)] = node_id
        node_counter += 1

        graphml += f'    <node id="{node_id}">\n'

        # Add node attributes
        if tree.component_name:
            graphml += f'      <data key="component_name">{_escape_xml(str(tree.component_name))}</data>\n'
        if tree.component_id:
            graphml += f'      <data key="component_id">{_escape_xml(str(tree.component_id))}</data>\n'
        if tree.facility_name:
            graphml += f'      <data key="facility_name">{_escape_xml(str(tree.facility_name))}</data>\n'
        if tree.okh_reference:
            graphml += f'      <data key="okh_reference">{_escape_xml(str(tree.okh_reference))}</data>\n'
        graphml += (
            f'      <data key="confidence_score">{tree.confidence_score}</data>\n'
        )
        graphml += f'      <data key="depth">{tree.depth}</data>\n'
        if tree.production_stage:
            graphml += f'      <data key="production_stage">{_escape_xml(str(tree.production_stage))}</data>\n'
        if tree.estimated_cost is not None:
            graphml += (
                f'      <data key="estimated_cost">{tree.estimated_cost}</data>\n'
            )
        if tree.estimated_time:
            graphml += f'      <data key="estimated_time">{_escape_xml(str(tree.estimated_time))}</data>\n'

        graphml += "    </node>\n"

    # Create edges for parent-child relationships
    edge_counter = 0
    for tree in solution.all_trees:
        source_node_id = tree_id_to_node_id.get(str(tree.id))
        if not source_node_id:
            continue

        # Parent-child edges (tree -> children)
        for child_id in tree.child_tree_ids:
            target_node_id = tree_id_to_node_id.get(str(child_id))
            if target_node_id:
                edge_id = f"e{edge_counter}"
                edge_counter += 1
                graphml += f'    <edge id="{edge_id}" source="{source_node_id}" target="{target_node_id}">\n'
                graphml += '      <data key="edge_type">parent-child</data>\n'
                graphml += "    </edge>\n"

        # Dependency edges (depends_on relationships)
        for dep_id in tree.depends_on:
            target_node_id = tree_id_to_node_id.get(str(dep_id))
            if target_node_id:
                edge_id = f"e{edge_counter}"
                edge_counter += 1
                graphml += f'    <edge id="{edge_id}" source="{target_node_id}" target="{source_node_id}">\n'
                graphml += '      <data key="edge_type">depends_on</data>\n'
                graphml += "    </edge>\n"

    graphml += "  </graph>\n"
    graphml += "</graphml>"

    return graphml


def _escape_xml(text: str) -> str:
    """Escape XML special characters."""
    if text is None:
        return ""
    text = str(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


async def _load_solution_from_source(
    solution_id: Optional[UUID] = None,
    file_path: Optional[str] = None,
    solution_data: Optional[dict] = None,
    storage_service: Optional[StorageService] = None,
) -> SupplyTreeSolution:
    """
    Load solution from storage, file, or inline data.

    Priority order:
    1. Storage (if solution_id and storage_service provided)
    2. Local file (if file_path provided)
    3. Inline JSON (if solution_data provided)

    Args:
        solution_id: UUID of solution in storage
        file_path: Path to local JSON file
        solution_data: Inline solution data (dict)
        storage_service: StorageService instance for loading from storage

    Returns:
        SupplyTreeSolution object

    Raises:
        ValueError: If no source provided or invalid format
        FileNotFoundError: If file_path doesn't exist
    """
    # Priority 1: Load from storage
    if solution_id and storage_service:
        return await storage_service.load_supply_tree_solution(solution_id)

    # Priority 2: Load from local file
    if file_path:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Solution file not found: {file_path}")

        with open(file_path, "r") as f:
            data = json.load(f)

        # Handle both full response format and solution-only format
        if "solution" in data:
            return SupplyTreeSolution.from_dict(data["solution"])
        elif "all_trees" in data:
            return SupplyTreeSolution.from_dict(data)
        else:
            raise ValueError(
                "Invalid solution file format: must contain 'solution' or 'all_trees' key"
            )

    # Priority 3: Use inline data
    if solution_data:
        # Handle both wrapped and direct formats
        if "solution" in solution_data:
            return SupplyTreeSolution.from_dict(solution_data["solution"])
        elif "all_trees" in solution_data:
            return SupplyTreeSolution.from_dict(solution_data)
        else:
            raise ValueError(
                "Invalid solution data format: must contain 'solution' or 'all_trees' key"
            )

    # No source provided
    raise ValueError("Must provide solution_id, file_path, or solution_data")
