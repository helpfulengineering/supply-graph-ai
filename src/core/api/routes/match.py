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
from ...services.storage_service import StorageService
from ...models.okh import OKHManifest
from ...utils.logging import get_logger

router = APIRouter(tags=["match"])

logger = get_logger(__name__)

async def get_matching_service() -> MatchingService:
    return await MatchingService.get_instance()

async def get_storage_service() -> StorageService:
    return await StorageService.get_instance()

@router.post("", response_model=MatchResponse)
async def match_requirements_to_capabilities(
    request: MatchRequest,
    matching_service: MatchingService = Depends(get_matching_service),
    storage_service: StorageService = Depends(get_storage_service)
):
    try:
        # 1. Validate the OKH manifest from the request
        if request.okh_manifest is None:
            raise HTTPException(status_code=400, detail="OKH manifest must be provided")
        try:
            request.okh_manifest.validate()
            logger.debug("OKH manifest validation successful")
        except ValueError as e:
            logger.error(f"OKH manifest validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid OKH manifest: {str(e)}")

        # 2. (Optional) Store the OKH manifest for audit/history
        try:
            okh_handler = storage_service.get_domain_handler("okh")
            await okh_handler.save(request.okh_manifest)
        except Exception as e:
            logger.warning(f"Failed to store OKH manifest: {e}")

        # 3. Load all OKW facilities from storage
        okw_handler = storage_service.get_domain_handler("okw")
        facilities = []
        try:
            okw_objects = await okw_handler.list()
            for obj in okw_objects:
                try:
                    facility = await okw_handler.load(obj["id"])
                    facilities.append(facility)
                except Exception as e:
                    logger.error(f"Failed to load OKW facility {obj['id']}: {e}")
            logger.info(f"Loaded {len(facilities)} OKW facilities from storage.")
        except Exception as e:
            logger.error(f"Failed to list/load OKW facilities: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load OKW facilities: {str(e)}")

        # 4. Run the matching logic (pass the in-memory OKH manifest and loaded OKW facilities)
        try:
            solutions = await matching_service.find_matches_with_manifest(
                okh_manifest=request.okh_manifest,
                facilities=facilities,
                optimization_criteria=request.optimization_criteria
            )
        except Exception as e:
            logger.error(f"Error during matching: {e}")
            raise HTTPException(status_code=500, detail=f"Error during matching: {str(e)}")

        # 5. Return the results
        if not solutions:
            return MatchResponse(
                supply_trees=[],
                confidence=0.0,
                metadata={
                    "message": "No matching facilities found",
                    "optimization_criteria": request.optimization_criteria
                }
            )
        return MatchResponse(
            supply_trees=[solution.tree for solution in solutions],
            confidence=sum(s.score for s in solutions) / len(solutions),
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