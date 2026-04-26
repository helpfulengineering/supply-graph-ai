/** OKH manifest types derived from fixture contract. */

export interface OkhFileRef {
  title: string;
  path: string;
  type: string;
  metadata: Record<string, string>;
}

export interface OkhMaterial {
  material_id: string;
  name: string;
  quantity: number | null;
  unit: string;
  notes: string | null;
}

export interface OkhPart {
  id: string;
  name: string;
  source: string[];
  export: string[];
  auxiliary: string[];
  image: string | null;
  tsdc: string[];
  material: string | null;
  outer_dimensions: { length: number; width: number; height: number } | null;
  mass: number | null;
  manufacturing_params: Record<string, string>;
}

export interface OkhLicense {
  hardware: string | null;
  documentation: string | null;
  software: string | null;
}

export interface OkhLicensor {
  name: string;
  email: string | null;
  affiliation: string | null;
  social: { platform: string; handle: string }[];
}

export interface OkhContributor {
  name: string;
  email: string | null;
  affiliation: string | null;
  social: { platform: string; handle: string }[];
}

export interface OkhManifest {
  id: string;
  title: string;
  version: string | null;
  repo: string | null;
  function: string | null;
  description: string | null;
  intended_use: string | null;
  keywords: string[];
  documentation_language: string | null;
  license: OkhLicense | null;
  licensor: OkhLicensor | null;
  contributors: OkhContributor[];
  manufacturing_processes: string[];
  materials: OkhMaterial[];
  design_files: OkhFileRef[];
  manufacturing_files: OkhFileRef[];
  making_instructions: OkhFileRef[];
  parts: OkhPart[];
  tool_list: string[];
  image: string | null;
  project_link: string | null;
}

export interface OkhListResponse {
  status: string;
  message: string;
  timestamp: string;
  request_id: string;
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
  items: OkhManifest[];
}
