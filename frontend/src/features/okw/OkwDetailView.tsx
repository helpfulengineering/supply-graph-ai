"use client";

import { MapPin } from "lucide-react";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  deleteOkw,
  fetchOkwDetail,
  getOkwProvenance,
  getOkwVisibility,
  validateOkw,
  type ValidationResult,
} from "../../api/ohm/okw";
import { useAuth } from "../../context/AuthContext";
import { LoadingState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/Badge";
import type { OkwFacility } from "../../types/okw";
import { humanizeProcess } from "./processDisplay";
import { FacilityDesigns } from "./FacilityDesigns";
import { AuthorshipPanel } from "../okh/AuthorshipPanel";
import { SharingPanel } from "./SharingPanel";
import { deleteConfirmMessage } from "./deleteConfirmMessage";
import {
  isSyncedFacilityProvenance,
  SyncedFacilityBanner,
} from "./SyncedFacilityBanner";
import { displayCountryName, displayRegionName } from "../match/geoDisplay";

function locationLabel(f: OkwFacility): string | null {
  const a = f.location?.address;
  const country = a?.country ?? f.location?.country;
  const region = a?.region;
  const parts = [
    a?.city ?? f.location?.city,
    region ? displayRegionName(region) : null,
    country ? displayCountryName(country) : null,
  ].filter(Boolean);
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
      <p className="mb-2 text-sm text-muted-foreground">
        Score: {Math.round(result.score * 100)}%
      </p>
      {[
        [
          "Errors",
          errors.map(
            (e) => (e as { message?: string }).message ?? JSON.stringify(e),
          ),
        ],
        ["Warnings", warnings],
        ["Suggestions", suggestions],
      ].map(([label, items]) =>
        (items as string[]).length > 0 ? (
          <div key={label as string} className="mb-2">
            <p className="text-xs font-semibold text-muted-foreground">
              {label}
            </p>
            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-foreground">
              {(items as string[]).map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
          </div>
        ) : null,
      )}
      {errors.length === 0 &&
        warnings.length === 0 &&
        suggestions.length === 0 && (
          <p className="text-sm text-muted-foreground">No issues reported.</p>
        )}
    </section>
  );
}

function PostCreateBanner({
  onDismiss,
  editHref,
}: {
  onDismiss: () => void;
  editHref: string;
}) {
  return (
    <div
      role="status"
      className="rounded-md border border-primary/30 bg-accent px-4 py-3 text-sm text-primary-ink"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="font-medium">Facility created</p>
          <p className="text-xs opacity-90">
            Add equipment or hours when you are ready, or share with peers from
            Sharing below. Visibility stays private until you change it.
          </p>
          <div className="flex flex-wrap gap-3 pt-1">
            <Link href={editHref} className="font-medium underline">
              Edit facility
            </Link>
            <a href="#sharing" className="font-medium underline">
              Sharing
            </a>
          </div>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={onDismiss}>
          Dismiss
        </Button>
      </div>
    </div>
  );
}

export function OkwDetailView({ id }: { id: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { hasWrite, reportAuthFailure } = useAuth();
  const pathname = usePathname() ?? "";
  const searchParams = useSearchParams();
  const showCreatedBanner = searchParams.get("created") === "1";

  const [validateState, setValidateState] = useState<
    "idle" | "running" | "done" | "error"
  >("idle");
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [validateError, setValidateError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const {
    data: f,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<OkwFacility>({
    queryKey: ["okw-detail", id],
    queryFn: () => fetchOkwDetail(id),
  });
  const provenance = useQuery({
    queryKey: ["okw", "provenance", id],
    queryFn: () => getOkwProvenance(id),
    retry: false,
  });

  const dismissCreatedBanner = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("created");
    const qs = next.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };

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

  const handleDelete = async () => {
    if (!hasWrite || !f) return;
    setDeleteError(null);

    let visibility: string | undefined;
    try {
      visibility = (await getOkwVisibility(id)).visibility;
    } catch {
      // Still allow delete if visibility lookup fails.
    }

    const ok = window.confirm(
      deleteConfirmMessage(f.name || "this facility", visibility),
    );
    if (!ok) return;

    setDeleting(true);
    try {
      await deleteOkw(id);
      await queryClient.invalidateQueries({ queryKey: ["network"] });
      router.push("/facilities");
    } catch (err) {
      reportAuthFailure(err);
      setDeleteError(err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setDeleting(false);
    }
  };

  if (isLoading) return <LoadingState message="Loading facility…" />;
  if (isError || !f) {
    return (
      <ErrorState
        description={
          error instanceof Error ? error.message : "Facility not found."
        }
        onRetry={() => refetch()}
      />
    );
  }

  const location = locationLabel(f);
  const equipment = f.equipment ?? [];
  const certifications = f.certifications ?? [];
  const editHref = `/facilities/${id}/edit`;

  return (
    <div className="space-y-8">
      <nav className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/facilities" className="hover:text-primary-ink">
          Facilities
        </Link>
        <span aria-hidden="true">›</span>
        <span className="truncate text-foreground">{f.name || "Facility"}</span>
      </nav>

      {showCreatedBanner && (
        <PostCreateBanner
          onDismiss={dismissCreatedBanner}
          editHref={editHref}
        />
      )}
      {isSyncedFacilityProvenance(provenance.data) && (
        <SyncedFacilityBanner publishedBy={provenance.data?.published_by} />
      )}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-foreground">
            {f.name || "Unnamed facility"}
          </h1>
          {location && (
            <p className="flex items-center gap-1.5 text-base text-muted-foreground"><MapPin aria-hidden="true" className="h-4 w-4 shrink-0" /> {location}</p>
          )}
          <div className="flex flex-wrap gap-1.5 pt-1">
            {f.access_type && <Badge variant="blue">{f.access_type}</Badge>}
            {f.facility_status && (
              <Badge
                variant={f.facility_status === "Active" ? "green" : "yellow"}
              >
                {f.facility_status}
              </Badge>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={() =>
              router.push(`/match?okw_id=${encodeURIComponent(id)}`)
            }
          >
            Find matching designs →
          </Button>
          <Button variant="outline" onClick={() => router.push(editHref)}>
            Edit
          </Button>
          <Button
            variant="outline"
            onClick={() => void handleValidate()}
            disabled={validateState === "running"}
          >
            {validateState === "running" ? "Validating…" : "Validate"}
          </Button>
          <Button
            variant="destructive"
            onClick={() => void handleDelete()}
            disabled={!hasWrite || deleting}
            title={
              hasWrite ? undefined : "Connect a write-capable API key to delete"
            }
          >
            {deleting ? "Deleting…" : "Delete"}
          </Button>
        </div>
      </div>

      {deleteError && (
        <p className="text-sm text-destructive" role="alert">
          {deleteError}
        </p>
      )}

      {validateState === "error" && (
        <ErrorState
          description={validateError ?? "Validation failed."}
          onRetry={handleValidate}
        />
      )}
      {validateState === "done" && result && (
        <ValidationPanel result={result} />
      )}

      <div className="max-w-xl">
        <AuthorshipPanel kind="okw" id={id} />
      </div>
      <SharingPanel id={id} />

      {f.description && (
        <section className="rounded-xl border border-border bg-card p-5">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            About
          </h2>
          <p className="text-sm text-muted-foreground">{f.description}</p>
        </section>
      )}

      {equipment.length > 0 && (
        <section className="rounded-xl border border-border bg-card p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Equipment ({equipment.length})
          </h2>
          <ul className="space-y-2">
            {equipment.map((e, i) => (
              <li key={i} className="flex items-center justify-between gap-2">
                <span className="text-sm text-foreground">
                  {[e.make, e.model].filter(Boolean).join(" ") || "Equipment"}
                </span>
                {e.equipment_type && (
                  <Badge variant="indigo">
                    {humanizeProcess(e.equipment_type)}
                  </Badge>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {certifications.length > 0 && (
        <section className="rounded-xl border border-border bg-card p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Certifications
          </h2>
          <div className="flex flex-wrap gap-1.5">
            {certifications.map((c) => (
              <Badge key={c} variant="default">
                {c}
              </Badge>
            ))}
          </div>
        </section>
      )}

      <FacilityDesigns okwId={id} />
    </div>
  );
}
