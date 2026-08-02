/**
 * LLM credential management (admin). Raw fetch until OpenAPI types are regenerated.
 */
import { ApiError, apiBaseUrl, errorMessage, requestIdFromError } from "./client";
import { authHeader } from "../../features/auth/tokenStorage";

export interface LLMCredentialStatus {
  provider: string;
  model?: string | null;
  masked_key: string;
  configured: boolean;
}

export interface LLMCredentialUpsert {
  api_key: string;
  model?: string | null;
  activate?: boolean;
}

async function llmFetch<T>(path: string, init?: RequestInit): Promise<T> {
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
      errorMessage(body, res.statusText),
      requestIdFromError(body, res),
    );
  }
  return body as T;
}

export async function listLLMCredentials(): Promise<LLMCredentialStatus[]> {
  const body = await llmFetch<{ credentials?: LLMCredentialStatus[] }>(
    "/api/llm/credentials",
  );
  return body.credentials ?? [];
}

export async function upsertLLMCredential(
  provider: string,
  payload: LLMCredentialUpsert,
): Promise<LLMCredentialStatus> {
  return llmFetch<LLMCredentialStatus>(`/api/llm/credentials/${provider}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteLLMCredential(provider: string): Promise<void> {
  await llmFetch(`/api/llm/credentials/${provider}`, { method: "DELETE" });
}

export async function testLLMCredential(provider: string): Promise<void> {
  await llmFetch(`/api/llm/credentials/${provider}/test`, { method: "POST" });
}
