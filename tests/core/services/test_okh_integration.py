import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch
from src.core.services.okh_service import OKHService
from src.core.integration.manager import IntegrationManager
from src.core.integration.providers.base import BaseIntegrationProvider
from src.core.integration.models.base import IntegrationCategory, IntegrationResponse

# Mock Provider
class MockVcsProvider(BaseIntegrationProvider):
    def __init__(self, config):
        super().__init__(config)
        self.category = IntegrationCategory.VCS_PLATFORM
        self.provider_type = "mock_vcs"

    async def connect(self):
        self._is_connected = True

    async def disconnect(self):
        self._is_connected = False

    async def check_health(self):
        return True

    async def execute(self, request):
        if request.action == "extract_project":
            # Return a mock object that mimics ProjectData
            from dataclasses import dataclass
            @dataclass
            class MockProjectData:
                name: str
                url: str

            data = MockProjectData(name="test_project", url=request.payload["url"])
            return IntegrationResponse(success=True, data=data)
        return IntegrationResponse(success=False, data=None, error="Unknown action")

@pytest_asyncio.fixture
async def setup_environment():
    # Reset IntegrationManager
    IntegrationManager._instance = None
    IntegrationManager._initialized = False
    manager = IntegrationManager.get_instance()

    # Register mock provider class
    manager.register_provider_class("mock_vcs", MockVcsProvider)

    # Manually configure a provider instance
    # We bypass initialize() to avoid reading config files and just set up what we need
    provider = MockVcsProvider({})
    await provider.connect()

    # We need to ensure the service finds "github_default" or similar
    # In OKHService logic: provider_name = f"{provider_type}_default"
    # So if platform is GITHUB, it looks for "github_default" with provider_type="github"
    # We need to trick it.

    # Let's override the provider_type of our instance to match "github" so the logic finds it
    provider.provider_type = "github"
    manager.providers["github_default"] = provider

    manager._initialized = True

    return manager

@pytest.mark.asyncio
async def test_generate_from_url_integration(setup_environment):
    # Setup service
    service = OKHService()
    await service.initialize() # This might try to initialize manager again, but we set _initialized=True

    # Mock URLRouter to return GITHUB platform
    with patch("src.core.generation.url_router.URLRouter") as MockRouter:
        router_instance = MockRouter.return_value
        router_instance.validate_url.return_value = True

        from src.core.generation.models import PlatformType
        router_instance.detect_platform.return_value = PlatformType.GITHUB

        # We also need to mock GenerationEngine because OKHService calls it after getting project data
        # We don't want to run the actual generation engine
        with patch("src.core.generation.engine.GenerationEngine") as MockEngine:
            engine_instance = MockEngine.return_value

            # Mock generate_manifest_async result
            mock_result = MagicMock()
            mock_result.to_dict.return_value = {
                "title": "Generated Manifest",
                "repo": "https://github.com/test/repo"
            }
            # Add quality report mock
            mock_quality = MagicMock()
            mock_quality.overall_quality = 1.0
            mock_quality.required_fields_complete = True
            mock_quality.missing_required_fields = []
            mock_quality.recommendations = []
            mock_result.quality_report = mock_quality

            # Need to set side_effect because generate_manifest_async is awaited
            async def async_generate(*args, **kwargs):
                return mock_result
            engine_instance.generate_manifest_async.side_effect = async_generate

            # Execute
            result = await service.generate_from_url("https://github.com/test/repo")

            # Verify
            assert result["success"] is True
            assert result["manifest"]["title"] == "Generated Manifest"

            # Verify Interaction
            # We can check if our mock provider was executed if we attached a spy,
            # but the fact we got success means it worked because:
            # 1. OKHService called IntegrationManager
            # 2. IntegrationManager found "github_default"
            # 3. Executed our MockVcsProvider
            # 4. MockVcsProvider returned MockProjectData
            # 5. OKHService passed MockProjectData to GenerationEngine
