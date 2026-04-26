/**
 * Shared API envelope types. All OHM API responses wrap their payload in this
 * standard structure.
 */

export interface ApiEnvelope<T> {
  status: "success" | "error";
  message: string;
  timestamp: string;
  request_id: string;
  data: T | null;
  metadata: Record<string, unknown>;
}

export interface PaginatedEnvelope<T> extends ApiEnvelope<null> {
  pagination: Pagination;
  items: T[];
}

export interface Pagination {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}
