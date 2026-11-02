"use client";

import { useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import { FIELD, LABEL } from "../../components/ui/field";
import { PANEL } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../api/ohm/client";
import { fetchSecurityPolicy, registerPerson } from "../../api/ohm/identity";

/**
 * One-screen signup that stays on the page that opened it (#572).
 *
 * Leaving for /register threw away an in-progress generation: the edited
 * result and the repository address. This signs the person in where they
 * are, and names the node and who runs it, because that is whose node the
 * account is on.
 */
export function InlineSignup({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { noteSession } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recoveryCode, setRecoveryCode] = useState<string | null>(null);

  const policy = useQuery({
    queryKey: ["identity", "security-policy"],
    queryFn: fetchSecurityPolicy,
    staleTime: 5 * 60_000,
    retry: false,
    enabled: open,
  });

  if (!open || typeof document === "undefined") return null;

  const nodeName = policy.data?.node_name || "this node";
  const operatorName = policy.data?.operator_name || "its operator";
  const closed = policy.data?.open_registration === false;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const name = displayName.trim();
    if (!name || !username.trim() || !password) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await registerPerson({
        username: username.trim(),
        password,
        display_name: name,
      });
      await noteSession();
      if (result.recovery_code) setRecoveryCode(result.recovery_code);
      else onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return createPortal(
    <div className="fixed inset-0" style={{ zIndex: "var(--z-overlay)" }}>
      <div
        className="absolute inset-0 bg-black/50"
        onClick={recoveryCode ? undefined : onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="inline-signup-title"
        className={`${PANEL} absolute left-1/2 top-1/2 w-[min(30rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 p-5`}
      >
        <h2 id="inline-signup-title" className={SECTION_TITLE}>
          Create an account on {nodeName}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Run by {operatorName}. A username, a password and a display name.
          Nothing else is asked for.
        </p>
        {closed ? (
          <p className="mt-4 text-sm">
            This node does not accept registrations. Ask {operatorName} for an
            account.
          </p>
        ) : recoveryCode ? (
          <div className="mt-4 space-y-3">
            <p className="text-sm">
              Recovery code: <span className="font-mono">{recoveryCode}</span>
            </p>
            <p className="text-sm text-muted-foreground">
              Save this somewhere other than this browser. It is the way back in
              if you forget the password.
            </p>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent"
            >
              Continue
            </button>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="mt-4 space-y-3">
            <label className={LABEL}>
              Username
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
                className={`${FIELD} mt-1 w-full`}
              />
            </label>
            <label className={LABEL}>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                required
                className={`${FIELD} mt-1 w-full`}
              />
            </label>
            <label className={LABEL}>
              Display name
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                autoComplete="name"
                required
                className={`${FIELD} mt-1 w-full`}
              />
            </label>
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={
                submitting ||
                !displayName.trim() ||
                !username.trim() ||
                !password
              }
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent disabled:opacity-50"
            >
              {submitting ? "Creating account…" : "Create account"}
            </button>
          </form>
        )}
      </div>
    </div>,
    document.body,
  );
}
