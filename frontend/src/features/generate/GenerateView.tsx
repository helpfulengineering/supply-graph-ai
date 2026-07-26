/**
 * Generate an OKH manifest from a repository URL (Slices A + B).
 *
 * Synchronous by design — production has no LLM key, so extraction always
 * degrades to the heuristic layers and finishes inside the ingress timeout.
 * The loading state is honestly indeterminate: no fake progress stages, an
 * up-front warning that it can take about a minute, and a Cancel that really
 * aborts the request.
 *
 * The result is not saved to the catalogue. Without user auth there is no owner
 * and no provenance, so a save would put unattributed records into a shared
 * catalogue. Download is the terminal action until auth exists.
 */

import { useRef, useState } from "react";
import { ApiError } from "../../api/ohm/client";
import { generateOkhFromUrl, type OkhQualityReport } from "../../api/ohm/okh";
import { toQualityBanner } from "./qualityBanner";
import { missingRequired } from "./manifestTiers";
import { TieredEditor } from "./TieredEditor";
import { checkRepoUrl } from "./urlValidation";

type Manifest = Record<string, unknown>;

/** How long to wait before giving up. Azure ingress caps sync requests near 4m. */
const TIMEOUT_MS = 90_000;

/**
 * Turn a failure into something a person can act on. The shared-token quota
 * case is called out specifically because it is expected to happen in normal
 * use, and "429" tells a non-technical user nothing.
 */
export function generationErrorMessage(err: unknown): string {
  if (err instanceof DOMException && err.name === "AbortError") {
    return "Generation was cancelled.";
  }
  if (err instanceof ApiError) {
    switch (err.status) {
      case 404:
        return "That repository couldn't be read. It may be private, misspelled, or moved — only public repositories are supported.";
      case 429:
        return "The shared rate limit for reading repositories has been reached. Please try again in a little while.";
      case 422:
        return `The repository couldn't be processed: ${err.message}`;
      case 504:
      case 408:
        return "The repository took too long to read. Very large repositories can exceed the time limit.";
      default:
        return err.status >= 500
          ? "Something went wrong while reading the repository. Please try again."
          : err.message;
    }
  }
  return err instanceof Error ? err.message : "Generation failed.";
}

function downloadJson(manifest: Manifest, filename: string) {
  const blob = new Blob([JSON.stringify(manifest, null, 2)], {
    type: "application/json",
  });
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(href);
}

function safeFilename(manifest: Manifest): string {
  const title = typeof manifest.title === "string" ? manifest.title : "design";
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
  return `${slug || "design"}.okh.json`;
}

export function GenerateView() {
  const [url, setUrl] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [report, setReport] = useState<OkhQualityReport | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const run = async () => {
    const check = checkRepoUrl(url);
    if (!check.valid) {
      setUrlError(check.message ?? "That URL can't be used.");
      return;
    }
    setUrlError(null);
    setError(null);
    setManifest(null);
    setPending(true);

    const controller = new AbortController();
    abortRef.current = controller;
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

    try {
      const result = await generateOkhFromUrl(check.normalized!, controller.signal);
      setManifest(result.manifest);
      setReport(result.qualityReport);
    } catch (err) {
      setError(generationErrorMessage(err));
    } finally {
      clearTimeout(timer);
      abortRef.current = null;
      setPending(false);
    }
  };

  const banner = manifest ? toQualityBanner(report) : null;
  const missing = manifest ? missingRequired(manifest) : [];

  return (
    <div className="space-y-6 py-4">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Generate a design from a URL</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Point OHM at a public GitHub or GitLab repository and it will read what's there
          into a structured design record. Extraction is imperfect by nature — you review
          and correct it before doing anything with it.
        </p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
        <label htmlFor="repo-url" className="block text-sm font-medium text-foreground">
          Repository URL
        </label>
        <div className="mt-1.5 flex gap-2">
          <input
            id="repo-url"
            type="url"
            value={url}
            disabled={pending}
            placeholder="https://github.com/owner/project"
            onChange={(e) => {
              setUrl(e.target.value);
              if (urlError) setUrlError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !pending) run();
            }}
            aria-invalid={urlError ? true : undefined}
            aria-describedby={urlError ? "repo-url-error" : undefined}
            className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
          />
          <button
            type="button"
            onClick={run}
            disabled={pending}
            className="rounded-md bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {pending ? "Reading…" : "Generate"}
          </button>
        </div>
        {urlError && (
          <p id="repo-url-error" role="alert" className="mt-1.5 text-sm text-red-600 dark:text-red-400">
            {urlError}
          </p>
        )}
      </div>

      {pending && (
        <div
          role="status"
          className="rounded-xl border border-indigo-100 bg-indigo-50 p-5 dark:border-indigo-900 dark:bg-indigo-950/30"
        >
          <p className="text-sm text-foreground">
            Reading the repository. This can take up to a minute — larger repositories
            take longer.
          </p>
          <button
            type="button"
            onClick={() => abortRef.current?.abort()}
            className="mt-3 rounded-md border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600"
          >
            Cancel
          </button>
        </div>
      )}

      {error && (
        <p
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        >
          {error}
        </p>
      )}

      {manifest && banner && (
        <>
          <div
            className={
              banner.tone === "warn"
                ? "rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/40"
                : "rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/40"
            }
          >
            <p className="text-sm font-medium text-foreground">{banner.headline}</p>
            {banner.recommendations.length > 0 && (
              <ul className="mt-2 list-disc pl-5 text-sm text-muted-foreground">
                {banner.recommendations.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
            <TieredEditor manifest={manifest} onChange={setManifest} />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={missing.length > 0}
              onClick={() => downloadJson(manifest, safeFilename(manifest))}
              className="rounded-md bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              Download JSON
            </button>
            {missing.length > 0 && (
              <p className="text-sm text-amber-700 dark:text-amber-400">
                Fill in {missing.length} required field{missing.length === 1 ? "" : "s"}{" "}
                first.
              </p>
            )}
          </div>

          <p className="text-xs text-muted-foreground">
            Generated designs aren't saved to the catalogue — download the file and keep
            it, or add it yourself once you're happy with it.
          </p>
        </>
      )}
    </div>
  );
}
