"""
Heuristic Matching Layer for OKH manifest generation.

This layer applies rule-based pattern recognition to extract information
from file structures, naming conventions, and content patterns.
"""

import re
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from .base import BaseGenerationLayer, LayerResult
from ..models import ProjectData, GenerationLayer, FileInfo, DocumentInfo


@dataclass
class FilePattern:
    """Pattern for matching files"""
    pattern: str
    field: str
    confidence: float
    extraction_method: str
    description: str


class HeuristicMatcher(BaseGenerationLayer):
    """Heuristic matching layer using rule-based pattern recognition"""
    
    def __init__(self):
        super().__init__(GenerationLayer.HEURISTIC)
        self.file_patterns = self._initialize_file_patterns()
        self.content_patterns = self._initialize_content_patterns()
    
    def _initialize_file_patterns(self) -> List[FilePattern]:
        """Initialize file pattern matching rules"""
        return [
            # License files
            FilePattern(
                pattern=r"(?i)^(license|licence)(\.(txt|md))?$",
                field="license",
                confidence=0.9,
                extraction_method="license_file_detection",
                description="License file detection"
            ),
            
            # BOM files
            FilePattern(
                pattern=r"(?i)^(bom|bill.of.materials|materials)(\.(txt|md|csv|json))?$",
                field="bom",
                confidence=0.8,
                extraction_method="bom_file_detection",
                description="Bill of Materials file detection"
            ),
            
            # Manufacturing files
            FilePattern(
                pattern=r"(?i)^(manufacturing|production|assembly)(\.(txt|md))?$",
                field="manufacturing_files",
                confidence=0.7,
                extraction_method="manufacturing_file_detection",
                description="Manufacturing instruction file detection"
            ),
            
            # Design files
            FilePattern(
                pattern=r"(?i)^(design|cad|model)(\.(txt|md))?$",
                field="design_files",
                confidence=0.7,
                extraction_method="design_file_detection",
                description="Design file detection"
            ),
            
            # Tool lists
            FilePattern(
                pattern=r"(?i)^(tools|equipment|requirements)(\.(txt|md))?$",
                field="tool_list",
                confidence=0.7,
                extraction_method="tool_list_detection",
                description="Tool list file detection"
            ),
            
            # Assembly instructions
            FilePattern(
                pattern=r"(?i)^(assembly|build|make|instructions)(\.(txt|md))?$",
                field="making_instructions",
                confidence=0.8,
                extraction_method="assembly_instruction_detection",
                description="Assembly instruction file detection"
            ),
            
            # Operating instructions
            FilePattern(
                pattern=r"(?i)^(operating|usage|manual|user.guide)(\.(txt|md))?$",
                field="operating_instructions",
                confidence=0.8,
                extraction_method="operating_instruction_detection",
                description="Operating instruction file detection"
            )
        ]
    
    def _initialize_content_patterns(self) -> Dict[str, List[Tuple[str, str, float]]]:
        """Initialize content pattern matching rules"""
        return {
            "function": [
                (r"(?i)(?:function|purpose|what.is.it|what.does.it.do)[\s:]*([^.\n]{10,100})", "function_description", 0.8),
                (r"(?i)(?:this.project.aims.to|this.project.creates|this.project.builds)[\s:]*([^.\n]{10,100})", "project_aims", 0.7),
                (r"(?i)(?:is a\s+)([^.\n]{10,100})(?:\s+that|\s+which|\s+for)", "is_a_description", 0.6)
            ],
            "intended_use": [
                (r"(?i)(?:intended.use|use.case|application|for\s+)([^.\n]{10,100})", "intended_use_direct", 0.9),
                (r"(?i)(?:can.be.used|suitable.for|designed.for)[\s:]*([^.\n]{10,100})", "intended_use_indirect", 0.7),
                (r"(?i)(?:perfect.for|ideal.for|great.for)[\s:]*([^.\n]{10,100})", "intended_use_positive", 0.6)
            ],
            "materials": [
                (r"(?i)(?:bill.of.materials|bom|materials|parts|components)[\s:]*([^=]{10,200})", "materials_direct", 0.8),
                (r"(?i)(?:made.from|constructed.from|built.using)[\s:]*([^.\n]{10,100})", "materials_construction", 0.7),
                (r"(?i)(?:requires|needs|uses)[\s:]*([^.\n]{10,100})", "materials_requirements", 0.6)
            ],
            "manufacturing_processes": [
                (r"(?i)(?:3d.print|3d.printing|printed)", "3D Printing", 0.9),
                (r"(?i)(?:laser.cut|laser.cutting)", "Laser cutting", 0.9),
                (r"(?i)(?:cnc|machining)", "CNC machining", 0.9),
                (r"(?i)(?:solder|soldering)", "Soldering", 0.8),
                (r"(?i)(?:assemble|assembly)", "Assembly", 0.7),
                (r"(?i)(?:fabricat|fabrication)", "Fabrication", 0.7)
            ],
        }
    
    async def process(self, project_data: ProjectData) -> LayerResult:
        """Process project data using heuristic matching"""
        result = LayerResult(self.layer_type)
        
        try:
            # Analyze file structure
            await self._analyze_file_structure(project_data, result)
            
            # Parse README content
            await self._parse_readme_content(project_data, result)
            
            # Analyze documentation files
            await self._analyze_documentation(project_data, result)
            
            # Extract from file names and paths
            await self._extract_from_file_names(project_data, result)
            
            # Apply content patterns
            await self._apply_content_patterns(project_data, result)
            
            # Extract version and documentation language
            await self._extract_metadata_fields(project_data, result)
            
            result.add_log(f"Heuristic layer processed {len(project_data.files)} files and {len(project_data.documentation)} documents")
            
        except Exception as e:
            result.add_error(f"Heuristic processing failed: {str(e)}")
        
        return result
    
    async def _analyze_file_structure(self, project_data: ProjectData, result: LayerResult):
        """Analyze file structure for manufacturing and design files"""
        file_paths = [f.path for f in project_data.files]
        
        # Check for common hardware project directories
        directories = set()
        for file_path in file_paths:
            path_parts = Path(file_path).parts
            for part in path_parts[:-1]:  # Exclude filename
                directories.add(part.lower())
        
        # Detect manufacturing files based on directory structure and file extensions
        manufacturing_indicators = {
            'stl', 'stls', '3d', 'print', 'printing', 'manufacturing', 'production',
            'assembly', 'build', 'make', 'fabrication', 'parts', 'hardware'
        }
        
        design_indicators = {
            'cad', 'design', 'model', 'models', 'openscad', 'freecad', 'fusion',
            'solidworks', 'inventor', 'sketchup', 'blender', 'step', 'stp', 'iges'
        }
        
        docs_indicators = {
            'docs', 'documentation', 'manual', 'guide', 'instructions', 'tutorial',
            'readme', 'help', 'wiki'
        }
        
        # Also check file extensions
        manufacturing_extensions = {'.stl', '.gcode', '.3mf', '.amf'}
        design_extensions = {'.scad', '.step', '.stp', '.iges', '.iges', '.dxf', '.dwg', '.kicad_pcb', '.kicad_mod'}
        doc_extensions = {'.md', '.txt', '.pdf', '.doc', '.docx'}
        
        # Count indicators
        manufacturing_score = len(manufacturing_indicators.intersection(directories))
        design_score = len(design_indicators.intersection(directories))
        docs_score = len(docs_indicators.intersection(directories))
        
        # Generate manufacturing files list
        manufacturing_files = []
        for file_path in file_paths:
            path_lower = file_path.lower()
            file_ext = Path(file_path).suffix.lower()
            
            # Skip GitHub-specific files and directories
            if (path_lower.startswith('.github/') or 
                path_lower.startswith('.git/') or
                path_lower.startswith('.vscode/') or
                'workflow' in path_lower):
                continue
            
            # Check directory structure and file extensions
            # Exclude design files from manufacturing files
            if (file_ext in design_extensions):
                continue
                
            if (any(indicator in path_lower for indicator in manufacturing_indicators) or 
                file_ext in manufacturing_extensions):
                manufacturing_files.append({
                    "title": Path(file_path).name,
                    "path": file_path,
                    "type": "manufacturing-files",
                    "metadata": {"detected_by": "file_analysis"}
                })
        
        if manufacturing_files:
            result.add_field(
                "manufacturing_files",
                manufacturing_files,
                0.8,  # Higher confidence for file-based detection
                "file_analysis",
                f"Detected {len(manufacturing_files)} manufacturing files"
            )
        
        # Generate design files list
        design_files = []
        for file_path in file_paths:
            path_lower = file_path.lower()
            file_ext = Path(file_path).suffix.lower()
            
            # Check directory structure and file extensions
            if (any(indicator in path_lower for indicator in design_indicators) or 
                file_ext in design_extensions):
                design_files.append({
                    "title": Path(file_path).name,
                    "path": file_path,
                    "type": "design-files",
                    "metadata": {"detected_by": "file_analysis"}
                })
        
        if design_files:
            result.add_field(
                "design_files",
                design_files,
                0.8,  # Higher confidence for file-based detection
                "file_analysis",
                f"Detected {len(design_files)} design files"
            )
        
        # Generate making instructions list
        making_instructions = []
        for file_path in file_paths:
            path_lower = file_path.lower()
            file_ext = Path(file_path).suffix.lower()
            
            # Skip GitHub-specific files and directories
            if (path_lower.startswith('.github/') or 
                path_lower.startswith('.git/') or
                path_lower.startswith('.vscode/') or
                'workflow' in path_lower):
                continue
            
            # Check directory structure and file extensions
            if (any(indicator in path_lower for indicator in docs_indicators) or 
                file_ext in doc_extensions):
                making_instructions.append({
                    "title": Path(file_path).name,
                    "path": file_path,
                    "type": "manufacturing-files",
                    "metadata": {"detected_by": "file_analysis"}
                })
        
        if making_instructions:
            result.add_field(
                "making_instructions",
                making_instructions,
                0.7,  # Higher confidence for file-based detection
                "file_analysis",
                f"Detected {len(making_instructions)} documentation files"
            )
    
    async def _parse_readme_content(self, project_data: ProjectData, result: LayerResult):
        """Parse README content for key information"""
        readme_content = ""
        
        # Find README file
        for file_info in project_data.files:
            if file_info.path.lower().startswith('readme'):
                readme_content = file_info.content
                break
        
        # Also check documentation
        for doc_info in project_data.documentation:
            if doc_info.title.lower().startswith('readme'):
                readme_content = doc_info.content
                break
        
        if not readme_content:
            return
        
        # Extract function/purpose - look for project description
        function_patterns = [
            r"(?i)this.project.aims.to\s+([^.]{20,200})",
            r"(?i)this.project.creates\s+([^.]{20,200})",
            r"(?i)this.project.builds\s+([^.]{20,200})",
            r"(?i)is a\s+([^.]{20,200})(?:\s+that|\s+which|\s+for)",
            r"(?i)the\s+([^.]{20,200})\s+is a\s+([^.]{20,200})"
        ]
        
        for pattern in function_patterns:
            function_match = re.search(pattern, readme_content, re.DOTALL)
            if function_match:
                function_text = function_match.group(1).strip()
                # Clean up the text - remove extra whitespace and newlines
                function_text = re.sub(r'\s+', ' ', function_text)
                function_text = re.sub(r'[^\w\s\-.,()]', '', function_text)
                if len(function_text) > 20 and not function_text.startswith('='):
                    result.add_field(
                        "function",
                        function_text,
                        0.8,
                        "readme_function_extraction",
                        "Extracted from README project description"
                    )
                    break
        
        # Extract intended use - look for specific use cases
        intended_use_patterns = [
            r"(?i)for\s+([^.]{20,200})(?:\s+in|\s+with|\s+using)",
            r"(?i)can.be.used\s+([^.]{20,200})",
            r"(?i)suitable.for\s+([^.]{20,200})",
            r"(?i)designed.for\s+([^.]{20,200})",
            r"(?i)functions.as\s+([^.]{20,200})",
            r"(?i)resulting.from.this.project.functions.as\s+([^.]{20,200})"
        ]
        
        for pattern in intended_use_patterns:
            intended_use_match = re.search(pattern, readme_content, re.DOTALL)
            if intended_use_match:
                intended_use_text = intended_use_match.group(1).strip()
                # Clean up the text - remove extra whitespace and newlines
                intended_use_text = re.sub(r'\s+', ' ', intended_use_text)
                intended_use_text = re.sub(r'[^\w\s\-.,()]', '', intended_use_text)
                if len(intended_use_text) > 20 and not intended_use_text.startswith('='):
                    result.add_field(
                        "intended_use",
                        intended_use_text,
                        0.8,
                        "readme_intended_use_extraction",
                        "Extracted from README intended use description"
                    )
                    break
        
        # Skip keywords extraction in heuristic layer - leave for NLP/LLM layers
        # Keywords require semantic understanding that regex cannot provide
        
        # Extract organization from URL
        if project_data.url:
            org_match = re.search(r'github\.com/([^/]+)/', project_data.url)
            if org_match:
                organization = org_match.group(1)
                result.add_field(
                    "organization",
                    {"name": organization},
                    0.9,
                    "url_organization_extraction",
                    f"Extracted from URL: {project_data.url}"
                )
        
        # Extract materials from BOM components if available
        materials = self._extract_materials_from_bom(project_data)
        if materials:
            result.add_field(
                "materials",
                materials,
                0.8,
                "bom_materials_extraction",
                "Extracted from BOM components"
            )
        else:
            # Fallback: Extract materials from README text
            materials = self._extract_materials_from_readme(readme_content)
            if materials:
                result.add_field(
                    "materials",
                    materials,
                    0.6,
                    "readme_materials_extraction",
                    "Extracted from README materials section"
                )
        
        # Extract tool list
        tools_match = re.search(r"(?i)(?:tools|equipment|requirements)[\s:]*([^\n]+)", readme_content)
        if tools_match:
            tools_text = tools_match.group(1).strip()
            tools = re.split(r'[,;|\n]', tools_text)
            tools = [tool.strip() for tool in tools if tool.strip()]
            if tools:
                result.add_field(
                    "tool_list",
                    tools,
                    0.7,
                    "readme_tools_extraction",
                    "Extracted from README tools section"
                )
    
    async def _analyze_documentation(self, project_data: ProjectData, result: LayerResult):
        """Analyze documentation files for additional information"""
        for doc_info in project_data.documentation:
            content = doc_info.content.lower()
            
            # Check for manufacturing processes using the same mapping as content patterns
            processes = self._extract_processes_from_text(content)
            
            if processes and not result.has_field('manufacturing_processes'):
                result.add_field(
                    "manufacturing_processes",
                    processes,
                    0.8,
                    "documentation_process_analysis",
                    f"Detected processes in {doc_info.title}"
                )
    
    async def _extract_from_file_names(self, project_data: ProjectData, result: LayerResult):
        """Extract information from file names and patterns"""
        for file_info in project_data.files:
            file_path = file_info.path.lower()
            file_name = Path(file_path).name.lower()
            
            # Apply file patterns
            for pattern in self.file_patterns:
                if re.search(pattern.pattern, file_name):
                    if pattern.field == "license":
                        # Extract license content
                        license_content = file_info.content
                        license_type = self._extract_license_type(license_content)
                        if license_type:
                            result.add_field(
                                "license",
                                license_type,
                                pattern.confidence,
                                pattern.extraction_method,
                                f"Detected from {file_name}"
                            )
                    elif pattern.field == "bom":
                        # Extract BOM content
                        bom_content = file_info.content
                        materials = self._parse_bom_content(bom_content)
                        if materials:
                            result.add_field(
                                "materials",
                                materials,
                                pattern.confidence,
                                pattern.extraction_method,
                                f"Parsed from {file_name}"
                            )
                    else:
                        # For other fields, add the file to the appropriate list
                        file_entry = {
                            "title": Path(file_info.path).name,
                            "path": file_info.path,
                            "type": f"{pattern.field.replace('_', '-')}-files",
                            "metadata": {"detected_by": "file_pattern"}
                        }
                        
                        if result.has_field(pattern.field):
                            # Add to existing list
                            existing = result.get_field(pattern.field).value
                            if isinstance(existing, list):
                                existing.append(file_entry)
                        else:
                            # Create new list
                            result.add_field(
                                pattern.field,
                                [file_entry],
                                pattern.confidence,
                                pattern.extraction_method,
                                f"Detected from {file_name}"
                            )
    
    async def _apply_content_patterns(self, project_data: ProjectData, result: LayerResult):
        """Apply content patterns to extract additional information"""
        all_content = ""
        
        # Combine all file content
        for file_info in project_data.files:
            all_content += file_info.content + "\n"
        
        for doc_info in project_data.documentation:
            all_content += doc_info.content + "\n"
        
        # Apply patterns
        for field, patterns in self.content_patterns.items():
            if result.has_field(field):
                continue  # Skip if already extracted
            
            for pattern, method, confidence in patterns:
                match = re.search(pattern, all_content)
                if match:
                    value = match.group(1).strip()
                    
                    # Special handling for different fields
                    if field == "keywords":
                        keywords = re.split(r'[,;|\n]', value)
                        keywords = [kw.strip() for kw in keywords if kw.strip()]
                        if keywords:
                            result.add_field(field, keywords, confidence, method, f"Pattern: {pattern}")
                    elif field == "manufacturing_processes":
                        processes = self._extract_processes_from_text(value)
                        if processes:
                            result.add_field(field, processes, confidence, method, f"Pattern: {pattern}")
                    else:
                        result.add_field(field, value, confidence, method, f"Pattern: {pattern}")
                    break  # Use first match
    
    def _parse_materials_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse materials from text"""
        materials = []
        
        # Look for structured material entries
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('=') or line.startswith('#'):
                continue
            
            # Skip markdown links and random text
            if '[' in line and ']' in line and '(' in line and ')' in line:
                continue
            if 'http' in line or 'www.' in line:
                continue
            if len(line) < 10:  # Skip very short lines
                continue
            
            # Try to parse quantity and unit
            quantity_match = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)', line)
            if quantity_match:
                quantity = float(quantity_match.group(1))
                unit = quantity_match.group(2)
                
                # Extract material name (everything before the quantity)
                material_name = line[:quantity_match.start()].strip()
                # Clean up material name
                material_name = re.sub(r'^[\*\-\+\s]+', '', material_name)  # Remove bullet points
                material_name = re.sub(r'\([^)]*\)', '', material_name)  # Remove parenthetical info
                material_name = material_name.strip()
                
                if material_name and len(material_name) > 3:
                    materials.append({
                        "material_id": material_name.upper().replace(' ', '_').replace('-', '_'),
                        "name": material_name,
                        "quantity": quantity,
                        "unit": unit,
                        "notes": "Extracted from README"
                    })
        
        return materials
    
    def _parse_bom_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse BOM content"""
        materials = []
        
        # Try different BOM formats
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # CSV format
            if ',' in line:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 2:
                    materials.append({
                        "material_id": parts[0].upper().replace(' ', '_'),
                        "name": parts[0],
                        "quantity": self._parse_quantity(parts[1]) if len(parts) > 1 else 1,
                        "unit": parts[2] if len(parts) > 2 else "pcs",
                        "notes": "Parsed from BOM file"
                    })
            # Simple list format
            else:
                quantity_match = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?\s*(.+)', line)
                if quantity_match:
                    quantity = float(quantity_match.group(1))
                    unit = quantity_match.group(2) or "pcs"
                    name = quantity_match.group(3).strip()
                    
                    materials.append({
                        "material_id": name.upper().replace(' ', '_'),
                        "name": name,
                        "quantity": quantity,
                        "unit": unit,
                        "notes": "Parsed from BOM file"
                    })
        
        return materials
    
    def _extract_license_type(self, content: str) -> Optional[str]:
        """Extract license type from license file content"""
        content_lower = content.lower()
        
        # Common license patterns
        license_patterns = {
            'MIT': r'mit\s+license',
            'Apache-2.0': r'apache\s+license',
            'GPL-3.0': r'gnu\s+general\s+public\s+license',
            'GPL-2.0': r'gnu\s+general\s+public\s+license\s+version\s+2',
            'BSD-3-Clause': r'bsd\s+3.clause',
            'BSD-2-Clause': r'bsd\s+2.clause',
            'CERN-OHL-S-2.0': r'cern\s+open\s+hardware\s+license',
            'CERN-OHL-P-2.0': r'cern\s+open\s+hardware\s+license\s+permissive',
            'CERN-OHL-W-2.0': r'cern\s+open\s+hardware\s+license\s+weakly.revocable'
        }
        
        for license_type, pattern in license_patterns.items():
            if re.search(pattern, content_lower):
                return license_type
        
        return None
    
    def _extract_processes_from_text(self, text: str) -> List[str]:
        """Extract manufacturing processes from text"""
        processes = []
        text_lower = text.lower()
        
        process_mapping = {
            '3d print': '3D Printing',
            '3d printing': '3D Printing',
            'laser cut': 'Laser cutting',
            'laser cutting': 'Laser cutting',
            'cnc': 'CNC machining',
            'machining': 'CNC machining',
            'solder': 'Soldering',
            'soldering': 'Soldering',
            'assemble': 'Assembly',
            'assembly': 'Assembly'
        }
        
        for keyword, process in process_mapping.items():
            if keyword in text_lower and process not in processes:
                processes.append(process)
        
        return processes
    
    async def _extract_metadata_fields(self, project_data: ProjectData, result: LayerResult):
        """Extract version and documentation language metadata"""
        
        # Extract version from repository metadata or default to 1.0.0
        if not result.has_field("version"):
            # Try to extract from repository metadata
            version = "1.0.0"  # Default version
            if project_data.metadata and "version" in project_data.metadata:
                version = project_data.metadata["version"]
            elif project_data.metadata and "tag_name" in project_data.metadata:
                version = project_data.metadata["tag_name"]
            
            result.add_field(
                "version",
                version,
                0.8,
                "metadata_version_extraction",
                "Extracted from repository metadata or default"
            )
        
        # Extract documentation language - default to English for GitHub repositories
        if not result.has_field("documentation_language"):
            # For now, default to English for GitHub repositories
            # In the future, this could be enhanced with language detection
            result.add_field(
                "documentation_language",
                "en",
                0.7,
                "default_language_assignment",
                "Default to English for GitHub repositories"
            )
    
    def _parse_quantity(self, text: str) -> float:
        """Parse quantity from text"""
        try:
            # Remove non-numeric characters except decimal point
            cleaned = re.sub(r'[^\d.]', '', text)
            return float(cleaned) if cleaned else 1.0
        except ValueError:
            return 1.0
    
    def _extract_materials_from_bom(self, project_data: ProjectData) -> List[str]:
        """Extract materials from BOM components if available"""
        materials = set()
        
        # Look for BOM files in the project data
        for file_info in project_data.files:
            if file_info.file_type == "bom" and file_info.content:
                # Parse BOM content to extract component names
                component_names = self._extract_component_names_from_bom(file_info.content)
                for name in component_names:
                    material = self._classify_component_material(name)
                    if material:
                        materials.add(material)
        
        return list(materials) if materials else []
    
    def _extract_component_names_from_bom(self, bom_content: str) -> List[str]:
        """Extract component names from BOM content"""
        component_names = []
        
        # Look for markdown table rows or list items
        lines = bom_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Check for markdown table rows (| component | quantity |)
            if '|' in line:
                parts = [part.strip() for part in line.split('|')]
                # Skip header rows and separator rows
                if len(parts) >= 3 and not any(char in parts[1].lower() for char in ['component', 'part', 'item', 'name', '---', '===']):
                    component_names.append(parts[1])  # Second column is usually component name
            
            # Check for list items (- component name)
            elif line.startswith('-') or line.startswith('*'):
                component_name = line[1:].strip()
                if component_name:
                    component_names.append(component_name)
        
        return component_names
    
    def _classify_component_material(self, component_name: str) -> Optional[str]:
        """Classify a component name into a material type"""
        name_lower = component_name.lower()
        
        # Material classification patterns - ordered by specificity (most specific first)
        material_patterns = [
            # Specific materials first (to avoid false matches)
            ('brass', ['brass']),
            ('copper', ['copper', 'cu ']),
            ('aluminum', ['aluminum', 'aluminium', 'al ', 'al-']),
            ('steel', ['stainless steel', 'steel']),  # stainless steel before steel
            ('PLA', ['pla', 'polylactic acid']),
            ('ABS', ['abs', 'acrylonitrile butadiene styrene']),
            ('PETG', ['petg', 'pet-g']),
            ('TPU', ['tpu', 'thermoplastic polyurethane']),
            ('wood', ['wood', 'plywood', 'mdf', 'oak', 'pine']),
            ('acrylic', ['acrylic', 'plexiglass', 'pmma']),
            # Component types
            ('electronics', ['arduino', 'raspberry pi', 'sensor', 'motor', 'servo', 'led', 'resistor', 'capacitor', 'transistor', 'ic', 'microcontroller']),
            ('fasteners', ['screw', 'bolt', 'nut', 'washer', 'rivet', 'pin']),
            ('cables', ['cable', 'wire', 'connector', 'jack', 'plug']),
            ('bearings', ['bearing', 'ball bearing', 'roller bearing']),
            ('springs', ['spring', 'coil spring', 'tension spring'])
        ]
        
        # Check each material pattern (first match wins)
        for material, patterns in material_patterns:
            for pattern in patterns:
                if pattern in name_lower:
                    return material
        
        return None
    
    def _extract_materials_from_readme(self, readme_content: str) -> List[str]:
        """Extract materials from README text as fallback"""
        materials = set()
        
        # Look for materials sections in README
        materials_patterns = [
            r"(?i)bill.of.materials[^=]*\n(.*?)(?=\n\n|\n[A-Z]|\n#|\n\*\*|\Z)",
            r"(?i)materials[^=]*\n(.*?)(?=\n\n|\n[A-Z]|\n#|\n\*\*|\Z)",
            r"(?i)parts[^=]*\n(.*?)(?=\n\n|\n[A-Z]|\n#|\n\*\*|\Z)"
        ]
        
        for pattern in materials_patterns:
            materials_match = re.search(pattern, readme_content, re.DOTALL)
            if materials_match:
                materials_text = materials_match.group(1).strip()
                # Clean up the text
                materials_text = re.sub(r'^=+\s*$', '', materials_text, flags=re.MULTILINE)
                materials_text = re.sub(r'^\s*\n', '', materials_text, flags=re.MULTILINE)
                
                if len(materials_text) > 20 and not materials_text.startswith('='):
                    # Extract component names from the text
                    component_names = self._extract_component_names_from_bom(materials_text)
                    for name in component_names:
                        material = self._classify_component_material(name)
                        if material:
                            materials.add(material)
                    break
        
        return list(materials) if materials else []
