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
  getToken,
  seedTokenFromEnv,
  setToken as persistToken,
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
  setToken: (token: string) => Promise<void>;
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

  const whoami = useQuery({
    queryKey: ["identity", "whoami", token],
    queryFn: fetchWhoami,
    enabled: Boolean(token),
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (whoami.error instanceof ApiError && whoami.error.status === 401) {
      clearToken();
      setTokenState(null);
      setAuthFailure("API key rejected. Paste a valid key in Settings.");
    }
  }, [whoami.error]);

  const setToken = useCallback(
    async (next: string) => {
      persistToken(next);
      setTokenState(getToken());
      setAuthFailure(null);
      await queryClient.invalidateQueries({ queryKey: ["identity", "whoami"] });
    },
    [queryClient],
  );

  const clear = useCallback(() => {
    clearToken();
    setTokenState(null);
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
