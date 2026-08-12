"use client";

import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  downloadPackageFile,
  fetchPackageMetadata,
  pinPackage,
  type PinRecord,
  splitPackageName,
  verifyPackagePin,
} from "../../api/package";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { Button } from "../../components/ui/button";
import { useAuth } from "../../context/AuthContext";
import { AttestationsPanel } from "../identity/AttestationsPanel";
import { CertifyPackagePanel } from "./CertifyPackagePanel";
import { PANEL } from "../../components/ui/surface";
import { cn } from "@/lib/utils";
import { PAGE_TITLE } from "../../components/ui/typography";

interface Props {
  org: string;
  project: string;
  version: string;
}

export function PackageDetailView({ org, project, version }: Props) {
  const { reportAuthFailure } = useAuth();
  const queryClient = useQueryClient();
  const packageName = `${org}/${project}`;
  const [pinResult, setPinResult] = useState<{
    pin_record: PinRecord;
    bundle_hash: string;
  } | null>(null);

  const meta = useQuery({
    queryKey: ["package", org, project, version],
    queryFn: () => fetchPackageMetadata(org, project, version),
  });

  const pin = useMutation({
    mutationFn: () => pinPackage(org, project, version),
    onError: reportAuthFailure,
    onSuccess: (result) => {
      setPinResult(result);
      void queryClient.invalidateQueries({
        queryKey: ["package", org, project, version],
      });
    },
  });

  const verify = useMutation({
    mutationFn: () => verifyPackagePin(org, project, version),
    onError: reportAuthFailure,
  });

  if (meta.isLoading) {
    return (
      <div className="space-y-6">
        <h1 className={cn(PAGE_TITLE, "break-all")}>{packageName}</h1>
        <LoadingSpinner message="Loading package…" />
      </div>
    );
  }
  if (meta.isError || !meta.data) {
    return (
      <div className="space-y-6">
        <h1 className={cn(PAGE_TITLE, "break-all")}>{packageName}</h1>
        <ErrorMessage error={meta.error ?? new Error("Package not found")} />
      </div>
    );
  }
  const pkg = meta.data;

  return (
    <div className="space-y-6">
      <Breadcrumb
        trail={[
          { label: "Packages", href: "/packages" },
          { label: `${packageName}@${version}` },
        ]}
      />

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className={cn(PAGE_TITLE, "break-all")}>{packageName}</h1>
          <p className="mt-1 font-mono text-sm text-muted-foreground">
            v{pkg.version}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={() =>
              void downloadPackageFile(packageName, version).catch(
                reportAuthFailure,
              )
            }
          >
            ↓ Download .tar.gz
          </Button>
          <Button
            variant="outline"
            disabled={pin.isPending}
            onClick={() => pin.mutate()}
          >
            {pin.isPending ? "Pinning…" : "Pin"}
          </Button>
          <Button
            variant="outline"
            disabled={verify.isPending}
            onClick={() => verify.mutate()}
          >
            {verify.isPending ? "Verifying…" : "Verify pin"}
          </Button>
        </div>
      </div>

      <dl className={cn(PANEL, "grid gap-3 text-sm sm:grid-cols-2")}>
        <div>
          <dt className="text-xs uppercase text-muted-foreground">Files</dt>
          <dd>{pkg.total_files}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase text-muted-foreground">Size</dt>
          <dd>{pkg.total_size_bytes.toLocaleString()} bytes</dd>
        </div>
        <div>
          <dt className="text-xs uppercase text-muted-foreground">Built</dt>
          <dd>{pkg.build_timestamp}</dd>
        </div>
        {pkg.okh_manifest_id && (
          <div>
            <dt className="text-xs uppercase text-muted-foreground">
              OKH manifest
            </dt>
            <dd>
              <Link
                className="font-mono text-primary-ink hover:underline"
                href={`/okh/${pkg.okh_manifest_id}`}
              >
                {pkg.okh_manifest_id}
              </Link>
            </dd>
          </div>
        )}
      </dl>

      {pin.isSuccess && pinResult && (
        <p className="text-sm text-success" role="status">
          Package pinned. Bundle {pinResult.bundle_hash}
        </p>
      )}
      {verify.isSuccess && (
        <p
          className={`text-sm ${verify.data.verified ? "text-success" : "text-warning"}`}
          role="status"
        >
          {verify.data.verified
            ? "Pin verified — contents unchanged."
            : `Pin drift: ${(verify.data.changed_files ?? []).join(", ") || "files changed"}`}
        </p>
      )}
      {(pin.isError || verify.isError) && (
        <p className="text-sm text-destructive" role="alert">
          {(pin.error ?? verify.error) instanceof Error
            ? ((pin.error ?? verify.error) as Error).message
            : "Action failed."}
        </p>
      )}

      <CertifyPackagePanel version={version} pin={pinResult} />
      <AttestationsPanel contentHash={pinResult?.bundle_hash} />
    </div>
  );
}

/** Parse route params; returns null if invalid. */
export function parsePackageRoute(
  org?: string,
  project?: string,
  version?: string,
): Props | null {
  if (!org || !project || !version) return null;
  try {
    splitPackageName(
      `${decodeURIComponent(org)}/${decodeURIComponent(project)}`,
    );
  } catch {
    return null;
  }
  return {
    org: decodeURIComponent(org),
    project: decodeURIComponent(project),
    version: decodeURIComponent(version),
  };
}
