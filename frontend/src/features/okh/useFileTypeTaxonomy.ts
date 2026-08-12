"use client";

/**
 * The server's file-type taxonomy, as an extension lookup.
 *
 * Instance configuration, not content: it changes when an operator edits the
 * YAML and reloads, so it takes the long stale time rather than the catalogue's.
 * A failure resolves to an empty map, which is exactly the "no taxonomy" case
 * `renderTierFrom` already falls back from — the file browser then behaves the
 * way it did before this existed.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchFileTypes, fileTypesByExtension } from "@/api/ohm/file-types";
import type { FileTypeDefinition } from "@/api/ohm/file-types";

export function useFileTypeTaxonomy(): Map<string, FileTypeDefinition> {
  const { data } = useQuery({
    queryKey: ["file-types"],
    queryFn: fetchFileTypes,
    retry: false,
    retryOnMount: false,
    staleTime: Infinity,
  });

  return useMemo(() => (data ? fileTypesByExtension(data) : new Map()), [data]);
}
