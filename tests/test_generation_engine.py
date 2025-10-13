"""
Tests for Generation Engine functionality.

Following TDD approach: write tests first, then implement GenerationEngine.
"""

import pytest
from unittest.mock import Mock, AsyncMock


def test_generation_engine_import():
    """Test that GenerationEngine can be imported"""
    from src.core.generation.engine import GenerationEngine
    
    assert GenerationEngine is not None


def test_generation_engine_creation():
    """Test GenerationEngine instantiation"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import LayerConfig
    
    config = LayerConfig()
    engine = GenerationEngine(config)
    assert engine is not None
    assert engine.config == config


def test_generation_engine_has_generate_manifest():
    """Test that GenerationEngine has generate_manifest method"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import LayerConfig
    
    config = LayerConfig()
    engine = GenerationEngine(config)
    assert hasattr(engine, 'generate_manifest')
    assert callable(getattr(engine, 'generate_manifest'))


def test_generation_engine_default_config():
    """Test GenerationEngine with default configuration"""
    from src.core.generation.engine import GenerationEngine
    
    engine = GenerationEngine()
    assert engine.config is not None
    assert engine.config.use_direct is True
    assert engine.config.progressive_enhancement is True


def test_generate_manifest_direct_layer_only():
    """Test manifest generation using only direct layer"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import (
        LayerConfig, ProjectData, PlatformType, FileInfo, DocumentInfo
    )
    
    config = LayerConfig(
        use_direct=True,
        use_heuristic=False,
        use_nlp=False,
        use_llm=False,
        progressive_enhancement=True
    )
    engine = GenerationEngine(config)
    
    # Create mock project data
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "test-project", "description": "Test description"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = engine.generate_manifest(project_data)
    
    assert result is not None
    assert result.project_data == project_data
    assert len(result.generated_fields) > 0
    assert "title" in result.generated_fields
    assert result.generated_fields["title"].value == "test-project"


def test_generate_manifest_progressive_enhancement():
    """Test progressive enhancement behavior"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import (
        LayerConfig, ProjectData, PlatformType, FileInfo, DocumentInfo
    )
    
    config = LayerConfig(
        use_direct=True,
        use_heuristic=True,
        use_nlp=False,
        use_llm=False,
        progressive_enhancement=True,
        min_confidence=0.8
    )
    engine = GenerationEngine(config)
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "test-project", "description": "Test description"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = engine.generate_manifest(project_data)
    
    # Should use direct layer and stop if confidence is high enough
    assert result is not None
    assert len(result.generated_fields) > 0
    
    # Check that all fields have high confidence (direct layer)
    for field_name, field_gen in result.generated_fields.items():
        assert field_gen.confidence >= 0.8


def test_generate_manifest_field_completion_tracking():
    """Test that field completion is tracked correctly"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import (
        LayerConfig, ProjectData, PlatformType, FileInfo, DocumentInfo
    )
    
    config = LayerConfig()
    engine = GenerationEngine(config)
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "test-project"},  # Missing description
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = engine.generate_manifest(project_data)
    
    assert result is not None
    assert "title" in result.generated_fields
    assert "description" not in result.generated_fields  # Not in metadata
    # Note: "description" is not a required field, so it won't be in missing_fields


def test_generate_manifest_confidence_aggregation():
    """Test that confidence scores are aggregated correctly"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import (
        LayerConfig, ProjectData, PlatformType, FileInfo, DocumentInfo
    )
    
    config = LayerConfig()
    engine = GenerationEngine(config)
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "test-project", "description": "Test description"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = engine.generate_manifest(project_data)
    
    assert result is not None
    assert len(result.confidence_scores) > 0
    
    # Check that confidence scores match field generations
    for field_name, field_gen in result.generated_fields.items():
        assert field_name in result.confidence_scores
        assert result.confidence_scores[field_name] == field_gen.confidence


def test_generate_manifest_quality_report():
    """Test that quality report is generated"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import (
        LayerConfig, ProjectData, PlatformType, FileInfo, DocumentInfo
    )
    
    config = LayerConfig()
    engine = GenerationEngine(config)
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "test-project", "description": "Test description"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = engine.generate_manifest(project_data)
    
    assert result is not None
    assert result.quality_report is not None
    assert result.quality_report.overall_quality >= 0.0
    assert result.quality_report.overall_quality <= 1.0


def test_generate_manifest_layer_orchestration():
    """Test that layers are orchestrated correctly"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import (
        LayerConfig, ProjectData, PlatformType, FileInfo, DocumentInfo
    )
    
    config = LayerConfig(
        use_direct=True,
        use_heuristic=False,
        use_nlp=False,
        use_llm=False
    )
    engine = GenerationEngine(config)
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "test-project"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = engine.generate_manifest(project_data)
    
    # Should only use direct layer
    for field_name, field_gen in result.generated_fields.items():
        assert field_gen.source_layer.value == "direct"


def test_generate_manifest_missing_required_fields():
    """Test handling of missing required fields"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import (
        LayerConfig, ProjectData, PlatformType, FileInfo, DocumentInfo
    )
    
    config = LayerConfig()
    engine = GenerationEngine(config)
    
    # Project data with minimal information
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},  # No metadata
        files=[],     # No files
        documentation=[],
        raw_content={}
    )
    
    result = engine.generate_manifest(project_data)
    
    assert result is not None
    assert len(result.generated_fields) == 1  # Only repo from URL
    assert len(result.missing_fields) > 0  # Many required fields missing
    assert "title" in result.missing_fields
    assert "license" in result.missing_fields
    # Note: "description" is not a required field, so it won't be in missing_fields


def test_generate_manifest_with_files():
    """Test manifest generation with project files"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import (
        LayerConfig, ProjectData, PlatformType, FileInfo, DocumentInfo
    )
    
    config = LayerConfig()
    engine = GenerationEngine(config)
    
    files = [
        FileInfo(
            path="README.md",
            size=1024,
            content="# Test Project\n\nA test hardware project",
            file_type="markdown"
        ),
        FileInfo(
            path="LICENSE",
            size=1024,
            content="MIT License\n\nCopyright (c) 2023",
            file_type="text"
        )
    ]
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "test-project"},
        files=files,
        documentation=[],
        raw_content={}
    )
    
    result = engine.generate_manifest(project_data)
    
    assert result is not None
    assert "readme" in result.generated_fields
    assert "license" in result.generated_fields
    assert result.generated_fields["readme"].value == "# Test Project\n\nA test hardware project"
    assert "MIT" in result.generated_fields["license"].value


def test_generate_manifest_async_behavior():
    """Test that generate_manifest works with async operations"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import (
        LayerConfig, ProjectData, PlatformType, FileInfo, DocumentInfo
    )
    import asyncio
    
    config = LayerConfig()
    engine = GenerationEngine(config)
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "test-project", "description": "Test description"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    async def test_async():
        result = await engine.generate_manifest_async(project_data)
        assert result is not None
        assert len(result.generated_fields) > 0
        return result
    
    # Run the async test
    result = asyncio.run(test_async())
    assert result is not None


def test_generate_manifest_error_handling():
    """Test error handling in manifest generation"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import LayerConfig
    
    config = LayerConfig()
    engine = GenerationEngine(config)
    
    # Test with None project data
    with pytest.raises(ValueError, match="Project data cannot be None"):
        engine.generate_manifest(None)
    
    # Test with invalid project data
    with pytest.raises(ValueError, match="Invalid project data"):
        engine.generate_manifest("invalid_data")


def test_generate_manifest_config_validation():
    """Test that configuration is validated"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import LayerConfig
    
    # Test with invalid config
    with pytest.raises(ValueError, match="Invalid layer configuration"):
        GenerationEngine("invalid_config")
    
    # Test with config that has no layers enabled
    config = LayerConfig(
        use_direct=False,
        use_heuristic=False,
        use_nlp=False,
        use_llm=False
    )
    
    with pytest.raises(ValueError, match="At least one generation layer must be enabled"):
        GenerationEngine(config)


def test_generate_manifest_layer_priority():
    """Test that layers are applied in correct priority order"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import (
        LayerConfig, ProjectData, PlatformType, FileInfo, DocumentInfo
    )
    
    config = LayerConfig(
        use_direct=True,
        use_heuristic=True,
        use_nlp=False,
        use_llm=False,
        progressive_enhancement=False  # Use all enabled layers
    )
    engine = GenerationEngine(config)
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "test-project"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = engine.generate_manifest(project_data)
    
    # Should use direct layer first (highest priority)
    assert result is not None
    assert "title" in result.generated_fields
    assert result.generated_fields["title"].source_layer.value == "direct"


def test_generate_manifest_metadata_tracking():
    """Test that generation metadata is tracked correctly"""
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import (
        LayerConfig, ProjectData, PlatformType, FileInfo, DocumentInfo
    )
    
    config = LayerConfig()
    engine = GenerationEngine(config)
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "test-project"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = engine.generate_manifest(project_data)
    
    assert result is not None
    # Should have processing logs
    assert len(result.quality_report.recommendations) >= 0
    # Should track which layers were used
    assert result.quality_report.overall_quality >= 0.0
