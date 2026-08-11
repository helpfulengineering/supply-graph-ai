"use client";

import { PackagesIllustration } from "../../components/ui/illustrations";
import { FIELD, FIELD_SM } from "../../components/ui/field";
import { PageHero } from "../../components/layout/PageHero";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  downloadPackagesZip,
  fetchPackageList,
  packageDetailPath,
  splitPackageName,
  type PackageZipItem,
} from "../../api/package";
import type { PackageListItem } from "../../types/package";
import { PackageCard } from "./PackageCard";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { EmptyState } from "../../components/ui/EmptyState";
import { Button } from "../../components/ui/button";
import { useAuth } from "../../context/AuthContext";

function matchesFilter(pkg: PackageListItem, q: string): boolean {
  if (!q) return true;
  const hay =
    `${pkg.package_name} ${pkg.version} ${pkg.okh_manifest_id ?? ""}`.toLowerCase();
  return hay.includes(q.toLowerCase());
}

function groupKey(pkg: PackageListItem): string {
  return pkg.package_name;
}

export function PackageListView() {
  const router = useRouter();
  const { reportAuthFailure } = useAuth();
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [zipping, setZipping] = useState(false);

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["package-list"],
    queryFn: () => fetchPackageList(1, 100),
  });

  const packages = data?.items ?? [];
  const filtered = useMemo(
    () => packages.filter((p) => matchesFilter(p, filter.trim())),
    [packages, filter],
  );

  const groups = useMemo(() => {
    const map = new Map<string, PackageListItem[]>();
    for (const pkg of filtered) {
      const key = groupKey(pkg);
      const list = map.get(key) ?? [];
      list.push(pkg);
      map.set(key, list);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [filtered]);

  function selectionKey(pkg: PackageListItem): string {
    return `${pkg.package_name}@${pkg.version}`;
  }

  function toggle(pkg: PackageListItem) {
    const key = selectionKey(pkg);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function downloadSelected() {
    const items: PackageZipItem[] = [];
    for (const key of selected) {
      const [name, version] = key.split("@");
      const { org, project } = splitPackageName(name);
      items.push({ org, project, version });
    }
    if (!items.length) return;
    setZipping(true);
    try {
      await downloadPackagesZip(items);
    } catch (e) {
      reportAuthFailure(e);
    } finally {
      setZipping(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHero
        title="Packages"
        crumb="archives · versions · downloads"
        actions={
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className={`${FIELD_SM} shrink-0 font-medium text-muted-foreground hover:bg-background`}
          >
            {isFetching ? "Refreshing…" : "↻ Refresh"}
          </button>
        }
      />

      <div className="rounded-xl border border-border bg-background px-5 py-4">
        <p className="text-sm font-medium text-foreground">
          Building a package
        </p>
        <p className="mt-1 text-sm text-foreground">
          Open a design and use{" "}
          <button
            type="button"
            onClick={() => router.push("/okh")}
            className="font-semibold text-primary-ink underline hover:no-underline"
          >
            Build on server
          </button>{" "}
          in the detail view. Packages then appear here.
        </p>
      </div>

      {!isLoading && !isError && packages.length > 0 && (
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="search"
            aria-label="Search packages"
            placeholder="Search name, version, or manifest id…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className={`${FIELD} w-full max-w-md`}
          />
          <Button
            disabled={selected.size === 0 || zipping}
            onClick={() => void downloadSelected()}
          >
            {zipping
              ? "Preparing zip…"
              : `Download selected (${selected.size})`}
          </Button>
        </div>
      )}

      {isLoading && (
        <div className="rounded-xl border border-border bg-background p-8">
          <LoadingSpinner message="Loading packages…" />
        </div>
      )}

      {isError && <ErrorMessage error={error} />}

      {!isLoading && !isError && (
        <>
          {filtered.length === 0 ? (
            <EmptyState
              icon={() => <PackagesIllustration className="h-10 w-10" />}
              heading={
                packages.length === 0 ? "No packages built yet" : "No matches"
              }
              body={
                packages.length === 0
                  ? "Build a package from an OKH design to make it available here."
                  : "Try a different search."
              }
              action={
                packages.length === 0 ? (
                  <button
                    type="button"
                    onClick={() => router.push("/okh")}
                    className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-on-accent"
                  >
                    Browse Designs
                  </button>
                ) : undefined
              }
            />
          ) : (
            <div className="space-y-6">
              <p className="text-sm text-muted-foreground">
                {filtered.length} package{filtered.length !== 1 ? "s" : ""}
                {filter.trim() ? " (filtered)" : ""}
              </p>
              {groups.map(([name, versions]) => (
                <section key={name} className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-sm font-semibold text-foreground">
                      {name}
                    </h2>
                    <div className="flex flex-wrap gap-1">
                      {versions.map((pkg) => (
                        <button
                          key={selectionKey(pkg)}
                          type="button"
                          className="rounded-full border border-border px-2 py-0.5 font-mono text-xs text-foreground hover:bg-background"
                          onClick={() =>
                            router.push(
                              packageDetailPath(pkg.package_name, pkg.version),
                            )
                          }
                        >
                          v{pkg.version}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-3">
                    {versions.map((pkg) => (
                      <PackageCard
                        key={selectionKey(pkg)}
                        pkg={pkg}
                        selected={selected.has(selectionKey(pkg))}
                        onToggle={() => toggle(pkg)}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
