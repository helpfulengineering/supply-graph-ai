# Supply Trees

## Overview

A Supply Tree is a data structure representing a complete manufacturing solution that maps requirements (specified in OKH) to available capabilities (specified in OKW). It consists of multiple connected workflows, each represented as a Directed Acyclic Graph (DAG), that together define how a specified quantity of objects can be manufactured.

## Core Concepts

### 1. Supply Tree
The Supply Tree is the top-level container that represents a complete manufacturing solution. Key properties:
- Holds multiple related workflows
- Tracks connections between workflows
- Maintains snapshots of source data (OKH/OKW)
- Supports validation and serialization
- Contains metadata for tracking and evaluation

### 2. Workflows
Each workflow in a Supply Tree represents a distinct manufacturing process:
- Implemented as a Directed Acyclic Graph (DAG)
- Contains nodes representing process steps
- Tracks entry and exit points
- Enforces dependency relationships
- Can be executed independently or as part of the larger solution

### 3. Workflow Nodes
Nodes represent individual manufacturing steps and contain:
- References to OKH requirements (what needs to be done)
- References to OKW capabilities (where it can be done)
- Input/output specifications
- Timing information
- Status tracking
- Confidence scores for matching quality

### 4. Workflow Connections
Connections define the relationships between workflows:
- Link output of one workflow to input of another
- Define assembly relationships
- Establish material flows
- Create process dependencies

### 5. Resource References
The Supply Tree uses a standardized URI system to reference OKH requirements and OKW capabilities:
- Format: `{type}://{identifier}/{path}#{fragment}`
- Examples: 
  - `okh://part-123/process/milling#tolerance`
  - `okw://facility-456/equipment/cnc-mill-1`
- Support for different resource types (OKH, OKW, domain-specific)

## Core Classes

### ResourceType Enum
```python
class ResourceType(Enum):
    """Resource types that can be referenced in a Supply Tree"""
    OKH = "okh"                      # OpenKnowHow manifest
    OKH_PROCESS = "okh_process"      # OKH process requirement
    OKH_MATERIAL = "okh_material"    # OKH material specification
    OKH_PART = "okh_part"            # OKH part specification
    OKW = "okw"                      # OpenKnowWhere facility
    OKW_EQUIPMENT = "okw_equipment"  # OKW equipment
    OKW_PROCESS = "okw_process"      # OKW manufacturing process
    RECIPE = "recipe"                # Cooking domain recipe
    KITCHEN = "kitchen"              # Cooking domain kitchen
```

### ResourceURI
```python
@dataclass
class ResourceURI:
    """Standardized reference to OKH/OKW resources"""
    resource_type: ResourceType
    identifier: str
    path: List[str]
    fragment: Optional[str] = None
    
    def __str__(self) -> str:
        """Convert to URI string"""
        path_str = "/".join(self.path)
        base = f"{self.resource_type.value}://{self.identifier}/{path_str}"
        return f"{base}#{self.fragment}" if self.fragment else base
    
    @classmethod
    def from_string(cls, uri_str: str) -> 'ResourceURI':
        """Parse URI string into ResourceURI object"""
        # Parse uri_str like "okh://part-123/process/milling#tolerance"
        scheme, rest = uri_str.split("://", 1)
        
        # Handle resource type
        try:
            resource_type = ResourceType(scheme)
        except ValueError:
            # For backward compatibility
            resource_type = ResourceType.OKH if scheme == "okh" else ResourceType.OKW
        
        # Split identifier and path
        parts = rest.split("/")
        identifier = parts[0]
        
        # Handle fragment if present
        path_str = "/".join(parts[1:])
        if "#" in path_str:
            path_str, fragment = path_str.split("#", 1)
        else:
            fragment = None
            
        path = path_str.split("/") if path_str else []
        
        return cls(
            resource_type=resource_type,
            identifier=identifier,
            path=path,
            fragment=fragment
        )
```

### ResourceSnapshot
```python
@dataclass
class ResourceSnapshot:
    """Snapshot of OKH/OKW data at a point in time"""
    uri: ResourceURI
    content: Dict
    timestamp: datetime = field(default_factory=datetime.now)
    version: Optional[str] = None
    
    def get_value(self) -> Optional[any]:
        """Get value at path specified in URI"""
        current = self.content
        for key in self.uri.path:
            if key not in current:
                return None
            current = current[key]
        
        if self.uri.fragment:
            return current.get(self.uri.fragment)
        return current
```

### ProcessStatus
```python
class ProcessStatus(Enum):
    """Status of a manufacturing process node"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
```

### WorkflowNode
```python
@dataclass
class WorkflowNode:
    """Node representing a step in a manufacturing workflow"""
    name: str
    id: UUID = field(default_factory=uuid4)
    okh_refs: List[ResourceURI] = field(default_factory=list)  # What needs to be done
    okw_refs: List[ResourceURI] = field(default_factory=list)  # Where it can be done
    input_requirements: Dict[str, any] = field(default_factory=dict)
    output_specifications: Dict[str, any] = field(default_factory=dict)
    estimated_time: timedelta = field(default_factory=lambda: timedelta())
    process_status: ProcessStatus = ProcessStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    assigned_facility: Optional[str] = None  # UUID of manufacturing facility
    assigned_equipment: Optional[str] = None  # UUID of equipment
    materials: List[str] = field(default_factory=list)  # Material references
    metadata: Dict = field(default_factory=dict)
    confidence_score: float = 1.0  # Confidence in this node's match
    substitution_used: bool = False  # Whether this uses a substitution
```

### Workflow
```python
@dataclass
class Workflow:
    """Represents a discrete manufacturing workflow as a DAG"""
    name: str
    id: UUID = field(default_factory=uuid4)
    graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    entry_points: Set[UUID] = field(default_factory=set)  # Nodes that start the workflow
    exit_points: Set[UUID] = field(default_factory=set)   # Nodes that end the workflow
    
    def add_node(self, node: WorkflowNode, dependencies: Set[UUID] = None) -> None:
        """Add a node to the workflow"""
        self.graph.add_node(node.id, data=node)
        
        # Add dependencies if specified
        if dependencies:
            for dep_id in dependencies:
                if dep_id not in self.graph.nodes:
                    raise ValueError(f"Dependency {dep_id} not found in workflow")
                self.graph.add_edge(dep_id, node.id)
        
        # Update entry/exit points
        if not dependencies:
            self.entry_points.add(node.id)
        
        self.exit_points.add(node.id)
        for dep_id in (dependencies or set()):
            if dep_id in self.exit_points:
                self.exit_points.discard(dep_id)
    
    def validate(self) -> bool:
        """Validate workflow graph"""
        if not nx.is_directed_acyclic_graph(self.graph):
            return False
        
        # Check all nodes have valid data
        for node_id in self.graph.nodes:
            if 'data' not in self.graph.nodes[node_id]:
                return False
        
        return True
    
    def get_node(self, node_id: UUID) -> Optional[WorkflowNode]:
        """Get node by ID"""
        if node_id in self.graph.nodes:
            return self.graph.nodes[node_id]['data']
        return None
    
    def update_node_status(self, node_id: UUID, status: ProcessStatus) -> bool:
        """Update status of a node"""
        if node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]['data']
            node.process_status = status
            
            # Update timestamps
            if status == ProcessStatus.IN_PROGRESS and not node.start_time:
                node.start_time = datetime.now()
            elif status in (ProcessStatus.COMPLETED, ProcessStatus.FAILED):
                node.end_time = datetime.now()
                
            return True
        return False
    
    def get_next_nodes(self, node_id: UUID) -> List[UUID]:
        """Get IDs of nodes that depend on the given node"""
        if node_id in self.graph.nodes:
            return list(self.graph.successors(node_id))
        return []
    
    def can_start_node(self, node_id: UUID) -> bool:
        """Check if a node can be started (all dependencies completed)"""
        if node_id not in self.graph.nodes:
            return False
            
        # Check all predecessor nodes are completed
        for pred_id in self.graph.predecessors(node_id):
            pred_node = self.graph.nodes[pred_id]['data']
            if pred_node.process_status != ProcessStatus.COMPLETED:
                return False
                
        return True
```

### WorkflowConnection
```python
@dataclass
class WorkflowConnection:
    """Defines a connection between two workflows"""
    source_workflow: UUID
    source_node: UUID
    target_workflow: UUID
    target_node: UUID
    connection_type: str  # e.g., "assembly", "component", "material"
    metadata: Dict = field(default_factory=dict)
```

### CircularDependencyError
```python
@dataclass
class CircularDependencyError:
    """Represents a detected circular dependency"""
    node_a: WorkflowNode
    node_b: WorkflowNode
    required_input: Optional[str] = None  # What input would resolve the circle
    
    def __str__(self):
        base = f"Circular dependency detected between {self.node_a.id} and {self.node_b.id}"
        if self.required_input:
            base += f"\nCan be resolved by providing: {self.required_input}"
        return base
```

### SupplyTree
```python
@dataclass
class SupplyTree:
    """Container for interconnected manufacturing workflows"""
    id: UUID = field(default_factory=uuid4)
    workflows: Dict[UUID, Workflow] = field(default_factory=dict)
    connections: List[WorkflowConnection] = field(default_factory=list)
    snapshots: Dict[str, ResourceSnapshot] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
    okh_reference: Optional[str] = None  # UUID of OKH manifest
    required_quantity: int = 1
    deadline: Optional[timedelta] = None
    metadata: Dict = field(default_factory=dict)

    def __init__(self):
        """Initialize a new SupplyTree"""
        self.id = uuid4()
        self.workflows = {}
        self.connections = []
        self.snapshots = {}
        self.creation_time = datetime.now()
        self.metadata = {}
    
    def add_workflow(self, workflow: Workflow) -> None:
        """Add a workflow to the supply tree"""
        if not workflow.validate():
            raise ValueError(f"Workflow {workflow.id} is invalid")
        self.workflows[workflow.id] = workflow
    
    def connect_workflows(self, connection: WorkflowConnection) -> None:
        """Add a connection between workflows"""
        # Validate workflows exist
        if connection.source_workflow not in self.workflows:
            raise ValueError(f"Source workflow {connection.source_workflow} not found")
        if connection.target_workflow not in self.workflows:
            raise ValueError(f"Target workflow {connection.target_workflow} not found")
            
        # Validate nodes exist
        source_wf = self.workflows[connection.source_workflow]
        target_wf = self.workflows[connection.target_workflow]
        
        if connection.source_node not in source_wf.graph.nodes:
            raise ValueError(f"Source node {connection.source_node} not found")
        if connection.target_node not in target_wf.graph.nodes:
            raise ValueError(f"Target node {connection.target_node} not found")
            
        self.connections.append(connection)
    
    def add_snapshot(self, uri: Union[ResourceURI, str], content: Dict) -> None:
        """Add a snapshot of OKH/OKW data"""
        if isinstance(uri, str):
            uri = ResourceURI.from_string(uri)
        self.snapshots[str(uri)] = ResourceSnapshot(uri=uri, content=content)
    
    def validate_against_okh(self, okh_manifest: OKHManifest) -> bool:
        """Validate supply tree against OKH manifest"""
        # Check if all required processes are represented in workflows
        required_processes = okh_manifest.extract_requirements()
        process_coverage = {proc.process_name: False for proc in required_processes}
        
        for workflow in self.workflows.values():
            for node_id in workflow.graph.nodes:
                node = workflow.graph.nodes[node_id]['data']
                for ref in node.okh_refs:
                    # Check if reference points to a process requirement
                    if ref.resource_type == ResourceType.OKH:
                        if "process" in ref.path:
                            # Mark this process as covered
                            process_name = ref.path[-1]
                            for proc_name in process_coverage:
                                if proc_name == process_name:
                                    process_coverage[proc_name] = True
        
        # Check if all required processes are covered
        return all(process_coverage.values())
    
    def validate_against_okw(self, facilities: List[ManufacturingFacility]) -> bool:
        """Validate supply tree against OKW facilities"""
        # Create lookup maps for facilities and equipment
        facility_map = {str(facility.id): facility for facility in facilities}
        equipment_map = {}
        for facility in facilities:
            for equipment in facility.equipment:
                equipment_map[str(getattr(equipment, 'id', uuid4()))] = (facility, equipment)
        
        # Check if all assigned facilities and equipment exist and are valid
        for workflow in self.workflows.values():
            for node_id in workflow.graph.nodes:
                node = workflow.graph.nodes[node_id]['data']
                
                # Skip unassigned nodes
                if not node.assigned_facility or not node.assigned_equipment:
                    continue
                
                # Check if assigned facility exists
                if node.assigned_facility not in facility_map:
                    return False
                
                # Check if assigned equipment exists
                if node.assigned_equipment not in equipment_map:
                    return False
                
                # Check if equipment belongs to assigned facility
                facility, equipment = equipment_map[node.assigned_equipment]
                if str(facility.id) != node.assigned_facility:
                    return False
                
                # Validate capability
                if not node.validate_capability(equipment):
                    return False
        
        return True
    
    def validate_current(self, okh_data: OKHManifest, okw_facilities: List[ManufacturingFacility]) -> bool:
        """Validate supply tree against current OKH/OKW data"""
        return (self.validate_against_okh(okh_data) and 
                self.validate_against_okw(okw_facilities))
    
    def validate_snapshot(self) -> bool:
        """Validate supply tree against snapshots"""
        # Validate all references exist in snapshots
        for workflow in self.workflows.values():
            for node_id in workflow.graph.nodes:
                node_data = workflow.graph.nodes[node_id].get('data')
                if not node_data:
                    return False
                    
                for ref in node_data.okh_refs + node_data.okw_refs:
                    uri_str = str(ref)
                    if uri_str not in self.snapshots:
                        return False
                        
                    # Validate referenced data exists in snapshot
                    snapshot = self.snapshots[uri_str]
                    if snapshot.get_value() is None:
                        # Check if this is a child path reference
                        # For example, okh://manifest-id/process_requirements/3d_printing
                        # might not exist directly, but may be resolvable
                        if not self._validate_child_path(ref, snapshot):
                            return False
                            
        return True
        
    def calculate_confidence(self) -> float:
        """Calculate overall confidence score for the supply tree"""
        if not self.workflows:
            return 0.0
            
        total_nodes = 0
        confidence_sum = 0.0
        
        for workflow in self.workflows.values():
            for node_id in workflow.graph.nodes:
                node_data = workflow.graph.nodes[node_id].get('data')
                if node_data:
                    total_nodes += 1
                    # Use node confidence if available, otherwise check references
                    if hasattr(node_data, 'confidence_score'):
                        confidence_sum += node_data.confidence_score
                    else:
                        # Calculate based on references
                        if node_data.okw_refs:
                            confidence_sum += 1.0
                        elif node_data.substitution_used:
                            confidence_sum += 0.7  # Lower confidence for substitutions
                        else:
                            confidence_sum += 0.0  # No capability found
        
        return confidence_sum / total_nodes if total_nodes > 0 else 0.0
        
    def to_dict(self) -> Dict:
        """Convert supply tree to serializable dictionary"""
        return {
            'id': str(self.id),
            'workflows': {
                str(wf_id): {
                    'id': str(wf.id),
                    'name': wf.name,
                    'graph': nx.node_link_data(wf.graph),
                    'entry_points': [str(ep) for ep in wf.entry_points],
                    'exit_points': [str(ep) for ep in wf.exit_points]
                }
                for wf_id, wf in self.workflows.items()
            },
            'connections': [
                {
                    'source_workflow': str(conn.source_workflow),
                    'source_node': str(conn.source_node),
                    'target_workflow': str(conn.target_workflow),
                    'target_node': str(conn.target_node),
                    'connection_type': conn.connection_type,
                    'metadata': conn.metadata
                }
                for conn in self.connections
            ],
            'snapshots': {
                uri: {
                    'content': snapshot.content,
                    'timestamp': snapshot.timestamp.isoformat(),
                    'version': snapshot.version
                }
                for uri, snapshot in self.snapshots.items()
            },
            'creation_time': self.creation_time.isoformat(),
            'okh_reference': self.okh_reference,
            'required_quantity': self.required_quantity,
            'deadline': str(self.deadline) if self.deadline else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SupplyTree':
        """Reconstruct supply tree from dictionary"""
        # Implementation details of dictionary reconstruction
        # [Code omitted for brevity]
        supply_tree = cls()
        # [Reconstruction logic]
        return supply_tree
```

### SupplyTreeSolution
```python
@dataclass
class SupplyTreeSolution:
    """A scored manufacturing solution"""
    tree: SupplyTree
    score: float
    metrics: Dict[str, Union[float, str, timedelta]] = field(default_factory=dict)
```

## Key Operations

### 1. Generating a Supply Tree

The SupplyTree class provides a class method to generate trees from OKH requirements and OKW capabilities:

```python
@classmethod
def generate_from_requirements(cls,
                             okh_manifest: 'OKHManifest',
                             facilities: List['ManufacturingFacility']) -> 'SupplyTree':
    """
    Generate a SupplyTree from OKH requirements and OKW capabilities
    
    Args:
        okh_manifest: The OKH manifest containing requirements
        facilities: List of manufacturing facilities to consider
            
    Returns:
        A valid SupplyTree that satisfies the requirements
    """
    supply_tree = cls()
    
    # Create workflows from OKH process requirements
    primary_workflow = Workflow(
        name=f"Primary workflow for {okh_manifest.title}",
        graph=nx.DiGraph(),
        entry_points=set(),
        exit_points=set()
    )
    
    # Extract process requirements
    process_requirements = okh_manifest.extract_requirements()
    
    # Create nodes for each process requirement
    # Match requirements to capabilities
    # Add workflows and connections
    # Add snapshots of source data
    
    return supply_tree
```

### 2. Validating a Supply Tree

Supply Trees can be validated in multiple ways:

```python
# Validate against original OKH/OKW data
supply_tree.validate_current(okh_manifest, facilities)

# Validate against snapshots (validation without external data)
supply_tree.validate_snapshot()

# Validate a specific workflow
workflow.validate()
```

### 3. Finding Matching Facilities

The Supply Tree can find suitable facilities for workflow nodes:

```python
def find_facility_for_node(self, node: WorkflowNode, 
                         facilities: List[ManufacturingFacility]) -> List[Tuple[ManufacturingFacility, Equipment]]:
    """Find suitable facilities and equipment for a workflow node"""
    matches = []
    
    for facility in facilities:
        # Skip inactive facilities
        if facility.facility_status != FacilityStatus.ACTIVE:
            continue
            
        for equipment in facility.equipment:
            if node.validate_capability(equipment):
                matches.append((facility, equipment))
    
    return matches
```

### 4. Calculating Confidence Scores

The Supply Tree includes methods to calculate confidence scores for the overall solution:

```python
def calculate_confidence(self) -> float:
    """Calculate overall confidence score for the supply tree"""
    # Implementation details
    # [Code omitted for brevity]
    return confidence_score  # 0.0 to 1.0
```

## Usage Examples

### Basic Example: Creating a Supply Tree

```python
# Create a SupplyTree
supply_tree = SupplyTree()

# Create a workflow
workflow = Workflow(name="Manufacturing Process")

# Create nodes for each manufacturing step
milling_node = WorkflowNode(
    name="Mill Housing",
    okh_refs=[ResourceURI(
        resource_type=ResourceType.OKH_PROCESS,
        identifier="design-123",
        path=["processes", "milling"]
    )],
    input_requirements={"material": "aluminum", "dimensions": "200x100x50mm"},
    output_specifications={"tolerance": "0.1mm"}
)

drilling_node = WorkflowNode(
    name="Drill Mounting Holes",
    okh_refs=[ResourceURI(
        resource_type=ResourceType.OKH_PROCESS,
        identifier="design-123",
        path=["processes", "drilling"]
    )],
    input_requirements={"material": "aluminum", "hole_count": 4},
    output_specifications={"hole_diameter": "5mm", "tolerance": "0.05mm"}
)

# Add nodes to workflow with dependencies
workflow.add_node(milling_node)
workflow.add_node(drilling_node, dependencies={milling_node.id})

# Add workflow to supply tree
supply_tree.add_workflow(workflow)

# Add data snapshots
supply_tree.add_snapshot(
    "okh://design-123",
    {"title": "Example Design", "processes": {"milling": {}, "drilling": {}}}
)

# Validate the supply tree
valid = supply_tree.validate_snapshot()
print(f"Supply tree is valid: {valid}")
```

### Advanced Example: Matching Requirements to Capabilities

```python
# Get OKH manifest and OKW facilities
okh_manifest = OKHManifest.from_file("design.json")
facilities = [
    ManufacturingFacility.from_file(f"facility_{i}.json")
    for i in range(3)
]

# Generate a supply tree
supply_tree = SupplyTree.generate_from_requirements(okh_manifest, facilities)

# Calculate confidence score
confidence = supply_tree.calculate_confidence()
print(f"Solution confidence: {confidence:.2f}")

# Create a solution object
solution = SupplyTreeSolution(
    tree=supply_tree,
    score=confidence,
    metrics={
        "estimated_time": timedelta(hours=24),
        "estimated_cost": 1250.00,
        "quality_score": 0.85
    }
)

# Serialize for storage
solution_dict = solution.to_dict()
with open("solution.json", "w") as f:
    json.dump(solution_dict, f)
```

## Best Practices

### 1. Resource URI Management
- Use standardized URI patterns for all references
- Create helper methods for common URI patterns
- Validate URIs before adding them to nodes
- Include enough path information to make URIs self-documenting

### 2. Workflow Design
- Design workflows to be focused and cohesive
- Map workflow dependencies explicitly
- Keep nodes simple and single-purpose
- Track entry and exit points for clarity

### 3. Validation Strategy
- Validate at multiple levels: nodes, workflows, and the overall tree
- Use different validation methods for different purposes
- Maintain snapshots for self-contained validation
- Include metadata about validation results

### 4. Confidence Scoring
- Use explicit confidence scores for all matches
- Track substitutions and their confidence impacts
- Calculate overall confidence using weighted scoring
- Include confidence metadata in serialized output

### 5. Serialization
- Implement complete serialization/deserialization
- Handle special types like UUIDs and timedeltas
- Include validation info in serialized output
- Maintain version information for backward compatibility

## Integration with OKH and OKW

The Supply Tree model is designed to seamlessly integrate with OKH and OKW models:

1. **OKH Integration**
   - Extract process requirements from OKH manifests
   - Reference specific parts and processes in OKH data
   - Validate against OKH requirements
   - Store OKH snapshots for validation

2. **OKW Integration**
   - Match requirements to facility capabilities
   - Reference specific equipment and processes in OKW data
   - Validate against facility constraints
   - Store OKW snapshots for validation

This integration enables the Supply Tree to act as a bridge between what needs to be made (OKH) and where it can be made (OKW), creating a complete manufacturing solution.