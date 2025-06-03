import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from src.core.api.routes.match import router as match_router
from src.core.api.routes.okh import router as okh_router
from src.core.api.routes.okw import router as okw_router
from src.core.api.routes.supply_tree import router as supply_tree_router
from src.core.api.routes.utility import router as utility_router

from src.core.domains.cooking.extractors import CookingExtractor
from src.core.domains.cooking.matchers import CookingMatcher
from src.core.domains.cooking.validators import CookingValidator
from src.core.domains.manufacturing.okh_extractor import OKHExtractor
from src.core.domains.manufacturing.okh_matcher import OKHMatcher
from src.core.domains.manufacturing.okh_validator import OKHValidator
from src.core.registry.domain_registry import DomainRegistry
from src.core.services.storage_service import StorageService
from src.core.services.service_registry import DomainMetadata, DomainStatus
from src.config import settings



# Initialize API key security
API_KEY_HEADER = APIKeyHeader(name="Authorization")

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize storage and register domain components
    try:
        # Initialize storage first
        storage_service = await StorageService.get_instance()
        await storage_service.configure(settings.STORAGE_CONFIG)
        
        # Then register domain components
        await register_domain_components()
        
        yield
        
        # Shutdown: Clean up resources
        await storage_service.disconnect()
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise

# Create FastAPI app with lifespan
app = FastAPI(
    title="Open Matching Engine API",
    description="API for matching OKH requirements with OKW capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define dependency for authentication
async def get_api_key(api_key: str = Depends(API_KEY_HEADER)):
    if not api_key.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token format"
        )
    
    token = api_key.replace("Bearer ", "")
    
    # TODO: Implement actual API key validation against database
    if token not in settings.API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    return token

# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "ok", 
        "domains": list(DomainRegistry.get_registered_domains()),
        "version": "1.0.0"
    }

# Create a versioned API
api_v1 = FastAPI()

# Include routers with appropriate prefixes
api_v1.include_router(match_router, prefix="/match", tags=["match"])
api_v1.include_router(okh_router, prefix="/okh", tags=["okh"])
api_v1.include_router(okw_router, prefix="/okw", tags=["okw"])
api_v1.include_router(supply_tree_router, prefix="/supply-tree", tags=["supply-tree"])
api_v1.include_router(utility_router, tags=["utility"])

# Mount the versioned API
app.mount("/v1", api_v1)

# Register domain components function (now called from lifespan)
async def register_domain_components():
    """Register all domain components with the registry."""
    
    # Register Cooking domain components
    await DomainRegistry.register_domain(
        "cooking",
        CookingExtractor(),
        CookingMatcher(),
        CookingValidator(),
        DomainMetadata(
            name="cooking",
            display_name="Cooking Domain",
            description="Domain for cooking-related matching",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"recipe", "ingredient"},
            supported_output_types={"recipe", "ingredient"}
        )
    )
    
    # Register Manufacturing domain components
    await DomainRegistry.register_domain(
        "manufacturing",
        OKHExtractor(),
        OKHMatcher(),
        OKHValidator(),
        DomainMetadata(
            name="manufacturing",
            display_name="Manufacturing Domain",
            description="Domain for manufacturing-related matching",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"okh", "okw"},
            supported_output_types={"okh", "okw"}
        )
    )

# Only run the app if this file is executed directly
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
