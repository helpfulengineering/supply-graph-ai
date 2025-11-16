# Hardcoded Values Implementation Specification

## Overview

This specification defines the implementation plan for replacing hardcoded values with configurable options. These hardcoded values create portability issues, security vulnerabilities, and configuration inconsistencies that need to be addressed before public release.

## Current State Analysis

### Issue 1: Azure Storage URL (Critical)

**Location**: `README.md:156`, `docs/development/local-development-setup.md:120`

**Current Implementation:**
```markdown
"Azure_Storage_ServiceName": "https://projdatablobstorage.blob.core.windows.net",
```

**Problems:**
- Organization-specific hardcoded URL
- Not portable to other deployments
- Appears in documentation (README and docs)
- Typo inconsistency: `projdatablobstorage` vs `projectdatablobstorage`

**Context:**
- Used in documentation examples
- Should be configurable via environment variables
- Storage configuration already supports environment variables

**Severity**: Critical - Not portable, organization-specific

### Issue 2: Default Encryption Credentials (Critical)

**Location**: `src/config/llm_config.py:168-169`

**Current Implementation:**
```python
salt = os.getenv("LLM_ENCRYPTION_SALT", "default_salt").encode()
password = os.getenv("LLM_ENCRYPTION_PASSWORD", "default_password").encode()
```

**Problems:**
- Weak default credentials ("default_salt", "default_password")
- Security vulnerability if defaults are used
- No warning or failure when defaults are used
- Encryption is ineffective with default values

**Context:**
- Used for encrypting LLM API keys
- Should fail securely if not configured
- Production deployments must use strong credentials

**Severity**: Critical - Security vulnerability

### Issue 3: CORS Default Configuration (Critical)

**Location**: `src/config/settings.py:24`

**Current Implementation:**
```python
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS", "*")
if CORS_ORIGINS_ENV == "*":
    # Allow all origins
    CORS_ORIGINS = ["*"]
```

**Problems:**
- Defaults to allowing all origins (`["*"]`)
- Security concern for production deployments
- No warning about security implications
- Should require explicit configuration

**Context:**
- CORS configuration for API
- Development may need `["*"]` but production should restrict
- Should fail or warn in production mode

**Severity**: Critical - Security concern

### Issue 4: API Keys Default (High Priority)

**Location**: `src/config/settings.py:33`

**Current Implementation:**
```python
API_KEYS = os.getenv("API_KEYS", "").split(",")
```

**Problems:**
- Defaults to empty list (no authentication)
- Security concern for production
- No validation that API keys are set in production
- Should require explicit configuration

**Context:**
- API key authentication
- Development may not need keys, but production must
- Should validate in production mode

**Severity**: High - Security concern

### Issue 5: Default Ports and URLs (High Priority)

**Locations**: Multiple files

**Current Implementation:**
- `src/config/settings.py:20`: `API_PORT = int(os.getenv("API_PORT", "8000"))`
- `src/core/main.py:222`: `uvicorn.run(..., port=8000, ...)`
- `src/cli/base.py:33`: `self.server_url = "http://localhost:8001"`
- Documentation references: `8001`, `8081`, `8000`

**Problems:**
- Inconsistent default ports (8000 vs 8001)
- Hardcoded in multiple places
- Documentation doesn't match code
- Should standardize to single default

**Context:**
- API server port configuration
- CLI server URL configuration
- Documentation examples

**Severity**: Medium - Confusion for users

### Issue 6: Organization-Specific URLs (Critical)

**Location**: `README.md:156,159,161`

**Current Implementation:**
```markdown
"Azure_Storage_ServiceName": "https://projdatablobstorage.blob.core.windows.net",
These OKHs and OKWs are taken from our repo: https://github.com/helpfulengineering/library.
Helpful created its own OKW template: https://github.com/helpfulengineering/OKF-Schema
```

**Problems:**
- Organization-specific URLs in documentation
- Not portable to other organizations
- Should use placeholders or environment variables
- Examples should be generic

**Context:**
- Documentation examples
- Should be configurable or use placeholders

**Severity**: Critical - Not portable, organization-specific

### Issue 7: Default Server URL (Low Priority)

**Location**: `src/cli/base.py:33`

**Current Implementation:**
```python
self.server_url = "http://localhost:8001"
```

**Problems:**
- Hardcoded default
- Should be configurable via environment variable
- Acceptable default but should allow override

**Context:**
- CLI configuration
- Default is reasonable but should be configurable

**Severity**: Low - Acceptable default, but should be configurable

### Issue 8: Ollama Default URL (Low Priority)

**Location**: `src/core/llm/providers/ollama.py:71`

**Current Implementation:**
```python
self._base_url = config.base_url or "http://localhost:11434"
```

**Problems:**
- Hardcoded default
- Should be configurable via environment variable
- Acceptable default but should allow override

**Context:**
- Ollama provider configuration
- Default is reasonable but should be configurable

**Severity**: Low - Acceptable default, but should be configurable

### Issue 9: Version Hardcoding

**Location**: `src/core/packaging/builder.py:703`

**Note**: This is already covered in the Version & Metadata specification. Reference that spec for implementation details.

## Requirements

### Functional Requirements

1. **Configuration Management**
   - All hardcoded values should be configurable via environment variables
   - Sensible defaults for development
   - Fail securely in production for security-sensitive values
   - Clear documentation of configuration options

2. **Security Requirements**
   - Encryption credentials must be explicitly configured
   - CORS should not default to allow all in production
   - API keys should be required in production
   - Warnings for insecure defaults

3. **Portability Requirements**
   - No organization-specific URLs in code
   - Documentation should use placeholders
   - Examples should be generic

4. **Consistency Requirements**
   - Standardize default ports
   - Consistent configuration patterns
   - Clear documentation

### Non-Functional Requirements

1. **Backward Compatibility**
   - Existing configurations should continue to work
   - Sensible defaults for development
   - Clear migration path

2. **Documentation**
   - Document all configuration options
   - Provide examples
   - Security warnings where appropriate

## Design Decisions

### Security-First Approach

**For Security-Sensitive Values:**
- Fail if not configured in production
- Warn if using defaults in development
- Require explicit configuration

**For Development Values:**
- Provide sensible defaults
- Allow environment variable override
- Document clearly

### Configuration Strategy

**Environment Variables:**
- Primary configuration method
- Clear naming conventions
- Documented in `env.template`

**Default Values:**
- Development-friendly defaults
- Production-safe defaults where possible
- Fail securely for security-sensitive values

### Documentation Strategy

**Use Placeholders:**
- Replace organization-specific URLs with placeholders
- Use generic examples
- Document configuration requirements

## Implementation Specification

### 1. Fix Azure Storage URL

**File: `README.md`**

**Update documentation to use placeholders:**

```markdown
# Our current working OKH and OKW libraries
Our current OKH and OKW libraries are implemented as publicly accessible Azure blob containers:

    "Azure_Storage_ServiceName": "${AZURE_STORAGE_SERVICE_NAME}",
    "Azure_Storage_OKH_ContainerName": "${AZURE_STORAGE_OKH_CONTAINER_NAME:-okh}",
    "Azure_Storage_OKW_ContainerName": "${AZURE_STORAGE_OKW_CONTAINER_NAME:-okw}"

These OKHs and OKWs are taken from our repo: ${OKH_LIBRARY_REPO_URL:-https://github.com/example/library}.

Example OKW template and OKH extensions are defined here: ${OKF_SCHEMA_REPO_URL:-https://github.com/example/OKF-Schema}

We are currently working with the Internet of Production Alliance (IoPA) to unify these extensions with their official schemas.

**Configuration:**
Set the following environment variables:
- `AZURE_STORAGE_SERVICE_NAME`: Azure storage service URL
- `AZURE_STORAGE_OKH_CONTAINER_NAME`: OKH container name (default: okh)
- `AZURE_STORAGE_OKW_CONTAINER_NAME`: OKW container name (default: okw)
- `OKH_LIBRARY_REPO_URL`: Repository URL for OKH library (optional)
- `OKF_SCHEMA_REPO_URL`: Repository URL for OKF schema (optional)
```

**File: `docs/development/local-development-setup.md`**

**Update to use placeholders:**

```markdown
    "Azure_Storage_ServiceName": "${AZURE_STORAGE_SERVICE_NAME}",
```

### 2. Fix Default Encryption Credentials

**File: `src/config/llm_config.py`**

**Update to fail securely:**

```python
def _get_encryption_key(self) -> bytes:
    """Get or generate encryption key for credential encryption"""
    import os
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    
    if self.encryption_key:
        key = self.encryption_key.encode()
    else:
        # Get encryption credentials from environment
        salt_env = os.getenv("LLM_ENCRYPTION_SALT")
        password_env = os.getenv("LLM_ENCRYPTION_PASSWORD")
        
        # Check if we're in production mode
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        
        # In production, require explicit configuration
        if is_production:
            if not salt_env or not password_env:
                raise ValueError(
                    "LLM_ENCRYPTION_SALT and LLM_ENCRYPTION_PASSWORD must be set in production. "
                    "These are required for secure credential encryption."
                )
            if salt_env == "default_salt" or password_env == "default_password":
                raise ValueError(
                    "Default encryption credentials cannot be used in production. "
                    "Please set LLM_ENCRYPTION_SALT and LLM_ENCRYPTION_PASSWORD to secure values."
                )
        
        # Use provided values or defaults (with warning in development)
        salt = (salt_env or "default_salt").encode()
        password = (password_env or "default_password").encode()
        
        if not is_production and (not salt_env or not password_env):
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "Using default encryption credentials. This is insecure for production. "
                "Please set LLM_ENCRYPTION_SALT and LLM_ENCRYPTION_PASSWORD environment variables."
            )
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
    
    self._fernet = Fernet(key)
    return key
```

### 3. Fix CORS Default Configuration

**File: `src/config/settings.py`**

**Update to be more secure by default:**

```python
# CORS settings
# Parse comma-separated origins from environment variable
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

if CORS_ORIGINS_ENV is None:
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
elif CORS_ORIGINS_ENV == "*":
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
```

### 4. Fix API Keys Default

**File: `src/config/settings.py`**

**Update to validate in production:**

```python
# API Keys
API_KEYS_ENV = os.getenv("API_KEYS", "")
API_KEYS = [key.strip() for key in API_KEYS_ENV.split(",") if key.strip()]

# Validate API keys in production
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
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
```

### 5. Standardize Default Ports

**File: `src/config/settings.py`**

**Update to use consistent default:**

```python
# API settings
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
# Standardize to port 8001 (matches CLI default)
API_PORT = int(os.getenv("API_PORT", "8001"))
```

**File: `src/core/main.py`**

**Update to use settings:**

```python
# Only run the app if this file is executed directly
if __name__ == "__main__":
    from src.config.settings import API_HOST, API_PORT
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=DEBUG)
```

**File: `src/cli/base.py`**

**Update to use environment variable:**

```python
def __init__(self):
    import os
    # Allow environment variable override
    default_server_url = os.getenv("OME_SERVER_URL", "http://localhost:8001")
    self.server_url = default_server_url
    self.timeout = 120.0
    self.retry_attempts = 3
    self.verbose = False
```

### 6. Fix Organization-Specific URLs in Documentation

**File: `README.md`**

**Update to use placeholders (see Issue 1 above)**

**File: `docs/development/local-development-setup.md`**

**Update to use placeholders (see Issue 1 above)**

### 7. Make Ollama URL Configurable

**File: `src/core/llm/providers/ollama.py`**

**Update to use environment variable:**

```python
def __init__(self, config: LLMProviderConfig):
    """
    Initialize the Ollama provider.
    
    Args:
        config: Configuration for the provider
        
    Raises:
        ValueError: If configuration is invalid
    """
    super().__init__(config)
    self._client: Optional[httpx.AsyncClient] = None
    
    # Get base URL from config, environment variable, or default
    import os
    default_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    self._base_url = config.base_url or default_url
    
    # Validate that this is a LOCAL provider
    if config.provider_type != LLMProviderType.LOCAL:
        raise ValueError(f"Provider type must be LOCAL, got {config.provider_type}")
```

### 8. Update Environment Template

**File: `env.template`**

**Add new environment variables:**

```bash
# Environment
ENVIRONMENT=development  # development or production

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
CORS_ORIGINS=*  # Comma-separated list of allowed origins, or * for all
API_KEYS=  # Comma-separated list of API keys for authentication

# LLM Encryption (REQUIRED in production)
LLM_ENCRYPTION_SALT=  # Salt for encryption key derivation
LLM_ENCRYPTION_PASSWORD=  # Password for encryption key derivation

# Storage Configuration
AZURE_STORAGE_SERVICE_NAME=  # Azure storage service URL
AZURE_STORAGE_OKH_CONTAINER_NAME=okh  # OKH container name
AZURE_STORAGE_OKW_CONTAINER_NAME=okw  # OKW container name

# Repository URLs (optional, for documentation)
OKH_LIBRARY_REPO_URL=  # Repository URL for OKH library
OKF_SCHEMA_REPO_URL=  # Repository URL for OKF schema

# CLI Configuration
OME_SERVER_URL=http://localhost:8001  # Default server URL for CLI

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434  # Ollama API base URL
```

## Integration Points

### 1. Configuration Loading

- All values loaded from environment variables
- Sensible defaults for development
- Fail securely in production

### 2. Documentation

- Updated to use placeholders
- Clear configuration instructions
- Security warnings where appropriate

### 3. Environment Template

- All new variables documented
- Clear descriptions
- Default values shown

## Testing Considerations

### Unit Tests

1. **Configuration Tests:**
   - Test default values
   - Test environment variable override
   - Test production mode validation
   - Test security warnings

2. **Security Tests:**
   - Test encryption credential validation
   - Test CORS configuration
   - Test API key validation

### Integration Tests

1. **End-to-End Configuration:**
   - Test with environment variables
   - Test with defaults
   - Test production mode

## Migration Plan

### Phase 1: Implementation (Current)
- Update configuration files
- Add environment variable support
- Update documentation

### Phase 2: Validation (Future)
- Add production mode checks
- Add configuration validation
- Add startup warnings

## Success Criteria

1. ✅ No hardcoded organization-specific URLs
2. ✅ Encryption credentials fail securely in production
3. ✅ CORS defaults are secure
4. ✅ API keys validated in production
5. ✅ Ports standardized
6. ✅ All values configurable via environment variables
7. ✅ Documentation uses placeholders
8. ✅ Environment template updated

## Open Questions / Future Enhancements

1. **Production Mode Detection:**
   - Should we use `ENVIRONMENT` variable?
   - Or detect from other indicators?

2. **Configuration Validation:**
   - Should we validate on startup?
   - Or fail on first use?

3. **Documentation Placeholders:**
   - Should we use `${VAR}` syntax?
   - Or `{{VAR}}` or other format?

## Dependencies

### No New Dependencies

- Uses only existing environment variable handling
- No external libraries required

## Implementation Order

1. Update `src/config/settings.py` for CORS and API keys
2. Update `src/config/llm_config.py` for encryption credentials
3. Standardize ports in `src/config/settings.py` and `src/core/main.py`
4. Update `src/cli/base.py` for server URL
5. Update `src/core/llm/providers/ollama.py` for Ollama URL
6. Update `README.md` and documentation files
7. Update `env.template`
8. Write tests
9. Update documentation

## Notes

### Security Considerations

**Production Mode:**
- Encryption credentials must be explicitly set
- CORS should not default to allow all
- API keys should be required
- Warnings for insecure configurations

**Development Mode:**
- Sensible defaults for convenience
- Warnings about security implications
- Easy to override with environment variables

### Backward Compatibility

**Existing Configurations:**
- Will continue to work with defaults
- New environment variables are optional
- Production mode is opt-in via `ENVIRONMENT` variable

### Documentation Strategy

**Placeholders:**
- Use `${VAR}` or `{{VAR}}` syntax
- Document required vs. optional variables
- Provide examples
- Security warnings where appropriate

