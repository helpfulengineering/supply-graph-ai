"""Shared client-facing API error messages."""

ERROR_NO_FILE_PROVIDED = "No file provided"
ERROR_UNSUPPORTED_YAML_JSON_FILE = (
    "Unsupported file type. Please upload a YAML (.yaml, .yml) or JSON (.json) file"
)


def format_invalid_file_format_detail(error: Exception) -> str:
    """Build a consistent invalid file format error detail."""
    return f"Invalid file format: {str(error)}"
