"""
Tests for Review Interface functionality.

Following TDD approach: write tests first, then implement ReviewInterface.
"""

import pytest
from unittest.mock import Mock, patch
from io import StringIO
import sys


def test_review_interface_import():
    """Test that ReviewInterface can be imported"""
    from src.core.generation.review import ReviewInterface
    
    assert ReviewInterface is not None


def test_review_interface_creation():
    """Test ReviewInterface instantiation"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import ManifestGeneration, ProjectData, PlatformType
    
    # Create mock manifest generation
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    assert interface is not None
    assert interface.manifest_generation == manifest_gen


def test_review_interface_has_review_method():
    """Test that ReviewInterface has review method"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import ManifestGeneration, ProjectData, PlatformType
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    assert hasattr(interface, 'review')
    assert callable(getattr(interface, 'review'))


def test_review_interface_has_edit_field_method():
    """Test that ReviewInterface has edit_field method"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import ManifestGeneration, ProjectData, PlatformType
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    assert hasattr(interface, 'edit_field')
    assert callable(getattr(interface, 'edit_field'))


def test_review_interface_has_add_field_method():
    """Test that ReviewInterface has add_field method"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import ManifestGeneration, ProjectData, PlatformType
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    assert hasattr(interface, 'add_field')
    assert callable(getattr(interface, 'add_field'))


def test_review_interface_has_remove_field_method():
    """Test that ReviewInterface has remove_field method"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import ManifestGeneration, ProjectData, PlatformType
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    assert hasattr(interface, 'remove_field')
    assert callable(getattr(interface, 'remove_field'))


def test_review_interface_has_show_quality_report_method():
    """Test that ReviewInterface has show_quality_report method"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import ManifestGeneration, ProjectData, PlatformType
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    assert hasattr(interface, 'show_quality_report')
    assert callable(getattr(interface, 'show_quality_report'))


def test_review_interface_has_export_manifest_method():
    """Test that ReviewInterface has export_manifest method"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import ManifestGeneration, ProjectData, PlatformType
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    assert hasattr(interface, 'export_manifest')
    assert callable(getattr(interface, 'export_manifest'))


def test_review_interface_edit_field():
    """Test editing a field in the manifest"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import (
        ManifestGeneration, ProjectData, PlatformType, FieldGeneration, GenerationLayer
    )
    
    # Create manifest with a field
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    field_gen = FieldGeneration(
        value="Original Title",
        confidence=0.9,
        source_layer=GenerationLayer.DIRECT,
        generation_method="direct_mapping",
        raw_source="metadata.name"
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={"title": field_gen},
        confidence_scores={"title": 0.9},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    
    # Edit the field
    interface.edit_field("title", "Updated Title")
    
    assert manifest_gen.generated_fields["title"].value == "Updated Title"
    assert manifest_gen.generated_fields["title"].confidence == 1.0  # User edit = 100% confidence


def test_review_interface_add_field():
    """Test adding a new field to the manifest"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import (
        ManifestGeneration, ProjectData, PlatformType, FieldGeneration, GenerationLayer
    )
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    
    # Add a new field
    interface.add_field("version", "1.0.0")
    
    assert "version" in manifest_gen.generated_fields
    assert manifest_gen.generated_fields["version"].value == "1.0.0"
    assert manifest_gen.generated_fields["version"].confidence == 1.0
    assert manifest_gen.generated_fields["version"].source_layer == GenerationLayer.USER_EDIT


def test_review_interface_remove_field():
    """Test removing a field from the manifest"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import (
        ManifestGeneration, ProjectData, PlatformType, FieldGeneration, GenerationLayer
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
        value="Test Title",
        confidence=0.9,
        source_layer=GenerationLayer.DIRECT,
        generation_method="direct_mapping",
        raw_source="metadata.name"
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={"title": field_gen},
        confidence_scores={"title": 0.9},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    
    # Remove the field
    interface.remove_field("title")
    
    assert "title" not in manifest_gen.generated_fields
    assert "title" not in manifest_gen.confidence_scores


def test_review_interface_show_quality_report():
    """Test displaying quality report"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import (
        ManifestGeneration, ProjectData, PlatformType, QualityReport
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
        overall_quality=0.8,
        required_fields_complete=True,
        missing_required_fields=[],
        low_confidence_fields=[],
        recommendations=["Test recommendation"]
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=quality_report,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    
    # Capture output
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        interface.show_quality_report()
        output = mock_stdout.getvalue()
    
    assert "Overall Quality: 0.8" in output
    assert "Required Fields Complete: True" in output
    assert "Test recommendation" in output


def test_review_interface_export_manifest():
    """Test exporting manifest to OKH format"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import (
        ManifestGeneration, ProjectData, PlatformType, FieldGeneration, GenerationLayer
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
        value="Test Project",
        confidence=0.9,
        source_layer=GenerationLayer.DIRECT,
        generation_method="direct_mapping",
        raw_source="metadata.name"
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={"title": field_gen},
        confidence_scores={"title": 0.9},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    
    # Export manifest
    okh_manifest = interface.export_manifest()
    
    assert okh_manifest is not None
    assert hasattr(okh_manifest, 'title')
    assert okh_manifest.title == "Test Project"


def test_review_interface_interactive_review():
    """Test interactive review process"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import (
        ManifestGeneration, ProjectData, PlatformType, FieldGeneration, GenerationLayer
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
        value="Test Title",
        confidence=0.9,
        source_layer=GenerationLayer.DIRECT,
        generation_method="direct_mapping",
        raw_source="metadata.name"
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={"title": field_gen},
        confidence_scores={"title": 0.9},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    
    # Test that the review method exists and can be called
    assert hasattr(interface, 'review')
    assert callable(interface.review)
    
    # Test the individual command methods work
    assert hasattr(interface, '_edit_field')
    assert hasattr(interface, '_add_field')
    assert hasattr(interface, '_remove_field')
    assert hasattr(interface, '_show_quality_report')
    assert hasattr(interface, '_export_manifest')
    assert hasattr(interface, '_quit')
    
    # Test that the commands dictionary is properly set up
    assert 'e' in interface._commands
    assert 'a' in interface._commands
    assert 'r' in interface._commands
    assert 'q' in interface._commands
    assert 'x' in interface._commands
    assert 'h' in interface._commands
    assert 'quit' in interface._commands


def test_review_interface_field_validation():
    """Test field validation during editing"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import (
        ManifestGeneration, ProjectData, PlatformType, FieldGeneration, GenerationLayer
    )
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    
    # Test adding invalid field
    with pytest.raises(ValueError, match="Invalid field name"):
        interface.add_field("", "value")
    
    # Test adding field with empty value
    with pytest.raises(ValueError, match="Field value cannot be empty"):
        interface.add_field("title", "")


def test_review_interface_help_command():
    """Test help command functionality"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import (
        ManifestGeneration, ProjectData, PlatformType
    )
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    
    # Test help display
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        interface.show_help()
        output = mock_stdout.getvalue()
    
    assert "Available commands:" in output
    assert "e - Edit field" in output
    assert "a - Add field" in output
    assert "r - Remove field" in output
    assert "q - Show quality report" in output
    assert "x - Export manifest" in output
    assert "h - Show help" in output
    assert "quit - Quit review" in output


def test_review_interface_error_handling():
    """Test error handling in review interface"""
    from src.core.generation.review import ReviewInterface
    from src.core.generation.models import (
        ManifestGeneration, ProjectData, PlatformType
    )
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    manifest_gen = ManifestGeneration(
        project_data=project_data,
        generated_fields={},
        confidence_scores={},
        quality_report=None,
        missing_fields=[]
    )
    
    interface = ReviewInterface(manifest_gen)
    
    # Test editing non-existent field
    with pytest.raises(ValueError, match="Field 'nonexistent' not found"):
        interface.edit_field("nonexistent", "value")
    
    # Test removing non-existent field
    with pytest.raises(ValueError, match="Field 'nonexistent' not found"):
        interface.remove_field("nonexistent")
