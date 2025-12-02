"""
File Categorization Service for LLM-based file categorization.

This service provides file categorization using:
- Layer 1: Heuristic rules (FileCategorizationRules)
- Layer 2: LLM content analysis (optional, when LLM available)
- Caching: By file content hash to reduce redundant LLM calls
- Fallback: To Layer 1 when LLM unavailable
"""

import hashlib
import json
import logging
import re
from typing import Dict, List, Optional, Any
from collections import defaultdict

from ..models import FileInfo, AnalysisDepth
from ..utils.file_categorization import (
    FileCategorizationResult,
    FileCategorizationRules,
)
from ..utils.file_content_parser import FileContentParser
from ...models.okh import DocumentationType
from ...llm.models.requests import LLMRequestConfig, LLMRequestType
from ...llm.models.responses import LLMResponseStatus

logger = logging.getLogger(__name__)


class FileCategorizationService:
    """
    Service for file categorization using LLM content analysis.

    This service coordinates between Layer 1 (heuristics) and Layer 2 (LLM)
    to provide accurate file categorization. It supports:
    - Configurable analysis depth (Shallow/Medium/Deep)
    - Per-file depth overrides
    - Caching by file content hash
    - Fallback to Layer 1 when LLM unavailable
    """

    def __init__(
        self,
        llm_service: Optional[Any] = None,  # LLMService type
        repository_mapping_service: Optional[
            Any
        ] = None,  # RepositoryMappingService type
        enable_caching: bool = True,
        min_confidence_for_llm: float = 0.5,  # Only use LLM if Layer 1 confidence < this
    ):
        """
        Initialize file categorization service.

        Args:
            llm_service: Optional LLM service for Layer 2 analysis
            repository_mapping_service: Optional repository mapping service for large repos
            enable_caching: Enable caching by file content hash
            min_confidence_for_llm: Minimum Layer 1 confidence threshold to skip LLM (use Layer 1 directly)
        """
        self.llm_service = llm_service
        self.repository_mapping_service = repository_mapping_service
        self.enable_caching = enable_caching
        self.min_confidence_for_llm = (
            min_confidence_for_llm  # If Layer 1 confidence >= this, skip LLM
        )

        # Initialize components
        self.file_categorization_rules = FileCategorizationRules()
        self.file_content_parser = FileContentParser()

        # Cache for categorization results (key: file content hash, value: FileCategorizationResult)
        self._cache: Dict[str, FileCategorizationResult] = {}

        self.logger = logging.getLogger(__name__)

    async def categorize_files(
        self,
        files: List[FileInfo],
        layer1_suggestions: Dict[str, FileCategorizationResult],
        analysis_depth: AnalysisDepth = AnalysisDepth.SHALLOW,
        per_file_depths: Optional[Dict[str, AnalysisDepth]] = None,
    ) -> Dict[str, FileCategorizationResult]:
        """
        Categorize files using LLM content analysis.

        Args:
            files: List of files to categorize
            layer1_suggestions: Layer 1 heuristic suggestions
            analysis_depth: Global default depth (Shallow/Medium/Deep)
            per_file_depths: Optional per-file depth overrides

        Returns:
            Dictionary mapping file paths to categorization results
        """
        results = {}
        per_file_depths = per_file_depths or {}

        # Check if LLM is available
        llm_available = await self._is_llm_available()

        for file_info in files:
            file_path = file_info.path

            # Skip excluded files
            if (
                file_path in layer1_suggestions
                and layer1_suggestions[file_path].excluded
            ):
                continue

            # Check cache first (if enabled)
            if self.enable_caching:
                cache_key = self._get_cache_key(file_info)
                if cache_key in self._cache:
                    self.logger.debug(f"Using cached categorization for {file_path}")
                    results[file_path] = self._cache[cache_key]
                    continue

            # Get Layer 1 suggestion
            layer1_suggestion = layer1_suggestions.get(file_path)

            # Skip LLM if Layer 1 has high confidence (trust Layer 1 for clear patterns)
            if (
                layer1_suggestion
                and layer1_suggestion.confidence >= self.min_confidence_for_llm
            ):
                self.logger.debug(
                    f"Skipping LLM for {file_path}: Layer 1 confidence {layer1_suggestion.confidence:.2f} >= {self.min_confidence_for_llm}"
                )
                results[file_path] = layer1_suggestion
                continue

            # Determine analysis depth for this file
            file_depth = per_file_depths.get(file_path, analysis_depth)

            # Use Layer 2 (LLM) if available, otherwise use Layer 1
            if llm_available:
                try:
                    categorization = await self._categorize_with_llm(
                        file_info, layer1_suggestion, file_depth
                    )
                    if categorization:
                        # Validate LLM response against Layer 1 for high-confidence suggestions
                        if layer1_suggestion and layer1_suggestion.confidence >= 0.8:
                            # If Layer 1 had high confidence, validate LLM didn't make a mistake
                            if (
                                categorization.documentation_type
                                != layer1_suggestion.documentation_type
                                and not categorization.excluded
                                and not layer1_suggestion.excluded
                            ):
                                # LLM overrode high-confidence Layer 1 - log warning but allow it
                                self.logger.warning(
                                    f"LLM overrode high-confidence Layer 1 suggestion for {file_path}: "
                                    f"Layer 1: {layer1_suggestion.documentation_type.value} (conf: {layer1_suggestion.confidence:.2f}), "
                                    f"LLM: {categorization.documentation_type.value} (conf: {categorization.confidence:.2f})"
                                )

                        results[file_path] = categorization
                        # Cache result
                        if self.enable_caching:
                            cache_key = self._get_cache_key(file_info)
                            self._cache[cache_key] = categorization
                        continue
                except Exception as e:
                    self.logger.warning(
                        f"LLM categorization failed for {file_path}: {e}, falling back to Layer 1"
                    )

            # Fallback to Layer 1
            if file_path in layer1_suggestions:
                results[file_path] = layer1_suggestions[file_path]
            else:
                # If no Layer 1 suggestion, use FileCategorizationRules directly
                from pathlib import Path

                file_path_obj = Path(file_path)
                categorization = self.file_categorization_rules.categorize_file(
                    filename=file_path_obj.name, file_path=file_path
                )
                results[file_path] = categorization

        return results

    async def _is_llm_available(self) -> bool:
        """
        Check if LLM service is available and ready to use.

        This method performs a comprehensive check to determine if LLM
        categorization can be used:
        - Service must exist and be initialized
        - Service must be enabled and healthy
        - At least one provider must be available

        Returns:
            True if LLM service is available and active, False otherwise
        """
        if self.llm_service is None:
            return False

        try:
            # Check if service is initialized and healthy
            # LLMService extends BaseService which has get_status() and is_healthy()
            if not hasattr(self.llm_service, "get_status"):
                # Service doesn't have status methods, assume not available
                return False

            # Check service status
            from ...services.base import ServiceStatus

            service_status = self.llm_service.get_status()
            if service_status != ServiceStatus.ACTIVE:
                # Service is not active (not initialized, error, etc.)
                return False

            # Check if service is healthy
            if not self.llm_service.is_healthy():
                # Service is not healthy
                return False

            # Check if LLM is enabled in configuration
            # LLMServiceConfig extends ServiceConfig which has enabled field
            if hasattr(self.llm_service, "config"):
                config = self.llm_service.config
                if hasattr(config, "enabled") and not config.enabled:
                    # LLM is disabled in configuration
                    return False

            # Check if at least one provider is available (async)
            if hasattr(self.llm_service, "get_available_providers"):
                available_providers = await self.llm_service.get_available_providers()
                if not available_providers or len(available_providers) == 0:
                    # No providers available
                    return False
            else:
                # Fallback: check _providers dict
                if hasattr(self.llm_service, "_providers"):
                    providers = self.llm_service._providers
                    if not providers or len(providers) == 0:
                        return False
                else:
                    # Can't check providers, assume not available
                    return False

            # All checks passed
            return True

        except Exception as e:
            # If any check fails, assume LLM is not available
            self.logger.warning(
                f"Error checking LLM service availability: {e}", exc_info=True
            )
            return False

    async def _categorize_with_llm(
        self,
        file_info: FileInfo,
        layer1_suggestion: Optional[FileCategorizationResult],
        depth: AnalysisDepth,
    ) -> Optional[FileCategorizationResult]:
        """
        Categorize a file using LLM content analysis.

        Args:
            file_info: File to categorize
            layer1_suggestion: Layer 1 suggestion (if available)
            depth: Analysis depth for this file

        Returns:
            FileCategorizationResult or None if LLM categorization fails
        """
        if not self.llm_service:
            return None

        try:
            # Initialize LLM service if needed
            from ...services.base import ServiceStatus

            if self.llm_service.status != ServiceStatus.ACTIVE:
                await self.llm_service.initialize()
            # Parse file content based on analysis depth
            content_preview = self.file_content_parser.parse_content(
                file_info=file_info, depth=depth
            )

            # Build prompt using FileCategorizationPrompts
            from .prompts.file_categorization_prompts import FileCategorizationPrompts

            # Create default Layer 1 suggestion if none provided
            if layer1_suggestion is None:
                from pathlib import Path

                file_path_obj = Path(file_info.path)
                layer1_suggestion = self.file_categorization_rules.categorize_file(
                    filename=file_path_obj.name, file_path=file_info.path
                )

            prompt = FileCategorizationPrompts.build_categorization_prompt(
                file_info=file_info,
                layer1_suggestion=layer1_suggestion,
                content_preview=content_preview or "",
                analysis_depth=depth,
            )

            # Create LLM request config
            config = LLMRequestConfig(
                max_tokens=2000,  # Reasonable limit for categorization
                temperature=0.1,  # Low temperature for consistent output
                timeout=30,
            )

            # Execute LLM request
            response = await self.llm_service.generate(
                prompt=prompt, request_type=LLMRequestType.GENERATION, config=config
            )

            # Check response status
            if response.status != LLMResponseStatus.SUCCESS:
                self.logger.warning(
                    f"LLM categorization failed for {file_info.path}: "
                    f"{response.error_message or 'Unknown error'}"
                )
                return None

            # Parse LLM response
            categorization = self._parse_llm_response(response.content, file_info.path)

            if categorization:
                self.logger.debug(
                    f"LLM categorized {file_info.path} as "
                    f"{categorization.documentation_type.value} "
                    f"(confidence: {categorization.confidence:.1%})"
                )
                return categorization
            else:
                self.logger.warning(
                    f"Failed to parse LLM response for {file_info.path}"
                )
                return None

        except Exception as e:
            self.logger.error(
                f"Error in LLM categorization for {file_info.path}: {e}", exc_info=True
            )
            return None

    def _parse_llm_response(
        self, response_content: str, file_path: str
    ) -> Optional[FileCategorizationResult]:
        """
        Parse LLM response and extract categorization result.

        Args:
            response_content: Raw LLM response content
            file_path: File path for logging

        Returns:
            FileCategorizationResult or None if parsing fails
        """
        try:
            # Extract JSON from response
            json_str = self._extract_json_from_response(response_content)

            if not json_str:
                self.logger.warning(f"No JSON found in LLM response for {file_path}")
                return None

            # Parse JSON with recovery attempts
            data = self._parse_json_with_recovery(json_str)

            if not data:
                self.logger.warning(
                    f"Failed to parse JSON from LLM response for {file_path}"
                )
                return None

            # Extract categorization fields
            doc_type_str = data.get("documentation_type", "").lower()
            confidence = float(data.get("confidence", 0.5))
            excluded = bool(data.get("excluded", False))
            reason = data.get("reason", "LLM categorization")

            # Convert string to DocumentationType
            try:
                doc_type = DocumentationType(doc_type_str)
            except (ValueError, KeyError):
                self.logger.warning(
                    f"Invalid documentation_type '{doc_type_str}' in LLM response for {file_path}"
                )
                return None

            # Validate confidence
            confidence = max(0.0, min(1.0, confidence))

            return FileCategorizationResult(
                documentation_type=doc_type,
                confidence=confidence,
                excluded=excluded,
                reason=reason,
            )

        except Exception as e:
            self.logger.error(
                f"Error parsing LLM response for {file_path}: {e}", exc_info=True
            )
            return None

    def _extract_json_from_response(self, response_content: str) -> Optional[str]:
        """
        Extract JSON from LLM response using multiple strategies.

        Args:
            response_content: Raw LLM response content

        Returns:
            Extracted JSON string or None if no JSON found
        """
        # Strategy 1: Find JSON between first { and last }
        json_start = response_content.find("{")
        json_end = response_content.rfind("}")

        if json_start != -1 and json_end > json_start:
            extracted = response_content[json_start : json_end + 1]

            # Strategy 2: Try to find JSON block (between code fences)
            code_block_markers = ["```json", "```JSON", "```"]
            for marker in code_block_markers:
                if marker in response_content:
                    start_idx = response_content.find(marker)
                    if start_idx != -1:
                        start_idx = response_content.find("\n", start_idx) + 1
                        end_marker = response_content.find("```", start_idx)
                        if end_marker != -1:
                            block_json = response_content[start_idx:end_marker].strip()
                            # Prefer code block extraction if it looks valid
                            if "{" in block_json and "}" in block_json:
                                return block_json

            return extracted

        # Strategy 3: Look for JSON after common keywords
        keywords = ["```json", "```JSON", "JSON:", "json:", "response:", "Response:"]
        for keyword in keywords:
            idx = response_content.find(keyword)
            if idx != -1:
                json_start = response_content.find("{", idx)
                if json_start != -1:
                    json_end = response_content.rfind("}", json_start)
                    if json_end > json_start:
                        return response_content[json_start : json_end + 1]

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

        self.logger.debug(
            f"All JSON recovery attempts failed (first 500 chars): {json_str[:500]}"
        )
        return None

    def _fix_trailing_commas(self, json_str: str) -> str:
        """Fix trailing commas before } or ]"""
        # Remove trailing commas before closing braces/brackets
        fixed = re.sub(r",\s*}", "}", json_str)
        fixed = re.sub(r",\s*]", "]", fixed)
        return fixed

    def _fix_missing_commas(self, json_str: str) -> str:
        """Fix missing commas between object properties"""
        # Add missing commas between properties
        # Pattern: "key": value "key2" -> "key": value, "key2"
        fixed = re.sub(r'"\s*:\s*([^,}\]]+)\s*"', r'": \1, "', json_str)
        # Remove duplicate commas
        fixed = re.sub(r",\s*,", ",", fixed)
        return fixed

    def _remove_json_comments(self, json_str: str) -> str:
        """Remove JSON comments (// and /* */)"""
        # Remove single-line comments
        fixed = re.sub(r"//.*?$", "", json_str, flags=re.MULTILINE)
        # Remove multi-line comments
        fixed = re.sub(r"/\*.*?\*/", "", fixed, flags=re.DOTALL)
        return fixed

    def _get_cache_key(self, file_info: FileInfo) -> str:
        """
        Generate cache key from file content hash.

        Args:
            file_info: File to generate cache key for

        Returns:
            Cache key (hash of file content)
        """
        if file_info.content is None:
            # For files without content, use path as key
            return hashlib.md5(file_info.path.encode("utf-8")).hexdigest()

        # Hash file content
        content_hash = hashlib.md5(file_info.content.encode("utf-8")).hexdigest()
        return content_hash
