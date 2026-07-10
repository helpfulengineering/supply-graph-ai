import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Link } from "react-router-dom";
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

export function OkhFilePreviewContent({ okhId, file, fullPage = false }: Props) {
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
  const showTextFetch = previewable && tier === "text_viewer" && !showImage && !showPdf;

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
    : "mt-2 mb-4 space-y-3 rounded-lg border border-indigo-200 bg-indigo-50/40 p-4 dark:border-indigo-800 dark:bg-indigo-950/20";

  if (!previewable) {
    return (
      <div className={wrapperClass}>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          <span className="font-medium">{label}</span>
          {file.file_type_display && (
            <span className="ml-2 text-xs text-slate-500">({file.file_type_display})</span>
          )}
        </p>
        <p className="font-mono text-xs text-slate-500">{file.display_path ?? file.path}</p>
        <p className="text-sm text-slate-500">No in-browser preview for this file type.</p>
        <a
          href={href}
          download
          className="inline-flex rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
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
          <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{label}</p>
          <p className="truncate font-mono text-xs text-slate-500">{file.display_path ?? file.path}</p>
        </div>
        <div className="flex shrink-0 gap-2">
          {!fullPage && (
            <Link
              to={`/okh/${encodeURIComponent(okhId)}/files/${encodePathSegments(file.path)}`}
              className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300"
            >
              Full preview
            </Link>
          )}
          <a
            href={href}
            download
            className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300"
          >
            Download
          </a>
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300"
          >
            Open tab
          </a>
        </div>
      </div>

      {showImage && (
        <img
          src={href}
          alt={label}
          className="max-h-96 w-full rounded-md border border-slate-100 bg-white object-contain dark:border-slate-800"
        />
      )}

      {showPdf && (
        <iframe
          src={href}
          title={label}
          className="h-[32rem] w-full rounded-md border border-slate-200 bg-white dark:border-slate-700"
        />
      )}

      {showTextFetch && (
        <>
          {loading && <p className="text-sm text-slate-500">Loading preview…</p>}
          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
          {textContent != null && isMarkdownFile(file) && (
            <article className="max-w-none space-y-2 rounded-md bg-white p-3 text-sm text-slate-700 dark:bg-slate-900 dark:text-slate-200 [&_h1]:text-lg [&_h1]:font-bold [&_h2]:text-base [&_h2]:font-semibold [&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1 [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-slate-50 [&_pre]:p-3">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{textContent}</ReactMarkdown>
            </article>
          )}
          {textContent != null && !isMarkdownFile(file) && (
            <pre className="max-h-96 overflow-auto rounded-md bg-white p-3 text-xs text-slate-800 dark:bg-slate-950 dark:text-slate-200">
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
