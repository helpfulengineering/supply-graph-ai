import { useMemo, useState } from "react";

export interface FacilityOption {
  id: string;
  name: string;
}

/**
 * Optional facility pre-filter for matching (web-ui review #4). A controlled,
 * collapsible checklist: the parent owns the selected-id set. An empty set
 * means "match against all facilities" — the default, so matching is unchanged
 * unless the user narrows it here.
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
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const selected = useMemo(() => new Set(selectedIds), [selectedIds]);

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return facilities;
    return facilities.filter((f) => f.name.toLowerCase().includes(needle));
  }, [facilities, q]);

  const summary =
    selectedIds.length === 0
      ? "Matching against all facilities"
      : `Limited to ${selectedIds.length} facilit${selectedIds.length === 1 ? "y" : "ies"}`;

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange([...next]);
  }

  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
      >
        <span aria-hidden="true">{open ? "▾" : "▸"}</span>
        <span>Facilities</span>
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-slate-600 dark:text-slate-300">
          {summary}
        </span>
      </button>

      {open && (
        <fieldset className="mt-2 max-w-md rounded-md border border-input p-3">
          <legend className="px-1 text-xs text-muted-foreground">
            Limit which facilities to match against (optional)
          </legend>

          {isLoading && (
            <p className="text-sm text-muted-foreground">Loading facilities…</p>
          )}
          {isError && (
            <p className="text-sm text-red-600 dark:text-red-400">
              Couldn’t load facilities — matching will use all of them.
            </p>
          )}

          {!isLoading && !isError && (
            <>
              <div className="mb-2 flex items-center gap-2">
                <input
                  type="search"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Filter facilities…"
                  aria-label="Filter facilities"
                  className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div className="mb-2 flex gap-3 text-xs">
                <button
                  type="button"
                  className="text-indigo-600 hover:underline dark:text-indigo-400"
                  onClick={() => onChange(facilities.map((f) => f.id))}
                >
                  Select all
                </button>
                <button
                  type="button"
                  className="text-slate-600 hover:underline dark:text-slate-300"
                  onClick={() => onChange([])}
                >
                  Clear
                </button>
              </div>
              <ul className="max-h-48 space-y-1 overflow-y-auto">
                {visible.map((f) => (
                  <li key={f.id}>
                    <label className="flex items-center gap-2 text-sm text-foreground">
                      <input
                        type="checkbox"
                        checked={selected.has(f.id)}
                        onChange={() => toggle(f.id)}
                      />
                      {f.name}
                    </label>
                  </li>
                ))}
                {visible.length === 0 && (
                  <li className="text-sm text-muted-foreground">No facilities match “{q}”.</li>
                )}
              </ul>
            </>
          )}
        </fieldset>
      )}
    </div>
  );
}
