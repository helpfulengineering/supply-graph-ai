"use client";

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

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchOkhTemplate } from "../../api/ohm/okh";
import { PageHero } from "../../components/layout/PageHero";
import { useRouter } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../api/ohm/client";
import { createOkh } from "../../api/ohm/okh";
import { Button } from "../../components/ui/button";
import { TieredEditor } from "../generate/TieredEditor";
import { missingRequired } from "../generate/manifestTiers";
import { downloadManifest } from "../generate/serialize";
import {
  PANEL,
  PANEL_DANGER,
  PANEL_WARNING,
} from "../../components/ui/surface";
import { cn } from "@/lib/utils";

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
  const router = useRouter();
  const { hasWrite, reportAuthFailure } = useAuth();
  const [manifest, setManifest] = useState<Manifest>(emptyManifest);
  // Seed the blank form from the server's own template, so a field the model
  // grows appears here without this file being edited. `emptyManifest` stays
  // as the offline shape — it is what the form opens with, and this only fills
  // keys it does not already carry, so nothing a user has typed is replaced.
  const template = useQuery({
    queryKey: ["okh-template"],
    queryFn: fetchOkhTemplate,
    retry: false,
    retryOnMount: false,
    staleTime: Infinity,
  });
  const seeded = useRef(false);
  useEffect(() => {
    if (seeded.current || !template.data) return;
    seeded.current = true;
    setManifest((current) => {
      const merged = { ...current } as Record<string, unknown>;
      for (const [key, value] of Object.entries(template.data)) {
        if (merged[key] === undefined) merged[key] = value;
      }
      return merged as Manifest;
    });
  }, [template.data]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const missing = missingRequired(manifest);
  const canSave = hasWrite && missing.length === 0 && !busy;

  async function onCreate() {
    setBusy(true);
    setError(null);
    try {
      const { id } = await createOkh(manifest, {});
      router.push(`/okh/${id}`);
    } catch (err) {
      if (
        err instanceof ApiError &&
        (err.status === 401 || err.status === 403)
      ) {
        reportAuthFailure(err);
      }
      setError(
        err instanceof Error ? err.message : "Could not create the design.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6 py-4">
      <PageHero
        title="New design"
        description="Describe the design field by field. Only the required fields are needed to save — everything else can be filled in later, and a thin record that exists is more useful than a perfect one that doesn't."
      />

      {!hasWrite && (
        <p className={cn(PANEL_WARNING, "text-sm text-warning-ink")}>
          You need a write-capable API key to save a design.{" "}
          <button
            type="button"
            onClick={() => router.push("/settings/session")}
            className="underline"
          >
            Connect one
          </button>
          . You can still fill this in and download it.
        </p>
      )}

      <div className={PANEL}>
        <TieredEditor manifest={manifest} onChange={setManifest} />
      </div>

      {error && (
        <p
          role="alert"
          className={cn(
            PANEL_DANGER,
            "text-sm text-destructive bg-destructive/10",
          )}
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
          <p className="text-sm text-warning">
            {missing.length} required field{missing.length === 1 ? "" : "s"}{" "}
            still to fill in.
          </p>
        )}
      </div>
    </div>
  );
}
