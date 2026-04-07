import { useState } from "react";
import { buildPackage } from "../../api/rfq";
import type { RFQDocument } from "../../types/rfq";

interface Props {
  doc: RFQDocument;
}

function ConfidencePill({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const colorClass =
    pct >= 80
      ? "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300"
      : pct >= 50
      ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300"
      : "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${colorClass}`}>
      {pct}% match
    </span>
  );
}

export function RfqDocumentCard({ doc }: Props) {
  const [copied, setCopied] = useState(false);
  const [buildStatus, setBuildStatus] = useState<"idle" | "building" | "done" | "error">("idle");
  const [packageRef, setPackageRef] = useState<{ name: string; version: string } | null>(null);

  const handleBuildPackage = () => {
    if (!doc.okh_manifest) return;
    const manifestId = (doc.okh_manifest.id as string) ?? "";
    if (!manifestId) {
      setBuildStatus("error");
      return;
    }
    buildPackage(manifestId)
      .then((result) => {
        const meta = result?.data?.metadata;
        if (meta) {
          setPackageRef({ name: meta.package_name, version: meta.version });
          setBuildStatus("done");
        }
      })
      .catch(() => setBuildStatus("error"));
    setBuildStatus("building");
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(doc.text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleDownloadText = () => {
    const blob = new Blob([doc.text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${doc.rfq_number}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadJson = () => {
    const payload = {
      rfq_number: doc.rfq_number,
      facility_name: doc.facility_name,
      facility_id: doc.facility_id,
      confidence: doc.confidence,
      rank: doc.rank,
      quantity: doc.quantity,
      generated_at: new Date().toISOString(),
      text: doc.text,
      // Full OKH manifest is included so the recipient has the complete design spec
      okh_manifest: doc.okh_manifest ?? null,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${doc.rfq_number}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      {/* Card header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 bg-slate-50 px-5 py-4 dark:border-slate-800 dark:bg-slate-800/50">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-7 items-center justify-center rounded bg-slate-200 text-xs font-bold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
              #{doc.rank}
            </span>
            <h3 className="truncate font-semibold text-slate-800 dark:text-slate-100">
              {doc.facility_name}
            </h3>
            <ConfidencePill score={doc.confidence} />
          </div>
          <p className="mt-0.5 font-mono text-xs text-slate-400 dark:text-slate-500">
            {doc.rfq_number} · qty {doc.quantity}
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex shrink-0 gap-2">
          <button
            onClick={handleCopy}
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            {copied ? "✓ Copied!" : "Copy text"}
          </button>
          <button
            onClick={handleDownloadText}
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            ↓ .txt
          </button>
          <button
            onClick={handleDownloadJson}
            className="rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-400 dark:hover:bg-indigo-900/40"
          >
            ↓ .json
          </button>
          {doc.okh_manifest && (
            <button
              onClick={handleBuildPackage}
              disabled={buildStatus === "building"}
              className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-60 transition-colors dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400 dark:hover:bg-emerald-900/40"
            >
              {buildStatus === "building"
                ? "Building…"
                : buildStatus === "done"
                ? "✓ Package built"
                : buildStatus === "error"
                ? "⚠ Build failed"
                : "📦 Build package"}
            </button>
          )}
        </div>
      </div>

      {/* Package download link after build completes */}
      {packageRef && (
        <div className="border-b border-slate-100 bg-emerald-50 px-5 py-2.5 dark:border-slate-800 dark:bg-emerald-950/20">
          <p className="text-xs text-emerald-700 dark:text-emerald-400">
            Package built:{" "}
            <span className="font-mono font-medium">{packageRef.name} @ {packageRef.version}</span>
            {" · "}
            <a
              href={`/v1/api/package/${packageRef.name}/${packageRef.version}/download`}
              download
              className="underline hover:no-underline"
            >
              Download ↓
            </a>
          </p>
        </div>
      )}

      {/* Document preview */}
      <pre className="overflow-x-auto whitespace-pre-wrap break-words px-5 py-4 font-mono text-xs leading-relaxed text-slate-700 dark:text-slate-300">
        {doc.text}
      </pre>
    </div>
  );
}
