/**
 * Reading a rules file before writing it.
 *
 * The whole point of the compare step is that an operator sees what an import
 * would do while it is still a question. These turn the server's per-domain
 * change lists into the one sentence that answers it.
 */
import type { RuleComparison } from "@/api/ohm/rules";
import type { CapabilityRule, RuleFileFormat } from "@/api/ohm/rules";

export interface ComparisonSummary {
  added: number;
  updated: number;
  deleted: number;
  domains: string[];
  /** "3 new · 1 changed · 12 unchanged" — or that nothing would change. */
  label: string;
}

export function summariseComparison(
  comparison: RuleComparison,
): ComparisonSummary {
  let added = 0;
  let updated = 0;
  let deleted = 0;
  const domains = Object.keys(comparison.domains);
  for (const domain of domains) {
    const changes = comparison.domains[domain]?.changes;
    added += changes?.added?.length ?? 0;
    updated += changes?.updated?.length ?? 0;
    deleted += changes?.deleted?.length ?? 0;
  }

  const parts: string[] = [];
  if (added) parts.push(`${added} new`);
  if (updated) parts.push(`${updated} changed`);
  if (deleted) parts.push(`${deleted} removed`);

  return {
    added,
    updated,
    deleted,
    domains,
    label: parts.length ? parts.join(" · ") : "no changes",
  };
}

/**
 * Guess the format from what was pasted, so the operator does not have to say.
 *
 * JSON is the narrow case and worth detecting rather than defaulting to: a
 * pasted JSON file sent as YAML parses (YAML is a JSON superset) but a pasted
 * YAML file sent as JSON does not, so guessing wrong in one direction is
 * harmless and in the other is a confusing parse error.
 */
export function guessRuleFormat(content: string): RuleFileFormat {
  return content.trim().startsWith("{") ? "json" : "yaml";
}

/** Rules by domain, for a list that reads as sections rather than one run. */
export function groupRulesByDomain(
  rules: readonly CapabilityRule[],
): Array<{ domain: string; rules: CapabilityRule[] }> {
  const byDomain = new Map<string, CapabilityRule[]>();
  for (const rule of rules) {
    const bucket = byDomain.get(rule.domain);
    if (bucket) bucket.push(rule);
    else byDomain.set(rule.domain, [rule]);
  }
  return [...byDomain]
    .map(([domain, group]) => ({
      domain,
      rules: [...group].sort((a, b) => a.id.localeCompare(b.id)),
    }))
    .sort((a, b) => a.domain.localeCompare(b.domain));
}

/** One line describing what a rule does, in the reader's terms. */
export function ruleSentence(rule: CapabilityRule): string {
  const satisfies = rule.satisfies_requirements.join(", ");
  if (!satisfies) return `${rule.capability} — no requirements declared`;
  return `${rule.capability} satisfies ${satisfies}`;
}
