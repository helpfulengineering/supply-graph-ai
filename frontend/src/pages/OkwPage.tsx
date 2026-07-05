import { useParams } from "react-router-dom";
import { NetworkView } from "../features/network/NetworkView";
import { OkwDetailView } from "../features/okw/OkwDetailView";

export function OkwPage() {
  const { id } = useParams<{ id?: string }>();
  // The list route is the unified network surface (local OKW ∪ MoM); the detail
  // route stays the local OKW facility page.
  return id ? <OkwDetailView id={id} /> : <NetworkView />;
}
