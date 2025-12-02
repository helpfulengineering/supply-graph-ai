"""
NLP Matching Layer Implementation

This module implements the NLP Matching layer for the Open Matching Engine (OME).
It provides natural language processing-based matching for semantic understanding
between requirements and capabilities.

This layer is part of the 4-layer matching architecture and inherits from
BaseMatchingLayer to ensure consistent interfaces and error handling.

The implementation uses spaCy for semantic similarity and entity recognition,
following the same pattern as the generation system's NLP layer.
"""

import asyncio
import logging
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

# Import spaCy for NLP processing
try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None

from .layers.base import BaseMatchingLayer, MatchingLayer, MatchingResult, MatchQuality

logger = logging.getLogger(__name__)


class NLPMatcher(BaseMatchingLayer):
    """
    NLP matching layer using natural language processing for semantic understanding.

    This layer provides semantic matching between requirements and capabilities
    using natural language processing techniques. It can understand synonyms,
    related terms, and semantic relationships that direct and heuristic matching
    might miss.

    Features:
    - Semantic similarity matching using spaCy
    - Synonym and related term detection
    - Context-aware matching
    - Configurable similarity thresholds
    - Comprehensive metadata tracking
    - Fallback to string similarity when spaCy is not available

    The implementation follows the same pattern as the generation system's NLP layer,
    using spaCy with preference for en_core_web_md (with word vectors) for semantic understanding.
    Falls back to en_core_web_lg or en_core_web_sm if md is not available.
    """

    def __init__(self, domain: str = "general", similarity_threshold: float = None):
        """
        Initialize the NLP matcher with lazy loading for memory efficiency.

        Args:
            domain: The domain this matcher operates in
            similarity_threshold: Minimum similarity score for matches (0.0 to 1.0)
                                 If None, uses domain-specific defaults optimized for en_core_web_md
        """
        super().__init__(MatchingLayer.NLP, domain)

        # Set domain-specific default thresholds optimized for en_core_web_md
        if similarity_threshold is None:
            if domain == "manufacturing":
                similarity_threshold = 0.3  # Optimized for manufacturing domain
            elif domain == "cooking":
                similarity_threshold = 0.4  # Slightly higher for cooking
            else:
                similarity_threshold = 0.4  # General default

        self.similarity_threshold = similarity_threshold

        # Validate similarity threshold
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(
                f"Similarity threshold must be between 0.0 and 1.0, got {similarity_threshold}"
            )

        # Lazy loading - don't initialize spaCy until first use to save memory
        self._nlp = None
        self._nlp_initialized = False
        self._domain_patterns = None
        self._patterns_initialized = False

    def _ensure_nlp_initialized(self):
        """Lazy initialization of spaCy NLP model to save memory"""
        if self._nlp_initialized:
            return self._nlp

        if not SPACY_AVAILABLE:
            logger.warning(
                "spaCy not available. NLP matching will use fallback string similarity."
            )
            self._nlp_initialized = True
            return None

        # Try to load models in order of preference (best to fallback)
        model_preferences = ["en_core_web_md", "en_core_web_lg", "en_core_web_sm"]

        for model_name in model_preferences:
            try:
                logger.info(f"Loading spaCy model '{model_name}' (lazy loading)")
                self._nlp = spacy.load(model_name)
                has_vectors = self._nlp.vocab.vectors.size > 0
                logger.info(
                    f"spaCy model '{model_name}' loaded successfully (vectors: {has_vectors})"
                )
                break
            except OSError:
                logger.warning(f"spaCy model '{model_name}' not found, trying next...")
                continue

        if self._nlp is None:
            logger.warning(
                "No spaCy models found. NLP matching will use fallback string similarity."
            )

        self._nlp_initialized = True
        return self._nlp

    def _ensure_domain_patterns_initialized(self):
        """Lazy initialization of domain patterns to save memory"""
        if self._patterns_initialized:
            return self._domain_patterns

        self._domain_patterns = {
            "manufacturing": {
                "processes": [
                    "machining",
                    "cnc",
                    "milling",
                    "turning",
                    "drilling",
                    "grinding",
                    "3d printing",
                    "additive manufacturing",
                    "laser cutting",
                    "cutting",
                    "welding",
                    "assembly",
                    "finishing",
                    "surface treatment",
                    "coating",
                ],
                "materials": [
                    "steel",
                    "aluminum",
                    "plastic",
                    "wood",
                    "ceramic",
                    "composite",
                    "metal",
                    "polymer",
                    "resin",
                    "filament",
                    "powder",
                ],
                "tools": [
                    "cnc machine",
                    "mill",
                    "lathe",
                    "drill",
                    "grinder",
                    "3d printer",
                    "laser cutter",
                    "welder",
                    "press",
                    "mold",
                    "die",
                ],
            },
            "cooking": {
                "techniques": [
                    "sautéing",
                    "roasting",
                    "boiling",
                    "grilling",
                    "baking",
                    "frying",
                    "steaming",
                    "braising",
                    "poaching",
                    "simmering",
                    "searing",
                ],
                "equipment": [
                    "pan",
                    "pot",
                    "oven",
                    "stove",
                    "grill",
                    "microwave",
                    "blender",
                    "mixer",
                    "knife",
                    "cutting board",
                    "whisk",
                    "spatula",
                ],
                "ingredients": [
                    "flour",
                    "sugar",
                    "salt",
                    "pepper",
                    "oil",
                    "butter",
                    "eggs",
                    "milk",
                    "cheese",
                    "meat",
                    "vegetables",
                    "herbs",
                    "spices",
                ],
            },
        }

        self._patterns_initialized = True
        return self._domain_patterns

    async def match(
        self, requirements: List[str], capabilities: List[str]
    ) -> List[MatchingResult]:
        """
        Match requirements to capabilities using NLP semantic analysis.

        Args:
            requirements: List of requirement strings to match
            capabilities: List of capability strings to match against

        Returns:
            List of MatchingResult objects with detailed metadata

        Raises:
            ValueError: If requirements or capabilities are invalid
            RuntimeError: If matching fails due to configuration issues
        """
        # Start tracking metrics
        self.start_matching(requirements, capabilities)
        self.log_matching_start(requirements, capabilities)

        try:
            # Validate inputs
            if not self.validate_inputs(requirements, capabilities):
                self.end_matching(success=False)
                return []

            results = []

            # Match each requirement against each capability
            for requirement in requirements:
                for capability in capabilities:
                    result = await self._match_single(requirement, capability)
                    results.append(result)

            # End metrics tracking
            matches_found = sum(1 for r in results if r.matched)
            self.end_matching(success=True, matches_found=matches_found)
            self.log_matching_end(results)

            return results

        except Exception as e:
            return self.handle_matching_error(e, [])

    async def _match_single(self, requirement: str, capability: str) -> MatchingResult:
        """
        Match a single requirement against a single capability using NLP.

        Args:
            requirement: The requirement string
            capability: The capability string

        Returns:
            MatchingResult with detailed metadata
        """
        try:
            # Calculate semantic similarity
            similarity = await self.calculate_semantic_similarity(
                requirement, capability
            )

            # Determine if this is a match based on threshold
            matched = similarity >= self.similarity_threshold

            # Determine match quality
            if similarity >= 0.9:
                quality = MatchQuality.SEMANTIC_MATCH
            elif similarity >= 0.7:
                quality = MatchQuality.SEMANTIC_MATCH
            else:
                quality = MatchQuality.NO_MATCH

            # Generate reasons for the match/no-match
            reasons = []
            if matched:
                reasons.append(
                    f"Semantic similarity {similarity:.3f} >= threshold {self.similarity_threshold}"
                )
                nlp = self._ensure_nlp_initialized()
                if nlp:
                    reasons.append("spaCy semantic analysis")
                else:
                    reasons.append("String similarity fallback")
            else:
                reasons.append(
                    f"Semantic similarity {similarity:.3f} < threshold {self.similarity_threshold}"
                )

            # Add domain-specific context
            domain_patterns = self._ensure_domain_patterns_initialized()
            if self.domain in domain_patterns:
                domain_context = self._analyze_domain_context(requirement, capability)
                if domain_context:
                    reasons.append(domain_context)

            return self.create_matching_result(
                requirement=requirement,
                capability=capability,
                matched=matched,
                confidence=similarity,
                method="nlp_semantic_match",
                reasons=reasons,
                quality=quality,
                semantic_similarity=similarity,
            )

        except Exception as e:
            logger.error(f"Error in NLP matching: {e}", exc_info=True)
            return self.create_matching_result(
                requirement=requirement,
                capability=capability,
                matched=False,
                confidence=0.0,
                method="nlp_semantic_match",
                reasons=[f"Error in NLP matching: {str(e)}"],
                quality=MatchQuality.NO_MATCH,
                semantic_similarity=0.0,
            )

    async def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two text strings with domain context awareness.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0

        # Normalize text
        text1 = self._normalize_text(text1)
        text2 = self._normalize_text(text2)

        # Enhance texts with domain context for better semantic understanding
        context_enhanced_text1 = self._enhance_with_domain_context(text1)
        context_enhanced_text2 = self._enhance_with_domain_context(text2)

        # If spaCy is available, use semantic similarity with context
        nlp = self._ensure_nlp_initialized()
        if nlp:
            try:
                # Process context-enhanced texts with spaCy
                doc1 = nlp(context_enhanced_text1)
                doc2 = nlp(context_enhanced_text2)

                # Calculate semantic similarity
                similarity = doc1.similarity(doc2)

                # Apply domain-specific boosting for known manufacturing terms
                domain_boost = self._calculate_domain_boost(text1, text2)
                boosted_similarity = min(1.0, similarity + domain_boost)

                return max(0.0, min(1.0, boosted_similarity))  # Clamp to [0, 1]

            except Exception as e:
                logger.warning(
                    f"spaCy similarity calculation failed: {e}, falling back to string similarity"
                )

        # Fallback to string similarity with domain context
        return self._calculate_string_similarity_with_context(text1, text2)

    async def find_synonyms(self, term: str) -> List[str]:
        """
        Find synonyms for a given term.

        Args:
            term: The term to find synonyms for

        Returns:
            List of synonym strings
        """
        synonyms = []

        # Check domain-specific patterns for synonyms
        domain_patterns = self._ensure_domain_patterns_initialized()
        if self.domain in domain_patterns:
            domain_patterns = domain_patterns[self.domain]
            normalized_term = self._normalize_text(term)

            for category, terms in domain_patterns.items():
                for pattern_term in terms:
                    if self._normalize_text(pattern_term) == normalized_term:
                        # Add other terms from the same category as potential synonyms
                        synonyms.extend([t for t in terms if t != pattern_term])
                        break

        # If spaCy is available, use WordNet for additional synonyms
        nlp = self._ensure_nlp_initialized()
        if nlp:
            try:
                doc = nlp(term)
                for token in doc:
                    if token.has_vector:
                        # Find similar words using spaCy's similarity
                        for word in nlp.vocab:
                            if word.has_vector and word.is_lower and word.is_alpha:
                                similarity = token.similarity(word)
                                if similarity > 0.7 and word.text != term.lower():
                                    synonyms.append(word.text)
            except Exception as e:
                logger.warning(f"spaCy synonym detection failed: {e}")

        return list(set(synonyms))  # Remove duplicates

    async def extract_key_concepts(self, text: str) -> List[str]:
        """
        Extract key concepts from text.

        Args:
            text: The text to extract concepts from

        Returns:
            List of key concept strings
        """
        concepts = []

        if not text:
            return concepts

        # Normalize text
        normalized_text = self._normalize_text(text)

        # Extract domain-specific concepts
        domain_patterns = self._ensure_domain_patterns_initialized()
        if self.domain in domain_patterns:
            domain_patterns = domain_patterns[self.domain]
            for category, terms in domain_patterns.items():
                for term in terms:
                    if self._normalize_text(term) in normalized_text:
                        concepts.append(term)

        # If spaCy is available, use NER for additional concepts
        nlp = self._ensure_nlp_initialized()
        if nlp:
            try:
                doc = nlp(text)
                for ent in doc.ents:
                    if ent.label_ in [
                        "ORG",
                        "PRODUCT",
                        "TECHNOLOGY",
                        "MONEY",
                        "QUANTITY",
                    ]:
                        concepts.append(ent.text)
            except Exception as e:
                logger.warning(f"spaCy concept extraction failed: {e}")

        return list(set(concepts))  # Remove duplicates

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        if not text:
            return ""

        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r"\s+", " ", text.lower().strip())

        # Remove special characters but keep alphanumeric and spaces
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        return normalized

    def _calculate_string_similarity(self, text1: str, text2: str) -> float:
        """Calculate string similarity as fallback when spaCy is not available"""
        if not text1 or not text2:
            return 0.0

        # Use SequenceMatcher for string similarity
        matcher = SequenceMatcher(None, text1, text2)
        return matcher.ratio()

    def _analyze_domain_context(
        self, requirement: str, capability: str
    ) -> Optional[str]:
        """Analyze domain-specific context for enhanced matching"""
        domain_patterns = self._ensure_domain_patterns_initialized()
        if self.domain not in domain_patterns:
            return None

        domain_patterns = domain_patterns[self.domain]
        req_normalized = self._normalize_text(requirement)
        cap_normalized = self._normalize_text(capability)

        # Check for domain-specific matches
        for category, terms in domain_patterns.items():
            req_matches = [
                term for term in terms if self._normalize_text(term) in req_normalized
            ]
            cap_matches = [
                term for term in terms if self._normalize_text(term) in cap_normalized
            ]

            if req_matches and cap_matches:
                # Check for overlapping terms
                overlapping = set(req_matches) & set(cap_matches)
                if overlapping:
                    return f"Domain match in {category}: {', '.join(overlapping)}"

        return None

    def _enhance_with_domain_context(self, text: str) -> str:
        """
        Enhance text with domain-specific context to improve semantic understanding.

        Args:
            text: Original text to enhance

        Returns:
            Context-enhanced text for better spaCy processing
        """
        if not text:
            return text

        # Get domain patterns
        domain_patterns = self._ensure_domain_patterns_initialized()
        if self.domain not in domain_patterns:
            return text

        domain_patterns = domain_patterns[self.domain]
        enhanced_text = text

        # Add domain context for manufacturing
        if self.domain == "manufacturing":
            # Add manufacturing context terms
            context_terms = []

            # Check for common manufacturing abbreviations and add full terms
            abbreviation_map = {
                "pcb": "printed circuit board electronics manufacturing",
                "3dp": "3d printing additive manufacturing",
                "cnc": "computer numerical control machining",
                "cad": "computer aided design engineering",
                "cam": "computer aided manufacturing",
                "sla": "stereolithography 3d printing",
                "fdm": "fused deposition modeling 3d printing",
                "sls": "selective laser sintering 3d printing",
                "dmls": "direct metal laser sintering additive manufacturing",
            }

            text_lower = text.lower()
            for abbrev, full_term in abbreviation_map.items():
                if abbrev in text_lower:
                    context_terms.append(full_term)

            # Only add general manufacturing context if we found specific abbreviations
            if context_terms:  # Only if we already found specific abbreviations
                context_terms.extend(["manufacturing process", "production capability"])

            # Combine original text with context
            if context_terms:
                enhanced_text = f"{text} {' '.join(context_terms)}"

        return enhanced_text

    def _calculate_domain_boost(self, text1: str, text2: str) -> float:
        """
        Calculate domain-specific similarity boost for known manufacturing terms.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Boost value between 0.0 and 0.3
        """
        domain_patterns = self._ensure_domain_patterns_initialized()
        if self.domain not in domain_patterns:
            return 0.0

        domain_patterns = domain_patterns[self.domain]
        boost = 0.0

        # Check for exact matches in domain patterns
        text1_lower = text1.lower()
        text2_lower = text2.lower()

        for category, terms in domain_patterns.items():
            text1_matches = [term for term in terms if term in text1_lower]
            text2_matches = [term for term in terms if term in text2_lower]

            # If both texts have terms from the same category, boost similarity
            if text1_matches and text2_matches:
                overlapping = set(text1_matches) & set(text2_matches)
                if overlapping:
                    boost += 0.2  # Strong boost for exact category matches
                else:
                    boost += 0.1  # Moderate boost for same category

        # Check for abbreviation matches
        abbreviation_map = {
            "pcb": ["printed circuit board", "circuit board"],
            "3dp": ["3d printing", "additive manufacturing"],
            "cnc": ["computer numerical control", "machining"],
            "sla": ["stereolithography", "3d printing"],
            "fdm": ["fused deposition modeling", "3d printing"],
        }

        for abbrev, full_terms in abbreviation_map.items():
            if (
                abbrev in text1_lower
                and any(term in text2_lower for term in full_terms)
            ) or (
                abbrev in text2_lower
                and any(term in text1_lower for term in full_terms)
            ):
                boost += 0.15  # Boost for abbreviation matches

        return min(0.3, boost)  # Cap boost at 0.3

    def _calculate_string_similarity_with_context(
        self, text1: str, text2: str
    ) -> float:
        """
        Calculate string similarity with domain context awareness as fallback.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Use the original string similarity method
        base_similarity = self._calculate_string_similarity(text1, text2)

        # Apply domain boost
        domain_boost = self._calculate_domain_boost(text1, text2)

        return min(1.0, base_similarity + domain_boost)

    def cleanup(self):
        """Clean up resources to prevent memory leaks"""
        if self._nlp is not None:
            logger.info("Cleaning up spaCy model to free memory")
            # spaCy models don't have explicit cleanup, but we can clear the reference
            self._nlp = None
            self._nlp_initialized = False

        # Clear domain patterns to free memory
        self._domain_patterns = None
        self._patterns_initialized = False

        logger.info("NLP matcher cleanup completed")
