"""
Remote storage handlers for OKH package PUSH/PULL operations
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from ..services.storage_service import StorageService
from ..models.package import PackageMetadata, FileInfo
from ..models.okh import OKHManifest

logger = logging.getLogger(__name__)

class PackageRemoteStorage:
    """Handles remote storage operations for OKH packages"""
    
    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
    
    def _get_package_base_key(self, org: str, project: str, version: str) -> str:
        """Get the base key for a package in remote storage"""
        return f"okh/packages/{org}/{project}/{version}"
    
    def _get_manifest_key(self, org: str, project: str, version: str) -> str:
        """Get the key for package manifest in remote storage"""
        return f"{self._get_package_base_key(org, project, version)}/manifest.json"
    
    def _get_build_info_key(self, org: str, project: str, version: str) -> str:
        """Get the key for build info in remote storage"""
        return f"{self._get_package_base_key(org, project, version)}/build-info.json"
    
    def _get_file_manifest_key(self, org: str, project: str, version: str) -> str:
        """Get the key for file manifest in remote storage"""
        return f"{self._get_package_base_key(org, project, version)}/file-manifest.json"
    
    def _get_file_key(self, org: str, project: str, version: str, file_path: str) -> str:
        """Get the key for a specific file in remote storage"""
        # Convert local file path to remote storage path
        # Remove the local package path prefix and use relative path
        if file_path.startswith(f"packages/{org}/{project}/{version}/"):
            relative_path = file_path[len(f"packages/{org}/{project}/{version}/"):]
        else:
            relative_path = file_path
        
        return f"{self._get_package_base_key(org, project, version)}/files/{relative_path}"
    
    async def push_package(
        self, 
        package_metadata: PackageMetadata, 
        local_package_path: Path
    ) -> Dict[str, Any]:
        """
        Push a local package to remote storage
        
        Args:
            package_metadata: Package metadata from local build
            local_package_path: Path to local package directory
            
        Returns:
            Dictionary with push results
        """
        logger.info(f"Pushing package {package_metadata.package_name}:{package_metadata.version}")
        
        # Parse package name
        org, project = package_metadata.package_name.split('/')
        version = package_metadata.version
        
        push_results = {
            "package_name": package_metadata.package_name,
            "version": version,
            "uploaded_files": [],
            "failed_files": [],
            "total_files": len(package_metadata.file_inventory),
            "total_size": package_metadata.total_size_bytes
        }
        
        try:
            # 1. Upload package manifest
            manifest_path = local_package_path / "okh-manifest.json"
            if manifest_path.exists():
                manifest_key = self._get_manifest_key(org, project, version)
                with open(manifest_path, 'rb') as f:
                    manifest_data = f.read()
                
                await self.storage_service.manager.put_object(
                    key=manifest_key,
                    data=manifest_data,
                    content_type="application/json",
                    metadata={
                        "package_name": package_metadata.package_name,
                        "version": version,
                        "type": "package_manifest"
                    }
                )
                push_results["uploaded_files"].append("manifest.json")
                logger.info(f"Uploaded manifest: {manifest_key}")
            
            # 2. Upload build info
            build_info_path = local_package_path / "metadata" / "build-info.json"
            if build_info_path.exists():
                build_info_key = self._get_build_info_key(org, project, version)
                with open(build_info_path, 'rb') as f:
                    build_info_data = f.read()
                
                await self.storage_service.manager.put_object(
                    key=build_info_key,
                    data=build_info_data,
                    content_type="application/json",
                    metadata={
                        "package_name": package_metadata.package_name,
                        "version": version,
                        "type": "build_info"
                    }
                )
                push_results["uploaded_files"].append("build-info.json")
                logger.info(f"Uploaded build info: {build_info_key}")
            
            # 3. Upload file manifest
            file_manifest_path = local_package_path / "metadata" / "file-manifest.json"
            if file_manifest_path.exists():
                file_manifest_key = self._get_file_manifest_key(org, project, version)
                with open(file_manifest_path, 'rb') as f:
                    file_manifest_data = f.read()
                
                await self.storage_service.manager.put_object(
                    key=file_manifest_key,
                    data=file_manifest_data,
                    content_type="application/json",
                    metadata={
                        "package_name": package_metadata.package_name,
                        "version": version,
                        "type": "file_manifest"
                    }
                )
                push_results["uploaded_files"].append("file-manifest.json")
                logger.info(f"Uploaded file manifest: {file_manifest_key}")
            
            # 4. Upload all package files
            for file_info in package_metadata.file_inventory:
                try:
                    local_file_path = Path(file_info.local_path)
                    if not local_file_path.exists():
                        logger.warning(f"Local file not found: {local_file_path}")
                        push_results["failed_files"].append({
                            "file": file_info.local_path,
                            "error": "Local file not found"
                        })
                        continue
                    
                    # Get remote storage key for this file
                    remote_file_key = self._get_file_key(org, project, version, file_info.local_path)
                    
                    # Upload file
                    with open(local_file_path, 'rb') as f:
                        file_data = f.read()
                    
                    await self.storage_service.manager.put_object(
                        key=remote_file_key,
                        data=file_data,
                        content_type=file_info.content_type or "application/octet-stream",
                        metadata={
                            "package_name": package_metadata.package_name,
                            "version": version,
                            "original_url": file_info.original_url,
                            "file_type": file_info.file_type,
                            "part_name": file_info.part_name or "",
                            "checksum_sha256": file_info.checksum_sha256,
                            "size_bytes": str(file_info.size_bytes)
                        }
                    )
                    
                    push_results["uploaded_files"].append(file_info.local_path)
                    logger.info(f"Uploaded file: {remote_file_key}")
                    
                except Exception as e:
                    logger.error(f"Failed to upload file {file_info.local_path}: {e}")
                    push_results["failed_files"].append({
                        "file": file_info.local_path,
                        "error": str(e)
                    })
            
            # 5. Create package index entry
            await self._create_package_index_entry(org, project, version, package_metadata)
            
            logger.info(f"Successfully pushed package {package_metadata.package_name}:{version}")
            logger.info(f"Uploaded {len(push_results['uploaded_files'])} files, {len(push_results['failed_files'])} failed")
            
        except Exception as e:
            logger.error(f"Failed to push package {package_metadata.package_name}:{version}: {e}")
            raise
        
        return push_results
    
    async def pull_package(
        self, 
        package_name: str, 
        version: str, 
        local_output_dir: Path
    ) -> PackageMetadata:
        """
        Pull a remote package to local storage
        
        Args:
            package_name: Package name (e.g., "org/project")
            version: Package version
            local_output_dir: Local directory to download to
            
        Returns:
            PackageMetadata for the downloaded package
        """
        logger.info(f"Pulling package {package_name}:{version}")
        
        # Parse package name
        org, project = package_name.split('/')
        
        try:
            # 1. Download and parse build info to get package metadata
            build_info_key = self._get_build_info_key(org, project, version)
            build_info_data = await self.storage_service.manager.get_object(build_info_key)
            build_info = json.loads(build_info_data.decode('utf-8'))
            
            # 2. Download and parse file manifest
            file_manifest_key = self._get_file_manifest_key(org, project, version)
            file_manifest_data = await self.storage_service.manager.get_object(file_manifest_key)
            file_manifest = json.loads(file_manifest_data.decode('utf-8'))
            
            # 3. Create local package directory
            local_package_path = local_output_dir / org / project / version
            local_package_path.mkdir(parents=True, exist_ok=True)
            
            # 4. Create package metadata
            # Add package_path to build_info for PackageMetadata creation
            build_info["package_path"] = str(local_package_path)
            package_metadata = PackageMetadata.from_dict({
                **build_info,
                "file_inventory": file_manifest["files"]
            })
            
            # 5. Download manifest
            manifest_key = self._get_manifest_key(org, project, version)
            manifest_data = await self.storage_service.manager.get_object(manifest_key)
            with open(local_package_path / "okh-manifest.json", 'wb') as f:
                f.write(manifest_data)
            
            # 6. Create metadata directory
            metadata_dir = local_package_path / "metadata"
            metadata_dir.mkdir(exist_ok=True)
            
            # Save build info and file manifest locally
            with open(metadata_dir / "build-info.json", 'wb') as f:
                f.write(build_info_data)
            with open(metadata_dir / "file-manifest.json", 'wb') as f:
                f.write(file_manifest_data)
            
            # 7. Download all package files
            for file_info in package_metadata.file_inventory:
                try:
                    # Get remote storage key
                    remote_file_key = self._get_file_key(org, project, version, file_info.local_path)
                    
                    # Download file
                    file_data = await self.storage_service.manager.get_object(remote_file_key)
                    
                    # Create local file path
                    local_file_path = local_package_path / file_info.local_path
                    local_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write file
                    with open(local_file_path, 'wb') as f:
                        f.write(file_data)
                    
                    logger.info(f"Downloaded file: {file_info.local_path}")
                    
                except Exception as e:
                    logger.error(f"Failed to download file {file_info.local_path}: {e}")
                    raise
            
            logger.info(f"Successfully pulled package {package_name}:{version}")
            return package_metadata
            
        except Exception as e:
            logger.error(f"Failed to pull package {package_name}:{version}: {e}")
            raise
    
    async def list_remote_packages(self) -> List[Dict[str, Any]]:
        """
        List all packages available in remote storage
        
        Returns:
            List of package information dictionaries
        """
        logger.info("Listing remote packages")
        
        packages = []
        
        try:
            # List all objects with okh/packages/ prefix
            async for obj in self.storage_service.manager.list_objects(prefix="okh/packages/"):
                key = obj["key"]
                
                # Look for build-info.json files to identify packages
                if key.endswith("/build-info.json"):
                    # Extract package info from key: okh/packages/org/project/version/build-info.json
                    parts = key.split('/')
                    if len(parts) >= 5:
                        org = parts[2]
                        project = parts[3]
                        version = parts[4]
                        package_name = f"{org}/{project}"
                        
                        packages.append({
                            "package_name": package_name,
                            "version": version,
                            "org": org,
                            "project": project,
                            "last_modified": obj.get("last_modified"),
                            "size": obj.get("size", 0)
                        })
            
            logger.info(f"Found {len(packages)} remote packages")
            return packages
            
        except Exception as e:
            logger.error(f"Failed to list remote packages: {e}")
            raise
    
    async def _create_package_index_entry(
        self, 
        org: str, 
        project: str, 
        version: str, 
        package_metadata: PackageMetadata
    ) -> None:
        """Create an entry in the package index for easy discovery"""
        index_key = f"okh/packages/{org}/{project}/index.json"
        
        try:
            # Try to get existing index
            try:
                index_data = await self.storage_service.manager.get_object(index_key)
                index = json.loads(index_data.decode('utf-8'))
            except:
                # Create new index if it doesn't exist
                index = {
                    "package_name": f"{org}/{project}",
                    "versions": {}
                }
            
            # Add version to index
            index["versions"][version] = {
                "version": version,
                "build_timestamp": package_metadata.build_timestamp.isoformat(),
                "total_files": package_metadata.total_files,
                "total_size_bytes": package_metadata.total_size_bytes,
                "ome_version": package_metadata.ome_version
            }
            
            # Save updated index
            index_json = json.dumps(index, indent=2)
            await self.storage_service.manager.put_object(
                key=index_key,
                data=index_json.encode('utf-8'),
                content_type="application/json",
                metadata={
                    "package_name": f"{org}/{project}",
                    "type": "package_index"
                }
            )
            
            logger.info(f"Updated package index: {index_key}")
            
        except Exception as e:
            logger.warning(f"Failed to create package index entry: {e}")
            # Don't fail the entire push operation for index issues
