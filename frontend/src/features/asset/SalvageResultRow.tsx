"use client";

import Link from "next/link";
import type { SalvageMatchItem } from "@/api/ohm/asset";
import { Badge } from "@/components/ui/Badge";
import { CHROME_LINK } from "@/components/layout/chromeLink";
import { CAPTION } from "@/components/ui/typography";
import { PANEL_INSET } from "@/components/ui/surface";
import { cn } from "@/lib/utils";
import { ClaimControl } from "./ClaimControl";
import { claimState } from "./claimState";
import { conditionInfo } from "./componentCondition";

/** One harvestable component, on the unit it currently sits in. */
export function SalvageResultRow({
  match,
  now,
  onClaimed,
}: {
  match: SalvageMatchItem;
  now: number;
  onClaimed?: () => void;
}) {
  const claim = claimState(match, now);
  const condition = conditionInfo(match.condition);

  return (
    <div
      className={cn(PANEL_INSET, "flex flex-wrap items-center gap-x-3 gap-y-2")}
    >
      <span className="text-sm font-medium text-foreground">
        {match.component_name}
      </span>
      <Badge variant={condition.tone}>{condition.label}</Badge>
      {match.part_number && (
        <span className={cn(CAPTION, "font-mono")}>{match.part_number}</span>
      )}
      <span className="min-w-0 flex-1 truncate text-sm text-muted-foreground">
        in{" "}
        <Link href={`/assets/${match.asset_id}`} className={CHROME_LINK}>
          {match.asset_tag}
        </Link>
        {match.location ? ` · ${match.location}` : ""}
      </span>
      {claim.claimed ? (
        <span className={cn(CAPTION, "shrink-0")}>{claim.label}</span>
      ) : (
        <ClaimControl
          assetId={match.asset_id}
          componentName={match.component_name}
          onClaimed={onClaimed}
        />
      )}
    </div>
  );
}
