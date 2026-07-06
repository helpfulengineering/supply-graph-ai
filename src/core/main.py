import asyncio
import json
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.config import settings

# Import new standardized API components
from src.core.api.error_handlers import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from src.core.api.middleware import setup_api_middleware
from src.core.api.routes.convert import router as convert_router
from src.core.api.routes.federation import router as federation_router
from src.core.api.routes.llm import router as llm_router
from src.core.api.routes.match import router as match_router
from src.core.api.routes.asset import router as asset_router
from src.core.api.routes.okh import router as okh_router
from src.core.api.routes.okw import router as okw_router
from src.core.api.routes.package import router as package_router
from src.core.api.routes.rfq import router as rfq_router
from src.core.api.routes.rules import router as rules_router
from src.core.api.routes.supply_tree import router as supply_tree_router
from src.core.api.routes.taxonomy import router as taxonomy_router
from src.core.api.routes.utility import router as utility_router
from src.core.domains.cooking.extractors import CookingExtractor
from src.core.domains.cooking.matchers import CookingMatcher
from src.core.domains.cooking.validation.compatibility import CookingValidatorCompat
from src.core.domains.manufacturing.okh_extractor import OKHExtractor
from src.core.domains.manufacturing.okh_matcher import OKHMatcher

# Import new enhanced validators with compatibility layers
from src.core.domains.manufacturing.validation.compatibility import (
    ManufacturingOKHValidatorCompat,
)
from src.core.errors.metrics import get_metrics_tracker
from src.core.registry.domain_registry import (
    DomainMetadata,
    DomainRegistry,
    DomainStatus,
)
from src.core.services.auth_service import AuthenticationService
from src.core.services.storage_service import StorageService
from src.core.utils.logging import get_logger, setup_logging

from .version import get_version

# Setup logging - convert string LOG_LEVEL to integer
_log_level_str = (
    settings.LOG_LEVEL.upper() if isinstance(settings.LOG_LEVEL, str) else "INFO"
)
_log_level_int = getattr(logging, _log_level_str, logging.INFO)
setup_logging(level=_log_level_int, log_file=settings.LOG_FILE)

# Get logger for this module
logger = get_logger(__name__)


# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application with graceful shutdown.

    Uvicorn handles SIGTERM/SIGINT signals and will call the shutdown phase
    of this lifespan context manager. We don't need to handle signals directly.
    """
    try:
        logger.info("Starting application")

        # Startup posture: validate config before anything else. Hard-fails in
        # production on invalid/missing config; warns and degrades otherwise.
        from src.config.schema import enforce_startup_config

        enforce_startup_config()

        # Initialize storage
        logger.info("Initializing storage service")
        storage_service = await StorageService.get_instance()
        try:
            await storage_service.configure(settings.STORAGE_CONFIG)
        except Exception as e:
            # Storage connection failure shouldn't prevent app startup
            # Log error but continue - storage operations will fail gracefully
            logger.warning(
                f"Storage service initialization failed: {e}. "
                f"Application will start but storage operations may be unavailable. "
                f"This may be a temporary network issue."
            )

        # Ensure directory structure exists (lazy initialization)
        # This allows the application to self-bootstrap on first run
        try:
            from .storage.organizer import StorageOrganizer

            organizer = StorageOrganizer(storage_service.manager)
            # Check if structure exists by looking for a known placeholder
            try:
                await storage_service.manager.get_object("okh/manifests/.gitkeep")
                logger.debug("Storage directory structure already exists")
            except FileNotFoundError:
                logger.info("Storage directory structure not found, creating it...")
                result = await organizer.create_directory_structure()
                logger.info(f"Created {result['total_created']} directories in storage")
        except Exception as e:
            # Log but don't fail startup - directory structure is not critical
            logger.warning(
                f"Failed to ensure directory structure exists: {e}. Continuing startup...",
                exc_info=True,  # Include full traceback for debugging
            )

        # Initialize authentication service
        logger.info("Initializing authentication service")
        await AuthenticationService.get_instance()

        # Register domain components
        logger.info("Registering domain components")
        await register_domain_components()

        if settings.OHM_FEDERATION_ENABLED:
            from .federation.service import FederationService

            logger.info(
                "Federation enabled (OHM_FEDERATION_ENABLED=true); "
                f"data_dir={settings.OHM_FEDERATION_DATA_DIR}"
            )
            try:
                from src.config.settings import API_PORT

                fed = await FederationService.get_instance()
                if fed.identity:
                    logger.info(f"Federation node DID: {fed.identity.did}")
                fed.start_mdns(API_PORT)
                fed.start_sync_loop()
            except Exception as e:
                logger.error(
                    "Federation failed to initialize (API will continue; "
                    "/v1/api/federation/* may return errors): %s",
                    e,
                    exc_info=True,
                )
        else:
            logger.info(
                "Federation disabled (set OHM_FEDERATION_ENABLED=true in the "
                "server process environment to enable /v1/api/federation/*)"
            )

        logger.info("Application startup complete")

        yield

    except Exception as e:
        logger.error("Error during startup", exc_info=True)
        raise
    finally:
        logger.info("Shutting down application")
        # Cleanup resources
        # Uvicorn will wait for in-flight requests to complete before calling this
        await cleanup_resources()
        logger.info("Application shutdown complete")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Open Hardware Manager API",
    description="API for matching OKH requirements with OKW capabilities",
    version=get_version(),
    lifespan=lifespan,
)

# Set up standardized error handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Set up API middleware
metrics_tracker = get_metrics_tracker()
setup_api_middleware(app, metrics_tracker)

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
        "message": "Open Hardware Manager API",
        "version": get_version(),
        "docs": {"main": "/docs", "v1": "/v1/docs"},
        "health": "/health",
        "api": "/v1",
    }


# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint with a storage-config fingerprint.

    Always returns 200 when the process is up (suitable as a liveness probe).
    Also reports the resolved storage target (provider / account / container) and
    object counts under ``okh/``/``okw/`` so config/data drift is visible from a
    public endpoint and can be asserted by the deploy gate. The fingerprint is
    best-effort and time-boxed — storage being down or slow never fails /health.
    """
    result = {
        "status": "ok",
        "domains": list(DomainRegistry.get_registered_domains()),
        "version": get_version(),
    }
    try:
        storage_service = await StorageService.get_instance()
        result["storage"] = await asyncio.wait_for(
            storage_service.get_config_fingerprint(), timeout=5.0
        )
    except Exception as e:
        result["storage"] = {"error": str(e)}
    return result


# Liveness probe endpoint
@app.get("/health/liveness", tags=["system"])
async def liveness_check():
    """Liveness probe endpoint for container orchestration.

    This endpoint indicates that the application process is alive.
    It should return quickly and not check external dependencies.
    Used by Kubernetes, Cloud Run, ECS, etc. to determine if the container should be restarted.
    """
    return {"status": "alive", "version": get_version()}


# Readiness probe endpoint
@app.get("/health/readiness", tags=["system"])
async def readiness_check():
    """Readiness probe endpoint for container orchestration.

    This endpoint checks if the application is ready to serve traffic.
    It verifies that critical dependencies (storage, auth service, domains) are initialized.
    Used by Kubernetes, Cloud Run, ECS, etc. to determine if traffic should be routed to this instance.
    """
    checks = {"storage": False, "auth_service": False, "domains": False}
    errors = []

    # Check storage service
    try:
        storage_service = await StorageService.get_instance()
        if storage_service:
            checks["storage"] = True
    except Exception as e:
        errors.append(f"Storage service not ready: {str(e)}")

    # Check authentication service
    try:
        auth_service = await AuthenticationService.get_instance()
        if auth_service:
            checks["auth_service"] = True
    except Exception as e:
        errors.append(f"Authentication service not ready: {str(e)}")

    # Check domain registration
    try:
        domains = list(DomainRegistry.get_registered_domains())
        if domains:
            checks["domains"] = True
    except Exception as e:
        errors.append(f"Domain registration failed: {str(e)}")

    # Determine overall readiness
    all_ready = all(checks.values())
    readiness_status = "ready" if all_ready else "not_ready"

    response = {
        "status": readiness_status,
        "checks": checks,
        "version": get_version(),
        "domains": (
            list(DomainRegistry.get_registered_domains()) if checks["domains"] else []
        ),
    }

    if errors:
        response["errors"] = errors

    # Return appropriate status code
    status_code = (
        status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return Response(
        content=json.dumps(response),
        status_code=status_code,
        media_type="application/json",
    )


# Create a versioned API
api_v1 = FastAPI(
    title="Open Hardware Manager API v1",
    description="Version 1 of the Open Hardware Manager API",
    version=get_version(),
)

# Include routers - those with prefixes don't need additional prefixes
api_v1.include_router(match_router, prefix="/api/match", tags=["match"])
api_v1.include_router(okh_router, prefix="/api/okh", tags=["okh"])
api_v1.include_router(okw_router, prefix="/api/okw", tags=["okw"])
api_v1.include_router(asset_router, prefix="/api/asset", tags=["asset"])
api_v1.include_router(
    supply_tree_router, tags=["supply-tree"]
)  # Already has /api/supply-tree prefix
api_v1.include_router(
    utility_router, tags=["utility"]
)  # Already has /api/utility prefix
api_v1.include_router(
    package_router, tags=["package"]
)  # Already has /api/package prefix
api_v1.include_router(llm_router, tags=["llm"])  # Already has /api/llm prefix
api_v1.include_router(
    rules_router, tags=["rules"]
)  # Already has /api/match/rules prefix
api_v1.include_router(
    convert_router, tags=["convert"]
)  # Already has /api/convert prefix
api_v1.include_router(
    taxonomy_router, tags=["taxonomy"]
)  # Already has /api/taxonomy prefix
api_v1.include_router(rfq_router, tags=["rfq"])  # Already has /api/rfq prefix
api_v1.include_router(
    federation_router, tags=["federation"]
)  # Already has /api/federation prefix

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
        version=get_version(),
        status=DomainStatus.ACTIVE,
        supported_input_types={"recipe", "kitchen"},
        supported_output_types={"cooking_workflow", "meal_plan"},
        documentation_url="https://docs.ohm.org/domains/cooking",
        maintainer="OHM Cooking Team",
    )

    DomainRegistry.register_domain(
        domain_name="cooking",
        extractor=CookingExtractor(),
        matcher=CookingMatcher(),
        validator=CookingValidatorCompat(),
        metadata=cooking_metadata,
    )

    # Register Manufacturing domain
    manufacturing_metadata = DomainMetadata(
        name="manufacturing",
        display_name="Manufacturing & Hardware Production",
        description="Domain for OKH/OKW manufacturing capability matching",
        version=get_version(),
        status=DomainStatus.ACTIVE,
        supported_input_types={"okh", "okw"},
        supported_output_types={"supply_tree", "manufacturing_plan"},
        documentation_url="https://docs.ohm.org/domains/manufacturing",
        maintainer="OHM Manufacturing Team",
    )

    DomainRegistry.register_domain(
        domain_name="manufacturing",
        extractor=OKHExtractor(),
        matcher=OKHMatcher(),
        validator=ManufacturingOKHValidatorCompat(),
        metadata=manufacturing_metadata,
    )


async def cleanup_resources():
    """Cleanup resources on shutdown"""
    try:
        logger.info("Cleaning up resources")
        if settings.OHM_FEDERATION_ENABLED:
            from .federation.service import FederationService

            try:
                fed = await FederationService.get_instance()
                fed.stop_mdns()
                await fed.stop_sync_loop()
            except Exception:
                pass
    except Exception as e:
        logger.error("Error during cleanup", exc_info=True)


# Only run the app if this file is executed directly
if __name__ == "__main__":
    from src.config.settings import API_HOST, API_PORT, DEBUG

    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=DEBUG)
