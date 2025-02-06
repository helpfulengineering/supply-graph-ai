# Validation Contexts

## Overview

Validation Contexts define how Process Requirements should be validated in specific use cases. They enable the same basic process to be validated differently based on its intended use, ensuring appropriate standards are met while maintaining flexibility in the manufacturing system.

## Core Concepts

### 1. Context Definition
```python
@dataclass
class ValidationContext:
    """Defines validation requirements for a specific use context"""
    domain: str                          # Domain of use (e.g., "medical", "hobby")
    standards: List[str]                 # Applicable standards (e.g., ISO, ASTM)
    acceptance_criteria: Dict[str, Any]   # Specific thresholds and requirements
    validation_procedures: Dict[str, Callable]  # How to validate
```

### 2. Validation Failure Handling
```python
@dataclass
class ValidationFailureResponse:
    """Defines what happens when validation fails"""
    severity: float                      # 0.0 to 1.0
    remediation_options: List[str]       # Possible fixes
    blocking: bool                       # Does this block the supply tree?
    reroute_options: Optional[List[str]] # Alternative paths
```

## Example: Multiple Contexts for Steel Knife

### 1. Hobby Context
```python
hobby_context = ValidationContext(
    domain="hobby_knife_making",
    standards=[
        "AISI_steel_grades"
    ],
    acceptance_criteria={
        "hardness_test": {
            "method": "rockwell_c",
            "min": 58,
            "max": 61,
            "sample_size": "single_point"
        },
        "edge_geometry": {
            "method": "angle_measurement",
            "tolerance": "±3_degrees"
        }
    },
    validation_procedures={
        "material_validation": lambda x: x["material_grade"] in ["1075", "1084", "1095"],
        "hardness_validation": lambda x: 58 <= x["hardness"] <= 61
    }
)

hobby_failure = ValidationFailureResponse(
    severity=0.5,                # Medium severity
    remediation_options=[
        "verify_steel_grade",
        "adjust_heat_treatment",
        "retry_hardness_test"
    ],
    blocking=False,             # Can attempt remediation
    reroute_options=[
        "alternative_steel_grade"
    ]
)
```

### 2. Medical Context
```python
surgical_context = ValidationContext(
    domain="medical_devices",
    standards=[
        "ISO_13485",
        "ASTM_F899",
        "ISO_7153-1"
    ],
    acceptance_criteria={
        "material_certification": {
            "method": "documentation_review",
            "requirements": [
                "material_cert",
                "processing_history",
                "batch_traceability"
            ]
        },
        "hardness_test": {
            "method": "rockwell_c",
            "min": 54,
            "max": 56,
            "sample_size": "100%"
        },
        "surface_finish": {
            "method": "profilometer",
            "max_roughness": "0.1μm"
        }
    },
    validation_procedures={
        "material_validation": lambda x: (
            x["material_grade"] in ["440A", "420HC"] and 
            x["certification"] == "medical_grade"
        ),
        "sterility_validation": lambda x: x["sterility_level"] == "surgical_grade"
    }
)

surgical_failure = ValidationFailureResponse(
    severity=1.0,              # Maximum severity
    remediation_options=[],    # No remediation allowed
    blocking=True,             # Fails entire supply tree
    reroute_options=None       # No alternatives
)
```

## Integration with Process Requirements

### 1. Context-Aware Validation
```python
@dataclass
class ProcessRequirement:
    """Process requirement with context-specific validation"""
    specification: Union[ExactProcessSpec, ProcessConstraints]
    validation_contexts: Dict[str, ValidationContext]
    failure_responses: Dict[str, ValidationFailureResponse]
    
    def validate(self, context_id: str, actual_state: Any) -> ValidationResult:
        """Validate this requirement in a specific context"""
        context = self.validation_contexts[context_id]
        
        # Apply context-specific validation procedures
        results = []
        for proc_name, proc in context.validation_procedures.items():
            result = proc(actual_state)
            results.append(result)
            
        # Handle validation failures
        if not all(results):
            return self.handle_failure(context_id, results)
            
        return ValidationResult(valid=True, context=context_id)
```

### 2. Supply Tree Integration
```python
class SupplyTree:
    """Manufacturing solution with context validation"""
    def validate_in_context(self, context_id: str) -> bool:
        """Validate entire solution in a specific context"""
        for workflow in self.workflows.values():
            for node in workflow.nodes:
                for req in node.requirements:
                    if not req.validate(context_id, node.actual_state):
                        return False
        return True
```

## Context Inheritance and Composition

### 1. Base Contexts
```python
@dataclass
class BaseContext:
    """Base validation context that can be extended"""
    standards: List[str]
    base_criteria: Dict[str, Any]
    base_procedures: Dict[str, Callable]

manufacturing_base = BaseContext(
    standards=["ISO_9001"],
    base_criteria={
        "documentation": "required",
        "traceability": "batch_level"
    },
    base_procedures={
        "basic_validation": standard_validation_procedure
    }
)
```

### 2. Extended Contexts
```python
def extend_context(base: BaseContext, 
                  extensions: Dict[str, Any]) -> ValidationContext:
    """Create new context extending a base context"""
    return ValidationContext(
        standards=[*base.standards, *extensions.get('standards', [])],
        acceptance_criteria={
            **base.base_criteria,
            **extensions.get('criteria', {})
        },
        validation_procedures={
            **base.base_procedures,
            **extensions.get('procedures', {})
        }
    )
```

## Best Practices

### 1. Context Definition
- Be explicit about standards
- Define clear acceptance criteria
- Implement robust validation procedures
- Document context requirements

### 2. Failure Handling
- Define appropriate severity levels
- Provide clear remediation paths
- Consider blocking vs. non-blocking failures
- Document rerouting options

### 3. Validation Implementation
- Use measurable criteria
- Implement reliable procedures
- Handle edge cases
- Maintain audit trails

### 4. Context Management
- Use standard references
- Support context inheritance
- Enable context composition
- Document context relationships

## Implementation Considerations

### 1. Validation Performance
- Efficient procedure implementation
- Caching validation results
- Parallel validation where possible
- Smart revalidation strategies

### 2. Context Flexibility
- Support multiple standards
- Allow procedure overrides
- Enable context composition
- Manage context versions

### 3. Documentation
- Record validation results
- Maintain audit trails
- Track context changes
- Document failures and resolutions

## Future Extensions

### 1. Advanced Validation
- Machine learning validation
- Automated testing
- Real-time monitoring
- Predictive validation

### 2. Context Management
- Dynamic context creation
- Context version control
- Context compatibility checking
- Context optimization

### 3. Integration
- External standard integration
- Certification system integration
- Quality management integration
- Compliance system integration