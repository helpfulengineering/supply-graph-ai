"""
Direct Matching Layer Implementation

This module implements the Direct Matching layer for the Open Matching Engine (OME).
It provides exact, case-insensitive string matching with detailed metadata tracking
and confidence scoring for both cooking and manufacturing domains.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class MatchQuality(Enum):
    """Quality indicators for matches"""
    PERFECT = "perfect"           # Exact match including case and whitespace
    CASE_DIFFERENCE = "case_diff" # Case difference only
    WHITESPACE_DIFFERENCE = "whitespace_diff"  # Whitespace difference only
    NEAR_MISS = "near_miss"       # Close but not exact (≤2 character differences)
    NO_MATCH = "no_match"         # No match found


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
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class DirectMatchResult:
    """Result of a direct matching operation."""
    requirement: str
    capability: str
    matched: bool
    confidence: float
    metadata: MatchMetadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "requirement": self.requirement,
            "capability": self.capability,
            "matched": self.matched,
            "confidence": self.confidence,
            "metadata": self.metadata.to_dict()
        }


class DirectMatcher(ABC):
    """Abstract base class for direct string matching between requirements and capabilities."""
    
    def __init__(self, domain: str, near_miss_threshold: int = 2):
        """
        Initialize the direct matcher.
        
        Args:
            domain: The domain this matcher operates in (e.g., 'cooking', 'manufacturing')
            near_miss_threshold: Maximum character differences to consider as near-miss
        """
        self.domain = domain
        self.near_miss_threshold = near_miss_threshold
    
    def match(self, requirement: str, capabilities: List[str]) -> List[DirectMatchResult]:
        """
        Perform direct string matching with detailed metadata.
        
        Args:
            requirement: The requirement string to match
            capabilities: List of capability strings to match against
            
        Returns:
            List of DirectMatchResult objects with detailed metadata
        """
        results = []
        requirement_lower = requirement.lower()
        
        for capability in capabilities:
            start_time = datetime.now()
            
            # Perform the matching
            result = self._match_single(requirement, requirement_lower, capability)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            result.metadata.processing_time_ms = processing_time
            
            results.append(result)
        
        return results
    
    def _match_single(self, requirement: str, requirement_lower: str, capability: str) -> DirectMatchResult:
        """
        Match a single requirement against a single capability.
        
        Args:
            requirement: Original requirement string
            requirement_lower: Lowercase version of requirement
            capability: Capability string to match against
            
        Returns:
            DirectMatchResult with detailed metadata
        """
        capability_lower = capability.lower()
        
        # Check for exact match (case-insensitive)
        if requirement_lower == capability_lower:
            # Calculate additional match quality indicators
            case_difference = requirement != capability
            whitespace_difference = self._has_whitespace_difference(requirement, capability)
            
            # Determine quality and confidence
            if not case_difference and not whitespace_difference:
                quality = MatchQuality.PERFECT
                confidence = 1.0
                reasons = ["Exact string match (case and whitespace identical)"]
            elif case_difference and not whitespace_difference:
                quality = MatchQuality.CASE_DIFFERENCE
                confidence = 0.95
                reasons = ["Exact string match (case-insensitive)"]
            elif not case_difference and whitespace_difference:
                quality = MatchQuality.WHITESPACE_DIFFERENCE
                confidence = 0.95
                reasons = ["Exact string match (whitespace difference)"]
            else:
                quality = MatchQuality.CASE_DIFFERENCE  # Both differences
                confidence = 0.9
                reasons = ["Exact string match (case and whitespace differences)"]
            
            # Create detailed metadata
            metadata = MatchMetadata(
                method=f"direct_match_{self.domain}",
                confidence=confidence,
                reasons=reasons,
                case_difference=case_difference,
                whitespace_difference=whitespace_difference,
                quality=quality
            )
            
            return DirectMatchResult(
                requirement=requirement,
                capability=capability,
                matched=True,
                confidence=confidence,
                metadata=metadata
            )
        else:
            # Check for near-miss using Levenshtein distance
            char_diff = self._levenshtein_distance(requirement_lower, capability_lower)
            
            if char_diff <= self.near_miss_threshold:
                # Near miss detected
                metadata = MatchMetadata(
                    method=f"direct_match_{self.domain}",
                    confidence=0.8,  # High but below threshold
                    reasons=[f"Near match with {char_diff} character differences"],
                    character_difference=char_diff,
                    quality=MatchQuality.NEAR_MISS
                )
                
                return DirectMatchResult(
                    requirement=requirement,
                    capability=capability,
                    matched=False,  # Not considered a match by direct matcher
                    confidence=0.8,
                    metadata=metadata
                )
            else:
                # No match
                metadata = MatchMetadata(
                    method=f"direct_match_{self.domain}",
                    confidence=0.0,
                    reasons=[f"No match (Levenshtein distance: {char_diff})"],
                    character_difference=char_diff,
                    quality=MatchQuality.NO_MATCH
                )
                
                return DirectMatchResult(
                    requirement=requirement,
                    capability=capability,
                    matched=False,
                    confidence=0.0,
                    metadata=metadata
                )
    
    def _has_whitespace_difference(self, str1: str, str2: str) -> bool:
        """
        Check if strings differ only in whitespace.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            True if strings differ only in whitespace
        """
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
    
    def _levenshtein_distance(self, str1: str, str2: str) -> int:
        """
        Calculate the Levenshtein distance between two strings.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Number of single-character edits needed to change str1 into str2
        """
        if len(str1) < len(str2):
            return self._levenshtein_distance(str2, str1)
        
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
    
    @abstractmethod
    def get_domain_specific_confidence_adjustments(self, requirement: str, capability: str) -> float:
        """
        Get domain-specific confidence adjustments.
        
        Args:
            requirement: The requirement string
            capability: The capability string
            
        Returns:
            Confidence adjustment factor (0.0 to 1.0)
        """
        pass
