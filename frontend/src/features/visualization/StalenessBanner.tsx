"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  extendSolutionTtl,
  fetchSolutionStaleness,
} from "@/api/ohm/supply-tree";
import { Button } from "@/components/ui/button";
import { PANEL_WARNING } from "@/components/ui/surface";
import { CAPTION } from "@/components/ui/typography";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils";

/** What "keep this" means, in days. Long enough to be worth pressing once. */
const EXTEND_DAYS = 30;

/**
 * A saved solution ages out, and until now nothing said so.
 *
 * Solutions carry a server-side TTL: one could expire under a reader who had
 * bookmarked it, with no warning and no way to prevent it. This turns an
 * invisible server behaviour into something a caller can act on.
 *
 * A banner rather than a modal — the tree below is perfectly readable while
 * stale, and interrupting a page someone came to read to tell them it still
 * works would be the wrong trade. Silent when the solution is fresh, and
 * silent when the endpoint is unavailable: a node that cannot answer is not a
 * reason to worry someone.
 */
export function StalenessBanner({ solutionId }: { solutionId: string }) {
  const queryClient = useQueryClient();
  const { showSuccess } = useToast();

  const staleness = useQuery({
    queryKey: ["solution-staleness", solutionId],
    queryFn: () => fetchSolutionStaleness(solutionId),
    retry: false,
    retryOnMount: false,
  });

  const extend = useMutation({
    mutationFn: () => extendSolutionTtl(solutionId, EXTEND_DAYS),
    onSuccess: () => {
      showSuccess(`Kept for another ${EXTEND_DAYS} days`);
      void queryClient.invalidateQueries({
        queryKey: ["solution-staleness", solutionId],
      });
      void queryClient.invalidateQueries({ queryKey: ["solutions"] });
    },
  });

  if (staleness.isError || !staleness.data?.is_stale) return null;

  const { staleness_reason, age_days } = staleness.data;

  return (
    <div
      role="status"
      className={cn(
        PANEL_WARNING,
        "mb-4 flex flex-wrap items-center gap-3 p-3",
      )}
    >
      <p className="text-sm text-foreground">
        This solution is stale
        {age_days != null ? ` — saved ${age_days} days ago` : ""}. It may be
        removed the next time the node cleans up.
      </p>
      {staleness_reason && <span className={CAPTION}>{staleness_reason}</span>}
      <Button
        variant="outline"
        size="sm"
        className="ml-auto"
        disabled={extend.isPending}
        onClick={() => extend.mutate()}
      >
        {extend.isPending ? "Keeping…" : `Keep for another ${EXTEND_DAYS} days`}
      </Button>
      {extend.isError && (
        <span className={cn(CAPTION, "text-destructive")} role="alert">
          {(extend.error as Error).message}
        </span>
      )}
    </div>
  );
}
