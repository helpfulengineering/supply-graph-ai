/**
 * LLM credentials and runtime state (admin).
 *
 * Was a hand-rolled fetch, under a comment saying "until OpenAPI types are
 * regenerated". They were: all five paths are in the committed schema, so this
 * is the typed client now and a backend change to any of them is a compile
 * error rather than a runtime surprise.
 */
import {
  apiClient,
  ApiError,
  errorMessage,
  requestIdFromError,
} from "./client";
import type { components } from "../generated/schema";

export type LLMCredentialStatus = components["schemas"]["LLMCredentialStatus"];
export type ProviderStatus = components["schemas"]["ProviderStatus"];
export type LLMHealth = components["schemas"]["LLMHealthResponse"];
export type LLMProviders = components["schemas"]["LLMProvidersResponse"];

/** `activate` is required by the schema (it has a server-side default, which
 *  openapi-typescript renders as required-in-the-body rather than optional). */
export type LLMCredentialUpsert = components["schemas"]["LLMCredentialUpsert"];

/**
 * Every provider a credential can be stored for.
 *
 * Client-side, and deliberately — GET /api/llm/providers looks like the right
 * source and is not: it lists providers the service has already INSTANTIATED,
 * which on a node with no keys is the empty list. Driving the picker from it
 * would mean a fresh instance offering nothing to configure, and no way to add
 * the first key.
 *
 * Authority is `LLMProvider` in src/config/llm_config.py. Kept in sync by
 * hand, which is worth naming as a cost: the list this replaced had drifted to
 * six of the seven, so `custom` could not be configured from the web app at
 * all. The fix that removes the duplication is a backend one — putting the
 * enum in the /providers response so it reaches the generated schema.
 */
export const LLM_PROVIDERS = [
  "anthropic",
  "openai",
  "azure_openai",
  "aws_bedrock",
  "google",
  "local",
  "custom",
] as const;

function fail(error: unknown, response: Response, fallback: string): never {
  throw new ApiError(
    response.status,
    errorMessage(error, `${fallback} (HTTP ${response.status})`),
    requestIdFromError(error, response),
  );
}

export async function listLLMCredentials(): Promise<LLMCredentialStatus[]> {
  const { data, error, response } = await apiClient.GET("/api/llm/credentials");
  if (error || !response.ok)
    fail(error, response, "Failed to load credentials");
  return data?.credentials ?? [];
}

export async function upsertLLMCredential(
  provider: string,
  payload: LLMCredentialUpsert,
): Promise<LLMCredentialStatus> {
  const { data, error, response } = await apiClient.PUT(
    "/api/llm/credentials/{provider}",
    { params: { path: { provider } }, body: payload },
  );
  if (error || !response.ok || !data)
    fail(error, response, "Failed to save credential");
  return data;
}

/**
 * Make a stored provider the active one, without re-entering its key.
 *
 * The node records the choice, so it survives a restart and is the same answer
 * in every worker — activation used to live only in the process that handled
 * the save.
 */
export async function setActiveLLMProvider(
  provider: string,
): Promise<LLMCredentialStatus> {
  const { data, error, response } = await apiClient.PUT(
    "/api/llm/active/{provider}",
    { params: { path: { provider } } },
  );
  if (error || !response.ok || !data)
    fail(error, response, "Failed to set the active provider");
  return data;
}

export async function deleteLLMCredential(provider: string): Promise<void> {
  const { error, response } = await apiClient.DELETE(
    "/api/llm/credentials/{provider}",
    {
      params: { path: { provider } },
    },
  );
  if (error || !response.ok)
    fail(error, response, "Failed to remove credential");
}

export async function testLLMCredential(provider: string): Promise<void> {
  const { error, response } = await apiClient.POST(
    "/api/llm/credentials/{provider}/test",
    { params: { path: { provider } } },
  );
  if (error || !response.ok) fail(error, response, "Credential test failed");
}

/**
 * Whether generation will work right now.
 *
 * The question a caller actually has when /okh/generate quietly degrades to
 * heuristic extraction — which it does, silently, with no key configured.
 */
export async function fetchLLMHealth(): Promise<LLMHealth> {
  const { data, error, response } = await apiClient.GET("/api/llm/health");
  if (error || !response.ok || !data)
    fail(error, response, "Failed to read LLM health");
  return data;
}

/** Which providers are live, with their models. See LLM_PROVIDERS on why this
 *  reports rather than offers. */
export async function fetchLLMProviders(): Promise<LLMProviders> {
  const { data, error, response } = await apiClient.GET("/api/llm/providers");
  if (error || !response.ok || !data)
    fail(error, response, "Failed to load providers");
  return data;
}
