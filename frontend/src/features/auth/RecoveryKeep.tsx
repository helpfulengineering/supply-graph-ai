"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FIELD_SM } from "../../components/ui/field";
import { TokenOnce } from "./TokenOnce";

/**
 * The one secret signup and recovery ask someone to keep.
 *
 * Copy is on the token panel. Download is the other way out of the browser.
 * Continue stays disabled until they say they have saved it.
 */
export function RecoveryKeep({
  code,
  heading,
  description,
}: {
  code: string;
  heading: string;
  description: string;
}) {
  const router = useRouter();
  const [saved, setSaved] = useState(false);

  function download() {
    const blob = new Blob([`${code}\n`], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ohm-recovery-code.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-3">
      <TokenOnce token={code} heading={heading} description={description} />
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className={FIELD_SM} onClick={download}>
          Download
        </button>
        <label className="flex items-center gap-2 text-sm text-foreground">
          <input
            type="checkbox"
            checked={saved}
            onChange={(event) => setSaved(event.target.checked)}
          />
          I have saved this recovery code
        </label>
        <button
          type="button"
          disabled={!saved}
          className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent hover:bg-primary disabled:opacity-50"
          onClick={() => router.push("/account")}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
