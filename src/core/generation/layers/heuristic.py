"""
Heuristic Matching Layer for OKH manifest generation.

This layer applies rule-based pattern recognition to extract information
from file structures, naming conventions, and content patterns.
"""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...models.okh import DocumentationType
from ..models import AnalysisDepth, GenerationLayer, LayerConfig, ProjectData
from ..utils.file_categorization import (
    FileCategorizationResult,
    FileCategorizationRules,
)
from .base import BaseGenerationLayer, LayerResult

logger = logging.getLogger(__name__)


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

    def __init__(self, layer_config: Optional[LayerConfig] = None):
        super().__init__(GenerationLayer.HEURISTIC, layer_config)
        self.file_patterns = self._initialize_file_patterns()
        self.content_patterns = self._initialize_content_patterns()
        self.file_categorization_rules = FileCategorizationRules()

        # Initialize FileCategorizationService if LLM categorization is enabled
        self.file_categorization_service = None
        if self.layer_config and self.layer_config.file_categorization_config.get(
            "enable_llm_categorization", True
        ):
            try:
                from ...llm.providers.base import LLMProviderType
                from ...llm.service import LLMService, LLMServiceConfig
                from ..services.file_categorization_service import (
                    FileCategorizationService,
                )

                # Create LLM service if LLM is configured
                llm_service = None
                if self.layer_config.use_llm and self.layer_config.is_llm_configured():
                    try:
                        service_config = LLMServiceConfig(
                            name="HeuristicMatcher",
                            default_provider=LLMProviderType.ANTHROPIC,
                            default_model=None,  # Use centralized config
                            max_retries=3,
                            retry_delay=1.0,
                            timeout=60,
                            enable_fallback=True,
                            max_cost_per_request=1.0,
                            enable_cost_tracking=True,
                            max_concurrent_requests=5,
                        )
                        llm_service = LLMService("HeuristicMatcher", service_config)
                    except Exception as e:
                        logger.warning(
                            f"Failed to create LLM service for file categorization: {e}"
                        )

                # Create FileCategorizationService
                enable_caching = self.layer_config.file_categorization_config.get(
                    "enable_caching", True
                )
                min_confidence_for_llm = (
                    self.layer_config.file_categorization_config.get(
                        "min_confidence_for_llm", 0.8
                    )
                )
                self.file_categorization_service = FileCategorizationService(
                    llm_service=llm_service,
                    enable_caching=enable_caching,
                    min_confidence_for_llm=min_confidence_for_llm,
                )
                logger.debug("FileCategorizationService initialized with LLM support")
            except ImportError as e:
                logger.warning(f"FileCategorizationService not available: {e}")
            except Exception as e:
                logger.warning(f"Failed to initialize FileCategorizationService: {e}")

    def _initialize_file_patterns(self) -> List[FilePattern]:
        """Initialize file pattern matching rules"""
        return [
            # License files
            FilePattern(
                pattern=r"(?i)^(license|licence)(\.(txt|md))?$",
                field="license",
                confidence=0.9,
                extraction_method="license_file_detection",
                description="License file detection",
            ),
            # BOM files
            FilePattern(
                pattern=r"(?i)^(bom|bill.of.materials|materials)(\.(txt|md|csv|json))?$",
                field="bom",
                confidence=0.8,
                extraction_method="bom_file_detection",
                description="Bill of Materials file detection",
            ),
            # Manufacturing files
            FilePattern(
                pattern=r"(?i)^(manufacturing|production|assembly)(\.(txt|md))?$",
                field="manufacturing_files",
                confidence=0.7,
                extraction_method="manufacturing_file_detection",
                description="Manufacturing instruction file detection",
            ),
            # Design files
            FilePattern(
                pattern=r"(?i)^(design|cad|model)(\.(txt|md))?$",
                field="design_files",
                confidence=0.7,
                extraction_method="design_file_detection",
                description="Design file detection",
            ),
            # Tool lists
            FilePattern(
                pattern=r"(?i)^(tools|equipment|requirements)(\.(txt|md))?$",
                field="tool_list",
                confidence=0.7,
                extraction_method="tool_list_detection",
                description="Tool list file detection",
            ),
            # Assembly instructions
            FilePattern(
                pattern=r"(?i)^(assembly|build|make|instructions)(\.(txt|md))?$",
                field="making_instructions",
                confidence=0.8,
                extraction_method="assembly_instruction_detection",
                description="Assembly instruction file detection",
            ),
            # Operating instructions
            FilePattern(
                pattern=r"(?i)^(operating|usage|manual|user.guide)(\.(txt|md))?$",
                field="operating_instructions",
                confidence=0.8,
                extraction_method="operating_instruction_detection",
                description="Operating instruction file detection",
            ),
        ]

    def _initialize_content_patterns(self) -> Dict[str, List[Tuple[str, str, float]]]:
        """Initialize content pattern matching rules"""
        return {
            "function": [
                (
                    r"(?i)(?:function|purpose|what.is.it|what.does.it.do)[\s:]*([^.\n]{10,100})",
                    "function_description",
                    0.8,
                ),
                (
                    r"(?i)(?:this.project.aims.to|this.project.creates|this.project.builds)[\s:]*([^.\n]{10,100})",
                    "project_aims",
                    0.7,
                ),
                (
                    r"(?i)(?:is a\s+)([^.\n]{10,100})(?:\s+that|\s+which|\s+for)",
                    "is_a_description",
                    0.6,
                ),
            ],
            "intended_use": [
                (
                    r"(?i)(?:intended.use|use.case|application|for\s+)([^.\n]{10,100})",
                    "intended_use_direct",
                    0.9,
                ),
                (
                    r"(?i)(?:can.be.used|suitable.for|designed.for)[\s:]*([^.\n]{10,100})",
                    "intended_use_indirect",
                    0.7,
                ),
                (
                    r"(?i)(?:perfect.for|ideal.for|great.for)[\s:]*([^.\n]{10,100})",
                    "intended_use_positive",
                    0.6,
                ),
            ],
            "materials": [
                (
                    r"(?i)(?:bill.of.materials|bom|materials|parts|components)[\s:]*([^=]{10,200})",
                    "materials_direct",
                    0.8,
                ),
                (
                    r"(?i)(?:made.from|constructed.from|built.using)[\s:]*([^.\n]{10,100})",
                    "materials_construction",
                    0.7,
                ),
                (
                    r"(?i)(?:requires|needs|uses)[\s:]*([^.\n]{10,100})",
                    "materials_requirements",
                    0.6,
                ),
            ],
            "manufacturing_processes": [
                (r"(?i)(?:3d.print|3d.printing|printed)", "3D Printing", 0.9),
                (r"(?i)(?:laser.cut|laser.cutting)", "Laser cutting", 0.9),
                (r"(?i)(?:cnc|machining)", "CNC machining", 0.9),
                (r"(?i)(?:solder|soldering)", "Soldering", 0.8),
                (r"(?i)(?:assemble|assembly)", "Assembly", 0.7),
                (r"(?i)(?:fabricat|fabrication)", "Fabrication", 0.7),
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

            result.add_log(
                f"Heuristic layer processed {len(project_data.files)} files and {len(project_data.documentation)} documents"
            )

        except Exception as e:
            result.add_error(f"Heuristic processing failed: {str(e)}")

        return result

    async def _analyze_file_structure(
        self, project_data: ProjectData, result: LayerResult
    ):
        """
        Analyze file structure using two-layer file categorization.

        This method uses:
        - Layer 1: FileCategorizationRules for fast heuristic categorization
        - Layer 2: FileCategorizationService with LLM content analysis (if enabled and available)

        Layer 1 provides suggestions that Layer 2 (LLM) will refine when available.
        Falls back to Layer 1 if LLM is unavailable or disabled.
        """
        # Step 1: Generate Layer 1 suggestions for all files
        layer1_suggestions: Dict[str, FileCategorizationResult] = {}
        for file_info in project_data.files:
            file_path = file_info.path
            filename = Path(file_path).name

            # Use FileCategorizationRules to get Layer 1 suggestion
            categorization_result = self.file_categorization_rules.categorize_file(
                filename, file_path
            )
            layer1_suggestions[file_path] = categorization_result

        # Step 2: Use FileCategorizationService if available (Layer 1 + Layer 2 LLM)
        final_categorizations: Dict[str, FileCategorizationResult] = {}

        if self.file_categorization_service:
            try:
                # Get analysis depth from config
                analysis_depth_str = self.layer_config.file_categorization_config.get(
                    "analysis_depth", "shallow"
                )
                analysis_depth = AnalysisDepth(analysis_depth_str.lower())

                # Use FileCategorizationService to get final categorizations
                # This will use LLM if available, otherwise fall back to Layer 1
                final_categorizations = (
                    await self.file_categorization_service.categorize_files(
                        files=project_data.files,
                        layer1_suggestions=layer1_suggestions,
                        analysis_depth=analysis_depth,
                    )
                )
                logger.debug(
                    f"FileCategorizationService categorized {len(final_categorizations)} files"
                )
            except Exception as e:
                logger.warning(
                    f"FileCategorizationService failed, falling back to Layer 1: {e}"
                )
                # Fall back to Layer 1 suggestions
                final_categorizations = layer1_suggestions
        else:
            # No FileCategorizationService available, use Layer 1 directly
            final_categorizations = layer1_suggestions

        # Step 3: Group files by DocumentationType
        categorized_files: Dict[DocumentationType, List[Dict[str, Any]]] = {}
        excluded_count = 0

        for file_info in project_data.files:
            file_path = file_info.path
            filename = Path(file_path).name

            # Get final categorization result
            categorization_result = final_categorizations.get(file_path)
            if not categorization_result:
                # If no result, use Layer 1 suggestion
                categorization_result = layer1_suggestions.get(file_path)
                if not categorization_result:
                    # Skip if no categorization available
                    continue

            # Skip excluded files
            if categorization_result.excluded:
                excluded_count += 1
                continue

            # Group files by DocumentationType
            doc_type = categorization_result.documentation_type
            if doc_type not in categorized_files:
                categorized_files[doc_type] = []

            # Check if we should include file metadata (default: False for less verbose output)
            include_metadata = (
                project_data.metadata.get("_include_file_metadata", False)
                if project_data.metadata
                else False
            )

            # Create DocumentRef-like structure for result
            file_entry = {"title": filename, "path": file_path, "type": doc_type.value}

            # Only include metadata if verbose mode is enabled
            if include_metadata:
                detected_by = (
                    "file_categorization_service"
                    if self.file_categorization_service
                    else "file_categorization_rules"
                )
                file_entry["metadata"] = {
                    "detected_by": detected_by,
                    "confidence": categorization_result.confidence,
                    "reason": categorization_result.reason,
                }

            categorized_files[doc_type].append(file_entry)

        # Add categorized files to result with appropriate field names
        # Map DocumentationType to OKHManifest field names
        field_mapping = {
            DocumentationType.MANUFACTURING_FILES: "manufacturing_files",
            DocumentationType.DESIGN_FILES: "design_files",
            DocumentationType.MAKING_INSTRUCTIONS: "making_instructions",
            DocumentationType.OPERATING_INSTRUCTIONS: "operating_instructions",
            DocumentationType.PUBLICATIONS: "publications",
            DocumentationType.DOCUMENTATION_HOME: "documentation_home",
            DocumentationType.TECHNICAL_SPECIFICATIONS: "technical_specifications",
            DocumentationType.SOFTWARE: "software",
            DocumentationType.SCHEMATICS: "schematics",
            DocumentationType.MAINTENANCE_INSTRUCTIONS: "maintenance_instructions",
            DocumentationType.DISPOSAL_INSTRUCTIONS: "disposal_instructions",
            DocumentationType.RISK_ASSESSMENT: "risk_assessment",
        }

        # Add each category to result
        for doc_type, files in categorized_files.items():
            if not files:
                continue

            # Calculate average confidence for this category
            # Handle both cases: with and without metadata
            confidences = [f.get("metadata", {}).get("confidence", 0.8) for f in files]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.8

            # Get field name
            field_name = field_mapping.get(doc_type)
            if not field_name:
                # Skip unmapped types (shouldn't happen, but be safe)
                continue

            # Special handling for documentation_home (it's a string, not a list)
            if doc_type == DocumentationType.DOCUMENTATION_HOME:
                if files:
                    # Use the first README file path
                    result.add_field(
                        "documentation_home",
                        files[0]["path"],
                        avg_confidence,
                        "file_categorization_rules",
                        f"Detected documentation home: {files[0]['title']}",
                    )
            else:
                # Add list of files
                result.add_field(
                    field_name,
                    files,
                    avg_confidence,
                    "file_categorization_rules",
                    f"Detected {len(files)} {doc_type.value} files",
                )

        if excluded_count > 0:
            logger.debug(
                f"Excluded {excluded_count} files (workflow, testing data, correspondence)"
            )

    async def _parse_readme_content(
        self, project_data: ProjectData, result: LayerResult
    ):
        """Parse README content for key information"""
        readme_content = ""

        # Find README file
        for file_info in project_data.files:
            if file_info.path.lower().startswith("readme"):
                readme_content = file_info.content
                break

        # Also check documentation
        for doc_info in project_data.documentation:
            if doc_info.title.lower().startswith("readme"):
                readme_content = doc_info.content
                break

        if not readme_content:
            return

        # Extract function/purpose - look for project description
        # Exclude common license disclaimer phrases and assembly instructions
        license_phrases = [
            "disclaimed",
            "warranty",
            "liability",
            "copyright",
            "license",
            "permission",
            "granted",
            "redistribute",
            "modify",
            "derivative",
            "respect of",
            "without limitation",
            "as is",
            "as available",
        ]

        # Phrases that indicate assembly instructions, not function
        assembly_phrases = [
            "pushing",
            "inserting",
            "screwing",
            "mounting",
            "attaching",
            "assembling",
            "installing",
            "fitting",
            "placing",
            "positioning",
            "without damaging",
            "carefully",
            "gently",
            "step",
            "instructions",
        ]

        # Better patterns that capture complete sentences describing what the project does
        function_patterns = [
            # Pattern: "The [Project] is a [description]"
            r"(?i)(?:^|\n|\.)\s*the\s+([A-Z][^\s]{2,30})\s+is\s+(?:a|an)\s+([^.]{30,200})\.(?:\s|$)",
            # Pattern: "[Project] is a [description]"
            r"(?i)(?:^|\n|\.)\s*([A-Z][^\s]{2,30})\s+is\s+(?:a|an)\s+([^.]{30,200})\.(?:\s|$)",
            # Pattern: "This project aims to [description]"
            r"(?i)(?:^|\n|\.)\s*this\s+project\s+aims\s+to\s+([^.]{30,200})\.(?:\s|$)",
            # Pattern: "This project creates/builds [description]"
            r"(?i)(?:^|\n|\.)\s*this\s+project\s+(?:creates|builds|provides|enables)\s+([^.]{30,200})\.(?:\s|$)",
            # Pattern: "A [description] for [purpose]"
            r"(?i)(?:^|\n|\.)\s*(?:a|an)\s+([^.]{30,200})\s+(?:for|that|which)\s+([^.]{20,150})\.(?:\s|$)",
        ]

        for pattern in function_patterns:
            function_match = re.search(
                pattern, readme_content, re.DOTALL | re.MULTILINE
            )
            if function_match:
                # Handle patterns with different numbers of capturing groups
                try:
                    if function_match.groups() and len(function_match.groups()) >= 1:
                        # Use the last group (usually the most descriptive)
                        function_text = function_match.group(-1).strip()
                    else:
                        # No capturing groups, skip this pattern
                        continue
                except (IndexError, AttributeError) as e:
                    # Handle "no such group" or other regex errors gracefully
                    logger.debug(f"Regex group access error in function pattern: {e}")
                    continue
                    # Clean up the text - remove extra whitespace and newlines
                    function_text = re.sub(r"\s+", " ", function_text)

                    # Validate: must be a complete, meaningful sentence
                    # Check if it contains license disclaimer phrases - skip if so
                    if any(
                        phrase in function_text.lower() for phrase in license_phrases
                    ):
                        continue
                    # Check if it contains assembly instruction phrases - skip if so
                    if any(
                        phrase in function_text.lower() for phrase in assembly_phrases
                    ):
                        continue
                    # Must start with a capital letter (complete sentence)
                    if not function_text[0].isupper():
                        continue
                    # Must contain meaningful words (not just fragments)
                    words = function_text.split()
                    if len(words) < 5:  # Too short to be meaningful
                        continue
                    # Check for sentence completeness - should end with punctuation or be substantial
                    if len(function_text) < 30:  # Too short
                        continue

                    # Remove excessive punctuation but keep basic punctuation
                    function_text = re.sub(r"[^\w\s\-.,()]", "", function_text)
                    # Ensure we have a reasonable length and it's not just formatting
                    if (
                        len(function_text) > 30
                        and len(function_text) < 500
                        and not function_text.startswith("=")
                    ):
                        confidence = self.calculate_confidence(
                            "function", function_text, "content_analysis"
                        )
                        result.add_field(
                            "function",
                            function_text,
                            confidence,
                            "readme_function_extraction",
                            "Extracted from README project description",
                        )
                        break

        # Extract intended use - look for specific use cases
        # Exclude license disclaimer phrases and assembly instructions
        # (license_phrases and assembly_phrases defined above)
        intended_use_patterns = [
            # Pattern: "Designed for [use case]"
            r"(?i)(?:^|\n|\.)\s*designed\s+for\s+([^.]{30,200})\.(?:\s|$)",
            # Pattern: "Can be used for [use case]"
            r"(?i)(?:^|\n|\.)\s*can\s+be\s+used\s+(?:for|to|in)\s+([^.]{30,200})\.(?:\s|$)",
            # Pattern: "Suitable for [use case]"
            r"(?i)(?:^|\n|\.)\s*suitable\s+for\s+([^.]{30,200})\.(?:\s|$)",
            # Pattern: "Intended for [use case]"
            r"(?i)(?:^|\n|\.)\s*intended\s+for\s+([^.]{30,200})\.(?:\s|$)",
            # Pattern: "Ideal/Perfect for [use case]"
            r"(?i)(?:^|\n|\.)\s*(?:ideal|perfect|great)\s+for\s+([^.]{30,200})\.(?:\s|$)",
            # Pattern: "Use cases include [list]"
            r"(?i)(?:^|\n|\.)\s*use\s+cases?\s+(?:include|are)\s+([^.]{30,200})\.(?:\s|$)",
            # Pattern: "Applications include [list]"
            r"(?i)(?:^|\n|\.)\s*applications?\s+(?:include|are)\s+([^.]{30,200})\.(?:\s|$)",
        ]

        for pattern in intended_use_patterns:
            intended_use_match = re.search(
                pattern, readme_content, re.DOTALL | re.MULTILINE
            )
            if intended_use_match:
                # Handle patterns with different numbers of capturing groups
                try:
                    if (
                        intended_use_match.groups()
                        and len(intended_use_match.groups()) >= 1
                    ):
                        intended_use_text = intended_use_match.group(1).strip()
                    else:
                        # No capturing groups, skip this pattern
                        continue
                except (IndexError, AttributeError) as e:
                    # Handle "no such group" or other regex errors gracefully
                    logger.debug(f"Regex group access error in intended_use pattern: {e}")
                    continue
                    # Check if it contains license disclaimer phrases - skip if so
                    if any(
                        phrase in intended_use_text.lower()
                        for phrase in license_phrases
                    ):
                        continue
                    # Check if it contains assembly instruction phrases - skip if so
                    if any(
                        phrase in intended_use_text.lower()
                        for phrase in assembly_phrases
                    ):
                        continue
                    # Clean up the text - remove extra whitespace and newlines
                    intended_use_text = re.sub(r"\s+", " ", intended_use_text)
                    # Must contain meaningful words (not just fragments)
                    words = intended_use_text.split()
                    if len(words) < 4:  # Too short to be meaningful
                        continue
                    # Check for sentence completeness
                    if len(intended_use_text) < 25:  # Too short
                        continue
                    # Remove excessive punctuation but keep basic punctuation
                    intended_use_text = re.sub(r"[^\w\s\-.,()]", "", intended_use_text)
                    # Ensure we have a reasonable length and it's not just formatting
                    if (
                        len(intended_use_text) > 25
                        and len(intended_use_text) < 500
                        and not intended_use_text.startswith("=")
                    ):
                        confidence = self.calculate_confidence(
                            "intended_use", intended_use_text, "content_analysis"
                        )
                        result.add_field(
                            "intended_use",
                            intended_use_text,
                            confidence,
                            "readme_intended_use_extraction",
                            "Extracted from README intended use description",
                        )
                        break

        # Skip keywords extraction in heuristic layer - leave for NLP/LLM layers
        # Keywords require semantic understanding that regex cannot provide

        # Extract organization from URL
        if project_data.url:
            org_match = re.search(r"github\.com/([^/]+)/", project_data.url)
            if org_match:
                try:
                    organization = org_match.group(1)
                    if organization:
                        confidence = self.calculate_confidence(
                            "organization",
                            {"name": organization},
                            "url_organization_extraction",
                        )
                        result.add_field(
                            "organization",
                            {"name": organization},
                            confidence,
                            "url_organization_extraction",
                            f"Extracted from URL: {project_data.url}",
                        )
                except (IndexError, AttributeError) as e:
                    logger.debug(f"Error extracting organization from URL: {e}")

        # Extract materials from BOM components if available
        materials = self._extract_materials_from_bom(project_data)
        if materials:
            confidence = self.calculate_confidence(
                "materials", materials, "bom_materials_extraction"
            )
            result.add_field(
                "materials",
                materials,
                confidence,
                "bom_materials_extraction",
                "Extracted from BOM components",
            )
        else:
            # Fallback: Extract materials from README text
            materials = self._extract_materials_from_readme(readme_content)
            if materials:
                confidence = self.calculate_confidence(
                    "materials", materials, "readme_materials_extraction"
                )
                result.add_field(
                    "materials",
                    materials,
                    confidence,
                    "readme_materials_extraction",
                    "Extracted from README materials section",
                )

        # Extract tool list - use word boundaries to avoid partial matches
        # Look for sections like "Tools:", "Equipment:", "Required tools:", etc.
        tools_patterns = [
            r"(?i)\b(?:tools|equipment|required\s+tools|tools\s+required|tools\s+needed)[\s:]+([^\n]+)",
            r"(?i)##\s*(?:tools|equipment)[\s:]*\n([^\n#]+)",
            r"(?i)###\s*(?:tools|equipment)[\s:]*\n([^\n#]+)",
        ]

        tools = []
        for pattern in tools_patterns:
            tools_match = re.search(pattern, readme_content)
            if tools_match:
                try:
                    tools_text = tools_match.group(1).strip()
                except (IndexError, AttributeError) as e:
                    # Handle "no such group" or other regex errors gracefully
                    logger.debug(f"Regex group access error in tools pattern: {e}")
                    continue
                # Split on common delimiters
                tools = re.split(r"[,;|\n•\-\*]", tools_text)
                # Clean up each tool
                tools = [tool.strip() for tool in tools if tool.strip()]
                # Filter out invalid entries (too short, contains only punctuation, etc.)
                tools = [
                    tool
                    for tool in tools
                    if len(tool) > 2
                    and not tool.endswith(":")
                    and not re.match(r"^[^\w]+$", tool)  # Not just punctuation
                    and not tool.lower() in ["tool", "tools", "equipment", "required"]
                ]
                if tools:
                    confidence = self.calculate_confidence(
                        "tool_list", tools, "readme_tools_extraction"
                    )
                    result.add_field(
                        "tool_list",
                        tools,
                        confidence,
                        "readme_tools_extraction",
                        "Extracted from README tools section",
                    )
                    break

    async def _analyze_documentation(
        self, project_data: ProjectData, result: LayerResult
    ):
        """Analyze documentation files for additional information"""
        for doc_info in project_data.documentation:
            content = doc_info.content.lower()

            # Check for manufacturing processes using the same mapping as content patterns
            processes = self._extract_processes_from_text(content)

            if processes and not result.has_field("manufacturing_processes"):
                result.add_field(
                    "manufacturing_processes",
                    processes,
                    0.8,
                    "documentation_process_analysis",
                    f"Detected processes in {doc_info.title}",
                )

    async def _extract_from_file_names(
        self, project_data: ProjectData, result: LayerResult
    ):
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
                            confidence = self.calculate_confidence(
                                "license", license_type, pattern.extraction_method
                            )
                            result.add_field(
                                "license",
                                license_type,
                                confidence,
                                pattern.extraction_method,
                                f"Detected from {file_name}",
                            )
                    elif pattern.field == "bom":
                        # Extract BOM content
                        bom_content = file_info.content
                        materials = self._parse_bom_content(bom_content)
                        if materials:
                            confidence = self.calculate_confidence(
                                "materials", materials, pattern.extraction_method
                            )
                            result.add_field(
                                "materials",
                                materials,
                                confidence,
                                pattern.extraction_method,
                                f"Parsed from {file_name}",
                            )
                    else:
                        # For other fields, add the file to the appropriate list
                        file_entry = {
                            "title": Path(file_info.path).name,
                            "path": file_info.path,
                            "type": f"{pattern.field.replace('_', '-')}-files",
                            "metadata": {"detected_by": "file_pattern"},
                        }

                        if result.has_field(pattern.field):
                            # Add to existing list
                            existing = result.get_field(pattern.field).value
                            if isinstance(existing, list):
                                existing.append(file_entry)
                        else:
                            # Create new list
                            confidence = self.calculate_confidence(
                                pattern.field, [file_entry], pattern.extraction_method
                            )
                            result.add_field(
                                pattern.field,
                                [file_entry],
                                confidence,
                                pattern.extraction_method,
                                f"Detected from {file_name}",
                            )

    async def _apply_content_patterns(
        self, project_data: ProjectData, result: LayerResult
    ):
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
                    # Handle patterns with and without capturing groups
                    try:
                        if match.groups() and len(match.groups()) >= 1:
                            value = match.group(1).strip()
                        else:
                            # For patterns without capturing groups, use the full match
                            value = match.group(0).strip()
                    except (IndexError, AttributeError) as e:
                        # Handle "no such group" or other regex errors gracefully
                        logger.debug(f"Regex group access error in content pattern: {e}")
                        continue

                    # Special handling for different fields
                    if field == "keywords":
                        keywords = re.split(r"[,;|\n]", value)
                        keywords = [kw.strip() for kw in keywords if kw.strip()]
                        if keywords:
                            confidence = self.calculate_confidence(
                                field, keywords, "pattern_matching"
                            )
                            result.add_field(
                                field,
                                keywords,
                                confidence,
                                method,
                                f"Pattern: {pattern}",
                            )
                    elif field == "manufacturing_processes":
                        processes = self._extract_processes_from_text(value)
                        if processes:
                            confidence = self.calculate_confidence(
                                field, processes, "pattern_matching"
                            )
                            result.add_field(
                                field,
                                processes,
                                confidence,
                                method,
                                f"Pattern: {pattern}",
                            )
                    else:
                        confidence = self.calculate_confidence(
                            field, value, "pattern_matching"
                        )
                        result.add_field(
                            field, value, confidence, method, f"Pattern: {pattern}"
                        )
                    break  # Use first match

    def _parse_materials_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse materials from text"""
        materials = []

        # Look for structured material entries
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("=") or line.startswith("#"):
                continue

            # Skip markdown links and random text
            if "[" in line and "]" in line and "(" in line and ")" in line:
                continue
            if "http" in line or "www." in line:
                continue
            if len(line) < 10:  # Skip very short lines
                continue

            # Try to parse quantity and unit
            quantity_match = re.search(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)", line)
            if quantity_match:
                try:
                    quantity = float(quantity_match.group(1))
                    unit = quantity_match.group(2)
                except (IndexError, AttributeError, ValueError) as e:
                    # Handle "no such group" or parsing errors gracefully
                    logger.debug(f"Error parsing quantity/unit from line: {e}")
                    continue

                # Extract material name (everything before the quantity)
                material_name = line[: quantity_match.start()].strip()
                # Clean up material name
                material_name = re.sub(
                    r"^[\*\-\+\s]+", "", material_name
                )  # Remove bullet points
                material_name = re.sub(
                    r"\([^)]*\)", "", material_name
                )  # Remove parenthetical info
                material_name = material_name.strip()

                if material_name and len(material_name) > 3:
                    materials.append(
                        {
                            "material_id": material_name.upper()
                            .replace(" ", "_")
                            .replace("-", "_"),
                            "name": material_name,
                            "quantity": quantity,
                            "unit": unit,
                            "notes": "Extracted from README",
                        }
                    )

        return materials

    def _parse_bom_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse BOM content"""
        materials = []

        # Try different BOM formats
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # CSV format
            if "," in line:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    materials.append(
                        {
                            "material_id": parts[0].upper().replace(" ", "_"),
                            "name": parts[0],
                            "quantity": (
                                self._parse_quantity(parts[1]) if len(parts) > 1 else 1
                            ),
                            "unit": parts[2] if len(parts) > 2 else "pcs",
                            "notes": "Parsed from BOM file",
                        }
                    )
            # Simple list format
            else:
                quantity_match = re.search(
                    r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?\s*(.+)", line
                )
                if quantity_match:
                    try:
                        quantity = float(quantity_match.group(1))
                        unit = quantity_match.group(2) or "pcs"
                        name = quantity_match.group(3).strip()
                    except (IndexError, AttributeError, ValueError) as e:
                        # Handle "no such group" or parsing errors gracefully
                        logger.debug(f"Error parsing BOM line: {e}")
                        continue

                    materials.append(
                        {
                            "material_id": name.upper().replace(" ", "_"),
                            "name": name,
                            "quantity": quantity,
                            "unit": unit,
                            "notes": "Parsed from BOM file",
                        }
                    )

        return materials

    def _extract_license_type(self, content: str) -> Optional[str]:
        """Extract license type from license file content"""
        content_lower = content.lower()

        # Common license patterns
        license_patterns = {
            "MIT": r"mit\s+license",
            "Apache-2.0": r"apache\s+license",
            "GPL-3.0": r"gnu\s+general\s+public\s+license",
            "GPL-2.0": r"gnu\s+general\s+public\s+license\s+version\s+2",
            "BSD-3-Clause": r"bsd\s+3.clause",
            "BSD-2-Clause": r"bsd\s+2.clause",
            "CERN-OHL-S-2.0": r"cern\s+open\s+hardware\s+license",
            "CERN-OHL-P-2.0": r"cern\s+open\s+hardware\s+license\s+permissive",
            "CERN-OHL-W-2.0": r"cern\s+open\s+hardware\s+license\s+weakly.revocable",
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
            "3d print": "3D Printing",
            "3d printing": "3D Printing",
            "laser cut": "Laser cutting",
            "laser cutting": "Laser cutting",
            "cnc": "CNC machining",
            "machining": "CNC machining",
            "solder": "Soldering",
            "soldering": "Soldering",
            "assemble": "Assembly",
            "assembly": "Assembly",
        }

        for keyword, process in process_mapping.items():
            if keyword in text_lower and process not in processes:
                processes.append(process)

        return processes

    async def _extract_metadata_fields(
        self, project_data: ProjectData, result: LayerResult
    ):
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
                "Extracted from repository metadata or default",
            )

        # Extract documentation language - default to English for GitHub repositories
        if not result.has_field("documentation_language"):
            # For now, default to English for GitHub repositories
            # In the future, this could be enhanced with language detection
            confidence = self.calculate_confidence(
                "documentation_language", "en", "default_language_assignment"
            )
            result.add_field(
                "documentation_language",
                "en",
                confidence,
                "default_language_assignment",
                "Default to English for GitHub repositories",
            )

    def _parse_quantity(self, text: str) -> float:
        """Parse quantity from text"""
        try:
            # Remove non-numeric characters except decimal point
            cleaned = re.sub(r"[^\d.]", "", text)
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
                component_names = self._extract_component_names_from_bom(
                    file_info.content
                )
                for name in component_names:
                    material = self._classify_component_material(name)
                    if material:
                        materials.add(material)

        return list(materials) if materials else []

    def _extract_component_names_from_bom(self, bom_content: str) -> List[str]:
        """Extract component names from BOM content"""
        component_names = []

        # Look for markdown table rows or list items
        lines = bom_content.split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Check for markdown table rows (| component | quantity |)
            if "|" in line:
                parts = [part.strip() for part in line.split("|")]
                # Skip header rows and separator rows
                if len(parts) >= 3 and not any(
                    char in parts[1].lower()
                    for char in ["component", "part", "item", "name", "---", "==="]
                ):
                    component_names.append(
                        parts[1]
                    )  # Second column is usually component name

            # Check for list items (- component name)
            elif line.startswith("-") or line.startswith("*"):
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
            ("brass", ["brass"]),
            ("copper", ["copper", "cu "]),
            ("aluminum", ["aluminum", "aluminium", "al ", "al-"]),
            ("steel", ["stainless steel", "steel"]),  # stainless steel before steel
            ("PLA", ["pla", "polylactic acid"]),
            ("ABS", ["abs", "acrylonitrile butadiene styrene"]),
            ("PETG", ["petg", "pet-g"]),
            ("TPU", ["tpu", "thermoplastic polyurethane"]),
            ("wood", ["wood", "plywood", "mdf", "oak", "pine"]),
            ("acrylic", ["acrylic", "plexiglass", "pmma"]),
            # Component types
            (
                "electronics",
                [
                    "arduino",
                    "raspberry pi",
                    "sensor",
                    "motor",
                    "servo",
                    "led",
                    "resistor",
                    "capacitor",
                    "transistor",
                    "ic",
                    "microcontroller",
                ],
            ),
            ("fasteners", ["screw", "bolt", "nut", "washer", "rivet", "pin"]),
            ("cables", ["cable", "wire", "connector", "jack", "plug"]),
            ("bearings", ["bearing", "ball bearing", "roller bearing"]),
            ("springs", ["spring", "coil spring", "tension spring"]),
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
            r"(?i)parts[^=]*\n(.*?)(?=\n\n|\n[A-Z]|\n#|\n\*\*|\Z)",
        ]

        for pattern in materials_patterns:
            materials_match = re.search(pattern, readme_content, re.DOTALL)
            if materials_match:
                try:
                    materials_text = materials_match.group(1).strip()
                except (IndexError, AttributeError) as e:
                    # Handle "no such group" or other regex errors gracefully
                    logger.debug(f"Regex group access error in materials pattern: {e}")
                    continue
                # Clean up the text
                materials_text = re.sub(
                    r"^=+\s*$", "", materials_text, flags=re.MULTILINE
                )
                materials_text = re.sub(
                    r"^\s*\n", "", materials_text, flags=re.MULTILINE
                )

                if len(materials_text) > 20 and not materials_text.startswith("="):
                    # Extract component names from the text
                    component_names = self._extract_component_names_from_bom(
                        materials_text
                    )
                    for name in component_names:
                        material = self._classify_component_material(name)
                        if material:
                            materials.add(material)
                    break

        return list(materials) if materials else []
