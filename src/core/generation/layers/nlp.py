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
from ..models import ProjectData, GenerationLayer, LayerConfig


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
    
    def __init__(self, layer_config: Optional[LayerConfig] = None):
        super().__init__(GenerationLayer.NLP, layer_config)
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
            # 3D Printing (high-confidence specific terms)
            EntityPattern(r'\b(3D print|3D printing|3D printed|FDM|SLA|SLS|FFF|fused deposition|selective laser)\b', 'process', 'manufacturing_processes', 0.9, '3D printing process'),
            
            # CNC Machining (high-confidence specific terms)
            EntityPattern(r'\b(CNC|machining|milling|turning|lathe)\b', 'process', 'manufacturing_processes', 0.8, 'CNC machining'),
            
            # Electronics (high-confidence specific terms)
            EntityPattern(r'\b(solder|soldering|soldered|PCB assembly|circuit assembly)\b', 'process', 'manufacturing_processes', 0.8, 'Electronics assembly'),
            
            # Assembly (medium-confidence - requires context)
            EntityPattern(r'\b(assemble|assembling|assembled|assembly|mount|mounting|install|installing|attach|attaching)\b', 'process', 'manufacturing_processes', 0.7, 'Assembly process'),
            
            # Generic verbs (low-confidence - require strong manufacturing context)
            # These are filtered more strictly by context validation
            EntityPattern(r'\b(print|printing|printed)\b', 'process', 'manufacturing_processes', 0.6, 'Printing (requires context)'),
            EntityPattern(r'\b(cut|cutting)\b', 'process', 'manufacturing_processes', 0.6, 'Cutting (requires context)'),
            EntityPattern(r'\b(drill|drilling|bore)\b', 'process', 'manufacturing_processes', 0.6, 'Drilling (requires context)'),
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
        """Extract README content from project data using shared utilities"""
        # Use shared utility to find README files
        readme_files = self.find_readme_files(project_data.files)
        if readme_files:
            # Clean the content using shared text processing
            content = readme_files[0].content
            return self.clean_text(content) if content else None
        
        # Look in documentation
        for doc in project_data.documentation:
            if doc.title.lower().startswith('readme'):
                content = doc.content
                return self.clean_text(content) if content else None
        
        return None
    
    def _analyze_content_with_nlp(self, content: str) -> Dict[str, Any]:
        """Analyze content using spaCy NLP"""
        if not content or not self.nlp:
            return {}
        
        doc = self.nlp(content)
        fields = {}
        
        # Extract main description
        description = self._extract_description(doc, content)
        if description:
            fields['description'] = description
        
        # Extract function/intended use
        function = self._extract_function(doc)
        if function:
            fields['function'] = function
        
        # Extract intended use (similar to function but more specific)
        intended_use = self._extract_intended_use(doc)
        if intended_use:
            fields['intended_use'] = intended_use
        
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
    
    def _extract_description(self, doc, content: str) -> Optional[str]:
        """Extract main project description from NLP analysis"""
        # Split content into sentences
        sentences = content.split('. ')
        
        # Look for the main project description in the first few sentences
        for i, sentence in enumerate(sentences[:5]):  # Check first 5 sentences
            sentence = sentence.strip()
            if len(sentence) < 30:  # Skip very short sentences
                continue
            
            # Look for sentences that describe what the project is
            description_indicators = [
                'is a', 'is an', 'is designed to', 'aims to', 'creates', 'builds',
                'provides', 'enables', 'allows', 'helps', 'facilitates'
            ]
            
            # Skip sentences that are clearly not descriptions
            skip_indicators = [
                'license', 'copyright', 'permission', 'warranty', 'disclaimer',
                'has moved to', 'moved to', 'migrated to', 'relocated to',
                'table of contents', 'contents', 'installation', 'setup',
                'getting started', 'quick start', 'printing the parts', 'before we start'
            ]
            
            # Check if this sentence describes the project
            has_description_indicator = any(indicator in sentence.lower() for indicator in description_indicators)
            has_skip_indicator = any(indicator in sentence.lower() for indicator in skip_indicators)
            
            # If it has description indicators and doesn't have skip indicators, use it
            if has_description_indicator and not has_skip_indicator:
                # Clean up the sentence
                cleaned = sentence.replace('\n', ' ').strip()
                # If it's too long, truncate it
                if len(cleaned) > 300:
                    return cleaned[:300] + '...'
                else:
                    return cleaned
            
            # Special case: if the sentence contains both "assembly instructions" and "is a",
            # extract just the "is a" part
            if 'assembly instructions' in sentence.lower() and 'is a' in sentence.lower():
                # Find the part after "is a"
                parts = sentence.split('is a')
                if len(parts) > 1:
                    description_part = 'is a' + parts[1]
                    # Take first sentence of this part
                    description_sentences = description_part.split('. ')
                    if description_sentences:
                        cleaned = description_sentences[0].replace('\n', ' ').strip()
                        # Remove any remaining title text before the colon
                        if ':' in cleaned:
                            # Find the last colon and take everything after it
                            last_colon = cleaned.rfind(':')
                            cleaned = cleaned[last_colon + 1:].strip()
                        if len(cleaned) > 300:
                            return cleaned[:300] + '...'
                        else:
                            return cleaned
        
        return None

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
    
    def _extract_intended_use(self, doc) -> Optional[str]:
        """Extract intended use from NLP analysis"""
        # Look for sentences that describe the intended use/application
        intended_use_sentences = []
        
        for sent in doc.sents:
            sent_text = sent.text.strip()
            
            # Skip very short sentences
            if len(sent_text) < 20:
                continue
            
            # Look for intended use indicators
            intended_use_indicators = [
                'perfect for', 'ideal for', 'designed for', 'suitable for',
                'intended for', 'used for', 'applications include', 'use cases',
                'target audience', 'end users', 'purpose is', 'goal is'
            ]
            
            if any(indicator in sent_text.lower() for indicator in intended_use_indicators):
                intended_use_sentences.append(sent_text)
        
        if intended_use_sentences:
            # Return the first (usually most relevant) intended use description
            return intended_use_sentences[0]
        
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
        """
        Extract manufacturing processes using entity patterns with context validation.
        
        This method filters out false positives by checking if matched terms are
        actually in manufacturing contexts, not just any verb in the text.
        """
        processes = set()
        
        # Manufacturing context keywords - terms that indicate manufacturing context
        manufacturing_context_keywords = {
            'manufacture', 'manufacturing', 'produce', 'production', 'fabricate', 'fabrication',
            'build', 'building', 'make', 'making', 'create', 'creating',
            'print', 'printing', '3d print', '3d printing', 'printable',
            'assemble', 'assembly', 'mount', 'install',
            'cut', 'cutting', 'machin', 'drill', 'drilling',
            'solder', 'soldering', 'weld', 'welding',
            'process', 'processing', 'tool', 'tools', 'equipment',
            'part', 'parts', 'component', 'components', 'material', 'materials'
        }
        
        # Extract matches from patterns
        for pattern in self.process_patterns:
            matches = re.finditer(pattern.pattern, content, re.IGNORECASE)
            for match in matches:
                # Extract matched text (use first group if available, otherwise use full match)
                if match.groups():
                    matched_text = match.group(1)  # Use first capturing group
                else:
                    matched_text = match.group(0)  # Use full match
                
                if isinstance(matched_text, tuple):
                    matched_text = matched_text[0]
                matched_text = matched_text.strip()
                
                if not matched_text:
                    continue
                
                # Validate context: check if match is in manufacturing context
                if self._is_manufacturing_context(match, content, manufacturing_context_keywords, doc, pattern):
                    processes.add(matched_text)
        
        return list(processes)
    
    def _is_manufacturing_context(self, match, content: str, context_keywords: set, doc, pattern) -> bool:
        """
        Check if a matched term is in a manufacturing context.
        
        Args:
            match: Regex match object
            content: Full content text
            context_keywords: Set of manufacturing context keywords
            doc: spaCy document
            pattern: EntityPattern that matched
            
        Returns:
            True if match is in manufacturing context, False otherwise
        """
        start_pos = match.start()
        end_pos = match.end()
        
        # For high-confidence patterns (specific manufacturing terms like "3D printing"),
        # trust them - they're unlikely to be false positives
        if pattern.confidence >= 0.8:
            return True
        
        # Extract surrounding context (100 chars before and after)
        context_start = max(0, start_pos - 100)
        context_end = min(len(content), end_pos + 100)
        context = content[context_start:context_end].lower()
        
        # Check for manufacturing context keywords nearby
        # Exclude the matched word itself from context keywords to avoid self-matching
        matched_word = match.group(0).lower().strip()
        context_keywords_filtered = {k for k in context_keywords if k != matched_word}
        
        context_words = set(context.split())
        has_manufacturing_context = any(keyword in context_words for keyword in context_keywords_filtered)
        
        # Also check for multi-word patterns (e.g., "3d printer", "3d printing")
        context_lower = context.lower()
        for keyword in context_keywords_filtered:
            if ' ' in keyword or keyword in context_lower:
                has_manufacturing_context = True
                break
        
        # Use spaCy to check if verb is in manufacturing-related sentence
        if doc:
            try:
                # Find the sentence containing the match
                matched_span = doc.char_span(start_pos, end_pos, alignment_mode='expand')
                if matched_span:
                    sentence = matched_span.sent
                    sentence_text = sentence.text.lower()
                    
                    # Check for manufacturing keywords in sentence
                    sentence_has_context = any(keyword in sentence_text for keyword in context_keywords)
                    
                    # Low-confidence patterns (generic verbs like "print", "test", "layer") need context
                    # High-confidence patterns already returned True above
                    return sentence_has_context or has_manufacturing_context
            except Exception:
                # If spaCy analysis fails, fall back to keyword check
                pass
        
        # Fallback: use keyword-based context check
        # For low-confidence patterns, require manufacturing context
        return has_manufacturing_context
    
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
        """Calculate confidence score for a field extraction using shared utility"""
        # Use shared confidence calculator with NLP-specific source
        source = "nlp_analysis"
        
        # Prepare content quality metrics for the shared calculator
        content_quality = {
            "length": len(content) if content else 0,
            "completeness": 1.0 if content and len(content) > 100 else 0.5
        }
        
        return self.calculate_confidence(field, value, source, content_quality)
    
    def _calculate_overall_confidence(self, confidence_scores: Dict[str, float]) -> float:
        """Calculate overall confidence for the layer using shared utility"""
        return self.calculate_layer_confidence(confidence_scores)
