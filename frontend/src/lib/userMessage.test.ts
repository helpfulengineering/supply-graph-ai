import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/ohm/client";
import { userFacingError } from "./userMessage";

/**
 * The properties that matter are not the exact sentences — copy gets edited —
 * but that every branch produces prose rather than a status code, and that
 * `retryable` never invites someone to repeat a request that cannot succeed.
 */

afterEach(() => {
  vi.unstubAllGlobals();
});

/** jsdom reports online by default; offline is the case worth constructing. */
function goOffline(): void {
  vi.stubGlobal("navigator", { ...navigator, onLine: false });
}

describe("userFacingError", () => {
  it("never leaks a bare status code into what the user reads", () => {
    for (const status of [401, 403, 404, 408, 409, 413, 422, 429, 500, 503]) {
      const msg = userFacingError(new ApiError(status, "raw"));
      expect(`${msg.title} ${msg.body}`).not.toMatch(/\b\d{3}\b/);
    }
  });

  it("does not offer a retry for failures a retry cannot fix", () => {
    for (const status of [401, 403, 404, 409, 413, 422]) {
      expect(userFacingError(new ApiError(status, "raw")).retryable).toBe(
        false,
      );
    }
  });

  it("offers a retry for the transient failures", () => {
    for (const status of [408, 429, 500, 502, 503, 504]) {
      expect(userFacingError(new ApiError(status, "raw")).retryable).toBe(true);
    }
  });

  it("keeps the API's validation text on a 422, where it names the field", () => {
    const msg = userFacingError(
      new ApiError(422, "manufacturing_processes is required"),
    );
    expect(msg.body).toBe("manufacturing_processes is required");
  });

  it("carries the request id through, so an operator can be given one", () => {
    const msg = userFacingError(new ApiError(500, "boom", "req-42"));
    expect(msg.requestId).toBe("req-42");
  });

  it("explains a dropped connection instead of showing 'Failed to fetch'", () => {
    const msg = userFacingError(new TypeError("Failed to fetch"));
    expect(msg.title).toBe("Could not reach the server");
    expect(msg.body).not.toMatch(/fetch/i);
  });

  it("blames the device, not the instance, when the browser says it is offline", () => {
    goOffline();
    expect(userFacingError(new ApiError(500, "boom")).title).toBe(
      "You are offline",
    );
  });

  it("distinguishes a cancelled request from a failure", () => {
    const abort = new Error("The operation was aborted");
    abort.name = "AbortError";
    expect(userFacingError(abort).title).toBe("That request was cancelled");
  });

  it("shows a plain Error's own message, which is usually already prose", () => {
    expect(userFacingError(new Error("Package not found")).body).toBe(
      "Package not found",
    );
  });

  it("withholds an untrusted Error's message, where it is a stack-trace phrase", () => {
    const msg = userFacingError(
      new Error("Cannot read properties of undefined (reading 'map')"),
      { trustErrorMessage: false },
    );
    expect(msg.body).not.toMatch(/undefined/);
    expect(msg.title).toBe("Something went wrong");
  });

  it("still describes a recognized failure exactly when the message is untrusted", () => {
    const msg = userFacingError(new ApiError(429, "slow down"), {
      trustErrorMessage: false,
    });
    expect(msg.title).toBe("Too many requests");
  });

  it("falls back to prose for a thrown non-Error", () => {
    const msg = userFacingError("kaboom");
    expect(msg.title).toBe("Something went wrong");
    expect(msg.body).not.toBe("kaboom");
  });
});
