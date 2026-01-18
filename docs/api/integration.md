# Unified Integration Framework (UIF) API

The Unified Integration Framework (UIF) provides a centralized way to manage external integrations such as LLMs, VCS platforms (GitHub, GitLab), and other third-party services.

## Overview

The UIF is built around a singleton `IntegrationManager` that handles:
*   **Provider Registration**: Dynamic registration of integration providers.
*   **Configuration**: Unified configuration via `config/integration_config.json`.
*   **Observability**: Centralized status and health checks.

## Endpoints

### List Providers

Get a list of all registered integration providers and their status.

**Endpoint**: `GET /v1/api/integration/providers`

**Response**:

```json
{
  "status": "success",
  "data": [
    {
      "name": "github_default",
      "type": "github",
      "category": "vcs_platform",
      "connected": true,
      "status": "active"
    },
    {
      "name": "anthropic_claude",
      "type": "anthropic",
      "category": "ai_model",
      "connected": true,
      "status": "active"
    }
  ]
}
```

### Provider Status

Get detailed health status for all providers.

**Endpoint**: `GET /v1/api/integration/status`

**Response**:

```json
{
  "status": "success",
  "data": {
    "github_default": {
      "status": "healthy",
      "connected": true,
      "category": "vcs_platform"
    },
    "anthropic_claude": {
      "status": "healthy",
      "connected": true,
      "category": "ai_model"
    }
  }
}
```

## Configuration

Integrations are configured in `config/integration_config.json`.

Example:

```json
{
  "providers": {
    "github_default": {
      "provider_type": "github",
      "use_secrets": true,
      "secret_key_env": "GITHUB_TOKEN",
      "cache_ttl_hours": 24
    }
  }
}
```

## Adding New Integrations

To add a new integration type:
1.  Implement `BaseIntegrationProvider` in `src/core/integration/providers/`.
2.  Register the provider class in `IntegrationManager`.
3.  Add configuration in `integration_config.json`.
