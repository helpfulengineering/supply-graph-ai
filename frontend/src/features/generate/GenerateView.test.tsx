import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { ApiError } from "../../api/ohm/client";
import { AuthProvider } from "../../context/AuthContext";
import { GenerateView, generationErrorMessage } from "./GenerateView";

function renderView() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <GenerateView />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("generationErrorMessage", () => {
  it("explains a 404 without blaming the user", () => {
    const msg = generationErrorMessage(new ApiError(404, "Not Found"));
    expect(msg).toContain("private");
    expect(msg).toContain("public repositories");
  });

  it("translates 429 into the shared-quota situation, not a status code", () => {
    const msg = generationErrorMessage(new ApiError(429, "Too Many Requests"));
    expect(msg).toContain("rate limit");
    expect(msg).not.toContain("429");
  });

  it("passes through the server's explanation on 422", () => {
    const msg = generationErrorMessage(
      new ApiError(422, "no manifest-like files found"),
    );
    expect(msg).toContain("no manifest-like files found");
  });

  it("keeps 5xx generic rather than leaking internals", () => {
    const msg = generationErrorMessage(
      new ApiError(500, "Traceback: KeyError foo"),
    );
    expect(msg).not.toContain("Traceback");
    expect(msg).toContain("Please try again");
  });

  it("names jobs unavailable on 503", () => {
    expect(generationErrorMessage(new ApiError(503, "disabled"))).toContain(
      "Background generation",
    );
  });

  it("falls back to the message for other 4xx", () => {
    expect(generationErrorMessage(new ApiError(400, "bad url"))).toBe(
      "bad url",
    );
  });

  it("handles a non-Error throw", () => {
    expect(generationErrorMessage("boom")).toBe("Generation failed.");
  });
});

describe("GenerateView — LLM generation without an account (#561)", () => {
  const RAW =
    "LLM-enabled generation requires authentication. Pass Authorization: Bearer <token>, or set no_llm=true.";

  function refuseLlm(bodies: Record<string, unknown>[]) {
    server.use(
      http.post("*/v1/api/okh/generate-from-url/jobs", async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        bodies.push(body);
        return body.no_llm
          ? HttpResponse.json(
              { batch_id: "b", jobs: [{ job_id: "j", url: "u" }] },
              { status: 202 },
            )
          : HttpResponse.json({ detail: RAW }, { status: 401 });
      }),
    );
  }

  async function generate() {
    await userEvent.type(
      screen.getByLabelText(/Repository URL/i),
      "https://github.com/mitra42/frugal-iot-hw-sensor",
    );
    await userEvent.click(screen.getByRole("button", { name: "Generate" }));
  }

  it("says an account is needed, and where to get one, in plain words", async () => {
    refuseLlm([]);
    renderView();
    await generate();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/needs an account on this node/i);
    expect(alert).not.toHaveTextContent("Authorization");
    expect(
      await within(alert).findByRole("button", { name: "Register" }),
    ).toBeInTheDocument();
    expect(
      within(alert).getByRole("link", { name: "Sign in" }),
    ).toHaveAttribute("href", "/settings/session");
  });

  it("reruns the same URL without the language model from the message", async () => {
    const bodies: Record<string, unknown>[] = [];
    refuseLlm(bodies);
    renderView();
    await generate();

    await userEvent.click(
      await screen.findByRole("button", {
        name: "Generate without the language model",
      }),
    );
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[1]).toMatchObject({
      urls: ["https://github.com/mitra42/frugal-iot-hw-sensor"],
      no_llm: true,
    });
  });

  it("signing up from the message keeps the address for another try with the model", async () => {
    const bodies: Record<string, unknown>[] = [];
    refuseLlm(bodies);
    renderView();
    await generate();

    await userEvent.click(
      await screen.findByRole("button", { name: "Register" }),
    );
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("OHM Node");
    expect(dialog).toHaveTextContent("the operator of this node");
    await userEvent.type(within(dialog).getByLabelText("Username"), "mitra");
    await userEvent.type(
      within(dialog).getByLabelText("Password"),
      "correct horse",
    );
    await userEvent.type(
      within(dialog).getByLabelText("Display name"),
      "Mitra",
    );
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Create account" }),
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Continue" }),
    );

    expect(screen.getByLabelText(/Repository URL/i)).toHaveValue(
      "https://github.com/mitra42/frugal-iot-hw-sensor",
    );
    await userEvent.click(screen.getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[1]).toMatchObject({
      urls: ["https://github.com/mitra42/frugal-iot-hw-sensor"],
    });
    expect(bodies[1].no_llm).not.toBe(true);
  });
});

describe("GenerateView — save for an organisation", () => {
  it("saves a generated design for the caller's only organisation", async () => {
    sessionStorage.setItem("ohm_api_key", "test-token");
    const organisations: Array<string | null> = [];
    const manifest = {
      title: "Widget",
      version: "1.0.0",
      function: "Holds things",
      documentation_language: "en",
      licensor: { name: "Ada" },
      license: { hardware: "MIT" },
    };
    server.use(
      http.get("*/v1/api/identity/affiliations", () =>
        HttpResponse.json([
          {
            space_did: "did:key:zFab",
            display_name: "FabLab",
            expires_at: "2026-12-01T00:00:00Z",
          },
        ]),
      ),
      http.post("*/v1/api/okh/generate-from-url/jobs", () =>
        HttpResponse.json(
          {
            batch_id: "b",
            jobs: [{ job_id: "j", url: "https://github.com/acme/widget" }],
          },
          { status: 202 },
        ),
      ),
      http.get("*/v1/api/okh/generate-from-url/jobs/j", () =>
        HttpResponse.json({ state: "SUCCESS", manifest }),
      ),
      http.get("*/v1/api/okh/generate-from-url/jobs/j/events", () =>
        HttpResponse.json({ events: [] }),
      ),
      http.post("*/v1/api/okh/create", ({ request }) => {
        organisations.push(new URL(request.url).searchParams.get("on_behalf_of"));
        return HttpResponse.json(
          { success: true, message: "created", okh: { id: "okh-1" } },
          { status: 201 },
        );
      }),
    );

    try {
      renderView();
      await userEvent.type(
        screen.getByLabelText(/Repository URL/i),
        "https://github.com/acme/widget",
      );
      await userEvent.click(screen.getByRole("button", { name: "Generate" }));
      expect(
        await screen.findByRole(
          "option",
          { name: "FabLab" },
          { timeout: 3000 },
        ),
      ).toBeInTheDocument();
      await waitFor(() =>
        expect(
          screen.getByRole("combobox", { name: /on behalf of/i }),
        ).toHaveValue("did:key:zFab"),
      );
      await userEvent.click(
        screen.getByRole("button", { name: "Save to this node" }),
      );
      await waitFor(() => expect(organisations).toEqual(["did:key:zFab"]));
    } finally {
      sessionStorage.removeItem("ohm_api_key");
    }
  });
});

describe("GenerateView — before a run", () => {
  it("says what will happen, in the stage names a reader can act on", () => {
    renderView();
    expect(screen.getByText("What will happen")).toBeInTheDocument();
    // The user-facing labels, not the pipeline's own stage keys.
    expect(screen.getByText("Reading repository")).toBeInTheDocument();
    expect(screen.getByText("Enhancing with AI")).toBeInTheDocument();
    expect(screen.queryByText("bom_verification")).not.toBeInTheDocument();
  });

  it("drops the model stage from the plan when the run will skip it", async () => {
    const user = userEvent.setup();
    renderView();
    await user.click(screen.getByLabelText("Skip the language model"));
    // Promising a stage that will not run is worse than saying nothing.
    expect(screen.queryByText("Enhancing with AI")).not.toBeInTheDocument();
    expect(screen.getByText("Reading repository")).toBeInTheDocument();
  });

  it("offers a way back in for a record already on disk", () => {
    renderView();
    expect(screen.getByText("Re-open a past run")).toBeInTheDocument();
    expect(screen.getByLabelText("Generation record")).toBeInTheDocument();
  });
});
