import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import type { VisualizationData } from "../../types/supply-tree";

interface Props {
  data: VisualizationData;
}

// Depth → node background color (light/dark handled via cytoscape styles)
const DEPTH_COLORS = ["#6366f1", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444"];

function depthColor(depth: number): string {
  return DEPTH_COLORS[depth % DEPTH_COLORS.length];
}

export function SupplyTreeGraph({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const nodes = data.supply_tree.nodes;
  const edges = data.supply_tree.edges;
  const isSingleNode = nodes.length === 1 && edges.length === 0;

  useEffect(() => {
    if (!containerRef.current) return;

    // Destroy previous instance
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const elements: cytoscape.ElementDefinition[] = [
      ...nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.facility_name || n.label,
          depth: n.depth,
          stage: n.production_stage,
          confidence: Math.round(n.confidence_score * 100),
        },
      })),
      ...edges.map((e) => ({
        data: {
          id: `${e.source}-${e.target}`,
          source: e.source,
          target: e.target,
          type: e.type,
        },
      })),
    ];

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      layout:
        nodes.length <= 1
          ? { name: "grid" }
          : nodes.length <= 6
            ? { name: "breadthfirst", directed: true, padding: 40, spacingFactor: 1.4 }
            : { name: "cose", padding: 40, nodeRepulsion: () => 8000 },
      style: [
        {
          selector: "node",
          style: {
            "background-color": (ele: cytoscape.NodeSingular) =>
              depthColor(ele.data("depth") as number),
            label: "data(label)",
            "text-valign": "bottom",
            "text-halign": "center",
            "font-size": "11px",
            color: "#475569",
            "text-margin-y": 6,
            width: 50,
            height: 50,
            "border-width": 2,
            "border-color": "#e2e8f0",
          },
        },
        {
          selector: "node[confidence]",
          style: {
            label: (ele: cytoscape.NodeSingular) =>
              `${ele.data("label") as string}\n${ele.data("confidence") as number}%`,
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#94a3b8",
            "target-arrow-color": "#94a3b8",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "font-size": "9px",
            label: "data(type)",
            color: "#94a3b8",
          },
        },
        {
          selector: ":selected",
          style: {
            "border-width": 3,
            "border-color": "#6366f1",
          },
        },
      ],
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    });

    // Fit after layout completes
    cyRef.current.one("layoutstop", () => {
      cyRef.current?.fit(undefined, 40);
    });

    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [nodes, edges]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3 dark:border-slate-800">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
          Supply Tree Graph
        </h3>
        <div className="flex items-center gap-3">
          {DEPTH_COLORS.slice(0, Math.max(1, new Set(nodes.map((n) => n.depth)).size)).map(
            (color, i) => (
              <span key={i} className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ background: color }}
                  aria-hidden="true"
                />
                Depth {i}
              </span>
            )
          )}
        </div>
      </div>

      {isSingleNode ? (
        <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
          <div
            className="flex h-16 w-16 items-center justify-center rounded-full text-white text-lg font-bold"
            style={{ background: depthColor(0) }}
          >
            {nodes[0]?.facility_name?.charAt(0) ?? "?"}
          </div>
          <p className="font-medium text-slate-700 dark:text-slate-200">
            {nodes[0]?.facility_name ?? "Facility"}
          </p>
          <p className="text-sm text-slate-400 dark:text-slate-500">
            Single-facility solution — no dependency edges
          </p>
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Run a match with <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">auto_detect_depth=true</code> for a richer graph
          </p>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="h-80 w-full"
          aria-label="Supply tree dependency graph"
        />
      )}
    </div>
  );
}
