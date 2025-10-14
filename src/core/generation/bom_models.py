"""
BOM normalization data models and utilities
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import re

# Import Component from the BOM models
from ..models.bom import Component


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
    """Collects BOM data from multiple sources in a project"""
    
    def __init__(self):
        self._bom_file_patterns = [
            r"(?i)bom(\.csv|\.txt|\.md|\.json|\.yaml|\.yml)?$",
            r"(?i)bill_of_materials(\.csv|\.txt|\.md|\.json|\.yaml|\.yml)?$",
            r"(?i)materials(\.csv|\.txt|\.md|\.json|\.yaml|\.yml)?$",
            r"(?i)parts(\.csv|\.txt|\.md|\.json|\.yaml|\.yml)?$"
        ]
        
        self._materials_section_patterns = [
            r"(?i)(?:##?\s*)?materials?[:\s]*\n(.*?)(?=\n##|\n\*\*|\Z)",
            r"(?i)(?:##?\s*)?bill\s+of\s+materials?[:\s]*\n(.*?)(?=\n##|\n\*\*|\Z)",
            r"(?i)(?:##?\s*)?parts?[:\s]*\n(.*?)(?=\n##|\n\*\*|\Z)",
            r"(?i)(?:##?\s*)?components?[:\s]*\n(.*?)(?=\n##|\n\*\*|\Z)"
        ]
    
    def collect_bom_data(self, project_data) -> List[BOMSource]:
        """
        Collect BOM data from all available sources in the project
        
        Args:
            project_data: ProjectData object containing files and documentation
            
        Returns:
            List of BOMSource objects with extracted BOM data
        """
        sources = []
        
        # 1. Extract from README materials sections
        sources.extend(self._extract_from_readme(project_data))
        
        # 2. Extract from dedicated BOM files
        sources.extend(self._extract_from_bom_files(project_data))
        
        # 3. Extract from documentation files
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
        """Extract components from structured formats (JSON, YAML)"""
        # For now, fallback to markdown parsing
        # TODO: Implement proper JSON/YAML parsing
        return self._extract_components_from_markdown(content, source)
    
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
                'generated_at': datetime.utcnow().isoformat() + 'Z',
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
