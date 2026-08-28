import { useMemo, useState } from "react";
import type { Kitchen } from "../../types/kitchen";
import { Fieldset } from "../../components/ui/Fieldset";
import { SCROLL_LIST } from "../../components/ui/surface";
import { FIELD, LINK_BUTTON, LINK_BUTTON_MUTED } from "../../components/ui/field";

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
    <Fieldset legend="Kitchens" description={summary} className="max-w-2xl">

      {isLoading && <p className="text-sm text-muted-foreground">Loading kitchens…</p>}
      {isError && (
        <p className="text-sm text-destructive">
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
            className={FIELD}
          />
          <div className="flex gap-3 text-xs">
            <button
              type="button"
              className={LINK_BUTTON}
              onClick={() => onChange(visible.map((k) => k.id))}
            >
              Select all visible
            </button>
            <button
              type="button"
              className={LINK_BUTTON_MUTED}
              onClick={() => onChange([])}
            >
              Clear
            </button>
          </div>
          <ul className={SCROLL_LIST}>
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
    </Fieldset>
  );
}
