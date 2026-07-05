import type { NetworkFilters as Filters } from "../../api/ohm/network";
import type { FilterOptions } from "./deriveFilterOptions";
import { Button } from "../../components/ui/button";

const SELECT_CLASS =
  "w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

function FilterSelect({
  label,
  value,
  allLabel,
  options,
  onChange,
  hint,
}: {
  label: string;
  value: string | undefined;
  allLabel: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  hint?: string;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-muted-foreground">
        {label}
        {hint && <span className="ml-1 text-xs text-slate-500">({hint})</span>}
      </span>
      <select
        className={SELECT_CLASS}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{allLabel}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

/**
 * Filter panel for the unified network surface. Cross-source axes
 * (source/country/city/process/status) plus the local-only axes
 * (region/access type) that soft-filter — the "(local only)" hint signals that
 * MoM spaces are kept but flagged ambiguous when those are set.
 */
export function NetworkFilters({
  filters,
  options,
  activeCount,
  onChange,
  onClear,
}: {
  filters: Filters;
  options: FilterOptions;
  activeCount: number;
  onChange: (next: Filters) => void;
  onClear: () => void;
}) {
  const set = (key: keyof Filters, value: string) =>
    onChange({ ...filters, [key]: value || undefined });

  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-foreground">Filters</h2>
        {activeCount > 0 && (
          <Button variant="ghost" size="sm" onClick={onClear}>
            Clear ({activeCount})
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-1">
        <FilterSelect
          label="Source"
          value={filters.source}
          allLabel="All sources"
          options={[
            { value: "local", label: "OHM facilities" },
            { value: "mom", label: "Maps of Making" },
          ]}
          onChange={(v) => set("source", v)}
        />
        <FilterSelect
          label="Country"
          value={filters.country}
          allLabel="All countries"
          options={options.countries.map((c) => ({ value: c, label: c }))}
          onChange={(v) => set("country", v)}
        />
        <label className="block text-sm">
          <span className="mb-1 block text-muted-foreground">City</span>
          <input
            type="search"
            className={SELECT_CLASS}
            placeholder="City contains…"
            value={filters.city ?? ""}
            onChange={(e) => set("city", e.target.value)}
          />
        </label>
        <FilterSelect
          label="Process"
          value={filters.process}
          allLabel="All processes"
          options={options.processes.map((p) => ({ value: p.id, label: p.label }))}
          onChange={(v) => set("process", v)}
        />
        <FilterSelect
          label="Status"
          value={filters.status}
          allLabel="Any status"
          options={options.statuses.map((s) => ({ value: s, label: s }))}
          onChange={(v) => set("status", v)}
        />
        <FilterSelect
          label="Region"
          hint="local only"
          value={filters.region}
          allLabel="All regions"
          options={options.regions.map((r) => ({ value: r, label: r }))}
          onChange={(v) => set("region", v)}
        />
        <FilterSelect
          label="Access"
          hint="local only"
          value={filters.access_type}
          allLabel="Any access"
          options={options.accessTypes.map((a) => ({ value: a, label: a }))}
          onChange={(v) => set("access_type", v)}
        />
      </div>
    </div>
  );
}
