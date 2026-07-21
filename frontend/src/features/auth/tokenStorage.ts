/** sessionStorage key for the peacetime API Bearer token (F0). */
const STORAGE_KEY = "ohm_api_key";

export function getToken(): string | null {
  try {
    const value = sessionStorage.getItem(STORAGE_KEY);
    return value && value.trim() ? value.trim() : null;
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  sessionStorage.setItem(STORAGE_KEY, token.trim());
}

export function clearToken(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}

/** Dev-only: seed session from VITE_OHM_API_KEY when empty. */
export function seedTokenFromEnv(): void {
  if (getToken()) return;
  const fromEnv = import.meta.env.VITE_OHM_API_KEY;
  if (typeof fromEnv === "string" && fromEnv.trim()) {
    setToken(fromEnv);
  }
}

/** Authorization header value, or null when unauthenticated. */
export function authHeader(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
