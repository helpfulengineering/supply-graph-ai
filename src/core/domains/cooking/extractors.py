from typing import Dict, Any, List
from ...models.base.base_extractors import BaseExtractor
from ...models.base.base_types import NormalizedRequirements, NormalizedCapabilities


class CookingExtractor(BaseExtractor):
    """Extractor for cooking domain"""

    def _initial_parse_requirements(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Initial parsing of recipe data"""
        # For MVP, just pass through the content
        return content

    def _detailed_extract_requirements(
        self, parsed_data: Dict[str, Any]
    ) -> NormalizedRequirements:
        """Extract recipe data to normalized requirements

        Handles both OKH format and simple recipe format:
        - OKH format: tool_list (list of strings), materials (list of objects or strings),
                      making_instructions (list of instruction objects),
                      manufacturing_processes (list of strings)
        - Simple format: ingredients, instructions, equipment, totalTime
        """
        # Check if this is an OKH format
        has_okh_fields = (
            "tool_list" in parsed_data or "making_instructions" in parsed_data
        )

        if has_okh_fields:
            # Extract from OKH format
            ingredients = []
            tools = []
            steps = []

            # Extract ingredients from materials
            materials = parsed_data.get("materials", [])
            for material in materials:
                if isinstance(material, dict):
                    # Could be a MaterialSpec object with name, quantity, etc.
                    material_name = (
                        material.get("name")
                        or material.get("material_type")
                        or material.get("identifier", "")
                    )
                    if material_name:
                        ingredients.append(material_name)
                elif isinstance(material, str):
                    ingredients.append(material)

            # Extract tools from tool_list
            tool_list = parsed_data.get("tool_list", [])
            for tool in tool_list:
                if isinstance(tool, str) and tool:
                    tools.append(tool)
                elif isinstance(tool, dict):
                    tool_name = (
                        tool.get("name")
                        or tool.get("tool")
                        or tool.get("identifier", "")
                    )
                    if tool_name:
                        tools.append(tool_name)

            # Extract steps from making_instructions
            making_instructions = parsed_data.get("making_instructions", [])
            for instruction in making_instructions:
                if isinstance(instruction, dict):
                    title = instruction.get("title", "")
                    path = instruction.get("path", "")
                    if title:
                        steps.append(title)
                    elif path:
                        steps.append(path)
                elif isinstance(instruction, str):
                    steps.append(instruction)

            # Extract processes (cooking techniques) from manufacturing_processes
            manufacturing_processes = parsed_data.get("manufacturing_processes", [])
            for process in manufacturing_processes:
                if isinstance(process, str) and process:
                    # Add as a step/technique
                    if process not in steps:
                        steps.append(process)

            processed = {
                "ingredients": ingredients,
                "steps": steps,
                "tools": tools,
                "time": parsed_data.get("totalTime", ""),
            }
        else:
            # Use simple recipe format
            processed = {
                "ingredients": parsed_data.get("ingredients", []),
                "steps": parsed_data.get("instructions", []),
                "tools": parsed_data.get("equipment", []),
                "time": parsed_data.get("totalTime", ""),
            }

        # Create normalized requirements
        result = NormalizedRequirements(content=processed, domain="cooking")

        return result

    def _initial_parse_capabilities(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Initial parsing of kitchen data"""
        # For MVP, just pass through the content
        return content

    def _detailed_extract_capabilities(
        self, parsed_data: Dict[str, Any]
    ) -> NormalizedCapabilities:
        """Extract kitchen data to normalized capabilities

        Handles both OKW facility format and simple cooking format:
        - OKW format: typical_materials (list of objects with material_type),
                      equipment (list of objects with equipment_type),
                      manufacturing_processes (list of strings)
        - Simple format: ingredients, tools, appliances (lists of strings)
        """
        # Check if this is an OKW facility format
        has_okw_fields = (
            "typical_materials" in parsed_data or "equipment" in parsed_data
        )

        if has_okw_fields:
            # Extract from OKW facility format
            available_ingredients = []
            available_tools = []
            appliances = []

            # Extract ingredients from typical_materials
            typical_materials = parsed_data.get("typical_materials", [])
            for material in typical_materials:
                if isinstance(material, dict):
                    material_type = material.get("material_type", "")
                    # Filter out empty strings
                    if material_type and material_type.strip():
                        # Extract name from URL if it's a Wikipedia URL
                        # Format: https://www.wikidata.org/wiki/Q12345 or just "Q12345"
                        if material_type.startswith("http"):
                            # Try to extract a readable name, or use the URL
                            available_ingredients.append(material_type)
                        else:
                            available_ingredients.append(material_type)
                elif isinstance(material, str) and material.strip():
                    available_ingredients.append(material)

            # Extract tools from equipment
            equipment = parsed_data.get("equipment", [])
            for eq in equipment:
                if isinstance(eq, dict):
                    equipment_type = eq.get("equipment_type", "")
                    manufacturing_process = eq.get("manufacturing_process", "")

                    # Add equipment type if present (filter out empty strings)
                    if equipment_type and equipment_type.strip():
                        if equipment_type.startswith("http"):
                            available_tools.append(equipment_type)
                        else:
                            available_tools.append(equipment_type)

                    # Manufacturing process might indicate cooking techniques/appliances
                    if manufacturing_process and manufacturing_process.strip():
                        if manufacturing_process.startswith("http"):
                            appliances.append(manufacturing_process)
                        else:
                            appliances.append(manufacturing_process)
                elif isinstance(eq, str) and eq.strip():
                    available_tools.append(eq)

            # Extract appliances from manufacturing_processes
            manufacturing_processes = parsed_data.get("manufacturing_processes", [])
            for process in manufacturing_processes:
                if isinstance(process, str) and process:
                    if process.startswith("http"):
                        appliances.append(process)
                    else:
                        appliances.append(process)

            processed = {
                "available_ingredients": available_ingredients,
                "available_tools": available_tools,
                "appliances": appliances,
            }
        else:
            # Use simple cooking format
            processed = {
                "available_ingredients": parsed_data.get("ingredients", []),
                "available_tools": parsed_data.get("tools", []),
                "appliances": parsed_data.get("appliances", []),
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
