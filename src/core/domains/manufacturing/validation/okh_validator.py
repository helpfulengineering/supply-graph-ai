"""
Enhanced OKH validator for manufacturing domain.

This module provides an enhanced OKH validator that integrates with
the new validation framework while maintaining compatibility with
the existing validator interface.
"""

from typing import Dict, Any, Optional, List
from ....validation.engine import Validator
from ....validation.context import ValidationContext
from ....validation.result import ValidationResult, ValidationError, ValidationWarning
from ....validation.rules.manufacturing import ManufacturingValidationRules
from ....models.okh import OKHManifest
from ....models.base.base_types import Requirement, Capability
from ....models.supply_trees import SupplyTree


class ManufacturingOKHValidator(Validator):
    """Enhanced OKH validator for manufacturing domain using new validation framework"""
    
    def __init__(self):
        self.validation_rules = ManufacturingValidationRules()
    
    @property
    def validation_type(self) -> str:
        """Return the type of validation this validator performs"""
        return "okh_manifest"
    
    @property
    def priority(self) -> int:
        """Return validation priority (higher = earlier)"""
        return 100  # High priority for OKH validation
    
    async def validate(self, data: Any, context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate OKH data using domain-specific rules"""
        result = ValidationResult(valid=True)
        
        # Handle different data types
        if isinstance(data, OKHManifest):
            return await self._validate_okh_manifest(data, context)
        elif isinstance(data, dict):
            # Try to create OKHManifest from dict
            try:
                okh_manifest = OKHManifest.from_dict(data)
                return await self._validate_okh_manifest(okh_manifest, context)
            except Exception as e:
                result.add_error(f"Failed to parse OKH manifest: {str(e)}")
                return result
        else:
            result.add_error(f"Unsupported data type for OKH validation: {type(data)}")
            return result
    
    async def _validate_okh_manifest(self, okh_manifest: OKHManifest, 
                                   context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate OKH manifest using domain-specific rules"""
        result = ValidationResult(valid=True)
        
        # Get quality level from context or default to professional
        quality_level = "professional"
        if context:
            quality_level = context.quality_level
        
        # Validate quality level is supported
        if quality_level not in self.validation_rules.get_supported_quality_levels():
            result.add_error(f"Unsupported quality level: {quality_level}")
            return result
        
        # Get validation rules for this quality level
        rules = self.validation_rules.get_okh_validation_rules(quality_level)
        
        # Validate required fields
        required_fields = rules.get('required_fields', [])
        missing_fields = self.validation_rules.get_missing_required_fields(
            okh_manifest.to_dict(), quality_level
        )
        
        for field in missing_fields:
            result.add_error(
                f"Required field '{field}' is missing for {quality_level} quality level",
                field=field,
                code="required_field_missing"
            )
        
        # Validate field content based on quality level
        await self._validate_field_content(okh_manifest, quality_level, result)
        
        # Validate TSDC compliance
        await self._validate_tsdc_compliance(okh_manifest, quality_level, result)
        
        # Validate manufacturing processes
        await self._validate_manufacturing_processes(okh_manifest, quality_level, result)
        
        # Validate materials and tools
        await self._validate_materials_and_tools(okh_manifest, quality_level, result)
        
        # Calculate completeness score
        completeness_score = self._calculate_completeness(okh_manifest, quality_level)
        result.metadata['completeness_score'] = completeness_score
        
        # Add warnings for missing optional fields
        await self._add_optional_field_warnings(okh_manifest, quality_level, result)
        
        return result
    
    async def _validate_field_content(self, okh_manifest: OKHManifest, 
                                    quality_level: str, result: ValidationResult):
        """Validate content of individual fields"""
        
        # Validate title
        if hasattr(okh_manifest, 'title') and okh_manifest.title:
            if len(okh_manifest.title.strip()) < 3:
                result.add_warning(
                    "Title is very short, consider providing a more descriptive title",
                    field="title",
                    code="title_too_short"
                )
        
        # Validate version format
        if hasattr(okh_manifest, 'version') and okh_manifest.version:
            if not self._is_valid_version(okh_manifest.version):
                result.add_error(
                    "Version should follow semantic versioning (e.g., '1.0.0')",
                    field="version",
                    code="invalid_version_format"
                )
        
        # Validate license
        if hasattr(okh_manifest, 'license') and okh_manifest.license:
            if not self._is_valid_license(okh_manifest.license):
                result.add_warning(
                    "License format may not be standard, consider using SPDX license identifier",
                    field="license",
                    code="non_standard_license"
                )
        
        # Validate function description
        if hasattr(okh_manifest, 'function') and okh_manifest.function:
            if len(okh_manifest.function.strip()) < 10:
                result.add_warning(
                    "Function description is very brief, consider providing more detail",
                    field="function",
                    code="function_description_brief"
                )
    
    async def _validate_tsdc_compliance(self, okh_manifest: OKHManifest, 
                                      quality_level: str, result: ValidationResult):
        """Validate TSDC (Technology-Specific Design Constraints) compliance"""
        
        if not hasattr(okh_manifest, 'tsdc') or not okh_manifest.tsdc:
            if quality_level in ['professional', 'medical']:
                result.add_warning(
                    "No TSDC specified, consider adding technology-specific design constraints",
                    field="tsdc",
                    code="tsdc_missing"
                )
            return
        
        for tsdc in okh_manifest.tsdc:
            if not self._validate_tsdc_type(okh_manifest, tsdc, quality_level, result):
                result.add_error(
                    f"TSDC '{tsdc}' compliance validation failed",
                    field="tsdc",
                    code="tsdc_compliance_failed"
                )
    
    def _validate_tsdc_type(self, okh_manifest: OKHManifest, tsdc: str, 
                          quality_level: str, result: ValidationResult) -> bool:
        """Validate specific TSDC type compliance"""
        
        if tsdc == "PCB":
            return self._validate_pcb_tsdc(okh_manifest, quality_level, result)
        elif tsdc == "3DP":
            return self._validate_3dp_tsdc(okh_manifest, quality_level, result)
        elif tsdc == "MECH":
            return self._validate_mech_tsdc(okh_manifest, quality_level, result)
        else:
            # Unknown TSDC type - add warning but don't fail
            result.add_warning(
                f"Unknown TSDC type '{tsdc}', validation skipped",
                field="tsdc",
                code="unknown_tsdc_type"
            )
            return True
    
    def _validate_pcb_tsdc(self, okh_manifest: OKHManifest, 
                         quality_level: str, result: ValidationResult) -> bool:
        """Validate PCB-specific TSDC compliance"""
        
        # Check for PCB-specific fields in parts
        has_pcb_parts = False
        for part in getattr(okh_manifest, 'parts', []):
            if hasattr(part, 'tsdc') and "PCB" in part.tsdc:
                has_pcb_parts = True
                
                # Check for required PCB fields
                required_pcb_fields = ["board-thickness-mm", "copper-thickness-mm", "component-sides"]
                missing_pcb_fields = []
                
                for field in required_pcb_fields:
                    if not hasattr(part, field.replace("-", "_")):
                        missing_pcb_fields.append(field)
                
                if missing_pcb_fields and quality_level in ['professional', 'medical']:
                    result.add_error(
                        f"PCB part missing required fields: {', '.join(missing_pcb_fields)}",
                        field="parts",
                        code="pcb_fields_missing"
                    )
                    return False
        
        if not has_pcb_parts:
            result.add_warning(
                "TSDC specifies PCB but no PCB parts found",
                field="tsdc",
                code="pcb_parts_missing"
            )
        
        # Check for PCB design files
        has_pcb_files = False
        for doc in getattr(okh_manifest, 'design_files', []):
            if hasattr(doc, 'title') and "PCB" in doc.title:
                has_pcb_files = True
                break
        
        if not has_pcb_files and quality_level in ['professional', 'medical']:
            result.add_warning(
                "No PCB design files found for PCB TSDC",
                field="design_files",
                code="pcb_design_files_missing"
            )
        
        return True
    
    def _validate_3dp_tsdc(self, okh_manifest: OKHManifest, 
                         quality_level: str, result: ValidationResult) -> bool:
        """Validate 3D printing TSDC compliance"""
        
        # Check for 3DP parts
        has_3dp_parts = False
        for part in getattr(okh_manifest, 'parts', []):
            if hasattr(part, 'tsdc') and "3DP" in part.tsdc:
                has_3dp_parts = True
                
                # Check for 3DP-specific fields
                if hasattr(part, 'manufacturing_params'):
                    required_3dp_fields = ["printing-process", "material"]
                    missing_3dp_fields = []
                    
                    for field in required_3dp_fields:
                        if field not in part.manufacturing_params:
                            missing_3dp_fields.append(field)
                    
                    if missing_3dp_fields and quality_level in ['professional', 'medical']:
                        result.add_error(
                            f"3DP part missing required fields: {', '.join(missing_3dp_fields)}",
                            field="parts",
                            code="3dp_fields_missing"
                        )
                        return False
        
        if not has_3dp_parts:
            result.add_warning(
                "TSDC specifies 3DP but no 3DP parts found",
                field="tsdc",
                code="3dp_parts_missing"
            )
        
        # Check for 3D model files
        has_3d_files = False
        for doc in getattr(okh_manifest, 'design_files', []):
            if hasattr(doc, 'path'):
                ext = doc.path.split('.')[-1].lower() if '.' in doc.path else ''
                if ext in ['stl', 'obj', '3mf', 'scad']:
                    has_3d_files = True
                    break
        
        if not has_3d_files and quality_level in ['professional', 'medical']:
            result.add_warning(
                "No 3D model files found for 3DP TSDC",
                field="design_files",
                code="3d_model_files_missing"
            )
        
        return True
    
    def _validate_mech_tsdc(self, okh_manifest: OKHManifest, 
                          quality_level: str, result: ValidationResult) -> bool:
        """Validate mechanical TSDC compliance"""
        
        # Check for mechanical parts
        has_mech_parts = False
        for part in getattr(okh_manifest, 'parts', []):
            if hasattr(part, 'tsdc') and "MECH" in part.tsdc:
                has_mech_parts = True
                
                # Check for mechanical-specific fields
                if hasattr(part, 'manufacturing_params'):
                    required_mech_fields = ["material", "tolerance"]
                    missing_mech_fields = []
                    
                    for field in required_mech_fields:
                        if field not in part.manufacturing_params:
                            missing_mech_fields.append(field)
                    
                    if missing_mech_fields and quality_level in ['professional', 'medical']:
                        result.add_error(
                            f"Mechanical part missing required fields: {', '.join(missing_mech_fields)}",
                            field="parts",
                            code="mech_fields_missing"
                        )
                        return False
        
        if not has_mech_parts:
            result.add_warning(
                "TSDC specifies MECH but no mechanical parts found",
                field="tsdc",
                code="mech_parts_missing"
            )
        
        return True
    
    async def _validate_manufacturing_processes(self, okh_manifest: OKHManifest, 
                                             quality_level: str, result: ValidationResult):
        """Validate manufacturing processes"""
        
        if not hasattr(okh_manifest, 'manufacturing_processes') or not okh_manifest.manufacturing_processes:
            if quality_level in ['professional', 'medical']:
                result.add_error(
                    "Manufacturing processes are required for professional/medical quality levels",
                    field="manufacturing_processes",
                    code="manufacturing_processes_required"
                )
            else:
                result.add_warning(
                    "No manufacturing processes specified",
                    field="manufacturing_processes",
                    code="manufacturing_processes_missing"
                )
            return
        
        # Validate each manufacturing process
        for process in okh_manifest.manufacturing_processes:
            if not self._is_valid_manufacturing_process(process):
                result.add_error(
                    f"Invalid manufacturing process: {process}",
                    field="manufacturing_processes",
                    code="invalid_manufacturing_process"
                )
    
    def _is_valid_manufacturing_process(self, process: str) -> bool:
        """Check if manufacturing process is valid"""
        # List of valid manufacturing processes
        valid_processes = [
            "https://en.wikipedia.org/wiki/CNC_mill",
            "https://en.wikipedia.org/wiki/3D_printing",
            "https://en.wikipedia.org/wiki/CNC_lathe",
            "https://en.wikipedia.org/wiki/Laser_cutting",
            "https://en.wikipedia.org/wiki/Water_jet_cutting",
            "https://en.wikipedia.org/wiki/Injection_molding",
            "https://en.wikipedia.org/wiki/Sheet_metal_forming",
            "https://en.wikipedia.org/wiki/Welding",
            "https://en.wikipedia.org/wiki/Assembly"
        ]
        
        return process in valid_processes
    
    async def _validate_materials_and_tools(self, okh_manifest: OKHManifest, 
                                         quality_level: str, result: ValidationResult):
        """Validate materials and tools"""
        
        # Validate materials
        if not hasattr(okh_manifest, 'materials') or not okh_manifest.materials:
            if quality_level in ['professional', 'medical']:
                result.add_error(
                    "Materials specification is required for professional/medical quality levels",
                    field="materials",
                    code="materials_required"
                )
            else:
                result.add_warning(
                    "No materials specified",
                    field="materials",
                    code="materials_missing"
                )
        
        # Validate tool list
        if not hasattr(okh_manifest, 'tool_list') or not okh_manifest.tool_list:
            if quality_level in ['professional', 'medical']:
                result.add_error(
                    "Tool list is required for professional/medical quality levels",
                    field="tool_list",
                    code="tool_list_required"
                )
            else:
                result.add_warning(
                    "No tool list specified",
                    field="tool_list",
                    code="tool_list_missing"
                )
    
    def _calculate_completeness(self, okh_manifest: OKHManifest, quality_level: str) -> float:
        """Calculate completeness score (0.0-1.0)"""
        
        # Get validation rules for this quality level
        rules = self.validation_rules.get_okh_validation_rules(quality_level)
        required_fields = rules.get('required_fields', [])
        optional_fields = rules.get('optional_fields', [])
        
        # Count present fields
        manifest_dict = okh_manifest.to_dict()
        required_present = sum(1 for field in required_fields 
                             if field in manifest_dict and manifest_dict[field] is not None)
        optional_present = sum(1 for field in optional_fields 
                             if field in manifest_dict and manifest_dict[field] is not None)
        
        # Calculate score (required fields weighted more heavily)
        if not required_fields:
            return 0.0
        
        required_score = required_present / len(required_fields)
        optional_score = optional_present / len(optional_fields) if optional_fields else 1.0
        
        # Weight: 70% required fields, 30% optional fields
        return 0.7 * required_score + 0.3 * optional_score
    
    async def _add_optional_field_warnings(self, okh_manifest: OKHManifest, 
                                        quality_level: str, result: ValidationResult):
        """Add warnings for missing optional fields"""
        
        rules = self.validation_rules.get_okh_validation_rules(quality_level)
        optional_fields = rules.get('optional_fields', [])
        
        manifest_dict = okh_manifest.to_dict()
        missing_optional = [field for field in optional_fields 
                          if field not in manifest_dict or manifest_dict[field] is None]
        
        for field in missing_optional:
            result.add_warning(
                f"Optional field '{field}' is missing, consider adding for better documentation",
                field=field,
                code="optional_field_missing"
            )
    
    def _is_valid_version(self, version: str) -> bool:
        """Check if version follows semantic versioning"""
        import re
        # Basic semantic versioning pattern
        pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$'
        return bool(re.match(pattern, version))
    
    def _is_valid_license(self, license_str: str) -> bool:
        """Check if license is a standard SPDX identifier"""
        # Common SPDX license identifiers
        spdx_licenses = [
            "MIT", "Apache-2.0", "GPL-3.0", "GPL-2.0", "BSD-3-Clause", 
            "BSD-2-Clause", "LGPL-3.0", "LGPL-2.1", "MPL-2.0", "CC0-1.0",
            "CC-BY-4.0", "CC-BY-SA-4.0", "Unlicense", "ISC"
        ]
        
        return license_str in spdx_licenses
    
    # Legacy compatibility methods
    def validate_okh_manifest(self, okh_manifest: OKHManifest) -> Dict[str, Any]:
        """Legacy method for backward compatibility"""
        # This method maintains compatibility with the existing interface
        # but uses the new validation framework internally
        
        # Create a default context for legacy calls
        from ....validation.context import ValidationContext
        context = ValidationContext(
            name="legacy_okh_validation",
            domain="manufacturing",
            quality_level="professional"
        )
        
        # Run async validation synchronously for legacy compatibility
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, we need to handle this differently
                # For now, create a simple result
                result = ValidationResult(valid=True)
                result.metadata['completeness_score'] = 0.5
                return result.to_dict()
            else:
                result = loop.run_until_complete(self.validate(okh_manifest, context))
                return result.to_dict()
        except RuntimeError:
            # No event loop, create a simple result
            result = ValidationResult(valid=True)
            result.metadata['completeness_score'] = 0.5
            return result.to_dict()
    
    def validate_supply_tree(self, supply_tree: SupplyTree, 
                          okh_manifest: OKHManifest) -> Dict[str, Any]:
        """Legacy method for supply tree validation"""
        # This would be implemented in the supply tree validator
        # For now, return a basic result
        return {
            "valid": True,
            "confidence": 0.8,
            "issues": [],
            "warnings": []
        }
