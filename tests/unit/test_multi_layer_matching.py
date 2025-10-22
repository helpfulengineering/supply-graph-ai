"""
Test suite for multi-layered matching architecture in MatchingService.

This test suite validates the restoration of the multi-layered matching approach
as described in the matching.md documentation. It tests each layer independently
and the integration between layers.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from src.core.services.matching_service import MatchingService
from src.core.models.okh import OKHManifest
from src.core.models.okw import ManufacturingFacility, Equipment, Location, Address
from src.core.models.supply_trees import SupplyTree, SupplyTreeSolution


class TestMultiLayerMatching:
    """Test suite for multi-layered matching architecture"""
    
    @pytest.fixture
    def matching_service(self):
        """Create a MatchingService instance for testing"""
        service = MatchingService()
        # Mock the services to avoid dependency issues
        service.okh_service = Mock()
        service.okw_service = Mock()
        service._initialized = True
        return service
    
    @pytest.fixture
    def sample_requirements(self):
        """Sample requirements for testing"""
        return [
            {"process_name": "PCB assembly"},
            {"process_name": "3D printing"},
            {"process_name": "CNC machining"}
        ]
    
    @pytest.fixture
    def sample_capabilities(self):
        """Sample capabilities for testing"""
        return [
            {"process_name": "PCB assembly"},
            {"process_name": "3D printing"},
            {"process_name": "CNC machining"},
            {"process_name": "pcb assembly"},  # Case variation
            {"process_name": "3D Printing"},   # Case variation
            {"process_name": "cnc machining"}, # Case variation
            {"process_name": "PCB_assembly"},  # Underscore variation
            {"process_name": "3d-printing"},   # Hyphen variation
        ]
    
    @pytest.fixture
    def sample_manifest(self):
        """Sample OKH manifest for testing"""
        return OKHManifest(
            id="test-manifest-1",
            title="Test Device",
            version="1.0.0",
            license="MIT",
            licensor="Test Licensor",
            documentation_language="en",
            function="Test Device",
            manufacturing_processes=["PCB assembly", "3D printing"]
        )
    
    @pytest.fixture
    def sample_facility(self):
        """Sample manufacturing facility for testing"""
        return ManufacturingFacility(
            id="test-facility-1",
            name="Test Manufacturing Facility",
            location=Location(
                address=Address(
                    street="123 Test St",
                    city="Test City",
                    region="Test Region",
                    postal_code="12345",
                    country="Test Country"
                ),
                gps_coordinates="37.7749,-122.4194"
            ),
            equipment=[
                Equipment(
                    equipment_type="PCB Assembly Machine",
                    manufacturing_process="PCB assembly"
                ),
                Equipment(
                    equipment_type="3D Printer",
                    manufacturing_process="3D printing"
                )
            ]
        )

    # Layer 1: Direct Matching Tests
    @pytest.mark.asyncio
    async def test_direct_match_exact_match(self, matching_service, sample_requirements, sample_capabilities):
        """Test Layer 1: Direct matching with exact matches"""
        # Test exact match
        result = await matching_service._direct_match("PCB assembly", "PCB assembly", "manufacturing")
        assert result is True
        
        # Test case-insensitive match
        result = await matching_service._direct_match("PCB assembly", "pcb assembly", "manufacturing")
        assert result is True
        
        # Test with Wikipedia URL
        result = await matching_service._direct_match(
            "https://en.wikipedia.org/wiki/PCB_assembly", 
            "PCB assembly", 
            "manufacturing"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_direct_match_no_match(self, matching_service):
        """Test Layer 1: Direct matching with no matches"""
        result = await matching_service._direct_match("PCB assembly", "welding", "manufacturing")
        assert result is False

    @pytest.mark.asyncio
    async def test_direct_match_domain_specific(self, matching_service):
        """Test Layer 1: Direct matching with domain-specific matchers"""
        # Test with manufacturing domain
        result = await matching_service._direct_match("CNC machining", "CNC machining", "manufacturing")
        assert result is True
        
        # Test with cooking domain
        result = await matching_service._direct_match("baking", "baking", "cooking")
        assert result is True

    # Layer 2: Heuristic Matching Tests
    @pytest.mark.asyncio
    async def test_heuristic_match_with_rules(self, matching_service, sample_requirements, sample_capabilities):
        """Test Layer 2: Heuristic matching with capability rules"""
        # Mock the capability matcher
        mock_result = Mock()
        mock_result.matched = True
        mock_result.confidence = 0.8
        mock_result.rule_used = Mock()
        mock_result.rule_used.id = "test-rule-1"
        mock_result.domain = "manufacturing"
        
        matching_service.capability_matcher = AsyncMock()
        matching_service.capability_matcher.match_requirements_to_capabilities.return_value = [mock_result]
        
        result = await matching_service._heuristic_match("PCB assembly", "electronics assembly", "manufacturing")
        assert result is True

    @pytest.mark.asyncio
    async def test_heuristic_match_no_rules(self, matching_service):
        """Test Layer 2: Heuristic matching when no rules match"""
        # Mock the capability matcher to return no matches
        matching_service.capability_matcher = AsyncMock()
        matching_service.capability_matcher.match_requirements_to_capabilities.return_value = []
        
        result = await matching_service._heuristic_match("PCB assembly", "welding", "manufacturing")
        assert result is False

    @pytest.mark.asyncio
    async def test_heuristic_match_low_confidence(self, matching_service):
        """Test Layer 2: Heuristic matching with low confidence"""
        # Mock the capability matcher to return low confidence
        mock_result = Mock()
        mock_result.matched = True
        mock_result.confidence = 0.5  # Below threshold
        mock_result.rule_used = Mock()
        mock_result.rule_used.id = "test-rule-1"
        mock_result.domain = "manufacturing"
        
        matching_service.capability_matcher = AsyncMock()
        matching_service.capability_matcher.match_requirements_to_capabilities.return_value = [mock_result]
        
        result = await matching_service._heuristic_match("PCB assembly", "electronics assembly", "manufacturing")
        assert result is False

    # Layer 3: NLP Matching Tests
    @pytest.mark.asyncio
    async def test_nlp_match_semantic_similarity(self, matching_service):
        """Test Layer 3: NLP matching with semantic similarity"""
        # Mock the NLP matcher
        mock_result = Mock()
        mock_result.matched = True
        mock_result.confidence = 0.8
        mock_result.metadata = Mock()
        mock_result.metadata.semantic_similarity = 0.85
        
        matching_service.nlp_matchers = {
            "manufacturing": AsyncMock()
        }
        matching_service.nlp_matchers["manufacturing"].match.return_value = [mock_result]
        
        result = await matching_service._nlp_match("PCB assembly", "printed circuit board assembly", "manufacturing")
        assert result is True

    @pytest.mark.asyncio
    async def test_nlp_match_no_semantic_similarity(self, matching_service):
        """Test Layer 3: NLP matching with no semantic similarity"""
        # Mock the NLP matcher to return no matches
        matching_service.nlp_matchers = {
            "manufacturing": AsyncMock()
        }
        matching_service.nlp_matchers["manufacturing"].match.return_value = []
        
        result = await matching_service._nlp_match("PCB assembly", "welding", "manufacturing")
        assert result is False

    @pytest.mark.asyncio
    async def test_nlp_match_unsupported_domain(self, matching_service):
        """Test Layer 3: NLP matching with unsupported domain"""
        result = await matching_service._nlp_match("PCB assembly", "PCB assembly", "unsupported_domain")
        assert result is False

    # Integration Tests: Multi-layer Matching
    @pytest.mark.asyncio
    async def test_can_satisfy_requirements_direct_match(self, matching_service, sample_requirements, sample_capabilities):
        """Test that _can_satisfy_requirements uses direct matching first"""
        # Mock the direct match to return True
        with patch.object(matching_service, '_direct_match', return_value=True) as mock_direct:
            result = await matching_service._can_satisfy_requirements(sample_requirements, sample_capabilities)
            assert result is True
            # Verify direct match was called
            assert mock_direct.called

    @pytest.mark.asyncio
    async def test_can_satisfy_requirements_heuristic_fallback(self, matching_service, sample_requirements, sample_capabilities):
        """Test that _can_satisfy_requirements falls back to heuristic matching"""
        # Mock direct match to return False, heuristic to return True
        with patch.object(matching_service, '_direct_match', return_value=False) as mock_direct, \
             patch.object(matching_service, '_heuristic_match', return_value=True) as mock_heuristic:
            
            result = await matching_service._can_satisfy_requirements(sample_requirements, sample_capabilities)
            assert result is True
            # Verify both methods were called
            assert mock_direct.called
            assert mock_heuristic.called

    @pytest.mark.asyncio
    async def test_can_satisfy_requirements_nlp_fallback(self, matching_service, sample_requirements, sample_capabilities):
        """Test that _can_satisfy_requirements falls back to NLP matching"""
        # Mock direct and heuristic to return False, NLP to return True
        with patch.object(matching_service, '_direct_match', return_value=False) as mock_direct, \
             patch.object(matching_service, '_heuristic_match', return_value=False) as mock_heuristic, \
             patch.object(matching_service, '_nlp_match', return_value=True) as mock_nlp:
            
            result = await matching_service._can_satisfy_requirements(sample_requirements, sample_capabilities)
            assert result is True
            # Verify all methods were called
            assert mock_direct.called
            assert mock_heuristic.called
            assert mock_nlp.called

    @pytest.mark.asyncio
    async def test_can_satisfy_requirements_no_match(self, matching_service, sample_requirements, sample_capabilities):
        """Test that _can_satisfy_requirements returns False when no layer matches"""
        # Mock all layers to return False
        with patch.object(matching_service, '_direct_match', return_value=False) as mock_direct, \
             patch.object(matching_service, '_heuristic_match', return_value=False) as mock_heuristic, \
             patch.object(matching_service, '_nlp_match', return_value=False) as mock_nlp:
            
            result = await matching_service._can_satisfy_requirements(sample_requirements, sample_capabilities)
            assert result is False
            # Verify all methods were called
            assert mock_direct.called
            assert mock_heuristic.called
            assert mock_nlp.called

    # Process Name Normalization Tests
    def test_normalize_process_name_wikipedia_url(self, matching_service):
        """Test process name normalization with Wikipedia URLs"""
        result = matching_service._normalize_process_name("https://en.wikipedia.org/wiki/PCB_assembly")
        assert result == "pcb assembly"
        
        result = matching_service._normalize_process_name("https://en.wikipedia.org/wiki/3D_printing")
        assert result == "3d printing"

    def test_normalize_process_name_case_whitespace(self, matching_service):
        """Test process name normalization with case and whitespace"""
        result = matching_service._normalize_process_name("  PCB   Assembly  ")
        assert result == "pcb assembly"
        
        result = matching_service._normalize_process_name("3D-Printing")
        assert result == "3d printing"

    def test_normalize_process_name_special_characters(self, matching_service):
        """Test process name normalization with special characters"""
        result = matching_service._normalize_process_name("PCB_Assembly")
        assert result == "pcb assembly"
        
        result = matching_service._normalize_process_name("3D-Printing")
        assert result == "3d printing"

    # Process Similarity Calculation Tests
    def test_calculate_process_similarity_exact_match(self, matching_service):
        """Test process similarity calculation with exact matches"""
        similarity = matching_service._calculate_process_similarity("PCB assembly", "PCB assembly")
        assert similarity == 1.0

    def test_calculate_process_similarity_substring_match(self, matching_service):
        """Test process similarity calculation with substring matches"""
        similarity = matching_service._calculate_process_similarity("PCB", "PCB assembly")
        assert similarity == 0.8

    def test_calculate_process_similarity_manufacturing_keywords(self, matching_service):
        """Test process similarity calculation with manufacturing keywords"""
        similarity = matching_service._calculate_process_similarity("CNC machining", "CNC mill")
        assert similarity > 0.5  # Should have good similarity due to CNC keyword

    def test_calculate_process_similarity_abbreviations(self, matching_service):
        """Test process similarity calculation with abbreviations"""
        similarity = matching_service._calculate_process_similarity("3DP", "3D printing")
        assert similarity > 0.5  # Should have good similarity due to abbreviation matching

    def test_calculate_process_similarity_no_match(self, matching_service):
        """Test process similarity calculation with no match"""
        similarity = matching_service._calculate_process_similarity("PCB assembly", "welding")
        assert similarity < 0.3  # Should have low similarity

    # End-to-End Integration Tests
    @pytest.mark.asyncio
    async def test_find_matches_with_manifest_multi_layer(self, matching_service, sample_manifest, sample_facility):
        """Test end-to-end matching with multi-layer approach"""
        # Mock the domain services
        mock_extractor = Mock()
        mock_extractor.extract_requirements.return_value = Mock(
            data=Mock(content={"process_requirements": [{"process_name": "PCB assembly"}]})
        )
        mock_extractor.extract_capabilities.return_value = Mock(
            data=Mock(content={"capabilities": [{"process_name": "PCB assembly"}]})
        )
        
        with patch('src.core.services.matching_service.DomainRegistry') as mock_registry:
            mock_registry.get_domain_services.return_value = Mock(extractor=mock_extractor)
            
            # Mock the multi-layer matching methods
            with patch.object(matching_service, '_can_satisfy_requirements', return_value=True) as mock_can_satisfy:
                solutions = await matching_service.find_matches_with_manifest(
                    okh_manifest=sample_manifest,
                    facilities=[sample_facility]
                )
                
                assert len(solutions) == 1
                assert isinstance(solutions, set)
                solution = list(solutions)[0]
                assert isinstance(solution, SupplyTreeSolution)
                assert solution.tree.facility_id == sample_facility.id
                assert mock_can_satisfy.called

    @pytest.mark.asyncio
    async def test_generate_supply_tree_with_multi_layer_confidence(self, matching_service, sample_manifest, sample_facility):
        """Test supply tree generation with multi-layer confidence scoring"""
        # Mock the multi-layer matching to return different confidence levels
        with patch.object(matching_service, '_direct_match', return_value=True) as mock_direct:
            tree = await matching_service._generate_supply_tree(
                manifest=sample_manifest,
                facility=sample_facility,
                domain="manufacturing"
            )
            
            assert isinstance(tree, SupplyTree)
            assert tree.facility_id == sample_facility.id
            assert tree.confidence_score > 0.0
            assert tree.match_type in ["direct", "heuristic", "partial", "unknown"]

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_direct_match_error_handling(self, matching_service):
        """Test error handling in direct matching"""
        # Test with invalid domain
        result = await matching_service._direct_match("PCB assembly", "PCB assembly", "invalid_domain")
        # Should fall back to simple matching
        assert result is True

    @pytest.mark.asyncio
    async def test_heuristic_match_error_handling(self, matching_service):
        """Test error handling in heuristic matching"""
        # Test with uninitialized capability matcher
        matching_service.capability_matcher = None
        result = await matching_service._heuristic_match("PCB assembly", "PCB assembly", "manufacturing")
        assert result is False

    @pytest.mark.asyncio
    async def test_nlp_match_error_handling(self, matching_service):
        """Test error handling in NLP matching"""
        # Test with exception in NLP matcher
        matching_service.nlp_matchers = {
            "manufacturing": AsyncMock(side_effect=Exception("NLP error"))
        }
        result = await matching_service._nlp_match("PCB assembly", "PCB assembly", "manufacturing")
        assert result is False

    # Performance Tests
    @pytest.mark.asyncio
    async def test_multi_layer_performance(self, matching_service, sample_requirements, sample_capabilities):
        """Test that multi-layer matching doesn't significantly impact performance"""
        import time
        
        start_time = time.time()
        result = await matching_service._can_satisfy_requirements(sample_requirements, sample_capabilities)
        end_time = time.time()
        
        # Should complete within reasonable time (less than 1 second)
        assert (end_time - start_time) < 1.0
        assert isinstance(result, bool)
