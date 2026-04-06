"""Canonical OKH metadata warning codes and formatting helpers."""

METADATA_CODE_TYPO = "METADATA_TYPO"
METADATA_CODE_FORMAT_ERROR = "METADATA_FORMAT_ERROR"
METADATA_CODE_MISPLACED_DATA = "METADATA_MISPLACED_DATA"
METADATA_CODE_DUPLICATE_DATA = "METADATA_DUPLICATE_DATA"
METADATA_CODE_UNKNOWN_FIELD = "METADATA_UNKNOWN_FIELD"
METADATA_CODE_EXCESSIVE_SIZE = "METADATA_EXCESSIVE_SIZE"


METADATA_WARNING_CODES = {
    "typo": METADATA_CODE_TYPO,
    "format_error": METADATA_CODE_FORMAT_ERROR,
    "misplaced_data": METADATA_CODE_MISPLACED_DATA,
    "duplicate_data": METADATA_CODE_DUPLICATE_DATA,
    "unknown_field": METADATA_CODE_UNKNOWN_FIELD,
    "excessive_size": METADATA_CODE_EXCESSIVE_SIZE,
}


def format_metadata_warning(code: str, message: str) -> str:
    """Format metadata warning message with canonical code prefix."""
    return f"[{code}] {message}"
