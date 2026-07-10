import type { OkhFileRef } from "../../types/okh";
import { encodePathSegments } from "./okhFilePath";

/** Prefer API ``url`` from enriched manifest detail; fallback for older payloads. */
export function okhFileHref(okhId: string, file: OkhFileRef): string {
  if (file.url) return file.url;
  if (file.path.startsWith("http://") || file.path.startsWith("https://")) {
    return file.path;
  }
  return `/v1/api/okh/${encodeURIComponent(okhId)}/files/${encodePathSegments(file.path)}`;
}
