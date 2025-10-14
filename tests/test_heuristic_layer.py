"""
Tests for the Heuristic Matching Layer.

This module tests the heuristic matching functionality including README parsing,
file structure analysis, license detection, and content pattern matching.
"""

import pytest
import asyncio
from pathlib import Path

from src.core.generation.layers.heuristic import HeuristicMatcher
from src.core.generation.models import ProjectData, PlatformType, FileInfo, DocumentInfo


class TestHeuristicMatcher:
    """Test cases for the HeuristicMatcher class"""
    
    def test_heuristic_matcher_initialization(self):
        """Test that HeuristicMatcher initializes correctly"""
        matcher = HeuristicMatcher()
        assert matcher.layer_type.value == "heuristic"
        assert len(matcher.file_patterns) > 0
        assert len(matcher.content_patterns) > 0
    
    @pytest.mark.asyncio
    async def test_readme_parsing(self):
        """Test README content parsing for key fields"""
        project_data = ProjectData(
            url="https://github.com/test/project",
            platform=PlatformType.GITHUB,
            metadata={"name": "Test Project", "description": "A test project"},
            files=[
                FileInfo(
                    path="README.md",
                    size=200,
                    content="""
# Test Project

Function: This is a 3D printable stethoscope for medical diagnosis.

Intended use: Medical diagnosis and patient care in clinical settings.

Materials: PLA filament, electronics components, sensors

Tools: 3D printer, soldering iron, multimeter

Keywords: medical, 3d-printing, stethoscope, healthcare
                    """,
                    file_type="markdown"
                )
            ],
            documentation=[
                DocumentInfo(
                    title="README",
                    path="README.md",
                    content="""
# Test Project

Function: This is a 3D printable stethoscope for medical diagnosis.

Intended use: Medical diagnosis and patient care in clinical settings.

Materials: PLA filament, electronics components, sensors

Tools: 3D printer, soldering iron, multimeter

Keywords: medical, 3d-printing, stethoscope, healthcare
                    """,
                    doc_type="readme"
                )
            ],
            raw_content={
                "README.md": """
# Test Project

Function: This is a 3D printable stethoscope for medical diagnosis.

Intended use: Medical diagnosis and patient care in clinical settings.

Materials: PLA filament, electronics components, sensors

Tools: 3D printer, soldering iron, multimeter

Keywords: medical, 3d-printing, stethoscope, healthcare
                """
            }
        )
        
        matcher = HeuristicMatcher()
        result = await matcher.process(project_data)
        
        # Check that key fields were extracted
        assert result.has_field("function")
        assert result.has_field("intended_use")
        # Keywords are now handled by NLP/LLM layers, not heuristic layer
        assert result.has_field("materials")
        assert result.has_field("tool_list")
        
        # Check field values
        function_field = result.get_field("function")
        assert "stethoscope" in function_field.value.lower()
        assert function_field.confidence >= 0.8
        
        intended_use_field = result.get_field("intended_use")
        assert "medical" in intended_use_field.value.lower()
        assert intended_use_field.confidence >= 0.8
        
        # Keywords are now handled by NLP/LLM layers, not heuristic layer
        
        materials_field = result.get_field("materials")
        assert "PLA filament" in materials_field.value
        assert "electronics" in materials_field.value
        
        tool_list_field = result.get_field("tool_list")
        assert isinstance(tool_list_field.value, list)
        assert "3D printer" in tool_list_field.value
        assert "soldering iron" in tool_list_field.value
    
    @pytest.mark.asyncio
    async def test_license_detection(self):
        """Test license file detection and parsing"""
        project_data = ProjectData(
            url="https://github.com/test/project",
            platform=PlatformType.GITHUB,
            metadata={"name": "Test Project"},
            files=[
                FileInfo(
                    path="LICENSE",
                    size=100,
                    content="""
MIT License

Copyright (c) 2023 Test Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
                    """,
                    file_type="text"
                )
            ],
            documentation=[],
            raw_content={
                "LICENSE": """
MIT License

Copyright (c) 2023 Test Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
                """
            }
        )
        
        matcher = HeuristicMatcher()
        result = await matcher.process(project_data)
        
        # Check license detection
        assert result.has_field("license")
        license_field = result.get_field("license")
        assert license_field.value == "MIT"
        assert license_field.confidence >= 0.9
    
    @pytest.mark.asyncio
    async def test_file_structure_analysis(self):
        """Test file structure analysis for manufacturing and design files"""
        project_data = ProjectData(
            url="https://github.com/test/project",
            platform=PlatformType.GITHUB,
            metadata={"name": "Test Project"},
            files=[
                FileInfo(path="stl/main.stl", size=1000, content="", file_type="stl"),
                FileInfo(path="stl/parts.stl", size=2000, content="", file_type="stl"),
                FileInfo(path="openscad/main.scad", size=500, content="", file_type="scad"),
                FileInfo(path="docs/assembly.md", size=300, content="", file_type="markdown"),
                FileInfo(path="docs/manufacturing.md", size=400, content="", file_type="markdown"),
            ],
            documentation=[],
            raw_content={}
        )
        
        matcher = HeuristicMatcher()
        result = await matcher.process(project_data)
        
        # Check manufacturing files detection
        assert result.has_field("manufacturing_files")
        manufacturing_files = result.get_field("manufacturing_files").value
        assert isinstance(manufacturing_files, list)
        assert len(manufacturing_files) >= 2  # Should detect STL files
        
        # Check design files detection
        assert result.has_field("design_files")
        design_files = result.get_field("design_files").value
        assert isinstance(design_files, list)
        assert len(design_files) >= 1  # Should detect OpenSCAD file
        
        # Check making instructions detection
        assert result.has_field("making_instructions")
        making_instructions = result.get_field("making_instructions").value
        assert isinstance(making_instructions, list)
        assert len(making_instructions) >= 2  # Should detect docs files
    
    @pytest.mark.asyncio
    async def test_manufacturing_process_detection(self):
        """Test manufacturing process detection from content"""
        project_data = ProjectData(
            url="https://github.com/test/project",
            platform=PlatformType.GITHUB,
            metadata={"name": "Test Project"},
            files=[],
            documentation=[
                DocumentInfo(
                    title="Assembly Guide",
                    path="docs/assembly.md",
                    content="""
# Assembly Guide

This project requires 3D printing of all components.
After printing, you need to solder the electronics.
The final assembly involves laser cutting the base plate.
                    """,
                    doc_type="assembly"
                )
            ],
            raw_content={
                "docs/assembly.md": """
# Assembly Guide

This project requires 3D printing of all components.
After printing, you need to solder the electronics.
The final assembly involves laser cutting the base plate.
                """
            }
        )
        
        matcher = HeuristicMatcher()
        result = await matcher.process(project_data)
        
        # Check manufacturing processes detection
        assert result.has_field("manufacturing_processes")
        processes = result.get_field("manufacturing_processes").value
        assert isinstance(processes, list)
        assert "3D Printing" in processes
        assert "Soldering" in processes
        assert "Laser cutting" in processes
    
    @pytest.mark.asyncio
    async def test_bom_parsing(self):
        """Test BOM file parsing"""
        project_data = ProjectData(
            url="https://github.com/test/project",
            platform=PlatformType.GITHUB,
            metadata={"name": "Test Project"},
            files=[
                FileInfo(
                    path="bom.csv",
                    size=200,
                    content="""
Component,Quantity,Unit,Notes
PLA Filament,500,g,White color
Arduino Nano,1,pcs,Microcontroller
LED,5,pcs,Red LEDs
Resistor,10,pcs,220 ohm
                    """,
                    file_type="csv"
                )
            ],
            documentation=[],
            raw_content={
                "bom.csv": """
Component,Quantity,Unit,Notes
PLA Filament,500,g,White color
Arduino Nano,1,pcs,Microcontroller
LED,5,pcs,Red LEDs
Resistor,10,pcs,220 ohm
                """
            }
        )
        
        matcher = HeuristicMatcher()
        result = await matcher.process(project_data)
        
        # Check BOM parsing
        assert result.has_field("materials")
        materials = result.get_field("materials").value
        assert isinstance(materials, list)
        assert len(materials) >= 4
        
        # Check specific materials
        material_names = [m["name"] for m in materials]
        assert "PLA Filament" in material_names
        assert "Arduino Nano" in material_names
        assert "LED" in material_names
        assert "Resistor" in material_names
        
        # Check quantities
        pla_material = next(m for m in materials if m["name"] == "PLA Filament")
        assert pla_material["quantity"] == 500
        assert pla_material["unit"] == "g"
    
    @pytest.mark.asyncio
    async def test_content_pattern_matching(self):
        """Test content pattern matching for various fields"""
        project_data = ProjectData(
            url="https://github.com/test/project",
            platform=PlatformType.GITHUB,
            metadata={"name": "Test Project"},
            files=[],
            documentation=[
                DocumentInfo(
                    title="Project Description",
                    path="docs/description.md",
                        content="""
This project aims to create a 3D printable microscope for scientific research.
It can be used for scientific research and education.
The device is made from PLA plastic and requires CNC machining for some parts.
                        """,
                    doc_type="description"
                )
            ],
            raw_content={
                    "docs/description.md": """
This project aims to create a 3D printable microscope for scientific research.
It can be used for scientific research and education.
The device is made from PLA plastic and requires CNC machining for some parts.
                    """
                }
        )
        
        matcher = HeuristicMatcher()
        result = await matcher.process(project_data)
        
        # Check function extraction
        assert result.has_field("function")
        function_field = result.get_field("function")
        assert "microscope" in function_field.value.lower()
        
        # Check intended use extraction
        assert result.has_field("intended_use")
        intended_use_field = result.get_field("intended_use")
        assert "research" in intended_use_field.value.lower() or "education" in intended_use_field.value.lower()
        
        # Check manufacturing processes
        assert result.has_field("manufacturing_processes")
        processes = result.get_field("manufacturing_processes").value
        assert "3D Printing" in processes
        assert "CNC machining" in processes
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in heuristic processing"""
        # Test with empty project data
        project_data = ProjectData(
            url="https://github.com/test/project",
            platform=PlatformType.GITHUB,
            metadata={},
            files=[],
            documentation=[],
            raw_content={}
        )
        
        matcher = HeuristicMatcher()
        result = await matcher.process(project_data)
        
        # Should not crash and should return minimal result
        # Now extracts version and documentation_language even with empty data
        assert len(result.fields) >= 2  # Should have version and documentation_language
        assert result.has_field("version")
        assert result.has_field("documentation_language")
        assert len(result.errors) == 0  # Should handle empty data gracefully
        assert len(result.processing_log) > 0  # Should have processing log
    
    @pytest.mark.asyncio
    async def test_confidence_scoring(self):
        """Test that confidence scores are appropriate"""
        project_data = ProjectData(
            url="https://github.com/test/project",
            platform=PlatformType.GITHUB,
            metadata={"name": "Test Project"},
            files=[
                FileInfo(
                    path="LICENSE",
                    size=100,
                    content="MIT License",
                    file_type="text"
                )
            ],
            documentation=[],
            raw_content={"LICENSE": "MIT License"}
        )
        
        matcher = HeuristicMatcher()
        result = await matcher.process(project_data)
        
        # Check confidence scores are within valid range
        for field_name, confidence in result.confidence_scores.items():
            assert 0.0 <= confidence <= 1.0, f"Confidence for {field_name} should be between 0 and 1, got {confidence}"
        
        # License detection should have high confidence
        if result.has_field("license"):
            license_confidence = result.get_confidence("license")
            assert license_confidence >= 0.8, f"License detection should have high confidence, got {license_confidence}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
