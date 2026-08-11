import { useState } from "react";
import { FIELD_SM } from "../../components/ui/field";
import {
  BuildPackageButton,
  okhFromUnknown,
} from "../package/BuildPackageButton";
import type { RFQDocument } from "../../types/rfq";

interface Props {
  doc: RFQDocument;
}

function ConfidencePill({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const colorClass =
    pct >= 80
      ? "bg-success/10 text-success bg-success/10/40"
      : pct >= 50
        ? "bg-warning text-warning"
        : "bg-destructive/10 text-destructive bg-destructive/10/40";
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${colorClass}`}
    >
      {pct}% match
    </span>
  );
}

export function RfqDocumentCard({ doc }: Props) {
  const [copied, setCopied] = useState(false);
  const okh = okhFromUnknown(doc.okh_manifest);

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
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      {/* Card header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-background px-5 py-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-7 items-center justify-center rounded bg-muted text-xs font-bold text-muted-foreground">
              #{doc.rank}
            </span>
            <h3 className="truncate font-semibold text-foreground">
              {doc.facility_name}
            </h3>
            <ConfidencePill score={doc.confidence} />
          </div>
          <p className="mt-0.5 font-mono text-xs text-muted-foreground">
            {doc.rfq_number} · qty {doc.quantity}
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex shrink-0 gap-2">
          <button
            onClick={handleCopy}
            className={`${FIELD_SM} font-medium text-foreground hover:bg-background transition-colors dark:hover:bg-muted`}
          >
            {copied ? "Copied" : "Copy text"}
          </button>
          <button
            onClick={handleDownloadText}
            className={`${FIELD_SM} font-medium text-foreground hover:bg-background transition-colors dark:hover:bg-muted`}
          >
            ↓ .txt
          </button>
          <button
            onClick={handleDownloadJson}
            className={`${FIELD_SM} border-primary/30 bg-accent font-medium text-primary-ink hover:bg-accent dark:hover:bg-accent/40`}
          >
            ↓ .json
          </button>
          {okh && <BuildPackageButton okh={okh} />}
        </div>
      </div>

      {/* Document preview */}
      <pre className="overflow-x-auto whitespace-pre-wrap break-words px-5 py-4 font-mono text-xs leading-relaxed text-foreground">
        {doc.text}
      </pre>
    </div>
  );
}
