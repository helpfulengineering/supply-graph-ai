/**
 * Identity API wrappers (Track F — F0/F1/F3).
 * Prefer typed openapi-fetch where the path exists in schema.d.ts;
 * security-policy, spaces, and bootstrap-edge use raw fetch until regenerated.
 */
import { apiClient, ApiError, apiBaseUrl, errorMessage, requestIdFromError } from "./client";
import { authHeader } from "../../features/auth/tokenStorage";
import type { components } from "../generated/schema";

export type AuthenticatedUser = components["schemas"]["AuthenticatedUser"];
export type APIKeyResponse = components["schemas"]["APIKeyResponse"];
export type APIKeyCreate = components["schemas"]["APIKeyCreate"];
export type Account = components["schemas"]["Account"];
export type AccountCreate = components["schemas"]["AccountCreate"];
export type Identity = components["schemas"]["Identity"];
export type IdentityMint = components["schemas"]["IdentityMint"];
export type CapabilityGrant = components["schemas"]["CapabilityGrant"];
export type GrantIssue = components["schemas"]["GrantIssue"];

export interface SecurityPolicyPublic {
  mode: string;
  require_auth_for_writes: boolean;
  custodial_keys_allowed: boolean;
  grant_ttl_days: number;
  recovery: string;
  trust_bootstrap: string;
  mdns_advertise: boolean;
  metadata_logging: string;
  registry_attestations: string;
  anonymous_submission_allowed: boolean;
}

/** Space claim (not yet in committed OpenAPI). */
export interface SpaceClaim {
  space_did: string;
  admin_did: string;
  claimed_at?: string;
  claim_method?: string;
  signature?: string;
}

async function identityFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...authHeader(),
      ...(init?.headers ?? {}),
    },
  });
  let body: unknown;
  try {
    body = await res.json();
  } catch {
    body = undefined;
  }
  if (!res.ok) {
    throw new ApiError(
      res.status,
      errorMessage(body, `Request failed (${res.status})`),
      requestIdFromError(body, res),
    );
  }
  return body as T;
}

export async function fetchWhoami(): Promise<AuthenticatedUser> {
  const { data, error, response } = await apiClient.GET("/api/identity/whoami");
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to load identity"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function fetchSecurityPolicy(): Promise<SecurityPolicyPublic> {
  return identityFetch<SecurityPolicyPublic>("/api/identity/security-policy");
}

export async function listApiKeys(): Promise<APIKeyResponse[]> {
  const { data, error, response } = await apiClient.GET("/api/identity/keys");
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to list API keys"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function createApiKey(body: APIKeyCreate): Promise<APIKeyResponse> {
  const { data, error, response } = await apiClient.POST("/api/identity/keys", {
    body,
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to create API key"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function revokeApiKey(keyId: string): Promise<void> {
  const { error, response } = await apiClient.DELETE("/api/identity/keys/{key_id}", {
    params: { path: { key_id: keyId } },
  });
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to revoke API key"),
      requestIdFromError(error, response),
    );
  }
}

export async function listAccounts(): Promise<Account[]> {
  const { data, error, response } = await apiClient.GET("/api/identity/accounts");
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to list accounts"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function createAccount(body: AccountCreate): Promise<Account> {
  const { data, error, response } = await apiClient.POST("/api/identity/accounts", {
    body,
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to create account"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function disableAccount(accountId: string): Promise<void> {
  const { error, response } = await apiClient.POST(
    "/api/identity/accounts/{account_id}/disable",
    { params: { path: { account_id: accountId } } },
  );
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to disable account"),
      requestIdFromError(error, response),
    );
  }
}

export async function mintIdentity(body: IdentityMint): Promise<Identity> {
  const { data, error, response } = await apiClient.POST("/api/identity/identities", {
    body,
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to mint identity"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function getIdentity(did: string): Promise<Identity> {
  const { data, error, response } = await apiClient.GET("/api/identity/identities/{did}", {
    params: { path: { did } },
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to load identity"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function rotateIdentity(did: string): Promise<Identity> {
  const { data, error, response } = await apiClient.POST(
    "/api/identity/identities/{did}/rotate",
    { params: { path: { did } } },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to rotate identity"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function listGrants(subjectDid: string): Promise<CapabilityGrant[]> {
  const { data, error, response } = await apiClient.GET("/api/identity/grants", {
    params: { query: { subject_did: subjectDid } },
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to list grants"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function issueGrant(body: GrantIssue): Promise<CapabilityGrant> {
  const { data, error, response } = await apiClient.POST("/api/identity/grants", {
    body,
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to issue grant"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function revokeGrant(grantId: string): Promise<void> {
  const { error, response } = await apiClient.DELETE("/api/identity/grants/{grant_id}", {
    params: { path: { grant_id: grantId } },
  });
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to revoke grant"),
      requestIdFromError(error, response),
    );
  }
}

export async function bootstrapEdgeGrant(subjectDid: string): Promise<CapabilityGrant> {
  const q = new URLSearchParams({ subject_did: subjectDid });
  return identityFetch<CapabilityGrant>(`/api/identity/grants/bootstrap-edge?${q}`, {
    method: "POST",
  });
}

export async function listSpaceClaims(): Promise<SpaceClaim[]> {
  return identityFetch<SpaceClaim[]>("/api/identity/spaces");
}

export async function claimSpace(spaceDid: string, adminDid: string): Promise<SpaceClaim> {
  return identityFetch<SpaceClaim>("/api/identity/spaces/claim", {
    method: "POST",
    body: JSON.stringify({ space_did: spaceDid, admin_did: adminDid }),
  });
}

/** Durable attestation (not yet in committed OpenAPI). */
export interface Attestation {
  attestation_id: string;
  type: string;
  issuer_did: string;
  subject_did: string;
  content_hash?: string | null;
  claim?: Record<string, unknown>;
  created_at?: string;
  expires_at?: string | null;
  signature?: string;
}

export interface CertifyRequest {
  subject_did: string;
  bundle_hash: string;
  version: string;
  issuer_did?: string | null;
  manifest_content_hash?: string | null;
  claim?: Record<string, unknown>;
}

export async function listAttestations(opts: {
  subject_did?: string;
  content_hash?: string;
}): Promise<Attestation[]> {
  const q = new URLSearchParams();
  if (opts.subject_did) q.set("subject_did", opts.subject_did);
  if (opts.content_hash) q.set("content_hash", opts.content_hash);
  const qs = q.toString();
  return identityFetch<Attestation[]>(
    `/api/identity/attestations${qs ? `?${qs}` : ""}`,
  );
}

export async function certifyRelease(body: CertifyRequest): Promise<Attestation> {
  return identityFetch<Attestation>("/api/identity/attestations/certify", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listReputation(subjectDid: string): Promise<Attestation[]> {
  return identityFetch<Attestation[]>(
    `/api/identity/reputation/${encodeURIComponent(subjectDid)}`,
  );
}
