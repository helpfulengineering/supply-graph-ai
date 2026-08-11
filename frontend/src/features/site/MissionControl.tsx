"use client";

import { useEffect, useState } from "react";
import { PageHero } from "../../components/layout/PageHero";
import { useSiteLayer } from "../../lib/site/useSiteLayer";
import { siteConfig } from "../../lib/site/config";
import { PANEL } from "../../components/ui/surface";
import { CARD_TITLE } from "../../components/ui/typography";
import { Button } from "../../components/ui/button";
import { clearVisitor, gateCopy, type GateCopy } from "../../lib/site/stack";
import { Gate } from "./Gate";
import { MyRecord } from "./MyRecord";
import { OperatorPanel } from "./OperatorPanel";
import { VisitorDirectory } from "./VisitorDirectory";
import { OperatorTools } from "./OperatorTools";

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
 *
 * WHAT RENDERS DEPENDS ON THE TIER, and the two tiers are independent doors
 * rather than a ladder:
 *
 *   nobody         the gate, and the operator token field
 *   visitor        + their own record, and the masked directory and feed
 *   operator       the same surfaces, unmasked, with the mutations
 *
 * An operator needs no visitor record and a visitor never becomes an operator
 * by signing in — which is why the token field is outside the signed-in
 * branch, and why `is_admin` on a visitor row is rendered as a marker rather
 * than as access. Each panel does its own reading; this component decides only
 * which of them exist.
 */
export function MissionControl() {
  // The route is gated in the server component; this hook only supplies state.
  const { visitor, isOperator, ready, refresh, unlock, lock } = useSiteLayer();
  const [copy, setCopy] = useState<GateCopy | null>(null);
  const [dismissed, setDismissed] = useState(false);
  // Bumped when a mutation lands, so panels reading the same rows from
  // different RPCs (an operator renaming their own row in the directory) do
  // not sit on each other's stale copy.
  const [changed, setChanged] = useState(0);
  // Same idea for the event count: the operator panel states a total that a
  // purge in the feed below invalidates.
  const [purged, setPurged] = useState(0);

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
      {/*
        The crumb repeats the nav entry's three nouns rather than inventing its
        own. nav.ts calls this group "Operator" and describes the page as
        "telemetry, visitor records, and instance administration"; a hero that
        said something else would make the drawer and the page disagree about
        what the reader just opened.
      */}
      <PageHero
        title="Mission Control"
        crumb="telemetry · visitor records · administration"
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
            <Button
              type="button"
              size="lg"
              className="mt-3"
              onClick={() => setDismissed(false)}
            >
              Sign in
            </Button>
          )}
        </section>
      )}

      {visitor && (
        <MyRecord
          key={`${visitor.email}-${changed}`}
          visitor={visitor}
          onErased={signOut}
          onSignOut={signOut}
        />
      )}

      <OperatorPanel
        isOperator={isOperator}
        unlock={unlock}
        lock={lock}
        eventsChanged={purged}
      />

      {(visitor || isOperator) && (
        <>
          <VisitorDirectory
            email={visitor?.email ?? null}
            isOperator={isOperator}
            onVisitorChanged={() => setChanged((n) => n + 1)}
          />
          <OperatorTools
            email={visitor?.email ?? null}
            isOperator={isOperator}
            onEventsChanged={() => setPurged((n) => n + 1)}
          />
        </>
      )}

      <p className="font-mono text-xs text-muted-foreground">
        site layer connected · {new URL(siteConfig.url).host}
      </p>
    </div>
  );
}
