"""
Rules Service

This service provides a high-level interface for managing capability rules.
It wraps CapabilityRuleManager and provides CRUD operations, import/export,
and rollback functionality.
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from .capability_rules import (
    CapabilityRule,
    CapabilityRuleSet,
    RuleType,
    CapabilityRuleManager
)
from .validation import ValidationService

logger = logging.getLogger(__name__)


class RulesService:
    """Service for managing capability rules with CRUD operations"""
    
    def __init__(
        self,
        rule_manager: CapabilityRuleManager,
        validation_service: Optional[ValidationService] = None
    ):
        """
        Initialize the rules service.
        
        Args:
            rule_manager: The rule manager instance
            validation_service: Optional validation service (creates one if not provided)
        """
        self.rule_manager = rule_manager
        self.validation_service = validation_service or ValidationService()
        self._backup: Optional[Dict[str, Any]] = None
    
    async def initialize(self) -> None:
        """Initialize the service by ensuring rule manager is initialized"""
        if not self.rule_manager._initialized:
            await self.rule_manager.initialize()
    
    # CRUD Operations
    
    async def create_rule(self, rule_data: Dict[str, Any]) -> CapabilityRule:
        """
        Create a new rule.
        
        Args:
            rule_data: Dictionary containing rule data
            
        Returns:
            The created CapabilityRule
            
        Raises:
            ValueError: If validation fails or rule already exists
        """
        # Validate rule data
        validation_result = await self.validation_service.validate_rule(rule_data)
        if not validation_result["valid"]:
            raise ValueError(f"Validation failed: {validation_result['errors']}")
        
        # Create rule from dict (validates via __post_init__)
        rule = CapabilityRule.from_dict(rule_data)
        
        # Check if rule already exists
        existing_rule = self.rule_manager.get_rule(rule.domain, rule.id)
        if existing_rule:
            raise ValueError(f"Rule '{rule.id}' already exists in domain '{rule.domain}'")
        
        # Get or create rule set for domain
        rule_set = self.rule_manager.get_rule_set(rule.domain)
        if not rule_set:
            # Create rule set with the new rule (can't create empty rule set)
            rule_set = CapabilityRuleSet(
                domain=rule.domain,
                version="1.0.0",
                rules={rule.id: rule}
            )
            self.rule_manager.add_rule_set(rule_set)
        else:
            # Add rule to existing rule set
            rule_set.add_rule(rule)
        
        logger.info(f"Created rule '{rule.id}' in domain '{rule.domain}'")
        return rule
    
    async def get_rule(self, domain: str, rule_id: str) -> Optional[CapabilityRule]:
        """
        Get a rule by domain and ID.
        
        Args:
            domain: The domain name
            rule_id: The rule ID
            
        Returns:
            The CapabilityRule if found, None otherwise
        """
        return self.rule_manager.get_rule(domain, rule_id)
    
    async def update_rule(
        self,
        domain: str,
        rule_id: str,
        rule_data: Dict[str, Any]
    ) -> CapabilityRule:
        """
        Update an existing rule.
        
        Args:
            domain: The domain name
            rule_id: The rule ID
            rule_data: Dictionary containing updated rule data
            
        Returns:
            The updated CapabilityRule
            
        Raises:
            ValueError: If rule not found or validation fails
        """
        # Check if rule exists
        existing_rule = self.rule_manager.get_rule(domain, rule_id)
        if not existing_rule:
            raise ValueError(f"Rule '{rule_id}' not found in domain '{domain}'")
        
        # Ensure rule_id and domain match
        rule_data["id"] = rule_id
        rule_data["domain"] = domain
        
        # Validate updated rule data
        validation_result = await self.validation_service.validate_rule(rule_data)
        if not validation_result["valid"]:
            raise ValueError(f"Validation failed: {validation_result['errors']}")
        
        # Create updated rule from dict
        updated_rule = CapabilityRule.from_dict(rule_data)
        
        # Update rule in rule set
        rule_set = self.rule_manager.get_rule_set(domain)
        if not rule_set:
            raise ValueError(f"Rule set for domain '{domain}' not found")
        
        rule_set.add_rule(updated_rule)  # add_rule replaces if exists
        
        logger.info(f"Updated rule '{rule_id}' in domain '{domain}'")
        return updated_rule
    
    async def delete_rule(self, domain: str, rule_id: str) -> bool:
        """
        Delete a rule.
        
        Args:
            domain: The domain name
            rule_id: The rule ID
            
        Returns:
            True if rule was deleted, False if not found
        """
        rule_set = self.rule_manager.get_rule_set(domain)
        if not rule_set:
            return False
        
        result = rule_set.remove_rule(rule_id)
        if result:
            logger.info(f"Deleted rule '{rule_id}' from domain '{domain}'")
            
            # If rule set is now empty, remove it
            if not rule_set.rules:
                self.rule_manager.remove_rule_set(domain)
        
        return result
    
    async def list_rules(
        self,
        domain: Optional[str] = None,
        tag: Optional[str] = None,
        include_metadata: bool = False
    ) -> Dict[str, Any]:
        """
        List all rules, optionally filtered by domain or tag.
        
        Args:
            domain: Optional domain filter
            tag: Optional tag filter
            include_metadata: Whether to include metadata in response
            
        Returns:
            Dictionary containing rules list and metadata
        """
        all_rules = []
        domains = []
        
        # Get domains to search
        if domain:
            if domain in self.rule_manager.rule_sets:
                domains = [domain]
            else:
                domains = []
        else:
            domains = self.rule_manager.get_available_domains()
        
        # Collect rules
        for dom in domains:
            rule_set = self.rule_manager.get_rule_set(dom)
            if not rule_set:
                continue
            
            if tag:
                rules = rule_set.get_rules_by_tag(tag)
            else:
                rules = rule_set.get_all_rules()
            
            for rule in rules:
                rule_dict = rule.to_dict(include_metadata=include_metadata)
                rule_dict["domain"] = dom  # Ensure domain is included
                all_rules.append(rule_dict)
        
        return {
            "rules": all_rules,
            "total": len(all_rules),
            "domains": list(set(domains))
        }
    
    # Rule Set Operations
    
    async def get_rule_set(self, domain: str) -> Optional[CapabilityRuleSet]:
        """
        Get a rule set by domain.
        
        Args:
            domain: The domain name
            
        Returns:
            The CapabilityRuleSet if found, None otherwise
        """
        return self.rule_manager.get_rule_set(domain)
    
    async def get_rule_sets(
        self,
        domain: Optional[str] = None
    ) -> Dict[str, CapabilityRuleSet]:
        """
        Get rule sets, optionally filtered by domain.
        
        Args:
            domain: Optional domain filter
            
        Returns:
            Dictionary mapping domain names to CapabilityRuleSet objects
        """
        if domain:
            rule_set = self.rule_manager.get_rule_set(domain)
            if rule_set:
                return {domain: rule_set}
            return {}
        else:
            return dict(self.rule_manager.rule_sets)
    
    async def import_rule_set(
        self,
        rule_set: CapabilityRuleSet,
        partial_update: bool = True
    ) -> Dict[str, Any]:
        """
        Import a rule set with rollback support.
        
        Args:
            rule_set: The rule set to import
            partial_update: If True, merge with existing rules; if False, replace
            
        Returns:
            Dictionary with import results:
            - imported_rules: number of new rules
            - updated_rules: number of updated rules
            - errors: list of errors
        """
        # Create backup
        backup = await self._create_backup()
        
        try:
            # Get existing rule set
            existing_rule_set = self.rule_manager.get_rule_set(rule_set.domain)
            
            imported_count = 0
            updated_count = 0
            
            if not existing_rule_set:
                # New domain - add all rules
                self.rule_manager.add_rule_set(rule_set)
                imported_count = len(rule_set.rules)
            elif partial_update:
                # Merge with existing rules
                for rule_id, new_rule in rule_set.rules.items():
                    if rule_id in existing_rule_set.rules:
                        existing_rule_set.add_rule(new_rule)  # Replaces existing
                        updated_count += 1
                    else:
                        existing_rule_set.add_rule(new_rule)
                        imported_count += 1
            else:
                # Replace entire rule set
                self.rule_manager.add_rule_set(rule_set)
                updated_count = len(rule_set.rules)
            
            # Validate all rules after import
            validation_result = await self._validate_all_rules()
            if not validation_result["valid"]:
                # Rollback on validation failure
                await self._restore_backup(backup)
                raise ValueError(
                    f"Validation failed after import: {validation_result['errors']}"
                )
            
            logger.info(
                f"Imported rule set for domain '{rule_set.domain}': "
                f"{imported_count} new, {updated_count} updated"
            )
            
            return {
                "imported_rules": imported_count,
                "updated_rules": updated_count,
                "errors": []
            }
        except Exception as e:
            # Rollback on any error
            await self._restore_backup(backup)
            logger.error(f"Import failed, rolled back: {e}")
            raise ValueError(f"Import failed: {str(e)}") from e
    
    async def reset_rules(self) -> None:
        """
        Reset all rules (clear all rule sets).
        
        This operation cannot be rolled back.
        """
        self.rule_manager.rule_sets.clear()
        logger.warning("All rules have been reset")
    
    # Backup and Rollback
    
    async def _create_backup(self) -> Dict[str, Any]:
        """Create backup of current rule state"""
        backup = {}
        for domain, rule_set in self.rule_manager.rule_sets.items():
            backup[domain] = rule_set.to_dict(include_metadata=True)
        return backup
    
    async def _restore_backup(self, backup: Dict[str, Any]) -> None:
        """Restore rules from backup"""
        # Clear current rules
        self.rule_manager.rule_sets.clear()
        
        # Restore from backup
        for domain, rule_set_data in backup.items():
            try:
                rule_set = CapabilityRuleSet.from_dict(rule_set_data)
                self.rule_manager.add_rule_set(rule_set)
            except Exception as e:
                logger.error(f"Failed to restore rule set for domain '{domain}': {e}")
                raise
    
    async def _validate_all_rules(self) -> Dict[str, Any]:
        """Validate all rule sets"""
        errors = []
        warnings = []
        
        for domain, rule_set in self.rule_manager.rule_sets.items():
            rule_set_dict = rule_set.to_dict(include_metadata=False)
            validation_result = await self.validation_service.validate_rule_set(rule_set_dict)
            
            if not validation_result["valid"]:
                errors.extend([
                    f"Domain '{domain}': {error}"
                    for error in validation_result["errors"]
                ])
            
            warnings.extend([
                f"Domain '{domain}': {warning}"
                for warning in validation_result["warnings"]
            ])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

