"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  fetchOkhDetail,
  validateOkh,
  type ValidationResult,
} from "../../api/ohm/okh";
import { LoadingState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/Badge";
import { OkhFileGroup } from "./OkhFileGroup";
import { BuildPackageButton } from "../package/BuildPackageButton";
import { ReleasesStrip } from "../package/ReleasesStrip";
import { AuthorshipPanel } from "./AuthorshipPanel";
import { VisibilityControl } from "./VisibilityControl";
import { AttestationsPanel } from "../identity/AttestationsPanel";
import type { OkhManifest } from "../../types/okh";

interface Props {
  id: string;
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value) return null;
  return (
    <div className="flex gap-2">
      <dt className="w-32 shrink-0 text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm text-foreground">{value}</dd>
    </div>
  );
}

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80 ? "bg-success" : pct >= 50 ? "bg-warning" : "bg-destructive";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 rounded-full bg-muted">
        <div
          className={`h-1.5 rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground">{pct}%</span>
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
      className="rounded-xl border border-border bg-card p-5"
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Validation
        </h2>
        <Badge variant={result.is_valid ? "green" : "yellow"}>
          {result.is_valid ? "Valid" : "Needs attention"}
        </Badge>
      </div>
      <div className="mb-3 flex items-center gap-2 text-sm text-muted-foreground">
        <span>Score</span>
        <ConfidenceBar score={result.score} />
      </div>
      {errors.length > 0 && (
        <div className="mb-2">
          <p className="text-xs font-semibold text-destructive">Errors</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-foreground">
            {errors.map((e, i) => (
              <li key={i}>{errorText(e)}</li>
            ))}
          </ul>
        </div>
      )}
      {warnings.length > 0 && (
        <div className="mb-2">
          <p className="text-xs font-semibold text-warning">Warnings</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-foreground">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
      {suggestions.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-primary-ink">Suggestions</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-foreground">
            {suggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
      {errors.length === 0 &&
        warnings.length === 0 &&
        suggestions.length === 0 && (
          <p className="text-sm text-muted-foreground">No issues reported.</p>
        )}
    </section>
  );
}

export function OkhDetailView({ id }: Props) {
  const router = useRouter();
  const [validateState, setValidateState] = useState<
    "idle" | "running" | "done" | "error"
  >("idle");
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [validateError, setValidateError] = useState<string | null>(null);

  const {
    data: okh,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<OkhManifest>({
    queryKey: ["okh-detail", id],
    queryFn: () => fetchOkhDetail(id),
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
        description={
          error instanceof Error ? error.message : "Design not found."
        }
        onRetry={() => refetch()}
      />
    );
  }

  const title = okh.title || "Untitled Design";
  const allFiles = [
    ...okh.design_files,
    ...okh.manufacturing_files,
    ...okh.making_instructions,
  ];

  return (
    <div className="space-y-8">
      <nav className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/okh" className="hover:text-primary-ink">
          Designs
        </Link>
        <span aria-hidden="true">›</span>
        <span className="truncate text-foreground">{title}</span>
      </nav>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-foreground">{title}</h1>
          {okh.function && (
            <p className="text-base text-muted-foreground">{okh.function}</p>
          )}
          {okh.description && okh.description !== okh.function && (
            <p className="text-sm text-muted-foreground">{okh.description}</p>
          )}
          <div className="flex flex-wrap gap-1.5 pt-1">
            {okh.version && <Badge variant="default">v{okh.version}</Badge>}
            {okh.documentation_language && (
              <Badge variant="blue">
                {okh.documentation_language.toUpperCase()}
              </Badge>
            )}
            {okh.manufacturing_processes.map((p) => (
              <Badge key={p} variant="indigo">
                {p}
              </Badge>
            ))}
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <BuildPackageButton okh={okh} />
          <Button onClick={() => router.push(`/match?okh_id=${okh.id}`)}>
            ⚡ Run Match
          </Button>
          <Button
            variant="outline"
            onClick={handleValidate}
            disabled={validateState === "running"}
          >
            {validateState === "running" ? "Validating…" : "Validate"}
          </Button>
        </div>
      </div>

      {validateState === "error" && (
        <ErrorState
          description={validateError ?? "Validation failed."}
          onRetry={handleValidate}
        />
      )}
      {validateState === "done" && result && (
        <ValidationPanel result={result} />
      )}

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-1">
          <section className="rounded-xl border border-border bg-card p-5">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Design Info
            </h2>
            <dl className="space-y-2">
              <MetaRow
                label="ID"
                value={<span className="font-mono text-xs">{okh.id}</span>}
              />
              {okh.repo && (
                <MetaRow
                  label="Repository"
                  value={
                    <a
                      href={okh.repo}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block max-w-[180px] truncate text-primary-ink hover:underline"
                    >
                      {okh.repo.replace(/^https?:\/\//, "")}
                    </a>
                  }
                />
              )}
              <MetaRow label="Licensor" value={okh.licensor?.name ?? null} />
              {okh.licensor?.affiliation && (
                <MetaRow label="Org" value={okh.licensor.affiliation} />
              )}
            </dl>
          </section>

          <AuthorshipPanel kind="okh" id={id} />
          <VisibilityControl kind="okh" id={id} />
          <ReleasesStrip okhId={id} />
          <AttestationsPanel />

          {(okh.license?.hardware ||
            okh.license?.documentation ||
            okh.license?.software) && (
            <section className="rounded-xl border border-border bg-card p-5">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                License
              </h2>
              <dl className="space-y-2">
                <MetaRow label="Hardware" value={okh.license.hardware} />
                <MetaRow
                  label="Documentation"
                  value={okh.license.documentation}
                />
                <MetaRow label="Software" value={okh.license.software} />
              </dl>
            </section>
          )}

          {okh.materials.length > 0 && (
            <section className="rounded-xl border border-border bg-card p-5">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Materials
              </h2>
              <ul className="space-y-2">
                {okh.materials.map((m, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between gap-2"
                  >
                    <span className="text-sm text-foreground">{m.name}</span>
                    {m.quantity != null && (
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {m.quantity} {m.unit}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {okh.keywords.length > 0 && (
            <section className="rounded-xl border border-border bg-card p-5">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Keywords
              </h2>
              <div className="flex flex-wrap gap-1.5">
                {okh.keywords.map((k) => (
                  <Badge key={k} variant="default">
                    {k}
                  </Badge>
                ))}
              </div>
            </section>
          )}
        </div>

        <div className="space-y-6 lg:col-span-2">
          {okh.intended_use && (
            <section className="rounded-xl border border-border bg-card p-5">
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Intended Use
              </h2>
              <p className="text-sm text-muted-foreground">
                {okh.intended_use}
              </p>
            </section>
          )}

          {allFiles.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              No file references attached to this design.
            </div>
          ) : (
            <section className="rounded-xl border border-border bg-card p-5">
              <h2 className="mb-5 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Files &amp; Documentation
              </h2>
              <div className="space-y-6">
                <OkhFileGroup
                  okhId={okh.id}
                  title="Design Files"
                  icon="📐"
                  files={okh.design_files}
                />
                <OkhFileGroup
                  okhId={okh.id}
                  title="Manufacturing Files"
                  icon="🏭"
                  files={okh.manufacturing_files}
                />
                <OkhFileGroup
                  okhId={okh.id}
                  title="Making Instructions"
                  icon="📋"
                  files={okh.making_instructions}
                />
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
