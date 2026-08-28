"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  componentStates,
  deleteAsset,
  fetchAsset,
  fetchTriageReport,
} from "@/api/ohm/asset";
import { PageHero } from "@/components/layout/PageHero";
import { CHROME_LINK } from "@/components/layout/chromeLink";
import { Button, buttonVariants } from "@/components/ui/button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { PANEL, PANEL_BODY, PANEL_DANGER } from "@/components/ui/surface";
import { BODY_MUTED, CAPTION } from "@/components/ui/typography";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { ASSET_DETAIL_CRUMB } from "./crumbs";
import { AssetStatusControl } from "./AssetStatusControl";
import { ComponentStateTable } from "./ComponentStateTable";
import { SourcingPanel } from "./SourcingPanel";
import { TriageReportPanel } from "./TriageReportPanel";
import { assetDeleteConfirmMessage } from "./assetDeleteConfirmMessage";
import { lastTriagedLabel } from "./triageProgress";
import { useDesignTitles } from "./useDesignTitles";

export function AssetDetailView({ id }: { id: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { hasWrite, reportAuthFailure } = useAuth();
  const designTitles = useDesignTitles();

  const asset = useQuery({
    queryKey: ["asset-detail", id],
    queryFn: () => fetchAsset(id),
    staleTime: 0,
  });

  const report = useQuery({
    queryKey: ["asset-triage-report", id],
    queryFn: () => fetchTriageReport(id),
    enabled: Boolean(asset.data),
    staleTime: 0,
  });

  // The moment the data was current, not the moment of render: every "3 days
  // ago" on the page is then relative to the same fetch, and re-rendering for
  // an unrelated reason cannot make two rows disagree.
  const now = asset.dataUpdatedAt || Date.now();
  const states = asset.data ? componentStates(asset.data) : [];

  const remove = useMutation({
    mutationFn: () => deleteAsset(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["asset-list"] });
      router.push("/assets");
    },
    onError: reportAuthFailure,
  });

  if (asset.isPending) return <LoadingState message="Loading asset…" />;

  if (asset.isError || !asset.data) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-6">
        <ErrorState
          title="Asset not found"
          description={(asset.error as Error)?.message}
          onRetry={() => void asset.refetch()}
        />
        <p className="mt-4 text-center">
          <Link href="/assets" className={CHROME_LINK}>
            Back to the fleet
          </Link>
        </p>
      </div>
    );
  }

  const record = asset.data;
  const designTitle =
    designTitles.get(record.manifest_id) ?? record.manifest_id;
  const triaged = lastTriagedLabel(record.last_triaged_at, now);

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <PageHero
        title={record.asset_tag}
        breadcrumb={[
          { label: "Assets", href: "/assets" },
          { label: record.asset_tag },
        ]}
        crumb={ASSET_DETAIL_CRUMB}
        description={
          <>
            Physical unit of{" "}
            <Link href={`/okh/${record.manifest_id}`} className={CHROME_LINK}>
              {designTitle}
            </Link>
            {record.location ? `, at ${record.location}` : ""}.
          </>
        }
        actions={
          <>
            <Link
              href={`/assets/salvage?design=${encodeURIComponent(record.manifest_id)}`}

              className={cn(
                buttonVariants({ variant: "outline", size: "sm" }),
                "no-underline",
              )}
            >
              Find a part
            </Link>
            {hasWrite && (
              <Link
                href={`/assets/${id}/triage`}
                className={cn(buttonVariants({ size: "sm" }), "no-underline")}
              >
                Run triage
              </Link>
            )}
          </>
        }
      />

      <div
        className={cn(
          PANEL,
          PANEL_BODY,
          "mb-6 flex flex-wrap items-start gap-x-8 gap-y-4",
        )}
      >
        <AssetStatusControl assetId={id} status={record.status} />
        <div>
          <p className={CAPTION}>Last triaged</p>
          <p className="text-sm text-foreground">{triaged ?? "Never"}</p>
        </div>
        {record.triage_notes && (
          <div className="min-w-0 flex-1">
            <p className={CAPTION}>Triage notes</p>
            <p className={cn(BODY_MUTED, "whitespace-pre-wrap")}>
              {record.triage_notes}
            </p>
          </div>
        )}
      </div>

      <div className="space-y-6">
        <ComponentStateTable states={states} now={now} />

        {report.isError ? (
          <ErrorState
            title="Could not load the triage report"
            description={(report.error as Error)?.message}
            onRetry={() => void report.refetch()}
          />
        ) : report.data ? (
          <TriageReportPanel report={report.data} />
        ) : null}

        <SourcingPanel
          assetId={id}
          lastTriagedAt={record.last_triaged_at}
          sourceNewCount={report.data?.summary?.source_new ?? null}
        />

        {hasWrite && (
          <section
            aria-labelledby="danger"
            className={cn(PANEL_DANGER, PANEL_BODY)}
          >
            {/* The panel already carries the destructive tone; the heading
                taking it too would be the colour said twice. */}
            <SectionHeading id="danger" role="card">
              Delete this asset
            </SectionHeading>
            <p className={cn(CAPTION, "mt-1")}>
              Removes the record and every observation on it. The design is
              unaffected.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              disabled={remove.isPending}
              onClick={() => {
                if (
                  window.confirm(
                    assetDeleteConfirmMessage(record.asset_tag, states, now),
                  )
                ) {
                  remove.mutate();
                }
              }}
            >
              {remove.isPending ? "Deleting…" : "Delete asset"}
            </Button>
          </section>
        )}
      </div>
    </div>
  );
}
