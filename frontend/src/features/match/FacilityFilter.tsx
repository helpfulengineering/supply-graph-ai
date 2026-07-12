import { useMemo, useState } from "react";
import {
  cityMatchKey,
  countryMatchKey,
  displayCountryName,
  displayRegionName,
  regionMatchKey,
} from "./geoDisplay";

export type FacilitySource = "local" | "mom";

export interface FacilityOption {
  id: string;
  name: string;
  city?: string | null;
  /** Province / state — OKW/network `region` field. */
  region?: string | null;
  country?: string | null;
  source?: FacilitySource | null;
}

export interface FacilityGeoFilters {
  source: "" | FacilitySource;
  country: string;
  /** Combined State / Region control (single backend field). */
  region: string;
  city: string;
}

const EMPTY_GEO: FacilityGeoFilters = {
  source: "",
  country: "",
  region: "",
  city: "",
};

function uniqueSorted(
  values: (string | null | undefined)[],
  display: (v: string) => string,
): { value: string; label: string }[] {
  const byKey = new Map<string, { value: string; label: string }>();
  for (const raw of values) {
    if (!raw?.trim()) continue;
    const label = display(raw.trim());
    const key = label.toLowerCase();
    if (!byKey.has(key)) byKey.set(key, { value: label, label });
  }
  return [...byKey.values()].sort((a, b) => a.label.localeCompare(b.label));
}

export function facilityPassesGeo(
  f: FacilityOption,
  geo: FacilityGeoFilters,
): boolean {
  if (geo.source && f.source !== geo.source) {
    return false;
  }
  if (geo.country && countryMatchKey(f.country) !== countryMatchKey(geo.country)) {
    return false;
  }
  if (geo.region && regionMatchKey(f.region) !== regionMatchKey(geo.region)) {
    return false;
  }
  if (geo.city && cityMatchKey(f.city) !== cityMatchKey(geo.city)) {
    return false;
  }
  return true;
}

function sourceLabel(source: FacilitySource | null | undefined): string {
  if (source === "mom") return "Maps of Making";
  if (source === "local") return "OHM";
  return "";
}

/**
 * Facility scope for matching. Always expanded. Defaults to the full network
 * universe (local ∪ Maps of Making); Source / geo filters narrow the checklist.
 */
export function FacilityFilter({
  facilities,
  selectedIds,
  onChange,
  isLoading,
  isError,
}: {
  facilities: FacilityOption[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  isLoading?: boolean;
  isError?: boolean;
}) {
  const [geo, setGeo] = useState<FacilityGeoFilters>(EMPTY_GEO);
  const [q, setQ] = useState("");
  const selected = useMemo(() => new Set(selectedIds), [selectedIds]);

  const sourceScoped = useMemo(() => {
    if (!geo.source) return facilities;
    return facilities.filter((f) => f.source === geo.source);
  }, [facilities, geo.source]);

  const countryOptions = useMemo(
    () => uniqueSorted(
      sourceScoped.map((f) => f.country),
      displayCountryName,
    ),
    [sourceScoped],
  );
  const regionOptions = useMemo(
    () => uniqueSorted(
      sourceScoped.map((f) => f.region),
      displayRegionName,
    ),
    [sourceScoped],
  );
  const cityOptions = useMemo(
    () => uniqueSorted(
      sourceScoped.map((f) => f.city),
      (v) => v,
    ),
    [sourceScoped],
  );

  const geoFiltered = useMemo(
    () => facilities.filter((f) => facilityPassesGeo(f, geo)),
    [facilities, geo],
  );

  const nameFiltered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return geoFiltered;
    return geoFiltered.filter((f) => f.name.toLowerCase().includes(needle));
  }, [geoFiltered, q]);

  /** Cap DOM size — MoM alone is thousands of spaces. */
  const LIST_CAP = 150;
  const visible = nameFiltered.slice(0, LIST_CAP);
  const hiddenCount = Math.max(0, nameFiltered.length - visible.length);

  const summary =
    selectedIds.length === 0
      ? "Select facilities to match against"
      : `${selectedIds.length} facilit${selectedIds.length === 1 ? "y" : "ies"} selected`;

  function setGeoField(key: keyof FacilityGeoFilters, value: string) {
    let nextGeo = { ...geo, [key]: value } as FacilityGeoFilters;
    // Source changes invalidate country/city/region that often only exist on the
    // other corpus (e.g. Austin + MoM → empty list).
    if (key === "source") {
      nextGeo = { ...nextGeo, country: "", region: "", city: "" };
    }
    setGeo(nextGeo);
    onChange(
      selectedIds.filter((id) => {
        const f = facilities.find((x) => x.id === id);
        if (!f) return false;
        return facilityPassesGeo(f, nextGeo);
      }),
    );
  }

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange([...next]);
  }

  const selectClass =
    "w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

  return (
    <fieldset className="max-w-2xl rounded-lg border border-input p-4">
      <legend className="px-1 text-sm font-medium text-foreground">
        Facilities
      </legend>
      <p className="mb-3 text-xs text-muted-foreground">{summary}</p>

      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading facilities…</p>
      )}
      {isError && (
        <p className="text-sm text-red-600 dark:text-red-400">
          Couldn’t load facilities. Try again before running a match.
        </p>
      )}

      {!isLoading && !isError && (
        <div className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1 block text-muted-foreground">Source</span>
              <select
                aria-label="Source"
                className={selectClass}
                value={geo.source}
                onChange={(e) =>
                  setGeoField("source", e.target.value as FacilityGeoFilters["source"])
                }
              >
                <option value="">All sources</option>
                <option value="local">OHM facilities</option>
                <option value="mom">Maps of Making</option>
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-muted-foreground">Country</span>
              <select
                aria-label="Country"
                className={selectClass}
                value={geo.country}
                onChange={(e) => setGeoField("country", e.target.value)}
              >
                <option value="">All countries</option>
                {countryOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-muted-foreground">State / Region</span>
              <select
                aria-label="State / Region"
                className={selectClass}
                value={geo.region}
                onChange={(e) => setGeoField("region", e.target.value)}
              >
                <option value="">All states / regions</option>
                {regionOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-muted-foreground">City</span>
              <select
                aria-label="City"
                className={selectClass}
                value={geo.city}
                onChange={(e) => setGeoField("city", e.target.value)}
              >
                <option value="">All cities</option>
                {cityOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Filter facilities by name…"
              aria-label="Filter facilities by name"
              className={selectClass}
            />
          </div>
          <div className="flex gap-3 text-xs">
            <button
              type="button"
              className="text-indigo-600 hover:underline dark:text-indigo-400"
              onClick={() => onChange(visible.map((f) => f.id))}
            >
              Select all visible
            </button>
            <button
              type="button"
              className="text-slate-600 hover:underline dark:text-slate-300"
              onClick={() => onChange([])}
            >
              Clear
            </button>
          </div>
          <ul className="max-h-56 space-y-1 overflow-y-auto rounded-md border border-input p-2">
            {visible.map((f) => (
              <li key={f.id}>
                <label className="flex items-center gap-2 text-sm text-foreground">
                  <input
                    type="checkbox"
                    aria-label={f.name}
                    checked={selected.has(f.id)}
                    onChange={() => toggle(f.id)}
                  />
                  <span className="min-w-0 flex-1 truncate" aria-hidden="true">
                    {f.name}
                  </span>
                  <span className="shrink-0 text-[10px] uppercase tracking-wide text-muted-foreground" aria-hidden="true">
                    {sourceLabel(f.source)}
                  </span>
                  <span className="truncate text-xs text-muted-foreground" aria-hidden="true">
                    {[
                      f.city,
                      f.region ? displayRegionName(f.region) : null,
                      f.country ? displayCountryName(f.country) : null,
                    ]
                      .filter(Boolean)
                      .join(", ")}
                  </span>
                </label>
              </li>
            ))}
            {visible.length === 0 && (
              <li className="text-sm text-muted-foreground">
                No facilities match the current filters.
              </li>
            )}
          </ul>
          <p className="text-xs text-muted-foreground">
            Showing {visible.length}
            {hiddenCount > 0 ? ` of ${nameFiltered.length}` : ""} facilities
            {geo.source === "mom"
              ? " (Maps of Making)"
              : geo.source === "local"
                ? " (OHM)"
                : " (local ∪ Maps of Making)"}
            {hiddenCount > 0
              ? " — narrow source/geo/name filters to see more."
              : ""}
          </p>
        </div>
      )}
    </fieldset>
  );
}
