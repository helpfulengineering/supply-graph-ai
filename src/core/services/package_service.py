import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import aiofiles

from ..models.okh import OKHManifest
from ..models.package import BuildOptions, PackageMetadata, calculate_file_checksum
from ..packaging.builder import PackageBuilder
from ..packaging.file_resolver import FileResolver
from ..utils.logging import get_logger
from .okh_service import OKHService

logger = get_logger(__name__)


class PackageService:
    """Service for managing OKH package building operations"""

    _instance = None

    @classmethod
    async def get_instance(cls) -> "PackageService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.initialize()
        return cls._instance

    def __init__(self):
        """Initialize the package service"""
        self.package_builder: Optional[PackageBuilder] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the service with dependencies"""
        if self._initialized:
            return

        # Initialize file resolver and package builder
        file_resolver = FileResolver()
        self.package_builder = PackageBuilder(file_resolver)

        self._initialized = True
        logger.info("Package service initialized")

    async def cleanup(self) -> None:
        """Clean up resources"""
        if self.package_builder and self.package_builder.file_resolver:
            await self.package_builder.file_resolver.cleanup()
        self._initialized = False
        logger.info("Package service cleaned up")

    async def ensure_initialized(self) -> None:
        """Ensure service is initialized"""
        if not self._initialized:
            raise RuntimeError("Package service not initialized")

    async def build_package_from_manifest(
        self, manifest: OKHManifest, options: Optional[BuildOptions] = None
    ) -> PackageMetadata:
        """
        Build a package from an OKH manifest

        Args:
            manifest: OKH manifest to build package from
            options: Build options (defaults to include all files)

        Returns:
            PackageMetadata with build information
        """
        await self.ensure_initialized()

        # Use default options if none provided
        if options is None:
            options = BuildOptions()

        # Set default output directory if not specified
        if not options.output_dir:
            # Use packages/ directory in repo root
            repo_root = Path(__file__).parent.parent.parent.parent
            options.output_dir = str(repo_root / "packages")

        logger.info(
            f"Building package for manifest: {manifest.title} v{manifest.version}"
        )

        # Validate manifest
        try:
            manifest.validate()
        except Exception as e:
            raise ValueError(f"Invalid OKH manifest: {e}")

        # Build the package
        output_dir = Path(options.output_dir)
        metadata = await self.package_builder.build_package(
            manifest, output_dir, options
        )

        logger.info(
            f"Package built successfully: {metadata.package_name}/{metadata.version}"
        )
        return metadata

    async def build_package_from_dict(
        self, manifest_data: Dict[str, Any], options: Optional[BuildOptions] = None
    ) -> PackageMetadata:
        """
        Build a package from manifest dictionary data

        Args:
            manifest_data: Dictionary containing OKH manifest data
            options: Build options (defaults to include all files)

        Returns:
            PackageMetadata with build information
        """
        # Create manifest from dictionary
        manifest = OKHManifest.from_dict(manifest_data)
        return await self.build_package_from_manifest(manifest, options)

    async def build_package_from_storage(
        self, manifest_id: UUID, options: Optional[BuildOptions] = None
    ) -> PackageMetadata:
        """
        Build a package from a manifest stored in the system

        Args:
            manifest_id: UUID of the stored manifest
            options: Build options (defaults to include all files)

        Returns:
            PackageMetadata with build information
        """
        await self.ensure_initialized()
        # Get the manifest from storage
        okh_service = await OKHService.get_instance()
        manifest = await okh_service.get(manifest_id)

        if not manifest:
            raise ValueError(f"OKH manifest not found: {manifest_id}")

        return await self.build_package_from_manifest(manifest, options)

    async def get_package_metadata(
        self, package_name: str, version: str
    ) -> Optional[PackageMetadata]:
        """
        Get metadata for a built package

        Args:
            package_name: Package name (e.g., "org/project")
            version: Package version

        Returns:
            PackageMetadata if found, None otherwise
        """
        await self.ensure_initialized()

        # Determine package path
        if not self.package_builder:
            return None

        # Use default output directory
        repo_root = Path(__file__).parent.parent.parent.parent
        output_dir = repo_root / "packages"
        package_path = output_dir / package_name / version

        # Check if package exists
        if not package_path.exists():
            logger.debug(f"Package path does not exist: {package_path}")
            return None

        # Load metadata
        metadata_path = package_path / "metadata" / "build-info.json"
        if not metadata_path.exists():
            logger.debug(f"Metadata file does not exist: {metadata_path}")
            return None

        try:
            async with aiofiles.open(metadata_path, "r") as f:
                metadata_data = json.loads(await f.read())

            # Load file manifest
            file_manifest_path = package_path / "metadata" / "file-manifest.json"
            if file_manifest_path.exists():
                async with aiofiles.open(file_manifest_path, "r") as f:
                    file_manifest_data = json.loads(await f.read())

                # Combine metadata
                metadata_data.update(
                    {
                        "file_inventory": file_manifest_data.get("files", []),
                        "package_path": str(package_path),
                    }
                )

            return PackageMetadata.from_dict(metadata_data)

        except Exception as e:
            logger.error(f"Error loading package metadata: {e}")
            return None

    async def list_built_packages(self) -> List[PackageMetadata]:
        """
        List all built packages

        Returns:
            List of PackageMetadata for all built packages
        """
        await self.ensure_initialized()

        # Use default output directory
        repo_root = Path(__file__).parent.parent.parent.parent
        packages_dir = repo_root / "packages"

        if not packages_dir.exists():
            return []

        packages = []

        # Walk through package directory structure
        logger.debug(f"Scanning packages directory: {packages_dir}")
        for org_dir in packages_dir.iterdir():
            logger.debug(
                f"Found org directory: {org_dir.name} (is_dir: {org_dir.is_dir()})"
            )
            if not org_dir.is_dir():
                continue

            for project_dir in org_dir.iterdir():
                logger.debug(
                    f"Found project directory: {project_dir.name} (is_dir: {project_dir.is_dir()})"
                )
                if not project_dir.is_dir():
                    continue

                for version_dir in project_dir.iterdir():
                    logger.debug(
                        f"Found version directory: {version_dir.name} (is_dir: {version_dir.is_dir()})"
                    )
                    if not version_dir.is_dir():
                        continue

                    package_name = f"{org_dir.name}/{project_dir.name}"
                    version = version_dir.name

                    logger.debug(f"Found package directory: {package_name}/{version}")
                    metadata = await self.get_package_metadata(package_name, version)
                    if metadata:
                        logger.debug(
                            f"Successfully loaded metadata for {package_name}/{version}"
                        )
                        packages.append(metadata)
                    else:
                        logger.debug(
                            f"Failed to load metadata for {package_name}/{version}"
                        )

        return packages

    async def delete_package(self, package_name: str, version: str) -> bool:
        """
        Delete a built package

        Args:
            package_name: Package name (e.g., "org/project")
            version: Package version

        Returns:
            True if deleted successfully, False otherwise
        """
        await self.ensure_initialized()

        # Determine package path
        repo_root = Path(__file__).parent.parent.parent.parent
        output_dir = repo_root / "packages"
        package_path = output_dir / package_name / version

        if not package_path.exists():
            return False

        try:
            shutil.rmtree(package_path)
            logger.info(f"Deleted package: {package_name}/{version}")
            return True
        except Exception as e:
            logger.error(f"Error deleting package {package_name}/{version}: {e}")
            return False

    async def verify_package(self, package_name: str, version: str) -> Dict[str, Any]:
        """
        Verify a built package's integrity

        Args:
            package_name: Package name (e.g., "org/project")
            version: Package version

        Returns:
            Dictionary with verification results
        """
        await self.ensure_initialized()

        metadata = await self.get_package_metadata(package_name, version)
        if not metadata:
            return {"valid": False, "error": "Package not found"}

        package_path = Path(metadata.package_path)
        verification_results = {
            "valid": True,
            "package_name": package_name,
            "version": version,
            "total_files": metadata.total_files,
            "total_size_bytes": metadata.total_size_bytes,
            "missing_files": [],
            "corrupted_files": [],
            "extra_files": [],
        }

        # Check if all expected files exist
        # The local_path in metadata is relative to repo root, we need to convert to absolute paths
        expected_files = set()
        for f in metadata.file_inventory:
            # f.local_path is like: packages/org/project/version/file
            # We need to resolve it relative to the repo root
            repo_root = Path(__file__).parent.parent.parent.parent
            expected_path = repo_root / f.local_path
            expected_files.add(str(expected_path))

        actual_files = set()
        for file_path in package_path.rglob("*"):
            if file_path.is_file():
                actual_files.add(str(file_path))

        # Find missing files
        for expected_file in expected_files:
            if expected_file not in actual_files:
                # Convert back to relative path for reporting
                rel_path = Path(expected_file).relative_to(repo_root)
                verification_results["missing_files"].append(str(rel_path))
                verification_results["valid"] = False

        # Find extra files (not in manifest)
        for actual_file in actual_files:
            if actual_file not in expected_files:
                # Convert to relative path for reporting
                rel_path = Path(actual_file).relative_to(repo_root)
                verification_results["extra_files"].append(str(rel_path))

        # Verify file checksums (if requested)
        for file_info in metadata.file_inventory:
            file_path = Path(file_info.local_path)
            if file_path.exists():
                try:
                    actual_checksum = calculate_file_checksum(file_path)
                    if actual_checksum != file_info.checksum_sha256:
                        verification_results["corrupted_files"].append(
                            file_info.local_path
                        )
                        verification_results["valid"] = False
                except Exception as e:
                    logger.warning(f"Could not verify checksum for {file_path}: {e}")
            else:
                verification_results["missing_files"].append(file_info.local_path)
                verification_results["valid"] = False

        return verification_results
