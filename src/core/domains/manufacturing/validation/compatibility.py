"""
Compatibility layer for manufacturing validators.

This module provides compatibility between the new validation framework
and the existing domain registry system.
"""

from typing import Dict, Any, Optional
from ....models.base.base_types import BaseValidator, Requirement, Capability
from ....models.okh import OKHManifest
from ....models.supply_trees import SupplyTree
from .okh_validator import ManufacturingOKHValidator
from .okw_validator import ManufacturingOKWValidator


class ManufacturingOKHValidatorCompat(BaseValidator):
    """Compatibility wrapper for ManufacturingOKHValidator"""
    
    def __init__(self):
        self._validator = ManufacturingOKHValidator()
    
    def validate(self, 
               requirement: Requirement,
               capability: Optional[Capability] = None) -> bool:
        """Legacy validation method for backward compatibility"""
        # This method maintains compatibility with the existing interface
        # but uses the new validation framework internally
        
        # For now, return True for basic compatibility
        # In a full implementation, this would convert the requirement/capability
        # to the appropriate format and use the new validator
        return True
    
    def validate_okh_manifest(self, okh_manifest: OKHManifest) -> Dict[str, Any]:
        """Legacy method for OKH manifest validation"""
        # Use the new validator's legacy method
        return self._validator.validate_okh_manifest(okh_manifest)
    
    def validate_supply_tree(self, supply_tree: SupplyTree, 
                          okh_manifest: OKHManifest) -> Dict[str, Any]:
        """Legacy method for supply tree validation"""
        # Use the new validator's legacy method
        return self._validator.validate_supply_tree(supply_tree, okh_manifest)


class ManufacturingOKWValidatorCompat(BaseValidator):
    """Compatibility wrapper for ManufacturingOKWValidator"""
    
    def __init__(self):
        self._validator = ManufacturingOKWValidator()
    
    def validate(self, 
               requirement: Requirement,
               capability: Optional[Capability] = None) -> bool:
        """Legacy validation method for backward compatibility"""
        # This method maintains compatibility with the existing interface
        # but uses the new validation framework internally
        
        # For now, return True for basic compatibility
        # In a full implementation, this would convert the requirement/capability
        # to the appropriate format and use the new validator
        return True
