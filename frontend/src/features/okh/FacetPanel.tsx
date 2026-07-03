import { Button } from "../../components/ui/button";
import { PRIMARY_FACET, type FacetGroup, type FacetKey, type FacetSelections } from "./facets";

interface Props {
  groups: FacetGroup[];
  selections: FacetSelections;
  selectedCount: number;
  onToggle: (key: FacetKey, value: string) => void;
  onClear: () => void;
}

export function FacetPanel({
  groups,
  selections,
  selectedCount,
  onToggle,
  onClear,
}: Props) {
  return (
    <nav aria-label="Filters" className="space-y-5 text-sm">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-foreground">Filters</h2>
        {selectedCount > 0 && (
          <Button variant="ghost" size="sm" onClick={onClear}>
            Clear all
          </Button>
        )}
      </div>

      {groups.map((group) => {
        const selected = selections[group.key] ?? [];
        return (
          <div key={group.key}>
            <h3 className="mb-2 flex items-center gap-1.5 font-medium text-muted-foreground">
              {group.label}
              {group.key === PRIMARY_FACET && (
                <span
                  title="Provisional categories derived from design text; a curated taxonomy is coming."
                  className="rounded bg-muted px-1 py-0.5 text-[10px] font-normal uppercase tracking-wide text-muted-foreground"
                >
                  provisional
                </span>
              )}
            </h3>
            <ul className="space-y-1">
              {group.options.map((opt) => {
                const checked = selected.includes(opt.value);
                return (
                  <li key={opt.value}>
                    <label className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 hover:bg-accent">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => onToggle(group.key, opt.value)}
                        className="h-4 w-4 accent-primary"
                      />
                      <span className="flex-1 truncate text-foreground">{opt.value}</span>
                      <span className="tabular-nums text-xs text-muted-foreground">
                        {opt.count}
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}
