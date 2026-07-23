import type { RecordProvenance } from "../../api/ohm/okw";

/** True when ingest stamped a federated OKW (role synced_from). */
export function isSyncedFacilityProvenance(
  provenance: RecordProvenance | null | undefined,
): boolean {
  if (!provenance) return false;
  return (provenance.authored_by ?? []).some((c) => c.role === "synced_from");
}

export function SyncedFacilityBanner({
  publishedBy,
}: {
  publishedBy: string | null | undefined;
}) {
  return (
    <div
      role="status"
      className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
    >
      <p className="font-medium">Synced from a federation peer</p>
      <p className="mt-1 text-xs opacity-90">
        {publishedBy ? (
          <>
            Publisher{" "}
            <code className="break-all text-xs">{publishedBy}</code>.{" "}
          </>
        ) : null}
        You can edit or delete this copy on this node; changes are not pushed back to the peer.
      </p>
    </div>
  );
}
