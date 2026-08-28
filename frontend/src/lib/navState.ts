/**
 * Cross-route hand-off state, replacing react-router's `location.state`.
 *
 * Two flows hand a payload to the next route without persisting it as a
 * record: generate → match (a whole reviewed-but-unsaved manifest) and
 * match → rfq (the selected solutions). The App Router has no navigation
 * state, so the payload is stashed in sessionStorage under a nonce and the
 * nonce travels in the URL (`?h=`). This mirrors history-entry semantics:
 * a refresh keeps the state (sessionStorage survives reload), back/forward
 * re-reads it (the URL carries the nonce), a direct visit has none, and a
 * new tab starts clean (sessionStorage is per-tab).
 */

const PREFIX = "ohm_nav_state:";
const MAX_ENTRIES = 10;

interface Entry {
  ts: number;
  payload: unknown;
}

function prune(): void {
  const keys: { key: string; ts: number }[] = [];
  for (let i = 0; i < sessionStorage.length; i += 1) {
    const key = sessionStorage.key(i);
    if (!key?.startsWith(PREFIX)) continue;
    try {
      const entry = JSON.parse(sessionStorage.getItem(key) ?? "") as Entry;
      keys.push({ key, ts: entry.ts });
    } catch {
      keys.push({ key, ts: 0 });
    }
  }
  keys
    .sort((a, b) => b.ts - a.ts)
    .slice(MAX_ENTRIES)
    .forEach(({ key }) => sessionStorage.removeItem(key));
}

/** Stash a payload and return the target URL carrying its nonce. */
export function withNavState(path: string, payload: unknown): string {
  const nonce = Math.random().toString(36).slice(2, 10);
  try {
    const entry: Entry = { ts: Date.now(), payload };
    sessionStorage.setItem(PREFIX + nonce, JSON.stringify(entry));
    prune();
  } catch {
    // Storage unavailable (private browsing quota, etc.) — navigate without
    // state; the destination treats a missing payload as a direct visit.
    return path;
  }
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}h=${nonce}`;
}

/** Read a stashed payload by nonce. Not consumed: refresh and back re-read it. */
export function readNavState<T>(nonce: string | null): T | null {
  if (!nonce) return null;
  try {
    const raw = sessionStorage.getItem(PREFIX + nonce);
    if (!raw) return null;
    return (JSON.parse(raw) as Entry).payload as T;
  } catch {
    return null;
  }
}
