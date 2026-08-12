"use client";

import { useState } from "react";
import { load as parseYaml } from "js-yaml";
import {
  fromDatasheet,
  fromOkhLosh,
  IMPORT_ACCEPT,
  IMPORT_FORMATS,
  importRouteFor,
} from "@/api/ohm/convert";
import type { OkhManifest } from "@/types/okh";
import { HINT, LABEL } from "@/components/ui/field";
import { PANEL, PANEL_BODY } from "@/components/ui/surface";
import { BODY_MUTED, CAPTION } from "@/components/ui/typography";
import { cn } from "@/lib/utils";

/**
 * Start a design from a file this node knows how to read.
 *
 * Four formats, one input, routed by extension: an OKH manifest is parsed in
 * the browser, and OKH-LOSH TOML and MSF datasheets go to /api/convert, which
 * returns a manifest WITHOUT storing it. That last part is the reason this uses
 * convert rather than /api/okh/upload — upload validates and saves in one step,
 * where this hands the result to the editor so it can be read before anything
 * is written.
 */
export function ImportDesignFile({
  onManifest,
}: {
  onManifest: (manifest: OkhManifest, filename: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handle(file: File) {
    setError(null);
    const route = importRouteFor(file.name);
    if (!route) {
      // Name the four it takes, rather than saying the one it got is wrong.
      setError(
        `${file.name} is not a format this node reads. Try .yaml, .json, .toml, or .docx.`,
      );
      return;
    }
    setBusy(true);
    try {
      if (route === "parse") {
        const text = await file.text();
        const parsed = parseYaml(text) as OkhManifest;
        if (!parsed || typeof parsed !== "object") {
          throw new Error("That file did not parse as a manifest.");
        }
        onManifest(parsed, file.name);
      } else {
        const manifest =
          route === "okh-losh"
            ? await fromOkhLosh(file)
            : await fromDatasheet(file);
        onManifest(manifest, file.name);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not read that file.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={cn(PANEL, PANEL_BODY)}>
      <p className={BODY_MUTED}>
        Start from a file you already have. Nothing is saved until you review
        the result and press Create.
      </p>

      <div className="mt-4">
        <label className={LABEL} htmlFor="import-design-file">
          Design file
        </label>
        <input
          id="import-design-file"
          type="file"
          accept={IMPORT_ACCEPT}
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handle(file);
          }}
          className="mt-1 block w-full text-sm text-foreground file:mr-3 file:min-h-9 file:rounded-md file:border file:border-border file:bg-muted file:px-3 file:text-sm file:font-medium hover:file:bg-accent"
        />
        <p className={HINT}>
          Read on this node; the file is not uploaded anywhere else.
        </p>
      </div>

      <dl className="mt-4 space-y-1">
        {IMPORT_FORMATS.map((format) => (
          <div key={format.label} className="flex flex-wrap gap-x-2 text-sm">
            <dt className="font-mono text-foreground">{format.label}</dt>
            <dd className={CAPTION}>{format.note}</dd>
          </div>
        ))}
      </dl>

      {busy && <p className={cn(CAPTION, "mt-3")}>Reading…</p>}
      {error && (
        <p className={cn(CAPTION, "mt-3 text-destructive")} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
