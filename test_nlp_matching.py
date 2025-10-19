#!/usr/bin/env python3
"""
Test script for NLP matching layer with real data
"""
import asyncio
import json
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.matching.nlp_matcher import NLPMatcher
from src.core.services.matching_service import MatchingService


async def test_nlp_matching_standalone():
    """Test NLP matching layer in isolation"""
    print("=== Testing NLP Matching Layer (Standalone) ===")
    
    # Create NLP matcher
    matcher = NLPMatcher(domain="manufacturing", similarity_threshold=0.7)
    
    # Test cases with semantic similarity
    test_cases = [
        ("machining", "CNC machining"),
        ("3D printing", "additive manufacturing"),
        ("surface treatment", "surface finishing"),
        ("laser cutting", "laser engraving"),
        ("assembly", "product assembly"),
        ("welding", "metal joining"),
        ("milling", "material removal"),
        ("turning", "lathe work")
    ]
    
    print(f"Testing {len(test_cases)} semantic similarity cases:")
    for req, cap in test_cases:
        similarity = await matcher.calculate_semantic_similarity(req, cap)
        print(f"  '{req}' vs '{cap}': {similarity:.3f}")
    
    # Test full matching
    print("\nTesting full matching:")
    requirements = ["machining", "3D printing", "surface finishing"]
    capabilities = ["CNC machining", "additive manufacturing", "surface treatment"]
    
    results = await matcher.match(requirements, capabilities)
    
    print(f"Found {len(results)} matches:")
    for result in results:
        print(f"  {result.requirement} -> {result.capability}: "
              f"matched={result.matched}, confidence={result.confidence:.3f}")
    
    # Cleanup
    matcher.cleanup()
    print("NLP matcher cleanup completed")


async def test_matching_service_integration():
    """Test NLP matching through MatchingService"""
    print("\n=== Testing MatchingService Integration ===")
    
    # Create matching service
    service = MatchingService()
    
    # Test the NLP matching method directly
    test_cases = [
        ("machining", "CNC machining", "manufacturing"),
        ("cooking", "baking", "cooking"),
        ("3D printing", "additive manufacturing", "manufacturing")
    ]
    
    print("Testing NLP matching through MatchingService:")
    for req, cap, domain in test_cases:
        result = await service._nlp_match(req, cap, domain)
        print(f"  '{req}' vs '{cap}' ({domain}): {result}")
    
    print("MatchingService integration test completed")


async def test_with_real_manifest():
    """Test with a real OKH manifest"""
    print("\n=== Testing with Real OKH Manifest ===")
    
    manifest_path = Path("test_nlp_manifest.json")
    if not manifest_path.exists():
        print("Test manifest not found, skipping real manifest test")
        return
    
    # Load manifest
    with open(manifest_path) as f:
        manifest_data = json.load(f)
    
    print(f"Loaded manifest: {manifest_data['title']}")
    
    # Extract process requirements
    processes = manifest_data.get("manufacturing_specs", {}).get("process_requirements", [])
    process_names = [p["process_name"] for p in processes]
    
    print(f"Process requirements: {process_names}")
    
    # Test NLP matching with these processes
    matcher = NLPMatcher(domain="manufacturing")
    
    # Test against some common manufacturing capabilities
    test_capabilities = [
        "CNC machining",
        "3D printing", 
        "laser cutting",
        "surface treatment",
        "assembly",
        "welding"
    ]
    
    print("\nTesting semantic matching:")
    for req in process_names:
        print(f"\nTesting '{req}':")
        for cap in test_capabilities:
            similarity = await matcher.calculate_semantic_similarity(req, cap)
            if similarity > 0.5:  # Only show relevant matches
                print(f"  vs '{cap}': {similarity:.3f}")
    
    matcher.cleanup()
    print("Real manifest test completed")


async def main():
    """Run all tests"""
    print("NLP Matching Layer - Real Data Testing")
    print("=" * 50)
    
    try:
        await test_nlp_matching_standalone()
        await test_matching_service_integration()
        await test_with_real_manifest()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
