"""
Unit tests for FileCategorizationPrompts.

Tests the structured prompt templates for LLM file categorization.
Following TDD approach: write tests first, then implement.
"""

import pytest
from pathlib import Path
from src.core.generation.services.prompts.file_categorization_prompts import FileCategorizationPrompts
from src.core.generation.models import FileInfo, AnalysisDepth
from src.core.generation.utils.file_categorization import FileCategorizationResult
from src.core.models.okh import DocumentationType


class TestFileCategorizationPrompts:
    """Test the FileCategorizationPrompts class."""
    
    def test_prompts_class_exists(self):
        """Test that FileCategorizationPrompts class exists."""
        assert FileCategorizationPrompts is not None
    
    def test_build_categorization_prompt_exists(self):
        """Test that build_categorization_prompt method exists."""
        assert hasattr(FileCategorizationPrompts, 'build_categorization_prompt')
    
    def test_build_categorization_prompt_basic(self):
        """Test building a basic categorization prompt."""
        file_info = FileInfo(
            path="docs/manual.md",
            size=1000,
            content="# Assembly Instructions\n\nStep 1: ...",
            file_type="markdown"
        )
        
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
            confidence=0.8,
            excluded=False,
            reason="Directory-based categorization"
        )
        
        prompt = FileCategorizationPrompts.build_categorization_prompt(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            content_preview="# Assembly Instructions\n\nStep 1: ...",
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "docs/manual.md" in prompt
        assert "MAKING_INSTRUCTIONS" in prompt or "making-instructions" in prompt
    
    def test_build_categorization_prompt_includes_file_metadata(self):
        """Test that prompt includes file metadata."""
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
        
        prompt = FileCategorizationPrompts.build_categorization_prompt(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            content_preview="",
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        assert "design/part.stl" in prompt
        assert ".stl" in prompt or "stl" in prompt
        assert "design" in prompt
    
    def test_build_categorization_prompt_includes_layer1_suggestion(self):
        """Test that prompt includes Layer 1 suggestion."""
        file_info = FileInfo(
            path="README.md",
            size=500,
            content="# Project\n\nDescription...",
            file_type="markdown"
        )
        
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.DOCUMENTATION_HOME,
            confidence=0.7,
            excluded=False,
            reason="Filename-based categorization"
        )
        
        prompt = FileCategorizationPrompts.build_categorization_prompt(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            content_preview="# Project\n\nDescription...",
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        assert "70.0%" in prompt or "70%" in prompt or "0.7" in prompt
        assert "DOCUMENTATION_HOME" in prompt or "documentation-home" in prompt
        assert "Filename-based" in prompt or "filename" in prompt.lower()
    
    def test_build_categorization_prompt_includes_content_preview(self):
        """Test that prompt includes content preview."""
        file_info = FileInfo(
            path="docs/specs.md",
            size=2000,
            content="# Technical Specifications\n\nDimensions: 100mm x 50mm\n\nTolerances: ±0.1mm",
            file_type="markdown"
        )
        
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.TECHNICAL_SPECIFICATIONS,
            confidence=0.6,
            excluded=False,
            reason="Filename-based categorization"
        )
        
        content_preview = "# Technical Specifications\n\nDimensions: 100mm x 50mm"
        
        prompt = FileCategorizationPrompts.build_categorization_prompt(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            content_preview=content_preview,
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        assert "Technical Specifications" in prompt
        assert "Dimensions" in prompt
    
    def test_build_categorization_prompt_includes_documentation_type_rules(self):
        """Test that prompt includes DocumentationType rules."""
        file_info = FileInfo(
            path="manual/assembly.md",
            size=1500,
            content="# Assembly Guide\n\nStep by step...",
            file_type="markdown"
        )
        
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
            confidence=0.8,
            excluded=False,
            reason="Directory-based categorization"
        )
        
        prompt = FileCategorizationPrompts.build_categorization_prompt(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            content_preview="# Assembly Guide\n\nStep by step...",
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        # Should include rules for MAKING_INSTRUCTIONS
        assert "MAKING_INSTRUCTIONS" in prompt or "making-instructions" in prompt
        # Should include description or examples
        assert any(keyword in prompt.lower() for keyword in ["instruction", "assembly", "build", "human"])
    
    def test_build_categorization_prompt_different_depths(self):
        """Test that prompt adapts to different analysis depths."""
        file_info = FileInfo(
            path="docs/manual.md",
            size=5000,
            content="A" * 5000,  # Long content
            file_type="markdown"
        )
        
        layer1_suggestion = FileCategorizationResult(
            documentation_type=DocumentationType.MAKING_INSTRUCTIONS,
            confidence=0.7,
            excluded=False,
            reason="Directory-based categorization"
        )
        
        # Test Shallow depth
        prompt_shallow = FileCategorizationPrompts.build_categorization_prompt(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            content_preview="A" * 500,  # First 500 chars
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        # Test Medium depth
        prompt_medium = FileCategorizationPrompts.build_categorization_prompt(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            content_preview="A" * 2000,  # First 2000 chars
            analysis_depth=AnalysisDepth.MEDIUM
        )
        
        # Test Deep depth
        prompt_deep = FileCategorizationPrompts.build_categorization_prompt(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            content_preview="A" * 5000,  # Full content
            analysis_depth=AnalysisDepth.DEEP
        )
        
        # All should be valid prompts
        assert len(prompt_shallow) > 0
        assert len(prompt_medium) > 0
        assert len(prompt_deep) > 0
        
        # Deep should mention full document analysis
        assert "full" in prompt_deep.lower() or "complete" in prompt_deep.lower() or "entire" in prompt_deep.lower()
    
    def test_build_categorization_prompt_excluded_file(self):
        """Test prompt building for excluded files."""
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
        
        prompt = FileCategorizationPrompts.build_categorization_prompt(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            content_preview="name: CI\non: push",
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        # Should mention exclusion or workflow
        assert "excluded" in prompt.lower() or "workflow" in prompt.lower() or "exclude" in prompt.lower()
    
    def test_build_categorization_prompt_json_output_format(self):
        """Test that prompt requests JSON output format."""
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
        
        prompt = FileCategorizationPrompts.build_categorization_prompt(
            file_info=file_info,
            layer1_suggestion=layer1_suggestion,
            content_preview="# Manual",
            analysis_depth=AnalysisDepth.SHALLOW
        )
        
        # Should request JSON format
        assert "json" in prompt.lower()
        assert "{" in prompt or "}" in prompt  # JSON structure mentioned
    
    def test_build_categorization_prompt_all_documentation_types(self):
        """Test that prompt includes rules for all DocumentationTypes."""
        file_info = FileInfo(
            path="test.md",
            size=100,
            content="Test",
            file_type="markdown"
        )
        
        # Test with different documentation types
        doc_types = [
            DocumentationType.MAKING_INSTRUCTIONS,
            DocumentationType.MANUFACTURING_FILES,
            DocumentationType.DESIGN_FILES,
            DocumentationType.DOCUMENTATION_HOME,
            DocumentationType.TECHNICAL_SPECIFICATIONS,
            DocumentationType.OPERATING_INSTRUCTIONS,
            DocumentationType.PUBLICATIONS,
        ]
        
        for doc_type in doc_types:
            layer1_suggestion = FileCategorizationResult(
                documentation_type=doc_type,
                confidence=0.7,
                excluded=False,
                reason="Test"
            )
            
            prompt = FileCategorizationPrompts.build_categorization_prompt(
                file_info=file_info,
                layer1_suggestion=layer1_suggestion,
                content_preview="Test",
                analysis_depth=AnalysisDepth.SHALLOW
            )
            
            # Should include the documentation type
            assert doc_type.value in prompt or doc_type.name in prompt

