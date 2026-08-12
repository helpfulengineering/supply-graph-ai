import { useQuery } from "@tanstack/react-query";
import {
  DataProcessingIcon,
  InternetIcon,
  ReliabilityIcon,
  SmartFactoryIcon,
  type IconProps,
} from "../components/icons";
import type { JSX } from "react";
import { PageHero } from "../components/layout/PageHero";
import { BRAND_TAGLINE_LINKS } from "../../app/brand";
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
  sourceVar,
  UNPLOTTED_VAR,
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
 * The label is written, not hidden in the tooltip. On a phone the row was four
 * icons and four bare figures — 9, 3,193, 361, 0 — and a glyph is not a unit:
 * nothing on screen said which number was facilities and which was errors, and
 * the tooltip that knew is a hover the reader does not have. It stays for the
 * pointer, where it repeats the label rather than being the only place to find
 * it.
 *
 * The figure steps down a size below `sm`, because four numbers at h3 on a
 * 375px viewport wrapped to two lines and still left no room for their names.
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
      className="flex min-w-0 items-center gap-1.5 rounded-md px-1 py-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:gap-2"
    >
      {/* The world's accent as ink, not a flat grey: the figure beside it
          already carries the theme, and a muted icon read as a disabled
          control. --color-primary-ink is the accent tempered for use as text,
          which is what an icon at this weight is. */}
      <Icon
        aria-hidden="true"
        className="h-4 w-4 shrink-0 text-primary-ink sm:h-5 sm:w-5"
      />
      {/* Label under the figure on a phone, beside it from `sm`. Two of these
          share a 375px line, and inline the longer names ("Maps of Making",
          "Requests (1h)") were cut to "Maps …" — a label truncated to its
          first word names nothing. Stacked, each gets its own line and no
          ellipsis. */}
      <div className="flex min-w-0 flex-col sm:flex-row sm:items-baseline sm:gap-2">
        <p className={cn(STAT_VALUE, "text-h4 sm:text-h3")}>{value}</p>
        <p className={cn(CAPTION, "min-w-0 truncate leading-tight")}>{label}</p>
      </div>
    </div>
  );

  return (
    <Tooltip content={label} value={value}>
      {card}
    </Tooltip>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span
      className={cn(
        CAPTION,
        "inline-flex items-center gap-1.5 whitespace-nowrap",
      )}
    >
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
          backgroundColor: color,
          boxShadow: `0 0 8px color-mix(in srgb, ${color} 45%, transparent)`,
        }}
        aria-hidden="true"
      />
      {label}
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
        {/*
          The three terms are the three things the app holds, so they are the
          three places to start. They read as a tagline and were dead text, one
          line under the h1 and above a map, on the page a first-time visitor
          lands on.
        */}
        <PageHero title="Open Hardware Manager" crumb={BRAND_TAGLINE_LINKS} />
      </div>

      {/*
        Hero: the manufacturing network map, straight under the page title.
        Named by aria-label rather than a visible heading — a title reading
        "Manufacturing network" above a map of the manufacturing network is a
        caption for something that needs no caption, and it pushed the map down
        the fold. The landmark keeps its name for anyone navigating by one.
      */}
      <section aria-label="Manufacturing network">
        {/* `relative` here and not on the section: the section also holds the
            summary line under the map, so anchoring to it put the legend at
            the bottom of both. */}
        <div className="relative h-[440px] overflow-hidden rounded-lg border border-panel-border">
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

          {/*
            The key, on the map it describes. In the heading row it aligned to
            nothing — the right edge of a container the map did not share — and
            asked the reader to carry two colours down the page. Here each dot
            sits beside the dots it names.

            Bottom-right, lifted clear of Leaflet's attribution, which owns
            that corner. `pointer-events-none` so it never takes a click meant
            for a marker underneath, and a z-index above the tile and marker
            panes but below the zoom control.

            A column on a phone, a row from `sm`. Three entries side by side
            need about 340px and a 375px viewport does not have them once the
            map's own gutters are paid: the key spanned the full width, each
            label broke over two lines, and its left edge ran past the map and
            over the unplotted bucket in the opposite corner. Stacked, it is as
            wide as its longest label and stays in its own corner.
          */}
          {m && !map.isLoading && !map.isError && (
            <div
              className="pointer-events-none absolute bottom-7 right-2 flex max-w-[calc(100%-1rem)] flex-col gap-0.5 rounded-md border border-panel-border bg-card/90 px-2 py-1 sm:flex-row sm:gap-3"
              style={{ zIndex: 500 }}
            >
              <LegendDot
                color={sourceVar("local")}
                label={SOURCE_STYLES.local.label}
              />
              <LegendDot
                color={sourceVar("mom")}
                label={SOURCE_STYLES.mom.label}
              />
              {m.dropped_no_coords > 0 && (
                <LegendDot color={UNPLOTTED_VAR} label="Without coordinates" />
              )}
            </div>
          )}

          {/*
            The spaces the map cannot plot, drawn on the map anyway.

            They are in every count and at no coordinate, so a key entry alone
            described a colour that appeared nowhere. A bucket pinned to the
            corner gives them the one position that is honest — off the map,
            still on it — and puts the key's third colour where a reader can
            match it. Sized and shaped like a cluster, because that is what it
            is: a group of spaces that do not resolve to a point.
          */}
          {m && !map.isLoading && !map.isError && m.dropped_no_coords > 0 && (
            <span
              title={`${m.dropped_no_coords.toLocaleString()} ${
                m.dropped_no_coords === 1 ? "space has" : "spaces have"
              } no coordinates and cannot be placed`}
              className="absolute bottom-7 left-2 flex h-7 min-w-7 items-center justify-center rounded-full px-2 text-xs font-semibold tabular-nums"
              style={{
                zIndex: 500,
                backgroundColor: UNPLOTTED_VAR,
                color: "var(--card)",
                boxShadow: `0 0 0 2px color-mix(in srgb, ${UNPLOTTED_VAR} 35%, transparent)`,
              }}
            >
              {m.dropped_no_coords.toLocaleString()}
            </span>
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

        It does get a surface, though — the same 90% glass every panel on the
        page now carries. Without one this band was the only content sitting
        directly on the blueprint grid, so four large figures read against a
        ruling while everything above and below them rested on a sheet. Still
        no boxes: one surface for the row, not four.
      */}
      {/* Two columns on a phone, one line from `sm`. Wrapping a flex row let
          three figures sit on the first line and the fourth on its own, which
          reads as a stray rather than as the last of four. */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 rounded-lg border border-panel-border bg-card/90 px-3 py-2 backdrop-blur-md sm:flex sm:flex-wrap sm:items-center sm:gap-x-6">
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
