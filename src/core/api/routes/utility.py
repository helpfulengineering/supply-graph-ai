from fastapi import APIRouter, Path, Depends

from ..models.utility.request import (
    DomainFilterRequest,
    ContextFilterRequest
)
from ..models.utility.response import (
    DomainsResponse,
    ContextsResponse,
    Domain,
    Context
)

# Create router with prefix and tags
router = APIRouter(prefix="/v1", tags=["utility"])

@router.get("/domains", response_model=DomainsResponse)
async def get_domains(
    filter_params: DomainFilterRequest = Depends()
):
    """List available domains"""
    # Placeholder implementation
    domains = [
        Domain(
            id="manufacturing",
            name="Manufacturing Domain",
            description="Hardware manufacturing capabilities"
        ),
        Domain(
            id="cooking",
            name="Cooking Domain",
            description="Food preparation capabilities"
        )
    ]
    
    # Apply name filter if provided
    if filter_params.name:
        domains = [d for d in domains if filter_params.name.lower() in d.name.lower()]
    
    return DomainsResponse(domains=domains)

@router.get("/contexts/{domain}", response_model=ContextsResponse)
async def get_contexts(
    domain: str = Path(..., title="The domain to get contexts for"),
    filter_params: ContextFilterRequest = Depends()
):
    """List validation contexts for a specific domain"""
    # Placeholder implementation
    if domain == "manufacturing":
        contexts = [
            Context(
                id="hobby",
                name="Hobby Manufacturing",
                description="Non-commercial, limited quality requirements"
            ),
            Context(
                id="professional",
                name="Professional Manufacturing",
                description="Commercial-grade production"
            )
        ]
    elif domain == "cooking":
        contexts = [
            Context(
                id="home",
                name="Home Cooking",
                description="Basic home kitchen capabilities"
            ),
            Context(
                id="commercial",
                name="Commercial Kitchen",
                description="Professional kitchen capabilities"
            )
        ]
    else:
        contexts = []
    
    # Apply name filter if provided
    if filter_params.name:
        contexts = [c for c in contexts if filter_params.name.lower() in c.name.lower()]
    
    return ContextsResponse(contexts=contexts)