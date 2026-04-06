"""Canonical storage constants for object keys and metadata."""

from uuid import UUID

SUPPLY_TREE_SOLUTIONS_PREFIX = "supply-tree-solutions"
SUPPLY_TREE_SOLUTIONS_METADATA_PREFIX = f"{SUPPLY_TREE_SOLUTIONS_PREFIX}/metadata"

AUTH_API_KEYS_PREFIX = "auth/api-keys"

STORAGE_OBJECT_TYPE_SUPPLY_TREE = "supply_tree"
STORAGE_OBJECT_TYPE_SUPPLY_TREE_SOLUTION = "supply_tree_solution"
STORAGE_OBJECT_TYPE_SOLUTION_METADATA = "solution_metadata"
STORAGE_OBJECT_TYPE_API_KEY = "api_key"

DEFAULT_SOLUTION_TTL_DAYS = 30


def build_solution_key(solution_id: UUID) -> str:
    """Build storage key for a supply tree solution payload."""
    return f"{SUPPLY_TREE_SOLUTIONS_PREFIX}/{solution_id}.json"


def build_solution_metadata_key(solution_id: UUID) -> str:
    """Build storage key for a supply tree solution metadata payload."""
    return f"{SUPPLY_TREE_SOLUTIONS_METADATA_PREFIX}/{solution_id}.json"
