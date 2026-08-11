import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../test/msw/server";
import { STORAGE_KEY } from "../features/settings/domainPreference";
import { useDomainPreference } from "./useDomainPreference";

function mockServerDefault(defaultDomain: string) {
  server.use(
    http.get("*/v1/api/utility/domains", () =>
      HttpResponse.json({ data: { domains: [], default_domain: defaultDomain } }),
    ),
  );
}

/** This jsdom test environment has no real localStorage; stub a minimal one
 * so the hook's stored-preference branch is actually exercised. */
function stubLocalStorage() {
  const store = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => void store.set(key, value),
    clear: () => store.clear(),
  });
}

describe("useDomainPreference", () => {
  beforeEach(() => {
    stubLocalStorage();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("defaults to manufacturing before the server default_domain resolves", () => {
    const { result } = renderHook(() => useDomainPreference());
    expect(result.current.domain).toBe("manufacturing");
  });

  it("adopts the server's default_domain on a first visit (no stored preference)", async () => {
    mockServerDefault("cooking");
    const { result } = renderHook(() => useDomainPreference());
    await waitFor(() => expect(result.current.domain).toBe("cooking"));
  });

  it("does not override an existing stored preference", async () => {
    localStorage.setItem(STORAGE_KEY, "manufacturing");
    mockServerDefault("cooking");
    const { result } = renderHook(() => useDomainPreference());
    // Give the (unmade, but just in case) fetch a tick to resolve.
    await new Promise((r) => setTimeout(r, 0));
    expect(result.current.domain).toBe("manufacturing");
  });

  it("does not clobber a manual change made while the fetch is in flight", async () => {
    mockServerDefault("cooking");
    const { result } = renderHook(() => useDomainPreference());
    act(() => result.current.setDomain("manufacturing"));
    await new Promise((r) => setTimeout(r, 0));
    expect(result.current.domain).toBe("manufacturing");
  });
});
