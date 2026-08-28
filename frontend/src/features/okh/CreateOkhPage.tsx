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
import { SegmentedControl } from "../../components/ui/SegmentedControl";
import { GuidedOkhCreate } from "./GuidedOkhCreate";
import { ImportDesignFile } from "./ImportDesignFile";

type EntryMode = "guided" | "file" | "json";

const ENTRY_METHODS = [
  { value: "guided" as const, label: "Guided" },
  { value: "file" as const, label: "From a file" },
  { value: "json" as const, label: "Paste JSON" },
];

export function CreateOkhPage() {
  const [mode, setMode] = useState<EntryMode>("guided");
  // What an imported file converted to. Handed to the JSON editor as its
  // starting text rather than created directly: a converted manifest is a
  // draft somebody should read before it becomes a record, which is the whole
  // reason this uses /api/convert instead of /api/okh/upload.
  const [imported, setImported] = useState("");

  // Was two Buttons carrying role="radio" inside a role="radiogroup" — correct
  // contrast (that was the previous fix here) but still a radio group with no
  // arrow-key handling, so the announced "1 of 2" was a promise nothing kept.
  // SegmentedControl implements the pattern once, for all three call sites.
  return (
    <div>
      <div className="flex justify-end pt-4">
        <SegmentedControl
          label="Entry method"
          value={mode}
          options={ENTRY_METHODS}
          onChange={setMode}
        />
      </div>

      {mode === "guided" ? (
        <GuidedOkhCreate />
      ) : mode === "file" ? (
        <div className="pt-4">
          <ImportDesignFile
            onManifest={(manifest) => {
              setImported(JSON.stringify(manifest, null, 2));
              setMode("json");
            }}
          />
        </div>
      ) : (
        <CreateJsonRecordPage
          // Remount when an import arrives, so the editor picks up the new
          // starting text: initialJson is read once, at mount, by design.
          key={imported ? `imported-${imported.length}` : "blank"}
          title="New design"
          listHref="/okh"
          listLabel="Designs"
          detailHref={(id) => `/okh/${id}`}
          validate={validateOkh}
          create={createOkh}
          initialJson={imported}
        />
      )}
    </div>
  );
}
