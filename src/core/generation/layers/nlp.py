"""
NLP Matching Layer for OKH manifest generation.

This layer uses spaCy for semantic understanding of project content,
extracting structured information from unstructured text in README files,
documentation, and other project content.
"""

import re
import spacy
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .base import BaseGenerationLayer, LayerResult
from ..models import ProjectData, GenerationLayer


@dataclass
class EntityPattern:
    """Pattern for matching entities in text"""
    pattern: str
    entity_type: str
    field: str
    confidence: float
    description: str


@dataclass
class TextClassification:
    """Result of text classification"""
    content_type: str
    process_type: str
    complexity_level: str
    confidence: float


class NLPMatcher(BaseGenerationLayer):
    """NLP matching layer using spaCy for semantic understanding"""
    
    def __init__(self):
        super().__init__(GenerationLayer.NLP)
        self.nlp = None
        self._initialize_nlp()
        self._initialize_entity_patterns()
        self._initialize_classification_patterns()
    
    def _initialize_nlp(self):
        """Initialize spaCy NLP model"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            # Fallback if model not available
            print("Warning: spaCy English model not found. NLP layer will be disabled.")
            self.nlp = None
    
    def _initialize_entity_patterns(self):
        """Initialize patterns for entity recognition"""
        self.material_patterns = [
            # 3D Printing Materials
            EntityPattern(r'\b(PLA|ABS|PETG|TPU|ASA|PC|Nylon|Resin)\b', 'material', 'materials', 0.9, '3D printing material'),
            EntityPattern(r'\b(PLA\+|ABS\+|PETG\+)\b', 'material', 'materials', 0.9, 'Enhanced 3D printing material'),
            
            # Electronics Components
            EntityPattern(r'\b(Arduino|Raspberry Pi|ESP32|ESP8266|STM32)\b', 'component', 'materials', 0.8, 'Microcontroller'),
            EntityPattern(r'\b(resistor|capacitor|transistor|diode|LED|sensor)\b', 'component', 'materials', 0.7, 'Electronic component'),
            EntityPattern(r'\b(servo|motor|stepper|DC motor|brushless)\b', 'component', 'materials', 0.8, 'Motor/actuator'),
            
            # Hardware Components
            EntityPattern(r'\b(screw|bolt|nut|washer|bearing|gear)\b', 'hardware', 'materials', 0.7, 'Hardware component'),
            EntityPattern(r'\b(M3|M4|M5|M6|M8)\b', 'hardware', 'materials', 0.8, 'Metric screw size'),
            EntityPattern(r'\b(ball bearing|linear bearing|pulley|belt)\b', 'hardware', 'materials', 0.8, 'Mechanical component'),
            
            # Materials by Type
            EntityPattern(r'\b(aluminum|steel|brass|copper|wood|plastic|acrylic)\b', 'material', 'materials', 0.7, 'Raw material'),
            EntityPattern(r'\b(filament|wire|cable|connector|jack)\b', 'material', 'materials', 0.6, 'Electrical material'),
        ]
        
        self.process_patterns = [
            # 3D Printing
            EntityPattern(r'\b(3D print|3D printing|FDM|SLA|SLS|FFF)\b', 'process', 'manufacturing_processes', 0.9, '3D printing process'),
            EntityPattern(r'\b(print|printing|extruder|hotend|bed|layer)\b', 'process', 'manufacturing_processes', 0.7, '3D printing related'),
            
            # CNC Machining
            EntityPattern(r'\b(CNC|machining|mill|lathe|router|cutting)\b', 'process', 'manufacturing_processes', 0.8, 'CNC machining'),
            EntityPattern(r'\b(end mill|drill bit|toolpath|G-code)\b', 'process', 'manufacturing_processes', 0.7, 'CNC tooling'),
            
            # Electronics
            EntityPattern(r'\b(solder|soldering|PCB|circuit|breadboard)\b', 'process', 'manufacturing_processes', 0.8, 'Electronics assembly'),
            EntityPattern(r'\b(program|programming|flash|upload|code)\b', 'process', 'manufacturing_processes', 0.6, 'Software programming'),
            
            # Assembly
            EntityPattern(r'\b(assemble|assembly|mount|install|attach)\b', 'process', 'manufacturing_processes', 0.7, 'Assembly process'),
            EntityPattern(r'\b(calibrate|calibration|tune|adjust|test)\b', 'process', 'manufacturing_processes', 0.6, 'Calibration/testing'),
        ]
        
        self.tool_patterns = [
            # 3D Printing Tools
            EntityPattern(r'\b(3D printer|printer|extruder|hotend|build plate)\b', 'tool', 'tool_list', 0.9, '3D printing equipment'),
            EntityPattern(r'\b(calipers|ruler|measuring|scale|multimeter)\b', 'tool', 'tool_list', 0.8, 'Measuring tools'),
            
            # Electronics Tools
            EntityPattern(r'\b(soldering iron|solder|flux|desoldering|multimeter)\b', 'tool', 'tool_list', 0.9, 'Electronics tools'),
            EntityPattern(r'\b(oscilloscope|logic analyzer|power supply|breadboard)\b', 'tool', 'tool_list', 0.8, 'Electronics equipment'),
            
            # Mechanical Tools
            EntityPattern(r'\b(drill|drill press|CNC|mill|lathe|router)\b', 'tool', 'tool_list', 0.8, 'Machining tools'),
            EntityPattern(r'\b(screwdriver|wrench|pliers|file|sandpaper)\b', 'tool', 'tool_list', 0.7, 'Hand tools'),
            
            # Software Tools
            EntityPattern(r'\b(CAD|Fusion 360|SolidWorks|FreeCAD|OpenSCAD)\b', 'tool', 'tool_list', 0.8, 'CAD software'),
            EntityPattern(r'\b(Cura|PrusaSlicer|Slic3r|Simplify3D)\b', 'tool', 'tool_list', 0.8, 'Slicing software'),
        ]
    
    def _initialize_classification_patterns(self):
        """Initialize patterns for text classification"""
        self.content_type_patterns = {
            'assembly_instructions': [
                r'\b(step \d+|first|next|then|finally|assemble|mount|install)\b',
                r'\b(instructions|guide|tutorial|how to)\b'
            ],
            'specifications': [
                r'\b(dimensions|size|weight|voltage|current|power)\b',
                r'\b(specification|specs|requirements|parameters)\b'
            ],
            'troubleshooting': [
                r'\b(problem|issue|error|fix|solution|troubleshoot)\b',
                r'\b(common issues|FAQ|help|support)\b'
            ],
            'overview': [
                r'\b(overview|introduction|about|description|summary)\b',
                r'\b(what is|this project|purpose|goal)\b'
            ]
        }
        
        self.complexity_patterns = {
            'beginner': [
                r'\b(beginner|easy|simple|basic|starter|introductory)\b',
                r'\b(no experience|first time|getting started)\b'
            ],
            'intermediate': [
                r'\b(intermediate|moderate|some experience|basic knowledge)\b',
                r'\b(requires|need|should have|familiar with)\b'
            ],
            'advanced': [
                r'\b(advanced|expert|complex|professional|experienced)\b',
                r'\b(requires expertise|advanced knowledge|professional level)\b'
            ]
        }
    
    async def process(self, project_data: ProjectData) -> LayerResult:
        """Process project data using NLP analysis"""
        if not self.nlp:
            result = LayerResult(GenerationLayer.NLP)
            result.add_error("spaCy model not available")
            return result
        
        result = LayerResult(GenerationLayer.NLP)
        
        # Analyze README content
        readme_content = self._extract_readme_content(project_data)
        if readme_content:
            nlp_fields = self._analyze_content_with_nlp(readme_content)
            
            # Add fields to result
            for field, value in nlp_fields.items():
                confidence = self._calculate_field_confidence(field, value, readme_content)
                result.add_field(field, value, confidence, "nlp_analysis", f"README content analysis")
        
        # Analyze documentation files
        doc_fields = self._analyze_documentation(project_data)
        for field, value in doc_fields.items():
            if not result.has_field(field):  # Don't override README fields
                confidence = self._calculate_field_confidence(field, value, "documentation")
                result.add_field(field, value, confidence, "nlp_analysis", "Documentation analysis")
        
        # Add processing metadata
        result.add_log(f"Analyzed {len(project_data.documentation)} documentation files")
        result.add_log(f"README analyzed: {bool(readme_content)}")
        result.add_log("NLP model: en_core_web_sm")
        
        return result
    
    def _extract_readme_content(self, project_data: ProjectData) -> Optional[str]:
        """Extract README content from project data"""
        # Look for README files
        for file_info in project_data.files:
            if file_info.path.lower().startswith('readme'):
                return file_info.content
        
        # Look in documentation
        for doc in project_data.documentation:
            if doc.title.lower().startswith('readme'):
                return doc.content
        
        return None
    
    def _analyze_content_with_nlp(self, content: str) -> Dict[str, Any]:
        """Analyze content using spaCy NLP"""
        if not content or not self.nlp:
            return {}
        
        doc = self.nlp(content)
        fields = {}
        
        # Extract function/intended use
        function = self._extract_function(doc)
        if function:
            fields['function'] = function
        
        # Extract materials using entity patterns
        materials = self._extract_materials(doc, content)
        if materials:
            fields['materials'] = materials
        
        # Extract manufacturing processes
        processes = self._extract_manufacturing_processes(doc, content)
        if processes:
            fields['manufacturing_processes'] = processes
        
        # Extract tool requirements
        tools = self._extract_tools(doc, content)
        if tools:
            fields['tool_list'] = tools
        
        # Classify content
        classification = self._classify_content(content)
        if classification:
            fields['content_classification'] = classification
        
        return fields
    
    def _extract_function(self, doc) -> Optional[str]:
        """Extract project function/intended use from NLP analysis"""
        # Look for sentences that describe what the project does
        function_sentences = []
        
        for sent in doc.sents:
            sent_text = sent.text.strip()
            
            # Skip very short sentences
            if len(sent_text) < 20:
                continue
            
            # Look for function indicators
            function_indicators = [
                'is designed to', 'is used to', 'allows you to', 'enables',
                'provides', 'creates', 'generates', 'measures', 'monitors',
                'controls', 'automates', 'detects', 'senses', 'displays'
            ]
            
            if any(indicator in sent_text.lower() for indicator in function_indicators):
                function_sentences.append(sent_text)
        
        if function_sentences:
            # Return the first (usually most relevant) function description
            return function_sentences[0]
        
        return None
    
    def _extract_materials(self, doc, content: str) -> List[str]:
        """Extract materials using entity patterns and NER"""
        materials = set()
        
        # Use entity patterns
        for pattern in self.material_patterns:
            matches = re.findall(pattern.pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]  # Take first group if tuple
                materials.add(match.strip())
        
        # Use spaCy NER for additional materials
        for ent in doc.ents:
            if ent.label_ in ['PRODUCT', 'ORG', 'MISC']:
                # Check if it looks like a material/component
                if any(keyword in ent.text.lower() for keyword in 
                      ['arduino', 'raspberry', 'sensor', 'motor', 'servo', 'led', 'resistor']):
                    materials.add(ent.text)
        
        return list(materials)
    
    def _extract_manufacturing_processes(self, doc, content: str) -> List[str]:
        """Extract manufacturing processes using entity patterns"""
        processes = set()
        
        for pattern in self.process_patterns:
            matches = re.findall(pattern.pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                processes.add(match.strip())
        
        return list(processes)
    
    def _extract_tools(self, doc, content: str) -> List[str]:
        """Extract required tools using entity patterns"""
        tools = set()
        
        for pattern in self.tool_patterns:
            matches = re.findall(pattern.pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                tools.add(match.strip())
        
        return list(tools)
    
    def _classify_content(self, content: str) -> Optional[TextClassification]:
        """Classify content type and complexity"""
        content_lower = content.lower()
        
        # Classify content type
        content_type = 'overview'  # default
        content_type_confidence = 0.5
        
        for ctype, patterns in self.content_type_patterns.items():
            matches = sum(1 for pattern in patterns if re.search(pattern, content_lower))
            if matches > 0:
                confidence = min(0.9, 0.5 + (matches * 0.1))
                if confidence > content_type_confidence:
                    content_type = ctype
                    content_type_confidence = confidence
        
        # Classify complexity
        complexity = 'intermediate'  # default
        complexity_confidence = 0.5
        
        for comp, patterns in self.complexity_patterns.items():
            matches = sum(1 for pattern in patterns if re.search(pattern, content_lower))
            if matches > 0:
                confidence = min(0.9, 0.5 + (matches * 0.1))
                if confidence > complexity_confidence:
                    complexity = comp
                    complexity_confidence = confidence
        
        overall_confidence = (content_type_confidence + complexity_confidence) / 2
        
        return TextClassification(
            content_type=content_type,
            process_type='mixed',  # Could be enhanced
            complexity_level=complexity,
            confidence=overall_confidence
        )
    
    def _analyze_documentation(self, project_data: ProjectData) -> Dict[str, Any]:
        """Analyze additional documentation files"""
        fields = {}
        
        for doc in project_data.documentation:
            if doc.title.lower().startswith('readme'):
                continue  # Already processed
            
            doc_content = doc.content
            if not doc_content:
                continue
            
            # Analyze documentation-specific content
            doc_fields = self._analyze_content_with_nlp(doc_content)
            
            # Merge fields (could be enhanced with conflict resolution)
            for field, value in doc_fields.items():
                if field not in fields:
                    fields[field] = value
                elif isinstance(fields[field], list) and isinstance(value, list):
                    # Merge lists
                    fields[field].extend(value)
                    fields[field] = list(set(fields[field]))  # Remove duplicates
        
        return fields
    
    def _calculate_field_confidence(self, field: str, value: Any, content: str) -> float:
        """Calculate confidence score for a field extraction"""
        base_confidence = 0.6  # Base confidence for NLP extraction
        
        # Adjust based on field type
        if field == 'function':
            # Higher confidence for function extraction
            base_confidence = 0.7
        elif field in ['materials', 'manufacturing_processes', 'tool_list']:
            # Medium confidence for entity extraction
            base_confidence = 0.6
        elif field == 'content_classification':
            # Lower confidence for classification
            base_confidence = 0.5
        
        # Adjust based on content quality
        if len(content) > 500:
            base_confidence += 0.1  # Longer content = more confidence
        elif len(content) < 100:
            base_confidence -= 0.2  # Very short content = less confidence
        
        # Adjust based on value quality
        if isinstance(value, list) and len(value) > 0:
            base_confidence += 0.1  # Found multiple items
        elif isinstance(value, str) and len(value) > 20:
            base_confidence += 0.1  # Substantial text extraction
        
        return min(0.9, max(0.1, base_confidence))
    
    def _calculate_overall_confidence(self, confidence_scores: Dict[str, float]) -> float:
        """Calculate overall confidence for the layer"""
        if not confidence_scores:
            return 0.0
        
        return sum(confidence_scores.values()) / len(confidence_scores)
