import { Link, useNavigate } from "react-router-dom";
import type { OkhManifest } from "../../types/okh";
import { deriveCategories, UNCATEGORIZED } from "./categories";
import { formatOkhDisplayTitle } from "./formatOkhDisplayTitle";
import { normalizeHardwareLicense } from "./normalizeHardwareLicense";

interface Props {
  okh: OkhManifest;
}

export function OkhListRow({ okh }: Props) {
  const navigate = useNavigate();
  const title = formatOkhDisplayTitle(okh.title);
  const category =
    deriveCategories(okh).find((c) => c !== UNCATEGORIZED) ?? UNCATEGORIZED;
  const author = okh.licensor?.name?.trim() || "—";
  const license = normalizeHardwareLicense(okh.license?.hardware) ?? "—";
  const processes = (okh.manufacturing_processes ?? []).slice(0, 3).join(", ");

  return (
    <div className="flex flex-col gap-2 border-b border-slate-100 py-3 last:border-0 dark:border-slate-800 sm:flex-row sm:items-center sm:gap-4">
      <Link
        to={`/okh/${okh.id}`}
        className="min-w-0 flex-1 no-underline hover:text-indigo-600 dark:hover:text-indigo-400"
      >
        <div className="font-medium text-slate-800 dark:text-slate-100 break-words">
          {title}
        </div>
        <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-500">
          <span>{category}</span>
          {processes && <span>{processes}</span>}
          <span>{author}</span>
          {okh.version && <span>v{okh.version}</span>}
          <span>{license}</span>
        </div>
      </Link>
      <button
        onClick={() => navigate(`/match?okh_id=${okh.id}`)}
        className="shrink-0 self-start rounded-md bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors dark:bg-indigo-950 dark:text-indigo-300 dark:hover:bg-indigo-900 sm:self-center"
      >
        Run Match ⚡
      </button>
    </div>
  );
}
