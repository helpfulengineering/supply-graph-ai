import { LoadingState } from "./states";

interface Props {
  message?: string;
  className?: string;
}

/**
 * The older spelling of `LoadingState`, and now the same component.
 *
 * These were two implementations of one thing: identical layout, identical
 * default message, differing only in which borrowed glyph they span — and
 * only one of them was in a live region, so half the app's loading states
 * were silent to a screen reader depending on which import a view happened to
 * pick. The mark-based loader made that split visible, since a page could
 * show the product's own mark in one panel and a generic arc in the next.
 *
 * Collapsing the ~20 call sites onto `LoadingState` is a rename, not a
 * behaviour change, and belongs in its own change; this makes the two
 * spellings mean the same thing today.
 */
export function LoadingSpinner({ message = "Loading…", className = "" }: Props) {
  return <LoadingState message={message} className={className} />;
}
