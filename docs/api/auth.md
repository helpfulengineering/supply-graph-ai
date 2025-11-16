# Authentication

The OME API uses Bearer token authentication via the `Authorization` header. This page describes how to authenticate with the API and manage API keys.

## Header Format

All authenticated requests must include the `Authorization` header with a Bearer token:

```
Authorization: Bearer <your-api-key>
```

## API Key Management

API keys can be managed through two methods:

1. **Environment Variables** (simple deployments, backward compatibility)
2. **Storage-based Keys** (production deployments, recommended)

### Environment Variable Keys

For simple deployments, API keys can be configured via environment variables:

```bash
API_KEYS=your-api-key-here,another-api-key
```

**Note:** Environment variable keys have full access (read, write, admin permissions) and cannot be revoked individually. For production deployments, use storage-based keys instead.

### Storage-based Keys

Storage-based API keys provide:
- Fine-grained permission control
- Key revocation capability
- Key expiration support
- Audit trail (last used timestamp)
- Key metadata (name, description)

Storage-based keys are stored in the configured storage backend (local filesystem, AWS S3, Azure Blob Storage, or Google Cloud Storage) and are managed through the authentication service.

## Getting an API Key

### Environment Variable Keys

Set the `API_KEYS` environment variable with comma-separated keys:

```bash
export API_KEYS="key1,key2,key3"
```

### Storage-based Keys

Storage-based keys can be created through:

1. **CLI Command** (when implemented):
   ```bash
   ome auth create-key --name "My API Key" --permissions read,write
   ```

2. **API Endpoint** (when implemented):
   ```bash
   POST /v1/api/auth/keys
   {
     "name": "My API Key",
     "description": "Key for my application",
     "permissions": ["read", "write"],
     "expires_at": "2025-12-31T23:59:59Z"
   }
   ```

**Important:** The API key token is only returned once during creation. Store it securely.

## Permissions

API keys support the following permission model:

### Built-in Permissions

- `read`: Read-only access to all endpoints
- `write`: Read and write access (create, update, delete operations)
- `admin`: Full access including system management

### Permission Hierarchy

- `admin` implies all permissions
- `write` implies `read`
- Domain permissions are additive (e.g., `domain:manufacturing`)

### Domain-specific Permissions

For domain-specific access control:

- `domain:<domain_name>`: Access to specific domain endpoints
  - Example: `domain:manufacturing` for manufacturing domain access
  - Example: `domain:cooking` for cooking domain access

## Configuration

### Authentication Mode

The authentication system supports three modes:

- `env`: Only environment variable keys are checked
- `storage`: Only storage-based keys are checked
- `hybrid`: Both environment variable and storage-based keys are checked (default)

Configure via environment variable:

```bash
AUTH_MODE=hybrid  # or "env" or "storage"
```

### Storage Configuration

Enable storage-based key management:

```bash
AUTH_ENABLE_STORAGE=true
```

### Cache Configuration

API key validation is cached for performance. Configure cache TTL:

```bash
AUTH_CACHE_TTL=300  # Cache time-to-live in seconds (default: 300 = 5 minutes)
```

### Key Generation

Configure the length of generated API keys:

```bash
AUTH_KEY_LENGTH=32  # Length in bytes (default: 32)
```

## Using Authentication in Endpoints

### Required Authentication

Use the `get_current_user` dependency for endpoints that require authentication:

```python
from fastapi import Depends
from src.core.api.dependencies import get_current_user
from src.core.models.auth import AuthenticatedUser

@app.get("/protected-endpoint")
async def protected_endpoint(user: AuthenticatedUser = Depends(get_current_user)):
    return {"message": f"Hello {user.name}!"}
```

### Optional Authentication

Use the `get_optional_user` dependency for endpoints that work with or without authentication:

```python
from fastapi import Depends
from src.core.api.dependencies import get_optional_user
from src.core.models.auth import AuthenticatedUser

@app.get("/public-endpoint")
async def public_endpoint(user: AuthenticatedUser | None = Depends(get_optional_user)):
    if user:
        return {"message": f"Hello authenticated user {user.name}!"}
    else:
        return {"message": "Hello anonymous user!"}
```

### Permission-based Access Control

Use the `require_authentication` decorator with permission requirements:

```python
from src.core.api.decorators import require_authentication
from src.core.api.dependencies import get_current_user
from src.core.models.auth import AuthenticatedUser

@require_authentication(required_permissions=["write"])
@app.post("/write-endpoint")
async def write_endpoint(user: AuthenticatedUser = Depends(get_current_user)):
    return {"message": "Write operation successful"}
```

## Error Responses

### 401 Unauthorized

Returned when:
- No authentication token is provided
- Invalid token format
- Token is invalid, expired, or revoked

Example response:

```json
{
  "success": false,
  "message": "Request failed: Invalid authentication token",
  "errors": [
    {
      "code": "UNAUTHORIZED",
      "message": "Invalid authentication token",
      "suggestion": "Please provide a valid authentication token."
    }
  ]
}
```

### 403 Forbidden

Returned when:
- User lacks required permissions

Example response:

```json
{
  "success": false,
  "message": "Request failed: Insufficient permissions",
  "errors": [
    {
      "code": "FORBIDDEN",
      "message": "Insufficient permissions",
      "suggestion": "This endpoint requires the following permissions: write, admin"
    }
  ]
}
```

## Security Best Practices

1. **Never log API keys**: API keys are never logged in plain text. Only key IDs are included in logs.

2. **Use storage-based keys for production**: Environment variable keys are convenient for development but lack fine-grained control.

3. **Rotate keys regularly**: Revoke and regenerate keys periodically.

4. **Use minimal permissions**: Grant only the permissions necessary for each application.

5. **Set expiration dates**: Configure expiration dates for keys to limit exposure.

6. **Monitor key usage**: Check `last_used_at` timestamps to identify unused or compromised keys.

## Migration from Environment Variables

To migrate from environment variable keys to storage-based keys:

1. Create storage-based keys with equivalent permissions
2. Update applications to use the new keys
3. Remove old keys from environment variables
4. Set `AUTH_MODE=storage` to disable environment variable keys

## Examples

### cURL

```bash
curl -H "Authorization: Bearer your-api-key-here" \
     http://localhost:8001/v1/api/okh
```

### Python (httpx)

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8001/v1/api/okh",
        headers={"Authorization": "Bearer your-api-key-here"}
    )
    print(response.json())
```

### Python (requests)

```python
import requests

headers = {
    "Authorization": "Bearer your-api-key-here"
}

response = requests.get(
    "http://localhost:8001/v1/api/okh",
    headers=headers
)
print(response.json())
```

### JavaScript (fetch)

```javascript
fetch('http://localhost:8001/v1/api/okh', {
  headers: {
    'Authorization': 'Bearer your-api-key-here'
  }
})
  .then(response => response.json())
  .then(data => console.log(data));
```

### Multiple API Keys

You can configure multiple API keys by providing a comma-separated list in the `API_KEYS` environment variable:

```bash
API_KEYS=key1,key2,key3
```

Any of these keys can be used for authentication. This is useful for:
- Supporting multiple applications
- Key rotation (create new key, update apps, remove old key)
- Different environments (development, staging, production)
