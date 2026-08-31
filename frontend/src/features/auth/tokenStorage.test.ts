import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  authHeader,
  clearToken,
  getSessionOrigin,
  getToken,
  seedTokenFromEnv,
  setToken,
} from "./tokenStorage";

/**
 * Two kinds of session (#415): one the app minted, which persists, and one
 * someone pasted, which does not. The distinction is how the session began —
 * not what it can do, because a registered user could be granted admin and an
 * operator could paste a read-only key.
 */
describe("tokenStorage", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.unstubAllEnvs();
  });

  it("round-trips a pasted token in sessionStorage only", () => {
    expect(getToken()).toBeNull();
    setToken("  secret-key  ", "pasted");

    expect(getToken()).toBe("secret-key");
    expect(authHeader()).toEqual({ Authorization: "Bearer secret-key" });
    expect(getSessionOrigin()).toBe("pasted");
    // The criterion an admin key depends on: it must not outlive the tab.
    expect(JSON.stringify({ ...localStorage })).not.toContain("secret-key");

    clearToken();
    expect(getToken()).toBeNull();
    expect(authHeader()).toEqual({});
  });

  it("persists a minted token so a registered visitor stays signed in", () => {
    setToken("minted-key", "minted");

    expect(getToken()).toBe("minted-key");
    expect(getSessionOrigin()).toBe("minted");
    expect(localStorage.getItem("ohm_api_key")).toBe("minted-key");
    // Reopening the tab clears sessionStorage but not localStorage.
    sessionStorage.clear();
    expect(getToken()).toBe("minted-key");
  });

  it("defaults to the shorter-lived session when a caller does not say", () => {
    setToken("unspecified");

    expect(getSessionOrigin()).toBe("pasted");
    expect(JSON.stringify({ ...localStorage })).not.toContain("unspecified");
  });

  it("lets a pasted key win in the tab it was pasted into", () => {
    setToken("minted-key", "minted");
    setToken("pasted-key", "pasted");

    expect(getToken()).toBe("pasted-key");
    expect(getSessionOrigin()).toBe("pasted");
  });

  it("never leaves the two stores holding different tokens", () => {
    setToken("first", "minted");
    setToken("second", "pasted");
    setToken("third", "minted");

    expect(getToken()).toBe("third");
    expect(sessionStorage.getItem("ohm_api_key")).toBeNull();
    expect(localStorage.getItem("ohm_api_key")).toBe("third");
  });

  it("signs out of both stores, not just this tab", () => {
    setToken("minted-key", "minted");
    setToken("pasted-key", "pasted");

    clearToken();

    expect(getToken()).toBeNull();
    expect(getSessionOrigin()).toBeNull();
    expect(JSON.stringify({ ...localStorage })).not.toContain("key");
    expect(JSON.stringify({ ...sessionStorage })).not.toContain("key");
  });

  it("seeds from NEXT_PUBLIC_OHM_API_KEY as a pasted session", () => {
    vi.stubEnv("NEXT_PUBLIC_OHM_API_KEY", "env-key");
    seedTokenFromEnv();

    expect(getToken()).toBe("env-key");
    // A key from the environment is one the developer already had, so it gets
    // the same treatment as one they typed in.
    expect(getSessionOrigin()).toBe("pasted");

    setToken("session-key", "pasted");
    seedTokenFromEnv();
    expect(getToken()).toBe("session-key");
  });

  it("survives a storage backend that throws", () => {
    const boom = () => {
      throw new Error("storage disabled");
    };
    const original = Storage.prototype.getItem;
    Storage.prototype.getItem = boom;
    try {
      expect(getToken()).toBeNull();
      expect(getSessionOrigin()).toBeNull();
      expect(authHeader()).toEqual({});
    } finally {
      Storage.prototype.getItem = original;
    }
  });
});
