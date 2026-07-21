import { useQuery } from "@tanstack/react-query";
import { fetchSecurityPolicy } from "../../api/ohm/identity";
import { Badge } from "../../components/ui/Badge";

/** Compact security-policy summary for Home System and Settings footer. */
export function SecurityPolicyBadge() {
  const policy = useQuery({
    queryKey: ["identity", "security-policy"],
    queryFn: fetchSecurityPolicy,
    staleTime: 5 * 60_000,
    retry: false,
  });

  if (policy.isLoading) {
    return <span className="text-xs text-muted-foreground">Loading policy…</span>;
  }
  if (policy.isError || !policy.data) {
    return null;
  }

  const p = policy.data;
  return (
    <div className="flex flex-wrap items-center gap-1.5" aria-label="Security policy">
      <Badge variant="indigo">{p.mode}</Badge>
      <Badge variant="default">grant TTL {p.grant_ttl_days}d</Badge>
      <Badge variant={p.mdns_advertise ? "green" : "default"}>
        mDNS {p.mdns_advertise ? "on" : "off"}
      </Badge>
    </div>
  );
}
