"use client";

import { FacilitiesIllustration } from "../../components/ui/illustrations";
import { FIELD, LABEL } from "../../components/ui/field";
import { PageHero } from "../../components/layout/PageHero";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  fetchNetworkSpaces,
  type NetworkFilters as Filters,
  type NetworkSpace,
} from "../../api/ohm/network";
import { CAPTION } from "../../components/ui/typography";
import { Button } from "../../components/ui/button";
import { deriveFilterOptions } from "./deriveFilterOptions";
import { filterUpdates, filtersFromParams, sameFilters } from "./filterParams";
import {
  mergeParams,
  oneOf,
  pageFromParam,
  toSearch,
} from "../../lib/urlState";
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
import { SeedPeerCta } from "./SeedPeerCta";
import { SegmentedControl } from "../../components/ui/SegmentedControl";

const PAGE_SIZE = 24;

const VIEW_OPTIONS = [
  { value: "list" as const, label: "List" },
  { value: "map" as const, label: "Map" },
];

function ViewToggle({
  view,
  onChange,
}: {
  view: "list" | "map";
  onChange: (v: "list" | "map") => void;
}) {
  // Was a hand-rolled twin of the match page's mode switch, down to the class
  // string, but wearing role="group"/aria-pressed instead of a radio group —
  // two spellings of one concept that also disagreed about what the concept
  // was. It is a one-of-N choice, so it is a radio group.
  return (
    <SegmentedControl
      label="View"
      value={view}
      options={VIEW_OPTIONS}
      onChange={onChange}
    />
  );
}

/** How long typing has to pause before the address catches up. */
const NAME_QUERY_SYNC_MS = 250;

export function NetworkView() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { hasWrite } = useAuth();
  // Seeded from the query string so the surface can be linked into — the
  // dashboard charts arrive here with a country or a process already chosen —
  // then owned locally, with the address bar kept in step by applyFilters.
  const [filters, setFilters] = useState<Filters>(() =>
    filtersFromParams(searchParams),
  );
  // View and page live in the address too, so a link reopens what the sender
  // was looking at rather than page 1 of the list.
  const [view, setView] = useState<"list" | "map">(() =>
    oneOf(searchParams.get("view"), ["list", "map"] as const, "list"),
  );
  const [page, setPage] = useState(() =>
    pageFromParam(searchParams.get("page")),
  );
  const [nameQuery, setNameQuery] = useState(() => searchParams.get("q") ?? "");

  /**
   * Adopt the address when it changes underneath this component.
   *
   * The state above is seeded from the query string and then owned locally,
   * which held while this view was the only thing writing to it. It is not: the
   * hero crumb links to `?source=...`, and Back restores an earlier filter.
   * Both replace the query string on the same route, so React never remounts
   * and a seed-once initialiser never sees them — the address changed and the
   * surface did not. The crumb links were dead on arrival because of it: the
   * URL moved, the underline and focus ring said "link", and the list stayed
   * exactly as it was.
   *
   * Guarded on a real difference so the write path does not feed itself.
   * applyFilters sets state and then calls syncUrl, which lands back here with
   * the values it just wrote; `sameFilters` keeps that from handing React a new
   * object and re-keying the filtered query for no change.
   *
   * Filters only, deliberately. View, page, and the name query are written by
   * this component alone, and `router.replace` lands asynchronously: adopting
   * `q` here means that while someone types "ab", the navigation carrying "a"
   * arrives afterwards and sets the box back to "a". Nothing outside the
   * component sets those three on this route — a link from elsewhere is a
   * different route and mounts the view fresh, which the initialisers already
   * handle.
   */
  useEffect(() => {
    setFilters((prev) => {
      const next = filtersFromParams(searchParams);
      return sameFilters(prev, next) ? prev : next;
    });
  }, [searchParams]);

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

  /**
   * What the map currently frames, or null before it has reported.
   *
   * Map view lists the spaces under the map rather than beside it, and the
   * question the list answers there is "which ones are these" — about the part
   * of the world on screen, not about all 3,000. Panning is the selection.
   */
  const [inView, setInView] = useState<NetworkSpace[] | null>(null);
  const onVisibleChange = useCallback((visible: NetworkSpace[]) => {
    setInView(visible);
    // A new region is a new list; page 3 of the last one means nothing here.
    // Not written to the address: the viewport is not in the query string, so
    // a page number pinned to it would not survive being linked anyway.
    setPage(1);
  }, []);

  const listed = view === "map" ? (inView ?? spaces) : spaces;
  const totalPages = Math.max(1, Math.ceil(listed.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = listed.slice(
    (safePage - 1) * PAGE_SIZE,
    safePage * PAGE_SIZE,
  );

  /**
   * Write the surface's own state back to the address, keeping everything it
   * does not own — the look rides in the same query string.
   *
   * Replace, not push: narrowing a filter is a refinement, not a step to go
   * back from.
   */
  const syncUrl = useCallback(
    (updates: Record<string, string | number | null>) => {
      const qs = mergeParams(new URLSearchParams(searchParams), updates);
      router.replace(`${pathname}${toSearch(qs)}`, { scroll: false });
    },
    [router, pathname, searchParams],
  );

  const applyFilters = (next: Filters) => {
    setFilters(next);
    setPage(1);
    syncUrl({ ...filterUpdates(next), page: null });
  };

  const applyView = (next: "list" | "map") => {
    setView(next);
    syncUrl({ view: next === "list" ? null : next });
  };

  const applyPage = (next: number) => {
    setPage(next);
    syncUrl({ page: next === 1 ? null : next });
  };

  /**
   * The address follows the search box, but not keystroke by keystroke.
   *
   * This wrote the URL on every character, so typing "FabLab Lyon" issued
   * eleven `router.replace` calls. The box is local state and stays instant
   * either way; what the writes buy is a shareable address, and an address is
   * only worth writing once the typing pauses.
   *
   * Eleven navigations for eleven characters is also unreliable, not merely
   * wasteful: under load the router coalesces them and the last one — the only
   * one carrying the complete query — can fail to land. Reproduced under
   * deliberate CPU contention, with the box correctly reading "Laser" and the
   * address stuck one character behind at `q=Lase`.
   *
   * Held in a ref so the pending write always uses the CURRENT syncUrl, which
   * closes over the latest search params. A timer capturing the callback at
   * schedule time would merge its update onto a snapshot taken a keystroke ago
   * and could drop a filter changed in between.
   */
  const syncUrlRef = useRef(syncUrl);
  useEffect(() => {
    syncUrlRef.current = syncUrl;
  }, [syncUrl]);

  const nameSyncTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(
    () => () => {
      if (nameSyncTimer.current) clearTimeout(nameSyncTimer.current);
    },
    [],
  );

  const applyNameQuery = (next: string) => {
    setNameQuery(next);
    setPage(1);
    if (nameSyncTimer.current) clearTimeout(nameSyncTimer.current);
    nameSyncTimer.current = setTimeout(() => {
      syncUrlRef.current({ q: next || null, page: null });
    }, NAME_QUERY_SYNC_MS);
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <PageHero
            title="Network"
            crumb={[
              { label: "local", href: "/facilities?source=local" },
              { label: "federated", href: "/facilities?source=mom" },
              // Was text, on the reasoning that "filtered" is a state rather
              // than a place. The controls that produce it ARE a place, and
              // they are what a reader following this term wants.
              { label: "filtered", href: "#filters" },
            ]}
          />
        </div>
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
      </div>

      <SeedPeerCta />

      <div className="grid gap-4 sm:gap-6 lg:grid-cols-[260px_1fr]">
        <aside id="filters" className="scroll-mt-20 space-y-4">
          {/*
            First control in the sidebar, above the filters: the site's primary
            call to action is "find your workshop on the map", and among several
            thousand spaces typing a name is what a person tries first.
          */}
          <div>
            <label htmlFor="space-name-search" className={LABEL}>
              Search by name
            </label>
            <input
              id="space-name-search"
              type="search"
              value={nameQuery}
              placeholder="e.g. FabLab Lyon"
              onChange={(e) => applyNameQuery(e.target.value)}
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
              <ViewToggle view={view} onChange={applyView} />
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

          {!active.isLoading && !active.isError && spaces.length > 0 && (
            <>
              {view === "map" && (
                <>
                  <div className="h-[520px] overflow-hidden rounded-xl border border-border">
                    <NetworkMap
                      spaces={spaces}
                      onVisibleChange={onVisibleChange}
                    />
                  </div>
                  <p className={CAPTION} role="status">
                    {listed.length === 0
                      ? "No spaces in view — pan or zoom out."
                      : `${listed.length.toLocaleString()} space${listed.length === 1 ? "" : "s"} in view`}
                  </p>
                </>
              )}
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {pageItems.map((s) => (
                  <NetworkSpaceCard key={`${s.source}-${s.id}`} space={s} />
                ))}
              </div>
              <Pagination
                page={safePage}
                totalPages={totalPages}
                totalItems={listed.length}
                pageSize={PAGE_SIZE}
                onPage={applyPage}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
