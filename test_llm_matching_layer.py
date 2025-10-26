#!/usr/bin/env python3
"""
Test script for LLM Matching Layer.

This script tests the LLM matching layer with sample requirements and capabilities
to verify that it can properly analyze facility capabilities for crisis response scenarios.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.matching.llm_matcher import LLMMatcher
from src.core.matching.layers.base import MatchingLayer


async def test_llm_matching_layer():
    """Test the LLM matching layer with sample data."""
    
    print("🧪 Testing LLM Matching Layer")
    print("=" * 50)
    
    # Create LLM matching layer
    try:
        matcher = LLMMatcher(domain="manufacturing", preserve_context=True)
        print("✅ LLM Matching Layer created successfully")
    except Exception as e:
        print(f"❌ Failed to create LLM Matching Layer: {e}")
        return
    
    # Test data - crisis response scenario
    requirements = [
        "CNC machining with 0.1mm tolerance",
        "Stainless steel 316L components",
        "Mass production of 10,000 units"
    ]
    
    capabilities = [
        "Precision machining with manual mills",
        "Stainless steel 304 available",
        "Small batch production, 100 units max"
    ]
    
    print(f"\n📋 Test Requirements:")
    for i, req in enumerate(requirements, 1):
        print(f"  {i}. {req}")
    
    print(f"\n🏭 Test Capabilities:")
    for i, cap in enumerate(capabilities, 1):
        print(f"  {i}. {cap}")
    
    print(f"\n🔄 Running LLM Analysis...")
    
    try:
        # Run matching analysis
        results = await matcher.match(requirements, capabilities)
        
        print(f"\n📊 Analysis Results:")
        print("=" * 50)
        
        for i, result in enumerate(results, 1):
            req_idx = (i - 1) // len(capabilities)
            cap_idx = (i - 1) % len(capabilities)
            
            req = requirements[req_idx]
            cap = capabilities[cap_idx]
            
            print(f"\n🔍 Match {i}: '{req}' vs '{cap}'")
            print(f"   Decision: {'✅ MATCH' if result.matched else '❌ NO MATCH'}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Quality: {result.metadata.quality.value}")
            print(f"   Method: {result.metadata.method}")
            print(f"   Processing Time: {result.metadata.processing_time_ms:.1f}ms")
            
            if result.metadata.reasons:
                print(f"   Reasons:")
                for reason in result.metadata.reasons[:3]:  # Show first 3 reasons
                    print(f"     • {reason}")
            
            # Show LLM analysis details if available
            if hasattr(result.metadata, 'llm_analysis') and result.metadata.llm_analysis:
                analysis = result.metadata.llm_analysis
                if 'key_factors' in analysis:
                    print(f"   Key Factors: {', '.join(analysis['key_factors'][:2])}")
                if 'recommendations' in analysis:
                    print(f"   Recommendations: {', '.join(analysis['recommendations'][:2])}")
        
        # Show metrics
        metrics = matcher.get_metrics()
        if metrics:
            print(f"\n📈 Performance Metrics:")
            print(f"   Total Requirements: {metrics.total_requirements}")
            print(f"   Total Capabilities: {metrics.total_capabilities}")
            print(f"   Matches Found: {metrics.matches_found}")
            print(f"   Match Rate: {metrics.match_rate:.2%}")
            print(f"   Processing Time: {metrics.processing_time_ms:.1f}ms")
            print(f"   Success: {metrics.success}")
        
        # Show LLM service status
        service_status = matcher.get_service_status()
        print(f"\n🔧 LLM Service Status:")
        print(f"   Status: {service_status.get('status', 'Unknown')}")
        if 'providers' in service_status and service_status['providers']:
            print(f"   Available Providers: {', '.join(service_status['providers'])}")
        
        print(f"\n✅ LLM Matching Layer test completed successfully!")
        
    except Exception as e:
        print(f"❌ LLM matching failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            await matcher.shutdown()
            print("🧹 Cleanup completed")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")


async def test_simple_matching():
    """Test with simpler data to verify basic functionality."""
    
    print("\n🧪 Testing Simple LLM Matching")
    print("=" * 50)
    
    try:
        matcher = LLMMatcher(domain="manufacturing", preserve_context=True)
        
        # Simple test case
        requirements = ["3D printing"]
        capabilities = ["Additive manufacturing"]
        
        print(f"Testing: '{requirements[0]}' vs '{capabilities[0]}'")
        
        results = await matcher.match(requirements, capabilities)
        
        if results:
            result = results[0]
            print(f"Result: {'✅ MATCH' if result.matched else '❌ NO MATCH'}")
            print(f"Confidence: {result.confidence:.2f}")
            print(f"Quality: {result.metadata.quality.value}")
        else:
            print("❌ No results returned")
        
        await matcher.shutdown()
        
    except Exception as e:
        print(f"❌ Simple test failed: {e}")
        import traceback
        traceback.print_exc()


async def run_tests_with_timeout():
    """Run tests with timeout to prevent hanging."""
    try:
        print("🚀 Starting LLM Matching Layer Tests")
        print("=" * 60)
        
        # Check if we're in the right environment
        if not os.getenv('ANTHROPIC_API_KEY'):
            print("⚠️  Warning: ANTHROPIC_API_KEY not found in environment")
            print("   LLM matching will fail without a valid API key")
            print("   Set ANTHROPIC_API_KEY in your .env file or environment")
            print()
        
        # Run tests with timeout
        print("🧪 Running tests with 60-second timeout...")
        
        # Test 1: Full matching test
        try:
            await asyncio.wait_for(test_llm_matching_layer(), timeout=60.0)
        except asyncio.TimeoutError:
            print("⏰ Test 1 timed out after 60 seconds")
        except Exception as e:
            print(f"❌ Test 1 failed: {e}")
        
        # Test 2: Simple matching test
        try:
            await asyncio.wait_for(test_simple_matching(), timeout=30.0)
        except asyncio.TimeoutError:
            print("⏰ Test 2 timed out after 30 seconds")
        except Exception as e:
            print(f"❌ Test 2 failed: {e}")
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test runner failed: {e}")


if __name__ == "__main__":
    asyncio.run(run_tests_with_timeout())
