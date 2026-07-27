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
import { Button } from "../../components/ui/button";
import { GuidedOkhCreate } from "./GuidedOkhCreate";

export function CreateOkhPage() {
  const [mode, setMode] = useState<"guided" | "json">("guided");

  // Uses the shared Button rather than hand-written utility classes: the raw
  // bg-primary/text-primary-foreground pairing failed contrast at 1.16:1 here,
  // while the design-system variants are already verified across the app.
  const tab = (value: "guided" | "json", label: string) => (
    <Button
      role="radio"
      aria-checked={mode === value}
      variant={mode === value ? "default" : "ghost"}
      onClick={() => setMode(value)}
    >
      {label}
    </Button>
  );

  return (
    <div>
      <div className="flex justify-end pt-4">
        <div role="radiogroup" aria-label="Entry method" className="inline-flex gap-1">
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
