"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { extractOkhRequirements } from "@/api/ohm/okh";
import type { OkhManifest } from "@/types/okh";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/states";
import { PANEL, PANEL_BODY } from "@/components/ui/surface";
import { BODY_MUTED, CAPTION, CARD_TITLE } from "@/components/ui/typography";
import { cn } from "@/lib/utils";

/**
 * What matching will actually look for in this design.
 *
 * A design's process requirements are derived, not authored, so the manifest
 * page can show every field it holds and still not answer "why did this not
 * match anything?". This is the answer, and it belongs beside Validate rather
 * than on the match page — it is a fact about the design.
 *
 * On demand: extraction is a POST of the whole manifest for a panel most
 * readers will not open.
 */
export function RequirementsDisclosure({ okh }: { okh: OkhManifest }) {
  const [open, setOpen] = useState(false);

  const query = useQuery({
    queryKey: ["okh-requirements", okh.id],
    queryFn: () =>
      extractOkhRequirements(okh as unknown as Record<string, unknown>),
    enabled: open,
    staleTime: 0,
  });

  return (
    <section aria-labelledby="requirements" className={cn(PANEL, PANEL_BODY)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="requirements" className={CARD_TITLE}>
          Requirements
        </h2>
        <Button variant="outline" size="sm" onClick={() => setOpen((v) => !v)}>
          {open ? "Hide" : "What will matching look for?"}
        </Button>
      </div>

      {open && (
        <div className="mt-3">
          {query.isPending ? (
            <p className={CAPTION}>Reading the manifest…</p>
          ) : query.isError ? (
            <ErrorState
              title="Could not read requirements"
              description={(query.error as Error)?.message}
              onRetry={() => void query.refetch()}
            />
          ) : (query.data?.length ?? 0) === 0 ? (
            <p className={BODY_MUTED}>
              This design declares no process requirements, so a match has
              nothing to look for — which is usually why one returns everything,
              or nothing.
            </p>
          ) : (
            <ul className="space-y-1">
              {query.data?.map((requirement, i) => {
                const name =
                  (requirement as { process_name?: string }).process_name ??
                  `Requirement ${i + 1}`;
                return (
                  <li
                    key={`${name}-${i}`}
                    className="flex flex-wrap items-center gap-2 text-sm"
                  >
                    <span className="text-foreground">{name}</span>
                    {(requirement as { quantity?: number }).quantity !=
                      null && (
                      <Badge>
                        ×{(requirement as { quantity?: number }).quantity}
                      </Badge>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
