/**
 * Collection interchange: a whole catalogue as one archive.
 *
 * Separate from okh.ts because these trade zip bytes and FormData rather than
 * JSON, and mixing binary helpers into the record client muddies both.
 *
 * The order these are meant to be used in is the point: export produces an
 * archive another node can read, diff says what importing one would do, and
 * import writes. The middle step is what makes the last one safe.
 */
import { apiBaseUrl, apiClient, ApiError, errorMessage } from "./client";
import { authHeader } from "../../features/auth/tokenStorage";

/** What an archive holds that this node does not, and vice versa. */
export interface CollectionDiff {
  only_in_archive: string[];
  only_local: string[];
}

export interface CollectionImportReport {
  dry_run: boolean;
  new: string[];
  duplicate: string[];
  conflict: string[];
  imported: number;
}

/**
 * Download every stored manifest as a zip.
 *
 * A raw fetch rather than the typed client: the response is an archive, and
 * `apiBaseUrl` is exported for exactly this — an endpoint whose body is bytes
 * has nothing for the generated types to check.
 */
export async function exportCollection(): Promise<Blob> {
  const response = await fetch(`${apiBaseUrl}/api/okh/export-collection`, {
    headers: { ...authHeader() },
  });
  if (!response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = undefined;
    }
    throw new ApiError(
      response.status,
      errorMessage(body, `Export failed (HTTP ${response.status})`),
    );
  }
  return response.blob();
}

async function postArchive<T>(
  path: "/api/okh/diff-collection" | "/api/okh/import-collection",
  file: File,
  fallback: string,
  query?: Record<string, boolean>,
): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const { data, error, response } = await apiClient.POST(path, {
    params: query ? { query } : undefined,
    body: form as unknown as never,
    // Untouched, so the browser's multipart boundary survives.
    bodySerializer: (body: unknown) => body as BodyInit,
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      // The backend's own suggestion for a malformed archive names the command
      // that produces a valid one, which is more use than "invalid file".
      errorMessage(error, `${fallback} (HTTP ${response.status})`),
    );
  }
  return data as T;
}

/** What importing this archive would change. Writes nothing. */
export function diffCollection(file: File): Promise<CollectionDiff> {
  return postArchive<CollectionDiff>(
    "/api/okh/diff-collection",
    file,
    "Could not read that archive",
  );
}

/** Import an archive. `dryRun` reports without writing. */
export function importCollection(
  file: File,
  dryRun = false,
): Promise<CollectionImportReport> {
  return postArchive<CollectionImportReport>(
    "/api/okh/import-collection",
    file,
    "Import failed",
    { dry_run: dryRun },
  );
}
