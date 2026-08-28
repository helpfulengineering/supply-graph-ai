import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "./client";
import {
  LLM_PROVIDERS,
  fetchLLMHealth,
  fetchLLMProviders,
  listLLMCredentials,
} from "./llm";

describe("LLM_PROVIDERS", () => {
  it("covers every member of the backend enum", () => {
    // src/config/llm_config.py::LLMProvider. The list this replaced had six of
    // the seven, so `custom` could not be configured from the web app at all.
    expect([...LLM_PROVIDERS].sort()).toEqual(
      [
        "anthropic",
        "aws_bedrock",
        "azure_openai",
        "custom",
        "google",
        "local",
        "openai",
      ].sort(),
    );
  });
});

describe("listLLMCredentials", () => {
  it("unwraps the credentials envelope", async () => {
    const credentials = await listLLMCredentials();
    expect(Array.isArray(credentials)).toBe(true);
  });

  it("throws ApiError carrying the status", async () => {
    server.use(
      http.get("*/v1/api/llm/credentials", () =>
        HttpResponse.json({ message: "nope" }, { status: 403 }),
      ),
    );
    await expect(listLLMCredentials()).rejects.toBeInstanceOf(ApiError);
    await expect(listLLMCredentials()).rejects.toMatchObject({ status: 403 });
  });
});

describe("runtime state", () => {
  it("reads the overall health status", async () => {
    const health = await fetchLLMHealth();
    expect(health.health_status).toBe("healthy");
  });

  it("reads the live providers and the default", async () => {
    const providers = await fetchLLMProviders();
    expect(providers.default_provider).toBe("anthropic");
    expect(providers.providers[0].model).toBe("claude-sonnet-4-5-20250929");
  });

  it("surfaces an unconfigured service as an error the panel can soften", async () => {
    // Not a fault: a node with no LLM is a normal deployment, so the panel
    // degrades rather than alarming. That decision needs the throw to happen.
    server.use(
      http.get("*/v1/api/llm/health", () =>
        HttpResponse.json(
          { detail: "LLM service unavailable" },
          { status: 503 },
        ),
      ),
    );
    await expect(fetchLLMHealth()).rejects.toMatchObject({ status: 503 });
  });
});
