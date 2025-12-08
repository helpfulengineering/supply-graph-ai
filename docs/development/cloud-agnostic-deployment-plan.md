# Cloud-Agnostic Deployment Plan

## Overview

This document outlines the plan to make the supply-graph-ai system cloud-agnostic, allowing deployment to any cloud provider (GCP, AWS, Azure) or container hosting service (Digital Ocean, Heroku, etc.).

## Current State Analysis

### Already Abstracted ✅

1. **Storage Providers**: Already have abstraction layer
   - `src/core/storage/providers/` - GCP, AWS, Azure, Local
   - `StorageProvider` base class with unified interface

2. **Secrets Management**: Already have abstraction layer
   - `src/core/utils/secrets_manager.py` - Supports AWS, GCP, Azure, ENV
   - `SecretsProvider` enum with auto-detection

### GCP-Specific Components ❌

1. **Deployment Scripts**
   - `deploy/prometheus/deploy.sh` - Uses `gcloud` commands
   - CI/CD workflow (`.github/workflows/ci-cd.yml`) - GCP-specific

2. **Documentation**
   - `docs/development/gcp-cloud-run-setup.md` - GCP-specific setup
   - `docs/development/prometheus-cloud-run-setup.md` - GCP-specific

3. **Configuration**
   - Environment variables hardcoded for GCP
   - Service account setup scripts

4. **Monitoring/Logging**
   - Cloud Logging integration (GCP-specific)
   - Prometheus deployment script (GCP-specific)

## Task 1: Comprehensive End-to-End Testing ✅ COMPLETED

### Status: ✅ Complete
**Completed Date**: December 2024

### Goals ✅
- ✅ Test all major API endpoints on deployed Cloud Run service
- ✅ Verify authentication works correctly
- ✅ Test actual functionality (not just health checks)
- ✅ Create reusable test suite for any deployment

### Test Categories

#### 1.1 Health & System Endpoints ✅
- [x] `GET /health` - Basic health check
- [x] `GET /health/readiness` - Readiness check
- [x] `GET /` - API information
- [x] `GET /v1` - API version info

#### 1.2 Authentication Tests ✅
- [x] Test with valid API key
- [x] Test with invalid API key (401)
- [x] Test without authentication (401/403)
- [ ] Test role-based access (read/write/admin) - *Not yet implemented in API*

#### 1.3 Core API Endpoints

**OKH Routes:**
- [x] `POST /v1/api/okh/create` - Create OKH manifest (with resilience for 500 errors)
- [x] `GET /v1/api/okh/{id}` - Retrieve OKH
- [x] `GET /v1/api/okh` - List OKH manifests
- [ ] `PUT /v1/api/okh/{id}` - Update OKH - *Not tested yet*
- [ ] `DELETE /v1/api/okh/{id}` - Delete OKH - *Not tested yet*

**OKW Routes:**
- [x] `POST /v1/api/okw/create` - Create OKW facility (with resilience for 500 errors)
- [x] `GET /v1/api/okw/{id}` - Retrieve OKW
- [x] `GET /v1/api/okw` - List/search OKW facilities
- [ ] `PUT /v1/api/okw/{id}` - Update OKW - *Not tested yet*
- [ ] `DELETE /v1/api/okw/{id}` - Delete OKW - *Not tested yet*

**Match Routes:**
- [x] `POST /v1/api/match` - Match OKH to OKW (✅ **Fully functional with 94% success rate**)
- [x] `GET /v1/api/match/domains` - List domains
- [ ] `POST /v1/api/match/validate` - Validate matching - *Not tested yet*

**Supply Tree Routes:**
- [x] `GET /v1/api/supply-tree` - List supply trees
- [ ] `POST /v1/api/supply-tree/create` - Create supply tree - *Not tested yet*
- [ ] `GET /v1/api/supply-tree/{id}` - Retrieve supply tree - *Not tested yet*

**Utility Routes:**
- [x] `GET /v1/api/utility/domains` - List domains
- [x] `GET /v1/api/utility/contexts?domain=manufacturing` - Get contexts
- [x] `GET /v1/api/okh/export` - Get OKH schema
- [x] `GET /v1/api/okw/export` - Get OKW schema

#### 1.4 Error Handling Tests ✅
- [x] 404 for non-existent resources
- [x] 422 for validation errors
- [x] 500/503 error handling (with resilience and proper logging)

#### 1.5 Integration Tests ✅
- [x] Storage operations (read, list) - Verified GCS integration working
- [x] Verify data persistence across requests - Confirmed 60+ OKH files accessible
- [x] Matching operations with real data - Successfully matched 33 OKH manifests with 384 total matches
- [ ] Create OKH → Match → Generate Supply Tree workflow - *Partial (create/match working)*

### Implementation ✅

1. **✅ Created test script** (`scripts/test-cloud-run-e2e.sh`)
   - Accepts SERVICE_URL and API_KEY as parameters
   - Tests all endpoints systematically
   - Generates test report

2. **✅ Created Python test suite** (`tests/integration/test_cloud_run_e2e.py`)
   - Uses pytest for structured testing
   - Can be run locally or in CI/CD
   - Generates detailed test reports
   - **Current Status**: 20 passed, 4 skipped (create/match operations skipped due to 500 errors during initial testing, but matching is now functional)

3. **✅ Added to CI/CD pipeline**
   - Runs after successful deployment
   - Fails pipeline if critical tests fail
   - Generates test reports as artifacts
   - Integrated with authentication token generation

### Key Achievements

- **✅ Matching Endpoint**: Fully functional with 94% success rate (31/33 successful matches)
- **✅ Storage Integration**: Successfully connected to GCS, accessing 60+ OKH files and 28 OKW facilities
- **✅ Resource Optimization**: Increased memory to 4Gi, reducing 503 errors from ~70% to ~6%
- **✅ Error Handling**: Improved logging and error reporting for better debugging
- **✅ Documentation**: Updated with memory requirements and deployment best practices

### Known Limitations

- Create operations (OKH/OKW) still return 500 errors in some cases (skipped in tests)
- Some endpoints (PUT, DELETE) not yet tested
- Role-based access control not yet implemented/tested

## Task 2: Cloud-Agnostic Deployment Architecture

### Goals
- Abstract all cloud-specific deployment logic
- Support multiple cloud providers (GCP, AWS, Azure)
- Support container hosting (Digital Ocean, Heroku, etc.)
- Maintain backward compatibility with existing GCP deployment

### Architecture Design

#### 2.1 Deployment Abstraction Layer

```
deploy/
├── base/
│   ├── __init__.py          ✅ Created
│   ├── deployer.py          ✅ Created - Base Deployer class
│   └── config.py            ✅ Created - Base deployment config (provider-agnostic)
├── providers/
│   ├── __init__.py          ✅ Created
│   ├── gcp/
│   │   ├── __init__.py      ✅ Created
│   │   ├── cloud_run.py     ⏳ TODO - GCP Cloud Run deployer
│   │   ├── config.py        ✅ Created - GCP-specific config with validation
│   │   └── iam.py           ⏳ TODO - GCP IAM setup (optional)
│   ├── aws/
│   │   ├── __init__.py
│   │   ├── ecs.py           # AWS ECS deployer
│   │   ├── fargate.py       # AWS Fargate deployer
│   │   └── config.py
│   ├── azure/
│   │   ├── __init__.py
│   │   ├── container_apps.py # Azure Container Apps
│   │   └── config.py
│   └── digitalocean/
│       ├── __init__.py
│       ├── app_platform.py  # Digital Ocean App Platform
│       └── config.py
├── scripts/
│   ├── deploy.sh            # Universal deployment script
│   ├── setup-gcp.sh         # GCP-specific setup
│   ├── setup-aws.sh         # AWS-specific setup
│   └── setup-azure.sh       # Azure-specific setup
└── config/
    ├── deployment.yaml      # Deployment configuration
    └── providers/           # Provider-specific configs
        ├── gcp.yaml
        ├── aws.yaml
        └── azure.yaml
```

#### 2.2 Configuration Management

**Unified Configuration Format** (`deploy/config/deployment.yaml`):
```yaml
provider: gcp  # gcp, aws, azure, digitalocean, etc.
environment: production
region: us-west1

# Common settings
service:
  name: supply-graph-ai
  image: ghcr.io/helpfulengineering/supply-graph-ai:latest
  port: 8080
  memory: 4Gi  # Updated: Required for NLP matching operations
  cpu: 2
  min_instances: 1
  max_instances: 100
  timeout: 300

# Provider-specific settings
providers:
  gcp:
    project_id: nathan-playground-368310
    service_account: supply-graph-ai@${project_id}.iam.gserviceaccount.com
    artifact_registry: us-west1-docker.pkg.dev/${project_id}/cloud-run-source-deploy
  aws:
    cluster: supply-graph-ai-cluster
    task_definition: supply-graph-ai-task
    ecr_repository: supply-graph-ai
  azure:
    resource_group: supply-graph-ai-rg
    container_registry: supplygraphai.azurecr.io
```

#### 2.3 Deployment Interface

**Base Deployer Class** (`deploy/base/deployer.py`):
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseDeployer(ABC):
    """Base class for cloud provider deployers"""
    
    @abstractmethod
    def setup(self, config: Dict[str, Any]) -> None:
        """Setup cloud resources (IAM, storage, etc.)"""
        pass
    
    @abstractmethod
    def deploy(self, config: Dict[str, Any]) -> str:
        """Deploy service and return service URL"""
        pass
    
    @abstractmethod
    def get_service_url(self, service_name: str) -> str:
        """Get the deployed service URL"""
        pass
    
    @abstractmethod
    def update(self, config: Dict[str, Any]) -> None:
        """Update existing deployment"""
        pass
    
    @abstractmethod
    def delete(self, service_name: str) -> None:
        """Delete deployment"""
        pass
```

#### 2.4 CI/CD Abstraction

**Multi-Provider CI/CD** (`.github/workflows/`):
- `ci-cd-gcp.yml` - GCP-specific workflow
- `ci-cd-aws.yml` - AWS-specific workflow
- `ci-cd-azure.yml` - Azure-specific workflow
- `ci-cd-base.yml` - Shared workflow steps (lint, test, build)

**Workflow Selection**:
- Use matrix strategy to test multiple providers
- Or use separate workflows triggered by branch/tag
- Or use environment-based selection

### Implementation Steps

#### Phase 1: Refactor Existing GCP Deployment ✅ COMPLETE
1. ✅ Extract GCP-specific logic into `deploy/providers/gcp/` - **COMPLETE**
   - ✅ Created base deployment structure (`deploy/base/`)
   - ✅ Created GCP-specific configuration (`deploy/providers/gcp/config.py`)
   - ✅ Removed GCP-specific defaults from base config (provider-agnostic)
   - ✅ Added GCP region format validation
   - ✅ GCP deployer implementation (`deploy/providers/gcp/cloud_run.py`)
2. ✅ Create base deployer interface - **COMPLETE**
   - ✅ `BaseDeployer` abstract class with all required methods
   - ✅ `BaseDeploymentConfig` with provider-agnostic defaults
   - ✅ Provider-specific config classes (GCP implemented)
3. ✅ Implement GCP deployer using base interface - **COMPLETE**
   - ✅ All deployment methods implemented
   - ✅ Secret handling and environment variable management
   - ✅ Image verification and service URL extraction
   - ✅ Tested and verified with actual GCP project
4. ⏳ Update CI/CD to use new deployer - **NEXT** (optional - can be done later)
5. ✅ Test backward compatibility - **COMPLETE** (deployed successfully)

#### Phase 2: Add AWS Support
1. Implement AWS deployer (`deploy/providers/aws/`)
2. Create AWS setup scripts
3. Add AWS CI/CD workflow
4. Test AWS deployment

#### Phase 3: Add Azure Support
1. Implement Azure deployer (`deploy/providers/azure/`)
2. Create Azure setup scripts
3. Add Azure CI/CD workflow
4. Test Azure deployment

#### Phase 4: Add Container Hosting Support
1. Implement Digital Ocean deployer
2. Add support for generic Docker/Kubernetes
3. Create universal deployment script

#### Phase 5: Documentation & Testing
1. Update all deployment documentation
2. Create provider comparison guide
3. Add migration guides
4. Comprehensive testing across providers

### Key Design Principles

1. **Backward Compatibility**: Existing GCP deployment should continue to work
2. **Progressive Enhancement**: Add providers incrementally
3. **Configuration Over Code**: Use YAML/config files for provider settings
4. **Fail Fast**: Validate configuration before deployment
5. **Clear Abstractions**: Each provider implements same interface
6. **Documentation**: Each provider has setup guide

### Migration Strategy

1. **Phase 1**: Refactor GCP deployment (no breaking changes)
2. **Phase 2**: Add new providers alongside GCP
3. **Phase 3**: Deprecate old GCP scripts (with migration guide)
4. **Phase 4**: Full multi-provider support

## Current Progress Summary

### ✅ Completed
- **Task 1**: Comprehensive E2E Testing - **COMPLETE**
  - Full test suite implemented and integrated into CI/CD
  - Matching endpoint verified and functional (94% success rate)
  - Storage integration working (GCS)
  - Resource requirements optimized (4Gi memory)
  - Documentation updated

### 🚧 In Progress
- **Task 2**: Cloud-Agnostic Deployment Architecture - **IN PROGRESS (Phase 1)**
  - ✅ Base deployment structure created (`deploy/base/`)
  - ✅ Base deployer interface implemented (`BaseDeployer`)
  - ✅ Base configuration classes created (provider-agnostic)
  - ✅ GCP-specific configuration class created with validation
  - ✅ Removed GCP-specific defaults from base config
  - ⏳ GCP deployer implementation (next step)

### 📋 Next Steps

#### Immediate Next Steps (Task 2 - Phase 1)
1. **Refactor Existing GCP Deployment** ✅ IN PROGRESS
   - [x] Extract GCP-specific logic from CI/CD workflow into `deploy/providers/gcp/` - **PARTIAL**
   - [x] Create base deployer interface (`deploy/base/deployer.py`) - **COMPLETE**
   - [x] Create base configuration classes (`deploy/base/config.py`) - **COMPLETE**
   - [x] Create GCP-specific configuration (`deploy/providers/gcp/config.py`) - **COMPLETE**
   - [x] Remove provider-specific defaults from base config - **COMPLETE**
   - [ ] Implement GCP deployer using base interface - **NEXT**
   - [ ] Update CI/CD to use new deployer
   - [ ] Test backward compatibility

2. **Create Deployment Abstraction Layer** ✅ COMPLETE
   - [x] Create `deploy/` directory structure - **COMPLETE**
   - [x] Implement `BaseDeployer` abstract class - **COMPLETE**
   - [x] Create unified configuration format (`deploy/config/deployment.yaml.example`) - **COMPLETE**
   - [x] Implement GCP-specific configuration class - **COMPLETE**
   - [ ] Implement GCP-specific deployer - **NEXT**

3. **Documentation Updates**
   - [ ] Update deployment guides to use new abstraction
   - [ ] Create migration guide from old to new deployment system
   - [ ] Document provider-specific requirements

#### Future Steps
- **Phase 2**: Add AWS Support
- **Phase 3**: Add Azure Support
- **Phase 4**: Add Container Hosting Support (Digital Ocean, etc.)
- **Phase 5**: Comprehensive testing and documentation across all providers

