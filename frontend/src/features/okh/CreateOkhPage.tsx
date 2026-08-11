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

const ENTRY_METHODS = [
  { value: "guided" as const, label: "Guided" },
  { value: "json" as const, label: "Paste JSON" },
];

export function CreateOkhPage() {
  const [mode, setMode] = useState<"guided" | "json">("guided");

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
