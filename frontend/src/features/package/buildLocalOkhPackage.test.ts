import { describe, expect, it } from "vitest";
import {
  packageFolderName,
  packageRelativePath,
} from "./buildLocalOkhPackage";

describe("packageFolderName", () => {
  it("sanitizes title and version", () => {
    expect(packageFolderName("Microlab Desktop!", "v1.2.3")).toBe(
      "microlab-desktop-v1.2.3",
    );
  });

  it("falls back when title empty", () => {
    expect(packageFolderName("", null)).toBe("okh-package-unversioned");
  });
});

describe("packageRelativePath", () => {
  it("uses display path and dedupes collisions", () => {
    const used = new Set<string>();
    expect(
      packageRelativePath(
        { title: "a", path: "docs/README.md", type: "x", metadata: {} },
        used,
      ),
    ).toBe("docs/README.md");
    expect(
      packageRelativePath(
        {
          title: "b",
          path: "https://github.com/o/r/raw/main/docs/README.md",
          type: "x",
          metadata: {},
        },
        used,
      ),
    ).toBe("docs/README-2.md");
  });
});
