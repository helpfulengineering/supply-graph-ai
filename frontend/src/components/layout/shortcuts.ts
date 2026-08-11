/**
 * The keyboard contract, as data.
 *
 * Ported from the reference stack's keyboard layer. Kept beside nav.ts and
 * separate from the hook so the drawer's help block and the tests read the
 * same source the handler does — a shortcut that works but is undocumented is
 * a shortcut nobody uses.
 */

/** `g` then a key. Targets are app routes; the chord window is CHORD_MS. */
export const CHORD_ROUTES: Record<string, string> = {
  d: "/",
  k: "/okh",
  f: "/facilities",
  m: "/match",
  p: "/packages",
  r: "/rfq",
  s: "/settings/session",
  // The Create group and Reference, which the first table skipped. A menu
  // entry with no chord is the half of the contract nobody can see is
  // missing; `shortcuts.test.ts` now fails if a nav route has none.
  g: "/okh/generate",
  n: "/okh/new",
  w: "/facilities/new",
  h: "/help",
  o: "/docs/",
};

/** How long `g` stays armed. Long enough to be deliberate, short enough that a
 *  stray `g` does not swallow the next keystroke. */
export const CHORD_MS = 1500;

export interface ShortcutDoc {
  keys: string[];
  desc: string;
}

export const SHORTCUTS: ShortcutDoc[] = [
  { keys: ["?"], desc: "open this menu" },
  { keys: ["Esc"], desc: "close" },
  { keys: ["t"], desc: "next theme" },
  { keys: ["m"], desc: "light / dark" },
  { keys: ["g", "d"], desc: "dashboard" },
  { keys: ["g", "k"], desc: "designs" },
  { keys: ["g", "f"], desc: "facilities" },
  { keys: ["g", "m"], desc: "match" },
  { keys: ["g", "p"], desc: "packages" },
  { keys: ["g", "r"], desc: "RFQ" },
  { keys: ["g", "s"], desc: "settings" },
  { keys: ["g", "g"], desc: "generate from URL" },
  { keys: ["g", "n"], desc: "new design" },
  { keys: ["g", "w"], desc: "new facility" },
  { keys: ["g", "h"], desc: "help" },
  { keys: ["g", "o"], desc: "documentation" },
];

/**
 * True when the key event should be left alone: the user is typing, or holding
 * a modifier that belongs to the browser or OS.
 *
 * contentEditable counts — the markdown and JSON editors are editable divs, not
 * inputs, and swallowing `t` inside one would be a data-entry bug rather than
 * a navigation nicety.
 */
export function isTypingTarget(event: KeyboardEvent): boolean {
  if (event.metaKey || event.ctrlKey || event.altKey) return true;
  const el = event.target as HTMLElement | null;
  if (!el) return false;
  if (el.isContentEditable) return true;
  return /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName);
}
