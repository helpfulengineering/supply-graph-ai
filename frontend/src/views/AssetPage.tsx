"use client";

import { useParams } from "next/navigation";
import { AssetDetailView } from "@/features/asset/AssetDetailView";
import { AssetListView } from "@/features/asset/AssetListView";

/** List or detail, discriminated by the route param — as OkwPage does. */
export function AssetPage() {
  const params = useParams<{ id?: string }>();
  const id = typeof params?.id === "string" ? params.id : undefined;
  return id ? <AssetDetailView id={id} /> : <AssetListView />;
}
