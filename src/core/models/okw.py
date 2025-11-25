from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Set
from enum import Enum
from datetime import datetime, date
from uuid import UUID, uuid4


class FacilityStatus(Enum):
    """Status of manufacturing facility"""
    ACTIVE = "Active"
    PLANNED = "Planned" 
    TEMPORARY_CLOSURE = "Temporary Closure"
    CLOSED = "Closed"


class AccessType(Enum):
    """How manufacturing equipment is accessed"""
    RESTRICTED = "Restricted"
    RESTRICTED_PUBLIC = "Restricted with public hours"
    SHARED = "Shared space"
    PUBLIC = "Public"
    MEMBERSHIP = "Membership"


class BatchSize(Enum):
    """Typical batch size ranges"""
    SMALL = "0 -- 50 units"
    MEDIUM = "50 -- 500 units"
    LARGE = "500 -- 5000 units"
    XLARGE = "5000 + units"


@dataclass
class Address:
    """Location address information"""
    number: Optional[str] = None
    street: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    postcode: Optional[str] = None


@dataclass
class What3Words:
    """What3Words geolocation reference"""
    words: str
    language: str  # ISO 639-2 or ISO 639-3 language code


@dataclass
class Location:
    """Location information with multiple addressing options"""
    address: Optional[Address] = None
    gps_coordinates: Optional[str] = None  # Decimal degrees
    directions: Optional[str] = None
    what3words: Optional[What3Words] = None
    city: Optional[str] = None
    country: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = {}
        if self.address:
            result["address"] = {k: v for k, v in self.address.__dict__.items() if v is not None}
        if self.gps_coordinates:
            result["gps_coordinates"] = self.gps_coordinates
        if self.directions:
            result["directions"] = self.directions
        if self.what3words:
            result["what3words"] = {
                "words": self.what3words.words, 
                "language": self.what3words.language
            }
        if self.city:
            result["city"] = self.city
        if self.country:
            result["country"] = self.country
        return result


@dataclass
class Contact:
    """Contact information"""
    landline: Optional[str] = None
    mobile: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None


@dataclass
class SocialMedia:
    """Social media information"""
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    instagram: Optional[str] = None
    other_urls: List[str] = field(default_factory=list)


@dataclass
class Agent:
    """Person or organization associated with a facility"""
    name: str
    location: Optional[Location] = None
    contact_person: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    languages: List[str] = field(default_factory=list)  # ISO 639 codes
    mailing_list: Optional[str] = None
    images: List[str] = field(default_factory=list)
    contact: Optional[Contact] = field(default_factory=Contact)
    social_media: Optional[SocialMedia] = field(default_factory=SocialMedia)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = {
            "name": self.name
        }
        
        # Add optional fields that are not None
        if self.location:
            result["location"] = self.location.to_dict()
        if self.contact_person:
            result["contact_person"] = self.contact_person
        if self.bio:
            result["bio"] = self.bio
        if self.website:
            result["website"] = self.website
        if self.languages:
            result["languages"] = self.languages
        if self.mailing_list:
            result["mailing_list"] = self.mailing_list
        if self.images:
            result["images"] = self.images
            
        # Add contact info if any field is set
        contact_dict = {k: v for k, v in self.contact.__dict__.items() if v is not None}
        if contact_dict:
            result["contact"] = contact_dict
            
        # Add social media if any field is set
        social_dict = {k: v for k, v in self.social_media.__dict__.items() if v is not None}
        if social_dict:
            result["social_media"] = social_dict
            
        return result


@dataclass
class CircularEconomy:
    """Circular economy related information"""
    applies_principles: bool = False
    description: Optional[str] = None
    by_products: List[str] = field(default_factory=list)


@dataclass
class HumanCapacity:
    """Human capacity information"""
    headcount: Optional[int] = None
    # Maker fields to be added in future version


@dataclass
class InnovationSpace:
    """Innovation space information"""
    staff: Optional[int] = None
    learning_resources: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    footfall: Optional[int] = None
    residencies: bool = False


@dataclass
class Material:
    """Material information"""
    material_type: str  # Wikipedia URL
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    supplier_location: Optional[Location] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = {
            "material_type": self.material_type
        }
        
        if self.manufacturer:
            result["manufacturer"] = self.manufacturer
        if self.brand:
            result["brand"] = self.brand
        if self.supplier_location:
            result["supplier_location"] = self.supplier_location.to_dict()
            
        return result


@dataclass
class Equipment:
    """Manufacturing equipment specification"""
    equipment_type: str  # Wikipedia URL reference
    manufacturing_process: str  # Wikipedia URL reference
    make: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    location: Optional[Location] = None
    condition: Optional[str] = None
    notes: Optional[str] = None
    owner: Optional[Agent] = None
    quantity: Optional[int] = None
    throughput: Optional[str] = None
    power_rating: Optional[int] = None  # Watts
    materials_worked: List[Material] = field(default_factory=list)
    maintenance_schedule: Optional[str] = None
    usage_levels: Optional[str] = None
    tolerance_class: Optional[str] = None  # ISO 2768
    current_firmware: Optional[str] = None
    uninterrupted_power_supply: bool = False
    
    # Common specific properties
    axes: Optional[int] = None
    bed_size: Optional[int] = None  # mm
    build_volume: Optional[int] = None  # mm^3
    computer_controlled: bool = False
    extraction_system: bool = False
    laser_power: Optional[int] = None  # Watts
    nozzle_size: Optional[int] = None  # mm
    working_surface: Optional[int] = None  # mm
    x_travel: Optional[int] = None  # mm
    y_travel: Optional[int] = None  # mm
    z_travel: Optional[int] = None  # mm
    
    # Additional properties can be stored in this dict
    additional_properties: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        # Start with basic properties
        result = {
            "equipment_type": self.equipment_type,
            "manufacturing_process": self.manufacturing_process
        }
        
        # Add optional basic fields
        for field in ["make", "model", "serial_number", "condition", "notes", 
                     "quantity", "throughput", "power_rating", "maintenance_schedule",
                     "usage_levels", "tolerance_class", "current_firmware"]:
            value = getattr(self, field)
            if value is not None:
                result[field] = value
                
        # Add boolean fields
        for field in ["uninterrupted_power_supply", "computer_controlled", 
                     "extraction_system"]:
            value = getattr(self, field)
            if value:
                result[field] = value
                
        # Add complex fields
        if self.location:
            result["location"] = self.location.to_dict()
        if self.owner:
            result["owner"] = self.owner.to_dict()
        if self.materials_worked:
            result["materials_worked"] = [m.to_dict() for m in self.materials_worked]
            
        # Add equipment-specific properties
        for field in ["axes", "bed_size", "build_volume", "laser_power", "nozzle_size",
                     "working_surface", "x_travel", "y_travel", "z_travel"]:
            value = getattr(self, field)
            if value is not None:
                result[field] = value
                
        # Add any additional properties
        result.update(self.additional_properties)
        
        return result


@dataclass
class RecordData:
    """Information about the data record itself"""
    date_created: datetime
    created_by: Agent
    last_updated: Optional[datetime] = None
    updated_by: Optional[Agent] = None
    date_verified: Optional[datetime] = None
    verified_by: Optional[Agent] = None
    data_collection_method: Optional[str] = None


@dataclass
class ManufacturingFacility:
    """Primary OKW Manufacturing Facility class"""
    name: str
    location: Location
    facility_status: FacilityStatus
    id: UUID = field(default_factory=uuid4)
    owner: Optional[Agent] = None
    contact: Optional[Agent] = None
    affiliations: List[Agent] = field(default_factory=list)
    opening_hours: Optional[str] = None
    description: Optional[str] = None
    date_founded: Optional[date] = None
    access_type: AccessType = AccessType.RESTRICTED
    wheelchair_accessibility: Optional[str] = None
    equipment: List[Equipment] = field(default_factory=list)
    manufacturing_processes: List[str] = field(default_factory=list)  # Wikipedia URLs
    typical_batch_size: Optional[BatchSize] = None
    floor_size: Optional[int] = None  # square meters
    storage_capacity: Optional[str] = None
    typical_materials: List[Material] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    backup_generator: Optional[bool] = False
    uninterrupted_power_supply: Optional[bool] = False
    road_access: Optional[bool] = False
    loading_dock: Optional[bool] = False
    maintenance_schedule: Optional[str] = None
    typical_products: List[str] = field(default_factory=list)
    partners_funders: List[Agent] = field(default_factory=list)
    customer_reviews: List[str] = field(default_factory=list)
    
    # Sub-property collections
    circular_economy: CircularEconomy = field(default_factory=CircularEconomy)
    human_capacity: HumanCapacity = field(default_factory=HumanCapacity)
    innovation_space: InnovationSpace = field(default_factory=InnovationSpace)
    
    # Record metadata
    record_data: Optional[RecordData] = None
    
    # Domain metadata
    domain: Optional[str] = None  # "manufacturing" or "cooking"

    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        result = {
            "id": str(self.id),
            "name": self.name,
            "location": self.location.to_dict(),
            "facility_status": self.facility_status.value
        }
        
        # Add optional fields
        if self.owner:
            result["owner"] = self.owner.to_dict()
        if self.contact:
            result["contact"] = self.contact.to_dict()
        if self.affiliations:
            result["affiliations"] = [a.to_dict() for a in self.affiliations]
        if self.opening_hours:
            result["opening_hours"] = self.opening_hours
        if self.description:
            result["description"] = self.description
        if self.date_founded:
            result["date_founded"] = self.date_founded.isoformat()
        
        result["access_type"] = self.access_type.value
        
        if self.wheelchair_accessibility:
            result["wheelchair_accessibility"] = self.wheelchair_accessibility
        # Always include equipment if it exists (even if empty list)
        if self.equipment is not None:
            result["equipment"] = [e.to_dict() for e in self.equipment]
        # Always include manufacturing_processes if it exists (even if empty list)
        if self.manufacturing_processes is not None:
            result["manufacturing_processes"] = self.manufacturing_processes
        if self.typical_batch_size:
            result["typical_batch_size"] = self.typical_batch_size.value
        if self.floor_size:
            result["floor_size"] = self.floor_size
        if self.storage_capacity:
            result["storage_capacity"] = self.storage_capacity
        # Always include typical_materials if it exists (even if empty list)
        if self.typical_materials is not None:
            result["typical_materials"] = [m.to_dict() for m in self.typical_materials]
        # Always include certifications if it exists (even if empty list)
        if self.certifications is not None:
            result["certifications"] = self.certifications
        
        # Boolean properties
        for field in ["backup_generator", "uninterrupted_power_supply", 
                     "road_access", "loading_dock"]:
            if getattr(self, field):
                result[field] = True
                
        if self.maintenance_schedule:
            result["maintenance_schedule"] = self.maintenance_schedule
        if self.typical_products:
            result["typical_products"] = self.typical_products
        if self.partners_funders:
            result["partners_funders"] = [p.to_dict() for p in self.partners_funders]
        if self.customer_reviews:
            result["customer_reviews"] = self.customer_reviews
            
        # Sub-property collections
        # Circular Economy
        ce_dict = {}
        if self.circular_economy.applies_principles:
            ce_dict["applies_principles"] = True
            if self.circular_economy.description:
                ce_dict["description"] = self.circular_economy.description
            if self.circular_economy.by_products:
                ce_dict["by_products"] = self.circular_economy.by_products
                
        if ce_dict:
            result["circular_economy"] = ce_dict
            
        # Human Capacity
        hc_dict = {}
        if self.human_capacity.headcount:
            hc_dict["headcount"] = self.human_capacity.headcount
        
        if hc_dict:
            result["human_capacity"] = hc_dict
            
        # Innovation Space
        is_dict = {}
        if self.innovation_space.staff:
            is_dict["staff"] = self.innovation_space.staff
        if self.innovation_space.learning_resources:
            is_dict["learning_resources"] = self.innovation_space.learning_resources
        if self.innovation_space.services:
            is_dict["services"] = self.innovation_space.services
        if self.innovation_space.footfall:
            is_dict["footfall"] = self.innovation_space.footfall
        if self.innovation_space.residencies:
            is_dict["residencies"] = True
            
        if is_dict:
            result["innovation_space"] = is_dict
            
        # Record data
        if self.record_data:
            record_data_dict = {
                "date_created": self.record_data.date_created.isoformat(),
                "created_by": self.record_data.created_by.to_dict()
            }
            
            if self.record_data.last_updated:
                record_data_dict["last_updated"] = self.record_data.last_updated.isoformat()
            if self.record_data.updated_by:
                record_data_dict["updated_by"] = self.record_data.updated_by.to_dict()
            if self.record_data.date_verified:
                record_data_dict["date_verified"] = self.record_data.date_verified.isoformat()
            if self.record_data.verified_by:
                record_data_dict["verified_by"] = self.record_data.verified_by.to_dict()
            if self.record_data.data_collection_method:
                record_data_dict["data_collection_method"] = self.record_data.data_collection_method
                
            result["record_data"] = record_data_dict
        
        # Domain field
        if self.domain:
            result["domain"] = self.domain
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ManufacturingFacility':
        """Create a ManufacturingFacility instance from a dictionary"""
        # Parse required fields
        name = data.get('name', '')
        
        # Parse location
        location_data = data.get('location', {})
        address_data = location_data.get('address', {})
        address = Address(
            number=address_data.get('number'),
            street=address_data.get('street'),
            district=address_data.get('district'),
            city=address_data.get('city'),
            region=address_data.get('region'),
            country=address_data.get('country'),
            postcode=address_data.get('postcode')
        )
        
        w3w_data = location_data.get('what3words', {})
        what3words = What3Words(
            words=w3w_data.get('words', ''),
            language=w3w_data.get('language', '')
        ) if w3w_data and 'words' in w3w_data else None
        
        location = Location(
            address=address,
            gps_coordinates=location_data.get('gps_coordinates'),
            directions=location_data.get('directions'),
            what3words=what3words,
            city=location_data.get('city'),
            country=location_data.get('country')
        )
        
        # Parse facility status
        facility_status_str = data.get('facility_status', 'Active')
        facility_status = FacilityStatus(facility_status_str)
        
        # Create base facility
        facility = cls(
            name=name,
            location=location,
            facility_status=facility_status
        )
        
        # Parse UUID if provided
        if 'id' in data:
            facility.id = UUID(data['id'])
        
        # Parse optional fields
        if 'opening_hours' in data:
            facility.opening_hours = data['opening_hours']
        if 'description' in data:
            facility.description = data['description']
        if 'date_founded' in data and data['date_founded']:
            facility.date_founded = date.fromisoformat(data['date_founded'])
        if 'access_type' in data:
            facility.access_type = AccessType(data['access_type'])
        if 'wheelchair_accessibility' in data:
            facility.wheelchair_accessibility = data['wheelchair_accessibility']
        if 'manufacturing_processes' in data:
            facility.manufacturing_processes = data['manufacturing_processes']
        if 'typical_batch_size' in data and data['typical_batch_size'] is not None:
            facility.typical_batch_size = BatchSize(data['typical_batch_size'])
        if 'floor_size' in data:
            facility.floor_size = data['floor_size']
        if 'storage_capacity' in data:
            facility.storage_capacity = data['storage_capacity']
        if 'certifications' in data:
            facility.certifications = data['certifications']
        if 'maintenance_schedule' in data:
            facility.maintenance_schedule = data['maintenance_schedule']
        if 'typical_products' in data:
            facility.typical_products = data['typical_products']
        if 'domain' in data:
            facility.domain = data['domain']
        
        # Boolean fields
        facility.backup_generator = data.get('backup_generator', False)
        facility.uninterrupted_power_supply = data.get('uninterrupted_power_supply', False)
        facility.road_access = data.get('road_access', False)
        facility.loading_dock = data.get('loading_dock', False)
        
        # Parse sub-property collections
        # Circular Economy
        ce_data = data.get('circular_economy', {})
        if ce_data:
            facility.circular_economy = CircularEconomy(
                applies_principles=ce_data.get('applies_principles', False),
                description=ce_data.get('description'),
                by_products=ce_data.get('by_products', [])
            )
        
        # Human Capacity
        hc_data = data.get('human_capacity', {})
        if hc_data:
            facility.human_capacity = HumanCapacity(
                headcount=hc_data.get('headcount')
            )
        
        # Innovation Space
        is_data = data.get('innovation_space', {})
        if is_data:
            facility.innovation_space = InnovationSpace(
                staff=is_data.get('staff'),
                learning_resources=is_data.get('learning_resources', []),
                services=is_data.get('services', []),
                footfall=is_data.get('footfall'),
                residencies=is_data.get('residencies', False)
            )
        
        # Parse complex types: owner, contact, affiliations, equipment, materials, etc.
        
        # Parse equipment
        if 'equipment' in data and data['equipment']:
            equipment_list = []
            for eq_data in data['equipment']:
                if isinstance(eq_data, dict):
                    # Parse location for equipment if present
                    eq_location = None
                    if 'location' in eq_data:
                        eq_loc_data = eq_data['location']
                        eq_address_data = eq_loc_data.get('address', {})
                        eq_address = Address(
                            number=eq_address_data.get('number'),
                            street=eq_address_data.get('street'),
                            district=eq_address_data.get('district'),
                            city=eq_address_data.get('city'),
                            region=eq_address_data.get('region'),
                            country=eq_address_data.get('country'),
                            postcode=eq_address_data.get('postcode')
                        )
                        eq_location = Location(
                            address=eq_address,
                            gps_coordinates=eq_loc_data.get('gps_coordinates'),
                            directions=eq_loc_data.get('directions'),
                            city=eq_loc_data.get('city'),
                            country=eq_loc_data.get('country')
                        )
                    
                    # Parse materials worked for equipment if present
                    materials_worked = []
                    if 'materials_worked' in eq_data:
                        for mat_data in eq_data['materials_worked']:
                            if isinstance(mat_data, dict):
                                material = Material(
                                    material_type=mat_data.get('material_type', ''),
                                    manufacturer=mat_data.get('manufacturer'),
                                    brand=mat_data.get('brand')
                                )
                                materials_worked.append(material)
                    
                    equipment = Equipment(
                        equipment_type=eq_data.get('equipment_type', ''),
                        manufacturing_process=eq_data.get('manufacturing_process', ''),
                        make=eq_data.get('make'),
                        model=eq_data.get('model'),
                        serial_number=eq_data.get('serial_number'),
                        location=eq_location,
                        condition=eq_data.get('condition'),
                        notes=eq_data.get('notes'),
                        quantity=eq_data.get('quantity'),
                        throughput=eq_data.get('throughput'),
                        power_rating=eq_data.get('power_rating'),
                        materials_worked=materials_worked,
                        maintenance_schedule=eq_data.get('maintenance_schedule')
                    )
                    equipment_list.append(equipment)
            facility.equipment = equipment_list
        
        # Parse typical materials
        if 'typical_materials' in data and data['typical_materials']:
            materials_list = []
            for mat_data in data['typical_materials']:
                if isinstance(mat_data, dict):
                    # Parse supplier location if present
                    supplier_location = None
                    if 'supplier_location' in mat_data:
                        sup_loc_data = mat_data['supplier_location']
                        sup_address_data = sup_loc_data.get('address', {})
                        sup_address = Address(
                            number=sup_address_data.get('number'),
                            street=sup_address_data.get('street'),
                            district=sup_address_data.get('district'),
                            city=sup_address_data.get('city'),
                            region=sup_address_data.get('region'),
                            country=sup_address_data.get('country'),
                            postcode=sup_address_data.get('postcode')
                        )
                        supplier_location = Location(
                            address=sup_address,
                            gps_coordinates=sup_loc_data.get('gps_coordinates'),
                            directions=sup_loc_data.get('directions'),
                            city=sup_loc_data.get('city'),
                            country=sup_loc_data.get('country')
                        )
                    
                    material = Material(
                        material_type=mat_data.get('material_type', ''),
                        manufacturer=mat_data.get('manufacturer'),
                        brand=mat_data.get('brand'),
                        supplier_location=supplier_location
                    )
                    materials_list.append(material)
            facility.typical_materials = materials_list
        
        # Parse owner and contact (Agent objects)
        if 'owner' in data and data['owner']:
            owner_data = data['owner']
            if isinstance(owner_data, dict):
                facility.owner = Agent(
                    name=owner_data.get('name', ''),
                    contact_person=owner_data.get('contact_person'),
                    bio=owner_data.get('bio'),
                    website=owner_data.get('website'),
                    languages=owner_data.get('languages', []),
                    mailing_list=owner_data.get('mailing_list')
                )
                # Parse contact sub-object if present
                if 'contact' in owner_data and owner_data['contact']:
                    contact_data = owner_data['contact']
                    facility.owner.contact = Contact(
                        landline=contact_data.get('landline'),
                        mobile=contact_data.get('mobile'),
                        fax=contact_data.get('fax'),
                        email=contact_data.get('email'),
                        whatsapp=contact_data.get('whatsapp')
                    )
                # Parse social media if present
                if 'social_media' in owner_data and owner_data['social_media']:
                    sm_data = owner_data['social_media']
                    facility.owner.social_media = SocialMedia(
                        facebook=sm_data.get('facebook'),
                        twitter=sm_data.get('twitter'),
                        instagram=sm_data.get('instagram'),
                        other_urls=sm_data.get('other_urls', [])
                    )
        
        if 'contact' in data and data['contact']:
            contact_data = data['contact']
            if isinstance(contact_data, dict):
                facility.contact = Agent(
                    name=contact_data.get('name', ''),
                    contact_person=contact_data.get('contact_person'),
                    bio=contact_data.get('bio'),
                    website=contact_data.get('website'),
                    languages=contact_data.get('languages', []),
                    mailing_list=contact_data.get('mailing_list')
                )
                # Parse contact sub-object if present
                if 'contact' in contact_data and contact_data['contact']:
                    contact_info_data = contact_data['contact']
                    facility.contact.contact = Contact(
                        landline=contact_info_data.get('landline'),
                        mobile=contact_info_data.get('mobile'),
                        fax=contact_info_data.get('fax'),
                        email=contact_info_data.get('email'),
                        whatsapp=contact_info_data.get('whatsapp')
                    )
                # Parse social media if present
                if 'social_media' in contact_data and contact_data['social_media']:
                    sm_data = contact_data['social_media']
                    facility.contact.social_media = SocialMedia(
                        facebook=sm_data.get('facebook'),
                        twitter=sm_data.get('twitter'),
                        instagram=sm_data.get('instagram'),
                        other_urls=sm_data.get('other_urls', [])
                    )
        
        # Parse affiliations
        if 'affiliations' in data and data['affiliations']:
            affiliations_list = []
            for aff_data in data['affiliations']:
                if isinstance(aff_data, dict):
                    affiliation = Agent(
                        name=aff_data.get('name', ''),
                        contact_person=aff_data.get('contact_person'),
                        bio=aff_data.get('bio'),
                        website=aff_data.get('website'),
                        languages=aff_data.get('languages', []),
                        mailing_list=aff_data.get('mailing_list')
                    )
                    affiliations_list.append(affiliation)
            facility.affiliations = affiliations_list
        
        return facility