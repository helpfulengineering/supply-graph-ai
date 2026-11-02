import { describe, expect, it } from "vitest";
import { copyUpstreamHeaders } from "./proxyHeaders";

describe("copyUpstreamHeaders", () => {
  it("keeps every Set-Cookie, not only the last", () => {
    const upstream = new Headers();
    upstream.append("set-cookie", "ohm_session=a; HttpOnly; Path=/");
    upstream.append("set-cookie", "ohm_csrf=b; Path=/");
    upstream.set("content-type", "application/json");

    const copied = copyUpstreamHeaders(upstream);

    expect(copied.get("content-type")).toBe("application/json");
    expect(copied.getSetCookie()).toEqual([
      "ohm_session=a; HttpOnly; Path=/",
      "ohm_csrf=b; Path=/",
    ]);
  });
});
