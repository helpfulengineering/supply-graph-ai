"""
Unit tests for AnalysisDepth enum.

Tests the configurable content analysis depth levels for file categorization.
Following TDD approach: write tests first, then implement.
"""

import pytest
from src.core.generation.models import AnalysisDepth


class TestAnalysisDepthEnum:
    """Test the AnalysisDepth enum."""
    
    def test_enum_exists(self):
        """Test that AnalysisDepth enum exists."""
        assert AnalysisDepth is not None
    
    def test_shallow_exists(self):
        """Test that SHALLOW enum member exists."""
        assert AnalysisDepth.SHALLOW is not None
        assert AnalysisDepth.SHALLOW.value == "shallow"
    
    def test_medium_exists(self):
        """Test that MEDIUM enum member exists."""
        assert AnalysisDepth.MEDIUM is not None
        assert AnalysisDepth.MEDIUM.value == "medium"
    
    def test_deep_exists(self):
        """Test that DEEP enum member exists."""
        assert AnalysisDepth.DEEP is not None
        assert AnalysisDepth.DEEP.value == "deep"
    
    def test_all_members_present(self):
        """Test that all expected enum members are present."""
        expected_members = {"SHALLOW", "MEDIUM", "DEEP"}
        actual_members = {member.name for member in AnalysisDepth}
        assert actual_members == expected_members
    
    def test_enum_from_string(self):
        """Test that enum can be created from string values."""
        assert AnalysisDepth("shallow") == AnalysisDepth.SHALLOW
        assert AnalysisDepth("medium") == AnalysisDepth.MEDIUM
        assert AnalysisDepth("deep") == AnalysisDepth.DEEP
    
    def test_enum_comparison(self):
        """Test that enum members can be compared."""
        assert AnalysisDepth.SHALLOW != AnalysisDepth.MEDIUM
        assert AnalysisDepth.MEDIUM != AnalysisDepth.DEEP
        assert AnalysisDepth.SHALLOW == AnalysisDepth.SHALLOW
    
    def test_enum_string_representation(self):
        """Test that enum has proper string representation."""
        assert str(AnalysisDepth.SHALLOW) == "AnalysisDepth.SHALLOW"
        assert repr(AnalysisDepth.SHALLOW) == "<AnalysisDepth.SHALLOW: 'shallow'>"

