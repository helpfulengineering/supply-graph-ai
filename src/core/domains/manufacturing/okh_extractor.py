from typing import Dict, List, Any

from src.core.models.base.base_extractors import BaseExtractor, ExtractionMetadata, ExtractionQuality, ExtractionFlag
from src.core.models.base.base_types import NormalizedRequirements, NormalizedCapabilities
from src.core.models.okh import OKHManifest, ProcessRequirement

class OKHExtractor(BaseExtractor):
    """Implementation of BaseExtractor for OKH data"""
    
    def __init__(self):
        super().__init__()
        self.okh_manifest = None
    
    def _initial_parse_requirements(self, content: Dict[str, Any]) -> OKHManifest:
        """Initial parsing of OKH requirements data"""
        try:
            # Check if content is already an OKH manifest
            if isinstance(content, OKHManifest):
                self.okh_manifest = content
                return content
                
            # Otherwise, parse the dictionary into an OKH manifest
            self.okh_manifest = OKHManifest.from_dict(content)
            return self.okh_manifest
        except Exception as e:
            # Log the error
            parsing_error = f"Error parsing OKH content: {str(e)}"
            
            # Create an extraction result with error
            metadata = ExtractionMetadata(
                extraction_quality=ExtractionQuality.INSUFFICIENT,
                flags=[ExtractionFlag.REQUIRES_HUMAN_VERIFICATION],
                processing_logs=[parsing_error]
            )
            
            # Return empty manifest
            return OKHManifest(
                title="",
                repo="",
                version="",
                license=None,
                licensor="",
                documentation_language="",
                function=""
            )
    
    def _detailed_extract_requirements(self, parsed_data: OKHManifest) -> NormalizedRequirements:
        """Extract detailed requirements from OKH manifest"""
        # Extract process requirements
        process_reqs = []
        
        # Add requirements from manufacturing specs
        if parsed_data.manufacturing_specs:
            process_reqs.extend(parsed_data.manufacturing_specs.process_requirements)
        
        # Extract implicit requirements from manufacturing processes
        for process in parsed_data.manufacturing_processes:
            req = ProcessRequirement(
                process_name=process,
                parameters={},
                validation_criteria={},
                required_tools=[]
            )
            process_reqs.append(req)
        
        # Extract requirements from parts
        for part in parsed_data.parts:
            for tsdc in part.tsdc:
                # Create process requirement based on TSDC
                params = part.manufacturing_params.copy() if hasattr(part, 'manufacturing_params') else {}
                params['material'] = part.material
                
                req = ProcessRequirement(
                    process_name=tsdc,
                    parameters=params,
                    validation_criteria={},
                    required_tools=[]
                )
                process_reqs.append(req)
        
        # Build normalized requirements content
        content = {
            "id": str(parsed_data.id),
            "name": parsed_data.title,
            "version": parsed_data.version,
            "processes": [pr.process_name for pr in process_reqs],
            "materials": [m.material_id for m in parsed_data.materials],
            "tools": parsed_data.tool_list.copy() if parsed_data.tool_list else [],
            "process_requirements": [self._convert_process_req_to_dict(req) for req in process_reqs],
            "tsdcs": parsed_data.tsdc.copy() if parsed_data.tsdc else [],
            "parts": [self._convert_part_to_dict(part) for part in parsed_data.parts]
        }
        
        # Add dimensions if available
        if parsed_data.manufacturing_specs and parsed_data.manufacturing_specs.outer_dimensions:
            content["outer_dimensions"] = parsed_data.manufacturing_specs.outer_dimensions
        
        # Create confidence scores
        confidence_scores = {
            "name": 1.0 if parsed_data.title else 0.0,
            "processes": 1.0 if process_reqs else 0.0,
            "materials": 1.0 if parsed_data.materials else 0.0,
            "tools": 1.0 if parsed_data.tool_list else 0.0,
            "tsdcs": 1.0 if parsed_data.tsdc else 0.0
        }
        
        # Create extraction metadata
        metadata = ExtractionMetadata(
            source_document=parsed_data.repo,
            confidence_scores=confidence_scores,
            processing_logs=[f"Extracted {len(process_reqs)} process requirements"]
        )
        
        # Create normalized requirements with metadata
        requirements = NormalizedRequirements(
            content=content,
            domain="manufacturing"
        )
        
        return requirements
    
    def _validate_and_refine_requirements(self, extracted_data: NormalizedRequirements) -> NormalizedRequirements:
        """Validate and refine extracted requirements"""
        return extracted_data
    
    def _initial_parse_capabilities(self, content: Dict[str, Any]) -> Dict:
        """Initial parsing of capabilities data"""
        return content
    
    def _detailed_extract_capabilities(self, parsed_data: Dict) -> NormalizedCapabilities:
        """Extract detailed capabilities"""
        return NormalizedCapabilities(
            content={},
            domain="manufacturing"
        )
    
    def _get_critical_fields(self, extraction_type: str) -> List[str]:
        """Define critical fields for quality assessment"""
        if extraction_type == "requirements":
            return ["name", "processes", "materials", "tools", "tsdcs"]
        return []
    
    def _convert_process_req_to_dict(self, req: ProcessRequirement) -> Dict:
        """Convert process requirement to dictionary"""
        return {
            "process_name": req.process_name,
            "parameters": req.parameters,
            "validation_criteria": req.validation_criteria,
            "required_tools": req.required_tools,
            "notes": req.notes
        }
    
    def _convert_part_to_dict(self, part) -> Dict:
        """Convert part to dictionary"""
        # Handle different part object types
        if hasattr(part, 'to_dict'):
            return part.to_dict()
        
        # Basic conversion for simple part objects
        result = {
            "name": getattr(part, 'name', ''),
            "id": str(getattr(part, 'id', '')),
            "tsdc": getattr(part, 'tsdc', []),
            "material": getattr(part, 'material', None)
        }
        
        # Add other fields if available
        for field in ['source', 'export', 'auxiliary', 'image']:
            if hasattr(part, field):
                result[field] = getattr(part, field)
        
        return result