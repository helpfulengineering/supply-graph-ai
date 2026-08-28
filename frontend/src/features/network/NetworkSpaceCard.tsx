"use client";

import { MapPin } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Badge } from "../../components/ui/Badge";
import type { NetworkSpace } from "../../api/ohm/network";
import { humanizeProcessId } from "./deriveFilterOptions";
import { SOURCE_STYLES } from "./networkSummary";
import { displayCountryName, displayRegionName } from "../match/geoDisplay";
import { PANEL } from "../../components/ui/surface";
import { CARD_TITLE } from "../../components/ui/typography";
import { ProcessChip } from "../../components/ui/ProcessChip";
import { cn } from "@/lib/utils";

const CARD_CLASS = `${PANEL} group flex h-full flex-col gap-3 no-underline shadow-sm transition-shadow hover:shadow-md`;

export function NetworkSpaceCard({ space }: { space: NetworkSpace }) {
  const location = [
    space.city,
    space.region ? displayRegionName(space.region) : null,
    space.country ? displayCountryName(space.country) : null,
  ]
    .filter(Boolean)
    .join(", ");
  // The raw id is kept alongside the label: the icon table is keyed by the
  // taxonomy id, and humanizing first would throw away what it matches on.
  const processes = (space.processes ?? []).map((id) => ({
    id,
    label: humanizeProcessId(id),
  }));

  const body = (
    <>
      <div>
        <div className="flex items-start justify-between gap-2">
          {/*
            `min-w-0 break-words` is the other half of the badge's
            `whitespace-nowrap`. A flex item's default `min-width: auto` is its
            min-content width, so a name carrying one long unbroken word —
            "die|frauenmöbelwerkstatt" — refuses to shrink and pushes the badge
            that must not wrap straight off the card's right edge.
          */}
          <h3
            className={cn(
              CARD_TITLE,
              "min-w-0 break-words group-hover:text-primary-ink",
            )}
          >
            {space.name || "Unnamed"}
          </h3>
          <Badge variant={space.source === "local" ? "indigo" : "green"}>
            {SOURCE_STYLES[space.source].label}
          </Badge>
        </div>
        {location && (
          <p className="mt-0.5 flex items-center gap-1.5 text-sm text-muted-foreground">
            <MapPin aria-hidden="true" className="h-3.5 w-3.5 shrink-0" />{" "}
            {location}
          </p>
        )}
        {space.ambiguous && (
          <p className="mt-1 text-xs text-warning">
            Ambiguous for the current filter (this source doesn’t report it)
          </p>
        )}
      </div>

      {processes.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {processes.slice(0, 4).map((p) => (
            <ProcessChip key={p.id} process={p.id} label={p.label} />
          ))}
          {processes.length > 4 && (
            <Badge variant="default">+{processes.length - 4}</Badge>
          )}
        </div>
      )}

      <span className="mt-auto text-sm font-medium text-primary-ink">
        {space.source === "local" ? "View facility →" : "Visit space ↗"}
      </span>
    </>
  );

  // Local facilities open their OHM detail page; MoM spaces link out (address /
  // contact live on the source's own page). A MoM space with no url isn't a link.
  if (space.source === "local") {
    return (
      <Link href={`/facilities/${space.id}`} className={CARD_CLASS}>
        {body}
      </Link>
    );
  }
  if (space.url) {
    return (
      <a
        href={space.url}
        target="_blank"
        rel="noreferrer"
        className={CARD_CLASS}
      >
        {body}
      </a>
    );
  }
  return <div className={CARD_CLASS}>{body as ReactNode}</div>;
}
