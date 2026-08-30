/**
 * The canonical file-type taxonomy — what a file IS, and how to show it.
 *
 * The frontend has carried a regex copy of this since the file browser shipped
 * (`okhFilePath.ts::inferRenderTier`), so a file type the regex has never heard
 * of falls to `download_only` even when the server knows how to render it. This
 * is the authority; the regex stays as the offline fallback.
 *
 * The endpoints used to answer with an untyped `data` payload, so these shapes
 * were declared here and narrowed by hand. Both routes now carry response
 * models (#373), so the types come from codegen and this module no longer
 * guesses — it maps.
 */
import {
  apiClient,
  ApiError,
  errorMessage,
  requestIdFromError,
} from "./client";
import type { components } from "../generated/schema";

export type FileTypeDefinition = components["schemas"]["FileTypeDefinition"];
export type FileTypeTaxonomy = components["schemas"]["FileTypeIndexData"];

function fail(error: unknown, response: Response, fallback: string): never {
  throw new ApiError(
    response.status,
    errorMessage(error, `${fallback} (HTTP ${response.status})`),
    requestIdFromError(error, response),
  );
}

export async function fetchFileTypes(): Promise<FileTypeTaxonomy> {
  const { data, error, response } = await apiClient.GET("/api/file-types");
  if (error || !response.ok || !data)
    fail(error, response, "Failed to load file types");
  return data.data;
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

export type FileTypeValidation =
  components["schemas"]["FileTypeValidationData"];

/** Check the file-types YAML on the server's disk. */
export async function validateFileTypes(): Promise<FileTypeValidation> {
  const { data, error, response } = await apiClient.GET(
    "/api/file-types/validate",
  );
  if (error || !response.ok || !data)
    fail(error, response, "Failed to validate file types");
  return data.data;
}
