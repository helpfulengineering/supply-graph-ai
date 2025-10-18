import os
import logging
from dotenv import load_dotenv
from src.core.storage.base import StorageConfig

from .storage_config import get_default_storage_config, StorageConfigError
from .llm_config import get_llm_config, is_llm_enabled, validate_llm_config


# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

# API settings
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# CORS settings
# Parse comma-separated origins from environment variable or use default
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS", "*")
if CORS_ORIGINS_ENV == "*":
    # Allow all origins
    CORS_ORIGINS = ["*"]
else:
    # Parse comma-separated list of allowed origins
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_ENV.split(",")]

# API Keys
API_KEYS = os.getenv("API_KEYS", "").split(",")

# Storage Configuration
try:
    STORAGE_CONFIG = get_default_storage_config()
except StorageConfigError as e:
    logger.error(f"Failed to load storage configuration: {e}")
    if DEBUG:
        # In debug mode, fall back to local storage
        STORAGE_CONFIG = StorageConfig(
            provider="local",
            bucket_name="storage"
        )
    else:
        raise

# LLM Configuration
LLM_CONFIG = get_llm_config()
LLM_ENABLED = is_llm_enabled()

# Validate LLM configuration on startup
if LLM_ENABLED:
    llm_validation = validate_llm_config()
    if not llm_validation["valid"]:
        logger.warning("LLM configuration has issues:")
        for error in llm_validation["errors"]:
            logger.warning(f"  - {error}")
    else:
        logger.info("LLM configuration validated successfully")
else:
    logger.info("LLM integration is disabled")
