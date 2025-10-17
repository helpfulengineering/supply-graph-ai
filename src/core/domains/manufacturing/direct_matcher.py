"""
Manufacturing Domain Direct Matcher

This module implements the MfgDirectMatcher for the manufacturing domain,
providing specialized direct matching for materials, components, and tools.
"""

import re
from typing import List, Dict, Any, Set
from ...matching.direct_matcher import DirectMatcher
from ...matching.layers.base import MatchingResult


class MfgDirectMatcher(DirectMatcher):
    """Direct matcher specialized for manufacturing domain with material/component/tool matching."""
    
    def __init__(self, near_miss_threshold: int = 2):
        """
        Initialize the manufacturing direct matcher.
        
        Args:
            near_miss_threshold: Maximum character differences to consider as near-miss
        """
        super().__init__(domain="manufacturing", near_miss_threshold=near_miss_threshold)
        
        # Manufacturing-specific confidence adjustments
        self._material_keywords = self._load_material_keywords()
        self._component_keywords = self._load_component_keywords()
        self._tool_keywords = self._load_tool_keywords()
        self._process_keywords = self._load_process_keywords()
        self._specification_keywords = self._load_specification_keywords()
    
    def _load_material_keywords(self) -> Set[str]:
        """Load common material keywords for confidence adjustments."""
        return {
            "steel", "aluminum", "copper", "brass", "bronze", "iron", "titanium",
            "stainless", "carbon", "alloy", "plastic", "polymer", "ceramic",
            "composite", "wood", "glass", "rubber", "fiber", "fabric", "leather",
            "paper", "cardboard", "foam", "foil", "sheet", "plate", "rod", "tube",
            "wire", "cable", "thread", "yarn", "filament", "powder", "granule",
            "pellet", "chip", "flake", "resin", "adhesive", "coating", "paint",
            "varnish", "lacquer", "primer", "sealant", "lubricant", "coolant"
        }
    
    def _load_component_keywords(self) -> Set[str]:
        """Load common component keywords for confidence adjustments."""
        return {
            "bolt", "screw", "nut", "washer", "rivet", "pin", "clip", "bracket",
            "mount", "bracket", "hinge", "latch", "handle", "knob", "button",
            "switch", "connector", "plug", "socket", "jack", "port", "terminal",
            "contact", "spring", "bearing", "gear", "pulley", "belt", "chain",
            "shaft", "coupling", "joint", "flange", "gasket", "seal", "o-ring",
            "valve", "pump", "motor", "actuator", "sensor", "transducer", "relay",
            "fuse", "circuit", "board", "chip", "module", "assembly", "subassembly"
        }
    
    def _load_tool_keywords(self) -> Set[str]:
        """Load common tool keywords for confidence adjustments."""
        return {
            "drill", "mill", "lathe", "grinder", "sander", "polisher", "cutter",
            "saw", "shear", "press", "punch", "die", "mold", "fixture", "jig",
            "clamp", "vise", "chuck", "collet", "mandrel", "reamer", "tap",
            "die", "reamer", "counterbore", "countersink", "end mill", "face mill",
            "ball mill", "slot mill", "keyway cutter", "broach", "hob", "gear cutter",
            "thread mill", "chamfer mill", "corner rounder", "engraver", "router",
            "plasma cutter", "laser cutter", "water jet", "edm", "wire edm"
        }
    
    def _load_process_keywords(self) -> Set[str]:
        """Load common manufacturing process keywords for confidence adjustments."""
        return {
            "machining", "turning", "milling", "drilling", "boring", "reaming",
            "tapping", "threading", "grinding", "honing", "lapping", "polishing",
            "buffing", "sanding", "cutting", "shearing", "punching", "stamping",
            "forming", "bending", "rolling", "drawing", "extruding", "forging",
            "casting", "molding", "injection", "compression", "transfer", "blow",
            "rotational", "thermoforming", "welding", "brazing", "soldering",
            "adhesive", "bonding", "assembly", "disassembly", "inspection", "testing",
            "quality", "control", "measurement", "calibration", "alignment"
        }
    
    def _load_specification_keywords(self) -> Set[str]:
        """Load common specification keywords for confidence adjustments."""
        return {
            "tolerance", "dimension", "specification", "standard", "grade", "class",
            "type", "size", "diameter", "length", "width", "height", "thickness",
            "radius", "angle", "surface", "finish", "roughness", "hardness",
            "strength", "tensile", "yield", "elastic", "modulus", "density",
            "conductivity", "thermal", "electrical", "magnetic", "corrosion",
            "resistance", "durability", "fatigue", "creep", "impact", "temperature",
            "pressure", "vacuum", "humidity", "environment", "atmosphere", "coating",
            "treatment", "annealing", "quenching", "tempering", "normalizing"
        }
    
    def get_domain_specific_confidence_adjustments(self, requirement: str, capability: str) -> float:
        """
        Get manufacturing-specific confidence adjustments based on domain knowledge.
        
        Args:
            requirement: The requirement string
            capability: The capability string
            
        Returns:
            Confidence adjustment factor (0.0 to 1.0)
        """
        # Start with base confidence
        adjustment = 1.0
        
        # Check for manufacturing-specific patterns that increase confidence
        req_lower = requirement.lower()
        cap_lower = capability.lower()
        
        # Material matching gets slight boost
        if self._contains_material_keywords(req_lower) and self._contains_material_keywords(cap_lower):
            adjustment += 0.05
        
        # Component matching gets slight boost
        if self._contains_component_keywords(req_lower) and self._contains_component_keywords(cap_lower):
            adjustment += 0.05
        
        # Tool matching gets slight boost
        if self._contains_tool_keywords(req_lower) and self._contains_tool_keywords(cap_lower):
            adjustment += 0.05
        
        # Process matching gets slight boost
        if self._contains_process_keywords(req_lower) and self._contains_process_keywords(cap_lower):
            adjustment += 0.05
        
        # Specification matching gets slight boost
        if self._contains_specification_keywords(req_lower) and self._contains_specification_keywords(cap_lower):
            adjustment += 0.03
        
        # Penalty for obvious mismatches (e.g., material vs tool)
        if (self._contains_material_keywords(req_lower) and self._contains_tool_keywords(cap_lower)) or \
           (self._contains_tool_keywords(req_lower) and self._contains_material_keywords(cap_lower)):
            adjustment -= 0.1
        
        # Ensure adjustment stays within bounds
        return max(0.0, min(1.0, adjustment))
    
    def _contains_material_keywords(self, text: str) -> bool:
        """Check if text contains material keywords."""
        return any(keyword in text for keyword in self._material_keywords)
    
    def _contains_component_keywords(self, text: str) -> bool:
        """Check if text contains component keywords."""
        return any(keyword in text for keyword in self._component_keywords)
    
    def _contains_tool_keywords(self, text: str) -> bool:
        """Check if text contains tool keywords."""
        return any(keyword in text for keyword in self._tool_keywords)
    
    def _contains_process_keywords(self, text: str) -> bool:
        """Check if text contains process keywords."""
        return any(keyword in text for keyword in self._process_keywords)
    
    def _contains_specification_keywords(self, text: str) -> bool:
        """Check if text contains specification keywords."""
        return any(keyword in text for keyword in self._specification_keywords)
    
    def match_materials(self, required_materials: List[str], available_materials: List[str]) -> List[MatchingResult]:
        """
        Match required materials against available materials.
        
        Args:
            required_materials: List of required material strings
            available_materials: List of available material strings
            
        Returns:
            List of MatchingResult objects for material matches
        """
        results = []
        for required in required_materials:
            material_results = self.match(required, available_materials)
            # Add material-specific metadata
            for result in material_results:
                result.metadata.reasons.append("Material matching")
                # Apply domain-specific confidence adjustment
                domain_adjustment = self.get_domain_specific_confidence_adjustments(
                    result.requirement, result.capability)
                result.confidence *= domain_adjustment
                result.metadata.confidence = result.confidence
            results.extend(material_results)
        return results
    
    def match_components(self, required_components: List[str], available_components: List[str]) -> List[MatchingResult]:
        """
        Match required components against available components.
        
        Args:
            required_components: List of required component strings
            available_components: List of available component strings
            
        Returns:
            List of MatchingResult objects for component matches
        """
        results = []
        for required in required_components:
            component_results = self.match(required, available_components)
            # Add component-specific metadata
            for result in component_results:
                result.metadata.reasons.append("Component matching")
                # Apply domain-specific confidence adjustment
                domain_adjustment = self.get_domain_specific_confidence_adjustments(
                    result.requirement, result.capability)
                result.confidence *= domain_adjustment
                result.metadata.confidence = result.confidence
            results.extend(component_results)
        return results
    
    def match_tools(self, required_tools: List[str], available_tools: List[str]) -> List[MatchingResult]:
        """
        Match required tools against available tools.
        
        Args:
            required_tools: List of required tool strings
            available_tools: List of available tool strings
            
        Returns:
            List of MatchingResult objects for tool matches
        """
        results = []
        for required in required_tools:
            tool_results = self.match(required, available_tools)
            # Add tool-specific metadata
            for result in tool_results:
                result.metadata.reasons.append("Tool matching")
                # Apply domain-specific confidence adjustment
                domain_adjustment = self.get_domain_specific_confidence_adjustments(
                    result.requirement, result.capability)
                result.confidence *= domain_adjustment
                result.metadata.confidence = result.confidence
            results.extend(tool_results)
        return results
    
    async def match_processes(self, required_processes: List[str], available_processes: List[str]) -> List[MatchingResult]:
        """
        Match required processes against available processes.
        
        Args:
            required_processes: List of required process strings
            available_processes: List of available process strings
            
        Returns:
            List of MatchingResult objects for process matches
        """
        results = []
        for required in required_processes:
            process_results = await self.match([required], available_processes)
            # Add process-specific metadata
            for result in process_results:
                result.metadata.reasons.append("Process matching")
                # Apply domain-specific confidence adjustment
                domain_adjustment = self.get_domain_specific_confidence_adjustments(
                    result.requirement, result.capability)
                result.confidence *= domain_adjustment
                result.metadata.confidence = result.confidence
            results.extend(process_results)
        return results
    
    def match_okh_requirements(self, okh_data: Dict[str, Any], okw_capabilities: Dict[str, Any]) -> Dict[str, List[MatchingResult]]:
        """
        Match all OKH requirements against OKW capabilities.
        
        Args:
            okh_data: OKH data containing materials, components, and processes
            okw_capabilities: OKW capabilities containing available items
            
        Returns:
            Dictionary with match results for each category
        """
        results = {
            "materials": [],
            "components": [],
            "tools": [],
            "processes": []
        }
        
        # Extract requirements from OKH data
        required_materials = okh_data.get("materials", [])
        required_components = okh_data.get("components", [])
        required_tools = okh_data.get("tools", [])
        required_processes = okh_data.get("processes", [])
        
        # Extract capabilities from OKW data
        available_materials = okw_capabilities.get("available_materials", [])
        available_components = okw_capabilities.get("available_components", [])
        available_tools = okw_capabilities.get("available_tools", [])
        available_processes = okw_capabilities.get("available_processes", [])
        
        # Perform matching for each category
        if required_materials and available_materials:
            results["materials"] = self.match_materials(required_materials, available_materials)
        
        if required_components and available_components:
            results["components"] = self.match_components(required_components, available_components)
        
        if required_tools and available_tools:
            results["tools"] = self.match_tools(required_tools, available_tools)
        
        if required_processes and available_processes:
            results["processes"] = self.match_processes(required_processes, available_processes)
        
        return results
