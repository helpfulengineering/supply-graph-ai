"""
Text processing utilities for generation layers.

This module provides centralized text processing functionality including
text cleaning, license extraction, version detection, and content classification.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class ContentClassification:
    """Result of content classification"""

    content_type: str
    process_type: str
    complexity_level: str
    confidence: float


class TextProcessor:
    """Centralized text processing utilities"""

    def __init__(self):
        self._license_patterns = self._initialize_license_patterns()
        self._version_patterns = self._initialize_version_patterns()
        self._process_patterns = self._initialize_process_patterns()
        self._content_type_patterns = self._initialize_content_type_patterns()
        self._complexity_indicators = self._initialize_complexity_indicators()

    def _initialize_license_patterns(self) -> Dict[str, str]:
        """Initialize license detection patterns"""
        return {
            "MIT": r"mit\s+license",
            "Apache-2.0": r"apache\s+license\s+version\s+2\.0|apache\s+2\.0",
            "GPL-3.0": r"gnu\s+general\s+public\s+license\s+version\s+3|gpl\s+v?3",
            "GPL-2.0": r"gnu\s+general\s+public\s+license\s+version\s+2|gpl\s+v?2",
            "BSD-3-Clause": r"bsd\s+3.clause|3.clause\s+bsd",
            "BSD-2-Clause": r"bsd\s+2.clause|2.clause\s+bsd",
            "BSD-1-Clause": r"bsd\s+1.clause|1.clause\s+bsd",
            "CERN-OHL-S-2.0": r"cern\s+open\s+hardware\s+license\s+strongly\s+reciprocal|cern\s+ohl\s+s",
            "CERN-OHL-P-2.0": r"cern\s+open\s+hardware\s+license\s+permissive|cern\s+ohl\s+p",
            "CERN-OHL-W-2.0": r"cern\s+open\s+hardware\s+license\s+weakly\s+reciprocal|cern\s+ohl\s+w",
            "CERN-OHL-1.2": r"cern\s+open\s+hardware\s+licen[cs]e\s+v?1\.2|cern\s+ohl\s+v?1\.2",
            "TAPR-OHL-1.0": r"tapr.*open.*hardware.*licen[cs]e|tapr.*ohl",
            "CC-BY-4.0": r"creative\s+commons\s+attribution\s+4\.0|cc\s+by\s+4\.0",
            "CC-BY-SA-4.0": r"creative\s+commons\s+attribution.sharealike\s+4\.0|cc\s+by.sa\s+4\.0",
            "Unlicense": r"unlicense|public\s+domain",
            "ISC": r"isc\s+license",
            "LGPL-3.0": r"gnu\s+lesser\s+general\s+public\s+license\s+version\s+3|lgpl\s+v?3",
            "LGPL-2.1": r"gnu\s+lesser\s+general\s+public\s+license\s+version\s+2\.1|lgpl\s+v?2\.1",
        }

    def _initialize_version_patterns(self) -> List[str]:
        """Initialize version detection patterns"""
        return [
            r"v?(\d+\.\d+\.\d+)",  # v1.2.3 or 1.2.3
            r"v?(\d+\.\d+)",  # v1.2 or 1.2
            r"version\s+(\d+\.\d+\.\d+)",  # version 1.2.3
            r"version\s+(\d+\.\d+)",  # version 1.2
            r"release\s+(\d+\.\d+\.\d+)",  # release 1.2.3
            r"release\s+(\d+\.\d+)",  # release 1.2
            r"(\d+\.\d+\.\d+[a-zA-Z]*)",  # 1.2.3a, 1.2.3-beta
            r"(\d+\.\d+[a-zA-Z]*)",  # 1.2a, 1.2-beta
        ]

    def _initialize_process_patterns(self) -> Dict[str, str]:
        """Initialize manufacturing process detection patterns"""
        return {
            "3D Printing": r"3d\s+print|3d\s+printing|fused\s+deposition|fdm|sla|sls",
            "Laser cutting": r"laser\s+cut|laser\s+cutting|laser\s+engrave",
            "CNC machining": r"cnc|machining|mill|mill|lathe|turning",
            "Soldering": r"solder|soldering|smt|through.hole",
            "Assembly": r"assemble|assembly|mount|install|attach",
            "Welding": r"weld|welding|tig|mig|arc\s+welding",
            "Cutting": r"cut|cutting|saw|shear|plasma\s+cut",
            "Drilling": r"drill|drilling|bore|ream",
            "Bending": r"bend|bending|fold|folding",
            "Grinding": r"grind|grinding|polish|polishing|sand|sanding",
            "Painting": r"paint|painting|coat|coating|primer",
            "Anodizing": r"anodiz|anodizing|anodize",
            "Heat treatment": r"heat\s+treat|anneal|temper|quench",
            "Injection molding": r"injection\s+mold|molding|moulding",
            "Casting": r"cast|casting|foundry|pour",
            "Forging": r"forge|forging|hammer|press",
        }

    def _initialize_content_type_patterns(self) -> Dict[str, List[str]]:
        """Initialize content type detection patterns"""
        return {
            "assembly_instructions": [
                "assembly",
                "assemble",
                "build",
                "construct",
                "put together",
                "step by step",
                "instructions",
                "guide",
                "tutorial",
            ],
            "operating_instructions": [
                "operation",
                "operate",
                "usage",
                "use",
                "manual",
                "user guide",
                "how to use",
                "getting started",
                "quick start",
            ],
            "manufacturing_instructions": [
                "manufacturing",
                "production",
                "fabrication",
                "make",
                "create",
                "manufacture",
                "produce",
                "fabricate",
            ],
            "technical_specifications": [
                "specification",
                "spec",
                "technical",
                "dimensions",
                "tolerance",
                "parameter",
                "requirement",
                "standard",
            ],
            "troubleshooting": [
                "troubleshoot",
                "troubleshooting",
                "problem",
                "issue",
                "error",
                "fix",
                "solution",
                "debug",
                "diagnose",
            ],
            "safety_instructions": [
                "safety",
                "warning",
                "caution",
                "danger",
                "hazard",
                "risk",
                "precaution",
                "protective",
                "ppe",
            ],
            "maintenance": [
                "maintenance",
                "maintain",
                "service",
                "repair",
                "calibrate",
                "inspect",
                "clean",
                "lubricate",
            ],
        }

    def _initialize_complexity_indicators(self) -> Dict[str, List[str]]:
        """Initialize complexity level indicators"""
        return {
            "beginner": [
                "simple",
                "easy",
                "basic",
                "beginner",
                "introductory",
                "starter",
                "no experience",
                "no prior knowledge",
                "straightforward",
            ],
            "intermediate": [
                "intermediate",
                "moderate",
                "some experience",
                "basic knowledge",
                "familiar with",
                "comfortable with",
                "standard",
            ],
            "advanced": [
                "advanced",
                "expert",
                "complex",
                "sophisticated",
                "professional",
                "experienced",
                "skilled",
                "technical",
                "specialized",
            ],
        }

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.

        Args:
            text: Raw text content

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove common markdown artifacts
        text = re.sub(r"#{1,6}\s*", "", text)  # Remove headers
        text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)  # Remove bold/italic
        text = re.sub(r"`([^`]+)`", r"\1", text)  # Remove inline code
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # Remove links

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Normalize quotes (avoiding smart quotes for now)
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(""", "'").replace(""", "'")

        # Remove excessive punctuation
        text = re.sub(r"[.]{2,}", ".", text)
        text = re.sub(r"[!]{2,}", "!", text)
        text = re.sub(r"[?]{2,}", "?", text)

        return text.strip()

    def extract_license_type(self, content: str) -> Optional[str]:
        """
        Extract license type from content.

        Args:
            content: License file content or text containing license information

        Returns:
            License type identifier, or None if not found
        """
        if not content:
            return None

        content_lower = content.lower()

        # Check for exact matches first
        for license_type, pattern in self._license_patterns.items():
            if re.search(pattern, content_lower):
                return license_type

        # Check for common license indicators
        if "no license" in content_lower or "unlicensed" in content_lower:
            return "Unlicense"

        if "proprietary" in content_lower or "all rights reserved" in content_lower:
            return "Proprietary"

        return None

    def extract_version_from_text(self, text: str) -> Optional[str]:
        """
        Extract version information from text.

        Args:
            text: Text content to search for version information

        Returns:
            Version string, or None if not found
        """
        if not text:
            return None

        text_lower = text.lower()

        # Try each version pattern
        for pattern in self._version_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                # Return the first match, preferring longer versions
                versions = sorted(matches, key=len, reverse=True)
                return versions[0]

        return None

    def extract_manufacturing_processes(self, text: str) -> List[str]:
        """
        Extract manufacturing processes from text.

        Args:
            text: Text content to analyze

        Returns:
            List of detected manufacturing processes
        """
        if not text:
            return []

        text_lower = text.lower()
        processes = []

        for process_name, pattern in self._process_patterns.items():
            if re.search(pattern, text_lower) and process_name not in processes:
                processes.append(process_name)

        return processes

    def classify_content_type(self, text: str) -> ContentClassification:
        """
        Classify the type of content.

        Args:
            text: Text content to classify

        Returns:
            Content classification result
        """
        if not text:
            return ContentClassification(
                content_type="unknown",
                process_type="unknown",
                complexity_level="unknown",
                confidence=0.0,
            )

        text_lower = text.lower()

        # Determine content type
        content_type = "general"
        content_confidence = 0.0

        for content_type_name, keywords in self._content_type_patterns.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > 0:
                confidence = min(matches / len(keywords), 1.0)
                if confidence > content_confidence:
                    content_type = content_type_name
                    content_confidence = confidence

        # Determine process type
        processes = self.extract_manufacturing_processes(text)
        process_type = "general"
        if processes:
            process_type = processes[0]  # Use the first detected process

        # Determine complexity level
        complexity_level = "intermediate"  # Default
        complexity_confidence = 0.0

        for level, indicators in self._complexity_indicators.items():
            matches = sum(1 for indicator in indicators if indicator in text_lower)
            if matches > 0:
                confidence = min(matches / len(indicators), 1.0)
                if confidence > complexity_confidence:
                    complexity_level = level
                    complexity_confidence = confidence

        # Calculate overall confidence
        overall_confidence = (content_confidence + complexity_confidence) / 2

        return ContentClassification(
            content_type=content_type,
            process_type=process_type,
            complexity_level=complexity_level,
            confidence=overall_confidence,
        )

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from text.

        Args:
            text: Text content to analyze
            max_keywords: Maximum number of keywords to return

        Returns:
            List of extracted keywords
        """
        if not text:
            return []

        # Clean text
        cleaned_text = self.clean_text(text)

        # Simple keyword extraction (can be enhanced with NLP)
        words = re.findall(r"\b[a-zA-Z]{3,}\b", cleaned_text.lower())

        # Filter out common stop words
        stop_words = {
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "up",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "among",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
            "my",
            "your",
            "his",
            "her",
            "its",
            "our",
            "their",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "shall",
            "a",
            "an",
            "some",
            "any",
            "all",
            "both",
            "each",
            "every",
            "other",
            "another",
            "such",
            "no",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "now",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "what",
            "which",
            "who",
            "whom",
            "whose",
        }

        # Count word frequency
        word_counts = {}
        for word in words:
            if word not in stop_words and len(word) > 2:
                word_counts[word] = word_counts.get(word, 0) + 1

        # Sort by frequency and return top keywords
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:max_keywords]]

    def extract_measurements(self, text: str) -> List[Dict[str, str]]:
        """
        Extract measurements and dimensions from text.

        Args:
            text: Text content to analyze

        Returns:
            List of measurement dictionaries with 'value', 'unit', and 'context'
        """
        if not text:
            return []

        # Pattern for measurements (e.g., "10mm", "5.5 inches", "2.5cm")
        measurement_pattern = (
            r"(\d+(?:\.\d+)?)\s*(mm|cm|m|inch|inches|in|ft|feet|ft|°|deg|degrees)"
        )

        measurements = []
        for match in re.finditer(measurement_pattern, text, re.IGNORECASE):
            value = match.group(1)
            unit = match.group(2).lower()

            # Get context (surrounding words)
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            context = text[start:end].strip()

            measurements.append({"value": value, "unit": unit, "context": context})

        return measurements

    def is_technical_content(self, text: str) -> bool:
        """
        Determine if text contains technical content.

        Args:
            text: Text content to analyze

        Returns:
            True if text appears to be technical
        """
        if not text:
            return False

        text_lower = text.lower()

        # Technical indicators
        technical_terms = [
            "specification",
            "dimension",
            "tolerance",
            "parameter",
            "voltage",
            "current",
            "resistance",
            "frequency",
            "wavelength",
            "temperature",
            "pressure",
            "force",
            "torque",
            "speed",
            "rpm",
            "accuracy",
            "precision",
            "calibration",
            "measurement",
            "sensor",
            "actuator",
            "controller",
            "algorithm",
            "protocol",
            "interface",
            "api",
            "database",
            "software",
            "hardware",
            "firmware",
            "circuit",
            "schematic",
            "pcb",
            "component",
        ]

        # Count technical terms
        technical_count = sum(1 for term in technical_terms if term in text_lower)

        # Consider it technical if it has multiple technical terms
        return technical_count >= 3
