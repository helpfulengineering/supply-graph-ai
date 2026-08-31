import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  clearToken,
  getSessionOrigin,
  getToken,
  seedTokenFromEnv,
  setToken as persistToken,
  type SessionOrigin,
} from "../features/auth/tokenStorage";
import { fetchWhoami, type AuthenticatedUser } from "../api/ohm/identity";
import { ApiError } from "../api/ohm/client";

export type AuthContextValue = {
  token: string | null;
  user: AuthenticatedUser | null;
  isAdmin: boolean;
  hasWrite: boolean;
  isLoading: boolean;
  authError: Error | null;
  /** `origin` decides whether the session outlives the tab — see tokenStorage. */
  setToken: (token: string, origin?: SessionOrigin) => Promise<void>;
  /** How the active session began, so the UI can say why it persists. */
  sessionOrigin: SessionOrigin | null;
  clear: () => void;
  /** Last 401/403 from a mutation or whoami — drives AuthBanner. */
  reportAuthFailure: (err: unknown) => void;
  clearAuthFailure: () => void;
  authFailure: string | null;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setTokenState] = useState<string | null>(() => {
    seedTokenFromEnv();
    return getToken();
  });
  const [authFailure, setAuthFailure] = useState<string | null>(null);
  const [sessionOrigin, setSessionOrigin] = useState<SessionOrigin | null>(() =>
    getSessionOrigin(),
  );

  const whoami = useQuery({
    queryKey: ["identity", "whoami", token],
    queryFn: fetchWhoami,
    enabled: Boolean(token),
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (whoami.error instanceof ApiError && whoami.error.status === 401) {
      // A persisted session that has simply aged out is the common case now
      // that self-service keys expire, and "rejected" reads as "something is
      // wrong with you" for what is really "this ran out, as designed".
      const expired = /expired/i.test(whoami.error.message);
      clearToken();
      setTokenState(null);
      setSessionOrigin(null);
      setAuthFailure(
        expired
          ? "Your key expired, so you have been signed out. Sign in again, or recover your account if you no longer have it."
          : "API key rejected. Paste a valid key in Settings.",
      );
    }
  }, [whoami.error]);

  const setToken = useCallback(
    async (next: string, origin: SessionOrigin = "pasted") => {
      persistToken(next, origin);
      setTokenState(getToken());
      setSessionOrigin(getSessionOrigin());
      setAuthFailure(null);
      await queryClient.invalidateQueries({ queryKey: ["identity", "whoami"] });
    },
    [queryClient],
  );

  const clear = useCallback(() => {
    clearToken();
    setTokenState(null);
    setSessionOrigin(null);
    setAuthFailure(null);
    queryClient.removeQueries({ queryKey: ["identity", "whoami"] });
  }, [queryClient]);

  const reportAuthFailure = useCallback((err: unknown) => {
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      setAuthFailure(
        err.status === 401
          ? "Authentication required. Connect an API key in Settings."
          : "Not authorized for this action.",
      );
    }
  }, []);

  const user = whoami.data ?? null;
  const permissions = user?.permissions ?? [];
  const isAdmin = permissions.includes("admin");
  const hasWrite = isAdmin || permissions.includes("write");

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isAdmin,
      hasWrite,
      isLoading: Boolean(token) && (whoami.isPending || whoami.isFetching),
      authError: whoami.error instanceof Error ? whoami.error : null,
      setToken,
      clear,
      reportAuthFailure,
      clearAuthFailure: () => setAuthFailure(null),
      authFailure,
      sessionOrigin,
    }),
    [
      token,
      user,
      isAdmin,
      hasWrite,
      whoami.isPending,
      whoami.isFetching,
      whoami.error,
      setToken,
      clear,
      reportAuthFailure,
      authFailure,
      sessionOrigin,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
