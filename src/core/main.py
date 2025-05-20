from fastapi import FastAPI
from src.core.api.routes.match import router as match_router
from src.core.domains.cooking.extractors import CookingExtractor
from src.core.domains.cooking.matchers import CookingMatcher
from src.core.domains.cooking.validators import CookingValidator
from src.core.registry.domain_registry import DomainRegistry
from src.core.api.routes.llm import router as llm_router

# Create FastAPI app
app = FastAPI(title="Open Matching Engine API")

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "domains": list(DomainRegistry._extractors.keys())}

# Register routes
app.include_router(match_router, tags=["matching"])
app.include_router(llm_router, tags=["llm"])

# Register domain components
DomainRegistry.register_extractor("cooking", CookingExtractor())
DomainRegistry.register_matcher("cooking", CookingMatcher())
DomainRegistry.register_validator("cooking", CookingValidator())

# Add manufacturing components when ready
# DomainRegistry.register_extractor("manufacturing", ManufacturingExtractor())
# DomainRegistry.register_matcher("manufacturing", ManufacturingMatcher())
# DomainRegistry.register_validator("manufacturing", ManufacturingValidator())