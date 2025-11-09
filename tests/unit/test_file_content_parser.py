"""
Unit tests for FileContentParser utility.

Tests the file content parsing utility for different analysis depths.
Following TDD approach: write tests first, then implement.
"""

import pytest
from pathlib import Path
from src.core.generation.utils.file_content_parser import FileContentParser
from src.core.generation.models import AnalysisDepth, FileInfo


class TestFileContentParser:
    """Test the FileContentParser class."""
    
    def test_parser_initialization(self):
        """Test that FileContentParser can be initialized."""
        parser = FileContentParser()
        assert parser is not None
    
    def test_parse_text_file_shallow(self):
        """Test parsing text file at shallow depth (first 500 chars)."""
        parser = FileContentParser()
        content = "# Test Document\n\nThis is a test document with some content." * 20  # Long content
        file_info = FileInfo(
            path="test.md",
            content=content,
            size=len(content.encode('utf-8')),
            file_type="markdown"
        )
        
        result = parser.parse_content(file_info, AnalysisDepth.SHALLOW)
        
        assert result is not None
        assert len(result) <= 500  # Should be limited to 500 chars
        assert "# Test Document" in result  # Should include beginning
    
    def test_parse_text_file_medium(self):
        """Test parsing text file at medium depth (first 2000 chars)."""
        parser = FileContentParser()
        content = "# Test Document\n\nThis is a test document with some content." * 50  # Long content
        file_info = FileInfo(
            path="test.md",
            content=content,
            size=len(content.encode('utf-8')),
            file_type="markdown"
        )
        
        result = parser.parse_content(file_info, AnalysisDepth.MEDIUM)
        
        assert result is not None
        assert len(result) <= 2000  # Should be limited to 2000 chars
        assert "# Test Document" in result  # Should include beginning
    
    def test_parse_text_file_deep(self):
        """Test parsing text file at deep depth (full content)."""
        parser = FileContentParser()
        content = "# Test Document\n\nThis is a test document with some content." * 10
        file_info = FileInfo(
            path="test.md",
            content=content,
            size=len(content.encode('utf-8')),
            file_type="markdown"
        )
        
        result = parser.parse_content(file_info, AnalysisDepth.DEEP)
        
        assert result is not None
        assert result == content  # Should include full content
    
    def test_parse_empty_file(self):
        """Test parsing empty file."""
        parser = FileContentParser()
        file_info = FileInfo(
            path="empty.txt",
            content="",
            size=0,
            file_type="text"
        )
        
        result = parser.parse_content(file_info, AnalysisDepth.SHALLOW)
        
        # Empty file should return empty string or None
        assert result == "" or result is None
    
    def test_parse_none_content(self):
        """Test parsing file with None content."""
        parser = FileContentParser()
        file_info = FileInfo(
            path="test.txt",
            content=None,
            size=0,
            file_type="text"
        )
        
        result = parser.parse_content(file_info, AnalysisDepth.SHALLOW)
        
        assert result is None
    
    def test_parse_binary_file_returns_none(self):
        """Test that binary files return None (will be handled by extract_binary_text)."""
        parser = FileContentParser()
        file_info = FileInfo(
            path="test.pdf",
            content=None,  # Binary files don't have text content
            size=1024,
            file_type="pdf"
        )
        
        result = parser.parse_content(file_info, AnalysisDepth.SHALLOW)
        
        # Binary files should return None from parse_content
        assert result is None
    
    def test_extract_binary_text_pdf(self):
        """Test extracting text from PDF file."""
        parser = FileContentParser()
        file_info = FileInfo(
            path="test.pdf",
            content=None,
            size=1024,
            file_type="pdf"
        )
        
        # This will fail initially (PDF extraction not implemented yet)
        # But should return None gracefully
        result = parser.extract_binary_text(file_info)
        
        # For now, should return None (will implement PDF extraction later)
        assert result is None or isinstance(result, str)
    
    def test_extract_binary_text_docx(self):
        """Test extracting text from DOCX file."""
        parser = FileContentParser()
        file_info = FileInfo(
            path="test.docx",
            content=None,
            size=2048,
            file_type="docx"
        )
        
        # This will fail initially (DOCX extraction not implemented yet)
        # But should return None gracefully
        result = parser.extract_binary_text(file_info)
        
        # For now, should return None (will implement DOCX extraction later)
        assert result is None or isinstance(result, str)
    
    def test_extract_binary_text_unsupported(self):
        """Test extracting text from unsupported binary file."""
        parser = FileContentParser()
        file_info = FileInfo(
            path="test.bin",
            content=None,
            size=512,
            file_type="binary"
        )
        
        result = parser.extract_binary_text(file_info)
        
        # Unsupported binary should return None
        assert result is None
    
    def test_parse_content_respects_depth_limits(self):
        """Test that parse_content respects depth limits."""
        parser = FileContentParser()
        
        # Create content longer than 2000 chars
        long_content = "A" * 5000
        file_info = FileInfo(
            path="long.txt",
            content=long_content,
            size=len(long_content.encode('utf-8')),
            file_type="text"
        )
        
        # Shallow should limit to ~500 chars
        shallow_result = parser.parse_content(file_info, AnalysisDepth.SHALLOW)
        assert shallow_result is not None
        assert len(shallow_result) <= 500
        
        # Medium should limit to ~2000 chars
        medium_result = parser.parse_content(file_info, AnalysisDepth.MEDIUM)
        assert medium_result is not None
        assert len(medium_result) <= 2000
        
        # Deep should include full content
        deep_result = parser.parse_content(file_info, AnalysisDepth.DEEP)
        assert deep_result is not None
        assert len(deep_result) == 5000

