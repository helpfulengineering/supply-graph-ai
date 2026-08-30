"use client";

import { useState } from "react";
import { PANEL, PANEL_BODY } from "@/components/ui/surface";
import { BODY_MUTED, CARD_TITLE } from "@/components/ui/typography";
import { LABEL } from "@/components/ui/field";
import { cn } from "@/lib/utils";
import {
  readGenerationProvenance,
  type GenerationProvenance,
} from "./generationProvenance";

/**
 * Bring a downloaded generation record back to read it again.
 *
 * Generated designs are not kept on the server — without accounts there is no
 * owner to attach a run to — so the file a user downloaded IS the copy. That
 * makes arriving here holding one an ordinary way to use this page, not an
 * edge case, which is why it sits beside the URL field rather than somewhere
 * further in.
 *
 * Read in the browser: nothing is uploaded, and there is no round trip to
 * lose the file to.
 */
export function ReopenRecord({
  onOpen,
}: {
  onOpen: (record: GenerationProvenance) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  async function read(file: File) {
    setError(null);
    let parsed: unknown;
    try {
      parsed = JSON.parse(await file.text());
    } catch {
      setError(`${file.name} is not valid JSON.`);
      return;
    }
    const record = readGenerationProvenance(parsed);
    if (!record) {
      // Named specifically: the likeliest mistake is handing this the manifest
      // rather than the record, and the two arrive as similar-looking files
      // from the same download.
      setError(
        `${file.name} is not a generation record. It should be the .provenance.json file, not the manifest.`,
      );
      return;
    }
    onOpen(record);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) void read(file);
      }}
      className={cn(PANEL, PANEL_BODY, dragging && "border-primary")}
    >
      <h2 className={CARD_TITLE}>Re-open a past run</h2>
      <p className={cn(BODY_MUTED, "mt-1")}>
        Generated designs are not kept on the server, so the record you
        downloaded is the copy. Drop it here, or choose it below.
      </p>

      <div className="mt-3">
        {/* The input is the control; the drop target is an enhancement over
            it. A drop zone alone cannot be reached from a keyboard. */}
        <label className={LABEL} htmlFor="reopen-provenance">
          Generation record
        </label>
        <input
          id="reopen-provenance"
          type="file"
          accept=".json,application/json"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void read(file);
          }}
          className="mt-1 block w-full text-sm text-foreground file:mr-3 file:min-h-9 file:rounded-md file:border file:border-border file:bg-muted file:px-3 file:text-sm file:font-medium hover:file:bg-accent"
        />
      </div>

      {error ? (
        <p role="alert" className="mt-2 text-sm text-destructive-ink">
          {error}
        </p>
      ) : null}
    </div>
  );
}
