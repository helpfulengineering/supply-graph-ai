import type { VisualizationData } from "../../types/supply-tree";

interface Props {
  data: VisualizationData;
  solutionId: string;
}

interface ArtifactDef {
  label: string;
  icon: string;
  href: string | null;
  description: string;
  download?: boolean;
}

export function ArtifactLinks({ data, solutionId }: Props) {
  const base = `/v1/api/supply-tree/solution/${solutionId}`;
  const artifacts = data.artifacts;

  const links: ArtifactDef[] = [
    {
      label: "HTML Report",
      icon: "📄",
      href: artifacts.html_report ? `${base}/report` : null,
      description: "Full interactive supply chain report",
    },
    {
      label: "GraphML Export",
      icon: "🗂️",
      href: artifacts.graphml_endpoint
        ? typeof artifacts.graphml_endpoint === "string"
          ? artifacts.graphml_endpoint
          : `${base}/export?format=graphml`
        : null,
      description: "Graph structure for Gephi or yEd",
      download: true,
    },
    {
      label: "JSON Bundle",
      icon: "📦",
      href: artifacts.json_bundle ? `${base}/export?format=json` : null,
      description: "Raw visualization data bundle",
      download: true,
    },
  ];

  return (
    <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="border-b border-slate-100 px-5 py-3 dark:border-slate-800">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
          Export Artifacts
        </h3>
        <p className="text-xs text-slate-400 dark:text-slate-500">
          Download or open generated artifacts for this solution
        </p>
      </div>
      <div className="divide-y divide-slate-100 dark:divide-slate-800">
        {links.map(({ label, icon, href, description, download }) => (
          <div
            key={label}
            className="flex items-center justify-between gap-4 px-5 py-4"
          >
            <div className="flex items-center gap-3">
              <span className="text-xl" aria-hidden="true">{icon}</span>
              <div>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{label}</p>
                <p className="text-xs text-slate-400 dark:text-slate-500">{description}</p>
              </div>
            </div>
            {href ? (
              <a
                href={href}
                target={download ? undefined : "_blank"}
                rel="noopener noreferrer"
                download={download || undefined}
                className="shrink-0 rounded-md bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors dark:bg-indigo-950 dark:text-indigo-300 dark:hover:bg-indigo-900"
              >
                {download ? "Download" : "Open"}
              </a>
            ) : (
              <span className="shrink-0 rounded-md bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                Unavailable
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
