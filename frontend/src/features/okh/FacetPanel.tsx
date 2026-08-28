import { Button } from "../../components/ui/button";
import { CHECKBOX, CHOICE_ROW } from "../../components/ui/field";
import {
  PRIMARY_FACET,
  type FacetGroup,
  type FacetKey,
  type FacetSelections,
} from "./facets";
import { CARD_TITLE, SECTION_LABEL_SM } from "../../components/ui/typography";
import { cn } from "@/lib/utils";

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
    <nav aria-label="Filters" className="space-y-6 text-sm">
      <div className="flex items-center justify-between">
        <h2 className={CARD_TITLE}>Filters</h2>
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
            <h3
              className={cn(SECTION_LABEL_SM, "mb-2 flex items-center gap-1.5")}
            >
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
                    <label className={CHOICE_ROW}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => onToggle(group.key, opt.value)}
                        className={CHECKBOX}
                      />
                      <span className="min-w-0 flex-1 truncate text-foreground">
                        {opt.value}
                      </span>
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
