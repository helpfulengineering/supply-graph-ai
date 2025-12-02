"""
OKH Package Management Module

This module provides functionality for building self-contained OKH packages
by downloading all externally-linked files and organizing them in a
standardized directory structure.
"""

from .file_resolver import FileResolver
from .builder import PackageBuilder

__all__ = ["FileResolver", "PackageBuilder"]
