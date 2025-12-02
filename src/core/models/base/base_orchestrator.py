from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import importlib
import logging
from typing import Any, Dict, List, Optional, TypeVar, Generic, Protocol, Type as PyType
import yaml

# Generic type variables for requirements and capabilities
R = TypeVar("R")
C = TypeVar("C")


class MatchStatus(Enum):
    """Comprehensive status for matching process"""

    PENDING = auto()
    IN_PROGRESS = auto()
    PARTIALLY_MATCHED = auto()
    FULLY_MATCHED = auto()
    NO_MATCH = auto()
    ERROR = auto()


@dataclass
class MatchingModuleConfig:
    """Configuration for a matching module"""

    name: str
    type: str  # e.g., 'exact', 'heuristic', 'nlp', 'ml'
    domain: str
    priority: int = 100
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


class MatchingModule(Protocol, Generic[R, C]):
    """
    Protocol defining the interface for matching modules

    Ensures all matching modules have a consistent interface
    """

    def match(self, requirements: List[R], capabilities: List[C]) -> Any:
        """
        Perform matching for a specific module

        Args:
            requirements: List of requirements to match
            capabilities: Available capabilities to match against

        Returns:
            Matching result specific to the module
        """
        ...


class BaseOrchestrator(ABC, Generic[R, C]):
    """
    Abstract base class for matching orchestration

    Defines the core lifecycle and state management for
    a domain-specific matching process
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        modules: Optional[List[MatchingModuleConfig]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize orchestrator with configuration

        Args:
            config_path: Path to YAML configuration file
            modules: Alternatively, directly provide module configurations
            logger: Optional custom logger (defaults to a new logger if not provided)
        """
        # Setup logging
        self.logger = logger or logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

        # System state tracking
        self.state: Dict[str, Any] = {
            "status": MatchStatus.PENDING,
            "start_time": None,
            "end_time": None,
            "total_iterations": 0,
            "matching_logs": [],
        }

        # Load module configurations
        self.modules: List[MatchingModuleConfig] = []
        if config_path:
            self.modules.extend(self._load_config_from_file(config_path))
        if modules:
            self.modules.extend(modules)

        # Validated and instantiated matching modules
        self._initialized_modules: List[MatchingModule[R, C]] = []

    def _load_config_from_file(self, config_path: str) -> List[MatchingModuleConfig]:
        """
        Load matching module configurations from YAML file

        Args:
            config_path: Path to configuration file

        Returns:
            List of matching module configurations
        """
        try:
            with open(config_path, "r") as config_file:
                config_data = yaml.safe_load(config_file)

            modules = []
            for module_config in config_data.get("matching_modules", []):
                # Validate domain matches
                if module_config.get("domain") == getattr(self, "domain", None):
                    modules.append(
                        MatchingModuleConfig(
                            name=module_config.get("name", ""),
                            type=module_config.get("type", ""),
                            domain=module_config.get("domain", ""),
                            priority=module_config.get("priority", 100),
                            enabled=module_config.get("enabled", True),
                            config=module_config.get("config", {}),
                        )
                    )

            return modules
        except (IOError, yaml.YAMLError) as e:
            self._log_error(f"Error loading configuration: {e}")
            return []

    def _import_module(
        self, module_config: MatchingModuleConfig
    ) -> Optional[MatchingModule[R, C]]:
        """
        Dynamically import and instantiate a matching module

        Args:
            module_config: Configuration for the module to import

        Returns:
            Instantiated module or None if import fails
        """
        try:
            # Construct module path based on domain and type
            module_path = f"{self.domain}_matching.{module_config.type}_modules"
            class_name = (
                f"{self.domain.capitalize()}{module_config.type.capitalize()}Module"
            )

            # Dynamically import the module
            module = importlib.import_module(module_path)
            module_class: PyType[MatchingModule[R, C]] = getattr(module, class_name)

            # Instantiate with configuration
            return module_class(**module_config.config)

        except (ImportError, AttributeError) as e:
            self._log_error(f"Error importing module {module_config.name}: {e}")
            return None

    def initialize(self) -> None:
        """
        Initialize all matching modules

        Validates, imports, and prepares modules for matching
        """
        # Sort modules by priority
        sorted_modules = sorted(
            [m for m in self.modules if m.enabled], key=lambda x: x.priority
        )

        # Import and validate modules
        self._initialized_modules = []
        for module_config in sorted_modules:
            module = self._import_module(module_config)
            if module:
                self._initialized_modules.append(module)

        # Update system state
        self.state["status"] = MatchStatus.IN_PROGRESS
        self.state["start_time"] = datetime.now()

    def reset(self) -> None:
        """
        Reset the orchestrator to its initial state

        Clears all state and reinitializes modules
        """
        self.state = {
            "status": MatchStatus.PENDING,
            "start_time": None,
            "end_time": None,
            "total_iterations": 0,
            "matching_logs": [],
        }
        self._initialized_modules = []

    @abstractmethod
    def match(self, requirements: List[R], capabilities: List[C]) -> Any:
        """
        Execute the full matching process

        To be implemented by domain-specific orchestrators

        Args:
            requirements: List of requirements to match
            capabilities: Available capabilities to match against

        Returns:
            Matching result specific to the domain
        """
        pass

    def _log_event(self, message: str) -> None:
        """
        Log a system event

        Args:
            message: Event description
        """
        event_log = {"timestamp": datetime.now(), "message": message}
        self.state["matching_logs"].append(event_log)
        self.logger.info(message)

    def _log_error(self, error_message: str) -> None:
        """
        Log an error event

        Args:
            error_message: Description of the error
        """
        self.state["status"] = MatchStatus.ERROR
        self._log_event(f"ERROR: {error_message}")
        self.logger.error(error_message)
