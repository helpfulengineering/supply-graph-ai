/** Package types derived from fixture contract and package API. */

export interface PackageListItem {
  package_name: string;
  version: string;
  okh_manifest_id: string | null;
  build_timestamp: string;
  total_files: number;
  total_size_bytes: number;
  build_options: Record<string, unknown>;
  package_path: string;
}

export interface PackageListResponse {
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
  items: PackageListItem[];
}

export interface PackageBuildMetadata {
  package_name: string;
  version: string;
  okh_manifest_id?: string | null;
  build_timestamp?: string;
  total_files?: number;
  total_size_bytes?: number;
  package_path?: string;
}

export interface PackageBuildResponse {
  status: string;
  message: string;
  timestamp: string;
  data: {
    metadata: PackageBuildMetadata;
  };
}
