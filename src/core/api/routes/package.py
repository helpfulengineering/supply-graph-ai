from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import Field

from src.config import settings

# Import existing models and services
from ...models.okh import OKHManifest
from ...models.package import BuildOptions, PackageMetadata
from ...packaging.remote_storage import PackageRemoteStorage
from ...services.okh_service import OKHService
from ...services.package_service import PackageService
from ...utils.logging import get_logger
from ..decorators import (
    api_endpoint,
    llm_endpoint,
    paginated_response,
    track_performance,
    validate_request,
)
from ..error_handlers import create_error_response, create_success_response

# Import new standardized components
from ..models.base import (
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
    ValidationResult,
)

# Import consolidated package models
from ..models.package.request import (
    PackageBuildRequest,
    PackagePullRequest,
    PackagePushRequest,
)
from ..models.package.response import (
    PackageListResponse,
    PackageMetadataResponse,
    PackagePullResponse,
    PackagePushResponse,
    PackageResponse,
    PackageVerificationResponse,
)

logger = get_logger(__name__)

# Create router with standardized patterns
router = APIRouter(
    prefix="/api/package",
    tags=["package"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    },
)


# Service dependencies
async def get_package_service() -> PackageService:
    """Get package service instance."""
    return await PackageService.get_instance()


async def get_okh_service() -> OKHService:
    """Get OKH service instance."""
    return await OKHService.get_instance()


async def get_remote_storage() -> PackageRemoteStorage:
    """Get package remote storage instance."""
    from ...services.storage_service import StorageService

    storage_service = await StorageService.get_instance()

    # Configure storage service if not already configured
    if not storage_service._configured:
        from ....config.storage_config import get_default_storage_config

        config = get_default_storage_config()
        await storage_service.configure(config)

    return PackageRemoteStorage(storage_service)


@router.post(
    "/build",
    response_model=PackageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Build Package from Manifest",
    description="""
    Build an OKH package from a manifest dictionary with enhanced capabilities.
    
    This endpoint provides:
    - Standardized request/response formats
    - LLM integration support
    - Enhanced error handling
    - Performance metrics
    - Validation
    
    **Features:**
    - Support for LLM-enhanced package building
    - Advanced build options
    - Real-time performance tracking
    - Detailed validation results
    """,
)
@api_endpoint(
    success_message="Package built successfully", include_metrics=True, track_llm=True
)
@validate_request(PackageBuildRequest)
@track_performance("package_build")
@llm_endpoint(
    default_provider="anthropic", default_model="claude-sonnet-4-5", track_costs=True
)
async def build_package_from_manifest(
    request: PackageBuildRequest,
    http_request: Request,
    package_service: PackageService = Depends(get_package_service),
):
    """
    Enhanced package building with standardized patterns.

    Args:
        request: Enhanced package build request with standardized fields
        http_request: HTTP request object for tracking
        package_service: Package service dependency

    Returns:
        Enhanced package response with data
    """
    request_id = getattr(http_request.state, "request_id", None)
    start_time = datetime.now()

    try:
        # Pre-validate and fix UUID issues in manifest data before parsing
        # This is a safeguard in case the API server hasn't been restarted with the latest fixes
        from ...validation.uuid_validator import UUIDValidator
        
        # Fix manifest ID if invalid
        if "id" in request.manifest_data:
            manifest_id = request.manifest_data["id"]
            if not UUIDValidator.is_valid_uuid(manifest_id):
                logger.warning(f"Fixing invalid manifest ID: {manifest_id}")
                request.manifest_data["id"] = UUIDValidator.fix_invalid_uuid(
                    manifest_id, fallback_to_random=True
                )
        
        # Fix part IDs if invalid
        if "parts" in request.manifest_data:
            for part in request.manifest_data["parts"]:
                if "id" in part:
                    part_id = part["id"]
                    if not UUIDValidator.is_valid_uuid(part_id):
                        logger.warning(f"Fixing invalid part ID: {part_id}")
                        part["id"] = UUIDValidator.fix_invalid_uuid(
                            part_id, fallback_to_random=True
                        )
        
        # Create manifest from data (this will also handle UUID conversion)
        manifest = OKHManifest.from_dict(request.manifest_data)

        # Use default options if none provided
        if request.options:
            options = BuildOptions(**request.options)
        else:
            options = BuildOptions()

        # Build package
        metadata = await package_service.build_package_from_manifest(manifest, options)

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Create enhanced response
        response_data = {
            "package": metadata.to_dict(),
            "processing_time": processing_time,
            "validation_results": await _validate_package_result(
                metadata.to_dict(), request_id
            ),
        }

        logger.info(
            f"Package built successfully",
            extra={
                "request_id": request_id,
                "package_name": (
                    metadata.name if hasattr(metadata, "name") else "unknown"
                ),
                "processing_time": processing_time,
                "llm_used": request.use_llm,
            },
        )

        return response_data

    except ValueError as e:
        # Handle validation errors using standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_400_BAD_REQUEST,
            request_id=request_id,
            suggestion="Please check the manifest data format and try again",
        )
        logger.error(
            f"Validation error building package: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        # Log unexpected errors using standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error building package: {str(e)}",
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
    "/build/{manifest_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
async def build_package_from_storage(
    manifest_id: UUID,
    options: Optional[BuildOptions] = None,
    package_service: PackageService = Depends(get_package_service),
):
    """
    Build an OKH package from a stored manifest

    Args:
        manifest_id: UUID of the stored manifest
        options: Build options (optional)

    Returns:
        Package metadata and build information
    """
    try:
        # Use default options if none provided
        if options is None:
            options = BuildOptions()

        # Build package
        metadata = await package_service.build_package_from_storage(
            manifest_id, options
        )

        return create_success_response(
            message="Package built successfully",
            data={"metadata": metadata.to_dict()},
            request_id=None,
        )

    except ValueError as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=None,
            suggestion="Please check the manifest ID and try again",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=None,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(f"Error building package from storage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/list",
    response_model=PaginatedResponse,
    summary="List Packages",
    description="""
    Get a paginated list of built packages with enhanced capabilities.
    
    **Features:**
    - Paginated results with sorting and filtering
    - Enhanced error handling
    - Performance metrics
    - Comprehensive validation
    """,
)
@paginated_response(default_page_size=20, max_page_size=100)
async def list_packages(
    pagination: PaginationParams = Depends(),
    package_service: PackageService = Depends(get_package_service),
    http_request: Request = None,
):
    """Enhanced package listing with pagination and metrics."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        packages = await package_service.list_built_packages()

        # Convert to list format
        package_list = [pkg.to_dict() for pkg in packages]

        # Apply pagination
        total_items = len(package_list)
        start_idx = (pagination.page - 1) * pagination.page_size
        end_idx = start_idx + pagination.page_size
        paginated_packages = package_list[start_idx:end_idx]

        # Create pagination info
        total_pages = (total_items + pagination.page_size - 1) // pagination.page_size

        # Create proper PaginatedResponse object
        from ..models.base import PaginationInfo

        pagination_info = PaginationInfo(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        )

        return PaginatedResponse(
            items=paginated_packages,
            pagination=pagination_info,
            message="Packages retrieved successfully",
            request_id=request_id,
        )

    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error listing packages: {str(e)}",
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


@router.get("/{package_name}/{version}", response_model=Dict[str, Any])
async def get_package_metadata(
    package_name: str,
    version: str,
    package_service: PackageService = Depends(get_package_service),
):
    """
    Get metadata for a specific package

    Args:
        package_name: Package name (e.g., "org/project")
        version: Package version

    Returns:
        Package metadata
    """
    try:
        metadata = await package_service.get_package_metadata(package_name, version)

        if not metadata:
            raise HTTPException(status_code=404, detail="Package not found")

        return create_success_response(
            message="Package metadata retrieved successfully",
            data={"metadata": metadata.to_dict()},
            request_id=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=None,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(f"Error getting package metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get("/{package_name}/{version}/verify", response_model=Dict[str, Any])
async def verify_package(
    package_name: str,
    version: str,
    package_service: PackageService = Depends(get_package_service),
):
    """
    Verify a package's integrity

    Args:
        package_name: Package name (e.g., "org/project")
        version: Package version

    Returns:
        Verification results
    """
    try:
        results = await package_service.verify_package(package_name, version)

        return create_success_response(
            message="Package verification completed successfully",
            data={"verification": results},
            request_id=None,
        )

    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=None,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(f"Error verifying package: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.delete("/{package_name}/{version}", response_model=Dict[str, Any])
async def delete_package(
    package_name: str,
    version: str,
    package_service: PackageService = Depends(get_package_service),
):
    """
    Delete a package

    Args:
        package_name: Package name (e.g., "org/project")
        version: Package version

    Returns:
        Deletion result
    """
    try:
        success = await package_service.delete_package(package_name, version)

        if not success:
            raise HTTPException(status_code=404, detail="Package not found")

        return create_success_response(
            message=f"Package {package_name}/{version} deleted successfully",
            data={},
            request_id=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=None,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(f"Error deleting package: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get("/{package_name}/{version}/download")
async def download_package(
    package_name: str,
    version: str,
    package_service: PackageService = Depends(get_package_service),
):
    """
    Download a package as a tarball

    Args:
        package_name: Package name (e.g., "org/project")
        version: Package version

    Returns:
        Tarball file download
    """
    try:
        metadata = await package_service.get_package_metadata(package_name, version)

        if not metadata:
            raise HTTPException(status_code=404, detail="Package not found")

        # Create tarball
        import tarfile
        import tempfile
        from pathlib import Path

        package_path = Path(metadata.package_path)
        tarball_name = f"{package_name.replace('/', '-')}-{version}.tar.gz"

        # Create temporary tarball
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as temp_file:
            with tarfile.open(temp_file.name, "w:gz") as tar:
                tar.add(
                    package_path, arcname=f"{package_name.replace('/', '-')}-{version}"
                )

            return FileResponse(
                path=temp_file.name,
                filename=tarball_name,
                media_type="application/gzip",
            )

    except HTTPException:
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=None,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(f"Error creating package tarball: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post("/push", response_model=PackagePushResponse)
async def push_package(
    request: PackagePushRequest,
    remote_storage: PackageRemoteStorage = Depends(get_remote_storage),
):
    """
    Push a local package to remote storage

    Args:
        request: Package push request containing package_name and version

    Returns:
        Push result
    """
    try:
        package_name = request.package_name
        version = request.version

        # Validate package name format - detect common mistake where version is included
        if "/" in version or package_name.count("/") > 1:
            # Check if version appears to be in package_name
            if version in package_name:
                suggested_package_name = package_name.rsplit("/", 1)[0]
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid package name format. It looks like you included the version in the package name.\n"
                        f"Received: package_name='{package_name}', version='{version}'\n"
                        f"Expected format: package_name='org/project' (e.g., 'fourthievesvinegar/solderless-microlab'), version='1.0.0'\n"
                        f"Suggested: Try 'ohm package push {suggested_package_name} {version}'"
                    ),
                )
        
        # Validate package name has exactly one slash (org/project format)
        if package_name.count("/") != 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid package name format. Package name must be in format 'org/project'.\n"
                    f"Received: '{package_name}'\n"
                    f"Expected: 'organization/project' (e.g., 'fourthievesvinegar/solderless-microlab')"
                ),
            )

        # Get package metadata first
        package_service = await get_package_service()
        metadata = await package_service.get_package_metadata(package_name, version)

        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Package {package_name}:{version} not found.\n"
                    f"Use 'ohm package list-packages' to see available packages and their versions."
                ),
            )

        # Push package
        from pathlib import Path

        local_package_path = Path(metadata.package_path)
        result = await remote_storage.push_package(metadata, local_package_path)

        return PackagePushResponse(
            success=True,
            message=f"Package {package_name}:{version} pushed successfully",
            remote_path=result.get("remote_path", "unknown"),
        )

    except ValueError as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=None,
            suggestion="Please check the package name and version and try again",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=None,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(f"Error pushing package: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post("/pull", response_model=PackagePullResponse)
async def pull_package(
    request: PackagePullRequest,
    remote_storage: PackageRemoteStorage = Depends(get_remote_storage),
):
    """
    Pull a remote package to local storage

    Args:
        request: Package pull request containing package_name, version, and optional output_dir

    Returns:
        Pull result
    """
    try:
        package_name = request.package_name
        version = request.version
        output_dir = request.output_dir

        # Determine output directory
        if output_dir:
            from pathlib import Path

            output_path = Path(output_dir)
        else:
            # Use default packages directory
            from pathlib import Path

            repo_root = Path(__file__).parent.parent.parent.parent.parent
            output_path = repo_root / "packages"

        # Pull package
        metadata = await remote_storage.pull_package(package_name, version, output_path)

        return PackagePullResponse(
            success=True,
            message=f"Package {package_name}:{version} pulled successfully",
            local_path=str(output_path),
            metadata=PackageMetadataResponse(
                name=metadata.name,
                version=metadata.version,
                package_path=metadata.package_path,
                created_at=getattr(metadata, "created_at", None),
                size=getattr(metadata, "size", None),
                checksum=getattr(metadata, "checksum", None),
                metadata=getattr(metadata, "metadata", {}),
            ),
        )

    except ValueError as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=None,
            suggestion="Please check the package name and version and try again",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=None,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(f"Error pulling package: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get("/remote", response_model=Dict[str, Any])
async def list_remote_packages(
    remote_storage: PackageRemoteStorage = Depends(get_remote_storage),
):
    """
    List packages available in remote storage

    Returns:
        List of remote packages
    """
    try:
        # List remote packages
        packages = await remote_storage.list_remote_packages()

        response = create_success_response(
            message="Remote packages listed successfully",
            data={"packages": packages, "total": len(packages)},
            request_id=None,
        )
        return response.model_dump(mode="json")

    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=None,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(f"Error listing remote packages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


# Helper functions
async def _validate_package_result(
    result: any, request_id: str
) -> List[ValidationResult]:
    """Validate package operation result."""
    try:
        validation_results = []

        # Basic validation
        is_valid = True
        errors = []
        warnings = []
        suggestions = []

        # Check if result exists
        if not result:
            is_valid = False
            errors.append("No result returned from operation")

        # Check required fields if result is a dict
        if isinstance(result, dict):
            if not result.get("name"):
                warnings.append("Missing package name in result")

            if not result.get("version"):
                warnings.append("Missing package version in result")

            if not result.get("package_path"):
                warnings.append("Missing package path in result")

        # Generate suggestions
        if not is_valid:
            suggestions.append("Review the input data and try again")

        validation_result = ValidationResult(
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
            f"Error validating package result: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        return []
