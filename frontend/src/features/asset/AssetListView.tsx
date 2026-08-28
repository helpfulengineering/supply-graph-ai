"use client";

import { useMemo } from "react";
import Link from "next/link";
import { PageHero } from "@/components/layout/PageHero";
import { Button, buttonVariants } from "@/components/ui/button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { FIELD_SM } from "@/components/ui/field";
import { CAPTION } from "@/components/ui/typography";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { AssetListRow } from "./AssetListRow";
import { ASSET_CRUMB } from "./crumbs";
import { ASSET_STATUSES, assetStatusInfo } from "./assetStatus";
import {
  buildAssetRows,
  designFilterOptions,
  groupAssetRows,
  type AssetGrouping,
} from "./assetListModel";
import { useAssetList } from "./useAssetList";
import { useDesignTitles } from "./useDesignTitles";

function SelectControl<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-xs text-muted-foreground">
      <span className="whitespace-nowrap">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className={`${FIELD_SM} text-foreground focus:outline-none focus:ring-2 focus:ring-ring`}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

/**
 * The fleet, as a work queue.
 *
 * Status is a `<select>` rather than a SegmentedControl: seven options will not
 * fit seven segments at 360px, and uniformity's rule is about hand-rolled
 * `role="radiogroup"`, which a native select does not claim.
 */
export function AssetListView() {
  const { state, setState, query } = useAssetList();
  const designTitles = useDesignTitles();
  const { hasWrite } = useAuth();
  // The moment the data was current, not the moment of render: every "3 days
  // ago" on the page is then relative to the same fetch, and re-rendering for
  // an unrelated reason cannot make two rows disagree.
  const now = query.dataUpdatedAt || Date.now();

  const assets = useMemo(() => query.data?.assets ?? [], [query.data]);
  const rows = useMemo(() => {
    const built = buildAssetRows(assets, { designTitles, query: state.query });
    return state.needsTriageOnly
      ? built.filter((r) => !r.asset.last_triaged_at)
      : built;
  }, [assets, designTitles, state.query, state.needsTriageOnly]);

  const groups = useMemo(
    () => groupAssetRows(rows, state.grouping, (s) => assetStatusInfo(s).label),
    [rows, state.grouping],
  );

  const filtered = Boolean(
    state.status ||
    state.manifestId ||
    state.query.trim() ||
    state.needsTriageOnly,
  );

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <PageHero
        title="Assets in the field"
        crumb={ASSET_CRUMB}
        description="Physical units built from the designs this node holds, and what condition they are in."
        actions={
          <>
            <Link
              href="/assets/salvage"
              className={cn(
                buttonVariants({ variant: "outline", size: "sm" }),
                "no-underline",
              )}
            >
              Find a part
            </Link>
            {hasWrite ? (
              <Link
                href="/assets/new"
                className={cn(buttonVariants({ size: "sm" }), "no-underline")}
              >
                Register asset
              </Link>
            ) : (
              <Link
                href="/settings/session"
                title="Registering a unit needs write access"
                className={cn(
                  buttonVariants({ variant: "outline", size: "sm" }),
                  "no-underline",
                )}
              >
                Sign in to register
              </Link>
            )}
          </>
        }
      />

      <div className="mb-4 flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex min-w-0 flex-1 items-center gap-2 text-xs text-muted-foreground">
            <span className="whitespace-nowrap">Search</span>
            <input
              type="search"
              value={state.query}
              onChange={(e) => setState({ query: e.target.value })}
              placeholder="Tag, location, or design"
              className={`${FIELD_SM} min-w-0 flex-1 text-foreground focus:outline-none focus:ring-2 focus:ring-ring`}
            />
          </label>
          <label className="flex min-h-6 items-center gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={state.needsTriageOnly}
              onChange={(e) => setState({ needsTriageOnly: e.target.checked })}
              className="h-4 w-4"
            />
            <span className="whitespace-nowrap">Never triaged</span>
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <SelectControl
            label="Status"
            value={state.status}
            onChange={(status) => setState({ status })}
            options={[
              { value: "", label: "All" },
              ...ASSET_STATUSES.map((s) => ({
                value: s.value as string,
                label: s.label,
              })),
            ]}
          />
          <SelectControl
            label="Design"
            value={state.manifestId}
            onChange={(manifestId) => setState({ manifestId })}
            options={[
              { value: "", label: "All" },
              ...designFilterOptions(assets, designTitles),
            ]}
          />
          <SelectControl<AssetGrouping>
            label="Group by"
            value={state.grouping}
            onChange={(grouping) => setState({ grouping })}
            options={[
              { value: "status", label: "Status" },
              { value: "design", label: "Design" },
              { value: "location", label: "Location" },
              { value: "none", label: "None" },
            ]}
          />
        </div>
      </div>

      {query.isPending ? (
        <LoadingState message="Loading assets…" />
      ) : query.isError ? (
        <ErrorState
          title="Could not load assets"
          description={(query.error as Error)?.message}
          onRetry={() => void query.refetch()}
        />
      ) : rows.length === 0 ? (
        // Three empty states, not one. "Nothing here yet" and "nothing matches
        // what you asked for" call for different next actions, and collapsing
        // them tells a user with an active filter that their fleet is empty.
        filtered ? (
          <EmptyState
            title="No assets match the current filters"
            description="Try a wider status, or clear the search."
            action={
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setState({
                    status: "",
                    manifestId: "",
                    query: "",
                    needsTriageOnly: false,
                  })
                }
              >
                Clear filters
              </Button>
            }
          />
        ) : (
          <EmptyState
            title="No assets registered"
            description="Register a unit to start tracking its condition, and to make its parts findable when another unit needs them."
            action={
              hasWrite ? (
                <Link
                  href="/assets/new"
                  className={cn(buttonVariants({ size: "sm" }), "no-underline")}
                >
                  Register asset
                </Link>
              ) : undefined
            }
          />
        )
      ) : (
        <div className="space-y-6">
          {groups.map((group) => (
            <section key={group.key} aria-labelledby={`group-${group.key}`}>
              <div className="mb-2 flex items-baseline justify-between gap-2">
                <SectionHeading id={`group-${group.key}`} role="card">
                  {group.label}
                </SectionHeading>
                <span className={CAPTION}>
                  {group.rows.length}{" "}
                  {group.rows.length === 1 ? "unit" : "units"}
                </span>
              </div>
              <div className={cn("space-y-1.5")}>
                {group.rows.map((row) => (
                  <AssetListRow key={row.asset.id} row={row} now={now} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
