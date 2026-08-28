"use client";

import { Toast as ToastPrimitive } from "@base-ui/react/toast";
import { AlertTriangle, CheckCircle2, Info, XCircle, X } from "lucide-react";
import type { ReactNode } from "react";
import { BODY_MUTED } from "./typography";
import { userFacingError } from "@/lib/userMessage";
import { cn } from "@/lib/utils";

/**
 * Transient notifications.
 *
 * The app had no way to say "that worked". Every outcome had to be either a
 * permanent banner in the layout — which is what `AuthBanner` is, and rightly,
 * because an expired key is a standing condition — or a line of text wedged
 * beside the control that produced it. So a sync that succeeded said nothing
 * at all, and a sync that failed said it in a sentence under a button, which
 * is off-screen the moment the list it just changed scrolls.
 *
 * Built on Base UI's toast for the same reason Tooltip and Button are: focus
 * management, the `aria-live` region, swipe-to-dismiss, hover-to-pause, and
 * the stacking maths are the library's problem. Everything visual is the token
 * layer's, so a toast re-themes with the other twenty worlds instead of
 * carrying the private palette every toast library ships with.
 *
 * A toast is for something transient and non-blocking. A failure the user must
 * act on belongs in the page — `ErrorMessage` — where it stays put.
 */

/** The tones a toast can carry. `type` is Base UI's own field, so this maps onto it. */
export type ToastTone = "success" | "error" | "warning" | "info";

/**
 * Tone as tokens.
 *
 * Ink is the blended `-ink` variant, not the raw status hue, for the reason
 * `Badge` gives: a mid-lightness colour on a 10% wash of itself lands under
 * AA. The card keeps the neutral panel surface and the hue arrives as a border
 * and an icon — a fully tinted card at this size reads as an alert banner,
 * which is the thing a toast is deliberately not.
 */
const TONES: Record<
  ToastTone,
  { icon: typeof Info; edge: string; ink: string }
> = {
  success: {
    icon: CheckCircle2,
    edge: "border-success/40",
    ink: "text-success-ink",
  },
  error: {
    icon: XCircle,
    edge: "border-destructive/40",
    ink: "text-destructive-ink",
  },
  warning: {
    icon: AlertTriangle,
    edge: "border-warning/40",
    ink: "text-warning-ink",
  },
  info: { icon: Info, edge: "border-info/40", ink: "text-info-ink" },
};

function toneOf(type: string | undefined): ToastTone {
  return type && type in TONES ? (type as ToastTone) : "info";
}

/**
 * The stack, its motion, and where it sits.
 *
 * Bottom-right on a desktop and full-width along the bottom on a phone, which
 * is where a thumb is and where it cannot cover the header. The transform maths
 * — collapsed toasts peeking behind the frontmost one, expanding on hover — is
 * Base UI's documented pattern driven by the `--toast-*` variables it sets;
 * only the surface and the timing are ours.
 *
 * `--z-overlay` for the reason Tooltip names: Leaflet's panes reach z-index 800
 * in the root stacking context, so anything less renders behind the map tiles.
 */
function ToastList() {
  const { toasts } = ToastPrimitive.useToastManager();

  return toasts.map((toast) => {
    const tone = TONES[toneOf(toast.type)];
    const Icon = tone.icon;
    return (
      <ToastPrimitive.Root
        key={toast.id}
        toast={toast}
        className={cn(
          "[--gap:0.6rem] [--peek:0.6rem]",
          "[--scale:calc(max(0,1-(var(--toast-index)*0.08)))] [--shrink:calc(1-var(--scale))]",
          "[--height:var(--toast-frontmost-height,var(--toast-height))]",
          "[--offset-y:calc(var(--toast-offset-y)*-1+calc(var(--toast-index)*var(--gap)*-1)+var(--toast-swipe-movement-y))]",
          "absolute bottom-0 left-auto right-0 w-full origin-bottom",
          "z-[calc(1000-var(--toast-index))] h-[var(--height)] select-none",
          // The surface: the app's own card, one step of elevation up.
          "rounded-lg border bg-card shadow-glow",
          tone.edge,
          // The gap between stacked toasts has to be hoverable, or moving the
          // pointer between them collapses the stack mid-gesture.
          "after:absolute after:left-0 after:top-full after:h-[calc(var(--gap)+1px)] after:w-full after:content-['']",
          "[transform:translateX(var(--toast-swipe-movement-x))_translateY(calc(var(--toast-swipe-movement-y)-(var(--toast-index)*var(--peek))-(var(--shrink)*var(--height))))_scale(var(--scale))]",
          "data-expanded:h-[var(--toast-height)] data-expanded:[transform:translateX(var(--toast-swipe-movement-x))_translateY(var(--offset-y))]",
          "data-starting-style:[transform:translateY(150%)]",
          "data-limited:opacity-0 data-ending-style:opacity-0",
          "[&[data-ending-style]:not([data-limited]):not([data-swipe-direction])]:[transform:translateY(150%)]",
          "data-ending-style:data-[swipe-direction=down]:[transform:translateY(calc(var(--toast-swipe-movement-y)+150%))]",
          "data-ending-style:data-[swipe-direction=right]:[transform:translateX(calc(var(--toast-swipe-movement-x)+150%))_translateY(var(--offset-y))]",
          "[transition:transform_0.4s_cubic-bezier(0.22,1,0.36,1),opacity_0.4s,height_0.15s]",
          // The whole entrance and stacking gesture is decoration; with motion
          // reduced the toast simply appears where it belongs.
          "motion-reduce:[transition:none]",
        )}
      >
        <ToastPrimitive.Content className="flex h-full items-start gap-3 overflow-hidden px-3 py-2.5 transition-opacity duration-200 data-behind:opacity-0 data-expanded:opacity-100">
          <Icon
            aria-hidden="true"
            className={cn("mt-0.5 h-4 w-4 shrink-0", tone.ink)}
          />
          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
            <ToastPrimitive.Title
              className={cn("text-sm font-medium", tone.ink)}
            />
            <ToastPrimitive.Description className={BODY_MUTED} />
            {toast.actionProps && (
              <ToastPrimitive.Action className="mt-1.5 self-start rounded-md border border-border px-2 py-1 text-xs font-medium text-foreground transition-colors hover:bg-muted" />
            )}
          </div>
          {/* An icon-only control, so it carries its own name — the tooltip
              rule in the design system, applied to the one place a toast has
              no visible label to lean on. */}
          <ToastPrimitive.Close
            aria-label="Dismiss notification"
            className="-mr-1 -mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <X aria-hidden="true" className="h-4 w-4" />
          </ToastPrimitive.Close>
        </ToastPrimitive.Content>
      </ToastPrimitive.Root>
    );
  });
}

/**
 * Mounted once, by the provider stack, above the app.
 *
 * `limit` is the point: an operation that fails in a loop can queue a dozen
 * notifications, and a screen buried in cards is worse than the silence this
 * replaced. Three visible, the rest collapsed behind them.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  return (
    <ToastPrimitive.Provider timeout={6000} limit={3}>
      {children}
      <ToastPrimitive.Portal>
        <ToastPrimitive.Viewport
          className="fixed bottom-4 left-4 right-4 top-auto sm:left-auto sm:w-90"
          style={{ zIndex: "var(--z-overlay)" }}
        >
          <ToastList />
        </ToastPrimitive.Viewport>
      </ToastPrimitive.Portal>
    </ToastPrimitive.Provider>
  );
}

export interface ToastOptions {
  /** Supporting line under the title. */
  description?: ReactNode;
  /** Milliseconds before auto-dismissal; 0 pins it until dismissed. */
  timeout?: number;
  /** A single follow-up — "Undo", "View". Keep it to one verb. */
  action?: { label: string; onClick: () => void };
}

/**
 * The app's toast API.
 *
 * Four verbs rather than one `add({ type })`, because the tone is the decision
 * a caller is actually making, and a positional string is the kind of argument
 * that ends up spelled "err" in one file and "danger" in another.
 *
 * `showError` takes the thrown thing rather than a string: every failure in
 * the app is already described by `userFacingError`, and a toast that invents
 * its own wording for a 429 is how one product grows two vocabularies for the
 * same event.
 */
export function useToast() {
  const manager = ToastPrimitive.useToastManager();

  const add = (tone: ToastTone, title: string, options?: ToastOptions) =>
    manager.add({
      type: tone,
      title,
      description: options?.description,
      timeout: options?.timeout,
      // Errors are announced urgently; the rest wait for a pause in speech.
      priority: tone === "error" ? "high" : "low",
      actionProps: options?.action
        ? { children: options.action.label, onClick: options.action.onClick }
        : undefined,
    });

  return {
    showSuccess: (title: string, options?: ToastOptions) =>
      add("success", title, options),
    showInfo: (title: string, options?: ToastOptions) =>
      add("info", title, options),
    showWarning: (title: string, options?: ToastOptions) =>
      add("warning", title, options),
    /**
     * Announce a failure in the same words the rest of the app uses for it.
     *
     * Pinned by default — `timeout: 0`. A message that explains what went
     * wrong is worthless if it has vanished by the time the reader looks up
     * from the control they were operating.
     */
    showError: (err: unknown, options?: ToastOptions) => {
      const message = userFacingError(err);
      return add("error", message.title, {
        description: options?.description ?? message.body,
        timeout: options?.timeout ?? 0,
        action: options?.action,
      });
    },
    dismiss: manager.close,
  };
}
