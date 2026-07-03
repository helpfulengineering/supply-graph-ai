import { useParams } from "react-router-dom";
import { OkwListView } from "../features/okw/OkwListView";
import { OkwDetailView } from "../features/okw/OkwDetailView";

export function OkwPage() {
  const { id } = useParams<{ id?: string }>();
  return id ? <OkwDetailView id={id} /> : <OkwListView />;
}
