from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional, Set, Union
from enum import Enum
from datetime import datetime
import networkx as nx
from uuid import UUID, uuid4




class ProcessStatus(Enum):
    """Status of a manufacturing process node"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass
class ProcessRequirement:
    """Requirements for a specific manufacturing process"""
    wikipedia_url: str  # Standard process classification
    equipment_required: List[str]  # Equipment Wikipedia URLs
    materials_required: List[str]  # Material Wikipedia URLs
    estimated_time: timedelta
    batch_size_min: int
    batch_size_max: Optional[int] = None
    quality_standards: List[str] = field(default_factory=list)  # ISO/ANSI refs
    skill_requirements: List[str] = field(default_factory=list)

@dataclass
class ProcessNode:
    """A node in the supply tree representing a manufacturing step"""
    id: UUID = field(default_factory=uuid4)
    process: ProcessRequirement
    facility_id: Optional[str] = None  # OKW facility reference
    status: ProcessStatus = ProcessStatus.PENDING
    start_time: Optional[timedelta] = None
    end_time: Optional[timedelta] = None
    actual_batch_size: Optional[int] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class CircularDependencyError:
    """Represents a detected circular dependency"""
    node_a: ProcessNode
    node_b: ProcessNode
    required_input: Optional[str] = None  # What input would resolve the circle
    
    def __str__(self):
        base = f"Circular dependency detected between {self.node_a.id} and {self.node_b.id}"
        if self.required_input:
            base += f"\nCan be resolved by providing: {self.required_input}"
        return base



class ResourceType(Enum):
    """Types of resources that can be referenced"""
    OKH = "okh"
    OKW = "okw"

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
        resource_type = ResourceType(scheme)
        
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

@dataclass
class WorkflowNode:
    """Node representing a step in a manufacturing workflow"""
    id: UUID = field(default_factory=uuid4)
    name: str
    okh_refs: List[ResourceURI] = field(default_factory=list)  # What needs to be done
    okw_refs: List[ResourceURI] = field(default_factory=list)  # Where it can be done
    input_requirements: Dict[str, any] = field(default_factory=dict)
    output_specifications: Dict[str, any] = field(default_factory=dict)
    estimated_time: timedelta = field(default_factory=lambda: timedelta())
    metadata: Dict = field(default_factory=dict)

    def validate_capability(self, equipment: 'Equipment') -> bool:
        """
        Validate if this node's requirements can be met by the given equipment
        Returns True if equipment can handle the requirements
        """
        # Implementation would check equipment capabilities against requirements
        pass

@dataclass
class CircularDependencyError:
    """Represents a detected circular dependency"""
    node_a: WorkflowNode
    node_b: WorkflowNode
    required_input: Optional[str] = None


@dataclass
class Workflow:
    """Represents a discrete manufacturing workflow as a DAG"""
    id: UUID = field(default_factory=uuid4)
    name: str
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
            self.exit_points.discard(dep_id)
    
    def validate(self) -> bool:
        """Validate workflow graph"""
        if not nx.is_directed_acyclic_graph(self.graph):
            return False
        return True

@dataclass
class WorkflowConnection:
    """Defines a connection between two workflows"""
    source_workflow: UUID
    source_node: UUID
    target_workflow: UUID
    target_node: UUID
    connection_type: str  # e.g., "assembly", "component", "material"
    metadata: Dict = field(default_factory=dict)

@dataclass
class SupplyTree:
    """Container for interconnected manufacturing workflows"""
    id: UUID = field(default_factory=uuid4)
    workflows: Dict[UUID, Workflow] = field(default_factory=dict)
    connections: List[WorkflowConnection] = field(default_factory=list)
    snapshots: Dict[str, ResourceSnapshot] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
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
    
    def validate_current(self, okh_data: Dict, okw_data: Dict) -> bool:
        """Validate supply tree against current OKH/OKW data"""
        # Implement validation against current state
        # This would check if all referenced capabilities still exist
        # and all requirements are still valid
        pass
    
    def validate_snapshot(self) -> bool:
        """Validate supply tree against snapshots"""
        # Validate all references exist in snapshots
        for workflow in self.workflows.values():
            for node_id in workflow.graph.nodes:
                node: WorkflowNode = workflow.graph.nodes[node_id]['data']
                for ref in node.okh_refs + node.okw_refs:
                    uri_str = str(ref)
                    if uri_str not in self.snapshots:
                        return False
                    # Validate referenced data exists in snapshot
                    if self.snapshots[uri_str].get_value() is None:
                        return False
        return True
    
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
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SupplyTree':
        """Reconstruct supply tree from dictionary"""
        # Implementation would reverse the to_dict() operation
        pass


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
            id=uuid4(),
            name=f"Primary workflow for {okh_manifest.title}",
            graph=nx.DiGraph(),
            entry_points=set(),
            exit_points=set()
        )
        
        # Map process requirements to equipment capabilities
        for req in okh_manifest.process_requirements:
            # Find matching equipment across facilities
            matched_equipment = []
            for facility in facilities:
                for equipment in facility.equipment:
                    if req.can_be_satisfied_by(equipment):
                        matched_equipment.append((facility, equipment))
            
            if not matched_equipment:
                raise ValueError(f"No matching equipment found for {req.name}")
            
            # Create node for this process requirement
            node = WorkflowNode(
                id=uuid4(),
                name=req.name,
                okh_refs=[ResourceURI(
                    resource_type="OKH",
                    identifier=okh_manifest.id,
                    path=["process_requirements", req.id]
                )],
                okw_refs=[ResourceURI(
                    resource_type="OKW",
                    identifier=facility.id,
                    path=["equipment", equipment.id]
                ) for facility, equipment in matched_equipment],
                input_requirements=req.input_requirements,
                output_specifications=req.output_specifications,
                estimated_time=req.estimated_time
            )
            
            primary_workflow.add_node(node)
            
        supply_tree.add_workflow(primary_workflow)
        
        # Create additional workflows for sub-assemblies if needed
        
        # Add relevant snapshots
        supply_tree.add_snapshot(f"okh://{okh_manifest.id}", okh_manifest.to_dict())
        for facility in facilities:
            supply_tree.add_snapshot(f"okw://{facility.id}", facility.to_dict())
        
        return supply_tree


@dataclass
class SupplyTreeSolution:
    """A scored manufacturing solution"""
    tree: SupplyTree
    score: float
    metrics: Dict[str, Union[float, str, timedelta]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert solution to serializable dictionary"""
        return {
            'score': self.score,
            'metrics': self.metrics,
            'graph': nx.node_link_data(self.tree.graph),
            'okh_reference': self.tree.okh_reference,
            'required_quantity': self.tree.required_quantity,
            'deadline': str(self.tree.deadline)
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SupplyTreeSolution':
        """Reconstruct solution from dictionary"""
        graph = nx.node_link_graph(data['graph'])
        tree = SupplyTree(
            graph=graph,
            okh_reference=data['okh_reference'],
            required_quantity=data['required_quantity'],
            deadline=timedelta(seconds=int(data['deadline'].total_seconds()))
        )
        return cls(
            tree=tree,
            score=data['score'],
            metrics=data['metrics']
        )