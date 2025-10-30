"""
Base service classes and utilities for the Open Matching Engine (OME).

This module provides standardized base classes and utilities that all services
inherit from, ensuring consistent patterns for initialization, error handling,
configuration management, and metrics tracking.

The base service architecture provides:
- Standardized singleton pattern implementation
- Common initialization and lifecycle management
- Consistent error handling and logging
- Configuration management utilities
- Metrics tracking for performance and usage
- LLM integration preparation interfaces

All services inherit from BaseService and must implement the required abstract methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, TypeVar, Generic, Type
from datetime import datetime, timedelta
from enum import Enum
import logging
import asyncio
from contextlib import asynccontextmanager

from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class ServiceStatus(Enum):
    """Status of a service instance."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"


@dataclass
class ServiceMetrics:
    """Metrics for tracking service performance and usage."""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    errors: List[str] = field(default_factory=list)
    average_response_time_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    configuration_changes: int = 0
    initialization_time_ms: float = 0.0

    @property
    def uptime(self) -> Optional[timedelta]:
        """Get service uptime."""
        if self.end_time:
            return self.end_time - self.start_time
        return datetime.now() - self.start_time

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "errors": self.errors,
            "average_response_time_ms": self.average_response_time_ms,
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
            "configuration_changes": self.configuration_changes,
            "initialization_time_ms": self.initialization_time_ms,
            "uptime_seconds": self.uptime.total_seconds() if self.uptime else None,
            "success_rate": self.success_rate
        }


@dataclass
class ServiceConfig:
    """Base configuration for services."""
    name: str
    version: str = "1.0.0"
    enabled: bool = True
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    log_level: str = "INFO"
    metrics_enabled: bool = True
    llm_integration_enabled: bool = False
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "log_level": self.log_level,
            "metrics_enabled": self.metrics_enabled,
            "llm_integration_enabled": self.llm_integration_enabled,
            "custom_settings": self.custom_settings
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceConfig':
        """Create configuration from dictionary."""
        return cls(**data)


class BaseService(ABC, Generic[T]):
    """
    Abstract base class for all OME services.

    This class provides a standardized foundation for all services, including:
    - Singleton pattern implementation
    - Common initialization and lifecycle management
    - Consistent error handling and logging
    - Configuration management
    - Metrics tracking
    - LLM integration preparation

    All concrete services must inherit from this class and implement the
    required abstract methods.
    """

    _instances: Dict[str, 'BaseService'] = {}
    _initialization_locks: Dict[str, asyncio.Lock] = {}

    def __init__(self, service_name: str, config: Optional[ServiceConfig] = None):
        """
        Initialize the base service.

        Args:
            service_name: Unique name for this service instance
            config: Service configuration. If None, uses default configuration.
        """
        self.service_name = service_name
        self.config = config or ServiceConfig(name=service_name)
        self.status = ServiceStatus.UNINITIALIZED
        self.metrics = ServiceMetrics(start_time=datetime.now())
        self.logger = get_logger(f"{__name__}.{service_name}")
        self._dependencies: Dict[str, Any] = {}
        self._initialization_start_time: Optional[datetime] = None

        self.logger.info(f"Initializing {service_name} service")

    @classmethod
    async def get_instance(
        cls,
        service_name: Optional[str] = None,
        config: Optional[ServiceConfig] = None,
        **kwargs
    ) -> T:
        """
        Get singleton instance of the service.

        Args:
            service_name: Name for the service instance. If None, uses class name.
            config: Service configuration.
            **kwargs: Additional arguments passed to service constructor.

        Returns:
            Service instance.
        """
        if service_name is None:
            service_name = cls.__name__

        if service_name not in cls._instances:
            # Create initialization lock if it doesn't exist
            if service_name not in cls._initialization_locks:
                cls._initialization_locks[service_name] = asyncio.Lock()

            async with cls._initialization_locks[service_name]:
                # Double-check pattern for thread safety
                if service_name not in cls._instances:
                    instance = cls(service_name, config, **kwargs)
                    await instance._initialize()
                    cls._instances[service_name] = instance

        return cls._instances[service_name]

    async def _initialize(self) -> None:
        """Internal initialization method."""
        if self.status != ServiceStatus.UNINITIALIZED:
            return

        self.status = ServiceStatus.INITIALIZING
        self._initialization_start_time = datetime.now()

        try:
            # Initialize dependencies first
            await self._initialize_dependencies()

            # Call service-specific initialization
            await self.initialize()

            # Calculate initialization time
            if self._initialization_start_time:
                init_time = datetime.now() - self._initialization_start_time
                self.metrics.initialization_time_ms = init_time.total_seconds() * 1000

            self.status = ServiceStatus.ACTIVE
            self.logger.info(f"{self.service_name} service initialized successfully "
                           f"in {self.metrics.initialization_time_ms:.2f}ms")

        except Exception as e:
            self.status = ServiceStatus.ERROR
            self.metrics.errors.append(f"Initialization failed: {str(e)}")
            self.logger.error(f"Failed to initialize {self.service_name} service: {e}", exc_info=True)
            raise

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the service.

        This method should be implemented by concrete services to perform
        service-specific initialization tasks.
        """
        pass

    async def _initialize_dependencies(self) -> None:
        """
        Initialize service dependencies.

        This method can be overridden by concrete services to initialize
        their dependencies before the main initialization.
        """
        pass

    async def ensure_initialized(self) -> None:
        """Ensure the service is properly initialized."""
        if self.status == ServiceStatus.UNINITIALIZED:
            await self._initialize()
        elif self.status == ServiceStatus.ERROR:
            raise RuntimeError(f"{self.service_name} service is in error state")

    async def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        if self.status in [ServiceStatus.SHUTTING_DOWN, ServiceStatus.SHUTDOWN]:
            return

        self.status = ServiceStatus.SHUTTING_DOWN
        self.logger.info(f"Shutting down {self.service_name} service")

        try:
            await self.cleanup()
            self.metrics.end_time = datetime.now()
            self.status = ServiceStatus.SHUTDOWN
            self.logger.info(f"{self.service_name} service shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during {self.service_name} service shutdown: {e}", exc_info=True)
            raise

    async def cleanup(self) -> None:
        """
        Cleanup service resources.

        This method can be overridden by concrete services to perform
        cleanup tasks during shutdown.
        """
        # Close any HTTP clients or other resources
        for dependency_name, dependency in self._dependencies.items():
            if hasattr(dependency, 'cleanup'):
                try:
                    await dependency.cleanup()
                    self.logger.debug(f"Cleaned up dependency: {dependency_name}")
                except Exception as e:
                    self.logger.warning(f"Error cleaning up dependency {dependency_name}: {e}")
            elif hasattr(dependency, 'close'):
                try:
                    if asyncio.iscoroutinefunction(dependency.close):
                        await dependency.close()
                    else:
                        dependency.close()
                    self.logger.debug(f"Closed dependency: {dependency_name}")
                except Exception as e:
                    self.logger.warning(f"Error closing dependency {dependency_name}: {e}")

    def add_dependency(self, name: str, dependency: Any) -> None:
        """Add a dependency to the service."""
        self._dependencies[name] = dependency
        self.logger.debug(f"Added dependency '{name}' to {self.service_name}")

    def get_dependency(self, name: str) -> Any:
        """Get a dependency by name."""
        if name not in self._dependencies:
            raise ValueError(f"Dependency '{name}' not found in {self.service_name}")
        return self._dependencies[name]

    def update_config(self, new_config: ServiceConfig) -> None:
        """Update service configuration."""
        old_config = self.config
        self.config = new_config
        self.metrics.configuration_changes += 1
        self.logger.info(f"Updated configuration for {self.service_name}")
        
        # Call service-specific config update
        self.on_config_updated(old_config, new_config)

    def on_config_updated(self, old_config: ServiceConfig, new_config: ServiceConfig) -> None:
        """
        Handle configuration updates.

        This method can be overridden by concrete services to handle
        configuration changes.
        """
        pass

    @asynccontextmanager
    async def track_request(self, request_name: str):
        """Context manager for tracking requests and performance."""
        start_time = datetime.now()
        self.metrics.total_requests += 1
        self.metrics.last_request_time = start_time

        try:
            self.logger.debug(f"Starting {request_name} in {self.service_name}")
            yield
            self.metrics.successful_requests += 1
            self.logger.debug(f"Completed {request_name} in {self.service_name}")
        except Exception as e:
            self.metrics.failed_requests += 1
            self.metrics.errors.append(f"{request_name}: {str(e)}")
            self.logger.error(f"Failed {request_name} in {self.service_name}: {e}", exc_info=True)
            raise
        finally:
            # Update average response time
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            if self.metrics.total_requests == 1:
                self.metrics.average_response_time_ms = response_time
            else:
                # Calculate running average
                total_time = self.metrics.average_response_time_ms * (self.metrics.total_requests - 1)
                self.metrics.average_response_time_ms = (total_time + response_time) / self.metrics.total_requests

    def get_metrics(self) -> ServiceMetrics:
        """Get current service metrics."""
        return self.metrics

    def get_status(self) -> ServiceStatus:
        """Get current service status."""
        return self.status

    def is_healthy(self) -> bool:
        """Check if the service is healthy."""
        return self.status == ServiceStatus.ACTIVE

    def get_health_info(self) -> Dict[str, Any]:
        """Get health information."""
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "healthy": self.is_healthy(),
            "uptime_seconds": self.metrics.uptime.total_seconds() if self.metrics.uptime else None,
            "total_requests": self.metrics.total_requests,
            "success_rate": self.metrics.success_rate,
            "average_response_time_ms": self.metrics.average_response_time_ms,
            "error_count": len(self.metrics.errors),
            "configuration": self.config.to_dict()
        }

    # LLM Integration Preparation
    def is_llm_enabled(self) -> bool:
        """Check if LLM integration is enabled for this service."""
        return self.config.llm_integration_enabled

    async def prepare_llm_integration(self) -> None:
        """
        Prepare the service for LLM integration.

        This method can be overridden by concrete services to perform
        LLM-specific preparation tasks.
        """
        if self.is_llm_enabled():
            self.logger.info(f"Preparing LLM integration for {self.service_name}")
            # Default implementation - can be overridden by concrete services
        else:
            self.logger.debug(f"LLM integration disabled for {self.service_name}")

    async def handle_llm_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle LLM requests.

        This method can be overridden by concrete services to handle
        LLM-specific requests.

        Args:
            request_data: LLM request data

        Returns:
            LLM response data
        """
        if not self.is_llm_enabled():
            raise RuntimeError(f"LLM integration not enabled for {self.service_name}")
        
        # Default implementation - should be overridden by concrete services
        return {"error": "LLM integration not implemented"}

    def __repr__(self) -> str:
        """String representation of the service."""
        return f"{self.__class__.__name__}(name='{self.service_name}', status={self.status.value})"
