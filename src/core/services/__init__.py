"""
Core services module for the Open Matching Engine (OME).

This module provides standardized service classes and utilities for managing
OKH manifests, OKW facilities, matching operations, and other core functionality.

All services inherit from BaseService to ensure consistent patterns for:
- Initialization and lifecycle management
- Error handling and logging
- Configuration management
- Metrics tracking
- LLM integration preparation
"""

from .base import (
    BaseService,
    ServiceConfig,
    ServiceMetrics,
    ServiceStatus
)

from .okh_service import OKHService
from .okw_service import OKWService
from .matching_service import MatchingService
from .storage_service import StorageService
from .package_service import PackageService
from .service_registry import ServiceRegistry

__all__ = [
    # Base classes
    "BaseService",
    "ServiceConfig", 
    "ServiceMetrics",
    "ServiceStatus",
    
    # Concrete services
    "OKHService",
    "OKWService", 
    "MatchingService",
    "StorageService",
    "PackageService",
    "ServiceRegistry"
]
