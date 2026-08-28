/**
 * Confirm copy for deleting an asset, warning when it strands a live claim.
 *
 * A claimed component is another coordinator's reservation on a part in this
 * unit. Deleting the record takes it away without telling them, so the count
 * goes in the sentence rather than being discovered later.
 */
import type { ComponentState } from "@/api/ohm/asset";
import { claimState } from "./claimState";

export function assetDeleteConfirmMessage(
  assetTag: string,
  states: readonly ComponentState[],
  now: number,
): string {
  const base = `Delete “${assetTag || "this asset"}”?`;
  const claims = states.filter(
    (state) => claimState(state, now).claimed,
  ).length;
  if (claims === 0) return base;
  const parts = claims === 1 ? "1 component is" : `${claims} components are`;
  return `${base}\n\n${parts} claimed for retrieval. Deleting this record cancels the claim without notifying whoever made it.`;
}
