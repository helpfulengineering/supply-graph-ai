import type { OkhFileRef } from "../../types/okh";

/** Prefer API ``url`` from enriched manifest detail; fallback for older payloads. */
export function okhFileHref(okhId: string, file: OkhFileRef): string {
  if (file.url) return file.url;
  if (file.path.startsWith("http://") || file.path.startsWith("https://")) {
    return file.path;
  }
  const encoded = file.path
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
  return `/v1/api/okh/${encodeURIComponent(okhId)}/files/${encoded}`;
}

/** PDFs and images open inline in a new tab; binaries download. */
export function okhFileOpensInline(file: OkhFileRef): boolean {
  const ref = (file.path || file.url || "").toLowerCase();
  return (
    ref.endsWith(".pdf") ||
    ref.endsWith(".png") ||
    ref.endsWith(".jpg") ||
    ref.endsWith(".jpeg") ||
    ref.endsWith(".gif") ||
    ref.endsWith(".webp") ||
    ref.endsWith(".md") ||
    ref.endsWith(".txt")
  );
}
