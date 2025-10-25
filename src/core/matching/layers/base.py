"""
Base classes for matching layers.

This module defines the abstract base classes and interfaces that all
matching layers must implement, along with shared utilities for
requirement-capability matching, confidence calculation, and result processing.

The base layer architecture provides:
- Standardized interfaces for all matching layers
- Shared utilities for common matching operations
- Consistent error handling and logging
- Configuration management
- Result processing and validation

All matching layers inherit from BaseMatchingLayer and must implement
the async match() method. The base class provides comprehensive utilities
for string matching, confidence calculation, and result processing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
from datetime import datetime, timedelta
import logging
import re

# Configure logging
logger = logging.getLogger(__name__)


class MatchingLayer(Enum):
    """Types of matching layers in the 4-layer architecture."""
    DIRECT = "direct"           # Direct string matching
    HEURISTIC = "heuristic"     # Rule-based matching
    NLP = "nlp"                 # Natural language processing
    LLM = "llm"                 # Large language model matching


class MatchQuality(Enum):
    """Quality indicators for matches."""
    PERFECT = "perfect"                    # Exact match including case and whitespace
    CASE_DIFFERENCE = "case_diff"          # Case difference only
    WHITESPACE_DIFFERENCE = "whitespace_diff"  # Whitespace difference only
    NEAR_MISS = "near_miss"                # Close but not exact (≤2 character differences)
    RULE_MATCH = "rule_match"              # Matched by heuristic rules
    SEMANTIC_MATCH = "semantic_match"      # Matched by NLP/LLM semantic analysis
    NO_MATCH = "no_match"                  # No match found


@dataclass
class MatchingMetrics:
    """Metrics for tracking matching performance and usage."""
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    matches_found: int = 0
    total_requirements: int = 0
    total_capabilities: int = 0
    processing_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get matching duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def match_rate(self) -> float:
        """Get match rate (matches found / total requirements)."""
        if self.total_requirements == 0:
            return 0.0
        return self.matches_found / self.total_requirements


@dataclass
class MatchMetadata:
    """Detailed metadata about a match operation."""
    method: str
    confidence: float
    reasons: List[str]
    character_difference: int = 0
    case_difference: bool = False
    whitespace_difference: bool = False
    quality: MatchQuality = MatchQuality.NO_MATCH
    processing_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    rule_used: Optional[str] = None
    semantic_similarity: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        return {
            "method": self.method,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "character_difference": self.character_difference,
            "case_difference": self.case_difference,
            "whitespace_difference": self.whitespace_difference,
            "quality": self.quality.value,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "rule_used": self.rule_used,
            "semantic_similarity": self.semantic_similarity
        }


@dataclass
class MatchingResult:
    """Result of a matching operation between requirements and capabilities."""
    requirement: str
    capability: str
    matched: bool
    confidence: float
    metadata: MatchMetadata
    layer_type: MatchingLayer
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "requirement": self.requirement,
            "capability": self.capability,
            "matched": self.matched,
            "confidence": self.confidence,
            "metadata": self.metadata.to_dict(),
            "layer_type": self.layer_type.value
        }


class BaseMatchingLayer(ABC):
    """
    Abstract base class for all matching layers.
    
    This class defines the interface that all matching layers must implement
    and provides common utilities for requirement-capability matching,
    confidence calculation, and result processing.
    
    Attributes:
        layer_type: The type of matching layer
        domain: The domain this layer operates in (e.g., 'manufacturing', 'cooking')
        metrics: Current matching metrics
    """
    
    def __init__(self, layer_type: MatchingLayer, domain: str = "general"):
        """
        Initialize the matching layer.
        
        Args:
            layer_type: The type of matching layer
            domain: The domain this layer operates in
        """
        self.layer_type = layer_type
        self.domain = domain
        self.metrics: Optional[MatchingMetrics] = None
        
        logger.info(f"Initialized {layer_type.value} matching layer for domain: {domain}")
    
    @abstractmethod
    async def match(self, requirements: List[str], capabilities: List[str]) -> List[MatchingResult]:
        """
        Match requirements to capabilities using this layer's method.
        
        Args:
            requirements: List of requirement strings to match
            capabilities: List of capability strings to match against
            
        Returns:
            List of MatchingResult objects with detailed metadata
            
        Raises:
            ValueError: If requirements or capabilities are invalid
            RuntimeError: If matching fails due to configuration issues
        """
        pass
    
    def start_matching(self, requirements: List[str], capabilities: List[str]) -> None:
        """
        Start tracking matching metrics.
        
        Args:
            requirements: List of requirements being matched
            capabilities: List of capabilities being matched against
        """
        # Handle None inputs gracefully
        req_count = len(requirements) if requirements is not None else 0
        cap_count = len(capabilities) if capabilities is not None else 0
        
        self.metrics = MatchingMetrics(
            start_time=datetime.now(),
            total_requirements=req_count,
            total_capabilities=cap_count
        )
        logger.info(f"Starting {self.layer_type.value} matching: {req_count} requirements vs {cap_count} capabilities")
    
    def end_matching(self, success: bool, matches_found: int = 0) -> None:
        """
        End tracking matching metrics.
        
        Args:
            success: Whether matching was successful
            matches_found: Number of matches found
        """
        if self.metrics:
            self.metrics.end_time = datetime.now()
            self.metrics.success = success
            self.metrics.matches_found = matches_found
            
            if self.metrics.start_time:
                duration = self.metrics.duration
                if duration:
                    self.metrics.processing_time_ms = duration.total_seconds() * 1000
            
            duration = self.metrics.duration
            if duration:
                logger.info(f"Matching completed in {duration.total_seconds():.2f}s - "
                          f"Success: {success}, Matches: {matches_found}/{self.metrics.total_requirements}")
    
    def add_error(self, error: str) -> None:
        """
        Add an error to the current matching metrics.
        
        Args:
            error: Error message to add
        """
        if self.metrics:
            self.metrics.errors.append(error)
        logger.error(f"{self.layer_type.value} matching error: {error}")
    
    def get_metrics(self) -> Optional[MatchingMetrics]:
        """
        Get current matching metrics.
        
        Returns:
            Current MatchingMetrics or None if no matching in progress
        """
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Reset matching metrics."""
        self.metrics = None
    
    def validate_inputs(self, requirements: List[str], capabilities: List[str]) -> bool:
        """
        Validate input requirements and capabilities.
        
        Args:
            requirements: List of requirement strings
            capabilities: List of capability strings
            
        Returns:
            True if inputs are valid, False otherwise
        """
        if requirements is None:
            self.add_error("Requirements list cannot be None")
            return False
        
        if capabilities is None:
            self.add_error("Capabilities list cannot be None")
            return False
        
        if not requirements:
            self.add_error("Requirements list cannot be empty")
            return False
        
        if not capabilities:
            self.add_error("Capabilities list cannot be empty")
            return False
        
        # Check for empty or None requirements
        for i, req in enumerate(requirements):
            if not req or not req.strip():
                self.add_error(f"Requirement at index {i} is empty or None")
                return False
        
        # Check for empty or None capabilities
        for i, cap in enumerate(capabilities):
            if not cap or not cap.strip():
                self.add_error(f"Capability at index {i} is empty or None")
                return False
        
        return True
    
    def create_matching_result(self, requirement: str, capability: str, 
                             matched: bool, confidence: float, 
                             method: str, reasons: List[str],
                             quality: MatchQuality = MatchQuality.NO_MATCH,
                             **kwargs) -> MatchingResult:
        """
        Create a MatchingResult with standardized metadata.
        
        Args:
            requirement: The requirement string
            capability: The capability string
            matched: Whether a match was found
            confidence: Confidence score (0.0 to 1.0)
            method: Method used for matching
            reasons: List of reasons for the match/no-match
            quality: Quality indicator for the match
            **kwargs: Additional metadata fields
            
        Returns:
            MatchingResult object
        """
        # Validate confidence score
        if not 0.0 <= confidence <= 1.0:
            logger.warning(f"Invalid confidence score {confidence}, clamping to [0.0, 1.0]")
            confidence = max(0.0, min(1.0, confidence))
        
        metadata = MatchMetadata(
            method=f"{method}_{self.domain}",
            confidence=confidence,
            reasons=reasons,
            quality=quality,
            **kwargs
        )
        
        return MatchingResult(
            requirement=requirement,
            capability=capability,
            matched=matched,
            confidence=confidence,
            metadata=metadata,
            layer_type=self.layer_type
        )
    
    def log_matching_start(self, requirements: List[str], capabilities: List[str]) -> None:
        """Log the start of matching operation."""
        req_count = len(requirements) if requirements is not None else 0
        cap_count = len(capabilities) if capabilities is not None else 0
        logger.info(f"[{self.layer_type.value}] Starting matching: {req_count} requirements vs {cap_count} capabilities")
    
    def log_matching_end(self, results: List[MatchingResult]) -> None:
        """Log the end of matching operation."""
        matches_found = sum(1 for r in results if r.matched)
        logger.info(f"[{self.layer_type.value}] Matching completed: {matches_found}/{len(results)} matches found")
    
    def handle_matching_error(self, error: Exception, results: List[MatchingResult]) -> List[MatchingResult]:
        """
        Handle matching errors gracefully.
        
        Args:
            error: The exception that occurred
            results: Current results list
            
        Returns:
            Results list with error information added
        """
        error_msg = f"Matching error in {self.layer_type.value} layer: {str(error)}"
        self.add_error(error_msg)
        logger.error(error_msg, exc_info=True)
        return results
    
    def calculate_levenshtein_distance(self, str1: str, str2: str) -> int:
        """
        Calculate the Levenshtein distance between two strings.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Number of single-character edits needed to change str1 into str2
        """
        if len(str1) < len(str2):
            return self.calculate_levenshtein_distance(str2, str1)
        
        if len(str2) == 0:
            return len(str1)
        
        previous_row = list(range(len(str2) + 1))
        for i, c1 in enumerate(str1):
            current_row = [i + 1]
            for j, c2 in enumerate(str2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def has_whitespace_difference(self, str1: str, str2: str) -> bool:
        """
        Check if strings differ only in whitespace.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            True if strings differ only in whitespace
        """
        import re
        
        # Check if strings are identical when normalized
        norm1 = re.sub(r'\s+', ' ', str1.strip())
        norm2 = re.sub(r'\s+', ' ', str2.strip())
        
        # If normalized strings are the same, check if original strings differ
        if norm1 == norm2:
            # Check if original strings differ in whitespace
            # Remove all whitespace and compare
            no_ws1 = re.sub(r'\s', '', str1)
            no_ws2 = re.sub(r'\s', '', str2)
            return no_ws1 == no_ws2 and str1 != str2
        else:
            # Strings differ in content, not just whitespace
            return False

    def normalize_process_name(self, process_name: str) -> str:
        """
        Normalize process names for better matching.
        
        This method handles:
        - Wikipedia URLs: Extracts the process name from URLs
        - Case normalization: Converts to lowercase
        - Whitespace normalization: Removes extra whitespace
        - Special character handling: Normalizes underscores, hyphens, etc.
        
        Args:
            process_name: The process name to normalize
            
        Returns:
            Normalized process name
        """
        if not process_name:
            return ""
        
        # Handle Wikipedia URLs
        if "wikipedia.org/wiki/" in process_name.lower():
            # Extract the process name from Wikipedia URL
            # e.g., "https://en.wikipedia.org/wiki/PCB_assembly" -> "PCB_assembly"
            parts = process_name.split("/wiki/")
            if len(parts) > 1:
                process_name = parts[1]
        
        # Normalize case and whitespace
        normalized = process_name.strip().lower()
        
        # Normalize special characters
        # Replace underscores and hyphens with spaces for better matching
        normalized = re.sub(r'[_\-]+', ' ', normalized)
        
        # Normalize multiple spaces to single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()
