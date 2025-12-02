from src.core.domains.manufacturing.okh_extractor import OKHExtractor
from src.core.domains.manufacturing.okh_matcher import OKHMatcher
from src.core.domains.manufacturing.okh_orchestrator import OKHOrchestrator
from src.core.domains.manufacturing.okh_validator import OKHValidator
from src.core.models.okh import OKHManifest


class OKHFactory:
    """Factory for creating and managing OKH components"""

    @staticmethod
    def create_extractor():
        """Create an OKH extractor instance"""
        return OKHExtractor()

    @staticmethod
    def create_matcher():
        """Create an OKH matcher instance"""
        return OKHMatcher()

    @staticmethod
    def create_validator():
        """Create an OKH validator instance"""
        return OKHValidator()

    @staticmethod
    def create_orchestrator(config_path=None):
        """Create an OKH orchestrator instance"""
        return OKHOrchestrator(config_path=config_path)

    @staticmethod
    def create_from_toml(file_path):
        """Create an OKH manifest from a TOML file"""
        return OKHManifest.from_toml(file_path)

    @staticmethod
    def create_from_dict(data):
        """Create an OKH manifest from a dictionary"""
        return OKHManifest.from_dict(data)

    @staticmethod
    def convert_to_normalized_requirements(okh_manifest):
        """Convert OKH manifest to normalized requirements"""
        extractor = OKHExtractor()
        return extractor.extract_requirements(okh_manifest.to_dict()).data
