from typing import Dict, Any, List
from ...models.base.base_extractors import BaseExtractor
from ...models.base.base_types import NormalizedRequirements, NormalizedCapabilities

class CookingExtractor(BaseExtractor):
    """Extractor for cooking domain"""
    
    def _initial_parse_requirements(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Initial parsing of recipe data"""
        # For MVP, just pass through the content
        return content
    
    def _detailed_extract_requirements(self, parsed_data: Dict[str, Any]) -> NormalizedRequirements:
        """Extract recipe data to normalized requirements"""
        processed = {
            "ingredients": parsed_data.get("ingredients", []),
            "steps": parsed_data.get("instructions", []),
            "tools": parsed_data.get("equipment", []),
            "time": parsed_data.get("totalTime", "")
        }
        
        # Create normalized requirements
        result = NormalizedRequirements(content=processed, domain="cooking")
        
        return result
    
    def _initial_parse_capabilities(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Initial parsing of kitchen data"""
        # For MVP, just pass through the content
        return content
    
    def _detailed_extract_capabilities(self, parsed_data: Dict[str, Any]) -> NormalizedCapabilities:
        """Extract kitchen data to normalized capabilities"""
        processed = {
            "available_ingredients": parsed_data.get("ingredients", []),
            "available_tools": parsed_data.get("tools", []),
            "appliances": parsed_data.get("appliances", [])
        }
        
        # Create normalized capabilities
        result = NormalizedCapabilities(content=processed, domain="cooking")
        
        return result
    
    def _get_critical_fields(self, extraction_type: str) -> List[str]:
        """Define critical fields for cooking domain"""
        if extraction_type == "requirements":
            return ["ingredients", "steps"]
        elif extraction_type == "capabilities":
            return ["available_ingredients", "available_tools"]
        return []