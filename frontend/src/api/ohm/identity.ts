/**
 * Identity API wrappers (Track F — F0/F1/F3).
 *
 * Every type here is generated from the API schema. The hand-written copies
 * that used to live in this file were not merely duplication: each one had
 * drifted, marking fields optional that the server always sends, so the UI was
 * defensively null-checking values that cannot be null.
 *
 * The wrappers below still split between typed `apiClient` and raw
 * `identityFetch`. That split no longer tracks anything real — every identity
 * path is in schema.d.ts now — so the remaining `identityFetch` callers are a
 * migration waiting to happen, not a category. Left alone here because
 * swapping transports changes error handling, which is a change with its own
 * tests to write.
 */
import {
  apiClient,
  ApiError,
  apiBaseUrl,
  errorMessage,
  requestIdFromError,
} from "./client";
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

/**
 * The node's identity/trust posture.
 *
 * Generated from the API schema now that the route declares a response model
 * (#373). It used to be hand-written, which meant a knob added on the server
 * reached the UI only if someone remembered to restate it here — and three of
 * them (open_registration, admin_break_glass, key_ttl_days) were added by hand
 * in exactly that way over the last few changes.
 */
export type SecurityPolicyPublic =
  components["schemas"]["SecurityPolicyResponse"];

/** A node's claim on its own space DID. */
export type SpaceClaim = components["schemas"]["SpaceClaim"];

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
  const { data, error, response } = await apiClient.GET(
    "/api/identity/security-policy",
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to load security policy"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export type RegistrationCreate = components["schemas"]["RegistrationCreate"];
export type RegistrationResponse =
  components["schemas"]["RegistrationResponse"];

/**
 * Register a person on this node. Deliberately unauthenticated: a node operator
 * should not be the only way to become someone on a node.
 *
 * The token in the response is the only copy that will ever exist.
 */
export async function registerPerson(
  displayName: string,
): Promise<RegistrationResponse> {
  const { data, error, response } = await apiClient.POST(
    "/api/identity/register",
    { body: { display_name: displayName } },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Registration failed"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

/**
 * Trade a recovery code for a working key on the same account and DID.
 *
 * Unauthenticated by necessity: the credential this returns is the one the
 * caller lost. Redeeming revokes the account's other keys and issues a
 * replacement code, so the response carries both values, once.
 */
export async function redeemRecoveryCode(
  code: string,
): Promise<RegistrationResponse> {
  const { data, error, response } = await apiClient.POST(
    "/api/identity/recover",
    { body: { code } },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "That recovery code is not valid"),
      requestIdFromError(error, response),
    );
  }
  return data;
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

export async function createApiKey(
  body: APIKeyCreate,
): Promise<APIKeyResponse> {
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

export async function revokeOtherApiKeys(): Promise<string> {
  const { data, error, response } = await apiClient.POST(
    "/api/identity/keys/revoke-others",
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to revoke other keys"),
      requestIdFromError(error, response),
    );
  }
  return data.message ?? "Done";
}

export async function renewApiKey(keyId: string): Promise<APIKeyResponse> {
  const { data, error, response } = await apiClient.POST(
    "/api/identity/keys/{key_id}/renew",
    { params: { path: { key_id: keyId } } },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to renew key"),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function revokeApiKey(keyId: string): Promise<void> {
  const { error, response } = await apiClient.DELETE(
    "/api/identity/keys/{key_id}",
    {
      params: { path: { key_id: keyId } },
    },
  );
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to revoke API key"),
      requestIdFromError(error, response),
    );
  }
}

export async function listAccounts(): Promise<Account[]> {
  const { data, error, response } = await apiClient.GET(
    "/api/identity/accounts",
  );
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
  const { data, error, response } = await apiClient.POST(
    "/api/identity/accounts",
    {
      body,
    },
  );
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
  const { data, error, response } = await apiClient.POST(
    "/api/identity/identities",
    {
      body,
    },
  );
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
  const { data, error, response } = await apiClient.GET(
    "/api/identity/identities/{did}",
    {
      params: { path: { did } },
    },
  );
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

export async function listGrants(
  subjectDid: string,
): Promise<CapabilityGrant[]> {
  const { data, error, response } = await apiClient.GET(
    "/api/identity/grants",
    {
      params: { query: { subject_did: subjectDid } },
    },
  );
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
  const { data, error, response } = await apiClient.POST(
    "/api/identity/grants",
    {
      body,
    },
  );
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
  const { error, response } = await apiClient.DELETE(
    "/api/identity/grants/{grant_id}",
    {
      params: { path: { grant_id: grantId } },
    },
  );
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, "Failed to revoke grant"),
      requestIdFromError(error, response),
    );
  }
}

export async function bootstrapEdgeGrant(
  subjectDid: string,
): Promise<CapabilityGrant> {
  const q = new URLSearchParams({ subject_did: subjectDid });
  return identityFetch<CapabilityGrant>(
    `/api/identity/grants/bootstrap-edge?${q}`,
    {
      method: "POST",
    },
  );
}

export async function listSpaceClaims(): Promise<SpaceClaim[]> {
  return identityFetch<SpaceClaim[]>("/api/identity/spaces");
}

export async function claimSpace(
  spaceDid: string,
  adminDid: string,
): Promise<SpaceClaim> {
  return identityFetch<SpaceClaim>("/api/identity/spaces/claim", {
    method: "POST",
    body: JSON.stringify({ space_did: spaceDid, admin_did: adminDid }),
  });
}

/** A durable, signed claim one DID makes about another. */
export type Attestation = components["schemas"]["Attestation"];

/** Body for certifying a release. */
export type CertifyRequest = components["schemas"]["CertifyRequest"];

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

export async function certifyRelease(
  body: CertifyRequest,
): Promise<Attestation> {
  return identityFetch<Attestation>("/api/identity/attestations/certify", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listReputation(
  subjectDid: string,
): Promise<Attestation[]> {
  return identityFetch<Attestation[]>(
    `/api/identity/reputation/${encodeURIComponent(subjectDid)}`,
  );
}

/** A DID bound to an external identifier (domain / oauth). */
export type IdentityBinding = components["schemas"]["IdentityBinding"];

/** Challenge to publish at .well-known to prove a domain. */
export type DomainBindStartResponse =
  components["schemas"]["DomainBindStartResponse"];

/** A DID as it appears in the node's public directory. */
export type DirectoryEntry = components["schemas"]["DirectoryEntry"];

export async function startDomainBinding(
  subjectDid: string,
  domain: string,
): Promise<DomainBindStartResponse> {
  return identityFetch<DomainBindStartResponse>(
    "/api/identity/bindings/domain",
    {
      method: "POST",
      body: JSON.stringify({ subject_did: subjectDid, domain }),
    },
  );
}

export async function verifyDomainBinding(
  subjectDid: string,
  domain: string,
): Promise<IdentityBinding> {
  return identityFetch<IdentityBinding>(
    "/api/identity/bindings/domain/verify",
    {
      method: "POST",
      body: JSON.stringify({ subject_did: subjectDid, domain }),
    },
  );
}

export async function bindOAuth(body: {
  subject_did: string;
  provider: string;
  external_subject: string;
}): Promise<IdentityBinding> {
  return identityFetch<IdentityBinding>("/api/identity/bindings/oauth", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listBindings(
  subjectDid?: string,
): Promise<IdentityBinding[]> {
  const q = subjectDid
    ? `?${new URLSearchParams({ subject_did: subjectDid })}`
    : "";
  return identityFetch<IdentityBinding[]>(`/api/identity/bindings${q}`);
}

export async function listDirectory(): Promise<DirectoryEntry[]> {
  return identityFetch<DirectoryEntry[]>("/api/identity/directory");
}

export async function publishDirectoryEntry(body: {
  did: string;
  display_name?: string;
  base_url?: string | null;
  domain?: string | null;
}): Promise<DirectoryEntry> {
  return identityFetch<DirectoryEntry>("/api/identity/directory", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
