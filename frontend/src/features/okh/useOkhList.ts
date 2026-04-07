import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { fetchOkhList } from "../../api/okh";
import type { OkhManifest } from "../../types/okh";

export type SortField = "title" | "version" | "documentation_language";
export type SortOrder = "asc" | "desc";

const PAGE_SIZE = 20;

function normalize(s: string | null | undefined) {
  return (s ?? "").toLowerCase();
}

function sortItems(items: OkhManifest[], field: SortField, order: SortOrder): OkhManifest[] {
  return [...items].sort((a, b) => {
    const av = normalize(a[field]);
    const bv = normalize(b[field]);
    const cmp = av.localeCompare(bv);
    return order === "asc" ? cmp : -cmp;
  });
}

function filterItems(items: OkhManifest[], query: string): OkhManifest[] {
  const q = query.trim().toLowerCase();
  if (!q) return items;
  return items.filter((item) => {
    return (
      normalize(item.title).includes(q) ||
      normalize(item.function).includes(q) ||
      normalize(item.description).includes(q) ||
      item.keywords.some((k) => k.toLowerCase().includes(q)) ||
      item.manufacturing_processes.some((p) => p.toLowerCase().includes(q))
    );
  });
}

export function useOkhList() {
  const [filterText, setFilterText] = useState("");
  const [sortField, setSortField] = useState<SortField>("title");
  const [sortOrder, setSortOrder] = useState<SortOrder>("asc");
  const [page, setPage] = useState(1);

  const query = useQuery({
    queryKey: ["okh-list"],
    queryFn: () => fetchOkhList({ page: 1, page_size: 100 }),
    staleTime: 60_000,
  });

  const processed = useMemo(() => {
    const items = query.data?.items ?? [];
    const filtered = filterItems(items, filterText);
    const sorted = sortItems(filtered, sortField, sortOrder);
    const totalItems = sorted.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
    const safePage = Math.min(page, totalPages);
    const start = (safePage - 1) * PAGE_SIZE;
    const pageItems = sorted.slice(start, start + PAGE_SIZE);
    return { pageItems, totalItems, totalPages, safePage };
  }, [query.data, filterText, sortField, sortOrder, page]);

  function handleFilterChange(text: string) {
    setFilterText(text);
    setPage(1);
  }

  function handleSortChange(field: SortField, order: SortOrder) {
    setSortField(field);
    setSortOrder(order);
    setPage(1);
  }

  return {
    ...processed,
    filterText,
    sortField,
    sortOrder,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    setPage,
    handleFilterChange,
    handleSortChange,
    PAGE_SIZE,
  };
}
