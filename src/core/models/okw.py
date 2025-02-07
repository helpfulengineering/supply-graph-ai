from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union
from datetime import date, datetime
from enum import Enum
from uuid import UUID


class FacilityStatus(Enum):
    """Status of manufacturing facility"""
    ACTIVE = "Active"
    PLANNED = "Planned" 
    TEMPORARY_CLOSURE = "Temporary Closure"
    CLOSED = "Closed"


class AccessType(Enum):
    """How manufacturing equipment is accessed"""
    RESTRICTED = "Restricted"  # Only certain people can use equipment
    RESTRICTED_PUBLIC = "Restricted with public hours"  # Public can use during limited hours
    SHARED = "Shared space"  # Shared workspace with qualifying criteria
    PUBLIC = "Public"  # Anyone may use equipment (training may be required)
    MEMBERSHIP = "Membership"  # Access requires membership


class BatchSize(Enum):
    """Typical batch size ranges"""
    SMALL = "0 -- 50 units"
    MEDIUM = "50 -- 500 units"
    LARGE = "500 -- 5000 units"
    XLARGE = "5000 + units"


@dataclass
class Location:
    """Location information with multiple addressing options"""
    address: Optional[Dict[str, str]] = field(default_factory=dict)  # number, street, district, etc.
    gps_coordinates: Optional[str] = None  # Decimal degrees format
    directions: Optional[str] = None  # Qualitative directions
    what3words: Optional[Dict[str, str]] = field(default_factory=dict)  # phrase and language
    city: Optional[str] = None
    country: Optional[str] = None


@dataclass 
class Contact:
    """Contact information for a facility or person"""
    landline: Optional[str] = None
    mobile: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None


@dataclass
class SocialMedia:
    """Social media presence information"""
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
    languages: List[str] = field(default_factory=list)  # ISO 639-2/639-3 codes
    mailing_list: Optional[str] = None
    images: List[str] = field(default_factory=list)
    contact: Optional[Contact] = None
    social_media: Optional[SocialMedia] = None


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
    materials_worked: List[str] = field(default_factory=list)
    maintenance_schedule: Optional[str] = None
    usage_levels: Optional[str] = None
    tolerance_class: Optional[str] = None  # ISO 2768
    current_firmware: Optional[str] = None
    uninterrupted_power: bool = False
    
    # Equipment-specific properties
    axes: Optional[int] = None
    bed_size: Optional[int] = None  # mm
    build_volume: Optional[int] = None  # mm^3
    layer_resolution: Optional[float] = None  # mm
    nozzle_size: Optional[float] = None  # mm
    max_spindle_speed: Optional[int] = None  # RPM
    computer_controlled: bool = False


@dataclass
class CircularEconomy:
    """Circular economy related information"""
    applies_principles: bool = False
    description: Optional[str] = None
    by_products: List[str] = field(default_factory=list)


@dataclass
class HumanCapacity:
    """Human capacity information"""
    headcount: Optional[int] = None  # Full-time equivalent
    makers: List[str] = field(default_factory=list)


@dataclass
class InnovationSpace:
    """Innovation and educational aspects"""
    staff_count: Optional[int] = None
    learning_resources: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    footfall: Optional[int] = None
    residencies_available: bool = False


@dataclass
class ManufacturingFacility:
    """Primary OKW Manufacturing Facility class"""
    # Required base fields
    name: str
    location: Location
    facility_status: FacilityStatus
    
    # Contact and ownership
    owner: Optional[Agent] = None
    contact: Optional[Agent] = None
    affiliations: List[Agent] = field(default_factory=list)
    
    # Basic information
    opening_hours: Optional[str] = None
    description: Optional[str] = None
    date_founded: Optional[date] = None
    access_type: Optional[AccessType] = None
    wheelchair_accessible: Optional[str] = None
    
    # Capabilities
    equipment: List[Equipment] = field(default_factory=list)
    manufacturing_processes: List[str] = field(default_factory=list)  # Wikipedia URLs
    typical_batch_size: Optional[BatchSize] = None
    size_floor_size: Optional[int] = None  # square meters
    storage_capacity: Optional[str] = None
    typical_materials: List[str] = field(default_factory=list)  # Wikipedia URLs
    certifications: List[str] = field(default_factory=list)
    
    # Infrastructure
    backup_generator: bool = False
    uninterrupted_power: bool = False
    road_access: bool = False
    loading_dock: bool = False
    
    # Operations
    maintenance_schedule: Optional[str] = None
    typical_products: List[str] = field(default_factory=list)
    partners_funders: List[Agent] = field(default_factory=list)
    customer_reviews: List[str] = field(default_factory=list)
    
    # Extended properties
    circular_economy: Optional[CircularEconomy] = None
    human_capacity: Optional[HumanCapacity] = None
    innovation_space: Optional[InnovationSpace] = None

    def validate(self) -> bool:
        """
        Validate that all required fields are present and properly formatted.
        Returns True if valid, raises ValidationError if invalid.
        """
        required_fields = [
            self.name,
            self.location,
            self.facility_status
        ]
        
        if not all(required_fields):
            missing = [
                field for field, value in zip(
                    ["name", "location", "facility_status"],
                    required_fields
                ) if not value
            ]
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
            
        return True
    
    def to_dict(self) -> Dict:
        """Convert the facility data to a dictionary format"""
        # Implementation would go here
        pass
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ManufacturingFacility':
        """Create a ManufacturingFacility instance from a dictionary"""
        # Implementation would go here
        pass


@dataclass
class RecordData:
    """Metadata about the OKW record itself"""
    date_created: datetime
    created_by: Agent
    last_updated: Optional[datetime] = None
    updated_by: Optional[Agent] = None
    date_verified: Optional[datetime] = None
    verified_by: Optional[Agent] = None
    data_collection_method: Optional[str] = None


# Example usage:
# if __name__ == "__main__":
#     # Create a basic manufacturing facility
#     location = Location(
#         address={
#             "street": "123 Maker Street",
#             "city": "Makerville",
#             "country": "Makerland"
#         },
#         gps_coordinates="51.5074° N, 0.1278° W"
#     )
    
#     owner = Agent(
#         name="Maker Space Inc",
#         contact=Contact(
#             email="info@makerspace.com",
#             mobile="+1234567890"
#         )
#     )
    
#     facility = ManufacturingFacility(
#         name="Community Maker Space",
#         location=location,
#         facility_status=FacilityStatus.ACTIVE,
#         owner=owner,
#         access_type=AccessType.MEMBERSHIP,
#         description="A community makerspace focused on 3D printing and CNC machining"
#     )
    
#     # Validate the facility data
#     try:
#         facility.validate()
#         print("Facility data is valid!")
#     except ValueError as e:
#         print(f"Facility validation failed: {e}")
