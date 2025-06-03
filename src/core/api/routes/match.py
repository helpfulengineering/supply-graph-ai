from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from ..models.match.request import (
    MatchRequest,
    ValidateMatchRequest
)
from ..models.match.response import (
    MatchResponse,
    ValidationResult
)
from ...services.matching_service import MatchingService
from ...services.okh_service import OKHService
from ...models.okh import OKHManifest
from ...utils.logging import get_logger

# Create router with prefix and tags
router = APIRouter(tags=["match"])

# Get logger for this module
logger = get_logger(__name__)

# Dependency to get matching service
async def get_matching_service() -> MatchingService:
    """Get an instance of the matching service"""
    return await MatchingService.get_instance()

# Dependency to get OKH service
async def get_okh_service() -> OKHService:
    """Get an instance of the OKH service"""
    return await OKHService.get_instance()

@router.post("", response_model=MatchResponse)
async def match_requirements_to_capabilities(
    request: MatchRequest,
    matching_service: MatchingService = Depends(get_matching_service),
    okh_service: OKHService = Depends(get_okh_service)
):
    """Match OKH requirements with OKW capabilities to generate valid supply trees"""
    try:
        # Handle direct OKH manifest submission
        if request.okh_manifest is not None:
            logger.info(
                "Processing direct OKH manifest submission",
                extra={
                    "manifest_title": request.okh_manifest.title,
                    "manifest_version": request.okh_manifest.version
                }
            )
            try:
                # Validate the OKH manifest
                request.okh_manifest.validate()
                logger.debug("OKH manifest validation successful")
                
                # Create a new OKH manifest in storage
                okh_manifest = await okh_service.create(request.okh_manifest)
                okh_id = okh_manifest.id
                logger.info(
                    "Created new OKH manifest in storage",
                    extra={"okh_id": str(okh_id)}
                )
                
            except ValueError as e:
                logger.error(
                    "OKH manifest validation failed",
                    extra={"error": str(e)},
                    exc_info=True
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid OKH manifest: {str(e)}"
                )
        else:
            # Use existing OKH manifest
            okh_id = request.okh_id
            logger.info(
                "Using existing OKH manifest",
                extra={"okh_id": str(okh_id)}
            )

        # Find matches using the OKH ID
        logger.info(
            "Finding matches for OKH manifest",
            extra={
                "okh_id": str(okh_id),
                "optimization_criteria": request.optimization_criteria
            }
        )
        solutions = await matching_service.find_matches(
            okh_id,
            optimization_criteria=request.optimization_criteria
        )
        
        if not solutions:
            logger.info(
                "No matching facilities found",
                extra={"okh_id": str(okh_id)}
            )
            return MatchResponse(
                supply_trees=[],
                confidence=0.0,
                metadata={
                    "message": "No matching facilities found",
                    "okh_id": str(okh_id),
                    "optimization_criteria": request.optimization_criteria
                }
            )
        
        logger.info(
            "Found matching facilities",
            extra={
                "okh_id": str(okh_id),
                "solution_count": len(solutions),
                "facility_count": sum(s.metrics["facility_count"] for s in solutions)
            }
        )
        
        return MatchResponse(
            supply_trees=[solution.tree for solution in solutions],
            confidence=sum(s.score for s in solutions) / len(solutions),
            metadata={
                "solution_count": len(solutions),
                "facility_count": sum(s.metrics["facility_count"] for s in solutions),
                "optimization_criteria": request.optimization_criteria,
                "okh_id": str(okh_id)
            }
        )
    except Exception as e:
        logger.error(
            "Error finding matches",
            extra={
                "okh_id": str(okh_id) if 'okh_id' in locals() else None,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error finding matches: {str(e)}"
        )

@router.post("/validate", response_model=ValidationResult)
async def validate_match(
    request: ValidateMatchRequest,
    matching_service: MatchingService = Depends(get_matching_service)
):
    """Validate an existing supply tree against requirements and capabilities"""
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