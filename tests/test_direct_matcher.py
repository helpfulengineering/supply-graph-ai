"""
Tests for Layer 1 Direct Matcher functionality.

Following TDD approach: write tests first, then implement DirectMatcher.
"""

import pytest
from unittest.mock import Mock


def test_direct_matcher_import():
    """Test that DirectMatcher can be imported"""
    from src.core.generation.layers.direct import DirectMatcher
    
    assert DirectMatcher is not None


def test_direct_matcher_creation():
    """Test DirectMatcher instantiation"""
    from src.core.generation.layers.direct import DirectMatcher
    
    matcher = DirectMatcher()
    assert matcher is not None


def test_direct_matcher_has_generate_fields():
    """Test that DirectMatcher has generate_fields method"""
    from src.core.generation.layers.direct import DirectMatcher
    
    matcher = DirectMatcher()
    assert hasattr(matcher, 'generate_fields')
    assert callable(getattr(matcher, 'generate_fields'))


def test_generate_fields_github_title():
    """Test direct mapping of GitHub repo name to manifest title"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    matcher = DirectMatcher()
    
    # Create mock project data
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "awesome-project", "description": "An awesome hardware project"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = matcher.generate_fields(project_data)
    
    assert "title" in result
    assert result["title"].value == "awesome-project"
    assert result["title"].confidence >= 0.9
    assert result["title"].source_layer.value == "direct"


def test_generate_fields_github_description():
    """Test direct mapping of GitHub description to manifest description"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    matcher = DirectMatcher()
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "awesome-project", "description": "An awesome hardware project"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = matcher.generate_fields(project_data)
    
    assert "description" in result
    assert result["description"].value == "An awesome hardware project"
    assert result["description"].confidence >= 0.9
    assert result["description"].source_layer.value == "direct"


def test_generate_fields_github_repo_url():
    """Test direct mapping of GitHub URL to manifest repo field"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    matcher = DirectMatcher()
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "awesome-project", "html_url": "https://github.com/user/repo"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = matcher.generate_fields(project_data)
    
    assert "repo" in result
    assert result["repo"].value == "https://github.com/user/repo"
    assert result["repo"].confidence >= 0.9
    assert result["repo"].source_layer.value == "direct"


def test_generate_fields_license_from_metadata():
    """Test direct mapping of license from metadata"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    matcher = DirectMatcher()
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={
            "name": "awesome-project",
            "license": {"name": "MIT License", "spdx_id": "MIT"}
        },
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = matcher.generate_fields(project_data)
    
    assert "license" in result
    assert result["license"].value == "MIT"
    assert result["license"].confidence >= 0.9
    assert result["license"].source_layer.value == "direct"


def test_generate_fields_license_from_file():
    """Test license detection from LICENSE file"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    matcher = DirectMatcher()
    
    files = [
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
        metadata={"name": "awesome-project"},
        files=files,
        documentation=[],
        raw_content={}
    )
    
    result = matcher.generate_fields(project_data)
    
    assert "license" in result
    # Should detect MIT from LICENSE file content
    assert "MIT" in result["license"].value
    assert result["license"].confidence >= 0.8
    assert result["license"].source_layer.value == "direct"


def test_generate_fields_readme_from_file():
    """Test README content extraction"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    matcher = DirectMatcher()
    
    files = [
        FileInfo(
            path="README.md",
            size=1024,
            content="# Awesome Project\n\nThis is an awesome hardware project.",
            file_type="markdown"
        )
    ]
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "awesome-project"},
        files=files,
        documentation=[],
        raw_content={}
    )
    
    result = matcher.generate_fields(project_data)
    
    assert "readme" in result
    assert result["readme"].value == "# Awesome Project\n\nThis is an awesome hardware project."
    assert result["readme"].confidence >= 0.9
    assert result["readme"].source_layer.value == "direct"


def test_generate_fields_gitlab_metadata():
    """Test direct mapping for GitLab metadata"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    matcher = DirectMatcher()
    
    project_data = ProjectData(
        platform=PlatformType.GITLAB,
        url="https://gitlab.com/user/repo",
        metadata={
            "name": "gitlab-project",
            "description": "A GitLab hardware project",
            "web_url": "https://gitlab.com/user/repo"
        },
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = matcher.generate_fields(project_data)
    
    assert "title" in result
    assert result["title"].value == "gitlab-project"
    assert "description" in result
    assert result["description"].value == "A GitLab hardware project"
    assert "repo" in result
    assert result["repo"].value == "https://gitlab.com/user/repo"


def test_generate_fields_missing_metadata():
    """Test behavior when metadata is missing"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    matcher = DirectMatcher()
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={},  # Empty metadata
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = matcher.generate_fields(project_data)
    
    # Should not generate metadata-based fields
    assert "title" not in result
    assert "description" not in result
    # But should still generate repo from URL
    assert "repo" in result
    assert result["repo"].value == "https://github.com/user/repo"


def test_generate_fields_empty_files():
    """Test behavior when no files are present"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    matcher = DirectMatcher()
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "awesome-project"},
        files=[],  # No files
        documentation=[],
        raw_content={}
    )
    
    result = matcher.generate_fields(project_data)
    
    # Should still generate metadata-based fields
    assert "title" in result
    assert result["title"].value == "awesome-project"
    
    # Should not generate file-based fields
    assert "readme" not in result
    assert "license" not in result


def test_generate_fields_confidence_scores():
    """Test that confidence scores are appropriate for direct matching"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    matcher = DirectMatcher()
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "awesome-project", "description": "Test description"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = matcher.generate_fields(project_data)
    
    # Direct mappings should have high confidence
    for field_name, field_gen in result.items():
        assert field_gen.confidence >= 0.8, f"Field {field_name} has low confidence: {field_gen.confidence}"


def test_generate_fields_generation_method():
    """Test that generation method is set correctly"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    matcher = DirectMatcher()
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "awesome-project"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = matcher.generate_fields(project_data)
    
    # All fields should have direct_mapping as generation method
    for field_name, field_gen in result.items():
        assert field_gen.generation_method == "direct_mapping", f"Field {field_name} has wrong method: {field_gen.generation_method}"


def test_generate_fields_raw_source():
    """Test that raw source is set correctly"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    matcher = DirectMatcher()
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/user/repo",
        metadata={"name": "awesome-project"},
        files=[],
        documentation=[],
        raw_content={}
    )
    
    result = matcher.generate_fields(project_data)
    
    # Check that raw source is set appropriately
    if "title" in result:
        assert result["title"].raw_source == "metadata.name"
    
    if "description" in result:
        assert result["description"].raw_source == "metadata.description"
    
    if "repo" in result:
        assert result["repo"].raw_source in ["metadata.html_url", "url"]
