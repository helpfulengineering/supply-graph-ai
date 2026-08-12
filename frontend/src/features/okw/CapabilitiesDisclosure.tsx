"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { extractOkwCapabilities } from "@/api/ohm/okw";
import type { OkwFacility } from "@/types/okw";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/states";
import { PANEL, PANEL_BODY } from "@/components/ui/surface";
import { BODY_MUTED, CAPTION, CARD_TITLE } from "@/components/ui/typography";
import { cn } from "@/lib/utils";

/**
 * What matching sees this facility as able to do.
 *
 * The mirror of the design page's Requirements panel, and the other half of
 * explaining a match: between them they say what was asked for and what was
 * offered, which is the pair a reader needs when the answer surprised them.
 */
export function CapabilitiesDisclosure({
  facility,
}: {
  facility: OkwFacility;
}) {
  const [open, setOpen] = useState(false);

  const query = useQuery({
    queryKey: ["okw-capabilities", facility.id],
    queryFn: () =>
      extractOkwCapabilities(facility as unknown as Record<string, unknown>),
    enabled: open,
    staleTime: 0,
  });

  return (
    <section aria-labelledby="capabilities" className={cn(PANEL, PANEL_BODY)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="capabilities" className={CARD_TITLE}>
          Capabilities
        </h2>
        <Button variant="outline" size="sm" onClick={() => setOpen((v) => !v)}>
          {open ? "Hide" : "What does matching see?"}
        </Button>
      </div>

      {open && (
        <div className="mt-3">
          {query.isPending ? (
            <p className={CAPTION}>Reading the record…</p>
          ) : query.isError ? (
            <ErrorState
              title="Could not read capabilities"
              description={(query.error as Error)?.message}
              onRetry={() => void query.refetch()}
            />
          ) : (query.data?.length ?? 0) === 0 ? (
            <p className={BODY_MUTED}>
              Matching derives no capabilities from this record, so it will not
              be returned for any design — usually because no equipment or
              process is listed.
            </p>
          ) : (
            <ul className="space-y-1">
              {query.data?.map((capability, i) => {
                const name =
                  (capability as { process_name?: string; name?: string })
                    .process_name ??
                  (capability as { name?: string }).name ??
                  `Capability ${i + 1}`;
                return (
                  <li key={`${name}-${i}`} className="text-sm text-foreground">
                    {name}
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
