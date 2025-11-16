# Documentation-Code Discrepancies Implementation Specification

## Overview

This specification defines the implementation plan for resolving discrepancies between documentation and code. These discrepancies can cause confusion for users and should be aligned before public release.

## Current State Analysis

### Issue 1: Authentication Header Mismatch

**Location**: 
- **Documentation**: `docs/api/auth.md:19`
- **Implementation**: `src/core/main.py:49,105`

**Documentation:**
```markdown
Include the API key in the `X-API-Key` header:
X-API-Key: your-secure-api-key
```

**Implementation:**
```python
API_KEY_HEADER = APIKeyHeader(name="Authorization")

async def get_api_key(api_key: str = Depends(API_KEY_HEADER)):
    if not api_key.startswith("Bearer "):
        raise HTTPException(...)
    token = api_key.replace("Bearer ", "")
    ...
```

**Problems:**
- Documentation shows `X-API-Key` header
- Code uses `Authorization: Bearer` format
- Users following documentation will get authentication errors
- Inconsistent with common API key patterns

**Context:**
- FastAPI's `APIKeyHeader` with name="Authorization" expects `Authorization: <value>`
- Code expects `Authorization: Bearer <token>` format
- Documentation shows simpler `X-API-Key: <key>` format

**Severity**: High - Users will be confused, authentication will fail

### Issue 2: Port Number Inconsistencies

**Location**: Multiple documentation files

**Current State:**
- `src/config/settings.py:20`: Default port `8000`
- `src/core/main.py:222`: Hardcoded port `8000` in uvicorn.run
- `src/cli/base.py:33`: Default server URL `http://localhost:8001`
- `docker-compose.yml:7,10`: Port `8001`
- Documentation references: `8001`, `8081`, `8000`

**Problems:**
- Inconsistent default ports across codebase
- Documentation doesn't match actual defaults
- Confusing for users trying to connect

**Context:**
- API server defaults to port 8000
- CLI expects server on port 8001
- Docker compose uses port 8001
- Documentation shows various ports

**Severity**: Medium - Confusion for users

### Issue 3: Environment Variable Names

**Location**: `env.template` vs `src/config/`

**Current State:**
- Some variables documented in `env.template` but not used
- Some variables used in code but not documented
- Naming inconsistencies

**Problems:**
- Users may set variables that aren't used
- Users may not know about required variables
- Inconsistent naming conventions

**Context:**
- `env.template` is the primary documentation for environment variables
- Code uses `os.getenv()` with various variable names
- Some variables have defaults, some don't

**Severity**: Medium - Configuration confusion

## Requirements

### Functional Requirements

1. **Documentation Accuracy**
   - All documentation matches actual implementation
   - Examples work as documented
   - Clear instructions for users

2. **Consistency**
   - Consistent naming conventions
   - Consistent default values
   - Consistent examples

3. **Completeness**
   - All environment variables documented
   - All API endpoints documented
   - All configuration options documented

### Non-Functional Requirements

1. **Usability**
   - Clear, accurate documentation
   - Working examples
   - Easy to follow

2. **Maintainability**
   - Documentation stays in sync with code
   - Clear process for updating docs
   - Automated checks where possible

## Design Decisions

### Authentication Header Strategy

**Option 1: Update Documentation to Match Code (Recommended)**
- Pros: Code is already implemented, follows Bearer token standard
- Cons: Slightly more complex for users

**Option 2: Update Code to Match Documentation**
- Pros: Simpler for users
- Cons: Requires code changes, breaks existing clients

**Decision: Option 1 (Update Documentation)**
- Bearer token format is standard
- Code is already implemented
- Easier to maintain

### Port Standardization Strategy

**Standardize to Port 8001:**
- Matches CLI default
- Matches Docker compose
- Update API server default
- Update documentation

### Environment Variable Strategy

**Comprehensive Documentation:**
- Document all used variables
- Document all defaults
- Clear descriptions
- Group by category

## Implementation Specification

### 1. Fix Authentication Header Documentation

**File: `docs/api/auth.md`**

**Update to match implementation:**

```markdown
# Authentication

The OME API supports authentication for secure deployments. This page describes the available authentication methods and how to implement them.

## Authentication Methods

### API Key Authentication

For simple deployments, API key authentication can be used.

#### Configuration

In your environment or configuration file:
```bash
API_KEYS=your-secure-api-key,another-api-key
```

#### Usage

Include the API key in the `Authorization` header using the Bearer token format:

```
Authorization: Bearer your-secure-api-key
```

**Example using curl:**
```bash
curl -H "Authorization: Bearer your-secure-api-key" \
     http://localhost:8001/v1/api/okh
```

**Example using Python:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8001/v1/api/okh",
        headers={"Authorization": "Bearer your-secure-api-key"}
    )
```

**Example using JavaScript:**
```javascript
fetch('http://localhost:8001/v1/api/okh', {
  headers: {
    'Authorization': 'Bearer your-secure-api-key'
  }
})
```

#### Multiple API Keys

You can configure multiple API keys by providing a comma-separated list:

```bash
API_KEYS=key1,key2,key3
```

Any of these keys can be used for authentication.

#### Security Notes

- API keys should be kept secret and not committed to version control
- Use environment variables or secure secret management systems
- Rotate API keys regularly
- In production, consider implementing database-backed API key validation

### OAuth2 (Planned)

For more complex deployments, OAuth2 authentication will be supported in a future release.

#### Configuration

In your environment or configuration file:
```bash
OME_AUTH_ENABLED=true
OME_AUTH_TYPE=oauth2
OME_OAUTH_ISSUER=https://your-auth-server.com
OME_OAUTH_AUDIENCE=your-audience
```

#### Usage

Include a valid JWT token in the Authorization header:

```
Authorization: Bearer <jwt-token>
```

## Implementing Authentication

### In FastAPI

Authentication is implemented using FastAPI's dependency injection system:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="Authorization")

async def get_api_key(api_key: str = Depends(api_key_header)):
    if not api_key.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token format"
        )
    token = api_key.replace("Bearer ", "")
    if token not in settings.API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    return token

@app.post("/secure-endpoint", dependencies=[Depends(get_api_key)])
async def secure_endpoint():
    return {"message": "You're authenticated!"}
```

## Error Responses

### Authentication Errors

If authentication fails, the API returns a 401 Unauthorized status with the following response:

```json
{
  "detail": "Invalid authentication token"
}
```

Common authentication errors:
- **401 Unauthorized**: Invalid or missing API key
- **401 Unauthorized**: Invalid authentication token format (must be "Bearer <token>")
```

### 2. Standardize Port Numbers

**File: `src/config/settings.py`**

**Update default port:**

```python
# API settings
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
# Standardize to port 8001 (matches CLI and Docker)
API_PORT = int(os.getenv("API_PORT", "8001"))
```

**File: `src/core/main.py`**

**Update to use settings:**

```python
# Only run the app if this file is executed directly
if __name__ == "__main__":
    from src.config.settings import API_HOST, API_PORT, DEBUG
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=DEBUG)
```

**File: `docs/api/routes.md`**

**Update all port references to 8001:**

```markdown
# Update all examples to use port 8001
# Example:
curl http://localhost:8001/v1/api/okh
```

**File: `README.md`**

**Update port references:**

```markdown
# Update any port references to 8001
# Example:
The API server runs on port 8001 by default.
```

**File: `docs/development/*.md`**

**Update all port references to 8001**

### 3. Audit and Document Environment Variables

**File: `env.template`**

**Update with comprehensive documentation:**

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

# Storage bucket/container name (provider-specific)
STORAGE_BUCKET_NAME=ome-storage

# Local storage path (only for local provider)
LOCAL_STORAGE_PATH=storage

# AWS S3 Configuration (if using aws_s3)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=your-s3-bucket

# Azure Blob Storage Configuration (if using azure_blob)
AZURE_STORAGE_ACCOUNT=your-storage-account
AZURE_STORAGE_KEY=your-storage-key
AZURE_STORAGE_CONTAINER=your-container

# Google Cloud Storage Configuration (if using gcp_storage)
GCP_PROJECT_ID=your-project-id
GCP_STORAGE_BUCKET=your-gcs-bucket
GCP_CREDENTIALS_JSON=your-service-account-json

# =============================================================================
# LLM Configuration
# =============================================================================
# Enable/disable LLM integration
LLM_ENABLED=false

# Default LLM provider: openai, anthropic, google, azure, local
LLM_DEFAULT_PROVIDER=anthropic

# Default LLM model
LLM_DEFAULT_MODEL=claude-3-sonnet-20240229

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
```

### 4. Create Environment Variable Audit Script

**File: `scripts/audit_env_vars.py` (new file)**

```python
#!/usr/bin/env python3
"""
Audit environment variables used in code vs documented in env.template.

This script identifies:
- Variables used in code but not documented
- Variables documented but not used
- Naming inconsistencies
"""

import re
import os
from pathlib import Path
from typing import Set, Dict, List
from dataclasses import dataclass


@dataclass
class EnvVarUsage:
    """Represents environment variable usage."""
    name: str
    file: str
    line: int
    context: str


class EnvVarAuditor:
    """Audits environment variable usage."""
    
    def __init__(self, code_dir: Path, env_template: Path):
        self.code_dir = code_dir
        self.env_template = env_template
        self.used_vars: Dict[str, List[EnvVarUsage]] = {}
        self.documented_vars: Set[str] = set()
    
    def scan_code(self) -> Dict[str, List[EnvVarUsage]]:
        """Scan code for environment variable usage."""
        pattern = r'os\.getenv\(["\']([^"\']+)["\']'
        
        for py_file in self.code_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line_num, line in enumerate(lines, 1):
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        var_name = match.group(1)
                        if var_name not in self.used_vars:
                            self.used_vars[var_name] = []
                        self.used_vars[var_name].append(
                            EnvVarUsage(
                                name=var_name,
                                file=str(py_file.relative_to(self.code_dir.parent)),
                                line=line_num,
                                context=line.strip()
                            )
                        )
            except Exception as e:
                print(f"Error scanning {py_file}: {e}")
        
        return self.used_vars
    
    def scan_template(self) -> Set[str]:
        """Scan env.template for documented variables."""
        if not self.env_template.exists():
            return set()
        
        pattern = r'^([A-Z_][A-Z0-9_]*)='
        
        with open(self.env_template, 'r', encoding='utf-8') as f:
            for line in f:
                # Skip comments and empty lines
                if line.strip().startswith('#') or not line.strip():
                    continue
                match = re.match(pattern, line)
                if match:
                    self.documented_vars.add(match.group(1))
        
        return self.documented_vars
    
    def generate_report(self) -> str:
        """Generate audit report."""
        used_vars = set(self.used_vars.keys())
        documented_vars = self.documented_vars
        
        undocumented = used_vars - documented_vars
        unused_docs = documented_vars - used_vars
        
        report = "Environment Variable Audit Report\n"
        report += "=" * 60 + "\n\n"
        
        report += f"Total variables used in code: {len(used_vars)}\n"
        report += f"Total variables documented: {len(documented_vars)}\n\n"
        
        if undocumented:
            report += f"UNDOCUMENTED VARIABLES ({len(undocumented)}):\n"
            report += "-" * 60 + "\n"
            for var in sorted(undocumented):
                usages = self.used_vars[var]
                report += f"\n  {var}\n"
                for usage in usages[:3]:  # Show first 3 usages
                    report += f"    - {usage.file}:{usage.line}\n"
                if len(usages) > 3:
                    report += f"    ... and {len(usages) - 3} more\n"
            report += "\n"
        
        if unused_docs:
            report += f"DOCUMENTED BUT UNUSED ({len(unused_docs)}):\n"
            report += "-" * 60 + "\n"
            for var in sorted(unused_docs):
                report += f"  - {var}\n"
            report += "\n"
        
        if not undocumented and not unused_docs:
            report += "✓ All environment variables are properly documented!\n"
        
        return report


def main():
    """Run environment variable audit."""
    project_root = Path(__file__).parent.parent
    code_dir = project_root / "src"
    env_template = project_root / "env.template"
    
    auditor = EnvVarAuditor(code_dir, env_template)
    auditor.scan_code()
    auditor.scan_template()
    
    report = auditor.generate_report()
    print(report)
    
    # Exit with error if undocumented variables found
    used_vars = set(auditor.used_vars.keys())
    documented_vars = auditor.documented_vars
    undocumented = used_vars - documented_vars
    
    if undocumented:
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### 5. Update API Documentation

**File: `docs/api/routes.md`**

**Update authentication examples:**

```markdown
## Authentication

All API requests require authentication using the `Authorization` header with Bearer token format:

```
Authorization: Bearer your-api-key
```

**Example:**
```bash
curl -H "Authorization: Bearer your-api-key" \
     http://localhost:8001/v1/api/okh
```

# Update all port references to 8001 throughout the document
```

### 6. Create Documentation Validation Script

**File: `scripts/validate_docs.py` (new file)**

```python
#!/usr/bin/env python3
"""
Validate documentation against code implementation.

This script checks:
- Authentication header format in docs vs code
- Port numbers in docs vs code
- API endpoint documentation vs implementation
"""

import re
from pathlib import Path
from typing import List, Dict


class DocValidator:
    """Validates documentation against code."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.issues = []
    
    def check_auth_header(self):
        """Check authentication header documentation."""
        auth_doc = self.project_root / "docs" / "api" / "auth.md"
        main_code = self.project_root / "src" / "core" / "main.py"
        
        if not auth_doc.exists() or not main_code.exists():
            return
        
        # Check code
        with open(main_code, 'r') as f:
            code_content = f.read()
        
        code_uses_bearer = 'APIKeyHeader(name="Authorization")' in code_content
        code_checks_bearer = 'api_key.startswith("Bearer ")' in code_content
        
        # Check docs
        with open(auth_doc, 'r') as f:
            doc_content = f.read()
        
        doc_uses_x_api_key = 'X-API-Key' in doc_content
        doc_uses_bearer = 'Authorization: Bearer' in doc_content or 'Bearer' in doc_content
        
        if code_uses_bearer and code_checks_bearer:
            if doc_uses_x_api_key and not doc_uses_bearer:
                self.issues.append({
                    "type": "auth_header_mismatch",
                    "severity": "high",
                    "file": str(auth_doc.relative_to(self.project_root)),
                    "issue": "Documentation shows X-API-Key but code uses Authorization: Bearer",
                    "recommendation": "Update documentation to use Authorization: Bearer format"
                })
    
    def check_port_numbers(self):
        """Check port number consistency."""
        # Check code defaults
        settings_file = self.project_root / "src" / "config" / "settings.py"
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                content = f.read()
                port_match = re.search(r'API_PORT.*=.*int\(os\.getenv\(["\']API_PORT["\'],\s*["\'](\d+)["\']\)', content)
                if port_match:
                    default_port = port_match.group(1)
                    
                    # Check docs
                    docs_dir = self.project_root / "docs"
                    for doc_file in docs_dir.rglob("*.md"):
                        with open(doc_file, 'r') as f:
                            doc_content = f.read()
                            # Find port references
                            port_refs = re.findall(r'localhost:(\d+)', doc_content)
                            for port in port_refs:
                                if port != default_port:
                                    self.issues.append({
                                        "type": "port_mismatch",
                                        "severity": "medium",
                                        "file": str(doc_file.relative_to(self.project_root)),
                                        "issue": f"Documentation shows port {port} but default is {default_port}",
                                        "recommendation": f"Update to port {default_port}"
                                    })
    
    def generate_report(self) -> str:
        """Generate validation report."""
        if not self.issues:
            return "✓ Documentation validation passed!\n"
        
        report = "Documentation Validation Report\n"
        report += "=" * 60 + "\n\n"
        
        by_severity = {}
        for issue in self.issues:
            severity = issue["severity"]
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(issue)
        
        for severity in ["high", "medium", "low"]:
            if severity in by_severity:
                report += f"\n{severity.upper()} ({len(by_severity[severity])}):\n"
                report += "-" * 60 + "\n"
                for issue in by_severity[severity]:
                    report += f"\n  File: {issue['file']}\n"
                    report += f"  Type: {issue['type']}\n"
                    report += f"  Issue: {issue['issue']}\n"
                    report += f"  Recommendation: {issue['recommendation']}\n"
        
        return report


def main():
    """Run documentation validation."""
    project_root = Path(__file__).parent.parent
    validator = DocValidator(project_root)
    
    validator.check_auth_header()
    validator.check_port_numbers()
    
    report = validator.generate_report()
    print(report)
    
    # Exit with error if high severity issues found
    high_severity = [i for i in validator.issues if i["severity"] == "high"]
    if high_severity:
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

## Integration Points

### 1. Documentation Updates

- Authentication documentation matches implementation
- Port numbers standardized
- Examples use correct formats

### 2. Code Updates

- Port defaults standardized
- Consistent configuration

### 3. Validation Tools

- Automated documentation validation
- Environment variable auditing
- CI/CD integration

## Testing Considerations

### Manual Testing

1. **Authentication:**
   - Test with `Authorization: Bearer` format
   - Verify documentation examples work
   - Test error messages

2. **Port Configuration:**
   - Test default port 8001
   - Test environment variable override
   - Verify CLI connects correctly

3. **Environment Variables:**
   - Test all documented variables
   - Verify defaults work
   - Test variable combinations

### Automated Testing

1. **Documentation Validation:**
   - Run validation script
   - Check for mismatches
   - Verify examples

2. **Environment Variable Audit:**
   - Run audit script
   - Check for undocumented variables
   - Verify all documented variables are used

## Migration Plan

### Phase 1: Documentation Updates (Current)
- Update authentication documentation
- Standardize port references
- Update environment variable documentation

### Phase 2: Code Standardization (Current)
- Standardize port defaults
- Ensure consistency

### Phase 3: Validation Tools (Future)
- Create validation scripts
- Add to CI/CD
- Regular audits

## Success Criteria

1. ✅ Authentication documentation matches implementation
2. ✅ Port numbers standardized to 8001
3. ✅ All environment variables documented
4. ✅ All documentation examples work
5. ✅ No discrepancies between docs and code
6. ✅ Validation scripts created

## Open Questions / Future Enhancements

1. **Automated Documentation Generation:**
   - Generate API docs from code?
   - Use OpenAPI schema?
   - Keep manual docs?

2. **Documentation Testing:**
   - Test all code examples?
   - Automated example validation?
   - Integration tests for docs?

3. **Documentation Maintenance:**
   - How to keep docs in sync?
   - Review process?
   - Automated checks?

## Dependencies

### No New Dependencies

- Uses only standard library
- No external libraries required

## Implementation Order

1. Update authentication documentation
2. Standardize port numbers in code
3. Update port references in documentation
4. Audit and update environment variable documentation
5. Create validation scripts
6. Run validation and fix issues
7. Update all documentation examples

## Notes

### Authentication Header

**Why Bearer Token Format:**
- Standard HTTP authentication pattern
- Compatible with OAuth2 (future)
- More flexible than custom headers
- Better security practices

**Migration for Users:**
- Update API clients to use `Authorization: Bearer` format
- Old `X-API-Key` format will not work
- Clear migration instructions in documentation

### Port Standardization

**Why Port 8001:**
- Matches CLI default
- Matches Docker compose
- Less likely to conflict with other services
- Consistent across all components

### Environment Variables

**Documentation Strategy:**
- Group by category
- Clear descriptions
- Show defaults
- Indicate required vs optional
- Security warnings where appropriate

