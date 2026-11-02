/**
 * A hint that this tab signed in with the session cookie (#570).
 *
 * The cookie itself is HttpOnly, so script cannot see it. The hint is not a
 * credential. It lives in localStorage so a new tab still knows to send the
 * cookie. It tells the client to send the cookie and the CSRF header, and to
 * leave any pasted API key out of the request while the session lasts.
 */

const HINT_KEY = "ohm_session_hint";

function safely(run: () => void): void {
  try {
    run();
  } catch {
    // A blocked store means the UI will not know about the cookie. The cookie
    // is still what authenticates.
  }
}

export function hasSessionHint(): boolean {
  try {
    return localStorage.getItem(HINT_KEY) === "1";
  } catch {
    return false;
  }
}

export function markSessionHint(): void {
  safely(() => localStorage.setItem(HINT_KEY, "1"));
}

export function clearSessionHint(): void {
  safely(() => localStorage.removeItem(HINT_KEY));
}

/** The readable CSRF cookie. The session cookie is HttpOnly and not here. */
export function readCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  for (const part of document.cookie.split("; ")) {
    const [name, ...rest] = part.split("=");
    if (name === "ohm_csrf" || name === "__Host-ohm_csrf") {
      return decodeURIComponent(rest.join("="));
    }
  }
  return null;
}
