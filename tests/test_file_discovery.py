import pytest
from pathlib import Path

from src.core.models.okh import OKHManifest, License, Person, DocumentRef, DocumentationType, PartSpec, Software
from src.core.models.package import BuildOptions
from src.core.packaging.builder import PackageBuilder


class TestFileDiscovery:
    """Test file discovery and categorization from OKH manifests"""
    
    @pytest.fixture
    def sample_manifest_with_files(self):
        """Create a manifest with various file types"""
        return OKHManifest(
            title="Test Project",
            version="1.0.0",
            license=License(hardware="CERN-OHL-S-2.0"),
            licensor=Person(name="Test Author"),
            documentation_language="en",
            function="Test function",
            manufacturing_files=[
                DocumentRef(
                    title="Assembly Guide",
                    path="https://example.com/assembly.pdf",
                    type=DocumentationType.MANUFACTURING_FILES
                ),
                DocumentRef(
                    title="Quality Checklist",
                    path="https://example.com/quality.pdf",
                    type=DocumentationType.QUALITY_INSTRUCTIONS
                )
            ],
            design_files=[
                DocumentRef(
                    title="3D Model",
                    path="https://example.com/model.stl",
                    type=DocumentationType.DESIGN_FILES
                )
            ],
            making_instructions=[
                DocumentRef(
                    title="Build Instructions",
                    path="https://example.com/build.md",
                    type=DocumentationType.MANUFACTURING_FILES
                )
            ],
            parts=[
                PartSpec(
                    name="Main Body",
                    source=["https://example.com/body.scad"],
                    export=["https://example.com/body.stl"],
                    auxiliary=["https://example.com/body_notes.md"],
                    image="https://example.com/body.jpg"
                )
            ],
            software=[
                Software(
                    release="https://example.com/firmware.bin",
                    installation_guide="https://example.com/install.md"
                )
            ],
            bom="https://example.com/bom.csv",
            image="https://example.com/project.jpg"
        )
    
    @pytest.fixture
    def package_builder(self):
        """Create a PackageBuilder instance"""
        return PackageBuilder()
    
    def test_categorize_documents_by_type(self, package_builder, sample_manifest_with_files):
        """Test categorization of documents by DocumentationType"""
        categorized = package_builder._categorize_documents_by_type(
            sample_manifest_with_files.manufacturing_files
        )
        
        assert "manufacturing-files" in categorized
        assert "quality-instructions" in categorized
        assert len(categorized["manufacturing-files"]) == 1
        assert len(categorized["quality-instructions"]) == 1
        
        # Check the specific documents
        manufacturing_docs = categorized["manufacturing-files"]
        assert manufacturing_docs[0].title == "Assembly Guide"
        
        quality_docs = categorized["quality-instructions"]
        assert quality_docs[0].title == "Quality Checklist"
    
    def test_discover_all_files_to_download(self, package_builder, sample_manifest_with_files):
        """Test discovery of all files that need to be downloaded"""
        options = BuildOptions()  # Include all files by default
        
        # This would be a new method we need to implement
        files_to_download = package_builder._discover_files_to_download(
            sample_manifest_with_files, options
        )
        
        # Should include files from all categories
        expected_categories = [
            "manufacturing-files", "design-files", "making-instructions",
            "parts", "software", "bom", "project-image"
        ]
        
        for category in expected_categories:
            assert category in files_to_download
            assert len(files_to_download[category]) > 0
    
    def test_discover_files_with_selective_inclusion(self, package_builder, sample_manifest_with_files):
        """Test file discovery with selective inclusion options"""
        options = BuildOptions(
            include_design_files=False,
            include_software=False,
            include_parts=False
        )
        
        files_to_download = package_builder._discover_files_to_download(
            sample_manifest_with_files, options
        )
        
        # Should exclude design files, software, and parts
        assert "design-files" not in files_to_download or len(files_to_download["design-files"]) == 0
        assert "software" not in files_to_download or len(files_to_download["software"]) == 0
        assert "parts" not in files_to_download or len(files_to_download["parts"]) == 0
        
        # Should still include manufacturing files and making instructions
        assert len(files_to_download["manufacturing-files"]) > 0
        assert len(files_to_download["making-instructions"]) > 0
    
    def test_count_total_files(self, package_builder, sample_manifest_with_files):
        """Test counting total files to be downloaded"""
        options = BuildOptions()
        files_to_download = package_builder._discover_files_to_download(
            sample_manifest_with_files, options
        )
        
        total_files = sum(len(files) for files in files_to_download.values())
        
        # Should count all files from all categories
        # manufacturing_files: 2, design_files: 1, making_instructions: 1
        # quality-instructions: 1 (duplicate from manufacturing_files categorization)
        # parts: 4 (source, export, auxiliary, image), software: 2, bom: 1, image: 1
        expected_total = 2 + 1 + 1 + 1 + 4 + 2 + 1 + 1  # = 13
        assert total_files == expected_total
    
    def test_file_discovery_with_empty_manifest(self, package_builder):
        """Test file discovery with minimal manifest"""
        minimal_manifest = OKHManifest(
            title="Minimal Project",
            version="1.0.0",
            license=License(hardware="CERN-OHL-S-2.0"),
            licensor=Person(name="Test Author"),
            documentation_language="en",
            function="Test function"
        )
        
        options = BuildOptions()
        files_to_download = package_builder._discover_files_to_download(
            minimal_manifest, options
        )
        
        # Should have empty lists for all categories
        for category, files in files_to_download.items():
            assert len(files) == 0
    
    def test_part_file_organization(self, package_builder, sample_manifest_with_files):
        """Test organization of part-specific files"""
        options = BuildOptions()
        files_to_download = package_builder._discover_files_to_download(
            sample_manifest_with_files, options
        )
        
        # Check that part files are properly organized
        assert "parts" in files_to_download
        part_files = files_to_download["parts"]
        
        # Should have files for the "Main Body" part
        main_body_files = [f for f in part_files if f.get("part_name") == "Main Body"]
        assert len(main_body_files) == 4  # source, export, auxiliary, image
        
        # Check filenames
        filenames = [f.get("filename") for f in main_body_files]
        assert "source_0" in filenames
        assert "export_0" in filenames
        assert "auxiliary_0" in filenames
        assert "part-image" in filenames
