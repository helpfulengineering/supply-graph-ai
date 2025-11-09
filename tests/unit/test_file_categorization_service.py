"""
Unit tests for FileCategorizationService.

Tests the service for file categorization using LLM content analysis.
Following TDD approach: write tests first, then implement.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from src.core.generation.services.file_categorization_service import FileCategorizationService
from src.core.generation.models import (
    FileInfo,
    AnalysisDepth
)
from src.core.generation.utils.file_categorization import FileCategorizationResult
from src.core.models.okh import DocumentationType


class TestFileCategorizationService:
    """Test the FileCategorizationService class."""
    
    def test_service_initialization(self):
        """Test that FileCategorizationService can be initialized."""
        service = FileCategorizationService()
        assert service is not None
    
    def test_service_initialization_with_llm_service(self):
        """Test that FileCategorizationService can be initialized with LLM service."""
        mock_llm_service = Mock()
        service = FileCategorizationService(llm_service=mock_llm_service)
        assert service.llm_service == mock_llm_service
    
    def test_service_initialization_with_repository_mapping_service(self):
        """Test that FileCategorizationService can be initialized with repository mapping service."""
        mock_repo_service = Mock()
        service = FileCategorizationService(repository_mapping_service=mock_repo_service)
        assert service.repository_mapping_service == mock_repo_service
    
    def test_service_initialization_with_caching_disabled(self):
        """Test that FileCategorizationService can be initialized with caching disabled."""
        service = FileCategorizationService(enable_caching=False)
        assert service.enable_caching is False
    
    @pytest.mark.asyncio
    async def test_categorize_files_layer1_only(self):
        """Test categorizing files using only Layer 1 (heuristics)."""
        service = FileCategorizationService()
        
        files = [
            FileInfo(path="manual/assembly.md", size=100, content="# Assembly", file_type="markdown"),
            FileInfo(path="design/part.stl", size=200, content="", file_type="stl"),
        ]
        
        # Layer 1 suggestions (from FileCategorizationRules)
        layer1_suggestions = {
            "manual/assembly.md": FileCategorizationResult(
                documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
                confidence=0.8,
                excluded=False,
                reason="Directory-based categorization"
            ),
            "design/part.stl": FileCategorizationResult(
                documentation_type=DocumentationType.MANUFACTURING_FILES,
                confidence=0.9,
                excluded=False,
                reason="Extension-based categorization"
            )
        }
        
        results = await service.categorize_files(
            files=files,
            layer1_suggestions=layer1_suggestions,
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        assert len(results) == 2
        assert "manual/assembly.md" in results
        assert "design/part.stl" in results
        assert results["manual/assembly.md"].documentation_type == DocumentationType.MAKING_INSTRUCTIONS
        assert results["design/part.stl"].documentation_type == DocumentationType.MANUFACTURING_FILES
    
    @pytest.mark.asyncio
    async def test_categorize_files_with_llm_fallback(self):
        """Test that service falls back to Layer 1 when LLM unavailable."""
        # Service without LLM service
        service = FileCategorizationService()
        
        files = [
            FileInfo(path="docs/manual.md", size=100, content="# Manual", file_type="markdown"),
        ]
        
        layer1_suggestions = {
            "docs/manual.md": FileCategorizationResult(
                documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
                confidence=0.7,
                excluded=False,
                reason="Directory-based categorization"
            )
        }
        
        results = await service.categorize_files(
            files=files,
            layer1_suggestions=layer1_suggestions,
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        # Should use Layer 1 suggestions when LLM unavailable
        assert len(results) == 1
        assert results["docs/manual.md"].documentation_type == DocumentationType.MAKING_INSTRUCTIONS
    
    @pytest.mark.asyncio
    async def test_categorize_files_per_file_depth_override(self):
        """Test categorizing files with per-file depth overrides."""
        service = FileCategorizationService()
        
        files = [
            FileInfo(path="docs/manual.md", size=100, content="# Manual", file_type="markdown"),
            FileInfo(path="docs/specs.md", size=200, content="# Specs", file_type="markdown"),
        ]
        
        layer1_suggestions = {
            "docs/manual.md": FileCategorizationResult(
                documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
                confidence=0.6,
                excluded=False,
                reason="Directory-based categorization"
            ),
            "docs/specs.md": FileCategorizationResult(
                documentation_type=DocumentationType.TECHNICAL_SPECIFICATIONS,
                confidence=0.7,
                excluded=False,
                reason="Filename-based categorization"
            )
        }
        
        per_file_depths = {
            "docs/manual.md": AnalysisDepth.DEEP,  # Override to deep
            "docs/specs.md": AnalysisDepth.MEDIUM  # Override to medium
        }
        
        results = await service.categorize_files(
            files=files,
            layer1_suggestions=layer1_suggestions,
            analysis_depth=AnalysisDepth.SHALLOW,  # Global default
            per_file_depths=per_file_depths
        )
        
        assert len(results) == 2
        # Service should respect per-file depth overrides
        # (Implementation will use these when LLM is available)
    
    @pytest.mark.asyncio
    async def test_categorize_files_excluded_files(self):
        """Test that excluded files are handled correctly."""
        service = FileCategorizationService()
        
        files = [
            FileInfo(path=".github/workflow.yml", size=50, content="", file_type="yaml"),
            FileInfo(path="docs/manual.md", size=100, content="# Manual", file_type="markdown"),
        ]
        
        layer1_suggestions = {
            ".github/workflow.yml": FileCategorizationResult(
                documentation_type=DocumentationType.DESIGN_FILES,  # Not used for excluded
                confidence=0.0,
                excluded=True,  # Excluded
                reason="Workflow file exclusion"
            ),
            "docs/manual.md": FileCategorizationResult(
                documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
                confidence=0.8,
                excluded=False,
                reason="Directory-based categorization"
            )
        }
        
        results = await service.categorize_files(
            files=files,
            layer1_suggestions=layer1_suggestions,
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        # Excluded files should not be in results
        assert ".github/workflow.yml" not in results
        assert "docs/manual.md" in results
    
    @pytest.mark.asyncio
    async def test_categorize_files_empty_list(self):
        """Test categorizing empty file list."""
        service = FileCategorizationService()
        
        results = await service.categorize_files(
            files=[],
            layer1_suggestions={},
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_categorize_files_caching(self):
        """Test that caching works correctly."""
        service = FileCategorizationService(enable_caching=True)
        
        files = [
            FileInfo(path="docs/manual.md", size=100, content="# Manual", file_type="markdown"),
        ]
        
        layer1_suggestions = {
            "docs/manual.md": FileCategorizationResult(
                documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
                confidence=0.7,
                excluded=False,
                reason="Directory-based categorization"
            )
        }
        
        # First call
        results1 = await service.categorize_files(
            files=files,
            layer1_suggestions=layer1_suggestions,
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        # Second call with same files (should use cache if LLM was used)
        results2 = await service.categorize_files(
            files=files,
            layer1_suggestions=layer1_suggestions,
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        # Results should be consistent
        assert results1["docs/manual.md"].documentation_type == results2["docs/manual.md"].documentation_type

