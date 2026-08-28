/**
 * Packages, on the typed client.
 *
 * A second module beside `src/api/package.ts`, which sits on the untyped
 * /v1/api island. The island is not extended — new work goes here, over the
 * generated schema, and the two coexist until the island is migrated on its
 * own.
 */
import { apiClient, ApiError, errorMessage } from "./client";

function fail(error: unknown, response: Response, fallback: string): never {
  throw new ApiError(
    response.status,
    errorMessage(error, `${fallback} (HTTP ${response.status})`),
  );
}

function payload<T>(data: unknown): T {
  return ((data as { data?: unknown } | undefined)?.data ?? data ?? {}) as T;
}

export interface PackageIntegrity {
  valid: boolean;
  errors?: string[];
}

/** Check the package's own contents against its manifest of file hashes. */
export async function verifyPackage(
  org: string,
  project: string,
  version: string,
): Promise<PackageIntegrity> {
  const { data, error, response } = await apiClient.GET(
    "/api/package/{org}/{project}/{version}/verify",
    { params: { path: { org, project, version } } },
  );
  if (error || !response.ok) fail(error, response, "Verification failed");
  const body = payload<Record<string, unknown>>(data);
  return {
    valid: Boolean(body.valid ?? body.verified),
    errors: (body.errors as string[]) ?? [],
  };
}

export interface SignatureVerdict {
  /** Null when no signature record exists — a different answer from invalid. */
  valid: boolean | null;
  signedBy?: string | null;
  message?: string;
}

/**
 * Check the Ed25519 signature over the package's file manifest.
 *
 * Two failures that mean opposite things, and the reason this returns a
 * tri-state rather than a boolean: a 404 means the package was built WITHOUT a
 * federation identity, which is a normal posture and not a fault, while
 * `valid: false` means the manifest has been tampered with. Collapsing them
 * would either alarm people about unsigned packages or hide a real one.
 */
export async function verifyPackageSignature(
  org: string,
  project: string,
  version: string,
): Promise<SignatureVerdict> {
  const { data, error, response } = await apiClient.GET(
    "/api/package/{org}/{project}/{version}/verify-signature",
    { params: { path: { org, project, version } } },
  );
  if (response.status === 404) {
    return {
      valid: null,
      message:
        "This package carries no signature. Build with a federation identity to sign one.",
    };
  }
  if (error || !response.ok) fail(error, response, "Signature check failed");
  const body = payload<Record<string, unknown>>(data);
  return {
    valid: Boolean(body.valid ?? body.verified),
    signedBy: (body.signed_by as string) ?? null,
  };
}

export interface RemotePackage {
  name: string;
  version: string;
  [key: string]: unknown;
}

/** What the configured remote store holds. */
export async function listRemotePackages(): Promise<RemotePackage[]> {
  const { data, error, response } = await apiClient.GET("/api/package/remote");
  if (error || !response.ok)
    fail(error, response, "Could not reach the remote");
  return payload<{ packages?: RemotePackage[] }>(data).packages ?? [];
}

/** Send a locally built package to the remote store. */
export async function pushPackage(
  name: string,
  version: string,
): Promise<void> {
  const { error, response } = await apiClient.POST("/api/package/push", {
    body: { package_name: name, version },
  });
  if (error || !response.ok) fail(error, response, "Push failed");
}

/** Fetch a package from the remote store into this node. */
export async function pullPackage(
  name: string,
  version: string,
): Promise<void> {
  const { error, response } = await apiClient.POST("/api/package/pull", {
    body: { package_name: name, version },
  });
  if (error || !response.ok) fail(error, response, "Pull failed");
}
