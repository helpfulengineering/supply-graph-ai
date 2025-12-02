"""
Temporary OKH validator for backward compatibility.

This file provides a temporary validator that maintains the same interface
as the original validator while the new validation framework is being integrated.
"""

import os
from typing import Dict, Any, Optional

from src.core.models.base.base_types import BaseValidator, Requirement, Capability
from src.core.models.okh import OKHManifest
from src.core.models.supply_trees import SupplyTree


class OKHValidator(BaseValidator):
    """Temporary implementation of BaseValidator for OKH data - maintains original interface"""

    def validate(
        self, requirement: Requirement, capability: Optional[Capability] = None
    ) -> bool:
        """Validate a requirement or requirement-capability pair"""
        # If no capability provided, just validate the requirement
        if not capability:
            return self._validate_requirement(requirement)

        # Validate requirement-capability pair
        return self._validate_pair(requirement, capability)

    def _validate_requirement(self, requirement: Requirement) -> bool:
        """Validate a requirement"""
        # Ensure requirement has a name
        if not requirement.name:
            return False

        # Ensure parameters dict is present
        if not hasattr(requirement, "parameters") or requirement.parameters is None:
            return False

        return True

    def _validate_pair(self, requirement: Requirement, capability: Capability) -> bool:
        """Validate a requirement-capability pair"""
        # Check basic requirement validity
        if not self._validate_requirement(requirement):
            return False

        # Check if capability can satisfy requirement
        if requirement.name == capability.type:
            return True

        # Check if capability parameters include this process
        if hasattr(capability, "parameters") and "processes" in capability.parameters:
            if requirement.name in capability.parameters["processes"]:
                return True

        return False

    def validate_okh_manifest(self, okh_manifest: OKHManifest) -> Dict[str, Any]:
        """
        Validate the OKH manifest for completeness and correctness
        """
        results = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "completeness_score": 0.0,
        }

        # Check required fields
        try:
            okh_manifest.validate()
        except ValueError as e:
            results["valid"] = False
            results["issues"].append(str(e))

        # Check TSDC compliance
        for tsdc in okh_manifest.tsdc:
            if not self._validate_tsdc(okh_manifest, tsdc):
                results["issues"].append(f"TSDC compliance issue: {tsdc}")
                results["valid"] = False

        # Calculate completeness score
        results["completeness_score"] = self._calculate_completeness(okh_manifest)

        # Check common issues
        self._check_common_issues(okh_manifest, results)

        return results

    def validate_supply_tree(
        self, supply_tree: SupplyTree, okh_manifest: OKHManifest
    ) -> Dict[str, Any]:
        """
        Validate a generated supply tree against the OKH manifest
        """
        results = {"valid": True, "issues": [], "warnings": [], "confidence": 0.0}

        # Validate basic supply tree structure
        if not supply_tree.validate_snapshot():
            results["valid"] = False
            results["issues"].append(
                "Supply tree validation failed - invalid snapshot references"
            )

        # Check if all process requirements are satisfied
        process_reqs = okh_manifest.extract_requirements()
        for req in process_reqs:
            if not self._is_requirement_satisfied(req, supply_tree):
                if getattr(req, "is_required", True):
                    results["valid"] = False
                    results["issues"].append(
                        f"Required process not satisfied: {req.process_name}"
                    )
                else:
                    results["warnings"].append(
                        f"Optional process not satisfied: {req.process_name}"
                    )

        # Calculate confidence score
        results["confidence"] = self._calculate_confidence(supply_tree, okh_manifest)

        return results

    def _validate_tsdc(self, okh_manifest: OKHManifest, tsdc: str) -> bool:
        """Validate TSDC compliance"""
        # Implement TSDC-specific validation logic
        if tsdc == "PCB":
            # Check for PCB-specific fields
            pcb_fields = [
                "board-thickness-mm",
                "copper-thickness-mm",
                "component-sides",
            ]

            # Check parts for PCB fields
            for part in okh_manifest.parts:
                if "PCB" in part.tsdc:
                    if not any(
                        hasattr(part, field.replace("-", "_")) for field in pcb_fields
                    ):
                        return False

            # Check for PCB design files
            has_pcb_files = False
            for doc in okh_manifest.design_files:
                if hasattr(doc, "title") and "PCB" in doc.title:
                    has_pcb_files = True
                    break

            if not has_pcb_files:
                return False

        elif tsdc == "3DP":
            # Check for 3D printing specific fields
            tdp_fields = ["printing-process", "material"]

            # Check parts for 3DP fields
            has_3dp_part = False
            for part in okh_manifest.parts:
                if "3DP" in part.tsdc:
                    has_3dp_part = True
                    if not (
                        hasattr(part, "manufacturing_params")
                        and any(
                            field.replace("-", "_") in part.manufacturing_params
                            for field in tdp_fields
                        )
                    ):
                        return False

            if not has_3dp_part:
                return False

            # Check for 3D model files
            has_3d_files = False
            for doc in okh_manifest.design_files:
                if hasattr(doc, "path"):
                    ext = os.path.splitext(doc.path)[1].lower()
                    if ext in [".stl", ".obj", ".3mf", ".scad"]:
                        has_3d_files = True
                        break

            if not has_3d_files:
                return False

        # Default to true for other TSDCs or if no specific validation
        return True

    def _calculate_completeness(self, okh_manifest: OKHManifest) -> float:
        """Calculate completeness score (0.0-1.0)"""
        # Define weights for different sections
        weights = {
            "basic_info": 0.2,  # title, repo, version, etc.
            "documentation": 0.3,  # design files, instructions, etc.
            "manufacturing": 0.3,  # processes, materials, etc.
            "standards": 0.1,  # standards compliance
            "parts": 0.1,  # part specifications
        }

        scores = {
            "basic_info": 0.0,
            "documentation": 0.0,
            "manufacturing": 0.0,
            "standards": 0.0,
            "parts": 0.0,
        }

        # Calculate basic info score
        basic_fields = [
            "title",
            "repo",
            "version",
            "license",
            "licensor",
            "documentation_language",
            "function",
            "description",
        ]
        present_count = sum(
            1 for field in basic_fields if getattr(okh_manifest, field, None)
        )
        scores["basic_info"] = present_count / len(basic_fields)

        # Calculate documentation score
        doc_fields = [
            "manufacturing_files",
            "design_files",
            "making_instructions",
            "operating_instructions",
            "bom",
        ]
        doc_count = sum(1 for field in doc_fields if getattr(okh_manifest, field, None))
        scores["documentation"] = doc_count / len(doc_fields)

        # Calculate manufacturing score
        manuf_fields = [
            "manufacturing_processes",
            "materials",
            "manufacturing_specs",
            "tool_list",
        ]
        manuf_count = sum(
            1 for field in manuf_fields if getattr(okh_manifest, field, None)
        )
        scores["manufacturing"] = manuf_count / len(manuf_fields)

        # Calculate standards score
        if hasattr(okh_manifest, "standards_used") and okh_manifest.standards_used:
            scores["standards"] = 1.0
        elif (
            hasattr(okh_manifest, "cpc_patent_class") and okh_manifest.cpc_patent_class
        ):
            scores["standards"] = 0.5

        # Calculate parts score
        if hasattr(okh_manifest, "parts") and okh_manifest.parts:
            scores["parts"] = 1.0

        # Calculate weighted score
        total_score = sum(weights[section] * scores[section] for section in weights)

        return total_score

    def _check_common_issues(self, okh_manifest: OKHManifest, results: Dict):
        """Check for common issues"""
        # Check file references
        for field in [
            "manufacturing_files",
            "design_files",
            "making_instructions",
            "operating_instructions",
        ]:
            if hasattr(okh_manifest, field):
                file_list = getattr(okh_manifest, field, [])
                for doc in file_list:
                    if hasattr(doc, "validate") and not doc.validate():
                        results["warnings"].append(
                            f"Invalid file reference: {doc.path} in {field}"
                        )

        # Check for incomplete data
        if (
            not hasattr(okh_manifest, "manufacturing_processes")
            or not okh_manifest.manufacturing_processes
        ):
            results["warnings"].append("No manufacturing processes specified")

        if not hasattr(okh_manifest, "materials") or not okh_manifest.materials:
            results["warnings"].append("No materials specified")

        if not hasattr(okh_manifest, "tool_list") or not okh_manifest.tool_list:
            results["warnings"].append("No tools specified")

    def _is_requirement_satisfied(self, requirement, supply_tree: SupplyTree) -> bool:
        """Check if a process requirement is satisfied in the supply tree"""
        for workflow in supply_tree.workflows.values():
            for node_id in workflow.graph.nodes:
                node = workflow.graph.nodes[node_id]["data"]

                # Check if node handles this requirement
                if (
                    hasattr(requirement, "process_name")
                    and requirement.process_name in node.name
                ):
                    # Check if node has capability references
                    if hasattr(node, "okw_refs") and node.okw_refs:
                        return True

        return False

    def _calculate_confidence(
        self, supply_tree: SupplyTree, okh_manifest: OKHManifest
    ) -> float:
        """Calculate confidence score for supply tree"""
        # Count satisfied requirements
        process_reqs = okh_manifest.extract_requirements()
        satisfied_count = sum(
            1
            for req in process_reqs
            if self._is_requirement_satisfied(req, supply_tree)
        )

        # Calculate basic confidence from ratio of satisfied requirements
        if not process_reqs:
            return 0.0

        basic_confidence = satisfied_count / len(process_reqs)

        # Calculate workflow confidence
        workflow_confidence = 0.0
        if supply_tree.workflows:
            connected_count = 0
            total_count = 0

            for workflow in supply_tree.workflows.values():
                if workflow.graph.number_of_nodes() <= 1:
                    continue

                # Check connectivity
                total_count += workflow.graph.number_of_nodes()
                for node in workflow.graph.nodes:
                    if workflow.graph.degree(node) > 0:
                        connected_count += 1

            if total_count > 0:
                workflow_confidence = connected_count / total_count

        # Combine scores
        return 0.7 * basic_confidence + 0.3 * workflow_confidence
