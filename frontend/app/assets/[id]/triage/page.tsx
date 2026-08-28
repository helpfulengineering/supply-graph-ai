"use client";

import { useParams } from "next/navigation";
import { AssetTriagePage } from "@/features/asset/AssetTriagePage";

export default function Page() {
  const params = useParams<{ id: string }>();
  return <AssetTriagePage id={String(params?.id ?? "")} />;
}
