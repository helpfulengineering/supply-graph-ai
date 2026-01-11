# Demo Infrastructure Verification

This module provides tools for verifying Cloud Run deployment accessibility and API endpoint functionality for the demo workflow.

## Files

- `verification.py` - Core verification classes and functions
- `verify_deployment.py` - Command-line script for Cloud Run verification
- `verify_local_deployment.py` - Command-line script for local Docker verification
- `run_pre_demo_check.py` - Automated pre-demo validation script
- `configure_public_access.py` - Script to configure Cloud Run public access
- `BACKUP_DEPLOYMENT.md` - Backup deployment runbook
- `PUBLIC_ACCESS.md` - Public access configuration guide
- `PRE_DEMO_CHECKLIST.md` - Comprehensive pre-demo validation checklist
- `README.md` - This file

## Usage

### Command-Line Script

Run the health check script:

```bash
# Use default Cloud Run URL
python demo/infrastructure/verify_deployment.py

# Use custom URL
python demo/infrastructure/verify_deployment.py --url https://custom-url.com

# Output as JSON
python demo/infrastructure/verify_deployment.py --json
```

### Programmatic Usage

```python
from demo.infrastructure.verification import CloudRunVerifier, run_health_check

# Single endpoint check
verifier = CloudRunVerifier()
health_result = await verifier.check_health()

# Comprehensive check
results = await run_health_check()
```

## Test Suite

### Unit Tests
- Location: `tests/demo/test_infrastructure_verification.py`
- Purpose: Test verification logic with mocked HTTP responses
- Run: `pytest tests/demo/test_infrastructure_verification.py -v`

### Integration Tests
- Location: `tests/demo/test_infrastructure_verification_integration.py`
- Purpose: Test actual Cloud Run deployment with real HTTP requests
- Run: `pytest tests/demo/test_infrastructure_verification_integration.py -v`
- Note: Requires Cloud Run deployment to be accessible

### Local Deployment Tests
- Location: `tests/demo/test_local_deployment.py`
- Purpose: Test local Docker deployment (localhost:8001) with real HTTP requests
- Run: `pytest tests/demo/test_local_deployment.py -v`
- Note: Requires local Docker deployment to be running

## Current Status (December 2024)

### ✅ Endpoints Accessible
All required endpoints are accessible:
- Health endpoint: `/health` ✅
- Match endpoint: `/v1/api/match` ✅
- OKH endpoint: `/v1/api/okh` ✅
- OKW endpoint: `/v1/api/okw` ✅

### ⚠️ Authentication Required
Currently, all endpoints return `403 Forbidden` for unauthenticated requests. This is expected behavior until public access is configured for the demo.

**Next Step**: Configure public access for demo endpoints (Task 1.1.3)

## Configuration

### Environment Variables

- `CLOUD_RUN_URL` - Override default Cloud Run URL
- `SKIP_INTEGRATION_TESTS` - Set to "true" to skip integration tests

### Default Configuration

- **Default URL**: `https://supply-graph-ai-1085931013579.us-west1.run.app`
- **Region**: `us-west-1`
- **Timeout**: 10 seconds

## Requirements Verification

### Functional Requirements
- ✅ **FR-1.1.1**: Cloud Run deployment accessible
- ✅ **FR-1.1.2**: API endpoints respond within time limits
- ✅ **FR-1.1.3**: Health check endpoint available
- ⚠️ **FR-1.1.4**: Public access needs to be configured (Task 1.1.3)

### Non-Functional Requirements
- ✅ **NFR-1.1.1**: Network latency measurable
- ✅ **NFR-1.1.2**: API availability testable
- ✅ **NFR-1.1.3**: Concurrent request handling testable
- ✅ **NFR-1.1.4**: Error handling implemented

## Local Deployment Verification

### Quick Start

```bash
# Verify local deployment (localhost:8001)
python -m demo.infrastructure.verify_local_deployment

# Use custom URL
python -m demo.infrastructure.verify_local_deployment --url http://localhost:8080
```

### Current Status

- ✅ Health endpoint: `/health` (200 OK, <10ms)
- ✅ Match endpoint: `/v1/api/match` (200 OK, ~3s)
- ✅ OKH endpoint: `/v1/api/okh` (200 OK, ~250ms)
- ⚠️ OKW endpoint: Timeout (expected if no data loaded)

See `BACKUP_DEPLOYMENT.md` for detailed setup and troubleshooting.

## Pre-Demo Validation

### Automated Checks

Run the automated pre-demo validation script:

```bash
python -m demo.infrastructure.run_pre_demo_check
```

This script checks:
- Cloud Run accessibility and public access
- Network latency
- API endpoint health
- Match endpoint performance
- OKH/OKW data availability
- Local backup deployment readiness

### Manual Checklist

For comprehensive pre-demo validation, use the detailed checklist:

```bash
# Review the checklist
cat demo/infrastructure/PRE_DEMO_CHECKLIST.md
```

The checklist includes:
- Cloud Run deployment verification
- Demo data availability checks
- Backup deployment readiness
- Network connectivity testing
- Demo interface configuration
- Error handling verification
- Final pre-demo checks (30 minutes before)

**Timeline:**
- **24 hours before**: Complete all critical items
- **2 hours before**: Quick verification checks
- **30 minutes before**: Final spot checks

## Next Steps

1. ✅ **Task 1.1**: Cloud Run verification (Complete)
2. ✅ **Task 1.2**: Backup deployment setup (Complete, except data loading)
3. ✅ **Task 1.3**: Pre-demo checklist (Complete)
4. **Task 1.2.3**: Create demo data loading procedure for local deployment
5. **Task 2**: Synthetic data preparation
