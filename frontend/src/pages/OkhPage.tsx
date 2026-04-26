import { useParams } from "react-router-dom";
import { OkhListView } from "../features/okh/OkhListView";
import { OkhDetailView } from "../features/okh/OkhDetailView";

export function OkhPage() {
  const { id } = useParams<{ id?: string }>();
  return id ? <OkhDetailView id={id} /> : <OkhListView />;
}
