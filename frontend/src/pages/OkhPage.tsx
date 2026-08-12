import { useParams } from "react-router-dom";
import { OkhListView } from "../features/okh/OkhListView";
import { OkhDetailView } from "../features/okh/OkhDetailView";
import { RecipeListView } from "../features/okh/RecipeListView";
import { useDomain } from "../context/DomainContext";

export function OkhPage() {
  const { id } = useParams<{ id?: string }>();
  const { domain } = useDomain();
  if (id) return <OkhDetailView id={id} />;
  // Cooking has no detail page (list-only, see the cooking-domain-instance plan).
  return domain === "cooking" ? <RecipeListView /> : <OkhListView />;
}
