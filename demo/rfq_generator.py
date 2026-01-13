"""
RFQ Generation Module

Generates Request for Quotation (RFQ) documents for matched facilities.
This is a demonstration feature showing how RFQs could be generated from matching results.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional


class RFQTemplate:
    """
    Standard RFQ template with placeholders for data substitution.
    
    Based on the approved template from item3-detailed-requirements.md.
    """
    
    TEMPLATE = """REQUEST FOR QUOTATION (RFQ)

Date: {date}
RFQ Number: {rfq_number}

To: {facility_name}
Contact: {facility_contact}
Location: {facility_location}

Subject: Request for Quotation - {component_name} for {design_name}

DESIGN INFORMATION:
- Design Name: {design_name}
- Design ID: {okh_id}
{component_section}
- Quantity Required: {quantity} {unit}
- Specifications: {specifications}

MANUFACTURING REQUIREMENTS:
- Processes: {process_list}
- Materials: {material_list}
- Quality Level: {quality_level}
- Delivery Timeline: {timeline}

Please provide quotation including:
- Unit price
- Total price for quantity specified
- Lead time
- Payment terms
- Shipping options

Thank you for your consideration.

{contact_info}
"""
    
    def __init__(self):
        """Initialize RFQ template."""
        pass
    
    def generate_rfq_number(self) -> str:
        """
        Generate a unique RFQ number.
        
        Returns:
            Unique RFQ number string (e.g., "RFQ-20250115-abc123")
        """
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8]
        return f"RFQ-{date_str}-{unique_id}"
    
    def render(
        self,
        facility_name: str,
        facility_contact: str,
        facility_location: str,
        design_name: str,
        okh_id: str,
        quantity: int,
        unit: str = "units",
        component_name: Optional[str] = None,
        component_section: Optional[str] = None,
        specifications: str = "See design documentation",
        process_list: str = "See manufacturing requirements",
        material_list: str = "See design specifications",
        quality_level: str = "professional",
        timeline: str = "To be determined",
        contact_info: str = "Please contact for additional information"
    ) -> str:
        """
        Render RFQ template with provided data.
        
        Args:
            facility_name: Name of the facility
            facility_contact: Contact information for facility
            facility_location: Location of facility
            design_name: Name of the OKH design
            okh_id: OKH design ID
            quantity: Quantity required
            unit: Unit of measurement (default: "units")
            component_name: Component name (if nested design)
            component_section: Additional component section text
            specifications: Design specifications
            process_list: Manufacturing processes required
            material_list: Materials required
            quality_level: Quality level (hobby, professional, medical)
            timeline: Delivery timeline
            contact_info: Contact information
            
        Returns:
            Rendered RFQ text
        """
        # Default component section if not provided
        if component_section is None:
            if component_name:
                component_section = f"- Component: {component_name}"
            else:
                component_section = ""
        
        # Use component_name or design_name for subject
        subject_component = component_name if component_name else design_name
        
        rfq_number = self.generate_rfq_number()
        date = datetime.now().strftime("%Y-%m-%d")
        
        return self.TEMPLATE.format(
            date=date,
            rfq_number=rfq_number,
            facility_name=facility_name,
            facility_contact=facility_contact,
            facility_location=facility_location,
            component_name=subject_component,
            design_name=design_name,
            okh_id=okh_id,
            component_section=component_section,
            quantity=quantity,
            unit=unit,
            specifications=specifications,
            process_list=process_list,
            material_list=material_list,
            quality_level=quality_level,
            timeline=timeline,
            contact_info=contact_info
        )


def extract_facility_info(
    tree_data: Dict[str, Any],
    facility_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extract facility information from tree data and optional facility data.
    
    Args:
        tree_data: Tree dictionary from matching result
        facility_data: Optional full facility data dictionary
        
    Returns:
        Dictionary with facility information:
        - name: str
        - location: Dict with city, state, country, gps_coordinates
        - contact: Dict with email, phone, etc.
    """
    info = {
        'name': tree_data.get('facility_name', 'Unknown Facility'),
        'location': {},
        'contact': {}
    }
    
    # Extract location from tree metadata
    metadata = tree_data.get('metadata', {})
    location_info = metadata.get('facility_location', {})
    
    if location_info:
        info['location'] = {
            'city': location_info.get('city', 'N/A'),
            'state': location_info.get('state', ''),
            'country': location_info.get('country', 'N/A'),
            'gps_coordinates': location_info.get('gps_coordinates', '')
        }
    
    # Extract contact from facility_data if provided
    if facility_data:
        contact = facility_data.get('contact', {})
        if contact:
            info['contact'] = {
                'email': contact.get('email', ''),
                'phone': contact.get('phone', ''),
                'name': contact.get('name', '')
            }
    
    # Format location string
    location_parts = []
    if info['location'].get('city') and info['location']['city'] != 'N/A':
        location_parts.append(info['location']['city'])
    if info['location'].get('state'):
        location_parts.append(info['location']['state'])
    if info['location'].get('country') and info['location']['country'] != 'N/A':
        location_parts.append(info['location']['country'])
    
    info['location_string'] = ', '.join(location_parts) if location_parts else 'Location not specified'
    
    # Format contact string
    contact_parts = []
    if info['contact'].get('email'):
        contact_parts.append(f"Email: {info['contact']['email']}")
    if info['contact'].get('phone'):
        contact_parts.append(f"Phone: {info['contact']['phone']}")
    if info['contact'].get('name'):
        contact_parts.append(f"Contact: {info['contact']['name']}")
    
    info['contact_string'] = '\n'.join(contact_parts) if contact_parts else 'Contact information not available'
    
    return info


def extract_design_info(design_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract design information from OKH design data.
    
    Args:
        design_data: OKH design dictionary (can be raw OKH manifest with 'title' 
                    or metadata object with 'name')
        
    Returns:
        Dictionary with design information:
        - name: str
        - okh_id: str
        - specifications: str
    """
    # OKH manifests use 'title', metadata objects use 'name'
    # Check both to handle either case
    design_name = design_data.get('name') or design_data.get('title', 'Unknown Design')
    
    info = {
        'name': design_name,
        'okh_id': str(design_data.get('id', design_data.get('okh_id', 'N/A'))),
        'specifications': ''
    }
    
    # Build specifications from available fields
    spec_parts = []
    if design_data.get('function'):
        spec_parts.append(f"Function: {design_data['function']}")
    if design_data.get('description'):
        spec_parts.append(design_data['description'])
    if design_data.get('version'):
        spec_parts.append(f"Version: {design_data['version']}")
    
    info['specifications'] = ' | '.join(spec_parts) if spec_parts else 'See design documentation'
    
    return info


def extract_component_info(component_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract component information for nested designs.
    
    Args:
        component_data: Component dictionary from tree or component mapping
        
    Returns:
        Dictionary with component information:
        - component_id: str
        - component_name: str
        - hierarchy: str (for nested components)
    """
    info = {
        'component_id': component_data.get('component_id', 'Unknown'),
        'component_name': component_data.get('component_name', 'Unknown Component'),
        'hierarchy': ''
    }
    
    # Build hierarchy string if parent component exists
    parent = component_data.get('parent_component')
    if parent:
        info['hierarchy'] = f" (for {parent})"
    
    return info


def calculate_quantity_allocation(
    total_quantity: int,
    facility_count: int
) -> Dict[str, int]:
    """
    Calculate quantity allocation across facilities using equal split.
    
    Args:
        total_quantity: Total quantity required
        facility_count: Number of facilities
        
    Returns:
        Dictionary mapping facility index to allocated quantity
    """
    if facility_count <= 0:
        return {}
    
    if facility_count == 1:
        return {0: total_quantity}
    
    # Equal split with remainder distributed
    base_quantity = total_quantity // facility_count
    remainder = total_quantity % facility_count
    
    allocation = {}
    for i in range(facility_count):
        # Distribute remainder to first facilities
        quantity = base_quantity + (1 if i < remainder else 0)
        allocation[i] = quantity
    
    return allocation


def extract_manufacturing_requirements(tree_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract manufacturing requirements from tree data.
    
    Args:
        tree_data: Tree dictionary from matching result
        
    Returns:
        Dictionary with:
        - process_list: str (formatted list of processes)
        - material_list: str (formatted list of materials)
    """
    # Extract capabilities (processes)
    capabilities = tree_data.get('capabilities_used', [])
    process_names = []
    for cap in capabilities:
        if isinstance(cap, str):
            # Handle Wikipedia URLs
            if 'wikipedia.org/wiki/' in cap:
                process_name = cap.split('/wiki/')[-1].replace('_', ' ').title()
                process_names.append(process_name)
            else:
                process_names.append(cap)
        else:
            process_names.append(str(cap))
    
    process_list = ', '.join(process_names) if process_names else 'See design requirements'
    
    # Extract materials
    materials = tree_data.get('materials_required', [])
    material_names = []
    for mat in materials:
        if isinstance(mat, str):
            # Parse MaterialSpec string representation
            if 'MaterialSpec' in mat:
                import re
                name_match = re.search(r"name='([^']+)'", mat)
                qty_match = re.search(r"quantity=([^,)]+)", mat)
                unit_match = re.search(r"unit='([^']+)'", mat)
                
                name = name_match.group(1) if name_match else "Unknown"
                qty = qty_match.group(1) if qty_match else None
                unit = unit_match.group(1) if unit_match else ""
                
                if qty and qty != "None" and qty != "N/A":
                    material_names.append(f"{name} ({qty} {unit})")
                else:
                    material_names.append(name)
            else:
                material_names.append(mat)
        elif isinstance(mat, dict):
            name = mat.get('name', mat.get('material_id', 'Unknown'))
            qty = mat.get('quantity')
            unit = mat.get('unit', '')
            if qty:
                material_names.append(f"{name} ({qty} {unit})")
            else:
                material_names.append(name)
        else:
            material_names.append(str(mat))
    
    material_list = ', '.join(material_names) if material_names else 'See design specifications'
    
    return {
        'process_list': process_list,
        'material_list': material_list
    }


def generate_rfq(
    matching_result: Dict[str, Any],
    design_data: Dict[str, Any],
    quantity: int,
    parsed_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Generate RFQs for all matched facilities.
    
    Args:
        matching_result: Full matching result from API
        design_data: OKH design data dictionary
        quantity: Total quantity required
        parsed_data: Optional pre-parsed matching data (from results_parser)
        
    Returns:
        List of RFQ dictionaries, each containing:
        - facility_name: str
        - rfq_text: str
        - quantity: int
        - components: List[str] (for nested designs)
    """
    from demo.results_parser import detect_matching_mode, parse_nested_solution, parse_single_level_solutions
    
    template = RFQTemplate()
    rfqs = []
    
    # Extract design info
    design_info = extract_design_info(design_data)
    
    # Get matching data
    if matching_result.get('status') != 'success':
        return rfqs
    
    data = matching_result.get('data', {})
    
    # Detect matching mode
    matching_mode = detect_matching_mode(data)
    
    # Parse solution data
    # For RFQ generation, we want ALL solutions, not just the selected one
    if parsed_data is None:
        if matching_mode == 'nested':
            parsed_data = parse_nested_solution(data, use_deduplication=True)
        else:
            # Don't use selection for RFQ generation - we want RFQs for all facilities
            parsed_data = parse_single_level_solutions(data, use_selection=False)
    elif matching_mode == 'single-level':
        # Even if parsed_data is provided (from UI with selection), re-parse without selection
        # to get all solutions for RFQ generation
        parsed_data = parse_single_level_solutions(data, use_selection=False)
    
    # Generate RFQs based on matching mode
    if matching_mode == 'nested':
        # Nested matching: one RFQ per facility with all components they produce
        deduplicated_facilities = parsed_data.get('deduplicated_facilities', [])
        
        if not deduplicated_facilities:
            # Fallback: try to get facilities from all_trees directly
            all_trees = parsed_data.get('all_trees', [])
            if all_trees:
                # Group trees by facility name
                facilities_dict = {}
                for tree in all_trees:
                    facility_name = tree.get('facility_name', 'Unknown')
                    if facility_name not in facilities_dict:
                        facilities_dict[facility_name] = []
                    facilities_dict[facility_name].append(tree)
                
                # Create facility entries from grouped trees
                facilities_in_solution = []
                for facility_name, trees in facilities_dict.items():
                    primary_tree = trees[0]  # Use first tree as primary
                    facilities_in_solution.append({
                        'name': facility_name,
                        'tree': primary_tree,
                        'trees': trees,
                        'component_id': primary_tree.get('component_id'),
                        'component_name': primary_tree.get('component_name')
                    })
            else:
                # Final fallback to facilities_in_solution from parsed_data
                facilities_in_solution = parsed_data.get('facilities_in_solution', [])
            
            # Generate RFQs from facilities_in_solution
            for facility_info in facilities_in_solution:
                tree = facility_info.get('tree', {})
                if not tree:
                    # Try to get from trees list
                    trees = facility_info.get('trees', [])
                    if trees:
                        tree = trees[0] if isinstance(trees[0], dict) else {}
                
                if not tree:
                    continue
                
                facility_info_extracted = extract_facility_info(tree)
                mfg_reqs = extract_manufacturing_requirements(tree)
                
                # Get component info (try multiple sources)
                component_id = facility_info.get('component_id') or tree.get('component_id')
                component_name = facility_info.get('component_name') or tree.get('component_name') or design_info['name']
                
                # Calculate quantity (equal split)
                facility_count = len(facilities_in_solution)
                allocation = calculate_quantity_allocation(quantity, facility_count)
                facility_index = facilities_in_solution.index(facility_info)
                allocated_quantity = allocation.get(facility_index, quantity // facility_count)
                
                # Generate RFQ
                component_section = f"- Component: {component_name}" if component_id else None
                
                rfq_text = template.render(
                    facility_name=facility_info_extracted['name'],
                    facility_contact=facility_info_extracted['contact_string'],
                    facility_location=facility_info_extracted['location_string'],
                    design_name=design_info['name'],
                    okh_id=design_info['okh_id'],
                    quantity=allocated_quantity,
                    component_name=component_name if component_id else None,
                    component_section=component_section,
                    specifications=design_info['specifications'],
                    process_list=mfg_reqs['process_list'],
                    material_list=mfg_reqs['material_list'],
                    quality_level="professional",
                    timeline="To be determined",
                    contact_info="Please contact for additional information"
                )
                
                rfqs.append({
                    'facility_name': facility_info_extracted['name'],
                    'rfq_text': rfq_text,
                    'quantity': allocated_quantity,
                    'components': [component_name] if component_id else []
                })
        else:
            # Use deduplicated facilities (preferred)
            facility_count = len(deduplicated_facilities)
            allocation = calculate_quantity_allocation(quantity, facility_count)
            
            for idx, facility in enumerate(deduplicated_facilities):
                # Get primary tree for facility info
                primary_tree = facility.get('primary_tree', {})
                if not primary_tree:
                    # Fallback to first component tree
                    components = facility.get('components', [])
                    if components:
                        primary_tree = components[0].get('tree', {})
                
                if not primary_tree:
                    continue
                
                facility_info_extracted = extract_facility_info(primary_tree)
                mfg_reqs = extract_manufacturing_requirements(primary_tree)
                
                # Get all components this facility produces
                components = facility.get('components', [])
                component_names = []
                for comp_info in components:
                    comp_name = comp_info.get('component_name') or comp_info.get('component_id', 'Unknown')
                    component_names.append(comp_name)
                
                # Use first component name for subject, or design name
                primary_component = component_names[0] if component_names else design_info['name']
                
                # Build component section
                if len(component_names) > 1:
                    component_section = "- Components:\n" + "\n".join(f"  - {name}" for name in component_names)
                elif component_names:
                    component_section = f"- Component: {component_names[0]}"
                else:
                    component_section = None
                
                # Get allocated quantity
                allocated_quantity = allocation.get(idx, quantity // facility_count)
                
                # Generate RFQ
                rfq_text = template.render(
                    facility_name=facility_info_extracted['name'],
                    facility_contact=facility_info_extracted['contact_string'],
                    facility_location=facility_info_extracted['location_string'],
                    design_name=design_info['name'],
                    okh_id=design_info['okh_id'],
                    quantity=allocated_quantity,
                    component_name=primary_component,
                    component_section=component_section,
                    specifications=design_info['specifications'],
                    process_list=mfg_reqs['process_list'],
                    material_list=mfg_reqs['material_list'],
                    quality_level="professional",
                    timeline="To be determined",
                    contact_info="Please contact for additional information"
                )
                
                rfqs.append({
                    'facility_name': facility_info_extracted['name'],
                    'rfq_text': rfq_text,
                    'quantity': allocated_quantity,
                    'components': component_names
                })
    else:
        # Single-level matching: one RFQ per solution
        solutions = parsed_data.get('solutions', [])
        facility_count = len(solutions)
        allocation = calculate_quantity_allocation(quantity, facility_count)
        
        for idx, solution in enumerate(solutions):
            tree = solution.get('tree', {})
            if not tree:
                continue
            
            facility_info_extracted = extract_facility_info(tree)
            mfg_reqs = extract_manufacturing_requirements(tree)
            
            # Get allocated quantity
            allocated_quantity = allocation.get(idx, quantity // facility_count)
            
            # Generate RFQ
            rfq_text = template.render(
                facility_name=facility_info_extracted['name'],
                facility_contact=facility_info_extracted['contact_string'],
                facility_location=facility_info_extracted['location_string'],
                design_name=design_info['name'],
                okh_id=design_info['okh_id'],
                quantity=allocated_quantity,
                component_name=None,  # Single-level, no component
                component_section=None,
                specifications=design_info['specifications'],
                process_list=mfg_reqs['process_list'],
                material_list=mfg_reqs['material_list'],
                quality_level="professional",
                timeline="To be determined",
                contact_info="Please contact for additional information"
            )
            
            rfqs.append({
                'facility_name': facility_info_extracted['name'],
                'rfq_text': rfq_text,
                'quantity': allocated_quantity,
                'components': []
            })
    
    return rfqs
