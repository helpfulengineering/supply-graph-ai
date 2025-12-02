import asyncio
import hashlib
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiofiles
import aiohttp

from ..models.okh import DocumentationType, DocumentRef
from ..models.package import DownloadOptions, FileInfo, ResolvedFile

logger = logging.getLogger(__name__)


class FileResolver:
    """Handles downloading and organizing external files for OKH packages"""

    def __init__(self, download_options: Optional[DownloadOptions] = None):
        self.download_options = download_options or DownloadOptions()
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self, max_concurrent: int = 5):
        """Initialize the file resolver with HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.download_options.timeout_seconds)
            connector = aiohttp.TCPConnector(limit=max_concurrent)

            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={"User-Agent": self.download_options.user_agent},
            )
            self._semaphore = asyncio.Semaphore(max_concurrent)

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            self.session = None
        self._semaphore = None

    async def resolve_and_download(
        self,
        file_ref: DocumentRef,
        target_path: Path,
        file_type: str,
        part_name: Optional[str] = None,
    ) -> ResolvedFile:
        """
        Download a file from a DocumentRef to the target path

        Args:
            file_ref: DocumentRef containing the file URL and metadata
            target_path: Local path where the file should be saved
            file_type: Type of file (e.g., "design-files", "manufacturing-files")
            part_name: Name of the part (for part-specific files)

        Returns:
            ResolvedFile with success status and file info
        """
        if not self.session:
            await self.initialize()

        # Ensure target directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine if this is a URL or local path
        if file_ref.path.startswith(("http://", "https://")):
            return await self._download_from_url(
                file_ref, target_path, file_type, part_name
            )
        else:
            return await self._copy_local_file(
                file_ref, target_path, file_type, part_name
            )

    async def _download_from_url(
        self,
        file_ref: DocumentRef,
        target_path: Path,
        file_type: str,
        part_name: Optional[str] = None,
    ) -> ResolvedFile:
        """Download a file from a URL"""
        url = file_ref.path
        retry_count = 0

        while retry_count <= self.download_options.max_retries:
            try:
                async with self._semaphore:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            # Get content type from response or guess from URL
                            content_type = response.headers.get("content-type", "")
                            if not content_type:
                                content_type, _ = mimetypes.guess_type(url)
                                content_type = (
                                    content_type or "application/octet-stream"
                                )

                            # Download file content
                            content = await response.read()

                            # Write to target path
                            async with aiofiles.open(target_path, "wb") as f:
                                await f.write(content)

                            # Calculate checksum
                            checksum = hashlib.sha256(content).hexdigest()

                            # Create file info
                            file_info = FileInfo(
                                original_url=url,
                                local_path=str(target_path),
                                content_type=content_type,
                                size_bytes=len(content),
                                checksum_sha256=checksum,
                                downloaded_at=datetime.now(),
                                file_type=file_type,
                                part_name=part_name,
                            )

                            logger.info(
                                f"Downloaded {url} to {target_path} ({len(content)} bytes)"
                            )
                            return ResolvedFile(success=True, file_info=file_info)

                        elif response.status in [301, 302, 303, 307, 308]:
                            # Handle redirects
                            if self.download_options.follow_redirects:
                                url = response.headers.get("location")
                                if url:
                                    url = urljoin(
                                        url, response.headers.get("location", "")
                                    )
                                    continue

                        logger.warning(f"HTTP {response.status} for {url}")
                        retry_count += 1

            except asyncio.TimeoutError:
                logger.warning(f"Timeout downloading {url} (attempt {retry_count + 1})")
                retry_count += 1
            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
                retry_count += 1

            if retry_count <= self.download_options.max_retries:
                # Exponential backoff
                wait_time = 2**retry_count
                logger.info(f"Retrying {url} in {wait_time} seconds...")
                await asyncio.sleep(wait_time)

        error_msg = f"Failed to download {url} after {self.download_options.max_retries} retries"
        logger.error(error_msg)
        return ResolvedFile(
            success=False, error_message=error_msg, retry_count=retry_count
        )

    async def _copy_local_file(
        self,
        file_ref: DocumentRef,
        target_path: Path,
        file_type: str,
        part_name: Optional[str] = None,
    ) -> ResolvedFile:
        """Copy a local file to the target path"""
        source_path = Path(file_ref.path)

        if not source_path.exists():
            error_msg = f"Local file not found: {source_path}"
            logger.error(error_msg)
            return ResolvedFile(success=False, error_message=error_msg)

        try:
            # Copy file content
            async with aiofiles.open(source_path, "rb") as src:
                content = await src.read()

            async with aiofiles.open(target_path, "wb") as dst:
                await dst.write(content)

            # Get file info
            stat = source_path.stat()
            content_type, _ = mimetypes.guess_type(str(source_path))
            content_type = content_type or "application/octet-stream"

            # Calculate checksum
            checksum = hashlib.sha256(content).hexdigest()

            file_info = FileInfo(
                original_url=str(source_path),
                local_path=str(target_path),
                content_type=content_type,
                size_bytes=stat.st_size,
                checksum_sha256=checksum,
                downloaded_at=datetime.now(),
                file_type=file_type,
                part_name=part_name,
            )

            logger.info(f"Copied {source_path} to {target_path}")
            return ResolvedFile(success=True, file_info=file_info)

        except Exception as e:
            error_msg = f"Error copying {source_path}: {e}"
            logger.error(error_msg)
            return ResolvedFile(success=False, error_message=error_msg)

    async def download_multiple_files(
        self,
        file_refs: List[DocumentRef],
        base_target_dir: Path,
        file_type: str,
        part_name: Optional[str] = None,
    ) -> List[ResolvedFile]:
        """
        Download multiple files concurrently, preserving directory structure

        Args:
            file_refs: List of DocumentRef objects to download
            base_target_dir: Base directory for downloaded files
            file_type: Type of files being downloaded
            part_name: Name of the part (for part-specific files)

        Returns:
            List of ResolvedFile objects
        """
        tasks = []

        # Extract relative paths preserving directory structure
        relative_paths = self._extract_relative_paths(file_refs)

        for i, file_ref in enumerate(file_refs):
            # Use preserved relative path structure
            relative_path = relative_paths[i]
            target_path = base_target_dir / relative_path

            # Create task for downloading
            task = self.resolve_and_download(
                file_ref, target_path, file_type, part_name
            )
            tasks.append(task)

        # Execute all downloads concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed ResolvedFile objects
        resolved_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = f"Exception downloading {file_refs[i].path}: {result}"
                logger.error(error_msg)
                resolved_results.append(
                    ResolvedFile(success=False, error_message=error_msg)
                )
            else:
                resolved_results.append(result)

        return resolved_results

    def _guess_extension_from_content_type(self, url: str) -> str:
        """Guess file extension from URL or content type"""
        # Try to get extension from URL path
        parsed_url = urlparse(url)
        path = Path(parsed_url.path)
        if path.suffix:
            return path.suffix

        # Common file extensions for different content types
        content_type_map = {
            "application/pdf": ".pdf",
            "text/markdown": ".md",
            "text/plain": ".txt",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "application/zip": ".zip",
            "application/x-tar": ".tar",
            "application/gzip": ".gz",
        }

        # This is a simplified approach - in practice, we'd need to make a HEAD request
        # to get the actual content type, but for now we'll use common patterns
        return ".bin"  # Default fallback

    def _extract_relative_paths(self, file_refs: List[DocumentRef]) -> List[str]:
        """
        Extract relative paths from file references, preserving directory structure.

        This method preserves the original directory structure from the source paths
        while sanitizing for filesystem compatibility. For example:
        - "docs/images/camera_screws_1.jpg" -> "docs/images/camera_screws_1.jpg"
        - "design_files/optics_for_objective_2.SPD" -> "design_files/optics_for_objective_2.SPD"
        - URL: "https://raw.githubusercontent.com/user/repo/master/docs/images/file.jpg"
          -> "docs/images/file.jpg"

        Args:
            file_refs: List of DocumentRef objects

        Returns:
            List of relative paths preserving directory structure
        """
        relative_paths = []

        for file_ref in file_refs:
            if file_ref.path.startswith(("http://", "https://")):
                # Extract path from URL
                parsed_url = urlparse(file_ref.path)
                url_path = parsed_url.path

                # Remove leading slash and extract relative path
                # For GitHub raw URLs like: /user/repo/master/docs/images/file.jpg
                # We want to extract: docs/images/file.jpg
                path_parts = url_path.strip("/").split("/")

                # Skip common repository path prefixes (user, repo, branch)
                # Look for common patterns like: user/repo/branch/path/to/file
                # We want to keep everything after the branch name
                if len(path_parts) >= 3:
                    # Common pattern: user/repo/branch/filepath
                    # Try to detect if third part is a branch name (common: master, main, develop)
                    branch_names = {
                        "master",
                        "main",
                        "develop",
                        "dev",
                        "trunk",
                        "default",
                    }
                    if (
                        path_parts[2].lower() in branch_names
                        or len(path_parts[2]) <= 20
                    ):
                        # Skip user/repo/branch, keep the rest
                        relative_path = "/".join(path_parts[3:])
                    else:
                        # Not a branch pattern, keep everything after repo name
                        relative_path = "/".join(path_parts[2:])
                else:
                    # Fallback: use filename only
                    relative_path = Path(url_path).name

                # If we couldn't extract a meaningful path, use filename
                if not relative_path or relative_path == Path(url_path).name:
                    filename = Path(url_path).name
                    if not filename or "." not in filename:
                        # Generate filename from title and extension
                        ext = self._guess_extension_from_content_type(file_ref.path)
                        relative_path = (
                            f"{self._sanitize_filename(file_ref.title)}{ext}"
                        )
                    else:
                        relative_path = filename
            else:
                # For relative paths, preserve the full structure
                relative_path = file_ref.path

            # Sanitize the path (handle each component separately)
            sanitized_parts = []
            for part in relative_path.split("/"):
                sanitized_part = self._sanitize_filename(part)
                if sanitized_part:  # Skip empty parts
                    sanitized_parts.append(sanitized_part)

            # Reconstruct path
            if sanitized_parts:
                relative_path = "/".join(sanitized_parts)
            else:
                # Fallback to filename if sanitization removed everything
                relative_path = self._sanitize_filename(file_ref.title) or "file"

            relative_paths.append(relative_path)

        # Optionally strip common prefix if all paths share the same prefix
        # This helps avoid redundant nesting (e.g., if all files are in "docs/")
        relative_paths = self._strip_common_prefix(relative_paths)

        return relative_paths

    def _strip_common_prefix(self, paths: List[str]) -> List[str]:
        """
        Strip common directory prefix from all paths if they all share it.

        For example, if all paths are:
        - "docs/images/file1.jpg"
        - "docs/images/file2.jpg"
        - "docs/parts/file3.md"

        The common prefix "docs/" would be stripped, resulting in:
        - "images/file1.jpg"
        - "images/file2.jpg"
        - "parts/file3.md"

        Args:
            paths: List of relative paths

        Returns:
            List of paths with common prefix stripped
        """
        if not paths or len(paths) == 1:
            return paths

        # Find common prefix by comparing path components
        path_components = [path.split("/") for path in paths]

        # Find the minimum length (to avoid index errors)
        min_length = min(len(components) for components in path_components)
        if min_length <= 1:
            # All paths are just filenames, no prefix to strip
            return paths

        # Find how many leading components are common
        common_prefix_length = 0
        for i in range(min_length):
            # Get the i-th component from all paths
            components_at_i = [components[i] for components in path_components]
            # Check if all components at this level are the same
            if len(set(components_at_i)) == 1:
                common_prefix_length = i + 1
            else:
                break

        # Only strip if there's a meaningful common prefix (at least 1 level)
        # and not all paths would become just filenames
        if common_prefix_length > 0 and common_prefix_length < min_length:
            # Strip the common prefix
            stripped_paths = []
            for components in path_components:
                if len(components) > common_prefix_length:
                    stripped_path = "/".join(components[common_prefix_length:])
                    stripped_paths.append(stripped_path)
                else:
                    # This path would become empty, keep original
                    stripped_paths.append("/".join(components))
            return stripped_paths

        return paths

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        import re

        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
        # Remove multiple underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores and dots
        sanitized = sanitized.strip("_.")
        return sanitized
