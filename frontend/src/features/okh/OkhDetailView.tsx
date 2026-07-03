import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import {
  fetchOkhDetail,
  validateOkh,
  type ValidationResult,
} from "../../api/ohm/okh";
import { LoadingState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/Badge";
import { OkhFileGroup } from "./OkhFileGroup";
import type { OkhManifest } from "../../types/okh";

interface Props {
  id: string;
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value) return null;
  return (
    <div className="flex gap-2">
      <dt className="w-32 shrink-0 text-xs text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="text-sm text-slate-700 dark:text-slate-200">{value}</dd>
    </div>
  );
}

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 rounded-full bg-slate-200 dark:bg-slate-700">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-500 dark:text-slate-400">{pct}%</span>
    </div>
  );
}

function errorText(err: unknown): string {
  const e = err as { message?: string; field?: string };
  if (e && typeof e.message === "string") {
    return e.field ? `${e.field}: ${e.message}` : e.message;
  }
  return JSON.stringify(err);
}

function ValidationPanel({ result }: { result: ValidationResult }) {
  const errors = result.errors ?? [];
  const warnings = result.warnings ?? [];
  const suggestions = result.suggestions ?? [];
  return (
    <section
      role="status"
      aria-label="Validation result"
      className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Validation
        </h2>
        <Badge variant={result.is_valid ? "green" : "yellow"}>
          {result.is_valid ? "Valid" : "Needs attention"}
        </Badge>
      </div>
      <div className="mb-3 flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
        <span>Score</span>
        <ConfidenceBar score={result.score} />
      </div>
      {errors.length > 0 && (
        <div className="mb-2">
          <p className="text-xs font-semibold text-red-600 dark:text-red-400">Errors</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-700 dark:text-slate-200">
            {errors.map((e, i) => (
              <li key={i}>{errorText(e)}</li>
            ))}
          </ul>
        </div>
      )}
      {warnings.length > 0 && (
        <div className="mb-2">
          <p className="text-xs font-semibold text-yellow-600 dark:text-yellow-400">Warnings</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-700 dark:text-slate-200">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
      {suggestions.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">Suggestions</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-700 dark:text-slate-200">
            {suggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
      {errors.length === 0 && warnings.length === 0 && suggestions.length === 0 && (
        <p className="text-sm text-slate-500 dark:text-slate-400">No issues reported.</p>
      )}
    </section>
  );
}

export function OkhDetailView({ id }: Props) {
  const navigate = useNavigate();
  const [validateState, setValidateState] = useState<"idle" | "running" | "done" | "error">("idle");
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [validateError, setValidateError] = useState<string | null>(null);

  const { data: okh, isLoading, isError, error, refetch } = useQuery<OkhManifest>({
    queryKey: ["okh-detail", id],
    queryFn: () => fetchOkhDetail(id),
    staleTime: 120_000,
  });

  const handleValidate = async () => {
    if (!okh) return;
    setValidateState("running");
    setValidateError(null);
    try {
      const res = await validateOkh(okh as unknown as Record<string, unknown>);
      setResult(res);
      setValidateState("done");
    } catch (e) {
      setValidateError(e instanceof Error ? e.message : "Validation failed.");
      setValidateState("error");
    }
  };

  if (isLoading) return <LoadingState message="Loading design…" />;
  if (isError || !okh) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Design not found."}
        onRetry={() => refetch()}
      />
    );
  }

  const title = okh.title || "Untitled Design";
  const allFiles = [...okh.design_files, ...okh.manufacturing_files, ...okh.making_instructions];

  return (
    <div className="space-y-8">
      <nav className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <Link to="/okh" className="hover:text-indigo-600 dark:hover:text-indigo-400">
          Designs
        </Link>
        <span aria-hidden="true">›</span>
        <span className="truncate text-slate-700 dark:text-slate-200">{title}</span>
      </nav>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">{title}</h1>
          {okh.function && <p className="text-base text-slate-600 dark:text-slate-300">{okh.function}</p>}
          {okh.description && okh.description !== okh.function && (
            <p className="text-sm text-slate-500 dark:text-slate-400">{okh.description}</p>
          )}
          <div className="flex flex-wrap gap-1.5 pt-1">
            {okh.version && <Badge variant="default">v{okh.version}</Badge>}
            {okh.documentation_language && (
              <Badge variant="blue">{okh.documentation_language.toUpperCase()}</Badge>
            )}
            {okh.manufacturing_processes.map((p) => (
              <Badge key={p} variant="indigo">{p}</Badge>
            ))}
          </div>
        </div>

        <div className="flex shrink-0 gap-2">
          <Button onClick={() => navigate(`/match?okh_id=${okh.id}&autorun=1`)}>
            ⚡ Run Match
          </Button>
          <Button variant="outline" onClick={handleValidate} disabled={validateState === "running"}>
            {validateState === "running" ? "Validating…" : "Validate"}
          </Button>
        </div>
      </div>

      {validateState === "error" && (
        <ErrorState description={validateError ?? "Validation failed."} onRetry={handleValidate} />
      )}
      {validateState === "done" && result && <ValidationPanel result={result} />}

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-1">
          <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Design Info
            </h2>
            <dl className="space-y-2">
              <MetaRow label="ID" value={<span className="font-mono text-xs">{okh.id}</span>} />
              {okh.repo && (
                <MetaRow
                  label="Repository"
                  value={
                    <a href={okh.repo} target="_blank" rel="noopener noreferrer"
                      className="block max-w-[180px] truncate text-indigo-600 hover:underline dark:text-indigo-400">
                      {okh.repo.replace(/^https?:\/\//, "")}
                    </a>
                  }
                />
              )}
              <MetaRow label="Licensor" value={okh.licensor?.name ?? null} />
              {okh.licensor?.affiliation && <MetaRow label="Org" value={okh.licensor.affiliation} />}
            </dl>
          </section>

          {(okh.license?.hardware || okh.license?.documentation || okh.license?.software) && (
            <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                License
              </h2>
              <dl className="space-y-2">
                <MetaRow label="Hardware" value={okh.license.hardware} />
                <MetaRow label="Documentation" value={okh.license.documentation} />
                <MetaRow label="Software" value={okh.license.software} />
              </dl>
            </section>
          )}

          {okh.materials.length > 0 && (
            <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Materials
              </h2>
              <ul className="space-y-2">
                {okh.materials.map((m, i) => (
                  <li key={i} className="flex items-center justify-between gap-2">
                    <span className="text-sm text-slate-700 dark:text-slate-200">{m.name}</span>
                    {m.quantity != null && (
                      <span className="shrink-0 text-xs text-slate-500 dark:text-slate-400">
                        {m.quantity} {m.unit}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {okh.keywords.length > 0 && (
            <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Keywords
              </h2>
              <div className="flex flex-wrap gap-1.5">
                {okh.keywords.map((k) => (
                  <Badge key={k} variant="default">{k}</Badge>
                ))}
              </div>
            </section>
          )}
        </div>

        <div className="space-y-6 lg:col-span-2">
          {allFiles.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-400 dark:border-slate-700 dark:text-slate-500">
              No file references attached to this design.
            </div>
          ) : (
            <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-5 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Files &amp; Documentation
              </h2>
              <div className="space-y-6">
                <OkhFileGroup title="Design Files" icon="📐" files={okh.design_files} />
                <OkhFileGroup title="Manufacturing Files" icon="🏭" files={okh.manufacturing_files} />
                <OkhFileGroup title="Making Instructions" icon="📋" files={okh.making_instructions} />
              </div>
            </section>
          )}

          {okh.intended_use && (
            <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Intended Use
              </h2>
              <p className="text-sm text-slate-600 dark:text-slate-300">{okh.intended_use}</p>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
