"""
Tests for OKH manifest generation data models.

Following TDD approach: write tests first, then implement models.
"""

import pytest
from datetime import datetime
from enum import Enum


def test_platform_type_enum():
    """Test that PlatformType enum exists and has expected values"""
    from src.core.generation.models import PlatformType
    
    assert hasattr(PlatformType, 'GITHUB')
    assert hasattr(PlatformType, 'GITLAB')
    assert hasattr(PlatformType, 'CODEBERG')
    assert hasattr(PlatformType, 'HACKADAY')
    assert hasattr(PlatformType, 'UNKNOWN')


def test_generation_quality_enum():
    """Test that GenerationQuality enum exists and has expected values"""
    from src.core.generation.models import GenerationQuality
    
    assert hasattr(GenerationQuality, 'COMPLETE')
    assert hasattr(GenerationQuality, 'PARTIAL')
    assert hasattr(GenerationQuality, 'INSUFFICIENT')
    assert hasattr(GenerationQuality, 'REQUIRES_REVIEW')


def test_generation_layer_enum():
    """Test that GenerationLayer enum exists and has expected values"""
    from src.core.generation.models import GenerationLayer
    
    assert hasattr(GenerationLayer, 'DIRECT')
    assert hasattr(GenerationLayer, 'HEURISTIC')
    assert hasattr(GenerationLayer, 'NLP')
    assert hasattr(GenerationLayer, 'LLM')


def test_project_data_creation():
    """Test ProjectData dataclass creation"""
    from src.core.generation.models import ProjectData, PlatformType
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "test-repo", "description": "Test repository"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    assert project_data.platform == PlatformType.GITHUB
    assert project_data.url == "https://github.com/user/repo"
    assert project_data.metadata["name"] == "test-repo"
    assert isinstance(project_data.files, list)
    assert isinstance(project_data.documentation, list)
    assert isinstance(project_data.raw_content, dict)


def test_field_generation_creation():
    """Test FieldGeneration dataclass creation"""
    from src.core.generation.models import FieldGeneration, GenerationLayer
    
    field_gen = FieldGeneration(
        value="Test Project",
        confidence=0.95,
        source_layer=GenerationLayer.DIRECT,
        generation_method="direct_mapping",
        raw_source="repo.name"
    )
    
    assert field_gen.value == "Test Project"
    assert field_gen.confidence == 0.95
    assert field_gen.source_layer == GenerationLayer.DIRECT
    assert field_gen.generation_method == "direct_mapping"
    assert field_gen.raw_source == "repo.name"


def test_generation_metadata_creation():
    """Test GenerationMetadata dataclass creation"""
    from src.core.generation.models import GenerationMetadata, GenerationQuality
    
    metadata = GenerationMetadata(
        generation_timestamp=datetime.now(),
        source_url="https://github.com/user/repo",
        generation_quality=GenerationQuality.COMPLETE,
        flags=[],
        confidence_scores={"title": 0.95, "description": 0.85},
        processing_logs=["Started generation", "Completed direct matching"]
    )
    
    assert isinstance(metadata.generation_timestamp, datetime)
    assert metadata.source_url == "https://github.com/user/repo"
    assert metadata.generation_quality == GenerationQuality.COMPLETE
    assert isinstance(metadata.flags, list)
    assert metadata.confidence_scores["title"] == 0.95
    assert len(metadata.processing_logs) == 2


def test_generation_metadata_add_log():
    """Test adding processing logs to GenerationMetadata"""
    from src.core.generation.models import GenerationMetadata
    
    metadata = GenerationMetadata()
    metadata.add_processing_log("Test log entry")
    
    assert "Test log entry" in metadata.processing_logs


def test_generation_metadata_update_confidence():
    """Test updating confidence scores in GenerationMetadata"""
    from src.core.generation.models import GenerationMetadata
    
    metadata = GenerationMetadata()
    metadata.update_confidence("title", 0.95)
    
    assert metadata.confidence_scores["title"] == 0.95


def test_manifest_generation_creation():
    """Test ManifestGeneration dataclass creation"""
    from src.core.generation.models import (
        ManifestGeneration, ProjectData, FieldGeneration,
        PlatformType, GenerationLayer, QualityReport
    )
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    field_gen = FieldGeneration(
        value="Test",
        confidence=0.9,
        source_layer=GenerationLayer.DIRECT,
        generation_method="direct",
        raw_source="test"
    )
    
    quality_report = QualityReport(
        overall_quality=0.85,
        required_fields_complete=True,
        missing_required_fields=[],
        low_confidence_fields=[],
        recommendations=[]
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={"title": field_gen},
        confidence_scores={"title": 0.9},
        quality_report=quality_report,
        missing_fields=[]
    )
    
    assert manifest_gen.project_data.platform == PlatformType.GITHUB
    assert "title" in manifest_gen.generated_fields
    assert manifest_gen.confidence_scores["title"] == 0.9
    assert manifest_gen.quality_report.overall_quality == 0.85
    assert isinstance(manifest_gen.missing_fields, list)


def test_quality_report_creation():
    """Test QualityReport dataclass creation"""
    from src.core.generation.models import QualityReport
    
    report = QualityReport(
        overall_quality=0.85,
        required_fields_complete=True,
        missing_required_fields=[],
        low_confidence_fields=["version"],
        recommendations=["Consider adding more detailed description"]
    )
    
    assert report.overall_quality == 0.85
    assert report.required_fields_complete is True
    assert len(report.missing_required_fields) == 0
    assert "version" in report.low_confidence_fields
    assert len(report.recommendations) == 1


def test_layer_config_creation():
    """Test LayerConfig dataclass creation"""
    from src.core.generation.models import LayerConfig
    
    config = LayerConfig(
        use_direct=True,
        use_heuristic=False,
        use_nlp=False,
        use_llm=False,
        min_confidence=0.7,
        progressive_enhancement=True,
        save_reference=False
    )
    
    assert config.use_direct is True
    assert config.use_heuristic is False
    assert config.use_nlp is False
    assert config.use_llm is False
    assert config.min_confidence == 0.7
    assert config.progressive_enhancement is True
    assert config.save_reference is False


def test_layer_config_defaults():
    """Test LayerConfig default values"""
    from src.core.generation.models import LayerConfig
    
    config = LayerConfig()
    
    # Should default to progressive enhancement with direct layer only
    assert config.use_direct is True
    assert config.progressive_enhancement is True
    assert config.min_confidence == 0.7


def test_generation_result_creation():
    """Test GenerationResult dataclass creation"""
    from src.core.generation.models import (
        GenerationResult, ManifestGeneration, GenerationMetadata,
        ProjectData, PlatformType, QualityReport
    )
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    quality_report = QualityReport(
        overall_quality=0.85,
        required_fields_complete=True,
        missing_required_fields=[],
        low_confidence_fields=[],
        recommendations=[]
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=quality_report,
        missing_fields=[]
    )
    
    metadata = GenerationMetadata()
    
    result = GenerationResult(
        data=manifest_gen,
        metadata=metadata
    )
    
    assert result.data == manifest_gen
    assert result.metadata == metadata


def test_file_info_creation():
    """Test FileInfo dataclass for tracking project files"""
    from src.core.generation.models import FileInfo
    
    file_info = FileInfo(
        path="README.md",
        size=1024,
        content="# Test Project",
        file_type="markdown"
    )
    
    assert file_info.path == "README.md"
    assert file_info.size == 1024
    assert file_info.content == "# Test Project"
    assert file_info.file_type == "markdown"


def test_document_info_creation():
    """Test DocumentInfo dataclass for tracking documentation"""
    from src.core.generation.models import DocumentInfo
    
    doc_info = DocumentInfo(
        title="User Manual",
        path="docs/manual.md",
        doc_type="user-manual",
        content="User manual content"
    )
    
    assert doc_info.title == "User Manual"
    assert doc_info.path == "docs/manual.md"
    assert doc_info.doc_type == "user-manual"
    assert doc_info.content == "User manual content"

