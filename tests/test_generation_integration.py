"""
Integration tests for OKH manifest generation using real reference data.

This module tests the generation system against the OpenFlexure Microscope manifest
as a reference implementation.
"""

import pytest
import json
from pathlib import Path


def test_openflexure_reference_manifest_exists():
    """Test that the reference manifest file exists and is valid JSON"""
    manifest_path = Path("test-data/openflexure-microscope.okh.json")
    assert manifest_path.exists(), "Reference manifest file not found"
    
    with open(manifest_path, 'r') as f:
        manifest_data = json.load(f)
    
    # Verify it's a valid OKH manifest
    assert "okhv" in manifest_data
    assert "title" in manifest_data
    assert "version" in manifest_data
    assert "license" in manifest_data
    assert "repo" in manifest_data


def test_openflexure_github_url_detection():
    """Test that the OpenFlexure GitHub URL is correctly detected"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    # Test the original GitHub URL from the manifest
    github_url = "https://github.com/rwb27/openflexure_microscope"
    assert router.detect_platform(github_url) == PlatformType.GITHUB
    assert router.validate_url(github_url) is True
    
    # Test repo info extraction
    owner, repo = router.extract_repo_info(github_url)
    assert owner == "rwb27"
    assert repo == "openflexure_microscope"


def test_openflexure_gitlab_url_detection():
    """Test that the OpenFlexure GitLab URL is correctly detected"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    # Test the GitLab URL from metadata
    gitlab_url = "https://gitlab.com/openflexure/openflexure-microscope"
    assert router.detect_platform(gitlab_url) == PlatformType.GITLAB
    assert router.validate_url(gitlab_url) is True
    
    # Test repo info extraction
    owner, repo = router.extract_repo_info(gitlab_url)
    assert owner == "openflexure"
    assert repo == "openflexure-microscope"


def test_openflexure_direct_matching():
    """Test direct field matching against OpenFlexure manifest data"""
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo
    
    # Load reference manifest
    manifest_path = Path("test-data/openflexure-microscope.okh.json")
    with open(manifest_path, 'r') as f:
        reference_manifest = json.load(f)
    
    # Create mock project data based on the reference manifest
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url=reference_manifest["repo"],
        metadata={
            "name": reference_manifest["title"],
            "description": reference_manifest["description"],
            "html_url": reference_manifest["repo"],
            "license": {
                "name": "CERN Open Hardware License",
                "spdx_id": "CERN-OHL-S-2.0"
            }
        },
        files=[
            FileInfo(
                path="README.md",
                size=1024,
                content="# OpenFlexure Microscope\n\n3D printable microscope",
                file_type="markdown"
            ),
            FileInfo(
                path="LICENSE",
                size=1024,
                content="CERN Open Hardware Licence Version 2 - Strongly Reciprocal",
                file_type="text"
            )
        ],
        documentation=[],
        raw_content={}
    )
    
    matcher = DirectMatcher()
    result = matcher.generate_fields(project_data)
    
    # Verify key fields are generated correctly
    assert "title" in result
    assert result["title"].value == "OpenFlexure Microscope"
    assert result["title"].confidence >= 0.9
    
    assert "description" in result
    assert "3D printable microscope" in result["description"].value
    assert result["description"].confidence >= 0.9
    
    assert "repo" in result
    assert result["repo"].value == reference_manifest["repo"]
    assert result["repo"].confidence >= 0.9
    
    assert "license" in result
    # License should be detected from LICENSE file content (first line)
    assert "CERN" in result["license"].value
    assert result["license"].confidence >= 0.8


def test_openflexure_manifest_structure():
    """Test that the reference manifest has the expected structure for generation"""
    manifest_path = Path("test-data/openflexure-microscope.okh.json")
    with open(manifest_path, 'r') as f:
        manifest_data = json.load(f)
    
    # Test required fields
    required_fields = ["title", "version", "license", "licensor", "documentation_language", "function"]
    for field in required_fields:
        assert field in manifest_data, f"Required field '{field}' missing from reference manifest"
        assert manifest_data[field], f"Required field '{field}' is empty in reference manifest"
    
    # Test license structure
    license_data = manifest_data["license"]
    assert isinstance(license_data, dict)
    assert "hardware" in license_data
    assert "documentation" in license_data
    assert "software" in license_data
    
    # Test that we have rich data for generation
    assert "description" in manifest_data
    assert "keywords" in manifest_data
    assert "manufacturing_files" in manifest_data
    assert "design_files" in manifest_data
    assert "materials" in manifest_data
    assert "manufacturing_processes" in manifest_data


def test_openflexure_github_extractor_mock():
    """Test GitHub extractor with OpenFlexure URL"""
    from src.core.generation.platforms.github import GitHubExtractor
    from src.core.generation.models import PlatformType
    import asyncio
    
    extractor = GitHubExtractor()
    
    # Test with the OpenFlexure GitHub URL
    url = "https://github.com/rwb27/openflexure_microscope"
    
    async def test_extraction():
        project_data = await extractor.extract_project(url)
        
        assert project_data.platform == PlatformType.GITHUB
        assert project_data.url == url
        assert "name" in project_data.metadata
        assert "description" in project_data.metadata
        assert len(project_data.files) > 0
        assert len(project_data.documentation) > 0
        
        return project_data
    
    # Run the async test
    project_data = asyncio.run(test_extraction())
    
    # Verify the mock data structure matches what we expect
    assert project_data.metadata["name"] == "openflexure_microscope"
    assert "mock" in project_data.metadata["description"].lower()


def test_generation_pipeline_with_openflexure():
    """Test the complete generation pipeline with OpenFlexure data"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import PlatformType
    import asyncio
    
    # Test the complete pipeline
    url = "https://github.com/rwb27/openflexure_microscope"
    
    async def test_pipeline():
        # Step 1: URL routing
        router = URLRouter()
        platform = router.detect_platform(url)
        assert platform == PlatformType.GITHUB
        
        # Step 2: Project extraction
        extractor = router.route_to_extractor(platform)
        project_data = await extractor.extract_project(url)
        
        # Step 3: Field generation
        matcher = DirectMatcher()
        generated_fields = matcher.generate_fields(project_data)
        
        # Verify we generated some fields
        assert len(generated_fields) > 0
        assert "title" in generated_fields
        assert "repo" in generated_fields
        
        return generated_fields
    
    # Run the pipeline test
    generated_fields = asyncio.run(test_pipeline())
    
    # Verify the generated fields have the expected structure
    for field_name, field_gen in generated_fields.items():
        assert field_gen.value is not None
        assert 0.0 <= field_gen.confidence <= 1.0
        assert field_gen.source_layer.value == "direct"
        assert field_gen.generation_method == "direct_mapping"
        assert field_gen.raw_source is not None


def test_openflexure_manifest_validation():
    """Test that the reference manifest can be loaded by our OKH model"""
    from src.core.models.okh import OKHManifest
    
    manifest_path = Path("test-data/openflexure-microscope.okh.json")
    with open(manifest_path, 'r') as f:
        manifest_data = json.load(f)
    
    # Test that our OKH model can parse the reference manifest
    try:
        okh_manifest = OKHManifest.from_dict(manifest_data)
        
        # Verify key fields
        assert okh_manifest.title == "OpenFlexure Microscope"
        assert okh_manifest.version == "5.20"
        assert okh_manifest.repo == "https://github.com/rwb27/openflexure_microscope"
        assert okh_manifest.license.hardware == "CERN-OHL-S-2.0"
        
        # Verify the manifest is valid
        assert okh_manifest.validate() is True
        
    except Exception as e:
        pytest.fail(f"Failed to parse reference manifest: {e}")


def test_openflexure_metadata_extraction():
    """Test extracting metadata that would be available from GitHub API"""
    manifest_path = Path("test-data/openflexure-microscope.okh.json")
    with open(manifest_path, 'r') as f:
        manifest_data = json.load(f)
    
    # Simulate what GitHub API would return
    mock_github_metadata = {
        "name": "openflexure_microscope",
        "full_name": "rwb27/openflexure_microscope",
        "description": manifest_data["description"],
        "html_url": manifest_data["repo"],
        "clone_url": f"{manifest_data['repo']}.git",
        "default_branch": "master",
        "license": {
            "name": "CERN Open Hardware License",
            "spdx_id": "CERN-OHL-S-2.0"
        },
        "topics": manifest_data["keywords"],
        "created_at": "2016-01-01T00:00:00Z",
        "updated_at": "2023-12-01T00:00:00Z"
    }
    
    # Test that our direct matcher can work with this metadata
    from src.core.generation.layers.direct import DirectMatcher
    from src.core.generation.models import ProjectData, PlatformType
    
    project_data = ProjectData(
        platform=PlatformType.GITHUB,
        url=manifest_data["repo"],
        metadata=mock_github_metadata,
        files=[],
        documentation=[],
        raw_content={}
    )
    
    matcher = DirectMatcher()
    result = matcher.generate_fields(project_data)
    
    # Verify we can extract the key information
    assert "title" in result
    assert result["title"].value == "openflexure_microscope"
    
    assert "description" in result
    assert result["description"].value == manifest_data["description"]
    
    assert "repo" in result
    assert result["repo"].value == manifest_data["repo"]
    
    assert "license" in result
    assert result["license"].value == "CERN-OHL-S-2.0"
