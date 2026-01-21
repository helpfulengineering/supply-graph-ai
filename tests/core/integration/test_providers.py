import pytest
from unittest.mock import MagicMock, patch
from src.core.integration.providers.github import GitHubProvider
from src.core.integration.providers.gitlab import GitLabProvider
from src.core.integration.models.base import IntegrationRequest

@pytest.fixture
def github_provider():
    config = {"api_key": "token", "cache_dir": "/tmp"}
    return GitHubProvider(config)

@pytest.fixture
def gitlab_provider():
    config = {"api_key": "token", "cache_dir": "/tmp"}
    return GitLabProvider(config)

@pytest.mark.asyncio
async def test_github_provider_connect(github_provider):
    with patch("src.core.integration.providers.github.GitHubExtractor") as mock_extractor:
        await github_provider.connect()
        assert github_provider.is_connected
        mock_extractor.assert_called_once()

@pytest.mark.asyncio
async def test_gitlab_provider_connect(gitlab_provider):
    with patch("src.core.integration.providers.gitlab.GitLabExtractor") as mock_extractor:
        await gitlab_provider.connect()
        assert gitlab_provider.is_connected
        mock_extractor.assert_called_once()

@pytest.mark.asyncio
async def test_github_execute_extract(github_provider):
    with patch("src.core.integration.providers.github.GitHubExtractor") as MockExtractor:
        mock_instance = MockExtractor.return_value
        mock_instance.extract_project = MagicMock()

        # Create a real-looking ProjectData or Dict
        # Since we use dataclasses.asdict, we should mock it to be a dataclass or a dict
        from dataclasses import dataclass
        @dataclass
        class MockProjectData:
            name: str

        mock_project_data = MockProjectData(name="test")

        await github_provider.connect()

        # Need to await the async method call on the mock if the real method is async
        async def async_extract(*args, **kwargs):
            return mock_project_data
        mock_instance.extract_project.side_effect = async_extract

        request = IntegrationRequest(
            provider_type="github",
            action="extract_project",
            payload={"url": "https://github.com/test/repo"}
        )
        response = await github_provider.execute(request)

        assert response.success
        # Verify we get the object back directly
        assert response.data.name == "test"
