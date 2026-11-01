import { act, renderHook, waitFor } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { useProcessDerivation } from "./useProcessDerivation";

type Manifest = Record<string, unknown>;

const DRAFT: Manifest = {
  title: "Frugal IoT sensor",
  manufacturing_processes: ["PCB Fabrication", "Sheet Metal Forming"],
  manufacturing_specs: {
    process_requirements: [
      { process_name: "PCB Fabrication" },
      { process_name: "Sheet Metal Forming" },
    ],
  },
  tsdc: ["PCB", "SHEET"],
};

/** Stands in for the node: keeps the requirement and code of listed processes. */
const CODES: Record<string, string> = {
  "PCB Fabrication": "PCB",
  "Sheet Metal Forming": "SHEET",
};
function derive(content: Manifest): Manifest {
  const names = content.manufacturing_processes as string[];
  return {
    ...content,
    manufacturing_specs: {
      process_requirements: names.map((process_name) => ({ process_name })),
    },
    tsdc: names.map((n) => CODES[n]).filter(Boolean),
  };
}

function nodeDerives(calls: Manifest[] = []) {
  server.use(
    http.post("*/v1/api/okh/normalize", async ({ request }) => {
      const { content } = (await request.json()) as { content: Manifest };
      calls.push(content);
      return HttpResponse.json({ content: derive(content) });
    }),
  );
  return calls;
}

function setup(initial: Manifest = DRAFT) {
  return renderHook(() => {
    const [manifest, setManifest] = useState<Manifest | null>(initial);
    return { manifest, ...useProcessDerivation(manifest, setManifest) };
  });
}

const withoutSheetMetal = (m: Manifest | null): Manifest => ({
  ...m,
  manufacturing_processes: ["PCB Fabrication"],
});

describe("useProcessDerivation (#562)", () => {
  it("brings the requirements and codes into line when a process is removed", async () => {
    nodeDerives();
    const { result } = setup();

    act(() => result.current.edit(withoutSheetMetal(result.current.manifest)));
    expect(result.current.state).toBe("updating");

    await waitFor(() => expect(result.current.state).toBe("current"));
    expect(result.current.manifest?.tsdc).toEqual(["PCB"]);
    expect(result.current.manifest?.manufacturing_specs).toEqual({
      process_requirements: [{ process_name: "PCB Fabrication" }],
    });
  });

  it("does not ask the node when the process list is unchanged", () => {
    const calls = nodeDerives();
    const { result } = setup();

    act(() => result.current.edit({ ...result.current.manifest, title: "Renamed" }));

    expect(result.current.state).toBe("current");
    expect(result.current.manifest?.title).toBe("Renamed");
    expect(calls).toHaveLength(0);
  });

  it("keeps edits made while the node was answering", async () => {
    nodeDerives();
    const { result } = setup();

    act(() => result.current.edit(withoutSheetMetal(result.current.manifest)));
    act(() => result.current.edit({ ...result.current.manifest, title: "Renamed" }));

    await waitFor(() => expect(result.current.state).toBe("current"));
    expect(result.current.manifest?.title).toBe("Renamed");
    expect(result.current.manifest?.tsdc).toEqual(["PCB"]);
  });

  it("applies only the answer to the latest process list", async () => {
    let first = true;
    server.use(
      http.post("*/v1/api/okh/normalize", async ({ request }) => {
        const { content } = (await request.json()) as { content: Manifest };
        if (first) {
          first = false;
          await delay(50);
        }
        return HttpResponse.json({ content: derive(content) });
      }),
    );
    const { result } = setup();

    act(() => result.current.edit(withoutSheetMetal(result.current.manifest)));
    act(() =>
      result.current.edit({
        ...result.current.manifest,
        manufacturing_processes: ["Sheet Metal Forming"],
      }),
    );

    await waitFor(() => expect(result.current.state).toBe("current"));
    await act(() => delay(80));
    expect(result.current.manifest?.tsdc).toEqual(["SHEET"]);
  });

  it("reports a failure, and recovers on retry", async () => {
    server.use(
      http.post("*/v1/api/okh/normalize", () =>
        HttpResponse.json({ detail: "down" }, { status: 503 }),
      ),
    );
    const { result } = setup();

    act(() => result.current.edit(withoutSheetMetal(result.current.manifest)));
    await waitFor(() => expect(result.current.state).toBe("failed"));

    nodeDerives();
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.state).toBe("current"));
    expect(result.current.manifest?.tsdc).toEqual(["PCB"]);
  });

  it("starts clean when a new manifest is loaded", async () => {
    server.use(
      http.post("*/v1/api/okh/normalize", () =>
        HttpResponse.json({ detail: "down" }, { status: 503 }),
      ),
    );
    const { result } = setup();
    act(() => result.current.edit(withoutSheetMetal(result.current.manifest)));
    await waitFor(() => expect(result.current.state).toBe("failed"));

    act(() => result.current.load({ title: "Another design" }));

    expect(result.current.state).toBe("current");
    expect(result.current.manifest).toEqual({ title: "Another design" });
  });
});
