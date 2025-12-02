import logging
import os

from dotenv import load_dotenv

from src.core.storage.base import StorageConfig

from .llm_config import get_llm_config, is_llm_enabled, validate_llm_config
from .storage_config import StorageConfigError, get_default_storage_config

# Import secrets manager (lazy import to avoid circular dependencies)
_secrets_manager = None


def _get_secret_or_env(key: str, default: str = None) -> str:
    """Get value from secrets manager or environment variable

    This function tries to get the value from the secrets manager first,
    then falls back to environment variables. This allows for cloud secrets
    manager integration while maintaining backward compatibility.

    Args:
        key: Configuration key name
        default: Default value if not found

    Returns:
        Configuration value or default
    """
    global _secrets_manager

    # Try environment variable first (fastest, most common)
    value = os.getenv(key)
    if value is not None:
        return value

    # Try secrets manager if enabled
    try:
        if _secrets_manager is None:
            # Lazy import to avoid circular dependencies
            from src.core.utils.secrets_manager import get_secrets_manager

            _secrets_manager = get_secrets_manager()

        # Only use secrets manager for sensitive values or if explicitly enabled
        use_secrets_manager = os.getenv("USE_SECRETS_MANAGER", "false").lower() in (
            "true",
            "1",
            "t",
        )

        # List of sensitive keys that should use secrets manager
        sensitive_keys = [
            "API_KEYS",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GOOGLE_AI_API_KEY",
            "AZURE_OPENAI_API_KEY",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AZURE_STORAGE_KEY",
            "GCP_CREDENTIALS_JSON",
            "LLM_ENCRYPTION_KEY",
            "LLM_ENCRYPTION_SALT",
            "LLM_ENCRYPTION_PASSWORD",
        ]

        if use_secrets_manager or key in sensitive_keys:
            secret_value = _secrets_manager.get_secret(key)
            if secret_value is not None:
                return secret_value
    except Exception as e:
        # If secrets manager fails, log and continue with env vars
        if not hasattr(_get_secret_or_env, "_logged_warning"):
            logger.debug(
                f"Secrets manager not available or failed: {e}. Using environment variables only."
            )
            _get_secret_or_env._logged_warning = True

    return default


# Load environment variables from .env file (for local development)
# In container environments, this will be a no-op if .env doesn't exist
load_dotenv()

logger = logging.getLogger(__name__)
LOG_LEVEL = _get_secret_or_env("LOG_LEVEL", "INFO")
LOG_FILE = _get_secret_or_env("LOG_FILE", "logs/app.log")

# API settings
DEBUG = _get_secret_or_env("DEBUG", "False").lower() in ("true", "1", "t")
API_HOST = _get_secret_or_env("API_HOST", "0.0.0.0")

# Port configuration: Support PORT env var (Cloud Run requirement) and API_PORT
# Cloud Run sets PORT, but we also support API_PORT for backward compatibility
PORT_ENV = os.getenv("PORT")  # Cloud Run sets this
API_PORT_ENV = os.getenv("API_PORT")  # Our custom env var
if PORT_ENV:
    API_PORT = int(PORT_ENV)
    if API_PORT_ENV and int(API_PORT_ENV) != int(PORT_ENV):
        logger.warning(
            f"Both PORT ({PORT_ENV}) and API_PORT ({API_PORT_ENV}) are set. "
            f"Using PORT={PORT_ENV} (Cloud Run standard)."
        )
elif API_PORT_ENV:
    API_PORT = int(API_PORT_ENV)
else:
    # Default to 8001 (matches CLI default)
    API_PORT = 8001

# CORS settings
# Parse comma-separated origins from environment variable
CORS_ORIGINS_ENV = _get_secret_or_env("CORS_ORIGINS")
ENVIRONMENT = _get_secret_or_env("ENVIRONMENT", "development").lower()

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
    CORS_ORIGINS = [
        origin.strip() for origin in CORS_ORIGINS_ENV.split(",") if origin.strip()
    ]
    if not CORS_ORIGINS:
        logger.warning("CORS_ORIGINS is set but empty. No CORS origins allowed.")

# API Keys (backward compatibility - used for environment variable keys)
# This is a sensitive value, so it will try secrets manager if enabled
API_KEYS_ENV = _get_secret_or_env("API_KEYS", "")
API_KEYS = (
    [key.strip() for key in API_KEYS_ENV.split(",") if key.strip()]
    if API_KEYS_ENV
    else []
)

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
AUTH_MODE = _get_secret_or_env("AUTH_MODE", "hybrid")  # "env", "storage", "hybrid"
AUTH_ENABLE_STORAGE = _get_secret_or_env("AUTH_ENABLE_STORAGE", "true").lower() in (
    "true",
    "1",
    "t",
)
AUTH_CACHE_TTL = int(
    _get_secret_or_env("AUTH_CACHE_TTL", "300")
)  # 5 minutes in seconds
AUTH_KEY_LENGTH = int(_get_secret_or_env("AUTH_KEY_LENGTH", "32"))  # bytes

# Storage Configuration
try:
    STORAGE_CONFIG = get_default_storage_config()
except StorageConfigError as e:
    logger.error(f"Failed to load storage configuration: {e}")
    if DEBUG:
        # In debug mode, fall back to local storage
        STORAGE_CONFIG = StorageConfig(provider="local", bucket_name="storage")
    else:
        raise

# Cache Configuration
CACHE_ENABLED = _get_secret_or_env("CACHE_ENABLED", "true").lower() in (
    "true",
    "1",
    "t",
)
CACHE_MAX_SIZE = int(_get_secret_or_env("CACHE_MAX_SIZE", "1000"))
CACHE_CLEANUP_INTERVAL = int(_get_secret_or_env("CACHE_CLEANUP_INTERVAL", "60"))

# Rate Limiting Configuration
RATE_LIMIT_ENABLED = _get_secret_or_env("RATE_LIMIT_ENABLED", "true").lower() in (
    "true",
    "1",
    "t",
)
RATE_LIMIT_CLEANUP_INTERVAL = int(
    _get_secret_or_env("RATE_LIMIT_CLEANUP_INTERVAL", "60")
)

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
