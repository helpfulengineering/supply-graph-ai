#!/usr/bin/env python3
"""
Direct Matching Layer Example

This example demonstrates the Direct Matching layer functionality
for both cooking and manufacturing domains.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.domains.cooking.direct_matcher import CookingDirectMatcher
from src.core.domains.manufacturing.direct_matcher import MfgDirectMatcher


def cooking_example():
    """Demonstrate cooking domain direct matching."""
    print("🍳 COOKING DOMAIN DIRECT MATCHING")
    print("=" * 40)
    
    matcher = CookingDirectMatcher()
    
    # Example 1: Basic ingredient matching
    print("\n1. Basic Ingredient Matching:")
    print("-" * 30)
    
    required_ingredients = ["flour", "sugar", "eggs"]
    available_ingredients = ["flour", "Flour", "sugar", "eggs", "salt", "flor"]
    
    for ingredient in required_ingredients:
        results = matcher.match(ingredient, available_ingredients)
        print(f"\nRequired: '{ingredient}'")
        
        for result in results:
            if result.matched:
                print(f"  ✓ Matches '{result.capability}' (confidence: {result.confidence:.2f})")
            elif result.confidence == 0.8:
                print(f"  ~ Near miss '{result.capability}' (confidence: {result.confidence:.2f})")
            else:
                print(f"  ✗ No match '{result.capability}' (confidence: {result.confidence:.2f})")
    
    # Example 2: Equipment matching
    print("\n\n2. Equipment Matching:")
    print("-" * 30)
    
    required_equipment = ["knife", "cutting board", "oven"]
    available_equipment = ["Knife", "cutting board", "Oven", "pan", "skillet"]
    
    results = matcher.match_equipment(required_equipment, available_equipment)
    
    for result in results:
        if result.matched:
            print(f"  ✓ {result.requirement} → {result.capability} (confidence: {result.confidence:.2f})")
        else:
            print(f"  ✗ {result.requirement} → {result.capability} (confidence: {result.confidence:.2f})")
    
    # Example 3: Complete recipe matching
    print("\n\n3. Complete Recipe Matching:")
    print("-" * 30)
    
    recipe_data = {
        "ingredients": ["flour", "sugar", "eggs", "butter"],
        "equipment": ["mixing bowl", "whisk", "oven"],
        "techniques": ["mix", "bake", "cool"]
    }
    
    kitchen_capabilities = {
        "available_ingredients": ["flour", "sugar", "eggs", "butter", "salt", "pepper"],
        "available_equipment": ["mixing bowl", "whisk", "oven", "pan", "knife"],
        "available_techniques": ["mix", "bake", "cool", "chop", "dice"]
    }
    
    results = matcher.match_recipe_requirements(recipe_data, kitchen_capabilities)
    
    for category, category_results in results.items():
        print(f"\n  {category.upper()}:")
        matched_count = sum(1 for r in category_results if r.matched)
        total_count = len(category_results)
        print(f"    Matched: {matched_count}/{total_count}")
        
        for result in category_results:
            if result.matched:
                print(f"      ✓ {result.requirement} → {result.capability} (confidence: {result.confidence:.2f})")


def manufacturing_example():
    """Demonstrate manufacturing domain direct matching."""
    print("\n\n🏭 MANUFACTURING DOMAIN DIRECT MATCHING")
    print("=" * 40)
    
    matcher = MfgDirectMatcher()
    
    # Example 1: Material matching
    print("\n1. Material Matching:")
    print("-" * 30)
    
    required_materials = ["steel", "aluminum", "copper"]
    available_materials = ["steel", "Steel", "aluminum", "copper", "brass", "stel"]
    
    for material in required_materials:
        results = matcher.match(material, available_materials)
        print(f"\nRequired: '{material}'")
        
        for result in results:
            if result.matched:
                print(f"  ✓ Matches '{result.capability}' (confidence: {result.confidence:.2f})")
            elif result.confidence == 0.8:
                print(f"  ~ Near miss '{result.capability}' (confidence: {result.confidence:.2f})")
            else:
                print(f"  ✗ No match '{result.capability}' (confidence: {result.confidence:.2f})")
    
    # Example 2: Tool matching
    print("\n\n2. Tool Matching:")
    print("-" * 30)
    
    required_tools = ["drill", "mill", "lathe"]
    available_tools = ["Drill", "mill", "Lathe", "grinder", "sander"]
    
    results = matcher.match_tools(required_tools, available_tools)
    
    for result in results:
        if result.matched:
            print(f"  ✓ {result.requirement} → {result.capability} (confidence: {result.confidence:.2f})")
        else:
            print(f"  ✗ {result.requirement} → {result.capability} (confidence: {result.confidence:.2f})")
    
    # Example 3: Complete OKH requirements matching
    print("\n\n3. Complete OKH Requirements Matching:")
    print("-" * 30)
    
    okh_data = {
        "materials": ["steel", "aluminum"],
        "components": ["bolt", "screw"],
        "tools": ["drill", "mill"],
        "processes": ["machining", "turning"]
    }
    
    okw_capabilities = {
        "available_materials": ["steel", "aluminum", "copper"],
        "available_components": ["bolt", "screw", "nut"],
        "available_tools": ["drill", "mill", "lathe"],
        "available_processes": ["machining", "turning", "milling"]
    }
    
    results = matcher.match_okh_requirements(okh_data, okw_capabilities)
    
    for category, category_results in results.items():
        print(f"\n  {category.upper()}:")
        matched_count = sum(1 for r in category_results if r.matched)
        total_count = len(category_results)
        print(f"    Matched: {matched_count}/{total_count}")
        
        for result in category_results:
            if result.matched:
                print(f"      ✓ {result.requirement} → {result.capability} (confidence: {result.confidence:.2f})")


def metadata_example():
    """Demonstrate detailed metadata tracking."""
    print("\n\n📊 METADATA TRACKING EXAMPLE")
    print("=" * 40)
    
    matcher = CookingDirectMatcher()
    results = matcher.match("flour", ["Flour", "flor", "sugar"])
    
    print("\nDetailed metadata for each match attempt:")
    print("-" * 40)
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Requirement: '{result.requirement}' vs Capability: '{result.capability}'")
        print(f"   Matched: {result.matched}")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Quality: {result.metadata.quality.value}")
        print(f"   Case difference: {result.metadata.case_difference}")
        print(f"   Whitespace difference: {result.metadata.whitespace_difference}")
        print(f"   Character difference: {result.metadata.character_difference}")
        print(f"   Processing time: {result.metadata.processing_time_ms:.2f}ms")
        print(f"   Reasons: {', '.join(result.metadata.reasons)}")
        print(f"   Timestamp: {result.metadata.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")


def confidence_scoring_example():
    """Demonstrate confidence scoring system."""
    print("\n\n🎯 CONFIDENCE SCORING SYSTEM")
    print("=" * 40)
    
    matcher = CookingDirectMatcher()
    
    test_cases = [
        ("flour", "flour", "Perfect match (identical)"),
        ("flour", "Flour", "Case difference"),
        ("flour", " flour ", "Whitespace difference"),
        ("flour", "Flour ", "Case and whitespace difference"),
        ("flour", "flor", "Near miss (1 character difference)"),
        ("flour", "flo", "Near miss (2 character differences)"),
        ("flour", "sugar", "No match (completely different)")
    ]
    
    print("\nConfidence scoring examples:")
    print("-" * 30)
    
    for requirement, capability, description in test_cases:
        results = matcher.match(requirement, [capability])
        result = results[0]
        
        print(f"{description}:")
        print(f"  '{requirement}' vs '{capability}'")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Quality: {result.metadata.quality.value}")
        print(f"  Matched: {result.matched}")
        print()


def main():
    """Run all examples."""
    print("🔍 DIRECT MATCHING LAYER EXAMPLES")
    print("=" * 50)
    print("This example demonstrates the Direct Matching layer")
    print("for the Open Matching Engine (OME).")
    
    try:
        cooking_example()
        manufacturing_example()
        metadata_example()
        confidence_scoring_example()
        
        print("\n" + "=" * 50)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("The Direct Matching Layer is working correctly.")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ EXAMPLE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
