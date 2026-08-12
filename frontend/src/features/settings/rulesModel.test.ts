import { describe, expect, it } from "vitest";
import type { CapabilityRule, RuleComparison } from "@/api/ohm/rules";
import {
  groupRulesByDomain,
  guessRuleFormat,
  ruleSentence,
  summariseComparison,
} from "./rulesModel";

function rule(overrides: Partial<CapabilityRule> = {}): CapabilityRule {
  return {
    id: "cnc",
    type: "capability",
    capability: "cnc_milling",
    satisfies_requirements: ["machining"],
    direction: "bidirectional",
    confidence: 0.9,
    domain: "manufacturing",
    description: null,
    source: null,
    tags: [],
    ...overrides,
  };
}

function comparison(
  changes: Partial<RuleComparison["domains"]>,
): RuleComparison {
  return { domains: changes as RuleComparison["domains"] };
}

describe("summariseComparison", () => {
  it("counts across every domain in the file", () => {
    const summary = summariseComparison(
      comparison({
        manufacturing: {
          changes: { added: ["a", "b"], updated: ["c"], deleted: [] },
        },
        cooking: { changes: { added: [], updated: [], deleted: ["d"] } },
      }),
    );
    expect(summary).toMatchObject({ added: 2, updated: 1, deleted: 1 });
    expect(summary.label).toBe("2 new · 1 changed · 1 removed");
  });

  it("says so plainly when an import would change nothing", () => {
    // "" or "0 new · 0 changed" both read as a broken control.
    const summary = summariseComparison(
      comparison({
        manufacturing: { changes: { added: [], updated: [], deleted: [] } },
      }),
    );
    expect(summary.label).toBe("no changes");
  });

  it("survives a domain with no changes key at all", () => {
    const summary = summariseComparison({
      domains: { manufacturing: {} as RuleComparison["domains"][string] },
    });
    expect(summary.label).toBe("no changes");
  });
});

describe("guessRuleFormat", () => {
  it("reads a leading brace as JSON", () => {
    expect(guessRuleFormat('  {"domain": "manufacturing"}')).toBe("json");
  });

  it("defaults to YAML", () => {
    // The safe direction: YAML is a JSON superset, so a JSON file parsed as
    // YAML still works, where a YAML file parsed as JSON does not.
    expect(guessRuleFormat("domain: manufacturing")).toBe("yaml");
    expect(guessRuleFormat("")).toBe("yaml");
  });
});

describe("groupRulesByDomain", () => {
  it("sorts domains, and rules within them", () => {
    const groups = groupRulesByDomain([
      rule({ id: "z", domain: "manufacturing" }),
      rule({ id: "a", domain: "manufacturing" }),
      rule({ id: "b", domain: "cooking" }),
    ]);
    expect(groups.map((g) => g.domain)).toEqual(["cooking", "manufacturing"]);
    expect(groups[1].rules.map((r) => r.id)).toEqual(["a", "z"]);
  });
});

describe("ruleSentence", () => {
  it("reads as a sentence about what the rule does", () => {
    expect(
      ruleSentence(rule({ satisfies_requirements: ["machining", "milling"] })),
    ).toBe("cnc_milling satisfies machining, milling");
  });

  it("names a rule that declares no requirements rather than trailing off", () => {
    expect(ruleSentence(rule({ satisfies_requirements: [] }))).toBe(
      "cnc_milling — no requirements declared",
    );
  });
});
