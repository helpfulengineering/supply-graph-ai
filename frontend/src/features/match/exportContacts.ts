import { exportMatchContacts } from "../../api/ohm/match";
import type { RankedSolution } from "./matchViewModel";

/**
 * Download the selected facilities as a contact list.
 *
 * Coordination happens outside OHM: this is how a match result leaves it. The
 * server formats — one implementation shared with `ohm match export-contacts` —
 * and names the file, because the name carries the design and the date and two
 * exports a week apart are meant to be diffable in a directory.
 */
export async function downloadContacts(
  selected: RankedSolution[],
  designName: string | undefined,
  matchedAt?: string,
): Promise<void> {
  const { blob, filename } = await exportMatchContacts({
    solutions: selected.map((s) => ({
      facility_id: s.facilityId,
      facility_name: s.facilityName,
      confidence: s.confidence,
      facility: (s.facility ?? {}) as Record<string, never>,
      tree: {},
    })),
    format: "csv",
    design_name: designName ?? null,
    matched_at: matchedAt ?? null,
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
