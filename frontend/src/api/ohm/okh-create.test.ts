import { describe, expect, it } from "vitest";
import { createOkh, getOkhProvenance, setOkhVisibility } from "./okh";
import { createOkw } from "./okw";

describe("okh create / provenance / visibility", () => {
  it("createOkh returns the stored id", async () => {
    const result = await createOkh({ title: "Test" });
    expect(result.id).toBe("okh-created");
  });

  it("getOkhProvenance returns authored_by", async () => {
    const p = await getOkhProvenance("okh-0001");
    expect(p?.authored_by?.[0]?.external_id).toBe("name:Test Author");
  });

  it("setOkhVisibility updates level", async () => {
    const v = await setOkhVisibility("okh-0001", "public");
    expect(v.visibility).toBe("public");
  });
});

describe("okw create", () => {
  it("createOkw returns the stored id", async () => {
    const result = await createOkw({ name: "Lab" });
    expect(result.id).toBe("okw-created");
  });
});
