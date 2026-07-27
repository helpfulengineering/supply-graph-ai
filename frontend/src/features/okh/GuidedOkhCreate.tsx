/**
 * Create a design through the same guided editor the URL import uses.
 *
 * "New design" previously accepted only pasted JSON, which asks the author to
 * already know the OKH format — the exact barrier OHM exists to remove. The
 * tiered editor already existed for reviewing generated manifests; the only
 * thing missing was starting it from an empty design instead of an extracted
 * one.
 *
 * Pasting JSON stays available for people who already have a manifest, but it
 * is no longer the only way in.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../api/ohm/client";
import { createOkh } from "../../api/ohm/okh";
import { Button } from "../../components/ui/button";
import { TieredEditor } from "../generate/TieredEditor";
import { missingRequired } from "../generate/manifestTiers";
import { downloadManifest } from "../generate/serialize";

type Manifest = Record<string, unknown>;

/**
 * A new design starts with the shape the editor expects, not an empty object,
 * so required nested fields render as inputs rather than as absent keys.
 */
export function emptyManifest(): Manifest {
  return {
    title: "",
    version: "",
    function: "",
    documentation_language: "en",
    licensor: { name: "" },
    license: { hardware: "" },
    manufacturing_processes: [],
  };
}

export function GuidedOkhCreate() {
  const navigate = useNavigate();
  const { hasWrite, reportAuthFailure } = useAuth();
  const [manifest, setManifest] = useState<Manifest>(emptyManifest);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const missing = missingRequired(manifest);
  const canSave = hasWrite && missing.length === 0 && !busy;

  async function onCreate() {
    setBusy(true);
    setError(null);
    try {
      const { id } = await createOkh(manifest, {});
      navigate(`/okh/${id}`);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        reportAuthFailure(err);
      }
      setError(err instanceof Error ? err.message : "Could not create the design.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6 py-4">
      <div>
        <h1 className="text-2xl font-bold text-foreground">New design</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Describe the design field by field. Only the required fields are needed to
          save — everything else can be filled in later, and a thin record that exists
          is more useful than a perfect one that doesn't.
        </p>
      </div>

      {!hasWrite && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100">
          You need a write-capable API key to save a design.{" "}
          <button
            type="button"
            onClick={() => navigate("/settings/session")}
            className="underline"
          >
            Connect one
          </button>
          . You can still fill this in and download it.
        </p>
      )}

      <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
        <TieredEditor manifest={manifest} onChange={setManifest} />
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        >
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Button disabled={!canSave} onClick={onCreate}>
          {busy ? "Saving…" : "Create design"}
        </Button>
        <Button
          variant="outline"
          disabled={missing.length > 0}
          onClick={() => downloadManifest(manifest, "yaml")}
        >
          Download YAML
        </Button>
        {missing.length > 0 && (
          <p className="text-sm text-amber-700 dark:text-amber-400">
            {missing.length} required field{missing.length === 1 ? "" : "s"} still to
            fill in.
          </p>
        )}
      </div>
    </div>
  );
}
