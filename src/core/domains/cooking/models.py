from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List
from uuid import UUID, uuid4

# Cooking-specific fields that distinguish a kitchen file from a manufacturing
# facility file.  At least one of these keys must be present for a JSON blob
# to be treated as a KitchenCapability.
_KITCHEN_FIELDS = {"appliances", "tools", "ingredients"}

# Presence of this key unambiguously marks a manufacturing facility file and
# takes priority over any incidental cooking fields.
_MANUFACTURING_DISCRIMINATOR = "facility_status"


@dataclass
class KitchenCapability:
    """A cooking-domain capability record stored under okw/ in remote storage.

    Kept intentionally lean: the three list fields map directly to the
    simple-format path in ``CookingExtractor._detailed_extract_capabilities()``.
    """

    id: UUID
    name: str
    appliances: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    ingredients: List[str] = field(default_factory=list)
    domain: str = "cooking"

    # ------------------------------------------------------------------ #
    # Factory / serialisation                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KitchenCapability":
        """Parse a raw dictionary into a KitchenCapability.

        Raises ``ValueError`` if required keys are missing.
        """
        if "id" not in data:
            raise ValueError("KitchenCapability requires an 'id' field")
        if "name" not in data:
            raise ValueError("KitchenCapability requires a 'name' field")

        return cls(
            id=UUID(str(data["id"])),
            name=str(data["name"]),
            appliances=list(data.get("appliances", [])),
            tools=list(data.get("tools", [])),
            ingredients=list(data.get("ingredients", [])),
            domain=str(data.get("domain", "cooking")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dictionary suitable for JSON serialisation and for
        passing directly into ``CookingExtractor.extract_capabilities()``.

        The three list keys (``appliances``, ``tools``, ``ingredients``) match
        the simple-format path in ``CookingExtractor._detailed_extract_capabilities()``.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "appliances": list(self.appliances),
            "tools": list(self.tools),
            "ingredients": list(self.ingredients),
            "domain": self.domain,
        }

    # ------------------------------------------------------------------ #
    # Type discriminator                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_kitchen_data(data: Dict[str, Any]) -> bool:
        """Return ``True`` when *data* looks like a kitchen file.

        Rules (evaluated in order):
        1. Any data containing ``facility_status`` is a manufacturing file → False.
        2. Data that contains at least one kitchen-specific key
           (``appliances``, ``tools``, ``ingredients``) with a non-empty value
           OR with the key present at all → True.
        3. Everything else → False.
        """
        if not data:
            return False
        if _MANUFACTURING_DISCRIMINATOR in data:
            return False
        return bool(_KITCHEN_FIELDS & data.keys())

    @staticmethod
    def is_cooking_capability(data: Dict[str, Any]) -> bool:
        """Return ``True`` when *data* should be treated as a cooking capability.

        Domain-first: if ``domain`` is set, it overrides heuristic shape.
        - ``domain == "manufacturing"`` → False (treat as manufacturing).
        - ``domain == "cooking"`` → True (treat as cooking).
        - Otherwise fall back to ``is_kitchen_data(data)``.
        """
        if not data:
            return False
        domain = data.get("domain")
        if domain == "manufacturing":
            return False
        if domain == "cooking":
            return True
        return KitchenCapability.is_kitchen_data(data)
