from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Union, Tuple, Any
from enum import Enum
from uuid import UUID, uuid4
import networkx as nx

from src.core.models.okh import OKHManifest, ProcessRequirement, MaterialSpec, DocumentRef
from src.core.models.okw import ManufacturingFacility, Equipment, Material, FacilityStatus, Agent


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


class ProcessStatus(Enum):
    """Status of a manufacturing process node"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


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
    
    def get_value_from_okh(self, okh_manifest: 'OKHManifest') -> Any:
        """Extract referenced value from an OKH manifest"""
        # Implementation to navigate the OKH manifest structure
        # based on path and fragment
    
    def get_value_from_okw(self, facility: 'ManufacturingFacility') -> Any:
        """Extract referenced value from an OKW facility"""
        # Implementation to navigate the OKW facility structure
        # based on path and fragment


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

    def validate_capability(self, equipment: 'Equipment') -> bool:
        """Validate if equipment can handle node requirements"""
        # Check if equipment type matches process requirements
        for ref in self.okh_refs:
            if ref.resource_type in [ResourceType.OKH_PROCESS, ResourceType.OKH]:
                # Extract process name from OKH reference
                process_name = self._extract_process_name(ref)
                
                # Check if equipment supports this process
                if process_name in equipment.manufacturing_process or any(
                    process_name in proc for proc in 
                    getattr(equipment, 'manufacturing_processes', [])
                ):
                    return True
                    
                # Check if equipment has this process in additional properties
                if hasattr(equipment, 'additional_properties') and equipment.additional_properties:
                    if 'processes' in equipment.additional_properties:
                        if process_name in equipment.additional_properties['processes']:
                            return True
        
        return False
    
    def _extract_process_name(self, uri: ResourceURI) -> str:
        """Extract process name from URI"""
        # Extract process name based on path structure
        # This is a simplification and would need proper implementation
        if 'process' in uri.path:
            idx = uri.path.index('process')
            if idx + 1 < len(uri.path):
                return uri.path[idx + 1]
        
        # Default to node name if no process found
        return self.name

    def assign_resources(self, facility_id: str, equipment_id: str) -> None:
        """Assign facility and equipment to this node"""
        self.assigned_facility = facility_id
        self.assigned_equipment = equipment_id
        self.metadata["assignment_timestamp"] = datetime.now().isoformat()


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


@dataclass
class Workflow:
    """Represents a discrete manufacturing workflow as a DAG"""
    name: str
    id: UUID = field(default_factory=uuid4)
    graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    entry_points: Set[UUID] = field(default_factory=set)  # Nodes that start the workflow
    exit_points: Set[UUID] = field(default_factory=set)   # Nodes that end the workflow
    
    class Config:
        arbitrary_types_allowed = True
    
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
    okh_reference: Optional[str] = None  # UUID of OKH manifest
    required_quantity: int = 1
    deadline: Optional[timedelta] = None
    metadata: Dict = field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True

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
    
    def _validate_child_path(self, ref: ResourceURI, snapshot: ResourceSnapshot) -> bool:
        """Validate a complex path reference by traversing parent paths"""
        # This would handle cases where paths reference nested structures
        # Implementation would traverse the path segments to validate
        
        # Simplified example:
        content = snapshot.content
        for segment in ref.path:
            if isinstance(content, dict) and segment in content:
                content = content[segment]
            elif isinstance(content, list) and segment.isdigit() and int(segment) < len(content):
                content = content[int(segment)]
            else:
                return False
                
        return True
    
    def find_facility_for_node(self, node: WorkflowNode, facilities: List[ManufacturingFacility]) -> List[Tuple[ManufacturingFacility, Equipment]]:
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
    
    def assign_node_to_facility(self, node_id: UUID, facility_id: str, equipment_id: str) -> bool:
        """Assign a node to a specific facility and equipment"""
        # Find the node
        found_node = False
        for workflow in self.workflows.values():
            if node_id in workflow.graph.nodes:
                node = workflow.graph.nodes[node_id]['data']
                node.assign_resources(facility_id, equipment_id)
                found_node = True
                break
                
        return found_node
    
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
        supply_tree = cls()
        
        # Set basic properties
        if 'id' in data:
            supply_tree.id = UUID(data['id'])
        if 'creation_time' in data:
            supply_tree.creation_time = datetime.fromisoformat(data['creation_time'])
        if 'okh_reference' in data:
            supply_tree.okh_reference = data['okh_reference']
        if 'required_quantity' in data:
            supply_tree.required_quantity = data['required_quantity']
        if 'deadline' in data and data['deadline']:
            supply_tree.deadline = timedelta(seconds=int(data['deadline'].total_seconds()))
        if 'metadata' in data:
            supply_tree.metadata = data['metadata']
        
        # Reconstruct workflows
        if 'workflows' in data:
            for wf_id_str, wf_data in data['workflows'].items():
                workflow = Workflow(
                    name=wf_data['name'],
                )
                
                # Set workflow ID
                if 'id' in wf_data:
                    workflow.id = UUID(wf_data['id'])
                
                # Reconstruct graph
                workflow.graph = nx.node_link_graph(wf_data['graph'])
                
                # Convert node data to WorkflowNode objects
                for node_id in workflow.graph.nodes:
                    node_data = workflow.graph.nodes[node_id].get('data', {})
                    if not isinstance(node_data, WorkflowNode):
                        # Reconstruct WorkflowNode object
                        node = WorkflowNode(
                            name=node_data.get('name', 'Unknown Node'),
                            id=UUID(node_id) if isinstance(node_id, str) else node_id
                        )
                        
                        # Add additional properties
                        for key, value in node_data.items():
                            if key != 'name' and hasattr(node, key):
                                setattr(node, key, value)
                                
                        workflow.graph.nodes[node_id]['data'] = node
                
                # Set entry and exit points
                workflow.entry_points = set(UUID(ep) if isinstance(ep, str) else ep 
                                          for ep in wf_data.get('entry_points', []))
                workflow.exit_points = set(UUID(ep) if isinstance(ep, str) else ep 
                                         for ep in wf_data.get('exit_points', []))
                
                supply_tree.workflows[workflow.id] = workflow
        
        # Reconstruct connections
        if 'connections' in data:
            for conn_data in data['connections']:
                connection = WorkflowConnection(
                    source_workflow=UUID(conn_data['source_workflow']),
                    source_node=UUID(conn_data['source_node']),
                    target_workflow=UUID(conn_data['target_workflow']),
                    target_node=UUID(conn_data['target_node']),
                    connection_type=conn_data['connection_type'],
                    metadata=conn_data.get('metadata', {})
                )
                supply_tree.connections.append(connection)
        
        # Reconstruct snapshots
        if 'snapshots' in data:
            for uri_str, snapshot_data in data['snapshots'].items():
                uri = ResourceURI.from_string(uri_str)
                snapshot = ResourceSnapshot(
                    uri=uri,
                    content=snapshot_data['content'],
                    timestamp=datetime.fromisoformat(snapshot_data['timestamp']),
                    version=snapshot_data.get('version')
                )
                supply_tree.snapshots[uri_str] = snapshot
        
        return supply_tree
        
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
        
        # Create dependency graph for processes if dependencies exist
        dependency_graph = nx.DiGraph()
        previous_node = None
        
        for req in process_requirements:
            # Create node for this process requirement
            node_id = uuid4()
            node = WorkflowNode(
                id=node_id,
                name=req.process_name,
                okh_refs=[ResourceURI(
                    resource_type=ResourceType.OKH_PROCESS,
                    identifier=str(okh_manifest.id),
                    path=["process_requirements", req.process_name]
                )],
                input_requirements=req.parameters,
                output_specifications=req.validation_criteria,
                estimated_time=timedelta(minutes=30)  # Default estimation, should be refined
            )
            
            # Find matching equipment across facilities
            for facility in facilities:
                for equipment in facility.equipment:
                    # Check if equipment can handle this process
                    if hasattr(req, 'can_be_satisfied_by'):
                        # Use OKH method if available
                        if req.can_be_satisfied_by(equipment):
                            node.okw_refs.append(ResourceURI(
                                resource_type=ResourceType.OKW_EQUIPMENT,
                                identifier=str(facility.id),
                                path=["equipment", getattr(equipment, "id", "0")]
                            ))
                    else:
                        # Fallback to process name matching
                        if req.process_name in equipment.manufacturing_process:
                            node.okw_refs.append(ResourceURI(
                                resource_type=ResourceType.OKW_EQUIPMENT,
                                identifier=str(facility.id),
                                path=["equipment", getattr(equipment, "id", "0")]
                            ))
            
            # Add node to workflow 
            primary_workflow.graph.add_node(node_id, data=node)
            
            # If we're building a linear workflow, connect to previous node
            if previous_node:
                primary_workflow.graph.add_edge(previous_node, node_id)
                
            previous_node = node_id
            
            # Update entry/exit points
            if not primary_workflow.graph.in_degree(node_id):
                primary_workflow.entry_points.add(node_id)
            if not primary_workflow.graph.out_degree(node_id):
                primary_workflow.exit_points.add(node_id)
        
        supply_tree.add_workflow(primary_workflow)
        
        # Add relevant snapshots
        supply_tree.add_snapshot(f"okh://{okh_manifest.id}", okh_manifest.to_dict())
        for facility in facilities:
            supply_tree.add_snapshot(f"okw://{facility.id}", facility.to_dict())
        
        return supply_tree

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

@dataclass
class SupplyTreeSolution:
    """A scored manufacturing solution"""
    tree: SupplyTree
    score: float
    metrics: Dict[str, Union[float, str, timedelta]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert solution to serializable dictionary"""
        return {
            'tree': self.tree.to_dict(),
            'score': self.score,
            'metrics': {k: str(v) if isinstance(v, timedelta) else v 
                        for k, v in self.metrics.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SupplyTreeSolution':
        """Reconstruct solution from dictionary"""
        tree = SupplyTree.from_dict(data['tree'])
        metrics = data['metrics']
        
        # Convert string timedeltas back to timedelta objects
        for k, v in metrics.items():
            if isinstance(v, str) and "day" in v or ":" in v:
                try:
                    days, time_part = v.split(', ')
                    days = int(days.split(' ')[0])
                    hours, minutes, seconds = map(int, time_part.split(':'))
                    metrics[k] = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
                except ValueError:
                    # If parsing fails, keep as string
                    pass
        
        return cls(
            tree=tree,
            score=data['score'],
            metrics=metrics
        )