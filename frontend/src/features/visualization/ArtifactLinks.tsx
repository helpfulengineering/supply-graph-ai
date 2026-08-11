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
    <div className="rounded-xl border border-border bg-card">
      <div className="border-b border-border px-5 py-3">
        <h3 className="text-sm font-semibold text-foreground">
          Export Artifacts
        </h3>
        <p className="text-xs text-muted-foreground">
          Download or open generated artifacts for this solution
        </p>
      </div>
      <div className="divide-y divide-border">
        {links.map(({ label, icon, href, description, download }) => (
          <div
            key={label}
            className="flex items-center justify-between gap-4 px-5 py-4"
          >
            <div className="flex items-center gap-3">
              <span className="text-xl" aria-hidden="true">
                {icon}
              </span>
              <div>
                <p className="text-sm font-medium text-foreground">{label}</p>
                <p className="text-xs text-muted-foreground">{description}</p>
              </div>
            </div>
            {href ? (
              <a
                href={href}
                target={download ? undefined : "_blank"}
                rel="noopener noreferrer"
                download={download || undefined}
                className="shrink-0 rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-primary-ink hover:bg-accent transition-colors"
              >
                {download ? "Download" : "Open"}
              </a>
            ) : (
              <span className="shrink-0 rounded-md bg-muted px-3 py-1.5 text-xs font-medium text-muted-foreground">
                Unavailable
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
