import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ..models.okh import OKHManifest, DocumentRef, DocumentationType, PartSpec, Software
from ..models.package import BuildOptions, PackageMetadata, FileInfo
from .file_resolver import FileResolver

logger = logging.getLogger(__name__)


class PackageBuilder:
    """Builds standardized OKH package directory structures"""

    def __init__(self, file_resolver: Optional[FileResolver] = None):
        self.file_resolver = file_resolver or FileResolver()

    async def build_package(
        self, manifest: OKHManifest, output_dir: Path, options: BuildOptions
    ) -> PackageMetadata:
        """
        Build a complete OKH package from a manifest

        Args:
            manifest: OKH manifest to build package from
            output_dir: Base directory for package output
            options: Build options controlling what to include

        Returns:
            PackageMetadata with build information
        """
        # Generate package path
        package_name = self._generate_package_name(manifest)
        package_path = output_dir / package_name / manifest.version

        logger.info(f"Building package: {package_name}/{manifest.version}")
        logger.info(f"Package path: {package_path}")

        # Create package directory structure
        await self._create_directory_structure(package_path)

        # Save the manifest
        manifest_path = package_path / "okh-manifest.json"
        await self._save_manifest(manifest, manifest_path)

        # Download and organize files with deduplication
        file_inventory = []
        downloaded_files = {}  # Track downloaded files by URL to avoid duplicates

        async with self.file_resolver:
            # Download document files
            if options.include_design_files:
                files = await self._download_document_files(
                    manifest.design_files,
                    package_path / "design-files",
                    "design-files",
                    manifest.repo,
                    downloaded_files,
                )
                file_inventory.extend(files)

            if options.include_manufacturing_files:
                files = await self._download_document_files(
                    manifest.manufacturing_files,
                    package_path / "manufacturing-files",
                    "manufacturing-files",
                    manifest.repo,
                    downloaded_files,
                )
                file_inventory.extend(files)

            if options.include_making_instructions:
                files = await self._download_document_files(
                    manifest.making_instructions,
                    package_path / "making-instructions",
                    "making-instructions",
                    manifest.repo,
                    downloaded_files,
                )
                file_inventory.extend(files)

            if options.include_operating_instructions:
                files = await self._download_document_files(
                    manifest.operating_instructions,
                    package_path / "operating-instructions",
                    "operating-instructions",
                    manifest.repo,
                    downloaded_files,
                )
                file_inventory.extend(files)

            # Download files by type
            files_by_type = self._categorize_documents_by_type(
                manifest.manufacturing_files
            )

            if (
                options.include_quality_instructions
                and "technical-specifications" in files_by_type
            ):
                files = await self._download_document_files(
                    files_by_type["technical-specifications"],
                    package_path / "technical-specifications",
                    "technical-specifications",
                    manifest.repo,
                    downloaded_files,
                )
                file_inventory.extend(files)

            if options.include_risk_assessment and "risk-assessment" in files_by_type:
                files = await self._download_document_files(
                    files_by_type["risk-assessment"],
                    package_path / "risk-assessment",
                    "risk-assessment",
                    manifest.repo,
                    downloaded_files,
                )
                file_inventory.extend(files)

            if options.include_schematics and "schematics" in files_by_type:
                files = await self._download_document_files(
                    files_by_type["schematics"],
                    package_path / "schematics",
                    "schematics",
                    manifest.repo,
                    downloaded_files,
                )
                file_inventory.extend(files)

            if options.include_tool_settings and "making-instructions" in files_by_type:
                files = await self._download_document_files(
                    files_by_type["making-instructions"],
                    package_path / "making-instructions",
                    "making-instructions",
                    manifest.repo,
                    downloaded_files,
                )
                file_inventory.extend(files)

            # Download BOM if present
            if manifest.bom:
                # Handle BOM as a dictionary with external_file reference
                if isinstance(manifest.bom, dict) and "external_file" in manifest.bom:
                    # BOM is a structured object with external file reference
                    bom_path = manifest.bom["external_file"]
                    bom_files = await self._download_single_file(
                        bom_path,
                        package_path / "manufacturing-files",
                        "bom",
                        "manufacturing-files",
                        manifest.repo,
                    )
                    file_inventory.extend(bom_files)
                elif isinstance(manifest.bom, str):
                    # BOM is a simple URL/path string
                    bom_files = await self._download_single_file(
                        manifest.bom,
                        package_path / "manufacturing-files",
                        "bom",
                        "manufacturing-files",
                        manifest.repo,
                    )
                    file_inventory.extend(bom_files)

            # Download archive if present
            if manifest.archive_download:
                archive_files = await self._download_single_file(
                    manifest.archive_download,
                    package_path / "software",
                    "archive",
                    "software",
                    manifest.repo,
                )
                file_inventory.extend(archive_files)

            # Download project image if present
            if manifest.image:
                image_files = await self._download_single_file(
                    manifest.image,
                    package_path / "metadata",
                    "project-image",
                    "metadata",
                    manifest.repo,
                )
                file_inventory.extend(image_files)

            # Download software
            if options.include_software and manifest.software:
                files = await self._download_software_files(
                    manifest.software, package_path, manifest.repo
                )
                file_inventory.extend(files)

            # Download parts
            if options.include_parts and manifest.parts:
                files = await self._download_parts_files(
                    manifest.parts, package_path, manifest.repo
                )
                file_inventory.extend(files)

        # Fix file paths to be relative to package directory
        fixed_file_inventory = []
        for file_info in file_inventory:
            # Convert absolute path to relative path from package directory
            if file_info.local_path.startswith(str(package_path)):
                relative_path = Path(file_info.local_path).relative_to(package_path)
                # Create new FileInfo with relative path (preserving subdirectory structure)
                fixed_file_info = FileInfo(
                    original_url=file_info.original_url,
                    local_path=str(relative_path),
                    content_type=file_info.content_type,
                    size_bytes=file_info.size_bytes,
                    checksum_sha256=file_info.checksum_sha256,
                    downloaded_at=file_info.downloaded_at,
                    file_type=file_info.file_type,
                    part_name=file_info.part_name,
                )
                fixed_file_inventory.append(fixed_file_info)
            else:
                # Keep original if path is already relative
                fixed_file_inventory.append(file_info)

        # Generate package metadata
        metadata = await self._generate_package_metadata(
            manifest, package_path, package_name, fixed_file_inventory, options
        )

        # Save metadata
        await self._save_package_metadata(metadata, package_path)

        logger.info(
            f"Package built successfully: {len(file_inventory)} files, {metadata.total_size_bytes} bytes"
        )
        return metadata

    def _generate_package_name(self, manifest: OKHManifest) -> str:
        """Generate package name from manifest"""
        # Extract organization
        if manifest.organization:
            if isinstance(manifest.organization, str):
                org_name = manifest.organization
            else:
                org_name = manifest.organization.name
        else:
            org_name = "community"

        # Sanitize names
        from ..models.package import sanitize_package_name

        org_sanitized = sanitize_package_name(org_name)
        project_sanitized = sanitize_package_name(manifest.title)

        return f"{org_sanitized}/{project_sanitized}"

    async def _create_directory_structure(self, package_path: Path):
        """Create the standard package directory structure"""
        directories = [
            "design-files",
            "manufacturing-files",
            "making-instructions",
            "operating-instructions",
            "technical-specifications",
            "risk-assessment",
            "software",
            "schematics",
            "parts",
            "metadata",
        ]

        for directory in directories:
            (package_path / directory).mkdir(parents=True, exist_ok=True)

        logger.debug(f"Created directory structure at {package_path}")

    async def _save_manifest(self, manifest: OKHManifest, manifest_path: Path):
        """Save the OKH manifest to the package"""
        import aiofiles

        manifest_data = manifest.to_dict()
        async with aiofiles.open(manifest_path, "w") as f:
            await f.write(json.dumps(manifest_data, indent=2))

        logger.debug(f"Saved manifest to {manifest_path}")

    async def _download_document_files(
        self,
        documents: List[DocumentRef],
        target_dir: Path,
        file_type: str,
        repo_url: str = None,
        downloaded_files: dict = None,
    ) -> List[FileInfo]:
        """Download a list of document files"""
        if not documents:
            return []

        # Convert repository file paths to GitHub raw URLs if needed
        processed_documents = []
        for doc in documents:
            if (
                not doc.path.startswith(("http://", "https://"))
                and repo_url
                and "github.com" in repo_url
            ):
                # This is a repository file path, construct GitHub raw URL
                if repo_url.endswith("/"):
                    repo_url = repo_url[:-1]

                # Extract user/repo from GitHub URL
                if "/github.com/" in repo_url:
                    repo_part = repo_url.split("/github.com/")[-1]
                    github_raw_url = f"https://raw.githubusercontent.com/{repo_part}/master/{doc.path}"
                else:
                    # Fallback: assume it's already a GitHub URL
                    github_raw_url = f"{repo_url}/raw/master/{doc.path}"

                # Create new DocumentRef with GitHub raw URL
                processed_doc = DocumentRef(
                    title=doc.title,
                    path=github_raw_url,
                    type=doc.type,
                    metadata=doc.metadata,
                )
                processed_documents.append(processed_doc)
            else:
                # Keep original document
                processed_documents.append(doc)

        # Filter out already downloaded files (deduplication)
        if downloaded_files is None:
            downloaded_files = {}

        unique_documents = []
        duplicate_documents = []

        for doc in processed_documents:
            if doc.path not in downloaded_files:
                unique_documents.append(doc)
            else:
                duplicate_documents.append(doc)
                logger.debug(f"Found duplicate file: {doc.path}")

        # Download unique files
        results = []
        if unique_documents:
            results = await self.file_resolver.download_multiple_files(
                unique_documents, target_dir, file_type
            )

        # Extract successful file info and track downloaded files
        file_infos = []
        for i, result in enumerate(results):
            if result.success and result.file_info:
                file_infos.append(result.file_info)
                # Track this file as downloaded
                downloaded_files[unique_documents[i].path] = result.file_info
            else:
                logger.warning(f"Failed to download file: {result.error_message}")

        # Handle duplicate files by creating symbolic links
        # Extract relative paths for duplicate documents to preserve structure
        duplicate_relative_paths = self.file_resolver._extract_relative_paths(
            duplicate_documents
        )

        for i, doc in enumerate(duplicate_documents):
            original_file_info = downloaded_files[doc.path]
            # Use preserved relative path structure for the duplicate
            relative_path = duplicate_relative_paths[i]

            # Create a new FileInfo for this duplicate with the correct target path
            duplicate_file_info = FileInfo(
                original_url=original_file_info.original_url,
                local_path=str(target_dir / relative_path),
                content_type=original_file_info.content_type,
                size_bytes=original_file_info.size_bytes,
                checksum_sha256=original_file_info.checksum_sha256,
                downloaded_at=original_file_info.downloaded_at,
                file_type=file_type,
                part_name=original_file_info.part_name,
            )
            file_infos.append(duplicate_file_info)

            # Create symbolic link to the original file
            original_path = Path(original_file_info.local_path)
            link_path = target_dir / relative_path

            try:
                if not link_path.exists():
                    link_path.symlink_to(original_path.absolute())
                    logger.debug(
                        f"Created symbolic link: {link_path} -> {original_path}"
                    )
            except Exception as e:
                logger.warning(f"Failed to create symbolic link for {doc.path}: {e}")

        return file_infos

    async def _download_single_file(
        self,
        url: str,
        target_dir: Path,
        filename: str,
        file_type: str,
        repo_url: str = None,
    ) -> List[FileInfo]:
        """Download a single file from URL or GitHub repository"""
        # Determine if this is a GitHub repository file path
        actual_url = url
        if (
            not url.startswith(("http://", "https://"))
            and repo_url
            and "github.com" in repo_url
        ):
            # This is a repository file path, construct GitHub raw URL
            # Convert https://github.com/user/repo to https://raw.githubusercontent.com/user/repo/master
            if repo_url.endswith("/"):
                repo_url = repo_url[:-1]

            # Extract user/repo from GitHub URL
            if "/github.com/" in repo_url:
                repo_part = repo_url.split("/github.com/")[-1]
                actual_url = (
                    f"https://raw.githubusercontent.com/{repo_part}/master/{url}"
                )
            else:
                # Fallback: assume it's already a GitHub URL
                actual_url = f"{repo_url}/raw/master/{url}"

        # Create a DocumentRef for the URL
        doc_ref = DocumentRef(
            title=filename,
            path=actual_url,
            type=DocumentationType.MANUFACTURING_FILES,  # Default type
        )

        # Determine target path, preserving directory structure
        if actual_url.startswith(("http://", "https://")):
            from urllib.parse import urlparse

            parsed_url = urlparse(actual_url)
            url_path = parsed_url.path

            # Extract relative path preserving directory structure
            path_parts = url_path.strip("/").split("/")
            if len(path_parts) >= 3:
                # Common pattern: user/repo/branch/filepath
                branch_names = {"master", "main", "develop", "dev", "trunk", "default"}
                if path_parts[2].lower() in branch_names or len(path_parts[2]) <= 20:
                    # Skip user/repo/branch, keep the rest
                    relative_path = "/".join(path_parts[3:])
                else:
                    relative_path = "/".join(path_parts[2:])
            else:
                relative_path = Path(url_path).name

            # If we couldn't extract a meaningful path, use filename
            if not relative_path or relative_path == Path(url_path).name:
                original_filename = Path(url_path).name
                if original_filename and "." in original_filename:
                    relative_path = original_filename
                else:
                    ext = self._guess_extension_from_url(actual_url)
                    relative_path = f"{filename}{ext}"

            target_path = target_dir / relative_path
        else:
            # For relative paths, preserve the full structure
            target_path = target_dir / url

        result = await self.file_resolver.resolve_and_download(
            doc_ref, target_path, file_type
        )

        if result.success and result.file_info:
            return [result.file_info]
        else:
            logger.warning(f"Failed to download {url}: {result.error_message}")
            return []

    async def _download_software_files(
        self, software_list: List[Software], package_path: Path, repo_url: str = None
    ) -> List[FileInfo]:
        """Download software files"""
        file_infos = []
        software_dir = package_path / "software"

        for software in software_list:
            # Download software release
            if software.release:
                release_files = await self._download_single_file(
                    software.release, software_dir, "release", "software", repo_url
                )
                file_infos.extend(release_files)

            # Download installation guide
            if software.installation_guide:
                install_dir = software_dir / "installation"
                install_dir.mkdir(exist_ok=True)
                install_files = await self._download_single_file(
                    software.installation_guide,
                    install_dir,
                    "installation-guide",
                    "software",
                    repo_url,
                )
                file_infos.extend(install_files)

        return file_infos

    async def _download_parts_files(
        self, parts: List[PartSpec], package_path: Path, repo_url: str = None
    ) -> List[FileInfo]:
        """Download part-specific files"""
        file_infos = []
        parts_dir = package_path / "parts"

        for part in parts:
            part_dir = parts_dir / self._sanitize_part_name(part.name)

            # Create part subdirectories
            for subdir in ["source", "export", "auxiliary", "images"]:
                (part_dir / subdir).mkdir(parents=True, exist_ok=True)

            # Download source files
            if part.source:
                source_list = (
                    part.source if isinstance(part.source, list) else [part.source]
                )
                source_docs = [
                    DocumentRef(
                        title=f"source_{i}",
                        path=path,
                        type=DocumentationType.DESIGN_FILES,
                    )
                    for i, path in enumerate(source_list)
                ]
                source_files = await self.file_resolver.download_multiple_files(
                    source_docs, part_dir / "source", "parts", part.name
                )
                for result in source_files:
                    if result.success and result.file_info:
                        file_infos.append(result.file_info)

            # Download export files
            if part.export:
                export_list = (
                    part.export if isinstance(part.export, list) else [part.export]
                )
                export_docs = [
                    DocumentRef(
                        title=f"export_{i}",
                        path=path,
                        type=DocumentationType.DESIGN_FILES,
                    )
                    for i, path in enumerate(export_list)
                ]
                export_files = await self.file_resolver.download_multiple_files(
                    export_docs, part_dir / "export", "parts", part.name
                )
                for result in export_files:
                    if result.success and result.file_info:
                        file_infos.append(result.file_info)

            # Download auxiliary files
            if part.auxiliary:
                aux_list = (
                    part.auxiliary
                    if isinstance(part.auxiliary, list)
                    else [part.auxiliary]
                )
                aux_docs = [
                    DocumentRef(
                        title=f"auxiliary_{i}",
                        path=path,
                        type=DocumentationType.MANUFACTURING_FILES,
                    )
                    for i, path in enumerate(aux_list)
                ]
                aux_files = await self.file_resolver.download_multiple_files(
                    aux_docs, part_dir / "auxiliary", "parts", part.name
                )
                for result in aux_files:
                    if result.success and result.file_info:
                        file_infos.append(result.file_info)

            # Download part image
            if part.image:
                image_files = await self._download_single_file(
                    part.image, part_dir / "images", "part-image", "parts", repo_url
                )
                for file_info in image_files:
                    file_info.part_name = part.name
                file_infos.extend(image_files)

        return file_infos

    def _categorize_documents_by_type(
        self, documents: List[DocumentRef]
    ) -> Dict[str, List[DocumentRef]]:
        """Categorize documents by their DocumentationType"""
        categorized = {}

        for doc in documents:
            doc_type = doc.type.value
            if doc_type not in categorized:
                categorized[doc_type] = []
            categorized[doc_type].append(doc)

        return categorized

    def _sanitize_part_name(self, part_name: str) -> str:
        """Sanitize part name for filesystem use"""
        from ..models.package import sanitize_package_name

        return sanitize_package_name(part_name)

    def _guess_extension_from_url(self, url: str) -> str:
        """Guess file extension from URL"""
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        path = Path(parsed_url.path)

        if path.suffix:
            return path.suffix

        # Common patterns
        if "github.com" in url and "/raw/" in url:
            return ".bin"  # GitHub raw files often don't have extensions

        return ".bin"  # Default fallback

    def _discover_files_to_download(
        self, manifest: OKHManifest, options: BuildOptions
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discover all files that need to be downloaded from the manifest

        Returns:
            Dictionary mapping file categories to lists of file information
        """
        files_to_download = {
            "manufacturing-files": [],
            "design-files": [],
            "making-instructions": [],
            "operating-instructions": [],
            "technical-specifications": [],
            "risk-assessment": [],
            "schematics": [],
            "software": [],
            "parts": [],
            "bom": [],
            "project-image": [],
        }

        # Manufacturing files
        if options.include_manufacturing_files and manifest.manufacturing_files:
            for doc in manifest.manufacturing_files:
                files_to_download["manufacturing-files"].append(
                    {
                        "document_ref": doc,
                        "target_category": "manufacturing-files",
                        "part_name": None,
                    }
                )

        # Design files
        if options.include_design_files and manifest.design_files:
            for doc in manifest.design_files:
                files_to_download["design-files"].append(
                    {
                        "document_ref": doc,
                        "target_category": "design-files",
                        "part_name": None,
                    }
                )

        # Making instructions
        if options.include_making_instructions and manifest.making_instructions:
            for doc in manifest.making_instructions:
                files_to_download["making-instructions"].append(
                    {
                        "document_ref": doc,
                        "target_category": "making-instructions",
                        "part_name": None,
                    }
                )

        # Operating instructions
        if options.include_operating_instructions and manifest.operating_instructions:
            for doc in manifest.operating_instructions:
                files_to_download["operating-instructions"].append(
                    {
                        "document_ref": doc,
                        "target_category": "operating-instructions",
                        "part_name": None,
                    }
                )

        # Categorize manufacturing files by type
        if options.include_manufacturing_files and manifest.manufacturing_files:
            files_by_type = self._categorize_documents_by_type(
                manifest.manufacturing_files
            )

            if (
                options.include_quality_instructions
                and "technical-specifications" in files_by_type
            ):
                for doc in files_by_type["technical-specifications"]:
                    files_to_download["technical-specifications"].append(
                        {
                            "document_ref": doc,
                            "target_category": "technical-specifications",
                            "part_name": None,
                        }
                    )

            if options.include_risk_assessment and "risk-assessment" in files_by_type:
                for doc in files_by_type["risk-assessment"]:
                    files_to_download["risk-assessment"].append(
                        {
                            "document_ref": doc,
                            "target_category": "risk-assessment",
                            "part_name": None,
                        }
                    )

            if options.include_schematics and "schematics" in files_by_type:
                for doc in files_by_type["schematics"]:
                    files_to_download["schematics"].append(
                        {
                            "document_ref": doc,
                            "target_category": "schematics",
                            "part_name": None,
                        }
                    )

            if options.include_tool_settings and "making-instructions" in files_by_type:
                for doc in files_by_type["making-instructions"]:
                    files_to_download["making-instructions"].append(
                        {
                            "document_ref": doc,
                            "target_category": "making-instructions",
                            "part_name": None,
                        }
                    )

        # BOM
        if manifest.bom:
            files_to_download["bom"].append(
                {
                    "url": manifest.bom,
                    "target_category": "manufacturing-files",
                    "filename": "bom",
                    "part_name": None,
                }
            )

        # Project image
        if manifest.image:
            files_to_download["project-image"].append(
                {
                    "url": manifest.image,
                    "target_category": "metadata",
                    "filename": "project-image",
                    "part_name": None,
                }
            )

        # Software
        if options.include_software and manifest.software:
            for software in manifest.software:
                if software.release:
                    files_to_download["software"].append(
                        {
                            "url": software.release,
                            "target_category": "software",
                            "filename": "release",
                            "part_name": None,
                        }
                    )

                if software.installation_guide:
                    files_to_download["software"].append(
                        {
                            "url": software.installation_guide,
                            "target_category": "software/installation",
                            "filename": "installation-guide",
                            "part_name": None,
                        }
                    )

        # Parts
        if options.include_parts and manifest.parts:
            for part in manifest.parts:
                part_name = self._sanitize_part_name(part.name)

                # Source files
                if part.source:
                    source_list = (
                        part.source if isinstance(part.source, list) else [part.source]
                    )
                    for i, source_url in enumerate(source_list):
                        files_to_download["parts"].append(
                            {
                                "url": source_url,
                                "target_category": f"parts/{part_name}/source",
                                "filename": f"source_{i}",
                                "part_name": part.name,
                            }
                        )

                # Export files
                if part.export:
                    export_list = (
                        part.export if isinstance(part.export, list) else [part.export]
                    )
                    for i, export_url in enumerate(export_list):
                        files_to_download["parts"].append(
                            {
                                "url": export_url,
                                "target_category": f"parts/{part_name}/export",
                                "filename": f"export_{i}",
                                "part_name": part.name,
                            }
                        )

                # Auxiliary files
                if part.auxiliary:
                    aux_list = (
                        part.auxiliary
                        if isinstance(part.auxiliary, list)
                        else [part.auxiliary]
                    )
                    for i, aux_url in enumerate(aux_list):
                        files_to_download["parts"].append(
                            {
                                "url": aux_url,
                                "target_category": f"parts/{part_name}/auxiliary",
                                "filename": f"auxiliary_{i}",
                                "part_name": part.name,
                            }
                        )

                # Part image
                if part.image:
                    files_to_download["parts"].append(
                        {
                            "url": part.image,
                            "target_category": f"parts/{part_name}/images",
                            "filename": "part-image",
                            "part_name": part.name,
                        }
                    )

        return files_to_download

    async def _generate_package_metadata(
        self,
        manifest: OKHManifest,
        package_path: Path,
        package_name: str,
        file_inventory: List[FileInfo],
        options: BuildOptions,
    ) -> PackageMetadata:
        """Generate package metadata"""
        # Calculate total size
        total_size = sum(f.size_bytes for f in file_inventory)

        # Get OME version from version module
        from ..version import get_version

        ome_version = get_version()

        return PackageMetadata(
            package_name=package_name,
            version=manifest.version,
            okh_manifest_id=manifest.id,
            build_timestamp=datetime.now(),
            ome_version=ome_version,
            total_files=len(file_inventory),
            total_size_bytes=total_size,
            file_inventory=file_inventory,
            build_options=options,
            package_path=str(package_path),
        )

    async def _save_package_metadata(
        self, metadata: PackageMetadata, package_path: Path
    ):
        """Save package metadata to files"""
        import aiofiles

        metadata_dir = package_path / "metadata"

        # Save build info
        build_info = {
            "package_name": metadata.package_name,
            "version": metadata.version,
            "okh_manifest_id": str(metadata.okh_manifest_id),
            "build_timestamp": metadata.build_timestamp.isoformat(),
            "ome_version": metadata.ome_version,
            "total_files": metadata.total_files,
            "total_size_bytes": metadata.total_size_bytes,
            "build_options": metadata.build_options.to_dict(),
        }

        build_info_path = metadata_dir / "build-info.json"
        async with aiofiles.open(build_info_path, "w") as f:
            await f.write(json.dumps(build_info, indent=2))

        # Save file manifest
        file_manifest = {
            "total_files": metadata.total_files,
            "total_size_bytes": metadata.total_size_bytes,
            "files": [f.to_dict() for f in metadata.file_inventory],
        }

        file_manifest_path = metadata_dir / "file-manifest.json"
        async with aiofiles.open(file_manifest_path, "w") as f:
            await f.write(json.dumps(file_manifest, indent=2))

        logger.debug(f"Saved package metadata to {metadata_dir}")
