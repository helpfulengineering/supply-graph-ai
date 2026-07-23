import type { TaxonomyProcess } from "./facilityFormModel";

function rootsOf(taxonomy: TaxonomyProcess[]): TaxonomyProcess[] {
  return taxonomy
    .filter((p) => !p.parent)
    .sort((a, b) => a.display_name.localeCompare(b.display_name));
}

function childrenOf(
  taxonomy: TaxonomyProcess[],
  parentId: string,
): TaxonomyProcess[] {
  return taxonomy
    .filter((p) => p.parent === parentId)
    .sort((a, b) => a.display_name.localeCompare(b.display_name));
}

interface Props {
  taxonomy: TaxonomyProcess[];
  selectedParents: string[];
  selectedSubtypes: string[];
  onChange: (next: { parents: string[]; subtypes: string[] }) => void;
  disabled?: boolean;
}

export function ProcessTaxonomyPicker({
  taxonomy,
  selectedParents,
  selectedSubtypes,
  onChange,
  disabled,
}: Props) {
  const roots = rootsOf(taxonomy);

  const toggleParent = (id: string) => {
    if (selectedParents.includes(id)) {
      const childIds = childrenOf(taxonomy, id).map((c) => c.canonical_id);
      onChange({
        parents: selectedParents.filter((p) => p !== id),
        subtypes: selectedSubtypes.filter((s) => !childIds.includes(s)),
      });
      return;
    }
    onChange({ parents: [...selectedParents, id], subtypes: selectedSubtypes });
  };

  const toggleSubtype = (parentId: string, id: string) => {
    const subtypes = selectedSubtypes.includes(id)
      ? selectedSubtypes.filter((s) => s !== id)
      : [...selectedSubtypes, id];
    const parents = selectedParents.includes(parentId)
      ? selectedParents
      : [...selectedParents, parentId];
    onChange({ parents, subtypes });
  };

  if (!roots.length) {
    return <p className="text-sm text-muted-foreground">No processes in taxonomy.</p>;
  }

  return (
    <ul className="space-y-3" aria-label="Manufacturing processes">
      {roots.map((root) => {
        const kids = childrenOf(taxonomy, root.canonical_id);
        const parentOn = selectedParents.includes(root.canonical_id);
        return (
          <li key={root.canonical_id} className="text-sm">
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={parentOn}
                disabled={disabled}
                onChange={() => toggleParent(root.canonical_id)}
              />
              <span className="font-medium text-slate-800 dark:text-slate-100">
                {root.display_name}
              </span>
            </label>
            {parentOn && kids.length > 0 && (
              <ul className="mt-2 ml-6 space-y-1.5 border-l border-slate-200 pl-3 dark:border-slate-700">
                {kids.map((kid) => (
                  <li key={kid.canonical_id}>
                    <label className="flex items-start gap-2 text-slate-700 dark:text-slate-200">
                      <input
                        type="checkbox"
                        className="mt-0.5"
                        checked={selectedSubtypes.includes(kid.canonical_id)}
                        disabled={disabled}
                        onChange={() =>
                          toggleSubtype(root.canonical_id, kid.canonical_id)
                        }
                      />
                      <span>{kid.display_name}</span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );
}
