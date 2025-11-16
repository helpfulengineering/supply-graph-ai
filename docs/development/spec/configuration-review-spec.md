# Configuration Review Implementation Specification

## Overview

This specification defines the implementation plan for resolving environment variable naming inconsistencies and ensuring comprehensive configuration documentation. The review identified discrepancies between variable names used in code and those documented in `env.template`.

## Current State Analysis

### Issue: Environment Variable Naming Inconsistencies

**Location**: Multiple files

**Problems:**
- Variable names in code don't match `env.template`
- Some variables used in code are not documented
- Inconsistent naming conventions across providers
- Users may set variables that aren't recognized

**Context:**
- `env.template` is the primary documentation for configuration
- Code uses `os.getenv()` with specific variable names
- Mismatches cause configuration to fail silently
- Users may be confused about which names to use

**Severity**: Medium - Configuration confusion, potential runtime errors

### Naming Inconsistencies Identified

#### 1. AWS Configuration

**env.template:**
- `AWS_REGION`

**Code (`storage_config.py:41`):**
- `AWS_DEFAULT_REGION`

**Impact**: Users setting `AWS_REGION` won't have it recognized

#### 2. Azure Configuration

**env.template:**
- `AZURE_STORAGE_ACCOUNT_NAME`
- `AZURE_STORAGE_ACCOUNT_KEY`
- `AZURE_CONTAINER_NAME`

**Code (`storage_config.py:23,24,99`):**
- `AZURE_STORAGE_ACCOUNT`
- `AZURE_STORAGE_KEY`
- `AZURE_STORAGE_CONTAINER`

**Impact**: All three Azure variables won't work as documented

#### 3. GCP Configuration

**env.template:**
- `GOOGLE_CLOUD_PROJECT_ID`
- `GOOGLE_CLOUD_STORAGE_BUCKET`

**Code (`storage_config.py:57,107`):**
- `GCP_PROJECT_ID`
- `GCP_STORAGE_BUCKET`

**Impact**: GCP configuration won't work as documented

#### 4. LLM Configuration

**env.template:**
- `LLM_PROVIDER`
- `LLM_MODEL`

**Code (`llm_config.py:293,299`):**
- `LLM_DEFAULT_PROVIDER`
- `LLM_DEFAULT_MODEL`

**Impact**: LLM provider/model configuration won't work as documented

### Undocumented Variables

#### Variables Used in Code but Not in env.template:

1. **LLM Encryption:**
   - `LLM_ENCRYPTION_KEY` - Used in `llm_config.py:157`
   - `LLM_ENCRYPTION_SALT` - Used in `llm_config.py:168` (has default)
   - `LLM_ENCRYPTION_PASSWORD` - Used in `llm_config.py:169` (has default)

2. **Storage:**
   - `LOCAL_STORAGE_PATH` - Used in `storage_config.py:110` (has default: "storage")

3. **Provider Base URLs:**
   - `{PROVIDER}_API_BASE_URL` - Used in `llm_config.py:314` (e.g., `OPENAI_API_BASE_URL`, `ANTHROPIC_API_BASE_URL`)

4. **OpenAI Organization:**
   - `OPENAI_ORGANIZATION_ID` - Used in `llm_config.py:322`

5. **GCP Credentials:**
   - `GCP_CREDENTIALS_JSON` - Used in `storage_config.py:58`

6. **Environment:**
   - `ENVIRONMENT` - Referenced in hardcoded-values-spec (for production mode detection)

7. **CLI:**
   - `OME_SERVER_URL` - Referenced in hardcoded-values-spec (for CLI server URL)

8. **Ollama:**
   - `OLLAMA_BASE_URL` - Referenced in hardcoded-values-spec (for Ollama provider)

## Requirements

### Functional Requirements

1. **Naming Consistency**
   - All variable names in code match `env.template`
   - Consistent naming conventions across providers
   - Clear, descriptive names

2. **Documentation Completeness**
   - All variables used in code are documented
   - Clear descriptions for each variable
   - Default values documented
   - Required vs optional clearly indicated

3. **Backward Compatibility**
   - Support both old and new names during transition
   - Clear migration path
   - Deprecation warnings

### Non-Functional Requirements

1. **Usability**
   - Clear, intuitive variable names
   - Consistent patterns
   - Easy to understand

2. **Maintainability**
   - Single source of truth
   - Easy to add new variables
   - Clear documentation

## Design Decisions

### Naming Standardization Strategy

**Option 1: Update Code to Match env.template (Recommended)**
- Pros: env.template is user-facing documentation, less disruptive
- Cons: Requires code changes

**Option 2: Update env.template to Match Code**
- Pros: No code changes needed
- Cons: Less intuitive names, breaks user expectations

**Option 3: Support Both Names (Transition Period)**
- Pros: Backward compatible, smooth migration
- Cons: More complex, temporary solution

**Decision: Option 1 (Update Code) with Option 3 (Transition Support)**
- Update code to use names from env.template
- Support both names during transition period
- Log deprecation warnings for old names
- Remove old name support in future version

### Naming Convention Standards

**Storage Provider Variables:**
- Use provider prefix: `{PROVIDER}_{RESOURCE}`
- Be consistent: `AZURE_STORAGE_ACCOUNT` not `AZURE_STORAGE_ACCOUNT_NAME`
- Use standard AWS names: `AWS_DEFAULT_REGION` (AWS standard)

**LLM Variables:**
- Use descriptive names: `LLM_DEFAULT_PROVIDER` not `LLM_PROVIDER`
- Or use simpler: `LLM_PROVIDER` (preferred for user-facing)

**Decision: Use Simpler Names for User-Facing Variables**
- `LLM_PROVIDER` instead of `LLM_DEFAULT_PROVIDER`
- `LLM_MODEL` instead of `LLM_DEFAULT_MODEL`
- Code can use `LLM_DEFAULT_PROVIDER` internally but read from `LLM_PROVIDER`

## Implementation Specification

### 1. Update Storage Configuration

**File: `src/config/storage_config.py`**

**Update to support both old and new names with deprecation warnings:**

```python
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def get_azure_credentials() -> Dict[str, str]:
    """Get Azure Blob Storage credentials from environment variables"""
    # Support both old and new names
    account_name = (
        os.getenv("AZURE_STORAGE_ACCOUNT_NAME") or  # New name (from env.template)
        os.getenv("AZURE_STORAGE_ACCOUNT")           # Old name (backward compatibility)
    )
    account_key = (
        os.getenv("AZURE_STORAGE_ACCOUNT_KEY") or   # New name (from env.template)
        os.getenv("AZURE_STORAGE_KEY")               # Old name (backward compatibility)
    )
    
    # Log deprecation warning if using old names
    if os.getenv("AZURE_STORAGE_ACCOUNT") and not os.getenv("AZURE_STORAGE_ACCOUNT_NAME"):
        logger.warning(
            "AZURE_STORAGE_ACCOUNT is deprecated. "
            "Please use AZURE_STORAGE_ACCOUNT_NAME instead."
        )
    if os.getenv("AZURE_STORAGE_KEY") and not os.getenv("AZURE_STORAGE_ACCOUNT_KEY"):
        logger.warning(
            "AZURE_STORAGE_KEY is deprecated. "
            "Please use AZURE_STORAGE_ACCOUNT_KEY instead."
        )
    
    if not account_name or not account_key:
        raise MissingCredentialsError(
            "Azure storage credentials not found. "
            "Please set AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY "
            "environment variables (or AZURE_STORAGE_ACCOUNT and AZURE_STORAGE_KEY for backward compatibility)."
        )
    
    return {
        "account_name": account_name,
        "account_key": account_key
    }

def get_aws_credentials() -> Dict[str, str]:
    """Get AWS S3 credentials from environment variables"""
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    # Support both AWS_REGION (env.template) and AWS_DEFAULT_REGION (AWS standard)
    region = (
        os.getenv("AWS_REGION") or                  # New name (from env.template)
        os.getenv("AWS_DEFAULT_REGION") or          # Old name (AWS standard)
        "us-east-1"                                 # Default
    )
    
    # Log deprecation warning if using old name
    if os.getenv("AWS_DEFAULT_REGION") and not os.getenv("AWS_REGION"):
        logger.warning(
            "AWS_DEFAULT_REGION is deprecated. "
            "Please use AWS_REGION instead (AWS_DEFAULT_REGION is still supported for AWS CLI compatibility)."
        )
    
    if not access_key or not secret_key:
        raise MissingCredentialsError(
            "AWS credentials not found. "
            "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
        )
    
    return {
        "access_key": access_key,
        "secret_key": secret_key,
        "region": region
    }

def get_gcp_credentials() -> Dict[str, str]:
    """Get Google Cloud Storage credentials from environment variables"""
    # Support both old and new names
    project_id = (
        os.getenv("GOOGLE_CLOUD_PROJECT_ID") or     # New name (from env.template)
        os.getenv("GCP_PROJECT_ID")                 # Old name (backward compatibility)
    )
    credentials_json = os.getenv("GCP_CREDENTIALS_JSON")
    
    # Log deprecation warning if using old name
    if os.getenv("GCP_PROJECT_ID") and not os.getenv("GOOGLE_CLOUD_PROJECT_ID"):
        logger.warning(
            "GCP_PROJECT_ID is deprecated. "
            "Please use GOOGLE_CLOUD_PROJECT_ID instead."
        )
    
    if not project_id or not credentials_json:
        raise MissingCredentialsError(
            "GCP credentials not found. "
            "Please set GOOGLE_CLOUD_PROJECT_ID and GCP_CREDENTIALS_JSON "
            "environment variables (or GCP_PROJECT_ID for backward compatibility)."
        )
    
    return {
        "project_id": project_id,
        "credentials_json": credentials_json
    }

def create_storage_config(
    provider: str,
    bucket_name: Optional[str] = None,
    region: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    encryption: Optional[Dict[str, str]] = None
) -> StorageConfig:
    """Create storage configuration for a provider"""
    # ... existing code ...
    
    if provider == "azure_blob":
        # Support both old and new container name
        if not bucket_name:
            bucket_name = (
                os.getenv("AZURE_CONTAINER_NAME") or        # New name (from env.template)
                os.getenv("AZURE_STORAGE_CONTAINER")        # Old name (backward compatibility)
            )
        
        # Log deprecation warning
        if os.getenv("AZURE_STORAGE_CONTAINER") and not os.getenv("AZURE_CONTAINER_NAME"):
            logger.warning(
                "AZURE_STORAGE_CONTAINER is deprecated. "
                "Please use AZURE_CONTAINER_NAME instead."
            )
    
    elif provider == "gcp_storage":
        # Support both old and new bucket name
        if not bucket_name:
            bucket_name = (
                os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET") or # New name (from env.template)
                os.getenv("GCP_STORAGE_BUCKET")             # Old name (backward compatibility)
            )
        
        # Log deprecation warning
        if os.getenv("GCP_STORAGE_BUCKET") and not os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET"):
            logger.warning(
                "GCP_STORAGE_BUCKET is deprecated. "
                "Please use GOOGLE_CLOUD_STORAGE_BUCKET instead."
            )
    
    # ... rest of existing code ...
```

### 2. Update LLM Configuration

**File: `src/config/llm_config.py`**

**Update to support both old and new names:**

```python
def _load_from_environment(self):
    """Load configuration from environment variables"""
    # Global LLM settings
    if os.getenv("LLM_ENABLED"):
        self.config.enabled = os.getenv("LLM_ENABLED").lower() in ("true", "1", "t")
    
    # Support both LLM_PROVIDER (env.template) and LLM_DEFAULT_PROVIDER (backward compatibility)
    provider_env = (
        os.getenv("LLM_PROVIDER") or               # New name (from env.template)
        os.getenv("LLM_DEFAULT_PROVIDER")          # Old name (backward compatibility)
    )
    
    if provider_env:
        # Log deprecation warning if using old name
        if os.getenv("LLM_DEFAULT_PROVIDER") and not os.getenv("LLM_PROVIDER"):
            logger.warning(
                "LLM_DEFAULT_PROVIDER is deprecated. "
                "Please use LLM_PROVIDER instead."
            )
        
        try:
            self.config.default_provider = LLMProvider(provider_env)
        except ValueError:
            logger.warning(f"Invalid LLM provider: {provider_env}")
    
    # Support both LLM_MODEL (env.template) and LLM_DEFAULT_MODEL (backward compatibility)
    model_env = (
        os.getenv("LLM_MODEL") or                  # New name (from env.template)
        os.getenv("LLM_DEFAULT_MODEL")             # Old name (backward compatibility)
    )
    
    if model_env:
        # Log deprecation warning if using old name
        if os.getenv("LLM_DEFAULT_MODEL") and not os.getenv("LLM_MODEL"):
            logger.warning(
                "LLM_DEFAULT_MODEL is deprecated. "
                "Please use LLM_MODEL instead."
            )
        
        self.config.default_model = model_env
    
    # ... rest of existing code ...
```

### 3. Update env.template

**File: `env.template`**

**Add missing variables and update descriptions:**

```bash
# Open Matching Engine Configuration Template
# Copy this file to .env and customize the values for your environment

# =============================================================================
# API Configuration
# =============================================================================
# Enable debug mode (development only)
DEBUG=false

# API server host (0.0.0.0 for all interfaces, 127.0.0.1 for localhost only)
API_HOST=0.0.0.0

# API server port (default: 8001)
API_PORT=8001

# =============================================================================
# CORS Configuration
# =============================================================================
# Allowed CORS origins (comma-separated list, or "*" for all)
# In production, specify exact origins: "https://example.com,https://app.example.com"
CORS_ORIGINS=*

# =============================================================================
# API Authentication
# =============================================================================
# Comma-separated list of API keys for authentication
# In production, use strong, randomly generated keys
API_KEYS=your-api-key-here,another-api-key

# =============================================================================
# Logging Configuration
# =============================================================================
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Log file path (relative to project root)
LOG_FILE=logs/app.log

# =============================================================================
# Storage Configuration
# =============================================================================
# Storage provider: local, aws_s3, azure_blob, gcp_storage
STORAGE_PROVIDER=local

# Storage bucket/container name (provider-specific, optional for some providers)
STORAGE_BUCKET_NAME=ome-storage

# Local storage path (only for local provider, default: storage)
LOCAL_STORAGE_PATH=storage

# AWS S3 Configuration (if using aws_s3)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
# AWS region (also supports AWS_DEFAULT_REGION for AWS CLI compatibility)
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-s3-bucket

# Azure Blob Storage Configuration (if using azure_blob)
# Note: Old names (AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_KEY, AZURE_STORAGE_CONTAINER) 
# are still supported for backward compatibility but deprecated
AZURE_STORAGE_ACCOUNT_NAME=your-storage-account
AZURE_STORAGE_ACCOUNT_KEY=your-storage-key
AZURE_CONTAINER_NAME=your-container

# Google Cloud Storage Configuration (if using gcp_storage)
# Note: Old names (GCP_PROJECT_ID, GCP_STORAGE_BUCKET) are still supported 
# for backward compatibility but deprecated
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_CLOUD_STORAGE_BUCKET=your-gcs-bucket
# GCP service account credentials (JSON string)
GCP_CREDENTIALS_JSON=your-service-account-json

# =============================================================================
# LLM Configuration
# =============================================================================
# Enable/disable LLM integration
LLM_ENABLED=false

# Default LLM provider: openai, anthropic, google, azure, local
# Note: LLM_DEFAULT_PROVIDER is still supported for backward compatibility but deprecated
LLM_PROVIDER=anthropic

# Default LLM model
# Note: LLM_DEFAULT_MODEL is still supported for backward compatibility but deprecated
LLM_MODEL=claude-3-sonnet-20240229

# Quality level: hobby, professional, medical
LLM_QUALITY_LEVEL=professional

# Strict mode for validation
LLM_STRICT_MODE=false

# LLM Encryption (REQUIRED in production)
# Salt for encryption key derivation (must be set in production)
LLM_ENCRYPTION_SALT=

# Password for encryption key derivation (must be set in production)
LLM_ENCRYPTION_PASSWORD=

# Alternative: Direct encryption key (if not using salt/password)
# If set, LLM_ENCRYPTION_SALT and LLM_ENCRYPTION_PASSWORD are ignored
LLM_ENCRYPTION_KEY=

# OpenAI Configuration (if using openai)
OPENAI_API_KEY=your-openai-api-key
OPENAI_ORGANIZATION_ID=your-org-id  # Optional
OPENAI_API_BASE_URL=https://api.openai.com/v1  # Optional, for custom endpoints

# Anthropic Configuration (if using anthropic)
ANTHROPIC_API_KEY=your-anthropic-api-key
ANTHROPIC_API_BASE_URL=https://api.anthropic.com  # Optional

# Google AI Configuration (if using google)
GOOGLE_AI_API_KEY=your-google-ai-api-key
GOOGLE_AI_API_BASE_URL=https://generativelanguage.googleapis.com  # Optional

# Azure OpenAI Configuration (if using azure)
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Local/Ollama Configuration (if using local)
OLLAMA_BASE_URL=http://localhost:11434  # Ollama API base URL

# =============================================================================
# Domain Configuration
# =============================================================================
# Enable/disable specific domains
COOKING_DOMAIN_ENABLED=true
MANUFACTURING_DOMAIN_ENABLED=true

# =============================================================================
# Environment Configuration
# =============================================================================
# Environment: development, production
# Affects security defaults and validation
ENVIRONMENT=development

# =============================================================================
# CLI Configuration
# =============================================================================
# Default server URL for CLI (optional, defaults to http://localhost:8001)
OME_SERVER_URL=http://localhost:8001

# =============================================================================
# Development/Testing Configuration
# =============================================================================
# Set to true for development mode
DEV_MODE=false

# Test data directory
TEST_DATA_DIR=test-data

# =============================================================================
# Container-specific Configuration
# =============================================================================
# These are typically set by the container runtime
CONTAINER_NAME=open-matching-engine
```

### 4. Create Configuration Validation Utility

**File: `src/config/validation.py`**

**Add variable name validation:**

```python
def validate_environment_variables() -> Dict[str, Any]:
    """
    Validate environment variables and check for deprecated names.
    
    Returns:
        Dict with validation results and warnings
    """
    warnings = []
    errors = []
    
    # Check for deprecated variable names
    deprecated_vars = {
        "AZURE_STORAGE_ACCOUNT": "AZURE_STORAGE_ACCOUNT_NAME",
        "AZURE_STORAGE_KEY": "AZURE_STORAGE_ACCOUNT_KEY",
        "AZURE_STORAGE_CONTAINER": "AZURE_CONTAINER_NAME",
        "GCP_PROJECT_ID": "GOOGLE_CLOUD_PROJECT_ID",
        "GCP_STORAGE_BUCKET": "GOOGLE_CLOUD_STORAGE_BUCKET",
        "LLM_DEFAULT_PROVIDER": "LLM_PROVIDER",
        "LLM_DEFAULT_MODEL": "LLM_MODEL",
    }
    
    for old_name, new_name in deprecated_vars.items():
        if os.getenv(old_name) and not os.getenv(new_name):
            warnings.append({
                "variable": old_name,
                "message": f"{old_name} is deprecated. Please use {new_name} instead.",
                "replacement": new_name
            })
    
    # Check AWS region (support both)
    if os.getenv("AWS_DEFAULT_REGION") and not os.getenv("AWS_REGION"):
        warnings.append({
            "variable": "AWS_DEFAULT_REGION",
            "message": "AWS_DEFAULT_REGION is deprecated. Please use AWS_REGION instead (AWS_DEFAULT_REGION is still supported for AWS CLI compatibility).",
            "replacement": "AWS_REGION"
        })
    
    return {
        "valid": len(errors) == 0,
        "warnings": warnings,
        "errors": errors
    }
```

### 5. Update Configuration Documentation

**File: `docs/configuration/environment-variables.md` (new file)**

**Create comprehensive documentation:**

```markdown
# Environment Variables

This document describes all environment variables used by the Open Matching Engine.

## Variable Naming Conventions

- Use uppercase with underscores: `VARIABLE_NAME`
- Use descriptive names: `AZURE_STORAGE_ACCOUNT_NAME` not `AZURE_ACCOUNT`
- Group by category with prefixes: `LLM_*`, `AWS_*`, `AZURE_*`

## Deprecated Variables

The following variables are deprecated but still supported for backward compatibility:

- `AZURE_STORAGE_ACCOUNT` → Use `AZURE_STORAGE_ACCOUNT_NAME`
- `AZURE_STORAGE_KEY` → Use `AZURE_STORAGE_ACCOUNT_KEY`
- `AZURE_STORAGE_CONTAINER` → Use `AZURE_CONTAINER_NAME`
- `GCP_PROJECT_ID` → Use `GOOGLE_CLOUD_PROJECT_ID`
- `GCP_STORAGE_BUCKET` → Use `GOOGLE_CLOUD_STORAGE_BUCKET`
- `LLM_DEFAULT_PROVIDER` → Use `LLM_PROVIDER`
- `LLM_DEFAULT_MODEL` → Use `LLM_MODEL`
- `AWS_DEFAULT_REGION` → Use `AWS_REGION` (AWS_DEFAULT_REGION still supported for AWS CLI compatibility)

Deprecated variables will be removed in a future version. Please update your configuration.

## ... (full documentation for all variables)
```

## Integration Points

### 1. Configuration Loading

- Support both old and new names
- Log deprecation warnings
- Clear error messages

### 2. Documentation

- Comprehensive variable documentation
- Deprecation notices
- Migration guides

### 3. Validation

- Startup validation
- Deprecation warnings
- Clear error messages

## Testing Considerations

### Unit Tests

1. **Variable Name Support:**
   - Test old names work
   - Test new names work
   - Test deprecation warnings

2. **Backward Compatibility:**
   - Test both names work simultaneously
   - Test priority (new name over old)

### Integration Tests

1. **Configuration Loading:**
   - Test with old names
   - Test with new names
   - Test with both

2. **Error Handling:**
   - Test missing variables
   - Test invalid values
   - Test deprecation warnings

## Migration Plan

### Phase 1: Add Support for Both Names (Current)
- Update code to support both old and new names
- Add deprecation warnings
- Update env.template

### Phase 2: Documentation (Current)
- Document all variables
- Create migration guide
- Update examples

### Phase 3: Remove Old Names (Future)
- Remove support for deprecated names
- Update all documentation
- Major version bump

## Success Criteria

1. ✅ All variables in code match env.template
2. ✅ All variables used in code are documented
3. ✅ Backward compatibility maintained
4. ✅ Deprecation warnings logged
5. ✅ Clear migration path
6. ✅ Comprehensive documentation

## Open Questions / Future Enhancements

1. **Variable Validation:**
   - Validate variable values on startup?
   - Type checking?
   - Range validation?

2. **Configuration Schema:**
   - Use JSON schema for validation?
   - Generate documentation from schema?
   - Type-safe configuration?

3. **Configuration Management:**
   - Configuration file support?
   - Hierarchical configuration?
   - Environment-specific configs?

## Dependencies

### No New Dependencies

- Uses only existing code
- No external libraries required

## Implementation Order

1. Update storage configuration to support both names
2. Update LLM configuration to support both names
3. Add deprecation warnings
4. Update env.template with all variables
5. Create configuration validation utility
6. Update documentation
7. Write tests
8. Update examples

## Notes

### Backward Compatibility Strategy

**Support Both Names:**
- Check new name first
- Fall back to old name
- Log deprecation warning
- Clear error messages

**Migration Timeline:**
- Phase 1: Support both (current)
- Phase 2: Warn about old names (current)
- Phase 3: Remove old names (future major version)

### Naming Convention Rationale

**Why Update Code to Match env.template:**
- env.template is user-facing
- Users expect documented names to work
- Less disruptive than changing documentation
- Can support both during transition

**Why Simpler Names:**
- `LLM_PROVIDER` is clearer than `LLM_DEFAULT_PROVIDER`
- Matches user expectations
- Consistent with other configuration
- Code can use internal names

