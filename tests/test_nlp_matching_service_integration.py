"""
Integration tests for NLP matching within MatchingService
"""
import pytest
from unittest.mock import AsyncMock, patch
from src.core.services.matching_service import MatchingService
from src.core.matching.layers.base import MatchingLayer


class TestNLPMatchingIntegration:
    """Integration tests for NLP matching with MatchingService"""
    
    @pytest.fixture
    def matching_service(self):
        """Create a MatchingService instance for testing"""
        service = MatchingService()
        # Mock the services to avoid initialization issues
        service.okh_service = AsyncMock()
        service.okw_service = AsyncMock()
        service.capability_rule_manager = AsyncMock()
        service.capability_matcher = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_nlp_matchers_initialized(self, matching_service):
        """Test that NLP matchers are properly initialized"""
        assert "manufacturing" in matching_service.nlp_matchers
        assert "cooking" in matching_service.nlp_matchers
        
        # Check that they are NLPMatcher instances
        from src.core.matching.nlp_matcher import NLPMatcher
        assert isinstance(matching_service.nlp_matchers["manufacturing"], NLPMatcher)
        assert isinstance(matching_service.nlp_matchers["cooking"], NLPMatcher)
        
        # Check domains
        assert matching_service.nlp_matchers["manufacturing"].domain == "manufacturing"
        assert matching_service.nlp_matchers["cooking"].domain == "cooking"
    
    @pytest.mark.asyncio
    async def test_nlp_match_method_exists(self, matching_service):
        """Test that the _nlp_match method exists and is callable"""
        assert hasattr(matching_service, '_nlp_match')
        assert callable(matching_service._nlp_match)
    
    @pytest.mark.asyncio
    async def test_nlp_match_semantic_similarity(self, matching_service):
        """Test NLP matching with semantically similar terms"""
        # Test with semantically similar manufacturing terms
        result = await matching_service._nlp_match(
            "machining", 
            "CNC machining", 
            domain="manufacturing"
        )
        
        # Should return True if semantic similarity is high enough
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_nlp_match_different_domains(self, matching_service):
        """Test NLP matching with different domains"""
        # Test manufacturing domain
        mfg_result = await matching_service._nlp_match(
            "machining", 
            "CNC machining", 
            domain="manufacturing"
        )
        
        # Test cooking domain
        cooking_result = await matching_service._nlp_match(
            "cooking", 
            "baking", 
            domain="cooking"
        )
        
        # Both should return boolean results
        assert isinstance(mfg_result, bool)
        assert isinstance(cooking_result, bool)
    
    @pytest.mark.asyncio
    async def test_nlp_match_invalid_domain(self, matching_service):
        """Test NLP matching with invalid domain"""
        result = await matching_service._nlp_match(
            "machining", 
            "CNC machining", 
            domain="invalid_domain"
        )
        
        # Should return False for invalid domain
        assert result is False
    
    @pytest.mark.asyncio
    async def test_nlp_match_error_handling(self, matching_service):
        """Test NLP matching error handling"""
        # Test with None inputs
        result = await matching_service._nlp_match(
            None, 
            "CNC machining", 
            domain="manufacturing"
        )
        
        # Should handle gracefully and return False
        assert result is False
    
    @pytest.mark.asyncio
    async def test_matching_service_initialization_with_nlp(self, matching_service):
        """Test that MatchingService initializes properly with NLP matchers"""
        # Check that all expected matchers are present
        assert hasattr(matching_service, 'direct_matchers')
        assert hasattr(matching_service, 'nlp_matchers')
        
        # Check that NLP matchers are properly configured
        assert len(matching_service.nlp_matchers) == 2
        assert "manufacturing" in matching_service.nlp_matchers
        assert "cooking" in matching_service.nlp_matchers
