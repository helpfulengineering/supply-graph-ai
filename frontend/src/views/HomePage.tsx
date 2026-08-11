import { useQuery } from "@tanstack/react-query";
import {
  DataProcessingIcon,
  InternetIcon,
  ReliabilityIcon,
  AwarenessIcon,
  SmartFactoryIcon,
  type IconProps,
} from "../components/icons";
import type { JSX } from "react";
import { PageHero } from "../components/layout/PageHero";
import { fetchDomains, fetchMetrics } from "../api/ohm/utility";
import { fetchNetworkSpaces } from "../api/ohm/network";
import { Badge } from "../components/ui/Badge";
import { LoadingState, ErrorState } from "../components/ui/states";
import { NetworkMap } from "../features/network/NetworkMapLazy";
import { GettingStarted } from "../features/dashboard/GettingStarted";
import { NetworkBarChart } from "../features/dashboard/NetworkBarChart";
import {
  capabilityCoverage,
  facilitiesByCountry,
} from "../features/dashboard/networkStats";
import { SecurityPolicyBadge } from "../features/settings/SecurityPolicyBadge";
import { PANEL } from "../components/ui/surface";
import { Tooltip } from "../components/ui/Tooltip";
import { cn } from "@/lib/utils";
import {
  CAPTION,
  SECTION_LABEL_SM,
  SECTION_TITLE,
  STAT_VALUE,
} from "../components/ui/typography";
import {
  buildNetworkSummary,
  SOURCE_STYLES,
  sourceColor,
} from "../features/network/networkSummary";

/**
 * One figure on the dashboard.
 *
 * Icon beside the number rather than a number alone in a box: at four across,
 * each card was a short figure and a short label in the top-left of a wide
 * panel, and the rest was empty. The icon uses the width the card already
 * spends, and gives the row something to scan by other than reading each
 * label.
 *
 * The label lives in the tooltip, which opens on tap as well as on hover — see
 * components/ui/Tooltip. `aria-label` carries it for assistive tech either way.
 */
function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: (props: IconProps) => JSX.Element;
  label: string;
  value: string;
}) {
  const card = (
    <div
      tabIndex={0}
      role="group"
      aria-label={`${label}: ${value}`}
      className="flex items-center gap-2 rounded-md px-1 py-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {/* The world's accent as ink, not a flat grey: the figure beside it
          already carries the theme, and a muted icon read as a disabled
          control. --color-primary-ink is the accent tempered for use as text,
          which is what an icon at this weight is. */}
      <Icon aria-hidden="true" className="h-5 w-5 shrink-0 text-primary-ink" />
      <p className={STAT_VALUE}>{value}</p>
    </div>
  );

  return (
    <Tooltip content={label} value={value}>
      {card}
    </Tooltip>
  );
}

function LegendDot({ source }: { source: "local" | "mom" }) {
  return (
    <span className={cn(CAPTION, "inline-flex items-center gap-1.5")}>
      {/*
        Lit, not printed. The dot is the key to the map's two colours and it
        was a flat 10px circle next to grey text — the same hue the markers
        use, with none of their presence. The halo is the source colour at 45%,
        which is decoration and carries no contrast requirement, so it can use
        the undiluted colour the label beside it could not.
      */}
      <span
        className="h-2.5 w-2.5 rounded-full"
        style={{
          backgroundColor: sourceColor(source),
          boxShadow: `0 0 8px color-mix(in srgb, ${sourceColor(source)} 45%, transparent)`,
        }}
        aria-hidden="true"
      />
      {SOURCE_STYLES[source].label}
    </span>
  );
}

export function HomePage() {
  const map = useQuery({
    queryKey: ["network", "baseline"],
    queryFn: () => fetchNetworkSpaces(),
  });
  const spaces = map.data?.spaces ?? [];
  const domains = useQuery({ queryKey: ["domains"], queryFn: fetchDomains });
  // Metrics are more volatile than the catalog data; keep a short stale window.
  const metrics = useQuery({
    queryKey: ["metrics"],
    queryFn: fetchMetrics,
    staleTime: 60_000,
  });

  const online = !domains.isError && !metrics.isError;
  const m = map.data;

  return (
    <div className="space-y-3 sm:space-y-4">
      <div>
        <PageHero
          title="Open Hardware Manager"
          crumb="designs · facilities · supply chains"
        />
      </div>

      {/* Hero: the manufacturing network map. */}
      <section aria-labelledby="network-heading">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h2
            id="network-heading"
            className={cn(SECTION_TITLE, "flex items-center gap-2")}
          >
            <AwarenessIcon
              aria-hidden="true"
              className="h-5 w-5 shrink-0 text-primary-ink"
            />
            Manufacturing network
          </h2>
          <div className="flex gap-3">
            <LegendDot source="local" />
            <LegendDot source="mom" />
          </div>
        </div>

        <div className="h-[440px] overflow-hidden rounded-xl border border-border">
          {map.isLoading && <LoadingState message="Loading the network map…" />}
          {map.isError && (
            <ErrorState
              description={
                map.error instanceof Error
                  ? map.error.message
                  : "Failed to load the map."
              }
              onRetry={() => map.refetch()}
            />
          )}
          {m && !map.isLoading && !map.isError && (
            <NetworkMap spaces={m.spaces} />
          )}
        </div>

        {m && (
          <p className="mt-2 text-sm text-muted-foreground">
            {buildNetworkSummary(m)}
          </p>
        )}
      </section>

      {/* Network + system stats. */}
      {/*
        One row, no boxes. Four short figures in four bordered cards spent a
        border, a margin and 16px of padding each to carry a number and a
        glyph — the whole band below the map for four values that fit on one
        line. They are a readout, not four sections.
      */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <StatCard
          icon={SmartFactoryIcon}
          label="OHM facilities"
          value={(m?.local_count ?? 0).toLocaleString()}
        />
        <StatCard
          icon={InternetIcon}
          label="Maps of Making"
          value={m?.mom_available ? (m?.mom_count ?? 0).toLocaleString() : "—"}
        />
        <StatCard
          icon={DataProcessingIcon}
          label="Requests (1h)"
          value={(metrics.data?.recent_requests_1h ?? 0).toLocaleString()}
        />
        <StatCard
          icon={ReliabilityIcon}
          label="Errors"
          value={(metrics.data?.total_errors ?? 0).toLocaleString()}
        />
      </div>

      {/*
        Derived from the space set the map above already loaded — no extra
        request. The counts answer the two questions the map shape raises but
        cannot: where the network actually concentrates, and what it can make.
      */}
      {spaces.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          <NetworkBarChart
            title="Where the network is"
            caption="Facilities by country"
            rows={facilitiesByCountry(spaces)}
            seriesIndex={0}
            noun="countries"
            hrefFor={(r) => `/facilities?country=${encodeURIComponent(r.key)}`}
          />
          <NetworkBarChart
            title="What it can make"
            caption="Facilities offering each capability"
            rows={capabilityCoverage(spaces)}
            seriesIndex={1}
            noun="capabilities"
            hrefFor={(r) => `/facilities?process=${encodeURIComponent(r.key)}`}
          />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <GettingStarted />
        </div>

        <div className="space-y-4">
          <section aria-labelledby="system-heading">
            <h2 id="system-heading" className={cn(SECTION_TITLE, "mb-3")}>
              System
            </h2>
            <div className={cn(PANEL, "space-y-3")}>
              <div className="flex items-center gap-2">
                <span
                  className={`h-2.5 w-2.5 rounded-full ${online ? "bg-success" : "bg-destructive"}`}
                  aria-hidden="true"
                />
                <span className="text-sm text-foreground">
                  {online ? "API online" : "API unreachable"}
                </span>
              </div>
              <div>
                <p className={cn(SECTION_LABEL_SM, "mb-1.5")}>Domains</p>
                <div className="flex flex-wrap gap-1.5">
                  {(domains.data ?? []).map((d) => (
                    <Badge key={d.id} variant="blue">
                      {d.name}
                    </Badge>
                  ))}
                  {domains.isLoading && (
                    <span className="text-xs text-muted-foreground">
                      loading…
                    </span>
                  )}
                </div>
              </div>
              <div>
                <p className={cn(SECTION_LABEL_SM, "mb-1.5")}>Security</p>
                <SecurityPolicyBadge />
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
