import type { OkhFileRef } from "../../types/okh";

/**
 * OKH file organization (pure, unit-tested).
 *
 * OKH manifests carry a flat, unordered list of files (100+ for real designs).
 * `buildFileTree` reconstructs the directory hierarchy from each file's `path`;
 * `pickHeadlineFiles` surfaces the handful a user would actually open (READMEs,
 * assembly instructions, BOMs, root-level docs).
 */

export interface FileTreeNode {
  name: string;
  path: string;
  file?: OkhFileRef;
  children: FileTreeNode[];
}

export function buildFileTree(files: OkhFileRef[]): FileTreeNode {
  const root: FileTreeNode = { name: "", path: "", children: [] };
  for (const f of files) {
    const parts = (f.path || f.title || "").split("/").filter(Boolean);
    if (parts.length === 0) continue;
    let cur = root;
    parts.forEach((part, i) => {
      const isLeaf = i === parts.length - 1;
      let child = cur.children.find(
        (c) => c.name === part && !!c.file === isLeaf,
      );
      if (!child) {
        child = { name: part, path: parts.slice(0, i + 1).join("/"), children: [] };
        if (isLeaf) child.file = f;
        cur.children.push(child);
      }
      cur = child;
    });
  }
  const sortRec = (n: FileTreeNode) => {
    // Folders before files, then alphabetical.
    n.children.sort((a, b) =>
      !!a.file === !!b.file ? a.name.localeCompare(b.name) : a.file ? 1 : -1,
    );
    n.children.forEach(sortRec);
  };
  sortRec(root);
  return root;
}

const HEADLINE_PATTERNS = [
  /readme/i,
  /assembl/i,
  /instruction/i,
  /\bmanual\b/i,
  /\bguide\b/i,
  /\bbom\b/i,
  /getting.?started/i,
  /\bbuild\b/i,
];

const DOC_EXT = /\.(md|pdf|txt|docx?|rst)$/i;

/** The most-inspectable files: matched by name, then root-level docs. Capped. */
export function pickHeadlineFiles(files: OkhFileRef[]): OkhFileRef[] {
  return files
    .map((f) => {
      const hay = `${f.title} ${f.path}`.toLowerCase();
      const isRootDoc = !f.path.includes("/") && DOC_EXT.test(f.path || f.title);
      const matched = HEADLINE_PATTERNS.some((p) => p.test(hay));
      return { f, score: (matched ? 2 : 0) + (isRootDoc ? 1 : 0) };
    })
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 12)
    .map((s) => s.f);
}
