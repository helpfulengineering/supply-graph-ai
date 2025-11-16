# Registry & Type System Refactoring Specification

## Overview

This specification defines the implementation plan for refactoring the domain registry to use proper base class types instead of `Any`. This addresses technical debt and improves type safety while maintaining backward compatibility.

## Current State Analysis

### Issue: Type System Inconsistency

**Location**: `src/core/registry/domain_registry.py:47-48,96`

**Current Implementation:**
```python
@dataclass
class DomainServices:
    """Container for all services associated with a domain"""
    extractor: BaseExtractor
    matcher: Any  # TODO: Make this BaseMatcher when existing classes are refactored
    validator: Any  # TODO: Make this BaseValidator when existing classes are refactored
    metadata: DomainMetadata
    orchestrator: Optional[Any] = None  # BaseOrchestrator when available

@classmethod
def _validate_services(cls, extractor: BaseExtractor, matcher: Any, validator: Any) -> None:
    """Validate that services implement required interfaces"""
    if not isinstance(extractor, BaseExtractor):
        raise TypeError(f"Extractor must inherit from BaseExtractor, got {type(extractor)}")
    # For now, be flexible with matcher and validator types to work with existing code
    # TODO: Refactor existing matchers and validators to inherit from base classes
    if matcher is None:
        raise TypeError("Matcher cannot be None")
    if validator is None:
        raise TypeError("Validator cannot be None")
```

**Problems:**
- Uses `Any` type for matcher and validator, losing type safety
- No compile-time type checking for matcher/validator interfaces
- Inconsistent inheritance across domain implementations
- Two different validator base classes exist (`BaseValidator` and `Validator`)

**Context:**
- `BaseExtractor` is properly typed and all extractors inherit from it
- Some matchers inherit from `BaseMatcher` (OKHMatcher), some don't (CookingMatcher)
- Some validators inherit from `BaseValidator` (OKHValidator), some from `Validator` (new validation framework)
- Domain registry needs to work with both old and new implementations

**Severity**: Medium - Technical debt, affects type safety and maintainability

### Current Inheritance Status

#### Matchers

**Inherit from BaseMatcher:**
- ✅ `OKHMatcher` (manufacturing) - inherits from `BaseMatcher`
- ✅ `MfgDirectMatcher` (manufacturing) - inherits from `DirectMatcher` (which may inherit from BaseMatcher)
- ✅ `CookingDirectMatcher` (cooking) - inherits from `DirectMatcher`

**Do NOT inherit from BaseMatcher:**
- ❌ `CookingMatcher` (cooking) - no base class

#### Validators

**Inherit from BaseValidator:**
- ✅ `OKHValidator` (manufacturing) - inherits from `BaseValidator`
- ✅ `ManufacturingOKHValidatorCompat` - inherits from `BaseValidator`
- ✅ `ManufacturingOKWValidatorCompat` - inherits from `BaseValidator`
- ✅ `CookingValidatorCompat` - inherits from `BaseValidator`

**Inherit from Validator (validation engine):**
- ✅ `ManufacturingOKHValidator` - inherits from `Validator` (new framework)
- ✅ `ManufacturingOKWValidator` - inherits from `Validator` (new framework)
- ✅ `ManufacturingSupplyTreeValidator` - inherits from `Validator` (new framework)
- ✅ `CookingRecipeValidator` - inherits from `Validator` (new framework)
- ✅ `CookingKitchenValidator` - inherits from `Validator` (new framework)

**Do NOT inherit from either:**
- ❌ `CookingValidator` - no base class

### Base Class Definitions

**BaseMatcher** (`src/core/models/base/base_types.py`):
```python
class BaseMatcher(ABC):
    """Abstract base class for matching requirements to capabilities"""
    
    @abstractmethod
    def match(self, 
              requirements: List[Requirement],
              capabilities: List[Capability]) -> MatchResult:
        """Match requirements against capabilities"""
        pass
```

**BaseValidator** (`src/core/models/base/base_types.py`):
```python
class BaseValidator(ABC):
    """Abstract base class for validation rules"""
    
    @abstractmethod
    def validate(self,
                requirement: Requirement,
                capability: Optional[Capability] = None) -> bool:
        """Validate a requirement or requirement-capability pair"""
        pass
```

**Validator** (`src/core/validation/engine.py`):
```python
class Validator(ABC):
    """Base class for all validators"""
    
    @abstractmethod
    async def validate(self, data: Any, context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate data and return result"""
    
    @property
    @abstractmethod
    def validation_type(self) -> str:
        """Return the type of validation this validator performs"""
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Return validation priority (higher = earlier)"""
```

## Requirements

### Functional Requirements

1. **Type Safety**
   - All matchers should inherit from `BaseMatcher`
   - All validators should inherit from `BaseValidator` (or have adapter)
   - Type hints should be accurate
   - Compile-time type checking should work

2. **Backward Compatibility**
   - Existing code should continue to work
   - No breaking changes to public APIs
   - Gradual migration path

3. **Dual Validator Support**
   - Support both `BaseValidator` (old) and `Validator` (new framework)
   - Provide adapter pattern if needed
   - Clear migration path

### Non-Functional Requirements

1. **Maintainability**
   - Clear inheritance hierarchy
   - Easy to add new domains
   - Consistent patterns

2. **Type Safety**
   - Proper type hints
   - IDE autocomplete support
   - Type checking with mypy

## Design Decisions

### Strategy: Gradual Refactoring with Adapter Pattern

**Option 1: Force All to Inherit from Base Classes (Breaking)**
- Pros: Clean, type-safe
- Cons: Breaking changes, requires refactoring all validators

**Option 2: Adapter Pattern (Recommended)**
- Pros: Backward compatible, supports both validator types
- Cons: Slightly more complex

**Option 3: Union Types**
- Pros: Supports both types
- Cons: Less type-safe, still uses `Any` effectively

**Decision: Option 2 (Adapter Pattern)**
- Create adapter for `Validator` -> `BaseValidator`
- Refactor matchers to inherit from `BaseMatcher`
- Use Union type for validators during transition
- Document migration path

### Validator Strategy

**Two Validator Types:**
1. `BaseValidator` - Old interface: `validate(requirement, capability) -> bool`
2. `Validator` - New interface: `async validate(data, context) -> ValidationResult`

**Solution:**
- Create `ValidatorAdapter` that wraps `Validator` and implements `BaseValidator`
- Use Union type: `BaseValidator | ValidatorAdapter`
- Or create common base interface

## Implementation Specification

### 1. Create Validator Adapter

**File: `src/core/registry/validator_adapter.py` (new file)**

```python
"""
Adapter for new validation framework validators to work with BaseValidator interface.

This adapter allows validators from the new validation framework (Validator)
to be used in contexts that expect BaseValidator.
"""

from typing import Optional
from ..models.base.base_types import BaseValidator, Requirement, Capability
from ..validation.engine import Validator as ValidationEngineValidator
from ..validation.context import ValidationContext
from ..validation.result import ValidationResult


class ValidatorAdapter(BaseValidator):
    """
    Adapter that wraps a ValidationEngineValidator to implement BaseValidator interface.
    
    This allows new framework validators to be used in contexts expecting BaseValidator.
    """
    
    def __init__(self, validator: ValidationEngineValidator):
        """
        Initialize adapter with a ValidationEngineValidator.
        
        Args:
            validator: Validator from new validation framework
        """
        if not isinstance(validator, ValidationEngineValidator):
            raise TypeError(f"validator must be ValidationEngineValidator, got {type(validator)}")
        self._validator = validator
    
    def validate(self,
                requirement: Requirement,
                capability: Optional[Capability] = None) -> bool:
        """
        Validate a requirement or requirement-capability pair.
        
        This method adapts the new async ValidationResult interface to the
        old synchronous bool interface.
        
        Args:
            requirement: Requirement to validate
            capability: Optional capability to validate against
            
        Returns:
            True if valid, False otherwise
        """
        import asyncio
        
        # Create validation context
        context = ValidationContext()
        context.add_data("requirement", requirement)
        if capability:
            context.add_data("capability", capability)
        
        # Call async validator (run in event loop if needed)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we can't use asyncio.run
                # For now, create a new task or use a different approach
                # This is a limitation - async validators in sync context
                # TODO: Consider making BaseValidator.validate async
                raise RuntimeError(
                    "Cannot use async validator in sync context. "
                    "Consider using async validation or sync validator."
                )
            else:
                result = asyncio.run(self._validator.validate(requirement, context))
        except RuntimeError:
            # No event loop, create one
            result = asyncio.run(self._validator.validate(requirement, context))
        
        return result.valid
    
    @property
    def wrapped_validator(self) -> ValidationEngineValidator:
        """Get the wrapped validator."""
        return self._validator
```

**Alternative: Make BaseValidator Async**

If we want to support async validators properly, we could make `BaseValidator.validate` async:

```python
class BaseValidator(ABC):
    """Abstract base class for validation rules"""
    
    @abstractmethod
    async def validate(self,
                      requirement: Requirement,
                      capability: Optional[Capability] = None) -> bool:
        """Validate a requirement or requirement-capability pair"""
        pass
```

But this would be a breaking change. Better to use adapter pattern.

### 2. Refactor CookingMatcher

**File: `src/core/domains/cooking/matchers.py`**

**Update to inherit from BaseMatcher:**

```python
from typing import List, Dict, Any
from uuid import uuid4
from ...models.base.base_types import (
    BaseMatcher, Requirement, Capability, MatchResult,
    NormalizedRequirements, NormalizedCapabilities
)
from ...models.supply_trees import SupplyTree

class CookingMatcher(BaseMatcher):
    """Matcher for cooking domain - simplified version without workflows"""
    
    def match(self, 
             requirements: List[Requirement],
             capabilities: List[Capability]) -> MatchResult:
        """
        Match requirements against capabilities.
        
        This is a simplified implementation that converts normalized data
        to requirements/capabilities and performs basic matching.
        
        Args:
            requirements: List of requirements to match
            capabilities: List of capabilities to match against
            
        Returns:
            MatchResult with matched capabilities and confidence
        """
        matched_capabilities = {}
        missing_requirements = []
        substitutions = []
        
        for req in requirements:
            matched = False
            for cap in capabilities:
                if self._can_satisfy(req, cap):
                    matched_capabilities[req] = cap
                    matched = True
                    break
            
            if not matched:
                missing_requirements.append(req)
        
        # Calculate confidence
        total = len(requirements)
        matched_count = len(matched_capabilities)
        confidence = matched_count / total if total > 0 else 0.0
        
        return MatchResult(
            confidence=confidence,
            matched_capabilities=matched_capabilities,
            missing_requirements=missing_requirements,
            substitutions=substitutions
        )
    
    def _can_satisfy(self, requirement: Requirement, capability: Capability) -> bool:
        """Check if capability can satisfy requirement."""
        # Simple name matching for now
        return requirement.name.lower() == capability.name.lower()
    
    def generate_supply_tree(self, 
                            requirements: NormalizedRequirements, 
                            capabilities: NormalizedCapabilities,
                            kitchen_name: str = "Cooking Facility",
                            recipe_name: str = "cooking_recipe") -> SupplyTree:
        """
        Generate a simplified cooking supply tree.
        
        This method is kept for backward compatibility but is not part of
        the BaseMatcher interface. Consider moving to a separate class.
        
        Args:
            requirements: Normalized requirements
            capabilities: Normalized capabilities
            kitchen_name: Name of the kitchen facility
            recipe_name: Name of the recipe
            
        Returns:
            SupplyTree representing the cooking workflow
        """
        # ... existing implementation ...
        # (keep existing code)
```

### 3. Refactor CookingValidator

**File: `src/core/domains/cooking/validators.py`**

**Update to inherit from BaseValidator:**

```python
from typing import Optional
from ...models.base.base_types import BaseValidator, Requirement, Capability

class CookingValidator(BaseValidator):
    """Validator for cooking domain"""
    
    def validate(self,
                requirement: Requirement,
                capability: Optional[Capability] = None) -> bool:
        """
        Validate a requirement or requirement-capability pair.
        
        Args:
            requirement: Requirement to validate
            capability: Optional capability to validate against
            
        Returns:
            True if valid, False otherwise
        """
        # Validate requirement
        if not requirement.name:
            return False
        
        if not hasattr(requirement, 'parameters') or requirement.parameters is None:
            return False
        
        # If capability provided, validate compatibility
        if capability:
            return self._validate_compatibility(requirement, capability)
        
        return True
    
    def _validate_compatibility(self, requirement: Requirement, capability: Capability) -> bool:
        """Validate that capability is compatible with requirement."""
        # Simple validation - can be enhanced
        return True
```

### 4. Update DomainRegistry Type Hints

**File: `src/core/registry/domain_registry.py`**

**Update to use proper types with Union for validators:**

```python
from typing import Dict, Type, Any, Optional, Set, List, Union
from dataclasses import dataclass
from enum import Enum
import logging
from ..models.base.base_extractors import BaseExtractor
from ..models.base.base_types import BaseMatcher, BaseValidator
from .validator_adapter import ValidatorAdapter
from ..validation.engine import Validator as ValidationEngineValidator

logger = logging.getLogger(__name__)

# Type alias for validators (supports both old and new)
ValidatorType = Union[BaseValidator, ValidatorAdapter]

@dataclass
class DomainServices:
    """Container for all services associated with a domain"""
    extractor: BaseExtractor
    matcher: BaseMatcher  # Now properly typed
    validator: ValidatorType  # Supports both BaseValidator and adapted Validator
    metadata: DomainMetadata
    orchestrator: Optional[Any] = None  # BaseOrchestrator when available

class DomainRegistry:
    """Unified registry for domain-specific components with management"""
    _domains: Dict[str, DomainServices] = {}
    _type_mappings: Dict[str, str] = {}
    
    @classmethod
    def register_domain(
        cls,
        domain_name: str,
        extractor: BaseExtractor,
        matcher: BaseMatcher,  # Now requires BaseMatcher
        validator: ValidatorType,  # Accepts BaseValidator or ValidatorAdapter
        metadata: DomainMetadata,
        orchestrator: Optional[Any] = None
    ) -> None:
        """Register a complete domain with all its services"""
        if domain_name in cls._domains:
            logger.warning(f"Overwriting existing domain: {domain_name}")
        
        # Validate services
        cls._validate_services(extractor, matcher, validator)
        
        # Wrap ValidationEngineValidator if needed
        if isinstance(validator, ValidationEngineValidator):
            validator = ValidatorAdapter(validator)
            logger.debug(f"Wrapped ValidationEngineValidator for domain {domain_name}")
        
        services = DomainServices(
            extractor=extractor,
            matcher=matcher,
            validator=validator,
            metadata=metadata,
            orchestrator=orchestrator
        )
        
        cls._domains[domain_name] = services
        
        # Register type mappings
        for input_type in metadata.supported_input_types:
            cls._type_mappings[input_type] = domain_name
        
        logger.info(f"Registered domain: {domain_name} with types: {metadata.supported_input_types}")
    
    @classmethod
    def _validate_services(cls, extractor: BaseExtractor, matcher: BaseMatcher, validator: ValidatorType) -> None:
        """Validate that services implement required interfaces"""
        if not isinstance(extractor, BaseExtractor):
            raise TypeError(f"Extractor must inherit from BaseExtractor, got {type(extractor)}")
        
        if not isinstance(matcher, BaseMatcher):
            raise TypeError(f"Matcher must inherit from BaseMatcher, got {type(matcher)}")
        
        # Validator can be BaseValidator or ValidationEngineValidator (will be wrapped)
        if isinstance(validator, BaseValidator):
            # Already correct type
            pass
        elif isinstance(validator, ValidationEngineValidator):
            # Will be wrapped by register_domain
            pass
        else:
            raise TypeError(
                f"Validator must be BaseValidator or ValidationEngineValidator, "
                f"got {type(validator)}"
            )
    
    @classmethod
    def get_matcher(cls, domain: str) -> BaseMatcher:
        """Get registered matcher for domain"""
        return cls.get_domain_services(domain).matcher
    
    @classmethod
    def get_validator(cls, domain: str) -> ValidatorType:
        """Get registered validator for domain"""
        return cls.get_domain_services(domain).validator
```

### 5. Update Domain Registration Calls

**File: `src/core/services/matching_service.py`**

**Update to use proper types:**

```python
# CookingMatcher now inherits from BaseMatcher, so this works
DomainRegistry.register_domain(
    domain_name="cooking",
    extractor=CookingExtractor(),
    matcher=CookingMatcher(),  # Now properly typed as BaseMatcher
    validator=CookingValidatorCompat(),  # Already BaseValidator
    metadata=cooking_metadata
)

# Manufacturing domain
DomainRegistry.register_domain(
    domain_name="manufacturing",
    extractor=OKHExtractor(),
    matcher=OKHMatcher(),  # Already BaseMatcher
    validator=ManufacturingOKHValidatorCompat(),  # Already BaseValidator
    metadata=manufacturing_metadata
)
```

**For new framework validators, they'll be automatically wrapped:**

```python
# If using new framework validator, it will be wrapped automatically
from ..domains.manufacturing.validation.okh_validator import ManufacturingOKHValidator

DomainRegistry.register_domain(
    domain_name="manufacturing",
    extractor=OKHExtractor(),
    matcher=OKHMatcher(),
    validator=ManufacturingOKHValidator(),  # Will be wrapped by ValidatorAdapter
    metadata=manufacturing_metadata
)
```

## Integration Points

### 1. Domain Registry

- Now uses proper types for matchers
- Supports both validator types via adapter
- Type-safe getter methods

### 2. Domain Implementations

- All matchers inherit from `BaseMatcher`
- Validators can use either `BaseValidator` or `Validator` (with adapter)
- Consistent interface

### 3. Service Registry

- `ServiceRegistry` already uses strict types
- Can be aligned with `DomainRegistry` approach

## Testing Considerations

### Unit Tests

1. **Validator Adapter Tests:**
   - Test wrapping ValidationEngineValidator
   - Test validate method conversion
   - Test error handling

2. **Matcher Refactoring Tests:**
   - Test CookingMatcher.match() method
   - Test backward compatibility
   - Test type checking

3. **Domain Registry Tests:**
   - Test type validation
   - Test automatic validator wrapping
   - Test getter methods return correct types

### Integration Tests

1. **End-to-End Domain Registration:**
   - Test registering domains with different validator types
   - Test using registered matchers/validators
   - Test backward compatibility

## Migration Plan

### Phase 1: Create Adapter (Non-Breaking)
- Create `ValidatorAdapter` class
- Add Union type support
- Update type hints

### Phase 2: Refactor Matchers (Non-Breaking)
- Refactor `CookingMatcher` to inherit from `BaseMatcher`
- Update domain registry to require `BaseMatcher`
- Test backward compatibility

### Phase 3: Refactor Validators (Non-Breaking)
- Refactor `CookingValidator` to inherit from `BaseValidator`
- Update domain registry to use Union type
- Test adapter with new framework validators

### Phase 4: Documentation (Non-Breaking)
- Document inheritance requirements
- Document adapter usage
- Update examples

## Success Criteria

1. ✅ All matchers inherit from `BaseMatcher`
2. ✅ All validators inherit from `BaseValidator` or use adapter
3. ✅ Domain registry uses proper type hints
4. ✅ No `Any` types for matcher/validator
5. ✅ Backward compatibility maintained
6. ✅ Type checking passes (mypy)
7. ✅ All tests pass

## Open Questions / Future Enhancements

1. **Async BaseValidator:**
   - Should `BaseValidator.validate` be async?
   - Would require refactoring all validators
   - Better long-term solution but breaking change

2. **Unified Validator Interface:**
   - Create common base class for both validator types?
   - Would require significant refactoring
   - May not be worth it if adapter works

3. **Type Stubs:**
   - Add type stubs for better IDE support?
   - Use Protocol for structural typing?

4. **ServiceRegistry Alignment:**
   - Align `ServiceRegistry` with `DomainRegistry`?
   - Consolidate into single registry?

## Dependencies

### No New Dependencies

- Uses existing base classes
- Uses existing validation framework
- No external libraries required

## Implementation Order

1. Create `ValidatorAdapter` class
2. Update `DomainRegistry` type hints
3. Refactor `CookingMatcher` to inherit from `BaseMatcher`
4. Refactor `CookingValidator` to inherit from `BaseValidator`
5. Update domain registration calls
6. Write tests
7. Update documentation

## Notes

### Validator Adapter Limitations

The `ValidatorAdapter` has a limitation: it cannot be used in async contexts where an event loop is already running. This is because it needs to call `asyncio.run()` which requires no running loop.

**Solutions:**
1. Make `BaseValidator.validate` async (breaking change)
2. Use `asyncio.create_task()` if loop is running (complex)
3. Document limitation and recommend using `BaseValidator` directly for sync contexts

### Type Checking

With Union types, type checkers may need explicit type narrowing:

```python
validator = DomainRegistry.get_validator("manufacturing")
if isinstance(validator, ValidatorAdapter):
    # Access wrapped_validator
    wrapped = validator.wrapped_validator
else:
    # Direct BaseValidator
    result = validator.validate(req, cap)
```

This is acceptable and provides type safety.

