# src/core/domains/cooking/extractors.py
from typing import Dict, Any, List
from ...models.base_extractors import BaseExtractor
from ...models.base_types import NormalizedRequirements, NormalizedCapabilities

class CookingExtractor(BaseExtractor):
    """Extractor for cooking domain"""
    
    def _initial_parse_requirements(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Initial parsing of recipe data"""
        # Basic normalization and parsing
        return content
    
    def _detailed_extract_requirements(self, parsed_data: Dict[str, Any]) -> NormalizedRequirements:
        """Extract recipe data to normalized requirements"""
        processed = {
            "ingredients": parsed_data.get("ingredients", []),
            "steps": parsed_data.get("instructions", []),
            "tools": parsed_data.get("equipment", []),
            "time": parsed_data.get("totalTime", "")
        }
        
        # Set confidence scores for critical fields
        result = NormalizedRequirements(content=processed, domain="cooking")
        
        return result
    
    def _initial_parse_capabilities(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Initial parsing of kitchen data"""
        # Basic normalization and parsing
        return content
    
    def _detailed_extract_capabilities(self, parsed_data: Dict[str, Any]) -> NormalizedCapabilities:
        """Extract kitchen data to normalized capabilities"""
        processed = {
            "available_ingredients": parsed_data.get("ingredients", []),
            "available_tools": parsed_data.get("tools", []),
            "appliances": parsed_data.get("appliances", [])
        }
        
        # Set confidence scores for critical fields
        result = NormalizedCapabilities(content=processed, domain="cooking")
        
        return result
    
    def _get_critical_fields(self, extraction_type: str) -> List[str]:
        """Define critical fields for cooking domain"""
        if extraction_type == "requirements":
            return ["ingredients", "steps"]
        elif extraction_type == "capabilities":
            return ["available_ingredients", "available_tools"]
        return []