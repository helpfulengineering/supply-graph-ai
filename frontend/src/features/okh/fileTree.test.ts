import { describe, expect, it } from "vitest";
import type { OkhFileRef } from "../../types/okh";
import { buildFileTree, pickHeadlineFiles } from "./fileTree";

function file(path: string, title = path): OkhFileRef {
  return { title, path, type: "design-files", metadata: {} };
}

describe("buildFileTree", () => {
  it("nests files by directory and puts folders before files", () => {
    const tree = buildFileTree([
      file("BBB_SCH.pdf"),
      file("images/a.jpg"),
      file("images/b.jpg"),
      file("MFG/board.drl"),
    ]);
    // Top level: folders (alphabetical, case-insensitive) before the root file.
    expect(tree.children.map((c) => c.name)).toEqual(["images", "MFG", "BBB_SCH.pdf"]);
    const images = tree.children.find((c) => c.name === "images")!;
    expect(images.file).toBeUndefined();
    expect(images.children.map((c) => c.name)).toEqual(["a.jpg", "b.jpg"]);
    expect(images.children[0].file).toBeDefined();
  });
});

describe("pickHeadlineFiles", () => {
  it("surfaces READMEs, assembly/instructions, BOMs, and root docs", () => {
    const picked = pickHeadlineFiles([
      file("README.md"),
      file("docs/Assembly_Instructions.pdf"),
      file("bom.csv", "BOM.csv"),
      file("images/random.jpg"),
      file("src/part.scad"),
    ]);
    const names = picked.map((f) => f.path);
    expect(names).toContain("README.md");
    expect(names).toContain("docs/Assembly_Instructions.pdf");
    expect(names).not.toContain("images/random.jpg");
    expect(names).not.toContain("src/part.scad");
  });

  it("caps the list and ranks name matches above bare root docs", () => {
    const many = Array.from({ length: 20 }, (_, i) => file(`doc${i}.pdf`));
    expect(pickHeadlineFiles([file("README.md"), ...many]).length).toBeLessThanOrEqual(12);
    expect(pickHeadlineFiles([file("README.md"), ...many])[0].path).toBe("README.md");
  });
});
