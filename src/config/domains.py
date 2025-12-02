"""
Domain configuration for the Open Matching Engine

This module defines the configuration for all supported domains,
including their metadata, supported types, and component mappings.
"""

from typing import Dict, Any, Set
from dataclasses import dataclass
from enum import Enum


class DomainStatus(Enum):
    """Status of a domain"""

    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


@dataclass
class DomainConfig:
    """Configuration for a domain"""

    name: str
    display_name: str
    description: str
    version: str
    status: DomainStatus
    supported_input_types: Set[str]
    supported_output_types: Set[str]
    documentation_url: str = None
    maintainer: str = None
    component_module: str = None  # Module path for domain components

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "status": self.status.value,
            "supported_input_types": list(self.supported_input_types),
            "supported_output_types": list(self.supported_output_types),
            "documentation_url": self.documentation_url,
            "maintainer": self.maintainer,
            "component_module": self.component_module,
        }


# Domain configurations
DOMAIN_CONFIGS = {
    "manufacturing": DomainConfig(
        name="manufacturing",
        display_name="Manufacturing & Hardware Production",
        description="Domain for OKH/OKW manufacturing capability matching",
        version="1.0.0",
        status=DomainStatus.ACTIVE,
        supported_input_types={"okh", "okw", "manufacturing_facility"},
        supported_output_types={"supply_tree", "manufacturing_plan", "workflow"},
        documentation_url="https://docs.ome.org/domains/manufacturing",
        maintainer="OME Manufacturing Team",
        component_module="src.core.domains.manufacturing",
    ),
    "cooking": DomainConfig(
        name="cooking",
        display_name="Cooking & Food Preparation",
        description="Domain for recipe and kitchen capability matching",
        version="1.0.0",
        status=DomainStatus.ACTIVE,
        supported_input_types={"recipe", "kitchen", "cooking_facility"},
        supported_output_types={"cooking_workflow", "meal_plan", "recipe_workflow"},
        documentation_url="https://docs.ome.org/domains/cooking",
        maintainer="OME Cooking Team",
        component_module="src.core.domains.cooking",
    ),
}

# Type to domain mapping for automatic detection
TYPE_DOMAIN_MAPPING = {
    "okh": None,  # Ambiguous - can be manufacturing or cooking, requires content detection
    "okw": None,  # Ambiguous - can be manufacturing or cooking, requires content detection
    "manufacturing_facility": "manufacturing",
    "recipe": "cooking",
    "kitchen": "cooking",
    "cooking_facility": "cooking",
}

# Domain-specific keyword mappings for content-based detection
DOMAIN_KEYWORDS = {
    "manufacturing": [
        "machining",
        "tolerance",
        "material",
        "equipment",
        "hardware",
        "manufacturing",
        "fabrication",
        "cnc",
        "3d printing",
        "additive",
        "subtractive",
        "tooling",
        "assembly",
        "production",
        "quality control",
        "inspection",
    ],
    "cooking": [
        "recipe",
        "ingredient",
        "kitchen",
        "cooking",
        "baking",
        "food",
        "meal",
        "preparation",
        "chef",
        "cuisine",
        "flavor",
        "seasoning",
        "nutrition",
        "dietary",
        "allergen",
        "temperature",
        "cooking time",
        # New keywords for OKH/OKW detection
        "oven",
        "stove",
        "refrigerator",
        "mixer",
        "blender",
        "sauté",
        "roast",
        "grill",
        "steam",
        "boil",
        "fry",
    ],
}


def get_domain_config(domain_name: str) -> DomainConfig:
    """Get configuration for a specific domain"""
    if domain_name not in DOMAIN_CONFIGS:
        raise ValueError(f"Unknown domain: {domain_name}")
    return DOMAIN_CONFIGS[domain_name]


def get_all_domain_configs() -> Dict[str, DomainConfig]:
    """Get all domain configurations"""
    return DOMAIN_CONFIGS.copy()


def get_active_domains() -> Dict[str, DomainConfig]:
    """Get only active domain configurations"""
    return {
        name: config
        for name, config in DOMAIN_CONFIGS.items()
        if config.status == DomainStatus.ACTIVE
    }


def infer_domain_from_type(input_type: str) -> str:
    """Infer domain from input type"""
    return TYPE_DOMAIN_MAPPING.get(input_type)


def get_domain_keywords(domain_name: str) -> list:
    """Get keywords for a specific domain"""
    return DOMAIN_KEYWORDS.get(domain_name, [])
