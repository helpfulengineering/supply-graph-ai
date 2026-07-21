import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { OkhManifest } from "../../types/okh";
import {
  buildPackageFromManifest,
  packageDetailPath,
} from "../../api/package";
import {
  buildLocalOkhPackage,
  type LocalPackageInput,
  type LocalPackageResult,
  type LocalPackageStatus,
} from "./buildLocalOkhPackage";
import { useAuth } from "../../context/AuthContext";
import { Button } from "../../components/ui/button";

interface Props {
  okh: LocalPackageInput["okh"];
  className?: string;
}

export function BuildPackageButton({ okh, className }: Props) {
  const { reportAuthFailure } = useAuth();
  const queryClient = useQueryClient();
  const [localStatus, setLocalStatus] = useState<LocalPackageStatus>("idle");
  const [localResult, setLocalResult] = useState<LocalPackageResult | null>(null);
  const [serverLink, setServerLink] = useState<string | null>(null);

  const serverBuild = useMutation({
    mutationFn: () => buildPackageFromManifest(okh.id),
    onSuccess: (meta) => {
      void queryClient.invalidateQueries({ queryKey: ["package-list"] });
      if (meta.package_name && meta.version) {
        setServerLink(packageDetailPath(meta.package_name, meta.version));
      }
    },
    onError: reportAuthFailure,
  });

  const handleLocal = async () => {
    if (!okh?.id) return;
    setLocalStatus("building");
    setLocalResult(null);
    try {
      const outcome = await buildLocalOkhPackage({ okh });
      setLocalResult(outcome);
      setLocalStatus(outcome.status);
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setLocalResult({
        status: "error",
        packageName: okh.title || "okh-package",
        written: 0,
        failed: [],
        message: `Unexpected package build failure: ${message}`,
      });
      setLocalStatus("error");
    }
  };

  return (
    <div className={className}>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          disabled={serverBuild.isPending || !okh?.id}
          title="Build package on the OHM server into package storage"
          onClick={() => {
            setServerLink(null);
            serverBuild.mutate();
          }}
        >
          {serverBuild.isPending ? "Building on server…" : "📦 Build on server"}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={localStatus === "building"}
          title="Save this design and its files to a folder on your computer"
          onClick={() => void handleLocal()}
        >
          {localStatus === "building" ? "Saving…" : "Save folder locally…"}
        </Button>
      </div>

      {serverBuild.isSuccess && (
        <p className="mt-1.5 max-w-sm text-xs text-emerald-700 dark:text-emerald-400" role="status">
          Built {serverBuild.data.package_name}@{serverBuild.data.version}.{" "}
          {serverLink && (
            <Link to={serverLink} className="font-semibold underline">
              Open package
            </Link>
          )}
        </p>
      )}
      {serverBuild.isError && (
        <p className="mt-1.5 max-w-sm text-xs text-red-600" role="alert">
          {serverBuild.error instanceof Error
            ? serverBuild.error.message
            : "Server build failed."}
        </p>
      )}

      {localResult && localStatus !== "cancelled" && localStatus !== "idle" && (
        <p
          className={`mt-1.5 max-w-sm text-xs ${
            localStatus === "error"
              ? "text-red-600"
              : localStatus === "partial"
                ? "text-amber-700"
                : "text-emerald-700"
          }`}
          role="status"
        >
          {localResult.message}
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
