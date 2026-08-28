/**
 * The salvage search, held in the URL.
 *
 * In the query string so a search is shareable — the same property the catalog
 * and match filters have, and the reason "have a look at what we've got for
 * this part" is a link rather than a set of instructions.
 */
import type { SalvageMatchRequest } from "@/api/ohm/asset";
import { COMPONENT_CONDITIONS, parseCondition } from "./componentCondition";
import type { ComponentCondition } from "./componentCondition";

export interface SalvageQuery {
  componentName: string;
  partNumber: string;
  manifestId: string;
  conditions: ComponentCondition[];
  includeClaimed: boolean;
}

export const EMPTY_SALVAGE_QUERY: SalvageQuery = {
  componentName: "",
  partNumber: "",
  manifestId: "",
  conditions: [],
  includeClaimed: false,
};

export function salvageQueryFromParams(params: URLSearchParams): SalvageQuery {
  const conditions = (params.get("conditions") ?? "")
    .split(",")
    .map((c) => parseCondition(c.trim()))
    .filter((c): c is ComponentCondition => c !== null);
  return {
    componentName: params.get("component") ?? "",
    partNumber: params.get("part") ?? "",
    manifestId: params.get("design") ?? "",
    conditions,
    includeClaimed: params.get("claimed") === "1",
  };
}

/** Only non-default values are written, so a plain search has a plain URL. */
export function salvageQueryToParams(query: SalvageQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.componentName.trim())
    params.set("component", query.componentName.trim());
  if (query.partNumber.trim()) params.set("part", query.partNumber.trim());
  if (query.manifestId) params.set("design", query.manifestId);
  if (
    query.conditions.length &&
    query.conditions.length < COMPONENT_CONDITIONS.length
  ) {
    params.set("conditions", query.conditions.join(","));
  }
  if (query.includeClaimed) params.set("claimed", "1");
  return params;
}

/**
 * The one rule the server enforces with a 422, restated in the client.
 *
 * Not defensive duplication: without it the only way to learn the rule is to
 * press the button and read an error, and the control that would tell you is
 * the one you did not fill in.
 */
export function salvageQueryError(query: SalvageQuery): string | null {
  if (!query.componentName.trim() && !query.partNumber.trim()) {
    return "Enter a component name or a part number to search.";
  }
  return null;
}

export function isSalvageQueryRunnable(query: SalvageQuery): boolean {
  return salvageQueryError(query) === null;
}

export function toSalvageRequest(query: SalvageQuery): SalvageMatchRequest {
  return {
    component_name: query.componentName.trim() || null,
    part_number: query.partNumber.trim() || null,
    manifest_id: query.manifestId || null,
    conditions: query.conditions.length ? [...query.conditions] : null,
    // Offered inverted in the UI: "include components already claimed" is the
    // decision a coordinator makes, where `exclude_claimed` is the server's
    // way of saying it.
    exclude_claimed: !query.includeClaimed,
  };
}
