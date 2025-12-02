"""
Import/Export Service for Capability Rules

This service handles importing and exporting rules from/to YAML and JSON files.
It provides comparison functionality for dry-run operations and uses dataclass
methods for all data conversions.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

import yaml

from .capability_rules import CapabilityRuleSet
from .rules_service import RulesService
from .validation import ValidationService

logger = logging.getLogger(__name__)


class ImportExportService:
    """Service for importing and exporting rules"""

    def __init__(
        self, validation_service: ValidationService, rules_service: RulesService
    ):
        """
        Initialize the import/export service.

        Args:
            validation_service: Service for validating rules
            rules_service: Service for managing rules
        """
        self.validation_service = validation_service
        self.rules_service = rules_service

    async def import_rules(
        self,
        file_content: str,
        file_format: str,
        domain: Optional[str] = None,
        partial_update: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Import rules from file content.

        Args:
            file_content: The file content as a string
            file_format: Format of the file ('yaml' or 'json')
            domain: Optional domain filter (if importing single domain)
            partial_update: If True, merge with existing rules; if False, replace
            dry_run: If True, validate and compare without applying changes

        Returns:
            Dict with import results:
            - imported_rules: number of new rules
            - updated_rules: number of updated rules
            - errors: list of errors
            - dry_run: whether this was a dry run
            - changes: (if dry_run) comparison results
        """
        # Parse file content
        try:
            if file_format.lower() == "yaml":
                data = yaml.safe_load(file_content)
            elif file_format.lower() == "json":
                data = json.loads(file_content)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to parse file: {str(e)}") from e

        # Handle multi-domain export format
        if "domains" in data:
            # Multi-domain export format
            if domain:
                # Filter to specific domain
                if domain not in data["domains"]:
                    raise ValueError(f"Domain '{domain}' not found in file")
                data = data["domains"][domain]
            else:
                # Import all domains
                results = {
                    "imported_rules": 0,
                    "updated_rules": 0,
                    "errors": [],
                    "dry_run": dry_run,
                }

                for dom, domain_data in data["domains"].items():
                    try:
                        domain_result = await self._import_single_domain(
                            domain_data, dom, partial_update, dry_run
                        )
                        results["imported_rules"] += domain_result.get(
                            "imported_rules", 0
                        )
                        results["updated_rules"] += domain_result.get(
                            "updated_rules", 0
                        )
                        if "errors" in domain_result:
                            results["errors"].extend(domain_result["errors"])
                    except Exception as e:
                        results["errors"].append(f"Domain '{dom}': {str(e)}")

                return results

        # Single domain format
        if domain and data.get("domain") != domain:
            raise ValueError(
                f"Rule set domain '{data.get('domain')}' does not match "
                f"requested domain '{domain}'"
            )

        return await self._import_single_domain(
            data, domain or data.get("domain"), partial_update, dry_run
        )

    async def _import_single_domain(
        self,
        data: Dict[str, Any],
        domain: Optional[str],
        partial_update: bool,
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Import a single domain's rule set"""
        # Validate using validation service
        validation_result = await self.validation_service.validate_rule_set(data)
        if not validation_result["valid"]:
            raise ValueError(
                f"Validation failed: {', '.join(validation_result['errors'])}"
            )

        # Convert to dataclass (this also validates)
        rule_set = CapabilityRuleSet.from_dict(data)

        if dry_run:
            # Return comparison results without applying
            comparison = await self._compare_rules(rule_set)
            return {
                "imported_rules": comparison["summary"]["total_added"],
                "updated_rules": comparison["summary"]["total_updated"],
                "errors": [],
                "dry_run": True,
                "changes": comparison,
            }

        # Apply changes
        result = await self.rules_service.import_rule_set(
            rule_set, partial_update=partial_update
        )
        result["dry_run"] = False
        return result

    async def export_rules(
        self,
        domain: Optional[str] = None,
        format: str = "yaml",
        include_metadata: bool = False,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Export rules to file content.

        Args:
            domain: Optional domain filter (exports all if not specified)
            format: Export format ('yaml' or 'json')
            include_metadata: Whether to include metadata (created_at, updated_at)

        Returns:
            Tuple of (file_content, metadata):
            - file_content: The serialized file content
            - metadata: Dictionary with export metadata
        """
        # Get rules from service
        rule_sets = await self.rules_service.get_rule_sets(domain=domain)

        if not rule_sets:
            raise ValueError(f"No rules found for domain '{domain or 'all'}'")

        if domain:
            # Export single domain
            rule_set = rule_sets[domain]
            data = rule_set.to_dict(include_metadata=include_metadata)
        else:
            # Export all domains
            data = {
                "domains": {
                    dom: rule_set.to_dict(include_metadata=include_metadata)
                    for dom, rule_set in rule_sets.items()
                }
            }

        # Serialize to requested format
        try:
            if format.lower() == "yaml":
                content = yaml.dump(
                    data, default_flow_style=False, sort_keys=False, allow_unicode=True
                )
            elif format.lower() == "json":
                content = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"Unsupported export format: {format}")
        except Exception as e:
            raise ValueError(f"Failed to serialize rules: {str(e)}") from e

        metadata = {
            "format": format,
            "domain": domain or "all",
            "rule_count": sum(len(rs.rules) for rs in rule_sets.values()),
            "domains": list(rule_sets.keys()),
        }

        return content, metadata

    async def _compare_rules(self, new_rule_set: CapabilityRuleSet) -> Dict[str, Any]:
        """
        Compare new rules with existing rules.

        Args:
            new_rule_set: The new rule set to compare

        Returns:
            Dictionary with comparison results:
            - changes: Dict with added, updated, deleted rule IDs
            - summary: Dict with counts
        """
        existing_rule_set = await self.rules_service.get_rule_set(new_rule_set.domain)

        if not existing_rule_set:
            return {
                "changes": {
                    "added": list(new_rule_set.rules.keys()),
                    "updated": [],
                    "deleted": [],
                },
                "summary": {
                    "total_added": len(new_rule_set.rules),
                    "total_updated": 0,
                    "total_deleted": 0,
                },
            }

        added = []
        updated = []
        deleted = []

        # Find added and updated rules
        for rule_id, new_rule in new_rule_set.rules.items():
            if rule_id not in existing_rule_set.rules:
                added.append(rule_id)
            else:
                # Compare rules by comparing their dict representations (excluding metadata)
                existing_rule = existing_rule_set.rules[rule_id]
                new_dict = new_rule.to_dict(include_metadata=False)
                existing_dict = existing_rule.to_dict(include_metadata=False)

                if new_dict != existing_dict:
                    updated.append(rule_id)

        # Find deleted rules
        for rule_id in existing_rule_set.rules:
            if rule_id not in new_rule_set.rules:
                deleted.append(rule_id)

        return {
            "changes": {"added": added, "updated": updated, "deleted": deleted},
            "summary": {
                "total_added": len(added),
                "total_updated": len(updated),
                "total_deleted": len(deleted),
            },
        }

    async def compare_rules(
        self, file_content: str, file_format: str, domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare rules from file with current rules (dry-run).

        Args:
            file_content: The file content as a string
            file_format: Format of the file ('yaml' or 'json')
            domain: Optional domain filter

        Returns:
            Dictionary with comparison results
        """
        # Parse and validate file
        try:
            if file_format.lower() == "yaml":
                data = yaml.safe_load(file_content)
            elif file_format.lower() == "json":
                data = json.loads(file_content)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to parse file: {str(e)}") from e

        # Handle multi-domain format
        if "domains" in data:
            if domain:
                if domain not in data["domains"]:
                    raise ValueError(f"Domain '{domain}' not found in file")
                data = data["domains"][domain]
            else:
                # Compare all domains
                all_comparisons = {}
                for dom, domain_data in data["domains"].items():
                    rule_set = CapabilityRuleSet.from_dict(domain_data)
                    all_comparisons[dom] = await self._compare_rules(rule_set)
                return {"domains": all_comparisons}

        # Single domain format
        rule_set = CapabilityRuleSet.from_dict(data)
        return await self._compare_rules(rule_set)
