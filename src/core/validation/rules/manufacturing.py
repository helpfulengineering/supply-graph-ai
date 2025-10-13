"""
Manufacturing domain validation rules.

This module provides validation rules for the manufacturing domain,
integrating with the existing domain configuration.
"""

from typing import Dict, Any, List
from .base import BaseValidationRules
# from ...config.domains import get_domain_config  # Not needed for now


class ManufacturingValidationRules(BaseValidationRules):
    """Validation rules for manufacturing domain - integrates with existing domain config"""
    
    def get_supported_quality_levels(self) -> List[str]:
        """Get supported quality levels for manufacturing domain"""
        return ["hobby", "professional", "medical"]
    
    def get_validation_rules(self, quality_level: str) -> Dict[str, Any]:
        """Get validation rules for a specific quality level"""
        if quality_level not in self.get_supported_quality_levels():
            raise ValueError(f"Unsupported quality level '{quality_level}' for manufacturing domain")
        
        base_rules = {
            'required_fields': self.get_required_fields(quality_level),
            'optional_fields': self.get_optional_fields(quality_level),
            'validation_strictness': self.get_validation_strictness(quality_level),
            'quality_levels': self.get_supported_quality_levels(),
            'domain': 'manufacturing'
        }
        
        # Add quality-specific rules
        if quality_level == "hobby":
            base_rules.update({
                'allow_incomplete_docs': True,
                'require_certifications': False,
                'require_quality_standards': False
            })
        elif quality_level == "professional":
            base_rules.update({
                'allow_incomplete_docs': False,
                'require_certifications': True,
                'require_quality_standards': True
            })
        elif quality_level == "medical":
            base_rules.update({
                'allow_incomplete_docs': False,
                'require_certifications': True,
                'require_quality_standards': True,
                'require_regulatory_compliance': True,
                'require_traceability': True
            })
        
        return base_rules
    
    def get_required_fields(self, quality_level: str) -> List[str]:
        """Get required fields for a specific quality level"""
        base_required = [
            'title', 'version', 'license', 'licensor', 
            'documentation_language', 'function'
        ]
        
        if quality_level == "hobby":
            return base_required
        elif quality_level == "professional":
            return base_required + [
                'manufacturing_specs', 'manufacturing_processes', 
                'materials', 'tool_list'
            ]
        elif quality_level == "medical":
            return base_required + [
                'manufacturing_specs', 'manufacturing_processes', 
                'materials', 'tool_list', 'quality_standards',
                'certifications', 'regulatory_compliance', 
                'traceability', 'testing_procedures'
            ]
        
        return base_required
    
    def get_optional_fields(self, quality_level: str) -> List[str]:
        """Get optional fields for a specific quality level"""
        base_optional = [
            'description', 'keywords', 'cpc_patent_class', 'tsdc',
            'derivative_of', 'variant_of', 'sub_parts', 'metadata'
        ]
        
        if quality_level == "hobby":
            return base_optional + ['manufacturing_processes']
        elif quality_level == "professional":
            return base_optional + [
                'quality_standards', 'certifications', 'regulatory_compliance'
            ]
        elif quality_level == "medical":
            return base_optional + [
                'traceability', 'testing_procedures', 'risk_assessment'
            ]
        
        return base_optional
    
    @staticmethod
    def get_okw_required_fields(quality_level: str) -> List[str]:
        """Get required fields for OKW validation based on quality level"""
        base_required = ['name', 'location', 'facility_status']
        
        if quality_level == "hobby":
            return base_required
        elif quality_level == "professional":
            return base_required + ['equipment', 'manufacturing_processes']
        elif quality_level == "medical":
            return base_required + ['equipment', 'manufacturing_processes', 'certifications']
        
        return base_required
    
    @staticmethod
    def get_okw_optional_fields(quality_level: str) -> List[str]:
        """Get optional fields for OKW validation based on quality level"""
        base_optional = [
            'description', 'owner', 'contact', 'affiliations', 'opening_hours',
            'date_founded', 'access_type', 'wheelchair_accessibility',
            'typical_batch_size', 'floor_size', 'storage_capacity',
            'typical_materials', 'certifications', 'metadata'
        ]
        
        if quality_level == "hobby":
            return base_optional
        elif quality_level == "professional":
            return base_optional + ['quality_standards']
        elif quality_level == "medical":
            return base_optional + ['quality_standards', 'regulatory_compliance']
        
        return base_optional
    
    @staticmethod
    def get_okh_validation_rules(quality_level: str = "professional") -> Dict[str, Any]:
        """Get OKH validation rules based on quality level"""
        base_rules = {
            'required_fields': ['title', 'version', 'license', 'licensor', 'documentation_language', 'function'],
            'optional_fields': ['description', 'keywords', 'manufacturing_processes', 'manufacturing_specs', 'quality_standards', 'certifications', 'regulatory_compliance'],
            'quality_levels': ["hobby", "professional", "medical"],
            'validation_contexts': ['manufacturing', 'hobby', 'professional']
        }

        quality_specific = {
            'hobby': {
                'required_fields': base_rules['required_fields'],
                'optional_fields': ['description', 'keywords', 'manufacturing_processes'],
                'validation_strictness': 'relaxed'
            },
            'professional': {
                'required_fields': base_rules['required_fields'] + ['manufacturing_specs'],
                'optional_fields': ['description', 'keywords', 'quality_standards', 'certifications'],
                'validation_strictness': 'standard'
            },
            'medical': {
                'required_fields': base_rules['required_fields'] + ['manufacturing_specs', 'quality_standards'],
                'optional_fields': ['description', 'keywords', 'certifications', 'regulatory_compliance'],
                'validation_strictness': 'strict'
            }
        }

        return quality_specific.get(quality_level, quality_specific['professional'])

    @staticmethod
    def get_okw_validation_rules(quality_level: str = "professional") -> Dict[str, Any]:
        """Get OKW validation rules based on quality level"""
        base_rules = {
            'required_fields': ['name', 'location', 'facility_status'],
            'optional_fields': ['equipment', 'manufacturing_processes', 'typical_materials', 'certifications', 'quality_standards', 'regulatory_compliance'],
            'equipment_validation': {
                'required_fields': ['name', 'type'],
                'optional_fields': ['specifications', 'location', 'materials_worked']
            },
            'process_validation': {
                'valid_processes': [
                    'https://en.wikipedia.org/wiki/CNC_mill',
                    'https://en.wikipedia.org/wiki/3D_printing',
                    'https://en.wikipedia.org/wiki/CNC_lathe',
                ]
            }
        }

        quality_specific = {
            'hobby': {
                'required_fields': base_rules['required_fields'],
                'optional_fields': ['equipment', 'manufacturing_processes', 'typical_materials'],
                'validation_strictness': 'relaxed'
            },
            'professional': {
                'required_fields': base_rules['required_fields'] + ['equipment', 'manufacturing_processes'],
                'optional_fields': ['typical_materials', 'certifications', 'quality_standards'],
                'validation_strictness': 'standard'
            },
            'medical': {
                'required_fields': base_rules['required_fields'] + ['equipment', 'manufacturing_processes', 'certifications'],
                'optional_fields': ['typical_materials', 'quality_standards', 'regulatory_compliance'],
                'validation_strictness': 'strict'
            }
        }

        return quality_specific.get(quality_level, quality_specific['professional'])
    
    @staticmethod
    def validate_quality_level(quality_level: str) -> bool:
        """Validate that a quality level is supported"""
        return quality_level in ["hobby", "professional", "medical"]
    
    @staticmethod
    def create_manufacturing_context(quality_level: str = "professional", strict_mode: bool = False):
        """Helper to create a manufacturing validation context"""
        from ...validation.context import ValidationContext
        return ValidationContext(
            name=f"manufacturing_{quality_level}",
            domain="manufacturing",
            quality_level=quality_level,
            strict_mode=strict_mode
        )
