"use client";

import { QuotesIllustration } from "../../components/ui/illustrations";
import { FIELD, FIELD_SM } from "../../components/ui/field";
import { PageHero } from "../../components/layout/PageHero";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { generateRfq } from "../../api/rfq";
import { fetchOkhDetail } from "../../api/okh";
import { RfqDocumentCard } from "./RfqDocumentCard";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { EmptyState } from "../../components/ui/EmptyState";
import type { RfqNavigationState, RFQDocument } from "../../types/rfq";
import { displayCountryName } from "../match/geoDisplay";
import { SECTION_LABEL } from "../../components/ui/typography";
import { PANEL, PANEL_ACCENT } from "../../components/ui/surface";
import { cn } from "@/lib/utils";
import type { CrumbTerm } from "../../components/layout/PageHero";

/**
 * One crumb for both of this view's heroes — the empty state and the generated
 * documents render the same page under two conditions, and the terms had been
 * written out twice.
 */
const RFQ_CRUMB: readonly CrumbTerm[] = [
  { label: "facilities", href: "/facilities" },
  { label: "quotes" },
  { label: "documents" },
];

interface Props {
  navState: RfqNavigationState | null;
}

export function RfqView({ navState }: Props) {
  const router = useRouter();
  const [quantity, setQuantity] = useState(1);
  const [rfqs, setRfqs] = useState<RFQDocument[]>([]);
  const [generated, setGenerated] = useState(false);

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: generateRfq,
    onSuccess: (response) => {
      setRfqs(response.data.rfqs);
      setGenerated(true);
    },
  });

  if (!navState || navState.solutions.length === 0) {
    return (
      <div className="space-y-6">
        <PageHero title="RFQ Generation" crumb={RFQ_CRUMB} />
        <EmptyState
          icon={() => <QuotesIllustration className="h-10 w-10" />}
          heading="No facilities selected"
          body="Return to the match results page, select one or more facilities, then click Contact selected facilities."
          action={
            <button
              onClick={() => router.push("/match")}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-on-accent hover:bg-primary"
            >
              Back to Match
            </button>
          }
        />
      </div>
    );
  }

  const { okhId, okhTitle, okhFunction, okhVersion, solutions } = navState;

  // Fetch the full manifest so we can embed it in the RFQ output
  // eslint-disable-next-line react-hooks/rules-of-hooks -- legacy reference page: conditional hook after early return. RFQ is out of v1 scope (PRD #184) and this page is slated for removal/rebuild; not refactoring throwaway code.
  const { data: fullManifest } = useQuery({
    queryKey: ["okh-detail-rfq", okhId],
    queryFn: () => fetchOkhDetail(okhId),
  });

  const handleGenerate = () => {
    mutate({
      okh_id: okhId,
      okh_title: okhTitle,
      okh_function: okhFunction,
      okh_version: okhVersion,
      quantity,
      okh_manifest: fullManifest as unknown as
        Record<string, unknown> | undefined,
      solutions: solutions.map((s) => ({
        facility_id: s.facility_id,
        facility_name: s.facility_name,
        confidence: s.confidence,
        score: s.score,
        rank: s.rank,
        tree: s.tree as unknown as Record<string, unknown>,
        facility: s.facility as unknown as Record<string, unknown>,
      })),
    });
  };

  const handleDownloadAll = () => {
    const combined = rfqs
      .map(
        (r) =>
          `${"=".repeat(60)}\n${r.rfq_number}\n${"=".repeat(60)}\n${r.text}`,
      )
      .join("\n\n");
    const blob = new Blob([combined], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rfq-bundle-${okhId.slice(0, 8)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadAllJson = () => {
    const payload = {
      okh_id: okhId,
      okh_title: okhTitle,
      quantity,
      generated_at: new Date().toISOString(),
      // Full manifest is included so the recipient can inspect or rebuild the package
      okh_manifest: fullManifest ?? null,
      rfqs,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rfq-bundle-${okhId.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <PageHero
        title="RFQ Generation"
        crumb={RFQ_CRUMB}
        description={
          <>
            Generating requests for quotation for{" "}
            <span className="font-medium text-foreground">{okhTitle}</span>
            {okhVersion && (
              <span className="ml-1 text-muted-foreground">v{okhVersion}</span>
            )}
          </>
        }
        actions={
          <button
            onClick={() => router.back()}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            ← Back
          </button>
        }
      />

      {/* Generation form */}
      {!generated && (
        <div className={PANEL}>
          <h2 className={cn(SECTION_LABEL, "mb-4")}>Configuration</h2>

          {/* Selected facilities summary */}
          <div className="mb-5 space-y-2">
            <p className="text-sm text-muted-foreground">
              <span className="font-semibold">{solutions.length}</span> facilit
              {solutions.length === 1 ? "y" : "ies"} selected:
            </p>
            <ul className="space-y-1.5">
              {solutions.map((s) => (
                <li
                  key={s.facility_id}
                  className="flex items-center gap-2 text-sm"
                >
                  <span className="flex h-5 w-6 items-center justify-center rounded bg-muted text-xs font-bold text-muted-foreground">
                    #{s.rank}
                  </span>
                  <span className="font-medium text-foreground">
                    {s.facility_name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {s.facility.location?.city ?? ""}
                    {s.facility.location?.city && s.facility.location?.country
                      ? ", "
                      : ""}
                    {s.facility.location?.country
                      ? displayCountryName(s.facility.location.country)
                      : ""}
                  </span>
                  <span className="ml-auto text-xs font-medium text-muted-foreground">
                    {Math.round(s.confidence * 100)}% match
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Quantity */}
          <div className="mb-6 flex items-center gap-3">
            <label
              htmlFor="rfq-quantity"
              className="text-sm font-medium text-foreground"
            >
              Production quantity
            </label>
            <input
              id="rfq-quantity"
              type="number"
              min={1}
              value={quantity}
              onChange={(e) =>
                setQuantity(Math.max(1, parseInt(e.target.value, 10) || 1))
              }
              className={`${FIELD} w-24 focus:border-primary/30 focus:ring-1`}
            />
            <span className="text-sm text-muted-foreground">units</span>
          </div>

          {okhFunction && (
            <p className="mb-5 rounded-lg bg-background px-4 py-3 text-sm text-muted-foreground italic">
              <span className="not-italic font-medium text-muted-foreground">
                Function:{" "}
              </span>
              {okhFunction}
            </p>
          )}

          <button
            onClick={handleGenerate}
            disabled={isPending}
            className="rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-on-accent hover:bg-primary disabled:opacity-60 transition-colors"
          >
            {isPending
              ? "Generating…"
              : `Generate ${solutions.length} RFQ${solutions.length !== 1 ? "s" : ""}`}
          </button>
        </div>
      )}

      {/* Loading */}
      {isPending && (
        <div className={cn(PANEL_ACCENT, "p-8")}>
          <LoadingSpinner message="Generating RFQ documents…" />
        </div>
      )}

      {/* Error */}
      {isError && <ErrorMessage error={error} />}

      {/* Results */}
      {generated && rfqs.length > 0 && (
        <div className="space-y-6">
          {/* Results header */}
          <div className="flex items-center justify-between">
            <h2 className={SECTION_LABEL}>
              {rfqs.length} RFQ document{rfqs.length !== 1 ? "s" : ""} generated
            </h2>
            <div className="flex gap-2">
              <button
                onClick={handleDownloadAll}
                className={`${FIELD_SM} font-medium text-foreground hover:bg-background transition-colors dark:hover:bg-muted`}
              >
                ↓ Download all (.txt)
              </button>
              <button
                onClick={handleDownloadAllJson}
                className={`${FIELD_SM} border-primary/30 bg-accent font-medium text-primary-ink hover:bg-accent`}
              >
                ↓ Download all (.json)
              </button>
              <button
                onClick={() => {
                  setGenerated(false);
                  setRfqs([]);
                }}
                className={`${FIELD_SM} font-medium text-muted-foreground hover:bg-background transition-colors`}
              >
                ← Edit settings
              </button>
            </div>
          </div>

          {/* Document cards */}
          <div className="space-y-6">
            {rfqs.map((doc) => (
              <RfqDocumentCard key={doc.rfq_number} doc={doc} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
