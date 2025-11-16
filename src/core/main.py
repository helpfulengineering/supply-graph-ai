import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.api.routes.match import router as match_router
from src.core.api.routes.okh import router as okh_router
from src.core.api.routes.okw import router as okw_router
from src.core.api.routes.supply_tree import router as supply_tree_router
from src.core.api.routes.utility import router as utility_router
from src.core.api.routes.package import router as package_router

# Import new standardized API components
from src.core.api.error_handlers import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from src.core.api.middleware import setup_api_middleware
# from src.core.errors.metrics import MetricsTracker  # TODO: Implement MetricsTracker
from src.core.api.dependencies import get_current_user, get_optional_user

from src.core.domains.cooking.extractors import CookingExtractor
from src.core.domains.cooking.matchers import CookingMatcher
from src.core.domains.manufacturing.okh_extractor import OKHExtractor
from src.core.domains.manufacturing.okh_matcher import OKHMatcher

# Import new enhanced validators with compatibility layers
from src.core.domains.manufacturing.validation.compatibility import ManufacturingOKHValidatorCompat
from src.core.domains.cooking.validation.compatibility import CookingValidatorCompat
from src.core.registry.domain_registry import DomainRegistry
from src.core.services.storage_service import StorageService
from src.core.services.auth_service import AuthenticationService
from src.core.registry.domain_registry import DomainMetadata, DomainStatus
from src.config import settings
from src.core.utils.logging import setup_logging, get_logger

# Setup logging
setup_logging(
    level=settings.LOG_LEVEL,
    log_file=settings.LOG_FILE
)

# Get logger for this module
logger = get_logger(__name__)

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
        
        # Initialize authentication service
        logger.info("Initializing authentication service")
        await AuthenticationService.get_instance()
        
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

# Set up standardized error handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Set up API middleware
# metrics_tracker = MetricsTracker()  # TODO: Implement MetricsTracker
setup_api_middleware(app, None)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Open Matching Engine API",
        "version": "1.0.0",
        "docs": {
            "main": "/docs",
            "v1": "/v1/docs"
        },
        "health": "/health",
        "api": "/v1"
    }

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
api_v1 = FastAPI(
    title="Open Matching Engine API v1",
    description="Version 1 of the Open Matching Engine API",
    version="1.0.0"
)

# Include routers - those with prefixes don't need additional prefixes
api_v1.include_router(match_router, prefix="/api/match", tags=["match"])
api_v1.include_router(okh_router, prefix="/api/okh", tags=["okh"])
api_v1.include_router(okw_router, prefix="/api/okw", tags=["okw"])
api_v1.include_router(supply_tree_router, tags=["supply-tree"])  # Already has /api/supply-tree prefix
api_v1.include_router(utility_router, tags=["utility"])  # Already has /api/utility prefix
api_v1.include_router(package_router, tags=["package"])  # Already has /api/package prefix

# Mount the versioned API
app.mount("/v1", api_v1)

# Register domain components function (now called from lifespan)
async def register_domain_components():
    """Register all domain components with the unified registry."""
    
    # Register Cooking domain
    cooking_metadata = DomainMetadata(
        name="cooking",
        display_name="Cooking & Food Preparation",
        description="Domain for recipe and kitchen capability matching",
        version="1.0.0",
        status=DomainStatus.ACTIVE,
        supported_input_types={"recipe", "kitchen"},
        supported_output_types={"cooking_workflow", "meal_plan"},
        documentation_url="https://docs.ome.org/domains/cooking",
        maintainer="OME Cooking Team"
    )
    
    DomainRegistry.register_domain(
        domain_name="cooking",
        extractor=CookingExtractor(),
        matcher=CookingMatcher(),
        validator=CookingValidatorCompat(),
        metadata=cooking_metadata
    )
    
    # Register Manufacturing domain
    manufacturing_metadata = DomainMetadata(
        name="manufacturing",
        display_name="Manufacturing & Hardware Production",
        description="Domain for OKH/OKW manufacturing capability matching",
        version="1.0.0",
        status=DomainStatus.ACTIVE,
        supported_input_types={"okh", "okw"},
        supported_output_types={"supply_tree", "manufacturing_plan"},
        documentation_url="https://docs.ome.org/domains/manufacturing",
        maintainer="OME Manufacturing Team"
    )
    
    DomainRegistry.register_domain(
        domain_name="manufacturing",
        extractor=OKHExtractor(),
        matcher=OKHMatcher(),
        validator=ManufacturingOKHValidatorCompat(),
        metadata=manufacturing_metadata
    )

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
