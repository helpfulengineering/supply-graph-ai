"""Policy constants for validation auto-fix behavior."""

from .okh_metadata_codes import METADATA_CODE_MISPLACED_DATA

FIX_WARNING_CODE_PARSE_ERROR = "PARSE_ERROR"
FIX_WARNING_CODE_MISSING_FIELD = "MISSING_FIELD"
FIX_WARNING_CODE_MISSING_RECOMMENDED_FIELD = "MISSING_RECOMMENDED_FIELD"

FIELD_ADDITION_ARRAY_DEFAULTS = {
    "manufacturing_processes": [],
    "equipment": [],
    "typical_materials": [],
    "certifications": [],
    "affiliations": [],
    "tool_list": [],
    "materials": [],
    "parts": [],
}

FIELD_ADDITION_OBJECT_DEFAULTS = {
    "contact": {"name": "Contact information needed", "contact": {}}
}

FIELD_ADDITION_CONFIDENCE = {
    "array_required": 0.3,
    "array_recommended": 0.2,
    "object_required": 0.2,
    "object_recommended": 0.1,
}

DATA_MOVEMENT_CONFIDENCE = {
    METADATA_CODE_MISPLACED_DATA: 0.9,
    "default": 0.75,
}
