# Authentication

The OME API supports authentication for secure deployments. This page describes the available authentication methods and how to implement them.

## Authentication Methods

### API Key Authentication

For simple deployments, API key authentication can be used.

#### Configuration

In your environment or configuration file:
OME_AUTH_ENABLED=true
OME_API_KEY=your-secure-api-key

#### Usage

Include the API key in the `X-API-Key` header:
X-API-Key: your-secure-api-key

### OAuth2 (Planned)

For more complex deployments, OAuth2 authentication will be supported.

#### Configuration

In your environment or configuration file:
OME_AUTH_ENABLED=true
OME_AUTH_TYPE=oauth2
OME_OAUTH_ISSUER=https://your-auth-server.com
OME_OAUTH_AUDIENCE=your-audience

#### Usage

Include a valid JWT token in the Authorization header:


## Implementing Authentication

### In FastAPI

Authentication is implemented using FastAPI's dependency injection system:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return api_key

@app.post("/secure-endpoint", dependencies=[Depends(get_api_key)])
def secure_endpoint():
    return {"message": "You're authenticated!"}
```