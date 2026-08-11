"use client";

import { useEffect, useState } from "react";
import { PageHero } from "../../components/layout/PageHero";
import { useSiteLayer } from "../../lib/site/useSiteLayer";
import { siteConfig } from "../../lib/site/config";
import { PANEL } from "../../components/ui/surface";
import { CARD_TITLE } from "../../components/ui/typography";
import { clearVisitor, gateCopy, type GateCopy } from "../../lib/site/stack";
import { Gate } from "./Gate";

/**
 * Mission Control — the site layer's own surface: telemetry, visitor records,
 * whitelabel config.
 *
 * It is a SITE surface and must not appear to grant application powers. The
 * ten admin panels under /settings are gated by the backend's whoami and are
 * untouched by anything here.
 *
 * With the layer disabled this route 404s rather than rendering an explanation.
 * That is the point of "off is a first-class state": on the default deployment
 * the feature does not exist, so a page apologising for its absence would be
 * describing a misconfiguration that isn't one.
 */
export function MissionControl() {
  // The route is gated in the server component; this hook only supplies state.
  const { visitor, isOperator, ready, refresh } = useSiteLayer();
  const [copy, setCopy] = useState<GateCopy | null>(null);
  const [dismissed, setDismissed] = useState(false);

  // Fetched rather than assumed: the gate's heading, body, and fine print are
  // the operator's to write, and `enabled: false` is their way to say this
  // instance asks nobody to sign in. Until it resolves no gate is shown, so a
  // gate-less instance never flashes one.
  useEffect(() => {
    let cancelled = false;
    void gateCopy().then((c) => {
      if (!cancelled) setCopy(c);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const gateOpen = ready && !visitor && !dismissed && copy?.enabled === true;

  function signOut(): void {
    clearVisitor();
    // Deliberately not re-gated: signing out and being handed the sign-in
    // dialog back reads as the page refusing to let go.
    setDismissed(true);
    refresh();
  }

  return (
    <div className="space-y-6">
      <PageHero
        title="Mission Control"
        crumb="telemetry · visitors · tiered access"
      />

      {gateOpen && copy && (
        <Gate
          copy={copy}
          onSignedIn={() => {
            setDismissed(false);
            refresh();
          }}
          onDismiss={() => setDismissed(true)}
        />
      )}

      {!visitor && (
        <section className={PANEL}>
          <h2 className={CARD_TITLE}>Not signed in</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Sign in at the gate to see your own record. Site sign-in is separate
            from your OHM API session and grants no application permissions.
          </p>
          {copy?.enabled && !gateOpen && (
            <button
              type="button"
              onClick={() => setDismissed(false)}
              className="mt-3 inline-flex min-h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/80"
            >
              Sign in
            </button>
          )}
        </section>
      )}

      {visitor && (
        <section className={PANEL}>
          <h2 className={CARD_TITLE}>My record</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {visitor.name} · {visitor.email}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            You control this record: rename it, or erase it and every telemetry
            event attributed to it.
          </p>
          <button
            type="button"
            onClick={signOut}
            className="mt-3 inline-flex min-h-9 items-center rounded-md border border-border px-3 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            Sign out
          </button>
          <p className="mt-2 text-xs text-muted-foreground">
            Signing out forgets this record on this device; it does not erase
            it.
          </p>
        </section>
      )}

      <section className={PANEL}>
        <h2 className={CARD_TITLE}>
          Operator{" "}
          <span className="ml-1 font-mono text-xs font-normal text-muted-foreground">
            {isOperator ? "verified" : "locked"}
          </span>
        </h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Unmasked visitor and telemetry reads require the operator token,
          verified server-side and held in this tab only. Site-layer operator
          status is not OHM admin.
        </p>
      </section>

      <p className="font-mono text-xs text-muted-foreground">
        site layer connected · {new URL(siteConfig.url).host}
      </p>
    </div>
  );
}
