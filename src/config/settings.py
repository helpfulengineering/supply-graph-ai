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
# Standardize to port 8001 (matches CLI default)
API_PORT = int(os.getenv("API_PORT", "8001"))

# CORS settings
# Parse comma-separated origins from environment variable
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

if CORS_ORIGINS_ENV is None or CORS_ORIGINS_ENV.strip() == "":
    # Default based on environment
    if ENVIRONMENT == "production":
        # In production, default to empty list (no CORS allowed)
        # Must be explicitly configured
        CORS_ORIGINS = []
        logger.warning(
            "CORS_ORIGINS not set in production. No CORS origins allowed by default. "
            "Set CORS_ORIGINS environment variable to allow specific origins."
        )
    else:
        # In development, allow all origins for convenience
        CORS_ORIGINS = ["*"]
        logger.info(
            "CORS_ORIGINS not set. Allowing all origins in development mode. "
            "Set CORS_ORIGINS environment variable to restrict origins."
        )
elif CORS_ORIGINS_ENV.strip() == "*":
    # Explicit wildcard
    if ENVIRONMENT == "production":
        logger.warning(
            "CORS_ORIGINS is set to '*' in production. This allows all origins. "
            "Consider restricting to specific origins for better security."
        )
    CORS_ORIGINS = ["*"]
else:
    # Parse comma-separated list of allowed origins
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_ENV.split(",") if origin.strip()]
    if not CORS_ORIGINS:
        logger.warning("CORS_ORIGINS is set but empty. No CORS origins allowed.")

# API Keys (backward compatibility - used for environment variable keys)
API_KEYS_ENV = os.getenv("API_KEYS", "")
API_KEYS = [key.strip() for key in API_KEYS_ENV.split(",") if key.strip()]

# Validate API keys in production
if ENVIRONMENT == "production":
    if not API_KEYS:
        logger.warning(
            "API_KEYS not set in production. API authentication is disabled. "
            "Set API_KEYS environment variable to enable authentication."
        )
    # Optionally, fail if no API keys in production
    # Uncomment the following to require API keys in production:
    # if not API_KEYS:
    #     raise ValueError(
    #         "API_KEYS must be set in production. "
    #         "Set API_KEYS environment variable with comma-separated list of API keys."
    #     )

# Authentication Configuration
AUTH_MODE = os.getenv("AUTH_MODE", "hybrid")  # "env", "storage", "hybrid"
AUTH_ENABLE_STORAGE = os.getenv("AUTH_ENABLE_STORAGE", "true").lower() in ("true", "1", "t")
AUTH_CACHE_TTL = int(os.getenv("AUTH_CACHE_TTL", "300"))  # 5 minutes in seconds
AUTH_KEY_LENGTH = int(os.getenv("AUTH_KEY_LENGTH", "32"))  # bytes

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

# Cache Configuration
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() in ("true", "1", "t")
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))
CACHE_CLEANUP_INTERVAL = int(os.getenv("CACHE_CLEANUP_INTERVAL", "60"))

# Rate Limiting Configuration
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "t")
RATE_LIMIT_CLEANUP_INTERVAL = int(os.getenv("RATE_LIMIT_CLEANUP_INTERVAL", "60"))

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
