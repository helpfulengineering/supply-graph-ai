from typing import Optional
from src.plugins.base import PluginSettings as BasePluginSettings
from pydantic import ConfigDict

class PluginSettings(BasePluginSettings):
    """Configuration for the WeFlourish-OHM integration plugin."""
    model_config = ConfigDict(env_prefix="WF_", extra="ignore")

    WEFLOURISH_API_URL: str = "https://weflourish.com/api"
    WEFLOURISH_API_KEY: Optional[str] = None
    OHM_WEBHOOK_SECRET: Optional[str] = None
    OHM_CALLBACK_URL_BASE: str = "http://localhost:8001/v1/api/rfq/webhooks/weflourish"
