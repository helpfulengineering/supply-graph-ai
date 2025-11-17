"""
LLM Generation Layer for OKH manifest generation.

This layer uses Large Language Models for advanced content analysis and field extraction.
It provides sophisticated understanding of project content and can generate high-quality
manifest fields through natural language processing.

The layer implements the Enhanced LLM Agent Prompt Engineering Strategy with:
- Context file management for transparent analysis
- Schema-aware prompting for accurate field mapping
- Integration with the LLM service for provider management
- validation and quality assurance
"""

import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .base import BaseGenerationLayer, LayerResult
from ..models import ProjectData, GenerationLayer, LayerConfig
from ...llm.service import LLMService, LLMServiceConfig
from ...llm.models.requests import LLMRequest, LLMRequestConfig, LLMRequestType
from ...llm.models.responses import LLMResponseStatus
from ...llm.providers.base import LLMProviderType
from ...services.base import ServiceStatus

# Configure logging
logger = logging.getLogger(__name__)


class LLMGenerationLayer(BaseGenerationLayer):
    """
    LLM Generation Layer using Large Language Models for advanced content analysis.
    
    This layer implements the Enhanced LLM Agent Prompt Engineering Strategy with:
    - Context file management for transparent analysis
    - Schema-aware prompting for accurate field mapping
    - Integration with the LLM service for provider management
    - validation and quality assurance
    
    The layer analyzes project repositories using LLM agents that can:
    - Understand repository structure and content
    - Extract complex fields from documentation and code
    - Generate high-quality OKH manifest fields
    - Provide confidence scores and validation metadata
    """
    
    def __init__(self, layer_config: Optional[LayerConfig] = None, llm_service: Optional[LLMService] = None, preserve_context: bool = False):
        """
        Initialize the LLM Generation Layer.
        
        Args:
            layer_config: Configuration for this layer. If None, uses default configuration.
            llm_service: LLM service instance. If None, creates a new one.
            preserve_context: If True, context files are preserved for debugging instead of cleaned up.
            
        Raises:
            RuntimeError: If LLM layer is not properly configured
        """
        super().__init__(GenerationLayer.LLM, layer_config)
        
        # Initialize LLM service
        self.llm_service = llm_service or self._create_llm_service()
        
        # Context file management
        self.context_dir = Path("temp_context")
        self.context_dir.mkdir(exist_ok=True)
        self.preserve_context = preserve_context
        
        # OKH Schema Reference (from our strategy document)
        self.okh_schema_prompt = self._load_okh_schema_prompt()
        
        logger.info(f"LLM Generation Layer initialized with provider: {self.llm_service.config.default_provider}")
    
    def _create_llm_service(self) -> LLMService:
        """Create LLM service (initialization will be done in process method)"""
        try:
            # Create LLM service configuration (uses centralized default model)
            service_config = LLMServiceConfig(
                name="LLMGenerationLayer",
                default_provider=LLMProviderType.ANTHROPIC,
                default_model=None,  # Use centralized config
                max_retries=3,
                retry_delay=1.0,
                timeout=60,  # Longer timeout for complex analysis
                enable_fallback=True,
                max_cost_per_request=2.0,  # Higher cost limit for generation
                enable_cost_tracking=True,
                max_concurrent_requests=5
            )
            
            # Create service (don't initialize yet)
            service = LLMService("LLMGenerationLayer", service_config)
            
            return service
            
        except Exception as e:
            logger.error(f"Failed to create LLM service: {e}")
            raise RuntimeError(f"LLM service creation failed: {e}")
    
    def _load_okh_schema_prompt(self) -> str:
        """Load the OKH schema prompt from our strategy document"""
        # This is a simplified version - in production, this would be loaded from the schema strategy
        return """
# OKH (Open Know-How) Manifest Schema Reference

## Core Purpose
The OKH manifest is designed to maximize interoperability and discoverability in open-source hardware by providing a standardized way to describe hardware projects, their manufacturing requirements, and dependencies.

## Required Fields

### title (string, required)
- **Purpose**: Human-readable project name
- **Format**: Clear, descriptive title
- **Example**: "Arduino IoT Sensor Node"
- **Mapping Strategy**: Extract from repository name, README title, or package.json

### version (string, required)
- **Purpose**: Project version identifier
- **Format**: Semantic versioning preferred (e.g., "1.2.3")
- **Example**: "1.0.0"
- **Mapping Strategy**: Extract from version files, git tags, or package managers

### license (License object, required)
- **Purpose**: License under which the project is released
- **Format**: License object with hardware, documentation, and software fields
- **Example**: {"hardware": "MIT", "documentation": "CC-BY-SA-4.0", "software": "GPL-3.0"}
- **Mapping Strategy**: Find in LICENSE file, package.json, or repository metadata

### licensor (string/Person/Organization, required)
- **Purpose**: Entity that holds the license
- **Format**: Can be string, Person object, or Organization object
- **Example**: "John Doe" or {"name": "John Doe", "email": "john@example.com"}
- **Mapping Strategy**: Extract from repository metadata, package.json, or documentation

### documentation_language (string/array, required)
- **Purpose**: Language(s) of the documentation
- **Format**: ISO language codes
- **Example**: "en" or ["en", "es", "fr"]
- **Mapping Strategy**: Analyze documentation files and repository metadata

### function (string, required)
- **Purpose**: Concise statement of WHAT the hardware does - its primary function or purpose
- **Format**: One sentence describing the core functionality (action-oriented, 15-30 words)
- **Focus**: The hardware's primary capability or what it accomplishes
- **Example**: "Environmental monitoring sensor node that measures temperature, humidity, and air quality"
- **DO NOT**: Include use cases, target users, or detailed features - those belong in description or intended_use
- **Mapping Strategy**: Extract the core functional purpose from README, project description, or technical documentation

## Optional Fields

### description (string, optional)
- **Purpose**: Comprehensive overview of the project - what it is, its features, capabilities, and context
- **Format**: Detailed multi-sentence description (50-200 words)
- **Focus**: Complete picture of the project including features, capabilities, technical details, and context
- **Example**: "A low-power IoT sensor node based on Arduino with environmental monitoring capabilities. Features include temperature, humidity, and air quality sensors, wireless connectivity via WiFi, battery-powered operation, and a compact 3D-printed enclosure. Designed for deployment in remote locations with minimal maintenance requirements."
- **Distinction from function**: Description is comprehensive and detailed; function is concise and action-oriented
- **Distinction from intended_use**: Description focuses on WHAT the project is; intended_use focuses on WHO uses it and FOR WHAT PURPOSE
- **Mapping Strategy**: Combine README content, project documentation, and code analysis to create a comprehensive overview

### intended_use (string, optional)
- **Purpose**: Describes WHO uses the hardware and FOR WHAT PURPOSE - the use cases, applications, and target users
- **Format**: One or two sentences describing use cases and target applications (20-50 words)
- **Focus**: Use cases, applications, target users, and scenarios where the hardware is deployed
- **Example**: "Designed for researchers, educators, and hobbyists conducting environmental monitoring in field studies, classroom experiments, and home automation projects"
- **DO NOT**: Include technical specifications, features, or what the hardware does - those belong in description or function
- **Distinction from function**: Function describes WHAT it does; intended_use describes WHO uses it and WHY
- **Distinction from description**: Description is a comprehensive overview; intended_use focuses specifically on use cases and applications
- **Mapping Strategy**: Extract from README sections about use cases, applications, target audience, or "who is this for" content

### keywords (array, optional)
- **Purpose**: Keywords for discoverability
- **Format**: Array of relevant tags
- **Example**: ["iot", "sensor", "arduino", "environmental"]
- **Mapping Strategy**: Analyze project content and domain knowledge

### manufacturing_processes (array, optional)
- **Purpose**: Manufacturing processes used
- **Format**: Array of process names
- **Example**: ["3D printing", "soldering", "assembly"]
- **Mapping Strategy**: Analyze manufacturing documentation

### materials (array, optional)
- **Purpose**: Materials used in the project
- **Format**: Array of MaterialSpec objects
- **Example**: [{"material_id": "PLA", "name": "PLA Filament", "quantity": 100, "unit": "g"}]
- **Mapping Strategy**: Extract from BOM and documentation

## Interoperability Guidelines

### Field Mapping Principles:
1. **Standardization**: Use consistent formats and terminology
2. **Completeness**: Provide as much detail as possible
3. **Accuracy**: Ensure information is correct and up-to-date
4. **Discoverability**: Include relevant keywords and tags
5. **Manufacturing Focus**: Prioritize manufacturing and assembly information

### Quality Standards:
- All required fields must be populated
- Information should be accurate and verifiable
- Manufacturing notes should be detailed and actionable
- Dependencies should be complete and specific
- Documentation links should be functional and relevant
"""
    
    async def process(self, project_data: ProjectData) -> LayerResult:
        """
        Process project data using LLM analysis.
        
        This method implements the Enhanced LLM Agent Prompt Engineering Strategy:
        1. Create temporary context file for analysis
        2. Run LLM analysis with schema-aware prompting
        3. Extract and validate manifest fields
        4. Clean up context file
        
        Args:
            project_data: Raw project data from platform extractor
            
        Returns:
            LayerResult containing extracted fields and metadata
            
        Raises:
            ValueError: If project data is invalid
            RuntimeError: If LLM processing fails
        """
        # Validate input
        if not self.validate_project_data(project_data):
            raise ValueError("Invalid project data")
        
        # Create result
        result = self.create_layer_result()
        
        # Create temporary context file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        context_file = self.context_dir / f"okh_analysis_{timestamp}.md"
        
        try:
            # Log processing start
            self.log_processing_start(project_data)
            
            # Initialize LLM service if not already done
            if self.llm_service.status != ServiceStatus.ACTIVE:
                await self.llm_service.initialize()
            
            # Initialize context file
            await self._create_context_file(context_file, project_data, result)
            
            # Run LLM analysis
            await self._run_llm_analysis(project_data, context_file, result)
            
            # Log processing end
            self.log_processing_end(result)
            
            return result
            
        except Exception as e:
            self.handle_processing_error(e, result)
            return result
    
        finally:
            # Clean up context file
            await self._cleanup_context_file(context_file)
    
    async def _create_context_file(self, context_file: Path, project_data: ProjectData, result: LayerResult):
        """Create and initialize context file with project data"""
        template_data = {
            "repo_name": project_data.metadata.get("name", "Unknown Project"),
            "timestamp": datetime.now().isoformat(),
            "tree_output": "To be populated by LLM",
            "readme_path": "To be identified",
            "doc_paths": "To be identified",
            "source_paths": "To be identified",
            "config_paths": "To be identified",
            "project_type": "To be determined",
            "domain": "To be determined",
            "technologies": "To be identified",
            "name_mapping": "To be mapped",
            "description_mapping": "To be mapped",
            "version_mapping": "To be mapped",
            "manufacturing_info": "To be extracted",
            "dependencies_info": "To be extracted",
            "tech_specs": "To be extracted",
            "overall_confidence": "To be calculated",
            "field_confidences": "To be calculated",
            "validation_notes": "To be documented",
            "final_manifest_json": "To be generated"
        }
        
        context_template = """
# OKH Manifest Generation Analysis
## Repository: {repo_name}
## Analysis Date: {timestamp}

## 1. Repository Structure Analysis
### Directory Tree:
{tree_output}

### Key Files Identified:
- README: {readme_path}
- Documentation: {doc_paths}
- Source Code: {source_paths}
- Configuration: {config_paths}

## 2. Content Analysis
### Project Type: {project_type}
### Domain: {domain}
### Key Technologies: {technologies}

## 3. Field Mapping Progress
### Direct Mappings:
- name: {name_mapping}
- description: {description_mapping}
- version: {version_mapping}

### Extracted Information:
- Manufacturing processes: {manufacturing_info}
- Dependencies: {dependencies_info}
- Technical specs: {tech_specs}

## 4. OKH Schema Mapping
### Required Fields Status:
- [ ] title
- [ ] version
- [ ] license
- [ ] licensor
- [ ] documentation_language
- [ ] function

### Optional Fields Status:
- [ ] description
- [ ] keywords
- [ ] manufacturing_processes
- [ ] materials

## 5. Quality Assessment
### Confidence Scores:
- Overall: {overall_confidence}
- Field-specific: {field_confidences}

### Validation Notes:
{validation_notes}

## 6. Final Manifest
{final_manifest_json}
"""
        
        content = context_template.format(**template_data)
        context_file.write_text(content)
        result.add_log(f"Created context file: {context_file}")
    
    async def _run_llm_analysis(self, project_data: ProjectData, context_file: Path, result: LayerResult):
        """Run LLM analysis with context file support"""
        try:
            # Build analysis prompt
            prompt = self._build_analysis_prompt(project_data, context_file)
            
            # Create LLM request config
            config = LLMRequestConfig(
                max_tokens=4000,
                temperature=0.1,  # Low temperature for consistent output
                timeout=60
            )
            
            # Execute LLM request
            response = await self.llm_service.generate(
                prompt=prompt,
                request_type=LLMRequestType.GENERATION,
                config=config
            )
            
            if response.status != LLMResponseStatus.SUCCESS:
                raise RuntimeError(f"LLM generation failed: {response.error_message}")
            
            # Parse response and extract manifest fields
            await self._parse_llm_response(response.content, result)
            
            result.add_log(f"LLM analysis completed successfully")
            
        except Exception as e:
            error_msg = f"LLM analysis failed: {str(e)}"
            result.add_error(error_msg)
            logger.error(error_msg, exc_info=True)
    
    def _build_analysis_prompt(self, project_data: ProjectData, context_file: Path) -> str:
        """Build the complete analysis prompt with schema reference"""
        # Get project information
        project_info = self._extract_project_info(project_data)
        
        return f"""
You are an expert OKH (Open Know-How) manifest generator specializing in open-source hardware projects. Your mission is to maximize interoperability and discoverability in the open-source hardware ecosystem.

## Core Objectives:
1. **Interoperability**: Create manifests that enable seamless integration with other hardware projects
2. **Discoverability**: Ensure projects can be easily found and understood by the community
3. **Standardization**: Follow OKH schema precisely for consistent data exchange
4. **Completeness**: Provide information for manufacturing and assembly

## Analysis Workflow:

### Phase 1: Repository Analysis
1. Use the context file: {context_file} as your scratchpad
2. Analyze the repository structure and content
3. Identify key files and directories
4. Document findings in the context file

### Phase 2: Content Extraction
1. Analyze README and documentation files
2. Extract technical specifications and requirements
3. Identify manufacturing processes and materials
4. Map dependencies and components
5. **CRITICAL: BOM Detection and Construction**
   - Look for explicit BOM files (bom.csv, bill_of_materials.txt, etc.)
   - If no explicit BOM found, construct BOM from parts lists, materials, and components mentioned in documentation
   - Extract part names, quantities, materials, and specifications
   - Map hardware components to OKH parts structure
6. **CRITICAL: Parts and Sub-parts Logic**
   - Identify main components (chassis, electronics, mechanical parts)
   - Distinguish between main parts and sub-components
   - Use file structure and documentation to determine part hierarchy
   - Map 3D models, PCBs, and assemblies to appropriate part categories
7. **CRITICAL: Software Repository Detection**
   - Look for software repository references in README
   - Detect patterns like "code can be found in [repository]" or "software repository"
   - Handle GitHub-specific patterns (separate repos for hardware/software)
   - Be context-aware: GitHub projects often separate hardware/software repos
8. Update context file with extracted information

### Phase 3: Schema Mapping
1. Reference the OKH schema for field requirements
2. Map extracted data to OKH fields
3. Ensure all required fields are populated
4. **CRITICAL: BOM Field Mapping**
   - If explicit BOM file found, reference it in bom field
   - If no explicit BOM, construct BOM from parts/materials analysis
   - Include all hardware components, quantities, and specifications
   - Format as URL to BOM file or parts list
5. **CRITICAL: Parts Field Population**
   - Map main hardware components to parts array
   - Include part names, IDs, source files (STL, CAD), materials, dimensions
   - Distinguish between main parts and sub-components
   - Use file structure to identify part relationships
6. **CRITICAL: Software Field Population**
   - Detect software repository references in README/documentation
   - Handle GitHub-specific patterns (separate hardware/software repos)
   - Include software repository URLs and descriptions
   - Be context-aware of platform differences (GitHub vs Thingiverse)
7. Validate field formats and content
8. Document mapping decisions in context file

### Phase 4: Quality Assurance
1. Verify completeness of all required fields
2. Check accuracy of extracted information
3. Ensure manufacturing notes are actionable
4. Validate dependency information
5. Confirm documentation links are functional

### Phase 5: Manifest Generation
1. Generate final OKH manifest JSON
2. Include confidence scores for each field
3. Document any assumptions or limitations
4. Update context file with final manifest
5. Return structured manifest with metadata

## Repository Data:
{json.dumps(project_info, indent=2)}

## ENHANCED ANALYSIS DATA - USE THIS DATA TO POPULATE FIELDS:
BOM Files Found: {len(project_info.get('bom_files', []))}
Part Files Found: {len(project_info.get('part_files', []))}
Software Indicators: {project_info.get('software_indicators', {})}

SPECIFIC BOM FILES TO USE:
{chr(10).join(project_info.get('bom_files', [])[:10])}

SPECIFIC PART FILES TO USE:
{chr(10).join(project_info.get('part_files', [])[:10])}

SPECIFIC SOFTWARE REFERENCES TO USE:
{chr(10).join(project_info.get('software_indicators', {}).get('software_references', [])[:5])}

MANDATORY REQUIREMENTS:
- You MUST use the BOM files listed above to populate the 'bom' field
- You MUST use the part files listed above to populate the 'parts' field  
- You MUST use the software references listed above to populate the 'software' field
- These fields CANNOT be empty or 'NOT_FOUND'
- If you cannot find specific data, construct reasonable entries based on the file names and project context

## OKH Schema Reference:
{self.okh_schema_prompt}

## Critical Field Distinctions - AVOID OVERLAP:

### description vs function vs intended_use:
- **description**: Comprehensive overview - "A 3D printable microscope with precise mechanical stage. Features include sub-micron positioning, multiple optics configurations, and excellent stability. Supports various optical setups from webcam lenses to 100x oil immersion objectives."
- **function**: Core functionality - "3D printable microscope with precise mechanical stage for sub-micron sample positioning and high-resolution imaging"
- **intended_use**: Use cases and applications - "Designed for researchers and educators conducting microscopy in laboratory settings, field studies, and educational demonstrations requiring precise sample positioning"

**CRITICAL**: These three fields must be DISTINCT and NON-OVERLAPPING:
- description = comprehensive overview (WHAT it is, features, capabilities)
- function = core functionality (WHAT it does, action-oriented)
- intended_use = use cases and applications (WHO uses it, FOR WHAT PURPOSE)

## Critical Field Examples:

### BOM Construction Examples:
- **Explicit BOM**: "bom.csv", "bill_of_materials.txt" → Reference in bom field
- **Implicit BOM**: Parts list in README → Construct BOM from documentation
- **Example**: "The rover requires: 6 wheels, 1 chassis, 2 motors, 1 Arduino" → Extract all components

### Parts Detection Examples:
- **Main Parts**: Chassis, wheels, motors, control board, mast
- **Sub-parts**: Screws, brackets, connectors, mounting hardware
- **File Mapping**: "chassis.stl" → chassis part, "wheel_assembly.step" → wheel assembly
- **Material Detection**: "3D printed PLA", "aluminum bracket", "steel screws"

### Software Repository Detection Examples:
- **GitHub Pattern**: "All code can be found in the osr-rover-code repository"
- **Direct Reference**: "Software repository: https://github.com/nasa-jpl/osr-rover-code"
- **Context Clues**: "Raspberry Pi", "ROS", "Python code", "Arduino sketches"
- **Platform Awareness**: GitHub projects often separate hardware/software repos

## Context File:
Use {context_file} as your scratchpad for analysis.

## Instructions:
1. **CRITICAL: Use the enhanced analysis data provided above**
2. **CRITICAL: BOM Field - DO NOT leave empty**
   - If bom_files array has items, reference the main BOM file
   - If no explicit BOM, construct from parts/materials in documentation
   - NEVER leave bom field empty - always provide a BOM reference or constructed BOM
3. **CRITICAL: Parts Field - DO NOT leave empty**
   - Use part_files array to identify main hardware components
   - Map 3D models (.stl, .step) to parts with materials and dimensions
   - Distinguish between main parts and sub-components
   - NEVER leave parts field empty - always populate with detected parts
4. **CRITICAL: Software Field - DO NOT leave empty**
   - Use software_indicators to find software repository references
   - Look for patterns like "code can be found in [repository]"
   - Handle GitHub-specific patterns (separate hardware/software repos)
   - NEVER leave software field empty - always populate with detected software
5. Create and populate the context file with your analysis
6. Follow the OKH schema precisely
7. Focus on interoperability and discoverability
8. Generate a complete, accurate OKH manifest
9. Return the manifest as valid JSON

**REMEMBER: The enhanced analysis has already detected BOM files, part files, and software references. Use this data!**
"""
    
    def _extract_project_info(self, project_data: ProjectData) -> Dict[str, Any]:
        """Extract project information for LLM analysis"""
        # Get README content
        readme_content = self._get_readme_content(project_data)
        
        # Get file structure
        file_structure = self._get_file_structure(project_data)
        
        # Get documentation
        documentation = [doc.title for doc in project_data.documentation]
        
        # Analyze files for BOM, parts, and software detection
        bom_files = self._find_bom_files(project_data)
        part_files = self._find_part_files(project_data)
        software_indicators = self._find_software_indicators(project_data)
        
        return {
            "name": project_data.metadata.get("name", "Unknown Project"),
            "url": project_data.url,
            "platform": project_data.platform.value if project_data.platform else "unknown",
            "description": project_data.metadata.get("description", ""),
            "readme_content": readme_content[:3000] if readme_content else None,  # Increased for better analysis
            "file_structure": file_structure,
            "documentation": documentation,
            "files_count": len(project_data.files),
            "documentation_count": len(project_data.documentation),
            "bom_files": bom_files,
            "part_files": part_files,
            "software_indicators": software_indicators
        }
    
    def _get_readme_content(self, project_data: ProjectData) -> Optional[str]:
        """Get README content from project data"""
        # Use shared utility to find README files
        readme_files = self.find_readme_files(project_data.files)
        if readme_files:
            return readme_files[0].content
        
        # Look in documentation
        for doc in project_data.documentation:
            if doc.title.lower().startswith('readme'):
                return doc.content
        
        return None
    
    def _get_file_structure(self, project_data: ProjectData) -> List[str]:
        """Get simplified file structure for LLM analysis"""
        structure = []
        for file_info in project_data.files[:50]:  # Limit to first 50 files
            structure.append(file_info.path)
        return structure
    
    def _find_bom_files(self, project_data: ProjectData) -> List[str]:
        """Find BOM-related files in the project"""
        bom_patterns = [
            'bom', 'bill_of_materials', 'parts_list', 'components',
            'materials', 'inventory', 'shopping_list'
        ]
        
        bom_files = []
        for file_info in project_data.files:
            file_path_lower = file_info.path.lower()
            for pattern in bom_patterns:
                if pattern in file_path_lower:
                    bom_files.append(file_info.path)
                    break
        
        return bom_files
    
    def _find_part_files(self, project_data: ProjectData) -> List[str]:
        """Find part-related files (3D models, CAD files, etc.)"""
        part_extensions = ['.stl', '.step', '.stp', '.obj', '.ply', '.3mf', '.cad', '.dxf']
        part_keywords = ['part', 'component', 'assembly', 'model', 'design']
        
        part_files = []
        for file_info in project_data.files:
            file_path_lower = file_info.path.lower()
            
            # Check for part file extensions
            if any(file_path_lower.endswith(ext) for ext in part_extensions):
                part_files.append(file_info.path)
                continue
            
            # Check for part-related keywords in path
            if any(keyword in file_path_lower for keyword in part_keywords):
                part_files.append(file_info.path)
        
        return part_files[:20]  # Limit to first 20 part files
    
    def _find_software_indicators(self, project_data: ProjectData) -> Dict[str, Any]:
        """Find software-related indicators in the project"""
        software_keywords = [
            'code', 'software', 'firmware', 'arduino', 'raspberry', 'pi',
            'python', 'cpp', 'c++', 'javascript', 'ros', 'linux', 'git'
        ]
        
        software_files = []
        software_references = []
        
        # Check file extensions
        software_extensions = ['.py', '.cpp', '.c', '.js', '.java', '.ino', '.sh', '.bash']
        
        for file_info in project_data.files:
            file_path_lower = file_info.path.lower()
            
            # Check for software file extensions
            if any(file_path_lower.endswith(ext) for ext in software_extensions):
                software_files.append(file_info.path)
            
            # Check for software keywords in path
            if any(keyword in file_path_lower for keyword in software_keywords):
                software_files.append(file_info.path)
        
        # Check README content for software repository references
        readme_content = self._get_readme_content(project_data)
        if readme_content:
            readme_lower = readme_content.lower()
            
            # Look for repository references
            import re
            repo_patterns = [
                r'code can be found in.*?repository',
                r'software.*?repository',
                r'github\.com/[^/\s]+/[^/\s]+',
                r'git\.com/[^/\s]+/[^/\s]+'
            ]
            
            for pattern in repo_patterns:
                matches = re.findall(pattern, readme_lower)
                software_references.extend(matches)
        
        return {
            "software_files": software_files[:10],  # Limit to first 10
            "software_references": software_references,
            "has_software_files": len(software_files) > 0,
            "has_software_references": len(software_references) > 0
        }
    
    async def _parse_llm_response(self, response_content: str, result: LayerResult):
        """Parse LLM response and extract manifest fields"""
        try:
            # Try to extract JSON from response with multiple strategies
            manifest_json = self._extract_json_from_response(response_content)
            
            if manifest_json:
                # Try to parse, with recovery attempts for common issues
                manifest_data = self._parse_json_with_recovery(manifest_json)
                
                if manifest_data:
                    # Extract fields from manifest data
                    await self._extract_fields_from_manifest(manifest_data, result)
                else:
                    # Failed to parse even with recovery - try to extract fields from partial JSON
                    logger.warning(
                        "JSON parsing failed even with recovery attempts, attempting partial field extraction. "
                        f"Extracted JSON (first 500 chars): {manifest_json[:500]}"
                    )
                    logger.debug(f"Full extracted JSON length: {len(manifest_json)} characters")
                    # Try to extract specific fields from the partial JSON string using regex
                    await self._extract_fields_from_partial_json(manifest_json, result)
                    # Also try text extraction as fallback for any missing fields
                    await self._extract_fields_from_text(response_content, result)
            else:
                # No JSON found - try to extract fields from text
                await self._extract_fields_from_text(response_content, result)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}")
            logger.debug(f"JSON error at line {e.lineno}, column {e.colno}: {e.msg}")
            await self._extract_fields_from_text(response_content, result)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            result.add_error(f"Failed to parse LLM response: {e}")
    
    def _extract_json_from_response(self, response_content: str) -> Optional[str]:
        """
        Extract JSON from LLM response using multiple strategies.
        
        Args:
            response_content: Raw LLM response content
            
        Returns:
            Extracted JSON string or None if no JSON found
        """
        # Strategy 1: Find JSON between first { and last }
        json_start = response_content.find('{')
        json_end = response_content.rfind('}')
        
        if json_start != -1 and json_end > json_start:
            extracted = response_content[json_start:json_end + 1]
            
            # Strategy 2: Try to find JSON block (between code fences or after keywords)
            # Check if we have markdown code blocks
            code_block_markers = ['```json', '```JSON', '```']
            for marker in code_block_markers:
                if marker in response_content:
                    start_idx = response_content.find(marker)
                    if start_idx != -1:
                        start_idx = response_content.find('\n', start_idx) + 1
                        end_marker = response_content.find('```', start_idx)
                        if end_marker != -1:
                            block_json = response_content[start_idx:end_marker].strip()
                            # Prefer code block extraction if it looks valid
                            if '{' in block_json and '}' in block_json:
                                return block_json
            
            return extracted
        
        # Strategy 3: Look for JSON after common keywords
        keywords = ['```json', '```JSON', 'JSON:', 'json:', 'manifest:', 'Manifest:']
        for keyword in keywords:
            idx = response_content.find(keyword)
            if idx != -1:
                # Find the next {
                json_start = response_content.find('{', idx)
                if json_start != -1:
                    json_end = response_content.rfind('}', json_start)
                    if json_end > json_start:
                        return response_content[json_start:json_end + 1]
        
        return None
    
    def _parse_json_with_recovery(self, json_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON with recovery attempts for common issues.
        
        Args:
            json_str: JSON string to parse
            
        Returns:
            Parsed JSON dict or None if parsing fails
        """
        # First try: Direct parse
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Recovery attempt 1: Fix trailing commas before } or ]
        try:
            fixed = self._fix_trailing_commas(json_str)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
        
        # Recovery attempt 2: Fix missing commas between object properties
        try:
            fixed = self._fix_missing_commas(json_str)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
        
        # Recovery attempt 3: Remove comments (// and /* */)
        try:
            fixed = self._remove_json_comments(json_str)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
        
        # Recovery attempt 4: Apply multiple fixes in combination
        # This handles cases where JSON has multiple issues (e.g., comments + trailing commas)
        try:
            fixed = self._remove_json_comments(json_str)
            fixed = self._fix_trailing_commas(fixed)
            fixed = self._fix_missing_commas(fixed)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
        
        # Recovery attempt 5: Try to extract and parse top-level object only
        try:
            # Sometimes LLM includes extra text - try to extract just the main object
            json_start = json_str.find('{')
            json_end = json_str.rfind('}')
            if json_start != -1 and json_end > json_start:
                isolated = json_str[json_start:json_end + 1]
                # Apply fixes to isolated JSON too
                try:
                    return json.loads(isolated)
                except json.JSONDecodeError:
                    fixed = self._remove_json_comments(isolated)
                    fixed = self._fix_trailing_commas(fixed)
                    fixed = self._fix_missing_commas(fixed)
                    return json.loads(fixed)
        except json.JSONDecodeError:
            pass
        
        # Log the actual JSON string that failed (for debugging)
        logger.warning(
            f"All JSON recovery attempts failed. JSON string (first 1000 chars):\n{json_str[:1000]}"
        )
        logger.debug(f"Full JSON string length: {len(json_str)} characters")
        return None
    
    def _fix_trailing_commas(self, json_str: str) -> str:
        """Fix trailing commas before } or ]"""
        import re
        # Remove trailing commas before closing braces/brackets
        fixed = re.sub(r',(\s*[}\]])', r'\1', json_str)
        return fixed
    
    def _fix_missing_commas(self, json_str: str) -> str:
        """Fix missing commas between object properties and array elements"""
        import re
        
        # Pattern 1: This pattern was too aggressive and caused issues
        # Disabled - Pattern 3 handles missing commas more reliably
        fixed = json_str
        
        # Pattern 2: Missing comma between properties on same line
        # Match: "key": value "next_key": - add comma before "next_key"
        fixed = re.sub(r'("\s*:\s*[^,}\]]+)\s+("[\w_]+"\s*:)', r'\1,\2', fixed)
        
        # Pattern 3: Missing comma after value before new property (multiline)
        # Match: "key": value\n    "next_key": - add comma at end of first line
        lines = fixed.split('\n')
        fixed_lines = []
        for i, line in enumerate(lines):
            if i < len(lines) - 1:
                next_line = lines[i + 1]
                # If current line has a property (contains :), doesn't end with comma/}/], 
                # and next line starts with a property (starts with quote followed by colon)
                if (':' in line and 
                    not line.rstrip().endswith(',') and 
                    not line.rstrip().endswith('}') and
                    not line.rstrip().endswith(']') and
                    re.match(r'^\s*"[^"]+"\s*:', next_line)):
                    # Add comma at end of current line
                    line = line.rstrip() + ','
            fixed_lines.append(line)
        
        fixed = '\n'.join(fixed_lines)
        
        # Pattern 4: Missing comma after closing brace/bracket before new property at same level
        # This pattern is disabled as it's too error-prone and causes more issues than it fixes
        # Pattern 3 already handles most missing comma cases between properties
        # The combination of comment removal, trailing comma fixes, and Pattern 3 should be sufficient
        
        return fixed
    
    def _remove_json_comments(self, json_str: str) -> str:
        """Remove JSON comments (// and /* */)"""
        import re
        # Remove // comments
        fixed = re.sub(r'//.*', '', json_str)
        # Remove /* */ comments
        fixed = re.sub(r'/\*.*?\*/', '', fixed, flags=re.DOTALL)
        return fixed
    
    async def _extract_fields_from_manifest(self, manifest_data: Dict[str, Any], result: LayerResult):
        """Extract fields from parsed manifest JSON"""
        # Required fields
        required_fields = ["title", "version", "license", "licensor", "documentation_language", "function"]
        
        for field in required_fields:
            if field in manifest_data:
                value = manifest_data[field]
                confidence = 0.9  # High confidence for LLM-generated fields
                result.add_field(
                    field,
                    value,
                    confidence,
                    "llm_generation",
                    "Generated by LLM analysis"
                )
        
        # Optional fields
        optional_fields = ["description", "keywords", "manufacturing_processes", "materials", "intended_use", "bom", "parts", "sub_parts", "software"]
        
        for field in optional_fields:
            if field in manifest_data:
                value = manifest_data[field]
                confidence = 0.8  # Good confidence for optional fields
                result.add_field(
                    field,
                    value,
                    confidence,
                    "llm_generation",
                    "Generated by LLM analysis"
                )
    
    async def _extract_fields_from_partial_json(self, json_str: str, result: LayerResult):
        """Extract fields from partial/invalid JSON using regex patterns"""
        import re
        
        # Extract function field - look for "function": "value"
        # Handle both single-line and multi-line values, escaped quotes, and truncated strings
        # Pattern: "function": "value" where value can contain escaped quotes and newlines
        # Also handle case where string might be truncated (no closing quote)
        function_pattern = r'"function"\s*:\s*"((?:[^"\\]|\\.|\\n)*?)(?:"|,|\n|$)'
        function_match = re.search(function_pattern, json_str, re.DOTALL)
        if function_match and not result.fields.get("function"):
            function_value = function_match.group(1)
            # Unescape common escape sequences
            function_value = function_value.replace('\\n', ' ').replace('\\"', '"').replace('\\\\', '\\')
            # Clean up whitespace
            function_value = ' '.join(function_value.split())
            # Only add if it looks reasonable (not a fragment)
            if len(function_value) > 20 and not any(phrase in function_value.lower() for phrase in ['disclaimed', 'warranty', 'license', 'respect of']):
                result.add_field("function", function_value, 0.85, "llm_partial_json", "Extracted from partial JSON")
        
        # Extract intended_use field
        intended_use_pattern = r'"intended_use"\s*:\s*"((?:[^"\\]|\\.|\\n)*?)(?:"|,|\n|$)'
        intended_use_match = re.search(intended_use_pattern, json_str, re.DOTALL)
        if intended_use_match and not result.fields.get("intended_use"):
            intended_use_value = intended_use_match.group(1)
            # Unescape common escape sequences
            intended_use_value = intended_use_value.replace('\\n', ' ').replace('\\"', '"').replace('\\\\', '\\')
            # Clean up whitespace
            intended_use_value = ' '.join(intended_use_value.split())
            # Only add if it looks reasonable
            if len(intended_use_value) > 20 and not any(phrase in intended_use_value.lower() for phrase in ['windows', 'mac', 'linux', 'disclaimed', 'respect of']):
                result.add_field("intended_use", intended_use_value, 0.85, "llm_partial_json", "Extracted from partial JSON")
        
        # Extract description field
        description_pattern = r'"description"\s*:\s*"((?:[^"\\]|\\.|\\n)*?)(?:"|,|\n|$)'
        description_match = re.search(description_pattern, json_str, re.DOTALL)
        if description_match and not result.fields.get("description"):
            description_value = description_match.group(1)
            # Unescape common escape sequences
            description_value = description_value.replace('\\n', ' ').replace('\\"', '"').replace('\\\\', '\\')
            # Clean up whitespace
            description_value = ' '.join(description_value.split())
            if len(description_value) > 30:
                result.add_field("description", description_value, 0.85, "llm_partial_json", "Extracted from partial JSON")
    
    async def _extract_fields_from_text(self, text: str, result: LayerResult):
        """Fallback: extract fields from text response"""
        # Only extract if we don't already have the field from partial JSON extraction
        lines = text.split('\n')
        
        for line in lines:
            if 'title:' in line.lower() and not result.fields.get("title"):
                title = line.split(':', 1)[1].strip()
                result.add_field("title", title, 0.7, "llm_text_extraction", "Extracted from text response")
            elif 'function:' in line.lower() and not result.fields.get("function"):
                function = line.split(':', 1)[1].strip()
                # Only add if it looks reasonable
                if len(function) > 20 and not any(phrase in function.lower() for phrase in ['disclaimed', 'warranty', 'license']):
                    result.add_field("function", function, 0.7, "llm_text_extraction", "Extracted from text response")
    
    async def _cleanup_context_file(self, context_file: Path):
        """Remove temporary context file (unless preserve_context is True)"""
        try:
            if context_file.exists():
                if self.preserve_context:
                    logger.info(f"Preserving context file for debugging: {context_file}")
                else:
                    context_file.unlink()
                    logger.debug(f"Cleaned up context file: {context_file}")
        except Exception as e:
            logger.warning(f"Failed to clean up context file {context_file}: {e}")
