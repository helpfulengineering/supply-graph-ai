/** Confirm copy for deleting a facility (shared warn when not private). */
export function deleteConfirmMessage(
  name: string,
  visibility: string | null | undefined,
): string {
  const base = `Delete “${name || "this facility"}”?`;
  if (visibility && visibility !== "private") {
    return `${base}\n\nThis facility is shared with peers; delete is local — peers may keep a copy.`;
  }
  return base;
}
