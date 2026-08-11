"use client";

import { MapPin } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Badge } from "../../components/ui/Badge";
import type { NetworkSpace } from "../../api/ohm/network";
import { humanizeProcessId } from "./deriveFilterOptions";
import { SOURCE_STYLES } from "./networkSummary";
import { displayCountryName, displayRegionName } from "../match/geoDisplay";

const CARD_CLASS =
  "group flex h-full flex-col gap-3 rounded-xl border border-border bg-card p-5 no-underline shadow-sm transition-shadow hover:shadow-md";

export function NetworkSpaceCard({ space }: { space: NetworkSpace }) {
  const location = [
    space.city,
    space.region ? displayRegionName(space.region) : null,
    space.country ? displayCountryName(space.country) : null,
  ]
    .filter(Boolean)
    .join(", ");
  const processes = (space.processes ?? []).map(humanizeProcessId);

  const body = (
    <>
      <div>
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-semibold text-foreground group-hover:text-primary-ink">
            {space.name || "Unnamed"}
          </h3>
          <Badge variant={space.source === "local" ? "indigo" : "green"}>
            {SOURCE_STYLES[space.source].label}
          </Badge>
        </div>
        {location && (
          <p className="mt-0.5 flex items-center gap-1.5 text-sm text-muted-foreground"><MapPin aria-hidden="true" className="h-3.5 w-3.5 shrink-0" /> {location}</p>
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
            <Badge key={p} variant="default">
              {p}
            </Badge>
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
