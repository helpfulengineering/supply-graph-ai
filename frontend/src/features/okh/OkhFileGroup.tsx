import type { OkhFileRef } from "../../types/okh";

interface Props {
  title: string;
  icon: string;
  files: OkhFileRef[];
}

function fileExtension(path: string): string {
  const parts = path.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toUpperCase() : "FILE";
}

export function OkhFileGroup({ title, icon, files }: Props) {
  if (files.length === 0) return null;

  return (
    <div>
      <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-slate-700 dark:text-slate-300">
        <span aria-hidden="true">{icon}</span>
        {title}
        <span className="ml-1 rounded-full bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">
          {files.length}
        </span>
      </h3>
      <ul className="space-y-1.5">
        {files.map((f, i) => (
          <li
            key={i}
            className="flex items-center justify-between gap-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 dark:border-slate-800 dark:bg-slate-800/50"
          >
            <div className="min-w-0">
              <p className="truncate text-sm text-slate-700 dark:text-slate-200">{f.title || f.path.split("/").pop()}</p>
              {f.metadata && Object.keys(f.metadata).length > 0 && (
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  {Object.entries(f.metadata).map(([k, v]) => `${k}: ${v}`).join(" · ")}
                </p>
              )}
            </div>
            <a
              href={f.path}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 rounded bg-white px-2 py-0.5 text-xs font-medium text-slate-500 shadow-sm ring-1 ring-slate-200 hover:text-indigo-600 hover:ring-indigo-300 transition-colors dark:bg-slate-700 dark:text-slate-300 dark:ring-slate-600 dark:hover:text-indigo-400"
            >
              {fileExtension(f.path)}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
