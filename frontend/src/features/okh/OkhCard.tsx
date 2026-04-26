import { Link, useNavigate } from "react-router-dom";
import { Badge } from "../../components/ui/Badge";
import type { OkhManifest } from "../../types/okh";

interface Props {
  okh: OkhManifest;
}

const PROCESS_COLORS: Record<string, "indigo" | "blue" | "green" | "yellow"> = {
  "3DP": "indigo",
  PCB: "blue",
  CNC: "green",
  Assembly: "yellow",
  Laser: "blue",
  Welding: "yellow",
};

function processColor(p: string): "indigo" | "blue" | "green" | "yellow" | "default" {
  return PROCESS_COLORS[p] ?? "default";
}

export function OkhCard({ okh }: Props) {
  const navigate = useNavigate();
  const title = okh.title || "Untitled Design";
  const subtitle = okh.function || okh.description || null;

  return (
    <div className="group flex flex-col rounded-xl border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md dark:border-slate-700 dark:bg-slate-900">
      {/* Clickable main body */}
      <Link
        to={`/okh/${okh.id}`}
        className="flex flex-1 flex-col gap-3 p-5 no-underline"
      >
        <div>
          <h3 className="font-semibold text-slate-800 group-hover:text-indigo-600 transition-colors dark:text-slate-100 dark:group-hover:text-indigo-400">
            {title}
          </h3>
          {subtitle && (
            <p className="mt-1 line-clamp-2 text-sm text-slate-500 dark:text-slate-400">
              {subtitle}
            </p>
          )}
        </div>

        {/* Manufacturing processes */}
        {okh.manufacturing_processes.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {okh.manufacturing_processes.slice(0, 4).map((p) => (
              <Badge key={p} variant={processColor(p)}>
                {p}
              </Badge>
            ))}
            {okh.manufacturing_processes.length > 4 && (
              <Badge variant="default">+{okh.manufacturing_processes.length - 4}</Badge>
            )}
          </div>
        )}

        {/* Meta row */}
        <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400 dark:text-slate-500">
          {okh.version && <span>v{okh.version}</span>}
          {okh.documentation_language && (
            <span className="uppercase">{okh.documentation_language}</span>
          )}
          {okh.license?.hardware && (
            <span className="truncate max-w-[120px]">{okh.license.hardware}</span>
          )}
          {okh.materials.length > 0 && (
            <span>{okh.materials.length} material{okh.materials.length !== 1 ? "s" : ""}</span>
          )}
        </div>
      </Link>

      {/* Action footer */}
      <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 dark:border-slate-800">
        <span className="text-xs text-slate-400 dark:text-slate-500 font-mono truncate max-w-[140px]">
          {okh.id.slice(0, 8)}…
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); navigate(`/match?okh_id=${okh.id}&autorun=1`); }}
          className="rounded-md bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors dark:bg-indigo-950 dark:text-indigo-300 dark:hover:bg-indigo-900"
        >
          Run Match ⚡
        </button>
      </div>
    </div>
  );
}
