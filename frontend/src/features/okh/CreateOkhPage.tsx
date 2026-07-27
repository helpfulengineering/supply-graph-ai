/**
 * New design: guided by default, raw JSON on request.
 *
 * The guided editor is the default because requiring someone to hand-author an
 * OKH manifest is the barrier OHM exists to remove. The JSON route stays for
 * people who already have a manifest — a shortcut, not the entry point.
 */

import { useState } from "react";
import { CreateJsonRecordPage } from "../create/CreateJsonRecordPage";
import { createOkh, validateOkh } from "../../api/ohm/okh";
import { GuidedOkhCreate } from "./GuidedOkhCreate";

export function CreateOkhPage() {
  const [mode, setMode] = useState<"guided" | "json">("guided");

  const tab = (value: "guided" | "json", label: string) => (
    <button
      type="button"
      role="radio"
      aria-checked={mode === value}
      onClick={() => setMode(value)}
      className={
        mode === value
          ? "bg-primary px-3 py-1.5 text-primary-foreground"
          : "bg-background px-3 py-1.5 text-foreground hover:bg-accent"
      }
    >
      {label}
    </button>
  );

  return (
    <div>
      <div className="flex justify-end pt-4">
        <div
          role="radiogroup"
          aria-label="Entry method"
          className="inline-flex overflow-hidden rounded-md border border-input text-sm"
        >
          {tab("guided", "Guided")}
          {tab("json", "Paste JSON")}
        </div>
      </div>

      {mode === "guided" ? (
        <GuidedOkhCreate />
      ) : (
        <CreateJsonRecordPage
          title="New design"
          listHref="/okh"
          listLabel="Designs"
          detailHref={(id) => `/okh/${id}`}
          validate={validateOkh}
          create={createOkh}
        />
      )}
    </div>
  );
}
