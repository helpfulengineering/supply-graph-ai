# Validation Framework File Structure Plan

## Overview

This document outlines the file structure for implementing the domain-integrated validation framework. The structure follows the existing codebase organization patterns and ensures consistency with the current architecture.

## Existing Directory Structure Analysis

### **Current Organization Patterns**
- **`src/core/api/`** - API routes and models
- **`src/core/services/`** - Business logic services
- **`src/core/models/`** - Data models and base classes
- **`src/core/domains/`** - Domain-specific implementations
- **`src/core/registry/`** - Registry and registration systems
- **`src/config/`** - Configuration and domain definitions

### **Existing Validation Infrastructure**
- **`src/core/services/validation_service.py`** - Empty file (placeholder)
- **`src/core/domains/manufacturing/okh_validator.py`** - Existing OKH validator
- **`src/core/domains/cooking/validators.py`** - Existing cooking validators
- **`src/core/api/routes/*/validate`** - Existing validation endpoints

## Proposed File Structure

### **Phase 1: Foundation Files**

#### **1. Core Validation Framework**
```
src/core/validation/
├── __init__.py
├── engine.py                    # ValidationEngine class
├── context.py                   # ValidationContext class
├── result.py                    # ValidationResult, ValidationError, ValidationWarning
├── factory.py                   # ValidationContextFactory
└── exceptions.py                # Validation-specific exceptions
```

#### **2. Validation Models (API Layer)**
```
src/core/api/models/validation/
├── __init__.py
├── request.py                   # ValidationRequest models
├── response.py                  # ValidationResponse models
└── context.py                   # ValidationContext API models
```

#### **3. Enhanced Validation Service**
```
src/core/services/validation_service.py  # Enhanced existing file
```

#### **4. Domain-Specific Validation Rules**
```
src/core/validation/rules/
├── __init__.py
├── base.py                      # BaseValidationRules class
├── manufacturing.py             # ManufacturingValidationRules
└── cooking.py                   # CookingValidationRules
```

#### **5. Validation Middleware**
```
src/core/validation/middleware/
├── __init__.py
├── error_handler.py             # Standardized error response middleware
└── validation_middleware.py     # Request/response validation middleware
```

### **Phase 2: Domain Integration Files**

#### **6. Domain-Specific Validators**
```
src/core/domains/manufacturing/validation/
├── __init__.py
├── okh_validator.py             # Enhanced OKH validator
├── okw_validator.py             # New OKW validator
└── supply_tree_validator.py     # New supply tree validator

src/core/domains/cooking/validation/
├── __init__.py
├── recipe_validator.py          # Enhanced recipe validator
└── kitchen_validator.py         # Enhanced kitchen validator
```

#### **7. Validation Configuration**
```
src/config/validation.py         # Validation configuration settings
```

### **Phase 3: Enhanced API Endpoints**

#### **8. Enhanced Validation Routes**
```
src/core/api/routes/validation.py  # New centralized validation routes
```

## Detailed File Specifications

### **Phase 1 Files**

#### **Staging Directory Structure**
```
src/core/validation/staging/
├── README.md                           # Staging documentation
├── validation_service_legacy.py        # Original empty validation service
├── manufacturing_okh_validator_legacy.py  # Existing OKH validator
└── cooking_validators_legacy.py        # Existing cooking validators
```

#### **`src/core/validation/__init__.py`**
```python
"""
Core validation framework for the Open Matching Engine.

This package provides a domain-integrated validation system that works
seamlessly with the existing domain management infrastructure.
"""

from .engine import ValidationEngine
from .context import ValidationContext
from .result import ValidationResult, ValidationError, ValidationWarning
from .factory import ValidationContextFactory

__all__ = [
    'ValidationEngine',
    'ValidationContext', 
    'ValidationResult',
    'ValidationError',
    'ValidationWarning',
    'ValidationContextFactory'
]
```

#### **`src/core/validation/engine.py`**
```python
"""
Central validation engine integrated with domain system.

This module provides the main ValidationEngine class that coordinates
validation across different domains and validation types.
"""

from typing import Dict, List, Optional, Any
from .context import ValidationContext
from .result import ValidationResult
from ..registry.domain_registry import DomainRegistry
from ..services.domain_service import DomainDetector

class ValidationEngine:
    """Central validation engine integrated with domain system"""
    # Implementation as specified in validation-strategy.md
```

#### **`src/core/validation/context.py`**
```python
"""
Validation context with domain integration.

This module provides the ValidationContext class that integrates
with the existing domain management system.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from ..registry.domain_registry import DomainRegistry

@dataclass
class ValidationContext:
    """Context for validation operations - integrates with existing domain system"""
    # Implementation as specified in validation-strategy.md
```

#### **`src/core/validation/result.py`**
```python
"""
Validation result models.

This module provides the ValidationResult, ValidationError, and ValidationWarning
classes for structured validation responses.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class ValidationError:
    """Represents a validation error"""
    # Implementation details

@dataclass
class ValidationWarning:
    """Represents a validation warning"""
    # Implementation details

@dataclass
class ValidationResult:
    """Result of a validation operation"""
    # Implementation details
```

#### **`src/core/validation/factory.py`**
```python
"""
Validation context factory.

This module provides the ValidationContextFactory class for creating
domain-aware validation contexts.
"""

from typing import Optional, Any
from .context import ValidationContext
from ..registry.domain_registry import DomainRegistry
from ..services.domain_service import DomainDetector

class ValidationContextFactory:
    """Factory for creating validation contexts from domain configurations"""
    # Implementation as specified in validation-strategy.md
```

#### **`src/core/validation/exceptions.py`**
```python
"""
Validation-specific exceptions.

This module provides custom exceptions for validation operations.
"""

class ValidationException(Exception):
    """Base exception for validation errors"""
    pass

class ValidationContextError(ValidationException):
    """Exception for validation context errors"""
    pass

class DomainValidationError(ValidationException):
    """Exception for domain-specific validation errors"""
    pass
```

#### **`src/core/api/models/validation/__init__.py`**
```python
"""
API models for validation operations.

This package provides Pydantic models for validation API requests and responses.
"""

from .request import ValidationRequest, ValidationContextRequest
from .response import ValidationResponse, ValidationContextResponse
from .context import ValidationContextModel

__all__ = [
    'ValidationRequest',
    'ValidationContextRequest', 
    'ValidationResponse',
    'ValidationContextResponse',
    'ValidationContextModel'
]
```

#### **`src/core/api/models/validation/request.py`**
```python
"""
Request models for validation API endpoints.

This module provides Pydantic models for validation requests.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class ValidationRequest(BaseModel):
    """Request model for validation operations"""
    content: Dict[str, Any]
    validation_type: str
    context: Optional[str] = None
    quality_level: Optional[str] = "professional"

class ValidationContextRequest(BaseModel):
    """Request model for validation context operations"""
    domain: str
    quality_level: Optional[str] = "professional"
    strict_mode: Optional[bool] = False
```

#### **`src/core/api/models/validation/response.py`**
```python
"""
Response models for validation API endpoints.

This module provides Pydantic models for validation responses.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from .context import ValidationContextModel

class ValidationIssue(BaseModel):
    """Model for validation issues"""
    severity: str  # "error", "warning", "info"
    message: str
    path: List[str] = []
    code: Optional[str] = None

class ValidationResponse(BaseModel):
    """Response model for validation operations"""
    valid: bool
    normalized_content: Dict[str, Any]
    issues: Optional[List[ValidationIssue]] = None
    context: Optional[ValidationContextModel] = None
    metadata: Dict[str, Any] = {}

class ValidationContextResponse(BaseModel):
    """Response model for validation context operations"""
    contexts: List[ValidationContextModel]
    total_count: int
```

#### **`src/core/api/models/validation/context.py`**
```python
"""
Context models for validation API.

This module provides Pydantic models for validation contexts.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class ValidationContextModel(BaseModel):
    """API model for validation context"""
    name: str
    domain: str
    quality_level: str
    strict_mode: bool = False
    validation_rules: Dict[str, Any] = {}
    supported_types: List[str] = []
```

#### **`src/core/validation/rules/__init__.py`**
```python
"""
Validation rules for different domains.

This package provides domain-specific validation rules that integrate
with the existing domain configuration system.
"""

from .base import BaseValidationRules
from .manufacturing import ManufacturingValidationRules
from .cooking import CookingValidationRules

__all__ = [
    'BaseValidationRules',
    'ManufacturingValidationRules',
    'CookingValidationRules'
]
```

#### **`src/core/validation/rules/base.py`**
```python
"""
Base validation rules class.

This module provides the base class for domain-specific validation rules.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseValidationRules(ABC):
    """Base class for domain-specific validation rules"""
    
    @abstractmethod
    def get_validation_rules(self, quality_level: str) -> Dict[str, Any]:
        """Get validation rules for a specific quality level"""
        pass
    
    @abstractmethod
    def get_required_fields(self, quality_level: str) -> List[str]:
        """Get required fields for a specific quality level"""
        pass
    
    @abstractmethod
    def get_optional_fields(self, quality_level: str) -> List[str]:
        """Get optional fields for a specific quality level"""
        pass
```

#### **`src/core/validation/rules/manufacturing.py`**
```python
"""
Manufacturing domain validation rules.

This module provides validation rules for the manufacturing domain,
integrating with the existing domain configuration.
"""

from typing import Dict, Any, List
from .base import BaseValidationRules
from ...config.domains import get_domain_config

class ManufacturingValidationRules(BaseValidationRules):
    """Validation rules for manufacturing domain"""
    # Implementation as specified in validation-strategy.md
```

#### **`src/core/validation/rules/cooking.py`**
```python
"""
Cooking domain validation rules.

This module provides validation rules for the cooking domain,
integrating with the existing domain configuration.
"""

from typing import Dict, Any, List
from .base import BaseValidationRules
from ...config.domains import get_domain_config

class CookingValidationRules(BaseValidationRules):
    """Validation rules for cooking domain"""
    # Implementation as specified in validation-strategy.md
```

#### **`src/core/validation/middleware/__init__.py`**
```python
"""
Validation middleware for API endpoints.

This package provides middleware for standardized error handling
and request/response validation.
"""

from .error_handler import ValidationErrorHandler
from .validation_middleware import ValidationMiddleware

__all__ = [
    'ValidationErrorHandler',
    'ValidationMiddleware'
]
```

#### **`src/core/validation/middleware/error_handler.py`**
```python
"""
Standardized error response middleware.

This module provides middleware for consistent error responses
across all validation endpoints.
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Callable
import logging

logger = logging.getLogger(__name__)

class ValidationErrorHandler:
    """Middleware for handling validation errors consistently"""
    # Implementation details
```

#### **`src/core/validation/middleware/validation_middleware.py`**
```python
"""
Request/response validation middleware.

This module provides middleware for automatic request and response validation.
"""

from fastapi import Request, Response
from typing import Callable
from .error_handler import ValidationErrorHandler

class ValidationMiddleware:
    """Middleware for automatic request/response validation"""
    # Implementation details
```

### **Phase 2 Files**

#### **`src/core/domains/manufacturing/validation/__init__.py`**
```python
"""
Manufacturing domain validation components.

This package provides domain-specific validators for the manufacturing domain.
"""

from .okh_validator import ManufacturingOKHValidator
from .okw_validator import ManufacturingOKWValidator
from .supply_tree_validator import ManufacturingSupplyTreeValidator

__all__ = [
    'ManufacturingOKHValidator',
    'ManufacturingOKWValidator', 
    'ManufacturingSupplyTreeValidator'
]
```

#### **`src/core/domains/manufacturing/validation/okh_validator.py`**
```python
"""
Enhanced OKH validator for manufacturing domain.

This module provides an enhanced OKH validator that integrates with
the new validation framework while maintaining compatibility with
the existing validator.
"""

from ...validation.rules.manufacturing import ManufacturingValidationRules
from ...validation.context import ValidationContext
from ...validation.result import ValidationResult

class ManufacturingOKHValidator:
    """Enhanced OKH validator for manufacturing domain"""
    # Implementation details
```

#### **`src/core/domains/manufacturing/validation/okw_validator.py`**
```python
"""
OKW validator for manufacturing domain.

This module provides a new OKW validator for the manufacturing domain.
"""

from ...validation.rules.manufacturing import ManufacturingValidationRules
from ...validation.context import ValidationContext
from ...validation.result import ValidationResult

class ManufacturingOKWValidator:
    """OKW validator for manufacturing domain"""
    # Implementation details
```

#### **`src/core/domains/manufacturing/validation/supply_tree_validator.py`**
```python
"""
Supply tree validator for manufacturing domain.

This module provides a supply tree validator for the manufacturing domain.
"""

from ...validation.rules.manufacturing import ManufacturingValidationRules
from ...validation.context import ValidationContext
from ...validation.result import ValidationResult

class ManufacturingSupplyTreeValidator:
    """Supply tree validator for manufacturing domain"""
    # Implementation details
```

#### **`src/core/domains/cooking/validation/__init__.py`**
```python
"""
Cooking domain validation components.

This package provides domain-specific validators for the cooking domain.
"""

from .recipe_validator import CookingRecipeValidator
from .kitchen_validator import CookingKitchenValidator

__all__ = [
    'CookingRecipeValidator',
    'CookingKitchenValidator'
]
```

#### **`src/core/domains/cooking/validation/recipe_validator.py`**
```python
"""
Enhanced recipe validator for cooking domain.

This module provides an enhanced recipe validator that integrates with
the new validation framework.
"""

from ...validation.rules.cooking import CookingValidationRules
from ...validation.context import ValidationContext
from ...validation.result import ValidationResult

class CookingRecipeValidator:
    """Enhanced recipe validator for cooking domain"""
    # Implementation details
```

#### **`src/core/domains/cooking/validation/kitchen_validator.py`**
```python
"""
Enhanced kitchen validator for cooking domain.

This module provides an enhanced kitchen validator that integrates with
the new validation framework.
"""

from ...validation.rules.cooking import CookingValidationRules
from ...validation.context import ValidationContext
from ...validation.result import ValidationResult

class CookingKitchenValidator:
    """Enhanced kitchen validator for cooking domain"""
    # Implementation details
```

#### **`src/config/validation.py`**
```python
"""
Validation configuration settings.

This module provides configuration settings for the validation framework.
"""

from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ValidationConfig:
    """Configuration for validation framework"""
    default_quality_level: str = "professional"
    strict_mode_default: bool = False
    validation_timeout: int = 30  # seconds
    max_validation_errors: int = 100
    enable_caching: bool = True
    cache_ttl: int = 3600  # seconds

# Global validation configuration
VALIDATION_CONFIG = ValidationConfig()
```

### **Phase 3 Files**

#### **`src/core/api/routes/validation.py`**
```python
"""
Centralized validation routes.

This module provides centralized validation endpoints that can be used
across different domains and validation types.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from typing import Optional
from ..models.validation.request import ValidationRequest, ValidationContextRequest
from ..models.validation.response import ValidationResponse, ValidationContextResponse
from ...validation.engine import ValidationEngine
from ...validation.factory import ValidationContextFactory

router = APIRouter(prefix="/validation", tags=["validation"])

@router.post("/validate", response_model=ValidationResponse)
async def validate_data(
    request: ValidationRequest,
    validation_engine: ValidationEngine = Depends(get_validation_engine)
):
    """Centralized validation endpoint"""
    # Implementation details

@router.get("/contexts/{domain}", response_model=ValidationContextResponse)
async def get_validation_contexts(
    domain: str,
    quality_level: Optional[str] = Query("professional"),
    validation_engine: ValidationEngine = Depends(get_validation_engine)
):
    """Get validation contexts for a domain"""
    # Implementation details
```

## File Creation Order

### **Phase 1: Foundation (Week 1)**

**Day 1: Staging Existing Infrastructure (CRITICAL FIRST STEP)**
1. Create `src/core/validation/staging/` directory
2. Move existing validation files to staging:
   - `src/core/services/validation_service.py` → `src/core/validation/staging/validation_service_legacy.py`
   - `src/core/domains/manufacturing/okh_validator.py` → `src/core/validation/staging/manufacturing_okh_validator_legacy.py`
   - `src/core/domains/cooking/validators.py` → `src/core/validation/staging/cooking_validators_legacy.py`
3. Create `src/core/validation/staging/README.md` with staging documentation
4. Verify existing validation endpoints still work (they should, as they import from original locations)

**Day 2-3: Core Framework**
1. Create `src/core/validation/` directory structure
2. Implement `src/core/validation/__init__.py`
3. Implement `src/core/validation/result.py`
4. Implement `src/core/validation/context.py`
5. Implement `src/core/validation/exceptions.py`

**Day 4-5: Engine and Factory**
1. Implement `src/core/validation/engine.py`
2. Implement `src/core/validation/factory.py`
3. Create `src/core/validation/rules/` directory structure
4. Implement `src/core/validation/rules/base.py`

**Day 6: API Models and Middleware**
1. Create `src/core/api/models/validation/` directory structure
2. Implement API model files
3. Create `src/core/validation/middleware/` directory structure
4. Implement middleware files

### **Phase 2: Domain Integration (Week 2)**

**Day 1-2: Domain Rules**
1. Implement `src/core/validation/rules/manufacturing.py`
2. Implement `src/core/validation/rules/cooking.py`
3. Implement `src/config/validation.py`

**Day 3-5: Domain Validators**
1. Create manufacturing validation directory structure
2. Implement manufacturing validators
3. Create cooking validation directory structure
4. Implement cooking validators

### **Phase 3: API Integration (Week 3)**

**Day 1-3: Enhanced Endpoints**
1. Implement `src/core/api/routes/validation.py`
2. Enhance existing validation endpoints
3. Update error handling middleware

**Day 4-5: Testing and Documentation**
1. Create comprehensive test suite
2. Update API documentation
3. Integration testing

## Integration Points

### **Existing File Modifications**

#### **`src/core/services/validation_service.py`**
- Replace empty file with enhanced validation service
- Integrate with new validation framework
- Maintain backward compatibility

#### **`src/core/domains/manufacturing/okh_validator.py`**
- Enhance existing validator to work with new framework
- Maintain existing interface for backward compatibility
- Add new validation capabilities

#### **`src/core/domains/cooking/validators.py`**
- Enhance existing validators to work with new framework
- Maintain existing interface for backward compatibility
- Add new validation capabilities

#### **Existing API Routes**
- Enhance existing validation endpoints in `okh.py`, `okw.py`, `match.py`
- Add domain-aware validation context support
- Implement standardized error responses

### **Configuration Integration**

#### **`src/config/domains.py`**
- No changes required - validation framework uses existing domain configs

#### **`src/core/registry/domain_registry.py`**
- No changes required - validation framework integrates with existing registry

#### **`src/core/services/domain_service.py`**
- No changes required - validation framework uses existing domain service

## Benefits of This Structure

1. **Consistency** - Follows existing codebase organization patterns
2. **Modularity** - Clear separation of concerns with focused modules
3. **Extensibility** - Easy to add new domains and validation types
4. **Integration** - Seamless integration with existing domain system
5. **Maintainability** - Clear file organization and naming conventions
6. **Backward Compatibility** - Enhances existing components without breaking changes

## Staging Strategy Benefits

### **Why Staging is Critical**

The staging approach provides several key benefits for a clean implementation:

1. **Clean Development Environment**
   - No confusion between old and new validation code
   - Clear separation of legacy and new implementations
   - Prevents accidental modification of existing working code

2. **Safe Migration Path**
   - Existing validation endpoints continue to work during development
   - Gradual migration ensures no breaking changes
   - Easy rollback if issues are discovered

3. **Development Clarity**
   - Clear understanding of what's being replaced vs. what's being enhanced
   - Documentation of existing functionality for reference
   - Systematic approach to validation framework implementation

4. **Testing Safety**
   - Existing validation behavior preserved for comparison
   - New framework can be tested against known working implementations
   - Regression testing against staged legacy code

### **Staging Process**

1. **Pre-Staging Verification**
   - Document current validation behavior
   - Run existing validation tests to establish baseline
   - Identify all validation endpoints and their current functionality

2. **Staging Execution**
   - Move files to staging directory with clear naming convention
   - Create comprehensive staging documentation
   - Verify system still works after staging (imports should still resolve)

3. **Post-Staging Development**
   - Implement new validation framework in clean environment
   - Reference staged files for understanding existing behavior
   - Maintain backward compatibility during development

4. **Migration and Cleanup**
   - Gradually migrate existing functionality to new framework
   - Test new implementations against staged legacy behavior
   - Remove staged files only after successful migration and testing

## Next Steps

1. **Review File Structure** - Confirm this structure aligns with your vision
2. **Create Implementation Plan** - Detailed task breakdown for each file
3. **Set Up Development Environment** - Create directory structure and initial files
4. **Begin Phase 1 Implementation** - Start with core framework files
5. **Create Test Suite** - Comprehensive testing for each component
6. **Documentation** - Update API documentation with new validation capabilities
