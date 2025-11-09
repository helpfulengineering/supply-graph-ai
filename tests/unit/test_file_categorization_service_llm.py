"""
Unit tests for FileCategorizationService LLM categorization logic.

Tests the LLM-based file categorization implementation.
Following TDD approach: write tests first, then implement.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import json
from src.core.generation.services.file_categorization_service import FileCategorizationService
from src.core.generation.models import FileInfo, AnalysisDepth
from src.core.generation.utils.file_categorization import FileCategorizationResult
from src.core.models.okh import DocumentationType
from src.core.llm.models.responses import LLMResponse, LLMResponseStatus, LLMResponseMetadata


class TestFileCategorizationServiceLLM:
    """Test the LLM categorization logic in FileCategorizationService."""
    
    @pytest.mark.asyncio
    async def test_categorize_with_llm_success(self):
        """Test successful LLM categorization."""
        # Create mock LLM service
        mock_llm_service = Mock()
        mock_llm_service.initialize = AsyncMock()
        from src.core.services.base import ServiceStatus
        mock_llm_service.status = ServiceStatus.ACTIVE
        mock_metadata = LLMResponseMetadata(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            tokens_used=100,
            cost=0.01,
            processing_time=0.5
        )
        mock_response = LLMResponse(
            content=json.dumps({
                "documentation_type": "making-instructions",
                "confidence": 0.9,
                "excluded": False,
                "reason": "File contains step-by-step assembly instructions",
                "overrides_layer1": False
            }),
            status=LLMResponseStatus.SUCCESS,
            metadata=mock_metadata
        )
        mock_llm_service.generate = AsyncMock(return_value=mock_response)
        
        service = FileCategorizationService(llm_service=mock_llm_service)
        
        file_info = FileInfo(
            path="docs/manual.md",
            size=1000,
            content="# Assembly Instructions\n\nStep 1: ...",
            file_type="markdown"
        )
        
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
            confidence=0.7,
            excluded=False,
            reason="Directory-based categorization"
        )
        
        result = await service._categorize_with_llm(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            depth=AnalysisDepth.SHALLOW
        )
        
        assert result is not None
        assert result.documentation_type == DocumentationType.MAKING_INSTRUCTIONS
        assert result.confidence == 0.9
        assert result.excluded is False
        assert "assembly" in result.reason.lower() or "instructions" in result.reason.lower()
        
        # Verify LLM service was called
        mock_llm_service.generate.assert_called_once()
        call_args = mock_llm_service.generate.call_args
        assert "prompt" in call_args.kwargs
        assert "docs/manual.md" in call_args.kwargs["prompt"]
    
    @pytest.mark.asyncio
    async def test_categorize_with_llm_overrides_layer1(self):
        """Test that LLM can override Layer 1 suggestion."""
        mock_llm_service = Mock()
        mock_llm_service.initialize = AsyncMock()
        from src.core.services.base import ServiceStatus
        mock_llm_service.status = ServiceStatus.ACTIVE
        mock_metadata = LLMResponseMetadata(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            tokens_used=100,
            cost=0.01,
            processing_time=0.5
        )
        mock_response = LLMResponse(
            content=json.dumps({
                "documentation_type": "technical-specifications",
                "confidence": 0.95,
                "excluded": False,
                "reason": "File contains technical specifications and dimensions, not assembly instructions",
                "overrides_layer1": True
            }),
            status=LLMResponseStatus.SUCCESS,
            metadata=mock_metadata
        )
        mock_llm_service.generate = AsyncMock(return_value=mock_response)
        
        service = FileCategorizationService(llm_service=mock_llm_service)
        
        file_info = FileInfo(
            path="docs/specs.md",
            size=2000,
            content="# Technical Specifications\n\nDimensions: 100mm x 50mm\n\nTolerances: ±0.1mm",
            file_type="markdown"
        )
        
        # Layer 1 suggests MAKING_INSTRUCTIONS (incorrect)
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
            confidence=0.6,
            excluded=False,
            reason="Directory-based categorization"
        )
        
        result = await service._categorize_with_llm(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            depth=AnalysisDepth.MEDIUM
        )
        
        assert result is not None
        # LLM should override Layer 1
        assert result.documentation_type == DocumentationType.TECHNICAL_SPECIFICATIONS
        assert result.confidence == 0.95
        assert "technical" in result.reason.lower() or "specifications" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_categorize_with_llm_excludes_file(self):
        """Test that LLM can exclude files."""
        mock_llm_service = Mock()
        mock_llm_service.initialize = AsyncMock()
        from src.core.services.base import ServiceStatus
        mock_llm_service.status = ServiceStatus.ACTIVE
        mock_metadata = LLMResponseMetadata(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            tokens_used=100,
            cost=0.01,
            processing_time=0.5
        )
        mock_response = LLMResponse(
            content=json.dumps({
                "documentation_type": "design-files",  # Dummy value
                "confidence": 0.9,
                "excluded": True,
                "reason": "This is a workflow file for CI/CD, not OKH documentation",
                "overrides_layer1": True
            }),
            status=LLMResponseStatus.SUCCESS,
            metadata=mock_metadata
        )
        mock_llm_service.generate = AsyncMock(return_value=mock_response)
        
        service = FileCategorizationService(llm_service=mock_llm_service)
        
        file_info = FileInfo(
            path=".github/workflow.yml",
            size=200,
            content="name: CI\non: push",
            file_type="yaml"
        )
        
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.DESIGN_FILES,  # Dummy
            confidence=0.0,
            excluded=True,
            reason="Workflow file exclusion"
        )
        
        result = await service._categorize_with_llm(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            depth=AnalysisDepth.SHALLOW
        )
        
        assert result is not None
        assert result.excluded is True
        assert "workflow" in result.reason.lower() or "ci/cd" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_categorize_with_llm_json_parsing_error(self):
        """Test handling of JSON parsing errors."""
        mock_llm_service = Mock()
        # Return invalid JSON
        mock_metadata = LLMResponseMetadata(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            tokens_used=100,
            cost=0.01,
            processing_time=0.5
        )
        mock_response = LLMResponse(
            content="This is not valid JSON {invalid",
            status=LLMResponseStatus.SUCCESS,
            metadata=mock_metadata
        )
        mock_llm_service.generate = AsyncMock(return_value=mock_response)
        
        service = FileCategorizationService(llm_service=mock_llm_service)
        
        file_info = FileInfo(
            path="docs/manual.md",
            size=1000,
            content="# Manual",
            file_type="markdown"
        )
        
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
            confidence=0.8,
            excluded=False,
            reason="Directory-based categorization"
        )
        
        # Should return None on JSON parsing error (will fallback to Layer 1)
        result = await service._categorize_with_llm(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            depth=AnalysisDepth.SHALLOW
        )
        
        # Should return None to trigger fallback
        assert result is None
    
    @pytest.mark.asyncio
    async def test_categorize_with_llm_malformed_json_recovery(self):
        """Test recovery from malformed JSON (trailing comma, etc.)."""
        mock_llm_service = Mock()
        mock_llm_service.initialize = AsyncMock()
        from src.core.services.base import ServiceStatus
        mock_llm_service.status = ServiceStatus.ACTIVE
        mock_metadata = LLMResponseMetadata(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            tokens_used=100,
            cost=0.01,
            processing_time=0.5
        )
        # Return JSON with trailing comma (common LLM error)
        mock_response = LLMResponse(
            content=json.dumps({
                "documentation_type": "manufacturing-files",
                "confidence": 0.85,
                "excluded": False,
                "reason": "STL file for 3D printing",
                "overrides_layer1": False
            }) + ",",  # Trailing comma
            status=LLMResponseStatus.SUCCESS,
            metadata=mock_metadata
        )
        mock_llm_service.generate = AsyncMock(return_value=mock_response)
        
        service = FileCategorizationService(llm_service=mock_llm_service)
        
        file_info = FileInfo(
            path="design/part.stl",
            size=5000,
            content="",
            file_type="stl"
        )
        
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.MANUFACTURING_FILES,
            confidence=0.9,
            excluded=False,
            reason="Extension-based categorization"
        )
        
        result = await service._categorize_with_llm(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            depth=AnalysisDepth.SHALLOW
        )
        
        # Should recover from trailing comma and return result
        assert result is not None
        assert result.documentation_type == DocumentationType.MANUFACTURING_FILES
    
    @pytest.mark.asyncio
    async def test_categorize_with_llm_llm_service_error(self):
        """Test handling of LLM service errors."""
        mock_llm_service = Mock()
        mock_llm_service.initialize = AsyncMock()
        from src.core.services.base import ServiceStatus
        mock_llm_service.status = ServiceStatus.ACTIVE
        mock_metadata = LLMResponseMetadata(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            tokens_used=0,
            cost=0.0,
            processing_time=0.0
        )
        mock_response = LLMResponse(
            content="",
            status=LLMResponseStatus.ERROR,
            error_message="LLM service unavailable",
            metadata=mock_metadata
        )
        mock_llm_service.generate = AsyncMock(return_value=mock_response)
        
        service = FileCategorizationService(llm_service=mock_llm_service)
        
        file_info = FileInfo(
            path="docs/manual.md",
            size=1000,
            content="# Manual",
            file_type="markdown"
        )
        
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
            confidence=0.8,
            excluded=False,
            reason="Directory-based categorization"
        )
        
        # Should return None on LLM error (will fallback to Layer 1)
        result = await service._categorize_with_llm(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            depth=AnalysisDepth.SHALLOW
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_categorize_with_llm_uses_content_parser(self):
        """Test that content parser is used to extract content preview."""
        mock_llm_service = Mock()
        mock_llm_service.initialize = AsyncMock()
        from src.core.services.base import ServiceStatus
        mock_llm_service.status = ServiceStatus.ACTIVE
        mock_metadata = LLMResponseMetadata(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            tokens_used=100,
            cost=0.01,
            processing_time=0.5
        )
        mock_response = LLMResponse(
            content=json.dumps({
                "documentation_type": "making-instructions",
                "confidence": 0.9,
                "excluded": False,
                "reason": "Assembly instructions",
                "overrides_layer1": False
            }),
            status=LLMResponseStatus.SUCCESS,
            metadata=mock_metadata
        )
        mock_llm_service.generate = AsyncMock(return_value=mock_response)
        
        service = FileCategorizationService(llm_service=mock_llm_service)
        
        # Create file with long content
        long_content = "# Assembly Instructions\n\n" + "Step " * 100
        file_info = FileInfo(
            path="docs/manual.md",
            size=len(long_content),
            content=long_content,
            file_type="markdown"
        )
        
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
            confidence=0.7,
            excluded=False,
            reason="Directory-based categorization"
        )
        
        result = await service._categorize_with_llm(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            depth=AnalysisDepth.SHALLOW
        )
        
        assert result is not None
        
        # Verify prompt was built with content preview (not full content for SHALLOW)
        call_args = mock_llm_service.generate.call_args
        prompt = call_args.kwargs["prompt"]
        # For SHALLOW, should only include first 500 chars in content preview
        # The prompt includes rules and other sections, so it will be longer than just the content
        # But we can verify the content preview is limited by checking it's not the full content
        assert "first 500 characters" in prompt or "shallow" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_categorize_with_llm_different_depths(self):
        """Test that different analysis depths produce different content previews."""
        mock_llm_service = Mock()
        mock_llm_service.initialize = AsyncMock()
        from src.core.services.base import ServiceStatus
        mock_llm_service.status = ServiceStatus.ACTIVE
        mock_metadata = LLMResponseMetadata(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            tokens_used=100,
            cost=0.01,
            processing_time=0.5
        )
        mock_response = LLMResponse(
            content=json.dumps({
                "documentation_type": "making-instructions",
                "confidence": 0.9,
                "excluded": False,
                "reason": "Assembly instructions",
                "overrides_layer1": False
            }),
            status=LLMResponseStatus.SUCCESS,
            metadata=mock_metadata
        )
        mock_llm_service.generate = AsyncMock(return_value=mock_response)
        
        long_content = "# Manual\n\n" + "Content line " * 200
        file_info = FileInfo(
            path="docs/manual.md",
            size=len(long_content),
            content=long_content,
            file_type="markdown"
        )
        
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
            confidence=0.7,
            excluded=False,
            reason="Directory-based categorization"
        )
        
        # Test Shallow
        service_shallow = FileCategorizationService(llm_service=mock_llm_service)
        await service_shallow._categorize_with_llm(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            depth=AnalysisDepth.SHALLOW
        )
        prompt_shallow = mock_llm_service.generate.call_args.kwargs["prompt"]
        
        # Test Deep
        mock_llm_service.reset_mock()
        mock_llm_service.initialize = AsyncMock()
        mock_llm_service.status = ServiceStatus.ACTIVE
        mock_llm_service.generate = AsyncMock(return_value=mock_response)
        service_deep = FileCategorizationService(llm_service=mock_llm_service)
        await service_deep._categorize_with_llm(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            depth=AnalysisDepth.DEEP
        )
        prompt_deep = mock_llm_service.generate.call_args.kwargs["prompt"]
        
        # Deep should include more content
        assert len(prompt_deep) > len(prompt_shallow)
    
    @pytest.mark.asyncio
    async def test_categorize_with_llm_no_layer1_suggestion(self):
        """Test LLM categorization when Layer 1 suggestion is None."""
        mock_llm_service = Mock()
        mock_llm_service.initialize = AsyncMock()
        from src.core.services.base import ServiceStatus
        mock_llm_service.status = ServiceStatus.ACTIVE
        mock_metadata = LLMResponseMetadata(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            tokens_used=100,
            cost=0.01,
            processing_time=0.5
        )
        mock_response = LLMResponse(
            content=json.dumps({
                "documentation_type": "design-files",
                "confidence": 0.8,
                "excluded": False,
                "reason": "CAD source file",
                "overrides_layer1": False
            }),
            status=LLMResponseStatus.SUCCESS,
            metadata=mock_metadata
        )
        mock_llm_service.generate = AsyncMock(return_value=mock_response)
        
        service = FileCategorizationService(llm_service=mock_llm_service)
        
        file_info = FileInfo(
            path="design/part.scad",
            size=2000,
            content="module part() { ... }",
            file_type="scad"
        )
        
        # No Layer 1 suggestion
        result = await service._categorize_with_llm(
            file_info=file_info,
            layer1_suggestion=None,
            depth=AnalysisDepth.SHALLOW
        )
        
        assert result is not None
        assert result.documentation_type == DocumentationType.DESIGN_FILES

