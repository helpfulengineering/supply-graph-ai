#!/usr/bin/env python3
"""
Test script to match recipes with kitchens using the matching service.

This script tests that we can match recipes to kitchens that are stored in storage.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.services.matching_service import MatchingService
from src.core.services.storage_service import StorageService
from src.core.services.domain_service import DomainDetector
from src.core.registry.domain_registry import DomainRegistry
from src.core.domains.cooking.extractors import CookingExtractor
from src.core.domains.cooking.matchers import CookingMatcher
from src.core.models.base.base_types import NormalizedRequirements, NormalizedCapabilities


async def test_recipe_kitchen_matching(recipe_file: str):
    """Test matching a recipe against kitchens in storage"""
    print(f"Testing recipe matching: {recipe_file}")
    
    # Load recipe
    with open(recipe_file, 'r') as f:
        recipe_data = json.load(f)
    
    print(f"Recipe: {recipe_data.get('name', 'Unknown')}")
    print(f"  Ingredients: {recipe_data.get('ingredients', [])}")
    print(f"  Equipment: {recipe_data.get('equipment', [])}")
    print(f"  Appliances: {recipe_data.get('appliances', [])}")
    
    # Initialize services
    storage_service = await StorageService.get_instance()
    from src.config.storage_config import get_default_storage_config
    await storage_service.configure(get_default_storage_config())
    
    # Load kitchens from storage
    kitchens = []
    async for obj in storage_service.manager.list_objects():
        try:
            # Only process kitchen files
            if 'kitchen' not in obj["key"].lower():
                continue
            
            data = await storage_service.manager.get_object(obj["key"])
            content = data.decode('utf-8')
            kitchen_data = json.loads(content)
            kitchens.append(kitchen_data)
            print(f"  Loaded kitchen: {kitchen_data.get('name', 'Unknown')}")
        except Exception as e:
            print(f"  Warning: Failed to load {obj['key']}: {e}")
            continue
    
    print(f"\nFound {len(kitchens)} kitchens in storage")
    
    if not kitchens:
        print("No kitchens found in storage. Please upload kitchen files first.")
        return
    
    # Use cooking domain extractor and matcher
    extractor = CookingExtractor()
    matcher = CookingMatcher()
    
    # Extract requirements from recipe
    extraction_result = extractor.extract_requirements(recipe_data)
    requirements = extraction_result.data if extraction_result.data else None
    
    if not requirements:
        print("Failed to extract requirements from recipe")
        return []
    
    print(f"\nExtracted requirements:")
    print(f"  Ingredients: {requirements.content.get('ingredients', [])}")
    print(f"  Steps: {len(requirements.content.get('steps', []))} steps")
    print(f"  Tools: {requirements.content.get('tools', [])}")
    
    # Test matching against each kitchen
    matches = []
    for kitchen in kitchens:
        print(f"\nTesting against kitchen: {kitchen.get('name', 'Unknown')}")
        
        # Extract capabilities from kitchen
        capabilities_result = extractor.extract_capabilities(kitchen)
        capabilities = capabilities_result.data if capabilities_result.data else None
        
        if not capabilities:
            print(f"  Warning: Failed to extract capabilities from kitchen")
            continue
        
        print(f"  Available ingredients: {capabilities.content.get('available_ingredients', [])}")
        print(f"  Available tools: {capabilities.content.get('available_tools', [])}")
        print(f"  Appliances: {capabilities.content.get('appliances', [])}")
        
        # Check if kitchen has required equipment/appliances
        recipe_equipment = set(requirements.content.get('tools', []))
        recipe_appliances = set(requirements.content.get('tools', []))  # Note: equipment field contains appliances
        kitchen_tools = set(capabilities.content.get('available_tools', []))
        kitchen_appliances = set(capabilities.content.get('appliances', []))
        
        # Check ingredient overlap
        recipe_ingredients = set(requirements.content.get('ingredients', []))
        kitchen_ingredients = set(capabilities.content.get('available_ingredients', []))
        ingredient_overlap = recipe_ingredients & kitchen_ingredients
        
        # Check equipment/appliance match
        equipment_match = recipe_equipment.issubset(kitchen_tools)
        appliance_match = recipe_appliances.issubset(kitchen_appliances)
        
        # Calculate match score
        ingredient_score = len(ingredient_overlap) / len(recipe_ingredients) if recipe_ingredients else 0
        equipment_score = 1.0 if equipment_match else 0.5  # Partial score if missing some
        appliance_score = 1.0 if appliance_match else 0.5
        
        overall_score = (ingredient_score * 0.4 + equipment_score * 0.3 + appliance_score * 0.3)
        
        print(f"  Match score: {overall_score:.2f}")
        print(f"    - Ingredient overlap: {len(ingredient_overlap)}/{len(recipe_ingredients)} ({ingredient_score:.2f})")
        print(f"    - Equipment match: {equipment_match} ({equipment_score:.2f})")
        print(f"    - Appliance match: {appliance_match} ({appliance_score:.2f})")
        
        if overall_score > 0.5:  # Threshold for valid match
            matches.append({
                "kitchen": kitchen.get('name'),
                "score": overall_score,
                "ingredient_overlap": list(ingredient_overlap),
                "equipment_match": equipment_match,
                "appliance_match": appliance_match
            })
    
    print(f"\n{'='*60}")
    print(f"MATCHING RESULTS")
    print(f"{'='*60}")
    print(f"Recipe: {recipe_data.get('name', 'Unknown')}")
    print(f"Total kitchens tested: {len(kitchens)}")
    print(f"Valid matches found: {len(matches)}")
    
    if matches:
        print(f"\nMatching kitchens:")
        for match in sorted(matches, key=lambda x: x['score'], reverse=True):
            print(f"  - {match['kitchen']}: {match['score']:.2f} (ingredients: {len(match['ingredient_overlap'])})")
    else:
        print(f"\nNo valid matches found.")
    
    await storage_service.cleanup()
    return matches


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test recipe-to-kitchen matching")
    parser.add_argument("recipe_file", help="Recipe JSON file to match")
    
    args = parser.parse_args()
    
    matches = await test_recipe_kitchen_matching(args.recipe_file)
    
    if matches:
        print(f"\n✅ SUCCESS: Found {len(matches)} valid match(es)")
        return 0
    else:
        print(f"\n❌ FAILURE: No valid matches found")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

