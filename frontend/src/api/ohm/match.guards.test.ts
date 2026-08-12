import { describe, it, expect, vi } from "vitest";
import { runMatch } from "./match";

/**
 * The match endpoint 422s when given no design at all, which was reachable
 * from the UI and produced "Must provide either okh_id/okh_manifest/okh_url"
 * — accurate, and useless to the person who clicked Run Match.
 *
 * The id FORMAT is deliberately not guarded here; see the test below.
 */

describe("runMatch request guards", () => {
  it("refuses when no design is selected", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    await expect(runMatch({ okwIds: ["a"] })).rejects.toThrow(
      /Select a design/i,
    );
    expect(
      fetchSpy,
      "no request should reach the server",
    ).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("does not second-guess the server's id format", async () => {
    // The deployed API parses okh_id as a UUID, but that is its rule to
    // enforce. A client that duplicates it rejects instances whose ids are
    // shaped differently — the mocked lane among them.
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ data: { solutions: [] } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    await expect(runMatch({ okhId: "okh-0001" })).resolves.toBeDefined();
    expect(fetchSpy).toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("allows an inline manifest, which needs no id", async () => {
    // The generate -> match hand-off carries an unsaved manifest on purpose,
    // so the id guard must not block it.
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ data: { solutions: [] } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    await expect(
      runMatch({ okhManifest: { title: "Unsaved" } as never }),
    ).resolves.toBeDefined();
    expect(fetchSpy).toHaveBeenCalled();
    fetchSpy.mockRestore();
  });
});
