"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { resolveSourcing } from "@/api/ohm/asset";
import { Button } from "@/components/ui/button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { CHROME_LINK } from "@/components/layout/chromeLink";
import { PANEL, PANEL_BODY, PANEL_INSET } from "@/components/ui/surface";
import { BODY_MUTED, CAPTION } from "@/components/ui/typography";
import { cn } from "@/lib/utils";
import { ClaimControl } from "./ClaimControl";
import { claimState } from "./claimState";
import { splitSourcing, sourcingUnavailableReason } from "./sourcingModel";

/**
 * Where the parts this unit needs could come from.
 *
 * Behind a button, deliberately. The endpoint builds the triage report and then
 * runs one fleet-wide salvage scan per component marked source_new — an O(n)
 * fan-out that would fire on every visit to this page, for a section that says
 * nothing until triage has happened.
 */
export function SourcingPanel({
  assetId,
  lastTriagedAt,
  sourceNewCount,
}: {
  assetId: string;
  lastTriagedAt: string | null | undefined;
  sourceNewCount: number | null;
}) {
  const [requested, setRequested] = useState(false);
  const unavailable = sourcingUnavailableReason(lastTriagedAt, sourceNewCount);

  const query = useQuery({
    queryKey: ["asset-sourcing", assetId],
    queryFn: () => resolveSourcing(assetId),
    enabled: requested && !unavailable,
    staleTime: 0,
  });

  // The moment the data was current, not the moment of render: every "3 days
  // ago" on the page is then relative to the same fetch, and re-rendering for
  // an unrelated reason cannot make two rows disagree.
  const now = query.dataUpdatedAt || Date.now();
  const split = query.data ? splitSourcing(query.data) : null;

  return (
    <section aria-labelledby="sourcing" className={cn(PANEL, PANEL_BODY)}>
      <SectionHeading id="sourcing" role="card">
        Sourcing
      </SectionHeading>

      {!requested || unavailable ? (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            disabled={Boolean(unavailable)}
            title={unavailable ?? undefined}
            onClick={() => setRequested(true)}
          >
            Resolve sourcing
          </Button>
          <span className={CAPTION}>
            {unavailable ??
              "Checks the fleet for each part this unit needs. Takes a moment."}
          </span>
        </div>
      ) : query.isPending ? (
        <LoadingState message="Checking the fleet…" />
      ) : query.isError ? (
        <ErrorState
          title="Could not resolve sourcing"
          description={(query.error as Error)?.message}
          onRetry={() => void query.refetch()}
        />
      ) : split?.empty ? (
        <p className={cn(BODY_MUTED, "mt-3")}>
          Triage found no components needing a replacement part.
        </p>
      ) : (
        <div className="mt-4 space-y-5">
          {split && split.fleetAvailable.length > 0 && (
            <div>
              <p className="text-sm font-medium text-foreground">
                Available in the fleet
              </p>
              <p className={CAPTION}>
                Another unit has one of these. Claim it to reserve it for 48
                hours.
              </p>
              <div className="mt-2 space-y-2">
                {split.fleetAvailable.map((row) => (
                  <div key={row.item.component_name} className={PANEL_INSET}>
                    <p className="text-sm font-medium text-foreground">
                      {row.item.component_name}
                      {row.item.part_number ? (
                        <span className={cn(CAPTION, "ml-2 font-mono")}>
                          {row.item.part_number}
                        </span>
                      ) : null}
                    </p>
                    <ul className="mt-2 space-y-1">
                      {row.matches.map((match) => {
                        const claim = claimState(match, now);
                        return (
                          <li
                            key={`${match.asset_id}:${match.component_name}`}
                            className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm"
                          >
                            <Link
                              href={`/assets/${match.asset_id}`}
                              className={CHROME_LINK}
                            >
                              {match.asset_tag}
                            </Link>
                            {match.location && (
                              <span className={CAPTION}>{match.location}</span>
                            )}
                            {claim.claimed ? (
                              <span className={CAPTION}>{claim.label}</span>
                            ) : (
                              <ClaimControl
                                assetId={match.asset_id}
                                componentName={match.component_name}
                                onClaimed={() => void query.refetch()}
                              />
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}

          {split && split.procureNew.length > 0 && (
            <div>
              <p className="text-sm font-medium text-foreground">Procure new</p>
              <p className={CAPTION}>
                Nothing in the fleet matched. The search was scoped to this
                design and the ones it declares compatible — a wider search may
                still find one.
              </p>
              <ul className="mt-2 space-y-1">
                {split.procureNew.map((row) => (
                  <li
                    key={row.item.component_name}
                    className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm"
                  >
                    <span className="font-medium text-foreground">
                      {row.item.component_name}
                    </span>
                    {row.item.part_number && (
                      <span className={cn(CAPTION, "font-mono")}>
                        {row.item.part_number}
                      </span>
                    )}
                    <Link
                      href={`/assets/salvage?component=${encodeURIComponent(row.item.component_name)}`}
                      className={CHROME_LINK}
                    >
                      Search the whole fleet
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
