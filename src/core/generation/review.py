"""
Review Interface for OKH manifest generation.

This module provides a CLI-based interface for reviewing, editing, and validating
generated OKH manifests before final export. It includes enhanced support for
tracking field sources, including LLM-generated content, and provides detailed
information about how each field was generated.

Key Features:
- Interactive field editing and validation
- Source tracking for all fields (Direct, Heuristic, NLP, LLM, User Edit)
- Quality assessment and recommendations
- LLM-specific indicators and confidence scoring
- Export to OKH manifest format
"""

import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .models import (
    ManifestGeneration, FieldGeneration, GenerationLayer, ProjectData
)
from ..models.okh import OKHManifest


@dataclass
class FieldSourceInfo:
    """Information about how a field was generated"""
    layer: GenerationLayer
    method: str
    confidence: float
    raw_source: str
    is_llm_generated: bool = False
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


class ReviewInterface:
    """
    Enhanced CLI-based interface for reviewing and editing generated manifests.
    
    This interface provides comprehensive review capabilities including:
    - Field source tracking (Direct, Heuristic, NLP, LLM, User Edit)
    - LLM-specific indicators and confidence scoring
    - Quality assessment and recommendations
    - Interactive editing and validation
    - Export to OKH manifest format
    """
    
    def __init__(self, manifest_generation: ManifestGeneration):
        """
        Initialize the review interface.
        
        Args:
            manifest_generation: The generated manifest to review
        """
        self.manifest_generation = manifest_generation
        self._commands = {
            'e': self._edit_field,
            'a': self._add_field,
            'r': self._remove_field,
            'q': self._show_quality_report,
            's': self._show_field_sources,
            'l': self._show_llm_fields,
            'x': self._export_manifest,
            'h': self._show_help,
            'quit': self._quit
        }
    
    async def review(self) -> Optional[OKHManifest]:
        """
        Start the interactive review process.
        
        Returns:
            OKHManifest if exported, None if quit
        """
            
        print("🔍 OKH Manifest Review Interface")
        print("=" * 50)
        print(f"Project: {self.manifest_generation.project_data.url}")
        print(f"Generated Fields: {len(self.manifest_generation.generated_fields)}")
        print(f"Missing Required: {len(self.manifest_generation.missing_fields)}")
        
        # Show field source summary
        source_summary = self._get_field_source_summary()
        print(f"Field Sources: {source_summary}")
        
        # Show LLM indicators if any LLM fields exist
        llm_fields = self._get_llm_fields()
        if llm_fields:
            print(f"🤖 LLM-Generated Fields: {len(llm_fields)}")
        
        print()
        
        self._show_help()
        
        while True:
            try:
                command = input("\n> ").strip().lower()
                
                if command in self._commands:
                    result = self._commands[command]()
                    if result is False:  # Quit command
                        break
                    elif isinstance(result, OKHManifest):  # Export command
                        return result
                else:
                    print("❌ Unknown command. Type 'h' for help.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Review cancelled by user.")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        return self.manifest_generation
    
    def _get_field_source_summary(self) -> str:
        """
        Get a summary of field sources.
        
        Returns:
            String summary of field sources
        """
        source_counts = {}
        for field_gen in self.manifest_generation.generated_fields.values():
            layer = field_gen.source_layer.value
            source_counts[layer] = source_counts.get(layer, 0) + 1
        
        summary_parts = []
        for layer, count in source_counts.items():
            summary_parts.append(f"{layer}: {count}")
        
        return ", ".join(summary_parts)
    
    def _get_llm_fields(self) -> Dict[str, FieldGeneration]:
        """
        Get all LLM-generated fields.
        
        Returns:
            Dictionary of LLM-generated fields
        """
        llm_fields = {}
        for field_name, field_gen in self.manifest_generation.generated_fields.items():
            if field_gen.source_layer == GenerationLayer.LLM:
                llm_fields[field_name] = field_gen
        return llm_fields
    
    def _show_field_sources(self) -> None:
        """Show detailed field source information"""
        print("\n📋 FIELD SOURCES")
        print("=" * 40)
        
        for field_name, field_gen in self.manifest_generation.generated_fields.items():
            layer_icon = self._get_layer_icon(field_gen.source_layer)
            confidence_bar = self._get_confidence_bar(field_gen.confidence)
            
            print(f"{layer_icon} {field_name}: {confidence_bar} ({field_gen.confidence:.2f})")
            print(f"   Method: {field_gen.generation_method}")
            print(f"   Source: {field_gen.raw_source}")
            
            # Show LLM-specific info if applicable
            if field_gen.source_layer == GenerationLayer.LLM:
                print(f"   🤖 LLM-Generated Content")
            
            print()
    
    def _show_llm_fields(self) -> None:
        """Show LLM-generated fields in detail"""
        llm_fields = self._get_llm_fields()
        
        if not llm_fields:
            print("\n🤖 No LLM-generated fields found")
            return
        
        print(f"\n🤖 LLM-GENERATED FIELDS ({len(llm_fields)})")
        print("=" * 50)
        
        for field_name, field_gen in llm_fields.items():
            confidence_bar = self._get_confidence_bar(field_gen.confidence)
            print(f"📝 {field_name}: {confidence_bar} ({field_gen.confidence:.2f})")
            print(f"   Value: {field_gen.value}")
            print(f"   Method: {field_gen.generation_method}")
            print(f"   Source: {field_gen.raw_source}")
            print()
    
    def _get_layer_icon(self, layer: GenerationLayer) -> str:
        """Get icon for layer type"""
        icons = {
            GenerationLayer.DIRECT: "🔗",
            GenerationLayer.HEURISTIC: "🔍",
            GenerationLayer.NLP: "🧠",
            GenerationLayer.LLM: "🤖",
            GenerationLayer.BOM_NORMALIZATION: "📋",
            GenerationLayer.USER_EDIT: "✏️"
        }
        return icons.get(layer, "❓")
    
    def _get_confidence_bar(self, confidence: float) -> str:
        """Get visual confidence bar"""
        if confidence >= 0.9:
            return "🟢" + "█" * 10
        elif confidence >= 0.7:
            return "🟡" + "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
        elif confidence >= 0.5:
            return "🟠" + "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
        else:
            return "🔴" + "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
    
    def edit_field(self, field_name: str, new_value: str) -> None:
        """
        Edit an existing field in the manifest.
        
        Args:
            field_name: Name of the field to edit
            new_value: New value for the field
            
        Raises:
            ValueError: If field doesn't exist or value is invalid
        """
        if not field_name:
            raise ValueError("Field name cannot be empty")
        
        if not new_value:
            raise ValueError("Field value cannot be empty")
        
        if field_name not in self.manifest_generation.generated_fields:
            raise ValueError(f"Field '{field_name}' not found")
        
        # Update the field with user edit
        field_gen = self.manifest_generation.generated_fields[field_name]
        field_gen.value = new_value
        field_gen.confidence = 1.0  # User edit = 100% confidence
        field_gen.source_layer = GenerationLayer.USER_EDIT
        field_gen.generation_method = "user_edit"
        field_gen.raw_source = "user_input"
        
        # Update confidence score
        self.manifest_generation.confidence_scores[field_name] = 1.0
        
        # Regenerate quality report
        self._regenerate_quality_report()
        
        print(f"✅ Updated field '{field_name}' to: {new_value}")
    
    def add_field(self, field_name: str, value: str) -> None:
        """
        Add a new field to the manifest.
        
        Args:
            field_name: Name of the field to add
            value: Value for the field
            
        Raises:
            ValueError: If field name or value is invalid
        """
        if not field_name:
            raise ValueError("Invalid field name")
        
        if not value:
            raise ValueError("Field value cannot be empty")
        
        if field_name in self.manifest_generation.generated_fields:
            raise ValueError(f"Field '{field_name}' already exists. Use edit instead.")
        
        # Create new field generation
        field_gen = FieldGeneration(
            value=value,
            confidence=1.0,  # User edit = 100% confidence
            source_layer=GenerationLayer.USER_EDIT,
            generation_method="user_edit",
            raw_source="user_input"
        )
        
        # Add to manifest
        self.manifest_generation.generated_fields[field_name] = field_gen
        self.manifest_generation.confidence_scores[field_name] = 1.0
        
        # Remove from missing fields if it was there
        if field_name in self.manifest_generation.missing_fields:
            self.manifest_generation.missing_fields.remove(field_name)
        
        # Regenerate quality report
        self._regenerate_quality_report()
        
        print(f"✅ Added field '{field_name}': {value}")
    
    def remove_field(self, field_name: str) -> None:
        """
        Remove a field from the manifest.
        
        Args:
            field_name: Name of the field to remove
            
        Raises:
            ValueError: If field doesn't exist
        """
        if field_name not in self.manifest_generation.generated_fields:
            raise ValueError(f"Field '{field_name}' not found")
        
        # Remove from generated fields and confidence scores
        del self.manifest_generation.generated_fields[field_name]
        del self.manifest_generation.confidence_scores[field_name]
        
        # Add to missing fields if it's a required field
        required_fields = [
            "title", "version", "license", "licensor", 
            "documentation_language", "function"
        ]
        if field_name in required_fields:
            self.manifest_generation.missing_fields.append(field_name)
        
        # Regenerate quality report
        self._regenerate_quality_report()
        
        print(f"✅ Removed field '{field_name}'")
    
    def show_quality_report(self) -> None:
        """Display the quality report for the manifest"""
        if not self.manifest_generation.quality_report:
            print("❌ No quality report available")
            return
        
        report = self.manifest_generation.quality_report
        
        print("\n📊 QUALITY REPORT")
        print("=" * 30)
        print(f"Overall Quality: {report.overall_quality:.2f}")
        print(f"Required Fields Complete: {report.required_fields_complete}")
        
        if report.missing_required_fields:
            print(f"Missing Required Fields: {', '.join(report.missing_required_fields)}")
        
        if report.low_confidence_fields:
            print(f"Low Confidence Fields: {', '.join(report.low_confidence_fields)}")
        
        if report.recommendations:
            print("\n💡 Recommendations:")
            for rec in report.recommendations:
                print(f"  • {rec}")
    
    def export_manifest(self) -> OKHManifest:
        """
        Export the manifest to OKH format.
        
        Returns:
            OKHManifest object ready for serialization
        """
        # Convert generated fields to OKH manifest format
        okh_data = {}
        
        # Add basic fields
        for field_name, field_gen in self.manifest_generation.generated_fields.items():
            okh_data[field_name] = field_gen.value
        
        # Add required OKH fields with defaults if missing
        if "okhv" not in okh_data:
            okh_data["okhv"] = "OKH-LOSHv1.0"
        
        if "id" not in okh_data:
            # Generate a simple ID based on the project URL
            url = self.manifest_generation.project_data.url
            # Create a deterministic UUID based on the URL
            namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace
            okh_data["id"] = str(uuid.uuid5(namespace, url))
        
        # Create OKH manifest
        try:
            okh_manifest = OKHManifest.from_dict(okh_data)
            print("✅ Manifest exported successfully")
            return okh_manifest
        except Exception as e:
            print(f"❌ Error exporting manifest: {e}")
            raise
    
    def _edit_field(self) -> None:
        """Interactive field editing"""
        field_name = input("Enter field name to edit: ").strip()
        if not field_name:
            print("❌ Field name cannot be empty")
            return
        
        if field_name not in self.manifest_generation.generated_fields:
            print(f"❌ Field '{field_name}' not found")
            return
        
        current_value = self.manifest_generation.generated_fields[field_name].value
        print(f"Current value: {current_value}")
        
        new_value = input("Enter new value: ").strip()
        if not new_value:
            print("❌ Value cannot be empty")
            return
        
        try:
            self.edit_field(field_name, new_value)
        except ValueError as e:
            print(f"❌ {e}")
    
    def _add_field(self) -> None:
        """Interactive field addition"""
        field_name = input("Enter field name to add: ").strip()
        if not field_name:
            print("❌ Field name cannot be empty")
            return
        
        value = input("Enter field value: ").strip()
        if not value:
            print("❌ Value cannot be empty")
            return
        
        try:
            self.add_field(field_name, value)
        except ValueError as e:
            print(f"❌ {e}")
    
    def _remove_field(self) -> None:
        """Interactive field removal"""
        field_name = input("Enter field name to remove: ").strip()
        if not field_name:
            print("❌ Field name cannot be empty")
            return
        
        try:
            self.remove_field(field_name)
        except ValueError as e:
            print(f"❌ {e}")
    
    def _show_quality_report(self) -> None:
        """Show quality report"""
        self.show_quality_report()
    
    def _export_manifest(self) -> OKHManifest:
        """Export manifest"""
        return self.export_manifest()
    
    def show_help(self) -> None:
        """Show help information"""
        print("\n📋 Available commands:")
        print("  e - Edit field")
        print("  a - Add field")
        print("  r - Remove field")
        print("  q - Show quality report")
        print("  x - Export manifest")
        print("  h - Show help")
        print("  quit - Quit review")
    
    def _show_help(self) -> None:
        """Internal method to show help (calls public method)"""
        self.show_help()
    
    def _quit(self) -> bool:
        """Quit the review process"""
        print("👋 Review completed. Goodbye!")
        return False
    
    def _regenerate_quality_report(self) -> None:
        """Regenerate the quality report after field changes"""
        from .quality import QualityAssessor
        
        # Update missing fields list
        required_fields = [
            "title", "version", "license", "licensor", 
            "documentation_language", "function"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in self.manifest_generation.generated_fields:
                missing_fields.append(field)
        
        self.manifest_generation.missing_fields = missing_fields
        
        # Regenerate quality report
        assessor = QualityAssessor()
        self.manifest_generation.quality_report = assessor.generate_quality_report(
            self.manifest_generation.generated_fields,
            self.manifest_generation.confidence_scores,
            self.manifest_generation.missing_fields,
            required_fields
        )
