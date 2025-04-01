from fastapi import APIRouter, HTTPException
from ..models.match.request import RequirementsInput, CapabilitiesInput
from ..models.match.response import SupplyTreeResponse
from ...services.matching_service import MatchingService

router = APIRouter()

@router.post("/match", response_model=SupplyTreeResponse)
async def match_requirements_to_capabilities(
    requirements: RequirementsInput, 
    capabilities: CapabilitiesInput
):
    """
    Match requirements to capabilities and generate a SupplyTree solution.
    """
    try:
        return await MatchingService.match(requirements, capabilities)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
