import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Type, Union

from ..models.base.base_extractors import BaseExtractor
from ..models.base.base_types import BaseMatcher, BaseValidator
from .validator_adapter import ValidatorAdapter

if TYPE_CHECKING:
    from ..validation.engine import Validator as ValidationEngineValidator

logger = logging.getLogger(__name__)

# Type alias for validators (supports both old and new)
ValidatorType = Union[BaseValidator, ValidatorAdapter]


class DomainStatus(Enum):
    """Status of a domain registration"""

    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


@dataclass
class DomainMetadata:
    """Metadata for a domain registration"""

    name: str
    display_name: str
    description: str
    version: str
    status: DomainStatus
    supported_input_types: Set[str]
    supported_output_types: Set[str]
    documentation_url: Optional[str] = None
    maintainer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary"""
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
        }


@dataclass
class DomainServices:
    """Container for all services associated with a domain"""

    extractor: BaseExtractor
    matcher: BaseMatcher  # Now properly typed
    validator: ValidatorType  # Supports both BaseValidator and adapted Validator
    metadata: DomainMetadata
    orchestrator: Optional[Any] = None  # BaseOrchestrator when available


class DomainRegistry:
    """Unified registry for domain-specific components with management"""

    _domains: Dict[str, DomainServices] = {}
    _type_mappings: Dict[str, str] = {}

    @classmethod
    def register_domain(
        cls,
        domain_name: str,
        extractor: BaseExtractor,
        matcher: BaseMatcher,  # Now requires BaseMatcher
        validator: Union[
            BaseValidator, Any
        ],  # Accepts BaseValidator or ValidationEngineValidator
        metadata: DomainMetadata,
        orchestrator: Optional[Any] = None,
    ) -> None:
        """Register a complete domain with all its services"""
        if domain_name in cls._domains:
            logger.warning(f"Overwriting existing domain: {domain_name}")

        # Validate services
        cls._validate_services(extractor, matcher, validator)

        # Wrap ValidationEngineValidator if needed (lazy import to avoid circular dependency)
        from ..validation.engine import Validator as ValidationEngineValidator

        if isinstance(validator, ValidationEngineValidator):
            validator = ValidatorAdapter(validator)
            logger.debug(f"Wrapped ValidationEngineValidator for domain {domain_name}")

        services = DomainServices(
            extractor=extractor,
            matcher=matcher,
            validator=validator,
            metadata=metadata,
            orchestrator=orchestrator,
        )

        cls._domains[domain_name] = services

        # Register type mappings
        for input_type in metadata.supported_input_types:
            cls._type_mappings[input_type] = domain_name

        logger.info(
            f"Registered domain: {domain_name} with types: {metadata.supported_input_types}"
        )

    @classmethod
    def _validate_services(
        cls,
        extractor: BaseExtractor,
        matcher: BaseMatcher,
        validator: Union[BaseValidator, Any],
    ) -> None:
        """Validate that services implement required interfaces"""
        if not isinstance(extractor, BaseExtractor):
            raise TypeError(
                f"Extractor must inherit from BaseExtractor, got {type(extractor)}"
            )

        if not isinstance(matcher, BaseMatcher):
            raise TypeError(
                f"Matcher must inherit from BaseMatcher, got {type(matcher)}"
            )

        # Validator can be BaseValidator or ValidationEngineValidator (will be wrapped)
        # Use lazy import to avoid circular dependency
        from ..validation.engine import Validator as ValidationEngineValidator

        if isinstance(validator, BaseValidator):
            # Already correct type
            pass
        elif isinstance(validator, ValidationEngineValidator):
            # Will be wrapped by register_domain
            pass
        else:
            raise TypeError(
                f"Validator must be BaseValidator or ValidationEngineValidator, "
                f"got {type(validator)}"
            )

    @classmethod
    def get_domain_services(cls, domain_name: str) -> DomainServices:
        """Get all services for a domain"""
        if domain_name not in cls._domains:
            raise ValueError(
                f"Domain '{domain_name}' not found. Available domains: {list(cls._domains.keys())}"
            )
        return cls._domains[domain_name]

    @classmethod
    def get_extractor(cls, domain: str) -> BaseExtractor:
        """Get registered extractor for domain"""
        return cls.get_domain_services(domain).extractor

    @classmethod
    def get_matcher(cls, domain: str) -> BaseMatcher:
        """Get registered matcher for domain"""
        return cls.get_domain_services(domain).matcher

    @classmethod
    def get_validator(cls, domain: str) -> ValidatorType:
        """Get registered validator for domain"""
        return cls.get_domain_services(domain).validator

    @classmethod
    def get_orchestrator(cls, domain_name: str) -> Optional[Any]:
        """Get orchestrator for domain if available"""
        return cls.get_domain_services(domain_name).orchestrator

    @classmethod
    def list_domains(cls, include_disabled: bool = False) -> List[str]:
        """List all available domain names"""
        if include_disabled:
            return list(cls._domains.keys())

        return [
            name
            for name, services in cls._domains.items()
            if services.metadata.status != DomainStatus.DISABLED
        ]

    @classmethod
    def get_domain_metadata(cls, domain_name: str) -> DomainMetadata:
        """Get metadata for a specific domain"""
        return cls.get_domain_services(domain_name).metadata

    @classmethod
    def get_all_metadata(
        cls, include_disabled: bool = False
    ) -> Dict[str, DomainMetadata]:
        """Get metadata for all domains"""
        result = {}
        for name, services in cls._domains.items():
            if include_disabled or services.metadata.status != DomainStatus.DISABLED:
                result[name] = services.metadata
        return result

    @classmethod
    def infer_domain_from_type(cls, input_type: str) -> Optional[str]:
        """Infer domain from input type"""
        return cls._type_mappings.get(input_type)

    @classmethod
    def validate_domain_compatibility(
        cls, requirements_domain: str, capabilities_domain: str
    ) -> bool:
        """Validate that two domains are compatible for matching"""
        # For now, require exact match
        # Future versions could support cross-domain matching
        return requirements_domain == capabilities_domain

    @classmethod
    def get_supported_types(cls, domain_name: str) -> Dict[str, Set[str]]:
        """Get supported input and output types for a domain"""
        metadata = cls.get_domain_metadata(domain_name)
        return {
            "input_types": metadata.supported_input_types,
            "output_types": metadata.supported_output_types,
        }

    @classmethod
    def validate_type_support(cls, domain_name: str, input_type: str) -> bool:
        """Validate that a domain supports a specific input type"""
        metadata = cls.get_domain_metadata(domain_name)
        return input_type in metadata.supported_input_types

    @classmethod
    def get_registered_domains(cls) -> List[str]:
        """Get list of all registered domains (backward compatibility)"""
        return cls.list_domains()

    @classmethod
    def health_check(cls) -> Dict[str, Any]:
        """Perform health check on all registered domains"""
        health_status = {
            "total_domains": len(cls._domains),
            "active_domains": len(cls.list_domains()),
            "domains": {},
        }

        for name, services in cls._domains.items():
            try:
                # Basic health check - ensure services are accessible
                domain_health = {
                    "status": services.metadata.status.value,
                    "extractor": type(services.extractor).__name__,
                    "matcher": type(services.matcher).__name__,
                    "validator": type(services.validator).__name__,
                    "orchestrator": (
                        type(services.orchestrator).__name__
                        if services.orchestrator
                        else None
                    ),
                    "supported_types": list(services.metadata.supported_input_types),
                }
                health_status["domains"][name] = domain_health
            except Exception as e:
                health_status["domains"][name] = {"status": "error", "error": str(e)}
                logger.error(f"Domain '{name}' health check failed: {str(e)}")

        return health_status
