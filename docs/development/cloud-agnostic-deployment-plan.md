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

## Task 1: Comprehensive End-to-End Testing

### Goals
- Test all major API endpoints on deployed Cloud Run service
- Verify authentication works correctly
- Test actual functionality (not just health checks)
- Create reusable test suite for any deployment

### Test Categories

#### 1.1 Health & System Endpoints
- [ ] `GET /health` - Basic health check
- [ ] `GET /health/readiness` - Readiness check
- [ ] `GET /` - API information
- [ ] `GET /v1` - API version info

#### 1.2 Authentication Tests
- [ ] Test with valid API key
- [ ] Test with invalid API key (401)
- [ ] Test without authentication (401)
- [ ] Test role-based access (read/write/admin)

#### 1.3 Core API Endpoints

**OKH Routes:**
- [ ] `POST /v1/api/okh/create` - Create OKH manifest
- [ ] `GET /v1/api/okh/{id}` - Retrieve OKH
- [ ] `GET /v1/api/okh` - List OKH manifests
- [ ] `PUT /v1/api/okh/{id}` - Update OKH
- [ ] `DELETE /v1/api/okh/{id}` - Delete OKH

**OKW Routes:**
- [ ] `POST /v1/api/okw/create` - Create OKW facility
- [ ] `GET /v1/api/okw/{id}` - Retrieve OKW
- [ ] `GET /v1/api/okw` - List/search OKW facilities
- [ ] `PUT /v1/api/okw/{id}` - Update OKW
- [ ] `DELETE /v1/api/okw/{id}` - Delete OKW

**Match Routes:**
- [ ] `POST /v1/api/match` - Match OKH to OKW
- [ ] `GET /v1/api/match/domains` - List domains
- [ ] `POST /v1/api/match/validate` - Validate matching

**Supply Tree Routes:**
- [ ] `POST /v1/api/supply-tree/create` - Create supply tree
- [ ] `GET /v1/api/supply-tree/{id}` - Retrieve supply tree
- [ ] `GET /v1/api/supply-tree` - List supply trees

**Utility Routes:**
- [ ] `GET /v1/api/utility/domains` - List domains
- [ ] `GET /v1/api/utility/contexts?domain=manufacturing` - Get contexts

#### 1.4 Error Handling Tests
- [ ] 404 for non-existent resources
- [ ] 422 for validation errors
- [ ] 500 error handling (if possible to trigger safely)

#### 1.5 Integration Tests
- [ ] Create OKH → Match → Generate Supply Tree workflow
- [ ] Storage operations (create, read, update, delete)
- [ ] Verify data persistence across requests

### Implementation Plan

1. **Create test script** (`scripts/test-cloud-run-e2e.sh`)
   - Accepts SERVICE_URL and API_KEY as parameters
   - Tests all endpoints systematically
   - Generates test report

2. **Create Python test suite** (`tests/integration/test_cloud_run_e2e.py`)
   - Uses pytest for structured testing
   - Can be run locally or in CI/CD
   - Generates detailed test reports

3. **Add to CI/CD pipeline**
   - Run after successful deployment
   - Fail pipeline if critical tests fail
   - Generate test reports as artifacts

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
│   ├── __init__.py
│   ├── deployer.py          # Base Deployer class
│   └── config.py            # Base deployment config
├── providers/
│   ├── __init__.py
│   ├── gcp/
│   │   ├── __init__.py
│   │   ├── cloud_run.py     # GCP Cloud Run deployer
│   │   ├── config.py        # GCP-specific config
│   │   └── iam.py           # GCP IAM setup
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
  memory: 1Gi
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

#### Phase 1: Refactor Existing GCP Deployment
1. Extract GCP-specific logic into `deploy/providers/gcp/`
2. Create base deployer interface
3. Implement GCP deployer using base interface
4. Update CI/CD to use new deployer
5. Test backward compatibility

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

## Next Steps

1. **Start with Task 1**: Implement comprehensive E2E tests
2. **Then Task 2**: Begin cloud-agnostic refactoring
3. **Iterate**: Add providers incrementally based on needs

