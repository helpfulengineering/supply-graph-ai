"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { FIELD, HINT, LABEL } from "../../components/ui/field";
import { useDialogFocus } from "../../lib/useDialogFocus";
import { signIn, type GateCopy } from "../../lib/site/stack";
import { gateFieldErrors, gateFieldsValid, type GateFieldErrors } from "./gateValidation";

interface GateProps {
  /** Operator-configured copy, already merged with the defaults. */
  copy: GateCopy;
  /** The visitor record now exists on this device — re-read site state. */
  onSignedIn: () => void;
  /** Dismissed without signing in. */
  onDismiss: () => void;
}

/**
 * The visitor gate: the sign-in the site layer's own surface asks for.
 *
 * WHAT IT GATES, AND WHAT IT MUST NOT. This stands in front of Mission
 * Control only. It never stands in front of the app: OHM's job is matching
 * designs to facilities, and a telemetry sign-in that blocked that would be
 * the site layer reaching past its boundary — the same boundary that keeps
 * isOperator out of isAdmin. Nothing here grants an application permission,
 * and the fine print says so where a visitor will actually read it.
 *
 * It is dismissible, and dismissal is not a dead end: Mission Control keeps a
 * sign-in button, so the escape hatch every modal needs (Esc, the backdrop,
 * "Not now") costs nobody the page they came for. Only the parts that are
 * genuinely per-visitor — your own record — need the record to exist.
 */
export function Gate({ copy, onSignedIn, onDismiss }: GateProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState<GateFieldErrors>({});
  const [failed, setFailed] = useState(false);
  const [pending, setPending] = useState(false);
  const ids = useId();

  useDialogFocus(panelRef, { active: true, onClose: onDismiss });

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const found = gateFieldErrors(name, email);
    setErrors(found);
    setFailed(false);
    if (!gateFieldsValid(found)) return;

    setPending(true);
    // Normalised to what the RPC stores, so the local record and the row agree
    // — the operator probe reads back by exactly this email.
    const ok = await signIn(name.trim(), email.trim().toLowerCase());
    setPending(false);
    if (ok) onSignedIn();
    else setFailed(true);
  }

  const titleId = `${ids}-title`;
  const bodyId = `${ids}-body`;
  const nameId = `${ids}-name`;
  const emailId = `${ids}-email`;

  return createPortal(
    <div className="fixed inset-0" style={{ zIndex: "var(--z-overlay)" }}>
      <div
        className="absolute inset-0 bg-black/50 animate-in fade-in duration-150 motion-reduce:animate-none"
        onClick={onDismiss}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={bodyId}
        className="absolute left-1/2 top-1/2 w-[min(30rem,calc(100vw-2rem))] max-h-[calc(100vh-2rem)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-border bg-card p-5 shadow-xl animate-in fade-in zoom-in-95 duration-150 motion-reduce:animate-none"
      >
        <h2 id={titleId} className="text-base font-semibold text-foreground">
          {copy.title}
        </h2>
        <p id={bodyId} className="mt-1 text-sm text-muted-foreground">
          {copy.body}
        </p>

        <form onSubmit={onSubmit} noValidate className="mt-4 space-y-3">
          <div>
            <label htmlFor={nameId} className={LABEL}>
              Name
            </label>
            <input
              id={nameId}
              name="name"
              type="text"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-invalid={errors.name ? true : undefined}
              aria-describedby={errors.name ? `${nameId}-error` : undefined}
              className={`${FIELD} mt-1`}
            />
            {errors.name && (
              <p id={`${nameId}-error`} className={HINT}>
                {errors.name}
              </p>
            )}
          </div>

          <div>
            <label htmlFor={emailId} className={LABEL}>
              Email
            </label>
            <input
              id={emailId}
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-invalid={errors.email ? true : undefined}
              aria-describedby={errors.email ? `${emailId}-error` : undefined}
              className={`${FIELD} mt-1`}
            />
            {errors.email && (
              <p id={`${emailId}-error`} className={HINT}>
                {errors.email}
              </p>
            )}
          </div>

          {failed && (
            <p role="alert" className="text-sm text-destructive">
              Sign-in could not be completed. Your connection or this site&apos;s
              record keeping may be unavailable — the rest of OHM is unaffected.
            </p>
          )}

          <div className="flex items-center gap-2 pt-1">
            <button
              type="submit"
              disabled={pending}
              className="inline-flex min-h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/80 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {pending ? "Signing in…" : "Sign in"}
            </button>
            <button
              type="button"
              onClick={onDismiss}
              className="inline-flex min-h-9 items-center rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              Not now
            </button>
          </div>
        </form>

        <p className="mt-4 border-t border-border pt-3 text-xs text-muted-foreground">
          {copy.fine}
        </p>
      </div>
    </div>,
    document.body,
  );
}
