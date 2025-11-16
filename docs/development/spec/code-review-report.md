# Pre-Publication Code Review Report

This document contains the comprehensive findings from the pre-publication code review of the Open Matching Engine (OME).

## Table of Contents
1. [TODO/FIXME/Placeholder Findings](#todofixmeplaceholder-findings)
2. [Hardcoded Values](#hardcoded-values)
3. [Documentation-Code Discrepancies](#documentation-code-discrepancies)
4. [Security Issues](#security-issues)
5. [Placeholder Implementations](#placeholder-implementations)
6. [Configuration Review](#configuration-review)

---

## TODO/FIXME/Placeholder Findings

### Critical TODOs (Blocking Release)

#### 1. Authentication & Authorization
- **File**: `src/core/main.py:114`
  - **Issue**: `# TODO: Implement actual API key validation against database`
  - **Context**: API key validation currently uses simple list check from environment variable
  - **Severity**: Critical - Security concern
  - **Recommendation**: Implement database-backed validation or document current limitation clearly

- **File**: `src/core/api/decorators.py:279`
  - **Issue**: `# TODO: Implement actual authentication and permission checking`
  - **Context**: `require_authentication` decorator is a placeholder
  - **Severity**: Critical - Security concern
  - **Recommendation**: Implement proper authentication/permission checking or remove decorator

#### 2. Metrics & Monitoring
- **File**: `src/core/main.py:23,92`
  - **Issue**: `# TODO: Implement MetricsTracker`
  - **Context**: MetricsTracker is commented out and not implemented
  - **Severity**: High - Missing functionality
  - **Recommendation**: Implement MetricsTracker or remove all references

- **File**: `src/core/api/middleware.py:15,26,128`
  - **Issue**: Multiple `# TODO: Implement MetricsTracker` comments
  - **Severity**: High - Missing functionality
  - **Recommendation**: Implement or remove references

- **File**: `src/core/api/decorators.py:26`
  - **Issue**: `# TODO: Implement MetricsTracker`
  - **Severity**: High - Missing functionality
  - **Recommendation**: Implement or remove references

#### 3. Core Functionality TODOs
- **File**: `src/core/api/routes/match.py:321`
  - **Issue**: `# TODO: Implement validation using matching service and new validation framework`
  - **Context**: Validation endpoint returns placeholder response
  - **Severity**: Critical - Incomplete feature
  - **Recommendation**: Implement proper validation or document as "coming soon"

- **File**: `src/core/api/routes/match.py:495`
  - **Issue**: `# TODO: Calculate actual processing time`
  - **Context**: Processing time hardcoded to 0.0
  - **Severity**: Medium - Missing metric
  - **Recommendation**: Implement actual timing calculation

- **File**: `src/core/services/matching_service.py:554`
  - **Issue**: `# TODO: Implement actual scoring logic`
  - **Severity**: High - Core functionality incomplete
  - **Recommendation**: Implement scoring logic

- **File**: `src/core/models/supply_trees.py:172`
  - **Issue**: `# TODO: add okw_reference: str`
  - **Severity**: Medium - Missing field
  - **Recommendation**: Add field or document why it's not needed

### High Priority TODOs

#### 4. Caching & Rate Limiting
- **File**: `src/core/api/decorators.py:311`
  - **Issue**: `# TODO: Implement actual caching logic`
  - **Severity**: High - Missing feature
  - **Recommendation**: Implement caching or remove decorator

- **File**: `src/core/api/decorators.py:344`
  - **Issue**: `# TODO: Implement actual rate limiting logic`
  - **Severity**: High - Security/Performance concern
  - **Recommendation**: Implement rate limiting or remove decorator

- **File**: `src/core/api/decorators.py:478`
  - **Issue**: `# TODO: Implement actual pagination logic`
  - **Severity**: Medium - Missing feature
  - **Recommendation**: Implement pagination or remove decorator

#### 5. File Processing
- **File**: `src/core/generation/utils/file_content_parser.py:97`
  - **Issue**: `# TODO: Implement PDF text extraction`
  - **Severity**: Medium - Missing feature
  - **Recommendation**: Implement or document limitation

- **File**: `src/core/generation/utils/file_content_parser.py:109`
  - **Issue**: `# TODO: Implement DOCX text extraction`
  - **Severity**: Medium - Missing feature
  - **Recommendation**: Implement or document limitation

#### 6. Version & Metadata
- **File**: `src/core/packaging/builder.py:703`
  - **Issue**: `# TODO: Get from actual version` (hardcoded "1.0.0")
  - **Severity**: Medium - Inaccurate metadata
  - **Recommendation**: Get version from package metadata

- **File**: `src/core/generation/services/repository_mapping_service.py:183`
  - **Issue**: `# TODO: Use proper timestamp` (hardcoded "now")
  - **Severity**: Low - Minor issue
  - **Recommendation**: Use proper datetime

#### 7. LLM & Provider Support
- **File**: `src/core/llm/service.py:128`
  - **Issue**: `# TODO: Add other providers as they're implemented`
  - **Severity**: Low - Future enhancement
  - **Recommendation**: Document current provider support

- **File**: `src/core/generation/services/file_categorization_service.py:180`
  - **Issue**: `# TODO: Implement proper LLM service status check`
  - **Severity**: Medium - Missing validation
  - **Recommendation**: Implement proper status check

#### 8. Domain-Specific TODOs
- **File**: `src/core/domains/manufacturing/okh_matcher.py:162`
  - **Issue**: `# TODO: Add more sophisticated substitution rules`
  - **Severity**: Low - Enhancement
  - **Recommendation**: Document current capabilities

- **File**: `src/core/generation/platforms/local_git.py:366`
  - **Issue**: `# TODO: Parse documentation files` (returns empty list)
  - **Severity**: Medium - Missing feature
  - **Recommendation**: Implement or document limitation

- **File**: `src/core/generation/bom_models.py:760`
  - **Issue**: `# TODO: Implement proper JSON/YAML parsing`
  - **Severity**: Medium - Missing feature
  - **Recommendation**: Implement or document limitation

#### 9. Registry & Type System
- **File**: `src/core/registry/domain_registry.py:47-48,96`
  - **Issue**: Multiple TODOs about refactoring to base classes
  - **Severity**: Medium - Technical debt
  - **Recommendation**: Refactor or document current structure

---

## Placeholder Implementations

### Critical Placeholders (Blocking Release)

#### 1. API Route Placeholders

**File**: `src/core/api/routes/okw.py:775`
- **Endpoint**: `POST /v1/api/okw/extract`
- **Issue**: Returns empty capabilities list
- **Code**: 
  ```python
  # Placeholder implementation
  return OKWExtractResponse(capabilities=[])
  ```
- **Severity**: Critical - Incomplete feature
- **Recommendation**: Implement extraction logic or return 501 Not Implemented

**File**: `src/core/api/routes/utility.py:75,173`
- **Endpoints**: Utility endpoints
- **Issue**: Placeholder implementations
- **Severity**: High - Incomplete features
- **Recommendation**: Implement or document as "coming soon"

**File**: `src/core/api/routes/supply_tree.py:223,288,358,414,464`
- **Endpoints**: 
  - `GET /v1/api/supply-tree/{id}` (line 223) - Returns 404
  - `GET /v1/api/supply-tree` (line 288) - Returns empty list
  - `PUT /v1/api/supply-tree/{id}` (line 358) - Returns 404
  - `DELETE /v1/api/supply-tree/{id}` (line 414) - Placeholder
  - `POST /v1/api/supply-tree/{id}/validate` (line 464) - Placeholder validation
- **Severity**: Critical - Core CRUD operations incomplete
- **Recommendation**: Implement full CRUD or document as "coming soon" with proper status codes

**File**: `src/core/api/routes/match.py:321-323,1102`
- **Endpoints**: 
  - `POST /v1/api/match/validate` (line 321) - Placeholder validation
  - ID generation (line 1102) - Placeholder ID
- **Severity**: Critical - Core functionality incomplete
- **Recommendation**: Implement proper validation and ID generation

#### 2. Service Placeholders

**File**: `src/core/storage/migration_service.py:323`
- **Issue**: Returns placeholder response
- **Severity**: Medium - Missing feature
- **Recommendation**: Implement or document limitation

**File**: `src/core/packaging/builder.py:702`
- **Issue**: OME version is placeholder
- **Severity**: Medium - Inaccurate metadata
- **Recommendation**: Get from package metadata

#### 3. Decorator Placeholders

**File**: `src/core/api/decorators.py:280,312,345,479`
- **Issues**: Multiple placeholder implementations in decorators
  - Authentication (line 280)
  - Caching (line 312)
  - Rate limiting (line 345)
  - Pagination (line 479)
- **Severity**: High - Missing functionality
- **Recommendation**: Implement or remove decorators

---

## Hardcoded Values

### Critical Hardcoded Values

#### 1. Azure Storage URL
- **File**: `README.md:156`
- **Value**: `https://projdatablobstorage.blob.core.windows.net`
- **Issue**: Organization-specific hardcoded URL
- **Severity**: Critical - Not portable
- **Recommendation**: Move to environment variable or configuration

#### 2. Default Encryption Credentials
- **File**: `src/config/llm_config.py:168-169`
- **Values**: 
  - `"default_salt"` (line 168)
  - `"default_password"` (line 169)
- **Issue**: Weak default credentials for encryption
- **Severity**: Critical - Security vulnerability
- **Recommendation**: Require explicit configuration or fail securely

#### 3. CORS Default Configuration
- **File**: `src/config/settings.py:24`
- **Value**: `CORS_ORIGINS = ["*"]` (default)
- **Issue**: Allows all origins by default
- **Severity**: Critical - Security concern
- **Recommendation**: Change default to empty list or document security implications

#### 4. API Keys Default
- **File**: `src/config/settings.py:33`
- **Value**: `API_KEYS = os.getenv("API_KEYS", "").split(",")`
- **Issue**: Defaults to empty list (no authentication)
- **Severity**: High - Security concern
- **Recommendation**: Require explicit configuration in production

### High Priority Hardcoded Values

#### 5. Default Ports and URLs
- **Files**: Multiple files reference `localhost:8001`, `localhost:8000`, `localhost:8081`
  - `docs/development/supply-graph-ai-integration.md:21,24` - Port mismatch (8081 vs 8001)
  - `docs/development/local-development-setup.md:233` - Port 8081 in config example
  - `src/core/main.py:222` - Port 8000 in uvicorn.run
  - `src/cli/base.py:33` - Port 8001 (correct default)
  - `docker-compose.yml:7,10,26` - Port 8001 (correct)
- **Issue**: Inconsistent port numbers in documentation and code
- **Severity**: Medium - Confusion for users
- **Recommendation**: Standardize to single default port (8001) and use environment variables

#### 6. Organization-Specific URLs
- **File**: `README.md:156,159,161`
  - `https://projdatablobstorage.blob.core.windows.net` - Hardcoded Azure storage URL
  - `https://github.com/helpfulengineering/library` - Organization-specific repo
  - `https://github.com/helpfulengineering/OKF-Schema` - Organization-specific repo
- **File**: `docs/development/local-development-setup.md:120`
  - `https://projectdatablobstorage.blob.core.windows.net` - Another hardcoded Azure URL (typo: projectdatablobstorage vs projdatablobstorage)
- **Issue**: Organization-specific URLs hardcoded in documentation
- **Severity**: Critical - Not portable, organization-specific
- **Recommendation**: Move to environment variables or configuration, use placeholders in docs

#### 6. Default Server URL
- **File**: `src/cli/base.py:33`
- **Value**: `self.server_url = "http://localhost:8001"`
- **Issue**: Hardcoded default
- **Severity**: Low - Acceptable default, but should be configurable
- **Recommendation**: Allow environment variable override

#### 7. Ollama Default URL
- **File**: `src/core/llm/providers/ollama.py:71`
- **Value**: `"http://localhost:11434"`
- **Issue**: Hardcoded default
- **Severity**: Low - Acceptable default
- **Recommendation**: Document as configurable via environment variable

#### 8. Version Hardcoding
- **File**: `src/core/packaging/builder.py:703`
- **Value**: `"1.0.0"`
- **Issue**: Hardcoded version
- **Severity**: Medium - Should come from package metadata
- **Recommendation**: Get from `__version__` or package metadata

---

## Security Issues

### Critical Security Issues

#### 1. Default Encryption Credentials
- **Location**: `src/config/llm_config.py:168-169`
- **Issue**: Uses "default_salt" and "default_password" if not configured
- **Risk**: Weak encryption if defaults are used
- **Recommendation**: Fail if encryption credentials not explicitly provided

#### 2. CORS Allows All Origins by Default
- **Location**: `src/config/settings.py:24-30`
- **Issue**: Defaults to `["*"]` allowing all origins
- **Risk**: CSRF attacks, unauthorized access
- **Recommendation**: Change default to empty list, require explicit configuration

#### 3. API Key Validation Not Database-Backed
- **Location**: `src/core/main.py:114-119`
- **Issue**: Simple list check from environment variable
- **Risk**: Cannot revoke keys, no audit trail
- **Recommendation**: Implement database-backed validation or document limitation

#### 4. Authentication Decorator Not Implemented
- **Location**: `src/core/api/decorators.py:279-280`
- **Issue**: `require_authentication` decorator is placeholder
- **Risk**: Routes may not be properly protected
- **Recommendation**: Implement proper authentication or remove decorator

#### 5. No Rate Limiting Implementation
- **Location**: `src/core/api/decorators.py:344`
- **Issue**: Rate limiting decorator is placeholder
- **Risk**: DoS vulnerability
- **Recommendation**: Implement rate limiting or document limitation

### High Priority Security Issues

#### 6. API Keys Default to Empty
- **Location**: `src/config/settings.py:33`
- **Issue**: No API keys required by default
- **Risk**: Unauthenticated access
- **Recommendation**: Require API keys in production mode

#### 7. Credential Logging Risk
- **Location**: Various files
- **Issue**: Need to verify credentials are not logged
- **Risk**: Credential exposure in logs
- **Recommendation**: Audit logging code for credential exposure

---

## Documentation-Code Discrepancies

### API Documentation Issues

#### 1. Authentication Header Mismatch
- **Documentation**: `docs/api/auth.md:19` shows `X-API-Key` header
- **Implementation**: `src/core/main.py:49,105` uses `Authorization: Bearer` format
- **Issue**: Documentation doesn't match implementation
- **Severity**: High - Users will be confused
- **Recommendation**: Update documentation to match implementation

#### 2. Port Number Inconsistencies
- **Documentation**: Multiple ports referenced (8001, 8081, 8000)
- **Implementation**: Default is 8001
- **Issue**: Confusing for users
- **Severity**: Medium
- **Recommendation**: Standardize documentation to use 8001

### Configuration Documentation

#### 3. Environment Variable Names
- **Documentation**: `env.template` uses various naming conventions
- **Implementation**: `src/config/settings.py` uses different names in some cases
- **Issue**: Need to verify all variables are documented
- **Severity**: Medium
- **Recommendation**: Audit and align all environment variables

---

## Configuration Review

### Environment Variables

#### Documented in env.template but need verification:
- `DEBUG` - Used in settings.py
- `API_HOST` - Used in settings.py
- `API_PORT` - Used in settings.py
- `CORS_ORIGINS` - Used in settings.py
- `API_KEYS` - Used in settings.py
- `LOG_LEVEL` - Used in settings.py
- `LOG_FILE` - Used in settings.py
- `STORAGE_PROVIDER` - Used in storage_config.py
- `STORAGE_BUCKET_NAME` - Used in storage_config.py
- AWS credentials - Used in storage_config.py
- Azure credentials - Used in storage_config.py
- GCP credentials - Used in storage_config.py
- LLM configuration variables - Used in llm_config.py

#### Potentially Undocumented:
- `LLM_ENCRYPTION_KEY` - Referenced in llm_config.py:157
- `LLM_ENCRYPTION_SALT` - Referenced in llm_config.py:168
- `LLM_ENCRYPTION_PASSWORD` - Referenced in llm_config.py:169
- `LOCAL_STORAGE_PATH` - Referenced in storage_config.py:110

---

## Summary by Severity

### Critical Issues (Must Fix Before Release)
1. Hardcoded Azure Storage URL in README
2. Default encryption credentials (default_salt/default_password)
3. CORS defaults to allow all origins
4. Placeholder API implementations (supply tree CRUD, validation endpoints)
5. Incomplete authentication implementation
6. Authentication header documentation mismatch

### High Priority Issues (Should Fix)
1. MetricsTracker not implemented (multiple references)
2. Rate limiting not implemented
3. Caching not implemented
4. API key validation not database-backed
5. Multiple placeholder decorators
6. Port number inconsistencies in documentation

### Medium Priority Issues (Nice to Have)
1. Processing time calculation missing
2. File format support (PDF, DOCX) missing
3. Version hardcoding
4. Various enhancement TODOs

---

## Recommendations

### Before Public Release

1. **Security Hardening**:
   - Remove default encryption credentials, require explicit configuration
   - Change CORS default to empty list
   - Document security implications of current authentication approach
   - Implement or remove placeholder security decorators

2. **Complete or Document Placeholders**:
   - Implement supply tree CRUD operations OR document as "coming soon" with proper 501 status codes
   - Implement validation endpoints OR document limitations
   - Remove or implement placeholder decorators

3. **Configuration Cleanup**:
   - Move hardcoded Azure URL to environment variable
   - Document all environment variables
   - Standardize port numbers in documentation

4. **Documentation Updates**:
   - Fix authentication header documentation
   - Standardize port references
   - Document placeholder implementations
   - Add security considerations section

5. **Code Cleanup**:
   - Remove or implement MetricsTracker
   - Get version from package metadata
   - Implement or remove placeholder decorators

## API Documentation Discrepancies

### Routes in Code but Not Fully Documented

1. **OKH Routes**:
   - `POST /v1/api/okh/generate-from-url` - Implemented but not in main routes documentation
   - `GET /v1/api/okh/export` - Implemented, documented
   - `POST /v1/api/okh/scaffold` - Implemented, documented
   - `POST /v1/api/okh/scaffold/cleanup` - Implemented, documented

2. **OKW Routes**:
   - `GET /v1/api/okw/export` - Implemented but not prominently documented
   - `POST /v1/api/okw/extract` - Implemented (placeholder), documented as `/extract-capabilities`

3. **Package Routes**:
   - `GET /v1/api/package/list` - Code uses `/list`, docs mention `/list-packages`
   - `GET /v1/api/package/{package_name}/{version}` - Implemented, documented
   - `GET /v1/api/package/{package_name}/{version}/verify` - Implemented, docs show `/verify` without path params
   - `GET /v1/api/package/{package_name}/{version}/download` - Implemented, documented
   - `DELETE /v1/api/package/{package_name}/{version}` - Implemented, docs show `/delete` without path params
   - `GET /v1/api/package/remote` - Implemented, docs mention `/list-remote`

4. **Supply Tree Routes**:
   - All CRUD routes are placeholders returning 404 or empty lists
   - `POST /v1/api/supply-tree/{id}/validate` - Implemented (placeholder), documented

5. **Match Routes**:
   - All routes appear to be documented

6. **Utility Routes**:
   - `GET /v1/api/utility/domains` - Implemented (placeholder), documented
   - `GET /v1/api/utility/contexts/{domain}` - Implemented (placeholder), documented

### Routes Documented but Not Found in Code

1. **LLM Routes** (mentioned in docs but no LLM routes file found):
   - `GET /v1/api/llm/health`
   - `POST /v1/api/llm/generate`
   - `POST /v1/api/llm/generate-okh`
   - `POST /v1/api/llm/match-facilities`
   - `GET /v1/api/llm/providers`
   - `GET /v1/api/llm/metrics`
   - `POST /v1/api/llm/provider`
   - **Issue**: LLM routes are documented but no corresponding route file exists
   - **Severity**: High - Documentation claims features that don't exist

2. **OKH Routes**:
   - `POST /v1/api/okh/from-storage` - Documented but not found in code

3. **Match Routes**:
   - `POST /v1/api/match/simulate` - Documented but not implemented

4. **Supply Tree Routes**:
   - `POST /v1/api/supply-tree/{id}/optimize` - Documented but not implemented
   - `GET /v1/api/supply-tree/{id}/export` - Documented but not implemented

### Path Parameter Discrepancies

1. **Package Routes**: Documentation shows simplified paths like `/verify` and `/delete`, but code uses `/{package_name}/{version}/verify` and `/{package_name}/{version}`
2. **OKW Extract**: Documentation shows `/extract-capabilities`, code has `/extract`

## CLI Documentation Review

### CLI Commands Summary

**Total Commands Found**: 53 commands across 7 groups

1. **OKH Group** (12 commands): validate, create, get, extract, list, delete, upload, generate-from-url, export, scaffold, scaffold-cleanup
2. **OKW Group** (9 commands): validate, create, get, list, delete, extract, upload, export, search
3. **Match Group** (3 commands): requirements, validate, domains
4. **Package Group** (8 commands): build, build-from-storage, list, get, verify, delete, download, push, pull, remote
5. **LLM Group** (13 commands): generate, generate-okh, analyze, providers (info, list, status, set, test), service (status, metrics, health, reset)
6. **System Group** (5 commands): health, info, domains, storage, logs
7. **Utility Group** (2 commands): domains, contexts

### CLI Documentation Accuracy

The CLI documentation appears comprehensive. All major command groups are documented. Need to verify:
- All command options match implementation
- All examples are accurate
- All command signatures match

## Configuration Review

### Environment Variables in Code vs env.template

#### Documented in env.template and Used in Code:
- `DEBUG` ✓
- `API_HOST` ✓
- `API_PORT` ✓
- `CORS_ORIGINS` ✓
- `API_KEYS` ✓
- `LOG_LEVEL` ✓
- `LOG_FILE` ✓
- `STORAGE_PROVIDER` ✓
- `STORAGE_BUCKET_NAME` ✓
- `AWS_ACCESS_KEY_ID` ✓
- `AWS_SECRET_ACCESS_KEY` ✓
- `AWS_REGION` (code uses `AWS_DEFAULT_REGION`) ⚠️
- `AWS_S3_BUCKET` ✓
- `AZURE_STORAGE_ACCOUNT_NAME` (code uses `AZURE_STORAGE_ACCOUNT`) ⚠️
- `AZURE_STORAGE_ACCOUNT_KEY` (code uses `AZURE_STORAGE_KEY`) ⚠️
- `AZURE_CONTAINER_NAME` (code uses `AZURE_STORAGE_CONTAINER`) ⚠️
- `GOOGLE_CLOUD_PROJECT_ID` (code uses `GCP_PROJECT_ID`) ⚠️
- `GOOGLE_CLOUD_STORAGE_BUCKET` (code uses `GCP_STORAGE_BUCKET`) ⚠️
- `LLM_ENABLED` ✓
- `LLM_PROVIDER` (code uses `LLM_DEFAULT_PROVIDER`) ⚠️
- `LLM_MODEL` (code uses `LLM_DEFAULT_MODEL`) ⚠️
- `LLM_QUALITY_LEVEL` ✓
- `LLM_STRICT_MODE` ✓
- Provider API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.) ✓

#### Used in Code but NOT in env.template:
- `LLM_ENCRYPTION_KEY` - Used in `llm_config.py:157`
- `LLM_ENCRYPTION_SALT` - Used in `llm_config.py:168` (has default)
- `LLM_ENCRYPTION_PASSWORD` - Used in `llm_config.py:169` (has default)
- `LOCAL_STORAGE_PATH` - Used in `storage_config.py:110` (has default)
- `AWS_DEFAULT_REGION` - Used in `storage_config.py:41` (env.template uses `AWS_REGION`)
- `AZURE_STORAGE_ACCOUNT` - Used in `storage_config.py:23` (env.template uses `AZURE_STORAGE_ACCOUNT_NAME`)
- `AZURE_STORAGE_KEY` - Used in `storage_config.py:24` (env.template uses `AZURE_STORAGE_ACCOUNT_KEY`)
- `AZURE_STORAGE_CONTAINER` - Used in `storage_config.py:99` (env.template uses `AZURE_CONTAINER_NAME`)
- `GCP_PROJECT_ID` - Used in `storage_config.py:57` (env.template uses `GOOGLE_CLOUD_PROJECT_ID`)
- `GCP_STORAGE_BUCKET` - Used in `storage_config.py:107` (env.template uses `GOOGLE_CLOUD_STORAGE_BUCKET`)
- `GCP_CREDENTIALS_JSON` - Used in `storage_config.py:58` (not in env.template)
- `LLM_DEFAULT_PROVIDER` - Used in `llm_config.py:293` (env.template uses `LLM_PROVIDER`)
- `LLM_DEFAULT_MODEL` - Used in `llm_config.py:299` (env.template uses `LLM_MODEL`)
- `OPENAI_ORGANIZATION_ID` - Used in `llm_config.py:322`
- Provider `_API_BASE_URL` variables - Used in `llm_config.py:314`

#### In env.template but NOT Used in Code:
- `COOKING_DOMAIN_ENABLED` - Not found in code
- `MANUFACTURING_DOMAIN_ENABLED` - Not found in code
- `DEV_MODE` - Not found in code
- `TEST_DATA_DIR` - Not found in code
- `ENV` - Not found in code
- `CONTAINER_NAME` - Not found in code

### Configuration Issues

1. **Variable Name Mismatches**: Multiple environment variables have different names in env.template vs. code
2. **Undocumented Variables**: Several variables used in code are not documented in env.template
3. **Unused Variables**: Some variables in env.template are not used in code

---

*Report generated as part of pre-publication code review*

