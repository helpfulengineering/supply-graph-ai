"use client";

/**
 * Generate an OKH manifest from one or more repository URLs.
 *
 * Submit-then-poll against async Celery jobs so generation can run longer than
 * the SPA nginx proxy timeout. Each URL is its own job with a real progress bar.
 *
 * The result is not saved to the catalogue. Without user auth there is no owner
 * and no provenance, so a save would put unattributed records into a shared
 * catalogue. Download, or hand the reviewed manifest straight to matching —
 * the API accepts an inline `okh_manifest`.
 */

import { useEffect, useMemo, useState } from "react";
import { FIELD, FIELD_SM, LABEL } from "../../components/ui/field";
import {
  PANEL,
  PANEL_ACCENT,
  PANEL_DANGER,
  PANEL_INSET,
  PANEL_WARNING,
} from "../../components/ui/surface";
import { PageHero } from "../../components/layout/PageHero";
import { useQueries } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { withNavState } from "../../lib/navState";
import { ApiError } from "../../api/ohm/client";
import {
  getGenerateJobStatus,
  revokeGenerateJob,
  submitGenerateJobs,
  type GenerateJobRef,
  type GenerateJobStatus,
  type OkhQualityReport,
} from "../../api/ohm/okh";
import { toQualityBanner } from "./qualityBanner";
import { downloadManifest } from "./serialize";
import { missingRequired } from "./manifestTiers";
import { TieredEditor } from "./TieredEditor";
import { parseRepoUrlList } from "./urlValidation";
import {
  aggregatePercent,
  isTerminalJobState,
  progressPercent,
  stageLabel,
} from "./jobProgress";
import { cn } from "@/lib/utils";

type Manifest = Record<string, unknown>;

/**
 * Turn a failure into something a person can act on. The shared-token quota
 * case is called out specifically because it is expected to happen in normal
 * use, and "429" tells a non-technical user nothing.
 */
export function generationErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 404:
        return "That repository couldn't be read. It may be private, misspelled, or moved — only public repositories are supported.";
      case 429:
        return "The shared rate limit for reading repositories has been reached. Please try again in a little while.";
      case 422:
        return `The repository couldn't be processed: ${err.message}`;
      case 503:
        return "Background generation isn't available on this node right now. Please try again later.";
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

function ProgressBar({
  label,
  value,
  id,
}: {
  label: string;
  value: number;
  id: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between gap-2 text-sm">
        <span className="text-foreground">{label}</span>
        <span className="tabular-nums text-muted-foreground">{value}%</span>
      </div>
      {/* role on the track so a 0% fill is still an accessible, visible control */}
      <div
        id={id}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
        aria-label={label}
        className="h-2 overflow-hidden rounded-full bg-muted"
      >
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-300"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

export function GenerateView() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<GenerateJobRef[]>([]);
  const [active, setActive] = useState(false);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [report, setReport] = useState<OkhQualityReport | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const statusQueries = useQueries({
    queries: jobs.map((job) => ({
      queryKey: ["okh-generate-job", job.job_id] as const,
      queryFn: () => getGenerateJobStatus(job.job_id),
      enabled: active && jobs.length > 0,
      refetchInterval: (q: {
        state: { data: GenerateJobStatus | undefined };
      }) => (isTerminalJobState(q.state.data?.state) ? false : 1000),
      retry: false,
    })),
  });

  const statuses = useMemo(() => {
    return jobs.map((job, i) => {
      const data = statusQueries[i]?.data;
      return {
        ...job,
        state: data?.state ?? "PENDING",
        stage: data?.stage,
        fraction: data?.fraction,
        message: data?.message,
        error: data?.error,
        manifest: data?.manifest,
        quality_report: data?.quality_report,
      };
    });
  }, [jobs, statusQueries]);

  const allTerminal =
    jobs.length > 0 && statuses.every((s) => isTerminalJobState(s.state));

  useEffect(() => {
    if (!active || !allTerminal) return;
    setActive(false);
    const successes = statuses.filter(
      (s) => s.state === "SUCCESS" && s.manifest,
    );
    const failures = statuses.filter((s) => s.state === "FAILURE");
    if (successes.length === 0) {
      if (failures.length > 0) {
        setError(
          failures[0].error
            ? `Generation failed: ${failures[0].error}`
            : "Generation failed.",
        );
      } else if (!error) {
        setError("Generation was cancelled.");
      }
      return;
    }
    const pick = successes[0];
    setSelectedJobId(pick.job_id);
    setManifest(pick.manifest as Manifest);
    setReport((pick.quality_report as OkhQualityReport | null) ?? null);
    if (failures.length > 0) {
      setError(
        `${failures.length} of ${statuses.length} URL${statuses.length === 1 ? "" : "s"} failed. Showing a successful result.`,
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- finalize once when the batch ends
  }, [active, allTerminal, statuses]);

  const run = async () => {
    const parsed = parseRepoUrlList(url);
    if (!parsed.valid) {
      setUrlError(parsed.message ?? "That URL can't be used.");
      return;
    }
    setUrlError(null);
    setError(null);
    setManifest(null);
    setReport(null);
    setSelectedJobId(null);
    setJobs([]);
    setActive(true);

    try {
      const batch = await submitGenerateJobs(parsed.urls);
      setJobs(batch.jobs);
    } catch (err) {
      setActive(false);
      setError(generationErrorMessage(err));
    }
  };

  const cancel = async () => {
    const running = statuses.filter((s) => !isTerminalJobState(s.state));
    await Promise.allSettled(running.map((s) => revokeGenerateJob(s.job_id)));
    setActive(false);
    setError("Generation was cancelled.");
  };

  const banner = manifest ? toQualityBanner(report) : null;
  const missing = manifest ? missingRequired(manifest) : [];
  const aggregate = aggregatePercent(statuses);
  const showProgress = active || (jobs.length > 0 && !manifest && !allTerminal);

  return (
    <div className="space-y-6">
      <div>
        <PageHero
          title="Generate a design from a URL"
          crumb="repository · extraction · review"
        />
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Point OHM at a public GitHub or GitLab repository and it will read
          what's there into a structured design record. You can paste several
          URLs separated by commas. Extraction is imperfect by nature — you
          review and correct it before doing anything with it.
        </p>
      </div>

      <div className={PANEL}>
        <label htmlFor="repo-url" className={LABEL}>
          Repository URL(s)
        </label>
        <div className="mt-1.5 flex gap-2">
          <input
            id="repo-url"
            type="text"
            value={url}
            disabled={active}
            placeholder="https://github.com/owner/project, https://gitlab.com/…"
            onChange={(e) => {
              setUrl(e.target.value);
              if (urlError) setUrlError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !active) void run();
            }}
            aria-invalid={urlError ? true : undefined}
            aria-describedby={urlError ? "repo-url-error" : "repo-url-hint"}
            className={`${FIELD} flex-1`}
          />
          <button
            type="button"
            onClick={() => void run()}
            disabled={active}
            className="rounded-md bg-primary px-5 py-2 text-sm font-semibold text-on-accent hover:bg-primary disabled:opacity-60"
          >
            {active ? "Reading…" : "Generate"}
          </button>
        </div>
        <p id="repo-url-hint" className="mt-1.5 text-xs text-muted-foreground">
          Separate multiple repositories with commas.
        </p>
        {urlError && (
          <p
            id="repo-url-error"
            role="alert"
            className="mt-1.5 text-sm text-destructive"
          >
            {urlError}
          </p>
        )}
      </div>

      {showProgress && (
        <div role="status" className={cn(PANEL_ACCENT, "space-y-4")}>
          <ProgressBar
            id="generate-aggregate-progress"
            label={
              jobs.length > 1
                ? `Overall progress (${statuses.filter((s) => s.state === "SUCCESS").length}/${jobs.length} done)`
                : stageLabel(statuses[0]?.stage, statuses[0]?.state)
            }
            value={aggregate}
          />
          {statuses.length > 1 && (
            <ul className="space-y-3">
              {statuses.map((s) => (
                <li key={s.job_id}>
                  <p className="mb-1 truncate font-mono text-xs text-muted-foreground">
                    {s.url}
                  </p>
                  <ProgressBar
                    id={`generate-progress-${s.job_id}`}
                    label={stageLabel(s.stage, s.state)}
                    value={progressPercent(s.state, s.fraction)}
                  />
                </li>
              ))}
            </ul>
          )}
          {active && (
            <button
              type="button"
              onClick={() => void cancel()}
              className={FIELD_SM}
            >
              Cancel
            </button>
          )}
        </div>
      )}

      {error && (
        <p
          role="alert"
          className={cn(
            PANEL_DANGER,
            "text-sm text-destructive bg-destructive/10",
          )}
        >
          {error}
        </p>
      )}

      {allTerminal &&
        statuses.filter((s) => s.state === "SUCCESS" && s.manifest).length >
          1 && (
          <div className="flex flex-wrap gap-2">
            {statuses
              .filter((s) => s.state === "SUCCESS" && s.manifest)
              .map((s) => (
                <button
                  key={s.job_id}
                  type="button"
                  onClick={() => {
                    setSelectedJobId(s.job_id);
                    setManifest(s.manifest as Manifest);
                    setReport(
                      (s.quality_report as OkhQualityReport | null) ?? null,
                    );
                  }}
                  className={
                    selectedJobId === s.job_id
                      ? "rounded-md bg-primary px-3 py-1.5 text-sm text-on-accent"
                      : "rounded-md border border-border px-3 py-1.5 text-sm"
                  }
                >
                  Review {s.url?.replace(/^https:\/\//, "")}
                </button>
              ))}
          </div>
        )}

      {manifest && banner && (
        <>
          <div className={banner.tone === "warn" ? PANEL_WARNING : PANEL_INSET}>
            <p className="text-sm font-medium text-foreground">
              {banner.headline}
            </p>
            {banner.recommendations.length > 0 && (
              <ul className="mt-2 list-disc pl-5 text-sm text-muted-foreground">
                {banner.recommendations.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            )}
          </div>

          <div className={PANEL}>
            <TieredEditor manifest={manifest} onChange={setManifest} />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={missing.length > 0}
              onClick={() => downloadManifest(manifest, "yaml")}
              className="rounded-md bg-primary px-5 py-2 text-sm font-semibold text-on-accent hover:bg-primary disabled:opacity-60"
            >
              Download YAML
            </button>
            <button
              type="button"
              disabled={missing.length > 0}
              onClick={() => downloadManifest(manifest, "json")}
              className={`${FIELD} px-5 font-semibold disabled:opacity-60`}
            >
              Download JSON
            </button>
            <button
              type="button"
              disabled={missing.length > 0}
              onClick={() =>
                router.push(
                  withNavState("/match", {
                    okhManifest: manifest,
                    okhTitle:
                      typeof manifest.title === "string"
                        ? manifest.title
                        : undefined,
                  }),
                )
              }
              className={`${FIELD} px-5 font-semibold disabled:opacity-60`}
            >
              Find who can build this
            </button>
            {missing.length > 0 && (
              <p className="text-sm text-warning">
                Fill in {missing.length} required field
                {missing.length === 1 ? "" : "s"} first.
              </p>
            )}
          </div>

          <p className="text-xs text-muted-foreground">
            Generated designs aren't saved to the catalogue — download the file
            and keep it, or add it yourself once you're happy with it.
          </p>
        </>
      )}
    </div>
  );
}
