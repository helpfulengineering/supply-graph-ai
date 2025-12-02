"""
BOM (Bill of Materials) data models
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from uuid import uuid4


@dataclass
class Component:
    """Represents a component in a Bill of Materials"""

    id: str
    name: str
    quantity: float
    unit: str
    sub_components: List["Component"] = field(default_factory=list)
    reference: Optional[Dict[str, str]] = None
    requirements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate component data"""
        if not self.id:
            self.id = str(uuid4())
        if not self.name:
            raise ValueError("Component must have a name")
        if self.quantity <= 0:
            raise ValueError("Component quantity must be positive")
        if not self.unit:
            raise ValueError("Component must have a unit")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = {
            "id": self.id,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "requirements": self.requirements,
            "metadata": self.metadata,
        }

        if self.sub_components:
            result["sub_components"] = [c.to_dict() for c in self.sub_components]

        if self.reference:
            result["reference"] = self.reference

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Component":
        """Create from dictionary representation"""
        sub_components = []

        if "sub_components" in data:
            for comp_data in data["sub_components"]:
                sub_components.append(cls.from_dict(comp_data))

        return cls(
            id=data.get("id", str(uuid4())),
            name=data["name"],
            quantity=data["quantity"],
            unit=data["unit"],
            sub_components=sub_components,
            reference=data.get("reference"),
            requirements=data.get("requirements", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class BillOfMaterials:
    """Container for a complete Bill of Materials"""

    name: str
    components: List[Component]
    id: str = field(default_factory=lambda: str(uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "name": self.name,
            "components": [c.to_dict() for c in self.components],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BillOfMaterials":
        """Create from dictionary representation"""
        components = [Component.from_dict(c) for c in data.get("components", [])]

        bom = cls(
            name=data["name"], components=components, metadata=data.get("metadata", {})
        )

        if "id" in data:
            bom.id = data["id"]

        return bom
