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
from src.core.utils.logging import setup_logging, get_logger

# Setup logging
setup_logging(
    level=settings.LOG_LEVEL,
    log_file=settings.LOG_FILE
)

# Get logger for this module
logger = get_logger(__name__)

# Initialize API key security
API_KEY_HEADER = APIKeyHeader(name="Authorization")

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application"""
    try:
        logger.info("Starting application")
        
        # Initialize storage
        logger.info("Initializing storage service")
        storage_service = await StorageService.get_instance()
        await storage_service.configure(settings.STORAGE_CONFIG)
        
        # Register domain components
        logger.info("Registering domain components")
        await register_domain_components()
        
        yield
        
    except Exception as e:
        logger.error("Error during startup", exc_info=True)
        raise
    finally:
        logger.info("Shutting down application")
        # Cleanup resources
        await cleanup_resources()

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
    DomainRegistry.register_extractor("cooking", CookingExtractor())
    DomainRegistry.register_matcher("cooking", CookingMatcher())
    DomainRegistry.register_validator("cooking", CookingValidator())
    
    # Register Manufacturing domain components
    DomainRegistry.register_extractor("manufacturing", OKHExtractor())
    DomainRegistry.register_matcher("manufacturing", OKHMatcher())
    DomainRegistry.register_validator("manufacturing", OKHValidator())

async def cleanup_resources():
    """Cleanup resources on shutdown"""
    try:
        logger.info("Cleaning up resources")
        # Add cleanup logic here
    except Exception as e:
        logger.error("Error during cleanup", exc_info=True)

# Only run the app if this file is executed directly
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
