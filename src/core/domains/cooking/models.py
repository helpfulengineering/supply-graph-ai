from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List
from uuid import UUID

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


# Cooking-specific fields that distinguish a simple-format recipe file from
# an OKH manifest. At least one of these keys must be present for a JSON blob
# to be treated as a Recipe via the simple format.
_RECIPE_FIELDS = {"ingredients", "instructions", "equipment"}

# Presence of this key marks an OKH-shaped manifest file (license is required
# on every real OKH manifest, recipe or hardware).
_OKH_DISCRIMINATOR = "license"

# manufacturing_processes verbs that mark an OKH-shaped manifest as a recipe
# rather than a hardware design. The OKH schema is generic enough to describe
# a recipe's bill of materials, tools, and instructions exactly as well as a
# hardware design's (see CookingExtractor._detailed_extract_requirements(),
# which already parses this same tool_list/materials/making_instructions
# shape for matching) -- shape alone cannot tell the two apart, so this is the
# one positive cooking signal available on legacy OKH-shaped recipe data that
# predates the `domain` field.
_OKH_COOKING_PROCESSES = {
    "bake",
    "boil",
    "braise",
    "broil",
    "chill",
    "cook",
    "ferment",
    "freeze",
    "fry",
    "grill",
    "knead",
    "marinate",
    "mix",
    "poach",
    "roast",
    "saute",
    "sauté",
    "simmer",
    "steam",
    "stir",
    "whisk",
}


def _has_okh_cooking_process(data: Dict[str, Any]) -> bool:
    processes = data.get("manufacturing_processes")
    if not isinstance(processes, list):
        return False
    return any(
        isinstance(p, str) and p.strip().lower() in _OKH_COOKING_PROCESSES
        for p in processes
    )


def _okh_material_names(data: Dict[str, Any]) -> List[str]:
    """Ingredient names from an OKH manifest's ``materials`` field, falling
    back to the non-standard ``metadata.original.bom_atoms`` mapping some
    hand-authored recipe manifests use instead (keys are ingredient names)."""
    names: List[str] = []
    for material in data.get("materials") or []:
        if isinstance(material, str):
            if material:
                names.append(material)
        elif isinstance(material, dict):
            name = (
                material.get("name")
                or material.get("material_type")
                or material.get("identifier")
            )
            if name:
                names.append(str(name))
    if not names:
        bom_atoms = ((data.get("metadata") or {}).get("original") or {}).get(
            "bom_atoms"
        )
        if isinstance(bom_atoms, dict):
            names = [str(k) for k in bom_atoms.keys()]
    return names


def _okh_tool_names(data: Dict[str, Any]) -> List[str]:
    """Equipment names from an OKH manifest's ``tool_list`` field."""
    names: List[str] = []
    for tool in data.get("tool_list") or []:
        if isinstance(tool, str):
            if tool:
                names.append(tool)
        elif isinstance(tool, dict):
            name = tool.get("name") or tool.get("tool") or tool.get("identifier")
            if name:
                names.append(str(name))
    return names


def _okh_instructions(data: Dict[str, Any]) -> List[str]:
    """Instruction steps from an OKH manifest's ``making_instructions`` field,
    falling back to its ``manufacturing_processes`` (cooking techniques) when
    no instructions are present."""
    steps: List[str] = []
    for instruction in data.get("making_instructions") or []:
        if isinstance(instruction, str):
            if instruction:
                steps.append(instruction)
        elif isinstance(instruction, dict):
            step = instruction.get("title") or instruction.get("path")
            if step:
                steps.append(str(step))
    if not steps:
        steps = [
            str(p)
            for p in (data.get("manufacturing_processes") or [])
            if isinstance(p, str)
        ]
    return steps


@dataclass
class Recipe:
    """A cooking-domain recipe record stored under okh/ in remote storage.

    Kept intentionally lean: the three list fields map directly to the
    simple-format path in ``CookingExtractor._detailed_extract_requirements()``.
    """

    id: UUID
    name: str
    ingredients: List[str] = field(default_factory=list)
    instructions: List[str] = field(default_factory=list)
    equipment: List[str] = field(default_factory=list)
    domain: str = "cooking"

    # ------------------------------------------------------------------ #
    # Factory / serialisation                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Recipe":
        """Parse a raw dictionary into a Recipe.

        Accepts both the simple format (``ingredients``/``instructions``/
        ``equipment``) and an OKH-shaped recipe (``title``/``materials``/
        ``tool_list``/``making_instructions``/``manufacturing_processes``),
        falling back field-by-field to the OKH equivalent so a partially
        simple-format file (e.g. explicit ``ingredients`` but no
        ``instructions``) still fills in from OKH fields where present.
        Mirrors ``CookingExtractor._detailed_extract_requirements()``, which
        parses this same OKH shape for matching.

        Raises ``ValueError`` if required keys (id, and either name or title)
        are missing.
        """
        if "id" not in data:
            raise ValueError("Recipe requires an 'id' field")
        name = data.get("name") or data.get("title")
        if not name:
            raise ValueError("Recipe requires a 'name' (or OKH 'title') field")

        return cls(
            id=UUID(str(data["id"])),
            name=str(name),
            ingredients=list(data.get("ingredients") or _okh_material_names(data)),
            instructions=list(data.get("instructions") or _okh_instructions(data)),
            equipment=list(data.get("equipment") or _okh_tool_names(data)),
            domain=str(data.get("domain", "cooking")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dictionary suitable for JSON serialisation and for
        passing directly into ``CookingExtractor.extract_requirements()``.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "ingredients": list(self.ingredients),
            "instructions": list(self.instructions),
            "equipment": list(self.equipment),
            "domain": self.domain,
        }

    # ------------------------------------------------------------------ #
    # Type discriminator                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_recipe_data(data: Dict[str, Any]) -> bool:
        """Return ``True`` when *data* looks like a recipe file.

        Rules (evaluated in order):
        1. Data that contains at least one simple-format recipe key
           (``ingredients``, ``instructions``, ``equipment``) → True.
        2. An OKH-shaped manifest (has ``license``) is a recipe only if its
           ``manufacturing_processes`` name a cooking technique (e.g.
           ``"bake"``) → True. Otherwise it is a hardware design → False.
        3. Everything else → False.
        """
        if not data:
            return False
        if _RECIPE_FIELDS & data.keys():
            return True
        if _OKH_DISCRIMINATOR in data:
            return _has_okh_cooking_process(data)
        return False

    @staticmethod
    def is_cooking_recipe(data: Dict[str, Any]) -> bool:
        """Return ``True`` when *data* should be treated as a recipe.

        Domain-first: if ``domain`` is set, it overrides heuristic shape.
        - ``domain == "manufacturing"`` → False (treat as OKH manifest).
        - ``domain == "cooking"`` → True (treat as recipe).
        - Otherwise fall back to ``is_recipe_data(data)``.
        """
        if not data:
            return False
        domain = data.get("domain")
        if domain == "manufacturing":
            return False
        if domain == "cooking":
            return True
        return Recipe.is_recipe_data(data)
