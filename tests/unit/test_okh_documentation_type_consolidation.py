"""
Unit tests for DocumentationType consolidation.

Tests that USER_MANUAL, TOOL_SETTINGS, and QUALITY_INSTRUCTIONS are properly
consolidated into OPERATING_INSTRUCTIONS, MAKING_INSTRUCTIONS, and TECHNICAL_SPECIFICATIONS.
"""

import pytest
from src.core.models.okh import (
    DocumentationType,
    DocumentRef,
    OKHManifest,
    License
)


class TestDocumentationTypeConsolidation:
    """Test that old types are removed and consolidated."""
    
    def test_user_manual_removed(self):
        """Test that USER_MANUAL is removed from enum."""
        assert not hasattr(DocumentationType, 'USER_MANUAL')
    
    def test_tool_settings_removed(self):
        """Test that TOOL_SETTINGS is removed from enum."""
        assert not hasattr(DocumentationType, 'TOOL_SETTINGS')
    
    def test_quality_instructions_removed(self):
        """Test that QUALITY_INSTRUCTIONS is removed from enum."""
        assert not hasattr(DocumentationType, 'QUALITY_INSTRUCTIONS')
    
    def test_operating_instructions_still_exists(self):
        """Test that OPERATING_INSTRUCTIONS still exists (consolidates USER_MANUAL)."""
        assert hasattr(DocumentationType, 'OPERATING_INSTRUCTIONS')
        assert DocumentationType.OPERATING_INSTRUCTIONS.value == "operating-instructions"
    
    def test_making_instructions_still_exists(self):
        """Test that MAKING_INSTRUCTIONS still exists (consolidates TOOL_SETTINGS)."""
        assert hasattr(DocumentationType, 'MAKING_INSTRUCTIONS')
        assert DocumentationType.MAKING_INSTRUCTIONS.value == "making-instructions"
    
    def test_technical_specifications_still_exists(self):
        """Test that TECHNICAL_SPECIFICATIONS still exists (consolidates QUALITY_INSTRUCTIONS)."""
        assert hasattr(DocumentationType, 'TECHNICAL_SPECIFICATIONS')
        assert DocumentationType.TECHNICAL_SPECIFICATIONS.value == "technical-specifications"


class TestBackwardCompatibility:
    """Test backward compatibility with old type values."""
    
    def test_user_manual_value_maps_to_operating_instructions(self):
        """Test that 'user-manual' string value maps to OPERATING_INSTRUCTIONS."""
        # The _missing_ method should map old values to new ones
        doc_type = DocumentationType('user-manual')
        assert doc_type == DocumentationType.OPERATING_INSTRUCTIONS
        assert doc_type.value == "operating-instructions"
    
    def test_tool_settings_value_maps_to_making_instructions(self):
        """Test that 'tool-settings' string value maps to MAKING_INSTRUCTIONS."""
        doc_type = DocumentationType('tool-settings')
        assert doc_type == DocumentationType.MAKING_INSTRUCTIONS
        assert doc_type.value == "making-instructions"
    
    def test_quality_instructions_value_maps_to_technical_specifications(self):
        """Test that 'quality-instructions' string value maps to TECHNICAL_SPECIFICATIONS."""
        doc_type = DocumentationType('quality-instructions')
        assert doc_type == DocumentationType.TECHNICAL_SPECIFICATIONS
        assert doc_type.value == "technical-specifications"
    
    def test_from_dict_with_old_values(self):
        """Test that from_dict() correctly handles old type values."""
        manifest_data = {
            'title': 'Test',
            'version': '1.0.0',
            'license': {'hardware': 'MIT'},
            'licensor': 'Test Author',
            'documentation_language': 'en',
            'function': 'Test function',
            'operating_instructions': [
                {
                    'title': 'User Manual',
                    'path': 'manual/user_guide.pdf',
                    'type': 'user-manual',  # Old value
                    'metadata': {}
                }
            ],
            'making_instructions': [
                {
                    'title': 'Tool Settings',
                    'path': 'config/tool_settings.md',
                    'type': 'tool-settings',  # Old value
                    'metadata': {}
                }
            ],
            'design_files': [
                {
                    'title': 'Quality Instructions',
                    'path': 'quality/quality_instructions.md',
                    'type': 'quality-instructions',  # Old value
                    'metadata': {}
                }
            ]
        }
        
        manifest = OKHManifest.from_dict(manifest_data)
        
        # Old values should be mapped to new types
        assert len(manifest.operating_instructions) == 1
        assert manifest.operating_instructions[0].type == DocumentationType.OPERATING_INSTRUCTIONS
        
        assert len(manifest.making_instructions) == 1
        assert manifest.making_instructions[0].type == DocumentationType.MAKING_INSTRUCTIONS
        
        assert len(manifest.design_files) == 1
        assert manifest.design_files[0].type == DocumentationType.TECHNICAL_SPECIFICATIONS


class TestDocumentRefWithConsolidatedTypes:
    """Test DocumentRef with consolidated types."""
    
    def test_operating_instructions_replaces_user_manual(self):
        """Test that OPERATING_INSTRUCTIONS can be used where USER_MANUAL was used."""
        doc = DocumentRef(
            title="User Manual",
            path="manual/user_guide.pdf",
            type=DocumentationType.OPERATING_INSTRUCTIONS
        )
        assert doc.type == DocumentationType.OPERATING_INSTRUCTIONS
        assert doc.type.value == "operating-instructions"
    
    def test_making_instructions_includes_tool_settings(self):
        """Test that MAKING_INSTRUCTIONS can include tool settings content."""
        doc = DocumentRef(
            title="Tool Settings",
            path="config/tool_settings.md",
            type=DocumentationType.MAKING_INSTRUCTIONS
        )
        assert doc.type == DocumentationType.MAKING_INSTRUCTIONS
        assert doc.type.value == "making-instructions"
    
    def test_technical_specifications_includes_quality_instructions(self):
        """Test that TECHNICAL_SPECIFICATIONS can include quality instructions."""
        doc = DocumentRef(
            title="Quality Instructions",
            path="quality/quality_instructions.md",
            type=DocumentationType.TECHNICAL_SPECIFICATIONS
        )
        assert doc.type == DocumentationType.TECHNICAL_SPECIFICATIONS
        assert doc.type.value == "technical-specifications"

