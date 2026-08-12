"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { CAPTION } from "@/components/ui/typography";
import { cn } from "@/lib/utils";
import type { AssetRow } from "./assetListModel";
import { assetStatusInfo } from "./assetStatus";
import { lastTriagedLabel } from "./triageProgress";

/**
 * One unit in the fleet.
 *
 * The whole row is the link, at `min-h-11`, because this is a queue read on a
 * phone in a workshop — a 24px text target inside a row would be the wrong
 * affordance for the primary action on the page.
 *
 * The design is named but not linked. A link inside a link is not a thing the
 * markup can express, and the design is one tap away from the detail page
 * this row leads to.
 */
export function AssetListRow({ row, now }: { row: AssetRow; now: number }) {
  const { asset, designTitle, progress } = row;
  const status = assetStatusInfo(asset.status);
  const triaged = lastTriagedLabel(asset.last_triaged_at, now);

  return (
    <Link
      href={`/assets/${asset.id}`}
      className="flex min-h-11 flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-border px-3 py-2 no-underline transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {/* Mono because an asset tag is a code read off a label, not a name. */}
      <span className="font-mono text-sm font-medium text-foreground">
        {asset.asset_tag}
      </span>
      <span className="min-w-0 flex-1 truncate text-sm text-muted-foreground">
        {designTitle}
      </span>
      {asset.location && (
        <span className={cn(CAPTION, "shrink-0")}>{asset.location}</span>
      )}
      <span className={cn(CAPTION, "shrink-0")}>
        {triaged ? `${progress.label} · ${triaged}` : progress.label}
      </span>
      <Badge variant={status.tone}>{status.label}</Badge>
    </Link>
  );
}
