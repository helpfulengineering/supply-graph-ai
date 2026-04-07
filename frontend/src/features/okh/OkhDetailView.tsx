import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { fetchOkhDetail } from "../../api/okh";
import { buildPackageFromManifest, packageDownloadUrl } from "../../api/package";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { Badge } from "../../components/ui/Badge";
import { OkhFileGroup } from "./OkhFileGroup";
import type { OkhManifest } from "../../types/okh";
import type { PackageBuildMetadata } from "../../types/package";

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

export function OkhDetailView({ id }: Props) {
  const navigate = useNavigate();
  const [buildState, setBuildState] = useState<
    "idle" | "building" | "done" | "error"
  >("idle");
  const [builtPackage, setBuiltPackage] = useState<PackageBuildMetadata | null>(null);

  const handleBuildPackage = async () => {
    setBuildState("building");
    try {
      const result = await buildPackageFromManifest(id);
      setBuiltPackage(result.data.metadata);
      setBuildState("done");
    } catch {
      setBuildState("error");
    }
  };

  const { data: okh, isLoading, isError, error, refetch } = useQuery<OkhManifest>({
    queryKey: ["okh-detail", id],
    queryFn: () => fetchOkhDetail(id),
    staleTime: 120_000,
  });

  if (isLoading) return <LoadingSpinner message="Loading design…" />;
  if (isError || !okh) return <ErrorMessage error={error ?? new Error("Not found")} retry={() => refetch()} />;

  const title = okh.title || "Untitled Design";
  const licensorName = okh.licensor?.name ?? null;
  const allFiles = [
    ...okh.design_files,
    ...okh.manufacturing_files,
    ...okh.making_instructions,
  ];

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <Link to="/okh" className="hover:text-indigo-600 dark:hover:text-indigo-400">
          Designs
        </Link>
        <span aria-hidden="true">›</span>
        <span className="truncate text-slate-700 dark:text-slate-200">{title}</span>
      </nav>

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">{title}</h1>
          {okh.function && (
            <p className="text-base text-slate-600 dark:text-slate-300">{okh.function}</p>
          )}
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

        <div className="flex shrink-0 flex-col gap-2 sm:items-end">
          <div className="flex gap-2">
            <button
              onClick={() => navigate(`/match?okh_id=${okh.id}&autorun=1`)}
              className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 transition-colors dark:bg-indigo-500 dark:hover:bg-indigo-400"
            >
              ⚡ Run Match
            </button>
            <button
              onClick={handleBuildPackage}
              disabled={buildState === "building"}
              className="rounded-lg border border-emerald-300 bg-emerald-50 px-5 py-2.5 text-sm font-semibold text-emerald-800 hover:bg-emerald-100 disabled:opacity-60 transition-colors dark:border-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300 dark:hover:bg-emerald-900/40"
            >
              {buildState === "building"
                ? "Building…"
                : buildState === "done"
                ? "✓ Package built"
                : buildState === "error"
                ? "⚠ Build failed"
                : "📦 Build Package"}
            </button>
          </div>

          {/* Package download link after build */}
          {buildState === "done" && builtPackage && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs dark:border-emerald-800 dark:bg-emerald-950/30">
              <span className="font-mono text-emerald-700 dark:text-emerald-400">
                {builtPackage.package_name} @ {builtPackage.version}
              </span>
              {builtPackage.total_files !== undefined && (
                <span className="ml-2 text-emerald-600 dark:text-emerald-500">
                  · {builtPackage.total_files} file{builtPackage.total_files !== 1 ? "s" : ""}
                </span>
              )}
              <a
                href={packageDownloadUrl(builtPackage.package_name, builtPackage.version)}
                download
                className="ml-3 font-semibold text-emerald-700 underline hover:no-underline dark:text-emerald-400"
              >
                ↓ Download
              </a>
              <button
                onClick={() => navigate("/packages")}
                className="ml-3 text-emerald-600 underline hover:no-underline dark:text-emerald-500"
              >
                View all packages →
              </button>
            </div>
          )}

          {buildState === "error" && (
            <p className="text-xs text-red-600 dark:text-red-400">
              Package build failed. Check that the API server is reachable and try again.
            </p>
          )}
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Left column: metadata */}
        <div className="space-y-6 lg:col-span-1">
          {/* Core metadata */}
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
                      className="truncate text-indigo-600 hover:underline dark:text-indigo-400 max-w-[180px] block">
                      {okh.repo.replace(/^https?:\/\//, "")}
                    </a>
                  }
                />
              )}
              {okh.project_link && (
                <MetaRow
                  label="Project"
                  value={
                    <a href={okh.project_link} target="_blank" rel="noopener noreferrer"
                      className="truncate text-indigo-600 hover:underline dark:text-indigo-400 max-w-[180px] block">
                      {okh.project_link.replace(/^https?:\/\//, "")}
                    </a>
                  }
                />
              )}
              <MetaRow label="Licensor" value={licensorName} />
              {okh.licensor?.affiliation && (
                <MetaRow label="Org" value={okh.licensor.affiliation} />
              )}
            </dl>
          </section>

          {/* License */}
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

          {/* Materials */}
          {okh.materials.length > 0 && (
            <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Materials
              </h2>
              <ul className="space-y-2">
                {okh.materials.map((m, i) => (
                  <li key={i} className="flex items-center justify-between gap-2">
                    <div>
                      <p className="text-sm text-slate-700 dark:text-slate-200">{m.name}</p>
                      <p className="text-xs text-slate-400 dark:text-slate-500">{m.material_id}</p>
                    </div>
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

          {/* Parts summary */}
          {okh.parts.length > 0 && (
            <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Parts ({okh.parts.length})
              </h2>
              <ul className="space-y-2">
                {okh.parts.map((part) => (
                  <li key={part.id} className="flex items-center justify-between gap-2">
                    <span className="text-sm text-slate-700 dark:text-slate-200">{part.name}</span>
                    <div className="flex items-center gap-1">
                      {part.tsdc.map((t) => (
                        <Badge key={t} variant="indigo">{t}</Badge>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Keywords */}
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

        {/* Right column: files */}
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

          {/* Tool list */}
          {okh.tool_list.length > 0 && (
            <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Tools Required
              </h2>
              <div className="flex flex-wrap gap-2">
                {okh.tool_list.map((t) => (
                  <span
                    key={t}
                    className="rounded-md bg-slate-50 px-2.5 py-1 text-sm text-slate-600 ring-1 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Contributors */}
          {okh.contributors.length > 0 && (
            <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Contributors
              </h2>
              <ul className="space-y-2">
                {okh.contributors.map((c, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-200 text-xs font-bold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                      {c.name.charAt(0)}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{c.name}</p>
                      {c.affiliation && (
                        <p className="text-xs text-slate-400 dark:text-slate-500">{c.affiliation}</p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Intended use */}
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

// Keep ConfidenceBar available for future use in other components
export { ConfidenceBar };
