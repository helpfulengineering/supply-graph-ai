import { useQuery } from "@tanstack/react-query";
import { fetchDomains } from "../../api/ohm/utility";
import { useDomain } from "../../context/DomainContext";
import { DEFAULT_DOMAIN, type OhmDomain } from "./domainPreference";

const FALLBACK_OPTIONS: { id: OhmDomain; name: string; description: string }[] = [
  {
    id: "manufacturing",
    name: "Manufacturing",
    description: "Hardware designs and manufacturing facilities (OKH / OKW).",
  },
  {
    id: "cooking",
    name: "Cooking",
    description: "Recipes and kitchens for cooking-domain matching.",
  },
];

function domainChoices(
  apiDomains: { id: string; name: string; description?: string | null }[] | undefined,
): typeof FALLBACK_OPTIONS {
  const byId = new Map(FALLBACK_OPTIONS.map((o) => [o.id, { ...o }]));
  for (const d of apiDomains ?? []) {
    if (d.id !== "manufacturing" && d.id !== "cooking") continue;
    const id = d.id as OhmDomain;
    const base = byId.get(id)!;
    byId.set(id, {
      id,
      name: d.name || base.name,
      description: d.description || base.description,
    });
  }
  return FALLBACK_OPTIONS.map((f) => byId.get(f.id)!);
}

export function DomainPanel() {
  const { domain, setDomain } = useDomain();
  const domains = useQuery({ queryKey: ["domains"], queryFn: fetchDomains });
  const choices = domainChoices(domains.data);

  return (
    <div className="space-y-6">
      <section
        aria-labelledby="domain-selection-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      >
        <h2 id="domain-selection-heading" className="text-lg font-semibold text-foreground">
          Domain selection
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Choose one matching domain for this browser. Default is {DEFAULT_DOMAIN}. Cooking
          shows Recipes and Kitchens in the nav; manufacturing shows Designs, Facilities,
          Packages, and Match.
        </p>

        <fieldset className="mt-4 space-y-3">
          <legend className="sr-only">Active domain</legend>
          {choices.map((opt) => {
            const selected = domain === opt.id;
            return (
              <label
                key={opt.id}
                className={[
                  "flex cursor-pointer gap-3 rounded-lg border p-3 transition-colors",
                  selected
                    ? "border-indigo-600 bg-indigo-50 dark:border-indigo-400 dark:bg-indigo-950"
                    : "border-slate-200 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800",
                ].join(" ")}
              >
                <input
                  type="radio"
                  name="ohm-domain"
                  value={opt.id}
                  checked={selected}
                  onChange={() => setDomain(opt.id)}
                  className="mt-1"
                />
                <span>
                  <span className="block text-sm font-medium text-foreground">{opt.name}</span>
                  {opt.description && (
                    <span className="mt-0.5 block text-sm text-muted-foreground">
                      {opt.description}
                    </span>
                  )}
                </span>
              </label>
            );
          })}
        </fieldset>

        {domains.isError && (
          <p className="mt-3 text-xs text-muted-foreground" role="status">
            Could not load domains from the API; showing built-in options.
          </p>
        )}
      </section>
    </div>
  );
}
