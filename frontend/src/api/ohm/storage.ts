/**
 * Storage configuration (admin).
 *
 * The interface to #377's endpoints: read what this instance is running on,
 * and point it somewhere else. Storage is the setting a freshly installed
 * instance most needs to change — the installer starts it on local storage,
 * and this is how it gets pointed at real storage afterwards.
 */
import {
  apiClient,
  ApiError,
  errorMessage,
  requestIdFromError,
} from "./client";
import type { components } from "../generated/schema";

export type StorageConfigData = components["schemas"]["StorageConfigData"];
export type StorageFingerprint = components["schemas"]["StorageFingerprint"];
export type StorageConfigView = components["schemas"]["StorageConfigView"];
export type StorageConfigureData =
  components["schemas"]["StorageConfigureData"];
export type StorageConfigureRequest =
  components["schemas"]["StorageConfigureRequest"];

/**
 * Providers, and the credential fields each one takes.
 *
 * Client-side, mirroring `PROVIDER_CREDENTIALS` in
 * `src/core/services/storage_reconfigure.py`. The server rejects an
 * unrecognised credential name rather than dropping it, so a drift here shows
 * up as a clear error from the API rather than a silent misconfiguration —
 * but it is still duplication, and the fix that removes it is a backend one:
 * putting the map in a response so it reaches the generated schema.
 */
export const STORAGE_PROVIDERS = {
  local: [],
  gcs: ["project_id", "credentials_path", "credentials_json"],
  azure_blob: ["account_name", "account_key", "connection_string"],
  aws_s3: ["access_key_id", "secret_access_key", "session_token"],
} as const;

export type StorageProvider = keyof typeof STORAGE_PROVIDERS;

export const STORAGE_PROVIDER_LABELS: Record<StorageProvider, string> = {
  local: "Local filesystem",
  gcs: "Google Cloud Storage",
  azure_blob: "Azure Blob Storage",
  aws_s3: "Amazon S3",
};

function fail(error: unknown, response: Response, fallback: string): never {
  throw new ApiError(
    response.status,
    errorMessage(error, `${fallback} (HTTP ${response.status})`),
    requestIdFromError(error, response),
  );
}

/** What this instance is configured with, and what it is actually reaching. */
export async function fetchStorageConfig(): Promise<StorageConfigView> {
  const { data, error, response } = await apiClient.GET("/api/storage/config");
  if (error || !response.ok || !data?.data)
    fail(error, response, "Failed to read storage configuration");
  return data.data;
}

/**
 * Switch backends. Validated end to end before it takes effect.
 *
 * A rejected configuration leaves the instance serving exactly as it was, and
 * the server says so in its error — which this deliberately does not reword.
 * The reassurance that nothing has broken is the most useful part of the
 * message, and it belongs to whichever layer actually knows it is true.
 */
export async function configureStorage(
  body: StorageConfigureRequest,
): Promise<StorageConfigureData> {
  const { data, error, response } = await apiClient.POST(
    "/api/storage/config",
    { body },
  );
  if (error || !response.ok || !data?.data)
    fail(error, response, "Failed to change storage configuration");
  return data.data;
}
