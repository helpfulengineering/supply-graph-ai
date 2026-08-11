"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { fetchOkhDetail } from "../../api/ohm/okh";
import { LoadingState, ErrorState } from "../../components/ui/states";
import { enrichFileRef } from "./okhFilePath";
import {
  decodeFilePathFromRoute,
  OkhFilePreviewContent,
} from "./OkhFilePreviewContent";

export function OkhFilePreviewPage() {
  const { id, path } = useParams<{ id: string; path: string[] }>();
  const filePathEncoded = Array.isArray(path) ? path.join("/") : path;
  const filePath = filePathEncoded
    ? decodeFilePathFromRoute(filePathEncoded)
    : "";

  const {
    data: okh,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["okh-detail", id],
    queryFn: () => fetchOkhDetail(id!),
    enabled: Boolean(id),
  });

  const file = useMemo(() => {
    if (!okh || !filePath) return null;
    const all = [
      ...okh.design_files,
      ...okh.manufacturing_files,
      ...okh.making_instructions,
    ];
    const match = all.find((f) => f.path === filePath);
    return enrichFileRef(
      match ?? { title: "", path: filePath, type: "", metadata: {} },
    );
  }, [okh, filePath]);

  if (!id) {
    return <ErrorState description="Missing design ID." />;
  }
  if (!filePath) {
    return <ErrorState description="Missing file path." />;
  }
  if (isLoading) return <LoadingState message="Loading file…" />;
  if (isError || !okh) {
    return (
      <ErrorState
        description={
          error instanceof Error ? error.message : "Design not found."
        }
      />
    );
  }
  if (!file) {
    return <ErrorState description="File not found in manifest." />;
  }

  const title = okh.title || "Untitled Design";

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/okh" className="hover:text-primary">
          Designs
        </Link>
        <span aria-hidden="true">›</span>
        <Link href={`/okh/${id}`} className="truncate hover:text-primary">
          {title}
        </Link>
        <span aria-hidden="true">›</span>
        <span className="truncate font-mono text-xs text-foreground">
          {file.display_path ?? file.path}
        </span>
      </nav>
      <OkhFilePreviewContent okhId={id} file={file} fullPage />
    </div>
  );
}
