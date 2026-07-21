import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  authHeader,
  clearToken,
  getToken,
  seedTokenFromEnv,
  setToken,
} from "./tokenStorage";

describe("tokenStorage", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.unstubAllEnvs();
  });

  it("round-trips a token in sessionStorage", () => {
    expect(getToken()).toBeNull();
    setToken("  secret-key  ");
    expect(getToken()).toBe("secret-key");
    expect(authHeader()).toEqual({ Authorization: "Bearer secret-key" });
    clearToken();
    expect(getToken()).toBeNull();
    expect(authHeader()).toEqual({});
  });

  it("seeds from VITE_OHM_API_KEY when session is empty", () => {
    vi.stubEnv("VITE_OHM_API_KEY", "env-key");
    seedTokenFromEnv();
    expect(getToken()).toBe("env-key");
    setToken("session-key");
    seedTokenFromEnv();
    expect(getToken()).toBe("session-key");
  });
});
