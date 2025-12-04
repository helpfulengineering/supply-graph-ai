# End-to-End Integration Tests

This directory contains comprehensive end-to-end tests for validating deployed Cloud Run services.

## Overview

The E2E test suite validates:
- Health and system endpoints
- Authentication and authorization
- Utility and metadata endpoints
- Read operations (list, search, get)
- Create operations (OKH, OKW)
- Match operations
- Error handling
- Metrics endpoints

## Prerequisites

- Python 3.11+
- `pytest` and `requests` packages
- Access to a deployed service URL
- Authentication credentials (API key or GCP identity token)

## Running Tests

### Local Execution

**Important**: The Cloud Run service requires authentication. You need to provide either:
- A GCP identity token (recommended for GCP Cloud Run)
- An API key (if configured)

```bash
# Set the service URL
export SERVICE_URL=https://supply-graph-ai-1085931013579.us-west1.run.app

# Option 1: Use GCP identity token (automatic if gcloud is configured)
# The tests will automatically try to get a token using 'gcloud auth print-identity-token'
# Just make sure you're authenticated: gcloud auth login
export USE_AUTH=true

# Option 2: Manually provide identity token
export IDENTITY_TOKEN=$(gcloud auth print-identity-token)
export USE_AUTH=true

# Option 3: Use API key (if your service supports it)
export API_KEY=your-api-key
export USE_AUTH=true

# Option 4: Disable authentication (only if service allows unauthenticated access)
export USE_AUTH=false

# Install dependencies
pip install pytest requests

# Run all tests
pytest tests/integration/test_cloud_run_e2e.py -v

# Run specific test class
pytest tests/integration/test_cloud_run_e2e.py::TestHealthEndpoints -v

# Run with detailed output
pytest tests/integration/test_cloud_run_e2e.py -v -s
```

### Using Shell Script

```bash
# Set environment variables
export SERVICE_URL=https://supply-graph-ai-1085931013579.us-west1.run.app
export API_KEY=your-api-key  # Optional
export IDENTITY_TOKEN=your-gcp-token  # Optional
export USE_AUTH=true

# Run the shell script
./scripts/test-cloud-run-e2e.sh
```

### GCP Cloud Run Authentication

For GCP Cloud Run services with `--no-allow-unauthenticated`, use identity tokens:

```bash
# Get identity token
IDENTITY_TOKEN=$(gcloud auth print-identity-token)

# Run tests
export SERVICE_URL=https://your-service.run.app
export IDENTITY_TOKEN="${IDENTITY_TOKEN}"
export USE_AUTH=true

pytest tests/integration/test_cloud_run_e2e.py -v
```

## Test Structure

### Test Classes

- **TestHealthEndpoints**: Basic health checks and system endpoints
- **TestAuthentication**: Authentication and authorization validation
- **TestUtilityEndpoints**: Utility and metadata endpoints
- **TestReadOperations**: List, search, and get operations
- **TestCreateOperations**: Create OKH and OKW resources
- **TestMatchOperations**: Matching OKH to OKW facilities
- **TestErrorHandling**: Error response validation
- **TestMetricsEndpoints**: Metrics endpoint validation

### Test Data

Tests create temporary resources (OKH manifests, OKW facilities) and automatically clean them up after all tests complete.

## CI/CD Integration

The E2E tests are automatically run in the CI/CD pipeline after successful deployment. See `.github/workflows/ci-cd.yml` for details.

## Troubleshooting

### Authentication Failures

If tests fail with 401 errors:
- Verify `IDENTITY_TOKEN` or `API_KEY` is set correctly
- Check that the service allows authenticated requests
- For GCP, ensure `gcloud auth print-identity-token` works

### Connection Errors

If tests fail to connect:
- Verify `SERVICE_URL` is correct
- Check network connectivity
- Ensure the service is deployed and running

### Test Failures

If specific tests fail:
- Check the service logs for errors
- Verify the service has required dependencies (storage, secrets)
- Ensure test data can be created (storage permissions)

## Adding New Tests

To add new E2E tests:

1. Add a new test method to the appropriate test class
2. Use the `base_url` and `auth_headers` fixtures
3. Follow the existing test patterns
4. Add cleanup if creating resources

Example:

```python
def test_new_endpoint(self, base_url, auth_headers):
    """Test description"""
    response = requests.get(
        f"{base_url}/v1/api/new-endpoint",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

