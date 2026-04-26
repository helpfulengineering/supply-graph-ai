import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { generateRfq } from "../../api/rfq";
import { fetchOkhDetail } from "../../api/okh";
import { RfqDocumentCard } from "./RfqDocumentCard";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { EmptyState } from "../../components/ui/EmptyState";
import type { RfqNavigationState, RFQDocument } from "../../types/rfq";

interface Props {
  navState: RfqNavigationState | null;
}

export function RfqView({ navState }: Props) {
  const navigate = useNavigate();
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
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
          RFQ Generation
        </h1>
        <EmptyState
          icon="📄"
          heading="No facilities selected"
          body="Return to the match results page, select one or more facilities, then click Generate RFQ."
          action={
            <button
              onClick={() => navigate("/match")}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 dark:bg-indigo-500"
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
  const { data: fullManifest } = useQuery({
    queryKey: ["okh-detail-rfq", okhId],
    queryFn: () => fetchOkhDetail(okhId),
    staleTime: 5 * 60 * 1000,
  });

  const handleGenerate = () => {
    mutate({
      okh_id: okhId,
      okh_title: okhTitle,
      okh_function: okhFunction,
      okh_version: okhVersion,
      quantity,
      okh_manifest: fullManifest as unknown as Record<string, unknown> | undefined,
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
      .map((r) => `${"=".repeat(60)}\n${r.rfq_number}\n${"=".repeat(60)}\n${r.text}`)
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
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
            RFQ Generation
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Generating requests for quotation for{" "}
            <span className="font-medium text-slate-700 dark:text-slate-200">
              {okhTitle}
            </span>
            {okhVersion && (
              <span className="ml-1 text-slate-400">v{okhVersion}</span>
            )}
          </p>
        </div>
        <button
          onClick={() => navigate(-1)}
          className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
        >
          ← Back
        </button>
      </div>

      {/* Generation form */}
      {!generated && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Configuration
          </h2>

          {/* Selected facilities summary */}
          <div className="mb-5 space-y-2">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              <span className="font-semibold">{solutions.length}</span> facilit
              {solutions.length === 1 ? "y" : "ies"} selected:
            </p>
            <ul className="space-y-1.5">
              {solutions.map((s) => (
                <li key={s.facility_id} className="flex items-center gap-2 text-sm">
                  <span className="flex h-5 w-6 items-center justify-center rounded bg-slate-100 text-xs font-bold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                    #{s.rank}
                  </span>
                  <span className="font-medium text-slate-700 dark:text-slate-200">
                    {s.facility_name}
                  </span>
                  <span className="text-xs text-slate-400">
                    {s.facility.location?.city ?? ""}
                    {s.facility.location?.city && s.facility.location?.country
                      ? ", "
                      : ""}
                    {s.facility.location?.country ?? ""}
                  </span>
                  <span className="ml-auto text-xs font-medium text-slate-500 dark:text-slate-400">
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
              className="text-sm font-medium text-slate-700 dark:text-slate-200"
            >
              Production quantity
            </label>
            <input
              id="rfq-quantity"
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value, 10) || 1))}
              className="w-24 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            />
            <span className="text-sm text-slate-500 dark:text-slate-400">units</span>
          </div>

          {okhFunction && (
            <p className="mb-5 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600 italic dark:bg-slate-800/50 dark:text-slate-300">
              <span className="not-italic font-medium text-slate-500 dark:text-slate-400">Function: </span>
              {okhFunction}
            </p>
          )}

          <button
            onClick={handleGenerate}
            disabled={isPending}
            className="rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60 transition-colors dark:bg-indigo-500 dark:hover:bg-indigo-400"
          >
            {isPending ? "Generating…" : `Generate ${solutions.length} RFQ${solutions.length !== 1 ? "s" : ""}`}
          </button>
        </div>
      )}

      {/* Loading */}
      {isPending && (
        <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-8 dark:border-indigo-900 dark:bg-indigo-950/30">
          <LoadingSpinner message="Generating RFQ documents…" />
        </div>
      )}

      {/* Error */}
      {isError && <ErrorMessage error={error} />}

      {/* Results */}
      {generated && rfqs.length > 0 && (
        <div className="space-y-5">
          {/* Results header */}
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {rfqs.length} RFQ document{rfqs.length !== 1 ? "s" : ""} generated
            </h2>
            <div className="flex gap-2">
              <button
                onClick={handleDownloadAll}
                className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                ↓ Download all (.txt)
              </button>
              <button
                onClick={handleDownloadAllJson}
                className="rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-400"
              >
                ↓ Download all (.json)
              </button>
              <button
                onClick={() => { setGenerated(false); setRfqs([]); }}
                className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50 transition-colors dark:border-slate-600 dark:bg-slate-800 dark:text-slate-400"
              >
                ← Edit settings
              </button>
            </div>
          </div>

          {/* Document cards */}
          <div className="space-y-5">
            {rfqs.map((doc) => (
              <RfqDocumentCard key={doc.rfq_number} doc={doc} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
