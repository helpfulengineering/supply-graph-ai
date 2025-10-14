"""
Generation Engine for OKH manifest generation.

This module provides the main orchestration engine that coordinates all generation
layers and manages progressive enhancement to create OKH manifests from project data.
"""

import asyncio
from typing import Dict, List, Optional, Any

from .models import (
    ProjectData, ManifestGeneration, FieldGeneration, LayerConfig,
    QualityReport, GenerationLayer, GenerationQuality
)
from .layers.direct import DirectMatcher
from .layers.heuristic import HeuristicMatcher
from .quality import QualityAssessor


class GenerationEngine:
    """Main orchestration engine for OKH manifest generation"""
    
    def __init__(self, config: Optional[LayerConfig] = None):
        """
        Initialize the generation engine.
        
        Args:
            config: Layer configuration. If None, uses default configuration.
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
            "title", "version", "license", "licensor", 
            "documentation_language", "function"
        ]
    
    def _validate_config(self):
        """Validate the layer configuration"""
        if not isinstance(self.config, LayerConfig):
            raise ValueError("Invalid layer configuration")
        
        # Check that at least one layer is enabled
        if not any([
            self.config.use_direct,
            self.config.use_heuristic,
            self.config.use_nlp,
            self.config.use_llm
        ]):
            raise ValueError("At least one generation layer must be enabled")
    
    def _initialize_matchers(self):
        """Initialize available layer matchers"""
        if self.config.use_direct:
            self._matchers[GenerationLayer.DIRECT] = DirectMatcher()
        
        if self.config.use_heuristic:
            self._matchers[GenerationLayer.HEURISTIC] = HeuristicMatcher()
        
        # Future layers will be added here
        # if self.config.use_nlp:
        #     self._matchers[GenerationLayer.NLP] = NLPMatcher()
        # if self.config.use_llm:
        #     self._matchers[GenerationLayer.LLM] = LLMMatcher()
    
    def generate_manifest(self, project_data: ProjectData) -> ManifestGeneration:
        """
        Generate an OKH manifest from project data.
        
        Args:
            project_data: Raw project data from platform
            
        Returns:
            ManifestGeneration containing generated fields and metadata
            
        Raises:
            ValueError: If project data is invalid
        """
        if project_data is None:
            raise ValueError("Project data cannot be None")
        
        if not isinstance(project_data, ProjectData):
            raise ValueError("Invalid project data")
        
        # Initialize result
        generated_fields = {}
        confidence_scores = {}
        missing_fields = []
        
        # Apply layers in priority order
        if self.config.progressive_enhancement:
            generated_fields, confidence_scores, missing_fields = self._progressive_enhancement(
                project_data, generated_fields, confidence_scores, missing_fields
            )
        else:
            generated_fields, confidence_scores, missing_fields = self._apply_all_layers(
                project_data, generated_fields, confidence_scores, missing_fields
            )
        
        # Generate quality report
        quality_report = self._quality_assessor.generate_quality_report(
            generated_fields, confidence_scores, missing_fields, self._required_fields
        )
        
        return ManifestGeneration(
            project_data=project_data,
            generated_fields=generated_fields,
            confidence_scores=confidence_scores,
            quality_report=quality_report,
            missing_fields=missing_fields
        )
    
    async def generate_manifest_async(self, project_data: ProjectData) -> ManifestGeneration:
        """
        Async version of generate_manifest for future async operations.
        
        Args:
            project_data: Raw project data from platform
            
        Returns:
            ManifestGeneration containing generated fields and metadata
        """
        # Initialize result containers
        generated_fields: Dict[str, FieldGeneration] = {}
        confidence_scores: Dict[str, float] = {}
        missing_fields: List[str] = []
        
        # Apply layers based on configuration
        if self.config.progressive_enhancement:
            generated_fields, confidence_scores, missing_fields = await self._progressive_enhancement(
                project_data, generated_fields, confidence_scores, missing_fields
            )
        else:
            generated_fields, confidence_scores, missing_fields = await self._apply_all_layers(
                project_data, generated_fields, confidence_scores, missing_fields
            )
        
        # Generate quality report
        quality_report = self._quality_assessor.generate_quality_report(
            generated_fields, confidence_scores, missing_fields, self._required_fields
        )
        
        # Create result
        return ManifestGeneration(
            project_data=project_data,
            generated_fields=generated_fields,
            confidence_scores=confidence_scores,
            quality_report=quality_report,
            missing_fields=missing_fields
        )
    
    async def _progressive_enhancement(self, project_data: ProjectData, 
                                generated_fields: Dict[str, FieldGeneration],
                                confidence_scores: Dict[str, float],
                                missing_fields: List[str]) -> tuple:
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
            GenerationLayer.LLM
        ]
        
        for layer in layer_order:
            if layer not in self._matchers:
                continue
            
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
            
            # Check if we should stop (all required fields have sufficient confidence)
            if self._should_stop_progressive_enhancement(confidence_scores):
                break
        
        # Update missing fields
        missing_fields = self._calculate_missing_fields(generated_fields)
        
        return generated_fields, confidence_scores, missing_fields
    
    async def _apply_all_layers(self, project_data: ProjectData,
                         generated_fields: Dict[str, FieldGeneration],
                         confidence_scores: Dict[str, float],
                         missing_fields: List[str]) -> tuple:
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
    
    def _should_stop_progressive_enhancement(self, confidence_scores: Dict[str, float]) -> bool:
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
    
    def _calculate_missing_fields(self, generated_fields: Dict[str, FieldGeneration]) -> List[str]:
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
