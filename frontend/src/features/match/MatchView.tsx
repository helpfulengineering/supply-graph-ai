"use client";

import { SearchX } from "lucide-react";
import { LABEL } from "../../components/ui/field";
import { PageHero } from "../../components/layout/PageHero";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { withNavState } from "../../lib/navState";
import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchAllOkhList } from "../../api/ohm/okh";
import { fetchNetworkSpaces } from "../../api/ohm/network";
import { runMatch } from "../../api/ohm/match";
import { track } from "../../lib/site/stack";
import { EVENTS, type MatchRunProps } from "../../lib/site/events";
import { ApiError } from "../../api/ohm/client";
import { solutionSelectionKey, toMatchView } from "./matchViewModel";
import {
  defaultTolerance,
  toleranceCeiling,
  withinTolerance,
} from "./nearMiss";
import {
  buildInlineMatchRequest,
  buildMatchRequest,
  SYSTEM_MODES,
  type SystemMode,
} from "./matchRequest";
import { DesignPicker } from "./DesignPicker";
import { FacilityFilter, type FacilityOption } from "./FacilityFilter";
import { MatchResultCard } from "./MatchResultCard";
import { toRfqSolutions } from "./rfqHandoff";
import {
  LoadingState,
  EmptyState,
  ErrorState,
} from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import {
  PANEL_ACCENT,
  PANEL_MUTED,
  PANEL_WARNING,
} from "../../components/ui/surface";
import { SegmentedControl } from "../../components/ui/SegmentedControl";
import { humanizeProcessId } from "../network/deriveFilterOptions";
import { formatOkhDisplayTitle } from "../okh/formatOkhDisplayTitle";
import { cn } from "@/lib/utils";
import type { RfqNavigationState } from "../../types/rfq";

const _AXIS_LABELS: Record<string, string> = {
  country: "country",
  city: "city",
  process: "process",
  source: "source",
  status: "status",
  region: "region",
  access_type: "access",
};

/** Readable summary of an active network filter for the match banner. */
function describeNetworkFilter(
  filter: Record<string, string | boolean>,
): string {
  const parts = Object.entries(filter)
    .filter(([key, value]) => key in _AXIS_LABELS && value)
    .map(([key, value]) => {
      const shown =
        key === "process" ? humanizeProcessId(String(value)) : String(value);
      return `${_AXIS_LABELS[key]}: ${shown}`;
    });
  const scope =
    filter.include_mom === false
      ? "OHM facilities only"
      : "local ∪ Maps of Making";
  return parts.length ? `${scope} — ${parts.join(" · ")}` : scope;
}

function spaceToOption(s: {
  id: string;
  name: string;
  city: string | null;
  region: string | null;
  country: string | null;
  source: "local" | "mom";
}): FacilityOption {
  return {
    id: s.id,
    name: s.name,
    city: s.city,
    region: s.region,
    country: s.country,
    source: s.source,
  };
}

/** Default network scope for Match page selections (local ∪ MoM). */
const MATCH_NETWORK_SCOPE: Record<string, string | boolean> = {
  include_mom: true,
};

export function MatchView({
  okhId,
  okwId,
  networkFilter,
  inlineManifest,
  inlineTitle,
}: {
  okhId?: string;
  /** Prefill facility selection (from a facility detail hand-off). */
  okwId?: string;
  networkFilter?: Record<string, string | boolean>;
  /**
   * A reviewed manifest handed over from generate-from-URL, matched without
   * being saved to the catalogue. When present the design picker is replaced,
   * since there is no catalogue entry to pick.
   */
  inlineManifest?: Record<string, unknown>;
  inlineTitle?: string;
}) {
  const router = useRouter();
  const networkMode = !!networkFilter;
  const designs = useQuery({
    queryKey: ["okh-list"],
    queryFn: () => fetchAllOkhList(),
  });
  // Shares the ["network","baseline"] cache populated by the Home and Network
  // pages so the large unfiltered facilities payload is fetched only once.
  const facilitiesQuery = useQuery({
    queryKey: ["network", "baseline"],
    queryFn: () => fetchNetworkSpaces({}),
    enabled: !networkMode,
  });
  const [selected, setSelected] = useState(okhId ?? "");
  const [mode, setMode] = useState<SystemMode>("standard");
  const [facilityIds, setFacilityIds] = useState<string[]>(() =>
    okwId ? [okwId] : [],
  );
  const [selectedSolutionKeys, setSelectedSolutionKeys] = useState<string[]>(
    [],
  );
  const mutation = useMutation({
    mutationFn: ({
      id,
      m,
      ids,
    }: {
      id: string;
      m: SystemMode;
      ids: string[];
    }) => {
      const scope = networkMode ? networkFilter : MATCH_NETWORK_SCOPE;
      return runMatch(
        inlineManifest
          ? buildInlineMatchRequest(inlineManifest, m, undefined, ids, scope)
          : buildMatchRequest(id, m, undefined, ids, scope),
      );
    },
    onSuccess: (raw, variables) => {
      setSelectedSolutionKeys([]);
      // The one outcome a page view cannot describe. A run that returns
      // nothing looks identical to a successful one in /match traffic, and
      // "this design never matches anything here" is the finding an operator
      // is actually looking for. Counted through the view model rather than
      // the raw envelope, so the number recorded is the number shown. Ids
      // only, never manifest contents — see events.ts.
      track(EVENTS.matchRun, {
        design: inlineManifest ? "inline" : variables.id,
        solutions: toMatchView(raw).totalSolutions,
        mode: variables.m,
        facilities: variables.ids.length,
      } satisfies MatchRunProps);
    },
  });
  const rawView = useMemo(
    () => (mutation.data ? toMatchView(mutation.data) : null),
    [mutation.data],
  );

  // The design's requirement count comes from the results themselves — every
  // solution is evaluated against the same requirement set.
  const requirementCount = useMemo(
    () =>
      rawView?.solutions.reduce(
        (max, s) => Math.max(max, s.coverage?.total ?? 0),
        0,
      ) ?? 0,
    [rawView],
  );
  const ceiling = toleranceCeiling(requirementCount);
  const [tolerance, setTolerance] = useState<number | null>(null);
  const effectiveTolerance = Math.min(
    tolerance ?? defaultTolerance(requirementCount),
    ceiling,
  );

  // Near-misses are filtered out by default rather than shown as if they
  // matched — the previous behaviour presented a facility that cannot build the
  // design as "Medium · 67%".
  const view = useMemo(() => {
    if (!rawView) return null;
    return {
      ...rawView,
      solutions: rawView.solutions.filter((s) =>
        withinTolerance(s.coverage, effectiveTolerance),
      ),
    };
  }, [rawView, effectiveTolerance]);

  const hiddenCount =
    (rawView?.solutions.length ?? 0) - (view?.solutions.length ?? 0);

  const selectedDesign = useMemo(
    () => (designs.data?.items ?? []).find((d) => d.id === selected) ?? null,
    [designs.data, selected],
  );

  const websiteByFacilityId = useMemo(() => {
    const map: Record<string, string | null | undefined> = {};
    for (const s of facilitiesQuery.data?.spaces ?? []) {
      map[s.id] = s.url;
    }
    return map;
  }, [facilitiesQuery.data]);

  const modeInfo = SYSTEM_MODES.find((s) => s.mode === mode);
  // A design handed over from generation is scoped to the whole network by
  // default (local ∪ MoM). The user asked "who can build this", not "who among
  // these facilities" — making them pick facilities first would be friction
  // that answers a question they did not ask. They can still narrow below.
  const requiresFacilityChoice = !networkMode && !inlineManifest;
  const canRun =
    (!!selected || !!inlineManifest) &&
    !mutation.isPending &&
    (!requiresFacilityChoice || facilityIds.length > 0);

  const facilityOptions = useMemo(
    () => (facilitiesQuery.data?.spaces ?? []).map(spaceToOption),
    [facilitiesQuery.data],
  );

  return (
    <div className="space-y-6">
      <PageHero
        title="Match a Design"
        crumb={[
          { label: "design", href: "/okh" },
          { label: "facilities", href: "/facilities" },
          // Solutions are what this page produces; there is no list of them to
          // send anyone to.
          { label: "solutions" },
        ]}
      />

      <div className="space-y-4">
        {inlineManifest ? (
          <div className={PANEL_MUTED}>
            <p className="text-sm font-medium text-foreground">
              {inlineTitle || "Generated design"}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Matching a design you generated and reviewed in this session. It
              has not been saved to the catalogue, and closing this page will
              discard it — download it first if you want to keep it.
            </p>
          </div>
        ) : (
          <DesignPicker
            designs={designs.data?.items ?? []}
            selectedId={selected}
            onSelect={setSelected}
            isLoading={designs.isLoading}
            isError={designs.isError}
          />
        )}

        {/*
          Stacks below `sm`, sits on one baseline above it. As a single
          `flex-wrap items-end` row the mode group and the button competed for
          a phone's width: the group kept its intrinsic size, the button was
          squeezed against it, and the mode description wrapped underneath both
          — so "Run Match" ended up floating beside a paragraph it has nothing
          to do with. Stacking makes the reading order the doing order: choose
          a mode, read what it means, then run.
        */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="min-w-0 sm:flex-1">
            <span className="mb-1 block text-sm text-muted-foreground">
              System mode
            </span>
            <SegmentedControl
              label="System mode"
              value={mode}
              options={SYSTEM_MODES.map((s) => ({
                value: s.mode,
                label: s.label,
              }))}
              onChange={setMode}
            />
            {modeInfo && (
              <p className="mt-1.5 max-w-xl text-xs text-muted-foreground">
                {modeInfo.description}
              </p>
            )}
          </div>
          <Button
            size="lg"
            className="w-full sm:w-auto"
            disabled={!canRun}
            onClick={() =>
              mutation.mutate({ id: selected, m: mode, ids: facilityIds })
            }
          >
            {mutation.isPending ? "Matching…" : "Run Match"}
          </Button>
        </div>
        {requiresFacilityChoice && selected && facilityIds.length === 0 && (
          <p className="text-xs text-warning">
            Select at least one facility below before running a match.
          </p>
        )}
        {!selected && (
          <p className="text-xs text-warning">
            Search and select a design above before running a match.
          </p>
        )}

        {networkMode ? (
          <div className={cn(PANEL_ACCENT, "text-sm")}>
            <p className="font-medium text-primary-ink">
              Matching against the network
            </p>
            <p className="mt-0.5 text-primary-ink">
              {describeNetworkFilter(networkFilter!)}
            </p>
          </div>
        ) : (
          <FacilityFilter
            facilities={facilityOptions}
            selectedIds={facilityIds}
            onChange={setFacilityIds}
            isLoading={facilitiesQuery.isLoading}
            isError={facilitiesQuery.isError}
          />
        )}
      </div>

      {mutation.isPending && (
        <LoadingState message="Matching against facilities…" />
      )}
      {mutation.isError && (
        <ErrorState
          description={
            mutation.error instanceof ApiError
              ? [
                  mutation.error.message,
                  mutation.error.requestId
                    ? `Request ID: ${mutation.error.requestId}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(" — ")
              : mutation.error instanceof Error
                ? mutation.error.message
                : "Match failed."
          }
          onRetry={() =>
            selected &&
            canRun &&
            mutation.mutate({ id: selected, m: mode, ids: facilityIds })
          }
        />
      )}

      {view &&
        !mutation.isPending &&
        (view.solutions.length === 0 ? (
          <EmptyState
            icon={
              <SearchX
                aria-hidden="true"
                className="h-8 w-8"
                strokeWidth={1.5}
              />
            }
            title="No matches found"
            description="No facilities can currently produce this design."
          />
        ) : (
          <div className="space-y-4">
            {view.summary && (
              <p className={cn(PANEL_MUTED, "text-sm text-foreground")}>
                {view.summary}
              </p>
            )}
            {view.coverageGaps.length > 0 && (
              <div className={cn(PANEL_WARNING, "text-sm")}>
                <p className="font-medium text-warning">Coverage gaps</p>
                <p className="mt-1 text-warning">
                  Unmatched: {view.coverageGaps.join(", ")}
                </p>
              </div>
            )}
            {ceiling > 0 && (
              <div className={PANEL_MUTED}>
                <label htmlFor="near-miss-tolerance" className={LABEL}>
                  Allow facilities missing up to{" "}
                  {effectiveTolerance === 0
                    ? "nothing"
                    : `${effectiveTolerance} requirement${effectiveTolerance === 1 ? "" : "s"}`}
                </label>
                <input
                  id="near-miss-tolerance"
                  type="range"
                  min={0}
                  max={ceiling}
                  step={1}
                  value={effectiveTolerance}
                  onChange={(e) => setTolerance(Number(e.target.value))}
                  className="mt-2 w-full max-w-sm"
                />
                <p className="mt-1 text-xs text-muted-foreground">
                  {/*
                    Capped at r-2 so a "match" always means at least two
                    satisfied requirements. Counting missing requirements rather
                    than a percentage keeps this comparable across designs: one
                    gap in a 2-requirement design is not the same as one gap in
                    a design with six.
                  */}
                  This design has {requirementCount} requirements. The most you
                  can relax to is {ceiling}, so a result always meets at least
                  two.
                  {hiddenCount > 0 &&
                    ` ${hiddenCount} facilit${hiddenCount === 1 ? "y is" : "ies are"} hidden at this setting.`}
                </p>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-muted-foreground">
                {view.totalSolutions} solution
                {view.totalSolutions !== 1 ? "s" : ""}
                {selectedSolutionKeys.length > 0
                  ? ` · ${selectedSolutionKeys.length} selected`
                  : ""}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={view.solutions.length === 0}
                  onClick={() =>
                    setSelectedSolutionKeys(
                      view.solutions.map((s, i) => solutionSelectionKey(s, i)),
                    )
                  }
                >
                  Select all
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={selectedSolutionKeys.length === 0}
                  onClick={() => setSelectedSolutionKeys([])}
                >
                  Clear selection
                </Button>
                <Button
                  size="sm"
                  disabled={
                    selectedSolutionKeys.length === 0 || !selectedDesign
                  }
                  onClick={() => {
                    const selectedSolutions = view.solutions.filter((s, i) =>
                      selectedSolutionKeys.includes(solutionSelectionKey(s, i)),
                    );
                    const state: RfqNavigationState = {
                      okhId: selectedDesign!.id,
                      okhTitle: formatOkhDisplayTitle(selectedDesign!.title),
                      okhFunction: selectedDesign!.function ?? undefined,
                      okhVersion: selectedDesign!.version ?? undefined,
                      solutions: toRfqSolutions(
                        selectedSolutions,
                        websiteByFacilityId,
                      ),
                    };
                    router.push(withNavState("/rfq", state));
                  }}
                >
                  Contact selected facilities →
                </Button>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Select one or more facilities to generate outreach RFQs and
              arrange production. Each card also links to that solution’s supply
              tree when available.
            </p>
            {view.solutions.map((s, i) => {
              const key = solutionSelectionKey(s, i);
              return (
                <MatchResultCard
                  key={key}
                  solution={s}
                  solutionId={view.solutionId}
                  selectionKey={key}
                  selected={selectedSolutionKeys.includes(key)}
                  onToggle={() =>
                    setSelectedSolutionKeys((prev) =>
                      prev.includes(key)
                        ? prev.filter((k) => k !== key)
                        : [...prev, key],
                    )
                  }
                />
              );
            })}
          </div>
        ))}
    </div>
  );
}
