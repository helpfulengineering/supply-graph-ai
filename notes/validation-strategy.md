# API Validation Strategy

## Current State Analysis

### **Existing Validation Patterns**

1. **Pydantic Model Validation** (Automatic)
   - Request/Response models use Pydantic for basic type validation
   - Custom validators using `@model_validator` (e.g., `MatchRequest.validate_okh_input()`)
   - Field-level validation with `Field()` constraints

2. **Manual Validation in API Routes**
   - File type validation in upload endpoints
   - Business logic validation (e.g., `okh_manifest.validate()`)
   - Ad-hoc error handling with `HTTPException`

3. **Service-Level Validation**
   - Some services have validation methods (e.g., `OKHService.validate()`)
   - Model-level validation (e.g., `OKHManifest.validate()`)
   - Inconsistent application across services

4. **Storage-Level Validation**
   - Basic model conversion validation in `from_dict()` methods
   - No systematic validation of data integrity

### **Current Issues**

1. **Inconsistent Validation Layers**
   - Some endpoints validate, others don't
   - Different validation approaches across similar endpoints
   - No clear validation hierarchy

2. **Missing Validation Points**
   - File upload validation is basic
   - No business rule validation for OKW facilities
   - No cross-field validation (e.g., equipment compatibility)

3. **Error Handling Inconsistency**
   - Different HTTP status codes for similar validation failures
   - Inconsistent error message formats
   - No structured validation error responses

4. **No Validation Context**
   - No domain-specific validation rules
   - No validation context (e.g., 'manufacturing' vs 'hobby')
   - No validation severity levels

## Proposed Validation Architecture

### **1. Validation Layers**

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   File Upload   │  │   Request       │  │   Response   │ │
│  │   Validation    │  │   Validation    │  │   Validation │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Service Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Business      │  │   Domain        │  │   Cross-     │ │
│  │   Rules         │  │   Rules         │  │   Field      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   Model Layer                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Schema        │  │   Type          │  │   Constraint │ │
│  │   Validation    │  │   Validation    │  │   Validation │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Storage Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Data          │  │   Integrity     │  │   Consistency│ │
│  │   Integrity     │  │   Checks        │  │   Validation │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### **2. Validation Points in Data Flow**

#### **A. Input Validation (API Layer)**
1. **File Upload Validation**
   - File type validation (extension, MIME type)
   - File size limits
   - File content parsing (JSON/YAML syntax)
   - Basic structure validation

2. **Request Validation**
   - Pydantic model validation (automatic)
   - Custom business rule validation
   - Cross-field validation
   - Required field validation

3. **Parameter Validation**
   - Path parameter validation (UUIDs, etc.)
   - Query parameter validation
   - Form data validation

#### **B. Business Logic Validation (Service Layer)**
1. **Domain-Specific Validation**
   - OKH manifest completeness
   - OKW facility capability validation
   - Supply tree workflow validation

2. **Cross-Entity Validation**
   - Equipment compatibility with processes
   - Material compatibility with equipment
   - Facility capacity validation

3. **Context-Aware Validation**
   - Manufacturing vs hobby contexts
   - Quality level requirements
   - Regulatory compliance

#### **C. Data Integrity Validation (Model Layer)**
1. **Schema Validation**
   - Required field presence
   - Data type correctness
   - Enum value validation

2. **Constraint Validation**
   - Range validation (e.g., positive numbers)
   - Format validation (e.g., email, URL)
   - Reference validation (e.g., valid UUIDs)

#### **D. Storage Validation (Storage Layer)**
1. **Data Consistency**
   - Referential integrity
   - Data versioning
   - Conflict resolution

2. **Performance Validation**
   - Data size limits
   - Query performance
   - Storage quotas

### **3. Validation Framework Design**

#### **A. Validation Engine**
```python
class ValidationEngine:
    """Central validation engine for all API operations"""
    
    def __init__(self):
        self.validators: Dict[str, List[Validator]] = {}
        self.contexts: Dict[str, ValidationContext] = {}
    
    async def validate(self, 
                      data: Any, 
                      validation_type: str, 
                      context: Optional[str] = None) -> ValidationResult:
        """Validate data using specified validation type and context"""
        
    def register_validator(self, 
                          validation_type: str, 
                          validator: Validator, 
                          priority: int = 0):
        """Register a validator for a specific validation type"""
        
    def register_context(self, 
                        context_name: str, 
                        context: ValidationContext):
        """Register a validation context"""
```

#### **B. Validator Interface**
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

#### **C. Validation Result**
```python
@dataclass
class ValidationResult:
    """Result of a validation operation"""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        """Add a validation error"""
        
    def add_warning(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        """Add a validation warning"""
```

#### **D. Validation Context (Integrated with Domain System)**
```python
@dataclass
class ValidationContext:
    """Context for validation operations - integrates with existing domain system"""
    name: str
    domain: str  # Must be a registered domain from DomainRegistry
    quality_level: str  # 'hobby', 'professional', 'medical'
    strict_mode: bool = False
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate that domain exists in registry"""
        from src.core.registry.domain_registry import DomainRegistry
        if self.domain not in DomainRegistry.list_domains():
            raise ValueError(f"Domain '{self.domain}' is not registered. Available domains: {DomainRegistry.list_domains()}")
    
    def get_domain_services(self):
        """Get domain services for this context"""
        from src.core.registry.domain_registry import DomainRegistry
        return DomainRegistry.get_domain_services(self.domain)
    
    def get_domain_validator(self):
        """Get domain-specific validator"""
        return self.get_domain_services().validator
```

### **4. Integration with Existing Domain System**

#### **A. Leveraging Existing Domain Infrastructure**

Our validation framework must integrate seamlessly with the existing domain management system:

1. **DomainRegistry Integration**
   - Use `DomainRegistry.get_domain_services()` to get domain-specific validators
   - Leverage existing `DomainMetadata` for validation context
   - Utilize `DomainStatus` for validation availability

2. **DomainDetector Integration**
   - Use `DomainDetector.detect_and_validate_domain()` for automatic domain detection
   - Leverage existing domain detection logic for validation context
   - Integrate with `DomainDetectionResult` for validation confidence

3. **Domain Configuration Integration**
   - Use `DOMAIN_CONFIGS` from `domains.py` for validation rules
   - Leverage `TYPE_DOMAIN_MAPPING` for automatic domain inference
   - Utilize `DOMAIN_KEYWORDS` for content-based validation

#### **B. Enhanced Validation Engine with Domain Integration**
```python
class ValidationEngine:
    """Central validation engine integrated with domain system"""
    
    def __init__(self):
        self.validators: Dict[str, List[Validator]] = {}
        self.domain_registry = DomainRegistry
        self.domain_detector = DomainDetector
    
    async def validate_with_domain_detection(self, 
                                           data: Any, 
                                           validation_type: str,
                                           requirements: Any = None,
                                           capabilities: Any = None) -> ValidationResult:
        """Validate data with automatic domain detection"""
        
        # Detect domain if not explicitly provided
        if requirements and capabilities:
            domain = self.domain_detector.detect_and_validate_domain(requirements, capabilities)
            context = ValidationContext(
                name=f"{domain}_validation",
                domain=domain,
                quality_level="professional"  # Default, can be overridden
            )
        else:
            context = None
        
        return await self.validate(data, validation_type, context)
    
    async def validate(self, 
                      data: Any, 
                      validation_type: str, 
                      context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate data using domain-specific validators"""
        
        result = ValidationResult(valid=True)
        
        # Get domain-specific validator if context provided
        if context:
            domain_validator = context.get_domain_validator()
            if domain_validator:
                domain_result = await domain_validator.validate(data, context)
                result.merge(domain_result)
        
        # Apply general validators
        for validator in self.validators.get(validation_type, []):
            validator_result = await validator.validate(data, context)
            result.merge(validator_result)
        
        return result
```

#### **C. Domain-Specific Validation Rules**

Based on the existing domain configurations, we can define validation rules:

```python
class DomainValidationRules:
    """Validation rules based on existing domain configurations"""
    
    @staticmethod
    def get_validation_rules(domain_name: str) -> Dict[str, Any]:
        """Get validation rules for a specific domain"""
        from src.config.domains import get_domain_config
        
        try:
            domain_config = get_domain_config(domain_name)
        except ValueError:
            return {}
        
        # Base rules from domain configuration
        rules = {
            "supported_input_types": list(domain_config.supported_input_types),
            "supported_output_types": list(domain_config.supported_output_types),
            "domain_status": domain_config.status.value,
            "version": domain_config.version
        }
        
        # Domain-specific validation rules
        if domain_name == "manufacturing":
            rules.update({
                "okh_required_fields": ["title", "version", "license", "function"],
                "okw_required_fields": ["name", "location", "facility_status"],
                "quality_levels": ["hobby", "professional", "medical"],
                "validation_contexts": ["manufacturing", "hobby", "professional"]
            })
        elif domain_name == "cooking":
            rules.update({
                "recipe_required_fields": ["name", "ingredients", "instructions"],
                "kitchen_required_fields": ["name", "location", "equipment"],
                "quality_levels": ["home", "commercial", "professional"],
                "validation_contexts": ["cooking", "home", "commercial"]
            })
        
        return rules
```

#### **D. Validation Context Factory**
```python
class ValidationContextFactory:
    """Factory for creating validation contexts from domain configurations"""
    
    @staticmethod
    def create_context(domain_name: str, 
                      quality_level: str = "professional",
                      strict_mode: bool = False) -> ValidationContext:
        """Create validation context from domain configuration"""
        
        # Validate domain exists
        from src.core.registry.domain_registry import DomainRegistry
        if domain_name not in DomainRegistry.list_domains():
            raise ValueError(f"Domain '{domain_name}' not found")
        
        # Get domain metadata
        domain_metadata = DomainRegistry.get_domain_metadata(domain_name)
        
        # Create context
        context = ValidationContext(
            name=f"{domain_name}_{quality_level}",
            domain=domain_name,
            quality_level=quality_level,
            strict_mode=strict_mode,
            custom_rules=DomainValidationRules.get_validation_rules(domain_name)
        )
        
        return context
    
    @staticmethod
    def create_from_detection(requirements: Any, 
                            capabilities: Any,
                            quality_level: str = "professional") -> ValidationContext:
        """Create validation context from domain detection"""
        
        from src.core.services.domain_service import DomainDetector
        
        # Detect domain
        domain = DomainDetector.detect_and_validate_domain(requirements, capabilities)
        
        # Create context
        return ValidationContextFactory.create_context(domain, quality_level)
```

### **5. Implementation Strategy**

#### **Phase 1: Foundation (Week 1)**

#### **1.1 Staging Existing Validation Infrastructure**
**Priority: CRITICAL - Must be done first**

Before implementing the new validation framework, we need to stage the existing validation infrastructure to avoid confusion and conflicts:

**Files to Move to Staging:**
```
# Create staging directory
mkdir -p src/core/validation/staging

# Move existing validation files
mv src/core/services/validation_service.py src/core/validation/staging/validation_service_legacy.py
mv src/core/domains/manufacturing/okh_validator.py src/core/validation/staging/manufacturing_okh_validator_legacy.py
mv src/core/domains/cooking/validators.py src/core/validation/staging/cooking_validators_legacy.py

# Create staging documentation
touch src/core/validation/staging/README.md
```

**Staging Documentation:**
```markdown
# Legacy Validation Infrastructure (Staged)

This directory contains the existing validation infrastructure that has been temporarily moved to avoid conflicts during the implementation of the new domain-integrated validation framework.

## Files Staged:
- `validation_service_legacy.py` - Original empty validation service
- `manufacturing_okh_validator_legacy.py` - Existing OKH validator for manufacturing domain
- `cooking_validators_legacy.py` - Existing cooking domain validators

## Migration Plan:
1. **Phase 1**: New validation framework implemented alongside staged files
2. **Phase 2**: Existing validators enhanced to work with new framework
3. **Phase 3**: Staged files integrated back into new structure
4. **Phase 4**: Legacy files removed after successful migration

## Backward Compatibility:
- All existing validation endpoints continue to work during migration
- New framework provides enhanced functionality while maintaining existing interfaces
- Gradual migration ensures no breaking changes
```

**Benefits of Staging:**
1. **Clean Implementation** - No confusion between old and new validation code
2. **Safe Migration** - Existing functionality preserved during transition
3. **Clear Documentation** - Staged files documented for future reference
4. **Rollback Safety** - Easy to restore original files if needed
5. **Development Clarity** - Clear separation between legacy and new code

#### **1.2 Create Validation Framework**
1. **Implement Core Framework**
   - Implement `ValidationEngine` base classes integrated with `DomainRegistry`
   - Create `ValidationResult` and `ValidationError` models
   - Set up `ValidationContext` system integrated with existing domain infrastructure
   - Create `ValidationContextFactory` for domain-aware context creation

2. **Standardize Error Responses**
   - Create consistent error response models
   - Implement error response middleware
   - Update existing endpoints to use standard errors

3. **Domain Integration**
   - Integrate validation framework with existing `DomainRegistry`
   - Leverage `DomainDetector` for automatic domain detection
   - Use existing `DOMAIN_CONFIGS` for validation rules

#### **Phase 2: Model Validation (Week 2)**
1. **Enhance Pydantic Models**
   - Add comprehensive field validators
   - Implement cross-field validation
   - Add custom validation methods

2. **Create Model Validators**
   - `OKHManifestValidator`
   - `ManufacturingFacilityValidator`
   - `SupplyTreeValidator`

#### **Phase 3: Service Validation (Week 3)**
1. **Business Rule Validators**
   - Equipment compatibility validation
   - Process capability validation
   - Material compatibility validation

2. **Domain-Specific Validators**
   - Manufacturing domain validators
   - Cooking domain validators
   - Context-aware validation

#### **Phase 4: API Integration (Week 4)**
1. **Update API Endpoints**
   - Integrate validation engine into all endpoints
   - Add validation context support
   - Implement consistent error handling

2. **File Upload Validation**
   - Comprehensive file validation
   - Content structure validation
   - Security validation

### **6. Validation Rules by Domain (Integrated with Existing System)**

#### **Manufacturing Domain Validation Rules**
```python
class ManufacturingValidationRules:
    """Validation rules for manufacturing domain - integrates with existing domain config"""
    
    @staticmethod
    def get_okh_validation_rules(quality_level: str = "professional") -> Dict[str, Any]:
        """Get OKH validation rules based on quality level"""
        base_rules = {
            'required_fields': ['title', 'version', 'license', 'licensor', 'documentation_language', 'function'],
            'quality_levels': ['hobby', 'professional', 'medical'],
            'validation_contexts': ['manufacturing', 'hobby', 'professional']
        }
        
        quality_specific = {
            'hobby': {
                'required_fields': base_rules['required_fields'],
                'optional_fields': ['description', 'keywords', 'manufacturing_processes'],
                'validation_strictness': 'relaxed'
            },
            'professional': {
                'required_fields': base_rules['required_fields'] + ['manufacturing_specs'],
                'optional_fields': ['description', 'keywords', 'quality_standards', 'certifications'],
                'validation_strictness': 'standard'
            },
            'medical': {
                'required_fields': base_rules['required_fields'] + ['manufacturing_specs', 'quality_standards'],
                'optional_fields': ['description', 'keywords', 'certifications', 'regulatory_compliance'],
                'validation_strictness': 'strict'
            }
        }
        
        return quality_specific.get(quality_level, quality_specific['professional'])
    
    @staticmethod
    def get_okw_validation_rules(quality_level: str = "professional") -> Dict[str, Any]:
        """Get OKW validation rules based on quality level"""
        base_rules = {
            'required_fields': ['name', 'location', 'facility_status'],
            'equipment_validation': {
                'required_fields': ['name', 'type'],
                'optional_fields': ['specifications', 'location', 'materials_worked']
            },
            'process_validation': {
                'valid_processes': [
                    'https://en.wikipedia.org/wiki/CNC_mill',
                    'https://en.wikipedia.org/wiki/3D_printing',
                    'https://en.wikipedia.org/wiki/CNC_lathe',
                    # ... other valid processes from existing domain config
                ]
            }
        }
        
        quality_specific = {
            'hobby': {
                'required_fields': base_rules['required_fields'],
                'optional_fields': ['equipment', 'manufacturing_processes', 'typical_materials'],
                'validation_strictness': 'relaxed'
            },
            'professional': {
                'required_fields': base_rules['required_fields'] + ['equipment', 'manufacturing_processes'],
                'optional_fields': ['typical_materials', 'certifications', 'quality_standards'],
                'validation_strictness': 'standard'
            },
            'medical': {
                'required_fields': base_rules['required_fields'] + ['equipment', 'manufacturing_processes', 'certifications'],
                'optional_fields': ['typical_materials', 'quality_standards', 'regulatory_compliance'],
                'validation_strictness': 'strict'
            }
        }
        
        return quality_specific.get(quality_level, quality_specific['professional'])
```

#### **Cooking Domain Validation Rules**
```python
class CookingValidationRules:
    """Validation rules for cooking domain - integrates with existing domain config"""
    
    @staticmethod
    def get_recipe_validation_rules(quality_level: str = "home") -> Dict[str, Any]:
        """Get recipe validation rules based on quality level"""
        base_rules = {
            'required_fields': ['name', 'ingredients', 'instructions'],
            'quality_levels': ['home', 'commercial', 'professional'],
            'validation_contexts': ['cooking', 'home', 'commercial']
        }
        
        quality_specific = {
            'home': {
                'required_fields': base_rules['required_fields'],
                'optional_fields': ['description', 'cooking_time', 'servings'],
                'validation_strictness': 'relaxed'
            },
            'commercial': {
                'required_fields': base_rules['required_fields'] + ['cooking_time', 'servings'],
                'optional_fields': ['description', 'nutritional_info', 'allergen_info'],
                'validation_strictness': 'standard'
            },
            'professional': {
                'required_fields': base_rules['required_fields'] + ['cooking_time', 'servings', 'nutritional_info'],
                'optional_fields': ['description', 'allergen_info', 'food_safety_notes'],
                'validation_strictness': 'strict'
            }
        }
        
        return quality_specific.get(quality_level, quality_specific['home'])
    
    @staticmethod
    def get_kitchen_validation_rules(quality_level: str = "home") -> Dict[str, Any]:
        """Get kitchen validation rules based on quality level"""
        base_rules = {
            'required_fields': ['name', 'location', 'equipment'],
            'equipment_validation': {
                'required_fields': ['name', 'type'],
                'optional_fields': ['specifications', 'capacity', 'features']
            }
        }
        
        quality_specific = {
            'home': {
                'required_fields': base_rules['required_fields'],
                'optional_fields': ['description', 'capacity', 'amenities'],
                'validation_strictness': 'relaxed'
            },
            'commercial': {
                'required_fields': base_rules['required_fields'] + ['capacity'],
                'optional_fields': ['description', 'amenities', 'certifications'],
                'validation_strictness': 'standard'
            },
            'professional': {
                'required_fields': base_rules['required_fields'] + ['capacity', 'certifications'],
                'optional_fields': ['description', 'amenities', 'food_safety_compliance'],
                'validation_strictness': 'strict'
            }
        }
        
        return quality_specific.get(quality_level, quality_specific['home'])
```

### **7. Integration with Existing Validation Endpoints**

#### **A. Leveraging Existing Validation Infrastructure**

The system already has validation endpoints that we can enhance:

1. **Existing Validation Endpoints**
   - `POST /v1/okh/validate` - OKH manifest validation
   - `POST /v1/okw/validate` - OKW facility validation (placeholder)
   - `POST /v1/match/validate` - Supply tree validation (placeholder)
   - `GET /v1/contexts/{domain}` - Domain validation contexts

2. **Enhancement Strategy**
   - Integrate new validation framework with existing endpoints
   - Add domain-aware validation context support
   - Implement quality-level validation
   - Add comprehensive error reporting

#### **B. Enhanced Validation Endpoint Implementation**
```python
@router.post("/validate", response_model=OKHValidationResponse)
async def validate_okh(
    request: OKHValidateRequest,
    validation_context: Optional[str] = Query(None, description="Validation context (e.g., 'manufacturing', 'hobby')"),
    quality_level: Optional[str] = Query("professional", description="Quality level (hobby, professional, medical)"),
    okh_service: OKHService = Depends(get_okh_service)
):
    """Enhanced OKH validation with domain-aware context"""
    try:
        # Create validation context
        context = ValidationContextFactory.create_context(
            domain_name="manufacturing",  # OKH is always manufacturing domain
            quality_level=quality_level,
            strict_mode=(quality_level == "medical")
        )
        
        # Use enhanced validation engine
        validation_engine = ValidationEngine()
        result = await validation_engine.validate(
            data=request.content,
            validation_type="okh_manifest",
            context=context
        )
        
        # Convert to response format
        return OKHValidationResponse(
            valid=result.valid,
            normalized_content=request.content,  # TODO: Implement normalization
            issues=[
                ValidationIssue(
                    severity="error" if not result.valid else "info",
                    message=error.message,
                    path=error.field.split('.') if error.field else []
                ) for error in result.errors
            ]
        )
        
    except Exception as e:
        logger.error(f"Error validating OKH manifest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while validating the OKH manifest"
        )
```

#### **C. Domain Context Integration**
```python
@router.get("/contexts/{domain}", response_model=ContextsResponse)
async def get_contexts(
    domain: str = Path(..., title="The domain to get contexts for"),
    filter_params: ContextFilterRequest = Depends()
):
    """Enhanced domain contexts with validation rules"""
    try:
        # Validate domain exists
        from src.core.registry.domain_registry import DomainRegistry
        if domain not in DomainRegistry.list_domains():
            raise HTTPException(
                status_code=404, 
                detail=f"Domain '{domain}' not found. Available domains: {DomainRegistry.list_domains()}"
            )
        
        # Get domain-specific validation contexts
        if domain == "manufacturing":
            contexts = [
                Context(
                    id="hobby",
                    name="Hobby Manufacturing",
                    description="Non-commercial, limited quality requirements",
                    validation_rules=ManufacturingValidationRules.get_okh_validation_rules("hobby")
                ),
                Context(
                    id="professional",
                    name="Professional Manufacturing",
                    description="Commercial-grade production",
                    validation_rules=ManufacturingValidationRules.get_okh_validation_rules("professional")
                ),
                Context(
                    id="medical",
                    name="Medical Manufacturing",
                    description="Medical device quality standards",
                    validation_rules=ManufacturingValidationRules.get_okh_validation_rules("medical")
                )
            ]
        elif domain == "cooking":
            contexts = [
                Context(
                    id="home",
                    name="Home Cooking",
                    description="Basic home kitchen capabilities",
                    validation_rules=CookingValidationRules.get_recipe_validation_rules("home")
                ),
                Context(
                    id="commercial",
                    name="Commercial Kitchen",
                    description="Professional kitchen capabilities",
                    validation_rules=CookingValidationRules.get_recipe_validation_rules("commercial")
                )
            ]
        else:
            contexts = []
        
        # Apply name filter if provided
        if filter_params.name:
            contexts = [c for c in contexts if filter_params.name.lower() in c.name.lower()]
        
        return ContextsResponse(contexts=contexts)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting contexts for domain {domain}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting validation contexts: {str(e)}"
        )
```

### **8. Error Handling Strategy**

#### **A. Error Response Format**
```json
{
  "error": {
    "code": "validation_failed",
    "message": "Validation failed for the provided data",
    "details": {
      "validation_type": "okh_manifest",
      "context": "manufacturing",
      "errors": [
        {
          "field": "manufacturing_specs",
          "code": "required_field_missing",
          "message": "Manufacturing specifications are required for professional quality level"
        }
      ],
      "warnings": [
        {
          "field": "description",
          "code": "recommended_field_missing",
          "message": "Description is recommended for better documentation"
        }
      ]
    }
  }
}
```

#### **B. HTTP Status Code Mapping**
- `400 Bad Request`: Input validation failures
- `422 Unprocessable Entity`: Business rule validation failures
- `409 Conflict`: Data integrity validation failures
- `413 Payload Too Large`: File size validation failures
- `415 Unsupported Media Type`: File type validation failures

### **7. Testing Strategy**

#### **A. Validation Testing**
1. **Unit Tests**
   - Test individual validators
   - Test validation contexts
   - Test error handling

2. **Integration Tests**
   - Test validation engine integration
   - Test API endpoint validation
   - Test cross-validator interactions

3. **End-to-End Tests**
   - Test complete validation workflows
   - Test error response formats
   - Test performance under load

#### **B. Test Data**
1. **Valid Test Data**
   - Complete, valid examples for each domain
   - Different quality levels and contexts

2. **Invalid Test Data**
   - Missing required fields
   - Invalid data types
   - Business rule violations

3. **Edge Cases**
   - Boundary values
   - Special characters
   - Large data sets

### **8. Migration Strategy**

#### **A. Backward Compatibility**
1. **Gradual Rollout**
   - Implement validation framework alongside existing code
   - Gradually migrate endpoints to use new validation
   - Maintain existing error formats during transition

2. **Feature Flags**
   - Use feature flags to enable/disable new validation
   - Allow per-endpoint validation control
   - Enable validation context switching

#### **B. Rollback Plan**
1. **Validation Bypass**
   - Ability to bypass validation for specific endpoints
   - Fallback to existing validation methods
   - Emergency validation disable

2. **Monitoring**
   - Track validation failure rates
   - Monitor API performance impact
   - Alert on validation errors

### **9. Performance Considerations**

#### **A. Validation Caching**
1. **Schema Caching**
   - Cache validation schemas
   - Cache validation contexts
   - Cache validation results for identical data

2. **Lazy Validation**
   - Validate only when needed
   - Defer expensive validations
   - Use async validation where possible

#### **B. Validation Optimization**
1. **Early Exit**
   - Stop validation on first critical error
   - Prioritize critical validations
   - Use validation shortcuts for common cases

2. **Batch Validation**
   - Validate multiple items together
   - Use bulk validation for file uploads
   - Optimize database validation queries

### **10. Monitoring and Observability**

#### **A. Validation Metrics**
1. **Success/Failure Rates**
   - Track validation success rates by endpoint
   - Monitor validation failure patterns
   - Alert on validation error spikes

2. **Performance Metrics**
   - Track validation execution time
   - Monitor validation memory usage
   - Measure validation throughput

#### **B. Validation Logging**
1. **Structured Logging**
   - Log validation attempts and results
   - Include validation context in logs
   - Track validation rule effectiveness

2. **Error Tracking**
   - Track validation error patterns
   - Monitor validation rule coverage
   - Identify validation gaps

## Implementation Priority

### **High Priority (Immediate)**
1. **Standardize Error Responses** - Critical for API consistency
2. **Create Validation Framework** - Foundation for all validation
3. **Fix Current Validation Issues** - Address existing problems

### **Medium Priority (Next 2 Weeks)**
4. **Implement Model Validators** - Core validation logic
5. **Add Business Rule Validation** - Domain-specific validation
6. **Update API Endpoints** - Integrate validation framework

### **Low Priority (Future)**
7. **Advanced Validation Features** - Context-aware validation
8. **Performance Optimization** - Caching and optimization
9. **Monitoring and Analytics** - Observability features

## Success Criteria

1. **Consistency**: All endpoints use the same validation approach
2. **Completeness**: All data flows have appropriate validation
3. **Performance**: Validation adds <100ms to API response times
4. **Usability**: Clear, actionable error messages for all validation failures
5. **Maintainability**: Easy to add new validation rules and contexts
6. **Reliability**: Validation failures are handled gracefully without system crashes

## Summary of Domain-Integrated Validation Strategy

### **Key Integration Points with Existing Domain System**

1. **DomainRegistry Integration**
   - Validation contexts must reference registered domains
   - Domain-specific validators retrieved from `DomainRegistry.get_domain_services()`
   - Domain metadata used for validation rule configuration

2. **DomainDetector Integration**
   - Automatic domain detection for validation context creation
   - Leverage existing domain detection confidence scoring
   - Use `DomainDetectionResult` for validation context selection

3. **Domain Configuration Integration**
   - Use `DOMAIN_CONFIGS` from `domains.py` for validation rules
   - Leverage `TYPE_DOMAIN_MAPPING` for automatic domain inference
   - Utilize `DOMAIN_KEYWORDS` for content-based validation

4. **Existing Validation Endpoint Enhancement**
   - Enhance existing `/v1/okh/validate`, `/v1/okw/validate`, `/v1/match/validate` endpoints
   - Add domain-aware validation context support
   - Implement quality-level validation (hobby, professional, medical)

### **Benefits of Domain Integration**

1. **Consistency** - Validation rules align with existing domain architecture
2. **Extensibility** - Easy to add new domains with their own validation rules
3. **Automatic Detection** - Leverage existing domain detection for validation context
4. **Backward Compatibility** - Enhance existing endpoints without breaking changes
5. **Centralized Management** - Domain validation rules managed through existing domain system

### **Implementation Priority (Updated)**

**Phase 1: Domain-Integrated Foundation**
1. Create `ValidationEngine` integrated with `DomainRegistry`
2. Implement `ValidationContext` with domain validation
3. Create `ValidationContextFactory` for domain-aware context creation
4. Standardize error responses across all endpoints

**Phase 2: Domain-Specific Validation Rules**
1. Implement `ManufacturingValidationRules` for OKH/OKW validation
2. Implement `CookingValidationRules` for recipe/kitchen validation
3. Create domain-specific validators that integrate with existing domain services

**Phase 3: Enhanced Validation Endpoints**
1. Enhance existing validation endpoints with domain-aware validation
2. Add quality-level validation support
3. Implement comprehensive error reporting

**Phase 4: Advanced Features**
1. Add validation caching and performance optimization
2. Implement validation monitoring and analytics
3. Add validation rule versioning and migration support

## Next Steps

1. **Review and Approve Strategy** - Get team buy-in on domain-integrated approach
2. **Create Implementation Plan** - Detailed task breakdown with domain integration
3. **Set Up Development Environment** - Validation framework setup with domain dependencies
4. **Begin Phase 1 Implementation** - Domain-integrated foundation and error standardization
5. **Create Test Suite** - Comprehensive validation testing with domain scenarios
6. **Documentation** - Update API documentation with domain-aware validation details
