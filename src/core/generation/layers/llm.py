"""
LLM Generation Layer for OKH manifest generation.

This layer uses Large Language Models for advanced content analysis and field extraction.
It provides sophisticated understanding of project content and can generate high-quality
manifest fields through natural language processing.

The layer implements the Enhanced LLM Agent Prompt Engineering Strategy with:
- Context file management for transparent analysis
- Schema-aware prompting for accurate field mapping
- Integration with the LLM service for provider management
- Comprehensive validation and quality assurance
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
    - Comprehensive validation and quality assurance
    
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
            # Create LLM service configuration
            service_config = LLMServiceConfig(
                name="LLMGenerationLayer",
                default_provider=LLMProviderType.ANTHROPIC,
                default_model="claude-3-5-sonnet-20241022",
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
- **Purpose**: Brief description of what the project does
- **Format**: Concise functional description
- **Example**: "Environmental monitoring sensor node"
- **Mapping Strategy**: Extract from README, project description, or code analysis

## Optional Fields

### description (string, optional)
- **Purpose**: Detailed project description
- **Format**: Comprehensive description of what the project does
- **Example**: "A low-power IoT sensor node based on Arduino with environmental monitoring capabilities"
- **Mapping Strategy**: Combine README content, project documentation, and code analysis

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
4. **Completeness**: Provide comprehensive information for manufacturing and assembly

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
5. Update context file with extracted information

### Phase 3: Schema Mapping
1. Reference the OKH schema for field requirements
2. Map extracted data to OKH fields
3. Ensure all required fields are populated
4. Validate field formats and content
5. Document mapping decisions in context file

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

## OKH Schema Reference:
{self.okh_schema_prompt}

## Context File:
Use {context_file} as your scratchpad for analysis.

## Instructions:
1. Create and populate the context file with your analysis
2. Follow the OKH schema precisely
3. Focus on interoperability and discoverability
4. Generate a complete, accurate OKH manifest
5. Return the manifest as valid JSON

Begin analysis now.
"""
    
    def _extract_project_info(self, project_data: ProjectData) -> Dict[str, Any]:
        """Extract project information for LLM analysis"""
        # Get README content
        readme_content = self._get_readme_content(project_data)
        
        # Get file structure
        file_structure = self._get_file_structure(project_data)
        
        # Get documentation
        documentation = [doc.title for doc in project_data.documentation]
        
        return {
            "name": project_data.metadata.get("name", "Unknown Project"),
            "url": project_data.url,
            "platform": project_data.platform.value if project_data.platform else "unknown",
            "description": project_data.metadata.get("description", ""),
            "readme_content": readme_content[:2000] if readme_content else None,  # Truncate for prompt
            "file_structure": file_structure,
            "documentation": documentation,
            "files_count": len(project_data.files),
            "documentation_count": len(project_data.documentation)
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
    
    async def _parse_llm_response(self, response_content: str, result: LayerResult):
        """Parse LLM response and extract manifest fields"""
        try:
            # Try to extract JSON from response
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                manifest_json = response_content[json_start:json_end]
                manifest_data = json.loads(manifest_json)
                
                # Extract fields from manifest data
                await self._extract_fields_from_manifest(manifest_data, result)
            else:
                # Fallback: try to extract fields from text
                await self._extract_fields_from_text(response_content, result)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}")
            await self._extract_fields_from_text(response_content, result)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            result.add_error(f"Failed to parse LLM response: {e}")
    
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
        optional_fields = ["description", "keywords", "manufacturing_processes", "materials", "intended_use"]
        
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
    
    async def _extract_fields_from_text(self, text: str, result: LayerResult):
        """Fallback: extract fields from text response"""
        # Simple text-based extraction as fallback
        lines = text.split('\n')
        
        for line in lines:
            if 'title:' in line.lower():
                title = line.split(':', 1)[1].strip()
                result.add_field("title", title, 0.7, "llm_text_extraction", "Extracted from text response")
            elif 'function:' in line.lower():
                function = line.split(':', 1)[1].strip()
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
