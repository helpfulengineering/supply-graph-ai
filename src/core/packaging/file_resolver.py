import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from urllib.parse import urlparse, urljoin
import mimetypes
import hashlib

from ..models.package import ResolvedFile, FileInfo, DownloadOptions
from ..models.okh import DocumentRef, DocumentationType

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
                headers={'User-Agent': self.download_options.user_agent}
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
        part_name: Optional[str] = None
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
        if file_ref.path.startswith(('http://', 'https://')):
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
        part_name: Optional[str] = None
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
                            content_type = response.headers.get('content-type', '')
                            if not content_type:
                                content_type, _ = mimetypes.guess_type(url)
                                content_type = content_type or 'application/octet-stream'
                            
                            # Download file content
                            content = await response.read()
                            
                            # Write to target path
                            async with aiofiles.open(target_path, 'wb') as f:
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
                                part_name=part_name
                            )
                            
                            logger.info(f"Downloaded {url} to {target_path} ({len(content)} bytes)")
                            return ResolvedFile(success=True, file_info=file_info)
                        
                        elif response.status in [301, 302, 303, 307, 308]:
                            # Handle redirects
                            if self.download_options.follow_redirects:
                                url = response.headers.get('location')
                                if url:
                                    url = urljoin(url, response.headers.get('location', ''))
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
                wait_time = 2 ** retry_count
                logger.info(f"Retrying {url} in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        
        error_msg = f"Failed to download {url} after {self.download_options.max_retries} retries"
        logger.error(error_msg)
        return ResolvedFile(success=False, error_message=error_msg, retry_count=retry_count)
    
    async def _copy_local_file(
        self,
        file_ref: DocumentRef,
        target_path: Path,
        file_type: str,
        part_name: Optional[str] = None
    ) -> ResolvedFile:
        """Copy a local file to the target path"""
        source_path = Path(file_ref.path)
        
        if not source_path.exists():
            error_msg = f"Local file not found: {source_path}"
            logger.error(error_msg)
            return ResolvedFile(success=False, error_message=error_msg)
        
        try:
            # Copy file content
            async with aiofiles.open(source_path, 'rb') as src:
                content = await src.read()
            
            async with aiofiles.open(target_path, 'wb') as dst:
                await dst.write(content)
            
            # Get file info
            stat = source_path.stat()
            content_type, _ = mimetypes.guess_type(str(source_path))
            content_type = content_type or 'application/octet-stream'
            
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
                part_name=part_name
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
        part_name: Optional[str] = None
    ) -> List[ResolvedFile]:
        """
        Download multiple files concurrently
        
        Args:
            file_refs: List of DocumentRef objects to download
            base_target_dir: Base directory for downloaded files
            file_type: Type of files being downloaded
            part_name: Name of the part (for part-specific files)
            
        Returns:
            List of ResolvedFile objects
        """
        tasks = []
        
        for i, file_ref in enumerate(file_refs):
            # Generate target filename
            if file_ref.path.startswith(('http://', 'https://')):
                # Extract filename from URL
                parsed_url = urlparse(file_ref.path)
                filename = Path(parsed_url.path).name
                if not filename or '.' not in filename:
                    # Generate filename from title and extension
                    ext = self._guess_extension_from_content_type(file_ref.path)
                    filename = f"{self._sanitize_filename(file_ref.title)}{ext}"
            else:
                # Use original filename for local files
                filename = Path(file_ref.path).name
            
            target_path = base_target_dir / filename
            
            # Create task for downloading
            task = self.resolve_and_download(file_ref, target_path, file_type, part_name)
            tasks.append(task)
        
        # Execute all downloads concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed ResolvedFile objects
        resolved_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = f"Exception downloading {file_refs[i].path}: {result}"
                logger.error(error_msg)
                resolved_results.append(ResolvedFile(success=False, error_message=error_msg))
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
            'application/pdf': '.pdf',
            'text/markdown': '.md',
            'text/plain': '.txt',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'application/zip': '.zip',
            'application/x-tar': '.tar',
            'application/gzip': '.gz'
        }
        
        # This is a simplified approach - in practice, we'd need to make a HEAD request
        # to get the actual content type, but for now we'll use common patterns
        return '.bin'  # Default fallback
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        import re
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        return sanitized.strip('_')
