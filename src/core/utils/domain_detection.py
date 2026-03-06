"""
Domain detection utilities for OKH and OKW data.

Provides a single canonical function for detecting whether a manifest or
facility dict belongs to the ``manufacturing`` or ``cooking`` domain.  All
CLI commands and API handlers should call :func:`detect_domain` rather than
implementing their own heuristics.
"""

from typing import Any, Dict

# Keywords in function/description text that suggest the cooking domain
_COOKING_CONTENT_KEYWORDS = (
    "recipe",
    "cooking",
    "baking",
    "ingredient",
    "food",
    "meal",
    "kitchen",
    "oven",
    "stove",
)

# Top-level dict keys that are strong structural indicators of the cooking domain
_COOKING_STRUCTURAL_KEYS = {"ingredients", "instructions"}

# Top-level dict keys that are strong structural indicators of the manufacturing domain
_MANUFACTURING_STRUCTURAL_KEYS = {"manufacturing_specs", "manufacturing_processes"}


def detect_domain(data: Dict[str, Any], default: str = "manufacturing") -> str:
    """
    Detect the domain (``"manufacturing"`` or ``"cooking"``) for a manifest
    or facility dictionary.

    Resolution order
    ----------------
    1. Explicit ``domain`` field in *data* — returned as-is if present.
    2. Structural OKH/manufacturing keys — ``manufacturing_specs`` or
       ``manufacturing_processes`` present alongside ``title`` and ``version``.
    3. Structural cooking keys — both ``ingredients`` and ``instructions``
       present alongside ``name``.
    4. Content heuristics — cooking keywords found in ``function`` or
       ``description`` text.
    5. *default* (``"manufacturing"``) — fallback for backward compatibility.

    Parameters
    ----------
    data:
        Dictionary representation of an OKH manifest or OKW facility.
    default:
        Domain to return when no signal is found.  Defaults to
        ``"manufacturing"`` for backward compatibility.

    Returns
    -------
    str
        ``"manufacturing"`` or ``"cooking"`` (or *default*).
    """
    # 1. Explicit domain field
    explicit = data.get("domain")
    if explicit:
        return str(explicit)

    # 2. Structural manufacturing indicators
    if (
        "title" in data
        and "version" in data
        and data.keys() & _MANUFACTURING_STRUCTURAL_KEYS
    ):
        return "manufacturing"

    # 3. Structural cooking indicators
    if "name" in data and _COOKING_STRUCTURAL_KEYS.issubset(data.keys()):
        return "cooking"

    # 4. Content heuristics — scan free-text fields
    content = " ".join(
        str(data.get(field, ""))
        for field in ("function", "description", "title", "name")
    ).lower()
    if any(kw in content for kw in _COOKING_CONTENT_KEYWORDS):
        return "cooking"

    # 5. Fallback
    return default
