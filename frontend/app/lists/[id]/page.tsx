"use client";

import { useParams } from "next/navigation";
import { CuratedListPage } from "@/features/lists/CuratedLists";

export default function Page() {
  const params = useParams<{ id: string }>();
  return <CuratedListPage listId={params.id} />;
}
