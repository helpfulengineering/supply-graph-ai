"""Unified cache layer — pluggable backends for API and service caching."""

from .backends.base import CacheBackend, CacheStats
from .helper import cached
from .keys import namespaced_key

__all__ = ["CacheBackend", "CacheStats", "cached", "namespaced_key"]
