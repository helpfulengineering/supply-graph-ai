import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { PANEL } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";
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
        className={cn(PANEL, "p-5")}
      >
        <h2 id="domain-selection-heading" className={SECTION_TITLE}>
          Domain selection
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Choose one matching domain for this browser. Default is {DEFAULT_DOMAIN}. Cooking
          shows Recipes and Kitchens in the nav; manufacturing shows Designs, Facilities,
          Packages, and Match.
        </p>

        <fieldset className="mt-4 min-w-0 space-y-3">
          <legend className="sr-only">Active domain</legend>
          {choices.map((opt) => {
            const selected = domain === opt.id;
            return (
              <label
                key={opt.id}
                className={[
                  "flex cursor-pointer gap-3 rounded-lg border p-3 transition-colors",
                  selected
                    ? "border-primary bg-accent/40"
                    : "border-border hover:bg-accent/30",
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
                    // muted-foreground is tuned for the default surface; on the
                    // selected option's indigo background it falls to 4.24:1,
                    // under the 4.5:1 AA threshold. Darken it when selected.
                    // Was a hand-picked indigo shade; primary-ink is the
                    // token that encodes the same fix everywhere.
                    <span
                      className={[
                        "mt-0.5 block text-sm",
                        selected
                          ? "text-primary-ink"
                          : "text-muted-foreground",
                      ].join(" ")}
                    >
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
