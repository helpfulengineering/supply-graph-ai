# Open Matching Engine (OME) - Developer Documentation

## Recent Design Decisions

### 1. Requirements Flexibility

The system now distinguishes between hard and soft requirements for manufacturing processes. This distinction is crucial for real-world manufacturing scenarios where some processes require exact replication while others can be more flexible.

#### Hard Requirements
- Must be followed exactly as specified
- Include precise tolerances and equipment specifications
- Used for safety-critical or quality-sensitive processes
- Validated against specific standards (ISO, ANSI, etc.)

#### Soft Requirements
- Specify desired outcomes rather than exact processes
- Allow flexibility in implementation
- Include input/output state requirements
- Support human-readable general instructions

### 2. Workflow Ports

Workflows now have explicit input and output ports to better manage and validate the flow of materials and components between processes.

#### Key Features
- Type checking between connected ports
- Validation of materials/components passing through ports
- Clear interface boundaries between workflows
- Support for quantity tracking

### 3. Parallel Processing Support

The system supports parallel manufacturing processes through metadata labels and scheduling hints, similar to Kubernetes resource labels.

#### Implementation
- Non-prescriptive approach using metadata
- Flexible scheduling hints for optimization
- Support for batch processing
- Facility-specific parallelization capabilities

## Class Documentation

### Requirements System

# Open Matching Engine (OME) - Developer Documentation

## Process Requirements System

### Overview

The OME uses a context-aware requirements system that allows the same basic requirements to be interpreted and validated differently based on their usage context. This enables a single Supply Tree to be evaluated for different purposes with different acceptance criteria.

### Core Classes

```python
@dataclass
class ValidationContext:
    """
    Defines how requirements should be validated in a specific context.
    
    Attributes:
        domain (str): The domain this context applies to (e.g., "medical", "consumer")
        standards (List[str]): Applicable standards (e.g., "ISO 13485")
        acceptance_criteria (Dict[str, Any]): Context-specific thresholds
        validation_procedures (Dict[str, Callable]): Validation implementations
    
    Notes:
        - Domains should use standardized names when possible
        - Standards should reference official designations
        - Acceptance criteria should be measurable
    """

@dataclass
class ValidationFailureResponse:
    """
    Defines the consequences and handling of validation failures.
    
    Attributes:
        severity (float): 0.0 to 1.0 scale of failure severity
        remediation_options (List[str]): Possible remediation steps
        blocking (bool): Whether this failure blocks the entire supply tree
        reroute_options (Optional[List[str]]): Alternative paths to try
    
    Notes:
        - severity = 0.0: Negligible impact
        - severity = 1.0: Critical failure
        - Set blocking=True for safety-critical requirements
    """

@dataclass
class ProcessRequirement:
    """
    Defines a requirement with context-specific validation.
    
    Attributes:
        specification (Union[ExactProcessSpec, ProcessConstraints]): 
            What needs to be true
        validation_contexts (Dict[str, ValidationContext]): 
            How to validate in different contexts
        failure_responses (Dict[str, ValidationFailureResponse]): 
            What happens on validation failure
    
    Default Behavior:
        - If no validation_contexts specified, accepts any value
        - If no failure_responses specified, treats failures as non-blocking
    """
```

### Integration with Supply Tree

The Supply Tree structure uses ProcessRequirements at multiple levels:

1. **Node Level**
   ```python
   @dataclass
   class WorkflowNode:
       """
       Node in a manufacturing workflow.
       
       Attributes:
           requirements (List[ProcessRequirement]): Requirements for this step
           context_id (Optional[str]): Current validation context
       """
       requirements: List[ProcessRequirement] = field(default_factory=list)
       context_id: Optional[str] = None
       
       def validate(self, context_id: Optional[str] = None) -> bool:
           """
           Validate node requirements in given context.
           Falls back to permissive defaults if no context specified.
           """
           if not self.requirements:
               return True  # No requirements = automatically valid
           
           ctx = context_id or self.context_id
           if not ctx:
               return True  # No context = permissive validation
           
           return all(req.validate(ctx) for req in self.requirements)
   ```

2. **Workflow Level**
   ```python
   @dataclass
   class Workflow:
       """
       Represents a manufacturing workflow.
       
       Attributes:
           requirements (List[ProcessRequirement]): Workflow-wide requirements
           context_id (Optional[str]): Default context for this workflow
       """
       def validate_in_context(self, context_id: str) -> bool:
           """
           Validate entire workflow in a specific context.
           """
           # Validate workflow-level requirements
           if not all(req.validate(context_id) for req in self.requirements):
               return False
           
           # Validate all nodes
           return all(node.validate(context_id) for node in self.nodes)
   ```

3. **Supply Tree Level**
   ```python
   @dataclass
   class SupplyTree:
       """
       Container for interconnected manufacturing workflows.
       
       Attributes:
           global_requirements (List[ProcessRequirement]): Tree-wide requirements
           default_context (Optional[str]): Default validation context
       """
       def validate_solution(self, context_id: Optional[str] = None) -> bool:
           """
           Validate entire solution in a specific context.
           Uses default_context if none specified.
           """
           ctx = context_id or self.default_context
           
           # Start with global requirements
           if ctx and not all(req.validate(ctx) for req in self.global_requirements):
               return False
           
           # Validate all workflows
           return all(wf.validate_in_context(ctx) for wf in self.workflows.values())
   ```

### Default Behavior

The system is designed to be permissive by default:

1. **No Requirements**
   - Nodes/workflows with no requirements are considered valid
   - Empty validation_contexts means no validation needed
   - Empty failure_responses means failures are non-blocking

2. **No Context**
   - If no context_id is specified, validation is permissive
   - Default context can be set at tree level and overridden lower
   - Multiple contexts can be validated separately

3. **Failure Handling**
   - By default, failures are non-blocking (severity = 0.0)
   - Default remediation is to continue with warnings
   - Explicit failure responses needed for blocking behavior

### Example Usage

```python
# Define a permissive requirement
basic_req = ProcessRequirement(
    specification=ProcessConstraints(
        input_state={"material": "wood"},
        output_state={"shape": "rectangular"},
        allowed_methods=["any"]
    ),
    validation_contexts={},  # No specific validation
    failure_responses={}     # Non-blocking failures
)

# Same requirement with strict medical context
medical_req = ProcessRequirement(
    specification=ProcessConstraints(
        input_state={"material": "medical_grade_steel"},
        output_state={"shape": "rectangular"},
        allowed_methods=["certified_process_only"]
    ),
    validation_contexts={
        "medical": ValidationContext(
            domain="medical",
            standards=["ISO 13485"],
            acceptance_criteria={"sterility": "surgical_grade"},
            validation_procedures={"sterility_test": sterility_validator}
        )
    },
    failure_responses={
        "medical": ValidationFailureResponse(
            severity=1.0,
            remediation_options=[],
            blocking=True,
            reroute_options=None
        )
    }
)

# Create nodes with different requirements
permissive_node = WorkflowNode(requirements=[basic_req])
strict_node = WorkflowNode(requirements=[medical_req], context_id="medical")

# Validate in different contexts
permissive_node.validate()  # True (permissive default)
strict_node.validate("medical")  # False if medical criteria not met
```

### Best Practices

1. **Requirements Definition**
   - Be explicit about validation needs
   - Use standard references where possible
   - Document acceptance criteria clearly
   - Consider failure consequences

2. **Context Management**
   - Use consistent context naming
   - Document context relationships
   - Consider context inheritance
   - Plan for multiple contexts

3. **Validation Implementation**
   - Implement reusable validators
   - Handle edge cases gracefully
   - Log validation failures
   - Provide clear error messages

4. **Supply Tree Integration**
   - Consider requirement scope
   - Use appropriate requirement level
   - Plan validation strategy
   - Document context usage

### Future Considerations

1. **Context Inheritance**
   - Hierarchy of validation contexts
   - Requirement inheritance
   - Context composition

2. **Validation Optimization**
   - Caching validation results
   - Parallel validation
   - Incremental validation

3. **Advanced Routing**
   - Context-aware path finding
   - Multi-context optimization
   - Failure recovery strategies

### Port System

```python
@dataclass
class Port:
    """
    Represents an input or output connection point for a workflow.
    
    Attributes:
        id (UUID): Unique identifier for the port
        name (str): Human-readable name
        type (str): Type of items passing through port
        specification (Dict): Expected properties of items
        validators (List[PortValidator]): Validation rules
        
    Example:
        ```python
        # Output port for finished chair legs
        leg_output = Port(
            name="finished_legs",
            type="component",
            specification={
                "component_type": "chair_leg",
                "material": "wood",
                "length": "45cm",
                "finish": "sanded"
            },
            validators=[
                DimensionValidator(tolerance=0.5),
                MaterialValidator(allowed_materials=["oak", "maple"])
            ]
        )
        ```
    """
```

### Parallel Processing System

```python
@dataclass
class WorkflowMetadata:
    """
    Metadata about workflow execution capabilities and requirements.
    
    Attributes:
        labels (Dict[str, str]): Key-value pairs for workflow classification
        annotations (Dict[str, str]): Additional descriptive metadata
        scheduling_hints (Dict[str, any]): Optimization hints for execution
        
    Label Conventions:
        parallel.ome.org/type: Type of parallelizable unit
        parallel.ome.org/batch: Whether batch processing is allowed
        parallel.ome.org/dependencies: Dependency requirements
        
    Example:
        ```python
        # Metadata for parallel leg manufacturing
        leg_metadata = WorkflowMetadata(
            labels={
                "parallel.ome.org/type": "component",
                "parallel.ome.org/batch": "true"
            },
            scheduling_hints={
                "max_parallel": 4,
                "min_batch_size": 1,
                "optimal_batch_size": 4
            }
        )
        ```
    """
```

## Implementation Guidelines

### 1. Requirement Handling

When implementing requirements:
- Clearly document which requirements are HARD vs SOFT
- Include validation methods for each requirement type
- Provide clear error messages for requirement violations
- Consider adding requirement inheritance/composition

### 2. Port Implementation

When implementing ports:
- Use strong type checking between connected ports
- Implement robust validation systems
- Consider buffering/queueing requirements
- Handle quantity tracking carefully

### 3. Parallel Processing

When implementing parallel processing:
- Keep implementation flexible and non-prescriptive
- Document all supported metadata labels
- Consider facility capabilities in scheduling
- Implement clear dependency management

## Future Considerations

### 1. Material Routing
- Future enhancement for material logistics
- Facility-level responsibility
- Optional capability
- Consider integration with external logistics systems

### 2. Validation Enhancement
- Add support for custom validation rules
- Implement validation rule composition
- Consider validation performance optimization
- Add support for validation reporting

### 3. Scheduling Optimization
- Enhanced parallel processing optimization
- Resource utilization improvements
- Cost optimization algorithms
- Time optimization strategies

## Contributing

When contributing to these systems:

1. Documentation
   - Update class documentation
   - Provide clear examples
   - Document edge cases
   - Update this developer guide

2. Testing
   - Add unit tests for new features
   - Include integration tests
   - Test edge cases
   - Document test scenarios

3. Code Style
   - Follow existing patterns
   - Use type hints
   - Document complex logic
   - Keep methods focused and small

## Best Practices

1. Requirement Definition
   - Be explicit about HARD vs SOFT requirements
   - Include clear validation criteria
   - Document assumptions
   - Provide examples

2. Port Design
   - Keep port interfaces clean
   - Validate early and often
   - Handle errors gracefully
   - Document port contracts

3. Parallel Processing
   - Use standard label formats
   - Document scheduling hints
   - Consider resource constraints
   - Handle failures appropriately