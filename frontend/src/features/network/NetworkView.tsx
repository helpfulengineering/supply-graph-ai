"use client";

import { FacilitiesIllustration } from "../../components/ui/illustrations";
import { FIELD, LABEL } from "../../components/ui/field";
import { PageHero } from "../../components/layout/PageHero";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  fetchNetworkSpaces,
  type NetworkFilters as Filters,
} from "../../api/ohm/network";
import { Button } from "../../components/ui/button";
import { deriveFilterOptions } from "./deriveFilterOptions";
import { filterByName } from "./nameSearch";
import { buildNetworkSummary } from "./networkSummary";
import { NetworkFilters } from "./NetworkFilters";
import { NetworkSpaceCard } from "./NetworkSpaceCard";
import { NetworkMap } from "./NetworkMapLazy";
import {
  LoadingState,
  EmptyState,
  ErrorState,
} from "../../components/ui/states";
import { Pagination } from "../../components/ui/Pagination";
import { useAuth } from "../../context/AuthContext";
import { cn } from "@/lib/utils";
import { SeedPeerCta } from "./SeedPeerCta";

const PAGE_SIZE = 24;

function ViewToggle({
  view,
  onChange,
}: {
  view: "list" | "map";
  onChange: (v: "list" | "map") => void;
}) {
  return (
    <div
      role="group"
      aria-label="View"
      className="inline-flex overflow-hidden rounded-md border border-input"
    >
      {(["list", "map"] as const).map((v) => (
        <button
          key={v}
          type="button"
          aria-pressed={view === v}
          onClick={() => onChange(v)}
          className={cn(
            "px-3 py-1.5 text-sm capitalize transition-colors",
            view === v
              ? "bg-primary text-primary-foreground"
              : "bg-background text-foreground hover:bg-accent",
          )}
        >
          {v}
        </button>
      ))}
    </div>
  );
}

export function NetworkView() {
  const router = useRouter();
  const { hasWrite } = useAuth();
  const [filters, setFilters] = useState<Filters>({});
  const [view, setView] = useState<"list" | "map">("list");
  const [page, setPage] = useState(1);
  const [nameQuery, setNameQuery] = useState("");

  // Carry the active filter into the match flow: pick a design there, match
  // against exactly this filtered network (local ∪ MoM).
  const matchAgainstThese = () => {
    const params = new URLSearchParams({ network: "1" });
    for (const [key, value] of Object.entries(filters)) {
      if (value) params.set(key, String(value));
    }
    router.push(`/match?${params.toString()}`);
  };

  const activeCount = Object.values(filters).filter(Boolean).length;
  const hasFilters = activeCount > 0;
  const createHref = hasWrite ? "/facilities/new" : "/settings/session";
  const createLabel = hasWrite ? "New facility" : "Connect API key";

  // Baseline (unfiltered) powers the filter options + the no-filter display.
  const baseline = useQuery({
    queryKey: ["network", "baseline"],
    queryFn: () => fetchNetworkSpaces({}),
  });
  // Server-side filtered display — only fetched when a filter is active.
  const filtered = useQuery({
    queryKey: ["network", filters],
    queryFn: () => fetchNetworkSpaces(filters),
    enabled: hasFilters,
  });

  const active = hasFilters ? filtered : baseline;
  const data = active.data;
  // Name search runs client-side over whatever the server returned, so it
  // composes with the filters above and costs no round trip — the map already
  // holds every space in memory to draw them.
  const spaces = useMemo(
    () => filterByName(data?.spaces ?? [], nameQuery),
    [data, nameQuery],
  );
  const options = useMemo(
    () => deriveFilterOptions(baseline.data?.spaces ?? []),
    [baseline.data],
  );

  const totalPages = Math.max(1, Math.ceil(spaces.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = spaces.slice(
    (safePage - 1) * PAGE_SIZE,
    safePage * PAGE_SIZE,
  );

  const applyFilters = (next: Filters) => {
    setFilters(next);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <PageHero
        title="Network"
        crumb="local · federated · filtered"
        actions={
          <Button
            title={
              hasWrite
                ? undefined
                : "Connect a write-capable API key first (opens Session)"
            }
            onClick={() => router.push(createHref)}
          >
            {createLabel}
          </Button>
        }
      />

      <SeedPeerCta />

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <aside className="space-y-4">
          {/*
            First control in the sidebar, above the filters: the site's primary
            call to action is "find your workshop on the map", and among several
            thousand spaces typing a name is what a person tries first.
          */}
          <div>
            <label
              htmlFor="space-name-search"
              className={LABEL}
            >
              Search by name
            </label>
            <input
              id="space-name-search"
              type="search"
              value={nameQuery}
              placeholder="e.g. FabLab Lyon"
              onChange={(e) => {
                setNameQuery(e.target.value);
                setPage(1);
              }}
              className={FIELD}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Matches name, city, and country.
            </p>
          </div>

          <NetworkFilters
            filters={filters}
            options={options}
            activeCount={activeCount}
            onChange={applyFilters}
            onClear={() => applyFilters({})}
          />
        </aside>

        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            {data && (
              <p className="text-sm text-muted-foreground">
                {buildNetworkSummary(data)}
              </p>
            )}
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={matchAgainstThese}>
                Match a design against these
              </Button>
              <ViewToggle view={view} onChange={setView} />
            </div>
          </div>

          {active.isLoading && <LoadingState message="Loading network…" />}
          {active.isError && (
            <ErrorState
              description={
                active.error instanceof Error
                  ? active.error.message
                  : "Failed to load the network."
              }
              onRetry={() => active.refetch()}
            />
          )}

          {!active.isLoading && !active.isError && spaces.length === 0 && (
            <EmptyState
              icon={<FacilitiesIllustration className="h-10 w-10" />}
              title={hasFilters ? "No spaces match" : "No spaces yet"}
              description={
                hasFilters
                  ? "Try loosening the filters."
                  : hasWrite
                    ? "Create your first local facility to get started."
                    : "Connect a write-capable API key, then create a facility."
              }
              action={
                hasFilters ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => applyFilters({})}
                  >
                    Clear filters
                  </Button>
                ) : (
                  <Button size="sm" onClick={() => router.push(createHref)}>
                    {createLabel}
                  </Button>
                )
              }
            />
          )}

          {!active.isLoading &&
            !active.isError &&
            spaces.length > 0 &&
            (view === "map" ? (
              <div className="h-[520px] overflow-hidden rounded-xl border border-border">
                <NetworkMap spaces={spaces} />
              </div>
            ) : (
              <>
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {pageItems.map((s) => (
                    <NetworkSpaceCard key={`${s.source}-${s.id}`} space={s} />
                  ))}
                </div>
                <Pagination
                  page={safePage}
                  totalPages={totalPages}
                  totalItems={spaces.length}
                  pageSize={PAGE_SIZE}
                  onPage={setPage}
                />
              </>
            ))}
        </div>
      </div>
    </div>
  );
}
