# Supply Trees

## Overview

A Supply Tree is a data structure representing a complete manufacturing solution that maps requirements (specified in OKH) to available capabilities (specified in OKW). It consists of multiple connected workflows, each represented as a Directed Acyclic Graph (DAG), that together define how a specified quantity of objects can be manufactured.
It captures all possible ways to manufacture a specified quantity of objects, including the facilities, materials, steps, and dependencies involved.

## Core Concepts

### 1. Supply Tree
- Represents a complete manufacturing solution
- Can have multiple branches representing parallel processes
- Has a defined depth (n) representing steps from raw materials to final product
- Must support evaluation and comparison of different solutions
- Should capture both successful paths and alternative routes

### 2. Nodes
Each node in the tree represents a manufacturing stage and must capture:

**Required Properties:**
- Location (reference to OKW facility)
- Input materials/components (with quantities)
- Output materials/components (with quantities)
- Process steps being performed
- Equipment requirements
- Time requirements
- Quality/certification requirements
 
**Optional Properties:**
- Cost factors
- Energy requirements
- Skill requirements
- Environmental impact factors

### 3. Dependencies
The structure must represent various types of dependencies:

**Process Dependencies:**
- Sequential steps (must happen in order)
- Parallel processes (can happen simultaneously)
- Optional processes
- Alternative processes

**Resource Dependencies:**
- Material requirements
- Equipment requirements
- Facility capabilities
- Human skill requirements

### 4. Metadata Layer
A wrapper around nodes that captures:

**Routing Logic:**
- Alternative paths
- Fallback options
- Retry strategies
- Failure handling

**Quality Metrics:**
- Complexity measures
- Cost factors
- Time efficiency
- Resource utilization
- Environmental impact

## Technical Requirements

### 1. Data Structure Properties

**Must Have:**
- Self-contained (includes all necessary information for manufacturing)
- Traversable (can walk the tree to analyze paths)
- Serializable (can be stored and transmitted)
- Immutable (solutions should be reproducible)

**Should Have:**
- Efficient storage
- Fast traversal
- Easy comparison between trees
- Version control friendly format

### 2. Operations

The structure must support:

**Analysis Operations:**
- Find all possible manufacturing paths
- Calculate total cost/time/resources for a path
- Identify bottlenecks and dependencies
- Compare different solutions
- Validate manufacturing feasibility

**Query Operations:**
- Find nodes by facility
- Find nodes by process type
- Find nodes by material
- Find alternative paths
- Find optimal solutions based on criteria

### 3. Integration Requirements

**Must integrate with:**
- OpenKnowHow (OKH) specification format
- OpenKnowWhere (OKW) specification format
- Standard workflow representations
- Common serialization formats

## Use Cases

### 1. Basic Manufacturing
Example: Simple product assembly from available components
- Depth 0: Final assembly facility
- Depth 1: Component suppliers

### 2. Complex Manufacturing
Example: Custom product requiring component fabrication
- Depth 0: Final assembly
- Depth 1: Component fabrication
- Depth 2: Raw material processing

### 3. Cooking Domain (Test Implementation)
Example: Restaurant meal preparation
- Depth 0: Kitchen preparing the meal
- Depth 1: Ingredient suppliers
- Depth 2: Raw ingredient processors


## Success Criteria

A successful implementation must:

1. Accurately represent all possible manufacturing solutions
2. Support efficient comparison between different solutions
3. Enable easy validation of manufacturing feasibility
4. Scale well with increasing manufacturing complexity
5. Support addition of new metrics and evaluation criteria
6. Maintain clarity and usability for both simple and complex cases


## Core Classes

### Supply Tree
```python
@dataclass
class SupplyTree:
    """Container for interconnected manufacturing workflows"""
    id: UUID
    workflows: Dict[UUID, Workflow]
    connections: List[WorkflowConnection]
    snapshots: Dict[str, ResourceSnapshot]
    creation_time: datetime
    metadata: Dict
```

The main container class managing the complete manufacturing solution. Key operations:
- `add_workflow(workflow)`: Add a validated workflow
- `connect_workflows(connection)`: Connect two workflows
- `add_snapshot(uri, content)`: Store OKH/OKW data snapshot
- `validate_current(okh_data, okw_data)`: Validate against current data
- `validate_snapshot()`: Validate against stored snapshots

### Workflow
```python
@dataclass
class Workflow:
    """Represents a discrete manufacturing workflow as a DAG"""
    id: UUID
    name: str
    graph: nx.DiGraph            # NetworkX DiGraph
    entry_points: Set[UUID]      # Start nodes
    exit_points: Set[UUID]       # End nodes
```

Represents a discrete manufacturing process. Key features:
- Uses NetworkX DiGraph for graph operations
- Tracks entry and exit points explicitly
- Validates graph is acyclic
- Manages node dependencies

### Workflow Node
```python
@dataclass
class WorkflowNode:
    """Node representing a step in a manufacturing workflow"""
    id: UUID
    name: str
    okh_refs: List[ResourceURI]  # What needs to be done
    okw_refs: List[ResourceURI]  # Where it can be done
    input_requirements: Dict[str, any]
    output_specifications: Dict[str, any]
    estimated_time: timedelta
    metadata: Dict
```

Represents a specific manufacturing step with:
- References to OKH requirements
- References to OKW capabilities
- Input/output specifications
- Timing information

### Workflow Connection
```python
@dataclass
class WorkflowConnection:
    """Defines a connection between two workflows"""
    source_workflow: UUID
    source_node: UUID
    target_workflow: UUID
    target_node: UUID
    connection_type: str        # e.g., "assembly", "component", "material"
    metadata: Dict
```

Defines how workflows connect, supporting:
- Component assembly
- Material flow
- Process dependencies

### Resource References

#### Resource URI
```python
@dataclass
class ResourceURI:
    """Standardized reference to OKH/OKW resources"""
    resource_type: ResourceType  # OKH or OKW
    identifier: str
    path: List[str]
    fragment: Optional[str]
```

Provides standardized references to OKH/OKW data:
- URI format: `{type}://{identifier}/{path}#{fragment}`
- Example: `okh://part-123/process/milling#tolerance`

#### Resource Snapshot
```python
@dataclass
class ResourceSnapshot:
    """Snapshot of OKH/OKW data at a point in time"""
    uri: ResourceURI
    content: Dict
    timestamp: datetime
    version: Optional[str]
```

Stores point-in-time data for validation:
- Complete content at time of creation
- Timestamp for versioning
- Accessor methods for referenced data

## Process Status and Requirements

### Process Status
```python
class ProcessStatus(Enum):
    """Status of a manufacturing process node"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
```

### Process Requirements
```python
@dataclass
class ProcessRequirement:
    """Requirements for a specific manufacturing process"""
    wikipedia_url: str            # Standard process classification
    equipment_required: List[str]  # Equipment Wikipedia URLs
    materials_required: List[str]  # Material Wikipedia URLs
    estimated_time: timedelta
    batch_size_min: int
    batch_size_max: Optional[int]
    quality_standards: List[str]   # ISO/ANSI refs
    skill_requirements: List[str]
```

## Error Handling

### Circular Dependencies
```python
@dataclass
class CircularDependencyError:
    """Represents a detected circular dependency"""
    node_a: ProcessNode
    node_b: ProcessNode
    required_input: Optional[str]  # What input would resolve the circle
```

## Solution Representation

```python
@dataclass
class SupplyTreeSolution:
    """A scored manufacturing solution"""
    tree: SupplyTree
    score: float
    metrics: Dict[str, Union[float, str, timedelta]]
```

Represents a complete, evaluated solution:
- Contains the full Supply Tree
- Includes solution score
- Tracks performance metrics

## Serialization

Supply Trees support full serialization:
- `to_dict()`: Convert to serializable dictionary
- `from_dict()`: Reconstruct from dictionary
- Handles graph serialization via NetworkX
- Preserves all references and metadata

## Usage Examples

### Creating a Basic Supply Tree
```python
# Create workflows
workflow1 = Workflow(name="Component Manufacturing")
workflow2 = Workflow(name="Assembly")

# Add nodes to workflows
node1 = WorkflowNode(
    name="Manufacture Part A",
    okh_refs=[ResourceURI.from_string("okh://part-a/process")],
    okw_refs=[ResourceURI.from_string("okw://facility-1/capabilities")]
)
workflow1.add_node(node1)

# Create supply tree
supply_tree = SupplyTree()
supply_tree.add_workflow(workflow1)
supply_tree.add_workflow(workflow2)

# Connect workflows
connection = WorkflowConnection(
    source_workflow=workflow1.id,
    source_node=node1.id,
    target_workflow=workflow2.id,
    target_node=assembly_node.id,
    connection_type="component"
)
supply_tree.connect_workflows(connection)
```

### Working with Snapshots
```python
# Add OKH/OKW snapshots
supply_tree.add_snapshot(
    "okh://part-a/process",
    {"process": "milling", "parameters": {...}}
)

# Validate against snapshots
is_valid = supply_tree.validate_snapshot()
```

## Best Practices

1. **Workflow Management**
   - Keep workflows focused and coherent
   - Validate before adding to tree
   - Maintain clear entry/exit points

2. **Resource References**
   - Use standardized URIs
   - Keep snapshots up to date
   - Validate references exist

3. **Connection Management**
   - Validate node existence
   - Use appropriate connection types
   - Include relevant metadata

4. **Error Handling**
   - Check for circular dependencies
   - Validate workflow integrity
   - Handle missing references

## Implementation Notes

1. **Graph Operations**
   - Uses NetworkX for graph operations
   - Ensures DAG properties
   - Supports efficient traversal

2. **Validation**
   - Multiple validation levels
   - Current state vs snapshots
   - Reference integrity checking

3. **Serialization**
   - Complete state preservation
   - Handle graph structures
   - Maintain references