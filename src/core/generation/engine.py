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
from .layers.nlp import NLPMatcher
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
        if self.config.use_nlp:
            self._matchers[GenerationLayer.NLP] = NLPMatcher()
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
        
        # Add BOM normalization if enabled
        full_bom_object = None
        if self.config.use_bom_normalization:
            try:
                bom = await self._generate_normalized_bom(project_data)
                full_bom_object = bom  # Store full BOM object for export
                # Add BOM to generated fields
                generated_fields["bom"] = FieldGeneration(
                    value=bom.to_dict(),
                    confidence=bom.metadata.get("overall_confidence", 0.8),
                    source_layer=GenerationLayer.BOM_NORMALIZATION,
                    generation_method="bom_normalization",
                    raw_source=f"Extracted from {len(bom.components)} sources"
                )
                confidence_scores["bom"] = bom.metadata.get("overall_confidence", 0.8)
                
                # Extract materials from BOM components - always override with structured data
                materials = self._extract_materials_from_bom(bom)
                if materials:
                    generated_fields["materials"] = FieldGeneration(
                        value=materials,
                        confidence=0.8,
                        source_layer=GenerationLayer.BOM_NORMALIZATION,
                        generation_method="bom_materials_extraction",
                        raw_source=f"Extracted from {len(bom.components)} BOM components"
                    )
                    confidence_scores["materials"] = 0.8
            except Exception as e:
                # Log error but don't fail the entire generation
                print(f"Warning: BOM normalization failed: {e}")
        
        # Analyze parts directory for parts and sub_parts fields
        parts_analysis = self._analyze_parts_directory(project_data)
        if parts_analysis["parts"]:
            generated_fields["parts"] = FieldGeneration(
                value=parts_analysis["parts"],
                confidence=0.7,
                source_layer=GenerationLayer.HEURISTIC,
                generation_method="parts_directory_analysis",
                raw_source=f"Analyzed {len(parts_analysis['parts'])} parts from directory structure"
            )
            confidence_scores["parts"] = 0.7
        
        if parts_analysis["sub_parts"]:
            generated_fields["sub_parts"] = FieldGeneration(
                value=parts_analysis["sub_parts"],
                confidence=0.7,
                source_layer=GenerationLayer.HEURISTIC,
                generation_method="parts_directory_analysis",
                raw_source=f"Analyzed {len(parts_analysis['sub_parts'])} sub-parts from directory structure"
            )
            confidence_scores["sub_parts"] = 0.7
        
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
            missing_fields=missing_fields,
            full_bom=full_bom_object
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
    
    async def _generate_normalized_bom(self, project_data: ProjectData):
        """
        Generate normalized BOM from project data.
        
        Args:
            project_data: Raw project data from platform
            
        Returns:
            BillOfMaterials object with normalized components
        """
        from .bom_models import BOMCollector, BOMProcessor, BOMBuilder
        
        # Collect BOM data from multiple sources
        collector = BOMCollector()
        sources = collector.collect_bom_data(project_data)
        
        # Process BOM data into components
        processor = BOMProcessor()
        components = processor.process_bom_sources(sources)
        
        # Build final BOM
        builder = BOMBuilder()
        project_name = project_data.metadata.get('name', 'Project')
        bom = builder.build_bom(components, f"{project_name} BOM")
        
        return bom
    
    def _extract_materials_from_bom(self, bom) -> List[str]:
        """Extract materials from BOM components"""
        materials = set()
        
        for component in bom.components:
            component_name = component.name
            material = self._classify_component_material(component_name)
            if material:
                materials.add(material)
        
        return list(materials) if materials else []
    
    def _classify_component_material(self, component_name: str) -> Optional[str]:
        """Classify a component name into a material type"""
        name_lower = component_name.lower()
        
        # Material classification patterns - ordered by specificity (most specific first)
        material_patterns = [
            # Specific materials first (to avoid false matches)
            ('brass', ['brass']),
            ('copper', ['copper', 'cu ']),
            ('aluminum', ['aluminum', 'aluminium', 'al ', 'al-']),
            ('steel', ['stainless steel', 'steel']),  # stainless steel before steel
            ('PLA', ['pla', 'polylactic acid']),
            ('ABS', ['abs', 'acrylonitrile butadiene styrene']),
            ('PETG', ['petg', 'pet-g']),
            ('TPU', ['tpu', 'thermoplastic polyurethane']),
            ('wood', ['wood', 'plywood', 'mdf', 'oak', 'pine']),
            ('acrylic', ['acrylic', 'plexiglass', 'pmma']),
            # Component types
            ('electronics', ['arduino', 'raspberry pi', 'sensor', 'motor', 'servo', 'led', 'resistor', 'capacitor', 'transistor', 'ic', 'microcontroller']),
            ('fasteners', ['screw', 'bolt', 'nut', 'washer', 'rivet', 'pin']),
            ('cables', ['cable', 'wire', 'connector', 'jack', 'plug']),
            ('bearings', ['bearing', 'ball bearing', 'roller bearing']),
            ('springs', ['spring', 'coil spring', 'tension spring'])
        ]
        
        # Check each material pattern (first match wins)
        for material, patterns in material_patterns:
            for pattern in patterns:
                if pattern in name_lower:
                    return material
        
        return None
    
    def _analyze_parts_directory(self, project_data) -> Dict[str, List[Dict[str, Any]]]:
        """
        Analyze parts directory structure to extract parts and sub_parts information.
        
        Args:
            project_data: ProjectData containing file information
            
        Returns:
            Dictionary with 'parts' and 'sub_parts' lists
        """
        parts = []
        sub_parts = []
        
        # Look for parts-related directories
        parts_directories = []
        for file_info in project_data.files:
            path = file_info.path.lower()
            if 'parts' in path and file_info.file_type == 'markdown':
                # Extract directory structure from path
                path_parts = file_info.path.split('/')
                if len(path_parts) >= 3 and path_parts[1] == 'parts':  # docs/parts/category/file.md
                    category = path_parts[2]
                    if category not in parts_directories:
                        parts_directories.append(category)
        
        # Analyze each parts category
        for category in parts_directories:
            category_files = []
            for file_info in project_data.files:
                if (file_info.path.startswith(f'docs/parts/{category}/') and 
                    file_info.file_type == 'markdown'):
                    category_files.append(file_info)
            
            if category_files:
                # Create a part entry for this category
                part_entry = {
                    "name": category.replace('_', ' ').title(),
                    "category": category,
                    "description": f"Components in the {category} category",
                    "files": [
                        {
                            "path": f.path,
                            "name": f.path.split('/')[-1].replace('.md', '').replace('_', ' ').title(),
                            "type": f.file_type,
                            "size": f.size
                        }
                        for f in category_files
                    ],
                    "file_count": len(category_files)
                }
                
                # Determine if this is a main part or sub-part based on category
                if category in ['electronics', 'optics', 'printed']:
                    parts.append(part_entry)
                else:
                    sub_parts.append(part_entry)
        
        # Also look for individual part files that might not be in categories
        individual_parts = []
        for file_info in project_data.files:
            if (file_info.path.startswith('docs/parts/') and 
                file_info.file_type == 'markdown' and
                not any(cat in file_info.path for cat in parts_directories)):
                
                part_name = file_info.path.split('/')[-1].replace('.md', '').replace('_', ' ').title()
                individual_parts.append({
                    "name": part_name,
                    "path": file_info.path,
                    "type": file_info.file_type,
                    "size": file_info.size
                })
        
        # Add individual parts as sub_parts
        if individual_parts:
            sub_parts.append({
                "name": "Individual Parts",
                "category": "individual",
                "description": "Individual part specifications",
                "files": individual_parts,
                "file_count": len(individual_parts)
            })
        
        return {
            "parts": parts,
            "sub_parts": sub_parts
        }
