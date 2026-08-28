/**
 * The canonical file-type taxonomy — what a file IS, and how to show it.
 *
 * The frontend has carried a regex copy of this since the file browser shipped
 * (`okhFilePath.ts::inferRenderTier`), so a file type the regex has never heard
 * of falls to `download_only` even when the server knows how to render it. This
 * is the authority; the regex stays as the offline fallback.
 *
 * The endpoints answer with `create_success_response`, whose `data` payload the
 * generated schema types as an open record — so the shapes below are declared
 * here rather than imported, and this module is the one place that narrows
 * them.
 */
import {
  apiClient,
  ApiError,
  errorMessage,
  requestIdFromError,
} from "./client";

export interface FileTypeDefinition {
  canonical_id: string;
  display_name: string;
  parent: string | null;
  extensions: string[];
  mime_types: string[];
  okh_role: string | null;
  render_tier: string | null;
}

export interface FileTypeTaxonomy {
  total: number;
  /** Where the server loaded it from — a YAML path, or "built-in". */
  source: string;
  file_types: FileTypeDefinition[];
}

function fail(error: unknown, response: Response, fallback: string): never {
  throw new ApiError(
    response.status,
    errorMessage(error, `${fallback} (HTTP ${response.status})`),
    requestIdFromError(error, response),
  );
}

/** Narrow the success envelope's open `data` record. */
function payload<T>(data: unknown): T {
  return ((data as { data?: unknown } | undefined)?.data ?? {}) as T;
}

export async function fetchFileTypes(): Promise<FileTypeTaxonomy> {
  const { data, error, response } = await apiClient.GET("/api/file-types");
  if (error || !response.ok) fail(error, response, "Failed to load file types");
  const body = payload<Partial<FileTypeTaxonomy>>(data);
  return {
    total: body.total ?? 0,
    source: body.source ?? "built-in",
    file_types: body.file_types ?? [],
  };
}

/** extension (no dot, lowercased) -> definition. */
export function fileTypesByExtension(
  taxonomy: FileTypeTaxonomy,
): Map<string, FileTypeDefinition> {
  const index = new Map<string, FileTypeDefinition>();
  for (const definition of taxonomy.file_types) {
    for (const extension of definition.extensions) {
      index.set(extension.replace(/^\./, "").toLowerCase(), definition);
    }
  }
  return index;
}

export interface FileTypeValidation {
  valid: boolean;
  total_file_types: number;
  errors: string[];
  source: string;
}

/** Check the file-types YAML on the server's disk. */
export async function validateFileTypes(): Promise<FileTypeValidation> {
  const { data, error, response } = await apiClient.GET(
    "/api/file-types/validate",
  );
  if (error || !response.ok)
    fail(error, response, "Failed to validate file types");
  const body = payload<Partial<FileTypeValidation>>(data);
  return {
    valid: body.valid ?? false,
    total_file_types: body.total_file_types ?? 0,
    errors: body.errors ?? [],
    source: body.source ?? "",
  };
}
