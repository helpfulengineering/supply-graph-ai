import { describe, expect, it } from "vitest";
import { okhFileHref } from "./okhFileHref";
import { canPreviewFile, enrichFileRef } from "./okhFilePath";

describe("okhFileHref", () => {
  it("prefers API url from enriched manifest", () => {
    expect(
      okhFileHref("abc", {
        title: "Plan",
        path: "docs/plan.pdf",
        url: "https://host/v1/api/okh/abc/files/docs/plan.pdf",
        type: "design",
        metadata: {},
      }),
    ).toBe("https://host/v1/api/okh/abc/files/docs/plan.pdf");
  });

  it("builds proxy path when url missing", () => {
    expect(
      okhFileHref("abc", {
        title: "Plan",
        path: "images/a.png",
        type: "design",
        metadata: {},
      }),
    ).toBe("/v1/api/okh/abc/files/images/a.png");
  });

  it("detects previewable types via enrichment fallback", () => {
    expect(
      canPreviewFile(
        enrichFileRef({
          title: "x",
          path: "x.pdf",
          type: "design",
          metadata: {},
        }),
      ),
    ).toBe(true);
    expect(
      canPreviewFile(
        enrichFileRef({
          title: "x",
          path: "x.stl",
          type: "design",
          metadata: {},
        }),
      ),
    ).toBe(false);
  });
});
