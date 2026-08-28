"use client";

import { useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { salvageMatch } from "@/api/ohm/asset";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import {
  CHECKBOX,
  CHOICE_ROW,
  FIELD,
  HINT,
  LABEL,
} from "@/components/ui/field";
import { Fieldset } from "@/components/ui/Fieldset";
import { PANEL, PANEL_BODY } from "@/components/ui/surface";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { CAPTION } from "@/components/ui/typography";
import { cn } from "@/lib/utils";
import { SALVAGE_CRUMB } from "./crumbs";
import { COMPONENT_CONDITIONS } from "./componentCondition";
import type { ComponentCondition } from "./componentCondition";
import { SalvageResultRow } from "./SalvageResultRow";
import {
  isSalvageQueryRunnable,
  salvageQueryError,
  salvageQueryFromParams,
  salvageQueryToParams,
  toSalvageRequest,
  type SalvageQuery,
} from "./salvageQuery";
import { useDesignTitles } from "./useDesignTitles";

/**
 * Find a part across the fleet.
 *
 * The unsearched state is NOT the empty state. A page that has run no query
 * should say what it is for; a page that ran one and found nothing should say
 * so and suggest widening. Collapsing those two is the classic bug in every
 * search UI, and it is worth the extra branch.
 */
export function SalvagePage() {
  const router = useRouter();
  const pathname = usePathname() ?? "/assets/salvage";
  const params = useSearchParams();
  const designTitles = useDesignTitles();

  const submitted = useMemo(
    () => salvageQueryFromParams(new URLSearchParams(params?.toString() ?? "")),
    [params],
  );
  const [draft, setDraft] = useState<SalvageQuery>(submitted);
  const runnable = isSalvageQueryRunnable(submitted);

  const query = useQuery({
    queryKey: ["asset-salvage", params?.toString() ?? ""],
    queryFn: () => salvageMatch(toSalvageRequest(submitted)),
    enabled: runnable,
    staleTime: 0,
  });

  // The moment the data was current, not the moment of render: every "3 days
  // ago" on the page is then relative to the same fetch, and re-rendering for
  // an unrelated reason cannot make two rows disagree.
  const now = query.dataUpdatedAt || Date.now();
  const draftError = salvageQueryError(draft);

  function submit() {
    const qs = salvageQueryToParams(draft).toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  function toggleCondition(condition: ComponentCondition, on: boolean) {
    setDraft((d) => ({
      ...d,
      conditions: on
        ? [...d.conditions, condition]
        : d.conditions.filter((c) => c !== condition),
    }));
  }

  const matches = query.data?.matches ?? [];

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <PageHero
        title="Find a part"
        breadcrumb={[
          { label: "Assets", href: "/assets" },
          { label: "Find a part" },
        ]}
        crumb={SALVAGE_CRUMB}
        description="Search the fleet for components marked harvestable during triage."
      />

      <form
        className={cn(PANEL, PANEL_BODY, "mb-6 space-y-4")}
        onSubmit={(e) => {
          e.preventDefault();
          if (!draftError) submit();
        }}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className={LABEL} htmlFor="salvage-component">
              Component name
            </label>
            <input
              id="salvage-component"
              value={draft.componentName}
              onChange={(e) =>
                setDraft({ ...draft, componentName: e.target.value })
              }
              placeholder="pump"
              className={FIELD}
            />
            <p className={HINT}>Matches any part of the name, ignoring case.</p>
          </div>
          <div>
            <label className={LABEL} htmlFor="salvage-part">
              Part number
            </label>
            <input
              id="salvage-part"
              value={draft.partNumber}
              onChange={(e) =>
                setDraft({ ...draft, partNumber: e.target.value })
              }
              placeholder="P-1042"
              className={FIELD}
            />
            <p className={HINT}>Exact match.</p>
          </div>
        </div>

        <div>
          <label className={LABEL} htmlFor="salvage-design">
            Design
          </label>
          <select
            id="salvage-design"
            value={draft.manifestId}
            onChange={(e) => setDraft({ ...draft, manifestId: e.target.value })}
            className={FIELD}
          >
            <option value="">Any design</option>
            {[...designTitles].map(([id, title]) => (
              <option key={id} value={id}>
                {title}
              </option>
            ))}
          </select>
          <p className={HINT}>
            Also searches designs declared compatible with this one.
          </p>
        </div>

        {/*
          Checkboxes, not a SegmentedControl: conditions are a multi-select, and
          `role="radiogroup"` would promise one-of-N for a control that is not.
        */}
        <Fieldset legend="Condition" legendHidden>
          <div className="flex flex-wrap gap-2">
            {COMPONENT_CONDITIONS.map((condition) => (
              <label key={condition.value} className={CHOICE_ROW}>
                <input
                  type="checkbox"
                  className={CHECKBOX}
                  checked={draft.conditions.includes(condition.value)}
                  onChange={(e) =>
                    toggleCondition(condition.value, e.target.checked)
                  }
                />
                <span>{condition.label}</span>
              </label>
            ))}
          </div>
        </Fieldset>

        <label className={CHOICE_ROW}>
          <input
            type="checkbox"
            className={CHECKBOX}
            checked={draft.includeClaimed}
            onChange={(e) =>
              setDraft({ ...draft, includeClaimed: e.target.checked })
            }
          />
          <span>Include components already claimed</span>
        </label>

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={Boolean(draftError)}>
            Search
          </Button>
          {/* The rule is visible before the button is pressed, not after. */}
          {draftError && <span className={CAPTION}>{draftError}</span>}
        </div>
      </form>

      {!runnable ? (
        <EmptyState
          title="Search the fleet for a part"
          description="Enter a component name or a part number. Results show which unit each part is in, and whether someone has already claimed it."
        />
      ) : query.isPending ? (
        <LoadingState message="Searching the fleet…" />
      ) : query.isError ? (
        <ErrorState
          title="Search failed"
          description={(query.error as Error)?.message}
          onRetry={() => void query.refetch()}
        />
      ) : matches.length === 0 ? (
        <EmptyState
          title="No harvestable parts match"
          description="Try dropping the design filter, adding conditions, or including parts that are already claimed."
        />
      ) : (
        <section aria-label="Search results" className="space-y-2">
          <p className={CAPTION}>
            {query.data?.total} {query.data?.total === 1 ? "part" : "parts"}{" "}
            found
          </p>
          {matches.map((match) => (
            <SalvageResultRow
              key={`${match.asset_id}:${match.component_name}`}
              match={match}
              now={now}
              onClaimed={() => void query.refetch()}
            />
          ))}
        </section>
      )}
    </div>
  );
}
