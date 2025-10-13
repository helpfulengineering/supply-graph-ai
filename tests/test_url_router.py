"""
Tests for URL router functionality.

Following TDD approach: write tests first, then implement URLRouter.
"""

import pytest
from unittest.mock import Mock


def test_url_router_import():
    """Test that URLRouter can be imported"""
    from src.core.generation.url_router import URLRouter
    
    assert URLRouter is not None


def test_detect_platform_github():
    """Test GitHub URL detection"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    # Test various GitHub URL formats
    assert router.detect_platform("https://github.com/user/repo") == PlatformType.GITHUB
    assert router.detect_platform("https://github.com/user/repo.git") == PlatformType.GITHUB
    assert router.detect_platform("http://github.com/user/repo") == PlatformType.GITHUB
    assert router.detect_platform("github.com/user/repo") == PlatformType.GITHUB


def test_detect_platform_gitlab():
    """Test GitLab URL detection"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    # Test various GitLab URL formats
    assert router.detect_platform("https://gitlab.com/user/repo") == PlatformType.GITLAB
    assert router.detect_platform("https://gitlab.com/user/repo.git") == PlatformType.GITLAB
    assert router.detect_platform("http://gitlab.com/user/repo") == PlatformType.GITLAB
    assert router.detect_platform("gitlab.com/user/repo") == PlatformType.GITLAB


def test_detect_platform_codeberg():
    """Test Codeberg URL detection"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    # Test various Codeberg URL formats
    assert router.detect_platform("https://codeberg.org/user/repo") == PlatformType.CODEBERG
    assert router.detect_platform("https://codeberg.org/user/repo.git") == PlatformType.CODEBERG
    assert router.detect_platform("http://codeberg.org/user/repo") == PlatformType.CODEBERG
    assert router.detect_platform("codeberg.org/user/repo") == PlatformType.CODEBERG


def test_detect_platform_hackaday():
    """Test Hackaday.io URL detection"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    # Test various Hackaday URL formats
    assert router.detect_platform("https://hackaday.io/project/12345") == PlatformType.HACKADAY
    assert router.detect_platform("http://hackaday.io/project/12345") == PlatformType.HACKADAY
    assert router.detect_platform("hackaday.io/project/12345") == PlatformType.HACKADAY


def test_detect_platform_unknown():
    """Test unknown URL detection"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    # Test unknown URLs
    assert router.detect_platform("https://example.com/repo") == PlatformType.UNKNOWN
    assert router.detect_platform("https://bitbucket.org/user/repo") == PlatformType.UNKNOWN
    assert router.detect_platform("not-a-url") == PlatformType.UNKNOWN
    assert router.detect_platform("") == PlatformType.UNKNOWN


def test_validate_url_valid():
    """Test URL validation with valid URLs"""
    from src.core.generation.url_router import URLRouter
    
    router = URLRouter()
    
    # Test valid URLs
    assert router.validate_url("https://github.com/user/repo") is True
    assert router.validate_url("http://github.com/user/repo") is True
    assert router.validate_url("https://gitlab.com/user/repo") is True
    assert router.validate_url("https://codeberg.org/user/repo") is True
    assert router.validate_url("https://hackaday.io/project/12345") is True


def test_validate_url_invalid():
    """Test URL validation with invalid URLs"""
    from src.core.generation.url_router import URLRouter
    
    router = URLRouter()
    
    # Test invalid URLs
    assert router.validate_url("not-a-url") is False
    assert router.validate_url("") is False
    assert router.validate_url("ftp://github.com/user/repo") is False
    assert router.validate_url("github.com") is False  # Missing path


def test_route_to_extractor_github():
    """Test routing to GitHub extractor"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    extractor = router.route_to_extractor(PlatformType.GITHUB)
    assert extractor is not None
    # Should return a GitHub extractor instance
    assert hasattr(extractor, 'extract_project')


def test_route_to_extractor_gitlab():
    """Test routing to GitLab extractor"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    extractor = router.route_to_extractor(PlatformType.GITLAB)
    assert extractor is not None
    # Should return a GitLab extractor instance
    assert hasattr(extractor, 'extract_project')


def test_route_to_extractor_unknown():
    """Test routing for unknown platform"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    # Should raise an exception for unknown platforms
    with pytest.raises(ValueError, match="No extractor available for platform"):
        router.route_to_extractor(PlatformType.UNKNOWN)


def test_route_to_extractor_hackaday():
    """Test routing to Hackaday extractor (not implemented yet)"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    # Should raise an exception for unimplemented platforms
    with pytest.raises(ValueError, match="No extractor available for platform"):
        router.route_to_extractor(PlatformType.HACKADAY)


def test_route_to_extractor_codeberg():
    """Test routing to Codeberg extractor (not implemented yet)"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    # Should raise an exception for unimplemented platforms
    with pytest.raises(ValueError, match="No extractor available for platform"):
        router.route_to_extractor(PlatformType.CODEBERG)


def test_validate_and_detect_combined():
    """Test combined URL validation and platform detection"""
    from src.core.generation.url_router import URLRouter
    from src.core.generation.models import PlatformType
    
    router = URLRouter()
    
    # Valid GitHub URL
    url = "https://github.com/user/repo"
    assert router.validate_url(url) is True
    assert router.detect_platform(url) == PlatformType.GITHUB
    
    # Invalid URL
    url = "not-a-url"
    assert router.validate_url(url) is False
    assert router.detect_platform(url) == PlatformType.UNKNOWN


def test_url_normalization():
    """Test URL normalization functionality"""
    from src.core.generation.url_router import URLRouter
    
    router = URLRouter()
    
    # Test that URLs are normalized consistently
    urls = [
        "https://github.com/user/repo",
        "https://github.com/user/repo.git",
        "http://github.com/user/repo",
        "github.com/user/repo"
    ]
    
    for url in urls:
        normalized = router.normalize_url(url)
        assert normalized.startswith("https://github.com/")
        assert normalized.endswith("/user/repo")


def test_extract_repo_info_github():
    """Test extracting repository information from GitHub URLs"""
    from src.core.generation.url_router import URLRouter
    
    router = URLRouter()
    
    url = "https://github.com/user/repo"
    owner, repo = router.extract_repo_info(url)
    
    assert owner == "user"
    assert repo == "repo"


def test_extract_repo_info_gitlab():
    """Test extracting repository information from GitLab URLs"""
    from src.core.generation.url_router import URLRouter
    
    router = URLRouter()
    
    url = "https://gitlab.com/user/repo"
    owner, repo = router.extract_repo_info(url)
    
    assert owner == "user"
    assert repo == "repo"


def test_extract_repo_info_invalid():
    """Test extracting repository information from invalid URLs"""
    from src.core.generation.url_router import URLRouter
    
    router = URLRouter()
    
    # Should raise exception for invalid URLs
    with pytest.raises(ValueError, match="Cannot extract repo info from URL"):
        router.extract_repo_info("not-a-url")
    
    with pytest.raises(ValueError, match="Cannot extract repo info from URL"):
        router.extract_repo_info("https://github.com/user")  # Missing repo
