/**
 * Identity API wrappers (Track F — F0/F1).
 * Prefer typed openapi-fetch where the path exists in schema.d.ts;
 * security-policy is untyped in OpenAPI today (Dict response).
 */
import { apiClient, ApiError, apiBaseUrl, errorMessage, requestIdFromError } from "./client";
import { authHeader } from "../../features/auth/tokenStorage";
import type { components } from "../generated/schema";

export type AuthenticatedUser = components["schemas"]["AuthenticatedUser"];
export type APIKeyResponse = components["schemas"]["APIKeyResponse"];
export type APIKeyCreate = components["schemas"]["APIKeyCreate"];
export type Account = components["schemas"]["Account"];
export type AccountCreate = components["schemas"]["AccountCreate"];

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
  const res = await fetch(`${apiBaseUrl}/api/identity/security-policy`, {
    headers: { Accept: "application/json", ...authHeader() },
  });
  if (!res.ok) {
    throw new ApiError(res.status, `Failed to load security policy (${res.status})`);
  }
  return res.json() as Promise<SecurityPolicyPublic>;
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
