"""
Unit tests for LayerConfig file categorization configuration.

Tests the file categorization configuration in LayerConfig.
Following TDD approach: write tests first, then implement.
"""

import pytest
from src.core.generation.models import LayerConfig, AnalysisDepth


class TestLayerConfigFileCategorization:
    """Test the file categorization configuration in LayerConfig."""
    
    def test_file_categorization_config_exists(self):
        """Test that file_categorization_config field exists."""
        config = LayerConfig()
        assert hasattr(config, 'file_categorization_config')
        assert isinstance(config.file_categorization_config, dict)
    
    def test_file_categorization_config_defaults(self):
        """Test that file_categorization_config has proper defaults."""
        config = LayerConfig()
        
        assert config.file_categorization_config["enable_llm_categorization"] is True
        assert config.file_categorization_config["analysis_depth"] == "shallow"
        assert config.file_categorization_config["fallback_to_heuristics"] is True
        assert config.file_categorization_config["batch_size"] == 10
        assert config.file_categorization_config["max_files_per_request"] == 50
        assert config.file_categorization_config["min_confidence_for_llm"] == 0.5
        assert config.file_categorization_config["enable_caching"] is True
    
    def test_file_categorization_config_custom(self):
        """Test that file_categorization_config can be customized."""
        custom_config = {
            "enable_llm_categorization": False,
            "analysis_depth": "deep",
            "batch_size": 20,
            "min_confidence_for_llm": 0.7
        }
        
        config = LayerConfig(file_categorization_config=custom_config)
        
        assert config.file_categorization_config["enable_llm_categorization"] is False
        assert config.file_categorization_config["analysis_depth"] == "deep"
        assert config.file_categorization_config["batch_size"] == 20
        assert config.file_categorization_config["min_confidence_for_llm"] == 0.7
        
        # Defaults should still be present for non-overridden values
        assert config.file_categorization_config["fallback_to_heuristics"] is True
        assert config.file_categorization_config["max_files_per_request"] == 50
    
    def test_file_categorization_config_merge(self):
        """Test that custom config merges with defaults."""
        custom_config = {
            "analysis_depth": "medium"
        }
        
        config = LayerConfig(file_categorization_config=custom_config)
        
        # Custom value should override default
        assert config.file_categorization_config["analysis_depth"] == "medium"
        
        # Other defaults should still be present
        assert config.file_categorization_config["enable_llm_categorization"] is True
        assert config.file_categorization_config["batch_size"] == 10

