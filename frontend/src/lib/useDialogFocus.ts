"use client";

import { useEffect, type RefObject } from "react";

interface DialogFocusOptions {
  /** Whether the dialog is currently mounted and modal. */
  active: boolean;
  /** Escape — and, where the caller wires it, the backdrop — dismisses. */
  onClose: () => void;
}

/**
 * Modal dialog behaviour: focus the first control, trap Tab inside the panel,
 * close on Escape, lock background scroll, and hand focus back to the opener
 * when the dialog unmounts.
 *
 * This lived inline in NavDrawer until the site-layer gate needed the same
 * five behaviours. Two hand-rolled traps is how one of them silently loses
 * Shift+Tab wrapping or focus restoration, and only the drawer has an e2e test
 * watching for it — so the behaviour is one function that both dialogs share.
 *
 * The dialog is expected to be rendered only while open (unmount is the exit
 * path), which is what makes focus restoration a cleanup and nothing more.
 */
export function useDialogFocus(
  panelRef: RefObject<HTMLElement | null>,
  { active, onClose }: DialogFocusOptions,
): void {
  useEffect(() => {
    if (!active) return;
    const opener = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    if (!panel) return;

    const focusables = () =>
      Array.from(
        panel.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
    focusables()[0]?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== "Tab") return;
      const items = focusables();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
      opener?.focus();
    };
  }, [active, onClose, panelRef]);
}
