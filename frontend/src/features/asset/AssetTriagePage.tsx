"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchAsset,
  fetchTriageChecklist,
  recordTriage,
} from "@/api/ohm/asset";
import { PageHero } from "@/components/layout/PageHero";
import { Button, buttonVariants } from "@/components/ui/button";
import { Fieldset } from "@/components/ui/Fieldset";
import { FIELD, HINT, LABEL } from "@/components/ui/field";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { PANEL, PANEL_BODY, PANEL_MUTED } from "@/components/ui/surface";
import { BODY_MUTED, CAPTION } from "@/components/ui/typography";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { triageCrumb } from "./crumbs";
import { TriageComponentRow } from "./TriageComponentRow";
import {
  formStateFromChecklist,
  isDirty,
  setCondition,
  toTriageRequest,
  triageFormError,
  updateRow,
  type TriageFormState,
} from "./triageFormModel";
import { triageProgress } from "./triageProgress";

/**
 * A triage session: load the checklist, walk the components, submit once.
 *
 * A route rather than a panel on the detail page. It is a working session with
 * dirty state, done on a phone in a workshop, and it is the one thing in this
 * section a coordinator sends someone a link to — the same reasons
 * /facilities/{id}/edit is a route.
 */
export function AssetTriagePage({ id }: { id: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, reportAuthFailure } = useAuth();

  const asset = useQuery({
    queryKey: ["asset-detail", id],
    queryFn: () => fetchAsset(id),
    staleTime: 0,
  });

  const checklist = useQuery({
    queryKey: ["asset-triage-checklist", id],
    queryFn: () => fetchTriageChecklist(id),
    staleTime: 0,
  });

  const [state, setState] = useState<TriageFormState | null>(null);
  const original = useMemo(
    () =>
      checklist.data
        ? formStateFromChecklist(checklist.data, {
            assessedBy: user?.name ?? "",
            sessionNotes: asset.data?.triage_notes ?? "",
          })
        : null,
    [checklist.data, asset.data?.triage_notes, user?.name],
  );

  useEffect(() => {
    if (original && state === null) setState(original);
  }, [original, state]);

  const submit = useMutation({
    mutationFn: () => {
      if (!state || !original) throw new Error("Checklist not loaded");
      return recordTriage(id, toTriageRequest(state, original));
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["asset-detail", id] });
      void queryClient.invalidateQueries({
        queryKey: ["asset-triage-report", id],
      });
      void queryClient.invalidateQueries({ queryKey: ["asset-sourcing", id] });
      void queryClient.invalidateQueries({ queryKey: ["asset-list"] });
      // Land on what the session just changed, not back at the top of the page.
      router.push(`/assets/${id}#triage-report`);
    },
    onError: reportAuthFailure,
  });

  if (asset.isPending || checklist.isPending) {
    return <LoadingState message="Loading checklist…" />;
  }

  if (checklist.isError || !checklist.data || !asset.data) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6">
        <ErrorState
          title="Could not load the triage checklist"
          description={(checklist.error as Error)?.message}
          onRetry={() => void checklist.refetch()}
        />
      </div>
    );
  }

  const data = checklist.data;
  const form = state ?? original!;
  const dirty = original ? isDirty(form, original) : false;
  const error = original ? triageFormError(form, original) : null;
  const progress = triageProgress(data.assessed_count, data.total_components);

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <PageHero
        title="Triage"
        breadcrumb={[
          { label: "Assets", href: "/assets" },
          { label: data.asset_tag, href: `/assets/${id}` },
          { label: "Triage" },
        ]}
        crumb={triageCrumb(data.manifest_id)}
        description={`Assess ${data.asset_tag} component by component.`}
      />

      <div className={cn(PANEL_MUTED, "mb-4 px-4 py-3")}>
        <p className="text-sm text-foreground">{progress.label}</p>
        {data.last_triaged_at && (
          <p className={cn(CAPTION, "mt-1")}>
            Previous observations are pre-filled. Recording again replaces them,
            and leaves components you do not touch as they are.
          </p>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!error) submit.mutate();
        }}
      >
        <div className={cn(PANEL, PANEL_BODY, "mb-4")}>
          <label className={LABEL} htmlFor="assessed-by">
            Assessed by
          </label>
          <input
            id="assessed-by"
            value={form.assessedBy}
            onChange={(e) => setState({ ...form, assessedBy: e.target.value })}
            placeholder="Your name"
            className={FIELD}
          />
          <p className={HINT}>
            Recorded against every observation in this session.
          </p>
        </div>

        {/*
          One fieldset for the whole checklist, not one per component: twelve
          components would otherwise be twelve nested panels.
        */}
        <Fieldset legend="Component conditions" legendHidden className="mb-4">
          {data.items.map((item) => {
            const row = form.rows.find(
              (r) => r.componentName === item.component_name,
            );
            if (!row) return null;
            return (
              <TriageComponentRow
                key={item.component_name}
                item={item}
                row={row}
                onChange={(patch) =>
                  setState(updateRow(form, item.component_name, patch))
                }
                onCondition={(condition) =>
                  setState(setCondition(form, item.component_name, condition))
                }
              />
            );
          })}
        </Fieldset>

        <div className={cn(PANEL, PANEL_BODY, "mb-4")}>
          <label className={LABEL} htmlFor="session-notes">
            Session notes
          </label>
          <textarea
            id="session-notes"
            rows={3}
            value={form.sessionNotes}
            onChange={(e) =>
              setState({ ...form, sessionNotes: e.target.value })
            }
            className={FIELD}
          />
          <p className={HINT}>Replaces the notes on the record.</p>
        </div>

        <div className="sticky bottom-0 flex flex-wrap items-center gap-3 border-t border-border bg-background/95 py-3 backdrop-blur">
          <Button type="submit" disabled={!dirty || submit.isPending}>
            {submit.isPending ? "Recording…" : "Record triage"}
          </Button>
          <Link
            href={`/assets/${id}`}
            className={cn(
              buttonVariants({ variant: "outline" }),
              "no-underline",
            )}
          >
            Cancel
          </Link>
          {error && dirty && <span className={CAPTION}>{error}</span>}
          {submit.isError && (
            <span className={cn(CAPTION, "text-destructive")} role="alert">
              {(submit.error as Error).message}
            </span>
          )}
          {!dirty && (
            <span className={BODY_MUTED}>
              Nothing recorded yet this session.
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
