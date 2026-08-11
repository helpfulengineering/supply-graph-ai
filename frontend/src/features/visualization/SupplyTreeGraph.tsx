import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import { useChartTokens } from "../../lib/chartTokens";
import type { VisualizationData } from "../../types/supply-tree";

interface Props {
  data: VisualizationData;
}

// Depth reads the world's own chart ramp, so the graph re-themes with
// everything else instead of carrying a private palette.
function depthColor(series: readonly string[], depth: number): string {
  return series[depth % series.length];
}

export function SupplyTreeGraph({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // cytoscape paints to canvas and cannot evaluate var().
  const t = useChartTokens();
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

    // animate: false throughout. An animating layout queues frames that write
    // positions back to the core; if the component unmounts mid-run
    // (StrictMode's double mount, or navigating away before cose settles) a
    // queued frame lands on a destroyed core and throws. Settling instantly
    // also makes the graph deterministic for screenshots and a11y scans.
    const layoutOptions: cytoscape.LayoutOptions =
      nodes.length <= 1
        ? { name: "grid", animate: false }
        : nodes.length <= 6
          ? {
              name: "breadthfirst",
              directed: true,
              padding: 40,
              spacingFactor: 1.4,
              animate: false,
            }
          : {
              name: "cose",
              padding: 40,
              nodeRepulsion: () => 8000,
              animate: false,
            };

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": (ele: cytoscape.NodeSingular) =>
              depthColor(t.series, ele.data("depth") as number),
            label: "data(label)",
            "text-valign": "bottom",
            "text-halign": "center",
            "font-size": "11px",
            color: t.textMuted,
            "text-margin-y": 6,
            width: 50,
            height: 50,
            "border-width": 2,
            "border-color": t.border,
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
            "line-color": t.border,
            "target-arrow-color": t.textFaint,
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "font-size": "9px",
            label: "data(type)",
            color: t.textFaint,
          },
        },
        {
          selector: ":selected",
          style: {
            "border-width": 3,
            "border-color": t.ring,
          },
        },
      ],
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    });

    // Run the layout by hand rather than through the constructor, so the
    // handle survives into cleanup. A layout animates by queueing frames that
    // write positions back to the core; if the component unmounts mid-run
    // (StrictMode's double mount, or navigating away before cose settles) a
    // queued frame lands on a destroyed core and throws. Stopping the layout
    // first drains that queue.
    const layout = cyRef.current.layout(layoutOptions);
    layout.one("layoutstop", () => {
      cyRef.current?.fit(undefined, 40);
    });
    layout.run();

    return () => {
      layout.stop();
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [nodes, edges, t]);

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-5 py-3">
        <h3 className="text-sm font-semibold text-foreground">
          Supply Tree Graph
        </h3>
        <div className="flex items-center gap-3">
          {t.series
            .slice(0, Math.max(1, new Set(nodes.map((n) => n.depth)).size))
            .map((color: string, i: number) => (
              <span
                key={i}
                className="flex items-center gap-1 text-xs text-muted-foreground"
              >
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ background: color }}
                  aria-hidden="true"
                />
                Depth {i}
              </span>
            ))}
        </div>
      </div>

      {isSingleNode ? (
        <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
          <div
            className="flex h-16 w-16 items-center justify-center rounded-full text-on-accent text-lg font-bold"
            style={{ background: depthColor(t.series, 0) }}
          >
            {nodes[0]?.facility_name?.charAt(0) ?? "?"}
          </div>
          <p className="font-medium text-foreground">
            {nodes[0]?.facility_name ?? "Facility"}
          </p>
          <p className="text-sm text-muted-foreground">
            Single-facility solution — no dependency edges
          </p>
          <p className="text-xs text-muted-foreground">
            Run a match with{" "}
            <code className="rounded bg-muted px-1">
              auto_detect_depth=true
            </code>{" "}
            for a richer graph
          </p>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="h-80 w-full"
          role="img"
          aria-label="Supply tree dependency graph"
        />
      )}
    </div>
  );
}
