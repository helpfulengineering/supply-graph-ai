import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp

from src.core.models.okh import DocumentRef, DocumentationType
from src.core.models.package import DownloadOptions, ResolvedFile
from src.core.packaging.file_resolver import FileResolver


class TestFileResolver:
    """Test FileResolver class"""
    
    @pytest.fixture
    def file_resolver(self):
        """Create a FileResolver instance for testing"""
        return FileResolver()
    
    @pytest.fixture
    def sample_document_ref(self):
        """Create a sample DocumentRef for testing"""
        return DocumentRef(
            title="Test Document",
            path="https://example.com/test.pdf",
            type=DocumentationType.MANUFACTURING_FILES,
            metadata={"version": "1.0"}
        )
    
    @pytest.fixture
    def local_document_ref(self, tmp_path):
        """Create a local DocumentRef for testing"""
        test_file = tmp_path / "local_test.txt"
        test_file.write_text("Local test content")
        
        return DocumentRef(
            title="Local Test Document",
            path=str(test_file),
            type=DocumentationType.DESIGN_FILES
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, file_resolver):
        """Test FileResolver initialization"""
        assert file_resolver.session is None
        assert file_resolver._semaphore is None
        
        # Test async context manager
        async with file_resolver:
            assert file_resolver.session is not None
            assert file_resolver._semaphore is not None
        
        # Session should be closed after context
        assert file_resolver.session is None
        assert file_resolver._semaphore is None
    
    @pytest.mark.asyncio
    async def test_download_from_url_success(self, file_resolver, sample_document_ref, tmp_path):
        """Test successful file download from URL"""
        target_path = tmp_path / "downloaded_file.pdf"
        
        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.read = AsyncMock(return_value=b"PDF content")
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with file_resolver:
                result = await file_resolver._download_from_url(
                    sample_document_ref, target_path, "manufacturing-files"
                )
        
        assert result.success is True
        assert result.file_info is not None
        assert result.file_info.original_url == "https://example.com/test.pdf"
        assert result.file_info.local_path == str(target_path)
        assert result.file_info.content_type == "application/pdf"
        assert result.file_info.size_bytes == len(b"PDF content")
        assert result.file_info.file_type == "manufacturing-files"
        assert target_path.exists()
        assert target_path.read_bytes() == b"PDF content"
    
    @pytest.mark.asyncio
    async def test_download_from_url_http_error(self, file_resolver, sample_document_ref, tmp_path):
        """Test file download with HTTP error"""
        target_path = tmp_path / "failed_download.pdf"
        
        # Mock HTTP error response
        mock_response = AsyncMock()
        mock_response.status = 404
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with file_resolver:
                result = await file_resolver._download_from_url(
                    sample_document_ref, target_path, "manufacturing-files"
                )
        
        assert result.success is False
        assert result.error_message is not None
        assert "Failed to download" in result.error_message
        assert result.retry_count > 0
        assert not target_path.exists()
    
    @pytest.mark.asyncio
    async def test_download_from_url_network_error(self, file_resolver, sample_document_ref, tmp_path):
        """Test file download with network error"""
        target_path = tmp_path / "network_error.pdf"
        
        # Mock network error
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = aiohttp.ClientError("Network error")
            
            async with file_resolver:
                result = await file_resolver._download_from_url(
                    sample_document_ref, target_path, "manufacturing-files"
                )
        
        assert result.success is False
        assert result.error_message is not None
        assert "Failed to download" in result.error_message
        assert result.retry_count > 0
        assert not target_path.exists()
    
    @pytest.mark.asyncio
    async def test_copy_local_file_success(self, file_resolver, local_document_ref, tmp_path):
        """Test successful local file copy"""
        target_path = tmp_path / "copied_file.txt"
        
        async with file_resolver:
            result = await file_resolver._copy_local_file(
                local_document_ref, target_path, "design-files"
            )
        
        assert result.success is True
        assert result.file_info is not None
        assert result.file_info.original_url == str(Path(local_document_ref.path))
        assert result.file_info.local_path == str(target_path)
        assert result.file_info.file_type == "design-files"
        assert target_path.exists()
        assert target_path.read_text() == "Local test content"
    
    @pytest.mark.asyncio
    async def test_copy_local_file_not_found(self, file_resolver, tmp_path):
        """Test local file copy when source doesn't exist"""
        non_existent_file = tmp_path / "non_existent.txt"
        target_path = tmp_path / "target.txt"
        
        doc_ref = DocumentRef(
            title="Non-existent Document",
            path=str(non_existent_file),
            type=DocumentationType.DESIGN_FILES
        )
        
        async with file_resolver:
            result = await file_resolver._copy_local_file(
                doc_ref, target_path, "design-files"
            )
        
        assert result.success is False
        assert result.error_message is not None
        assert "Local file not found" in result.error_message
        assert not target_path.exists()
    
    @pytest.mark.asyncio
    async def test_resolve_and_download_url(self, file_resolver, sample_document_ref, tmp_path):
        """Test resolve_and_download with URL"""
        target_path = tmp_path / "resolved_file.pdf"
        
        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.read = AsyncMock(return_value=b"PDF content")
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with file_resolver:
                result = await file_resolver.resolve_and_download(
                    sample_document_ref, target_path, "manufacturing-files"
                )
        
        assert result.success is True
        assert result.file_info is not None
        assert target_path.exists()
    
    @pytest.mark.asyncio
    async def test_resolve_and_download_local(self, file_resolver, local_document_ref, tmp_path):
        """Test resolve_and_download with local file"""
        target_path = tmp_path / "resolved_local.txt"
        
        async with file_resolver:
            result = await file_resolver.resolve_and_download(
                local_document_ref, target_path, "design-files"
            )
        
        assert result.success is True
        assert result.file_info is not None
        assert target_path.exists()
        assert target_path.read_text() == "Local test content"
    
    @pytest.mark.asyncio
    async def test_download_multiple_files(self, file_resolver, tmp_path):
        """Test downloading multiple files concurrently"""
        # Create multiple document refs
        doc_refs = []
        for i in range(3):
            doc_ref = DocumentRef(
                title=f"Document {i}",
                path=f"https://example.com/file{i}.pdf",
                type=DocumentationType.MANUFACTURING_FILES
            )
            doc_refs.append(doc_ref)
        
        target_dir = tmp_path / "downloads"
        target_dir.mkdir()
        
        # Mock successful HTTP responses
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.read = AsyncMock(return_value=b"PDF content")
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with file_resolver:
                results = await file_resolver.download_multiple_files(
                    doc_refs, target_dir, "manufacturing-files"
                )
        
        assert len(results) == 3
        for result in results:
            assert result.success is True
            assert result.file_info is not None
        
        # Check that files were created
        downloaded_files = list(target_dir.glob("*.pdf"))
        assert len(downloaded_files) == 3
    
    def test_sanitize_filename(self, file_resolver):
        """Test filename sanitization"""
        # Test basic sanitization
        assert file_resolver._sanitize_filename("Test File") == "Test_File"
        assert file_resolver._sanitize_filename("File@#$%") == "File"
        
        # Test multiple underscores
        assert file_resolver._sanitize_filename("Test___File") == "Test_File"
        
        # Test leading/trailing underscores
        assert file_resolver._sanitize_filename("_Test_File_") == "Test_File"
    
    def test_guess_extension_from_content_type(self, file_resolver):
        """Test extension guessing from content type"""
        # Test URL with extension
        assert file_resolver._guess_extension_from_url("https://example.com/file.pdf") == ".pdf"
        assert file_resolver._guess_extension_from_url("https://example.com/file.stl") == ".stl"
        
        # Test URL without extension
        assert file_resolver._guess_extension_from_url("https://example.com/file") == ".bin"
        
        # Test GitHub raw URL
        assert file_resolver._guess_extension_from_url("https://github.com/user/repo/raw/main/file") == ".bin"
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, file_resolver, sample_document_ref, tmp_path):
        """Test retry logic with exponential backoff"""
        target_path = tmp_path / "retry_test.pdf"
        
        # Mock responses: first two fail, third succeeds
        mock_responses = [
            AsyncMock(status=500),  # First attempt fails
            AsyncMock(status=503),  # Second attempt fails
            AsyncMock(status=200, headers={"content-type": "application/pdf"}, read=AsyncMock(return_value=b"Success"))  # Third succeeds
        ]
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.side_effect = mock_responses
            
            # Mock sleep to avoid actual delays in tests
            with patch('asyncio.sleep'):
                async with file_resolver:
                    result = await file_resolver._download_from_url(
                        sample_document_ref, target_path, "manufacturing-files"
                    )
        
        assert result.success is True
        assert result.file_info is not None
        assert target_path.exists()
    
    @pytest.mark.asyncio
    async def test_redirect_handling(self, file_resolver, sample_document_ref, tmp_path):
        """Test HTTP redirect handling"""
        target_path = tmp_path / "redirect_test.pdf"
        
        # Mock redirect response
        mock_redirect_response = AsyncMock()
        mock_redirect_response.status = 302
        mock_redirect_response.headers = {"location": "https://example.com/redirected.pdf"}
        
        # Mock final successful response
        mock_success_response = AsyncMock()
        mock_success_response.status = 200
        mock_success_response.headers = {"content-type": "application/pdf"}
        mock_success_response.read = AsyncMock(return_value=b"Redirected content")
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.side_effect = [mock_redirect_response, mock_success_response]
            
            async with file_resolver:
                result = await file_resolver._download_from_url(
                    sample_document_ref, target_path, "manufacturing-files"
                )
        
        assert result.success is True
        assert result.file_info is not None
        assert target_path.exists()
