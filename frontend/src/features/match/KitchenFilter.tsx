import { useMemo, useState } from "react";
import type { Kitchen } from "../../types/kitchen";

/**
 * Kitchen scope for cooking-domain matching. Deliberately simpler than
 * FacilityFilter (no geo filters): kitchens have no location fields.
 */
export function KitchenFilter({
  kitchens,
  selectedIds,
  onChange,
  isLoading,
  isError,
}: {
  kitchens: Kitchen[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  isLoading?: boolean;
  isError?: boolean;
}) {
  const [q, setQ] = useState("");
  const selected = useMemo(() => new Set(selectedIds), [selectedIds]);

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return kitchens;
    return kitchens.filter((k) => k.name.toLowerCase().includes(needle));
  }, [kitchens, q]);

  const summary =
    selectedIds.length === 0
      ? "Select kitchens to match against"
      : `${selectedIds.length} kitchen${selectedIds.length === 1 ? "" : "s"} selected`;

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange([...next]);
  }

  return (
    <fieldset className="max-w-2xl rounded-lg border border-input p-4">
      <legend className="px-1 text-sm font-medium text-foreground">Kitchens</legend>
      <p className="mb-3 text-xs text-muted-foreground">{summary}</p>

      {isLoading && <p className="text-sm text-muted-foreground">Loading kitchens…</p>}
      {isError && (
        <p className="text-sm text-red-600 dark:text-red-400">
          Couldn’t load kitchens. Try again before running a match.
        </p>
      )}

      {!isLoading && !isError && (
        <div className="space-y-3">
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filter kitchens by name…"
            aria-label="Filter kitchens by name"
            className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <div className="flex gap-3 text-xs">
            <button
              type="button"
              className="text-indigo-600 hover:underline dark:text-indigo-400"
              onClick={() => onChange(visible.map((k) => k.id))}
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
            {visible.map((k) => (
              <li key={k.id}>
                <label className="flex items-center gap-2 text-sm text-foreground">
                  <input
                    type="checkbox"
                    aria-label={k.name}
                    checked={selected.has(k.id)}
                    onChange={() => toggle(k.id)}
                  />
                  <span className="min-w-0 flex-1 truncate">{k.name}</span>
                </label>
              </li>
            ))}
            {visible.length === 0 && (
              <li className="text-sm text-muted-foreground">
                No kitchens match the current filter.
              </li>
            )}
          </ul>
        </div>
      )}
    </fieldset>
  );
}
