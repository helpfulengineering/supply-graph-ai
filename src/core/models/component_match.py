"""
ComponentMatch data model for nested supply tree generation.

This model represents a component during the matching process,
tracking its position in the component hierarchy and any resolved references.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .bom import Component
from .okh import OKHManifest
from .supply_trees import SupplyTree


@dataclass
class ComponentMatch:
    """Represents a component in the matching process"""
    
    component: Component
    """The component being matched"""
    
    depth: int
    """Depth in hierarchy (0 = top level)"""
    
    parent_component_id: Optional[str] = None
    """ID of parent component (None for root)"""
    
    okh_manifest: Optional[OKHManifest] = None
    """Resolved OKH manifest if component references one"""
    
    path: List[str] = field(default_factory=list)
    """Path from root (e.g., ['Device', 'Housing', 'Frame'])"""
    
    matched: bool = False
    """Whether this component has been matched to facilities"""
    
    supply_trees: List[SupplyTree] = field(default_factory=list)
    """SupplyTrees generated for this component"""
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation"""
        result = {
            "component": self.component.to_dict(),
            "depth": self.depth,
            "path": self.path,
            "matched": self.matched,
        }
        
        if self.parent_component_id:
            result["parent_component_id"] = self.parent_component_id
        
        if self.okh_manifest:
            result["okh_manifest"] = self.okh_manifest.to_dict()
        
        if self.supply_trees:
            result["supply_trees"] = [tree.to_dict() for tree in self.supply_trees]
        
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> "ComponentMatch":
        """Create from dictionary representation"""
        from .bom import Component
        from .okh import OKHManifest
        from .supply_trees import SupplyTree
        
        component = Component.from_dict(data["component"])
        okh_manifest = None
        if "okh_manifest" in data and data["okh_manifest"]:
            okh_manifest = OKHManifest.from_dict(data["okh_manifest"])
        
        supply_trees = []
        if "supply_trees" in data and data["supply_trees"]:
            supply_trees = [SupplyTree.from_dict(tree_data) for tree_data in data["supply_trees"]]
        
        return cls(
            component=component,
            depth=data["depth"],
            parent_component_id=data.get("parent_component_id"),
            okh_manifest=okh_manifest,
            path=data.get("path", []),
            matched=data.get("matched", False),
            supply_trees=supply_trees
        )

