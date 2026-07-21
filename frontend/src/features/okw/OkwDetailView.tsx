import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { fetchOkwDetail, validateOkw, type ValidationResult } from "../../api/ohm/okw";
import { LoadingState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/Badge";
import type { OkwFacility } from "../../types/okw";
import { humanizeProcess } from "./processDisplay";
import { FacilityDesigns } from "./FacilityDesigns";
import { AuthorshipPanel } from "../okh/AuthorshipPanel";
import { VisibilityControl } from "../okh/VisibilityControl";

function locationLabel(f: OkwFacility): string | null {
  const a = f.location?.address;
  const parts = [a?.city ?? f.location?.city, a?.region, a?.country ?? f.location?.country].filter(
    Boolean,
  );
  return parts.length ? parts.join(", ") : null;
}

function ValidationPanel({ result }: { result: ValidationResult }) {
  const warnings = result.warnings ?? [];
  const suggestions = result.suggestions ?? [];
  const errors = result.errors ?? [];
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
      <p className="mb-2 text-sm text-slate-600 dark:text-slate-300">
        Score: {Math.round(result.score * 100)}%
      </p>
      {[
        ["Errors", errors.map((e) => (e as { message?: string }).message ?? JSON.stringify(e))],
        ["Warnings", warnings],
        ["Suggestions", suggestions],
      ].map(([label, items]) =>
        (items as string[]).length > 0 ? (
          <div key={label as string} className="mb-2">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">{label}</p>
            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-700 dark:text-slate-200">
              {(items as string[]).map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
          </div>
        ) : null,
      )}
      {errors.length === 0 && warnings.length === 0 && suggestions.length === 0 && (
        <p className="text-sm text-slate-500 dark:text-slate-400">No issues reported.</p>
      )}
    </section>
  );
}

export function OkwDetailView({ id }: { id: string }) {
  const navigate = useNavigate();
  const [validateState, setValidateState] = useState<"idle" | "running" | "done" | "error">("idle");
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [validateError, setValidateError] = useState<string | null>(null);

  const { data: f, isLoading, isError, error, refetch } = useQuery<OkwFacility>({
    queryKey: ["okw-detail", id],
    queryFn: () => fetchOkwDetail(id),
  });

  const handleValidate = async () => {
    if (!f) return;
    setValidateState("running");
    setValidateError(null);
    try {
      setResult(await validateOkw(f as unknown as Record<string, unknown>));
      setValidateState("done");
    } catch (e) {
      setValidateError(e instanceof Error ? e.message : "Validation failed.");
      setValidateState("error");
    }
  };

  if (isLoading) return <LoadingState message="Loading facility…" />;
  if (isError || !f) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Facility not found."}
        onRetry={() => refetch()}
      />
    );
  }

  const location = locationLabel(f);
  const equipment = f.equipment ?? [];
  const certifications = f.certifications ?? [];

  return (
    <div className="space-y-8">
      <nav className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <Link to="/facilities" className="hover:text-indigo-600 dark:hover:text-indigo-400">
          Facilities
        </Link>
        <span aria-hidden="true">›</span>
        <span className="truncate text-slate-700 dark:text-slate-200">{f.name || "Facility"}</span>
      </nav>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
            {f.name || "Unnamed facility"}
          </h1>
          {location && <p className="text-base text-slate-600 dark:text-slate-300">📍 {location}</p>}
          <div className="flex flex-wrap gap-1.5 pt-1">
            {f.access_type && <Badge variant="blue">{f.access_type}</Badge>}
            {f.facility_status && (
              <Badge variant={f.facility_status === "Active" ? "green" : "yellow"}>
                {f.facility_status}
              </Badge>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => navigate(`/match?okw_id=${encodeURIComponent(id)}`)}>
            Find matching designs →
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

      <div className="grid gap-6 lg:grid-cols-2">
        <AuthorshipPanel kind="okw" id={id} />
        <VisibilityControl kind="okw" id={id} />
      </div>

      {f.description && (
        <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            About
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-300">{f.description}</p>
        </section>
      )}

      {equipment.length > 0 && (
        <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Equipment ({equipment.length})
          </h2>
          <ul className="space-y-2">
            {equipment.map((e, i) => (
              <li key={i} className="flex items-center justify-between gap-2">
                <span className="text-sm text-slate-700 dark:text-slate-200">
                  {[e.make, e.model].filter(Boolean).join(" ") || "Equipment"}
                </span>
                {e.equipment_type && (
                  <Badge variant="indigo">{humanizeProcess(e.equipment_type)}</Badge>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {certifications.length > 0 && (
        <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Certifications
          </h2>
          <div className="flex flex-wrap gap-1.5">
            {certifications.map((c) => (
              <Badge key={c} variant="default">{c}</Badge>
            ))}
          </div>
        </section>
      )}

      <FacilityDesigns okwId={id} />
    </div>
  );
}
