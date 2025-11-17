"""
Version information for Open Matching Engine (OME).

This module provides a single source of truth for the OME version.
Update this value when releasing a new version.
"""

__version__ = "1.0.0"

# Version components for programmatic access
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0


def get_version() -> str:
    """Get the current OME version."""
    return __version__


def get_version_tuple() -> tuple:
    """Get version as a tuple (major, minor, patch)."""
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)

