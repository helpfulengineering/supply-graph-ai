"use client";

import { useEffect, useState } from "react";
import { FIELD_SM } from "../../components/ui/field";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import type { OkhFileRef } from "../../types/okh";
import {
  canPreviewFile,
  encodePathSegments,
  filePrimaryLabel,
  inferRenderTier,
  isImageFile,
  isMarkdownFile,
  isPdfFile,
} from "./okhFilePath";
import { okhFileHref } from "./okhFileHref";

const MAX_TEXT_PREVIEW_BYTES = 5 * 1024 * 1024;

interface Props {
  okhId: string;
  file: OkhFileRef;
  fullPage?: boolean;
}

export function OkhFilePreviewContent({
  okhId,
  file,
  fullPage = false,
}: Props) {
  const href = okhFileHref(okhId, file);
  const label = filePrimaryLabel(file);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const tier =
    file.render_tier ?? inferRenderTier(file.display_path ?? file.path);
  const previewable = canPreviewFile(file);
  const showImage = previewable && isImageFile(file);
  const showPdf = previewable && isPdfFile(file) && !showImage;
  const showTextFetch =
    previewable && tier === "text_viewer" && !showImage && !showPdf;

  useEffect(() => {
    if (!showTextFetch) {
      setTextContent(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setTextContent(null);
    fetch(href)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const len = Number(res.headers.get("content-length") || 0);
        if (len > MAX_TEXT_PREVIEW_BYTES) {
          throw new Error("File too large for inline preview");
        }
        return res.text();
      })
      .then((text) => {
        if (!cancelled) setTextContent(text);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load preview");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [href, showTextFetch]);

  const wrapperClass = fullPage
    ? "min-h-[50vh] space-y-4"
    : "mt-2 mb-4 space-y-3 rounded-lg border border-primary/30 bg-accent/40 p-4";

  if (!previewable) {
    return (
      <div className={wrapperClass}>
        <p className="text-sm text-muted-foreground">
          <span className="font-medium">{label}</span>
          {file.file_type_display && (
            <span className="ml-2 text-xs text-muted-foreground">
              ({file.file_type_display})
            </span>
          )}
        </p>
        <p className="font-mono text-xs text-muted-foreground">
          {file.display_path ?? file.path}
        </p>
        <p className="text-sm text-muted-foreground">
          No in-browser preview for this file type.
        </p>
        <a
          href={href}
          download
          className="inline-flex rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent hover:bg-primary"
        >
          Download
        </a>
      </div>
    );
  }

  return (
    <div className={wrapperClass}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">{label}</p>
          <p className="truncate font-mono text-xs text-muted-foreground">
            {file.display_path ?? file.path}
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          {!fullPage && (
            <Link
              href={`/okh/${encodeURIComponent(okhId)}/files/${encodePathSegments(file.path)}`}
              className={`${FIELD_SM} font-medium text-muted-foreground hover:bg-background`}
            >
              Full preview
            </Link>
          )}
          <a
            href={href}
            download
            className={`${FIELD_SM} font-medium text-muted-foreground hover:bg-background`}
          >
            Download
          </a>
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className={`${FIELD_SM} font-medium text-muted-foreground hover:bg-background`}
          >
            Open tab
          </a>
        </div>
      </div>

      {showImage && (
        <img
          src={href}
          alt={label}
          className="max-h-96 w-full rounded-md border border-border bg-card object-contain"
        />
      )}

      {showPdf && (
        <iframe
          src={href}
          title={label}
          className="h-[32rem] w-full rounded-md border border-border bg-card"
        />
      )}

      {showTextFetch && (
        <>
          {loading && (
            <p className="text-sm text-muted-foreground">Loading preview…</p>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
          {textContent != null && isMarkdownFile(file) && (
            <article className="max-w-none space-y-2 rounded-md bg-card p-3 text-sm text-foreground [&_h1]:text-lg [&_h1]:font-bold [&_h2]:text-base [&_h2]:font-semibold [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-background [&_pre]:p-3">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {textContent}
              </ReactMarkdown>
            </article>
          )}
          {textContent != null && !isMarkdownFile(file) && (
            <pre className="max-h-96 overflow-auto rounded-md bg-card p-3 text-xs text-foreground">
              {textContent}
            </pre>
          )}
        </>
      )}
    </div>
  );
}

export function decodeFilePathFromRoute(encoded: string): string {
  return encoded
    .split("/")
    .map((segment) => decodeURIComponent(segment))
    .join("/");
}
