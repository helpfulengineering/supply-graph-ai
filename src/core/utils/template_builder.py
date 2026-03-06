"""
Blank manifest template builder for OKH and OKW models.

Generates an empty JSON template dict from a dataclass definition.
All required fields are included as empty strings / zero values; all
optional fields are shown as ``null``; list fields are shown as ``[]``.

Users can fill the template in manually or use the ``create-interactive``
command for a guided experience.
"""

import dataclasses
import inspect
from enum import Enum
from typing import Any, Dict, Type, get_args, get_origin

# Built-in collection types that should default to empty list
_LIST_ORIGINS = (list,)

# Type name → empty placeholder mapping for scalar types
_SCALAR_DEFAULTS: Dict[str, Any] = {
    "str": "",
    "int": 0,
    "float": 0.0,
    "bool": False,
}


def build_blank_template(cls: Type) -> Dict[str, Any]:
    """
    Build a blank JSON-serialisable template dict from a dataclass type.

    Rules
    -----
    * Required fields with no default → ``""`` for str, ``0`` for int/float,
      ``false`` for bool, ``{}`` for nested dataclasses.
    * Optional fields (``Optional[X]``) → ``null``.
    * List fields → ``[]``.
    * Enum fields → the string value of the first enum member.
    * Nested dataclasses → recursed into (only one level deep for templates).
    * UUID fields → ``""`` (placeholder).
    """
    if not dataclasses.is_dataclass(cls):
        raise TypeError(f"{cls} is not a dataclass")

    result: Dict[str, Any] = {}

    for f in dataclasses.fields(cls):
        field_type = f.type

        # Resolve string annotations to actual types where possible
        if isinstance(field_type, str):
            try:
                import sys

                module = sys.modules.get(cls.__module__, None)
                ns = getattr(module, "__dict__", {}) if module else {}
                field_type = eval(field_type, ns)  # noqa: S307
            except Exception:
                # If we can't resolve, default to ""
                result[f.name] = ""
                continue

        result[f.name] = _default_for_type(field_type, f)

    return result


def _struct_template_for(t: Any) -> Any:
    """
    Return a structured template value for complex types, or ``None`` for plain
    scalars (signalling the caller should fall back to ``[]`` / ``""``).

    Handles:
    * Dataclass  → ``build_blank_template(t)``
    * ``dict``   → ``{}``
    * ``Union[X, Y, ...]`` — picks the most structured non-None member
    """
    import typing

    if dataclasses.is_dataclass(t):
        return build_blank_template(t)
    if t is dict or get_origin(t) is dict:
        return {}

    inner_origin = get_origin(t)
    inner_args = get_args(t)
    if inner_origin is typing.Union:
        for arg in inner_args:
            if arg is not type(None) and dataclasses.is_dataclass(arg):
                return build_blank_template(arg)
        for arg in inner_args:
            if arg is not type(None) and (arg is dict or get_origin(arg) is dict):
                return {}

    return None


def _default_for_type(field_type: Any, field: dataclasses.Field) -> Any:
    """Derive the blank-template value for a given field type."""
    import typing

    origin = get_origin(field_type)
    args = get_args(field_type)

    # Union[X, None] (Optional) or Union[X, Y, ...] (non-optional Union)
    if origin is typing.Union:
        non_none_args = [a for a in args if a is not type(None)]
        is_optional = len(non_none_args) < len(args)

        # Prefer the most structured type: dataclass > List[dataclass] > dict > scalar
        for arg in non_none_args:
            if dataclasses.is_dataclass(arg):
                return build_blank_template(arg)

        for arg in non_none_args:
            inner_origin = get_origin(arg)
            inner_args = get_args(arg)
            if inner_origin in _LIST_ORIGINS and inner_args:
                structured = _struct_template_for(inner_args[0])
                if structured is not None:
                    return [structured]
                # List[scalar]: fall through to scalar fallback below

        for arg in non_none_args:
            if arg is dict or get_origin(arg) is dict:
                return {}

        # All scalar args (str, int, …)
        return None if is_optional else ""

    # List[X] → [{...}] for structured element types, [] for scalars
    if origin in _LIST_ORIGINS or (origin is None and field_type is list):
        if args:
            structured = _struct_template_for(args[0])
            if structured is not None:
                return [structured]
        return []

    # Check field default / default_factory first
    has_default = field.default is not dataclasses.MISSING
    has_factory = field.default_factory is not dataclasses.MISSING  # type: ignore[misc]

    # Enum → first value as string (or the declared default)
    if inspect.isclass(field_type) and issubclass(field_type, Enum):
        members = list(field_type)
        if has_default and isinstance(field.default, field_type):
            return field.default.value
        return members[0].value if members else ""

    # Nested dataclass → recurse
    if dataclasses.is_dataclass(field_type):
        return build_blank_template(field_type)

    # UUID
    type_name = getattr(field_type, "__name__", "")
    if type_name == "UUID":
        return ""

    # datetime / date
    if type_name in ("datetime", "date"):
        return ""

    # Plain dict
    if field_type is dict or get_origin(field_type) is dict:
        return {}

    # Scalar types
    scalar = _SCALAR_DEFAULTS.get(type_name)
    if scalar is not None:
        return type(scalar)()

    # Fallback: use the field's default if available
    if has_default:
        default_val = field.default
        if isinstance(default_val, Enum):
            return default_val.value
        return default_val
    if has_factory:
        return field.default_factory()  # type: ignore[misc]

    return ""


def strip_none_for_toml(obj: Any) -> Any:
    """
    Recursively remove ``None`` values from a template dict so the result is
    safe to pass to ``tomli_w.dumps()``.

    TOML has no null type.  Optional fields that have not been filled in are
    simply omitted from the TOML output — the absence of a key is the TOML
    equivalent of ``null``.

    Lists are kept as-is (empty lists are valid TOML).  Nested dicts are
    processed recursively, and any dict that becomes empty after stripping is
    also omitted.
    """
    if isinstance(obj, dict):
        stripped = {k: strip_none_for_toml(v) for k, v in obj.items() if v is not None}
        # Further drop any nested dict that became entirely empty after stripping
        return {k: v for k, v in stripped.items() if v != {}}
    if isinstance(obj, list):
        return [strip_none_for_toml(item) for item in obj if item is not None]
    return obj


def okh_blank_template() -> Dict[str, Any]:
    """Return a blank OKH manifest template dict."""
    from ..models.okh import OKHManifest

    return build_blank_template(OKHManifest)


def okw_blank_template() -> Dict[str, Any]:
    """Return a blank OKW facility template dict."""
    from ..models.okw import ManufacturingFacility

    return build_blank_template(ManufacturingFacility)
