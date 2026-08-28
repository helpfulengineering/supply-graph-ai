"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateAsset } from "@/api/ohm/asset";
import { FIELD_SM } from "@/components/ui/field";
import { CAPTION } from "@/components/ui/typography";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils";
import { ASSET_STATUSES, assetStatusInfo } from "./assetStatus";

/**
 * Set the lifecycle status, and say what the chosen value means.
 *
 * This is the whole reason there is no /assets/{id}/edit route. The update
 * body is four optional fields, two of which (status, triage_notes) are
 * OUTPUTS of triage rather than things anyone types — a general edit form
 * would present `restored` as a free choice, inviting a unit marked repaired
 * with no triage record behind it. Narrowed to one control, with the meaning
 * of the selected value under it, the choice is at least an informed one.
 */
export function AssetStatusControl({
  assetId,
  status,
}: {
  assetId: string;
  status: string;
}) {
  const { hasWrite, reportAuthFailure } = useAuth();
  const { showSuccess } = useToast();
  const queryClient = useQueryClient();
  const info = assetStatusInfo(status);

  const mutation = useMutation({
    mutationFn: (next: string) => updateAsset(assetId, { status: next }),
    onSuccess: (asset) => {
      showSuccess(`Status set to ${assetStatusInfo(asset.status).label}`);
      void queryClient.invalidateQueries({
        queryKey: ["asset-detail", assetId],
      });
      void queryClient.invalidateQueries({ queryKey: ["asset-list"] });
    },
    onError: reportAuthFailure,
  });

  if (!hasWrite) {
    return (
      <div>
        <p className="text-sm text-foreground">{info.label}</p>
        <p className={CAPTION}>{info.meaning}</p>
      </div>
    );
  }

  return (
    <div>
      <label className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="whitespace-nowrap">Status</span>
        <select
          value={status}
          disabled={mutation.isPending}
          onChange={(e) => mutation.mutate(e.target.value)}
          className={`${FIELD_SM} text-foreground focus:outline-none focus:ring-2 focus:ring-ring`}
        >
          {ASSET_STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
          {/* A status the app has not heard of stays selectable rather than
              silently switching the unit to whatever sorts first. */}
          {!ASSET_STATUSES.some((s) => s.value === status) && (
            <option value={status}>{info.label}</option>
          )}
        </select>
      </label>
      <p className={cn(CAPTION, "mt-1")}>{info.meaning}</p>
      {mutation.isError && (
        <p className={cn(CAPTION, "mt-1 text-destructive")} role="alert">
          {(mutation.error as Error).message}
        </p>
      )}
    </div>
  );
}
