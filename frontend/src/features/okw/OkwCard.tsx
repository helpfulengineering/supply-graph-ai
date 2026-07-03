import { Badge } from "../../components/ui/Badge";
import type { OkwFacility } from "../../types/okw";
import { humanizeProcess } from "./processDisplay";

function locationLabel(f: OkwFacility): string | null {
  const a = f.location?.address;
  const parts = [a?.city ?? f.location?.city, a?.region, a?.country ?? f.location?.country].filter(
    Boolean,
  );
  return parts.length ? parts.join(", ") : null;
}

export function OkwCard({ facility }: { facility: OkwFacility }) {
  const location = locationLabel(facility);
  const processes = (facility.manufacturing_processes ?? []).map(humanizeProcess);

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div>
        <h3 className="font-semibold text-slate-800 dark:text-slate-100">
          {facility.name || "Unnamed facility"}
        </h3>
        {location && (
          <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">📍 {location}</p>
        )}
      </div>

      {processes.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {processes.slice(0, 4).map((p) => (
            <Badge key={p} variant="indigo">{p}</Badge>
          ))}
          {processes.length > 4 && <Badge variant="default">+{processes.length - 4}</Badge>}
        </div>
      )}

      <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-1">
        {facility.access_type && <Badge variant="blue">{facility.access_type}</Badge>}
        {facility.facility_status && (
          <Badge variant={facility.facility_status === "Active" ? "green" : "yellow"}>
            {facility.facility_status}
          </Badge>
        )}
      </div>
    </div>
  );
}
