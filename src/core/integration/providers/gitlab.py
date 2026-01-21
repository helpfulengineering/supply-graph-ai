from typing import Any, Dict, Optional
import logging
from .base import BaseIntegrationProvider
from ..models.base import IntegrationCategory, IntegrationRequest, IntegrationResponse, ProviderStatus
from ...generation.platforms.gitlab import GitLabExtractor

logger = logging.getLogger(__name__)

class GitLabProvider(BaseIntegrationProvider):
    """
    GitLab integration provider using the existing GitLabExtractor.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.category = IntegrationCategory.VCS_PLATFORM
        self.provider_type = "gitlab"
        self._extractor: Optional[GitLabExtractor] = None

    async def connect(self) -> None:
        """Initialize the GitLabExtractor."""
        try:
            token = self.config.get("api_key")
            cache_dir = self.config.get("cache_dir")

            self._extractor = GitLabExtractor(
                gitlab_token=token,
                cache_dir=cache_dir
            )
            self._is_connected = True
            logger.info("GitLabProvider connected")
        except Exception as e:
            logger.error(f"Failed to connect GitLabProvider: {e}")
            self._is_connected = False
            raise

    async def disconnect(self) -> None:
        """Cleanup resources."""
        self._extractor = None
        self._is_connected = False
        logger.info("GitLabProvider disconnected")

    async def check_health(self) -> bool:
        """Check if we can connect to GitLab API."""
        if not self._is_connected or not self._extractor:
            return False
        return self._is_connected

    async def execute(self, request: IntegrationRequest) -> IntegrationResponse:
        """
        Execute GitLab operations.
        Supported actions: 'extract_project'
        """
        if not self._is_connected or not self._extractor:
            return IntegrationResponse(success=False, data=None, error="Provider not connected")

        try:
            if request.action == "extract_project":
                url = request.payload.get("url")
                if not url:
                    return IntegrationResponse(success=False, data=None, error="URL required")

                project_data = await self._extractor.extract_project(url)
                # Return object directly (in-process)
                return IntegrationResponse(
                    success=True,
                    data=project_data
                )

            else:
                return IntegrationResponse(success=False, data=None, error=f"Unknown action: {request.action}")

        except Exception as e:
            logger.error(f"GitLabProvider execution error: {e}")
            return IntegrationResponse(success=False, data=None, error=str(e))
