import { beforeEach, describe, expect, it, vi } from "vitest";
import { setToken, clearToken } from "../../features/auth/tokenStorage";
import { get } from "../client";
import { fetchWhoami } from "./identity";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api clients attach Bearer", () => {
  beforeEach(() => {
    clearToken();
    vi.restoreAllMocks();
  });

  it("legacy get includes Authorization when token is set", async () => {
    setToken("test-token");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await get("/utility/domains");

    expect(fetchMock).toHaveBeenCalled();
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer test-token");
  });

  it("typed client includes Authorization when token is set", async () => {
    setToken("typed-token");
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        key_id: "00000000-0000-0000-0000-000000000001",
        name: "test",
        permissions: ["admin"],
        account_id: "00000000-0000-0000-0000-000000000001",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchWhoami();

    expect(fetchMock).toHaveBeenCalled();
    const input = fetchMock.mock.calls[0][0] as Request;
    expect(input.headers.get("Authorization")).toBe("Bearer typed-token");
  });
});
