import { useState } from "react";
import type { OkhManifest } from "../../types/okh";
import {
  buildLocalOkhPackage,
  type LocalPackageInput,
  type LocalPackageResult,
  type LocalPackageStatus,
} from "./buildLocalOkhPackage";

interface Props {
  okh: LocalPackageInput["okh"];
  className?: string;
}

export function BuildPackageButton({ okh, className }: Props) {
  const [status, setStatus] = useState<LocalPackageStatus>("idle");
  const [result, setResult] = useState<LocalPackageResult | null>(null);

  const handleBuild = async () => {
    if (!okh?.id) {
      setStatus("error");
      setResult({
        status: "error",
        packageName: "okh-package",
        written: 0,
        failed: [],
        message: "Missing design id — cannot build package.",
      });
      return;
    }

    setStatus("building");
    setResult(null);
    try {
      const outcome = await buildLocalOkhPackage({ okh });
      setResult(outcome);
      setStatus(outcome.status);
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setResult({
        status: "error",
        packageName: okh.title || "okh-package",
        written: 0,
        failed: [],
        message: `Unexpected package build failure: ${message}`,
      });
      setStatus("error");
    }
  };

  return (
    <div className={className}>
      <button
        type="button"
        onClick={() => void handleBuild()}
        disabled={status === "building"}
        title="Save this design and its files to a folder on your computer"
        className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
      >
        {status === "building" ? "Building…" : "📦 Build Package"}
      </button>

      {result && status !== "cancelled" && status !== "idle" && (
        <p
          className={`mt-1.5 max-w-sm text-xs ${
            status === "error"
              ? "text-red-600 dark:text-red-400"
              : status === "partial"
                ? "text-amber-700 dark:text-amber-400"
                : "text-emerald-700 dark:text-emerald-400"
          }`}
          role="status"
        >
          {result.message}
          {result.failed.length > 0 && result.failed.length <= 5 && (
            <span className="mt-1 block font-mono text-[10px] opacity-80">
              {result.failed.map((f) => f.path).join(", ")}
            </span>
          )}
        </p>
      )}
    </div>
  );
}

/** Narrow a loose RFQ/API manifest blob into LocalPackageInput.okh when possible. */
export function okhFromUnknown(
  raw: Record<string, unknown> | null | undefined,
): OkhManifest | null {
  if (!raw || typeof raw.id !== "string") return null;
  return {
    id: raw.id,
    title: typeof raw.title === "string" ? raw.title : "Untitled Design",
    version: typeof raw.version === "string" ? raw.version : null,
    repo: typeof raw.repo === "string" ? raw.repo : null,
    function: typeof raw.function === "string" ? raw.function : null,
    description: typeof raw.description === "string" ? raw.description : null,
    intended_use: typeof raw.intended_use === "string" ? raw.intended_use : null,
    keywords: Array.isArray(raw.keywords) ? (raw.keywords as string[]) : [],
    documentation_language:
      typeof raw.documentation_language === "string" ? raw.documentation_language : null,
    license: (raw.license as OkhManifest["license"]) ?? null,
    licensor: (raw.licensor as OkhManifest["licensor"]) ?? null,
    contributors: Array.isArray(raw.contributors)
      ? (raw.contributors as OkhManifest["contributors"])
      : [],
    manufacturing_processes: Array.isArray(raw.manufacturing_processes)
      ? (raw.manufacturing_processes as string[])
      : [],
    materials: Array.isArray(raw.materials) ? (raw.materials as OkhManifest["materials"]) : [],
    design_files: Array.isArray(raw.design_files)
      ? (raw.design_files as OkhManifest["design_files"])
      : [],
    manufacturing_files: Array.isArray(raw.manufacturing_files)
      ? (raw.manufacturing_files as OkhManifest["manufacturing_files"])
      : [],
    making_instructions: Array.isArray(raw.making_instructions)
      ? (raw.making_instructions as OkhManifest["making_instructions"])
      : [],
    parts: Array.isArray(raw.parts) ? (raw.parts as OkhManifest["parts"]) : [],
    tool_list: Array.isArray(raw.tool_list) ? (raw.tool_list as string[]) : [],
    image: typeof raw.image === "string" ? raw.image : null,
    project_link: typeof raw.project_link === "string" ? raw.project_link : null,
  };
}
