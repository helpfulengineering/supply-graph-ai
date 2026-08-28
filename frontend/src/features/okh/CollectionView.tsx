"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  diffCollection,
  exportCollection,
  importCollection,
} from "@/api/ohm/okh-collection";
import type {
  CollectionDiff,
  CollectionImportReport,
} from "@/api/ohm/okh-collection";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { CHECKBOX, CHOICE_ROW, HINT, LABEL } from "@/components/ui/field";
import { PANEL, PANEL_BODY, PANEL_INSET } from "@/components/ui/surface";
import { BODY_MUTED, CAPTION } from "@/components/ui/typography";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils";
import { COLLECTION_CRUMB } from "./collectionCrumb";

/**
 * Move a body of designs between nodes.
 *
 * Collections are one page where single records are actions on the page that
 * owns them: export, compare and import are one artifact through one flow, and
 * the compare in the middle is the whole reason the flow exists — a maintainer
 * sees what an import would do while it is still a question.
 */
export function CollectionView() {
  const { hasWrite, reportAuthFailure } = useAuth();
  const { showSuccess } = useToast();
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [diff, setDiff] = useState<CollectionDiff | null>(null);
  const [report, setReport] = useState<CollectionImportReport | null>(null);
  const [preview, setPreview] = useState(true);

  const download = useMutation({
    mutationFn: exportCollection,
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "ohm-collection.zip";
      link.click();
      URL.revokeObjectURL(url);
    },
  });

  const compare = useMutation({
    mutationFn: () => diffCollection(file!),
    onSuccess: (result) => {
      setDiff(result);
      setReport(null);
    },
  });

  const apply = useMutation({
    mutationFn: () => importCollection(file!, preview),
    onSuccess: (result) => {
      setReport(result);
      if (!result.dry_run) {
        showSuccess(`Imported ${result.imported} design(s)`);
        void queryClient.invalidateQueries({ queryKey: ["okh-list-all"] });
      }
    },
    onError: reportAuthFailure,
  });

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <PageHero
        title="Design collection"
        breadcrumb={[
          { label: "Designs", href: "/okh" },
          { label: "Collection" },
        ]}
        crumb={COLLECTION_CRUMB}
        description="Move a whole catalogue between OHM nodes, one archive at a time."
      />

      <section
        aria-labelledby="export"
        className={cn(PANEL, PANEL_BODY, "mb-6")}
      >
        <SectionHeading id="export" role="card">
          Export
        </SectionHeading>
        <p className={cn(BODY_MUTED, "mt-1")}>
          Produces an archive another OHM node can import. Private designs are
          included only if your key can see them.
        </p>
        <Button
          variant="outline"
          size="sm"
          className="mt-3"
          disabled={download.isPending}
          onClick={() => download.mutate()}
        >
          {download.isPending ? "Building…" : "Download collection"}
        </Button>
        {download.isError && (
          <p className={cn(CAPTION, "mt-2 text-destructive")} role="alert">
            {(download.error as Error).message}
          </p>
        )}
      </section>

      <section
        aria-labelledby="compare"
        className={cn(PANEL, PANEL_BODY, "mb-6")}
      >
        <SectionHeading id="compare" role="card">
          Compare
        </SectionHeading>
        <p className={cn(BODY_MUTED, "mt-1")}>
          Reads an archive and says how it differs from this catalogue. Writes
          nothing.
        </p>

        <div className="mt-3">
          <label className={LABEL} htmlFor="collection-file">
            Collection archive
          </label>
          <input
            id="collection-file"
            type="file"
            accept=".zip"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setDiff(null);
              setReport(null);
            }}
            className="mt-1 block w-full text-sm text-foreground file:mr-3 file:min-h-9 file:rounded-md file:border file:border-border file:bg-muted file:px-3 file:text-sm file:font-medium hover:file:bg-accent"
          />
          <p className={HINT}>
            A zip produced by `ohm okh export-collection`, or by Export above.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="mt-3"
          disabled={!file || compare.isPending}
          onClick={() => compare.mutate()}
        >
          {compare.isPending ? "Reading…" : "Compare"}
        </Button>

        {compare.isError && (
          <p className={cn(CAPTION, "mt-2 text-destructive")} role="alert">
            {(compare.error as Error).message}
          </p>
        )}

        {diff && (
          // Symmetric, deliberately: an import is a one-way operation, and
          // seeing only what would arrive hides that the archive is missing
          // things this node has.
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className={PANEL_INSET}>
              <p className="text-sm font-medium text-foreground">
                Only in the archive ({diff.only_in_archive.length})
              </p>
              <ul className="mt-1 space-y-0.5">
                {diff.only_in_archive.map((id) => (
                  <li key={id} className={cn(CAPTION, "font-mono")}>
                    {id}
                  </li>
                ))}
              </ul>
            </div>
            <div className={PANEL_INSET}>
              <p className="text-sm font-medium text-foreground">
                Only here ({diff.only_local.length})
              </p>
              <ul className="mt-1 space-y-0.5">
                {diff.only_local.map((id) => (
                  <li key={id} className={cn(CAPTION, "font-mono")}>
                    {id}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </section>

      <section aria-labelledby="import" className={cn(PANEL, PANEL_BODY)}>
        <SectionHeading id="import" role="card">
          Import
        </SectionHeading>
        <p className={cn(BODY_MUTED, "mt-1")}>
          Writes the archive&rsquo;s designs into this node. Available once the
          same file has been compared.
        </p>

        <label className={cn(CHOICE_ROW, "mt-3")}>
          <input
            type="checkbox"
            className={CHECKBOX}
            checked={preview}
            onChange={(e) => setPreview(e.target.checked)}
          />
          {/* An explicit checkbox rather than a hidden default: "this run wrote
              nothing" is a fact the reader should have chosen, not discovered. */}
          <span>Preview only — report what would happen, write nothing</span>
        </label>

        <Button
          size="sm"
          className="mt-3"
          disabled={!file || !diff || apply.isPending || !hasWrite}
          title={hasWrite ? undefined : "Importing needs write access"}
          onClick={() => apply.mutate()}
        >
          {apply.isPending
            ? "Importing…"
            : preview
              ? "Preview import"
              : "Import"}
        </Button>

        {apply.isError && (
          <p className={cn(CAPTION, "mt-2 text-destructive")} role="alert">
            {(apply.error as Error).message}
          </p>
        )}

        {report && (
          <div className={cn(PANEL_INSET, "mt-4 text-sm")} role="status">
            <p className="text-foreground">
              {report.dry_run ? "Preview: " : ""}
              {report.new.length} new · {report.duplicate.length} duplicate ·{" "}
              {report.conflict.length} conflict
              {report.dry_run ? "" : ` · ${report.imported} imported`}
            </p>
            {report.conflict.length > 0 && (
              <p className={cn(CAPTION, "mt-1")}>
                A conflict is the same id holding different content. Those are
                left alone.
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
