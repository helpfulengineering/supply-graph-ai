from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import FileResponse
import logging

from ...models.okh import OKHManifest
from ...models.package import BuildOptions, PackageMetadata
from ...services.package_service import PackageService
from ...services.okh_service import OKHService
from ...packaging.remote_storage import PackageRemoteStorage
from src.config import settings
from ...utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/package", tags=["package"])


async def get_package_service() -> PackageService:
    """Dependency to get package service instance"""
    return await PackageService.get_instance()


async def get_okh_service() -> OKHService:
    """Dependency to get OKH service instance"""
    return await OKHService.get_instance()


async def get_remote_storage() -> PackageRemoteStorage:
    """Dependency to get package remote storage instance"""
    from ...services.storage_service import StorageService
    storage_service = await StorageService.get_instance()
    await storage_service.configure(settings.STORAGE_CONFIG)
    return PackageRemoteStorage(storage_service)


@router.post("/build", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def build_package_from_manifest(
    manifest_data: Dict[str, Any],
    options: Optional[BuildOptions] = None,
    package_service: PackageService = Depends(get_package_service)
):
    """
    Build an OKH package from a manifest dictionary
    
    Args:
        manifest_data: OKH manifest data
        options: Build options (optional)
        
    Returns:
        Package metadata and build information
    """
    try:
        # Create manifest from data
        manifest = OKHManifest.from_dict(manifest_data)
        
        # Use default options if none provided
        if options is None:
            options = BuildOptions()
        
        # Build package
        metadata = await package_service.build_package_from_manifest(manifest, options)
        
        return {
            "status": "success",
            "message": "Package built successfully",
            "metadata": metadata.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid manifest: {str(e)}")
    except Exception as e:
        logger.error(f"Error building package: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to build package: {str(e)}")


@router.post("/build/{manifest_id}", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def build_package_from_storage(
    manifest_id: UUID,
    options: Optional[BuildOptions] = None,
    package_service: PackageService = Depends(get_package_service)
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
        metadata = await package_service.build_package_from_storage(manifest_id, options)
        
        return {
            "status": "success",
            "message": "Package built successfully",
            "metadata": metadata.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error building package from storage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to build package: {str(e)}")


@router.get("/list", response_model=Dict[str, Any])
async def list_packages(
    package_service: PackageService = Depends(get_package_service)
):
    """
    List all built packages
    
    Returns:
        List of package metadata
    """
    try:
        packages = await package_service.list_built_packages()
        
        return {
            "status": "success",
            "packages": [pkg.to_dict() for pkg in packages],
            "total": len(packages)
        }
        
    except Exception as e:
        logger.error(f"Error listing packages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list packages: {str(e)}")


@router.get("/{package_name}/{version}", response_model=Dict[str, Any])
async def get_package_metadata(
    package_name: str,
    version: str,
    package_service: PackageService = Depends(get_package_service)
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
        
        return {
            "status": "success",
            "metadata": metadata.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting package metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get package metadata: {str(e)}")


@router.get("/{package_name}/{version}/verify", response_model=Dict[str, Any])
async def verify_package(
    package_name: str,
    version: str,
    package_service: PackageService = Depends(get_package_service)
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
        
        return {
            "status": "success",
            "verification": results
        }
        
    except Exception as e:
        logger.error(f"Error verifying package: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify package: {str(e)}")


@router.delete("/{package_name}/{version}", response_model=Dict[str, Any])
async def delete_package(
    package_name: str,
    version: str,
    package_service: PackageService = Depends(get_package_service)
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
        
        return {
            "status": "success",
            "message": f"Package {package_name}/{version} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting package: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete package: {str(e)}")


@router.get("/{package_name}/{version}/download")
async def download_package(
    package_name: str,
    version: str,
    package_service: PackageService = Depends(get_package_service)
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
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as temp_file:
            with tarfile.open(temp_file.name, 'w:gz') as tar:
                tar.add(package_path, arcname=f"{package_name.replace('/', '-')}-{version}")
            
            return FileResponse(
                path=temp_file.name,
                filename=tarball_name,
                media_type='application/gzip'
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating package tarball: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create package tarball: {str(e)}")


@router.post("/push", response_model=Dict[str, Any])
async def push_package(
    request_data: Dict[str, str],
    remote_storage: PackageRemoteStorage = Depends(get_remote_storage)
):
    """
    Push a local package to remote storage
    
    Args:
        request_data: JSON data containing package_name and version
        
    Returns:
        Push result
    """
    try:
        package_name = request_data.get("package_name")
        version = request_data.get("version")
        
        if not package_name or not version:
            raise HTTPException(status_code=400, detail="package_name and version are required")
        
        # Get package metadata first
        package_service = await get_package_service()
        metadata = await package_service.get_package_metadata(package_name, version)
        
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Package {package_name}:{version} not found")
        
        # Push package
        from pathlib import Path
        local_package_path = Path(metadata.package_path)
        result = await remote_storage.push_package(metadata, local_package_path)
        
        return {
            "status": "success",
            "message": f"Package {package_name}:{version} pushed successfully",
            "remote_path": result.get("remote_path", "unknown")
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error pushing package: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to push package: {str(e)}")


@router.post("/pull", response_model=Dict[str, Any])
async def pull_package(
    request_data: Dict[str, Any],
    remote_storage: PackageRemoteStorage = Depends(get_remote_storage)
):
    """
    Pull a remote package to local storage
    
    Args:
        request_data: JSON data containing package_name, version, and optional output_dir
        
    Returns:
        Pull result
    """
    try:
        package_name = request_data.get("package_name")
        version = request_data.get("version")
        output_dir = request_data.get("output_dir")
        
        if not package_name or not version:
            raise HTTPException(status_code=400, detail="package_name and version are required")
        
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
        
        return {
            "status": "success",
            "message": f"Package {package_name}:{version} pulled successfully",
            "metadata": metadata.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error pulling package: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pull package: {str(e)}")


@router.get("/remote", response_model=Dict[str, Any])
async def list_remote_packages(
    remote_storage: PackageRemoteStorage = Depends(get_remote_storage)
):
    """
    List packages available in remote storage
    
    Returns:
        List of remote packages
    """
    try:
        # List remote packages
        packages = await remote_storage.list_remote_packages()
        
        return {
            "status": "success",
            "packages": packages,
            "total": len(packages)
        }
        
    except Exception as e:
        logger.error(f"Error listing remote packages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list remote packages: {str(e)}")
