# Security Issues Implementation Specification

## Overview

This specification defines the implementation plan for addressing security issues identified in the pre-publication review. While many specific security issues are addressed in other specifications (authentication, hardcoded values, etc.), this spec focuses on the credential logging risk audit and provides a comprehensive security validation framework.

## Current State Analysis

### Security Issues Already Addressed in Other Specs

The following security issues are covered in other specifications:

1. **Default Encryption Credentials** - Covered in `hardcoded-values-spec.md`
2. **CORS Default Configuration** - Covered in `hardcoded-values-spec.md`
3. **API Key Validation** - Covered in `authentication-authorization-spec.md`
4. **Authentication Decorator** - Covered in `authentication-authorization-spec.md`
5. **Rate Limiting** - Covered in `caching-rate-limiting-spec.md`
6. **API Keys Default** - Covered in `hardcoded-values-spec.md`

### Issue: Credential Logging Risk

**Location**: Various files throughout codebase

**Current State:**
- Need to audit all logging statements for credential exposure
- No systematic filtering of sensitive data in logs
- Risk of accidentally logging API keys, passwords, tokens, etc.

**Problems:**
- Credentials may be logged in error messages
- Request/response logging may include sensitive headers
- Debug logging may expose sensitive configuration
- No automatic filtering of sensitive data

**Context:**
- Logging is used extensively throughout the codebase
- Error handlers log exceptions which may contain sensitive data
- API request/response logging may include headers with credentials
- Configuration logging may expose secrets

**Severity**: High - Security risk if credentials are exposed in logs

## Requirements

### Functional Requirements

1. **Credential Logging Prevention**
   - Audit all logging statements for credential exposure
   - Implement automatic filtering of sensitive data
   - Create secure logging utilities
   - Document logging best practices

2. **Security Validation Framework**
   - Create security audit utilities
   - Implement credential detection in logs
   - Provide security validation tools
   - Document security best practices

3. **Error Handling Security**
   - Ensure error messages don't leak sensitive data
   - Filter credentials from exception messages
   - Sanitize error responses

### Non-Functional Requirements

1. **Security**
   - No credentials in logs
   - No sensitive data in error messages
   - Secure by default

2. **Maintainability**
   - Easy to add new sensitive field patterns
   - Clear documentation
   - Automated checks

## Design Decisions

### Credential Filtering Strategy

**Pattern-Based Filtering:**
- Identify common credential patterns (api_key, password, secret, token, etc.)
- Create filter function to sanitize log messages
- Apply filtering automatically in logging utilities

**Manual Audit:**
- Review all logging statements
- Check error handlers
- Verify request/response logging

### Logging Utility Enhancement

**Secure Logging Wrapper:**
- Create secure logging wrapper that filters sensitive data
- Apply filtering automatically
- Provide explicit methods for sensitive data logging

## Implementation Specification

### 1. Create Secure Logging Utility

**File: `src/core/utils/secure_logging.py` (new file)**

```python
"""
Secure logging utilities for OME.

This module provides secure logging functions that automatically filter
sensitive data such as API keys, passwords, tokens, and other credentials.
"""

import logging
import re
from typing import Any, Dict, Optional
from functools import wraps


# Patterns for sensitive data detection
SENSITIVE_PATTERNS = [
    # API keys and tokens
    r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    r'(?i)(token|bearer)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    r'(?i)(access[_-]?token|access_token)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    r'(?i)(refresh[_-]?token|refresh_token)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    
    # Passwords and secrets
    r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    r'(?i)(secret|secret[_-]?key)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    r'(?i)(private[_-]?key|privatekey)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    
    # Credentials
    r'(?i)(credential|credentials)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    r'(?i)(auth[_-]?token|authtoken)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    
    # AWS/Azure/GCP credentials
    r'(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    r'(?i)(azure[_-]?storage[_-]?account[_-]?key)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    r'(?i)(gcp[_-]?service[_-]?account[_-]?key)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    
    # Encryption keys
    r'(?i)(encryption[_-]?key|encryption_key)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
    r'(?i)(encryption[_-]?salt|encryption_salt)\s*[:=]\s*["\']?([^"\'\s,}]+)["\']?',
]

# Fields that should always be filtered
SENSITIVE_FIELDS = [
    'api_key', 'api-key', 'apikey', 'token', 'bearer', 'access_token',
    'refresh_token', 'password', 'passwd', 'pwd', 'secret', 'secret_key',
    'private_key', 'credential', 'credentials', 'auth_token', 'authtoken',
    'aws_access_key_id', 'aws_secret_access_key', 'azure_storage_account_key',
    'gcp_service_account_key', 'encryption_key', 'encryption_salt',
    'authorization', 'x-api-key', 'x-auth-token'
]

# Replacement string for sensitive data
SENSITIVE_REPLACEMENT = "[REDACTED]"


def sanitize_string(text: str) -> str:
    """
    Sanitize a string by replacing sensitive data patterns.
    
    Args:
        text: String to sanitize
        
    Returns:
        Sanitized string with sensitive data replaced
    """
    if not isinstance(text, str):
        return text
    
    sanitized = text
    
    # Replace patterns
    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, r'\1: [REDACTED]', sanitized)
    
    return sanitized


def sanitize_dict(data: Dict[str, Any], depth: int = 0, max_depth: int = 10) -> Dict[str, Any]:
    """
    Sanitize a dictionary by replacing sensitive field values.
    
    Args:
        data: Dictionary to sanitize
        depth: Current recursion depth
        max_depth: Maximum recursion depth
        
    Returns:
        Sanitized dictionary
    """
    if depth > max_depth:
        return data
    
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    
    for key, value in data.items():
        # Check if key is sensitive
        key_lower = key.lower()
        is_sensitive = any(
            sensitive_field.lower() in key_lower 
            for sensitive_field in SENSITIVE_FIELDS
        )
        
        if is_sensitive:
            # Replace sensitive value
            if isinstance(value, str) and value:
                # Show first 4 and last 4 characters if long enough
                if len(value) > 8:
                    sanitized[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    sanitized[key] = SENSITIVE_REPLACEMENT
            else:
                sanitized[key] = SENSITIVE_REPLACEMENT
        elif isinstance(value, dict):
            # Recursively sanitize nested dictionaries
            sanitized[key] = sanitize_dict(value, depth + 1, max_depth)
        elif isinstance(value, list):
            # Sanitize list items
            sanitized[key] = [
                sanitize_dict(item, depth + 1, max_depth) if isinstance(item, dict)
                else sanitize_string(item) if isinstance(item, str)
                else item
                for item in value
            ]
        elif isinstance(value, str):
            # Sanitize string values
            sanitized[key] = sanitize_string(value)
        else:
            sanitized[key] = value
    
    return sanitized


def sanitize_log_message(message: str, *args, **kwargs) -> tuple:
    """
    Sanitize log message and arguments.
    
    Args:
        message: Log message format string
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Tuple of (sanitized_message, sanitized_args, sanitized_kwargs)
    """
    # Sanitize message
    sanitized_message = sanitize_string(message)
    
    # Sanitize args
    sanitized_args = tuple(
        sanitize_dict(arg) if isinstance(arg, dict)
        else sanitize_string(arg) if isinstance(arg, str)
        else arg
        for arg in args
    )
    
    # Sanitize kwargs
    sanitized_kwargs = sanitize_dict(kwargs) if kwargs else {}
    
    return sanitized_message, sanitized_args, sanitized_kwargs


class SecureLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that automatically sanitizes sensitive data."""
    
    def process(self, msg, kwargs):
        """Process log message and sanitize sensitive data."""
        # Sanitize message
        sanitized_msg = sanitize_string(msg)
        
        # Sanitize extra data
        if 'extra' in kwargs and isinstance(kwargs['extra'], dict):
            kwargs['extra'] = sanitize_dict(kwargs['extra'])
        
        return sanitized_msg, kwargs


def get_secure_logger(name: str) -> logging.Logger:
    """
    Get a logger with automatic sensitive data filtering.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance with secure logging enabled
    """
    base_logger = logging.getLogger(name)
    return SecureLoggerAdapter(base_logger, {})


def secure_log_decorator(func):
    """
    Decorator to automatically sanitize function arguments and return values in logs.
    
    This decorator wraps a function and ensures that any logging within the function
    automatically filters sensitive data.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get logger for the function
        logger = get_secure_logger(func.__module__)
        
        # Log function call (sanitized)
        logger.debug(
            f"Calling {func.__name__}",
            extra={
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            }
        )
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            # Log error (sanitized)
            logger.error(
                f"Error in {func.__name__}: {str(e)}",
                exc_info=True,
                extra={
                    "function": func.__name__,
                    "error_type": type(e).__name__
                }
            )
            raise
    
    return wrapper
```

### 2. Update Error Handlers

**File: `src/core/api/error_handlers.py`**

**Update to use secure logging:**

```python
from ..utils.secure_logging import get_secure_logger, sanitize_dict

# Replace logger initialization
logger = get_secure_logger(__name__)

# Update error response creation to sanitize
def create_error_response(
    self,
    error: Union[Exception, str],
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    request_id: str = None,
    field: str = None,
    value: any = None,
    suggestion: str = None
) -> ErrorResponse:
    """Create a standardized error response."""
    # Sanitize error message
    if isinstance(error, str):
        error_message = sanitize_string(error)
    else:
        error_message = sanitize_string(str(error))
    
    # Sanitize value if provided
    if value is not None:
        if isinstance(value, dict):
            value = sanitize_dict(value)
        elif isinstance(value, str):
            value = sanitize_string(value)
    
    # ... rest of implementation
```

### 3. Update Request/Response Logging

**File: `src/core/api/middleware.py`**

**Update to sanitize headers:**

```python
from ..utils.secure_logging import sanitize_dict, get_secure_logger

# Use secure logger
logger = get_secure_logger(__name__)

# In request logging middleware
async def dispatch(self, request: Request, call_next):
    # ... existing code ...
    
    # Sanitize headers before logging
    headers_dict = dict(request.headers)
    sanitized_headers = sanitize_dict(headers_dict)
    
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "headers": sanitized_headers,  # Use sanitized headers
            "query_params": dict(request.query_params)
        }
    )
    
    # ... rest of implementation
```

### 4. Create Security Audit Utility

**File: `src/core/utils/security_audit.py` (new file)**

```python
"""
Security audit utilities for OME.

This module provides tools to audit the codebase for potential security issues,
including credential exposure in logs, insecure configurations, and other
security vulnerabilities.
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class SecurityFinding:
    """Represents a security finding."""
    file_path: str
    line_number: int
    severity: str  # "critical", "high", "medium", "low"
    issue_type: str
    description: str
    recommendation: str
    code_snippet: str


class SecurityAuditor:
    """Audits codebase for security issues."""
    
    SENSITIVE_PATTERNS = [
        (r'logger\.(info|debug|warning|error|critical)\([^)]*api[_-]?key', 'credential_logging'),
        (r'logger\.(info|debug|warning|error|critical)\([^)]*password', 'credential_logging'),
        (r'logger\.(info|debug|warning|error|critical)\([^)]*secret', 'credential_logging'),
        (r'logger\.(info|debug|warning|error|critical)\([^)]*token', 'credential_logging'),
        (r'print\([^)]*api[_-]?key', 'credential_print'),
        (r'print\([^)]*password', 'credential_print'),
        (r'print\([^)]*secret', 'credential_print'),
        (r'print\([^)]*token', 'credential_print'),
    ]
    
    def audit_file(self, file_path: Path) -> List[SecurityFinding]:
        """
        Audit a single file for security issues.
        
        Args:
            file_path: Path to file to audit
            
        Returns:
            List of security findings
        """
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                for pattern, issue_type in self.SENSITIVE_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        finding = SecurityFinding(
                            file_path=str(file_path),
                            line_number=line_num,
                            severity="high",
                            issue_type=issue_type,
                            description=f"Potential credential exposure in logging/print statement",
                            recommendation="Use secure logging utilities or sanitize sensitive data",
                            code_snippet=line.strip()
                        )
                        findings.append(finding)
        
        except Exception as e:
            # Skip files that can't be read
            pass
        
        return findings
    
    def audit_directory(self, directory: Path, extensions: List[str] = None) -> List[SecurityFinding]:
        """
        Audit a directory for security issues.
        
        Args:
            directory: Directory to audit
            extensions: File extensions to check (default: ['.py'])
            
        Returns:
            List of security findings
        """
        if extensions is None:
            extensions = ['.py']
        
        findings = []
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix in extensions:
                file_findings = self.audit_file(file_path)
                findings.extend(file_findings)
        
        return findings
    
    def generate_report(self, findings: List[SecurityFinding]) -> str:
        """
        Generate a security audit report.
        
        Args:
            findings: List of security findings
            
        Returns:
            Formatted report string
        """
        if not findings:
            return "No security issues found."
        
        report = f"Security Audit Report\n"
        report += f"{'=' * 50}\n\n"
        report += f"Total findings: {len(findings)}\n\n"
        
        # Group by severity
        by_severity = {}
        for finding in findings:
            if finding.severity not in by_severity:
                by_severity[finding.severity] = []
            by_severity[finding.severity].append(finding)
        
        for severity in ['critical', 'high', 'medium', 'low']:
            if severity in by_severity:
                report += f"\n{severity.upper()} ({len(by_severity[severity])}):\n"
                report += f"{'-' * 50}\n"
                for finding in by_severity[severity]:
                    report += f"\n  File: {finding.file_path}:{finding.line_number}\n"
                    report += f"  Type: {finding.issue_type}\n"
                    report += f"  Description: {finding.description}\n"
                    report += f"  Recommendation: {finding.recommendation}\n"
                    report += f"  Code: {finding.code_snippet}\n"
        
        return report
```

### 5. Update Logging Configuration

**File: `src/core/utils/logging.py`**

**Update to use secure logging by default:**

```python
from .secure_logging import get_secure_logger, sanitize_dict

# Update get_logger to use secure logger
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with secure logging enabled.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance with automatic sensitive data filtering
    """
    return get_secure_logger(name)
```

### 6. Create Security Audit Script

**File: `scripts/security_audit.py` (new file)**

```python
#!/usr/bin/env python3
"""
Security audit script for OME codebase.

This script audits the codebase for potential security issues,
including credential exposure in logs, insecure configurations, etc.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.utils.security_audit import SecurityAuditor

def main():
    """Run security audit."""
    auditor = SecurityAuditor()
    
    # Audit src directory
    src_dir = Path(__file__).parent.parent / "src"
    findings = auditor.audit_directory(src_dir)
    
    # Generate report
    report = auditor.generate_report(findings)
    print(report)
    
    # Exit with error code if critical or high severity findings
    critical_high = [f for f in findings if f.severity in ['critical', 'high']]
    if critical_high:
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
```

## Integration Points

### 1. Logging System

- All loggers use secure logging by default
- Automatic filtering of sensitive data
- Consistent across all modules

### 2. Error Handling

- Error messages sanitized
- Exception details filtered
- No credential leakage

### 3. Request/Response Logging

- Headers sanitized
- Query parameters checked
- Body content filtered

## Testing Considerations

### Unit Tests

1. **Sanitization Tests:**
   - Test pattern matching
   - Test dictionary sanitization
   - Test string sanitization
   - Test nested structures

2. **Logging Tests:**
   - Test secure logger
   - Test automatic filtering
   - Test log adapter

### Integration Tests

1. **End-to-End Security:**
   - Test actual logging with credentials
   - Verify credentials are filtered
   - Test error handling

2. **Audit Tests:**
   - Test security auditor
   - Test report generation
   - Test finding detection

## Migration Plan

### Phase 1: Implementation (Current)
- Create secure logging utilities
- Update error handlers
- Update request/response logging
- Create security audit utility

### Phase 2: Audit (Future)
- Run security audit on codebase
- Fix identified issues
- Add to CI/CD pipeline

## Success Criteria

1. ✅ Secure logging utilities created
2. ✅ All logging uses secure utilities
3. ✅ Credentials filtered from logs
4. ✅ Error messages sanitized
5. ✅ Security audit utility created
6. ✅ No credentials in logs verified
7. ✅ Documentation updated

## Open Questions / Future Enhancements

1. **Audit Automation:**
   - Should we add to CI/CD?
   - Pre-commit hooks?
   - Regular scheduled audits?

2. **Pattern Updates:**
   - How to add new sensitive patterns?
   - Configuration file?
   - Plugin system?

3. **Performance:**
   - Impact of sanitization on performance?
   - Caching strategies?
   - Lazy evaluation?

## Dependencies

### No New Dependencies

- Uses only standard library
- No external libraries required

## Implementation Order

1. Create secure logging utilities
2. Create security audit utility
3. Update error handlers
4. Update request/response logging
5. Update logging configuration
6. Create audit script
7. Run security audit
8. Fix identified issues
9. Update documentation

## Notes

### Security Best Practices

**Logging:**
- Never log credentials directly
- Use secure logging utilities
- Sanitize all user input in logs
- Filter sensitive headers

**Error Handling:**
- Don't expose sensitive data in error messages
- Sanitize exception details
- Use generic error messages for users
- Log detailed errors securely

**Configuration:**
- Don't log configuration with secrets
- Use secure storage for credentials
- Validate configuration on startup
- Fail securely if misconfigured

