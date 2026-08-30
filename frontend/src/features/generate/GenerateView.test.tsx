import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/ohm/client";
import { GenerateView, generationErrorMessage } from "./GenerateView";

function renderView() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <GenerateView />
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
    const msg = generationErrorMessage(new ApiError(422, "no manifest-like files found"));
    expect(msg).toContain("no manifest-like files found");
  });

  it("keeps 5xx generic rather than leaking internals", () => {
    const msg = generationErrorMessage(new ApiError(500, "Traceback: KeyError foo"));
    expect(msg).not.toContain("Traceback");
    expect(msg).toContain("Please try again");
  });

  it("names jobs unavailable on 503", () => {
    expect(generationErrorMessage(new ApiError(503, "disabled"))).toContain(
      "Background generation",
    );
  });

  it("falls back to the message for other 4xx", () => {
    expect(generationErrorMessage(new ApiError(400, "bad url"))).toBe("bad url");
  });

  it("handles a non-Error throw", () => {
    expect(generationErrorMessage("boom")).toBe("Generation failed.");
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
