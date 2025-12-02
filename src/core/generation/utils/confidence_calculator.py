"""
Confidence calculation utilities for generation layers.

This module provides standardized confidence scoring for field extractions
across all generation layers, ensuring consistent quality assessment.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from ..models import GenerationLayer


class ConfidenceLevel(Enum):
    """Confidence level categories"""

    VERY_LOW = 0.1
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9


@dataclass
class ConfidenceRule:
    """Rule for calculating confidence scores"""

    field: str
    base_confidence: float
    source_multipliers: Dict[str, float]
    quality_adjustments: Dict[str, float]
    description: str


class ConfidenceCalculator:
    """Standardized confidence scoring for field extractions"""

    def __init__(self):
        self._confidence_rules = self._initialize_confidence_rules()
        self._source_quality_scores = self._initialize_source_quality_scores()
        self._field_importance_weights = self._initialize_field_importance_weights()

    def _initialize_confidence_rules(self) -> Dict[str, ConfidenceRule]:
        """Initialize confidence calculation rules for different fields"""
        return {
            "title": ConfidenceRule(
                field="title",
                base_confidence=0.9,
                source_multipliers={
                    "direct_mapping": 1.0,
                    "metadata_extraction": 0.95,
                    "file_name_analysis": 0.8,
                    "content_analysis": 0.7,
                    "nlp_extraction": 0.6,
                },
                quality_adjustments={
                    "length_optimal": 0.1,  # 10-100 characters
                    "length_short": -0.2,  # < 10 characters
                    "length_long": -0.1,  # > 100 characters
                    "has_special_chars": -0.1,
                    "is_generic": -0.3,
                },
                description="Title extraction confidence rules",
            ),
            "description": ConfidenceRule(
                field="description",
                base_confidence=0.8,
                source_multipliers={
                    "direct_mapping": 1.0,
                    "readme_extraction": 0.9,
                    "content_analysis": 0.8,
                    "nlp_extraction": 0.7,
                    "file_name_analysis": 0.5,
                },
                quality_adjustments={
                    "length_optimal": 0.1,  # 50-500 characters
                    "length_short": -0.3,  # < 50 characters
                    "length_long": 0.0,  # > 500 characters
                    "has_technical_terms": 0.1,
                    "is_generic": -0.2,
                },
                description="Description extraction confidence rules",
            ),
            "license": ConfidenceRule(
                field="license",
                base_confidence=0.9,
                source_multipliers={
                    "license_file_detection": 1.0,
                    "metadata_extraction": 0.95,
                    "direct_mapping": 0.9,
                    "content_analysis": 0.8,
                    "pattern_matching": 0.7,
                },
                quality_adjustments={
                    "standard_license": 0.1,
                    "custom_license": -0.2,
                    "no_license_found": -0.5,
                    "multiple_licenses": -0.1,
                },
                description="License extraction confidence rules",
            ),
            "version": ConfidenceRule(
                field="version",
                base_confidence=0.8,
                source_multipliers={
                    "metadata_extraction": 1.0,
                    "tag_detection": 0.95,
                    "file_name_analysis": 0.8,
                    "content_analysis": 0.7,
                    "pattern_matching": 0.6,
                },
                quality_adjustments={
                    "semantic_version": 0.1,
                    "simple_version": 0.0,
                    "pre_release": -0.1,
                    "no_version": -0.5,
                },
                description="Version extraction confidence rules",
            ),
            "materials": ConfidenceRule(
                field="materials",
                base_confidence=0.7,
                source_multipliers={
                    "bom_extraction": 0.9,
                    "content_analysis": 0.8,
                    "nlp_extraction": 0.7,
                    "pattern_matching": 0.6,
                    "heuristic_analysis": 0.5,
                },
                quality_adjustments={
                    "multiple_materials": 0.1,
                    "standard_materials": 0.1,
                    "single_material": -0.1,
                    "generic_materials": -0.2,
                },
                description="Materials extraction confidence rules",
            ),
            "manufacturing_processes": ConfidenceRule(
                field="manufacturing_processes",
                base_confidence=0.6,
                source_multipliers={
                    "content_analysis": 0.8,
                    "nlp_extraction": 0.7,
                    "pattern_matching": 0.6,
                    "heuristic_analysis": 0.5,
                    "file_structure_analysis": 0.4,
                },
                quality_adjustments={
                    "multiple_processes": 0.1,
                    "standard_processes": 0.1,
                    "single_process": -0.1,
                    "generic_processes": -0.2,
                },
                description="Manufacturing processes extraction confidence rules",
            ),
            "tool_list": ConfidenceRule(
                field="tool_list",
                base_confidence=0.6,
                source_multipliers={
                    "content_analysis": 0.8,
                    "nlp_extraction": 0.7,
                    "pattern_matching": 0.6,
                    "heuristic_analysis": 0.5,
                    "file_structure_analysis": 0.4,
                },
                quality_adjustments={
                    "multiple_tools": 0.1,
                    "specific_tools": 0.1,
                    "generic_tools": -0.1,
                    "no_tools": -0.3,
                },
                description="Tool list extraction confidence rules",
            ),
            "function": ConfidenceRule(
                field="function",
                base_confidence=0.7,
                source_multipliers={
                    "content_analysis": 0.8,
                    "nlp_extraction": 0.7,
                    "readme_extraction": 0.6,
                    "heuristic_analysis": 0.5,
                },
                quality_adjustments={
                    "clear_purpose": 0.1,
                    "technical_description": 0.1,
                    "vague_description": -0.2,
                    "no_description": -0.4,
                },
                description="Function extraction confidence rules",
            ),
            "intended_use": ConfidenceRule(
                field="intended_use",
                base_confidence=0.6,
                source_multipliers={
                    "content_analysis": 0.8,
                    "nlp_extraction": 0.7,
                    "readme_extraction": 0.6,
                    "heuristic_analysis": 0.5,
                },
                quality_adjustments={
                    "specific_use_case": 0.1,
                    "multiple_use_cases": 0.1,
                    "generic_use_case": -0.1,
                    "no_use_case": -0.3,
                },
                description="Intended use extraction confidence rules",
            ),
        }

    def _initialize_source_quality_scores(self) -> Dict[str, float]:
        """Initialize quality scores for different data sources"""
        return {
            "github_api": 0.95,
            "gitlab_api": 0.95,
            "file_content": 0.8,
            "file_name": 0.6,
            "directory_structure": 0.5,
            "content_analysis": 0.7,
            "pattern_matching": 0.6,
            "heuristic_analysis": 0.5,
            "nlp_extraction": 0.7,
            "user_input": 1.0,
            "fallback": 0.1,
        }

    def _initialize_field_importance_weights(self) -> Dict[str, float]:
        """Initialize importance weights for different fields"""
        return {
            "title": 1.0,
            "description": 0.9,
            "license": 0.8,
            "version": 0.7,
            "function": 0.8,
            "intended_use": 0.7,
            "materials": 0.6,
            "manufacturing_processes": 0.6,
            "tool_list": 0.5,
            "organization": 0.4,
            "repo": 0.3,
        }

    def calculate_field_confidence(
        self,
        field: str,
        value: Any,
        source: str,
        content_quality: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate confidence score for a field extraction.

        Args:
            field: Name of the field being extracted
            value: Extracted value
            source: Source of the extraction (method/source)
            content_quality: Optional quality metrics for the source content

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Get base confidence rule
        rule = self._confidence_rules.get(field)
        if not rule:
            # Default rule for unknown fields
            base_confidence = 0.5
            source_multiplier = self._source_quality_scores.get(source, 0.5)
        else:
            base_confidence = rule.base_confidence
            source_multiplier = rule.source_multipliers.get(source, 0.5)

        # Calculate base confidence
        confidence = base_confidence * source_multiplier

        # Apply quality adjustments
        if rule and content_quality:
            for quality_factor, adjustment in rule.quality_adjustments.items():
                if self._evaluate_quality_factor(
                    quality_factor, value, content_quality
                ):
                    confidence += adjustment

        # Apply value-specific adjustments
        confidence = self._apply_value_adjustments(confidence, field, value)

        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))

    def _evaluate_quality_factor(
        self, factor: str, value: Any, content_quality: Dict[str, Any]
    ) -> bool:
        """Evaluate a quality factor for confidence adjustment"""
        if factor == "length_optimal":
            if isinstance(value, str):
                length = len(value)
                if factor == "length_optimal":
                    return 10 <= length <= 100
                elif factor == "length_short":
                    return length < 10
                elif factor == "length_long":
                    return length > 100
        elif factor == "has_special_chars":
            return isinstance(value, str) and any(c in value for c in "!@#$%^&*()")
        elif factor == "is_generic":
            generic_terms = ["project", "repository", "code", "software", "hardware"]
            return isinstance(value, str) and any(
                term in value.lower() for term in generic_terms
            )
        elif factor == "standard_license":
            standard_licenses = ["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause"]
            return isinstance(value, str) and any(
                license in value for license in standard_licenses
            )
        elif factor == "semantic_version":
            import re

            return (
                isinstance(value, str)
                and re.match(r"^\d+\.\d+\.\d+", value) is not None
            )
        elif factor == "multiple_materials":
            return isinstance(value, list) and len(value) > 1
        elif factor == "clear_purpose":
            return (
                isinstance(value, str)
                and len(value) > 20
                and "purpose" in value.lower()
            )

        return False

    def _apply_value_adjustments(
        self, confidence: float, field: str, value: Any
    ) -> float:
        """Apply value-specific confidence adjustments"""
        if value is None or value == "":
            return confidence * 0.1  # Very low confidence for empty values

        if isinstance(value, str):
            if len(value.strip()) == 0:
                return confidence * 0.1
            elif len(value) < 3:
                return confidence * 0.5  # Very short values are less reliable

        if isinstance(value, list):
            if len(value) == 0:
                return confidence * 0.1
            elif len(value) == 1:
                return confidence * 0.8  # Single items are less reliable than multiple

        return confidence

    def calculate_layer_confidence(self, confidence_scores: Dict[str, float]) -> float:
        """
        Calculate overall confidence for a layer.

        Args:
            confidence_scores: Dictionary of field confidence scores

        Returns:
            Overall layer confidence score
        """
        if not confidence_scores:
            return 0.0

        # Weight confidence scores by field importance
        weighted_scores = []
        total_weight = 0.0

        for field, confidence in confidence_scores.items():
            weight = self._field_importance_weights.get(field, 0.5)
            weighted_scores.append(confidence * weight)
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return sum(weighted_scores) / total_weight

    def get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """
        Get confidence level category for a score.

        Args:
            confidence: Confidence score between 0.0 and 1.0

        Returns:
            Confidence level category
        """
        if confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.7:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def get_confidence_rules(self, field: str) -> Optional[ConfidenceRule]:
        """
        Get confidence rules for a specific field.

        Args:
            field: Field name

        Returns:
            Confidence rule or None if not found
        """
        return self._confidence_rules.get(field)

    def get_source_quality_score(self, source: str) -> float:
        """
        Get quality score for a data source.

        Args:
            source: Source identifier

        Returns:
            Quality score between 0.0 and 1.0
        """
        return self._source_quality_scores.get(source, 0.5)

    def get_field_importance_weight(self, field: str) -> float:
        """
        Get importance weight for a field.

        Args:
            field: Field name

        Returns:
            Importance weight between 0.0 and 1.0
        """
        return self._field_importance_weights.get(field, 0.5)

    def validate_confidence_score(self, confidence: float) -> bool:
        """
        Validate that a confidence score is within valid range.

        Args:
            confidence: Confidence score to validate

        Returns:
            True if valid, False otherwise
        """
        return 0.0 <= confidence <= 1.0

    def normalize_confidence_scores(
        self, confidence_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Normalize confidence scores to ensure they're within valid range.

        Args:
            confidence_scores: Dictionary of confidence scores

        Returns:
            Normalized confidence scores
        """
        normalized = {}
        for field, confidence in confidence_scores.items():
            normalized[field] = max(0.0, min(1.0, confidence))
        return normalized
