"""
LLM Matching Layer Implementation

This module implements the LLM Matching layer for the Open Matching Engine (OME).
It provides Large Language Model enhanced matching for complex semantic understanding
between requirements and capabilities, particularly designed for crisis response scenarios.

This layer is part of the 4-layer matching architecture and inherits from
BaseMatchingLayer to ensure consistent interfaces and error handling.

The LLM layer uses a prompt engineering strategy for:
- Capability assessment across multiple dimensions
- Crisis response context awareness
- Non-standardized terminology handling
- Practical substitution and adaptation analysis
- Confidence scoring with detailed reasoning
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..services.base import ServiceStatus
from .layers.base import (
    BaseMatchingLayer,
    MatchingLayer,
    MatchingResult,
    MatchMetadata,
    MatchQuality,
)

logger = logging.getLogger(__name__)


class LLMMatcher(BaseMatchingLayer):
    """
    LLM Matching Layer using Large Language Models for advanced capability assessment.

    This layer leverages LLMs to perform sophisticated matching between requirements
    and capabilities using natural language understanding. It's particularly designed
    for crisis response scenarios where terminology may be non-standardized and
    quick, practical decisions are needed.

    The layer analyzes capability compatibility across multiple dimensions:
    - Process compatibility and substitutions
    - Material availability and alternatives
    - Tool/equipment requirements and adaptations
    - Skill/expertise requirements and gaps
    - Scale/capacity considerations and options

    Features:
    - Crisis response context awareness
    - Non-standardized terminology handling
    - Practical substitution analysis
    - Detailed capability assessment
    - Confidence scoring with reasoning
    - Integration with LLM service for provider management
    """

    def __init__(
        self,
        domain: str = "general",
        llm_service: Optional[Any] = None,
        preserve_context: bool = False,
    ):
        """
        Initialize the LLM Matching Layer.

        Args:
            domain: The domain this layer operates in (e.g., 'manufacturing', 'cooking')
            llm_service: LLM service instance. If None, creates a new one.
            preserve_context: If True, context files are preserved for debugging instead of cleaned up.

        Raises:
            RuntimeError: If LLM layer is not properly configured
        """
        super().__init__(MatchingLayer.LLM, domain)

        # Initialize LLM service
        self.llm_service = llm_service or self._create_llm_service()

        # Context file management
        self.context_dir = Path("temp_matching_context")
        self.context_dir.mkdir(exist_ok=True)
        self.preserve_context = preserve_context

        # Load matching prompt strategy
        self.matching_prompt = self._load_matching_prompt()

        logger.info(f"Initialized LLM matching layer for domain: {domain}")

    def _create_llm_service(self):
        """Create and configure LLM service for matching operations."""
        try:
            # Lazy import to avoid circular dependencies
            from ..llm.providers.base import LLMProviderType
            from ..llm.service import LLMService, LLMServiceConfig

            config = LLMServiceConfig(
                name="LLMMatchingService",
                default_provider=LLMProviderType.ANTHROPIC,
                default_model=None,  # Use centralized config
                max_retries=3,
                retry_delay=1.0,
                timeout=30.0,
            )

            service = LLMService(config)
            logger.info("Created LLM service for matching layer")
            return service

        except Exception as e:
            logger.error(f"Failed to create LLM service: {e}")
            raise RuntimeError(f"LLM service creation failed: {e}")

    def _load_matching_prompt(self) -> str:
        """Load the matching system prompt."""
        return """
You are an expert manufacturing and production capability analyst specializing in crisis response and disaster recovery scenarios. Your role is to determine if a facility CAN PRODUCE a specific hardware item by analyzing requirements against capabilities.

## Your Mission
In crisis situations, terminology is often non-standardized, information is incomplete, and quick decisions are needed. Your job is to intelligently assess whether a facility has the capability to produce a required item, even when descriptions don't match exactly.

## Analysis Framework

### Capability Assessment Areas
1. **Process Compatibility**: Can the facility perform the required manufacturing processes?
2. **Material Availability**: Does the facility have access to required materials or suitable substitutes?
3. **Tool/Equipment Requirements**: Does the facility have necessary tools and equipment?
4. **Skill/Expertise Requirements**: Does the facility have required technical expertise?
5. **Scale/Capacity**: Can the facility produce at the required scale?

### Matching Principles
- **Capability Focus**: Focus on what the facility CAN do, not exact terminology matches
- **Substitution Awareness**: Consider material and process substitutions that would work
- **Scale Flexibility**: Consider if facility can adapt to different scales
- **Expertise Assessment**: Evaluate if facility has transferable skills
- **Resource Availability**: Consider what resources are actually available

### Crisis Response Considerations
- **Non-Standard Terminology**: Facilities may use local, informal, or outdated terms
- **Incomplete Information**: Work with partial or uncertain data
- **Creative Solutions**: Look for alternative approaches and substitutions
- **Urgency**: Prioritize quick, practical assessments over perfect accuracy
- **Resource Constraints**: Consider what's actually available in crisis situations

## Output Format
Provide your analysis in the following JSON format:

```json
{
  "match_decision": true/false,
  "confidence_score": 0.0-1.0,
  "capability_assessment": {
    "process_compatibility": {
      "score": 0.0-1.0,
      "analysis": "Detailed analysis of process compatibility",
      "substitutions": ["List of possible process substitutions"]
    },
    "material_availability": {
      "score": 0.0-1.0,
      "analysis": "Analysis of material requirements vs availability",
      "substitutions": ["List of possible material substitutions"]
    },
    "tool_equipment": {
      "score": 0.0-1.0,
      "analysis": "Analysis of tool and equipment requirements",
      "adaptations": ["List of possible adaptations or alternatives"]
    },
    "expertise_skills": {
      "score": 0.0-1.0,
      "analysis": "Analysis of required vs available expertise",
      "training_needs": ["List of training or skill gaps"]
    },
    "scale_capacity": {
      "score": 0.0-1.0,
      "analysis": "Analysis of production scale and capacity",
      "scaling_options": ["List of scaling possibilities"]
    }
  },
  "overall_analysis": "Analysis of the match",
  "key_factors": ["List of 3-5 most important factors in this match"],
  "recommendations": ["List of recommendations for making this match work"],
  "risks": ["List of potential risks or challenges"],
  "crisis_adaptability": "Assessment of how well this facility can adapt to crisis conditions"
}
```

## Confidence Scoring Guidelines
- **0.9-1.0**: Excellent match - facility clearly has all required capabilities
- **0.7-0.9**: Good match - facility has most capabilities with minor gaps
- **0.5-0.7**: Moderate match - facility has some capabilities but significant gaps
- **0.3-0.5**: Poor match - facility has limited capabilities
- **0.0-0.3**: No match - facility cannot produce the required item

## Analysis Examples

### Example 1: Process Substitution
**Requirement**: "CNC machining with 0.1mm tolerance"
**Facility Capability**: "Precision machining with manual mills"
**Analysis**: Manual mills can achieve 0.1mm tolerance with skilled operators. Process substitution is viable.
**Confidence**: 0.7

### Example 2: Material Substitution
**Requirement**: "Stainless steel 316L"
**Facility Capability**: "Stainless steel 304 available"
**Analysis**: 304 can substitute for 316L in many applications. Check specific requirements.
**Confidence**: 0.6

### Example 3: Scale Adaptation
**Requirement**: "Mass production of 10,000 units"
**Facility Capability**: "Small batch production, 100 units max"
**Analysis**: Facility can produce but not at required scale. Consider batch production.
**Confidence**: 0.4

Remember: In crisis situations, perfect matches are rare. Focus on practical solutions that can work with available resources and expertise.
"""

    async def match(
        self, requirements: List[str], capabilities: List[str]
    ) -> List[MatchingResult]:
        """
        Match requirements to capabilities using LLM analysis.

        Args:
            requirements: List of requirement strings to match
            capabilities: List of capability strings to match against

        Returns:
            List of MatchingResult objects with detailed metadata
        """
        # Start tracking metrics
        self.start_matching(requirements, capabilities)

        try:
            # Validate inputs
            if not self.validate_inputs(requirements, capabilities):
                self.end_matching(success=False)
                return []

            # Initialize LLM service if needed
            if self.llm_service.status != ServiceStatus.ACTIVE:
                await self.llm_service.initialize()

            results = []

            # Match each requirement against each capability
            for requirement in requirements:
                for capability in capabilities:
                    result = await self._match_single(requirement, capability)
                    results.append(result)

            # End metrics tracking
            matches_found = sum(1 for r in results if r.matched)
            self.end_matching(success=True, matches_found=matches_found)

            return results

        except Exception as e:
            return self.handle_matching_error(e, [])

    async def _match_single(self, requirement: str, capability: str) -> MatchingResult:
        """Match a single requirement against a single capability using LLM analysis."""
        start_time = datetime.now()

        try:
            # Create context file for this analysis
            context_file = (
                self.context_dir / f"match_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.md"
            )

            # Build analysis prompt
            prompt = self._build_matching_prompt(requirement, capability)

            # Run LLM analysis
            analysis_result = await self._run_llm_analysis(prompt, context_file)

            # Parse LLM response
            match_data = self._parse_llm_response(analysis_result)

            # Create matching result
            result = self._create_matching_result_from_analysis(
                requirement, capability, match_data, start_time
            )

            # Cleanup context file unless preserving
            if not self.preserve_context:
                self._cleanup_context_file(context_file)

            return result

        except Exception as e:
            logger.error(
                f"LLM matching failed for '{requirement}' vs '{capability}': {e}"
            )

            # Return no-match result on error
            return self.create_matching_result(
                requirement=requirement,
                capability=capability,
                matched=False,
                confidence=0.0,
                method="llm_error",
                reasons=[f"LLM analysis failed: {str(e)}"],
                quality=MatchQuality.NO_MATCH,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            )

    def _build_matching_prompt(self, requirement: str, capability: str) -> str:
        """Build the complete prompt for LLM matching analysis."""

        # Extract domain-specific context
        domain_context = self._get_domain_context()

        prompt = f"""
{self.matching_prompt}

## Current Analysis Request

### Requirement (What needs to be produced):
**Description**: {requirement}

### Facility Capability (What facility can do):
**Description**: {capability}

### Domain Context:
{domain_context}

### Crisis Context:
**Crisis Type**: General emergency response
**Urgency Level**: Medium
**Resource Constraints**: Standard
**Timeline**: Flexible

## Analysis Task
Analyze whether this facility CAN PRODUCE the required item, considering the crisis context and non-standardized terminology. Focus on practical solutions and substitutions that could work in emergency conditions.

Provide your analysis in the specified JSON format.
"""

        return prompt

    def _get_domain_context(self) -> str:
        """Get domain-specific context for the prompt."""

        if self.domain == "manufacturing":
            return """
### Manufacturing-Specific Considerations

#### Process Substitutions
- **CNC Machining** ↔ **Manual Machining** (with skilled operators)
- **3D Printing** ↔ **Rapid Prototyping** (various technologies)
- **Laser Cutting** ↔ **Plasma Cutting** ↔ **Water Jet Cutting**
- **Injection Molding** ↔ **Compression Molding** ↔ **3D Printing**

#### Material Substitutions
- **Stainless Steel 316L** ↔ **Stainless Steel 304** (for non-critical applications)
- **Aluminum 6061** ↔ **Aluminum 5052** (with design adjustments)
- **ABS Plastic** ↔ **PLA Plastic** (for prototyping)
- **Carbon Fiber** ↔ **Fiberglass** (for structural applications)

#### Equipment Adaptations
- **CNC Mill** ↔ **Manual Mill** (with skilled operator)
- **Laser Cutter** ↔ **Plasma Cutter** (for metal cutting)
- **3D Printer** ↔ **Manual Fabrication** (for simple parts)
- **Press Brake** ↔ **Manual Bending** (for sheet metal)

#### Scale Adaptations
- **Mass Production** → **Batch Production** (smaller quantities)
- **Automated Assembly** → **Manual Assembly** (with more labor)
- **Continuous Process** → **Batch Process** (with setup time)
"""

        elif self.domain == "cooking":
            return """
### Cooking-Specific Considerations

#### Technique Substitutions
- **Sauté** ↔ **Pan-fry** ↔ **Stir-fry**
- **Roast** ↔ **Bake** ↔ **Grill**
- **Boil** ↔ **Simmer** ↔ **Steam**

#### Equipment Substitutions
- **Oven** ↔ **Toaster Oven** ↔ **Stovetop**
- **Stand Mixer** ↔ **Hand Mixer** ↔ **Manual Mixing**
- **Food Processor** ↔ **Blender** ↔ **Manual Chopping**

#### Ingredient Substitutions
- **Fresh Herbs** ↔ **Dried Herbs** (with quantity adjustments)
- **Butter** ↔ **Oil** ↔ **Margarine**
- **Cream** ↔ **Milk** ↔ **Non-dairy alternatives**
"""

        else:
            return """
### General Considerations

#### Process Substitutions
- Look for alternative methods that achieve the same result
- Consider manual vs automated approaches
- Evaluate different technologies for the same purpose

#### Material Substitutions
- Consider alternative materials with similar properties
- Look for locally available alternatives
- Evaluate cost and availability trade-offs

#### Equipment Adaptations
- Consider equipment that can be adapted or modified
- Look for multi-purpose tools and equipment
- Evaluate manual vs automated alternatives
"""

    async def _run_llm_analysis(self, prompt: str, context_file: Path) -> str:
        """Run LLM analysis and return the response."""
        try:
            # Lazy import to avoid circular dependencies
            from ..llm.models.requests import LLMRequestConfig, LLMRequestType
            from ..llm.models.responses import LLMResponseStatus

            # Create LLM request
            request_config = LLMRequestConfig(
                temperature=0.2,  # Low temperature for consistent results
                max_tokens=2000,  # Sufficient for detailed analysis
                timeout=30,
            )

            # Call LLM service
            response = await self.llm_service.generate(
                prompt=prompt,
                request_type=LLMRequestType.ANALYSIS,
                config=request_config,
            )

            if response.status == LLMResponseStatus.SUCCESS:
                # Write context file for debugging
                self._write_context_file(context_file, prompt, response.content)
                return response.content
            else:
                raise RuntimeError(f"LLM generation failed: {response.error_message}")

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            raise RuntimeError(f"LLM analysis failed: {e}")

    def _write_context_file(
        self, context_file: Path, prompt: str, response: str
    ) -> None:
        """Write context file for debugging purposes."""
        try:
            content = f"""# LLM Matching Analysis Context

## Analysis Timestamp
{datetime.now().isoformat()}

## Domain
{self.domain}

## Prompt
{prompt}

## LLM Response
{response}

## Analysis Notes
This file contains the complete context for the LLM matching analysis.
The LLM was asked to determine if a facility can produce a required item
considering crisis response scenarios and non-standardized terminology.
"""

            context_file.write_text(content)
            logger.debug(f"Wrote context file: {context_file}")

        except Exception as e:
            logger.warning(f"Failed to write context file {context_file}: {e}")

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response and extract matching data."""
        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_str = response[json_start:json_end]
            match_data = json.loads(json_str)

            # Validate required fields
            required_fields = [
                "match_decision",
                "confidence_score",
                "capability_assessment",
            ]
            for field in required_fields:
                if field not in match_data:
                    raise ValueError(f"Missing required field: {field}")

            return match_data

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response content: {response}")

            # Return default no-match data
            return {
                "match_decision": False,
                "confidence_score": 0.0,
                "capability_assessment": {
                    "process_compatibility": {"score": 0.0, "analysis": "Parse error"},
                    "material_availability": {"score": 0.0, "analysis": "Parse error"},
                    "tool_equipment": {"score": 0.0, "analysis": "Parse error"},
                    "expertise_skills": {"score": 0.0, "analysis": "Parse error"},
                    "scale_capacity": {"score": 0.0, "analysis": "Parse error"},
                },
                "overall_analysis": f"Failed to parse LLM response: {str(e)}",
                "key_factors": ["Parse error"],
                "recommendations": ["Check LLM response format"],
                "risks": ["Response parsing failed"],
                "crisis_adaptability": "Unable to assess due to parse error",
            }

    def _create_matching_result_from_analysis(
        self,
        requirement: str,
        capability: str,
        match_data: Dict[str, Any],
        start_time: datetime,
    ) -> MatchingResult:
        """Create MatchingResult from LLM analysis data."""

        # Extract basic match information
        matched = match_data.get("match_decision", False)
        confidence = float(match_data.get("confidence_score", 0.0))

        # Determine match quality based on confidence
        if confidence >= 0.9:
            quality = MatchQuality.SEMANTIC_MATCH
        elif confidence >= 0.7:
            quality = MatchQuality.SEMANTIC_MATCH
        elif confidence >= 0.5:
            quality = MatchQuality.SEMANTIC_MATCH
        else:
            quality = MatchQuality.NO_MATCH

        # Build reasons from analysis
        reasons = []
        if match_data.get("overall_analysis"):
            reasons.append(f"LLM Analysis: {match_data['overall_analysis']}")

        if match_data.get("key_factors"):
            reasons.extend(
                [f"Key Factor: {factor}" for factor in match_data["key_factors"][:3]]
            )

        # Add capability assessment details
        assessment = match_data.get("capability_assessment", {})
        for category, data in assessment.items():
            if isinstance(data, dict) and "score" in data:
                score = data.get("score", 0.0)
                if score > 0.5:
                    reasons.append(f"{category.replace('_', ' ').title()}: {score:.2f}")

        # Calculate processing time
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        return self.create_matching_result(
            requirement=requirement,
            capability=capability,
            matched=matched,
            confidence=confidence,
            method="llm_capability_analysis",
            reasons=reasons,
            quality=quality,
            processing_time_ms=processing_time_ms,
            semantic_similarity=confidence,
        )

    def _cleanup_context_file(self, context_file: Path) -> None:
        """Clean up context file unless preserving for debugging."""
        try:
            if context_file.exists():
                context_file.unlink()
                logger.debug(f"Cleaned up context file: {context_file}")
        except Exception as e:
            logger.warning(f"Failed to cleanup context file {context_file}: {e}")

    async def shutdown(self) -> None:
        """Shutdown the LLM matching layer and cleanup resources."""
        try:
            if self.llm_service:
                await self.llm_service.shutdown()

            # Cleanup context directory unless preserving
            if not self.preserve_context and self.context_dir.exists():
                import shutil

                shutil.rmtree(self.context_dir)
                logger.info("Cleaned up LLM matching context directory")

            logger.info("LLM matching layer shutdown completed")

        except Exception as e:
            logger.error(f"Error during LLM matching layer shutdown: {e}")

    def get_service_status(self) -> Dict[str, Any]:
        """Get the current status of the LLM service."""
        if not self.llm_service:
            return {"status": "not_initialized", "error": "No LLM service"}

        return {
            "status": self.llm_service.status.value,
            "providers": self.llm_service.get_available_providers(),
            "metrics": self.llm_service.get_service_metrics(),
        }
