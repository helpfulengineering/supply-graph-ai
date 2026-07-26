import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/ohm/client";
import { generationErrorMessage } from "./GenerateView";

describe("generationErrorMessage", () => {
  it("says cancelled, not failed, when the user aborts", () => {
    const abort = new DOMException("aborted", "AbortError");
    expect(generationErrorMessage(abort)).toBe("Generation was cancelled.");
  });

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

  it("names the size problem on a timeout", () => {
    expect(generationErrorMessage(new ApiError(504, "gateway timeout"))).toContain(
      "too long",
    );
  });

  it("falls back to the message for other 4xx", () => {
    expect(generationErrorMessage(new ApiError(400, "bad url"))).toBe("bad url");
  });

  it("handles a non-Error throw", () => {
    expect(generationErrorMessage("boom")).toBe("Generation failed.");
  });
});
