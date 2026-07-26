/**
 * Manifest serialisation for download (pure, unit-tested).
 *
 * Both formats are offered because both are used in practice. A good part of
 * the OKH ecosystem publishes YAML — it is far easier to read and hand-edit
 * than JSON, which matters for a file a human is expected to review and correct.
 */

import { dump } from "js-yaml";

export type DownloadFormat = "json" | "yaml";

export interface SerializedManifest {
  text: string;
  filename: string;
  mimeType: string;
}

/** Slugify a title into a safe, readable filename stem. */
export function filenameStem(manifest: Record<string, unknown>): string {
  const title = typeof manifest.title === "string" ? manifest.title : "";
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
  return slug || "design";
}

export function serializeManifest(
  manifest: Record<string, unknown>,
  format: DownloadFormat,
): SerializedManifest {
  const stem = filenameStem(manifest);
  if (format === "yaml") {
    return {
      // `noRefs` keeps repeated objects expanded rather than emitting YAML
      // anchors/aliases, which are valid but confuse humans and some readers.
      // `lineWidth: -1` stops long descriptions being wrapped mid-sentence.
      text: dump(manifest, { noRefs: true, lineWidth: -1, sortKeys: false }),
      filename: `${stem}.okh.yaml`,
      mimeType: "application/yaml",
    };
  }
  return {
    text: JSON.stringify(manifest, null, 2),
    filename: `${stem}.okh.json`,
    mimeType: "application/json",
  };
}

/** Trigger a browser download of the serialized manifest. */
export function downloadManifest(
  manifest: Record<string, unknown>,
  format: DownloadFormat,
): void {
  const { text, filename, mimeType } = serializeManifest(manifest, format);
  const href = URL.createObjectURL(new Blob([text], { type: mimeType }));
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(href);
}
