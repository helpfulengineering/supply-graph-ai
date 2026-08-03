"""
Quality assessment for OKH manifest generation.

This module provides functionality to assess the quality of generated manifest fields,
validate required fields, and generate quality reports with recommendations.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .models import FieldGeneration, QualityReport


@dataclass
class ValidationResult:
    """Result of field validation"""

    is_valid: bool
    missing_fields: List[str]
    low_confidence_fields: List[str]
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class QualityAssessor:
    """Assesses the quality of generated manifest fields"""

    def __init__(self):
        self._confidence_threshold = 0.7
        self._high_confidence_threshold = 0.9

    def assess_field_confidence(self, field: str, value: Any, source: str) -> float:
        """
        Assess confidence score for a specific field.

        Args:
            field: Field name
            value: Field value
            source: Source of the field

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not value or (isinstance(value, str) and not value.strip()):
            return 0.0

        # Base confidence based on source
        if source == "metadata.name" and field == "title":
            return 0.95
        elif source == "metadata.description" and field == "description":
            return 0.9
        elif source == "metadata.html_url" and field == "repo":
            return 0.95
        elif source == "metadata.license" and field == "license":
            return 0.9
        elif source == "README.md" and field == "readme":
            return 0.9
        elif source == "LICENSE" and field == "license":
            return 0.9
        else:
            # Default confidence based on value quality
            if isinstance(value, str):
                if len(value) > 10:
                    return 0.8
                elif len(value) > 5:
                    return 0.7
                else:
                    return 0.6
            else:
                return 0.8

    def validate_required_fields(
        self, generated_fields: Dict[str, FieldGeneration], required_fields: List[str]
    ) -> ValidationResult:
        """
        Validate that all required fields are present.

        Args:
            generated_fields: Dictionary of generated fields
            required_fields: List of required field names

        Returns:
            ValidationResult with validation status
        """
        missing_fields = []
        low_confidence_fields = []

        for field in required_fields:
            if field not in generated_fields:
                missing_fields.append(field)
            elif generated_fields[field].confidence < self._confidence_threshold:
                low_confidence_fields.append(field)

        is_valid = len(missing_fields) == 0 and len(low_confidence_fields) == 0

        return ValidationResult(
            is_valid=is_valid,
            missing_fields=missing_fields,
            low_confidence_fields=low_confidence_fields,
        )

    def generate_quality_report(
        self,
        generated_fields: Dict[str, FieldGeneration],
        confidence_scores: Dict[str, float],
        missing_fields: List[str],
        required_fields: List[str],
    ) -> QualityReport:
        """
        Generate a quality report.

        Args:
            generated_fields: Dictionary of generated fields
            confidence_scores: Dictionary of confidence scores
            missing_fields: List of missing field names
            required_fields: List of required field names

        Returns:
            QualityReport with assessment results
        """
        # Calculate overall quality
        overall_quality = self._calculate_overall_quality(
            confidence_scores, required_fields
        )

        # Check if required fields are complete
        if len(required_fields) == 0:
            # If no required fields specified, consider it complete
            required_fields_complete = True
        else:
            required_fields_complete = len(missing_fields) == 0

        # Identify low confidence fields
        low_confidence_fields = [
            field
            for field, score in confidence_scores.items()
            if score < self._confidence_threshold
        ]

        # Generate recommendations
        recommendations = self._generate_recommendations(
            missing_fields, low_confidence_fields, generated_fields
        )

        return QualityReport(
            overall_quality=overall_quality,
            required_fields_complete=required_fields_complete,
            missing_required_fields=missing_fields,
            low_confidence_fields=low_confidence_fields,
            recommendations=recommendations,
        )

    def _calculate_overall_quality(
        self, confidence_scores: Dict[str, float], required_fields: List[str]
    ) -> float:
        """
        Calculate overall quality score.

        Args:
            confidence_scores: Dictionary of confidence scores
            required_fields: List of required field names

        Returns:
            Overall quality score between 0.0 and 1.0
        """
        if not confidence_scores:
            return 0.0

        # Calculate weighted average (required fields have higher weight)
        total_score = 0.0
        total_weight = 0.0

        for field, score in confidence_scores.items():
            weight = 2.0 if field in required_fields else 1.0
            total_score += score * weight
            total_weight += weight

        # Add penalty for missing required fields
        missing_required = [
            field for field in required_fields if field not in confidence_scores
        ]
        penalty = len(missing_required) * 0.1

        if total_weight > 0:
            base_quality = total_score / total_weight
            return max(0.0, base_quality - penalty)
        else:
            return 0.0

    def _generate_recommendations(
        self,
        missing_fields: List[str],
        low_confidence_fields: List[str],
        generated_fields: Dict[str, FieldGeneration],
    ) -> List[str]:
        """
        Generate recommendations for improving manifest quality.

        Args:
            missing_fields: List of missing field names
            low_confidence_fields: List of low confidence field names
            generated_fields: Dictionary of generated fields

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Recommendations for missing fields
        if missing_fields:
            if len(missing_fields) == 1:
                recommendations.append(
                    f"Add missing required field: {missing_fields[0]}"
                )
            else:
                recommendations.append(
                    f"Add missing required fields: {', '.join(missing_fields)}"
                )

        # Recommendations for low confidence fields
        if low_confidence_fields:
            recommendations.append(
                f"Improve confidence for fields: {', '.join(low_confidence_fields)}"
            )

        # Specific recommendations based on field types
        if "title" in missing_fields:
            recommendations.append("Add a clear, descriptive title for the project")

        if "description" in missing_fields:
            recommendations.append(
                "Add a detailed description explaining the project's purpose"
            )

        if "license" in missing_fields:
            recommendations.append(
                "Specify the license for hardware, documentation, and software"
            )

        if "function" in missing_fields:
            recommendations.append(
                "Describe the primary function or purpose of the hardware"
            )

        # Recommendations for improving existing fields
        if "title" in low_confidence_fields:
            recommendations.append(
                "Consider improving the project title for better clarity"
            )

        if "description" in low_confidence_fields:
            recommendations.append("Enhance the project description with more detail")

        return recommendations


# --- Did the LLM actually run? -----------------------------------------------
#
# Generation degrades to direct + heuristic + NLP whenever no LLM is usable, and
# that degradation used to be invisible outside the logs: a reviewer could not
# tell whether a thin manifest reflected a thin repository or a missing
# provider. Declared availability is not proof either — a stored key can be
# expired, and a named local model can be down — so this reports what HAPPENED,
# not what was configured.


class LLMUsageStatus:
    """Why the LLM did or did not contribute to a run."""

    USED = "used"
    NOT_REQUESTED = "not_requested"  # caller passed no_llm
    DISABLED = "disabled"  # LLM_ENABLED=false
    NOT_CONFIGURED = "not_configured"  # no credential for any provider
    FAILED = "failed"  # available and attempted, but errored
    SKIPPED = "skipped"  # enough confidence reached before it ran


# Reasons that mean "nothing is wrong, this is what you asked for".
_DELIBERATE = {LLMUsageStatus.NOT_REQUESTED, LLMUsageStatus.DISABLED}

_RECOMMENDATIONS = {
    LLMUsageStatus.NOT_CONFIGURED: (
        "Generated without an LLM — no provider is configured, so descriptive "
        "fields such as 'function' were not inferred. Add a provider credential "
        "in Settings to improve extraction."
    ),
    LLMUsageStatus.FAILED: (
        "Generated without an LLM — the configured provider could not be reached, "
        "so descriptive fields such as 'function' were not inferred. Check the "
        "credential is valid and the provider is reachable."
    ),
    LLMUsageStatus.DISABLED: (
        "Generated without an LLM — it is switched off (LLM_ENABLED=false), so "
        "descriptive fields such as 'function' were not inferred."
    ),
}


def summarize_llm_usage(
    config, layer_usage_counts=None, layer_error_counts=None
) -> Dict[str, Any]:
    """Report whether the LLM contributed, and why not when it did not.

    Args:
        config: the :class:`LayerConfig` the run used, carrying the availability
            resolved at the entry point.
        layer_usage_counts: the engine's per-layer execution counts. A layer that
            raised never increments its count.
        layer_error_counts: the engine's per-layer failure counts. This is what
            separates "attempted and failed" from "never reached" — without it
            the two are indistinguishable, since neither leaves a usage count.

    Returns a dict merged into the quality report. ``llm_used`` is what tests and
    the production probe assert on; ``llm_status`` says why.
    """
    counts = layer_usage_counts or {}
    errors = layer_error_counts or {}
    ran = counts.get("llm", 0) > 0

    if ran:
        status = LLMUsageStatus.USED
    elif not getattr(config, "use_llm", False):
        status = LLMUsageStatus.NOT_REQUESTED
    elif not getattr(config, "llm_available", False):
        # The entry point already decided why; reuse its word for it so the
        # report and the logs agree.
        status = getattr(config, "llm_unavailable_reason", None) or (
            LLMUsageStatus.NOT_CONFIGURED
        )
    elif errors.get("llm", 0) > 0:
        status = LLMUsageStatus.FAILED
    else:
        # Enabled, available, no attempt recorded: progressive enhancement met
        # its confidence threshold before reaching it.
        status = LLMUsageStatus.SKIPPED

    return {
        "llm_used": ran,
        "llm_status": status,
        "llm_provider": getattr(config, "llm_provider", None) if ran else None,
    }


def llm_usage_recommendation(summary: Dict[str, Any]) -> Optional[str]:
    """A plain-language line for a run that had no LLM, or None.

    Rendered by the existing quality banner without any frontend change. Silent
    for deliberate choices — telling someone who passed ``no_llm`` that they got
    no LLM is noise.
    """
    if summary.get("llm_used"):
        return None
    # _RECOMMENDATIONS omits NOT_REQUESTED and SKIPPED: telling someone who
    # passed no_llm that they got no LLM is noise, and stopping early because
    # confidence was already high is a success, not a degradation.
    return _RECOMMENDATIONS.get(summary.get("llm_status"))
