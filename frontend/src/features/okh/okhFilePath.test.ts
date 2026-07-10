import { describe, expect, it } from "vitest";
import {
  buildDirectoryTree,
  canPreviewFile,
  enrichFileRef,
  fileBasename,
  fileDirectory,
  inferRenderTier,
  isImageFile,
  normalizeDisplayPath,
  ROOT_DIRECTORY_LABEL,
} from "./okhFilePath";

describe("normalizeDisplayPath", () => {
  it("keeps relative paths", () => {
    expect(normalizeDisplayPath("design/model.stl")).toBe("design/model.stl");
  });

  it("strips github raw prefix", () => {
    expect(
      normalizeDisplayPath(
        "https://github.com/o/r/raw/main/docs/assembly/README.md",
      ),
    ).toBe("docs/assembly/README.md");
  });

  it("strips github blob prefix", () => {
    expect(
      normalizeDisplayPath("https://github.com/o/r/blob/main/design/foo.step"),
    ).toBe("design/foo.step");
  });
});

describe("buildDirectoryTree", () => {
  it("nests subdirectories under a single parent", () => {
    const tree = buildDirectoryTree([
      {
        title: "Root readme",
        path: "README.md",
        type: "design-files",
        metadata: {},
      },
      {
        title: "Backend readme",
        path: "backend/README.md",
        type: "design-files",
        metadata: {},
      },
      {
        title: "Test",
        path: "backend/tests/recipe_model_test.py",
        type: "design-files",
        metadata: {},
      },
      {
        title: "Docs",
        path: "docs/assembly/README.md",
        type: "design-files",
        metadata: {},
      },
      {
        title: "Guide",
        path: "docs/assembly/guide.pdf",
        type: "design-files",
        metadata: {},
      },
    ]);

    expect(tree.directory).toBe(ROOT_DIRECTORY_LABEL);
    expect(tree.files).toHaveLength(1);
    expect(tree.files[0]?.path).toBe("README.md");
    expect(tree.children.map((c) => c.directory)).toEqual(["backend", "docs"]);

    const backend = tree.children[0]!;
    expect(backend.files).toHaveLength(1);
    expect(backend.children[0]?.directory).toBe("backend/tests");

    const docs = tree.children[1]!;
    expect(docs.children[0]?.directory).toBe("docs/assembly");
    expect(docs.children[0]?.files).toHaveLength(2);
  });

  it("never duplicates a directory path", () => {
    const tree = buildDirectoryTree([
      { title: "a", path: "backend/a.txt", type: "x", metadata: {} },
      { title: "b", path: "backend/b.txt", type: "x", metadata: {} },
      { title: "c", path: "backend/tests/c.txt", type: "x", metadata: {} },
    ]);

    const seen = new Set<string>();
    function walk(node: ReturnType<typeof buildDirectoryTree>): void {
      expect(seen.has(node.directory)).toBe(false);
      seen.add(node.directory);
      for (const child of node.children) walk(child);
    }
    walk(tree);
    expect(seen.has("backend")).toBe(true);
    expect(seen.has("backend/tests")).toBe(true);
  });

  it("places root files under root label", () => {
    expect(fileDirectory("README.md")).toBe(ROOT_DIRECTORY_LABEL);
    expect(fileBasename("docs/a.txt")).toBe("a.txt");
  });
});

describe("preview inference without API enrichment", () => {
  it("infers image and markdown tiers from extension", () => {
    expect(inferRenderTier("docs/media/logo.png")).toBe("native_inline");
    expect(inferRenderTier("docs/index.md")).toBe("text_viewer");
    expect(inferRenderTier("parts/box.stl")).toBe("wasm_3d");
  });

  it("enables preview for images without render_tier from API", () => {
    const file = enrichFileRef({
      title: "Logo",
      path: "docs/media/logo.png",
      type: "design-files",
      metadata: {},
    });
    expect(file.render_tier).toBe("native_inline");
    expect(canPreviewFile(file)).toBe(true);
    expect(isImageFile(file)).toBe(true);
  });
});
