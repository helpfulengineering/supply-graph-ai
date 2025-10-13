"""
OKH Manifest Generation System

This module provides functionality for generating OKH manifests from external sources
like GitHub repositories, GitLab projects, and other platforms.

The generation system uses a multi-layer approach:
1. Direct matching - exact field mappings from platform metadata
2. Heuristic matching - rule-based pattern recognition (future)
3. NLP matching - semantic understanding of content (future)
4. LLM matching - AI-powered content understanding (future)
"""

from .models import (
    PlatformType,
    GenerationQuality,
    GenerationLayer,
    ProjectData,
    FieldGeneration,
    GenerationMetadata,
    ManifestGeneration,
    QualityReport,
    LayerConfig,
    GenerationResult,
    FileInfo,
    DocumentInfo
)

__all__ = [
    'PlatformType',
    'GenerationQuality', 
    'GenerationLayer',
    'ProjectData',
    'FieldGeneration',
    'GenerationMetadata',
    'ManifestGeneration',
    'QualityReport',
    'LayerConfig',
    'GenerationResult',
    'FileInfo',
    'DocumentInfo'
]
