from src.plugins.base import PluginSettings as BasePluginSettings

class PluginSettings(BasePluginSettings):
    """
    Plugin-specific settings.
    Can be configured via environment variables with the prefix TEMPLATE_PLUGIN_.
    """
    API_KEY: str = "default_key"

    class Config:
        env_prefix = "TEMPLATE_PLUGIN_"
