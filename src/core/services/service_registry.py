import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from src.core.services.storage_service import StorageService

from ..domains.cooking.extractors import CookingExtractor
from ..domains.cooking.matchers import CookingMatcher
from ..domains.cooking.validators import CookingValidator
from ..domains.manufacturing.okh_extractor import OKHExtractor
from ..domains.manufacturing.okh_matcher import OKHMatcher
from ..domains.manufacturing.okh_orchestrator import OKHOrchestrator
from ..domains.manufacturing.okh_validator import OKHValidator
from ..models.base.base_extractors import BaseExtractor
from ..models.base.base_types import BaseMatcher, BaseValidator


class DomainStatus(Enum):
    """Status of domain availability"""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    DISABLED = "disabled"


@dataclass
class DomainMetadata:
    """Metadata about a domain"""

    name: str
    display_name: str
    description: str
    version: str
    status: DomainStatus
    supported_input_types: Set[str]
    supported_output_types: Set[str]
    documentation_url: Optional[str] = None
    maintainer: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "status": self.status.value,
            "supported_input_types": list(self.supported_input_types),
            "supported_output_types": list(self.supported_output_types),
            "documentation_url": self.documentation_url,
            "maintainer": self.maintainer,
            "dependencies": self.dependencies,
        }


@dataclass
class DomainServices:
    """Container for all services associated with a domain"""

    extractor: BaseExtractor
    matcher: BaseMatcher
    validator: BaseValidator
    metadata: DomainMetadata
    orchestrator: Optional[Any] = None  # BaseOrchestrator when available
    storage: Optional[StorageService] = None


class DomainValidationError(Exception):
    """Raised when domain validation fails"""

    pass


class DomainNotFoundError(Exception):
    """Raised when requested domain is not found"""

    pass


class ServiceRegistry:
    """Enhanced registry for domain-specific services with validation and enumeration"""

    def __init__(self):
        self._domains: Dict[str, DomainServices] = {}
        self._type_mappings: Dict[str, str] = {}
        self._logger = logging.getLogger(__name__)

    async def register_domain(
        self,
        domain_name: str,
        extractor: BaseExtractor,
        matcher: BaseMatcher,
        validator: BaseValidator,
        metadata: DomainMetadata,
        orchestrator: Optional[Any] = None,
    ) -> None:
        """
        Register a complete domain with all its services

        Args:
            domain_name: Unique domain identifier
            extractor: Domain-specific extractor
            matcher: Domain-specific matcher
            validator: Domain-specific validator
            metadata: Domain metadata
            orchestrator: Optional domain-specific orchestrator
        """
        if domain_name in self._domains:
            self._logger.warning(f"Overwriting existing domain: {domain_name}")

        # Validate services
        self._validate_services(extractor, matcher, validator)

        # Initialize storage for domain
        storage = None
        try:
            storage = await StorageService.get_instance()
            await storage.register_domain_handler(domain_name)
        except Exception as e:
            self._logger.warning(
                f"Failed to initialize storage for domain {domain_name}: {e}"
            )

        services = DomainServices(
            extractor=extractor,
            matcher=matcher,
            validator=validator,
            metadata=metadata,
            orchestrator=orchestrator,
            storage=storage,
        )

        self._domains[domain_name] = services

        # Register type mappings
        for input_type in metadata.supported_input_types:
            self._type_mappings[input_type] = domain_name

        self._logger.info(
            f"Registered domain: {domain_name} with types: {metadata.supported_input_types}"
        )

    def _validate_services(
        self, extractor: BaseExtractor, matcher: BaseMatcher, validator: BaseValidator
    ) -> None:
        """Validate that services implement required interfaces"""
        if not isinstance(extractor, BaseExtractor):
            raise DomainValidationError("Extractor must implement BaseExtractor")
        if not isinstance(matcher, BaseMatcher):
            raise DomainValidationError("Matcher must implement BaseMatcher")
        if not isinstance(validator, BaseValidator):
            raise DomainValidationError("Validator must implement BaseValidator")

    def get_domain_services(self, domain_name: str) -> DomainServices:
        """Get all services for a domain"""
        if domain_name not in self._domains:
            raise DomainNotFoundError(
                f"Domain '{domain_name}' not found. Available domains: {self.list_domains()}"
            )

        services = self._domains[domain_name]

        # Check if domain is available
        if services.metadata.status == DomainStatus.DISABLED:
            raise DomainValidationError(f"Domain '{domain_name}' is disabled")

        return services

    def get_extractor(self, domain_name: str) -> BaseExtractor:
        """Get extractor for domain"""
        return self.get_domain_services(domain_name).extractor

    def get_matcher(self, domain_name: str) -> BaseMatcher:
        """Get matcher for domain"""
        return self.get_domain_services(domain_name).matcher

    def get_validator(self, domain_name: str) -> BaseValidator:
        """Get validator for domain"""
        return self.get_domain_services(domain_name).validator

    def get_orchestrator(self, domain_name: str) -> Optional[Any]:
        """Get orchestrator for domain if available"""
        return self.get_domain_services(domain_name).orchestrator

    def list_domains(self, include_disabled: bool = False) -> List[str]:
        """List all available domain names"""
        if include_disabled:
            return list(self._domains.keys())

        return [
            name
            for name, services in self._domains.items()
            if services.metadata.status != DomainStatus.DISABLED
        ]

    def get_domain_metadata(self, domain_name: str) -> DomainMetadata:
        """Get metadata for a specific domain"""
        return self.get_domain_services(domain_name).metadata

    def get_all_metadata(
        self, include_disabled: bool = False
    ) -> Dict[str, DomainMetadata]:
        """Get metadata for all domains"""
        result = {}
        for name, services in self._domains.items():
            if include_disabled or services.metadata.status != DomainStatus.DISABLED:
                result[name] = services.metadata
        return result

    def infer_domain_from_type(self, input_type: str) -> Optional[str]:
        """Infer domain from input type"""
        return self._type_mappings.get(input_type)

    def validate_domain_compatibility(
        self, requirements_domain: str, capabilities_domain: str
    ) -> bool:
        """Validate that two domains are compatible for matching"""
        # For now, require exact match
        # Future versions could support cross-domain matching
        return requirements_domain == capabilities_domain

    def get_supported_types(self, domain_name: str) -> Dict[str, Set[str]]:
        """Get supported input and output types for a domain"""
        metadata = self.get_domain_metadata(domain_name)
        return {
            "input_types": metadata.supported_input_types,
            "output_types": metadata.supported_output_types,
        }

    def validate_type_support(self, domain_name: str, input_type: str) -> bool:
        """Validate that a domain supports a specific input type"""
        metadata = self.get_domain_metadata(domain_name)
        return input_type in metadata.supported_input_types

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all registered domains"""
        health_status = {
            "total_domains": len(self._domains),
            "active_domains": len(
                [
                    d
                    for d in self._domains.values()
                    if d.metadata.status == DomainStatus.ACTIVE
                ]
            ),
            "domain_status": {},
            "issues": [],
        }

        for name, services in self._domains.items():
            try:
                # Basic service availability check
                status = {
                    "status": services.metadata.status.value,
                    "extractor": services.extractor is not None,
                    "matcher": services.matcher is not None,
                    "validator": services.validator is not None,
                    "orchestrator": services.orchestrator is not None,
                }

                # Check dependencies if any
                missing_deps = []
                for dep in services.metadata.dependencies:
                    if dep not in self._domains:
                        missing_deps.append(dep)

                if missing_deps:
                    status["missing_dependencies"] = missing_deps
                    health_status["issues"].append(
                        f"Domain '{name}' has missing dependencies: {missing_deps}"
                    )

                health_status["domain_status"][name] = status

            except Exception as e:
                health_status["domain_status"][name] = {"error": str(e)}
                health_status["issues"].append(
                    f"Domain '{name}' health check failed: {str(e)}"
                )

        return health_status


# Global service registry instance
service_registry = ServiceRegistry()


# Domain registration helper functions
def register_cooking_domain():
    """Register the cooking domain"""
    metadata = DomainMetadata(
        name="cooking",
        display_name="Cooking & Food Preparation",
        description="Domain for recipe and kitchen capability matching",
        version="1.0.0",
        status=DomainStatus.ACTIVE,
        supported_input_types={"recipe", "kitchen"},
        supported_output_types={"cooking_workflow", "meal_plan"},
        documentation_url="https://docs.ome.org/domains/cooking",
        maintainer="OME Cooking Team",
    )

    service_registry.register_domain(
        domain_name="cooking",
        extractor=CookingExtractor(),
        matcher=CookingMatcher(),
        validator=CookingValidator(),
        metadata=metadata,
    )


def register_manufacturing_domain():
    """Register the manufacturing domain"""
    metadata = DomainMetadata(
        name="manufacturing",
        display_name="Manufacturing & Hardware Production",
        description="Domain for OKH/OKW manufacturing capability matching",
        version="1.0.0",
        status=DomainStatus.ACTIVE,
        supported_input_types={"okh", "okw"},
        supported_output_types={"supply_tree", "manufacturing_plan"},
        documentation_url="https://docs.ome.org/domains/manufacturing",
        maintainer="OME Manufacturing Team",
    )

    service_registry.register_domain(
        domain_name="manufacturing",
        extractor=OKHExtractor(),
        matcher=OKHMatcher(),
        validator=OKHValidator(),
        metadata=metadata,
        orchestrator=OKHOrchestrator(),
    )


def initialize_default_domains():
    """Initialize all default domains"""
    register_cooking_domain()
    register_manufacturing_domain()
