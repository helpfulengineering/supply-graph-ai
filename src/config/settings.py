import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from src.core.storage.base import StorageConfig

from .auth_constants import AUTH_MODE_HYBRID
from .llm_config import get_llm_config, is_llm_enabled, validate_llm_config
from .schema import get_settings, resolve_cors_origins
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

# CORS + environment now come from the typed config schema (Slice 1). The
# schema layers per-environment TOML defaults under process env vars; CORS
# posture warnings are logged once here.
_schema_settings = get_settings()
ENVIRONMENT = _schema_settings.environment
CORS_ORIGINS = resolve_cors_origins(
    _schema_settings.cors_origins, ENVIRONMENT, log=True
)

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

# Authentication Configuration
AUTH_MODE = _get_secret_or_env(
    "AUTH_MODE", AUTH_MODE_HYBRID
)  # "env", "storage", "hybrid"
AUTH_ENABLE_STORAGE = _get_secret_or_env("AUTH_ENABLE_STORAGE", "true").lower() in (
    "true",
    "1",
    "t",
)
AUTH_CACHE_TTL = int(
    _get_secret_or_env("AUTH_CACHE_TTL", "300")
)  # 5 minutes in seconds
AUTH_KEY_LENGTH = int(_get_secret_or_env("AUTH_KEY_LENGTH", "32"))  # bytes

# Security Mode: identity/trust/authz posture (distinct axis from SystemMode matching
# rigor). "peacetime" implemented; "crisis"/"shielded" reserved. Resolved into a
# SecurityPolicy via src/config/security_policy.py. See docs/architecture/security-modes.md.
OHM_SECURITY_MODE = _get_secret_or_env("OHM_SECURITY_MODE", "peacetime")

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

# When true, skip StorageOrganizer .gitkeep seeding on app startup (no PUTs to remote).
STORAGE_SKIP_DIRECTORY_BOOTSTRAP = _get_secret_or_env(
    "STORAGE_SKIP_DIRECTORY_BOOTSTRAP", "false"
).lower() in ("true", "1", "t")

# Cache Configuration
CACHE_ENABLED = _get_secret_or_env("CACHE_ENABLED", "true").lower() in (
    "true",
    "1",
    "t",
)
CACHE_MAX_SIZE = int(_get_secret_or_env("CACHE_MAX_SIZE", "1000"))
CACHE_CLEANUP_INTERVAL = int(_get_secret_or_env("CACHE_CLEANUP_INTERVAL", "60"))
# ``memory`` = in-process LRU (default, zero deps). ``redis`` = Redis protocol
# (Valkey, Azure Cache for Redis, ElastiCache, self-hosted Redis sidecar).
CACHE_BACKEND = (_get_secret_or_env("CACHE_BACKEND", "memory") or "memory").lower()
CACHE_REDIS_URL = (_get_secret_or_env("CACHE_REDIS_URL", "") or "").strip() or None
CACHE_KEY_PREFIX = (_get_secret_or_env("CACHE_KEY_PREFIX", "ohm") or "ohm").strip()

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

# Matching Configuration
# Maximum depth for BOM explosion in nested matching
# This controls how deep the system will recurse when matching nested components
# Higher values allow deeper nesting but may impact performance
MAX_DEPTH = int(_get_secret_or_env("MAX_DEPTH", "5"))
if MAX_DEPTH < 0 or MAX_DEPTH > 10:
    logger.warning(
        f"MAX_DEPTH ({MAX_DEPTH}) is outside recommended range (0-10). "
        "Consider using a value between 1-5 for optimal performance."
    )

# NLP veto (second opinion on fuzzy direct + heuristic hits)
MATCHING_NLP_VETO_ENABLED = _get_secret_or_env(
    "MATCHING_NLP_VETO_ENABLED", "false"
).lower() in ("true", "1", "t")
MATCHING_NLP_VETO_THRESHOLD = float(
    _get_secret_or_env("MATCHING_NLP_VETO_THRESHOLD", "0.2")
)
if not 0.0 <= MATCHING_NLP_VETO_THRESHOLD <= 1.0:
    logger.warning(
        f"MATCHING_NLP_VETO_THRESHOLD ({MATCHING_NLP_VETO_THRESHOLD}) should be in [0, 1]; "
        "clamping may occur at runtime."
    )

# When set, match requests with no inline `okw_facilities` load `*.json` from this path
# (recursively) instead of listing remote storage — avoids hanging curls when cloud
# storage is slow or misconfigured. Production should normally leave this unset.
_match_local = (_get_secret_or_env("MATCHING_LOCAL_OKW_JSON_DIR", "") or "").strip()
MATCHING_LOCAL_OKW_JSON_DIR = _match_local or None

# When true (default), MatchingService.initialize() eagerly loads spaCy models for
# each domain. When false, models load on first NLP use — avoids long stalls inside
# FastAPI Depends(get_matching_service) on constrained or cold-start environments.
MATCHING_PREINIT_NLP = _get_secret_or_env("MATCHING_PREINIT_NLP", "true").lower() in (
    "true",
    "1",
    "t",
)

# When true (default), MatchingService.initialize() runs during app lifespan startup
# so POST /match does not pay cold-init cost on the first user request. Readiness
# stays not_ready until init completes. Set false only for fast local dev without NLP.
MATCHING_EAGER_INIT = _get_secret_or_env("MATCHING_EAGER_INIT", "true").lower() in (
    "true",
    "1",
    "t",
)

# Max seconds to wait for MatchingService.get_instance() during startup pre-init
# and FastAPI Depends resolution (spaCy load can exceed 20s on constrained hosts).
MATCHING_INIT_TIMEOUT_SECONDS = float(
    _get_secret_or_env("MATCHING_INIT_TIMEOUT_SECONDS", "120")
)

# Federation (Phase 5 MVP — disabled by default)
OHM_FEDERATION_ENABLED = _get_secret_or_env(
    "OHM_FEDERATION_ENABLED", "false"
).lower() in (
    "true",
    "1",
    "t",
)
OHM_FEDERATION_NODE_NAME = _get_secret_or_env("OHM_FEDERATION_NODE_NAME", "OHM Node")
OHM_FEDERATION_NODE_ROLE = _get_secret_or_env("OHM_FEDERATION_NODE_ROLE", "peer")
OHM_FEDERATION_SYNC_INTERVAL_SEC = int(
    _get_secret_or_env("OHM_FEDERATION_SYNC_INTERVAL_SEC", "60")
)
_manual_peers = _get_secret_or_env("OHM_FEDERATION_MANUAL_PEERS", "") or ""
OHM_FEDERATION_MANUAL_PEERS = [p.strip() for p in _manual_peers.split(",") if p.strip()]
_relay_urls = _get_secret_or_env("OHM_FEDERATION_RELAY_URLS", "") or ""
OHM_FEDERATION_RELAY_URLS = [u.strip() for u in _relay_urls.split(",") if u.strip()]
_registry_urls = _get_secret_or_env("OHM_FEDERATION_REGISTRY_URLS", "") or ""
OHM_FEDERATION_REGISTRY_URLS = [
    u.strip() for u in _registry_urls.split(",") if u.strip()
]
OHM_FEDERATION_DATA_DIR = _get_secret_or_env(
    "OHM_FEDERATION_DATA_DIR",
    str(Path.home() / ".ohm" / "federation"),
)
OHM_FEDERATION_REGISTER_PUBLIC = _get_secret_or_env(
    "OHM_FEDERATION_REGISTER_PUBLIC", "false"
).lower() in ("true", "1", "t")
OHM_FEDERATION_MDNS_ENABLED = _get_secret_or_env(
    "OHM_FEDERATION_MDNS_ENABLED", "true"
).lower() in ("true", "1", "t")
OHM_FEDERATION_SYNC_RATE_LIMIT_PER_MIN = int(
    _get_secret_or_env("OHM_FEDERATION_SYNC_RATE_LIMIT_PER_MIN", "60")
)
# Optional public seed peer (e.g. https://openhardwaremanager.org). Empty = no seed CTA.
OHM_FEDERATION_SEED_PEER_URL = (
    _get_secret_or_env("OHM_FEDERATION_SEED_PEER_URL", "") or ""
).strip()

# Do not log MATCHING_* here: this module imports before main.setup_logging(), so
# INFO lines would be dropped by the default root logger (WARNING). Log from lifespan.
