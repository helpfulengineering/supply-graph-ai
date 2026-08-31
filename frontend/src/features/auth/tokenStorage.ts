/**
 * Where the API bearer token lives, and for how long.
 *
 * Two kinds of session, because they belong to two different people (#415):
 *
 * - **minted** — the app issued this token itself, at registration or recovery.
 *   It persists, so a member of the public who joined is still signed in
 *   tomorrow. Re-entering a 43-character secret on every new tab is the
 *   pressure that trains people to keep credentials somewhere careless.
 * - **pasted** — someone typed a key they already had into Settings, which is
 *   what an operator does with an admin key. Tab-scoped, exactly as before.
 *
 * The distinction is how the session *began*, not what it can do. Recording it
 * beats inferring it later from permissions: a registered user could be granted
 * admin, and an operator could paste a read-only key, so permissions answer a
 * different question than "should this survive the tab".
 *
 * Persisting a credential means an XSS in the app reads it for as long as it is
 * valid, which on its own is a bad trade. It is acceptable here only because
 * two other things landed first: self-service keys now expire (#413), and their
 * owner can revoke them without finding an operator (#413). Persistence,
 * expiry, and revocation are one package.
 */

const STORAGE_KEY = "ohm_api_key";
const ORIGIN_KEY = "ohm_api_key_origin";

/** How a session began. Persisted alongside the token it describes. */
export type SessionOrigin = "minted" | "pasted";

/** Storage can throw outright — Safari private mode, cookies-blocked. */
function safely<T>(read: () => T, fallback: T): T {
  try {
    return read();
  } catch {
    return fallback;
  }
}

function normalise(value: string | null): string | null {
  return value && value.trim() ? value.trim() : null;
}

/**
 * The token for this tab.
 *
 * A pasted key wins over a persisted one: pasting is a deliberate act in this
 * tab, and it would be strange for it to be silently overridden by a session
 * the visitor started days ago.
 */
export function getToken(): string | null {
  return safely(
    () =>
      normalise(sessionStorage.getItem(STORAGE_KEY)) ??
      normalise(localStorage.getItem(STORAGE_KEY)),
    null,
  );
}

/** How the active session began, or null when there is none. */
export function getSessionOrigin(): SessionOrigin | null {
  return safely(() => {
    if (normalise(sessionStorage.getItem(STORAGE_KEY))) return "pasted";
    if (normalise(localStorage.getItem(STORAGE_KEY))) {
      return (localStorage.getItem(ORIGIN_KEY) as SessionOrigin) ?? "minted";
    }
    return null;
  }, null);
}

/**
 * Adopt a token. `origin` decides whether it outlives the tab.
 *
 * Defaults to `pasted`, the conservative of the two: a caller that forgets to
 * say gets the shorter-lived session rather than the more exposed one.
 */
export function setToken(token: string, origin: SessionOrigin = "pasted"): void {
  const value = token.trim();
  // Written to one store only, so the two can never disagree about the token.
  clearToken();
  try {
    if (origin === "minted") {
      localStorage.setItem(STORAGE_KEY, value);
      localStorage.setItem(ORIGIN_KEY, origin);
    } else {
      sessionStorage.setItem(STORAGE_KEY, value);
    }
  } catch {
    // A blocked store must not leave the caller believing they are signed in.
  }
}

/** Clear both stores. Signing out has to mean everywhere, not just this tab. */
export function clearToken(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(ORIGIN_KEY);
  } catch {
    // Nothing to clear if the store is unavailable.
  }
}

/** Dev-only: seed session from NEXT_PUBLIC_OHM_API_KEY when empty. */
export function seedTokenFromEnv(): void {
  if (getToken()) return;
  const fromEnv = process.env.NEXT_PUBLIC_OHM_API_KEY;
  if (typeof fromEnv === "string" && fromEnv.trim()) {
    // A key from the environment is one the developer already had: pasted.
    setToken(fromEnv, "pasted");
  }
}

/** Authorization header value, or null when unauthenticated. */
export function authHeader(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
