import type { Attestation } from "../../api/ohm/identity";
import { Badge } from "../../components/ui/Badge";

/** Renders type / issuer / created_at only — no reputation scores. */
export function AttestationList({ items }: { items: Attestation[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">No attestations.</p>;
  }
  return (
    <ul className="divide-y divide-border">
      {items.map((a) => (
        <li key={a.attestation_id} className="py-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="blue">{a.type}</Badge>
            {a.created_at && (
              <span className="text-xs text-muted-foreground">
                {a.created_at}
              </span>
            )}
          </div>
          <p className="mt-1 break-all font-mono text-xs text-muted-foreground">
            issuer {a.issuer_did}
          </p>
          <p className="mt-0.5 break-all font-mono text-xs text-muted-foreground">
            subject {a.subject_did}
          </p>
        </li>
      ))}
    </ul>
  );
}
