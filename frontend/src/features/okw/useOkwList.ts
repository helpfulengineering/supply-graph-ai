import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { searchOkw } from "../../api/ohm/okw";
import type { OkwFacility } from "../../types/okw";
import { humanizeProcess } from "./processDisplay";

const PAGE_SIZE = 24;

function locationText(f: OkwFacility): string {
  const a = f.location?.address;
  return [a?.city ?? f.location?.city, a?.region, a?.country ?? f.location?.country]
    .filter(Boolean)
    .join(" ");
}

function textMatches(f: OkwFacility, q: string): boolean {
  if (!q) return true;
  const hay = [
    f.name,
    f.description,
    locationText(f),
    ...(f.manufacturing_processes ?? []).map(humanizeProcess),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return hay.includes(q.trim().toLowerCase());
}

function distinct(values: (string | null | undefined)[]): string[] {
  return [...new Set(values.filter((v): v is string => !!v))].sort();
}

export function useOkwList() {
  const [filterText, setFilterText] = useState("");
  const [access, setAccess] = useState<Set<string>>(new Set());
  const [status, setStatus] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);

  const query = useQuery({
    queryKey: ["okw-list"],
    queryFn: () => searchOkw({ page: 1, page_size: 100 }),
    staleTime: 60_000,
  });

  const all = useMemo(() => query.data?.results ?? [], [query.data]);

  const accessOptions = useMemo(() => distinct(all.map((f) => f.access_type)), [all]);
  const statusOptions = useMemo(() => distinct(all.map((f) => f.facility_status)), [all]);

  const processed = useMemo(() => {
    const filtered = all.filter(
      (f) =>
        textMatches(f, filterText) &&
        (access.size === 0 || (f.access_type != null && access.has(f.access_type))) &&
        (status.size === 0 || (f.facility_status != null && status.has(f.facility_status))),
    );
    const totalItems = filtered.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
    const safePage = Math.min(page, totalPages);
    const pageItems = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
    return { pageItems, totalItems, totalPages, safePage };
  }, [all, filterText, access, status, page]);

  function toggle(set: Set<string>, setter: (s: Set<string>) => void, value: string) {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    setter(next);
    setPage(1);
  }

  return {
    ...processed,
    filterText,
    accessOptions,
    statusOptions,
    selectedAccess: access,
    selectedStatus: status,
    filterCount: access.size + status.size,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    setPage,
    setFilterText: (t: string) => {
      setFilterText(t);
      setPage(1);
    },
    toggleAccess: (v: string) => toggle(access, setAccess, v),
    toggleStatus: (v: string) => toggle(status, setStatus, v),
    clearFilters: () => {
      setAccess(new Set());
      setStatus(new Set());
      setFilterText("");
      setPage(1);
    },
    PAGE_SIZE,
  };
}
