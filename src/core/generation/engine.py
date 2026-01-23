"""
Generation Engine for OKH manifest generation.

This module provides the main orchestration engine that coordinates all generation
layers and manages progressive enhancement to create OKH manifests from project data.
The engine supports both synchronous and asynchronous processing, with
error handling and quality assessment.

Key Features:
- Multi-layer processing with progressive enhancement
- Async support for concurrent layer processing
- Error handling and recovery
- Quality assessment and reporting
- LLM layer integration with fallback mechanisms
- BOM normalization and processing
- Extensible architecture for new layers

The engine follows the incremental development principle, making small, focused
changes while maintaining backward compatibility.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .layers.direct import DirectMatcher
from .layers.heuristic import HeuristicMatcher
from .layers.nlp import NLPMatcher
from .models import (
    FieldGeneration,
    GenerationLayer,
    LayerConfig,
    ManifestGeneration,
    ProjectData,
    QualityReport,
)
from .quality import QualityAssessor

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class EngineMetrics:
    """Metrics for tracking engine performance and usage"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_processing_time: float = 0.0
    layer_usage_counts: Dict[str, int] = None
    error_counts: Dict[str, int] = None

    def __post_init__(self):
        if self.layer_usage_counts is None:
            self.layer_usage_counts = {}
        if self.error_counts is None:
            self.error_counts = {}


class GenerationEngine:
    """
    Main orchestration engine for OKH manifest generation.

    This class coordinates all generation layers and manages the progressive
    enhancement process to create high-quality OKH manifests from project data.
    It supports both synchronous and asynchronous processing with error handling
    and quality assessment.

    The engine follows a multi-layer approach:
    1. Direct mapping from platform metadata
    2. Heuristic pattern recognition
    3. Natural language processing
    4. Large language model analysis (when configured)
    5. BOM normalization and processing
    6. Quality assessment and reporting

    Attributes:
        config: Layer configuration for the engine
        _matchers: Dictionary of initialized layer matchers
        _quality_assessor: Quality assessment component
        _required_fields: List of required OKH manifest fields
        _metrics: Performance and usage metrics
    """

    def __init__(self, config: Optional[LayerConfig] = None):
        """
        Initialize the generation engine.

        Args:
            config: Layer configuration. If None, uses default configuration.

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If layer initialization fails
        """
        self.config = config or LayerConfig()
        self._validate_config()

        # Initialize layer matchers
        self._matchers = {}
        self._initialize_matchers()

        # Initialize quality assessor
        self._quality_assessor = QualityAssessor()

        # Required fields for OKH manifests
        self._required_fields = [
            "title",
            "version",
            "license",
            "licensor",
            "documentation_language",
            "function",
        ]

        # Initialize metrics
        self._metrics = EngineMetrics()

        logger.info(f"GenerationEngine initialized with {len(self._matchers)} layers")

    def _validate_config(self):
        """Validate the layer configuration"""
        if not isinstance(self.config, LayerConfig):
            raise ValueError("Invalid layer configuration")

        # Check that at least one layer is enabled
        if not any(
            [
                self.config.use_direct,
                self.config.use_heuristic,
                self.config.use_nlp,
                self.config.use_llm,
            ]
        ):
            raise ValueError("At least one generation layer must be enabled")

    def _initialize_matchers(self):
        """
        Initialize available layer matchers based on configuration.

        This method initializes the appropriate layer matchers based on the
        configuration settings. It includes error handling for layer initialization
        failures and logging for debugging purposes.

        Raises:
            RuntimeError: If critical layer initialization fails
        """
        try:
            if self.config.use_direct:
                self._matchers[GenerationLayer.DIRECT] = DirectMatcher(self.config)
                logger.debug("Direct layer initialized")

            if self.config.use_heuristic:
                self._matchers[GenerationLayer.HEURISTIC] = HeuristicMatcher(
                    self.config
                )
                logger.debug("Heuristic layer initialized")

            if self.config.use_nlp:
                self._matchers[GenerationLayer.NLP] = NLPMatcher(self.config)
                logger.debug("NLP layer initialized")

            # Initialize LLM layer if configured and available
            if self.config.use_llm and self.config.is_llm_configured():
                try:
                    # Import LLM matcher dynamically to avoid import errors if not available
                    from .layers.llm import LLMGenerationLayer

                    self._matchers[GenerationLayer.LLM] = LLMGenerationLayer(
                        self.config
                    )
                    logger.info(
                        f"LLM layer initialized with provider: {self.config.get_llm_provider()}"
                    )
                except ImportError as e:
                    logger.warning(f"LLM layer not available: {e}")
                    if not self.config.llm_config.get("fallback_to_nlp", True):
                        raise RuntimeError("LLM layer required but not available")
                except Exception as e:
                    logger.error(f"Failed to initialize LLM layer: {e}")
                    if not self.config.llm_config.get("fallback_to_nlp", True):
                        raise RuntimeError(f"LLM layer initialization failed: {e}")
            elif self.config.use_llm:
                logger.warning("LLM layer enabled but not properly configured")

        except Exception as e:
            logger.error(f"Failed to initialize layer matchers: {e}")
            raise RuntimeError(f"Layer initialization failed: {e}")

        # Ensure at least one layer is available
        if not self._matchers:
            raise RuntimeError("No generation layers available")

        logger.info(f"Initialized {len(self._matchers)} generation layers")

    def generate_manifest(
        self, project_data: ProjectData, include_file_metadata: bool = False
    ) -> ManifestGeneration:
        """
        Generate an OKH manifest from project data (synchronous version).

        This method provides synchronous manifest generation with error handling
        and metrics tracking. For better performance with multiple layers,
        consider using the async version.

        Args:
            project_data: Raw project data from platform

        Returns:
            ManifestGeneration containing generated fields and metadata

        Raises:
            ValueError: If project data is invalid
            RuntimeError: If generation fails due to system errors
        """
        import time

        start_time = time.time()
        self._metrics.total_requests += 1

        try:
            # Validate input
            if project_data is None:
                raise ValueError("Project data cannot be None")

            if not isinstance(project_data, ProjectData):
                raise ValueError("Invalid project data")

            logger.info(f"Starting manifest generation for project: {project_data.url}")

            # Store generation options in project_data metadata for layers to access
            if not hasattr(project_data, "metadata") or project_data.metadata is None:
                project_data.metadata = {}
            project_data.metadata["_include_file_metadata"] = include_file_metadata

            # Initialize result containers
            generated_fields: Dict[str, FieldGeneration] = {}
            confidence_scores: Dict[str, float] = {}
            missing_fields: List[str] = []

            # Apply layers based on configuration
            if self.config.progressive_enhancement:
                generated_fields, confidence_scores, missing_fields = (
                    self._progressive_enhancement(
                        project_data,
                        generated_fields,
                        confidence_scores,
                        missing_fields,
                    )
                )
            else:
                generated_fields, confidence_scores, missing_fields = (
                    self._apply_all_layers(
                        project_data,
                        generated_fields,
                        confidence_scores,
                        missing_fields,
                    )
                )

            # Normalize fields before quality assessment (manufacturing_processes, etc.)
            generated_fields = self._normalize_generated_fields(generated_fields)

            # Validate and filter out obviously bad field values
            generated_fields = self._validate_field_values(generated_fields)

            # Ensure materials only come from BOM if BOM exists
            # This prevents false positives from text extraction (e.g., "electronics" mentioned in docs but not in BOM)
            # Note: The improved extraction logic (extracting from component names) is applied above in BOM normalization
            # This section ensures that if BOM exists, we use only BOM materials and remove false positives
            if "bom" in generated_fields:
                # Check if materials came from BOM normalization
                if "materials" in generated_fields:
                    materials_field = generated_fields.get("materials")
                    if isinstance(materials_field, FieldGeneration):
                        # If materials didn't come from BOM, but BOM exists, re-extract to ensure accuracy
                        if (
                            materials_field.source_layer
                            != GenerationLayer.BOM_NORMALIZATION
                        ):
                            bom_value = generated_fields.get("bom")
                            if isinstance(bom_value, FieldGeneration):
                                bom_data = bom_value.value
                                bom_obj = None

                                # Try to get BOM object
                                if hasattr(bom_data, "components"):
                                    bom_obj = bom_data
                                elif (
                                    isinstance(bom_data, dict)
                                    and "components" in bom_data
                                ):
                                    from ..models.bom import BillOfMaterials

                                    try:
                                        bom_obj = BillOfMaterials.from_dict(bom_data)
                                    except Exception as e:
                                        logger.debug(
                                            f"Could not reconstruct BOM object: {e}"
                                        )

                                if bom_obj and hasattr(bom_obj, "components"):
                                    # Re-extract using improved logic
                                    bom_materials = self._extract_materials_from_bom(
                                        bom_obj
                                    )
                                    if bom_materials:
                                        generated_fields["materials"] = FieldGeneration(
                                            value=bom_materials,
                                            confidence=0.9,
                                            source_layer=GenerationLayer.BOM_NORMALIZATION,
                                            generation_method="bom_materials_extraction",
                                            raw_source=f"Extracted from {len(bom_obj.components)} BOM components",
                                        )
                                        confidence_scores["materials"] = 0.9
                                    else:
                                        # BOM has no materials - remove false positives
                                        logger.debug(
                                            "BOM exists but no materials extracted; removing non-BOM materials"
                                        )
                                        generated_fields.pop("materials", None)
                                        confidence_scores.pop("materials", None)
                else:
                    # No materials yet, but BOM exists - extract from BOM
                    bom_value = generated_fields.get("bom")
                    if isinstance(bom_value, FieldGeneration):
                        bom_data = bom_value.value
                        bom_obj = None

                        if hasattr(bom_data, "components"):
                            bom_obj = bom_data
                        elif isinstance(bom_data, dict) and "components" in bom_data:
                            from ..models.bom import BillOfMaterials

                            try:
                                bom_obj = BillOfMaterials.from_dict(bom_data)
                            except Exception as e:
                                logger.debug(f"Could not reconstruct BOM object: {e}")

                        if bom_obj and hasattr(bom_obj, "components"):
                            bom_materials = self._extract_materials_from_bom(bom_obj)
                            if bom_materials:
                                generated_fields["materials"] = FieldGeneration(
                                    value=bom_materials,
                                    confidence=0.9,
                                    source_layer=GenerationLayer.BOM_NORMALIZATION,
                                    generation_method="bom_materials_extraction",
                                    raw_source=f"Extracted from {len(bom_obj.components)} BOM components",
                                )
                                confidence_scores["materials"] = 0.9

            # Update missing fields after normalization
            missing_fields = self._calculate_missing_fields(generated_fields)

            # Generate quality report
            quality_report = self._quality_assessor.generate_quality_report(
                generated_fields,
                confidence_scores,
                missing_fields,
                self._required_fields,
            )

            # Create result
            result = ManifestGeneration(
                project_data=project_data,
                generated_fields=generated_fields,
                confidence_scores=confidence_scores,
                quality_report=quality_report,
                missing_fields=missing_fields,
                include_file_metadata=include_file_metadata,
            )

            # Update metrics
            processing_time = time.time() - start_time
            self._update_metrics(processing_time, success=True)

            logger.info(
                f"Manifest generation completed in {processing_time:.2f}s with quality: {quality_report.overall_quality:.2f}"
            )

            return result

        except Exception as e:
            # Update metrics
            processing_time = time.time() - start_time
            self._update_metrics(processing_time, success=False, error=str(e))

            logger.error(
                f"Manifest generation failed after {processing_time:.2f}s: {e}"
            )
            raise

    def _update_metrics(
        self, processing_time: float, success: bool, error: Optional[str] = None
    ):
        """
        Update engine metrics with processing results.

        Args:
            processing_time: Time taken for processing in seconds
            success: Whether the processing was successful
            error: Error message if processing failed
        """
        if success:
            self._metrics.successful_requests += 1
        else:
            self._metrics.failed_requests += 1
            if error:
                error_type = (
                    type(error).__name__ if hasattr(error, "__name__") else "Unknown"
                )
                self._metrics.error_counts[error_type] = (
                    self._metrics.error_counts.get(error_type, 0) + 1
                )

        # Update average processing time
        total_requests = (
            self._metrics.successful_requests + self._metrics.failed_requests
        )
        if total_requests > 0:
            current_avg = self._metrics.average_processing_time
            self._metrics.average_processing_time = (
                current_avg * (total_requests - 1) + processing_time
            ) / total_requests

    def get_metrics(self) -> EngineMetrics:
        """
        Get current engine metrics.

        Returns:
            EngineMetrics object with current performance data
        """
        return self._metrics

    def reset_metrics(self):
        """Reset engine metrics to initial state."""
        self._metrics = EngineMetrics()
        logger.info("Engine metrics reset")

    async def generate_manifest_async(
        self, project_data: ProjectData, include_file_metadata: bool = False
    ) -> ManifestGeneration:
        """
        Async version of generate_manifest for concurrent layer processing.

        This method provides asynchronous manifest generation with better performance
        for multiple layers and error handling. It supports concurrent
        processing of independent layers and includes BOM normalization.

        Args:
            project_data: Raw project data from platform

        Returns:
            ManifestGeneration containing generated fields and metadata

        Raises:
            ValueError: If project data is invalid
            RuntimeError: If generation fails due to system errors
        """
        import time

        start_time = time.time()
        self._metrics.total_requests += 1

        try:
            # Validate input
            if project_data is None:
                raise ValueError("Project data cannot be None")

            if not isinstance(project_data, ProjectData):
                raise ValueError("Invalid project data")

            logger.info(
                f"Starting async manifest generation for project: {project_data.url}"
            )

            # Store generation options in project_data metadata for layers to access
            if not hasattr(project_data, "metadata") or project_data.metadata is None:
                project_data.metadata = {}
            project_data.metadata["_include_file_metadata"] = include_file_metadata

            # Initialize result containers
            generated_fields: Dict[str, FieldGeneration] = {}
            confidence_scores: Dict[str, float] = {}
            missing_fields: List[str] = []

            # Apply layers based on configuration
            if self.config.progressive_enhancement:
                generated_fields, confidence_scores, missing_fields = (
                    await self._progressive_enhancement_async(
                        project_data,
                        generated_fields,
                        confidence_scores,
                        missing_fields,
                    )
                )
            else:
                generated_fields, confidence_scores, missing_fields = (
                    await self._apply_all_layers_async(
                        project_data,
                        generated_fields,
                        confidence_scores,
                        missing_fields,
                    )
                )

            # Add BOM normalization if enabled
            full_bom_object = None
            if self.config.use_bom_normalization:
                try:
                    bom = await self._generate_normalized_bom(project_data)
                    full_bom_object = bom  # Store full BOM object for export
                    # Add BOM to generated fields
                    generated_fields["bom"] = FieldGeneration(
                        value=bom.to_dict(),
                        confidence=bom.metadata.get("overall_confidence", 0.8),
                        source_layer=GenerationLayer.BOM_NORMALIZATION,
                        generation_method="bom_normalization",
                        raw_source=f"Extracted from {len(bom.components)} sources",
                    )
                    confidence_scores["bom"] = bom.metadata.get(
                        "overall_confidence", 0.8
                    )

                    # Extract materials from BOM components using improved extraction logic
                    # This takes priority over other material extraction sources
                    materials = self._extract_materials_from_bom(bom)
                    if materials:
                        generated_fields["materials"] = FieldGeneration(
                            value=materials,
                            confidence=0.9,  # Higher confidence for BOM-based extraction
                            source_layer=GenerationLayer.BOM_NORMALIZATION,
                            generation_method="bom_materials_extraction",
                            raw_source=f"Extracted from {len(bom.components)} BOM components",
                        )
                        confidence_scores["materials"] = 0.9
                except Exception as e:
                    # Log error but don't fail the entire generation
                    logger.warning(f"BOM normalization failed: {e}")

            # Analyze parts directory for parts and sub_parts fields
            parts_analysis = self._analyze_parts_directory(project_data)
            if parts_analysis["parts"]:
                generated_fields["parts"] = FieldGeneration(
                    value=parts_analysis["parts"],
                    confidence=0.7,
                    source_layer=GenerationLayer.HEURISTIC,
                    generation_method="parts_directory_analysis",
                    raw_source=f"Analyzed {len(parts_analysis['parts'])} parts from directory structure",
                )
                confidence_scores["parts"] = 0.7

            if parts_analysis["sub_parts"]:
                generated_fields["sub_parts"] = FieldGeneration(
                    value=parts_analysis["sub_parts"],
                    confidence=0.7,
                    source_layer=GenerationLayer.HEURISTIC,
                    generation_method="parts_directory_analysis",
                    raw_source=f"Analyzed {len(parts_analysis['sub_parts'])} sub-parts from directory structure",
                )
                confidence_scores["sub_parts"] = 0.7

            # Generate quality report
            quality_report = self._quality_assessor.generate_quality_report(
                generated_fields,
                confidence_scores,
                missing_fields,
                self._required_fields,
            )

            # Create result
            result = ManifestGeneration(
                project_data=project_data,
                generated_fields=generated_fields,
                confidence_scores=confidence_scores,
                quality_report=quality_report,
                missing_fields=missing_fields,
                full_bom=full_bom_object,
                include_file_metadata=include_file_metadata,
            )

            # Update metrics
            processing_time = time.time() - start_time
            self._update_metrics(processing_time, success=True)

            logger.info(
                f"Async manifest generation completed in {processing_time:.2f}s with quality: {quality_report.overall_quality:.2f}"
            )

            return result

        except Exception as e:
            # Update metrics
            processing_time = time.time() - start_time
            self._update_metrics(processing_time, success=False, error=str(e))

            logger.error(
                f"Async manifest generation failed after {processing_time:.2f}s: {e}"
            )
            raise

    async def _progressive_enhancement_async(
        self,
        project_data: ProjectData,
        generated_fields: Dict[str, FieldGeneration],
        confidence_scores: Dict[str, float],
        missing_fields: List[str],
    ) -> Tuple[Dict[str, FieldGeneration], Dict[str, float], List[str]]:
        """
        Apply layers progressively with async support, stopping when quality threshold is met.

        Args:
            project_data: Raw project data
            generated_fields: Current generated fields
            confidence_scores: Current confidence scores
            missing_fields: Current missing fields

        Returns:
            Tuple of (generated_fields, confidence_scores, missing_fields)
        """
        # Get enabled layers in processing order
        enabled_layers = self.config.get_enabled_layers()

        for layer in enabled_layers:
            if layer not in self._matchers:
                continue

            try:
                # Apply layer
                layer_result = await self._matchers[layer].process(project_data)

                # Merge results
                for field_name, field_gen in layer_result.fields.items():
                    if field_name not in generated_fields:
                        # New field
                        generated_fields[field_name] = field_gen
                        confidence_scores[field_name] = field_gen.confidence
                    elif field_gen.confidence > generated_fields[field_name].confidence:
                        # Better confidence, replace
                        generated_fields[field_name] = field_gen
                        confidence_scores[field_name] = field_gen.confidence

                # Update layer usage metrics
                self._metrics.layer_usage_counts[layer.value] = (
                    self._metrics.layer_usage_counts.get(layer.value, 0) + 1
                )

                # Check if we should stop (all required fields have sufficient confidence)
                if self._should_stop_progressive_enhancement(confidence_scores):
                    logger.debug(
                        f"Progressive enhancement stopped at layer: {layer.value}"
                    )
                    break

            except Exception as e:
                logger.warning(f"Layer {layer.value} failed: {e}")
                # Continue with other layers
                continue

        # Update missing fields
        missing_fields = self._calculate_missing_fields(generated_fields)

        return generated_fields, confidence_scores, missing_fields

    async def _apply_all_layers_async(
        self,
        project_data: ProjectData,
        generated_fields: Dict[str, FieldGeneration],
        confidence_scores: Dict[str, float],
        missing_fields: List[str],
    ) -> Tuple[Dict[str, FieldGeneration], Dict[str, float], List[str]]:
        """
        Apply all enabled layers concurrently without progressive enhancement.

        Args:
            project_data: Raw project data
            generated_fields: Current generated fields
            confidence_scores: Current confidence scores
            missing_fields: Current missing fields

        Returns:
            Tuple of (generated_fields, confidence_scores, missing_fields)
        """
        # Get enabled layers
        enabled_layers = self.config.get_enabled_layers()

        # Create tasks for concurrent execution
        tasks = []
        for layer in enabled_layers:
            if layer in self._matchers:
                task = self._matchers[layer].process(project_data)
                tasks.append((layer, task))

        # Execute all layers concurrently
        results = await asyncio.gather(
            *[task for _, task in tasks], return_exceptions=True
        )

        # Process results
        for (layer, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.warning(f"Layer {layer.value} failed: {result}")
                continue

            # Merge results (keep highest confidence)
            # Special handling: prefer LLM-generated values for function and intended_use
            for field_name, field_gen in result.fields.items():
                if field_name not in generated_fields:
                    generated_fields[field_name] = field_gen
                    confidence_scores[field_name] = field_gen.confidence
                elif (
                    field_name in ["function", "intended_use"]
                    and layer == GenerationLayer.LLM
                ):
                    # Prefer LLM-generated values for these fields if LLM is available
                    # Even if confidence is slightly lower, LLM values are generally better
                    existing = generated_fields[field_name]
                    if existing.source_layer != GenerationLayer.LLM:
                        # Replace non-LLM value with LLM value
                        generated_fields[field_name] = field_gen
                        confidence_scores[field_name] = field_gen.confidence
                    elif field_gen.confidence > existing.confidence:
                        # LLM value with higher confidence
                        generated_fields[field_name] = field_gen
                        confidence_scores[field_name] = field_gen.confidence
                elif field_gen.confidence > generated_fields[field_name].confidence:
                    generated_fields[field_name] = field_gen
                    confidence_scores[field_name] = field_gen.confidence

            # Update layer usage metrics
            self._metrics.layer_usage_counts[layer.value] = (
                self._metrics.layer_usage_counts.get(layer.value, 0) + 1
            )

        # Update missing fields
        missing_fields = self._calculate_missing_fields(generated_fields)

        return generated_fields, confidence_scores, missing_fields

    async def _progressive_enhancement(
        self,
        project_data: ProjectData,
        generated_fields: Dict[str, FieldGeneration],
        confidence_scores: Dict[str, float],
        missing_fields: List[str],
    ) -> tuple:
        """
        Apply layers progressively, stopping when quality threshold is met.

        Args:
            project_data: Raw project data
            generated_fields: Current generated fields
            confidence_scores: Current confidence scores
            missing_fields: Current missing fields

        Returns:
            Tuple of (generated_fields, confidence_scores, missing_fields)
        """
        # Apply layers in priority order
        layer_order = [
            GenerationLayer.DIRECT,
            GenerationLayer.HEURISTIC,
            GenerationLayer.NLP,
            GenerationLayer.LLM,
        ]

        for layer in layer_order:
            if layer not in self._matchers:
                continue

            # Apply layer
            layer_result = await self._matchers[layer].process(project_data)

            # Merge results
            # Special handling: prefer LLM-generated values for function and intended_use
            for field_name, field_gen in layer_result.fields.items():
                if field_name not in generated_fields:
                    # New field
                    generated_fields[field_name] = field_gen
                    confidence_scores[field_name] = field_gen.confidence
                elif (
                    field_name in ["function", "intended_use"]
                    and layer == GenerationLayer.LLM
                ):
                    # Prefer LLM-generated values for these fields if LLM is available
                    # Even if confidence is slightly lower, LLM values are generally better
                    existing = generated_fields[field_name]
                    if existing.source_layer != GenerationLayer.LLM:
                        # Replace non-LLM value with LLM value
                        generated_fields[field_name] = field_gen
                        confidence_scores[field_name] = field_gen.confidence
                    elif field_gen.confidence > existing.confidence:
                        # LLM value with higher confidence
                        generated_fields[field_name] = field_gen
                        confidence_scores[field_name] = field_gen.confidence
                elif field_gen.confidence > generated_fields[field_name].confidence:
                    # Better confidence, replace
                    generated_fields[field_name] = field_gen
                    confidence_scores[field_name] = field_gen.confidence

            # Check if we should stop (all required fields have sufficient confidence)
            if self._should_stop_progressive_enhancement(confidence_scores):
                break

        # Update missing fields
        missing_fields = self._calculate_missing_fields(generated_fields)

        return generated_fields, confidence_scores, missing_fields

    async def _apply_all_layers(
        self,
        project_data: ProjectData,
        generated_fields: Dict[str, FieldGeneration],
        confidence_scores: Dict[str, float],
        missing_fields: List[str],
    ) -> tuple:
        """
        Apply all enabled layers without progressive enhancement.

        Args:
            project_data: Raw project data
            generated_fields: Current generated fields
            confidence_scores: Current confidence scores
            missing_fields: Current missing fields

        Returns:
            Tuple of (generated_fields, confidence_scores, missing_fields)
        """
        # Apply all enabled layers
        for layer, matcher in self._matchers.items():
            layer_result = await matcher.process(project_data)

            # Merge results (keep highest confidence)
            for field_name, field_gen in layer_result.fields.items():
                if field_name not in generated_fields:
                    generated_fields[field_name] = field_gen
                    confidence_scores[field_name] = field_gen.confidence
                elif field_gen.confidence > generated_fields[field_name].confidence:
                    generated_fields[field_name] = field_gen
                    confidence_scores[field_name] = field_gen.confidence

        # Update missing fields
        missing_fields = self._calculate_missing_fields(generated_fields)

        return generated_fields, confidence_scores, missing_fields

    def _should_stop_progressive_enhancement(
        self, confidence_scores: Dict[str, float]
    ) -> bool:
        """
        Check if progressive enhancement should stop.

        Args:
            confidence_scores: Current confidence scores

        Returns:
            True if should stop, False otherwise
        """
        # Check if all required fields have sufficient confidence
        for field in self._required_fields:
            if field not in confidence_scores:
                return False
            if confidence_scores[field] < self.config.min_confidence:
                return False

        return True

    def _calculate_missing_fields(
        self, generated_fields: Dict[str, FieldGeneration]
    ) -> List[str]:
        """
        Calculate which required fields are missing.

        Args:
            generated_fields: Current generated fields

        Returns:
            List of missing required field names
        """
        missing = []
        for field in self._required_fields:
            if field not in generated_fields:
                missing.append(field)

        return missing

    def _normalize_generated_fields(
        self, generated_fields: Dict[str, FieldGeneration]
    ) -> Dict[str, FieldGeneration]:
        """
        Normalize generated fields to improve quality.

        This method normalizes list fields like manufacturing_processes to:
        - Remove duplicates (case-insensitive)
        - Normalize to standard forms
        - Filter out non-contextual entries

        Args:
            generated_fields: Dictionary of field generations

        Returns:
            Normalized dictionary of field generations
        """
        normalized = generated_fields.copy()

        # Normalize manufacturing_processes
        if "manufacturing_processes" in normalized:
            processes_value = normalized["manufacturing_processes"].value
            if isinstance(processes_value, list):
                normalized_processes = self._normalize_manufacturing_processes(
                    processes_value
                )
                # Update the field generation with normalized value
                normalized["manufacturing_processes"] = FieldGeneration(
                    value=normalized_processes,
                    confidence=normalized["manufacturing_processes"].confidence,
                    source_layer=normalized["manufacturing_processes"].source_layer,
                    generation_method=normalized[
                        "manufacturing_processes"
                    ].generation_method,
                    raw_source=normalized["manufacturing_processes"].raw_source,
                )

        return normalized

    def _validate_field_values(
        self, generated_fields: Dict[str, FieldGeneration]
    ) -> Dict[str, FieldGeneration]:
        """
        Validate and filter out obviously bad field values.

        This method performs post-processing validation to catch bad extractions
        that might have passed through individual layers, such as:
        - Sentence fragments
        - License disclaimers
        - Assembly instructions
        - Software compatibility information (for hardware fields)

        Args:
            generated_fields: Dictionary of generated fields

        Returns:
            Dictionary with bad values filtered out
        """
        validated = {}

        # Phrases that indicate bad extractions
        bad_phrases = {
            "function": [
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
                "pushing",
                "inserting",
                "screwing",
                "mounting",
                "attaching",
                "without damaging",
                "carefully",
                "gently",
                "step",
                "instructions",
                "windows",
                "mac",
                "linux",
                "operating system",
                "compatible with",
                "manual",
                "automatic",
                "stage control",  # Too generic/fragment
            ],
            "intended_use": [
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
                "pushing",
                "inserting",
                "screwing",
                "mounting",
                "attaching",
                "without damaging",
                "carefully",
                "gently",
                "step",
                "instructions",
                "windows",
                "mac",
                "linux",
                "operating system",
                "compatible with",
                "software",
                "runs on",
                "supports",
                "platform",
            ],
        }

        for field_name, field_gen in generated_fields.items():
            if field_name not in bad_phrases:
                # No validation needed for this field
                validated[field_name] = field_gen
                continue

            value = field_gen.value

            # Skip validation for non-string values
            if not isinstance(value, str):
                validated[field_name] = field_gen
                continue

            value_lower = value.lower().strip()

            # Don't filter out LLM-generated values - trust the LLM's judgment
            # LLM values are generally better even if they contain some phrases
            if field_gen.source_layer == GenerationLayer.LLM:
                # Only filter LLM values if they're clearly wrong (very short or obvious fragments)
                if len(value.strip()) < 15:
                    logger.warning(
                        f"Filtered out too short LLM {field_name} value: {value[:50]}..."
                    )
                    continue
                # Allow LLM values through even if they contain some bad phrases
                validated[field_name] = field_gen
                continue

            # Check if value contains bad phrases (for non-LLM values)
            if any(phrase in value_lower for phrase in bad_phrases[field_name]):
                logger.warning(f"Filtered out bad {field_name} value: {value[:50]}...")
                continue

            # Additional validation for function and intended_use
            if field_name in ["function", "intended_use"]:
                # Must be a reasonable length
                if len(value.strip()) < 20:
                    logger.warning(
                        f"Filtered out too short {field_name} value: {value}"
                    )
                    continue

                # Must have reasonable word count
                words = value.split()
                if len(words) < 4:
                    logger.warning(
                        f"Filtered out too short {field_name} value: {value}"
                    )
                    continue

                # Must start with capital letter (complete sentence)
                if not value[0].isupper():
                    logger.warning(
                        f"Filtered out {field_name} value that doesn't start with capital: {value}"
                    )
                    continue

            # Value passed validation
            validated[field_name] = field_gen

        return validated

    def _normalize_manufacturing_processes(self, processes: List[str]) -> List[str]:
        """
        Normalize manufacturing processes list.

        - Removes duplicates (case-insensitive)
        - Normalizes to lowercase standard forms
        - Maps to canonical manufacturing process names
        - Filters out non-manufacturing verbs

        Args:
            processes: List of process names (may include duplicates, various cases)

        Returns:
            Normalized, deduplicated list of manufacturing processes
        """
        if not processes:
            return []

        # Map of common variations to canonical names
        canonical_map = {
            "print": "3d printing",
            "printing": "3d printing",
            "3d print": "3d printing",
            "3d printing": "3d printing",
            "fdm": "3d printing",
            "sla": "3d printing",
            "sls": "3d printing",
            "assemble": "assembly",
            "assembling": "assembly",
            "attach": "assembly",
            "attaching": "assembly",
            "install": "assembly",
            "installing": "assembly",
            "mount": "assembly",
            "mounting": "assembly",
            "test": None,  # Filter out generic "test" - not a manufacturing process
            "layer": None,  # Filter out generic "layer" - part of 3d printing but not a process
        }

        # Set of valid manufacturing processes (canonical names)
        valid_processes = {
            "3d printing",
            "laser cutting",
            "cnc machining",
            "soldering",
            "assembly",
            "welding",
            "cutting",
            "drilling",
            "bending",
            "grinding",
            "painting",
            "anodizing",
            "heat treatment",
            "injection molding",
            "casting",
            "forging",
            "machining",
            "turning",
            "milling",
            "sawing",
            "shearing",
            "plasma cutting",
            "tig welding",
            "mig welding",
            "arc welding",
            "polishing",
            "sanding",
            "coating",
            "annealing",
            "tempering",
            "quenching",
        }

        normalized = []
        seen = set()

        for process in processes:
            if not process or not isinstance(process, str):
                continue

            # Normalize to lowercase for comparison
            process_lower = process.lower().strip()

            # Skip empty strings
            if not process_lower:
                continue

            # Map to canonical name
            canonical = canonical_map.get(process_lower)

            # If explicitly mapped to None, filter it out
            if canonical is None and process_lower in canonical_map:
                continue

            # Use canonical name if mapped, otherwise use lowercase version
            final_name = canonical if canonical is not None else process_lower

            # Check if it's a valid manufacturing process
            # Allow if it's in valid_processes or contains manufacturing-related keywords
            is_valid = final_name in valid_processes or any(
                keyword in final_name
                for keyword in [
                    "print",
                    "cut",
                    "weld",
                    "machin",
                    "assemble",
                    "solder",
                    "drill",
                    "bend",
                    "grind",
                    "paint",
                    "cast",
                    "forge",
                    "mold",
                    "treat",
                ]
            )

            if not is_valid:
                continue

            # Deduplicate using lowercase comparison
            final_lower = final_name.lower()
            if final_lower not in seen:
                seen.add(final_lower)
                # Capitalize first letter for consistency
                normalized.append(final_name.title())

        return normalized

    async def _generate_normalized_bom(self, project_data: ProjectData):
        """
        Generate normalized BOM from project data.

        Args:
            project_data: Raw project data from platform

        Returns:
            BillOfMaterials object with normalized components
        """
        from .bom_models import BOMBuilder, BOMCollector, BOMProcessor

        # Collect BOM data from multiple sources
        collector = BOMCollector()
        sources = collector.collect_bom_data(project_data)

        # Process BOM data into components
        processor = BOMProcessor()
        components = processor.process_bom_sources(sources)

        # LLM Review Step (if enabled)
        if self.config.use_llm and self.config.is_llm_configured():
            try:
                components = await self._review_components_with_llm(components, sources)
            except Exception as e:
                # Log error but don't fail the entire generation
                logger.warning(
                    f"LLM component review failed: {e}, using all components"
                )
                # Continue with all components if LLM review fails

        # Build final BOM
        builder = BOMBuilder()
        project_name = project_data.metadata.get("name", "Project")
        bom = builder.build_bom(components, f"{project_name} BOM")

        return bom

    async def _review_components_with_llm(
        self,
        components: List[Any],
        sources: List[Any],
    ) -> List[Any]:
        """
        Review extracted components using LLM to filter invalid component names.

        Args:
            components: List of extracted Component objects
            sources: List of BOMSource objects (for context)

        Returns:
            Filtered list of valid Component objects
        """
        from ..llm.models.requests import LLMRequestType
        from ..llm.models.responses import LLMResponseStatus

        if not components:
            return components

        # Configuration constants
        # Increase max_tokens for large component lists to avoid truncation
        # With 65 components, JSON response can easily exceed 4000 tokens
        max_tokens = 8000  # Max tokens for response (increased from 4000)
        max_input_tokens = 200000  # Typical max context window (conservative estimate)

        prompt = None
        estimated_tokens = None

        try:
            # Get or create LLM service
            llm_service = await self._get_llm_service_for_review()

            # Build prompt
            component_list = self._format_components_for_prompt(components)
            source_excerpts = self._format_source_excerpts(sources, components)
            prompt = self._build_component_review_prompt(
                component_list, source_excerpts
            )

            # Estimate token count for the prompt
            estimated_tokens = self._estimate_token_count(prompt)

            # Check if input exceeds token limit
            if estimated_tokens > max_input_tokens:
                logger.error(
                    f"LLM component review skipped: Input prompt exceeds token limit. "
                    f"Estimated tokens: {estimated_tokens:,}, Max input tokens: {max_input_tokens:,}. "
                    f"Components: {len(components)}, Sources: {len(sources)}. "
                    f"Consider reducing the number of components or source excerpts."
                )
                return components  # Return all components if input too large

            # Call LLM
            from ..llm.models.requests import LLMRequestConfig

            request_config = LLMRequestConfig(
                max_tokens=max_tokens,  # Enough for JSON response (default 4000, may need increase for large component lists)
                temperature=0.1,  # Low temperature for consistent validation
            )

            response = await llm_service.generate(
                prompt=prompt,
                request_type=LLMRequestType.ANALYSIS,  # Use ANALYSIS for component review
                config=request_config,
            )

            # Parse response
            if response.status == LLMResponseStatus.SUCCESS:
                validated_components = self._parse_llm_validation_response(
                    response.content, components
                )
                logger.info(
                    f"LLM review: {len(validated_components)}/{len(components)} components validated "
                    f"(estimated input tokens: {estimated_tokens:,})"
                )
                return validated_components
            else:
                logger.warning(f"LLM validation failed: {response.error}")
                return components  # Return all if LLM fails

        except Exception as e:
            error_msg = str(e).lower()

            # Estimate tokens if we have the prompt (may not be available if error occurred early)
            if prompt is not None and estimated_tokens is None:
                estimated_tokens = self._estimate_token_count(prompt)

            # Check if error is related to token/context limits
            token_limit_keywords = [
                "token",
                "context length",
                "context window",
                "max tokens",
                "input too long",
                "exceeds",
                "limit",
                "too many tokens",
            ]

            if any(keyword in error_msg for keyword in token_limit_keywords):
                token_info = (
                    f"Estimated input tokens: {estimated_tokens:,}"
                    if estimated_tokens
                    else "Token count unavailable"
                )
                logger.error(
                    f"LLM component review failed due to token limit: {e}. "
                    f"{token_info}. "
                    f"Max tokens configured: {max_tokens:,}. "
                    f"Components: {len(components)}, Sources: {len(sources)}. "
                    f"Consider reducing the number of components or source excerpts, or increase max_tokens."
                )
            else:
                logger.warning(f"LLM component review error: {e}")

            return components  # Return all components on error

    async def _get_llm_service_for_review(self):
        """Get or create LLM service for component review."""
        from ..llm.service import LLMService, LLMServiceConfig
        from ..llm.providers.base import LLMProviderType

        # Try to reuse LLM service from LLM layer if available
        if GenerationLayer.LLM in self._matchers:
            llm_layer = self._matchers[GenerationLayer.LLM]
            if hasattr(llm_layer, "llm_service") and llm_layer.llm_service:
                # Initialize if needed
                if llm_layer.llm_service.status.value != "active":
                    await llm_layer.llm_service.initialize()
                return llm_layer.llm_service

        # Create temporary LLM service for review
        service_config = LLMServiceConfig(
            name="BOMComponentReview",
            default_provider=LLMProviderType.ANTHROPIC,
            max_retries=2,
            timeout=30,
        )
        llm_service = LLMService("BOMComponentReview", service_config)
        await llm_service.initialize()
        return llm_service

    def _format_components_for_prompt(self, components: List[Any]) -> str:
        """Format components list for LLM prompt."""
        lines = []
        for i, comp in enumerate(components, 1):
            source_info = comp.metadata.get("file_path", "unknown")
            confidence = comp.metadata.get("confidence", 0.0)
            lines.append(
                f"{i}. ID: {comp.id}\n"
                f"   Name: {comp.name}\n"
                f"   Quantity: {comp.quantity} {comp.unit}\n"
                f"   Source: {source_info}\n"
                f"   Confidence: {confidence:.2f}"
            )
        return "\n\n".join(lines)

    def _format_source_excerpts(self, sources: List[Any], components: List[Any]) -> str:
        """Extract and format relevant source excerpts."""
        # Map components to their sources
        source_map = {}
        for comp in components:
            file_path = comp.metadata.get("file_path")
            if file_path:
                if file_path not in source_map:
                    source_map[file_path] = []
                source_map[file_path].append(comp)

        # Extract excerpts from sources
        excerpts = []
        for source in sources:
            if source.file_path in source_map:
                # Extract first 2000 chars for context
                content = source.raw_content[:2000]
                excerpts.append(f"**{source.file_path}:**\n```\n{content}\n```")

        return "\n\n".join(excerpts) if excerpts else "No source excerpts available."

    def _build_component_review_prompt(
        self, component_list: str, source_excerpts: str
    ) -> str:
        """Build the LLM prompt for component review."""
        return f"""# BOM Component Validation Task

You are reviewing a list of components extracted from project documentation to identify which are valid hardware parts/components and which are false positives (instructions, units, commands, etc.).

## Task
Review each extracted component and determine if it represents a valid hardware part/component that should be included in a Bill of Materials (BOM).

## Valid Component Examples

Valid components are actual physical parts, materials, or hardware items:

✅ **Good Examples:**
- "M3x25mm hexagon head screws" - Specific hardware part
- "Arduino Nano" - Electronic component
- "12V DC power supply" - Power component
- "Header pins, 2.54mm pitch" - Connector component
- "Peristaltic pump with stepper motor" - Mechanical component
- "Barrel plug connector, 5.5mm x 2.1mm" - Connector with specifications
- "Circulating pump" - Mechanical component
- "Stepper motor cable" - Cable/connector component
- "20 gauge wire" - Material/component with specification
- "PCB board" - Electronic component

## Invalid Component Examples

Invalid components are instructions, units, commands, or non-physical items:

❌ **Bad Examples:**
- "slots." - Single word with punctuation, no context
- "inches" - Unit of measurement, not a component
- "command" - Action word, not a component
- "pin" - Too generic, no specification
- "P1" - Code reference, not a component name
- "units per minute" - Unit phrase, not a component
- "command, but there are some key differences..." - Sentence fragment
- "Version" - Generic word, not a component
- "to install" - Instruction phrase
- "and the" - Sentence fragment
- "G90G91 g-code parser state" - Software/instruction, not hardware

## Component List to Review

Below is the list of extracted components with their source information:

{component_list}

## Source Material Context

For reference, here are excerpts from the source documents where these components were extracted:

{source_excerpts}

## Output Format

Return a JSON object with the following structure:

```json
{{
  "valid_components": [
    {{
      "id": "component_id",
      "name": "component_name",
      "reason": "Brief explanation why this is valid"
    }}
  ],
  "invalid_components": [
    {{
      "id": "component_id",
      "name": "component_name",
      "reason": "Brief explanation why this is invalid (e.g., 'unit of measurement', 'instruction text', 'too generic')"
    }}
  ],
  "suggested_improvements": [
    {{
      "id": "component_id",
      "original_name": "original_name",
      "suggested_name": "improved_name",
      "reason": "Explanation of improvement"
    }}
  ]
}}
```

## Instructions

1. **Be strict** - Only include components that are clearly valid hardware parts
2. **Consider context** - Use source material to understand if a component is valid
3. **Filter aggressively** - When in doubt, exclude (better to have fewer valid components than many invalid ones)
4. **Suggest improvements** - If a component name is valid but could be clearer, suggest an improved name
5. **Preserve specificity** - Keep detailed component names (e.g., "M3x25mm hexagon head screws" is better than "screws")

Review all components and return the JSON response."""

    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for a given text.

        Uses a simple heuristic: ~1.3 tokens per word, which is a reasonable
        approximation for English text. More accurate tokenization would require
        the actual tokenizer for each model, but this provides a good estimate.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Simple estimation: ~1.3 tokens per word (common for English)
        # This is similar to what Anthropic provider uses
        word_count = len(text.split())
        estimated_tokens = int(word_count * 1.3)

        # Add some overhead for special characters, formatting, etc.
        # JSON structures and markdown add extra tokens
        if "```" in text or "{" in text:
            estimated_tokens = int(estimated_tokens * 1.1)

        return estimated_tokens

    def _parse_llm_validation_response(
        self, response_content: str, components: List[Any]
    ) -> List[Any]:
        """
        Parse LLM validation response and filter components.

        Uses robust JSON extraction and recovery mechanisms to handle:
        - Markdown-wrapped JSON
        - Truncated responses
        - Malformed JSON (trailing commas, missing commas, comments)
        - Partial JSON extraction
        """
        import json
        import re

        try:
            # Step 1: Extract JSON from response (handle markdown code blocks and other formats)
            json_str = self._extract_json_from_validation_response(response_content)

            if not json_str:
                logger.warning("No JSON found in LLM validation response")
                return components  # Return all if no JSON found

            # Step 2: Parse JSON with recovery attempts
            validation = self._parse_json_with_recovery(json_str)

            if not validation:
                logger.warning(
                    f"Failed to parse LLM validation response after recovery attempts. "
                    f"Response length: {len(response_content)}, "
                    f"JSON length: {len(json_str) if json_str else 0}"
                )
                return components  # Return all if parsing fails

            # Step 3: Create map of valid component IDs
            valid_ids = {comp["id"] for comp in validation.get("valid_components", [])}

            # Step 4: Apply suggested name improvements
            improvements = {
                comp["id"]: comp["suggested_name"]
                for comp in validation.get("suggested_improvements", [])
            }

            # Step 5: Filter and update components
            filtered = []
            for comp in components:
                if comp.id in valid_ids:
                    # Apply name improvement if suggested
                    if comp.id in improvements:
                        original_name = comp.name
                        comp.name = improvements[comp.id]
                        # Update metadata
                        comp.metadata["llm_reviewed"] = True
                        comp.metadata["original_name"] = original_name
                        comp.metadata["name_improved"] = True
                    else:
                        comp.metadata["llm_reviewed"] = True
                    filtered.append(comp)
                else:
                    logger.debug(
                        f"LLM filtered out invalid component: {comp.name} (ID: {comp.id})"
                    )

            return filtered

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(
                f"Failed to parse LLM validation response: {e}. "
                f"Response length: {len(response_content)} chars. "
                f"Returning all components."
            )
            return components  # Return all if parsing fails

    def _extract_json_from_validation_response(
        self, response_content: str
    ) -> Optional[str]:
        """
        Extract JSON string from LLM response, handling various formats.

        Tries multiple strategies:
        1. Markdown code blocks (```json ... ```)
        2. Plain code blocks (``` ... ```)
        3. JSON after keywords
        4. First/last brace matching
        5. Truncated JSON recovery
        """
        import re

        content = response_content.strip()

        # Strategy 1: Markdown JSON code block
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            if json_end > json_start:
                return content[json_start:json_end].strip()

        # Strategy 2: Plain code block
        if "```" in content:
            json_start = content.find("```") + 3
            json_end = content.find("```", json_start)
            if json_end > json_start:
                extracted = content[json_start:json_end].strip()
                # Only return if it looks like JSON (starts with {)
                if extracted.startswith("{"):
                    return extracted

        # Strategy 3: Look for JSON after common keywords
        keywords = ["JSON:", "json:", "response:", "validation:"]
        for keyword in keywords:
            idx = content.find(keyword)
            if idx != -1:
                # Find the next {
                json_start = content.find("{", idx)
                if json_start != -1:
                    json_end = content.rfind("}", json_start)
                    if json_end > json_start:
                        return content[json_start : json_end + 1]

        # Strategy 4: Find first { and last } (handles truncated responses)
        json_start = content.find("{")
        if json_start != -1:
            json_end = content.rfind("}")
            if json_end > json_start:
                return content[json_start : json_end + 1]

        # Strategy 5: Try to find JSON object even if truncated (missing closing brace)
        json_start = content.find("{")
        if json_start != -1:
            # Try to extract up to the last complete object/array
            # This is a best-effort for truncated responses
            extracted = content[json_start:]
            # Try to find the last complete structure
            # Count braces to find where JSON might be complete
            brace_count = 0
            last_valid_pos = -1
            for i, char in enumerate(extracted):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        last_valid_pos = i
            if last_valid_pos > 0:
                return extracted[: last_valid_pos + 1]
            # If no complete structure, return what we have (will try recovery)
            return extracted

        return None

    def _parse_json_with_recovery(self, json_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON with recovery attempts for common issues.

        Handles:
        - Trailing commas
        - Missing commas
        - Comments (// and /* */)
        - Truncated JSON (tries to extract partial structure)
        """
        import json
        import re

        if not json_str:
            return None

        # First try: Direct parse
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Recovery attempt 1: Fix trailing commas before } or ]
        try:
            fixed = re.sub(r",(\s*[}\]])", r"\1", json_str)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # Recovery attempt 2: Remove comments (// and /* */)
        try:
            # Remove single-line comments
            fixed = re.sub(r"//.*?$", "", json_str, flags=re.MULTILINE)
            # Remove multi-line comments
            fixed = re.sub(r"/\*.*?\*/", "", fixed, flags=re.DOTALL)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # Recovery attempt 3: Fix missing commas between object properties
        try:
            # Pattern: "key": value "next_key": -> "key": value, "next_key":
            fixed = re.sub(r'("\s*:\s*[^,}\]]+)\s+("[\w_]+"\s*:)', r"\1,\2", json_str)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # Recovery attempt 4: Apply multiple fixes in combination
        try:
            fixed = json_str
            # Remove comments
            fixed = re.sub(r"//.*?$", "", fixed, flags=re.MULTILINE)
            fixed = re.sub(r"/\*.*?\*/", "", fixed, flags=re.DOTALL)
            # Fix trailing commas
            fixed = re.sub(r",(\s*[}\]])", r"\1", fixed)
            # Fix missing commas
            fixed = re.sub(r'("\s*:\s*[^,}\]]+)\s+("[\w_]+"\s*:)', r"\1,\2", fixed)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # Recovery attempt 5: Try to extract and parse top-level object only
        try:
            json_start = json_str.find("{")
            json_end = json_str.rfind("}")
            if json_start != -1 and json_end > json_start:
                isolated = json_str[json_start : json_end + 1]
                # Apply fixes to isolated JSON
                try:
                    return json.loads(isolated)
                except json.JSONDecodeError:
                    fixed = isolated
                    fixed = re.sub(r"//.*?$", "", fixed, flags=re.MULTILINE)
                    fixed = re.sub(r"/\*.*?\*/", "", fixed, flags=re.DOTALL)
                    fixed = re.sub(r",(\s*[}\]])", r"\1", fixed)
                    return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # Recovery attempt 6: Try to extract partial JSON if truncated
        # This is a last resort - try to get at least valid_components if possible
        try:
            # Look for "valid_components" array even if JSON is incomplete
            valid_components_match = re.search(
                r'"valid_components"\s*:\s*\[(.*?)\]', json_str, re.DOTALL
            )
            invalid_components_match = re.search(
                r'"invalid_components"\s*:\s*\[(.*?)\]', json_str, re.DOTALL
            )
            improvements_match = re.search(
                r'"suggested_improvements"\s*:\s*\[(.*?)\]', json_str, re.DOTALL
            )

            if valid_components_match or invalid_components_match:
                # Try to construct minimal valid JSON
                partial_json = "{"
                if valid_components_match:
                    partial_json += (
                        f'"valid_components": [{valid_components_match.group(1)}],'
                    )
                if invalid_components_match:
                    partial_json += (
                        f'"invalid_components": [{invalid_components_match.group(1)}],'
                    )
                if improvements_match:
                    partial_json += (
                        f'"suggested_improvements": [{improvements_match.group(1)}],'
                    )
                # Remove trailing comma
                partial_json = re.sub(r",\s*$", "", partial_json)
                partial_json += "}"

                return json.loads(partial_json)
        except (json.JSONDecodeError, AttributeError):
            pass

        # All recovery attempts failed
        logger.debug(
            f"All JSON recovery attempts failed. JSON string (first 1000 chars):\n{json_str[:1000]}"
        )
        logger.debug(f"Full JSON string length: {len(json_str)} characters")
        return None

    def _extract_materials_from_bom(self, bom) -> List[str]:
        """
        Extract materials from BOM components.

        This method analyzes component names to extract:
        1. Explicit material types (PLA, steel, aluminum, etc.)
        2. Materials mentioned in component descriptions (silicone, plastic, etc.)
        3. Component categories that represent materials (springs, electronics, etc.)

        Args:
            bom: BillOfMaterials object with components

        Returns:
            List of unique material names extracted from BOM components
        """
        materials = set()

        for component in bom.components:
            component_name = component.name.lower()

            # First, try to classify as a known component type (springs, electronics, etc.)
            material_type = self._classify_component_material(component_name)
            if material_type:
                materials.add(material_type)

            # Second, extract material names directly from component description
            # Look for material keywords in the component name
            extracted_materials = self._extract_materials_from_component_name(
                component_name
            )
            materials.update(extracted_materials)

        return sorted(list(materials)) if materials else []

    def _extract_materials_from_component_name(self, component_name: str) -> List[str]:
        """
        Extract material types from component names.

        Examples:
        - "Clear Translucent Silicone Hose Pipe Tubing" -> ["silicone"]
        - "PLA Filament" -> ["PLA"]
        - "Steel Spring" -> ["steel"]

        Args:
            component_name: Lowercase component name

        Returns:
            List of material names found in the component name
        """
        materials = set()

        # Material keywords to look for in component names (ordered by specificity)
        material_keywords = {
            # Plastics and polymers
            "silicone",
            "rubber",
            "latex",
            "plastic",
            "polymer",
            "PLA",
            "ABS",
            "PETG",
            "TPU",
            "ASA",
            "PC",
            "nylon",
            "resin",
            # Metals
            "aluminum",
            "aluminium",
            "steel",
            "stainless steel",
            "brass",
            "copper",
            "iron",
            "titanium",
            "zinc",
            "nickel",
            "chrome",
            # Composites and other materials
            "wood",
            "plywood",
            "MDF",
            "fiberglass",
            "carbon fiber",
            "ceramic",
            "glass",
            "paper",
            "cardboard",
            "fabric",
            "leather",
            # Materials by properties (note: hose, tube, pipe are product forms, not materials)
            "filament",
            "wire",
            "cable",
            "foam",
            "foam rubber",
        }

        # Check for material keywords in the component name
        words = component_name.split()
        for word in words:
            word_clean = word.lower().strip(".,;:()[]{}")
            if word_clean in material_keywords:
                # Normalize to standard form
                normalized = self._normalize_material_name(word_clean)
                if normalized:
                    materials.add(normalized)

        # Also check for multi-word materials
        for material in material_keywords:
            if " " in material and material in component_name:
                normalized = self._normalize_material_name(material)
                if normalized:
                    materials.add(normalized)

        return list(materials)

    def _normalize_material_name(self, material: str) -> str:
        """
        Normalize material name to standard form.

        Args:
            material: Material name (lowercase)

        Returns:
            Normalized material name or None if should be filtered
        """
        # Normalization map
        normalization_map = {
            "aluminium": "aluminum",
            "pla": "PLA",
            "abs": "ABS",
            "petg": "PETG",
            "tpu": "TPU",
            "asa": "ASA",
            "pc": "PC",
            "mdf": "MDF",
            "nylon": "nylon",
            "resin": "resin",
        }

        # Get normalized form
        normalized = normalization_map.get(material, material)

        # Capitalize first letter for consistency (except for acronyms)
        if normalized.isupper() or len(normalized) <= 4:
            return normalized
        else:
            return normalized.capitalize()

    def _classify_component_material(self, component_name: str) -> Optional[str]:
        """Classify a component name into a material type"""
        import re

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
            # Component types (only if they represent actual material categories in BOM)
            # Note: Electronics should only be added if there are actual electronic components
            # Use word boundaries for short patterns to avoid false matches (e.g., "ic" matching "translucent")
            (
                "electronics",
                [
                    "arduino",
                    "raspberry pi",
                    "microcontroller",
                    r"\bic\b",
                    "integrated circuit",
                    r"\bboard\b",
                    "pcb",
                ],
            ),
            ("fasteners", ["screw", "bolt", "nut", "washer", "rivet", "pin"]),
            ("cables", ["cable", "wire", "connector", "jack", "plug"]),
            ("bearings", ["bearing", "ball bearing", "roller bearing"]),
            (
                "springs",
                ["spring", "coil spring", "tension spring", "compression spring"],
            ),
        ]

        # Check each material pattern (first match wins)
        for material, patterns in material_patterns:
            for pattern in patterns:
                # Use regex word boundaries for patterns that need them (start with \b)
                if pattern.startswith(r"\b"):
                    # Pattern is a regex with word boundaries
                    if re.search(pattern, name_lower):
                        return material
                else:
                    # Use simple substring match for longer patterns or multi-word patterns
                    # But check if it's a single short word that could match falsely
                    if len(pattern) <= 3 and pattern.isalpha():
                        # For short single words, use word boundary matching
                        if re.search(r"\b" + re.escape(pattern) + r"\b", name_lower):
                            return material
                    else:
                        # For longer patterns or multi-word, use simple substring
                        if pattern in name_lower:
                            return material

        return None

    def _analyze_parts_directory(self, project_data) -> Dict[str, List[Dict[str, Any]]]:
        """
        Analyze parts directory structure to extract parts and sub_parts information.

        Args:
            project_data: ProjectData containing file information

        Returns:
            Dictionary with 'parts' and 'sub_parts' lists
        """
        parts = []
        sub_parts = []

        # Look for parts-related directories
        parts_directories = []
        for file_info in project_data.files:
            path = file_info.path.lower()
            if "parts" in path and file_info.file_type == "markdown":
                # Extract directory structure from path
                path_parts = file_info.path.split("/")
                if (
                    len(path_parts) >= 3 and path_parts[1] == "parts"
                ):  # docs/parts/category/file.md
                    category = path_parts[2]
                    if category not in parts_directories:
                        parts_directories.append(category)

        # Analyze each parts category
        for category in parts_directories:
            category_files = []
            for file_info in project_data.files:
                if (
                    file_info.path.startswith(f"docs/parts/{category}/")
                    and file_info.file_type == "markdown"
                ):
                    category_files.append(file_info)

            if category_files:
                # Create a part entry for this category
                part_entry = {
                    "name": category.replace("_", " ").title(),
                    "category": category,
                    "description": f"Components in the {category} category",
                    "files": [
                        {
                            "path": f.path,
                            "name": f.path.split("/")[-1]
                            .replace(".md", "")
                            .replace("_", " ")
                            .title(),
                            "type": f.file_type,
                            "size": f.size,
                        }
                        for f in category_files
                    ],
                    "file_count": len(category_files),
                }

                # Determine if this is a main part or sub-part based on category
                if category in ["electronics", "optics", "printed"]:
                    parts.append(part_entry)
                else:
                    sub_parts.append(part_entry)

        # Also look for individual part files that might not be in categories
        individual_parts = []
        for file_info in project_data.files:
            if (
                file_info.path.startswith("docs/parts/")
                and file_info.file_type == "markdown"
                and not any(cat in file_info.path for cat in parts_directories)
            ):

                part_name = (
                    file_info.path.split("/")[-1]
                    .replace(".md", "")
                    .replace("_", " ")
                    .title()
                )
                individual_parts.append(
                    {
                        "name": part_name,
                        "path": file_info.path,
                        "type": file_info.file_type,
                        "size": file_info.size,
                    }
                )

        # Add individual parts as sub_parts
        if individual_parts:
            sub_parts.append(
                {
                    "name": "Individual Parts",
                    "category": "individual",
                    "description": "Individual part specifications",
                    "files": individual_parts,
                    "file_count": len(individual_parts),
                }
            )

        return {"parts": parts, "sub_parts": sub_parts}
