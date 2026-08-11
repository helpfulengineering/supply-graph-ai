"use client";

import { useEffect, useRef, type RefObject } from "react";

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
 * `active` is the modal window, not the mounted window: a dialog that plays an
 * exit animation stays in the DOM for a beat after it stops being modal, and
 * releasing the trap at the start of that beat — rather than at unmount — is
 * what hands focus back while the panel is still sliding out.
 */
export function useDialogFocus(
  panelRef: RefObject<HTMLElement | null>,
  { active, onClose }: DialogFocusOptions,
): void {
  // Through a ref, so the effect below runs ONCE per opening. It used to take
  // onClose as a dependency, and every caller passes an inline arrow — so any
  // re-render of the opener tore the trap down and built it again, and the
  // teardown moves focus. Picking a theme inside the drawer re-rendered the
  // header, which threw focus from the radio back to the close button; worse,
  // the rebuild then recorded the drawer's own radio as the "opener", so
  // closing returned focus to an element that no longer existed and it landed
  // on <body>. Both were live in production.
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

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
        onCloseRef.current();
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
  }, [active, panelRef]);
}
