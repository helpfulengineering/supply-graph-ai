from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.core.models.okh import OKHManifest
from src.core.models.okw import ManufacturingFacility


class ResourceType(Enum):
    """Resource types that can be referenced in a Supply Tree"""

    OKH = "okh"  # OpenKnowHow manifest
    OKH_PROCESS = "okh_process"  # OKH process requirement
    OKH_MATERIAL = "okh_material"  # OKH material specification
    OKH_PART = "okh_part"  # OKH part specification
    OKW = "okw"  # OpenKnowWhere facility
    OKW_EQUIPMENT = "okw_equipment"  # OKW equipment
    OKW_PROCESS = "okw_process"  # OKW manufacturing process
    RECIPE = "recipe"  # Cooking domain recipe
    KITCHEN = "kitchen"  # Cooking domain kitchen


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
    def from_string(cls, uri_str: str) -> "ResourceURI":
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
            fragment=fragment,
        )

    def get_value_from_okh(self, okh_manifest: "OKHManifest") -> Any:
        """Extract referenced value from an OKH manifest"""
        try:
            # Convert manifest to dict for easier navigation
            manifest_dict = (
                okh_manifest.to_dict()
                if hasattr(okh_manifest, "to_dict")
                else okh_manifest.__dict__
            )

            # Navigate through the path
            current = manifest_dict
            for key in self.path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                elif isinstance(current, list) and key.isdigit():
                    index = int(key)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                else:
                    return None

            # Handle fragment if present
            if self.fragment and isinstance(current, dict):
                return current.get(self.fragment)

            return current

        except (AttributeError, KeyError, ValueError, IndexError):
            return None

    def get_value_from_okw(self, facility: "ManufacturingFacility") -> Any:
        """Extract referenced value from an OKW facility"""
        try:
            # Convert facility to dict for easier navigation
            facility_dict = (
                facility.to_dict()
                if hasattr(facility, "to_dict")
                else facility.__dict__
            )

            # Navigate through the path
            current = facility_dict
            for key in self.path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                elif isinstance(current, list) and key.isdigit():
                    index = int(key)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                else:
                    return None

            # Handle fragment if present
            if self.fragment and isinstance(current, dict):
                return current.get(self.fragment)

            return current

        except (AttributeError, KeyError, ValueError, IndexError):
            return None


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
class SupplyTree:
    """
    Simplified SupplyTree

    This class contains only the essential data needed for matching facilities
    to requirements.
    """

    # facility_id: UUID
    # replace facility_id with okw_reference: str
    facility_name: str
    okh_reference: str
    confidence_score: float
    okw_reference: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    estimated_cost: Optional[float] = None
    estimated_time: Optional[str] = None
    materials_required: List[str] = field(default_factory=list)
    capabilities_used: List[str] = field(default_factory=list)
    match_type: str = "unknown"  # "direct", "heuristic", "nlp", "llm"
    metadata: Dict[str, Any] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
    
    # NEW: Hierarchical relationships (for nested supply tree support)
    parent_tree_id: Optional[UUID] = None
    """ID of parent SupplyTree (if this represents a component of a larger product)"""
    
    child_tree_ids: List[UUID] = field(default_factory=list)
    """IDs of child SupplyTrees (components that this tree depends on)"""
    
    # NEW: Component tracking
    component_id: Optional[str] = None
    """ID of the component this SupplyTree represents (from BOM)"""
    
    component_name: Optional[str] = None
    """Human-readable name of the component"""
    
    component_quantity: Optional[float] = None
    """Quantity of this component needed"""
    
    component_unit: Optional[str] = None
    """Unit for component quantity (e.g., 'pieces', 'kg')"""
    
    # NEW: Dependency tracking
    depends_on: List[UUID] = field(default_factory=list)
    """SupplyTree IDs that must be completed before this one"""
    
    required_by: List[UUID] = field(default_factory=list)
    """SupplyTree IDs that depend on this one"""
    
    # NEW: Multi-facility coordination
    production_stage: str = "final"
    """Stage of production: 'component', 'sub-assembly', 'final'"""
    
    assembly_location: Optional[UUID] = None
    """Facility ID where final assembly happens (for final stage only)"""
    
    depth: int = 0
    """Depth in component hierarchy (0 = top level)"""
    
    component_path: List[str] = field(default_factory=list)
    """Path from root component (e.g., ['Device', 'Housing', 'Frame'])"""

    def __post_init__(self):
        """Post-initialization processing"""
        # Truncate confidence_score to 2 decimal places
        self.confidence_score = round(self.confidence_score, 2)

    def __hash__(self):
        """Enable Set operations by hashing on facility_name, okh_reference, and okw_reference"""
        return hash((self.facility_name, self.okh_reference, self.okw_reference))

    def __eq__(self, other):
        """Enable Set operations by comparing facility_name, okh_reference, and okw_reference"""
        if not isinstance(other, SupplyTree):
            return False
        return (self.facility_name, self.okh_reference, self.okw_reference) == (
            other.facility_name,
            other.okh_reference,
            other.okw_reference,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary"""
        return {
            "id": str(self.id),
            "facility_name": self.facility_name,
            "okh_reference": self.okh_reference,
            "okw_reference": self.okw_reference,
            "confidence_score": self.confidence_score,
            "estimated_cost": self.estimated_cost,
            "estimated_time": self.estimated_time,
            "materials_required": self.materials_required,
            "capabilities_used": self.capabilities_used,
            "match_type": self.match_type,
            "metadata": self.metadata,
            "creation_time": self.creation_time.isoformat(),
            # New hierarchical fields
            "parent_tree_id": str(self.parent_tree_id) if self.parent_tree_id else None,
            "child_tree_ids": [str(cid) for cid in self.child_tree_ids],
            "component_id": self.component_id,
            "component_name": self.component_name,
            "component_quantity": self.component_quantity,
            "component_unit": self.component_unit,
            "depends_on": [str(did) for did in self.depends_on],
            "required_by": [str(rid) for rid in self.required_by],
            "production_stage": self.production_stage,
            "assembly_location": str(self.assembly_location) if self.assembly_location else None,
            "depth": self.depth,
            "component_path": self.component_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SupplyTree":
        """Create from dictionary"""
        # Parse UUID fields for hierarchical relationships
        parent_tree_id = None
        if "parent_tree_id" in data and data["parent_tree_id"]:
            try:
                parent_tree_id = UUID(data["parent_tree_id"])
            except (ValueError, TypeError):
                pass
        
        child_tree_ids = []
        if "child_tree_ids" in data and data["child_tree_ids"]:
            for cid in data["child_tree_ids"]:
                try:
                    child_tree_ids.append(UUID(cid))
                except (ValueError, TypeError):
                    pass
        
        depends_on = []
        if "depends_on" in data and data["depends_on"]:
            for did in data["depends_on"]:
                try:
                    depends_on.append(UUID(did))
                except (ValueError, TypeError):
                    pass
        
        required_by = []
        if "required_by" in data and data["required_by"]:
            for rid in data["required_by"]:
                try:
                    required_by.append(UUID(rid))
                except (ValueError, TypeError):
                    pass
        
        assembly_location = None
        if "assembly_location" in data and data["assembly_location"]:
            try:
                assembly_location = UUID(data["assembly_location"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            facility_name=data["facility_name"],
            okh_reference=data["okh_reference"],
            okw_reference=data.get(
                "okw_reference"
            ),  # Optional for backward compatibility
            confidence_score=data["confidence_score"],
            estimated_cost=data.get("estimated_cost"),
            estimated_time=data.get("estimated_time"),
            materials_required=data.get("materials_required", []),
            capabilities_used=data.get("capabilities_used", []),
            match_type=data.get("match_type", "unknown"),
            metadata=data.get("metadata", {}),
            creation_time=(
                datetime.fromisoformat(data["creation_time"])
                if "creation_time" in data
                else datetime.now()
            ),
            # New hierarchical fields
            parent_tree_id=parent_tree_id,
            child_tree_ids=child_tree_ids,
            component_id=data.get("component_id"),
            component_name=data.get("component_name"),
            component_quantity=data.get("component_quantity"),
            component_unit=data.get("component_unit"),
            depends_on=depends_on,
            required_by=required_by,
            production_stage=data.get("production_stage", "final"),
            assembly_location=assembly_location,
            depth=data.get("depth", 0),
            component_path=data.get("component_path", []),
        )

    @classmethod
    def from_facility_and_manifest(
        cls,
        facility: ManufacturingFacility,
        manifest: OKHManifest,
        confidence_score: float,
        match_type: str = "unknown",
        estimated_cost: Optional[float] = None,
        estimated_time: Optional[str] = None,
    ) -> "SupplyTree":
        """
        Create a SupplyTree from a facility and manifest.

        This is the primary factory method for creating simplified supply trees
        during the matching process.
        """
        # Extract materials from manifest
        materials_required = []
        if hasattr(manifest, "materials") and manifest.materials:
            materials_required = [str(material) for material in manifest.materials]

        # Extract capabilities from facility
        capabilities_used = []
        for equipment in facility.equipment:
            if hasattr(equipment, "manufacturing_process"):
                # manufacturing_process is a string, not a list
                if isinstance(equipment.manufacturing_process, str):
                    capabilities_used.append(equipment.manufacturing_process)
                elif isinstance(equipment.manufacturing_process, list):
                    capabilities_used.extend(equipment.manufacturing_process)
            if hasattr(equipment, "manufacturing_processes"):
                # manufacturing_processes is a list
                if isinstance(equipment.manufacturing_processes, list):
                    capabilities_used.extend(equipment.manufacturing_processes)

        # Create metadata
        metadata = {
            "okh_title": manifest.title,
            "facility_name": facility.name or f"Facility {str(facility.id)[:8]}",
            "generation_method": "simplified_matching",
            "domain": "manufacturing",
            "equipment_count": len(facility.equipment),
            "process_count": len(manifest.manufacturing_processes or []),
        }

        # Get OKW reference (facility ID or name)
        okw_reference = str(facility.id) if hasattr(facility, "id") else facility.name

        return cls(
            facility_name=facility.name or f"Facility {str(facility.id)[:8]}",
            okh_reference=str(manifest.id),
            okw_reference=okw_reference,
            confidence_score=confidence_score,
            estimated_cost=estimated_cost,
            estimated_time=estimated_time,
            materials_required=materials_required,
            capabilities_used=capabilities_used,
            match_type=match_type,
            metadata=metadata,
        )


@dataclass
class ValidationResult:
    """Result of solution validation"""
    
    is_valid: bool
    """Whether the solution is valid"""
    
    errors: List[str] = field(default_factory=list)
    """List of error messages"""
    
    warnings: List[str] = field(default_factory=list)
    """List of warning messages"""
    
    unmatched_components: List[str] = field(default_factory=list)
    """Component IDs that could not be matched"""
    
    circular_dependencies: List[List[UUID]] = field(default_factory=list)
    """Detected circular dependencies"""
    
    missing_dependencies: List[UUID] = field(default_factory=list)
    """SupplyTree IDs with missing dependencies"""
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "unmatched_components": self.unmatched_components,
            "circular_dependencies": [[str(u) for u in cycle] for cycle in self.circular_dependencies],
            "missing_dependencies": [str(u) for u in self.missing_dependencies]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ValidationResult":
        """Create from dictionary representation"""
        return cls(
            is_valid=data["is_valid"],
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            unmatched_components=data.get("unmatched_components", []),
            circular_dependencies=[
                [UUID(u) for u in cycle] 
                for cycle in data.get("circular_dependencies", [])
            ],
            missing_dependencies=[
                UUID(u) for u in data.get("missing_dependencies", [])
            ]
        )


@dataclass
class SupplyTreeSolution:
    """
    Unified solution for supply tree matching.
    
    Supports both simple (single-tree) and nested (multi-tree) cases.
    For backward compatibility, simple cases can use the `tree` property
    to access the single tree directly.
    """

    # Core fields - always present
    all_trees: List[SupplyTree]
    """All SupplyTrees (flat list for easy iteration)"""
    
    score: float
    """Confidence score for this solution (average of tree confidence scores)"""
    
    metrics: Dict[str, Any] = field(default_factory=dict)
    """Additional metrics about the matching process"""
    
    # Nested/hierarchical fields - optional, populated for nested cases
    root_trees: Optional[List[SupplyTree]] = None
    """Top-level SupplyTrees (final products). Defaults to all_trees if None."""
    
    component_mapping: Optional[Dict[str, List[SupplyTree]]] = None
    """Component ID → List of SupplyTrees for that component (for nested cases)"""
    
    dependency_graph: Optional[Dict[UUID, List[UUID]]] = None
    """Dependency graph: tree_id → [dependent_tree_ids] (for nested cases)"""
    
    production_sequence: Optional[List[List[UUID]]] = None
    """Production stages: each inner list can be done in parallel (for nested cases)"""
    
    validation_result: Optional[ValidationResult] = None
    """Validation result for this solution (for nested cases)"""
    
    total_estimated_cost: Optional[float] = None
    """Sum of all SupplyTree costs (for nested cases)"""
    
    total_estimated_time: Optional[str] = None
    """Critical path time (longest dependency chain) (for nested cases)"""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata (matching parameters, etc.)"""

    def __post_init__(self):
        """Post-initialization processing"""
        # Truncate score to 2 decimal places
        self.score = round(self.score, 2)
        
        # Set root_trees to all_trees if not specified (simple case)
        if self.root_trees is None:
            self.root_trees = self.all_trees
        
        # Calculate score from trees if not provided (for nested cases)
        # Allow empty solutions for error/fallback cases (check metadata for error indicators)
        if not self.all_trees and not (self.metadata and (self.metadata.get("error") or self.metadata.get("warning"))):
            raise ValueError("SupplyTreeSolution must have at least one tree (unless it's an error/fallback case)")
        
        # If score is 0.0 and we have trees, calculate average confidence
        if self.score == 0.0 and self.all_trees:
            self.score = sum(tree.confidence_score for tree in self.all_trees) / len(self.all_trees)
            self.score = round(self.score, 2)

    @property
    def tree(self) -> SupplyTree:
        """
        Convenience property for backward compatibility.
        Returns the single tree if there's only one, otherwise raises ValueError.
        """
        if len(self.all_trees) == 1:
            return self.all_trees[0]
        raise ValueError(
            f"Solution contains {len(self.all_trees)} trees. "
            "Use all_trees property for multi-tree solutions."
        )
    
    @property
    def is_nested(self) -> bool:
        """Check if this is a nested solution (multiple trees with relationships)"""
        return (
            len(self.all_trees) > 1 or
            self.component_mapping is not None or
            self.dependency_graph is not None
        )

    def get_dependency_graph(self) -> Dict[UUID, List[UUID]]:
        """
        Build dependency graph from SupplyTrees (for nested cases).
        
        The dependency graph represents which SupplyTrees depend on which others.
        A tree depends on another if:
        - It has a parent_tree_id (parent must be completed first)
        - It has entries in depends_on list (explicit dependencies)
        
        Returns:
            Dictionary mapping tree_id -> list of dependent tree_ids
        """
        if self.dependency_graph is not None:
            return self.dependency_graph
        
        graph = {}
        for tree in self.all_trees:
            dependencies = []
            # Add parent as dependency (parent must be completed before child)
            if tree.parent_tree_id:
                dependencies.append(tree.parent_tree_id)
            # Add explicit dependencies
            if tree.depends_on:
                dependencies.extend(tree.depends_on)
            # Remove duplicates while preserving order
            seen = set()
            unique_deps = []
            for dep in dependencies:
                if dep not in seen:
                    seen.add(dep)
                    unique_deps.append(dep)
            graph[tree.id] = unique_deps
        return graph
    
    def validate_solution(self) -> ValidationResult:
        """Validate that all components have matches and dependencies are satisfied (for nested cases)"""
        errors = []
        warnings = []
        unmatched_components = []
        missing_dependencies = []
        
        # Check that all components have matches (if component_mapping exists)
        if self.component_mapping:
            for component_id, trees in self.component_mapping.items():
                if not trees:
                    unmatched_components.append(component_id)
                    errors.append(f"Component {component_id} has no matching facilities")
        
        # Check for missing dependencies
        all_tree_ids = {tree.id for tree in self.all_trees}
        for tree in self.all_trees:
            for dep_id in tree.depends_on:
                if dep_id not in all_tree_ids:
                    missing_dependencies.append(dep_id)
                    errors.append(f"SupplyTree {tree.id} depends on missing tree {dep_id}")
        
        # Check for circular dependencies (basic check)
        circular_dependencies = self._detect_circular_dependencies()
        if circular_dependencies:
            warnings.append(f"Detected {len(circular_dependencies)} potential circular dependencies")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            unmatched_components=unmatched_components,
            circular_dependencies=circular_dependencies,
            missing_dependencies=missing_dependencies
        )
    
    def _detect_circular_dependencies(self) -> List[List[UUID]]:
        """
        Detect circular dependencies using enhanced DFS algorithm.
        
        This method detects all cycles in the dependency graph and returns
        them as lists of UUIDs representing the circular path.
        
        Returns:
            List of cycles, where each cycle is a list of UUIDs forming a circular path
        """
        dependency_graph = self.get_dependency_graph()
        if not dependency_graph:
            return []
        
        visited = set()
        rec_stack = set()
        cycles = []
        cycle_paths = set()  # Track cycles we've already found to avoid duplicates
        
        def dfs(node: UUID, path: List[UUID]) -> None:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                # Create a normalized cycle representation (sorted by first UUID)
                cycle_tuple = tuple(sorted(set(cycle)))
                if cycle_tuple not in cycle_paths:
                    cycle_paths.add(cycle_tuple)
                    cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            dependencies = dependency_graph.get(node, [])
            for dep in dependencies:
                dfs(dep, path + [node])
            
            rec_stack.remove(node)
        
        # Check all nodes in the dependency graph
        for tree_id in dependency_graph.keys():
            if tree_id not in visited:
                dfs(tree_id, [])
        
        return cycles
    
    def get_assembly_sequence(self) -> List[List[SupplyTree]]:
        """Get production sequence with SupplyTree objects (for nested cases)"""
        if not self.production_sequence:
            return []
        
        sequence = []
        tree_map = {tree.id: tree for tree in self.all_trees}
        for stage in self.production_sequence:
            trees = [tree_map[tree_id] for tree_id in stage if tree_id in tree_map]
            sequence.append(trees)
        return sequence
    
    def calculate_total_cost(self) -> float:
        """
        Calculate total estimated cost across all SupplyTrees.
        
        This method sums the estimated_cost from all trees in the solution.
        If no trees have cost estimates, returns 0.0.
        
        Returns:
            Total estimated cost as a float
        """
        total = 0.0
        trees_with_cost = 0
        for tree in self.all_trees:
            if tree.estimated_cost is not None:
                total += tree.estimated_cost
                trees_with_cost += 1
        
        # Log if some trees don't have cost estimates
        if trees_with_cost < len(self.all_trees) and len(self.all_trees) > 0:
            from ..utils.logging import get_logger
            logger = get_logger(__name__)
            logger.debug(
                f"Only {trees_with_cost} of {len(self.all_trees)} trees have cost estimates",
                extra={
                    "trees_with_cost": trees_with_cost,
                    "total_trees": len(self.all_trees)
                }
            )
        
        return total
    
    def calculate_critical_path_time(self) -> str:
        """
        Calculate critical path time (longest dependency chain).
        
        This method calculates the estimated time for the critical path,
        which is the longest sequence of dependent tasks that determines
        the minimum project duration.
        
        Returns:
            String representation of estimated time (e.g., "2-3 weeks", "5 stages")
        """
        if not self.production_sequence:
            return "Unknown"
        
        # If trees have estimated_time, try to calculate actual time
        # Otherwise, use stage count as approximation
        times_with_values = [
            tree.estimated_time 
            for tree in self.all_trees 
            if tree.estimated_time and tree.estimated_time != "Unknown"
        ]
        
        if times_with_values:
            # For now, return stage count with note about time estimates
            num_stages = len(self.production_sequence)
            return f"{num_stages} stages (time estimates available)"
        
        # Fallback to stage count
        num_stages = len(self.production_sequence)
        return f"{num_stages} stages"
    
    @staticmethod
    def _calculate_production_sequence(
        dependency_graph: Dict[UUID, List[UUID]]
    ) -> List[List[UUID]]:
        """
        Calculate production sequence using topological sort.
        
        Returns list of stages, where each stage can be produced in parallel.
        
        Algorithm:
        1. Build in-degree map (how many dependencies each node has)
        2. Initialize queue with nodes that have no dependencies
        3. While queue is not empty:
           a. Process all nodes in current queue (parallel stage)
           b. For each processed node, decrement in-degree of dependents
           c. Add nodes with in-degree 0 to next stage queue
        4. Return list of stages
        """
        if not dependency_graph:
            return []
        
        # Build in-degree map
        in_degree: Dict[UUID, int] = {node: 0 for node in dependency_graph.keys()}
        for node, deps in dependency_graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # Initialize queue with nodes that have no dependencies
        queue = [node for node, degree in in_degree.items() if degree == 0]
        stages = []
        
        while queue:
            # Current stage (can be done in parallel)
            current_stage = queue.copy()
            stages.append(current_stage)
            queue = []
            
            # Process nodes in current stage
            for node in current_stage:
                # Decrement in-degree of dependents
                # Note: We need to find which nodes depend on this node
                # (reverse lookup in dependency graph)
                for dependent_node, deps in dependency_graph.items():
                    if node in deps:
                        in_degree[dependent_node] -= 1
                        if in_degree[dependent_node] == 0:
                            queue.append(dependent_node)
        
        return stages

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary"""
        result = {
            "all_trees": [tree.to_dict() for tree in self.all_trees],
            "root_trees": [tree.to_dict() for tree in self.root_trees] if self.root_trees else None,
            "score": self.score,
            "metrics": self.metrics,
            "metadata": self.metadata,
            "is_nested": self.is_nested,
        }
        
        # Backward compatibility: include single tree as "tree" if only one tree
        if len(self.all_trees) == 1:
            result["tree"] = self.all_trees[0].to_dict()
        
        # Include nested fields if present
        if self.component_mapping is not None:
            result["component_mapping"] = {
                comp_id: [tree.to_dict() for tree in trees]
                for comp_id, trees in self.component_mapping.items()
            }
        
        if self.dependency_graph is not None:
            result["dependency_graph"] = {
                str(tree_id): [str(dep_id) for dep_id in deps]
                for tree_id, deps in self.dependency_graph.items()
            }
        
        if self.production_sequence is not None:
            result["production_sequence"] = [
                [str(tree_id) for tree_id in stage]
                for stage in self.production_sequence
            ]
        
        if self.validation_result is not None:
            result["validation_result"] = self.validation_result.to_dict()
        
        if self.total_estimated_cost is not None:
            result["total_estimated_cost"] = self.total_estimated_cost
        
        if self.total_estimated_time is not None:
            result["total_estimated_time"] = self.total_estimated_time
        
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SupplyTreeSolution":
        """Create from dictionary representation"""
        # Handle backward compatibility: if "tree" field exists, convert to all_trees
        if "tree" in data and "all_trees" not in data:
            all_trees = [SupplyTree.from_dict(data["tree"])]
        else:
            all_trees = [SupplyTree.from_dict(t) for t in data.get("all_trees", [])]
        
        root_trees = None
        if "root_trees" in data and data["root_trees"]:
            root_trees = [SupplyTree.from_dict(t) for t in data["root_trees"]]
        
        component_mapping = None
        if "component_mapping" in data and data["component_mapping"]:
            component_mapping = {
                comp_id: [SupplyTree.from_dict(t) for t in trees]
                for comp_id, trees in data["component_mapping"].items()
            }
        
        dependency_graph = None
        if "dependency_graph" in data and data["dependency_graph"]:
            dependency_graph = {
                UUID(tree_id): [UUID(dep_id) for dep_id in deps]
                for tree_id, deps in data["dependency_graph"].items()
            }
        
        production_sequence = None
        if "production_sequence" in data and data["production_sequence"]:
            production_sequence = [
                [UUID(tree_id) for tree_id in stage]
                for stage in data["production_sequence"]
            ]
        
        validation_result = None
        if "validation_result" in data and data["validation_result"]:
            validation_result = ValidationResult.from_dict(data["validation_result"])
        
        return cls(
            all_trees=all_trees,
            root_trees=root_trees,
            score=data.get("score", 0.0),
            metrics=data.get("metrics", {}),
            component_mapping=component_mapping,
            dependency_graph=dependency_graph,
            production_sequence=production_sequence,
            validation_result=validation_result,
            total_estimated_cost=data.get("total_estimated_cost"),
            total_estimated_time=data.get("total_estimated_time"),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_single_tree(cls, tree: SupplyTree, score: Optional[float] = None, metrics: Optional[Dict[str, Any]] = None) -> "SupplyTreeSolution":
        """Factory method for creating a solution from a single tree (backward compatibility)"""
        return cls(
            all_trees=[tree],
            root_trees=[tree],
            score=score if score is not None else tree.confidence_score,
            metrics=metrics or {}
        )
    
    @classmethod
    def from_nested_trees(
        cls,
        all_trees: List[SupplyTree],
        root_trees: List[SupplyTree],
        component_mapping: Dict[str, List[SupplyTree]],
        score: Optional[float] = None,
        metrics: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "SupplyTreeSolution":
        """Factory method for creating a nested solution from multiple trees"""
        # Calculate score if not provided
        if score is None:
            score = sum(tree.confidence_score for tree in all_trees) / len(all_trees) if all_trees else 0.0
        
        solution = cls(
            all_trees=all_trees,
            root_trees=root_trees,
            component_mapping=component_mapping,
            score=score,
            metrics=metrics or {},
            metadata=metadata or {}
        )
        
        # Build dependency graph and production sequence
        solution.dependency_graph = solution.get_dependency_graph()
        # Calculate production sequence using topological sort
        solution.production_sequence = SupplyTreeSolution._calculate_production_sequence(
            solution.dependency_graph
        )
        
        # Validate solution
        solution.validation_result = solution.validate_solution()
        
        # Calculate aggregates
        solution.total_estimated_cost = solution.calculate_total_cost()
        solution.total_estimated_time = solution.calculate_critical_path_time()
        
        return solution

    def __hash__(self):
        """Enable Set operations by hashing on tree IDs"""
        if len(self.all_trees) == 1:
            # For single-tree solutions, use the same hash as before
            tree = self.all_trees[0]
            return hash((tree.facility_name, tree.okh_reference, tree.okw_reference))
        else:
            # For multi-tree solutions, hash on all tree IDs
            return hash(tuple(sorted(tree.id for tree in self.all_trees)))

    def __eq__(self, other):
        """Enable Set operations by comparing tree IDs"""
        if not isinstance(other, SupplyTreeSolution):
            return False
        
        if len(self.all_trees) == 1 and len(other.all_trees) == 1:
            # For single-tree solutions, use the same comparison as before
            return (
                self.all_trees[0].facility_name,
                self.all_trees[0].okh_reference,
                self.all_trees[0].okw_reference,
            ) == (
                other.all_trees[0].facility_name,
                other.all_trees[0].okh_reference,
                other.all_trees[0].okw_reference,
            )
        else:
            # For multi-tree solutions, compare tree IDs
            return set(tree.id for tree in self.all_trees) == set(tree.id for tree in other.all_trees)
