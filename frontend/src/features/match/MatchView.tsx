import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchAllOkhList } from "../../api/ohm/okh";
import { fetchNetworkSpaces } from "../../api/ohm/network";
import { runMatch } from "../../api/ohm/match";
import { ApiError } from "../../api/ohm/client";
import { toMatchView } from "./matchViewModel";
import { buildMatchRequest, SYSTEM_MODES, type SystemMode } from "./matchRequest";
import { DesignPicker } from "./DesignPicker";
import { FacilityFilter, type FacilityOption } from "./FacilityFilter";
import { MatchResultCard } from "./MatchResultCard";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import { humanizeProcessId } from "../network/deriveFilterOptions";
import { cn } from "@/lib/utils";

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
function describeNetworkFilter(filter: Record<string, string | boolean>): string {
  const parts = Object.entries(filter)
    .filter(([key, value]) => key in _AXIS_LABELS && value)
    .map(([key, value]) => {
      const shown = key === "process" ? humanizeProcessId(String(value)) : String(value);
      return `${_AXIS_LABELS[key]}: ${shown}`;
    });
  const scope = filter.include_mom === false ? "OHM facilities only" : "local ∪ Maps of Making";
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
}: {
  okhId?: string;
  /** Prefill facility selection (from a facility detail hand-off). */
  okwId?: string;
  networkFilter?: Record<string, string | boolean>;
}) {
  const networkMode = !!networkFilter;
  const designs = useQuery({
    queryKey: ["okh-list"],
    queryFn: () => fetchAllOkhList(),
    staleTime: 60_000,
  });
  const facilitiesQuery = useQuery({
    queryKey: ["network", "match-filter"],
    queryFn: () => fetchNetworkSpaces({}),
    staleTime: 300_000,
    enabled: !networkMode,
  });
  const [selected, setSelected] = useState(okhId ?? "");
  const [mode, setMode] = useState<SystemMode>("standard");
  const [facilityIds, setFacilityIds] = useState<string[]>(() =>
    okwId ? [okwId] : [],
  );
  const mutation = useMutation({
    mutationFn: ({ id, m, ids }: { id: string; m: SystemMode; ids: string[] }) =>
      runMatch(
        buildMatchRequest(
          id,
          m,
          undefined,
          ids,
          networkMode ? networkFilter : MATCH_NETWORK_SCOPE,
        ),
      ),
  });
  const view = useMemo(
    () => (mutation.data ? toMatchView(mutation.data) : null),
    [mutation.data],
  );

  const modeInfo = SYSTEM_MODES.find((s) => s.mode === mode);
  const canRun =
    !!selected &&
    !mutation.isPending &&
    (networkMode || facilityIds.length > 0);

  const facilityOptions = useMemo(
    () => (facilitiesQuery.data?.spaces ?? []).map(spaceToOption),
    [facilitiesQuery.data],
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Match a Design</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Choose a design and the facilities to compare, then run a match.
        </p>
      </div>

      <div className="space-y-4">
        <DesignPicker
          designs={designs.data?.items ?? []}
          selectedId={selected}
          onSelect={setSelected}
          isLoading={designs.isLoading}
          isError={designs.isError}
        />

        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1">
            <span className="mb-1 block text-sm text-muted-foreground">System mode</span>
            <div
              role="radiogroup"
              aria-label="System mode"
              className="inline-flex overflow-hidden rounded-md border border-input"
            >
              {SYSTEM_MODES.map((s) => (
                <button
                  key={s.mode}
                  type="button"
                  role="radio"
                  aria-checked={mode === s.mode}
                  onClick={() => setMode(s.mode)}
                  className={cn(
                    "px-3 py-1.5 text-sm transition-colors",
                    mode === s.mode
                      ? "bg-primary text-primary-foreground"
                      : "bg-background text-foreground hover:bg-accent",
                  )}
                >
                  {s.label}
                </button>
              ))}
            </div>
            {modeInfo && (
              <p className="mt-1.5 max-w-xl text-xs text-muted-foreground">{modeInfo.description}</p>
            )}
          </div>
          <Button
            disabled={!canRun}
            onClick={() => mutation.mutate({ id: selected, m: mode, ids: facilityIds })}
          >
            {mutation.isPending ? "Matching…" : "⚡ Run Match"}
          </Button>
        </div>
        {!networkMode && selected && facilityIds.length === 0 && (
          <p className="text-xs text-amber-700 dark:text-amber-400">
            Select at least one facility below before running a match.
          </p>
        )}
        {!selected && (
          <p className="text-xs text-amber-700 dark:text-amber-400">
            Search and select a design above before running a match.
          </p>
        )}

        {networkMode ? (
          <div className="rounded-lg border border-indigo-200 bg-indigo-50/60 p-3 text-sm dark:border-indigo-800 dark:bg-indigo-950/30">
            <p className="font-medium text-indigo-800 dark:text-indigo-300">
              Matching against the network
            </p>
            <p className="mt-0.5 text-indigo-700 dark:text-indigo-400">
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

      {mutation.isPending && <LoadingState message="Matching against facilities…" />}
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

      {view && !mutation.isPending &&
        (view.solutions.length === 0 ? (
          <EmptyState
            icon="🔍"
            title="No matches found"
            description="No facilities can currently produce this design."
          />
        ) : (
          <div className="space-y-4">
            {view.summary && (
              <p className="rounded-lg border bg-muted/40 p-4 text-sm text-foreground">
                {view.summary}
              </p>
            )}
            {view.coverageGaps.length > 0 && (
              <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-4 text-sm dark:border-yellow-800 dark:bg-yellow-950/30">
                <p className="font-medium text-yellow-800 dark:text-yellow-300">Coverage gaps</p>
                <p className="mt-1 text-yellow-700 dark:text-yellow-400">
                  Unmatched: {view.coverageGaps.join(", ")}
                </p>
              </div>
            )}
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                {view.totalSolutions} solution{view.totalSolutions !== 1 ? "s" : ""}
              </p>
              {view.solutionId && (
                <Link
                  to={`/visualization/${view.solutionId}`}
                  className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  View supply tree →
                </Link>
              )}
            </div>
            {view.solutions.map((s, i) => (
              <MatchResultCard key={s.facilityId ?? i} solution={s} />
            ))}
          </div>
        ))}
    </div>
  );
}
