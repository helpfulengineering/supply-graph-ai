"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ApiError } from "@/api/ohm/client";
import { claimComponent } from "@/api/ohm/asset";
import { Button } from "@/components/ui/button";
import { FIELD_SM } from "@/components/ui/field";
import { CAPTION } from "@/components/ui/typography";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils";

/**
 * Reserve a component on another unit for retrieval.
 *
 * An inline disclosure rather than a dialog. The app has three hand-rolled
 * `role="dialog"` blocks and no shared Dialog primitive, so a fourth would be
 * a fourth focus trap to get right — and this control appears once per row in
 * a list that can be long, where a modal per row is the wrong shape anyway.
 *
 * A 409 is rendered as STATE, not as an error. Claims lapse after 48h and the
 * server checks that lazily, so two coordinators reading the same list can
 * both see a part as free; the second one to press is not at fault and should
 * not be shown a failure.
 */
export function ClaimControl({
  assetId,
  componentName,
  onClaimed,
}: {
  assetId: string;
  componentName: string;
  onClaimed?: () => void;
}) {
  const { hasWrite, user, reportAuthFailure } = useAuth();
  const { showSuccess } = useToast();
  const [open, setOpen] = useState(false);
  const [claimedBy, setClaimedBy] = useState(user?.name ?? "");
  const [conflict, setConflict] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => claimComponent(assetId, componentName, claimedBy.trim()),
    onSuccess: (result) => {
      setOpen(false);
      setConflict(null);
      showSuccess(`Claimed ${componentName}`, {
        description: `Reserved for ${result.claimed_by}. Claims lapse after 48 hours.`,
      });
      onClaimed?.();
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        setConflict(error.message);
        onClaimed?.();
        return;
      }
      reportAuthFailure(error);
    },
  });

  if (!hasWrite) return null;

  if (conflict) {
    return (
      <span className={cn(CAPTION, "text-warning-ink")} role="status">
        {conflict}
      </span>
    );
  }

  if (!open) {
    return (
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        Claim
      </Button>
    );
  }

  return (
    <form
      className="flex flex-wrap items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (claimedBy.trim()) mutation.mutate();
      }}
    >
      <label className="sr-only" htmlFor={`claim-${assetId}-${componentName}`}>
        Who is claiming {componentName}
      </label>
      <input
        id={`claim-${assetId}-${componentName}`}
        value={claimedBy}
        onChange={(e) => setClaimedBy(e.target.value)}
        placeholder="Your name"
        className={`${FIELD_SM} text-foreground focus:outline-none focus:ring-2 focus:ring-ring`}
      />
      <Button
        type="submit"
        size="sm"
        disabled={!claimedBy.trim() || mutation.isPending}
      >
        {mutation.isPending ? "Claiming…" : "Confirm"}
      </Button>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => setOpen(false)}
      >
        Cancel
      </Button>
      {mutation.isError &&
        !(
          mutation.error instanceof ApiError && mutation.error.status === 409
        ) && (
          <span className={cn(CAPTION, "text-destructive")} role="alert">
            {(mutation.error as Error).message}
          </span>
        )}
    </form>
  );
}
