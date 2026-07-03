/** OKW facility view types (subset of the facility payload the catalog renders). */

export interface OkwAddress {
  city?: string | null;
  region?: string | null;
  country?: string | null;
}

export interface OkwLocation {
  address?: OkwAddress | null;
  city?: string | null;
  country?: string | null;
}

export interface OkwEquipment {
  equipment_type?: string | null;
  make?: string | null;
  model?: string | null;
}

export interface OkwFacility {
  id: string;
  name: string;
  location: OkwLocation | null;
  manufacturing_processes: string[];
  access_type: string | null;
  facility_status: string | null;
  description: string | null;
  equipment?: OkwEquipment[];
  certifications?: string[];
}
