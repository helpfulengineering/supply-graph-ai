"use client";

import { useParams } from "next/navigation";
import { OkhListView } from "../features/okh/OkhListView";
import { OkhDetailView } from "../features/okh/OkhDetailView";
import { RecipeListView } from "../features/okh/RecipeListView";
import { RecipeDetailView } from "../features/okh/RecipeDetailView";
import { useDomain } from "../context/DomainContext";

export function OkhPage() {
  const { id } = useParams<{ id?: string }>();
  const { domain } = useDomain();
  if (id)
    return domain === "cooking" ? (
      <RecipeDetailView id={id} />
    ) : (
      <OkhDetailView id={id} />
    );
  return domain === "cooking" ? <RecipeListView /> : <OkhListView />;
}
