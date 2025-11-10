from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from uuid import UUID, uuid4

from src.core.models.okh import OKHManifest
from src.core.models.okw import ManufacturingFacility


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
        try:
            # Convert manifest to dict for easier navigation
            manifest_dict = okh_manifest.to_dict() if hasattr(okh_manifest, 'to_dict') else okh_manifest.__dict__
            
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
    
    def get_value_from_okw(self, facility: 'ManufacturingFacility') -> Any:
        """Extract referenced value from an OKW facility"""
        try:
            # Convert facility to dict for easier navigation
            facility_dict = facility.to_dict() if hasattr(facility, 'to_dict') else facility.__dict__
            
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
    # TODO: add okw_reference: str
    confidence_score: float
    id: UUID = field(default_factory=uuid4)
    estimated_cost: Optional[float] = None
    estimated_time: Optional[str] = None
    materials_required: List[str] = field(default_factory=list)
    capabilities_used: List[str] = field(default_factory=list)
    match_type: str = "unknown"  # "direct", "heuristic", "nlp", "llm"
    metadata: Dict[str, Any] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization processing"""
        # Truncate confidence_score to 2 decimal places
        self.confidence_score = round(self.confidence_score, 2)
    
    def __hash__(self):
        """Enable Set operations by hashing on facility_name and okh_reference"""
        return hash((self.facility_name, self.okh_reference))
    
    def __eq__(self, other):
        """Enable Set operations by comparing facility_name and okh_reference"""
        if not isinstance(other, SupplyTree):
            return False
        return (self.facility_name, self.okh_reference) == (other.facility_name, other.okh_reference)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary"""
        return {
            'id': str(self.id),
            'facility_name': self.facility_name,
            'okh_reference': self.okh_reference,
            'confidence_score': self.confidence_score,
            'estimated_cost': self.estimated_cost,
            'estimated_time': self.estimated_time,
            'materials_required': self.materials_required,
            'capabilities_used': self.capabilities_used,
            'match_type': self.match_type,
            'metadata': self.metadata,
            'creation_time': self.creation_time.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SupplyTree':
        """Create from dictionary"""
        return cls(
            id=UUID(data['id']) if 'id' in data else uuid4(),
            facility_name=data['facility_name'],
            okh_reference=data['okh_reference'],
            confidence_score=data['confidence_score'],
            estimated_cost=data.get('estimated_cost'),
            estimated_time=data.get('estimated_time'),
            materials_required=data.get('materials_required', []),
            capabilities_used=data.get('capabilities_used', []),
            match_type=data.get('match_type', 'unknown'),
            metadata=data.get('metadata', {}),
            creation_time=datetime.fromisoformat(data['creation_time']) if 'creation_time' in data else datetime.now()
        )
    
    @classmethod
    def from_facility_and_manifest(
        cls,
        facility: ManufacturingFacility,
        manifest: OKHManifest,
        confidence_score: float,
        match_type: str = "unknown",
        estimated_cost: Optional[float] = None,
        estimated_time: Optional[str] = None
    ) -> 'SupplyTree':
        """
        Create a SupplyTree from a facility and manifest.
        
        This is the primary factory method for creating simplified supply trees
        during the matching process.
        """
        # Extract materials from manifest
        materials_required = []
        if hasattr(manifest, 'materials') and manifest.materials:
            materials_required = [str(material) for material in manifest.materials]
        
        # Extract capabilities from facility
        capabilities_used = []
        for equipment in facility.equipment:
            if hasattr(equipment, 'manufacturing_process'):
                # manufacturing_process is a string, not a list
                if isinstance(equipment.manufacturing_process, str):
                    capabilities_used.append(equipment.manufacturing_process)
                elif isinstance(equipment.manufacturing_process, list):
                    capabilities_used.extend(equipment.manufacturing_process)
            if hasattr(equipment, 'manufacturing_processes'):
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
            "process_count": len(manifest.manufacturing_processes or [])
        }
        
        return cls(
            facility_name=facility.name or f"Facility {str(facility.id)[:8]}",
            okh_reference=str(manifest.id),
            confidence_score=confidence_score,
            estimated_cost=estimated_cost,
            estimated_time=estimated_time,
            materials_required=materials_required,
            capabilities_used=capabilities_used,
            match_type=match_type,
            metadata=metadata
        )

@dataclass
class SupplyTreeSolution:
    """
    Simplified solution containing simplified supply tree.
    
    This replaces the complex SupplyTreeSolution that contained
    full workflow-based SupplyTree objects.
    """
    tree: SupplyTree
    score: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing"""
        # Truncate score to 2 decimal places
        self.score = round(self.score, 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary"""
        return {
            'tree': self.tree.to_dict(),
            'score': self.score,
            'metrics': self.metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SupplyTreeSolution':
        """Create from dictionary"""
        return cls(
            tree=SupplyTree.from_dict(data['tree']),
            score=data['score'],
            metrics=data.get('metrics', {})
        )
    
    def __hash__(self):
        """Enable Set operations by hashing on facility_name and okh_reference"""
        return hash((self.tree.facility_name, self.tree.okh_reference))
    
    def __eq__(self, other):
        """Enable Set operations by comparing facility_name and okh_reference"""
        if not isinstance(other, SupplyTreeSolution):
            return False
        return (self.tree.facility_name, self.tree.okh_reference) == (other.tree.facility_name, other.tree.okh_reference)

