"""
JSON Schema Generator for Dataclasses

This utility generates JSON schemas in canonical format from Python dataclasses
using Pydantic's schema generation capabilities.
"""

import inspect
from dataclasses import MISSING, dataclass, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Optional, Type
from uuid import UUID

try:
    from pydantic import TypeAdapter, create_model
    from pydantic.json_schema import JsonSchemaValue
except ImportError:
    raise ImportError(
        "Pydantic is required for schema generation. Install with: pip install pydantic"
    )


def generate_json_schema(
    dataclass_type: Type, title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a JSON schema in canonical format from a dataclass.

    Args:
        dataclass_type: The dataclass type to generate a schema for
        title: Optional title for the schema (defaults to class name)

    Returns:
        A JSON schema dictionary in canonical format

    Example:
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class Example:
        ...     name: str
        ...     age: int
        >>> schema = generate_json_schema(Example)
    """
    if not is_dataclass(dataclass_type):
        raise ValueError(f"{dataclass_type} is not a dataclass")

    # Use Pydantic's TypeAdapter to generate schema
    try:
        adapter = TypeAdapter(dataclass_type)
        schema = adapter.json_schema()

        # Ensure schema has proper title
        if title:
            schema["title"] = title
        elif "title" not in schema:
            schema["title"] = dataclass_type.__name__

        # Ensure schema has proper $schema reference
        if "$schema" not in schema:
            schema["$schema"] = "http://json-schema.org/draft-07/schema#"

        # Add description if available
        if hasattr(dataclass_type, "__doc__") and dataclass_type.__doc__:
            schema["description"] = dataclass_type.__doc__.strip()

        # Ensure proper format
        schema = _normalize_schema(schema, dataclass_type)

        return schema
    except Exception as e:
        # Fallback: generate schema manually
        return _generate_schema_manually(dataclass_type, title)


def _normalize_schema(schema: Dict[str, Any], dataclass_type: Type) -> Dict[str, Any]:
    """
    Normalize the schema to ensure canonical format.

    This handles:
    - Converting Pydantic-specific formats to standard JSON Schema
    - Ensuring proper type definitions
    - Handling nested dataclasses
    """
    # Ensure required fields are properly defined
    if "properties" in schema:
        required_fields = []
        for field in fields(dataclass_type):
            # Check if field has a default value
            if field.default is MISSING and field.default_factory is MISSING:
                required_fields.append(field.name)

        if required_fields:
            schema["required"] = required_fields

    # Recursively normalize nested schemas
    if "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            if isinstance(prop_schema, dict):
                schema["properties"][prop_name] = _normalize_property_schema(
                    prop_schema
                )

    # Handle definitions/defs for nested types
    if "definitions" in schema:
        for def_name, def_schema in schema["definitions"].items():
            if isinstance(def_schema, dict):
                schema["definitions"][def_name] = _normalize_property_schema(def_schema)

    return schema


def _normalize_property_schema(prop_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a property schema to canonical format."""
    # Handle enum types
    if "enum" in prop_schema:
        # Keep enum as is
        pass

    # Handle array types
    if "items" in prop_schema:
        if isinstance(prop_schema["items"], dict):
            prop_schema["items"] = _normalize_property_schema(prop_schema["items"])

    # Handle union types (anyOf)
    if "anyOf" in prop_schema:
        prop_schema["anyOf"] = [
            _normalize_property_schema(item) if isinstance(item, dict) else item
            for item in prop_schema["anyOf"]
        ]

    return prop_schema


def _generate_schema_manually(
    dataclass_type: Type, title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fallback method to generate schema manually if Pydantic fails.

    This is a basic implementation that handles common types.
    """
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "title": title or dataclass_type.__name__,
        "properties": {},
        "required": [],
    }

    if hasattr(dataclass_type, "__doc__") and dataclass_type.__doc__:
        schema["description"] = dataclass_type.__doc__.strip()

    for field in fields(dataclass_type):
        field_schema = _get_field_schema(field)
        schema["properties"][field.name] = field_schema

        # Add to required if no default
        if field.default is MISSING and field.default_factory is MISSING:
            schema["required"].append(field.name)

    return schema


def _get_field_schema(field) -> Dict[str, Any]:
    """Get JSON schema for a dataclass field."""
    field_type = field.type
    origin = getattr(field_type, "__origin__", None)

    # Handle Optional types
    if origin is not None:
        if hasattr(field_type, "__args__"):
            args = field_type.__args__
            # Check if it's Optional (Union with None)
            if type(None) in args:
                # Get the non-None type
                non_none_types = [arg for arg in args if arg is not type(None)]
                if non_none_types:
                    return _type_to_schema(non_none_types[0])

            # Handle List types
            if origin is list:
                if args:
                    return {"type": "array", "items": _type_to_schema(args[0])}

            # Handle Dict types
            if origin is dict:
                return {"type": "object", "additionalProperties": True}

            # Handle Union types
            if origin is type(None) or (
                hasattr(origin, "__name__") and origin.__name__ == "Union"
            ):
                # For Union, use anyOf
                non_none_types = [arg for arg in args if arg is not type(None)]
                if len(non_none_types) == 1:
                    return _type_to_schema(non_none_types[0])
                elif len(non_none_types) > 1:
                    return {"anyOf": [_type_to_schema(t) for t in non_none_types]}

    return _type_to_schema(field_type)


def _type_to_schema(python_type: Type) -> Dict[str, Any]:
    """Convert a Python type to JSON schema type."""
    # Handle dataclasses
    if is_dataclass(python_type):
        return {
            "type": "object",
            "title": python_type.__name__,
            "properties": {},
            "required": [],
        }

    # Handle enums
    if inspect.isclass(python_type) and issubclass(python_type, Enum):
        return {"type": "string", "enum": [e.value for e in python_type]}

    # Handle built-in functions (like 'any') - treat as object
    if (
        not inspect.isclass(python_type)
        and callable(python_type)
        and python_type.__name__ in ["any", "all"]
    ):
        return {"type": "object", "additionalProperties": True}

    # Handle basic types
    type_mapping = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        UUID: {"type": "string", "format": "uuid"},
        date: {"type": "string", "format": "date"},
        datetime: {"type": "string", "format": "date-time"},
        dict: {"type": "object", "additionalProperties": True},
        list: {"type": "array"},
        type(None): {"type": "null"},
    }

    if python_type in type_mapping:
        return type_mapping[python_type]

    # Default to object for unknown types
    return {"type": "object", "additionalProperties": True}
