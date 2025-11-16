# Authentication & Authorization Implementation Specification

## Overview

This specification defines the implementation plan for fixing critical authentication and authorization issues identified in the pre-publication code review. The current implementation has placeholder authentication logic that must be replaced with a production-ready system.

## Current State Analysis

### Issue 1: API Key Validation in `src/core/main.py:114`

**Current Implementation:**
```python
async def get_api_key(api_key: str = Depends(API_KEY_HEADER)):
    if not api_key.startswith("Bearer "):
        raise HTTPException(...)
    
    token = api_key.replace("Bearer ", "")
    
    # TODO: Implement actual API key validation against database
    if token not in settings.API_KEYS:
        raise HTTPException(...)
    
    return token
```

**Problems:**
- Simple list check from environment variable (`settings.API_KEYS`)
- No database persistence
- No key revocation capability
- No audit trail
- No key metadata (creation date, expiration, permissions, etc.)
- Keys stored in environment variable (not scalable)

### Issue 2: Authentication Decorator in `src/core/api/decorators.py:279`

**Current Implementation:**
```python
def require_authentication(required_permissions: List[str] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check authentication
            auth_header = request.headers.get("Authorization") if request else None
            if not auth_header:
                # Return 401 error
            
            # TODO: Implement actual authentication and permission checking
            # This is a placeholder for future implementation
            
            return await func(*args, **kwargs)
```

**Problems:**
- Only checks for presence of Authorization header
- No actual token validation
- No permission checking despite accepting `required_permissions` parameter
- Not integrated with `get_api_key` dependency

### Issue 3: Documentation Mismatch

**Documentation (`docs/api/auth.md:19`):**
- Shows `X-API-Key` header format

**Implementation (`src/core/main.py:49,105`):**
- Uses `Authorization: Bearer <token>` format

**Problem:**
- Documentation doesn't match implementation, causing user confusion

## Requirements

### Functional Requirements

1. **API Key Management**
   - Support multiple API keys per deployment
   - Store API keys in persistent storage (using existing StorageService)
   - Support key creation, validation, revocation, and expiration
   - Track key metadata (name, description, created_at, last_used_at, expires_at)
   - Support key permissions/roles for fine-grained access control

2. **Authentication**
   - Validate API keys from `Authorization: Bearer <token>` header
   - Support backward compatibility with environment variable keys during migration
   - Provide clear error messages for invalid/expired/revoked keys
   - Log authentication attempts (success and failure) for audit trail

3. **Authorization**
   - Support permission-based access control
   - Define permission model (read, write, admin, domain-specific permissions)
   - Check permissions in `require_authentication` decorator
   - Support public endpoints (no authentication required)

4. **Configuration**
   - Support environment variable keys for simple deployments (backward compatible)
   - Support storage-based keys for production deployments
   - Allow configuration of authentication mode (env-only, storage-only, hybrid)
   - Document all configuration options

### Non-Functional Requirements

1. **Performance**
   - Cache validated keys in memory to avoid storage lookups on every request
   - Implement cache invalidation on key revocation/update
   - Minimize latency impact on authenticated requests

2. **Security**
   - Never log API keys in plain text
   - Hash API keys in storage (use secure hashing algorithm)
   - Support key rotation without downtime
   - Rate limit authentication attempts to prevent brute force

3. **Reliability**
   - Graceful degradation if storage is unavailable (fallback to env keys)
   - Clear error messages for configuration issues
   - Support for key validation during application startup

4. **Maintainability**
   - Clear separation of concerns (authentication service, storage layer, decorators)
   - Comprehensive logging for debugging
   - Type hints and documentation

## Design Decisions

### Architecture

**Layered Approach:**
1. **Authentication Service Layer** (`src/core/services/auth_service.py`)
   - Core authentication logic
   - Key validation and permission checking
   - Cache management

2. **Storage Layer** (`src/core/storage/auth_storage.py`)
   - API key persistence using existing StorageService
   - Key CRUD operations
   - Storage abstraction for future database support

3. **Dependency Layer** (`src/core/api/dependencies.py`)
   - FastAPI dependencies for authentication
   - Integration with FastAPI's dependency injection

4. **Decorator Layer** (`src/core/api/decorators.py`)
   - Enhanced `require_authentication` decorator
   - Permission checking integration

### Storage Strategy

**Phase 1: StorageService-based (Incremental)**
- Use existing StorageService to store API keys as JSON files
- Storage path: `auth/api-keys/{key_id}.json`
- Allows migration from env variables without adding new dependencies
- Compatible with all existing storage providers (local, AWS, Azure, GCP)

**Future Phase: Database Support**
- Can add SQLite/PostgreSQL support later without changing service interface
- Storage abstraction allows seamless migration

### Key Format

**Storage Format:**
```json
{
  "key_id": "uuid-string",
  "key_hash": "bcrypt-hashed-token",
  "name": "User-friendly key name",
  "description": "Optional description",
  "permissions": ["read", "write", "admin"],
  "created_at": "2024-01-01T00:00:00Z",
  "last_used_at": "2024-01-15T12:00:00Z",
  "expires_at": "2025-01-01T00:00:00Z",  // null for no expiration
  "revoked": false,
  "created_by": "system"  // or user identifier
}
```

**Key Generation:**
- Generate secure random tokens (32+ bytes, base64 encoded)
- Store only hashed version in storage
- Return plain token only once during creation

### Permission Model

**Built-in Permissions:**
- `read`: Read-only access to all endpoints
- `write`: Read and write access (create, update, delete)
- `admin`: Full access including system management
- `domain:<domain_name>`: Domain-specific permissions (e.g., `domain:manufacturing`)

**Permission Hierarchy:**
- `admin` implies all permissions
- `write` implies `read`
- Domain permissions are additive

### Backward Compatibility

**Migration Strategy:**
1. Support environment variable keys during transition period
2. Allow hybrid mode (check env keys first, then storage)
3. Provide CLI command to migrate env keys to storage
4. Document migration path for users

## Implementation Specification

### 1. Data Models

**File: `src/core/models/auth.py`**

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class APIKey(BaseModel):
    """API Key model for storage"""
    key_id: UUID
    key_hash: str  # bcrypt hashed token
    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked: bool = False
    created_by: str = "system"

class APIKeyCreate(BaseModel):
    """Request model for creating API key"""
    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=lambda: ["read"])
    expires_at: Optional[datetime] = None

class APIKeyResponse(BaseModel):
    """Response model for API key (without hash)"""
    key_id: UUID
    name: str
    description: Optional[str] = None
    permissions: List[str]
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked: bool = False
    token: Optional[str] = None  # Only returned on creation

class AuthenticatedUser(BaseModel):
    """Model representing authenticated user/API key"""
    key_id: UUID
    name: str
    permissions: List[str]
```

### 2. Authentication Service

**File: `src/core/services/auth_service.py`**

**Class: `AuthenticationService`**

**Responsibilities:**
- Validate API keys
- Check permissions
- Manage key cache
- Coordinate with storage layer

**Methods:**

```python
class AuthenticationService:
    async def validate_api_key(self, token: str) -> AuthenticatedUser:
        """
        Validate an API key token and return authenticated user.
        
        Args:
            token: Plain text API key token
            
        Returns:
            AuthenticatedUser with key_id, name, and permissions
            
        Raises:
            HTTPException with 401 if invalid/expired/revoked
        """
        
    async def check_permission(
        self, 
        user: AuthenticatedUser, 
        required_permissions: List[str]
    ) -> bool:
        """
        Check if user has required permissions.
        
        Args:
            user: Authenticated user
            required_permissions: List of required permissions
            
        Returns:
            True if user has all required permissions
        """
        
    async def create_api_key(
        self, 
        key_data: APIKeyCreate
    ) -> APIKeyResponse:
        """
        Create a new API key.
        
        Args:
            key_data: Key creation data
            
        Returns:
            APIKeyResponse with generated token (only time it's returned)
        """
        
    async def revoke_api_key(self, key_id: UUID) -> None:
        """Revoke an API key."""
        
    async def list_api_keys(self) -> List[APIKeyResponse]:
        """List all API keys (without tokens)."""
        
    def _hash_token(self, token: str) -> str:
        """Hash a token using bcrypt."""
        
    def _verify_token(self, token: str, key_hash: str) -> bool:
        """Verify a token against its hash."""
        
    def _check_env_keys(self, token: str) -> Optional[AuthenticatedUser]:
        """Check environment variable keys (backward compatibility)."""
        
    async def _load_key_from_storage(self, key_id: UUID) -> Optional[APIKey]:
        """Load API key from storage."""
        
    def _get_key_id_from_token(self, token: str) -> Optional[UUID]:
        """Extract key_id from token (if token format includes it)."""
```

**Cache Strategy:**
- In-memory cache: `Dict[UUID, Tuple[APIKey, datetime]]` (key_id -> (key_data, cached_at))
- Cache TTL: 5 minutes
- Cache invalidation on key revocation/update
- Cache miss triggers storage lookup

### 3. Storage Layer

**File: `src/core/storage/auth_storage.py`**

**Class: `AuthStorage`**

**Responsibilities:**
- Persist API keys using StorageService
- Provide CRUD operations for keys
- Handle storage abstraction

**Methods:**

```python
class AuthStorage:
    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self._storage_prefix = "auth/api-keys"
    
    async def save_key(self, key: APIKey) -> None:
        """Save API key to storage."""
        
    async def load_key(self, key_id: UUID) -> Optional[APIKey]:
        """Load API key from storage."""
        
    async def list_keys(self) -> List[APIKey]:
        """List all API keys from storage."""
        
    async def delete_key(self, key_id: UUID) -> None:
        """Delete API key from storage."""
    
    def _get_storage_key(self, key_id: UUID) -> str:
        """Get storage path for key."""
        return f"{self._storage_prefix}/{key_id}.json"
```

**Storage Format:**
- JSON files in `auth/api-keys/` directory
- One file per key: `{key_id}.json`
- Uses existing StorageService interface

### 4. FastAPI Dependencies

**File: `src/core/api/dependencies.py` (new file)**

**Function: `get_current_user`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from src.core.services.auth_service import AuthenticationService
from src.core.models.auth import AuthenticatedUser

API_KEY_HEADER = APIKeyHeader(name="Authorization")

async def get_current_user(
    auth_header: str = Depends(API_KEY_HEADER)
) -> AuthenticatedUser:
    """
    FastAPI dependency for authentication.
    
    Validates Authorization: Bearer <token> header and returns authenticated user.
    
    Args:
        auth_header: Authorization header value
        
    Returns:
        AuthenticatedUser if valid
        
    Raises:
        HTTPException 401 if invalid
    """
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token format. Expected 'Bearer <token>'"
        )
    
    token = auth_header.replace("Bearer ", "").strip()
    
    auth_service = await AuthenticationService.get_instance()
    return await auth_service.validate_api_key(token)
```

**Function: `get_optional_user`**

```python
async def get_optional_user(
    auth_header: Optional[str] = Depends(OptionalAPIKeyHeader)
) -> Optional[AuthenticatedUser]:
    """
    Optional authentication dependency for public endpoints.
    
    Returns None if no auth header, otherwise validates and returns user.
    """
    if not auth_header:
        return None
    
    return await get_current_user(auth_header)
```

### 5. Enhanced Decorator

**File: `src/core/api/decorators.py`**

**Update: `require_authentication` decorator**

```python
def require_authentication(required_permissions: List[str] = None):
    """
    Decorator for requiring authentication and permissions.
    
    Args:
        required_permissions: List of required permissions. If None, only authentication required.
        
    Usage:
        @require_authentication()
        async def endpoint(user: AuthenticatedUser = Depends(get_current_user)):
            ...
            
        @require_authentication(required_permissions=["write"])
        async def write_endpoint(user: AuthenticatedUser = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract AuthenticatedUser from kwargs (injected by FastAPI dependency)
            user = None
            for key, value in kwargs.items():
                if isinstance(value, AuthenticatedUser):
                    user = value
                    break
            
            if not user:
                # If no user found, check if endpoint uses get_current_user dependency
                # This is a fallback - ideally endpoints should use Depends(get_current_user)
                error_response = create_error_response(
                    error="Authentication required",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    suggestion="This endpoint requires authentication. Use Depends(get_current_user) in your endpoint."
                )
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content=error_response.dict()
                )
            
            # Check permissions if required
            if required_permissions:
                auth_service = await AuthenticationService.get_instance()
                has_permission = await auth_service.check_permission(
                    user, 
                    required_permissions
                )
                
                if not has_permission:
                    error_response = create_error_response(
                        error="Insufficient permissions",
                        status_code=status.HTTP_403_FORBIDDEN,
                        suggestion=f"This endpoint requires the following permissions: {', '.join(required_permissions)}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content=error_response.dict()
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
```

**Note:** The decorator is primarily for documentation and permission checking. Actual authentication should be done via FastAPI dependencies (`Depends(get_current_user)`).

### 6. Update Main Application

**File: `src/core/main.py`**

**Changes:**

1. **Remove old `get_api_key` function** (lines 105-121)
2. **Import new dependency:**
   ```python
   from src.core.api.dependencies import get_current_user
   ```
3. **Update authentication dependency usage** in routes that need it

**Backward Compatibility:**
- Keep support for environment variable keys during migration
- AuthenticationService will check env keys if storage lookup fails

### 7. Configuration

**File: `src/config/settings.py`**

**Add new settings:**

```python
# Authentication Configuration
AUTH_MODE = os.getenv("AUTH_MODE", "hybrid")  # "env", "storage", "hybrid"
AUTH_ENABLE_STORAGE = os.getenv("AUTH_ENABLE_STORAGE", "true").lower() in ("true", "1", "t")
AUTH_CACHE_TTL = int(os.getenv("AUTH_CACHE_TTL", "300"))  # 5 minutes
AUTH_KEY_LENGTH = int(os.getenv("AUTH_KEY_LENGTH", "32"))  # bytes
```

**File: `env.template`**

**Add:**

```bash
# Authentication Configuration
# Mode: "env" (environment variables only), "storage" (storage only), "hybrid" (both)
AUTH_MODE=hybrid
AUTH_ENABLE_STORAGE=true
AUTH_CACHE_TTL=300
AUTH_KEY_LENGTH=32
```

### 8. Documentation Updates

**File: `docs/api/auth.md`**

**Update to match implementation:**

```markdown
## Authentication

The OME API uses Bearer token authentication via the `Authorization` header.

### Header Format

```
Authorization: Bearer <your-api-key>
```

### API Key Management

API keys can be managed through:
1. Environment variables (simple deployments)
2. Storage-based keys (production deployments)

### Getting an API Key

[Document how to create keys via CLI or API]
```

## Integration Points

### 1. StorageService Integration

- Use existing `StorageService.get_instance()` to access storage
- Store keys in `auth/api-keys/` path
- Compatible with all storage providers (local, AWS, Azure, GCP)

### 2. FastAPI Dependency Injection

- Use FastAPI's `Depends()` for authentication
- Integrate with existing route structure
- Support optional authentication for public endpoints

### 3. Error Handling

- Use existing `create_error_response()` from `error_handlers.py`
- Return standardized error responses
- Log authentication failures for audit

### 4. Logging

- Use existing logging infrastructure
- Log authentication attempts (success/failure)
- Never log API keys in plain text
- Include key_id in logs (not token)

## Testing Considerations

### Unit Tests

1. **AuthenticationService Tests:**
   - Token validation (valid, invalid, expired, revoked)
   - Permission checking
   - Cache behavior
   - Environment variable fallback

2. **AuthStorage Tests:**
   - CRUD operations
   - Storage provider compatibility

3. **Dependencies Tests:**
   - `get_current_user` dependency
   - Error handling

### Integration Tests

1. **End-to-end authentication:**
   - Create key → Use key → Revoke key → Verify rejection

2. **Permission enforcement:**
   - Test endpoints with different permission requirements

3. **Backward compatibility:**
   - Test environment variable keys still work

### Security Tests

1. **Token security:**
   - Verify tokens are hashed in storage
   - Verify tokens are never logged

2. **Rate limiting:**
   - Test brute force protection (if implemented)

## Migration Plan

### Phase 1: Implementation (Current)
- Implement AuthenticationService
- Implement AuthStorage
- Update dependencies and decorators
- Add configuration options

### Phase 2: Migration Support
- CLI command to migrate env keys to storage
- Hybrid mode support
- Documentation updates

### Phase 3: Deprecation (Future)
- Deprecate environment variable keys
- Require storage-based keys
- Remove env key support

## Success Criteria

1. ✅ API keys can be stored in persistent storage
2. ✅ Keys can be validated with proper error handling
3. ✅ Permission checking works correctly
4. ✅ Backward compatibility with env keys maintained
5. ✅ Documentation matches implementation
6. ✅ All authentication-related TODOs resolved
7. ✅ No security vulnerabilities introduced
8. ✅ Performance impact is minimal (<10ms overhead)

## Open Questions / Future Enhancements

1. **Key Rotation:**
   - Support for key rotation without downtime
   - Automatic expiration and renewal

2. **Rate Limiting:**
   - Per-key rate limiting
   - Brute force protection

3. **Audit Logging:**
   - Comprehensive audit trail
   - Integration with logging service

4. **OAuth2 Support:**
   - JWT token validation
   - OAuth2 provider integration

5. **Database Backend:**
   - SQLite for local deployments
   - PostgreSQL for production
   - Migration from storage-based to database

## Dependencies

### New Dependencies

- `bcrypt` - For secure password hashing (API key hashing)
- `secrets` - For secure random token generation (Python stdlib)

### Existing Dependencies

- `fastapi` - Already in use
- `pydantic` - Already in use
- `StorageService` - Already in use

## Implementation Order

1. Create data models (`src/core/models/auth.py`)
2. Implement storage layer (`src/core/storage/auth_storage.py`)
3. Implement authentication service (`src/core/services/auth_service.py`)
4. Create FastAPI dependencies (`src/core/api/dependencies.py`)
5. Update decorator (`src/core/api/decorators.py`)
6. Update main application (`src/core/main.py`)
7. Update configuration (`src/config/settings.py`, `env.template`)
8. Update documentation (`docs/api/auth.md`)
9. Write tests
10. Migration CLI command (optional, Phase 2)

