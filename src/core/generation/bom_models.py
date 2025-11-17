"""
BOM normalization data models and utilities
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import re
import json
import yaml
import logging

# Import Component from the BOM models
from ..models.bom import Component, BillOfMaterials

logger = logging.getLogger(__name__)


class BOMSourceType(Enum):
    """Types of BOM data sources"""
    README_MATERIALS = "readme_materials"
    README_BOM = "readme_bom"
    BOM_FILE = "bom_file"
    DOCUMENTATION = "documentation"
    ASSEMBLY_GUIDE = "assembly_guide"


@dataclass
class BOMSource:
    """Represents a source of BOM data"""
    source_type: BOMSourceType
    raw_content: str
    file_path: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate BOM source data"""
        if not self.raw_content.strip():
            raise ValueError("BOM source must have non-empty raw content")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if not self.file_path:
            raise ValueError("BOM source must have a file path")


class BOMCollector:
    """Collects BOM data from multiple sources in a project using NLP-enhanced detection"""
    
    def __init__(self):
        self._bom_file_patterns = [
            r"(?i)bom(\.csv|\.txt|\.md|\.json|\.yaml|\.yml)?$",
            r"(?i)bill_of_materials(\.csv|\.txt|\.md|\.json|\.yaml|\.yml)?$",
            r"(?i)materials(\.csv|\.txt|\.md|\.json|\.yaml|\.yml)?$",
            r"(?i)parts(\.csv|\.txt|\.md|\.json|\.yaml|\.yml)?$"
        ]
        
        # Legacy regex patterns (kept for fallback)
        self._materials_section_patterns = [
            r"(?i)(?:##?\s*)?materials?[:\s]*\n(.*?)(?=\n##|\n\*\*|\Z)",
            r"(?i)(?:##?\s*)?bill\s+of\s+materials?[:\s]*\n(.*?)(?=\n##|\n\*\*|\Z)",
            r"(?i)(?:##?\s*)?parts?[:\s]*\n(.*?)(?=\n##|\n\*\*|\Z)",
            r"(?i)(?:##?\s*)?components?[:\s]*\n(.*?)(?=\n##|\n\*\*|\Z)"
        ]
        
        # Initialize NLP for BOM detection
        self._nlp = None
        self._bom_keywords = {
            'materials', 'components', 'parts', 'hardware', 'supplies', 'items',
            'bill of materials', 'bom', 'shopping list', 'parts list', 'materials list',
            'required', 'needed', 'purchase', 'buy', 'acquire', 'obtain'
        }
        self._quantity_indicators = {
            'x', 'pcs', 'pieces', 'units', 'each', 'per', 'quantity', 'qty',
            'count', 'number', 'amount', 'total'
        }
    
    def collect_bom_data(self, project_data) -> List[BOMSource]:
        """
        Collect BOM data from all available sources in the project using NLP-enhanced detection
        
        Args:
            project_data: ProjectData object containing files and documentation
            
        Returns:
            List of BOMSource objects with extracted BOM data
        """
        sources = []
        
        # 1. NLP-enhanced extraction from README and documentation
        sources.extend(self._extract_with_nlp(project_data))
        
        # 2. Extract from dedicated BOM files (legacy method)
        sources.extend(self._extract_from_bom_files(project_data))
        
        # 3. Fallback to regex-based extraction if NLP finds nothing
        if not sources:
            sources.extend(self._extract_from_readme(project_data))
            sources.extend(self._extract_from_documentation(project_data))
        
        return sources
    
    def _extract_from_readme(self, project_data) -> List[BOMSource]:
        """Extract BOM data from README materials sections"""
        sources = []
        
        # Check README files
        for file_info in project_data.files:
            if self._is_readme_file(file_info.path):
                content = file_info.content
                if not content:
                    continue
                
                # Look for materials sections
                for pattern in self._materials_section_patterns:
                    matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
                    for match in matches:
                        materials_text = match.group(1).strip()
                        if materials_text and len(materials_text) > 20:  # Minimum content length
                            source = BOMSource(
                                source_type=BOMSourceType.README_MATERIALS,
                                raw_content=materials_text,
                                file_path=file_info.path,
                                confidence=self._calculate_readme_confidence(materials_text),
                                metadata={
                                    "section": "materials",
                                    "pattern": pattern,
                                    "line_start": content[:match.start()].count('\n') + 1
                                }
                            )
                            sources.append(source)
        
        # Check documentation
        for doc_info in project_data.documentation:
            if doc_info.title.lower() == "readme" or "readme" in doc_info.path.lower():
                content = doc_info.content
                if not content:
                    continue
                
                # Look for materials sections
                for pattern in self._materials_section_patterns:
                    matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
                    for match in matches:
                        materials_text = match.group(1).strip()
                        if materials_text and len(materials_text) > 20:
                            source = BOMSource(
                                source_type=BOMSourceType.README_MATERIALS,
                                raw_content=materials_text,
                                file_path=doc_info.path,
                                confidence=self._calculate_readme_confidence(materials_text),
                                metadata={
                                    "section": "materials",
                                    "pattern": pattern,
                                    "line_start": content[:match.start()].count('\n') + 1
                                }
                            )
                            sources.append(source)
        
        return sources
    
    def _extract_from_bom_files(self, project_data) -> List[BOMSource]:
        """Extract BOM data from dedicated BOM files"""
        sources = []
        
        for file_info in project_data.files:
            if self._is_bom_file(file_info.path):
                content = file_info.content
                if not content:
                    continue
                
                source = BOMSource(
                    source_type=BOMSourceType.BOM_FILE,
                    raw_content=content,
                    file_path=file_info.path,
                    confidence=self._calculate_bom_file_confidence(content, file_info.path),
                    metadata={
                        "file_type": file_info.file_type,
                        "size": file_info.size
                    }
                )
                sources.append(source)
        
        return sources
    
    def _extract_from_documentation(self, project_data) -> List[BOMSource]:
        """Extract BOM data from documentation files"""
        sources = []
        
        for doc_info in project_data.documentation:
            # Skip README (already processed)
            if doc_info.title.lower() == "readme" or "readme" in doc_info.path.lower():
                continue
            
            content = doc_info.content
            if not content:
                continue
            
            # Look for materials sections in documentation
            for pattern in self._materials_section_patterns:
                matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    materials_text = match.group(1).strip()
                    if materials_text and len(materials_text) > 20:
                        source = BOMSource(
                            source_type=BOMSourceType.DOCUMENTATION,
                            raw_content=materials_text,
                            file_path=doc_info.path,
                            confidence=self._calculate_documentation_confidence(materials_text),
                            metadata={
                                "doc_type": doc_info.doc_type,
                                "title": doc_info.title,
                                "section": "materials"
                            }
                        )
                        sources.append(source)
        
        return sources
    
    def _is_readme_file(self, file_path: str) -> bool:
        """Check if file is a README file"""
        path_lower = file_path.lower()
        return (
            path_lower == "readme.md" or
            path_lower == "readme.txt" or
            path_lower.startswith("readme.") or
            "readme" in path_lower
        )
    
    def _is_bom_file(self, file_path: str) -> bool:
        """Check if file is a BOM file based on name patterns"""
        path_lower = file_path.lower()
        return any(re.search(pattern, path_lower) for pattern in self._bom_file_patterns)
    
    def _calculate_readme_confidence(self, content: str) -> float:
        """Calculate confidence score for README materials section"""
        confidence = 0.6  # Base confidence for README
        
        # Increase confidence for structured content
        if re.search(r'^\s*[\*\-\+]\s+', content, re.MULTILINE):  # Bullet points
            confidence += 0.1
        if re.search(r'\d+\s+\w+', content):  # Quantity + unit patterns
            confidence += 0.1
        if re.search(r'\([^)]*\.(stl|step|scad|dxf)\)', content, re.IGNORECASE):  # File references
            confidence += 0.1
        if len(content.split('\n')) > 3:  # Multiple lines
            confidence += 0.1
        
        return round(min(confidence, 0.9), 2)  # Cap at 0.9 and round to 2 decimal places
    
    def _calculate_bom_file_confidence(self, content: str, file_path: str) -> float:
        """Calculate confidence score for BOM file"""
        confidence = 0.8  # Base confidence for BOM files
        
        # Increase confidence for structured formats
        if file_path.lower().endswith('.csv'):
            if ',' in content and '\n' in content:
                confidence += 0.1
        elif file_path.lower().endswith(('.json', '.yaml', '.yml')):
            confidence += 0.1
        
        # Increase confidence for content quality
        if re.search(r'\d+\s+\w+', content):  # Quantity + unit patterns
            confidence += 0.05
        if len(content.split('\n')) > 2:  # Multiple lines
            confidence += 0.05
        
        return round(min(confidence, 0.95), 2)  # Cap at 0.95 and round to 2 decimal places
    
    def _calculate_documentation_confidence(self, content: str) -> float:
        """Calculate confidence score for documentation materials section"""
        confidence = 0.5  # Base confidence for documentation
        
        # Increase confidence for structured content
        if re.search(r'^\s*[\*\-\+]\s+', content, re.MULTILINE):  # Bullet points
            confidence += 0.1
        if re.search(r'\d+\s+\w+', content):  # Quantity + unit patterns
            confidence += 0.1
        if len(content.split('\n')) > 2:  # Multiple lines
            confidence += 0.1
        
        return round(min(confidence, 0.8), 2)  # Cap at 0.8 and round to 2 decimal places
    
    def _extract_with_nlp(self, project_data) -> List[BOMSource]:
        """
        Extract BOM data using NLP-enhanced detection for flexible BOM location
        
        Args:
            project_data: ProjectData object containing files and documentation
            
        Returns:
            List of BOMSource objects with extracted BOM data
        """
        sources = []
        
        # Initialize spaCy if not already done
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load("en_core_web_sm")
                # Increase max length for large files
                self._nlp.max_length = 2000000  # 2MB limit
            except OSError:
                # Fallback if spaCy model not available
                print("Warning: spaCy model not available, falling back to regex patterns")
                return sources
        
        # Analyze all text files for BOM content
        for file_info in project_data.files:
            if self._is_text_file(file_info) and file_info.content:
                try:
                    # Skip very large files to avoid memory issues
                    if len(file_info.content) > 1000000:  # 1MB limit
                        print(f"Warning: Skipping large file {file_info.path} ({len(file_info.content)} chars)")
                        continue
                    
                    bom_sections = self._find_bom_sections_with_nlp(file_info.content, file_info.path)
                    for section in bom_sections:
                        source = BOMSource(
                            source_type=BOMSourceType.README_BOM,
                            raw_content=section['content'],
                            file_path=file_info.path,
                            confidence=section['confidence'],
                            metadata={
                                "nlp_detected": True,
                                "section_title": section.get('title', ''),
                                "detection_method": "nlp_enhanced"
                            }
                        )
                        sources.append(source)
                except Exception as e:
                    print(f"Warning: NLP processing failed for {file_info.path}: {e}")
                    continue
        
        return sources
    
    def _is_text_file(self, file_info) -> bool:
        """Check if file is a text file that might contain BOM data"""
        text_extensions = {'.md', '.txt', '.rst', '.doc', '.docx', '.pdf', '.html', '.json', '.yaml', '.yml'}
        image_extensions = {'.svg', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.ico'}
        excluded_files = {'license', 'copying', 'authors', 'contributors', 'changelog', 'version'}
        path_lower = file_info.path.lower()
        
        # Exclude image files (including SVG)
        if any(path_lower.endswith(ext) for ext in image_extensions):
            return False
        
        # Exclude license and other non-BOM files
        if any(excluded in path_lower for excluded in excluded_files):
            return False
        
        # Check file extension
        if any(path_lower.endswith(ext) for ext in text_extensions):
            return True
        
        # Check if it's a README or documentation file
        if any(keyword in path_lower for keyword in ['readme', 'doc', 'manual', 'guide', 'instructions']):
            return True
        
        # Check file type from metadata
        if hasattr(file_info, 'file_type'):
            return file_info.file_type in ['markdown', 'text', 'document']
        
        return False
    
    def _find_bom_sections_with_nlp(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Use NLP to find BOM sections in content
        
        Args:
            content: Text content to analyze
            file_path: Path of the file being analyzed
            
        Returns:
            List of dictionaries with 'content', 'confidence', and 'title' keys
        """
        if not self._nlp:
            return []
        
        sections = []
        doc = self._nlp(content)
        
        # Split content into potential sections (by headers or major breaks)
        content_sections = self._split_into_sections(content)
        
        for section_text in content_sections:
            if len(section_text.strip()) < 50:  # Skip very short sections
                continue
            
            # Analyze section with NLP
            confidence = self._analyze_bom_likelihood(section_text)
            
            if confidence > 0.4:  # Higher threshold to reduce false positives
                # Extract section title
                title = self._extract_section_title(section_text)
                
                sections.append({
                    'content': section_text,
                    'confidence': confidence,
                    'title': title
                })
        
        # Merge adjacent sections with similar content
        sections = self._merge_adjacent_bom_sections(sections)
        
        return sections
    
    def _split_into_sections(self, content: str) -> List[str]:
        """Split content into logical sections"""
        sections = []
        
        # Split by markdown headers
        header_pattern = r'\n(#{1,6}\s+.*?)\n'
        parts = re.split(header_pattern, content, flags=re.MULTILINE)
        
        current_section = ""
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Content part
                current_section += part
            else:  # Header part
                if current_section.strip():
                    sections.append(current_section.strip())
                current_section = part + "\n"
        
        # Add the last section
        if current_section.strip():
            sections.append(current_section.strip())
        
        # If no headers found, split by double newlines
        if len(sections) <= 1:
            sections = [s.strip() for s in content.split('\n\n') if s.strip()]
        
        return sections
    
    def _analyze_bom_likelihood(self, text: str) -> float:
        """
        Analyze text to determine likelihood of being BOM content
        
        Args:
            text: Text to analyze
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not self._nlp:
            return 0.0
        
        doc = self._nlp(text.lower())
        confidence = 0.0
        
        # Check for BOM-related keywords
        bom_keyword_count = 0
        for token in doc:
            if token.text in self._bom_keywords:
                bom_keyword_count += 1
        
        if bom_keyword_count > 0:
            confidence += min(bom_keyword_count * 0.1, 0.4)
        
        # Penalize legal/license content
        legal_keywords = ['license', 'copyright', 'warranty', 'liability', 'terms', 'conditions', 'agreement']
        legal_count = sum(1 for keyword in legal_keywords if keyword in text.lower())
        if legal_count > 0:
            confidence -= min(legal_count * 0.2, 0.5)  # Significant penalty for legal content
        
        # Check for quantity patterns
        quantity_patterns = [
            r'\d+\s*(x|pcs?|pieces?|units?|each|per)\s+',
            r'\d+\s+\w+',  # number + word
            r'\*\s*\d+',   # bullet with number
            r'^\s*\d+\s+', # line starting with number
        ]
        
        quantity_matches = 0
        for pattern in quantity_patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            quantity_matches += len(matches)
        
        if quantity_matches > 0:
            confidence += min(quantity_matches * 0.05, 0.3)
        
        # Check for list-like structures
        if re.search(r'^\s*[\*\-\+]\s+', text, re.MULTILINE):  # Bullet points
            confidence += 0.1
        if re.search(r'^\s*\d+\.\s+', text, re.MULTILINE):  # Numbered lists
            confidence += 0.1
        
        # Check for material/component indicators
        material_indicators = ['silicone', 'plastic', 'metal', 'wood', 'fabric', 'rubber', 'glass']
        for indicator in material_indicators:
            if indicator in text.lower():
                confidence += 0.05
        
        # Check for size/specification patterns
        if re.search(r'\d+\s*(mm|cm|m|inch|in|ft|feet)', text, re.IGNORECASE):
            confidence += 0.1
        
        return round(min(confidence, 0.9), 2)
    
    def _extract_section_title(self, text: str) -> str:
        """Extract section title from text"""
        lines = text.split('\n')
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if line.startswith('#'):
                return line.lstrip('#').strip()
            if line and not line.startswith(('*', '-', '+', '1.', '2.', '3.')):
                return line[:50]  # First 50 chars as title
        return "BOM Section"
    
    def _merge_adjacent_bom_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge adjacent sections that are likely part of the same BOM
        
        Args:
            sections: List of BOM section dictionaries
            
        Returns:
            List of merged sections
        """
        if len(sections) <= 1:
            return sections
        
        merged = []
        current_section = sections[0]
        
        for next_section in sections[1:]:
            # Check if sections should be merged
            if self._should_merge_sections(current_section, next_section):
                # Merge sections
                current_section = {
                    'content': current_section['content'] + '\n\n' + next_section['content'],
                    'confidence': max(current_section['confidence'], next_section['confidence']),
                    'title': current_section['title']  # Keep first title
                }
            else:
                # Add current section and start new one
                merged.append(current_section)
                current_section = next_section
        
        # Add the last section
        merged.append(current_section)
        
        return merged
    
    def _should_merge_sections(self, section1: Dict[str, Any], section2: Dict[str, Any]) -> bool:
        """
        Determine if two sections should be merged
        
        Args:
            section1: First section
            section2: Second section
            
        Returns:
            True if sections should be merged
        """
        # Merge if both have similar confidence levels
        confidence_diff = abs(section1['confidence'] - section2['confidence'])
        if confidence_diff < 0.1:
            return True
        
        # Merge if both contain similar content patterns
        content1 = section1['content'].lower()
        content2 = section2['content'].lower()
        
        # Check for similar BOM indicators
        bom_indicators = ['*', 'bullet', 'list', 'item', 'part', 'component']
        indicators1 = sum(1 for indicator in bom_indicators if indicator in content1)
        indicators2 = sum(1 for indicator in bom_indicators if indicator in content2)
        
        if indicators1 > 0 and indicators2 > 0 and abs(indicators1 - indicators2) <= 1:
            return True
        
        return False


class BOMProcessor:
    """Processes raw BOM data into structured components"""
    
    def __init__(self):
        self._component_id_counter = 0
    
    def process_bom_sources(self, sources: List[BOMSource]) -> List['Component']:
        """
        Process all BOM sources into components
        
        Args:
            sources: List of BOMSource objects
            
        Returns:
            List of Component objects with deduplication applied
        """
        all_components = []
        
        for source in sources:
            # Clean and normalize text
            cleaned_text = self._clean_text(source.raw_content)
            
            # Extract components based on source type
            if source.source_type == BOMSourceType.BOM_FILE:
                components = self._extract_components_from_file(cleaned_text, source)
            else:
                components = self._extract_components_from_markdown(cleaned_text, source)
            
            all_components.extend(components)
        
        # Deduplicate components
        unique_components = self._deduplicate_components(all_components)
        
        return unique_components
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove markdown formatting (but preserve bullet points)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Remove bold
        text = re.sub(r'^\*\*$', '', text, flags=re.MULTILINE)  # Remove standalone ** lines
        text = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'\1', text)  # Remove italic (but not bullet points)
        text = re.sub(r'^=+\s*$', '', text, flags=re.MULTILINE)  # Remove separator lines
        
        # Normalize whitespace
        text = re.sub(r'\n\s*\n', '\n', text)  # Remove empty lines
        text = re.sub(r'[ \t]+', ' ', text)    # Normalize spaces
        text = text.strip()
        
        return text
    
    def _extract_components_from_file(self, content: str, source: BOMSource) -> List['Component']:
        """Extract components from structured file formats"""
        file_path = source.file_path.lower()
        
        if file_path.endswith('.csv'):
            return self._extract_components_from_csv(content, source)
        elif file_path.endswith(('.json', '.yaml', '.yml')):
            return self._extract_components_from_structured(content, source)
        else:
            # Fallback to markdown parsing
            return self._extract_components_from_markdown(content, source)
    
    def _extract_components_from_csv(self, content: str, source: BOMSource) -> List['Component']:
        """Extract components from CSV format"""
        components = []
        lines = content.strip().split('\n')
        
        if len(lines) < 2:
            return components
        
        # Parse header
        header = [col.strip().lower() for col in lines[0].split(',')]
        
        # Find column indices
        name_col = self._find_column_index(header, ['item', 'name', 'component', 'part'])
        qty_col = self._find_column_index(header, ['quantity', 'qty', 'amount', 'count'])
        unit_col = self._find_column_index(header, ['unit', 'units', 'measure'])
        
        if name_col is None:
            return components
        
        # Parse data rows
        for line in lines[1:]:
            if not line.strip():
                continue
                
            columns = [col.strip() for col in line.split(',')]
            if len(columns) <= name_col:
                continue
            
            name = columns[name_col]
            if not name:
                continue
            
            # Extract quantity
            quantity = 1.0
            if qty_col is not None and qty_col < len(columns):
                try:
                    quantity = float(columns[qty_col])
                except (ValueError, TypeError):
                    quantity = 1.0
            
            # Extract unit
            unit = "pcs"
            if unit_col is not None and unit_col < len(columns):
                unit = columns[unit_col] or "pcs"
            
            component = Component(
                id=self._generate_component_id(name),
                name=name,
                quantity=quantity,
                unit=unit,
                metadata={
                    "source": source.source_type.value,
                    "file_path": source.file_path,
                    "confidence": source.confidence
                }
            )
            components.append(component)
        
        return components
    
    def _extract_components_from_markdown(self, content: str, source: BOMSource) -> List['Component']:
        """Extract components from markdown list format"""
        components = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for bullet point patterns
            if line.startswith(('*', '-', '+')):
                component = self._parse_markdown_line(line, source)
                if component:
                    components.append(component)
        
        return components
    
    def _parse_markdown_line(self, line: str, source: BOMSource) -> Optional['Component']:
        """Parse a single markdown line into a component"""
        # Remove bullet point
        line = re.sub(r'^[\*\-\+]\s*', '', line)
        
        # Pattern: "quantity name (file.ext)" or "quantity name"
        patterns = [
            r'(\d+(?:\.\d+)?)\s+([^(]+?)\s*\(([^)]+)\)',  # "1 item (file.stl)"
            r'(\d+(?:\.\d+)?)\s+(.+)',                    # "1 item"
            r'(\d+(?:\.\d+)?)x\s+([^(]+?)\s*\(([^)]+)\)', # "2x item (file.stl)"
            r'(\d+(?:\.\d+)?)x\s+(.+)',                   # "2x item"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                quantity = float(match.group(1))
                name = match.group(2).strip()
                
                # Extract file reference if present
                file_reference = None
                if len(match.groups()) >= 3 and match.group(3):
                    file_reference = match.group(3).strip()
                
                # Clean up name
                name = re.sub(r'[^\w\s\-.,()]', '', name).strip()
                
                if name and len(name) > 2:  # Minimum name length
                    metadata = {
                        "source": source.source_type.value,
                        "file_path": source.file_path,
                        "confidence": source.confidence
                    }
                    
                    if file_reference:
                        metadata["file_reference"] = file_reference
                    
                    return Component(
                        id=self._generate_component_id(name),
                        name=name,
                        quantity=quantity,
                        unit="pcs",  # Default unit
                        metadata=metadata
                    )
        
        return None
    
    def _extract_components_from_structured(self, content: str, source: BOMSource) -> List['Component']:
        """
        Extract components from structured formats (JSON, YAML).
        
        Supports multiple BOM schemas:
        - Array of component objects: [{"name": "...", "quantity": ...}, ...]
        - Object with components array: {"components": [...], ...}
        - Object with parts array: {"parts": [...], ...}
        - Object with items array: {"items": [...], ...}
        
        Args:
            content: File content as string
            source: BOMSource object with file metadata
            
        Returns:
            List of Component objects
        """
        file_path = source.file_path.lower()
        components = []
        
        try:
            # Parse JSON or YAML
            if file_path.endswith('.json'):
                data = json.loads(content)
            elif file_path.endswith(('.yaml', '.yml')):
                data = yaml.safe_load(content)
            else:
                # Unknown format, fallback to markdown
                return self._extract_components_from_markdown(content, source)
            
            if not data:
                return []
            
            # Extract components array from different schema formats
            components_data = None
            
            if isinstance(data, list):
                # Array of components
                components_data = data
            elif isinstance(data, dict):
                # Object with components array (check top level first)
                for key in ['components', 'parts', 'items', 'materials', 'bom']:
                    if key in data:
                        value = data[key]
                        # Handle nested structure: {"bom": {"components": [...]}}
                        if isinstance(value, dict):
                            for nested_key in ['components', 'parts', 'items', 'materials']:
                                if nested_key in value and isinstance(value[nested_key], list):
                                    components_data = value[nested_key]
                                    break
                        elif isinstance(value, list):
                            components_data = value
                            break
                    if components_data:
                        break
                
                # If no array found, try to extract from dict values
                if not components_data:
                    # Check if dict values are component objects
                    if all(isinstance(v, dict) for v in data.values()):
                        components_data = list(data.values())
            
            if not components_data:
                # Couldn't find components, fallback to markdown
                logger.warning(f"Could not find components array in structured BOM: {source.file_path}")
                return self._extract_components_from_markdown(content, source)
            
            # Parse each component
            for comp_data in components_data:
                if not isinstance(comp_data, dict):
                    continue
                
                component = self._parse_component_from_dict(comp_data, source)
                if component:
                    components.append(component)
            
            return components
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON BOM {source.file_path}: {e}")
            return self._extract_components_from_markdown(content, source)
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML BOM {source.file_path}: {e}")
            return self._extract_components_from_markdown(content, source)
        except Exception as e:
            logger.warning(f"Error parsing structured BOM {source.file_path}: {e}", exc_info=True)
            return self._extract_components_from_markdown(content, source)
    
    def _parse_component_from_dict(self, comp_data: Dict[str, Any], source: BOMSource) -> Optional['Component']:
        """
        Parse a single component from dictionary data.
        
        Supports various field name variations:
        - Name: name, item, component, part, id, title
        - Quantity: quantity, qty, amount, count, number
        - Unit: unit, units, measure, uom
        - Description: description, desc, notes, comment
        
        Args:
            comp_data: Dictionary with component data
            source: BOMSource object
            
        Returns:
            Component object or None if parsing fails
        """
        # Extract name
        name = None
        for key in ['name', 'item', 'component', 'part', 'id', 'title']:
            if key in comp_data and comp_data[key]:
                name = str(comp_data[key]).strip()
                break
        
        if not name:
            return None
        
        # Extract quantity
        quantity = 1.0
        for key in ['quantity', 'qty', 'amount', 'count', 'number']:
            if key in comp_data:
                try:
                    quantity = float(comp_data[key])
                    break
                except (ValueError, TypeError):
                    continue
        
        # Extract unit
        unit = "pcs"
        for key in ['unit', 'units', 'measure', 'uom']:
            if key in comp_data and comp_data[key]:
                unit = str(comp_data[key]).strip()
                break
        
        # Extract description/notes (store in metadata since Component doesn't have description field)
        description = None
        for key in ['description', 'desc', 'notes', 'comment', 'note']:
            if key in comp_data and comp_data[key]:
                description = str(comp_data[key]).strip()
                break
        
        # Extract metadata (all other fields)
        standard_fields = ['name', 'item', 'component', 'part', 'id', 'title',
                          'quantity', 'qty', 'amount', 'count', 'number',
                          'unit', 'units', 'measure', 'uom',
                          'description', 'desc', 'notes', 'comment', 'note']
        metadata = {k: v for k, v in comp_data.items() 
                    if k not in standard_fields}
        
        # Add description to metadata if present
        if description:
            metadata['description'] = description
        
        # Add source metadata
        metadata.update({
            "source": source.source_type.value,
            "file_path": source.file_path,
            "confidence": source.confidence
        })
        
        # Generate component ID
        component_id = self._generate_component_id(name)
        
        # Create component
        return Component(
            id=component_id,
            name=name,
            quantity=quantity,
            unit=unit,
            metadata=metadata
        )
    
    def _find_column_index(self, header: List[str], possible_names: List[str]) -> Optional[int]:
        """Find the index of a column by name"""
        for i, col in enumerate(header):
            if any(name in col for name in possible_names):
                return i
        return None
    
    def _generate_component_id(self, name: str) -> str:
        """Generate a unique component ID"""
        self._component_id_counter += 1
        # Create a clean ID from the name
        clean_name = re.sub(r'[^\w]', '_', name.lower())
        return f"{clean_name}_{self._component_id_counter}"
    
    def _deduplicate_components(self, components: List['Component']) -> List['Component']:
        """Remove duplicate components, keeping the one with highest confidence"""
        component_map = {}
        
        for component in components:
            # Use name as the key for deduplication
            key = component.name.lower().strip()
            
            if key not in component_map:
                component_map[key] = component
            else:
                # Keep the component with higher confidence
                existing = component_map[key]
                if component.metadata.get("confidence", 0) > existing.metadata.get("confidence", 0):
                    component_map[key] = component
        
        return list(component_map.values())


class BOMBuilder:
    """Builds final BOM from processed components"""
    
    def __init__(self):
        pass
    
    def build_bom(self, components: List[Component], project_name: str = "Project BOM") -> 'BillOfMaterials':
        """
        Build final BOM with validation and metadata
        
        Args:
            components: List of processed components
            project_name: Name for the BOM
            
        Returns:
            BillOfMaterials object
        """
        from ..models.bom import BillOfMaterials
        from datetime import datetime
        
        # Validate components
        validated_components = self._validate_components(components)
        
        # Create BOM
        bom = BillOfMaterials(
            name=project_name,
            components=validated_components,
            metadata={
                'generated_at': datetime.now().isoformat() + 'Z',
                'source_count': len(components),
                'final_count': len(validated_components),
                'generation_method': 'bom_normalization'
            }
        )
        
        return bom
    
    def _validate_components(self, components: List[Component]) -> List[Component]:
        """Validate components and filter out invalid ones"""
        validated = []
        
        for component in components:
            try:
                # Basic validation
                if not component.name or len(component.name.strip()) < 2:
                    continue
                if component.quantity <= 0:
                    continue
                if not component.unit:
                    component.unit = "pcs"  # Default unit
                
                validated.append(component)
            except Exception:
                # Skip invalid components
                continue
        
        return validated
