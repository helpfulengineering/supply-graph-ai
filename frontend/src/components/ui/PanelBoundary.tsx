"use client";

import { Component, type ReactNode } from "react";
import { PANEL, PANEL_BODY } from "./surface";
import { BODY_MUTED, CARD_TITLE } from "./typography";
import { cn } from "@/lib/utils";

interface Props {
  /** Names the panel in the fallback, so a reader knows what is missing. */
  label: string;
  children: ReactNode;
}

interface State {
  failed: boolean;
}

/**
 * A boundary around one optional panel.
 *
 * `app/error.tsx` catches a throw already, but it is route-scoped: it replaces
 * the whole view, so one secondary panel costs the graph and the KPIs with it.
 * A panel's own `isError` handling covers only *fetch* failure — a render that
 * throws is above it.
 *
 * No retry, deliberately: re-rendering the same bad payload throws again. The
 * route boundary's "Try again" re-fetches, which can actually change it.
 */
export class PanelBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error) {
    // The console is this app's only sink (see app/error.tsx). Containing a
    // failure silently would be a worse trade than the crash it replaces.
    console.error(`Panel "${this.props.label}" failed to render:`, error);
  }

  render() {
    if (!this.state.failed) return this.props.children;

    // role="status" already implies a polite live region, which is what
    // announces a panel that fails on a re-render rather than on mount.
    return (
      <section role="status" className={cn(PANEL, PANEL_BODY)}>
        {/* Not SectionHeading: that renders a permalink, and a failure state
            is not a destination. */}
        <h2 className={CARD_TITLE}>{this.props.label}</h2>
        <p className={cn(BODY_MUTED, "mt-2")}>
          This panel could not be displayed. The rest of the page is unaffected.
        </p>
      </section>
    );
  }
}
