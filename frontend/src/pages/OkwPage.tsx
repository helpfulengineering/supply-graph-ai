import { useParams } from "react-router-dom";
import { NetworkView } from "../features/network/NetworkView";
import { OkwDetailView } from "../features/okw/OkwDetailView";
import { KitchenListView } from "../features/okw/KitchenListView";
import { useDomain } from "../context/DomainContext";

export function OkwPage() {
  const { id } = useParams<{ id?: string }>();
  const { domain } = useDomain();
  // The list route is the unified network surface (local OKW ∪ MoM); the detail
  // route stays the local OKW facility page. Cooking has no detail page
  // (list-only, see the cooking-domain-instance plan).
  if (id) return <OkwDetailView id={id} />;
  return domain === "cooking" ? <KitchenListView /> : <NetworkView />;
}
