import type { OkhFileRef } from "../../types/okh";

export const ROOT_DIRECTORY_LABEL = "(root)";

type RenderTier = NonNullable<OkhFileRef["render_tier"]>;

const GITHUB_HOSTED =
  /^https?:\/\/(?:www\.)?github\.com\/[^/]+\/[^/]+\/(?:raw|blob)\/[^/]+\/(.+)$/i;
const GITHUB_RAW =
  /^https?:\/\/raw\.githubusercontent\.com\/[^/]+\/[^/]+\/[^/]+\/(.+)$/i;
const GITLAB_RAW =
  /^https?:\/\/[^/]+\/[^/]+\/[^/]+\/-\/raw\/[^/]+\/(.+)$/i;
const GITLAB_BLOB =
  /^https?:\/\/[^/]+\/[^/]+\/[^/]+\/-\/blob\/[^/]+\/(.+)$/i;

function rejectTraversal(path: string): string {
  if (path.split("/").includes("..")) {
    throw new Error("invalid file path");
  }
  return path;
}

export function normalizeDisplayPath(path: string): string {
  const raw = (path || "").trim().replace(/\\/g, "/");
  if (!raw) return "";

  for (const pattern of [GITHUB_HOSTED, GITHUB_RAW, GITLAB_RAW, GITLAB_BLOB]) {
    const match = raw.match(pattern);
    if (match?.[1]) {
      return rejectTraversal(match[1].replace(/^\//, ""));
    }
  }

  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    const withoutQuery = raw.split("?")[0] ?? raw;
    return rejectTraversal(withoutQuery.replace(/\/$/, "").split("/").pop() ?? "");
  }

  return rejectTraversal(raw.replace(/^\//, ""));
}

export function fileBasename(displayPath: string): string {
  if (!displayPath) return "";
  const parts = displayPath.split("/");
  return parts[parts.length - 1] ?? "";
}

export function fileDirectory(displayPath: string): string {
  if (!displayPath) return ROOT_DIRECTORY_LABEL;
  const parts = displayPath.split("/");
  if (parts.length <= 1) return ROOT_DIRECTORY_LABEL;
  return parts.slice(0, -1).join("/");
}

/** Client fallback when API has not enriched render_tier. */
export function inferRenderTier(displayPath: string): RenderTier {
  const ref = displayPath.toLowerCase();
  if (/\.(png|jpe?g|gif|webp|bmp|svg|pdf)$/.test(ref)) return "native_inline";
  if (/\.(md|markdown|mdown|txt|log|csv|json|ya?ml|xml|toml|gcode|nc|scad)$/.test(ref)) {
    return "text_viewer";
  }
  if (/\.(stl|obj|ply)$/.test(ref)) return "wasm_3d";
  return "download_only";
}

export function enrichFileRef(file: OkhFileRef): OkhFileRef {
  const display_path = file.display_path ?? normalizeDisplayPath(file.path);
  return {
    ...file,
    display_path,
    directory: file.directory ?? fileDirectory(display_path),
    basename: fileBasename(display_path),
    render_tier: file.render_tier ?? inferRenderTier(display_path),
  };
}

export interface DirectoryTreeNode {
  directory: string;
  name: string;
  files: OkhFileRef[];
  children: DirectoryTreeNode[];
}

function comparePath(a: string, b: string): number {
  return a.localeCompare(b, undefined, { sensitivity: "base" });
}

function sortTree(node: DirectoryTreeNode): void {
  node.files.sort((a, b) =>
    comparePath(a.display_path ?? a.path, b.display_path ?? b.path),
  );
  node.children.sort((a, b) => comparePath(a.directory, b.directory));
  for (const child of node.children) sortTree(child);
}

/** Nested directory tree; each path appears once, root-first tree-walk order. */
export function buildDirectoryTree(files: OkhFileRef[]): DirectoryTreeNode {
  const enriched = files.map(enrichFileRef);
  const root: DirectoryTreeNode = {
    directory: ROOT_DIRECTORY_LABEL,
    name: "/",
    files: [],
    children: [],
  };
  const byPath = new Map<string, DirectoryTreeNode>([[ROOT_DIRECTORY_LABEL, root]]);

  function ensureDir(dirPath: string): DirectoryTreeNode {
    const existing = byPath.get(dirPath);
    if (existing) return existing;

    const parts = dirPath.split("/");
    const name = parts[parts.length - 1] ?? dirPath;
    const node: DirectoryTreeNode = {
      directory: dirPath,
      name,
      files: [],
      children: [],
    };
    byPath.set(dirPath, node);

    const parentPath =
      parts.length === 1 ? ROOT_DIRECTORY_LABEL : parts.slice(0, -1).join("/");
    ensureDir(parentPath).children.push(node);
    return node;
  }

  for (const file of enriched) {
    ensureDir(file.directory ?? ROOT_DIRECTORY_LABEL).files.push(file);
  }

  sortTree(root);
  return root;
}

export function filePrimaryLabel(file: OkhFileRef): string {
  const basename = file.basename ?? fileBasename(file.display_path ?? file.path);
  const title = (file.title || "").trim();
  if (title && title.toLowerCase() !== basename.toLowerCase()) {
    return title;
  }
  return basename || file.path.split("/").pop() || "file";
}

export function canPreviewFile(file: OkhFileRef): boolean {
  const tier = file.render_tier ?? inferRenderTier(file.display_path ?? file.path);
  return tier === "native_inline" || tier === "text_viewer";
}

export function isImageFile(file: OkhFileRef): boolean {
  const mime = file.mime_type ?? "";
  if (mime.startsWith("image/")) return true;
  return /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(file.display_path ?? file.path);
}

export function isPdfFile(file: OkhFileRef): boolean {
  if (file.file_type === "document_pdf") return true;
  if ((file.mime_type ?? "") === "application/pdf") return true;
  return /\.pdf$/i.test(file.display_path ?? file.path);
}

export function isMarkdownFile(file: OkhFileRef): boolean {
  return /\.(md|markdown|mdown)$/i.test(file.display_path ?? file.path);
}

export function encodePathSegments(path: string): string {
  return path
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}
